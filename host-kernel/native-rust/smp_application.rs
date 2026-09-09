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
use core::sync::atomic::{AtomicUsize, Ordering};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_condvar, new_mutex, Arc, CondVar, Mutex},
};

pub(crate) const CAPACITY: usize = 64;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

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
            // Existing exported monotonic seconds clock bounds repeated queries.
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

#[pin_data]
pub(crate) struct Remote {
    owner: OsToken,
    procfs: Arc<ProcfsRemote>,
    #[pin]
    slots: Mutex<Vec<Option<Entry>>>,
    #[pin]
    changed: CondVar,
    syscall_cursor: AtomicUsize,
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
                syscall_cursor: AtomicUsize::new(0), pagers, release_token,
                releases <- new_mutex!(releases) }),
            GFP_KERNEL,
        )
    }

    pub(crate) fn reserve(&self, pid: i32) -> Result<Token> {
        let syscalls = Mailbox::new().map_err(errno)?;
        let mut slots = self.slots.lock();
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
        });
        Ok(token)
    }

    pub(crate) fn queued_cpu(&self) -> Option<i32> {
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
        let image = entry.prepare.as_ref().ok_or(EINVAL)?;
        if entry.quarantined || cpu < 0 {
            return Err(EINVAL);
        }
        kernel::error::to_result(image.result().ok_or(EBUSY)?)?;
        entry.procfs.as_ref().cloned().ok_or(EIO)
    }

    pub(crate) fn publish(
        &self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
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
            if entry.syscalls.drained()
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
    ) -> Result<bool> {
        if token == self.release_token {
            return self
                .releases
                .lock()
                .publish(cpu, |packet| send(packet).map_err(|error| error.to_errno()))
                .map_err(errno);
        }
        let mut slots = self.slots.lock();
        let Some(entry) = slots
            .iter_mut()
            .flatten()
            .find(|entry| entry.key() == token)
        else {
            return Ok(false);
        };
        let published = entry
            .syscalls
            .publish(cpu, |packet| send(packet).map_err(|e| e.to_errno()))
            .map_err(errno)?;
        if entry.needs_cleanup && entry.syscalls.drained() && !entry.quarantined {
            if let Err(error) = entry.request_cleanup() {
                entry.quarantined = true;
                pr_err!(
                    "IHK-SMP: syscall drain retained application pid={} cleanup_errno={}\n",
                    entry.cleanup.pid(),
                    error.to_errno()
                );
                // Publication already happened. The caller must still notify
                // the guest even when the following cleanup cannot advance.
            }
        }
        Ok(published)
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
            let prepare = entry.prepare.as_ref().ok_or(EINVAL)?;
            kernel::error::to_result(prepare.result().ok_or(EBUSY)?)?;
            let tid = i64::from_le_bytes(bytes[..8].try_into().unwrap());
            let tid = i32::try_from(tid).map_err(|_| EINVAL)?;
            let worker = entry.syscalls.open_worker(tid).map_err(errno)?;
            bytes[8..16].copy_from_slice(&worker.to_le_bytes());
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
        bytes[48..56].copy_from_slice(&1u64.to_le_bytes());
        loop {
            let entry = slots
                .iter()
                .flatten()
                .find(|entry| entry.key() == token)
                .ok_or(ENOENT)?;
            if entry.syscalls.returned(worker, serial).map_err(errno)? {
                return Ok(());
            }
            // An interrupted return retains its original result, response and
            // worker binding for publication. WAIT cannot take new work early.
            if self.changed.wait_interruptible(&mut slots) {
                return Err(EINTR);
            }
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
