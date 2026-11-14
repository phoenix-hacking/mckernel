"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One source-only process-VM public-entry driver composition; no compiler invocation.
"""
import hashlib
import json
from pathlib import Path
import re

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
P = D.parent.parent

def ref(p):
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def section(text, start, end):
    assert text.count(start) == text.count(end) == 1, (start, end)
    return text[text.index(start):text.index(end, text.index(start))]

def put(name, data):
    with (D / name).open('x') as f:
        f.write(data)

c_path = ROOT / 'arch/x86_64/kernel/syscall.c'
r_path = ROOT / 'kernel/rust/syscall_policy.rs'
c = c_path.read_text()
r = r_path.read_text()
abi = ROOT / 'kernel/rust/abi.rs'
leaf = D.parent / 'f06_process_vm_entry.rs'
caller = D.parent / 'future-abi-facts-output-3/real-ABI-and-validation-caller.c'
old = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-process-vm-rw-source-1/future-fixture-source-only')
facts = old / 'real-ABI-Rust-facts.inc'
put('abi.rs', abi.read_text())
put('f06_process_vm_entry.rs', leaf.read_text())
put('ABI-caller.inc', caller.read_text())
put('Rust-ABI-facts.inc', facts.read_text())

body = section(r, '#[no_mangle]\npub extern "C" fn process_vm_validate_args(',
               '#[no_mangle]\npub unsafe extern "C" fn prctl_body_result(')
types = section(r, 'type ProcessVmRwFn =', 'type UtilThreadFn =')
layouts = section(r, '#[repr(C)]\npub struct ArchProcessVmRwOffsets {',
                  '#[repr(C)]\npub struct MemlockLogRecord {')
node = section(r, '#[repr(C, align(64))]\nstruct McsRwlockNode {',
               '#[repr(C)]\npub struct SyscallItimerOffsets {')
offsets = section(r, '#[used]\n#[export_name = "arch_process_vm_rw_kernel_offsets"]',
                  '// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n// Generated only from the genuine syscall_list.h/profile.h pinned in the manifest.')
names = ['EINVAL', 'EFAULT', 'ESRCH', 'EPERM', 'IOV_MAX', 'PROCESS_VM_READ',
         'PROCESS_VM_WRITE', 'PS_EXITED', 'PS_ZOMBIE', 'PAGE_SIZE', 'PAGE_SHIFT',
         'PAGE_MASK', 'PF_POPULATE', 'PF_WRITE', 'PF_USER', 'VR_PROT_READ', 'VR_PROT_WRITE']
constants = '\n'.join(next(line for line in r.splitlines()
                           if line.startswith('const ' + name + ':')) for name in names) + '\n'
for name, data in [('actual-body.inc', body), ('actual-types.inc', types),
                   ('actual-layouts.inc', layouts), ('actual-node.inc', node),
                   ('actual-offsets.inc', offsets), ('actual-constants.inc', constants)]:
    put(name, data)
rust = '''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile, write};
use crate::abi::{CInt, CLong, CULong, IhkAtomic, Iovec, Process, ProcessVm, SizeT, Thread, VmRange};
use crate::lock_helpers::McsRwlockNodeIrqsave;
#[path = "abi.rs"]
mod abi;
include!("fixture-providers.rs");
include!("actual-types.inc");
include!("actual-layouts.inc");
include!("actual-node.inc");
include!("actual-constants.inc");
include!("actual-offsets.inc");
include!("actual-body.inc");
include!("Rust-ABI-facts.inc");
#[path = "f06_process_vm_entry.rs"]
mod f06_process_vm_entry;
extern "C" {
    fn arch_process_vm_rw_log_bridge(record: *const ArchProcessVmRwLogRecord);
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { loop {} }
'''
put('fixture.rs', rust)

c_types = section(c, 'typedef void (*arch_process_vm_rw_lock_fn_t)(void *vm);',
                  'struct ptrace_report_signal_offsets {')
prototype = section(c, 'extern int arch_process_vm_read_writev_body_result(int pid,',
                    'extern void arch_clear_single_step_body_result(')
adapters = section(c, '\nstatic void\narch_process_vm_rw_read_lock_bridge(void *vm)',
                   '\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nextern void arch_process_vm_rw_log_bridge')
entry = section(c, '\nint do_process_vm_read_writev(int pid, ',
                '\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n#line 3662\nint move_pages_smp_handler')
for name, data in [('original-types.inc', c_types), ('original-body-prototype.inc', prototype),
                   ('original-adapters.inc', adapters), ('original-entry.inc', entry)]:
    put(name, data)
prologue = c.split('\nvoid terminate_mcexec(int, int);', 1)[0] + '\n'
put('genuine-prologue.inc', prologue)
prototypes = '''
struct cpu_local_var *fixture_cpu(void);
void fixture_range_lock(ihk_rwspinlock_t *);
void fixture_range_unlock(ihk_rwspinlock_t *);
struct vm_range *fixture_lookup(struct process_vm *, unsigned long, unsigned long);
struct process *fixture_find(int, struct mcs_rwlock_node_irqsave *);
void fixture_process_unlock(struct process *, struct mcs_rwlock_node_irqsave *);
void fixture_update_lock(struct mcs_rwlock_lock *, struct mcs_rwlock_node *);
void fixture_update_unlock(struct mcs_rwlock_lock *, struct mcs_rwlock_node *);
void fixture_hold(struct process_vm *);
void fixture_release(struct process_vm *);
int fixture_vtop(struct page_table *, const void *, unsigned long *, unsigned long *);
int fixture_fault(struct process_vm *, void *, unsigned long);
void *fixture_phys(unsigned long);
void *fixture_copy(void *, const void *, size_t);
extern void arch_process_vm_rw_log_bridge(const struct arch_process_vm_rw_log_record *);
extern const struct arch_process_vm_rw_offsets arch_process_vm_rw_kernel_offsets;
'''
redirects = {
    'get_this_cpu_local_var': 'fixture_cpu',
    'ihk_rwspinlock_read_lock_noirq': 'fixture_range_lock',
    'ihk_rwspinlock_read_unlock_noirq': 'fixture_range_unlock',
    'lookup_process_memory_range': 'fixture_lookup', 'find_process': 'fixture_find',
    'process_unlock': 'fixture_process_unlock',
    'mcs_rwlock_reader_lock_noirq': 'fixture_update_lock',
    'mcs_rwlock_reader_unlock_noirq': 'fixture_update_unlock',
    'hold_process_vm': 'fixture_hold', 'release_process_vm': 'fixture_release',
    'ihk_mc_pt_virt_to_phys_size': 'fixture_vtop', 'page_fault_process_vm': 'fixture_fault',
    'phys_to_virt': 'fixture_phys', 'fast_memcpy': 'fixture_copy',
    'do_process_vm_read_writev': 'original_selected_process_vm_rw',
}
defines = ''.join('#undef ' + k + '\n#define ' + k + ' ' + v + '\n'
                  for k, v in redirects.items())
undefines = ''.join('#undef ' + k + '\n' for k in redirects)
fixture_c = ('#include "genuine-prologue.inc"\n#include "original-types.inc"\n'
             '#include "original-body-prototype.inc"\n' + prototypes + defines +
             '#include "original-adapters.inc"\n#include "original-entry.inc"\n' + undefines +
             '#include "ABI-caller.inc"\n#include "controlled-driver.inc"\n')
put('fixture.c', fixture_c)

previous = json.loads((D.parent / 'NEXT-ABI-FACTS-COMMAND.json').read_text())
out = D / 'future-output-1'
gcc = list(previous['argv'])
gcc[gcc.index('-o') + 1] = str(out / 'fixture.o')
gcc[gcc.index('-c') + 1] = str(D / 'fixture.c')
rustc = Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
commands = [
    [str(rustc), '--edition=2021', '--crate-name', 'f06_process_vm_fixture', '--crate-type',
     'staticlib', '-C', 'panic=abort', '-C', 'opt-level=1', '-C', 'code-model=large',
     '-C', 'relocation-model=static', str(D / 'fixture.rs'), '-o', str(out / 'libfixture.a')],
    gcc,
    ['/usr/bin/gcc-9', '-no-pie', str(out / 'fixture.o'), str(out / 'libfixture.a'),
     '-o', str(out / 'driver')],
    [str(out / 'driver')],
]
manifest = dict(status='SOURCE_ONLY_ROOT_GRANT_REQUIRED', scope=__doc__,
    purpose='Compile actual public entry/body and genuine-header C baseline; compare ABI22 and controlled40 boundary pairs plus4 invalid flags; no kernel effects.',
    canonical=[ref(c_path), ref(r_path), ref(abi)],
    reused=[ref(leaf), ref(caller), ref(facts), ref(ROOT / 'kernel/rust/lock_helpers.rs')],
    genuine_configuration=ref(P / 'GENUINE-NOCACHE-CONFIGURATION.json'),
    tools=[ref(Path('/usr/bin/gcc-9')), ref(rustc)],
    inputs=[ref(q) for q in sorted(D.iterdir()) if q.is_file()],
    cwd=str(D), fresh_output=str(out), commands=commands, limits=previous['limits'],
    admission='Unchanged reviewed e8b84de3.admission()/04b5/adf, fixed cutoffs, HOST/scratch floors, fresh Root grant before dispatch.',
    redirects=redirects, expected_stdout='PASS process_vm public entry ABI22 controlled pairs40 invalidflags4\n',
    holds=['real MM/usercopy/fault/concurrency', 'VMlock192/ABI6 direct receipt unresolved',
           'final-reference and current-stack ownership', 'native/default selection'],
    actual_compile=None, actual_link=None, actual_runtime=None)
put('FUTURE-HOST-COMMAND-PLAN.json', json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(status='PASS_SOURCE_COMPOSITION', commands=len(commands),
                     plan=ref(D / 'FUTURE-HOST-COMMAND-PLAN.json'))))
