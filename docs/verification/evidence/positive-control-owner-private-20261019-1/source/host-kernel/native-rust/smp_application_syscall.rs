// SPDX-License-Identifier: GPL-2.0
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
    pub(crate) fn has_fork_link_response(&self, cpu: i32, matches: impl Fn(&Request) -> bool) -> bool {
        self.has_private_fork_response(cpu, 1, matches)
    }

    /// A freeze observer only; no selector or wire scalar grants authority.
    pub(crate) fn has_private_fork_response(&self, cpu: i32, selector: u64,
        matches: impl Fn(&Request) -> bool) -> bool {
        self.calls.iter().flatten().any(|call| {
            let request = call.delivery.request();
            !call.kernel && !call.service && request.number() == 56
                && request.arguments()[0] == selector && request.cpu() == cpu && matches(request)
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
        self.publish_observed(cpu, send, |_, _, _| {})
    }

    /// The metadata observer runs immediately after Completion::publish has
    /// completed status Release and response-memory release, BEFORE fallible
    /// delivery/worker bookkeeping. It may only update preallocated metadata
    /// under the caller's slots lock; no external callback or allocation.
    pub(crate) fn publish_observed(
        &mut self, cpu: i32, send: impl FnOnce(&[u8; 128]) -> Result,
        observed: impl FnOnce(&Request, Option<u64>, u64),
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
        observed(call.delivery.request(), call.worker.map(Worker::wire), call.delivery.serial().wire());
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
