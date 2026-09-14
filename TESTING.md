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
Rocky Linux 9 UBI               | 16, 17, 18          | `rocky9-full`, `all_absent`, `bind_guardrails`, `hba_guardrails`, `replication`, `timescaledb`, `validation`, `patroni_config`, `patroni_failover`, `patroni_membership`, `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Full baseline, cleanup, guardrails, physical replication, inventory validation, TimescaleDB sources, Patroni membership, failover, and managed etcd
Red Hat Enterprise Linux 9 UBI | 16, 17, 18          | `rhel9-full`             | Full baseline, bind, git, and repository workflow
Rocky Linux 10 UBI              | 16, 17, 18          | `rocky10-baseline`           | Baseline installation and multi-version coverage
Red Hat Enterprise Linux 10 UBI| 16, 17, 18          | `rhel10-baseline`            | Baseline installation and multi-version coverage
Fedora 43                       | 17, 18               | `fedora43-baseline`          | PGDG repository and baseline installation
Fedora 44                       | 17, 18               | `fedora44-baseline`          | PGDG repository and baseline installation
Rocky Linux 9 UBI               | 17, 18               | `rocky9-etcd-cluster`, `rocky9-etcd-tls-member`, `rocky9-etcd-tls-cluster` | Managed three-member etcd, quorum recovery, Patroni failover, TLS etcd, and PostgreSQL 18 smoke coverage
Rocky Linux 8/10 UBI            | 17, 18               | `el8-el10-etcd-matrix`    | Managed etcd package and service coverage across EL8 and EL10 with PostgreSQL 18 smoke coverage

The coverage target is PostgreSQL 17 and 18 on Fedora, and PostgreSQL 16, 17,
and 18 on the longer-lived Rocky Linux and RHEL platforms. The Rocky Linux 8
and RHEL 8 baseline scenarios currently cover PostgreSQL 17 and 18, while the
Rocky Linux 9 and 10 and RHEL 9 and 10 scenarios cover PostgreSQL 16, 17, and
18.

The following scenarios are supplemental manual coverage and are not part of
the automated Molecule matrix or CI:

Platform/image                  | Ansible or application versions | Molecule scenarios | Main coverage
--------------------------------|---------------------|--------------------|--------------
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_patroni_failover`, `vagrant_etcd_quorum` | Three combined systemd VMs, static private endpoints, Patroni failover, and etcd quorum loss/recovery
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_etcd_leader_failure`, `vagrant_hard_patroni_failure`, `vagrant_network_partition`, `vagrant_quorum_primary_failure` | Manual leader replacement, guarded hard failure, symmetric partition, and DCS-loss safety/recovery
Rocky Linux 9 Vagrant box `generic/rocky9` 4.3.12 | 17 | `vagrant_restart_smoke`, `vagrant_tls_rotation`, `vagrant_etcd_snapshot_restore` | Serial restart smoke with membership/data checks, test-only certificate rotation, and isolated etcd restore

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
- `molecule/vagrant_patroni_failover` is supplemental manual Vagrant/libvirt
  coverage using three combined Rocky Linux 9 VMs. It stops the actual Patroni
  primary while retaining etcd quorum, checks the replacement leader and data,
  and verifies that the failed member rejoins. It checks SELinux enforcing and
  etcd and Patroni listeners bind to the configured static private addresses.
  Its Vagrant-only `prepare.yml` installs and starts firewalld, assigns `eth1`
  to a dedicated private-cluster zone, and permanently and immediately allows
  only source `192.168.250.0/24` to TCP ports 2379, 2380, 5432, and 8008.
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

The fast matrix contains `validation`, `rocky9-full`, `all_absent`,
`patroni_config`, `rocky10-baseline`, `rhel10-baseline`, and
`fedora44-baseline`. The daily matrix runs
all automated scenarios listed in this document, including the older EL and
Fedora baseline images, replication and guardrail scenarios, both TimescaleDB
repository variants, and the multi-member Patroni and etcd scenarios. It
excludes the supplemental manual Vagrant scenarios.

The workflow cancels an older in-progress run for the same branch or scheduled
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

The CI workflow installs the exact Ansible Core, ansible-lint, Molecule, and
molecule-plugins versions defined in `requirements-ci.txt` in its isolated
Python environment. The shared local environment must not be modified to
match these pins. Check for a version mismatch first and report it instead of
installing or upgrading packages.

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

Molecule's current releases do not provide Ansible Lint as a built-in
scenario phase, so this is a separate static-analysis gate in the same test
workflow. The repository's `.ansible-lint` file keeps the profile and shared
exclusions in version control.

Run all automated scenarios from the role directory. This excludes the
resource-intensive manual Vagrant scenarios:

```bash
for scenario in molecule/*; do
    case "${scenario##*/}" in
        vagrant_*) continue ;;
    esac
    molecule test -s "${scenario##*/}" || exit 1
done
```

Run the supplemental manual Vagrant scenarios separately, only when Vagrant,
libvirt/KVM, and the required guest networking are available:

```bash
for scenario in molecule/vagrant_*; do
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
