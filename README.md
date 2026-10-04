> **Maturity State: Beta**<br>
> **RC Readiness: 85%**

## Maturity assessment

Assessed ref: the current working tree, including staged changes, against `HEAD` commit `fb38fb9`. Evidence includes the role implementation, defaults, documentation, CI definitions, 311 parsed YAML documents, production-profile Ansible Lint, syntax checks, and focused guardrail tests. The new baseline-service, endpoint-collision, and replication-inspection guardrails pass locally. Molecule execution is not claimed: no completed end-to-end scenario run or successful CI result for this change set is available. Supplemental Vagrant scenarios remain static manual coverage only. This is an engineering-readiness assessment, not production approval.

| Category / criterion | Score | Evidence / rationale |
|---|---:|---|
| **Scope and Public Contract** | **10/12** | |
| Purpose and boundaries | 3/3 | README documents PostgreSQL, Patroni/etcd boundaries, destructive cleanup, and ownership. |
| Inputs and states | 4/5 | Blueprint structure, defaults, validation tasks, and state table are extensive; the large interface is not represented by role metadata. |
| Support contract | 3/4 | Rocky/RHEL/Fedora and PG 16–18 support, PGDG sources, and prerequisites are documented and defaulted. |
| **Functional Completeness** | **19/20** | |
| Core convergence | 8/8 | Installation, versions, instances, configuration, databases, roles, extensions, replication, Patroni, and managed etcd are implemented. |
| Applicable lifecycle | 6/6 | Present/absent, start/stop/restart, update, cleanup, replication, membership, and failover paths are implemented; supplemental Vagrant recovery paths are static/manual coverage only in this worktree. |
| Platform and dependency handling | 3/3 | EL/Fedora repository paths, interpreters, PGDG packages, and Patroni/etcd dependencies are handled. |
| Failure and rerun behavior | 2/3 | Validation and retry/rejoin paths are present; supplemental outage, failure, partition, restart, rotation, and restore scenarios remain unrun here, and interruption and rollback coverage is not complete. |
| **Validation and Safety** | **16/20** | |
| Preflight validation | 5/6 | Types, required fields, references, conflicts, paths, HBA, cluster, replication, and platform checks are implemented before mutation. |
| Secure behavior | 5/6 | Safe SSL defaults, certificate handling, restrictive permissions, repository checks, and escaped SQL are documented/implemented; external PKI and firewall remain boundaries. |
| Destructive guardrails | 4/5 | Explicit destructive states, PostgreSQL-specific path checks, ownership markers, and guardrail scenarios protect cleanup. |
| Check and diff behavior | 2/3 | Validation-only non-mutation is tested; representative mutating check-mode coverage is incomplete. |
| **Convergence and Recovery** | **10/13** | |
| Idempotent convergence | 4/5 | Idempotence is exercised in normal and Patroni paths; broad state coverage is not evidenced at this ref. |
| State transitions | 3/4 | Removal, outage, failover, and rejoin scenarios cover important transitions; not all transitions have equivalent evidence. |
| Operational recovery | 3/4 | Handlers, retries, quorum restoration, member rejoin, serial restart, TLS rotation, and isolated DCS restore are implemented; supplemental Vagrant execution is not verified here. Host suspend/power-loss and rollback evidence is absent. |
| **Automated Testing and CI** | **22/25** | |
| Static quality checks | 3/3 | CI defines production-profile ansible-lint and syntax checks; both passed locally for this worktree. |
| Input validation tests | 4/4 | Validation scenario covers valid/invalid blueprints, ordering, cleanup, and actionable failures without installation. |
| Functional verification | 6/6 | Existing Molecule scenarios and supplemental Vagrant verification playbooks define observable package, service, database, replication, Patroni, etcd, TLS, failover, quorum recovery, restart, partition safety, snapshot restore, and rejoin checks; Vagrant execution is not claimed here. |
| Idempotence tests | 3/4 | Representative normal and Patroni idempotence runs exist; complete state coverage is not shown. |
| Lifecycle and guardrail tests | 4/4 | Cleanup, bind/HBA guardrails, outages, failover, membership, rejoin, partition safety, restart, TLS rotation, and snapshot-restore checks are present; supplemental Vagrant execution remains unverified. |
| Supported-platform matrix | 2/3 | Automated EL8–10 and Fedora 43–44 matrix is declared; current green evidence and every version path are not independently confirmed here. |
| CI enforcement | 0/1 | Workflow is present, but no successful CI run for this uncommitted worktree/ref was available as assessment evidence. |
| **Documentation and Release Hygiene** | **8/10** | |
| Operator documentation | 4/4 | README includes requirements, states, examples, safety behavior, platforms, repositories, and limitations. |
| Test and limitation documentation | 2/2 | TESTING.md documents the matrix, commands, Vagrant host prerequisites, known gaps, and the unrun supplemental Vagrant scenarios; those scenarios remain manual and are excluded from CI. |
| Contribution contract | 1/2 | CONTRIBUTING.md covers blueprint validation, examples, tests, and syntax; release-impact guidance is limited. |
| Repository and release metadata | 1/2 | License, pinned CI dependencies, collections, and history exist; standard role metadata/version compatibility declarations are absent. |
| **Total RC Readiness** | **85/100** | Rounded down per the assessment method; current changes improve verification diagnostics and static guardrails, but do not establish end-to-end execution evidence. |

**State decision:** Numeric state is **Beta** (60–99%). The mandatory Beta cap applies because platform/support coverage remains materially unverified at this ref and the expanded Vagrant scenarios are supplemental manual evidence, not CI-gated. No successful CI result for this change set, completed Molecule scenario run, Stable/Mature production review, or production approval is claimed.

**RC blockers and missing evidence:** obtain a green CI result for the assessed change set and complete representative Molecule scenarios in a clean, correctly pinned environment; expand check-mode, interruption/rollback, and full lifecycle/platform coverage; add standard role metadata and release compatibility declarations. The supplemental Vagrant evidence still requires Vagrant, libvirt/KVM, the pinned provider, a prepared system-libvirt network, guest resources, and host authorization; it cannot substitute for CI or production-like evidence. The smallest readiness gains are clean Molecule/CI evidence, focused check-mode and interruption/rollback tests, broader platform evidence, and metadata completion.

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
> The role's main functionality is substantially implemented, with scenario
> definitions and static verification evidence covering supported Enterprise
> Linux versions. It supports
> multi-version and multi-instance PostgreSQL deployments, database and role
> management, extensions, replication, inventory validation, repository
> workflows, filesystem handling, and destructive cleanup. Molecule execution
> is not claimed for this assessment: environment blockers prevented reliable
> scenario completion, so functional and lifecycle coverage remains incomplete
> or unverified. The role remains at Beta because its interfaces and behavior
> may still change, and broader long-term production evidence and
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

Supported operating systems and lifecycle targets:

Operating system                | Supported versions | Upstream lifecycle target
--------------------------------|--------------------|-------------------------
Rocky Linux                     | 8, 9, 10           | Rocky 8 until 31 May 2029; Rocky 9 until 31 May 2032; Rocky 10 until 31 May 2035
Red Hat Enterprise Linux (UBI)  | 8, 9, 10           | RHEL 8, 9 and 10 follow Red Hat's ten-year lifecycle; planned major-release ends are 31 May 2029, 31 May 2032 and 31 May 2035
Fedora                          | 43, 44             | Approximately 13 months per release; Fedora 43 is maintained until one month after Fedora 45, and Fedora 44 until one month after Fedora 46

The Rocky Linux dates are based on the [Rocky Linux release guide](https://wiki.rockylinux.org/rocky/version/).
RHEL and UBI follow the [Red Hat Enterprise Linux lifecycle policy](https://access.redhat.com/support/policy/updates/errata);
the role does not manage Red Hat subscriptions. Fedora follows the
[Fedora release lifecycle](https://fedoraproject.org/wiki/Fedora_Release_Life_Cycle),
so its end dates move with the actual release schedule. These lifecycle
targets should be reviewed when adding or removing a supported major version.

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
Updating installed role-managed packages | update              |
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
Run post-install SQL jobs       | post_installs_present |

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

The `update` state updates only packages that are both managed by this role and
currently installed on the host. It does not run a general system-wide DNF
update, install packages that are missing, install certificate bootstrap
packages, or run certificate/controller-source preflight. The role records
packages it installs in a marker file and uses that record for later updates.

The automated `validation` scenario exercises validation and no-mutation
behavior only; it does not run fresh `clusters_present` convergence or generate
certificates. Fresh auto-generated Patroni and etcd certificate paths are
covered by the Rocky Linux 9 TLS lifecycle scenarios. See [TESTING.md](TESTING.md)
for the executed matrix and scenario boundaries. Its disposable fixture cleanup
accepts safe root-owned, non-symlink system ancestors without group/other write
(including Rocky/Podman's legitimate `0555` container `/`) while retaining exact
`0700` permissions for private scenario artifact parents.

The replication Molecule fixture is test-only and linux/amd64-only. Its
Dockerfile uses `FROM --platform=linux/amd64`, which may invoke emulation on an
ARM host; native amd64 host and Podman runtime preflight is required before the
image build. Bypassing that local preflight may allow the build to complete and
then fail late during preparation, and is not a supported execution mode. See
[TESTING.md](TESTING.md) for the required checks and replication networking behavior.

The `all_absent` state is intentionally destructive: it removes PostgreSQL
packages, repository configuration, service files, data, logs, and the
PostgreSQL operating system user. Use it only when the host should be reset to
a clean pre-PostgreSQL baseline.

Requirements
------------

- Operating systems covered by the automated Molecule test matrix are listed
  in [TESTING.md](TESTING.md).

- Other components
  - Ansible Core 2.21.3 (the pinned CI version)
  - The repository collection lock pins `ansible.utils` to 6.1.0,
    `ansible.posix` to 2.2.2, and `containers.podman` to 1.20.2.
    `ansible.posix` is a runtime dependency for managed etcd ACLs; these are
    the versions used with the repository's Ansible Core 2.21.x CI line; see
    [collections.yml](collections.yml).

The versions used by the automated CI test environment are documented in
[requirements-ci.txt](requirements-ci.txt) and installed by GitHub Actions.
Use the same file before running Molecule locally so local and CI tests use the
same Ansible Core, ansible-lint, Molecule, and molecule-plugins versions.

### Clean-host certificate preflight

The role first performs pure inventory, schema, and path-model validation. On a
clean host, `present` (and the `install` state that invokes it) then installs
only the certificate inspection bootstrap packages (`acl`, `coreutils`,
`openssl`, and `util-linux`). This bootstrap package installation is the only
unavoidable mutation before tool-dependent certificate checks. No PostgreSQL
application, configuration, or data is changed before those checks complete.
The full certificate/PKI preflight runs immediately afterward, before normal
state convergence. Cluster seed-artifact checks run on the selected seed host;
local certificate destinations are checked on each current host.

Usage
=====

How to run playbook with inventory
----------------------------------

Use playbook and inventory examples to create your own playbook and run command below.

```bash
ansible-playbook -i <inventory_file> <playbook_file> -kK
```

From the repository root, the executable example can be syntax-checked or run
without installing the checkout or editing an Ansible configuration file:

```bash
ANSIBLE_ROLES_PATH="$(pwd)/.." ansible-playbook -i <inventory_file> docs/playbook-example.yml -kK
```

`ANSIBLE_ROLES_PATH` points at the parent of this checkout, which is the role
search path required by the role name used in the example.

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

Patroni member identity is strict: `inventory_hostname` and the managed
instance name must match one declared `clusters[].members` record. A mismatch
is rejected before Patroni configuration is changed, with an actionable error.

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

The package is selected only when the cluster DCS provider is `etcd3`. When
managed etcd is not enabled, external etcd remains the responsibility of the
surrounding role or infrastructure layer. The default package name can be
overridden with `pg_patroni_etcd_package`, while additional Patroni packages
can be supplied through `pg_patroni_additional_packages`.

For hosts listed in `dcs.etcd.members`, define the local etcd bind address
explicitly, for example in host variables:

```yaml
pg_etcd_bind_address: 10.0.0.11
```

The `dcs.etcd.members[].host` value is an inventory identity used to select and
delegate to a managed host; it is not the etcd endpoint address. Endpoint
addresses belong in `peer_url`, `client_url`, and DCS `endpoints`, which may use
DNS names or bracketed IPv6 literals independently of the inventory name.

TLS certificates for Patroni and managed etcd can either be supplied by the
inventory or generated by the role. The existing `ca_file`, `cert_file`, and
`key_file` fields remain supported. Set `auto_generate: true` to create a
cluster CA and member certificates automatically. The CA private key remains
on the first cluster member; only the CA certificate and member certificate
are distributed. Generated certificates use the configured member hostname in
their subject alternative name.

The generated etcd leaves are member-specific: each host receives separate
client and peer key/certificate pairs for its own cluster member. Client
certificates use client-authentication EKU; peer certificates use
server/client EKU. Client and peer material use their explicit
`etcd-client.*` and `etcd-peer.*` destinations. The supplemental TLS-rotation scenario
follows the same rule and additionally includes each member's private IP SAN;
it does not use a shared leaf.

Generated CA and staging artifacts remain only on the seed host in the
dedicated `/var/lib/postgresql-pki-seed` directory, `root:root` mode `0700`
with no default ACLs; private artifacts are mode `0600`. Distributed generated CA certificates and etcd member material are
normalized to `root:etcd` mode `0640`; Patroni receives explicit ACL access only
to client CA/certificate/key material, never to peer-only private keys. Managed
PKI directories have no default ACLs, preventing inherited access from
weakening that isolation.

When `auto_generate` is false, etcd TLS paths are external immutable inputs.
Define `tls.access_group` (or `pg_etcd_external_tls_access_group`) as a
pre-provisioned POSIX group containing both `etcd` and the Patroni/PostgreSQL
service account for parent-directory traversal and client CA/certificate/key
files. Peer certificate/key files must instead be `root:etcd` mode `0640`;
they must not be readable by Patroni (a shared peer/client CA is permitted).
The role validates regular non-symlink
files, ownership, `0640` mode, parent traversal, absence of named/default ACLs,
SELinux context, and effective positive and negative reads for both accounts.
It never creates, chowns, chmods, relabels, or grants access to external TLS
files or parent directories; missing or overly broad access fails with an
actionable error.

External managed-etcd TLS is an all-material contract: a partial definition
(for example, only `client.ca_file`) is rejected as incomplete before any host
mutation. Use `auto_generate: true` for role-generated client and peer
material, or provide the complete external CA, certificate, key, and access
group settings.

PKI replacement uses a per-pair staging directory on the destination
filesystem, validates the complete key/certificate/CSR set, and then commits
with a journal recording original state and commit progress. Runtime rollback
restores only paths committed by that transaction and refuses to overwrite a
path changed by another process. A failed rollback preserves staging and
backup paths and fails loudly without printing certificate contents.
This is **not** a filesystem-level atomicity guarantee: multiple destinations
cannot be replaced atomically by ordinary filesystem operations. Root-owned
per-pair locks serialize generation, commit, rollback, and recovery. Startup
detects any orphan manifest, preserves its staging and backups, and fails
loudly for operator recovery rather than silently converging a partial pair.
If interrupted, inspect the reported staging directory's `manifest` and
`journal`, restore any recorded backups as appropriate, and remove the staging
directory only after verifying the destination pair. The next run intentionally
fails until this recovery decision is made.
The guarantee is pair commit/rollback semantics during a running role task;
crash recovery and injected-failure behavior are not claimed as tested. Generated
certificate serials are random, reserved under a
root-owned `0600` per-CA registry protected by `flock`, and checked against
all existing generated certificates. Zero serials, duplicate registry entries,
and duplicate certificate serials are rejected; random allocation retries on
zero or collision.

All controller-side CA sources (replication and client CA sources) use the same
strict policy before any managed-host mutation: an existing root-owned regular
non-symlink file, readable by its owner, with no group/other write permission
(modes matching `^0?[4-7][0145][0145]$`). The controller preflight, replication
runtime guard, and client CA installation enforce this policy consistently.

Managed etcd `client.key_file` and `peer.key_file` destinations must be
different. The role grants Patroni access to client material and explicitly
removes access to peer-only material; sharing these paths would defeat that
isolation and is rejected during inventory validation.

For managed etcd:

The blueprint keeps HTTPS endpoints so the role can validate and configure
secure transport. When rendering Patroni `etcd3.hosts`, the role removes the
URL scheme and supplies `protocol: https` plus the configured TLS files,
matching the format expected by supported Patroni versions.

```yaml
dcs:
  provider: etcd3
  endpoints: [https://pg01:2379, https://pg02:2379, https://pg03:2379]
  etcd:
    enabled: true
    tls:
      auto_generate: true
    members:
      - {name: etcd01, host: pg01, peer_url: https://pg01:2380, client_url: https://pg01:2379}
      - {name: etcd02, host: pg02, peer_url: https://pg02:2380, client_url: https://pg02:2379}
      - {name: etcd03, host: pg03, peer_url: https://pg03:2380, client_url: https://pg03:2379}
```

For Patroni REST API TLS, place `auto_generate: true` under
`patroni.restapi`. Automatic generation creates the server certificate and CA.
The default REST listener is `127.0.0.1:8008`; an omitted advertised address
uses the member's inventory hostname at port 8008. The listener remains the
explicit loopback-only insecure exception, while a routable advertised REST
address requires TLS and the
required authentication mapping; wildcard listeners are rejected. To expose
the endpoint, either enable `auto_generate: true` or provide `enabled: true`
with complete `cafile`, `certfile`, and `keyfile` inputs (and a valid
authentication username and password).
`verify_client: optional` permits clients with certificates while retaining
compatibility with the role-managed Patroni readiness client; the TLS scenario
verifies both a valid client request and a certificate-less request succeed. The role does
not currently manage a separate operator client certificate/key/CA trust chain,
so `verify_client: required` is rejected during validation. Use `none` or
`optional` until complete client-credential management is supported.

The `pg_patroni_restapi_endpoint_fallback_address` variable supplies the host
part of the default advertised REST endpoint when
`patroni.restapi.connect_address` is omitted. Its default is the member's
inventory-derived host, while the listener remains loopback-only. A custom fallback must be a
non-empty hostname or IP address without control characters; invalid values
are rejected during validation before host mutation. The effective port is
`pg_patroni_restapi_port` unless `patroni.restapi.port` overrides it.

The fallback is an advertised address, not a listener override: an explicit
`patroni.restapi.listen` remains authoritative. The role checks that the
rendered `patroni.yml` `restapi.connect_address` agrees with the canonical
per-instance endpoint model. A routable fallback therefore has the same
security contract as any advertised endpoint: enable TLS with generated or
complete external certificate material and provide REST authentication. Do not
use a routable HTTP fallback.

Patroni listen endpoints are checked host-wide before mutation. Same-port
wildcard listeners overlap all addresses, including across address families:
`0.0.0.0:port` and `[::]:port` are conservatively rejected because the role
does not explicitly enforce `IPV6_V6ONLY`. Specific IPv4 and IPv6 listeners
remain valid when the operating system can bind them independently.

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
HTTP endpoints are rejected. With external TLS (`auto_generate: false`),
certificate files must be pre-provisioned by the surrounding certificate
workflow and are treated as immutable by the role. With
`tls.auto_generate: true`, the role generates the required certificates during
`clusters_present` or `install` lifecycle before enabling the cluster. The
current implementation supports static cluster bootstrap. Add/remove member
operations and snapshot/restore remain separate operational procedures.

Use `state: clusters_present` to converge Patroni configuration and its service
unit without changing PostgreSQL databases or roles. This state is not a
package-free render operation: it installs the configured Patroni, PostgreSQL,
and (for `etcd3`) etcd prerequisites, plus the certificate-generation tools,
before rendering configuration. Use `state: validate` when a no-mutation
blueprint check is required. `state: install` also handles the cluster
configuration as part of the normal installation flow.

All other role states run the same inventory validation automatically before
performing their state-specific work.

When an instance uses TimescaleDB, `instances_started` ensures the selected
TimescaleDB package and repository are present before starting the PostgreSQL
service. This prevents PostgreSQL from starting before its configured preload
library has been installed.

Setting `pg_patroni_reinitialize` is destructive: it stops the local Patroni
service and removes the local instance data directory before bootstrap. It is
disabled by default and must only be enabled for an intentional, disposable
rebootstrap.
Post-bootstrap configuration finalization never enables this operation.

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

The `safe` security profile uses `hostssl` as the default network access type
and rejects explicit non-SSL host access. Generated server certificates include
the configured `certificate_subject_alt_names` values (default: `localhost`).
These names can be set per instance when clients connect using another DNS
name.

`security_ssl` defaults to the selected `security_profile`. The combination
`security_profile: safe` with `security_ssl: off` is rejected because it would
claim the safe HBA policy while disabling its required TLS transport. Use
`security_ssl: safe` with the safe profile, or explicitly select
`security_profile: off` when the less restrictive profile is intentional.

Before destructive cleanup, the role validates that its data and log roots are
absolute PostgreSQL-specific paths ending in `/pgsql`, rejects traversal and
system-root paths, and requires a role-managed marker created by the `present`
state. Custom data roots such as `/srv/data/pgsql` are supported; cleanup
refuses unmarked roots.

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
           security_ssl: <safe|off>              # optional; defaults to security_profile
           certificate_subject_alt_names:       # optional DNS SANs for generated certificate
            - <dns name>
          client_certificate_authority_content: |  # optional complete trusted CA PEM; provide real PEM content
            # Example intentionally omitted: this field must contain one complete PEM certificate.
          client_certificate_authority_src: <path> # optional controller-side CA PEM path for client certificate auth
          replication:                        # optional physical primary/standby replication settings
            role: <primary|standby>
            replication_user: <username>
            replication_password: <cleartext password>
            allowed_standby_addresses:        # primary only
              - <CIDR>
            primary_host: <hostname or IP>    # standby only
            primary_port: <port>              # standby only, default 5432
            sslrootcert: <absolute CA destination> # standby only, mandatory
            sslrootcert_content: <CA content>     # exactly one of content/src
            primary_certificate_subject_alt_names: # standby only, must include primary_host
              - <hostname or IP matching primary_host>
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

Physical replication uses `sslmode=verify-full` and an explicit `sslrootcert`
in durable standby connection settings. The primary host must be present in
the server certificate SAN and the primary pg_hba rule must be `hostssl`.
Certificates containing only a CN may require replacement; the role fails
closed rather than weakening certificate verification.

Before standby bootstrap, provide a trusted CA through replication
`sslrootcert_content` or `sslrootcert_src`; both the CA input and an absolute
`sslrootcert` destination are required. The role does not assume that a default
or system CA trusts the primary. Provide exactly one non-empty CA input; defining
both is rejected as ambiguous. Controller-side source files for both replication
and client certificate authorities must be root-owned, non-symlink regular files
with an owner-readable mode and no group/other write bits. This matches the
strict ownership policy used before the source is copied to the runtime-owned
certificate path. Set
`primary_certificate_subject_alt_names` on the standby replication record and
include `primary_host`; this documents and validates the SAN contract. The role
writes the replication password to the postgres-owned 0600 `.pgpass` beside
the data directory, while `primary_conninfo` retains `verify-full` and the CA
path for reconnects.

Controller-side CA source checks are delegated to `localhost` for each managed
host immediately before that host's state-specific work. Sources are deduplicated
within the host only; the role does not aggregate sources across hosts and does
not provide a cross-host validation barrier. Consequently, `serial` and `free`
strategies validate each host's own sources as that host reaches the role, and
controller checks inspect source metadata only without changing target hosts or
printing certificate contents.

When controller-side CA sources are present, the role requires the absolute
controller paths `/usr/bin/getfacl` and `/usr/bin/namei`. It fails clearly on
localhost when either executable is missing, and never installs controller
packages, changes PATH, or mutates controller files. AWX, CI, and remote
execution environments must provision these tools externally. With no
controller-side CA source, these tools are not required. Target hosts receive
the `acl` and `util-linux` prerequisites only for states that perform the
certificate preflight.

Raw Patroni `pg_hba` entries intentionally use a restricted, unquoted grammar:
the supported authentication methods are `trust`, `reject`, `scram-sha-256`,
`md5`, `password`, `peer`, `ident`, `cert`, `pam`, `ldap`, `radius`, `gss`,
and `sspi`. PostgreSQL 17 `oauth` entries and quoted/advanced option forms are
not accepted; validation fails with the supported-method message rather than
silently claiming compatibility.
In every profile except the explicit `off` profile, password-based network
methods (`password`, `md5`, `scram-sha-256`, `pam`, `ldap`, and `radius`) are
accepted only on `hostssl` records and require PostgreSQL TLS; this applies to
both structured and raw HBA records. Local peer and other local methods remain
available. Structured HBA options use the supported PostgreSQL subset:
`clientcert`, `clientname`, `map`, PAM, LDAP, RADIUS, Kerberos, GSS delegation,
and `account` options with validated values. Unknown, duplicate, conflicting,
or invalid options fail closed. Raw HBA options use the same validated names
and values; quoted and advanced PostgreSQL forms remain intentionally rejected.

All DCS server endpoints and an optional proxy must use one uniform `http` or
`https` scheme. HTTPS endpoints and proxies are supported only for the `etcd3`
provider, where enabled etcd client TLS renders Patroni's TLS protocol and
files. The role does not manage the provider-specific TLS models for `consul`
or `kubernetes`; those providers must use HTTP endpoints, and proxies are
available only with `etcd3`. HTTP renders no TLS protocol. Mixed or
unsupported schemes are rejected. Managed etcd is fail-closed: when managed
etcd TLS is enabled/rendered, every client endpoint and proxy must be HTTPS.
Validation covers HTTP-with-TLS and HTTPS-without-TLS as separate failure
cases so neither mismatch can be hidden by an earlier failure.

Endpoint models retain whether the input explicitly supplied `http://` or
`https://` in `has_scheme`; omitted schemes use the applicable TLS-derived
default. DNS names are lower-cased and one terminal DNS dot is removed for
rendering and SAN identities. IP literals are canonicalized with Ansible's IP
address filter (including compressed IPv6), and IPv6 is bracketed only when
rendered as host:port. The canonical host is the sole source for endpoint
rendering, readiness checks, and certificate SAN identities.

For `host`, `hostssl`, and `hostnossl` raw records, the address token must be a
dotted IPv4 address or CIDR, a valid IPv6 address or CIDR, or exactly
`samehost`/`samenet`. `local` records have no address token. Raw records are
single-line records separated by ASCII spaces; tabs, controls, comments,
quotes, arbitrary address tokens, and unsupported PostgreSQL line forms are
rejected before rendering. The accepted raw line is rendered unchanged after
validation; it is never silently reparsed or reinterpreted. The
`patroni.allow_broad_hba` opt-in must be a native YAML boolean and only permits
the explicitly broad CIDR address tokens `0.0.0.0/0` and `::/0`. Bare wildcard
addresses (`0.0.0.0` and `::`) are rejected even with the opt-in; use the CIDR
forms so the contract is unambiguous.
It does not bypass safe-profile or authentication-method restrictions.
The same exact-token contract applies to `replication.allow_broad_hba`; a
non-canonical address with a broad prefix (for example `192.0.2.1/0`) is
rejected even when the opt-in is true.

Patroni raw HBA validation is cluster-scoped and runs for every Patroni
cluster, including clusters with no instances, before any state mutation. A
cluster with instances derives its effective profile from those instances;
mixed `security_profile` values are rejected as ambiguous. An instance-less
cluster uses the documented default `pg_patroni_default_security_profile`,
which defaults to `safe`. Set the profile on instances, not under
`patroni.security_profile`; that nested override is rejected.

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
            sslrootcert: /var/lib/pgsql/17/data/primary-root-ca.crt
            # Public, fake CA certificate for documentation only; never use it
            # to secure a real deployment.
            sslrootcert_content: |
              -----BEGIN CERTIFICATE-----
              MIIDRzCCAi+gAwIBAgIUO5aYETKMpyN4/PT5iAiUbfToIxswDQYJKoZIhvcNAQEL
              BQAwKzEpMCcGA1UEAwwgZXhhbXBsZS5pbnZhbGlkIGRvY3VtZW50YXRpb24gQ0Ew
              HhcNMjYwOTE0MjM0MTI5WhcNMzYwOTExMjM0MTI5WjArMSkwJwYDVQQDDCBleGFt
              cGxlLmludmFsaWQgZG9jdW1lbnRhdGlvbiBDQTCCASIwDQYJKoZIhvcNAQEBBQAD
              ggEPADCCAQoCggEBAN4d8zdXSpaZpYo4+j6S80tKfwGpnukVfp/gG9D/xKdPu5lg
              iNkMhHHMq0yXfR9WStx+Nwcq8GgLfhES8v/sHCqhETz/DuX6eOuxKYaT5R7TMFr6
              zpQbAu8zIyIC/yUDn7FmP4EcHSYoUJB/mBwopjn5hW3AdoOxODHWCM2JJZjEmfWN
              ia8rVqp94HhNSr/ZI6sF1c74fmZY53ZBquJbTpY6O26dyNTD7PnVZbCR+0oLncj9
              BJR5Eqr7LB4uCcA9dKPaMa9jrrdVQayXOv+OkbnF1/+BokowlyBr9osCwaRZxYWi
              ah41xU+tHcuDOt2zn/NaxYWUwDpb9heFzb/RXZECAwEAAaNjMGEwHQYDVR0OBBYE
              FBYHjCwvZ7feOLMaNLZ+JEKu+gvZMB8GA1UdIwQYMBaAFBYHjCwvZ7feOLMaNLZ+
              JEKu+gvZMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMA0GCSqGSIb3
              DQEBCwUAA4IBAQBCCujSyZ1R9XLxn4I7ySbkzp6A5694pUlGRh/HnErX6SUx6+k2
              BYmPAcWAvzmf8IB1Iz2vZ1qO6/ev1G9CI2+W4YzSKX4P45XywKhwecwXji5ZJa9L
              WNE8B/auD1wCObdk3JHPnlbZsS9TAh3yaaqNfIQfiHev5jq9T4AFUaJ6HWxV2m23
              pnH8a1XoFmGu4/m+gZbcr7pMDHqkBAzQOgtdu2uqz0DkHOSyT1KHDojCCunVl6nK
              LjXJbzKpI225/vyIAgMRLEGY5NbD2gAiU9lca/R0HtgTLnJiabWwAiYaKjmCpXo7
              0HjKuAt7PZwjlACKicKX0VdI/mvANRRjADd3
              -----END CERTIFICATE-----
            primary_certificate_subject_alt_names:
              - 192.168.1.10
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
                      type: hostssl
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
                sslrootcert: /var/lib/pgsql/17/data/primary-root-ca.crt
                sslrootcert_content: |
                  -----BEGIN CERTIFICATE-----
                  MIIDRzCCAi+gAwIBAgIUO5aYETKMpyN4/PT5iAiUbfToIxswDQYJKoZIhvcNAQEL
                  BQAwKzEpMCcGA1UEAwwgZXhhbXBsZS5pbnZhbGlkIGRvY3VtZW50YXRpb24gQ0Ew
                  HhcNMjYwOTE0MjM0MTI5WhcNMzYwOTExMjM0MTI5WjArMSkwJwYDVQQDDCBleGFt
                  cGxlLmludmFsaWQgZG9jdW1lbnRhdGlvbiBDQTCCASIwDQYJKoZIhvcNAQEBBQAD
                  ggEPADCCAQoCggEBAN4d8zdXSpaZpYo4+j6S80tKfwGpnukVfp/gG9D/xKdPu5lg
                  iNkMhHHMq0yXfR9WStx+Nwcq8GgLfhES8v/sHCqhETz/DuX6eOuxKYaT5R7TMFr6
                  zpQbAu8zIyIC/yUDn7FmP4EcHSYoUJB/mBwopjn5hW3AdoOxODHWCM2JJZjEmfWN
                  ia8rVqp94HhNSr/ZI6sF1c74fmZY53ZBquJbTpY6O26dyNTD7PnVZbCR+0oLncj9
                  BJR5Eqr7LB4uCcA9dKPaMa9jrrdVQayXOv+OkbnF1/+BokowlyBr9osCwaRZxYWi
                  ah41xU+tHcuDOt2zn/NaxYWUwDpb9heFzb/RXZECAwEAAaNjMGEwHQYDVR0OBBYE
                  FBYHjCwvZ7feOLMaNLZ+JEKu+gvZMB8GA1UdIwQYMBaAFBYHjCwvZ7feOLMaNLZ+
                  JEKu+gvZMA8GA1UdEwEB/wQFMAMBAf8wDgYDVR0PAQH/BAQDAgEGMA0GCSqGSIb3
                  DQEBCwUAA4IBAQBCCujSyZ1R9XLxn4I7ySbkzp6A5694pUlGRh/HnErX6SUx6+k2
                  BYmPAcWAvzmf8IB1Iz2vZ1qO6/ev1G9CI2+W4YzSKX4P45XywKhwecwXji5ZJa9L
                  WNE8B/auD1wCObdk3JHPnlbZsS9TAh3yaaqNfIQfiHev5jq9T4AFUaJ6HWxV2m23
                  pnH8a1XoFmGu4/m+gZbcr7pMDHqkBAzQOgtdu2uqz0DkHOSyT1KHDojCCunVl6nK
                  LjXJbzKpI225/vyIAgMRLEGY5NbD2gAiU9lca/R0HtgTLnJiabWwAiYaKjmCpXo7
                  0HjKuAt7PZwjlACKicKX0VdI/mvANRRjADd3
                  -----END CERTIFICATE-----
                primary_certificate_subject_alt_names:
                  - 192.168.1.10
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
```

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
