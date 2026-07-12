# Sprint 4 Review Transcript - Week 6

**Date:** 2026-07-12

**Public handling:** sanitized English transcript. Participant identities, private recording link, exact timecodes, and any customer-identifying details belong only in the Week 6 Moodle PDF.

---

## Opening

**Presenter:** Let's start with the product demonstration and then cover the transition-readiness questions required for the course.

**Customer:** I am here and ready. The camera is not necessary; the screen demonstration is enough.

## Product Walkthrough

**Presenter:** The structure has changed and the product is operational. We added Russian and English language selection and made the UX clearer: the operator describes the business, uploads contacts, reviews the first generated message, and then launches the bot so it writes to leads.

**Presenter:** In the business section, we can add, edit, delete, open, and view businesses. Each business has a description, target audience, manager goal, success criteria, and behavior style. The funnel can also be edited: stages, reminders, timezone, and working hours are configurable so the manager does not reply at inappropriate times.

**Presenter:** Campaigns can be paused or deleted. We will upload contacts, select a business, review generated first messages, and launch a test campaign.

**Presenter:** The bot generated several first messages. They are roughly adequate and can be regenerated before launch. We also focus on Telegram safety: anti-spam filters, limits on how many messages one account sends, and staggered sending so the account is not blocked.

## Live Conversation Behavior

**Presenter:** A live outbound message has been sent. The bot writes like a human: it uses typing delay and does not reply instantly. We also added handling for cases where a lead sends several messages in a row; the bot groups them and processes them together rather than answering every message separately.

**Presenter:** One reply still showed a role-consistency problem where the bot went out of character. This needs more work. We also tested hostile/off-topic prompts such as asking the bot to solve unrelated tasks. In most cases the bot resisted and steered the conversation back or politely ended it.

**Customer:** Everything is clear and generally adequate. I would like to test it myself. Please send me the bot.

**Presenter:** Yes, we will send the bot link.

## Lead Discovery

**Customer:** How is parsing/search working?

**Presenter:** Lead discovery is a new feature. The operator provides target audience and search criteria. Instead of paying for a TGStat-style API, the system uses Telegram data visible to the configured seller account in public groups/chats. The manager account can join relevant thematic groups, and the system searches visible public messages to find potential leads.

**Customer:** Do the groups need to be loaded manually?

**Presenter:** For now, yes. The account must join relevant groups manually. Automating discovery of group lists would require a paid external source. For MVP, manually joining 50-100 relevant groups is workable.

**Presenter:** The first narrow query did not return enough results. After broadening the query, the system found relevant public groups and messages. The system can export results as CSV, and that CSV is compatible with the campaign upload flow.

**Customer:** It looks adequate, but the main question is quality.

## Model / Prompt Quality

**Customer:** The issue with generation may be the model. It sometimes goes out of role or produces system-like output. If the API supports routing to other models, try testing alternatives.

**Presenter:** Understood. We will check what model/provider is currently used and evaluate alternatives through the routing API if available.

## Transition-Readiness Discussion

**Presenter:** What do you want to see improved next?

**Customer:** I want better results from search/parsing and stronger message quality. I also want less manual setup. Ideally, I describe the business in detail, the system finds suitable leads, shows that it found around 50 leads, and then I can launch the campaign without approving and checking every step.

**Presenter:** So the detailed business description is acceptable, but after that you want the system to handle lead discovery and campaign launch with minimal additional configuration.

**Customer:** Yes. The detailed business description is fine. After that I do not want to approve and verify everything repeatedly.

**Presenter:** Have you independently tried the Week 6 trial release yet?

**Customer:** Not yet.

**Presenter:** What is needed for the product to remain useful after the course when the team stops supporting it?

**Customer:** Bring parsing/search quality to a good level and make campaign start require minimal involvement.

## Recording Permission

**Presenter:** Can we save this recording and share it with instructors for the course submission?

**Customer:** Yes, I do not mind. Some fragments may need to be cut if necessary.

**Presenter:** Thank you. We will continue improving the product and send the bot access.

**Customer:** Good. If it does not start when I test it, I will message the team. I will also send approximate feedback today.
