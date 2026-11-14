#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Create a private host-test input from actual source bodies. Execution requires a
reviewed unprivileged profile and coordinator resource share; this is not a runner.
"""
from pathlib import Path
import hashlib
import re

ROOT = Path('/home/holden/mckernel')
HERE = Path(__file__).resolve().parent
SOURCE = ROOT / 'kernel/rust/process_helpers.rs'
NAMES = [
    'process_clone_thread_shared_vm_state_body_result',
    'process_ref_release_should_destroy_result', 'process_ref_dec_and_test_result',
    'process_ref_atomic_at', 'process_ref_inc_direct_result',
    'process_ref_dec_and_test_direct_result', 'process_ref_inc_result',
    'process_chain_process_body_result', 'process_chain_thread_body_result',
    'field_ptr', 'process_thread_action_result', 'process_thread_profile_result',
    'process_vm_action_result', 'process_release_thread_body_result',
]

def extract(text, name):
    pattern = r'(?m)^(?:pub )?(?:unsafe )?(?:extern "C" )?fn ' + re.escape(name) + r'\s*\('
    matches = list(re.finditer(pattern, text))
    if len(matches) != 1:
        raise ValueError(f'{name}: expected one definition, found {len(matches)}')
    start = matches[0].start()
    body = text.index('{', matches[0].end())
    depth = 1
    for i in range(body + 1, len(text)):
        if text[i] == '{': depth += 1
        if text[i] == '}': depth -= 1
        if depth == 0: return text[start:i + 1]
    raise ValueError(f'{name}: unbalanced source')

raw = SOURCE.read_bytes()
text = raw.decode('utf-8')
bodies = '\n\n'.join(extract(text, name) for name in NAMES)
template = (HERE / 'fixture.template.rs').read_text()
if template.count('// ACTUAL_SOURCE_BODIES') != 1: raise ValueError('template marker')
output = HERE / 'generated.actual.rs'
if output.exists(): raise FileExistsError(output)
output.write_text(template.replace('// ACTUAL_SOURCE_BODIES', bodies))
(HERE / 'source.sha256').write_text(hashlib.sha256(raw).hexdigest() + '  ' + str(SOURCE) + '\n')
