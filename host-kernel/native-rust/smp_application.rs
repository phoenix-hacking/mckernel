// SPDX-License-Identifier: GPL-2.0
//! Bounded application connections and independently pumped prepare/cleanup.

use super::{
    application_rpc::{Exchange, Token},
    smp_application_image::Preparation,
    smp_resource::OsToken,
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

const CAPACITY: usize = 64;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

struct Entry {
    cleanup: Exchange,
    prepare: Option<Preparation>,
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
}

impl Remote {
    pub(crate) fn new(owner: OsToken) -> Result<Arc<Self>> {
        let mut slots = Vec::with_capacity(CAPACITY, GFP_KERNEL)?;
        for _ in 0..CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Arc::pin_init(
            pin_init!(Self { owner, slots <- new_mutex!(slots) }),
            GFP_KERNEL,
        )
    }

    pub(crate) fn reserve(&self, pid: i32) -> Result<Token> {
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

    pub(crate) fn close(&self, token: Token) {
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
            if entry.prepare.is_none() && entry.cleanup.reserved()
                || entry.cleanup.release_ready()
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
            entry.request_cleanup()?;
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
