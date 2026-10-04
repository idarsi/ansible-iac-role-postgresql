#!/bin/bash
set -euo pipefail
root=$(mktemp -d)
trap 'rm -rf -- "$root"' EXIT
source "$(dirname "$0")/../files/pki_registry.sh"
declare -F validate_pki_serial_paths validate_pki_serial_registry >/dev/null
printf '01\n02aa\n' >"$root/valid"
validate_pki_serial_registry "$root/valid"
mkdir -p "$root/safe"
ln -s "$root/valid" "$root/link"
if validate_pki_serial_paths "$root/link" "$root/safe/missing" 2>/dev/null; then
  printf 'PKI path guardrail followed a symlink\n' >&2; exit 1
fi
chmod 0770 "$root/safe"
if validate_pki_directory_path "$root/safe/new-lock" 2>/dev/null; then
  printf 'unsafe PKI directory ancestor was accepted\n' >&2; exit 1
fi

# ACL parsing is deterministic even on hosts without setfacl: these fixtures
# exercise the parser through a controlled getfacl command.
fake_bin="$root/parser-bin"
mkdir "$fake_bin"
chmod 0700 "$root/safe"
printf '%s\n' '#!/bin/sh' 'cat "$PKI_ACL_FIXTURE"' >"$fake_bin/getfacl"
chmod 0755 "$fake_bin/getfacl"
for fixture in owner_mode named_user named_group default_user; do
  export PKI_ACL_FIXTURE="$(dirname "$0")/fixtures/pki_acl_${fixture}.txt"
  if [[ "$fixture" == owner_mode ]]; then
    PATH="$fake_bin:$PATH" validate_pki_directory_path "/"
  elif PATH="$fake_bin:$PATH" validate_pki_directory_path "/"; then
    printf 'unsafe ACL parser fixture was accepted: %s\n' "$fixture" >&2; exit 1
  fi
done

# ACL mutation fixtures additionally verify the host's setfacl implementation
# when it is available; the parser contract above must never be skipped.
if command -v setfacl >/dev/null 2>&1; then
  chmod 0700 "$root/safe"
  setfacl -m "u:nobody:--x" "$root/safe"
  if validate_pki_directory_path "$root/safe/named-acl" 2>/dev/null; then
    printf 'named ACL directory fixture was accepted\n' >&2; exit 1
  fi
  setfacl -b "$root/safe"
  setfacl -d -m "u::rwx,g::---,o::---,u:nobody:--x" "$root/safe"
  if validate_pki_directory_path "$root/safe/default-acl" 2>/dev/null; then
    printf 'default ACL directory fixture was accepted\n' >&2; exit 1
  fi
  setfacl -k "$root/safe"

  fake_bin="$root/fake-bin"
  mkdir "$fake_bin"
  printf '%s\n' '#!/bin/sh' 'exit 77' >"$fake_bin/getfacl"
  chmod 0755 "$fake_bin/getfacl"
  if PATH="$fake_bin:$PATH" validate_pki_directory_path "$root/safe/getfacl-failure" 2>/dev/null; then
    printf 'getfacl failure fixture was accepted\n' >&2; exit 1
  fi
fi

# Parse the complete reachable task graph.  Includes are followed rather than
# treated as opaque text so a mutation hidden in a preflight/convergence child
# cannot bypass the gate.
python3 - "$PWD" <<'PY'
from pathlib import Path
import sys
import yaml
import tempfile
import shutil

root = Path(sys.argv[1])
mutation_modules = {"file", "copy", "template", "assemble", "acl", "package", "dnf", "yum", "service", "systemd", "systemd_service", "user", "group", "mount", "lineinfile", "blockinfile", "replace", "known_hosts", "shell", "raw", "script", "get_url", "uri", "archive", "ini_file", "xml", "postgresql_db", "postgresql_user", "podman_container", "filesystem", "lvol", "parted"}
read_only_words = ("check", "inspect", "stat", "validate", "assert", "reject", "require", "verify", "probe", "collect")

def walk(value, path=()):
    if isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, path + (index,))
    elif isinstance(value, dict):
        if any(key in value for key in ("name", "block", "rescue", "always")):
            yield value, path
        for key in ("block", "rescue", "always"):
            if key in value:
                yield from walk(value[key], path + (key,))

def module(task):
    control = {"name", "when", "register", "changed_when", "failed_when", "loop", "loop_control", "vars", "become", "become_user", "delegate_to", "no_log", "tags", "notify", "block", "rescue", "always", "args", "environment", "until", "retries", "delay", "check_mode", "throttle", "run_once", "listen", "module_defaults"}
    return next((key.rsplit('.', 1)[-1] for key in task if key not in control and not key.startswith("ansible.builtin.include_") and not key.startswith("ansible.builtin.import_")), None)

def target(task):
    targets = []
    for key in ("ansible.builtin.include_tasks", "ansible.builtin.import_tasks"):
        value = task.get(key)
        if isinstance(value, str):
            if "{{ pg_state }}" in value or "{{ task_state }}" in value:
                # Dynamic state dispatch is bounded by the role's task files.
                targets.extend(str(path.relative_to(root / "tasks")) for path in (root / "tasks").glob("*.yml")
                               if path.stem not in {"main", "loop_instances", "loop_databases"})
            elif "{{" not in value:
                targets.append(value)
            else:
                # A non-state dynamic include is unsafe to ignore.  The role
                # currently has no such include, but fail closed if one is
                # introduced later.
                raise AssertionError(f"unresolved include target in task: {value}")
    return targets

def scan(path, gated=False, seen=None):
    seen = set() if seen is None else seen
    path = path.resolve()
    if path in seen:
        return
    seen.add(path)
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, list), path
    for task, task_path in walk(document):
        name = str(task.get("name", ""))
        current = module(task)
        children = target(task)
        include_keys = [key for key in task if key.endswith("include_tasks") or key.endswith("import_tasks")]
        if include_keys and not children:
            raise AssertionError(f"unresolved include target in {path}:{task_path}")
        for child in children:
            child_path = (path.parent / child).resolve()
            child_gated = (gated or "PREFLIGHT COMPLETE" in name
                           or "tool-dependent certificate preflight" in name.lower()
                           or "bootstrap packages" in name.lower())
            # The wrapper's preflight include is itself the gate boundary;
            # convergence is gated only by the following explicit marker.
            if "preflight" in child_path.name:
                child_gated = False
            scan(child_path, child_gated, seen)
        if current in mutation_modules and not gated:
            raise AssertionError(f"mutation before preflight in {path}:{task_path}")
        if current in {"command", "shell"} and not any(word in name.lower() for word in read_only_words) and not gated:
            raise AssertionError(f"unclassified command before preflight in {path}:{task_path}")
        if "PREFLIGHT COMPLETE" in name or "tool-dependent certificate preflight" in name.lower():
            gated = True

# Check the real entry graph, including main dispatch and dynamic state files.
scan(root / "tasks/main.yml")
for filename in ("tasks/certification_present.yml", "tasks/cluster_certificates_present.yml"):
    scan(root / filename)

# The staged clean-install contract is represented in the main task order.
main = yaml.safe_load((root / "tasks/main.yml").read_text())
names = [str(task.get("name", "")).lower() for task in main if isinstance(task, dict)]
pure = names.index("running pure postgresql inventory and certificate model preflight")
bootstrap = names.index("installing certificate preflight bootstrap packages")
full = names.index("running tool-dependent certificate preflight")
state = names.index("state: ensure postgresql installations are present")
assert pure < bootstrap < full < state, "staged preflight order is not pure -> bootstrap -> full -> state"
bootstrap_tasks = yaml.safe_load((root / "tasks/bootstrap_packages_present.yml").read_text())
assert all(any(key.endswith("include_tasks") for key in task) for task in bootstrap_tasks), "bootstrap stage contains a non-package task"

# Negative fixture: prove the recursive parser rejects a write inserted into
# the preflight graph, without changing the working tree.
with tempfile.TemporaryDirectory() as directory:
    fixture = Path(directory) / "tasks"
    shutil.copytree(root / "tasks", fixture)
    bad = fixture / "certificate_preflight.yml"
    bad.write_text(bad.read_text() + '\n- name: "negative mutation fixture"\n  ansible.builtin.file:\n    path: "/tmp/guardrail-negative"\n    state: "touch"\n')
    try:
        scan(fixture / "certificate_preflight.yml")
    except AssertionError:
        pass
    else:
        raise AssertionError("negative mutation fixture was accepted")

# An include with no statically resolvable target must never be silently
# skipped by the graph checker.
    unresolved = fixture / "certification_present.yml"
    unresolved.write_text(unresolved.read_text() + '\n- name: "unresolved include fixture"\n  ansible.builtin.include_tasks: "{{ missing_fixture }}.yml"\n')
    try:
        scan(unresolved)
    except AssertionError as error:
        assert "unresolved include target" in str(error)
    else:
        raise AssertionError("unresolved include fixture was accepted")

def tasks(value):
    if isinstance(value, list):
        for child in value:
            yield from tasks(child)
    elif isinstance(value, dict):
        if any(key.startswith("ansible.builtin.") for key in value):
            yield value
        for key in ("block", "rescue", "always"):
            if key in value:
                yield from tasks(value[key])

cert = list(tasks(yaml.safe_load((root / "tasks/certification_preflight.yml").read_text())))
cluster = list(tasks(yaml.safe_load((root / "tasks/cluster_certificates_preflight.yml").read_text())))
assert any("ansible.builtin.stat" in task and task["ansible.builtin.stat"].get("follow") is False
           and "pg_certificate_preflight_paths" in str(task.get("loop", ""))
           for task in cert), "certificate destination stat task is missing"
assert any("ansible.builtin.command" in task and "namei" in str(task["ansible.builtin.command"])
           for task in cert), "controller ancestor inspection task is missing"
assert any("ansible.builtin.set_fact" in task and
           {"pg_certificate_serial_registry", "pg_certificate_serial_lock"}.issubset(task["ansible.builtin.set_fact"])
           for task in cert), "certificate serial model is missing"
assert any("ansible.builtin.set_fact" in task and
           "pg_cluster_seed_pki_artifacts" in str(task["ansible.builtin.set_fact"]) and
           "pg_cluster_generated_pki_destinations" in str(task["ansible.builtin.set_fact"]) and
           "pg_cluster_patroni_external_pki_destinations" in str(task["ansible.builtin.set_fact"])
           for task in cluster), "cluster seed/generated/external model is missing"
assert any("ansible.builtin.command" in task and "getfacl" in str(task["ansible.builtin.command"])
           for task in cluster), "cluster ACL inspection task is missing"
assert any("ansible.builtin.stat" in task and task["ansible.builtin.stat"].get("follow") is False
            for task in cluster), "cluster path inspection task is missing"

# The validation scenario must consume (not create) the Molecule scenario
# directory, and both lifecycle hooks must inspect safety before deletion.
prepare = yaml.safe_load((root / "molecule/validation/prepare.yml").read_text())
destroy = yaml.safe_load((root / "molecule/validation/destroy.yml").read_text())
prepare_text = (root / "molecule/validation/prepare.yml").read_text()
destroy_text = (root / "molecule/validation/destroy.yml").read_text()
assert "Require a pre-existing safe controller scenario directory" in prepare_text
assert "iac_validation_fixture_ancestors.results[0].stat.exists" in prepare_text
assert "iac_validation_scenario_directory }}/.artifacts" in prepare_text
assert prepare_text.index("Require a pre-existing safe controller scenario directory") < prepare_text.index("Creating private controller fixture artifact base")
assert prepare_text.index("Checking every stale controller manifest component ACL") < prepare_text.index("Removing stale controller-side validation fixtures")
assert destroy_text.index("Require a pre-existing safe controller scenario directory before cleanup") < destroy_text.index("Removing only the validated controller fixture root")
assert destroy_text.index("Checking every controller manifest component ACL") < destroy_text.index("Removing only the validated controller fixture root")

# Molecule cleanup namei checks must fail closed.  In particular, rc=1 is not
# an unconditional allowance: it requires the matching fixture-root stat to
# have succeeded and proved that the root is absent.
for cleanup in root.glob("molecule/**/{destroy,cleanup}.yml"):
    text = cleanup.read_text()
    assert "rc in [0, 1]" not in text, f"unconditional namei rc allowance in {cleanup}"
    if "namei" in text:
        assert "failed | default(false) | bool is false" in text, f"namei failure gate missing in {cleanup}"
        assert "stat.exists is defined" in text, f"namei absence proof missing in {cleanup}"
PY
printf '%s\n' 'PKI registry, lock-serialization, and parsed task guardrails passed'
