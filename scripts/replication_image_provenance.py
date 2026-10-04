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
EXPECTED_AMD64_CHILD_DIGEST = "sha256:d706f937383b94727cfece22e2e29d67e26ed85c8156993e4718ca68c5e7dcd4"
EXPECTED_PINNED_DIGEST = "sha256:b33dfee97df5b631945b9b04ffc2f4deb28862db927c86cb0afb94ef9861dfb5"
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
    normalized = f"docker.io/{match.group('repository')}@{match.group('digest')}"
    return normalized if normalized in OBSERVED_REPO_DIGESTS else None


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
    """Validate only the observed canonical aliases, never image identity."""
    if not isinstance(values, list) or not values:
        raise ValueError(f"{name} image has no valid RepoDigests")
    normalized = [normalize_repo_digest(value) for value in values]
    if (
        any(value is None for value in normalized)
        or any(value not in OBSERVED_REPO_DIGESTS for value in normalized)
        or len(set(normalized)) != len(normalized)
    ):
        raise ValueError(f"{name} image has unknown or duplicate RepoDigests")
    return normalized


def validate_index(value: str, name: str = "base") -> None:
    """Require the inspected pinned OCI index to name its linux/amd64 child."""
    index = load(value, f"{name} OCI index")
    manifests = index.get("manifests")
    if not isinstance(manifests, list) or not manifests:
        raise ValueError(
            f"{name} OCI index inspection is unavailable or has no manifests"
        )
    matches = []
    for manifest in manifests:
        if not isinstance(manifest, dict):
            continue
        platform = manifest.get("platform")
        if (
            isinstance(platform, dict)
            and platform.get("os") == "linux"
            and platform.get("architecture") == "amd64"
            and normalize_digest(manifest.get("digest")) == EXPECTED_AMD64_CHILD_DIGEST
        ):
            matches.append(manifest)
    if len(matches) != 1:
        raise ValueError(
            f"{name} OCI index does not contain exactly one expected linux/amd64 child"
        )


def validate_pinned_object(value: str, image: dict, name: str = "base") -> None:
    """Validate Podman-backed metadata for the pinned OCI index or a direct platform manifest."""
    document = load(value, f"{name} OCI object")
    media_type = document.get("mediaType")
    if media_type in {
        "application/vnd.oci.image.index.v1+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
    }:
        validate_index(value, name)
        selected_child_digest(image, name)
        return
    if media_type in {
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.docker.distribution.manifest.v2+json",
    }:
        if normalize_digest(image.get("Digest")) != EXPECTED_PINNED_DIGEST:
            raise ValueError(f"{name} direct manifest is not the pinned digest")
        if image.get("Architecture") != "amd64" or image.get("Os") != "linux":
            raise ValueError(f"{name} direct manifest is not linux/amd64")
        return
    raise ValueError(f"{name} OCI object has an unsupported media type")


def selected_child_digest(image: dict, name: str) -> str:
    """Return Podman's selected platform manifest digest, not an alias."""
    digest = normalize_digest(image.get("Digest"))
    if digest != EXPECTED_AMD64_CHILD_DIGEST:
        raise ValueError(
            f"{name} selected child manifest is not the expected linux/amd64 digest"
        )
    if image.get("Architecture") != "amd64" or image.get("Os") != "linux":
        raise ValueError(f"{name} image is not the native linux/amd64 image")
    return digest


def normalize_image_json(value: str, index_json: str, name: str = "base") -> str:
    image = load(value, name)
    validate_pinned_object(index_json, image, name)
    normalize_repo_digests(image.get("RepoDigests"), name)
    return json.dumps(image, separators=(",", ":"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-json")
    parser.add_argument("--derived-json")
    parser.add_argument("--base-id")
    parser.add_argument("--repo-digest")
    parser.add_argument("--normalize-json")
    parser.add_argument("--index-json")
    args = parser.parse_args()
    try:
        if args.normalize_json is not None:
            if args.index_json is None:
                raise ValueError(
                    "--index-json is required; refusing independent image-field validation"
                )
            print(normalize_image_json(args.normalize_json, args.index_json))
            return 0
        if args.base_id is None or args.repo_digest is None:
            raise ValueError("--base-id and --repo-digest are required for comparison")
        if args.base_json is None or args.derived_json is None:
            raise ValueError(
                "--base-json and --derived-json are required for comparison"
            )
        if args.index_json is None:
            raise ValueError(
                "--index-json is required; refusing independent image-field validation"
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
        validate_pinned_object(args.index_json, base)
        normalize_repo_digests(base.get("RepoDigests"), "base")
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
