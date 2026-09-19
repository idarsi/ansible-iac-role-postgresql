#!/usr/bin/env python3
"""Execute the cluster PKI collision contract through Ansible itself."""

import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ANSIBLE_PLAYBOOK = os.environ.get("ANSIBLE_PLAYBOOK_COMMAND", "ansible-playbook")
PLAYBOOK = ROOT / "scripts/fixtures/cluster_collision_paths.yml"
ANSIBLE_TIMEOUT_SECONDS = float(os.environ.get("CLUSTER_COLLISION_TIMEOUT", "120"))

if ANSIBLE_TIMEOUT_SECONDS <= 0:
    raise ValueError("CLUSTER_COLLISION_TIMEOUT must be greater than zero")


def assert_cluster_normalization_contract():
    """Keep loop input separate from the normalized record consumed below it."""
    version_text = (ROOT / "tasks/validate/validate_version.yml").read_text()
    cluster_text = (ROOT / "tasks/validate/validate_cluster.yml").read_text()
    assert "loop_var: pg_validation_cluster_input" in version_text
    assert "pg_validation_cluster_record: \"{{ pg_validation_cluster_input | combine({}, recursive=true) }}\"" in cluster_text
    assert cluster_text.count("pg_validation_cluster_input") == 1, (
        "cluster consumers must use the normalized record"
    )
    for consumer in (
        "pg_patroni_restapi_tls_enabled",
        "pg_patroni_explicit_tls_path_count",
        "pg_patroni_cafile_canonical",
        "pg_patroni_certfile_canonical",
        "pg_patroni_keyfile_canonical",
    ):
        assert consumer in cluster_text, f"missing normalized TLS consumer: {consumer}"


def cluster_for(case_name, root):
    """Build only fixture input; normalization and validation remain in the role."""
    paths = {
        "patroni_ca": f"{root}/generated/patroni/ca.crt",
        "patroni_cert": f"{root}/generated/patroni/server.crt",
        "patroni_key": f"{root}/generated/patroni/server.key",
        "etcd_ca": f"{root}/generated/etcd/ca.crt",
        "etcd_client_cert": f"{root}/generated/etcd/client.crt",
        "etcd_client_key": f"{root}/generated/etcd/client.key",
        "etcd_peer_cert": f"{root}/generated/etcd/peer.crt",
        "etcd_peer_key": f"{root}/generated/etcd/peer.key",
    }
    base = {
        "name": "collision-fixture",
        "provider": "patroni",
        "members": [{"host": "localhost"}],
        "patroni": {"restapi": {"auto_generate": True, "cafile": paths["patroni_ca"],
                                  "certfile": paths["patroni_cert"], "keyfile": paths["patroni_key"]}},
        "dcs": {
            "etcd": {
                "enabled": True,
                "members": [{"host": "localhost"}],
                "tls": {"auto_generate": True, "ca_file": paths["etcd_ca"],
                        "client": {"ca_file": paths["etcd_ca"],
                                   "cert_file": paths["etcd_client_cert"],
                                   "key_file": paths["etcd_client_key"]},
                        "peer": {"ca_file": paths["etcd_ca"],
                                  "cert_file": paths["etcd_peer_cert"],
                                  "key_file": paths["etcd_peer_key"]}},
            }
        },
    }
    if case_name == "role-coverage-is-complete":
        # This coverage fixture intentionally omits generated-etcd so the
        # role-coverage assertion proves that an absent occurrence is caught.
        base["dcs"] = {"etcd": {"enabled": False}}
    if case_name == "managed-role-collision-is-rejected":
        base["seed_directory"] = f"{root}/registry"
    elif case_name == "shared-ca-is-allowed":
        base["provider"] = "etcd"
        base["patroni"] = {}
    elif case_name == "ca-and-non-ca-collision-is-rejected":
        base["provider"] = "etcd"
        base["patroni"] = {}
        base["dcs"]["etcd"]["tls"]["client"] = {
            "cert_file": paths["etcd_ca"]
        }
    elif case_name == "missing-normalized-destinations-are-valid":
        base["patroni"] = {
            "restapi": {
                "cafile": f"{root}/missing/ca.crt",
                "certfile": f"{root}/missing/server.crt",
                "keyfile": f"{root}/missing/server.key",
            }
        }
        base["dcs"] = {"etcd": {"enabled": False}}
    elif case_name == "disabled-tls-is-valid":
        base["patroni"] = {"restapi": {}}
        base["dcs"] = {"etcd": {"enabled": False}}
    elif case_name == "patroni-only-is-valid":
        base["dcs"] = {"etcd": {"enabled": False}}
    elif case_name == "etcd-only-is-valid":
        base["provider"] = "etcd"
        base["patroni"] = {}
    return base


def main():
    assert_cluster_normalization_contract()
    fixture = json.loads(
        (ROOT / "scripts/fixtures/cluster_collision_paths.json").read_text()
    )
    for case in fixture:
        # Every scenario gets an isolated root.  Nothing in the contract may
        # inspect a production path, including cases expected to fail.
        with tempfile.TemporaryDirectory(prefix="cluster-collision-") as temporary:
            root = Path(temporary)
            paths = {
                "metadata_directory": str(root / "metadata"),
                "seed_directory": str(root / "seed"),
                "registry_directory": str(root / "registry"),
                "lock_directory": str(root / "lock"),
                "registry_path": str(root / "registry" / "fixture.serials"),
                "lock_path": str(root / "lock" / "fixture.lock"),
            }
            if case["name"] == "managed-role-collision-is-rejected":
                paths["seed_directory"] = paths["registry_directory"]
            for directory in ("metadata", "seed", "registry", "lock", "missing",
                              "generated/patroni", "generated/etcd"):
                (root / directory).mkdir(parents=True, exist_ok=True)
            variables = {
                "fixture_case": case["name"],
                "pg_cluster": cluster_for(case["name"], temporary),
                "fixture_root": temporary,
                "fixture_paths": paths,
                "fixture_role_coverage_case": case["name"] == "role-coverage-is-complete",
                "pg_version": "17",
            }
            variables_path = root / f"{case['name']}.json"
            # Execute the production controller-safe collision path directly.
            # It includes production cluster_certificates_normalize.yml and
            # validate/normalize_path.yml, but deliberately excludes host
            # inspection and convergence tasks (and therefore privilege
            # escalation).
            variables["fixture_preflight_path"] = str(
                ROOT / "tasks/cluster_certificates_collision_preflight.yml"
            )
            variables_path.write_text(json.dumps(variables))
            command = [ANSIBLE_PLAYBOOK, "-i", "localhost,", str(PLAYBOOK),
                       "--extra-vars", f"@{variables_path}"]
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
                env={**os.environ, "ANSIBLE_BECOME_ASK_PASS": "false",
                     "ANSIBLE_DISPLAY_OK_HOSTS": "false",
                     "ANSIBLE_DISPLAY_SKIPPED_HOSTS": "false"},
            )
            try:
                stdout, stderr = process.communicate(timeout=ANSIBLE_TIMEOUT_SECONDS)
                result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
            except subprocess.TimeoutExpired as error:
                # ansible-playbook can leave module children behind; terminate
                # the complete disposable process group before reporting the
                # bounded failure.
                os.killpg(process.pid, signal.SIGKILL)
                stdout, stderr = process.communicate()
                captured = "".join(
                    part.decode(errors="replace") if isinstance(part, bytes) else part or ""
                    for part in (stdout, stderr)
                )
                raise AssertionError(
                    f"{case['name']} timed out after {ANSIBLE_TIMEOUT_SECONDS:g}s; "
                    "the local fixture must not wait for privilege escalation.\n"
                    f"command: {' '.join(command)}\n{captured}"
                ) from error
            output = result.stdout + result.stderr
            valid = result.returncode == 0
            assert valid == case["valid"], (
                f"{case['name']} failed with exit code {result.returncode}; "
                f"command: {' '.join(command)}\n{output}"
            )
            if not valid:
                assert case["expected_failure_message"] in output, (
                    f"{case['name']} missing expected failure message:\n{output}"
                )

    print("cluster collision contract: PASS")


if __name__ == "__main__":
    main()
