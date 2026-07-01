---
name: ubiquitous-language
description: >
  Scan the codebase to extract domain terminology and create a Ubiquitous Language document
  (from Domain-Driven Design). Use this to reduce AI verbosity, improve alignment between
  planning and implementation, and give the AI a shared vocabulary with the codebase.
  Run this at the start of any project or when the AI seems to be "talking across purposes".
---

# Ubiquitous Language Skill

## Purpose

From Domain-Driven Design (DDD): create a shared vocabulary between you, the AI, domain experts,
and the code itself. Matt Pocco describes this as "a powerhouse" that:

- Allows the AI to think in a less verbose way
- Makes implementation more aligned with what was planned
- Reduces communication overhead between you and the AI

> "Conversations among developers and expressions of the code and conversations with domain experts
> are all derived from the same domain model." — Eric Evans, Domain-Driven Design

## Instructions

### Step 1: Scan the Codebase

Use a sub-agent to explore the codebase and collect:

- All class names, function names, and module names
- Variable names that appear to be domain concepts (not generic ones like `i`, `tmp`, `data`)
- Comments that explain domain concepts
- Any existing documentation that uses technical terms
- Error messages and log strings that reference domain concepts

### Step 2: Identify Domain Clusters

Group the collected terms into **bounded contexts** — natural clusters of related concepts.
For example:

- "Order lifecycle" (submit, fill, cancel, reject)
- "Market data" (OHLCV, bid, ask, spread, depth)
- "Infrastructure" (route, endpoint, payload, timeout)

### Step 3: Generate the Ubiquitous Language Document

Create `UBIQUITOUS_LANGUAGE.md` in the project root with this structure:

```markdown
# Ubiquitous Language — [Project Name]

> This document defines the shared vocabulary for this codebase.
> Use these exact terms in code, comments, plans, and AI conversations.

## [Bounded Context 1: e.g., Trading]

| Term | Definition | Used In | Synonyms to Avoid |
|------|-----------|---------|-------------------|
| Order | ... | ... | ... |

## [Bounded Context 2: e.g., Infrastructure]

| Term | Definition | Used In | Synonyms to Avoid |
|------|-----------|---------|-------------------|
```

### Step 4: Validate with User

Present a draft and ask:

- "Are these terms used consistently?"
- "Are there terms we use differently in different contexts?"
- "Are there business terms missing from the codebase?"

### Step 5: Keep It Current

- Update the document whenever new domain concepts are introduced
- Reference the document in your system prompt or CLAUDE.md
- Include it as context in grilling sessions and PRD drafts

## Rules

- Use the exact terms from the codebase — don't invent cleaner-sounding names
- Mark synonyms/aliases explicitly to avoid confusion
- Include the file/module where each term is primarily used
- Don't include generic programming terms (class, function, etc.)
- Keep it concise — this is a reference, not documentation
- Pass this document to every grilling session and PRD-writing session as context

## Example: When to Run This

- New contributor joining a complex project
- AI keeps using wrong terminology (using "order" when you mean "fill")
- Planning sessions feel misaligned with the resulting code
- Two modules use different names for the same concept (naming drift)
