# Phase 6 Ticket: Harden VRL Built-ins

Status: DONE

## Objective

Expand the VRL VS Code extension built-in function data from the initial 3-function scaffold to a broader, official-doc-backed completion and hover set.

## Scope

- Add common array, path, string, system, and type functions to `vscode-vrl/src/data/vrl-builtins.json`.
- Keep the existing data schema: `name`, `detail`, `doc`, `insertText`.
- Preserve the extension's existing diagnostic behavior that normalizes fallible `!` calls.

## Source Evidence

- Official Vector VRL function reference: <https://vector.dev/docs/reference/vrl/functions/>
- The official reference contains each added function name and signature family: `append`, `contains`, `del`, `downcase`, `exists`, `get`, `includes`, `length`, `log`, `now`, `parse_json`, `pop`, `push`, `replace`, `set`, `split`, `strip_whitespace`, `to_int`, `to_string`, `upcase`.

## No-Slop Corrections Applied

- Kept fallible completions as bang-form snippets for `get`, `set`, `parse_json`, `to_int`, and `to_string`.
- Corrected `replace` to the official three-argument signature shape instead of adding an unsupported `count` parameter.
- Used static-path snippets for `del` and `exists` because the official `del` docs call out `remove` for dynamic path deletion.

## Validation

- JSON parse/count: PASS, 20 entries.
- Duplicate builtin names: PASS, 0 duplicates.
- Compile command: `npm run compile` from `vscode-vrl/`.
- Compile result: PASS, `tsc -p ./` exited 0.
- SHA-256 `vscode-vrl/src/data/vrl-builtins.json`: `A27BE25F8E5A2BCDE4D5BEAA28465A2C9035FA18454E32ED59F75F6A755BAE10`.

## Files Changed

- `vscode-vrl/src/data/vrl-builtins.json`
- `doc/tickets/006_harden_vrl_builtins.md`
