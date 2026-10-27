"""Exercise 05: scope memories by customer, bot and ticket.

    user_id  = the customer
    agent_id = the bot (shipping-bot or billing-bot)
    run_id   = the ticket

add() stores all three. search() decides which scope to look in.
Pick the wrong scope and one customer's memories reach another customer.
"""

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory

SCOPES = {
    "Customer · user_id": lambda ctx: {"user_id": ctx["customer"]},
    "Customer + bot · user_id, agent_id": lambda ctx: {"user_id": ctx["customer"], "agent_id": ctx["bot"]},
    "This ticket · run_id": lambda ctx: {"run_id": ctx["ticket"]},
    "Bot only · agent_id  (wrong!)": lambda ctx: {"agent_id": ctx["bot"]},
}

SCENARIO = [
    {"customer": "bob", "bot": "shipping-bot", "scope": "Customer · user_id", "new_ticket": True,
     "say": "Hi, I'm Bob. Please ship my small Scylla plushie to my office: 12 Harbour Street, Oslo."},
    {"customer": "alice", "scope": "Bot only · agent_id  (wrong!)", "new_ticket": True,
     "say": "Hi! Which address will you ship my order to?"},
    {"scope": "Customer · user_id", "new_ticket": True,
     "say": "Hi! Which address will you ship my order to?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def controls(sb):
    st.session_state.setdefault("scope", list(SCOPES)[0])
    sb.radio("search() scope", list(SCOPES), key="scope")
    return {"scope": st.session_state.scope}


def respond(text, ctx, history, turn):
    filters = SCOPES[ctx["scope"]](ctx)
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters=filters, top_k=5)["results"]
        s.detail = [f"filters = {filters}"] + [
            f'{m["memory"]} · {m.get("user_id") or "?"} · score {m["score"]:.2f}' for m in found
        ]

    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    # NEW: every memory now records who said it, to which bot, in which ticket.
    with turn.step("mem0.add") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"],
            agent_id=ctx["bot"],
            run_id=ctx["ticket"],
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


ui.page("05", "Scope memories: customer, bot, ticket")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True, controls=controls)
ui.chat(ctx, respond, SCENARIO)
