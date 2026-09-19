#!/usr/bin/env python3
"""Guard the Podman inspect JSON and Ansible registered-loop contracts."""

import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).parents[1]

CONTAINER_ASSERT = "Require an image reference in every inspected replication container"
IMAGE_ASSERT = "Require amd64 Rocky replication images and exact package"
CONTAINER_INSPECT = "Inspect replication image provenance and architecture"
IMAGE_INSPECT = "Inspect the image referenced by each replication container"
NETWORK_ASSERT = "Require the exact default Podman network mapping and IPv4 value"
UNICAST_ASSERT = "Require a unicast IPv4 address on the default Podman network"


def registered_result_contract(result):
    """Return the command-result fields used by the replication assertions."""
    for field in ("rc", "stdout", "stderr"):
        assert field in result
    assert result["rc"] == 0
    assert isinstance(result["stdout"], str)
    assert isinstance(result["stderr"], str)
    return result


def task_by_name(tasks, name):
    return next(task for task in tasks if task.get("name") == name)


def inspect_task_contract(tasks, name, register, loop_var, command):
    """Bind the assertions to the exact registered command-loop producers."""
    task = task_by_name(tasks, name)
    assert set(task) >= {"name", "ansible.builtin.command", "loop", "loop_control", "register"}
    assert task["register"] == register
    assert task["loop_control"]["loop_var"] == loop_var
    assert task["ansible.builtin.command"]["argv"][1:4] == command


def assertion_loop_contract(tasks, name, producer_register, loop_var):
    """Ensure assertions consume the exact producer registered-loop results."""
    task = task_by_name(tasks, name)
    assert task.get("loop") == "{{ " + producer_register + ".results }}"
    assert task.get("loop_control", {}).get("loop_var") == loop_var


def assertion_expressions(task):
    assertions = task["ansible.builtin.assert"]["that"]
    assert isinstance(assertions, list)
    assert all(isinstance(expression, str) for expression in assertions)
    # Fold YAML block scalars so equivalent task expressions compare as one
    # structured assertion, rather than inspecting the playbook source text.
    return {" ".join(expression.split()) for expression in assertions}


def run_network_contract(stage, assertion, case, expected_success):
    """Execute the exact staged filter and assertion tasks for one fixture."""
    result = {
        "pg_replication_container": case["container"],
        "stdout": json.dumps(case["network"]),
    }
    playbook = [{
        "hosts": "localhost",
        "connection": "local",
        "gather_facts": False,
        "vars": {
            "pg_replication_containers": [case["container"]],
            "pg_replication_container_networks": {"results": [result]},
            "pg_replication_network_ipv4_unicast_by_container": {},
        },
        "tasks": [
            stage,
            assertion,
        ],
    }]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml") as handle:
        yaml.safe_dump(playbook, handle, sort_keys=False)
        handle.flush()
        completed = subprocess.run(
            [shutil.which("ansible-playbook") or "ansible-playbook", "-i", "localhost,", handle.name],
            capture_output=True,
            text=True,
            check=False,
        )
    if expected_success:
        assert completed.returncode == 0, completed.stdout + completed.stderr
    else:
        assert completed.returncode != 0, completed.stdout + completed.stderr
        assert "must use only Podman's default network with a unicast IPv4 address" in (
            completed.stdout + completed.stderr
        )


def main():
    fixture = json.loads(
        (ROOT / "scripts/fixtures/replication_inspect_registered_results.json").read_text()
    )
    container_result = fixture["container_result"]
    registered_result_contract(container_result)
    assert container_result["ansible_loop_var"] == "pg_replication_container"
    container_json = json.loads(container_result["stdout"])
    assert container_result["pg_replication_container"] == "instance-idarsi-rl9-primary"
    assert set(container_json) == {"Image"}
    assert isinstance(container_json["Image"], str) and container_json["Image"]

    built_result = fixture["built_image_result"]
    registered_result_contract(built_result)
    nested_result = built_result["pg_replication_image_result"]
    registered_result_contract(nested_result)
    assert built_result["ansible_loop_var"] == "pg_replication_image_result"
    assert nested_result["ansible_loop_var"] == "pg_replication_container"
    image_json = json.loads(built_result["stdout"])
    assert nested_result["pg_replication_container"] == container_result[
        "pg_replication_container"
    ]
    assert json.loads(nested_result["stdout"])["Image"] == image_json["Id"]
    assert set(image_json) == {"Architecture", "Os", "Id", "Config"}
    assert image_json["Architecture"] == "amd64"
    assert image_json["Os"] == "linux"
    assert set(image_json["Config"]) == {"Labels"}
    assert set(image_json["Config"]["Labels"]) == {
        "io.idarsi.replication.base-identity",
        "io.idarsi.replication.base-image",
        "io.idarsi.replication.base-digest",
        "io.idarsi.replication.build-contract",
    }

    prepare = yaml.safe_load((ROOT / "molecule/replication/prepare.yml").read_text())
    tasks = prepare[0]["tasks"]
    networks_fixture = json.loads(
        (ROOT / "scripts/fixtures/replication_container_networks.json").read_text()
    )
    assert set(networks_fixture) == {"primary", "standby"}
    assert set(networks_fixture["primary"]) == {
        "explicit_null", "wrong_type", "empty", "non_unicast", "valid_ipv4"
    }
    assert set(networks_fixture["standby"]) == set(networks_fixture["primary"])

    network_assertions = assertion_expressions(task_by_name(tasks, NETWORK_ASSERT))
    unicast_assertions = assertion_expressions(task_by_name(tasks, UNICAST_ASSERT))
    assert any("is mapping" in expression for expression in network_assertions)
    assert any("IPAddress" in expression for expression in network_assertions)
    assert any("is defined" in expression for expression in network_assertions)
    assert any("is string" in expression for expression in network_assertions)
    assert not any("ipaddr" in expression for expression in network_assertions)
    assert any('keys() | list | sort == ["podman"]' in expression for expression in network_assertions)
    assert any('"host" not in' in expression for expression in network_assertions)
    assert any('"pasta" not in' in expression for expression in network_assertions)

    stage = task_by_name(tasks, "Stage the inspected Podman IPv4 unicast result")
    stage_text = str(stage)
    assert "ansible.utils.ipaddr('unicast')" in stage_text
    assert "is ansible.utils.ipv4" in stage_text
    assert stage.get("when") and all("ipaddr" not in expression for expression in stage["when"])
    stage_conditions = {" ".join(expression.split()) for expression in stage["when"]}
    assert {
        "pg_replication_network_payload is mapping",
        "pg_replication_network_podman is mapping",
        "pg_replication_network_ipv4_candidate is string",
        "pg_replication_network_ipv4_candidate | trim | length > 0",
        "pg_replication_network_ipv4_candidate is ansible.utils.ipv4",
    } <= stage_conditions
    assert any(
        "pg_replication_network_ipv4_unicast_by_container.get" in expression
        and "is not none" in expression
        for expression in unicast_assertions
    )
    assert any(
        "pg_replication_network_ipv4_unicast_by_container.get" in expression
        and "pg_replication_network_ipv4_candidate_by_container.get" in expression
        for expression in unicast_assertions
    )
    assertion = task_by_name(tasks, UNICAST_ASSERT)
    for host, cases in networks_fixture.items():
        for name, network in cases.items():
            run_network_contract(
                stage,
                assertion,
                {"container": f"instance-idarsi-rl9-{host}", "network": network},
                name == "valid_ipv4",
            )

    inspect_task_contract(
        tasks,
        CONTAINER_INSPECT,
        "pg_replication_image_preflight",
        "pg_replication_container",
        ["container", "inspect", "{{ pg_replication_container }}"],
    )
    inspect_task_contract(
        tasks,
        IMAGE_INSPECT,
        "pg_replication_built_image_preflight",
        "pg_replication_image_result",
        ["image", "inspect", "{{ (pg_replication_image_result['stdout'] | from_json)['Image'] }}"],
    )
    assertion_loop_contract(
        tasks,
        CONTAINER_ASSERT,
        "pg_replication_image_preflight",
        "pg_replication_image_result",
    )
    assertion_loop_contract(
        tasks,
        IMAGE_ASSERT,
        "pg_replication_built_image_preflight",
        "pg_replication_built_image_result",
    )
    container_assertions = assertion_expressions(task_by_name(tasks, CONTAINER_ASSERT))
    image_assertions = assertion_expressions(task_by_name(tasks, IMAGE_ASSERT))

    assert {
        "pg_replication_image_result['rc'] == 0",
         "(pg_replication_image_result['stdout'] | from_json) is mapping",
         "'Image' in (pg_replication_image_result['stdout'] | from_json)",
         "(pg_replication_image_result['stdout'] | from_json)['Image'] is string",
         "pg_replication_image_result['ansible_loop_var'] == \"pg_replication_container\"",
         "pg_replication_image_result['rc'] is integer",
         "pg_replication_image_result['stdout'] is string",
         "pg_replication_image_result['stderr'] is string",
    } <= container_assertions
    assert {
         "pg_replication_built_image_result['rc'] == 0",
         "pg_replication_built_image_result['rc'] is integer",
         "pg_replication_built_image_result['stdout'] is string",
         "pg_replication_built_image_result['stderr'] is string",
         "pg_replication_built_image_result['ansible_loop_var'] == \"pg_replication_image_result\"",
         "(pg_replication_built_image_result['pg_replication_image_result']['stdout'] | from_json) is mapping",
         "'Image' in (pg_replication_built_image_result['pg_replication_image_result']['stdout'] | from_json)",
         "(pg_replication_built_image_result['pg_replication_image_result']['stdout'] | from_json)['Image'] is string",
         "pg_replication_built_image_result['pg_replication_image_result']['rc'] is integer",
         "pg_replication_built_image_result['pg_replication_image_result']['stdout'] is string",
         "pg_replication_built_image_result['pg_replication_image_result']['stderr'] is string",
         "pg_replication_built_image_result['pg_replication_image_result']['ansible_loop_var'] == \"pg_replication_container\"",
         "(pg_replication_built_image_result['stdout'] | from_json)['Architecture'] == \"amd64\"",
        "(pg_replication_built_image_result['stdout'] | from_json)['Config']['Labels'] is mapping",
        "((pg_replication_built_image_result['pg_replication_image_result']['stdout'] | from_json)['Image'] | regex_replace('^([0-9a-f]{64})$', 'sha256:\\\\1')) == ((pg_replication_built_image_result['stdout'] | from_json)['Id'] | regex_replace('^([0-9a-f]{64})$', 'sha256:\\\\1'))",
    } <= image_assertions

    all_expressions = container_assertions | image_assertions
    forbidden = re.compile(
        r"(?:\bitem\b|\bName\b|\.Name\b|\[['\"]Name['\"]\]|"
        r"\bis\s+(?:not\s+)?undefined\b|\bdefault\s*\(|\|\s*d\s*\()"
    )
    assert not any(forbidden.search(expression) for expression in all_expressions)
    print("replication Podman inspect shape guardrails: PASS")


if __name__ == "__main__":
    main()
