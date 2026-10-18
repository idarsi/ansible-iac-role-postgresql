# PostgreSQL inventory examples

These examples demonstrate the public `iac_blueprint.postgresql` inventory
shape. Copy the relevant file into your inventory and replace example hosts,
addresses, and secret references with values for your environment. Keep
credentials in Ansible Vault or another secret manager; never commit secret
values. Apply a suitable firewall policy separately.

| Example | Purpose |
| --- | --- |
| [single-instance.yml](single-instance.yml) | One standalone PostgreSQL instance with an application role and database. |
| [streaming-replication.yml](streaming-replication.yml) | Physical primary/standby replication across two hosts. |
| [patroni-etcd.yml](patroni-etcd.yml) | Three-member Patroni cluster with role-managed TLS etcd. |

Cluster definitions are version-scoped and must be identical on every member
host. The role selects the local member using `inventory_hostname` and the
instance name. For managed etcd, set `pg_etcd_bind_address` per host to a
specific, reachable interface address; do not use a wildcard. Managed etcd
requires TLS and certificate paths under `/etc/etcd/`. This role configures
services and TLS paths but does not issue or distribute production PKI. See
[TESTING.md](../../TESTING.md) for coverage and operational limitations.
