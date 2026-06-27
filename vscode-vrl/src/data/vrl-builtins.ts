import builtinsJson from "./vrl-builtins.json";

export interface VrlBuiltin {
  name: string;
  detail: string;
  doc: string;
  insertText: string;
}

export const VRL_BUILTINS: readonly VrlBuiltin[] = builtinsJson;

export const VRL_BUILTIN_NAMES = new Set(VRL_BUILTINS.map((builtin) => builtin.name));

export function findBuiltin(name: string): VrlBuiltin | undefined {
  const normalizedName = name.replace(/!$/, "");
  const exact = VRL_BUILTINS.find((builtin) => builtin.name === name);
  if (exact) {
    return exact;
  }

  return VRL_BUILTINS.find((builtin) => builtin.name.replace(/!$/, "") === normalizedName);
}
