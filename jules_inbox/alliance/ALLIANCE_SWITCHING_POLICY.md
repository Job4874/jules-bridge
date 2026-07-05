# Alliance Switching Policy

Preferred Creator: jules
Preferred Implementer: antigravity_cli
Active Implementer: antigravity_cli

Decision Table:
- If complex task and Jules ready and Antigravity ready: Jules creates the patch/worker packet; Antigravity implements/reviews through dry-run prompt support.
- If Jules ready but Antigravity unavailable: Jules owns creation and implementation; bridge marks alliance as partial until the Google lane is restored.
- If Antigravity ready but Jules unavailable: Antigravity can analyze, but actual change creation is blocked until Jules or Codex owns the patch.
- If legacy Gemini installed but model smoke blocked: Use it only for capability/skill visibility; prefer Antigravity for supported model execution.
- If any live execution requested: Require explicit route-specific live flags, bounded timeout, proof capture, and no secret printing.

Handoff Contract:
- creator returns changed files, tests run, blockers, and next action
- implementer returns reasoning, suggested patch scope, and risk list
- switch controller records proof before calling the goal complete
