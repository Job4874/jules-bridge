# Jules Worker Packet JT-026-bd5ee7

- instance_index: 21
- status: unknown
- task_type: testing
- source: C:\Users\abdul\.codex\attachments\0c875dac-3076-454f-bf1d-24b611cb0a40\pasted-text-1.txt
- fingerprint: bd5ee7dfff1c
- repo_path: C:\aotp\projects\OracleV5

## Objective
Complete exactly this Jules card: Add test for RegisterSelectorCandidate

## Task Details
- File: OracleV5.Strategy/OracleStrategy_Part15_Selector.cs:453
- Issue: Add test for RegisterSelectorCandidate
- Language: csharp
- Rationale: The method is a straightforward state-modifying or status-returning function, making it easy to mock necessary state and assert expected output or state changes.

## Operating Rules
- Work on one card only; do not opportunistically refactor unrelated code.
- Do not stop at a plan or ask for plan approval; plan briefly in the report and proceed unless a hard blocker prevents work.
- Preserve existing behavior unless the card explicitly asks for behavior change.
- Run the narrowest relevant verification first, then the broader suite if practical.
- Record concrete evidence: commands, test result summaries, hashes, screenshots, or PR links.
- Do not reveal private chain-of-thought. Use a concise rationale, decision log, and evidence checklist instead.
- If blocked, write the blocker, attempted evidence, and the exact next question.

## Completion report
Write a short report with:
- what changed
- verification performed
- files touched
- whether a PR/commit was created
- next action or blocker

## Raw Card Excerpt
```text
🧪 Testing Improvement Task
You are a testing-focused agent. Your mission is to analyze and implement a testing improvement that will increase the reliability and coverage of the codebase.

Task Details
File: OracleV5.Strategy/OracleStrategy_Part15_Selector.cs:453 Issue: Add test for RegisterSelectorCandidate

Language: csharp

Current Code:

public void ResetSelectorCandidates() { if (selectorCandidates == null) selectorCandidates = new List<SelectorCandidate>(); selectorCandidates.Clear(); selectedCandidate = null; } public void RegisterSelectorCandidate(SelectorCandidate candidate) { if (candidate == null) return; if (selectorCandidates == null) selectorCandidates = new List<SelectorCandidate>(); if (string.IsNullOrWhiteSpace(candidate.Symbol)) candidate.Symbol = Instrument != null ? Instrument.FullName : "UNKNOWN";
Rationale: The method is a straightforward state-modifying or status-returning function, making it easy to mock necessary state and assert expected output or state changes.

Your Process
1. 🔍 UNDERSTAND - Analyze the Testing Gap
Review the code that needs testing
Understand what functionality should be tested
Identify edge cases and error conditions
2. 📋 PLAN - Design the Test Strategy
Before writing tests, plan your approach:

What test framework is used in this project?
What existing test patterns should you follow?
What scenarios need to be covered?
3. 🔧 IMPLEMENT - Write Effective Tests
Write clear, focused test cases
Follow existing testing patterns and conventions
Cover happy paths, edge cases, and error conditions
Use appropriate mocks and test doubles
Ensure tests are deterministic and not flaky
4. ✅ VERIFY - Validate the Tests
Run the new tests to ensure they pass
Run the full test suite to ensure no regressions
Verify the tests actually catch bugs (try breaking the code to confirm the test fails)
5. 📝 DOCUMENT - Explain the Testing Improvement
Create a PR with:

Title: "🧪 [testing improvement description]"
Description with:
🎯 What: The testing gap addressed
📊 Coverage: What scenarios are now tested
✨ Result: The improvement in test coverage
Remember: Good tests are the safety net that allows confident refactoring. Write tests that catch real bugs.

Modify OracleV5.Strategy/Diagnostics/OracleStrategy_Part99_SelfTest.cs using the str_replace_editor tool to add a call to TestRegisterSelectorCandidate() inside the ExecuteSimModeSelfTest method.

🔒 Security Vulnerability Fix Task
You are a security-focused agent. Your mission is to analyze and fix a security vulnerability that could put the codebase or its users at risk.

Task Details
File: OracleV5.Strategy/Execution/BracketBuilder.cs:58 Issue: Predictable Random ID Generation for Bracket

Language: csharp

Vulnerable Code:

public BracketBuilder BeginBracket(string symbol, double entryPrice, int quantity) { Symbol = symbol; EntryPrice = entryPrice; Quantity = quantity; BracketId = Guid.NewGuid().ToString("N"); return this; }
Rationale: BracketId should ideally use secure PRNG. Can be fixed cleanly without breaking changes.

Your Process
1. 🔍 UNDERSTAND - Analyze the Security Issue
Review the surrounding code and understand the data flow
Identify the specific vulnerability type and its potential impact
Consider attack vectors and exploitation scenarios
2. 🛡️ ASSESS - Evaluate the Risk
Before making changes, assess the security risk:

What data or functionality could be compromised?
Who could exploit this vulnerability?
What is the blast radius if exploited?
If possible, search for known CVEs, advisories, or recommended fixes for this vulnerability type
This may reveal simpler solutions (e.g., dependency updates) or important context
3. 🔧 IMPLEMENT - Fix with Security in Mind
Write a secure fix that eliminates the vulnerability
Follow security best practices for this type of issue
Ensure the fix doesn't introduce new vulnerabilities
Preserve existing functionality
4. ✅ VERIFY - Validate the Fix
Run format and lint checks
```
