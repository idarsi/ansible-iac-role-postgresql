#!/usr/bin/env python3
"""Check managed etcd metadata ownership and path guardrails."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
TASKS = ROOT / "tasks/etcd_present.yml"


def tasks(value):
    if isinstance(value, list):
        for child in value:
            yield from tasks(child)
    elif isinstance(value, dict):
        if any(key.startswith("ansible.builtin.") for key in value):
            yield value
        for key in ("block", "rescue", "always"):
            if key in value:
                yield from tasks(value[key])


def main():
    source = TASKS.read_text()
    parsed = list(tasks(yaml.safe_load(source)))
    names = [str(task.get("name", "")) for task in parsed]
    path_gate = names.index("Rejecting unsafe managed etcd metadata paths before inspection")
    data_stat = names.index("Checking existing managed etcd data directory")
    metadata_stat = names.index("Checking managed etcd metadata directory and marker")
    assert path_gate < data_stat < metadata_stat

    assert "pg_etcd_metadata_marker_path | dirname == pg_etcd_metadata_directory ~ '/' ~ pg_etcd_metadata_identity" in source
    assert "pg_etcd_metadata_marker_path == pg_etcd_metadata_directory ~ '/' ~ pg_etcd_metadata_identity ~ '/' ~ pg_etcd_data_directory_marker" in source
    assert "not (item.stat.islnk | default(false))" in source
    assert "^0[0-7][0145][0145]$" in source
    # The task must invoke the absolute tool path; retain the physical-path
    # guard (-P) instead of accepting a PATH-selected getfacl binary.
    assert '"/usr/bin/getfacl", "-P"' in source
    assert "pg_etcd_data_directory_stat.stat.pw_name | default('') == 'etcd'" in source
    assert "pg_etcd_data_directory_stat.stat.mode | default('') == '0700'" in source
    assert "Capturing managed etcd data directory identity" in names
    assert "pg_etcd_data_directory_final_stat.stat.dev | string ==" in source
    assert "pg_etcd_data_directory_final_stat.stat.inode | string ==" in source
    assert "not (pg_etcd_data_directory_stat.stat.islnk | default(false))" in source
    assert "pg_etcd_data_path != pg_etcd_metadata_directory" in source
    assert "not pg_etcd_data_path.startswith(pg_etcd_metadata_directory ~ '/')" in source

    external_paths = (ROOT / "tasks/validate/validate_external_path_ancestors.yml").read_text()
    assert "namespace(paths=['/'])" in external_paths
    assert "components | length - 1" in external_paths
    assert "pg_external_path_ancestor_paths | intersect(pg_external_path_paths) | length == 0" in external_paths

    # namei rc=1 is permitted only when the matching stat succeeded and
    # explicitly proved that the destination is absent.
    assert "rc in [0, 1]" not in source
    assert "item.failed | default(false) | bool is false" in source
    assert "pg_etcd_tls_destination_stats.results" in source
    assert ".failed |" in source and "default(false) | bool) is false" in source
    assert ".stat.exists |" in source and "bool) is false" in source

    acl_index = names.index("Inspecting managed etcd metadata marker ACL")
    acl_reject_index = names.index("Rejecting unsafe managed etcd metadata marker ACL")
    assert metadata_stat < acl_index < acl_reject_index
    assert "^default:" in source
    assert "^user:[^:]+:" in source
    assert "^group:[^:]+:" in source
    assert "Rejecting a symlinked managed etcd metadata marker" in names

    # The four focused lifecycle/attack outcomes must remain explicit.
    assert "not pg_etcd_data_directory_stat.stat.exists or pg_etcd_metadata_stats.results[2].stat.exists" in source
    assert "when: not pg_etcd_metadata_stats.results[2].stat.exists" in source
    print("managed etcd metadata path, lifecycle, ancestor, and ACL guardrails: PASS")


if __name__ == "__main__":
    main()
