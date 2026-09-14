#!/usr/bin/env bash
set -euo pipefail

# Deliberately narrow host-side failure injection for the supplemental tests.
# The caller must provide the exact libvirt domain returned by `virsh list`.
uri="${LIBVIRT_DEFAULT_URI:-qemu:///system}"
action="${1:?action (destroy|start) is required}"
domain="${2:?exact domain is required}"
case "${action}" in destroy|start) ;; *) exit 2 ;; esac
if [[ ! "${domain}" =~ ^molecule\.[^.]+\.vagrant_hard_patroni_failure_pg0[1-3]$ ]]; then
  printf 'Refusing unexpected Molecule domain: %s\n' "${domain}" >&2
  exit 3
fi
mapfile -t matches < <(virsh -c "${uri}" list --all --name | awk -v d="${domain}" '$0 == d {print}')
[[ "${#matches[@]}" -eq 1 && "${matches[0]}" == "${domain}" ]]
if [[ "${action}" == start ]] && [[ "$(virsh -c "${uri}" domstate "${domain}")" == running ]]; then
  exit 0
fi
virsh -c "${uri}" "${action}" "${domain}"
