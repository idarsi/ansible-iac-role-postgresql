#!/usr/bin/env python3
"""Exercise the managed-etcd filesystem contract in an isolated fixture.

This is deliberately a controller-side test.  It never resolves, changes, or
creates the role's production accounts and never needs privilege escalation.
"""

import os
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
TASKS = ROOT / "tasks/etcd_present.yml"
DEFAULTS = ROOT / "defaults/main.yml"


def task_records(value):
    """Yield module task mappings, including tasks nested in blocks."""
    if isinstance(value, list):
        for child in value:
            yield from task_records(child)
    elif isinstance(value, dict):
        if any(key.startswith("ansible.builtin.") for key in value):
            yield value
        for key in ("block", "rescue", "always"):
            yield from task_records(value.get(key, []))


def production_contract():
    """Read and verify the path/identity expressions implemented by the role."""
    defaults = yaml.safe_load(DEFAULTS.read_text())
    source = TASKS.read_text()
    parsed_tasks = list(task_records(yaml.safe_load(source)))
    by_name = {str(task.get("name", "")): task for task in parsed_tasks}
    required_defaults = {
        "pg_etcd_data_directory": "/var/lib/etcd/data",
        "pg_etcd_data_directory_root": "/var/lib/etcd",
        "pg_etcd_metadata_directory": "/var/lib/etcd/.idarsi-managed",
        "pg_etcd_data_directory_marker": "managed-etcd",
    }
    assert {key: defaults.get(key) for key in required_defaults} == required_defaults

    def args(task_name):
        task = by_name.get(task_name)
        assert task is not None, f"managed etcd contract task disappeared: {task_name}"
        return task[next(key for key in task if key.startswith("ansible.builtin."))]

    metadata_args = args("Ensuring managed etcd metadata directories exist")
    data_args = args("Ensuring managed etcd data directory exists when absent")
    marker_args = args("Writing managed etcd metadata marker")
    assert (metadata_args["owner"], metadata_args["group"], metadata_args["mode"]) == (
        "root", "root", "0700"
    )
    assert (data_args["owner"], data_args["group"], data_args["mode"]) == (
        "etcd", "etcd", "0700"
    )
    assert (marker_args["owner"], marker_args["group"], marker_args["mode"]) == (
        "root", "root", "0600"
    )

    # Keep this test coupled to the expressions, not merely to duplicated defaults.
    assert "pg_etcd_data_directory_root, pg_etcd_data_path | dirname" in source
    assert "pg_etcd_config.data_dir | default(pg_etcd_data_directory)" in source
    assert "{{ pg_etcd_metadata_directory }}/{{ pg_version }}-{{ pg_cluster.name }}/{{ pg_etcd_data_directory_marker }}" in source
    assert "pg_etcd_metadata_marker_path == pg_etcd_metadata_directory ~ '/' ~ pg_etcd_metadata_identity ~ '/' ~ pg_etcd_data_directory_marker" in source
    assert "^0[0-7][0145][0145]$" in source
    return {
        **required_defaults,
        "data_mode": int(data_args["mode"], 8),
        "metadata_mode": int(metadata_args["mode"], 8),
        "marker_mode": int(marker_args["mode"], 8),
        "data_owner": data_args["owner"],
        "data_group": data_args["group"],
        "metadata_owner": metadata_args["owner"],
        "metadata_group": metadata_args["group"],
    }


def acl(path: Path) -> str:
    result = subprocess.run(
        ["getfacl", "-P", "--absolute-names", "--", str(path)],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def has_extended_acl(output: str) -> bool:
    return any(
        line.startswith(("default:", "user:", "group:"))
        and not line.startswith(("user::", "group::"))
        for line in output.splitlines()
    )


def secure(path, marker, value, data_identity, metadata_identity, identity=None, acl_check=True):
    try:
        data = path.lstat()
    except FileNotFoundError:
        return True
    if not stat.S_ISDIR(data.st_mode) or stat.S_ISLNK(data.st_mode):
        return False
    if (data.st_mode & 0o777, data.st_uid, data.st_gid) != (
        0o700, *data_identity
    ):
        return False
    if identity is not None and (data.st_dev, data.st_ino) != identity:
        return False
    if acl_check and has_extended_acl(acl(path)):
        return False
    for ancestor in (path.parent, marker.parent, marker.parent.parent):
        ancestor_stat = ancestor.lstat()
        if (
            not stat.S_ISDIR(ancestor_stat.st_mode)
            or stat.S_ISLNK(ancestor_stat.st_mode)
            or (ancestor_stat.st_mode & 0o777, ancestor_stat.st_uid, ancestor_stat.st_gid)
            != (0o700, *metadata_identity)
        ):
            return False
    if marker.is_symlink() or not marker.is_file():
        return False
    marker_stat = marker.lstat()
    return (
        (marker_stat.st_mode & 0o777, marker_stat.st_uid, marker_stat.st_gid)
        == (0o600, *metadata_identity)
        and marker.read_text() == value
        and (not acl_check or not has_extended_acl(acl(marker)))
    )


def data_path_allowed(data, metadata):
    return data != metadata and not data.startswith(metadata + "/")


def main():
    contract = production_contract()
    # Numeric identities are explicit fixture expectations.  They describe the
    # invoking user only; the production names above are verified independently.
    fixture_uid, fixture_gid = os.getuid(), os.getgid()
    data_identity = (fixture_uid, fixture_gid)
    metadata_identity = (fixture_uid, fixture_gid)
    acl_available = bool(
        subprocess.run(["sh", "-c", "command -v getfacl && command -v setfacl"], check=False,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
    )
    if not acl_available:
        print("SKIP: getfacl/setfacl unavailable; ACL mutation checks are optional")

    value = "managed-etcd:17:test\n"
    with tempfile.TemporaryDirectory(prefix="etcd-lifecycle-") as temporary:
        root = Path(temporary)
        data = root / "var/lib/etcd/data"
        metadata = root / "var/lib/etcd/.idarsi-managed/17-test"
        marker = metadata / contract["pg_etcd_data_directory_marker"]
        assert secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
        data.mkdir(mode=contract["data_mode"], parents=True)
        metadata.mkdir(mode=contract["metadata_mode"], parents=True)
        marker.write_text(value)
        for directory in (root, root / "var", root / "var/lib", root / "var/lib/etcd", data, metadata.parent, metadata):
            os.chmod(directory, contract["data_mode"] if directory == data else contract["metadata_mode"])
        os.chmod(marker, contract["marker_mode"])
        assert secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)

        os.chmod(data, 0o720)
        assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
        os.chmod(data, contract["data_mode"])
        assert not secure(data, marker, value, (fixture_uid + 1, fixture_gid), metadata_identity, acl_check=acl_available)
        assert not secure(data, marker, value, (fixture_uid, fixture_gid + 1), metadata_identity, acl_check=acl_available)
        alternate_groups = [group for group in os.getgroups() if group != fixture_gid]
        if alternate_groups:
            os.chown(data, fixture_uid, alternate_groups[0])
            assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
            os.chown(data, fixture_uid, fixture_gid)
        else:
            print("SKIP: no alternate supplementary group; actual wrong-group mutation unavailable")
        os.chmod(data.parent, 0o722)
        assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
        os.chmod(data.parent, contract["metadata_mode"])

        marker.unlink()
        marker.symlink_to(root / "replacement")
        (root / "replacement").write_text(value)
        assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
        marker.unlink()
        marker.write_text("tampered\n")
        assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
        marker.write_text(value)

        if acl_available:
            assert subprocess.run(["setfacl", "-m", "u:65534:r-x", str(data)], check=False).returncode == 0
            assert not secure(data, marker, value, data_identity, metadata_identity)
            subprocess.run(["setfacl", "-b", str(data)], check=True)
            assert subprocess.run(["setfacl", "-d", "-m", "u::rwx", str(data)], check=False).returncode == 0
            assert not secure(data, marker, value, data_identity, metadata_identity)
            subprocess.run(["setfacl", "-k", str(data)], check=True)

        assert data_path_allowed("/var/lib/etcd/data", "/var/lib/etcd/.idarsi-managed")
        assert not data_path_allowed("/var/lib/etcd/.idarsi-managed", "/var/lib/etcd/.idarsi-managed")
        assert not data_path_allowed("/var/lib/etcd/.idarsi-managed/nested", "/var/lib/etcd/.idarsi-managed")
        original_identity = (data.stat().st_dev, data.stat().st_ino)
        replacement_dir = root / "data-replacement"
        replacement_dir.mkdir(mode=0o700)
        data.rename(root / "data-real")
        replacement_dir.rename(data)
        assert not secure(data, marker, value, data_identity, metadata_identity, original_identity, acl_available)
        data.rename(root / "data-replacement")
        data.symlink_to(root / "data-real")
        assert not secure(data, marker, value, data_identity, metadata_identity, acl_check=acl_available)
    print("managed etcd data lifecycle and filesystem guardrails: PASS")


if __name__ == "__main__":
    main()
