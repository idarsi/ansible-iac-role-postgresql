# Testing

This role uses Molecule with the Podman driver for automated integration
testing. The test matrix below describes the environments currently covered by
the repository. It is not a complete list of operating systems that the role
may work on.

## Automated test matrix

Platform/image                  | Ansible or application versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 8 UBI               | 17, 18              | `rocky8-baseline`             | PGDG repository and multi-version baseline installation
Red Hat Enterprise Linux 8 UBI | 17, 18              | `rhel8-baseline`              | PGDG repository and multi-version baseline installation
Rocky Linux 9.8 historical fixture (derived `replication` image, **amd64 only**) | 17 | `replication` | Physical primary/standby replication with systemd and the minimal signed-repository `iproute` prerequisite
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9-full`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10-baseline`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10-baseline`            | Baseline installation and multi-version coverage
Fedora 43                       | 17, 18               | `fedora43-baseline`          | PGDG repository and baseline installation
Fedora 44                       | 17, 18               | `fedora44-baseline`          | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 17, 18               | `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Managed three-member etcd, quorum recovery, Patroni failover, fresh auto-generated TLS certificates, and PostgreSQL 18 smoke coverage
Rocky Linux 9.8 historical fixture (derived `patroni_config` image, **amd64 only**) | 17 | `patroni_config` | Patroni configuration, endpoint normalization, TLS fixtures, and package/tool preflight
Rocky Linux 9 UBI               | 17, 18               | `rocky9-etcd-tls-member` | Custom safe generated destinations, generated-PKI guardrails, immutable external etcd TLS with access-group membership and peer-key isolation
Rocky Linux 8/10 UBI            | 17, 18               | `el8-el10-etcd-matrix`    | Managed etcd package and service coverage across EL8 and EL10 with PostgreSQL 18 smoke coverage

The coverage target is PostgreSQL 17 and 18 on Fedora, and PostgreSQL 16, 17,
and 18 on the longer-lived Rocky Linux and RHEL platforms. The Rocky Linux 8
and RHEL 8 baseline scenarios currently cover PostgreSQL 17 and 18, while the
Rocky Linux 9 and 10 and RHEL 9 and 10 scenarios cover PostgreSQL 16, 17, and
18.

The following scenarios are supplemental manual coverage and are not part of
the automated Molecule matrix or CI. They were not run during this change;
their playbooks are static coverage definitions only.

Platform/image                  | Ansible or application versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_patroni_failover`, `vagrant_etcd_quorum` | Three combined systemd VMs, static private endpoints, Patroni failover, and etcd quorum loss/recovery
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_etcd_leader_failure`, `vagrant_hard_patroni_failure`, `vagrant_network_partition`, `vagrant_quorum_primary_failure` | Manual leader replacement, guarded hard failure, symmetric partition, and DCS-loss safety/recovery
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_restart_smoke`, `vagrant_tls_rotation`, `vagrant_etcd_snapshot_restore` | Serial restart smoke with membership/data checks, test-only certificate rotation, and isolated etcd restore

The static checks completed for this change are YAML parsing of every repository
YAML file, production-profile `ansible-lint`, and syntax checks for the
documentation playbook, every scenario `converge.yml`, and the
`vagrant_patroni_failover/prepare.yml` and `vagrant_patroni_failover/verify.yml`
files. The CI workflow does not syntax-check the other Vagrant scenario
`prepare.yml` or `verify.yml` files. No Vagrant scenario passed an end-to-end run here; the
Vagrant scenarios remain unverified until the tester runs them with the required
Vagrant/libvirt host setup.

The focused empty managed-etcd endpoint-index contract is executable without
Molecule at `scripts/etcd_endpoint_index_contract_test.py`. It validates that
a minimal `state: validate` blueprint publishes
`pg_validation_etcd_endpoint_index` as a native empty list.

The focused PKI guardrail test is executable at
`scripts/pki_guardrails_test.sh`. It validates the shared registry parser
(from `files/pki_registry.sh`) for empty, malformed, zero, and duplicate
entries, plus exclusive lock behavior.
CI verifies that both PKI helper files are present and executable, then invokes
this script with Bash before installing collections and running Ansible lint.
The replication guardrail also executes the launcher with
`REPLICATION_TARGET_PYTHON_COMMAND` unset and verifies that the target-image
fallback reaches the mocked Molecule/prepare boundary without starting
Molecule.
The executable `scripts/controller_preflight_guardrails_test.py` check verifies that the
`update` state skips bootstrap and certificate/controller preflight, while
controller CA checks use only absolute inspection-tool paths, fail clearly when
tools are absent, reject relative/non-string/traversal source fixtures before
filesystem inspection, and remain skipped when no CA source is configured. It
also guards the read-only validation path from package mutation.
The focused managed-etcd metadata guardrail test is executable at
`scripts/etcd_metadata_guardrails_test.py`; it checks path validation ordering,
fresh-marker lifecycle handling, ancestor symlink/write protections, and
named/default marker ACL rejection.
The executable `scripts/etcd_data_directory_lifecycle_test.py` additionally
parses the role's actual data-root, `config.data_dir`, metadata, and marker
derivation expressions, then creates only controller-local temporary
directories, files, symlinks, and (when available) ACLs. It exercises
absent/fresh, correctly marked, wrong owner/group expectations, writable and
ancestor-mode mutations, marker tamper/symlink, named/default ACL, metadata
overlap, replacement refusal, and dangling-data-symlink presence cases. The
fixture uses the invoking user's explicit numeric uid/gid and never resolves or
changes the production `root`/`etcd` accounts; production owner names and
modes are verified from the role source. If ACL tools are unavailable, ACL
cases are clearly reported as `SKIP` rather than failing. An actual wrong-owner
mutation is not portable without privilege and is therefore represented by a
wrong expected numeric identity; an actual wrong-group mutation runs only when
the invoking user has an alternate supplementary group. No sudo or account
creation is used, and no host ownership is changed.
The static-analysis job installs `acl` and `util-linux` on its Ubuntu runner
for these checks. Each Molecule job installs the same two packages alongside
Podman and explicitly checks `getfacl` and `namei` before running scenarios;
the validation target `prepare.yml` independently installs both packages in
the target fixtures, while controller-side fixture checks remain controller
prerequisites and do not mutate the controller.
It does not inject a filesystem failure into Ansible's real rollback shell;
partial-rollback recovery remains covered by the fail-closed journal/manifest
implementation and requires disposable-host fault injection by the tester.

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
  configuration, undefined certificate-auth map references, and empty or
  ambiguous client CA content/source inputs.
 - `molecule/validation` validates valid and invalid PostgreSQL blueprints
   without installing PostgreSQL packages, including the missing-blueprint
   execution-context guardrail, platform-before-blueprint validation ordering,
   destructive cleanup path validation, and PostgreSQL instance-name validation.
   It also covers strict IPv4/IPv6 replication CIDRs and rejects malformed,
   non-string, whitespace, comment, and pg_hba token-injection address values.
   Raw Patroni HBA coverage uses the cluster-effective security profile,
    including an instance-less cluster's secure default, rejects mixed instance
    profiles and nested Patroni profile overrides, and exercises native boolean
    broad-address opt-in and safe-profile restrictions. It also verifies native
    string enforcement for `security_profile` and `security_ssl`, including YAML
    boolean coercion, non-string values, independent field failures, and quoted
    `safe`/`off` acceptance. It also verifies that
    incomplete managed-etcd TLS (including a client-CA-only definition) fails
    with an actionable incomplete-TLS/CA message. DCS scheme mismatches are
    exercised in independent plays for both HTTP-with-TLS and
    HTTPS-without-TLS, each with its own expected rescue assertion. It also
    verifies that invalid raw HBA and mixed-profile validation leave pre-existing
   configuration sentinels unchanged, including content, ownership, modes,
   timestamps, package state, and service state. The dedicated `prepare.yml`
   creates the fixtures and records snapshots; `converge.yml` performs no
   fixture setup or mutation.
    Remote snapshots and sentinels are fixture state only, stored under the
    run-scoped `/run/ansible-validation/<scenario-host-ephemeral-basename>`
    root. This path is not used for Ansible remote, async, or controller-local
     temporary files; destroy removes only a validated, marker-owned root. The
     checks require `/` and `/run` to be root-owned, non-symlink directories
     without group/other write (allowing Rocky/Podman's legitimate `0555` `/`),
     while the scenario artifact parents remain exact `0700` private directories.
    The validation scenario does not exercise fresh `clusters_present`
   convergence or generate certificates. It only validates the certificate
   inputs and guardrails, including external Patroni TLS ancestor rejection;
    validation does not mutate those paths. Patroni endpoint guardrails also
    cover bracketed IPv6 scheme-free rendering, member-derived connect defaults,
    and rejection without publishing invalid records into the host-wide index.
    Fresh auto-generated Patroni/etcd
   certificate paths are covered by the `rocky9-etcd-tls-member` and
   `rocky9-etcd-tls-cluster` lifecycle scenarios, which require the ACL/path
   tooling contract before certificate generation. External etcd TLS inputs
   additionally require an explicit pre-provisioned shared access group;
   those lifecycle scenarios verify effective etcd and Patroni reads while
   preserving external file and parent metadata.
   - `molecule/validation` additionally performs lightweight controller-side
    assertions for proxy exclusion, version/cluster model isolation, inventory
    identity mismatch rejection, orphan transaction guardrails, and
     host-specific replication CA source validation. It also validates a regular
     controller CA source without target mutation or source-content logging. The
     latter verifies that
    each inventory host validates only its own delegated controller source;
     it does not claim a cross-host barrier or global aggregation. Its destroy
     lifecycle uses isolated marked fixtures to exercise valid stale-root
     reprepare behavior and refusal/preservation for hidden, manifest, symlink
     target, and symlink component tampering.
     The validation callback is configured explicitly for both the provisioner
     and verifier through
     `IDARSI_VALIDATION_CALLBACK_ROOT` and `IDARSI_VALIDATION_CALLBACK_PATH` by
     `molecule.yml`. It writes only to the current run's private Molecule
     directory, with parent/destination symlink, ownership, mode, and ACL
     checks. There is no `/tmp/validation-callback.log` fallback; missing or
     unsafe callback configuration fails closed. Callback task fields are
     opaque stable SHA-256 identifiers, never raw task names, so controls,
     credentials, and variable expressions cannot be emitted.
 - `molecule/patroni_config` verifies that a valid raw Patroni HBA record is
  rendered identically into Patroni configuration and PostgreSQL HBA output.
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
  replication between two derived Rocky Linux 9.8 UBI containers on native
  linux/amd64, including the
  minimal `iproute` image prerequisite, standby
  bootstrap with `pg_basebackup`, replicated test data visibility, default
   Podman bridge connectivity, and effective `pg_hba`/`client_addr` checks.
  Molecule builds `molecule/replication/Dockerfile.j2` from an immutable Rocky
  Linux 9.8 UBI init digest during `create`, before Ansible gathers facts;
  the layer installs the exact `iproute` NEVRA from Rocky 9.8 HTTPS
  repositories with certificate, repository-metadata, and package signature
  verification, then cleans DNF metadata. The key is downloaded over verified
  HTTPS and its full primary fingerprint is checked before any DNF or
  repository use; pre-existing repository files are moved aside and every DNF
   operation explicitly selects only the three pinned Rocky repositories. The
   Dockerfile, CI, and prepare assertions require native amd64; they fail rather
   than silently selecting QEMU or another architecture. The installed Podman
   Molecule plugin does not support a platform `architecture` key, so the
   scenario omits that key and enforces the policy through the image build and
   runtime checks instead. Rocky does not expose
  content-addressed repository metadata for 9.8, so those URLs remain mutable
  and the image is not fully reproducible; the static image guardrail checks
   the digest, URLs, exact NEVRA, signing-key fingerprint, ordering, repository
   isolation, and security options. The runtime `$(rpm -q ...)` command
   substitution strips rpm's trailing record newline; the shared normalizer
   accepts that exact single record but rejects interior or multiple records.
   The shell guardrail restores a fixture's trailing newline when testing the
   normalizer's newline path.
   Before `create`, CI pulls the exact digest with Podman, records its actual
   image ID and repo digest in runner-scoped provenance and environment
   variables, and `prepare.yml` compares the derived image's `RootFS.Layers`
   prefix against the recorded base image layers. This is an independent
   chain check rather than a label check; a matching label with a different
   base layer fails. Local runs must provide
   `MOLECULE_REPLICATION_BASE_IMAGE_ID` and
   `MOLECULE_REPLICATION_BASE_REPO_DIGEST` from an equivalent pre-build
    an absolute Podman executable's `pull`/`image inspect` step. OCI images built with layer
   squashing or a non-Podman builder may not preserve this layer-prefix
    relationship and are unsupported by this guardrail.
    CI resolves the controller Python and Molecule entry point from the
    `actions/setup-python` installation through `scripts/replication_runtime.sh`,
    not through `command -v`; Podman, Molecule, netavark, and aardvark-dns must
     each be non-symlink regular executables before Python or Molecule runs. Python
     entrypoints are preserved (virtualenv and `actions/setup-python` may expose
     them through symlinks), while their resolved targets are validated as regular
     executables. Netavark and aardvark-dns
    remain resolved from fixed system locations and are exported alongside the
    Podman and provenance variables.
   The Rocky signing key is checked against the authoritative fingerprint
  `21CB256AE16FC54C6E652949702D426D350D275D`; no repository checksum is
  currently available, so a mismatch fails closed. The image uses privileged
   containers to run systemd. The controller must use rootless Podman; container
   privilege is a disposable test exception and is not production role behavior.
    Replication connects to each container as `root` through the Podman container
    connection plugin and uses `ansible_become_method: su` for every play and
    task that escalates. `prepare.yml` verifies that `/usr/bin/su` exists and is
    executable before convergence. This test-only contract has no sudo fallback
    and no image package changes; host-layer least privilege and rootless Podman
    remain unchanged.
   Containers start with the supported Podman plugin `extra_opts` value
   `--network=podman`. The scenario deliberately
  omits the platform `network` setting: the Molecule Podman plugin otherwise
    treats the platform `network` value as scenario-owned and its initial destroy
   attempts to remove it. `prepare.yml` requires the exact `podman` mapping and
   rejects host, pasta, and extra networks. Molecule therefore destroys only
   the containers and never owns or deletes Podman's reserved default bridge.

### Replication fixture trust and key rotation

The replication fixture is intentionally **linux/amd64-only** and targets the
historical Rocky Linux 9.8 repositories. It is not a production repository
configuration. The image build verifies the Rocky key fingerprint
`21CB256AE16FC54C6E652949702D426D350D275D` and fails closed on mismatch. A
repository-published checksum for the key is not available; the fingerprint is
therefore authoritative. On rotation, obtain the replacement key from Rocky's
official HTTPS distribution, independently verify its published fingerprint,
update the URL/fingerprint in `Dockerfile.j2` and the static guardrail, then
rebuild and review the resulting image digest and package NEVRA. Do not accept
a changed fingerprint merely to repair a failing build, and do not retain the
old key unless Rocky documents an overlap period.
 - `molecule/patroni_config` validates Patroni configuration convergence from a
   shared cluster blueprint using the supported `clusters_present` state. Its
   derived, amd64-only Rocky 9.8 fixture pins the base image digest and uses
   HTTPS Rocky repositories with certificate, metadata, and package-signature
   verification to preinstall the exact `bash` package used as the
    Patroni/etcd test double, plus `acl`, `util-linux`, `openssl`, and `python3`
     for the role's certificate preflight. The fixture checks package facts and
     absolute regular executable paths before converge. Rocky may expose
     `/usr/bin/python3` as a symlink, so the test-only preflight follows it for
     the executable check while retaining the configured entrypoint; it does not alter
    production package behavior. The static
   `scripts/patroni_config_image_guardrails_test.py` rejects moving images,
   insecure repositories, and update/distro-sync/allowerasing/nobest/downgrade
    style mutations. Rocky 9.8 repository metadata is mutable and has no
    content-addressed snapshot; the digest, signing-key fingerprint, and exact
    package NEVRA checks are a fail-closed snapshot guard, not a claim of full
    image reproducibility. Its focused assertions cover the secure loopback listener,
   advertised REST and PostgreSQL connect addresses, and DCS endpoint scheme
   normalization.
The production-role changes present in this broader repository work are
intentional security hardening and lifecycle improvements; they are not
test-only changes or workarounds for the `patroni_config` fixture. The fixture
only persists its resolved interpreter as a host-local fact so verification
does not depend on the target's `PATH`.
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
- `molecule/rocky9-etcd-tls-member` validates a TLS-enabled managed etcd member,
  including fresh auto-generated Patroni/etcd certificate paths, custom
  generated destinations, secure ownership/modes, and cleanup of issuance
  artifacts. Its second convergence provisions fake external CA,
  client, and peer material with a pre-existing access group, parent metadata,
  and ACLs; it verifies that validation leaves that content and metadata
  unchanged, that etcd and Patroni can read their required client material, and
  that Patroni cannot read the peer-only key.
- `molecule/rocky9-etcd-tls-cluster` validates a three-member TLS etcd cluster,
  fresh auto-generated Patroni/etcd certificates, client and peer certificate
  configuration, and TLS quorum recovery.
- `molecule/vagrant_patroni_failover` is supplemental manual Vagrant/libvirt
  coverage using three combined Rocky Linux 9 VMs. It stops the actual Patroni
  primary while retaining etcd quorum, checks the replacement leader and data,
  and verifies that the failed member rejoins. It checks SELinux enforcing and
  etcd and Patroni listeners bind to the configured static private addresses.
  Its Vagrant-only `prepare.yml` installs and starts firewalld, assigns `eth1`
  to a dedicated private-cluster zone, and permanently and immediately allows
   only source `192.168.250.0/24` to TCP ports 2379, 2380, 5432, and 8008.
   `pg01` is the disposable CA authority; only its public CA certificate is
   distributed. Each guest receives distinct client and peer leaf keys, and
   verification checks the common CA fingerprint, leaf uniqueness, and chain
   validation. The authority's private staging directory remains on pg01 and
   is never copied to another guest. The transaction helper uses descriptor
   reads, no-follow/lstat checks, a journal with identity metadata, and
   fail-closed recovery. These controls do not eliminate races against a
   privileged process or guarantee durability across filesystem/device power
   loss. Firewalld is configured before wildcard listeners and the NAT
   interface is not admitted to the private zone.
- `molecule/vagrant_etcd_quorum` is supplemental manual Vagrant/libvirt
  coverage using the same three-VM topology. It stops two etcd services, proves
  a client write fails without quorum using a separate probe key, restores both
  members, and verifies the original committed continuity key, membership, and
  actual Patroni leader. The probe request may commit asynchronously after the
  client reports failure and is removed after recovery. It also verifies the
  Patroni private listener. Its Vagrant-only `prepare.yml` applies the same
   dedicated-zone firewalld rules before role convergence.
- `molecule/vagrant_etcd_leader_failure` stops the discovered etcd leader only,
  then checks leader replacement, key continuity, endpoint health, and rejoin.
  This is an operational DCS smoke test, not a guarantee for every failure mode.
- `molecule/vagrant_hard_patroni_failure` uses the guarded host helper
  `scripts/vagrant-ha-virsh.sh` to destroy exactly one expected libvirt domain,
  then starts it again and checks promotion, continuity, and rejoin.
- `molecule/vagrant_network_partition` adds a temporary priority reject rule to
  the dedicated `eth1` firewalld zone and always removes it. NAT/SSH (`eth0`) is
  untouched; a task barrier confirms both host-side rules before disruption
  assertions. This validates guest firewall behavior, not a switch-level or
  perfectly simultaneous packet cut; host scheduling and already-in-flight
  connections remain limitations. Asymmetric packet loss is out of scope. If the
  verifier is interrupted, manually remove the temporary rule on `pg01` and
  `pg02` with `firewall-cmd --zone=idarsi-private --remove-rich-rule="rule family=ipv4 source address=<peer-private-address> priority=-100 reject"` and the same command with `--permanent`, then verify with `--query-rich-rule`; never alter the NAT/SSH zone.
- `molecule/vagrant_quorum_primary_failure` combines etcd quorum loss with a
  Patroni primary stop and asserts no unsafe write or promotion before recovery.
- `molecule/vagrant_restart_smoke` restarts Patroni serially and checks health,
  three-member membership, one-leader safety, and PostgreSQL data continuity.
  It is not a PostgreSQL major-upgrade test.
- `molecule/vagrant_tls_rotation` creates a disposable CA and a distinct leaf
  for each etcd member, with that member's DNS and private IP SANs. It installs
  an old+new trust bundle, rotates one member at a time, and after every
  rotation asserts certificate ownership/mode, effective PostgreSQL read
  access, exactly three Patroni members (one leader and two replicas), and both
  PostgreSQL and DCS continuity markers. It is test-only coverage and does not
  exercise role-managed issuance. Old-CA removal or revocation is not
  implemented or covered; the old CA intentionally remains in the temporary
  trust bundle for this compatibility smoke test.
- `molecule/vagrant_etcd_snapshot_restore` restores a live etcd snapshot into a
  fresh disposable directory and cluster identity, never over live data.
  PostgreSQL data is explicitly not restored.
- `molecule/el8-el10-etcd-matrix` validates managed PGDG etcd installation and the
  local etcd and Patroni endpoints on EL8 and EL10.
- `molecule/rocky10-baseline` validates the same baseline behavior on Rocky Linux 10.
- `molecule/rhel10-baseline` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI.
- `molecule/fedora43-baseline` and `molecule/fedora44-baseline` validate PostgreSQL 17 and 18
  installations from the Fedora-specific PGDG repository workflow.

The GitHub Actions workflow runs syntax and production-profile lint checks in
the `ansible-lint` job. Molecule jobs are independent and run in parallel by
scenario; they are not gated by that static-analysis job. Pull requests and
pushes to `main` run a fast representative matrix;
the complete automated scenario matrix runs once per day and can also be started with
`workflow_dispatch`.

The fast matrix contains `replication`, `validation`, `rocky9-full`,
`all_absent`, `patroni_config`, `rocky10-baseline`, `rhel10-baseline`, and
`fedora44-baseline`. `replication` runs in the fast matrix exactly as CI
executes it: through `scripts/replication_molecule.sh`, including its native
amd64, pinned-image provenance, trusted-runtime, and reserved-network
preflight. The daily matrix runs
all automated scenarios listed in this document, including the older EL and
Fedora baseline images, replication and guardrail scenarios, both TimescaleDB
repository variants, and the multi-member Patroni and etcd scenarios. It
excludes the supplemental manual Vagrant scenarios.

The workflow cancels an older in-progress run for the same branch or scheduled
workflow when a newer run starts.

The daily replication job checks the runner's native `x86_64` host and
Podman's native `amd64` runtime before Molecule can build the image. The image
Dockerfile passes the explicit `linux/amd64` platform to its pinned base image;
Docker's `FROM --platform=linux/amd64` may otherwise invoke emulation when the
host is ARM. Native amd64 host and runtime preflight is therefore required
before the build, and both replication platforms explicitly set
`pre_build_image: false` so Molecule uses the checked-in Dockerfile build.
Emulation is intentionally unsupported. A local bypass of the preflight may
build successfully and fail only later in `prepare.yml`; that late failure is
not a supported local execution mode.

The replication image is test-only and does not affect the role's runtime
package or systemd behavior. The reserved `podman` network is pre-existing;
the replication helper and workflow never create or remove it.
Containers attach to it through the explicit `--network=podman` creation
option. The platform `network` key remains unset because the installed
Molecule Podman plugin deletes a configured `item.network` during destroy. The
prepare play inspects the actual container network settings and fails fast
unless the exact reserved network is present; pasta and host-network fallback
are rejected. Converge discovers the standby address and subnet from the
`podman` network, and verification checks the effective PostgreSQL HBA and
`client_addr` against it.

If an interrupted replication run prevents container destruction, run the
container-only cleanup through the trusted replication runtime helper:

```bash
export IDARSI_ANSIBLE_TESTING_VENV="${IDARSI_ANSIBLE_TESTING_VENV:-/home/arsi/.local/share/venvs/idarsi-ansible-testing}"
export REPLICATION_PYTHON_COMMAND="${IDARSI_ANSIBLE_TESTING_VENV}/bin/python"
export REPLICATION_MOLECULE_COMMAND="${IDARSI_ANSIBLE_TESTING_VENV}/bin/molecule"
. ./scripts/replication_runtime.sh
replication_runtime_preflight
export MOLECULE_PODMAN_EXECUTABLE="${REPLICATION_PODMAN_COMMAND}"
export CONTAINERS_HELPER_BINARY_DIR
"${REPLICATION_MOLECULE_COMMAND}" destroy -s replication
```

The preflight validates configured or discovered Podman, Molecule, netavark,
and aardvark-dns paths as absolute, no-follow regular executables. It
canonicalizes the trusted Python entry point before validating the resulting
executable, and exports the canonical Podman, Molecule, Python, netavark, and
aardvark-dns paths. This strict runtime policy applies to
the `replication` scenario only. Do not remove the `podman` network. For all other scenarios, run
`molecule destroy -s <scenario>`. Do not invoke a separate `molecule cleanup`
phase unless that scenario provides a cleanup playbook.
For a disruption scenario, manually restore stopped services with
`systemctl start etcd.service patroni-17-main.service postgresql-17-main.service`
as applicable, remove temporary firewalld rules using the commands above, and
remove `/tmp/molecule-etcd.snap`, `/tmp/molecule-restored-etcd.pid`,
`/tmp/molecule-restored-etcd.log`, and any `molecule-etcd-restore-*` directory
on the guest. These are best-effort
operator recovery steps; interrupted verification cannot guarantee automatic
cleanup.

The CI workflow installs the exact Ansible Core, ansible-lint, Molecule, and
molecule-plugins versions defined in `requirements-ci.txt` in its isolated
Python environment. The shared local environment must not be modified to
match these pins. Check for a version mismatch first and report it instead of
installing or upgrading packages.

The validation scenario's controller-side fixture checks require the portable
`getfacl` and `namei` commands to already exist on the controller. Install the
packages providing these commands through the controller's normal OS
provisioning (for example, `acl` and `util-linux` on RHEL/Rocky). The scenario
fails clearly when either command is absent and never installs controller
packages. The target-host prepare play provisions `acl` and `util-linux`
through the target play with `su`.

The Vagrant scenarios are supplemental manual coverage and are not run in CI.
They require Vagrant, the libvirt provider/plugin, libvirt/KVM, and resources
for three Rocky Linux 9 guests. The pinned box and static private addresses
make the topology reproducible, but host networking, provider versions, SELinux
policy packages, and firewall defaults can still vary. These scenarios do not
test host suspend, power loss, split-brain fencing, or a two-node etcd cluster;
they use disposable, one-day, self-signed test certificates and deliberately
insecure fake Patroni/PostgreSQL credentials. These fixtures must never be
used outside disposable test guests. The scenarios assert SELinux enforcing
and required listeners; their Vagrant-only prepare playbooks also configure
the guest firewalld rules needed by the private cluster network. Firewalld
remains guest-owned and is not managed or claimed by this role.

The Vagrant `prepare` playbooks install the signed PGDG repository package and
enable its Rocky Linux 9 extras repository before installing the test `etcd`
package. Because those packages can upgrade OpenSSL while the guest's sshd is
still linked to the previous library, each prepare playbook reboots every
guest after package setup and waits for Ansible connectivity before creating
certificates or applying configuration. The reboot uses the existing NAT SSH
interface and does not change host networking. No repository or package setup
is required on the host.

The supplemental Vagrant scenarios require the pre-existing libvirt network
`idarsi-postgresql-molecule`. Each platform explicitly sets the vagrant-libvirt
provider URI to `qemu:///system`; this prevents Vagrant's default/session URI
from silently selecting a different network namespace. The Vagrant interface keeps
`network_name: private_network` (the valid Molecule Vagrant interface type) and
uses `libvirt__network_name` to select that existing vagrant-libvirt network.
Clean environments also require Vagrant, libvirt, and the `vagrant-libvirt`
provider version 0.11.2 on the host. The CI requirements pin the Molecule Vagrant
plugin, but do not install host Vagrant or libvirt packages.
Vagrant-libvirt and the setup commands must use the same libvirt connection URI:
`qemu:///system`. The system
libvirt daemon owns the network and VM definitions; they are not per-user
session resources. The user running the setup script and Vagrant must be
authorized to access the system libvirt socket (commonly through the local
`libvirt` group and/or a matching polkit rule; the exact group and policy are
distribution-specific). Do not run Vagrant with `sudo` to work around missing
authorization. The libvirt daemon also needs access to the VM storage, and its
service account (`qemu`, `libvirt-qemu`, or the platform equivalent) must be
able to read or write those paths. A session URI instead keeps resources
owned by the invoking user and requires the same user for setup and Vagrant.
The network and VM resources must still be created and accessed through that
URI.
The network must provide `192.168.250.0/24`; guest addresses are reserved by
MAC from `192.168.250.201` through `192.168.250.203`, outside the default DHCP
range. Each Vagrant private interface specifies a fixed MAC address, and the
dedicated network XML contains the matching libvirt DHCP host reservation.
This avoids relying on NetworkManager profile creation or post-boot address
changes. The NAT connection on `eth0` therefore remains the Ansible SSH path
and default route across reboots. The prepare playbooks install a managed
`/etc/hosts` block mapping `pg01`/`pg02`/`pg03` to the reserved addresses.
The disposable etcd certificate includes both these DNS names and IP SANs, so
TLS verification remains enabled when either form is used.

Set up this dedicated network explicitly before running either scenario:

```bash
export LIBVIRT_DEFAULT_URI="${LIBVIRT_DEFAULT_URI:-qemu:///system}"
./scripts/setup-idarsi-postgresql-molecule-network.sh
virsh -c "${LIBVIRT_DEFAULT_URI}" net-info idarsi-postgresql-molecule
virsh -c "${LIBVIRT_DEFAULT_URI}" net-dumpxml idarsi-postgresql-molecule
```

The repository-local script defines, starts, and enables autostart for this
dedicated network on `${LIBVIRT_DEFAULT_URI:-qemu:///system}` when it does not
already exist. When it already exists, it adds the three reservations to the
live and persistent network configuration, and refuses a conflicting MAC/IP
reservation or a matching MAC/IP reservation with a different hostname. It
never deletes an existing host network. Review the XML and choose a different
unused subnet and matching guest addresses if `192.168.250.0/24` conflicts
with the test host. Do not run the scenarios until the named network exists
and is active on the URI Vagrant will use. Keep `LIBVIRT_DEFAULT_URI` exported
when running the Vagrant scenario commands below.

## Running tests

Run the production-profile Ansible Lint check and syntax check using the
shared local test environment. The commands below do not install packages or
modify that environment. Set `IDARSI_ANSIBLE_TESTING_VENV` to the path of the
shared test environment before running them:

```bash
export IDARSI_ANSIBLE_TESTING_VENV="${IDARSI_ANSIBLE_TESTING_VENV:?Set this to the shared idarsi-ansible-testing environment}"
PATH="${IDARSI_ANSIBLE_TESTING_VENV}/bin:$PATH" \
  ANSIBLE_ROLES_PATH=.. ansible-lint --profile production
PATH="${IDARSI_ANSIBLE_TESTING_VENV}/bin:$PATH" \
  ANSIBLE_ROLES_PATH=.. ansible-playbook --syntax-check \
  -i docs/inventory-example.yml docs/playbook-example.yml
```

Compare the shared environment with the project pins before running tests:

```bash
PATH="${IDARSI_ANSIBLE_TESTING_VENV}/bin:$PATH" \
  python - <<'PY'
from importlib.metadata import version

expected = {
    "ansible-core": "2.21.3",
    "ansible-lint": "26.8.0",
    "molecule": "26.8.0",
    "molecule-plugins": "26.7.15",
}
for package, required in expected.items():
    installed = version(package)
    status = "OK" if installed == required else "MISMATCH"
    print(f"{package}: installed={installed}, required={required} [{status}]")
PY
```

If any package is marked `MISMATCH`, use the CI environment or report the
mismatch; do not change the shared environment.

The contract scripts use `ansible-playbook` from `PATH` by default. To run
them with the shared environment, either prepend its `bin` directory to
`PATH`, or set `ANSIBLE_PLAYBOOK_COMMAND` to an explicit executable:

```bash
export IDARSI_ANSIBLE_TESTING_VENV="${IDARSI_ANSIBLE_TESTING_VENV:-/home/arsi/.local/share/venvs/idarsi-ansible-testing}"
export PATH="${IDARSI_ANSIBLE_TESTING_VENV}/bin:$PATH"
python scripts/cluster_collision_paths_test.py
# Alternatively: ANSIBLE_PLAYBOOK_COMMAND="${IDARSI_ANSIBLE_TESTING_VENV}/bin/ansible-playbook" \
#   python scripts/cluster_collision_paths_test.py
```

Molecule's current releases do not provide Ansible Lint as a built-in
scenario phase, so this is a separate static-analysis gate in the same test
workflow. The repository's `.ansible-lint` file keeps the profile and shared
exclusions in version control.

Run all automated scenarios from the role directory. This excludes the
resource-intensive manual Vagrant scenarios. The reserved `podman` network
must already exist; the workflow and helper never create or remove it. Their
`always()` cleanup destroys only the replication containers:

The following snippets are POSIX `sh` compatible; they do not require Bash.

```bash
set -eu
for scenario in molecule/*; do
    case "${scenario##*/}" in
        vagrant_*) continue ;;
    esac
    if [ "${scenario##*/}" = replication ]; then
        ./scripts/replication_molecule.sh || exit 1
    else
        molecule test -s "${scenario##*/}" || exit 1
    fi
done
```

Run the supplemental manual Vagrant scenarios separately, only when Vagrant,
libvirt/KVM, and the required guest networking are available:

```bash
for scenario in molecule/vagrant_*; do
    molecule test -s "${scenario##*/}" || exit 1
done
```

Run an individual non-replication scenario:

```bash
molecule test -s <scenario>
```

For an individual replication run, use the repository helper. It pulls and
inspects the exact pinned base digest, exports its image ID and repo digest,
then runs Molecule; container creation selects Podman's default bridge with
the explicit `--network=podman` option:

```bash
./scripts/replication_molecule.sh
```

The helper traps exit and destroys only the containers. If interrupted, use the
container cleanup procedure above; do not remove the `podman` network. The
command deterministically builds and uses the derived image from
`molecule/replication/Dockerfile.j2`; no manual image tag or role runtime
override is required.

The replication scenario requires exact base-image metadata. Use
`scripts/replication_molecule.sh`, which sources the runtime helper and runs its
strict preflight before any Podman, image, or Molecule operation. The preflight
rejects missing, relative, symlinked, or non-executable values, validates
no-follow regular executables, canonicalizes trusted paths internally, exports
`REPLICATION_PODMAN_COMMAND`, `REPLICATION_MOLECULE_COMMAND`,
`REPLICATION_PYTHON_COMMAND`, `REPLICATION_TARGET_PYTHON_COMMAND`,
`REPLICATION_NETAVARK_COMMAND`, and
`REPLICATION_AARDVARK_COMMAND`, and passes their common directory to Podman as
`CONTAINERS_HELPER_BINARY_DIR`; it does not modify PATH or accept
arbitrary search directories. The wrapper exports the same absolute
executable in `MOLECULE_PODMAN_EXECUTABLE` and must be used to launch the
scenario. Bare `molecule test -s replication` is unsupported because the
Molecule Podman driver does not consume `driver.environment`; `molecule.yml`
therefore does not claim to configure that process environment. `prepare.yml`
resolves Podman, Molecule, netavark, and aardvark-dns only from the same fixed
trusted candidate lists used by the wrapper; it uses `stat(follow=false)` and
accepts only regular executable files. An explicitly supplied wrapper value is
never replaced, and `prepare.yml` never uses `command -v` or another PATH
search. It fails closed when the controller Python executable or fixed
repository provenance helper is unavailable. The controller
`REPLICATION_PYTHON_COMMAND` and target-host
`REPLICATION_TARGET_PYTHON_COMMAND` contracts are independent. The launcher
defaults the target variable to the target-image interpreter
`/usr/bin/python3` when it is unset, and passes that value through
`molecule.yml` to `prepare.yml`, where the target interpreter is validated.
Override it before launching when the image uses another absolute executable:

```bash
REPLICATION_TARGET_PYTHON_COMMAND=/usr/local/bin/python3 \
  ./scripts/replication_molecule.sh
```

Use the launcher for direct replication runs; bare `molecule` invocation does
not provide the launcher fallback or the trusted runtime exports. This
replication-only setup also requires rootless Podman, netavark, aardvark-dns, and
the Molecule Podman plugin. The prepare contract requires exactly `podman` and
rejects host, pasta, or extra networks. The plugin guardrail parses the installed
destroy playbook and verifies its `item.network is defined` condition; the
scenario's unset `network` therefore prevents reserved-network deletion. The
Molecule-helper guardrail additionally verifies that failed execution still
attempts container destruction without issuing any network removal.

Useful scenarios include:

```bash
molecule test -s rocky9-full
molecule test -s validation
molecule test -s timescaledb
molecule test -s patroni_config
molecule test -s patroni_membership
molecule test -s patroni_failover
molecule test -s rocky9-etcd-cluster
molecule test -s rocky9-etcd-tls-member
molecule test -s rocky9-etcd-tls-cluster
molecule test -s vagrant_patroni_failover
molecule test -s vagrant_etcd_quorum
molecule test -s vagrant_etcd_leader_failure
molecule test -s vagrant_hard_patroni_failure
molecule test -s vagrant_network_partition
molecule test -s vagrant_quorum_primary_failure
molecule test -s vagrant_restart_smoke
molecule test -s vagrant_tls_rotation
molecule test -s vagrant_etcd_snapshot_restore
molecule test -s el8-el10-etcd-matrix
molecule test -s rocky8-baseline
molecule test -s rhel8-baseline
molecule test -s rhel9-full
molecule test -s rocky10-baseline
molecule test -s rhel10-baseline
molecule test -s fedora43-baseline
molecule test -s fedora44-baseline
```

Run replication only with the complete individual replication command above.
It supplies the pinned image provenance and uses the reserved pre-existing
`podman` network without attempting to create or remove it. Rootless Podman is
required by the shared runtime preflight.

Run only syntax checks when working on task or scenario structure:

```bash
molecule syntax -s <scenario>
```

The scenarios use Ansible Galaxy collections for their test infrastructure. The
role requires `ansible.posix` at runtime for managed etcd ACLs; scenario tasks
also use `ansible.posix` and `containers.podman`. The pinned versions are listed
in `collections.yml`.
The repository lock file pins `ansible.utils` to 6.1.0, `ansible.posix` to
2.2.2, and `containers.podman` to 1.20.2. `ansible.utils` supplies the
`ip_address` tests used by the role; `ansible.posix` and `containers.podman`
are used by scenario tasks and test infrastructure. These exact versions are
also used by the full Molecule scenarios.

Known limitation: the guardrail that refuses Patroni reinitialization when
existing data is present but the expected service unit is unknown is not
covered by a Molecule scenario. It depends on the host's live systemd service
fact inventory; the implementation guard remains covered by static review and
the normal Patroni lifecycle scenarios exercise the known-service path.

Known limitation: `rocky9-etcd-tls-cluster` requires an active SELinux policy
and both the `getenforce` and `restorecon` tools because managed TLS
certificate installation is intentionally fail-closed. Before running the
scenario, explicitly classify the controller's Podman runtime:
`MOLECULE_HOST_RUNTIME_ROOTLESS_PODMAN=true` for rootless Podman, or `false`
otherwise. The value is passed through Molecule inventory; the target
container is not expected to contain the Podman CLI. The scenario skips only
when the value is `true` **and** the SELinux policy/tooling check fails. An
unknown or missing classification, and missing SELinux capability on a
non-rootless host, fail the scenario; they are never silently skipped. The
role's production security behavior is not relaxed.
The external TLS snapshot compares content hashes, owner/group/mode, file
timestamps, parent metadata, ACLs, and SELinux contexts. SELinux checks are
skipped when policy tooling is unavailable (as in unsupported rootless
containers); the scenario still checks all other metadata and access rules.
# Validation cleanup test limitation

Tamper cases deliberately invoke the shared destroy cleanup and assert that a
refused cleanup preserves the root before collecting evidence.  The fixture is
then removed by a separately path-validated test teardown; this teardown is a
disposable-test limitation and is not production cleanup behavior.
