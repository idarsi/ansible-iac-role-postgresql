#!/bin/bash
# Shared PostgreSQL PKI serial-registry parser.  Callers must hold the
# registry/cluster transaction lock while invoking this function.
validate_pki_serial_paths() {
  local registry="$1" lock="$2" path parent metadata
  for path in "$registry" "$lock"; do
    parent=$(dirname -- "$path")
    while :; do
      [[ -d "$parent" && ! -L "$parent" ]] || {
        printf 'Unsafe PKI serial path parent: %s\n' "$parent" >&2; return 1
      }
      metadata=$(stat -c '%F %u %g %a' -- "$parent") || {
        printf 'Unable to stat PKI serial path parent: %s\n' "$parent" >&2; return 1
      }
      [[ "$metadata" == "directory 0 0 700" || "$metadata" == "directory 0 0 710" ||
         "$metadata" == "directory 0 0 711" || "$metadata" == "directory 0 0 750" ||
         "$metadata" == "directory 0 0 751" || "$metadata" == "directory 0 0 755" ]] || {
        printf 'Unsafe PKI serial path parent: %s\n' "$parent" >&2; return 1
      }
      [[ "$parent" == "/" ]] && break
      parent=$(dirname -- "$parent")
    done
    if [[ -L "$path" ]]; then
      printf 'Unsafe PKI serial registry or lock: %s\n' "$path" >&2; return 1
    fi
    if [[ -e "$path" ]]; then
      metadata=$(stat -c '%F %u %g %a' -- "$path") || return 1
      [[ "$metadata" == "regular file 0 0 600" ]] || {
        printf 'Unsafe PKI serial registry or lock: %s\n' "$path" >&2; return 1
      }
    fi
  done
}

# Validate a directory path before an Ansible file task or mkdir creates it.
# The final directory may be absent, but every existing component (including
# the root) must be a root-owned directory without group/other write access or
# extended/default ACL entries.
validate_pki_directory_path() {
  local path="$1" current metadata acl
  [[ "$path" == /* && "$path" != *$'\n'* ]] || {
    printf 'Unsafe PKI directory path: %s\n' "$path" >&2; return 1
  }
  current="$path"
  while :; do
    if [[ -e "$current" || -L "$current" ]]; then
      [[ -d "$current" && ! -L "$current" ]] || {
        printf 'Unsafe PKI directory component: %s\n' "$current" >&2; return 1
      }
      metadata=$(stat -c '%F %u %g %a' -- "$current") || return 1
       [[ "$metadata" =~ ^directory\ 0\ 0\ [0-7][0145][0145]$ ]] || {
        printf 'Unsafe PKI directory component: %s\n' "$current" >&2; return 1
      }
      acl=$(getfacl --absolute-names -- "$current") || return 1
      while IFS= read -r line; do
        case "$line" in
          '#'*|'user::'*|'group::'*|'other::'*) ;;
          *)
            printf 'Unsafe PKI directory ACL: %s\n' "$current" >&2; return 1 ;;
        esac
      done <<< "$acl"
    fi
    [[ "$current" == "/" ]] && break
    current=$(dirname -- "$current")
  done
}

validate_pki_serial_registry() {
  local registry="$1" line key
  declare -A seen=()
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" ]] || { printf 'Malformed empty serial registry entry in %s\n' "$registry" >&2; return 1; }
    [[ "$line" =~ ^[0-9A-Fa-f]+$ && ! "$line" =~ ^0+$ ]] || {
      printf 'Invalid or zero serial registry entry in %s: %s\n' "$registry" "$line" >&2; return 1;
    }
    key="${line,,}"
    [[ -z "${seen[$key]+x}" ]] || {
      printf 'Duplicate serial registry entry in %s: %s\n' "$registry" "$line" >&2; return 1;
    }
    seen[$key]=1
  done < "$registry"
}
