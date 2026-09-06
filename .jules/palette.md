## 2024-05-17 - Chat Message Announcer
**Learning:** Found that the dynamic chat interface was not announcing incoming messages to screen reader users automatically.
**Action:** Added `aria-live="polite"` to dynamic content regions so new items are read out without interrupting the user's current flow.
