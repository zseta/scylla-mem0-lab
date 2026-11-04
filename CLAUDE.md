# CLAUDE.md

mem0 + ScyllaDB workshop: a Streamlit support bot that gains memory one exercise at a time. Overview in [lab/README.md](lab/README.md).

## Rules

- Each `lab/exercise/NN-*/app.py` is a full copy of the bot at that stage, not a diff. A change to shared bot behavior goes into every later exercise's `app.py`. Shared code lives in `lab/common/`.
- `instruqt/01-workshop/assignment.md` is generated. Edit `lab/intro.md` or `exercise/*/lab.md`, then run `lab/build-instruqt.sh`.
- Keep the ids in `instruqt/01-workshop/frontmatter.yml`; Instruqt assigned them.
- `lab.md` instructions: terse. One action per step, no filler.
- Terminal commands go in ```` ```run,sh ```` blocks.
- A step on another tab links to it: write the exact tab title in bold (**Terminal**, **Terminal 2**, **App**). The build makes it `[**App**](tab-2)` ([Instruqt tab links](https://docs.instruqt.com/tracks/challenges/using-markdown-editor), zero-based, `frontmatter.yml` order). Don't hard-code `tab-N`.
- Exercise numbers, file names and versions are listed in `lab/README.md`. Update it when they change.

## Run

```bash
cd lab && uv sync
exercise/01-start-scylladb/run.sh && exercise/02-connect-mem0/run.sh
exercise/NN-*/run.sh      # app on :8501, log in lab/.data/app.log
./reset.sh                # drop memories (--all: also the cluster)
```

Locally the bot uses Gemini: needs `GOOGLE_API_KEY` in `lab/.env` or the repo-root `.env` (exercise 00 asks for it). On Instruqt it uses Claude on Amazon Bedrock (`LLM_PROVIDER=bedrock` in `lab/.env`, written by the track setup), with Gemini as the fallback. `PYTHONPATH=lab uv run --project lab python -m common.check_llm` checks the LLM. No test suite; check changes by running the exercise.
