"""Capture an allowlisted validation record without serialising task results."""

import hashlib
import json
import os
import re
import stat
import subprocess

from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = "aggregate"
    CALLBACK_NAME = "validation_capture"
    CALLBACK_NEEDS_ENABLED = False
    CALLBACK_NEEDS_WHITELIST = False
    ALLOWED_FIELDS = frozenset(("task", "status", "censored"))
    # The malformed-proxy action is an include wrapper.  Capture the leaf
    # validation task, not the wrapper, because the wrapper result only says
    # that an included task failed and is not the actionable failure record.
    CAPTURED_ACTION_TASKS = {
        "Validate a valid PostgreSQL blueprint": "Running validation for a valid blueprint",
        "Reject a malformed DCS proxy": "Checking endpoint syntax",
    }
    CAPTURED_TASK_NAMES = frozenset(CAPTURED_ACTION_TASKS.values())
    ALLOWED_STATUSES = frozenset(("ok", "failed", "unreachable"))
    PATH_ENV = "IDARSI_VALIDATION_CALLBACK_PATH"
    ROOT_ENV = "IDARSI_VALIDATION_CALLBACK_ROOT"

    def __init__(self):
        super().__init__()
        self.path = os.environ.get(self.PATH_ENV)
        self.root = os.environ.get(self.ROOT_ENV)
        self._validate_configuration()

    def _validate_configuration(self):
        if not self.path or not self.root or not os.path.isabs(self.path) or not os.path.isabs(self.root):
            raise RuntimeError("Validation callback requires absolute path and root configuration")
        if os.path.normpath(self.root) != self.root or os.path.normpath(self.path) != self.path:
            raise RuntimeError("Validation callback paths must be normalized absolute paths")
        if os.path.commonpath((self.root, self.path)) != self.root or self.path == self.root:
            raise RuntimeError("Validation callback path must be below its private run root")

        expected_uid = os.geteuid()
        current = "/"
        components = self.path.strip("/").split("/")
        parent_components = components[:-1]
        for component in parent_components:
            current = os.path.join(current, component)
            try:
                metadata = os.lstat(current)
            except OSError as error:
                raise RuntimeError(f"Validation callback parent is missing: {current}") from error
            if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
                raise RuntimeError(f"Validation callback parent is not a directory: {current}")
            mode = stat.S_IMODE(metadata.st_mode)
            safe_sticky_tmp = metadata.st_uid == 0 and mode == 0o1777
            if metadata.st_uid not in (0, expected_uid) or (metadata.st_mode & 0o022 and not safe_sticky_tmp):
                raise RuntimeError(f"Validation callback parent is not private: {current}")
            self._assert_acl_safe(current)
        try:
            destination = os.lstat(self.path)
        except FileNotFoundError:
            return
        except OSError as error:
            raise RuntimeError("Validation callback destination cannot be inspected") from error
        if (stat.S_ISLNK(destination.st_mode) or not stat.S_ISREG(destination.st_mode)
                or destination.st_uid != expected_uid or stat.S_IMODE(destination.st_mode) != 0o600):
            raise RuntimeError("Validation callback destination is unsafe")
        self._assert_acl_safe(self.path)

    @staticmethod
    def _assert_acl_safe(path):
        try:
            acl = subprocess.run(
                ["getfacl", "--absolute-names", "--", path],
                check=False, capture_output=True, text=True,
            )
        except OSError as error:
            raise RuntimeError("Validation callback requires getfacl for ACL validation") from error
        if acl.returncode != 0 or re.search(r"^(?:default:|user:[^:]+:|group:[^:]+:)", acl.stdout, re.MULTILINE):
            raise RuntimeError(f"Validation callback path has unsafe ACLs: {path}")

    def _capture(self, result, status):
        task_name = self._task_name(result)
        play_name = self._play_name(result)
        if task_name not in self.CAPTURED_TASK_NAMES:
            return
        if play_name and self.CAPTURED_ACTION_TASKS.get(play_name) != task_name:
            return
        record = {
            "task": self._task_identifier(result),
            "status": status,
            # The callback deliberately emits only censored metadata.  Never
            # inspect or serialise the result payload, including no_log data.
            "censored": True,
        }
        if set(record) != self.ALLOWED_FIELDS or status not in self.ALLOWED_STATUSES:
            return
        payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
        flags = os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW
        try:
            try:
                descriptor = os.open(self.path, flags | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                descriptor = os.open(self.path, flags)
            with os.fdopen(descriptor, "ab", closefd=True) as capture:
                metadata = os.fstat(capture.fileno())
                if (not stat.S_ISREG(metadata.st_mode) or metadata.st_uid != os.geteuid()
                        or stat.S_IMODE(metadata.st_mode) != 0o600):
                    raise RuntimeError("Validation callback destination became unsafe")
                capture.write(payload)
        except OSError as error:
            raise RuntimeError("Validation callback refused unsafe or unavailable destination") from error

    @staticmethod
    def _task_name(result):
        task = getattr(result, "_task", None)
        return str(getattr(task, "name", "") or getattr(result, "task" + "_name", ""))

    @classmethod
    def _task_identifier(cls, result):
        """Hash play, host, task, and handler context without exposing names."""
        task = getattr(result, "_task", None)
        host = getattr(result, "_host", None)
        parents = []
        current = getattr(task, "_parent", None)
        while current is not None and len(parents) < 16:
            parents.append(current)
            current = getattr(current, "_parent", None)
        play = cls._play_name(result)
        handler = next(
            (getattr(parent, "name", "") for parent in parents
             if "handler" in parent.__class__.__name__.lower()),
            "",
        )
        identity = "".join(
            f"{len(value)}:{value}"
            for value in (
                str(play),
                str(getattr(host, "name", "")),
                cls._task_name(result),
                str(handler),
            )
        )
        return "action-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @staticmethod
    def _play_name(result):
        task = getattr(result, "_task", None)
        current = getattr(task, "_parent", None)
        parents = []
        while current is not None and len(parents) < 16:
            parents.append(current)
            current = getattr(current, "_parent", None)
        return next(
            (str(getattr(parent, "name", "")) for parent in parents
             if parent.__class__.__name__.lower() == "play"),
            "",
        )

    def v2_runner_on_ok(self, result):
        self._capture(result, "ok")

    def v2_runner_on_failed(self, result, ignore_errors=False):
        self._capture(result, "failed")

    def v2_runner_on_unreachable(self, result):
        # Keep unreachable actions as an explicit, deterministic failure record.
        # Do not let the normal callback summary hide an action that never ran.
        self._capture(result, "unreachable")
