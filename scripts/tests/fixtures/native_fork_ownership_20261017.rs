// SPDX-License-Identifier: GPL-2.0
// Boundary harness for verbatim production functions, substituted by the test.
// Linux VFS/MM and backend transport are fixtures; the fault-routing and worker
// admission decisions below come directly from the production Rust bodies.
#![allow(dead_code, non_camel_case_types)]
use std::{cell::{Cell, RefCell, RefMut}, ffi::c_void, pin::Pin, ptr::{self, NonNull}};
type Result<T = ()> = std::result::Result<T, i32>;
const EINVAL: i32 = -22;
const EACCES: i32 = -13;
const ENOENT: i32 = -2;
const EBUSY: i32 = -16;
const EOVERFLOW: i32 = -75;
fn errno(code: i32) -> i32 { code }
trait ErrorValue { fn to_errno(self) -> i32; }
impl ErrorValue for i32 { fn to_errno(self) -> i32 { self } }
struct Arc<T>(std::sync::Arc<T>);
impl<T> Arc<T> {
    fn new(value: T) -> Self { Self(std::sync::Arc::new(value)) }
    fn into_raw(this: Self) -> *const T { std::sync::Arc::into_raw(this.0) }
    unsafe fn from_raw(raw: *const T) -> Self { Self(unsafe { std::sync::Arc::from_raw(raw) }) }
    fn strong_count(this: &Self) -> usize { std::sync::Arc::strong_count(&this.0) }
}
impl<T> Clone for Arc<T> { fn clone(&self) -> Self { Self(self.0.clone()) } }
impl<T> std::ops::Deref for Arc<T> {
    type Target = T;
    fn deref(&self) -> &T { &self.0 }
}
struct ArcBorrow<'a, T> { raw: *const T, lifetime: std::marker::PhantomData<&'a T> }
impl<'a, T> ArcBorrow<'a, T> {
    unsafe fn from_raw(raw: *const T) -> Self { Self { raw, lifetime: std::marker::PhantomData } }
}
impl<T> std::ops::Deref for ArcBorrow<'_, T> {
    type Target = T;
    fn deref(&self) -> &T { unsafe { &*self.raw } }
}
impl<T> From<ArcBorrow<'_, T>> for Arc<T> {
    fn from(borrow: ArcBorrow<'_, T>) -> Self {
        let borrowed = std::mem::ManuallyDrop::new(unsafe { Arc::from_raw(borrow.raw) });
        Arc::clone(&borrowed)
    }
}
mod kernel {
    pub mod error {
        pub fn to_result(code: i32) -> Result<(), i32> {
            if code < 0 { Err(code) } else { Ok(()) }
        }
    }
}
mod application_abi { pub const LOOKUP: u32 = 3; }
mod wire {
    pub fn put_word(bytes: &mut [u8], offset: usize, value: u64) -> Result<(), i32> {
        bytes.get_mut(offset..offset + 8).ok_or(-22)?.copy_from_slice(&value.to_le_bytes());
        Ok(())
    }
    pub fn word(bytes: &[u8], offset: usize) -> Result<u64, i32> {
        Ok(u64::from_le_bytes(bytes.get(offset..offset + 8).ok_or(-22)?.try_into().unwrap()))
    }
}
mod bindings {
    use super::c_void;
    pub struct mm_struct { pub identity: u64 }
    pub struct file { pub private_data: *mut c_void }
    pub const VM_PFNMAP: u64 = 1024;
    pub const VM_DONTEXPAND: u64 = 2048;
    pub const VM_DONTDUMP: u64 = 4096;
    #[derive(Clone, Copy)]
    pub struct vma_geometry { pub vm_start: u64, pub vm_end: u64 }
    #[derive(Clone, Copy)]
    pub struct vma_fields { pub __bindgen_anon_1: vma_geometry }
    #[derive(Clone, Copy)]
    pub struct vma_flags { pub __vm_flags: u64 }
    #[derive(Clone, Copy)]
    pub struct vm_area_struct {
        pub vm_mm: *mut mm_struct, pub vm_file: *mut file,
        pub vm_private_data: *mut c_void, pub vm_ops: *const (),
        pub vm_pgoff: u64, pub __bindgen_anon_1: vma_fields, pub __bindgen_anon_2: vma_flags,
    }
    pub struct fault_fields { pub vma: *mut vm_area_struct, pub address: u64 }
    pub struct vm_fault { pub __bindgen_anon_1: fault_fields, pub flags: u64 }
}
struct MmIdentity(NonNull<bindings::mm_struct>);
struct Mirror { mm: MmIdentity, start: u64, end: u64 }
struct Registration { calls: Cell<usize>, physical: u64 }
impl Registration {
    fn invoke(&self, command: u32, bytes: &mut [u8]) -> Result {
        assert_eq!(command, application_abi::LOOKUP);
        self.calls.set(self.calls.get() + 1);
        wire::put_word(bytes, 16, self.physical)?;
        wire::put_word(bytes, 24, 3)
    }
}
struct VmOperations(());
static VM_OPERATIONS: VmOperations = VmOperations(());
@VMA_OWNERS@
fn vma(mm: *mut bindings::mm_struct, file: *mut bindings::file) -> bindings::vm_area_struct {
    bindings::vm_area_struct {
        vm_mm: mm, vm_file: file, vm_private_data: ptr::null_mut(), vm_ops: ptr::null(), vm_pgoff: 0,
        __bindgen_anon_1: bindings::vma_fields {
            __bindgen_anon_1: bindings::vma_geometry { vm_start: 0, vm_end: 0x8000 },
        },
        __bindgen_anon_2: bindings::vma_flags { __vm_flags: 0 },
    }
}
struct FaultPage {
    vma: *mut bindings::vm_area_struct,
    address: u64,
    physical: u64,
    permissions: u64,
}
mod fault_body {
    use super::*;
    // The extracted function uses super::application_abi as in production.
    @LOOKUP_FAULT@

    #[test]
    fn inherited_child_fault_rejects_parent_mapping_before_lookup() {
        let mut parent_mm = bindings::mm_struct { identity: 11 };
        let mut child_mm = bindings::mm_struct { identity: 12 };
        let registration = Arc::new(Registration { calls: Cell::new(0), physical: 0x9000 });
        let mirror = Arc::new(Mirror {
            mm: MmIdentity(NonNull::from(&mut parent_mm)), start: 0, end: 0x8000,
        });
        let owner = Arc::new(VmaOwner { registration: registration.clone(), mirror });
        let mut file = bindings::file { private_data: ptr::null_mut() };
        let mut vma = vma(&mut child_mm, &mut file);
        vma.vm_ops = &VM_OPERATIONS.0;
        vma.vm_private_data = Arc::into_raw(owner).cast_mut().cast();
        let mut fault = bindings::vm_fault {
            __bindgen_anon_1: bindings::fault_fields { vma: &mut vma, address: 0x1000 }, flags: 0,
        };
        assert!(matches!(unsafe { lookup_fault(&mut fault, false) }, Err(EACCES)));
        assert_eq!(registration.calls.get(), 0);
        // The same inherited file still correctly serves the parent's MM.
        vma.vm_mm = &mut parent_mm;
        let page = unsafe { lookup_fault(&mut fault, false) }.unwrap();
        assert_eq!(page.address, 0x1000);
        assert_eq!(page.physical, 0x9000);
        assert_eq!(page.permissions, 3);
        assert_eq!(page.vma, &mut vma as *mut _);
        assert_eq!(registration.calls.get(), 1);
        unsafe { vma_close(&mut vma) };
    }
}
type Token = u64;
struct Mutex<T>(RefCell<T>);
impl<T> Mutex<T> { fn lock(&self) -> RefMut<'_, T> { self.0.borrow_mut() } }
struct Preparation { outcome: Option<i32> }
impl Preparation { fn result(&self) -> Option<i32> { self.outcome } }
struct Mailbox { opens: usize, closes: usize }
impl Mailbox {
    fn open_worker(&mut self, _tid: i32) -> Result<u64> { self.opens += 1; Ok(77) }
    fn close_worker(&mut self, _handle: u64) -> Result { self.closes += 1; Ok(()) }
    fn quarantined(&self) -> bool { false }
}
struct Entry {
    token: Token, closed: bool, needs_cleanup: bool, quarantined: bool,
    prepare: Option<Preparation>, syscalls: Mailbox,
    baseline_cancel_calls: usize, baseline_cancel_worker: Option<u64>,
}
impl Entry { fn key(&self) -> Token { self.token } }
// Explicit no-child baseline adapter for the newly introduced worker-close
// dependency. This fixture has exactly one parent and cannot represent a child
// transaction. Real child cancellation is covered by the backend actual bodies.
fn abort_parent_forks(slots: &mut [Option<Entry>], parent: Token, worker: Option<u64>) {
    assert_eq!(slots.len(), 1, "no-child baseline only");
    let entry = slots[0].as_mut().expect("baseline parent remains live");
    assert_eq!(entry.key(), parent, "no child entry in this adapter");
    entry.baseline_cancel_calls += 1;
    entry.baseline_cancel_worker = worker;
}
struct Remote { slots: Mutex<Vec<Option<Entry>>> }
impl Remote {
    @WORKER@
}
fn remote(prepare: Option<Preparation>) -> Remote {
    Remote { slots: Mutex(RefCell::new(vec![Some(Entry {
        token: 4, closed: false, needs_cleanup: false, quarantined: false,
        prepare, syscalls: Mailbox { opens: 0, closes: 0 },
        baseline_cancel_calls: 0, baseline_cancel_worker: None,
    })])) }
}
#[test]
fn reserved_child_cannot_open_worker_without_adopted_image() {
    let backend = remote(None);
    let mut bytes = [0; 16];
    bytes[..8].copy_from_slice(&123i64.to_le_bytes());
    assert_eq!(backend.worker(4, &mut bytes, true), Err(EINVAL));
    assert_eq!(backend.slots.lock()[0].as_ref().unwrap().syscalls.opens, 0);
    assert_eq!(&bytes[8..], &[0; 8]);
}
#[test]
fn prepared_child_control_can_open_worker() {
    let backend = remote(Some(Preparation { outcome: Some(0) }));
    let mut bytes = [0; 16];
    bytes[..8].copy_from_slice(&123i64.to_le_bytes());
    assert_eq!(backend.worker(4, &mut bytes, true), Ok(()));
    assert_eq!(u64::from_le_bytes(bytes[8..].try_into().unwrap()), 77);
    assert_eq!(backend.slots.lock()[0].as_ref().unwrap().syscalls.opens, 1);
    bytes[..8].copy_from_slice(&77u64.to_le_bytes());
    assert_eq!(backend.worker(4, &mut bytes, false), Ok(()));
    let slots = backend.slots.lock();
    let parent = slots[0].as_ref().unwrap();
    assert_eq!(parent.syscalls.closes, 1);
    assert_eq!(parent.baseline_cancel_calls, 1);
    assert_eq!(parent.baseline_cancel_worker, Some(77));
}
#[test]
fn pending_or_failed_preparation_does_not_open_worker() {
    for (outcome, expected) in [(None, EBUSY), (Some(-5), -5)] {
        let backend = remote(Some(Preparation { outcome }));
        assert_eq!(backend.worker(4, &mut [0; 16], true), Err(expected));
        assert_eq!(backend.slots.lock()[0].as_ref().unwrap().syscalls.opens, 0);
    }
}
