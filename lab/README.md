# Workshop lab: agent memory with mem0 and ScyllaDB

A support bot for the ScyllaDB Plushie Shop. It starts with no memory, and each exercise adds one mem0 feature on a 3-node ScyllaDB cluster. Every chat turn shows the CQL mem0 ran and how long each step took.

## Layout

```
lab/
  setup.sh             pre-start: Docker, uv, Python 3.14, deps, embedding model, images
  reset.sh             drop all memories (--all: also remove the cluster)
  cqlsh.sh             cqlsh on scylla-1, in the lab keyspace
  build-instruqt.sh    intro.md + exercise/*/lab.md -> ../instruqt/01-workshop/assignment.md
  intro.md             assignment intro
  pyproject.toml       dependencies (mem0 pinned to the ScyllaDB provider PR commit)
  common/              shared code: config, CQL capture, Gemini wrapper, Streamlit UI, assets
  exercise/
    00-run-the-bot/        app.py           bot with no memory
    01-start-scylladb/     docker-compose   3 nodes, 3 racks + Vector Store
    02-connect-mem0/       connect.py       keyspace RF=3, mem0 creates its schema
    03-add-memories/       app.py           add()
    04-search-memories/    app.py           search()
    05-scoping/            app.py           user_id / agent_id / run_id, wrong-scope leak
    06-memory-lifecycle/   app.py           rep dashboard: get_all, update, delete, history, delete_all
    07-metadata/           app.py           metadata + filters
    08-custom-instructions/ app.py          what gets remembered
    09-performance/        app.py, load.sh  add() in the background; seed + benchmark (no LLM)
    10-high-availability/  app.py, ha_check.sh  QUORUM, stop a node
```

Each exercise folder has `run.sh` (the one command) and `lab.md` (lesson + steps). Each `app.py` is a full copy of the bot at that stage, so `diff exercise/03-*/app.py exercise/04-*/app.py` shows exactly what changed.

## Stack

| Part | Version |
|---|---|
| ScyllaDB | `scylladb/scylla:2026.3.4`, 3 nodes, `--smp 1 --memory 1G`, one rack each |
| Vector Store | `scylladb/vector-store:1.14.0` |
| mem0 | `zseta/mem0@5ffebb1` (PR mem0ai/mem0#5373, ScyllaDB provider) |
| LLM | Gemini `gemini-3.5-flash-lite` (override with `GEMINI_MODEL`) |
| Embeddings | `BAAI/bge-small-en-v1.5`, 384 dims, CPU |
| UI | Streamlit on port 8501, ScyllaDB Design System colors |
| Python | 3.14 via uv, CPU-only torch |

## Run locally

Needs Docker and [uv](https://docs.astral.sh/uv/). On Linux, run several ScyllaDB nodes only after `sudo sysctl -w fs.aio-max-nr=1048576` if a node fails with an AIO error. The compose file already lowers each node's AIO needs.

```bash
cd lab
uv sync
exercise/00-run-the-bot/run.sh        # asks for the Gemini key once, saves lab/.env
exercise/01-start-scylladb/run.sh
exercise/02-connect-mem0/run.sh
exercise/03-add-memories/run.sh       # then open http://localhost:8501
```

Logs: `lab/.data/app.log`. Start over: `./reset.sh`, then exercise 02 again.

## Instruqt

`../instruqt/` holds the track: one VM (`scylladb`), one challenge with every exercise, tabs **Terminal**, **Terminal 2** and **App** (port 8501), no check scripts.

- `track_scripts/setup-scylladb` clones the repo to `/root/mem0-lab` and runs `lab/setup.sh`. Repo: https://github.com/zseta/scylla-mem0-lab.
- After editing any `lab.md`, run `./build-instruqt.sh`, then `instruqt track push`.

## Gemini usage

Each chat turn is 2 Gemini calls: the reply and mem0's fact extraction (about 8k input tokens). Playing every scenario once is about 45 calls and 170k tokens (measured). Exercises 09 and 10 load and check data with `add(infer=False)`, which uses no LLM. Rate-limit errors (429) are retried automatically, and the sidebar counts calls and tokens.
