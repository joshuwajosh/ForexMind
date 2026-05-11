"""
ForexMind - Multi-Provider LLM Client
Provider order:
1. Cerebras  -- 1M tokens/day (PRIMARY, FASTEST)
2. Gemini    -- 1500 req/day  (BACKUP 1)
3. Groq      -- 30 req/min    (BACKUP 2)
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# -- Load all keys from .env --------------------------------------------------
CEREBRAS_KEY = os.getenv("CEREBRAS_API_KEY", "").strip()
GOOGLE_KEY   = os.getenv("GOOGLE_API_KEY", "").strip()
GROQ_KEY     = os.getenv("GROQ_API_KEY", "").strip()

# -- Settings -----------------------------------------------------------------
MAX_TOKENS     = 2048
TEMPERATURE    = 0.3
RETRY_DELAY    = 2
RETRY_ATTEMPTS = 2

# -- URLs ---------------------------------------------------------------------
CEREBRAS_URL = "https://api.cerebras.ai/v1/chat/completions"
GEMINI_URL   = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"


class GroqClient:
    """
    Multi-provider LLM client.
    Two interfaces supported so all existing code works:
      llm.call(prompt, system)      -- used by analysts.py, researchers.py
      llm.chat(messages, system)    -- used by execution.py
    """

    def __init__(self):
        print("  [LLM] Provider chain:")
        if CEREBRAS_KEY:
            print("    OK Cerebras  (1M tokens/day) -- PRIMARY")
        else:
            print("    -- Cerebras  -- key missing in .env")
        if GOOGLE_KEY:
            print("    OK Gemini    (1500 req/day)  -- BACKUP 1")
        else:
            print("    -- Gemini    -- key missing in .env")
        if GROQ_KEY:
            print("    OK Groq      (30 req/min)    -- BACKUP 2")
        else:
            print("    -- Groq      -- key missing in .env")

    # -------------------------------------------------------------------------
    # PUBLIC: call(prompt, system)
    # Used by: analysts.py, researchers.py
    # -------------------------------------------------------------------------
    def call(self, prompt, system=None, max_tokens=MAX_TOKENS):
        return self._run_chain(
            messages=[{"role": "user", "content": prompt}],
            system=system,
            max_tokens=max_tokens
        )

    # -------------------------------------------------------------------------
    # PUBLIC: chat(messages, system)
    # Used by: execution.py (trader, risk manager, portfolio manager)
    # -------------------------------------------------------------------------
    def chat(self, messages, system=None, max_tokens=MAX_TOKENS):
        return self._run_chain(
            messages=messages,
            system=system,
            max_tokens=max_tokens
        )

    # -------------------------------------------------------------------------
    # PUBLIC: quick(prompt) -- legacy alias
    # -------------------------------------------------------------------------
    def quick(self, prompt, system=""):
        return self.call(prompt, system)

    # -------------------------------------------------------------------------
    # INTERNAL: try each provider in order
    # -------------------------------------------------------------------------
    def _run_chain(self, messages, system=None, max_tokens=MAX_TOKENS):
        time.sleep(1)

        providers = []
        if CEREBRAS_KEY:
            providers.append(("Cerebras", self._cerebras))
        if GOOGLE_KEY:
            providers.append(("Gemini",   self._gemini))
        if GROQ_KEY:
            providers.append(("Groq",     self._groq))

        if not providers:
            return "[ERROR] No LLM API keys found in .env file!"

        for name, fn in providers:
            try:
                result = fn(messages, system, max_tokens)
                if result and not result.startswith("Error:") and not result.startswith("[ERROR]"):
                    return result
                print(f"  [LLM] {name} failed -- {result[:80]} -- trying next...")
            except Exception as e:
                print(f"  [LLM] {name} exception: {str(e)[:80]} -- trying next...")

        return "Analysis unavailable -- all LLM providers exhausted."

    # -------------------------------------------------------------------------
    # PROVIDER: OpenAI-compatible (Cerebras, Groq)
    # -------------------------------------------------------------------------
    def _openai_compatible(self, url, api_key, model, messages, system, max_tokens):
        full_messages = []
        if system:
            full_messages.append({"role": "system", "content": system})
        full_messages.extend(messages)

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model":       model,
            "messages":    full_messages,
            "max_tokens":  max_tokens,
            "temperature": TEMPERATURE,
        }

        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                r = requests.post(url, headers=headers, json=payload, timeout=60)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"].strip()
                elif r.status_code == 429:
                    wait = RETRY_DELAY * attempt * 2
                    print(f"  [LLM] Rate limited -- waiting {wait}s...")
                    time.sleep(wait)
                elif r.status_code == 401:
                    return "Error: HTTP 401 -- invalid API key"
                elif r.status_code == 402:
                    return "Error: HTTP 402 -- credits exhausted"
                else:
                    return f"Error: HTTP {r.status_code} -- {r.text[:100]}"
            except requests.exceptions.Timeout:
                print(f"  [LLM] Timeout (attempt {attempt}) -- retrying...")
                time.sleep(RETRY_DELAY)
            except Exception as e:
                return f"Error: {str(e)}"
        return "Error: retries exhausted"

    def _cerebras(self, messages, system, max_tokens):
        return self._openai_compatible(
            CEREBRAS_URL, CEREBRAS_KEY,
            "llama-3.3-70b",
            messages, system, max_tokens
        )

    def _groq(self, messages, system, max_tokens):
        return self._openai_compatible(
            GROQ_URL, GROQ_KEY,
            "llama-3.3-70b-versatile",
            messages, system, max_tokens
        )

    # -------------------------------------------------------------------------
    # PROVIDER: Gemini (different API format)
    # -------------------------------------------------------------------------
    def _gemini(self, messages, system, max_tokens):
        parts = []
        if system:
            parts.append(f"[SYSTEM INSTRUCTIONS]\n{system}\n\n[USER REQUEST]")
        for msg in messages:
            role = "Assistant" if msg["role"] == "assistant" else "User"
            parts.append(f"{role}: {msg['content']}")
        combined_prompt = "\n".join(parts)

        url = f"{GEMINI_URL}?key={GOOGLE_KEY}"
        payload = {
            "contents": [{"parts": [{"text": combined_prompt}]}],
            "generationConfig": {
                "maxOutputTokens": max_tokens,
                "temperature":     TEMPERATURE,
            },
        }
        try:
            r = requests.post(
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=60,
            )
            if r.status_code == 200:
                data = r.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts_out = candidates[0].get("content", {}).get("parts", [])
                    if parts_out:
                        return parts_out[0].get("text", "").strip()
                return "Error: Gemini returned empty response"
            elif r.status_code == 429:
                time.sleep(10)
                return "Error: Gemini 429 rate limit"
            elif r.status_code == 400:
                return f"Error: Gemini 400 -- {r.text[:120]}"
            else:
                return f"Error: Gemini HTTP {r.status_code}"
        except Exception as e:
            return f"Error: Gemini exception -- {str(e)}"


# -- Singleton so all agents share one client ---------------------------------
_client = None

def get_llm():
    global _client
    if _client is None:
        _client = GroqClient()
    return _client