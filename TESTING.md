# Testing

This role uses Molecule with the Podman driver for automated integration
testing. The test matrix below describes the environments currently covered by
the repository. It is not a complete list of operating systems that the role
may work on.

## Automated test matrix

Platform/image                  | PostgreSQL versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 8 UBI               | 17                  | `rocky8`            | PGDG repository and baseline installation
Red Hat Enterprise Linux 8 UBI | 17                  | `rhel8`             | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 16, 17, 18          | `default`, `all_absent`, `bind_guardrails`, `hba_guardrails`, `replication`, `timescaledb`, `validation` | Full baseline, cleanup, guardrails, physical replication, inventory validation, and TimescaleDB sources
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10`            | Baseline installation and multi-version coverage

Fedora is not included in the current automated test matrix.

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
  without installing PostgreSQL packages.
- `molecule/timescaledb` validates TimescaleDB installation from both PGDG and
  the Timescale Community repository on Rocky Linux 9.
- `molecule/rocky8` validates the baseline repository workflow on Rocky Linux
  8, including PGDG enablement, `powertools`, and PostgreSQL module
  disablement.
- `molecule/rhel8` validates the same baseline repository workflow on Red Hat
  Enterprise Linux 8 UBI, including PGDG enablement and PostgreSQL module
  disablement. The role does not configure Red Hat subscription repositories.
- `molecule/rhel9` validates the default multi-instance, bind, git, and
  repository workflow on Red Hat Enterprise Linux 9 UBI.
- `molecule/replication` validates optional physical primary/standby
  replication between two Rocky Linux 9 containers, including standby
  bootstrap with `pg_basebackup` and replicated test data visibility.
- `molecule/rocky10` validates the same baseline behavior on Rocky Linux 10.
- `molecule/rhel10` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI.

## Running tests

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
molecule test -s rocky8
molecule test -s rhel8
molecule test -s rhel9
molecule test -s rocky10
molecule test -s rhel10
```

Run only syntax checks when working on task or scenario structure:

```bash
molecule syntax -s <scenario>
```

The scenarios use Ansible Galaxy collections for their test infrastructure.
The role itself uses only `ansible.builtin.*` modules and does not require
those test-driver collections at runtime.
