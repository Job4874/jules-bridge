# Context Sub-Agent Packet: Context Cartographer

- role_id: context_cartographer
- mission: Inventory source shape, durable rules, risks, and retrieval needs.
- task: Optimize Jules context handling from the active goal attachments.
- context_strategy: smart_truncation_head_tail_memory_store
- source_count: 2
- active_prompt_chars: 1924
- omitted_middle_chars: 28450
- compression_ratio: 0.0632

## Operating Rules
- Keep the main conversation light; do heavy source analysis inside this packet.
- Use source fingerprints and path refs for retrieval; do not assume omitted middle content is irrelevant.
- Preserve head/tail evidence and ask for retrieval only when the missing middle is necessary.
- Do not reveal private chain-of-thought. Return concise rationale, decisions, and evidence.

## Deliverables
- source inventory
- operating rules
- missing or risky source notes

## Source Capsules

### pasted-text-1.txt
- path_ref: path-ref:47be67f6cb96
- sha256: 481519daebbe72768edd9f212e222ed5c856af326937fa97236cc588430473eb
- chars: 6926
- omitted_middle_chars: 5926
- omitted_middle_sha256: a9ffb1ced3637b29bcd70d01f252fa9061af1f910d429bc2bc965136f7043f3d
- signals: long_session_evals, evidence

Head:
```text

Referenced pasted text files:
- pasted text file: path-redacted Read this file before continuing.
Sent as goal
Thursday 9:54 PM

Worked for 55s
Read the pasted file fully enough to identify its shape and risks.

It is a ~344 KB, 8,130-line mixed paste. The first major section is a transcript about building “Job Pilot” with agentic workflow/context files and skills like architect, remember, review, recover, and 
```

Tail:
```text
 The automation is now much closer: it can run the communication cycle and maintain COT state, but actual Jules instance creation is still gated by the external CLI/session-list timeout.

2 memory citations

02_architecture.md
Document · MD

05_gotchas.md
Document · MD

06_progress_tracker.md
Document · MD
Show 2 more

Edited 11 files
+402
-34

Run-JulesDispatch.ps1
+35
-34

bridge.py
+71
-0

context/02_architecture.md
+3
-0

Show 8 more files
Thursday 10:42 PM


```

### pasted-text-2.txt
- path_ref: path-ref:7a9e895ab013
- sha256: 8e2163d980af6250ccae62c04e345f0fe208799821b6f11df5bb0a7cac6b9bd2
- chars: 23524
- omitted_middle_chars: 22524
- omitted_middle_sha256: 0da0f430c811cf46bdd21ab8d3b1232edf8e0f6632bb6a0881b932dabba584e0
- signals: context_engineering, smart_truncation, memory_store, subagents, long_session_evals

Head:
```text
Introduction and speaker background
0:00
All
0:07
[music]
0:15
right, welcome. Thanks so much for
0:16
coming today. Um, I'm here to talk a
0:18
little bit about context windows and I'm
0:19
really excited because I get to talk
0:21
about something that my team and I have
0:23
been building for honestly close to a
0:25
year now, uh, which is RA agent Alex.
0:27
Um, so I'm going to talk a little bit
0:29
about some of the lessons we learned
0:30
about context management an
```

Tail:
```text
ave to
15:38
get a little bit more sophisticated and
15:39
invest in that. But right now, it's
15:41
working. So, we're kind of focused more
15:42
on the long-term memory because I feel
15:44
like that's where I'm getting the most
15:45
complaints.
15:47
Yeah. Any other questions?
15:53
All right. Well, come find me downstairs
15:55
if you have any questions. Thanks so
15:56
much for the the time. [applause]
16:14
[music]

All

From AI Engineer

Computer programming

```

## Completion Report
Return: findings, decisions, files or routes affected, verification needed, blockers.
