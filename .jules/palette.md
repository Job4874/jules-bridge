## 2026-09-07 - Add missing ARIA attributes to dashboard UI
**Learning:** Found a pattern where interactive elements like toggle buttons, filter buttons, and navigation links were lacking proper ARIA attributes to communicate their state to assistive technologies, making the dashboard less accessible.
**Action:** When adding new interactive toggle buttons or navigation elements, always ensure `aria-pressed` or `aria-current` is applied correctly. Make sure text inputs and select elements have appropriate `aria-label` attributes if not implicitly linked.
