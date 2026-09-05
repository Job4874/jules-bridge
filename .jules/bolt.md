## 2026-07-08 - Optimize string construction in retrospective module
**Learning:** Nested generator expressions (`"".join("".join(s) for s in kept)`) for joining list of lists of strings are significantly slower than accumulating segments in a flat list using `.extend()` and doing a single `"".join()` at the end.
**Action:** When constructing strings from deeply nested iterables, flatten them into a single list first before joining.
