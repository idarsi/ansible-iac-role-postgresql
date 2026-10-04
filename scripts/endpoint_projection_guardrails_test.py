#!/usr/bin/env python3
"""Guard the single-owner endpoint projection architecture."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def task_text(path: Path) -> str:
    return path.read_text()


def main() -> None:
    inventory = task_text(ROOT / "tasks/validate/validate_inventory.yml")
    projection = task_text(ROOT / "tasks/validate/publish_etcd_endpoint_index.yml")
    patroni = task_text(ROOT / "tasks/patroni_present.yml")
    validation = "\n".join(
        path.read_text()
        for path in (ROOT / "tasks/validate").glob("*.yml")
    )

    endpoint_index = inventory + projection
    assert "cluster_model.record.dcs.etcd.members_normalized" in endpoint_index
    assert "cluster_model.record.dcs.etcd.members | default([])" not in endpoint_index
    assert "member.client_endpoint_model" in endpoint_index
    assert "canonical_endpoint" in endpoint_index
    assert "host_is_ipv6" in endpoint_index
    assert "san_identities" in endpoint_index

    patroni_tasks = yaml.safe_load(patroni)
    assert not any(
        task.get("ansible.builtin.include_tasks") == "endpoint_normalize.yml"
        for task in patroni_tasks
    )
    assert "pg_patroni_endpoint_projection" in patroni
    assert "pg_patroni_restapi_canonical_endpoint_model" in patroni

    assert validation.count("pg_validation_etcd_members_normalized: []") == 1
    print("canonical endpoint projection, Patroni normalization, and reset guardrails: PASS")


if __name__ == "__main__":
    main()
