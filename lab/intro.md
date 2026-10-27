Welcome! In this lab you give an AI support bot a memory with **mem0**, stored in **ScyllaDB**.

You start with a bot that forgets everything between tickets. In each exercise you run one command and add one mem0 feature. You also see the CQL that mem0 sends to ScyllaDB, and what ScyllaDB does with it.

**Tabs**

- **Terminal**: run the commands. Use **Terminal 2** when one command keeps running.
- **App**: the bot (Streamlit). Reload this tab after each `./run.sh`.

**Each exercise**

1. `cd` into the exercise folder and run `./run.sh`.
2. Open the **App** tab and click **▶ Play scenario**, then **Next ▶** for each message. Or chat yourself.
3. Read **Under the hood** on the right: each step of a turn, with its CQL and latency.

You need a Gemini API key. Get one for free at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Playing every scenario once uses about 45 Gemini calls (about 170k tokens). Each message you type adds 2 calls.
