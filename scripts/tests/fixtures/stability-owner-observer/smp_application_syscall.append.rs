// VERIFICATION OVERLAY ONLY. The caller holds this mailbox's existing owner lock.
impl<M: ResponseMemory> Mailbox<M> {
    pub(crate) fn verification_read16(
        &self,
        pid: Option<i32>,
        application: u64,
    ) -> Result<Option<crate::stability_observer::Selection>> {
        use crate::stability_observer as observer;
        if self.closed || self.quarantined {
            return Err(-71);
        }
        let mut selected = None;
        for call in self.calls.iter().flatten() {
            let delivery = call.delivery.verification_delivery();
            if delivery.phase != "delivered"
                || call.cancelled
                || call.kernel
                || call.service
                || call.completion.is_some()
                || delivery.number != 0
                || delivery.arguments[0] != 0
                || delivery.arguments[2] != 16
                || pid.is_some_and(|pid| pid != delivery.pid)
            {
                continue;
            }
            let claim = call
                .response
                .as_ref()
                .and_then(Response::verification_owner)
                .ok_or(-95)?;
            let worker = call.worker.ok_or(-71)?;
            if claim.response.physical != delivery.response
                || claim.response.serial.is_none()
                || claim.response.end.checked_sub(claim.response.physical) != Some(40)
            {
                return Err(-71);
            }
            if selected.is_some() {
                return Err(-16);
            }
            selected = Some(observer::Selection {
                os: claim.os,
                generation: claim.generation,
                pid: delivery.pid,
                cpu: delivery.cpu,
                requester: delivery.requester,
                application,
                worker: worker.wire(),
                delivery: delivery.serial,
                ledger_serial: claim.response.serial.unwrap(),
                ledger_index: claim.response.index,
                response: claim.response.physical,
                response_end: claim.response.end,
            });
        }
        Ok(selected)
    }

    pub(crate) fn verification_mailbox(
        &self,
        calls: &mut crate::stability_observer::Rows<
            crate::stability_observer::Call,
            { crate::stability_observer::CALLS },
        >,
        workers: &mut crate::stability_observer::Rows<
            crate::stability_observer::Worker,
            { crate::stability_observer::WORKERS },
        >,
    ) -> crate::stability_observer::Mailbox {
        use crate::stability_observer as observer;
        for (index, call) in self
            .calls
            .iter()
            .enumerate()
            .filter_map(|(index, call)| call.as_ref().map(|call| (index, call)))
        {
            let (completion_response, completion_wake) = call
                .completion
                .as_ref()
                .map(Completion::verification_state)
                .unwrap_or((false, false));
            let owner = match call.response.as_ref() {
                Some(response) => response.verification_owner(),
                None => call
                    .completion
                    .as_ref()
                    .and_then(Completion::verification_owner),
            };
            calls.push(observer::Call {
                index,
                delivery: call.delivery.verification_delivery(),
                response: call.response.is_some(),
                completion: call.completion.is_some(),
                completion_response,
                completion_wake,
                owner,
                worker: call.worker.map(|worker| (worker.wire(), worker.tid())),
                cancelled: call.cancelled,
                kernel: call.kernel,
                service: call.service,
                transferred: call.transferred,
                publication_since: call.publication_since,
            });
        }
        for (index, worker) in self
            .workers
            .iter()
            .enumerate()
            .filter_map(|(index, worker)| worker.as_ref().map(|worker| (index, worker)))
        {
            workers.push(observer::Worker {
                index,
                handle: worker.worker.wire(),
                tid: worker.worker.tid(),
                delivery: worker.delivery.map(Token::wire),
                completed: worker.completed.map(Token::wire),
            });
        }
        observer::Mailbox {
            call_slots: self.calls.len(),
            worker_slots: self.workers.len(),
            closed: self.closed,
            quarantined: self.quarantined,
            completion_cursor: self.completion_cursor,
        }
    }
}
