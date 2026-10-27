"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused source-composition regression; no compiler, execution oracle or native claim.
"""
import hashlib
import json
from pathlib import Path
import prepare_candidate as candidate

D = Path(__file__).resolve().parent
bindings = json.loads((D / 'SOURCE-BINDINGS.json').read_text())
c_path, rust_path = [Path(r['path']) for r in bindings['before']]
for r in bindings['before'] + [bindings['reused_fragment']]:
    assert candidate.reference(Path(r['path'])) == r, 'frozen source changed'
c, rust, module, parts = candidate.compose(c_path.read_text(), rust_path.read_text(), candidate.PREVIOUS.read_text())
assert (D / 'syscall.c').read_text() == c
assert (D / 'syscall_policy.rs').read_text() == rust
assert (D / 'f06_process_vm_entry.rs').read_text() == module
# Disabling the paired selector recovers the entire original C translation unit.
assert c.replace(parts['adapter_wrapper'], parts['adapters'], 1).replace(
    parts['entry_wrapper'], parts['entry'], 1) == c_path.read_text()
assert rust.removesuffix(parts['selection']) == rust_path.read_text()
# All adapters are reused byte-for-byte; no algorithm, locks or copy provider added.
old = candidate.PREVIOUS.read_text()
callbacks = old[old.index('unsafe extern "C" fn f06_process_vm_rw_read_lock'):old.index('\n#[used]')]
assert callbacks in module
assert callbacks.count('unsafe extern "C" fn ') == 13
assert module.count('pub unsafe extern "C" fn do_process_vm_read_writev(') == 1
assert module.count('MaybeUninit::<McsRwlockNodeIrqsave>::uninit()') == 1
assert module.count('MaybeUninit::<McsRwlockNode>::uninit()') == 1
assert module.count('Some(arch_process_vm_rw_log_bridge)') == 1
assert '&F06_PROCESS_VM_RW_OFFSETS' in module
assert 'static F06_PROCESS_VM_RW_OFFSETS' not in module
assert 'static mut F06_PROCESS_VM_' not in module
assert 'unsafe extern "C" fn f06_process_vm_rw_log' not in module
assert 'arch_process_vm_read_writev_body_result(' in module
# Canonical logger and thirteen-offset storage remain exactly one sole provider.
assert rust.count('pub unsafe extern "C" fn arch_process_vm_rw_log_bridge(') == 1
assert rust.count('pub static F06_PROCESS_VM_RW_OFFSETS:') == 1
# The C + Rust gate must be selected together by the dispatcher; never auto-enabled.
assert '#[cfg(f06_process_vm_entry_candidate)]' in parts['selection']
assert 'defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_PROCESS_VM_ENTRY)' in parts['entry_wrapper']
result = dict(status='PASS_FOCUSED_SOURCE_COMPOSITION', checks=16,
              scope='source identity/reversibility/reuse/provider uniqueness only',
              compile=None, link=None, native=None, whole_file_retirement=False)
print(json.dumps(result, sort_keys=True))
