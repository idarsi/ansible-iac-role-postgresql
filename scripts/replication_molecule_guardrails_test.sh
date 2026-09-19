#!/bin/sh
set -eu

# Exercise the helper trap without starting Molecule.  A failed test must still
# attempt container destruction, and neither operation may create or remove the
# Podman's pre-existing reserved default bridge network.
root=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

# Use the same selected controller interpreter as the replication wrapper and
# CI. Do not independently discover python3: that can validate a different
# environment from the one carrying the Molecule Podman plugin.
selected_python=${REPLICATION_PYTHON_COMMAND:-/home/arsi/.local/share/venvs/idarsi-ansible-testing/bin/python}
[ -x "$selected_python" ] || {
  printf '%s\n' "replication runtime guardrail failed: selected interpreter is not executable: $selected_python" >&2
  exit 1
}

# Every workflow step that can invoke the replication Podman executable must
# establish the runtime trust boundary first.  Keep this check close to the
# helper guardrails so a duplicated fast/daily job cannot regress silently.
"$selected_python" - "$root/.github/workflows/tests.yml" <<'PY'
import pathlib
import re
import sys

import yaml

workflow = yaml.safe_load(pathlib.Path(sys.argv[1]).read_text())
testing = pathlib.Path(sys.argv[1]).parents[2] / "TESTING.md"
testing_text = testing.read_text()
replication_dir = testing.parent / "molecule/replication"
scenario = yaml.safe_load((replication_dir / "molecule.yml").read_text())
scenario_env = scenario.get("provisioner", {}).get("env", {})
scenario_vars = scenario.get("provisioner", {}).get("vars", {})
workflow_text = pathlib.Path(sys.argv[1]).read_text()
assert "CONTAINERS_HELPER_BINARY_DIR" in workflow_text, (
    "workflow must establish the effective Podman helper directory"
)
assert "MOLECULE_PODMAN_EXECUTABLE=%s" not in workflow_text, (
    "CI must not mask missing launcher exports through GITHUB_ENV"
)
assert scenario_env.get("REPLICATION_PYTHON_COMMAND") == "${REPLICATION_PYTHON_COMMAND}", (
    "replication Molecule must receive the selected controller interpreter"
)
assert "environment" not in scenario.get("driver", {}), (
    "unsupported driver.environment must not claim to configure the Podman plugin"
)
assert "pg_replication_controller_python_executable" in scenario_vars, (
    "replication Molecule must define the controller interpreter contract"
)
assert "pg_replication_target_python_executable" in scenario_vars, (
    "replication Molecule must define the target interpreter contract"
)
assert "REPLICATION_PYTHON_COMMAND" in scenario_vars["pg_replication_controller_python_executable"], (
    "controller interpreter contract must be sourced from REPLICATION_PYTHON_COMMAND"
)
assert "REPLICATION_TARGET_PYTHON_COMMAND" in scenario_vars["pg_replication_target_python_executable"], (
    "target interpreter contract must be sourced from REPLICATION_TARGET_PYTHON_COMMAND"
)
assert scenario_env.get("REPLICATION_TARGET_PYTHON_COMMAND") == "${REPLICATION_TARGET_PYTHON_COMMAND}", (
    "Molecule must receive the target interpreter selected by the launcher"
)
prepare_text = (replication_dir / "prepare.yml").read_text()
wrapper_text = (testing.parent / "scripts/replication_molecule.sh").read_text()
assert "pg_replication_podman_configured" in prepare_text, (
    "replication prepare must retain the explicitly configured Podman value"
)
assert "pg_replication_molecule_candidates" in prepare_text, (
    "direct Molecule must have a controlled Molecule executable fallback"
)
for candidate in ("/usr/local/bin/molecule", "/usr/bin/molecule"):
    assert candidate in prepare_text, f"direct Molecule candidate is missing: {candidate}"
for candidate in ("/usr/libexec/netavark", "/usr/libexec/podman/netavark", "/usr/lib/podman/netavark"):
    assert candidate in prepare_text, f"direct netavark candidate is missing: {candidate}"
for candidate in ("/usr/libexec/aardvark-dns", "/usr/libexec/podman/aardvark-dns", "/usr/libexec/aardvark", "/usr/lib/podman/aardvark-dns", "/usr/lib/podman/aardvark"):
    assert candidate in prepare_text, f"direct aardvark candidate is missing: {candidate}"
assert "command -v" not in prepare_text, "prepare must not discover runtime tools through PATH"
assert "follow: false" in prepare_text, "direct runtime resolution must not follow symlinks"
assert "Never replace an explicitly supplied wrapper value" in prepare_text, (
    "replication Podman fallback contract must be documented"
)
assert 'MOLECULE_PODMAN_EXECUTABLE: "${REPLICATION_PODMAN_COMMAND:-/usr/bin/podman}"' in (
    replication_dir / "molecule.yml"
).read_text(), "the wrapper Podman value must remain authoritative"
scenario_env_text = (replication_dir / "molecule.yml").read_text()
for variable in (
    "REPLICATION_MOLECULE_COMMAND",
    "REPLICATION_NETAVARK_COMMAND",
    "REPLICATION_AARDVARK_COMMAND",
):
    assert f'{variable}: "${{{variable}:-' in scenario_env_text, (
        f"the wrapper {variable} override must reach prepare.yml"
    )
assert 'CONTAINERS_HELPER_BINARY_DIR: "${CONTAINERS_HELPER_BINARY_DIR:-/usr/libexec/podman}"' in scenario_env_text, (
    "Podman helper directory must be passed through supported configuration"
)
assert ": \"${REPLICATION_PYTHON_COMMAND:=" in wrapper_text, (
    "replication wrapper must set the shared venv interpreter contract"
)
assert "export REPLICATION_PYTHON_COMMAND" in wrapper_text, (
    "replication wrapper must export the interpreter contract"
)
assert 'export MOLECULE_PODMAN_EXECUTABLE="$REPLICATION_PODMAN_COMMAND"' in wrapper_text, (
    "replication launcher must export the Podman executable"
)
assert "export CONTAINERS_HELPER_BINARY_DIR" in wrapper_text, (
    "replication launcher must export the Podman helper directory"
)
assert "pg_replication_controller_python_executable" in prepare_text, (
    "replication prepare fixture must define the selected controller interpreter"
)
assert "pg_replication_target_python_executable" in prepare_text, (
    "replication prepare must validate the propagated target interpreter"
)
host_vars = scenario.get("provisioner", {}).get("inventory", {}).get("host_vars", {})
expected_hosts = {
    "instance-idarsi-rl9-primary",
    "instance-idarsi-rl9-standby",
}
assert set(host_vars) == expected_hosts, "replication host vars must cover both containers"
for host in expected_hosts:
    assert host_vars[host] == {
        "ansible_connection": "containers.podman.podman",
        "ansible_user": "root",
        "ansible_become_method": "su",
        "ansible_python_interpreter": (
            "{{ lookup('env', 'REPLICATION_TARGET_PYTHON_COMMAND') "
            "| default('/usr/bin/python3', true) }}"
        ),
    }, f"{host}: replication inventory connection contract changed"
    assert "pg_replication_target_python_executable" not in host_vars[host]["ansible_python_interpreter"], (
        f"{host}: target interpreter must not recursively reference its own variable"
    )
for playbook_name in ("prepare.yml", "converge.yml", "verify.yml", "cleanup.yml"):
    plays = yaml.safe_load((replication_dir / playbook_name).read_text())
    for play in plays:
        play_vars = play.get("vars", {})
        for key in ("ansible_connection", "ansible_user", "ansible_become_method"):
            assert key not in play_vars, (
                f"{playbook_name}/{play.get('name')}: {key} belongs in Molecule inventory"
            )
platform_keys = set(scenario["platforms"][0])
supported_platform_keys = {
    "name", "image", "dockerfile", "command", "privileged", "pre_build_image",
    "systemd", "tty", "extra_opts", "volumes",
}
assert platform_keys <= supported_platform_keys, (
    f"replication platform contains unsupported properties: "
    f"{sorted(platform_keys - supported_platform_keys)}"
)
assert not platform_keys & {"ansible_connection", "ansible_user", "ansible_become_method"}, (
    "replication platform properties contain Ansible inventory variables"
)
assert "ansible_become_method: sudo" not in "\n".join(
    (replication_dir / name).read_text() for name in
    ("molecule.yml", "prepare.yml", "converge.yml", "verify.yml", "cleanup.yml")
), "replication contains a sudo become-method fallback"
assert "/usr/bin/podman" not in testing_text, "TESTING.md contains a direct Podman path"
assert "readlink -f" not in testing_text, "TESTING.md performs path canonicalization directly"
assert "replication_runtime_preflight" in testing_text, "TESTING.md omits replication runtime preflight"
assert "pre-existing" in testing_text and "never create or remove" in testing_text, (
    "TESTING.md must document the reserved network lifecycle"
)
for playbook_name in ("converge.yml", "verify.yml"):
    playbook_text = (replication_dir / playbook_name).read_text()
    assert 'pg_replication_target_python_executable: "{{ ansible_python_interpreter }}"' not in playbook_text, (
        f"{playbook_name}: target interpreter must not recurse through ansible_python_interpreter"
    )
    assert "- python3" not in playbook_text, (
        f"{playbook_name}: hardcoded python3 invocation bypasses the selected interpreter"
    )
for playbook_name in ("molecule.yml", "prepare.yml"):
    assert "REPLICATION_TARGET_PYTHON_COMMAND" in (replication_dir / playbook_name).read_text(), (
        f"{playbook_name}: target Python environment fallback is missing"
    )
prepare_text = (replication_dir / "prepare.yml").read_text()
assert "Resolve the target Python interpreter before any target use" in prepare_text, (
    "prepare must execute target Python resolution before stat or interpreter use"
)
cleanup_text = (replication_dir / "cleanup.yml").read_text()
assert 'pg_replication_target_python_executable: "{{ ansible_python_interpreter }}"' not in cleanup_text, (
    "cleanup must use the launcher interpreter contract without recursion"
)
launcher_text = wrapper_text
assert "documented target fallback" in launcher_text, (
    "the direct-launcher target Python fallback must be documented"
)
assert ": \"${REPLICATION_TARGET_PYTHON_COMMAND:=/usr/bin/python3}\"" in launcher_text, (
    "the launcher must define the documented target Python fallback"
)
for job_name in ("molecule-fast", "molecule-daily"):
    steps = workflow["jobs"][job_name]["steps"]
    for step in steps:
        run = step.get("run", "")
        if "REPLICATION_PODMAN_COMMAND}" not in run:
            continue
        preflight = run.find("replication_runtime_preflight")
        assert preflight >= 0, f"{job_name}/{step['name']}: missing runtime preflight"
        for match in re.finditer(r'"\$\{REPLICATION_PODMAN_COMMAND\}"', run):
            assert preflight < match.start(), (
                f"{job_name}/{step['name']}: Podman invocation precedes preflight"
            )

    run_step = next(step for step in steps if step.get("name") == "Run Molecule scenario")
    run = run_step["run"]
    branch = 'if [ "${{ matrix.scenario }}" = replication ]; then'
    assert branch in run, f"{job_name}: scenario runtime branching is not explicit"
    replication_run, unrelated_run = run.split(branch, 1)[1].split("else", 1)
    assert replication_run.index("scripts/replication_molecule.sh") >= 0, (
        f"{job_name}: replication must use the launcher contract"
    )
    assert "replication_runtime_preflight" not in unrelated_run, (
        f"{job_name}: unrelated scenarios must not inherit replication preflight"
    )
    assert '"${CI_PYTHON_COMMAND}" -m molecule test' in unrelated_run, (
        f"{job_name}: unrelated scenarios must retain the normal Molecule path"
    )

daily_destroy = next(
    step for step in workflow["jobs"]["molecule-daily"]["steps"]
    if step.get("name") == "Destroy replication containers without touching the default network"
)
daily_destroy_run = daily_destroy["run"]
for export in (
    'export MOLECULE_PODMAN_EXECUTABLE="${REPLICATION_PODMAN_COMMAND}"',
    "export CONTAINERS_HELPER_BINARY_DIR",
):
    assert export in daily_destroy_run, (
        f"molecule-daily cleanup must export {export} before direct Molecule destroy"
    )
assert daily_destroy_run.index("replication_runtime_preflight") < daily_destroy_run.index(
    'export MOLECULE_PODMAN_EXECUTABLE="${REPLICATION_PODMAN_COMMAND}"'
)
assert daily_destroy_run.index("export CONTAINERS_HELPER_BINARY_DIR") < daily_destroy_run.index(
    '"${REPLICATION_MOLECULE_COMMAND}" destroy -s replication'
)
print("replication CI Podman preflight ordering: PASS")
PY

mkdir "$tmp/bin" "$tmp/runtime" "$tmp/scripts"
cp "$root/scripts/replication_molecule.sh" "$root/scripts/replication_runtime.sh" \
  "$root/scripts/replication_image_normalize.sh" "$tmp/scripts/"
chmod +x "$tmp/scripts"/*.sh

# setup-python and virtualenvs can provide symlinked entry points.  Preserve the
# selected entrypoint, but validate its canonical target before using it.
mkdir "$tmp/python-layout"
printf '%s\n' '#!/bin/sh' >"$tmp/python-layout/python-real"
chmod +x "$tmp/python-layout/python-real"
ln -s "$tmp/python-layout/python-real" "$tmp/python-layout/python"
resolved_python=$(REPLICATION_PYTHON_COMMAND="$tmp/python-layout/python" \
  sh -c '. "$1"; replication_runtime_activate python; printf "%s" "$REPLICATION_PYTHON_COMMAND"' \
  sh "$tmp/scripts/replication_runtime.sh")
[ "$resolved_python" = "$tmp/python-layout/python" ] || {
  printf '%s\n' 'replication runtime guardrail failed: Python entrypoint was not preserved' >&2
  exit 1
}

cat >"$tmp/bin/podman" <<'MOCK'
#!/bin/sh
set -eu
case "$1 ${2:-}" in
  "info --format")
    case "$3" in
      *Rootless*) printf '%s\n' "${MOCK_ROOTLESS:-true}" ;;
      *NetworkBackend*) printf '%s\n' netavark ;;
      *Host.Arch*) printf '%s\n' amd64 ;;
      *) exit 1 ;;
    esac ;;
  pull*) printf '%s\n' podman-pull >>"$MOCK_LOG"; exit 0 ;;
  "image inspect")
    printf '%s\n' podman-image-inspect >>"$MOCK_LOG"
    case "$5" in
      *RepoDigests*)
        printf '%s\n' \
          'docker.io/rockylinux/rockylinux@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5' \
          'docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4' ;;
       *) printf '%s\n' 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa' ;;
     esac ;;
  "ps -a") printf '%s\n' podman-ps >>"$MOCK_LOG"; exit 0 ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$tmp/bin/podman"
for helper in netavark aardvark-dns; do
  printf '%s\n' '#!/bin/sh' >"$tmp/bin/$helper"
  chmod +x "$tmp/bin/$helper"
done
ln -s "$tmp/bin/netavark" "$tmp/bin/netavark-symlink"
if REPLICATION_NETAVARK_COMMAND="$tmp/bin/netavark-symlink" \
  sh -c '. "$1"; replication_runtime_activate netavark' sh "$tmp/scripts/replication_runtime.sh"; then
  printf '%s\n' 'replication runtime guardrail failed: symlinked netavark was accepted' >&2
  exit 1
fi
if REPLICATION_NETAVARK_COMMAND="$tmp/bin" \
  sh -c '. "$1"; replication_runtime_activate netavark' sh "$tmp/scripts/replication_runtime.sh"; then
  printf '%s\n' 'replication runtime guardrail failed: non-regular netavark was accepted' >&2
  exit 1
fi

# Read the rootful fixture before installing the mocked Python. Otherwise the
# mock shadows the interpreter used here and leaves MOCK_ROOTLESS empty.
mock_rootless=$("$selected_python" -c 'import json, sys; print(str(json.load(open(sys.argv[1]))["Host"]["Security"]["Rootless"]).lower())' \
  "$root/scripts/fixtures/replication_rootful_runtime.json")
[ "$mock_rootless" = false ] || {
  printf '%s\n' 'replication runtime guardrail failed: rootful fixture did not resolve to false' >&2
  exit 1
}

mkdir -p "$tmp/venv/bin" "$tmp/venv/lib/python3.13/site-packages/molecule_plugins"
printf '%s\n' 'home = unused' >"$tmp/venv/pyvenv.cfg"
cat >"$tmp/venv/lib/python3.13/site-packages/molecule_plugins/__init__.py" <<'PY'
PY
cat >"$tmp/venv/lib/python3.13/site-packages/molecule_plugins/podman.py" <<'PY'
import os
from pathlib import Path

Path(os.environ["MOCK_PLUGIN_IMPORT_LOG"]).write_text("imported\n")
PY
mkdir -p "$tmp/untrusted-site/molecule_plugins"
cat >"$tmp/untrusted-site/molecule_plugins/__init__.py" <<'PY'
PY
cat >"$tmp/untrusted-site/molecule_plugins/podman.py" <<'PY'
import os
from pathlib import Path

Path(os.environ["MOCK_SHADOW_IMPORT_LOG"]).write_text("shadowed\n")
raise ImportError("untrusted plugin shadowed the trusted fixture")
PY
cat >"$tmp/venv/bin/python" <<'MOCK'
#!/bin/sh
set -eu
[ "${0}" = "${MOCK_PRESERVED_PYTHON}" ] || exit 1
case "${1:-}" in
  -c)
    case "${2:-}" in
      *sysconfig.get_path*)
         printf '%s\n' "$MOCK_SITE" ;;
      *)
         printf '%s\n' "${PYTHONPATH:-}" >"$MOCK_PYTHONPATH_LOG"
         exec "$MOCK_SELECTED_INTERPRETER" "$@" ;;
    esac ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$tmp/venv/bin/python"
cat >"$tmp/bin/molecule" <<'MOCK'
#!/bin/sh
set -eu
printf '%s\n' "MOLECULE_PODMAN_EXECUTABLE=${MOLECULE_PODMAN_EXECUTABLE-}" \
  "CONTAINERS_HELPER_BINARY_DIR=${CONTAINERS_HELPER_BINARY_DIR-}" \
  "REPLICATION_TARGET_PYTHON_COMMAND=${REPLICATION_TARGET_PYTHON_COMMAND-}" >>"$MOCK_ENV_LOG"
case "$1 ${2:-} ${3:-}" in
  "destroy -s replication")
    printf '%s\n' molecule-destroy >>"$MOCK_LOG"
    case "${MOCK_DESTROY_MODE:-failed}" in
      absent) printf '%s\n' 'container not found' >&2; exit 7 ;;
      permission) printf '%s\n' 'permission denied' >&2; exit 13 ;;
      plugin) printf '%s\n' 'plugin failed' >&2; exit 17 ;;
      mixed)
        printf '%s\n' 'container not found' 'permission denied' >&2
        exit 19 ;;
      *) exit 7 ;;
    esac ;;
  "test -s replication") printf '%s\n' molecule-test >>"$MOCK_LOG"; exit "${MOCK_TEST_STATUS:-42}" ;;
  *) exit 1 ;;
esac
MOCK
chmod +x "$tmp/bin/molecule"

export PATH="$tmp/bin:/usr/bin:/bin"
export REPLICATION_PODMAN_COMMAND="$tmp/bin/podman"
export REPLICATION_MOLECULE_COMMAND="$tmp/bin/molecule"
export REPLICATION_NETAVARK_COMMAND="$tmp/bin/netavark"
export REPLICATION_AARDVARK_COMMAND="$tmp/bin/aardvark-dns"
export REPLICATION_PYTHON_COMMAND="$tmp/venv/bin/python"
export MOCK_SITE="$tmp/venv/lib/python3.13/site-packages"
export MOCK_PYTHONPATH_LOG="$tmp/pythonpath.log"
export MOCK_PLUGIN_IMPORT_LOG="$tmp/plugin-import.log"
export MOCK_SHADOW_IMPORT_LOG="$tmp/shadow-import.log"
export MOCK_SELECTED_INTERPRETER="$selected_python"
export MOCK_PRESERVED_PYTHON="$tmp/venv/bin/python"
export XDG_RUNTIME_DIR="$tmp/runtime"
export MOCK_LOG="$tmp/log" MOCK_ID="$tmp/id"
export MOCK_ENV_LOG="$tmp/molecule-env.log"

# The effective Podman helper directory must be derived from, and passed with,
# the same override names used by CI, the wrapper, and molecule.yml.
helper_dir=$(sh -c '. "$1"; replication_runtime_activate netavark; replication_runtime_activate aardvark-dns; replication_runtime_netavark_dir=${REPLICATION_NETAVARK_COMMAND%/*}; replication_runtime_aardvark_dir=${REPLICATION_AARDVARK_COMMAND%/*}; [ "$replication_runtime_netavark_dir" = "$replication_runtime_aardvark_dir" ]; CONTAINERS_HELPER_BINARY_DIR="$replication_runtime_netavark_dir"; printf "%s" "$CONTAINERS_HELPER_BINARY_DIR"' \
  sh "$tmp/scripts/replication_runtime.sh")
[ "$helper_dir" = "$tmp/bin" ] || {
  printf '%s\n' 'replication runtime guardrail failed: helper override was not passed to Podman' >&2
  exit 1
}

# Before the wrapper repairs ordering, the selected interpreter must reject an
# untrusted plugin shadowing the temporary venv-like fixture.
if PYTHONPATH="$tmp/untrusted-site:$MOCK_SITE" "$tmp/venv/bin/python" \
  -c 'import molecule_plugins.podman'; then
  printf '%s\n' 'replication runtime guardrail failed: plugin import accepted untrusted PYTHONPATH order' >&2
  exit 1
fi
[ -s "$MOCK_SHADOW_IMPORT_LOG" ] || {
  printf '%s\n' 'replication runtime guardrail failed: untrusted plugin fixture was not exercised' >&2
  exit 1
}

# Keep the direct helper assertion: the preflight itself must reject rootful
# Podman independently of the wrapper.
if MOCK_ROOTLESS="$mock_rootless" sh -c '. "$1"; replication_runtime_preflight' sh \
  "$tmp/scripts/replication_runtime.sh"; then
  printf '%s\n' 'replication runtime guardrail failed: rootful Podman was accepted' >&2
  exit 1
fi

# Export the fixture result into the actual wrapper subprocess.  This proves
# the wrapper stops at its preflight, before image, network, or Molecule work.
export MOCK_ROOTLESS="$mock_rootless"
: >"$MOCK_LOG"
if "$tmp/scripts/replication_molecule.sh"; then
  printf '%s\n' 'replication Molecule guardrail failed: rootful wrapper was accepted' >&2
  exit 1
fi
[ ! -s "$MOCK_LOG" ] || {
  printf '%s\n' 'replication Molecule guardrail failed: wrapper performed image/network/Molecule work before rejection' >&2
  exit 1
}

export MOCK_ROOTLESS=true
: >"$MOCK_LOG"
if env -u REPLICATION_TARGET_PYTHON_COMMAND \
  PYTHONPATH="$tmp/untrusted-site:$MOCK_SITE:$MOCK_SITE" \
  "$tmp/scripts/replication_molecule.sh"; then
  exit 1
fi
set -- $(tr '\n' ' ' <"$MOCK_LOG")
[ "$1" = podman-pull ]
[ "$2" = podman-image-inspect ]
[ "$3" = podman-image-inspect ]
[ "$4" = molecule-test ]
[ "$5" = molecule-destroy ]
[ "$6" = podman-ps ]
[ "$(sed -n '1p' "$MOCK_ENV_LOG")" = "MOLECULE_PODMAN_EXECUTABLE=$tmp/bin/podman" ]
[ "$(sed -n '2p' "$MOCK_ENV_LOG")" = "CONTAINERS_HELPER_BINARY_DIR=$tmp/bin" ]
[ "$(sed -n '3p' "$MOCK_ENV_LOG")" = "REPLICATION_TARGET_PYTHON_COMMAND=/usr/bin/python3" ] || {
  printf '%s\n' 'replication Molecule guardrail failed: target Python fallback did not reach Molecule' >&2
  exit 1
}
[ "$(cut -d: -f1 "$MOCK_PYTHONPATH_LOG")" = "$MOCK_SITE" ] || {
  printf '%s\n' 'replication Molecule guardrail failed: derived site-packages was not prepended' >&2
  exit 1
}
[ "$(tr -d '\n' <"$MOCK_PYTHONPATH_LOG")" = "$MOCK_SITE:$tmp/untrusted-site" ] || {
  printf '%s\n' 'replication Molecule guardrail failed: untrusted entry was not preserved after trusted site-packages' >&2
  exit 1
}
[ "$(tr ':' '\n' <"$MOCK_PYTHONPATH_LOG" | grep -c -F -- "$MOCK_SITE")" -eq 1 ] || {
  printf '%s\n' 'replication Molecule guardrail failed: derived site-packages was duplicated' >&2
  exit 1
}
[ -s "$MOCK_PLUGIN_IMPORT_LOG" ] || {
  printf '%s\n' 'replication Molecule guardrail failed: Podman plugin import was not executed' >&2
  exit 1
}
printf '%s\n' 'replication Molecule cleanup guardrails: PASS'

# A narrowly recognized absent-container diagnostic is tolerated only after the
# post-destroy inspection proves no reserved container remains.  Permission and
# plugin failures must retain their destroy status even when nothing remains.
for mode in absent permission plugin mixed; do
  : >"$MOCK_LOG"
  set +e
  MOCK_TEST_STATUS=0 MOCK_DESTROY_MODE="$mode" "$tmp/scripts/replication_molecule.sh"
  result=$?
  set -e
  case "$mode" in
    absent) [ "$result" -eq 0 ] ;;
    permission) [ "$result" -eq 13 ] ;;
    plugin) [ "$result" -eq 17 ] ;;
    mixed) [ "$result" -eq 19 ] ;;
  esac || {
    printf '%s\n' "replication cleanup guardrail failed: unexpected $mode status $result" >&2
    exit 1
  }
done
printf '%s\n' 'replication cleanup absent-vs-failure guardrails: PASS'

# Exercise direct launcher/configuration resolution with no target override. The
# mocked Molecule command stands in for prepare: it must receive the target-image
# fallback without starting Molecule or changing the shared testing environment.
: >"$MOCK_LOG"
: >"$MOCK_ENV_LOG"
if env -u REPLICATION_TARGET_PYTHON_COMMAND MOCK_TEST_STATUS=0 MOCK_DESTROY_MODE=absent \
  "$tmp/scripts/replication_molecule.sh"; then
  :
else
  printf '%s\n' 'replication fallback guardrail failed: direct launcher resolution failed' >&2
  exit 1
fi
[ "$(sed -n '3p' "$MOCK_ENV_LOG")" = "REPLICATION_TARGET_PYTHON_COMMAND=/usr/bin/python3" ] || {
  printf '%s\n' 'replication fallback guardrail failed: target fallback did not reach prepare' >&2
  exit 1
}
grep -Fqx molecule-test "$MOCK_LOG" || {
  printf '%s\n' 'replication fallback guardrail failed: launcher did not reach Molecule' >&2
  exit 1
}
printf '%s\n' 'replication target Python fallback launcher/prepare guardrail: PASS'
