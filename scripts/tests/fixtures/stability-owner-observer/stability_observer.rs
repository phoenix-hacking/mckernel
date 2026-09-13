// SPDX-License-Identifier: GPL-2.0-only
//! VERIFICATION OVERLAY ONLY. Host-owned metadata; no peer memory reads.
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering};

pub(crate) const VERSION: u32 = 1;
pub(crate) const APPS: usize = 8;
pub(crate) const CALLS: usize = 8;
pub(crate) const WORKERS: usize = 16;
pub(crate) const TAGS: usize = 16;
pub(crate) const PAGERS: usize = 16;

pub(crate) struct Rows<T: Copy, const N: usize> {
    pub(crate) rows: [Option<T>; N],
    pub(crate) total: usize,
    pub(crate) used: usize,
}
impl<T: Copy, const N: usize> Rows<T, N> {
    pub(crate) const fn new() -> Self {
        Self {
            rows: [None; N],
            total: 0,
            used: 0,
        }
    }
    pub(crate) fn push(&mut self, row: T) {
        self.total += 1;
        if self.used < N {
            self.rows[self.used] = Some(row);
            self.used += 1;
        }
    }
    pub(crate) fn complete(&self) -> bool {
        self.total == self.used
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Tag {
    pub(crate) index: usize,
    pub(crate) serial: Option<u64>,
    pub(crate) physical: u64,
    pub(crate) end: u64,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Claim {
    pub(crate) os: u32,
    pub(crate) generation: u64,
    pub(crate) response: Tag,
    pub(crate) payload: Option<Tag>,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Delivery {
    pub(crate) serial: u64,
    pub(crate) phase: &'static str,
    pub(crate) phase_worker: Option<(u64, i32)>,
    pub(crate) pid: i32,
    pub(crate) cpu: i32,
    pub(crate) requester: i32,
    pub(crate) target: i32,
    pub(crate) number: u64,
    pub(crate) response: u64,
    pub(crate) arguments: [u64; 6],
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Call {
    pub(crate) index: usize,
    pub(crate) delivery: Delivery,
    pub(crate) response: bool,
    pub(crate) completion: bool,
    pub(crate) completion_response: bool,
    pub(crate) completion_wake: bool,
    pub(crate) owner: Option<Claim>,
    pub(crate) worker: Option<(u64, i32)>,
    pub(crate) cancelled: bool,
    pub(crate) kernel: bool,
    pub(crate) service: bool,
    pub(crate) transferred: bool,
    pub(crate) publication_since: Option<u64>,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Worker {
    pub(crate) index: usize,
    pub(crate) handle: u64,
    pub(crate) tid: i32,
    pub(crate) delivery: Option<u64>,
    pub(crate) completed: Option<u64>,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Mailbox {
    pub(crate) call_slots: usize,
    pub(crate) worker_slots: usize,
    pub(crate) closed: bool,
    pub(crate) quarantined: bool,
    pub(crate) completion_cursor: usize,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Rpc {
    pub(crate) token: u64,
    pub(crate) os: i32,
    pub(crate) cpu: i32,
    pub(crate) pid: i32,
    pub(crate) message: i32,
    pub(crate) reply: i32,
    pub(crate) argument: u64,
    pub(crate) phase: &'static str,
    pub(crate) result: Option<i32>,
    pub(crate) waiter: bool,
    pub(crate) unscheduled_deleted: bool,
    pub(crate) retirement_query: bool,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Process {
    pub(crate) token: u64,
    pub(crate) pid: i32,
    pub(crate) cpu: i32,
    pub(crate) live: bool,
    pub(crate) published: bool,
    pub(crate) main_seen: bool,
    pub(crate) tids: usize,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct App {
    pub(crate) index: usize,
    pub(crate) token: u64,
    pub(crate) pid: i32,
    pub(crate) owner_slot: i32,
    pub(crate) prepare: Option<u64>,
    pub(crate) schedule: Option<u64>,
    pub(crate) retirement: Option<u64>,
    pub(crate) retirement_after: u64,
    pub(crate) procfs: Option<Process>,
    pub(crate) scheduled: bool,
    pub(crate) needs_cleanup: bool,
    pub(crate) closed: bool,
    pub(crate) quarantined: bool,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Image {
    pub(crate) exchange: Rpc,
    pub(crate) result: Option<i32>,
    pub(crate) thread: u64,
    pub(crate) page_table: u64,
    pub(crate) buffers_retained: bool,
    pub(crate) descriptor: Option<u64>,
    pub(crate) args: Option<u64>,
    pub(crate) envs: Option<u64>,
}
#[derive(Clone, Copy, Debug)]
pub(crate) struct Pager {
    pub(crate) index: usize,
    pub(crate) token: u64,
    pub(crate) references: u64,
    pub(crate) readable_owner: usize,
    pub(crate) writable_owner: Option<usize>,
}
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) struct Selection {
    pub(crate) os: u32,
    pub(crate) generation: u64,
    pub(crate) pid: i32,
    pub(crate) cpu: i32,
    pub(crate) requester: i32,
    pub(crate) application: u64,
    pub(crate) worker: u64,
    pub(crate) delivery: u64,
    pub(crate) ledger_serial: u64,
    pub(crate) ledger_index: usize,
    pub(crate) response: u64,
    pub(crate) response_end: u64,
}
#[derive(Clone, Copy, Debug)]
pub(crate) enum Phase {
    BlockedRead,
    AcceptedReturn,
    Terminal,
    TerminalPlusFive,
    Recovery,
    AfterEightHello,
}

// One selection per fresh verification module/guest. No reset or reuse path.
static STATE: AtomicU64 = AtomicU64::new(0);
static OS: AtomicU64 = AtomicU64::new(0);
static GENERATION: AtomicU64 = AtomicU64::new(0);
static PID: AtomicI32 = AtomicI32::new(0);
static CPU: AtomicI32 = AtomicI32::new(0);
static REQUESTER: AtomicI32 = AtomicI32::new(0);
static APPLICATION: AtomicU64 = AtomicU64::new(0);
static WORKER: AtomicU64 = AtomicU64::new(0);
static DELIVERY: AtomicU64 = AtomicU64::new(0);
static SERIAL: AtomicU64 = AtomicU64::new(0);
static INDEX: AtomicU64 = AtomicU64::new(0);
static RESPONSE: AtomicU64 = AtomicU64::new(0);
static RESPONSE_END: AtomicU64 = AtomicU64::new(0);
static NEXT_SNAPSHOT: AtomicU64 = AtomicU64::new(1);
static ADDRESS_CALLS: AtomicU64 = AtomicU64::new(0);
static PAYLOAD_CALLS: AtomicU64 = AtomicU64::new(0);
static PAYLOAD_BYTES: AtomicU64 = AtomicU64::new(0);
static RELEASE_CALLS: AtomicU64 = AtomicU64::new(0);
static RELEASED: AtomicBool = AtomicBool::new(false);
static AFTER_RELEASE: AtomicU64 = AtomicU64::new(0);
static DUPLICATE_RELEASE: AtomicU64 = AtomicU64::new(0);

pub(crate) fn selected() -> Option<Selection> {
    if STATE.load(Ordering::Acquire) != 2 {
        return None;
    }
    Some(Selection {
        os: OS.load(Ordering::Relaxed) as u32,
        generation: GENERATION.load(Ordering::Relaxed),
        pid: PID.load(Ordering::Relaxed),
        cpu: CPU.load(Ordering::Relaxed),
        requester: REQUESTER.load(Ordering::Relaxed),
        application: APPLICATION.load(Ordering::Relaxed),
        worker: WORKER.load(Ordering::Relaxed),
        delivery: DELIVERY.load(Ordering::Relaxed),
        ledger_serial: SERIAL.load(Ordering::Relaxed),
        ledger_index: INDEX.load(Ordering::Relaxed) as usize,
        response: RESPONSE.load(Ordering::Relaxed),
        response_end: RESPONSE_END.load(Ordering::Relaxed),
    })
}
pub(crate) fn select(value: Selection) -> core::result::Result<Selection, i32> {
    match STATE.compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire) {
        Ok(_) => {
            OS.store(value.os as u64, Ordering::Relaxed);
            GENERATION.store(value.generation, Ordering::Relaxed);
            PID.store(value.pid, Ordering::Relaxed);
            CPU.store(value.cpu, Ordering::Relaxed);
            REQUESTER.store(value.requester, Ordering::Relaxed);
            APPLICATION.store(value.application, Ordering::Relaxed);
            WORKER.store(value.worker, Ordering::Relaxed);
            DELIVERY.store(value.delivery, Ordering::Relaxed);
            SERIAL.store(value.ledger_serial, Ordering::Relaxed);
            INDEX.store(value.ledger_index as u64, Ordering::Relaxed);
            RESPONSE.store(value.response, Ordering::Relaxed);
            RESPONSE_END.store(value.response_end, Ordering::Relaxed);
            STATE.store(2, Ordering::Release);
            Ok(value)
        }
        Err(1) => Err(-11),
        Err(_) => selected().filter(|old| *old == value).ok_or(-16),
    }
}
fn matches(claim: Claim) -> bool {
    selected().is_some_and(|key| {
        key.os == claim.os
            && key.generation == claim.generation
            && Some(key.ledger_serial) == claim.response.serial
            && key.ledger_index == claim.response.index
            && key.response == claim.response.physical
            && key.response_end == claim.response.end
    })
}
pub(crate) fn address(claim: Claim) {
    if matches(claim) {
        ADDRESS_CALLS.fetch_add(1, Ordering::AcqRel);
        if RELEASED.load(Ordering::Acquire) {
            AFTER_RELEASE.fetch_add(1, Ordering::AcqRel);
        }
    }
}
pub(crate) fn payload(claim: Claim, bytes: usize) {
    if matches(claim) {
        PAYLOAD_CALLS.fetch_add(1, Ordering::AcqRel);
        PAYLOAD_BYTES.fetch_add(bytes as u64, Ordering::AcqRel);
        if RELEASED.load(Ordering::Acquire) {
            AFTER_RELEASE.fetch_add(1, Ordering::AcqRel);
        }
    }
}
pub(crate) fn release(claim: Claim) {
    if matches(claim) {
        RELEASE_CALLS.fetch_add(1, Ordering::AcqRel);
        if RELEASED.swap(true, Ordering::AcqRel) {
            DUPLICATE_RELEASE.fetch_add(1, Ordering::AcqRel);
        }
    }
}
pub(crate) fn begin(phase: Phase, selection: Selection) -> core::result::Result<u64, i32> {
    let sequence = NEXT_SNAPSHOT
        .fetch_update(Ordering::AcqRel, Ordering::Acquire, |old| {
            old.checked_add(1)
        })
        .map_err(|_| -75)?;
    kernel::pr_info!("STABILITY_OWNER_BEGIN version={} sequence={} phase={:?} selection={:?} sampling=independent_domains\n",
        VERSION, sequence, phase, selection);
    Ok(sequence)
}
pub(crate) fn end(sequence: u64, complete: bool) -> bool {
    let after_release = AFTER_RELEASE.load(Ordering::Acquire);
    let duplicate_release = DUPLICATE_RELEASE.load(Ordering::Acquire);
    let counters_valid = after_release == 0 && duplicate_release == 0;
    kernel::pr_info!("STABILITY_OWNER_COUNTERS version={} sequence={} selected_ledger_serial={:?} address_calls={} payload_calls={} payload_bytes={} release_calls={} released={} after_release_calls={} duplicate_release={} sampling=independent_atomics\n",
        VERSION, sequence, selected().map(|key| key.ledger_serial), ADDRESS_CALLS.load(Ordering::Acquire),
        PAYLOAD_CALLS.load(Ordering::Acquire), PAYLOAD_BYTES.load(Ordering::Acquire), RELEASE_CALLS.load(Ordering::Acquire),
        RELEASED.load(Ordering::Acquire), after_release, duplicate_release);
    kernel::pr_info!(
        "STABILITY_OWNER_END version={} sequence={} complete={} counters_valid={} result={}\n",
        VERSION,
        sequence,
        complete,
        counters_valid,
        if !complete {
            "INCOMPLETE_FAIL"
        } else if !counters_valid {
            "COUNTER_FAIL"
        } else {
            "COMPLETE_SNAPSHOT"
        }
    );
    complete && counters_valid
}
const _: () = {
    assert!(core::mem::size_of::<Rows<Call, CALLS>>() <= 4096);
    assert!(core::mem::size_of::<Rows<Worker, WORKERS>>() <= 1024);
    assert!(core::mem::size_of::<Rows<App, APPS>>() <= 2048);
    assert!(core::mem::size_of::<Rows<Tag, TAGS>>() <= 1024);
    assert!(core::mem::size_of::<Rows<Pager, PAGERS>>() <= 1024);
};
