// VERIFICATION OVERLAY ONLY. Full observations/logging never hold production guards.
impl Runtime {
    #[inline(never)]
    fn verification_phase_snapshot(&self, phase: crate::stability_observer::Phase) -> Result<u64> {
        let sequence = crate::stability_phase::snapshot_begin(phase).map_err(errno)?;
        let result = self.verification_observe(phase);
        super::super::smp_application_syscall::stability_fault_observe();
        crate::stability_phase::observe_hold(sequence);
        crate::stability_phase::snapshot_end(sequence, result.as_ref().err().map_or(0, |error| error.to_errno()));
        result.map(|()| sequence)
    }
    /// One end-pump invocation, on the selected Runtime's single Packets thread.
    #[inline(never)]
    fn verification_accepted_phase(&self) {
        use crate::{stability_observer as observer, stability_phase as phase};
        if !phase::accepted_pending() { return; }
        let Some(key) = observer::selected() else { return; };
        if key.os != self.owner.slot() || key.generation != self.owner.generation() { return; }
        let Ok(_permit) = phase::permit() else { return; };
        if !phase::accepted_pending() { return; }
        let result = (|| -> Result {
            let Some(timer) = self.application.verification_begin_accepted_hold(key, &self.error)?
                else { return Ok(()); };
            // EMITTING was installed under slots. Every subsequent selected retry
            // uses HOST_HOLD_CALLS, even if another caller is introduced later.
            let sequence = self.verification_phase_snapshot(observer::Phase::AcceptedReturn)?;
            self.application.verification_commit_accepted_hold(key, &self.error, timer, sequence)?;
            phase::observe_ready();
            Ok(())
        })();
        if let Err(error) = result {
            phase::invalid(error.to_errno());
            kernel::pr_err!("STABILITY_PHASE_INVALID version=1 phase=AcceptedReturn errno={} mono_ns={} publication_deadline_unchanged=true\n",
                error.to_errno(), phase::now_ns());
        }
        // Permit drops here. No host wait, sleep, or retained production guard.
    }
    #[inline(never)]
    fn verification_command_phase(&self, request: &crate::stability_phase::Request) -> Result<u64> {
        use crate::{stability_observer as observer, stability_phase as phase};
        let command = request.phase;
        if command == phase::QUERY { return Ok(0); }
        // Every dispatched release is one-shot, including a failed health/timer check.
        if command == phase::RELEASE_ACCEPTED {
            let begin = phase::now_ns();
            let result = (|| -> Result {
                phase::claim_release().map_err(errno)?;
                if request.accepted_sequence != phase::accepted_sequence() || !phase::is_held() {
                    return Err(errno(-116));
                }
                let key = observer::selected().ok_or(EAGAIN)?;
                self.application.verification_release_accepted_hold(key, &self.error)
            })();
            if let Err(error) = &result { phase::invalid(error.to_errno()); }
            phase::observe_release(request, begin, result.as_ref().err().map_or(0, |error| error.to_errno()));
            return result.map(|()| phase::accepted_sequence());
        }
        if phase::invalid_errno() != 0 { return Err(errno(phase::invalid_errno())); }
        if command == phase::SELECT_BLOCKED {
            return self.verification_phase_snapshot(observer::Phase::BlockedRead);
        }
        let key = observer::selected().ok_or(EAGAIN)?;
        if command == phase::ACCEPTED_STATUS {
            // Ordinary next-sequence polling may precede RET preparation. Do
            // not mistake a still-Delivered call for an invalid Completion.
            match phase::stage() {
                1 | 2 | 4 => return Err(EAGAIN),
                3 => return Err(errno(-116)),
                5 => {},
                _ => return Err(EIO),
            }
            self.application.verification_held_status(key, &self.error)?;
            return Ok(phase::accepted_sequence());
        }
        let status = self.application.verification_phase_status(key)?;
        let runtime_error = self.error.load(Ordering::Acquire);
        let observed = match command {
            phase::TERMINAL | phase::TERMINAL_PLUS_FIVE => {
                if phase::MODE != 2 || phase::stage() != 3 || runtime_error == 0 || status.transport_error == 0 {
                    return Err(EAGAIN);
                }
                if command == phase::TERMINAL_PLUS_FIVE {
                    let terminal = phase::terminal_ns();
                    if terminal == 0 || phase::now_ns().saturating_sub(terminal) < 5_000_000_000 { return Err(EAGAIN); }
                    observer::Phase::TerminalPlusFive
                } else { observer::Phase::Terminal }
            }
            phase::RECOVERY | phase::AFTER_EIGHT_HELLO => {
                if phase::MODE != 3 || runtime_error != 0 || status.transport_error != 0
                    || phase::stage() != 3 || status.original_application || status.applications != 0 {
                    return Err(EAGAIN);
                }
                if command == phase::AFTER_EIGHT_HELLO {
                    if !phase::recovery_seen() { return Err(EINVAL); }
                    observer::Phase::AfterEightHello
                } else { observer::Phase::Recovery }
            }
            _ => return Err(EINVAL),
        };
        let sequence = self.verification_phase_snapshot(observed)?;
        if command == phase::TERMINAL { phase::mark_terminal(); }
        if command == phase::RECOVERY { phase::mark_recovery(); }
        Ok(sequence)
    }
}
impl Started {
    pub(super) fn verification_phase_command(&self, request: &crate::stability_phase::Request) -> Result<u64> {
        self.runtime.verification_command_phase(request)
    }
}
