# mem0 + ScyllaDB lab

Hands-on workshop: give an AI support bot memory with [mem0](https://github.com/mem0ai/mem0), stored in a 3-node ScyllaDB cluster. Eleven exercises, each adding one mem0 feature and showing the CQL behind it.

## Quick start

Needs Docker, [uv](https://docs.astral.sh/uv/), and a free [Gemini API key](https://aistudio.google.com/apikey).

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
- `instruqt/`: Instruqt track. Rebuild with `lab/build-instruqt.sh`, then `instruqt track push`.
