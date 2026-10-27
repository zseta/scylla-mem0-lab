"""Shared helpers for the mem0 + ScyllaDB workshop.

Each exercise's app.py holds the lesson code (the mem0 calls).
Everything that is plumbing lives here: config, CQL capture, Gemini wrapper, UI chrome.
"""

import os

# mem0 sends anonymous usage telemetry by default. Not needed in a lab.
os.environ.setdefault("MEM0_TELEMETRY", "False")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
