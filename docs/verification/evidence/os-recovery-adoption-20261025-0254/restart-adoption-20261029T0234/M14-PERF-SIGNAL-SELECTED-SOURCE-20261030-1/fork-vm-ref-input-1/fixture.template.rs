// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private behavioral input. This file is not an actual kernel ABI test.
#![allow(dead_code, non_camel_case_types)]
use core::ffi::c_void;
use core::mem::offset_of;
use core::ptr::{null_mut, addr_of_mut};
use core::sync::atomic::{AtomicI32, Ordering};
type CULong = u64;
type CInt = i32;
const EINVAL: CInt = 22;
#[repr(C)] struct IhkAtomic { counter: i32 }
#[repr(C)] struct AbiListHead { next: *mut AbiListHead, prev: *mut AbiListHead }
type ProcessRefIncFn = unsafe extern "C" fn(*mut c_void, CULong);
type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessMcsRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadProfileFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessVmActionFn = unsafe extern "C" fn(*mut c_void);
#[repr(C)] struct Vm { refs: IhkAtomic }
#[repr(C)] struct Thread { refs: IhkAtomic, vm: *mut c_void, proc_: *mut c_void }
static DESTROY_CALLS: AtomicI32 = AtomicI32::new(0);
static LIST_ADDS: AtomicI32 = AtomicI32::new(0);
unsafe fn process_list_add_tail_result(_: *mut AbiListHead, _: *mut AbiListHead) -> CInt {
    LIST_ADDS.fetch_add(1, Ordering::SeqCst); 1
}
unsafe extern "C" fn no_lock(_: CULong, _: *mut c_void) {}
unsafe extern "C" fn noop(_: *mut c_void) {}
unsafe extern "C" fn destroy(_: *mut c_void) { DESTROY_CALLS.fetch_add(1, Ordering::SeqCst); }
unsafe extern "C" fn release_vm(vm: *mut c_void) {
    let _ = process_ref_dec_and_test_direct_result(vm, offset_of!(Vm, refs) as u64);
}
// ACTUAL_SOURCE_BODIES
unsafe fn release(t: *mut Thread) {
    let _ = process_release_thread_body_result(t.cast(), offset_of!(Thread, refs) as u64,
        offset_of!(Thread, vm) as u64, offset_of!(Thread, proc_) as u64, None, None,
        Some(noop), Some(destroy), Some(release_vm));
}
unsafe fn setup(vm: &mut Vm, thread: &mut Thread) {
    let rc = process_clone_thread_shared_vm_state_body_result((thread as *mut Thread).cast(),
        1usize as *mut c_void, (vm as *mut Vm).cast(), offset_of!(Thread, vm) as u64,
        offset_of!(Thread, proc_) as u64);
    assert_eq!(rc, 0);
}
unsafe fn chain(vm: &mut Vm) {
    let mut a = AbiListHead { next: null_mut(), prev: null_mut() };
    let mut b = AbiListHead { next: null_mut(), prev: null_mut() };
    let mut c = AbiListHead { next: null_mut(), prev: null_mut() };
    let mut d = AbiListHead { next: null_mut(), prev: null_mut() };
    let mut node = 0u8;
    let rc = process_chain_thread_body_result(&mut a, &mut b, 0, &mut c, &mut d, 0,
        (vm as *mut Vm).cast(), offset_of!(Vm, refs) as u64, addr_of_mut!(node).cast(),
        Some(no_lock), Some(no_lock), None);
    assert_eq!(rc, 0);
}
fn thread() -> Thread { Thread { refs: IhkAtomic { counter: 2 }, vm: null_mut(), proc_: null_mut() } }
fn vm() -> Vm { Vm { refs: IhkAtomic { counter: 1 } } }
fn main() { unsafe {
    // Exact legacy abort shape: original sets child count to one before final release.
    let mut v = vm(); let mut t = thread(); setup(&mut v, &mut t);
    assert_eq!(v.refs.counter, 1); t.refs.counter = 1; release(&mut t);
    assert_eq!(v.refs.counter, 0, "pre-chain abort consumed parent VM reference");
    // Successful publication obtains the extra VM edge; final child release consumes it.
    let mut v = vm(); let mut t = thread(); setup(&mut v, &mut t); chain(&mut v);
    assert_eq!(v.refs.counter, 2); t.refs.counter = 1; release(&mut t);
    assert_eq!(v.refs.counter, 1); assert_eq!(LIST_ADDS.load(Ordering::SeqCst), 2);
    // Candidate reference accounting only: pin before abort, or transfer after chain.
    let mut v = vm(); let mut t = thread(); setup(&mut v, &mut t);
    assert_eq!(process_ref_inc_direct_result((&mut v as *mut Vm).cast(), 0), 0);
    t.refs.counter = 1; release(&mut t); assert_eq!(v.refs.counter, 1);
    let mut v = vm(); let mut t = thread(); setup(&mut v, &mut t);
    assert_eq!(process_ref_inc_direct_result((&mut v as *mut Vm).cast(), 0), 0);
    chain(&mut v); release_vm((&mut v as *mut Vm).cast());
    t.refs.counter = 1; release(&mut t); assert_eq!(v.refs.counter, 1);
    assert_eq!(DESTROY_CALLS.load(Ordering::SeqCst), 4);
    println!("actual-body reference accounting scenarios passed");
} }
