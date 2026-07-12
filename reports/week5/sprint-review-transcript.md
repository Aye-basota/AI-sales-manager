# Sprint Review & UAT Session Transcript — Week 5 / Sprint 3

**Participants:** Daniel (development team), Mark (customer / Product Owner stakeholder)
**Date:** 2026-07-05
**Format:** Combined recorded session — customer-executed UAT followed by Sprint Review discussion
**Consent:** Customer explicitly confirmed the recording and transcript may be used for the team's course submission.

> Note: This transcript is translated from the original Russian-language session for the public repository. The private recording itself is submitted separately via Moodle, together with Moodle-only timecodes marking the UAT and Sprint Review segments, per Artifact Requirements.

---

## Introduction

**Daniel:** We moved the bot to our production server — effectively a VPS — so it can run 24/7 and reply to you at any time. We also reworked the dialogue logic itself to make it more natural and human-like, in order to guide the person more toward making a purchase. That's the core of what changed this sprint. Let's run the old regression scenario first, then two new ones.

## UAT — Regression Scenario: Existing Q&A Behavior

**Daniel:** I'm sending you the contact/company file now — pick the "motor oils" test company so we can check pricing questions.

**Mark:** Got it, sent. Let's see if it replies.

*(Bot replies, referencing the customer's business segment and known pain points around supply and demand forecasting.)*

**Mark:** All good, it replies properly, same as before.

**Daniel:** Great — so after the migration nothing broke. Next, let's check the bot still behaves correctly with an off-topic message.

**Mark:** Sent something unrelated to the topic — it steered me back to the relevant subject. Behaves appropriately.

**Daniel:** Good, that's the important baseline confirmed.

## UAT — New Scenario 1: 24/7 Availability via VPS

**Daniel:** Now the new part. Availability should now be 24/7 — nothing is running on my machine or teammates' machines anymore. Previously the bot only worked while my computer was on; now it should work at any time, evening or morning.

**Mark:** Understood, let's test it.

**Daniel:** It's about 10 PM right now — I can turn off Docker entirely on my side and you can still test it.

*(Daniel shuts down the local Docker environment.)*

**Daniel:** Send another message — ask it to elaborate on the oil products, for example.

**Mark:** Docker is off on your end, and yes — it still replies, all working, great.

## UAT — New Scenario 2: Natural Conversational Flow / Lead Nurturing

**Daniel:** This scenario covers the reworked prompts — the goal was for the bot to not just answer questions but actively guide the conversation toward a booking or purchase, asking clarifying questions and suggesting next steps.

**Mark:** Let me ask about pricing for maintenance and an oil change.

*(Bot responds with clarifying questions and consultative guidance rather than a flat price.)*

**Mark:** It's speaking more naturally now. Before it just gave a price; now it asks clarifying questions and leads toward booking.

**Daniel:** Great, that matches what we were aiming for.

## Closing Feedback

**Daniel:** Thank you, Mark. Overall, are you satisfied? Anything you'd like us to improve next?

**Mark:** Overall, great work, everything works well. The one thing I didn't like is the admin panel interface — it's not very convenient. When launching a new campaign and uploading contacts, once you click through a step (e.g., launching the campaign), there's no way to go back and edit or fix something. The interface should be made more intuitive.

**Daniel:** Understood, noted. We'll address this in Sprint 4.

**Mark:** Also — yes, you can use this recording and transcript for your coursework.

---

## Summary of Outcomes (for Sprint Review cross-reference)

- Regression: existing Q&A and off-topic handling confirmed unaffected by the VPS migration.
- New: 24/7 availability via VPS deployment confirmed working with local dev environment fully shut down.
- New: reworked conversational/lead-nurturing prompts confirmed to produce more natural, consultative responses that guide toward booking.
- Feedback received: admin panel workflow lacks a "back"/edit option once a step (e.g., campaign launch) has been confirmed; interface needs to be more intuitive.
- Customer consent obtained to use the recording and this transcript for course submission.
