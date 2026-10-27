"""Exercise 00: the support bot WITHOUT memory.

Each reply sees only the messages of the current ticket.
Open a new ticket and the bot has forgotten everything.
"""

from common import gemini, shop, ui

SCENARIO = [
    {"customer": "alice", "new_ticket": True,
     "say": "Hi, I'm Alice. My order #4821, a large Scylla plushie, still hasn't arrived. I live in Berlin."},
    {"say": "Please send updates by email, not phone. Thanks!"},
    {"new_ticket": True, "say": "Hi again! Any news about my order?"},
]


def respond(text, ctx, history, turn):
    with turn.step("Gemini: reply") as s:
        s.detail = f"Prompt = system prompt + {len(history)} messages of this ticket. No memory."
        return gemini.chat_reply(shop.system_prompt(), history, text)


ui.page("00", "A support bot with no memory")
ui.apply_scenario_step(SCENARIO)
ctx = ui.sidebar()
ui.chat(ctx, respond, SCENARIO)
