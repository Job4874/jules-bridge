# Jules Self-Unblocking Protocol

This file is mandatory operating context. The operator should not have to manually unblock the same class of problem over and over.

## Goal

When blocked, Jules must first run a bounded self-unblocking loop that improves reasoning, tool use, extension discovery, and local knowledge before escalating to the operator.

Use HRE as the public reasoning scaffold:

1. Hypothesis: what is probably blocking progress?
2. Route: which tool, extension, file, endpoint, skill, or repo surface can test it?
3. Evidence: what concrete output proves the hypothesis true or false?

Do not expose private chain-of-thought. Report the HRE checkpoint as concise decision notes and evidence.

## Required Blocker Taxonomy

Classify the blocker before asking for help:

- Tool gap: a route, extension, CLI, skill, or connector may exist but was not discovered or used.
- Knowledge gap: the answer is probably in `context/`, `docs/`, `memory/`, `.agents/skills/`, `jules_inbox/`, or `GET /tentacles`.
- Environment gap: auth, display, network, VM, process, bridge, repo, or provider state is actually unavailable.
- Contract gap: missing JSON flags, wrong route shape, wrong shell, wrong path, stale branch, stale runtime, or stale evidence.
- Implementation gap: code or tests need a narrow patch.
- Evidence gap: work may be complete, but proof is missing or stale.
- Human-policy gap: operator approval is genuinely required for live orders, secrets, paid scaling, destructive cleanup, or plan approval unavailable through the Jules CLI.

## Mandatory Self-Unblocking Loop

Before escalating, do up to three bounded passes:

1. Re-read the current task and name the single blocker in one sentence.
2. Run `GET /tentacles`, then choose the narrowest available route or local file read that can test the blocker.
3. Search the local knowledge surfaces:
   - `jules_inbox/JULES_TOOL_REQUIREMENTS.md`
   - `context/04_ai_workflow_rules.md`
   - `context/05_gotchas.md`
   - `memory/general.md`
   - `memory/reasoning.md`
   - relevant domain memory such as `memory/oracle.md` or `memory/quantower.md`
   - `.agents/AGENTS.md`
   - `.agents/skills/*/SKILL.md`
4. If the blocker is tool-related, inspect the route manifest and the relevant module or skill before declaring the tool missing.
5. If the blocker is a repeated failure, run the `recover` skill and inspect the last request log via `GET /session/log`.
6. If the blocker is a stale or missing-evidence claim, refresh the smallest proof artifact instead of asking the operator to interpret it.
7. After each pass, write a public HRE checkpoint:
   - hypothesis tested
   - tool or file used
   - result
   - next move

Stop after three failed passes only when the remaining need is external to Jules.

## Escalation Rules

Escalate only with this exact shape:

```text
BLOCKER ESCALATION
class:
task:
attempted HRE passes:
tools/files checked:
exact error/output:
why this needs operator input:
smallest requested action:
```

Do not escalate vague statements such as "I need access", "tool unavailable", or "blocked" without route names, file paths, error text, and the recovery attempts already made.

## Learning Requirement

Every resolved blocker must leave reusable knowledge:

- Add or update a short entry in `memory/reasoning.md` for reasoning/tool-use patterns.
- Add a gotcha to `context/05_gotchas.md` if the failure can recur.
- Update `JULES_RESPONSE.md` with what changed, verification, and next action.
- If code/routes changed, run `imprint`, then `review`, then `remember`.

The standard is simple: the next Jules session should know what to try without the operator repeating himself.
