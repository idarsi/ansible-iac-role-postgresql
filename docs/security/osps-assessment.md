# OpenSSF OSPS Baseline Level 1 self-assessment

> Self-assessment, not independent audit or certification. This is not a compliance claim.

- **Baseline:** OSPS 2026.02.19 ([official source](https://baseline.openssf.org/versions/2026-02-19.html))
- **Project / repository URL:** https://github.com/idarsi/ansible-iac-role-postgresql
- **Assessment scope:** This role repository, its GitHub-hosted CI, and the `idarsi/ansible-iac-shared-tasks` source submodule, which is a constituent runtime codebase: its task implementations are checked out under `tasks/shared` and invoked by this role. Whether either codebase is compiled into or included in separate released assets is unknown; hosted release assets were not inspectable. OSPS-QA-04.01 is therefore assessed as applicable because this project uses multiple codebases, irrespective of whether compiled/release assets exist. Targets are GitHub organization/repository settings; Actions/runners/test infrastructure; source/dependencies/distribution; documentation/maintenance.
- **Assessed commit:** `8345b764f8b9a45bfef24c2a07eac02e295817e6` (2026-10-21)
- **Local modifications:** baseline was clean at the assessed commit. Both this OSPS report and the README maturity-summary update are assessment-time modifications and were not used as evidence for OSPS controls.
- **Assessment date:** 2026-10-31
- **Methods:** Read-only checkout review of README, CONTRIBUTING, LICENSE, workflow, dependency/collection declarations, submodule metadata and checkout, tracked files, tags, and git history; `git status`, `git ls-tree`, `git submodule status`, and tracked-file enumeration. Public hosted settings/API, workflow run logs, organization policies and full release metadata were not available to inspect. No settings, secrets, runners, or systems were changed.
- **Visibility limitations:** Local checkout only. GitHub private settings, enforcement, access controls, API responses, and effective runner/secret permissions cannot be inferred from workflow YAML. Public listing/HTTP availability was not independently verified in this environment.

Statuses: **Met**, **Unmet**, **Unverified**, or justified **Not applicable**. Catalog wording and official upstream explanatory recommendations are distinguished below; additional remediation suggestions are Idarsi advice, not additional OSPS requirements.

## Requirement results

### OSPS-AC-01.01 — MFA for sensitive repository access
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** The requirement concerns VCS access, not PostgreSQL/Linux user MFA. Checkout evidence cannot show MFA enforcement.
- **Evidence:** Repository remote is GitHub (`git remote -v`); no organization settings/API evidence available, assessed 2026-10-31 at the commit above.
- **Necessary remediation:** Authorized maintainer to verify effective MFA enforcement for all relevant sensitive-resource access; record scoped evidence.

### OSPS-AC-02.01 — least-privilege collaborator assignment
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** No evidence of collaborator invitation defaults or manual permission assignment in source.
- **Evidence:** Repository checkout and workflow inspected; effective GitHub settings unavailable.
- **Necessary remediation:** Verify collaborator grant flow/default privileges with authorized settings access.

### OSPS-AC-03.01 — prevent direct primary-branch commits
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** Workflow triggers on pull requests and main pushes; this does not establish a restriction preventing direct commits.
- **Evidence:** `.github/workflows/tests.yml`; branch protection/ruleset/API evidence unavailable.
- **Necessary remediation:** Verify effective protection/ruleset prevents direct primary-branch changes.

### OSPS-AC-03.02 — explicit confirmation for primary-branch deletion
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** Local refs do not establish remote branch deletion controls.
- **Evidence:** GitHub protection/ruleset evidence unavailable.
- **Necessary remediation:** Verify deletion is protected or treated as a sensitive, explicitly confirmed operation.

### OSPS-BR-01.01 — sanitize untrusted CI metadata
- **Applicability:** Applicable when pipeline uses untrusted metadata; pull_request workflow does.
- **Status:** Met.
- **Target area:** Actions/runners/test infrastructure.
- **Implementation:** Pull request metadata is used only as GitHub event trigger context; matrix values are fixed literals and the scenario interpolation is from that fixed matrix, not a free-form title/branch/author. No untrusted metadata is passed into shell commands.
- **Evidence:** `.github/workflows/tests.yml` at assessed commit: scenario matrices are enumerated and command uses `${{ matrix.scenario }}`; workflow inputs not present.
- **Necessary remediation:** None evidenced. Upstream recommendation to validate all untrusted metadata is guidance, not a separate requirement.

### OSPS-BR-01.03 — isolate untrusted snapshots from privileged credentials/assets
- **Applicability:** Applicable; pull_request executes role code and tests.
- **Status:** Unverified.
- **Target area:** Actions/runners/test infrastructure.
- **Implementation:** Workflow declares `permissions: contents: read`, uses hosted `ubuntu-latest`, and has no declared secrets; however hosted effective token permissions, repository secrets exposure, runner isolation/cleanup, and external runner configuration are not verifiable from YAML alone.
- **Evidence:** `.github/workflows/tests.yml`; no run details/settings/API evidence. Test runs execute Ansible/Molecule role code and Podman containers; KVM scenarios are not in the shown workflow matrix.
- **Necessary remediation:** Verify effective PR token/secrets permissions and runner trust/cleanup; ensure no privileged assets or internal reachability are exposed.

### OSPS-BR-03.01 — encrypted official project channels
- **Applicability:** Applicable.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Identified project/source links and submodule URL use HTTPS or SSH; no official plaintext URI identified in inspected docs and metadata.
- **Evidence:** `.gitmodules` uses `https://github.com/...`; `README.md` links GitHub and other project pages with HTTPS; repository remote uses SSH. Local-source inspection only; endpoint behavior not probed.
- **Necessary remediation:** None evidenced.

### OSPS-BR-03.02 — authenticated distribution channel
- **Applicability:** Applicable if official distribution channel is provided; version tags exist, but hosted release channel details were not accessible.
- **Status:** Unverified.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** GitHub is the source channel and uses authenticated transport protocols; hosted release assets/tags and distribution protections were not inspected.
- **Evidence:** `git tag --list` shows `v0.1.0`, `v0.1.1`; no release/API evidence. HTTPS/SSH declaration alone does not establish hosted asset authentication.
- **Necessary remediation:** Verify any published release channel and assets use cryptographically authenticated distribution.

### OSPS-BR-07.01 — prevent unencrypted sensitive data in VCS
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** `.gitignore` and ordinary source review cannot establish prevention of accidental secret commits; no current independent secret-scan result was available.
- **Evidence:** Tracked-file inventory and `.gitignore` inspected at assessed commit; no scanning tool/run evidence reviewed. No secret values reproduced.
- **Necessary remediation:** Run and maintain repository secret scanning/prevention appropriate to the VCS; investigate findings without placing secret material in this report.

### OSPS-DO-01.01 — user guides for basic functionality after release
- **Applicability:** Applicable; repository has version tags.
- **Status:** Met.
- **Target area:** Documentation/maintenance.
- **Implementation:** README documents purpose, supported platforms, states, requirements, blueprint shape and examples; TESTING.md documents test scenarios and boundaries.
- **Evidence:** `README.md`, `TESTING.md`, assessed commit; user guidance is present in checked-out source.
- **Necessary remediation:** None evidenced.

### OSPS-DO-02.01 — defect reporting guide after release
- **Applicability:** Applicable; repository has version tags.
- **Status:** Unmet.
- **Target area:** Documentation/maintenance.
- **Implementation:** CONTRIBUTING.md covers contribution/test process but checked-in docs do not explain how users report defects or provide a visible issue-reporting path.
- **Evidence:** `README.md`, `CONTRIBUTING.md`; local docs at assessed commit.
- **Necessary remediation:** Add an explicit defect-reporting guide/path and expectations.

### OSPS-GV-02.01 — public discussion mechanisms while active
- **Applicability:** Applicable; project has recent activity (commit dated 2026-10-21).
- **Status:** Unverified.
- **Target area:** Documentation/maintenance.
- **Implementation:** No discussion channel is identified in inspected source; GitHub discussion/issue feature settings and availability are not established by this checkout.
- **Evidence:** `README.md`, `CONTRIBUTING.md`, repository activity; hosted issue/discussion settings not accessed.
- **Necessary remediation:** Verify and document an accessible public discussion mechanism for proposed changes and usage obstacles.

### OSPS-GV-03.01 — contribution process while active
- **Applicability:** Applicable; active project.
- **Status:** Met.
- **Target area:** Documentation/maintenance.
- **Implementation:** Contribution guidance defines blueprint change, validation, examples, testing and contribution expectations.
- **Evidence:** `CONTRIBUTING.md` at assessed commit.
- **Necessary remediation:** None evidenced.

### OSPS-LE-02.01 — source license meets OSI/FSF definition
- **Applicability:** Applicable; active project.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Source is licensed under MIT.
- **Evidence:** `LICENSE` at assessed commit.
- **Necessary remediation:** None evidenced.

### OSPS-LE-02.02 — released software asset license meets OSI/FSF definition
- **Applicability:** Applicable if released software assets exist; version tags exist, but whether separate assets are published was not verifiable.
- **Status:** Unverified.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Source license is MIT; separate hosted release asset licensing and contents were not inspected.
- **Evidence:** `LICENSE`, local tags; GitHub release/API unavailable.
- **Necessary remediation:** Verify applicable release assets carry an eligible license.

### OSPS-LE-03.01 — source license included in repository
- **Applicability:** Applicable; active project.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** License file is present at repository root.
- **Evidence:** `LICENSE` at assessed commit.
- **Necessary remediation:** None evidenced.

### OSPS-LE-03.02 — released asset license included with assets
- **Applicability:** Applicable if release assets are distributed; tags exist but assets unknown.
- **Status:** Unverified.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Root source license is present; location of any separate release assets and accompanying license was not inspected.
- **Evidence:** `LICENSE`; hosted releases inaccessible to this review.
- **Necessary remediation:** Verify license accompanies each applicable release asset.

### OSPS-QA-01.01 — publicly readable source at static URL
- **Applicability:** Applicable; active project.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** Static GitHub URL is documented, but public readability was not independently verified.
- **Evidence:** README project URL and configured remote; no anonymous access/API result.
- **Necessary remediation:** Verify anonymous public read access and stable canonical URL.

### OSPS-QA-01.02 — publicly readable change/author/time history
- **Applicability:** Applicable.
- **Status:** Unverified.
- **Target area:** GitHub organization/repository settings.
- **Implementation:** Local Git history contains authorship/timestamps, but public visibility and completeness/rewrite policy cannot be proven locally.
- **Evidence:** Local history at assessed commit; hosted public history/settings not verified.
- **Necessary remediation:** Verify public history access and that changes/authors/times are retained.

### OSPS-QA-02.01 — direct dependency list when supported
- **Applicability:** Applicable; supported dependency mechanisms are used.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Collections, CI Python packages and exact Ansible Core versions are declared; shared role tasks are pinned as a Git submodule commit.
- **Evidence:** `collections.yml`, `requirements-ci.txt`, `.github/workflows/tests.yml`, `.gitmodules`, `git ls-tree HEAD tasks/shared`; checked-out submodule commit `892a8f87027d17e1a41bea5c7aa40b82cf5abc41`.
- **Necessary remediation:** None evidenced.

### OSPS-QA-04.01 — document project codebases when multiple repositories
- **Applicability:** Applicable; shared-task repository is consumed as a submodule.
- **Status:** Unmet.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** `.gitmodules` identifies shared-task source, but project documentation does not explain its role/status/intent as a constituent codebase.
- **Evidence:** `.gitmodules`, README and CONTRIBUTING inspected; no codebase inventory found.
- **Necessary remediation:** Document the shared-task codebase, relationship, status and intent.

### OSPS-QA-05.01 — no generated executable artifacts in VCS
- **Applicability:** Applicable; active project.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** Tracked files are role source, configuration, docs and text fixtures; no generated executable artifact identified.
- **Evidence:** Tracked-file enumeration at assessed commit; no executable artifact filename/type found.
- **Necessary remediation:** None evidenced.

### OSPS-QA-05.02 — no unreviewable binary artifacts in VCS
- **Applicability:** Applicable; active project.
- **Status:** Met.
- **Target area:** Source/dependencies/distribution.
- **Implementation:** No unreviewable binary assets identified among tracked files.
- **Evidence:** Tracked-file enumeration and binary-extension scan at assessed commit.
- **Necessary remediation:** None evidenced.

### OSPS-VM-02.01 — security contacts in documentation while active
- **Applicability:** Applicable; active project.
- **Status:** Unmet.
- **Target area:** Documentation/maintenance.
- **Implementation:** No security contact/reporting instructions were found in README, CONTRIBUTING, or a security document.
- **Evidence:** Documentation file inventory and inspected README/CONTRIBUTING at assessed commit.
- **Necessary remediation:** Add security contact details or a monitored security reporting channel.

## Outstanding external settings and actions

| Setting/action | Related requirement(s) | Evidence/limitation | Owner or required access | Status/action |
|---|---|---|---|---|
| Verify MFA, collaborator defaults, branch protection/deletion, public visibility/history | AC-01.01, AC-02.01, AC-03.01, AC-03.02, QA-01.01, QA-01.02 | GitHub settings/API unavailable | Repository/organization administrator | Unverified; inspect effective policy |
| Verify PR token/secrets and runner isolation/cleanup | BR-01.03 | YAML is not proof of effective hosted runner controls | Repository administrator and CI operator | Unverified; inspect settings and run evidence |
| Verify release channels/assets and public issue/discussion access | BR-03.02, LE-02.02, LE-03.02, GV-02.01 | Hosted release and feature/API evidence unavailable | Repository maintainer | Unverified; inspect public endpoints/settings |

## Assessment conclusion

- **Level 1 result:** Not established. Applicable controls remain Unmet or Unverified; no compliance claim is made.
- **Unmet controls:** OSPS-DO-02.01, OSPS-QA-04.01, OSPS-VM-02.01.
- **Unverified controls:** OSPS-AC-01.01, OSPS-AC-02.01, OSPS-AC-03.01, OSPS-AC-03.02, OSPS-BR-01.03, OSPS-BR-03.02, OSPS-BR-07.01, OSPS-GV-02.01, OSPS-LE-02.02, OSPS-LE-03.02, OSPS-QA-01.01, OSPS-QA-01.02.
- **Not applicable:** None. Conditional release controls are treated as applicable because version tags exist; separate asset publication remains unknown, hence Unverified rather than waived.
- **Scope caveat:** This assessment does not determine deployed-server hardening and does not replace an Ansible implementation security review. The catalog's upstream explanatory recommendations and Idarsi advice are not additional mandatory OSPS text.
