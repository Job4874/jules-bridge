## 2024-05-18 - Missing ARIA states on custom styled components
**Learning:** In the Dashboard UI, interactive elements like `.rail-button`, `.worker-entry`, and filter buttons convey their selection/activation state strictly via CSS classes (`active`, `selected`) rather than semantic `aria-` attributes.
**Action:** Always verify that CSS-based selection indicators are paired with corresponding `aria-current`, `aria-selected`, or `aria-pressed` states for screen readers.
