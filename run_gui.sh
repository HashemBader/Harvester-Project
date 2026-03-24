#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export SSL_CERT_FILE="${SSL_CERT_FILE:-$(python3 -c 'import certifi; print(certifi.where())' 2>/dev/null || true)}"
if [[ -n "${SSL_CERT_FILE}" ]]; then
  export REQUESTS_CA_BUNDLE="$SSL_CERT_FILE"
fi

exec python3 src/gui_launcher.py
