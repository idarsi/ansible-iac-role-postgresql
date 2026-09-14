#!/usr/bin/env bash
set -euo pipefail

export LC_ALL=C

network_name="idarsi-postgresql-molecule"
network_xml="$(dirname -- "${BASH_SOURCE[0]}")/idarsi-postgresql-molecule-network.xml"
virsh_uri="${LIBVIRT_DEFAULT_URI:-qemu:///system}"

if ! command -v virsh >/dev/null 2>&1; then
  printf 'virsh is required (install/configure libvirt first).\n' >&2
  exit 1
fi

if ! command -v xmllint >/dev/null 2>&1; then
  printf 'xmllint is required to validate an existing libvirt network safely.\n' >&2
  exit 1
fi

validate_existing_network() {
  local network_xml_content="$1"
  local xpath expected actual check
  local -a checks=(
    "/network/name|${network_name}"
    '/network/forward/@mode|nat'
    '/network/bridge/@name|virbr250'
    '/network/bridge/@stp|on'
    '/network/bridge/@delay|0'
    '/network/ip/@address|192.168.250.1'
    '/network/ip/@netmask|255.255.255.0'
    '/network/ip/dhcp/range/@start|192.168.250.100'
    '/network/ip/dhcp/range/@end|192.168.250.199'
  )

  # Ignore libvirt-generated UUIDs and DHCP reservations, but reject any
  # existing network whose topology or essential configuration differs from
  # the network used by the Vagrant scenario.
  for check in "${checks[@]}"; do
    xpath="${check%%|*}"
    expected="${check#*|}"
    actual="$(xmllint --xpath "string(${xpath})" - <<<"${network_xml_content}")"
    if [[ "${actual}" != "${expected}" ]]; then
      printf 'Existing libvirt network %s has conflicting configuration: %s is %q, expected %q.\n' \
        "${network_name}" "${xpath}" "${actual}" "${expected}" >&2
      exit 1
    fi
  done

  for xpath in '/network/forward' '/network/bridge' '/network/ip' '/network/ip/dhcp' '/network/ip/dhcp/range'; do
    actual="$(xmllint --xpath "count(${xpath})" - <<<"${network_xml_content}")"
    if [[ "${actual}" != '1' ]]; then
      printf 'Existing libvirt network %s has conflicting configuration: expected exactly one %s, found %s.\n' \
        "${network_name}" "${xpath}" "${actual}" >&2
      exit 1
    fi
  done
}

validate_reservations() {
  local network_xml_content="$1" reservation mac hostname address count
  local -a reservations=(
    "52:54:00:fa:25:01 pg01 192.168.250.201"
    "52:54:00:fa:25:02 pg02 192.168.250.202"
    "52:54:00:fa:25:03 pg03 192.168.250.203"
  )
  for reservation in "${reservations[@]}"; do
    read -r mac hostname address <<<"${reservation}"
    count="$(xmllint --xpath "count(/network/ip/dhcp/host[@mac='${mac}' and @ip='${address}' and @name='${hostname}'])" - <<<"${network_xml_content}")"
    [[ "${count}" == '1' ]] || return 1
  done
}

validate_reservation_conflicts() {
  local network_xml_content="$1" reservation mac hostname address count actual_mac actual_address
  local -a reservations=(
    "52:54:00:fa:25:01 pg01 192.168.250.201"
    "52:54:00:fa:25:02 pg02 192.168.250.202"
    "52:54:00:fa:25:03 pg03 192.168.250.203"
  )
  for reservation in "${reservations[@]}"; do
    read -r mac hostname address <<<"${reservation}"
    count="$(xmllint --xpath "count(/network/ip/dhcp/host[@ip='${address}'])" - <<<"${network_xml_content}")"
    [[ "${count}" == '0' || "${count}" == '1' ]] || {
      printf 'Address %s has multiple persistent/live reservations; inspect %s.\n' "${address}" "${network_name}" >&2
      return 1
    }
    if [[ "${count}" == '1' ]]; then
      actual_mac="$(xmllint --xpath "string(/network/ip/dhcp/host[@ip='${address}']/@mac)" - <<<"${network_xml_content}")"
      [[ "${actual_mac}" == "${mac}" ]] || {
        printf 'Address %s is reserved by MAC %s instead of %s; inspect %s.\n' "${address}" "${actual_mac}" "${mac}" "${network_name}" >&2
        return 1
      }
    fi
    count="$(xmllint --xpath "count(/network/ip/dhcp/host[@mac='${mac}'])" - <<<"${network_xml_content}")"
    if [[ "${count}" != '0' && "${count}" != '1' ]]; then
      printf 'MAC %s has multiple reservations; inspect %s.\n' "${mac}" "${network_name}" >&2
      return 1
    fi
    if [[ "${count}" == '1' ]]; then
      actual_address="$(xmllint --xpath "string(/network/ip/dhcp/host[@mac='${mac}']/@ip)" - <<<"${network_xml_content}")"
      [[ "${actual_address}" == "${address}" ]] || {
        printf 'MAC %s is reserved for another address; inspect %s.\n' "${mac}" "${network_name}" >&2
        return 1
      }
    fi
  done
}

reconcile_reservations() {
  local network_xml_content="$1" update_scope="$2"
  local reservation mac hostname address mac_count address_count actual_address actual_mac actual_hostname
  local -a reservations=(
    "52:54:00:fa:25:01 pg01 192.168.250.201"
    "52:54:00:fa:25:02 pg02 192.168.250.202"
    "52:54:00:fa:25:03 pg03 192.168.250.203"
  )

  for reservation in "${reservations[@]}"; do
    read -r mac hostname address <<<"${reservation}"
    mac_count="$(xmllint --xpath "count(/network/ip/dhcp/host[@mac='${mac}'])" - <<<"${network_xml_content}")"
    address_count="$(xmllint --xpath "count(/network/ip/dhcp/host[@ip='${address}'])" - <<<"${network_xml_content}")"
    if [[ "${mac_count}" == '1' ]]; then
      actual_address="$(xmllint --xpath "string(/network/ip/dhcp/host[@mac='${mac}']/@ip)" - <<<"${network_xml_content}")"
      actual_hostname="$(xmllint --xpath "string(/network/ip/dhcp/host[@mac='${mac}']/@name)" - <<<"${network_xml_content}")"
      [[ "${actual_address}" == "${address}" && "${actual_hostname}" == "${hostname}" ]] || {
        printf 'Reservation for MAC %s conflicts with %s; inspect %s.\n' "${mac}" "${address}" "${network_name}" >&2
        return 1
      }
      continue
    fi
    [[ "${mac_count}" == '0' && "${address_count}" == '0' ]] || {
      printf 'Reservation %s/%s conflicts with existing DHCP state; inspect %s.\n' "${mac}" "${address}" "${network_name}" >&2
      return 1
    }
    virsh -c "${virsh_uri}" net-update "${network_name}" add-last ip-dhcp-host \
      "<host mac='${mac}' name='${hostname}' ip='${address}'/>" "${update_scope}"
  done
}

network_is_active() {
  local network_info

  network_info="$(virsh -c "${virsh_uri}" net-info "${network_name}")" || return 1
  [[ "${network_info}" =~ (^|$'\n')Active:[[:space:]]+yes($|$'\n') ]]
}

network_is_autostart() {
  local network_info

  network_info="$(virsh -c "${virsh_uri}" net-info "${network_name}")" || return 1
  [[ "${network_info}" =~ (^|$'\n')Autostart:[[:space:]]+yes($|$'\n') ]]
}

ensure_network_autostart() {
  network_is_autostart && return 0
  virsh -c "${virsh_uri}" net-autostart "${network_name}"
}

start_network_if_needed() {
  if network_is_active; then
    return 0
  fi

  # A concurrent start can race the status check.  Treat that specific case
  # as success, but do not hide other net-start failures.
  if ! virsh -c "${virsh_uri}" net-start "${network_name}"; then
    network_is_active
  fi
}

if virsh -c "${virsh_uri}" net-info "${network_name}" >/dev/null 2>&1; then
  inactive_xml="$(virsh -c "${virsh_uri}" net-dumpxml --inactive "${network_name}")"
  validate_existing_network "${inactive_xml}"
  # An inactive defined network has no live XML to dump.  Validate its
  # persistent definition before changing autostart or active state instead.
  validate_reservation_conflicts "${inactive_xml}"

  if network_is_active; then
    current_xml="$(virsh -c "${virsh_uri}" net-dumpxml "${network_name}")"
    validate_existing_network "${current_xml}"
    # Check live and persistent state before mutating autostart or reservations.
    validate_reservation_conflicts "${current_xml}"
  fi

  start_network_if_needed
  ensure_network_autostart

  # Obtain live XML only after the network has been started.  Reconcile the
  # persistent definition and live state independently, then validate both.
  current_xml="$(virsh -c "${virsh_uri}" net-dumpxml "${network_name}")"
  validate_existing_network "${current_xml}"
  validate_reservation_conflicts "${current_xml}"
  reconcile_reservations "${inactive_xml}" --config
  inactive_xml="$(virsh -c "${virsh_uri}" net-dumpxml --inactive "${network_name}")"
  validate_existing_network "${inactive_xml}"
  validate_reservation_conflicts "${inactive_xml}"
  reconcile_reservations "${current_xml}" --live
  current_xml="$(virsh -c "${virsh_uri}" net-dumpxml "${network_name}")"
  validate_existing_network "${current_xml}"
  validate_reservations "${current_xml}"
  inactive_xml="$(virsh -c "${virsh_uri}" net-dumpxml --inactive "${network_name}")"
  validate_existing_network "${inactive_xml}"
  validate_reservations "${inactive_xml}"
  printf 'Libvirt network %s already exists on %s; DHCP reservations verified.\n' "${network_name}" "${virsh_uri}"
  exit 0
fi

virsh -c "${virsh_uri}" net-define "${network_xml}"
virsh -c "${virsh_uri}" net-start "${network_name}"
virsh -c "${virsh_uri}" net-autostart "${network_name}"
printf 'Created and started libvirt network %s on %s (192.168.250.0/24).\n' "${network_name}" "${virsh_uri}"
