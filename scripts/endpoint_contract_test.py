#!/usr/bin/env python3
"""Exercise the endpoint contract task with representative endpoint values."""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
CONTRACT = ROOT / "tasks/validate/test_endpoint_contract.yml"
RESULT_MARKER = "ENDPOINT_CONTRACT_RESULT "


VALID_CASES = (
    {
        "input": "Example.COM.:5432/",
        "default_scheme": "https",
        "scheme": "https",
        "has_scheme": False,
        "host": "Example.COM.",
        "canonical": "example.com",
        "rendered": "example.com:5432",
    },
    {
        "input": "http://192.0.2.10:6432",
        "default_scheme": "https",
        "scheme": "http",
        "has_scheme": True,
        "host": "192.0.2.10",
        "canonical": "192.0.2.10",
        "rendered": "http://192.0.2.10:6432",
    },
    {
        "input": "https://[2001:0DB8:0:0:0:0:0:1]:2379/",
        "default_scheme": "https",
        "scheme": "https",
        "has_scheme": True,
        "host": "2001:0DB8:0:0:0:0:0:1",
        "canonical": "2001:db8::1",
        "rendered": "https://[2001:db8::1]:2379",
    },
)

INVALID_CASES = (
    ("*.example.org:2379", "invalid host or port"),
    ("2001:db8::1:2379", "must be a host:port endpoint"),
    ("example.org", "must be a host:port endpoint"),
    ("example.org:0001", "canonical decimal digits"),
    ("[not-an-ipv6-address]:2379", "brackets are only valid"),
)


def run_contract(endpoint):
    playbook = {
        "hosts": "all",
        "gather_facts": False,
        "tasks": [
            {"ansible.builtin.include_tasks": str(CONTRACT)},
            {
                "ansible.builtin.debug": {
                    "msg": RESULT_MARKER
                    + "{{ pg_endpoint_contract_model | to_json }}"
                }
            },
        ],
        "vars": {"pg_endpoint_contract": endpoint},
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml") as temporary:
        yaml.safe_dump([playbook], temporary, sort_keys=False)
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
            text=True,
            capture_output=True,
            check=False,
        )
    return result


def assert_valid_case(case):
    result = run_contract(case)
    assert result.returncode == 0, result.stdout + result.stderr
    matches = re.findall(re.escape(RESULT_MARKER) + r"(\{.*\})", result.stdout)
    assert len(matches) == 1, result.stdout
    model = json.loads(matches[0].replace('\\"', '"'))
    for key in ("scheme", "has_scheme", "host", "canonical_host"):
        expected_key = "canonical" if key == "canonical_host" else key
        assert model[key] == case[expected_key], (case, model)
    assert model["rendered_endpoint"] == case["rendered"]


def assert_invalid_case(endpoint, expected_error):
    result = run_contract(
        {
            "input": endpoint,
            "default_scheme": "http",
            "scheme": "http",
            "has_scheme": False,
            "host": "unused",
            "canonical": "unused",
        }
    )
    assert result.returncode != 0, result.stdout
    assert expected_error in result.stdout, result.stdout + result.stderr


def main():
    for case in VALID_CASES:
        assert_valid_case(case)
    for endpoint, expected_error in INVALID_CASES:
        assert_invalid_case(endpoint, expected_error)
    print("endpoint contract normalization cases: PASS")


if __name__ == "__main__":
    sys.exit(main())
