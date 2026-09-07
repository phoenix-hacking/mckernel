// SPDX-License-Identifier: GPL-2.0
//! IHK's shared-memory IKC ring primitive.
//!
//! The wire-visible header is declared by the canonical x86_64 ABI module.
//! This module owns only the bounded ring-index protocol and packet copies. It
//! allocates no memory, calls no C implementation, and changes no public UAPI.

use core::cell::UnsafeCell;
use core::hint::spin_loop;
use core::marker::PhantomData;
use core::mem::{align_of, size_of};
use core::ptr::{addr_of, addr_of_mut, copy, read_volatile, write};
use core::ptr::NonNull;
use core::sync::atomic::{AtomicBool, AtomicU64, Ordering};

use super::abi::IhkIkcQueueHead;

const LEGACY_EMPTY_SENTINEL: i32 = -1;
const LEGACY_WRITE_QUEUE_RETRY: usize = 128;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EUCLEAN: i32 = 117;

/// A validated snapshot of the shared queue counters.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct QueueSnapshot {
    pub(crate) packet_size: usize,
    pub(crate) packet_count: u64,
    pub(crate) read: u64,
    pub(crate) published: u64,
    pub(crate) reserved: u64,
}

/// Queue outcomes are kept typed until a legacy ABI boundary needs an errno.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum QueueError {
    Invalid,
    Empty,
    Full,
    Busy,
    Corrupt,
}

impl QueueError {
    /// Preserve the legacy empty sentinel and full/argument errno values.
    pub(crate) const fn legacy_status(self) -> i32 {
        match self {
            Self::Invalid => -EINVAL,
            Self::Empty => LEGACY_EMPTY_SENTINEL,
            Self::Full | Self::Busy => -EBUSY,
            Self::Corrupt => -EUCLEAN,
        }
    }
}

/// Releases the process-local single-consumer claim on every return path.
struct ConsumerClaim<'queue>(&'queue AtomicBool);

impl Drop for ConsumerClaim<'_> {
    fn drop(&mut self) {
        self.0.store(false, Ordering::Release);
    }
}

/// A lifetime-bound view of one mapped IKC queue.
///
/// Packet slots are intentionally not exposed as Rust references: the other
/// endpoint may be a C McKernel instance operating on the same bytes.
pub(crate) struct SharedQueue<'mapping> {
    head: NonNull<IhkIkcQueueHead>,
    mapping_bytes: usize,
    consumer_active: AtomicBool,
    _mapping: PhantomData<&'mapping UnsafeCell<u8>>,
}

// SAFETY: `SharedQueue` never creates references to packet storage. All shared
// counters are accessed atomically and immutable metadata is read volatile.
unsafe impl Send for SharedQueue<'_> {}

// SAFETY: Concurrent producers coordinate reservations/publication through
// the aligned counters. Consumers are serialized by `consumer_active`, so a
// producer cannot reuse a slot until its sole local consumer finishes copying.
unsafe impl Sync for SharedQueue<'_> {}

impl<'mapping> SharedQueue<'mapping> {
    /// Initialize a queue in exclusively owned, suitably aligned storage.
    pub(crate) fn initialize(
        storage: &'mapping mut [u8],
        id: u32,
        queue_type: u16,
        packet_size: u16,
    ) -> Result<Self, QueueError> {
        let header_bytes = size_of::<IhkIkcQueueHead>();
        let packet_bytes = usize::from(packet_size);
        let address = storage.as_mut_ptr() as usize;
        if address % align_of::<IhkIkcQueueHead>() != 0
            || packet_bytes == 0
            || packet_bytes % size_of::<u64>() != 0
            || storage.len() < header_bytes
        {
            return Err(QueueError::Invalid);
        }
        let packet_count = (storage.len() - header_bytes) / packet_bytes;
        if packet_count < 2 || packet_count > u32::MAX as usize {
            return Err(QueueError::Invalid);
        }
        let queue_size = packet_bytes
            .checked_mul(packet_count)
            .ok_or(QueueError::Invalid)?;

        let head = storage.as_mut_ptr().cast::<IhkIkcQueueHead>();
        // SAFETY: `storage` is exclusive for `'mapping`, has the checked
        // alignment and size, and the value initializes every header byte.
        unsafe {
            write(
                head,
                IhkIkcQueueHead {
                    id,
                    type_: queue_type,
                    packet_size,
                    packet_count: packet_count as u32,
                    flags: 0,
                    read_offset: 0,
                    max_read_offset: 0,
                    write_offset: 0,
                    queue_size: queue_size as u64,
                    channel_id: 0,
                    read_cpu: 0,
                    write_cpu: 0,
                    reserved: 0,
                },
            );
        }

        // SAFETY: The header was just initialized in the same live mapping.
        unsafe { Self::attach(head, storage.len()) }
    }

    /// Attach to an existing shared queue mapping.
    ///
    /// # Safety
    ///
    /// `head..head + mapping_bytes` must remain mapped for `'mapping`. The
    /// remote endpoint must obey the legacy reservation/publication protocol
    /// using aligned atomic operations compatible with Linux's `cmpxchg`.
    /// Rust must be the sole dequeue owner: no remote endpoint may consume and
    /// exactly one local `SharedQueue` view may exist for this mapping. No Rust
    /// reference may alias the header or payload while this view lives; remote
    /// access is restricted to the agreed shared-memory protocol. Callers must
    /// also preserve the legacy IRQ-disabled/non-sleeping progress rule from a
    /// successful write reservation through publication.
    // SAFETY: Callers must uphold the mapping lifetime, no-alias, aligned
    // Linux-cmpxchg peer, sole Rust dequeue owner, and IRQ-disabled progress
    // obligations documented above for the entire attached view lifetime.
    pub(crate) unsafe fn attach(
        head: *mut IhkIkcQueueHead,
        mapping_bytes: usize,
    ) -> Result<Self, QueueError> {
        let head = NonNull::new(head).ok_or(QueueError::Invalid)?;
        if head.as_ptr() as usize % align_of::<IhkIkcQueueHead>() != 0
            || mapping_bytes < size_of::<IhkIkcQueueHead>()
            || (head.as_ptr() as usize).checked_add(mapping_bytes).is_none()
        {
            return Err(QueueError::Invalid);
        }
        let queue = Self {
            head,
            mapping_bytes,
            consumer_active: AtomicBool::new(false),
            _mapping: PhantomData,
        };
        queue.snapshot()?;
        Ok(queue)
    }

    #[inline]
    fn read_counter(&self) -> &AtomicU64 {
        // SAFETY: `attach` checked the header alignment and lifetime. The
        // frozen ABI places this field at an 8-byte-aligned offset.
        unsafe { AtomicU64::from_ptr(addr_of_mut!((*self.head.as_ptr()).read_offset)) }
    }

    #[inline]
    fn publish_counter(&self) -> &AtomicU64 {
        // SAFETY: Same mapping/alignment argument as `read_counter`; this is
        // the frozen max_read_offset field at offset 24.
        unsafe { AtomicU64::from_ptr(addr_of_mut!((*self.head.as_ptr()).max_read_offset)) }
    }

    #[inline]
    fn write_counter(&self) -> &AtomicU64 {
        // SAFETY: Same mapping/alignment argument as `read_counter`; this is
        // the frozen write_offset field at offset 32.
        unsafe { AtomicU64::from_ptr(addr_of_mut!((*self.head.as_ptr()).write_offset)) }
    }

    fn metadata(&self) -> (usize, u64, u64) {
        // SAFETY: The header remains mapped for `'mapping`. Metadata is
        // initialized before publication and is immutable while attached;
        // volatile reads also avoid manufacturing shared Rust references.
        unsafe {
            (
                usize::from(read_volatile(addr_of!((*self.head.as_ptr()).packet_size))),
                u64::from(read_volatile(addr_of!((*self.head.as_ptr()).packet_count))),
                read_volatile(addr_of!((*self.head.as_ptr()).queue_size)),
            )
        }
    }

    /// Capture and validate metadata plus the three monotonic counters.
    pub(crate) fn snapshot(&self) -> Result<QueueSnapshot, QueueError> {
        let (packet_size, packet_count, queue_size) = self.metadata();
        if packet_size == 0
            || packet_size % size_of::<u64>() != 0
            || packet_count < 2
        {
            return Err(QueueError::Corrupt);
        }
        let payload_bytes = packet_size
            .checked_mul(packet_count as usize)
            .ok_or(QueueError::Corrupt)?;
        let required = size_of::<IhkIkcQueueHead>()
            .checked_add(payload_bytes)
            .ok_or(QueueError::Corrupt)?;
        if queue_size != payload_bytes as u64 || required > self.mapping_bytes {
            return Err(QueueError::Corrupt);
        }

        // The three counters are independently atomic. Take a stable bracket
        // around the publication load so a concurrently advancing consumer or
        // producer cannot manufacture an impossible mixed-generation view.
        let (read, published, reserved) = loop {
            let read_before = self.read_counter().load(Ordering::Acquire);
            let reserved_before = self.write_counter().load(Ordering::Acquire);
            let published = self.publish_counter().load(Ordering::Acquire);
            let reserved_after = self.write_counter().load(Ordering::Acquire);
            let read_after = self.read_counter().load(Ordering::Acquire);
            if read_before == read_after && reserved_before == reserved_after {
                break (read_before, published, reserved_before);
            }
            spin_loop();
        };
        let reserved_distance = reserved.wrapping_sub(read);
        let published_distance = published.wrapping_sub(read);
        if reserved_distance >= packet_count
            || published_distance > reserved_distance
        {
            return Err(QueueError::Corrupt);
        }
        Ok(QueueSnapshot {
            packet_size,
            packet_count,
            read,
            published,
            reserved,
        })
    }

    pub(crate) fn is_empty(&self) -> Result<bool, QueueError> {
        let state = self.snapshot()?;
        Ok(state.read == state.published)
    }

    pub(crate) fn is_full(&self) -> Result<bool, QueueError> {
        let state = self.snapshot()?;
        Ok(state.reserved.wrapping_sub(state.read) == state.packet_count - 1)
    }

    #[inline]
    fn packet_pointer(&self, sequence: u64, state: QueueSnapshot) -> *mut u8 {
        let slot = sequence % state.packet_count;
        let offset = size_of::<IhkIkcQueueHead>() + slot as usize * state.packet_size;
        // Pointer arithmetic is deferred to the copy sites, after `snapshot`
        // proved the complete slot lies inside the mapping.
        self.head.as_ptr().cast::<u8>().wrapping_add(offset)
    }

    fn overlaps_mapping(&self, pointer: *const u8, bytes: usize) -> bool {
        let mapping_start = self.head.as_ptr() as usize;
        // `attach` rejected an overflowing mapped range.
        let mapping_end = mapping_start + self.mapping_bytes;
        let start = pointer as usize;
        let Some(end) = start.checked_add(bytes) else {
            return true;
        };
        start < mapping_end && mapping_start < end
    }

    /// Reserve, copy, and publish one packet without allocation.
    ///
    /// Once reservation succeeds, the calling kernel context must not sleep,
    /// unwind, or allow a same-CPU queue producer to interrupt it before this
    /// method publishes. A later producer intentionally waits for that ordered
    /// publication, matching the legacy IRQ-disabled protocol.
    pub(crate) fn try_enqueue(&self, packet: &[u8]) -> Result<(), QueueError> {
        let mut full_attempts = 0_usize;
        loop {
            let state = self.snapshot()?;
            if packet.len() < state.packet_size {
                return Err(QueueError::Invalid);
            }
            if self.overlaps_mapping(packet.as_ptr(), state.packet_size) {
                return Err(QueueError::Invalid);
            }
            if state.reserved.wrapping_sub(state.read) == state.packet_count - 1 {
                full_attempts += 1;
                if full_attempts > LEGACY_WRITE_QUEUE_RETRY {
                    return Err(QueueError::Full);
                }
                spin_loop();
                continue;
            }
            if self
                .write_counter()
                .compare_exchange_weak(
                    state.reserved,
                    state.reserved.wrapping_add(1),
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .is_err()
            {
                spin_loop();
                continue;
            }

            let destination = self.packet_pointer(state.reserved, state);
            // SAFETY: `snapshot` proved the destination slot is wholly mapped;
            // the reservation gives this producer exclusive access to it and
            // the source slice was checked to contain `packet_size` bytes.
            // Mapping overlap was rejected above. `copy` is used only as a
            // raw-byte transfer between the disjoint packet and queue slot.
            unsafe {
                copy(packet.as_ptr(), destination, state.packet_size);
            }

            loop {
                let current = self.publish_counter().load(Ordering::Acquire);
                if current == state.reserved {
                    if self
                        .publish_counter()
                        .compare_exchange_weak(
                            current,
                            current.wrapping_add(1),
                            Ordering::Release,
                            Ordering::Acquire,
                        )
                        .is_ok()
                    {
                        return Ok(());
                    }
                } else if state.reserved.wrapping_sub(current) >= state.packet_count {
                    return Err(QueueError::Corrupt);
                }
                spin_loop();
            }
        }
    }

    /// Claim and copy one published packet.
    pub(crate) fn try_dequeue(&self, packet: &mut [u8]) -> Result<(), QueueError> {
        // The wire format has no separate claim counter. Serialize local
        // consumers so `read_offset` can remain unchanged until the packet is
        // completely copied; this prevents producers from wrapping onto the
        // slot during a speculative losing-consumer copy.
        let claim = self
            .consumer_active
            .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
            .map(|_| ConsumerClaim(&self.consumer_active))
            .map_err(|_| QueueError::Busy)?;
        loop {
            let state = self.snapshot()?;
            if packet.len() < state.packet_size {
                return Err(QueueError::Invalid);
            }
            if self.overlaps_mapping(packet.as_ptr(), state.packet_size) {
                return Err(QueueError::Invalid);
            }
            if state.read == state.published {
                return Err(QueueError::Empty);
            }
            let source = self.packet_pointer(state.read, state);
            // Copy before advancing `read_offset`: the producer is forbidden
            // from reusing this slot while that counter still names it. The
            // process-local claim above excludes another Rust consumer from
            // copying or advancing this queue concurrently.
            // SAFETY: `snapshot` proved the source slot is wholly mapped, its
            // acquire load observed release publication, and the destination
            // slice is large enough. Mapping overlap was rejected above, so
            // `copy` is only a raw-byte transfer between disjoint regions.
            unsafe {
                copy(source, packet.as_mut_ptr(), state.packet_size);
            }
            if self
                .read_counter()
                .compare_exchange_weak(
                    state.read,
                    state.read.wrapping_add(1),
                    Ordering::Release,
                    Ordering::Acquire,
                )
                .is_ok()
            {
                drop(claim);
                return Ok(());
            }
            spin_loop();
        }
    }
}

#[cfg(test)]
mod internal_tests {
    use super::*;

    #[repr(C, align(64))]
    struct Storage([u8; 320]);

    #[test]
    fn consumer_claim_is_exclusive_and_released_on_every_error() {
        let mut storage = Storage([0; 320]);
        let queue = SharedQueue::initialize(&mut storage.0, 1, 2, 64).unwrap();

        queue.consumer_active.store(true, Ordering::Relaxed);
        assert_eq!(queue.try_dequeue(&mut [0; 64]), Err(QueueError::Busy));
        assert!(queue.consumer_active.load(Ordering::Relaxed));
        queue.consumer_active.store(false, Ordering::Relaxed);

        assert_eq!(queue.try_dequeue(&mut [0; 64]), Err(QueueError::Empty));
        assert!(!queue.consumer_active.load(Ordering::Relaxed));

        queue.try_enqueue(&[0; 64]).unwrap();
        assert_eq!(queue.try_dequeue(&mut [0; 63]), Err(QueueError::Invalid));
        assert!(!queue.consumer_active.load(Ordering::Relaxed));
        queue.try_dequeue(&mut [0; 64]).unwrap();

        let read = queue.read_counter().load(Ordering::Relaxed);
        queue
            .write_counter()
            .store(read.wrapping_add(4), Ordering::Relaxed);
        assert_eq!(queue.try_dequeue(&mut [0; 64]), Err(QueueError::Corrupt));
        assert!(!queue.consumer_active.load(Ordering::Relaxed));
    }
}
