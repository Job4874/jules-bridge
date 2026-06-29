#!/usr/bin/env python3
"""Test Gemini and OpenRouter connectivity from this VM."""
import os
from pathlib import Path

# Load env
env_file = Path(os.path.expanduser("~/.jules_worker.env"))
print(f"Env file: {env_file} exists={env_file.exists()}")

if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            os.environ[k.strip()] = v.strip()

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
OR_KEY = os.environ.get("OPENROUTER_API_KEY", "")

print(f"GEMINI_KEY loaded: {'YES (len=' + str(len(GEMINI_KEY)) + ')' if GEMINI_KEY else 'NO'}")
print(f"OR_KEY loaded:     {'YES (len=' + str(len(OR_KEY)) + ')' if OR_KEY else 'NO'}")

import requests

# Test Gemini
print("\n--- Testing Gemini ---")
try:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    payload = {"contents": [{"role": "user", "parts": [{"text": "Reply GEMINI_OK"}]}]}
    r = requests.post(url, json=payload, timeout=20)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        print(f"Response: {text}")
    else:
        print(f"Error: {r.text[:300]}")
except Exception as e:
    print(f"Exception: {e}")

# Test OpenRouter
print("\n--- Testing OpenRouter ---")
try:
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        json={"model": "google/gemma-3-27b-it:free",
              "messages": [{"role": "user", "content": "Reply OPENROUTER_OK"}]},
        headers={"Authorization": f"Bearer {OR_KEY}"},
        timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        text = r.json()["choices"][0]["message"]["content"]
        print(f"Response: {text[:100]}")
    else:
        print(f"Error: {r.text[:300]}")
except Exception as e:
    print(f"Exception: {e}")

print("\n--- Done ---")
