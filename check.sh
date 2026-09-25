#!/usr/bin/env bash
# Everything CI runs, on every interpreter CI runs it on, plus the tool against itself.
set -uo pipefail
cd "$(dirname "$0")"
status=0
for python in "$@"; do
  printf '\n=== %s ===\n' "$("$python" -V 2>&1)"
  PYTHONPATH=src "$python" -m pytest tests -q || status=1
  PYTHONPATH=src "$python" -m receipts.cli --repo . --quiet || status=1
  err=$(PYTHONPATH=src "$python" -m receipts.cli --repo . 2>&1 >/dev/null)
  if [ -n "$err" ]; then echo "wrote to stderr: $err"; status=1; fi
done
exit $status
