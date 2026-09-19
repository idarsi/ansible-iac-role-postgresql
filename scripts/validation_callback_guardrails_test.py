"""Fast guardrails for opaque validation callback task identifiers."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path


VERIFY = (Path(__file__).parents[1] / "molecule" / "validation" / "verify.yml").read_text()


def action_identifier(play_name, host_name, task_name):
    identity = "".join(
        f"{len(value)}:{value}"
        for value in (play_name, host_name, task_name, "")
    )
    return "action-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()


def main():
    sensitive_name = "Deploy password={{ vault_database_password }}\n\x1b[31m"
    identifier = action_identifier("Guardrail play", "guardrail-host", sensitive_name)
    expected = identifier
    assert identifier == expected
    assert re.fullmatch(r"action-[0-9a-f]{64}", identifier)
    assert sensitive_name not in identifier
    assert "vault_database_password" not in identifier
    callback_source = (Path(__file__).parents[1] / "molecule" / "validation" / "callback_plugins" / "validation_capture.py").read_text()
    assert "v2_runner_on_unreachable" in callback_source
    assert '"unreachable"' in callback_source
    assert "b56dc7b8653f52ad" not in VERIFY
    assert "836e6569840204ad" not in VERIFY
    assert "Hash current validation action identities" in VERIFY
    assert "Assert expected status for every current validation action" in VERIFY
    assert "Report unreachable validation actions as deterministic failures" in VERIFY
    assert 'name: "Checking endpoint syntax"' in VERIFY
    assert 'name: "Applying malformed DCS proxy"' not in VERIFY

    # Exercise the callback through Ansible's real event flow.  The outer
    # include_role action must not replace or hide the failing inner task.
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        fixture_role = root / "validation_fixture" / "tasks"
        fixture_role.mkdir(parents=True)
        fixture_role.joinpath("main.yml").write_text(
            """---
- name: \"Checking endpoint syntax\"
  ansible.builtin.fail:
    msg: \"fixture endpoint syntax failed\"
"""
        )
        playbook = root / "fixture.yml"
        playbook.write_text(
            """---
- name: \"Reject a malformed DCS proxy\"
  hosts: localhost
  connection: local
  gather_facts: false
  tasks:
    - name: \"Applying malformed DCS proxy\"
      ansible.builtin.include_role:
        name: validation_fixture
"""
        )
        config = root / "ansible.cfg"
        config.write_text(
            """[defaults]
callbacks_enabled = validation_capture, ansible.legacy.validation_capture
callback_plugins = {callback_plugins}
roles_path = {roles_path}
""".format(
                callback_plugins=Path(__file__).parents[1] / "molecule" / "validation" / "callback_plugins",
                roles_path=root,
            )
        )
        capture = root / "validation-callback.log"
        environment = {
            **os.environ,
            "ANSIBLE_CONFIG": str(config),
            "ANSIBLE_CALLBACK_PLUGINS": str(Path(__file__).parents[1] / "molecule" / "validation" / "callback_plugins"),
            "ANSIBLE_CALLBACKS_ENABLED": "validation_capture,ansible.legacy.validation_capture",
            "ANSIBLE_LOAD_CALLBACK_PLUGINS": "true",
            "ANSIBLE_ROLES_PATH": str(root),
            "IDARSI_VALIDATION_CALLBACK_ROOT": str(root),
            "IDARSI_VALIDATION_CALLBACK_PATH": str(capture),
        }
        ansible_playbook = shutil.which("ansible-playbook") or "ansible-playbook"
        run = subprocess.run(
            [ansible_playbook, "-i", "localhost,", str(playbook)],
            cwd=Path(__file__).parents[1],
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        assert run.returncode != 0, run.stdout + run.stderr
        assert capture.is_file(), run.stdout + run.stderr
        records = [json.loads(line) for line in capture.read_text().splitlines()]
    assert len(records) == 1
    assert records[0]["status"] == "failed"
    assert records[0]["task"] == action_identifier(
        "", "localhost", "Checking endpoint syntax"
    )
    assert records[0]["task"] != action_identifier(
        "", "localhost", "Applying malformed DCS proxy"
    )


if __name__ == "__main__":
    main()
