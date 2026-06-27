# API & Agent Inventory — Jules Bridge

**Updated:** 2026-06-27  
**Focus:** Google/GCP keys, language models, subscriptions, agent fleet (not Quantower)

---

## Google Cloud — Projectmywebsite

| Resource | Status | Notes |
|----------|--------|-------|
| GCP Project | `projectmywebsite` | Console logged in (operator verified) |
| Generative Language API | **Required** | Enable at APIs & Services → Library → "Generative Language API" |
| Agent Platform API key | In `.env` as `GEMINI_API_KEY` | Prefix `AQ.*` — **429 depleted prepayment credits** |
| Standard API key ("62 APIs") | In GCP Credentials | Prefix `AIzaSy*` — **400 API_KEY_INVALID** for `generativelanguage.googleapis.com` (restrictions or API not enabled) |

### Fix GEMINI for bridge reasoning

Bridge routes `POST /reasoning/solve`, `/reasoning/plan`, `/reasoning/execute_step` use:

| Alias | Model | Env |
|-------|-------|-----|
| `stub` | deterministic | no key |
| `fast` | `gemini-2.0-flash` | `GEMINI_API_KEY` |
| `smart` | `gemini-2.5-pro` | `GEMINI_API_KEY` |

**Required:** A Generative Language API key with billing/credits active — NOT Agent Platform-only.

Steps:
1. GCP Console → APIs & Services → Enable **Generative Language API**
2. Create new API key OR edit "62 APIs" key → add **Generative Language API** to restrictions (or unrestricted for dev)
3. Set `GEMINI_API_KEY=<AIzaSy...>` in `C:\Users\abdul\.jules\.env`
4. Restart bridge: `python bridge.py` (loads `.env` via `notify_email.load_env()`)

Service accounts visible in project (for future agent deploy):
- `vertex-express@projectmywebsite.iam.gserviceaccount.com`
- `trading-bot-deployer@projectmywebsite.iam.gserviceaccount.com`
- Compute Engine default SA

---

## Azure — tibin-agent-vm-01

| Field | Value |
|-------|-------|
| VM Name | `tibin-agent-vm-01` |
| Public IP | `74.249.129.209` |
| OS | Linux |
| Size | Standard_D2s_v3 |
| Subscription | Azure for Students |
| Resource Group | `tibin-agent-vm...` |
| SSH | `azureuser@74.249.129.209` — **blocked: no private key in `~/.ssh`** |
| Azure CLI | `az login` required on host |

---

## Jules Remote Agent Fleet (Google OAuth)

| Component | Path / Value |
|-----------|--------------|
| Jules CLI | `C:\Users\abdul\AppData\Roaming\npm\bin\jules.exe` v0.1.42 |
| OAuth Client | `716860248198-...apps.googleusercontent.com` |
| Remote repo | `Job4874/OracleV5` |
| Preflight | `POST /jules/preflight` |
| Launch | `POST /jules/launch` `{dry_run:false, launch:true}` |
| Cycle | `POST /jules/cycle` |
| COT ledger | `jules_inbox/jules_dispatch/JULES_COT_LEDGER.json` |
| Worker packets | 29 launched, 29 complete (last cycle) |
| Active remote sessions | 40+ (testing, code health, security agents) |

Jules auth paths checked — none exist locally (`~/.jules_auth`, etc.). Remote list works → OAuth session active via CLI.

---

## Bridge Local Agents (Cursor / skills)

| Agent type | Location | Invoke |
|------------|----------|--------|
| Context subagents | `POST /akc/subagents` | cartographer, memory_curator, planner, verification |
| HRM reasoning | `POST /reasoning/solve` | H/L/ACT with Gemini |
| Human-mimic driver | `POST /ui/drive_quantower_login` | credential manager |
| VM boot | `POST /vm/boot_secondary` | `Launch-Bridge-WithVM.cmd` |
| Email tentacle | `POST /notify/email` | Gmail → iCloud (working) |

Cursor plugin subagent: `jules-oracle-operator` at `~/.cursor/plugins/local/jules-oracle-operator/`

Skills (`.agents/skills/`): architect, imprint, review, recover, remember, grill-me, write-prd, prd-to-issues, ralph-loop

---

## Subscriptions & Access (operator logged in)

| Service | Account | Status |
|---------|---------|--------|
| Google Account | atibin@student.cccs.edu | Logged in |
| GCP Console | Projectmywebsite | Logged in |
| Google Gemini (web) | gemini.google.com Pro | Logged in |
| Azure Portal | CCCS student | Logged in, VM running |
| Gmail bridge | atibin7@gmail.com → iCloud | SMTP working |
| Jules CLI | Google OAuth | Remote sessions active |

---

## Current Blockers (API/Agents only)

1. **GEMINI_API_KEY** — wrong type or depleted → reasoning falls back to stub
2. **Azure SSH** — no private key deployed to VM
3. **Jules preflight** — `remote_timeout_possible_auth_required` when remote list times out
4. **google.generativeai** — deprecated; migrate to `google.genai` package long-term

---

## Next Actions

1. Operator: fix GCP Generative Language API key in `.env`, restart bridge
2. Operator: add SSH public key to Azure VM or run `az ssh vm --name tibin-agent-vm-01`
3. Jules: `POST /jules/cycle` with `{launch:true, dry_run:false}` after Gemini live
4. Deploy agent runtime to Azure VM once SSH works

**Never commit API keys.** Store only in `.env` (gitignored).
