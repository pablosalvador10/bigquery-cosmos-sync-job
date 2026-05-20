---
description: Documentation philosophy for READMEs, guides, markdown docs, and code comments.
applyTo: '**/*.md,docs/**'
---

# Documentation Philosophy

## Durable
- Document durable concepts, rationale, and mental models.
- Avoid duplicating volatile implementation details that drift quickly.

## Single Source Of Truth
- Keep each fact authoritative in one location.
- Link to source docs instead of duplicating large references.

## Self-Documentation
- Prefer clear naming and structure first.
- Add docs where code alone cannot convey intent, constraints, and trade-offs.

## Cohesion
- Keep docs next to the code they describe.
- The team that owns code owns its docs.

## Economy
- Favor fewer high-value docs over many low-signal docs.
- Use examples to teach principles rather than long checklists.

## Practical Rules
- Keep docs concise, concrete, and updated with behavior changes.
- If API contracts change, update API docs in the same change.
- Do not include secrets or environment-specific credentials in docs.
