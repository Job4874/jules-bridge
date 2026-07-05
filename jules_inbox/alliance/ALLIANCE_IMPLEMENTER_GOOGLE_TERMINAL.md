# Alliance Implementer Packet: Google Terminal Agent

Objective: Create a complex codebase alliance where Jules owns actual change creation and the supported Google terminal agent implements/reviews with dry-run-first controls.

Active Implementer: antigravity_cli

Role: Support implementation with bounded codebase reasoning, model/plugin capability checks, and review notes.

Target Files:
- bridge.py
- modules/alliance_switchboard.py
- modules/__init__.py
- tests/test_alliance_switchboard.py
- tests/test_bridge_routes.py

Responsibilities:
- Use Antigravity CLI as the supported Google terminal-agent path when ready.
- Keep prompts dry-run-first; do not request edit-capable execution without explicit approval.
- Explain skill/plugin/model capability from the CLI point of view.
- Return risks, suggested patch scope, and verification ideas to Jules/the bridge.

Bridge Surfaces:
- POST /gemini/antigravity/preflight
- POST /gemini/antigravity/prompt
- POST /gemini/preflight
- POST /gemini/prompt
