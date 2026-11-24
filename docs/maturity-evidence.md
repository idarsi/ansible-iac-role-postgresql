# Maturity evidence and migration limits

Assessment boundary: role source at
`45f3547681387dda4b0609bc81eda8703b218153`, before the managed-test migration.
The README's **Beta / 86%** is historical project metadata. Its underlying
criterion scorecard was not available in the repository; this migration does
not substantiate it, replace it, or silently infer regression.

A separate read-only reconstruction using the current Idarsi maturity rubric
reported the following category totals:

| Category | Reconstruction / maximum |
| --- | --- |
| Scope and public contract | 7.5 / 12 |
| Functional completeness | 15.5 / 20 |
| Validation and safety | 7.5 / 20 |
| Convergence and recovery | 6.5 / 13 |
| Automated testing and CI | 21 / 25 |
| Documentation and release hygiene | 7 / 10 |
| **Total (rounded down)** | **65 / 100** |

This is an independent reconstruction with a different evidence basis, **not
an accepted replacement for the historical 86%**. Without the historical
criterion-level assessment, the numbers are not a comparable before/after
series. No changed production evidence justifies altering the published score
as part of this test-integration task.

Beta remains the applicable ceiling because materially distinct support paths
lack current independent runtime acceptance. Migration declarations, static
checks, scenario counts and configured CI are not lifecycle, platform,
idempotence, supervised CLI or actual GUI execution evidence.

Read-only review also identified out-of-scope production limitations: uninstall
cleanup can bypass complete preflight, secret-bearing derived facts need review,
and replication password changes can be hidden by convergence reporting.
These are not repaired by the test migration and prevent an RC claim pending
separate safety review and remediation. Production behavior and the
`tasks/shared` gitlink are intentionally unchanged.

## Post-implementation update (2026-11-24)

The independent assessor retained **66% / Beta** for role base `45f3547` plus
dirty migration changes. The only scoring change from the explicit pre-migration
65% table above is test/limitation documentation **1/2 → 2/2**: documentation
and release hygiene rises from 7/10 to 8/10. All other category totals are
unchanged. This does not replace or substantiate the historical README 86%.

Independent testing now records direct validation and retained PostgreSQL
replication passes, managed CLI validation, actual GUI whole-topology
replication, and native supervised hard-primary failure/rejoin. Their exact
dirty-source qualifications, helper normalizer hash, representative idempotence
and authoritative cleanup are in the [runtime ledger](../TESTING.md#runtime-acceptance-ledger-2026-11-24).
The hard-failure pass used a dirty helper fix, not clean `f9f0…`. Its unchanged
tested normalizer code is now recorded in reviewed local follow-up commit
`aa0e2a7677f66e9b00658ec3d655243634f654a0` and pinned by the role; this
does not rewrite the producing dirty-source qualification. These results are
not passes at a later documentation/role commit or of the complete 25-scenario
OS/controller matrix.

Beta and the score remain unchanged after those runtime results. Fedora 43 is
blocked by missing media; other unexecuted scenarios and compatibility paths,
remote helper publication and hosted CI enforcement remain unverified.
Representative changed=0 idempotence does **not** resolve the existing hidden
replication-password convergence limitation. The uninstall preflight and
secret-bearing-fact findings above are likewise unchanged and out of scope.
No production fix or RC promotion is claimed. Future qualification and a
separate production-safety task remain distinct work.
