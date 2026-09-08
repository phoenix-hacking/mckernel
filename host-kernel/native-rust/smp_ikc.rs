// SPDX-License-Identifier: GPL-2.0
//! Native master and regular queue endpoints for the owned boot service.
//!
//! IRQ callbacks signal work in retained shared queues. The serialized BOOT
//! process consumes packets, allocates channels and sends replies; no callback
//! allocates or recursively acquires the resource mutex held by that process.

use super::{
    abi::{IhkIkcMasterPacket, IhkIkcPacketHeader, IhkIkcQueueHead, IHK_IKC_MASTER_MSG_INIT_ACK},
    ikc_master::{ListenerDirection, ListenerRegistry, ListenerSpec, MasterError},
    ikc_queue::{QueueError, SharedProducer, SharedQueue},
    smp_resource::OsToken,
};
use core::{
    ptr,
    sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering},
};
use kernel::{bindings, prelude::*};

pub(super) const CONTROL_QUEUE_BYTES: usize = 4 * 4096;
pub(super) const CONTROL_PACKET_BYTES: usize = 128;
const _: () = assert!(core::mem::size_of::<super::abi::IkcScdPacket>() == CONTROL_PACKET_BYTES);
const _: () = assert!(core::mem::offset_of!(super::abi::IkcScdPacket, message) == 8);
const _: () = assert!(core::mem::offset_of!(super::abi::IkcScdPacket, payload) == 24);
static LISTENERS: ListenerRegistry = ListenerRegistry::new();

pub(super) fn master_error(error: MasterError) -> Error {
    kernel::error::to_result(error.legacy_status())
        .err()
        .unwrap_or(EIO)
}

fn queue_error(error: QueueError) -> Error {
    kernel::error::to_result(error.legacy_status())
        .err()
        .unwrap_or(EIO)
}

/// Called once during module initialization, before the control device exists.
/// Registrations stay immutable until module removal, which active OSes veto.
/// The owner identifies this module's service; channels also retain OsToken.
pub(super) fn initialize_listeners() -> Result {
    for (port, magic, direction) in [
        (501, 0x1329, ListenerDirection::Send),
        (503, 0x1129, ListenerDirection::Receive),
    ] {
        let spec = ListenerSpec::try_new(
            port,
            CONTROL_PACKET_BYTES as u32,
            CONTROL_QUEUE_BYTES as u64,
            magic,
            direction,
            1,
        )
        .map_err(master_error)?;
        LISTENERS.register(spec).map_err(master_error)?;
    }
    Ok(())
}

pub(super) fn listeners() -> &'static ListenerRegistry {
    &LISTENERS
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

pub(super) fn notify(cpu: u32) -> Result {
    validate_apic()?;
    let mut mask = bindings::cpumask::default();
    let word = cpu as usize / 64;
    if word >= mask.bits.len() {
        return Err(EINVAL);
    }
    mask.bits[word] = 1 << (cpu % 64);
    // SAFETY: The caller holds the exact assigned offline CPU's device and
    // topology guards. Linux saves/restores IRQs and uses its retained hardware
    // identity. This is the unchanged physical-destination mask entry.
    unsafe { bindings::__SCT__apic_call_send_IPI_mask(&mask, 0xd1) };
    Ok(())
}

struct ProducerClaim<'queue>(&'queue AtomicBool);
impl Drop for ProducerClaim<'_> {
    fn drop(&mut self) {
        self.0.store(false, Ordering::Release);
    }
}

/// Exactly one local sender may reserve at a time. An interrupting sender
/// returns EBUSY instead of waiting behind the producer that it interrupted.
struct OutboundQueue {
    queue: SharedProducer<'static>,
    active: AtomicBool,
}

impl OutboundQueue {
    // SAFETY: The owner supplies retained, disjoint revision-2 peer storage,
    // immutable metadata and no Rust aliases. This is its sole host producer.
    unsafe fn attach(head: *mut IhkIkcQueueHead, bytes: usize, packet_size: usize) -> Result<Self> {
        // SAFETY: The caller transfers the checked peer mapping/protocol above.
        let queue = unsafe { SharedProducer::attach(head, bytes) }.map_err(queue_error)?;
        let state = queue.snapshot().map_err(queue_error)?;
        if state.packet_size != packet_size
            || state.packet_count as usize
                != (bytes - core::mem::size_of::<IhkIkcQueueHead>()) / packet_size
            || state.read != 0
            || state.published != 0
            || state.reserved != 0
        {
            return Err(EIO);
        }
        Ok(Self {
            queue,
            active: AtomicBool::new(false),
        })
    }

    fn send(&self, packet: &[u8]) -> Result {
        self.active
            .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
            .map_err(|_| EBUSY)?;
        let _claim = ProducerClaim(&self.active);
        // No allocation, sleeping or other producer can intervene in this
        // reservation/publication sequence. Same-CPU reentry fails above.
        self.queue.try_enqueue(packet).map_err(queue_error)
    }
}

pub(super) struct BootMaster {
    owner: OsToken,
    receive: SharedQueue<'static>,
    send: OutboundQueue,
    ack_claimed: AtomicBool,
    pending: AtomicBool,
    packets: AtomicU64,
    error: AtomicI32,
}

impl BootMaster {
    // SAFETY: Both disjoint page-aligned mappings belong to this exact started
    // generation and stay live permanently. The guest note selected revision 2.
    // Metadata is immutable after status 2, no Rust references alias storage,
    // and these are the sole host endpoints for their respective queues.
    pub(super) unsafe fn new(
        owner: OsToken,
        receive: *mut IhkIkcQueueHead,
        send: *mut IhkIkcQueueHead,
        mapping_bytes: usize,
    ) -> Result<Self> {
        if receive == send || mapping_bytes < 4096 {
            return Err(EINVAL);
        }
        // SAFETY: The caller transfers the checked sole-consumer mapping.
        let receive =
            unsafe { SharedQueue::attach(receive, mapping_bytes) }.map_err(queue_error)?;
        let state = receive.snapshot().map_err(queue_error)?;
        if state.packet_size != 56 || state.read != 0 || state.published != 0 || state.reserved != 0
        {
            return Err(EIO);
        }
        // SAFETY: The same owner supplies the disjoint revision-2 send mapping.
        let send = unsafe { OutboundQueue::attach(send, mapping_bytes, 56)? };
        Ok(Self {
            owner,
            receive,
            send,
            ack_claimed: AtomicBool::new(false),
            pending: AtomicBool::new(false),
            packets: AtomicU64::new(0),
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
        self.send_packet(
            cpu,
            &IhkIkcMasterPacket {
                header: IhkIkcPacketHeader {
                    channel: ptr::null_mut(),
                },
                message: IHK_IKC_MASTER_MSG_INIT_ACK,
                reference: 0,
                parameters: [0; 5],
            },
        )
    }

    pub(super) fn send_packet(&self, cpu: u32, packet: &IhkIkcMasterPacket) -> Result {
        self.publish(&Self::encode(packet))?;
        notify(cpu)
    }

    pub(super) fn encode(packet: &IhkIkcMasterPacket) -> [u8; 56] {
        let mut bytes = [0u8; 56];
        bytes[8..12].copy_from_slice(&packet.message.to_le_bytes());
        bytes[12..16].copy_from_slice(&packet.reference.to_le_bytes());
        for (index, value) in packet.parameters.iter().enumerate() {
            bytes[16 + index * 8..24 + index * 8].copy_from_slice(&value.to_le_bytes());
        }
        bytes
    }

    /// An error means nothing was published. Notify only after success, and
    /// never retry a publication merely because its later notification failed.
    pub(super) fn publish(&self, packet: &[u8; 56]) -> Result {
        self.send.send(packet)
    }

    /// Hard IRQ: only an atomic notification; packets stay in their owned ring.
    pub(super) fn interrupt(&self) {
        self.pending.store(true, Ordering::Release);
    }

    pub(super) fn take_notification(&self) -> bool {
        self.pending.swap(false, Ordering::Acquire)
    }
    pub(super) fn packets(&self) -> u64 {
        self.packets.load(Ordering::Acquire)
    }
    pub(super) fn error(&self) -> i32 {
        self.error.load(Ordering::Acquire)
    }

    /// Process context only. The BOOT service bounds each drain and retains all
    /// resource guards. No remote header cookie is dereferenced or borrowed.
    pub(super) fn next_packet(&self) -> Result<Option<IhkIkcMasterPacket>> {
        let mut bytes = [0u8; 56];
        match self.receive.try_dequeue(&mut bytes) {
            Ok(()) => {}
            Err(QueueError::Empty | QueueError::Busy) => return Ok(None),
            Err(error) => {
                self.error.store(error.legacy_status(), Ordering::Release);
                return Err(queue_error(error));
            }
        }
        self.packets.fetch_add(1, Ordering::Release);
        Ok(Some(IhkIkcMasterPacket {
            header: IhkIkcPacketHeader {
                channel: ptr::null_mut(),
            },
            message: u32::from_le_bytes(bytes[8..12].try_into().unwrap()),
            reference: u32::from_le_bytes(bytes[12..16].try_into().unwrap()),
            parameters: core::array::from_fn(|index| {
                u64::from_le_bytes(bytes[16 + index * 8..24 + index * 8].try_into().unwrap())
            }),
        }))
    }
}

/// Endpoint metadata may move, while both underlying page allocations remain
/// stable. Its containing owner retires this view before freeing private pages,
/// or retains both permanently before publishing a successful CONNECT_REPLY.
pub(super) struct ControlChannel {
    pub(super) owner: OsToken,
    pub(super) cookie: u64,
    pub(super) port: i32,
    pub(super) guest_cpu: u32,
    pub(super) receive_physical: u64,
    pub(super) send_physical: u64,
    receive: SharedQueue<'static>,
    send: OutboundQueue,
    pub(super) received: u64,
    pub(super) first: Option<[u8; CONTROL_PACKET_BYTES]>,
}

impl ControlChannel {
    // SAFETY: The adapter owns both complete disjoint mappings and their
    // metadata publication, and retains them for every exposed endpoint use.
    // Only this value consumes receive or sends through the revision-2 peer.
    pub(super) unsafe fn new(
        owner: OsToken,
        cookie: u64,
        port: i32,
        guest_cpu: u32,
        receive_physical: u64,
        send_physical: u64,
        receive: *mut IhkIkcQueueHead,
        send: *mut IhkIkcQueueHead,
    ) -> Result<Self> {
        // SAFETY: The caller provides private initialized receive storage.
        let receive =
            unsafe { SharedQueue::attach(receive, CONTROL_QUEUE_BYTES) }.map_err(queue_error)?;
        let state = receive.snapshot().map_err(queue_error)?;
        if state.packet_size != CONTROL_PACKET_BYTES
            || state.read != 0
            || state.published != 0
            || state.reserved != 0
        {
            return Err(EIO);
        }
        // SAFETY: The caller supplies the checked revision-2 guest queue.
        let send =
            unsafe { OutboundQueue::attach(send, CONTROL_QUEUE_BYTES, CONTROL_PACKET_BYTES)? };
        Ok(Self {
            owner,
            cookie,
            port,
            guest_cpu,
            receive_physical,
            send_physical,
            receive,
            send,
            received: 0,
            first: None,
        })
    }

    pub(super) fn next_packet(&mut self) -> Result<Option<[u8; CONTROL_PACKET_BYTES]>> {
        let mut packet = [0u8; CONTROL_PACKET_BYTES];
        match self.receive.try_dequeue(&mut packet) {
            Ok(()) => {}
            Err(QueueError::Empty | QueueError::Busy) => return Ok(None),
            Err(error) => return Err(queue_error(error)),
        }
        if self.first.is_none() {
            self.first = Some(packet);
        }
        self.received += 1;
        Ok(Some(packet))
    }

    /// Sole host producer. The exchange lock must span publication and its
    /// Published transition; the CPU notification follows outside that lock.
    pub(super) fn publish(&self, packet: &[u8; CONTROL_PACKET_BYTES]) -> Result {
        self.send.send(packet)
    }
}
