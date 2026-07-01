# Architecture Map

- `syntaxes/vrl.tmLanguage.json`: TextMate grammar for colorization and tokenization.
- `language-configuration.json`: editor comment, bracket, and auto-closing rules for `.vrl` files.
- `snippets/vrl.snippets.json`: template completions contributed through VS Code snippets.
- `src/extension.ts`: main entry point. Registers providers only.
- `src/providers/`: modular providers for hover, completion, and diagnostics.
- `src/data/vrl-builtins.json`: single source of truth for built-in functions and documentation.
- `src/data/vrl-builtins.ts`: typed wrapper around the JSON data for provider consumption.

## Boundaries

- Do not put provider logic in `src/extension.ts`.
- Do not duplicate function signatures inside providers.
- Prefer native `vscode.languages` APIs over LSP until the project has a concrete LSP requirement.
- Treat diagnostics as editor assistance, not a full VRL compiler.
