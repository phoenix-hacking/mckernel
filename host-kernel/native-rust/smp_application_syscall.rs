// SPDX-License-Identifier: GPL-2.0
//! Owned bounded mailbox within one existing application registration.

use super::{
    application_rpc::Token,
    application_syscall::{Completion, Delivery, Request, Response, ResponseMemory, Worker},
};
use kernel::prelude::{Vec, GFP_KERNEL};

type Result<T = ()> = core::result::Result<T, i32>;
pub(crate) const CAPACITY: usize = 64;

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
}

pub(crate) struct Mailbox<M: ResponseMemory> {
    calls: Vec<Option<Call<M>>>,
    workers: Vec<Option<WorkerState>>,
    closed: bool,
    quarantined: bool,
}

impl<M: ResponseMemory> Mailbox<M> {
    pub(crate) fn new() -> Result<Self> {
        let mut calls = Vec::with_capacity(CAPACITY, GFP_KERNEL).map_err(|e| e.to_errno())?;
        let mut workers = Vec::with_capacity(CAPACITY, GFP_KERNEL).map_err(|e| e.to_errno())?;
        for _ in 0..CAPACITY {
            calls.push(None, GFP_KERNEL).map_err(|e| e.to_errno())?;
            workers.push(None, GFP_KERNEL).map_err(|e| e.to_errno())?;
        }
        Ok(Self {
            calls,
            workers,
            closed: false,
            quarantined: false,
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
        *slot = Some(Call {
            delivery,
            response: Some(response),
            completion: None,
            worker: None,
            cancelled: false,
        });
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
        // The original WAIT path serves targeted work before general work.
        let targeted = self.calls.iter().position(|slot| {
            slot.as_ref().is_some_and(|call| {
                call.delivery.eligible(worker.worker)
                    && call.delivery.request().target() == worker.worker.tid()
            })
        });
        let Some(index) = targeted.or_else(|| {
            self.calls.iter().position(|slot| {
                slot.as_ref()
                    .is_some_and(|call| call.delivery.eligible(worker.worker))
            })
        }) else {
            return Ok(None);
        };
        let call = self.calls[index].as_mut().unwrap();
        let bytes = call.delivery.reserve(worker.worker)?;
        worker.delivery = Some(call.delivery.serial());
        call.worker = Some(worker.worker);
        Ok(Some((call.delivery.serial().wire(), bytes)))
    }

    pub(crate) fn copied(&mut self, handle: u64, serial: u64, success: bool) -> Result {
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
        call.delivery.check_return(worker.worker, cpu)?;
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

    pub(crate) fn returned(&self, handle: u64, serial: u64) -> Result<bool> {
        let worker = self
            .workers
            .iter()
            .flatten()
            .find(|state| state.worker.wire() == handle)
            .ok_or(-2)?;
        if worker.completed.map(Token::wire) == Some(serial) {
            return Ok(true);
        }
        if self.quarantined {
            return Err(-71);
        }
        if worker.delivery.map(Token::wire) != Some(serial) {
            return Err(-16);
        }
        Ok(false)
    }

    pub(crate) fn queued_cpu(&self) -> Option<i32> {
        self.calls
            .iter()
            .flatten()
            .find(|call| call.completion.is_some())
            .map(|call| call.delivery.request().cpu())
    }

    /// Queue publication and final status happen under the outer application's
    /// short mutex. The caller notifies the guest and Linux waiters afterwards.
    pub(crate) fn publish(
        &mut self,
        cpu: i32,
        send: impl FnOnce(&[u8; 128]) -> Result,
    ) -> Result<bool> {
        let Some(slot) = self.calls.iter_mut().find(|slot| {
            slot.as_ref().is_some_and(|call| {
                call.delivery.request().cpu() == cpu && call.completion.is_some()
            })
        }) else {
            return Ok(false);
        };
        let call = slot.as_mut().unwrap();
        call.completion.as_mut().unwrap().publish(send)?;
        if call.cancelled {
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
        self.closed = true;
        self.cancel_pending()
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
