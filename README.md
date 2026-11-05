# mem0 + ScyllaDB lab

Hands-on workshop: give an AI support bot memory with [mem0](https://github.com/mem0ai/mem0), stored in a 3-node ScyllaDB cluster. Eleven exercises, each adding one mem0 feature and showing the CQL behind it.

## Guided workshop

The lab is designed for the guided workshop on Instruqt: [bit.ly/scylla-mem0](https://bit.ly/scylla-mem0). It runs in your browser. The sandbox has the ScyllaDB cluster and Claude on Amazon Bedrock, so you do not need an API key.

## Run locally

To run the lab on your laptop, you need Docker, [uv](https://docs.astral.sh/uv/), and a free [Gemini API key](https://aistudio.google.com/apikey). Locally, the bot uses Gemini as its LLM.

```bash
cd lab
uv sync
exercise/00-run-the-bot/run.sh     # asks for the Gemini key once
exercise/01-start-scylladb/run.sh
exercise/02-connect-mem0/run.sh
exercise/03-add-memories/run.sh    # open http://localhost:8501
```

## Layout

- `lab/`: exercises, shared code, setup scripts. Details in [lab/README.md](lab/README.md).
- `instruqt/`: Instruqt track. Rebuild with `lab/build-instruqt.sh`. `git push` to `main` also pushes it to Instruqt (`.githooks/pre-push`; enable once with `git config core.hooksPath .githooks`).
