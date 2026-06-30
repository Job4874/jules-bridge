# Implementation Plan

## Decision

This VS Code extension is scaffolded as an isolated project under `vscode-vrl/` so it does not disturb the existing `.jules` bridge repository.

## Scope

1. Create a clean VS Code extension file tree for VRL language support.
2. Add agent guardrail context files so future coding agents follow the architecture.
3. Wire VS Code contribution points for `.vrl` files, grammar, snippets, and language configuration.
4. Implement modular TypeScript providers for completions, hover documentation, and lightweight diagnostics.
5. Keep VRL builtins in `src/data/vrl-builtins.json` as the single source of truth.
6. Verify with TypeScript compilation.

## Validation

- `npm install`
- `npm run compile`

## Next Hardening Options

- Expand `src/data/vrl-builtins.json` from the official VRL function reference.
- Replace lightweight diagnostics with parser-backed validation once a trusted VRL parser is chosen.
