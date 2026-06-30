---
name: architect
description: >
  Run before starting any complex feature, new module, or major change.
  Reads the project context files, interviews the user one question at a time to resolve design decisions,
  and produces a clear, structured implementation plan.
---

# Architect Skill

## Purpose

Prevent implementation drift, architectural misalignment, and wasted tokens by establishing a clear, agreed-upon technical plan before writing any code.

## Instructions

1. **Gather Context**:
   - Read all context files in the `context/` directory (`01_project_overview.md`, `02_architecture.md`, `03_code_standards.md`, etc.).
   - Inspect the codebase for relevant existing files or patterns.
2. **Conduct the Design Interview**:
   - Ask **one question at a time** in the chat. Do not list multiple questions at once.
   - For every question, present:
     - The issue/decision that needs resolution.
     - Your recommendation.
     - The rationale behind your recommendation.
3. **Resolve Design Elements**:
   - Data models & storage (e.g. database schema changes, file formats).
   - Public module interfaces and route signatures.
   - Edge cases and constraints.
   - Testing approach.
4. **Generate the Plan**:
   - Once the user agrees to the decisions (or instructs you to proceed), write/update the `implementation_plan.md` file.
   - Wait for the user's explicit approval before proceeding to the execute phase.
