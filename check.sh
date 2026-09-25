#!/usr/bin/env bash
# Everything CI runs, on every interpreter CI runs it on, plus the tool against itself.
set -uo pipefail
cd "$(dirname "$0")"
status=0
for python in "$@"; do
  printf '\n=== %s ===\n' "$("$python" -V 2>&1)"
  PYTHONPATH=src "$python" -m pytest tests -q || status=1
  PYTHONPATH=src "$python" -m receipts.cli --repo . --quiet || status=1
done
exit $status
