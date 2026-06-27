# Product Repository Requirements

These requirements apply to the product repository throughout the course. Each section states when its requirements become mandatory.

## Baseline Repository Requirements

### Repository Setup and Access

1. Create the product repository in your team organization on the [IU GitLab platform](https://gitlab.pg.innopolis.university), [GitLab](https://gitlab.com/), or [GitHub](https://github.com/).

2. Use a monorepo: store the product source code, documentation, reports, API/interface artifacts, and setup instructions in the same repository.

3. The repository must be public. License team-created content under the MIT License and add the MIT License text to `LICENSE` in the repository root.

4. Before creating the product repository, inform the customer that the project must be developed publicly and that team-created content will be MIT-licensed. Obtain the customer's written consent. Written consent includes a message via Telegram, email, or another chat service — a paper signature is not required. Retain the evidence outside the repository and submit it privately through Moodle when required.

5. If the customer does not consent or raises concerns, contact the TA immediately. Do not create the product repository or publish project materials until the TA provides instructions.

6. Add all team members before collaborative work begins.

7. Maintain a root `README.md` containing the project description, local setup instructions, links to the main documentation, and the current deployment or runnable artifact where applicable.

8. Keep the repository and required external artifacts accessible until the course has been graded.

### Licensing and Attribution

1. Do not commit customer-owned code, datasets, media, trademarks, or other assets unless the customer explicitly permits their public redistribution.

2. Do not commit third-party code, datasets, media, or other assets unless their license permits the intended use and public redistribution. Students are responsible for verifying license compatibility.

3. Customer-owned and third-party items may retain separate redistributable licenses and are excluded from the repository-wide MIT License.

4. If the repository includes customer-owned items or vendored/copied third-party code or assets, create `ATTRIBUTION.md` in the repository root. For each item, document its name, source, author or owner, license, and use in the product.

5. Normal package-manager dependencies do not require entries in `ATTRIBUTION.md`; document them using the appropriate dependency manifest and lockfile.

### Basic Branch Protection and PR/MR Workflow

1. Protect the default branch (`main` or equivalent) after the initial repository setup commit:

   * Disable direct pushes.
   * Require at least one approval from another team member before merging, where supported.
   * Do not allow PR/MR authors to approve their own changes.

2. The initial repository setup commit is the only change that may be pushed directly to the default branch. Use Pull Requests (PRs) or Merge Requests (MRs) for all later changes, including documentation and configuration changes.

3. If the selected platform or plan cannot enforce required approvals, such as GitLab Free, another team member must still approve each PR/MR before it is merged. The approval must be visible in its history.

4. For each change:

   * Create a separate branch.
   * Submit the change through a PR/MR.
   * Keep the PR/MR focused on one change where practical.
   * Obtain approval from at least one other team member.
   * Document the automated and/or manual testing performed.

5. Create a PR/MR template that prompts for:

   * Summary of changes
   * Testing performed
   * Reviewer checklist

6. Do not rewrite repository history or delete PRs/MRs, reviews, or other assignment evidence until the relevant assignment has been graded.

7. Rewriting history is allowed only when necessary to remove accidentally committed sensitive data. Follow the incident-response procedure below.

### Lychee Link Checking

1. Configure Lychee link-checking CI using the official guide for the selected platform:

   * [GitHub Actions](https://lychee.cli.rs/continuous-integration/github/)
   * [GitLab CI](https://lychee.cli.rs/continuous-integration/gitlab/)

2. Check all repository Markdown files, including every file under `reports/`.

3. Run Lychee on PRs/MRs and on changes to the protected default branch.

4. The latest protected-default-branch run must pass before submission.

5. Check repository-relative links and public external links. Authenticated, rate-limited, unstable, or otherwise unsuitable links may be excluded narrowly.

6. Document and justify every excluded link, then manually verify it before submission. Do not broadly exclude all external links.

### Configuration, Sensitive Information, and Public Artifacts

1. Add a `.gitignore` appropriate for the selected technology stack.

2. Commit dependency lockfiles where the selected ecosystem supports them.

3. If the product requires environment variables or secret configuration, add a sanitized `.env.example` and ignore `.env` and other secret files.

4. Commit generated files only when required for deployment, grading, or tool compatibility. Ignore other generated files.

5. Do not commit large binaries, datasets, recordings, model weights, or similar large files to normal Git history. Add them to `.gitignore`. When genuinely required, use approved external storage or Git LFS.

6. Use external storage according to the artifact's sensitivity:

   * Store public, non-sensitive artifacts in package registries or publicly accessible cloud storage.
   * Store private recordings or instructor-only evidence in access-controlled university storage or cloud storage shared only with instructors.
   * Do not store or submit real, personal, or production credentials, secrets, or unnecessary PII.
   * Dedicated limited-permission test credentials may be submitted privately when an assignment requires them.

7. Do not use Git LFS or public external storage to publish private or confidential information.

8. Do not commit credentials, PII, confidential customer materials, raw recordings, recording links, or test credentials.

9. Sanitize public repository documents. Use GitHub/GitLab usernames, roles, or pseudonyms such as "customer" instead of real names where possible.

10. Use only sanitized demo/test data in public deployments, video demonstrations, screenshots, API documentation, Swagger/Postman examples, and other public materials.

11. Keep public and private evidence separate:

    * Public reports, releases, CI/test/coverage evidence, sanitized screenshots, public sanitized demo videos, and sanitized customer summaries may be committed or linked publicly.
    * Private recordings, private transcripts or notes when publication is refused, exact recording timecodes, university emails, private credentials, private access instructions, private consent evidence, and customer-identifying evidence must be submitted only through Moodle or another instructor-approved private channel.
    * Presentation slides may be committed only when the copy is intentionally public and sanitized.
    * Rehearsed presentation videos must remain private unless the team intentionally publishes a sanitized version.

### Sensitive-Data Incident Response

If credentials, PII, confidential information, or other sensitive data are accidentally committed:

1. Immediately revoke or rotate exposed credentials.
2. Temporarily make the repository private when necessary.
3. Notify the TA as soon as possible.
4. Remove the sensitive data from current files and Git history.
5. Privately document what was exposed, when it was exposed, and the remediation performed; send this documentation to the TA.

## Issue-Linked Workflow Requirements

### Issue-Linked Workflow

Use [Process Requirements](Process_Requirements.md) as the authoritative source for reusable Scrum and workflow semantics such as Product Backlog structure, Sprint semantics, issue roles, Work Status meanings, acceptance criteria terminology, and evidence expectations. This section defines only how those shared requirements must be configured or enforced in the repository platform.

1. Create and use templates appropriate to the selected platform:

   * **GitHub:** create Issue Forms in `.github/ISSUE_TEMPLATE/` and a PR template in `.github/pull_request_template.md`.
   * **GitLab:** create issue templates in `.gitlab/issue_templates/` and an MR template in `.gitlab/merge_request_templates/`.

2. Create separate issue forms/templates for:

   * **User Story:** user role/persona, desired action, expected value, description, and acceptance criteria.
   * **Other PBI:** issue type, description, and acceptance criteria.
   * **Course Task:** description and expected evidence or deliverable.
   * **Bug Report:** problem description, reproduction steps, expected behavior, actual behavior, environment, and acceptance criteria for the fix.

   Include any additional fields needed to satisfy the shared process requirements, such as implementer, reviewer, and explicit deliverable or evidence notes when the expected evidence is not obvious from a normal linked PR/MR.

   Course Task issues are not PBIs and do not count toward any backlog-size minimums.

3. Disable blank issue creation where supported.

4. For each non-automated change:

   * Create the branch from the relevant issue page where supported.
   * Name the branch `<issue-number>-short-description`, for example `42-add-login-form`.
   * Link the PR/MR to the relevant issue.
   * Verify the relevant acceptance criteria before merging.

5. Extend the PR/MR template to prompt for the related issue and acceptance-criteria verification.

6. Automated dependency-update PRs/MRs do not need to link to an issue, but still require review and configured checks.

7. Disable squash and rebase merging where supported. Use merge commits.

8. If the selected platform supports custom fields, labels, saved views, milestones, boards, or equivalent workflow configuration, configure them so the shared process requirements remain inspectable. Examples include reviewer capture, Sprint container visibility, and MVP version tagging where an assignment requires it.

### Releases and Changelog

Use releases and changelog entries to preserve traceability between delivered product increments, source code, and user-visible changes.

Process Requirements define the Sprint milestone and Sprint increment semantics. This section defines how repository releases, tags, changelog entries, artifacts, and demo links preserve delivered-increment evidence.

1. Version releases using [Semantic Versioning](https://semver.org/) and prefix Git tags with `v`, for example `v0.1.0`.

2. Teams may create any number of SemVer releases during development.

3. Map each submitted course MVP milestone or required sprint increment to one selected SemVer release. Do not create a release retroactively for MVP v0:

   * Identify the mapped course MVP milestone in the release description.
   * Link the milestone to the selected release in the assignment report.
   * Map each later release-mapped MVP milestone to a release with higher SemVer precedence.

   A Sprint milestone remains the planning and inspection container. A SemVer release is the packaged delivered increment created from the protected default branch after the Sprint work is completed; it may map to a Sprint increment, but it does not replace the Sprint milestone.

4. Each submitted tag and release must point to a commit on the protected default branch.

5. Do not move, replace, or delete tags/releases mapped to submitted MVP milestones until the course has been graded.

6. Protect mapped tags from modification or deletion where supported.

7. Include runnable built artifacts where applicable. Libraries may provide a package/build artifact and runnable example. Hosted applications may link to the deployment and access instructions.

8. Provide links to run instructions unless an assignment explicitly specifies otherwise.

9. Provide a public sanitized video demonstration shorter than two minutes unless an assignment explicitly specifies otherwise. If the requirement applies, surface the video link in the relevant assignment report artifacts.

10. Maintain `CHANGELOG.md` in the repository root following [Keep a Changelog](https://keepachangelog.com/).

11. Maintain `[Unreleased]` during development and add an issue-linked entry for every user-visible change using applicable categories: `Added`, `Changed`, `Deprecated`, `Removed`, `Fixed`, and `Security`.

12. Extend the PR/MR template with a changelog checklist requiring exactly one selection:

    * Added or updated a user-visible entry in `CHANGELOG.md`.
    * Not applicable because the change is not user-visible.

13. When creating a release, move included entries into a dated SemVer section, link it to the release, and create a new empty `[Unreleased]` section.

## Required Starting Assignment 4

### Quality Automation and CI

Use [Process Requirements](Process_Requirements.md) as the authoritative source for architecture, quality requirements, quality requirement tests, Definition of Done, traceability, UAT, and Sprint evidence. This section defines the repository automation and evidence required starting in Assignment 4.

The automation, tests, coverage evidence, automated quality requirement tests, additional QA checks, and CI gates and evidence introduced for Assignment 4 and referenced by the Definition of Done are maintained repository requirements. They must continue to apply during later project work unless a later requirement explicitly supersedes them or the team replaces a check with a documented equivalent or stronger check.

Process Requirements define what counts as a quality requirement, QRT, UAT, or Done status. This section defines how those requirements must be automated, evidenced, and kept active in the repository.

Architecture documentation and ADRs introduced in Assignment 5 are maintained repository requirements after they are introduced.

1. Configure CI using GitHub Actions, GitLab CI, or an equivalent platform-supported CI system.

2. Run CI on PRs/MRs and on changes to the protected default branch.

3. The CI pipeline may use separate jobs or multiple steps inside a smaller number of jobs, but it must make the required checks and results inspectable.

4. The CI pipeline must include:

   * Source-code linting where applicable to the stack
   * Formatting check or type checking where applicable to the stack
   * Build or testable snapshot creation where needed
   * Automated unit tests
   * Automated integration tests
   * Automated quality requirement tests
   * Line coverage reporting for tested code
   * At least one additional QA check, such as dependency update or dependency health checking, dependency vulnerability scanning, static analysis beyond the normal compiler or type checker, accessibility checking, API contract checking, or performance testing

   Link checking of any kind, including baseline Lychee, cannot satisfy the Assignment 4 additional QA check. The additional QA check must be distinct from required linting, formatting/type-checking, build, test, coverage, quality requirement test checks, and any link-checking job. For Assignment 4, a single CI check cannot count both as an automated quality requirement test and as the additional QA check.

5. Minimum acceptable CI examples:

   * **Web frontend:** install dependencies, lint, format or type check, build, unit tests, integration or component tests, automated quality requirement tests such as accessibility or performance checks, line coverage, and one additional QA check such as dependency vulnerability scanning.
   * **API/backend:** install dependencies, lint, format or type check, build or package creation, unit tests for critical business logic, integration tests for API plus database or service interaction, automated quality requirement tests such as response-time, contract, reliability, or security checks, line coverage, and one additional QA check such as static analysis or dependency vulnerability scanning.
   * **CLI/library:** install dependencies, lint, format or type check, build or package creation, unit tests, integration tests against realistic command or package usage, automated quality requirement tests such as startup time, portability, error handling, or compatibility checks, line coverage, and one additional QA check such as dependency scanning or static analysis.

6. Keep the Assignment 4 CI checks active for later project work. Later PRs/MRs and protected-default-branch changes must continue to run the relevant linting, build, test, coverage, quality requirement, and QA checks.

7. Do not remove, disable, or narrow tests and quality gates after Assignment 4 only because the assignment has been submitted. If a product change makes a check obsolete, replace it with an equivalent or stronger check and document the reason.

8. Dependency-update checks, dependency-risk checks, static analysis, accessibility checks, API contract checks, performance checks, or equivalent automated QA checks are recommended where the selected platform and stack support them.

9. Teams must maintain the following repository documentation introduced in Assignment 4:

   * `docs/quality-requirements.md`
   * `docs/quality-requirement-tests.md`
   * `docs/testing.md`
   * `docs/user-acceptance-tests.md`

   Starting in Assignment 5, teams must also maintain:

   * `docs/architecture.md`
   * At least three ADRs in `docs/adr/`

10. Teams must identify the product's critical modules and report line coverage for those modules. Critical modules are source files, packages, or product areas responsible for core user workflows, persistence, external integration, security, business rules, or other behavior where defects would materially affect the product.

11. Each critical module must have at least 30% automated line coverage unless a TA explicitly approves another threshold.

12. If global repository coverage is lower than critical-module coverage, explain why and identify the untested or lightly tested areas.

13. Maintain `docs/testing.md` as the canonical testing status artifact. It must show, at minimum:

    * Critical modules and their coverage status
    * Unit test status
    * Integration test status
    * Automated quality requirement test status
    * Linting, formatting, type checking, and additional QA check status
    * Additional QA check objective or risk addressed, scope, latest result, evidence, and limitations or follow-up work
    * CI links, latest protected-default-branch result, and branch protection or rules evidence
    * Manual test evidence where automation is not feasible and where the evidence does not count as a quality requirement test
    * Which Assignment 4 quality gates remain active for later project work, or which documented replacements supersede them

14. Use tables similar to this structure in `docs/testing.md`:

    ```markdown
    ## Critical Modules and Coverage

    | Critical module | Why critical | Required line coverage | Current line coverage | Evidence |
    |---|---|---:|---:|---|
    | `src/search.ts` | Main user workflow. | 30% | 42% | [Coverage run](...) |

    ## Automated Test Status

    | Test type | Scope | Command or CI check | Latest result | Evidence |
    |---|---|---|---|---|
    | Unit tests | Critical product logic | `npm test -- --coverage` | Passing | [CI run](...) |
    | Integration tests | API and database interaction | `npm run test:integration` | Passing | [CI run](...) |
    | Automated QRTs | QR-001, QR-002, QR-003 | `npm run test:quality` | Passing | [QRT report](...) |

    ## CI and QA Check Status

    | Gate or check | Required for Done? | Latest protected-branch status | Evidence |
    |---|---|---|---|
    | Linting | Yes | Passing | [CI run](...) |
    | Formatting or type checking | Yes | Passing | [CI run](...) |
    | Additional QA check | Yes | Passing | [Check report](...) |

    ## Additional QA Check Rationale

    | QA objective or risk | Additional QA check | Scope | Latest result | Evidence | Limitations or follow-up |
    |---|---|---|---|---|---|
    | Dependencies with known vulnerabilities may expose users or deployments to avoidable risk. | Automated dependency vulnerability scan. | Product dependency manifests and lockfiles. | Passing | [CI run](...) | Some vulnerabilities may require manual triage or delayed upstream fixes. |

    ## Manual Evidence That Does Not Count as QRT

    | Evidence | Scope | Result | Follow-up PBI or issue |
    |---|---|---|---|
    | Customer UAT observation | Checkout flow | Passed with minor wording feedback | [#42](...) |
    ```

15. Automated unit tests must cover critical product logic.

16. Automated integration tests must cover important interactions between product components where applicable. Examples include API routes with persistence, service boundaries, bot command or webhook flows, configuration validation, or UI components interacting with application state or API boundaries. Full browser end-to-end testing is not required in Assignment 4.

17. If a product has little traditional source code, for example a no-code or configuration-heavy product, the team must still automate meaningful checks where possible and explain the adapted testing strategy in `docs/testing.md`.

18. The team Definition of Done must require relevant CI checks, test evidence, coverage expectations, and quality gates before a PBI can be marked `Done`.

19. The Definition of Done must continue to govern later project work. Later PBIs must satisfy the relevant tests, CI gates, quality requirement checks, and evidence rules for the changed product areas.

20. The latest protected-default-branch CI run must pass before submission unless the applicable assignment public report clearly documents a temporary external outage or TA-approved exception. The applicable assignment public report must also include inspectable branch protection or rules evidence.

## Recommended Throughout the Course

1. Enable secret scanning and push protection where supported.

2. Provide a Nix flake with a development shell or a `devenv` configuration for a reproducible development environment.
