#!/usr/bin/env bash
# Reproduce the table in README.md: clone each project and audit its claims.
#   ./demo/scan.sh [directory-to-clone-into]
set -uo pipefail
cd "$(dirname "$0")/.."
WORK="${1:-/tmp/receipts-scan}"
mkdir -p "$WORK"
REPOS="urllib3/urllib3 python-openxml/python-docx jsvine/pdfplumber Textualize/rich encode/httpx
pallets/click psf/black python-poetry/poetry mkdocs/mkdocs tiangolo/sqlmodel Delgan/loguru
pallets/jinja pallets/werkzeug pypa/packaging tqdm/tqdm python-attrs/attrs"
for repo in $REPOS; do
  name="${repo##*/}"
  [ -d "$WORK/$name" ] || git clone -q --depth 1 "https://github.com/$repo.git" "$WORK/$name"
  printf '%-16s ' "$name"
  PYTHONPATH=src python3 -m receipts.cli --repo "$WORK/$name" --quiet 2>/dev/null
done
