# Sprint 4 Review Notes - Week 6

**Date:** 2026-07-12

**Participants / roles:** development team and customer/stakeholder.

**Format:** live product walkthrough, customer Q&A, transition-readiness discussion, and informal UAT-style observations.

**Recording/publication handling:** the public repository uses sanitized notes and summary. Private recording links, exact timecodes, and any customer-identifying details belong only in the Week 6 Moodle PDF.

## Scope Reviewed

- Business/script setup through the Telegram Admin Bot.
- Contact CSV upload and campaign launch flow.
- Generated first-message preview and regeneration.
- Campaign start and anti-spam/rate-limit behavior.
- Live outbound/inbound conversation behavior, including typing delay and multi-message handling.
- Telegram lead discovery through public/group message search and CSV export.
- Current transition readiness and what must happen before final Week 7 handover.

## Customer Trial Observations

- The customer saw the current product run through an end-to-end campaign-style workflow.
- The customer asked to receive access and try the bot independently after the call.
- Lead discovery returned real Telegram accounts/messages in the demonstrated groups, but the customer judged result quality as an area needing improvement.
- The bot still showed occasional risk of breaking character or producing weak role-consistency output.
- The customer wanted less manual setup before starting a campaign.

## Feedback And Decisions

| Feedback / decision | Resulting action |
|---|---|
| Lead discovery needs better quality. | Carry into Sprint 5 as an explicit transition action; related existing issue: [#28](https://github.com/Aye-basota/AI-sales-manager/issues/28). |
| Campaign launch should require less manual checking after the business is described. | Carry into Sprint 5 as a setup-friction action; related existing issue: [#68](https://github.com/Aye-basota/AI-sales-manager/issues/68). |
| Prompt/model quality still needs improvement. | Track through prompt configuration/versioning work: [#55](https://github.com/Aye-basota/AI-sales-manager/issues/55). |
| Independent customer trial access is needed. | Public Week 6 bot access artifact recorded: [@salesmanager228_bot](https://t.me/salesmanager228_bot). Independent-use evidence remains a Week 7 follow-up. |

## Transition-Readiness Findings

- The product is not yet shown as deployed or operated on the customer side.
- Independent customer use of the Week 6 trial is not yet publicly evidenced.
- The handover documentation is useful for technical setup and now points to the public Week 6 bot access artifact.
- Written customer confirmation is still needed for Week 7 final handover.

## Private Submission Items

- Private recording link and exact timecodes for the Sprint Review / customer trial / transition-readiness discussion.
- Any customer-identifying consent or confirmation evidence.
- The public product-access screenshot is sanitized in `reports/week6/images/product-access.png`; any screenshot with credentials, private chats, phone numbers, or customer-identifying details must stay private.
