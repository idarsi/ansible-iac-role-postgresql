ANSIBLE-IAC-ROLE-POSTGRESQL
===========================
**COPYRIGHT** 2025 ^(ida|arsi)$ collective  
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
Installing PostgreSQL           | present             |
Uninstalling PostgreSQL         | absent              |
Create PostgreSQL instances     | instances_present   |
Remove PostgreSQL instances     | instances_absent    |
Start PostgreSQL instances      | instances_started   |
Stop PostgreSQL instances       | instances_stopped   |
Restart PostgreSQL instances    | instances_restarted |
Create databases                | databases_present   |
Remove databases                | databases_absent    |
Create database users           | users_present       |
Remove database users           | users_absent        |

Requirements
------------

- Operating system (tested on)
  - Fedora Linux 42
  - Fedora Linux 41
  - Red Hat Enterprise Linux 9
  - Red Hat Enterprise Linux 8
  - Rocky Linux 10
  - Rocky Linux 9
  - Rocky Linux 8

- Other components
  - Ansible 2.15 or higher

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
    state: users_present

  - role: ansible-iac-role-postgresql
    state: databases_present
```

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
      instances:
        - name: <instance name>                # must be unique on host
          port: <custom port>                  # default: version-specific PostgreSQL default
          configuration_profile: <name>        # e.g. "balanced"
          autotuning_profile: <name>           # e.g. "balanced"
          security_profile: <name>             # e.g. "safe"
          configuration:                       # optional, direct postgresql.conf overrides
            key: value
          databases:
            - name: <dbname>
              owner: <username>
              extensions:                      # Installs required OS package and runs CREATE EXTENSION in the database
                - name: <extension>
              access:                          # optional pg_hba.conf entries for this database
                - name: <username>
                  address: <CIDR>
                  type: <host|hostssl|local>   # optional, default: host
                  method: <auth_method>        # optional, default: scram-sha-256
          roles:                               # roles that exist in this instance
            - name: <username>
              password: <cleartext password>   # optional
              encrypted_password: <SCRAM hash> # optional
              createdb: true|false             # optional
              createuser: true|false           # optional
              superuser: true|false            # optional
              login: true|false                # optional
```

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

Minimal example: just install PostgreSQL with one instance

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: data
```
