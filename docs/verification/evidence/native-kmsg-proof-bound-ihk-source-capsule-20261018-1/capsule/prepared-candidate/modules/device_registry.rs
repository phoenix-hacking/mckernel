// SPDX-License-Identifier: GPL-2.0
//! Allocation-free provider-device registry and publication state machine.
//!
//! A Linux-facing adapter will eventually keep the provider payload and the
//! registered `mcdN` object outside this model.  That adapter must reserve a
//! slot before calling provider initialization, publish only after every
//! external operation succeeds, and hold the unregister guard while it drains
//! child OS objects and performs external teardown.  Rolling a guard back
//! restores only registry state; the adapter must first compensate any
//! external teardown it has already performed.  No callback, allocation,
//! kernel binding, or raw pointer is needed here.
//!
//! Each slot is one atomic word.  Consequently an open, OS attachment, or
//! unregister transition has one linearization point.  Generation-tagged
//! handles prevent a recycled minor from reviving an earlier provider.

use core::sync::atomic::{AtomicU64, Ordering};

pub(crate) const DEVICE_CAPACITY: usize = 64;

// Registry identity one is reserved for the single production IHK provider
// registry.  Dynamically constructed test/policy registries start at two so a
// handle can never cross the static/dynamic boundary by identity collision.
const PRODUCTION_DEVICE_REGISTRY_ID: u64 = 1;
static NEXT_DEVICE_REGISTRY_ID: AtomicU64 = AtomicU64::new(2);

// Positive v1 provider tokens are self-identifying without exposing a Rust
// layout across the module ABI.  Bits 0..5 carry the minor, bits 6..33 the
// nonzero 28-bit generation, bits 34..38 the ABI version, and bits 39..62 the
// ASCII magic "IHK".  Bit 63 is always clear, leaving negative i64 values for
// errno returns from the exported attach function.
const PROVIDER_TOKEN_MINOR_BITS: u32 = 6;
const PROVIDER_TOKEN_GENERATION_SHIFT: u32 = PROVIDER_TOKEN_MINOR_BITS;
const PROVIDER_TOKEN_HEADER_SHIFT: u32 = 34;
const PROVIDER_TOKEN_VERSION: u64 = 1;
const PROVIDER_TOKEN_MAGIC: u64 = 0x49_48_4b;
const PROVIDER_TOKEN_HEADER: u64 = (PROVIDER_TOKEN_MAGIC << 5) | PROVIDER_TOKEN_VERSION;
const PROVIDER_TOKEN_MINOR_MASK: u64 = (1 << PROVIDER_TOKEN_MINOR_BITS) - 1;
const PROVIDER_TOKEN_GENERATION_MASK: u64 = MAX_GENERATION;

// Internal errno bridge for a future Linux adapter.  The legacy registration
// API itself returns a nullable handle, so these richer failures are not a
// claim about its externally observable return convention.
const ENOENT: i32 = 2;
const ENOMEM: i32 = 12;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EOVERFLOW: i32 = 75;
const ESTALE: i32 = 116;
const EUCLEAN: i32 = 117;

const PHASE_MASK: u64 = 0x7;
const PHASE_VACANT: u64 = 0;
const PHASE_PUBLISHING: u64 = 1;
const PHASE_LIVE: u64 = 2;
const PHASE_UNPUBLISHING: u64 = 3;
const PHASE_RETIRED: u64 = 4;

const SHAREABLE_SHIFT: u32 = 3;
const SHAREABLE_ONE: u64 = 1 << SHAREABLE_SHIFT;
const PROVIDER_REFERENCE_SHIFT: u32 = 4;
const PROVIDER_REFERENCE_MASK: u64 = 0xffff << PROVIDER_REFERENCE_SHIFT;
const PROVIDER_REFERENCE_ONE: u64 = 1 << PROVIDER_REFERENCE_SHIFT;
const OS_REFERENCE_SHIFT: u32 = 20;
const OS_REFERENCE_MASK: u64 = 0xffff << OS_REFERENCE_SHIFT;
const OS_REFERENCE_ONE: u64 = 1 << OS_REFERENCE_SHIFT;
const MAX_REFERENCES: u16 = u16::MAX;
const GENERATION_SHIFT: u32 = 36;
const MAX_GENERATION: u64 = u64::MAX >> GENERATION_SHIFT;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum SharePolicy {
    Exclusive,
    Shared,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ActiveDevicePhase {
    Publishing,
    Live,
    Unpublishing,
}

impl ActiveDevicePhase {
    const fn from_bits(value: u64) -> Result<Self, DeviceRegistryError> {
        match value {
            PHASE_PUBLISHING => Ok(Self::Publishing),
            PHASE_LIVE => Ok(Self::Live),
            PHASE_UNPUBLISHING => Ok(Self::Unpublishing),
            _ => Err(DeviceRegistryError::Corrupt),
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DeviceRegistryError {
    NotFound,
    Capacity,
    Busy,
    InvalidMinor,
    InvalidToken,
    RegistryIdentityExhausted,
    GenerationExhausted,
    ProviderReferenceOverflow,
    OsReferenceOverflow,
    StaleHandle,
    Corrupt,
}

impl DeviceRegistryError {
    pub(crate) const fn errno(self) -> i32 {
        match self {
            Self::NotFound => -ENOENT,
            Self::Capacity => -ENOMEM,
            Self::Busy => -EBUSY,
            Self::InvalidMinor | Self::InvalidToken => -EINVAL,
            Self::RegistryIdentityExhausted
            | Self::GenerationExhausted
            | Self::ProviderReferenceOverflow
            | Self::OsReferenceOverflow => -EOVERFLOW,
            Self::StaleHandle => -ESTALE,
            Self::Corrupt => -EUCLEAN,
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) struct DeviceHandle {
    registry_id: u64,
    minor: u8,
    generation: u64,
}

impl DeviceHandle {
    pub(crate) const fn registry_id(self) -> u64 {
        self.registry_id
    }

    pub(crate) const fn minor(self) -> usize {
        self.minor as usize
    }

    pub(crate) const fn generation(self) -> u64 {
        self.generation
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct DeviceSnapshot {
    pub(crate) handle: DeviceHandle,
    pub(crate) phase: ActiveDevicePhase,
    pub(crate) share_policy: SharePolicy,
    /// References owned by successful control-device opens.  A Linux adapter
    /// must additionally pin the provider module behind every callback table.
    pub(crate) provider_references: u16,
    /// References retained by OS objects derived from this provider.
    pub(crate) os_references: u16,
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

pub(crate) struct DeviceRegistry {
    registry_id: u64,
    slots: [Slot; DEVICE_CAPACITY],
}

// The production identity exists exactly once in the compiled IHK provider.
// Test-only registries may exercise the private constructor from this module,
// but no sibling module can create another registry with identity one.
pub(crate) static IHK_DEVICE_REGISTRY: DeviceRegistry = DeviceRegistry::production();

impl DeviceRegistry {
    /// Constructs the one module-lifetime production registry in const space.
    const fn production() -> Self {
        Self {
            registry_id: PRODUCTION_DEVICE_REGISTRY_ID,
            slots: [const { Slot::new() }; DEVICE_CAPACITY],
        }
    }

    pub(crate) fn new() -> Result<Self, DeviceRegistryError> {
        Ok(Self {
            registry_id: next_registry_id()?,
            slots: [const { Slot::new() }; DEVICE_CAPACITY],
        })
    }

    /// Reserves the first reusable minor and blocks all operations on it.
    ///
    /// Dropping the returned guard aborts publication.  The generation is
    /// consumed even on abort so a handle observed during failed external
    /// setup can never name the next provider in that slot.
    ///
    /// A successful reservation is linearizable.  A full-table error is a
    /// transient scan result under concurrent churn, and `live_count` and
    /// `active_count` are likewise observations rather than snapshots.  A
    /// Linux adapter needing the legacy registration irqsave spinlock's stable
    /// first-fit result must serialize calls to `reserve` externally.
    pub(crate) fn reserve(
        &self,
        share_policy: SharePolicy,
    ) -> Result<ReservationGuard<'_>, DeviceRegistryError> {
        let mut generation_exhausted = false;

        for minor in 0..DEVICE_CAPACITY {
            let slot = &self.slots[minor];
            loop {
                let current = slot.word.load(Ordering::Acquire);
                validate_slot_word(current)?;
                match phase(current) {
                    PHASE_VACANT => {
                        let old_generation = generation(current);
                        if old_generation == MAX_GENERATION {
                            let retired = pack(
                                PHASE_RETIRED,
                                SharePolicy::Exclusive,
                                0,
                                0,
                                old_generation,
                            );
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
                        let publishing = pack(
                            PHASE_PUBLISHING,
                            share_policy,
                            0,
                            0,
                            next_generation,
                        );
                        if slot
                            .word
                            .compare_exchange(
                                current,
                                publishing,
                                Ordering::AcqRel,
                                Ordering::Acquire,
                            )
                            .is_ok()
                        {
                            return Ok(ReservationGuard {
                                registry: self,
                                handle: DeviceHandle {
                                    registry_id: self.registry_id,
                                    minor: minor as u8,
                                    generation: next_generation,
                                },
                                publishing,
                                armed: true,
                            });
                        }
                    }
                    PHASE_RETIRED => {
                        generation_exhausted = true;
                        break;
                    }
                    PHASE_PUBLISHING | PHASE_LIVE | PHASE_UNPUBLISHING => break,
                    _ => return Err(DeviceRegistryError::Corrupt),
                }
            }
        }

        if generation_exhausted {
            Err(DeviceRegistryError::GenerationExhausted)
        } else {
            Err(DeviceRegistryError::Capacity)
        }
    }

    /// Resolves a user-visible minor only while its provider is fully live.
    pub(crate) fn resolve_minor(
        &self,
        minor: usize,
    ) -> Result<DeviceHandle, DeviceRegistryError> {
        let slot = self.slot_by_minor(minor)?;
        let current = slot.word.load(Ordering::Acquire);
        validate_slot_word(current)?;
        match phase(current) {
            PHASE_LIVE => Ok(DeviceHandle {
                registry_id: self.registry_id,
                minor: minor as u8,
                generation: generation(current),
            }),
            PHASE_PUBLISHING | PHASE_UNPUBLISHING => Err(DeviceRegistryError::Busy),
            PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound),
            _ => Err(DeviceRegistryError::Corrupt),
        }
    }

    pub(crate) fn snapshot(
        &self,
        handle: DeviceHandle,
    ) -> Result<DeviceSnapshot, DeviceRegistryError> {
        let current = self.active_word(handle)?;
        Ok(DeviceSnapshot {
            handle,
            phase: ActiveDevicePhase::from_bits(phase(current))?,
            share_policy: share_policy(current),
            provider_references: provider_references(current),
            os_references: os_references(current),
        })
    }

    /// Encodes an exact handle as a positive, versioned scalar module token.
    ///
    /// The handle must still identify a live slot in this registry.  The
    /// resulting value is architecture-neutral for the locked x86_64 ABI and
    /// never aliases a negative errno return.
    pub(crate) fn encode_provider_token(
        &self,
        handle: DeviceHandle,
    ) -> Result<i64, DeviceRegistryError> {
        if self.registry_id != PRODUCTION_DEVICE_REGISTRY_ID {
            return Err(DeviceRegistryError::InvalidToken);
        }
        let snapshot = self.snapshot(handle)?;
        if snapshot.phase != ActiveDevicePhase::Live {
            return Err(DeviceRegistryError::Busy);
        }
        let token = (PROVIDER_TOKEN_HEADER << PROVIDER_TOKEN_HEADER_SHIFT)
            | (handle.generation << PROVIDER_TOKEN_GENERATION_SHIFT)
            | handle.minor as u64;
        if token == 0 || token > i64::MAX as u64 {
            return Err(DeviceRegistryError::Corrupt);
        }
        Ok(token as i64)
    }

    /// Decodes only the exact v1 token shape for this production registry.
    ///
    /// Slot phase and generation are checked by the requested registry
    /// operation after decoding, so old but well-formed tokens become stale or
    /// not-found rather than being reinterpreted as a current handle.
    pub(crate) fn decode_provider_token(
        &self,
        token: i64,
    ) -> Result<DeviceHandle, DeviceRegistryError> {
        if self.registry_id != PRODUCTION_DEVICE_REGISTRY_ID || token <= 0 {
            return Err(DeviceRegistryError::InvalidToken);
        }
        let raw = token as u64;
        if raw >> PROVIDER_TOKEN_HEADER_SHIFT != PROVIDER_TOKEN_HEADER {
            return Err(DeviceRegistryError::InvalidToken);
        }
        let minor = raw & PROVIDER_TOKEN_MINOR_MASK;
        let handle_generation =
            (raw >> PROVIDER_TOKEN_GENERATION_SHIFT) & PROVIDER_TOKEN_GENERATION_MASK;
        if minor >= DEVICE_CAPACITY as u64 || handle_generation == 0 {
            return Err(DeviceRegistryError::InvalidToken);
        }
        Ok(DeviceHandle {
            registry_id: self.registry_id,
            minor: minor as u8,
            generation: handle_generation,
        })
    }

    /// Publishes the single minor-zero provider lease used by the SMP module.
    ///
    /// Concurrent or duplicate attach attempts may reserve another minor
    /// transiently, but they abort that reservation and fail with `Busy`.
    /// Thus no unsuccessful call leaves an additional live provider.
    pub(crate) fn attach_provider_token(&self) -> Result<i64, DeviceRegistryError> {
        let reservation = self.reserve(SharePolicy::Shared)?;
        let reserved = reservation.handle();
        if reserved.minor() != 0 {
            reservation.abort()?;
            return Err(DeviceRegistryError::Busy);
        }
        let handle = reservation.publish()?;
        match self.encode_provider_token(handle) {
            Ok(token) => Ok(token),
            Err(error) => {
                let cleanup = self
                    .begin_unregister(handle)
                    .and_then(|unregister| unregister.commit());
                match cleanup {
                    Ok(()) => Err(error),
                    Err(cleanup_error) => Err(cleanup_error),
                }
            }
        }
    }

    /// Retires exactly the provider generation named by a v1 token.
    ///
    /// A failed commit drops its armed guard and restores the live phase, so
    /// child OS references can drain before the same token is retried.
    pub(crate) fn detach_provider_token(
        &self,
        token: i64,
    ) -> Result<DeviceHandle, DeviceRegistryError> {
        let handle = self.decode_provider_token(token)?;
        self.begin_unregister(handle)?.commit()?;
        Ok(handle)
    }

    /// Retires the exact token owned by the reviewed SMP module destructor.
    ///
    /// The namespaced caller keeps this token in one non-Copy owner and never
    /// exposes child references.  Reaching an invalid, stale, busy, or corrupt
    /// state is therefore an internal ownership invariant violation, not a
    /// recoverable module-exit result.  Failing stop prevents teardown from
    /// silently succeeding while a live provider entry is abandoned.
    pub(crate) fn retire_owned_provider_token(&self, token: i64) -> DeviceHandle {
        match self.detach_provider_token(token) {
            Ok(handle) => handle,
            Err(error) => panic!(
                "provider lease ownership invariant violated: errno={}",
                error.errno(),
            ),
        }
    }

    /// Acquires the provider reference owned by one successfully opened file.
    pub(crate) fn acquire_open(
        &self,
        handle: DeviceHandle,
    ) -> Result<OpenLease<'_>, DeviceRegistryError> {
        let slot = self.slot_by_handle(handle)?;
        loop {
            let current = checked_live_word(slot, handle)?;
            let references = provider_references(current);
            if share_policy(current) == SharePolicy::Exclusive && references != 0 {
                return Err(DeviceRegistryError::Busy);
            }
            if references == MAX_REFERENCES {
                return Err(DeviceRegistryError::ProviderReferenceOverflow);
            }
            match slot.word.compare_exchange(
                current,
                current + PROVIDER_REFERENCE_ONE,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(OpenLease {
                        registry: self,
                        handle,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    /// Acquires one open reference and transfers it across the module ABI as
    /// the exact generation-tagged provider token.
    ///
    /// The trusted receiving module must retain one non-Copy owner for every
    /// successful call and balance each owner with one
    /// `release_owned_open_token` call.  Multiple shared opens intentionally
    /// receive the same token: the registry reference count, rather than a
    /// uniquely identifiable Rust value crossing the ABI, is the authority.
    pub(crate) fn acquire_open_token(
        &self,
        minor: usize,
    ) -> Result<i64, DeviceRegistryError> {
        let handle = self.resolve_minor(minor)?;
        let lease = self.acquire_open(handle)?;
        match self.encode_provider_token(lease.handle()) {
            Ok(token) => {
                core::mem::forget(lease);
                Ok(token)
            }
            Err(error) => Err(error),
        }
    }

    /// Releases one exact open reference owned by the reviewed SMP adapter.
    ///
    /// Invalid, stale, and zero-reference releases are internal ownership
    /// violations.  Because concurrent shared opens carry the same scalar, a
    /// duplicate close cannot be distinguished while another reference is
    /// live; the reviewed non-Copy caller must therefore remain count-balanced.
    /// Failing stop prevents teardown after a detectable accounting divergence.
    pub(crate) fn release_owned_open_token(&self, token: i64) -> DeviceHandle {
        let release = self
            .decode_provider_token(token)
            .and_then(|handle| self.release_open_checked(handle).map(|()| handle));
        match release {
            Ok(handle) => handle,
            Err(error) => panic!(
                "provider open ownership invariant violated: errno={}",
                error.errno(),
            ),
        }
    }

    /// Acquires the provider ownership reference retained by one OS object.
    pub(crate) fn acquire_os(
        &self,
        handle: DeviceHandle,
    ) -> Result<DeviceOsLease<'_>, DeviceRegistryError> {
        let slot = self.slot_by_handle(handle)?;
        loop {
            let current = checked_live_word(slot, handle)?;
            if os_references(current) == MAX_REFERENCES {
                return Err(DeviceRegistryError::OsReferenceOverflow);
            }
            match slot.word.compare_exchange(
                current,
                current + OS_REFERENCE_ONE,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(DeviceOsLease {
                        registry: self,
                        handle,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    /// Excludes new opens and OS attachments while external teardown runs.
    ///
    /// The caller must not invoke sleeping teardown while executing this
    /// method; it should first obtain the guard and then perform that work.
    /// Existing OS leases may drain while the guard blocks new attachments.
    /// Dropping or explicitly rolling back the guard restores the current
    /// counters to `Live`.  Commit permanently vacates the slot, but succeeds
    /// only after both reference classes reach zero.
    pub(crate) fn begin_unregister(
        &self,
        handle: DeviceHandle,
    ) -> Result<UnregisterGuard<'_>, DeviceRegistryError> {
        let slot = self.slot_by_handle(handle)?;
        loop {
            let current = checked_live_word(slot, handle)?;
            if provider_references(current) != 0 {
                return Err(DeviceRegistryError::Busy);
            }
            let unpublishing = (current & !PHASE_MASK) | PHASE_UNPUBLISHING;
            match slot.word.compare_exchange(
                current,
                unpublishing,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    return Ok(UnregisterGuard {
                        registry: self,
                        handle,
                        armed: true,
                    });
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn live_count(&self) -> Result<usize, DeviceRegistryError> {
        let mut count = 0;
        for slot in &self.slots {
            let current = slot.word.load(Ordering::Acquire);
            validate_slot_word(current)?;
            if phase(current) == PHASE_LIVE {
                count += 1;
            }
        }
        Ok(count)
    }

    pub(crate) fn active_count(&self) -> Result<usize, DeviceRegistryError> {
        let mut count = 0;
        for slot in &self.slots {
            let current = slot.word.load(Ordering::Acquire);
            validate_slot_word(current)?;
            if matches!(
                phase(current),
                PHASE_PUBLISHING | PHASE_LIVE | PHASE_UNPUBLISHING
            ) {
                count += 1;
            }
        }
        Ok(count)
    }

    fn slot_by_minor(&self, minor: usize) -> Result<&Slot, DeviceRegistryError> {
        self.slots
            .get(minor)
            .ok_or(DeviceRegistryError::InvalidMinor)
    }

    fn slot_by_handle(&self, handle: DeviceHandle) -> Result<&Slot, DeviceRegistryError> {
        if handle.registry_id != self.registry_id || handle.generation == 0 {
            return Err(DeviceRegistryError::StaleHandle);
        }
        self.slot_by_minor(handle.minor())
    }

    fn active_word(&self, handle: DeviceHandle) -> Result<u64, DeviceRegistryError> {
        let slot = self.slot_by_handle(handle)?;
        let current = slot.word.load(Ordering::Acquire);
        validate_slot_word(current)?;
        if generation(current) != handle.generation {
            return Err(DeviceRegistryError::StaleHandle);
        }
        match phase(current) {
            PHASE_PUBLISHING | PHASE_LIVE | PHASE_UNPUBLISHING => Ok(current),
            PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound),
            _ => Err(DeviceRegistryError::Corrupt),
        }
    }

    fn release_open_checked(&self, handle: DeviceHandle) -> Result<(), DeviceRegistryError> {
        let slot = self.slot_by_handle(handle)?;
        loop {
            let current = checked_live_word(slot, handle)?;
            if provider_references(current) == 0 {
                return Err(DeviceRegistryError::Corrupt);
            }
            if slot
                .word
                .compare_exchange(
                    current,
                    current - PROVIDER_REFERENCE_ONE,
                    Ordering::Release,
                    Ordering::Relaxed,
                )
                .is_ok()
            {
                return Ok(());
            }
        }
    }

    fn release_open(&self, handle: DeviceHandle) {
        let _ = self.release_open_checked(handle);
    }

    fn release_os(&self, handle: DeviceHandle) {
        let Ok(slot) = self.slot_by_handle(handle) else {
            return;
        };
        loop {
            let current = slot.word.load(Ordering::Acquire);
            if validate_slot_word(current).is_err()
                || generation(current) != handle.generation
                || !matches!(phase(current), PHASE_LIVE | PHASE_UNPUBLISHING)
                || os_references(current) == 0
            {
                return;
            }
            if slot
                .word
                .compare_exchange(
                    current,
                    current - OS_REFERENCE_ONE,
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

#[must_use = "dropping a reservation aborts provider publication"]
pub(crate) struct ReservationGuard<'a> {
    registry: &'a DeviceRegistry,
    handle: DeviceHandle,
    publishing: u64,
    armed: bool,
}

impl ReservationGuard<'_> {
    pub(crate) const fn handle(&self) -> DeviceHandle {
        self.handle
    }

    pub(crate) fn publish(mut self) -> Result<DeviceHandle, DeviceRegistryError> {
        let live = (self.publishing & !PHASE_MASK) | PHASE_LIVE;
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(
                self.publishing,
                live,
                Ordering::Release,
                Ordering::Acquire,
            )
            .map_err(|_| DeviceRegistryError::Corrupt)?;
        self.armed = false;
        Ok(self.handle)
    }

    pub(crate) fn abort(mut self) -> Result<(), DeviceRegistryError> {
        self.abort_inner()?;
        self.armed = false;
        Ok(())
    }

    fn abort_inner(&self) -> Result<(), DeviceRegistryError> {
        let vacant = pack(
            PHASE_VACANT,
            SharePolicy::Exclusive,
            0,
            0,
            self.handle.generation,
        );
        self.registry.slots[self.handle.minor()]
            .word
            .compare_exchange(
                self.publishing,
                vacant,
                Ordering::Release,
                Ordering::Acquire,
            )
            .map(|_| ())
            .map_err(|_| DeviceRegistryError::Corrupt)
    }
}

impl Drop for ReservationGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let _ = self.abort_inner();
        }
    }
}

#[must_use = "an open lease keeps its provider registered until drop"]
pub(crate) struct OpenLease<'a> {
    registry: &'a DeviceRegistry,
    handle: DeviceHandle,
}

impl OpenLease<'_> {
    pub(crate) const fn handle(&self) -> DeviceHandle {
        self.handle
    }
}

impl Drop for OpenLease<'_> {
    fn drop(&mut self) {
        self.registry.release_open(self.handle);
    }
}

#[must_use = "an OS lease keeps its provider registered until drop"]
pub(crate) struct DeviceOsLease<'a> {
    registry: &'a DeviceRegistry,
    handle: DeviceHandle,
}

impl DeviceOsLease<'_> {
    pub(crate) const fn handle(&self) -> DeviceHandle {
        self.handle
    }
}

impl Drop for DeviceOsLease<'_> {
    fn drop(&mut self) {
        self.registry.release_os(self.handle);
    }
}

#[must_use = "dropping an unregister guard restores the live provider"]
pub(crate) struct UnregisterGuard<'a> {
    registry: &'a DeviceRegistry,
    handle: DeviceHandle,
    armed: bool,
}

impl UnregisterGuard<'_> {
    pub(crate) const fn handle(&self) -> DeviceHandle {
        self.handle
    }

    pub(crate) fn commit(mut self) -> Result<(), DeviceRegistryError> {
        let slot = self.registry.slot_by_handle(self.handle)?;
        loop {
            let current = checked_unpublishing_word(slot, self.handle)?;
            if provider_references(current) != 0 || os_references(current) != 0 {
                return Err(DeviceRegistryError::Busy);
            }
            let vacant = pack(
                PHASE_VACANT,
                SharePolicy::Exclusive,
                0,
                0,
                self.handle.generation,
            );
            match slot.word.compare_exchange(
                current,
                vacant,
                Ordering::Release,
                Ordering::Acquire,
            ) {
                Ok(_) => {
                    self.armed = false;
                    return Ok(());
                }
                Err(_) => continue,
            }
        }
    }

    pub(crate) fn rollback(mut self) -> Result<DeviceHandle, DeviceRegistryError> {
        self.rollback_inner()?;
        self.armed = false;
        Ok(self.handle)
    }

    fn rollback_inner(&self) -> Result<(), DeviceRegistryError> {
        let slot = self.registry.slot_by_handle(self.handle)?;
        loop {
            let current = checked_unpublishing_word(slot, self.handle)?;
            let live = (current & !PHASE_MASK) | PHASE_LIVE;
            match slot.word.compare_exchange(
                current,
                live,
                Ordering::Release,
                Ordering::Acquire,
            ) {
                Ok(_) => return Ok(()),
                Err(_) => continue,
            }
        }
    }
}

impl Drop for UnregisterGuard<'_> {
    fn drop(&mut self) {
        if self.armed {
            let _ = self.rollback_inner();
        }
    }
}

fn checked_live_word(
    slot: &Slot,
    handle: DeviceHandle,
) -> Result<u64, DeviceRegistryError> {
    let current = slot.word.load(Ordering::Acquire);
    validate_slot_word(current)?;
    if generation(current) != handle.generation {
        return Err(DeviceRegistryError::StaleHandle);
    }
    match phase(current) {
        PHASE_LIVE => Ok(current),
        PHASE_PUBLISHING | PHASE_UNPUBLISHING => Err(DeviceRegistryError::Busy),
        PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound),
        _ => Err(DeviceRegistryError::Corrupt),
    }
}

fn checked_unpublishing_word(
    slot: &Slot,
    handle: DeviceHandle,
) -> Result<u64, DeviceRegistryError> {
    let current = slot.word.load(Ordering::Acquire);
    validate_slot_word(current)?;
    if generation(current) != handle.generation {
        return Err(DeviceRegistryError::StaleHandle);
    }
    match phase(current) {
        PHASE_UNPUBLISHING => Ok(current),
        PHASE_PUBLISHING | PHASE_LIVE => Err(DeviceRegistryError::Busy),
        PHASE_VACANT | PHASE_RETIRED => Err(DeviceRegistryError::NotFound),
        _ => Err(DeviceRegistryError::Corrupt),
    }
}

fn validate_slot_word(word: u64) -> Result<(), DeviceRegistryError> {
    let provider_references = provider_references(word);
    let os_references = os_references(word);
    let generation = generation(word);
    match phase(word) {
        PHASE_VACANT
            if provider_references == 0
                && os_references == 0
                && share_policy(word) == SharePolicy::Exclusive =>
        {
            Ok(())
        }
        PHASE_PUBLISHING
            if generation != 0 && provider_references == 0 && os_references == 0 =>
        {
            Ok(())
        }
        PHASE_LIVE
            if generation != 0
                && (share_policy(word) == SharePolicy::Shared
                    || provider_references <= 1) =>
        {
            Ok(())
        }
        PHASE_UNPUBLISHING if generation != 0 && provider_references == 0 => Ok(()),
        PHASE_RETIRED
            if generation == MAX_GENERATION
                && provider_references == 0
                && os_references == 0
                && share_policy(word) == SharePolicy::Exclusive =>
        {
            Ok(())
        }
        _ => Err(DeviceRegistryError::Corrupt),
    }
}

const fn pack(
    phase: u64,
    share_policy: SharePolicy,
    provider_references: u16,
    os_references: u16,
    generation: u64,
) -> u64 {
    (generation << GENERATION_SHIFT)
        | ((os_references as u64) << OS_REFERENCE_SHIFT)
        | ((provider_references as u64) << PROVIDER_REFERENCE_SHIFT)
        | (match share_policy {
            SharePolicy::Exclusive => 0,
            SharePolicy::Shared => SHAREABLE_ONE,
        })
        | phase
}

const fn phase(word: u64) -> u64 {
    word & PHASE_MASK
}

const fn share_policy(word: u64) -> SharePolicy {
    if word & SHAREABLE_ONE == 0 {
        SharePolicy::Exclusive
    } else {
        SharePolicy::Shared
    }
}

const fn provider_references(word: u64) -> u16 {
    ((word & PROVIDER_REFERENCE_MASK) >> PROVIDER_REFERENCE_SHIFT) as u16
}

const fn os_references(word: u64) -> u16 {
    ((word & OS_REFERENCE_MASK) >> OS_REFERENCE_SHIFT) as u16
}

const fn generation(word: u64) -> u64 {
    word >> GENERATION_SHIFT
}

fn next_registry_id() -> Result<u64, DeviceRegistryError> {
    next_registry_id_from(&NEXT_DEVICE_REGISTRY_ID)
}

fn next_registry_id_from(sequence: &AtomicU64) -> Result<u64, DeviceRegistryError> {
    let mut current = sequence.load(Ordering::Relaxed);
    loop {
        let next = current
            .checked_add(1)
            .ok_or(DeviceRegistryError::RegistryIdentityExhausted)?;
        if current == 0 {
            return Err(DeviceRegistryError::RegistryIdentityExhausted);
        }
        match sequence.compare_exchange_weak(
            current,
            next,
            Ordering::Relaxed,
            Ordering::Relaxed,
        ) {
            Ok(_) => return Ok(current),
            Err(observed) => current = observed,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashSet;
    use std::sync::{Arc, Barrier};
    use std::thread;

    fn publish(registry: &DeviceRegistry, share_policy: SharePolicy) -> DeviceHandle {
        registry.reserve(share_policy).unwrap().publish().unwrap()
    }

    fn registry() -> DeviceRegistry {
        DeviceRegistry::new().unwrap()
    }

    fn expect_error<T>(
        result: Result<T, DeviceRegistryError>,
    ) -> DeviceRegistryError {
        match result {
            Ok(_) => panic!("operation unexpectedly succeeded"),
            Err(error) => error,
        }
    }

    #[test]
    fn exact_capacity_first_fit_generation_reuse_and_stale_rejection() {
        let registry = registry();
        let mut handles = std::vec::Vec::new();
        for minor in 0..DEVICE_CAPACITY {
            let handle = publish(&registry, SharePolicy::Shared);
            assert_eq!(minor, handle.minor());
            assert_eq!(1, handle.generation());
            handles.push(handle);
        }
        assert_eq!(DEVICE_CAPACITY, registry.live_count().unwrap());
        assert_eq!(
            DeviceRegistryError::Capacity,
            expect_error(registry.reserve(SharePolicy::Exclusive))
        );

        let stale = handles[9];
        registry.begin_unregister(stale).unwrap().commit().unwrap();
        let replacement = publish(&registry, SharePolicy::Exclusive);
        assert_eq!(stale.minor(), replacement.minor());
        assert_eq!(stale.generation() + 1, replacement.generation());
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            registry.snapshot(stale).unwrap_err()
        );
    }

    #[test]
    fn dropping_reservation_aborts_and_consumes_generation() {
        let registry = registry();
        let abandoned = {
            let reservation = registry.reserve(SharePolicy::Shared).unwrap();
            let handle = reservation.handle();
            assert_eq!(ActiveDevicePhase::Publishing, registry.snapshot(handle).unwrap().phase);
            assert_eq!(DeviceRegistryError::Busy, registry.resolve_minor(0).unwrap_err());
            handle
        };
        assert_eq!(0, registry.active_count().unwrap());
        assert_eq!(DeviceRegistryError::NotFound, registry.resolve_minor(0).unwrap_err());
        let live = publish(&registry, SharePolicy::Exclusive);
        assert_eq!(abandoned.generation() + 1, live.generation());
    }

    #[test]
    fn explicit_reservation_abort_restores_slot() {
        let registry = registry();
        let reservation = registry.reserve(SharePolicy::Exclusive).unwrap();
        let handle = reservation.handle();
        reservation.abort().unwrap();
        assert_eq!(DeviceRegistryError::NotFound, registry.snapshot(handle).unwrap_err());
        assert_eq!(0, registry.active_count().unwrap());
    }

    #[test]
    fn publication_preserves_sharing_policy() {
        let registry = registry();
        let shared = publish(&registry, SharePolicy::Shared);
        let exclusive = publish(&registry, SharePolicy::Exclusive);
        assert_eq!(SharePolicy::Shared, registry.snapshot(shared).unwrap().share_policy);
        assert_eq!(SharePolicy::Exclusive, registry.snapshot(exclusive).unwrap().share_policy);
        assert_eq!(shared, registry.resolve_minor(shared.minor()).unwrap());
        assert_eq!(exclusive, registry.resolve_minor(exclusive.minor()).unwrap());
    }

    #[test]
    fn shareable_provider_references_are_counted_and_released() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        let first = registry.acquire_open(handle).unwrap();
        let second = registry.acquire_open(handle).unwrap();
        assert_eq!(handle, first.handle());
        assert_eq!(2, registry.snapshot(handle).unwrap().provider_references);
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.begin_unregister(handle))
        );
        drop(first);
        assert_eq!(1, registry.snapshot(handle).unwrap().provider_references);
        drop(second);
        assert_eq!(0, registry.snapshot(handle).unwrap().provider_references);
    }

    #[test]
    fn exclusive_provider_allows_only_one_open() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Exclusive);
        let first = registry.acquire_open(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.acquire_open(handle))
        );
        drop(first);
        let replacement = registry.acquire_open(handle).unwrap();
        assert_eq!(handle, replacement.handle());
    }

    #[test]
    fn os_references_drain_while_unpublishing() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Exclusive);
        let open = registry.acquire_open(handle).unwrap();
        let first_os = registry.acquire_os(handle).unwrap();
        let second_os = registry.acquire_os(handle).unwrap();
        let snapshot = registry.snapshot(handle).unwrap();
        assert_eq!(1, snapshot.provider_references);
        assert_eq!(2, snapshot.os_references);
        assert_eq!(handle, first_os.handle());
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.begin_unregister(handle))
        );
        drop(open);
        let unregister = registry.begin_unregister(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.acquire_os(handle))
        );
        drop(first_os);
        assert_eq!(1, registry.snapshot(handle).unwrap().os_references);
        drop(second_os);
        unregister.commit().unwrap();
    }

    #[test]
    fn provider_reference_overflow_fails_without_field_carry() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        registry.slots[handle.minor()].word.store(
            pack(
                PHASE_LIVE,
                SharePolicy::Shared,
                MAX_REFERENCES,
                7,
                handle.generation,
            ),
            Ordering::Release,
        );
        assert_eq!(
            DeviceRegistryError::ProviderReferenceOverflow,
            expect_error(registry.acquire_open(handle))
        );
        let snapshot = registry.snapshot(handle).unwrap();
        assert_eq!(MAX_REFERENCES, snapshot.provider_references);
        assert_eq!(7, snapshot.os_references);
    }

    #[test]
    fn os_reference_overflow_fails_without_generation_carry() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Exclusive);
        registry.slots[handle.minor()].word.store(
            pack(
                PHASE_LIVE,
                SharePolicy::Exclusive,
                0,
                MAX_REFERENCES,
                handle.generation,
            ),
            Ordering::Release,
        );
        assert_eq!(
            DeviceRegistryError::OsReferenceOverflow,
            expect_error(registry.acquire_os(handle))
        );
        assert_eq!(
            handle.generation,
            registry.snapshot(handle).unwrap().handle.generation()
        );
    }

    #[test]
    fn dropping_unregister_guard_restores_live_state() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        {
            let unregister = registry.begin_unregister(handle).unwrap();
            assert_eq!(handle, unregister.handle());
            let snapshot = registry.snapshot(handle).unwrap();
            assert_eq!(ActiveDevicePhase::Unpublishing, snapshot.phase);
            assert_eq!(SharePolicy::Shared, snapshot.share_policy);
            assert_eq!(DeviceRegistryError::Busy, registry.resolve_minor(0).unwrap_err());
            assert_eq!(
                DeviceRegistryError::Busy,
                expect_error(registry.acquire_open(handle))
            );
        }
        assert_eq!(ActiveDevicePhase::Live, registry.snapshot(handle).unwrap().phase);
        let _open = registry.acquire_open(handle).unwrap();
    }

    #[test]
    fn explicit_unregister_rollback_reopens_provider() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Exclusive);
        let restored = registry.begin_unregister(handle).unwrap().rollback().unwrap();
        assert_eq!(handle, restored);
        assert_eq!(ActiveDevicePhase::Live, registry.snapshot(handle).unwrap().phase);
        let _open = registry.acquire_open(handle).unwrap();
    }

    #[test]
    fn premature_unregister_commit_fails_and_rolls_back() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        let os = registry.acquire_os(handle).unwrap();
        let unregister = registry.begin_unregister(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            unregister.commit().unwrap_err()
        );
        assert_eq!(ActiveDevicePhase::Live, registry.snapshot(handle).unwrap().phase);
        drop(os);
        registry.begin_unregister(handle).unwrap().commit().unwrap();
    }

    #[test]
    fn unregister_commit_vacates_and_reuse_stales_old_handle() {
        let registry = registry();
        let old = publish(&registry, SharePolicy::Exclusive);
        registry.begin_unregister(old).unwrap().commit().unwrap();
        assert_eq!(DeviceRegistryError::NotFound, registry.snapshot(old).unwrap_err());
        let current = publish(&registry, SharePolicy::Exclusive);
        assert!(current.generation() > old.generation());
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            expect_error(registry.acquire_os(old))
        );
    }

    #[test]
    fn foreign_registry_handle_is_always_stale() {
        let first = registry();
        let second = registry();
        let first_handle = publish(&first, SharePolicy::Shared);
        let second_handle = publish(&second, SharePolicy::Shared);
        assert_ne!(first_handle.registry_id(), second_handle.registry_id());
        assert_eq!(first_handle.minor(), second_handle.minor());
        assert_eq!(first_handle.generation(), second_handle.generation());
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            second.snapshot(first_handle).unwrap_err()
        );
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            expect_error(second.acquire_open(first_handle))
        );
        assert_eq!(0, second.snapshot(second_handle).unwrap().provider_references);
    }

    #[test]
    fn registry_identity_exhaustion_is_nonwrapping() {
        let exhausted = AtomicU64::new(u64::MAX);
        assert_eq!(
            DeviceRegistryError::RegistryIdentityExhausted,
            next_registry_id_from(&exhausted).unwrap_err()
        );
        assert_eq!(u64::MAX, exhausted.load(Ordering::Relaxed));

        let invalid = AtomicU64::new(0);
        assert_eq!(
            DeviceRegistryError::RegistryIdentityExhausted,
            next_registry_id_from(&invalid).unwrap_err()
        );
        assert_eq!(0, invalid.load(Ordering::Relaxed));
    }

    #[test]
    fn generation_exhaustion_retires_without_wrapping() {
        let registry = registry();
        for slot in &registry.slots {
            slot.word.store(
                pack(
                    PHASE_VACANT,
                    SharePolicy::Exclusive,
                    0,
                    0,
                    MAX_GENERATION,
                ),
                Ordering::Release,
            );
        }
        assert_eq!(
            DeviceRegistryError::GenerationExhausted,
            expect_error(registry.reserve(SharePolicy::Shared))
        );
        for slot in &registry.slots {
            let current = slot.word.load(Ordering::Acquire);
            assert_eq!(PHASE_RETIRED, phase(current));
            assert_eq!(MAX_GENERATION, generation(current));
        }
    }

    #[test]
    fn one_retired_minor_does_not_hide_an_available_slot() {
        let registry = registry();
        registry.slots[0].word.store(
            pack(
                PHASE_VACANT,
                SharePolicy::Exclusive,
                0,
                0,
                MAX_GENERATION,
            ),
            Ordering::Release,
        );
        let reservation = registry.reserve(SharePolicy::Shared).unwrap();
        assert_eq!(1, reservation.handle().minor());
    }

    #[test]
    fn malformed_packed_words_fail_closed_as_corrupt() {
        let zero_generation_registry = registry();
        zero_generation_registry.slots[0].word.store(
            pack(PHASE_LIVE, SharePolicy::Exclusive, 0, 0, 0),
            Ordering::Release,
        );
        assert_eq!(
            DeviceRegistryError::Corrupt,
            zero_generation_registry.resolve_minor(0).unwrap_err()
        );

        let vacant_reference_registry = registry();
        vacant_reference_registry.slots[0].word.store(
            pack(PHASE_VACANT, SharePolicy::Exclusive, 1, 0, 4),
            Ordering::Release,
        );
        assert_eq!(
            DeviceRegistryError::Corrupt,
            expect_error(vacant_reference_registry.reserve(SharePolicy::Shared))
        );

        let exclusive_reference_registry = registry();
        exclusive_reference_registry.slots[0].word.store(
            pack(PHASE_LIVE, SharePolicy::Exclusive, 2, 0, 1),
            Ordering::Release,
        );
        assert_eq!(
            DeviceRegistryError::Corrupt,
            exclusive_reference_registry.resolve_minor(0).unwrap_err()
        );
        assert_eq!(
            DeviceRegistryError::Corrupt,
            exclusive_reference_registry.live_count().unwrap_err()
        );
    }

    #[test]
    fn lease_drop_does_not_rewrite_corrupt_slot_words() {
        let open_registry = registry();
        let open_handle = publish(&open_registry, SharePolicy::Exclusive);
        let open = open_registry.acquire_open(open_handle).unwrap();
        let corrupt_open = pack(
            PHASE_LIVE,
            SharePolicy::Exclusive,
            2,
            0,
            open_handle.generation,
        );
        open_registry.slots[open_handle.minor()].word.store(
            corrupt_open,
            Ordering::Release,
        );
        drop(open);
        assert_eq!(
            corrupt_open,
            open_registry.slots[open_handle.minor()].word.load(Ordering::Acquire)
        );

        let os_registry = registry();
        let os_handle = publish(&os_registry, SharePolicy::Exclusive);
        let os = os_registry.acquire_os(os_handle).unwrap();
        let unregister = os_registry.begin_unregister(os_handle).unwrap();
        let corrupt_os = pack(
            PHASE_UNPUBLISHING,
            SharePolicy::Exclusive,
            1,
            1,
            os_handle.generation,
        );
        os_registry.slots[os_handle.minor()].word.store(
            corrupt_os,
            Ordering::Release,
        );
        drop(os);
        assert_eq!(
            corrupt_os,
            os_registry.slots[os_handle.minor()].word.load(Ordering::Acquire)
        );
        drop(unregister);
    }

    #[test]
    fn open_before_unregister_excludes_unregister() {
        let registry = registry();
        let handle = publish(&registry, SharePolicy::Shared);
        let open = registry.acquire_open(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.begin_unregister(handle))
        );
        drop(open);
        registry.begin_unregister(handle).unwrap().commit().unwrap();
    }

    #[test]
    fn unregister_before_open_excludes_new_references() {
        let registry = registry();
        let unregister = registry.begin_unregister(publish(&registry, SharePolicy::Shared)).unwrap();
        let handle = unregister.handle();
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.acquire_open(handle))
        );
        assert_eq!(
            DeviceRegistryError::Busy,
            expect_error(registry.acquire_os(handle))
        );
        unregister.rollback().unwrap();
        let _open = registry.acquire_open(handle).unwrap();
    }

    #[test]
    fn concurrent_publications_claim_unique_slots() {
        const WORKERS: usize = 16;
        let registry = Arc::new(registry());
        let start = Arc::new(Barrier::new(WORKERS));
        let mut workers = std::vec::Vec::new();
        for _ in 0..WORKERS {
            let registry = Arc::clone(&registry);
            let start = Arc::clone(&start);
            workers.push(thread::spawn(move || {
                start.wait();
                publish(&registry, SharePolicy::Shared)
            }));
        }
        let handles: std::vec::Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().unwrap())
            .collect();
        let minors: HashSet<_> = handles.iter().map(|handle| handle.minor()).collect();
        assert_eq!(WORKERS, minors.len());
        assert_eq!(WORKERS, registry.live_count().unwrap());
    }

    #[test]
    fn production_registry_token_round_trip_is_positive_and_exact() {
        let registry = DeviceRegistry::production();
        let token = registry.attach_provider_token().unwrap();
        assert!(token > 0);
        let handle = registry.decode_provider_token(token).unwrap();
        assert_eq!(handle, registry.decode_provider_token(token).unwrap());
        assert_eq!(0, handle.minor());
        assert_eq!(1, handle.generation());

        let open = registry.acquire_open(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            registry.detach_provider_token(token).unwrap_err()
        );
        drop(open);

        let os = registry.acquire_os(handle).unwrap();
        assert_eq!(
            DeviceRegistryError::Busy,
            registry.detach_provider_token(token).unwrap_err()
        );
        assert_eq!(ActiveDevicePhase::Live, registry.snapshot(handle).unwrap().phase);
        drop(os);
        assert_eq!(handle, registry.detach_provider_token(token).unwrap());
        assert_eq!(0, registry.active_count().unwrap());
    }

    #[test]
    fn provider_open_tokens_count_shared_files_and_release_once_each() {
        let registry = DeviceRegistry::production();
        let provider_token = registry.attach_provider_token().unwrap();
        let handle = registry.decode_provider_token(provider_token).unwrap();

        let first = registry.acquire_open_token(0).unwrap();
        let second = registry.acquire_open_token(0).unwrap();
        assert_eq!(provider_token, first);
        assert_eq!(first, second);
        assert_eq!(2, registry.snapshot(handle).unwrap().provider_references);
        assert_eq!(handle, registry.release_owned_open_token(first));
        assert_eq!(1, registry.snapshot(handle).unwrap().provider_references);
        assert_eq!(
            DeviceRegistryError::Busy,
            registry.detach_provider_token(provider_token).unwrap_err()
        );
        assert_eq!(handle, registry.release_owned_open_token(second));
        assert_eq!(0, registry.snapshot(handle).unwrap().provider_references);
        assert_eq!(handle, registry.detach_provider_token(provider_token).unwrap());
    }

    #[test]
    fn owned_open_token_release_fails_stop_on_unbalanced_receipt() {
        let registry = DeviceRegistry::production();
        let provider_token = registry.attach_provider_token().unwrap();
        let receipt = registry.acquire_open_token(0).unwrap();
        registry.release_owned_open_token(receipt);

        let duplicate = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            registry.release_owned_open_token(receipt);
        }));
        assert!(duplicate.is_err());
        assert_eq!(
            registry.decode_provider_token(provider_token).unwrap(),
            registry.detach_provider_token(provider_token).unwrap()
        );

        let malformed = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| {
            registry.release_owned_open_token(-1);
        }));
        assert!(malformed.is_err());
    }

    #[test]
    fn provider_token_header_version_and_generation_fail_closed() {
        let registry = DeviceRegistry::production();
        let handle = publish(&registry, SharePolicy::Shared);
        let token = registry.encode_provider_token(handle).unwrap();
        let zero_generation = (PROVIDER_TOKEN_HEADER << PROVIDER_TOKEN_HEADER_SHIFT) as i64;
        for malformed in [0, -1, i64::MAX, token ^ (1_i64 << 34), zero_generation] {
            assert_eq!(
                DeviceRegistryError::InvalidToken,
                registry.decode_provider_token(malformed).unwrap_err()
            );
        }
    }

    #[test]
    fn provider_token_is_stale_after_unregister_and_slot_reuse() {
        let registry = DeviceRegistry::production();
        let token = registry.attach_provider_token().unwrap();
        let first = registry.decode_provider_token(token).unwrap();
        assert_eq!(first, registry.detach_provider_token(token).unwrap());
        let decoded = registry.decode_provider_token(token).unwrap();
        assert_eq!(DeviceRegistryError::NotFound, registry.snapshot(decoded).unwrap_err());

        let replacement_token = registry.attach_provider_token().unwrap();
        let replacement = registry.decode_provider_token(replacement_token).unwrap();
        assert_eq!(first.minor(), replacement.minor());
        assert!(replacement.generation() > first.generation());
        assert_eq!(
            DeviceRegistryError::StaleHandle,
            registry.snapshot(decoded).unwrap_err()
        );
    }

    #[test]
    fn dynamic_registry_cannot_issue_or_accept_production_tokens() {
        let production = DeviceRegistry::production();
        let token = production.attach_provider_token().unwrap();
        let dynamic = registry();
        let dynamic_handle = publish(&dynamic, SharePolicy::Shared);
        assert_eq!(
            DeviceRegistryError::InvalidToken,
            dynamic.encode_provider_token(dynamic_handle).unwrap_err()
        );
        assert_eq!(
            DeviceRegistryError::InvalidToken,
            dynamic.decode_provider_token(token).unwrap_err()
        );
    }

    #[test]
    fn concurrent_provider_attaches_publish_exactly_one_minor_zero_lease() {
        const WORKERS: usize = 16;
        let registry = Arc::new(DeviceRegistry::production());
        let start = Arc::new(Barrier::new(WORKERS));
        let mut workers = std::vec::Vec::new();
        for _ in 0..WORKERS {
            let registry = Arc::clone(&registry);
            let start = Arc::clone(&start);
            workers.push(thread::spawn(move || {
                start.wait();
                registry.attach_provider_token()
            }));
        }
        let results: std::vec::Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().unwrap())
            .collect();
        let tokens: std::vec::Vec<_> = results
            .iter()
            .filter_map(|result| result.as_ref().ok().copied())
            .collect();
        assert_eq!(1, tokens.len());
        assert_eq!(
            WORKERS - 1,
            results
                .iter()
                .filter(|result| **result == Err(DeviceRegistryError::Busy))
                .count()
        );
        assert_eq!(1, registry.live_count().unwrap());
        assert_eq!(
            0,
            registry
                .decode_provider_token(tokens[0])
                .unwrap()
                .minor()
        );
        registry.detach_provider_token(tokens[0]).unwrap();
    }

    #[test]
    fn concurrent_duplicate_detach_has_one_winner_and_no_live_slot() {
        const WORKERS: usize = 8;
        let registry = Arc::new(DeviceRegistry::production());
        let token = registry.attach_provider_token().unwrap();
        let start = Arc::new(Barrier::new(WORKERS));
        let mut workers = std::vec::Vec::new();
        for _ in 0..WORKERS {
            let registry = Arc::clone(&registry);
            let start = Arc::clone(&start);
            workers.push(thread::spawn(move || {
                start.wait();
                registry.detach_provider_token(token)
            }));
        }
        let results: std::vec::Vec<_> = workers
            .into_iter()
            .map(|worker| worker.join().unwrap())
            .collect();
        assert_eq!(1, results.iter().filter(|result| result.is_ok()).count());
        assert!(results.iter().filter_map(|result| result.as_ref().err()).all(
            |error| matches!(error, DeviceRegistryError::Busy | DeviceRegistryError::NotFound)
        ));
        assert_eq!(0, registry.active_count().unwrap());
    }

    #[test]
    fn errno_mapping_and_minor_bounds_fail_closed() {
        let registry = registry();
        assert_eq!(
            DeviceRegistryError::InvalidMinor,
            registry.resolve_minor(DEVICE_CAPACITY).unwrap_err()
        );
        let mappings = [
            (DeviceRegistryError::NotFound, -2),
            (DeviceRegistryError::Capacity, -12),
            (DeviceRegistryError::Busy, -16),
            (DeviceRegistryError::InvalidMinor, -22),
            (DeviceRegistryError::InvalidToken, -22),
            (DeviceRegistryError::RegistryIdentityExhausted, -75),
            (DeviceRegistryError::GenerationExhausted, -75),
            (DeviceRegistryError::ProviderReferenceOverflow, -75),
            (DeviceRegistryError::OsReferenceOverflow, -75),
            (DeviceRegistryError::StaleHandle, -116),
            (DeviceRegistryError::Corrupt, -117),
        ];
        for (error, expected) in mappings {
            assert_eq!(expected, error.errno());
        }
    }
}
