#!/usr/bin/env python3
"""Regression guard for invalid replication address normalization."""

from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def main():
    fixture = yaml.safe_load(
        (ROOT / "scripts/fixtures/replication_invalid_non_unicast_ipv4.yml").read_text()
    )
    assert fixture["allowed_standby_addresses"] == ["224.0.0.1"]
    for path in (
        ROOT / "tasks/validate/validate_replication.yml",
        ROOT / "tasks/validate/validate_replication_record.yml",
    ):
        text = path.read_text()
        assert "| ansible.utils.ipaddr('unicast')" in text
        parse = text.index("Parsing validated" if "validate_replication_record" in str(path) else "Parsing validated")
        guard = text.index("is parseable")
        assert guard < parse, f"{path} parses before the invalid-address guard"
        non_empty = text.index('name: "Checking each primary replication standby address"')
        assert non_empty < guard, f"{path} reaches ipaddr before the non-empty-string guard"
        guard_text = text[non_empty:guard]
        assert "is not none" in guard_text and "is string" in guard_text
        parsing = text[parse:]
        assert "pg_replication_allowed_standby_addresses_parsed +" in parsing or "pg_validation_replication_parsed_addresses +" in parsing
        assert "| ansible.utils.ipaddr('network/prefix')" in parsing

    validation = (ROOT / "tasks/validate/validate_replication.yml").read_text()
    record = (ROOT / "tasks/validate/validate_replication_record.yml").read_text()
    assert "Primary replication requires replication_user, replication_password, and allowed_standby_addresses" in validation
    assert "Standby replication requires primary_host, primary_port, replication_user, and replication_password" in validation
    assert "PostgreSQL primary replication configuration requires replication_user," in record
    assert "PostgreSQL standby replication configuration requires primary_host, primary_port, replication_user, and replication_password" in record
    print("replication invalid non-unicast normalization guard: PASS")


if __name__ == "__main__":
    main()
