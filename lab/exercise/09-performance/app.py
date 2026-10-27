"""Exercise 09: keep memory writes off the hot path.

The customer waits for: search (a few ms in ScyllaDB) + the LLM reply.
add() makes its own LLM call to extract facts. That takes about a second,
and the customer does not need to wait for it. Run it in the background.
"""

from concurrent.futures import ThreadPoolExecutor

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

PRIVACY_INSTRUCTIONS = """\
Only remember facts that help customer support of a plushie shop:
orders, products, shipping city and address, contact preferences, problems and their status.
Never remember payment card numbers, expiry dates, CVV codes, passwords, phone numbers
or health information. Leave them out completely, do not paraphrase them."""

SCENARIO = [
    {"customer": "alice", "bot": "shipping-bot", "new_ticket": True,
     "say": "Hi! Can I add gift wrapping to my next order? It's a birthday present for Leo."},
    {"new_ticket": True, "wait": 6, "say": "Hi, quick question: who was the gift for again?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


# NEW: a small worker pool for memory writes
@st.cache_resource
def get_writer():
    return ThreadPoolExecutor(max_workers=2, thread_name_prefix="mem0-add")


memory = get_memory()
writer = get_writer()


def respond(text, ctx, history, turn):
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=5)["results"]
        s.detail = [f'{m["memory"]} · score {m["score"]:.2f}' for m in found] or "Nothing found."

    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    # NEW: queue the write and return the reply right away
    with turn.step("mem0.add · queued in background") as s:
        writer.submit(
            memory.add,
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"], agent_id=ctx["bot"], run_id=ctx["ticket"],
            prompt=PRIVACY_INSTRUCTIONS,
        )
        s.detail = "The customer does not wait for fact extraction. Its CQL runs after this turn, so it is not listed here."
    return reply


ui.page("09", "Performance: memory off the hot path")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True)
ui.chat(ctx, respond, SCENARIO)
