#!/usr/bin/env python3
"""Regression guard for replication prerequisite validation precedence."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def main():
    fixture = yaml.safe_load(
        (ROOT / "scripts/fixtures/replication_prerequisite_precedence.yml").read_text()
    )
    assert len(fixture["primary"]["cases"]) == 7
    assert len(fixture["standby"]["cases"]) == 9
    assert any("replication_user" not in case["record"] for case in fixture["primary"]["cases"])
    assert any(case["record"].get("replication_user") == "" for case in fixture["primary"]["cases"])
    assert any("primary_port" not in case["record"] for case in fixture["standby"]["cases"])
    assert any(case["record"].get("primary_port") == "" for case in fixture["standby"]["cases"])
    assert any(case["record"].get("primary_port") == "5432" for case in fixture["standby"]["cases"])

    record = (ROOT / "tasks/validate/validate_replication_record.yml").read_text()
    inventory = (ROOT / "tasks/validate/validate_replication.yml").read_text()
    for text in (record, inventory):
        assert "is not none" in text
        assert "| string | trim | length > 0" in text
    assert record.index("pg_replication.replication_user is defined") < record.index(
        'name: "Checking SQL replication identifiers"'
    )
    assert record.index("pg_replication.primary_host is defined") < record.index(
        'name: "Checking standby replication configuration"'
    )
    assert inventory.index('name: "Checking standby replication prerequisites"') < inventory.index(
        'name: "Checking standby replication configuration"'
    )
    assert inventory.index('name: "Checking standby replication prerequisites"') < inventory.index(
        'name: "Checking allow_broad_hba type"'
    )
    assert inventory.index('name: "Checking primary replication prerequisites"') < inventory.index(
        'name: "Checking allow_broad_hba type"'
    )
    assert record.index('name: "Checking standby replication prerequisites"') < record.index(
        'name: "Checking allow_broad_hba type"'
    )
    for text in (record, inventory):
        assert "^(0|[1-9][0-9]*)$" in text
        assert "Normalizing standby replication primary port" in text
    for message in (fixture["primary"]["message"], fixture["standby"]["message"]):
        normalized_message = " ".join(message.split())
        assert normalized_message in " ".join(record.split())
        assert normalized_message in " ".join(inventory.split())
    print("replication prerequisite precedence guard: PASS")


if __name__ == "__main__":
    main()
