---
name: remember
description: >
  Run at the end of every coding session.
  Synthesizes decisions made, patterns established, and progress completed during the session,
  and compresses them into a memory file in the `memory/` directory.
---

# Remember Skill

## Purpose

Ensure continuity across separate sessions. Instead of starting from scratch or re-explaining context, this skill preserves the history of decisions, gotchas, and architectural choices.

## Instructions

1. **Analyze the Session**:
   - Scan the git history or modified files to review changes made.
   - Scan the `bridge.log` or test outputs for errors or behavior solved.
2. **Synthesize Changes**:
   - Extract any new conventions, patterns, or library patterns discovered.
   - Document any resolved blockers.
3. **Write Memory**:
   - Update `memory/general.md` or a domain-specific memory file (e.g. `memory/oracle.md`).
   - Ensure the summary is highly compressed but retains technical details (e.g., exact class names, route paths, behavior).
4. **Update Progress Tracker**:
   - Mark the completed items in `context/06_progress_tracker.md`.
