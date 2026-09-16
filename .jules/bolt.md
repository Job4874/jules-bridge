## 2025-06-01 - Optimizing String Assembly in Loops
**Learning:** In deeply nested loops string concatenation using nested generator expressions (e.g. `"".join("".join(s) for s in kept)`) has significant CPU overhead due to bytecode evaluation for every iteration.
**Action:** When accumulating strings in loops, always flatten the segments into a single `List[str]` using `list.extend()` and perform a single flat `"".join()` at the end, which is pushed directly to the highly optimized C-layer of Python's standard library.
