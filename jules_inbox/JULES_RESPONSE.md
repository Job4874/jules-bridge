# Jules - API/Agent Focus (Quantower deprioritized)

**Updated:** 2026-06-27T04:08Z

## Diagnosis: Why Gemini reasoning returns STUB

| Key in .env | Type | Test result |
|-------------|------|-------------|
| AQ.Ab8RN... | Agent Platform | 429 prepayment credits depleted |
| AIzaSy... (GCP "62 APIs") | Standard GCP | 400 API_KEY_INVALID for generativelanguage |

Bridge `/reasoning/solve` model=smart falls back to stub when Gemini fails.

## What works NOW

- Jules CLI remote fleet (40+ sessions, OAuth active)
- POST /notify/email (Gmail SMTP)
- POST /jules/cycle (29/29 COT)
- GCP/Azure/Gemini web consoles (operator logged in)

## Operator fix (5 min)

1. GCP ? Enable **Generative Language API** on Projectmywebsite
2. Create fresh API key with that API enabled + billing
3. Update GEMINI_API_KEY in .env, restart bridge
4. Azure: add SSH key to tibin-agent-vm-01 for agent deploy

Full inventory: jules_inbox/API_AGENT_INVENTORY.md