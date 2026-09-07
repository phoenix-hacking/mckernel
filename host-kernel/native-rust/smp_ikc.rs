// SPDX-License-Identifier: GPL-2.0
//! Initial native master exchange using the existing shared queue primitive.
//!
//! Started boot storage retains both mappings and this stable callback target.
//! Listener effects and repeated outbound packet support remain separate work.

use super::{
    abi::{IhkIkcMasterPacket, IhkIkcPacketHeader, IhkIkcQueueHead, IHK_IKC_MASTER_MSG_INIT_ACK},
    ikc_master::ConnectOffer,
    ikc_queue::{QueueError, SharedQueue},
    smp_resource::OsToken,
};
use core::{
    ptr,
    sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering},
};
use kernel::{bindings, prelude::*};

fn queue_error(error: QueueError) -> Error {
    kernel::error::to_result(error.legacy_status())
        .err()
        .unwrap_or(EIO)
}

/// Reject logical routing: the guest owns its APIC state after INIT/SIPI.
pub(super) fn validate_apic() -> Result {
    // SAFETY: Linux initializes this permanent read-only driver before module
    // loading. Bindgen generated the exact header and bitfield accessors.
    let driver = unsafe { bindings::apic };
    if driver.is_null() || unsafe { bindings::apic::dest_mode_logical_raw(driver) } != 0 {
        return Err(ENODEV);
    }
    Ok(())
}

fn notify(cpu: u32) -> Result {
    validate_apic()?;
    let mut mask = bindings::cpumask::default();
    let word = cpu as usize / 64;
    if word >= mask.bits.len() {
        return Err(EINVAL);
    }
    mask.bits[word] = 1 << (cpu % 64);
    // SAFETY: The caller holds the exact assigned offline CPU's device and
    // topology guards. This is Linux's existing physical-destination mask API;
    // it saves/restores IRQs and uses the retained per-CPU hardware identity.
    unsafe { bindings::__SCT__apic_call_send_IPI_mask(&mask, 0xd1) };
    Ok(())
}

pub(super) struct BootMaster {
    owner: OsToken,
    receive: SharedQueue<'static>,
    send: *mut IhkIkcQueueHead,
    mapping_bytes: usize,
    ack_claimed: AtomicBool,
    packets: AtomicU64,
    first: [AtomicU64; 7],
    error: AtomicI32,
}

// SAFETY: The started owner permanently retains these mappings. Atomic queue
// operations serialize consumption, and only the initial producer writes send.
unsafe impl Send for BootMaster {}
// SAFETY: Shared mutation uses atomics. The first packet becomes immutable
// before packets is release-published; the sole Linux target serializes IRQs.
unsafe impl Sync for BootMaster {}

impl BootMaster {
    // SAFETY: Both disjoint page-aligned queue mappings belong to this exact
    // started OS generation and remain live permanently. Their peer metadata
    // is immutable after status 2. Linux is the sole receive consumer and sole
    // initial send producer, with no aliased Rust storage references.
    pub(super) unsafe fn new(
        owner: OsToken,
        receive: *mut IhkIkcQueueHead,
        send: *mut IhkIkcQueueHead,
        mapping_bytes: usize,
    ) -> Result<Self> {
        if receive == send || send.is_null() || mapping_bytes < 4096 {
            return Err(EINVAL);
        }
        // SAFETY: The caller proved this entire queue mapping. These metadata
        // fields are immutable after architecture readiness; no reference to
        // shared packet or header storage is manufactured.
        let send_packet_size = unsafe { ptr::read_volatile(ptr::addr_of!((*send).packet_size)) };
        if send_packet_size != 56 {
            return Err(EIO);
        }
        // SAFETY: The caller transfers the sole receive endpoint of retained
        // shared storage, with the exact mapping and peer protocol above.
        let receive =
            unsafe { SharedQueue::attach(receive, mapping_bytes) }.map_err(queue_error)?;
        let snapshot = receive.snapshot().map_err(queue_error)?;
        if snapshot.packet_size != 56
            || snapshot.read != 0
            || snapshot.published != 0
            || snapshot.reserved != 0
        {
            return Err(EIO);
        }
        Ok(Self {
            owner,
            receive,
            send,
            mapping_bytes,
            ack_claimed: AtomicBool::new(false),
            packets: AtomicU64::new(0),
            first: [const { AtomicU64::new(0) }; 7],
            error: AtomicI32::new(0),
        })
    }

    pub(super) fn owner(&self) -> OsToken {
        self.owner
    }

    pub(super) fn send_initial_ack(&self, cpu: u32) -> Result {
        self.ack_claimed
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| EBUSY)?;
        let mut packet = [0_u8; 56];
        packet[8..12].copy_from_slice(&IHK_IKC_MASTER_MSG_INIT_ACK.to_le_bytes());
        // SAFETY: ack_claimed permits exactly one producer call. This owner
        // never resets the queue or reuses a slot, including after consumption.
        unsafe { SharedQueue::publish_initial(self.send, self.mapping_bytes, &packet) }
            .map_err(queue_error)?;
        notify(cpu)
    }

    /// Hard IRQ only: no allocations, resource mutexes, listener effects or IPI.
    pub(super) fn interrupt(&self) {
        for _ in 0..16 {
            let mut packet = [0_u8; 56];
            match self.receive.try_dequeue(&mut packet) {
                Ok(()) => {
                    if self.packets.load(Ordering::Relaxed) == 0 {
                        for (index, word) in packet.chunks_exact(8).enumerate() {
                            self.first[index].store(
                                u64::from_le_bytes(word.try_into().unwrap()),
                                Ordering::Relaxed,
                            );
                        }
                    }
                    self.packets.fetch_add(1, Ordering::Release);
                }
                Err(QueueError::Empty | QueueError::Busy) => break,
                Err(error) => {
                    self.error.store(error.legacy_status(), Ordering::Release);
                    break;
                }
            }
        }
    }

    pub(super) fn packets(&self) -> u64 {
        self.packets.load(Ordering::Acquire)
    }
    pub(super) fn error(&self) -> i32 {
        self.error.load(Ordering::Acquire)
    }

    pub(super) fn first_connect(&self) -> Result<ConnectOffer> {
        if self.packets() == 0 {
            return Err(EAGAIN);
        }
        let words: [u64; 7] =
            core::array::from_fn(|index| self.first[index].load(Ordering::Relaxed));
        // The remote header cookie is intentionally ignored, never dereferenced.
        let packet = IhkIkcMasterPacket {
            header: IhkIkcPacketHeader {
                channel: ptr::null_mut(),
            },
            message: words[1] as u32,
            reference: (words[1] >> 32) as u32,
            parameters: [words[2], words[3], words[4], words[5], words[6]],
        };
        ConnectOffer::decode(&packet).map_err(|_| EIO)
    }
}
