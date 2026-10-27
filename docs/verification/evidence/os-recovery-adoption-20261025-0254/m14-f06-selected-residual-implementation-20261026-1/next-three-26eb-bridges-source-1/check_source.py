"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused identity, paired-selector and fallback checks for three selected leaves.
No compiler, provider execution, broad inventory or acceptance claim.
"""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
results = []
for label in ['copy-to-user', 'copy-from-user', 'forward-context']:
    d = D / label
    b = json.loads((d / 'SOURCE-BINDINGS.json').read_text())
    plan = json.loads((d / 'FUTURE-HOST-COMMAND-PLAN.json').read_text())
    for row in plan['inputs'] + plan['tools'] + b['canonical_before'] + [
            b['selected_cursor'], b['selected_object'], b['reused_fragment'],
            b['provider_source'], plan['genuine_configuration']]:
        raw = Path(row['path']).read_bytes()
        assert len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], row['path']
    cursor = json.loads(Path(b['selected_cursor']['path']).read_text())
    assert cursor['rows']['F06']['count'] == 31
    assert b['symbol'] in cursor['rows']['F06']['defined_FUNC_names']
    c = (d / 'syscall.c').read_text()
    policy = (d / 'syscall_policy.rs').read_text()
    assert c.count(b['C_wrapper']) == 1
    assert c.replace(b['C_wrapper'], b['original_C'], 1) == (d / 'BASE.syscall.c').read_text()
    assert policy.removesuffix(b['rust_selection']) == (d / 'BASE.syscall_policy.rs').read_text()
    assert (d / 'BASE.syscall.c').read_text() == Path(b['canonical_before'][0]['path']).read_text()
    assert (d / 'BASE.syscall_policy.rs').read_text() == Path(b['canonical_before'][1]['path']).read_text()
    leaf = (d / 'bridge.rs').read_text()
    excerpt = leaf[leaf.index('/// # Safety'):]
    assert hashlib.sha256(excerpt.encode()).hexdigest() == b['reused_exact_body_sha256']
    assert excerpt in Path(b['reused_fragment']['path']).read_text()
    assert leaf.count('pub unsafe extern "C" fn ') == 1
    assert b['symbol'] in leaf and b['real_provider'] in leaf
    assert 'kprintf' not in leaf and 'asm!' not in leaf
    assert plan['expected_cases'] == (140 if label == 'forward-context' else 175)
    assert len(plan['commands']) == 3
    assert not Path(plan['fresh_output']).exists()
    assert plan['actual_compile'] is plan['actual_runtime'] is None
    fixture = (d / 'fixture.c').read_text()
    rust = (d / 'fixture.rs').read_text()
    assert '#include <memory.h>' in fixture
    assert '__builtin_types_compatible_p' in fixture
    assert '#define ' + b['symbol'] + ' original_bridge' in fixture
    assert '#define ' + b['real_provider'] + ' fixture_provider' in fixture
    assert '#[link_name = "fixture_provider"]' in rust
    assert 'fn ' + b['symbol'] not in rust
    assert 'CHECK(now == old' in fixture and 'CHECK(calls == 1' in fixture
    if label != 'forward-context':
        assert 'result as CLong' in leaf
        assert 'now == (long)response' in fixture
        assert '0x8000000000000000UL' in fixture and '~0UL' in fixture
    else:
        assert 'super::syscall_generic_forwarding(number, context.cast())' in leaf
        assert '0x7fffffffffffffffL' in fixture and '(-0x7fffffffffffffffL - 1)' in fixture
    results.append(dict(symbol=b['symbol'], status='PASS_FOCUSED_SELECTED_SOURCE',
                        selected_cursor_count=31, source_reuse='exact body',
                        fallback='byte-exact reversible', proposed_mock_cases=plan['expected_cases']))
assert json.loads((D/'PROVIDER-PREDICATE-CORRECTION-TEST.json').read_text())['status'] == 'PASS'
print(json.dumps(dict(status='PASS_THREE_SELECTED26EB_PRIVATE_LEAVES_SOURCE',
                     results=results, actual_compile=None, actual_native=None), sort_keys=True))
