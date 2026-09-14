## 2026-07-21 - Added Contextual Aria Labels
**Learning:** Found that the model select and chat input areas in `App.jsx` lacked explicit screen-reader hints (`aria-label`) and stateful tooltips. This pattern suggests other interactive elements (like custom selects or complex textareas) might also lack proper accessibility context.
**Action:** When working on interactive inputs or selectors, always check if an explicit `aria-label` is needed for screen readers and verify if dynamic tooltip hints (e.g., "Processing...", "Enter to send") could enhance the visual experience.
