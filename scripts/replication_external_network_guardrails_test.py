#!/usr/bin/env python3
"""Guard replication network validation against unsafe indexing and evaluation."""

import json
from pathlib import Path
import re

import yaml


ROOT = Path(__file__).parents[1]
CONVERGE = ROOT / "molecule/replication/converge.yml"
ROLE_VALIDATION = ROOT / "tasks/validate/validate_replication.yml"
RECORD_VALIDATION = ROOT / "tasks/validate/validate_replication_record.yml"
IPADDR_NAME = "Validate the configured external-network IPv4 address and subnet"
STRUCTURE_NAME = "Validate the external-network inspection structure before indexing"
COUNT_NAME = "Validate the inspected network keys and subnet count before indexing"
SUBNET_NAME = "Validate the selected subnet structure before indexing"
NON_EMPTY_GUARD_NAME = "Reject missing or empty external-network IPv4 and subnet values"
SYNTAX_GUARD_NAME = "Validate external-network IPv4 and subnet syntax before filters"
ARITHMETIC_GUARD_NAME = "Validate external-network subnet alignment before arithmetic"
PUBLISH_NAME = "Publish the validated external-network IPv4 address and subnet"
INVALID_INCLUDE_NAME = "Exercise invalid external-network values in the actual validation path"
VALID_INCLUDE_NAME = "Validate and publish the valid external-network case"


def expressions(task):
    return {" ".join(expression.split()) for expression in task["ansible.builtin.assert"]["that"]}


def task_index(tasks, name):
    return next(index for index, task in enumerate(tasks) if task.get("name") == name)


def flattened_tasks(play_tasks):
    """Expose nested task blocks as a single ordered list for structural checks."""
    flattened = []
    for task in play_tasks:
        if "block" in task:
            flattened.extend(flattened_tasks(task["block"]))
            flattened.extend(flattened_tasks(task.get("rescue", [])))
            flattened.extend(flattened_tasks(task.get("always", [])))
        else:
            flattened.append(task)
    return flattened


def valid_subnet_fixture(value):
    return isinstance(value, list) and len(value) == 1 and isinstance(value[0], dict)


def main():
    for validation_path in (ROLE_VALIDATION, RECORD_VALIDATION):
        validation_text = validation_path.read_text()
        assert "| map('ansible.utils.ipaddr'" not in validation_text, (
            f"{validation_path} must not eagerly evaluate ipaddr over possibly-null input"
        )
        assert "is not none" in validation_text and "is string" in validation_text
        assert "ansible.utils.ipaddr('network/prefix')" in validation_text

    playbook = yaml.safe_load(CONVERGE.read_text())
    tasks = flattened_tasks(playbook[0]["tasks"])
    invalid_include_index = task_index(tasks, INVALID_INCLUDE_NAME)
    valid_include_index = task_index(tasks, VALID_INCLUDE_NAME)
    assert invalid_include_index < valid_include_index

    validation_case = yaml.safe_load(
        (ROOT / "molecule/replication/validate_external_network_case.yml").read_text()
    )[0]
    validation_tasks = validation_case["block"]
    non_empty_index = task_index(validation_tasks, NON_EMPTY_GUARD_NAME)
    syntax_index = task_index(validation_tasks, SYNTAX_GUARD_NAME)
    arithmetic_index = task_index(validation_tasks, ARITHMETIC_GUARD_NAME)
    ipaddr_index = task_index(validation_tasks, IPADDR_NAME)
    assert non_empty_index < syntax_index < arithmetic_index < ipaddr_index

    guard = expressions(validation_tasks[non_empty_index])
    assert {
        "pg_replication_external_ipv4_candidate is defined",
        "pg_replication_external_ipv4_candidate is not none",
        "pg_replication_external_ipv4_candidate is string",
        "pg_replication_external_ipv4_candidate | trim | length > 0",
        "pg_replication_external_subnet_candidate is defined",
        "pg_replication_external_subnet_candidate is not none",
        "pg_replication_external_subnet_candidate is string",
        "pg_replication_external_subnet_candidate | trim | length > 0",
    } <= guard
    assert not any("ipaddr" in expression for expression in guard)
    syntax_guard = expressions(validation_tasks[syntax_index])
    assert any("is match" in expression for expression in syntax_guard)
    assert "pg_replication_external_ipv4_candidate is ansible.utils.ipv4" not in guard
    arithmetic_guard = expressions(validation_tasks[arithmetic_index])
    assert "pg_replication_external_ipv4_candidate is ansible.utils.ipv4" not in arithmetic_guard
    assert any("%" in expression and "32 -" in expression for expression in arithmetic_guard), (
        "strict subnet validation must reject host bits without normalizing through ipaddr"
    )
    assert "pg_replication_external_ipv4_candidate is ansible.utils.ipv4" in str(
        validation_tasks[task_index(validation_tasks, "Validate external-network IPv4 values before address filters")]
    )
    for task in validation_tasks[:ipaddr_index]:
        assert "ansible.utils.ipaddr" not in str(task), (
            "external-network input syntax/type guards must precede every ipaddr expression"
        )
    assert not any(
        task.get("ansible.builtin.assert")
        and (
            "canonical" in str(task).lower()
            or "network/prefix" in str(task)
            or "pg_replication_external_subnet_normalized"
            in str(task)
        )
        for task in validation_tasks[ipaddr_index + 1 :]
    ), "canonical subnet validation must not occur after an ipaddr expression"

    structure_index = task_index(tasks, STRUCTURE_NAME)
    count_index = task_index(tasks, COUNT_NAME)
    subnet_index = task_index(tasks, SUBNET_NAME)
    assert structure_index < count_index < subnet_index < invalid_include_index < valid_include_index
    assert "pg_replication_subnets_data | length == 1" in expressions(tasks[count_index])
    assert "pg_replication_subnets_data | first is mapping" in expressions(tasks[subnet_index])
    assert '"subnet" in (pg_replication_subnets_data | first)' in expressions(tasks[subnet_index])
    validation_text = (ROOT / "molecule/replication/validate_external_network_case.yml").read_text()
    assert "pg_replication_external_ipv4_candidate" in validation_text
    assert "pg_replication_external_subnet_candidate" in validation_text
    publish_index = task_index(validation_tasks, PUBLISH_NAME)
    publish_text = str(validation_tasks[publish_index]["ansible.builtin.set_fact"])
    assert "['podman']['IPAddress']" not in publish_text
    assert "[0]['subnet']" not in publish_text
    unsafe_indexing = re.compile(r"\[['\"]podman['\"]\]\[['\"]IPAddress['\"]\]|\[0\]\[['\"]subnet['\"]\]")
    assert not any(unsafe_indexing.search(str(task)) for task in validation_tasks)
    assert "omit" not in CONVERGE.read_text()
    invalid_case = yaml.safe_load(
        (ROOT / "molecule/replication/validate_external_network_invalid_case.yml").read_text()
    )
    assert invalid_case[0]["ansible.builtin.set_fact"] == {
        "pg_shared_failure_messages": [], "pg_shared_failure_results": []
    }
    invalid_case = invalid_case[1]
    assert invalid_case["rescue"]
    assert all(
        "ansible.builtin.set_fact" not in str(task)
        or "pg_replication_invalid_external_network_outcomes" in str(task)
        for task in invalid_case["rescue"]
    )
    assert all("ansible.builtin.set_fact" not in str(task) for task in invalid_case["block"])
    assert "pg_replication_external_case" in str(tasks[invalid_include_index]["vars"])
    fixtures = json.loads((ROOT / "scripts/fixtures/replication_external_network_subnets.json").read_text())
    assert valid_subnet_fixture(fixtures["valid"])
    for name in ("zero", "multiple"):
        assert not valid_subnet_fixture(fixtures[name]), name

    invalid_values = json.loads(
        (ROOT / "scripts/fixtures/replication_external_network_invalid_values.json").read_text()
    )
    assert invalid_values
    assert {
        "missing_ipv4",
        "null_ipv4",
        "empty_ipv4",
        "missing_subnet",
        "null_subnet",
        "empty_subnet",
    } <= invalid_values.keys()
    assert all(
        isinstance(case.get("published_facts"), dict)
        and case["published_facts"] == {}
        for case in invalid_values.values()
    )
    assert all(case.get("expected_message") for case in invalid_values.values())
    assert invalid_values["invalid_subnet"]["subnets"][0]["subnet"] == "10.88.0.2/16"
    assert invalid_values["invalid_subnet"]["expected_message"] == "canonical IPv4 CIDR"
    converge_text = CONVERGE.read_text()
    assert "replication_external_network_invalid_values.json" in converge_text
    assert "pg_replication_invalid_external_network_outcomes" in converge_text
    assert "expected_published_facts" in converge_text
    assert "published_facts == pg_replication_invalid_outcome.expected_published_facts" in converge_text
    invalid_case_text = (ROOT / "molecule/replication/validate_external_network_invalid_case.yml").read_text()
    assert "pg_replication_external_ipv4 is defined" in invalid_case_text
    assert "pg_replication_external_subnet is defined" in invalid_case_text
    assert "Fail if the invalid external-network case was accepted" in (
        ROOT / "molecule/replication/validate_external_network_invalid_case.yml"
    ).read_text()
    print("replication external-network ordering, indexing, and subnet-count guardrails: PASS")


if __name__ == "__main__":
    main()
