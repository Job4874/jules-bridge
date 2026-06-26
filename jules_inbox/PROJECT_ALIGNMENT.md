# DEVELOPMENT SYNC

Jules: The recent commits on the UI driver and VM manager are structurally excellent. The operator has reviewed the tests and the architecture is approved. To improve development velocity and reduce friction, we are standardizing how you report environment constraints. If you hit a sandbox limitation or lack an integration needed to complete an H/L/ACT loop, you must explicitly log this in your PR descriptions or commit messages.

**LOGGING PROTOCOL:**

Prefix any resource requests or environment blockers with the exact string `[ARCH-BLOCKER]:` so the operator can quickly parse it and adjust your environment permissions accordingly.