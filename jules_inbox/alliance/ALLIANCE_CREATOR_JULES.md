# Alliance Creator Packet: Jules

Objective: Create a complex codebase alliance where Jules owns actual change creation and the supported Google terminal agent implements/reviews with dry-run-first controls.

Role: Create the actual change plan and own the patch or Jules worker packet.

Target Files:
- bridge.py
- modules/alliance_switchboard.py
- modules/__init__.py
- tests/test_alliance_switchboard.py
- tests/test_bridge_routes.py

Responsibilities:
- Read AKC/context and current repo state before editing.
- Return affected files, tests, blockers, and exact next action.
- Do not create remote sessions or apply live changes unless the operator sends explicit live flags.
- Preserve dry-run-first behavior and keep secrets redacted.

Bridge Surfaces:
- POST /jules/preflight
- POST /jules/dispatch
- POST /jules/cycle
- POST /jules/fleet-watch

Current Mode: two_agent_alliance
