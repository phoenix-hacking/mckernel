// Deterministic Linux adapters for actual shutdown epoch/CPU proof bodies.
// Hardware CPU reset, real Linux callback drain and physical release are not tested.
#![allow(dead_code)]
// Additional deterministic owners for consumed production shutdown consumers.
// Linux namespace removal, real task exit and actual hardware remain boundaries.
static IRQ_PRE_STATUS:AtomicI32=AtomicI32::new(0);
static SERVICE_LOCKS:AtomicU32=AtomicU32::new(0);
static JOIN_COUNT:AtomicU32=AtomicU32::new(0);
static JOIN_BLOCK:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
static JOIN_ENTERED:AtomicU32=AtomicU32::new(0);
static NAMESPACE_DROPS:AtomicU32=AtomicU32::new(0);
static CALLBACK_DRAIN_BLOCK:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
static CALLBACK_DRAIN_ENTERED:AtomicU32=AtomicU32::new(0);
static CALLBACK_STORAGE_DROPS:AtomicU32=AtomicU32::new(0);
static MEMORY_COMMITS:AtomicU32=AtomicU32::new(0);
static IRQ_RELEASE_STATUS:AtomicI32=AtomicI32::new(0);
static MAP_STATUS:AtomicI32=AtomicI32::new(0);
static INJECT_STALE:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
struct AdapterMutex<T>(std::sync::Mutex<T>);
impl<T> AdapterMutex<T> {
 fn new(value:T)->Self{Self(std::sync::Mutex::new(value))}
 fn lock(&self)->CountedGuard<'_,T>{let guard=self.0.lock().unwrap();SERVICE_LOCKS.fetch_add(1,Ordering::AcqRel);CountedGuard{guard,counter:&SERVICE_LOCKS}}
}
fn no_dependent_locks(){assert_eq!((CPU_LOCKS.load(Ordering::Acquire),MEMORY_LOCKS.load(Ordering::Acquire),HOTPLUG_LOCKS.load(Ordering::Acquire),SERVICE_LOCKS.load(Ordering::Acquire)),(0,0,0,0));}
trait ErrorNumber {fn to_errno(self)->i32;}
impl ErrorNumber for i32 {fn to_errno(self)->i32{self}}
mod kernel {pub mod error {pub type Error=i32;}}
const EINVAL:i32=-22;
const IHK_SMP_SHUTDOWN_V6_POST_EFFECT:i64=1_i64<<62;
static OBSERVATION_LOGS:std::sync::Mutex<Vec<String>>=std::sync::Mutex::new(Vec::new());
static OBSERVE_MANY:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
macro_rules! pr_info {($($t:tt)*)=>{{crate::OBSERVATION_LOGS.lock().unwrap().push(format!($($t)*));}}}
fn shutdown_v6_post_effect(error: kernel::error::Error) -> i64 {
    IHK_SMP_SHUTDOWN_V6_POST_EFFECT | (error.to_errno() as u32 as i64)
}
unsafe extern "C" fn ihk_smp_shutdown_v6(slot: u32, generation: u64) -> i64 {
    let owner = match unsafe { smp_resource::OsToken::from_ihk_lease_v2(slot, generation) } {
        Ok(owner) => owner,
        Err(_) => return EINVAL.to_errno() as i64,
    };

    // This actual callback retains os_runtime's synchronous operation/module
    // lease while one boot claim spans every stage, including final commit.
    let boot = match smp_memory::claim_shutdown_boot(owner) {
        Ok(boot) => boot,
        Err(error) => {
            pr_info!("IHK-SMP: shutdown os={} generation={} stage=claim result={} effect=pre\n", slot, generation, error.to_errno());
            return error.to_errno() as i64;
        }
    };
    match smp_cpu::shutdown_os_boot(boot) {
        Ok(()) => {
            pr_info!("IHK-SMP: shutdown os={} generation={} stage=reconcile result=0 effect=complete\n", slot, generation);
            0
        }
        Err(failure) => {
            pr_info!("IHK-SMP: shutdown os={} generation={} stage={} result={} effect={}\n", slot, generation,
                failure.stage, failure.error.to_errno(), if failure.post_effect { "post" } else { "pre" });
            if failure.post_effect { shutdown_v6_post_effect(failure.error) }
                else { failure.error.to_errno() as i64 }
        }
    }
}


fn reset_integration_state(){OBSERVATION_LOGS.lock().unwrap().clear();OBSERVE_MANY.store(false,Ordering::Release);CALLBACK_DRAIN_BLOCK.store(false,Ordering::Release);for counter in [&CALLBACK_DRAIN_ENTERED,&CALLBACK_STORAGE_DROPS,&JOIN_COUNT,&JOIN_ENTERED,&NAMESPACE_DROPS,&MEMORY_COMMITS]{counter.store(0,Ordering::Release);}JOIN_BLOCK.store(false,Ordering::Release);IRQ_RELEASE_STATUS.store(0,Ordering::Release);IRQ_PRE_STATUS.store(0,Ordering::Release);MAP_STATUS.store(0,Ordering::Release);INJECT_STALE.store(false,Ordering::Release);}

use std::sync::atomic::{AtomicI32, AtomicU32, Ordering};
static CPU_LOCKS: AtomicU32 = AtomicU32::new(0);
static MEMORY_LOCKS: AtomicU32 = AtomicU32::new(0);
static HOTPLUG_LOCKS: AtomicU32 = AtomicU32::new(0);
static STOP_CALLS: AtomicU32 = AtomicU32::new(0);
static IRQ_STATUS: AtomicI32 = AtomicI32::new(0);
struct CountedGuard<'a, T> { guard: std::sync::MutexGuard<'a,T>, counter: &'static AtomicU32 }
impl<T> std::ops::Deref for CountedGuard<'_,T> { type Target=T; fn deref(&self)->&T { &self.guard } }
impl<T> std::ops::DerefMut for CountedGuard<'_,T> { fn deref_mut(&mut self)->&mut T { &mut self.guard } }
impl<T> Drop for CountedGuard<'_,T> { fn drop(&mut self) { self.counter.fetch_sub(1,Ordering::AcqRel); } }
mod smp_resource { pub(super) use super::smp_cpu::OsToken; }
mod sysfs_remote {pub(super) fn fixture_service_remote()->Arc<Remote>{setup(0)}
impl Remote {pub(super) fn fixture_callbacks(&self,n:usize){self.state.lock().callbacks=n;}}

// Production Remote call/wait/publish/reply/shutdown and Attribute Drop bodies
// execute with std synchronization. Linux callback removal and hardware are
// outside this test; SharedData backing stays owned by the test until join.

use std::{ptr, sync::{Arc, atomic::{AtomicBool, Ordering}}, time::{Duration, Instant}};
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Error(pub(crate) i32);
impl Error { fn to_errno(self) -> i32 { self.0 } }
type Result<T = ()> = std::result::Result<T, Error>;
const EIO: Error = Error(-5);
const EINVAL: Error = Error(-22);
const ENODEV: Error = Error(-19);
const EINTR: Error = Error(-4);
const EBUSY: Error = Error(-16);
mod kernel { pub mod error { pub fn to_result(n: i32) -> super::super::Result { if n < 0 { Err(super::super::Error(n)) } else { Ok(()) } } } }
macro_rules! pr_err { ($($t:tt)*) => { { let _ = format_args!($($t)*); } } }
mod sysfs_request { #[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Client {
    pub(crate) operations: u64,
    pub(crate) instance: u64,
}
}
mod sysfs_rpc { // SPDX-License-Identifier: GPL-2.0-only
// Single-buffer remote sysfs exchange adapted from mcctrl's Rust RPC bodies.
//
// The Linux adapter serializes access to this state and the owned data page.
// A waiter leaving does not cancel publication: only a matching response or
// a proven pre-publication send failure permits the data page to be reused.

use super::sysfs_request::Client;
use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const PACKET_BYTES: usize = 128;
pub(crate) const DATA_BYTES: usize = 4096;
static NEXT_TOKEN: AtomicU64 = AtomicU64::new(1);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct Token(u64);

impl Token {
    pub(crate) fn wire(self) -> u64 {
        self.0
    }

    fn allocate() -> Result<Self, i32> {
        NEXT_TOKEN
            .fetch_update(Ordering::Relaxed, Ordering::Relaxed, |value| {
                (value < i64::MAX as u64).then(|| value + 1)
            })
            .map(Self)
            .map_err(|_| -75)
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum Call {
    Show { capacity: usize },
    Store { bytes: usize },
    Release,
}

impl Call {
    fn message(self) -> i32 {
        match self {
            Self::Show { .. } => 0x3a,
            Self::Store { .. } => 0x3c,
            Self::Release => 0x3e,
        }
    }

    fn limit(self) -> usize {
        match self {
            Self::Show { capacity } => capacity,
            Self::Store { bytes } => bytes,
            Self::Release => 0,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Phase {
    Queued,
    Published,
    Complete(Result<usize, i32>),
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Pending {
    token: Token,
    client: Client,
    call: Call,
    phase: Phase,
}

pub(crate) struct Exchange {
    pending: Option<Pending>,
}

impl Exchange {
    pub(crate) const fn new() -> Self {
        Self { pending: None }
    }

    pub(crate) fn token(&self) -> Option<Token> {
        self.pending.map(|pending| pending.token)
    }

    /// The caller must fill store bytes before releasing its shared-state lock.
    /// Special ops are mapped snooping requests, never remote function tokens.
    pub(crate) fn begin(&mut self, client: Client, call: Call) -> Result<Token, i32> {
        if self.pending.is_some() {
            return Err(-16);
        }
        if (1..=1000).contains(&client.operations) || call.limit() > DATA_BYTES {
            return Err(-22);
        }
        let token = Token::allocate()?;
        self.pending = Some(Pending {
            token,
            client,
            call,
            phase: Phase::Queued,
        });
        Ok(token)
    }

    /// Peeking does not transfer ownership. A full transport queue may retry
    /// these exact bytes until publication, with no duplicated guest request.
    pub(crate) fn outgoing(&self) -> Option<(Token, [u8; PACKET_BYTES])> {
        let pending = self.pending?;
        if pending.phase != Phase::Queued {
            return None;
        }
        let mut packet = [0; PACKET_BYTES];
        packet[8..12].copy_from_slice(&pending.call.message().to_le_bytes());
        if let Call::Store { bytes } = pending.call {
            packet[12..16].copy_from_slice(&(bytes as i32).to_le_bytes());
        }
        packet[24..32].copy_from_slice(&pending.token.wire().to_le_bytes());
        packet[32..40].copy_from_slice(&pending.client.operations.to_le_bytes());
        packet[40..48].copy_from_slice(&pending.client.instance.to_le_bytes());
        Some((pending.token, packet))
    }

    /// The adapter holds its state lock across queue publication and this
    /// transition, before notification or response dispatch can acquire it.
    pub(crate) fn published(&mut self, token: Token) -> Result<(), i32> {
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token != token || pending.phase != Phase::Queued {
            return Err(-16);
        }
        pending.phase = Phase::Published;
        Ok(())
    }

    /// Only a transport failure proven to precede publication can use this.
    /// IPI failure after queue publication leaves the exchange outstanding.
    pub(crate) fn fail_unpublished(&mut self, token: Token, error: i32) -> Result<(), i32> {
        if !(-4095..0).contains(&error) {
            return Err(-22);
        }
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token != token || pending.phase != Phase::Queued {
            return Err(-16);
        }
        pending.phase = Phase::Complete(Err(error));
        Ok(())
    }

    /// Queue acquisition must already synchronize the peer's preceding data
    /// writes. Stale, foreign or wrong-kind replies never complete this call.
    pub(crate) fn accept(&mut self, packet: &[u8]) -> Result<(), i32> {
        if packet.len() != PACKET_BYTES {
            return Err(-22);
        }
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        let error = i32::from_le_bytes(packet[12..16].try_into().unwrap());
        let token = u64::from_le_bytes(packet[24..32].try_into().unwrap());
        let result = i64::from_le_bytes(packet[32..40].try_into().unwrap());
        let pending = self.pending.as_mut().ok_or(-2)?;
        if pending.token.wire() != token || message != pending.call.message() + 1 {
            return Err(-2);
        }
        if pending.phase != Phase::Published {
            return Err(-16);
        }
        // The matching response retires the peer callback even when its count
        // is invalid. Record an error without exposing any out-of-bounds data.
        let status = if error != if result < 0 { result as i32 } else { 0 } || result < -4095 {
            Err(-71)
        } else if result < 0 {
            Err(result as i32)
        } else if result as u64 > pending.call.limit() as u64 {
            Err(-75)
        } else {
            Ok(result as usize)
        };
        pending.phase = Phase::Complete(status);
        Ok(())
    }

    pub(crate) fn completed(&self, token: Token) -> Result<bool, i32> {
        let pending = self.pending.ok_or(-2)?;
        if pending.token != token {
            return Err(-2);
        }
        Ok(matches!(pending.phase, Phase::Complete(_)))
    }

    /// The same serial caller keeps the data page excluded until it has copied
    /// a successful show result. No timeout/interruption may invoke this early.
    pub(crate) fn finish(&mut self, token: Token) -> Result<Result<usize, i32>, i32> {
        let pending = self.pending.ok_or(-2)?;
        if pending.token != token {
            return Err(-2);
        }
        let Phase::Complete(result) = pending.phase else {
            return Err(-16);
        };
        self.pending = None;
        Ok(result)
    }
}

}
use sysfs_request::Client;
use sysfs_rpc::{Call, Exchange, PACKET_BYTES};
struct Mutex<T>(std::sync::Mutex<T>);
struct Guard<'a,T>(Option<std::sync::MutexGuard<'a,T>>);
impl<T> Mutex<T> {
    fn new(v:T)->Self { Self(std::sync::Mutex::new(v)) }
    fn lock(&self)->Guard<'_,T> { Guard(Some(self.0.lock().unwrap())) }
}
impl<T> std::ops::Deref for Guard<'_,T> { type Target=T; fn deref(&self)->&T { self.0.as_ref().unwrap() } }
impl<T> std::ops::DerefMut for Guard<'_,T> { fn deref_mut(&mut self)->&mut T { self.0.as_mut().unwrap() } }
struct CondVar { cv: std::sync::Condvar, interrupt: AtomicBool }
impl CondVar {
    fn new()->Self { Self { cv: std::sync::Condvar::new(), interrupt: AtomicBool::new(false) } }
    fn wait<T>(&self,g:&mut Guard<'_,T>) { g.0=Some(self.cv.wait(g.0.take().unwrap()).unwrap()); }
    fn wait_interruptible<T>(&self,g:&mut Guard<'_,T>)->bool {
        self.wait(g); self.interrupt.swap(false,Ordering::AcqRel)
    }
    fn notify_all(&self) { self.cv.notify_all(); }
}
type Owner=super::smp_resource::OsToken;
fn owner(slot:u32,generation:u64)->Owner {super::smp_cpu::fixture_owner(slot,generation)}
struct SharedData { owner:Owner, address:u64 }
pub(crate) struct PeerStopped<'boot> {
    cpus: &'boot super::smp_cpu::StoppedCpus<'boot>,
}
impl<'boot> PeerStopped<'boot> {
    pub(super) fn after_reset(cpus: &'boot super::smp_cpu::StoppedCpus<'boot>) -> Self {
        Self { cpus }
    }
    pub(super) fn matches_owner(&self, owner: super::smp_resource::OsToken) -> bool {
        self.cpus.matches_owner(owner)
    }
    pub(super) fn matches_boot(&self, boot: &super::smp_memory::ShutdownBoot) -> bool {
        self.cpus.matches_boot(boot)
    }
}
struct State {
    exchange: Exchange,
    caller: bool,
    callbacks: usize,
    peer_stopped: bool,
}
pub(crate) struct Remote { data:SharedData, state:Mutex<State>, changed:CondVar }
fn errno(value: i32) -> Error {
    kernel::error::to_result(value).err().unwrap_or(EIO)
}
impl Remote { pub(crate) fn shutdown_after_peer_stop(&self, proof: &PeerStopped<'_>) -> Result<bool> {
        if !proof.matches_owner(self.data.owner) {
            return Err(EINVAL);
        }
        let mut state = self.state.lock();
        state.peer_stopped = true;
        let drained = state.callbacks == 0;
        drop(state);
        self.changed.notify_all();
        Ok(drained)
    }
pub(crate) fn shutdown_drained(&self, proof: &PeerStopped<'_>) -> Result<bool> {
        if !proof.matches_owner(self.data.owner) {
            return Err(EINVAL);
        }
        let state = self.state.lock();
        Ok(state.peer_stopped && state.callbacks == 0)
    }
pub(crate) fn publish(&self, send: impl FnOnce(&[u8; PACKET_BYTES]) -> Result) -> Result<bool> {
        let mut state = self.state.lock();
        if state.peer_stopped {
            return Err(ENODEV);
        }
        let Some((token, packet)) = state.exchange.outgoing() else {
            return Ok(false);
        };
        send(&packet)?;
        state.exchange.published(token).map_err(errno)?;
        Ok(true)
    }
pub(crate) fn queued(&self) -> bool {
        let state = self.state.lock();
        !state.peer_stopped && state.exchange.outgoing().is_some()
    }
pub(crate) fn reply(&self, packet: &[u8]) -> Result {
        let mut state = self.state.lock();
        if state.peer_stopped {
            return Err(ENODEV);
        }
        state.exchange.accept(packet).map_err(errno)?;
        drop(state);
        self.changed.notify_all();
        Ok(())
    }
fn call(
        &self,
        client: Client,
        call: Call,
        input: &[u8],
        output: &mut [u8],
        interruptible: bool,
    ) -> Result<usize> {
        let mut state = self.state.lock();
        if state.peer_stopped {
            return Err(ENODEV);
        }
        state.callbacks = state.callbacks.checked_add(1).ok_or(EBUSY)?;
        let result = (|| {
            while state.caller {
                if state.peer_stopped {
                    return Err(ENODEV);
                }
                if interruptible {
                    if self.changed.wait_interruptible(&mut state) {
                        return Err(EINTR);
                    }
                } else {
                    self.changed.wait(&mut state);
                }
            }
            if state.peer_stopped {
                return Err(ENODEV);
            }
            state.caller = true;
            // This scope always releases the caller flag, including an interrupted
            // wait, but deliberately retains any outstanding exchange and its data.
            let result = (|| {
                if let Some(token) = state.exchange.token() {
                    while !state.exchange.completed(token).map_err(errno)? {
                        if state.peer_stopped {
                            return Err(ENODEV);
                        }
                        if interruptible {
                            if self.changed.wait_interruptible(&mut state) {
                                return Err(EINTR);
                            }
                        } else {
                            self.changed.wait(&mut state);
                        }
                    }
                    // A preceding caller left on a signal; its completed result is
                    // discarded only after the peer has retired that exact token.
                    let _ = state.exchange.finish(token).map_err(errno)?;
                }
                if state.peer_stopped {
                    return Err(ENODEV);
                }
                let token = state.exchange.begin(client, call).map_err(errno)?;
                if let Call::Store { bytes } = call {
                    debug_assert_eq!(bytes, input.len());
                    for (index, byte) in input.iter().copied().enumerate() {
                        // SAFETY: begin bounds bytes to this retained page. This
                        // sole caller fills it before publish can acquire the lock.
                        unsafe {
                            ptr::write_volatile((self.data.address as *mut u8).add(index), byte)
                        };
                    }
                }
                while !state.exchange.completed(token).map_err(errno)? {
                    if state.peer_stopped {
                        return Err(ENODEV);
                    }
                    if interruptible {
                        if self.changed.wait_interruptible(&mut state) {
                            return Err(EINTR);
                        }
                    } else {
                        self.changed.wait(&mut state);
                    }
                }
                if state.peer_stopped {
                    return Err(ENODEV);
                }
                let bytes = state
                    .exchange
                    .finish(token)
                    .map_err(errno)?
                    .map_err(errno)?;
                if matches!(call, Call::Show { .. }) {
                    for (index, byte) in output.get_mut(..bytes).ok_or(EIO)?.iter_mut().enumerate()
                    {
                        // SAFETY: The matching acquired response retires the peer's
                        // write. The state lock and caller flag exclude a new call
                        // until these bounded volatile reads have completed.
                        *byte = unsafe {
                            ptr::read_volatile((self.data.address as *const u8).add(index))
                        };
                    }
                }
                Ok(bytes)
            })();
            state.caller = false;
            result
        })();
        state.callbacks -= 1;
        drop(state);
        self.changed.notify_all();
        result
    }
}
pub(crate) struct Attribute {
    remote: Arc<Remote>,
    client: Client,
    published: AtomicBool,
}
impl Drop for Attribute {
    fn drop(&mut self) {
        // A validated shutdown witness already excluded the peer and closed
        // this Remote. Namespace removal now drains local callbacks; sending
        // RELEASE to the stopped guest has no remaining protocol meaning.
        if self.remote.state.lock().peer_stopped { return; }
        if self.published.load(Ordering::Acquire) && self.client.operations != 0 {
            // File owns this Arc until sysfs_remove_file has drained callbacks.
            // Wait uninterruptibly for release: a signal must not let unlink
            // acknowledge while McKernel can still access the instance.
            if let Err(error) = self
                .remote
                .call(self.client, Call::Release, &[], &mut [], false)
            {
                pr_err!(
                    "IHK-SMP: remote sysfs release failed os={} generation={} error={}\n",
                    self.remote.data.owner.slot(),
                    self.remote.data.owner.generation(),
                    error.to_errno()
                );
            }
        }
    }
}
fn setup(address:u64)->Arc<Remote> { setup_owner(address,owner(7,91)) }
fn setup_owner(address:u64,owner:Owner)->Arc<Remote> {
    Arc::new(Remote { data:SharedData {owner,address},
        state:Mutex::new(State {exchange:Exchange::new(),caller:false,callbacks:0,peer_stopped:false}), changed:CondVar::new() })
}
fn client()->Client { Client {operations:1001,instance:99} }
fn wait_for(r:&Remote, count:usize) {
    let deadline=Instant::now()+Duration::from_secs(2);
    loop {
        if r.state.lock().callbacks==count { return; }
        assert!(Instant::now()<deadline,"callback admission timeout");
        std::thread::yield_now();
    }
}
fn publish(r:&Remote)->[u8;PACKET_BYTES] {
    let mut packet=[0;PACKET_BYTES];
    assert!(r.publish(|p| {packet=*p;Ok(())}).unwrap()); packet
}
fn response(mut packet:[u8;PACKET_BYTES], bytes:i64)->[u8;PACKET_BYTES] {
    let kind=i32::from_le_bytes(packet[8..12].try_into().unwrap())+1;
    packet[8..12].copy_from_slice(&kind.to_le_bytes());
    packet[12..16].copy_from_slice(&0i32.to_le_bytes());
    packet[32..40].copy_from_slice(&bytes.to_le_bytes()); packet
}
#[test] fn blocked_release_drop_and_pending_show_cancel_without_payload_release() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let page=Box::new([0xa5u8;4096]);
    let r=setup(page.as_ptr() as u64); let weak=Arc::downgrade(&r);
    let attribute=Attribute {remote:r.clone(),client:client(),published:AtomicBool::new(true)};
    let release=std::thread::spawn(move || drop(attribute));
    wait_for(&r,1); let packet=publish(&r);
    let token=r.state.lock().exchange.token();
    let other=r.clone(); let show=std::thread::spawn(move || {
        let mut out=[0x7bu8;8];
        assert_eq!(other.call(client(),Call::Show {capacity:8},&[],&mut out,true),Err(ENODEV));
        assert_eq!(out,[0x7b;8]);
    });
    wait_for(&r,2);
    assert!(!r.shutdown_drained(proof).unwrap());
    assert!(!r.shutdown_after_peer_stop(proof).unwrap());
    release.join().unwrap();show.join().unwrap();
    assert!(r.shutdown_drained(proof).unwrap());
    assert_eq!(r.state.lock().callbacks,0);
    assert!(!r.state.lock().caller);
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(r.reply(&response(packet,0)),Err(ENODEV));
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(page.as_slice(),&[0xa5;4096]);
    assert_eq!(Arc::strong_count(&r),1);
    assert!(weak.upgrade().is_some());drop(r);assert!(weak.upgrade().is_none());
    });
}
#[test] fn foreign_generation_or_slot_has_zero_effect_then_normal_reply_succeeds() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let page=Box::new([0x66u8;4096]);
    // Each remote belongs to a foreign owner. The proof comes only from the
    // actual scoped CPU/IRQ producer; no owner-field proof fabrication remains.
    for foreign in [owner(7,90),owner(8,91)] {
        let r=setup_owner(page.as_ptr() as u64,foreign);
        let other=r.clone();let task=std::thread::spawn(move || {
            let mut out=[0;4];let result=other.call(client(),Call::Show {capacity:4},&[],&mut out,true);
            (result,out)
        });
        wait_for(&r,1); let packet=publish(&r);
        assert_eq!(r.shutdown_after_peer_stop(proof),Err(EINVAL));
        assert_eq!(r.shutdown_drained(proof),Err(EINVAL));
        assert!(!r.state.lock().peer_stopped);
        assert_eq!(r.state.lock().callbacks,1);
        r.reply(&response(packet,4)).unwrap();
        assert_eq!(task.join().unwrap(),(Ok(4),[0x66;4]));
    }
    let r=setup(page.as_ptr() as u64);
    assert!(r.shutdown_after_peer_stop(proof).unwrap());
    });
}
#[test] fn terminal_admission_and_duplicate_stop_do_not_publish_or_reuse_payload() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let r=setup(0);assert!(r.shutdown_after_peer_stop(proof).unwrap());
    assert!(r.shutdown_after_peer_stop(proof).unwrap());assert!(!r.queued());
    let mut touched=false;
    assert_eq!(r.publish(|_| {touched=true;Ok(())}),Err(ENODEV)); assert!(!touched);
    assert_eq!(r.call(client(),Call::Store {bytes:1},&[1],&mut [],true),Err(ENODEV));
    assert_eq!(r.call(client(),Call::Release,&[],&mut [],false),Err(ENODEV));
    assert_eq!(r.state.lock().callbacks,0);assert!(r.state.lock().exchange.token().is_none());
    // Actual Attribute::drop must return without queuing another Release.
    drop(Attribute {remote:r.clone(),client:client(),published:AtomicBool::new(true)});
    assert!(r.state.lock().exchange.token().is_none());
    });
}
#[test] fn interrupted_published_exchange_remains_owned_until_peer_stop_cancels_successor() {
    super::smp_cpu::fixture_peer_scope(|proof| {
    let r=setup(0);let other=r.clone();
    let show=std::thread::spawn(move || other.call(client(),Call::Show {capacity:0},&[],&mut [],true));
    wait_for(&r,1);let packet=publish(&r);
    {let _state=r.state.lock();r.changed.interrupt.store(true,Ordering::Release);r.changed.notify_all();}
    assert_eq!(show.join().unwrap(),Err(EINTR));
    let token=r.state.lock().exchange.token();assert!(token.is_some());
    let other=r.clone();let release=std::thread::spawn(move || other.call(client(),Call::Release,&[],&mut [],false));
    wait_for(&r,1);assert!(!r.shutdown_after_peer_stop(proof).unwrap());
    assert_eq!(release.join().unwrap(),Err(ENODEV));
    assert!(r.shutdown_drained(proof).unwrap());
    assert_eq!(r.state.lock().exchange.token(),token);
    assert_eq!(r.reply(&response(packet,0)),Err(ENODEV));
    });
}

}
mod smp_memory {

    struct ObservedExtent {start:u64,length:u64,owner:Option<OsToken>}
    impl ObservedExtent {
      fn start(&self)->u64{self.start}fn length(&self)->u64{self.length}
      fn numa_node(&self)->u32{0}fn owner(&self)->Option<OsToken>{self.owner}
    }
    impl Map {
      fn len(&self)->usize{if crate::OBSERVE_MANY.load(Ordering::Acquire){65}else{3}}
      fn extent(&self,index:usize)->Option<ObservedExtent>{
        if index>=self.len(){return None;}
        Some(ObservedExtent{start:4096+(index as u64)*8192,length:8192,
          owner:if index==0{self.owner}else if index==1{Some(super::smp_cpu::fixture_owner(7,92))}else{None}})
      }
    }
    pub(super) fn integration_epoch(owner:OsToken)->u64{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.id}

    struct MemoryWorkspace;
    impl MemoryWorkspace{fn new(_staging:&mut [Option<()>;1])->Result<Self>{Ok(Self)}}
    struct Map{owner:Option<OsToken>}
    struct MapTransaction<'a>{map:&'a mut Map}
    impl Map{fn prepare_release_all<'a>(&'a mut self,owner:OsToken,_work:&mut MemoryWorkspace)->Result<MapTransaction<'a>>{
        if super::MAP_STATUS.load(Ordering::Acquire)!=0||self.owner!=Some(owner){return Err(EIO);}Ok(MapTransaction{map:self})
    }}
    impl MapTransaction<'_>{fn begin_external_effects(&mut self)->Result{Ok(())}fn compensated_rollback(self)->Result{Ok(())}fn commit(self)->Result{self.map.owner=None;super::MEMORY_COMMITS.fetch_add(1,Ordering::AcqRel);Ok(())}}
    pub(super) fn integration_image_present(owner:OsToken)->bool{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].is_some()}
    pub(super) fn integration_assigned(owner:OsToken)->bool{unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().map.owner==Some(owner)}

    use std::{marker::PhantomData, ptr, sync::atomic::{AtomicPtr, AtomicU32, AtomicU64, Ordering}};
    use super::smp_cpu::{OsToken,Result};
    const EIO:i32=-5; const EBUSY:i32=-16; const EINVAL:i32=-22; const ENODEV:i32=-19;
    const GFP_KERNEL:()=();
    struct Arc<T>(std::sync::Arc<T>);
    impl<T> Arc<T> { fn new(value:T,_flags:())->Result<Self> {Ok(Self(std::sync::Arc::new(value)))} fn ptr_eq(a:&Self,b:&Self)->bool {std::sync::Arc::ptr_eq(&a.0,&b.0)} }
    impl<T> Clone for Arc<T> {fn clone(&self)->Self {Self(self.0.clone())}}
    impl<T> std::ops::Deref for Arc<T> {type Target=T;fn deref(&self)->&T {&self.0}}
    pub(super) mod service {
 use crate::smp_cpu::Result;
 use crate::ErrorNumber;
 type Error=i32;
 use crate::AdapterMutex as Mutex;
 use std::sync::{Arc,atomic::{AtomicBool,Ordering}};
 const EBUSY:i32=-16;const EINVAL:i32=-22;
 struct Tagged;
 struct Ledger{requests:Vec<Option<Tagged>>,responses:Vec<Option<Tagged>>,payloads:Vec<Option<Tagged>>,snoops:Vec<Tagged>,procfs:Vec<Tagged>,zeroing:Vec<Tagged>,exec_payloads:Vec<Option<Tagged>>}
 struct LedgerMutex(Mutex<Ledger>);
 impl LedgerMutex{fn lock(&self)->crate::CountedGuard<'_,Ledger>{
  if crate::INJECT_STALE.swap(false,Ordering::AcqRel){crate::smp_memory::replace_epoch(crate::smp_cpu::fixture_owner(7,91));}
  self.0.lock()
 }}
 pub(super) struct Memory{pub(super) owner:crate::smp_cpu::OsToken,ledger:LedgerMutex}
 impl Memory{
  pub(super) fn shutdown_quiescent(&self) -> Result {
        let ledger = self.ledger.lock();
        if ledger.requests.iter().any(Option::is_some)
            || ledger.responses.iter().any(Option::is_some)
            || ledger.payloads.iter().any(Option::is_some)
            || ledger.exec_payloads.iter().any(Option::is_some)
            || !ledger.snoops.is_empty()
            || !ledger.procfs.is_empty()
            || !ledger.zeroing.is_empty()
        {
            return Err(EBUSY);
        }
        Ok(())
    }
 }
 pub(super) struct ProcfsRemote{memory:Arc<Memory>,active:AtomicBool,slots:Mutex<Vec<Option<()>>>}
 impl ProcfsRemote{
  pub(super) fn close_if_quiescent(
        &self,
        proof: &crate::sysfs_remote::PeerStopped<'_>,
    ) -> Result {
        if !proof.matches_owner(self.memory.owner) {
            return Err(EINVAL);
        }
        let slots = self.slots.lock();
        self.active.store(false, Ordering::Release);
        if slots.iter().any(Option::is_some) {
            return Err(EBUSY);
        }
        Ok(())
    }
 }
 struct Namespace{_tree:crate::callback_boundary::Tree}
 impl Namespace{fn new()->Self{Self{_tree:crate::callback_boundary::tree()}}}
 impl Drop for Namespace{fn drop(&mut self){crate::no_dependent_locks();crate::NAMESPACE_DROPS.fetch_add(1,Ordering::AcqRel);}}
 struct Service{_namespace:Namespace}
 struct ProcfsService{processes:Vec<()>,_namespace:Namespace}
 impl ProcfsService{
  pub(super) fn shutdown_quiescent(&self) -> Result {
        if !self.processes.is_empty() {
            return Err(EBUSY);
        }
        Ok(())
    }
 }
 struct Pending{length:usize}
 struct Transport{master_reply:Option<[u8;56]>}
 struct Runtime{
  remote:Arc<crate::sysfs_remote::Remote>,application:Arc<crate::smp_application::Remote>,procfs:ProcfsRemote,memory:Arc<Memory>,
  pending:Mutex<Pending>,procfs_pending:Mutex<Vec<()>>,zero_pending:Mutex<Vec<()>>,transport:Mutex<Transport>,service:Mutex<Option<Service>>,procfs_service:Mutex<Option<ProcfsService>>,
 }
 struct Thread{role:u32,joined:AtomicBool}
 impl Thread{fn stop_join(&self){
  crate::no_dependent_locks();
  if !self.joined.swap(true,Ordering::AcqRel){
   crate::JOIN_ENTERED.fetch_add(1,Ordering::AcqRel);
   while crate::JOIN_BLOCK.load(Ordering::Acquire){std::thread::yield_now();}
   crate::JOIN_COUNT.fetch_add(1,Ordering::AcqRel);
   if self.role==0{crate::STOP_CALLS.fetch_add(1,Ordering::AcqRel);}
  }
 }}
 #[derive(Clone)]
pub(in super::super) struct Started {
    runtime: Arc<Runtime>,
    metadata: Arc<Thread>,
    packets: Arc<Thread>,
    zeroing: Arc<Thread>,
}
 impl Started{
  pub(super) fn stop_workers_after_peer_stop(
        &self,
        proof: &super::super::sysfs_remote::PeerStopped<'_>,
    ) -> Result {
        self.runtime.remote.shutdown_after_peer_stop(proof)?;
        self.packets.stop_join();
        self.metadata.stop_join();
        self.zeroing.stop_join();
        if !self.runtime.remote.shutdown_drained(proof)? {
            return Err(EBUSY);
        }
        Ok(())
    }
pub(super) fn close_application_admission(&self) -> Result {
        self.runtime.application.shutdown_close_if_quiescent()
    }
pub(super) fn same_runtime(&self, other: &Self) -> bool {
        Arc::ptr_eq(&self.runtime, &other.runtime)
    }
pub(super) fn retire_after_peer_stop(
        &self,
        proof: &super::super::sysfs_remote::PeerStopped<'_>,
    ) -> Result {
        let failed = |stage: &'static str, error: Error| {
            pr_info!("IHK-SMP: shutdown services os={} generation={} stage={} result={}; remaining owners retained\n",
                self.runtime.memory.owner.slot(), self.runtime.memory.owner.generation(), stage, error.to_errno());
            error
        };
        self.runtime.application.shutdown_quiescent().map_err(|error| failed("application_quiesce", error))?;
        self.runtime.procfs.close_if_quiescent(proof).map_err(|error| failed("procfs_sessions", error))?;
        self.stop_workers_after_peer_stop(proof).map_err(|error| failed("workers_remote_drain", error))?;
        if self.runtime.pending.lock().length != 0
            || !self.runtime.procfs_pending.lock().is_empty()
            || !self.runtime.zero_pending.lock().is_empty()
            || self.runtime.transport.lock().master_reply.is_some() {
            return Err(failed("pending_work", EBUSY));
        }
        // Do not take either namespace owner until all fallible preflights
        // finish. A busy process keeps the original Service and all callbacks.
        {
            let service = self.runtime.procfs_service.lock();
            if let Some(service) = service.as_ref() {
                service.shutdown_quiescent().map_err(|error| failed("procfs_processes", error))?;
            }
        }
        let sysfs = self.runtime.service.lock().take();
        let procfs = self.runtime.procfs_service.lock().take();
        // No resource/service/transport guard spans Linux callback rundown.
        drop(sysfs);
        drop(procfs);
        if !self.runtime.remote.shutdown_drained(proof)? { return Err(failed("callbacks", EBUSY)); }
        self.runtime.application.shutdown_quiescent().map_err(|error| failed("application_after_drain", error))?;
        self.runtime.procfs.close_if_quiescent(proof).map_err(|error| failed("procfs_sessions", error))?;
        self.runtime.memory.shutdown_quiescent().map_err(|error| failed("memory_ledger", error))
    }
 }
 static LAST:std::sync::Mutex<Option<Arc<Runtime>>>=std::sync::Mutex::new(None);
 pub(super) fn fixture_started()->Started{
  let memory=Arc::new(Memory{owner:crate::smp_cpu::fixture_owner(7,91),ledger:LedgerMutex(Mutex::new(Ledger{requests:vec![None],responses:vec![None],payloads:vec![None],snoops:vec![],procfs:vec![],zeroing:vec![],exec_payloads:vec![]}))});
  let runtime=Arc::new(Runtime{remote:crate::sysfs_remote::fixture_service_remote(),application:Arc::new(crate::smp_application::Remote::fixture()),procfs:ProcfsRemote{memory:memory.clone(),active:AtomicBool::new(true),slots:Mutex::new(vec![None])},memory,pending:Mutex::new(Pending{length:0}),procfs_pending:Mutex::new(vec![]),zero_pending:Mutex::new(vec![]),transport:Mutex::new(Transport{master_reply:None}),service:Mutex::new(Some(Service{_namespace:Namespace::new()})),procfs_service:Mutex::new(Some(ProcfsService{processes:vec![],_namespace:Namespace::new()}))});
  *LAST.lock().unwrap()=Some(runtime.clone());
  Started{runtime,metadata:Arc::new(Thread{role:1,joined:AtomicBool::new(false)}),packets:Arc::new(Thread{role:0,joined:AtomicBool::new(false)}),zeroing:Arc::new(Thread{role:2,joined:AtomicBool::new(false)})}
 }
 pub(crate) fn configure(kind:u32){let r=LAST.lock().unwrap();let r=r.as_ref().unwrap();match kind{
  1=>r.application.fixture_busy(),2=>r.remote.fixture_callbacks(1),3=>r.memory.ledger.lock().responses[0]=Some(Tagged),
  4=>r.pending.lock().length=1,5=>r.procfs.slots.lock()[0]=Some(()),6=>r.application.fixture_pager_busy(),7=>r.procfs_service.lock().as_mut().unwrap().processes.push(()),_=>()}}
 pub(crate) fn app_retained()->usize{LAST.lock().unwrap().as_ref().unwrap().application.fixture_retained()}
 pub(crate) fn reserve_after_close()->bool{LAST.lock().unwrap().as_ref().unwrap().application.reserve(456).is_err()}
 pub(crate) fn namespaces_retained()->bool{let r=LAST.lock().unwrap();let r=r.as_ref().unwrap();r.service.lock().is_some()&&r.procfs_service.lock().is_some()}
}
    static NEXT_BOOT_EPOCH: AtomicU64 = AtomicU64::new(1);
const SHUTDOWN_OPEN: u32 = 0;
const SHUTDOWN_ACTIVE: u32 = 1;
const SHUTDOWN_RETAINED: u32 = 2;
const SHUTDOWN_SERVICES_RETIRED: u32 = 3;
const SHUTDOWN_COMMITTED: u32 = 4;

struct BootEpoch {
    id: u64,
    shutdown: AtomicU32,
}

impl BootEpoch {
    fn allocate() -> Result<Arc<Self>> {
        let id = NEXT_BOOT_EPOCH.fetch_update(Ordering::AcqRel, Ordering::Acquire,
            |next| next.checked_add(1)).map_err(|_| EIO)?;
        Ok(Arc::new(Self { id, shutdown: AtomicU32::new(SHUTDOWN_OPEN) }, GFP_KERNEL)?)
    }

    fn claim(&self) -> Result {
        let previous = self.shutdown.load(Ordering::Acquire);
        if !matches!(previous, SHUTDOWN_OPEN | SHUTDOWN_RETAINED) { return Err(EBUSY); }
        self.shutdown.compare_exchange(previous, SHUTDOWN_ACTIVE,
            Ordering::AcqRel, Ordering::Acquire).map_err(|_| EBUSY)?;
        Ok(())
    }

    fn admission_open(&self) -> bool {
        self.shutdown.load(Ordering::Acquire) == SHUTDOWN_OPEN
    }
}

/// A unique live shutdown transaction, acquired under the memory mutex. Its
/// epoch Arc and Started clone retain identities; BootStorage retains every
/// original mapping/ledger/callback owner. Dropping a failed transaction keeps
/// admission closed. This is deliberately not a physical retirement proof.
#[allow(dead_code)]
pub(super) struct ShutdownBoot {
    owner: super::smp_resource::OsToken,
    epoch: Arc<BootEpoch>,
    started: service::Started,
    // Keep shutdown orchestration and all Linux lock guards on one task.
    _task: PhantomData<*mut ()>,
}

#[allow(dead_code)]
impl ShutdownBoot {
    pub(super) fn owner(&self) -> super::smp_resource::OsToken { self.owner }
    pub(super) fn epoch_id(&self) -> u64 { self.epoch.id }
    pub(super) fn matches_owner(&self, owner: super::smp_resource::OsToken) -> bool {
        self.owner == owner && matches!(self.epoch.shutdown.load(Ordering::Acquire),
            SHUTDOWN_ACTIVE | SHUTDOWN_SERVICES_RETIRED)
    }
    pub(super) fn same_epoch(&self, other: &Self) -> bool {
        self.matches_owner(other.owner) && other.matches_owner(self.owner)
            && Arc::ptr_eq(&self.epoch, &other.epoch)
    }

    pub(super) fn close_application_admission(&self) -> Result {
        self.started.close_application_admission()
    }

    /// Only the exact current CPU/IRQ witness may retire the retained Runtime.
    /// The epoch transition follows joins, synchronous callback rundown and
    /// all ledger checks; no physical owner is removed at this boundary.
    pub(super) fn retire_services(&self, proof: &super::sysfs_remote::PeerStopped<'_>) -> Result {
        if !proof.matches_boot(self) { return Err(EIO); }
        self.revalidate()?;
        self.started.retire_after_peer_stop(proof)?;
        self.revalidate()?;
        self.epoch.shutdown.compare_exchange(SHUTDOWN_ACTIVE, SHUTDOWN_SERVICES_RETIRED,
            Ordering::AcqRel, Ordering::Acquire).map_err(|_| EIO)?;
        Ok(())
    }

    /// Short revalidation only; callers must release the guard before joins.
    pub(super) fn revalidate(&self) -> Result {
        let published = PUBLISHED.load(Ordering::Acquire);
        if published.is_null() { return Err(ENODEV); }
        // SAFETY: Started storage retains the resource/module owners. This
        // claim never outlives the synchronous backend lease which acquired it.
        let context = unsafe { &*published }.lock();
        context.validate_shutdown_boot(self)
    }

    /// This method has no resource guard. CPU orchestration calls it only
    /// after leaving its CPU/hotplug scope. It releases no physical owner.
    pub(super) fn stop_workers(&self, proof: &super::sysfs_remote::PeerStopped<'_>) -> Result {
        if !proof.matches_boot(self) { return Err(EIO); }
        self.revalidate()?;
        self.started.stop_workers_after_peer_stop(proof)?;
        self.revalidate()
    }
}

impl Drop for ShutdownBoot {
    fn drop(&mut self) {
        // Never reopen admission after a reset, cancellation or partial stop.
        if self.epoch.shutdown.load(Ordering::Acquire) != SHUTDOWN_COMMITTED {
            self.epoch.shutdown.store(SHUTDOWN_RETAINED, Ordering::Release);
        }
    }
}


    struct MockIrq { drained: bool }
    impl MockIrq {fn release_drained(&mut self,_owner:OsToken)->Result{let status=super::IRQ_RELEASE_STATUS.load(Ordering::Acquire);if status!=0{return Err(status);}if !self.drained{return Err(EIO);}self.drained=false;Ok(())} fn shutdown_drained(&self,_owner:OsToken)->bool {self.drained} }
    struct PreparedBoot {sysfs:Option<()>, continuing:Option<service::Started>, irq:MockIrq }
    struct BootStorage { epoch:Arc<BootEpoch>, started:bool, shutdown_terminal:bool, prepared:PreparedBoot }
    struct LoadedImage { owner:OsToken, boot:Option<BootStorage> }
    impl LoadedImage {fn started(&self)->bool {self.boot.as_ref().is_some_and(|boot|boot.started)}}
    struct MemoryContext { images:[Option<LoadedImage>;64],arguments:[Option<()>;64],map:Map,staging:[Option<()>;1] }
    impl MemoryContext {
fn observe_shutdown_memory(&self, claim: &ShutdownBoot, phase: &str) {
        let owner = claim.owner;
        let count = self.map.len();
        let emitted = count.min(64);
        pr_info!("IHK-SMP: resource-memory-v1 os={} generation={} epoch={} phase={} rows={} emitted={} complete={}\n",
            owner.slot(), owner.generation(), claim.epoch_id(), phase, count, emitted, (count <= 64) as u8);
        for index in 0..emitted {
            if let Some(range) = self.map.extent(index) {
                let token = range.owner();
                pr_info!("IHK-SMP: resource-memory-row-v1 os={} generation={} epoch={} phase={} index={} start={} bytes={} numa={} owner_none={} owner_slot={} owner_generation={}\n",
                    owner.slot(), owner.generation(), claim.epoch_id(), phase, index,
                    range.start(), range.length(), range.numa_node(), token.is_none() as u8,
                    token.map_or(0, |token| token.slot()), token.map_or(0, |token| token.generation()));
            }
        }
    }
fn finish_shutdown_claim(&mut self, claim: &ShutdownBoot, commit_cpu: impl FnOnce()) -> Result {
        self.verify()?;
        self.validate_shutdown_boot(claim)?;
        if claim.epoch.shutdown.load(Ordering::Acquire) != SHUTDOWN_SERVICES_RETIRED {
            return Err(EBUSY);
        }
        self.observe_shutdown_memory(claim, "prepared");
        let owner = claim.owner;
        let image = self.images.get_mut(owner.slot() as usize)
            .and_then(Option::as_mut).ok_or(EIO)?;
        let boot = image.boot.as_mut().ok_or(EIO)?;
        // Sysfs moved into the exact Runtime before BOOT returned. A second
        // owner or mismatched continuing service cannot borrow its proof.
        if boot.prepared.sysfs.is_some() || !boot.prepared.continuing.as_ref()
            .is_some_and(|started| started.same_runtime(&claim.started)) {
            return Err(EBUSY);
        }
        let mut workspace = MemoryWorkspace::new(&mut self.staging).map_err(|_| EIO)?;
        let mut transaction = self.map.prepare_release_all(owner, &mut workspace).map_err(|_| EIO)?;
        transaction.begin_external_effects().map_err(|_| EIO)?;
        if let Err(error) = boot.prepared.irq.release_drained(owner) {
            transaction.compensated_rollback().map_err(|_| EIO)?;
            return Err(error);
        }
        // No fallible operation remains. Both policy mutexes and Linux
        // hotplug exclusion span the coupled logical commit, never a join.
        commit_cpu();
        transaction.commit().unwrap_or_else(|_| panic!("shutdown claim lost memory preflight"));
        claim.epoch.shutdown.store(SHUTDOWN_COMMITTED, Ordering::Release);
        boot.started = false;
        self.images[owner.slot() as usize] = None;
        self.arguments[owner.slot() as usize] = None;
        self.observe_shutdown_memory(claim, "committed");
        Ok(())
    }
fn verify(&self)->Result{Ok(())}

        fn require_unstarted(&self, owner: super::smp_resource::OsToken) -> Result {
        if let Some(image) = self
            .images
            .get(owner.slot() as usize)
            .ok_or(EINVAL)?
            .as_ref()
        {
            if image.owner != owner {
                return Err(EIO);
            }
            if image.boot.as_ref().is_some_and(|boot| !boot.epoch.admission_open()) {
                return Err(EBUSY);
            }
            if image.started() {
                return Err(EBUSY);
            }
        }
        Ok(())
    }
fn claim_shutdown_boot(&self, owner: super::smp_resource::OsToken) -> Result<ShutdownBoot> {
        let image = self.images.get(owner.slot() as usize)
            .and_then(Option::as_ref).ok_or(EINVAL)?;
        if image.owner != owner { return Err(EIO); }
        let boot = image.boot.as_ref().ok_or(EIO)?;
        if !boot.started || boot.shutdown_terminal { return Err(EBUSY); }
        let started = boot.prepared.continuing.as_ref().ok_or(EBUSY)?.clone();
        boot.epoch.claim()?;
        Ok(ShutdownBoot { owner, epoch: boot.epoch.clone(), started, _task: PhantomData })
    }
fn validate_shutdown_boot(&self, claim: &ShutdownBoot) -> Result {
        let image = self.images.get(claim.owner.slot() as usize)
            .and_then(Option::as_ref).ok_or(EIO)?;
        let boot = image.boot.as_ref().ok_or(EIO)?;
        if image.owner != claim.owner || !boot.started || boot.shutdown_terminal
            || !claim.matches_owner(image.owner) || !Arc::ptr_eq(&boot.epoch, &claim.epoch)
            || !boot.prepared.irq.shutdown_drained(image.owner) {
            return Err(EIO);
        }
        Ok(())
    }
    }
    struct ContextMutex(std::sync::Mutex<MemoryContext>);
    impl ContextMutex {fn lock(&self)->super::CountedGuard<'_,MemoryContext> {
        let guard=self.0.lock().unwrap(); super::MEMORY_LOCKS.fetch_add(1,Ordering::AcqRel);
        super::CountedGuard {guard,counter:&super::MEMORY_LOCKS}
    }}
    static PUBLISHED:AtomicPtr<ContextMutex>=AtomicPtr::new(ptr::null_mut());
    pub(super) fn claim_shutdown_boot(owner: super::smp_resource::OsToken) -> Result<ShutdownBoot> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() { return Err(ENODEV); }
    // SAFETY: Synchronous backend lease and retained started storage pin it.
    let context = unsafe { &*published }.lock();
    context.claim_shutdown_boot(owner)
}
    pub(super) enum ShutdownIrqFailure {PreEffect(i32),PostEffect(i32)}
    pub(super) fn shutdown_close_irq_senders(owner:OsToken)->std::result::Result<(),ShutdownIrqFailure> {
        let pre=super::IRQ_PRE_STATUS.load(Ordering::Acquire);if pre!=0{return Err(ShutdownIrqFailure::PreEffect(pre));}
        let status=super::IRQ_STATUS.load(Ordering::Acquire);
        if status!=0 {return Err(ShutdownIrqFailure::PostEffect(status));}
        let mut context=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();
        let image=context.images[owner.slot() as usize].as_mut().unwrap();
        image.boot.as_mut().unwrap().prepared.irq.drained=true;Ok(())
    }
    pub(super) fn setup(owner:OsToken) {
        let mut images=[const{None};64];
        images[owner.slot() as usize]=Some(LoadedImage {owner,boot:Some(BootStorage {epoch:BootEpoch::allocate().unwrap(),started:true,shutdown_terminal:false,prepared:PreparedBoot {sysfs:None,continuing:Some(service::fixture_started()),irq:MockIrq {drained:false}}})});
        PUBLISHED.store(Box::into_raw(Box::new(ContextMutex(std::sync::Mutex::new(MemoryContext {images,arguments:[None;64],map:Map{owner:Some(owner)},staging:[None]})))),Ordering::Release);
    }
    pub(super) fn ordinary_boot(owner:OsToken)->Result {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().require_unstarted(owner)}
    pub(super) fn admission_open(owner:OsToken)->bool {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.admission_open()}
    pub(super) fn replace_epoch(owner:OsToken) {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_mut().unwrap().boot.as_mut().unwrap().epoch=BootEpoch::allocate().unwrap();}
    pub(super) fn invalidate(owner:OsToken) {unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock().images[owner.slot() as usize].as_ref().unwrap().boot.as_ref().unwrap().epoch.shutdown.store(SHUTDOWN_RETAINED,Ordering::Release);}
    // Alias a live claim only in the fixture to check matching without taking
    // ownership of the transaction or changing its state on Drop.
    fn current_claim_for_test()->std::mem::ManuallyDrop<ShutdownBoot> {
        let context=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();
        let image=context.images.iter().flatten().next().unwrap();let boot=image.boot.as_ref().unwrap();
        std::mem::ManuallyDrop::new(ShutdownBoot {owner:image.owner,epoch:boot.epoch.clone(),started:service::fixture_started(),_task:PhantomData})
    }
pub(super) fn finish_shutdown_claim(claim: &ShutdownBoot, commit_cpu: impl FnOnce()) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() { return Err(ENODEV); }
    // SAFETY: The synchronous provider lease and exact boot claim pin owners.
    let mut context = unsafe { &*published }.lock();
    context.finish_shutdown_claim(claim, commit_cpu)
}
    pub(super) fn retire_os_boot(_owner:OsToken)->Result {Ok(())}
    pub(super) fn release_os_resources(_owner:OsToken,commit:impl FnOnce())->Result {commit();Ok(())}
    pub(super) fn finish_shutdown(_owner:OsToken,commit:impl FnOnce())->Result {commit();Ok(())}
}
mod smp_topology {
    pub struct Cpu {
        pub linux_id: u32,
        pub apic_id: u32,
    }
}
mod smp_cpu {
    use std::pin::Pin;
    use std::ptr;
    use std::sync::atomic::{AtomicBool, AtomicI32, AtomicPtr, AtomicU32, Ordering};
    use std::sync::Arc;

    const SMP_MAX_CPUS: usize = 4;
    const EIO: i32 = -5;
    const ENODEV: i32 = -19;
    const EINVAL: i32 = -22;
    const EBUSY:i32=-16;
    type Error = i32;
    pub(super) type Result<T = ()> = std::result::Result<T, Error>;
    trait ErrorNumber {
        fn to_errno(self) -> i32;
    }
    impl ErrorNumber for i32 {
        fn to_errno(self) -> i32 {
            self
        }
    }

    mod bindings {
        use super::{AtomicBool, AtomicI32, Ordering, SMP_MAX_CPUS};
        #[allow(non_camel_case_types)]
        pub struct device;
        pub unsafe fn put_device(_device: *mut device) {
            super::DEVICE_DROPS.fetch_add(1, Ordering::Relaxed);
        }
        static ONLINE: [AtomicBool; SMP_MAX_CPUS] =
            [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
        static STATUS: [AtomicI32; SMP_MAX_CPUS] = [const { AtomicI32::new(0) }; SMP_MAX_CPUS];
        static BREAK_AFTER_ONLINE: [AtomicBool; SMP_MAX_CPUS] =
            [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
        pub fn reset() {
            for cpu in 0..SMP_MAX_CPUS {
                ONLINE[cpu].store(false, Ordering::Relaxed);
                STATUS[cpu].store(0, Ordering::Relaxed);
                BREAK_AFTER_ONLINE[cpu].store(false, Ordering::Relaxed);
            }
        }
        pub fn online(cpu: usize) -> bool {
            ONLINE[cpu].load(Ordering::Acquire)
        }
        pub fn set_online(cpu: usize, value: bool) {
            ONLINE[cpu].store(value, Ordering::Release);
        }
        pub fn set_status(cpu: usize, value: i32) {
            STATUS[cpu].store(value, Ordering::Release);
        }
        pub fn break_identity_after_online(cpu: usize) {
            BREAK_AFTER_ONLINE[cpu].store(true, Ordering::Release);
        }
        pub unsafe fn get_cpu_device(cpu: u32) -> *mut device {
            (cpu as usize + 0x1000) as *mut device
        }
        pub unsafe fn device_online(cpu_device: *mut device) -> i32 {
            super::ONLINE_CALLS.fetch_add(1, Ordering::Relaxed);
            let cpu = cpu_device as usize - 0x1000;
            let status = STATUS[cpu].load(Ordering::Acquire);
            if status == 0 {
                ONLINE[cpu].store(true, Ordering::Release);
            }
            status
        }
        pub fn identity_broken(cpu: usize) -> bool {
            BREAK_AFTER_ONLINE[cpu].load(Ordering::Acquire) && online(cpu)
        }
    }
    mod kernel {
        pub mod error {
            pub fn to_result(status: i32) -> Result<(), i32> {
                if status == 0 {
                    Ok(())
                } else {
                    Err(status)
                }
            }
        }
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    pub(super) struct OsToken {
        slot: u32,
        generation: u64,
    }
    impl OsToken {pub(super) unsafe fn from_ihk_lease_v2(slot:u32,generation:u64)->Result<Self>{if slot>=64||generation==0{return Err(EINVAL);}Ok(Self{slot,generation})}
        pub(super) const fn slot(self) -> u32 {
            self.slot
        }
        pub(super) const fn generation(self) -> u64 {
            self.generation
        }
    }
    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    struct HostCpuSnapshot {
        hardware_id: u32,
        numa_node: u32,
        online: bool,
    }
    #[allow(dead_code)]
    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
    enum CpuState {
        Online,
        Absent,
        Available,
        Assigned,
        Quarantined,
    }
    #[derive(Clone, Copy)]
    struct Slot {
        state: CpuState,
        owner: Option<OsToken>,
        hardware_id: u32,
        numa_node: u32,
    }
    impl Slot {
        fn state(&self) -> CpuState {
            self.state
        }
        fn owner(&self) -> Option<OsToken> {
            self.owner
        }
        fn hardware_id(&self) -> u32 {
            self.hardware_id
        }
        fn numa_node(&self) -> u32 {
            self.numa_node
        }
    }
    struct CpuTable<const N: usize> {
        slots: [Slot; N],
    }
    struct ShutdownOnline<'a> { table: &'a mut CpuTable<SMP_MAX_CPUS>, cpus: &'a [usize] }
    impl ShutdownOnline<'_> {
        fn commit(self) {
            for &cpu in self.cpus {
                self.table.slots[cpu].owner = None;
                self.table.slots[cpu].state = CpuState::Online;
            }
        }
    }
    impl CpuTable<SMP_MAX_CPUS> {
        fn preflight_shutdown_online(&self, owner: OsToken, cpus: &[usize]) -> Result {
            if cpus.iter().any(|&cpu| self.slots[cpu].owner != Some(owner)) { return Err(EIO); }
            Ok(())
        }
        fn prepare_shutdown_online<'a>(&'a mut self, owner: OsToken, cpus: &'a [usize]) -> Result<ShutdownOnline<'a>> {
            self.preflight_shutdown_online(owner, cpus)?;
            Ok(ShutdownOnline { table: self, cpus })
        }
        fn slot(&self, cpu: usize) -> Result<&Slot> {
            self.slots.get(cpu).ok_or(EIO)
        }
        fn assigned_cpus(
            &self,
            owner: OsToken,
            requests: &mut [usize; SMP_MAX_CPUS],
        ) -> Result<usize> {
            let mut count = 0;
            for cpu in 1..SMP_MAX_CPUS {
                if self.slots[cpu].state == CpuState::Assigned
                    && self.slots[cpu].owner == Some(owner)
                {
                    requests[count] = cpu;
                    count += 1;
                }
            }
            Ok(count)
        }
        fn prepare_assign<'a>(
            &'a mut self,
            owner: OsToken,
            cpus: &'a [usize],
            _journal: &mut [CpuChange],
        ) -> Result<Transaction<'a>> {
            Ok(Transaction {
                table: self,
                owner: Some(owner),
                cpus,
            })
        }
        fn prepare_release<'a>(
            &'a mut self,
            _owner: OsToken,
            cpus: &'a [usize],
            _journal: &mut [CpuChange],
        ) -> Result<Transaction<'a>> {
            Ok(Transaction {
                table: self,
                owner: None,
                cpus,
            })
        }
    }
    struct Transaction<'a> {
        table: &'a mut CpuTable<SMP_MAX_CPUS>,
        owner: Option<OsToken>,
        cpus: &'a [usize],
    }
    impl Transaction<'_> {
        fn begin_external_effects(&mut self) -> Result {
            BEGIN_CALLS.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
        fn commit(self) -> Result {
            COMMITS.fetch_add(1, Ordering::Relaxed);
            for &cpu in self.cpus {
                self.table.slots[cpu].owner = self.owner;
            }
            Ok(())
        }
        fn compensated_rollback(self) -> Result {
            ROLLBACKS.fetch_add(1, Ordering::Relaxed);
            Ok(())
        }
    }
    #[derive(Clone, Copy)]
    struct CpuChange;
    struct ResourceModulePin;
    impl Drop for ResourceModulePin {
        fn drop(&mut self) {
            PIN_DROPS.fetch_add(1, Ordering::Relaxed);
        }
    }
    struct CpuRequest {
        array: usize,
        count: usize,
    }
    struct UserSlice;
    impl UserSlice {
        fn new(_array: usize, _length: usize) -> Self {
            Self
        }
        fn reader(self) -> Self {
            self
        }
        fn read<T>(&mut self) -> Result<T> {
            Err(EINVAL)
        }
    }
    struct DeviceHotplugGuard;
    impl Drop for DeviceHotplugGuard {fn drop(&mut self) {super::HOTPLUG_LOCKS.fetch_sub(1,Ordering::AcqRel);}}
    impl DeviceHotplugGuard {
        fn lock() -> Self {
            super::HOTPLUG_LOCKS.fetch_add(1,Ordering::AcqRel);Self
        }
    }
    struct LinuxCpuBatch<'a> {
        devices: &'a [Option<CpuDevice>; SMP_MAX_CPUS],
        _hotplug: &'a DeviceHotplugGuard,
    }
    impl LinuxCpuBatch<'_> {
        fn observe(&mut self, cpu: usize) -> Result<HostCpuSnapshot> {
            self.devices[cpu].as_ref().ok_or(ENODEV)?;
            observed_cpu(cpu, &CpuReadGuard::lock(), self._hotplug)
        }
    }

    // std::sync::Mutex has the same T: Send bounds as the pinned kernel Lock:
    // both Send and Sync require Send, not Sync, of the protected payload.
    struct Mutex<T>(std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        fn lock(&self) -> super::CountedGuard<'_, T> {
            let guard=self.0.lock().unwrap();super::CPU_LOCKS.fetch_add(1,Ordering::AcqRel);super::CountedGuard {guard,counter:&super::CPU_LOCKS}
        }
    }
    type ContextMutex = Mutex<&'static mut CpuContext>;
    static PUBLISHED: AtomicPtr<ContextMutex> = AtomicPtr::new(ptr::null_mut());
    // Representative module envelope retaining the actual extracted controller.
    // Other fields carry independent Send+Sync owners and do not hide CPU bounds.
    #[allow(dead_code)]
    struct ModuleEnvelope {
        cpu_controller: Option<CpuController>,
        other_owners: Arc<()>,
    }

    struct CpuReadGuard;
    impl CpuReadGuard {
        fn lock() -> Self {
            Self
        }
    }

    static RESET_CALLS: AtomicU32 = AtomicU32::new(0);
    static ONLINE_CALLS: AtomicU32 = AtomicU32::new(0);
    pub(super) static FINISH_STATUS: AtomicI32 = AtomicI32::new(0);
    static BLOCK_ONLINE: [AtomicBool; SMP_MAX_CPUS] = [const { AtomicBool::new(true) }; SMP_MAX_CPUS];
    pub(super) static RETIRE_CALLS: AtomicU32 = AtomicU32::new(0);
    pub(super) static MEMORY_RELEASES: AtomicU32 = AtomicU32::new(0);
    static BEGIN_CALLS: AtomicU32 = AtomicU32::new(0);
    static COMMITS: AtomicU32 = AtomicU32::new(0);
    static ROLLBACKS: AtomicU32 = AtomicU32::new(0);
    static DEVICE_DROPS: AtomicU32 = AtomicU32::new(0);
    static PIN_DROPS: AtomicU32 = AtomicU32::new(0);
    static OBSERVATIONS: [AtomicU32; SMP_MAX_CPUS] = [const { AtomicU32::new(0) }; SMP_MAX_CPUS];
    static FAIL_ON_OBSERVATION: [AtomicU32; SMP_MAX_CPUS] =
        [const { AtomicU32::new(0) }; SMP_MAX_CPUS];
    fn reset_mock() {
        bindings::reset();
        RESET_CALLS.store(0, Ordering::Relaxed);
        ONLINE_CALLS.store(0, Ordering::Relaxed);
        FINISH_STATUS.store(0, Ordering::Relaxed);
        for counter in [
            &RETIRE_CALLS,
            &MEMORY_RELEASES,
            &BEGIN_CALLS,
            &COMMITS,
            &ROLLBACKS,
            &DEVICE_DROPS,
            &PIN_DROPS,
        ] {
            counter.store(0, Ordering::Relaxed);
        }
        for cpu in 0..SMP_MAX_CPUS {
            OBSERVATIONS[cpu].store(0, Ordering::Relaxed);
            FAIL_ON_OBSERVATION[cpu].store(0, Ordering::Relaxed);
        }
    }
    fn fail_on_observation(cpu: usize, observation: u32) {
        FAIL_ON_OBSERVATION[cpu].store(observation, Ordering::Release);
    }
    fn observed_cpu(
        cpu: usize,
        _read: &CpuReadGuard,
        _hotplug: &DeviceHotplugGuard,
    ) -> Result<HostCpuSnapshot> {
        let observation = OBSERVATIONS[cpu].fetch_add(1, Ordering::AcqRel) + 1;
        let bad = observation == FAIL_ON_OBSERVATION[cpu].load(Ordering::Acquire)
            || bindings::identity_broken(cpu);
        Ok(HostCpuSnapshot {
            hardware_id: if bad { 0xffff } else { 0x20 + cpu as u32 },
            numa_node: 1,
            online: bindings::online(cpu),
        })
    }
    unsafe fn native_reset_secondary_cpu_via_init(_apic_id: u32) {
        RESET_CALLS.fetch_add(1, Ordering::Release);
    }
    struct TransitionTask;
    impl TransitionTask {
        fn new(_cpu: usize) -> Self {
            Self
        }
    }

    #[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RetainedCpuDevice(*mut bindings::device);

unsafe impl Send for RetainedCpuDevice {}

unsafe impl Sync for RetainedCpuDevice {}

impl RetainedCpuDevice {
    const fn empty() -> Self {
        Self(ptr::null_mut())
    }

    fn is_null(self) -> bool {
        self.0.is_null()
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ShutdownCpuFailureStage {
    None,
    PreResetValidation,
    DeviceOnline,
    PostOnlineValidation,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ShutdownCpuJournal {
    owner_slot: u32,
    owner_generation: u64,
    // Zero belongs to the old unscoped adapter and cannot mint a peer proof.
    boot_epoch: u64,
    cpu: u32,
    apic_id: u32,
    numa_node: u32,
    device: RetainedCpuDevice,
    recorded: bool,
    reset_attempted: bool,
    online_attempted: bool,
    /// Exact `device_online` status, retained even when a positive no-op is
    /// normalized to EIO for the fail-closed public result.
    online_status: i32,
    online: bool,
    retained: bool,
    first_failure_stage: ShutdownCpuFailureStage,
    first_failure: i32,
}

impl ShutdownCpuJournal {
    const fn empty() -> Self {
        Self {
            owner_slot: 0,
            owner_generation: 0,
            boot_epoch: 0,
            cpu: 0,
            apic_id: 0,
            numa_node: 0,
            device: RetainedCpuDevice::empty(),
            recorded: false,
            reset_attempted: false,
            online_attempted: false,
            online_status: 0,
            online: false,
            retained: false,
            first_failure_stage: ShutdownCpuFailureStage::None,
            first_failure: 0,
        }
    }

    fn record(
        &mut self,
        owner: OsToken,
        cpu: usize,
        snapshot: HostCpuSnapshot,
        device: *mut bindings::device,
    ) {
        *self = Self {
            owner_slot: owner.slot(),
            owner_generation: owner.generation(),
            boot_epoch: 0,
            cpu: cpu as u32,
            apic_id: snapshot.hardware_id,
            numa_node: snapshot.numa_node,
            device: RetainedCpuDevice(device),
            recorded: true,
            reset_attempted: false,
            online_attempted: false,
            online_status: 0,
            online: false,
            retained: false,
            first_failure_stage: ShutdownCpuFailureStage::None,
            first_failure: 0,
        };
    }

    fn matches_owner(&self, owner: OsToken) -> bool {
        self.recorded
            && self.owner_slot == owner.slot()
            && self.owner_generation == owner.generation()
    }

    fn reset_attempted(&mut self) {
        self.reset_attempted = true;
    }

    fn online(&mut self) {
        self.online = true;
    }

    fn online_attempted(&mut self) {
        self.online_attempted = true;
    }

    fn online_status(&mut self, status: i32) {
        self.online_status = status;
    }

    fn retain(&mut self, stage: ShutdownCpuFailureStage, failure: i32) {
        self.retained = true;
        if self.first_failure == 0 {
            self.first_failure_stage = stage;
            self.first_failure = failure;
        }
    }
}

fn shutdown_journal_blocks_ordinary_use(journal: &[ShutdownCpuJournal]) -> bool {
    journal.iter().any(|record| record.recorded)
}

struct CpuDevice(*mut bindings::device, Arc<super::smp_topology::Cpu>);

unsafe impl Send for CpuDevice {}

impl Drop for CpuDevice {
    fn drop(&mut self) {
        // SAFETY: This non-Copy value owns exactly one successful get_device.
        unsafe { bindings::put_device(self.0) };
    }
}

#[allow(dead_code)]
struct CpuContext {
    table: CpuTable<SMP_MAX_CPUS>,
    journal: [CpuChange; SMP_MAX_CPUS],
    shutdown_journal: [ShutdownCpuJournal; SMP_MAX_CPUS],
    requests: [usize; SMP_MAX_CPUS],
    requested: [bool; SMP_MAX_CPUS],
    devices: [Option<CpuDevice>; SMP_MAX_CPUS],
    pin: Option<ResourceModulePin>,
    poisoned: bool,
}

#[allow(dead_code)]
pub(super) struct CpuController {
    mutex: Pin<Box<ContextMutex>>,
    hotplug_state: i32,
    irq_target_state: i32,
}

pub(super) fn release_os_resources(owner: OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK's DestroyGuard and ProviderModule pin this callback and its
    // controller until both classes have been returned to the reserved pool.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    context.verify_owned(&hotplug)?;
    drop(hotplug);
    let count = context
        .table
        .assigned_cpus(owner, &mut context.requests)
        .map_err(|_| EIO)?;
    if count == 0 {
        return super::smp_memory::release_os_resources(owner, || {});
    }
    let mut transaction = context
        .table
        .prepare_release(owner, &context.requests[..count], &mut context.journal)
        .map_err(|_| EIO)?;
    transaction.begin_external_effects().map_err(|_| EIO)?;
    // Memory calls commit_cpu only after its complete preflight, while both
    // context locks remain held. No fallible operation follows that callback.
    let mut cpu_transaction = Some(transaction);
    let result = super::smp_memory::release_os_resources(owner, || {
        cpu_transaction
            .take()
            .unwrap()
            .commit()
            .unwrap_or_else(|_| panic!("OS CPU cleanup invariant violated"));
    });
    if let Some(transaction) = cpu_transaction {
        // Memory preparation failed before any ownership changed. CPU's
        // external phase consisted only of logical preflight, so compensation
        // requires no Linux hotplug operation and restores the original table.
        transaction.compensated_rollback().map_err(|_| EIO)?;
    }
    result
}

pub(super) fn reconcile_shutdown(owner: OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() { return Err(ENODEV); }
    // SAFETY: The synchronous callback retains the generation and module.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    let count = context.table.assigned_cpus(owner, &mut context.requests).map_err(|_| EIO)?;
    if count == 0 || context.shutdown_journal.iter().filter(|r| r.recorded).count() != count {
        return Err(EIO);
    }
    {
        let read = CpuReadGuard::lock();
        for index in 0..count {
            let record = context.shutdown_journal[index];
            if !record.reset_attempted || !record.online
                || record.cpu as usize != context.requests[index] { return Err(EIO); }
            context.validate_shutdown_target(owner, record, true, &read, &hotplug)?;
        }
    }
    let transaction = context.table.prepare_shutdown_online(owner, &context.requests[..count]).map_err(|_| EIO)?;
    super::smp_memory::finish_shutdown(owner, || {
        transaction.commit();
    })?;
    // Memory returns success only after invoking the infallible table commit.
    // Both policy locks and Linux hotplug exclusion covered that boundary;
    // this remaining owner cleanup is infallible under the CPU mutex.
    for index in 0..count {
        let cpu = context.requests[index];
        // Keep the module-owned Linux device reference and original topology.
        // Shutdown releases the boot assignment, not module discovery state;
        // a later reserve revalidates this identity before any offline effect.
        BLOCK_ONLINE[cpu].store(false, Ordering::Release);
        context.shutdown_journal[index] = ShutdownCpuJournal::empty();
    }
    context.poisoned = false;
    if !context.has_owned_cpu() { context.pin.take(); }
    Ok(())
}

pub(super) enum ShutdownResetFailure {
    PreEffect(Error),
    PostEffect(Error),
}

pub(super) fn shutdown_reset_and_reonline_outcome(
    owner: OsToken,
) -> core::result::Result<(), ShutdownResetFailure> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ShutdownResetFailure::PreEffect(ENODEV));
    }
    // SAFETY: The exact OS lease and operation lock retain this controller and
    // its journals across the complete reset/re-online transaction.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    match context.shutdown_reset_and_reonline(owner, &hotplug) {
        Ok(()) => Ok(()),
        Err(error) if context
            .shutdown_journal
            .iter()
            .any(|record| record.matches_owner(owner) && record.reset_attempted) =>
        {
            Err(ShutdownResetFailure::PostEffect(error))
        }
        Err(error) => Err(ShutdownResetFailure::PreEffect(error)),
    }
}
pub(super) struct StoppedCpus<'boot> {
    boot: &'boot super::smp_memory::ShutdownBoot,
}
impl StoppedCpus<'_> {
    pub(super) fn matches_owner(&self, owner: OsToken) -> bool { self.boot.matches_owner(owner) }
    pub(super) fn matches_boot(&self, boot: &super::smp_memory::ShutdownBoot) -> bool {
        self.boot.same_epoch(boot)
    }
}
pub(super) fn with_shutdown_workers_stopped(
    owner: OsToken,
    operation: impl for<'boot> FnOnce(&'boot super::smp_memory::ShutdownBoot) -> Result,
) -> Result {
    let boot = super::smp_memory::claim_shutdown_boot(owner)?;
    super::smp_memory::shutdown_close_irq_senders(owner).map_err(|failure| match failure {
        super::smp_memory::ShutdownIrqFailure::PreEffect(error)
        | super::smp_memory::ShutdownIrqFailure::PostEffect(error) => error,
    })?;
    boot.revalidate()?;
    {
        let published = PUBLISHED.load(Ordering::Acquire);
        if published.is_null() { return Err(ENODEV); }
        // SAFETY: The synchronous backend lease and boot claim retain the
        // controller. No guard or journal borrow escapes this short scope.
        let mut guard = unsafe { &*published }.lock();
        let hotplug = DeviceHotplugGuard::lock();
        guard.reset_shutdown_boot(&boot, &hotplug)?;
    }
    // All CPU/memory/hotplug guards are gone before any worker can be joined.
    boot.revalidate()?;
    let cpus = StoppedCpus { boot: &boot };
    let proof = super::sysfs_remote::PeerStopped::after_reset(&cpus);
    boot.stop_workers(&proof)?;
    operation(&boot)?;
    boot.revalidate()
}

    impl CpuContext {
        fn new(cpus: &[usize]) -> Self {
            let owner = token();
            let vacant = Slot {
                state: CpuState::Absent,
                owner: None,
                hardware_id: 0,
                numa_node: 0,
            };
            let mut context = Self {
                table: CpuTable {
                    slots: [vacant; SMP_MAX_CPUS],
                },
                shutdown_journal: [ShutdownCpuJournal::empty(); SMP_MAX_CPUS],
                journal: [CpuChange; SMP_MAX_CPUS],
                requests: [0; SMP_MAX_CPUS],
                requested: [false; SMP_MAX_CPUS],
                devices: [const { None }; SMP_MAX_CPUS],
                pin: Some(ResourceModulePin),
                poisoned: false,
            };
            for &cpu in cpus {
                context.table.slots[cpu] = Slot {
                    state: CpuState::Assigned,
                    owner: Some(owner),
                    hardware_id: 0x20 + cpu as u32,
                    numa_node: 1,
                };
                context.devices[cpu] = Some(CpuDevice(
                    (cpu + 0x1000) as *mut bindings::device,
                    Arc::new(super::smp_topology::Cpu {
                        linux_id: cpu as u32,
                        apic_id: 0x20 + cpu as u32,
                    }),
                ));
            }
            context
        }
        fn verify_owned(&mut self, hotplug: &DeviceHotplugGuard) -> Result {
        if self.poisoned || shutdown_journal_blocks_ordinary_use(&self.shutdown_journal) {
            self.poisoned = true;
            return Err(EIO);
        }
        let mut host = LinuxCpuBatch {
            devices: &self.devices,
            _hotplug: hotplug,
        };
        for cpu in 0..SMP_MAX_CPUS {
            let slot = self.table.slot(cpu).map_err(|_| EIO)?;
            match slot.state() {
                CpuState::Online | CpuState::Absent => continue,
                CpuState::Available | CpuState::Assigned => {
                    let expected = HostCpuSnapshot {
                        hardware_id: slot.hardware_id(),
                        numa_node: slot.numa_node(),
                        online: false,
                    };
                    if host.observe(cpu) == Ok(expected) {
                        continue;
                    }
                }
                _ => {}
            }
            self.poisoned = true;
            return Err(EIO);
        }
        Ok(())
    }

fn has_owned_cpu(&self) -> bool {
        (0..SMP_MAX_CPUS).any(|cpu| {
            self.table.slot(cpu).map_or(true, |slot| {
                !matches!(slot.state(), CpuState::Online | CpuState::Absent)
            })
        })
    }

fn change_os(&mut self, owner: OsToken, request: &CpuRequest, assign: bool) -> Result<isize> {
        // A retained shutdown journal is an uncertain physical transition.
        // Fence it before either changing memory's unstarted boot storage or
        // accepting a zero-count success: a later ordinary assign/release
        // must never make those retained owners look releasable again.
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        drop(hotplug);
        super::smp_memory::retire_os_boot(owner)?;
        if request.count == 0 {
            return Ok(0);
        }
        // Preserve input order: it defines the McKernel logical CPU rank.
        // The shared policy rejects duplicates and checks the whole request.
        let mut reader = UserSlice::new(request.array, request.count * 4).reader();
        for index in 0..request.count {
            let cpu = reader.read::<i32>()?;
            if cpu <= 0 || cpu as usize >= SMP_MAX_CPUS {
                return Err(EINVAL);
            }
            self.requests[index] = cpu as usize;
        }
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        drop(hotplug);
        let mut transaction = if assign {
            self.table
                .prepare_assign(owner, &self.requests[..request.count], &mut self.journal)
        } else {
            self.table
                .prepare_release(owner, &self.requests[..request.count], &mut self.journal)
        }
        .map_err(|_| EINVAL)?;
        // These are initial-state ownership transfers; Linux CPUs remain
        // offline, retained by their existing device owners and CPUHP veto.
        transaction.begin_external_effects().map_err(|_| EIO)?;
        transaction
            .commit()
            .unwrap_or_else(|_| panic!("OS CPU publication invariant violated"));
        Ok(0)
    }

fn retain_shutdown_failure(
        &mut self,
        count: usize,
        stage: ShutdownCpuFailureStage,
        failure: Error,
    ) -> Error {
        for record in &mut self.shutdown_journal[..count] {
            if record.recorded {
                record.retain(stage, failure.to_errno());
            }
        }
        self.poisoned = true;
        failure
    }

fn prevalidate_shutdown_targets(
        &self,
        owner: OsToken,
        count: usize,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let read = CpuReadGuard::lock();
        for index in 0..count {
            let cpu = self.requests[index];
            let slot = self.table.slot(cpu).map_err(|_| EIO)?;
            let device = self
                .devices
                .get(cpu)
                .and_then(Option::as_ref)
                .ok_or(ENODEV)?;
            // SAFETY: The two guards stabilize this retained CPU-device
            // association before the first irreversible journal record.
            let current = unsafe { bindings::get_cpu_device(cpu as u32) };
            let actual = observed_cpu(cpu, &read, hotplug)?;
            if device.0.is_null()
                || current != device.0
                || device.1.linux_id as usize != cpu
                || slot.state() != CpuState::Assigned
                || slot.owner() != Some(owner)
                || slot.hardware_id() != device.1.apic_id
                || slot.numa_node() != actual.numa_node
                || actual.hardware_id != device.1.apic_id
                || actual.online
            {
                return Err(EIO);
            }
        }
        Ok(())
    }

fn validate_shutdown_target(
        &self,
        owner: OsToken,
        record: ShutdownCpuJournal,
        expected_online: bool,
        topology: &CpuReadGuard,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let cpu = record.cpu as usize;
        if !record.matches_owner(owner) || cpu == 0 || cpu >= SMP_MAX_CPUS {
            return Err(EIO);
        }
        let slot = self.table.slot(cpu).map_err(|_| EIO)?;
        let retained = self.devices.get(cpu).and_then(Option::as_ref).ok_or(EIO)?;
        // SAFETY: The two guards stabilize the CPU-device association. The
        // record was captured from this retained, get_device-owned pointer.
        let current = unsafe { bindings::get_cpu_device(cpu as u32) };
        if record.device.is_null()
            || current != record.device.0
            || retained.0 != record.device.0
            || retained.1.linux_id as usize != cpu
            || retained.1.apic_id != record.apic_id
            || slot.state() != CpuState::Assigned
            || slot.owner() != Some(owner)
            || slot.hardware_id() != record.apic_id
            || slot.numa_node() != record.numa_node
        {
            return Err(EIO);
        }
        let actual = observed_cpu(cpu, topology, hotplug)?;
        if actual.hardware_id != record.apic_id
            || actual.numa_node != record.numa_node
            || actual.online != expected_online
        {
            return Err(EIO);
        }
        Ok(())
    }

fn shutdown_reset_and_reonline(
        &mut self,
        owner: OsToken,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let retry = shutdown_journal_blocks_ordinary_use(&self.shutdown_journal);
        if retry {
            if self.shutdown_journal.iter().any(|r| r.recorded && !r.matches_owner(owner)) {
                return Err(EIO);
            }
        } else if self.poisoned {
            return Err(EIO);
        }
        let count = self
            .table
            .assigned_cpus(owner, &mut self.requests)
            .map_err(|_| EIO)?;
        if count == 0 {
            return Err(EINVAL);
        }

        if retry {
            if self.shutdown_journal.iter().filter(|r| r.recorded).count() != count
                || (0..count).any(|i| self.shutdown_journal[i].cpu as usize != self.requests[i])
            {
                return Err(EIO);
            }
        } else {
        self.prevalidate_shutdown_targets(owner, count, hotplug)?;

        // The complete canonical device/identity preflight above finished
        // before the first record. Record every target before any reset or
        // online effect, so every later error has a complete retention set.
        // The stored device pointer is held live by CpuDevice's get_device
        // reference until a separate, successful lifecycle release.
        for index in 0..count {
            let cpu = self.requests[index];
            let slot = self
                .table
                .slot(cpu)
                .unwrap_or_else(|_| panic!("shutdown CPU prevalidation lost a canonical slot"));
            let device = self.devices[cpu]
                .as_ref()
                .unwrap_or_else(|| panic!("shutdown CPU prevalidation lost a retained device"));
            self.shutdown_journal[index].record(
                owner,
                cpu,
                HostCpuSnapshot {
                    hardware_id: slot.hardware_id(),
                    numa_node: slot.numa_node(),
                    online: false,
                },
                device.0,
            );
        }
        }

        {
            let read = CpuReadGuard::lock();
            for index in 0..count {
                let record = self.shutdown_journal[index];
                // Linux may return an error after changing the online bit.
                // Prove the current exact identity before recognizing that
                // effect; never repeat device_online on an already-online AP.
                if record.online_attempted && self.validate_shutdown_target(
                    owner, record, true, &read, hotplug).is_ok() {
                    self.shutdown_journal[index].online();
                    continue;
                }
                if self
                    .validate_shutdown_target(owner, record,
                        record.online || (record.online_attempted && record.online_status == 0),
                        &read, hotplug)
                    .is_err()
                {
                    return Err(self.retain_shutdown_failure(
                        count,
                        ShutdownCpuFailureStage::PreResetValidation,
                        EIO,
                    ));
                }
            }
            for index in 0..count {
                let record = &mut self.shutdown_journal[index];
                if record.reset_attempted { continue; }
                // SAFETY: CPU read exclusion fixes this validated APIC target.
                // The pending native wrapper owns its exact preemption bracket
                // and returns before this Rust code can reach device_online.
                unsafe { native_reset_secondary_cpu_via_init(record.apic_id) };
                record.reset_attempted();
            }
        }

        // CPU read-side exclusion is gone here. The wrapper's preemption
        // bracket also ended before it returned. Linux's synchronous
        // device_online is sleepable and may invoke CPUHP paths.
        for index in 0..count {
            let record = self.shutdown_journal[index];
            if record.online { continue; }
            // A successful Linux return is an applied effect even when its
            // post-observation failed. Revalidate it, never online it twice.
            if record.online_attempted && record.online_status == 0 {
                let read = CpuReadGuard::lock();
                self.validate_shutdown_target(owner, record, true, &read, hotplug)?;
                self.shutdown_journal[index].online();
                continue;
            }
            let _permission = TransitionTask::new(record.cpu as usize);
            self.shutdown_journal[index].online_attempted();
            // SAFETY: Device-hotplug exclusion and the retained journal device
            // identity serialize the exact Linux transition. Positive/no-op is
            // rejected just as strictly as a negative Linux errno.
            let status = unsafe { bindings::device_online(record.device.0) };
            self.shutdown_journal[index].online_status(status);
            if status != 0 {
                let failure = if status < 0 {
                    kernel::error::to_result(status).unwrap_err()
                } else {
                    EIO
                };
                return Err(self.retain_shutdown_failure(
                    count,
                    ShutdownCpuFailureStage::DeviceOnline,
                    failure,
                ));
            }
            let read = CpuReadGuard::lock();
            if self
                .validate_shutdown_target(owner, record, true, &read, hotplug)
                .is_err()
            {
                return Err(self.retain_shutdown_failure(
                    count,
                    ShutdownCpuFailureStage::PostOnlineValidation,
                    EIO,
                ));
            }
            self.shutdown_journal[index].online();
        }
        Ok(())
    }
fn reset_shutdown_boot(
        &mut self,
        boot: &super::smp_memory::ShutdownBoot,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let owner = boot.owner();
        if !boot.matches_owner(owner) { return Err(EIO); }
        if self.shutdown_journal.iter().any(|record| record.recorded
            && (!record.matches_owner(owner) || record.boot_epoch != boot.epoch_id())) {
            return Err(EIO);
        }
        let result = self.shutdown_reset_and_reonline(owner, hotplug);
        // Bind even a partial first attempt: a later bounded recovery must
        // retain that same boot epoch rather than adopt an owner-only journal.
        for record in &mut self.shutdown_journal {
            if record.matches_owner(owner) && record.boot_epoch == 0 {
                record.boot_epoch = boot.epoch_id();
            }
        }
        result?;
        let count = self.table.assigned_cpus(owner, &mut self.requests).map_err(|_| EIO)?;
        if count == 0 || self.shutdown_journal.iter().filter(|record| record.recorded).count() != count {
            return Err(EIO);
        }
        let read = CpuReadGuard::lock();
        for index in 0..count {
            let record = self.shutdown_journal[index];
            if record.boot_epoch != boot.epoch_id() || !record.reset_attempted || !record.online
                || !record.online_attempted || record.online_status != 0
                || record.cpu as usize != self.requests[index] {
                return Err(EIO);
            }
            self.validate_shutdown_target(owner, record, true, &read, hotplug)?;
        }
        Ok(())
    }
    }

    fn token() -> OsToken {
        OsToken {
            slot: 7,
            generation: 91,
        }
    }
    fn run(cpus: &[usize]) -> (CpuContext, Result) {
        let mut context = CpuContext::new(cpus);
        let result = context.shutdown_reset_and_reonline(token(), &DeviceHotplugGuard);
        (context, result)
    }


    fn install_cpu(cpus:&[usize])->&'static Mutex<&'static mut CpuContext> {
        let context=Box::leak(Box::new(CpuContext::new(cpus)));
        let mutex=Box::leak(Box::new(Mutex(std::sync::Mutex::new(context))));
        PUBLISHED.store(mutex,Ordering::Release);mutex
    }
    fn setup_epoch(cpus:&[usize])->&'static Mutex<&'static mut CpuContext> {
        super::reset_integration_state();reset_mock();super::STOP_CALLS.store(0,Ordering::Release);super::IRQ_STATUS.store(0,Ordering::Release);
        super::smp_memory::setup(token());install_cpu(cpus)
    }
    #[test] fn scoped_success_joins_outside_all_dependent_locks_and_keeps_admission_closed() {
        let cpu=setup_epoch(&[1,2]);let mut observed=false;
        assert_eq!(with_shutdown_workers_stopped(token(),|boot| {
            observed=true;assert_eq!(boot.revalidate(),Ok(()));
            assert!(!super::smp_memory::admission_open(token()));
            assert_eq!(super::smp_memory::ordinary_boot(token()),Err(EBUSY));
            assert!(matches!(super::smp_memory::claim_shutdown_boot(token()),Err(EBUSY)));
            Ok(())
        }),Ok(()));
        assert!(observed);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),1);
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),2);
        assert!(!super::smp_memory::admission_open(token()));
        let cpu=cpu.lock();assert!(cpu.shutdown_journal[..2].iter().all(|r|r.boot_epoch!=0));
        assert!(cpu.devices[1].is_some()&&cpu.devices[2].is_some());
        assert!(cpu.table.slots[1].owner==Some(token()));
    }
    #[test] fn stale_generation_and_same_generation_reboot_cannot_adopt_journal() {
        let cpu=setup_epoch(&[1]);
        let stale=OsToken{slot:token().slot(),generation:token().generation()-1};
        assert!(matches!(super::smp_memory::claim_shutdown_boot(stale),Err(EIO)));
        assert_eq!(with_shutdown_workers_stopped(token(), |_|Ok(())),Ok(()));
        let first=cpu.lock().shutdown_journal[0].boot_epoch;
        super::smp_memory::replace_epoch(token());
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("stale epoch reached callback")),Err(EIO));
        assert_eq!(cpu.lock().shutdown_journal[0].boot_epoch,first);
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),1);
    }
    #[test] fn reset_error_partial_online_and_irq_error_never_mint_worker_authority() {
        for status in [-19,1] {
            let cpu=setup_epoch(&[1,2]);bindings::set_status(2,status);
            let result=with_shutdown_workers_stopped(token(), |_|panic!("partial proof reached callback"));
            assert!(result.is_err());assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
            let cpu=cpu.lock();assert!(cpu.shutdown_journal[..2].iter().all(|r|r.boot_epoch!=0&&r.recorded));
            assert!(cpu.devices[1].is_some()&&cpu.devices[2].is_some());
        }
        setup_epoch(&[1]);super::IRQ_STATUS.store(-5,Ordering::Release);
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("IRQ failure reached callback")),Err(EIO));
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
    }
    #[test] fn complete_but_unscoped_legacy_journal_cannot_mint_proof() {
        let cpu=setup_epoch(&[1]);
        {let mut cpu=cpu.lock();assert_eq!(cpu.shutdown_reset_and_reonline(token(),&DeviceHotplugGuard::lock()),Ok(()));}
        assert_eq!(with_shutdown_workers_stopped(token(), |_|panic!("legacy journal reached callback")),Err(EIO));
        assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);
    }
    #[test] fn active_claim_excludes_concurrent_claim_and_reboot_and_stale_commit() {
        setup_epoch(&[1]);let boot=super::smp_memory::claim_shutdown_boot(token()).unwrap();
        let owner=token();std::thread::spawn(move || {
            assert!(matches!(super::smp_memory::claim_shutdown_boot(owner),Err(EBUSY)));
            assert_eq!(super::smp_memory::ordinary_boot(owner),Err(EBUSY));
            assert!(!super::smp_memory::admission_open(owner));
        }).join().unwrap();
        super::smp_memory::shutdown_close_irq_senders(token()).ok().unwrap();
        assert_eq!(boot.revalidate(),Ok(()));
        super::smp_memory::replace_epoch(token());assert_eq!(boot.revalidate(),Err(EIO));
    }
    #[test] fn ended_transaction_revokes_peer_authority_and_post_join_revalidation() {
        setup_epoch(&[1]);let boot=super::smp_memory::claim_shutdown_boot(token()).unwrap();
        super::smp_memory::shutdown_close_irq_senders(token()).ok().unwrap();
        {let mut guard=unsafe{&*PUBLISHED.load(Ordering::Acquire)}.lock();guard.reset_shutdown_boot(&boot,&DeviceHotplugGuard::lock()).unwrap();}
        let cpus=StoppedCpus{boot:&boot};let proof=super::sysfs_remote::PeerStopped::after_reset(&cpus);
        assert!(proof.matches_boot(&boot));super::smp_memory::invalidate(token());
        assert!(!proof.matches_boot(&boot));assert_eq!(boot.stop_workers(&proof),Err(EIO));
        assert_eq!(super::STOP_CALLS.load(Ordering::Acquire),0);
        setup_epoch(&[1]);
        assert_eq!(with_shutdown_workers_stopped(token(), |_| {super::smp_memory::replace_epoch(token());Ok(())}),Err(EIO));
    }
    pub(super) fn fixture_owner(slot:u32,generation:u64)->OsToken {OsToken{slot,generation}}
    pub(super) fn fixture_peer_scope(operation:impl for<'a> FnOnce(&super::sysfs_remote::PeerStopped<'a>)) {
        setup_epoch(&[1]);
        with_shutdown_workers_stopped(token(),|boot| {
            // The actual orchestrator already proved IRQ drain/reset/re-online
            // for this exact live boot before exposing its post-join scope.
            let cpus=StoppedCpus{boot};let proof=super::sysfs_remote::PeerStopped::after_reset(&cpus);
            operation(&proof);Ok(())
        }).unwrap();
    }
    pub(super) struct ShutdownFailure {
    pub(super) stage: &'static str,
    pub(super) error: Error,
    pub(super) post_effect: bool,
}
impl ShutdownFailure {
    fn at(stage: &'static str, error: Error, post_effect: bool) -> Self {
        Self { stage, error, post_effect }
    }
}
pub(super) fn shutdown_os_boot(
    boot: super::smp_memory::ShutdownBoot,
) -> core::result::Result<(), ShutdownFailure> {
    let owner = boot.owner();
    // Acquiring this boot claim has already closed native admission. Its Drop
    // retains that close, so even an IRQ-local PreEffect error is externally
    // post-effect: IHK must never restore Running/reopen its callback gate.
    boot.close_application_admission().map_err(|error|
        ShutdownFailure::at("application_quiesce", error, true))?;
    super::smp_memory::shutdown_close_irq_senders(owner).map_err(|failure| match failure {
        super::smp_memory::ShutdownIrqFailure::PreEffect(error) =>
            ShutdownFailure::at("irq_close", error, true),
        super::smp_memory::ShutdownIrqFailure::PostEffect(error) =>
            ShutdownFailure::at("irq_close", error, true),
    })?;
    boot.revalidate().map_err(|error| ShutdownFailure::at("epoch_before_reset", error, true))?;
    {
        let published = PUBLISHED.load(Ordering::Acquire);
        if published.is_null() { return Err(ShutdownFailure::at("reset_reonline", ENODEV, true)); }
        // SAFETY: The synchronous backend lease and boot claim retain this
        // controller and exact journal. Neither guard escapes to worker joins.
        let mut guard = unsafe { &*published }.lock();
        let hotplug = DeviceHotplugGuard::lock();
        guard.reset_shutdown_boot(&boot, &hotplug)
            .map_err(|error| ShutdownFailure::at("reset_reonline", error, true))?;
    }
    boot.revalidate().map_err(|error| ShutdownFailure::at("epoch_after_reset", error, true))?;
    {
        let cpus = StoppedCpus { boot: &boot };
        let proof = super::sysfs_remote::PeerStopped::after_reset(&cpus);
        boot.retire_services(&proof)
            .map_err(|error| ShutdownFailure::at("services_retire", error, true))?;
    }
    // The borrowed peer witness is gone; move the SAME live claim into the
    // coupled logical commit. No owner-only reconstruction is permitted.
    reconcile_shutdown_boot(boot).map_err(|error| ShutdownFailure::at("reconcile", error, true))
}
fn reconcile_shutdown_boot(boot: super::smp_memory::ShutdownBoot) -> Result {
    let owner = boot.owner();
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() { return Err(ENODEV); }
    // SAFETY: The provider lease retains the module and the claim retains this
    // exact stopped boot. The CPU -> memory lock order covers only preflight
    // and the infallible logical commit, never callback removal or a join.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    let count = context.table.assigned_cpus(owner, &mut context.requests).map_err(|_| EIO)?;
    if count == 0 || context.shutdown_journal.iter().filter(|record| record.recorded).count() != count {
        return Err(EIO);
    }
    {
        let read = CpuReadGuard::lock();
        for index in 0..count {
            let record = context.shutdown_journal[index];
            if record.boot_epoch != boot.epoch_id() || !record.reset_attempted
                || !record.online || !record.online_attempted || record.online_status != 0
                || record.cpu as usize != context.requests[index] { return Err(EIO); }
            context.validate_shutdown_target(owner, record, true, &read, &hotplug)?;
        }
    }
    context.observe_shutdown_cpus(&boot, "prepared", count);
    let transaction = context.table.prepare_shutdown_online(owner, &context.requests[..count]).map_err(|_| EIO)?;
    super::smp_memory::finish_shutdown_claim(&boot, || { transaction.commit(); })?;
    context.observe_shutdown_cpus(&boot, "committed", count);
    for index in 0..count {
        let cpu = context.requests[index];
        // Keep the module-owned Linux device reference and original topology.
        // Shutdown releases the boot assignment, not module discovery state;
        // a later reserve revalidates this identity before any offline effect.
        BLOCK_ONLINE[cpu].store(false, Ordering::Release);
        context.shutdown_journal[index] = ShutdownCpuJournal::empty();
    }
    context.poisoned = false;
    if !context.has_owned_cpu() { context.pin.take(); }
    // The final Started Arc can run Thread/Runtime destructors. Even though
    // each thread is already joined, keep that drop outside dependent locks.
    drop(hotplug);
    drop(guard);
    drop(boot);
    Ok(())
}

    fn invoke_provider()->i64{unsafe{super::ihk_smp_shutdown_v6(token().slot(),token().generation())}}
    fn assert_retained(cpu:&Mutex<&mut CpuContext>){
        assert!(super::smp_memory::integration_image_present(token()));
        assert!(super::smp_memory::integration_assigned(token()));
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
        let cpu=cpu.lock();assert_eq!(cpu.table.slots[1].owner,Some(token()));assert!(cpu.devices[1].is_some());
    }
    #[test]fn integrated_quiescent_provider_consumes_same_claim_and_releases_exactly_once(){
        let cpu=setup_epoch(&[1,2]);assert_eq!(invoke_provider(),0);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
        assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),3);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);
        assert!(!super::smp_memory::integration_image_present(token()));assert!(!super::smp_memory::integration_assigned(token()));
        {let cpu=cpu.lock();for c in [1,2]{assert!(cpu.devices[c].is_some());assert_eq!(cpu.table.slots[c].owner,None);assert_eq!(cpu.table.slots[c].state,CpuState::Online);assert!(!cpu.shutdown_journal[c-1].recorded);}}
        assert_eq!(invoke_provider(),-22);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);
    }
    #[test]fn integrated_active_application_and_pager_are_post_claim_busy_without_discard(){
        for kind in [1,6]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            let result=invoke_provider();assert_ne!(result&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_eq!(result as u32 as i32,-16);assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);
            assert!(super::smp_memory::service::reserve_after_close());
            if kind==1{assert_eq!(super::smp_memory::service::app_retained(),1);}
            assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),0);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),0);assert_retained(cpu);
        }
    }
    #[test]fn integrated_active_callback_pending_worker_and_procfs_are_post_effect_busy(){
        for kind in [2,4,5,7]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            let result=invoke_provider();assert_ne!(result,0);assert_ne!(result&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);
            assert_eq!(RESET_CALLS.load(Ordering::Acquire),1);assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),0);
            assert!(super::smp_memory::service::namespaces_retained());assert_retained(cpu);
        }
    }
    #[test]fn integrated_ledger_busy_and_map_preflight_failure_retain_all_physical_owners(){
        for kind in [3,0]{let cpu=setup_epoch(&[1]);super::smp_memory::service::configure(kind);
            if kind==0{super::MAP_STATUS.store(-5,Ordering::Release);}
            assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
            assert_eq!(super::NAMESPACE_DROPS.load(Ordering::Acquire),2);assert_eq!(super::JOIN_COUNT.load(Ordering::Acquire),3);
        }
    }
    #[test]fn integrated_same_epoch_is_revalidated_after_callback_drain_before_commit(){
        let cpu=setup_epoch(&[1]);super::INJECT_STALE.store(true,Ordering::Release);
        assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
    }
    #[test]fn integrated_irq_release_failure_preserves_both_logical_maps_and_devices(){
        let cpu=setup_epoch(&[1]);super::IRQ_RELEASE_STATUS.store(-5,Ordering::Release);
        assert_ne!(invoke_provider()&super::IHK_SMP_SHUTDOWN_V6_POST_EFFECT,0);assert_retained(cpu);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
    }
    #[test]fn integrated_actual_file_tree_drop_blocks_release_until_linux_callback_drain_returns(){
        setup_epoch(&[1]);super::CALLBACK_DRAIN_BLOCK.store(true,Ordering::Release);
        let running=std::thread::spawn(invoke_provider);
        let deadline=std::time::Instant::now()+std::time::Duration::from_secs(2);
        while super::CALLBACK_DRAIN_ENTERED.load(Ordering::Acquire)==0{assert!(std::time::Instant::now()<deadline);std::thread::yield_now();}
        super::no_dependent_locks();assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);assert_eq!(super::CALLBACK_STORAGE_DROPS.load(Ordering::Acquire),0);
        assert!(super::smp_memory::integration_image_present(token()));
        super::CALLBACK_DRAIN_BLOCK.store(false,Ordering::Release);assert_eq!(running.join().unwrap(),0);
        assert_eq!(super::CALLBACK_STORAGE_DROPS.load(Ordering::Acquire),2);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
    }
    #[test]fn integrated_worker_join_blocks_final_release_without_dependent_locks(){
        setup_epoch(&[1]);super::JOIN_BLOCK.store(true,Ordering::Release);
        let running=std::thread::spawn(invoke_provider);
        let deadline=std::time::Instant::now()+std::time::Duration::from_secs(2);
        while super::JOIN_ENTERED.load(Ordering::Acquire)==0{assert!(std::time::Instant::now()<deadline);std::thread::yield_now();}
        super::no_dependent_locks();assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);
        assert!(super::smp_memory::integration_image_present(token()));assert_eq!(super::smp_memory::ordinary_boot(token()),Err(EBUSY));
        super::JOIN_BLOCK.store(false,Ordering::Release);assert_eq!(running.join().unwrap(),0);
        assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);
    }


    fn runtime_setup()->(super::os_registry::OsRegistry,super::os_registry::OsHandle){
        let registry=super::os_registry::OsRegistry::new();
        for _ in 0..7{registry.reserve().unwrap().commit().unwrap();}
        for _ in 0..90{let reservation=registry.reserve().unwrap();assert_eq!(reservation.handle().minor(),7);drop(reservation);}
        let handle=registry.reserve().unwrap().commit().unwrap();assert_eq!((handle.minor(),handle.generation()),(7,91));
        registry.transition(handle,super::os_registry::OsStatus::Booting).unwrap();
        registry.transition(handle,super::os_registry::OsStatus::Running).unwrap();
        super::runtime_consumer::reset();(registry,handle)
    }
    #[test]fn integrated_runtime_keeps_running_closed_after_every_post_claim_gate_effect(){
        for kind in [1,6,8]{let cpu=setup_epoch(&[1]);let(registry,handle)=runtime_setup();
            if kind==8{super::IRQ_PRE_STATUS.store(-5,Ordering::Release);}else{super::smp_memory::service::configure(kind);}
            let result=super::runtime_consumer::transaction(&registry,handle,false);
            assert_eq!(result,if kind==8{-5}else{-16});
            assert!(super::runtime_consumer::closed(),"IHK admission reopened after native gate closure");
            assert_eq!(registry.snapshot(handle).unwrap().status,super::os_registry::OsStatus::Shutdown,"registry restored Running while native gates remain closed");
            assert!(!super::smp_memory::admission_open(token()));
            if kind!=8{assert!(super::smp_memory::service::reserve_after_close());}
            assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_retained(cpu);
        }
    }
    #[test]fn integrated_runtime_true_no_claim_failure_restores_running_without_closing_native_gates(){
        let cpu=setup_epoch(&[1]);let(registry,handle)=runtime_setup();
        assert_eq!(super::runtime_consumer::transaction(&registry,handle,true),-5);
        assert!(!super::runtime_consumer::closed());
        assert_eq!(registry.snapshot(handle).unwrap().status,super::os_registry::OsStatus::Running);
        assert!(super::smp_memory::admission_open(token()));
        assert!(!super::smp_memory::service::reserve_after_close());
        assert_eq!(RESET_CALLS.load(Ordering::Acquire),0);assert_retained(cpu);
    }

impl CpuContext {
fn observe_shutdown_cpus(&self, boot: &super::smp_memory::ShutdownBoot, phase: &str, count: usize) {
        let owner = boot.owner();
        let emitted = count.min(64);
        pr_info!("IHK-SMP: resource-cpu-v1 os={} generation={} epoch={} phase={} rows={} emitted={} complete={}\n",
            owner.slot(), owner.generation(), boot.epoch_id(), phase, count, emitted, (count <= 64) as u8);
        for index in 0..emitted {
            let cpu = self.requests[index];
            if let Ok(slot) = self.table.slot(cpu) {
                let token = slot.owner();
                pr_info!("IHK-SMP: resource-cpu-row-v1 os={} generation={} epoch={} phase={} index={} cpu={} hardware={} numa={} state={:?} owner_none={} owner_slot={} owner_generation={}\n",
                    owner.slot(), owner.generation(), boot.epoch_id(), phase, index, cpu,
                    slot.hardware_id(), slot.numa_node(), slot.state(), token.is_none() as u8,
                    token.map_or(0, |token| token.slot()), token.map_or(0, |token| token.generation()));
            }
        }
    }
}

    #[test]
    fn actual_resource_observations_preserve_commit_and_failure_boundaries(){
      let output=std::env::var("M05_OBSERVATION_OUTPUT").unwrap();
      for (case,failure) in [("good",0),("irq_retained",1),("map_retained",2),("epoch_retained",3),("bounded_unknown",4)] {
        setup_epoch(&[1,2]);
        let epoch=super::smp_memory::integration_epoch(token());
        match failure {1=>{super::IRQ_RELEASE_STATUS.store(-5,Ordering::Release);},
          2=>{super::MAP_STATUS.store(-5,Ordering::Release);},
          3=>{super::INJECT_STALE.store(true,Ordering::Release);},
          4=>{super::OBSERVE_MANY.store(true,Ordering::Release);},_=>{}}
        let result=invoke_provider();
        let logs=super::OBSERVATION_LOGS.lock().unwrap().join("");
        std::fs::write(format!("{}/{}.log",output,case),&logs).unwrap();
        std::fs::write(format!("{}/{}.json",output,case),format!("{{\"os\":7,\"generation\":91,\"epoch\":{},\"result\":{}}}\n",epoch,result)).unwrap();
        if failure==0||failure==4 {assert_eq!(result,0);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),1);}
        else {assert_ne!(result,0);assert_eq!(super::MEMORY_COMMITS.load(Ordering::Acquire),0);assert!(!logs.contains("phase=committed"));}
      }
    }

// COMPILE_FAIL_CONTROL

}


mod smp_application {
 use super::smp_cpu::{OsToken,Result};
 use super::AdapterMutex as Mutex;
 use std::sync::atomic::{AtomicBool,AtomicI32,Ordering};
 const EBUSY:i32=-16;const ENODEV:i32=-19;const EINVAL:i32=-22;const EAGAIN:i32=-11;
 fn errno(error:i32)->i32{error}
 #[derive(Clone,Copy)] pub(super) struct Token(u64);
 struct Exchange{pid:i32,token:Token}
 impl Exchange {fn new(_owner:i32,_cpu:i32,pid:i32)->Result<Self>{Ok(Self{pid,token:Token(pid as u64)})}fn pid(&self)->i32{self.pid}fn token(&self)->Token{self.token}}
 struct Mailbox{busy:bool}
 impl Mailbox {fn new()->Result<Self>{Ok(Self{busy:false})}fn drained(&self)->bool{!self.busy}}
 struct Entry {parent_slot_pins:u32,fork_ingress:Option<()>,inherited_root:Option<()>,cleanup:Exchange,owner_slot:i32,prepare:Option<()>,schedule:Option<()>,retirement:Option<()>,retirement_after:u64,procfs:Option<()>,syscalls:Mailbox,scheduled:bool,needs_cleanup:bool,closed:bool,quarantined:bool}
 struct Registry{entries:Mutex<Vec<Option<()>>>}
 impl Registry {pub(crate) fn shutdown_quiescent(&self) -> Result {
        let entries = self.entries.lock();
        if entries.iter().any(Option::is_some) {
            return Err(EBUSY);
        }
        Ok(())
    }
 }
 pub(super) struct Remote {owner:OsToken,slots:Mutex<Vec<Option<Entry>>>,shutdown_closed:AtomicBool,transport_error:AtomicI32,releases:Mutex<Mailbox>,pagers:Registry}
 impl Remote {
  pub(crate) fn reserve(&self, pid: i32) -> Result<Token> {
        let syscalls = Mailbox::new().map_err(errno)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if self.shutdown_closed.load(Ordering::Acquire) { return Err(ENODEV); }
        // Late and quarantined requests continue excluding numeric PID reuse.
        if slots
            .iter()
            .flatten()
            .any(|entry| entry.cleanup.pid() == pid)
        {
            return Err(EINVAL);
        }
        let slot = slots.iter_mut().find(|slot| slot.is_none()).ok_or(EAGAIN)?;
        let cleanup = Exchange::new(self.owner.slot() as i32, 0, pid).map_err(errno)?;
        let token = cleanup.token();
        *slot = Some(Entry {
            cleanup,
            owner_slot: self.owner.slot() as i32,
            prepare: None,
            schedule: None,
            retirement: None,
            retirement_after: 0,
            procfs: None,
            syscalls,
            scheduled: false,
            needs_cleanup: false,
            closed: false,
            quarantined: false,
            parent_slot_pins: 0,
            fork_ingress:None,
            inherited_root:None,
        });
        Ok(token)
    }
fn transport_health(&self) -> Result {
        let error = self.transport_error.load(Ordering::Acquire);
        if error == 0 {
            Ok(())
        } else {
            Err(errno(error))
        }
    }
pub(crate) fn shutdown_close_if_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        self.shutdown_closed.store(true, Ordering::Release);
        if slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }
pub(crate) fn shutdown_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        if !self.shutdown_closed.load(Ordering::Acquire)
            || slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }
  pub(super) fn fixture()->Self {Self{owner:super::smp_cpu::fixture_owner(7,91),slots:Mutex::new(vec![None,None]),shutdown_closed:AtomicBool::new(false),transport_error:AtomicI32::new(0),releases:Mutex::new(Mailbox{busy:false}),pagers:Registry{entries:Mutex::new(vec![None,None])}}}
  pub(super) fn fixture_busy(&self){assert!(self.reserve(123).is_ok());}
  pub(super) fn fixture_retained(&self)->usize{self.slots.lock().iter().filter(|slot|slot.is_some()).count()}
  pub(super) fn fixture_pager_busy(&self){self.pagers.entries.lock()[0]=Some(());}
 }
}
mod callback_boundary {
 use std::{ptr,sync::Arc};
 struct ParentMutex(std::sync::Mutex<bool>);
 impl ParentMutex{fn lock(&self)->std::sync::MutexGuard<'_,bool>{self.0.lock().unwrap()}}
 struct ObjectRef(*mut ());
 unsafe impl Send for ObjectRef{} unsafe impl Sync for ObjectRef{}
 struct DirectoryState{registered:ParentMutex,object:ObjectRef}
 trait AttributeOps:Send+Sync{}
 struct Marker;
 impl AttributeOps for Marker{}
 impl Drop for Marker{fn drop(&mut self){assert!(!crate::CALLBACK_DRAIN_BLOCK.load(crate::Ordering::Acquire));crate::CALLBACK_STORAGE_DROPS.fetch_add(1,crate::Ordering::AcqRel);}}
 struct Attribute{attr:usize}
 struct AttributeStorage<T>{attribute:Attribute,_operations:T}
 struct File<T:AttributeOps>{parent:Arc<DirectoryState>,storage:Box<AttributeStorage<T>>}
 mod bindings{pub unsafe fn sysfs_remove_file_ns(_object:*mut (),_attribute:*const usize,_namespace:*const ()){
  crate::no_dependent_locks();crate::CALLBACK_DRAIN_ENTERED.fetch_add(1,crate::Ordering::AcqRel);
  while crate::CALLBACK_DRAIN_BLOCK.load(crate::Ordering::Acquire){std::thread::yield_now();}
 }}
 impl<T: AttributeOps> Drop for File<T> {
    fn drop(&mut self) {
        let registered = self.parent.registered.lock();
        if !*registered {
            return;
        }
        // SAFETY: The mutex excludes direct parent removal; the unique file
        // registration owns this exact parent/name. Linux
        // deactivates and drains callbacks before returning; only then may
        // fields drop. A previously removed parent has no replacement under
        // this old kobject, and the separate reference keeps it valid.
        unsafe {
            bindings::sysfs_remove_file_ns(
                self.parent.object.0,
                &self.storage.attribute.attr,
                ptr::null(),
            )
        };
    }
}
 struct Node{_file:File<Marker>}
 pub(super) struct Tree{nodes:Vec<Node>}
 impl Drop for Tree {
    fn drop(&mut self) {
        // All children were published after their parents. Preserve that order
        // on removal, then drain every file/link before its parent's last put.
        while let Some(node) = self.nodes.pop() {
            drop(node);
        }
    }
}
 pub(super) fn tree()->Tree{let parent=Arc::new(DirectoryState{registered:ParentMutex(std::sync::Mutex::new(true)),object:ObjectRef(ptr::null_mut())});Tree{nodes:vec![Node{_file:File{parent,storage:Box::new(AttributeStorage{attribute:Attribute{attr:0},_operations:Marker})}}]}}
}
impl From<sysfs_remote::Error> for i32{fn from(error:sysfs_remote::Error)->Self{error.0}}

mod abi {
pub const IHK_OS_STATUS_NOT_BOOTED: i32 = 0;
pub const IHK_OS_STATUS_LOADING: i32 = 1;
pub const IHK_OS_STATUS_BOOTING: i32 = 2;
pub const IHK_OS_STATUS_BOOTED: i32 = 3;
pub const IHK_OS_STATUS_READY: i32 = 4;
pub const IHK_OS_STATUS_RUNNING: i32 = 5;
pub const IHK_OS_STATUS_FREEZING: i32 = 6;
pub const IHK_OS_STATUS_FROZEN: i32 = 7;
pub const IHK_OS_STATUS_SHUTDOWN: i32 = 8;
pub const IHK_OS_STATUS_FAILED: i32 = 9;
pub const IHK_OS_STATUS_HUNGUP: i32 = 10;
pub const IHK_OS_STATUS_COUNT: i32 = 11;
}
mod os_registry {
// SPDX-License-Identifier: GPL-2.0
//! Allocation-free OS-minor registry and lifecycle-state foundation.
//!
//! The frozen IHK core reserves the first free entry from a 64-element table,
//! marks it invalid while creation is in progress, publishes it only after
//! initialization, refuses destruction while references are held, and returns
//! the slot to the table only after destruction succeeds.  This module models
//! those ownership rules without calling C or allocating memory.  A generation
//! is part of every handle so an entry recycled at the same minor cannot be
//! mistaken for the prior OS instance.

use core::sync::atomic::{AtomicU64, Ordering};

use super::abi::{
    IHK_OS_STATUS_BOOTED, IHK_OS_STATUS_BOOTING, IHK_OS_STATUS_COUNT, IHK_OS_STATUS_FAILED,
    IHK_OS_STATUS_FREEZING, IHK_OS_STATUS_FROZEN, IHK_OS_STATUS_HUNGUP, IHK_OS_STATUS_LOADING,
    IHK_OS_STATUS_NOT_BOOTED, IHK_OS_STATUS_READY, IHK_OS_STATUS_RUNNING, IHK_OS_STATUS_SHUTDOWN,
};

pub(crate) const OS_CAPACITY: usize = 64;

// Linux errno values used by the frozen host-driver paths.
const ENOENT: i32 = 2;
const ENOMEM: i32 = 12;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EOVERFLOW: i32 = 75;
const ESTALE: i32 = 116;
const EUCLEAN: i32 = 117;

const PHASE_MASK: u64 = 0x7;
const PHASE_VACANT: u64 = 0;
const PHASE_RESERVED: u64 = 1;
const PHASE_LIVE: u64 = 2;
const PHASE_DESTROYING: u64 = 3;
const PHASE_RETIRED: u64 = 4;

const STATUS_SHIFT: u32 = 3;
const STATUS_MASK: u64 = 0xf << STATUS_SHIFT;
const REFERENCE_SHIFT: u32 = 7;
const REFERENCE_MASK: u64 = 0xffff << REFERENCE_SHIFT;
const REFERENCE_ONE: u64 = 1 << REFERENCE_SHIFT;
const MAX_REFERENCES: u16 = u16::MAX;
const GENERATION_SHIFT: u32 = 23;
const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum OsStatus {
    NotBooted = 0,
    Loading = 1,
    Booting = 2,
    Booted = 3,
    Ready = 4,
    Running = 5,
    Freezing = 6,
    Frozen = 7,
    Shutdown = 8,
    Failed = 9,
    Hungup = 10,
}

impl OsStatus {
    const fn from_bits(value: u8) -> Result<Self, RegistryError> {
        match value {
            0 => Ok(Self::NotBooted),
            1 => Ok(Self::Loading),
            2 => Ok(Self::Booting),
            3 => Ok(Self::Booted),
            4 => Ok(Self::Ready),
            5 => Ok(Self::Running),
            6 => Ok(Self::Freezing),
            7 => Ok(Self::Frozen),
            8 => Ok(Self::Shutdown),
            9 => Ok(Self::Failed),
            10 => Ok(Self::Hungup),
            _ => Err(RegistryError::Corrupt),
        }
    }
}

// Keep the state representation tied to the canonical x86_64 ABI capture.
const _: [(); OsStatus::NotBooted as usize] = [(); IHK_OS_STATUS_NOT_BOOTED as usize];
const _: [(); OsStatus::Loading as usize] = [(); IHK_OS_STATUS_LOADING as usize];
const _: [(); OsStatus::Booting as usize] = [(); IHK_OS_STATUS_BOOTING as usize];
const _: [(); OsStatus::Booted as usize] = [(); IHK_OS_STATUS_BOOTED as usize];
const _: [(); OsStatus::Ready as usize] = [(); IHK_OS_STATUS_READY as usize];
const _: [(); OsStatus::Running as usize] = [(); IHK_OS_STATUS_RUNNING as usize];
const _: [(); OsStatus::Freezing as usize] = [(); IHK_OS_STATUS_FREEZING as usize];
const _: [(); OsStatus::Frozen as usize] = [(); IHK_OS_STATUS_FROZEN as usize];
const _: [(); OsStatus::Shutdown as usize] = [(); IHK_OS_STATUS_SHUTDOWN as usize];
const _: [(); OsStatus::Failed as usize] = [(); IHK_OS_STATUS_FAILED as usize];
const _: [(); OsStatus::Hungup as usize] = [(); IHK_OS_STATUS_HUNGUP as usize];

// Each bit names a permitted next state.  Re-publishing the current state is
// idempotent and is accepted separately.  The matrix is intentionally strict:
// it follows the observable load/boot/monitor/freeze/shutdown paths of the
// frozen SMP provider and rejects all unreviewed edges.
const ALLOWED_TRANSITIONS: [u16; 11] = [
    (1 << 1) | (1 << 2), // not-booted -> load/boot
    (1 << 0) | (1 << 8), // loading -> initial/shutdown
    (1 << 3) | (1 << 4) | (1 << 5) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 4) | (1 << 5) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 6) | (1 << 8) | (1 << 9) | (1 << 10),
    1 << 0,                         // shutdown -> initial
    (1 << 0) | (1 << 8),            // failed -> initial/shutdown
    (1 << 0) | (1 << 8) | (1 << 9), // hungup -> initial/shutdown/fail
];

const _: [(); ALLOWED_TRANSITIONS.len()] = [(); IHK_OS_STATUS_COUNT as usize];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum RegistryError {
    NotFound,
    Capacity,
    Busy,
    InvalidMinor,
    InvalidTransition,
    GenerationExhausted,
    ReferenceOverflow,
    StaleHandle,
    Corrupt,
}

impl RegistryError {
    pub(crate) const fn errno(self) -> i32 {
        match self {
            Self::NotFound => -ENOENT,
            Self::Capacity => -ENOMEM,
            Self::Busy => -EBUSY,
            Self::InvalidMinor | Self::InvalidTransition => -EINVAL,
            Self::GenerationExhausted | Self::ReferenceOverflow => -EOVERFLOW,
            Self::StaleHandle => -ESTALE,
            Self::Corrupt => -EUCLEAN,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct OsHandle {
    minor: u8,
    generation: u64,
}

impl OsHandle {
    pub(crate) const fn minor(self) -> usize {
        self.minor as usize
    }

    pub(crate) const fn generation(self) -> u64 {
        self.generation
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct OsSnapshot {
    pub(crate) handle: OsHandle,
    pub(crate) status: OsStatus,
    pub(crate) references: u16,
}

struct Slot {
    word: AtomicU64,
}

impl Slot {
    const fn new() -> Self {
        Self {
            word: AtomicU64::new(0),
        }
    }
}

pub(crate) struct OsRegistry {
    slots: [Slot; OS_CAPACITY],
}

impl OsRegistry {
    pub(crate) const fn new() -> Self {
        Self {
            slots: [const { Slot::new() }; OS_CAPACITY],
        }
    }

    pub(crate) fn reserve(&self) -> Result<ReservationGuard<'_>, RegistryError> {
        let mut generation_exhausted = false;

        for minor in 0..OS_CAPACITY {
            let slot = &self.slots[minor];
            loop {
                let current = slot.word.load(Ordering::Acquire);
                match phase(current) {
                    PHASE_VACANT => {
                        let old_generation = generation(current);
                        if old_generation == MAX_GENERATION {
                            let retired =
                                pack(PHASE_RETIRED, OsStatus::NotBooted, 0, old_generation);
                            if slot
                                .word
                                .compare_exchange(
                                    current,
                                    retired,
                                    Ordering::AcqRel,
                                    Ordering::Acquire,
                                )
                                .is_ok()
                            {
                                generation_exhausted = true;
                                break;
                            }
                            continue;
                        }

                        let next_generation = old_generation + 1;
                        let reserved =
                            pack(PHASE_RESERVED, OsStatus::NotBooted, 0, next_generation);
                        if slot
                            .word
                            .compare_exchange(
                                current,
                                reserved,
                                Ordering::AcqRel,
                                Ordering::Acquire,
                            )
                            .is_ok()
                        {
                            return Ok(ReservationGuard {
                                registry: self,
                                handle: OsHandle {
                                    minor: minor as u8,
                                    generation: next_generation,
                                },
                                reserved,
                                armed: true,
                            });
                        }
                    }
                    PHASE_RETIRED => {
                        generation_exhausted = true;
                        break;
                    }
                    PHASE_RESERVED | PHASE_LIVE | PHASE_DESTROYING => break,
                    _ => return Err(RegistryError::Corrupt),
                }
            }
        }

        if generation_exhausted {
            Err(RegistryError::GenerationExhausted)
        } else {
            Err(RegistryError::Capacity)
        }
    }

    pub(crate) fn resolve_minor(&self, minor: usize) -> Result<OsHandle, RegistryError> {
        let slot = self.slot_by_minor(minor)?;
        let current = slot.word.load(Ordering::Acquire);
        match phase(current) {
            PHASE_LIVE => Ok(OsHandle {
                minor: minor as u8,
                generation: generation(current),
            }),
            PHASE_RESERVED | PHASE_DESTROYING => Err(RegistryError::Busy),
            PHASE_VACANT | PHASE_RETIRED => Err(RegistryError::NotFound),
            _ => Err(RegistryError::Corrupt),
        }
    }

    pub(crate) fn snapshot(&self, handle: OsHandle) -> Result<OsSnapshot, RegistryError> {
        let current = self.live_word(handle)?;
        Ok(OsSnapshot {
            handle,
            status: status(current)?,
            references: references(current),
        })
    }

    pub(crate) fn transition(&self, handle: OsHandle, next: OsStatus) -> Result<(), RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            let previous = status(current)?;
            if previous == next {
                return Ok(());
            }
            if ALLOWED_TRANSITIONS[previous as usize] & (1 << (next as u8)) == 0 {
                return Err(RegistryError::InvalidTransition);
            }
            let updated = (current & !STATUS_MASK) | ((next as u64) << STATUS_SHIFT);
            match slot
                .word
                .compare_exchange(current, updated, Ordering::AcqRel, Ordering::Acquire)
            {
                Ok(_) => return Ok(()),
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn acquire(&self, handle: OsHandle) -> Result<OsLease<'_>, RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            if references(current) == MAX_REFERENCES {
                return Err(RegistryError::ReferenceOverflow);
            }
            match slot.word.compare_exchange(
                current,
                current + REFERENCE_ONE,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(OsLease {
                        registry: self,
                        handle,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn begin_destroy(
        &self,
        handle: OsHandle,
    ) -> Result<DestroyGuard<'_>, RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            if references(current) != 0 {
                return Err(RegistryError::Busy);
            }
            let destroying = (current & !PHASE_MASK) | PHASE_DESTROYING;
            match slot.word.compare_exchange(
                current,
                destroying,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(DestroyGuard {
                        registry: self,
                        handle,
                        live: current,
                        destroying,
                        armed: true,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    /// Begin the exclusive, effect-bearing shutdown transaction.  The slot
    /// remains generation-tagged and its reference count is deliberately
    /// untouched while the transaction is in flight.
    pub(crate) fn begin_shutdown(
        &self,
        handle: OsHandle,
    ) -> Result<ShutdownGuard<'_>, RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            let previous = status(current)?;
            if !matches!(
                previous,
                OsStatus::Ready
                    | OsStatus::Running
                    | OsStatus::Failed
                    | OsStatus::Hungup
                    | OsStatus::Shutdown
            ) {
                return Err(RegistryError::InvalidTransition);
            }
            let shutdown = pack(
                PHASE_DESTROYING,
                OsStatus::Shutdown,
                references(current),
                handle.generation,
            );
            match slot
                .word
                .compare_exchange(current, shutdown, Ordering::AcqRel, Ordering::Acquire)
            {
                Ok(_) => {
                    return Ok(ShutdownGuard {
                        registry: self,
                        handle,
                        original: current,
                        shutdown,
                        armed: true,
                        irreversible: false,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn live_count(&self) -> usize {
        self.slots
            .iter()
            .filter(|slot| phase(slot.word.load(Ordering::Acquire)) == PHASE_LIVE)
            .count()
    }

    fn slot_by_minor(&self, minor: usize) -> Result<&Slot, RegistryError> {
        self.slots.get(minor).ok_or(RegistryError::InvalidMinor)
    }

    fn live_word(&self, handle: OsHandle) -> Result<u64, RegistryError> {
        checked_live_word(&self.slots[handle.minor()], handle)
    }
}

pub(crate) struct ReservationGuard<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
    reserved: u64,
    armed: bool,
}

impl ReservationGuard<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }

    pub(crate) fn commit(mut self) -> Result<OsHandle, RegistryError> {
        let live = (self.reserved & !PHASE_MASK) | PHASE_LIVE;
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(self.reserved, live, Ordering::Release, Ordering::Acquire)
            .map_err(|_| RegistryError::Corrupt)?;
        self.armed = false;
        Ok(self.handle)
    }
}

impl Drop for ReservationGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let vacant = pack(PHASE_VACANT, OsStatus::NotBooted, 0, self.handle.generation);
            let _ = self.registry.slots[self.handle.minor()]
                .word
                .compare_exchange(self.reserved, vacant, Ordering::Release, Ordering::Relaxed);
        }
    }
}

pub(crate) struct OsLease<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
}

impl OsLease<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }
}

impl Drop for OsLease<'_> {
    fn drop(&mut self) {
        let slot = &self.registry.slots[self.handle.minor()];
        loop {
            let current = slot.word.load(Ordering::Acquire);
            let shutdown =
                phase(current) == PHASE_DESTROYING && status(current) == Ok(OsStatus::Shutdown);
            if generation(current) != self.handle.generation
                || (!shutdown && phase(current) != PHASE_LIVE)
                || references(current) == 0
            {
                return;
            }
            if slot
                .word
                .compare_exchange(
                    current,
                    current - REFERENCE_ONE,
                    Ordering::Release,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                return;
            }
        }
    }
}

pub(crate) struct DestroyGuard<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
    live: u64,
    destroying: u64,
    armed: bool,
}

/// Exclusive shutdown state transaction.  `PHASE_DESTROYING` is the
/// allocation-free operation lock; the externally visible status is already
/// `Shutdown` before any backend effect may begin.
pub(crate) struct ShutdownGuard<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
    original: u64,
    shutdown: u64,
    armed: bool,
    irreversible: bool,
}

impl ShutdownGuard<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }

    pub(crate) fn status(&self) -> OsStatus {
        OsStatus::Shutdown
    }

    /// Mark the point after which dropping the guard must not roll back the
    /// original status.  The retained live word permits a later retry.
    pub(crate) fn mark_irreversible(&mut self) -> Result<(), RegistryError> {
        let current = self.registry.slots[self.handle.minor()]
            .word
            .load(Ordering::Acquire);
        if !is_shutdown_word(current, self.handle) {
            return Err(RegistryError::Busy);
        }
        self.irreversible = true;
        Ok(())
    }

    pub(crate) fn commit(mut self) -> Result<(), RegistryError> {
        let slot = &self.registry.slots[self.handle.minor()];
        loop {
            let current = slot.word.load(Ordering::Acquire);
            if !is_shutdown_word(current, self.handle) {
                return Err(RegistryError::Corrupt);
            }
            let not_booted = pack(
                PHASE_LIVE,
                OsStatus::NotBooted,
                references(current),
                self.handle.generation,
            );
            if slot
                .word
                .compare_exchange(current, not_booted, Ordering::Release, Ordering::Acquire)
                .is_ok()
            {
                break;
            }
        }
        self.armed = false;
        Ok(())
    }
}

impl Drop for ShutdownGuard<'_> {
    fn drop(&mut self) {
        if !self.armed {
            return;
        }
        let slot = &self.registry.slots[self.handle.minor()];
        loop {
            let current = slot.word.load(Ordering::Acquire);
            if !is_shutdown_word(current, self.handle) {
                break;
            }
            let target = if self.irreversible {
                (current & !PHASE_MASK) | PHASE_LIVE
            } else {
                (self.original & !REFERENCE_MASK) | (current & REFERENCE_MASK)
            };
            if slot
                .word
                .compare_exchange(current, target, Ordering::Release, Ordering::Relaxed)
                .is_ok()
            {
                break;
            }
        }
    }
}

fn is_shutdown_word(word: u64, handle: OsHandle) -> bool {
    generation(word) == handle.generation()
        && phase(word) == PHASE_DESTROYING
        && status(word) == Ok(OsStatus::Shutdown)
}

impl DestroyGuard<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }

    /// Status captured by the successful exclusive transition. Opens and
    /// status transitions cannot race this snapshot while the guard is armed.
    pub(crate) fn status(&self) -> Result<OsStatus, RegistryError> {
        status(self.live)
    }

    pub(crate) fn commit(mut self) -> Result<(), RegistryError> {
        let vacant = pack(PHASE_VACANT, OsStatus::NotBooted, 0, self.handle.generation);
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(
                self.destroying,
                vacant,
                Ordering::Release,
                Ordering::Acquire,
            )
            .map_err(|_| RegistryError::Corrupt)?;
        self.armed = false;
        Ok(())
    }
}

impl Drop for DestroyGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let _ = self.registry.slots[self.handle.minor()]
                .word
                .compare_exchange(
                    self.destroying,
                    self.live,
                    Ordering::Release,
                    Ordering::Relaxed,
                );
        }
    }
}

fn checked_live_word(slot: &Slot, handle: OsHandle) -> Result<u64, RegistryError> {
    let current = slot.word.load(Ordering::Acquire);
    if generation(current) != handle.generation {
        return Err(RegistryError::StaleHandle);
    }
    match phase(current) {
        PHASE_LIVE => Ok(current),
        PHASE_RESERVED | PHASE_DESTROYING => Err(RegistryError::Busy),
        PHASE_VACANT | PHASE_RETIRED => Err(RegistryError::NotFound),
        _ => Err(RegistryError::Corrupt),
    }
}

const fn pack(phase: u64, status: OsStatus, references: u16, generation: u64) -> u64 {
    (generation << GENERATION_SHIFT)
        | ((references as u64) << REFERENCE_SHIFT)
        | ((status as u64) << STATUS_SHIFT)
        | phase
}

const fn phase(word: u64) -> u64 {
    word & PHASE_MASK
}

const fn status(word: u64) -> Result<OsStatus, RegistryError> {
    OsStatus::from_bits(((word & STATUS_MASK) >> STATUS_SHIFT) as u8)
}

const fn references(word: u64) -> u16 {
    ((word & REFERENCE_MASK) >> REFERENCE_SHIFT) as u16
}

const fn generation(word: u64) -> u64 {
    word >> GENERATION_SHIFT
}


}
mod runtime_consumer {
use super::smp_cpu::Result;
use std::{ptr,sync::atomic::{AtomicU32,Ordering}};
const EBUSY:i32=-16;
const SHUTDOWN_V6_POST_EFFECT: i64 = 1_i64 << 62;
const SHUTDOWN_V6_PAYLOAD_MASK: i64 = 0xffff_ffff;
const ADMISSION_CLOSED: u32 = 1 << 31;
const ADMISSION_OVERFLOW: u32 = 1 << 30;
const ADMISSION_COUNT_MASK: u32 = !(ADMISSION_CLOSED | ADMISSION_OVERFLOW);
struct Admission {
    word: AtomicU32,
}
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
    /// successful boot also calls it after its registered success state is committed.
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
enum ShutdownCallbackOutcome {
    Complete,
    PreEffectFailure(i32),
    // Reserved for the future teardown adapter; v5 cannot produce this tag.
    #[allow(dead_code)]
    PostEffectFailure(i32),
}
fn shutdown_v6_outcome(result: i64) -> ShutdownCallbackOutcome {
    if result == 0 {
        return ShutdownCallbackOutcome::Complete;
    }
    // Pre-effect Linux errno values are negative and therefore have all high
    // bits set when widened.  The tag is intentionally positive so this
    // range check cannot confuse an ordinary negative errno for post-effect.
    if result >= SHUTDOWN_V6_POST_EFFECT {
        let payload = (result & SHUTDOWN_V6_PAYLOAD_MASK) as u32 as i32;
        return ShutdownCallbackOutcome::PostEffectFailure(payload);
    }
    if (-4095..0).contains(&result) {
        ShutdownCallbackOutcome::PreEffectFailure(result as i32)
    } else {
        ShutdownCallbackOutcome::PreEffectFailure(-5)
    }
}
fn shutdown_errno(result: i32) -> i32 {
    if (-4095..0).contains(&result) {
        result
    } else {
        -5
    }
}
fn finish_shutdown(
    mut guard: super::os_registry::ShutdownGuard<'_>,
    admission: ShutdownAdmission,
    outcome: ShutdownCallbackOutcome,
) -> i32 {
    match outcome {
        ShutdownCallbackOutcome::Complete => match guard.commit() {
            Ok(()) => {
                admission.commit();
                0
            }
            Err(error) => {
                // A completed callback is already post-effect.  Keep
                // admission closed even if registry publication is corrupt.
                admission.commit();
                error.errno()
            }
        },
        ShutdownCallbackOutcome::PreEffectFailure(result) => shutdown_errno(result),
        ShutdownCallbackOutcome::PostEffectFailure(result) => {
            // The callback declared an effect. Commit admission first so even
            // an unexpected registry word cannot reopen the callback surface.
            admission.commit();
            if let Err(error) = guard.mark_irreversible() {
                // ShutdownGuard may restore only the registry word on this
                // rejected publication. The effect boundary is still final:
                // the committed admission claim must remain closed while the
                // registry error is returned to the caller.
                return error.errno();
            }
            shutdown_errno(result)
        }
    }
}

    static ADMISSION:Admission=Admission::new();
    static OPERATION:std::sync::Mutex<()>=std::sync::Mutex::new(());
    pub(super) fn reset(){ADMISSION.word.store(0,Ordering::Release);}
    pub(super) fn closed()->bool{ADMISSION.is_closed()}
    pub(super) fn transaction(registry:&super::os_registry::OsRegistry,handle:super::os_registry::OsHandle,stale:bool)->i32{
        // Real production registry lease remains live across the actual callback
        // and finish consumer. std mutex supplies the operation serialization;
        // an actual Linux ProviderModule pin is outside this source fixture.
        let _lease=registry.acquire(handle).unwrap();
        let _operation=OPERATION.lock().unwrap();
        let admission=ADMISSION.close_for_shutdown().unwrap();
        let guard=registry.begin_shutdown(handle).unwrap();
        assert!(ADMISSION.is_closed());
        let generation=if stale{handle.generation()-1}else{handle.generation()};
        let result=unsafe{super::ihk_smp_shutdown_v6(handle.minor() as u32,generation)};
        finish_shutdown(guard,admission,shutdown_v6_outcome(result))
    }

}
