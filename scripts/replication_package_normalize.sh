#!/bin/sh

# RPM prints an epoch of zero in some query formats and omits it in others.
# Older query formats can also render an absent epoch as `(none)`. Accept only
# those representations of the one pinned package; every
# package name, epoch, version, release, and architecture remains exact.
normalize_replication_iproute_nevra() {
  replication_expected_nevra=$1
  replication_actual_nevra=$2
  # rpm query formats normally terminate each record with a newline.  Accept
  # exactly one record terminator, but never discard a second record.
  replication_newline='
'
  case "$replication_actual_nevra" in
    *"$replication_newline") replication_actual_nevra=${replication_actual_nevra%"$replication_newline"} ;;
  esac
  case "$replication_actual_nevra" in
    *"$replication_newline"*) return 1 ;;
  esac
  replication_without_epoch=$(printf '%s\n' "$replication_expected_nevra" | \
    sed 's/-0:/-/')
  replication_with_none_epoch=$(printf '%s\n' "$replication_expected_nevra" | \
    sed 's/-0:/-(none):/')
  case "$replication_actual_nevra" in
    "$replication_expected_nevra"|"$replication_without_epoch"|"$replication_with_none_epoch")
      printf '%s\n' "$replication_expected_nevra"
      ;;
    *) return 1 ;;
  esac
}
