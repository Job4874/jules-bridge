# No Slop Workflow

- generated_at_utc: 2026-06-26T17:35:52.943204+00:00
- task: Optimize context handling sub-agent workflow from current pasted transcripts.
- mode: spec_first
- context_window_chars: 170000
- target_utilization_ratio: 0.4
- active_prompt_chars: 3382
- over_budget: False
- recommendation: within_budget: keep research, plan, and implementation phases explicit

## Phases

### research
- artifact: RESEARCH.md
- goal: Find how the system works and identify exact files, flows, and line references.
- done_when: Reviewer can understand the system path without re-searching the repo.

### plan
- artifact: IMPLEMENTATION_PLAN.md
- goal: Specify every intended change, file target, test, and rollback concern before editing code.
- done_when: Plan is shorter than the change and catches design mistakes before code.

### implement
- artifact: CODE_AND_EVIDENCE
- goal: Make the planned changes, keep context under budget, and update the plan as phases complete.
- done_when: Tests, route smoke, hashes, or runtime evidence prove the requested behavior.

## Review Gates

- review_research_before_plan
- review_plan_before_code
- record_evidence_before_done
