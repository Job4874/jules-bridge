## 2024-03-20 - Custom Button-Based UI Selection Components Accessibility
 **Learning:** The React application utilizes generic `<button>` elements styled with CSS classes (`.active`, `.selected`) to represent selected states for navigation, list items, and filters, but screen readers cannot announce these visual states without proper ARIA attributes.
 **Action:** Proactively scan custom components like `NavRail` and selection lists (e.g., workers, events) for missing `aria-current` (for navigation) or `aria-pressed` (for toggles/selections) and add them alongside the visual state logic.
