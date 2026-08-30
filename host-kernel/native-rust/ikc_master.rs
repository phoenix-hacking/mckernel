// SPDX-License-Identifier: GPL-2.0
//! Allocation-free IKC master/listener protocol substrate.
//!
//! This module deliberately stops at typed state transitions. It never maps a
//! queue, allocates or frees a channel, invokes a listener, sends a packet,
//! wakes a waiter, or sleeps. A later kernel adapter must perform those
//! effects in the execution context carried by each returned action.

use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};

use super::abi::{
    IHK_IKC_MASTER_MSG_CONNECT, IHK_IKC_MASTER_MSG_CONNECT_REPLY,
    IHK_IKC_MASTER_MSG_DISCONNECT, IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL,
    IHK_IKC_MAX_PORT, IKC_FLAG_DESTROY_ACKED, IKC_FLAG_DESTROYING,
    IKC_FLAG_ENABLED, IhkIkcMasterPacket, IhkIkcPacketHeader,
};

const ENOENT: i32 = 2;
const EINTR: i32 = 4;
const ENOMEM: i32 = 12;
const EBUSY: i32 = 16;
const EINVAL: i32 = 22;
const EPROTO: i32 = 71;
const ECONNABORTED: i32 = 103;
const ECONNREFUSED: i32 = 111;
const ESTALE: i32 = 116;

const SLOT_EMPTY: u64 = 0;
const SLOT_REGISTERING: u64 = 1;
const SLOT_ACTIVE: u64 = 2;
const SLOT_DRAINING: u64 = 3;
const SLOT_PHASE_MASK: u64 = 3;
const MAX_GENERATION: u64 = u64::MAX >> 2;

/// The legacy receive path runs directly from its interrupt handler, while
/// connect/disconnect callers may block in process context.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ExecutionContext {
    Interrupt,
    Process,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum MasterError {
    Invalid,
    Busy,
    NoEntry,
    NoMemory,
    ConnectionAborted,
    ConnectionRefused,
    Interrupted,
    Protocol,
    Stale,
}

impl MasterError {
    pub(crate) const fn legacy_status(self) -> i32 {
        match self {
            Self::Invalid => -EINVAL,
            Self::Busy => -EBUSY,
            Self::NoEntry => -ENOENT,
            Self::NoMemory => -ENOMEM,
            Self::ConnectionAborted => -ECONNABORTED,
            Self::ConnectionRefused => -ECONNREFUSED,
            Self::Interrupted => -EINTR,
            Self::Protocol => -EPROTO,
            Self::Stale => -ESTALE,
        }
    }

    const fn reply_errno(self) -> u32 {
        (-self.legacy_status()) as u32
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ListenerDirection {
    Send,
    Receive,
}

/// Immutable registration metadata. `owner` is an adapter-owned opaque ID,
/// never a pointer that this substrate dereferences.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ListenerSpec {
    pub(crate) port: u16,
    pub(crate) packet_size: u32,
    pub(crate) queue_size: u64,
    pub(crate) magic: i32,
    pub(crate) direction: ListenerDirection,
    pub(crate) owner: u64,
}

impl ListenerSpec {
    pub(crate) fn try_new(
        port: i32,
        packet_size: u32,
        queue_size: u64,
        magic: i32,
        direction: ListenerDirection,
        owner: u64,
    ) -> Result<Self, MasterError> {
        if port < 0
            || port as u32 >= IHK_IKC_MAX_PORT
            || packet_size == 0
            || queue_size == 0
            || owner == 0
        {
            return Err(MasterError::Invalid);
        }
        Ok(Self {
            port: port as u16,
            packet_size,
            queue_size,
            magic,
            direction,
            owner,
        })
    }
}

/// Generation-qualified registration identity; stale users cannot address a
/// later listener that reused the same port.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ListenerToken {
    pub(crate) port: u16,
    pub(crate) generation: u64,
}

struct ListenerSlot {
    control: AtomicU64,
    readers: AtomicU32,
    packet_size: AtomicU32,
    queue_size: AtomicU64,
    magic: AtomicU32,
    direction: AtomicU32,
    owner: AtomicU64,
}

impl ListenerSlot {
    const fn new() -> Self {
        Self {
            control: AtomicU64::new(SLOT_EMPTY),
            readers: AtomicU32::new(0),
            packet_size: AtomicU32::new(0),
            queue_size: AtomicU64::new(0),
            magic: AtomicU32::new(0),
            direction: AtomicU32::new(0),
            owner: AtomicU64::new(0),
        }
    }

    fn snapshot(&self, port: u16) -> ListenerSpec {
        ListenerSpec {
            port,
            packet_size: self.packet_size.load(Ordering::Relaxed),
            queue_size: self.queue_size.load(Ordering::Relaxed),
            magic: self.magic.load(Ordering::Relaxed) as i32,
            direction: if self.direction.load(Ordering::Relaxed) == 0 {
                ListenerDirection::Send
            } else {
                ListenerDirection::Receive
            },
            owner: self.owner.load(Ordering::Relaxed),
        }
    }

    fn clear(&self) {
        self.packet_size.store(0, Ordering::Relaxed);
        self.queue_size.store(0, Ordering::Relaxed);
        self.magic.store(0, Ordering::Relaxed);
        self.direction.store(0, Ordering::Relaxed);
        self.owner.store(0, Ordering::Relaxed);
    }
}

const fn pack_control(generation: u64, phase: u64) -> u64 {
    (generation << 2) | phase
}

const fn control_generation(control: u64) -> u64 {
    control >> 2
}

const fn next_generation(current: u64) -> u64 {
    let next = (current + 1) & MAX_GENERATION;
    if next == 0 { 1 } else { next }
}

/// Result of the two-phase explicit unregister operation.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum UnregisterState {
    Pending,
    Removed,
}

/// Fixed-capacity listener table. The native integration instantiates 512
/// slots, matching the frozen legacy table exactly.
pub(crate) struct ListenerRegistry<const N: usize = { IHK_IKC_MAX_PORT as usize }> {
    slots: [ListenerSlot; N],
}

impl<const N: usize> ListenerRegistry<N> {
    pub(crate) const fn new() -> Self {
        Self {
            slots: [const { ListenerSlot::new() }; N],
        }
    }

    fn slot(&self, port: i32) -> Result<(u16, &ListenerSlot), MasterError> {
        if port < 0 || port as u32 >= IHK_IKC_MAX_PORT || port as usize >= N {
            return Err(MasterError::Invalid);
        }
        Ok((port as u16, &self.slots[port as usize]))
    }

    pub(crate) fn register(&self, spec: ListenerSpec) -> Result<ListenerToken, MasterError> {
        if spec.packet_size == 0 || spec.queue_size == 0 || spec.owner == 0 {
            return Err(MasterError::Invalid);
        }
        let (port, slot) = self.slot(i32::from(spec.port))?;
        let observed = slot.control.load(Ordering::Acquire);
        if observed & SLOT_PHASE_MASK != SLOT_EMPTY {
            return Err(MasterError::Busy);
        }
        let generation = next_generation(control_generation(observed));
        let registering = pack_control(generation, SLOT_REGISTERING);
        slot.control
            .compare_exchange(observed, registering, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| MasterError::Busy)?;

        // An acquisition that observed the preceding generation may briefly
        // increment `readers` after EMPTY was published. Its control recheck
        // cannot match this generation, so it never snapshots these fields.
        slot.packet_size.store(spec.packet_size, Ordering::Relaxed);
        slot.queue_size.store(spec.queue_size, Ordering::Relaxed);
        slot.magic.store(spec.magic as u32, Ordering::Relaxed);
        slot.direction.store(
            u32::from(spec.direction == ListenerDirection::Receive),
            Ordering::Relaxed,
        );
        slot.owner.store(spec.owner, Ordering::Relaxed);
        slot.control
            .store(pack_control(generation, SLOT_ACTIVE), Ordering::Release);
        Ok(ListenerToken { port, generation })
    }

    pub(crate) fn acquire(&self, port: i32) -> Result<ListenerLease<'_>, MasterError> {
        let (port, slot) = self.slot(port)?;
        loop {
            let control = slot.control.load(Ordering::Acquire);
            if control & SLOT_PHASE_MASK != SLOT_ACTIVE {
                return Err(MasterError::NoEntry);
            }
            let prior = slot.readers.fetch_add(1, Ordering::AcqRel);
            if prior == u32::MAX {
                slot.readers.fetch_sub(1, Ordering::Release);
                return Err(MasterError::Busy);
            }
            if slot.control.load(Ordering::Acquire) == control {
                return Ok(ListenerLease {
                    slot,
                    token: ListenerToken {
                        port,
                        generation: control_generation(control),
                    },
                    spec: slot.snapshot(port),
                });
            }
            slot.readers.fetch_sub(1, Ordering::Release);
        }
    }

    pub(crate) fn begin_unregister(
        &self,
        token: ListenerToken,
    ) -> Result<UnregisterState, MasterError> {
        let (_, slot) = self.slot(i32::from(token.port))?;
        let active = pack_control(token.generation, SLOT_ACTIVE);
        let draining = pack_control(token.generation, SLOT_DRAINING);
        match slot
            .control
            .compare_exchange(active, draining, Ordering::AcqRel, Ordering::Acquire)
        {
            Ok(_) => self.finish_draining(slot, token.generation),
            Err(current) if current == draining => self.finish_draining(slot, token.generation),
            Err(current) if current == pack_control(token.generation, SLOT_REGISTERING) => {
                Ok(UnregisterState::Pending)
            }
            Err(_) => Err(MasterError::Stale),
        }
    }

    pub(crate) fn finish_unregister(
        &self,
        token: ListenerToken,
    ) -> Result<UnregisterState, MasterError> {
        let (_, slot) = self.slot(i32::from(token.port))?;
        let draining = pack_control(token.generation, SLOT_DRAINING);
        match slot.control.load(Ordering::Acquire) {
            current if current == draining => {}
            current if current == pack_control(token.generation, SLOT_REGISTERING) => {
                return Ok(UnregisterState::Pending);
            }
            _ => return Err(MasterError::Stale),
        }
        self.finish_draining(slot, token.generation)
    }

    fn finish_draining(
        &self,
        slot: &ListenerSlot,
        generation: u64,
    ) -> Result<UnregisterState, MasterError> {
        if slot.readers.load(Ordering::Acquire) != 0 {
            return Ok(UnregisterState::Pending);
        }
        let draining = pack_control(generation, SLOT_DRAINING);
        let finalizing = pack_control(generation, SLOT_REGISTERING);
        match slot.control.compare_exchange(
            draining,
            finalizing,
            Ordering::AcqRel,
            Ordering::Acquire,
        ) {
            Ok(_) => {}
            Err(current) if current == finalizing => return Ok(UnregisterState::Pending),
            Err(_) => return Err(MasterError::Stale),
        }
        // A speculative acquire may have incremented after the first load but
        // cannot validate against FINALIZING. Let it retire before clearing.
        if slot.readers.load(Ordering::Acquire) != 0 {
            slot.control.store(draining, Ordering::Release);
            return Ok(UnregisterState::Pending);
        }
        slot.clear();
        slot.control
            .store(pack_control(generation, SLOT_EMPTY), Ordering::Release);
        Ok(UnregisterState::Removed)
    }
}

/// An acquire/release lease prevents listener metadata reuse while an adapter
/// performs the accepted operation outside the registry lock.
pub(crate) struct ListenerLease<'registry> {
    slot: &'registry ListenerSlot,
    token: ListenerToken,
    spec: ListenerSpec,
}

impl ListenerLease<'_> {
    pub(crate) const fn token(&self) -> ListenerToken {
        self.token
    }

    pub(crate) const fn spec(&self) -> ListenerSpec {
        self.spec
    }
}

impl Drop for ListenerLease<'_> {
    fn drop(&mut self) {
        let prior = self.slot.readers.fetch_sub(1, Ordering::Release);
        debug_assert!(prior != 0);
    }
}

/// Decoded form of the legacy CONNECT master packet.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ConnectOffer {
    pub(crate) reference: u32,
    pub(crate) port: i32,
    pub(crate) packet_size: u32,
    pub(crate) receive_queue: u64,
    pub(crate) send_queue: u64,
    pub(crate) remote_channel_cookie: u64,
    pub(crate) magic: i32,
    pub(crate) interrupt_cpu: i32,
}

impl ConnectOffer {
    fn decode(packet: &IhkIkcMasterPacket) -> Result<Self, MasterError> {
        if packet.message != IHK_IKC_MASTER_MSG_CONNECT {
            return Err(MasterError::Protocol);
        }
        let packed = packet.parameters[0];
        let port = (packed as u32) as i32;
        if port < 0 || port as u32 >= IHK_IKC_MAX_PORT {
            return Err(MasterError::Invalid);
        }
        Ok(Self {
            reference: packet.reference,
            port,
            packet_size: (packed >> 32) as u32,
            receive_queue: packet.parameters[1],
            send_queue: packet.parameters[2],
            remote_channel_cookie: packet.parameters[3],
            magic: packet.parameters[4] as u32 as i32,
            interrupt_cpu: (packet.parameters[4] >> 32) as u32 as i32,
        })
    }
}

/// Outbound CONNECT fields are packed only after validation. Queue names are
/// from the initiating endpoint: the local send queue is parameter 1 and the
/// local receive queue is parameter 2, matching the frozen legacy sender.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct ConnectRequest {
    reference: u32,
    port: u16,
    packet_size: u32,
    local_send_queue: u64,
    local_receive_queue: u64,
    local_channel_cookie: u64,
    magic: i32,
    interrupt_cpu: i32,
}

impl ConnectRequest {
    pub(crate) fn try_new(
        reference: u32,
        port: i32,
        packet_size: u32,
        local_send_queue: u64,
        local_receive_queue: u64,
        local_channel_cookie: u64,
        magic: i32,
        interrupt_cpu: i32,
    ) -> Result<Self, MasterError> {
        if port < 0
            || port as u32 >= IHK_IKC_MAX_PORT
            || packet_size == 0
            || local_send_queue == 0
            || local_receive_queue == 0
            || local_channel_cookie == 0
        {
            return Err(MasterError::Invalid);
        }
        Ok(Self {
            reference,
            port: port as u16,
            packet_size,
            local_send_queue,
            local_receive_queue,
            local_channel_cookie,
            magic,
            interrupt_cpu,
        })
    }

    pub(crate) fn master_packet(self) -> IhkIkcMasterPacket {
        IhkIkcMasterPacket {
            header: IhkIkcPacketHeader {
                channel: core::ptr::null_mut(),
            },
            message: IHK_IKC_MASTER_MSG_CONNECT,
            reference: self.reference,
            parameters: [
                (u64::from(self.packet_size) << 32) | u64::from(self.port),
                self.local_send_queue,
                self.local_receive_queue,
                self.local_channel_cookie,
                (u64::from(self.interrupt_cpu as u32) << 32)
                    | u64::from(self.magic as u32),
            ],
        }
    }
}

/// A successful accept result supplied by the later kernel adapter after it
/// allocates/initializes a real channel.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct AcceptSuccess {
    pub(crate) receive_queue: u64,
    pub(crate) accepted_channel_cookie: u64,
}

pub(crate) struct AcceptPlan<'registry> {
    lease: ListenerLease<'registry>,
    offer: ConnectOffer,
}

impl AcceptPlan<'_> {
    pub(crate) const fn listener(&self) -> ListenerSpec {
        self.lease.spec()
    }

    pub(crate) const fn listener_token(&self) -> ListenerToken {
        self.lease.token()
    }

    pub(crate) const fn offer(&self) -> ConnectOffer {
        self.offer
    }

    /// Receive listeners must establish their regular-channel CPU association
    /// before invoking the legacy-equivalent handler.
    pub(crate) const fn regular_channel_cpu(&self) -> Option<i32> {
        match self.lease.spec.direction {
            ListenerDirection::Receive => Some(self.offer.interrupt_cpu),
            ListenerDirection::Send => None,
        }
    }

    /// A negative adapter status is preserved as the positive errno carried by
    /// the legacy reply, including arbitrary listener callback failures.
    pub(crate) fn connect_reply(
        self,
        result: Result<AcceptSuccess, i32>,
    ) -> Result<MasterReply, MasterError> {
        let mut parameters = [0; 5];
        match result {
            Ok(success) => {
                parameters[1] = success.receive_queue;
                parameters[2] = self.offer.remote_channel_cookie;
                parameters[3] = success.accepted_channel_cookie;
            }
            Err(status) => {
                let errno = status.checked_neg().ok_or(MasterError::Protocol)?;
                if errno == 0 {
                    return Err(MasterError::Protocol);
                }
                parameters[0] = u64::try_from(errno).map_err(|_| MasterError::Protocol)?;
            }
        }
        Ok(MasterReply {
            message: IHK_IKC_MASTER_MSG_CONNECT_REPLY,
            reference: self.offer.reference,
            parameters,
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) struct MasterReply {
    pub(crate) message: u32,
    pub(crate) reference: u32,
    pub(crate) parameters: [u64; 5],
}

impl MasterReply {
    pub(crate) fn packet(self) -> IhkIkcMasterPacket {
        IhkIkcMasterPacket {
            header: IhkIkcPacketHeader {
                channel: core::ptr::null_mut(),
            },
            message: self.message,
            reference: self.reference,
            parameters: self.parameters,
        }
    }
}

/// The side effect required after classifying a received master packet. Every
/// decision also requires exactly one packet release by the adapter.
pub(crate) enum RouteAction<'registry> {
    DeliverPacket { channel_cookie: u64 },
    Accept(AcceptPlan<'registry>),
    SendConnectError(MasterReply),
    WakeReply { message: u32, reference: u32 },
    ObserveDisconnect { channel_cookie: u64, reference: u32 },
    Architecture { message: u32 },
    Reject(MasterError),
}

pub(crate) struct RouteDecision<'registry> {
    pub(crate) action: RouteAction<'registry>,
    pub(crate) context: ExecutionContext,
    pub(crate) release_packet: bool,
}

pub(crate) struct MasterRouter<'registry, const N: usize> {
    listeners: &'registry ListenerRegistry<N>,
}

impl<'registry, const N: usize> MasterRouter<'registry, N> {
    pub(crate) const fn new(listeners: &'registry ListenerRegistry<N>) -> Self {
        Self { listeners }
    }

    pub(crate) fn route(
        &self,
        packet: &IhkIkcMasterPacket,
        context: ExecutionContext,
    ) -> RouteDecision<'registry> {
        let action = match packet.message {
            IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL => {
                if packet.parameters[3] == 0 {
                    RouteAction::Reject(MasterError::NoEntry)
                } else {
                    RouteAction::DeliverPacket {
                        channel_cookie: packet.parameters[3],
                    }
                }
            }
            IHK_IKC_MASTER_MSG_CONNECT => match ConnectOffer::decode(packet) {
                Err(error) => RouteAction::SendConnectError(connect_error(packet.reference, error)),
                Ok(offer) => match self.listeners.acquire(offer.port) {
                    Err(_) => RouteAction::SendConnectError(connect_error(
                        packet.reference,
                        MasterError::ConnectionRefused,
                    )),
                    Ok(lease) if lease.spec().magic != offer.magic => {
                        RouteAction::SendConnectError(connect_error(
                            packet.reference,
                            MasterError::ConnectionRefused,
                        ))
                    }
                    Ok(lease) if lease.spec().packet_size != offer.packet_size => {
                        RouteAction::SendConnectError(connect_error(
                            packet.reference,
                            MasterError::ConnectionAborted,
                        ))
                    }
                    Ok(lease) => RouteAction::Accept(AcceptPlan { lease, offer }),
                },
            },
            IHK_IKC_MASTER_MSG_CONNECT_REPLY => RouteAction::WakeReply {
                message: packet.message,
                reference: packet.reference,
            },
            IHK_IKC_MASTER_MSG_DISCONNECT => {
                if packet.parameters[3] == 0 {
                    RouteAction::Reject(MasterError::NoEntry)
                } else {
                    RouteAction::ObserveDisconnect {
                        channel_cookie: packet.parameters[3],
                        reference: packet.reference,
                    }
                }
            }
            message => RouteAction::Architecture { message },
        };
        RouteDecision {
            action,
            context,
            release_packet: true,
        }
    }
}

fn connect_error(reference: u32, error: MasterError) -> MasterReply {
    MasterReply {
        message: IHK_IKC_MASTER_MSG_CONNECT_REPLY,
        reference,
        parameters: [u64::from(error.reply_errno()), 0, 0, 0, 0],
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ConnectPhase {
    Prepared,
    Waiting,
    Connected,
    Failed,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum ConnectAction {
    WaitForReply,
    Cleanup { status: i32 },
    Publish {
        remote_queue: u64,
        echoed_local_cookie: u64,
        remote_channel_cookie: u64,
    },
}

/// Process-context transaction bookkeeping. Wait-list registration, actual
/// blocking, and channel ownership remain adapter responsibilities.
pub(crate) struct ConnectTransaction {
    reference: u32,
    phase: ConnectPhase,
}

impl ConnectTransaction {
    pub(crate) const fn new(reference: u32) -> Self {
        Self {
            reference,
            phase: ConnectPhase::Prepared,
        }
    }

    pub(crate) const fn phase(&self) -> ConnectPhase {
        self.phase
    }

    pub(crate) fn sent(&mut self, send_status: i32) -> Result<ConnectAction, MasterError> {
        if self.phase != ConnectPhase::Prepared {
            return Err(MasterError::Protocol);
        }
        if send_status == 0 {
            self.phase = ConnectPhase::Waiting;
            Ok(ConnectAction::WaitForReply)
        } else {
            self.phase = ConnectPhase::Failed;
            Ok(ConnectAction::Cleanup {
                status: MasterError::Busy.legacy_status(),
            })
        }
    }

    pub(crate) fn interrupted(&mut self) -> Result<ConnectAction, MasterError> {
        if self.phase != ConnectPhase::Waiting {
            return Err(MasterError::Protocol);
        }
        self.phase = ConnectPhase::Failed;
        Ok(ConnectAction::Cleanup {
            status: MasterError::Interrupted.legacy_status(),
        })
    }

    pub(crate) fn reply(
        &mut self,
        packet: &IhkIkcMasterPacket,
    ) -> Result<ConnectAction, MasterError> {
        if self.phase != ConnectPhase::Waiting
            || packet.message != IHK_IKC_MASTER_MSG_CONNECT_REPLY
            || packet.reference != self.reference
        {
            return Err(MasterError::Protocol);
        }
        let result = packet.parameters[0];
        if result != 0 {
            let errno = i32::try_from(result).map_err(|_| MasterError::Protocol)?;
            self.phase = ConnectPhase::Failed;
            return Ok(ConnectAction::Cleanup { status: -errno });
        }
        self.phase = ConnectPhase::Connected;
        Ok(ConnectAction::Publish {
            remote_queue: packet.parameters[1],
            echoed_local_cookie: packet.parameters[2],
            remote_channel_cookie: packet.parameters[3],
        })
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum DisconnectAction {
    SendAndWaitForAck,
    SendWithoutWait,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum IncomingDisconnectAction {
    InitiateReciprocalDisconnect,
    WakeDisconnectWaiter,
}

/// Atomic flag transitions replace the legacy unsynchronized flag read. The
/// adapter still owns channel memory and decides when a destroy-ready channel
/// may actually be freed.
pub(crate) struct ChannelLifecycle {
    flags: AtomicU32,
}

impl ChannelLifecycle {
    pub(crate) const fn new(flags: u32) -> Self {
        Self {
            flags: AtomicU32::new(flags),
        }
    }

    pub(crate) fn flags(&self) -> u32 {
        self.flags.load(Ordering::Acquire)
    }

    pub(crate) fn begin_disconnect(&self) -> Result<DisconnectAction, MasterError> {
        let mut current = self.flags.load(Ordering::Acquire);
        loop {
            if current & IKC_FLAG_DESTROYING != 0 {
                return Err(MasterError::Busy);
            }
            let next = (current & !IKC_FLAG_ENABLED) | IKC_FLAG_DESTROYING;
            match self
                .flags
                .compare_exchange_weak(current, next, Ordering::AcqRel, Ordering::Acquire)
            {
                Ok(_) if current & IKC_FLAG_DESTROY_ACKED == 0 => {
                    return Ok(DisconnectAction::SendAndWaitForAck);
                }
                Ok(_) => return Ok(DisconnectAction::SendWithoutWait),
                Err(changed) => current = changed,
            }
        }
    }

    pub(crate) fn observe_disconnect(&self) -> IncomingDisconnectAction {
        let prior = self
            .flags
            .fetch_or(IKC_FLAG_DESTROY_ACKED, Ordering::AcqRel);
        if prior & IKC_FLAG_DESTROYING == 0 {
            IncomingDisconnectAction::InitiateReciprocalDisconnect
        } else {
            IncomingDisconnectAction::WakeDisconnectWaiter
        }
    }

    pub(crate) fn destroy_ready(&self) -> bool {
        let flags = self.flags.load(Ordering::Acquire);
        flags & (IKC_FLAG_DESTROYING | IKC_FLAG_DESTROY_ACKED)
            == (IKC_FLAG_DESTROYING | IKC_FLAG_DESTROY_ACKED)
    }
}
