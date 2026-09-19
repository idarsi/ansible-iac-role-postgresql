#!/bin/sh

# Resolve replication runtime tools without changing PATH.  Network helpers are
# installed in these fixed libexec locations on Fedora/RHEL.  Podman may also
# provide an explicitly configured absolute helper path through its environment
# variables; relative paths and PATH-derived directory injection are rejected.
replication_runtime_absolute_executable() {
  case "${1:-}" in
    /*) [ -f "$1" ] && [ -x "$1" ] && [ ! -L "$1" ] ;;
    *) return 1 ;;
  esac
}

# Do not resolve trusted tools through PATH.  This is the fixed location on the
# supported Linux images and keeps a hostile PATH from changing the result.
replication_runtime_readlink=/usr/bin/readlink

replication_runtime_resolve_executable() {
  replication_runtime_requested=$1
  replication_runtime_absolute_executable "$replication_runtime_requested" || return 1
  # prepare.yml uses stat(follow=false), so reject an untrusted final path.
  [ ! -L "$replication_runtime_requested" ] || return 1
  [ -x "$replication_runtime_readlink" ] || return 1
  replication_runtime_resolved=$("$replication_runtime_readlink" -f -- "$replication_runtime_requested") || return 1
  replication_runtime_absolute_executable "$replication_runtime_resolved" || return 1
  printf '%s\n' "$replication_runtime_resolved"
}

# Python entrypoints may be symlinks (both setup-python and a venv commonly use
# one).  Preserve the selected entrypoint so its environment/site-packages stay
# coupled, but validate its canonical target before returning it.
replication_runtime_resolve_python_executable() {
  replication_runtime_requested=$1
  case "$replication_runtime_requested" in
    /*) : ;;
    *) return 1 ;;
  esac
  [ -x "$replication_runtime_readlink" ] || return 1
  replication_runtime_resolved=$("$replication_runtime_readlink" -f -- "$replication_runtime_requested") || return 1
  replication_runtime_absolute_executable "$replication_runtime_resolved" || return 1
  printf '%s\n' "$replication_runtime_requested"
}

replication_runtime_resolve() {
  replication_runtime_tool=$1
  replication_runtime_configured=${2:-}
  if [ -n "$replication_runtime_configured" ]; then
    replication_runtime_resolve_executable "$replication_runtime_configured" || return 1
    return 0
  fi
  case "$replication_runtime_tool" in
    podman) replication_runtime_candidates='/usr/bin/podman /usr/local/bin/podman' ;;
    molecule) replication_runtime_candidates='/usr/local/bin/molecule /usr/bin/molecule' ;;
    netavark) replication_runtime_candidates='/usr/libexec/netavark /usr/libexec/podman/netavark' ;;
    aardvark-dns) replication_runtime_candidates='/usr/libexec/aardvark-dns /usr/libexec/podman/aardvark-dns /usr/libexec/aardvark' ;;
    python) replication_runtime_candidates='/usr/bin/python3 /usr/local/bin/python3' ;;
    *) return 1 ;;
  esac
  for replication_runtime_candidate in $replication_runtime_candidates; do
    if replication_runtime_resolve_executable "$replication_runtime_candidate"; then
      return 0
    fi
  done
  return 1
}

replication_runtime_activate() {
  replication_runtime_path=''
  case "$1" in
    podman) replication_runtime_path=$(replication_runtime_resolve podman "${REPLICATION_PODMAN_COMMAND:-}") || return 1 ;;
    molecule) replication_runtime_path=$(replication_runtime_resolve molecule "${REPLICATION_MOLECULE_COMMAND:-}") || return 1 ;;
    netavark) replication_runtime_path=$(replication_runtime_resolve netavark "${REPLICATION_NETAVARK_COMMAND:-}") || return 1 ;;
    aardvark-dns) replication_runtime_path=$(replication_runtime_resolve aardvark-dns "${REPLICATION_AARDVARK_COMMAND:-}") || return 1 ;;
    python)
      if [ -n "${REPLICATION_PYTHON_COMMAND:-}" ]; then
        replication_runtime_path=$(replication_runtime_resolve_python_executable "$REPLICATION_PYTHON_COMMAND") || return 1
      else
        replication_runtime_path=$(replication_runtime_resolve python) || return 1
      fi
      ;;
    *) return 1 ;;
  esac
  case "$1" in
    podman) REPLICATION_PODMAN_COMMAND=$replication_runtime_path; export REPLICATION_PODMAN_COMMAND ;;
    molecule) REPLICATION_MOLECULE_COMMAND=$replication_runtime_path; export REPLICATION_MOLECULE_COMMAND ;;
    netavark) REPLICATION_NETAVARK_COMMAND=$replication_runtime_path; export REPLICATION_NETAVARK_COMMAND ;;
    aardvark-dns) REPLICATION_AARDVARK_COMMAND=$replication_runtime_path; export REPLICATION_AARDVARK_COMMAND ;;
    python) REPLICATION_PYTHON_COMMAND=$replication_runtime_path; export REPLICATION_PYTHON_COMMAND ;;
  esac
}

replication_runtime_preflight() {
  for replication_runtime_tool in podman molecule netavark aardvark-dns python; do
    replication_runtime_activate "$replication_runtime_tool" || {
      printf '%s\n' "Replication requires a trusted absolute $replication_runtime_tool executable" >&2
      return 1
    }
  done
  # Podman discovers both netavark and aardvark-dns from the configured helper
  # directory.  Refuse split directories: merely validating executable paths
  # without passing this supported Podman setting would be a false guarantee.
  replication_runtime_netavark_dir=${REPLICATION_NETAVARK_COMMAND%/*}
  replication_runtime_aardvark_dir=${REPLICATION_AARDVARK_COMMAND%/*}
  [ "$replication_runtime_netavark_dir" = "$replication_runtime_aardvark_dir" ] || {
    printf '%s\n' 'Replication requires netavark and aardvark-dns in one Podman helper directory' >&2
    return 1
  }
  CONTAINERS_HELPER_BINARY_DIR=$replication_runtime_netavark_dir
  export CONTAINERS_HELPER_BINARY_DIR
  replication_runtime_rootless=$(
    "$REPLICATION_PODMAN_COMMAND" info --format '{{.Host.Security.Rootless}}'
  ) || {
    printf '%s\n' 'Replication requires Podman rootless runtime information' >&2
    return 1
  }
  [ "$replication_runtime_rootless" = true ] || {
    printf '%s\n' 'Replication requires rootless Podman; rootful Podman is not supported' >&2
    return 1
  }
  "$REPLICATION_PYTHON_COMMAND" -c 'import molecule_plugins.podman' >/dev/null 2>&1 || {
    printf '%s\n' 'Replication requires the installed Molecule Podman plugin (import molecule_plugins.podman failed)' >&2
    return 1
  }
}
