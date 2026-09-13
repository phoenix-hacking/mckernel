// SPDX-License-Identifier: GPL-2.0-only
// VERIFICATION OVERLAY ONLY: appended to mcctrl_process.rs, never production.
// Select one actual copied read16 delivery, then observe its real backend call.
// All fields belong to retained native host objects; no guest memory is read.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
struct StabilityRetKey {
    os: u32,
    generation: u64,
    pid: i32,
    tid: i32,
    worker: u64,
    delivery: u64,
}
static STABILITY_RET_STATE: AtomicU64 = AtomicU64::new(0);
static STABILITY_RET_OS: AtomicU64 = AtomicU64::new(0);
static STABILITY_RET_GENERATION: AtomicU64 = AtomicU64::new(0);
static STABILITY_RET_PID: AtomicI32 = AtomicI32::new(0);
static STABILITY_RET_TID: AtomicI32 = AtomicI32::new(0);
static STABILITY_RET_WORKER: AtomicU64 = AtomicU64::new(0);
static STABILITY_RET_DELIVERY: AtomicU64 = AtomicU64::new(0);
static STABILITY_RET_ENTERED: AtomicBool = AtomicBool::new(false);
static STABILITY_RET_LEFT: AtomicBool = AtomicBool::new(false);

fn stability_ret_key(registration: &Registration, worker: &HostWorker, delivery: u64) -> StabilityRetKey {
    StabilityRetKey {
        os: registration.slot,
        generation: registration.generation,
        pid: registration.pid,
        // Metadata lookup failure makes the observation invalid; it must not
        // alter the production operation's original result or authority.
        tid: worker.identity.number().unwrap_or(-1),
        worker: worker.handle,
        delivery,
    }
}

fn stability_ret_select(key: StabilityRetKey) {
    if STABILITY_RET_STATE.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire).is_err() {
        return;
    }
    STABILITY_RET_OS.store(key.os as u64, Ordering::Relaxed);
    STABILITY_RET_GENERATION.store(key.generation, Ordering::Relaxed);
    STABILITY_RET_PID.store(key.pid, Ordering::Relaxed);
    STABILITY_RET_TID.store(key.tid, Ordering::Relaxed);
    STABILITY_RET_WORKER.store(key.worker, Ordering::Relaxed);
    STABILITY_RET_DELIVERY.store(key.delivery, Ordering::Relaxed);
    STABILITY_RET_STATE.store(2, Ordering::Release);
    kernel::pr_info!("STABILITY_RET_SELECTED version=1 key={:?} valid={} mono_ns={}\n",
        key, key.pid > 0 && key.tid > 0 && key.worker != 0 && key.delivery != 0,
        unsafe { bindings::ktime_get() });
}

fn stability_ret_matches(key: StabilityRetKey) -> bool {
    STABILITY_RET_STATE.load(Ordering::Acquire) == 2
        && key.os as u64 == STABILITY_RET_OS.load(Ordering::Relaxed)
        && key.generation == STABILITY_RET_GENERATION.load(Ordering::Relaxed)
        && key.pid == STABILITY_RET_PID.load(Ordering::Relaxed)
        && key.tid == STABILITY_RET_TID.load(Ordering::Relaxed)
        && key.worker == STABILITY_RET_WORKER.load(Ordering::Relaxed)
        && key.delivery == STABILITY_RET_DELIVERY.load(Ordering::Relaxed)
}

fn stability_ret_enter(key: StabilityRetKey, value: i64, cpu: i64) {
    if stability_ret_matches(key) {
        let duplicate = STABILITY_RET_ENTERED.swap(true, Ordering::AcqRel);
        // One duplicate record is already a hard evidence failure; leave the
        // first selected identity immutable throughout the fresh guest.
        if duplicate {
            STABILITY_RET_STATE.store(3, Ordering::Release);
        }
        kernel::pr_info!("STABILITY_RET_ENTER version=1 key={:?} value={} cpu={} duplicate={} mono_ns={}\n",
            key, value, cpu, duplicate, unsafe { bindings::ktime_get() });
    }
}

fn stability_ret_leave(key: StabilityRetKey, error: i32, accepted: u64) {
    if stability_ret_matches(key) {
        let duplicate = STABILITY_RET_LEFT.swap(true, Ordering::AcqRel);
        if duplicate {
            STABILITY_RET_STATE.store(3, Ordering::Release);
        }
        kernel::pr_info!("STABILITY_RET_LEAVE version=1 key={:?} errno={} accepted={} duplicate={} mono_ns={}\n",
            key, error, accepted, duplicate, unsafe { bindings::ktime_get() });
    }
}
