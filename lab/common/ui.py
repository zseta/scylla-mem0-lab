"""Streamlit chrome shared by every exercise: header, sidebar, chat, scenario player, "Under the hood" panel.

Colors and fonts come from the ScyllaDB Design System (scylladb-ds bundle v0.6.69, light theme).
"""

import itertools
import time

import streamlit as st

from common import cql_trace, gemini
from common.config import ASSETS_DIR, CUSTOMERS, GEMINI_MODEL
from common.shop import BOT_NAME, SHOP_NAME
from common.turn import Turn

MASCOT = str(ASSETS_DIR / "mascot.svg")
PLUSHIES = str(ASSETS_DIR / "plushies.jpg")
SCENARIO_PAUSE = 2.5  # seconds between scenario steps

# scylladb-ds light theme tokens, resolved to hex
DS = {
    "bg-page": "#f5f9fd",  # gray-50
    "bg-surface": "#ffffff",
    "bg-accent": "#d8f5fa",  # primary-50
    "bg-code": "#f2f5fe",  # secondary-50
    "text-color": "#465271",  # gray-600
    "text-emphasis": "#161a34",  # gray-800
    "text-muted": "#697797",  # gray-500
    "text-link": "#0079b3",  # primary-600
    "text-code": "#554783",  # secondary-600
    "border-color": "#d1dff3",  # gray-200
    "brand-secondary": "#3b2b57",  # secondary-800
}

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,300..800&family=Roboto+Mono:wght@400;500&display=swap');
html, body, [class*="st-"], .stMarkdown, .stChatMessage {{ font-family: 'Roboto Flex', sans-serif; }}
code, pre, .stCode {{ font-family: 'Roboto Mono', monospace !important; }}
h1, h2, h3 {{ color: {DS['text-emphasis']}; letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: {DS['bg-page']}; border-right: 1px solid {DS['border-color']}; }}
.lab-header {{ display: flex; align-items: center; gap: 14px; padding: 4px 0 10px; border-bottom: 1px solid {DS['border-color']}; margin-bottom: 14px; }}
.lab-header .shop {{ font-size: 1.45rem; font-weight: 700; color: {DS['brand-secondary']}; line-height: 1.1; }}
.lab-header .exercise {{ font-size: 0.9rem; color: {DS['text-muted']}; }}
.hood-title {{ font-weight: 650; color: {DS['text-emphasis']}; margin: 2px 0 6px; }}
.step-head {{ display: flex; justify-content: space-between; font-size: 0.86rem; font-weight: 600;
              color: {DS['text-emphasis']}; background: {DS['bg-accent']}; border-radius: 6px; padding: 4px 10px; margin: 10px 0 4px; }}
.step-head .ms {{ font-family: 'Roboto Mono', monospace; color: {DS['text-link']}; }}
.cql-ms {{ font-family: 'Roboto Mono', monospace; font-size: 0.75rem; color: {DS['text-muted']}; margin: -6px 0 6px 2px; }}
.ticket-note {{ text-align: center; font-size: 0.8rem; color: {DS['text-muted']}; margin: 8px 0; }}
</style>
"""


def page(exercise: str, title: str):
    st.set_page_config(page_title=f"{SHOP_NAME} · {exercise}", page_icon=MASCOT, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    left, right = st.columns([1, 14], vertical_alignment="center")
    left.image(MASCOT, width=52)
    right.markdown(
        f'<div class="lab-header"><div><div class="shop">{SHOP_NAME} · Support</div>'
        f'<div class="exercise">Exercise {exercise}: {title}</div></div></div>',
        unsafe_allow_html=True,
    )
    gemini.on_rate_limit = _rate_limit_notice


def _rate_limit_notice(seconds):
    try:
        st.toast(f"Gemini rate limit hit. Retrying in {seconds}s...")
    except Exception:
        pass


# ---------- conversations and tickets ----------

_ticket_numbers = itertools.count(1001)


def _state():
    s = st.session_state
    s.setdefault("customer", CUSTOMERS[0])
    s.setdefault("tickets", {})  # customer -> current ticket id
    s.setdefault("conversations", {})  # ticket id -> [{"role", "content"}]
    s.setdefault("turns", {})  # ticket id -> last Turn
    s.setdefault("play_index", None)
    return s


def new_ticket(customer: str) -> str:
    s = _state()
    ticket = f"T-{next(_ticket_numbers)}"
    while ticket in s.conversations:
        ticket = f"T-{next(_ticket_numbers)}"
    s.tickets[customer] = ticket
    s.conversations[ticket] = []
    return ticket


def current_ticket(customer: str) -> str:
    s = _state()
    return s.tickets.get(customer) or new_ticket(customer)


# ---------- sidebar ----------


def sidebar(show_bot=False, controls=None) -> dict:
    """Customer picker, ticket, optional bot picker and exercise controls. Returns the context dict."""
    s = _state()
    sb = st.sidebar
    sb.image(PLUSHIES, width="stretch")
    sb.selectbox("Customer · user_id", CUSTOMERS, key="customer")
    ctx = {"customer": s.customer}
    if show_bot:
        s.setdefault("bot", "shipping-bot")
        sb.selectbox("Bot · agent_id", ["shipping-bot", "billing-bot"], key="bot")
        ctx["bot"] = s.bot
    ticket = current_ticket(s.customer)
    sb.markdown(f"**Ticket** `{ticket}`" + (" · run_id" if show_bot else ""))
    if sb.button("New ticket", width="stretch"):
        ticket = new_ticket(s.customer)
    ctx["ticket"] = ticket
    if controls:
        sb.divider()
        ctx.update(controls(sb) or {})
    _usage(sb)
    return ctx


def _usage(sb):
    u = gemini.usage
    sb.divider()
    sb.caption(
        f"Gemini `{GEMINI_MODEL}` · {u['calls']} calls "
        f"({u['by_purpose'].get('reply', 0)} replies, {u['by_purpose'].get('mem0', 0)} mem0) · "
        f"{u['input_tokens'] + u['output_tokens']:,} tokens"
    )


# ---------- chat + scenario player ----------


def chat(ctx: dict, respond, scenario: list[dict] | None = None, height=520):
    """Chat column + "Under the hood" column.

    respond(text, ctx, history, turn) -> reply text
    scenario steps: {"say": "..."} plus optional keys applied before the turn:
      "customer", "bot" (any session_state key), "new_ticket": True,
      "wait": seconds to pause before this step (default SCENARIO_PAUSE)
    """
    s = _state()
    ticket = ctx["ticket"]
    messages = s.conversations.setdefault(ticket, [])

    chat_col, hood_col = st.columns([3, 2], gap="large")
    with chat_col:
        if scenario:
            b1, b2 = st.columns([1, 3], vertical_alignment="center")
            if s.play_index is None:
                if b1.button("▶ Play scenario", type="primary", width="stretch"):
                    s.play_index = 0
                    st.rerun()
            else:
                b1.button(f"Playing {s.play_index + 1}/{len(scenario)}", disabled=True, width="stretch")
        box = st.container(height=height, border=True)
        with box:
            st.markdown(f'<div class="ticket-note">{ctx["customer"]} · ticket {ticket}</div>', unsafe_allow_html=True)
            for m in messages:
                _message(m)
        typed = st.chat_input(f"Write as {ctx['customer']}...")

    pending = typed
    if s.play_index is not None and scenario:
        step = scenario[s.play_index]
        pending = step.get("say")
        if s.play_index > 0:
            # A new memory becomes searchable about a second after add() (the Vector Store follows CDC).
            # Pause between steps so the next question can find what the previous turn stored.
            with box, st.spinner("Next message in a moment..."):
                time.sleep(step.get("wait", SCENARIO_PAUSE))

    if pending:
        _message({"role": "user", "content": pending}, box)
        turn = Turn()
        with box, st.spinner(f"{BOT_NAME} is thinking..."):
            reply = respond(pending, ctx, list(messages), turn)
        messages += [{"role": "user", "content": pending}, {"role": "assistant", "content": reply}]
        s.turns[ticket] = turn

    if s.play_index is not None and scenario:
        s.play_index += 1
        if s.play_index >= len(scenario):
            s.play_index = None
        st.rerun()
    if pending:
        st.rerun()

    with hood_col:
        under_the_hood(s.turns.get(ticket))


def apply_scenario_step(scenario: list[dict] | None):
    """Call BEFORE sidebar(): applies customer/bot/ticket changes of the current scenario step."""
    s = _state()
    if not scenario or s.play_index is None:
        return
    step = scenario[s.play_index]
    for key, value in step.items():
        if key not in ("say", "new_ticket", "wait"):
            s[key] = value
    if step.get("new_ticket"):
        new_ticket(s.customer)


def _message(m, container=None):
    target = container or st
    avatar = MASCOT if m["role"] == "assistant" else "🧑"
    with target.chat_message(m["role"], avatar=avatar):
        st.markdown(m["content"])


# ---------- under the hood ----------


def under_the_hood(turn: Turn | None):
    st.markdown('<div class="hood-title">Under the hood · last turn</div>', unsafe_allow_html=True)
    if not turn:
        st.caption("Send a message. Each step of the turn shows up here, with the CQL it ran on ScyllaDB.")
        return
    for step in turn.steps:
        n = len(step.cql)
        cql_label = f" · {n} CQL" if n else ""
        st.markdown(
            f'<div class="step-head"><span>{step.name}{cql_label}</span>'
            f'<span class="ms">{step.elapsed_ms:,.0f} ms</span></div>',
            unsafe_allow_html=True,
        )
        if step.detail is not None:
            if isinstance(step.detail, list):
                for line in step.detail:
                    st.markdown(f"- {line}")
            else:
                st.caption(str(step.detail))
        show_cql(step.cql)


def show_cql(events, limit=6):
    for e in events[:limit]:
        st.code(cql_trace.format_event(e), language="sql", wrap_lines=True)
        ms = f"{e.elapsed_ms:.1f} ms" if e.elapsed_ms is not None else "pending"
        st.markdown(f'<div class="cql-ms">{ms}{" · ERROR " + e.error if e.error else ""}</div>', unsafe_allow_html=True)
    if len(events) > limit:
        with st.expander(f"{len(events) - limit} more statements"):
            for e in events[limit:]:
                st.code(cql_trace.format_event(e), language="sql", wrap_lines=True)
