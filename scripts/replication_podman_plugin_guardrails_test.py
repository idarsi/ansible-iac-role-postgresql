#!/usr/bin/env python3
"""Check the supported Molecule Podman network option and generated argv."""

import json
import re
import sys
from pathlib import Path

import yaml


def _access_keys(expression):
    """Return keys used through Jinja bracket, dot, and ``get`` access."""
    # Do not evaluate Jinja or depend on whether its string literals use single
    # quotes, double quotes, or no quotes.  These small lexical rules describe
    # the access shape that this guardrail cares about.
    identifier = r"[A-Za-z_][A-Za-z0-9_]*"
    accesses = set()
    accesses.update(
        re.findall(
            rf"\[\s*(?:['\"]\s*)?(?P<key>{identifier})\s*(?:['\"]\s*)?\]",
            expression,
        )
    )
    accesses.update(re.findall(rf"\.\s*(?P<key>{identifier})\b", expression))
    accesses.update(
        re.findall(
            rf"\.\s*get\s*\(\s*(?:['\"]\s*)?(?P<key>{identifier})\s*(?:['\"]\s*)?\s*\)",
            expression,
        )
    )
    return accesses


def _require_accesses(expression, required):
    """Assert the expression contains every required structural access."""
    missing = set(required) - _access_keys(expression)
    assert not missing, f"Jinja expression is missing accesses {sorted(missing)}: {expression}"


def _find_task(tasks, predicate, description):
    """Find a plugin task by its operation, not a version-specific display name."""
    matches = [task for task in tasks if predicate(task)]
    assert len(matches) == 1, f"expected one {description}, found {len(matches)}"
    return matches[0]


def _walk_tasks(tasks):
    """Yield tasks recursively, including blocks, rescue, and always tasks."""
    for task in tasks:
        yield task
        for key in ("block", "rescue", "always"):
            yield from _walk_tasks(task.get(key, []))


def _walk_playbook(playbook):
    """Yield tasks from plays, including handlers and nested task blocks."""
    for play in playbook:
        yield from _walk_tasks(play.get("tasks", []))
        yield from _walk_tasks(play.get("handlers", []))


def main():
    try:
        import molecule_plugins.podman
    except ImportError as error:
        raise AssertionError("Molecule Podman plugin is not installed") from error

    plugin_root = Path(molecule_plugins.podman.__file__).parent
    schema = json.loads((plugin_root / "schema/driver.json").read_text())
    platform = schema["$defs"]["MoleculePlatformModel"]["properties"]
    assert platform["extra_opts"]["type"] == "array"
    assert platform["extra_opts"]["items"]["type"] == "string"

    create = (plugin_root / "playbooks/create.yml").read_text()
    assert 'cmd_args: "{{ molecule_podman_args' in create
    assert "item.extra_opts" in create
    assert 'network: "{{ item.network | default(omit) }}"' in create

    destroy = yaml.safe_load((plugin_root / "playbooks/destroy.yml").read_text())
    destroy_tasks = list(_walk_playbook(destroy))
    network_destroy = _find_task(
        destroy_tasks,
        lambda task: "containers.podman.podman_network" in task
        and task.get("loop") == "{{ molecule_yml.platforms | flatten(levels=1) }}",
        "Podman network destroy task",
    )
    assert "item.network is defined" in network_destroy["when"]
    assert network_destroy["containers.podman.podman_network"]["name"] == "{{ item.network }}"

    molecule_file = Path(__file__).parents[1] / "molecule/replication/molecule.yml"
    molecule = yaml.safe_load(molecule_file.read_text())
    platforms = molecule["platforms"]
    assert len(platforms) == 2
    for platform in platforms:
        assert "network" not in platform
        rendered_create_argv = list(platform.get("extra_opts", []))
        assert rendered_create_argv == ["--network=podman"]
        assert not any(
            option in {"--network=pasta", "--network=host", "--network=none"}
            or option.startswith("--network=") and option != "--network=podman"
            for option in rendered_create_argv
        )

    converge_file = Path(__file__).parents[1] / "molecule/replication/converge.yml"
    converge = yaml.safe_load(converge_file.read_text())
    network_task = _find_task(
        list(_walk_tasks(converge[0]["tasks"])),
        lambda task: task.get("ansible.builtin.include_tasks") == "validate_external_network_case.yml"
        and "pg_replication_external_network_case" in task.get("vars", {}),
        "external-network validation include",
    )
    expressions = network_task["vars"]["pg_replication_external_network_case"]
    subnet_expression = expressions["subnets"]
    assert subnet_expression == "{{ pg_replication_subnets_data }}"
    address_expression = expressions["ipv4"]
    assert "pg_replication_container_network_data" in address_expression
    _require_accesses(address_expression, {"podman", "IPAddress"})

    fixture = yaml.safe_load(
        (Path(__file__).parent / "fixtures/replication_podman_plugin_expressions.yml").read_text()
    )
    for expression in fixture["valid"]:
        _require_accesses(expression["subnet"], {"subnet"})
        _require_accesses(expression["address"], {"podman", "IPAddress"})
    for expression in fixture["invalid"]:
        try:
            _require_accesses(expression["expression"], set(expression["required"]))
        except AssertionError:
            continue
        raise AssertionError(f"Invalid Jinja fixture unexpectedly passed: {expression}")
    print("replication Podman plugin schema and argv guardrails: PASS")


if __name__ == "__main__":
    try:
        main()
    except (AssertionError, KeyError, OSError, json.JSONDecodeError) as error:
        print(f"replication Podman plugin guardrail: {error}", file=sys.stderr)
        raise SystemExit(1)
