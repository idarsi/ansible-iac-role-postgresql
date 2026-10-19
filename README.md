> **Maturity State: Beta**<br>
> **RC Readiness: 85%** ([assessment](docs/maturity-assessment.md))

ANSIBLE-IAC-ROLE-POSTGRESQL
===============================
**COPYRIGHT** 2026 ^(ida|arsi)$ collective
**LICENSE** MIT Licence [LICENSE](LICENSE)
**AUTHORS**
- Arsi Atomi <arsi@atomi.sh>
- Arsi Atomi <arsi.atomi@valtori.fi>

Overview
--------

This Ansible role provides a declarative way to install PostgreSQL and converge
configured instances and database resources.

This role uses the `iac_blueprint` model to define the desired state, while
Ansible handles the host-specific implementation. See [Idarsi](https://github.com/idarsi)
for further information.

The role manages:

- PostgreSQL packages, repositories, instances, and services.
- Databases, roles, extensions, configuration, and physical replication.
- Optional Patroni clusters and explicitly enabled role-managed etcd.

The role does not manage:

- External PKI, firewall policy, or external DCS provisioning.
- Operational etcd membership changes or general host-wide system administration.

Supported platforms
-------------------

| Operating system                  | Supported versions                | Automated test coverage                   |
|-----------------------------------|-----------------------------------|-------------------------------------------|
| Rocky Linux                       | 8, 9, 10                          | 9, 10 (Molecule; see [TESTING.md](TESTING.md)) |
| Red Hat Enterprise Linux (UBI)    | 8, 9, 10                          | 9, 10 (Molecule; see [TESTING.md](TESTING.md)) |
| Fedora                            | 43, 44                            | 43, 44 (Molecule; see [TESTING.md](TESTING.md)) |

Rocky 8 and Red Hat/UBI 8 are allowed by `defaults/main.yml` and the role's
platform preflight; EL8 repository handling is implemented in
`tasks/repo_present_el8.yml`. They are support claims derived from implementation,
not from automated coverage. See [TESTING.md](TESTING.md) for the tested matrix.

Supported states
----------------

| State                  | Behaviour |
|------------------------|-----------|
| `install`              | Installs and configures declared PostgreSQL resources and applicable clusters. |
| `update`               | Updates installed packages recorded as managed by this role. |
| `uninstall`            | Stops and removes declared instances and the PostgreSQL installation. |
| `all_absent`           | Destructively removes PostgreSQL and role-managed remnants, including data and the PostgreSQL OS user; cleanup guards apply. |
| `validate`             | Validates the blueprint without applying PostgreSQL state. |
| `present`              | Ensures PostgreSQL packages and repositories are present. |
| `absent`               | Removes PostgreSQL installation in the declared scope subject to safeguards. |
| `instances_present`    | Ensures declared instances and configuration are present. |
| `instances_absent`     | Stops and removes declared instances subject to ownership safeguards. |
| `instances_started`    | Starts declared instances and required extension packages. |
| `instances_stopped`    | Stops declared instances without removing them. |
| `instances_restarted`  | Restarts declared instances. |
| `replication_present`  | Configures physical replication; standby bootstrap may initialize its data directory. |
| `clusters_present`     | Renders declared Patroni/cluster configuration without converging databases or roles. |
| `databases_present`    | Ensures declared databases and extensions are present. |
| `databases_absent`     | Removes declared databases. |
| `roles_present`        | Ensures declared database roles are present. |
| `roles_absent`         | Removes declared database roles. |
| `post_installs_present`| Runs declared post-install SQL jobs. |

Quick start
-----------

See the [inventory examples](docs/inventory/), including standalone,
streaming replication, and Patroni with managed TLS etcd.

Requirements
------------

### Source checkout

`tasks/shared` is a Git submodule that provides `log_write.yml`. Initialize it
before running Ansible or Molecule. For a new clone, use:

```sh
git clone --recurse-submodules https://github.com/idarsi/ansible-iac-role-postgresql.git
```

Or initialize it in an existing checkout:

```sh
git submodule update --init --recursive
```

An error such as `Could not find ... shared/log_write.yml` means the shared-task
submodule is missing or uninitialized; it does not indicate a missing Molecule
scenario file.

Control node

- Ansible Core 2.19.12 or newer
- `ansible.posix` (>=1.3.0) and `containers.podman` (>=1.7.0); see [collections.yml](collections.yml)

Target host

- Supported operating system and version listed above; package repositories and network access to fetch selected software must be available.

Blueprint structure
-------------------

Configuration is read from:

`iac_blueprint.postgresql`

Minimal structure:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
```

Top-level blueprint variables
-----------------------------

| Variable          | Required (yes/no) | Default       | Short description |
|-------------------|-------------------|---------------|-------------------|
| `iac_blueprint`   | yes               | None          | Mapping containing the required `postgresql` list of version-level PostgreSQL declarations. |

Configuration examples
----------------------

Minimal deployment with a database and role:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          roles:
            - name: app
              password: "{{ vault_postgresql_app_password }}"
          databases:
            - name: appdb
              owner: app
              access:
                - name: app
                  address: 192.168.1.0/24
```

See [docs/inventory/](docs/inventory/) for practical deployment examples.
Managed etcd requires TLS and per-host `pg_etcd_bind_address`. The `all_absent`
and `pg_patroni_reinitialize` operations are destructive and should only be
used with deliberate intent.

For exact state behavior and test coverage, see [TESTING.md](TESTING.md).
