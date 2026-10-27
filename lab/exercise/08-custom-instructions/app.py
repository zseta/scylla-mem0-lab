"""Exercise 08: control WHAT mem0 remembers with custom instructions.

By default mem0 keeps any fact that looks useful, including a card number.
custom_instructions tell the extraction step what to keep and what to drop.
Set them once in the config, or per call with add(prompt=...), as here.
"""

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

PRIVACY_INSTRUCTIONS = """\
Only remember facts that help customer support of a plushie shop:
orders, products, shipping city and address, contact preferences, problems and their status.
Never remember payment card numbers, expiry dates, CVV codes, passwords, phone numbers
or health information. Leave them out completely, do not paraphrase them."""

SENSITIVE = ("Hi, I'm Bob. Charge my card 4111 1111 1111 1111, expiry 12/28, for a Scylla Plushie Family. "
             "Call me at +47 555 01234 when it ships. I'm allergic to wool, is the plushie wool-free?")

SCENARIO = [
    {"customer": "bob", "bot": "billing-bot", "privacy": False, "new_ticket": True, "say": SENSITIVE},
    {"privacy": True, "new_ticket": True, "say": SENSITIVE},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def controls(sb):
    st.session_state.setdefault("privacy", False)
    sb.toggle("Privacy instructions", key="privacy")
    if st.session_state.privacy:
        sb.caption(PRIVACY_INSTRUCTIONS)
    return {"privacy": st.session_state.privacy}


def respond(text, ctx, history, turn):
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=5)["results"]
        s.detail = [f'{m["memory"]} · score {m["score"]:.2f}' for m in found] or "Nothing found."

    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    # NEW: custom instructions for the fact extraction
    with turn.step("mem0.add · privacy " + ("ON" if ctx["privacy"] else "OFF")) as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"], agent_id=ctx["bot"], run_id=ctx["ticket"],
            prompt=PRIVACY_INSTRUCTIONS if ctx["privacy"] else None,
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


ui.page("08", "Custom instructions: control what is remembered")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True, controls=controls)
ui.chat(ctx, respond, SCENARIO)
