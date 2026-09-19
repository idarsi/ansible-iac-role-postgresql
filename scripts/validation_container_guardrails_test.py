"""Contract tests for the validation scenario's controller container guard."""

import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile

import yaml


ROOT = Path(__file__).parents[1]
PREPARE = ROOT / "molecule" / "validation" / "prepare.yml"
PROBE_TASKS = ROOT / "molecule" / "validation" / "container_guard.yml"
MOLECULE = ROOT / "molecule" / "validation" / "molecule.yml"


def task(tasks, name):
    return next(entry for entry in tasks if entry.get("name") == name)


def availability_allowed(return_code):
    return return_code in (0, 1)


def container_matches_contract(inspect):
    return (
        inspect.get("State", {}).get("Running") is True
        and inspect.get("State", {}).get("Status") == "running"
        and inspect.get("ImageName") == "docker.io/rockylinux/rockylinux:9-ubi-init"
        and inspect.get("Path") == "/sbin/init"
    )


FIXTURE_PLAYBOOK = """
---
- name: "Exercise validation container guard"
  hosts: localhost
  connection: local
  gather_facts: false
  vars:
    iac_validation_podman_executable: "{{ lookup('ansible.builtin.env', 'MOCK_PODMAN') }}"
    iac_validation_container_names:
      - "validation-fixture"
    iac_validation_expected_image: "docker.io/rockylinux/rockylinux:9-ubi-init"
    iac_validation_expected_command: "/sbin/init"
  tasks:
    - name: "Run production validation container guard"
      ansible.builtin.include_tasks: "{{ lookup('ansible.builtin.env', 'VALIDATION_CONTAINER_GUARD_TASK_FILE') }}"
"""


MOCK_PODMAN = """#!/usr/bin/env python3
import json
import os
import sys

mode = os.environ["MOCK_PODMAN_MODE"]
if sys.argv[1:3] == ["container", "exists"]:
    if mode == "absent":
        print("container does not exist", file=sys.stderr)
        raise SystemExit(1)
    if mode == "infrastructure":
        print("podman storage unavailable", file=sys.stderr)
        raise SystemExit(125)
    raise SystemExit(0)

if mode == "malformed":
    print("{not-json")
elif mode == "stopped":
    print(json.dumps([{"State": {"Running": False, "Status": "exited"}, "ImageName": "docker.io/rockylinux/rockylinux:9-ubi-init", "Path": "/sbin/init"}]))
elif mode == "wrong-image":
    print(json.dumps([{"State": {"Running": True, "Status": "running"}, "ImageName": "docker.io/other:image", "Path": "/sbin/init"}]))
elif mode == "wrong-command":
    print(json.dumps([{"State": {"Running": True, "Status": "running"}, "ImageName": "docker.io/rockylinux/rockylinux:9-ubi-init", "Path": "/bin/sh"}]))
else:
    print(json.dumps([{"State": {"Running": True, "Status": "running"}, "ImageName": "docker.io/rockylinux/rockylinux:9-ubi-init", "Path": "/sbin/init"}]))
"""


def run_fixture(mode):
    ansible_playbook = shutil.which("ansible-playbook") or "ansible-playbook"
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        mock = root / "podman"
        mock.write_text(MOCK_PODMAN)
        mock.chmod(mock.stat().st_mode | stat.S_IXUSR)
        playbook = root / "guard.yml"
        playbook.write_text(FIXTURE_PLAYBOOK)
        environment = {
            **os.environ,
            "MOCK_PODMAN": str(mock),
            "MOCK_PODMAN_MODE": mode,
            "VALIDATION_CONTAINER_GUARD_TASK_FILE": str(PROBE_TASKS),
        }
        return subprocess.run(
            [ansible_playbook, "-i", "localhost,", "-c", "local", str(playbook)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )


def main():
    plays = yaml.safe_load(PREPARE.read_text())
    probe_tasks = yaml.safe_load(PROBE_TASKS.read_text())
    controller_tasks = probe_tasks
    assert any(
        entry.get("ansible.builtin.include_tasks") == "container_guard.yml"
        for entry in plays[0]["tasks"]
    )
    availability = task(controller_tasks, "Check validation container availability")
    availability_guard = task(
        controller_tasks, "Reject Podman availability errors with original command context"
    )
    missing = task(controller_tasks, "Reject missing validation containers before target execution")
    inspection = task(controller_tasks, "Inspect validation container image, state, and command")
    inspection_error = task(controller_tasks, "Reject inspection errors with original command context")
    stale = task(controller_tasks, "Reject stale, stopped, or replaced validation containers")

    # Podman documents rc=1 for an absent container. Every other command error
    # must remain visible instead of being converted into a missing container.
    assert availability["failed_when"] is False
    assert availability_guard["when"] == "iac_validation_container_name.rc not in [0, 1]"
    assert "iac_validation_container_name.rc" in availability_guard["ansible.builtin.fail"]["msg"]
    assert "iac_validation_container_name.cmd" in availability_guard["ansible.builtin.fail"]["msg"]
    assert "iac_validation_container_name.stderr" in availability_guard["ansible.builtin.fail"]["msg"]
    assert "equalto', 1" in missing["ansible.builtin.assert"]["fail_msg"]

    # Inspection is deliberately separate: existence is not enough to prove
    # that Molecule still owns the expected running container.
    argv = inspection["ansible.builtin.command"]["argv"]
    assert argv[1:4] == ["container", "inspect", "--format"]
    assert argv[4] == "json"
    assert inspection_error["when"] == "iac_validation_container_name.rc != 0"
    conditions = "\n".join(stale["ansible.builtin.assert"]["that"])
    for required in ("State.Running", "State.Status", "ImageName", "Path"):
        assert required in conditions
    assert "iac_validation_expected_image" in stale["ansible.builtin.assert"]["fail_msg"]
    assert "iac_validation_expected_command" in stale["ansible.builtin.assert"]["fail_msg"]
    assert all(
        "item.item" not in yaml.safe_dump(entry)
        for entry in controller_tasks
    )

    scenario = yaml.safe_load(MOLECULE.read_text())
    sequence = scenario["scenario"]["test_sequence"]
    assert sequence.index("create") < sequence.index("prepare") < sequence.index("converge")
    expected_platforms = {
        platform["name"]: platform for platform in scenario["platforms"]
    }
    assert {"instance-idarsi-validation", "instance-idarsi-etcd"} == set(expected_platforms)
    for platform in expected_platforms.values():
        assert platform["image"] == "docker.io/rockylinux/rockylinux:9-ubi-init"
        assert platform["command"] == "/sbin/init"

    # Explicit contract examples: absent is a recoverable/stage-specific
    # failure, infrastructure errors are not, and a stale container is unsafe.
    assert availability_allowed(1)
    for infrastructure_error in (125, 126, 127):
        assert not availability_allowed(infrastructure_error)
    expected = {
        "State": {"Running": True, "Status": "running"},
        "ImageName": "docker.io/rockylinux/rockylinux:9-ubi-init",
        "Path": "/sbin/init",
    }
    assert container_matches_contract(expected)
    assert not container_matches_contract({**expected, "State": {"Running": False, "Status": "exited"}})
    assert not container_matches_contract({**expected, "ImageName": "docker.io/other:image"})

    # Run the guard as a real, minimal Ansible playbook with a mocked Podman
    # executable. This catches regressions that static YAML assertions miss.
    absent = run_fixture("absent")
    assert absent.returncode != 0
    assert "Absent container results" in absent.stdout + absent.stderr
    infrastructure = run_fixture("infrastructure")
    assert infrastructure.returncode != 0
    for context in ("rc=125", "podman", "podman storage unavailable"):
        assert context in infrastructure.stdout + infrastructure.stderr
    for invalid in ("malformed", "stopped", "wrong-image", "wrong-command"):
        assert run_fixture(invalid).returncode != 0
    valid = run_fixture("valid")
    assert valid.returncode == 0, valid.stdout + valid.stderr
    print("validation container availability/staleness guardrails: PASS")


if __name__ == "__main__":
    main()
