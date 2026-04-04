#!/usr/bin/env bash
set -euo pipefail

NOVAACT_PYTHON="${NOVAACT_PYTHON:-python3}"
if ! "$NOVAACT_PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
  echo "Nova Act SDK requires Python 3.10+. Got: $($NOVAACT_PYTHON --version 2>&1) ($NOVAACT_PYTHON)" >&2
  echo "Install e.g. sudo apt install python3.12 && NOVAACT_PYTHON=python3.12 $0" >&2
  exit 1
fi

if [[ -n "${NOVAACT_RELEASE_TAG:-}" ]]; then
  tag="${NOVAACT_RELEASE_TAG}"
else
  auth_header=()
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    auth_header=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  fi

  release_json="$(curl -fsSL "${auth_header[@]}" \
    https://api.github.com/repos/aws/nova-act/releases/latest)"
  tag="$(python3 - <<'PY'
import json
import sys

payload = sys.stdin.read()
if not payload.strip():
  sys.exit("NovaAct release metadata was empty. Set NOVAACT_RELEASE_TAG to install a known version.")

try:
  data = json.loads(payload)
except json.JSONDecodeError as exc:
  sys.exit(f"Failed to parse NovaAct release metadata: {exc}")

tag = data.get("tag_name")
if not tag:
  sys.exit("NovaAct release metadata missing tag_name. Set NOVAACT_RELEASE_TAG to install a known version.")

print(tag)
PY
<<<"$release_json")"
fi

echo "Installing NovaAct SDK from release ${tag} (using ${NOVAACT_PYTHON})..."
"$NOVAACT_PYTHON" -m pip install "https://github.com/aws/nova-act/archive/refs/tags/${tag}.tar.gz"
