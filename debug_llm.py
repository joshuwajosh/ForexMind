"""
debug_llm.py
Run this in D:\algotrade\ForexMind\
It tests all 4 LLM keys and shows EXACTLY what error each one gives.

Usage:
  python debug_llm.py
"""

import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()

CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "")
GOOGLE_KEY   = os.getenv("GOOGLE_API_KEY", "")
DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GROQ_KEY     = os.getenv("GROQ_API_KEY", "")

TEST_PROMPT  = "Say the word HELLO and nothing else."

print("\n" + "="*55)
print("  ForexMind — LLM API Key Debugger")
print("="*55)

# ── Helper ─────────────────────────────────────────────
def openai_test(name, url, key, model):
    print(f"\n[{name}]")
    if not key:
        print("  ❌ Key is EMPTY in .env — not set")
        return
    print(f"  Key starts with : {key[:12]}...")
    try:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model":      model,
                "messages":   [{"role": "user", "content": TEST_PROMPT}],
                "max_tokens": 20,
            },
            timeout=20,
        )
        print(f"  HTTP Status     : {r.status_code}")
        if r.status_code == 200:
            text = r.json()["choices"][0]["message"]["content"].strip()
            print(f"  ✅ WORKING — Response: {text}")
        else:
            print(f"  ❌ FAILED  — Response body: {r.text[:300]}")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")

# ── 1. Cerebras ────────────────────────────────────────
openai_test(
    "Cerebras",
    "https://api.cerebras.ai/v1/chat/completions",
    CEREBRAS_KEY,
    "llama-3.3-70b"
)
time.sleep(1)

# ── 2. Gemini ──────────────────────────────────────────
print(f"\n[Gemini]")
if not GOOGLE_KEY:
    print("  ❌ Key is EMPTY in .env — not set")
else:
    print(f"  Key starts with : {GOOGLE_KEY[:12]}...")
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GOOGLE_KEY}"
        r = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={"contents": [{"parts": [{"text": TEST_PROMPT}]}]},
            timeout=20,
        )
        print(f"  HTTP Status     : {r.status_code}")
        if r.status_code == 200:
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            print(f"  ✅ WORKING — Response: {text}")
        else:
            print(f"  ❌ FAILED  — Response body: {r.text[:300]}")
    except Exception as e:
        print(f"  ❌ EXCEPTION: {e}")
time.sleep(1)

# ── 3. DeepSeek ────────────────────────────────────────
openai_test(
    "DeepSeek",
    "https://api.deepseek.com/v1/chat/completions",
    DEEPSEEK_KEY,
    "deepseek-chat"
)
time.sleep(1)

# ── 4. Groq ────────────────────────────────────────────
openai_test(
    "Groq",
    "https://api.groq.com/openai/v1/chat/completions",
    GROQ_KEY,
    "llama3-70b-8192"
)

# ── Summary ────────────────────────────────────────────
print("\n" + "="*55)
print("  Copy the output above and share it — ")
print("  we'll fix whichever ones show ❌")
print("="*55 + "\n")
