"""
Quick Gemini latency diagnostic.
Run from the backend directory:
    .venv\Scripts\python.exe ..\scripts\check_gemini_latency.py

Tests each thinking level and reports wall-clock time + actual thinking tokens used.
This tells you:
  - Whether the API key / network is responsive at all
  - Whether the thinking_budget is actually being honoured (check thinking_tokens column)
  - Which level is fast enough to use in production
"""

import asyncio
import os
import sys
import time

# Allow running from the scripts/ dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

from google import genai
from google.genai import types

API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("gemini_api_key")
MODEL   = os.getenv("LLM_MODEL_GENERATION", "gemini-3.1-flash-lite")

LEVELS = [
    ("none",    "NONE",    0),
    ("minimal", "MINIMAL", 512),
    ("low",     "LOW",     1024),
]

PING_PROMPT = "Reply with the single word: hello"


async def probe(level_name: str, level_enum: str, budget: int):
    client = genai.Client(api_key=API_KEY)

    # Try ThinkingLevel enum first (gemini-3.x)
    try:
        enum_val = getattr(types.ThinkingLevel, level_enum, None)
        thinking_cfg = types.ThinkingConfig(thinking_level=enum_val) if enum_val else types.ThinkingConfig(thinking_budget=budget)
    except AttributeError:
        thinking_cfg = types.ThinkingConfig(thinking_budget=budget)

    config = types.GenerateContentConfig(
        thinking_config=thinking_cfg,
        temperature=0.0,
    )

    t0 = time.monotonic()
    try:
        resp = await client.aio.models.generate_content(
            model=MODEL, contents=PING_PROMPT, config=config
        )
        elapsed = time.monotonic() - t0
        thoughts = getattr(resp.usage_metadata, "thoughts_token_count", "n/a") if resp.usage_metadata else "n/a"
        out_tokens = resp.usage_metadata.candidates_token_count if resp.usage_metadata else "n/a"
        text = (resp.text or "").strip()[:40]
        print(f"  [{level_name:8s}]  {elapsed:5.1f}s   thinking_tokens={thoughts:>6}   out={out_tokens:>4}   reply={text!r}")
    except Exception as e:
        elapsed = time.monotonic() - t0
        print(f"  [{level_name:8s}]  {elapsed:5.1f}s   ERROR: {e}")


async def main():
    if not API_KEY:
        print("ERROR: GEMINI_API_KEY not found in environment / .env")
        return

    print(f"\nGemini latency diagnostic — model: {MODEL}\n")
    print(f"  {'Level':<10}  {'Time':>6}   {'Thinking Tkns':>14}   {'Out Tkns':>9}   Reply")
    print("  " + "-" * 70)
    for name, enum, budget in LEVELS:
        await probe(name, enum, budget)
    print()
    print("Interpretation:")
    print("  thinking_tokens = 0 or n/a  → thinking is OFF  (fastest)")
    print("  thinking_tokens > 0          → model is thinking (adds latency)")
    print("  If 'none' still shows thinking_tokens > 0, the model ignores the budget.")
    print()


if __name__ == "__main__":
    asyncio.run(main())
