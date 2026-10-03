#!/usr/bin/env bash
set -euo pipefail

if ! command -v brew >/dev/null 2>&1; then
  echo "Install Homebrew first: https://brew.sh" >&2
  exit 1
fi

brew install libraqm pkgconf jpeg-turbo
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
export PKG_CONFIG_PATH="$(brew --prefix)/lib/pkgconfig:$(brew --prefix libraqm)/lib/pkgconfig:$(brew --prefix jpeg-turbo)/lib/pkgconfig${PKG_CONFIG_PATH:+:$PKG_CONFIG_PATH}"
python -m pip install --no-binary=Pillow -r requirements.txt
python - <<'PY'
from PIL import features
if not features.check("raqm"):
    raise SystemExit("Pillow was built without RAQM; Indic text shaping will not work.")
print("Setup complete: Pillow has HarfBuzz/RAQM shaping enabled.")
PY
