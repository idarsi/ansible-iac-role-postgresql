#!/usr/bin/env python3
"""Check that endpoint normalization publishes only validated output."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
TASKS = ROOT / "tasks/endpoint_normalize.yml"
CONTRACT = ROOT / "tasks/validate/test_endpoint_contract.yml"


def main():
    tasks = yaml.safe_load(TASKS.read_text())
    set_fact_indexes = [
        index for index, task in enumerate(tasks) if "ansible.builtin.set_fact" in task
    ]
    assert len(set_fact_indexes) == 1
    assert tasks[set_fact_indexes[0]]["name"] == "Publishing canonical endpoint model after validation"
    assert set_fact_indexes[0] == len(tasks) - 2
    assert all("ansible.builtin.set_fact" not in str(task) for task in tasks[: set_fact_indexes[0]])
    assert not any(task.get("ansible.builtin.include_tasks") == "host_port.yml" for task in tasks)

    contract_tasks = yaml.safe_load(CONTRACT.read_text())
    normalize = contract_tasks[0]
    assert normalize.get("ansible.builtin.include_tasks") == "../endpoint_normalize.yml"
    assert normalize["vars"]["pg_endpoint_normalize_result_fact"] == "pg_endpoint_contract_model"
    assert contract_tasks[1]["name"] == "Check endpoint contract"
    assertions = contract_tasks[1]["ansible.builtin.assert"]["that"]
    assert any("canonical_host" in expression for expression in assertions)
    assert any("san_identities" in expression for expression in assertions)
    assert all("pg_replication" not in str(task) for task in contract_tasks)
    print("endpoint publish-after-validation and endpoint contract guardrails: PASS")


if __name__ == "__main__":
    main()
