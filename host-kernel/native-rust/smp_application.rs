// SPDX-License-Identifier: GPL-2.0
//! Linux ownership for bounded, independently pumped application cleanup.

use super::{
    application_rpc::{Exchange, Token},
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

#[pin_data]
pub(crate) struct Remote {
    owner: OsToken,
    #[pin]
    slots: Mutex<Vec<Option<Exchange>>>,
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
        // Retained late requests also exclude reuse of their numeric guest PID.
        if slots.iter().flatten().any(|entry| entry.pid() == pid) {
            return Err(EINVAL);
        }
        let slot = slots.iter_mut().find(|slot| slot.is_none()).ok_or(EAGAIN)?;
        let entry = Exchange::new(self.owner.slot() as i32, 0, pid).map_err(errno)?;
        let token = entry.token();
        *slot = Some(entry);
        Ok(token)
    }

    pub(crate) fn queued(&self) -> bool {
        self.slots.lock().iter().flatten().any(Exchange::queued)
    }

    pub(crate) fn publish(&self, send: impl FnOnce(&[u8; 128]) -> Result) -> Result<bool> {
        let mut slots = self.slots.lock();
        let Some(entry) = slots.iter_mut().flatten().find(|entry| entry.queued()) else {
            return Ok(false);
        };
        let packet = entry.outgoing().ok_or(EIO)?;
        // Hold the state lock across publication and its transition. A full
        // transport retries the same owned bytes, without allocating or losing
        // the request. Failed notification after this must never undo ownership.
        send(&packet)?;
        entry.published().map_err(errno)?;
        Ok(true)
    }

    pub(crate) fn reply(&self, packet: &[u8; 128]) -> Result {
        let mut slots = self.slots.lock();
        for slot in &mut *slots {
            let Some(entry) = slot.as_mut() else {
                continue;
            };
            match entry.accept(packet) {
                Ok(()) => {
                    pr_info!("IHK-SMP: application cleanup ACK os={} generation={} pid={} token={} errno={} abandoned={}\n",
                        self.owner.slot(), self.owner.generation(), entry.pid(), entry.token().wire(),
                        entry.result().unwrap(), entry.abandoned() as u8);
                    if entry.retired() {
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
            .find(|slot| slot.as_ref().is_some_and(|entry| entry.token() == token))
        {
            let entry = slot.as_mut().unwrap();
            if entry.reserved() || entry.result().is_some() {
                *slot = None;
            } else {
                entry.abandon();
            }
        }
    }

    pub(crate) fn cleanup(&self, token: Token) -> Result {
        {
            let mut slots = self.slots.lock();
            let entry = slots
                .iter_mut()
                .flatten()
                .find(|entry| entry.token() == token)
                .ok_or(ENOENT)?;
            entry.begin().map_err(errno)?;
        }
        // Match the legacy release handler's bounded cleanup wait. No OS, CPU,
        // memory, transport or process-publication lock spans any sleep. The
        // independent packet worker continues after a timed-out caller departs.
        for _ in 0..500 {
            {
                let mut slots = self.slots.lock();
                let slot = slots
                    .iter_mut()
                    .find(|slot| slot.as_ref().is_some_and(|entry| entry.token() == token))
                    .ok_or(ENOENT)?;
                if let Some(error) = slot.as_ref().unwrap().result() {
                    *slot = None;
                    return kernel::error::to_result(error).map(|_| ());
                }
            }
            // SAFETY: Cleanup is called only from sleepable IHK file release.
            unsafe { bindings::msleep(10) };
        }
        self.close(token);
        Err(errno(-110))
    }
}
