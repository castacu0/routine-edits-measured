#!/usr/bin/env bash
# Render a self-contained HTML document to PDF with headless Chrome.
#
#   ./scripts/html2pdf.sh path/to/doc.html path/to/doc.pdf
#
# Same headless-Chrome path as paper/build_handoff.py, so no extra toolchain.
set -euo pipefail
SRC="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUT="$2"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
if [ ! -x "$CHROME" ]; then
  CHROME="$(command -v google-chrome || command -v chromium || true)"
fi
[ -n "$CHROME" ] || { echo "✖ Chrome/Chromium not found"; exit 1; }
"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw --virtual-time-budget=8000 \
  --print-to-pdf="$OUT" "file://$SRC" 2>/dev/null
echo "✔ $OUT"
