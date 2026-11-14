#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib
import subprocess
import tempfile
here = Path(__file__).resolve().parent
source = here.parents[5] / 'kernel/rust/process_helpers.rs'
text = source.read_text()
def extract(name):
    sig = 'pub unsafe extern "C" fn ' + name + '('
    assert text.count(sig) == 1
    start = text.index(sig); brace = text.index('{', start); depth = 0
    for end in range(brace, len(text)):
        if text[end] == '{': depth += 1
        if text[end] == '}':
            depth -= 1
            if depth == 0: return text[start:end + 1]
    raise ValueError('unclosed function')
release = extract('process_release_thread_body_result')
checked = extract('process_release_thread_checked_body_result')
candidate = (here / 'find_thread_live.rs.inc').read_text()
print('release body', hashlib.sha256(release.encode()).hexdigest(), flush=True)
print('checked body', hashlib.sha256(checked.encode()).hexdigest(), flush=True)
print('candidate', hashlib.sha256(candidate.encode()).hexdigest(), flush=True)
template = (here / 'fixture.template.rs').read_text()
assert template.count('// INSERT_ACTUAL_FUNCTIONS') == 1
with tempfile.TemporaryDirectory(prefix='m14-live-lookup-') as temp:
    path = Path(temp)
    (path / 'fixture.rs').write_text(template.replace('// INSERT_ACTUAL_FUNCTIONS', release + '\n\n' + checked + '\n\n' + candidate))
    subprocess.run(['rustc', '+1.85.1', '--edition=2021', '-D', 'warnings', str(path / 'fixture.rs'), '-o', str(path / 'fixture')], check=True)
    subprocess.run([str(path / 'fixture')], check=True)
