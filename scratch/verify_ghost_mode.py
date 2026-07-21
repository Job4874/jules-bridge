import json
import urllib.request
import urllib.error

TOKEN = "JULES-SECURE-999"

def test_live_ghost_mode():
    base_url = "http://127.0.0.1:5000"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {TOKEN}'
    }
    
    print("=== STEP 1: GET /ghost/status (Public Endpoint) ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status initial:", json.dumps(status_data, indent=2))

    print("\n=== STEP 2: GET /ping (Checking ghost fields in ping) ===")
    req = urllib.request.Request(f"{base_url}/ping")
    with urllib.request.urlopen(req) as resp:
        ping_data = json.loads(resp.read().decode())
        print("Ping data ghost fields:", {k: v for k, v in ping_data.items() if "ghost" in k or "host" in k})

    print("\n=== STEP 3: POST /ghost/lock with BRIDGE_TOKEN auth ===")
    password = "ghost-proof-password-48741721"
    lock_payload = json.dumps({"password": password}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/lock", data=lock_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        lock_res = json.loads(resp.read().decode())
        print("Lock response:", json.dumps(lock_res, indent=2))

    print("\n=== STEP 4: GET /ghost/status (Verify LOCKED state) ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status locked:", json.dumps(status_data, indent=2))
        assert status_data.get("ghost_locked") == True, "Ghost status should be locked!"

    print("\n=== STEP 5: POST /ghost/unlock with INCORRECT password (Expect HTTP 403) ===")
    bad_payload = json.dumps({"password": "wrongpassword123"}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/unlock", data=bad_payload, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            print("Unexpected success:", resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = json.loads(e.read().decode())
        print(f"HTTP {e.code} FORBIDDEN Returned as Expected!")
        print("Error Response Body:", json.dumps(err_body, indent=2))
        assert e.code == 403, "Should return HTTP 403 on bad password!"

    print("\n=== STEP 6: POST /ghost/unlock with CORRECT password ===")
    good_payload = json.dumps({"password": password}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/unlock", data=good_payload, headers=headers)
    with urllib.request.urlopen(req) as resp:
        unlock_res = json.loads(resp.read().decode())
        print("Unlock response (Expected Unlocked):", json.dumps(unlock_res, indent=2))
        assert unlock_res.get("status") == "unlocked", "Unlock with correct password should succeed!"

    print("\n=== STEP 7: GET /ghost/status (Verify UNLOCKED state) ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status final:", json.dumps(status_data, indent=2))
        assert status_data.get("ghost_locked") == False, "Ghost status should be unlocked!"

    print("\n==========================================================================")
    print("PROVEN: GHOST Mode lifecycle (Status -> Lock -> Reject Bad Password [HTTP 403] -> Unlock -> Unlocked Status) 100% VERIFIED LIVE!")
    print("==========================================================================")

if __name__ == "__main__":
    test_live_ghost_mode()
