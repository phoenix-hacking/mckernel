// SPDX-License-Identifier: GPL-2.0
//! Bounded application connections and independently pumped prepare/cleanup.

use super::{
    application_pager::Operation as PagerOperation,
    application_rpc::{Exchange, Token},
    application_syscall::Request,
    smp_application_image::Preparation,
    smp_application_syscall::Mailbox,
    smp_file_pager::{Prepared as PagerFile, Registry as Pagers},
    smp_memory::{ProcfsProcess, ProcfsRemote, SyscallResponse},
    smp_resource::OsToken,
};
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicUsize, Ordering};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_condvar, new_mutex, Arc, CondVar, Mutex},
};

#[path = "current_fork_task_mm.rs"]
mod current_fork_task_mm;
use current_fork_task_mm::ChildTaskMm;
#[path="current_fork_control.rs"]
mod current_fork_control;

pub(crate) const CAPACITY: usize = 64;
const PUBLICATION_TIMEOUT_SECONDS: u64 = 5;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

// Real inherited-root view, never a fabricated successful Preparation/Exchange.
// It is published only with the exact sealed PreparedForkIngress owner.
struct InheritedRoot {root:u64,start:u64,end:u64,uid:u32,gid:u32,control_cpu:i32,nonce:u64}
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
    fork_ingress:Option<PreparedForkIngress>,
    inherited_root:Option<InheritedRoot>,
}

impl Entry {
    fn backend_ready(&self)->Result {
        // This mutex also covers every inherited-root read. Installing the
        // owned revoke capsule therefore closes admission and drains all
        // earlier backend accesses before the out-of-lock Linux MM callback.
        if self.fork_ingress.as_ref().is_some_and(|owner|owner.host_revoke.is_some()){return Err(EBUSY);}
        if let Some(image)=&self.prepare{return kernel::error::to_result(image.result().ok_or(EBUSY)?).map(|_|());}
        if self.inherited_root.as_ref().is_some_and(|image|image.control_cpu>=0)&&self.fork_ingress.as_ref().is_some_and(|f|f.sealed.load(Ordering::Acquire)){return Ok(());}
        Err(EINVAL)
    }
    fn inherited_policy(&self,start:u64,end:u64)->Result<(u32,u32)> {
        if let Some(image)=&self.prepare{return image.inherited_policy(start,end);}
        self.backend_ready()?;let image=self.inherited_root.as_ref().ok_or(EINVAL)?;
        if image.start!=start||image.end!=end{return Err(EACCES);}Ok((image.uid,image.gid))
    }
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

/// Storage-lifetime pin only: this does not retain a task/MM, an outstanding
/// response, service admission or fork phase authority. No unauthenticated
/// release endpoint exists. Discard deliberately retains the counted slot and
/// Remote allocation; ManuallyDrop neither takes slots nor runs foreign Drop.
#[allow(dead_code)]
pub(crate) struct ParentSlotPin {
    remote: core::mem::ManuallyDrop<Arc<Remote>>,
    owner: OsToken,
    parent: Token,
}

#[allow(dead_code)]
impl ParentSlotPin {
    pub(crate) fn matches(&self, remote: &Arc<Remote>, owner: OsToken, parent: Token) -> bool {
        Arc::ptr_eq(&self.remote, remote) && self.owner.slot() == owner.slot()
            && self.owner.generation() == owner.generation() && self.parent == parent
    }
}

/// Prepared original response plus exact live child task/MM identity.
/// Discard retains every durable owner; only rollback can release the pins.
/// This does not grant a seal, successful fork, final ACK, or runnable credit.
#[must_use]
#[derive(Clone,Copy,Eq,PartialEq)]
enum ForkResponseLocation {Ticket,Mailbox,MailboxQuarantined}
pub(crate) struct PreparedForkIngress {
    remote: core::mem::ManuallyDrop<Arc<Remote>>,
    child_task: core::mem::ManuallyDrop<ChildTaskMm>,
    response: core::mem::ManuallyDrop<super::smp_application_syscall::ForkResponse<SyscallResponse>>,
    parent: Token,
    child: Token,
    finished: bool,
    response_location:ForkResponseLocation,
    sealed:AtomicBool,
    carrier_nonce:u64,
    first_return_written:bool,
    first_return_committed:bool,
    first_return_published:bool,
    host_start_return:Option<(u64,u64)>,
    lease:core::mem::ManuallyDrop<Option<BackendForkLeaseV4>>,
    host_revoke:Option<current_fork_control::OwnedRevoke>,
}
struct BackendForkLeaseV4 {owner:*mut core::ffi::c_void,release:super::application_abi::ForkLeaseReleaseV4}
// The originating IHK owner explicitly permits transfer; Drop is outside locks.
unsafe impl Send for BackendForkLeaseV4 {}
unsafe impl Sync for BackendForkLeaseV4 {}
impl Drop for BackendForkLeaseV4 {fn drop(&mut self){unsafe {(self.release)(self.owner)};}}
unsafe extern "C" fn commit_fork_seal_v4(context:*mut core::ffi::c_void) {
    // This pointer borrows a preallocated, stack-stable actual provider owner
    // through the synchronous callback only. No allocation/lock/foreign Drop.
    unsafe {&*context.cast::<AtomicBool>()}.store(true,Ordering::Release);
}
impl PreparedForkIngress {
    unsafe fn adopt_scope_v4(&mut self,call:&super::application_abi::ForkAdoptCallV4)->Result {
        let callback=call.consumer.ok_or(EINVAL)?;let active=self.child_task.active()?;
        let child_pid=self.child_task.tgid();let child_mm=active.identity() as u64;
        let sealed=core::ptr::from_ref(&self.sealed).cast_mut().cast();
        let nonce_out=&mut self.carrier_nonce;
        self.response.with_memory(|request,memory|{
            let nonce=memory.current_fork_carrier(request).map_err(|e|e.to_errno())?;
            *nonce_out=nonce;
            let scope=super::application_abi::ForkSealV4 {
                prepared:super::application_abi::ForkPreparedV3 {geometry:call.geometry,
                    child_pid,reserved:0,child_mm,response:request.response(),nonce},
                seal:Some(commit_fork_seal_v4),context:sealed};
            let status=unsafe {callback(call.context,&scope)};
            if status>0||status< -4095 {return Err(-71);}
            if status==0 {Ok(())}else{Err(status)}
        }).map_err(errno)
    }



    /// A failed rollback preserves this owner for quarantine/reconciliation.
    /// It never infers an ACK or successful publication from a return code.
    pub(crate) fn rollback(&mut self) -> Result {
        if self.finished || self.sealed.load(Ordering::Acquire) { return Err(EINVAL); }
        if self.response_location!=ForkResponseLocation::Ticket{return Err(errno(-71));}
        {
            let mut slots = self.remote.slots.lock();
            let p = slots.iter().position(|slot| slot.as_ref().is_some_and(|e| e.key() == self.parent)).ok_or(ENOENT)?;
            let c = slots.iter().position(|slot| slot.as_ref().is_some_and(|e| e.key() == self.child)).ok_or(ENOENT)?;
            if p == c || slots[p].as_ref().unwrap().parent_slot_pins == 0
                || slots[c].as_ref().unwrap().parent_slot_pins == 0 { return Err(EINVAL); }
            let disposition=slots[p].as_mut().unwrap().syscalls.restore_fork_response(&mut self.response).map_err(errno)?;
            self.response_location=ForkResponseLocation::Mailbox;
            if disposition==super::smp_application_syscall::ForkRestoreDisposition::MailboxNeedsCancellation {
                let (worker,serial)=self.response.route();
                if slots[p].as_mut().unwrap().syscalls.resume_fork_cancellation(worker,serial).is_err(){
                    self.response_location=ForkResponseLocation::MailboxQuarantined;
                    return Err(errno(-71));
                }
            }
            slots[p].as_mut().unwrap().parent_slot_pins -= 1;
            slots[c].as_mut().unwrap().parent_slot_pins -= 1;
            self.finished = true;
        }
        // Linux/task/MM/Remote Drop occurs after all provider locks end.
        unsafe {
            core::mem::ManuallyDrop::drop(&mut self.lease);
            core::mem::ManuallyDrop::drop(&mut self.child_task);
            core::mem::ManuallyDrop::drop(&mut self.response);
            core::mem::ManuallyDrop::drop(&mut self.remote);
        }
        Ok(())
    }
}

#[pin_data]
pub(crate) struct Remote {
    owner: OsToken,
    procfs: Arc<ProcfsRemote>,
    #[pin]
    slots: Mutex<Vec<Option<Entry>>>,
    #[pin]
    changed: CondVar,
    syscall_cursor: AtomicUsize,
    transport_error: AtomicI32,
    shutdown_closed: AtomicBool,
    pagers: Arc<Pagers>,
    release_token: Token,
    #[pin]
    releases: Mutex<Mailbox<SyscallResponse>>,
}

impl Remote {
    pub(crate) fn new(owner: OsToken, procfs: Arc<ProcfsRemote>) -> Result<Arc<Self>> {
        let pagers = Pagers::new()?;
        let releases = Mailbox::new().map_err(errno)?;
        let release_token = Token::allocate().map_err(errno)?;
        let mut slots = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { owner, procfs, slots <- new_mutex!(slots), changed <- new_condvar!(),
                syscall_cursor: AtomicUsize::new(0), transport_error: AtomicI32::new(0), shutdown_closed: AtomicBool::new(false), pagers, release_token,
                releases <- new_mutex!(releases) }),
            GFP_KERNEL,
        )
    }

    /// Acquire only from the exact live connection/OS owner, under the same
    /// exclusion as reserve, shutdown admission and every slot-removal gate.
    /// This is internal future-provider storage plumbing, not fork activation.
    #[allow(dead_code)]
    pub(crate) fn pin_parent_slot(self: &Arc<Self>, expected_owner: OsToken,
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

    /// Inputs must come from exact borrowed IHK parent/child application
    /// connections, with the SAME live OS/module lease. Geometry only filters
    /// an already owned delivery; it never manufactures that authority.
    /// This preparatory producer cannot seal VMAs or publish Registration.
    pub(crate) fn prepare_fork_ingress(self: &Arc<Self>, expected_owner: OsToken,
        parent: Token, child: Token, matches: impl Fn(&Request) -> bool,
    ) -> Result<PreparedForkIngress> {
        if parent == child || expected_owner.slot() != self.owner.slot()
            || expected_owner.generation() != self.owner.generation() { return Err(EACCES); }
        let child_pid = {
            let slots = self.slots.lock();
            slots.iter().flatten().find(|e| e.key() == child).ok_or(ENOENT)?.cleanup.pid()
        };
        // All task/MM acquisition and reference cleanup happen outside slots.
        let child_task = ChildTaskMm::current(child_pid)?;
        let mut slots = self.slots.lock();
        self.transport_health()?;
        if self.shutdown_closed.load(Ordering::Acquire) { return Err(ENODEV); }
        let p = slots.iter().position(|slot| slot.as_ref().is_some_and(|e| e.key() == parent)).ok_or(ENOENT)?;
        let c = slots.iter().position(|slot| slot.as_ref().is_some_and(|e| e.key() == child)).ok_or(ENOENT)?;
        let pe = slots[p].as_ref().unwrap();
        let ce = slots[c].as_ref().unwrap();
        if pe.owner_slot != self.owner.slot() as i32 || ce.owner_slot != self.owner.slot() as i32
            || ce.cleanup.pid() != child_task.tgid() { return Err(EACCES); }
        if pe.closed || pe.needs_cleanup || pe.quarantined || !pe.scheduled
            || ce.closed || ce.needs_cleanup || ce.quarantined || ce.scheduled || ce.prepare.is_some()
            || ce.parent_slot_pins != 0 || ce.fork_ingress.is_some() || ce.inherited_root.is_some() { return Err(EBUSY); }
        let pins = pe.parent_slot_pins.checked_add(1).ok_or(errno(-(bindings::EOVERFLOW as i32)))?;
        let parent_pid = pe.cleanup.pid();
        let (worker, serial, request) = pe.syscalls.unique_delivered_fork(|request| {
            request.number() == 56 && request.pid() == parent_pid && matches(request)
        }).map_err(errno)?.ok_or(ENOENT)?;
        // No allocation/identity check follows this first ownership effect.
        let response = slots[p].as_mut().unwrap().syscalls
            .park_fork_response(worker, serial, &request).map_err(errno)?;
        slots[p].as_mut().unwrap().parent_slot_pins = pins;
        slots[c].as_mut().unwrap().parent_slot_pins = 1;
        drop(slots);
        Ok(PreparedForkIngress {
            remote: core::mem::ManuallyDrop::new(self.clone()),
            child_task: core::mem::ManuallyDrop::new(child_task),
            response: core::mem::ManuallyDrop::new(response), parent, child, finished: false,
            response_location:ForkResponseLocation::Ticket,
            sealed:AtomicBool::new(false),carrier_nonce:0,first_return_written:false,first_return_committed:false,first_return_published:false,host_start_return:None,lease:core::mem::ManuallyDrop::new(None),host_revoke:None,
        })
    }


    fn prepare_inherited_backend(&self,owner:&mut PreparedForkIngress,
        geometry:super::application_abi::ForkGeometryV3)->Result<(InheritedRoot,Arc<ProcfsProcess>)> {
        let end=geometry.start.checked_add(geometry.length).ok_or(EINVAL)?;
        let(uid,gid)={let slots=self.slots.lock();let parent=slots.iter().flatten().find(|e|e.key()==owner.parent).ok_or(ENOENT)?;
            parent.inherited_policy(geometry.start,end)?};
        let control_cpu=owner.response.with_memory(|request,memory|{
            memory.validate_fork_root(request,geometry.root).map_err(|e|e.to_errno())?;Ok(request.cpu())
        }).map_err(errno)?;
        // This CPU routes existing procfs control exchanges. It never claims
        // the child's execution CPU or releases the guest's reserved CPU credit.
        let procfs=ProcfsProcess::new(self.procfs.clone(),owner.child,owner.child_task.tgid(),control_cpu,uid,gid)?;
        Ok((InheritedRoot{root:geometry.root,start:geometry.start,end,uid,gid,control_cpu,nonce:0},procfs))
    }

    pub(crate) unsafe fn adopt_current_fork(self:&Arc<Self>,parent:Token,child:Token,
        call:&mut super::application_abi::ForkAdoptCallV4)->Result {
        if call.lease.is_null()||call.release_lease.is_none()||call.consumer.is_none(){return Err(EINVAL);}
        let geometry=call.geometry;
        let mut owner=self.prepare_fork_ingress(self.owner,parent,child,|request|{
            let a=request.arguments();!matches!(a[0],1|2|3)&&a[1]==geometry.start&&a[2]==geometry.length
                &&a[3]==geometry.root&&a[4]!=0&&a[4]%8==0&&a[4].checked_add(128).is_some()
                &&a[5]==0x313030434b46434d
        })?;
        let(mut image,procfs)=match self.prepare_inherited_backend(&mut owner,geometry) {
            Ok(prepared)=>prepared,Err(error)=>{
                if owner.rollback().is_err(){return Err(errno(-71));}return Err(error);
            }
        };
        // Ownership transfer of the actual preallocated IHK object precedes
        // all callback/MM effects. No numeric ACK substitutes for this owner.
        let lease=BackendForkLeaseV4{owner:call.lease,release:call.release_lease.take().unwrap()};
        *owner.lease=Some(lease);call.lease=core::ptr::null_mut();
        let observation=unsafe {owner.adopt_scope_v4(call)};
        if owner.sealed.load(Ordering::Acquire) {
            // prepare_fork_ingress reserves the exact entry via both counted
            // pins and empty fork_ingress; removal is impossible. No fallible
            // operation or allocation follows irreversible MM publication.
            let mut slots=self.slots.lock();
            let entry=slots.iter_mut().flatten().find(|e|e.key()==child).expect("reserved fork child lost");
            assert!(entry.fork_ingress.is_none()&&entry.inherited_root.is_none()&&entry.procfs.is_none());
            image.nonce=owner.carrier_nonce;assert!(image.nonce!=0);
            entry.inherited_root=Some(image);entry.procfs=Some(procfs);
            entry.fork_ingress=Some(owner);drop(slots);
            if observation.is_err(){return Err(errno(-71));}
            return Ok(());
        }
        if owner.rollback().is_err(){return Err(errno(-71));}
        observation.and(Err(errno(-71)))
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
            fork_ingress:None,
            inherited_root:None,
        });
        Ok(token)
    }

    /// Share the reservation mutex with reserve: an Application clone taken
    /// immediately before shutdown cannot admit a new slot afterward. Busy
    /// entries remain intact so their existing owners can finish normal cleanup.
    pub(crate) fn shutdown_close_if_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        self.shutdown_closed.store(true, Ordering::Release);
        if slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }

    /// This is a negative ownership check, never a cancellation/discard path.
    pub(crate) fn shutdown_quiescent(&self) -> Result {
        let slots = self.slots.lock();
        if !self.shutdown_closed.load(Ordering::Acquire)
            || slots.iter().any(Option::is_some) || !self.releases.lock().drained() {
            return Err(EBUSY);
        }
        self.pagers.shutdown_quiescent()
    }

    pub(crate) fn queued_cpu(&self) -> Option<i32> {
        if self.transport_health().is_err() {
            return None;
        }
        self.slots
            .lock()
            .iter()
            .flatten()
            .map(Entry::next)
            .find(|exchange| exchange.queued())
            .map(Exchange::cpu)
    }

    pub(crate) fn advance(&self) -> Result {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        // This task continues even if the original RET waiter is dying. No
        // intentionally blocking user syscall is timed: only accepted results
        // whose response/wake has not reached real publication are bounded.
        // SAFETY: ktime_get_seconds is the same permanent, non-sleeping Linux
        // clock export used for retirement retries. Reading it while slots is
        // locked cannot alias application-owned memory or publish a response.
        let now = unsafe { bindings::ktime_get_seconds() } as u64;
        if let Err(error) = self.expire_publications(&mut slots, now) {
            drop(slots);
            self.changed.notify_all();
            return Err(error);
        }
        for slot in &mut *slots {
            if let Some(entry) = slot {
                if entry.needs_cleanup && !entry.quarantined {
                    if let Err(error) = entry.request_cleanup() {
                        entry.quarantined = true;
                        pr_err!(
                            "IHK-SMP: application cleanup retained pid={} errno={}\n",
                            entry.cleanup.pid(),
                            error.to_errno()
                        );
                    }
                }
                if entry.closed && entry.cleanup.retired() && entry.release_ready() {
                    *slot = None;
                }
            }
        }
        Ok(())
    }

    pub(crate) fn procfs_process(&self, pid: i32, cpu: i32) -> Result<Arc<ProcfsProcess>> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.cleanup.pid() == pid)
            .ok_or(ENOENT)?;
        entry.backend_ready()?;
        if entry.quarantined || cpu < 0 {
            return Err(EINVAL);
        }
        entry.procfs.as_ref().cloned().ok_or(EIO)
    }

    pub(crate) fn publish(
        &self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        self.transport_health()?;
        let Some(entry) = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.next().queued() && entry.next().cpu() == cpu)
        else {
            return Ok(false);
        };
        let is_schedule = entry
            .schedule
            .as_ref()
            .is_some_and(|schedule| schedule.queued());
        let exchange = entry.next_mut();
        let packet = exchange.outgoing().ok_or(EIO)?;
        // Publication and the irreversible scheduled transition share this lock.
        send(&packet)?;
        exchange.published().map_err(errno)?;
        if is_schedule {
            entry.scheduled = true;
            pr_info!(
                "IHK-SMP: application SCHEDULE os={} generation={} pid={} cpu={}\n",
                self.owner.slot(),
                self.owner.generation(),
                entry.cleanup.pid(),
                cpu
            );
            self.changed.notify_all();
        }
        Ok(true)
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

    pub(crate) fn syscall_request(
        &self,
        request: Request,
        claim: impl FnOnce(&Request) -> Result<SyscallResponse>,
    ) -> Result {
        if PagerOperation::is_release(&request) {
            let slots = self.slots.lock();
            self.transport_health()?;
            // A shared file object can outlive the original PID. This exact-OS
            // response queue owns no launcher/MM and is pumped independently.
            let result = self
                .releases
                .lock()
                .admit_serviced(
                    request,
                    |request| claim(request).map_err(|error| error.to_errno()),
                    |request| {
                        let PagerOperation::Release { handle, references } =
                            PagerOperation::decode(request).unwrap()
                        else {
                            unreachable!()
                        };
                        self.pagers
                            .release(handle, references)
                            .unwrap_or_else(|error| error.to_errno() as i64)
                    },
                )
                .map(|_| ())
                .map_err(errno);
            drop(slots);
            self.changed.notify_all();
            return result;
        }
        let result = (|| {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.cleanup.pid() == request.pid())
                .ok_or(ENOENT)?;
            if !entry.scheduled || entry.quarantined {
                return Err(EINVAL);
            }
            let result = entry
                .syscalls
                .admit(request, |request| claim(request).map_err(|e| e.to_errno()));
            if let Err(error) = result {
                if error != -11 {
                    entry.quarantined = true;
                }
                return Err(errno(error));
            }
            Ok(())
        })();
        self.changed.notify_all();
        result
    }

    pub(crate) fn syscall_cpu(&self) -> Option<(Token, i32)> {
        if self.transport_health().is_err() {
            return None;
        }
        let start = self.syscall_cursor.fetch_add(1, Ordering::Relaxed);
        if start % 2 == 0 {
            if let Some(cpu) = self.releases.lock().queued_cpu() {
                return Some((self.release_token, cpu));
            }
        }
        let slots = self.slots.lock();
        let application =
            super::smp_application_syscall::cyclic(start, slots.len()).find_map(|index| {
                let entry = slots[index].as_ref()?;
                entry.syscalls.queued_cpu().map(|cpu| (entry.key(), cpu))
            });
        drop(slots);
        application.or_else(|| {
            self.releases
                .lock()
                .queued_cpu()
                .map(|cpu| (self.release_token, cpu))
        })
    }

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
        // `send` above means only queue publication. Notification runs after
        // the response has released its memory, but under the same application
        // mutex as RET completion. Its error must never retry that publication.
        let published = self.finish_publication(&mut slots, result, notify)?;
        if published {
            // Record the original positive response at its real publication
            // boundary, under the same slots guard as every later selector1
            // admission. The sleeping RET waiter need not run first.
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token&&owner.first_return_committed
                        &&!owner.first_return_published).map(|owner|owner.response.route());
                let Some((worker,serial))=route else{continue;};
                let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
                if parent.syscalls.returned(worker,serial).map_err(errno)? {
                    slots[index].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_published=true;
                }
            }
            for index in 0..slots.len() {
                let route=slots[index].as_ref().and_then(|entry|entry.fork_ingress.as_ref())
                    .filter(|owner|owner.parent==token).and_then(|owner|owner.host_start_return);
                let Some((worker,serial))=route else{continue;};
                let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
                if parent.syscalls.returned(worker,serial).map_err(errno)? {
                    // Exact successful selector1 RET has been published. This
                    // is child admission, never destruction/final-ACK proof.
                    let child=slots[index].as_mut().unwrap();
                    child.scheduled=true;
                    child.fork_ingress.as_mut().unwrap().host_start_return=None;
                }
            }
        }
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
    }

    fn transport_health(&self) -> Result {
        let error = self.transport_error.load(Ordering::Acquire);
        if error == 0 {
            Ok(())
        } else {
            Err(errno(error))
        }
    }

    fn expire_publications(&self, slots: &mut [Option<Entry>], now: u64) -> Result {
        let expired = slots.iter_mut().flatten().any(|entry| {
            entry
                .syscalls
                .publication_expired(now, PUBLICATION_TIMEOUT_SECONDS)
        }) || self
            .releases
            .lock()
            .publication_expired(now, PUBLICATION_TIMEOUT_SECONDS);
        if expired {
            pr_err!("IHK-SMP: application transport failure os={} generation={} phase=publication_timeout errno=-110\n",
                self.owner.slot(), self.owner.generation());
            self.quarantine_transport(slots, errno(-110));
            return Err(errno(-110));
        }
        Ok(())
    }

    /// Caller holds slots; all publication, failure and admission decisions
    /// share that mutex. No guest bytes or cancellation responses are written.
    fn quarantine_transport(&self, slots: &mut [Option<Entry>], error: Error) {
        if self
            .transport_error
            .compare_exchange(0, error.to_errno(), Ordering::AcqRel, Ordering::Acquire)
            .is_err()
        {
            return;
        }
        for entry in slots.iter_mut().flatten() {
            entry.quarantined = true;
            entry.needs_cleanup = true;
            entry.syscalls.quarantine();
            if let Some(procfs) = &entry.procfs {
                procfs.close();
            }
        }
        self.releases.lock().quarantine();
    }

    /// A hard target/channel error before entering publication follows the
    /// same terminal transition. Wake after releasing all publication locks.
    pub(crate) fn fail_transport(&self, error: Error) {
        let mut slots = self.slots.lock();
        self.quarantine_transport(&mut slots, error);
        drop(slots);
        self.changed.notify_all();
    }

    /// Record a continuing-service failure at the same admission boundary as
    /// transport quarantine. The referenced error belongs to our retained
    /// Runtime. Callers hold none of the application/publication locks.
    pub(crate) fn fail_service(&self, service_error: &AtomicI32, error: Error) -> bool {
        let mut slots = self.slots.lock();
        let first = service_error.compare_exchange(
            0,
            error.to_errno(),
            Ordering::AcqRel,
            Ordering::Acquire,
        );
        let recorded = first.err().unwrap_or(error.to_errno());
        self.quarantine_transport(&mut slots, errno(recorded));
        drop(slots);
        self.changed.notify_all();
        first.is_ok()
    }

    fn finish_publication(
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
    }

    pub(crate) fn notify_syscalls(&self) {
        self.changed.notify_all();
    }

    pub(crate) fn worker(&self, token: Token, bytes: &mut [u8], open: bool) -> Result {
        if bytes.len() != 16 {
            return Err(EINVAL);
        }
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if open {
            if entry.closed || entry.needs_cleanup || entry.quarantined {
                return Err(EBUSY);
            }
            entry.backend_ready()?;
            let tid = i64::from_le_bytes(bytes[..8].try_into().unwrap());
            let tid = i32::try_from(tid).map_err(|_| EINVAL)?;
            let worker = entry.syscalls.open_worker(tid).map_err(errno)?;
            bytes[8..16].copy_from_slice(&worker.to_le_bytes());
            self.changed.notify_all();
            Ok(())
        } else {
            let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
            let result = entry.syscalls.close_worker(worker);
            entry.quarantined |= entry.syscalls.quarantined();
            result.map_err(errno)
        }
    }

    pub(crate) fn wait_syscall(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() != 96 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let mut slots = self.slots.lock();
        loop {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed || entry.needs_cleanup || entry.quarantined {
                return Err(errno(-32));
            }
            if kernel::current!().signal_pending() {
                return Err(EINTR);
            }
            if let Some((serial, output)) = entry.syscalls.reserve(worker).map_err(errno)? {
                bytes[8..16].copy_from_slice(&serial.to_le_bytes());
                bytes[16..96].copy_from_slice(&output);
                return Ok(());
            }
            // Linux queues the waiter before releasing this exact mutex. No
            // transport, OS operation or user-copy lock is held by the caller.
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn copied_syscall(&self, token: Token, bytes: &[u8]) -> Result {
        if bytes.len() != 24 {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let success = word(16);
        if success > 1 {
            return Err(EINVAL);
        }
        let result = {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            entry
                .syscalls
                .copied(word(0), word(8), success != 0)
                .map_err(errno)
        };
        self.changed.notify_all();
        result
    }


    pub(crate) fn transfer_exec(&self,token:Token,bytes:&mut[u8])->Result{
        if bytes.len()<=32||bytes.len()-32>16384{return Err(EINVAL);}
        let word=|at|u64::from_le_bytes(bytes[at..at+8].try_into().unwrap());
        let(worker,serial,physical,direction)=(word(0),word(8),word(16),word(24));
        let step=super::exec_transfer_checked::Step{physical,bytes:bytes.len()-32,direction};
        let mut slots=self.slots.lock();let entry=slots.iter_mut().flatten().find(|e|e.key()==token).ok_or(ENOENT)?;
        entry.syscalls.transfer_exec(worker,serial,step,&mut bytes[32..],
            |r,m|m.prepare_exec_delivery(r,token.wire(),worker,serial),
            |r,m,key,step,data|m.copy_exec_delivery(r,key,step,data)).map_err(errno)
    }
    pub(crate) fn exec_usercopy_done(&self,token:Token,bytes:&mut[u8])->Result{
        if bytes.len()!=24{return Err(EINVAL);}let word=|at|u64::from_le_bytes(bytes[at..at+8].try_into().unwrap());
        if word(16)>1{return Err(EINVAL);}
        let mut slots=self.slots.lock();let entry=slots.iter_mut().flatten().find(|e|e.key()==token).ok_or(ENOENT)?;
        let result=entry.syscalls.exec_usercopy_done(word(0),word(8),word(16)==1);entry.quarantined|=entry.syscalls.quarantined();
        self.changed.notify_all();result.map_err(errno)
    }

    pub(crate) fn transfer_tids(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() <= 32 || bytes.len() - 32 > super::application_image::MAX_FLAT_BYTES {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let (worker, serial, physical, direction) = (word(0), word(8), word(16), word(24));
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        entry
            .syscalls
            .transfer_tids(
                worker,
                serial,
                physical,
                &mut bytes[32..],
                direction,
                |request, memory, data| {
                    memory
                        .copy_tids(request, data)
                        .map_err(|error| error.to_errno())
                },
            )
            .map_err(errno)?;
        pr_info!("application_tids=transferred os={} generation={} pid={} worker={} delivery={} physical={:x} bytes={}\n",
            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), worker, serial, physical, bytes.len() - 32);
        Ok(())
    }

    pub(crate) fn clear_syscall(&self, token: Token, bytes: &mut [u8], finish: bool) -> Result {
        if bytes.len() != 40 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
        let value = i64::from_le_bytes(bytes[24..32].try_into().unwrap());
        bytes[16..].fill(0);
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if !finish {
            let (start, end) = entry
                .syscalls
                .begin_invalidation(worker, serial)
                .map_err(errno)?;
            bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
            bytes[24..32].copy_from_slice(&start.to_le_bytes());
            bytes[32..40].copy_from_slice(&end.to_le_bytes());
            return Ok(());
        }
        let outcome = entry.syscalls.finish_invalidation(worker, serial, value);
        entry.quarantined |= entry.syscalls.quarantined();
        let completed = outcome.map_err(errno)?;
        bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
        bytes[24..32].copy_from_slice(&completed.to_le_bytes());
        pr_info!("host_mapping=invalidated os={} generation={} pid={} worker={} delivery={} value={} completed={}\n",
            self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), worker, serial, value, completed);
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn pager_syscall(&self, token: Token, bytes: &mut [u8]) -> Result {
        if bytes.len() != 32 {
            return Err(EINVAL);
        }
        let worker = u64::from_le_bytes(bytes[..8].try_into().unwrap());
        let serial = u64::from_le_bytes(bytes[8..16].try_into().unwrap());
        bytes[16..].fill(0);
        let request = {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            entry.syscalls.begin_kernel(worker, serial).map_err(errno)?
        };
        bytes[16..24].copy_from_slice(&1u64.to_le_bytes());
        enum Work {
            Create(PagerFile),
            Value(i64),
        }
        let outcome = (|| -> Result<Work> {
            let operation = PagerOperation::decode(&request).map_err(errno)?;
            self.with_pager_memory(token, worker, serial, |request, memory| {
                memory.prepare_pager(request)
            })?;
            match operation {
                PagerOperation::Create { fd, .. } => PagerFile::open(fd).map(Work::Create),
                PagerOperation::Io {
                    write,
                    handle,
                    offset,
                    bytes,
                    ..
                } => self
                    .pagers
                    .io(write, handle, offset, bytes, |offset, data, to_guest| {
                        self.with_pager_memory(token, worker, serial, |_, memory| {
                            memory.pager_copy(offset, data, to_guest)
                        })
                    })
                    .map(Work::Value),
                PagerOperation::Release { .. } => Err(EINVAL), // Owned by continuing ingress.
            }
        })();
        let mut value = -512i64;
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        let finished = entry.syscalls.finish_kernel(worker, serial, |_, memory| {
            let result = match outcome {
                Ok(Work::Create(prepared)) => self
                    .pagers
                    .create(prepared, |data| memory.pager_copy(0, data, true)),
                Ok(Work::Value(value)) => Ok(value),
                Err(error) => Err(error),
            };
            value = result.unwrap_or_else(|error| error.to_errno() as i64);
            Ok(value)
        });
        entry.quarantined |= entry.syscalls.quarantined();
        finished.map_err(errno)?;
        bytes[24..32].copy_from_slice(&value.to_le_bytes());
        pr_info!("file_pager=completed os={} generation={} pid={} worker={} delivery={} operation={} value={}\n",
            self.owner.slot(), self.owner.generation(), request.pid(), worker, serial, request.arguments()[0], value);
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
        }
    }

    fn with_pager_memory<T>(
        &self,
        token: Token,
        worker: u64,
        serial: u64,
        operation: impl FnOnce(&Request, &mut SyscallResponse) -> Result<T>,
    ) -> Result<T> {
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        entry
            .syscalls
            .with_kernel_memory(worker, serial, |request, memory| {
                operation(request, memory).map_err(|error| error.to_errno())
            })
            .map_err(errno)
    }

    fn prepare_owned_parent_return(&self,slots:&mut [Option<Entry>],parent:Token,child_index:usize,
        worker:u64,serial:u64,cpu:i64,value:i64,length:u64)->Result {
        let parent_index=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
        if parent_index==child_index{return Err(EACCES);}
        let(p,c)=if parent_index<child_index {let(a,b)=slots.split_at_mut(child_index);
            (a[parent_index].as_mut().ok_or(ENOENT)?,b[0].as_mut().ok_or(ENOENT)?)}else{
            let(a,b)=slots.split_at_mut(parent_index);(b[0].as_mut().ok_or(ENOENT)?,a[child_index].as_mut().ok_or(ENOENT)?)};
        if p.closed||p.needs_cleanup||p.quarantined||c.closed||c.needs_cleanup||c.quarantined{return Err(EBUSY);}
        c.backend_ready()?;
        if !c.syscalls.has_open_worker(){return Err(EBUSY);}
        let image=c.inherited_root.as_ref().ok_or(EINVAL)?;let owner=c.fork_ingress.as_mut().ok_or(EINVAL)?;
        if !owner.sealed.load(Ordering::Acquire)||owner.first_return_written||owner.first_return_committed||owner.first_return_published
            ||owner.response_location!=ForkResponseLocation::Ticket||owner.parent!=parent
            ||owner.response.route()!=(worker,serial)||owner.response.request().cpu() as i64!=cpu
            ||value!=owner.child_task.tgid() as i64||value<=0||length!=0{return Err(EACCES);}
        owner.response.check_unpublished().map_err(errno)?;
        let receipt=super::application_syscall::ForkFirstReceipt {
            slot:self.owner.slot(),generation:self.owner.generation(),parent:owner.parent.wire(),worker,delivery:serial,
            child:owner.child.wire(),child_pid:owner.child_task.tgid(),child_mm:owner.child_task.identity(),
            root:image.root,start:image.start,length:image.end-image.start,nonce:image.nonce,
            response:owner.response.request().response(),
        };
        owner.response.with_memory(|request,memory|memory.write_first_fork_receipt(request,&receipt).map_err(|e|e.to_errno())).map_err(errno)?;
        owner.first_return_written=true;
        // The original response returns to its exact mailbox, never a new
        // response/RET0. Any later error records mailbox ownership and retains
        // task/MM/root/IHK owners; it cannot replay the carrier as fresh input.
        let disposition=p.syscalls.restore_fork_response(&mut owner.response).map_err(errno)?;
        owner.response_location=ForkResponseLocation::Mailbox;
        if disposition==super::smp_application_syscall::ForkRestoreDisposition::MailboxNeedsCancellation {
            if p.syscalls.resume_fork_cancellation(worker,serial).is_err(){owner.response_location=ForkResponseLocation::MailboxQuarantined;}
            return Err(errno(-71));
        }
        Ok(())
    }

    fn current_host_start_child(&self,slots:&[Option<Entry>],parent:Token,
        worker:u64,serial:u64,cpu:i64,value:i64,length:u64)->Result<Option<usize>> {
        let pe=slots.iter().flatten().find(|entry|entry.key()==parent).ok_or(ENOENT)?;
        let request=pe.syscalls.delivered_fork_request(worker,serial).map_err(errno)?;
        let Some(request)=request else{return Ok(None);};
        let args=request.arguments();
        if args[0]!=1||args[5]!=0x313030434b46434d{return Ok(None);}
        if value!=0{return Ok(None);}
        let a=request.arguments();
        if cpu!=request.cpu() as i64||length!=0||request.pid()!=pe.cleanup.pid()
            ||request.target()!=0{return Err(EACCES);}
        let mut matched=None;
        for (index,entry) in slots.iter().enumerate() {
            let Some(ce)=entry else{continue;};
            let Some(owner)=ce.fork_ingress.as_ref() else{continue;};
            if owner.parent!=parent||owner.child_task.tgid() as u64!=a[1]{continue;}
            let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            let original=owner.response.request();
            if matched.is_some()||ce.closed||ce.needs_cleanup||ce.quarantined||ce.scheduled
                ||owner.host_start_return.is_some()||owner.host_revoke.is_some()
                ||!owner.sealed.load(Ordering::Acquire)||!owner.first_return_published
                ||owner.child!=ce.key()||!ce.syscalls.has_open_worker()
                ||image.end-image.start!=a[2]||image.root!=a[3]
                ||original.arguments()[4]!=a[4]||original.arguments()[5]!=a[5]
                ||original.requester()!=request.requester()||original.cpu()!=request.cpu()
                {return Err(EACCES);}
            ce.backend_ready()?;matched=Some(index);
        }
        matched.map(Some).ok_or(EACCES)
    }

    pub(crate) fn return_syscall(
        &self,
        token: Token,
        bytes: &mut [u8],
        copy: impl FnOnce(&Request, u64, &mut [u8]) -> Result,
    ) -> Result {
        if bytes.len() != 72 {
            return Err(EINVAL);
        }
        let word = |offset| u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap());
        let (worker, serial, cpu, value, destination, length) = (
            word(0),
            word(8),
            word(16) as i64,
            word(24) as i64,
            word(32),
            word(40),
        );
        if length > 16 {
            return Err(EINVAL);
        }
        bytes[48..56].fill(0); // Output: whether the continuing owner accepted the return.
        let mut slots = self.slots.lock();
        let started_child=self.current_host_start_child(&slots,token,worker,serial,cpu,value,length)?;
        let owned_child=loop {
            let child=slots.iter().position(|e|e.as_ref().and_then(|e|e.fork_ingress.as_ref()).is_some_and(|f|
                f.parent==token&&f.response.route()==(worker,serial)));
            let Some(child)=child else {break None;};
            // CondVar waits release slots: parent close/cleanup/quarantine can
            // make this return impossible while the child remains live/unready.
            // Revalidate parent BEFORE every possible child-readiness wait.
            let parent=slots.iter().flatten().find(|entry|entry.key()==token).ok_or(ENOENT)?;
            if parent.closed||parent.needs_cleanup||parent.quarantined{return Err(EBUSY);}
            let entry=slots[child].as_ref().ok_or(ENOENT)?;
            if entry.closed||entry.needs_cleanup||entry.quarantined{return Err(EBUSY);}
            if !entry.syscalls.has_open_worker(){
                // The actual child worker must have opened against its adopted
                // MM/registration. No synthetic ready flag replaces that fact.
                if self.changed.wait_interruptible(&mut slots){return Err(EINTR);}continue;
            }
            self.prepare_owned_parent_return(&mut slots,token,child,worker,serial,cpu,value,length)?;
            break Some(child);
        };
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        let result = entry
            .syscalls
            .return_value(worker, serial, cpu, value, |request| {
                if length == 0 {
                    return Ok(());
                }
                copy(request, destination, &mut bytes[56..56 + length as usize])
                    .map_err(|e| e.to_errno())
            });
        entry.quarantined |= entry.syscalls.quarantined();
        result.map_err(errno)?;
        if let Some(child)=started_child {
            slots[child].as_mut().unwrap().fork_ingress.as_mut().unwrap().host_start_return=Some((worker,serial));
        }
        if let Some(child)=owned_child {
            slots[child].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_committed=true;
        }
        bytes[48..56].copy_from_slice(&1u64.to_le_bytes());
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.quarantined {
                return Err(errno(-71));
            }
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                if let Some(child)=owned_child {
                    // Only the continuing publisher records this observation.
                    // The waiter validates it; it cannot publish it late.
                    if !slots[child].as_ref().unwrap().fork_ingress.as_ref().unwrap().first_return_published {
                        return Err(errno(-71));
                    }
                }
                // A real first positive return is still not a runnable,
                // revoke/final-ACK, terminal release or scheduled-task receipt.
                return Ok(());
            }
            // The return is committed: complete its real publication before
            // exposing success to the launcher. A signal cannot cancel or
            // replay that result. The continuing owner still handles errors,
            // quarantine and wake publication; ordinary WAIT is interruptible.
            self.changed.wait(&mut slots);
        }
    }

    pub(crate) fn prepare(
        &self,
        token: Token,
        bytes: &mut [u8],
        cpus: usize,
        direct_map: u64,
    ) -> Result {
        // All allocations and input validation finish outside the state lock.
        let mut prepare = Preparation::new(self.owner.slot() as i32, bytes, cpus, direct_map)?;
        let (uid, gid) = prepare.procfs_credentials()?;
        let procfs = ProcfsProcess::new(
            self.procfs.clone(),
            token,
            prepare.input.pid,
            prepare.input.cpu,
            uid,
            gid,
        )?;
        {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed
                || entry.needs_cleanup
                || entry.quarantined
                || entry.prepare.is_some()
                || !entry.cleanup.reserved()
            {
                return Err(EBUSY);
            }
            if prepare.input.pid != entry.cleanup.pid() {
                return Err(EINVAL);
            }
            prepare.exchange.begin().map_err(errno)?;
            entry.procfs = Some(procfs);
            entry.prepare = Some(prepare);
        }
        for _ in 0..3000 {
            {
                let slots = self.slots.lock();
                let entry = slots
                    .iter()
                    .flatten()
                    .find(|entry| entry.key() == token)
                    .ok_or(ENOENT)?;
                let prepare = entry.prepare.as_ref().ok_or(EIO)?;
                if entry.quarantined {
                    return Err(errno(-71));
                }
                if prepare.result().is_some() {
                    return prepare.copy_result(bytes);
                }
            }
            // SAFETY: Called only from the launcher's sleepable ioctl context.
            unsafe { bindings::msleep(10) };
        }
        let mut slots = self.slots.lock();
        let entry = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.quarantined {
            return Err(errno(-71));
        }
        let prepare = entry.prepare.as_mut().ok_or(EIO)?;
        // Resolve the completion/timeout race while holding the same reply lock.
        if prepare.result().is_some() {
            return prepare.copy_result(bytes);
        }
        prepare.exchange.abandon();
        entry.request_cleanup()?;
        Err(errno(-110))
    }

    pub(crate) fn start(&self, token: Token, bytes: &[u8]) -> Result {
        let mut slots = self.slots.lock();
        {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.closed || entry.needs_cleanup || entry.quarantined || entry.schedule.is_some()
            {
                return Err(EBUSY);
            }
            let image = entry.prepare.as_ref().ok_or(EINVAL)?;
            image.authorize_start(bytes)?;
            let mut schedule = Exchange::schedule(
                self.owner.slot() as i32,
                image.input.cpu,
                image.input.pid,
                image.thread,
            )
            .map_err(errno)?;
            schedule.begin().map_err(errno)?;
            entry.schedule = Some(schedule);
        }
        loop {
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.scheduled {
                return Ok(());
            }
            if entry.needs_cleanup || entry.closed || entry.quarantined {
                return Err(EBUSY);
            }
            if self.changed.wait_interruptible(&mut slots) {
                let entry = slots
                    .iter_mut()
                    .flatten()
                    .find(|entry| entry.key() == token)
                    .ok_or(ENOENT)?;
                if entry.scheduled {
                    return Ok(());
                }
                // The same mutex excludes publication while cancelling queued work.
                entry.schedule = None;
                entry.request_cleanup()?;
                return Err(EINTR);
            }
        }
    }

    pub(crate) fn with_page_table<T>(&self,token:Token,use_root:impl FnOnce(u64)->Result<T>)->Result<T> {
        let slots=self.slots.lock();let entry=slots.iter().flatten().find(|e|e.key()==token).ok_or(ENOENT)?;
        if entry.closed||entry.needs_cleanup||entry.quarantined{return Err(EBUSY);}entry.backend_ready()?;
        let root=if let Some(image)=&entry.prepare{image.page_table}else{entry.inherited_root.as_ref().ok_or(EINVAL)?.root};
        use_root(root)
    }

    pub(crate) fn with_prepared<T>(
        &self,
        token: Token,
        use_image: impl FnOnce(&Preparation) -> Result<T>,
    ) -> Result<T> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.key() == token)
            .ok_or(ENOENT)?;
        if entry.needs_cleanup || entry.closed || entry.quarantined {
            return Err(EBUSY);
        }
        let prepare = entry.prepare.as_ref().ok_or(EINVAL)?;
        kernel::error::to_result(prepare.result().ok_or(EBUSY)?)?;
        use_image(prepare)
    }

    // Request cleanup without waiting for publication, ACK or retirement.
    // The retained entry and independent packet pump own those transitions.
    pub(crate) fn begin_cleanup(&self, token: Token) -> Result {
        let result = (|| {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            entry.request_cleanup()
        })();
        self.changed.notify_all();
        result
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
