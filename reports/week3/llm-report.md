# LLM Usage Report

## Tools Used

The team used the following AI/LLM-powered tools during Assignment 3:

- **GitHub Copilot / LLM assistant** — code suggestions, refactoring, documentation drafting, and test scaffolding.
- **ChatGPT / Claude** — drafting user stories, acceptance criteria, report sections, and brainstorming architecture decisions.

## How LLMs Were Used

1. **Code generation and review**
   - LLM-assisted drafting of the DashScope provider integration in `app/llm/engine.py`.
   - Refactoring of `app/config.py` to support multiple LLM providers.
   - Schema fix for `sales_funnel` from `Dict` to `List`.

2. **Documentation and reports**
   - Drafting `reports/week3/reflection.md`, `reports/week3/llm-report.md`, and `docs/definition-of-done.md`.
   - Updating `CHANGELOG.md` and `README.md` sections.

3. **Test scaffolding**
   - Suggestions for unit tests and fallback/retry scenarios in `tests/test_llm_engine.py`.

4. **Process artifacts**
   - Templates for GitHub issue templates and pull request template.
   - Guidance on SemVer release workflow and changelog structure.

## Human Oversight

All LLM-generated code and text were reviewed, edited, and tested by team members before commit. No secrets or API keys were generated or committed by AI tools. The team retains full responsibility for the final content.

## Disclosure

This report itself was drafted with LLM assistance and then reviewed by the team for accuracy and completeness.
