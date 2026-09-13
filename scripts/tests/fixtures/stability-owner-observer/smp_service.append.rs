// VERIFICATION OVERLAY ONLY. Root wires calls at externally supervised phases.
#[allow(dead_code)]
impl Runtime {
    pub(super) fn verification_select_read16(
        &self,
        pid: Option<i32>,
    ) -> Result<crate::stability_observer::Selection> {
        self.application.verification_select_read16(pid)
    }

    #[inline(never)]
    pub(super) fn verification_observe(&self, phase: crate::stability_observer::Phase) -> Result {
        use crate::stability_observer as observer;
        let selection = observer::selected().ok_or(EAGAIN)?;
        if selection.os != self.owner.slot() || selection.generation != self.owner.generation() {
            return Err(EINVAL);
        }
        let sequence = observer::begin(phase, selection).map_err(errno)?;
        // Each short scope ends before a later domain lock or printk begins.
        let metadata_pending = { self.pending.lock().length };
        let procfs_pending = { self.procfs_pending.lock().len() };
        let zero_pending = { self.zero_pending.lock().len() };
        kernel::pr_info!("STABILITY_OWNER_RUNTIME version={} sequence={} os={} generation={} runtime_owner={:x} runtime_error={} metadata_pending={} procfs_pending={} zero_pending={} completed={} rejected={} zeroed={}\n",
            observer::VERSION, sequence, self.owner.slot(), self.owner.generation(), self as *const Self as usize,
            self.error.load(Ordering::Acquire), metadata_pending, procfs_pending, zero_pending,
            self.completed.load(Ordering::Acquire), self.rejected.load(Ordering::Acquire), self.zeroed.load(Ordering::Acquire));
        let mut complete = self.application.verification_emit(sequence);
        // The application and pager guards ended before the memory ledger.
        complete &= self.memory.verification_emit_ledger(sequence);
        if observer::end(sequence, complete) {
            Ok(())
        } else {
            Err(errno(-75))
        }
    }
}
#[allow(dead_code)]
impl Started {
    pub(super) fn verification_select_read16(
        &self,
        pid: Option<i32>,
    ) -> Result<crate::stability_observer::Selection> {
        self.runtime.verification_select_read16(pid)
    }
    pub(super) fn verification_observe(&self, phase: crate::stability_observer::Phase) -> Result {
        self.runtime.verification_observe(phase)
    }
}
