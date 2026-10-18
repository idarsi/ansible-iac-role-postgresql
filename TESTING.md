# Testing

This role uses Molecule with the Podman driver for automated integration
testing. The test matrix below describes the environments currently covered by
the repository. It is not a complete list of operating systems that the role
may work on.

## Automated test matrix

Platform/image                  | Ansible or application versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 9 UBI               | 16, 17, 18          | `rocky9-full`, `all_absent`, `bind_guardrails`, `hba_guardrails`, `replication`, `timescaledb`, `validation`, `patroni_config`, `patroni_failover`, `patroni_membership`, `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Full baseline, cleanup, guardrails, physical replication, inventory validation, TimescaleDB sources, Patroni membership, failover, and managed etcd
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9-full`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10-baseline`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10-baseline`            | Baseline installation and multi-version coverage
Fedora 43                       | 17, 18               | `fedora43-baseline`          | PGDG repository and baseline installation
Fedora 44                       | 17, 18               | `fedora44-baseline`          | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 17, 18               | `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Managed three-member etcd, quorum recovery, Patroni failover, TLS etcd, and PostgreSQL 18 smoke coverage
Rocky Linux 9/10 UBI            | 17, 18               | `el9-el10-etcd-matrix`    | Managed etcd package and service coverage across EL9 and EL10 with PostgreSQL 18 smoke coverage

The coverage target is PostgreSQL 17 and 18 on Fedora, and PostgreSQL 16, 17,
and 18 on Rocky Linux and RHEL 9 and 10.

## Ansible Core compatibility lanes

The role's minimum supported line is Ansible Core 2.19.12. The recommended
development line is 2.20.8. Ansible Core 2.21.3 is a forward-compatibility
probe until the role explicitly adopts it as a supported line.

| Ansible Core | Purpose | Automated coverage |
| --- | --- | --- |
| 2.19.12 (`ansible-min`) | Minimum supported line | Scheduled `validation` and `rocky9-full` compatibility scenarios |
| 2.20.8 (`ansible-current`) | Recommended development line | Pull-request fast scenarios and the complete scheduled automated Molecule matrix |
| 2.21.3 (`ansible-next`) | Forward-compatibility probe | Scheduled `validation` and `rocky9-full`; non-blocking until adopted |

The compatibility scenarios check the same validation and baseline paths at
the version boundaries. They do not run the full feature matrix on every
Ansible Core line. Update this table and the README support claim together when
the supported range changes.

The following KVM scenarios are supplemental manual coverage and are not part of
the automated Molecule matrix or CI. They use the shared Idarsi test environment
and its `idarsi-test` libvirt network, and install from the official Rocky Linux 9 tree:

Platform/image                  | Ansible or application versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 9 KVM guests from the configured install ISO | 17 | `kvm_patroni_failover`, `kvm_etcd_quorum` | Three combined systemd VMs, static private endpoints, Patroni failover, and etcd quorum loss/recovery
Rocky Linux 9 KVM guests from the configured install ISO | 17 | `kvm_etcd_leader_failure`, `kvm_hard_patroni_failure`, `kvm_network_partition`, `kvm_quorum_primary_failure` | Manual leader replacement, guarded hard failure, symmetric partition, and DCS-loss safety/recovery
Rocky Linux 9 KVM guests from the configured install ISO | 17 | `kvm_restart_smoke`, `kvm_tls_rotation`, `kvm_etcd_snapshot_restore` | Serial restart smoke with membership/data checks, test-only certificate rotation, and isolated etcd restore

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
  execution-context guardrail, platform-before-blueprint validation ordering,
  destructive cleanup path validation, and PostgreSQL instance-name validation.
- `molecule/timescaledb` validates TimescaleDB installation from both PGDG and
  the Timescale Community repository on Rocky Linux 9 and 10 and Red Hat
  Enterprise Linux 9 and 10 UBI.
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
- `molecule/kvm_patroni_failover` is supplemental manual KVM/libvirt
  coverage using three combined Rocky Linux 9 VMs. It stops the actual Patroni
  primary while retaining etcd quorum, checks the replacement leader and data,
  and verifies that the failed member rejoins. It checks SELinux enforcing and
  etcd and Patroni listeners bind to the configured static private addresses.
  Its KVM-specific `prepare.yml` installs and starts firewalld, assigns the guest test-network
  interface to a dedicated private-cluster zone, and permanently and immediately allows
  only source `192.168.250.0/24` to TCP ports 2379, 2380, 5432, and 8008.
- `molecule/kvm_etcd_quorum` is supplemental manual KVM/libvirt
  coverage using the same three-VM topology. It stops two etcd services, proves
  a client write fails without quorum using a separate probe key, restores both
  members, and verifies the original committed continuity key, membership, and
  actual Patroni leader. The probe request may commit asynchronously after the
  client reports failure and is removed after recovery. It also verifies the
  Patroni private listener. Its KVM-specific `prepare.yml` applies the same
   dedicated-zone firewalld rules before role convergence.
- `molecule/kvm_etcd_leader_failure` stops the discovered etcd leader only,
  then checks leader replacement, key continuity, endpoint health, and rejoin.
  This is an operational DCS smoke test, not a guarantee for every failure mode.
- `molecule/kvm_hard_patroni_failure` uses the guarded host helper
  the shared KVM VM helper to stop exactly the selected guest,
  then starts it again and checks promotion, continuity, and rejoin.
- `molecule/kvm_network_partition` adds a temporary priority reject rule to
  the dedicated `idarsi-private` firewalld zone and always removes it. SSH remains available through the shared test network; a task barrier confirms both host-side rules before disruption
  assertions. This validates guest firewall behavior, not a switch-level or
  perfectly simultaneous packet cut; host scheduling and already-in-flight
  connections remain limitations. Asymmetric packet loss is out of scope. If the
  verifier is interrupted, manually remove the temporary rule on `pg01` and
  `pg02` with `firewall-cmd --zone=idarsi-private --remove-rich-rule="rule family=ipv4 source address=<peer-private-address> priority=-100 reject"` and the same command with `--permanent`, then verify with `--query-rich-rule`; never alter the NAT/SSH zone.
- `molecule/kvm_quorum_primary_failure` combines etcd quorum loss with a
  Patroni primary stop and asserts no unsafe write or promotion before recovery.
- `molecule/kvm_restart_smoke` restarts Patroni serially and checks health,
  three-member membership, one-leader safety, and PostgreSQL data continuity.
  It is not a PostgreSQL major-upgrade test.
- `molecule/kvm_tls_rotation` creates a disposable CA and a distinct leaf
  for each etcd member, with that member's DNS and private IP SANs. It installs
  an old+new trust bundle, rotates one member at a time, and after every
  rotation asserts certificate ownership/mode, effective PostgreSQL read
  access, exactly three Patroni members (one leader and two replicas), and both
  PostgreSQL and DCS continuity markers. It is test-only coverage and does not
  exercise role-managed issuance. Old-CA removal or revocation is not
  implemented or covered; the old CA intentionally remains in the temporary
  trust bundle for this compatibility smoke test.
- `molecule/kvm_etcd_snapshot_restore` restores a live etcd snapshot into a
  fresh disposable directory and cluster identity, never over live data.
  PostgreSQL data is explicitly not restored.
- `molecule/el9-el10-etcd-matrix` validates managed PGDG etcd installation and the
  local etcd and Patroni endpoints on Rocky Linux 9 and 10.
- `molecule/rocky10-baseline` validates the same baseline behavior on Rocky Linux 10.
- `molecule/rhel10-baseline` validates the same baseline behavior on Red Hat Enterprise
  Linux 10 UBI.
- `molecule/fedora43-baseline` and `molecule/fedora44-baseline` validate PostgreSQL 17 and 18
  installations from the Fedora-specific PGDG repository workflow.

The GitHub Actions workflow runs syntax and production-profile lint checks
with Ansible Core 2.20.8. Pull requests and pushes to `main` run a fast
representative Molecule matrix on that line. The complete automated scenario
matrix runs once per day on 2.20.8. The scheduled workflow also runs the
minimum-version and forward-compatibility lanes described above. Molecule jobs
are independent and run in parallel by scenario; static checks do not gate
individual scenario jobs.

The pull-request fast matrix contains `validation`, `rocky9-full`,
`rocky10-baseline`, `rhel10-baseline`, and `fedora44-baseline`. It checks
validation, the primary EL9 path, and representative EL10, RHEL, and Fedora
baselines. The daily matrix runs
all automated scenarios listed in this document, including the older EL and
Fedora baseline images, replication and guardrail scenarios, both TimescaleDB
repository variants, and the multi-member Patroni and etcd scenarios. It
excludes the supplemental manual KVM scenarios.

The pull-request matrix is intentionally a fast regression gate, not the full
coverage promise. Full Molecule coverage is the complete automated scenario
set documented in this file; the scheduled run exercises that set. The
workflow cancels an older in-progress run for the same branch or scheduled
workflow when a newer run starts.

If an interrupted run prevents Molecule's final cleanup, first run
`molecule cleanup -s <scenario>` and then `molecule destroy -s <scenario>`.
For a disruption scenario, manually restore stopped services with
`systemctl start etcd.service patroni-17-main.service postgresql-17-main.service`
as applicable, remove temporary firewalld rules using the commands above, and
remove `/tmp/molecule-etcd.snap`, `/tmp/molecule-restored-etcd.pid`,
`/tmp/molecule-restored-etcd.log`, and any `molecule-etcd-restore-*` directory
on the guest. These are best-effort
operator recovery steps; interrupted verification cannot guarantee automatic
cleanup.

GitHub Actions creates an isolated Python environment. `requirements-ci.txt`
pins Ansible Lint and the Molecule tools; each CI lane supplies its explicit
Ansible Core version. Local runs use the pinned environments from
`idarsi-ansible-test-environments` instead of installing or upgrading packages
in the shared environment.

The KVM scenarios are supplemental manual coverage and are not run in CI. They
require the shared test environment, access to the official Rocky Linux 9 install
tree, libvirt/KVM, and resources for three guests. Static private addresses make
the topology reproducible, but host networking, SELinux policy packages, and
firewall defaults can still vary. These scenarios do not
test host suspend, power loss, split-brain fencing, or a two-node etcd cluster;
they use disposable, one-day, self-signed test certificates and deliberately
insecure fake Patroni/PostgreSQL credentials. These fixtures must never be
used outside disposable test guests. The scenarios assert SELinux enforcing
and required listeners; their KVM-specific prepare playbooks also configure
the guest firewalld rules needed by the private cluster network. Firewalld
remains guest-owned and is not managed or claimed by this role.

The KVM `prepare` playbooks install the signed PGDG repository package and
enable its Rocky Linux 9 extras repository before installing test `etcd`. They
reboot each guest after package setup and wait for Ansible connectivity before
creating certificates or applying role configuration. All guests use the
shared `idarsi-test` NAT network prepared by the test-environment installer;
cluster scenarios assign static addresses `.201` through `.203` outside its
DHCP pool. The playbooks add those addresses to `/etc/hosts` and configure the
guest firewalld zone needed by the cluster tests.

Each KVM scenario uses the Rocky Linux 9 Minimal ISO selected by `install.sh`,
over the shared NAT network. If no ISO is already selected or present in
`/var/lib/libvirt/boot`, the installer asks before downloading the current image
(about 2.76 GB) and verifies its SHA256. No Vagrant installation or
scenario-specific libvirt network setup is needed. Install the test environment
with its KVM profile, activate its Ansible environment, and run a scenario by
name:

```bash
/path/to/idarsi-ansible-test-environments/install.sh kvm ansible-current
source /path/to/idarsi-ansible-test-environments/.venv/ansible-current/bin/activate
molecule test -s kvm_patroni_failover
```

The KVM scenarios use static addresses in a shared subnet, so run one of these
three-guest scenarios at a time on each test host.

## Running tests

Install or update the shared Podman environment using the
`idarsi-ansible-test-environments` repository, then activate the desired
pinned environment before running checks from this role repository:

```bash
cd /path/to/idarsi-ansible-test-environments
./install.sh podman ansible-current
source .venv/ansible-current/bin/activate
cd /path/to/ansible-iac-role-postgresql
ANSIBLE_ROLES_PATH=.. ansible-lint --profile production
ANSIBLE_ROLES_PATH=.. ansible-playbook --syntax-check \
  -i docs/inventory-example.yml docs/playbook-example.yml
molecule test -s rocky9-full
```

Molecule's current releases do not provide Ansible Lint as a built-in
scenario phase, so this is a separate static-analysis gate in the same test
workflow. The repository's `.ansible-lint` file keeps the profile and shared
exclusions in version control.

Run all automated scenarios from the role directory. This excludes the
resource-intensive manual KVM scenarios:

```bash
for scenario in molecule/*; do
    case "${scenario##*/}" in
        kvm_*) continue ;;
    esac
    molecule test -s "${scenario##*/}" || exit 1
done
```

Run the supplemental manual KVM scenarios separately after installing the shared
test environment:

```bash
for scenario in molecule/kvm_*; do
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
molecule test -s kvm_patroni_failover
molecule test -s kvm_etcd_quorum
molecule test -s kvm_etcd_leader_failure
molecule test -s kvm_hard_patroni_failure
molecule test -s kvm_network_partition
molecule test -s kvm_quorum_primary_failure
molecule test -s kvm_restart_smoke
molecule test -s kvm_tls_rotation
molecule test -s kvm_etcd_snapshot_restore
molecule test -s el9-el10-etcd-matrix
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

Known limitation: the guardrail that refuses Patroni reinitialization when
existing data is present but the expected service unit is unknown is not
covered by a Molecule scenario. It depends on the host's live systemd service
fact inventory; the implementation guard remains covered by static review and
the normal Patroni lifecycle scenarios exercise the known-service path.
