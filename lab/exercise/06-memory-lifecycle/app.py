"""Exercise 06: manage the memory lifecycle from a rep dashboard.

mem0 v3 only ADDs memories. When a fact changes ("I moved"), the old fact stays.
Fixing that is the application's job:
    get_all()   list a customer's memories
    update()    rewrite one memory
    delete()    remove one memory
    history()   see how a memory changed
    delete_all() forget a customer ("right to be forgotten")
"""

import streamlit as st

from common import gemini, shop, ui
from common.memory import create_memory
from common.turn import Turn

SCENARIO = [
    {"customer": "alice", "bot": "shipping-bot", "new_ticket": True,
     "say": "Hi, I moved! My new address is Rua Augusta 10, Lisbon. Please use it from now on."},
    {"new_ticket": True, "say": "Hi! Which address will you ship my next order to?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    return create_memory()


memory = get_memory()


def respond(text, ctx, history, turn):
    filters = {"user_id": ctx["customer"]}
    with turn.step("mem0.search") as s:
        found = memory.search(text, filters=filters, top_k=5)["results"]
        s.detail = [f'{m["memory"]} · score {m["score"]:.2f}' for m in found] or "Nothing found."
    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)
    with turn.step("mem0.add") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"], agent_id=ctx["bot"], run_id=ctx["ticket"],
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


# NEW: the rep dashboard


def run_action(name, fn):
    turn = Turn()
    with turn.step(name) as s:
        s.detail = fn()
    st.session_state.dash_turn = turn
    st.rerun()


def show_history(memory_id):
    changes = memory.history(memory_id)
    return [f'{c["created_at"][:19]} · {c["event"]}: {c.get("old_memory") or "-"} → {c.get("new_memory") or "-"}'
            for c in changes] or "No history."


def dashboard(ctx):
    customer = ctx["customer"]
    listing = Turn()
    with listing.step("mem0.get_all") as s:
        rows = memory.get_all(filters={"user_id": customer}, top_k=100)["results"]
        s.detail = f"{len(rows)} memories"

    left, right = st.columns([3, 2], gap="large")
    with left:
        st.markdown(f"#### Memories of {customer} · {len(rows)}")
        for r in sorted(rows, key=lambda r: r.get("created_at") or ""):
            mid = r["id"]
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([8, 2, 2, 2], vertical_alignment="center")
                c1.markdown(r["memory"])
                c1.caption(f'id {mid[:8]} · bot {r.get("agent_id") or "-"} · ticket {r.get("run_id") or "-"} · '
                           f'created {(r.get("created_at") or "")[:16]}')
                with c2.popover("Edit"):
                    text = st.text_area("Memory", r["memory"], key=f"edit-{mid}")
                    if st.button("Save", key=f"save-{mid}", type="primary"):
                        run_action("mem0.update", lambda: memory.update(mid, text=text)["message"])
                if c3.button("History", key=f"hist-{mid}"):
                    run_action("mem0.history", lambda: show_history(mid))
                if c4.button("Delete", key=f"del-{mid}"):
                    run_action("mem0.delete", lambda: memory.delete(mid)["message"])

        st.divider()
        sure = st.checkbox(f"I really want to forget everything about {customer}")
        if st.button(f"Forget {customer} · delete_all()", disabled=not sure):
            run_action("mem0.delete_all", lambda: memory.delete_all(user_id=customer)["message"])

    with right:
        ui.under_the_hood(st.session_state.get("dash_turn") or listing)


ui.page("06", "Memory lifecycle: update, delete, history")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True)
chat_tab, dash_tab = st.tabs(["Chat", "Rep dashboard"])
with dash_tab:
    dashboard(ctx)
with chat_tab:
    ui.chat(ctx, respond, SCENARIO)
