"""Exercise 03: the bot WRITES memories with mem0 add().

After every turn, mem0 extracts facts from the exchange (one Gemini call),
embeds them on CPU and stores them in ScyllaDB.
The bot does not READ memories yet. That comes in exercise 04.
"""

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

SCENARIO = [
    {"customer": "alice", "new_ticket": True,
     "say": "Hi, I'm Alice. My order #4821, a large Scylla plushie, still hasn't arrived. I live in Berlin."},
    {"say": "Please send updates by email, not phone. Thanks!"},
    {"new_ticket": True, "say": "Hi again! Any news about my order?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def respond(text, ctx, history, turn):
    with turn.step("Gemini: reply") as s:
        s.detail = f"Prompt = system prompt + {len(history)} messages of this ticket. No memory read yet."
        reply = gemini.chat_reply(shop.system_prompt(), history, text)

    # NEW: store what was said. mem0 decides which facts are worth keeping.
    with turn.step("mem0.add") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"],
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


ui.page("03", "Write memories with add()")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar()
ui.chat(ctx, respond, SCENARIO)
