# AKC Context Checkpoint

- generated_at_utc: 2026-06-26T02:59:23.788160+00:00
- status: ready
- source_count: 5
- readable_count: 5
- missing_count: 0
- operating_rule_count: 9

## Source Inventory

| name | path_ref | readable | sha256 | lines | bytes |
| --- | --- | ---: | --- | ---: | ---: |
| pasted-text-1.txt | path-ref:056a0d4c8729 | True | a886f3a19d985307 | 8140 | 344586 |
| pasted-text-2.txt | path-ref:1c7be4ed40cd | True | 8f3a168d909e6211 | 5520 | 263580 |
| pasted-text-3.txt | path-ref:5932c64a9a69 | True | 02557d5675b91ba1 | 5341 | 229045 |
| pasted-text-4.txt | path-ref:786c26672406 | True | b762c649b2a68063 | 972 | 21455 |
| pasted-text-5.txt | path-ref:8765e5a8cf4f | True | f9debedb5c6df4c4 | 1835 | 96714 |

## Operating Rules

- `context_system`: Load compact, source-backed project context before implementation and keep progress trackers current. Matched: context file, context files, project context, agents.md.
- `grill_alignment`: Use a grill/alignment pass before PRDs, tickets, or coding on non-trivial work. Matched: grill, shared design concept, shared understanding, design concept.
- `tdd_feedback`: Use TDD and short feedback loops: write the test first, make it pass, then refactor. Matched: tdd, feedback loop, feedback loops.
- `evidence_gates`: Treat tests, hashes, screenshots, and runtime output as required evidence before trusting completion claims. Matched: evidence, prove, verification, verified.
- `deep_modules`: Prefer deep modules with simple interfaces and test at the module boundary. Matched: deep module, deep modules, simple interface.
- `ralph_loop`: Drive autonomous work through one focused ticket at a time, with tests and evidence before the next loop. Matched: ralph, ticket, loop.
- `hrm_reasoning`: Separate high-level planning from low-level execution and use budgeted halting checks. Matched: hrm, high-level, low-level, planner, worker.
- `smart_zone`: Keep tasks inside the model smart zone; checkpoint durable context instead of bloating one session. Matched: smart zone, dumb zone, context window, clear the context, compact.
- `google_drive_cloud`: Use Google Drive or Google Cloud as external storage only with explicit source inventory and verified integration state. Matched: google drive, google cloud, cloud, storage.

## Daily Loop

1. Load this checkpoint and the core context files.
2. Grill for alignment before non-trivial planning.
3. Convert aligned work into one focused ticket.
4. Use TDD at the module boundary.
5. Record evidence before review or completion claims.
