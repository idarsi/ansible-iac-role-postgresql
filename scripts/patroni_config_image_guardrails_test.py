#!/usr/bin/env python3
"""Structural guardrails for the test-only Patroni configuration image."""

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
dockerfile = (ROOT / "molecule/patroni_config/Dockerfile.j2").read_text()
scenario = yaml.safe_load((ROOT / "molecule/patroni_config/molecule.yml").read_text())
prepare = (ROOT / "molecule/patroni_config/prepare.yml").read_text()
verify = (ROOT / "molecule/patroni_config/verify.yml").read_text()


def _named_task(tasks, name):
    """Return the one task with *name*, rejecting ambiguous fixtures."""

    matches = [task for task in tasks if task.get("name") == name]
    assert len(matches) == 1, f"expected exactly one task named {name!r}"
    return matches[0]


def _assert_fact_directory_guard(tasks):
    """Check the specifically named parent-directory stat/assertion pair."""

    stat_task = _named_task(tasks, "Inspect the local facts directory without following links")
    stat_module = stat_task.get("ansible.builtin.stat")
    assert isinstance(stat_module, dict)
    assert stat_task.get("register") == "patroni_config_fact_directory"
    assert stat_module.get("path") == "{{ patroni_config_fact_path | dirname }}"
    assert stat_module.get("follow") is False

    guard_task = _named_task(tasks, "Require a safe local facts directory")
    guard = guard_task.get("ansible.builtin.assert")
    assert isinstance(guard, dict)
    assert set(guard.get("that", [])) == {
        "patroni_config_fact_directory.stat.exists",
        "patroni_config_fact_directory.stat.isdir",
        "not patroni_config_fact_directory.stat.islnk",
        'patroni_config_fact_directory.stat.pw_name == "root"',
        'patroni_config_fact_directory.stat.gr_name == "root"',
        'patroni_config_fact_directory.stat.mode == "0755"',
    }


from_line = next(line for line in dockerfile.splitlines() if line.startswith("FROM "))
assert "--platform=linux/amd64" in from_line
assert re.search(r"rockylinux:9-ubi-init@sha256:[0-9a-f]{64}$", from_line)

repo_block = re.search(r"printf '%s\\n'(?P<body>.*?)> /etc/yum.repos.d/", dockerfile, re.S)
assert repo_block, "the Dockerfile must generate an explicit repository file"
repo_lines = re.findall(r"'([^']*)'", repo_block.group("body"))
repos = {}
current = None
for line in repo_lines:
    if line.startswith("[") and line.endswith("]"):
        current = line[1:-1]
        repos[current] = {}
    elif "=" in line and current:
        key, value = line.split("=", 1)
        repos[current][key] = value
assert set(repos) == {"rocky-9.8-baseos", "rocky-9.8-appstream", "rocky-9.8-extras"}
for repo in repos.values():
    assert repo["enabled"] == "1"
    assert repo["sslverify"] == "1"
    assert repo["gpgcheck"] == "1"
    assert repo["repo_gpgcheck"] == "1"
    assert repo["gpgkey"] == "https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9"
    assert repo["baseurl"].startswith("https://dl.rockylinux.org/pub/rocky/9.8/")
assert "21CB256AE16FC54C6E652949702D426D350D275D" in dockerfile

assert "--disablerepo='*'" in dockerfile
assert "swap coreutils-single coreutils-0:8.32-40.el9.x86_64" in dockerfile
for unsafe in ("dnf update", "dnf distro-sync", "--allowerasing", "--nobest", "--downgrade", "--downloadonly"):
    assert unsafe not in dockerfile
assert "rpm -q --qf" in dockerfile and "bash-0:5.1.8-9.el9.x86_64" in dockerfile
assert "coreutils-0:8.32-40.el9.x86_64" in dockerfile
assert 'test "$(rpm -q coreutils-single 2>/dev/null || true)" = "package coreutils-single is not installed"' in dockerfile
for tool in ("bash", "openssl", "getfacl", "setfacl", "namei", "python3"):
    assert f"command -v {tool}" in dockerfile
assert 'python3_path="$(/usr/bin/readlink -e -- /usr/bin/python3)"' in dockerfile
assert 'test -f "${python3_path}" && test ! -L "${python3_path}" && test -x "${python3_path}"' in dockerfile

assert scenario["platforms"][0]["pre_build_image"] is False
assert scenario["platforms"][0]["dockerfile"] == "Dockerfile.j2"
prepare_tasks = yaml.safe_load(prepare)[0]["tasks"]
assert any("ansible.builtin.package_facts" in task for task in prepare_tasks)
_assert_fact_directory_guard(prepare_tasks)
assert any(
    task.get("ansible.builtin.command", {}).get("argv") == [
        "/usr/bin/readlink", "-e", "--", "/usr/bin/python3"
    ]
    for task in prepare_tasks
)
assert any(
    "patroni_config_python_realpath.stdout" in str(task)
    and task.get("ansible.builtin.stat", {}).get("follow") is False
    for task in prepare_tasks
)
assert any("stat.isreg" in str(task) and "stat.executable" in str(task) for task in prepare_tasks)
assert any("patroni_config_python_interpreter" in str(task) for task in prepare_tasks)
assert "/etc/ansible/facts.d/patroni_config.fact" in prepare
assert "/usr/bin/readlink" in prepare and "command -v readlink" not in prepare
assert any("rpm" in str(task.get("ansible.builtin.command", {})) for task in prepare_tasks)
assert "bash-0:5.1.8-9.el9.x86_64" in prepare
assert "coreutils-0:8.32-40.el9.x86_64" in prepare
verify_tasks = yaml.safe_load(verify)[0]["tasks"]
prepare_vars = yaml.safe_load(prepare)[0]["vars"]
verify_vars = yaml.safe_load(verify)[0]["vars"]
assert prepare_vars["patroni_config_fact_path"] == verify_vars["patroni_config_fact_path"] == "/etc/ansible/facts.d/patroni_config.fact"
assert prepare_vars["patroni_config_fact_key"] == verify_vars["patroni_config_fact_key"] == "python_interpreter"
assert "patroni_config_fact_path" in prepare and "patroni_config_fact_key" in prepare
assert "patroni_config_persisted_python_interpreter" in verify
fact_copy = next(task for task in prepare_tasks if "Write the canonical" in task["name"])
copy_args = fact_copy["ansible.builtin.copy"]
assert copy_args["dest"] == "{{ patroni_config_fact_path }}"
assert copy_args["follow"] is False and copy_args["unsafe_writes"] is False
assert copy_args["mode"] == "0644" and copy_args["owner"] == "root" and copy_args["group"] == "root"
assert "patroni_config_fact_key" in copy_args["content"]
assert any("stat.isreg" in str(task) and "stat.islnk" in str(task) for task in prepare_tasks)
assert any("stat.isreg" in str(task) and "stat.islnk" in str(task) for task in verify_tasks)
assert any("ansible_local" in str(task) and "python_interpreter" in str(task) for task in verify_tasks)
python_probe = next(task for task in verify_tasks if "Probe fallback Patroni address" in task["name"])
assert python_probe["ansible.builtin.command"]["argv"][0] == "{{ patroni_config_persisted_python_interpreter }}"
assert python_probe["ansible.builtin.command"]["argv"][0] != "python3"

negative_fixture = yaml.safe_load(
    (ROOT / "scripts/fixtures/patroni_config_bootstrap_stat_negative.yml").read_text()
)
try:
    _assert_fact_directory_guard(negative_fixture[0]["tasks"])
except AssertionError:
    pass
else:
    raise AssertionError("a bootstrap-tools stat must not satisfy the parent-directory guard")

print("patroni_config image guardrails: PASS")
