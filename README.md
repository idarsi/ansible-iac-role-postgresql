ANSIBLE-IAC-ROLE-POSTGRESQL
===========================
**COPYRIGHT** 2026 ^(ida|arsi)$ collective  
**LICENSE** MIT License [LICENSE](LICENSE)  
**AUTHORS**
- Arsi Atomi <arsi@atomi.sh>  
- Arsi Atomi <arsi.atomi@valtori.fi>  

Overview
========

This Ansible role provides a declarative way to deploy and manage PostgreSQL
environments with multiple major versions, instances, databases, roles,
extensions, and supporting infrastructure.

Its development goal is to make complex PostgreSQL installations possible to
roll out and maintain across large environments with as little manual work as
possible. The role is also intended to evolve toward continuously verifying
that the deployed PostgreSQL configuration remains aligned with the desired
blueprint and organizational compliance requirements.

The role uses the `iac_blueprint` model to keep the desired state in one
structured inventory while Ansible handles the host-specific implementation.

> **Maturity Level: Beta**<br>
> The role's main functionality is complete and covered by extensive Molecule
> scenarios across supported Enterprise Linux versions. It supports
> multi-version and multi-instance PostgreSQL deployments, database and role
> management, extensions, replication, inventory validation, repository
> workflows, filesystem handling, and destructive cleanup. The role remains at
> Beta because its interfaces and behavior may still change, Fedora is not part
> of the automated test matrix, and broader long-term production evidence and
> backward-compatibility guarantees have not yet been established.

Supported PostgreSQL major versions:
- PostgreSQL 18 — supported until 14 November 2030
- PostgreSQL 17 — supported until 8 November 2029
- PostgreSQL 16 — supported until 9 November 2028

These versions are installed from the PostgreSQL Global Development Group
(PGDG) repositories. PGDG follows the PostgreSQL project's policy of
supporting each major version for five years after its initial release. The
PGDG repository provides packages and updates for supported PostgreSQL
versions throughout their support lifetime.

On Red Hat Enterprise Linux (including UBI) and Rocky Linux, the role uses the
PGDG repository for PostgreSQL packages. It does not install PostgreSQL from
Red Hat's distribution PostgreSQL packages. The host's Red Hat or Rocky Linux
base repositories remain platform prerequisites; the role only manages the
additional Rocky Linux repositories needed by its package workflow.

See the [PostgreSQL versioning policy](https://www.postgresql.org/support/versioning/)
and the [PGDG Red Hat family platform documentation](https://www.postgresql.org/download/linux/redhat/)
for the current lifecycle and repository support information.

These operations are supported:

Operation                       | State               |
--------------------------------|---------------------|
Installing and configuring all  | install             |
Uninstalling all                | uninstall           |
Removing PostgreSQL completely  | all_absent          |
Validating inventory            | validate             |
Installing PostgreSQL           | present             |
Uninstalling PostgreSQL         | absent              |
Create PostgreSQL instances     | instances_present   |
Remove PostgreSQL instances     | instances_absent    |
Start PostgreSQL instances      | instances_started   |
Stop PostgreSQL instances       | instances_stopped   |
Restart PostgreSQL instances    | instances_restarted |
Ensure replication is present   | replication_present |
Ensure cluster configuration is present | clusters_present |
Create databases                | databases_present   |
Remove databases                | databases_absent    |
Create database users           | roles_present       |
Remove database users           | roles_absent        |

Quick start
-----------

Install PostgreSQL 17 with one instance:

```yaml
---
- hosts: postgres
  become: true
  roles:
    - role: ansible-iac-role-postgresql
      state: install
  vars:
    iac_blueprint:
      postgresql:
        - version: 17
          instances:
            - name: main
```

The role validates the complete inventory before applying the selected state.
Run only the validation when checking a blueprint without changing the host:

```yaml
- hosts: postgres
  become: true
  roles:
    - role: ansible-iac-role-postgresql
      state: validate
```

The `all_absent` state is intentionally destructive: it removes PostgreSQL
packages, repository configuration, service files, data, logs, and the
PostgreSQL operating system user. Use it only when the host should be reset to
a clean pre-PostgreSQL baseline.

Requirements
------------

- Operating systems covered by the automated Molecule test matrix are listed
  in [TESTING.md](TESTING.md). Fedora is not included in the current automated
  test coverage.

- Other components
  - Ansible 2.15 or higher

The versions used by the automated CI test environment are documented in
[TESTING.md](TESTING.md). The CI currently pins Ansible Core 2.16,
ansible-lint 25.x, Molecule 6.x, and molecule-plugins 23.x–24.x for
repeatable test runs.

Usage
=====

How to run playbook with inventory
----------------------------------

Use playbook and inventory examples to create your own playbook and run command below.

```bash
ansible-playbook -i <inventory_file> <playbook_file> -kK
```

Playbook example
----------------

```yaml
---
- hosts: postgres
  become: true

  roles:
  - role: ansible-iac-role-postgresql
    state: install
```

The above example is equivalent to the example below in practical use.

```yaml
---
- hosts: postgres
  become: true

  roles:
  - role: ansible-iac-role-postgresql
    state: present

  - role: ansible-iac-role-postgresql
    state: instances_present

  - role: ansible-iac-role-postgresql
    state: instances_started

  - role: ansible-iac-role-postgresql
    state: roles_present

  - role: ansible-iac-role-postgresql
    state: databases_present

  - role: ansible-iac-role-postgresql
    state: replication_present
```

To validate the complete PostgreSQL inventory without applying a PostgreSQL
state, run the role with the `validate` state:

```yaml
---
- hosts: postgres
  become: true

  roles:
  - role: ansible-iac-role-postgresql
    state: validate
```

PostgreSQL clustering
---------------------

Clustering is modeled separately from a PostgreSQL instance. A version-level
`clusters` record is shared with every member host, while each instance points
to its cluster by name. The role selects the local member by matching
`inventory_hostname` and the instance name. The supported providers are
`standalone`, `streaming_replication`, and `patroni`.

For Patroni, the DCS is an external dependency. This role installs and
configures the Patroni agent and its systemd unit, but it does not provision
etcd, Consul, or Kubernetes. Patroni instances are started through Patroni,
not through the PostgreSQL systemd unit directly.

For an `etcd3` DCS, the role automatically installs the PGDG
`patroni-etcd` package together with Patroni. This follows the PGDG Patroni
packaging guidance and keeps the Patroni package and its etcd client support
from the same repository family:

```yaml
pg_patroni_etcd_package: patroni-etcd
```

The package is selected only when the cluster DCS provider is `etcd3`. The
When managed etcd is not enabled, external etcd remains the responsibility of
the surrounding role or infrastructure layer. The default package name can be
overridden with `pg_patroni_etcd_package`, while additional Patroni packages
can be supplied through `pg_patroni_additional_packages`.

For hosts listed in `dcs.etcd.members`, define the local etcd bind address
explicitly, for example in host variables:

```yaml
pg_etcd_bind_address: 10.0.0.11
```

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      clusters:
        - name: core-db
          provider: patroni
          dcs:
            provider: etcd3
            endpoints:
              - https://etcd01.example.org:2379
              - https://etcd02.example.org:2379
              - https://etcd03.example.org:2379
                etcd:
                  enabled: true
                  # Required on every host managed as an etcd member.
                  # Define pg_etcd_bind_address in host_vars/group_vars.
                  initial_cluster_token: core-dcs
              members:
                - name: etcd01
                  host: etcd01.example.org
                  peer_url: https://etcd01.example.org:2380
                  client_url: https://etcd01.example.org:2379
                - name: etcd02
                  host: etcd02.example.org
                  peer_url: https://etcd02.example.org:2380
                  client_url: https://etcd02.example.org:2379
                - name: etcd03
                  host: etcd03.example.org
                  peer_url: https://etcd03.example.org:2380
                  client_url: https://etcd03.example.org:2379
              tls:
                enabled: true
                client:
                  ca_file: /etc/etcd/pki/ca.crt
                  cert_file: /etc/etcd/pki/etcd-client.crt
                  key_file: /etc/etcd/pki/etcd-client.key
                peer:
                  ca_file: /etc/etcd/pki/ca.crt
                  cert_file: /etc/etcd/pki/etcd-peer.crt
                  key_file: /etc/etcd/pki/etcd-peer.key
          patroni:
            ttl: 30
            loop_wait: 10
            retry_timeout: 10
            synchronous_mode: false
            restapi:
              authentication:
                username: patroni
                password: "{{ vault_patroni_restapi_password }}"
              allowlist:
                - db01.example.org
                - db02.example.org
          members:
            - host: db01.example.org
              instance: main
              name: core-db01
            - host: db02.example.org
              instance: main
              name: core-db02
      instances:
        - name: main
          cluster: core-db
          configuration:
            port: 5432
```

When `dcs.etcd.enabled` is `true`, the role installs the PGDG `etcd` package
on hosts listed in `dcs.etcd.members`, renders the local member configuration,
and enables the `etcd` systemd service. Managed etcd requires TLS/mTLS and an
explicit host-level `pg_etcd_bind_address`; wildcard bind addresses and plain
HTTP endpoints are rejected. Certificate files must be provisioned by the
surrounding certificate workflow before enabling the cluster. The current
implementation supports static cluster bootstrap. Add/remove member operations
and snapshot/restore remain separate operational procedures.

Use `state: clusters_present` to render Patroni configuration and its service
unit without changing PostgreSQL databases or roles. `state: install` also
handles the cluster configuration as part of the normal installation flow.

All other role states run the same inventory validation automatically before
performing their state-specific work.

When an instance uses TimescaleDB, `instances_started` ensures the selected
TimescaleDB package and repository are present before starting the PostgreSQL
service. This prevents PostgreSQL from starting before its configured preload
library has been installed.

To aggressively remove PostgreSQL from a host, including repository
configuration, the operating system user, and PostgreSQL-owned data
directories, run:

```yaml
---
- hosts: postgres
  become: true

  roles:
  - role: ansible-iac-role-postgresql
    state: all_absent
```

`all_absent` is intentionally destructive. It stops PostgreSQL systemd units,
removes PostgreSQL packages and repository configuration, deletes PostgreSQL
service files, removes PostgreSQL data and log directories, and deletes the
PostgreSQL operating system user together with its home directory. It also
removes version-scoped managed Git working trees before the final directory
cleanup. Use it when a host or test environment must be reset back to a clean
pre-PostgreSQL baseline instead of preserving any existing PostgreSQL data.

Inventory example
-----------------

```yaml
---
postgres:
  hosts:
    example.org:
  vars:
    iac_blueprint:
      postgresql:
        - version: 17
          instances:
            - name: main
```

Shared filesystem helpers
-------------------------

Version-scoped `directories:`, `files:`, `binds:`, and `git:` entries are
implemented through the shared task library under `tasks/shared`.

For the exact `binds:` record structure and examples, see:

- `tasks/shared/README.md`

The PostgreSQL role also supports moving the whole PostgreSQL home/data tree to
another filesystem location with a bind mount while keeping the legacy path in
place:

```yaml
pg_real_dir: /srv/data/pgsql
pg_bind_dir: /var/lib/pgsql
```

This creates `/srv/data/pgsql` when needed, moves existing data from
`/var/lib/pgsql` to the new location when the migration preconditions are met,
and then bind-mounts `/srv/data/pgsql` back to `/var/lib/pgsql`.

iac_blueprint inventory structure
---------------------------------

This role uses iac_blueprint.postgresql as the top-level inventory key. Each entry under it represents 
a specific PostgreSQL major version and includes one or more instances configured independently on the 
same or different hosts.

Top-level structure:

```yaml
iac_blueprint:
  postgresql:
    - version: <major version number>          # e.g. 17
      directories:                             # optional filesystem directories
        - path: <path>
          owner: <owner>
          group: <group>
          mode: <mode>
      files:                                   # optional files with inline content
        - path: <path>
          content: <content>
          owner: <owner>
          group: <group>
          mode: <mode>
      git:                                     # optional git working trees
        - repo: <repository url or path>
          dest: <destination path>
          version: <branch, tag, or commit>    # optional
          update: true|false                   # optional
          force: true|false                    # optional
          recursive: true|false                # optional
      cron:                                    # optional cronjobs
        - name: <name>
          job: <command>
          user: <user>
          minute: <minute>
          hour: <hour>
          weekday: <weekday>
          cron_file: <cron_file>
      post_install:                             # optional SQL jobs
        jobs:
          - database: <database>                # optional, defaults to postgres
            sql: <SQL statement(s)>              # executed as the postgres OS user
      instances:
        - name: <instance name>                # must be unique on host
          port: <custom port>                  # default: version-specific PostgreSQL default
          configuration_profile: <name>        # e.g. "balanced"
          autotuning_profile: <name>           # e.g. "balanced"
          security_profile: <name>             # e.g. "safe"
          client_certificate_authority_content: |  # optional trusted CA PEM for client certificate auth
            -----BEGIN CERTIFICATE-----
            ...
            -----END CERTIFICATE-----
          client_certificate_authority_src: <path> # optional controller-side CA PEM path for client certificate auth
          replication:                        # optional physical primary/standby replication settings
            role: <primary|standby>
            replication_user: <username>
            replication_password: <cleartext password>
            allowed_standby_addresses:        # primary only
              - <CIDR>
            primary_host: <hostname or IP>    # standby only
            primary_port: <port>              # standby only, default 5432
            slot_name: <slot name>            # optional
            application_name: <name>          # optional, standby only
            reinitialize: true|false          # optional, standby only
          maprole:                            # optional pg_ident.conf mappings, also used by certificate auth
            - mapname: <map name>
              system_username: <system user or certificate CN/DN>
              pg_username: <database role>
          configuration:                       # optional, direct postgresql.conf overrides
            key: value
          databases:
            - name: <dbname>
              owner: <username>
              extensions:                      # Installs required OS package and runs CREATE EXTENSION in the database
                - name: <extension>
                  source: <pgdg|community>     # timescaledb only; defaults to pgdg
              access:                          # optional pg_hba.conf entries for this database
                - name: <username>
                  address: <CIDR>
                  type: <host|hostssl|local>   # optional, default: host
                  method: <auth_method>        # optional, default: scram-sha-256
                  clientcert: <verify-ca|verify-full> # optional, hostssl only
                  clientname: <CN|DN>          # optional, hostssl only
                  map: <map name>              # optional, hostssl certificate auth only
          roles:                               # roles that exist in this instance
            - name: <username>
              password: <cleartext password>   # optional
              encrypted_password: <SCRAM hash> # optional
              createdb: true|false             # optional
              createuser: true|false           # optional
              superuser: true|false            # optional
              login: true|false                # optional
              description: <role comment>      # optional
```

For TimescaleDB, omitting `source` installs the Apache-licensed package from
the PostgreSQL PGDG repository. Set `source: community` to use the Timescale
Community repository and package:

```yaml
extensions:
  - name: timescaledb
    source: community
```

The TimescaleDB Community repository is managed directly by the role with a
repository file and its GPG key. Repository metadata signatures are verified
with `repo_gpgcheck`; the repository currently does not provide RPM package
signing keys, so package-level `gpgcheck` remains disabled. The vendor
installation script is not used.
TimescaleDB is added automatically to `shared_preload_libraries` while
preserving other configured preload libraries.

For physical primary/standby replication, declare the same TimescaleDB
extension and `source` on both hosts. The package must be installed locally on
the standby even though `CREATE EXTENSION` and other database writes are run
only on the primary. A standby configuration that explicitly preloads
TimescaleDB without declaring the extension metadata fails inventory
validation.

A minimal working iac_blueprint that installs PostgreSQL 17 with one instance and allows user app to 
connect to database appdb from a specific network:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          roles:
            - name: app
              password: changeme
          databases:
            - name: appdb
              owner: app
              access:
                - name: app
                  address: 192.168.1.0/24
```

Certificate authentication example with explicit certificate-aware pg_hba fields:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          security_profile: safe
          client_certificate_authority_src: /srv/pki/postgresql/client-root-ca.crt
          maprole:
            - mapname: app_cert_map
              system_username: app-client
              pg_username: app_user
          roles:
            - name: app_user
              login: true
          databases:
            - name: appdb
              owner: app_user
              access:
                - name: app_user
                  address: 192.168.1.0/24
                  type: hostssl
                  method: cert
                  clientname: CN
                  map: app_cert_map
```

Primary/standby physical replication example
--------------------------------------------

Primary host inventory:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          security_profile: safe
          replication:
            role: primary
            replication_user: replicator
            replication_password: changeme
            allowed_standby_addresses:
              - 192.168.1.11/32
            slot_name: standby1
          roles:
            - name: app_user
              password: changeme
          databases:
            - name: appdb
              owner: app_user
```

Standby host inventory:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          security_profile: safe
          replication:
            role: standby
            primary_host: 192.168.1.10
            primary_port: 5432
            replication_user: replicator
            replication_password: changeme
            slot_name: standby1
            application_name: pg-standby-1
          databases:
            - name: appdb
              extensions:
                - name: plpython3u
```

If the primary database uses extensions that require operating system packages,
define the same `databases[].extensions` metadata on the standby host as well.
The standby must have the extension packages installed locally even though
`CREATE EXTENSION` runs only on the primary and reaches the standby through
physical replication.

Complete two-host inventory example:

```yaml
postgres_primary:
  hosts:
    pg-primary.example.org:
  vars:
    iac_blueprint:
      postgresql:
        - version: 17
          instances:
            - name: main
              security_profile: safe
              configuration:
                listen_addresses: "*"
                port: 5432
              replication:
                role: primary
                replication_user: replicator
                replication_password: changeme
                allowed_standby_addresses:
                  - 192.168.1.11/32
                slot_name: standby1
              roles:
                - name: app_user
                  password: changeme
                  login: true
              databases:
                - name: appdb
                  extensions:
                    - name: plpython3u
                  owner: app_user
                  access:
                    - name: app_user
                      address: 192.168.1.0/24
                      type: host
                      method: scram-sha-256

postgres_secondary:
  hosts:
    pg-standby.example.org:
  vars:
    iac_blueprint:
      postgresql:
        - version: 17
          instances:
            - name: main
              security_profile: safe
              configuration:
                listen_addresses: "*"
                port: 5432
              replication:
                role: standby
                primary_host: 192.168.1.10
                primary_port: 5432
                replication_user: replicator
                replication_password: changeme
                slot_name: standby1
                application_name: pg-standby-1
              databases:
                - name: appdb
                  extensions:
                    - name: plpython3u
```

Recommended execution order for a basic two-host setup:

1. Run `present`, `instances_present`, `instances_started`, `roles_present`,
   and `databases_present` on the primary host.
2. Run `replication_present` on the primary host so the replication role and
   optional slot exist.
3. Run `present` and `replication_present` on the standby host to bootstrap
   it with `pg_basebackup`.
4. Run `instances_present` and `instances_started` on the standby host to
   render local overrides and start the replicated instance.

The standby host should not be the target for `roles_present` or
`databases_present`; those write operations belong on the primary host.

Blueprint cron jobs must run as `postgres`. Version-scoped filesystem entries
are limited to PostgreSQL auxiliary paths under `/var/lib/pgsql/`,
`/var/log/pgsql/`, `/etc/pgsql/`, or `/tmp/`; PostgreSQL data directories,
Patroni, etcd, and systemd paths cannot be managed through these entries.
Post-install jobs accept SQL through `sql` and are always executed with
`psql` as the PostgreSQL operating-system user. Shell `command` and
`run_as` fields are not supported.

Minimal example: just install PostgreSQL with one instance

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: data
```

Optional filesystem and cron example

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      directories:
        - path: /var/lib/pgsql/backups
          owner: postgres
          group: postgres
          mode: "0750"
          files:
            - path: /etc/pgsql/backup.env
              content: "PGUSER=postgres\n"
              owner: root
              group: root
              mode: "0640"
          git:
            - repo: /srv/git/pg-maintenance
              dest: /var/lib/pgsql/git/pg-maintenance
              version: main
              update: true
          cron:
            - name: pg_backup
              user: postgres
          minute: "0"
          hour: "2"
          job: "/usr/local/bin/pg_backup"
          cron_file: pg_backup
      instances:
        - name: data

Definitions
-----------

In PostgreSQL documentation the term cluster refers to a collection of
databases. Because cluster is also commonly used for a group of servers, this
document uses instance for a PostgreSQL server-local cluster. A single host
may run one or more PostgreSQL instances on different ports.

Architecture
------------

This Ansible role uses the `iac_blueprint` declarative inventory structure. It
defines the desired end state of services — such as service versions,
instances, configuration profiles, and users — in a structured format. The
role interprets this blueprint and applies the necessary changes.

Repository checkout
-------------------

The shared task library is included as a Git submodule under `tasks/shared`.
Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/idarsi/ansible-iac-role-postgresql.git
```

If the repository was already cloned without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

Static analysis and Molecule testing
------------------------------------

The repository runs Ansible Lint with the `production` profile as a separate
static-analysis gate before the Molecule scenarios. See [TESTING.md](TESTING.md)
for the current test matrix, scenario coverage, and test commands.
