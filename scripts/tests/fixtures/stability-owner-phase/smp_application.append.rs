// VERIFICATION OVERLAY ONLY. No external lock may span this call.
impl Remote {
    pub(crate) fn verification_phase_status(
        &self,
        key: crate::stability_observer::Selection,
    ) -> Result<crate::stability_phase::Status> {
        if key.os != self.owner.slot() || key.generation != self.owner.generation() {
            return Err(EINVAL);
        }
        let slots = self.slots.lock();
        let original = slots
            .iter()
            .flatten()
            .find(|entry| entry.key().wire() == key.application);
        let selected_completion = match original {
            Some(entry) => entry
                .syscalls
                .verification_phase_completion(key)
                .map_err(errno)?,
            None => false,
        };
        Ok(crate::stability_phase::Status {
            transport_error: self.transport_error.load(Ordering::Acquire),
            applications: slots.iter().flatten().count(),
            original_application: original.is_some(),
            selected_completion,
        })
    }
}
