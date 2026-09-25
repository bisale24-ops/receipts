#!/usr/bin/env bash
# Audit every repository in a directory and fail if any of them produces stderr,
# an unexpected exit code, or a traceback. A check with an exit code, not an eyeball.
#   ./demo/crash-hunt.sh /path/containing/clones
set -uo pipefail
cd "$(dirname "$0")/.."
WORK="${1:?usage: crash-hunt.sh DIRECTORY_OF_CLONES}"
bad=0
count=0
for repo in "$WORK"/*/; do
  [ -d "$repo" ] || continue
  count=$((count + 1))
  for form in "--quiet" "--json" ""; do
    err=$(PYTHONPATH=src python3 -m receipts.cli --repo "$repo" $form 2>&1 >/dev/null)
    code=$?
    if [ -n "$err" ]; then
      printf 'STDERR  %-22s %s\n' "$(basename "$repo")" "$(printf '%s' "$err" | head -1)"
      bad=1
    fi
    if [ "$code" -gt 1 ]; then
      printf 'EXIT %-3s %-22s\n' "$code" "$(basename "$repo")"
      bad=1
    fi
  done
done
if [ "$bad" -eq 0 ]; then
  echo "clean: $count repositories × 3 output forms, no stderr, no exit above 1"
fi
exit $bad
