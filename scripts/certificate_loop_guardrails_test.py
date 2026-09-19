#!/usr/bin/env python3
"""Reject implicit Ansible loop state in certificate convergence tasks."""

from pathlib import Path
import re
import json
import yaml


ROOT = Path(__file__).parents[1]
TARGETS = (
    ROOT / "tasks/certification_preflight.yml",
    ROOT / "tasks/certification_converge.yml",
    ROOT / "tasks/cluster_certificates_apply.yml",
)
CLUSTER_CERTIFICATE_CONVERGE = ROOT / "tasks/cluster_certificates_converge.yml"
CLUSTER_CERTIFICATE_NORMALIZE = ROOT / "tasks/cluster_certificates_normalize.yml"
CLUSTER_CERTIFICATE_PREFLIGHT = ROOT / "tasks/cluster_certificates_preflight.yml"
PATRONI_PRESENT = ROOT / "tasks/patroni_present.yml"
BARE_ITEM = re.compile(r"(?<![A-Za-z0-9_.\"'])item(?:\.(?:path|stat|item)|\b)")
SELECTATTR = re.compile(r"selectattr\('([^']+)'\s*,")


def when_text(task):
    value = task.get("when", [])
    return "\n".join(map(str, value if isinstance(value, list) else [value]))


def walk(value):
    if isinstance(value, list):
        for child in value:
            yield from walk(child)
    elif isinstance(value, dict):
        if "loop" in value:
            yield value
        for key in ("block", "rescue", "always"):
            if key in value:
                yield from walk(value[key])


for path in TARGETS:
    document = yaml.safe_load(path.read_text())
    assert isinstance(document, list), path
    text = path.read_text()
    assert not BARE_ITEM.search(text), f"implicit item in {path}: {BARE_ITEM.search(text).group()}"
    for task in walk(document):
        control = task.get("loop_control")
        assert isinstance(control, dict), f"loop without loop_control: {path}:{task.get('name')}"
        loop_var = control.get("loop_var")
        assert isinstance(loop_var, str) and loop_var and loop_var != "item", (
            f"invalid loop_var in {path}:{task.get('name')}"
        )
        rendered = str({key: value for key, value in task.items()
                        if key not in {"loop", "loop_control"}})
        reference_text = rendered
        include = task.get("ansible.builtin.include_tasks")
        if isinstance(include, str) and "{{" not in include:
            reference_text += (path.parent / include).read_text()
        assert loop_var in reference_text, (
            f"loop_var is not referenced in {path}:{task.get('name')}"
        )

# A multi-condition ``when`` must remain a YAML list.  A joined or
# mis-indented condition can silently turn the guard into one expression.
for path, task_name in (
    (ROOT / "tasks/etcd_present.yml", "Checking externally supplied etcd TLS ownership and permissions"),
    (ROOT / "tasks/cluster_certificates_apply.yml", "Inspecting cluster PKI lock directory ACLs before creation"),
):
    task = next(task for task in yaml.safe_load(path.read_text()) if task.get("name") == task_name)
    assert isinstance(task.get("when"), list), f"when must be a list in {path}:{task_name}"
    assert len(task["when"]) == 2, f"conditions must be separate when items in {path}:{task_name}"

cluster = (ROOT / "tasks/cluster_certificates_apply.yml").read_text()
cluster_tasks = yaml.safe_load(cluster)
converge = yaml.safe_load(CLUSTER_CERTIFICATE_CONVERGE.read_text())
normalize = CLUSTER_CERTIFICATE_NORMALIZE.read_text()
cluster_preflight = CLUSTER_CERTIFICATE_PREFLIGHT.read_text()

# A namei rc=1 is safe only for a destination that a successful stat proves
# absent.  Never accept the unconditional rc in [0, 1] shortcut.
assert "rc in [0, 1]" not in cluster
assert "pg_cluster_pki_path_check.failed | default(false) | bool is false" in cluster
assert "pg_cluster_generated_pki_destination_stats.results" in cluster
assert ".failed | default(false) | bool) is false" in cluster
assert ".stat.exists | bool) is false" in cluster

# Generated destinations are an output boundary: an existing destination may
# only be a regular, non-symlink file.  The guard must run before generation,
# copy, or move can mutate it, while an absent destination remains valid only
# with the namei/stat proof.
destination_guard = next(
    task for task in cluster_tasks
    if task.get("name") == "Rejecting unsafe pre-existing generated cluster certificate destinations before mutation"
)
guard_text = str(destination_guard)
assert "stat.isreg" in guard_text and "stat.islnk" in guard_text
assert "pg_cluster_pki_path_checks.results" in guard_text
assert "stat.exists" in guard_text
mutation_names = {
    "Reconciling cluster certificate authority material as one rollback transaction",
    "Generating member certificate request on the seed host",
    "Installing generated etcd cluster CA certificate",
    "Installing generated Patroni cluster CA certificate",
    "Installing generated Patroni REST API certificate pair with rollback journal",
}
task_names = [task.get("name") for task in cluster_tasks]
guard_index = task_names.index(destination_guard["name"])
assert guard_index < min(task_names.index(name) for name in mutation_names)

def generated_destination_is_safe(stat):
    return not stat.get("exists", False) or (
        stat.get("isreg", False) and not stat.get("islnk", False)
    )

assert not generated_destination_is_safe({"exists": True, "isdir": True})
assert generated_destination_is_safe({"exists": False})

# Certificate generation and installation must not run in check mode.  This
# is a boundary assertion rather than a check on individual mutating tasks:
# registered producers in the apply file must never be skipped independently.
apply_include = next(
    task for task in converge
    if task.get("ansible.builtin.include_tasks") == "cluster_certificates_apply.yml"
)
apply_when = when_text(apply_include)
assert "not (ansible_check_mode | bool)" in apply_when

# A certificate member is selected by canonical inventory identity, and an
# alias must fail closed rather than silently selecting a different member.
assert "selectattr('host', 'equalto', inventory_hostname)" in cluster
assert "pg_cluster_local_patroni_members | length == 1" in cluster
assert "pg_cluster_local_etcd_members | length == 1" in cluster
assert "host | default('') == inventory_hostname" in cluster

# Seed and per-member artifacts must use the canonical member.host value, not
# inventory aliases or the controller's current inventory name.
assert "(member.host | regex_replace" in normalize
assert "((member.host | string | hash('sha256'))" in normalize
assert "(member.host | regex_replace" in cluster
assert "((member.host | string | hash('sha256'))" in cluster

# The rendered-file verification is unavailable when template preview leaves
# the destination absent; normal runs retain the complete validation chain.
for task_name in (
    "Reading rendered Patroni configuration for endpoint verification",
    "Parsing rendered Patroni configuration for endpoint verification",
    "Checking rendered Patroni advertised endpoint is canonical",
):
    task = next(task for task in yaml.safe_load(PATRONI_PRESENT.read_text())
                if task.get("name") == task_name)
    task_when = when_text(task)
    assert "not (ansible_check_mode | bool)" in task_when, task_name

# Registered loop results expose the producer's loop value under the producer's
# explicit loop variable, not under an implicit ``item`` alias.
certification = (ROOT / "tasks/certification_preflight.yml").read_text()
certification_tasks = yaml.safe_load(certification)
certification_present_tasks = yaml.safe_load(
    (ROOT / "tasks/certification_present.yml").read_text()
)
external_ancestors = (ROOT / "tasks/validate/validate_external_path_ancestors.yml").read_text()
for selector in (
    "pg_certificate_preflight_tool_result.pg_certificate_preflight_tool_record.key",
    "pg_certificate_preflight_stat_result.pg_certificate_preflight_path",
    "pg_certificate_preflight_acl_target.pg_certificate_preflight_path",
    "pg_certificate_preflight_acl_result.pg_certificate_preflight_acl_target.pg_certificate_preflight_path",
):
    assert selector in certification, f"missing certificate loop-result selector: {selector}"
assert "failed | default(false) | bool is false" in certification
assert "namei_result.rc | default(-1) == 0" in certification
assert "acl_result.rc | default(-1) == 0" in certification
assert "rejectattr('skipped', 'defined')" in certification
assert "pg_certificate_preflight_acl_target.stat.exists" in certification
assert "pg_certificate_generated_destinations" in certification
assert "pg_certificate_preflight_namei_result.item in pg_certificate_generated_destinations" not in certification
assert "pg_certificate_managed_paths" in certification
assert "pg_certificate_generated_destinations | unique | list | length == pg_certificate_generated_destinations | length" in certification
assert "pg_certificate_generated_destinations | intersect(pg_certificate_managed_paths)" in certification
assert "pg_certificate_preflight_paths" in certification
collision_guard = next(
    task for task in certification_tasks
    if task.get("name") == "Rejecting colliding PostgreSQL certificate destinations before inspection"
)
assert certification_tasks.index(collision_guard) < next(
    index for index, task in enumerate(certification_tasks)
    if task.get("name") == "Inspecting PostgreSQL SSL, serial, registry, and destination paths"
)
assert "| trim | length) == 0" in certification
assert "pg_external_path_ancestor_result.stat.gr_name | default('') == pg_external_path_service_group" in external_ancestors
assert "^0[0-7][145][0145]$" in external_ancestors
# Other certificate result mappings retain their explicit contracts.
expected_result_record_selectors = (
    "selectattr('pg_cluster_pki_preflight_stat_result.pg_cluster_pki_preflight_path', 'equalto', pg_cluster_pki_preflight_stat.pg_cluster_pki_preflight_path)",
    "selectattr('pg_cluster_local_pki_stat_result.pg_cluster_local_pki_path', 'equalto', pg_cluster_local_pki_stat.pg_cluster_local_pki_path)",
    "selectattr('pg_cluster_generated_pki_acl_path', 'equalto', pg_cluster_generated_pki_acl_path)",
)
for selector in expected_result_record_selectors:
    assert selector in cluster, f"missing registered-result mapping: {selector}"

# Registered results use the producer task's explicit loop variable as their
# selector key; Ansible does not add an ``item`` alias for custom loop vars.
for selector in (
    "pg_cluster_preflight_acl_target.pg_cluster_preflight_path",
    "pg_cluster_seed_preflight_acl_target.pg_cluster_seed_preflight_path",
):
    assert selector in cluster_preflight, f"missing cluster ACL loop-result selector: {selector}"

# namei returns rc=1 for a missing final path.  That result is safe only when
# the matching stat succeeded and explicitly proves that the target is absent.
for namei_var, stats_var in (
    ("pg_cluster_preflight_namei_result", "pg_cluster_preflight_stats"),
    ("pg_cluster_seed_preflight_namei_result", "pg_cluster_seed_preflight_stats"),
):
    assert f"{namei_var}.rc | default(-1) == 0 or" in cluster_preflight
    assert f"{namei_var}.rc | default(-1) == 1" in cluster_preflight
    assert f"{stats_var}.results" in cluster_preflight
    assert (
        f"selectattr('pg_cluster_{'seed_' if 'seed_' in namei_var else ''}preflight_path', 'equalto', "
        f"{namei_var}.pg_cluster_{'seed_' if 'seed_' in namei_var else ''}preflight_path)"
    ) in cluster_preflight
    assert ".failed | default(false) | bool) is false" in cluster_preflight
    assert ".stat.exists is defined" in cluster_preflight
    assert ".stat.exists | bool) is false" in cluster_preflight

assert "| dirname" in cluster_preflight
assert "stderr | default('') | trim) == ''" in cluster_preflight
assert "ENOTDIR" in cluster_preflight
assert 'pg_cluster_local_preflight_paths: "{{ pg_cluster_preflight_paths }}"' in cluster_preflight
assert "difference(pg_cluster_seed_preflight_paths)" not in cluster_preflight
assert 'delegate_to: "{{ pg_cluster_local_preflight_host }}"' in cluster_preflight


def namei_rc_is_safe(namei_result, stat_results):
    """Model the fail-closed rc=1 exception covered by the task assertions."""
    path = namei_result.get("pg_certificate_preflight_path")
    matching = [
        record for record in stat_results
        if record.get("pg_certificate_preflight_path") == path
    ]
    parent_path = "/".join(path.rstrip("/").split("/")[:-1]) or "/"
    parents = [
        record for record in stat_results
        if record.get("pg_certificate_preflight_path") == parent_path
    ]
    return (
        not namei_result.get("failed", False)
        and not namei_result.get("stderr", "").strip()
        and (
            namei_result.get("rc", -1) == 0
            or (
                namei_result.get("rc", -1) == 1
                and len(matching) == 1
                and not matching[0].get("failed", False)
                and matching[0].get("stat", {}).get("exists") is False
                and len(parents) == 1
                and not parents[0].get("failed", False)
                and parents[0].get("stat", {}).get("exists") is True
                and parents[0].get("stat", {}).get("isdir") is True
                and not parents[0].get("stat", {}).get("islnk", False)
            )
        )
    )


assert not namei_rc_is_safe(
    {"pg_certificate_preflight_path": "/missing", "rc": 1},
    [{"pg_certificate_preflight_path": "/missing", "failed": True, "stat": {"exists": False}}],
)
assert namei_rc_is_safe(
    {"pg_certificate_preflight_path": "/missing", "rc": 1},
    [
        {"pg_certificate_preflight_path": "/missing", "failed": False, "stat": {"exists": False}},
        {"pg_certificate_preflight_path": "/", "failed": False, "stat": {"exists": True, "isdir": True}},
    ],
)
assert not namei_rc_is_safe(
    {"pg_certificate_preflight_path": "/missing", "rc": 1},
    [
        {"pg_certificate_preflight_path": "/missing", "failed": False, "stat": {"exists": False}},
        {"pg_certificate_preflight_path": "/missing", "failed": False, "stat": {"exists": False}},
    ],
)

path_proof_cases = json.loads(
    (ROOT / "scripts/fixtures/cluster_certificate_path_proof.json").read_text()
)
for case in path_proof_cases:
    assert namei_rc_is_safe(case["namei"], case["stats"]) == case["safe"], case["name"]

# Standalone certification has a strict read-only boundary.  Its completion
# gate must be encountered before the convergence include, with no named
# mutation task before that gate.
preflight_names = [str(task.get("name", "")) for task in certification_tasks]
assert preflight_names[-1] == "PREFLIGHT COMPLETE - all PostgreSQL certificate paths are safe"
assert all(
    not any(module in str(task) for module in ("ansible.builtin.file", "ansible.builtin.copy", "ansible.builtin.template", "ansible.builtin.shell"))
    for task in certification_tasks
), "standalone certification preflight contains a mutation task"
present_names = [str(task.get("name", "")) for task in certification_present_tasks]
gate = present_names.index("Checking published PostgreSQL certificate preflight model")
converge = present_names.index("PREFLIGHT COMPLETE - converge PostgreSQL certificate pair")
assert gate < converge, "standalone certification convergence precedes its preflight gate"
assert not any(
    any(word in name.lower() for word in ("ensuring", "installing", "reconciling", "restricting", "creating", "removing"))
    for name in present_names[:gate]
), "named certification mutation precedes standalone preflight"

for attribute in SELECTATTR.findall(cluster):
    assert attribute in {
        "item", "key", "member", "host", "cluster", "version",
        "pg_cluster_pki_preflight_stat_result.pg_cluster_pki_preflight_path",
        "pg_cluster_local_pki_stat_result.pg_cluster_local_pki_path",
        "pg_cluster_generated_pki_acl_path", "pg_cluster_generated_pki_destination",
        "pg_cluster_pki_path",
    }, (
        f"selectattr uses a non-result or unverified attribute {attribute!r}"
    )

# Every ACL cleanup must consume the matching registered command result, be
# skipped in check mode, and use the same path loop as the cleanup command.
acl_cleanup = next(
    task for task in yaml.safe_load(cluster)
    if task.get("name") == "Removing inherited default ACLs from generated PKI directories"
)
cleanup_when = "\n".join(str(value) for value in acl_cleanup["when"])
assert acl_cleanup["loop"] == "{{ pg_cluster_generated_pki_destinations | map('dirname') | unique | list }}"
assert acl_cleanup["loop_control"]["loop_var"] == "pg_cluster_generated_pki_acl_path"
assert "pg_cluster_generated_pki_acl_before_removal.results" in cleanup_when
assert "selectattr('pg_cluster_generated_pki_acl_path', 'equalto', pg_cluster_generated_pki_acl_path)" in cleanup_when
assert "not ansible_check_mode" in cleanup_when

print("certificate loop-scope guardrails passed")
