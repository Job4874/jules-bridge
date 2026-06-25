---
name: grill-me
description: >
  Interview the user relentlessly to reach a shared design concept before any planning or coding begins.
  Use this at the very start of any new feature, project, or non-trivial task. Prevents misalignment.
  Never eagerly jump to producing a plan — keep asking until full alignment is achieved.
---

# Grill Me Skill

## Purpose
Reach a **shared design concept** — a mutual understanding between you (the AI) and the user — before producing any plan, PRD, or code.

This prevents the most common failure mode: the AI eagerly producing a plan based on incomplete understanding, then spending many tokens implementing the wrong thing.

Inspired by Frederick P. Brooks (*The Design of Design*): when collaborators build something together, the shared mental model of what they're building IS the design concept. That's what this skill creates.

## Instructions

1. **Explore the codebase first** (if one exists). Use a sub-agent to avoid polluting the main context. The sub-agent should summarise: key modules, existing patterns, tech stack, and anything relevant to the user's request.

2. **Begin the interview**. Ask one question at a time. Do NOT ask multiple questions at once.

3. **For every question**:
   - Provide YOUR recommended answer (based on best practices and codebase knowledge)
   - Explain WHY you're recommending it (briefly)
   - Wait for the user's response before continuing

4. **Walk the design tree**. Cover these branches in rough order, resolving dependencies as they arise:
   - Core data model decisions
   - Business logic / rules
   - Edge cases and constraints
   - Integration points with existing systems
   - UI/UX considerations
   - Performance and scalability concerns
   - Testing strategy
   - Rollout / migration concerns (e.g. retroactive data backfills)

5. **Do NOT produce a plan, PRD, or summary until**:
   - All major design branches have been resolved, OR
   - The user explicitly asks you to stop grilling and move on

6. **Keep going** even if you think you have enough information. Probe assumptions. Surface the questions the user hasn't thought to ask. The value is in the questions that surprise the user.

7. **When complete**: Summarise all decisions made during the session. This summary becomes the input to `/write-prd`.

## Rules
- Ask ONE question at a time
- Always provide a recommended answer with brief rationale
- Never rush to produce a plan
- Never ask about things already decided in the conversation
- Surface non-obvious edge cases (retroactive data, permissions, error states, etc.)
- Treat the conversation history as a valuable asset — it IS the design concept

## Example Opening
> "I've explored the codebase and have a good picture of the existing architecture. Let me ask you some questions to make sure we're fully aligned before we plan anything.
>
> **Question 1: [Most fundamental decision about the feature]**
> My recommendation: [answer]. Reason: [why].
>
> What do you think?"
