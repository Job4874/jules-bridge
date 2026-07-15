# MISSION QUEUE — Autonomous Task Inbox

> Drop tasks here. Antigravity picks them up automatically.
> Status: `pending` → `active` → `done` / `failed`
> Assigned to: `playwright_agent` | `jules_fleet` | `cursor` | `claude` | `self`

---

## TASK-001
- **type**: quiz
- **title**: Demo — Google Forms Self-Test
- **url**: https://docs.google.com/forms/d/e/1FAIpQLSdummy/viewform
- **deadline**: 2099-12-31 23:59
- **assigned_to**: playwright_agent
- **status**: done
- **notes**: Demo task. Replace URL with real quiz URL.

---

## TASK-002
- **type**: research
- **title**: Daily briefing — pull top 5 trading news headlines
- **url**: https://www.reuters.com/business/finance/
- **deadline**: daily
- **assigned_to**: playwright_agent
- **status**: done
- **notes**: Navigate, extract headlines, write to memory/daily_briefing.md

---

## TASK-003
- **type**: code
- **title**: Keep Jules PR queue clear — review + merge safe PRs
- **url**: https://github.com/Job4874/jules-bridge/pulls
- **deadline**: daily
- **assigned_to**: jules_fleet
- **status**: pending
- **notes**: Run /jules/fleet-watch, auto-merge non-conflicting PRs

---

## HOW TO ADD A TASK

Copy this template and paste above the last `---`:

```
## TASK-NNN
- **type**: quiz | research | code | form | email | trading
- **title**: Short description
- **url**: https://target-url.com
- **deadline**: YYYY-MM-DD HH:MM | daily | weekly
- **assigned_to**: playwright_agent | jules_fleet | cursor | claude | self
- **status**: done
- **notes**: Any extra context
```
