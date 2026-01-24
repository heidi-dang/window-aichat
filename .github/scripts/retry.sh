#!/usr/bin/env bash
set -euo pipefail

max="${1:-}"
delay="${2:-}"
if [[ -z "${max}" || -z "${delay}" ]]; then
  echo "usage: retry.sh <max_attempts> <base_delay_seconds> -- <command...>" >&2
  exit 2
fi

shift 2
if [[ "${1:-}" == "--" ]]; then
  shift
fi

if [[ $# -lt 1 ]]; then
  echo "usage: retry.sh <max_attempts> <base_delay_seconds> -- <command...>" >&2
  exit 2
fi

attempt=1
while true; do
  if "$@"; then
    exit 0
  fi
  if (( attempt >= max )); then
    exit 1
  fi
  sleep_seconds=$(( delay * attempt ))
  sleep "${sleep_seconds}"
  attempt=$(( attempt + 1 ))
done
