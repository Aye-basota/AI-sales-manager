# Assignment 3

## Part 1: Migrate User Stories to the Product Backlog

In Assignment 2, you documented and prioritized user stories in `reports/week2/user-stories.md` and negotiated the proposed MVP v1 scope with the customer. In this assignment, migrate the active stories into the issue-based Product Backlog, refine the backlog, plan the Sprint, deliver MVP v1, and report the results.

Use [Process Requirements](Process_Requirements.md#product-backlog-items-and-scope) as the authoritative source for reusable Scrum and workflow semantics such as Product Backlog structure, [requirement status](Process_Requirements.md#user-stories-requirement-status-and-decomposition), [traceability](Process_Requirements.md#traceability-and-user-story-index), [acceptance criteria rules](Process_Requirements.md#acceptance-criteria), [Sprint cadence](Process_Requirements.md#sprint-cadence-and-scrum-events), [Sprint roles](Process_Requirements.md#sprint-roles-and-evidence), [Work Status meanings](Process_Requirements.md#work-status), and [evidence expectations](Process_Requirements.md#sprint-roles-and-evidence). Use [Product Repository Requirements](Repository_Requirements.md#required-starting-assignment-3) as the authoritative source for repository-platform workflow configuration.

1. Preserve `reports/week2/user-stories.md` as the historical Assignment 2 artifact. Do not rewrite it during migration.

2. Create one issue for every active user story from Assignment 2.

3. Preserve each stable ID in the issue title:

   ```text
   US-001: View available courses
   ```

   The title should be a short summary of the user story. The full user-story statement must still appear in the issue body. Do not replace the stable ID with the platform-assigned issue number. Stable IDs must not be changed, reused, or reassigned.

4. Copy the following information into each migrated issue:

   * Stable user-story ID
   * User-story statement
   * MoSCoW priority
   * Notes, constraints, assumptions, and open questions

5. Continue refining the Product Backlog after migration according to [Process Requirements](Process_Requirements.md#product-goal-and-product-backlog-management):

   * Add newly discovered user stories when appropriate.
   * Split overly large or unclear stories into smaller PBIs while preserving traceability.
   * Mark invalid, duplicated, obsolete, infeasible, or otherwise unnecessary stories as removed instead of deleting their history.

6. Preserve Requirement status for every story using the canonical shared meanings from [Process Requirements](Process_Requirements.md#user-stories-requirement-status-and-decomposition). Do not create issues for removed stories unless an issue is useful for preserving discussion or decisions.

7. Create and maintain the current user-story index in:

   ```text
   docs/user-stories.md
   ```

8. Use the following structure in `docs/user-stories.md`:

   ```markdown
   | ID | Short title | MoSCoW priority | Issue | Requirement status | Work Status | Sprint |
   |---|---|---|---|---|---|---|
   | US-001 | View available courses | Must Have | [#12](...) | Active | Done | [Sprint 1](...) |
   | US-002 | Export course list | Could Have | [#13](...) | Active | To Do | — |
   | US-003 | Print course catalogue | — | — | Removed | — | — |
   ```

9. `docs/user-stories.md` must index all user stories for traceability, including:

   * Active stories with issue links
   * Removed stories with preserved stable IDs and removed status

10. In `docs/user-stories.md`:

    * For active stories, `Work Status` must mirror the current issue `Work Status` for quick traceability using the canonical shared values from [Process Requirements](Process_Requirements.md#work-status).
    * `Sprint` must link to the Sprint milestone when the story is assigned to a Sprint, or use `—` when the story is not currently assigned to any Sprint.
    * Keep active stories ordered by MoSCoW priority, then by Sprint, then by stable ID.
    * Place removed stories after all active stories.
    * Keep the file synchronized with the issue tracker according to the shared traceability rules in [Process Requirements](Process_Requirements.md#traceability-and-user-story-index).

11. `docs/user-stories.md` is the authoritative current registry of stable user-story IDs and current user-story membership. Do not use it as the detailed Sprint execution plan.

12. After migration, do not duplicate full mutable story content in `docs/user-stories.md`.

13. When adding a new user story after migration, assign it the next unused stable ID after the highest existing `US-xxx` value already present in `docs/user-stories.md`.

14. If stories were removed, split, or replaced during refinement, preserve that explanation in the relevant issue history and update `docs/user-stories.md` accordingly.

15. Update current documentation to reference the migrated issues where appropriate.

## Part 2: Apply the Assignment 3 Repository Workflow

Complete all applicable shared workflow requirements in [Process Requirements](Process_Requirements.md#sprint-roles-and-evidence) and all repository-platform requirements under **Required Starting Assignment 3** in [Product Repository Requirements](Repository_Requirements.md#required-starting-assignment-3).

During Assignment 3, ensure the repository workflow provides evidence of all of the following:

1. User Story, Other PBI, Course Task, and Bug Report issue templates.

2. Issue-linked branches and PRs/MRs, including issue-number branch naming using the format:

   ```text
   <issue-number>-short-description
   ```

3. Acceptance-criteria verification before merge.

4. Extended PR/MR template.

5. Merge-commit workflow.

6. SemVer releases and MVP-to-release mapping.

7. Root `CHANGELOG.md` and changelog workflow.

8. Link to access or run instructions for the delivered MVP v1.

9. Public sanitized video demonstration shorter than two minutes.

10. Issue-linked reviewed PRs/MRs as evidence of the workflow.

11. Every team member must participate in the workflow by doing all of the following during Assignment 3:

    * Push at least one commit
    * Create at least one issue-linked PR/MR
    * Review and approve at least one other team member's PR/MR
    * Leave at least one meaningful review comment on another team member's PR/MR

## Part 3: Create and Refine the Product Backlog

1. Create and maintain the Product Backlog using GitHub Issues/Projects, GitLab Issues/Boards, or an equivalent issue-based Product Backlog supported by the course.

2. Ensure the Product Backlog contains at least 15 qualifying PBIs.

3. Follow [Process Requirements](Process_Requirements.md#product-backlog-items-and-scope) for what counts as a PBI.

4. The following do not count toward the required 15 qualifying PBIs:

   * `Won't Have` PBIs
   * Removed PBIs
   * Assignment-administration or `Course Task` issues

5. Each PBI counted toward the required 15 must include:

   * Clear title
   * Description
   * Type
   * Work Status
   * MoSCoW priority
   * Story Points
   * Milestone where applicable
   * Assignee when included in the current Sprint Backlog

6. PBIs counted toward the required 15 do not all need acceptance criteria yet. For Assignment 3, acceptance-criteria requirements depend on MVP version and Sprint readiness as defined below.

7. Use the canonical Work Status meanings from [Process Requirements](Process_Requirements.md#work-status).

8. Refine the Product Backlog to satisfy the shared **DEEP** expectations in [Process Requirements](Process_Requirements.md#product-goal-and-product-backlog-management).

9. Create and keep accessible:

   * A Product Backlog board/view
   * A current Sprint Backlog board/view

   Use GitHub Projects, GitLab Boards, or another equivalent saved board/view that makes the Product Backlog and Sprint Backlog state inspectable.

## Part 4: Add Acceptance Criteria

1. Add at least three acceptance criteria to every PBI marked as part of `MVP v1`.

2. PBIs planned for later MVP versions, such as `MVP v2` or `MVP v3`, may omit acceptance criteria until they are refined further or selected for Sprint execution.

3. Any PBI selected for the current Sprint must have acceptance criteria before it may be treated as `Ready`, even if it is not marked as part of `MVP v1`.

4. Follow the shared acceptance-criteria rules in [Process Requirements](Process_Requirements.md#acceptance-criteria).

5. Review criteria as a team and clarify ambiguous PBIs before estimation and Sprint Planning.

## Part 5: Estimate the Product Backlog

1. Estimate the Product Backlog according to the shared estimation rules in [Process Requirements](Process_Requirements.md#sprint-planning-readiness-and-estimation).

2. Record the final estimate on each PBI counted toward the required 15. You do not need to document every estimation round.

3. Record the total current Product Backlog size in Story Points in the Week 3 report.

## Part 6: Create the Definition of Done

1. Create:

   ```text
   docs/definition-of-done.md
   ```

2. Use `docs/definition-of-done.md` to define the team's shared minimum completion standard.

3. Follow [Process Requirements](Process_Requirements.md#definition-of-done) for the shared course-level Definition of Done expectations and minimum content.

4. The Definition of Done should also require updating `CHANGELOG.md` for every user-visible change, consistent with [Product Repository Requirements](Repository_Requirements.md#required-starting-assignment-3).

5. A PBI may be marked `Done` only according to [Process Requirements](Process_Requirements.md#definition-of-done) and the team Definition of Done.

## Part 7: Create the Sprint Backlog and Plan MVP v1

1. Create the milestone for the current Sprint with its start and finish dates.

2. Follow the shared Sprint cadence and event expectations in [Process Requirements](Process_Requirements.md#sprint-cadence-and-scrum-events).

3. Define the Sprint Goal for the current Sprint in the Sprint milestone description, following the shared Sprint Goal expectations in [Process Requirements](Process_Requirements.md#sprint-planning-readiness-and-estimation).

4. For this course, use the Sprint milestone as the authoritative container for the Sprint-selected PBIs. Issues assigned to the current Sprint milestone are the selected Sprint Backlog items. The Sprint Backlog board/view must show that same set of milestone-scoped items in an inspectable view. Developers may manage the current execution plan separately; you do not need to document that plan in a separate required artifact.

5. Track MVP version separately from the Sprint milestone:

   * Use a custom field or equivalent property where available, for example `MVP version`.
   * If the platform does not support a suitable field, use a dedicated label such as `mvp-v1`, `mvp-v2`, or `mvp-v3`.
   * On GitHub, the recommended approach is to use the Table view in GitHub Projects with a custom `MVP version` field and group items by that field.

6. Select the PBIs planned for MVP v1:

   * Select user stories only from the `Must Have` stories.
   * MVP v1 does not need to include every `Must Have` story.
   * Include the necessary technical, infrastructure, design, documentation, deployment, testing, or other supporting PBIs required to deliver the selected scope.
   * Mark each selected MVP v1 PBI using the chosen MVP version field or label.

7. Assign every selected Sprint PBI to the current Sprint milestone.

8. Ensure every selected Sprint PBI appears in the current Sprint Backlog board/view.

9. Assign every selected Sprint PBI to a team member in platform metadata.

10. Record a different reviewer for every selected Sprint PBI in the issue description.

11. Ensure every selected Sprint PBI has acceptance criteria, is estimated, and is sufficiently detailed for implementation.

12. Calculate the total number of Story Points selected for the current Sprint.

13. Decompose current Sprint user stories into smaller linked technical PBIs as needed so developers can start working without additional clarification.

14. Follow [Process Requirements](Process_Requirements.md#user-stories-requirement-status-and-decomposition) for user-story and supporting-PBI structure, [roles](Process_Requirements.md#sprint-roles-and-evidence), [readiness](Process_Requirements.md#sprint-planning-readiness-and-estimation), [Work Status](Process_Requirements.md#work-status), and [evidence expectations](Process_Requirements.md#sprint-roles-and-evidence).

15. Current Sprint items must use the canonical shared `Work Status` values, and the Sprint Backlog board/view must make the current state of those items inspectable.

16. The agreed MVP v1 scope is the set of PBIs marked with the `MVP v1` version field or label.

17. All PBIs selected for MVP v1 must be completed, reviewed, verified, and marked `Done` by the Assignment 3 submission. User stories selected for MVP v1 are marked `Done` only when all linked supporting PBIs required to satisfy their acceptance criteria are completed.

## Part 8: Implement and Verify MVP v1

1. Deliver the MVP v1 scope negotiated in Assignment 2 and finalized through Assignment 3 Product Backlog refinement and Sprint Planning.

2. MVP v1 must include:

   * All user stories marked as part of `MVP v1`
   * All supporting PBIs marked as part of `MVP v1`

3. By submission, every PBI marked as part of `MVP v1` must satisfy the shared completion rules in [Process Requirements](Process_Requirements.md#definition-of-done) and be marked `Done`.

4. Verify the relevant acceptance criteria and record verification evidence in the PR/MR and the Week 3 report.

5. Provide a usable delivered increment appropriate to the product type. For example:

   * **Web/mobile:** the hosted application works for the selected MVP v1 flows.
   * **API/service:** the documented endpoints needed by MVP v1 are accessible and usable.
   * **CLI:** the released command-line interface supports the delivered MVP v1 workflows.
   * **Library:** the released package/build and usage example demonstrate the delivered MVP v1 functionality.

6. Keep the delivered MVP v1 accessible until the assignment has been graded.

## Part 9: Sprint Review with the Customer

1. Arrange a Sprint Review meeting with the customer. As many team members as possible should attend.

2. Present and discuss:

   * The planned MVP v1 scope
   * The implemented MVP v1 increment
   * Any changes between the planned and implemented scope
   * Remaining gaps, risks, or follow-up items

3. Conduct the Sprint Review according to the shared Scrum-event expectations in [Process Requirements](Process_Requirements.md#sprint-cadence-and-scrum-events), and review the current Product Backlog and Sprint Backlog with the customer.

4. Obtain explicit customer feedback on the implemented MVP v1 increment against the planned scope.

5. If the customer accepts the reviewed MVP v1 increment and scope, obtain explicit approval. Otherwise, document the requested changes and follow-up actions.

6. Before the meeting, ask whether the customer permits publishing a redacted or sanitized English transcript in the public repository. If that permission was already obtained earlier in the project, you may reuse it and do not need to ask again for repository publication.

7. **Always ask for permission before recording starts.** Recording permission is separate and must be obtained before each recorded meeting.

8. Before recording, ask whether the customer permits sharing a sanitized English transcript privately with instructors for assessment if public repository publication is refused.

9. Write the English customer review transcript in:

   ```text
   reports/week3/customer-review-transcript.md
   ```

   Clean it for readability without changing meaning. Place each timestamp on a separate line. Remove PII and confidential business information while preserving enough context for evaluation. Use `[inaudible]` and `[redacted]` where appropriate.

10. Publish the transcript only if repository publication permission has been obtained. If public publication was refused but private instructor sharing was permitted, do not commit the transcript. State this in `reports/week3/README.md` and include the sanitized transcript only in the Moodle PDF or equivalent private instructor-sharing channel.

11. If recording or private instructor sharing is refused, write detailed English notes in:

   ```text
   reports/week3/customer-review-notes.md
   ```

   The notes replace the transcript as evidence. Record the discussion chronologically and include the scope reviewed, implemented increment shown, customer feedback, questions, decisions, approvals, requested changes, and resulting Product Backlog updates. Sanitize the notes before sharing them with instructors or publishing them.

12. Write the meeting summary in:

   ```text
   reports/week3/customer-review-summary.md
   ```

   Include the date, participants or roles, artifacts demonstrated, scope reviewed, implemented increment discussed, approvals or requested changes, risks, action points, and resulting Product Backlog or scope changes.

## Part 10: Create or Update the Roadmap

1. Create and maintain:

   ```text
   docs/roadmap.md
   ```

2. Follow the shared roadmap requirements in [Process Requirements](Process_Requirements.md#roadmap).

## Part 11: Reflect on the Week

Write:

```text
reports/week3/reflection.md
```

Include:

1. `## Learning points`: what the team learned from Product Backlog migration, Product Backlog refinement, estimation, Sprint Planning, MVP v1 delivery, customer review, release preparation, and workflow enforcement.

2. `## Validated assumptions`: assumptions or decisions confirmed or rejected through implementation, testing, deployment, review, or customer feedback.

3. `## Friction and gaps`: unresolved requirements, technical risks, missing scope, blocked work, review/process friction, follow-up questions, and uncertainties discovered during MVP v1 delivery.

4. `## Planned response`: how the team will respond in the next Sprint or assignment, with links to affected PBIs, milestones, releases, or documentation where relevant.

## Part 12: Conduct a Sprint Retrospective

Write:

```text
reports/week3/retrospective.md
```

This retrospective must be public and sanitized. Do not include sensitive personal information or private conflict details.

Include:

1. `## What went well`: three specific points.
2. `## What did not go well`: three specific points.
3. `## Action points`: one or two concrete improvement actions for the next Sprint.

## Part 13: Report on LLM Usage

Write:

```text
reports/week3/llm-report.md
```

Describe how AI/LLM tools were used. If no AI tools were used, state that explicitly.

## Assignment Report in the Repository

Create the following public Week 3 report structure:

```text
reports/
└── week3/
    ├── README.md
    ├── customer-review-summary.md
    ├── customer-review-transcript.md # if publication is permitted
    ├── customer-review-notes.md      # if recording or private sharing is refused
    ├── reflection.md
    ├── retrospective.md
    ├── llm-report.md
    └── images/
```

Use `reports/week3/README.md` as the canonical public Week 3 report and submission index for Assignment 3. It must contain the required Week 3 summary content listed below and provide direct links to every applicable required repository file and external artifact. Keep separate artifacts only where this assignment explicitly requires a dedicated file.

Write the public Week 3 report in:

```text
reports/week3/README.md
```

Use this file as the canonical public Week 3 report and submission index for Assignment 3.

Include:

1. Project name, short description, and link to the root `LICENSE`.
2. Summary of the current user-story and PBI scope since Assignment 2, with links to `docs/user-stories.md` and relevant issues for current state and history.
3. Report on which customer feedback points from Assignment 2 were addressed in MVP v1.
4. Link to historical `reports/week2/user-stories.md`.
5. Link to current `docs/user-stories.md`.
6. Link to the Product Backlog board/view.
7. Link to the current Sprint Backlog board/view.
8. Link to the current Sprint milestone as the authoritative source for the Sprint Goal, Sprint dates, and current Sprint scope.
9. Total Product Backlog size in Story Points.
10. Total current Sprint size in Story Points.
11. Link to the MVP version field, filtered view, or equivalent grouped view showing the MVP v1 scope.
12. Description of the selected MVP v1 scope.
13. Explanation of PBI types, statuses, priorities, Sprint milestone usage, MVP version tracking, and task-decomposition approach.
    Use the shared definitions from `Process_Requirements.md` where appropriate instead of restating them inconsistently.
14. Short summary of the roadmap direction for the current and next Sprint, with a link to `docs/roadmap.md`. Do not duplicate the full roadmap or backlog tables here.
15. References to the verification evidence for the completed MVP v1 PBIs.
16. Summary of the current product status.
17. Summary of the next steps.
18. A contribution traceability table mapping each team member to their issues, PRs/MRs, and review activity.
19. Link to the SemVer release mapped to `MVP v1`.
20. Link to the root `CHANGELOG.md`.
21. Link to `Process_Requirements.md`.
22. Link to `docs/roadmap.md`.
23. Link to `docs/definition-of-done.md`.
24. Links to the issue templates and the extended PR/MR template.
25. Links to reviewed issue-linked PRs/MRs created during Week 3.
26. Link to the delivered MVP v1 deployment, runnable artifact, or equivalent access point.
27. Link to access or run instructions in the root `README.md`.
28. Link to the public sanitized video demonstration shorter than two minutes.
29. Embedded screenshots from `reports/week3/images/` showing:

    * Product Backlog view
    * Sprint Backlog view
    * Sprint milestone
    * MVP version field, grouped view, or filtered view
    * SemVer release
    * Delivered MVP v1
    * Example reviewed issue-linked PR/MR

30. Link to the published customer review transcript; state that the transcript is shared only through Moodle or an equivalent private instructor-sharing channel if public publication was refused but private sharing was permitted; or link to the customer review notes if recording or private sharing was refused.
31. Link to the customer review summary.
32. Link to the Week 3 reflection.
33. Link to the retrospective.
34. Link to the LLM report.

## Assignment Report on Moodle

Create one PDF containing:

1. Project name and team number.
2. Table with team members, GitHub/GitLab usernames, assigned roles, and required university-identity mapping.
3. Summary of contributions.
4. Commit-hash permalink to `reports/week3/README.md`.
5. Commit-hash permalink to the product repository tree at the submission commit. The commit must be on the protected default branch.
6. Live links to:

   * Product Backlog board/view
   * Current Sprint Backlog board/view
   * Current Sprint milestone
   * MVP version field, filtered view, or equivalent grouped view showing the MVP v1 scope
   * SemVer release mapped to `MVP v1`
   * Delivered MVP v1 deployment, runnable artifact, or equivalent access point
   * Public sanitized video demonstration shorter than two minutes

7. Live links to:

   * `docs/user-stories.md`
   * `Process_Requirements.md`
   * `docs/roadmap.md`
   * `docs/definition-of-done.md`
   * `CHANGELOG.md`

8. Links to the reviewed issue-linked PRs/MRs used as Assignment 3 evidence.
9. Exact access instructions for the delivered MVP v1, including any limited-permission test credentials if needed.
10. Customer recording link, only if the customer permitted private instructor sharing. Store it outside the repository and make it accessible only to instructors.
11. Sanitized English customer review transcript if it could not be published but private instructor sharing was permitted, or detailed English notes if recording or private sharing was refused.
12. Explanation of the customer feedback, approvals, requested changes, and resulting Product Backlog updates.

> [!IMPORTANT]
> Verify all links before submission. Public links must be publicly viewable but not publicly editable. Required artifacts and links must remain accessible until the assignment has been graded.

### Submission Procedure

* Submit the PDF through Moodle.
* Only **one submission per team** is required.

### AI and LLM Usage

You may use AI tools, LLMs, or other productivity tools. However:

1. Explicitly report which tools were used and how.
2. The submission must contain meaningful analysis and original team effort.
3. Do not submit filler text, generic AI-generated content, or unnecessary explanations.

Failure to disclose AI usage or submitting low-value AI-generated content may result in a failing grade.
