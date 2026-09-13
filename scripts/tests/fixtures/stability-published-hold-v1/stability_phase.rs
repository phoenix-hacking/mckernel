// SPDX-License-Identifier: GPL-2.0-only
//! VERIFICATION ONLY: isolated published-mode profile, never a public ABI.
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering};

pub(crate) const COMMAND: u32 = 0xc100_f502;
pub(crate) const VERSION: u32 = 2;
pub(crate) const BYTES: usize = 256;
pub(crate) const MODE: u32 = @MODE@;
pub(crate) const SELECT_BLOCKED: u32 = 1;
pub(crate) const TERMINAL: u32 = 2;
pub(crate) const TERMINAL_PLUS_FIVE: u32 = 3;
pub(crate) const RECOVERY: u32 = 4;
pub(crate) const AFTER_EIGHT_HELLO: u32 = 5;
pub(crate) const QUERY: u32 = 6;
pub(crate) const ACCEPTED_STATUS: u32 = 7;
pub(crate) const RELEASE_ACCEPTED: u32 = 8;
const ARMED: u64 = 1;
const ACCEPTED_PENDING: u64 = 2;
const RELEASED: u64 = 3;
const EMITTING: u64 = 4;
const HELD_READY: u64 = 5;
// Evidence budget only. Overflow invalidates verification, never resets a timer.
pub(crate) const HOLD_LIMIT: u64 = 1_000_000;
static BUSY: AtomicBool = AtomicBool::new(false);
static STAGE: AtomicU64 = AtomicU64::new(0);
static NONCE_LOW: AtomicU64 = AtomicU64::new(0);
static NONCE_HIGH: AtomicU64 = AtomicU64::new(0);
static REQUEST_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static SNAPSHOT_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static ACCEPTED_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static BARRIER_CALLS: AtomicU64 = AtomicU64::new(0);
static HOST_HOLD_CALLS: AtomicU64 = AtomicU64::new(0);
static TIMER_SECONDS: AtomicU64 = AtomicU64::new(0);
static TIMER_PRESENT: AtomicBool = AtomicBool::new(false);
static HELD_NS: AtomicU64 = AtomicU64::new(0);
static RELEASE_ATTEMPTED: AtomicBool = AtomicBool::new(false);
static RELEASE_COMMITS: AtomicU64 = AtomicU64::new(0);
static INVALID: AtomicI32 = AtomicI32::new(0);
static TERMINAL_NS: AtomicU64 = AtomicU64::new(0);
static RECOVERY_SEEN: AtomicBool = AtomicBool::new(false);

pub(crate) struct Permit;
impl Drop for Permit {
    fn drop(&mut self) { BUSY.store(false, Ordering::Release); }
}
pub(crate) fn permit() -> Result<Permit, i32> {
    BUSY.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .map(|_| Permit).map_err(|_| -11)
}
pub(crate) fn now_ns() -> u64 {
    // SAFETY: Same pure monotonic clock as the original verification overlay.
    unsafe { kernel::bindings::ktime_get() as u64 }
}
pub(crate) fn invalid(error: i32) {
    let _ = INVALID.compare_exchange(0, if error < 0 { error } else { -71 },
        Ordering::AcqRel, Ordering::Acquire);
}
pub(crate) fn invalid_errno() -> i32 { INVALID.load(Ordering::Acquire) }
pub(crate) fn stage() -> u64 { STAGE.load(Ordering::Acquire) }
pub(crate) fn timer() -> Option<u64> {
    TIMER_PRESENT.load(Ordering::Acquire).then(|| TIMER_SECONDS.load(Ordering::Acquire))
}
pub(crate) fn accepted_sequence() -> u64 { ACCEPTED_SEQUENCE.load(Ordering::Acquire) }
pub(crate) fn deadline(timer: u64) -> Result<u64, i32> {
    timer.checked_add(5).and_then(|end| end.checked_mul(1_000_000_000)).ok_or(-75)
}
pub(crate) fn check_deadline(timer: u64, releasing: bool) -> Result<(), i32> {
    let now = now_ns();
    let reserve = if releasing && MODE == 3 { 2_000_000_000 } else { 0 };
    if now.checked_add(reserve).ok_or(-75)? >= deadline(timer)? { return Err(-110); }
    Ok(())
}

/// Matched actual Completion::prepare, while its existing slots lock is held.
pub(crate) fn accepted_selected() {
    if STAGE.compare_exchange(ARMED, ACCEPTED_PENDING, Ordering::AcqRel, Ordering::Acquire).is_err() {
        invalid(-71);
    }
}
pub(crate) enum SendGate { Released, BeforeSnapshot, HostHold }
/// Called under the same slots lock as begin_emitting/commit_release.
/// The original barrier count freezes BEFORE AcceptedReturn BEGIN and counts.
pub(crate) fn before_selected_send() -> SendGate {
    match stage() {
        RELEASED => SendGate::Released,
        ACCEPTED_PENDING => {
            if BARRIER_CALLS.fetch_update(Ordering::AcqRel, Ordering::Acquire,
                |old| old.checked_add(1)).is_err() { invalid(-75); }
            SendGate::BeforeSnapshot
        }
        value => {
            if value != EMITTING && value != HELD_READY { invalid(-71); }
            if HOST_HOLD_CALLS.fetch_update(Ordering::AcqRel, Ordering::Acquire,
                |old| if old < HOLD_LIMIT { Some(old + 1) } else { None }).is_err() { invalid(-75); }
            SendGate::HostHold
        }
    }
}
pub(crate) fn accepted_pending() -> bool { stage() == ACCEPTED_PENDING && invalid_errno() == 0 }
/// Permit + original slots lock held; caller copied Some(timer) from the call.
pub(crate) fn begin_emitting(original_timer: u64) -> Result<(), i32> {
    if invalid_errno() != 0 || timer().is_some() { return Err(-71); }
    check_deadline(original_timer, false)?;
    STAGE.compare_exchange(ACCEPTED_PENDING, EMITTING, Ordering::AcqRel, Ordering::Acquire)
        .map_err(|_| -71)?;
    TIMER_SECONDS.store(original_timer, Ordering::Relaxed);
    TIMER_PRESENT.store(true, Ordering::Release);
    Ok(())
}
/// Revalidated the same live Completion and timer under slots after full output.
pub(crate) fn commit_held(sequence: u64, original_timer: u64) -> Result<(), i32> {
    if sequence != 2 || accepted_sequence() != 0 || timer() != Some(original_timer)
        || invalid_errno() != 0 { return Err(-71); }
    check_deadline(original_timer, false)?;
    ACCEPTED_SEQUENCE.store(sequence, Ordering::Relaxed);
    HELD_NS.store(now_ns(), Ordering::Relaxed);
    STAGE.compare_exchange(EMITTING, HELD_READY, Ordering::AcqRel, Ordering::Acquire)
        .map_err(|_| -71)?;
    Ok(())
}
pub(crate) fn claim_release() -> Result<(), i32> {
    RELEASE_ATTEMPTED.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .map(|_| ()).map_err(|_| -116)
}
/// Permit + slots held, original claim/health/timer rechecked by Remote.
pub(crate) fn commit_release(original_timer: u64) -> Result<(), i32> {
    if !RELEASE_ATTEMPTED.load(Ordering::Acquire) || invalid_errno() != 0
        || timer() != Some(original_timer) || accepted_sequence() != 2
        || RELEASE_COMMITS.load(Ordering::Acquire) != 0 { return Err(-71); }
    check_deadline(original_timer, true)?;
    STAGE.compare_exchange(HELD_READY, RELEASED, Ordering::AcqRel, Ordering::Acquire)
        .map_err(|_| -116)?;
    // The selected sender cannot acquire slots until both scalar writes finish.
    RELEASE_COMMITS.store(1, Ordering::Release);
    Ok(())
}
pub(crate) fn is_held() -> bool { stage() == HELD_READY && invalid_errno() == 0 }

pub(crate) fn word(bytes: &[u8; BYTES], offset: usize) -> u64 {
    u64::from_le_bytes(bytes[offset..offset + 8].try_into().unwrap())
}
pub(crate) fn put(bytes: &mut [u8; BYTES], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}
fn small(bytes: &[u8; BYTES], offset: usize) -> u32 {
    u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap())
}
pub(crate) struct Request {
    pub(crate) phase: u32, pub(crate) os: u32, pub(crate) pid: i32,
    pub(crate) generation: u64, pub(crate) sequence: u64,
    pub(crate) nonce_low: u64, pub(crate) nonce_high: u64,
    pub(crate) delivery: u64, pub(crate) ledger_serial: u64,
    pub(crate) accepted_sequence: u64, pub(crate) uart_sequence: u64,
    pub(crate) ack: [u64; 4],
}
impl Request {
    pub(crate) fn read(bytes: &[u8; BYTES]) -> Result<Self, i32> {
        let request = Self { phase: small(bytes, 4), os: small(bytes, 8),
            pid: small(bytes, 12) as i32, generation: word(bytes, 16), sequence: word(bytes, 24),
            nonce_low: word(bytes, 32), nonce_high: word(bytes, 40),
            delivery: word(bytes, 48), ledger_serial: word(bytes, 56),
            accepted_sequence: word(bytes, 64), uart_sequence: word(bytes, 72),
            ack: [word(bytes, 80), word(bytes, 88), word(bytes, 96), word(bytes, 104)] };
        if small(bytes, 0) != VERSION || !(2..=3).contains(&MODE)
            || !(SELECT_BLOCKED..=RELEASE_ACCEPTED).contains(&request.phase)
            || request.os >= 64 || request.pid <= 0 || request.generation == 0
            || request.sequence == 0 || (request.nonce_low | request.nonce_high) == 0
            || (MODE != 2 && matches!(request.phase, TERMINAL | TERMINAL_PLUS_FIVE))
            || (MODE != 3 && matches!(request.phase, RECOVERY | AFTER_EIGHT_HELLO)) {
            return Err(-22);
        }
        if request.phase == RELEASE_ACCEPTED {
            if request.accepted_sequence != 2 || request.uart_sequence != 2
                || request.ack.iter().all(|&word| word == 0)
                || bytes[112..].iter().any(|&byte| byte != 0) { return Err(-22); }
        } else if bytes[64..].iter().any(|&byte| byte != 0) { return Err(-22); }
        Ok(request)
    }
    /// Permit held. Malformed/stale input never changes sequence or ownership.
    pub(crate) fn validate(&self) -> Result<(), i32> {
        if self.sequence != REQUEST_SEQUENCE.load(Ordering::Acquire).checked_add(1).ok_or(-75)? {
            return Err(-116);
        }
        if self.phase == SELECT_BLOCKED {
            if stage() != 0 || self.delivery != 0 || self.ledger_serial != 0 { return Err(-16); }
        } else {
            let key = crate::stability_observer::selected().ok_or(-11)?;
            if stage() == 0 || self.os != key.os || self.generation != key.generation
                || self.pid != key.pid || self.delivery != key.delivery || self.ledger_serial != key.ledger_serial
                || self.nonce_low != NONCE_LOW.load(Ordering::Acquire)
                || self.nonce_high != NONCE_HIGH.load(Ordering::Acquire) { return Err(-116); }
        }
        Ok(())
    }
    pub(crate) fn bind(&self) {
        NONCE_LOW.store(self.nonce_low, Ordering::Relaxed);
        NONCE_HIGH.store(self.nonce_high, Ordering::Relaxed);
        STAGE.store(ARMED, Ordering::Release);
    }
    pub(crate) fn consume(&self) { REQUEST_SEQUENCE.store(self.sequence, Ordering::Release); }
}

pub(crate) fn snapshot_begin(phase: crate::stability_observer::Phase) -> Result<u64, i32> {
    use crate::stability_observer::Phase;
    let prior = match phase {
        Phase::BlockedRead if stage() == ARMED => 0,
        Phase::AcceptedReturn if stage() == EMITTING => 1,
        Phase::Terminal if MODE == 2 && stage() == RELEASED => 2,
        Phase::TerminalPlusFive if MODE == 2 && stage() == RELEASED => 3,
        Phase::Recovery if MODE == 3 && stage() == RELEASED => 2,
        Phase::AfterEightHello if MODE == 3 && stage() == RELEASED => 3,
        _ => return Err(-116),
    };
    if SNAPSHOT_SEQUENCE.load(Ordering::Acquire) != prior { return Err(-116); }
    let sequence = SNAPSHOT_SEQUENCE.fetch_update(Ordering::AcqRel, Ordering::Acquire,
        |value| value.checked_add(1)).map_err(|_| -75)? + 1;
    kernel::pr_info!("STABILITY_PHASE_SNAPSHOT_BEGIN version=1 phase_sequence={} phase={:?} nonce_low={:016x} nonce_high={:016x} mono_ns={} sampling=independent_domains\n",
        sequence, phase, NONCE_LOW.load(Ordering::Acquire), NONCE_HIGH.load(Ordering::Acquire), now_ns());
    Ok(sequence)
}
pub(crate) fn snapshot_end(sequence: u64, error: i32) {
    kernel::pr_info!("STABILITY_PHASE_SNAPSHOT_END version=1 phase_sequence={} errno={} mono_ns={} barrier_calls={} verification_errno={}\n",
        sequence, error, now_ns(), BARRIER_CALLS.load(Ordering::Acquire), invalid_errno());
}
#[inline(never)]
pub(crate) fn observe_hold(sequence: u64) {
    kernel::pr_info!("STABILITY_HOLD_COUNTS version=1 mode={} phase_sequence={} stage={} timer_present={} timer_seconds={} host_hold_calls={} release_commits={} release_attempted={} verification_errno={} mono_ns={}\n",
        MODE, sequence, stage(), TIMER_PRESENT.load(Ordering::Acquire), TIMER_SECONDS.load(Ordering::Acquire),
        HOST_HOLD_CALLS.load(Ordering::Acquire), RELEASE_COMMITS.load(Ordering::Acquire),
        RELEASE_ATTEMPTED.load(Ordering::Acquire), invalid_errno(), now_ns());
}
#[inline(never)]
pub(crate) fn observe_ready() {
    kernel::pr_info!("STABILITY_HOLD_READY version=1 mode={} accepted_sequence={} nonce_low={:016x} nonce_high={:016x} timer_seconds={} held_ns={} host_hold_calls={} mono_ns={}\n",
        MODE, accepted_sequence(), NONCE_LOW.load(Ordering::Acquire), NONCE_HIGH.load(Ordering::Acquire),
        TIMER_SECONDS.load(Ordering::Acquire), HELD_NS.load(Ordering::Acquire), HOST_HOLD_CALLS.load(Ordering::Acquire), now_ns());
}
#[inline(never)]
pub(crate) fn observe_release(request: &Request, begin: u64, error: i32) {
    kernel::pr_info!("STABILITY_HOLD_RELEASE version=1 mode={} request_sequence={} accepted_sequence={} uart_sequence={} nonce_low={:016x} nonce_high={:016x} ack_le0={:016x} ack_le1={:016x} ack_le2={:016x} ack_le3={:016x} errno={} release_commits={} timer_seconds={} begin_ns={} end_ns={}\n",
        MODE, request.sequence, request.accepted_sequence, request.uart_sequence, request.nonce_low, request.nonce_high,
        request.ack[0], request.ack[1], request.ack[2], request.ack[3], error,
        RELEASE_COMMITS.load(Ordering::Acquire), TIMER_SECONDS.load(Ordering::Acquire), begin, now_ns());
}
pub(crate) fn terminal_ns() -> u64 { TERMINAL_NS.load(Ordering::Acquire) }
pub(crate) fn mark_terminal() {
    let _ = TERMINAL_NS.compare_exchange(0, now_ns(), Ordering::AcqRel, Ordering::Acquire);
}
pub(crate) fn recovery_seen() -> bool { RECOVERY_SEEN.load(Ordering::Acquire) }
pub(crate) fn mark_recovery() { RECOVERY_SEEN.store(true, Ordering::Release); }
pub(crate) fn output(bytes: &mut [u8; BYTES], snapshot: u64, error: i32, begin: u64) {
    // Release input contains a digest here. Every output byte is defined afresh.
    bytes[64..].fill(0);
    put(bytes, 64, snapshot); put(bytes, 72, error as i64 as u64);
    if let Some(key) = crate::stability_observer::selected() {
        for (offset, value) in [(80, key.application), (88, key.worker), (96, key.delivery),
            (104, key.ledger_serial), (112, key.ledger_index as u64), (120, key.response),
            (128, key.response_end), (152, key.generation)] { put(bytes, offset, value); }
        bytes[136..140].copy_from_slice(&key.pid.to_le_bytes());
        bytes[140..144].copy_from_slice(&key.cpu.to_le_bytes());
        bytes[144..148].copy_from_slice(&key.requester.to_le_bytes());
        bytes[148..152].copy_from_slice(&key.os.to_le_bytes());
    }
    for (offset, value) in [(160, stage()), (168, accepted_sequence()), (176, terminal_ns()),
        (184, invalid_errno() as i64 as u64), (192, BARRIER_CALLS.load(Ordering::Acquire)),
        (200, REQUEST_SEQUENCE.load(Ordering::Acquire)), (208, TIMER_SECONDS.load(Ordering::Acquire)),
        (216, TIMER_PRESENT.load(Ordering::Acquire) as u64), (224, HELD_NS.load(Ordering::Acquire)),
        (232, HOST_HOLD_CALLS.load(Ordering::Acquire)), (240, begin), (248, now_ns())] {
        put(bytes, offset, value);
    }
}
pub(crate) struct CompletionStatus {
    pub(crate) present: bool, pub(crate) publication_since: Option<u64>,
}
pub(crate) struct Status {
    pub(crate) transport_error: i32, pub(crate) applications: usize,
    pub(crate) original_application: bool, pub(crate) selected_completion: bool,
    pub(crate) publication_since: Option<u64>,
}
