# Process Requirements

These requirements define the reusable Scrum, workflow, and product-management expectations used across the course. Assignment documents may add stricter or more specific requirements for a particular week, but they must not redefine the same shared terms differently.

## Product Backlog Items and Scope

1. A Product Backlog item (PBI) is an issue or equivalent tracked item representing product work that improves the product.

2. PBIs may include user stories, bugs, technical work, infrastructure work, research, design, testing, deployment, and maintained product documentation or maintained workflow documentation that improves the product repository.

3. A Course Task is tracked work whose primary purpose is course reporting, grading evidence, submission packaging, or course administration rather than improving the product.

4. Course Tasks are not PBIs even if the team tracks them in the same platform.

5. By default, artifacts under `reports/` are Course Task artifacts.

6. Maintained artifacts such as `docs/user-stories.md`, `docs/roadmap.md`, `docs/definition-of-done.md`, root setup documentation, deployment/run instructions, interface specifications, and `CHANGELOG.md` are not Course Tasks when they improve the maintained product repository.

## Product Goal and Product Backlog Management

1. Maintain a Product Goal as the longer-lived target for the product. The Product Backlog should evolve toward that goal.

2. Maintain one current Product Backlog that acts as the single ordered source of product work for the team.

3. Product Backlog refinement is an ongoing recurring activity. Refine the backlog throughout the Sprint instead of postponing all clarification until Sprint Planning.

4. The Product Backlog must satisfy **DEEP**:

   * **Detailed appropriately:** near-term and high-priority PBIs are more detailed than distant PBIs.
   * **Emergent:** add, remove, split, merge, clarify, and reorder PBIs as the team learns.
   * **Estimated:** sufficiently understood PBIs are estimated before the team commits to them in a Sprint.
   * **Prioritized:** the backlog is ordered so the most valuable or important work is considered first.

5. Keep enough refined backlog near the top that the next Sprint can be planned without major preventable ambiguity.

## User Stories, Requirement Status, and Decomposition

1. A user-story issue must contain:

   * The stable user-story ID where applicable
   * The user-story statement
   * Relevant notes, constraints, assumptions, or open questions
   * Acceptance criteria

2. Use stable user-story IDs consistently once assigned. Do not change, reuse, or reassign them.

3. Requirement status for a user story is one of:

   * `Active` - an accepted, current product requirement
   * `Removed` - no longer considered a current product requirement

4. Preserve the stable IDs and history of removed stories. Explain why they were removed instead of deleting the requirement history.

5. Do not use a user-story issue as the main container for implementation subtasks.

6. When implementation, design, testing, deployment, or other supporting work needs to be tracked explicitly, create separate linked PBIs.

7. A separate linked PBI is required when the work needs its own implementer responsibility, review, acceptance criteria, estimation, or verification evidence.

8. User stories selected for a Sprint must be small enough to be completed within that Sprint. If a story is too large or unclear, split or refine it before Sprint Planning while preserving traceability.

9. A user story is completed only when all linked supporting PBIs required to satisfy its acceptance criteria are completed. A user-story issue does not require its own dedicated implementation PR/MR.

## Acceptance Criteria

1. Use `acceptance criteria` terminology for PBIs.

2. Acceptance criteria must be specific, observable, and testable.

3. Given/When/Then ([Gherkin](https://cucumber.io/docs/gherkin/reference)) is recommended for behavioral scenarios, but any clear and testable format is acceptable.

4. A PBI that is expected to be implemented, reviewed, or verified must not be treated as ready for execution without acceptance criteria appropriate to that work.

## Architecture, Quality Requirements, and Quality Requirement Tests

1. Quality requirements describe how well the product must satisfy stakeholder needs. They are non-functional requirements that influence architecture, technology choices, testing strategy, and release readiness.

2. Software architecture is the set of structures needed to reason about the system. These structures comprise software elements, relations among them, and properties of both.

3. Architecture documentation should describe the current system structure, important elements, relations between them, external systems, and quality-relevant properties at a level that helps the team reason about product change.

4. Use Architecture Decision Records (ADRs) to preserve important quality-relevant architecture decisions, rationale, and tradeoffs.

5. Use a recognized quality model to structure quality requirements. For this course, use ISO/IEC 25010 quality characteristics and sub-characteristics where applicable. Required quality requirements should be distinguished at the sub-characteristic level, such as:

   * Time behaviour
   * Resource utilization
   * Availability
   * Fault tolerance
   * Confidentiality
   * Integrity
   * Interoperability
   * Operability
   * Modifiability
   * Testability

6. Each quality requirement must have a stable ID using the format:

   ```text
   QR-001
   ```

7. A quality requirement must explain:

   * The selected ISO/IEC 25010 quality sub-characteristic
   * Why that quality requirement matters for this product and stakeholders
   * The measurable scenario
   * The automated quality requirement tests that verify it

   After ADRs are introduced in Assignment 5, each quality requirement must also link to the architecture decisions that address it.

8. Specify each quality requirement as a measurable scenario using this structure:

   ```text
   When <source> <stimulus> under <environment>,
   the <artifact> shall <response> within <response measure>.
   ```

9. The response measure must be concrete enough to test. Avoid vague measures such as `fast`, `secure`, `user-friendly`, or `reliable` without measurable criteria.

10. Each quality requirement must have at least one linked automated quality requirement test with a stable ID using the format:

    ```text
    QRT-001
    ```

11. A quality requirement test is an automated test or CI check that directly verifies one or more measurable quality requirement scenarios.

    Repository requirements define which CI jobs and repository evidence must exist. This section defines only whether a test or check qualifies as a QRT for traceability and quality-requirement verification.

12. Quality requirement tests must define:

    * Stable ID
    * Linked quality requirement ID
    * Verification method
    * Test data, setup, or environment
    * Automated command or CI check
    * Expected measurable result
    * Evidence location

13. Required unit tests, coverage checks, type checking, or static analysis may count as quality requirement tests only when they directly verify a measurable quality requirement scenario. For example, type checking may verify an Analysability scenario, and unit-test coverage may verify a Testability scenario.

14. Manual quality evidence, manual reviews, observations, and UATs may support testing status, but they do not count as quality requirement tests unless a later assignment or TA-approved exception explicitly allows it.

15. Treat quality requirements and quality requirement tests as maintained product assets starting in Assignment 4. Treat architecture documentation and ADRs as maintained product assets starting in Assignment 5. Later project work must keep introduced assets current, extend them when product scope or risk changes, and preserve history when a requirement, test, or decision is replaced.

16. Preserve traceability between architecture elements, ADRs, quality requirements, quality requirement tests, PBIs, PRs/MRs, CI jobs, manual evidence where applicable, and reported test results after the relevant artifacts are introduced.

17. Use one section per quality requirement. This structure is recommended:

    ```markdown
    ## QR-001: Search response time

    **ISO/IEC 25010 sub-characteristic:** Time behaviour

    **Scenario:** When an end user submits a course search request under normal production-like load, the search API shall return matching results within 2 seconds for 95% of requests.

    **Why this matters:** Users need quick feedback when searching available courses because slow search blocks the main workflow.

    **Linked quality requirement tests:** [QRT-001](quality-requirement-tests.md#qrt-001-search-response-time)
    ```

18. Example quality requirements may use maintainability sub-characteristics when the scenario is measurable. For example:

    ```markdown
    ## QR-002: Type-check feedback time

    **ISO/IEC 25010 sub-characteristic:** Analysability

    **Scenario:** When a developer opens or updates a pull request under the CI build environment, the product type-checking or static-analysis gate shall analyze the changed product code and complete within 5 seconds, failing the build if type or interface errors are detected.

    **Why this matters:** Developers need fast feedback about type and interface mistakes so they can diagnose change impact before merging.

    **Linked quality requirement tests:** [QRT-002](quality-requirement-tests.md#qrt-002-ci-type-check-feedback-time)
    ```

    ```markdown
    ## QR-003: Critical module testability

    **ISO/IEC 25010 sub-characteristic:** Testability

    **Scenario:** When a developer changes a critical product module under the standard CI environment, the module shall have automated unit tests that achieve at least 30% line coverage for that module.

    **Why this matters:** Critical product logic must be directly verifiable so defects can be detected before merge.

    **Linked quality requirement tests:** [QRT-003](quality-requirement-tests.md#qrt-003-critical-module-unit-coverage)
    ```

19. Use one section per quality requirement test. This structure is recommended:

    ```markdown
    ## QRT-002: CI type-check feedback time

    **Linked quality requirement:** QR-002

    **Verification method:** Automated CI check.

    **Test data, setup, or environment:** Standard CI build environment for pull requests and protected default-branch updates.

    **Automated command or CI check:** CI type-checking or static-analysis job.

    **Expected measurable result:** The gate completes in 5 seconds or less and fails when type or interface errors are detected.

    **Evidence link:** Latest protected default-branch CI run showing the job result and duration.
    ```

20. Use this table to distinguish the main evidence types:

    | Evidence type | What it means | Can it count as QRT? |
    |---|---|---|
    | Quality requirement | Measurable non-functional product requirement with `QR-NNN` ID. | No; it is the requirement being verified. |
    | QRT | Automated test or CI check with `QRT-NNN` ID that directly verifies a measurable QR scenario. | Yes. |
    | Unit test | Automated test for isolated product logic or a small module. | Only if linked to a measurable QR scenario. |
    | Integration test | Automated test for interaction between product components, such as API plus persistence or UI component plus state/API boundary. | Only if linked to a measurable QR scenario. |
    | UAT | Customer-executed end-user scenario. | No. |
    | Manual evidence | Observation, review, screenshot, or exploratory check. | No. |

## User Acceptance Tests

1. User acceptance tests (UATs) describe end-user-facing scenarios that customers or relevant stakeholders can execute to inspect whether the product supports intended user goals.

2. Each maintained UAT scenario should have a stable ID using the format:

   ```text
   UAT-001
   ```

3. Each maintained UAT scenario should include:

   * Stable scenario ID
   * Scenario status, such as `Active`, `Retired`, or `Superseded`
   * User goal
   * Preconditions
   * Step-by-step instructions
   * Expected outcome for each important step or for the scenario as a whole
   * Assignment-specific execution results when required
   * Customer comments or observed issues after execution
   * Resulting PBIs or issues after execution

4. Keep UAT IDs stable:

   * If a UAT scenario is still valid but needs clarification, edit it in place and keep the same ID.
   * If the clarification or refinement preserves the same user goal, keep the same ID.
   * If a UAT scenario becomes obsolete, mark it `Retired` with a short reason. Do not delete it or reuse its ID.
   * If the user goal or scenario meaning changes materially, create a new UAT ID and optionally mark the old one `Retired` or `Superseded`.

5. Preserve UAT execution history when an assignment requires customer execution evidence. Add new execution-result sections instead of overwriting previous assignment results.

6. UAT results that reveal product gaps, defects, or changed stakeholder expectations must be converted into traceable Product Backlog decisions.

7. This section defines maintained UAT scenario structure and traceability rules. Repository requirements and assignment documents define storage, evidence, and public or private artifact handling.

## Traceability and User-Story Index

1. Traceability means preserving the links between a requirement or user story and the downstream work and evidence that implement and verify it.

2. At minimum, maintain traceability between:

   * Stable user-story IDs
   * User-story issues
   * Linked supporting PBIs where applicable
   * Sprint assignment where applicable
   * Related PRs/MRs
   * Verification evidence

3. When a story is removed, split, superseded, or replaced, preserve its history and explain the change instead of deleting it.

4. When a team maintains a current user-story index such as `docs/user-stories.md`, that index is the authoritative registry of stable user-story IDs and current user-story membership, while the issue tracker remains the authoritative source for live issue details and execution state.

5. A current user-story index should mirror enough live issue metadata for quick traceability, such as the issue link, requirement status, current Work Status, and Sprint assignment where applicable.

## Customer Feedback Traceability

1. Customer feedback that affects product scope, quality, usability, or delivery risk must be converted into traceable Product Backlog decisions.

2. For each material feedback point, record:

   * The feedback point or requested change
   * The resulting PBI, issue, roadmap item, or decision record
   * The current status or planned response

3. For every material feedback point, document whether it was:

   * Addressed in the Sprint
   * Partially addressed
   * Added to the backlog for later
   * Rejected or deferred with rationale

4. Feedback that the team decides not to address must still be documented with a short rationale and, where useful, a backlog link for future reconsideration.

5. Do not treat the number of completed issues as the main measure of progress. The Sprint scope should be justified by stakeholder value, quality improvement, risk reduction, and evidence that the selected work is Done.

## Sprint Cadence and Scrum Events

1. Use Sprints as the recurring container for development work, inspection, and adaptation.

2. Unless a TA explicitly approves another cadence, a Sprint runs from Monday to Sunday.

3. Each Sprint must have a Sprint Goal: a short value-focused statement describing what the team intends to deliver and why that Sprint is worthwhile.

4. Sprint Planning must produce:

   * A Sprint Goal
   * The selected Sprint PBIs
   * A workable plan to deliver them

5. The Sprint Backlog is the set of Sprint-selected PBIs plus the current delivery plan needed to achieve the Sprint Goal.

6. Use the Sprint milestone or equivalent Sprint container consistently so the Sprint Backlog remains inspectable.

   The Sprint milestone is the planning and inspection container. It records the Sprint Goal, dates, selected PBIs, and current workflow state.

   A SemVer release is the packaged delivered increment created from the protected default branch after Sprint work is completed. A release may map to the delivered Sprint increment, but it does not replace the Sprint milestone.

   Repository requirements define how releases, tags, artifacts, and changelog entries are created and preserved. This section defines the Sprint and release roles in planning and inspection.

7. Hold a Daily Scrum or equivalent daily developer coordination event during the Sprint to inspect progress toward the Sprint Goal and adapt the plan for the next day of work.

8. Conduct a Sprint Review with relevant stakeholders to inspect the delivered outcome, discuss what changed, collect feedback, and adapt the Product Backlog as needed.

9. Conduct a Sprint Retrospective after the Sprint Review and before the next Sprint Planning. Identify concrete improvements to quality, collaboration, tools, or process, and carry the most useful improvements into the next Sprint.

## Sprint Planning, Readiness, and Estimation

1. Estimate PBIs using Story Points and the Modified Fibonacci scale:

   ```text
   1, 2, 3, 5, 8, 13, 20, 40, 100
   ```

2. Estimation must be collaborative. Planning Poker is recommended, but another collaborative relative-estimation process is acceptable.

3. If the team cannot estimate a PBI confidently, split or clarify it before committing to it in a Sprint.

4. A Sprint-selected PBI must be sufficiently ready to start. At minimum, it must have:

   * A clear expected outcome
   * The required description and context
   * Acceptance criteria
   * An estimate
   * An implementer
   * A different reviewer

5. A Sprint-selected user story may require additional linked supporting PBIs before it is ready for execution.

6. A Sprint Goal should be a short value-focused statement that makes it possible to judge at the end of the Sprint whether the intended outcome was achieved.

## Sprint Roles and Evidence

1. Each Sprint-tracked PBI must name:

   * One implementer responsible for doing the work
   * One different reviewer responsible for reviewing the work and confirming it is ready for completion

2. If the selected platform does not provide a suitable native field for the reviewer, record that role in the issue template or issue body.

3. Each issue must describe the expected outcome clearly.

4. A linked PR/MR is the default implementation evidence for a change.

5. Explicit named deliverables are required only when the expected evidence is not obvious from a normal linked PR/MR, such as a design artifact, API specification, deployment artifact, or documentation artifact.

6. Implementation PRs/MRs normally link to the supporting PBIs that do the work. They do not need to link directly to the parent user-story issue when traceability is preserved through linked supporting PBIs, related PRs/MRs, and verification evidence.

## Work Status

Use the following Work Status values consistently wherever the course requires issue status tracking:

* `To Do` - the PBI remains in the Product Backlog and is not currently ready to start
* `Ready` - the PBI is selected for the current Sprint, assigned, estimated, has the required description and acceptance criteria, and can be started without major unanswered questions
* `In Progress` - work has started on the PBI
* `Review` - the current implementation is ready for review, and the issue-linked PR/MR is open or the review is actively happening
* `Done` - for a supporting or implementation PBI, the issue acceptance criteria are satisfied, the team Definition of Done is satisfied, the issue-linked PR/MR is merged into the protected default branch, and the PBI is complete for the Sprint; for a user-story issue, the story acceptance criteria are satisfied, the team Definition of Done is satisfied, and all linked supporting PBIs required to satisfy the story's acceptance criteria are reviewed, merged, verified, and marked `Done`

## Definition of Done

1. Every team must maintain a team-specific Definition of Done in:

   ```text
   docs/definition-of-done.md
   ```

2. The team Definition of Done defines the shared minimum completion standard for work in that repository.

3. A PBI may be marked `Done` only when both:

   * Its issue-specific acceptance criteria are satisfied
   * The team Definition of Done is satisfied

4. The team Definition of Done should, at minimum, require:

   * All issue acceptance criteria are satisfied
   * The work is reviewed by another team member
   * For user stories, the linked supporting PBIs provide the required implementation, review, and verification evidence
   * Required tests or checks pass
   * Relevant quality requirements and quality requirement tests are satisfied or explicitly documented as not applicable
   * Relevant architecture documentation is satisfied or explicitly documented as not applicable after architecture documentation is introduced in Assignment 5
   * CI quality gates pass before merge when CI is configured for the repository
   * Verification evidence is preserved in the normal workflow artifacts

5. For supporting or implementation PBIs, `Done` normally also means the issue-linked PR/MR is merged into the protected default branch.

6. When later project work changes the product stack, architecture, quality requirements, critical modules, or CI configuration, update the Definition of Done so it continues to describe the current completion standard.

7. This section defines completion semantics. Repository requirements and assignment documents define specific CI gates, tests, coverage thresholds, platform enforcement, and automation evidence.

## Roadmap

1. Every team must maintain a current roadmap in:

   ```text
   docs/roadmap.md
   ```

2. `docs/roadmap.md` is the Sprint-by-Sprint delivery plan. It must not duplicate the full user-story index or repeat full mutable issue content that already lives in the issue tracker.

3. Structure the roadmap as a list of Sprints. For each Sprint, include:

   * Sprint name or number
   * Link to the corresponding Sprint milestone
   * Sprint start and finish dates
   * Sprint Goal
   * Short focus or expected outcome statement
   * Linked planned items for that Sprint, such as user stories and supporting PBIs

4. Keep the roadmap lightweight and traceable:

   * Use links to issues or other tracked PBIs instead of copying their full descriptions.
   * Summarize the intended Sprint outcome briefly instead of restating backlog metadata such as MoSCoW priority, Requirement status, Work Status, or full acceptance criteria.

5. Update the roadmap as the product direction and Product Backlog evolve.
