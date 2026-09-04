## 2026-09-04 - NavRail ARIA and State fixes
**Learning:** Found that the NavRail rail-button does not use aria-current or aria-pressed for active state which helps screen readers identify the selected navigation item.
**Action:** Add aria-current to reflect the active state in NavRail buttons for better accessibility.
