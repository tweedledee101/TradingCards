#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${NOVAACT_RELEASE_TAG:-}" ]]; then
  tag="${NOVAACT_RELEASE_TAG}"
else
  auth_header=()
  if [[ -n "${GITHUB_TOKEN:-}" ]]; then
    auth_header=(-H "Authorization: Bearer ${GITHUB_TOKEN}")
  fi

  release_json="$(curl -fsSL "${auth_header[@]}" \
    https://api.github.com/repos/aws/nova-act/releases/latest)"
  tag="$(python - <<'PY'
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

echo "Installing NovaAct SDK from release ${tag}..."
pip install "https://github.com/aws/nova-act/archive/refs/tags/${tag}.tar.gz"
