"""Gemini wrapper: one place for retries on rate limits and for counting usage.

Both the bot's replies and mem0's fact extraction go through
google.genai Models.generate_content, so patching it once covers every call.
"""

import contextvars
import threading
import time

from google import genai
from google.genai import errors, types
from google.genai.models import Models

from common.config import GEMINI_MODEL, google_api_key

# Who is calling Gemini right now: "reply" for the bot, "mem0" for fact extraction.
purpose = contextvars.ContextVar("purpose", default="mem0")

usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "by_purpose": {}}
_lock = threading.Lock()
_installed = False

# Set by the UI to show "rate limited, waiting Ns" while a retry waits.
on_rate_limit = None

RETRY_DELAYS = [5, 10, 20, 40]


def _record(response):
    meta = getattr(response, "usage_metadata", None)
    with _lock:
        usage["calls"] += 1
        usage["input_tokens"] += getattr(meta, "prompt_token_count", 0) or 0
        usage["output_tokens"] += getattr(meta, "candidates_token_count", 0) or 0
        key = purpose.get()
        usage["by_purpose"][key] = usage["by_purpose"].get(key, 0) + 1


def install():
    global _installed
    if _installed:
        return
    _installed = True
    original = Models.generate_content

    def generate_content(self, *args, **kwargs):
        for attempt, delay in enumerate([0, *RETRY_DELAYS]):
            if delay:
                if on_rate_limit:
                    on_rate_limit(delay)
                time.sleep(delay)
            try:
                response = original(self, *args, **kwargs)
                _record(response)
                return response
            except errors.APIError as e:
                if e.code not in (429, 503) or attempt == len(RETRY_DELAYS):
                    raise

    Models.generate_content = generate_content


_client = None


def client() -> genai.Client:
    global _client
    install()
    if _client is None:
        _client = genai.Client(api_key=google_api_key())
    return _client


def chat_reply(system_prompt: str, history: list[dict], user_message: str) -> str:
    """One bot reply. history: [{"role": "user"|"assistant", "content": str}, ...]"""
    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
        for m in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))
    token = purpose.set("reply")
    try:
        response = client().models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3),
        )
    finally:
        purpose.reset(token)
    return (response.text or "").strip()
