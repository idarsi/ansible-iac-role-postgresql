#!/usr/bin/env python3
"""Guard native-list normalization for external path ancestor inspection."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "tasks/validate/validate_external_path_ancestors.yml").read_text()


def main():
    assert "pg_external_path_paths is string" in SOURCE
    assert "pg_external_path_paths | default([], true) | list" in SOURCE
    assert "ns.paths | to_json | from_json" in SOURCE
    assert "pg_external_path_ancestor_paths is not string" in SOURCE
    assert "pg_external_path_acl_paths is not string" in SOURCE
    assert "pg_external_path_acl_paths | select('string')" in SOURCE
    assert "pg_external_path_acl_paths }}" in SOURCE
    guard = SOURCE.index('name: "Rejecting unsafe external TLS path input shape"')
    first_consumer = SOURCE.index('loop: "{{ pg_external_path_ancestor_paths }}"')
    assert guard < first_consumer, "ancestor consumers must follow the input guard"
    print("external path ancestor native-list guard: PASS")


if __name__ == "__main__":
    main()
