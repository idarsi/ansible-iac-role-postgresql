# Testing

This role uses Molecule with the Podman driver for automated integration
testing. The test matrix below describes the environments currently covered by
the repository. It is not a complete list of operating systems that the role
may work on.

## Automated test matrix

Platform/image                  | PostgreSQL versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 8 UBI               | 17, 18              | `rocky8-baseline`             | PGDG repository and multi-version baseline installation
Red Hat Enterprise Linux 8 UBI | 17, 18              | `rhel8-baseline`              | PGDG repository and multi-version baseline installation
Rocky Linux 9 UBI               | 16, 17, 18          | `rocky9-full`, `all_absent`, `bind_guardrails`, `hba_guardrails`, `replication`, `timescaledb`, `validation`, `patroni_config`, `patroni_failover`, `patroni_membership`, `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Full baseline, cleanup, guardrails, physical replication, inventory validation, TimescaleDB sources, Patroni membership, failover, and managed etcd
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9-full`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10-baseline`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10-baseline`            | Baseline installation and multi-version coverage
Fedora 43                       | 17, 18               | `fedora43-baseline`          | PGDG repository and baseline installation
Fedora 44                       | 17, 18               | `fedora44-baseline`          | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 17, 18               | `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Managed three-member etcd, quorum recovery, Patroni failover, TLS etcd, and PostgreSQL 18 smoke coverage
Rocky Linux 8/10 UBI            | 17, 18               | `el8-el10-etcd-matrix`    | Managed etcd package and service coverage across EL8 and EL10 with PostgreSQL 18 smoke coverage

The coverage target is PostgreSQL 17 and 18 on Fedora, and PostgreSQL 16, 17,
and 18 on the longer-lived Rocky Linux and RHEL platforms. The Rocky Linux 8
and RHEL 8 baseline scenarios currently cover PostgreSQL 17 and 18, while the
Rocky Linux 9 and 10 and RHEL 9 and 10 scenarios cover PostgreSQL 16, 17, and
18.

## Scenario coverage

- `molecule/rocky9-full` validates package installation, multi-instance startup,
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
- `molecule/rocky8-baseline` validates PostgreSQL 17 and 18 with the baseline repository
  workflow on Rocky Linux 8, including PGDG enablement, `powertools`, and
  PostgreSQL module disablement.
- `molecule/rhel8-baseline` validates the same baseline repository workflow on Red Hat
  Enterprise Linux 8 UBI for PostgreSQL 17 and 18, including PGDG enablement
  and PostgreSQL module disablement. The role does not configure Red Hat
  subscription repositories.
- `molecule/rhel9-full` validates the default multi-instance, bind, git, and
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
- `molecule/rocky9-etcd-cluster` validates a role-managed three-member PGDG etcd
  cluster, etcd key persistence across a member outage, and Patroni failover
  and recovery on the managed DCS.
- `molecule/rocky9-etcd-tls-member` validates a TLS-enabled managed etcd member.
- `molecule/rocky9-etcd-tls-cluster` validates a three-member TLS etcd cluster,
  client and peer certificate configuration, and TLS quorum recovery.
- `molecule/el8-el10-etcd-matrix` validates managed PGDG etcd installation and the
  local etcd and Patroni endpoints on EL8 and EL10.
- `molecule/rocky10-baseline` validates the same baseline behavior on Rocky Linux 10.
- `molecule/rhel10-baseline` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI.
- `molecule/fedora43-baseline` and `molecule/fedora44-baseline` validate PostgreSQL 17 and 18
  installations from the Fedora-specific PGDG repository workflow.

The GitHub Actions workflow runs the production-profile lint check and the
Molecule scenarios as separate jobs. Molecule scenarios run in parallel by
scenario. Pull requests and pushes to `main` run a fast representative matrix;
the complete scenario matrix runs once per day and can also be started with
`workflow_dispatch`.

The fast matrix contains `validation`, `rocky9-full`, `all_absent`,
`patroni_config`, `rocky10-baseline`, `rhel10-baseline`, and
`fedora44-baseline`. The daily matrix runs
all scenarios listed in this document, including the older EL and Fedora
baseline images, replication and guardrail scenarios, both TimescaleDB
repository variants, and the multi-member Patroni and etcd scenarios.

The workflow cancels an older in-progress run for the same branch or scheduled
workflow when a newer run starts.

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
for scenario in molecule/*; do
    molecule test -s "${scenario##*/}" || exit 1
done
```

Run an individual scenario:

```bash
molecule test -s <scenario>
```

Useful scenarios include:

```bash
molecule test -s rocky9-full
molecule test -s validation
molecule test -s timescaledb
molecule test -s replication
molecule test -s patroni_config
molecule test -s patroni_membership
molecule test -s patroni_failover
molecule test -s rocky9-etcd-cluster
molecule test -s rocky9-etcd-tls-member
molecule test -s rocky9-etcd-tls-cluster
molecule test -s el8-el10-etcd-matrix
molecule test -s rocky8-baseline
molecule test -s rhel8-baseline
molecule test -s rhel9-full
molecule test -s rocky10-baseline
molecule test -s rhel10-baseline
molecule test -s fedora43-baseline
molecule test -s fedora44-baseline
```

Run only syntax checks when working on task or scenario structure:

```bash
molecule syntax -s <scenario>
```

The scenarios use Ansible Galaxy collections for their test infrastructure.
The role itself uses only `ansible.builtin.*` modules and does not require
those test-driver collections at runtime.
