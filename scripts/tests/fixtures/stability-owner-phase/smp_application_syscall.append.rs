// VERIFICATION OVERLAY ONLY. Caller owns the existing mailbox lock.
impl<M: ResponseMemory> Mailbox<M> {
    pub(crate) fn verification_phase_completion(
        &self,
        key: crate::stability_observer::Selection,
    ) -> Result<bool> {
        let Some(call) = self.calls.iter().flatten()
            .find(|call| call.delivery.serial().wire() == key.delivery) else { return Ok(false); };
        let delivery = call.delivery.verification_delivery();
        if delivery.pid != key.pid
            || delivery.cpu != key.cpu
            || delivery.requester != key.requester
            || delivery.response != key.response
            || delivery.number != 0
            || delivery.arguments[0] != 0
            || delivery.arguments[2] != 16
            || call.worker.map(|worker| worker.wire()) != Some(key.worker)
        {
            return Err(-71);
        }
        let Some(completion) = call.completion.as_ref() else { return Ok(false); };
        let claim = completion.verification_owner().ok_or(-71)?;
        if call.cancelled
            || call.kernel
            || call.service
            || call.response.is_some()
            || delivery.phase != "returning"
            || completion.verification_state() != (true, true)
            || claim.os != key.os
            || claim.generation != key.generation
            || claim.response.serial != Some(key.ledger_serial)
            || claim.response.index != key.ledger_index
            || claim.response.physical != key.response
            || claim.response.end != key.response_end
        {
            return Err(-71);
        }
        Ok(true)
    }
}
