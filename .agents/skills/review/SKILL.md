---
name: review
description: >
  Run after completing any feature or file modification.
  Checks the implementation against the plan, verifies code standards, and surfaces potential bugs.
---

# Review Skill

## Purpose
Enforce quality, standards, and correctness without making automatic edits. Provides feedback categorized by severity.

## Instructions
1. **Compare Implementation against Plan**:
   - Check if all deliverables in the approved plan have been met.
   - Verify signatures match the spec.
2. **Check Code Standards**:
   - Review imports, type hints, docstrings, and architectural boundaries (e.g. components should not contain database logic, deep modules should expose simple surfaces).
3. **Run Checks**:
   - Compile code and run existing tests (`python -m pytest tests/ -v`).
4. **Output Report**:
   - Return issues structured by severity:
     - **Critical**: Broken functionality, test failures, or violation of major boundaries.
     - **Important**: Missing type hints, missing docstrings, or suboptimal patterns.
     - **Minor**: Style tweaks or minor optimizations.
   - Do NOT automatically fix the code. Let the developer review the feedback first.
