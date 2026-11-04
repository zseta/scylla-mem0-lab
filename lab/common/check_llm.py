"""Checks that the LLM answers: one bot reply, and one JSON reply through mem0's own LLM client.

Exit code 0 when both work. Used by the Instruqt track setup and by exercise 00.
Usage: PYTHONPATH=lab python -m common.check_llm
"""

import json
import sys

from common import llm
from common.config import llm_config


def main():
    print(f"Checking {llm.NAME} {llm.MODEL}...", file=sys.stderr)
    reply = llm.chat_reply("You are a test. Answer with one word.", [], "Say: ready")
    if not reply:
        sys.exit("The bot reply was empty.")

    from mem0.utils.factory import LlmFactory

    config = llm_config()
    mem0_llm = LlmFactory.create(config["provider"], config["config"])
    answer = mem0_llm.generate_response(
        [{"role": "system", "content": 'Answer with JSON only: {"facts": ["<one fact>"]}'},
         {"role": "user", "content": "My name is Nora and I live in Berlin."}],
        response_format={"type": "json_object"},
    )
    try:
        json.loads(answer.strip().removeprefix("```json").removesuffix("```"))
    except ValueError:
        sys.exit(f"mem0 got no JSON back: {answer[:200]!r}")
    print(f"{llm.NAME} works ({llm.usage['calls']} calls).", file=sys.stderr)


if __name__ == "__main__":
    main()
