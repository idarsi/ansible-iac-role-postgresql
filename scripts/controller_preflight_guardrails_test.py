#!/usr/bin/env python3
"""Static guardrails for update and controller-side CA preflight semantics."""

import json
from pathlib import Path
import os
import tempfile

import yaml


ROOT = Path(__file__).parents[1]


def tasks(path):
    document = yaml.safe_load(path.read_text())
    return [task for task in document if isinstance(task, dict)]


def main():
    main_tasks = tasks(ROOT / "tasks/main.yml")
    by_name = {task.get("name", ""): task for task in main_tasks}

    controller_when = str(by_name["Running controller-side CA source validation"]["when"])
    bootstrap_when = str(by_name["Installing certificate preflight bootstrap packages"]["when"])
    certificate_when = str(by_name["Running tool-dependent certificate preflight"]["when"])
    for condition in (controller_when, bootstrap_when, certificate_when):
        assert "update" not in condition, f"update must not enter: {condition}"

    pure_preflight = by_name["Running pure PostgreSQL inventory and certificate model preflight"]
    assert pure_preflight["when"] == "state != 'update'"

    update = (ROOT / "tasks/update.yml").read_text()
    assert 'state: "latest"' in update
    assert "bootstrap_packages_present" not in update
    assert "certificate_preflight" not in update

    controller_tasks = tasks(ROOT / "tasks/validate/validate_controller_sources.yml")
    controller_source = (ROOT / "tasks/validate/validate_controller_sources.yml").read_text()
    assert "rc | default(-1) in [0, 1]" not in controller_source
    assert "pg_validation_controller_ca_source_namei_result.failed | default(false) | bool is false" in controller_source
    assert "pg_validation_controller_ca_source_namei_stats.results" in controller_source
    assert ".failed | default(false) | bool) is false" in controller_source
    assert ".stat.exists | bool) is false" in controller_source
    tool_stat = next(task for task in controller_tasks if "Checking required controller" in task["name"])
    assert tool_stat["delegate_to"] == "localhost"
    assert tool_stat["become"] is False
    assert tool_stat["ansible.builtin.stat"]["follow"] is False
    assert "pg_validation_controller_ca_sources | length > 0" in str(tool_stat["when"])
    assert tool_stat["ansible.builtin.stat"]["path"] == "{{ pg_validation_controller_ca_inspection_tool }}"
    assert tool_stat["loop"] == ["/usr/bin/namei", "/usr/bin/getfacl"]

    tool_assert = next(task for task in controller_tasks if "Requiring controller CA" in task["name"])
    assert "pg_validation_controller_ca_sources | length > 0" in str(tool_assert["when"])
    assert "never installs controller packages" in tool_assert["ansible.builtin.assert"]["fail_msg"]
    tool_conditions = tool_assert["ansible.builtin.assert"]["that"]
    assert any("islnk" in str(condition) for condition in tool_conditions)
    assert any("isreg" in str(condition) for condition in tool_conditions)
    assert any("executable" in str(condition) for condition in tool_conditions)

    source_type = next(task for task in controller_tasks if "source value types" in task["name"])
    source_path = next(task for task in controller_tasks if "source path safety" in task["name"])
    source_type_index = controller_tasks.index(source_type)
    source_path_index = controller_tasks.index(source_path)
    tool_index = controller_tasks.index(tool_stat)
    ancestor_index = next(index for index, task in enumerate(controller_tasks)
                          if "source ancestors" in task.get("name", "") and "Deriving" in task["name"])
    assert source_type_index < source_path_index < tool_index < ancestor_index
    assert "is string" in str(source_type["ansible.builtin.assert"]["that"])
    assert "^/[^/]" in str(source_path["ansible.builtin.assert"]["that"])
    assert "//" in str(source_path["ansible.builtin.assert"]["that"])
    assert "\\.{1,2}" in str(source_path["ansible.builtin.assert"]["that"])

    fixtures = json.loads((ROOT / "scripts/fixtures/controller_ca_sources.json").read_text())

    def safe_source(value):
        return (isinstance(value, str) and value.startswith("/")
                and not value.startswith("//") and "//" not in value
                and not value.endswith("/") and "\n" not in value and "\r" not in value
                and "\\" not in value
                and not any(component in {".", ".."} for component in value.split("/")))

    for fixture in fixtures:
        actual = all(safe_source(source) for source in fixture["sources"])
        assert actual == fixture["valid"], fixture["name"]
    assert any(fixture["name"] == "no-source" and not fixture["sources"]
               and fixture["valid"] for fixture in fixtures)

    commands = [task["ansible.builtin.command"]["argv"][0] for task in controller_tasks
                if "ansible.builtin.command" in task]
    assert commands and set(commands) == {"/usr/bin/namei", "/usr/bin/getfacl"}

    # Validation is inventory/read-only only: its dispatcher must not include
    # package bootstrap or certificate convergence paths.
    assert "state == 'validate'" not in str(by_name["Installing certificate preflight bootstrap packages"].get("when", ""))
    assert "state == 'validate'" not in str(by_name["Running tool-dependent certificate preflight"].get("when", ""))

    # Exercise the fail-closed executable contract with isolated temporary
    # paths.  This never masks or changes a host command and covers the
    # missing, symlink, non-regular, and non-executable cases.
    def accepted(path):
        info = os.lstat(path) if os.path.lexists(path) else None
        return bool(info and os.path.isfile(path) and not os.path.islink(path)
                    and os.access(path, os.X_OK))

    with tempfile.TemporaryDirectory() as directory:
        regular = Path(directory) / "tool"
        regular.write_text("#!/bin/sh\nexit 0\n")
        regular.chmod(0o700)
        symlink = Path(directory) / "symlink"
        symlink.symlink_to(regular)
        non_regular = Path(directory) / "directory"
        non_regular.mkdir()
        non_executable = Path(directory) / "not-executable"
        non_executable.write_text("stub\n")
        assert accepted(regular)
        assert not accepted(Path(directory) / "missing")
        assert not accepted(symlink)
        assert not accepted(non_regular)
        assert not accepted(non_executable)


if __name__ == "__main__":
    main()
