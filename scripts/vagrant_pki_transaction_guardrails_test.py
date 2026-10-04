#!/usr/bin/env python3
"""Cheap failure-injection checks for the Vagrant PKI transaction helper."""
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "files" / "vagrant_pki_transaction.py"


def run(injection):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "pki"
        staging = root / "staging"
        (root / "client").mkdir(parents=True)
        staging.mkdir()
        for name, value in (("ca.crt", b"ca"), ("client.crt", b"client-cert"),
                            ("client.key", b"client-key"), ("peer.crt", b"peer-cert"),
                            ("peer.key", b"peer-key")):
            (staging / name).write_bytes(value)
        command = ["python3", str(HELPER), "--root", str(root), "--staging", str(staging),
                   "--transaction", "guardrail", "--inject", injection]
        environment = dict(os.environ, VAGRANT_PKI_TRANSACTION_TEST_MODE="1")
        result = subprocess.run(command, capture_output=True, text=True, check=False, env=environment)
        assert result.returncode != 0, injection
        assert (root / ".client-marker-guardrail").exists() == (injection in ("marker", "cleanup"))
        assert not (root / "client" / "etcd-client.crt").is_symlink()


for failure in ("copy", "rename", "marker", "cleanup", "backed_up", "installed", "committed", "rollback"):
    run(failure)
print("vagrant PKI transaction failure-injection guardrails: PASS")
