#!/usr/bin/env python3
"""Exercise managed-etcd endpoint-index contracts."""

import shutil
import subprocess
import tempfile
import os
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
INVENTORY_TASKS = ROOT / "tasks/validate/validate_inventory.yml"


def main() -> None:
    playbook = [
        {
            "hosts": "all",
            "gather_facts": False,
            "vars": {
                "state": "validate",
                "iac_blueprint": {"postgresql": []},
                "pg_versions": [],
                "pg_etcd_data_directory": "/var/lib/etcd",
            },
            "tasks": [
                {"ansible.builtin.include_tasks": str(INVENTORY_TASKS)},
                {
                    "ansible.builtin.assert": {
                        "that": [
                            "pg_validation_managed_etcd_records == []",
                            "pg_validation_etcd_endpoint_index | type_debug == 'list'",
                            "pg_validation_etcd_endpoint_index == []",
                        ],
                        "fail_msg": "Empty managed-etcd input must publish a native empty list",
                    }
                },
            ],
        },
        {
            "hosts": "all",
            "gather_facts": False,
            "vars": {
                "state": "validate",
                "iac_blueprint": {
                    "postgresql": [
                        {
                            "version": 17,
                            "clusters": [
                                {
                                    "name": "contract-etcd",
                                    "provider": "patroni",
                                    "dcs": {
                                        "provider": "etcd3",
                                        "endpoints": ["https://etcd.example.org:2379"],
                                        "etcd": {
                                            "enabled": True,
                                            "members": [
                                                {
                                                    "name": "etcd01",
                                                    "host": "localhost",
                                                    "peer_url": "https://etcd.example.org:2380",
                                                    "client_url": "https://etcd.example.org:2379",
                                                }
                                            ],
                                        },
                                    },
                                    "patroni": {
                                        "restapi": {
                                            "authentication": {
                                                "username": "patroni",
                                                "password": "fake-password",
                                            }
                                        }
                                    },
                                    "members": [
                                        {
                                            "host": "localhost",
                                            "instance": "main",
                                            "name": "member",
                                        }
                                    ],
                                }
                            ],
                            "instances": [
                                {"name": "main", "cluster": "contract-etcd"}
                            ],
                        }
                    ]
                },
                "pg_versions": "{{ iac_blueprint.postgresql }}",
                "pg_contract_cluster_models": [
                    {
                        "key": "17:contract-etcd",
                        "version": "17",
                        "record": {
                            "name": "contract-etcd",
                            "dcs": {
                                "etcd": {
                                    "members_normalized": [
                                        {
                                            "name": "etcd01",
                                            "host": "localhost",
                                            "peer_url": "https://etcd.example.org:2380",
                                            "client_url": "https://etcd.example.org:2379",
                                            "peer_endpoint_model": {
                                                "san_identities": ["etcd.example.org"]
                                            },
                                            "client_endpoint_model": {
                                                "canonical_endpoint": "etcd.example.org:2379",
                                                "canonical_host": "etcd.example.org",
                                                "has_scheme": True,
                                                "host": "etcd.example.org",
                                                "host_is_ipv6": False,
                                                "is_wildcard": False,
                                                "path": "",
                                                "port": 2379,
                                                "protocol": "https",
                                                "rendered_endpoint": "https://etcd.example.org:2379",
                                                "rendered_host": "etcd.example.org",
                                                "san_identities": ["etcd.example.org"],
                                                "scheme": "https",
                                                "scheme_free_endpoint": "etcd.example.org:2379",
                                                "uri": "https://etcd.example.org:2379",
                                            },
                                        }
                                    ]
                                }
                            },
                        },
                    }
                ],
            },
            "tasks": [
                {"ansible.builtin.set_fact": {"pg_validation_cluster_models": "{{ pg_contract_cluster_models }}"}},
                {"ansible.builtin.include_tasks": str(ROOT / "tasks/validate/publish_etcd_endpoint_index.yml")},
                {
                    "ansible.builtin.assert": {
                        "that": [
                            "pg_validation_etcd_endpoint_index | length == 1",
                            "pg_validation_etcd_endpoint_index[0].keys() | list | sort == ["
                            "'canonical_endpoint', 'canonical_host', 'client_url', 'cluster', "
                            "'has_scheme', 'host', 'host_is_ipv6', 'key', 'member', 'name', "
                            "'path', 'peer_url', 'protocol', 'rendered_endpoint', 'rendered_host', "
                            "'san_identities', 'scheme', 'scheme_free_endpoint', 'uri', 'version'"
                            "]",
                            "'port' not in pg_validation_etcd_endpoint_index[0]",
                            "'is_wildcard' not in pg_validation_etcd_endpoint_index[0]",
                            "pg_validation_etcd_endpoint_index[0].canonical_endpoint == 'etcd.example.org:2379'",
                            "pg_validation_etcd_endpoint_index[0].rendered_endpoint == 'https://etcd.example.org:2379'",
                            "pg_validation_etcd_endpoint_index[0].key == '17:contract-etcd:localhost'",
                            "pg_validation_etcd_endpoint_index[0].san_identities == ['etcd.example.org']",
                        ],
                        "fail_msg": "Non-empty managed-etcd endpoint index must publish its canonical projected schema",
                    }
                },
            ],
        },
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml") as temporary:
        yaml.safe_dump(playbook, temporary, sort_keys=False)
        temporary.flush()
        result = subprocess.run(
            [
                shutil.which("ansible-playbook") or "ansible-playbook",
                "-i",
                "localhost,",
                "-c",
                "local",
            temporary.name,
            ],
            cwd=ROOT,
            env={**os.environ, "ANSIBLE_ROLES_PATH": str(ROOT.parent)},
            text=True,
            capture_output=True,
            check=False,
        )

    assert result.returncode == 0, result.stdout + result.stderr
    print("managed-etcd endpoint index list contracts: PASS")


if __name__ == "__main__":
    main()
