# Testing

## Declared scope versus runtime evidence

The repository contains **25 whole-scenario managed declarations**, migrated
from 29 historical scenarios. This is not a validation-only suite. Scenarios
cover installation, versions, filesystem binds, removal, replication, Patroni,
etcd, TLS, recovery and negative guardrails. They remain ordinary role-owned
Molecule scenarios; the TUI is optional.

**Declarations are not runtime proof.** The ledger below records five independent
tester acceptance selections with source/controller qualifications. It does not
establish a full 25-scenario or supported OS/controller-matrix pass. No GitHub CI
pass or required-check enforcement is established by configuring a workflow.
Historical privileged-container/shared-network tests do not prove replacements.

The historical source remains available at
`45f3547681387dda4b0609bc81eda8703b218153`. The mapping below preserves every
test purpose and OS-specific assertion; consolidation does not remove the
separate Rocky/RHEL/Fedora playbooks. Unexecuted replacements retain declared
coverage intent, not acceptance inferred from the historical tests.

### Read-only verification evidence (2026-11-24)

Tested source was the current branch at role base `45f3547` **plus dirty
changes**, with helper base `9c2cabe` **plus dirty changes**. Neither is a
new committed migration revision. The tester's bounded read-only harness
(`postgresql-readonly-check.py`) recorded the TimescaleDB recheck in artifact
`postgresql-current-timescaledb-recheck-readonly-results.json`; local paths and
logs are intentionally not stored here.

| Check | Observed result |
| --- | --- |
| Current controller capabilities + resolve | 24/25 PASS; `kvm-baseline` BLOCKED by missing Fedora 43 image |
| Effective configuration bindings | All 25 PASS |
| TimescaleDB current-controller recheck | PASS: capabilities, resolve, effective configuration and complete eight-name metadata topology; original source selections preserved |
| Next controller representative probes | PASS: `podman-validation`, `kvm-replication`, `kvm-hard-patroni-failure` |

These are configuration/capability results only. The separate runtime evidence
below must not be borrowed to label other scenarios or controller lanes PASS.

### Runtime acceptance ledger (2026-11-24)

All five selections used Ansible Core **2.20.8**, Molecule **26.8.0**, and role
base `45f3547681387dda4b0609bc81eda8703b218153` **plus dirty tested changes**.
They do not attest a subsequent documentation or role commit. The first four
used clean local helper `f9f0b7bd1af671035eb5e6fb5959826392acac4f`.
The hard-failure selection instead used that helper **plus a dirty normalizer
fix**; it is explicitly not a clean-`f9f0…` hard-failure pass.

| Selection | Independent tester result |
| --- | --- |
| Direct `podman-validation` full test sequence | PASS: 617 tasks, idempotence changed=0, verify and destroy |
| Direct `kvm-replication` retained phases | PASS: dependency/create/prepare/converge/idempotence/verify/destroy all exit 0; SQL row, slots, streaming, PL/Python and service assertions; changed=0 on both guests |
| Managed CLI `podman-validation` | PASS: campaign 322, origin `cli`, observed worker exit 0 |
| Actual GUI whole `kvm-replication` | PASS: unmodified `RoleTestApp` through Textual Pilot, complete two-host selection; campaign 323, origin `tui_gui`, worker exit 0, idempotence/SQL/verify |
| Native three-ISO-VM supervised `kvm-hard-patroni-failure` | PASS with dirty helper fix: create/prepare/converge, changed=0 idempotence on all three, verify and destroy; pg01 owned poweroff changed=true/shut-off, pg03 promotion, pg01 owned restart changed=true/running with the same UUID, replica rejoin and both before/after SQL markers |

The actual GUI used clean TUI revision
`2b6e1fd54bb9f3d0be8bc4f148396aa543679416`. All five selections had fresh
authoritative `cleaned` evidence. The managed CLI/GUI sessions exited and
admission was clear. For hard failure, create/guest-stop/guest-start/destroy
operations were sealed, all eight journalled sessions were gone, and cleanup
needed neither recovery nor sudo.

The successful hard-failure source is additionally bound by these SHA-256 hashes:

| Dirty tested file | SHA-256 |
| --- | --- |
| Role `molecule/kvm-hard-patroni-failure/verify.yml` | `13d4bd7ecfb9876f64f388fd7e748ea0c0fef3add55746b1ee57a6bb6547934e` |
| Role `molecule/kvm-hard-patroni-failure/helper_result.yml` | `96cb8618d148bcdd8b659e7d105a6f6e728d294a856a3bef911d99740d0a9870` |
| Helper guest-control normalizer | `c948843e33dfb78d6eae6328bbaac65fe91a2e7dffd8ea4f6a081c6720f4c998` |

That tested normalizer code is now recorded unchanged in reviewed local helper
follow-up commit `aa0e2a7677f66e9b00658ec3d655243634f654a0`, parent `f9f0…`,
and the role pins that commit. This does not relabel the hard-failure run as
execution at the later commit SHA; its actual producing source remains the
dirty helper qualification above. The helper checkout is clean and not pushed.

Earlier environment-binding, private-Galaxy-discovery and typed-YAML assertion
failures were corrected before these passes; failed role pilots either allocated
nothing or completed sealed normal cleanup. An earlier hard-failure attempt
exposed the helper normalizer mismatch before guest-stop mutation and also
completed sealed cleanup. Separately, the historical retained helper network
was cleaned by approved rootless, bounded normal-libvirt reconciliation; its
original destroy remains unsealed, not retroactively PASS. None of these cleanup
claims establishes universal firewall cleanliness.

**Not verified:** the complete 25-scenario suite, full OS/controller matrix,
hosted GitHub CI/enforcement, or remote helper publication. Fedora 43 baseline
remains BLOCKED by missing media. Remaining scenarios, including the six-VM
external-DCS cases, are optional future qualification, not completed acceptance.
The helper follow-up commit is now pinned; publication/CI evidence remains absent.
Raw logs, private paths and generated credentials are not stored here.

## Approved controller and helper prerequisites

Use the existing environments from
[idarsi-ansible-test-environments](https://github.com/idarsi/idarsi-ansible-test-environments).
Do not create a role-local `.venv`, install into shared controllers, upgrade
pins, or reconfigure the host to make a role check pass. Initialize the existing
`tasks/shared` submodule at the recorded gitlink; do not update it.

The reviewed helper revision in
[`tests/helper-revision.txt`](tests/helper-revision.txt) is local commit
`aa0e2a7677f66e9b00658ec3d655243634f654a0`, including the tested normalizer
fix. Operators need this exact compatible checkout; its remote publication
remains unverified. Earlier passes retain their actual `f9f0…` clean/dirty
runtime qualifications above rather than claiming a rerun at the new commit.
All scenarios require
`idarsi.scenario-context/v1`, validated effective configuration and both
`direct` and `supervised` lifecycle modes. The hard-poweroff test additionally
requires the advertised `guest-stop` and `guest-start` actions.

Both local rootless Podman discovery and local `qemu:///system` libvirt discovery
must succeed, even for validation. Remote/rootful Podman, guessed guest names,
host-wide purges, raw virsh substitutions and manufactured handoff variables are
unsupported. Host package/service/storage/network preparation is an operator
prerequisite, not a role action. Follow the shared
[dual-mode lifecycle and recovery contract](https://github.com/idarsi/idarsi-ansible-test-environments/blob/main/docs/isolated-test-runs.md).

| Lane | Current pin / intent | Declaration |
| --- | --- | --- |
| `ansible-min` | Core 2.15, Python 3.9 | Unsupported: below role minimum Core 2.19.12 |
| `ansible-current` | Core 2.20.8 | Five representative runtime selections PASS above; remaining matrix unverified |
| `ansible-next` | Core 2.21.3 | Representative capability probes PASS only; workload matrix unverified, not adopted support |

`min_ansible_core: "2.19"` is the metadata format's major/minor gate; the actual
role prerequisite remains **2.19.12**, not 2.19.0. There is no supported
minimum-controller runtime claim from the shared `ansible-min` lane. Historical
Core 2.15-specific collection manifests are retained only as historical fixtures,
not an invitation to bypass the minimum.

## KVM images and topology

All full-host/systemd/mount/firewall scenarios use the shared native KVM
lifecycle, never relabelled privileged containers. Prepare existing qcow2 images
separately using the shared environment's documented image preparation workflow.
Managed runs do not build bases, register RHEL subscriptions, or modify bases.

Export the image variables needed by the selected whole scenario:

| Variable | Required prepared guest |
| --- | --- |
| `IDARSI_TEST_KVM_ROCKY9_IMAGE` | Rocky Linux 9 |
| `IDARSI_TEST_KVM_ROCKY10_IMAGE` | Rocky Linux 10 |
| `IDARSI_TEST_KVM_RHEL9_IMAGE` | RHEL 9 with authorized working repositories |
| `IDARSI_TEST_KVM_RHEL10_IMAGE` | RHEL 10.2 with authorized working repositories |
| `IDARSI_TEST_KVM_FEDORA43_IMAGE` | Fedora 43 |
| `IDARSI_TEST_KVM_FEDORA44_IMAGE` | Fedora 44 |

The nine former `kvm_*` combined-cluster scenarios retain their native
installation-source workflow instead of requiring a prepared base image:
export `IDARSI_TEST_KVM_INSTALL_SOURCE` to an existing compatible Rocky 9
installation source. Their shared kickstart template is supplied by the pinned
helper. The managed adapter installs owned guests directly; it does not invoke
the legacy shared base builder. Do not download or build media during a run.

Images need NetworkManager, Python, an SSH `molecule` user with passwordless
sudo, and working distribution repositories. The guest preparation installs
test-only utilities from those repositories. Fedora images need Python's
distribution DNF bindings, as the former Dockerfiles did. RHEL content access
and availability of the selected PGDG release are prerequisites; full RHEL
VM behavior is not inferred from earlier UBI evidence. RHEL 10.2 preserves the
historical PGDG metadata constraint; do not silently substitute another release.

Native helper inventory supplies connection addresses and ownership. Guest
`/etc/hosts`, etcd endpoints, SANs and firewall fixtures use generated context,
not a host-shared subnet or static connection overrides. Replication uses the
primary VM's private address on port 5432, not a host-published Podman port.
Logical inventory names remain stable. Every metadata lane contains the whole
topology; never filter a cluster or platform matrix with `--platform-name`.

Read-only prerequisite review found prepared readable Rocky 9/10, RHEL 9/10
and Fedora 44 sources, working local rootless Podman/system-libvirt discovery,
KVM access and writable test storage, with SELinux enforcing. This is
prerequisite evidence only, not a create/service pass. **Fedora 43 runtime is
BLOCKED** because no prepared image or installation medium was found in the
documented locations; its support declaration is not silently removed. RHEL
guest repository readiness, media provenance and actual create permissions
remain runtime-unverified.

The host uses active modular libvirt sockets. A legacy setup check expecting
monolithic `libvirtd` can report a false failure; do not reconfigure the host
to satisfy it. Locate existing images using the shared bounded
`kvm-base-image find` workflow only, without autobuild/download. Serialize
qualification: external-DCS scenarios declare 18 GiB / 12 vCPUs each and the
TimescaleDB topology has eight guests. Capacity is not guaranteed by metadata
or by the helper.

## Complete scenario and migration matrix

PG coverage remains 16/17/18 for Rocky/RHEL baselines, 17/18 on Fedora, and the
existing scenario-specific 17/18 checks for etcd and extensions.

| Managed scenario | Historical scenario(s) | Preserved topology and purpose |
| --- | --- | --- |
| `podman-validation` | `validation` | One nonprivileged Rocky 9 container, sleep command; all valid/invalid blueprint and non-mutation assertions |
| `kvm-full` | `rocky9-full`, `rhel9-full` | Two OS guests, independent OS-specific full installation/binds/git/SQL/security assertions |
| `kvm-baseline` | `rocky10-baseline`, `rhel10-baseline`, `fedora43-baseline`, `fedora44-baseline` | Four OS guests with their original distinct baseline assertions |
| `kvm-all-absent` | `all_absent` | One Rocky 9 guest, install fixture then guarded removal, repeated cleanup and preservation assertions |
| `kvm-bind-guardrails` | `bind_guardrails` | One guest, data conflict and active-service migration failures |
| `kvm-hba-guardrails` | `hba_guardrails` | One guest, exact address/CA/map validation failures |
| `kvm-replication` | `replication` | Two guests, real primary/standby bootstrap and data visibility |
| `kvm-timescaledb` | `timescaledb` | Eight guests: PGDG/community sources on Rocky/RHEL 9/10 |
| `kvm-patroni-config` | `patroni_config` | One guest, rendering, repeated convergence and check/diff file non-mutation |
| `kvm-patroni-unknown-service` | `patroni_unknown_service` | One guest, exact pre-existing-data service guardrail and non-mutation |
| `kvm-patroni-membership` | `patroni_membership` | Three external-DCS guests plus three PG guests; member removal/rejoin and finalization |
| `kvm-patroni-failover` | `patroni_failover` | Three external-DCS guests plus three PG guests; quorum, leader replacement, rejoin and continuity |
| `kvm-etcd-cluster` | `rocky9-etcd-cluster` | Three combined etcd/PG guests, TLS, quorum, Patroni failover and PG18 smoke |
| `kvm-etcd-tls-member` | `rocky9-etcd-tls-member` | One combined guest, auto-generated etcd TLS and PG18 smoke |
| `kvm-etcd-tls-cluster` | `rocky9-etcd-tls-cluster` | Three combined guests, shared TLS and quorum recovery |
| `kvm-etcd-platform-matrix` | `el9-el10-etcd-matrix` | Two Rocky 9/10 guests, PGDG etcd/service and PG18 coverage |
| `kvm-combined-patroni-failover` | `kvm_patroni_failover` | Three combined Rocky 9 guests, Patroni failover |
| `kvm-etcd-quorum` | `kvm_etcd_quorum` | Three combined guests, quorum loss/recovery |
| `kvm-etcd-leader-failure` | `kvm_etcd_leader_failure` | Three combined guests, live etcd leader replacement |
| `kvm-hard-patroni-failure` | `kvm_hard_patroni_failure` | Three combined guests, ownership-checked abrupt live-primary poweroff/start, SSH/rejoin and both continuity markers |
| `kvm-network-partition` | `kvm_network_partition` | Three combined guests, symmetric guest firewall partition/recovery |
| `kvm-quorum-primary-failure` | `kvm_quorum_primary_failure` | Three combined guests, DCS-loss primary safety/recovery |
| `kvm-restart-smoke` | `kvm_restart_smoke` | Three combined guests, serial restart, membership and data |
| `kvm-tls-rotation` | `kvm_tls_rotation` | Three combined guests, certificate rotation and continuity |
| `kvm-etcd-snapshot-restore` | `kvm_etcd_snapshot_restore` | Three combined guests, isolated snapshot restore and data assertions |

Guardrail failure exercises are in verify rather than being repeated as
convergence. Their validation-only converge is not claimed as mutating
idempotence evidence. Removal fixtures are installed during prepare; normal
converge remains repeatable. Stateful disruptions and transient membership
selection belong to verify, not an idempotence rerun.

## Private dependencies and failure-closed context

Every scenario calls [`tests/dependency.py`](tests/dependency.py) through
Molecule's shell dependency plugin with these explicit effective-config arguments:

```text
python3 "${MOLECULE_PROJECT_DIRECTORY}/tests/dependency.py"
  --scenario-directory "${MOLECULE_SCENARIO_DIRECTORY}"
  --ephemeral-directory "${MOLECULE_EPHEMERAL_DIRECTORY}"
  --molecule-file "${MOLECULE_FILE}"
  --env-file "${MOLECULE_ENV_FILE}"
  --helper-directory "${IDARSI_TEST_ENVIRONMENT}"
```

The YAML folded command is one invocation. The installed shell plugin does not
export Molecule's computed environment to its subprocess; the bootstrap must
not assume those keys are already exported. It validates scenario ownership and
canonical metadata, rejects conflicting inherited bindings, and passes only the
explicit matching Molecule/helper bindings to the resolver. Genuine
`IDARSI_RUN_ID`/`IDARSI_HANDOFF*` values are inherited unchanged, never manufactured.
The returned ephemeral directory must match the explicit effective directory.
This also preserves nondefault `--env-file` and retained-phase contexts without
a wrapper or a guessed cache path.

Allocation-free regression tests exercise the installed Molecule dependency
subprocess under the existing current and next controllers, using a fake
resolve-only helper and fake Galaxy installer in an isolated scaffold. They
cover missing computed environment, retained/custom env-file bindings and
partial-handoff rejection. This is subprocess-contract evidence, not a native
backend, collection-installation or PostgreSQL lifecycle pass.

It calls `scenario-context resolve` (not
`init`) before installation, validates the returned contract and destination,
and installs role-owned manifests under the resolved private collections
directory with an installation lock. Common pins are in
[`tests/collections.yml`](tests/collections.yml); scenario-specific manifests
remain in their scenario directories. Nothing is installed into a shared venv.
Galaxy's child environment sets `ANSIBLE_COLLECTIONS_PATH` to **only** the
resolved private destination and `ANSIBLE_COLLECTIONS_SCAN_SYS_PATH=false`;
the obsolete plural path alias is removed. It never appends shared search
roots. Role-owned manifests use exact FQCN/version pins. While retaining the
installation lock, bootstrap verifies regular, non-symlink `MANIFEST.json` and
`FILES.json` beneath the physical private collection directory and checks its
namespace, name and version. A successful Galaxy no-op is not installation proof.

An offline real-Galaxy regression builds a tiny local fixture archive entirely
in temporary storage. An exact version already installed in a separate external
search root reproduces the old `-p`-only no-op; the isolated child environment
must physically install it privately, and a repeat must retain that installation.
No role dependencies are fetched and no shared controller is modified.

Keep the exact effective safe-files glob
`${MOLECULE_EPHEMERAL_DIRECTORY}/collections/*`. It prevents Molecule's
post-destroy pruning from deleting private dependencies. Partial/invalid
`IDARSI_RUN_ID` or `IDARSI_HANDOFF*` context must reject before mutation; never
fall back to direct mode. The execution context is not public `iac_blueprint`.

## Direct operation without the TUI

From the role root, with portable checkout paths and already prepared images:

```sh
export IDARSI_TEST_ENVIRONMENT="/path/to/idarsi-ansible-test-environments"
source "$IDARSI_TEST_ENVIRONMENT/.venv/ansible-current/bin/activate"
git submodule update --init --recursive

# Read-only effective-configuration checks; not backend lifecycle acceptance.
"$IDARSI_TEST_ENVIRONMENT/scripts/scenario-context" capabilities \
  --backend kvm --scenario kvm-replication --role "$PWD"
"$IDARSI_TEST_ENVIRONMENT/scripts/scenario-context" resolve \
  --backend kvm --scenario kvm-replication --role "$PWD"

molecule test -s kvm-replication
# Or retain guests between ordinary separate commands, stopping on failure:
molecule create -s kvm-replication &&
molecule prepare -s kvm-replication &&
molecule converge -s kvm-replication &&
molecule verify -s kvm-replication &&
molecule destroy -s kvm-replication
```

Use any scenario above with its image prerequisites. Direct create/converge/
verify/destroy do not require the TUI or supervisor wrapper. Direct context
identity includes the canonical role checkout, scenario, backend and effective
ephemeral directory. Same-context direct concurrency is unsupported.
Standalone `create` does not imply the `prepare` phase has run: for fixture-heavy
scenarios, explicitly run `molecule prepare -s SCENARIO` between create and
converge, as Molecule's ordinary phase model requires. `molecule test` runs it
automatically. Separate-phase acceptance must include that prerequisite rather
than weakening or skipping fixture assertions.

## Optional supervised CLI and TUI

```sh
"$IDARSI_TEST_ENVIRONMENT/scripts/test-run" run \
  --backend kvm --scenario kvm-replication "$PWD"
```

Use the existing TUI environment for explicit matrix selection:

```sh
idarsi-tests-run list --role postgresql --roles-dir "$ROLES_DIR" \
  --environment-repository "$IDARSI_TEST_ENVIRONMENT"
idarsi-tests-run plan --role postgresql --roles-dir "$ROLES_DIR" \
  --environment-repository "$IDARSI_TEST_ENVIRONMENT" \
  --cell kvm-replication whole_scenario 'whole scenario' ansible-current
idarsi-tests-run run --role postgresql --roles-dir "$ROLES_DIR" \
  --environment-repository "$IDARSI_TEST_ENVIRONMENT" \
  --cell kvm-replication whole_scenario 'whole scenario' ansible-current \
  --expect-sha FULL_APPROVED_COMMIT_SHA --yes
```

In the GUI, Space selects the exact scenario/lane, `r` previews, `y` confirms.
Planning, lack of a lock icon, or an apparent worker exit is not execution or
cleanup proof. Record actual GUI-origin campaign/cell evidence separately from
CLI-origin results. The supervisor executes the whole scenario once.

## Verification ownership, CI and recovery

Developers run only cheap YAML/JSON parsing, focused unit/contract/syntax checks
and `git diff --check` using existing tools. The tester owns infrastructure,
full tests, separate phases, negative handoff probes, idempotence, supported
controller/OS coverage, cancellation/concurrency, supervised CLI and actual GUI
acceptance. Report exact commands and results and do not repeat passing developer
checks unless code changed or independent reproduction is needed.

Python static typing and dedicated Python security analysis of
`tests/dependency.py` remain **unverified**. Focused unit, syntax and formatting
checks do not establish complete Python acceptance; no missing tools were
installed to perform these checks.

CI static checks run on proposed changes. Managed runtime jobs require prepared
self-hosted runners, both backend discovery permissions, existing pinned
controllers, exact compatible helper and prepared images. The workflow must not
pretend that an Ubuntu runner with Podman alone can exercise full KVM tests.
Configured fast/daily/forward-compatibility intent is not an executed CI pass;
the remaining workload/platform matrix is unverified and Fedora 43 is blocked.
The `idarsi-managed-tests` GitHub environment must have operator approval and
appropriate protection before self-hosted execution; fork PRs do not run that
job. The two controller lanes are serialized. Runner registration, environment
protection and required-check enforcement are operator configuration, not
established evidence from this source change.

Only fresh original-context authoritative `cleaned` inspection establishes
cleanup. Preserve journals and leases after incomplete mutations, including
failed guest control; do not use raw virsh, guessed physical names, force-unlock,
delete state, or purge host resources. Recovery can legitimately be inspection
only. Consult the shared contract and escalate instead of inventing a workaround.
The known production limitations in the
[maturity evidence note](docs/maturity-evidence.md) are outside this migration.
