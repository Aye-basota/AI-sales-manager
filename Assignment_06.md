# Assignment 6

## Focus

In Assignment 6, continue the Sprint-based maintained-product model across Weeks 6 and 7 with stronger emphasis on customer-facing completion, trial handover, follow-up maintenance, actual transition, and final delivery of `MVP v3`. The goal is not only to ship one more increment. The goal is to deliver a customer-usable final course version, let the customer try a stable trial version in Week 6, respond to the resulting feedback in Week 7, transition the product in a concrete and inspectable way, and prepare a strong Demo Day presentation.

Assignment 6 builds on the maintained product, testing, CI, architecture, development-process, and hosted-documentation assets introduced earlier. Week 6 and Week 7 are both formal Sprints for this assignment. Sprint 4 in Week 6 should produce a stable trial or handover-candidate release together with customer-facing documentation review and transition-readiness evidence. Sprint 5 in Week 7 should use the customer's trial feedback, remaining fixes, documentation updates, and transition work to deliver the final course version, `MVP v3`.

The customer handover documentation, contributor guidance, agent guidance, and the updated customer-facing documentation set are maintained project assets. Later work during Week 7 must keep them current when access details, deployment steps, limitations, transition status, workflow expectations, or setup and verification commands change.

Use [Artifact Requirements](Artifact_Requirements.md) as the authoritative source for shared artifact terminology, weekly public report semantics, release and milestone artifact semantics, screenshot evidence, Sprint Review artifacts, maintained handover artifact structure, hosted artifact visibility, public sanitized demo video handling, presentation-slide and rehearsal-video privacy rules, and public/private evidence handling. Use [Process Requirements](Process_Requirements.md) as the authoritative source for shared Scrum, Product Backlog, traceability, [customer feedback](Process_Requirements.md#customer-feedback-traceability), [Definition of Done](Process_Requirements.md#definition-of-done), [quality requirement and quality requirement test](Process_Requirements.md#quality-requirements-and-quality-requirement-tests), [architecture and ADR](Process_Requirements.md#architecture-documentation-and-adrs), and [UAT](Process_Requirements.md#user-acceptance-tests) semantics. Use [Product Repository Requirements](Repository_Requirements.md) as the authoritative source for repository workflow, [release and changelog](Repository_Requirements.md#releases-and-changelog), [issue-linked workflow](Repository_Requirements.md#issue-linked-workflow-requirements), [configuration and secrets baseline](Repository_Requirements.md#configuration-sensitive-information-and-public-artifacts), and [CI and automation](Repository_Requirements.md#quality-automation-and-ci) requirements.

Assignment 6 adds week-specific deliverables, separate Week 6 and Week 7 reporting, a maintained customer-handover artifact, trial-handover evidence, final-transition evidence, and Demo Day preparation requirements. Where this assignment repeats a shared rule as a checklist item, the shared requirement remains the definition of the term and this assignment states what evidence must be produced for Weeks 6 and 7.

For this assignment:

* Most maintained project assets live in `docs/`, while `CONTRIBUTING.md` and `AGENTS.md` live in the repository root.
* `docs/customer-handover.md` is the maintained customer-handover artifact.
* The Week 6 public report means `reports/week6/README.md`.
* The Week 7 public report means `reports/week7/README.md`.
* `reports/week7/README.md` is the final Assignment 6 submission index and must link the full Week 6 evidence.
* The Week 6 Moodle PDF and the Week 7 Moodle PDF are separate canonical private submission wrappers. They contain the public permalinks plus the private identity, recording, credential, rehearsed presentation video, slides, and access details that must not be committed to the public repository for their respective submission points.

Follow [Artifact Requirements](Artifact_Requirements.md#cross-cutting-artifact-rules), [Artifact Requirements](Artifact_Requirements.md#shared-artifact-visibility-table), [Artifact Requirements](Artifact_Requirements.md#recording-artifacts-and-timecodes), and [Artifact Requirements](Artifact_Requirements.md#moodle-pdf-submission-wrapper-artifact) for reusable public/private evidence handling. For Assignment 6, keep Week 6 and Week 7 evidence separated according to those shared rules and place only private identity, private recordings, exact private timecodes, private access instructions, private credentials, private consent evidence, presentation slides, rehearsed presentation video links, and other customer-identifying evidence in the private submission channel.

Teams may submit before the end of Week 7 only if they have already completed both Sprint 4 and Sprint 5 outcomes, transitioned the product, created the final `MVP v3` release, and prepared the full Week 6 and Week 7 evidence required by this assignment.

## Part 1: Refine the Product Backlog and Plan Sprint 4 and Sprint 5

1. Refine the Product Backlog before Sprint 4 planning.

2. Review:

   * customer feedback on `MVP v2`
   * current product gaps and reliability issues
   * unfinished or partially finished product work
   * documentation gaps that would block handover or independent customer use
   * deployment, configuration, or access problems that would block transition
   * Demo Day preparation needs

3. Create or update PBIs for the selected Assignment 6 scope. The scope may include product features, bug fixes, usability work, testing work, deployment work, transition work, documentation, infrastructure, and automation.

4. Create an explicit Sprint 4 milestone for Week 6 with:

   * Sprint start and finish dates
   * Sprint Goal
   * selected Sprint PBIs

5. Create an explicit Sprint 5 milestone for Week 7 with:

   * Sprint start and finish dates
   * Sprint Goal
   * selected Sprint PBIs or a clearly marked expected follow-up scope if some Week 7 work depends on Week 6 customer feedback

6. Both Sprint 4 and Sprint 5 are formal and gradeable Sprint containers for this assignment.

7. Use the Sprint 4 and Sprint 5 milestones as the authoritative Sprint containers. Issues assigned to those milestones are the selected Sprint Backlog items.

8. The Sprint 4 Goal should explain the Week 6 trial-release and transition-readiness outcome the team intends to deliver.

9. The Sprint 5 Goal should explain the Week 7 maintenance, final-transition, or final-delivery outcome the team intends to deliver.

10. Assign every selected Sprint PBI to the relevant Sprint milestone.

11. Ensure every selected Sprint PBI has:

    * clear expected outcome
    * acceptance criteria
    * Story Points
    * implementer
    * different reviewer
    * current Work Status

12. Keep the Product Backlog board or view and both Sprint Backlog board or views inspectable.

13. The Sprint Backlog board or view must use GitHub or GitLab platform functionality, such as a Kanban board or GitHub Projects view. Do not use a Markdown artifact as the Sprint work-management board or view.

14. Update `docs/roadmap.md` to reflect the current course outcome, the remaining Week 6 and Week 7 work, `MVP v3`, and the state reached by the end of the course. Do not extend the roadmap into speculative post-course version planning.

## Part 2: Deliver the Week 6 Trial Release

1. Implement the selected Sprint 4 scope.

2. Sprint 4 must produce a stable trial release or handover-candidate release that the customer can try before the final transition.

3. Deploy or otherwise provide the Week 6 trial increment so the customer and TA can access it.

4. Keep the relevant Week 6 product access artifact accessible until grading is complete.

5. Create a new SemVer release for the Sprint 4 trial increment.

6. The Week 6 release must:

   * use a SemVer tag prefixed with `v`
   * point to a commit on the protected default branch
   * identify that it is the Week 6 trial or handover-candidate release for Assignment 6
   * link to the Sprint 4 milestone
   * link to current run or access instructions
   * link to `docs/customer-handover.md` where practical
   * link to `reports/week6/README.md`

7. Update `CHANGELOG.md` for user-visible changes according to [Product Repository Requirements](Repository_Requirements.md#releases-and-changelog).

8. Update the root `README.md` with current setup, usage, run, or deployment instructions when they changed.

## Part 3: Polish the Public Repository Entry Point and Customer-Facing Documentation

1. Treat the public repository entry point and the customer-facing documentation set as first-class Assignment 6 deliverables.

2. Update `README.md` so it works as the main public entry point to the product at handover time.

3. `README.md` should help a first-time reader quickly understand:

   * what the product is
   * how to access the current version
   * where to find the maintained documentation
   * where to find the current handover guidance

4. Keep `README.md` current, concise, and directly readable. It should be credible as a real repository front page rather than a duplicated documentation index.

5. `README.md` must, at minimum, include:

   * the project name and a short description
   * a prominent link to the current product access artifact
   * a prominent link to the current hosted documentation site
   * a link to `docs/customer-handover.md`
   * links to `CONTRIBUTING.md` and `AGENTS.md`
   * either short setup, run, or access guidance or a clear link to those instructions
   * links to the most relevant maintained documentation for a customer or TA reviewer

6. Use `README.md` to route readers to the right maintained documents rather than to duplicate detailed handover, contribution, or agent instructions that belong elsewhere.

7. Use relative repository links where practical for repository-resident documentation.

8. Embed images or diagrams in context when they materially help a first-time reader understand the product or how to access it.

9. The Assignment 6 customer-facing documentation review must cover at minimum:

   * `README.md`
   * `docs/customer-handover.md`
   * current access or usage instructions
   * deployment or installation instructions where relevant
   * troubleshooting or support notes
   * known limitations

10. Create or update the maintained contributor and agent guidance according to [Artifact Requirements](Artifact_Requirements.md#contributingmd), [Artifact Requirements](Artifact_Requirements.md#agentsmd), and [Product Repository Requirements](Repository_Requirements.md#maintained-contributor-and-agent-guidance).

11. Create or update:

    ```text
    CONTRIBUTING.md
    AGENTS.md
    ```

12. Keep `README.md`, `CONTRIBUTING.md`, and `AGENTS.md` current during both Week 6 and Week 7 work when product access, documentation entry points, workflow, setup steps, verification commands, review expectations, safety constraints, or links to maintained documentation change.

## Part 4: Maintain the Customer Handover Documentation

1. Follow [Artifact Requirements](Artifact_Requirements.md#docscustomer-handovermd) for the maintained structure and content of `docs/customer-handover.md`.

2. Create or update:

   ```text
   docs/customer-handover.md
   ```

3. `docs/customer-handover.md` must describe the current actual handover state of the product rather than an aspirational future state.

4. Keep it practical and customer-facing. It may summarize and link to more detailed documentation, but it must not be only a bare link list.

5. For Assignment 6, `docs/customer-handover.md` must make the concrete transition scope inspectable. At minimum, it must clearly state:

   * which repository, service, deployment, account, access, or ownership arrangements were transferred to the customer, delegated, or intentionally retained by the team, where relevant
   * which environment variables, configuration values, external services, or secrets-handling steps the customer must know about without exposing secrets
   * which setup, deployment, recovery, or verification steps the customer must be able to follow
   * which documentation pages are the main entry points for normal customer use, operation, and troubleshooting
   * whether the current documentation set is sufficient for the reached handover level and what support still remains necessary

6. Keep `docs/customer-handover.md` current during both Week 6 and Week 7 work. If customer feedback, access details, deployment steps, limitations, or transition status change, update the document accordingly.

## Part 5: Conduct the Week 6 Transition-Readiness Meeting and Customer Trial

1. Meet the customer in Week 6 to discuss transition readiness and let the customer try the Week 6 trial release.

2. The Week 6 meeting must discuss at minimum:

   * whether the product is complete enough for transition
   * which parts are ready and which still need changes
   * whether the customer is already using the product and, if so, how
   * if the customer is not using it yet, why not
   * whether the product is already deployed or operated on the customer side and, if not, what blocks that
   * what must happen in Week 7 to complete transition
   * how to increase the chance that the product remains useful after final delivery
   * customer feedback on the reviewed customer-facing documentation set

3. During or before that meeting, ask the customer to review the Assignment 6 customer-facing documentation set defined in Part 3.

4. If practical for the product, let the customer try the product independently or with minimal guidance using the Week 6 trial release.

5. Record whether the customer:

   * confirmed that the product is ready for independent use after Week 7 work
   * independently used the trial release
   * deployed or operated it on their side

6. If the customer identifies product, deployment, documentation, or handover problems, convert them into traceable PBIs, issues, or explicit transition actions.

7. The Week 6 meeting may also satisfy Sprint Review and customer-executed UAT evidence if the relevant shared requirements are satisfied.

## Part 6: Run Sprint 5 and Perform Follow-Up Maintenance

1. Use Sprint 5 in Week 7 as a formal Sprint for maintenance, follow-up fixes, documentation updates, usability improvement, deployment work, or other remaining actions discovered during Week 6.

2. Sprint 5 may include fewer new features than earlier Sprints. That is acceptable when the Sprint is used to complete transition, remove blockers, improve reliability, clarify instructions, or respond to customer trial feedback.

3. Keep PRs or MRs issue-linked and reviewed according to [Product Repository Requirements](Repository_Requirements.md#issue-linked-workflow-requirements).

4. Verify acceptance criteria before merge according to [Process Requirements](Process_Requirements.md#acceptance-criteria).

5. Keep all relevant Assignment 4 and Assignment 5 tests, quality gates, CI checks, quality requirement tests, architecture documentation, and development-process documentation current when Sprint 5 changes the affected product areas.

## Part 7: Transition the Product and Release MVP v3

1. Complete the actual transition in Week 7.

2. The Week 7 result must be the final course version, `MVP v3`.

3. `MVP v3` must include:

   * the final product changes selected for Assignment 6
   * relevant fixes or improvements discovered during the Week 6 customer trial
   * updated customer-facing documentation and handover material
   * the final product access arrangement intended for course evaluation and customer use

4. Deploy or otherwise provide `MVP v3` so the customer and TA can access it.

5. Keep the relevant final product access artifact accessible until grading is complete.

6. Create a new SemVer release for the final Assignment 6 increment mapped to `MVP v3`.

7. The final release must:

   * use a SemVer tag prefixed with `v`
   * point to a commit on the protected default branch
   * have higher SemVer precedence than the Week 6 trial release
   * identify that it maps to `MVP v3`
   * link to the Sprint 5 milestone
   * link to current run or access instructions
   * link to `docs/customer-handover.md`
   * link to `reports/week7/README.md`
   * link to the public sanitized demo video

8. Update `CHANGELOG.md` by moving the final released entries from `[Unreleased]` into a dated SemVer section.

## Part 8: Confirm the Final Transition Outcome and Product Usefulness

1. During Week 7, confirm the final transition outcome with the customer or relevant stakeholder.

2. Ask the customer or relevant stakeholder explicitly whether they accept the current `docs/customer-handover.md` as sufficient for the reached handover level and current transition scope.

3. In `docs/customer-handover.md` and `reports/week7/README.md`, state explicitly which handover level has been reached:

   * `Ready for independent use`
   * `Independently used by customer`
   * `Deployed or operated on customer side`

4. All three levels are acceptable outcomes, but the team must state which one it actually reached by submission.

5. In `docs/customer-handover.md` and `reports/week7/README.md`, also state the customer-confirmation status as one of:

   * `Accepted`
   * `Accepted with follow-up items`
   * `Not yet accepted`

6. The customer-confirmation status is separate from the handover level. For example, a team may reach `Ready for independent use` while still being `Accepted with follow-up items`.

7. If the customer independently uses the product or deploys or operates it on their side, preserve inspectable evidence where practical. Sanitized public summary evidence belongs in the Week 7 report. Private recordings, exact timecodes, credentials, or customer-identifying details belong only in the private submission channel.

8. If stronger transition levels were not reached by submission, explain:

   * why not
   * whether the blocker is on the team side, customer side, or external
   * what evidence of readiness was still obtained
   * what remaining actions would still be needed

9. If the customer-confirmation status is `Accepted with follow-up items` or `Not yet accepted`, explain:

   * what follow-up items, requested changes, or blockers remain
   * whether the blocker is on the team side, customer side, or external
   * what evidence of transition readiness or usefulness was still obtained
   * what remaining actions would still be needed for full acceptance

10. If the customer does not respond by submission, include evidence that the team requested confirmation and treat the missing response as a blocker rather than as implicit acceptance.

## Part 9: Update and Execute User Acceptance Tests

1. Follow [Process Requirements](Process_Requirements.md#user-acceptance-tests) for maintained UAT semantics and [Artifact Requirements](Artifact_Requirements.md#uat-public-result-summary-artifact) for public/private handling.

2. Maintain the relevant active UAT scenarios in:

   ```text
   docs/user-acceptance-tests.md
   ```

3. Execute the relevant maintained UAT scenarios for the changed or customer-critical user-facing behavior during the Week 6 trial, the Week 7 transition confirmation, or both.

4. If one recorded meeting includes customer-executed UAT, transition discussion, and Sprint Review discussion, one recording, one transcript or notes file, and one summary may cover those activities. Include private exact timecodes where the private submission channel requires them.

5. In the Week 6 and Week 7 public reports, summarize:

   * which relevant UAT scenarios passed
   * which scenarios failed or still need changes
   * the most important feedback points received
   * the resulting PBIs or issues

## Part 10: Conduct Sprint Reviews for Week 6 and Week 7

1. Conduct a Sprint Review for Sprint 4 and another Sprint Review for Sprint 5 according to [Process Requirements](Process_Requirements.md#sprint-cadence-and-scrum-events).

2. The Week 6 Sprint Review must discuss at minimum:

   * the planned Sprint 4 Goal
   * the Week 6 trial release
   * customer-facing documentation review results
   * transition-readiness findings
   * customer trial or UAT results
   * resulting follow-up work for Sprint 5

3. The Week 7 Sprint Review must discuss at minimum:

   * the planned Sprint 5 Goal
   * delivered `MVP v3`
   * resolved and unresolved follow-up issues from Week 6
   * final transition status and usefulness
   * customer use, deployment, or operational status where relevant
   * remaining risks and post-course limitations where relevant

4. Follow [Artifact Requirements](Artifact_Requirements.md#sprint-review-artifacts) and [Artifact Requirements](Artifact_Requirements.md#recording-artifacts-and-timecodes) for the shared permission, transcript, notes, summary, and public/private handling rules.

5. If the Sprint Review uses a transcript, write the English transcript in:

   ```text
   reports/week6/sprint-review-transcript.md
   reports/week7/sprint-review-transcript.md
   ```

6. If the Sprint Review uses notes instead of a transcript, write detailed English notes in:

   ```text
   reports/week6/sprint-review-notes.md
   reports/week7/sprint-review-notes.md
   ```

7. Write the Sprint Review summaries in:

   ```text
   reports/week6/sprint-review-summary.md
   reports/week7/sprint-review-summary.md
   ```

8. If the same recorded meeting includes customer-executed UAT, transition discussion, and the Sprint Review discussion, one recording, transcript or notes file, and summary may cover those activities. Include private exact timecodes where the private submission channel requires them.

## Part 11: Conduct Sprint Retrospectives for Week 6 and Week 7

1. Conduct a Sprint Retrospective after the Week 6 Sprint Review and another after the Week 7 Sprint Review.

2. Write:

   ```text
   reports/week6/retrospective.md
   reports/week7/retrospective.md
   ```

3. Use the retrospective structure defined in [Artifact Requirements](Artifact_Requirements.md#retrospective-artifact).

## Part 12: Reflect on Week 6 and Week 7 and Report LLM Usage

1. Follow [Artifact Requirements](Artifact_Requirements.md#reflection-artifact) for the shared reflection structure.

2. Write:

   ```text
   reports/week6/reflection.md
   reports/week7/reflection.md
   ```

3. The Week 6 reflection should emphasize what the team learned from the trial release, the documentation review, the Week 6 customer meeting, and the discovered transition blockers.

4. The Week 7 reflection should emphasize what the team learned from follow-up maintenance, final transition work, customer usefulness feedback, and final delivery of `MVP v3`.

5. Follow [Artifact Requirements](Artifact_Requirements.md#llm-report-artifact) for the shared LLM report expectations.

6. Write:

   ```text
   reports/week6/llm-report.md
   reports/week7/llm-report.md
   ```

## Part 13: Prepare, Submit, and Rehearse the Presentation

1. Prepare a slide deck for the Assignment 6 presentation sequence.

2. Submit the slide deck as a PDF together with the Week 6 Moodle PDF submission by the end of Week 6, Sunday, `23:59`. Do not commit the slides to the public repository.

3. The Week 6 Moodle PDF must include a private link to a rehearsed presentation video. The rehearsed presentation video must show team members standing and presenting. The link must be accessible to instructors and must not be committed to the public repository.

4. The Week 7 Moodle PDF must include the updated slide deck as a PDF again. Slides may be refined after the Week 7 lab rehearsal, so resubmit the current slide version with the Week 7 Moodle PDF.

5. The Week 7 lab includes a required rehearsal presentation. This rehearsal is required preparation for Demo Day, but it is graded separately from Assignment 6.

6. The Week 7 lab rehearsal audience is the other students in the lab and the TA.

7. All team members must attend the Week 7 lab rehearsal and the Week 8 Demo Day presentation.

8. Each team member must present at least one slide during the Week 7 lab rehearsal and during the Week 8 Demo Day presentation.

9. Timing for the Week 7 lab rehearsal:

   * 5 minutes for the presentation
   * 3 minutes for Q&A
   * the rehearsal presentation will be stopped when the time runs out

10. Timing for Week 8 Demo Day:

    * 7 minutes for the presentation
    * 7 minutes for Q&A
    * the presentation will be stopped when the time runs out

11. Teams will present during Week 8 Demo Day.

12. Teams are grouped by customer or project and each team attends the assigned two-hour Demo Day presentation window.

13. The presentation must include a well-rehearsed demo under 2 minutes. Use a pre-recorded demo for the in-class presentation rather than a live demo.

14. Suggested presentation structure:

    * project context and target users: the customer, the problem, and why it matters
    * final product and the most important delivered requirements
    * well-rehearsed pre-recorded demo under 2 minutes
    * customer usefulness: what part of the solution is already in use by the customer and whether it is deployed or operated on the customer side
    * key engineering, process, and quality evidence in brief
    * remaining limitations and current handover status
    * team contribution and reflection: contribution of each team member, lessons learned, and what the team would do differently if starting again
    * links to the deployed product and the repository

15. Keep the presentation concise and narrative-driven. Do not rely on simply reading notes from a phone or laptop.

16. Rehearse for timing. Make sure the talk fits the Week 7 rehearsal limit and the Week 8 Demo Day limit.

17. Explain the problem and project context clearly. Do not assume that reviewers remember the project details or understand the customer context.

18. Explain clearly whether the customer is actually using the product already, and if not, why not.

19. During Q&A, the person who worked on the relevant part should answer where possible. One person should not answer all questions for the team.

## Part 14: Record a Public Sanitized Demo Video for MVP v3

1. Record a public sanitized demo video according to [Artifact Requirements](Artifact_Requirements.md#public-sanitized-demo-video-artifact). The public sanitized demo video is a product demonstration for everyone, not a private customer-trial recording and not the private rehearsal presentation video.

2. The public sanitized demo video must explain the final state of `MVP v3`, including what was improved, fixed, or added during Assignment 6.

3. Link the public sanitized demo video from `reports/week7/README.md` and from the final SemVer release mapped to `MVP v3`.

## Assignment Report in the Repository

Create the following public report structure:

```text
reports/
|-- week6/
|   |-- README.md
|   |-- sprint-review-summary.md
|   |-- sprint-review-transcript.md # if publication is permitted
|   |-- sprint-review-notes.md      # if recording or private sharing is refused
|   |-- reflection.md
|   |-- retrospective.md
|   |-- llm-report.md
|   `-- images/
`-- week7/
    |-- README.md
    |-- sprint-review-summary.md
    |-- sprint-review-transcript.md # if publication is permitted
    |-- sprint-review-notes.md      # if recording or private sharing is refused
    |-- reflection.md
    |-- retrospective.md
    |-- llm-report.md
    `-- images/
```

Use `reports/week6/README.md` as the canonical Week 6 public report for Sprint 4. Use `reports/week7/README.md` as the canonical Week 7 public report for Sprint 5 and as the final Assignment 6 submission index. The Week 7 report must link the complete relevant Week 6 evidence instead of duplicating it.

### Week 6 Report

`reports/week6/README.md` must contain direct links to every applicable required Week 6 repository file and external public artifact.

Include:

1. Project name and short description.
2. Link to the Product Backlog board or view.
3. Link to the Sprint 4 Backlog board or view.
4. Link to the Sprint 4 milestone.
5. Sprint 4 Goal, Sprint dates, and short scope summary.
6. Total Sprint 4 size in Story Points.
7. Summary of the Week 6 trial-release changes.
8. Link to the Week 6 product access artifact.
9. Link to current access or run instructions.
10. Link to `README.md`.
11. Link to `CONTRIBUTING.md`.
12. Link to `AGENTS.md`.
13. Link to `docs/customer-handover.md`.
14. Link to the hosted documentation site.
15. Summary of the customer-facing documentation review, including what the customer found clear, unclear, or missing.
16. Transition-readiness summary, including what must still happen in Week 7.
17. Customer feedback response table with feedback points and resulting PBIs or issues.
18. Explanation of feedback not yet addressed.
19. Link to `docs/roadmap.md`.
20. Link to the maintained quality, testing, architecture, development-process, and other customer-relevant documentation updated during Sprint 4.
21. Summary of relevant UAT or customer-trial results.
22. Link to the Week 6 SemVer trial release.
23. Link to `CHANGELOG.md`.
24. Link to the published Sprint Review transcript or a statement that publication was refused and the transcript is shared only through Moodle or another approved private instructor-sharing channel, or a link to the Sprint Review notes if recording or private sharing was refused.
25. Link to `reports/week6/sprint-review-summary.md`.
26. Link to `reports/week6/reflection.md`.
27. Link to `reports/week6/retrospective.md`.
28. Link to `reports/week6/llm-report.md`.
29. Summary of the current product status and expected Week 7 follow-up work.
30. Contribution traceability table mapping each team member to issues, PRs or MRs, review activity, testing, documentation, transition, or deployment work.
31. Embedded screenshots from `reports/week6/images/` for the Sprint milestone, Week 6 release, example reviewed issue-linked PR or MR, and other inspectable Week 6 evidence where public links may not be reliably inspectable.

### Week 7 Report

`reports/week7/README.md` must contain direct links to every applicable required Week 7 repository file and external public artifact. Keep it lighter than the Week 6 report by focusing on Week 7 follow-up work, final transition outcome, and final delivery rather than re-explaining the full project context.

Include:

1. Link to `reports/week6/README.md`.
2. Link to the Product Backlog board or view.
3. Link to the Sprint 5 Backlog board or view.
4. Link to the Sprint 5 milestone.
5. Sprint 5 Goal, Sprint dates, and short scope summary.
6. Total Sprint 5 size in Story Points.
7. Summary of the Week 7 follow-up maintenance and final `MVP v3` changes.
8. Link to the final product access artifact.
9. Link to current access or run instructions.
10. Link to `README.md`.
11. Link to `CONTRIBUTING.md`.
12. Link to `AGENTS.md`.
13. Link to `docs/customer-handover.md`.
14. Link to the hosted documentation site.
15. Final transition outcome summary stating which handover level was reached and which customer-confirmation status was received.
16. Summary of what was transferred, delegated, or otherwise made available during the final transition, with direct reference to the current `docs/customer-handover.md`.
17. Explanation of any remaining transition blockers, limitations, support expectations, or follow-up items identified by the customer.
18. Summary of customer-independent use, customer-side deployment, or customer-side operation evidence where available.
19. Customer feedback response table for Sprint 5 follow-up work.
20. Summary of relevant Week 7 UAT or customer-trial results.
21. Link to the final SemVer release mapped to `MVP v3`.
22. Link to `CHANGELOG.md`.
23. Link to the public sanitized demo video.
24. Demo Day preparation summary, including a brief note that the required Week 7 rehearsal preparation was completed.
25. Link to the published Sprint Review transcript or a statement that publication was refused and the transcript is shared only through Moodle or another approved private instructor-sharing channel, or a link to the Sprint Review notes if recording or private sharing was refused.
26. Link to `reports/week7/sprint-review-summary.md`.
27. Link to `reports/week7/reflection.md`.
28. Link to `reports/week7/retrospective.md`.
29. Link to `reports/week7/llm-report.md`.
30. Summary of the final product status.
31. Contribution traceability table mapping each team member to issues, PRs or MRs, review activity, testing, documentation, transition, deployment, or Demo Day preparation work.
32. Embedded screenshots from `reports/week7/images/` for the Sprint milestone, final release, final product access or deployment evidence where public inspection may be difficult, example reviewed issue-linked PR or MR, and other inspectable Week 7 evidence.

## Assignment Report on Moodle

Create two separate Moodle PDF submissions during Assignment 6. Each submission uses one PDF named:

```text
Team_Number_Project_Name.pdf
```

The Week 6 submission is due at the end of Week 6, Sunday, `23:59`. The Week 7 submission is due at the end of Week 7 according to the normal assignment deadline.

### Week 6 Moodle PDF

Include:

1. Project name and team number.
2. Table with team members, full names, university emails, GitHub or GitLab usernames, assigned Scrum roles, and assigned technical responsibilities.
3. Who did what during Sprint 4.
4. Who did not participate in any of the activities.
5. Commit-hash permalink to `reports/week6/README.md`.
6. Commit-hash permalink to the product repository tree at the Week 6 submission commit. The commit must be on the protected default branch.
7. Link to the Week 6 private recording used for customer trial, transition-readiness discussion, Sprint Review, UAT, or any combination of those activities.
8. Exact private timecodes where one recording covers multiple required activities.
9. Sanitized English Sprint Review transcript if it could not be published but private instructor sharing was permitted, or detailed English Sprint Review notes if recording or private instructor sharing was refused.
10. Exact private access instructions for the Week 6 product access artifact, including limited-permission test credentials if needed.
11. Link to the rehearsed presentation video showing team members standing and presenting.
12. Any instructor-only evidence that must not be committed publicly, such as private consent, access, credential, or customer-identifying evidence.

### Week 7 Moodle PDF

Include:

1. Project name and team number.
2. Table with team members, full names, university emails, GitHub or GitLab usernames, assigned Scrum roles, and assigned technical responsibilities.
3. Who did what during Sprint 5.
4. Who did not participate in any of the activities.
5. Commit-hash permalink to `reports/week7/README.md`.
6. Commit-hash permalink to the final product repository tree at the Week 7 submission commit. The commit must be on the protected default branch.
7. Link to the Week 7 private recording used for final transition confirmation, Sprint Review, UAT, or any combination of those activities.
8. Exact private timecodes where one recording covers multiple required activities.
9. Sanitized English Sprint Review transcript if it could not be published but private instructor sharing was permitted, or detailed English Sprint Review notes if recording or private instructor sharing was refused.
10. Exact private access instructions for the final product access artifact, including limited-permission test credentials if needed.
11. Private proof of the Week 7 transition-confirmation request and response tied to the current `docs/customer-handover.md`. Any written confirmation is acceptable. A screenshot of the message exchange is a sufficient example. If the customer did not confirm acceptance or did not respond, include the request and any reply or other private evidence of that unresolved status.
12. Any instructor-only evidence that must not be committed publicly, such as private consent, access, credential, or customer-identifying evidence.

All public evidence must be indexed in `reports/week6/README.md` and `reports/week7/README.md`. Keep the private Week 6 and Week 7 evidence in their respective Moodle PDF submission wrappers rather than merging them into one final private report.

> [!IMPORTANT]
> Verify all public and private links before submission. Public links must be publicly viewable but not publicly editable. Private Moodle links must be accessible to instructors. Required artifacts and links must remain accessible until the assignment has been graded.

### Submission Procedure

* By the end of Week 6, Sunday, `23:59`, submit the Week 6 PDF through Moodle together with the slide-deck PDF.
* By the end of Week 7, submit the Week 7 PDF through Moodle together with the updated slide-deck PDF.
* Include the private link to the rehearsed presentation video inside the Week 6 Moodle PDF rather than as a separate uploaded file.
* One Week 6 PDF, one Week 7 PDF, one Week 6 slide-deck PDF, and one Week 7 slide-deck PDF per team are required.

### AI and LLM Usage

You may use AI tools, LLMs, or other productivity tools. However:

1. Explicitly report which tools were used and how.
2. The submission must contain meaningful analysis and original team effort.
3. Do not submit filler text, generic AI-generated content, or unnecessary explanations.

Failure to disclose AI usage or submitting low-value AI-generated content may result in a failing grade.
