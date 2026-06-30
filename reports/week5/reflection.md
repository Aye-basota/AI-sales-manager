# Week 5 Reflection

## Learning points

- **Architecture documentation:** Producing explicit static, dynamic, and deployment views forced the team to articulate design decisions that had previously existed only in code. Writing the component diagram revealed that the `DialogManager` carries too many responsibilities and is a candidate for decomposition in a future Sprint.

- **ADRs:** Recording Architecture Decision Records turned out to be more useful than expected. Writing the "Why" section for each ADR made the team aware of assumptions that had not been previously stated — for example, the choice of pyrofork over the official Bot API was implicit until documented.

- **Git workflow documentation:** The gitGraph diagram made the branching strategy visible to all team members. Before this Sprint, not everyone was following the `<issue-number>-short-description` naming convention. After the diagram was shared, branch names became consistent.

- **Configuration management:** Auditing the `.gitignore` and `.env.example` during this Sprint revealed that a Telegram session file had been accidentally committed in an early commit. It was purged from history using `git filter-repo`. This is now explicitly covered in the Definition of Done.

- **MVP v2 delivery:** Delivering operator takeover and inbound rate limiting required coordinating changes across three layers (API, core logic, admin bot). The architecture documentation helped the team agree on where the `is_paused_by_operator` flag should live before implementation started.

- **Customer review:** The customer confirmed that manual operator takeover addresses the main gap from MVP v1. The customer also requested a funnel stage distribution chart in analytics, which was added to the backlog as a Sprint 4 item.

- **Process maturity:** The team now consistently links PRs to issues, writes acceptance criteria before starting implementation, and updates the CHANGELOG. These habits were not yet consistent in Sprint 1.

## Validated assumptions

- **Feature-branch isolation works:** Parallel development on `45-operator-takeover` and `46-rate-limiting` proceeded without conflicts because the two features touch different modules.
- **PlantUML/Mermaid diagrams are maintainable:** Keeping diagram sources in the repository alongside the code makes them easy to update when the architecture changes — unlike exported screenshots, which become stale immediately.
- **Rate limiting reduces Telegram ban risk:** Initial testing showed that enforcing a daily message limit per account brings outreach within Telegram's recommended per-account limits.

## Friction and gaps

- **No live deployment yet:** MVP v2 is runnable locally and via Docker, but the team still does not have a persistent hosted instance. This makes the customer review dependent on a local demo, which is less reliable.
- **Architecture complexity is growing:** The `DialogManager` now handles message routing, LLM calls, funnel transitions, and operator state. This is a coupling risk that should be addressed by extracting a `FunnelService` in Sprint 4.
- **CI pipeline is local only:** Tests run locally. GitHub Actions CI is not yet configured. This is listed as a Sprint 4 action point.
- **UAT coverage is limited:** The team executed UAT scenarios manually with the customer. Automating at least the happy-path UAT scenarios would provide faster feedback.

## Planned response

- Sprint 4 will introduce GitHub Actions CI so every PR is validated automatically. See [`docs/roadmap.md`](../../docs/roadmap.md).
- Extract `FunnelService` from `DialogManager` to reduce coupling. This will be created as a new PBI in the next Sprint.
- Set up a persistent staging environment on a VPS or cloud provider so customer demos are always live.
- Add calendar integration (`meeting_intent` → Google Calendar / Calendly) as the next major feature after architecture hardening.
