fn credential_request(request: &Request) -> bool {
    request.number() == 122 && request.arguments()[1] == 1
}
impl<M> Mailbox<M> {
pub(crate) fn write_credentials(
        &mut self, handle: u64, serial: u64, physical: u64, bytes: &mut [u8],
        copy: impl FnOnce(&Request, &mut M, u64, &mut [u8]) -> Result,
    ) -> Result {
        if self.closed || self.quarantined { return Err(-32); }
        let worker = self.workers.iter().flatten()
            .find(|state| state.worker.wire() == handle).ok_or(-2)?;
        if worker.delivery.map(Token::wire) != Some(serial) { return Err(-16); }
        let call = self.calls.iter_mut().flatten()
            .find(|call| call.delivery.serial().wire() == serial).ok_or(-2)?;
        if call.kernel || call.fork_parked || call.service || call.cancelled
            || call.credential_written || call.completion.is_some() { return Err(-16); }
        let request = call.delivery.request();
        call.delivery.check_return(worker.worker, request.cpu() as i64)?;
        if !credential_request(request) || request.arguments()[0] != physical
            || physical == 0 || physical % 4 != 0 || bytes.len() != 32
            || physical.checked_add(32).is_none() || physical % 4096 > 4096 - 32
        { return Err(-22); }
        copy(request, call.response.as_mut().ok_or(-71)?.memory_mut(), physical, bytes)?;
        // The closure returns only after all 32 stores and retained payload
        // claim; return/cancel and guest publication run under the same lock.
        call.credential_written = true;
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
        if call.kernel || call.fork_parked {
            return Err(-16);
        }
        // Both success and failure RET must wait for the exact descriptor
        // UserSlice COMMIT/ABORT. A failed callback can leave this pending;
        // retaining the original Response/group is mandatory for every value.
        if call.exec.as_ref().is_some_and(|exec|exec.pending()) {
            return Err(-16);
        }
        call.delivery.check_return(worker.worker, cpu)?;
        let request = call.delivery.request();
        #[cfg(m14_getcred_private_candidate)]
        if credential_request(request) && !call.credential_written {
            return Err(-16);
        }
        if value == 0 && request.number() == 186 && request.arguments()[4] != 0 {
            request.tid_buffer()?;
            if !call.transferred {
                return Err(-22);
            }
        }
        if value==0&&request.number()==59&&!call.exec.as_ref().ok_or(-22)?.complete(request)?{return Err(-22);}
        // Only an already copied kernel buffer is used here, never user access.
        // Failed validation/copy leaves Delivered available for a proper retry.
        copy(call.delivery.request())?;
        call.delivery.begin_return(worker.worker, cpu)?;
        let response = call.response.take().ok_or(-71)?;
        match response.prepare_retained(worker.worker.tid(),value) {
            Ok(completion)=>call.completion=Some(completion),
            Err((response,error))=>{
                call.response=Some(response);self.quarantined=true;return Err(error);
            }
        }
        Ok(())
    }
fn cancel_call(call: &mut Call<M>) -> Result {
        if call.completion.is_some() {
            return Ok(());
        }
        // The guest ignores every do_syscall result. A negative cancellation
        // also wakes it, so retain the response rather than publish stale data.
        #[cfg(m14_getcred_private_candidate)]
        if credential_request(call.delivery.request()) && !call.credential_written {
            call.cancelled = true;
            return Err(-16);
        }
        if call.kernel || call.fork_parked || call.exec.as_ref().is_some_and(|e|e.pending()) {
            call.cancelled = true;
            return Ok(());
        }
        call.delivery.cancel()?;
        let response=call.response.take().ok_or(-71)?;
        match response.prepare_retained(0,-512) {
            Ok(completion)=>call.completion=Some(completion),
            Err((response,error))=>{
                // Keep the original claim/root/module owner in quarantine;
                // an unsuccessful response preparation never consumes it.
                call.response=Some(response);call.cancelled=true;return Err(error);
            }
        }
        call.cancelled=true;Ok(())
    }
}
impl FakeMemory {
pub(crate) fn copy_credentials(&mut self, request: &SyscallRequest, physical: u64,
        bytes: &mut [u8]) -> Result {
        if request.number() != 122 || request.arguments()[1] != 1
            || request.arguments()[0] != physical || physical == 0
            || physical % 4 != 0 || physical % 4096 > 4096 - 32 || bytes.len() != 32
            || physical.checked_add(32).is_none() { return Err(EINVAL); }
        // One-page range remains within one original page-aligned PageOwner;
        // the retained Memory owner and ledger also cover its entire extent.
        self.prepare_payload(physical, 32, true)?;
        self.pager_copy(0, bytes, true)
    }
}
