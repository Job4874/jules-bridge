import * as vscode from "vscode";
import { findBuiltin } from "../data/vrl-builtins";

const VRL_SELECTOR: vscode.DocumentSelector = { language: "vrl" };
const VRL_WORD = /[A-Za-z_][A-Za-z0-9_]*!?/;

export function registerHoverProvider(context: vscode.ExtensionContext): void {
  const provider = vscode.languages.registerHoverProvider(VRL_SELECTOR, {
    provideHover(document, position) {
      const range = document.getWordRangeAtPosition(position, VRL_WORD);
      if (!range) {
        return undefined;
      }

      const word = document.getText(range);
      const builtin = findBuiltin(word);
      if (!builtin) {
        return undefined;
      }

      const markdown = new vscode.MarkdownString();
      markdown.appendCodeblock(builtin.detail, "vrl");
      markdown.appendMarkdown(builtin.doc);
      return new vscode.Hover(markdown, range);
    },
  });

  context.subscriptions.push(provider);
}
