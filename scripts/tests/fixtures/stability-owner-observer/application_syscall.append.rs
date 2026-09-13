// VERIFICATION OVERLAY ONLY: copied host metadata; never memory.address().
#[allow(dead_code)]
impl Delivery {
    pub(crate) fn verification_delivery(&self) -> crate::stability_observer::Delivery {
        use crate::stability_observer as observer;
        let (phase, worker) = match self.phase {
            Phase::Queued => ("queued", None),
            Phase::Copying(worker) => ("copying", Some((worker.wire(), worker.tid()))),
            Phase::Delivered(worker) => ("delivered", Some((worker.wire(), worker.tid()))),
            Phase::Returning(worker) => ("returning", Some((worker.wire(), worker.tid()))),
            Phase::Servicing => ("servicing", None),
            Phase::Cancelling => ("cancelling", None),
            Phase::Complete => ("complete", None),
        };
        observer::Delivery {
            serial: self.serial.wire(),
            phase,
            phase_worker: worker,
            pid: self.request.pid(),
            cpu: self.request.cpu(),
            requester: self.request.requester(),
            target: self.request.target(),
            number: self.request.number(),
            response: self.request.response(),
            arguments: self.request.arguments(),
        }
    }
}
impl<M: ResponseMemory> Response<M> {
    pub(crate) fn verification_owner(&self) -> Option<crate::stability_observer::Claim> {
        self.memory.verification_owner()
    }
}
impl<M: ResponseMemory> Completion<M> {
    pub(crate) fn verification_owner(&self) -> Option<crate::stability_observer::Claim> {
        self.response
            .as_ref()
            .and_then(Response::verification_owner)
    }
    pub(crate) fn verification_state(&self) -> (bool, bool) {
        (self.response.is_some(), self.wake.is_some())
    }
}
