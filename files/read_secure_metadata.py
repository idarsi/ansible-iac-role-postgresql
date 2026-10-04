#!/usr/bin/env python3
"""Read a run-scoped file without following replacement symlinks."""

import argparse
import json
import os
import stat


def check_directory_descriptor(directory_stat: os.stat_result, expected_uid: int) -> None:
    """Reject non-directories, unexpected owners, and writable ancestors."""
    mode = stat.S_IMODE(directory_stat.st_mode)
    # A root-owned sticky directory such as /tmp is a safe system traversal
    # boundary; files below it are still checked descriptor-safely.
    sticky_system_directory = (
        directory_stat.st_uid == 0
        and mode & stat.S_ISVTX
        and mode & 0o022 == 0o022
    )
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise ValueError("metadata ancestor is not a directory")
    if directory_stat.st_uid not in (0, expected_uid) and not sticky_system_directory:
        raise ValueError("metadata ancestor is not owned by the expected uid")
    if mode & 0o022 and not sticky_system_directory:
        raise ValueError("metadata ancestor is group/other writable")


def read_metadata(path: str, expected_uid: int = 0, expected_mode: int = 0o600,
                  raw: bool = False) -> object:
    if not os.path.isabs(path):
        raise ValueError("metadata path must be absolute")
    components = [component for component in path.split(os.sep) if component]
    if not components:
        raise ValueError("metadata path must name a file")
    # Open every ancestor by descriptor.  A path-wide lstat does not prevent an
    # attacker replacing an already-checked ancestor before the final open.
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent_fd = os.open(os.sep, flags)
    try:
        check_directory_descriptor(os.fstat(parent_fd), expected_uid)
        for component in components[:-1]:
            next_fd = os.open(component, flags, dir_fd=parent_fd)
            check_directory_descriptor(os.fstat(next_fd), expected_uid)
            os.close(parent_fd)
            parent_fd = next_fd
        name = components[-1]
        parent_stat = os.fstat(parent_fd)
        check_directory_descriptor(parent_stat, expected_uid)
        before = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(before.st_mode) or before.st_uid != expected_uid:
            raise ValueError("metadata is not an owned regular file")
        if expected_mode == 0o600 and (before.st_mode & 0o777) != 0o600:
            raise ValueError("metadata must have mode 0600")
        if expected_mode != 0o600 and (before.st_mode & 0o777) != expected_mode:
            raise ValueError("metadata has unexpected mode")
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
        try:
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_mode, before.st_uid) != (
                after.st_dev,
                after.st_ino,
                after.st_mode,
                after.st_uid,
            ):
                raise ValueError("metadata changed while it was being opened")
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                fd = None
                return stream.read() if raw else json.load(stream)
        except Exception:
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass
            raise
    finally:
        os.close(parent_fd)


parser = argparse.ArgumentParser()
parser.add_argument("path")
parser.add_argument("--uid", type=int, default=0)
parser.add_argument("--mode", type=lambda value: int(value, 8), default=0o600)
parser.add_argument("--raw", action="store_true")
args = parser.parse_args()
value = read_metadata(args.path, args.uid, args.mode, args.raw)
print(value if args.raw else json.dumps(value, separators=(",", ":")), end="" if args.raw else "\n")
