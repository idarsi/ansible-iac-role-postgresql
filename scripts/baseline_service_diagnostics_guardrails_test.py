#!/usr/bin/env python3
"""Guard baseline service verification against losing failure diagnostics."""

from pathlib import Path
import re


ROOT = Path(__file__).parents[1]
BASELINES = (
    "molecule/rhel8-baseline/verify.yml",
    "molecule/rocky8-baseline/verify.yml",
    "molecule/rhel9-full/verify.yml",
    "molecule/rocky9-full/verify.yml",
    "molecule/rhel10-baseline/verify.yml",
    "molecule/rocky10-baseline/verify.yml",
)


for relative_path in BASELINES:
    text = (ROOT / relative_path).read_text()
    assert re.search(
        r"Checking PostgreSQL (?:services are enabled|service enablement).*?"
        r"register: pg_service_enabled_checks.*?failed_when: false",
        text,
        re.DOTALL,
    ), f"{relative_path}: enablement check must be non-fatal"
    assert re.search(
        r"Checking PostgreSQL (?:services are active|services).*?"
        r".*?register: pg_service_checks.*?failed_when: false",
        text,
        re.DOTALL,
    ), f"{relative_path}: active check must be non-fatal"
    assert "pg_service_checks.results | zip(pg_service_enabled_checks.results)" in text, (
        f"{relative_path}: journal diagnostics must correlate active and enabled checks"
    )
    assert "when: item.0.rc != 0 or item.1.rc != 0" in text, (
        f"{relative_path}: journal diagnostics must run for either failure"
    )
    assert 'fail_msg: "One or more PostgreSQL services are not enabled"' in text, (
        f"{relative_path}: enablement must remain a strict assertion"
    )

print("Baseline service diagnostics guardrail passed")
