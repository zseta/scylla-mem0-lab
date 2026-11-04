"""LLM wrapper: one place for retries on rate limits and for counting usage.

The bot runs on Claude on Amazon Bedrock, or on Gemini (LLM_PROVIDER in config.py).
Both the bot's replies and mem0's fact extraction go through one SDK call
(Bedrock Converse in botocore, or google.genai Models.generate_content), so patching it once covers every call.
"""

import contextvars
import threading
import time

from common.config import AWS_REGION, BEDROCK_MODEL, GEMINI_MODEL, LLM_MODEL, LLM_PROVIDER, google_api_key

NAME = "Claude on Bedrock" if LLM_PROVIDER == "bedrock" else "Gemini"
MODEL = LLM_MODEL

# Who is calling the LLM right now: "reply" for the bot, "mem0" for fact extraction.
purpose = contextvars.ContextVar("purpose", default="mem0")

usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "by_purpose": {}}
_lock = threading.Lock()
_installed = False

# Set by the UI to show "rate limited, waiting Ns" while a retry waits.
on_rate_limit = None

RETRY_DELAYS = [5, 10, 20, 40]


def _record(input_tokens, output_tokens):
    with _lock:
        usage["calls"] += 1
        usage["input_tokens"] += input_tokens or 0
        usage["output_tokens"] += output_tokens or 0
        key = purpose.get()
        usage["by_purpose"][key] = usage["by_purpose"].get(key, 0) + 1


def _with_retries(call, retryable):
    for attempt, delay in enumerate([0, *RETRY_DELAYS]):
        if delay:
            if on_rate_limit:
                on_rate_limit(delay)
            time.sleep(delay)
        try:
            return call()
        except Exception as e:
            if not retryable(e) or attempt == len(RETRY_DELAYS):
                raise


def install():
    global _installed
    if _installed:
        return
    _installed = True
    if LLM_PROVIDER == "bedrock":
        _install_bedrock()
    else:
        _install_gemini()


def _install_bedrock():
    from botocore.client import BaseClient
    from botocore.exceptions import ClientError

    original = BaseClient._make_api_call
    throttled = ("ThrottlingException", "ServiceUnavailableException")

    def _make_api_call(self, operation_name, api_params):
        if operation_name != "Converse":  # only bedrock-runtime has Converse
            return original(self, operation_name, api_params)

        def call():
            response = original(self, operation_name, api_params)
            u = response.get("usage", {})
            _record(u.get("inputTokens"), u.get("outputTokens"))
            return response

        return _with_retries(call, lambda e: isinstance(e, ClientError) and e.response["Error"]["Code"] in throttled)

    BaseClient._make_api_call = _make_api_call


def _install_gemini():
    from google.genai import errors
    from google.genai.models import Models

    original = Models.generate_content

    def generate_content(self, *args, **kwargs):
        def call():
            response = original(self, *args, **kwargs)
            meta = getattr(response, "usage_metadata", None)
            _record(getattr(meta, "prompt_token_count", 0), getattr(meta, "candidates_token_count", 0))
            return response

        return _with_retries(call, lambda e: isinstance(e, errors.APIError) and e.code in (429, 503))

    Models.generate_content = generate_content


_client = None


def client():
    global _client
    install()
    if _client is None:
        if LLM_PROVIDER == "bedrock":
            import boto3

            _client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
        else:
            from google import genai

            _client = genai.Client(api_key=google_api_key())
    return _client


def chat_reply(system_prompt: str, history: list[dict], user_message: str) -> str:
    """One bot reply. history: [{"role": "user"|"assistant", "content": str}, ...]"""
    messages = [*history, {"role": "user", "content": user_message}]
    token = purpose.set("reply")
    try:
        if LLM_PROVIDER == "bedrock":
            return _bedrock_reply(system_prompt, messages)
        return _gemini_reply(system_prompt, messages)
    finally:
        purpose.reset(token)


def _bedrock_reply(system_prompt, messages):
    response = client().converse(
        modelId=BEDROCK_MODEL,
        system=[{"text": system_prompt}],
        messages=[{"role": m["role"], "content": [{"text": m["content"]}]} for m in messages],
        inferenceConfig={"temperature": 0.3, "maxTokens": 2000},
    )
    return "".join(block.get("text", "") for block in response["output"]["message"]["content"]).strip()


def _gemini_reply(system_prompt, messages):
    from google.genai import types

    contents = [
        types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])])
        for m in messages
    ]
    response = client().models.generate_content(
        model=GEMINI_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=system_prompt, temperature=0.3),
    )
    return (response.text or "").strip()
