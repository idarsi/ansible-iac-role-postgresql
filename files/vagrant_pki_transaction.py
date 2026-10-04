#!/usr/bin/env python3
"""Fail-closed, journalled PKI replacement for the disposable Vagrant guests.

This is deliberately a small privileged helper.  It protects against symlink
redirection and interrupted local operations, but cannot prevent a privileged
attacker racing between checks, nor make a filesystem immune to sudden power
loss.
"""
import argparse
import grp
import hashlib
import json
import os
import stat
import sys
from pathlib import Path


def identity(path, expected_type=None):
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or (expected_type == "file" and not stat.S_ISREG(info.st_mode)):
        raise RuntimeError(f"unsafe path: {path}")
    if expected_type == "dir" and not stat.S_ISDIR(info.st_mode):
        raise RuntimeError(f"unsafe path: {path}")
    return {"dev": info.st_dev, "ino": info.st_ino, "uid": info.st_uid,
            "gid": info.st_gid, "mode": stat.S_IMODE(info.st_mode)}


def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def digest(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"unsafe path: {path}")
        value = hashlib.sha256()
        while block := os.read(fd, 131072):
            value.update(block)
        return value.hexdigest()
    finally:
        os.close(fd)


def read_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise RuntimeError(f"unsafe path: {path}")
        chunks = []
        while block := os.read(fd, 131072):
            chunks.append(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def write_new(path, data, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        view = memoryview(data)
        while view:
            view = view[os.write(fd, view):]
        os.fchmod(fd, mode)
        os.fsync(fd)
    finally:
        os.close(fd)
    identity(path, "file")
    sync_dir(path.parent)
    return digest(path)


def replace_journal(path, data):
    """Replace the journal as a synced file, then sync its parent directory."""
    temporary = path.with_name(f".{path.name}.new")
    if os.path.lexists(temporary):
        raise RuntimeError(f"unexpected journal temporary: {temporary}")
    write_new(temporary, data, 0o600)
    os.replace(temporary, path)
    sync_dir(path.parent)
    return identity(path, "file"), digest(path)


def group_gid(name):
    try:
        return grp.getgrnam(name).gr_gid
    except KeyError:
        if os.environ.get("VAGRANT_PKI_TRANSACTION_TEST_MODE") == "1":
            return os.getgid()
        raise


def checked_unlink(path, expected):
    if identity(path, "file") != expected:
        raise RuntimeError(f"identity changed; preserving evidence: {path}")
    os.unlink(path)
    sync_dir(path.parent)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--staging", required=True)
    parser.add_argument("--transaction", required=True)
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--inject", choices=("copy", "rename", "marker", "cleanup",
                                              "backed_up", "installed", "committed", "rollback"))
    args = parser.parse_args()
    root, staging = Path(args.root), Path(args.staging)
    identity(root, "dir")
    identity(staging, "dir")
    marker = root / f".client-marker-{args.transaction}"
    manifest = root / f".client-manifest-{args.transaction}"
    journal = root / f".client-journal-{args.transaction}"
    backup = root / f".client-backup-{args.transaction}"
    names = (("ca.crt", "ca.crt", "tlsreaders"),
             ("etcd-peer.crt", "peer.crt", "etcd"),
             ("etcd-peer.key", "peer.key", "etcd"),
             ("client/etcd-client.crt", "client.crt", "tlsreaders"),
             ("client/etcd-client.key", "client.key", "tlsreaders"))
    destinations = [(root / dst, staging / src, group) for dst, src, group in names]
    created = []
    installed = {}
    journal_hash = manifest_hash = marker_hash = None
    journal_identity = None
    journal_data = None

    def journal_phase(phase):
        nonlocal journal_hash, journal_identity, journal_data
        journal_data["phase"] = phase
        journal_identity, journal_hash = replace_journal(
            journal, (json.dumps(journal_data, sort_keys=True) + "\n").encode())
        if args.inject == phase:
            raise RuntimeError(f"{phase} interruption injection")
    try:
        records = []
        for destination, source, _ in destinations:
            identity(destination.parent, "dir")
            identity(source, "file")
            old = None
            if os.path.lexists(destination):
                old_identity = identity(destination, "file")
                old = {"identity": old_identity, "digest": digest(destination)}
            records.append({"path": str(destination), "old": old})
        manifest_hash = write_new(manifest, (json.dumps(records, sort_keys=True) + "\n").encode())
        created.append((manifest, identity(manifest, "file")))
        marker_data = {"transaction": args.transaction, "manifest": manifest_hash,
                       "phase": "prepared", "records": records}
        marker_hash = write_new(marker, (json.dumps(marker_data, sort_keys=True) + "\n").encode())
        created.append((marker, identity(marker, "file")))
        journal_data = {
            "transaction": args.transaction,
            "phase": "prepared",
            "phases": ["prepared", "backed_up", "installed", "committed"],
            "records": records,
        }
        journal_hash = write_new(journal, (json.dumps(journal_data, sort_keys=True) + "\n").encode())
        created.append((journal, identity(journal, "file")))
        if args.inject == "marker":
            checked_unlink(marker, created[1][1])
            write_new(marker, b"tampered\n")
            raise RuntimeError("marker tamper injection")
        os.mkdir(backup, 0o700)
        sync_dir(root)
        for destination, _, _ in destinations:
            if os.path.lexists(destination):
                identity(destination, "file")
                backup_file = backup / destination.name
                os.link(destination, backup_file, follow_symlinks=False)
                sync_dir(backup)
        journal_identity = identity(journal, "file")
        journal_phase("backed_up")
        for index, (destination, source, group) in enumerate(destinations):
            identity(destination.parent, "dir")
            if os.path.lexists(destination):
                identity(destination, "file")
            temporary = root / f".client-new-{args.transaction}-{index}"
            write_new(temporary, read_bytes(source), 0o640)
            owner = 0 if os.environ.get("VAGRANT_PKI_TRANSACTION_TEST_MODE") != "1" else os.getuid()
            os.chown(temporary, owner, group_gid(group), follow_symlinks=False)
            fd = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            fd = os.open(temporary, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)
            if args.inject == "copy" and index == 1:
                raise RuntimeError("partial copy injection")
            os.replace(temporary, destination)
            sync_dir(destination.parent)
            identity(destination, "file")
            installed[str(destination)] = digest(destination)
            if args.inject == "rename" and index == 1:
                raise RuntimeError("rename injection")
        journal_phase("installed")
        if args.inject == "cleanup":
            checked_unlink(marker, created[1][1])
            write_new(marker, b"replacement\n")
            raise RuntimeError("cleanup replacement injection")
        journal_phase("committed")
        for path, expected in created:
            checked_unlink(path, expected)
        for item in backup.iterdir():
            checked_unlink(item, identity(item, "file"))
        os.rmdir(backup)
        sync_dir(root)
        for item in staging.iterdir():
            checked_unlink(item, identity(item, "file"))
        os.rmdir(staging)
        sync_dir(root)
    except Exception:
        # Never clean up when any journal/marker identity or digest is suspect.
        try:
            if (journal_hash and identity(journal, "file") == journal_identity and digest(journal) == journal_hash
                    and identity(marker, "file") == created[1][1] and digest(marker) == marker_hash
                    and identity(manifest, "file") == created[0][1] and digest(manifest) == manifest_hash):
                journal_phase("rollback")
                created[2] = (journal, journal_identity)
                for destination, _, _ in destinations:
                    old = backup / destination.name
                    if os.path.lexists(old):
                        identity(old, "file")
                        os.replace(old, destination)
                        sync_dir(destination.parent)
                    elif str(destination) in installed and os.path.lexists(destination):
                        if digest(destination) != installed[str(destination)]:
                            raise RuntimeError("replacement changed; preserving evidence")
                        os.unlink(destination)
                        sync_dir(destination.parent)
                for path, expected in reversed(created):
                    checked_unlink(path, expected)
        except Exception:
            pass
        raise
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
