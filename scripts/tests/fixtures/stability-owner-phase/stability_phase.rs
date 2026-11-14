// SPDX-License-Identifier: GPL-2.0-only
//! VERIFICATION OVERLAY ONLY. No production or exported ABI.
use core::sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering};

pub(crate) const COMMAND: u32 = 0xc100_f501;
pub(crate) const VERSION: u32 = 1;
pub(crate) const BYTES: usize = 256;
pub(crate) const SELECT_BLOCKED: u32 = 1;
pub(crate) const TERMINAL: u32 = 2;
pub(crate) const TERMINAL_PLUS_FIVE: u32 = 3;
pub(crate) const RECOVERY: u32 = 4;
pub(crate) const AFTER_EIGHT_HELLO: u32 = 5;
pub(crate) const QUERY: u32 = 6;
const ARMED: u64 = 1;
const ACCEPTED_PENDING: u64 = 2;
const RELEASED: u64 = 3;
static BUSY: AtomicBool = AtomicBool::new(false);
static STAGE: AtomicU64 = AtomicU64::new(0);
static NONCE_LOW: AtomicU64 = AtomicU64::new(0);
static NONCE_HIGH: AtomicU64 = AtomicU64::new(0);
static REQUEST_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static SNAPSHOT_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static ACCEPTED_SEQUENCE: AtomicU64 = AtomicU64::new(0);
static BARRIER_CALLS: AtomicU64 = AtomicU64::new(0);
static INVALID: AtomicI32 = AtomicI32::new(0);
static TERMINAL_NS: AtomicU64 = AtomicU64::new(0);
static RECOVERY_SEEN: AtomicBool = AtomicBool::new(false);

pub(crate) struct Permit;
impl Drop for Permit {
    fn drop(&mut self) {
        BUSY.store(false, Ordering::Release);
    }
}
pub(crate) fn permit() -> Result<Permit, i32> {
    BUSY.compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
        .map(|_| Permit)
        .map_err(|_| -11)
}
pub(crate) fn now_ns() -> u64 {
    // SAFETY: Pure monotonic Linux clock; no guest memory or production lock.
    unsafe { kernel::bindings::ktime_get() as u64 }
}
pub(crate) fn invalid(error: i32) {
    let value = if error < 0 { error } else { -71 };
    let _ = INVALID.compare_exchange(0, value, Ordering::AcqRel, Ordering::Acquire);
}
pub(crate) fn invalid_errno() -> i32 {
    INVALID.load(Ordering::Acquire)
}
pub(crate) fn stage() -> u64 {
    STAGE.load(Ordering::Acquire)
}

/// Caller already matched the real selected key and committed Completion::prepare.
/// Only scalar atomics run under the caller's existing slots lock.
pub(crate) fn accepted_selected() {
    if STAGE
        .compare_exchange(ARMED, ACCEPTED_PENDING, Ordering::AcqRel, Ordering::Acquire)
        .is_err()
    {
        invalid(-71);
    }
}

/// Caller matched the original selected Request and delivery before this hook.
/// This is observation-barrier EAGAIN, never a physical-full or fault attempt.
pub(crate) fn before_selected_send() -> Result<(), i32> {
    // Observation failure after initial release must not re-arm the barrier
    // and manufacture transport backpressure. The verification result stays
    // failed independently; the original real send still runs.
    if stage() == RELEASED {
        return Ok(());
    }
    BARRIER_CALLS.fetch_add(1, Ordering::AcqRel);
    if stage() != ACCEPTED_PENDING {
        invalid(-71);
    }
    Err(-11)
}
pub(crate) fn accepted_pending() -> bool {
    stage() == ACCEPTED_PENDING && invalid_errno() == 0
}
pub(crate) fn release_accepted(sequence: u64) {
    ACCEPTED_SEQUENCE.store(sequence, Ordering::Release);
    if invalid_errno() != 0 {
        return;
    }
    if STAGE
        .compare_exchange(
            ACCEPTED_PENDING,
            RELEASED,
            Ordering::AcqRel,
            Ordering::Acquire,
        )
        .is_err()
    {
        invalid(-71);
    }
}

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
    pub(crate) phase: u32,
    pub(crate) os: u32,
    pub(crate) pid: i32,
    pub(crate) generation: u64,
    pub(crate) sequence: u64,
    pub(crate) nonce_low: u64,
    pub(crate) nonce_high: u64,
    pub(crate) delivery: u64,
    pub(crate) ledger_serial: u64,
}
impl Request {
    pub(crate) fn read(bytes: &[u8; BYTES]) -> Result<Self, i32> {
        let request = Self {
            phase: small(bytes, 4),
            os: small(bytes, 8),
            pid: small(bytes, 12) as i32,
            generation: word(bytes, 16),
            sequence: word(bytes, 24),
            nonce_low: word(bytes, 32),
            nonce_high: word(bytes, 40),
            delivery: word(bytes, 48),
            ledger_serial: word(bytes, 56),
        };
        if small(bytes, 0) != VERSION
            || !(SELECT_BLOCKED..=QUERY).contains(&request.phase)
            || request.os >= 64
            || request.pid < 0
            || request.generation == 0
            || request.sequence == 0
            || (request.nonce_low | request.nonce_high) == 0
            || bytes[64..].iter().any(|&byte| byte != 0)
        {
            return Err(-22);
        }
        Ok(request)
    }

    /// Called only under Permit; input copy and parsing preceded all locks.
    pub(crate) fn validate(&self) -> Result<(), i32> {
        if self.sequence
            != REQUEST_SEQUENCE
                .load(Ordering::Acquire)
                .checked_add(1)
                .ok_or(-75)?
        {
            return Err(-116);
        }
        if self.phase == SELECT_BLOCKED {
            if stage() != 0 || self.delivery != 0 || self.ledger_serial != 0 {
                return Err(-16);
            }
        } else {
            let selected = crate::stability_observer::selected().ok_or(-11)?;
            if stage() == 0
                || self.os != selected.os
                || self.generation != selected.generation
                || self.pid != selected.pid
                || self.delivery != selected.delivery
                || self.ledger_serial != selected.ledger_serial
                || self.nonce_low != NONCE_LOW.load(Ordering::Acquire)
                || self.nonce_high != NONCE_HIGH.load(Ordering::Acquire)
            {
                return Err(-116);
            }
        }
        Ok(())
    }
    pub(crate) fn bind(&self) {
        NONCE_LOW.store(self.nonce_low, Ordering::Relaxed);
        NONCE_HIGH.store(self.nonce_high, Ordering::Relaxed);
        STAGE.store(ARMED, Ordering::Release);
    }
    pub(crate) fn consume(&self) {
        REQUEST_SEQUENCE.store(self.sequence, Ordering::Release);
    }
}

/// Permit serializes observer calls only; it is not a whole-OS state lock.
pub(crate) fn snapshot_begin(phase: crate::stability_observer::Phase) -> Result<u64, i32> {
    let sequence = SNAPSHOT_SEQUENCE
        .fetch_update(Ordering::AcqRel, Ordering::Acquire, |value| {
            value.checked_add(1)
        })
        .map_err(|_| -75)?
        + 1;
    kernel::pr_info!("STABILITY_PHASE_SNAPSHOT_BEGIN version=1 phase_sequence={} phase={:?} nonce_low={:016x} nonce_high={:016x} mono_ns={} sampling=independent_domains\n",
        sequence, phase, NONCE_LOW.load(Ordering::Acquire), NONCE_HIGH.load(Ordering::Acquire), now_ns());
    Ok(sequence)
}
pub(crate) fn snapshot_end(sequence: u64, error: i32) {
    kernel::pr_info!("STABILITY_PHASE_SNAPSHOT_END version=1 phase_sequence={} errno={} mono_ns={} barrier_calls={} verification_errno={}\n",
        sequence, error, now_ns(), BARRIER_CALLS.load(Ordering::Acquire), invalid_errno());
}
pub(crate) fn terminal_ns() -> u64 {
    TERMINAL_NS.load(Ordering::Acquire)
}
pub(crate) fn mark_terminal() {
    let _ = TERMINAL_NS.compare_exchange(0, now_ns(), Ordering::AcqRel, Ordering::Acquire);
}
pub(crate) fn recovery_seen() -> bool {
    RECOVERY_SEEN.load(Ordering::Acquire)
}
pub(crate) fn mark_recovery() {
    RECOVERY_SEEN.store(true, Ordering::Release);
}
pub(crate) fn output(bytes: &mut [u8; BYTES], snapshot_sequence: u64, error: i32) {
    put(bytes, 64, snapshot_sequence);
    put(bytes, 72, error as i64 as u64);
    if let Some(key) = crate::stability_observer::selected() {
        for (offset, value) in [
            (80, key.application),
            (88, key.worker),
            (96, key.delivery),
            (104, key.ledger_serial),
            (112, key.ledger_index as u64),
            (120, key.response),
            (128, key.response_end),
            (152, key.generation),
        ] {
            put(bytes, offset, value);
        }
        bytes[136..140].copy_from_slice(&key.pid.to_le_bytes());
        bytes[140..144].copy_from_slice(&key.cpu.to_le_bytes());
        bytes[144..148].copy_from_slice(&key.requester.to_le_bytes());
        bytes[148..152].copy_from_slice(&key.os.to_le_bytes());
    }
    put(bytes, 160, stage());
    put(bytes, 168, ACCEPTED_SEQUENCE.load(Ordering::Acquire));
    put(bytes, 176, terminal_ns());
    put(bytes, 184, invalid_errno() as i64 as u64);
    put(bytes, 192, BARRIER_CALLS.load(Ordering::Acquire));
    put(bytes, 200, REQUEST_SEQUENCE.load(Ordering::Acquire));
}

pub(crate) struct Status {
    pub(crate) transport_error: i32,
    pub(crate) applications: usize,
    pub(crate) original_application: bool,
    pub(crate) selected_completion: bool,
}
