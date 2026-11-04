"""Exercise 08: high availability. Stop a ScyllaDB node while the bot keeps working.

Every row has 3 replicas, one per rack. Reads and writes use QUORUM:
2 of 3 replicas must answer. With one node down, 2 are still up.
"""

import streamlit as st
from cassandra import ConsistencyLevel

from common import gemini, shop, ui
from common.memory import create_memory, set_consistency

PRIVACY_INSTRUCTIONS = """\
Only remember facts that help customer support of a plushie shop:
orders, products, shipping city and address, contact preferences, problems and their status.
Never remember phone numbers or health information.
Leave them out completely, do not paraphrase them."""

SCENARIO = [
    {"customer": "nora", "bot": "shipping-bot", "new_ticket": True,
     "say": "Hi! Please remind me: what's my latest shipping address?"},
    {"say": "Thanks! If I'm not home, please leave my parcels at the café downstairs."},
    {"new_ticket": True, "say": "Hi! Where will the courier leave my parcel if I'm out?"},
]


@st.cache_resource(show_spinner="Connecting to ScyllaDB...")
def get_memory():
    memory = create_memory()
    # NEW: QUORUM for every read and write mem0 makes
    set_consistency(memory, ConsistencyLevel.QUORUM)
    return memory


memory = get_memory()


def cluster_status(sb):
    """What the driver knows about each node right now."""
    sb.markdown("**Cluster** · consistency `QUORUM`")
    hosts = sorted(memory.vector_store.cluster.metadata.all_hosts(), key=lambda h: h.rack or "")
    for h in hosts:
        sb.markdown(f'{"🟢" if h.is_up else "🔴"} `{h.address}` · {h.rack} · {"up" if h.is_up else "DOWN"}')
    if sb.button("Refresh status", width="stretch"):
        st.rerun()


def respond(text, ctx, history, turn):
    with turn.step("mem0.search · QUORUM") as s:
        found = memory.search(text, filters={"user_id": ctx["customer"]}, top_k=10)["results"]
        s.detail = [f'{m["memory"]} · score {m["score"]:.2f}' for m in found] or "Nothing found."

    with turn.step("Gemini: reply"):
        reply = gemini.chat_reply(shop.system_prompt([m["memory"] for m in found]), history, text)

    with turn.step("mem0.add · QUORUM") as s:
        result = memory.add(
            [{"role": "user", "content": text}, {"role": "assistant", "content": reply}],
            user_id=ctx["customer"], agent_id=ctx["bot"], run_id=ctx["ticket"],
            prompt=PRIVACY_INSTRUCTIONS,
        )
        s.detail = [f'{r["event"]}: {r["memory"]}' for r in result["results"]] or "No new facts in this exchange."
    return reply


ui.page("08", "High availability: lose a node, keep the memory")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar(show_bot=True, controls=cluster_status)
ui.chat(ctx, respond, SCENARIO)
