// VERIFICATION OVERLAY ONLY. Public helpers must be called without slots,
// transport, CPU/controller, pager or ledger guards held by the caller.
#[allow(dead_code)]
impl Remote {
    pub(crate) fn verification_select_read16(
        &self,
        pid: Option<i32>,
    ) -> Result<crate::stability_observer::Selection> {
        use crate::stability_observer as observer;
        if pid.is_some_and(|pid| pid <= 0) {
            return Err(EINVAL);
        }
        let slots = self.slots.lock();
        self.transport_health()?;
        let mut selected = None;
        for entry in slots.iter().flatten() {
            if entry.closed || entry.needs_cleanup || entry.quarantined {
                continue;
            }
            if let Some(candidate) = entry
                .syscalls
                .verification_read16(pid, entry.key().wire())
                .map_err(errno)?
            {
                if candidate.os != self.owner.slot()
                    || candidate.generation != self.owner.generation()
                {
                    return Err(EIO);
                }
                if selected.is_some() {
                    return Err(EBUSY);
                }
                selected = Some(candidate);
            }
        }
        observer::select(selected.ok_or(EAGAIN)?).map_err(errno)
    }

    #[inline(never)]
    pub(crate) fn verification_emit(&self, sequence: u64) -> bool {
        use crate::stability_observer as observer;
        let mut rows = observer::Rows::<observer::App, { observer::APPS }>::new();
        let health;
        let capacity;
        {
            let slots = self.slots.lock();
            health = self.transport_error.load(Ordering::Acquire);
            capacity = slots.len();
            for (index, entry) in slots
                .iter()
                .enumerate()
                .filter_map(|(index, entry)| entry.as_ref().map(|entry| (index, entry)))
            {
                rows.push(observer::App {
                    index,
                    token: entry.key().wire(),
                    pid: entry.cleanup.pid(),
                    owner_slot: entry.owner_slot,
                    prepare: entry
                        .prepare
                        .as_ref()
                        .map(|prepare| prepare.exchange.token().wire()),
                    schedule: entry.schedule.as_ref().map(|value| value.token().wire()),
                    retirement: entry.retirement.as_ref().map(|value| value.token().wire()),
                    retirement_after: entry.retirement_after,
                    procfs: entry
                        .procfs
                        .as_ref()
                        .map(|process| process.verification_process()),
                    scheduled: entry.scheduled,
                    needs_cleanup: entry.needs_cleanup,
                    closed: entry.closed,
                    quarantined: entry.quarantined,
                });
            }
        }
        kernel::pr_info!("STABILITY_OWNER_DOMAIN version={} sequence={} domain=applications os={} generation={} transport_error={} slots={} total={} emitted={} complete={} release_token={}\n",
            observer::VERSION, sequence, self.owner.slot(), self.owner.generation(), health,
            capacity, rows.total, rows.used, rows.complete(), self.release_token.wire());
        let mut complete = rows.complete();
        for (index, row) in rows.rows.iter().flatten().enumerate() {
            kernel::pr_info!(
                "STABILITY_OWNER_APP version={} sequence={} ordinal={} row={:?}\n",
                observer::VERSION,
                sequence,
                index,
                row
            );
            complete &= self.verification_emit_detail(sequence, row.token);
            complete &= self.verification_emit_mailbox(sequence, Some(row.token));
        }
        complete &= self.verification_emit_mailbox(sequence, None);
        // No slots guard remains when acquiring the pager registry.
        complete &= self.pagers.verification_emit(sequence);
        complete
    }

    #[inline(never)]
    fn verification_emit_detail(&self, sequence: u64, token: u64) -> bool {
        use crate::stability_observer as observer;
        let detail = {
            let slots = self.slots.lock();
            slots
                .iter()
                .flatten()
                .find(|entry| entry.key().wire() == token)
                .map(|entry| {
                    (
                        entry.cleanup.verification_rpc(),
                        entry
                            .prepare
                            .as_ref()
                            .map(|image| image.verification_image()),
                        entry
                            .schedule
                            .as_ref()
                            .map(|value| value.verification_rpc()),
                        entry
                            .retirement
                            .as_ref()
                            .map(|value| value.verification_rpc()),
                    )
                })
        };
        let Some((cleanup, prepare, schedule, retirement)) = detail else {
            kernel::pr_info!("STABILITY_OWNER_DETAIL version={} sequence={} application={} present=false complete=false\n",
                observer::VERSION, sequence, token);
            return false;
        };
        kernel::pr_info!(
            "STABILITY_OWNER_RPC version={} sequence={} application={} role=cleanup row={:?}\n",
            observer::VERSION,
            sequence,
            token,
            cleanup
        );
        kernel::pr_info!(
            "STABILITY_OWNER_IMAGE version={} sequence={} application={} row={:?}\n",
            observer::VERSION,
            sequence,
            token,
            prepare
        );
        kernel::pr_info!(
            "STABILITY_OWNER_RPC version={} sequence={} application={} role=schedule row={:?}\n",
            observer::VERSION,
            sequence,
            token,
            schedule
        );
        kernel::pr_info!(
            "STABILITY_OWNER_RPC version={} sequence={} application={} role=retirement row={:?}\n",
            observer::VERSION,
            sequence,
            token,
            retirement
        );
        true
    }

    #[inline(never)]
    fn verification_emit_mailbox(&self, sequence: u64, application: Option<u64>) -> bool {
        use crate::stability_observer as observer;
        let mut calls = observer::Rows::<observer::Call, { observer::CALLS }>::new();
        let mut workers = observer::Rows::<observer::Worker, { observer::WORKERS }>::new();
        let state = {
            let slots = self.slots.lock();
            match application {
                Some(token) => slots
                    .iter()
                    .flatten()
                    .find(|entry| entry.key().wire() == token)
                    .map(|entry| {
                        entry
                            .syscalls
                            .verification_mailbox(&mut calls, &mut workers)
                    }),
                None => Some(
                    self.releases
                        .lock()
                        .verification_mailbox(&mut calls, &mut workers),
                ),
            }
        };
        let claims_known = calls
            .rows
            .iter()
            .flatten()
            .all(|call| !(call.response || call.completion_response) || call.owner.is_some());
        let complete = state.is_some() && calls.complete() && workers.complete() && claims_known;
        kernel::pr_info!("STABILITY_OWNER_DOMAIN version={} sequence={} domain=mailbox application={:?} release_token={} state={:?} calls_total={} calls_emitted={} workers_total={} workers_emitted={} claims_known={} complete={}\n",
            observer::VERSION, sequence, application, self.release_token.wire(), state, calls.total,
            calls.used, workers.total, workers.used, claims_known, complete);
        for (index, call) in calls.rows.iter().flatten().enumerate() {
            // Two records keep each printk well below the native line limit.
            kernel::pr_info!("STABILITY_OWNER_DELIVERY version={} sequence={} application={:?} ordinal={} row={:?}\n",
                observer::VERSION, sequence, application, index, call.delivery);
            kernel::pr_info!("STABILITY_OWNER_CALL version={} sequence={} application={:?} ordinal={} slot={} owner={:?} response={} completion={} completion_response={} completion_wake={} worker={:?} cancelled={} kernel={} service={} transferred={} publication_since={:?}\n",
                observer::VERSION, sequence, application, index, call.index, call.owner, call.response,
                call.completion, call.completion_response, call.completion_wake, call.worker,
                call.cancelled, call.kernel, call.service, call.transferred, call.publication_since);
        }
        for (index, worker) in workers.rows.iter().flatten().enumerate() {
            kernel::pr_info!("STABILITY_OWNER_WORKER version={} sequence={} application={:?} ordinal={} row={:?}\n",
                observer::VERSION, sequence, application, index, worker);
        }
        complete
    }
}
