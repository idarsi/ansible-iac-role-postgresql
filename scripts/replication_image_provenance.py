#!/usr/bin/env python3
"""Check that a derived image retains the inspected base image layer chain."""

import argparse
import json
import re
import sys

DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
EXPECTED_REPO_DIGEST = (
    "docker.io/rockylinux/rockylinux:9-ubi-init@"
    "sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
)
OBSERVED_EQUIVALENT_REPO_DIGEST = (
    "docker.io/rockylinux/rockylinux@"
    "sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4"
)
OBSERVED_UNTAGGED_B33D_REPO_DIGEST = (
    "docker.io/rockylinux/rockylinux@"
    "sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
)
OBSERVED_REPO_DIGESTS = {
    OBSERVED_UNTAGGED_B33D_REPO_DIGEST,
    OBSERVED_EQUIVALENT_REPO_DIGEST,
}
REPO_DIGEST_PATTERN = re.compile(
    r"^(?P<registry>(?:docker\.io|index\.docker\.io))/"
    r"(?P<repository>rockylinux/rockylinux)@(?P<digest>sha256:[0-9a-f]{64})$"
)


def normalize_digest(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    candidate = value.removeprefix("sha256:")
    if re.fullmatch(r"[0-9a-f]{64}", candidate):
        return f"sha256:{candidate}"
    return None


def normalize_repo_digest(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = REPO_DIGEST_PATTERN.fullmatch(value)
    if match is None:
        return None
    return f"docker.io/{match.group('repository')}@{match.group('digest')}"


def repo_digest_alias_kind(value: object) -> str | None:
    """Return the accepted alias form without discarding its spelling."""
    if not isinstance(value, str):
        return None
    if value == OBSERVED_UNTAGGED_B33D_REPO_DIGEST:
        return "untagged-b33d"
    if value == OBSERVED_EQUIVALENT_REPO_DIGEST:
        return "untagged-d706"
    return None


def load(value: str, name: str) -> dict:
    try:
        result = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{name} inspection is not JSON: {error}") from error
    if not isinstance(result, dict):
        raise ValueError(f"{name} inspection must be a JSON object")
    return result


def layers(image: dict, name: str) -> list[str]:
    rootfs = image.get("RootFS")
    image_layers = rootfs.get("Layers") if isinstance(rootfs, dict) else None
    if (
        not isinstance(image_layers, list)
        or not image_layers
        or not all(
            isinstance(layer, str) and DIGEST_PATTERN.fullmatch(layer)
            for layer in image_layers
        )
    ):
        raise ValueError(f"{name} image has no valid RootFS.Layers")
    return image_layers


def normalize_repo_digests(values: object, name: str) -> list[str]:
    """Validate the exact two untagged Podman RepoDigests aliases.

    The tagged pinned reference is supplied independently; it is not a
    RepoDigests entry in the Podman output.
    """
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} image has no valid RepoDigests")
    if len(values) != 2:
        raise ValueError(f"{name} RepoDigests must contain the exact two untagged aliases")
    normalized = [normalize_repo_digest(value) for value in values]
    kinds = [repo_digest_alias_kind(value) for value in normalized]
    if any(value is None for value in normalized):
        raise ValueError(f"{name} image has no valid RepoDigests")
    if any(kind is None for kind in kinds) or sorted(kinds) != ["untagged-b33d", "untagged-d706"]:
        raise ValueError(f"{name} RepoDigests contains duplicate or unsupported aliases")
    return normalized


def normalize_image_json(value: str, name: str = "base") -> str:
    image = load(value, name)
    # Validate without discarding the observed triple: the inspection artifact
    # must retain the evidence that both untagged aliases were present.
    normalize_repo_digests(image.get("RepoDigests"), name)
    return json.dumps(image, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-json")
    parser.add_argument("--derived-json")
    parser.add_argument("--base-id")
    parser.add_argument("--repo-digest")
    parser.add_argument("--normalize-json")
    args = parser.parse_args()
    try:
        if args.normalize_json is not None:
            print(normalize_image_json(args.normalize_json))
            return 0
        if args.base_id is None or args.repo_digest is None:
            raise ValueError("--base-id and --repo-digest are required for comparison")
        if args.base_json is None or args.derived_json is None:
            raise ValueError(
                "--base-json and --derived-json are required for comparison"
            )
        base = load(args.base_json, "base")
        derived = load(args.derived_json, "derived")
        recorded_base_id = normalize_digest(args.base_id)
        if recorded_base_id is None:
            raise ValueError("recorded base ID is not a valid sha256 digest")
        # The recorded value is a provenance claim, not merely a digest-shaped
        # input: only the exact repository, tag, and pinned digest is valid.
        if args.repo_digest != EXPECTED_REPO_DIGEST:
            raise ValueError(
                "recorded base repo digest is not the expected pinned digest"
            )
        if normalize_digest(base.get("Id")) != recorded_base_id:
            raise ValueError("inspected base ID differs from recorded base ID")
        base_repo_digests = normalize_repo_digests(base.get("RepoDigests"), "base")
        if set(base_repo_digests) != OBSERVED_REPO_DIGESTS:
            raise ValueError("inspected base RepoDigests contains unexpected aliases")
        # A derived image is a separate artifact.  Builders commonly publish
        # it under different repository aliases (or without RepoDigests), so
        # never apply the base image's alias set to the derived image.
        base_layers = layers(base, "base")
        derived_layers = layers(derived, "derived")
        if derived_layers[: len(base_layers)] != base_layers:
            raise ValueError(
                "derived RootFS.Layers does not retain the base layer prefix"
            )
    except ValueError as error:
        print(f"replication image provenance failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
