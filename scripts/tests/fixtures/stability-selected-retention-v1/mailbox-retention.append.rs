
// VERIFICATION ONLY, selected-retention-v1. The existing application slots lock
// serializes selection, cancellation, preparation, publication and release.
fn stability_retention_selected(owner: Option<crate::stability_observer::Claim>) -> bool {
    crate::stability_observer::selected()
        .is_some_and(|selected| stability_fault_owner_matches(owner, selected))
}

fn stability_retention_cancel(owner: Option<crate::stability_observer::Claim>) -> Result {
    if stability_retention_selected(owner) && !crate::stability_phase::retention_released() {
        // Existing callers quarantine the Mailbox/Entry and retain its Call,
        // Worker, Response/Completion and backing owners on this error.
        crate::stability_phase::invalid(-125);
        return Err(-71);
    }
    Ok(())
}

fn stability_retention_pre_publish(owner: Option<crate::stability_observer::Claim>) -> Result {
    use core::sync::atomic::Ordering;
    if !stability_retention_selected(owner) {
        return Ok(());
    }
    // This is the original gate/counter block, moved from the optional send
    // callback. It runs independently of cancelled/kernel/service and wake.
    match crate::stability_phase::before_selected_send() {
        crate::stability_phase::SendGate::Released => {},
        crate::stability_phase::SendGate::BeforeSnapshot => {
            STABILITY_FAULT_BARRIERS.fetch_add(1, Ordering::AcqRel);
            return Err(-11);
        }
        crate::stability_phase::SendGate::HostHold => return Err(-11),
    }
    Ok(())
}
