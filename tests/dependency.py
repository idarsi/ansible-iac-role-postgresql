#!/usr/bin/env python3
"""Install scenario collections into the helper-resolved private context.

Molecule expands explicit scenario/cache/env-file/helper arguments in each
scenario's dependency command. Its shell plugin does not export Config.env to
the subprocess. Bind only those validated Molecule paths for helper resolution;
inherit genuine IDARSI_RUN_ID/IDARSI_HANDOFF* unchanged. Uses resolve, never init.
The installer and its lock are role-owned; no shared controller environment is
modified. Scenario manifests remain molecule/SCENARIO/collections.yml.
"""

from __future__ import annotations

import fcntl
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys

import yaml


def galaxy_environment(
    destination: Path, environment: dict[str, str]
) -> dict[str, str]:
    """Restrict Galaxy's installed-collection discovery to this private context."""
    child = dict(environment)
    child["ANSIBLE_COLLECTIONS_PATH"] = str(destination)
    child["ANSIBLE_COLLECTIONS_SCAN_SYS_PATH"] = "false"
    child.pop("ANSIBLE_COLLECTIONS_PATHS", None)
    return child


def required_collections(manifest: Path) -> list[dict[str, str]]:
    """Read role-owned exact pins so successful CLI exit is not installation proof."""
    document = yaml.safe_load(manifest.read_text())
    records = document.get("collections") if isinstance(document, dict) else None
    if not isinstance(records, list):
        raise ValueError("Collection manifest must contain a collections list")
    for record in records:
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("name"), str)
            or not re.fullmatch(r"[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*", record["name"])
            or not isinstance(record.get("version"), str)
            or not re.fullmatch(r"\d+\.\d+\.\d+", record["version"])
        ):
            raise ValueError(
                "Role test collections require FQCN names and exact version pins"
            )
    return records


def verify_private_collection(destination: Path, name: str, version: str) -> None:
    """Require regular installed metadata under the private physical destination."""
    namespace, collection = name.split(".")
    directory = destination / "ansible_collections" / namespace / collection
    for path in (destination / "ansible_collections", directory.parent, directory):
        if path.is_symlink() or not path.is_dir():
            raise ValueError("Private collection is missing or uses a symlink: " + name)
    for filename in ("MANIFEST.json", "FILES.json"):
        path = directory / filename
        if path.is_symlink() or not path.is_file():
            raise ValueError("Private collection metadata is missing: " + name)
    info = json.loads((directory / "MANIFEST.json").read_text())["collection_info"]
    if (
        info.get("namespace") != namespace
        or info.get("name") != collection
        or info.get("version") != version
    ):
        raise ValueError("Private collection does not match its declared pin: " + name)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "scenario-directory",
        "ephemeral-directory",
        "molecule-file",
        "env-file",
        "helper-directory",
    ):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    role = Path(__file__).resolve().parents[1]
    if Path(args.scenario_directory).is_symlink():
        raise ValueError("Scenario directory must not be a symlink")
    scenario_directory = Path(args.scenario_directory).resolve(strict=True)
    if scenario_directory.parent != role / "molecule":
        raise ValueError("Scenario directory must be an immediate role-owned scenario")
    scenario = scenario_directory.name
    source = scenario_directory / "molecule.yml"
    if not source.is_file() or source.is_symlink():
        raise ValueError("Scenario must have a regular role-owned molecule.yml")
    metadata = json.loads((role / "role-test.json").read_text())
    backend = metadata["scenarios"][scenario]["execution"]["backend"]
    if backend not in {"podman", "kvm"}:
        raise ValueError("Scenario metadata must declare a native backend")
    ephemeral = Path(args.ephemeral_directory)
    molecule_file = Path(args.molecule_file)
    helper_directory = Path(args.helper_directory).resolve(strict=True)
    if not ephemeral.is_absolute() or not molecule_file.is_absolute():
        raise ValueError("Molecule must supply absolute effective context paths")
    if any(
        path.is_symlink() for path in (ephemeral, *ephemeral.parents, molecule_file)
    ):
        raise ValueError("Effective context paths must not use symlinks")
    ephemeral = ephemeral.resolve()
    if ephemeral == Path("/") or not molecule_file.resolve().is_relative_to(ephemeral):
        raise ValueError("Effective Molecule file must belong to its ephemeral context")
    # The helper independently validates these against installed Molecule's
    # effective configuration. Never create or replace supervision markers.
    environment = dict(os.environ)
    bindings = {
        "MOLECULE_PROJECT_DIRECTORY": str(role),
        "MOLECULE_SCENARIO_DIRECTORY": str(scenario_directory),
        "MOLECULE_SCENARIO_NAME": scenario,
        "MOLECULE_EPHEMERAL_DIRECTORY": str(ephemeral),
        "MOLECULE_FILE": str(molecule_file.resolve()),
        "MOLECULE_ENV_FILE": args.env_file,
        "IDARSI_TEST_ENVIRONMENT": str(helper_directory),
    }
    for key, value in bindings.items():
        if key in environment:
            previous = environment[key]
            matches = previous == value
            if key == "MOLECULE_ENV_FILE":
                if previous not in {"", "None"} and value not in {"", "None"}:
                    matches = Path(previous).resolve() == Path(value).resolve()
            elif key != "MOLECULE_SCENARIO_NAME":
                matches = (
                    bool(previous) and Path(previous).resolve() == Path(value).resolve()
                )
            if not matches:
                raise ValueError("Conflicting inherited context binding: " + key)
        environment[key] = value
    helper = helper_directory / "scripts/scenario-context"
    supervised = any(
        key == "IDARSI_RUN_ID" or key.startswith("IDARSI_HANDOFF")
        for key in environment
    )
    result = subprocess.run(
        [
            str(helper),
            "resolve",
            "--backend",
            backend,
            "--scenario",
            scenario,
            "--role",
            str(role),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    context = json.loads(result.stdout)
    if not isinstance(context, dict):
        raise ValueError("Helper response must be a scenario context object")
    if (
        context.get("schema") != "idarsi.scenario-context/v1"
        or context.get("effective_config_validated") is not True
        or set(context.get("lifecycle_modes", [])) != {"direct", "supervised"}
        or context.get("role") != str(role)
        or context.get("scenario") != scenario
        or context.get("backend") != backend
        or context.get("mode") != ("supervised" if supervised else "direct")
        or context.get("ephemeral_directory") != str(ephemeral)
    ):
        raise ValueError("Helper returned an invalid scenario context")
    destination = Path(context["collections_directory"])
    if not destination.is_absolute() or destination != ephemeral / "collections":
        raise ValueError(
            "Collections directory must belong to the resolved ephemeral context"
        )
    # Resolve already-existing ancestors without following a substituted symlink.
    for ancestor in reversed((destination, *destination.parents)):
        if ancestor.is_symlink():
            raise ValueError("Symlink in collections directory")
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = destination.stat()
    if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
        raise ValueError("Collections directory must be controller-owned and private")
    lock = destination / ".postgresql-galaxy.lock"
    fd = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w") as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_mode & 0o077
        ):
            raise ValueError("Unsafe collection installation lock")
        fcntl.flock(stream, fcntl.LOCK_EX)
        manifests = [role / "tests" / "collections.yml"]
        requirements = role / "molecule" / scenario / "collections.yml"
        if requirements.exists():
            manifests.append(requirements)
        expected = [
            record
            for manifest in manifests
            for record in required_collections(manifest)
        ]
        installer_environment = galaxy_environment(destination, environment)
        for manifest in manifests:
            subprocess.run(
                [
                    "ansible-galaxy",
                    "collection",
                    "install",
                    "-r",
                    str(manifest),
                    "-p",
                    str(destination),
                ],
                check=True,
                env=installer_environment,
            )
        for record in expected:
            verify_private_collection(destination, record["name"], record["version"])


if __name__ == "__main__":
    try:
        main()
    except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"Scenario dependency bootstrap failed: {error}", file=sys.stderr)
        sys.exit(1)
