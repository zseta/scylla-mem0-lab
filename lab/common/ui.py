"""Streamlit chrome shared by every exercise: header, sidebar, chat, scenario player, "Under the hood" panel.

Colors and fonts come from the ScyllaDB Design System (scylladb-ds bundle v0.6.69, light and dark themes).
Streamlit's own widgets get the same colors from run_app.sh.
"""

import base64
import html
import itertools
import time

import streamlit as st

from common import cql_trace, gemini
from common.config import ASSETS_DIR, CUSTOMERS, GEMINI_MODEL
from common.shop import BOT_NAME, SHOP_NAME
from common.turn import Turn

MASCOT = str(ASSETS_DIR / "mascot.svg")
MASCOT_URI = "data:image/svg+xml;base64," + base64.b64encode((ASSETS_DIR / "mascot.svg").read_bytes()).decode()
PLUSHIES = str(ASSETS_DIR / "plushies.jpg")
SCENARIO_PAUSE = 2.5  # minimum seconds between two scenario steps

# scylladb-ds theme tokens, resolved to hex: (light, dark)
DS = {
    "bg-page": ("#f5f9fd", "#161a34"),  # gray-50 / gray-800
    "bg-accent": ("#d8f5fa", "#05233e"),  # primary-50 / primary-950
    "text-emphasis": ("#161a34", "#f5f9fd"),  # gray-800 / gray-50
    "text-muted": ("#697797", "#8a9cbc"),  # gray-500 / gray-400
    "text-link": ("#0079b3", "#20c2f4"),  # primary-600 / primary-400
    "border-color": ("#d1dff3", "#242c48"),  # gray-200 / gray-700
    "brand": ("#3b2b57", "#c6caf7"),  # secondary-800 / secondary-200
}
_light = " ".join(f"--{k}: {v[0]};" for k, v in DS.items())
_dark = " ".join(f"--{k}: {v[1]};" for k, v in DS.items())

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Roboto+Flex:opsz,wght@8..144,300..800&family=Roboto+Mono:wght@400;500&display=swap');
:root {{ {_dark} }}
:root[data-theme="light"] {{ {_light} }}
html, body, [class*="st-"], .stMarkdown, .stChatMessage {{ font-family: 'Roboto Flex', sans-serif; }}
code, pre, .stCode {{ font-family: 'Roboto Mono', monospace !important; }}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
[data-testid="stColumn"]:has(.hood-title) pre code {{ font-size: 0.75rem; }}  /* CQL: fit ~30 chars per line */
h1, h2, h3 {{ color: var(--text-emphasis); letter-spacing: -0.01em; }}
[data-testid="stSidebar"] {{ background: var(--bg-page); border-right: 1px solid var(--border-color); }}
[data-testid="stMainBlockContainer"] {{ padding-top: 3.5rem; }}
.theme-switching [data-baseweb="popover"] {{ opacity: 0; }}
.lab-header {{ display: flex; align-items: center; gap: 14px; padding: 4px 0 10px; border-bottom: 1px solid var(--border-color); }}
.lab-header img {{ width: 48px; height: 48px; flex: none; }}
.lab-header .titles {{ flex: 1; min-width: 0; }}
.lab-header .shop {{ font-size: 1.45rem; font-weight: 700; color: var(--brand); line-height: 1.15; }}
.lab-header .exercise {{ font-size: 0.9rem; color: var(--text-muted); }}
.theme-toggle {{ flex: none; font: inherit; font-size: 0.85rem; color: var(--text-emphasis); background: transparent;
                 border: 1px solid var(--border-color); border-radius: 999px; padding: 5px 12px; cursor: pointer; }}
.theme-toggle:hover {{ border-color: var(--text-link); color: var(--text-link); }}
:root:not([data-theme="light"]) .theme-toggle .to-dark, :root[data-theme="light"] .theme-toggle .to-light {{ display: none; }}
.hood-title {{ font-weight: 650; color: var(--text-emphasis); margin: 2px 0 6px; }}
.step-head {{ display: flex; justify-content: space-between; gap: 8px; font-size: 0.86rem; font-weight: 600;
              color: var(--text-emphasis); background: var(--bg-accent); border-radius: 6px; padding: 4px 10px; margin: 10px 0 4px; }}
.step-head .ms {{ font-family: 'Roboto Mono', monospace; color: var(--text-link); white-space: nowrap; }}
.cql-ms {{ font-family: 'Roboto Mono', monospace; font-size: 0.75rem; color: var(--text-muted); margin: -6px 0 6px 2px; }}
.ticket-note {{ text-align: center; font-size: 0.8rem; color: var(--text-muted); margin: 8px 0; }}
.next-step {{ font-size: 0.85rem; color: var(--text-muted); margin: 2px 0 6px; }}
.next-step b {{ color: var(--text-emphasis); }}
@media (max-width: 1100px) {{
  /* chat above "Under the hood" once the chat column gets too narrow */
  [data-testid="stHorizontalBlock"]:has(.hood-title) {{ flex-wrap: wrap; }}
  [data-testid="stHorizontalBlock"]:has(.hood-title) > [data-testid="stColumn"] {{ flex: 1 1 100%; min-width: 100%; }}
}}
@media (max-width: 640px) {{
  [data-testid="stMainBlockContainer"] {{ padding-top: 3rem; }}
  .lab-header {{ gap: 10px; }}
  .lab-header img {{ width: 36px; height: 36px; }}
  .lab-header .shop {{ font-size: 1.1rem; }}
  .lab-header .exercise {{ font-size: 0.8rem; }}
  .theme-toggle .label {{ display: none; }}
}}
</style>
"""

# Light/Dark switch. Streamlit keeps its theme choice in localStorage and switches it from the ⋮ menu.
# The button drives that menu, so the switch needs no page reload and the chat stays.
# The first visit picks Dark. html[data-theme] tells the CSS above which colors to use.
THEME_JS = """
<script>
(() => {
  const KEY = `stActiveTheme-${location.pathname}-v2`;
  const stored = () => { try { return JSON.parse(localStorage.getItem(KEY)); } catch { return null; } };
  const current = () => ["Dark", "Light"].includes(stored()) ? stored().toLowerCase()
    : (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
  const sync = () => { document.documentElement.dataset.theme = current(); };
  const pick = async (name) => {
    const menu = document.querySelector('[data-testid="stMainMenu"] button');
    if (!menu) return;
    document.documentElement.classList.add("theme-switching");
    menu.click();
    for (let i = 0; i < 40; i++) {
      const item = document.querySelector(`[data-testid="stMainMenuItem-theme-${name}"]`);
      if (item) { item.click(); break; }
      await new Promise((r) => setTimeout(r, 25));
    }
    if (document.querySelector('[data-testid="stMainMenuList"]')) menu.click();
    document.documentElement.classList.remove("theme-switching");
    sync();
  };
  if (!window.plushieTheme) {
    window.plushieTheme = { pick, current };
    setInterval(sync, 500);  // also follows a switch made in the ⋮ menu
    try {
      if (!localStorage.getItem("plushie-theme-set")) {
        localStorage.setItem("plushie-theme-set", "1");
        if (!["Dark", "Light"].includes(stored())) setTimeout(() => pick("Dark"), 300);
      }
    } catch {}
  }
  sync();
  document.querySelectorAll(".theme-toggle").forEach((b) => {
    b.onclick = () => window.plushieTheme.pick(window.plushieTheme.current() === "dark" ? "Light" : "Dark");
  });
})();
</script>
"""


def page(exercise: str, title: str):
    st.set_page_config(page_title=f"{SHOP_NAME} · {exercise}", page_icon=MASCOT, layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.html(
        f'<div class="lab-header"><img src="{MASCOT_URI}" alt="">'
        f'<div class="titles"><div class="shop">{SHOP_NAME} · Support</div>'
        f'<div class="exercise">Exercise {exercise}: {title}</div></div>'
        '<button class="theme-toggle" type="button" title="Switch light/dark mode">'
        '<span class="to-light">☀<span class="label"> Light</span></span>'
        '<span class="to-dark">☾<span class="label"> Dark</span></span></button></div>' + THEME_JS,
        unsafe_allow_javascript=True,
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
    s.setdefault("play_index", None)  # next scenario step, None when no scenario is running
    s.setdefault("play_go", False)  # True: run that step in this script run
    s.setdefault("play_last", 0.0)  # time.monotonic() at the end of the last scenario step
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
      "wait": minimum seconds since the previous step (default SCENARIO_PAUSE)
    The scenario sends one step per click, so the presenter sets the pace.
    """
    s = _state()
    ticket = ctx["ticket"]
    messages = s.conversations.setdefault(ticket, [])

    chat_col, hood_col = st.columns([3, 2], gap="large")
    with chat_col:
        if scenario:
            _scenario_controls(scenario)
        box = st.container(height=height, border=True)
        with box:
            st.markdown(f'<div class="ticket-note">{ctx["customer"]} · ticket {ticket}</div>', unsafe_allow_html=True)
            for m in messages:
                _message(m)
        typed = st.chat_input(f"Write as {ctx['customer']}...")

    pending = typed
    playing = scenario and s.play_index is not None and s.play_go
    if playing:
        step = scenario[s.play_index]
        pending = step.get("say")
        # A new memory becomes searchable about a second after add() (the Vector Store follows CDC).
        # Wait so the next question can find what the previous turn stored.
        left = step.get("wait", SCENARIO_PAUSE) - (time.monotonic() - s.play_last)
        if s.play_index > 0 and left > 0:
            with box, st.spinner("Waiting for the memory to become searchable..."):
                time.sleep(left)

    if pending:
        _message({"role": "user", "content": pending}, box)
        turn = Turn()
        with box, st.spinner(f"{BOT_NAME} is thinking..."):
            reply = respond(pending, ctx, list(messages), turn)
        messages += [{"role": "user", "content": pending}, {"role": "assistant", "content": reply}]
        s.turns[ticket] = turn

    if playing:
        s.play_go = False
        s.play_last = time.monotonic()
        s.play_index += 1
        if s.play_index >= len(scenario):
            s.play_index = None
    if pending:
        st.rerun()

    with hood_col:
        under_the_hood(s.turns.get(ticket))


def _scenario_controls(scenario: list[dict]):
    """▶ Play scenario, then Next ▶ for each step, with a preview of the next message."""
    s = _state()
    index = s.play_index or 0
    with st.container(horizontal=True, vertical_alignment="center"):
        if s.play_index is None:
            if st.button("▶ Play scenario", type="primary"):
                s.play_index, s.play_go = 0, True
                st.rerun()
        else:
            busy = s.play_go  # this step runs below, in this script run
            label = f"Sending {index + 1}/{len(scenario)}..." if busy else f"Next ▶ {index + 1}/{len(scenario)}"
            if st.button(label, type="primary", disabled=busy):
                s.play_go = True
                st.rerun()
            if st.button("Stop", disabled=busy):
                s.play_index = None
                st.rerun()
    if s.play_index is None:
        st.markdown(f'<div class="next-step">{len(scenario)} messages, one per click. '
                    f'{_describe(scenario[0], "First")}</div>', unsafe_allow_html=True)
    elif not s.play_go:
        st.markdown(f'<div class="next-step">{_describe(scenario[index], "Next")}</div>', unsafe_allow_html=True)


def _describe(step: dict, prefix: str) -> str:
    who = step.get("customer") or _state().customer
    changes = [f"{k} → {v}" for k, v in step.items() if k not in ("say", "new_ticket", "wait", "customer")]
    if step.get("new_ticket"):
        changes.append("new ticket")
    extra = f" ({', '.join(changes)})" if changes else ""
    return f"{prefix}: <b>{html.escape(who)}</b>{html.escape(extra)}: “{html.escape(step.get('say', ''))}”"


def apply_scenario_step(scenario: list[dict] | None):
    """Call BEFORE sidebar(): applies customer/bot/ticket changes of the scenario step about to run."""
    s = _state()
    if not scenario or s.play_index is None or not s.play_go:
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
