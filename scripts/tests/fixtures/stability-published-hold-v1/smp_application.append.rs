// VERIFICATION OVERLAY ONLY. No transport lock is acquired by these methods.
impl Remote {
    fn verification_status_locked(
        &self, slots: &[Option<Entry>], key: crate::stability_observer::Selection,
    ) -> Result<crate::stability_phase::Status> {
        if key.os != self.owner.slot() || key.generation != self.owner.generation() {
            return Err(EINVAL);
        }
        let original = slots.iter().flatten().find(|entry| entry.key().wire() == key.application);
        let completion = match original {
            Some(entry) => entry.syscalls.verification_phase_completion(key).map_err(errno)?,
            None => crate::stability_phase::CompletionStatus { present: false, publication_since: None },
        };
        Ok(crate::stability_phase::Status {
            transport_error: self.transport_error.load(Ordering::Acquire),
            applications: slots.iter().flatten().count(), original_application: original.is_some(),
            selected_completion: completion.present, publication_since: completion.publication_since,
        })
    }
    pub(crate) fn verification_phase_status(
        &self, key: crate::stability_observer::Selection,
    ) -> Result<crate::stability_phase::Status> {
        let slots = self.slots.lock();
        self.verification_status_locked(&slots, key)
    }
    fn verification_live_hold_locked(
        &self, slots: &[Option<Entry>], key: crate::stability_observer::Selection,
        service_error: &AtomicI32,
    ) -> Result<crate::stability_phase::Status> {
        let status = self.verification_status_locked(slots, key)?;
        // fail_service takes this same slots lock before publishing service_error.
        if service_error.load(Ordering::Acquire) != 0 || status.transport_error != 0
            || !status.original_application || !status.selected_completion { return Err(EIO); }
        let original = slots.iter().flatten().find(|entry| entry.key().wire() == key.application)
            .ok_or(EIO)?;
        // Match the original selection's local admission checks, independently
        // of the global transport error. No retiring app may authorize release.
        if original.closed || original.needs_cleanup || original.quarantined { return Err(EIO); }
        Ok(status)
    }
    /// None is legitimate: only the next ordinary advance initializes the timer.
    pub(crate) fn verification_begin_accepted_hold(
        &self, key: crate::stability_observer::Selection, service_error: &AtomicI32,
    ) -> Result<Option<u64>> {
        let slots = self.slots.lock();
        let status = self.verification_live_hold_locked(&slots, key, service_error)?;
        let Some(timer) = status.publication_since else { return Ok(None); };
        crate::stability_phase::begin_emitting(timer).map_err(errno)?;
        Ok(Some(timer))
    }
    /// Full observation completed without a production guard. Recheck before ready.
    pub(crate) fn verification_commit_accepted_hold(
        &self, key: crate::stability_observer::Selection, service_error: &AtomicI32,
        timer: u64, sequence: u64,
    ) -> Result {
        let slots = self.slots.lock();
        let status = self.verification_live_hold_locked(&slots, key, service_error)?;
        if status.publication_since != Some(timer) { return Err(errno(-116)); }
        crate::stability_phase::commit_held(sequence, timer).map_err(errno)
    }
    pub(crate) fn verification_held_status(
        &self, key: crate::stability_observer::Selection, service_error: &AtomicI32,
    ) -> Result {
        let slots = self.slots.lock();
        let status = self.verification_live_hold_locked(&slots, key, service_error)?;
        let timer = status.publication_since.ok_or(EAGAIN)?;
        if !crate::stability_phase::is_held() || crate::stability_phase::timer() != Some(timer) {
            return Err(EAGAIN);
        }
        crate::stability_phase::check_deadline(timer, false).map_err(errno)
    }
    /// Original publication holds transport -> slots; this path takes slots ONLY.
    /// The immutable delivery serial names the same Request; no guest-memory read.
    pub(crate) fn verification_release_accepted_hold(
        &self, key: crate::stability_observer::Selection, service_error: &AtomicI32,
    ) -> Result {
        let slots = self.slots.lock();
        let status = self.verification_live_hold_locked(&slots, key, service_error)?;
        let timer = status.publication_since.ok_or(EAGAIN)?;
        crate::stability_phase::commit_release(timer).map_err(errno)
    }
}
