#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then echo 'First run: bash install.sh'; exit 1; fi
exec .venv/bin/python app.py
