=============================================================================
UAT 1: Verify 24/7 Production Availability via VPS Deployment
=============================================================================
Description: 
Ensures the MVP v2 is successfully deployed to the production VPS and 
can reliably handle user interactions at any time, independently of a 
local development environment.

Acceptance Criteria:
- GIVEN the AI assistant application is fully deployed to the production VPS
- WHEN a user sends a message to the assistant via the messaging interface 
  outside of standard business hours (e.g., at 3:00 AM)
- THEN the system should successfully receive and process the request
- AND the AI assistant should reply with a relevant response within the 
  defined latency threshold (e.g., < 3 seconds)
- AND no server timeouts, 502 Bad Gateway, or "application sleeping" 
  errors should occur.

=============================================================================
UAT 2: Verify Natural Conversational Flow and Structured Lead Nurturing
=============================================================================
Description: 
Ensures the enhanced system prompts successfully guide the AI to build 
trust through conversation rather than immediately pushing a hard sale 
or funnel link to the user.

Acceptance Criteria:
- GIVEN a new, unrecognized user initiates a chat with the AI assistant
- WHEN the user asks top-of-funnel questions (e.g., asking for general 
  information or expressing a common pain point)
- THEN the AI assistant should respond using a natural, empathetic tone 
  that directly addresses the user's specific question
- AND the assistant must NOT output a direct purchase link or aggressive 
  sales call-to-action in its initial replies
- AND ONLY AFTER a predefined nurturing condition is met (e.g., 3 successful 
  value-adding exchanges or the user explicitly asking for pricing/next steps)
- THEN the assistant should smoothly transition the user into the structured 
  sales funnel.
=============================================================================
