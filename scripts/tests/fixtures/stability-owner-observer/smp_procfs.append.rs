// VERIFICATION OVERLAY ONLY. No procfs namespace teardown or guest access.
#[allow(dead_code)]
impl Process {
    pub(crate) fn verification_process(&self) -> crate::stability_observer::Process {
        crate::stability_observer::Process {
            token: self.context.key.wire(),
            pid: self.context.pid,
            cpu: self.context.cpu,
            live: self.context.live.load(Ordering::Acquire),
            published: self.published.load(Ordering::Acquire),
            main_seen: self.main_seen.load(Ordering::Acquire),
            tids: self.tids.lock().len(),
        }
    }
}
