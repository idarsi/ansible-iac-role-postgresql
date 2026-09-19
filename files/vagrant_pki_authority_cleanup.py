#!/usr/bin/env python3
"""Remove disposable Vagrant PKI authority material and sync its parent."""
import os
import stat
import sys
from pathlib import Path


def sync(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def checked_tree(authority, guests):
    if not authority.is_absolute() or authority == Path("/"):
        raise SystemExit("unsafe authority path")
    if authority.is_symlink() or not authority.is_dir():
        raise SystemExit("authority staging directory is not a real directory")
    authority_info = authority.lstat()
    if (authority_info.st_uid != 0 or authority_info.st_gid != 0
            or stat.S_IMODE(authority_info.st_mode) != 0o700):
        raise SystemExit("unsafe authority staging ownership or mode")
    expected = {"ca.key", "ca.crt", "ca.srl", "client.ext", "guests"}
    if {entry.name for entry in authority.iterdir()} != expected:
        raise SystemExit("unexpected authority staging entry")
    for entry in authority.iterdir():
        info = entry.lstat()
        expected_directory = entry.name == "guests"
        valid_type = stat.S_ISDIR(info.st_mode) if expected_directory else stat.S_ISREG(info.st_mode)
        if (not valid_type or info.st_uid != 0 or info.st_gid != 0
                or entry.is_symlink()):
            raise SystemExit(f"unsafe authority staging entry: {entry}")
    guest_root = authority / "guests"
    guest_root_info = guest_root.lstat()
    if (not guest_root.is_dir() or guest_root.is_symlink()
            or guest_root_info.st_uid != 0 or guest_root_info.st_gid != 0
            or stat.S_IMODE(guest_root_info.st_mode) != 0o700):
        raise SystemExit("guest authority tree is not a real directory")
    if {entry.name for entry in guest_root.iterdir()} != set(guests):
        raise SystemExit("unexpected guest authority entry")
    for guest in guests:
        directory = guest_root / guest
        directory_info = directory.lstat()
        if (directory.is_symlink() or not directory.is_dir()
                or directory_info.st_uid != 0 or directory_info.st_gid != 0
                or stat.S_IMODE(directory_info.st_mode) != 0o700):
            raise SystemExit(f"unsafe guest authority directory: {directory}")
        names = {"leaf.ext", "client.key", "client.csr", "client.crt",
                 "peer.key", "peer.csr", "peer.crt"}
        if {entry.name for entry in directory.iterdir()} != names:
            raise SystemExit(f"incomplete guest authority tree: {directory}")
        for entry in directory.iterdir():
            info = entry.lstat()
            if (entry.is_symlink() or not entry.is_file() or info.st_uid != 0
                    or info.st_gid != 0):
                raise SystemExit(f"unsafe guest authority entry: {entry}")


authority = Path(sys.argv[1])
guests = sys.argv[2:]
if not guests or len(set(guests)) != len(guests):
    raise SystemExit("guest allowlist is required and must be unique")
checked_tree(authority, guests)
for child in authority.iterdir():
    if child.name == "guests":
        for guest in guests:
            for leaf in (child / guest).iterdir():
                leaf.unlink()
            (child / guest).rmdir()
        child.rmdir()
    else:
        child.unlink()
sync(authority)
authority.rmdir()
sync(authority.parent)
