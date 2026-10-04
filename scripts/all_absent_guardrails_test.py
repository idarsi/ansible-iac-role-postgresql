#!/usr/bin/env python3
"""Static guardrails for role-owned all_absent package cleanup."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def task_records(value):
    for task in value or []:
        if not isinstance(task, dict):
            continue
        yield task
        yield from task_records(task.get("block"))
        yield from task_records(task.get("rescue"))
        yield from task_records(task.get("always"))


all_absent = list(task_records(yaml.safe_load((ROOT / "tasks/all_absent.yml").read_text())))
package_present = list(task_records(yaml.safe_load((ROOT / "tasks/package_present.yml").read_text())))

cleanup = next(task for task in all_absent if task.get("name") == "Ensuring all PostgreSQL packages are absent")
module = cleanup["ansible.builtin.dnf"]
assert "allowerasing" not in module, "all_absent must never enable allowerasing"
assert module["name"] == "{{ pg_all_absent_packages }}", "all_absent must remove only marker-owned packages"
assert cleanup["when"] == "pg_all_absent_packages | length > 0"

marker = next(task for task in all_absent if task.get("name") == "Reading managed package marker")
assert marker.get("when") == "pg_managed_packages_marker.stat.exists"
assert any(task.get("name") == "Selecting installed role-owned packages" for task in all_absent)

install = next(
    task
    for task in package_present
    if task.get("name") == "Ensuring packages are installed"
    and "ansible.builtin.dnf" in task
)
assert install["ansible.builtin.dnf"]["allowerasing"] is True

print("all_absent ownership and allowerasing guardrails: PASS")
