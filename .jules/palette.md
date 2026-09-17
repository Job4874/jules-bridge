## 2026-09-17 - Chat Input Contextual State
**Learning:** In standard conversational UIs, failing to disable the input field during the AI's "thinking" state often leads to rapid overlapping queries which can confuse users and disrupt chat history parsing.
**Action:** When working on asynchronous UI actions (like chat forms), always verify if the input itself needs to be locked or put in a loading state alongside the submit button to preserve UX consistency.
