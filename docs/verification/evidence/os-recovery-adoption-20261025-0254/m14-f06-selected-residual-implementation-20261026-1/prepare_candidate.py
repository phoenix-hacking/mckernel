"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One private current-source selector composition. No compiler or canonical writes.
"""
import difflib
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
PREVIOUS = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-process-vm-rw-source-1/candidate/syscall_policy.process_vm_rw.FRAGMENT.rs')


def reference(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def compose(c, policy, previous):
    begin = '\nstatic void\narch_process_vm_rw_read_lock_bridge(void *vm)'
    end = '\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nextern void arch_process_vm_rw_log_bridge'
    assert c.count(begin) == c.count(end) == 1
    left = c.index(begin); right = c.index(end, left)
    adapters = c[left:right]
    condition = '(defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_PROCESS_VM_ENTRY))'
    adapter_wrapper = '\n#if !' + condition + adapters + '\n#endif\n'
    selected = c[:left] + adapter_wrapper + c[right:]
    begin_entry = '\nint do_process_vm_read_writev(int pid, '
    end_entry = '\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n#line 3662\nint move_pages_smp_handler'
    assert selected.count(begin_entry) == selected.count(end_entry) == 1
    left = selected.index(begin_entry); right = selected.index(end_entry, left)
    entry = selected[left:right]
    declaration = '\nextern int do_process_vm_read_writev(int pid,\n\t\tconst struct iovec *local_iov, unsigned long liovcnt,\n\t\tconst struct iovec *remote_iov, unsigned long riovcnt,\n\t\tunsigned long flags, int op);\n'
    entry_wrapper = '\n#if ' + condition + declaration + '#else\n' + entry + '\n#endif\n'
    selected = selected[:left] + entry_wrapper + selected[right:]
    callbacks = previous[previous.index('unsafe extern "C" fn f06_process_vm_rw_read_lock'):previous.index('\n#[used]')]
    public_entry = previous[previous.index('/// Reuse the exact validated process-VM'):]
    public_entry = public_entry.replace('Some(f06_process_vm_rw_log)', 'Some(arch_process_vm_rw_log_bridge)')
    public_entry = public_entry.replace('#[no_mangle]', '''///
/// # Safety
/// The caller supplies the same live process-VM operation and initialized iovecs
/// as the existing C entry. Current CPU/thread ownership remains valid through
/// this synchronous call. Existing providers retain process/VM/lock lifetimes,
/// user-copy validation and partial-copy/error cleanup. The two distinct stack
/// lock nodes must not escape the existing synchronous body or its callbacks.
#[no_mangle]''', 1)
    module = '''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reuse the existing private entry/callbacks; canonical logger/offsets stay sole providers.
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::ptr::{addr_of, addr_of_mut, read_volatile};

use crate::abi::{CInt, CULong, Iovec, Process, ProcessVm, SizeT};
use crate::lock_helpers::McsRwlockNodeIrqsave;

use super::{
    arch_process_vm_read_writev_body_result, arch_process_vm_rw_log_bridge,
    McsRwlockNode, F06_PROCESS_VM_RW_OFFSETS,
};

''' + callbacks + '\n' + public_entry
    selection = '''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Paired centrally with MCKERNEL_RUST_F06_PROCESS_VM_ENTRY; no automatic selection.
#[cfg(f06_process_vm_entry_candidate)]
#[path = "f06_process_vm_entry.rs"]
mod f06_process_vm_entry;
'''
    assert 'mod f06_process_vm_entry;' not in policy
    return selected, policy + selection, module, dict(adapters=adapters, adapter_wrapper=adapter_wrapper,
        entry=entry, entry_wrapper=entry_wrapper, selection=selection)


def main():
    previous = PREVIOUS.read_text()
    assert reference(PREVIOUS)['sha256'] == '3f9ecdfa165680224b983928939d5d81015cc9a075fae25210deafb7f9c1c3b5'
    c_path = ROOT / 'arch/x86_64/kernel/syscall.c'
    policy_path = ROOT / 'kernel/rust/syscall_policy.rs'
    c, policy = c_path.read_text(), policy_path.read_text()
    candidate_c, candidate_policy, module, parts = compose(c, policy, previous)
    for name, data in [('syscall.c', candidate_c), ('syscall_policy.rs', candidate_policy),
                       ('f06_process_vm_entry.rs', module)]:
        with (D / name).open('x') as output:
            output.write(data)
    for name, before, after, canonical in [('syscall.c.diff', c, candidate_c, 'arch/x86_64/kernel/syscall.c'),
                                          ('syscall_policy.rs.diff', policy, candidate_policy, 'kernel/rust/syscall_policy.rs')]:
        (D / name).write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                   fromfile=canonical, tofile=canonical)))
    (D / 'SOURCE-BINDINGS.json').write_text(json.dumps(dict(scope=__doc__,
        before=[reference(c_path), reference(policy_path)], reused_fragment=reference(PREVIOUS),
        after=[reference(D / name) for name in ['syscall.c', 'syscall_policy.rs', 'f06_process_vm_entry.rs']],
        actual_compile=None, actual_link=None, actual_native=None,
        central_activation={'C':'MCKERNEL_RUST_F06_PROCESS_VM_ENTRY', 'Rust':'f06_process_vm_entry_candidate'}), indent=2)+'\n')


if __name__ == '__main__':
    main()
