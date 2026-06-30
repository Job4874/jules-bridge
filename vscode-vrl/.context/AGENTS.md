# VRL Extension - Agent Directives

- Reading order: read `.context/02_architecture.md` before writing any VS Code API logic.
- Hard rule 1: never use raw Language Server Protocol boilerplate unless explicitly instructed. Use the native `vscode.languages` API for hovers, completions, and diagnostics first.
- Hard rule 2: all VRL built-in functions must be sourced from `src/data/vrl-builtins.json`. Do not hallucinate VRL function signatures in providers.
- Hard rule 3: keep syntax highlighting in `syntaxes/vrl.tmLanguage.json`; keep runtime editor behavior in `src/providers/`.
- Hard rule 4: the extension must compile with `npm run compile` before being called ready.
