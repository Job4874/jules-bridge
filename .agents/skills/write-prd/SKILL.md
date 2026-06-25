---
name: write-prd
description: >
  Distill the current conversation (ideally a completed grill-me session) into a Product Requirements Document.
  The PRD is the "destination document" — it defines WHERE you're going, not HOW you'll get there.
  Use after a grill-me session, or with a detailed problem description as input.
---

# Write PRD Skill

## Purpose
Create a **destination document** that captures the shared design concept from the grilling session. This document:
- Defines the full scope of the feature
- Captures all decisions made
- Provides user stories as an acceptance baseline
- Identifies the modules/files that will change
- Does NOT dictate implementation order (that's the job of `/prd-to-issues`)

This is NOT "specs to code". The code and codebase are kept in mind throughout.

## Instructions

### Step 1: Gather Input
If no grilling session has occurred yet, ask the user for a detailed description of the problem. Then optionally run a brief grilling session (or use the existing conversation).

### Step 2: Explore the Codebase (if not already done)
Use a sub-agent to identify:
- The modules most likely to be affected
- Existing patterns to follow
- Any constraints or gotchas

Present a list of **proposed modules to modify** to the user for confirmation before writing the PRD.

### Step 3: Write the PRD
Output a markdown document with this structure:

```markdown
# PRD: [Feature Name]

## Problem Statement
[What problem does the user/client have? Why does it matter?]

## Solution
[High-level description of what we're building to solve it]

## User Stories
Given [context], when [action], then [outcome].

- Given a user has completed a lesson, when they return to the dashboard, then they see their points total updated
- [Continue for all acceptance criteria]

## Implementation Decisions
- [Decision 1]: [What was decided and why]
- [Decision 2]: [...]
- [Edge case resolution]: [...]

## Testing Decisions
- [What needs unit tests]
- [What needs integration tests]
- [What edge cases need explicit test coverage]

## Proposed Modules to Modify
- `src/services/[module].ts` — [reason]
- `src/components/[component].tsx` — [reason]
- `db/schema.ts` — [reason]
- [etc.]
```

### Step 4: Save the PRD
Save the PRD to `./issues/prd-[feature-name].md` (or to a GitHub issue if configured).

## Rules
- Keep the PRD focused on WHAT and WHY, not HOW
- Every user story should be independently testable
- Include testing decisions — they are as important as implementation decisions
- Do not skip the "proposed modules" section — keeping code in mind prevents "specs to code" drift
- The user does NOT need to review this document line-by-line — LLMs are excellent at summarization, and if the grill session was thorough, the PRD will be accurate
