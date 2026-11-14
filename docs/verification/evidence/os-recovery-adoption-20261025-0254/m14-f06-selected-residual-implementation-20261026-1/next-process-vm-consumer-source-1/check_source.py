"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source-only consumer checks; this invokes no compiler or kernel effects.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

D = Path(__file__).resolve().parent
B = json.loads((D / 'SOURCE-BINDINGS.json').read_text())
helper = Path(B['composition_helper']['path'])
assert hashlib.sha256(helper.read_bytes()).hexdigest() == B['composition_helper']['sha256']
spec = importlib.util.spec_from_file_location('existing_composition', helper)
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)
c = (D / 'BASE.syscall.c').read_text()
rust = (D / 'BASE.syscall_policy.rs').read_text()
old = Path(B['reused_fragment']['path']).read_text()
selected_c, selected_rust, leaf, parts = compose.compose(c, rust, old)

def validate(candidate_c, candidate_rust, candidate_leaf):
    assert candidate_c == selected_c, 'paired C selection changed'
    assert candidate_rust == selected_rust, 'paired Rust selection changed'
    assert candidate_leaf == leaf, 'reused consumer changed'
    assert candidate_c.replace(parts['adapter_wrapper'], parts['adapters'], 1).replace(
        parts['entry_wrapper'], parts['entry'], 1) == c, 'C fallback not reversible'
    assert candidate_rust.removesuffix(parts['selection']) == rust
    assert candidate_leaf.count('unsafe extern "C" fn f06_process_vm_rw_') == 13
    assert candidate_leaf.count('pub unsafe extern "C" fn do_process_vm_read_writev(') == 1
    assert candidate_leaf.count('MaybeUninit::<McsRwlockNodeIrqsave>::uninit()') == 1
    assert candidate_leaf.count('MaybeUninit::<McsRwlockNode>::uninit()') == 1
    assert candidate_leaf.count('Some(arch_process_vm_rw_log_bridge)') == 1
    assert '&F06_PROCESS_VM_RW_OFFSETS' in candidate_leaf
    assert candidate_rust.count('pub static F06_PROCESS_VM_RW_OFFSETS:') == 1
    assert candidate_rust.count('pub unsafe extern "C" fn arch_process_vm_rw_log_bridge(') == 1
    assert 'fn f06_process_vm_rw_log' not in candidate_leaf
    assert 'static F06_PROCESS_VM_RW_OFFSETS' not in candidate_leaf
    assert 'process_vm_rw_body_result(' in rust
    assert rust.count('Some(do_process_vm_read_writev),') == 2

validate((D / 'syscall.c').read_text(), (D / 'syscall_policy.rs').read_text(),
         (D / 'f06_process_vm_entry.rs').read_text())
# These in-memory negative cases verify failures are observable without changing evidence.
for mutation in [(selected_c.replace('MCKERNEL_RUST_F06_PROCESS_VM_ENTRY', 'BROKEN', 1), selected_rust, leaf),
                 (selected_c, selected_rust.replace('f06_process_vm_entry_candidate', 'BROKEN', 1), leaf),
                 (selected_c, selected_rust, leaf.replace('MaybeUninit::<McsRwlockNode>',
                                                        'MaybeUninit::<McsRwlockNodeIrqsave>', 1))]:
    try:
        validate(*mutation)
    except AssertionError:
        pass
    else:
        raise AssertionError('consumer mutation escaped source check')
for r in B['canonical_before'] + [B['reused_fragment'], B['reused_leaf'], B['abi'],
                                  B['lock_helpers'], B['process_helpers'], B['x86_memory_helpers']]:
    assert hashlib.sha256(Path(r['path']).read_bytes()).hexdigest() == r['sha256'], r['path']
proof = json.loads((D / 'SELECTED-SYMBOL-PROOF.json').read_text())
assert len(proof['symbols']) == 14
assert all(s['allocated'] and s['type'] == 'FUNC' for s in proof['symbols'].values())
print(json.dumps({'status': 'PASS_PROCESS_VM_CONSUMER_SOURCE', 'selected_functions': 14,
                  'negative_source_cases': 3, 'fallback': 'byte-exact reversible',
                  'scope': 'source identity, composition, caller and selected-object evidence only',
                  'actual_compile': None, 'actual_link': None, 'actual_native': None}, sort_keys=True))
