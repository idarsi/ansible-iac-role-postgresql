# Maturity assessment

**Repository:** `ansible-iac-role-postgresql`
**Assessed ref:** `update/postgresql-inventory-examples` at task-result HEAD
**Maturity state:** Beta
**RC readiness:** 85% (score-based state Beta; no state cap changes the result)

The score evaluates role implementation, defaults, validation, README,
`TESTING.md`, Molecule scenarios, and CI workflow. It measures engineering
readiness for Release Candidate, not production suitability.

| Category / criterion | Max | Awarded | Evidence and remaining gap |
| --- | ---: | ---: | --- |
| **Scope and public contract** | **12** | **10** | |
| Purpose and boundaries | 3 | 3 | README identifies ownership and exclusions. |
| Inputs and states | 5 | 4 | Validation covers key input types and constraints; the extensive input surface is not fully catalogued in README. |
| Support contract | 4 | 3 | OS, PostgreSQL, Ansible, collections, and test matrix are documented; EL8 has no automated coverage. |
| **Functional completeness** | **20** | **17** | |
| Core convergence | 8 | 7 | Installation, resources, replication, Patroni, and managed etcd are implemented and tested; not every feature combination is covered. |
| Applicable lifecycle | 6 | 5 | Lifecycle/resource states exist; transition evidence is not exhaustive. |
| Platform and dependency handling | 3 | 3 | EL/Fedora repository paths and dependencies are implemented and matrix-covered for automated targets. |
| Failure and rerun behavior | 3 | 2 | Recovery and cluster scenarios exist; some host-specific failures remain uncovered. |
| **Validation and safety** | **20** | **17** | |
| Preflight validation | 6 | 5 | Complete inventory preflight checks types, values, references, and conflicts; some fields rely on broad assertions. |
| Secure behavior | 6 | 5 | TLS and security-sensitive cluster guards exist; secret handling across all paths lacks full automated evidence. |
| Destructive guardrails | 5 | 5 | Cleanup paths/ownership markers and explicit reinitialization opt-in are guarded. |
| Check and diff behavior | 3 | 2 | Module-based convergence is present, but comprehensive check/diff behavior is not tested. |
| **Convergence and recovery** | **13** | **11** | |
| Idempotent convergence | 5 | 4 | Representative baseline and cluster reruns are covered, not every state/platform combination. |
| State transitions | 4 | 3 | Removal, restart, replication, and membership transitions have partial coverage. |
| Operational recovery | 4 | 4 | Failover, quorum, restart, and interruption recovery are documented and exercised. |
| **Automated testing and CI** | **25** | **21** | |
| Static quality checks | 3 | 3 | CI runs syntax and production-profile Ansible Lint. |
| Input validation tests | 4 | 4 | Validation scenario tests valid/invalid inputs and failures without package install. |
| Functional verification | 6 | 5 | Broad outcome coverage; not every public feature has equivalent integration coverage. |
| Idempotence tests | 4 | 3 | Representative paths check reruns; coverage is not universal. |
| Lifecycle and guardrail tests | 4 | 4 | Cleanup, bind/HBA guardrails, membership, and failures are covered. |
| Supported-platform matrix | 3 | 2 | Rocky/RHEL 9/10 and Fedora 43/44 are covered; EL8 is not automated. |
| CI enforcement | 1 | 0 | Workflow exists, but required branch protection is not evidenced in-repository. |
| **Documentation and release hygiene** | **10** | **9** | |
| Operator documentation | 4 | 4 | README and topology examples document scope, states, requirements, and safe secret references. |
| Test and limitation documentation | 2 | 2 | `TESTING.md` describes coverage, commands, boundaries, and known gaps. |
| Contribution contract | 2 | 2 | `CONTRIBUTING.md` synchronizes validation, examples, tests, and docs. |
| Repository and release metadata | 2 | 1 | License and compatibility/dependency information exist; release history and maintenance policy are not fully evidenced. |
| **Total** | **100** | **85** | |

The score maps to **Beta**. No mandatory state cap lowers it: the role has
executable functionality, meaningful automated functional tests, and
representative idempotence evidence. It is not an RC: readiness is below 100%,
and independent production review is not established.

## Smallest readiness improvements

- Add automated EL8 evidence or narrow the support claim.
- Establish and record required CI/branch-protection enforcement.
- Expand check/diff, state-transition, and security-sensitive secret-path tests.
- Document the complete public schema and record release/compatibility policy
  and maintenance ownership.

The documentation change introduces no runtime behavior. Cluster lifecycle
verification remains part of the existing automated/manual test matrix.
