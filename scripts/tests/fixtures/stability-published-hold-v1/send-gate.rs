    match crate::stability_phase::before_selected_send() {
        crate::stability_phase::SendGate::Released => {},
        crate::stability_phase::SendGate::BeforeSnapshot => {
            STABILITY_FAULT_BARRIERS.fetch_add(1, Ordering::AcqRel);
            return Err(-11);
        }
        crate::stability_phase::SendGate::HostHold => return Err(-11),
    }
