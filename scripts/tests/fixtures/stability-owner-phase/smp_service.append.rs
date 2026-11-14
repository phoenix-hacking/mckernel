// VERIFICATION OVERLAY ONLY. All full observations run outside production guards.
impl Runtime {
    fn verification_phase_snapshot(&self, phase: crate::stability_observer::Phase) -> Result<u64> {
        let sequence = crate::stability_phase::snapshot_begin(phase).map_err(errno)?;
        let result = self.verification_observe(phase);
        super::super::smp_application_syscall::stability_fault_observe();
        crate::stability_phase::snapshot_end(
            sequence,
            result.as_ref().err().map_or(0, |error| error.to_errno()),
        );
        result.map(|()| sequence)
    }

    /// Root inserts exactly one call at end-pump, after all seven service calls.
    fn verification_accepted_phase(&self) {
        use crate::{stability_observer as observer, stability_phase as phase};
        if !phase::accepted_pending() {
            return;
        }
        let Some(selected) = observer::selected() else { return; };
        // Other OS packet workers must not claim or invalidate this global,
        // immutable selection. They keep pumping their own ordinary work.
        if selected.os != self.owner.slot() || selected.generation != self.owner.generation() {
            return;
        }
        let Ok(_permit) = phase::permit() else { return; };
        if !phase::accepted_pending() {
            return;
        }
        let result = (|| -> Result<u64> {
            let key = observer::selected().ok_or(EAGAIN)?;
            let status = self.application.verification_phase_status(key)?;
            if self.error.load(Ordering::Acquire) != 0
                || status.transport_error != 0
                || !status.selected_completion
            {
                return Err(EIO);
            }
            self.verification_phase_snapshot(observer::Phase::AcceptedReturn)
        })();
        match result {
            Ok(sequence) => phase::release_accepted(sequence),
            Err(error) => {
                phase::invalid(error.to_errno());
                kernel::pr_err!("STABILITY_PHASE_INVALID version=1 phase=AcceptedReturn errno={} mono_ns={} publication_deadline_unchanged=true\n",
                    error.to_errno(), phase::now_ns());
            }
        }
    }

    fn verification_command_phase(&self, command: u32) -> Result<u64> {
        use crate::{stability_observer as observer, stability_phase as phase};
        if command == phase::QUERY {
            return Ok(0);
        }
        if phase::invalid_errno() != 0 {
            return Err(errno(phase::invalid_errno()));
        }
        if command == phase::SELECT_BLOCKED {
            return self.verification_phase_snapshot(observer::Phase::BlockedRead);
        }
        let key = observer::selected().ok_or(EAGAIN)?;
        let status = self.application.verification_phase_status(key)?;
        let runtime_error = self.error.load(Ordering::Acquire);
        let observed = match command {
            phase::TERMINAL | phase::TERMINAL_PLUS_FIVE => {
                if runtime_error == 0 || status.transport_error == 0 {
                    return Err(EAGAIN);
                }
                if command == phase::TERMINAL_PLUS_FIVE {
                    let terminal = phase::terminal_ns();
                    if terminal == 0 || phase::now_ns().saturating_sub(terminal) < 5_000_000_000 {
                        return Err(EAGAIN);
                    }
                    observer::Phase::TerminalPlusFive
                } else {
                    observer::Phase::Terminal
                }
            }
            phase::RECOVERY | phase::AFTER_EIGHT_HELLO => {
                if runtime_error != 0
                    || status.transport_error != 0
                    || phase::stage() != 3
                    || status.original_application
                    || status.applications != 0
                {
                    return Err(EAGAIN);
                }
                if command == phase::AFTER_EIGHT_HELLO {
                    if !phase::recovery_seen() {
                        return Err(EINVAL);
                    }
                    // Actual eight-launch provenance is external evidence, not a label count.
                    observer::Phase::AfterEightHello
                } else {
                    observer::Phase::Recovery
                }
            }
            _ => return Err(EINVAL),
        };
        let sequence = self.verification_phase_snapshot(observed)?;
        if command == phase::TERMINAL {
            phase::mark_terminal();
        }
        if command == phase::RECOVERY {
            phase::mark_recovery();
        }
        Ok(sequence)
    }
}
impl Started {
    pub(super) fn verification_phase_command(&self, command: u32) -> Result<u64> {
        self.runtime.verification_command_phase(command)
    }
}
