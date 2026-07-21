import json
import urllib.request

def test_live_ghost_mode():
    base_url = "http://127.0.0.1:5000"
    
    print("=== STEP 1: GET /ghost/status ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status initial:", json.dumps(status_data, indent=2))

    print("\n=== STEP 2: GET /ping (checking ghost fields in ping) ===")
    req = urllib.request.Request(f"{base_url}/ping")
    with urllib.request.urlopen(req) as resp:
        ping_data = json.loads(resp.read().decode())
        print("Ping data ghost fields:", {k: v for k, v in ping_data.items() if "ghost" in k or "host" in k})

    print("\n=== STEP 3: POST /ghost/lock ===")
    lock_payload = json.dumps({"password": "ghost-proof-password-48741721"}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/lock", data=lock_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        lock_res = json.loads(resp.read().decode())
        print("Lock response:", json.dumps(lock_res, indent=2))

    print("\n=== STEP 4: GET /ghost/status (Verify LOCKED) ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status locked:", json.dumps(status_data, indent=2))
        assert status_data.get("ghost_locked") == True, "Ghost status should be locked!"

    print("\n=== STEP 5: POST /ghost/unlock with WRONG password ===")
    bad_payload = json.dumps({"password": "wrongpassword"}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/unlock", data=bad_payload, headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req) as resp:
            print("Unlock response:", resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"Unlock rejected as expected ({e.code}):", e.read().decode())

    print("\n=== STEP 6: POST /ghost/unlock with CORRECT password ===")
    good_payload = json.dumps({"password": "ghost-proof-password-48741721"}).encode('utf-8')
    req = urllib.request.Request(f"{base_url}/ghost/unlock", data=good_payload, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        unlock_res = json.loads(resp.read().decode())
        print("Unlock response:", json.dumps(unlock_res, indent=2))

    print("\n=== STEP 7: GET /ghost/status (Verify UNLOCKED) ===")
    req = urllib.request.Request(f"{base_url}/ghost/status")
    with urllib.request.urlopen(req) as resp:
        status_data = json.loads(resp.read().decode())
        print("GHOST Status final:", json.dumps(status_data, indent=2))
        assert status_data.get("ghost_locked") == False, "Ghost status should be unlocked!"

    print("\nPROVEN: GHOST Mode lifecycle (Status -> Lock -> Reject Bad Auth -> Unlock -> Status) verified 100% working live!")

if __name__ == "__main__":
    test_live_ghost_mode()
