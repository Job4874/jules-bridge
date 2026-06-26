# Context Quality Eval

- generated_at_utc: 2026-06-26T17:35:52.943204+00:00
- task: Optimize context handling sub-agent workflow from current pasted transcripts.
- name: ten_turn_preload_probe_turn_11
- signal: long_session_evals
- preload_turns: 10
- probe_turn: 11
- context_over_budget: False
- purpose: Expose late context failures by preloading 10 turns and checking whether probe turn 11 still uses the retained context correctly.
- release_gate: For long-running workflows, run or document this eval before marking context handling complete.
