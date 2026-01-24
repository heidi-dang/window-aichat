#!/usr/bin/env bash
set -euo pipefail

image="${1:-}"
digest="${2:-}"
if [[ -z "${image}" || -z "${digest}" ]]; then
  echo "usage: verify-ghcr.sh <image_ref> <digest>" >&2
  exit 2
fi

docker buildx imagetools inspect "${image}@${digest}" >/dev/null
