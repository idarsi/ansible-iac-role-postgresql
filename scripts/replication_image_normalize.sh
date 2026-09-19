#!/bin/sh

# Validate the exact two untagged Podman RepoDigests observed for the replication
# base image. Keep these functions side-effect free so CI and the local
# Molecule wrapper use the same fail-closed contract.
normalize_replication_sha256() {
  replication_digest=$1
  case "$replication_digest" in
    sha256:*) replication_digest=${replication_digest#sha256:} ;;
  esac
  printf '%s\n' "$replication_digest" | awk '
    length($0) == 64 && $0 !~ /[^0-9a-f]/ { print "sha256:" $0; exit }
    { exit 1 }
  '
}

normalize_replication_base_repo_digest() {
  replication_repo_digest=$1
  replication_repo_digest=${replication_repo_digest/index.docker.io/docker.io}
  case "$replication_repo_digest" in
    docker.io/rockylinux/rockylinux@sha256:*) ;;
    *) return 1 ;;
  esac
  replication_digest=${replication_repo_digest##*@}
  case "$replication_digest" in
    sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5|sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4)
      printf '%s\n' "docker.io/rockylinux/rockylinux@${replication_digest}" ;;
    *) return 1 ;;
  esac
}

validate_replication_base_repo_digests() {
  [ "$replication_base_ref" = "docker.io/rockylinux/rockylinux:9-ubi-init@${replication_expected_digest}" ] || return 1
  replication_repo_digests=$(awk '
    NF { print; count++; next }
    { exit 1 }
    END { if (count < 1) exit 1 }
  ') || return 1
  replication_seen=0
  replication_untagged_b33d=0
  replication_untagged_d706=0
  while IFS= read -r replication_repo_digest; do
    replication_normalized_repo_digest=$(normalize_replication_base_repo_digest "$replication_repo_digest") || return 1
    [ -n "$replication_normalized_repo_digest" ] || return 1
    replication_seen=$((replication_seen + 1))
    case "$replication_normalized_repo_digest" in
      docker.io/rockylinux/rockylinux@${replication_expected_digest}) replication_untagged_b33d=$((replication_untagged_b33d + 1)) ;;
      docker.io/rockylinux/rockylinux@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4) replication_untagged_d706=$((replication_untagged_d706 + 1)) ;;
      *) return 1 ;;
    esac
  done <<EOF
$replication_repo_digests
EOF
  [ "$replication_seen" -eq 2 ] &&
    [ "$replication_untagged_b33d" -eq 1 ] &&
    [ "$replication_untagged_d706" -eq 1 ] || return 1
  printf '%s\n' "$replication_base_ref"
}
