// VERIFICATION OVERLAY ONLY.
#[allow(dead_code)]
impl Exchange {
    pub(crate) fn verification_rpc(&self) -> crate::stability_observer::Rpc {
        crate::stability_observer::Rpc {
            token: self.token.wire(),
            os: self.os,
            cpu: self.cpu,
            pid: self.pid,
            message: self.message,
            reply: self.reply,
            argument: self.argument,
            phase: match self.phase {
                Phase::Reserved => "reserved",
                Phase::Queued => "queued",
                Phase::Published => "published",
                Phase::Complete(_) => "complete",
            },
            result: self.result(),
            waiter: self.waiter,
            unscheduled_deleted: self.unscheduled_deleted,
            retirement_query: self.retirement_query,
        }
    }
}
