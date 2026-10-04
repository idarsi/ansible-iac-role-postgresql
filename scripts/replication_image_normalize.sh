#!/bin/sh

# Validate Podman RepoDigests as syntactic aliases only. The immutable pinned
# index and selected child manifest are checked from raw image-inspect JSON.
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
  case "$replication_repo_digest" in
    index.docker.io/*) replication_repo_digest="docker.io/${replication_repo_digest#index.docker.io/}" ;;
  esac
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
  replication_seen_b33d=0
  replication_seen_d706=0
  while IFS= read -r replication_repo_digest; do
    replication_normalized_repo_digest=$(normalize_replication_base_repo_digest "$replication_repo_digest") || return 1
    [ -n "$replication_normalized_repo_digest" ] || return 1
    replication_seen=$((replication_seen + 1))
    case "$replication_normalized_repo_digest" in
      *'@sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5') replication_seen_b33d=$((replication_seen_b33d + 1)) ;;
      *'@sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4') replication_seen_d706=$((replication_seen_d706 + 1)) ;;
      *) return 1 ;;
    esac
  done <<EOF
$replication_repo_digests
EOF
  [ "$replication_seen" -ge 1 ] || return 1
  [ "$replication_seen_b33d" -le 1 ] && [ "$replication_seen_d706" -le 1 ] || return 1
  printf '%s\n' "$replication_base_ref"
}
