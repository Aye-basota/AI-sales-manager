# Development Process and Configuration Management

This document describes how the AI Sales Manager team develops, reviews, and releases the product.

## Git Workflow

*(Insert Mermaid `gitGraph` diagram here and explain the workflow.)*

## Definition of Done

See [`docs/definition-of-done.md`](definition-of-done.md).

## Configuration Management

- Environment variables are documented in `.env.example`.
- Secrets and credentials are never committed to the repository.
- CI/CD configuration lives in `.github/workflows/`.

## Sprint Workflow

- Sprint Planning produces a Sprint Goal and selected PBIs.
- Work is tracked through GitHub issues and milestones.
- Changes are made via issue-linked Pull Requests reviewed by another team member.
- Releases use Semantic Versioning and are created from the protected `main` branch.

> This file is a placeholder maintained by the process team. Replace with full development-process content for Assignment 5 Part 3.
