---
name: prd-to-issues
description: >
  Break a PRD into independently grabbable implementation tickets using vertical slices (tracer bullets).
  Creates a kanban board of issues with dependency/blocking relationships and AFK vs human-in-loop classification.
  CRITICAL: Issues must be vertical slices, NOT horizontal layers.
---

# PRD to Issues Skill

## Purpose
Transform the destination document (PRD) into a **journey map** — a set of concrete, independently implementable tickets that:
- Are ordered by dependency (blocking relationships)
- Each touch multiple layers (vertical slices, not horizontal)
- Are classified as AFK or human-in-the-loop
- Are small enough to fit in the LLM smart zone (~100K tokens)

## The Most Important Rule: Vertical Slices

### ❌ BAD — Horizontal Slices (what AI naturally produces)
```
Issue 1: Create all database schema changes
Issue 2: Build all service/business logic
Issue 3: Add all frontend components
```
Problem: You don't know if anything works until Issue 3 is complete. No feedback loop.

### ✅ GOOD — Vertical Slices (tracer bullets)
```
Issue 1: Award points for lesson completion, visible on dashboard
  → Schema change + service logic + dashboard counter = end-to-end feedback
Issue 2: Add streak tracking, visible on dashboard
  → New streak table + streak service + streak badge on dashboard
```
Each issue crosses ALL layers. You can test it end-to-end when it's done.

> **Tracer Bullet Analogy**: Anti-aircraft gunners attach phosphor to every 6th bullet so they can SEE where they're aiming in the dark. Without it, they shoot blind. Horizontal coding = shooting blind. Vertical slices = tracer bullets = immediate feedback.

## Instructions

### Step 1: Locate the PRD
Find `./issues/prd-[feature-name].md` or ask the user where the PRD is.

### Step 2: Explore the Codebase (if fresh session)
Use a sub-agent to understand the layer structure:
- What are the database/schema layers?
- What are the service/API layers?
- What are the UI/frontend layers?
- What are the cross-cutting concerns (auth, logging, etc.)?

### Step 3: Draft Vertical Slice Issues
For each proposed issue, verify it contains work across AT LEAST:
- One data layer change (schema, migration, or data access)
- One business logic change (service, handler, or controller)
- One observable output (UI element, API response, or log entry a human can verify)

If an issue only touches one layer → it's horizontal → split or merge it.

### Step 4: Present the Kanban Board
Show the user a summary table before creating files:

```
| # | Title | Blocked By | Type | Vertical Slice? |
|---|-------|------------|------|-----------------|
| 1 | Award points for lesson completion, visible on dashboard | none | AFK | ✅ |
| 2 | Streak tracking with dashboard badge | #1 | AFK | ✅ |
| 3 | Retroactive points backfill for existing users | #1 | AFK | ✅ |
| 4 | Gamification settings page (admin) | #1, #2 | human-in-loop | ✅ |
```

Ask: "Does this look right? Are any slices too horizontal?"

### Step 5: Create Issue Files
After user confirms, write each issue to `./issues/issue-[N]-[slug].md`:

```markdown
# Issue [N]: [Title]

**Type**: AFK | human-in-loop
**Blocked by**: Issue [X], Issue [Y] (or "none")
**Estimated scope**: Small | Medium | Large

## Objective
[One sentence: what will exist that didn't before, and how will you verify it?]

## Vertical Slice Scope
- **Data layer**: [what schema/migration/query changes]
- **Service layer**: [what business logic changes]
- **UI/API layer**: [what the user/caller will see when done]

## Acceptance Criteria
- [ ] [Testable criterion 1]
- [ ] [Testable criterion 2]
- [ ] [Testable criterion 3]

## Implementation Notes
[Relevant context from the PRD and grilling session that the implementing agent needs]

## Testing Requirements
[From the PRD testing decisions — what tests are required for this slice]
```

## Rules
- Never create an issue that only touches one architectural layer
- The first issue should ALWAYS be a vertical slice that produces something visible
- Classify every issue as AFK or human-in-loop explicitly
- Keep issues small enough to complete in one session (~100K token budget)
- The dependency graph should be reviewable at a glance — no deeply nested blocking chains
- If the AI produces a "create the [service/module]" issue with no UI or data component, it's horizontal — flag it
