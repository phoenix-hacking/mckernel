#!/bin/bash
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Parent must relay a new ordinary CPU profile slot before invoking this file.
set -euo pipefail
if [[ "${1:-}" != "--ordinary-slot-granted" ]]; then
  echo 'No compiler/test authorization: pass --ordinary-slot-granted only after the parent relays a live ordinary slot.' >&2
  exit 2
fi
cd -- "$(dirname -- "$0")"
mkdir fixture-attempt-1
python3 - <<'PY'
import json,hashlib
from pathlib import Path
for name,digest in json.loads(Path('prepared-assets.json').read_text()).items():
 assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==digest,name
for name,x in json.loads(Path('source-bindings.json').read_text()).items():
 if 'snapshot' in x:
  assert hashlib.sha256(Path(x['snapshot']).read_bytes()).hexdigest()==x['sha256'],name
PY
cc -std=gnu11 -O2 -Wall -Wextra -Werror -c original_reference.c -o fixture-attempt-1/original_reference.o >fixture-attempt-1/cc.log 2>&1
rustc --edition=2021 -C opt-level=2 -C panic=abort fixture.rs -C link-arg=fixture-attempt-1/original_reference.o -o fixture-attempt-1/signalfd-fixture >fixture-attempt-1/rustc.log 2>&1
./fixture-attempt-1/signalfd-fixture >fixture-attempt-1/result.log 2>&1
cat fixture-attempt-1/result.log
