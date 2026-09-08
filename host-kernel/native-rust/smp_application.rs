// SPDX-License-Identifier: GPL-2.0
//! Bounded application connections and independently pumped prepare/cleanup.

use super::{
    application_rpc::{Exchange, Token},
    application_syscall::Request,
    smp_application_image::Preparation,
    smp_application_syscall::Mailbox,
    smp_memory::SyscallResponse,
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
    prepare: Option<Preparation>,
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
            _ => &self.cleanup,
        }
    }
    fn next_mut(&mut self) -> &mut Exchange {
        match self.prepare.as_mut() {
            Some(prepare) if prepare.result().is_none() => &mut prepare.exchange,
            _ => &mut self.cleanup,
        }
    }
    fn request_cleanup(&mut self) -> Result {
        self.needs_cleanup = true;
        if self.quarantined {
            return Err(errno(-71));
        }
        if let Err(error) = self.syscalls.close() {
            self.quarantined = true;
            return Err(errno(error));
        }
        if !self.syscalls.drained() {
            return Ok(());
        }
        // START's future scheduled owner must supply its own retirement path.
        // Never terminate a scheduled task through the prepared-thread pointer.
        if self.scheduled {
            return Err(errno(-95));
        }
        if let Some(prepare) = &self.prepare {
            if prepare.result().is_none() {
                return Ok(());
            }
            if self.cleanup.reserved() {
                self.cleanup
                    .cleanup_target(prepare.input.cpu, prepare.thread)
                    .map_err(errno)?;
            }
        }
        if self.cleanup.reserved() {
            self.cleanup.begin().map_err(errno)?;
        }
        Ok(())
    }
}

#[pin_data]
pub(crate) struct Remote {
    owner: OsToken,
    #[pin]
    slots: Mutex<Vec<Option<Entry>>>,
    #[pin]
    changed: CondVar,
    syscall_cursor: AtomicUsize,
}

impl Remote {
    pub(crate) fn new(owner: OsToken) -> Result<Arc<Self>> {
        let mut slots = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { owner, slots <- new_mutex!(slots), changed <- new_condvar!(),
                syscall_cursor: AtomicUsize::new(0) }),
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
            prepare: None,
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

    pub(crate) fn publish(
        &self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let mut slots = self.slots.lock();
        let Some(exchange) = slots
            .iter_mut()
            .flatten()
            .map(Entry::next_mut)
            .find(|exchange| exchange.queued() && exchange.cpu() == cpu)
        else {
            return Ok(false);
        };
        let packet = exchange.outgoing().ok_or(EIO)?;
        // Queue publication and the state transition share this short lock.
        // A full queue retries the same bytes and retains every physical owner.
        send(&packet)?;
        exchange.published().map_err(errno)?;
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
                        if entry.closed && entry.cleanup.retired() {
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
            match entry.cleanup.accept(packet) {
                Ok(()) => {
                    pr_info!("IHK-SMP: application cleanup ACK os={} generation={} pid={} token={} errno={} abandoned={}\n",
                        self.owner.slot(), self.owner.generation(), entry.cleanup.pid(), entry.key().wire(),
                        entry.cleanup.result().unwrap(), entry.cleanup.abandoned() as u8);
                    if entry.closed && entry.cleanup.retired() {
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
                // An untrustworthy success cannot prove prepared-task retirement.
                // Retain its bounded slot until actual OS shutdown is implemented.
                return;
            }
            if entry.syscalls.drained()
                && (entry.prepare.is_none() && entry.cleanup.reserved()
                    || entry.cleanup.release_ready())
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
        let slots = self.slots.lock();
        let start = self.syscall_cursor.fetch_add(1, Ordering::Relaxed);
        super::smp_application_syscall::cyclic(start, slots.len()).find_map(|index| {
            let entry = slots[index].as_ref()?;
            entry.syscalls.queued_cpu().map(|cpu| (entry.key(), cpu))
        })
    }

    pub(crate) fn publish_syscall(
        &self,
        token: Token,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
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
                if entry.cleanup.release_ready() {
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
