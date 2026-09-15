#!/usr/bin/env bash
# Benchmark a local Ollama model against the two roles Nostromo binds to local inference
# (Bootstrap Plan §11.9). Run ON the Spark. Writes a markdown report to stdout.
#
# The point is not to compare models. It is to establish that this baseline is operationally
# acceptable for Mother's routing and Brett's collection, and — the part that matters — that it
# declines to conclude when the evidence does not support a conclusion. Every task therefore has
# a paired control whose correct answer is "escalate", because a model that can only answer has
# not been shown to know when not to.
#
# Usage: bench-local-model.sh [model-tag] [ollama-host]
set -euo pipefail
MODEL="${1:-qwen3.6:35b-a3b}"
HOST="${2:-http://localhost:11434}"
exec python3 "$(dirname "${BASH_SOURCE[0]}")/bench_local_model.py" "$MODEL" "$HOST"
