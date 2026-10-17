// SPDX-License-Identifier: GPL-2.0
// Actual RPC, request/response, mailbox and fork reservation decisions.
// Vec allocation, Linux child PID/MM and OS identity are explicit adapters.
#![allow(dead_code)]
extern crate self as kernel;
use std::{cell::UnsafeCell, ptr::NonNull, sync::{Arc, atomic::{AtomicUsize, Ordering}}};
type Result<T = ()> = std::result::Result<T, i32>;
const EINVAL: i32 = -22; const EACCES: i32 = -13; const EBUSY: i32 = -16;
const ENOENT: i32 = -2; const EOVERFLOW: i32 = -75;
fn errno(code: i32) -> i32 { code }
pub mod error { pub fn to_result(value: i32) -> std::result::Result<(), i32> { if value < 0 { Err(value) } else { Ok(()) } } }
pub mod prelude {
    pub const GFP_KERNEL: u32 = 0;
    pub struct Vec<T>(std::vec::Vec<T>);
    pub trait VecExt<T>: Sized {
        fn with_capacity(capacity: usize, flags: u32) -> std::result::Result<Self, ()>;
        fn push(&mut self, value: T, flags: u32) -> std::result::Result<(), ()>;
    }
    impl<T> VecExt<T> for Vec<T> {
        fn with_capacity(capacity: usize, _: u32) -> std::result::Result<Self, ()> { Ok(Self(std::vec::Vec::with_capacity(capacity))) }
        fn push(&mut self, value: T, _: u32) -> std::result::Result<(), ()> { self.0.push(value); Ok(()) }
    }
    impl<T> std::ops::Deref for Vec<T> { type Target = std::vec::Vec<T>; fn deref(&self) -> &Self::Target { &self.0 } }
    impl<T> std::ops::DerefMut for Vec<T> { fn deref_mut(&mut self) -> &mut Self::Target { &mut self.0 } }
}
mod application_rpc { @RPC@ }
mod application_syscall { @SYSCALL@ }
mod smp_application_syscall { @MAILBOX@ }
use application_rpc::{Exchange, Token};
use application_syscall::{Request, ResponseMemory};
use smp_application_syscall::Mailbox;
mod smp_application_image {
    use super::*;
@TRANSITIONS@
@RESERVATION_METADATA@
}
use smp_application_image::*;
#[derive(Clone, Copy)]
struct OsToken(u32, u64);
impl OsToken { fn slot(self) -> u32 { self.0 } fn generation(self) -> u64 { self.1 } }
struct ForkChildOwner { number: i32, mm: NonNull<()> }
struct Entry {
    cleanup: Exchange, owner_slot: i32, owner_generation: u64, scheduled: bool,
    closed: bool, needs_cleanup: bool, quarantined: bool, prepare: Option<()>,
    fork: Option<ChildFork>, syscalls: Mailbox<Memory>,
}
impl Entry { @ENTRY_KEY@ }
@BACKEND_HELPERS@

#[repr(C, align(8))]
struct GuestWords(UnsafeCell<[u64; 5]>);
struct Memory { physical: u64, words: Arc<GuestWords>, released: Arc<AtomicUsize> }
unsafe impl ResponseMemory for Memory {
    fn physical(&self) -> u64 { self.physical }
    fn address(&mut self) -> *mut u8 { self.words.0.get().cast() }
    unsafe fn release(self) { self.released.fetch_add(1, Ordering::SeqCst); }
}
fn request(root: u64, nonce: u64, response: u64, tid: i32, marker: u64) -> Request {
    let mut bytes = [0u8; 128];
    bytes[8..12].copy_from_slice(&4i32.to_le_bytes());
    bytes[24..28].copy_from_slice(&0i32.to_le_bytes());
    bytes[32..36].copy_from_slice(&100i32.to_le_bytes());
    bytes[48..52].copy_from_slice(&101i32.to_le_bytes());
    bytes[52..56].copy_from_slice(&tid.to_le_bytes());
    bytes[56..64].copy_from_slice(&1u64.to_le_bytes());
    bytes[64..72].copy_from_slice(&56u64.to_le_bytes());
    for (index, value) in [0u64, 0, 0x8000, root, nonce, marker].iter().enumerate() {
        bytes[72 + index*8..80 + index*8].copy_from_slice(&value.to_le_bytes());
    }
    bytes[120..128].copy_from_slice(&response.to_le_bytes());
    Request::decode(&bytes, 1).unwrap()
}
fn admit(mailbox: &mut Mailbox<Memory>, request: Request) -> (Arc<GuestWords>, Arc<AtomicUsize>) {
    let words = Arc::new(GuestWords(UnsafeCell::new([0, 0, 2, 0, 0])));
    let released = Arc::new(AtomicUsize::new(0));
    mailbox.admit(request, |request| Ok(Memory { physical: request.response(), words: words.clone(), released: released.clone() })).unwrap();
    (words, released)
}
fn entry(pid: i32, scheduled: bool) -> Entry {
    Entry { cleanup: Exchange::new(0, 0, pid).unwrap(), owner_slot: 0, owner_generation: 2,
        scheduled, closed: false, needs_cleanup: false, quarantined: false,
        prepare: scheduled.then_some(()), fork: None, syscalls: Mailbox::new().unwrap() }
}
fn child_owner(pid: i32) -> Arc<ForkChildOwner> {
    Arc::new(ForkChildOwner { number: pid, mm: NonNull::new(0x1000usize as *mut ()).unwrap() })
}
fn geometry() -> ForkGeometry { ForkGeometry { start: 0, length: 0x8000, root: 0x9000 } }
fn setup() -> (Vec<Option<Entry>>, Token, Token, u64, u64, Arc<GuestWords>, Arc<AtomicUsize>) {
    let mut parent = entry(100, true);
    let child = entry(123, false);
    let worker = parent.syscalls.open_worker(200).unwrap();
    let (words, released) = admit(&mut parent.syscalls, request(0x9000, 7, 0xa000, 200, FORK_NATIVE_MARKER));
    let (serial, _) = parent.syscalls.reserve(worker).unwrap().unwrap();
    parent.syscalls.copied(worker, serial, true).unwrap();
    let p = parent.key(); let c = child.key();
    (vec![Some(parent), Some(child)], p, c, worker, serial, words, released)
}

#[test]
fn unique_delivered_rejects_queued_copying_kernel_and_returning_without_changing_claim() {
    let mut mailbox = Mailbox::new().unwrap();
    let worker = mailbox.open_worker(200).unwrap();
    let (_, released) = admit(&mut mailbox, request(0x9000, 7, 0xa000, 200, FORK_NATIVE_MARKER));
    assert!(mailbox.unique_delivered(|_| true).unwrap().is_none());
    let (serial, _) = mailbox.reserve(worker).unwrap().unwrap();
    assert!(mailbox.unique_delivered(|_| true).unwrap().is_none());
    mailbox.begin_kernel(worker, serial).unwrap();
    assert!(mailbox.unique_delivered(|_| true).unwrap().is_none());
    assert_eq!(released.load(Ordering::SeqCst), 0);
    mailbox.finish_kernel(worker, serial, |_, _| Ok(0)).unwrap();
    assert!(mailbox.unique_delivered(|_| true).unwrap().is_none());
    mailbox.publish(0, |_| Ok(())).unwrap();
    assert!(mailbox.unique_delivered(|_| true).unwrap().is_none());
    assert_eq!(released.load(Ordering::SeqCst), 1);
}

#[test]
fn reserve_commit_and_real_ret_publication_keep_original_response_claim() {
    let (mut slots, parent, child, worker, serial, words, released) = setup();
    let owner = child_owner(123);
    let token = reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, owner.clone(), geometry()).unwrap();
    assert_eq!(Arc::strong_count(&owner), 2);
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert!(slots[0].as_ref().unwrap().syscalls.unique_delivered(|_| true).unwrap().is_some());
    assert_eq!(authorize_fork_return(&slots, parent, worker, serial, 0, 123), Err(EBUSY));
    commit_fork_in_slots(&mut slots, child, token).unwrap();
    assert_eq!(commit_fork_in_slots(&mut slots, child, token), Err(EBUSY));
    assert_eq!(authorize_fork_return(&slots, parent, worker, serial, 0, 124), Err(EINVAL));
    authorize_fork_return(&slots, parent, worker, serial, 0, 123).unwrap();
    slots[0].as_mut().unwrap().syscalls.return_value(worker, serial, 0, 123, |_| Ok(())).unwrap();
    record_fork_return(&mut slots, parent, worker, serial, 123);
    assert_eq!(released.load(Ordering::SeqCst), 0);
    assert_eq!(slots[0].as_mut().unwrap().syscalls.publish(0, |_| Err(-11)), Err(-11));
    observe_fork_publication(&mut slots, parent);
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::AdoptedAwaitFirstReturn);
    slots[0].as_mut().unwrap().syscalls.publish(0, |_| Ok(())).unwrap();
    observe_fork_publication(&mut slots, parent);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(unsafe { (*words.0.get())[1] }, 1);
    assert_eq!(unsafe { (*words.0.get())[3] }, 123);
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase(), ForkPhase::FirstReturnPublished);
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.identity.root, 0x9000);
}

#[test]
fn cancellation_before_ret_retains_child_root_and_original_cancel_publication() {
    let (mut slots, parent, child, worker, serial, words, released) = setup();
    let owner = child_owner(123);
    let token = reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, owner.clone(), geometry()).unwrap();
    abort_fork_in_slots(&mut slots, child, token).unwrap();
    assert_eq!(authorize_fork_return(&slots, parent, worker, serial, 0, 123), Err(EBUSY));
    assert_eq!(reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, owner.clone(), geometry()), Err(EBUSY));
    assert_eq!(slots[0].as_mut().unwrap().syscalls.close_worker(worker), Err(-16));
    abort_parent_forks(&mut slots, parent, Some(worker));
    assert_eq!(released.load(Ordering::SeqCst), 0);
    slots[0].as_mut().unwrap().syscalls.publish(0, |_| Ok(())).unwrap();
    observe_fork_publication(&mut slots, parent);
    let record = &slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation;
    assert_eq!(record.state.phase(), ForkPhase::AbortRequested);
    assert!(record.return_published);
    assert_eq!(record.identity.root, 0x9000);
    assert_eq!(record.state.permit_guest_destroy(record.identity), Err(EBUSY));
    assert_eq!(Arc::strong_count(&owner), 2);
    assert_eq!(released.load(Ordering::SeqCst), 1);
    assert_eq!(unsafe { (*words.0.get())[3] } as i64, -512);
}

#[test]
fn mismatch_replay_and_child_capacity_fail_without_publishing() {
    for variant in 0..8 {
        let (mut slots, parent, child, _, _, _, released) = setup();
        let mut g = geometry(); let mut os = OsToken(0,2); let mut pid = 123;
        match variant {
            0 => g.root += 4096, 1 => g.length += 4096, 2 => g.start += 4096,
            3 => os.0 = 1, 4 => os.1 = 3, 5 => pid = 124,
            6 => slots[1].as_mut().unwrap().prepare = Some(()),
            _ => slots[1].as_mut().unwrap().scheduled = true,
        }
        assert!(reserve_fork_in_slots(os, &mut slots, parent, child, child_owner(pid), g).is_err());
        assert!(slots[1].as_ref().unwrap().fork.is_none());
        assert_eq!(released.load(Ordering::SeqCst), 0);
    }
    let (mut slots, parent, child, _, _, _, released) = setup();
    let token = reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, child_owner(123), geometry()).unwrap();
    assert_eq!(commit_fork_in_slots(&mut slots, child, token + 1), Err(EACCES));
    assert_eq!(abort_fork_in_slots(&mut slots, parent, token), Err(ENOENT));
    assert_eq!(reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, child_owner(123), geometry()), Err(EBUSY));
    assert_eq!(slots[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.token.wire(), token);
    assert_eq!(released.load(Ordering::SeqCst), 0);
}

#[test]
fn ambiguous_or_non_native_requests_cannot_authorize_reservation() {
    for (nonce, marker) in [(0, FORK_NATIVE_MARKER), (7, 0)] {
        let mut p = entry(100, true); let c = entry(123, false);
        let worker = p.syscalls.open_worker(200).unwrap();
        admit(&mut p.syscalls, request(0x9000, nonce, 0xa000, 200, marker));
        let (serial, _) = p.syscalls.reserve(worker).unwrap().unwrap();
        p.syscalls.copied(worker, serial, true).unwrap();
        let parent = p.key(); let child = c.key(); let mut slots = vec![Some(p),Some(c)];
        assert_eq!(reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, child_owner(123), geometry()), Err(ENOENT));
        assert!(slots[1].as_ref().unwrap().fork.is_none());
    }
    let mut p = entry(100, true); let c = entry(123, false);
    for (tid, nonce, physical) in [(200,7,0xa000),(201,8,0xb000)] {
        let worker = p.syscalls.open_worker(tid).unwrap();
        admit(&mut p.syscalls, request(0x9000, nonce, physical, tid, FORK_NATIVE_MARKER));
        let (serial, _) = p.syscalls.reserve(worker).unwrap().unwrap();
        p.syscalls.copied(worker, serial, true).unwrap();
    }
    let parent = p.key(); let child = c.key(); let mut slots = vec![Some(p),Some(c)];
    assert_eq!(reserve_fork_in_slots(OsToken(0,2), &mut slots, parent, child, child_owner(123), geometry()), Err(EBUSY));
    assert!(slots[1].as_ref().unwrap().fork.is_none());
}
