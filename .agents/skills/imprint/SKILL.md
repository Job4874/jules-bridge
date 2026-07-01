---
name: imprint
description: >
  Run after creating or modifying API routes or module layouts.
  Captures coding patterns, route structures, and middleware registration to maintain system-wide consistency.
---

# Imprint Skill

## Purpose

Ensure that new modules, routes, and API responses strictly match the established conventions and architectural boundaries, preventing code sprawl.

## Instructions

1. **Analyze Design Patterns**:
   - Inspect newly created routes in `bridge.py` or module wrappers in `modules/`.
   - Verify they align with existing structures (e.g. Flask error handlers, return type formats like `TypedDict`, JSON response envelopes).
2. **Register Pattern**:
   - Check if new patterns are documented. If not, record them in the Gotchas file (`context/05_gotchas.md`) or UBIQUITOUS_LANGUAGE.md.
   - Update `modules/__init__.py` to ensure symbols are exported correctly.
3. **Scan for Inconsistencies**:
   - Verify that no duplicate route prefixes, helper scripts, or imports exist.
   - Flag any deviations from code standards.
