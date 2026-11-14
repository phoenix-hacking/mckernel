#![allow(dead_code)]
use std::sync::{Arc,atomic::{AtomicBool,AtomicI32,AtomicUsize,Ordering}};
use std::marker::PhantomData;
type Error=i32;type Result<T=()>=std::result::Result<T,i32>;
const EIO:i32=-5;const ENODEV:i32=-19;const EACCES:i32=-13;const ENOENT:i32=-2;const EBUSY:i32=-16;const EINVAL:i32=-22;const EAGAIN:i32=-11;const EINTR:i32=-4;
mod kernel{pub mod error{pub fn to_result(v:i32)->std::result::Result<i32,i32>{if v<0{Err(v)}else{Ok(v)}}}}
macro_rules! pr_info{($($v:tt)*)=>{()}}
struct Mutex<T>(std::sync::Mutex<T>);impl<T> Mutex<T>{fn new(v:T)->Self{Self(std::sync::Mutex::new(v))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
#[derive(Default)]struct CondVar;impl CondVar{fn notify_all(&self){}}
mod bindings{use super::*;pub static SLEEPS:AtomicUsize=AtomicUsize::new(0);pub unsafe fn msleep(_:u32){SLEEPS.fetch_add(1,Ordering::SeqCst);}pub unsafe fn ktime_get_seconds()->i64{0}}
struct SyscallResponse;
// Existing actual-body boundary: syscall/procfs/prepared-image services are
// adapters. The exact current Exchange, Entry, counter and close/removal bodies
// below are compiled unchanged. No service/guest/kernel-runtime proof is claimed.
struct Mailbox<T>{drained:bool,closed:bool,_kind:PhantomData<T>}
impl<T> Mailbox<T>{fn new()->Result<Self>{Ok(Self{drained:true,closed:false,_kind:PhantomData})}fn drained(&self)->bool{self.drained}fn close(&mut self)->Result{self.closed=true;Ok(())}}
struct ProcfsProcess;impl ProcfsProcess{fn close(&self){}fn drained(&self)->bool{true}fn threads_retired(&self)->bool{true}}
struct Input{cpu:i32,pid:i32}struct Preparation{exchange:Exchange,input:Input,thread:u64}
impl Preparation{fn result(&self)->Option<i32>{self.exchange.result()}fn finish(&mut self,_:&mut impl FnMut(u64,usize)->Result)->Result{Ok(())}}
#[path="/home/holden/mckernel-work/host-preparation/practical-create-ppd-provider-repair-20261019-1/current-source-integration-1/application_rpc.rs"] mod application_rpc;
use application_rpc::{Exchange,Token};
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(crate) struct OsToken {
    slot: u32,
    generation: u64,
}
impl OsToken{pub(crate) const fn slot(self) -> u32 {
        self.slot
    }pub(crate) const fn generation(self) -> u64 {
        self.generation
    }}
fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}
mod actual{use super::*;
struct Entry {
    cleanup: Exchange,
    owner_slot: i32,
    prepare: Option<Preparation>,
    schedule: Option<Exchange>,
    retirement: Option<Exchange>,
    retirement_after: u64,
    procfs: Option<Arc<ProcfsProcess>>,
    syscalls: Mailbox<SyscallResponse>,
    scheduled: bool,
    needs_cleanup: bool,
    closed: bool,
    quarantined: bool,
    parent_slot_pins: usize,
}
impl Entry {
    fn key(&self) -> Token {
        self.cleanup.token()
    }
    fn next(&self) -> &Exchange {
        match self.prepare.as_ref() {
            Some(prepare) if prepare.result().is_none() => &prepare.exchange,
            _ => match self.schedule.as_ref() {
                Some(schedule) if schedule.result().is_none() => schedule,
                _ => self.retirement.as_ref().unwrap_or(&self.cleanup),
            },
        }
    }
    fn next_mut(&mut self) -> &mut Exchange {
        match self.prepare.as_mut() {
            Some(prepare) if prepare.result().is_none() => &mut prepare.exchange,
            _ => match self.schedule.as_mut() {
                Some(schedule) if schedule.result().is_none() => schedule,
                _ => self.retirement.as_mut().unwrap_or(&mut self.cleanup),
            },
        }
    }
    fn release_ready(&self) -> bool {
        !self.quarantined
            && self.parent_slot_pins == 0
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
    }

    fn request_cleanup(&mut self) -> Result {
        self.needs_cleanup = true;
        if let Some(procfs) = &self.procfs {
            procfs.close();
        }
        if self.quarantined {
            return Err(errno(-71));
        }
        // Close both admissions before waiting: procfs rundown can need a
        // blocked syscall to be cancelled by the independent packet pump.
        if let Err(error) = self.syscalls.close() {
            self.quarantined = true;
            return Err(errno(error));
        }
        if !self.scheduled {
            self.schedule = None; // Nothing published can be cancelled here.
        }
        if !self.syscalls.drained() || self.procfs.as_ref().is_some_and(|procfs| !procfs.drained())
        {
            return Ok(());
        }
        if let Some(prepare) = &self.prepare {
            if prepare.result().is_none() {
                return Ok(());
            }
            if self.cleanup.reserved() {
                self.cleanup
                    .cleanup_target(
                        prepare.input.cpu,
                        if self.scheduled { 0 } else { prepare.thread },
                    )
                    .map_err(errno)?;
            }
        }
        if self.cleanup.reserved() {
            self.cleanup.begin().map_err(errno)?;
        }
        if self.scheduled && self.cleanup.result().is_some() {
            kernel::error::to_result(self.cleanup.result().unwrap())?;
            let retry = self
                .retirement
                .as_ref()
                .is_none_or(|query| query.result() == Some(-11));
            // SAFETY: ktime_get_seconds is a permanent Linux monotonic-clock
            // export, callable while this mutex is held and independent of any
            // retiring application. Its scalar result neither borrows nor
            // changes the retained exchange state.
            let now = unsafe { bindings::ktime_get_seconds() } as u64;
            if retry && now >= self.retirement_after {
                let mut query =
                    Exchange::retirement(self.owner_slot, self.cleanup.cpu(), self.cleanup.pid())
                        .map_err(errno)?;
                query.begin().map_err(errno)?;
                self.retirement = Some(query);
            }
        }
        Ok(())
    }
}
pub(crate) struct ParentSlotPin {
    remote: core::mem::ManuallyDrop<Arc<Remote>>,
    owner: OsToken,
    parent: Token,
}
impl ParentSlotPin {
    pub(crate) fn matches(&self, remote: &Arc<Remote>, owner: OsToken, parent: Token) -> bool {
        Arc::ptr_eq(&self.remote, remote) && self.owner.slot() == owner.slot()
            && self.owner.generation() == owner.generation() && self.parent == parent
    }
}
pub(crate) struct Remote{owner:OsToken,slots:Mutex<Vec<Option<Entry>>>,changed:CondVar,transport_error:AtomicI32,shutdown_closed:AtomicBool}
impl Remote{pub(crate) fn pin_parent_slot(self: &Arc<Self>, expected_owner: OsToken,
        parent: Token) -> Result<ParentSlotPin>
    {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if self.shutdown_closed.load(Ordering::Acquire) { return Err(ENODEV); }
        if expected_owner.slot() != self.owner.slot()
            || expected_owner.generation() != self.owner.generation() { return Err(EACCES); }
        let entry = slots.iter_mut().flatten().find(|entry| entry.key() == parent).ok_or(ENOENT)?;
        if entry.owner_slot != self.owner.slot() as i32 { return Err(EACCES); }
        if entry.closed || entry.needs_cleanup || entry.quarantined { return Err(EBUSY); }
        let pins = entry.parent_slot_pins.checked_add(1).ok_or_else(|| errno(-75))?;
        let pin = ParentSlotPin { remote: core::mem::ManuallyDrop::new(self.clone()),
            owner: self.owner, parent };
        entry.parent_slot_pins = pins;
        Ok(pin)
    }
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
pub(crate) fn reply(
        &self,
        packet: &[u8; 128],
        mut memory: impl FnMut(u64, usize) -> Result,
    ) -> Result {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        for slot in &mut *slots {
            let Some(entry) = slot.as_mut() else {
                continue;
            };
            if message == super::application_rpc::TID_DELETE {
                match entry.cleanup.accept_unscheduled_delete(packet) {
                    Ok(()) => {
                        pr_info!("IHK-SMP: application unscheduled delete os={} generation={} pid={} cpu={} tid=0 cleanup_token={}\n",
                            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(),
                            entry.cleanup.cpu(), entry.key().wire());
                        if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                            *slot = None;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            if let Some(prepare) = entry
                .prepare
                .as_mut()
                .filter(|prepare| prepare.result().is_none())
            {
                match prepare.exchange.accept(packet) {
                    Ok(()) => {
                        let outcome = prepare.finish(&mut memory);
                        entry.quarantined =
                            prepare.exchange.result() == Some(0) && outcome.is_err();
                        pr_info!("IHK-SMP: application prepare ACK os={} generation={} pid={} token={} errno={} abandoned={} quarantined={}\n",
                            self.owner.slot(), self.owner.generation(), prepare.input.pid,
                            prepare.exchange.token().wire(), prepare.result().unwrap(),
                            prepare.exchange.abandoned() as u8, entry.quarantined as u8);
                        if entry.needs_cleanup && !entry.quarantined {
                            entry.request_cleanup()?;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            if let Some(query) = &mut entry.retirement {
                match query.accept(packet) {
                    Ok(()) => {
                        let result = query.result().unwrap();
                        pr_info!("IHK-SMP: application retirement os={} generation={} pid={} token={} errno={}\n",
                            self.owner.slot(), self.owner.generation(), query.pid(), query.token().wire(), result);
                        if result == -11 {
                            // SAFETY: This reads only Linux's permanent
                            // monotonic clock while the entry remains covered
                            // by slots; the value is copied into a local retry
                            // deadline and has no application-memory lifetime.
                            entry.retirement_after =
                                unsafe { bindings::ktime_get_seconds() } as u64 + 1;
                        } else if result != 0 {
                            entry.quarantined = true;
                        }
                        if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                            *slot = None;
                        }
                        return Ok(());
                    }
                    Err(-2 | -16) => continue,
                    Err(error) => return Err(errno(error)),
                }
            }
            match entry.cleanup.accept(packet) {
                Ok(()) => {
                    pr_info!("IHK-SMP: application cleanup ACK os={} generation={} pid={} token={} errno={} abandoned={}\n",
                        self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), entry.key().wire(),
                        entry.cleanup.result().unwrap(), entry.cleanup.abandoned() as u8);
                    if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                        *slot = None;
                    }
                    return Ok(());
                }
                Err(-2 | -16) => continue,
                Err(error) => return Err(errno(error)),
            }
        }
        Err(ENOENT)
    }
fn close_inner(&self, token: Token) {
        let mut slots = self.slots.lock();
        if let Some(slot) = slots
            .iter_mut()
            .find(|slot| slot.as_ref().is_some_and(|entry| entry.key() == token))
        {
            let entry = slot.as_mut().unwrap();
            if entry.quarantined {
                entry.closed = true;
                if let Some(procfs) = &entry.procfs {
                    procfs.close();
                }
                // An untrustworthy success cannot prove prepared-task retirement.
                // Retain its bounded slot until actual OS shutdown is implemented.
                return;
            }
            if entry.parent_slot_pins == 0
                && entry.syscalls.drained()
                && entry.procfs.as_ref().is_none_or(|procfs| procfs.drained())
                && (entry.prepare.is_none() && entry.cleanup.reserved() || entry.release_ready())
            {
                *slot = None;
            } else {
                entry.closed = true;
                entry.cleanup.abandon();
                if let Some(prepare) = &mut entry.prepare {
                    prepare.exchange.abandon();
                }
                let _ = entry.request_cleanup();
            }
        }
    }
pub(crate) fn close(&self, token: Token) {
        self.close_inner(token);
        self.changed.notify_all();
    }
pub(crate) fn cleanup(&self, token: Token) -> Result {
        {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            let result = entry.request_cleanup();
            drop(slots);
            self.changed.notify_all();
            result?;
        }
        // The independent packet worker continues past a departing waiter.
        for _ in 0..500 {
            {
                let mut slots = self.slots.lock();
                let slot = slots
                    .iter_mut()
                    .find(|slot| slot.as_ref().is_some_and(|entry| entry.key() == token))
                    .ok_or(ENOENT)?;
                let entry = slot.as_ref().unwrap();
                if entry.quarantined {
                    return Err(errno(-71));
                }
                if entry.release_ready() {
                    let error = entry.cleanup.result().unwrap();
                    *slot = None;
                    return kernel::error::to_result(error).map(|_| ());
                }
            }
            // SAFETY: Called only from sleepable application-owner release.
            unsafe { bindings::msleep(10) };
        }
        self.close(token);
        Err(errno(-110))
    }
}

fn owner(generation:u64)->OsToken{OsToken{slot:0,generation}}
fn remote()->Arc<Remote>{Arc::new(Remote{owner:owner(2),slots:Mutex::new((0..4).map(|_|None).collect()),changed:CondVar,transport_error:AtomicI32::new(0),shutdown_closed:AtomicBool::new(false)})}
fn count(r:&Remote,t:Token)->usize{r.slots.lock().iter().flatten().find(|e|e.key()==t).unwrap().parent_slot_pins}
fn packet(r:&Remote,t:Token)->[u8;128]{let mut slots=r.slots.lock();let e=slots.iter_mut().flatten().find(|e|e.key()==t).unwrap();let mut p=e.cleanup.outgoing().unwrap();e.cleanup.published().unwrap();p[8..12].copy_from_slice(&application_rpc::CLEANUP_REPLY.to_le_bytes());p}
fn queue(r:&Remote,t:Token){let mut slots=r.slots.lock();let e=slots.iter_mut().flatten().find(|e|e.key()==t).unwrap();e.request_cleanup().unwrap();}
#[test]fn current_pin_exact_identity_admission_overflow_and_no_effects(){
 let r=remote();let t=r.reserve(101).unwrap();let before=Arc::strong_count(&r);
 assert!(matches!(r.pin_parent_slot(owner(3),t),Err(EACCES)));
 assert!(matches!(r.pin_parent_slot(OsToken{slot:1,generation:2},t),Err(EACCES)));
 assert!(matches!(r.pin_parent_slot(owner(2),Token::allocate().unwrap()),Err(ENOENT)));
 assert_eq!(count(&r,t),0);assert_eq!(Arc::strong_count(&r),before);
 r.slots.lock()[0].as_mut().unwrap().owner_slot=1;assert!(matches!(r.pin_parent_slot(owner(2),t),Err(EACCES)));assert_eq!(count(&r,t),0);r.slots.lock()[0].as_mut().unwrap().owner_slot=0;
 r.slots.lock()[0].as_mut().unwrap().parent_slot_pins=usize::MAX;
 assert!(matches!(r.pin_parent_slot(owner(2),t),Err(-75)));assert_eq!(count(&r,t),usize::MAX);assert_eq!(Arc::strong_count(&r),before);
 for kind in 0..5{let r=remote();let t=r.reserve(100+kind).unwrap();match kind{0=>r.transport_error.store(-5,Ordering::Release),1=>r.shutdown_closed.store(true,Ordering::Release),2=>r.slots.lock()[0].as_mut().unwrap().closed=true,3=>r.slots.lock()[0].as_mut().unwrap().needs_cleanup=true,_=>r.slots.lock()[0].as_mut().unwrap().quarantined=true};assert!(r.pin_parent_slot(owner(2),t).is_err());assert_eq!(count(&r,t),0);assert_eq!(Arc::strong_count(&r),1);}
}
#[test]fn current_actual_close_reserved_removal_is_blocked_only_by_owned_slot_pin(){
 let r=remote();let t=r.reserve(101).unwrap();r.close(t);assert!(r.slots.lock().iter().all(Option::is_none));
 let r=remote();let t=r.reserve(102).unwrap();let pin=r.pin_parent_slot(owner(2),t).unwrap();assert!(pin.matches(&r,owner(2),t));assert!(!pin.matches(&r,owner(3),t));assert!(!pin.matches(&remote(),owner(2),t));assert_eq!(count(&r,t),1);
 {let slots=r.slots.lock();drop(pin);assert_eq!(slots[0].as_ref().unwrap().parent_slot_pins,1);}
 r.close(t);let slots=r.slots.lock();let e=slots[0].as_ref().unwrap();assert!(e.closed&&e.needs_cleanup);assert_eq!(e.parent_slot_pins,1);assert!(!e.release_ready());drop(slots);assert!(matches!(r.pin_parent_slot(owner(2),t),Err(EBUSY)));
 let weak=Arc::downgrade(&r);drop(r);let retained=weak.upgrade().expect("discarded pin released Remote storage");assert_eq!(retained.slots.lock()[0].as_ref().unwrap().parent_slot_pins,1);assert_eq!(Arc::strong_count(&retained),2);
}
#[test]fn current_actual_reply_and_final_cleanup_keep_pinned_slot_and_reap_unpinned_slot(){
 let r=remote();let t=r.reserve(101).unwrap();queue(&r,t);let p=packet(&r,t);assert_eq!(r.reply(&p,|_,_|Ok(())),Ok(()));assert!(r.slots.lock()[0].as_ref().unwrap().release_ready());assert_eq!(r.cleanup(t),Ok(()));assert!(r.slots.lock().iter().all(Option::is_none));
 let r=remote();let t=r.reserve(102).unwrap();let pin=r.pin_parent_slot(owner(2),t).unwrap();queue(&r,t);r.slots.lock()[0].as_mut().unwrap().closed=true;r.slots.lock()[0].as_mut().unwrap().cleanup.abandon();let p=packet(&r,t);assert_eq!(r.reply(&p,|_,_|Ok(())),Ok(()));assert_eq!(count(&r,t),1);assert!(!r.slots.lock()[0].as_ref().unwrap().release_ready());let before=bindings::SLEEPS.load(Ordering::SeqCst);assert_eq!(r.cleanup(t),Err(-110));assert_eq!(bindings::SLEEPS.load(Ordering::SeqCst)-before,500);assert_eq!(count(&r,t),1);drop(pin);
}

}
