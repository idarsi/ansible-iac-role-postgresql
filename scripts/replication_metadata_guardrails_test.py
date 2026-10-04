#!/usr/bin/env python3
"""Check the replication metadata reader and persisted CIDR guardrails."""

import json
import os
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).parents[1]
READER = ROOT / "files/read_secure_metadata.py"
PYTHON = os.environ.get("REPLICATION_PYTHON_COMMAND", "/usr/bin/python3")


def invoke(path, *extra):
    return subprocess.run(
        [PYTHON, str(READER), *extra, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def main():
    source = {"address": "192.0.2.7", "cidr": "192.0.2.7/32"}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        metadata = root / "metadata.json"
        metadata.write_text(json.dumps(source))
        os.chmod(metadata, 0o600)

        valid = invoke(metadata, "--uid", str(os.getuid()))
        assert valid.returncode == 0, valid.stderr
        assert json.loads(valid.stdout) == source

        os.chmod(metadata, 0o640)
        assert invoke(metadata, "--uid", str(os.getuid())).returncode != 0

        metadata.write_text(json.dumps({"address": source["address"], "cidr": "192.0.2.0/24"}))
        os.chmod(metadata, 0o600)
        persisted = json.loads(metadata.read_text())
        assert persisted["cidr"] != persisted["address"] + "/32"
        converge = (ROOT / "molecule/replication/converge.yml").read_text()
        assert "pg_replication_metadata.cidr == pg_replication_metadata.address ~ '/32'" in converge

        replacement = root / "replacement.json"
        replacement.write_text(json.dumps(source))
        os.chmod(replacement, 0o600)
        metadata.unlink()
        metadata.symlink_to(replacement)
        assert invoke(metadata, "--uid", str(os.getuid())).returncode != 0

        metadata.unlink()
        metadata.mkdir()
        assert invoke(metadata, "--uid", str(os.getuid())).returncode != 0
    print("replication metadata mode, exact CIDR, symlink, and read-failure guardrails: PASS")


if __name__ == "__main__":
    main()
