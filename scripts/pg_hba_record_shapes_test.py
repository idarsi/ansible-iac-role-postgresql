#!/usr/bin/env python3
"""Render both supported pg_hba record shapes through the real template."""

from pathlib import Path
import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).parents[1]
fixture = yaml.safe_load((ROOT / "scripts/fixtures/pg_hba_record_shapes.yml").read_text())
environment = Environment(
    loader=FileSystemLoader(ROOT / "templates"),
    undefined=StrictUndefined,
    keep_trailing_newline=True,
)
template = environment.get_template("pg_hba.conf.j2")

raw_output = template.render(
    pg_global_access=[],
    pg_cluster_provider="patroni",
    pg_cluster={"patroni": {"pg_hba": fixture["raw_patroni"]}},
    pg_replication_enabled=False,
    pg_databases=[],
)
structured_output = template.render(
    pg_global_access=[],
    pg_cluster_provider="standalone",
    pg_cluster={},
    pg_replication_enabled=False,
    pg_databases=[{"name": "reporting", "access": fixture["structured_instance"]}],
)

assert "host all reporting 10.0.0.0/24 scram-sha-256" in raw_output
assert "host reporting reporting 10.0.0.0/24 scram-sha-256" in structured_output
assert "{'name':" not in raw_output + structured_output
print("pg_hba record-shape rendering regression passed")
