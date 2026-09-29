#!/usr/bin/env bash
# Literal-only source finalization; independent fetched release remains required.
set -Eeuo pipefail
SOURCE_TEMPLATE_ONLY=true
if "$SOURCE_TEMPLATE_ONLY"; then
  echo DRAFT_NOT_RELEASED >&2
  exit 1
fi
exec /usr/bin/sudo -A /usr/bin/python3 -E -s -B /home/holden/mckernel/docs/verification/evidence/native-exact-candidate-quarantine-recover-704f6654-1.py \
  --release /home/holden/mckernel/docs/verification/stability-native-exact-candidate-quarantine-recovery-execution-release-704f6654-1.json
