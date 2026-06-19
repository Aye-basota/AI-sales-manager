# Week 3 Reflection

## Learning points

- **Product Backlog migration:** Moving user stories from a static markdown file to issue-based tracking makes status and ownership explicit, but requires discipline to keep `docs/user-stories.md` synchronized.
- **Refinement and estimation:** Breaking MVP v1 into small, implementable PBIs (funnel schema, prompt generation, scheduler integration, admin bot) made the scope clearer and easier to estimate.
- **Sprint Planning:** Using a Sprint milestone as the authoritative container kept the Sprint Backlog inspectable and linked every PBI to a concrete time box.
- **MVP v1 delivery:** The configurable sales funnel showed that end-to-end integration (DB → schema → prompts → bot → scheduler → tests) is more work than isolated features, but also where the real value is.
- **Customer review:** Presenting a working increment early surfaced the need for operator takeover and better analytics—feedback that was not obvious from the backlog alone.
- **Release preparation:** SemVer tagging, changelogs, and merge-commit workflows create a reliable audit trail for instructors and stakeholders.

## Validated assumptions

- **OpenAI-compatible providers are interchangeable:** Adding DashScope confirmed that the existing `httpx`/`chat/completions` abstraction works with another provider by changing only URL, key, and model names.
- **Funnel-aware prompts improve message relevance:** Initial tests show that stage-specific instructions keep first messages short and CTAs timed correctly.
- **Schema mismatch is a real risk:** `sales_funnel` was declared as a dict in the schema but used as a list in the core; fixing it early prevented runtime errors.

## Friction and gaps

- **No GitHub CLI access:** Issues, milestones, and projects must be created manually in the web UI, which is slower than scripting.
- **Missing live deployment:** MVP v1 is runnable locally and via Docker, but there is no permanent hosted instance yet.
- **Limited customer evidence:** The public video demonstration and sanitized transcript still need to be recorded and uploaded.
- **Operator tools gap:** Manual dialog takeover and funnel stage override are not implemented; they are planned for Sprint 2.
- **Process overhead:** Writing acceptance criteria, updating changelogs, and maintaining traceability adds overhead that the team is still getting used to.

## Planned response

- Sprint 2 will focus on operator takeover, inbound rate limiting, Redis conversation locks, and funnel analytics. See [`docs/roadmap.md`](../../docs/roadmap.md).
- Create GitHub Issues for US-05, US-06, US-07, and US-09 and assign them to Sprint 2 milestone once it is created.
- Record and publish a sanitized two-minute MVP v1 demonstration video.
- Set up a persistent staging environment for customer demos.
