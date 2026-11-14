#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare a private, line-preserving comment correction for the PRIVATE-2 overlay.
No compiler or test execution.
"""
from pathlib import Path
import difflib, hashlib, re
here = Path(__file__).resolve().parent
source = here.parent / 'M14-ARCH5-CUTOVER-1/postimage/kernel/rust/syscall_policy.rs'
atomic_patch = here.parent / 'M14-ARCH5-SIGNAL-ATOMIC-PRIVATE-2/SIGNAL-ATOMIC.PRIVATE.patch'
original = source.read_text()
old = ('/// payload is read after transfer/free. Counter races and overwritten old core\n'
       '/// slots remain independent existing debt, not silently fixed here.\n')
new = ('/// payload is read after transfer/free. Diagnostic budget claims are atomic;\n'
       '/// overwritten old core slots remain independent existing debt.\n')
assert original.count(old) == 1
assert old.count('\n') == new.count('\n')
# PRIVATE-2 does not touch this comment; this separate patch applies after it.
assert old not in atomic_patch.read_text()
changed = original.replace(old, new, 1)
def macros(text):
    return [(n, m.start(), line) for n, line in enumerate(text.splitlines(), 1)
            for m in re.finditer(r'\b(?:line|file|column)!\s*\(', line)]
assert macros(original) == macros(changed)
diff = ''.join(difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                                   fromfile='a/kernel/rust/syscall_policy.rs',
                                   tofile='b/kernel/rust/syscall_policy.rs'))
(here/'SIGNAL-COMMENT.PRIVATE.patch').write_text(diff)
for p in (source, atomic_patch, here/'SIGNAL-COMMENT.PRIVATE.patch', here/'make_comment_patch.py'):
    print(hashlib.sha256(p.read_bytes()).hexdigest(), p)
print('PASS source-only: two comment lines changed; all location macro coordinates retained; PRIVATE-2 does not change comment')
