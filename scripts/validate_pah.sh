#!/bin/bash
set -euo pipefail

HUB_URL="https://automation-hub.example.com/api/galaxy"
TOKEN="${ANSIBLE_GALAXY_SERVER_CORP_PAH_TOKEN:?missing token}"

HTTP_CODE="$(
  curl -sS -o /tmp/pah_probe.json -w '%{http_code}' \
    -H "Authorization: token ${TOKEN}" \
    "${HUB_URL}/v3/collections/?limit=1"
)"

if [ "$HTTP_CODE" = "200" ]; then
  echo "PAH token works collections endpoint reachable and we were able to successfully auth."
else
  echo "PAH auth failed (HTTP $HTTP_CODE). Body:"
  sed -n '1,120p' /tmp/pah_probe.json
  exit 1
fi