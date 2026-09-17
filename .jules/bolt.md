## 2024-09-17 - Avoid Synchronous State Updates in useEffect
**Learning:** In the React frontend, calling state setters (like `setState`) synchronously inside a `useEffect` hook triggers cascading re-renders. This is flagged by `oxlint` as `react(set-state-in-effect)`.
**Action:** Derive the required values dynamically during the standard render cycle instead of updating state synchronously in `useEffect`.
