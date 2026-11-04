# 00 · Run the support bot (no memory)

Meet **plushie-bot**, the support bot of the ScyllaDB Plushie Shop. It runs on an LLM (Claude on Amazon Bedrock) and answers questions about orders, shipping and returns.

It has no memory. Each reply sees only the messages of the current ticket. When the customer opens a new ticket, the bot starts from zero. That is the problem this workshop solves.

## Exercise

1. **Terminal**: start the bot. It checks that the LLM answers first. If Bedrock does not answer, it asks for a Gemini API key ([get one here](https://aistudio.google.com/apikey)).

   ```run,sh
   cd ~/mem0-lab/lab/exercise/00-run-the-bot && ./run.sh
   ```

2. **App**: click **▶ Play scenario**, then **Next ▶** for each message. The line above the chat shows who sends what next. Nora reports a late order, then opens a new ticket and asks for news.
3. **App**: read the reply in the new ticket. The bot asks for the order number again.
4. Optional: write your own messages. Click **New ticket** in the sidebar to start a fresh conversation.

## What happened

- Every turn sends one prompt to the LLM: the system prompt plus the messages of this ticket.
- The **Under the hood** panel shows one step per turn: `LLM: reply`. No database is involved yet.
- The sidebar counts LLM calls and tokens.

**Takeaway:** chat history is not memory. The next exercises give the bot a memory that outlives the ticket.
