# Testing

This role uses Molecule with the Podman driver for automated integration
testing. The test matrix below describes the environments currently covered by
the repository. It is not a complete list of operating systems that the role
may work on.

## Automated test matrix

Platform/image                  | PostgreSQL versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 8 UBI               | 17, 18              | `rocky8`             | PGDG repository and multi-version baseline installation
Red Hat Enterprise Linux 8 UBI | 17, 18              | `rhel8`              | PGDG repository and multi-version baseline installation
Rocky Linux 9 UBI               | 16, 17, 18          | `default`, `all_absent`, `bind_guardrails`, `hba_guardrails`, `replication`, `timescaledb`, `validation`, `patroni_config`, `patroni_failover`, `patroni_membership` | Full baseline, cleanup, guardrails, physical replication, inventory validation, TimescaleDB sources, Patroni membership, and failover
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10`            | Baseline installation and multi-version coverage
Fedora 43                       | 17                   | `fedora43`          | PGDG repository and baseline installation
Fedora 44                       | 17                   | `fedora44`          | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 17                   | `etcd_server`, `etcd_tls_cluster` | Managed three-member etcd, quorum recovery, Patroni failover, and TLS etcd
Rocky Linux 8/10 UBI            | 17                   | `etcd_el_matrix`    | Managed etcd package and service coverage across EL8 and EL10

The 8-series scenarios cover PostgreSQL 17 and 18. The Rocky Linux 9 and 10
and RHEL 9 and 10 scenarios already cover PostgreSQL 16, 17, and 18.

## Scenario coverage

- `molecule/default` validates package installation, multi-instance startup,
  version-scoped managed filesystem resources including `binds:`, cron
  entries, role/database provisioning, extension creation, and generated
  access configuration on Rocky Linux 9.
- `molecule/all_absent` validates destructive cleanup of packages,
  repositories, bind mounts, service files, managed resources, and the
  PostgreSQL operating system user on Rocky Linux 9.
- `molecule/bind_guardrails` validates that bind-mount migration fails safely
  when source and target both contain data or when PostgreSQL services are
  still running against the target directory.
- `molecule/hba_guardrails` validates that pg_hba validation failures report
  specific root causes for invalid address usage, missing client CA
  configuration, and undefined certificate-auth map references.
- `molecule/validation` validates valid and invalid PostgreSQL blueprints
  without installing PostgreSQL packages, including the missing-blueprint
  execution-context guardrail, destructive cleanup path validation, and
  PostgreSQL instance-name validation.
- `molecule/timescaledb` validates TimescaleDB installation from both PGDG and
  the Timescale Community repository on Rocky Linux 9 and 10 and Red Hat
  Enterprise Linux 9 and 10 UBI.
- `molecule/rocky8` validates PostgreSQL 17 and 18 with the baseline repository
  workflow on Rocky Linux 8, including PGDG enablement, `powertools`, and
  PostgreSQL module disablement.
- `molecule/rhel8` validates the same baseline repository workflow on Red Hat
  Enterprise Linux 8 UBI for PostgreSQL 17 and 18, including PGDG enablement
  and PostgreSQL module disablement. The role does not configure Red Hat
  subscription repositories.
- `molecule/rhel9` validates the default multi-instance, bind, git, and
  repository workflow on Red Hat Enterprise Linux 9 UBI.
- `molecule/replication` validates optional physical primary/standby
  replication between two Rocky Linux 9 containers, including standby
  bootstrap with `pg_basebackup` and replicated test data visibility.
- `molecule/patroni_config` validates Patroni configuration rendering from a
  shared cluster blueprint, including host-local member selection.
- `molecule/patroni_membership` validates a three-member Patroni cluster,
  removal of one member from the etcd DCS, and rejoining that member as a
  replica.
- `molecule/patroni_failover` validates a three-member Patroni cluster with a
  real three-member etcd DCS. It covers idempotent role execution, one etcd
  member outage and quorum continuity, Patroni member removal and rejoin,
  primary failover, data survival, writes while a replica is offline, and
  rejoining both the offline replica and the failed primary.
- `molecule/etcd_server` validates a role-managed three-member PGDG etcd
  cluster, etcd key persistence across a member outage, and Patroni failover
  and recovery on the managed DCS.
- `molecule/etcd_tls_cluster` validates a three-member TLS etcd cluster,
  client and peer certificate configuration, and TLS quorum recovery.
- `molecule/etcd_el_matrix` validates managed PGDG etcd installation and the
  local etcd and Patroni endpoints on EL8 and EL10.
- `molecule/rocky10` validates the same baseline behavior on Rocky Linux 10.
- `molecule/rhel10` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI.
- `molecule/fedora43` and `molecule/fedora44` validate PostgreSQL 17
  installation from the Fedora-specific PGDG repository workflow.

The GitHub Actions workflow runs the production-profile lint check and the
Molecule scenarios as separate jobs. Molecule scenarios run in parallel by
scenario, while the lint job is shared by all pull requests.

The workflow uses the exact Ansible Core, ansible-lint, Molecule, and
molecule-plugins versions defined in `requirements-ci.txt`. Install that file
locally before running Molecule to reproduce the CI test environment.

## Running tests

Run the production-profile Ansible Lint check before the Molecule scenarios:

```bash
python -m pip install -r requirements-ci.txt
ANSIBLE_ROLES_PATH=.. ansible-lint --profile production
```

Molecule's current releases do not provide Ansible Lint as a built-in
scenario phase, so this is a separate static-analysis gate in the same test
workflow. The repository's `.ansible-lint` file keeps the profile and shared
exclusions in version control.

Run all scenarios from the role directory:

```bash
molecule test
```

Run an individual scenario:

```bash
molecule test -s <scenario>
```

Useful scenarios include:

```bash
molecule test -s default
molecule test -s validation
molecule test -s timescaledb
molecule test -s replication
molecule test -s patroni_config
molecule test -s patroni_membership
molecule test -s patroni_failover
molecule test -s etcd_server
molecule test -s etcd_tls_cluster
molecule test -s etcd_el_matrix
molecule test -s rocky8
molecule test -s rhel8
molecule test -s rhel9
molecule test -s rocky10
molecule test -s rhel10
molecule test -s fedora43
molecule test -s fedora44
```

Run only syntax checks when working on task or scenario structure:

```bash
molecule syntax -s <scenario>
```

The scenarios use Ansible Galaxy collections for their test infrastructure.
The role itself uses only `ansible.builtin.*` modules and does not require
those test-driver collections at runtime.
