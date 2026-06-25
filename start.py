import time
import subprocess
from pyngrok import ngrok

print("Starting Jules Bridge locally...")
# Start the Flask app in the background
flask_process = subprocess.Popen(["python", "bridge.py"])
time.sleep(2) # Give it a second to bind

print("Opening ngrok tunnel...")
# Open a tunnel on port 5000
public_url = ngrok.connect(5000, domain="parade-marrow-pulp.ngrok-free.dev")

print("========================================")
print(f"🔗 NGROK URL: {public_url.public_url}")
print("========================================")
print("Keeping process alive. Do not close.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
    flask_process.terminate()
