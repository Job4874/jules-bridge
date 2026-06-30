---
name: recover
description: >
  Run when a session is stuck, tests are failing repeatedly, or the agent is in a doom loop.
  Diagnoses the current failure mode and provides the correct remediation steps.
---

# Recover Skill

## Purpose

Halt agent spiraling and context pollution by diagnosing failures and returning to a clean, known-good baseline.

## Instructions

1. **Identify the Failure Mode**:
   - **Doom Loop**: The agent is making the same edit or running the same command repeatedly.
   - **Polluted Context**: The chat history is bloated with failed attempts and the model is guessing.
   - **Broken Assumption**: A fundamental assumption about an API or system interface was wrong.
2. **Diagnose and Prescribe**:
   - Check test outputs, compilation logs, or `bridge.log`.
   - Run `POST /retrospective/analyze` if applicable.
   - Propose clear remediation:
     - Revert changes to the last git commit.
     - Reset the chat/session state.
     - Revise the implementation plan.
