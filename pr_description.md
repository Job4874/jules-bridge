💡 **What:** Replaced the manual nested python loop for calculating `signal_counts` in `_context_metrics` with a C-optimized one-liner: `dict(Counter(chain.from_iterable(row.get("signals", []) for row in rows)))`.

🎯 **Why:** The previous approach iteratively retrieved, updated, and re-assigned values in a dictionary for every single signal string within every single row. `collections.Counter` handles the updates at the C level, and `itertools.chain.from_iterable` flattens the nested lists lazily using C-level loops, dramatically lowering Python overhead.

📊 **Measured Improvement:** We created a benchmark script testing the counting of variable-length signal strings across 100,000 rows. The results over 10 runs were:
- **Baseline**: 7.0587 seconds
- **Optimized**: 5.5538 seconds
- **Improvement**: ~21.32% performance boost for the inner signal counting loop logic.
