import * as vscode from "vscode";
import { registerCompletionProvider } from "./providers/completion";
import { registerDiagnosticProvider } from "./providers/diagnostics";
import { registerHoverProvider } from "./providers/hover";

export function activate(context: vscode.ExtensionContext): void {
  console.log("VRL Language Support is now active.");

  registerCompletionProvider(context);
  registerHoverProvider(context);
  registerDiagnosticProvider(context);
}

export function deactivate(): void {}
