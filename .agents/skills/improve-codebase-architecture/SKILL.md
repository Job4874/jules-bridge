---
name: improve-codebase-architecture
description: >
  Identify shallow modules in a codebase and refactor them into deep modules (from John Ousterhout's
  "A Philosophy of Software Design"). Use when the AI keeps getting confused navigating the codebase,
  tests are hard to write, or you feel cognitive overload from too many small files with tangled concerns.
  Produces a clean module boundary map and executes the refactor incrementally.
---

# Improve Codebase Architecture Skill

## Purpose
Turn a codebase full of **shallow modules** (many small files, complex interfaces, tangled concerns)
into a codebase full of **deep modules** (few focused modules, simple interfaces, hidden complexity).

From John Ousterhout (*A Philosophy of Software Design*):
> "Deep modules provide powerful functionality through a simple interface.
> Shallow modules have complex interfaces relative to the functionality they provide."

Matt Pocco: "Bad codebases make bad agents. AI is really good at creating shallow modules.
You need to actively push back against that."

## When to Use
- AI keeps navigating to wrong files or missing dependencies
- Tests require mocking 5+ things to test anything
- You feel cognitive overload reading the codebase
- Adding a feature requires touching 8+ files
- Two or more files mix concerns from different domains

## Instructions

### Step 1: Map the Current Architecture
Use a sub-agent to create a dependency map:
- List all modules/files and their sizes (lines)
- For each, list: what it imports, what imports it, what domain it belongs to
- Identify "shallow" indicators: many small functions, complex import graphs, mixed concerns

Present findings as a table:
```
| Module | Lines | Imports | Depth Score | Domain |
|--------|-------|---------|-------------|--------|
```

### Step 2: Identify Refactor Opportunities
Look for clusters of related code that can be wrapped in a single deep module:
- Files that always change together (high coupling)
- Files from the same domain with multiple callers
- "Helper" files that have grown organically and leaked concerns
- Routes/handlers that contain business logic (should be in a module)

**Signs of a good deep module candidate:**
- Multiple small files that all relate to one concept
- A file imported by many callers with a wide interface
- Infrastructure concerns mixed with business logic

### Step 3: Design the Module Interfaces FIRST
Before moving any code, design the public interface for each new module:
- What are the 3–5 public functions/methods?
- What are their inputs and outputs? (Use TypedDict or dataclasses)
- What does a caller NEED to know? (Keep this minimal)
- What can be hidden? (Keep this maximal)

Review with the user before implementing.

### Step 4: Execute the Refactor as Vertical Slices
Implement one module at a time, in dependency order (dependencies first):
1. Create the new module file with its interface
2. Move relevant code into private implementations
3. Write tests at the module interface (not the implementation)
4. Update all callers to use the new interface
5. Delete the old shallow modules
6. Verify tests pass

### Step 5: Update the Ubiquitous Language
After refactoring, run the `ubiquitous-language` skill to update the shared vocabulary document —
new module names become canonical terms.

## Rules
- Design the interface before moving any code
- Never create a new module without tests at its boundary
- Keep the public interface as small as possible (3–5 functions max per module)
- The caller should never need to know implementation details
- Keep `__init__.py` or index files as pure re-exports only
- Never mix infrastructure concerns (HTTP, filesystem) with domain logic in one module

## The Deep Module Test
A module is deep if:
- ✅ A new developer can use it after reading only the interface (not the implementation)
- ✅ A test for it only mocks external resources (not internal implementation details)
- ✅ Adding a new internal feature doesn't change the public interface
- ✅ The module name clearly describes ONE domain concept
