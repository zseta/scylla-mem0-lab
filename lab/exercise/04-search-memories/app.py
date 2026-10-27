"""Exercise 04: the bot READS memories with mem0 search() before it answers.

search() embeds the question and runs one ANN query on ScyllaDB,
limited to this customer's memories. The results go into the prompt.
"""

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

SCENARIO = [
    {"customer": "alice", "new_ticket": True,
     "say": "Hi, I'm Alice. My order #4821, a large Scylla plushie, still hasn't arrived. I live in Berlin."},
    {"say": "Please send updates by email, not phone. Thanks!"},
    {"new_ticket": True, "say": "Hi again! Any news about my order?"},
    {"customer": "bob", "new_ticket": True, "say": "Hi! Do you remember what I ordered?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def respond(text, ctx, history, turn):
    # NEW: look up what we know about this customer, before answering.
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=5)["results"]
        s.detail = [f'{m["memory"]} · score {m["score"]:.2f}' for m in found] or "Nothing found for this customer."

    with turn.step("Gemini: reply") as s:
        s.detail = f"Prompt = system prompt + {len(found)} memories + {len(history)} messages of this ticket."
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    with turn.step("mem0.add") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"],
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


ui.page("04", "Read memories with search()")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar()
ui.chat(ctx, respond, SCENARIO)
