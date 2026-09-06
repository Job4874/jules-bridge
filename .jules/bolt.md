## 2026-09-06 - Optimize string concatenation in `academic_agent.py` loops
**Learning:** In `modules/academic_agent.py`, `build_answer_prompt` and `_write_academic_memory` construct strings iteratively in loops using the `+=` operator. Python strings are immutable, so repeated concatenation (especially in a loop with multiple segments) creates intermediate string objects, leading to O(N^2) memory and CPU overhead.
**Action:** Use list `append()` / `extend()` and `"".join(list)` instead of `+=` for string assembly inside loops, following the explicit memory optimization instruction for "Bolt".
