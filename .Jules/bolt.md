## 2024-05-15 - Optimizing nested list string concatenation
**Learning:** Using nested `.join("".join(s) ...)` on a `List[List[str]]` causes unnecessary overhead by first combining sublists and then recombining them, creating many intermediate strings.
**Action:** Use `itertools.chain.from_iterable` to flatten `List[List[str]]` into an iterable of strings and perform a single `"".join()` on it.
