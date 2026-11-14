#![feature(arbitrary_self_types)]
// SPDX-License-Identifier: GPL-2.0
// Actual RPC, request/response, mailbox and fork reservation decisions.
// Vec allocation, Linux child PID/MM and OS identity are explicit adapters.
#![allow(dead_code)]
extern crate self as kernel;
use std::{ptr::NonNull, sync::{atomic::{AtomicBool, AtomicUsize, AtomicI32, Ordering}}};
type Result<T = ()> = std::result::Result<T, i32>;
const EINVAL: i32 = -22; const EACCES: i32 = -13; const EBUSY: i32 = -16;
const EAGAIN: i32 = -11; const ENOENT: i32 = -2; const EOVERFLOW: i32 = -75;
fn errno(code: i32) -> i32 { code }
trait ToErrno { fn to_errno(self) -> i32; }
impl ToErrno for i32 { fn to_errno(self) -> i32 { self } }

macro_rules! pr_err { ($($args:tt)*) => { let _ = format_args!($($args)*); } }
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
mod application_rpc{// SPDX-License-Identifier: GPL-2.0
//! Traditional SCD application exchange, adapted from the existing Rust RPC owner.
//!
//! A registration reserves its descriptor before publication. Caller departure
//! cannot retire queued/published work. Unscheduled prepared cleanup retains
//! its owner through both acknowledgement and the matching deletion event.

use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const PACKET_BYTES: usize = 128;
pub(crate) const PREPARE: i32 = 1;
pub(crate) const PREPARE_REPLY: i32 = 2;
pub(crate) const SCHEDULE: i32 = 3;
pub(crate) const CLEANUP: i32 = 9;
pub(crate) const CLEANUP_REPLY: i32 = 10;
pub(crate) const TID_DELETE: i32 = 0x45;
const PROCFS_ANSWER: i32 = 0x13;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Token(u64);

impl Token {
    pub(crate) fn allocate() -> Result<Self, i32> {
        NEXT_TOKEN
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                (value < i64::MAX as u64).then(|| value + 1)
            })
            .map(Self)
            .map_err(|_| -75)
    }

    pub(crate) fn wire(self) -> u64 {
        self.0
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Reserved,
    Queued,
    Published,
    Complete(i32),
}

pub(crate) struct Exchange {
    token: Token,
    os: i32,
    cpu: i32,
    pid: i32,
    message: i32,
    reply: i32,
    argument: u64,
    phase: Phase,
    waiter: bool,
    unscheduled_deleted: bool,
    retirement_query: bool,
}

impl Exchange {
    pub(crate) fn new(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        if pid <= 0 {
            return Err(-22);
        }
        Self::reserve(os, cpu, pid)
    }

    fn reserve(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        if os < 0 || cpu < 0 || pid < 0 {
            return Err(-22);
        }
        let token = Token::allocate()?;
        Ok(Self {
            token,
            os,
            cpu,
            pid,
            message: CLEANUP,
            reply: CLEANUP_REPLY,
            argument: 0,
            phase: Phase::Reserved,
            waiter: true,
            unscheduled_deleted: false,
            retirement_query: false,
        })
    }

    /// The caller must retain the descriptor and its pointed-to physical
    /// allocations from publication until the matching prepare acknowledgement.
    pub(crate) fn prepare(os: i32, cpu: i32, pid: i32, descriptor: u64) -> Result<Self, i32> {
        if descriptor == 0 || descriptor % 4096 != 0 {
            return Err(-22);
        }
        let mut exchange = Self::new(os, cpu, pid)?;
        exchange.message = PREPARE;
        exchange.reply = PREPARE_REPLY;
        exchange.argument = descriptor;
        Ok(exchange)
    }

    /// Read-only native PID-hash query. Ordinary cleanup ACKs cannot satisfy it.
    pub(crate) fn retirement(os: i32, cpu: i32, pid: i32) -> Result<Self, i32> {
        let mut exchange = Self::new(os, cpu, pid)?;
        exchange.retirement_query = true;
        Ok(exchange)
    }

    /// SCHEDULE has no reply; publication transfers the prepared thread owner.
    pub(crate) fn schedule(os: i32, cpu: i32, pid: i32, thread: u64) -> Result<Self, i32> {
        let mut exchange = Self::new(os, cpu, pid)?;
        exchange.cleanup_target(cpu, thread)?;
        if thread == 0 {
            return Err(-22);
        }
        exchange.message = SCHEDULE;
        Ok(exchange)
    }

    /// The owner retains the 808-byte request, host data pages, and exact OS
    /// generation until a matching native reply proves guest mapping retirement.
    /// Caller departure or an unmarked legacy answer cannot release these pages.
    pub(crate) fn procfs(
        os: i32,
        cpu: i32,
        pid: i32,
        descriptor: u64,
        release: bool,
    ) -> Result<Self, i32> {
        const PROCFS_REQUEST: i32 = 0x12;
        const PROCFS_RELEASE: i32 = 0x15;
        if descriptor == 0 || descriptor % 4096 != 0 {
            return Err(-22);
        }
        let mut exchange = Self::reserve(os, cpu, pid)?;
        exchange.message = if release {
            PROCFS_RELEASE
        } else {
            PROCFS_REQUEST
        };
        exchange.reply = PROCFS_ANSWER;
        exchange.argument = descriptor;
        Ok(exchange)
    }

    /// Refine the reserved cleanup target only after a checked prepare reply.
    /// It must use the same guest CPU queue as preparation and scheduling.
    pub(crate) fn cleanup_target(&mut self, cpu: i32, thread: u64) -> Result<(), i32> {
        if !self.reserved() || self.message != CLEANUP || self.retirement_query {
            return Err(-16);
        }
        if cpu < 0 || thread != 0 && thread < 0xffff_8000_0000_0000 {
            return Err(-22);
        }
        self.cpu = cpu;
        self.argument = thread;
        Ok(())
    }

    pub(crate) fn cpu(&self) -> i32 {
        self.cpu
    }

    pub(crate) fn token(&self) -> Token {
        self.token
    }
    pub(crate) fn pid(&self) -> i32 {
        self.pid
    }
    pub(crate) fn reserved(&self) -> bool {
        self.phase == Phase::Reserved
    }
    pub(crate) fn queued(&self) -> bool {
        self.phase == Phase::Queued
    }
    pub(crate) fn abandoned(&self) -> bool {
        !self.waiter
    }

    pub(crate) fn begin(&mut self) -> Result<(), i32> {
        if !self.reserved() {
            return Err(-16);
        }
        self.phase = Phase::Queued;
        Ok(())
    }

    pub(crate) fn outgoing(&self) -> Option<[u8; PACKET_BYTES]> {
        if !self.queued() {
            return None;
        }
        let mut packet = [0; PACKET_BYTES];
        packet[8..12].copy_from_slice(&self.message.to_le_bytes());
        // Traditional reply is at 16; offset 24 belongs to its CPU reference.
        packet[16..24].copy_from_slice(&self.token.wire().to_le_bytes());
        packet[24..28].copy_from_slice(&self.cpu.to_le_bytes());
        packet[28..32].copy_from_slice(&self.os.to_le_bytes());
        packet[32..36].copy_from_slice(&self.pid.to_le_bytes());
        packet[40..48].copy_from_slice(&self.argument.to_le_bytes());
        if self.retirement_query {
            packet[120..128].copy_from_slice(b"MCRQ0001");
        }
        Some(packet)
    }

    pub(crate) fn published(&mut self) -> Result<(), i32> {
        if !self.queued() {
            return Err(-16);
        }
        self.phase = if self.message == SCHEDULE {
            Phase::Complete(0)
        } else {
            Phase::Published
        };
        Ok(())
    }

    pub(crate) fn accept(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let token = u64::from_le_bytes(packet[16..24].try_into().unwrap());
        let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
        let argument = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        if token != self.token.wire()
            || message != self.reply
            || cpu != self.cpu
            || argument != self.argument
        {
            return Err(-2);
        }
        if self.reply == PROCFS_ANSWER
            && (i32::from_le_bytes(packet[32..36].try_into().unwrap()) != self.pid
                || &packet[120..128] != b"MCPR0001")
        {
            return Err(-2);
        }
        if self.retirement_query
            && (i32::from_le_bytes(packet[28..32].try_into().unwrap()) != self.os
                || i32::from_le_bytes(packet[32..36].try_into().unwrap()) != self.pid
                || &packet[120..128] != b"MCRE0001")
        {
            return Err(-2);
        }
        if self.phase != Phase::Published {
            return Err(-16);
        }
        let error = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        self.phase = Phase::Complete(if (-4095..=0).contains(&error) {
            error
        } else {
            -71
        });
        Ok(())
    }

    pub(crate) fn result(&self) -> Option<i32> {
        if let Phase::Complete(error) = self.phase {
            Some(error)
        } else {
            None
        }
    }

    /// A prepared, unscheduled thread emits an advisory procfs deletion with
    /// TID zero after its cleanup reply. Its resp_pa is an expired peer-stack
    /// address, not a reply target. Never map or write it for this operation.
    pub(crate) fn accept_unscheduled_delete(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
        let os = i32::from_le_bytes(packet[28..32].try_into().unwrap());
        let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
        let tid = u64::from_le_bytes(packet[40..48].try_into().unwrap());
        if self.message != CLEANUP
            || self.argument == 0
            || message != TID_DELETE
            || cpu != self.cpu
            || os != self.os
            || pid != self.pid
            || tid != 0
        {
            return Err(-2);
        }
        if self.result().is_none() || self.unscheduled_deleted {
            return Err(-16);
        }
        self.unscheduled_deleted = true;
        Ok(())
    }

    /// These wire events allow local exchange release; final guest destruction
    /// still requires the same-CPU handler barrier. Scheduled TIDs need their
    /// full procfs/process lifecycle owner before START is supported.
    pub(crate) fn release_ready(&self) -> bool {
        self.result().is_some()
            && (self.message != CLEANUP || self.argument == 0 || self.unscheduled_deleted)
    }

    pub(crate) fn abandon(&mut self) {
        self.waiter = false;
    }
    pub(crate) fn retired(&self) -> bool {
        self.abandoned() && self.release_ready()
    }
}
}
mod application_syscall{// SPDX-License-Identifier: GPL-2.0
//! Existing syscall wire format, delivery ownership and ordered completion.
//!
//! The native mailbox must supply referenced worker identities, exclusive guest
//! response claims and retained OS/module/page owners. This module supplies no
//! PID registry, memory mapping, scheduler, user-copy or synthetic syscall result.

use super::application_rpc::Token;
use core::{
    marker::PhantomData,
    ptr,
    sync::atomic::{AtomicU64, Ordering},
};

pub(crate) const REQUEST_MESSAGE: i32 = 4;
pub(crate) const WAKE_MESSAGE: i32 = 0x14;
pub(crate) const REQUEST_BYTES: usize = 72;
pub(crate) const RESPONSE_BYTES: usize = 40;
pub(crate) const WAIT_BYTES: usize = 88;
pub(crate) const RETURN_BYTES: usize = 40;

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct Request {
    cpu: i32,
    pid: i32,
    requester: i32,
    target: i32,
    response: u64,
    bytes: [u8; REQUEST_BYTES],
}

impl Request {
    /// The queue consumer supplies the exact OS generation and acquires packet
    /// publication before decoding. The existing producer leaves osnum zero.
    pub(crate) fn decode(packet: &[u8], cpus: usize) -> Result<Self, i32> {
        if packet.len() != 128 {
            return Err(-22);
        }
        let integer = |offset| i32::from_le_bytes(packet[offset..offset + 4].try_into().unwrap());
        let word = |offset| u64::from_le_bytes(packet[offset..offset + 8].try_into().unwrap());
        let cpu = integer(24);
        let pid = integer(32);
        let requester = integer(48);
        let target = integer(52);
        let response = word(120);
        if integer(8) != REQUEST_MESSAGE
            || cpu < 0
            || cpu as usize >= cpus
            || pid <= 0
            || requester <= 0
            || target < 0
            || word(56) != 1
            || response == 0
            || response % 8 != 0
            || response.checked_add(RESPONSE_BYTES as u64).is_none()
        {
            return Err(-22);
        }
        Ok(Self {
            cpu,
            pid,
            requester,
            target,
            response,
            bytes: packet[48..120].try_into().unwrap(),
        })
    }

    pub(crate) fn cpu(&self) -> i32 {
        self.cpu
    }
    pub(crate) fn pid(&self) -> i32 {
        self.pid
    }
    pub(crate) fn requester(&self) -> i32 {
        self.requester
    }
    pub(crate) fn target(&self) -> i32 {
        self.target
    }
    pub(crate) fn response(&self) -> u64 {
        self.response
    }
    pub(crate) fn number(&self) -> u64 {
        u64::from_le_bytes(self.bytes[16..24].try_into().unwrap())
    }

    pub(crate) fn arguments(&self) -> [u64; 6] {
        core::array::from_fn(|index| {
            let offset = 24 + index * 8;
            u64::from_le_bytes(self.bytes[offset..offset + 8].try_into().unwrap())
        })
    }

    /// The selected clear_host_pte bridge delegates nr 11 with address/length.
    /// This checks wire geometry only; the caller must still check its exact
    /// retained Mirror and current MM before any Linux PTE is changed.
    pub(crate) fn invalidation_range(&self) -> Result<(u64, u64), i32> {
        if self.number() != 11 {
            return Err(-22);
        }
        let arguments = self.arguments();
        let (start, bytes) = (arguments[0], arguments[1]);
        let end = start.checked_add(bytes).ok_or(-22)?;
        if bytes == 0 || start % 4096 != 0 || bytes % 4096 != 0 {
            return Err(-22);
        }
        Ok((start, end))
    }

    /// Existing settid/act_gettid exchange: the launcher copies count i32 TIDs
    /// to the exact physical buffer named by the retained guest request.
    pub(crate) fn tid_buffer(&self) -> Result<(u64, u64), i32> {
        let arguments = self.arguments();
        let bytes = arguments[4].checked_mul(4).ok_or(-22)?;
        let physical = arguments[5];
        if self.number() != 186
            || bytes == 0
            || physical == 0
            || physical % 4 != 0
            || physical.checked_add(bytes).is_none()
        {
            return Err(-22);
        }
        Ok((physical, bytes))
    }

    pub(crate) fn authorize_return_copy(&self, destination: u64, bytes: usize) -> Result<(), i32> {
        // Both existing launcher selections copy only act_futex_clock's native
        // timespec through RET. Its guest physical destination is request arg0.
        let target = u64::from_le_bytes(self.bytes[24..32].try_into().unwrap());
        if self.number() != 202 || bytes != 16 || destination != target {
            return Err(-22);
        }
        Ok(())
    }

    /// Exactly the two fields copied by mcexec_wait_syscall. The trailing pid
    /// field is not written by the original host path and remains untouched.
    pub(crate) fn wait_output(&self) -> [u8; 80] {
        let mut bytes = [0; 80];
        bytes[..8].copy_from_slice(&(self.cpu as u64).to_le_bytes());
        bytes[8..].copy_from_slice(&self.bytes);
        bytes[16..24].fill(0); // The host acknowledges its private packet copy.
        bytes
    }

    fn wake(&self) -> [u8; 128] {
        let mut packet = [0; 128];
        packet[8..12].copy_from_slice(&WAKE_MESSAGE.to_le_bytes());
        // WAKE uses the union's ttid member, not traditional.pid or req.ttid.
        packet[24..28].copy_from_slice(&self.requester.to_le_bytes());
        packet
    }
}

/// A private, never-reused worker token must remain attached to the referenced
/// Linux TID/MM owner. A numeric TID supplied by userspace is not this identity.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Worker {
    identity: Token,
    tid: i32,
}

impl Worker {
    pub(crate) fn new(tid: i32) -> Result<Self, i32> {
        if tid <= 0 {
            return Err(-22);
        }
        Ok(Self {
            identity: Token::allocate()?,
            tid,
        })
    }

    pub(crate) fn wire(self) -> u64 {
        self.identity.wire()
    }

    pub(crate) fn tid(self) -> i32 {
        self.tid
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Queued,
    Copying(Worker),
    Delivered(Worker),
    Returning(Worker),
    Servicing,
    Cancelling,
    Complete,
}

/// State is held under the future mailbox's short mutex. A failed copyout
/// returns the original request to the queue without releasing its response.
pub(crate) struct Delivery {
    serial: Token,
    request: Request,
    phase: Phase,
}

impl Delivery {
    pub(crate) fn new(request: Request) -> Result<Self, i32> {
        Ok(Self {
            serial: Token::allocate()?,
            request,
            phase: Phase::Queued,
        })
    }

    pub(crate) fn serial(&self) -> Token {
        self.serial
    }

    pub(crate) fn request(&self) -> &Request {
        &self.request
    }

    pub(crate) fn eligible(&self, worker: Worker) -> bool {
        self.phase == Phase::Queued
            && (self.request.target == 0 || self.request.target == worker.tid)
    }

    pub(crate) fn reserve(&mut self, worker: Worker) -> Result<[u8; 80], i32> {
        if !self.eligible(worker) {
            return Err(-16);
        }
        self.phase = Phase::Copying(worker);
        Ok(self.request.wait_output())
    }

    pub(crate) fn copied(&mut self, worker: Worker, success: bool) -> Result<(), i32> {
        if self.phase != Phase::Copying(worker) {
            return Err(-16);
        }
        self.phase = if success {
            Phase::Delivered(worker)
        } else {
            Phase::Queued
        };
        Ok(())
    }

    pub(crate) fn check_return(&self, worker: Worker, cpu: i64) -> Result<(), i32> {
        if self.phase != Phase::Delivered(worker) {
            return Err(-16);
        }
        if cpu != self.request.cpu as i64 {
            return Err(-22);
        }
        Ok(())
    }

    pub(crate) fn begin_return(&mut self, worker: Worker, cpu: i64) -> Result<(), i32> {
        self.check_return(worker, cpu)?;
        self.phase = Phase::Returning(worker);
        Ok(())
    }

    /// Call only after actual response status publication, never merely after
    /// putting a wake in a software queue. Queue-full retains Returning.
    pub(crate) fn completed(&mut self, worker: Worker) -> Result<(), i32> {
        if self.phase != Phase::Returning(worker) {
            return Err(-16);
        }
        self.phase = Phase::Complete;
        Ok(())
    }

    pub(crate) fn cancel(&mut self) -> Result<(), i32> {
        if !matches!(
            self.phase,
            Phase::Queued | Phase::Copying(_) | Phase::Delivered(_)
        ) {
            return Err(-16);
        }
        self.phase = Phase::Cancelling;
        Ok(())
    }

    pub(crate) fn cancelled(&mut self) -> Result<(), i32> {
        if self.phase != Phase::Cancelling {
            return Err(-16);
        }
        self.phase = Phase::Complete;
        Ok(())
    }

    pub(crate) fn begin_service(&mut self) -> Result<(), i32> {
        if self.phase != Phase::Queued {
            return Err(-16);
        }
        self.phase = Phase::Servicing;
        Ok(())
    }

    pub(crate) fn serviced(&mut self) -> Result<(), i32> {
        if self.phase != Phase::Servicing {
            return Err(-16);
        }
        self.phase = Phase::Complete;
        Ok(())
    }
}

/// An exclusive retained mapping, owned independently of a mailbox's location.
///
/// # Safety
/// The complete response prefix at address() belongs to physical() in the exact
/// retained OS generation. Its aligned address and exclusive host claim remain
/// valid through final status publication. Only the guest may concurrently
/// change its atomic status/state fields. Unfinished destruction must retain
/// or quarantine the claim and backing owners until peer retirement is proved.
pub(crate) unsafe trait ResponseMemory {
    fn physical(&self) -> u64;
    fn address(&mut self) -> *mut u8;

    /// # Safety
    /// Final response status has been published after any required wake.
    /// Release host bookkeeping/owners only; never access guest memory here.
    unsafe fn release(self);
}

pub(crate) struct Borrowed<'a> {
    address: *mut u8,
    physical: u64,
    _retained: PhantomData<&'a mut [u8; RESPONSE_BYTES]>,
}

// SAFETY: The only constructor is Response::new, whose caller supplies the
// external exclusive mapping/lifetime claim. Dropping this view changes none
// of that external ownership and accesses no peer memory.
unsafe impl ResponseMemory for Borrowed<'_> {
    fn physical(&self) -> u64 {
        self.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.address
    }
    unsafe fn release(self) {}
}

/// No Rust reference to the guest's mutable byte object is created. The Request
/// is copied so the retained capability can move between native worker queues.
pub(crate) struct Response<M: ResponseMemory> {
    memory: M,
    request: Request,
}

impl<M: ResponseMemory> Response<M> {
    /// The mailbox exclusively retains this response before completion starts.
    /// Native memory adapters may attach independently authorized payload claims;
    /// the original response address and its ownership must remain unchanged.
    pub(crate) fn memory_mut(&mut self) -> &mut M {
        &mut self.memory
    }
    // BEGIN PRIVATE FORK RESPONSE RECONCILIATION
    /// Check the original still-exclusive response before any MM effect.
    pub(crate) fn check_fork_unpublished(&mut self, expected: &Request) -> Result<(), i32> {
        if &self.request != expected { return Err(-13); }
        let address = self.memory.address();
        // SAFETY: Response retains its constructor-validated exclusive mapping.
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(-16);
        }
        Ok(())
    }
    // END PRIVATE FORK RESPONSE RECONCILIATION

}

impl<'a> Response<Borrowed<'a>> {
    /// # Safety
    /// address maps this request's entire response prefix in its exact retained
    /// OS generation. The original pages/module and an exclusive host mapping
    /// claim outlive 'a. Only the guest may concurrently change status/requester
    /// state using aligned atomic accesses. No other host responder may access
    /// this span. Reject aliases before constructing this capability.
    pub(crate) unsafe fn new(request: &'a Request, address: *mut u8) -> Result<Self, i32> {
        Self::from_memory(
            request,
            Borrowed {
                address,
                physical: request.response(),
                _retained: PhantomData,
            },
        )
    }
}

impl<M: ResponseMemory> Response<M> {
    pub(crate) fn from_memory(request: &Request, mut memory: M) -> Result<Self, i32> {
        let address = memory.address();
        if address.is_null()
            || address as usize % 8 != 0
            || (address as usize).checked_add(RESPONSE_BYTES).is_none()
            || memory.physical() != request.response()
        {
            return Err(-22);
        }
        Ok(Self {
            memory,
            request: request.clone(),
        })
    }

    /// Claim the guest's wake state exactly once. On a protocol error the outer
    /// owner must retain/quarantine the mapping, never fabricate completion.
    pub(crate) fn prepare(mut self, servicing_tid: i32, value: i64) -> Result<Completion<M>, i32> {
        // Original host cancellation and in-kernel services use stid zero.
        if servicing_tid < 0 {
            return Err(-22);
        }
        // SAFETY: The constructor's exclusive response claim and retained
        // mapping cover all these aligned fields for this complete operation.
        let address = self.memory.address();
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        // SAFETY: The same exclusive retained response mapping contains the
        // independently aligned state word at byte offset 16 for this operation.
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(-71);
        }
        // Preserve ttid, fault_address, the guest-only pde_data and all guards.
        // SAFETY: The exclusive response claim keeps these two aligned writable
        // fields live; volatile writes touch only the host-owned protocol words.
        unsafe {
            ptr::write_volatile(address.add(4).cast::<i32>(), servicing_tid);
            ptr::write_volatile(address.add(24).cast::<i64>(), value);
        }
        let wake = match state.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) => None,
            Err(2) => {
                state
                    .compare_exchange(2, 1, Ordering::AcqRel, Ordering::Acquire)
                    .map_err(|_| -71)?;
                Some(self.request.wake())
            }
            Err(_) => return Err(-71),
        };
        Ok(Completion {
            response: Some(self),
            wake,
        })
    }
}

pub(crate) struct Completion<M: ResponseMemory> {
    response: Option<Response<M>>,
    wake: Option<[u8; 128]>,
}

impl<M: ResponseMemory> Completion<M> {
    // BEGIN PRIVATE FORK COMPLETION RECONCILIATION
    /// The caller owns Remote.slots from validation through publication
    /// permission. None validates only; Some(-125) reconciles the already
    /// prepared, UNPUBLISHED original response without preparing it again.
    pub(crate) fn reconcile_fork_unpublished(
        &mut self, expected: &Request, expected_value: i64, replacement: Option<i64>,
    ) -> Result<(), i32> {
        if replacement.is_some_and(|value| value != -125) { return Err(-22); }
        let response = self.response.as_mut().ok_or(-16)?;
        if &response.request != expected { return Err(-13); }
        let address = response.memory.address();
        // SAFETY: The same original Completion exclusively retains this span;
        // no publish can run concurrently through this exclusive borrow.
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || state.load(Ordering::Acquire) != 1
            || unsafe { ptr::read_volatile(address.add(24).cast::<i64>()) } != expected_value
        { return Err(-16); }
        if let Some(value) = replacement {
            // Preserve the exact wake, state1, response and physical claim.
            // Only the host-owned servicing TID and result change. The later
            // original publish supplies its sole status Release and release.
            unsafe {
                ptr::write_volatile(address.add(4).cast::<i32>(), 0);
                ptr::write_volatile(address.add(24).cast::<i64>(), value);
            }
        }
        Ok(())
    }
    // END PRIVATE FORK COMPLETION RECONCILIATION

    /// send must mean real queue publication; an error must mean no packet was
    /// published. The caller notifies the guest after successful publication.
    /// Full queues retain the same wake, response and result for retry.
    pub(crate) fn publish(
        &mut self,
        send: impl FnOnce(&[u8; 128]) -> Result<(), i32>,
    ) -> Result<(), i32> {
        if self.response.is_none() {
            return Err(-16);
        }
        if let Some(packet) = &self.wake {
            send(packet)?;
        }
        let mut response = self.response.take().unwrap();
        let address = response.memory.address();
        // SAFETY: The mapping claim is retained until this final release store.
        // The guest can retire the response immediately after it sees status=1;
        // no method, retry or destructor accesses that address afterwards.
        unsafe {
            AtomicU64::from_ptr(address.add(8).cast()).store(1, Ordering::Release);
            response.memory.release();
        }
        Ok(())
    }
}
}
mod smp_application_syscall{// SPDX-License-Identifier: GPL-2.0
//! Owned bounded mailbox within one existing application registration.

use super::{
    application_rpc::Token,
    application_syscall::{Completion, Delivery, Request, Response, ResponseMemory, Worker},
};
use kernel::prelude::{Vec, VecExt, GFP_KERNEL};

type Result<T = ()> = core::result::Result<T, i32>;
pub(crate) const CAPACITY: usize = 64;

pub(crate) fn cyclic(start: usize, capacity: usize) -> impl Iterator<Item = usize> {
    (0..capacity).map(move |offset| (start % capacity + offset) % capacity)
}

struct WorkerState {
    worker: Worker,
    delivery: Option<Token>,
    completed: Option<Token>,
}

struct Call<M: ResponseMemory> {
    delivery: Delivery,
    response: Option<Response<M>>,
    completion: Option<Completion<M>>,
    worker: Option<Worker>,
    cancelled: bool,
    kernel: bool,
    fork_ingress_pending: bool,
    service: bool,
    transferred: bool,
    publication_since: Option<u64>,
}

pub(crate) struct Mailbox<M: ResponseMemory> {
    calls: Vec<Option<Call<M>>>,
    workers: Vec<Option<WorkerState>>,
    closed: bool,
    quarantined: bool,
    completion_cursor: usize,
}

/// Owns the SAME unpublished response while the IHK-pinned payload constructor
/// runs outside Remote.slots. It is never a copied Request granting memory.
#[must_use = "restore the exact response before ending the ingress freeze"]
pub(crate) struct ForkIngressResponse<M: ResponseMemory> {
    response: Option<Response<M>>,
    request: Request,
    worker: u64,
    serial: u64,
}
impl<M: ResponseMemory> ForkIngressResponse<M> {
    pub(crate) fn request(&self) -> &Request { &self.request }
    pub(crate) fn response(&mut self) -> Result<&mut Response<M>> { self.response.as_mut().ok_or(-71) }
}
impl<M: ResponseMemory> Drop for ForkIngressResponse<M> {
    fn drop(&mut self) {
        // An exceptional lost ticket cannot unmap the original response while
        // the call still names it. The real scoped provider must retain its
        // independent IHK owner and publication freeze on this uncertainty.
        if let Some(response) = self.response.take() { core::mem::forget(response); }
    }
}

impl<M: ResponseMemory> Mailbox<M> {
    pub(crate) fn new() -> Result<Self> {
        // The pinned kernel maps its payload-free AllocError to ENOMEM.
        let mut calls = Vec::with_capacity(CAPACITY, GFP_KERNEL).map_err(|_| -12)?;
        let mut workers = Vec::with_capacity(CAPACITY, GFP_KERNEL).map_err(|_| -12)?;
        for _ in 0..CAPACITY {
            calls.push(None, GFP_KERNEL).map_err(|_| -12)?;
            workers.push(None, GFP_KERNEL).map_err(|_| -12)?;
        }
        Ok(Self {
            calls,
            workers,
            closed: false,
            quarantined: false,
            completion_cursor: 0,
        })
    }

    pub(crate) fn open_worker(&mut self, tid: i32) -> Result<u64> {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        // Only the referenced Linux identity owner can retire the old record.
        // Reusing a numeric TID cannot bind to its old opaque worker token.
        if self
            .workers
            .iter()
            .flatten()
            .any(|state| state.worker.tid() == tid)
        {
            return Err(-16);
        }
        let slot = self
            .workers
            .iter_mut()
            .find(|slot| slot.is_none())
            .ok_or(-11)?;
        let worker = Worker::new(tid)?;
        let handle = worker.wire();
        *slot = Some(WorkerState {
            worker,
            delivery: None,
            completed: None,
        });
        Ok(handle)
    }

    pub(crate) fn close_worker(&mut self, handle: u64) -> Result {
        if self.quarantined {
            return Err(-71);
        }
        let slot = self
            .workers
            .iter_mut()
            .find(|slot| {
                slot.as_ref()
                    .is_some_and(|state| state.worker.wire() == handle)
            })
            .ok_or(-2)?;
        if let Some(serial) = slot.as_ref().unwrap().delivery {
            let call = self
                .calls
                .iter_mut()
                .flatten()
                .find(|call| call.delivery.serial() == serial)
                .ok_or(-71)?;
            if let Err(error) = Self::cancel_call(call) {
                self.quarantined = true;
                return Err(error);
            }
            // The Linux PID/MM owner retries retirement after publication;
            // numeric TID reuse remains excluded until then.
            return Err(-16);
        }
        *slot = None;
        Ok(())
    }

    /// The caller serializes admission with scheduling and process close.
    /// Capacity failure occurs before taking a response claim, allowing retry
    /// of the same retained transport packet without a second host responder.
    pub(crate) fn admit(
        &mut self,
        request: Request,
        claim: impl FnOnce(&Request) -> Result<M>,
    ) -> Result<bool> {
        self.admit_inner(request, claim, None::<fn(&Request) -> i64>)
    }

    /// Only continuing-service operations that require no caller file table.
    /// The effect runs once, after a response claim, and survives process close.
    pub(crate) fn admit_serviced(
        &mut self,
        request: Request,
        claim: impl FnOnce(&Request) -> Result<M>,
        service: impl FnOnce(&Request) -> i64,
    ) -> Result<bool> {
        self.admit_inner(request, claim, Some(service))
    }

    fn admit_inner(
        &mut self,
        request: Request,
        claim: impl FnOnce(&Request) -> Result<M>,
        service: Option<impl FnOnce(&Request) -> i64>,
    ) -> Result<bool> {
        if self.quarantined {
            return Err(-71);
        }
        if self
            .calls
            .iter()
            .flatten()
            .any(|call| call.delivery.request() == &request)
        {
            return Ok(false);
        }
        if self
            .calls
            .iter()
            .flatten()
            .any(|call| call.delivery.request().response() == request.response())
        {
            return Err(-71);
        }
        let slot = self
            .calls
            .iter_mut()
            .find(|slot| slot.is_none())
            .ok_or(-11)?;
        let delivery = Delivery::new(request)?;
        let memory = claim(delivery.request())?;
        let response = match Response::from_memory(delivery.request(), memory) {
            Ok(response) => response,
            Err(error) => {
                self.quarantined = true;
                return Err(error);
            }
        };
        let mut call = Call {
            delivery,
            response: Some(response),
            completion: None,
            worker: None,
            cancelled: false,
            kernel: false,
            service: false,
            transferred: false,
            fork_ingress_pending: false,
            publication_since: None,
        };
        if let Some(service) = service {
            call.delivery.begin_service()?;
            let value = service(call.delivery.request());
            match call.response.take().ok_or(-71)?.prepare(0, value) {
                Ok(completion) => call.completion = Some(completion),
                Err(error) => {
                    self.quarantined = true;
                    return Err(error);
                }
            }
            call.service = true;
        }
        *slot = Some(call);
        if self.closed {
            self.cancel_pending()?;
        }
        Ok(true)
    }

    pub(crate) fn reserve(&mut self, handle: u64) -> Result<Option<(u64, [u8; 80])>> {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        let worker = self
            .workers
            .iter_mut()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if let Some(serial) = worker.delivery {
            if self
                .calls
                .iter()
                .flatten()
                .any(|call| call.delivery.serial() == serial && call.completion.is_some())
            {
                return Ok(None);
            }
            return Err(-16);
        }
        // Preserve targeted priority and arrival order even after a newer
        // request reuses an earlier array slot. Tokens never wrap or repeat.
        let Some(index) = self
            .calls
            .iter()
            .enumerate()
            .filter_map(|(index, slot)| {
                let call = slot.as_ref()?;
                call.delivery
                    .eligible(worker.worker)
                    .then_some((index, call))
            })
            .min_by_key(|(_, call)| {
                (
                    call.delivery.request().target() != worker.worker.tid(),
                    call.delivery.serial().wire(),
                )
            })
            .map(|(index, _)| index)
        else {
            return Ok(None);
        };
        let call = self.calls[index].as_mut().unwrap();
        let bytes = call.delivery.reserve(worker.worker)?;
        worker.delivery = Some(call.delivery.serial());
        call.worker = Some(worker.worker);
        Ok(Some((call.delivery.serial().wire(), bytes)))
    }

    pub(crate) fn copied(&mut self, handle: u64, serial: u64, success: bool) -> Result {
        if self.quarantined {
            return Err(-71);
        }
        let worker = self
            .workers
            .iter_mut()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) {
            return Err(-16);
        }
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        call.delivery.copied(worker.worker, success)?;
        if !success {
            worker.delivery = None;
            call.worker = None;
        }
        Ok(())
    }

    /// Copy a running settid payload while the caller holds the application
    /// mutex. The callback uses only kernel bytes and retains its payload claim
    /// in the response until the ordinary launcher RET is actually published.
    pub(crate) fn transfer_tids(
        &mut self,
        handle: u64,
        serial: u64,
        physical: u64,
        bytes: &mut [u8],
        direction: u64,
        copy: impl FnOnce(&Request, &mut M, &mut [u8]) -> Result,
    ) -> Result {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        let worker = self
            .workers
            .iter()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) {
            return Err(-16);
        }
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        if call.kernel
            || call.service
            || call.cancelled
            || call.transferred
            || call.completion.is_some()
        {
            return Err(-16);
        }
        let request = call.delivery.request();
        call.delivery
            .check_return(worker.worker, request.cpu() as i64)?;
        if direction != 0 || request.tid_buffer()? != (physical, bytes.len() as u64) {
            return Err(-22);
        }
        copy(
            request,
            call.response.as_mut().ok_or(-71)?.memory_mut(),
            bytes,
        )?;
        call.transferred = true;
        Ok(())
    }

    /// Convert the exact reserved WAIT delivery into in-kernel work. Close
    /// cannot complete or reuse its response while that work accesses memory.
    pub(crate) fn begin_kernel(&mut self, handle: u64, serial: u64) -> Result<Request> {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        self.copied(handle, serial, true)?;
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        call.kernel = true;
        Ok(call.delivery.request().clone())
    }

    pub(crate) fn begin_invalidation(&mut self, handle: u64, serial: u64) -> Result<(u64, u64)> {
        let range = self
            .calls
            .iter()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?
            .delivery
            .request()
            .invalidation_range()?;
        self.begin_kernel(handle, serial)?;
        Ok(range)
    }

    /// This result comes only from the retained worker's completed Mirror
    /// operation. A close during that operation defers its cancellation here.
    pub(crate) fn finish_invalidation(
        &mut self,
        handle: u64,
        serial: u64,
        value: i64,
    ) -> Result<i64> {
        if !(-4095..=0).contains(&value) {
            return Err(-22);
        }
        self.calls
            .iter()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?
            .delivery
            .request()
            .invalidation_range()?;
        let mut completed = -512;
        self.finish_kernel(handle, serial, |_, _| {
            completed = value;
            Ok(value)
        })?;
        Ok(completed)
    }

    pub(crate) fn with_kernel_memory<T>(
        &mut self,
        handle: u64,
        serial: u64,
        use_memory: impl FnOnce(&Request, &mut M) -> Result<T>,
    ) -> Result<T> {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        let worker = call.worker.ok_or(-71)?;
        if !call.kernel || call.cancelled || worker.wire() != handle || call.completion.is_some() {
            return Err(-16);
        }
        use_memory(
            call.delivery.request(),
            call.response.as_mut().ok_or(-71)?.memory_mut(),
        )
    }

    pub(crate) fn finish_kernel(
        &mut self,
        handle: u64,
        serial: u64,
        result: impl FnOnce(&Request, &mut M) -> Result<i64>,
    ) -> Result {
        if self.quarantined {
            return Err(-71);
        }
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        let worker = call.worker.ok_or(-71)?;
        if !call.kernel || worker.wire() != handle || call.completion.is_some() {
            return Err(-16);
        }
        call.kernel = false;
        if self.closed || call.cancelled {
            return Self::cancel_call(call);
        }
        let value = result(
            call.delivery.request(),
            call.response.as_mut().ok_or(-71)?.memory_mut(),
        )
        .unwrap_or_else(|error| error as i64);
        call.delivery
            .begin_return(worker, call.delivery.request().cpu() as i64)?;
        match call.response.take().ok_or(-71)?.prepare(0, value) {
            Ok(completion) => call.completion = Some(completion),
            Err(error) => {
                self.quarantined = true;
                return Err(error);
            }
        }
        Ok(())
    }

    pub(crate) fn return_value(
        &mut self,
        handle: u64,
        serial: u64,
        cpu: i64,
        value: i64,
        copy: impl FnOnce(&Request) -> Result,
    ) -> Result {
        if self.closed || self.quarantined {
            return Err(-32);
        }
        let worker = self
            .workers
            .iter()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) {
            return Err(-16);
        }
        let call = self
            .calls
            .iter_mut()
            .flatten()
            .find(|call| call.delivery.serial().wire() == serial)
            .ok_or(-2)?;
        if call.kernel || call.fork_ingress_pending {
            return Err(-16);
        }
        call.delivery.check_return(worker.worker, cpu)?;
        let request = call.delivery.request();
        if value == 0 && request.number() == 186 && request.arguments()[4] != 0 {
            request.tid_buffer()?;
            if !call.transferred {
                return Err(-22);
            }
        }
        // Only an already copied kernel buffer is used here, never user access.
        // Failed validation/copy leaves Delivered available for a proper retry.
        copy(call.delivery.request())?;
        call.delivery.begin_return(worker.worker, cpu)?;
        let response = call.response.take().ok_or(-71)?;
        match response.prepare(worker.worker.tid(), value) {
            Ok(completion) => call.completion = Some(completion),
            Err(error) => {
                self.quarantined = true;
                return Err(error);
            }
        }
        Ok(())
    }

    // BEGIN PRIVATE FORK MAILBOX RECONCILIATION
    /// Full Request equality binds OS/body/response/nonce in addition to the
    /// actual retained worker and delivery. No caller geometry grants access.
    fn fork_abort_call(&mut self, handle: u64, serial: u64, expected: &Request) -> Result<&mut Call<M>> {
        if self.quarantined { return Err(-71); }
        let worker = self.workers.iter().flatten().find(|worker| worker.worker.wire() == handle).ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) { return Err(-16); }
        let call = self.calls.iter_mut().flatten().find(|call| call.delivery.serial().wire() == serial).ok_or(-2)?;
        if call.delivery.request() != expected || call.worker != Some(worker.worker)
            || call.kernel || call.service || expected.number() != 56
        { return Err(-13); }
        Ok(call)
    }
    pub(crate) fn check_fork_abort(&mut self, handle: u64, serial: u64,
        expected: &Request, expected_value: Option<i64>) -> Result
    {
        let call = self.fork_abort_call(handle, serial, expected)?;
        if let Some(completion) = &mut call.completion {
            let old = expected_value.unwrap_or(-512);
            if expected_value.is_none() && !call.cancelled { return Err(-71); }
            completion.reconcile_fork_unpublished(expected, old, None)
        } else {
            if expected_value.is_some() { return Err(-71); }
            call.response.as_mut().ok_or(-16)?.check_fork_unpublished(expected)
        }
    }
    pub(crate) fn reconcile_fork_abort(&mut self, handle: u64, serial: u64,
        expected: &Request, expected_value: Option<i64>) -> Result
    {
        self.check_fork_abort(handle, serial, expected, expected_value)?;
        let call = self.fork_abort_call(handle, serial, expected)?;
        if let Some(completion) = &mut call.completion {
            completion.reconcile_fork_unpublished(expected, expected_value.unwrap_or(-512), Some(-125))?;
            // Preserve Returning versus Cancelling. In particular never mark
            // an existing Returning completion cancelled after rewriting it.
        } else {
            call.delivery.cancel()?;
            let response = call.response.take().ok_or(-71)?;
            call.completion = Some(response.prepare(0, -125)?);
            call.cancelled = true;
        }
        Ok(())
    }
    // END PRIVATE FORK MAILBOX RECONCILIATION

    // BEGIN PRIVATE FORK INGRESS RESPONSE TICKET
    /// Caller first reserves a real provisional parent-publication hold under
    /// Remote.slots. The exact response is then moved, never duplicated. This
    /// separate gate preserves ordinary user delivery/origin semantics.
    pub(crate) fn take_fork_ingress_response(&mut self, handle: u64, serial: u64,
        expected: &Request) -> Result<ForkIngressResponse<M>>
    {
        if self.closed || self.quarantined { return Err(-32); }
        let call = self.fork_abort_call(handle, serial, expected)?;
        if call.cancelled || call.fork_ingress_pending || call.completion.is_some() { return Err(-16); }
        let worker = call.worker.ok_or(-71)?;
        call.delivery.check_return(worker, expected.cpu() as i64)?;
        call.response.as_mut().ok_or(-16)?.check_fork_unpublished(expected)?;
        let response = call.response.take().ok_or(-71)?;
        call.fork_ingress_pending = true;
        Ok(ForkIngressResponse { response: Some(response), request: expected.clone(), worker: handle, serial })
    }

    /// Restore before the caller removes its publication hold. A close while
    /// construction ran may mark cancellation, but cannot consume the ticket.
    pub(crate) fn restore_fork_ingress_response(&mut self, ticket: &mut ForkIngressResponse<M>) -> Result {
        let closed = self.closed;
        if self.quarantined { return Err(-71); }
        let call = self.fork_abort_call(ticket.worker, ticket.serial, &ticket.request)?;
        if !call.fork_ingress_pending || call.response.is_some() || call.completion.is_some() { return Err(-16); }
        let response = ticket.response.take().ok_or(-71)?;
        call.response = Some(response);
        call.fork_ingress_pending = false;
        if closed || call.cancelled { Self::cancel_call(call)?; }
        Ok(())
    }
    // END PRIVATE FORK INGRESS RESPONSE TICKET

    /// Freeze-only observer for an authenticated carrier's second clone. It
    /// includes queued and automatically cancelled responses before a link
    /// ticket exists; matching grants no publication or lifecycle authority.
pub(crate) fn has_private_fork_response(&self, cpu: i32, selector: u64,
        matches: impl Fn(&Request) -> bool) -> bool {
        self.calls.iter().flatten().any(|call| {
            let request = call.delivery.request();
            !call.kernel && !call.service && request.number() == 56
                && request.arguments()[0] == selector && request.cpu() == cpu && matches(request)
        })
    }
    pub(crate) fn has_fork_link_response(&self, cpu: i32, matches: impl Fn(&Request) -> bool) -> bool {
        self.calls.iter().flatten().any(|call| {
            let request = call.delivery.request();
            !call.kernel && !call.service && request.number() == 56
                && request.arguments()[0] == 1 && request.cpu() == cpu && matches(request)
        })
    }

    pub(crate) fn returned(&self, handle: u64, serial: u64) -> Result<bool> {
        if self.quarantined {
            return Err(-71);
        }
        let worker = self
            .workers
            .iter()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if worker.completed.map(Token::wire) == Some(serial) {
            return Ok(true);
        }
        if worker.delivery.map(Token::wire) != Some(serial) {
            return Err(-16);
        }
        Ok(false)
    }

    /// Immutable discovery under Remote.slots. The predicate must inspect
    /// local scalar metadata only, with no external calls or reentrancy. A
    /// copied Request confers no payload access after this guard is released.
    /// The response claim and ordinary RET stay owned by the original Call.
    pub(crate) fn unique_delivered(
        &self,
        matches: impl Fn(&Request) -> bool,
    ) -> Result<Option<(u64, u64, Request)>> {
        if self.closed || self.quarantined { return Err(-32); }
        let mut found = None;
        for call in self.calls.iter().flatten() {
            if call.kernel || call.service || call.cancelled || call.completion.is_some()
                || call.response.is_none() || !matches(call.delivery.request())
            { continue; }
            let Some(worker) = call.worker else { continue; };
            let serial = call.delivery.serial();
            if !self.workers.iter().flatten().any(|state| {
                state.worker == worker && state.delivery == Some(serial)
            }) || call.delivery.check_return(worker, call.delivery.request().cpu() as i64).is_err()
            { continue; }
            if found.is_some() { return Err(-16); }
            found = Some((worker.wire(), serial.wire(), call.delivery.request().clone()));
        }
        Ok(found)
    }

    pub(crate) fn queued_cpu(&self) -> Option<i32> {
        if self.quarantined {
            return None;
        }
        self.next_completion(None)
            .map(|index| self.calls[index].as_ref().unwrap().delivery.request().cpu())
    }

    fn next_completion(&self, cpu: Option<i32>) -> Option<usize> {
        cyclic(self.completion_cursor, self.calls.len()).find(|&index| {
            self.calls[index].as_ref().is_some_and(|call| {
                call.completion.is_some()
                    && cpu.is_none_or(|cpu| call.delivery.request().cpu() == cpu)
            })
        })
    }

    /// Queue publication and final status happen under the outer application's
    /// short mutex. The caller notifies the guest and Linux waiters afterwards.
    pub(crate) fn publish(
        &mut self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        if self.quarantined {
            return Err(-71);
        }
        let Some(index) = self.next_completion(Some(cpu)) else {
            return Ok(false);
        };
        self.completion_cursor = (index + 1) % self.calls.len();
        let slot = &mut self.calls[index];
        let call = slot.as_mut().unwrap();
        call.completion.as_mut().unwrap().publish(send)?;
        if call.service {
            call.delivery.serviced()?;
        } else if call.cancelled {
            call.delivery.cancelled()?;
        } else {
            call.delivery.completed(call.worker.ok_or(-71)?)?;
        }
        if let Some(owner) = call.worker {
            let worker = self
                .workers
                .iter_mut()
                .flatten()
                .find(|state| state.worker == owner)
                .ok_or(-71)?;
            if worker.delivery != Some(call.delivery.serial()) {
                return Err(-71);
            }
            worker.delivery = None;
            worker.completed = Some(call.delivery.serial());
        }
        *slot = None;
        Ok(true)
    }

    pub(crate) fn close(&mut self) -> Result {
        if self.quarantined {
            return Err(-71);
        }
        self.closed = true;
        self.cancel_pending()
    }

    /// A failed transport cannot acknowledge or cancel an unfinished response.
    /// Retain every call and its exact memory claim; in-flight kernel work may
    /// finish its independent I/O, but may no longer copy or publish peer data.
    pub(crate) fn quarantine(&mut self) {
        self.closed = true;
        self.quarantined = true;
    }

    /// The independent packet owner supplies CLOCK_MONOTONIC seconds. Each
    /// committed completion has its own deadline, so progress by another call
    /// cannot indefinitely reset a blocked response's publication lifetime.
    pub(crate) fn publication_expired(&mut self, now: u64, timeout: u64) -> bool {
        if self.quarantined {
            return false;
        }
        self.calls.iter_mut().flatten().any(|call| {
            if call.completion.is_none() {
                return false;
            }
            let since = call.publication_since.get_or_insert(now);
            now.saturating_sub(*since) >= timeout
        })
    }

    fn cancel_pending(&mut self) -> Result {
        for call in self.calls.iter_mut().flatten() {
            if let Err(error) = Self::cancel_call(call) {
                self.quarantined = true;
                return Err(error);
            }
        }
        Ok(())
    }

    fn cancel_call(call: &mut Call<M>) -> Result {
        if call.completion.is_some() {
            return Ok(());
        }
        if call.kernel || call.fork_ingress_pending {
            call.cancelled = true;
            return Ok(());
        }
        call.delivery.cancel()?;
        let response = call.response.take().ok_or(-71)?;
        call.completion = Some(response.prepare(0, -512)?);
        call.cancelled = true;
        Ok(())
    }

    pub(crate) fn drained(&self) -> bool {
        !self.quarantined && self.calls.iter().all(Option::is_none)
    }

    pub(crate) fn quarantined(&self) -> bool {
        self.quarantined
    }
}
}
use application_rpc::{Exchange, Token};
use application_syscall::Request;
use smp_application_syscall::Mailbox;
mod smp_application_image{use super::*;
// This first slice supplies the checked transitions only. No connection admits
// an adopted image yet: non-null CREATE_PPD remains rejected. Integration must
// retain referenced Linux PID/MM owners and the real original delivery claim;
// these scalar identities are comparison keys, never standalone authority.
#[allow(dead_code)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkIdentity {
    pub(crate) slot: u32,
    pub(crate) generation: u64,
    pub(crate) parent: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) child: u64,
    pub(crate) child_pid: i32,
    pub(crate) child_mm: usize,
    pub(crate) root: u64,
    pub(crate) start: u64,
    pub(crate) length: u64,
    pub(crate) nonce: u64,
}

#[allow(dead_code)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ForkPhase {
    Reserved,
    AdoptedAwaitFirstReturn,
    FirstReturnPublished,
    GuestLinkObserved,
    Linked,
    AbortRequested,
    HostRevoked,
    GuestDestroyed,
    Released,
    Quarantined,
}

#[allow(dead_code)]
pub(crate) struct ForkAdoption {
    identity: ForkIdentity,
    phase: ForkPhase,
    accesses: u32,
    prepared: bool,
    abort_pending: bool,
    quarantine_pending: bool,
}

#[allow(dead_code)]
impl ForkAdoption {
    pub(crate) fn reserve(identity: ForkIdentity) -> Result<Self> {
        if identity.generation == 0 || identity.parent == 0 || identity.worker == 0
            || identity.delivery == 0 || identity.child == 0 || identity.child == identity.parent
            || identity.child_pid <= 0 || identity.child_mm == 0
            || identity.root == 0 || identity.root % 4096 != 0
            || identity.start % 4096 != 0 || identity.length == 0 || identity.length % 4096 != 0
            || identity.start.checked_add(identity.length).is_none() || identity.nonce == 0
        {
            return Err(EINVAL);
        }
        Ok(Self { identity, phase: ForkPhase::Reserved, accesses: 0,
            prepared: false, abort_pending: false, quarantine_pending: false })
    }

    fn check(&self, identity: ForkIdentity) -> Result {
        if self.identity != identity { return Err(EACCES); }
        Ok(())
    }

    pub(crate) fn phase(&self) -> ForkPhase { self.phase }

    pub(crate) fn prepared(&self) -> bool { self.prepared }

    pub(crate) fn prepare_lease(&mut self) -> Result {
        if self.phase != ForkPhase::Reserved || self.prepared || self.abort_pending {
            return Err(EBUSY);
        }
        self.prepared = true;
        Ok(())
    }

    // Called only after the child MM and local publication locks are released.
    // Cancellation never changes the phase while the exclusive lease is live.
    pub(crate) fn finish_lease(&mut self, identity: ForkIdentity, sealed: bool, completed: bool) -> Result {
        self.check(identity)?;
        if !self.prepared || self.phase != ForkPhase::Reserved { return Err(EBUSY); }
        self.prepared = false;
        self.phase = if self.quarantine_pending || sealed && !completed {
            ForkPhase::Quarantined
        } else if !sealed || self.abort_pending {
            ForkPhase::AbortRequested
        } else {
            ForkPhase::AdoptedAwaitFirstReturn
        };
        Ok(())
    }

    pub(crate) fn adopted(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::Reserved || self.prepared { return Err(EBUSY); }
        self.phase = ForkPhase::AdoptedAwaitFirstReturn;
        Ok(())
    }

    /// Call before publishing the ordinary launcher RET. Wrong positive PIDs
    /// never change the transaction or publish a result for another child.
    pub(crate) fn authorize_first_return(&self, identity: ForkIdentity, value: i64) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::AdoptedAwaitFirstReturn { return Err(EBUSY); }
        if value != identity.child_pid as i64 && !(-4095..0).contains(&value) {
            return Err(EINVAL);
        }
        Ok(())
    }

    pub(crate) fn first_return_published(&mut self, identity: ForkIdentity, value: i64) -> Result {
        self.authorize_first_return(identity, value)?;
        self.phase = if value < 0 { ForkPhase::AbortRequested } else { ForkPhase::FirstReturnPublished };
        Ok(())
    }

    pub(crate) fn observe_link(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::FirstReturnPublished { return Err(EBUSY); }
        self.phase = ForkPhase::GuestLinkObserved;
        Ok(())
    }

    pub(crate) fn second_return_published(&mut self, identity: ForkIdentity, result: i32) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::GuestLinkObserved { return Err(EBUSY); }
        if result > 0 || result < -4095 { return Err(EINVAL); }
        self.phase = if result == 0 { ForkPhase::Linked } else { ForkPhase::AbortRequested };
        Ok(())
    }

    pub(crate) fn begin_access(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if !matches!(self.phase, ForkPhase::AdoptedAwaitFirstReturn | ForkPhase::FirstReturnPublished
            | ForkPhase::GuestLinkObserved | ForkPhase::Linked) { return Err(EBUSY); }
        self.accesses = self.accesses.checked_add(1).ok_or(EOVERFLOW)?;
        Ok(())
    }

    pub(crate) fn end_access(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        self.accesses = self.accesses.checked_sub(1).ok_or(EINVAL)?;
        Ok(())
    }

    pub(crate) fn request_abort(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.prepared { self.abort_pending = true; return Ok(()); }
        match self.phase {
            ForkPhase::Released | ForkPhase::GuestDestroyed | ForkPhase::Quarantined => return Err(EBUSY),
            ForkPhase::HostRevoked => return Ok(()),
            _ => self.phase = ForkPhase::AbortRequested,
        }
        Ok(())
    }

    /// # Safety
    /// Caller must have closed admissions, drained all other operations, and
    /// revoked every host alias with completed TLB invalidation under the exact
    /// child MM/per-VMA exclusion. An exiting MM or missing PID is not proof.
    pub(crate) unsafe fn host_revoked(&mut self, identity: ForkIdentity, result: i32) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::AbortRequested || self.accesses != 0 { return Err(EBUSY); }
        kernel::error::to_result(result)?;
        if result != 0 { return Err(EINVAL); }
        self.phase = ForkPhase::HostRevoked;
        Ok(())
    }

    // BEGIN PRIVATE FORK PROVEN REVOKE
    pub(crate) fn revoke_drained(&self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.prepared || self.accesses != 0
            || !matches!(self.phase, ForkPhase::AbortRequested | ForkPhase::Quarantined | ForkPhase::HostRevoked)
        { return Err(EBUSY); }
        Ok(())
    }
    /// # Safety
    /// Stronger reconciliation boundary: exact backend admissions are closed
    /// and drained, the ORIGINAL retained first RET is still unpublished and
    /// reconciled to the terminal negative under its publication lock, and an
    /// authenticated real alias/TLB receipt covers this exact identity. This
    /// does not authorize guest destruction from ordinary quarantine alone.
    pub(crate) unsafe fn reconciled_quarantined_host_revoke(&mut self, identity: ForkIdentity) -> Result {
        self.revoke_drained(identity)?;
        if self.phase != ForkPhase::Quarantined { return Err(EBUSY); }
        self.phase = ForkPhase::HostRevoked;
        Ok(())
    }
    // END PRIVATE FORK PROVEN REVOKE

    pub(crate) fn permit_guest_destroy(&self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.phase != ForkPhase::HostRevoked || self.accesses != 0 { return Err(EBUSY); }
        Ok(())
    }

    /// # Safety
    /// Caller observed the final destructor of this exact guest VM after the
    /// revoke barrier, not merely a void release_thread return or absent PID.
    pub(crate) unsafe fn guest_destroyed(&mut self, identity: ForkIdentity) -> Result {
        self.permit_guest_destroy(identity)?;
        self.phase = ForkPhase::GuestDestroyed;
        Ok(())
    }

    pub(crate) fn acknowledge_destroyed(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.phase == ForkPhase::Released { return Ok(()); }
        if self.phase != ForkPhase::GuestDestroyed { return Err(EBUSY); }
        self.phase = ForkPhase::Released;
        Ok(())
    }

    pub(crate) fn quarantine(&mut self, identity: ForkIdentity) -> Result {
        self.check(identity)?;
        if self.phase == ForkPhase::Released { return Err(EBUSY); }
        if self.prepared { self.quarantine_pending = true; return Ok(()); }
        self.phase = ForkPhase::Quarantined;
        Ok(())
    }
}

// Native guest protocol marker. No existing 1-14 operation or launcher UAPI
// changes, and no new application opcode is routed in this bounded slice.
#[allow(dead_code)]
pub(crate) const FORK_NATIVE_MARKER: u64 = u64::from_le_bytes(*b"MCFK0001");

#[allow(dead_code)]
#[derive(Clone, Copy)]
pub(crate) struct ForkGeometry {
    pub(crate) start: u64,
    pub(crate) length: u64,
    pub(crate) root: u64,
}

#[allow(dead_code)]
pub(crate) struct ForkReservation {
    pub(crate) token: super::application_rpc::Token,
    pub(crate) identity: ForkIdentity,
    pub(crate) cpu: i32,
    pub(crate) first: super::application_syscall::Request,
    pub(crate) state: ForkAdoption,
    pub(crate) return_value: Option<i64>,
    pub(crate) return_published: bool,
}

#[allow(dead_code)]
impl ForkReservation {
    pub(crate) fn authorize_return(&self, value: i64) -> Result {
        if self.state.prepared() { return Err(EBUSY); }
        match self.state.phase() {
            ForkPhase::Reserved | ForkPhase::AbortRequested => {
                if !(-4095..0).contains(&value) { return Err(EBUSY); }
                Ok(())
            }
            _ => self.state.authorize_first_return(self.identity, value),
        }
    }

    pub(crate) fn observe_publication(&mut self) {
        if self.return_published { return; }
        let result = match self.return_value {
            Some(value) if value > 0 => self.state.first_return_published(self.identity, value),
            _ => self.state.request_abort(self.identity),
        };
        if result.is_err() { let _ = self.state.quarantine(self.identity); }
        self.return_published = true;
    }
}
}
use smp_application_image::*;

use core::ffi::c_void;
use std::{ptr, sync::atomic::{AtomicPtr, AtomicU32}};
const EIO:i32=-5; const ENODEV:i32=-19;
#[derive(Debug)]
struct AllocError;
impl From<AllocError> for i32 { fn from(_:AllocError)->Self {-12} }
struct Arc<T>{inner:std::sync::Arc<T>}
impl<T> Arc<T>{fn strong_count(this:&Self)->usize{std::sync::Arc::strong_count(&this.inner)}}
impl<T> Arc<T>{
    fn new(value:T,_:u32)->std::result::Result<Self,AllocError>{if ARC_FAIL_NEXT.swap(false,Ordering::SeqCst){drop(value);return Err(AllocError);}Ok(Self{inner:std::sync::Arc::new(value)})}
    fn downgrade(value:&Self)->std::sync::Weak<T>{std::sync::Arc::downgrade(&value.inner)}
    fn ptr_eq(left:&Self,right:&Self)->bool{std::sync::Arc::ptr_eq(&left.inner,&right.inner)}
}
impl<T> Clone for Arc<T>{fn clone(&self)->Self{Self{inner:self.inner.clone()}}}
impl<T> std::ops::Deref for Arc<T>{type Target=T;fn deref(&self)->&T{&self.inner}}
const GFP_KERNEL:u32=0;
static ARC_FAIL_NEXT:AtomicBool=AtomicBool::new(false);
thread_local!{static LOCK_DEPTH:std::cell::Cell<usize>=const{std::cell::Cell::new(0)};static JOINT_ID:std::cell::Cell<(i32,usize)>=const{std::cell::Cell::new((123,0x1000))};static MM_ACTIVE:std::cell::Cell<bool>=const{std::cell::Cell::new(false)};}

const ESRCH:i32=-3;
use smp_resource::OsToken;
use smp_memory::SyscallResponse as Memory;
#[path="/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/smp_resource.rs"] mod smp_resource;
#[path="/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/smp_image.rs"] mod smp_image;
#[path="/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/ihk_mapping.rs"] mod ihk_mapping;
#[path="/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/application_pager.rs"] mod application_pager;

// Linux direct-map/allocator services are explicit, all ledgers and bytes real.
mod smp_memory {
 pub(crate) use crate::smp_resource;
 pub(crate) use crate::memory::service::Application;
 pub(crate) use storage::{SyscallResponse,ForkPayload,ForkPayloadSeed,fork_payload_construct,fork_payload_abort,fork_payload_complete};
 pub(crate) mod storage {
  use crate::application_syscall::{Request as SyscallRequest,ResponseMemory,RESPONSE_BYTES};
  use crate::smp_resource::{MemoryExtent,MemoryMap,OsToken};
  use crate::smp_image::IDENTITY_WINDOW_END;
  use core::{ptr,sync::atomic::{AtomicU64,Ordering}};
  use crate::{Arc,ToErrno};use adapters::*;
  #[path="/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/private_fork_carrier_request_20261017.rs"] mod fork_carrier_request;
  mod adapters {
   pub type Error=i32;pub type Result<T=()> = std::result::Result<T,i32>;
   pub const EINVAL:i32=-22;pub const EBUSY:i32=-16;pub const EIO:i32=-5;pub const ENOMEM:i32=-12;pub const EAGAIN:i32=-11;pub const EACCES:i32=-13;pub const GFP_KERNEL:u32=0;
   pub struct Mutex<T>(std::sync::Mutex<T>);impl<T> Mutex<T>{pub fn new(x:T)->Self{Self(std::sync::Mutex::new(x))}pub fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
   pub struct Vec<T>(pub std::vec::Vec<T>);impl<T> Vec<T>{pub fn new()->Self{Self(std::vec::Vec::new())}pub fn as_slice(&self)->&[T]{&self.0}pub fn push(&mut self,x:T,_:u32)->Result{self.0.push(x);Ok(())}}
   impl<T> core::ops::Deref for Vec<T>{type Target=[T];fn deref(&self)->&[T]{&self.0}}impl<T> core::ops::DerefMut for Vec<T>{fn deref_mut(&mut self)->&mut[T]{&mut self.0}}
   pub struct Box<T>(std::boxed::Box<T>);impl<T> Box<T>{pub fn new(x:T,_:u32)->Result<Self>{Ok(Self(std::boxed::Box::new(x)))}pub fn into_raw(x:Self)->*mut T{std::boxed::Box::into_raw(x.0)}pub unsafe fn from_raw(p:*mut T)->Self{Self(unsafe{std::boxed::Box::from_raw(p)})}}
  }
  fn errno(code:i32)->i32{code}
  trait GuestExtents {
    fn len(&self) -> usize;
    fn extent(&self, index: usize) -> Option<MemoryExtent>;
}

impl<const N: usize> GuestExtents for MemoryMap<N> {
    fn len(&self) -> usize {
        MemoryMap::len(self)
    }
    fn extent(&self, index: usize) -> Option<MemoryExtent> {
        MemoryMap::extent(self, index)
    }
}

impl GuestExtents for [MemoryExtent] {
    fn len(&self) -> usize {
        <[MemoryExtent]>::len(self)
    }
    fn extent(&self, index: usize) -> Option<MemoryExtent> {
        self.get(index).copied()
    }
}

fn checked_guest_bytes(
    map: &(impl GuestExtents + ?Sized),
    owner: super::smp_resource::OsToken,
    direct_map: u64,
    physical: u64,
    bytes: usize,
) -> Result<*mut u8> {
    let end = physical.checked_add(bytes as u64).ok_or(EINVAL)?;
    if physical == 0 || bytes == 0 || end > IDENTITY_WINDOW_END {
        return Err(EINVAL);
    }
    direct_map.checked_add(end - 1).ok_or(EINVAL)?;
    for index in 0..map.len() {
        let extent = map.extent(index).ok_or(EIO)?;
        if extent.owner() == Some(owner)
            && extent.start() <= physical
            && end <= extent.end().map_err(|_| EIO)?
        {
            return Ok(direct_map.checked_add(physical).ok_or(EINVAL)? as *mut u8);
        }
    }
    Err(EINVAL)
}

  #[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct Span {
    physical: u64,
    end: u64,
}

impl Span {
    pub(super) fn new(physical: u64, bytes: usize) -> Result<Self> {
        if physical == 0 || bytes == 0 {
            return Err(EINVAL);
        }
        Ok(Self {
            physical,
            end: physical.checked_add(bytes as u64).ok_or(EINVAL)?,
        })
    }

    fn overlaps(self, other: Self) -> bool {
        self.physical < other.end && other.physical < self.end
    }
}

#[derive(Clone, Copy)]
struct Tagged {
    span: Span,
    serial: u64,
}

struct Ledger {
    fixed: Vec<Span>,
    requests: Vec<Option<Tagged>>,
    responses: Vec<Option<Tagged>>,
    payloads: Vec<Option<Tagged>>,
    fork_payloads: Vec<Option<Tagged>>,
    snoops: Vec<Tagged>,
    procfs: Vec<Tagged>,
    zeroing: Vec<Tagged>,
    serial: u64,
}

impl Ledger {
    fn conflicts(&self, span: Span, snoops: bool) -> bool {
        self.fixed.iter().any(|old| old.overlaps(span))
            || self
                .requests
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .payloads
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self.fork_payloads.iter().flatten().any(|old| old.span.overlaps(span))
            || self
                .responses
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
            || self.procfs.iter().any(|old| old.span.overlaps(span))
            || self.zeroing.iter().any(|old| old.span.overlaps(span))
    }

    fn tag(&mut self, span: Span) -> Result<Tagged> {
        self.serial = self.serial.checked_add(1).ok_or_else(|| errno(-75))?;
        Ok(Tagged {
            span,
            serial: self.serial,
        })
    }
}


  pub(crate) struct Memory {
    pub(crate) owner: OsToken,
    pub(super) direct_map: u64,
    extents: Vec<MemoryExtent>,
    layout: crate::smp_image::BootLayout,
    numa_nodes: usize,
    ledger: Mutex<Ledger>,
}
  impl Memory{fn address(&self, physical: u64, bytes: usize) -> Result<u64> {
        checked_guest_bytes(
            self.extents.as_slice(),
            self.owner,
            self.direct_map,
            physical,
            bytes,
        )
        .map(|value| value as u64)
    } pub(super) fn application_range(&self, physical: u64, bytes: usize) -> Result {
        self.address(physical, bytes)?;
        if self
            .ledger
            .lock()
            .conflicts(Span::new(physical, bytes)?, true)
        {
            return Err(EBUSY);
        }
        Ok(())
    } pub(crate) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let physical = request.response();
        if physical % 8 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, RESPONSE_BYTES)?;
        let span = Span::new(physical, RESPONSE_BYTES)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let slot = ledger
            .responses
            .iter()
            .position(Option::is_none)
            .ok_or(EAGAIN)?;
        // SAFETY: The checked exact-generation RAM is aligned and disjoint
        // from every active service access. The guest owns only atomic state.
        let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
        // SAFETY: The same retained, response-sized mapping covers the
        // eight-byte-aligned state word at offset 16. The held ledger claim
        // excludes host aliases, while the guest accesses this shared word
        // atomically; this creates no Rust reference to guest memory.
        let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(errno(-71));
        }
        let tag = ledger.tag(span)?;
        ledger.responses[slot] = Some(tag);
        Ok(SyscallResponse {
            memory: self.clone(),
            address,
            tag,
            slot,
            payload: None,
        })
    }}
  pub(crate) struct SyscallResponse {
    memory: Arc<Memory>,
    address: u64,
    tag: Tagged,
    slot: usize,
    // Same slot in a distinct ledger: this capability outlives all page I/O
    // and stays excluded until the response's actual final publication.
    payload: Option<(Tagged, u64, bool)>,
}

impl SyscallResponse {
    pub(crate) fn prepare_pager(&mut self, request: &SyscallRequest) -> Result {
        let operation = crate::application_pager::Operation::decode(request).map_err(errno)?;
        let Some((physical, bytes, to_guest)) = operation.payload() else {
            return Ok(());
        };
        self.prepare_payload(physical, bytes, to_guest)
    }

    fn prepare_payload(&mut self, physical: u64, bytes: usize, to_guest: bool) -> Result {
        if self.payload.is_some() {
            return Err(EBUSY);
        }
        let address = self.memory.address(physical, bytes)?;
        let span = Span::new(physical, bytes)?;
        let mut ledger = self.memory.ledger.lock();
        if ledger.payloads[self.slot].is_some() || ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let tag = ledger.tag(span)?;
        ledger.payloads[self.slot] = Some(tag);
        self.payload = Some((tag, address, to_guest));
        Ok(())
    }

    pub(crate) fn copy_tids(&mut self, request: &SyscallRequest, bytes: &mut [u8]) -> Result {
        let (physical, length) = request.tid_buffer().map_err(errno)?;
        if length != bytes.len() as u64 {
            return Err(EINVAL);
        }
        self.prepare_payload(physical, bytes.len(), true)?;
        self.pager_copy(0, bytes, true)
    }

    pub(crate) fn pager_copy(&mut self, offset: usize, bytes: &mut [u8], to_guest: bool) -> Result {
        let (tag, address, direction) = self.payload.ok_or(EINVAL)?;
        if to_guest != direction
            || offset
                .checked_add(bytes.len())
                .is_none_or(|end| end as u64 > tag.span.end - tag.span.physical)
        {
            return Err(EINVAL);
        }
        // SAFETY: The bounded offset lies in the retained payload span. The
        // mailbox reservation or complete-transfer critical section excludes
        // completion and cancellation, and its unique tag excludes every host
        // mapping; byte accesses need no stronger alignment or Rust reference.
        for (index, byte) in bytes.iter_mut().enumerate() {
            unsafe {
                let pointer = (address as *mut u8).add(offset + index);
                if to_guest {
                    ptr::write_volatile(pointer, *byte);
                } else {
                    *byte = ptr::read_volatile(pointer);
                }
            }
        }
        Ok(())
    }
}

// SAFETY: Memory::syscall is the only constructor. It validates the complete
// retained mapping and excludes aliases under the shared ledger. Unfinished
// destruction does not remove the tag or acknowledge the guest.
unsafe impl ResponseMemory for SyscallResponse {
    fn physical(&self) -> u64 {
        self.tag.span.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.address as *mut u8
    }
    unsafe fn release(self) {
        let mut ledger = self.memory.ledger.lock();
        let slot = &mut ledger.responses[self.slot];
        assert!(slot
            .as_ref()
            .is_some_and(|tag| tag.serial == self.tag.serial));
        *slot = None;
        if let Some((tag, _, _)) = self.payload {
            assert!(ledger.payloads[self.slot]
                .as_ref()
                .is_some_and(|old| old.serial == tag.serial));
            ledger.payloads[self.slot] = None;
        }
        // The guest can already reuse the response; only host bookkeeping is
        // accessed above. No destructor dereferences its address.
    }
}


  
/// A synchronous constructor seed, never an owned response or a phase proof.
/// The registered SMP adoption callback supplies this only after authenticating
/// the exact original Delivered call while IHK's initializing pending owner
/// retains admission, OS storage and provider/module text. No Runtime dispatch
/// path may construct it or read the submission bytes.
pub(crate) struct ForkPayloadSeed<'a> {
    response: &'a mut SyscallResponse,
    request: &'a SyscallRequest,
    owner: OsToken,
    used: bool,
}
impl<'a> ForkPayloadSeed<'a> {
    /// # Safety
    /// The exact original Delivered response remains exclusively borrowed for
    /// this entire seed/attach call. The actual IHK pending ForkProviderOwner
    /// spans construction, rollback, callback return and any sealed capsule.
    /// The guest kernel owns private, retained 128-byte backing and cannot
    /// rewrite it while its original request waits for host completion.
    pub(crate) unsafe fn new(response: &'a mut SyscallResponse,
        request: &'a SyscallRequest, owner: OsToken) -> Self
    { Self { response, request, owner, used: false } }
}

/// Storage ownership only: this non-Clone capability authenticates no phase,
/// full key, sequence or successful adoption. IHK owns its allocation; SMP may
/// borrow it only while the exact epoch/capsule remains retained. Ordinary RET
/// releases only the independent 40-byte response, never this ledger entry.
pub(crate) struct ForkPayload {
    memory: Arc<Memory>,
    address: u64,
    tag: Tagged,
    slot: usize,
    original_response: u64,
    descriptor: fork_carrier_request::RequestDescriptor,
}
impl ForkPayload {
    pub(crate) fn descriptor(&self) -> &fork_carrier_request::RequestDescriptor { &self.descriptor }
    pub(crate) fn physical(&self) -> u64 { self.tag.span.physical }
    pub(crate) fn original_response(&self) -> u64 { self.original_response }
    pub(crate) fn owner(&self) -> OsToken { self.memory.owner }

    /// Caller supplies the exact pinned capsule's exclusive borrow. The real
    /// backend must independently authorize each direction/phase/sequence.
    pub(crate) fn copy_to_guest(&mut self, bytes: &[u8; 128]) -> Result {
        self.copy(bytes.as_ptr().cast_mut(), true)
    }
    pub(crate) fn copy_from_guest(&mut self, bytes: &mut [u8; 128]) -> Result {
        self.copy(bytes.as_mut_ptr(), false)
    }
    fn copy(&mut self, bytes: *mut u8, to_guest: bool) -> Result {
        let ledger = self.memory.ledger.lock();
        if !ledger.fork_payloads.get(self.slot).and_then(Option::as_ref)
            .is_some_and(|old| old.serial == self.tag.serial && old.span == self.tag.span)
        { return Err(EIO); }
        // SAFETY: The IHK capsule and original Memory owners retain the whole
        // mapped span. The unique tag excludes every host alias. This exclusive
        // borrow and actual delivery/RET ordering exclude peer byte access.
        // These are byte operations; no reference to shared guest bytes exists.
        for index in 0..128 { unsafe {
            let peer = (self.address as *mut u8).add(index);
            if to_guest { ptr::write_volatile(peer, ptr::read(bytes.add(index))); }
            else { ptr::write(bytes.add(index), ptr::read_volatile(peer)); }
        }}
        Ok(())
    }
}

/// # Safety
/// Called ONLY by IHK's exact initializing payload attach, under its genuine
/// independent pending owner, with a live unique ForkPayloadSeed and output.
/// Output remains owned by IHK, never by the SMP borrowed pointer. On failure
/// no mapping/tag/context was published; on success IHK must retain it until
/// safe unsealed rollback, or true final ACK PLUS its actual RET publication
/// receipt and completion of every last response access. All SMP borrows must
/// end before either consuming cleanup; stage2 acceptance alone is insufficient.
pub(crate) unsafe extern "C" fn fork_payload_construct(
    seed: *mut core::ffi::c_void, out: *mut *mut core::ffi::c_void,
) -> i32 {
    let result = (|| -> Result {
        if seed.is_null() || out.is_null() { return Err(EINVAL); }
        let seed = unsafe { &mut *seed.cast::<ForkPayloadSeed<'_>>() };
        if seed.used { return Err(EBUSY); }
        seed.used = true;
        let response = &mut *seed.response;
        if seed.owner != response.memory.owner || seed.request.number() != 56
            || seed.request.response() != response.tag.span.physical
        { return Err(EACCES); }
        let args = seed.request.arguments();
        let physical = fork_carrier_request::RequestDescriptor::physical(&args).map_err(errno)?;
        let address = response.memory.address(physical, 128)?;
        let span = Span::new(physical, 128)?;
        let mut ledger = response.memory.ledger.lock();
        if !ledger.responses.get(response.slot).and_then(Option::as_ref)
            .is_some_and(|tag| tag.serial == response.tag.serial && tag.span == response.tag.span)
        { return Err(EIO); }
        if ledger.conflicts(span, true) { return Err(EBUSY); }
        let slot = ledger.fork_payloads.iter().position(Option::is_none).ok_or(EAGAIN)?;
        // First payload read occurs only after exact response/owner checks and
        // while shared ledger exclusion reserves the full checked span. No
        // other host claim can enter before the final tag insertion below.
        let mut bytes = [0u8; 128];
        for (index, byte) in bytes.iter_mut().enumerate() {
            *byte = unsafe { ptr::read_volatile((address as *const u8).add(index)) };
        }
        let descriptor = fork_carrier_request::RequestDescriptor::decode(&bytes, &args).map_err(errno)?;
        let tag = ledger.tag(span)?;
        // Allocate BEFORE inserting the claim: allocation failure publishes
        // neither a tag nor an output context and requires no rollback callback.
        let payload = Box::new(ForkPayload { memory: response.memory.clone(), address,
            tag, slot, original_response: response.tag.span.physical, descriptor }, GFP_KERNEL)?;
        ledger.fork_payloads[slot] = Some(tag);
        unsafe { out.write(Box::into_raw(payload).cast()); }
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

// Only the two typed lifecycle callbacks below may consume an IHK-owned box.
// Failure leaves its pointer, tag and owners intact for quarantine; no retry
// after a successful consuming return may use the old pointer.
unsafe fn fork_payload_release(context: *mut core::ffi::c_void) -> i32 {
    if context.is_null() { return EINVAL.to_errno(); }
    let payload = unsafe { &*context.cast::<ForkPayload>() };
    {
        let mut ledger = payload.memory.ledger.lock();
        let Some(slot) = ledger.fork_payloads.get_mut(payload.slot) else { return EIO.to_errno(); };
        if !slot.as_ref().is_some_and(|tag| tag.serial == payload.tag.serial && tag.span == payload.tag.span)
        { return EIO.to_errno(); }
        *slot = None;
    }
    // SAFETY: IHK is the sole allocation owner and excludes all SMP borrows.
    // Its independent ForkProviderOwner still spans this callback return, so
    // neither the Memory Arc nor provider text is its last OS/module hold.
    unsafe { drop(Box::from_raw(context.cast::<ForkPayload>())); }
    0
}
/// # Safety
/// IHK proved the exact capsule NEVER sealed and all SMP borrows ended. This
/// callback completes BEFORE backend publication unfreezes and before IHK drops
/// the initializing pending owner. No sealed/cancel/copy uncertainty may enter.
pub(crate) unsafe extern "C" fn fork_payload_abort(context: *mut core::ffi::c_void) -> i32 {
    unsafe { fork_payload_release(context) }
}
/// # Safety
/// IHK accepted the actual generation/nonce/full-key final destruction ACK and
/// exact alias/TLB/access-drain proofs AND the actual final-ACK RET publication
/// receipt. Every last response access ended and ChildFork relinquished every
/// borrow. Stage2 acceptance alone is insufficient and cannot call this cleanup.
/// The independent pending owner remains live through this callback return.
pub(crate) unsafe extern "C" fn fork_payload_complete(context: *mut core::ffi::c_void) -> i32 {
    unsafe { fork_payload_release(context) }
}

  pub(crate) fn new_fixture(storage:*mut u8,bytes:usize)->Arc<Memory>{
   let owner=unsafe{OsToken::from_ihk_lease_v2(0,2).unwrap()};let base=0x1000000;
   let mut map=MemoryMap::<4>::new();let mut slots=[None;4];let mut workspace=crate::smp_resource::MemoryWorkspace::new(&mut slots).unwrap();
   map.insert_free(base,bytes as u64,0,&mut workspace).unwrap();map.assign(owner,base,bytes as u64,&mut workspace).unwrap();
   let layout=crate::smp_image::BootLayout::select(&map,owner).unwrap();let mut extents=Vec::new();extents.push(map.extent(0).unwrap(),0).unwrap();
   Arc::new(Memory{owner,direct_map:storage as u64-base,extents,layout,numa_nodes:1,ledger:adapters::Mutex::new(Ledger{fixed:Vec::new(),requests:Vec(vec![None;8]),responses:Vec(vec![None;8]),payloads:Vec(vec![None;8]),fork_payloads:Vec(vec![None;8]),snoops:Vec::new(),procfs:Vec::new(),zeroing:Vec::new(),serial:0})},0).unwrap()
  }
  pub(crate) fn claims(memory:&Memory)->(usize,usize){let l=memory.ledger.lock();(l.responses.iter().flatten().count(),l.fork_payloads.iter().flatten().count())}
 }
}

struct Mutex<T>(std::sync::Mutex<T>);
struct FixtureGuard<'a,T>{inner:Option<std::sync::MutexGuard<'a,T>>}
impl<T> std::ops::Deref for FixtureGuard<'_,T>{type Target=T;fn deref(&self)->&T{self.inner.as_ref().unwrap()}}
impl<T> std::ops::DerefMut for FixtureGuard<'_,T>{fn deref_mut(&mut self)->&mut T{self.inner.as_mut().unwrap()}}
impl<T> Drop for FixtureGuard<'_,T>{fn drop(&mut self){drop(self.inner.take());LOCK_DEPTH.with(|depth|{assert!(depth.get()>0);depth.set(depth.get()-1);});run_unlocked_hook();}}
impl<T> Mutex<T>{fn new(value:T)->Self{Self(std::sync::Mutex::new(value))}fn lock(&self)->FixtureGuard<'_,T>{MM_ACTIVE.with(|active|assert!(!active.get(),"provider lock under MM"));let inner=self.0.lock().unwrap();LOCK_DEPTH.with(|depth|depth.set(depth.get()+1));FixtureGuard{inner:Some(inner)}}}

mod smp_application {use super::*;use crate::smp_memory::SyscallResponse;use crate::consumer_fixture::bindings;
struct ForkChildOwner {
    pid: NonNull<bindings::pid>,
    mm: NonNull<bindings::mm_struct>,
    number: i32,
}
// SAFETY: Only immutable identity and the Linux owned PID/MM references move.
unsafe impl Send for ForkChildOwner {}
// SAFETY: No MM mapping access follows from these shared structural identities.
unsafe impl Sync for ForkChildOwner {}
impl ForkChildOwner {
    fn current() -> Result<Self> {
        // SAFETY: Linux acquires both references from the live current task.
        let pid = NonNull::new(unsafe {
            bindings::get_task_pid(bindings::get_current(), bindings::pid_type_PIDTYPE_TGID)
        }).ok_or(ESRCH)?;
        let Some(mm) = NonNull::new(unsafe { bindings::get_task_mm(bindings::get_current()) }) else {
            unsafe { bindings::put_pid(pid.as_ptr()) };
            return Err(ESRCH);
        };
        let number = unsafe { bindings::pid_nr_ns(pid.as_ptr(), ptr::addr_of_mut!(bindings::init_pid_ns)) };
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let grabbed = if number > 0 {
            count.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
                |value| (value > 0).then(|| value.checked_add(1)).flatten()).map_err(|_| errno(-75))
        } else { Err(ESRCH) };
        // SAFETY: End transient mm_users even on failure; only mm_count may
        // survive publication, matching the established mirror lifetime rule.
        unsafe { bindings::mmput(mm.as_ptr()) };
        if let Err(error) = grabbed {
            unsafe { bindings::put_pid(pid.as_ptr()) };
            return Err(error);
        }
        Ok(Self { pid, mm, number })
    }
}
impl Drop for ForkChildOwner {
    fn drop(&mut self) {
        let count = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.mm_count.counter
        )) };
        let old = count.fetch_sub(1, Ordering::SeqCst);
        assert!(old > 0);
        if old == 1 { unsafe { bindings::__mmdrop(self.mm.as_ptr()) }; }
        unsafe { bindings::put_pid(self.pid.as_ptr()) };
    }
}

struct Entry {
    cleanup: Exchange, owner_slot: i32, owner_generation: u64, scheduled: bool,
    closed: bool, needs_cleanup: bool, quarantined: bool, prepare: Option<()>,
    fork_ingress:Option<fork_ingress::ForkIngressMarker>, fork: Option<ChildFork>, syscalls: Mailbox<Memory>, fork_prepared_parent_refs: u32,
    procfs: Option<Procfs>, retirement: Option<Exchange>,
}
struct Procfs;
impl Procfs { fn drained(&self) -> bool { true } fn threads_retired(&self) -> bool { true } }
impl Entry {     fn key(&self) -> Token {
        self.cleanup.token()
    }     fn release_ready(&self) -> bool {
        self.fork.is_none() && self.fork_ingress.is_none() && self.fork_prepared_parent_refs == 0 && !self.quarantined
            && self.cleanup.release_ready()
            && self.syscalls.drained()
            && self.procfs.as_ref().is_none_or(|procfs| procfs.drained())
            && (!self.scheduled
                || self.cleanup.result() == Some(0)
                    && self
                        .retirement
                        .as_ref()
                        .is_some_and(|query| query.result() == Some(0))
                    && self
                        .procfs
                        .as_ref()
                        .is_some_and(|procfs| procfs.threads_retired()))
    } fn request_cleanup(&mut self)->Result { Ok(()) } }
pub(crate) struct Remote { owner: OsToken, slots: Mutex<Vec<Option<Entry>>>, transport_failed: AtomicBool, release_token: Token, releases: Mutex<Mailbox<Memory>> }
impl Remote{fn transport_health(&self)->Result{if self.transport_failed.load(Ordering::Relaxed){Err(EIO)}else{Ok(())}}
fn quarantine_transport(&self,_:&mut[Option<Entry>],_:i32){self.transport_failed.store(true,Ordering::Relaxed);}
pub(crate) fn publish_syscall(
        &self,
        token: Token,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
        notify: impl FnOnce() -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if token == self.release_token {
            let result = self
                .releases
                .lock()
                .publish(cpu, |packet| send(packet).map_err(|error| error.to_errno()))
                .map_err(errno);
            return self.finish_publication(&mut slots, result, notify);
        }
        if fork_publication_frozen(&slots, token, cpu)
            || fork_link::publication_frozen(&mut slots, token, cpu)
        { return Ok(false); }
        let Some(entry) = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
        else {
            return Ok(false);
        };
        let result = entry
            .syscalls
            .publish(cpu, |packet| send(packet).map_err(|e| e.to_errno()))
            .map_err(errno);
        if matches!(&result, Ok(true)) {
            observe_fork_publication(&mut slots, token);
            fork_link::observe_publication(&mut slots, token);
        }
        // `send` above means only queue publication. Notification runs after
        // the response has released its memory, but under the same application
        // mutex as RET completion. Its error must never retry that publication.
        let published = self.finish_publication(&mut slots, result, notify)?;
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.needs_cleanup && entry.syscalls.drained() && !entry.quarantined {
            if let Err(error) = entry.request_cleanup() {
                entry.quarantined = true;
                pr_err!(
                    "IHK-SMP: syscall drain retained application pid={} cleanup_errno={}\n",
                    entry.cleanup.pid(),
                    error.to_errno()
                );
                // Publication and notification already happened. A following
                // cleanup failure cannot cause another syscall publication.
            }
        }
        Ok(published)
    }fn finish_publication(
        &self,
        slots: &mut [Option<Entry>],
        published: Result<bool>,
        notify: impl FnOnce() -> Result,
    ) -> Result<bool> {
        match published {
            Ok(true) => match notify() {
                Ok(()) => Ok(true),
                Err(error) => {
                    pr_err!("IHK-SMP: application transport failure os={} generation={} phase=postpublication_notify errno={}\n",
                        self.owner.slot(), self.owner.generation(), error.to_errno());
                    self.quarantine_transport(slots, error);
                    Err(error)
                }
            },
            Ok(false) => Ok(false),
            Err(error) if error == EBUSY || error == EAGAIN => Ok(false),
            Err(error) => {
                pr_err!("IHK-SMP: application transport failure os={} generation={} phase=prepublication errno={}\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno());
                self.quarantine_transport(slots, error);
                Err(error)
            }
        }
    }pub(crate) fn prepare_fork(self: &Arc<Self>, parent: Token, child: Token, geometry: ForkGeometry) -> Result<PreparedForkLease> {
        let child_owner = Arc::new(ForkChildOwner::current()?, GFP_KERNEL)?;
        let seal = Arc::new(PreparedForkSeal { sealed: AtomicBool::new(false) }, GFP_KERNEL)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let (token, identity) = reserve_fork_in_slots(self.owner, &mut slots, parent, child, child_owner, geometry, seal.clone())?;
        Ok(PreparedForkLease { remote: Some(self.clone()), seal, child, token, identity })
    }}

struct PreparedForkSeal {
    sealed: AtomicBool,
}

struct ForkParentPin {
    parent: Token,
    identity: ForkIdentity,
    reservation: u64,
    remote: Arc<Remote>,
}
impl ForkAckRecord {
    fn new(epoch: u64) -> Self {
        Self { epoch, delivery: None, busy: false, verified: false,
            accepted: false, published: false, publication_busy: false }
    }
}
struct ForkAckRecord {
    epoch: u64,
    delivery: Option<ForkAckDelivery>,
    busy: bool,
    verified: bool,
    accepted: bool,
    published: bool,
    publication_busy: bool,
}
#[derive(Clone)]
struct ForkAckDelivery {
    worker: u64,
    serial: u64,
    cpu: i32,
    request: Request,
}
struct ChildFork {
    owner: Arc<ForkChildOwner>,
    reservation: ForkReservation,
    seal: Arc<PreparedForkSeal>,
    // Deliberate retention after any sealed outcome. Only an actual revoke,
    // completed TLB barrier and final guest destruction ACK may break it.
    retained_remote: Option<Arc<Remote>>,
    retained_parent: Option<ForkParentPin>,
    link: Option<fork_link::ForkLinkRecord>,
    ack: Option<ForkAckRecord>,
    control: Option<fork_link::ForkControlOwner>,
    // A failed UNSEALED payload rollback retains the actual typed lease and
    // its publication freeze for later exact reconciliation, never a raw lease.
    held_lease: Option<PreparedForkLease>,
}

// This capability cannot be copied or manufactured from the diagnostic token.
// Immutable authority and the preallocated seal survive child-MM exclusion.
// BEGIN PREPARED FORK LEASE
pub(crate) struct PreparedForkLease {
    remote: Option<Arc<Remote>>,
    seal: Arc<PreparedForkSeal>,
    child: Token,
    token: u64,
    identity: ForkIdentity,
}

// This view cannot outlive or be copied independently of the exclusive lease
// borrow. Only the SAME preallocated atomic is lent to the synchronous bridge.
pub(crate) struct PreparedForkBorrow<'lease> {
    pub(crate) identity: ForkIdentity,
    pub(crate) sealed: &'lease AtomicBool,
}

#[allow(dead_code)]
impl Remote { pub(crate) fn release_fork_ack(&self, child: Token, key: ForkIdentity, epoch: u64) -> Result {
        let retired = {
            let mut slots = self.slots.lock();
            let index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
            let fork = slots[index].as_ref().unwrap().fork.as_ref().ok_or(ENOENT)?;
            if let Some(pin) = &fork.retained_parent {
                if pin.parent.wire() != key.parent || pin.identity != key
                    || pin.reservation != fork.reservation.token.wire()
                    || !core::ptr::eq(&*pin.remote, self) { return Err(EACCES); }
                // No reviewed normal-handoff or terminal pin-consumption
                // endpoint exists yet. Keep this exact parent Entry alive.
                return Err(EBUSY);
            }
            if fork.control.is_some() { return Err(EBUSY); }
            let ack = fork.ack.as_ref().ok_or(EIO)?;
            if fork.reservation.identity != key || ack.epoch != epoch || !ack.verified
                || !ack.accepted || !ack.published || !ack.publication_busy || ack.busy
                || fork.reservation.state.phase() != ForkPhase::Released
            { return Err(EACCES); }
            slots[index].take()
        };
        drop(retired);
        Ok(())
    } }
impl PreparedForkLease {
    pub(crate) fn borrow_seal(&mut self) -> PreparedForkBorrow<'_> {
        PreparedForkBorrow { identity: self.identity, sealed: &self.seal.sealed }
    }

    /// The consumer calls this exactly at its infallible VMA owner/PFN commit.
    /// No lock, allocation, callback, destructor or cancellation processing is
    /// permitted here. Repeated stores do not weaken the exclusive capability.
    pub(crate) fn seal(&mut self) {
        self.seal.sealed.store(true, Ordering::Release);
    }

    /// Call after MM unlock, local publication and publication-guard release.
    pub(crate) fn finish(mut self) {
        self.finish_inner(true);
    }

    /// Retain an unsealed lease after an uncertain payload rollback. This is
    /// recoverable exact-key storage; its prepared state and parent pin remain.
    pub(crate) fn retain_prepared(self) -> core::result::Result<(), Self> {
        let Some(remote) = self.remote.as_ref().cloned() else { return Err(self); };
        let mut slots = remote.slots.lock();
        let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) else { return Err(self); };
        if fork.reservation.identity != self.identity || !Arc::ptr_eq(&fork.seal, &self.seal)
            || !fork.reservation.state.prepared() || fork.held_lease.is_some()
        { return Err(self); }
        fork.retained_remote = Some(remote.clone());
        fork.held_lease = Some(self);
        drop(slots);
        Ok(())
    }

    /// The original MM callback and all local guards have returned. The exact
    /// IHK owner/capsule has become publishable before entry; this one slots
    /// lock covers phase/key/SAME seal validation, fixed first receipt write,
    /// and readiness. No fallible allocation or external callback occurs here.
    /// # Safety
    /// The genuine IHK capsule owns this initialized context under the SAME
    /// scoped adoption. No other payload borrow may exist before slots unlock.
    /// The caller passes a pointer, never an exclusive reference spanning the
    /// publication unlock and return; LINK may borrow immediately after unlock.
    pub(crate) unsafe fn finish_with_payload(&mut self, mut payload: NonNull<super::smp_memory::ForkPayload>) -> Result {
        let remote = self.remote.as_ref().ok_or(EIO)?.clone();
        let mut slots = remote.slots.lock();
        remote.transport_health()?;
        {
            let fork = child_fork_in_slots(&mut slots, self.child, self.token)?;
            if fork.reservation.identity != self.identity || !Arc::ptr_eq(&fork.seal, &self.seal)
                || !self.seal.sealed.load(Ordering::Acquire) || fork.held_lease.is_some()
                || !fork.reservation.state.prepared()
            { return Err(EACCES); }
            fork.reservation.state.finish_lease(self.identity, true, true)?;
            if fork.reservation.state.phase() != ForkPhase::AdoptedAwaitFirstReturn { return Err(EBUSY); }
        }
        let mut result = {
            // SAFETY: The actual IHK scope pins the initialized capsule. This
            // exclusive reference exists only inside the slots-held block;
            // its function-argument protector ends before publication unlock.
            let payload = unsafe { payload.as_mut() };
            fork_link::commit_adopted_fork_carrier_in_slots(
                remote.owner, &mut slots, self.child, self.identity, payload,
            )
        };
        if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
            if result.is_err() { let _ = fork.reservation.state.quarantine(self.identity); }
            fork.retained_remote = Some(remote.clone());
        } else { result = Err(EIO); }
        // The first return does not end parent-dependent LINK/ACK discovery.
        // Move this existing constructor pin; never decrement it at publication.
        if retain_fork_parent_pin(&remote, &mut slots, self.child, self.token, self.identity).is_err() {
            result = Err(EIO);
            if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
                let _ = fork.reservation.state.quarantine(self.identity);
            }
        }
        self.remote = None;
        drop(slots);
        result
    }

    fn finish_inner(&mut self, completed: bool) {
        let Some(remote) = self.remote.take() else { return; };
        let sealed = self.seal.sealed.load(Ordering::Acquire);
        let mut slots = remote.slots.lock();
        let transport_failed = remote.transport_health().is_err();
        let mut retained = false;
        if let Ok(fork) = child_fork_in_slots(&mut slots, self.child, self.token) {
            if fork.reservation.identity == self.identity
                && core::ptr::eq(&*fork.seal, &*self.seal)
            {
                if transport_failed { let _ = fork.reservation.state.quarantine(self.identity); }
                let result = fork.reservation.state.finish_lease(self.identity, sealed, completed);
                if result.is_err() { let _ = fork.reservation.state.quarantine(self.identity); }
                if sealed {
                    // This is outside MM/local publication exclusion. The
                    // preexisting Arc is cloned only here, never during seal.
                    fork.retained_remote = Some(remote.clone());
                    retained = true;
                }
            }
        }
        if let Some(parent) = slots.iter_mut().flatten().find(|entry| entry.key().wire() == self.identity.parent) {
            parent.fork_prepared_parent_refs = parent.fork_prepared_parent_refs.saturating_sub(1);
        }
        drop(slots);
        if sealed && !retained {
            // Corruption/failure cannot turn a sealed root into free ownership.
            // Retain the whole backend if the exact slot cannot be found.
            core::mem::forget(remote);
        }
    }
}

impl Drop for PreparedForkLease {
    fn drop(&mut self) { self.finish_inner(false); }
}
// END PREPARED FORK LEASE

fn retain_fork_parent_pin(remote: &Arc<Remote>, slots: &mut [Option<Entry>],
    child: Token, token: u64, identity: ForkIdentity) -> Result {
    let parent = slots.iter().flatten().find(|entry| entry.key().wire() == identity.parent)
        .filter(|entry| entry.fork_prepared_parent_refs != 0).ok_or(EIO)?.key();
    let fork = child_fork_in_slots(slots, child, token)?;
    if fork.reservation.identity != identity || fork.retained_parent.is_some() { return Err(EACCES); }
    fork.retained_parent = Some(ForkParentPin { parent, identity, reservation: token, remote: remote.clone() });
    Ok(())
}
// Caller holds this Remote's slots lock for discovery through publication.
// All child-owner allocation precedes this function; no guest/root is accessed.
fn reserve_fork_in_slots(
    owner: OsToken, slots: &mut [Option<Entry>], parent: Token, child: Token,
    child_owner: Arc<ForkChildOwner>, geometry: ForkGeometry, seal: Arc<PreparedForkSeal>,
) -> Result<(u64, ForkIdentity)> {
    if parent == child { return Err(EINVAL); }
    let parent_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == parent)).ok_or(ENOENT)?;
    let child_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
    let p = slots[parent_index].as_ref().unwrap();
    let c = slots[child_index].as_ref().unwrap();
    if p.closed || p.needs_cleanup || p.quarantined || !p.scheduled
        || c.closed || c.needs_cleanup || c.quarantined || c.scheduled || c.prepare.is_some()
        || c.fork.is_some() || c.fork_ingress.is_some() || c.cleanup.pid() != child_owner.number
    { return Err(EBUSY); }
    if p.owner_slot != owner.slot() as i32 || c.owner_slot != owner.slot() as i32
        || p.owner_generation != owner.generation() || c.owner_generation != owner.generation()
    {
        return Err(EACCES);
    }
    let parent_pid = p.cleanup.pid();
    let proof = p.syscalls.unique_delivered(|request| {
        let args = request.arguments();
        request.number() == 56 && request.pid() == parent_pid
            && !matches!(args[0], 1 | 2 | 3)
            && args[1] == geometry.start && args[2] == geometry.length && args[3] == geometry.root
            && args[4] != 0 && args[5] == FORK_NATIVE_MARKER
    }).map_err(errno)?.ok_or(ENOENT)?;
    let (worker, serial, request) = proof;
    let nonce = request.arguments()[4];
    if slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()).any(|fork| {
        let key = fork.reservation.identity;
        key.root == geometry.root || key.parent == parent.wire()
            && (key.delivery == serial || key.nonce == nonce)
    }) { return Err(EBUSY); }
    let identity = ForkIdentity {
        slot: owner.slot(), generation: owner.generation(), parent: parent.wire(),
        worker, delivery: serial, child: child.wire(), child_pid: child_owner.number,
        child_mm: child_owner.mm.as_ptr() as usize, root: geometry.root,
        start: geometry.start, length: geometry.length, nonce,
    };
    let mut state = ForkAdoption::reserve(identity)?;
    state.prepare_lease()?;
    let parent_refs = p.fork_prepared_parent_refs.checked_add(1).ok_or(EOVERFLOW)?;
    let token = Token::allocate().map_err(errno)?;
    let result = token.wire();
    slots[parent_index].as_mut().unwrap().fork_prepared_parent_refs = parent_refs;
    slots[child_index].as_mut().unwrap().fork = Some(ChildFork {
        owner: child_owner, seal, retained_remote: None, retained_parent: None, ack: None, link: None, control: None, held_lease: None,
        reservation: ForkReservation { token, identity, cpu: request.cpu(), first: request,
            state, return_value: None, return_published: false },
    });
    Ok((result, identity))
}

fn child_fork_in_slots(slots: &mut [Option<Entry>], child: Token, token: u64) -> Result<&mut ChildFork> {
    let entry = slots.iter_mut().flatten().find(|entry| entry.key() == child).ok_or(ENOENT)?;
    let fork = entry.fork.as_mut().ok_or(ENOENT)?;
    if fork.reservation.token.wire() != token || fork.reservation.identity.child != child.wire()
        || fork.owner.number != entry.cleanup.pid()
        || fork.owner.mm.as_ptr() as usize != fork.reservation.identity.child_mm
    { return Err(EACCES); }
    Ok(fork)
}

fn abort_fork_in_slots(slots: &mut [Option<Entry>], child: Token, token: u64) -> Result {
    let fork = child_fork_in_slots(slots, child, token)?;
    if let Some(link) = &fork.link { link.cancel_if_open()?; }
    fork.reservation.state.request_abort(fork.reservation.identity)
}

fn abort_parent_forks(slots: &mut [Option<Entry>], parent: Token, worker: Option<u64>) {
    fork_ingress::abort_parent_ingress(slots, parent, worker);
    for fork in slots.iter_mut().flatten().filter_map(|entry| entry.fork.as_mut()) {
        let identity = fork.reservation.identity;
        if identity.parent == parent.wire() && worker.is_none_or(|worker|
            identity.worker == worker || fork.link.as_ref().is_some_and(|link| link.has_second_worker(worker))) {
            if fork.link.as_ref().is_some_and(|link| link.cancel_if_open().is_err()) { continue; }
            let _ = fork.reservation.state.request_abort(identity);
        }
    }
}

// Pending cancellation can destroy the guest root on a negative first RET.
// Keep the original response claim unpublished while MM adoption is active;
// after seal, abort/quarantine stays frozen until the real host revoke barrier.
fn fork_publication_frozen(slots: &[Option<Entry>], parent: Token, cpu: i32) -> bool {
    if fork_ingress::publication_frozen(slots, parent, cpu)
        || fork_link::control_publication_frozen(slots, parent, cpu) { return true; }
    slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()).any(|fork| {
        let record = &fork.reservation;
        record.identity.parent == parent.wire() && record.cpu == cpu
            && (record.state.prepared()
                || fork.seal.sealed.load(Ordering::Acquire)
                    && matches!(record.state.phase(), ForkPhase::AbortRequested
                        | ForkPhase::Quarantined))
    })
}

fn authorize_fork_ack_return(slots: &[Option<Entry>], parent: Token, worker: u64,
    serial: u64, cpu: i64, value: i64) -> Result {
    for fork in slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()) {
        let Some(ack) = fork.ack.as_ref() else { continue; };
        let Some(delivery) = ack.delivery.as_ref() else { continue; };
        if fork.reservation.identity.parent == parent.wire()
            && delivery.worker == worker && delivery.serial == serial
            && (value != 0 || cpu != delivery.cpu as i64 || !ack.verified || !ack.accepted || ack.published)
        { return Err(EBUSY); }
    }
    Ok(())
}
fn authorize_fork_return(slots: &[Option<Entry>], parent: Token, worker: u64, serial: u64, cpu: i64, value: i64) -> Result {
    fork_link::authorize_control_return(slots, parent, worker, serial)?;
    fork_link::authorize_return(slots, parent, worker, serial, cpu, value)?;
    authorize_fork_ack_return(slots, parent, worker, serial, cpu, value)?;
    for fork in slots.iter().flatten().filter_map(|entry| entry.fork.as_ref()) {
        let record = &fork.reservation;
        if record.identity.parent == parent.wire() && record.identity.worker == worker
            && record.identity.delivery == serial
        {
            if record.cpu as i64 != cpu { return Err(EINVAL); }
            record.authorize_return(value)?;
        }
    }
    Ok(())
}

fn record_fork_return(slots: &mut [Option<Entry>], parent: Token, worker: u64, serial: u64, value: i64) {
    fork_link::record_return(slots, parent, worker, serial, value);
    for fork in slots.iter_mut().flatten().filter_map(|entry| entry.fork.as_mut()) {
        let record = &mut fork.reservation;
        if record.identity.parent == parent.wire() && record.identity.worker == worker && record.identity.delivery == serial {
            record.return_value = Some(value);
            if value < 0 { let _ = record.state.request_abort(record.identity); }
        }
    }
}

fn observe_fork_publication(slots: &mut [Option<Entry>], parent: Token) {
    let Some(parent_index) = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == parent)) else { return; };
    for index in 0..slots.len() {
        let completion = slots[index].as_ref().and_then(|entry| entry.fork.as_ref()).and_then(|fork| {
            let record = &fork.reservation;
            if record.identity.parent != parent.wire() || record.return_published { return None; }
            Some(slots[parent_index].as_ref().unwrap().syscalls.returned(record.identity.worker, record.identity.delivery))
        });
        if let Some(result) = completion {
            let record = &mut slots[index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
            match result {
                Ok(true) => record.observe_publication(),
                Ok(false) => {},
                Err(_) => { let _ = record.state.quarantine(record.identity); },
            }
        }
    }
}

mod fork_backend_progress{use super::*;
// This completion boundary covers ONLY the original unpublished first RET.
// Running/second-link teardown requires its separately authenticated protocol.
fn fork_progress_in_slots(
    owner: OsToken, slots: &mut [Option<Entry>], child: Token,
    identity: ForkIdentity, stage: u32,
) -> Result<(Option<usize>, usize)> {
    use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_GUEST_DESTROYED_V1};
    if identity.slot != owner.slot() || identity.generation != owner.generation()
        || identity.child != child.wire()
    { return Err(EACCES); }
    let child_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key() == child)).ok_or(ENOENT)?;
    let entry = slots[child_index].as_mut().unwrap();
    let fork = entry.fork.as_mut().ok_or(ENOENT)?;
    if fork.reservation.identity != identity || fork.owner.number != entry.cleanup.pid()
        || fork.owner.mm.as_ptr() as usize != identity.child_mm
        || !fork.seal.sealed.load(Ordering::Acquire)
    { return Err(EACCES); }
    // Positive first-publication pins have no reviewed terminal consumer yet.
    // Enforce retention at this generic destruction API as well as ACK release,
    // before changing a phase or permitting any child-slot removal.
    if fork.control.is_some()
        || stage == FORK_GUEST_DESTROYED_V1 && fork.retained_parent.is_some() { return Err(EBUSY); }
    if stage == FORK_HOST_REVOKED_V1 {
        // A sealed LINK grants irreversible same-kind2 handoff permission.
        // Host abort cannot alter that phase or close admissions afterwards.
        if let Some(link) = &fork.link { link.cancel_if_open()?; }
        // Close ACTUAL existing service admission before drain. Every current
        // prepare/start/worker/wait/with_prepared path observes this gate under
        // the same slots mutex. No child image was prepared or scheduled at
        // this original-first-RET boundary; foreign active state fails closed.
        entry.needs_cleanup = true;
        if fork.reservation.state.phase() != ForkPhase::Quarantined {
            fork.reservation.state.request_abort(identity)?;
        }
        entry.syscalls.close().map_err(errno)?;
    } else if stage != FORK_GUEST_DESTROYED_V1 { return Err(EINVAL); }
    if !entry.needs_cleanup || entry.scheduled || entry.prepare.is_some()
        || entry.procfs.is_some() || !entry.syscalls.drained()
    { return Err(EBUSY); }
    fork.reservation.state.revoke_drained(identity)?;
    let first = fork.reservation.first.clone();
    let value = fork.reservation.return_value;
    let published = fork.reservation.return_published;
    if stage == FORK_GUEST_DESTROYED_V1 {
        fork.reservation.state.permit_guest_destroy(identity)?;
        if !published || value != Some(super::application_abi::FORK_ABORT_RETURN_V1) { return Err(EBUSY); }
        // Publication retained the authenticated full child key and terminal
        // value. The parent's normally retired mailbox is no longer needed.
        return Ok((None, child_index));
    } else if published { return Err(EBUSY); }
    let parent_index = slots.iter().position(|slot| slot.as_ref().is_some_and(|entry| entry.key().wire() == identity.parent)).ok_or(ENOENT)?;
    if stage == FORK_HOST_REVOKED_V1 {
        // Establish exact response ownership/unpublished state BEFORE any MM
        // callback. AbortRequested/Quarantined freezes all its publication.
        slots[parent_index].as_mut().unwrap().syscalls.check_fork_abort(
            identity.worker, identity.delivery, &first, value,
        ).map_err(errno)?;
    }
    Ok((Some(parent_index), child_index))
}

#[allow(dead_code)]
impl Remote {
    pub(crate) fn begin_fork_progress(&self, child: Token, identity: ForkIdentity, stage: u32) -> Result {
        let mut slots = self.slots.lock();
        fork_progress_in_slots(self.owner, &mut slots, child, identity, stage)?;
        Ok(())
    }

    /// # Safety
    /// A module-pinned, typed verifier just established the requested actual
    /// alias/TLB or authenticated final in-band destructor proof for this key.
    /// No verifier/callback/borrowed pointer escapes into Remote state.
    pub(crate) unsafe fn finish_fork_progress(&self, child: Token, identity: ForkIdentity, stage: u32) -> Result {
        use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_ABORT_RETURN_V1};
        let mut slots = self.slots.lock();
        let (parent_index, child_index) = fork_progress_in_slots(self.owner, &mut slots, child, identity, stage)?;
        if stage == FORK_HOST_REVOKED_V1 {
            let parent_index = parent_index.ok_or(EIO)?;
            let record = &slots[child_index].as_ref().unwrap().fork.as_ref().unwrap().reservation;
            let first = record.first.clone();
            let value = record.return_value;
            slots[parent_index].as_mut().unwrap().syscalls.reconcile_fork_abort(
                identity.worker, identity.delivery, &first, value,
            ).map_err(errno)?;
            let record = &mut slots[child_index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
            // One publication lock atomically commits the terminal negative
            // metadata and its permission. No stale positive can pass between.
            record.return_value = Some(FORK_ABORT_RETURN_V1);
            if record.state.phase() == ForkPhase::Quarantined {
                unsafe { record.state.reconciled_quarantined_host_revoke(identity) }?;
            } else {
                unsafe { record.state.host_revoked(identity, 0) }?;
            }
            drop(slots);
            return Ok(());
        }
        let record = &mut slots[child_index].as_mut().unwrap().fork.as_mut().unwrap().reservation;
        unsafe { record.state.guest_destroyed(identity) }?;
        record.state.acknowledge_destroyed(identity)?;
        // Exact final proof retires this never-scheduled reservation itself;
        // ordinary CLEANUP must not send another destructor for the same child.
        let retired = slots[child_index].take();
        drop(slots);
        // Structural PID/MM and retained Remote cycles drop outside all locks.
        drop(retired);
        Ok(())
    }
}
}
#[path="/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/positive-control-owner-1/fixture-link.rs"] mod fork_link; pub(crate) use fork_link::{PreparedLinkTicket,PreparedControlTicket};
#[path="/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/positive-control-owner-1/fixture-ingress.rs"] mod fork_ingress;

// Sole-thread setup of real mailboxes and real Memory response ownership.
fn entry(pid:i32,scheduled:bool)->Entry{Entry{cleanup:Exchange::new(0,0,pid).unwrap(),owner_slot:0,owner_generation:2,scheduled,closed:false,needs_cleanup:false,quarantined:false,prepare:scheduled.then_some(()),fork:None,fork_ingress:None,syscalls:Mailbox::new().unwrap(),fork_prepared_parent_refs:0,procfs:None,retirement:None}}
pub(crate) fn fixture(memory:&Arc<crate::smp_memory::storage::Memory>,request:Request)->(Arc<Remote>,Token,Token,u64,u64){
 let mut p=entry(101,true);let c=entry(102,false);let w=p.syscalls.open_worker(200).unwrap();p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();let(s,_)=p.syscalls.reserve(w).unwrap().unwrap();p.syscalls.copied(w,s,true).unwrap();let pt=p.key();let ct=c.key();
 let remote=Arc::new(Remote{owner:memory.owner,slots:Mutex::new(vec![Some(p),Some(c)]),transport_failed:AtomicBool::new(false),release_token:Token::allocate().unwrap(),releases:Mutex::new(Mailbox::new().unwrap())},0).unwrap();(remote,pt,ct,w,s)
}
pub(crate) fn delivered_concurrent_link(remote:&Remote,parent:Token,memory:&Arc<crate::smp_memory::storage::Memory>,request:Request)->(u64,u64){
 let mut slots=remote.slots.lock();let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();
 assert_eq!(p.syscalls.open_worker(201),Err(EBUSY));let w=p.syscalls.open_worker(202).unwrap();
 p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();let(s,_)=p.syscalls.reserve(w).unwrap().unwrap();p.syscalls.copied(w,s,true).unwrap();(w,s)
}
pub(crate) fn delivered(remote:&Remote,parent:Token,memory:&Arc<crate::smp_memory::storage::Memory>,request:Request)->(u64,u64){let mut slots=remote.slots.lock();let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();let w=p.syscalls.open_worker(201).unwrap();p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();let(s,_)=p.syscalls.reserve(w).unwrap().unwrap();p.syscalls.copied(w,s,true).unwrap();(w,s)}
pub(crate) fn return_actual(remote:&Remote,parent:Token,w:u64,s:u64,cpu:i64,value:i64)->Result{let mut slots=remote.slots.lock();authorize_fork_return(&slots,parent,w,s,cpu,value)?;let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();p.syscalls.return_value(w,s,cpu,value,|_|Ok(())).map_err(errno)?;record_fork_return(&mut slots,parent,w,s,value);Ok(())}
pub(crate) fn phase(remote:&Remote)->ForkPhase{remote.slots.lock()[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.state.phase()}
pub(crate) fn scheduled(remote:&Remote)->bool{remote.slots.lock()[1].as_ref().unwrap().scheduled}
// This is test-process retention, never a final runtime release protocol.
pub(crate) fn retain_fixture(remote:Arc<Remote>){std::mem::forget(remote);}
pub(crate) fn close_worker_actual(remote:&Remote,parent:Token,worker:u64){let mut slots=remote.slots.lock();let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();assert_eq!(p.syscalls.close_worker(worker),Err(EBUSY));abort_parent_forks(&mut slots,parent,Some(worker));}
pub(crate) fn corrupt_generation(remote:&Remote){remote.slots.lock()[1].as_mut().unwrap().owner_generation+=1;}
pub(crate) fn fork_present(remote:&Remote)->bool{remote.slots.lock()[1].as_ref().unwrap().fork.is_some()}
pub(crate) fn check_parent_pin(remote:&Arc<Remote>, parent:Token, child:Token) {
 let mut slots=remote.slots.lock();
 let p=slots.iter().flatten().find(|e|e.key()==parent).unwrap();
 assert_eq!(p.fork_prepared_parent_refs,1);
 assert!(!p.release_ready());
 let fork=slots.iter().flatten().find(|e|e.key()==child).unwrap().fork.as_ref().unwrap();
 let pin=fork.retained_parent.as_ref().expect("positive first return lost parent Entry pin");
 assert_eq!(pin.parent,parent); assert_eq!(pin.identity,fork.reservation.identity);
 assert_eq!(pin.reservation,fork.reservation.token.wire()); assert!(Arc::ptr_eq(&pin.remote,remote));
 let key=pin.identity;let token=pin.reservation;
 assert_eq!(retain_fork_parent_pin(remote,&mut slots,child,token,key),Err(EACCES));
 let mut bad=key;bad.parent=Token::allocate().unwrap().wire();
 assert_eq!(retain_fork_parent_pin(remote,&mut slots,child,token,bad),Err(EIO));
 let mut bad=key;bad.child=parent.wire();
 assert!(retain_fork_parent_pin(remote,&mut slots,child,token,bad).is_err());
 assert_eq!(slots.iter().flatten().find(|e|e.key()==parent).unwrap().fork_prepared_parent_refs,1);
 let phase=slots.iter().flatten().find(|e|e.key()==child).unwrap().fork.as_ref().unwrap().reservation.state.phase();
 drop(slots);
 assert_eq!(remote.begin_fork_progress(child,key,crate::application_abi::FORK_GUEST_DESTROYED_V1),Err(EBUSY));
 assert_eq!(remote.release_fork_ack(child,key,1),Err(EBUSY));
 let slots=remote.slots.lock();
 assert_eq!(slots.iter().flatten().find(|e|e.key()==child).unwrap().fork.as_ref().unwrap().reservation.state.phase(),phase);
 assert_eq!(slots.iter().flatten().find(|e|e.key()==parent).unwrap().fork_prepared_parent_refs,1);
}




pub(crate) fn control_state(remote:&Remote)->(u32,bool,bool,ForkPhase,u64) {
 let slots=remote.slots.lock(); let p=slots[0].as_ref().unwrap();let c=slots[1].as_ref().unwrap();let f=c.fork.as_ref().unwrap();
 (p.fork_prepared_parent_refs,f.control.is_some(),f.control.as_ref().is_some_and(fork_link::control_quarantined),f.reservation.state.phase(),fork_link::control_sequence(f.link.as_ref().unwrap()))
}
pub(crate) fn parent_count(remote:&Remote,n:u32){remote.slots.lock()[0].as_mut().unwrap().fork_prepared_parent_refs=n;}
pub(crate) fn check_control_owned(remote:&Arc<Remote>,parent:Token,child:Token,w:u64,s:u64,request:&Request){fork_link::check_control_owner(remote,parent,child,w,s,request)}
pub(crate) fn control_no_release(remote:&Remote,parent:Token,child:Token){
 let key=remote.slots.lock()[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.identity;
 let before=control_state(remote);assert_eq!(remote.begin_fork_progress(child,key,crate::application_abi::FORK_HOST_REVOKED_V1),Err(EBUSY));
 assert_eq!(remote.begin_fork_progress(child,key,crate::application_abi::FORK_GUEST_DESTROYED_V1),Err(EBUSY));
 assert_eq!(remote.release_fork_ack(child,key,1),Err(EBUSY));assert_eq!(control_state(remote),before);
 assert!(!remote.slots.lock()[0].as_ref().unwrap().release_ready());let _=parent;
}

pub(crate) fn transport_failure(remote:&Remote,on:bool){remote.transport_failed.store(on,Ordering::Relaxed);}
pub(crate) fn cancel_child(remote:&Remote,child:Token)->Result{let mut slots=remote.slots.lock();let token=slots.iter().flatten().find(|e|e.key()==child).unwrap().fork.as_ref().unwrap().reservation.token.wire();abort_fork_in_slots(&mut slots,child,token)}

}
use smp_application::*;
mod application_abi {
// SPDX-License-Identifier: GPL-2.0
//! Versioned, kernel-only application connection to the exact SMP OS owner.

use core::ffi::c_void;

pub(crate) const VERSION: u32 = 1;
pub(crate) const CLEANUP: u32 = 1;
pub(crate) const PREPARE: u32 = 2;
pub(crate) const LOOKUP: u32 = 3;
pub(crate) const TRANSFER: u32 = 4;
pub(crate) const WORKER_OPEN: u32 = 5;
pub(crate) const WORKER_CLOSE: u32 = 6;
pub(crate) const WAIT_SYSCALL: u32 = 7;
pub(crate) const COPIED_SYSCALL: u32 = 8;
pub(crate) const RETURN_SYSCALL: u32 = 9;
pub(crate) const START: u32 = 10;
pub(crate) const PAGER_SYSCALL: u32 = 11;
pub(crate) const CLEAR_SYSCALL: u32 = 12;
pub(crate) const CLEAR_DONE: u32 = 13;
pub(crate) const TID_TRANSFER: u32 = 14;

// TID_TRANSFER: worker/delivery/physical/direction in 32 kernel-only bytes,
// followed by the complete copied launcher TID array. The backend checks the
// exact Delivered nr-186 request, count and destination before any guest write.
// This does not complete the syscall; the original launcher RET still owns its
// result. Handles are taken only from the referenced current Linux worker.

// CLEAR: 40 kernel-only bytes: worker, delivery, accepted output, start, end.
// BEGIN returns the checked range from the retained nr-11 request and reserves
// in-kernel ownership. DONE replaces start with the actual Mirror::clear result
// and clears end; acceptance transfers completion to the continuing pump.
// The caller must retain its worker/MM/connection through the actual clear and
// submit DONE on both success and error. No user pointer or range is an input.

// PAGER: 32 kernel-only bytes, worker/delivery, accepted output, actual result.
// It consumes the exact reserved WAIT packet before any userspace copy. Its
// payload addresses come only from that retained packet, never from this ABI.

// Kernel-only buffers: WORKER_OPEN/CLOSE 16 bytes (tid/handle, output handle);
// WAIT 96 bytes (worker, delivery, original 80-byte copyout); COPIED 24 bytes
// (worker, delivery, successful-copy flag); RETURN 72 bytes (worker, delivery,
// cpu, value, copy destination/length, accepted output flag, up to 16 data bytes).
// Handles originate in the backend and remain attached to referenced Linux
// worker/MM owners. None of these handles are accepted from the user UAPI.

// SAFETY: IHK holds the OS operation guard and exact-generation/module lease.
// Success transfers a non-null, concurrency-safe connection; failure leaves
// output null. Acquisition may reserve resources but cannot publish guest work.
pub(crate) type Open = unsafe extern "C" fn(u32, u64, i32, *mut *mut c_void) -> i32;
// SAFETY: The connection and its owners remain live for every concurrent call.
// No OS operation/publication lock is held. Buffer, when a command defines one,
// is exclusive kernel storage borrowed only for this call, never a user pointer.
pub(crate) type Invoke = unsafe extern "C" fn(*mut c_void, u32, *mut u8, usize) -> i64;
// SAFETY: Called once after all invocations end. Close destroys the connection
// before IHK drops its lease. Published work must retain independent ownership.
pub(crate) type Close = unsafe extern "C" fn(*mut c_void);

// BEGIN PRIVATE FORK ADOPTION ABI V1
// Dedicated kernel-only callback ABI; Invoke commands 1-14 remain unchanged.
// Geometry follows the native prepare_process header (rpgtable, start, len).
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkGeometryV1 {
    pub(crate) root: u64,
    pub(crate) start: u64,
    pub(crate) length: u64,
}

// Scalar comparison keys, never ownership or addresses to dereference.
#[repr(C)]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ForkIdentityV1 {
    pub(crate) slot: u32,
    pub(crate) reserved0: u32,
    pub(crate) generation: u64,
    pub(crate) parent: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) child: u64,
    pub(crate) child_pid: i32,
    pub(crate) reserved1: u32,
    pub(crate) child_mm: u64,
    pub(crate) root: u64,
    pub(crate) start: u64,
    pub(crate) length: u64,
    pub(crate) nonce: u64,
}

// BORROWED only for one synchronous callback. The provider retains the actual
// PreparedForkLease, its preallocated flag, exact OS/module and admission hold.
// The consumer must not retain the descriptor, context, flag or any reference.
// After validating every identity/geometry field and before touching the MM,
// its non-Copy scoped capability may perform ONLY the inline Release store at
// the infallible VMA commit. No callback, allocation, lock or Drop runs there.
#[repr(C)]
pub(crate) struct ForkSealV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) sealed: *mut core::sync::atomic::AtomicBool,
}

pub(crate) type ForkAdoptConsumerV1 = unsafe extern "C" fn(*mut c_void, *mut ForkSealV1) -> i32;
// Both contexts are live successful opens of the same provider/OS generation.
// No operations, registry, provider or Remote slots lock spans this call or its
// consumer callback. The caller pins its consumer module and borrows stack
// context and both connections until callback return. All descriptor pointers
// are private borrowed kernel storage; no public user opcode is added.
pub(crate) type ForkAdoptV1 = unsafe extern "C" fn(
    *mut c_void,
    *mut c_void,
    *const ForkGeometryV1,
    Option<ForkAdoptConsumerV1>,
    *mut c_void,
) -> i32;
// END PRIVATE FORK ADOPTION ABI V1

// BEGIN PRIVATE FORK PROGRESS ABI V1
pub(crate) const FORK_HOST_REVOKED_V1: u32 = 1;
pub(crate) const FORK_GUEST_DESTROYED_V1: u32 = 2;
// An original do_fork consumes this terminal cancellation before final ACK.
// Do not use -ERESTARTSYS: the original child must be destroyed exactly once.
pub(crate) const FORK_ABORT_RETURN_V1: i64 = -125;

// SAFETY: A private typed context retains the exact Registration, referenced
// producer proof and caller Linux module for this synchronous borrow. Stage1
// runs only AFTER provider abort/drain and performs the real Mirror alias/TLB
// revoke before success. A retry may check that same cached non-Copy receipt.
// Stage2 accepts ONLY an authenticated original in-band caller's final thread
// AND VM destruction result2 for every immutable identity field. A host revoke
// receipt alone cannot construct that proof. No user pointer/bool is authority.
// No proof/context pointer may escape, and no dependent lock spans this call.
pub(crate) type ForkVerifyV1 = unsafe extern "C" fn(*mut c_void, *const ForkIdentityV1) -> i32;
// Dedicated private progress; this is never an application Invoke opcode.
// The child connection remains live and caller module-pinned through return.
// The provider owns the exact pending transaction and all phase transitions;
// it must call verify only outside OS/table/Remote locks, then revalidate.
pub(crate) type ForkProgressV1 = unsafe extern "C" fn(
    *mut c_void,
    *const ForkIdentityV1,
    u32,
    Option<ForkVerifyV1>,
    *mut c_void,
) -> i32;
// END PRIVATE FORK PROGRESS ABI V1

// BEGIN PRIVATE FORK CONSUMER CAPSULE ABI V1
// IHK acquires the consumer's Linux module reference BEFORE Construct. Seed is
// borrowed only for construction; successful non-null output transfers exactly
// one opaque consumer Box. Error with non-null output also transfers cleanup.
pub(crate) type ForkCapsuleConstructV1 = unsafe extern "C" fn(*mut c_void, *mut *mut c_void) -> i32;
// The actual PreparedForkLease supplies this full-key preview synchronously
// BEFORE any MM effect. It allocates storage only: actual ForkClaim/receipt
// validation remains mandatory for every later verifier/Accept. No phase0
// initializing entry permits progress. NULL/error transfer rules match v1.
pub(crate) type ForkInitialConstructV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, *mut *mut c_void,
) -> i32;
// IHK invokes Destroy outside every dependent lock while its own module pin is
// live, then calls module_put from IHK text after Destroy returns. No owned
// ModuleLease or Rust owner crosses this ABI, and consumer Drop releases none.
pub(crate) type ForkCapsuleDestroyV1 = unsafe extern "C" fn(*mut c_void);
// Only IHK calls Accept AFTER durable exact-key final ACK and backend Released.
// A matching already-accepted context is idempotent; failure retains context,
// module and OS/provider ownership for an Accept-only retry. This cannot itself
// run guest cleanup/destruction. No caller boolean grants final acceptance.
pub(crate) type ForkCapsuleAcceptV1 = unsafe extern "C" fn(*mut c_void, *const ForkIdentityV1) -> i32;
// END PRIVATE FORK CONSUMER CAPSULE ABI V1

// BEGIN PRIVATE FORK LINK ABI V1
// Borrowed only through one synchronous, module-pinned callback. The SAME
// preallocated gate permits OPEN(0)->CANCELLED(1) or OPEN(0)->SEALED(2).
// SEALED is irreversible: only this exact kind2/result0 transaction may retry.
#[repr(C)]
pub(crate) struct ForkLinkSealV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) second_worker: u64,
    pub(crate) second_delivery: u64,
    pub(crate) second_cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) carrier_physical: u64,
    pub(crate) carrier_sequence: u64,
    pub(crate) gate: *mut core::sync::atomic::AtomicU8,
}
// Full referenced child PID/MM/VMA validation precedes the ONLY inline gate
// CAS under MM write exclusion. No lock/allocation/callback/Drop under that CAS.
pub(crate) type ForkCapsuleLinkV1 = unsafe extern "C" fn(*mut c_void, *mut ForkLinkSealV1) -> i32;
// Backend derives the exact key/ticket first. IHK then claims its actual
// pending capsule/payload, invokes stored consumer verification, and calls the
// SAME trusted provider continuation while every owner/module pin stays live.
// Ticket/payload contexts are borrowed only until Finish returns; no callback
// pointer or stack context is stored. SEALED failures retain the durable ticket.
pub(crate) type ForkLinkFinishV1 = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;
pub(crate) type ForkLinkResolveV1 = unsafe extern "C" fn(
    *mut c_void, *mut ForkLinkSealV1, Option<ForkLinkFinishV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareLinkV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkLinkResolveV1>, *mut c_void,
) -> i32;
// END PRIVATE FORK LINK ABI V1

// BEGIN PRIVATE FORK PAYLOAD CAPSULE ABI V1
// Construct starts with a NULL output. Non-NULL transfers exactly one opaque
// context even on error; NULL on error guarantees no remaining claim/context.
// IHK reserves capsule storage BEFORE construction under its real independent
// admission/OS/provider hold. No owned Rust/module/OS lease crosses this ABI.
pub(crate) type ForkPayloadConstructV1 = unsafe extern "C" fn(*mut c_void, *mut *mut c_void) -> i32;
// 0 consumes the context/claim exactly once. Negative retains it unchanged;
// positive is a protocol error and retains it. IHK calls outside all guards,
// with provider ownership live until callback return. Abort is preseal only,
// BEFORE publication unfreeze; Complete additionally needs authenticated final
// destruction AND actual final RET publication, never stage2 proof alone.
pub(crate) type ForkPayloadDropV1 = unsafe extern "C" fn(*mut c_void) -> i32;
pub(crate) type ForkPayloadAttachV1 = unsafe extern "C" fn(
    *mut c_void, Option<ForkPayloadConstructV1>, *mut c_void,
    Option<ForkPayloadDropV1>, Option<ForkPayloadDropV1>, *mut *mut c_void,
) -> i32;
// BORROWED stack scope only. Seed/outparams/scope never escape synchronous
// attach. The returned context is borrowed under the live exact capsule epoch;
// all SMP ticket/ChildFork pointers must clear BEFORE Abort/Complete frees it.
#[repr(C)]
pub(crate) struct ForkPayloadScopeV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) slot: u32,
    pub(crate) reserved0: u32,
    pub(crate) generation: u64,
    pub(crate) epoch: u64,
    pub(crate) context: *mut c_void,
    pub(crate) attach: Option<ForkPayloadAttachV1>,
}
pub(crate) type ForkAdoptScopedV1 = unsafe extern "C" fn(
    *mut c_void, *mut c_void, *const ForkGeometryV1, *mut ForkPayloadScopeV1,
    Option<ForkAdoptConsumerV1>, *mut c_void,
) -> i32;
// END PRIVATE FORK PAYLOAD CAPSULE ABI V1

// BEGIN PRIVATE FORK FINALIZATION ABI V1
// The IHK claim, never the caller, selects its exact owned payload context.
// The provider materializes a short exclusive borrow only under its slots
// lock. Stage1 writes kind3/-125 before permitting the original negative RET.
pub(crate) type ForkProgressPayloadV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u32, Option<ForkVerifyV1>, *mut c_void,
    *mut c_void,
) -> i32;

// Borrowed metadata from the actual owned selector3 delivery. Header bytes
// alone are not a guest destruction proof; its trusted provider ticket must
// validate the retained carrier and original in-band checked result2 producer.
#[repr(C)]
pub(crate) struct ForkGuestAckV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) epoch: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) physical: u64,
    pub(crate) sequence: u64,
}
pub(crate) type ForkAckVerifyV1 = unsafe extern "C" fn(*mut c_void, *mut c_void) -> i32;
pub(crate) type ForkAckFinishV1 = unsafe extern "C" fn(*mut c_void) -> i32;
pub(crate) type ForkAckResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkGuestAckV1, Option<ForkAckVerifyV1>,
    Option<ForkAckFinishV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareAckV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkAckResolveV1>, *mut c_void,
) -> i32;
// These immutable registered callbacks validate the actual durable publication
// record and later retire that exact backend owner. IHK invokes neither under
// its table lock. Receipt contexts are synchronous borrows, never owned leases.
pub(crate) type ForkPublicationVerifyV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u64, *mut c_void,
) -> i32;
pub(crate) type ForkReleaseAckV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkIdentityV1, u64,
) -> i32;
// END PRIVATE FORK FINALIZATION ABI V1

// Distinct synchronous, park-only control ABI. No receipt/MM/terminal authority.
#[repr(C)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub(crate) struct ForkControlV1 {
    pub(crate) version: u32,
    pub(crate) bytes: u32,
    pub(crate) identity: ForkIdentityV1,
    pub(crate) epoch: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) cpu: i32,
    pub(crate) reserved: u32,
    pub(crate) physical: u64,
    pub(crate) response: u64,
}
// Payload is a shared metadata borrow owned by the exact IHK pending claim.
// No pointer, claim or ticket may escape either synchronous callback.
pub(crate) type ForkControlParkV1 = unsafe extern "C" fn(*mut c_void, *const c_void) -> i32;
pub(crate) type ForkControlResolveV1 = unsafe extern "C" fn(
    *mut c_void, *const ForkControlV1, Option<ForkControlParkV1>, *mut c_void,
) -> i32;
pub(crate) type ForkPrepareControlV1 = unsafe extern "C" fn(
    *mut c_void, u64, u64, i64, i64, Option<ForkControlResolveV1>, *mut c_void,
) -> i32;

}
struct BridgeRuntime{application:Arc<Remote>}
mod memory{pub(crate) mod service{use crate::*;pub(crate) use crate::smp_memory::storage as memory;struct Started{runtime:Arc<BridgeRuntime>}
pub(in super::super) struct Application {
    started: Started,
    token: application_rpc::Token,
}

impl Application{pub(crate) fn fixture(runtime:Arc<BridgeRuntime>,token:Token)->Self{Self{started:Started{runtime},token}}

    /// Both successful connections remain borrowed through callback return.
    /// No Remote slots, runtime or OS operation lock spans the consumer.
    pub(in super::super) unsafe fn adopt_fork(
        &self,
        child: &Self,
        geometry: super::super::application_abi::ForkGeometryV1,
        consumer: super::super::application_abi::ForkAdoptConsumerV1,
        context: *mut core::ffi::c_void,
    ) -> Result {
        use super::super::application_abi::{ForkIdentityV1, ForkSealV1, VERSION};
        // Identity equality, not matching scalar labels, establishes the actual
        // continuing Runtime and Remote authority before preparation effects.
        if !Arc::ptr_eq(&self.started.runtime, &child.started.runtime)
            || !Arc::ptr_eq(
                &self.started.runtime.application,
                &child.started.runtime.application,
            )
        {
            return Err(EACCES);
        }
        let mut lease = self.started.runtime.application.prepare_fork(
            self.token,
            child.token,
            super::super::smp_application_image::ForkGeometry {
                root: geometry.root,
                start: geometry.start,
                length: geometry.length,
            },
        )?;
        let (status, sealed) = {
            let borrowed = lease.borrow_seal();
            let key = borrowed.identity;
            let mut descriptor = ForkSealV1 {
                version: VERSION,
                bytes: core::mem::size_of::<ForkSealV1>() as u32,
                identity: ForkIdentityV1 {
                    slot: key.slot,
                    reserved0: 0,
                    generation: key.generation,
                    parent: key.parent,
                    worker: key.worker,
                    delivery: key.delivery,
                    child: key.child,
                    child_pid: key.child_pid,
                    reserved1: 0,
                    child_mm: key.child_mm as u64,
                    root: key.root,
                    start: key.start,
                    length: key.length,
                    nonce: key.nonce,
                },
                // The consumer obtains atomic interior mutability only. This
                // is the exact producer flag, never an alternate acknowledgement.
                sealed: core::ptr::from_ref(borrowed.sealed).cast_mut(),
            };
            // SAFETY: The non-Copy borrow pins the real lease's exact atomic
            // for this synchronous callback. IHK retains independent admission
            // and exact OS/provider ownership; mcctrl retains its module/MM.
            let status = unsafe { consumer(context, &mut descriptor) };
            (status, borrowed.sealed.load(Ordering::Acquire))
        };
        // All consumer MM/local guards have ended before any lease destructor,
        // Remote lock, allocation or cancellation processing may run here.
        if status == 0 && sealed {
            lease.finish();
            Ok(())
        } else {
            drop(lease); // Sealed error quarantines; unsealed error aborts.
            Err(errno(if (-4095..0).contains(&status) { status } else { -71 }))
        }
    }

    /// # Safety
    /// IHK lends its genuine initializing payload scope and both live
    /// connections. The carrier owns the actual provisional/Prepared lease;
    /// unsealed rollback consumes its payload BEFORE publication can unfreeze.
    pub(in super::super) unsafe fn adopt_fork_scoped(
        &self, child: &Self,
        geometry: super::super::application_abi::ForkGeometryV1,
        scope: &super::super::application_abi::ForkPayloadScopeV1,
        consumer: super::super::application_abi::ForkAdoptConsumerV1,
        context: *mut core::ffi::c_void,
    ) -> Result {
        use super::super::application_abi::{ForkIdentityV1, ForkSealV1, VERSION};
        if !Arc::ptr_eq(&self.started.runtime, &child.started.runtime)
            || !Arc::ptr_eq(&self.started.runtime.application, &child.started.runtime.application)
        { return Err(EACCES); }
        let mut carrier = unsafe { self.started.runtime.application.prepare_fork_carrier(
            self.token, child.token,
            super::super::smp_application_image::ForkGeometry {
                root: geometry.root, start: geometry.start, length: geometry.length,
            }, scope,
        ) }?;
        let (status, sealed) = {
            let borrowed = carrier.borrow_seal();
            let key = borrowed.identity;
            let mut descriptor = ForkSealV1 {
                version: VERSION, bytes: core::mem::size_of::<ForkSealV1>() as u32,
                identity: ForkIdentityV1 {
                    slot: key.slot, reserved0: 0, generation: key.generation,
                    parent: key.parent, worker: key.worker, delivery: key.delivery,
                    child: key.child, child_pid: key.child_pid, reserved1: 0,
                    child_mm: key.child_mm as u64, root: key.root, start: key.start,
                    length: key.length, nonce: key.nonce,
                },
                sealed: core::ptr::from_ref(borrowed.sealed).cast_mut(),
            };
            let status = unsafe { consumer(context, &mut descriptor) };
            (status, borrowed.sealed.load(Ordering::Acquire))
        };
        if status == 0 && sealed {
            // This publishes actual IHK ownership before a same-slots-lock
            // checked fixed first receipt/READY commit may permit first RET.
            carrier.finish()
        } else {
            drop(carrier);
            Err(errno(if (-4095..0).contains(&status) { status } else { -71 }))
        }
    }

    /// # Safety
    /// The registered IHK resolver owns the exact pending capsule/payload
    /// borrow through the synchronous SAME-ticket Finish continuation.
pub(in super::super) unsafe fn prepare_fork_control(
        &self, worker: u64, serial: u64, cpu: i64, value: i64,
        resolve: super::super::application_abi::ForkControlResolveV1, context: *mut core::ffi::c_void,
    ) -> Result<bool> {
        let Some(mut ticket) = self.started.runtime.application.begin_fork_control(
            self.token, worker, serial, cpu, value,
        )? else { return Ok(false); };
        let descriptor = ticket.descriptor();
        let status = unsafe { resolve(context, &descriptor, Some(Self::park_fork_control_scope),
            core::ptr::from_mut(&mut ticket).cast()) };
        if status != 0 {
            ticket.quarantine_if_parked();
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        Ok(true)
    }
unsafe extern "C" fn park_fork_control_scope(ticket: *mut core::ffi::c_void,
        payload: *const core::ffi::c_void) -> i32 {
        if ticket.is_null() || payload.is_null() { return EINVAL.to_errno(); }
        let ticket = unsafe { &mut *ticket.cast::<super::super::smp_application::PreparedControlTicket>() };
        let payload = unsafe { &*payload.cast::<memory::ForkPayload>() };
        unsafe { ticket.park(payload) }.map_or_else(|e| e.to_errno(), |()| 0)
    }
    pub(in super::super) unsafe fn prepare_fork_link(
        &self, worker: u64, serial: u64, cpu: i64, value: i64,
        resolver: super::super::application_abi::ForkLinkResolveV1,
        context: *mut core::ffi::c_void,
    ) -> Result {
        let Some(mut ticket) = self.started.runtime.application.begin_fork_link(
            self.token, worker, serial, cpu, value,
        )? else { return Ok(()); };
        let mut descriptor = ticket.descriptor();
        let status = unsafe { resolver(context, &mut descriptor,
            Some(Self::finish_fork_link_scope), core::ptr::from_mut(&mut ticket).cast()) };
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        kernel::error::to_result(status)
    }

    unsafe extern "C" fn finish_fork_link_scope(
        ticket: *mut core::ffi::c_void, payload: *mut core::ffi::c_void,
    ) -> i32 {
        if ticket.is_null() || payload.is_null() { return EINVAL.to_errno(); }
        // SAFETY: Only this module's registered producer supplies the live
        // stack ticket; only IHK lends its exact owned payload context while
        // every provider/consumer/OS pin and exclusive pending claim is live.
        let ticket = unsafe { &mut *ticket.cast::<super::super::smp_application::PreparedLinkTicket>() };
        let payload = unsafe { &mut *payload.cast::<memory::ForkPayload>() };
        unsafe { ticket.finish_with_payload(payload) }.map_or_else(|e| e.to_errno(), |()| 0)
    }
    /// # Safety
    /// The caller pins its actual proof context/module and successful child
    /// connection for this synchronous borrow. Proof callbacks retain no ABI
    /// pointers and can manufacture neither a host nor guest scalar receipt.
    pub(in super::super) unsafe fn fork_progress(
        &self, identity: super::super::application_abi::ForkIdentityV1, stage: u32,
        verify: super::super::application_abi::ForkVerifyV1, context: *mut core::ffi::c_void,
    ) -> Result {
        use super::super::application_abi::{FORK_HOST_REVOKED_V1, FORK_GUEST_DESTROYED_V1};
        if identity.reserved0 != 0 || identity.reserved1 != 0
            || !matches!(stage, FORK_HOST_REVOKED_V1 | FORK_GUEST_DESTROYED_V1)
        { return Err(EINVAL); }
        let key = super::super::smp_application_image::ForkIdentity {
            slot: identity.slot, generation: identity.generation, parent: identity.parent,
            worker: identity.worker, delivery: identity.delivery, child: identity.child,
            child_pid: identity.child_pid, child_mm: identity.child_mm as usize,
            root: identity.root, start: identity.start, length: identity.length, nonce: identity.nonce,
        };
        let remote = &self.started.runtime.application;
        remote.begin_fork_progress(self.token, key, stage)?;
        // Provider/OS/table/slots guards all ended BEFORE real MM revocation or
        // final guest-proof validation. Stage1 has closed real admissions and
        // proved original response ownership; it remains frozen until finish.
        let status = unsafe { verify(context, &identity) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        // SAFETY: The actual typed verifier established this exact proof. The
        // backend rechecks the full key, actual service drain and response.
        unsafe { remote.finish_fork_progress(self.token, key, stage) }
    }
    
}}}

// SAFETY: IHK validates two live exact-generation connections and retains the
// registered provider module, independent OS admission and both connections.
// The geometry and context are kernel-only synchronous borrows, never user UAPI.
unsafe extern "C" fn application_adopt_fork(
    parent: *mut core::ffi::c_void,
    child: *mut core::ffi::c_void,
    geometry: *const application_abi::ForkGeometryV1,
    consumer: Option<application_abi::ForkAdoptConsumerV1>,
    context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() || child.is_null() || geometry.is_null() {
        return EINVAL.to_errno();
    }
    let Some(consumer) = consumer else { return EINVAL.to_errno(); };
    // SAFETY: Only actual successful Application contexts cross this registered
    // callback; their connections and the geometry borrow outlive this call.
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    let child = unsafe { &*child.cast::<smp_memory::Application>() };
    let geometry = unsafe { *geometry };
    // SAFETY: The caller pins the scoped consumer and its context until return.
    unsafe { parent.adopt_fork(child, geometry, consumer, context) }
        .map_or_else(|error| error.to_errno(), |()| 0)
}
// The child is a borrowed successful Application open. IHK independently
// claims/pins the exact pending owner before dispatch, without a held lock.
unsafe extern "C" fn application_fork_progress(
    child: *mut core::ffi::c_void,
    identity: *const application_abi::ForkIdentityV1,
    stage: u32,
    verify: Option<application_abi::ForkVerifyV1>,
    context: *mut core::ffi::c_void,
) -> i32 {
    if child.is_null() || identity.is_null() { return EINVAL.to_errno(); }
    let Some(verify) = verify else { return EINVAL.to_errno(); };
    let child = unsafe { &*child.cast::<smp_memory::Application>() };
    let identity = unsafe { *identity };
    // SAFETY: The exact child and typed proof context/module are synchronous
    // retained borrows. Application revalidates its actual token/runtime.
    unsafe { child.fork_progress(identity, stage, verify, context) }
        .map_or_else(|error| error.to_errno(), |()| 0)
}

unsafe extern "C" fn application_adopt_fork_scoped(
    parent: *mut core::ffi::c_void, child: *mut core::ffi::c_void,
    geometry: *const application_abi::ForkGeometryV1,
    scope: *mut application_abi::ForkPayloadScopeV1,
    consumer: Option<application_abi::ForkAdoptConsumerV1>, context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() || child.is_null() || geometry.is_null() || scope.is_null() { return EINVAL.to_errno(); }
    let Some(consumer) = consumer else { return EINVAL.to_errno(); };
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    let child = unsafe { &*child.cast::<smp_memory::Application>() };
    unsafe { parent.adopt_fork_scoped(child, *geometry, &*scope, consumer, context) }
        .map_or_else(|e| e.to_errno(), |()| 0)
}

unsafe extern "C" fn application_prepare_fork_control(
    parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64,
    resolver: Option<application_abi::ForkControlResolveV1>, context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() { return EINVAL.to_errno(); }
    let Some(resolver) = resolver else { return EINVAL.to_errno(); };
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    unsafe { parent.prepare_fork_control(worker, serial, cpu, value, resolver, context) }
        .map_or_else(|e| e.to_errno(), |parked| i32::from(parked))
}
unsafe extern "C" fn application_prepare_fork_link(
    parent: *mut core::ffi::c_void, worker: u64, serial: u64, cpu: i64, value: i64,
    resolver: Option<application_abi::ForkLinkResolveV1>, context: *mut core::ffi::c_void,
) -> i32 {
    if parent.is_null() { return EINVAL.to_errno(); }
    let Some(resolver) = resolver else { return EINVAL.to_errno(); };
    let parent = unsafe { &*parent.cast::<smp_memory::Application>() };
    unsafe { parent.prepare_fork_link(worker, serial, cpu, value, resolver, context) }
        .map_or_else(|e| e.to_errno(), |()| 0)
}

// Source-only scaffold: exact current provider-runtime bodies; Linux registry/allocator/module adapters explicit.
// Requires surrounding actual Remote, Application, memory, ABI and mutex scaffolds; contains no scenarios/tests or fake carrier.
mod provider_runtime {
    use super::*;
    use std::marker::PhantomData;
    struct Box<T>(std::boxed::Box<T>);
    impl<T> Box<T> {
        fn new(value:T,_:u32)->std::result::Result<Self,AllocError>{Ok(Self(std::boxed::Box::new(value)))}
        fn into_raw(value:Self)->*mut T{std::boxed::Box::into_raw(value.0)}
        unsafe fn from_raw(value:*mut T)->Self{Self(unsafe{std::boxed::Box::from_raw(value)})}
    }
    impl<T> std::ops::Deref for Box<T>{type Target=T;fn deref(&self)->&T{&self.0}}
    #[derive(Clone,Copy,Eq,PartialEq)]
    struct OsHandle { minor:usize,generation:u64 }
    impl OsHandle { fn minor(self)->usize{self.minor}fn generation(self)->u64{self.generation} }
    enum OsStatus { Ready,Running }
    struct Snapshot {status:OsStatus}
    #[derive(Debug)]
    struct RegistryError;
    impl RegistryError {fn errno(&self)->i32{-116}}
    struct OsRegistry {refs:[AtomicUsize;4]}
    static OS_REGISTRY:OsRegistry=OsRegistry{refs:[const{AtomicUsize::new(0)};4]};
    impl OsRegistry {
        fn acquire(&'static self,handle:OsHandle)->std::result::Result<OsLease<'static>,RegistryError>{
            if handle.minor>=4 || handle.generation==0{return Err(RegistryError)}
            self.refs[handle.minor].fetch_add(1,Ordering::SeqCst);
            Ok(OsLease{handle,_life:PhantomData})
        }
        fn snapshot(&self,_:OsHandle)->std::result::Result<Snapshot,RegistryError>{Ok(Snapshot{status:OsStatus::Running})}
    }
    struct OsLease<'a>{handle:OsHandle,_life:PhantomData<&'a OsRegistry>}
    impl OsLease<'_>{fn handle(&self)->OsHandle{self.handle}}
    impl Drop for OsLease<'_>{fn drop(&mut self){assert!(OS_REGISTRY.refs[self.handle.minor].fetch_sub(1,Ordering::SeqCst)>0)}}
    struct Admission {
    word: AtomicU32,
}

const ADMISSION_CLOSED: u32 = 1 << 31;
const ADMISSION_OVERFLOW: u32 = 1 << 30;
const ADMISSION_COUNT_MASK: u32 = !(ADMISSION_CLOSED | ADMISSION_OVERFLOW);

impl Admission {
    const fn new() -> Self {
        Self {
            word: AtomicU32::new(0),
        }
    }

    /// Acquire one callback/context admission.  A full count permanently
    /// closes and poisons the gate, rather than wrapping to zero and admitting
    /// a callback that shutdown could no longer observe.
    fn enter(&self) -> Result<AdmissionOwner> {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & (ADMISSION_CLOSED | ADMISSION_OVERFLOW) != 0 {
                return Err(EBUSY);
            }
            let count = current & ADMISSION_COUNT_MASK;
            if count == ADMISSION_COUNT_MASK {
                let _ = self.word.compare_exchange(
                    current,
                    current | ADMISSION_CLOSED | ADMISSION_OVERFLOW,
                    Ordering::AcqRel,
                    Ordering::Acquire,
                );
                return Err(EBUSY);
            }
            if self
                .word
                .compare_exchange(current, current + 1, Ordering::AcqRel, Ordering::Acquire)
                .is_ok()
            {
                return Ok(AdmissionOwner {
                    admission: ptr::from_ref(self),
                });
            }
        }
    }

    /// Close admission for one shutdown attempt. This is called only under the
    /// per-OS operation mutex, which is also the order used by serialized
    /// application/topology callbacks. An idle close left by an earlier
    /// successful shutdown can be claimed for cleanup retry after a failed
    /// reboot; an overflow poison can never be claimed or reopened.
    fn close_for_shutdown(&self) -> Result<ShutdownAdmission> {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & ADMISSION_OVERFLOW != 0 {
                return Err(EBUSY);
            }
            let count = current & ADMISSION_COUNT_MASK;
            if current & ADMISSION_CLOSED != 0 {
                if count != 0 {
                    return Err(EBUSY);
                }
                return Ok(ShutdownAdmission {
                    admission: ptr::from_ref(self),
                    reopen_on_drop: false,
                    armed: true,
                });
            }
            if self
                .word
                .compare_exchange(
                    current,
                    current | ADMISSION_CLOSED,
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .is_ok()
            {
                if count != 0 {
                    // The close was ours, so it is safe to undo immediately.
                    // Do not wait for drain: shutdown reports bounded EBUSY.
                    self.reopen_unpoisoned();
                    return Err(EBUSY);
                }
                return Ok(ShutdownAdmission {
                    admission: ptr::from_ref(self),
                    reopen_on_drop: true,
                    armed: true,
                });
            }
        }
    }

    /// Reopen a non-poisoned gate. Only a ShutdownAdmission that changed the
    /// gate from open to closed may call this on a pre-effect failure; a
    /// successful boot also calls it after Ready is committed.
    fn reopen_unpoisoned(&self) {
        loop {
            let current = self.word.load(Ordering::Acquire);
            if current & ADMISSION_OVERFLOW != 0 {
                return;
            }
            if self
                .word
                .compare_exchange(
                    current,
                    current & !ADMISSION_CLOSED,
                    Ordering::Release,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                return;
            }
        }
    }

    fn is_closed(&self) -> bool {
        self.word.load(Ordering::Acquire) & ADMISSION_CLOSED != 0
    }
}

    #[must_use = "a shutdown close claim must commit or restore admission"]
struct ShutdownAdmission {
    admission: *const Admission,
    reopen_on_drop: bool,
    armed: bool,
}

impl ShutdownAdmission {
    /// Leave the gate closed after the successful shutdown effect/registry
    /// commit, or after an impossible post-effect registry corruption.
    fn commit(mut self) {
        self.armed = false;
    }
}

impl Drop for ShutdownAdmission {
    fn drop(&mut self) {
        if !self.armed || !self.reopen_on_drop {
            return;
        }
        // SAFETY: The operation mutex and caller's OsLease retain the object
        // through the complete shutdown transaction.
        unsafe { &*self.admission }.reopen_unpoisoned();
    }
}

    #[must_use = "an admitted callback/context must release its admission owner"]
struct AdmissionOwner {
    admission: *const Admission,
}

impl Drop for AdmissionOwner {
    fn drop(&mut self) {
        // SAFETY: See the type-level lifetime contract above. The object and
        // its Admission remain live until this owner has dropped.
        let admission = unsafe { &*self.admission };
        loop {
            let current = admission.word.load(Ordering::Acquire);
            let count = current & ADMISSION_COUNT_MASK;
            if count == 0 {
                // Never underflow into a false live count. This is reachable
                // only after a trusted owner lifetime violation.
                return;
            }
            if admission
                .word
                .compare_exchange(current, current - 1, Ordering::Release, Ordering::Relaxed)
                .is_ok()
            {
                return;
            }
        }
    }
}

    #[derive(Clone,Copy)]
    struct ApplicationCallbacks {
    open: super::application_abi::Open,
    invoke: super::application_abi::Invoke,
    close: super::application_abi::Close,
    adopt_fork: Option<super::application_abi::ForkAdoptV1>,
    fork_progress: Option<super::application_abi::ForkProgressV1>,
    adopt_fork_scoped: Option<super::application_abi::ForkAdoptScopedV1>,
    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,
    fork_progress_payload: Option<super::application_abi::ForkProgressPayloadV1>,
    prepare_fork_ack: Option<super::application_abi::ForkPrepareAckV1>,
    fork_publication_verify: Option<super::application_abi::ForkPublicationVerifyV1>,
    release_fork_ack: Option<super::application_abi::ForkReleaseAckV1>,
    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,
}
    #[derive(Clone,Copy)]
    struct Backend {application:Option<ApplicationCallbacks>}
    struct OsObject {admission:Admission,backend:Option<Backend>,forks:Mutex<ForkPendingTable>}
    static OS_OBJECTS:[AtomicPtr<OsObject>;4]=[const{AtomicPtr::new(ptr::null_mut())};4];
    struct BackendApplication {
    context: ptr::NonNull<c_void>,
    callbacks: ApplicationCallbacks,
}

// SAFETY: The registered callback contract supplies a concurrency-safe opaque
// owner. Only invoke borrows it; final Drop follows the last such borrow.
unsafe impl Send for BackendApplication {}
// SAFETY: The same registered opaque owner permits shared references; invoke
// serializes its callback contract, and final Drop follows every such borrow.
unsafe impl Sync for BackendApplication {}

impl Drop for BackendApplication {
    fn drop(&mut self) {
        // SAFETY: This successful open is uniquely owned and its OS/module
        // lease is the later-dropping field of ApplicationConnection.
        unsafe { (self.callbacks.close)(self.context.as_ptr()) };
    }
}

struct ApplicationConnection {
    backend: BackendApplication,
    // BackendApplication drops first so its close callback retains admission;
    // this owner then drops before the exact OS lease/module release.
    _admission: AdmissionOwner,
    _lease: OsLease<'static>,
}

    fn to_result(status:i32)->Result{if status<0{Err(status)}else{Ok(())}}
    mod bindings {#[allow(non_camel_case_types)]pub(crate) struct module;}
    static CONSUMER_MODULE:bindings::module=bindings::module;
    static MODULE_PINS:AtomicU32=AtomicU32::new(0);
    static MODULE_GET_FAIL:AtomicBool=AtomicBool::new(false);
    static MODULE_ARC_FAIL_AFTER_GET:AtomicBool=AtomicBool::new(false);
    static MODULE_EVENTS:std::sync::Mutex<std::vec::Vec<&'static str>>=std::sync::Mutex::new(std::vec::Vec::new());
    unsafe fn try_module_get(_: *mut c_void)->bool{
        LOCK_DEPTH.with(|depth|assert_eq!(depth.get(),0));
        if MODULE_GET_FAIL.swap(false,Ordering::SeqCst){MODULE_EVENTS.lock().unwrap().push("get_failed");return false;}
        MODULE_PINS.fetch_add(1,Ordering::SeqCst);MODULE_EVENTS.lock().unwrap().push("get");if MODULE_ARC_FAIL_AFTER_GET.swap(false,Ordering::SeqCst){ARC_FAIL_NEXT.store(true,Ordering::SeqCst);}true
    }
    unsafe fn module_put(_: *mut c_void){
        LOCK_DEPTH.with(|depth|assert_eq!(depth.get(),0));MM_ACTIVE.with(|active|assert!(!active.get()));
        assert!(FORK_PROVIDER_OWNER_COUNT.load(Ordering::SeqCst)>0,"provider owner dropped before consumer module put");
        MODULE_EVENTS.lock().unwrap().push("put");assert!(MODULE_PINS.fetch_sub(1,Ordering::SeqCst)>0);
    }
    #[must_use = "the module reference must remain owned until OS destruction"]
pub(super) struct ProviderModule(*mut bindings::module);

impl ProviderModule {
    /// # Safety
    /// `module` must be a valid Linux module pointer whose allocation remains
    /// live throughout this call. A pinned control file or a registration lock
    /// excluding the owner's unregister/exit supplies that lifetime. It must
    /// never be a userspace value. A going-away module may refuse acquisition.
    pub(super) unsafe fn acquire(module: *mut bindings::module) -> Result<Self> {
        if module.is_null() {
            return Err(EINVAL);
        }
        // SAFETY: The caller keeps this Linux module allocation live for the call.
        if !unsafe { try_module_get(module.cast()) } {
            return Err(EBUSY);
        }
        Ok(Self(module))
    }
}

impl Drop for ProviderModule {
    fn drop(&mut self) {
        // SAFETY: This unique owner balances one successful try_module_get.
        // No callback into that module may continue after this final put.
        unsafe { module_put(self.0.cast()) };
    }
}


    
// A pending entry owns independent exact-generation admission/OS/provider
// ownership. All table access uses OsObject.forks; lookup clones an Arc while
// holding that mutex before it may release the guard. No raw table pointer is
// read outside exclusion. A monotonic epoch distinguishes every slot reuse.
const FORK_PROVIDER_CAPACITY: usize = 64;
const FORK_PROVIDER_PENDING: u32 = 1;
const FORK_PROVIDER_QUARANTINED: u32 = 2;
const FORK_PROVIDER_HOST_REVOKED: u32 = 3;
const FORK_PROVIDER_BUSY: u32 = 4;
static FORK_PROVIDER_OWNER_COUNT: AtomicU32 = AtomicU32::new(0);

struct ForkProviderCapacity;
impl ForkProviderCapacity {
    fn reserve() -> Result<Self> {
        FORK_PROVIDER_OWNER_COUNT.fetch_update(Ordering::AcqRel, Ordering::Acquire,
            |count| (count < FORK_PROVIDER_CAPACITY as u32).then(|| count + 1))
            .map_err(|_| EBUSY)?;
        Ok(Self)
    }
}
impl Drop for ForkProviderCapacity {
    fn drop(&mut self) {
        let old = FORK_PROVIDER_OWNER_COUNT.fetch_sub(1, Ordering::Release);
        assert!(old > 0);
    }
}

struct ForkProviderOwner {
    _admission: AdmissionOwner,
    _lease: OsLease<'static>,
    // Release aggregate capacity only AFTER admission and OS/module ownership.
    _capacity: ForkProviderCapacity,
}
// SAFETY: The exact lease pins Admission's address. All owner operations are
// immutable or atomic; final field destruction follows the last Arc borrow.
unsafe impl Send for ForkProviderOwner {}
// SAFETY: The pinned registry and admission support concurrent atomic borrows.
unsafe impl Sync for ForkProviderOwner {}

struct ForkConsumerCapsule {
    context: AtomicPtr<c_void>,
    destroy: super::application_abi::ForkCapsuleDestroyV1,
    verify: super::application_abi::ForkVerifyV1,
    accept: super::application_abi::ForkCapsuleAcceptV1,
    _link: Option<super::application_abi::ForkCapsuleLinkV1>,
    // Drop invokes the consumer first; this field releases its pin afterwards
    // from IHK code, with the independent provider owner still live.
    _module: ProviderModule,
}
// SAFETY: The trusted constructor supplies one owned concurrency-safe context;
// exact pending claims serialize verify/accept, and Arc pins final destruction.
unsafe impl Send for ForkConsumerCapsule {}
// SAFETY: Context access is confined to the exclusive epoch claim callbacks.
unsafe impl Sync for ForkConsumerCapsule {}
impl Drop for ForkConsumerCapsule {
    fn drop(&mut self) {
        // SAFETY: IHK uniquely owns the successful constructor output. Every
        // callback borrow has ended, no table/MM/slots guard is live, and the
        // later-dropping module field still pins this exact consumer code.
        let context = self.context.load(Ordering::Acquire);
        if !context.is_null() { unsafe { (self.destroy)(context) }; }
    }
}
#[derive(Clone, Copy, Eq, PartialEq)]
enum ForkReceiptPhase { Reserved, Acknowledged, Finished }

// Storage is allocated and installed BEFORE Construct transfers any context.
// Only scoped Abort/future authenticated Complete may consume that context.
// No ordinary Drop invokes foreign code or treats a failed cleanup as success.
struct ForkPayloadCapsule {
    context: AtomicPtr<c_void>,
    abort: super::application_abi::ForkPayloadDropV1,
    _complete: super::application_abi::ForkPayloadDropV1,
}
// SAFETY: Context is opaque; the exclusive initializing scope or exact BUSY
// claim serializes callbacks, and its owner pins the provider module.
unsafe impl Send for ForkPayloadCapsule {}
// SAFETY: Scalar context publication is atomic; no unsynchronized dereference.
unsafe impl Sync for ForkPayloadCapsule {}

struct ForkPendingEntry {
    identity: Option<super::application_abi::ForkIdentityV1>,
    epoch: u64,
    phase: u32,
    host_revoked: bool,
    guest_released: bool,
    final_published: bool, consumer_accepted: bool, payload_completed: bool, backend_released: bool,
    attempted: bool,
    receipt_index: Option<usize>,
    capsule: Option<Arc<ForkConsumerCapsule>>,
    payload: Option<Arc<ForkPayloadCapsule>>,
    child_context: usize,
    // Any entry teardown, including conservative reconciliation, destroys the
    // consumer capsule/module before releasing independent provider ownership.
    owner: Arc<ForkProviderOwner>,
}
#[derive(Clone, Copy)]
struct ForkCompletedReceipt {
    identity: super::application_abi::ForkIdentityV1,
    child_context: usize,
    epoch: u64,
    phase: ForkReceiptPhase,
}
struct ForkPendingTable {
    next_epoch: u64,
    entries: [Option<ForkPendingEntry>; FORK_PROVIDER_CAPACITY],
    completed: [Option<ForkCompletedReceipt>; FORK_PROVIDER_CAPACITY],
}
impl ForkPendingTable {
    fn new() -> Self {
        Self { next_epoch: 0, entries: [const { None }; FORK_PROVIDER_CAPACITY],
            completed: [None; FORK_PROVIDER_CAPACITY] }
    }
}

struct ForkProviderReservation {
    object: *const OsObject,
    index: usize,
    epoch: u64,
    owner: Arc<ForkProviderOwner>,
    active: bool,
}
impl ForkProviderReservation {
    fn reserve(object: &OsObject, owner: Arc<ForkProviderOwner>, child_context: usize) -> Result<Self> {
        let mut table = object.forks.lock();
        let index = table.entries.iter().position(Option::is_none).ok_or(EBUSY)?;
        let epoch = table.next_epoch.checked_add(1).ok_or(EOVERFLOW)?;
        table.next_epoch = epoch;
        table.entries[index] = Some(ForkPendingEntry {
            owner: owner.clone(), identity: None, epoch, phase: 0,
            host_revoked: false, guest_released: false, final_published: false, consumer_accepted: false, payload_completed: false, backend_released: false, attempted: false, receipt_index: None, capsule: None, payload: None, child_context,
        });
        drop(table);
        Ok(Self { object: ptr::from_ref(object), index, epoch, owner, active: true })
    }
    fn bind_identity(&self, identity: super::application_abi::ForkIdentityV1) -> Result {
        // SAFETY: Our owner lease pins the object/table until this Arc drops.
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || !Arc::ptr_eq(&entry.owner, &self.owner)
            || entry.phase != 0 || entry.identity.is_some()
        { return Err(EIO); }
        entry.identity = Some(identity);
        Ok(())
    }
    fn retain(mut self, quarantined: bool) {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        if let Some(entry) = table.entries[self.index].as_mut() {
            if entry.epoch == self.epoch && Arc::ptr_eq(&entry.owner, &self.owner) {
                if self.active && entry.phase == 0 {
                    entry.phase = if quarantined { FORK_PROVIDER_QUARANTINED } else { FORK_PROVIDER_PENDING };
                } else if !self.active && quarantined && entry.phase == FORK_PROVIDER_PENDING {
                    // Scoped ready may publish before backend return. Never
                    // overwrite a concurrent BUSY/advanced completion claim.
                    entry.phase = FORK_PROVIDER_QUARANTINED;
                }
            }
        }
        self.active = false;
    }
}
impl Drop for ForkProviderReservation {
    fn drop(&mut self) {
        if !self.active { return; }
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            if table.entries[self.index].as_ref().is_some_and(|entry|
                entry.epoch == self.epoch && Arc::ptr_eq(&entry.owner, &self.owner) && entry.phase == 0)
            {
                if table.entries[self.index].as_ref().unwrap().payload.is_some() {
                    // No exceptional preseal return may orphan a live carrier.
                    // Keep its exact reachable capsule and real owner until
                    // explicit scoped rollback consumed and detached it.
                    table.entries[self.index].as_mut().unwrap().phase = FORK_PROVIDER_QUARANTINED;
                    None
                } else { table.entries[self.index].take() }
            } else { None }
        };
        // All ownership destructors run after the table guard/callback ends.
        drop(removed);
    }
}

struct ForkPayloadScopeStack {
    reservation: *mut ForkProviderReservation,
    descriptor: *mut super::application_abi::ForkPayloadScopeV1,
    consumer: *const ForkConsumerScope,
    constructing: bool,
    cleaning: bool,
    rollback_ready: bool,
    // Default true: only the actual provider's completed scoped rollback may
    // clear uncertainty after removing claims/restoring its exact response.
    uncertain: bool,
}

unsafe fn fork_payload_scope_binding(scope: *mut super::application_abi::ForkPayloadScopeV1)
    -> Result<*mut ForkPayloadScopeStack>
{
    use super::application_abi::{ForkPayloadScopeV1, VERSION};
    if scope.is_null() { return Err(EINVAL); }
    let descriptor = unsafe { &*scope };
    if descriptor.version != VERSION || descriptor.bytes as usize != core::mem::size_of::<ForkPayloadScopeV1>()
        || descriptor.reserved0 != 0 || descriptor.context.is_null()
        || descriptor.attach.map(|f| f as usize) != Some(fork_payload_attach_scope as super::application_abi::ForkPayloadAttachV1 as usize)
    { return Err(EINVAL); }
    // SAFETY: This is an IHK-created stack context borrowed synchronously by
    // the registered provider, never wire/user storage or an owned lease.
    let stack = unsafe { &*descriptor.context.cast::<ForkPayloadScopeStack>() };
    if stack.descriptor != scope || stack.reservation.is_null() || stack.consumer.is_null() { return Err(EACCES); }
    let reservation = unsafe { &*stack.reservation };
    let handle = reservation.owner._lease.handle();
    if descriptor.slot as usize != handle.minor() || descriptor.generation != handle.generation()
        || descriptor.epoch != reservation.epoch || !reservation.active
    { return Err(EACCES); }
    Ok(descriptor.context.cast())
}

unsafe fn abort_fork_payload_scope(raw: *mut ForkPayloadScopeStack, rollback_ready: bool) -> Result {
    let stack = unsafe { &mut *raw };
    if stack.constructing || stack.cleaning { return Err(EBUSY); }
    let consumer = unsafe { &*stack.consumer };
    if consumer.active || consumer.sealed || consumer.uncertain { return Err(EBUSY); }
    let reservation = unsafe { &*stack.reservation };
    let object = unsafe { &*reservation.object };
    let capsule = {
        let table = object.forks.lock();
        let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0
            || !Arc::ptr_eq(&entry.owner, &reservation.owner)
        { return Err(EACCES); }
        entry.payload.clone()
    };
    if let Some(capsule) = capsule {
        let context = capsule.context.load(Ordering::Acquire);
        if !context.is_null() {
            // No MM/table/slots/registry guard spans foreign cleanup. The
            // original independent provider owner pins its code through return.
            stack.cleaning = true;
            // End the exclusive stack borrow BEFORE foreign code can reenter
            // this synchronous scope; reacquire only after callback return.
            let status = unsafe { (capsule.abort)(context) };
            let stack = unsafe { &mut *raw };
            stack.cleaning = false;
            if status != 0 {
                stack.uncertain = true;
                return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
            }
            capsule.context.store(ptr::null_mut(), Ordering::Release);
        }
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner)
                || !entry.payload.as_ref().is_some_and(|stored| Arc::ptr_eq(stored, &capsule))
            { return Err(EACCES); }
            entry.payload.take()
        };
        drop(removed);
        drop(capsule);
    }
    if rollback_ready {
        let stack = unsafe { &mut *raw };
        stack.rollback_ready = true;
        stack.uncertain = false;
    }
    Ok(())
}

unsafe extern "C" fn fork_payload_attach_scope(
    context: *mut c_void,
    construct: Option<super::application_abi::ForkPayloadConstructV1>, seed: *mut c_void,
    abort: Option<super::application_abi::ForkPayloadDropV1>,
    complete: Option<super::application_abi::ForkPayloadDropV1>, out: *mut *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        if context.is_null() || out.is_null() { return Err(EINVAL); }
        unsafe { out.write(ptr::null_mut()) };
        let descriptor = unsafe { (*context.cast::<ForkPayloadScopeStack>()).descriptor };
        let raw = unsafe { fork_payload_scope_binding(descriptor) }?;
        let stack = unsafe { &mut *raw };
        if raw.cast::<c_void>() != context || stack.constructing || stack.cleaning || stack.rollback_ready { return Err(EBUSY); }
        let consumer = unsafe { &*stack.consumer };
        if consumer.active || consumer.invoked || consumer.sealed || consumer.uncertain { return Err(EBUSY); }
        let construct = construct.ok_or(EINVAL)?;
        let abort = abort.ok_or(EINVAL)?;
        let complete = complete.ok_or(EINVAL)?;
        let reservation = unsafe { &*stack.reservation };
        let object = unsafe { &*reservation.object };
        {
            let table = object.forks.lock();
            let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.payload.is_some()
            { return Err(EBUSY); }
        }
        // Every fallible metadata allocation precedes owned context transfer.
        let capsule = Arc::new(ForkPayloadCapsule {
            context: AtomicPtr::new(ptr::null_mut()), abort, _complete: complete,
        }, GFP_KERNEL)?;
        {
            let mut table = object.forks.lock();
            let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
            if entry.epoch != reservation.epoch || entry.phase != 0
                || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.payload.is_some()
            { return Err(EBUSY); }
            entry.payload = Some(capsule.clone());
        }
        stack.constructing = true;
        let mut owned = ptr::null_mut();
        // No &mut stack borrow is kept across a potentially reentrant ctor.
        let status = unsafe { construct(seed, &mut owned) };
        // Capture even an error's non-NULL output into preallocated storage.
        capsule.context.store(owned, Ordering::Release);
        let stack = unsafe { &mut *raw };
        stack.constructing = false;
        if status != 0 || owned.is_null() {
            unsafe { abort_fork_payload_scope(raw, false) }?;
            return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
        }
        unsafe { out.write(owned) };
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Only the registered provider borrows this actual IHK stack scope. It has
/// cleared every payload pointer/borrow and restored its response/rollback
/// state, with provisional publication still frozen and no dependent guard.
/// No wire value or generic Drop may fabricate this rollback authority.
#[export_name = "ihk_os_application_abort_fork_payload_v1"]
pub(crate) unsafe extern "C" fn abort_fork_payload_application(
    scope: *mut super::application_abi::ForkPayloadScopeV1,
) -> i32 {
    let result = (|| -> Result {
        let stack = unsafe { fork_payload_scope_binding(scope) }?;
        unsafe { abort_fork_payload_scope(stack, true) }
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Called only by the actual registered provider after the MM callback/local
/// publication has returned, with its typed PreparedForkLease still prepared.
/// No dependent lock is live. This publishes IHK ownership before the SAME
/// slots-lock canonical first-write/READY transaction can permit first RET.
#[export_name = "ihk_os_application_ready_fork_payload_v1"]
pub(crate) unsafe extern "C" fn ready_fork_payload_application(
    scope: *mut super::application_abi::ForkPayloadScopeV1,
) -> i32 {
    let result = (|| -> Result {
        let raw = unsafe { fork_payload_scope_binding(scope) }?;
        let stack = unsafe { &mut *raw };
        if stack.constructing || stack.cleaning || stack.rollback_ready { return Err(EBUSY); }
        let consumer = unsafe { &*stack.consumer };
        if !consumer.invoked || consumer.active || !consumer.sealed || consumer.uncertain { return Err(EBUSY); }
        let reservation = unsafe { &mut *stack.reservation };
        let object = unsafe { &*reservation.object };
        let mut table = object.forks.lock();
        let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity.is_none()
            || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.attempted
            || entry.capsule.as_ref().is_none_or(|capsule| capsule.context.load(Ordering::Acquire).is_null())
            || entry.payload.as_ref().is_none_or(|capsule| capsule.context.load(Ordering::Acquire).is_null())
        { return Err(EBUSY); }
        let key = entry.identity.unwrap();
        if key.slot != consumer.slot || key.generation != consumer.generation
            || key.root != consumer.geometry.root || key.start != consumer.geometry.start
            || key.length != consumer.geometry.length
        { return Err(EACCES); }
        entry.phase = FORK_PROVIDER_PENDING;
        reservation.active = false;
        stack.uncertain = false;
        drop(table);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

struct ForkProviderClaim {
    object: *const OsObject,
    index: usize,
    epoch: u64,
    identity: super::application_abi::ForkIdentityV1,
    previous_phase: u32,
    guest_released: bool,
    attempted: bool,
    receipt_index: Option<usize>,
    // Capsule destruction/module_put precede the last provider owner release.
    capsule: Option<Arc<ForkConsumerCapsule>>,
    payload: Option<Arc<ForkPayloadCapsule>>,
    owner: Arc<ForkProviderOwner>,
    active: bool,
}
enum ForkClaimLookup { Pending(ForkProviderClaim), Completed }
impl ForkProviderClaim {
    // stage0 is private attachment/cancellation lookup, never a wire opcode.
    fn acquire(object: &OsObject, identity: super::application_abi::ForkIdentityV1,
        child_context: usize, stage: u32) -> Result<ForkClaimLookup>
    {
        let mut table = object.forks.lock();
        if stage == super::application_abi::FORK_GUEST_DESTROYED_V1
            && table.completed.iter().flatten().any(|receipt|
                receipt.identity == identity && receipt.child_context == child_context
                    && receipt.phase == ForkReceiptPhase::Finished)
        { return Ok(ForkClaimLookup::Completed); }
        let index = table.entries.iter().position(|entry| entry.as_ref().is_some_and(|entry|
            entry.identity == Some(identity) && entry.child_context == child_context)).ok_or(ENOENT)?;
        let entry = table.entries[index].as_ref().unwrap();
        if stage == super::application_abi::FORK_HOST_REVOKED_V1 && entry.host_revoked {
            return Ok(ForkClaimLookup::Completed);
        }
        if entry.phase == 0 || entry.phase == FORK_PROVIDER_BUSY
            || stage == super::application_abi::FORK_GUEST_DESTROYED_V1 && !entry.host_revoked
        { return Err(EBUSY); }
        if stage != 0 && entry.capsule.is_none() { return Err(ENODEV); }
        // Completion receipts have an independent lifetime from pending slots.
        // Reserve before the first revoke effect; Finished cells are never
        // evicted by pending-slot reuse. Until authenticated receipt retirement
        // exists, exhaustion deliberately retains ownership and fails closed.
        let receipt_index = if stage != 0 {
            if let Some(receipt_index) = entry.receipt_index {
                let receipt = table.completed[receipt_index].as_ref().ok_or(EIO)?;
                if receipt.epoch != entry.epoch || receipt.identity != identity
                    || receipt.child_context != child_context
                    || receipt.phase == ForkReceiptPhase::Finished
                { return Err(EIO); }
                Some(receipt_index)
            } else {
                if stage != super::application_abi::FORK_HOST_REVOKED_V1 { return Err(EIO); }
                let receipt_index = table.completed.iter().position(Option::is_none).ok_or(EBUSY)?;
                let epoch = entry.epoch;
                table.completed[receipt_index] = Some(ForkCompletedReceipt { identity, child_context,
                    epoch, phase: ForkReceiptPhase::Reserved });
                table.entries[index].as_mut().unwrap().receipt_index = Some(receipt_index);
                Some(receipt_index)
            }
        } else { entry.receipt_index };
        let entry = table.entries[index].as_mut().unwrap();
        let claim = Self { object: ptr::from_ref(object), index, epoch: entry.epoch,
            identity, previous_phase: entry.phase, guest_released: entry.guest_released,
            attempted: entry.attempted, receipt_index, capsule: entry.capsule.clone(), payload: entry.payload.clone(), owner: entry.owner.clone(), active: true };
        entry.phase = FORK_PROVIDER_BUSY;
        if stage == super::application_abi::FORK_HOST_REVOKED_V1 { entry.attempted = true; }
        drop(table);
        Ok(ForkClaimLookup::Pending(claim))
    }
fn acquire_control(object: &OsObject, identity: super::application_abi::ForkIdentityV1,
        child_context: usize, epoch: u64) -> Result<Self> {
        let mut table = object.forks.lock();
        let index = table.entries.iter().position(|e| e.as_ref().is_some_and(|e|
            e.identity == Some(identity) && e.child_context == child_context && e.epoch == epoch)).ok_or(ENOENT)?;
        let entry = table.entries[index].as_mut().unwrap();
        if epoch == 0 || entry.phase != FORK_PROVIDER_PENDING || entry.host_revoked || entry.guest_released
            || entry.attempted || entry.capsule.is_none() || entry.payload.is_none()
            || entry.final_published || entry.consumer_accepted || entry.payload_completed || entry.backend_released
        { return Err(EBUSY); }
        let claim = Self { object: ptr::from_ref(object), index, epoch, identity,
            previous_phase: entry.phase, guest_released: entry.guest_released,
            attempted: entry.attempted, receipt_index: entry.receipt_index,
            capsule: entry.capsule.clone(), payload: entry.payload.clone(), owner: entry.owner.clone(), active: true };
        entry.phase = FORK_PROVIDER_BUSY;
        Ok(claim)
    }
fn restore_control(mut self) -> Result {
        let result = {
            let object = unsafe { &*self.object };
            let mut table = object.forks.lock();
            match table.entries[self.index].as_mut() {
                Some(entry) if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                    && Arc::ptr_eq(&entry.owner, &self.owner) => {
                    if entry.phase == FORK_PROVIDER_BUSY && self.previous_phase == FORK_PROVIDER_PENDING {
                        entry.phase = FORK_PROVIDER_PENDING;
                        self.active = false;
                        Ok(())
                    } else {
                        entry.phase = FORK_PROVIDER_QUARANTINED;
                        Err(EIO)
                    }
                },
                _ => Err(EIO),
            }
        };
        // No table/Remote/MM guard is held. Forgetting this original claim
        // retains its OS/admission/capsule/module owners; no foreign Drop or
        // arbitrary decrement may run on a mismatched/reused pending entry.
        if result.is_err() { core::mem::forget(self); }
        result
    }
    fn begin_link_attempt(&mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || entry.host_revoked || entry.guest_released || entry.capsule.is_none() || entry.payload.is_none()
        { return Err(EBUSY); }
        entry.attempted = true;
        self.attempted = true;
        Ok(())
    }
    fn restore(mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
        { return Err(EIO); }
        entry.phase = self.previous_phase;
        self.active = false;
        Ok(())
    }
    fn install_capsule(mut self, capsule: Arc<ForkConsumerCapsule>) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            || entry.attempted || entry.capsule.is_some()
        { return Err(EBUSY); }
        entry.capsule = Some(capsule.clone());
        entry.phase = self.previous_phase;
        self.active = false;
        Ok(())
    }
    fn cancel_capsule(mut self) -> Result {
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
            if entry.epoch != self.epoch || entry.identity != Some(self.identity)
                || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
                || entry.attempted
            { return Err(EBUSY); }
            let removed = entry.capsule.take();
            entry.phase = self.previous_phase;
            removed
        };
        self.active = false;
        // The caller retains an independent live file/callback module owner
        // through return into consumer code. This cancels ONLY its unattempted
        // capsule; the pending root owner, identity and epoch remain intact.
        drop(removed);
        Ok(())
    }
    fn mark_guest_released(&mut self) -> Result {
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
        if entry.epoch != self.epoch || entry.identity != Some(self.identity)
            || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
        { return Err(EIO); }
        if entry.receipt_index != self.receipt_index { return Err(EIO); }
        let receipt_index = self.receipt_index.ok_or(EIO)?;
        let receipt = table.completed[receipt_index].as_mut().ok_or(EIO)?;
        if receipt.epoch != self.epoch || receipt.identity != self.identity
            || receipt.phase != ForkReceiptPhase::Reserved
        { return Err(EIO); }
        // This durable exact key survives Accept failure. Retry must never
        // repeat the guest verifier, checked destructor or backend transition.
        receipt.phase = ForkReceiptPhase::Acknowledged;
        table.entries[self.index].as_mut().unwrap().guest_released = true;
        self.guest_released = true;
        Ok(())
    }
    fn finish(mut self, stage: u32) -> Result {
        let object = unsafe { &*self.object };
        let removed = {
            let mut table = object.forks.lock();
            let entry = table.entries[self.index].as_mut().ok_or(EIO)?;
            if entry.epoch != self.epoch || entry.identity != Some(self.identity)
                || !Arc::ptr_eq(&entry.owner, &self.owner) || entry.phase != FORK_PROVIDER_BUSY
            { return Err(EIO); }
            if stage == super::application_abi::FORK_HOST_REVOKED_V1 {
                entry.host_revoked = true;
                entry.phase = FORK_PROVIDER_HOST_REVOKED;
                None
            } else {
                if !entry.guest_released || !self.guest_released { return Err(EIO); }
                // Stage2 alone is not final transport publication. Payload
                // Complete stays closed until its genuine final-RET receipt
                // is joined; never remove ownership with a live carrier.
                if entry.payload.is_some() { return Err(EBUSY); }
                if entry.receipt_index != self.receipt_index { return Err(EIO); }
                let receipt = table.completed[self.receipt_index.ok_or(EIO)?].as_mut().ok_or(EIO)?;
                if receipt.epoch != self.epoch || receipt.identity != self.identity
                    || receipt.phase != ForkReceiptPhase::Acknowledged
                { return Err(EIO); }
                // Accept succeeded. Cache FINISHED before releasing ownership.
                receipt.phase = ForkReceiptPhase::Finished;
                table.entries[self.index].take()
            }
        };
        self.active = false;
        drop(removed);
        Ok(())
    }
}
impl Drop for ForkProviderClaim {
    fn drop(&mut self) {
        if !self.active { return; }
        let object = unsafe { &*self.object };
        let mut table = object.forks.lock();
        if let Some(entry) = table.entries[self.index].as_mut() {
            if entry.epoch == self.epoch && entry.identity == Some(self.identity)
                && Arc::ptr_eq(&entry.owner, &self.owner) && entry.phase == FORK_PROVIDER_BUSY
            { entry.phase = FORK_PROVIDER_QUARANTINED; }
        }
    }
}

#[derive(Clone, Copy)]
struct ForkInitialCapsule {
    module: *mut c_void,
    construct: super::application_abi::ForkInitialConstructV1,
    seed: *mut c_void,
    destroy: super::application_abi::ForkCapsuleDestroyV1,
    verify: super::application_abi::ForkVerifyV1,
    accept: super::application_abi::ForkCapsuleAcceptV1,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
}

unsafe fn construct_initial_fork_capsule(reservation: *const ForkProviderReservation,
    identity: super::application_abi::ForkIdentityV1, initial: ForkInitialCapsule) -> Result
{
    let reservation = unsafe { &*reservation };
    let object = unsafe { &*reservation.object };
    {
        let table = object.forks.lock();
        let entry = table.entries[reservation.index].as_ref().ok_or(EIO)?;
        if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity != Some(identity)
            || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.capsule.is_some()
        { return Err(EBUSY); }
    }
    let module = unsafe { ProviderModule::acquire(initial.module.cast()) }?;
    // Allocate every capsule byte BEFORE the constructor transfers ownership
    // and before the actual MM consumer can seal any VMA adoption.
    let capsule = Arc::new(ForkConsumerCapsule {
        context: AtomicPtr::new(ptr::null_mut()), destroy: initial.destroy,
        verify: initial.verify, accept: initial.accept, _link: initial.link, _module: module,
    }, GFP_KERNEL)?;
    let mut context = ptr::null_mut();
    let status = unsafe { (initial.construct)(initial.seed, &identity, &mut context) };
    capsule.context.store(context, Ordering::Release);
    if status != 0 || context.is_null() {
        // Non-NULL error output is destroyed while its IHK-owned consumer pin
        // and independent provider owner remain live, outside every guard.
        drop(capsule);
        return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
    }
    let mut table = object.forks.lock();
    let entry = table.entries[reservation.index].as_mut().ok_or(EIO)?;
    if entry.epoch != reservation.epoch || entry.phase != 0 || entry.identity != Some(identity)
        || !Arc::ptr_eq(&entry.owner, &reservation.owner) || entry.capsule.is_some()
    { return Err(EBUSY); }
    entry.capsule = Some(capsule.clone());
    drop(table);
    drop(capsule);
    Ok(())
}

struct ForkConsumerScope {
    callback: super::application_abi::ForkAdoptConsumerV1,
    context: *mut c_void,
    reservation: *mut ForkProviderReservation,
    geometry: super::application_abi::ForkGeometryV1,
    slot: u32,
    generation: u64,
    invoked: bool,
    sealed: bool,
    uncertain: bool,
    active: bool,
    initial: Option<ForkInitialCapsule>,
}

// SAFETY: Only the registered provider calls this synchronously with its actual
// borrowed seal descriptor; neither this wrapper nor the consumer retains it.
unsafe extern "C" fn fork_consumer_scope(
    context: *mut c_void,
    descriptor: *mut super::application_abi::ForkSealV1,
) -> i32 {
    use super::application_abi::{ForkSealV1, VERSION};
    // SAFETY: adopt_fork owns this stack context until provider return.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    if descriptor.is_null() || scope.invoked {
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    let descriptor = unsafe { &mut *descriptor };
    let identity = descriptor.identity;
    let flag = descriptor.sealed;
    if descriptor.version != VERSION || descriptor.bytes as usize != core::mem::size_of::<ForkSealV1>()
        || identity.reserved0 != 0 || identity.reserved1 != 0
        || identity.slot != scope.slot || identity.generation != scope.generation
        || identity.root != scope.geometry.root || identity.start != scope.geometry.start
        || identity.length != scope.geometry.length || flag.is_null()
        || identity.parent == 0 || identity.child == 0 || identity.child == identity.parent
        || identity.worker == 0 || identity.delivery == 0 || identity.nonce == 0
        || identity.child_pid <= 0 || identity.child_mm == 0
    {
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    // The provider guarantees the exact atomic outlives the callback. Capture
    // its address before the consumer; descriptor edits never redirect our read.
    if unsafe { &*flag }.load(Ordering::Acquire) {
        scope.sealed = true;
        scope.uncertain = true;
        return EINVAL.to_errno();
    }
    // Bind under table exclusion BEFORE calling the MM consumer. Completion
    // rejects initializing entries; no table guard spans the consumer callback.
    if let Err(error) = unsafe { &*scope.reservation }.bind_identity(identity) {
        scope.uncertain = true;
        return error.to_errno();
    }
    let initial = scope.initial;
    let reservation = scope.reservation;
    if let Some(initial) = initial {
        if let Err(error) = unsafe { construct_initial_fork_capsule(reservation, identity, initial) } {
            return error.to_errno();
        }
    }
    // The constructor may reenter private APIs; do not retain an exclusive
    // scope borrow across it. Phase0 still forbids every progress operation.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    scope.invoked = true;
    // No operations, registry, provider, table or Remote lock spans callback.
    scope.active = true;
    let callback = scope.callback;
    let callback_context = scope.context;
    let status = unsafe { callback(callback_context, descriptor) };
    // End the earlier exclusive stack borrow before foreign code; a reentrant
    // scoped payload operation may inspect its active flag, never mutate it.
    let scope = unsafe { &mut *context.cast::<ForkConsumerScope>() };
    scope.active = false;
    scope.sealed = unsafe { &*flag }.load(Ordering::Acquire);
    status
}

/// # Safety
/// Both contexts are borrowed live successful opens; caller excludes close and
/// pins its consumer module throughout this synchronous call. Geometry/context
/// are private kernel storage and the callback may not retain borrowed pointers.
#[export_name = "ihk_os_application_adopt_fork_v1"]
pub(crate) unsafe extern "C" fn adopt_fork_application(
    parent: *mut c_void,
    child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>,
    context: *mut c_void,
) -> i32 {
    unsafe { adopt_fork_application_inner(parent, child, geometry, consumer, context, None) }
}

/// # Safety
/// Same borrowed connection/geometry contract as v1. The additional constructor
/// seed and callbacks are actual live consumer-module storage, borrowed only
/// through this call. IHK pins and preallocates its capsule before MM effects;
/// preview keys allocate storage only and never replace actual ForkClaim proof.
#[export_name = "ihk_os_application_adopt_fork_v2"]
pub(crate) unsafe extern "C" fn adopt_fork_application_v2(
    parent: *mut c_void, child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    module: *mut c_void,
    construct: Option<super::application_abi::ForkInitialConstructV1>, seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void,
) -> i32 {
    let (Some(construct), Some(destroy), Some(verify), Some(accept)) = (construct, destroy, verify, accept)
        else { return EINVAL.to_errno(); };
    if module.is_null() { return EINVAL.to_errno(); }
    let initial = ForkInitialCapsule { module, construct, seed, destroy, verify, accept, link };
    unsafe { adopt_fork_application_inner(parent, child, geometry, consumer, context, Some(initial)) }
}

unsafe fn adopt_fork_application_inner(
    parent: *mut c_void, child: *mut c_void,
    geometry: *const super::application_abi::ForkGeometryV1,
    consumer: Option<super::application_abi::ForkAdoptConsumerV1>, context: *mut c_void,
    initial: Option<ForkInitialCapsule>,
) -> i32 {
    let result = (|| -> Result {
        if parent.is_null() || child.is_null() || geometry.is_null() { return Err(EINVAL); }
        let consumer = consumer.ok_or(EINVAL)?;
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let child = unsafe { &*child.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        if handle != child._lease.handle() { return Err(EACCES); }
        let geometry = unsafe { *geometry };
        if geometry.root == 0 || geometry.root % 4096 != 0 || geometry.start % 4096 != 0
            || geometry.length == 0 || geometry.length % 4096 != 0
            || geometry.start.checked_add(geometry.length).is_none()
        { return Err(EINVAL); }
        let lease = OS_REGISTRY.acquire(handle).map_err(|error| errno(error.errno()))?;
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        // SAFETY: The independent exact lease excludes OsObject/provider free.
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let adopt = registered.adopt_fork.ok_or(ENODEV)?;
        for callbacks in [parent.backend.callbacks, child.backend.callbacks] {
            if callbacks.open as usize != registered.open as usize
                || callbacks.invoke as usize != registered.invoke as usize
                || callbacks.close as usize != registered.close as usize
                || callbacks.adopt_fork.map(|callback| callback as usize) != Some(adopt as usize)
                || callbacks.fork_progress.map(|callback| callback as usize) != registered.fork_progress.map(|callback| callback as usize)
                || callbacks.adopt_fork_scoped.map(|callback| callback as usize) != registered.adopt_fork_scoped.map(|callback| callback as usize)
                || callbacks.prepare_fork_link.map(|callback| callback as usize) != registered.prepare_fork_link.map(|callback| callback as usize)
            { return Err(EACCES); }
        }
        let snapshot = OS_REGISTRY.snapshot(handle).map_err(|error| errno(error.errno()))?;
        if !matches!(snapshot.status, OsStatus::Ready | OsStatus::Running) { return Err(EBUSY); }
        let admission = object.admission.enter()?;
        let capacity = ForkProviderCapacity::reserve()?;
        let owner = Arc::new(ForkProviderOwner {
            _admission: admission, _lease: lease, _capacity: capacity,
        }, GFP_KERNEL)?;
        let mut reservation = ForkProviderReservation::reserve(object, owner, child.backend.context.as_ptr() as usize)?;
        let mut scope = ForkConsumerScope {
            callback: consumer, context, reservation: ptr::from_mut(&mut reservation), geometry,
            slot: handle.minor() as u32, generation: handle.generation(),
            invoked: false, sealed: false, uncertain: false, active: false, initial,
        };
        // SAFETY: Both connections and independent admission/OS/provider hold
        // stay live; the wrapper and caller context are synchronous stack borrows.
        // No OS operation, registry, provider or pending-table lock is held.
        let status = if let Some(adopt_scoped) = registered.adopt_fork_scoped {
            let mut payload_stack = ForkPayloadScopeStack {
                reservation: ptr::from_mut(&mut reservation), descriptor: ptr::null_mut(),
                consumer: ptr::from_mut(&mut scope).cast_const(), constructing: false, cleaning: false,
                rollback_ready: false, uncertain: true,
            };
            let stack_pointer = ptr::from_mut(&mut payload_stack);
            let mut payload_scope = super::application_abi::ForkPayloadScopeV1 {
                version: super::application_abi::VERSION,
                bytes: core::mem::size_of::<super::application_abi::ForkPayloadScopeV1>() as u32,
                slot: handle.minor() as u32, reserved0: 0, generation: handle.generation(),
                epoch: reservation.epoch, context: stack_pointer.cast(), attach: Some(fork_payload_attach_scope),
            };
            unsafe { (*stack_pointer).descriptor = ptr::from_mut(&mut payload_scope) };
            let status = unsafe { adopt_scoped(
                parent.backend.context.as_ptr(), child.backend.context.as_ptr(), &geometry,
                &mut payload_scope, Some(fork_consumer_scope), ptr::from_mut(&mut scope).cast(),
            ) };
            if !scope.sealed && (!payload_stack.rollback_ready || payload_stack.uncertain) {
                scope.uncertain = true;
            }
            status
        } else {
            unsafe { adopt(
                parent.backend.context.as_ptr(), child.backend.context.as_ptr(), &geometry,
                Some(fork_consumer_scope), ptr::from_mut(&mut scope).cast(),
            ) }
        };
        if scope.sealed || scope.uncertain {
            reservation.retain(status != 0 || scope.uncertain);
        } else {
            drop(reservation); // Safe pre-effect rollback, after callback return.
        }
        if status == 0 && (!scope.invoked || !scope.sealed || scope.uncertain) {
            return Err(errno(-71));
        }
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        to_result(status)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}
// SAFETY: The caller supplies a live successful connection, excludes close
// and retains its exact allocation through this entire private borrow.
unsafe fn fork_application_binding<'a>(
    child: *mut c_void, key: super::application_abi::ForkIdentityV1,
) -> Result<(&'a ApplicationConnection, &'a OsObject, ApplicationCallbacks)> {
    if child.is_null() { return Err(EINVAL); }
    let child = unsafe { &*child.cast::<ApplicationConnection>() };
    let handle = child._lease.handle();
    if key.slot as usize != handle.minor() || key.generation != handle.generation()
        || key.reserved0 != 0 || key.reserved1 != 0
    { return Err(EACCES); }
    let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
    if raw.is_null() { return Err(EIO); }
    let object = unsafe { &*raw };
    let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
    let callbacks = child.backend.callbacks;
    if callbacks.open as usize != registered.open as usize
        || callbacks.invoke as usize != registered.invoke as usize
        || callbacks.close as usize != registered.close as usize
        || callbacks.adopt_fork.map(|callback| callback as usize) != registered.adopt_fork.map(|callback| callback as usize)
        || callbacks.fork_progress.map(|callback| callback as usize) != registered.fork_progress.map(|callback| callback as usize)
        || callbacks.adopt_fork_scoped.map(|callback| callback as usize) != registered.adopt_fork_scoped.map(|callback| callback as usize)
        || callbacks.prepare_fork_link.map(|callback| callback as usize) != registered.prepare_fork_link.map(|callback| callback as usize)
        || registered.fork_progress.is_none()
    { return Err(EACCES); }
    Ok((child, object, registered))
}

struct ForkLinkResolverScope {
    object: *const OsObject,
    slot: u32,
    generation: u64,
}

unsafe extern "C" fn resolve_fork_control_scope(
    context: *mut c_void, descriptor: *const super::application_abi::ForkControlV1,
    park: Option<super::application_abi::ForkControlParkV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkControlV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let park = park.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let before = unsafe { *descriptor }; let key = before.identity;
        if before.version != VERSION || before.bytes as usize != core::mem::size_of::<ForkControlV1>()
            || before.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation || before.epoch == 0
            || key.parent == 0 || key.child == 0 || key.parent == key.child || key.worker == 0
            || key.delivery == 0 || key.nonce == 0 || key.child_pid <= 0 || key.child_mm == 0
            || before.worker == 0 || before.delivery == 0 || before.cpu < 0
            || before.physical == 0 || before.response == 0
        { return Err(EACCES); }
        let object = unsafe { &*scope.object };
        let child_context = {
            let table = object.forks.lock();
            table.entries.iter().flatten().find(|e| e.identity == Some(key) && e.epoch == before.epoch)
                .map(|e| e.child_context).ok_or(ENOENT)?
        };
        let claim = ForkProviderClaim::acquire_control(object, key, child_context, before.epoch)?;
        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        if capsule.context.load(Ordering::Acquire).is_null() { return Err(EIO); }
        let payload_context = payload.context.load(Ordering::Acquire);
        if payload_context.is_null() { return Err(EIO); }
        // No IHK table guard spans backend/Remote code. Both exact capsules,
        // module and OS admission remain owned by this BUSY claim. Callback is
        // registered backend code, and receives ONLY shared payload metadata.
        let status = unsafe { park(ticket, payload_context.cast_const()) };
        if unsafe { *descriptor } != before { return Err(errno(-71)); }
        if status != 0 {
            // The trusted park callback has no fallible step after moving its
            // response. A refusal therefore has no backend ownership effects.
            claim.restore_control()?;
            return Err(errno(if (-4095..0).contains(&status) { status } else { -71 }));
        }
        // Restore failure retains the original IHK claim; caller retains its durable
        // parked response and independently marks its backend owner uncertain.
        claim.restore_control()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}
pub(crate) unsafe extern "C" fn prepare_fork_control_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result<bool> {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|b| b.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.adopt_fork.map(|f| f as usize) != registered.adopt_fork.map(|f| f as usize)
            || callbacks.fork_progress.map(|f| f as usize) != registered.fork_progress.map(|f| f as usize)
            || callbacks.adopt_fork_scoped.map(|f| f as usize) != registered.adopt_fork_scoped.map(|f| f as usize)
            || callbacks.prepare_fork_link.map(|f| f as usize) != registered.prepare_fork_link.map(|f| f as usize)
            || callbacks.fork_progress_payload.map(|f| f as usize) != registered.fork_progress_payload.map(|f| f as usize)
            || callbacks.prepare_fork_ack.map(|f| f as usize) != registered.prepare_fork_ack.map(|f| f as usize)
            || callbacks.fork_publication_verify.map(|f| f as usize) != registered.fork_publication_verify.map(|f| f as usize)
            || callbacks.release_fork_ack.map(|f| f as usize) != registered.release_fork_ack.map(|f| f as usize)
            || callbacks.prepare_fork_control.map(|f| f as usize) != registered.prepare_fork_control.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_control else { return Ok(false); };
        let mut scope = ForkLinkResolverScope { object: ptr::from_ref(object), slot: handle.minor() as u32,
            generation: handle.generation() };
        match unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_control_scope), ptr::from_mut(&mut scope).cast()) } {
            0 => Ok(false), 1 => Ok(true), e if (-4095..0).contains(&e) => Err(errno(e)), _ => Err(errno(-71)),
        }
    })();
    result.map_or_else(|e| e.to_errno(), |parked| i32::from(parked))
}
unsafe extern "C" fn resolve_fork_link_scope(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkLinkSealV1,
    finish: Option<super::application_abi::ForkLinkFinishV1>, ticket: *mut c_void,
) -> i32 {
    let result = (|| -> Result {
        use super::application_abi::{ForkLinkSealV1, VERSION};
        if context.is_null() || descriptor.is_null() || ticket.is_null() { return Err(EINVAL); }
        let finish = finish.ok_or(EINVAL)?;
        let scope = unsafe { &*context.cast::<ForkLinkResolverScope>() };
        let d = unsafe { &*descriptor };
        let key = d.identity;
        if d.version != VERSION || d.bytes as usize != core::mem::size_of::<ForkLinkSealV1>()
            || d.reserved != 0 || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != scope.slot || key.generation != scope.generation
            || key.parent == 0 || key.child == 0 || key.parent == key.child
            || key.worker == 0 || key.delivery == 0 || key.nonce == 0 || key.child_pid <= 0 || key.child_mm == 0
            || d.second_worker == 0 || d.second_delivery == 0 || d.second_cpu < 0
            || d.carrier_physical == 0 || d.carrier_sequence == 0 || d.gate.is_null()
        { return Err(EACCES); }
        let before = (d.version, d.bytes, d.identity, d.second_worker, d.second_delivery,
            d.second_cpu, d.reserved, d.carrier_physical, d.carrier_sequence, d.gate);
        let object = unsafe { &*scope.object };
        // Copy only a scalar under exclusion. No context is dereferenced until
        // acquire rechecks the full key and clones its actual owner/capsules.
        let child_context = {
            let table = object.forks.lock();
            table.entries.iter().flatten().find(|entry| entry.identity == Some(key))
                .map(|entry| entry.child_context).ok_or(ENOENT)?
        };
        let mut claim = match ForkProviderClaim::acquire(object, key, child_context, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        claim.begin_link_attempt()?;
        let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
        let verify = capsule._link.ok_or(ENODEV)?;
        let consumer_context = capsule.context.load(Ordering::Acquire);
        let payload = claim.payload.as_ref().ok_or(ENODEV)?;
        let payload_context = payload.context.load(Ordering::Acquire);
        if consumer_context.is_null() || payload_context.is_null() { return Err(EIO); }
        // Every exact epoch/capsule/module/OS pin remains owned by claim. No
        // table/Remote/MM guard spans either callback. Cache the provider's
        // continuation and ticket before consumer code can edit its descriptor.
        let status = unsafe { verify(consumer_context, descriptor) };
        let d = unsafe { &*descriptor };
        let after = (d.version, d.bytes, d.identity, d.second_worker, d.second_delivery,
            d.second_cpu, d.reserved, d.carrier_physical, d.carrier_sequence, d.gate);
        if after != before { return Err(errno(-71)); }
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        if unsafe { &*before.9 }.load(Ordering::Acquire) != 2 { return Err(errno(-71)); }
        let status = unsafe { finish(ticket, payload_context) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        // Restore only this exact BUSY epoch; all attempted errors instead
        // quarantine and retain its contexts, including any SEALED link gate.
        claim.restore()
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// The actual live parent Registration/file pins this connection and caller
/// module through return. Scalars come from its retained RETURN invocation;
/// only the registered backend derives a child key from the owned delivery.
#[export_name = "ihk_os_application_prepare_fork_link_v1"]
pub(crate) unsafe extern "C" fn prepare_fork_link_application(
    parent: *mut c_void, worker: u64, serial: u64, cpu: i64, value: i64,
) -> i32 {
    let result = (|| -> Result {
        if parent.is_null() { return Err(EINVAL); }
        let parent = unsafe { &*parent.cast::<ApplicationConnection>() };
        let handle = parent._lease.handle();
        let raw = OS_OBJECTS[handle.minor()].load(Ordering::Acquire);
        if raw.is_null() { return Err(EIO); }
        let object = unsafe { &*raw };
        let registered = object.backend.and_then(|backend| backend.application).ok_or(ENODEV)?;
        let callbacks = parent.backend.callbacks;
        if callbacks.open as usize != registered.open as usize
            || callbacks.invoke as usize != registered.invoke as usize
            || callbacks.close as usize != registered.close as usize
            || callbacks.adopt_fork.map(|f| f as usize) != registered.adopt_fork.map(|f| f as usize)
            || callbacks.fork_progress.map(|f| f as usize) != registered.fork_progress.map(|f| f as usize)
            || callbacks.adopt_fork_scoped.map(|f| f as usize) != registered.adopt_fork_scoped.map(|f| f as usize)
            || callbacks.prepare_fork_link.map(|f| f as usize) != registered.prepare_fork_link.map(|f| f as usize)
        { return Err(EACCES); }
        let Some(prepare) = registered.prepare_fork_link else { return Ok(()); };
        let mut scope = ForkLinkResolverScope {
            object: ptr::from_ref(object), slot: handle.minor() as u32, generation: handle.generation(),
        };
        let status = unsafe { prepare(parent.backend.context.as_ptr(), worker, serial, cpu, value,
            Some(resolve_fork_link_scope), ptr::from_mut(&mut scope).cast()) };
        if status > 0 || status < -4095 { return Err(errno(-71)); }
        to_result(status)
    })();
    result.map_or_else(|e| e.to_errno(), |()| 0)
}

/// # Safety
/// The caller has an independent LIVE file/callback module owner through
/// return into consumer text. consumer_module is that exact THIS_MODULE, never
/// a userspace value. Constructor seed is borrowed until callback return; its
/// transferred context retains the exact Registration. No owned module lease
/// crosses this ABI. All callbacks are module-resident immutable identities.
#[export_name = "ihk_os_application_attach_fork_capsule_v1"]
pub(crate) unsafe extern "C" fn attach_fork_capsule_application(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    consumer_module: *mut c_void,
    construct: Option<super::application_abi::ForkCapsuleConstructV1>,
    seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
) -> i32 {
    // SAFETY: The original ABI preserves its exact arguments and lifetime.
    unsafe { attach_fork_capsule_application_v2(child, identity, consumer_module,
        construct, seed, destroy, verify, accept, None) }
}

/// # Safety
/// Same ownership contract as v1. The distinct optional link verifier borrows
/// only its actual preallocated gate; host revoke never substitutes for link.
#[export_name = "ihk_os_application_attach_fork_capsule_v2"]
pub(crate) unsafe extern "C" fn attach_fork_capsule_application_v2(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    consumer_module: *mut c_void,
    construct: Option<super::application_abi::ForkCapsuleConstructV1>,
    seed: *mut c_void,
    destroy: Option<super::application_abi::ForkCapsuleDestroyV1>,
    verify: Option<super::application_abi::ForkVerifyV1>,
    accept: Option<super::application_abi::ForkCapsuleAcceptV1>,
    link: Option<super::application_abi::ForkCapsuleLinkV1>,
) -> i32 {
    let result = (|| -> Result {
        if identity.is_null() { return Err(EINVAL); }
        let construct = construct.ok_or(EINVAL)?;
        let destroy = destroy.ok_or(EINVAL)?;
        let verify = verify.ok_or(EINVAL)?;
        let accept = accept.ok_or(EINVAL)?;
        let key = unsafe { *identity };
        let (child, object, _) = unsafe { fork_application_binding(child, key) }?;
        let claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.capsule.is_some() || claim.attempted {
            claim.restore()?;
            return Err(EBUSY);
        }
        // The table lock ended before module acquisition or consumer code.
        let module = match unsafe { ProviderModule::acquire(consumer_module.cast()) } {
            Ok(module) => module,
            Err(error) => { claim.restore()?; return Err(error); }
        };
        let mut context = ptr::null_mut();
        let status = unsafe { construct(seed, &mut context) };
        if status != 0 || context.is_null() {
            if !context.is_null() { unsafe { destroy(context) }; }
            // Consumer Drop/Destroy has returned BEFORE this IHK-owned put.
            drop(module);
            claim.restore()?;
            return Err(errno(if status == 0 { -5 } else if (-4095..0).contains(&status) { status } else { -71 }));
        }
        let capsule = ForkConsumerCapsule {
            context: AtomicPtr::new(context), destroy, verify, accept, _link: link, _module: module,
        };
        let capsule = match Arc::new(capsule, GFP_KERNEL) {
            Ok(capsule) => capsule,
            Err(error) => { claim.restore()?; return Err(error.into()); }
        };
        claim.install_capsule(capsule)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// Same live connection and independent caller file/module ownership as attach.
/// This is never called by a generic Drop or unpinned consumer context. It
/// detaches ONLY an unattempted capsule; physical pending ownership remains.
#[export_name = "ihk_os_application_cancel_fork_capsule_v1"]
pub(crate) unsafe extern "C" fn cancel_fork_capsule_application(
    child: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    let result = (|| -> Result {
        if identity.is_null() { return Err(EINVAL); }
        let key = unsafe { *identity };
        let (child, object, _) = unsafe { fork_application_binding(child, key) }?;
        let claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, 0)? {
            ForkClaimLookup::Pending(claim) => claim,
            ForkClaimLookup::Completed => return Err(EIO),
        };
        if claim.attempted || claim.capsule.is_none() {
            let status = if claim.attempted { EBUSY } else { ENOENT };
            claim.restore()?;
            return Err(status);
        }
        claim.cancel_capsule()
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

/// # Safety
/// The live child and proof context are retained through return. Stage1 uses
/// ONLY the IHK-owned capsule's registered verifier/context. Stage2 proof comes
/// ONLY from authenticated original in-band final destruction, never a host
/// receipt. Final release is initiated outside MCCTRL, or the caller retains a
/// separate live file/callback module owner until return into consumer text.
#[export_name = "ihk_os_application_fork_progress_v1"]
pub(crate) unsafe extern "C" fn fork_progress_application(
    child: *mut c_void,
    identity: *const super::application_abi::ForkIdentityV1,
    stage: u32,
    verify: Option<super::application_abi::ForkVerifyV1>,
    context: *mut c_void,
) -> i32 {
    use super::application_abi::{FORK_HOST_REVOKED_V1, FORK_GUEST_DESTROYED_V1};
    let result = (|| -> Result {
        if identity.is_null() || !matches!(stage, FORK_HOST_REVOKED_V1 | FORK_GUEST_DESTROYED_V1)
        { return Err(EINVAL); }
        let key = unsafe { *identity };
        let (child, object, registered) = unsafe { fork_application_binding(child, key) }?;
        let progress = registered.fork_progress.ok_or(ENODEV)?;
        let mut claim = match ForkProviderClaim::acquire(object, key, child.backend.context.as_ptr() as usize, stage)? {
            ForkClaimLookup::Completed => return Ok(()),
            ForkClaimLookup::Pending(claim) => claim,
        };
        let (host_verify, capsule_context, accept) = {
            let capsule = claim.capsule.as_ref().ok_or(ENODEV)?;
            let context = capsule.context.load(Ordering::Acquire);
            if context.is_null() { return Err(EIO); }
            (capsule.verify, context, capsule.accept)
        };
        if stage == FORK_HOST_REVOKED_V1 {
            // Independent capsule Arc/module/Registration and OS/provider
            // ownership survive last fd closure or any attempted error.
            let status = unsafe { progress(child.backend.context.as_ptr(), &key, stage, Some(host_verify), capsule_context) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            return claim.finish(stage);
        }
        if !claim.guest_released {
            let verify = verify.ok_or(EINVAL)?;
            let status = unsafe { progress(child.backend.context.as_ptr(), &key, stage, Some(verify), context) };
            if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
            claim.mark_guest_released()?;
        }
        // ACK_RECEIVED is durable and receipt capacity was reserved before
        // Remote's irreversible transition. Retry executes ONLY Accept here.
        let status = unsafe { accept(capsule_context, &key) };
        if status != 0 { return Err(errno(if (-4095..0).contains(&status) { status } else { -71 })); }
        claim.finish(stage)
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}


// Concrete registered callback path, same original independent IHK holds.
unsafe extern "C" fn open(_:u32,_:u64,_:i32,_:*mut *mut c_void)->i32{0}
unsafe extern "C" fn invoke(_: *mut c_void,_:u32,_:*mut u8,_:usize)->i64{0}
unsafe extern "C" fn close(context:*mut c_void){unsafe{drop(std::boxed::Box::from_raw(context.cast::<smp_memory::Application>()))}}
fn callbacks()->ApplicationCallbacks{ApplicationCallbacks{open,invoke,close,adopt_fork:Some(application_adopt_fork),fork_progress:Some(application_fork_progress),adopt_fork_scoped:Some(application_adopt_fork_scoped),prepare_fork_link:Some(application_prepare_fork_link),prepare_fork_control:Some(application_prepare_fork_control),fork_progress_payload:None,prepare_fork_ack:None,fork_publication_verify:None,release_fork_ack:None}}
pub(crate) struct Connections{parent:std::boxed::Box<ApplicationConnection>,child:std::boxed::Box<ApplicationConnection>,object:std::boxed::Box<OsObject>}
impl Connections{pub(crate) fn raw(&mut self)->(*mut c_void,*mut c_void){(ptr::from_mut(&mut*self.parent).cast(),ptr::from_mut(&mut*self.child).cast())}}
pub(crate) fn connections(remote:Arc<Remote>,p:Token,c:Token)->Connections{
 assert!(OS_OBJECTS[0].load(Ordering::Acquire).is_null());
 let mut object=std::boxed::Box::new(OsObject{admission:Admission::new(),backend:Some(Backend{application:Some(callbacks())}),forks:Mutex::new(ForkPendingTable::new())});OS_OBJECTS[0].store(ptr::from_mut(&mut*object),Ordering::Release);
 let runtime=Arc::new(BridgeRuntime{application:remote},0).unwrap();let handle=OsHandle{minor:0,generation:2};
 let make=|app:smp_memory::Application|std::boxed::Box::new(ApplicationConnection{backend:BackendApplication{context:NonNull::new(std::boxed::Box::into_raw(std::boxed::Box::new(app)).cast()).unwrap(),callbacks:callbacks()},_admission:object.admission.enter().unwrap(),_lease:OS_REGISTRY.acquire(handle).unwrap()});
 let parent=make(smp_memory::Application::fixture(runtime.clone(),p));let child=make(smp_memory::Application::fixture(runtime,c));Connections{parent,child,object}
}
pub(crate) fn consumer_module()->*mut c_void{ptr::addr_of!(CONSUMER_MODULE).cast_mut().cast()}
pub(crate) fn retained()->usize{let raw=OS_OBJECTS[0].load(Ordering::Acquire);if raw.is_null(){return 0;}unsafe{&*raw}.forks.lock().entries.iter().flatten().count()}
// All successful/uncertain carriers remain retained. No fabricated final ACK
// teardown is called to make test counters balance.
pub(crate) fn retain_connections(c:Connections){OS_OBJECTS[0].store(ptr::null_mut(),Ordering::Release);std::mem::forget(c);}
thread_local!{static CONNECTION_CONTEXTS:std::cell::Cell<(*mut c_void,*mut c_void)>=const{std::cell::Cell::new((ptr::null_mut(),ptr::null_mut()))};}
pub(crate) fn set_connection_contexts(p:*mut c_void,c:*mut c_void){CONNECTION_CONTEXTS.with(|v|v.set((p,c)));}
pub(crate) fn connection_context(pid:i32)->*mut c_void{CONNECTION_CONTEXTS.with(|v|{let(p,c)=v.get();if pid==101{p}else{c}})}



pub(crate) fn control_pending_state()->(u32,bool,bool,u64) {
 let raw=OS_OBJECTS[0].load(Ordering::Acquire);let table=unsafe{&*raw}.forks.lock();let e=table.entries.iter().flatten().next().unwrap();(e.phase,e.attempted,e.host_revoked,e.epoch)
}
pub(crate) fn pending_owner_counts()->(usize,usize,usize){let raw=OS_OBJECTS[0].load(Ordering::Acquire);let table=unsafe{&*raw}.forks.lock();let e=table.entries.iter().flatten().next().unwrap();(Arc::strong_count(&e.owner),Arc::strong_count(e.capsule.as_ref().unwrap()),Arc::strong_count(e.payload.as_ref().unwrap()))}
pub(crate) unsafe fn park_with_restore_conflict(remote:&Arc<Remote>,parent:Token,w:u64,s:u64,replace_epoch:bool)->i32 {
 let mut ticket=remote.begin_fork_control(parent,w,s,0,-95).unwrap().unwrap();let d=ticket.descriptor();
 let raw=OS_OBJECTS[0].load(Ordering::Acquire);let object=unsafe{&*raw};
 let child_context={let table=object.forks.lock();table.entries.iter().flatten().next().unwrap().child_context};
 let claim=ForkProviderClaim::acquire_control(object,d.identity,child_context,d.epoch).unwrap();
 {let payload=claim.payload.as_ref().unwrap().context.load(Ordering::Acquire);assert_eq!(unsafe{ticket.park(&*payload.cast::<crate::smp_memory::storage::ForkPayload>())},Ok(()));}
 {let mut table=object.forks.lock();let e=table.entries.iter_mut().flatten().next().unwrap();if replace_epoch{e.epoch+=1;}else{e.phase=FORK_PROVIDER_PENDING;}}
 let status=claim.restore_control().map_or_else(|e|e.to_errno(),|()|0);ticket.quarantine_if_parked();status
}
pub(crate) fn alter_control_pending(phase:Option<u32>,epoch:Option<u64>){let raw=OS_OBJECTS[0].load(Ordering::Acquire);let mut table=unsafe{&*raw}.forks.lock();let e=table.entries.iter_mut().flatten().next().unwrap();if let Some(p)=phase{e.phase=p;}if let Some(v)=epoch{e.epoch=v;}}

pub(crate) fn current_key()->application_abi::ForkIdentityV1{let raw=OS_OBJECTS[0].load(Ordering::Acquire);let table=unsafe{&*raw}.forks.lock();table.entries.iter().flatten().find_map(|e|e.identity).unwrap()}

}
#[allow(dead_code, non_camel_case_types)]
mod consumer_fixture {
use std::{cell::{Cell, RefCell, RefMut}, ffi::c_void, pin::Pin, ptr::{self, NonNull}, sync::atomic::{AtomicBool, AtomicI32, Ordering}};
type Result<T = ()> = std::result::Result<T, i32>;
const ESRCH: i32 = -3; const EINVAL: i32 = -22; const EACCES: i32 = -13;
const EBUSY:i32=-16; const EFAULT:i32=-14; const EIO:i32=-5;
const EOVERFLOW: i32 = -75; const GFP_KERNEL: u32 = 0;
fn errno(code: i32) -> i32 { code }
mod kernel { pub mod error { pub fn to_result(code:i32)->Result<(),i32>{if code<0{Err(code)}else{Ok(())}} } }
thread_local! { static ALLOCATION: Cell<(usize, usize)> = const { Cell::new((0,0)) }; }
fn allocate() -> Result { ALLOCATION.with(|a| { let (n, fail) = a.get(); a.set((n+1,fail)); if n+1 == fail { Err(-12) } else { Ok(()) } }) }
struct Arc<T>(std::sync::Arc<T>);
impl<T> Arc<T> {
    fn new(value: T, _: u32) -> Result<Self> { allocate()?; Ok(Self(std::sync::Arc::new(value))) }
    fn into_raw(this: Self) -> *const T { std::sync::Arc::into_raw(this.0) }
    unsafe fn from_raw(raw: *const T) -> Self { Self(unsafe { std::sync::Arc::from_raw(raw) }) }
    fn strong_count(this: &Self) -> usize { std::sync::Arc::strong_count(&this.0) }
}
impl<T> Clone for Arc<T> { fn clone(&self) -> Self { Self(self.0.clone()) } }
impl<T> std::ops::Deref for Arc<T> { type Target = T; fn deref(&self) -> &T { &self.0 } }
struct ArcBorrow<'a,T> { raw: *const T, lifetime: std::marker::PhantomData<&'a T> }
impl<'a,T> ArcBorrow<'a,T> { unsafe fn from_raw(raw: *const T) -> Self { Self { raw, lifetime: std::marker::PhantomData } } }
impl<T> std::ops::Deref for ArcBorrow<'_,T> { type Target=T; fn deref(&self)->&T { unsafe { &*self.raw } } }
impl<T> From<ArcBorrow<'_,T>> for Arc<T> {
    fn from(borrow:ArcBorrow<'_,T>)->Self { let value=std::mem::ManuallyDrop::new(unsafe { Arc::from_raw(borrow.raw) }); Arc::clone(&value) }
}
struct Vec<T>(std::vec::Vec<T>);
impl<T> Vec<T> {
    fn with_capacity(n: usize, _:u32)->Result<Self> { allocate()?; Ok(Self(std::vec::Vec::with_capacity(n))) }
    fn push(&mut self, value:T, _:u32)->Result { assert!(self.0.len()<self.0.capacity()); self.0.push(value); Ok(()) }
}
impl<T> std::ops::Deref for Vec<T> { type Target=std::vec::Vec<T>; fn deref(&self)->&Self::Target { &self.0 } }
impl<T> std::ops::DerefMut for Vec<T> { fn deref_mut(&mut self)->&mut Self::Target { &mut self.0 } }
struct Mutex<T>(RefCell<T>);
impl<T> Mutex<T> { fn lock(&self)->RefMut<'_,T> { self.0.borrow_mut() } }
pub(crate) mod bindings {
    use super::*;
    #[allow(non_camel_case_types)] pub struct pid;
    #[allow(non_upper_case_globals)] pub static mut init_pid_ns:()=();
    pub unsafe fn get_task_pid(_: *mut(),_:u32)->*mut pid{2usize as*mut pid}
    pub unsafe fn pid_nr_ns(_: *mut pid,_:*mut())->i32{102}
    pub unsafe fn put_pid(_: *mut pid){}
    #[allow(non_upper_case_globals)] pub const pid_type_PIDTYPE_TGID:u32=1;
    pub unsafe fn get_pid_task(referenced_pid:*mut self::pid,_:u32)->*mut(){if referenced_pid.is_null(){ptr::null_mut()}else{1usize as*mut()}}
    pub unsafe fn put_task_struct(_: *mut()){}

    #[repr(C)] pub struct atomic_t { pub counter:i32 }
    #[repr(C)] pub struct mm_fields { pub mm_count:atomic_t }
    #[repr(C)] pub struct mm_union { pub __bindgen_anon_1:mm_fields,pub mm_users:atomic_t }
    #[repr(C)] pub struct mm_struct { pub __bindgen_anon_1:mm_union, pub users:Cell<i32>, pub drops:Cell<usize> }
    #[repr(C)] pub struct file { pub private_data:*mut c_void }
    pub const VM_PFNMAP:u64=1024; pub const VM_DONTEXPAND:u64=2048; pub const VM_DONTDUMP:u64=4096;
    #[repr(C)] pub struct geometry { pub vm_start:u64, pub vm_end:u64 }
    #[repr(C)] pub struct fields { pub __bindgen_anon_1:geometry }
    #[repr(C)] pub struct flags { pub __vm_flags:u64 }
    #[repr(C)] pub struct vm_area_struct {
        pub vm_mm:*mut mm_struct, pub vm_file:*mut file, pub vm_private_data:*mut c_void,
        pub vm_ops:*const (), pub vm_pgoff:u64, pub __bindgen_anon_1:fields, pub __bindgen_anon_2:flags,
        pub old_owner:*mut c_void, pub writing:bool, pub cleared:bool,
    }
    pub struct fault_fields { pub vma:*mut vm_area_struct, pub address:u64 }
    pub struct vm_fault { pub __bindgen_anon_1:fault_fields, pub flags:u64 }
    pub unsafe fn get_current()->*mut () { ptr::null_mut() }
    pub unsafe fn get_task_mm(_: *mut ())->*mut mm_struct { MODEL.with(|m| { let mm=m.borrow().mm; unsafe { (*mm).__bindgen_anon_1.mm_users.counter+=1;(*mm).users.set((*mm).__bindgen_anon_1.mm_users.counter) }; mm }) }
    pub unsafe fn mmput(mm:*mut mm_struct) { unsafe { (*mm).__bindgen_anon_1.mm_users.counter-=1;(*mm).users.set((*mm).__bindgen_anon_1.mm_users.counter) }; }
    pub unsafe fn __mmdrop(mm:*mut mm_struct) { unsafe { (*mm).drops.set((*mm).drops.get()+1) }; }
    pub unsafe fn find_vma(mm:*mut mm_struct, address:u64)->*mut vm_area_struct {
        MODEL.with(|m| { let m=m.borrow(); assert!(m.locked); assert_eq!(mm,m.mm);
            m.vmas.iter().copied().find(|v| unsafe { (**v).__bindgen_anon_1.__bindgen_anon_1.vm_end>address }).unwrap_or(ptr::null_mut()) })
    }
    pub unsafe fn zap_vma_ptes(vma:*mut vm_area_struct, first:u64, length:u64) {
        MODEL.with(|m| { let mut m=m.borrow_mut(); assert!(m.locked);
            for pointer in &m.vmas { unsafe { assert!((**pointer).writing); assert_eq!((**pointer).vm_private_data,(**pointer).old_owner); } }
            unsafe { assert_eq!(first,(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start); assert_eq!(first+length,(*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end); (*vma).cleared=true; }
            m.events.push("zap"); })
    }
}
struct Model { mm:*mut bindings::mm_struct, vmas:std::vec::Vec<*mut bindings::vm_area_struct>, locked:bool, valid:bool, events:std::vec::Vec<&'static str> }
thread_local! { static MODEL: RefCell<Model> = RefCell::new(Model { mm:ptr::null_mut(),vmas:vec![],locked:false,valid:true,events:vec![] }); }
#[no_mangle] unsafe extern "C" fn mckernel_inherited_mmap_write_lock(mm:*mut bindings::mm_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut();crate::MM_ACTIVE.with(|a|assert!(!a.replace(true))); m.valid=m.valid&&m.mm==mm&&!m.locked; m.locked=true; m.events.push("lock"); });
}
#[no_mangle] unsafe extern "C" fn mckernel_inherited_mmap_write_unlock(mm:*mut bindings::mm_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut(); m.valid=m.valid&&m.mm==mm&&m.locked; for v in &m.vmas { unsafe { (**v).writing=false; } } m.events.push("unlock"); m.locked=false;crate::MM_ACTIVE.with(|a|assert!(a.replace(false))); });
crate::run_mm_unlock_hook();
}
#[no_mangle] unsafe extern "C" fn mckernel_inherited_vma_start_write(vma:*mut bindings::vm_area_struct) {
    MODEL.with(|m| { let mut m=m.borrow_mut(); m.valid=m.valid&&m.locked&&unsafe{(*vma).vm_mm==m.mm}; unsafe { (*vma).writing=true; } m.events.push("write"); });
}
mod application_abi { pub(super) use crate::application_abi::*; }
mod mcctrl_process {pub(super) use super::actual::ForkClaim;pub(super) use super::actual::completion::{ForkLinkBinding,BorrowedLinkSeal,ReferencedChildMm};}
mod mcctrl_vm {pub(super) use super::actual::{ForkRevocation,ForkLinkReceipt};}
mod wire {
    pub fn put_word(b:&mut[u8],o:usize,v:u64)->Result<(),i32> { b[o..o+8].copy_from_slice(&v.to_le_bytes()); Ok(()) }
    pub fn word(b:&[u8],o:usize)->Result<u64,i32> { Ok(u64::from_le_bytes(b[o..o+8].try_into().unwrap())) }
}
thread_local!{static CURRENT_PID:Cell<(i32,usize)>=const{Cell::new((102,2))};static USER_SPAN:Cell<(usize,usize)>=const{Cell::new((0,0))};}
struct ProcessId{number:i32,identity:usize}
impl ProcessId{fn current()->Result<Self>{CURRENT_PID.with(|p|{let(n,id)=p.get();Ok(Self{number:n,identity:id})})}fn same(&self,other:&Self)->bool{self.identity==other.identity}fn number(&self)->Result<i32>{if self.number>0{Ok(self.number)}else{Err(ESRCH)}}}
struct UserSlice{address:usize,bytes:usize}
impl UserSlice{fn new(address:usize,bytes:usize)->Self{Self{address,bytes}}fn reader(self)->Self{self}fn read_slice(self,output:&mut[u8])->Result{USER_SPAN.with(|s|{let(address,bytes)=s.get();if self.address!=address||self.bytes>bytes||output.len()!=self.bytes{return Err(EFAULT);}output.copy_from_slice(unsafe{std::slice::from_raw_parts(address as *const u8,self.bytes)});Ok(())})}}
struct FixtureContext(i32);
impl FixtureContext{fn as_ptr(&self)->*mut c_void{crate::provider_runtime::connection_context(self.0)}}
struct Registration { fork_accepted:AtomicBool,context:FixtureContext,fork:Mutex<Option<actual::ForkClaim>>,slot:u32, generation:u64, pid:i32,physical:u64,calls:Cell<usize>,_pid:ProcessId,mapping:Mutex<Option<Arc<actual::Mirror>>>,armed:AtomicBool }
fn registration(slot:u32,generation:u64,physical:u64)->Registration{let parent=physical==0x9000;Registration{fork_accepted:AtomicBool::new(false),context:FixtureContext(if parent{101}else{102}),fork:Mutex(RefCell::new(None)),slot,generation,pid:if parent{101}else{102},physical,calls:Cell::new(0),_pid:ProcessId{number:if parent{101}else{102},identity:if parent{1}else{2}},mapping:Mutex(RefCell::new(None)),armed:AtomicBool::new(false)}}
impl Registration {
    pub(super) fn same_generation(&self, other: &Self) -> bool {
        self.slot == other.slot && self.generation != 0 && self.generation == other.generation
    }
    pub(super) fn validate_inherited_child(&self, parent: &Self) -> Result {
        if !self.same_generation(parent) {
            return Err(EACCES);
        }
        let current = ProcessId::current()?;
        if !self._pid.same(&current) || self._pid.same(&parent._pid)
            || current.number()? != self.pid
        {
            return Err(EACCES);
        }
        Ok(())
    }
    fn acquire(slot:u32,generation:u64,pid:ProcessId)->Result<Arc<Self>>{let mut r=registration(slot,generation,0x19000);r.pid=pid.number()?;r._pid=pid;Arc::new(r,0)}
    fn invoke(&self, command:u32, bytes:&mut[u8])->Result { assert_eq!(command,3); self.calls.set(self.calls.get()+1); wire::put_word(bytes,16,self.physical)?; wire::put_word(bytes,24,3) }
}
struct VmOperations(()); static VM_OPERATIONS:VmOperations=VmOperations(());
struct FaultPage { vma:*mut bindings::vm_area_struct,address:u64,physical:u64,permissions:u64 }
struct ThisModule;static THIS_MODULE:ThisModule=ThisModule;impl ThisModule{fn as_ptr(&self)->*mut c_void{crate::provider_runtime::consumer_module()}}
mod actual{
use super::*;use crate::ToErrno;
struct CurrentMm(NonNull<bindings::mm_struct>);
impl CurrentMm {
    fn get() -> Result<Self> {
        // SAFETY: The current task remains valid; Linux acquires mm_users.
        let mm = unsafe { bindings::get_task_mm(bindings::get_current()) };
        Ok(Self(NonNull::new(mm).ok_or(ESRCH)?))
    }
}
impl Drop for CurrentMm {
    fn drop(&mut self) {
        // SAFETY: Balance exactly the transient mm_users reference. It is
        // never stored in a VMA-retained owner, which would form a cycle.
        unsafe { bindings::mmput(self.0.as_ptr()) };
    }
}

struct MmIdentity(NonNull<bindings::mm_struct>);
// SAFETY: Only identity and Linux's atomic structural reference are shared.
// VMA access additionally requires a transient current mm_users reference/lock.
unsafe impl Send for MmIdentity {}
// SAFETY: Shared MmIdentity use exposes only immutable identity while its owned
// structural reference keeps the opaque mm alive until the single Drop balance.
unsafe impl Sync for MmIdentity {}
impl MmIdentity {
    fn from_current(mm: &CurrentMm) -> Result<Self> {
        // SAFETY: The current mm_users reference implies a live mm_count.
        // This is Linux mmgrab's atomic increment with checked overflow.
        let count = unsafe {
            AtomicI32::from_ptr(ptr::addr_of_mut!(
                (*mm.0.as_ptr())
                    .__bindgen_anon_1
                    .__bindgen_anon_1
                    .mm_count
                    .counter
            ))
        };
        count
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |n| {
                (n > 0).then(|| n.checked_add(1)).flatten()
            })
            .map_err(|_| errno(-75))?;
        Ok(Self(mm.0))
    }
}
impl Drop for MmIdentity {
    fn drop(&mut self) {
        // SAFETY: Balance exactly our mmgrab reference. SeqCst preserves the
        // full barrier required by Linux mmdrop and membarrier before release.
        let count = unsafe {
            AtomicI32::from_ptr(ptr::addr_of_mut!(
                (*self.0.as_ptr())
                    .__bindgen_anon_1
                    .__bindgen_anon_1
                    .mm_count
                    .counter
            ))
        };
        let old = count.fetch_sub(1, Ordering::SeqCst);
        assert!(old > 0);
        if old == 1 {
            // SAFETY: This was the final structural reference.
            unsafe { bindings::__mmdrop(self.0.as_ptr()) };
        }
    }
}


pub(super) struct Mirror {
    mm: MmIdentity,
    pub(super) start: u64,
    pub(super) end: u64,
    admission: AtomicBool,
    foreign_alias_seen: AtomicBool,
}
// Each installed VMA owns one raw Arc. A file is neutral after its initial
// mmap: inheriting vm_file must not retain the parent's application forever.
struct VmaOwner {
    registration: Arc<Registration>,
    mirror: Arc<Mirror>,
}
struct MappingFile {
    bootstrap: Pin<Box<Mutex<Option<Arc<VmaOwner>>>>>,
}

// SAFETY: The caller holds Linux's live VMA exclusion and keeps its owned raw
// Arc valid for the entire returned borrow. Owner changes require both mmap
// write exclusion and the pinned Linux per-VMA write discipline.
unsafe fn vma_owner<'a>(vma: *mut bindings::vm_area_struct) -> Result<ArcBorrow<'a, VmaOwner>> {
    let raw = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
    if raw.is_null() || unsafe { (*vma).vm_ops } != &VM_OPERATIONS.0 {
        return Err(EACCES);
    }
    // SAFETY: mmap and open install exactly one owned raw reference, and the
    // caller excludes close/rebind throughout this borrow.
    Ok(unsafe { ArcBorrow::from_raw(raw) })
}

// SAFETY: Linux calls open on a copied VMA while the original owner is live.
// This includes both a same-MM split and a different-MM fork. Clone is an
// allocation-free reference increment; the inherited MM mismatch stays intact.
unsafe extern "C" fn vma_open(vma: *mut bindings::vm_area_struct) {
    if let Ok(owner) = unsafe { vma_owner(vma) } {
        if unsafe { (*vma).vm_mm } != owner.mirror.mm.0.as_ptr() {
            // A foreign MM may retain already populated PFNs. Until a full
            // alias registry exists, no revoke receipt may ignore that MM.
            owner.mirror.foreign_alias_seen.store(true, Ordering::Release);
        }
        let reference: Arc<VmaOwner> = owner.into();
        unsafe { (*vma).vm_private_data = Arc::into_raw(reference).cast_mut().cast() };
    }
}

// SAFETY: Linux invokes close once for each successfully opened/mapped VMA,
// after its fault borrows end. Returning this raw owner balances exactly that
// VMA's reference; the file no longer contains an application owner.
unsafe extern "C" fn vma_close(vma: *mut bindings::vm_area_struct) {
    let raw = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
    unsafe { (*vma).vm_private_data = ptr::null_mut() };
    if !raw.is_null() {
        unsafe { drop(Arc::from_raw(raw)) };
    }
}

// Native thunks are supplied by 0011-mm-export-inherited-vma-write-primitives.
// They use Linux mmap_write_lock/unlock (including vma_end_write_all) and
// vma_start_write, not manually replicated semaphore/sequence operations.
extern "C" {
    fn mckernel_inherited_mmap_write_lock(mm: *mut bindings::mm_struct);
    fn mckernel_inherited_mmap_write_unlock(mm: *mut bindings::mm_struct);
    fn mckernel_inherited_vma_start_write(vma: *mut bindings::vm_area_struct);
}

struct InheritedMmWrite<'a> {
    mm: &'a CurrentMm,
}
impl Drop for InheritedMmWrite<'_> {
    fn drop(&mut self) {
        // SAFETY: The transaction acquired this exact live MM's write lock.
        unsafe { mckernel_inherited_mmap_write_unlock(self.mm.0.as_ptr()) };
    }
}

struct InheritedVmaReplacement {
    vma: NonNull<bindings::vm_area_struct>,
    owner: Option<Arc<VmaOwner>>,
}

#[allow(dead_code)]
impl Mirror {
    /// Replace only the current child MM's complete inherited mirror extent.
    ///
    /// # Safety
    /// The parent proof must come from retained backend/VMA
    /// provenance. `seal` must commit that already-reserved backend transaction
    /// infallibly under this exclusion, without allocation, sleepable external
    /// calls, user copies, or publication beforehand. The seal capability
    /// must remain alive through unlock; defer cancellation, local registration
    /// publication and all possible owner destructors until this returns.
    /// No runtime caller is
    /// permitted until native ABI and revoke/final-ACK proofs are verified.
    pub(super) unsafe fn inherit_vmas(
        parent: &Arc<Self>, parent_registration: &Arc<Registration>,
        child_registration: Arc<Registration>, start: u64, end: u64,
        seal: impl FnOnce(&Arc<Self>),
    ) -> Result<Arc<Self>> {
        if start != parent.start || end != parent.end || start >= end
            || start % 4096 != 0 || end % 4096 != 0
        { return Err(EINVAL); }
        if ptr::eq(&**parent_registration, &*child_registration)
            || !parent_registration.same_generation(&child_registration)
        { return Err(EACCES); }
        child_registration.validate_inherited_child(parent_registration)?;
        let mm = CurrentMm::get()?;
        if mm.0 == parent.mm.0 { return Err(EACCES); }
        let child = Arc::new(Self { mm: MmIdentity::from_current(&mm)?, start, end, admission: AtomicBool::new(true), foreign_alias_seen: AtomicBool::new(false) }, GFP_KERNEL)?;
        let owner = Arc::new(VmaOwner { registration: child_registration, mirror: child.clone() }, GFP_KERNEL)?;
        // SAFETY: The referenced live child MM remains retained through unlock.
        unsafe { mckernel_inherited_mmap_write_lock(mm.0.as_ptr()) };
        let guard = InheritedMmWrite { mm: &mm };
        let result = (|| -> Result {
            let mut address = start;
            let mut count = 0usize;
            let mut file = ptr::null_mut();
            let mut flags = None;
            // Preflight the entire extent before allocation-dependent journal
            // publication, any per-VMA write transition, PFN zap or owner swap.
            while address < end {
                let vma = unsafe { bindings::find_vma(mm.0.as_ptr(), address) };
                if vma.is_null() { return Err(EINVAL); }
                let (first, last, current_flags) = unsafe {
                    ((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                     (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end,
                     (*vma).__bindgen_anon_2.__vm_flags)
                };
                let required = (bindings::VM_PFNMAP | bindings::VM_DONTEXPAND | bindings::VM_DONTDUMP) as u64;
                if first != address || last <= first || last > end || last % 4096 != 0
                    || unsafe { (*vma).vm_mm } != mm.0.as_ptr()
                    || unsafe { (*vma).vm_file.is_null() }
                    || unsafe { (*vma).vm_pgoff } != (first - start) / 4096
                    || current_flags & required != required
                { return Err(EINVAL); }
                if count == 0 { file = unsafe { (*vma).vm_file }; flags = Some(current_flags); }
                if unsafe { (*vma).vm_file } != file || flags != Some(current_flags) { return Err(EACCES); }
                let inherited = unsafe { vma_owner(vma) }?;
                if !ptr::eq(&*inherited.registration, &**parent_registration)
                    || !ptr::eq(&*inherited.mirror, &**parent)
                { return Err(EACCES); }
                count = count.checked_add(1).ok_or(EOVERFLOW)?;
                address = last;
            }
            let mut replacements = Vec::with_capacity(count, GFP_KERNEL)?;
            let mut address = start;
            while address < end {
                // Same MM write exclusion preserves the validated VMA set.
                let vma = NonNull::new(unsafe { bindings::find_vma(mm.0.as_ptr(), address) }).ok_or(EINVAL)?;
                replacements.push(InheritedVmaReplacement { vma, owner: Some(owner.clone()) }, GFP_KERNEL)?;
                address = unsafe { (*vma.as_ptr()).__bindgen_anon_1.__bindgen_anon_1.vm_end };
            }
            // All fallible work is complete. Exclude every VMA reader before
            // clearing all inherited aliases; only then publish child owners.
            for replacement in replacements.iter() {
                unsafe { mckernel_inherited_vma_start_write(replacement.vma.as_ptr()) };
            }
            for replacement in replacements.iter() {
                let vma = replacement.vma.as_ptr();
                let first = unsafe { (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start };
                let last = unsafe { (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end };
                unsafe { bindings::zap_vma_ptes(vma, first, last - first) };
            }
            for replacement in replacements.iter_mut() {
                let vma = replacement.vma.as_ptr();
                let old = unsafe { (*vma).vm_private_data.cast::<VmaOwner>() };
                unsafe { (*vma).vm_private_data = Arc::into_raw(replacement.owner.take().unwrap()).cast_mut().cast() };
                // Parent Arcs above retain Registration/Mirror while this raw
                // per-VMA owner is balanced; their final release cannot run.
                unsafe { drop(Arc::from_raw(old)) };
            }
            seal(&child);
            Ok(())
        })();
        drop(guard); // Real mmap_write_unlock ends the per-VMA write epoch.
        result?;
        Ok(child)
    }
}

unsafe fn lookup_fault(vmf: *mut bindings::vm_fault, write: bool) -> Result<FaultPage> {
    // SAFETY: Linux supplies the live fault structure and retained VMA.
    let (vma, address, flags) = unsafe {
        (
            (*vmf).__bindgen_anon_1.vma,
            (*vmf).__bindgen_anon_1.address,
            (*vmf).flags,
        )
    };
    // SAFETY: The fault's VMA exclusion retains its exact per-VMA raw owner.
    let owner = unsafe { vma_owner(vma) }?;
    let mirror = &owner.mirror;
    if !mirror.admission.load(Ordering::Acquire) { return Err(EBUSY); }
    // SAFETY: The same locked live VMA remains valid while its MM identity is
    // compared against the per-VMA owner before any request is issued.
    if unsafe { (*vma).vm_mm } != mirror.mm.0.as_ptr()
        || address < mirror.start
        || address >= mirror.end
    {
        return Err(EACCES);
    }
    let mut request = [0; 32];
    wire::put_word(&mut request, 0, address).map_err(errno)?;
    // FAULT_FLAG_WRITE=bit 0 and FAULT_FLAG_INSTRUCTION=bit 8 in Linux.
    let access = u64::from(write || flags & 1 != 0) | u64::from(flags & 256 != 0) << 1;
    wire::put_word(&mut request, 8, access).map_err(errno)?;
    owner
        .registration
        .invoke(super::application_abi::LOOKUP, &mut request)?;
    Ok(FaultPage {
        vma,
        address,
        physical: wire::word(&request, 16).map_err(errno)?,
        permissions: wire::word(&request, 24).map_err(errno)?,
    })
}

/// Decoded legacy CREATE_PPD geometry; it contains no authority by itself.
#[derive(Clone, Copy)]
pub(super) struct ForkDescriptor {
    pub(super) start: u64,
    pub(super) length: u64,
    pub(super) root: u64,
}

#[allow(dead_code)]
impl ForkDescriptor {
    fn read(argument: usize, compat: bool) -> Result<Self> {
        if argument == 0 { return Err(EINVAL); }
        let mut bytes = [0u8; 24];
        let width = if compat { 4 } else { 8 };
        UserSlice::new(argument, width * 3).reader().read_slice(&mut bytes[..width * 3])?;
        let mut words = [0u64; 3];
        for (index, word) in words.iter_mut().enumerate() {
            let start = index * width;
            *word = if compat {
                u32::from_le_bytes(bytes[start..start + 4].try_into().unwrap()) as u64
            } else {
                u64::from_le_bytes(bytes[start..start + 8].try_into().unwrap())
            };
        }
        let descriptor = Self { root: words[0], start: words[1], length: words[2] };
        descriptor.end()?;
        Ok(descriptor)
    }

    fn end(self) -> Result<u64> {
        if self.start % 4096 != 0 || self.length == 0 || self.length % 4096 != 0
            || self.root == 0 || self.root % 4096 != 0 { return Err(EINVAL); }
        self.start.checked_add(self.length).ok_or(EINVAL)
    }
}


struct Process{pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>}
struct Context{slot:u32,generation:u64,process:Arc<Process>}

/// Created only after validating a provider-owned scoped callback. Scalar keys
/// alone cannot construct this claim outside this module.
#[allow(dead_code)]
pub(super) struct ForkClaim { identity: super::application_abi::ForkIdentityV1 }
#[allow(dead_code)]
impl ForkClaim {
    pub(super) fn identity(&self) -> super::application_abi::ForkIdentityV1 { self.identity }
}

struct BorrowedSeal<'callback> {
    flag: &'callback AtomicBool,
    identity: super::application_abi::ForkIdentityV1,
}
impl<'callback> BorrowedSeal<'callback> {
    /// # Safety
    /// Only the registered synchronous provider callback may lend descriptor
    /// storage and flag. Its actual exclusive lease/module/OS owners outlive
    /// this whole borrow; neither pointer may escape or be retained here.
    unsafe fn from_provider(
        descriptor: &'callback mut super::application_abi::ForkSealV1,
        parent: &Registration, child: &Registration, geometry: ForkDescriptor,
        child_mm: u64,
    ) -> Result<Self> {
        let key = descriptor.identity;
        if descriptor.version != 1
            || descriptor.bytes as usize != core::mem::size_of::<super::application_abi::ForkSealV1>()
            || descriptor.sealed.is_null()
            || descriptor.sealed as usize % core::mem::align_of::<AtomicBool>() != 0
            || key.reserved0 != 0 || key.reserved1 != 0
            || key.slot != child.slot || key.generation == 0 || key.generation != child.generation
            || !child.same_generation(parent) || key.child_pid != child.pid || key.child_mm != child_mm
            || key.parent == 0 || key.child == 0 || key.parent == key.child
            || key.worker == 0 || key.delivery == 0 || key.nonce == 0
            || key.root != geometry.root || key.start != geometry.start || key.length != geometry.length
        { return Err(EACCES); }
        // SAFETY: The checked registered provider lends this exact aligned
        // preallocated AtomicBool while retaining the actual lease.
        let flag = unsafe { &*descriptor.sealed };
        if flag.load(Ordering::Acquire) { return Err(EBUSY); }
        Ok(Self { flag, identity: key })
    }
    fn seal(&mut self) { self.flag.store(true, Ordering::Release); }
}

struct ForkAttempt<'a> {
    process: &'a Arc<Process>, parent: &'a Arc<Registration>, child: &'a Arc<Registration>,
    parent_mirror: &'a Arc<Mirror>, descriptor: ForkDescriptor,
    called: bool, published: bool,
}

// SAFETY: Only the synchronous provider callback receives this borrowed stack
// attempt; both Registration connections/module owners survive the whole call.
unsafe extern "C" fn fork_adopt_consumer(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkSealV1,
) -> i32 {
    if context.is_null() || descriptor.is_null() { return EINVAL.to_errno(); }
    let attempt = unsafe { &mut *context.cast::<ForkAttempt<'_>>() };
    if attempt.called { return EBUSY.to_errno(); }
    attempt.called = true;
    let result = (|| -> Result {
        attempt.child.validate_inherited_child(attempt.parent)?;
        let child_mm = Mirror::current_mm_identity()?;
        let mut seal = unsafe { BorrowedSeal::from_provider(&mut *descriptor,
            attempt.parent, attempt.child, attempt.descriptor, child_mm) }?;
        let mut publication = attempt.process.registration.lock();
        if publication.is_some() { return Err(EINVAL); }
        let mut mapping = attempt.child.mapping.lock();
        let mut claim = attempt.child.fork.lock();
        if mapping.is_some() || claim.is_some() { return Err(EINVAL); }
        // No provider calls/locks, fallible work or owner Drop in this seal.
        let mirror = unsafe { Mirror::inherit_vmas(attempt.parent_mirror, attempt.parent,
            attempt.child.clone(), attempt.descriptor.start, attempt.descriptor.end()?, |_| seal.seal()) }?;
        // MM and per-VMA write exclusion have ended. Preallocated publication
        // slots make all remaining local work infallible.
        *mapping = Some(mirror);
        *claim = Some(ForkClaim { identity: seal.identity });
        attempt.child.armed.store(true, Ordering::Release);
        *publication = Some(attempt.child.clone());
        drop(claim);
        drop(mapping);
        drop(publication);
        attempt.published = true;
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}


/// A retained exact mirror plus full authenticated transaction identity. There
/// is no caller-asserted or public constructor, and this proof is not Copy.
#[allow(dead_code)]
pub(super) struct ForkRevocation {
    mirror: Arc<Mirror>,
    identity: super::application_abi::ForkIdentityV1,
}
#[allow(dead_code)]
impl ForkRevocation {
    pub(super) fn identity(&self) -> super::application_abi::ForkIdentityV1 { self.identity }
    pub(super) fn matches(&self, identity: super::application_abi::ForkIdentityV1) -> bool {
        self.identity == identity && !self.mirror.admission.load(Ordering::Acquire)
    }
}

#[allow(dead_code)]
impl Mirror {
    pub(super) fn current_mm_identity() -> Result<u64> {
        Ok(CurrentMm::get()?.0.as_ptr() as u64)
    }

    /// Retain provenance from Linux's actual inherited VMA before crossing the
    /// provider boundary. The later transaction revalidates every VMA again.
    pub(super) fn inherited_registration(start: u64, end: u64) -> Result<(Arc<Self>, Arc<Registration>)> {
        if start >= end || start % 4096 != 0 || end % 4096 != 0 { return Err(EINVAL); }
        let mm = CurrentMm::get()?;
        unsafe { mckernel_inherited_mmap_write_lock(mm.0.as_ptr()) };
        let guard = InheritedMmWrite { mm: &mm };
        let vma = unsafe { bindings::find_vma(mm.0.as_ptr(), start) };
        if vma.is_null() || unsafe { (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start } != start {
            return Err(EACCES);
        }
        let owner = unsafe { vma_owner(vma) }?;
        if owner.mirror.mm.0 == mm.0 || owner.mirror.start != start || owner.mirror.end != end
            || !owner.mirror.admission.load(Ordering::Acquire) { return Err(EACCES); }
        let retained = (owner.mirror.clone(), owner.registration.clone());
        drop(guard);
        Ok(retained)
    }

    /// Called only with identity retained from the authenticated provider's
    /// scoped callback. Geometry alone is never sufficient to create proof.
    pub(super) fn revoke_fork_aliases(self: &Arc<Self>, claim: &super::mcctrl_process::ForkClaim) -> Result<ForkRevocation> {
        let identity = claim.identity();
        if identity.child_mm != self.mm.0.as_ptr() as u64 || identity.start != self.start
            || identity.start.checked_add(identity.length) != Some(self.end)
            || identity.generation == 0 || identity.root == 0 || identity.root % 4096 != 0
            || identity.parent == 0 || identity.child == 0 || identity.parent == identity.child
            || identity.worker == 0 || identity.delivery == 0 || identity.nonce == 0
            || identity.child_pid <= 0 || identity.reserved0 != 0 || identity.reserved1 != 0
        { return Err(EACCES); }
        // Monotonic closure. Unknown mm/alias outcomes keep every owner and
        // this gate closed; absence of a PID is never revocation evidence.
        self.admission.store(false, Ordering::Release);
        // Equivalent to Linux mmget_not_zero, with fail-closed overflow. The
        // owned mm_count makes this atomic address valid; users==0 is EBUSY.
        let users = unsafe { AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.0.as_ptr()).__bindgen_anon_1.mm_users.counter)) };
        users.fetch_update(Ordering::Acquire, Ordering::Relaxed, |n| {
            if n > 0 { n.checked_add(1) } else { None }
        }).map_err(|_| EBUSY)?;
        let mm = CurrentMm(self.mm.0);
        unsafe { mckernel_inherited_mmap_write_lock(mm.0.as_ptr()) };
        let guard = InheritedMmWrite { mm: &mm };
        let result = (|| -> Result {
            if self.foreign_alias_seen.load(Ordering::Acquire) { return Err(EBUSY); }
            // Full MM scan includes moved/split aliases outside start..end.
            // Pass0 validates every matching VMA before any write/PFN effect;
            // then exclude all readers, then zap all matching mappings. Linux
            // zap_vma_ptes calls zap_page_range_single -> tlb_finish_mmu.
            for pass in 0..3 {
                let mut address = 0;
                loop {
                    let vma = unsafe { bindings::find_vma(mm.0.as_ptr(), address) };
                    if vma.is_null() { break; }
                    let (first, last) = unsafe { ((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                        (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end) };
                    if first < address || last <= first || last % 4096 != 0
                        || unsafe { (*vma).vm_mm } != mm.0.as_ptr() { return Err(EBUSY); }
                    if unsafe { (*vma).vm_ops } == &VM_OPERATIONS.0 {
                        let owner = unsafe { vma_owner(vma) }.map_err(|_| EBUSY)?;
                        if ptr::eq(&*owner.mirror, &**self) {
                            if first % 4096 != 0 || unsafe { (*vma).vm_file.is_null() }
                                || unsafe { (*vma).__bindgen_anon_2.__vm_flags } & bindings::VM_PFNMAP as u64 == 0
                            { return Err(EBUSY); }
                            if pass == 1 { unsafe { mckernel_inherited_vma_start_write(vma) }; }
                            if pass == 2 { unsafe { bindings::zap_vma_ptes(vma, first, last - first) }; }
                        }
                    }
                    address = last;
                }
            }
            Ok(())
        })();
        drop(guard);
        drop(mm); // transient users reference, after write/per-VMA unlock
        result?;
        Ok(ForkRevocation { mirror: self.clone(), identity })
    }
}


/// Constructed only by the actual VMA validation + same-ticket atomic seal.
/// It retains structural owners, never a persistent mm_users reference.
#[allow(dead_code)]
pub(super) struct ForkLinkReceipt {
    mirror: Arc<Mirror>,
    _registration: Arc<Registration>,
    binding: super::mcctrl_process::ForkLinkBinding,
}
#[allow(dead_code)]
impl ForkLinkReceipt {
    pub(super) fn matches(&self, binding: super::mcctrl_process::ForkLinkBinding) -> bool {
        self.binding == binding && self.mirror.admission.load(Ordering::Acquire)
    }
}
struct ForkLinkMmWrite<'mm> { mm: &'mm super::mcctrl_process::ReferencedChildMm }
impl Drop for ForkLinkMmWrite<'_> {
    fn drop(&mut self) {
        // SAFETY: Exactly this borrowed live child MM was locked on entry.
        unsafe { mckernel_inherited_mmap_write_unlock(self.mm.as_ptr()) };
    }
}
#[allow(dead_code)]
impl Mirror {
    pub(super) fn validate_fork_link(
        self: &Arc<Self>, claim: &super::mcctrl_process::ForkClaim,
        registration: &Arc<Registration>, mm: &super::mcctrl_process::ReferencedChildMm,
        seal: &mut super::mcctrl_process::BorrowedLinkSeal<'_>,
    ) -> Result<ForkLinkReceipt> {
        let key = claim.identity();
        if key != seal.binding().identity || key.child_mm != mm.as_ptr() as u64
            || self.mm.0.as_ptr() != mm.as_ptr() || key.start != self.start
            || key.start.checked_add(key.length) != Some(self.end)
            || key.generation == 0 || key.root == 0 || key.root % 4096 != 0
            || self.start >= self.end || self.start % 4096 != 0 || self.end % 4096 != 0
        { return Err(EACCES); }
        // Allocate/clone every durable owner before MM exclusion. The transient
        // users reference is borrowed only and never moves into this receipt.
        let receipt = ForkLinkReceipt { mirror: self.clone(), _registration: registration.clone(), binding: seal.binding() };
        unsafe { mckernel_inherited_mmap_write_lock(mm.as_ptr()) };
        let guard = ForkLinkMmWrite { mm };
        let result = (|| -> Result {
            if !self.admission.load(Ordering::Acquire) || self.foreign_alias_seen.load(Ordering::Acquire) { return Err(EBUSY); }
            let mut address = self.start;
            while address < self.end {
                let vma = unsafe { bindings::find_vma(mm.as_ptr(), address) };
                if vma.is_null() { return Err(EBUSY); }
                let (first, last, flags) = unsafe { (
                    (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                    (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end,
                    (*vma).__bindgen_anon_2.__vm_flags) };
                let required = (bindings::VM_PFNMAP | bindings::VM_DONTEXPAND | bindings::VM_DONTDUMP) as u64;
                if first != address || last <= first || last > self.end || last % 4096 != 0
                    || unsafe { (*vma).vm_mm } != mm.as_ptr() || flags & required != required
                    || unsafe { (*vma).vm_file.is_null() } || unsafe { (*vma).vm_pgoff } != (first - self.start) / 4096
                { return Err(EBUSY); }
                let owner = unsafe { vma_owner(vma) }.map_err(|_| EBUSY)?;
                if !ptr::eq(&*owner.mirror, &**self) || !ptr::eq(&*owner.registration, &**registration) { return Err(EACCES); }
                address = last;
            }
            // Fail closed on extra moved/duplicated aliases of this mirror.
            // They cannot silently expand the owner set handed to the child.
            let mut address = 0;
            loop {
                let vma = unsafe { bindings::find_vma(mm.as_ptr(), address) };
                if vma.is_null() { break; }
                let (first, last) = unsafe { ((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                    (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end) };
                if first < address || last <= first || unsafe { (*vma).vm_mm } != mm.as_ptr() { return Err(EBUSY); }
                if unsafe { (*vma).vm_ops } == &VM_OPERATIONS.0 {
                    let owner = unsafe { vma_owner(vma) }.map_err(|_| EBUSY)?;
                    if ptr::eq(&*owner.mirror, &**self)
                        && (first < self.start || last > self.end
                            || !ptr::eq(&*owner.registration, &**registration)) { return Err(EBUSY); }
                }
                address = last;
            }
            // The complete extent and all owners remain unchanged under this
            // MM write lock. Only this inline atomic can commit the ticket;
            // cancellation wins OPEN -> CANCELLED or we win OPEN -> SEALED.
            seal.try_seal()
        })();
        drop(guard);
        // Both error owner destruction and later mmput are outside exclusion.
        result?;
        Ok(receipt)
    }
}

impl Registration{pub(super) fn revoke_fork(self: &Arc<Self>) -> Result<super::mcctrl_vm::ForkRevocation> {
        let mirror = self.mapping.lock().clone().ok_or(EBUSY)?;
        let claim = self.fork.lock();
        let claim = claim.as_ref().ok_or(EBUSY)?;
        let key = claim.identity();
        if key.slot != self.slot || key.generation != self.generation || key.child_pid != self.pid {
            return Err(EACCES);
        }
        mirror.revoke_fork_aliases(claim)
    }}
pub(super) mod completion{use super::*;

#[derive(Clone, Copy, Eq, PartialEq)]
pub(in super::super) struct ForkLinkBinding {
    pub(in super::super) identity: super::application_abi::ForkIdentityV1,
    second_worker: u64, second_delivery: u64, second_cpu: i32,
    carrier_physical: u64, carrier_sequence: u64, gate: usize,
}

pub(in super::super) struct BorrowedLinkSeal<'ticket> {
    gate: &'ticket core::sync::atomic::AtomicU8,
    binding: ForkLinkBinding,
}
impl<'ticket> BorrowedLinkSeal<'ticket> {
    // SAFETY: Only the IHK resolver lends this descriptor while its exclusively
    // claimed pending capsule/module and the exact backend ticket remain live.
    // Descriptor storage never escapes; only the retained gate identity does.
    unsafe fn from_provider(
        descriptor: &'ticket mut super::application_abi::ForkLinkSealV1,
        expected: super::application_abi::ForkIdentityV1,
    ) -> Result<Self> {
        if descriptor.version != 1 || descriptor.bytes as usize != core::mem::size_of::<super::application_abi::ForkLinkSealV1>()
            || descriptor.identity != expected || descriptor.reserved != 0
            || descriptor.second_worker == 0 || descriptor.second_delivery == 0
            || descriptor.second_cpu < 0 || descriptor.carrier_physical == 0
            || descriptor.carrier_physical % 8 != 0
            || descriptor.carrier_physical.checked_add(128).is_none()
            || descriptor.carrier_sequence == 0 || descriptor.gate.is_null()
        { return Err(EACCES); }
        let gate = unsafe { &*descriptor.gate };
        let binding = ForkLinkBinding { identity: expected,
            second_worker: descriptor.second_worker, second_delivery: descriptor.second_delivery,
            second_cpu: descriptor.second_cpu, carrier_physical: descriptor.carrier_physical,
            carrier_sequence: descriptor.carrier_sequence, gate: descriptor.gate as usize };
        Ok(Self { gate, binding })
    }
    pub(in super::super) fn binding(&self) -> ForkLinkBinding { self.binding }
    pub(in super::super) fn sealed(&self) -> bool { self.gate.load(Ordering::Acquire) == 2 }
    // The only operation permitted after VMA validation under MM exclusion.
    // No MM mutation precedes it: a concurrent cancellation can safely win.
    #[inline(always)]
    pub(in super::super) fn try_seal(&mut self) -> Result {
        self.gate.compare_exchange(0, 2, Ordering::AcqRel, Ordering::Acquire)
            .map(|_| ()).map_err(|_| EBUSY)
    }
}

/// Transient mm_users only. Never stored in a durable receipt/capsule: that
/// would form a VMA -> Registration -> capsule -> mm_users cycle.
pub(in super::super) struct ReferencedChildMm { mm: NonNull<bindings::mm_struct> }
impl ReferencedChildMm {
    pub(in super::super) fn as_ptr(&self) -> *mut bindings::mm_struct { self.mm.as_ptr() }
}
impl Drop for ReferencedChildMm {
    fn drop(&mut self) {
        // SAFETY: Balance exactly get_task_mm, after MM write unlock and outside
        // all local/provider locks. The outer capsule pins our callback text.
        unsafe { bindings::mmput(self.mm.as_ptr()) };
    }
}

impl Registration {
    fn fork_link_mm(&self, identity: super::application_abi::ForkIdentityV1) -> Result<ReferencedChildMm> {
        if self.slot != identity.slot || self.generation != identity.generation
            || self.pid != identity.child_pid || self._pid.number()? != identity.child_pid
            || !self.armed.load(Ordering::Acquire) || self.fork_accepted.load(Ordering::Acquire)
        { return Err(EACCES); }
        // SAFETY: The retained PID object excludes numeric reuse. A task
        // reference pins the child while get_task_mm acquires its real users.
        let task = unsafe { bindings::get_pid_task(self._pid.identity as*mut bindings::pid, bindings::pid_type_PIDTYPE_TGID) };
        if task.is_null() { return Err(ESRCH); }
        let mm = unsafe { bindings::get_task_mm(task) };
        unsafe { bindings::put_task_struct(task) };
        let mm = ReferencedChildMm { mm: NonNull::new(mm).ok_or(ESRCH)? };
        if mm.as_ptr() as u64 != identity.child_mm { return Err(EACCES); }
        Ok(mm)
    }
}

// SAFETY: IHK dispatches only its stored capsule callback, outside slots, while
// the exact prepared backend link ticket and its atomic gate remain pinned.
pub(super) unsafe extern "C" fn fork_verify_link(
    context: *mut c_void, descriptor: *mut super::application_abi::ForkLinkSealV1,
) -> i32 {
    if context.is_null() || descriptor.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let result = (|| -> Result {
        if context.accepted || context.receipt.is_some() { return Err(EBUSY); }
        let mut seal = unsafe { BorrowedLinkSeal::from_provider(&mut *descriptor, context.identity) }?;
        if let Some(receipt) = context.link_receipt.as_ref() {
            return if receipt.matches(seal.binding()) && seal.sealed() { Ok(()) } else { Err(EACCES) };
        }
        let registration = context.registration.clone();
        let mm = registration.fork_link_mm(context.identity)?;
        let mirror = registration.mapping.lock().clone().ok_or(EBUSY)?;
        let result = {
            let claim = registration.fork.lock();
            let claim = claim.as_ref().ok_or(EBUSY)?;
            if claim.identity() != context.identity { return Err(EACCES); }
            mirror.validate_fork_link(claim, &registration, &mm, &mut seal)
        };
        // mmput can trigger VMA/Registration destructors: no MM or claim lock
        // remains. Persistent ownership uses mm_count, never this users ref.
        drop(mm);
        context.link_receipt = Some(result?);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

struct Box<T>(std::boxed::Box<T>);impl<T> Box<T>{fn new(v:T,_:u32)->Result<Self>{Ok(Self(std::boxed::Box::new(v)))}fn into_raw(v:Self)->*mut T{std::boxed::Box::into_raw(v.0)}unsafe fn from_raw(p:*mut T)->Self{Self(unsafe{std::boxed::Box::from_raw(p)})}}

/// Exclusively owned by IHK's typed capsule. The surrounding capsule acquired
/// its mcctrl ModuleLease BEFORE construction and destroys this Box while that
/// external pin remains live; IHK releases the module only after return.
struct PendingForkProof {
    registration: Arc<Registration>,
    receipt: Option<super::mcctrl_vm::ForkRevocation>,
    identity: super::application_abi::ForkIdentityV1,
    accepted: bool,
    link_receipt: Option<super::mcctrl_vm::ForkLinkReceipt>,
}
struct ForkProofSeed<'a> {
    registration: &'a Arc<Registration>,
    identity: super::application_abi::ForkIdentityV1,
}

// SAFETY: IHK supplies exclusive initialized output and borrows this seed only
// during the synchronous attach. Its external module lease already pins every
// constructor/error/destructor instruction. No MM/provider lock is held.
unsafe extern "C" fn fork_proof_construct(seed: *mut c_void, output: *mut *mut c_void) -> i32 {
    if seed.is_null() || output.is_null() { return EINVAL.to_errno(); }
    unsafe { output.write(ptr::null_mut()) };
    let seed = unsafe { &*seed.cast::<ForkProofSeed<'_>>() };
    let result = (|| -> Result<_> {
        if seed.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(seed.identity)
            || seed.registration.fork_accepted.load(Ordering::Acquire) { return Err(EACCES); }
        Box::new(PendingForkProof { registration: seed.registration.clone(), receipt: None,
            identity: seed.identity, accepted: false, link_receipt: None }, GFP_KERNEL).map_err(Into::into)
    })();
    match result {
        Ok(context) => { unsafe { output.write(Box::into_raw(context).cast()) }; 0 }
        Err(error) => error.to_errno(),
    }
}

// SAFETY: IHK alone supplies the authenticated PreparedForkLease preview,
// outside all locks and BEFORE the MM consumer can seal. Its independent
// module lease already pins allocation/error cleanup and all later callbacks.
// This creates storage, not adoption, LINK, revocation or final-ACK proof.
pub(super) unsafe extern "C" fn fork_proof_initial_construct(
    seed: *mut c_void, preview: *const super::application_abi::ForkIdentityV1,
    output: *mut *mut c_void,
) -> i32 {
    if seed.is_null() || preview.is_null() || output.is_null() { return EINVAL.to_errno(); }
    unsafe { output.write(ptr::null_mut()) };
    let attempt = unsafe { &*seed.cast::<ForkAttempt<'_>>() };
    let identity = unsafe { *preview };
    let result = (|| -> Result<_> {
        attempt.child.validate_inherited_child(attempt.parent)?;
        let current_mm = Mirror::current_mm_identity()?;
        let child = attempt.child;
        if identity.reserved0 != 0 || identity.reserved1 != 0
            || identity.slot != child.slot || identity.generation == 0 || identity.generation != child.generation
            || !child.same_generation(attempt.parent) || identity.child_pid != child.pid
            || identity.child_mm != current_mm || identity.parent == 0 || identity.child == 0
            || identity.parent == identity.child || identity.worker == 0 || identity.delivery == 0
            || identity.nonce == 0 || identity.root != attempt.descriptor.root
            || identity.start != attempt.descriptor.start || identity.length != attempt.descriptor.length
            || child.fork_accepted.load(Ordering::Acquire) || child.fork.lock().is_some()
            || child.mapping.lock().is_some() || attempt.process.registration.lock().is_some()
        { return Err(EACCES); }
        // Every fallible allocation completes before the independent MM
        // callback. A phase0 IHK entry cannot invoke any progress callback.
        Box::new(PendingForkProof { registration: child.clone(), receipt: None,
            identity, accepted: false, link_receipt: None }, GFP_KERNEL).map_err(Into::into)
    })();
    match result {
        Ok(context) => { unsafe { output.write(Box::into_raw(context).cast()) }; 0 }
        Err(error) => error.to_errno(),
    }
}

// SAFETY: Only IHK returns the exact sole Box after its scoped invocations end.
// Its capsule holds mcctrl's module lease throughout this destructor and all
// field Drops, then performs module_put from IHK text after this returns.
pub(super) unsafe extern "C" fn fork_proof_destroy(context: *mut c_void) {
    if !context.is_null() { unsafe { drop(Box::from_raw(context.cast::<PendingForkProof>())) }; }
}

// SAFETY: Only IHK's capsule dispatches this with its authenticated pending key
// AFTER actual original-response freeze/backend drain, outside all locks. IHK
// exclusively claims that entry; callback/context pointers never escape.
pub(super) unsafe extern "C" fn fork_verify_host(
    context: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    if context.is_null() || identity.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let identity = unsafe { *identity };
    let result = (|| -> Result {
        if identity != context.identity || context.accepted { return Err(EACCES); }
        if context.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(identity) {
            return Err(EACCES);
        }
        if let Some(receipt) = context.receipt.as_ref() {
            return if receipt.matches(identity) { Ok(()) } else { Err(EACCES) };
        }
        // Actual MM revocation is inside this callback, never precomputed while
        // a positive RET might still be publishable. Errors retain the capsule.
        let receipt = context.registration.revoke_fork()?;
        if !receipt.matches(identity) { return Err(EACCES); }
        context.receipt = Some(receipt);
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}

// SAFETY: IHK invokes ONLY after authentic final in-band destructor ACK and its
// exact durable receipt cache are committed, outside all locks under the pin.
// There is deliberately no public caller-asserted success/boolean constructor.
pub(super) unsafe extern "C" fn fork_proof_accept(
    context: *mut c_void, identity: *const super::application_abi::ForkIdentityV1,
) -> i32 {
    if context.is_null() || identity.is_null() { return EINVAL.to_errno(); }
    let context = unsafe { &mut *context.cast::<PendingForkProof>() };
    let identity = unsafe { *identity };
    let result = (|| -> Result {
        if identity != context.identity { return Err(EACCES); }
        if context.accepted { return Ok(()); }
        if !context.receipt.as_ref().is_some_and(|receipt| receipt.matches(identity)) {
            return Err(EBUSY);
        }
        if context.registration.fork.lock().as_ref().map(ForkClaim::identity) != Some(identity) {
            return Err(EACCES);
        }
        // No fallible work follows. Keep the full key for exact retry/cache
        // reconciliation, and prevent ordinary CLEANUP from destroying twice.
        context.registration.armed.store(false, Ordering::Release);
        context.registration.fork_accepted.store(true, Ordering::Release);
        context.accepted = true;
        Ok(())
    })();
    result.map_or_else(|error| error.to_errno(), |()| 0)
}


}
struct Scenario {
    owner:Arc<VmaOwner>, parent:Arc<Mirror>, parent_registration:Arc<Registration>, child_registration:Arc<Registration>,
    parent_vma:Box<bindings::vm_area_struct>, children:std::vec::Vec<Box<bindings::vm_area_struct>>,
    file:Box<bindings::file>, parent_mm:Box<bindings::mm_struct>, child_mm:Box<bindings::mm_struct>,
}
fn mm()->Box<bindings::mm_struct> { Box::new(bindings::mm_struct { __bindgen_anon_1:bindings::mm_union {
    __bindgen_anon_1:bindings::mm_fields { mm_count:bindings::atomic_t { counter:1 } },mm_users:bindings::atomic_t{counter:1} },users:Cell::new(1),drops:Cell::new(0) }) }
fn count(mm:&bindings::mm_struct)->i32 { unsafe { AtomicI32::from_ptr(ptr::addr_of!(mm.__bindgen_anon_1.__bindgen_anon_1.mm_count.counter).cast_mut()) }.load(Ordering::SeqCst) }
fn vma(mm:*mut bindings::mm_struct,file:*mut bindings::file,first:u64,last:u64,owner:Arc<VmaOwner>)->Box<bindings::vm_area_struct> {
    let raw=Arc::into_raw(owner).cast_mut().cast();
    Box::new(bindings::vm_area_struct {vm_mm:mm,vm_file:file,vm_private_data:raw,old_owner:raw,vm_ops:&VM_OPERATIONS.0,vm_pgoff:first/4096,
        __bindgen_anon_1:bindings::fields {__bindgen_anon_1:bindings::geometry {vm_start:first,vm_end:last}},
        __bindgen_anon_2:bindings::flags {__vm_flags:1024|2048|4096},writing:false,cleared:false})
}
impl Scenario {
    fn new()->Self {
        ALLOCATION.with(|a|a.set((0,0)));
        let mut parent_mm=mm(); let mut child_mm=mm();
        MODEL.with(|m|m.borrow_mut().mm=&mut *parent_mm);
        let current=CurrentMm::get().unwrap();
        let parent=Arc::new(Mirror {mm:MmIdentity::from_current(&current).unwrap(),start:0,end:0x8000,admission:AtomicBool::new(true),foreign_alias_seen:AtomicBool::new(false)},0).unwrap(); drop(current);
        let parent_registration=Arc::new(registration(0,2,0x9000),0).unwrap();
        let child_registration=Arc::new(registration(0,2,0x19000),0).unwrap();
        *parent_registration.mapping.lock()=Some(parent.clone());
        let owner=Arc::new(VmaOwner {registration:parent_registration.clone(),mirror:parent.clone()},0).unwrap();
        let mut file=Box::new(bindings::file {private_data:ptr::null_mut()});
        let parent_vma=vma(&mut *parent_mm,&mut *file,0,0x8000,owner.clone());
        let children=vec![vma(&mut *child_mm,&mut *file,0,0x4000,owner.clone()),vma(&mut *child_mm,&mut *file,0x4000,0x8000,owner.clone())];
        let mut scenario=Self {owner,parent,parent_registration,child_registration,parent_vma,children,file,parent_mm,child_mm};
        scenario.install(); scenario
    }
    fn install(&mut self) { MODEL.with(|m|*m.borrow_mut()=Model {mm:&mut *self.child_mm,vmas:self.children.iter_mut().map(|v|&mut **v as *mut _).collect(),locked:false,valid:true,events:vec![]}); ALLOCATION.with(|a|a.set((0,0))); }
    fn unchanged(&self, refs:usize) {
        assert_eq!(Arc::strong_count(&self.owner),refs);
        assert_eq!(count(&self.child_mm),1); assert_eq!(self.child_mm.users.get(),1);
        for v in &self.children { assert_eq!(v.vm_private_data,v.old_owner); assert!(!v.cleared); }
        MODEL.with(|m| { let m=m.borrow(); assert!(m.valid); assert!(!m.locked); assert!(!m.events.contains(&"write")); assert!(!m.events.contains(&"zap")); });
    }
    fn run(&self)->Result<Arc<Mirror>> { unsafe { Mirror::inherit_vmas(&self.parent,&self.parent_registration,self.child_registration.clone(),0,0x8000,|_| panic!("seal must not run on validation failure")) } }
}
impl Drop for Scenario { fn drop(&mut self) { unsafe { vma_close(&mut *self.parent_vma); for v in &mut self.children { vma_close(&mut **v); } } } }

// The actual consumer callbacks validate all inherited VMAs and derive proofs;
// callers can choose failures but never directly mint a seal or receipt.
unsafe extern "C" fn ihk_os_application_abort_fork_payload_v1(scope:*mut crate::application_abi::ForkPayloadScopeV1)->i32{unsafe{crate::provider_runtime::abort_fork_payload_application(scope)}}
unsafe extern "C" fn ihk_os_application_ready_fork_payload_v1(scope:*mut crate::application_abi::ForkPayloadScopeV1)->i32{unsafe{crate::provider_runtime::ready_fork_payload_application(scope)}}
fn original_request(second:bool)->crate::Request{
 let mut args=[0u64;6];unsafe{let request=guest_request();args.copy_from_slice(core::slice::from_raw_parts(request.add(24).cast::<u64>(),6))};if second{args[0]=1;args[1]=102;}
 let response=if second{0x1c00000u64}else{0x1b00000};
 let mut bytes=[0u8;128];bytes[8..12].copy_from_slice(&4i32.to_le_bytes());bytes[24..28].copy_from_slice(&0i32.to_le_bytes());bytes[32..36].copy_from_slice(&101i32.to_le_bytes());bytes[48..52].copy_from_slice(&101i32.to_le_bytes());bytes[52..56].copy_from_slice(&(if second{201i32}else{200}).to_le_bytes());bytes[56..64].copy_from_slice(&1u64.to_le_bytes());bytes[64..72].copy_from_slice(&56u64.to_le_bytes());for(n,a)in args.iter().enumerate(){bytes[72+n*8..80+n*8].copy_from_slice(&a.to_le_bytes());}bytes[120..128].copy_from_slice(&response.to_le_bytes());crate::Request::decode(&bytes,1).unwrap()
}
unsafe extern "C"{#[link_name="fork_carrier_guest_initialize"]fn guest_initialize()->i32;#[link_name="fork_carrier_guest_arena"]fn guest_arena()->*mut u8;#[link_name="fork_carrier_guest_arena_bytes"]fn guest_arena_bytes()->usize;#[link_name="fork_carrier_guest_request"]fn guest_request()->*const u8;#[link_name="fork_carrier_guest_accept"]fn guest_accept(stage:i32,result:i64)->i32;#[link_name="fork_carrier_guest_second_request"]fn guest_second_request()->i32;}
struct Joined {mm:Scenario,process:Arc<Process>,connections:Option<crate::provider_runtime::Connections>,remote:crate::Arc<crate::Remote>,memory:crate::Arc<crate::smp_memory::storage::Memory>,parent:crate::Token,child:crate::Token,worker:u64,serial:u64}
impl Joined {
 fn new()->Self{
  assert_eq!(unsafe{guest_initialize()},0);let mm=Scenario::new();CURRENT_PID.with(|p|p.set((102,2)));
  let process=Arc::new(Process{pid:ProcessId{number:102,identity:2},registration:Mutex(RefCell::new(None))},0).unwrap();
  let memory=crate::smp_memory::storage::new_fixture(unsafe{guest_arena()},unsafe{guest_arena_bytes()});let(remote,parent,child,worker,serial)=crate::smp_application::fixture(&memory,original_request(false));let mut connections=crate::provider_runtime::connections(remote.clone(),parent,child);let(p,c)=connections.raw();crate::provider_runtime::set_connection_contexts(p,c);
  Self{mm,process,connections:Some(connections),remote,memory,parent,child,worker,serial}
 }
 fn adopt(&mut self)->i32{
  let mut attempt=ForkAttempt{process:&self.process,parent:&self.mm.parent_registration,child:&self.mm.child_registration,parent_mirror:&self.mm.parent,descriptor:ForkDescriptor{root:0x19000,start:0,length:0x8000},called:false,published:false};
  let(p,c)=self.connections.as_mut().unwrap().raw();let geometry=crate::application_abi::ForkGeometryV1{root:0x19000,start:0,length:0x8000};
  let rc=unsafe{crate::provider_runtime::adopt_fork_application_v2(p,c,&geometry,crate::provider_runtime::consumer_module(),Some(completion::fork_proof_initial_construct),ptr::from_mut(&mut attempt).cast(),Some(completion::fork_proof_destroy),Some(completion::fork_verify_host),Some(completion::fork_proof_accept),Some(completion::fork_verify_link),Some(fork_adopt_consumer),ptr::from_mut(&mut attempt).cast())};
  if rc==0{assert!(attempt.called&&attempt.published);}rc
 }
 fn first_return(&mut self){assert_eq!(crate::smp_application::return_actual(&self.remote,self.parent,self.worker,self.serial,0,102),Ok(()));assert_eq!(self.remote.publish_syscall(self.parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(1,102)},0);assert_eq!(crate::smp_memory::storage::claims(&self.memory),(0,1));}
 fn link(&mut self)->(i32,u64,u64){assert_eq!(unsafe{guest_second_request()},0);let(w,s)=crate::smp_application::delivered(&self.remote,self.parent,&self.memory,original_request(true));let(p,_)=self.connections.as_mut().unwrap().raw();let result=unsafe{crate::provider_runtime::prepare_fork_link_application(p,w,s,0,0)};(result,w,s)}
 fn retain(mut self){let connections=self.connections.take().unwrap();crate::provider_runtime::retain_connections(connections);std::mem::forget(self);}
}


// Test-only retain-on-unwind guard: a failed assertion still fails libtest, but
// never treats the static guest arena as a safely destructible owned mapping.
// This does not catch errors or authorize any production cleanup/release.
struct RetainedJoined { value:Option<Joined> }
impl RetainedJoined { fn new()->Self{Self{value:Some(Joined::new())}} fn retain(self){} }
impl core::ops::Deref for RetainedJoined { type Target=Joined;fn deref(&self)->&Joined{self.value.as_ref().unwrap()} }
impl core::ops::DerefMut for RetainedJoined { fn deref_mut(&mut self)->&mut Joined{self.value.as_mut().unwrap()} }
impl Drop for RetainedJoined { fn drop(&mut self){if let Some(j)=self.value.take(){j.retain();}} }
fn concurrent_link_request()->crate::Request {
 let args=original_request(true).arguments();let mut bytes=[0u8;128];
 bytes[8..12].copy_from_slice(&4i32.to_le_bytes());bytes[24..28].copy_from_slice(&0i32.to_le_bytes());
 bytes[32..36].copy_from_slice(&101i32.to_le_bytes());bytes[48..52].copy_from_slice(&101i32.to_le_bytes());
 // Distinct authentic fixture Linux worker and matching Request requester.
 bytes[52..56].copy_from_slice(&202i32.to_le_bytes());bytes[56..64].copy_from_slice(&1u64.to_le_bytes());
 bytes[64..72].copy_from_slice(&56u64.to_le_bytes());for(n,a)in args.iter().enumerate(){bytes[72+n*8..80+n*8].copy_from_slice(&a.to_le_bytes());}
 // first_return() proved zero response claims, then parkedcontrol owns ONLY
 // 0x1c00000. Admit below must itself prove 0x1b00000 is available again.
 bytes[120..128].copy_from_slice(&0x1b00000u64.to_le_bytes());crate::Request::decode(&bytes,1).unwrap()
}

fn control_request(change:Option<(usize,u64)>)->crate::Request {
 let request=original_request(true);let mut args=request.arguments();args[0]=2;if let Some((i,v))=change{args[i]=v;}
 let mut bytes=[0u8;128];bytes[8..12].copy_from_slice(&4i32.to_le_bytes());bytes[24..28].copy_from_slice(&0i32.to_le_bytes());bytes[32..36].copy_from_slice(&101i32.to_le_bytes());bytes[48..52].copy_from_slice(&101i32.to_le_bytes());bytes[52..56].copy_from_slice(&201i32.to_le_bytes());bytes[56..64].copy_from_slice(&1u64.to_le_bytes());bytes[64..72].copy_from_slice(&56u64.to_le_bytes());for(n,a)in args.iter().enumerate(){bytes[72+n*8..80+n*8].copy_from_slice(&a.to_le_bytes());}bytes[120..128].copy_from_slice(&0x1c00000u64.to_le_bytes());crate::Request::decode(&bytes,1).unwrap()
}
fn control(j:&mut Joined,r:crate::Request)->(i32,u64,u64){let(w,s)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,r);let(p,_)=j.connections.as_mut().unwrap().raw();(unsafe{crate::provider_runtime::prepare_fork_control_application(p,w,s,0,-95)},w,s)}
#[test]fn actual_control_fresh_response_parked_once_and_blocks_link_return_removal(){
 let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();let before=crate::provider_runtime::control_pending_state();let r=control_request(None);
 let(rc,w,s)=control(&mut j,r.clone());assert_eq!(rc,1);assert_eq!(crate::provider_runtime::control_pending_state(),before);
 let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1);assert_eq!(state.3,crate::ForkPhase::FirstReturnPublished);assert_eq!(state.4,1);
 crate::smp_application::check_control_owned(&j.remote,j.parent,j.child,w,s,&r);crate::smp_application::control_no_release(&j.remote,j.parent,j.child);
 let(p,_)=j.connections.as_mut().unwrap().raw();assert!(unsafe{crate::provider_runtime::prepare_fork_control_application(p,w,s,0,-95)}<0);assert_eq!(crate::smp_application::control_state(&j.remote),state);
 assert_eq!(j.remote.publish_syscall(j.parent,0,|_|panic!("parked response must not publish"),||Ok(())),Ok(false));
 assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));let(lw,ls)=crate::smp_application::delivered_concurrent_link(&j.remote,j.parent,&j.memory,concurrent_link_request());assert!(unsafe{crate::provider_runtime::prepare_fork_link_application(p,lw,ls,0,0)}<0);assert_eq!(crate::smp_application::control_state(&j.remote),state);
 j.retain();
}
#[test]fn actual_control_wrong_identity_epoch_phase_and_overflow_have_no_transfer(){
 // Independent real owner/claim instances; each failure retains unchanged real response.
 for case in 0..4 {
  let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();
  let old=crate::provider_runtime::control_pending_state();let r=control_request(if case==0{Some((3,0x29000))}else{None});
  if case==1{crate::provider_runtime::alter_control_pending(None,Some(old.3+1));}
  if case==2{crate::provider_runtime::alter_control_pending(Some(2),None);}
  if case==3{crate::smp_application::parent_count(&j.remote,u32::MAX);}
  let before=crate::smp_application::control_state(&j.remote);let pending=crate::provider_runtime::control_pending_state();
  let(rc,_,_)=control(&mut j,r);assert!(rc<0,"case {case}");assert_eq!(crate::smp_application::control_state(&j.remote),before);assert_eq!(crate::provider_runtime::control_pending_state(),pending);j.retain();
 }
}
#[test]fn actual_control_restore_conflict_retains_exact_claim_and_response_after_close(){
 for replace_epoch in [false,true] {
  let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();let r=control_request(None);
  let(w,s)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,r.clone());
  let old=crate::provider_runtime::control_pending_state();let counts=crate::provider_runtime::pending_owner_counts();let memory=crate::smp_memory::storage::claims(&j.memory);
  assert_eq!(unsafe{crate::provider_runtime::park_with_restore_conflict(&j.remote,j.parent,w,s,replace_epoch)},-5);
  let after=crate::provider_runtime::control_pending_state();assert_eq!(after.0,if replace_epoch{4}else{2});assert_eq!(after.3,old.3+u64::from(replace_epoch));assert_eq!((after.1,after.2),(old.1,old.2));
  assert_eq!(crate::provider_runtime::pending_owner_counts(),(counts.0+1,counts.1+1,counts.2+1));
  assert_eq!(crate::smp_memory::storage::claims(&j.memory),memory);let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1&&state.2);
  crate::smp_application::check_control_owned(&j.remote,j.parent,j.child,w,s,&r);
  crate::smp_application::close_worker_actual(&j.remote,j.parent,w);assert_eq!(crate::smp_memory::storage::claims(&j.memory),memory);let after=crate::smp_application::control_state(&j.remote);assert_eq!(after.0,2);assert!(after.1);j.retain();
 }
}
#[test]fn actual_control_ordinary_first_return_passes_without_pin_or_payload_effect(){
 let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);let before=crate::provider_runtime::control_pending_state();let state=crate::smp_application::control_state(&j.remote);
 let(p,_)=j.connections.as_mut().unwrap().raw();assert_eq!(unsafe{crate::provider_runtime::prepare_fork_control_application(p,j.worker,j.serial,0,102)},0);assert_eq!(crate::provider_runtime::control_pending_state(),before);assert_eq!(crate::smp_application::control_state(&j.remote),state);j.first_return();j.retain();
}

#[test]fn actual_durable_parent_pin_survives_positive_first_ret_failed_link_and_parent_close(){
 let mut j=Joined::new();assert_eq!(j.adopt(),0);
 crate::smp_application::check_parent_pin(&j.remote,j.parent,j.child);
 j.first_return();crate::smp_application::check_parent_pin(&j.remote,j.parent,j.child);
 j.mm.children[1].vm_pgoff+=1;let(rc,w,_)=j.link();assert!(rc<0);
 crate::smp_application::check_parent_pin(&j.remote,j.parent,j.child);
 crate::smp_application::close_worker_actual(&j.remote,j.parent,w);
 crate::smp_application::check_parent_pin(&j.remote,j.parent,j.child);
 assert_eq!(crate::provider_runtime::retained(),1);j.retain();
}
#[test]fn actual_memory_ingress_first_and_link_writer_publish_to_original_guest_consumer(){let mut j=Joined::new();assert_eq!(j.adopt(),0);assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::AdoptedAwaitFirstReturn);assert_eq!(crate::provider_runtime::retained(),1);j.first_return();assert!(!crate::smp_application::scheduled(&j.remote));let(rc,w,s)=j.link();assert_eq!(rc,0);assert_eq!(j.mm.child_mm.users.get(),1,"transient child mm_users escaped LINK callback");assert!(!crate::smp_application::scheduled(&j.remote));assert_eq!(crate::smp_application::return_actual(&j.remote,j.parent,w,s,0,0),Ok(()));assert_eq!(j.remote.publish_syscall(j.parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(2,0)},0);assert!(crate::smp_application::scheduled(&j.remote));assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::Linked);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(0,1));j.retain();}
#[test]fn actual_wrong_child_mm_vma_rejects_link_before_seal_and_keeps_payload_owner(){let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();j.mm.children[1].vm_pgoff+=1;let(rc,_,_)=j.link();assert!(rc<0);assert!(!crate::smp_application::scheduled(&j.remote));assert_eq!(crate::provider_runtime::retained(),1);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));assert_eq!(unsafe{guest_accept(2,0)},-11);j.retain();}
#[test]fn actual_parent_close_before_ticket_cannot_publish_automatic_negative(){let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();assert_eq!(unsafe{guest_second_request()},0);let(w,_)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,original_request(true));crate::smp_application::close_worker_actual(&j.remote,j.parent,w);assert_eq!(j.remote.publish_syscall(j.parent,0,|_|panic!("automatic negative exposed"),||panic!("notify before proof")),Ok(false));assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));assert_eq!(crate::provider_runtime::retained(),1);j.retain();}
#[test]fn actual_stale_generation_rejects_before_payload_or_mm_effect(){let mut j=Joined::new();crate::smp_application::corrupt_generation(&j.remote);assert!(j.adopt()<0);assert!(!crate::smp_application::fork_present(&j.remote));assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,0));assert!(j.mm.children.iter().all(|v|!v.cleared));j.retain();}
#[test]fn actual_link_before_first_ret_is_not_a_handoff_permission(){let mut j=Joined::new();assert_eq!(j.adopt(),0);let(w,s)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,original_request(true));let(p,_)=j.connections.as_mut().unwrap().raw();assert!(unsafe{crate::provider_runtime::prepare_fork_link_application(p,w,s,0,0)}<0);assert!(!crate::smp_application::scheduled(&j.remote));assert_eq!(crate::smp_memory::storage::claims(&j.memory),(2,1));j.retain();}

fn wire_kind()->u32{let mut args=[0u64;6];unsafe{let request=guest_request();args.copy_from_slice(core::slice::from_raw_parts(request.add(24).cast::<u64>(),6));let p=guest_arena().add((args[4]-0x1000000)as usize);if core::slice::from_raw_parts(p,8)!=b"MCFKW001"{return 0;}u32::from_le_bytes([p.add(16).read_volatile(),p.add(17).read_volatile(),p.add(18).read_volatile(),p.add(19).read_volatile()])}}
#[test]fn actual_immediate_link_after_first_writer_unlock_precedes_outer_adopt_return(){
 let mut j=Joined::new();let remote=j.remote.clone();let memory=j.memory.clone();let parent=j.parent;let worker=j.worker;let serial=j.serial;let(p,_)=j.connections.as_mut().unwrap().raw();let p=p as usize;let fired=std::rc::Rc::new(Cell::new(false));let seen=fired.clone();let active=std::rc::Rc::new(Cell::new(true));let in_call=active.clone();
 crate::UNLOCK_HOOK.with(|h|*h.borrow_mut()=Some(std::boxed::Box::new(move||{if wire_kind()!=1{return false;}assert!(in_call.get(),"hook happened after outer adoption returned");seen.set(true);assert_eq!(crate::smp_application::return_actual(&remote,parent,worker,serial,0,102),Ok(()));assert_eq!(remote.publish_syscall(parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(1,102)},0);assert_eq!(unsafe{guest_second_request()},0);let(w,s)=crate::smp_application::delivered(&remote,parent,&memory,original_request(true));assert_eq!(unsafe{crate::provider_runtime::prepare_fork_link_application(p as*mut c_void,w,s,0,0)},0);assert_eq!(crate::smp_application::return_actual(&remote,parent,w,s,0,0),Ok(()));assert_eq!(remote.publish_syscall(parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(2,0)},0);true})));
 assert_eq!(j.adopt(),0);active.set(false);assert!(fired.get());assert_eq!(wire_kind(),2);assert_eq!(j.mm.child_mm.users.get(),1);assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::Linked);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(0,1));j.retain();
}
#[test]fn actual_host_between_ready_and_checked_finish_blocks_kind1_ret_and_revoke(){
 let mut j=Joined::new();let(_,c)=j.connections.as_mut().unwrap().raw();let c=c as usize;let fired=std::rc::Rc::new(Cell::new(false));let seen=fired.clone();
 crate::READY_HOOK.with(|h|*h.borrow_mut()=Some(std::boxed::Box::new(move||{seen.set(true);let key=crate::provider_runtime::current_key();let events=MODEL.with(|m|m.borrow().events.clone());assert_eq!(unsafe{crate::provider_runtime::fork_progress_application(c as*mut c_void,&key,crate::application_abi::FORK_HOST_REVOKED_V1,None,ptr::null_mut())},-16);assert_eq!(MODEL.with(|m|m.borrow().events.clone()),events,"prepared HOST reached verifier/MM");assert_eq!(wire_kind(),0);})));
 assert!(j.adopt()<0);assert!(fired.get());assert_eq!(wire_kind(),0);assert!(j.mm.child_registration.mapping.lock().as_ref().unwrap().admission.load(Ordering::Acquire),"host verifier ran despite prepared lease");assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::Quarantined);assert_eq!(j.remote.publish_syscall(j.parent,0,|_|panic!("first RET after abort"),||panic!("notify after abort")),Ok(false));assert_eq!(unsafe{guest_accept(1,102)},-11);assert_eq!(crate::provider_runtime::retained(),1);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));j.retain();
}
#[test]fn actual_sealed_link_finish_error_retains_same_ticket_and_retries_identical_receipt(){
 let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();let remote=j.remote.clone();crate::MM_UNLOCK_HOOK.with(|h|*h.borrow_mut()=Some(std::boxed::Box::new(move||crate::smp_application::transport_failure(&remote,true))));let(rc,w,s)=j.link();assert_eq!(rc,-5);assert_eq!(wire_kind(),1);assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::FirstReturnPublished);assert!(!crate::smp_application::scheduled(&j.remote));assert_eq!(crate::smp_application::cancel_child(&j.remote,j.child),Err(-16));assert_eq!(crate::smp_application::return_actual(&j.remote,j.parent,w,s,0,-125),Err(-16));assert_eq!(crate::provider_runtime::retained(),1);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));crate::smp_application::transport_failure(&j.remote,false);let(p,_)=j.connections.as_mut().unwrap().raw();assert_eq!(unsafe{crate::provider_runtime::prepare_fork_link_application(p,w,s,0,0)},0);assert_eq!(wire_kind(),2);assert_eq!(crate::smp_application::return_actual(&j.remote,j.parent,w,s,0,0),Ok(()));assert_eq!(j.remote.publish_syscall(j.parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(2,0)},0);assert!(crate::smp_application::scheduled(&j.remote));assert_eq!(j.mm.child_mm.users.get(),1);j.retain();
}
#[test]fn actual_same_ticket_repeat_keeps_sequence_and_duplicate_ret_has_no_effect(){
 let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();let(rc,w,s)=j.link();assert_eq!(rc,0);let(p,_)=j.connections.as_mut().unwrap().raw();assert_eq!(unsafe{crate::provider_runtime::prepare_fork_link_application(p,w,s,0,0)},0);assert_eq!(wire_kind(),2);assert_eq!(crate::smp_application::return_actual(&j.remote,j.parent,w,s,0,0),Ok(()));assert_eq!(j.remote.publish_syscall(j.parent,0,|_|Ok(()),||Ok(())),Ok(true));assert_eq!(unsafe{guest_accept(2,0)},0);assert!(crate::smp_application::return_actual(&j.remote,j.parent,w,s,0,0).is_err());assert_eq!(wire_kind(),2);assert_eq!(j.mm.child_mm.users.get(),1);assert_eq!(crate::smp_memory::storage::claims(&j.memory),(0,1));j.retain();
}

}
}

mod guest_record_init{use core::{ffi::c_void,sync::atomic::{AtomicI32,Ordering}};type CInt=i32;type CULong=u64;const EINVAL:i32=22;
#[repr(C)]
#[derive(Clone, Copy)]
pub struct ProcessForkDestroyIdentity {
    pub slot: u32,
    pub child_pid: CInt,
    pub generation: CULong, pub parent: CULong, pub worker: CULong,
    pub delivery: CULong, pub child: CULong, pub child_mm: CULong,
    pub root: CULong, pub start: CULong, pub length: CULong, pub nonce: CULong,
}
#[repr(C)]
pub struct ProcessForkDestroyRecord {
    pub identity: ProcessForkDestroyIdentity,
    pub thread: *mut c_void,
    pub phase: CInt,
    pub result: CInt,
}

fn fork_destroy_identity_valid(key: &ProcessForkDestroyIdentity) -> bool {
    key.generation != 0 && key.parent != 0 && key.worker != 0 && key.delivery != 0
        && key.child != 0 && key.child != key.parent && key.child_pid > 0 && key.child_mm != 0
        && key.root != 0 && key.root % 4096 == 0 && key.start % 4096 == 0
        && key.length != 0 && key.length % 4096 == 0
        && key.start.checked_add(key.length).is_some() && key.nonce != 0
}
#[no_mangle]
pub unsafe extern "C" fn process_fork_destroy_record_init_result(
    record: *mut ProcessForkDestroyRecord, identity: *const ProcessForkDestroyIdentity,
    thread: *mut c_void,
) -> CInt {
    if record.is_null() || identity.is_null() || thread.is_null() { return -EINVAL; }
    let key = *identity;
    if !fork_destroy_identity_valid(&key) { return -EINVAL; }
    let phase = AtomicI32::from_ptr(core::ptr::addr_of_mut!((*record).phase));
    if phase.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire).is_err() { return -16; }
    (*record).identity = key;
    (*record).thread = thread;
    (*record).result = 0;
    phase.store(2, Ordering::Release);
    0
}

}


thread_local!{static UNLOCK_HOOK:std::cell::RefCell<Option<std::boxed::Box<dyn FnMut()->bool>>>=const{std::cell::RefCell::new(None)};static MM_UNLOCK_HOOK:std::cell::RefCell<Option<std::boxed::Box<dyn FnOnce()>>>=const{std::cell::RefCell::new(None)};static READY_HOOK:std::cell::RefCell<Option<std::boxed::Box<dyn FnOnce()>>>=const{std::cell::RefCell::new(None)};}
fn run_unlocked_hook(){if LOCK_DEPTH.with(|v|v.get())!=0{return;}let hook=UNLOCK_HOOK.with(|h|h.borrow_mut().take());if let Some(mut h)=hook{MM_ACTIVE.with(|m|assert!(!m.get()));if !h(){UNLOCK_HOOK.with(|v|*v.borrow_mut()=Some(h));}}}
fn run_mm_unlock_hook(){let hook=MM_UNLOCK_HOOK.with(|h|h.borrow_mut().take());if let Some(h)=hook{LOCK_DEPTH.with(|v|assert_eq!(v.get(),0));MM_ACTIVE.with(|m|assert!(!m.get()));h();}}
#[no_mangle]unsafe extern "C" fn fixture_ready_fork_payload_v1(scope:*mut application_abi::ForkPayloadScopeV1)->i32{let rc=unsafe{provider_runtime::ready_fork_payload_application(scope)};if rc==0{let hook=READY_HOOK.with(|h|h.borrow_mut().take());if let Some(h)=hook{LOCK_DEPTH.with(|v|assert_eq!(v.get(),0));MM_ACTIVE.with(|m|assert!(!m.get()));h();}}rc}
