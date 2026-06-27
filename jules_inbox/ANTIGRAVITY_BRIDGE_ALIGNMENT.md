# Antigravity ↔ Jules Bridge Alignment

**Updated:** 2026-06-27  
**Operator auth:** gcloud ADC live (`atibin7@gmail.com`, project `tibin-terminal-2026`)

---

## Two Google Projects (do not conflate)

| Project | Purpose | Auth |
|---------|---------|------|
| `projectmywebsite` | Legacy GCP console, Agent Platform keys | API keys in Credentials |
| `tibin-terminal-2026` | **Active** — gcloud ADC, quota project | `gcloud auth login` + `application-default login` |

ADC file: `C:\Users\abdul\AppData\Roaming\gcloud\application_default_credentials.json`

---

## Antigravity Handover Source

Read-only handover bundle (458 files):

```
C:\Users\abdul\.gemini\antigravity-ide\scratch\tibin_handover\TIBIN_CODEX_MASTER_HANDOVER_V2\
```

Start files:
1. `00_START_HERE/README_FIRST.md`
2. `00_START_HERE/CURRENT_HANDOVER_STATUS.md`
3. `05_IMPLEMENTATION_SPECS/API_AND_AUTH_SPEC_SUMMARY.md`
4. `04_CODEX_PROMPTS/CODEX_MASTER_HANDOVER_PROMPT.md`

Bridge read via: `POST /fs/read` with path above.

---

## Bridge Tentacles for Antigravity Tools

| Antigravity need | Jules route |
|------------------|-------------|
| Read handover specs | `POST /fs/read`, `POST /fs/list` |
| Run gcloud / deploy | `POST /shell` (powershell) |
| Gemini / LLM reasoning | `POST /reasoning/solve` `{model:"fast\|smart"}` |
| Context subagents | `POST /akc/subagents` |
| Jules remote workers | `POST /jules/cycle`, `POST /jules/preflight` |
| Operator email loop | `POST /notify/email` |
| GCP auth verify | `POST /shell` → `gcloud auth list` |
| Browser (logged-in Edge) | `POST /apps/launch_browser` |

---

## Gemini Auth Path (recommended after ADC)

1. **Enable APIs** (done): `generativelanguage.googleapis.com`, `aiplatform.googleapis.com` on `tibin-terminal-2026`
2. **Call with ADC token** (works without `.env` API key):

```powershell
$token = gcloud auth application-default print-access-token
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent" `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d '{"contents":[{"parts":[{"text":"hello"}]}]}'
```

3. **Optional:** Create API key in `tibin-terminal-2026` → set `GEMINI_API_KEY` in `.env` → restart bridge

---

## Host Resource Warning

Task Manager showed **99% memory / 100% disk** — close unused Jules remote sessions, browsers, and duplicate bridge/python processes before heavy deploy. Bridge shell OOM on Quantower restart was caused by this.

---

## Operator Email Protocol

One email at a time via `POST /notify/email`. Subject prefix `[JULES-*]` or `[ARCH-BLOCKER]`.

---

## Next Bridge Actions

1. Wire ADC token fallback into `modules/reasoning_module.py` (when `GEMINI_API_KEY` fails)
2. Index Antigravity handover into `POST /akc/context` checkpoint
3. Deploy agent runtime to Azure VM once SSH key added
4. Pull Antigravity API specs into Jules inbox for agent tool manifest
