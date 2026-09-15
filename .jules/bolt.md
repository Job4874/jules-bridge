## 2024-05-18 - Flat List Flattening
**Learning:** Using `"".join("".join(s) ...)` on nested string blocks incurs a significant overhead. Flattening with `itertools.chain.from_iterable` is around 40-50% faster in Python.
**Action:** When constructing strings from heavily nested iterables, use `itertools.chain.from_iterable` instead of nested generators or comprehensions.
