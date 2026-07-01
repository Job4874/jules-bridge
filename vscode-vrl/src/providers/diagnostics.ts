import * as vscode from "vscode";
import { findBuiltin } from "../data/vrl-builtins";

const CONTROL_WORDS = new Set(["if", "else", "for", "in", "return", "abort", "assert", "match"]);
const OPEN_TO_CLOSE = new Map([
  ["(", ")"],
  ["[", "]"],
  ["{", "}"],
]);
const CLOSE_TO_OPEN = new Map([
  [")", "("],
  ["]", "["],
  ["}", "{"],
]);

interface StackEntry {
  char: string;
  line: number;
  character: number;
}

export function registerDiagnosticProvider(context: vscode.ExtensionContext): void {
  const collection = vscode.languages.createDiagnosticCollection("vrl");

  for (const document of vscode.workspace.textDocuments) {
    if (document.languageId === "vrl") {
      refreshDiagnostics(document, collection);
    }
  }

  context.subscriptions.push(
    collection,
    vscode.workspace.onDidOpenTextDocument((document) => refreshDiagnostics(document, collection)),
    vscode.workspace.onDidChangeTextDocument((event) => refreshDiagnostics(event.document, collection)),
    vscode.workspace.onDidCloseTextDocument((document) => collection.delete(document.uri))
  );
}

function refreshDiagnostics(
  document: vscode.TextDocument,
  collection: vscode.DiagnosticCollection
): void {
  if (document.languageId !== "vrl") {
    return;
  }

  const diagnostics: vscode.Diagnostic[] = [];
  const bracketStack: StackEntry[] = [];

  for (let lineIndex = 0; lineIndex < document.lineCount; lineIndex += 1) {
    const line = document.lineAt(lineIndex);
    const sanitized = stripStringsAndComments(line.text);

    collectBracketDiagnostics(sanitized, lineIndex, bracketStack, diagnostics);
    collectFunctionDiagnostics(sanitized, lineIndex, diagnostics);
  }

  for (const entry of bracketStack) {
    const expected = OPEN_TO_CLOSE.get(entry.char);
    diagnostics.push(
      new vscode.Diagnostic(
        new vscode.Range(entry.line, entry.character, entry.line, entry.character + 1),
        `Missing closing '${expected}'.`,
        vscode.DiagnosticSeverity.Error
      )
    );
  }

  collection.set(document.uri, diagnostics);
}

function collectBracketDiagnostics(
  text: string,
  lineIndex: number,
  stack: StackEntry[],
  diagnostics: vscode.Diagnostic[]
): void {
  for (let character = 0; character < text.length; character += 1) {
    const char = text[character];
    if (OPEN_TO_CLOSE.has(char)) {
      stack.push({ char, line: lineIndex, character });
      continue;
    }

    if (!CLOSE_TO_OPEN.has(char)) {
      continue;
    }

    const expectedOpen = CLOSE_TO_OPEN.get(char);
    const last = stack.at(-1);
    if (last?.char === expectedOpen) {
      stack.pop();
      continue;
    }

    diagnostics.push(
      new vscode.Diagnostic(
        new vscode.Range(lineIndex, character, lineIndex, character + 1),
        `Unexpected closing '${char}'.`,
        vscode.DiagnosticSeverity.Error
      )
    );
  }
}

function collectFunctionDiagnostics(
  text: string,
  lineIndex: number,
  diagnostics: vscode.Diagnostic[]
): void {
  const functionCall = /\b([A-Za-z_][A-Za-z0-9_]*!?)(?=\s*\()/g;
  for (const match of text.matchAll(functionCall)) {
    const name = match[1];
    if (CONTROL_WORDS.has(name) || findBuiltin(name)) {
      continue;
    }

    const start = match.index ?? 0;
    diagnostics.push(
      new vscode.Diagnostic(
        new vscode.Range(lineIndex, start, lineIndex, start + name.length),
        `Unknown VRL built-in '${name}'. Add it to src/data/vrl-builtins.json if it is valid.`,
        vscode.DiagnosticSeverity.Information
      )
    );
  }
}

function stripStringsAndComments(text: string): string {
  let output = "";
  let quote: string | undefined;
  let escaped = false;

  for (const char of text) {
    if (quote) {
      output += " ";
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = undefined;
      }
      continue;
    }

    if (char === "#") {
      output += " ".repeat(text.length - output.length);
      break;
    }

    if (char === "\"" || char === "'") {
      quote = char;
      output += " ";
      continue;
    }

    output += char;
  }

  return output;
}
