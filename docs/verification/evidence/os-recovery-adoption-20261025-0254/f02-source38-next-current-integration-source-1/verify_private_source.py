"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Check this fixed thirteen-record storage successor without a compiler.
"""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent


def check_ref(row):
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']


def main():
    manifest = json.loads((P / 'SOURCE-IMPLEMENTATION-AND-ACTUAL13-ABI.json').read_text())
    for row in manifest['preimages'] + manifest['postimages']:
        check_ref(row)
    before = (P / 'preimages/kernel/process.c').read_text()
    after = (P / 'candidate/kernel/process.c').read_text()
    marker = '/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n * Preserve the original tracked callsite numbers; do not use Rust line!/file!.\n'
    start = after.index(marker)
    stop = after.index('#line 100\n', start)
    assert before[:before.index('#line 100\n')] == after[:start]
    macro = after[start:stop]
    assert '#define PROCESS_TRACKED_LINE_STORAGE(name, value) extern const int name\n' in macro
    assert '#define PROCESS_TRACKED_LINE_STORAGE(name, value) const int name = value\n' in macro
    restored = after[:start] + after[stop:]
    for row in manifest['data_records']:
        replacement = 'PROCESS_TRACKED_LINE_STORAGE(%s, %d);' % (row['name'], row['value'])
        assert restored.count(replacement) == 1
        restored = restored.replace(replacement, row['declaration'])
    assert restored == before, 'Any unrelated source, logical #line or diagnostic change is forbidden'
    rust_before = (P / 'preimages/kernel/rust/process_helpers.rs').read_text()
    rust_after = (P / 'candidate/kernel/rust/process_helpers.rs').read_text()
    fragment = (P / 'process_tracked_lines.FRAGMENT.rs').read_text()
    assert rust_after == rust_before.rstrip() + '\n\n' + fragment
    assert 'line!' not in fragment and 'file!' not in fragment
    for row in manifest['data_records']:
        assert 'pub static %s: CInt = %d;' % (row['name'], row['value']) in fragment
        assert row['actual_current_object']['size'] == 4
        assert row['actual_current_object']['signed_value'] == row['value']
    check_ref(manifest['current_process_object'])
    recipe = json.loads((P / 'EXACT-NEXT-THREE-COMPILER-COMMANDS.NOT-ADMITTED.json').read_text())
    base = json.loads(Path(recipe['source_profile']['path']).read_text())
    assert recipe['commands'] == base['exact_commands']
    assert recipe['commands'][1]['argv'][-1] == '/src/kernel/process.c'
    print(json.dumps(dict(status='PASS_SOURCE_ONLY_EXACT13_AND_UNCHANGED_OTHER_SOURCE',
                          records=13, new_compilers=0, actual_retirements=0)))


if __name__ == '__main__':
    main()
