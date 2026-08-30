// SPDX-License-Identifier: GPL-2.0
//! Allocation-free OS-minor registry and lifecycle-state foundation.
//!
//! The frozen IHK core reserves the first free entry from a 64-element table,
//! marks it invalid while creation is in progress, publishes it only after
//! initialization, refuses destruction while references are held, and returns
//! the slot to the table only after destruction succeeds.  This module models
//! those ownership rules without calling C or allocating memory.  A generation
//! is part of every handle so an entry recycled at the same minor cannot be
//! mistaken for the prior OS instance.

use core::sync::atomic::{AtomicU64, Ordering};

use super::abi::{
    IHK_OS_STATUS_BOOTED, IHK_OS_STATUS_BOOTING, IHK_OS_STATUS_FAILED,
    IHK_OS_STATUS_FREEZING, IHK_OS_STATUS_FROZEN, IHK_OS_STATUS_HUNGUP,
    IHK_OS_STATUS_LOADING, IHK_OS_STATUS_NOT_BOOTED, IHK_OS_STATUS_READY,
    IHK_OS_STATUS_RUNNING, IHK_OS_STATUS_SHUTDOWN, IHK_OS_STATUS_COUNT,
};

pub(crate) const OS_CAPACITY: usize = 64;

// Linux errno values used by the frozen host-driver paths.
const ENOENT: i32 = 2;
const ENOMEM: i32 = 12;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EOVERFLOW: i32 = 75;
const ESTALE: i32 = 116;
const EUCLEAN: i32 = 117;

const PHASE_MASK: u64 = 0x7;
const PHASE_VACANT: u64 = 0;
const PHASE_RESERVED: u64 = 1;
const PHASE_LIVE: u64 = 2;
const PHASE_DESTROYING: u64 = 3;
const PHASE_RETIRED: u64 = 4;

const STATUS_SHIFT: u32 = 3;
const STATUS_MASK: u64 = 0xf << STATUS_SHIFT;
const REFERENCE_SHIFT: u32 = 7;
const REFERENCE_MASK: u64 = 0xffff << REFERENCE_SHIFT;
const REFERENCE_ONE: u64 = 1 << REFERENCE_SHIFT;
const MAX_REFERENCES: u16 = u16::MAX;
const GENERATION_SHIFT: u32 = 23;
const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(u8)]
pub(crate) enum OsStatus {
    NotBooted = 0,
    Loading = 1,
    Booting = 2,
    Booted = 3,
    Ready = 4,
    Running = 5,
    Freezing = 6,
    Frozen = 7,
    Shutdown = 8,
    Failed = 9,
    Hungup = 10,
}

impl OsStatus {
    const fn from_bits(value: u8) -> Result<Self, RegistryError> {
        match value {
            0 => Ok(Self::NotBooted),
            1 => Ok(Self::Loading),
            2 => Ok(Self::Booting),
            3 => Ok(Self::Booted),
            4 => Ok(Self::Ready),
            5 => Ok(Self::Running),
            6 => Ok(Self::Freezing),
            7 => Ok(Self::Frozen),
            8 => Ok(Self::Shutdown),
            9 => Ok(Self::Failed),
            10 => Ok(Self::Hungup),
            _ => Err(RegistryError::Corrupt),
        }
    }
}

// Keep the state representation tied to the canonical x86_64 ABI capture.
const _: [(); OsStatus::NotBooted as usize] = [(); IHK_OS_STATUS_NOT_BOOTED as usize];
const _: [(); OsStatus::Loading as usize] = [(); IHK_OS_STATUS_LOADING as usize];
const _: [(); OsStatus::Booting as usize] = [(); IHK_OS_STATUS_BOOTING as usize];
const _: [(); OsStatus::Booted as usize] = [(); IHK_OS_STATUS_BOOTED as usize];
const _: [(); OsStatus::Ready as usize] = [(); IHK_OS_STATUS_READY as usize];
const _: [(); OsStatus::Running as usize] = [(); IHK_OS_STATUS_RUNNING as usize];
const _: [(); OsStatus::Freezing as usize] = [(); IHK_OS_STATUS_FREEZING as usize];
const _: [(); OsStatus::Frozen as usize] = [(); IHK_OS_STATUS_FROZEN as usize];
const _: [(); OsStatus::Shutdown as usize] = [(); IHK_OS_STATUS_SHUTDOWN as usize];
const _: [(); OsStatus::Failed as usize] = [(); IHK_OS_STATUS_FAILED as usize];
const _: [(); OsStatus::Hungup as usize] = [(); IHK_OS_STATUS_HUNGUP as usize];

// Each bit names a permitted next state.  Re-publishing the current state is
// idempotent and is accepted separately.  The matrix is intentionally strict:
// it follows the observable load/boot/monitor/freeze/shutdown paths of the
// frozen SMP provider and rejects all unreviewed edges.
const ALLOWED_TRANSITIONS: [u16; 11] = [
    (1 << 1) | (1 << 2),                         // not-booted -> load/boot
    (1 << 0) | (1 << 8),                         // loading -> initial/shutdown
    (1 << 3) | (1 << 4) | (1 << 5) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 4) | (1 << 5) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 6) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 7) | (1 << 8) | (1 << 9) | (1 << 10),
    (1 << 5) | (1 << 6) | (1 << 8) | (1 << 9) | (1 << 10),
    1 << 0,                                       // shutdown -> initial
    (1 << 0) | (1 << 8),                         // failed -> initial/shutdown
    (1 << 0) | (1 << 8) | (1 << 9),              // hungup -> initial/shutdown/fail
];

const _: [(); ALLOWED_TRANSITIONS.len()] = [(); IHK_OS_STATUS_COUNT as usize];

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum RegistryError {
    NotFound,
    Capacity,
    Busy,
    InvalidMinor,
    InvalidTransition,
    GenerationExhausted,
    ReferenceOverflow,
    StaleHandle,
    Corrupt,
}

impl RegistryError {
    pub(crate) const fn errno(self) -> i32 {
        match self {
            Self::NotFound => -ENOENT,
            Self::Capacity => -ENOMEM,
            Self::Busy => -EBUSY,
            Self::InvalidMinor | Self::InvalidTransition => -EINVAL,
            Self::GenerationExhausted | Self::ReferenceOverflow => -EOVERFLOW,
            Self::StaleHandle => -ESTALE,
            Self::Corrupt => -EUCLEAN,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct OsHandle {
    minor: u8,
    generation: u64,
}

impl OsHandle {
    pub(crate) const fn minor(self) -> usize {
        self.minor as usize
    }

    pub(crate) const fn generation(self) -> u64 {
        self.generation
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct OsSnapshot {
    pub(crate) handle: OsHandle,
    pub(crate) status: OsStatus,
    pub(crate) references: u16,
}

struct Slot {
    word: AtomicU64,
}

impl Slot {
    const fn new() -> Self {
        Self {
            word: AtomicU64::new(0),
        }
    }
}

pub(crate) struct OsRegistry {
    slots: [Slot; OS_CAPACITY],
}

impl OsRegistry {
    pub(crate) const fn new() -> Self {
        Self {
            slots: [const { Slot::new() }; OS_CAPACITY],
        }
    }

    pub(crate) fn reserve(&self) -> Result<ReservationGuard<'_>, RegistryError> {
        let mut generation_exhausted = false;

        for minor in 0..OS_CAPACITY {
            let slot = &self.slots[minor];
            loop {
                let current = slot.word.load(Ordering::Acquire);
                match phase(current) {
                    PHASE_VACANT => {
                        let old_generation = generation(current);
                        if old_generation == MAX_GENERATION {
                            let retired = pack(PHASE_RETIRED, OsStatus::NotBooted, 0, old_generation);
                            if slot
                                .word
                                .compare_exchange(
                                    current,
                                    retired,
                                    Ordering::AcqRel,
                                    Ordering::Acquire,
                                )
                                .is_ok()
                            {
                                generation_exhausted = true;
                                break;
                            }
                            continue;
                        }

                        let next_generation = old_generation + 1;
                        let reserved = pack(
                            PHASE_RESERVED,
                            OsStatus::NotBooted,
                            0,
                            next_generation,
                        );
                        if slot
                            .word
                            .compare_exchange(
                                current,
                                reserved,
                                Ordering::AcqRel,
                                Ordering::Acquire,
                            )
                            .is_ok()
                        {
                            return Ok(ReservationGuard {
                                registry: self,
                                handle: OsHandle {
                                    minor: minor as u8,
                                    generation: next_generation,
                                },
                                reserved,
                                armed: true,
                            });
                        }
                    }
                    PHASE_RETIRED => {
                        generation_exhausted = true;
                        break;
                    }
                    PHASE_RESERVED | PHASE_LIVE | PHASE_DESTROYING => break,
                    _ => return Err(RegistryError::Corrupt),
                }
            }
        }

        if generation_exhausted {
            Err(RegistryError::GenerationExhausted)
        } else {
            Err(RegistryError::Capacity)
        }
    }

    pub(crate) fn resolve_minor(&self, minor: usize) -> Result<OsHandle, RegistryError> {
        let slot = self.slot_by_minor(minor)?;
        let current = slot.word.load(Ordering::Acquire);
        match phase(current) {
            PHASE_LIVE => Ok(OsHandle {
                minor: minor as u8,
                generation: generation(current),
            }),
            PHASE_RESERVED | PHASE_DESTROYING => Err(RegistryError::Busy),
            PHASE_VACANT | PHASE_RETIRED => Err(RegistryError::NotFound),
            _ => Err(RegistryError::Corrupt),
        }
    }

    pub(crate) fn snapshot(&self, handle: OsHandle) -> Result<OsSnapshot, RegistryError> {
        let current = self.live_word(handle)?;
        Ok(OsSnapshot {
            handle,
            status: status(current)?,
            references: references(current),
        })
    }

    pub(crate) fn transition(
        &self,
        handle: OsHandle,
        next: OsStatus,
    ) -> Result<(), RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            let previous = status(current)?;
            if previous == next {
                return Ok(());
            }
            if ALLOWED_TRANSITIONS[previous as usize] & (1 << (next as u8)) == 0 {
                return Err(RegistryError::InvalidTransition);
            }
            let updated = (current & !STATUS_MASK) | ((next as u64) << STATUS_SHIFT);
            match slot.word.compare_exchange(
                current,
                updated,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => return Ok(()),
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn acquire(&self, handle: OsHandle) -> Result<OsLease<'_>, RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            if references(current) == MAX_REFERENCES {
                return Err(RegistryError::ReferenceOverflow);
            }
            match slot.word.compare_exchange(
                current,
                current + REFERENCE_ONE,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(OsLease {
                        registry: self,
                        handle,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn begin_destroy(
        &self,
        handle: OsHandle,
    ) -> Result<DestroyGuard<'_>, RegistryError> {
        let slot = &self.slots[handle.minor()];
        loop {
            let current = checked_live_word(slot, handle)?;
            if references(current) != 0 {
                return Err(RegistryError::Busy);
            }
            let destroying = (current & !PHASE_MASK) | PHASE_DESTROYING;
            match slot.word.compare_exchange(
                current,
                destroying,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(DestroyGuard {
                        registry: self,
                        handle,
                        live: current,
                        destroying,
                        armed: true,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn live_count(&self) -> usize {
        self.slots
            .iter()
            .filter(|slot| phase(slot.word.load(Ordering::Acquire)) == PHASE_LIVE)
            .count()
    }

    fn slot_by_minor(&self, minor: usize) -> Result<&Slot, RegistryError> {
        self.slots.get(minor).ok_or(RegistryError::InvalidMinor)
    }

    fn live_word(&self, handle: OsHandle) -> Result<u64, RegistryError> {
        checked_live_word(&self.slots[handle.minor()], handle)
    }
}

pub(crate) struct ReservationGuard<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
    reserved: u64,
    armed: bool,
}

impl ReservationGuard<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }

    pub(crate) fn commit(mut self) -> Result<OsHandle, RegistryError> {
        let live = (self.reserved & !PHASE_MASK) | PHASE_LIVE;
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(
                self.reserved,
                live,
                Ordering::Release,
                Ordering::Acquire,
            )
            .map_err(|_| RegistryError::Corrupt)?;
        self.armed = false;
        Ok(self.handle)
    }
}

impl Drop for ReservationGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let vacant = pack(
                PHASE_VACANT,
                OsStatus::NotBooted,
                0,
                self.handle.generation,
            );
            let _ = self.registry.slots[self.handle.minor()]
                .word
                .compare_exchange(
                    self.reserved,
                    vacant,
                    Ordering::Release,
                    Ordering::Relaxed,
                );
        }
    }
}

pub(crate) struct OsLease<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
}

impl OsLease<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }
}

impl Drop for OsLease<'_> {
    fn drop(&mut self) {
        let slot = &self.registry.slots[self.handle.minor()];
        loop {
            let current = slot.word.load(Ordering::Acquire);
            if generation(current) != self.handle.generation
                || phase(current) != PHASE_LIVE
                || references(current) == 0
            {
                return;
            }
            if slot
                .word
                .compare_exchange(
                    current,
                    current - REFERENCE_ONE,
                    Ordering::Release,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                return;
            }
        }
    }
}

pub(crate) struct DestroyGuard<'a> {
    registry: &'a OsRegistry,
    handle: OsHandle,
    live: u64,
    destroying: u64,
    armed: bool,
}

impl DestroyGuard<'_> {
    pub(crate) const fn handle(&self) -> OsHandle {
        self.handle
    }

    pub(crate) fn commit(mut self) -> Result<(), RegistryError> {
        let vacant = pack(
            PHASE_VACANT,
            OsStatus::NotBooted,
            0,
            self.handle.generation,
        );
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(
                self.destroying,
                vacant,
                Ordering::Release,
                Ordering::Acquire,
            )
            .map_err(|_| RegistryError::Corrupt)?;
        self.armed = false;
        Ok(())
    }
}

impl Drop for DestroyGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let _ = self.registry.slots[self.handle.minor()]
                .word
                .compare_exchange(
                    self.destroying,
                    self.live,
                    Ordering::Release,
                    Ordering::Relaxed,
                );
        }
    }
}

fn checked_live_word(slot: &Slot, handle: OsHandle) -> Result<u64, RegistryError> {
    let current = slot.word.load(Ordering::Acquire);
    if generation(current) != handle.generation {
        return Err(RegistryError::StaleHandle);
    }
    match phase(current) {
        PHASE_LIVE => Ok(current),
        PHASE_RESERVED | PHASE_DESTROYING => Err(RegistryError::Busy),
        PHASE_VACANT | PHASE_RETIRED => Err(RegistryError::NotFound),
        _ => Err(RegistryError::Corrupt),
    }
}

const fn pack(phase: u64, status: OsStatus, references: u16, generation: u64) -> u64 {
    (generation << GENERATION_SHIFT)
        | ((references as u64) << REFERENCE_SHIFT)
        | ((status as u64) << STATUS_SHIFT)
        | phase
}

const fn phase(word: u64) -> u64 {
    word & PHASE_MASK
}

const fn status(word: u64) -> Result<OsStatus, RegistryError> {
    OsStatus::from_bits(((word & STATUS_MASK) >> STATUS_SHIFT) as u8)
}

const fn references(word: u64) -> u16 {
    ((word & REFERENCE_MASK) >> REFERENCE_SHIFT) as u16
}

const fn generation(word: u64) -> u64 {
    word >> GENERATION_SHIFT
}
