"""Exercise 07: tag memories with metadata, then filter searches on it.

add(metadata={...}) stores extra fields with each memory.
search(filters={...}) can filter on them, next to user_id / agent_id / run_id.
"""

import re

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

CATEGORIES = ["shipping", "billing", "product"]

SCENARIO = [
    {"customer": "alice", "bot": "billing-bot", "category": "billing", "filter_on": False, "new_ticket": True,
     "say": "I was charged twice for order #4821. Please refund one of the charges."},
    {"category": "product", "new_ticket": True,
     "say": "Is the large plushie machine washable? I want one for my nephew Leo."},
    {"category": "billing", "filter_on": True, "new_ticket": True,
     "say": "Hi, what's the status of my case?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def controls(sb):
    st.session_state.setdefault("category", CATEGORIES[0])
    st.session_state.setdefault("filter_on", False)
    sb.selectbox("Ticket category · metadata", CATEGORIES, key="category")
    sb.toggle("Search only this category", key="filter_on")
    return {"category": st.session_state.category, "filter_on": st.session_state.filter_on}


def respond(text, ctx, history, turn):
    # NEW: metadata filter next to the entity filter
    filters = {"user_id": ctx["customer"]}
    if ctx["filter_on"]:
        filters["category"] = ctx["category"]
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters=filters, top_k=5)["results"]
        s.detail = [f"filters = {filters}"] + [
            f'{m["memory"]} · {(m.get("metadata") or {}).get("category", "-")} · score {m["score"]:.2f}' for m in found
        ]

    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    # NEW: tag the memories of this turn
    metadata = {"category": ctx["category"]}
    order = re.search(r"#(\d{4})", text)
    if order:
        metadata["order_id"] = order.group(1)
    with turn.step("mem0.add") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"], agent_id=ctx["bot"], run_id=ctx["ticket"],
            metadata=metadata,
        )
        s.detail = [f"metadata = {metadata}"] + [f'{r["event"]}: {r["memory"]}' for r in result["results"]]
    return reply


ui.page("07", "Metadata and filters")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True, controls=controls)
ui.chat(ctx, respond, SCENARIO)
