#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import difflib
import hashlib
here = Path(__file__).resolve().parent
source = here.parents[5] / 'kernel/rust/process_helpers.rs'
raw = source.read_bytes()
assert hashlib.sha256(raw).hexdigest() == 'be562522271404c8e5f7cf07f7a7fff9caed6e7be125d4098c7cfb35d1134da1'
original = raw.decode()
start = original.index('pub unsafe extern "C" fn find_thread(pid: CInt, tid: CInt) -> *mut Thread {')
end = original.index('\n}\n', start) + 2
body = original[start:end]
assert body.count('    process_find_thread_body_result(') == 1
assert body.count('        Some(process_hold_thread_bridge),\n') == 1
body = body.replace('    process_find_thread_body_result(', '    process_find_thread_live_body_result(')
body = body.replace('        Some(process_hold_thread_bridge),\n', '')
new = original[:start] + body + original[end:] + '\n' + (here/'find_thread_live.rs.inc').read_text()
patch = ''.join(difflib.unified_diff(original.splitlines(keepends=True), new.splitlines(keepends=True), fromfile='a/kernel/rust/process_helpers.rs', tofile='b/kernel/rust/process_helpers.rs'))
(here/'LOOKUP-LIVE.PRIVATE-NOT-APPLIED.patch').write_text(patch)
print('source', hashlib.sha256(raw).hexdigest())
print('patch', hashlib.sha256(patch.encode()).hexdigest())
