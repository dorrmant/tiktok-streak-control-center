#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
PYTHON="$(command -v python3)"
if ! "$PYTHON" -c 'import venv' >/dev/null 2>&1; then
  echo 'Install python3-venv first: sudo apt install python3-venv'
  exit 1
fi
if [[ ! -x .venv/bin/python ]]; then "$PYTHON" -m venv .venv; fi
.venv/bin/python -m pip install -r requirements.txt
chmod +x run.sh install.sh
.venv/bin/python - <<'PY'
from backend import Backend
b = Backend()
print('Bot found:', b.config.get('bot_source') or 'NOT FOUND')
print('Config created: config.json (contains your dashboard password; never commit it)')
PY
[[ -f config.json ]] && chmod 600 config.json
echo 'Install complete. You need Google Chrome or Chromium installed. Run ./run.sh'
