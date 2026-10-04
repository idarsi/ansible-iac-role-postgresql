#!/bin/sh
set -eu
replication_script_dir=${0%/*}
[ "$replication_script_dir" = "$0" ] && replication_script_dir=.
. "$replication_script_dir/replication_runtime.sh"

# Keep local replication runs on the shared test environment.  CI may override
# these values with its setup-python location, but the wrapper must not fall
# back to an unrelated controller Python or Molecule executable.
replication_testing_venv=${IDARSI_ANSIBLE_TESTING_VENV:-/home/arsi/.local/share/venvs/idarsi-ansible-testing}
export IDARSI_ANSIBLE_TESTING_VENV="$replication_testing_venv"
: "${REPLICATION_PYTHON_COMMAND:=$replication_testing_venv/bin/python}"
# This is the only documented target fallback in the direct launcher for the Python executable installed
# in the Rocky target image. CI may override it; molecule.yml only propagates
# the already-selected value and never resolves a target interpreter itself.
: "${REPLICATION_TARGET_PYTHON_COMMAND:=/usr/bin/python3}"
: "${REPLICATION_MOLECULE_COMMAND:=$replication_testing_venv/bin/molecule}"
export REPLICATION_PYTHON_COMMAND REPLICATION_TARGET_PYTHON_COMMAND REPLICATION_MOLECULE_COMMAND
replication_runtime_activate python || {
  printf '%s\n' 'Replication requires a trusted absolute Python executable' >&2
  exit 1
}
replication_python_site=$(
  "$REPLICATION_PYTHON_COMMAND" -c 'import sysconfig; print(sysconfig.get_path("purelib"))'
) || {
  printf '%s\n' 'Unable to derive Python site-packages from the selected replication Python' >&2
  exit 1
}
[ -n "$replication_python_site" ] && case "$replication_python_site" in
  /*) ;;
  *) printf '%s\n' 'Selected replication Python returned a non-absolute site-packages path' >&2; exit 1 ;;
esac
[ -d "$replication_python_site" ] && [ ! -L "$replication_python_site" ] || {
  printf '%s\n' 'Selected replication Python returned an untrusted site-packages directory' >&2
  exit 1
}
# The selected interpreter owns this derived site-packages directory.  Remove
# every inherited occurrence before prepending it so an earlier untrusted
# entry cannot shadow the Molecule plugin (and duplicates cannot reappear).
replication_pythonpath=$replication_python_site
replication_pythonpath_ifs=$IFS
IFS=:
for replication_pythonpath_entry in ${PYTHONPATH:-}; do
  [ "$replication_pythonpath_entry" = "$replication_python_site" ] && continue
  replication_pythonpath=$replication_pythonpath:$replication_pythonpath_entry
done
IFS=$replication_pythonpath_ifs
PYTHONPATH=$replication_pythonpath
export PYTHONPATH
replication_runtime_preflight
# The Podman plugin reads these from the Molecule process environment.  Keep
# these exports in the launcher rather than relying on unsupported Molecule
# driver configuration (or CI accidentally supplying them).
export MOLECULE_PODMAN_EXECUTABLE="$REPLICATION_PODMAN_COMMAND"
export CONTAINERS_HELPER_BINARY_DIR
base_ref="docker.io/rockylinux/rockylinux:9-ubi-init@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
replication_base_ref=$base_ref

test "$(uname -m)" = x86_64 || {
  printf '%s\n' 'Replication requires a native x86_64 host; QEMU is not supported.' >&2
  exit 1
}
test "$("$REPLICATION_PODMAN_COMMAND" info --format '{{.Host.Arch}}')" = amd64 || {
  printf '%s\n' 'Replication requires a native amd64 Podman runtime; emulation is not supported.' >&2
  exit 1
}
. "$(dirname "$0")/replication_image_normalize.sh"
replication_expected_digest=$(normalize_replication_sha256 "${base_ref##*@}")
"$REPLICATION_PODMAN_COMMAND" pull --quiet "$base_ref" >/dev/null
raw_base_id=$("$REPLICATION_PODMAN_COMMAND" image inspect "$base_ref" --format '{{.Id}}')
base_id=$(normalize_replication_sha256 "$raw_base_id") || {
  printf '%s\n' 'Unable to determine the exact Rocky base image ID' >&2; exit 1
}
raw_base_repo_digests=$("$REPLICATION_PODMAN_COMMAND" image inspect "$base_ref" --format '{{range .RepoDigests}}{{println .}}{{end}}')
base_repo_digest=$(printf '%s\n' "$raw_base_repo_digests" | validate_replication_base_repo_digests)
[ "$base_repo_digest" = "$base_ref" ] || {
  printf '%s\n' 'Unable to determine the exact Rocky base image repo digest' >&2; exit 1
}
export MOLECULE_REPLICATION_BASE_IMAGE_ID="$base_id"
export MOLECULE_REPLICATION_BASE_REPO_DIGEST="$base_repo_digest"
cleanup_replication_containers() {
  status=$?
  cleanup_status=0
  replication_destroy_output=$(mktemp "${TMPDIR:-/tmp}/replication-destroy.XXXXXX") || {
    printf '%s\n' 'Unable to create replication cleanup status file' >&2
    cleanup_status=1
    replication_destroy_output=''
  }
  if [ -n "$replication_destroy_output" ]; then
    if "$REPLICATION_MOLECULE_COMMAND" destroy -s replication >"$replication_destroy_output" 2>&1; then
      :
    else
      cleanup_status=$?
    fi
  else
    cleanup_status=1
  fi
  if [ "$cleanup_status" -ne 0 ]; then
    printf '%s\n' 'Molecule container cleanup command failed; inspecting remaining containers' >&2
  fi
  if [ -n "$replication_destroy_output" ] && [ "$cleanup_status" -ne 0 ] &&
    replication_destroy_was_only_missing_container "$replication_destroy_output"; then
    cleanup_status=0
  fi
  replication_instances=$(
    "$REPLICATION_PODMAN_COMMAND" ps -a --format '{{.Names}}'
  ) || {
    printf '%s\n' 'Unable to inspect replication containers during cleanup' >&2
    cleanup_status=1
    replication_instances='__cleanup_inspection_failed__'
  }
  replication_instance_found=false
  for replication_instance in $replication_instances; do
    case "$replication_instance" in
      instance-idarsi-rl9-primary|instance-idarsi-rl9-standby)
        replication_instance_found=true
        ;;
    esac
  done
  if "$replication_instance_found"; then
    printf '%s\n' 'Molecule cleanup left replication containers behind' >&2
    cleanup_status=1
  fi
  [ -n "$replication_destroy_output" ] && rm -f -- "$replication_destroy_output"
  if [ "$cleanup_status" -ne 0 ]; then
    status=$cleanup_status
  fi
  exit "$status"
}

# Molecule can report an already-removed container as a destroy failure.  Do
# not hide a real failure merely because that diagnostic appears in the same
# output (or on another output line).
replication_destroy_was_only_missing_container() {
  replication_destroy_missing=false
  replication_destroy_other=false
  while IFS= read -r replication_destroy_line || [ -n "$replication_destroy_line" ]; do
    replication_destroy_lower=$(printf '%s' "$replication_destroy_line" | tr '[:upper:]' '[:lower:]')
    case "$replication_destroy_lower" in
      *'no such container'*|*'container not found'*|*'does not exist'*)
        replication_destroy_missing=true
        replication_destroy_remainder=$(printf '%s' "$replication_destroy_lower" |
          sed 's/no such container//g; s/container not found//g; s/does not exist//g; s/error:[[:space:]]*//g')
        case "$replication_destroy_remainder" in
          *error*|*fail*|*denied*|*permission*|*unable*|*cannot*|*fatal*) replication_destroy_other=true ;;
        esac
        ;;
      *error*|*fail*|*denied*|*permission*|*unable*|*cannot*|*fatal*)
        replication_destroy_other=true
        ;;
    esac
  done <"$1"
  [ "$replication_destroy_missing" = true ] && [ "$replication_destroy_other" = false ]
}
trap cleanup_replication_containers EXIT HUP INT TERM

"$REPLICATION_MOLECULE_COMMAND" test -s replication
