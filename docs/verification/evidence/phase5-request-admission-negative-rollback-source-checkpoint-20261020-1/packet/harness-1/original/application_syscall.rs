// SPDX-License-Identifier: GPL-2.0
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

/// Metadata built only by the exact sealed backend owner. No field grants
/// a root/task/MM/runnable/revoke/final-ACK permit; Request owns its provenance.
pub(crate) struct ForkFirstReceipt {
    pub slot:u32,pub generation:u64,pub parent:u64,pub worker:u64,pub delivery:u64,
    pub child:u64,pub child_pid:i32,pub child_mm:u64,pub root:u64,pub start:u64,pub length:u64,
    pub nonce:u64,pub response:u64,
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

    /// Current MCFKC001 args[4] is a physical carrier, never the nonce.
    /// Called only after the original Response owner claims and copies it.
    pub(crate) fn current_fork_carrier(&self, bytes:&[u8;128]) -> Result<u64,i32> {
        let args=self.arguments();
        let word=|at|u64::from_le_bytes(bytes[at..at+8].try_into().unwrap());
        if self.number()!=56 || matches!(args[0],1|2|3) || args[5]!=0x313030434b46434d
            || args[4]==0 || args[4]%8!=0 || args[4].checked_add(128).is_none()
            || bytes[..8]!=*b"MCFKQ001" || bytes[8..12]!=[1,0,56,0]
            || u32::from_le_bytes(bytes[12..16].try_into().unwrap())!=128
            || u32::from_le_bytes(bytes[16..20].try_into().unwrap())!=1
            || bytes[20..24]!=[0;4] || word(24)==0 || word(32)!=args[3]
            || word(40)!=args[1] || word(48)!=args[2] || bytes[56..].iter().any(|b|*b!=0)
            || args[3]==0 || args[3]%4096!=0 || args[1]%4096!=0
            || args[2]==0 || args[2]%4096!=0 || args[1].checked_add(args[2]).is_none()
        {return Err(-13);}
        Ok(word(24))
    }

    pub(crate) fn first_fork_receipt(&self,key:&ForkFirstReceipt)->Result<[u8;128],i32> {
        let a=self.arguments();
        if self.number()!=56||matches!(a[0],1|2|3)||a[5]!=0x313030434b46434d
            ||key.generation==0||key.parent==0||key.worker==0||key.delivery==0
            ||key.child==0||key.child==key.parent||key.child_pid<=0||key.child_mm==0||key.nonce==0
            ||key.response!=self.response()||key.root!=a[3]||key.start!=a[1]||key.length!=a[2]
            ||key.root==0||key.root%4096!=0||key.start%4096!=0||key.length==0
            ||key.length%4096!=0||key.start.checked_add(key.length).is_none(){return Err(-13);}
        let mut out=[0;128];out[..8].copy_from_slice(b"MCFKW001");out[8..12].copy_from_slice(&[1,0,40,0]);
        out[12..16].copy_from_slice(&128u32.to_le_bytes());out[16..20].copy_from_slice(&1u32.to_le_bytes());
        out[24..32].copy_from_slice(&1u64.to_le_bytes());out[32..40].copy_from_slice(&(key.child_pid as u64).to_le_bytes());
        out[40..44].copy_from_slice(&key.slot.to_le_bytes());out[44..48].copy_from_slice(&key.child_pid.to_le_bytes());
        for(at,value)in[(48,key.generation),(56,key.parent),(64,key.worker),(72,key.delivery),(80,key.child),
            (88,key.child_mm),(96,key.root),(104,key.start),(112,key.length),(120,key.nonce)] {
            out[at..at+8].copy_from_slice(&value.to_le_bytes());
        }
        Ok(out)
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

    /// Observe only the original response before parking it for fork work.
    /// This does not grant fork authority or publish any protocol word.
    pub(crate) fn check_unpublished(&mut self, expected: &Request) -> Result<(), i32> {
        if &self.request != expected { return Err(-13); }
        let address = self.memory.address();
        // SAFETY: Response owns this exact aligned complete mapping claim.
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(-71);
        }
        Ok(())
    }

    /// Claim the guest's wake state exactly once. On a protocol error the outer
    /// owner must retain/quarantine the mapping, never fabricate completion.
    pub(crate) fn prepare(self,servicing_tid:i32,value:i64)->Result<Completion<M>,i32> {
        self.prepare_retained(servicing_tid,value).map_err(|(_owner,error)|error)
    }

    /// Cancellation/rollback callers preserve the actual original response
    /// on EVERY failed publication preparation, including a changed peer state.
    pub(crate) fn prepare_retained(mut self, servicing_tid:i32,value:i64)
        -> Result<Completion<M>,(Self,i32)> {
        // Original host cancellation and in-kernel services use stid zero.
        if servicing_tid < 0 {
            return Err((self,-22));
        }
        // SAFETY: The constructor's exclusive response claim and retained
        // mapping cover all these aligned fields for this complete operation.
        let address = self.memory.address();
        let status = unsafe { AtomicU64::from_ptr(address.add(8).cast()) };
        // SAFETY: The same exclusive retained response mapping contains the
        // independently aligned state word at byte offset 16 for this operation.
        let state = unsafe { AtomicU64::from_ptr(address.add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err((self,-71));
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
                if state.compare_exchange(2,1,Ordering::AcqRel,Ordering::Acquire).is_err() {
                    return Err((self,-71));
                }
                Some(self.request.wake())
            }
            Err(_) => return Err((self,-71)),
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

impl<M: ResponseMemory> Response<M> { pub(crate) fn fixture_replace_request(&mut self, other: Request) { self.request=other; } }

impl Delivery { pub(crate) fn fixture_phase_snapshot(&self)->std::string::String { format!("{:?}",self.phase) } }
