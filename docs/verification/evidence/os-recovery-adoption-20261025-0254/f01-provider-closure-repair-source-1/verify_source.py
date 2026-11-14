"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only verification of this fixed, one-use F01 source binding; no compiler.
"""
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent


def verify(row):
    data = Path(row['path']).read_bytes()
    assert len(data) == row['bytes'], row['path']
    assert hashlib.sha256(data).hexdigest() == row['sha256'], row['path']
    return data


def main():
    binding = json.loads((P / 'PROVIDER-SOURCE-BINDING.json').read_text())
    original = verify(binding['selected_memory_source']).splitlines(keepends=True)
    prepared = verify(binding['prepared_memory_source']).splitlines(keepends=True)
    assert len(original) == len(prepared)
    kept = set()
    for row in binding['fixed_exact_memory_spans']:
        a, b = row['first'] - 1, row['last']
        data = b''.join(original[a:b])
        assert hashlib.sha256(data).hexdigest() == row['sha256'], row['name']
        assert original[a:b] == prepared[a:b], row['name']
        kept.update(range(a, b))
    assert all(line == b'\n' for i, line in enumerate(prepared) if i not in kept)
    for key in ('unchanged_fixture', 'existing_lower_boundary_mocks', 'lib'):
        verify(binding[key])
    for row in binding['supporting_modules']:
        source, target = verify(row['source']), verify(row['prepared'])
        if row.get('exact_full_module'):
            assert source == target
        else:
            original_lines = source.splitlines(keepends=True)
            target_lines = target.splitlines(keepends=True)
            for span in row['spans']:
                a, b = span['first'] - 1, span['last']
                assert original_lines[a:b] == target_lines[a:b]
    recipe = json.loads((P / 'EXACT-ROOT-PROPOSED-RECIPE.NOT-ADMITTED.json').read_text())
    for row in recipe['inputs'] + recipe['tools']:
        verify(row)
    print(json.dumps({'status': 'PASS_STATIC_EXACT_SOURCE_BINDING_ONLY',
                      'memory_extern_roots': len(binding['root_memory_externs']),
                      'memory_functions': binding['memory_functions'],
                      'compiler_executions': 0, 'fixture_executions': 0}))


if __name__ == '__main__':
    main()
