## 2026-09-15 - Hardcoded token in VM relay fixed
**Vulnerability:** A static hardcoded token (`JULES-VM-WORKER-999`) was used in `modules/vm_relay.py` to authenticate HTTP requests to the worker VM, exposing the service to unauthorized commands from anyone reading the repository source.
**Learning:** Hardcoded authentication credentials, even in local development or proxy relays, create massive supply chain and operational risks. Tokens must be dynamically generated.
**Prevention:** Avoid static token defaults in code. Use `secrets.token_hex()` to generate runtime tokens, persist them via hidden `.env` files added to `.gitignore`, and validate them on startup rather than trusting static fallbacks.
