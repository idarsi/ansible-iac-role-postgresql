ANSIBLE-ROLE-POSTGRESQL
=======================
**COPYRIGHT** 2025 ^(ida|arsi)$ collective  
**LICENSE** MIT License [LICENSE]
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

Global variables
----------------

