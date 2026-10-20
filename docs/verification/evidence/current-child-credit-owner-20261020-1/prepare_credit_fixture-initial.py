from pathlib import Path
import hashlib, json, re, sys
sys.path.insert(0, '/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
F = P / 'fixture'
F.mkdir()
rows = []
def ref(path):
    b = path.read_bytes()
    return {'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}
def copy(source, name):
    target = F / name
    with target.open('xb') as stream: stream.write(source.read_bytes())
    rows.append({'actual_source': ref(source), 'fixture': ref(target), 'whole_module_equal': True})
copy(ROOT / 'kernel/rust/abi.rs', 'abi.rs')
copy(ROOT / 'kernel/rust/fork_control_registry.rs', 'fork_control_registry.rs')
copy(P / 'source/kernel/rust/fork_control_guest.rs', 'fork_control_guest.rs')
target = F / 'fork_child_credits.rs'
actual = P / 'source/kernel/rust/fork_child_credits.rs'
tests = P / 'credit_tests.rs'
with target.open('xb') as stream: stream.write(actual.read_bytes() + tests.read_bytes())
rows.append({'actual_source': ref(actual), 'fixture': ref(target),
             'production_prefix_byte_equal': True, 'appended_test_only': ref(tests)})
source = (ROOT / 'kernel/rust/process_helpers.rs').read_text()
names = ['process_ref_release_should_destroy_result', 'process_ref_dec_and_test_result',
         'process_ref_atomic_at', 'process_ref_dec_and_test_direct_result', 'field_ptr',
         'process_thread_profile_result', 'process_thread_action_result', 'process_vm_action_result',
         'process_release_thread_body_result', 'release_thread']
selected = []
for name in names:
    marker = re.search(r'(?m)^(?:pub )?(?:unsafe )?(?:extern "C" )?fn ' + name + r'\(', source)
    assert marker, name
    body = balanced_item(source, marker.group())
    selected.append(body)
    rows.append({'source': str(ROOT / 'kernel/rust/process_helpers.rs'), 'item': name,
                 'sha256': hashlib.sha256(body.encode()).hexdigest(), 'actual_body_equal': True})
aliases = []
for name in ['ProcessRefDecAndTestFn', 'ProcessThreadProfileFn', 'ProcessThreadActionFn', 'ProcessVmActionFn']:
    match = re.search(r'(?m)^pub type ' + name + r'\s*=.*?;', source, re.S)
    assert match, name
    aliases.append(match.group())
prelude = '''use core::ffi::c_void;
use core::mem::offset_of;
use core::sync::atomic::{AtomicI32,Ordering};
use crate::abi::{CInt,CULong,Thread,IhkAtomic};
const EINVAL:i32=22;
unsafe extern "C" fn process_release_thread_profile_bridge(_: *mut c_void, _: *mut c_void){crate::unexpected_destructor();}
unsafe extern "C" fn process_procfs_delete_thread_bridge(_: *mut c_void){crate::unexpected_destructor();}
unsafe extern "C" fn process_destroy_thread_bridge(_: *mut c_void){crate::unexpected_destructor();}
unsafe extern "C" fn process_release_vm_bridge(_: *mut c_void){crate::unexpected_destructor();}
'''
with (F / 'process_helpers.rs').open('x') as stream:
    stream.write(prelude + '\n'.join(aliases + selected))
cpu = (ROOT / 'kernel/rust/x86_cpu_helpers.rs').read_text()
match = re.search(r'(?m)^pub(?: unsafe)? extern "C" fn cpu_pause\(', cpu)
assert match
pause = balanced_item(cpu, match.group())
with (F / 'x86_cpu_helpers.rs').open('x') as stream: stream.write(pause)
rows.append({'source': str(ROOT / 'kernel/rust/x86_cpu_helpers.rs'), 'item': 'cpu_pause',
             'sha256': hashlib.sha256(pause.encode()).hexdigest(), 'actual_body_equal': True})
root = r'''#![allow(dead_code)]
use std::sync::atomic::{AtomicUsize,Ordering};
mod abi;
mod process_helpers;
mod fork_control_registry;
mod fork_control_guest;
mod x86_cpu_helpers;
static OFFLOAD_CALLS:AtomicUsize=AtomicUsize::new(0);
static DESTRUCTORS:AtomicUsize=AtomicUsize::new(0);
fn unexpected_destructor(){DESTRUCTORS.fetch_add(1,Ordering::SeqCst);panic!("no last parent reference/destructor authorized");}
#[no_mangle]
unsafe extern "C" fn do_syscall(_: *mut abi::SyscallRequest,_:abi::CInt)->abi::CLong{
    OFFLOAD_CALLS.fetch_add(1,Ordering::SeqCst);-95
}
mod cls{
    use std::sync::atomic::{AtomicPtr,Ordering};use crate::abi::CpuLocalVar;
    static CURRENT:AtomicPtr<CpuLocalVar>=AtomicPtr::new(core::ptr::null_mut());
    pub unsafe fn set(pointer:*mut CpuLocalVar){CURRENT.store(pointer,Ordering::SeqCst);}
    pub unsafe fn get_this_cpu_local_var()->*mut CpuLocalVar{CURRENT.load(Ordering::SeqCst)}
}
mod x86_memory_helpers{
    pub unsafe fn virt_to_phys(pointer:*mut core::ffi::c_void)->u64{pointer as u64}
}
mod mem_helpers{
    use std::alloc::{alloc,dealloc,Layout};use std::sync::atomic::{AtomicUsize,Ordering};
    use core::ffi::c_void;use crate::fork_control_guest::Carrier;
    static FREES:AtomicUsize=AtomicUsize::new(0);
    pub unsafe fn kmalloc(bytes:i32,_:i32)->*mut c_void{
        assert_eq!(bytes as usize,core::mem::size_of::<Carrier>());
        alloc(Layout::new::<Carrier>()).cast()
    }
    pub unsafe fn kfree(pointer:*mut c_void){
        FREES.fetch_add(1,Ordering::SeqCst);dealloc(pointer.cast(),Layout::new::<Carrier>());
    }
    pub fn frees()->usize{FREES.load(Ordering::SeqCst)}
}
'''
with (F / 'actual-child-credits.rs').open('x') as stream: stream.write(root)
inputs = {'schema': 'mckernel.actual-current-child-credit-fixture.v1', 'rows': rows,
          'actual_layouts': 'whole current abi.rs, distinct real Thread/Process/ProcessVm/CpuLocalVar objects',
          'actual_release': '10 unchanged production release_thread/refcount/action bodies with real SeqCst decrement',
          'adapters': ['CLS current pointer', 'Linux allocator for Carrier only', 'pointer physical-address adapter',
                       'unexecuted destructor bridges fail closed', 'do_syscall adapter always-95 and asserted0calls'],
          'not_proven': ['real CPU reservation acquisition/release', 'guest offload/hardware', 'current do_fork caller integration', 'last-reference destructor'],
          'new_tests': 3, 'old_tests_replayed': 0, 'new_C_compute': 0}
with (P / 'FIXTURE-INPUTS.json').open('x') as stream: json.dump(inputs, stream, sort_keys=True, indent=2); stream.write('\n')
