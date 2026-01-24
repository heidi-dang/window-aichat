#!/usr/bin/env bash
set -euo pipefail

base="${1:-}"
if [[ -z "${base}" ]]; then
  echo "usage: healthcheck.sh <base_url>" >&2
  exit 2
fi

curl -fsS "${base}/" >/dev/null
curl -fsS "${base}/api/models" >/dev/null
