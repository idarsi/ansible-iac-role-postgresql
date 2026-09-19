#!/usr/bin/env python3
"""Contract checks for Patroni check-mode normalization and certificate safety."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_tasks(path):
    return yaml.safe_load((ROOT / path).read_text())


def find_task(tasks, predicate, description):
    matches = [task for task in tasks if predicate(task)]
    assert len(matches) == 1, f"expected exactly one {description} task"
    return matches[0]


def main():
    patroni = load_tasks("tasks/patroni_present.yml")
    converge = load_tasks("tasks/cluster_certificates_converge.yml")
    apply = load_tasks("tasks/cluster_certificates_apply.yml")
    validation = load_tasks("tasks/validate/validate_cluster.yml")

    normalize_task = find_task(
        patroni,
        lambda task: "pg_patroni_endpoint_projection" in task.get(
            "ansible.builtin.set_fact", {}
        ),
        "Patroni endpoint projection",
    )
    lookup_task = find_task(
        patroni,
        lambda task: "pg_patroni_restapi_canonical_endpoint_models"
        in task.get("ansible.builtin.set_fact", {}),
        "canonical Patroni REST endpoint model lookup",
    )
    normalize = patroni.index(normalize_task)
    lookup = patroni.index(lookup_task)
    assert normalize < lookup, "check mode must build endpoint models before lookup"
    provenance_task = find_task(
        patroni,
        lambda task: "pg_patroni_endpoint_projection"
        in str(task.get("ansible.builtin.assert", {}))
        and "pg_preflight_patroni_endpoint_models" in str(task),
        "Patroni endpoint projection provenance",
    )
    provenance = patroni.index(provenance_task)
    assert normalize < provenance < lookup, "check mode must publish the preflight endpoint projection before lookup"
    assert "pg_patroni_endpoint_projection" in patroni[normalize]["ansible.builtin.set_fact"]
    apply_text = str(apply)
    assert "pg_preflight_patroni_endpoint_models_by_key" in apply_text, (
        "certificate apply must consume the preflight Patroni endpoint index"
    )
    assert "pg_cluster_certificate_patroni_endpoint_models" in apply_text
    assert "pg_preflight_patroni_endpoint_models" in apply_text
    assert "pg_preflight_etcd_endpoint_models" in apply_text
    assert not any(
        "Initializing canonical" in task.get("name", "")
        or "Publishing canonical" in task.get("name", "")
        or "pg_cluster_etcd_member_endpoint_models: []" in str(task)
        for task in apply
    ), "apply mode must not reset or republish the etcd endpoint index"
    assert not any("pg_patroni_endpoint_models_derived" in str(task) for task in patroni)
    assert not any(
        "cluster_patroni_endpoint_normalize.yml" in str(task)
        for task in apply
    ), "apply mode must not republish canonical endpoint models"
    assert not any(
        "pg_patroni_endpoint_models_derived" in str(task)
        and "pg_cluster_certificate_patroni_endpoint_models" not in str(task)
        for task in apply
    ), "apply mode must not reset or republish the canonical endpoint index"
    assert any(
        task.get("ansible.builtin.include_tasks") == "cluster_certificates_normalize.yml"
        for task in patroni[:normalize]
    ), "endpoint preflight must use the pure certificate normalization path"

    assert converge[0]["when"] == "ansible_check_mode | bool"
    assert converge[1]["when"] == "not (ansible_check_mode | bool)"
    assert "cluster_certificates_apply.yml" in converge[1]["ansible.builtin.include_tasks"]

    duplicate = find_task(
        validation,
        lambda task: "unique" in str(
            task.get("ansible.builtin.assert", {}).get("that", [])
        )
        and "inventory hosts" in str(task),
        "duplicate cluster member validation",
    )
    assert "unique" in duplicate["ansible.builtin.assert"]["that"][0]

    rendered_checks = [task for task in patroni if "rendered Patroni" in task.get("name", "")]
    assert rendered_checks, "rendered configuration contract disappeared"
    assert all(
        "not (ansible_check_mode | bool)" in str(task.get("when", ""))
        for task in rendered_checks
    )


if __name__ == "__main__":
    main()
    print("Patroni check-mode contract: PASS")
