// SPDX-License-Identifier: GPL-2.0-only
// VERIFICATION OVERLAY ONLY: appended to smp_application_syscall.rs.
// @MODE@ is replaced with the frozen mode 1..4 by the isolated stager.
const STABILITY_FAULT_MODE: u32 = @MODE@;
static STABILITY_FAULT_ATTEMPTS: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);
static STABILITY_FAULT_BARRIERS: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);
static STABILITY_FAULT_SINCE: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);
static STABILITY_FAULT_PUBLISHED: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);
static STABILITY_FAULT_NOTIFICATION: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);
static STABILITY_FAULT_REAL_SENDS: core::sync::atomic::AtomicU64 = core::sync::atomic::AtomicU64::new(0);

fn stability_fault_publish(packet: &[u8; 128], send: impl FnOnce(&[u8; 128]) -> Result) -> Result {
    use core::sync::atomic::Ordering;
    let attempt = STABILITY_FAULT_REAL_SENDS.fetch_update(Ordering::AcqRel, Ordering::Acquire,
        |old| Some(old.saturating_add(1))).unwrap().saturating_add(1);
    if attempt > 32 {
        crate::stability_phase::invalid(-75);
    }
    let begin = unsafe { kernel::bindings::ktime_get() };
    let result = send(packet);
    let end = unsafe { kernel::bindings::ktime_get() };
    if result.is_ok() {
        STABILITY_FAULT_PUBLISHED.store(1, Ordering::Release);
    }
    if attempt <= 32 {
        kernel::pr_info!("STABILITY_FAULT_REAL_SEND version=1 mode={} attempt={} errno={} begin_ns={} end_ns={}\n",
            STABILITY_FAULT_MODE, attempt, result.as_ref().map_or_else(|error| *error, |_| 0), begin, end);
    }
    result
}

fn stability_fault_owner_matches(owner: Option<crate::stability_observer::Claim>, selected: crate::stability_observer::Selection) -> bool {
    owner.is_some_and(|claim| claim.os == selected.os && claim.generation == selected.generation
        && claim.response.serial == Some(selected.ledger_serial)
        && claim.response.index == selected.ledger_index
        && claim.response.physical == selected.response && claim.response.end == selected.response_end)
}

fn stability_fault_accepted(request: &Request, delivery: u64, eligible: bool, owner: Option<crate::stability_observer::Claim>) {
    let Some(selected) = crate::stability_observer::selected() else { return; };
    let args = request.arguments();
    if stability_fault_owner_matches(owner, selected) && eligible && request.number() == 0 && args[0] == 0 && args[2] == 16
        && request.pid() == selected.pid && request.cpu() == selected.cpu
        && request.requester() == selected.requester && delivery == selected.delivery
        && request.response() == selected.response
    {
        crate::stability_phase::accepted_selected();
    }
}

fn stability_fault_send(
    request: &Request,
    delivery: u64,
    eligible: bool,
    owner: Option<crate::stability_observer::Claim>,
    packet: &[u8; 128],
    send: impl FnOnce(&[u8; 128]) -> Result,
) -> Result {
    use core::sync::atomic::Ordering;
    let Some(selected) = crate::stability_observer::selected() else {
        return send(packet);
    };
    let args = request.arguments();
    if !stability_fault_owner_matches(owner, selected) || !eligible || request.number() != 0 || args[0] != 0 || args[2] != 16
        || request.pid() != selected.pid || request.cpu() != selected.cpu
        || request.requester() != selected.requester || delivery != selected.delivery
        || request.response() != selected.response
    {
        return send(packet);
    }
    // The initial selected key was bound to real OS-generation/ledger/worker
    // owners while this request was Delivered. The selection never resets.
    // A scalar-only barrier can defer publication until the unlocked pump has
    // emitted AcceptedReturn. It never resets the production completion clock.
    if let Err(error) = crate::stability_phase::before_selected_send() {
        STABILITY_FAULT_BARRIERS.fetch_add(1, Ordering::AcqRel);
        return Err(error);
    }
    if STABILITY_FAULT_PUBLISHED.load(Ordering::Acquire) != 0 {
        kernel::pr_info!("STABILITY_FAULT_INVALID version=1 reason=duplicate_selected_send\n");
        return Err(-71);
    }
    let now = unsafe { kernel::bindings::ktime_get() };
    if now <= 0 { return Err(-71); }
    let now = now as u64;
    let old = STABILITY_FAULT_ATTEMPTS.fetch_update(Ordering::AcqRel, Ordering::Acquire,
        |old| old.checked_add(1)).map_err(|_| -75)?;
    if old == 0 {
        STABILITY_FAULT_SINCE.store(now, Ordering::Release);
        kernel::pr_info!("STABILITY_FAULT_SELECTED version=1 mode={} selection={:?} buffer={:x} bytes=16 mono_ns={}\n",
            STABILITY_FAULT_MODE, selected, args[1], now);
    }
    match STABILITY_FAULT_MODE {
        1 => {
            kernel::pr_info!("STABILITY_FAULT_PREPUBLICATION version=1 errno=-5 attempts={} mono_ns={}\n", old + 1, now);
            Err(-5)
        }
        2 => {
            // This is the real unchanged ControlChannel::publish callback.
            stability_fault_publish(packet, send)?;
            kernel::pr_info!("STABILITY_FAULT_PUBLISHED version=1 mode=2 attempts={} mono_ns={}\n", old + 1, unsafe { kernel::bindings::ktime_get() });
            Ok(())
        }
        3 if now.saturating_sub(STABILITY_FAULT_SINCE.load(Ordering::Acquire)) >= 2_000_000_000 => {
            stability_fault_publish(packet, send)?;
            kernel::pr_info!("STABILITY_FAULT_RECOVERED version=1 mode=3 attempts={} mono_ns={}\n", old + 1, unsafe { kernel::bindings::ktime_get() });
            Ok(())
        }
        3 | 4 => Err(-11),
        _ => Err(-22),
    }
}

pub(crate) fn stability_fault_notify(os: u32, generation: u64, application: u64, cpu: i32, notify: impl FnOnce() -> Result) -> Result {
    use core::sync::atomic::Ordering;
    if STABILITY_FAULT_MODE == 2
        && crate::stability_observer::selected().is_some_and(|key| key.os == os && key.generation == generation && key.application == application && key.cpu == cpu)
        && STABILITY_FAULT_PUBLISHED.load(Ordering::Acquire) == 1
        && STABILITY_FAULT_NOTIFICATION.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire).is_ok()
    {
        kernel::pr_info!("STABILITY_FAULT_NOTIFICATION version=1 errno=-5 published=1 mono_ns={}\n", unsafe { kernel::bindings::ktime_get() });
        return Err(-5);
    }
    notify()
}

pub(crate) fn stability_fault_observe() {
    use core::sync::atomic::Ordering;
    kernel::pr_info!("STABILITY_FAULT_COUNTS version=1 mode={} attempts={} barrier_attempts={} published={} notification_failures={} real_sends={} since_ns={} mono_ns={}\n",
        STABILITY_FAULT_MODE, STABILITY_FAULT_ATTEMPTS.load(Ordering::Acquire),
        STABILITY_FAULT_BARRIERS.load(Ordering::Acquire), STABILITY_FAULT_PUBLISHED.load(Ordering::Acquire),
        STABILITY_FAULT_NOTIFICATION.load(Ordering::Acquire), STABILITY_FAULT_REAL_SENDS.load(Ordering::Acquire), STABILITY_FAULT_SINCE.load(Ordering::Acquire),
        unsafe { kernel::bindings::ktime_get() });
}
