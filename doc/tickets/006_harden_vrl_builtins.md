# Phase 6 Ticket: Harden VRL Built-ins

## Objective
Harden the VRL VS Code extension by expanding the `src/data/vrl-builtins.json` file with a comprehensive set of official Vector VRL functions.

## Context
Currently, `vrl-builtins.json` contains only 3 functions. This limits the effectiveness of IntelliSense and hover documentation in the extension.

## Scope
1.  Expand `vscode-vrl/src/data/vrl-builtins.json` with 17+ common VRL functions researched from official docs.
2.  Ensure each entry follows the existing schema: `name`, `detail`, `doc`, `insertText`.
3.  Verify that `npm run compile` still passes in `vscode-vrl/`.

## Tasks
- [ ] Add array functions: `append`, `push`, `pop`, `includes`, `length`.
- [ ] Add string functions: `downcase`, `upcase`, `contains`, `replace`, `split`, `strip_whitespace`.
- [ ] Add path functions: `get`, `set`, `del`, `exists`.
- [ ] Add system/utility functions: `log`, `parse_json`, `now`.

## Validation
- [ ] `npm run compile` in `vscode-vrl/` returns exit code 0.
- [ ] Manual inspection of `vrl-builtins.json` for JSON validity.

## Evidence
- SHA-256 of updated `vrl-builtins.json`.
- Compilation output.
