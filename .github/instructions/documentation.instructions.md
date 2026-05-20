---
applyTo: "**/*.md,docs/**"
---
# Documentation philosophy

These principles apply to documentation in all its forms—READMEs, guides, doc comments in code, or anything else that explains how things work. The goal is documentation that adds understanding without adding burden.

## Durability
Document what's stable; let volatile details live in code where they stay current automatically.

The underlying question is: *will this outlast the next refactor?* Concepts, rationale, and mental models tend to be durable. Implementation details, file structures, and argument lists tend to change—and when they do, separate documentation becomes a liability rather than an asset.

**Example:** A CLI tool's README benefits from explaining what the tool does and when to use it. But documenting every flag is wasteful when the code already has `--help` with the same information—and the docs will drift as flags evolve. An illustrative example of a common workflow adds lasting value; an exhaustive reference duplicates what the code already provides.

## Single source of truth

Information should live in exactly one place. When it needs to appear elsewhere, derive it rather than duplicate it.

**Why this matters:** Duplicated content drifts apart over time. Updates require finding all copies. Conflicting information erodes trust. The maintenance burden grows with every copy, and eventually nobody knows which version is authoritative.

**How to maintain it:** When the same information needs to appear in multiple places, use automatic syncing or linking rather than maintaining separate copies manually. For example, this repository syncs agent instruction files from human-readable documentation—one source, automatically derived. When referencing external information, link to the authoritative source rather than duplicating content that will drift.

## Self-documentation

Well-structured code and clear naming often document themselves. The question is whether additional documentation adds understanding or just adds maintenance burden.

**Signal vs. noise:** A function signature is already documentation—it tells you the name, parameters, and return type. A doc comment that restates what a developer can glean from the signature is noise: it adds maintenance burden without adding understanding. Save documentation for what isn't obvious from the code: the *why*, the gotchas, the non-obvious constraints.

**Example — README as orientation vs. index:**

```markdown
<!-- Just an index—duplicates what the file browser shows, goes stale -->
## Contents
- [Component A](component-a/)
- [Component B](component-b/)
- [Component C](component-c/)

<!-- Adds understanding—explains the concept, helps readers orient -->
## Organization

Components are organized by domain. Each has its own folder with
a README covering its public API. Start with Component A if you're
new—it demonstrates the core patterns used throughout.
```

## Audience awareness

Documentation serves multiple audiences: humans learning the codebase and AI agents performing tasks. What works for one generally works for the other—clear rationale, concrete examples, and explicit constraints help both humans building mental models and agents shaping their outputs. Write for humans; agents will benefit too.

## Cohesion
Documentation lives with its subject matter—same folder, same repo, same ownership.

**Why this matters:** Ownership becomes clear: whoever maintains the code maintains the docs. Context is preserved: readers find documentation where they're already working. Updates happen naturally: changes to code prompt changes to adjacent docs.

**Example:** A library's documentation belongs in the library's README, not in a central wiki maintained by a different team. When documentation lives with its subject, the people closest to the code—who understand it best and notice when it changes—are the ones responsible for keeping the docs current.

## Economy
Strive for broad coverage from fewer elements. The goal is efficiency—maximizing the value of each piece of documentation while minimizing maintenance burden and cognitive load.

This principle connects the others: Durability says *what* to document (stable things), Single Source of Truth says *where* (one place), Cohesion says *with what* (its subject). Economy asks: given those constraints, how do we cover the most ground with the least overhead?

## Generality
Favor general principles over exhaustive rules. A principle illustrated by a well-chosen example helps readers internalize the underlying *why*—enabling them to handle situations the author never anticipated.

**Why this works:** Understanding scales; checklists don't. Readers who grasp the rationale can extrapolate to novel cases. This is equally true for humans building mental models and agents shaping their outputs.

**Why exhaustive enumeration falls short:** No list can anticipate every case. Enumeration requires constant maintenance, invites compliance without understanding, and leaves readers stuck when they encounter unlisted situations.

**This isn't about being terse.** Elaborate where it builds understanding—explaining rationale, showing how things play out, providing examples that build intuition. It becomes counterproductive when it merely catalogs cases instead of conveying the underlying pattern.

**Illustrative over prescriptive examples.** A few well-chosen examples illuminate a concept broadly—they show the principle in action and help readers recognize similar situations. Prescriptive examples that try to enumerate specific cases ("do X in situation A, Y in situation B") defeat the purpose: they become another checklist to maintain and leave readers stuck when they encounter situation C.

**A few examples of how this manifests:**
- Standards and practices that align mindset and culture land better when they transfer the underlying *why*. Readers who internalize rationale can apply it to situations the author never anticipated.
- Tool documentation that enumerates every flag or argument faces a Durability problem—it duplicates what's in the code and goes stale. Illustrative examples that accelerate ramp-up add more lasting value.
- Reference material that duplicates authoritative sources faces a Single Source of Truth problem. Linking and adding contextual orientation keeps things current.
