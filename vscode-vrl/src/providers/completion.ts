import * as vscode from "vscode";
import { VRL_BUILTINS } from "../data/vrl-builtins";

const VRL_SELECTOR: vscode.DocumentSelector = { language: "vrl" };

export function registerCompletionProvider(context: vscode.ExtensionContext): void {
  const provider = vscode.languages.registerCompletionItemProvider(
    VRL_SELECTOR,
    {
      provideCompletionItems() {
        return VRL_BUILTINS.map(toCompletionItem);
      },
    },
    ".",
    "!",
    "("
  );

  context.subscriptions.push(provider);
}

function toCompletionItem(builtin: (typeof VRL_BUILTINS)[number]): vscode.CompletionItem {
  const item = new vscode.CompletionItem(builtin.name, vscode.CompletionItemKind.Function);
  item.detail = builtin.detail;
  item.documentation = new vscode.MarkdownString(builtin.doc);
  item.insertText = new vscode.SnippetString(builtin.insertText);
  item.filterText = `${builtin.name} ${builtin.name.replace(/!$/, "")}`;
  return item;
}
