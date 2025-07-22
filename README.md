ANSIBLE-ROLE-POSTGRESQL
=======================
**COPYRIGHT** 2025 ^(ida|arsi)$ collective  
**LICENSE** MIT License [LICENSE]()  
**AUTHORS**
- Arsi Atomi <arsi@atomi.sh>  

Overview
========

This Ansible role is designed to simplify and enhance the flexibility of PostgreSQL management.

Supported PostgreSQL versions (from PostgreSQL repository):
- PostgreSQL 17
- PostgreSQL 16

These operations are supported:
- Installing PostgreSQL
- Uninstalling PostgreSQL
- Creating PostgreSQL instance
- Removing PostgreSQL instance
- Starting PostgreSQL instance service
- Stopping PostgreSQL instance service
- Creating database
- Removing database
- Creating database user
- Removing database user

Requirements
------------

- Operating system (one mandatory)
  - Fedora Linux 42
  - Fedora Linux 41
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
      extensions:                              # (optional) extensions installed at package level
        - name: <extension_name>
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
              extensions:                      # optional per-database extensions (CREATE EXTENSION)
                - name: <extension>
              access:                          # optional pg_hba.conf entries for this database
                - name: <username>
                  address: <CIDR>
                  type: <host|hostssl|local>   # optional, default: host
                  method: <auth_method>        # optional, default: scram-sha-256
          users:                               # users that exist in this instance
            - name: <username>
              password: <cleartext password>   # optional
              encrypted_password: <SCRAM hash> # optional
              createdb: true|false              # optional
              createuser: true|false            # optional
              superuser: true|false             # optional
              login: true|false                 # optional
```

A minimal working iac_blueprint that installs PostgreSQL 17 with one instance and allows user app to 
connect to database appdb from a specific network:

```yaml
iac_blueprint:
  postgresql:
    - version: 17
      instances:
        - name: main
          users:
            - name: app
              password: changeme
          databases:
            - name: appdb
              owner: app
              access:
                - name: app
                  address: 192.168.1.0/24
```
