# STOP CHECKING STATUS — START CODING TICKET 007

## Time Check
You have been running for 20 MINUTES. Your bridge log shows ZERO file reads,
ZERO shell commands, ZERO code changes. You have only been checking status
routes (health, dashboard, VM, oracle) and sending emails.

## THIS IS A SOFT DOOM LOOP
Repeating status checks without doing work IS a doom loop. Rule 2 in
memory/reasoning.md says: "If you detect yourself calling any route > 5x,
STOP and run the recover skill."

## YOUR TASK RIGHT NOW

### Step 1: Read Ticket 007
The file is at `doc/tickets/007_dashboard_circuit_breaker.md` in your local repo.
You can read it with `cat` or by opening it. You do NOT need the bridge for this.

### Step 2: Write the test FIRST (TDD)
Create `tests/test_circuit_breaker.py` with the red tests before writing any
implementation code.

### Step 3: Implement the circuit breaker
Add `_circuit_breaker_check()` as a `@app.before_request` hook in `bridge.py`.

### Step 4: Run tests
`python3 -m pytest tests/ -v`

### Step 5: Record evidence
`POST /retrospective/record_evidence` with the test output hash.

## DO NOT
- Call GET /health, GET /dashboard/status, or POST /vm/resource_pressure again
- Send more emails until you have CODE to show
- Check tentacles again — you already know the routes

## START NOW
Every minute you spend checking status is a minute NOT spent on the circuit breaker.
