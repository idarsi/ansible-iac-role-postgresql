ANSIBLE-IAC-ROLE-POSTGRESQL
===========================
**COPYRIGHT** 2026 ^(ida|arsi)$ collective  
**LICENSE** MIT License [LICENSE](LICENSE)  
**AUTHORS**
- Arsi Atomi <arsi@atomi.sh>  
- Arsi Atomi <arsi.atomi@valtori.fi>  

Overview
========

This Ansible role is designed to simplify and enhance the flexibility of PostgreSQL management.

This role uses only ansible.builtin.* ansible modules.

Supported PostgreSQL versions (from PostgreSQL repository):
- PostgreSQL 18
- PostgreSQL 17
- PostgreSQL 16

These operations are supported:

Operation                       | State               |
--------------------------------|---------------------|
Installing and configuring all  | install             |
Uninstalling all                | uninstall           |
Removing PostgreSQL completely  | all_absent          |
Validating inventory             | validate             |
Installing PostgreSQL           | present             |
Uninstalling PostgreSQL         | absent              |
Create PostgreSQL instances     | instances_present   |
Remove PostgreSQL instances     | instances_absent    |
Start PostgreSQL instances      | instances_started   |
Stop PostgreSQL instances       | instances_stopped   |
Restart PostgreSQL instances    | instances_restarted |
Ensure replication is present   | replication_present |
Create databases                | databases_present   |
Remove databases                | databases_absent    |
Create database users           | roles_present       |
Remove database users           | roles_absent        |

Requirements
------------

- Operating system (tested on)
  - Red Hat Enterprise Linux 10
  - Fedora Linux 42
  - Fedora Linux 41
  - Red Hat Enterprise Linux 9
  - Red Hat Enterprise Linux 8
  - Rocky Linux 10
  - Rocky Linux 9
  - Rocky Linux 8

- Other components
  - Ansible 2.15 or higher

Repository checkout
-------------------

This role includes the shared task library as a Git submodule under
`tasks/shared`.

Clone the repository with submodules:

```bash
git clone --recurse-submodules https://github.com/idarsi/ansible-iac-role-postgresql.git
```

If you already cloned the repository without submodules, initialize them with:

```bash
git submodule update --init --recursive
```

Code Quality
------------

This project adheres to the [Ansible Lint](https://ansible-lint.readthedocs.io)
**production** profile, ensuring high-quality and production-ready
configuration management.

Role Testing
------------

This role includes baseline Molecule scenarios:

- `molecule/default` validates package installation, multi-instance startup,
  version-scoped managed filesystem resources including `binds:`, cron
  entries, role/database provisioning, extension creation, and generated
  access configuration on Rocky Linux 9
- `molecule/all_absent` validates destructive cleanup of packages,
  repositories, bind mounts, service files, managed resources, and the
  PostgreSQL operating system user on Rocky Linux 9
- `molecule/bind_guardrails` validates that bind-mount migration fails safely
  when source and target both contain data or when PostgreSQL services are
  still running against the target directory
- `molecule/hba_guardrails` validates that pg_hba validation failures report
  specific root causes for invalid address usage, missing client CA
  configuration, and undefined certificate-auth map references
- `molecule/validation` validates valid and invalid PostgreSQL blueprints
  without installing PostgreSQL packages
- `molecule/timescaledb` validates TimescaleDB installation from both PGDG and
  the Timescale Community repository on Rocky Linux 9
- `molecule/rocky8` validates the baseline repository workflow on Rocky Linux
  8, including PGDG enablement, `powertools`, and PostgreSQL module disablement
- `molecule/rhel8` validates the same baseline repository workflow on Red Hat
  Enterprise Linux 8 UBI, including PGDG enablement, CodeReady Builder, and
  PostgreSQL module disablement
- `molecule/rhel9` validates the default multi-instance, bind, git, and
  repository workflow on Red Hat Enterprise Linux 9 UBI
- `molecule/replication` validates optional physical primary/standby
  replication between two Rocky Linux 9 containers, including standby
  bootstrap with `pg_basebackup` and replicated test data visibility
- `molecule/rocky10` validates the same baseline behavior on Rocky Linux 10
- `molecule/rhel10` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI

Run locally from the role directory:

```bash
molecule test
```

Run the default scenario only:

```bash
molecule test -s default
```

Run the `all_absent` scenario only:

```bash
molecule test -s all_absent
```

Run the bind guardrail scenario only:

```bash
molecule test -s bind_guardrails
```

Run the pg_hba guardrail scenario only:

```bash
molecule test -s hba_guardrails
```

Run the inventory validation scenario only:

```bash
molecule test -s validation
```

Run the TimescaleDB package-source scenario only:

```bash
molecule test -s timescaledb
```

Run the Rocky Linux 10 scenario:

```bash
molecule test -s rocky10
```

Run the Rocky Linux 8 repository scenario:

```bash
molecule test -s rocky8
```

Run the Red Hat Enterprise Linux 8 repository scenario:

```bash
molecule test -s rhel8
```

Run the Red Hat Enterprise Linux 9 UBI scenario:

```bash
molecule test -s rhel9
```

Run the replication scenario:

```bash
molecule test -s replication
```

Run the Red Hat Enterprise Linux 10 UBI scenario:

```bash
molecule test -s rhel10
```

Definitions
-----------

In PostgreSQL documentation, the term cluster refers to a collection of databases. However, this can be 
misleading, as cluster is more commonly used to describe a group of servers. In this document, the term 
cluster has been replaced with instance for clarity. A single host may run one or more PostgreSQL 
instances on different ports.

Architecture
------------

This Ansible role uses the iac_blueprint declarative inventory structure. It defines the desired end 
state of services — such as service versions, instances, configuration profiles, and users — in a clear, 
structured format. The role is responsible for interpreting this blueprint and applying the necessary 
changes, separating the what from the how.

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
repository file and its GPG key; the vendor installation script is not used.
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
