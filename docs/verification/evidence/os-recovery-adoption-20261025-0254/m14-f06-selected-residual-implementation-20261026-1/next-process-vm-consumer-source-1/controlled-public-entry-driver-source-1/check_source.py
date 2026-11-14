"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source checks for the controlled public-entry driver, no compiler or effects.
"""
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
plan = json.loads((D / 'FUTURE-HOST-COMMAND-PLAN.json').read_text())
for row in plan['inputs'] + plan['canonical'] + plan['reused'] + plan['tools']:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'], row['path']
c = Path(plan['canonical'][0]['path']).read_text()
r = Path(plan['canonical'][1]['path']).read_text()
for name in ['original-types.inc', 'original-body-prototype.inc', 'original-adapters.inc',
             'original-entry.inc', 'genuine-prologue.inc']:
    assert (D / name).read_text() in c, name
for name in ['actual-body.inc', 'actual-types.inc', 'actual-layouts.inc',
             'actual-node.inc', 'actual-offsets.inc']:
    assert (D / name).read_text() in r, name
assert (D / 'f06_process_vm_entry.rs').read_bytes() == Path(plan['reused'][0]['path']).read_bytes()
assert (D / 'ABI-caller.inc').read_bytes() == Path(plan['reused'][1]['path']).read_bytes()
assert (D / 'Rust-ABI-facts.inc').read_bytes() == Path(plan['reused'][2]['path']).read_bytes()
assert (D / 'abi.rs').read_bytes() == Path(plan['canonical'][2]['path']).read_bytes()
leaf = (D / 'f06_process_vm_entry.rs').read_text()
rust = (D / 'fixture.rs').read_text()
fixture = (D / 'fixture.c').read_text()
driver = (D / 'controlled-driver.inc').read_text()
providers = (D / 'fixture-providers.rs').read_text()
assert leaf.count('pub unsafe extern "C" fn do_process_vm_read_writev(') == 1
assert leaf.count('unsafe extern "C" fn f06_process_vm_rw_') == 13
assert 'fn do_process_vm_read_writev(' not in providers
assert '#include "original-entry.inc"' in fixture
assert 'include!("actual-body.inc")' in rust
assert 'mod f06_process_vm_entry;' in rust
assert '#[link_name = "fixture_cpu"]' in providers
assert 'f06_process_vm_rw_compare_ABI() == 0' in driver
assert 'f06_process_vm_rw_validation_entry_comparison() == 0' in driver
assert 'm < CASE_COUNT' in driver and 'op < 2' in driver
assert 'int expected_copied = mode == NORMAL || mode == FAULT_RETRY ? 32 : mode == PARTIAL_FAIL ? 16 : 0;' in driver
assert 'if (m == MISSING_PROCESS || m == EXITED_PROCESS) return -ESRCH;' in driver
assert 'CHECK(invoke(1, op) == old && effect_count == n);' in driver
assert 'effects[i].a == saved_effects[i].a' in driver
assert 'record->a' not in driver and 'record->b' not in driver
assert '((void *)node != find_node' in driver
assert 'node == find_node && hash_held && !update_held' in driver
assert 'range_locks[id]-- == 1' in driver
assert 'vm_holds == 1 && !hash_held && !update_held' in driver
assert len(plan['commands']) == 4
assert not Path(plan['fresh_output']).exists()
assert all(plan[k] is None for k in ['actual_compile', 'actual_link', 'actual_runtime'])
assert plan['redirects']['do_process_vm_read_writev'] == 'original_selected_process_vm_rw'
assert plan['expected_stdout'] == 'PASS process_vm public entry ABI22 controlled pairs40 invalidflags4\n'
print(json.dumps(dict(status='PASS_CONTROLLED_PUBLIC_ENTRY_SOURCE',
    actual_target='unchanged public entry +13 adapters +canonical orchestration',
    ABI_facts=22, controlled_pairs=40, invalid_flags=4, commands=4,
    actual_compile=None, actual_runtime=None, native=None), sort_keys=True))
