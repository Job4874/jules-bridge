🎯 **What:**
Added unit tests for the `compute_macd` function within `modules/tibin_core.py`. This function calculates the Moving Average Convergence Divergence (MACD) indicator, and its correctness is crucial for the signal-to-execution pipeline. Previously, it lacked test coverage.

📊 **Coverage:**
The newly introduced tests cover the following scenarios:
- **Basic functionality:** Validates that the function correctly outputs three `pandas.Series` of equal length to the input series.
- **Custom parameters:** Verifies that passing custom `fast`, `slow`, and `signal` periods correctly adjusts the computations.
- **Empty input series:** Asserts that an empty `pandas.Series` gracefully returns three empty series without errors.
- **Constant trend values:** Ensures that if a series with constant values is provided, the function mathematically calculates the correct MACD, signal line, and histogram values (`0.0`).

✨ **Result:**
The `compute_macd` function now has robust coverage, significantly improving the reliability of the codebase. The tests verify standard execution, edge cases, and custom input parameters securely using deterministic assertions.
