#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
dockerfile=$root/molecule/replication/Dockerfile.j2
molecule_file=$root/molecule/replication/molecule.yml
ci_file=$root/.github/workflows/tests.yml
prepare_file=$root/molecule/replication/prepare.yml
provenance_helper=$root/scripts/replication_image_provenance.py
normalize_helper=$root/scripts/replication_image_normalize.sh
package_normalize_helper=$root/scripts/replication_package_normalize.sh
selected_python=${REPLICATION_PYTHON_COMMAND:-/home/arsi/.local/share/venvs/idarsi-ansible-testing/bin/python}
repo_digest_fixture=$root/scripts/fixtures/replication_base_repo_digests_podman.txt
derived_without_repo_digests_fixture=$root/scripts/fixtures/replication_derived_without_repo_digests.json
derived_distinct_repo_digest_fixture=$root/scripts/fixtures/replication_derived_with_distinct_repo_digest.json
rootful_runtime_fixture=$root/scripts/fixtures/replication_rootful_runtime.json
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

[ -x "$selected_python" ] || {
  printf '%s\n' "replication image guardrail failed: selected interpreter is not executable: $selected_python" >&2
  exit 1
}

# Keep every replication command surface on the same interpreter contract.
# Ignore this guardrail's explanatory text and the runtime resolver's
# documented system candidates; reject executable Python bypasses elsewhere.
"$selected_python" - "$root" <<'PY'
from pathlib import Path
import re
import sys

root = Path(sys.argv[1])
files = [
    root / "tasks/replication_present.yml",
    root / "molecule/replication/molecule.yml",
    root / "molecule/replication/prepare.yml",
    root / "molecule/replication/converge.yml",
    root / "molecule/replication/verify.yml",
    root / "molecule/replication/cleanup.yml",
    root / "scripts/replication_molecule.sh",
    root / "scripts/replication_image_guardrails_test.sh",
]
bypass = re.compile(r"(?:^|[|;&(]\s*)(?:python3|/usr/bin/python3)(?:\s|$)")
for path in files:
    for number, line in enumerate(path.read_text().splitlines(), 1):
        if path.name == "replication_image_guardrails_test.sh" and "command -v (molecule|python3)" in line:
            continue
        if bypass.search(line.split("#", 1)[0]):
            raise SystemExit(f"replication interpreter bypass in {path}:{number}")
print("replication interpreter contract scan: PASS")
PY

assert_contains() {
  needle=$1
  if ! grep -F -- "$needle" "$dockerfile" >/dev/null; then
    printf 'replication image guardrail failed: missing %s\n' "$needle" >&2
    exit 1
  fi
}

assert_file_contains() {
  file=$1
  needle=$2
  if ! grep -F -- "$needle" "$file" >/dev/null; then
    printf 'replication image guardrail failed: missing %s in %s\n' "$needle" "$file" >&2
    exit 1
  fi
}

assert_file_line_order() {
  file=$1
  first=$2
  second=$3
  first_line=$(grep -nF -- "$first" "$file" | awk -F: 'NR == 1 { print $1; exit }')
  second_line=$(grep -nF -- "$second" "$file" | awk -F: 'NR == 1 { print $1; exit }')
  [ -n "$first_line" ] && [ -n "$second_line" ] && [ "$first_line" -lt "$second_line" ] || {
    printf 'replication image guardrail failed: %s must precede %s in %s\n' "$first" "$second" "$file" >&2
    exit 1
  }
}

assert_replication_provenance_guard_precedes_commands() {
  file=$1
  # Do not use the assertion's fail_msg as an ordering marker.  Parse the task
  # structure so a comment, a weak assertion, or a later assertion cannot make
  # a command look guarded.  This also covers future containers.podman.* tasks.
  "$selected_python" - "$file" <<'PY'
import re
import sys

import yaml


path = sys.argv[1]
with open(path, encoding="utf-8") as stream:
    document = yaml.safe_load(stream)


def tasks_from(value):
    if isinstance(value, list):
        for entry in value:
            yield from tasks_from(entry)
    elif isinstance(value, dict):
        for key in ("tasks", "block", "rescue", "always"):
            if key in value:
                yield from tasks_from(value[key])
        # A task itself is yielded only when it has a task name or a module.
        if "name" in value or any("." in str(key) or key in {"command", "shell", "assert"} for key in value):
            yield value


tasks = list(tasks_from(document))


def compact(value):
    return re.sub(r"\s+", " ", str(value)).strip()


rootless_inspection_name = "Inspect the resolved Podman runtime security"
rootless_assertion_name = "Require a rootless Podman runtime"
rootless_inspection_positions = [
    position for position, task in enumerate(tasks)
    if task.get("name") == rootless_inspection_name
]
rootless_assertion_positions = [
    position for position, task in enumerate(tasks)
    if task.get("name") == rootless_assertion_name
]
if len(rootless_inspection_positions) != 1 or len(rootless_assertion_positions) != 1:
    raise SystemExit("expected exactly one structural rootless Podman runtime guard")
rootless_inspection_position = rootless_inspection_positions[0]
rootless_assertion_position = rootless_assertion_positions[0]
if rootless_inspection_position >= rootless_assertion_position:
    raise SystemExit("rootless Podman assertion must follow runtime inspection")
rootless_assertion = tasks[rootless_assertion_position].get("ansible.builtin.assert", {})
if "(pg_replication_podman_rootless.stdout | trim | from_json) is sameas true" not in {
    compact(predicate) for predicate in rootless_assertion.get("that", [])
}:
    raise SystemExit("rootless Podman assertion must require JSON true")
required_assertion_name = "Require canonical replication base-image provenance inputs"
required_predicates = {
    "pg_replication_base_image_id is defined",
    "pg_replication_base_image_id is string",
    "pg_replication_base_image_id | length > 0",
    'pg_replication_base_image_id is match("^sha256:[0-9a-f]{64}$")',
    "pg_replication_base_repo_digest is defined",
    "pg_replication_base_repo_digest is string",
    "pg_replication_base_repo_digest | length > 0",
    r'pg_replication_base_repo_digest is match( "^docker\\.io/rockylinux/rockylinux:9-ubi-init@sha256:[0-9a-f]{64}$")',
    'pg_replication_base_repo_digest == pg_replication_image_name ~ "@" ~ pg_replication_image_digest',
}
def is_exact_base_assertion(task):
    assertion = task.get("ansible.builtin.assert")
    if task.get("name") != required_assertion_name or not isinstance(assertion, dict):
        return False
    predicates = {compact(predicate) for predicate in assertion.get("that", [])}
    if not required_predicates.issubset(predicates):
        # The repository's folded YAML expression may have a space after '('.
        predicates_without_call_spacing = {predicate.replace("match( ", "match(") for predicate in predicates}
        expected = {predicate.replace("match( ", "match(") for predicate in required_predicates}
        if not expected.issubset(predicates_without_call_spacing):
            return False
    fail_msg = compact(assertion.get("fail_msg", ""))
    return "canonical sha256 image ID" in fail_msg and "exact pinned Rocky base reference with digest" in fail_msg


guard_positions = [position for position, task in enumerate(tasks) if is_exact_base_assertion(task)]
if len(guard_positions) != 1:
    raise SystemExit("expected exactly one structural exact base metadata assertion")
guard_position = guard_positions[0]

for position, task in enumerate(tasks):
    module_names = set(task).intersection({"command", "shell", "ansible.builtin.command", "ansible.builtin.shell"})
    module_names.update(key for key in task if str(key).startswith("containers.podman."))
    if module_names and position <= guard_position and position != rootless_inspection_position:
        raise SystemExit("a command, shell, or containers.podman.* task precedes the exact base metadata assertion")
PY
}

assert_contains 'FROM --platform=linux/amd64 docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
test -f "$dockerfile" || { printf '%s\n' 'replication image guardrail failed: Dockerfile build fixture is missing' >&2; exit 1; }
assert_file_contains "$molecule_file" 'image: docker.io/rockylinux/rockylinux:9-ubi-init'
platform_count=$(grep -Foc 'image: docker.io/rockylinux/rockylinux:9-ubi-init' "$molecule_file")
[ "$platform_count" -eq 2 ] || { printf '%s\n' 'replication image guardrail failed: both replication platforms must define images' >&2; exit 1; }
[ "$(grep -Foc 'pre_build_image: false' "$molecule_file")" -eq 2 ] || {
  printf '%s\n' 'replication image guardrail failed: both replication platforms must disable pre-built images' >&2
  exit 1
}
for platform in instance-idarsi-rl9-primary instance-idarsi-rl9-standby; do
  platform_prebuild=$(awk -v target="$platform" '
    $0 ~ "name: " target "$" { in_platform=1; next }
    in_platform && /^[[:space:]]+- name:/ { exit }
    in_platform && /pre_build_image: false/ { found=1 }
    END { print found + 0 }
  ' "$molecule_file")
  [ "$platform_prebuild" -eq 1 ] || {
    printf 'replication image guardrail failed: %s is not wired to build its image\n' "$platform" >&2
    exit 1
  }
done
assert_contains '21CB256AE16FC54C6E652949702D426D350D275D'
assert_contains 'primary_fingerprints='
assert_contains 'test "${primary_fingerprints}" = "21CB256AE16FC54C6E652949702D426D350D275D" || {'
assert_contains "awk -F: '\$1 == \"pub\""
assert_contains "--disablerepo='*'"
assert_contains "--enablerepo='rocky-9.8-baseos,rocky-9.8-appstream,rocky-9.8-extras'"
assert_contains 'unexpected effective Rocky repository set'
assert_contains 'ca-certificates gnupg2'
assert_contains 'test -x "$(command -v curl)"'
assert_contains 'curl-minimal'
assert_contains '--whatprovides /usr/bin/curl'
if grep -Eq '^[[:space:]]+ca-certificates curl([[:space:]\\]|$)' "$dockerfile"; then
  printf '%s\n' 'replication image guardrail failed: curl must not be installed over curl-minimal' >&2
  exit 1
fi
assert_contains 'awk '\''$1 == "repo" { header=1; next } header && $1 != "repolist:" && NF { print $1 }'\'' | sort'
if grep -Eq 'ca-certificates[^[:space:]]*\*|curl-[^[:space:]]*\*|gnupg2-[^[:space:]]*\*' "$dockerfile"; then
  printf '%s\n' 'replication image guardrail failed: wildcard package specifications are not valid provenance pins' >&2
  exit 1
fi
assert_contains 'mkdir -p /etc/yum.repos.d.disabled'
assert_contains 'mv -- "${repo}" /etc/yum.repos.d.disabled/'
if grep -Eq '^[[:space:]]+architecture:' "$molecule_file"; then
  printf '%s\n' 'replication image guardrail failed: unsupported Molecule platform architecture key found' >&2
  exit 1
fi
assert_file_contains "$ci_file" 'test "$(uname -m)" = x86_64 || {'
assert_file_contains "$ci_file" '. scripts/replication_runtime.sh'
assert_file_contains "$ci_file" 'replication_runtime_preflight'
assert_file_contains "$ci_file" '${pythonLocation}/bin/python'
assert_file_contains "$ci_file" '${pythonLocation}/bin/molecule'
if grep -Eq 'command -v (molecule|python3)|python_command=.*command -v|molecule_command=.*command -v' "$ci_file"; then
  printf '%s\n' 'replication image guardrail failed: replication runtime must not use PATH shadowing' >&2
  exit 1
fi
assert_file_contains "$ci_file" 'test "$("${REPLICATION_PODMAN_COMMAND}" info --format '\''{{.Host.Arch}}'\'')" = amd64 || {'
assert_file_line_order "$ci_file" 'Require native amd64 replication host and Podman before image build' 'Run Molecule scenario'
ci_check_line=$(grep -nF 'Require native amd64 replication host and Podman before image build' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
ci_host_check_line=$(grep -nF 'test "$(uname -m)" = x86_64 || {' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
ci_runtime_check_line=$(grep -nF 'test "$("${REPLICATION_PODMAN_COMMAND}" info --format '\''{{.Host.Arch}}'\'')" = amd64 || {' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
ci_run_line=$(grep -nF 'scripts/replication_molecule.sh' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
ci_image_line=$(grep -nF 'Pull and record the exact Rocky base image before build' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
ci_provenance_line=$(grep -nF 'MOLECULE_REPLICATION_BASE_REPO_DIGEST' "$ci_file" | awk -F: 'NR == 2 { print $1; exit }')
[ -n "$ci_check_line" ] && [ -n "$ci_host_check_line" ] && [ -n "$ci_runtime_check_line" ] && \
  [ -n "$ci_image_line" ] && [ -n "$ci_provenance_line" ] && [ -n "$ci_run_line" ] && \
  [ "$ci_host_check_line" -lt "$ci_run_line" ] && \
  [ "$ci_runtime_check_line" -lt "$ci_run_line" ] && \
  [ "$ci_image_line" -lt "$ci_run_line" ] && \
  [ "$ci_provenance_line" -lt "$ci_run_line" ] || {
  printf '%s\n' 'replication image guardrail failed: CI preflight, image pull, and provenance must precede the launcher' >&2
  exit 1
}
assert_file_contains "$prepare_file" '          - uname'
assert_file_contains "$prepare_file" '          - info'
assert_file_contains "$prepare_file" 'pg_replication_podman_executable'
assert_file_contains "$prepare_file" '- container'
assert_file_contains "$prepare_file" '- image'
assert_file_contains "$prepare_file" 'RepoDigests'
assert_file_contains "$prepare_file" 'replication_image_provenance.py'
assert_file_contains "$prepare_file" 'follow: false'
assert_file_contains "$prepare_file" 'pg_replication_provenance_helper_stat.stat.islnk'
assert_file_contains "$prepare_file" '--base-json'
assert_file_contains "$prepare_file" '--derived-json'
assert_file_contains "$prepare_file" '--normalize-json'
assert_file_contains "$prepare_file" '.Host.Security.Rootless'
assert_file_contains "$prepare_file" 'from_json) is sameas true'
test -f "$rootful_runtime_fixture" || {
  printf '%s\n' 'replication image guardrail failed: rootful runtime fixture is missing' >&2
  exit 1
}
"$selected_python" - "$rootful_runtime_fixture" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    runtime = json.load(stream)
assert runtime["Host"]["Security"]["Rootless"] is False
print("rootful Podman rejection fixture: PASS")
PY
assert_replication_provenance_guard_precedes_commands "$prepare_file"
assert_file_line_order "$prepare_file" 'Require a rootless Podman runtime' 'Inspect the exact pulled Rocky base image provenance'
assert_file_line_order "$prepare_file" 'Require a rootless Podman runtime' 'Inspect replication image provenance and architecture'
assert_file_line_order "$prepare_file" 'Require a rootless Podman runtime' 'Inspect replication container network attachments'
cat >"$tmp/negative-prepare.yml" <<'EOF'
- name: "Require an amd64 controller and Podman runtime"
  ansible.builtin.shell: "podman info"
- name: "Require canonical replication base-image provenance inputs"
  ansible.builtin.assert:
    that:
      - pg_replication_base_image_id is defined
    fail_msg: "ID and the exact pinned Rocky base reference with digest"
EOF
if assert_replication_provenance_guard_precedes_commands "$tmp/negative-prepare.yml"; then
  printf '%s\n' 'replication image guardrail failed: negative ordering fixture was accepted' >&2
  exit 1
fi
cat >"$tmp/module-before-guard.yml" <<'EOF'
- name: "Run a command before the provenance guard"
  ansible.builtin.command: "true"
- name: "Require canonical replication base-image provenance inputs"
  ansible.builtin.assert:
    that:
      - pg_replication_base_image_id is defined
      - pg_replication_base_image_id is string
      - pg_replication_base_image_id | length > 0
      - pg_replication_base_image_id is match("^sha256:[0-9a-f]{64}$")
      - pg_replication_base_repo_digest is defined
      - pg_replication_base_repo_digest is string
      - pg_replication_base_repo_digest | length > 0
      - pg_replication_base_repo_digest is match("^docker\\.io/rockylinux/rockylinux:9-ubi-init@sha256:[0-9a-f]{64}$")
      - pg_replication_base_repo_digest == pg_replication_image_name ~ "@" ~ pg_replication_image_digest
    fail_msg: "Replication base-image provenance must provide a canonical sha256 image ID and the exact pinned Rocky base reference with digest"
EOF
if assert_replication_provenance_guard_precedes_commands "$tmp/module-before-guard.yml"; then
  printf '%s\n' 'replication image guardrail failed: command-before-guard fixture was accepted' >&2
  exit 1
fi
cat >"$tmp/podman-module-before-guard.yml" <<'EOF'
- name: "Run a Podman module before the provenance guard"
  containers.podman.podman_container:
    name: "example"
- name: "Require canonical replication base-image provenance inputs"
  ansible.builtin.assert:
    that:
      - pg_replication_base_image_id is defined
      - pg_replication_base_image_id is string
      - pg_replication_base_image_id | length > 0
      - pg_replication_base_image_id is match("^sha256:[0-9a-f]{64}$")
      - pg_replication_base_repo_digest is defined
      - pg_replication_base_repo_digest is string
      - pg_replication_base_repo_digest | length > 0
      - pg_replication_base_repo_digest is match("^docker\\.io/rockylinux/rockylinux:9-ubi-init@sha256:[0-9a-f]{64}$")
      - pg_replication_base_repo_digest == pg_replication_image_name ~ "@" ~ pg_replication_image_digest
    fail_msg: "Replication base-image provenance must provide a canonical sha256 image ID and the exact pinned Rocky base reference with digest"
EOF
if assert_replication_provenance_guard_precedes_commands "$tmp/podman-module-before-guard.yml"; then
  printf '%s\n' 'replication image guardrail failed: containers.podman-before-guard fixture was accepted' >&2
  exit 1
fi
assert_file_contains "$dockerfile" 'normalize_replication_iproute_nevra()'
test -f "$package_normalize_helper" || { printf '%s\n' 'replication image guardrail failed: package normalization helper is missing' >&2; exit 1; }
test -f "$provenance_helper" || { printf '%s\n' 'replication image guardrail failed: provenance helper is missing' >&2; exit 1; }
test -f "$derived_without_repo_digests_fixture" || { printf '%s\n' 'replication image guardrail failed: derived no-RepoDigests fixture is missing' >&2; exit 1; }
test -f "$derived_distinct_repo_digest_fixture" || { printf '%s\n' 'replication image guardrail failed: derived distinct-RepoDigest fixture is missing' >&2; exit 1; }
assert_file_contains "$ci_file" '"${REPLICATION_PODMAN_COMMAND}" pull --quiet "${base_ref}"'
assert_file_contains "$ci_file" 'MOLECULE_REPLICATION_BASE_IMAGE_ID'
assert_file_contains "$ci_file" 'MOLECULE_REPLICATION_BASE_REPO_DIGEST'
assert_file_contains "$ci_file" 'validate_replication_base_repo_digests'
assert_file_contains "$root/scripts/replication_molecule.sh" 'validate_replication_base_repo_digests'
[ "$(grep -Foc 'Pull and record the exact Rocky base image before build' "$ci_file")" -eq 2 ] || {
  printf '%s\n' 'replication image guardrail failed: exact base pull must precede both possible replication builds' >&2
  exit 1
}
assert_file_line_order "$ci_file" 'Pull and record the exact Rocky base image before build' 'Run Molecule scenario'

# The image cannot source a controller-side file during its build. Keep its
# self-contained copy byte-for-byte identical to the shared helper function so
# the build and prepare.yml cannot silently acquire different acceptance rules.
docker_normalizer=$(awk '/^normalize_replication_iproute_nevra\(\) \{/{capture=1} capture {print} capture && /^\}$/{exit}' "$dockerfile")
shared_normalizer=$(awk '/^normalize_replication_iproute_nevra\(\) \{/{capture=1} capture {print} capture && /^\}$/{exit}' "$package_normalize_helper")
[ -n "$docker_normalizer" ] && [ "$docker_normalizer" = "$shared_normalizer" ] || {
  printf '%s\n' 'replication image guardrail failed: Dockerfile package normalizer drifted from shared helper' >&2
  exit 1
}

# The shared normalization must accept only the exact observed aliases and reject
# every single-alias, alternate-alias, or extra-entry form.
replication_base_ref='docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
replication_expected_digest="sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
. "$normalize_helper"
test -f "$repo_digest_fixture" || { printf '%s\n' 'replication image guardrail failed: exact Podman RepoDigests fixture is missing' >&2; exit 1; }
validate_replication_base_repo_digests <"$repo_digest_fixture" | grep -Fx "$replication_base_ref" >/dev/null || {
  printf '%s\n' 'replication image guardrail failed: exact Podman RepoDigests fixture was rejected' >&2
  exit 1
}
printf '%s\n' \
  'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' |
  validate_replication_base_repo_digests | grep -Fx "$replication_base_ref" >/dev/null || {
   printf '%s\n' 'replication image guardrail failed: exact shell aliases were rejected' >&2
   exit 1;
 }
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
   printf '%s\n' 'replication image guardrail failed: single untagged alias was accepted' >&2
   exit 1;
 fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' |
  validate_replication_base_repo_digests >/dev/null; then
   printf '%s\n' 'replication image guardrail failed: single d706 alias was accepted' >&2
   exit 1;
 fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
   printf '%s\n' 'replication image guardrail failed: tagged pulled reference was accepted as RepoDigest' >&2
   exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' |
  validate_replication_base_repo_digests >/dev/null; then
   printf '%s\n' 'replication image guardrail failed: short tagged alias was accepted' >&2
   exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: multiple non-equivalent aliases were accepted' >&2
  exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
   printf '%s\n' 'replication image guardrail failed: four equivalent shell aliases were accepted' >&2
  exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: duplicate shell aliases were accepted' >&2
  exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
  'docker.io/example/extra@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: unexpected shell RepoDigests entry was accepted' >&2
  exit 1
fi
if printf '%s\n\n' \
   'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: trailing newline shell fixture was accepted' >&2
  exit 1
fi
if printf '%s\n' \
  'docker.io/rockylinux/rockylinux:9-ubi@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: different-tag shell fixture was accepted' >&2
  exit 1
fi
if printf '%s\n' \
  'docker.io/example/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' |
  validate_replication_base_repo_digests >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: different-repository shell fixture was accepted' >&2
  exit 1
fi

# Exercise the exact comparator used by prepare.yml, including a matching
# label with a mismatched layer chain. This must fail independently of labels.
base_json='{"Id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":["docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5","docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4"],"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
canonical_base_json=$("$selected_python" "$provenance_helper" --normalize-json "$base_json")
printf '%s' "$canonical_base_json" | "$selected_python" -c 'import json,sys; digests=json.load(sys.stdin)["RepoDigests"]; assert len(digests) == 2 and all(d.startswith("docker.io/rockylinux/rockylinux@sha256:") for d in digests)'
matching_json='{"Id":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","Config":{"Labels":{"io.idarsi.replication.base-digest":"expected"}},"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111","sha256:3333333333333333333333333333333333333333333333333333333333333333"]}}'
mismatched_json='{"Id":"sha256:dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd","Config":{"Labels":{"io.idarsi.replication.base-digest":"expected"}},"RootFS":{"Layers":["sha256:2222222222222222222222222222222222222222222222222222222222222222","sha256:3333333333333333333333333333333333333333333333333333333333333333"]}}'
"$selected_python" "$provenance_helper" --base-json "$canonical_base_json" --derived-json "$matching_json" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
# The shared comparator accepts the exact untagged aliases while requiring the
# tagged pinned reference independently; prepare.yml normalizes the artifact.
"$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$matching_json" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
# Derived RepoDigests are independent metadata: both absent and unrelated
# derived aliases must pass while the base aliases remain strictly checked.
"$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$(cat "$derived_without_repo_digests_fixture")" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
"$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$(cat "$derived_distinct_repo_digest_fixture")" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'
"$selected_python" - "$provenance_helper" <<'PY'
import importlib.util
import sys

spec = importlib.util.spec_from_file_location("provenance", sys.argv[1])
provenance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provenance)
assert provenance.normalize_digest("a" * 64) == "sha256:" + "a" * 64
assert provenance.normalize_repo_digest(provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST) == provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST
assert provenance.normalize_repo_digest(
    provenance.OBSERVED_EQUIVALENT_REPO_DIGEST
) == provenance.OBSERVED_EQUIVALENT_REPO_DIGEST
assert provenance.normalize_repo_digest(
    provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST
) == provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST
assert provenance.normalize_repo_digests([
    provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST,
    provenance.OBSERVED_EQUIVALENT_REPO_DIGEST,
], "base") == [provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST, provenance.OBSERVED_EQUIVALENT_REPO_DIGEST]
for aliases, message in [
    (["docker.io/rockylinux/rockylinux@sha256:" + "b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"], "untagged-only b33d"),
    ([provenance.OBSERVED_EQUIVALENT_REPO_DIGEST], "untagged-only d706"),
    ([provenance.OBSERVED_EQUIVALENT_REPO_DIGEST], "missing untagged b33d"),
    ([provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST] * 2, "duplicate aliases"),
    ([provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST,
      provenance.OBSERVED_EQUIVALENT_REPO_DIGEST,
      provenance.OBSERVED_EQUIVALENT_REPO_DIGEST], "extra alias"),
    ([provenance.EXPECTED_REPO_DIGEST,
      provenance.OBSERVED_EQUIVALENT_REPO_DIGEST], "tagged pulled reference"),
]:
    try:
        provenance.normalize_repo_digests(aliases, "base")
    except ValueError:
        pass
    else:
        raise AssertionError(message + " were accepted")
try:
    provenance.normalize_repo_digests([
        provenance.OBSERVED_UNTAGGED_B33D_REPO_DIGEST,
        "docker.io/rockylinux/rockylinux@sha256:" + "c" * 64,
    ], "base")
except ValueError:
    pass
else:
    raise AssertionError("non-equivalent RepoDigests aliases were accepted")
assert provenance.normalize_repo_digest(provenance.EXPECTED_REPO_DIGEST) is None
assert provenance.normalize_repo_digest(
    "docker.io/example/rockylinux:9-ubi-init@sha256:" + "b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
) is None
assert provenance.normalize_repo_digest(
    "rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4"
) is None
PY
invalid_repo_json='{"Id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":["not-a-repo-digest"],"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
unexpected_repo_json='{"Id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":["docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5","docker.io/example/extra@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"],"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
null_repo_json='{"Id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":null,"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
scalar_repo_json='{"Id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":"docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5","RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
empty_repo_json='{"Id":"sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","RepoDigests":[],"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111"]}}'
invalid_layers_json='{"Id":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","RootFS":{"Layers":["sha256:not-a-digest"]}}'
if "$selected_python" "$provenance_helper" --base-json "$invalid_repo_json" --derived-json "$matching_json" --base-id 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
  printf '%s\n' 'replication image guardrail failed: malformed RepoDigests fixture was accepted' >&2
  exit 1
fi
if "$selected_python" "$provenance_helper" --base-json "$unexpected_repo_json" --derived-json "$matching_json" --base-id 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
  printf '%s\n' 'replication image guardrail failed: unexpected RepoDigests fixture was accepted' >&2
  exit 1
fi
for invalid_repo_fixture in null_repo_json scalar_repo_json empty_repo_json; do
  eval "invalid_repo=\${$invalid_repo_fixture}"
  if "$selected_python" "$provenance_helper" --base-json "$invalid_repo" --derived-json "$matching_json" --base-id 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
    printf 'replication image guardrail failed: %s RepoDigests fixture was accepted\n' "$invalid_repo_fixture" >&2
    exit 1
  fi
done
if "$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$invalid_layers_json" --base-id 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
  printf '%s\n' 'replication image guardrail failed: malformed RootFS.Layers fixture was accepted' >&2
  exit 1
fi
if "$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$matching_json" --base-id 'not-an-image-id' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
  printf '%s\n' 'replication image guardrail failed: malformed base ID fixture was accepted' >&2
  exit 1
fi
if "$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$mismatched_json" --base-id 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'; then
  printf '%s\n' 'replication image guardrail failed: mismatched layer fixture was accepted' >&2
  exit 1
fi
if "$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$matching_json" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'; then
  printf '%s\n' 'replication image guardrail failed: wrong pinned digest was accepted' >&2
  exit 1
fi
malformed_extra_derived_json='{"Id":"sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","RepoDigests":["docker.io/example/derived@sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc","malformed-extra"],"RootFS":{"Layers":["sha256:1111111111111111111111111111111111111111111111111111111111111111","sha256:3333333333333333333333333333333333333333333333333333333333333333"]}}'
# Even malformed derived RepoDigests are outside the base provenance claim;
# identity, labels, and the fail-closed layer prefix are the derived checks.
"$selected_python" "$provenance_helper" --base-json "$base_json" --derived-json "$malformed_extra_derived_json" --base-id 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' --repo-digest 'docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5'

# The implementation uses argv entries (podman container inspect --format),
# not a shell literal.  Check the command semantics so harmless YAML/layout
# changes do not weaken this guardrail.
if ! awk '
  /pg_replication_podman_executable/ { podman=1; container=0; inspect=0; format=0; next }
  podman && /- container[[:space:]]*$/ { container=1; next }
  podman && container && /- inspect[[:space:]]*$/ { inspect=1; next }
  podman && container && inspect && /- --format[[:space:]]*$/ { format=1; exit }
  podman && /^[[:space:]]+- name:/ { podman=0 }
  END { exit !(podman && container && inspect && format) }
' "$prepare_file"; then
  printf '%s\n' 'replication image guardrail failed: container image inspection must use podman container inspect with --format' >&2
  exit 1
fi
assert_file_line_order "$prepare_file" 'Require an amd64 controller and Podman runtime' 'Inspect replication container network attachments'
assert_file_line_order "$prepare_file" 'Require amd64 Rocky replication images and exact package' 'Inspect replication container network attachments'
assert_file_line_order "$prepare_file" 'Inspect replication container network attachments' 'Require the exact default Podman network mapping'
assert_file_contains "$molecule_file" '"--network=podman"'
if grep -Eq '^[[:space:]]+network:' "$molecule_file"; then
  printf '%s\n' 'replication image guardrail failed: Molecule platform network must remain unset' >&2
  exit 1
fi
assert_contains 'baseurl=https://dl.rockylinux.org/pub/rocky/9.8/BaseOS/$basearch/os/'
assert_contains 'baseurl=https://dl.rockylinux.org/pub/rocky/9.8/AppStream/$basearch/os/'
assert_contains 'baseurl=https://dl.rockylinux.org/pub/rocky/9.8/extras/$basearch/os/'
assert_contains 'gpgkey=https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9'
assert_contains "iproute-0:6.17.0-2.el9.x86_64"
assert_contains "iproute-0:6.17.0-2.el9.x86_64"
assert_file_contains "$prepare_file" '          - uname'
assert_file_contains "$prepare_file" '          - --qf'
assert_contains "'sslverify=1'"
assert_contains "'gpgcheck=1'"
assert_contains "'repo_gpgcheck=1'"

for setting in sslverify=1 gpgcheck=1 repo_gpgcheck=1; do
  count=$(grep -Foc "'$setting'" "$dockerfile")
  [ "$count" -eq 3 ] || {
    printf 'replication image guardrail failed: expected %s in all repositories\n' "$setting" >&2
    exit 1
  }
done
[ "$(grep -Fc 'baseurl=https://dl.rockylinux.org/pub/rocky/9.8/' "$dockerfile")" -eq 3 ]
[ "$(grep -Fc 'gpgkey=https://dl.rockylinux.org/pub/rocky/RPM-GPG-KEY-Rocky-9' "$dockerfile")" -eq 3 ]
[ "$(grep -Foc -- "--disablerepo='*'" "$dockerfile")" -eq 2 ] || {
  printf '%s\n' 'replication image guardrail failed: DNF operations are not repository-isolated' >&2
  exit 1
}
[ "$(grep -Foc -- "--enablerepo='rocky-9.8-baseos,rocky-9.8-appstream,rocky-9.8-extras'" "$dockerfile")" -eq 2 ] || {
  printf '%s\n' 'replication image guardrail failed: DNF operations do not select pinned repositories' >&2
  exit 1
}

. "$package_normalize_helper"
package_expected='iproute-0:6.17.0-2.el9.x86_64'
replication_newline=$(printf '\nX')
replication_newline=${replication_newline%X}
for package_fixture in \
  "$root/scripts/fixtures/replication_iproute_rpm_with_epoch.txt" \
  "$root/scripts/fixtures/replication_iproute_rpm_without_epoch.txt" \
  "$root/scripts/fixtures/replication_iproute_rpm_with_none_epoch.txt"; do
  test -f "$package_fixture" || { printf 'replication image guardrail failed: missing package fixture %s\n' "$package_fixture" >&2; exit 1; }
  "$selected_python" - "$package_fixture" <<'PY'
from pathlib import Path
import sys

assert Path(sys.argv[1]).read_bytes().endswith(b"\n"), sys.argv[1]
PY
  # Command substitution removes trailing newlines.  Re-attach the fixture's
  # record terminator explicitly so this test exercises the shared normalizer's
  # single-record newline acceptance rather than the runtime's stripped value.
  package_actual=$(cat "$package_fixture")
  package_actual=${package_actual}${replication_newline}
  [ "$(normalize_replication_iproute_nevra "$package_expected" "$package_actual")" = "$package_expected" ] || {
    printf 'replication image guardrail failed: valid package fixture was rejected: %s\n' "$package_fixture" >&2
    exit 1
  }
done
package_extra_fixture=$root/scripts/fixtures/replication_iproute_rpm_with_extra_record.txt
test -f "$package_extra_fixture" || { printf 'replication image guardrail failed: missing package fixture %s\n' "$package_extra_fixture" >&2; exit 1; }
package_extra_actual=$(cat "$package_extra_fixture")
package_extra_actual=${package_extra_actual}${replication_newline}
if normalize_replication_iproute_nevra "$package_expected" "$package_extra_actual" >/dev/null; then
  printf 'replication image guardrail failed: extra package record was accepted: %s\n' "$package_extra_fixture" >&2
  exit 1
fi
package_injected_actual=${package_expected}${replication_newline}evil-package-record
if normalize_replication_iproute_nevra "$package_expected" "$package_injected_actual" >/dev/null; then
  printf '%s\n' 'replication image guardrail failed: newline-injected package record was accepted' >&2
  exit 1
fi
for package_actual in \
  'iproute-1:6.17.0-2.el9.x86_64' \
  'iproute-0:6.17.0-3.el9.x86_64' \
  'iproute-0:6.17.0-2.el9.aarch64' \
  'iproute2-0:6.17.0-2.el9.x86_64' \
  'iproute-6.17.0-2.el9.x86_64-extra'; do
  if normalize_replication_iproute_nevra "$package_expected" "$package_actual" >/dev/null; then
    printf 'replication image guardrail failed: invalid package NEVRA was accepted: %s\n' "$package_actual" >&2
    exit 1
  fi
done

key_line=$(grep -nF 'curl --fail --silent' "$dockerfile" | cut -d: -f1)
fingerprint_line=$(grep -nF 'primary_fingerprints=' "$dockerfile" | cut -d: -f1)
import_line=$(grep -nF 'rpm --import /tmp/RPM-GPG-KEY-Rocky-9' "$dockerfile" | cut -d: -f1)
dnf_line=$(grep -nF 'dnf --assumeyes' "$dockerfile" | awk -F: 'NR == 1 { print $1; exit }')
[ "$key_line" -lt "$fingerprint_line" ] && [ "$fingerprint_line" -lt "$import_line" ] && [ "$import_line" -lt "$dnf_line" ] || {
  printf '%s\n' 'replication image guardrail failed: key verification/import must precede DNF' >&2
  exit 1
}

if grep -Eq 'head[[:space:]]+-n|cut -d: -f2[[:space:]]*\|[[:space:]]*head' "$dockerfile"; then
  printf '%s\n' 'replication image guardrail failed: truncated fingerprint extraction found' >&2
  exit 1
fi

[ "$(grep -Foc 'primary_fingerprints=' "$dockerfile")" -eq 1 ] || {
  printf '%s\n' 'replication image guardrail failed: ambiguous primary fingerprint check' >&2
  exit 1
}

# Reject a key containing the expected primary key plus an additional primary
# key; accepting only the first fingerprint would trust an unexpected key.
printf '%s\n' \
  'pub:-:2048:1:expected::::::::0' \
  'fpr:::::::::21CB256AE16FC54C6E652949702D426D350D275D:' \
  'pub:-:2048:1:unexpected::::::::0' \
  'fpr:::::::::AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA:' >"$tmp/extra-primary-key-colons"
extra_primary_fingerprints=$(awk -F: '$1 == "pub" { primary=1; next } primary && $1 == "fpr" { print $10; primary=0 }' "$tmp/extra-primary-key-colons")
expected_extra_primary_fingerprints=$(printf '%s\n' \
  '21CB256AE16FC54C6E652949702D426D350D275D' \
  'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
[ "$extra_primary_fingerprints" = "$expected_extra_primary_fingerprints" ] || {
  printf '%s\n' 'replication image guardrail failed: negative fingerprint fixture is invalid' >&2
  exit 1
}
[ "$extra_primary_fingerprints" != '21CB256AE16FC54C6E652949702D426D350D275D' ] || {
  printf '%s\n' 'replication image guardrail failed: extra primary fingerprint was accepted' >&2
  exit 1
}

# This mirrors the extraction and exact comparison performed in the image
# build. It remains a static fixture check: this script does not run DNF or
# build the image.
extract_enabled_repositories() {
  awk '$1 == "repo" { header=1; next } header && $1 != "repolist:" && NF { print $1 }' | sort
}

assert_expected_enabled_repositories() {
  enabled_repositories=$(extract_enabled_repositories)
  expected_repositories=$(printf '%s\n' rocky-9.8-appstream rocky-9.8-baseos rocky-9.8-extras)
  [ "$enabled_repositories" = "$expected_repositories" ]
}

# The effective-repository assertion must reject an unexpected enabled repo,
# not merely recognize the three expected names among a larger set. Keep the
# fixture in the format consumed by `dnf repolist enabled`, including its
# header and summary line, and first prove the expected output is accepted.
printf '%s\n' \
  'repo id                         repo name' \
  'rocky-9.8-appstream             Rocky Linux 9.8 - AppStream' \
  'rocky-9.8-baseos                Rocky Linux 9.8 - BaseOS' \
  'rocky-9.8-extras                Rocky Linux 9.8 - Extras' \
  'repolist: 3' >"$tmp/repolist"
assert_expected_enabled_repositories <"$tmp/repolist" || {
  printf '%s\n' 'replication image guardrail failed: repository fixture does not match the expected effective set' >&2
  exit 1
}
printf '%s\n' \
  'repo id                         repo name' \
  'rocky-9.8-appstream             Rocky Linux 9.8 - AppStream' \
  'rocky-9.8-baseos                Rocky Linux 9.8 - BaseOS' \
  'rocky-9.8-extras                Rocky Linux 9.8 - Extras' \
  'unexpected-extra-fixture        Unexpected extra repository' \
  'repolist: 4' >"$tmp/repolist-with-extra"
if assert_expected_enabled_repositories <"$tmp/repolist-with-extra"; then
  printf '%s\n' 'replication image guardrail failed: extra-repository negative fixture was not rejected' >&2
  exit 1
fi

if grep -Eq '(^|[[:space:]])http://' "$dockerfile"; then
  printf '%s\n' 'replication image guardrail failed: insecure HTTP URL found' >&2
  exit 1
fi

if grep -Eiq '(^|[[:space:]])(update|upgrade)([[:space:]]|$)|allowerasing|gpgcheck[[:space:]]*=[[:space:]]*0|repo_gpgcheck[[:space:]]*=[[:space:]]*0|sslverify[[:space:]]*=[[:space:]]*0|--no-gpg-check|disable-gpg' "$dockerfile"; then
  printf '%s\n' 'replication image guardrail failed: unsafe package/repository option found' >&2
  exit 1
fi

printf '%s\n' 'replication image guardrails: PASS'
