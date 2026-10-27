#!/usr/bin/env bash
# Exercise 05: start this exercise's version of the bot.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
"$HERE/../../common/run_app.sh" "$HERE"
