// SPDX-License-Identifier: GPL-2.0-only
//! Continuing native control service, retained beyond the synchronous BOOT call.

use super::super::{
    application_image, application_rpc, application_syscall,
    ikc_master::{AcceptSuccess, ExecutionContext, MasterRouter, RouteAction},
    smp_application, smp_cpu,
    smp_ikc::{self, BootMaster, CONTROL_PACKET_BYTES, CONTROL_QUEUE_BYTES},
    smp_resource::OsToken,
    sysfs_remote::{Attribute, Remote},
    sysfs_request as wire,
    sysfs_setup::{Service, SharedData},
    sysfs_tree::Handle,
};
use super::{abi, BootCpu, MemoryMap, OwnedControlChannel, PreparedBoot, MAX_EXTENTS};
use core::{
    mem::offset_of,
    ptr,
    sync::atomic::{AtomicBool, AtomicI32, AtomicU64, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

#[path = "sysfs_memory.rs"]
mod memory;
#[path = "smp_procfs.rs"]
pub(in super::super) mod procfs;
pub(in super::super) use memory::SyscallResponse;
#[path = "sysfs_snoop.rs"]
mod snoop;

const METADATA_CAPACITY: usize = 64;

fn errno(code: i32) -> Error {
    kernel::error::to_result(code).err().unwrap_or(EIO)
}

struct Metadata {
    claim: memory::Claim,
    request: wire::Request,
}

struct Pending {
    slots: Vec<Option<Metadata>>,
    head: usize,
    length: usize,
}

impl Pending {
    fn new() -> Result<Self> {
        let mut slots = Vec::with_capacity(METADATA_CAPACITY, GFP_KERNEL)?;
        for _ in 0..METADATA_CAPACITY {
            slots.push(None, GFP_KERNEL)?;
        }
        Ok(Self {
            slots,
            head: 0,
            length: 0,
        })
    }

    fn push(&mut self, item: Metadata) -> Option<Metadata> {
        if self.length == self.slots.len() {
            return Some(item);
        }
        let index = (self.head + self.length) % self.slots.len();
        debug_assert!(self.slots[index].is_none());
        self.slots[index] = Some(item);
        self.length += 1;
        None
    }

    fn pop(&mut self) -> Option<Metadata> {
        if self.length == 0 {
            return None;
        }
        let item = self.slots[self.head].take();
        self.head = (self.head + 1) % self.slots.len();
        self.length -= 1;
        item
    }
}

struct Transport {
    channels: Vec<OwnedControlChannel>,
    master_reply: Option<[u8; 56]>,
}

#[pin_data]
struct Runtime {
    owner: OsToken,
    memory: Arc<memory::Memory>,
    cpus: Vec<BootCpu>,
    data: SharedData,
    remote: Arc<Remote>,
    application: Arc<smp_application::Remote>,
    procfs: Arc<procfs::Remote>,
    master: Arc<BootMaster>,
    master_receive: u64,
    master_send: u64,
    master_bytes: usize,
    status_address: u64,
    error: AtomicI32,
    completed: AtomicU64,
    rejected: AtomicU64,
    #[pin]
    transport: Mutex<Transport>,
    #[pin]
    service: Mutex<Option<Service>>,
    #[pin]
    pending: Mutex<Pending>,
    #[pin]
    procfs_service: Mutex<procfs::Service>,
    #[pin]
    procfs_pending: Mutex<Vec<procfs::Event>>,
}

impl Runtime {
    fn fail(&self, error: Error) {
        if self
            .error
            .compare_exchange(0, error.to_errno(), Ordering::AcqRel, Ordering::Acquire)
            .is_ok()
        {
            pr_err!("IHK-SMP: continuing service error os={} generation={} errno={}; workers and all started owners retained\n",
                self.owner.slot(), self.owner.generation(), error.to_errno());
        }
    }

    fn dispatch(&self, port: i32, packet: &[u8; CONTROL_PACKET_BYTES]) -> Result {
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        if port != 503 {
            return Err(EINVAL);
        }
        if message == 0x13 {
            if let Err(error) = self.procfs.reply(packet) {
                if error != ENOENT {
                    return Err(error);
                }
                self.rejected.fetch_add(1, Ordering::Relaxed);
            }
            return Ok(());
        }
        if message == 0x44
            || message == application_rpc::TID_DELETE
                && u64::from_le_bytes(packet[40..48].try_into().unwrap()) != 0
        {
            let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
            let os = i32::from_le_bytes(packet[28..32].try_into().unwrap());
            let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
            let tid = u64::from_le_bytes(packet[40..48].try_into().unwrap());
            if os != self.owner.slot() as i32
                || cpu < 0
                || cpu as usize >= self.cpus.len()
                || tid == 0
                || tid > i32::MAX as u64
            {
                return Err(EINVAL);
            }
            let process = self.application.procfs_process(pid, cpu)?;
            let mut pending = self.procfs_pending.lock();
            // Refuse overflow without acknowledging CREATE. Retain started
            // ownership and report a service failure, but keep draining this
            // channel: a later answer may unblock namespace rundown.
            if pending.len() == METADATA_CAPACITY {
                return Err(ENOMEM);
            }
            let completion = if message == 0x44 {
                Some(
                    self.memory
                        .procfs(
                            u64::from_le_bytes(packet[120..128].try_into().unwrap()),
                            true,
                        )
                        .map_err(|error| if error == EAGAIN { ENOMEM } else { error })?,
                )
            } else {
                None
            }; // DELETE resp_pa is expired guest stack; never use it.
            pending.push(
                procfs::Event {
                    process,
                    tid: tid as i32,
                    completion,
                },
                GFP_KERNEL,
            )?;
            return Ok(());
        }
        if message == application_syscall::REQUEST_MESSAGE {
            let request =
                application_syscall::Request::decode(packet, self.cpus.len()).map_err(errno)?;
            return self
                .application
                .syscall_request(request, |request| self.memory.syscall(request));
        }
        if matches!(
            message,
            application_rpc::CLEANUP_REPLY
                | application_rpc::PREPARE_REPLY
                | application_rpc::TID_DELETE
        ) {
            if let Err(error) = self.application.reply(packet, |physical, bytes| {
                self.memory.application_range(physical, bytes)
            }) {
                if error != ENOENT {
                    return Err(error);
                }
                self.rejected.fetch_add(1, Ordering::Relaxed);
            }
            return Ok(());
        }
        if matches!(message, 0x3b | 0x3d | 0x3f) {
            // Stale/foreign/wrong-kind replies cannot retire the live exchange.
            // Duplicate responses are harmless and must not stop the pump.
            if let Err(error) = self.remote.reply(packet) {
                if error != ENOENT {
                    return Err(error);
                }
                self.rejected.fetch_add(1, Ordering::Relaxed);
            }
            return Ok(());
        }
        let Some(kind) = wire::Kind::from_message(message) else {
            pr_info!(
                "IHK-SMP: unserviced continuing request os={} generation={} port={} message={:x}\n",
                self.owner.slot(),
                self.owner.generation(),
                port,
                message
            );
            return Err(errno(-38));
        };
        let physical = u64::from_le_bytes(packet[24..32].try_into().unwrap());
        let claim = match self.memory.claim(kind, physical) {
            Ok(claim) => claim,
            Err(error) => {
                let rejected = self.rejected.fetch_add(1, Ordering::Relaxed);
                if rejected < 16 {
                    pr_info!("IHK-SMP: rejected sysfs mapping os={} generation={} message={:x} physical={:x} errno={}; original request untouched\n",
                        self.owner.slot(), self.owner.generation(), message, physical, error.to_errno());
                }
                // A duplicate/overlap must never acknowledge over its original
                // request. Keep draining the legitimate request and responses.
                if error == EBUSY {
                    return Ok(());
                }
                return Err(error);
            }
        };
        let request = match claim.snapshot() {
            Ok(request) => request,
            Err(error) => return claim.complete(Err(error)),
        };
        let rejected = self.pending.lock().push(Metadata { claim, request });
        if let Some(item) = rejected {
            // The extra admission claim guarantees a checked completion even
            // with 64 queued descriptors and one blocked metadata operation.
            item.claim.complete(Err(ENOMEM))?;
        }
        Ok(())
    }

    fn metadata(&self) -> Result<bool> {
        {
            let item = {
                let mut pending = self.procfs_pending.lock();
                if pending.is_empty() {
                    None
                } else {
                    Some(pending.remove(0))
                }
            };
            let mut service = self.procfs_service.lock();
            service.retire();
            if let Some(item) = item {
                if let Some(completion) = item.completion {
                    service.create(item.process, item.tid)?;
                    completion.created()?;
                } else {
                    service.delete(&item.process, item.tid)?;
                }
            }
        }
        let Some(item) = self.pending.lock().pop() else {
            return Ok(false);
        };
        let result = (|| {
            let mut service = self.service.lock();
            let tree = service.as_mut().ok_or(EIO)?.tree();
            let path = item.request.path();
            match item.request.operation {
                wire::Operation::Create { mode, client } => {
                    if (1..=1000).contains(&client.operations) {
                        let operations =
                            snoop::Snoop::new(&item.claim, client.operations, client.instance)?;
                        tree.create(path, mode, operations)?;
                    } else {
                        let operations = Attribute::new(self.remote.clone(), client)?;
                        tree.create(path, mode, operations.clone())?;
                        // Failed create never releases an unpublished guest
                        // instance. The construction reference remains until
                        // successful publication has armed the final release.
                        operations.arm();
                    }
                    Ok(None)
                }
                wire::Operation::Mkdir => tree.mkdir(path).map(|handle| Some(handle.wire())),
                wire::Operation::Symlink { target } => {
                    tree.symlink(Handle::from_wire(target)?, path).map(|_| None)
                }
                wire::Operation::Lookup => tree.lookup(path).map(|handle| Some(handle.wire())),
                wire::Operation::Unlink { flags } => tree.unlink(path, flags).map(|_| None),
            }
        })();
        let count = self.completed.fetch_add(1, Ordering::Relaxed) + 1;
        if count <= 256 {
            pr_info!("IHK-SMP: sysfs metadata os={} generation={} sequence={} operation={:?} path={} errno={}\n",
                self.owner.slot(), self.owner.generation(), count, item.request.operation,
                core::str::from_utf8(item.request.path()).unwrap_or("<non-UTF8>"),
                result.as_ref().err().map_or(0, |error| error.to_errno()));
        }
        item.claim.complete(result)?;
        Ok(true)
    }

    fn flush_master(&self) -> Result<bool> {
        if self.transport.lock().master_reply.is_none() {
            return Ok(true);
        }
        let target = *self.cpus.first().ok_or(EIO)?;
        smp_cpu::with_runtime_target(self.owner, target, |cpu| {
            smp_ikc::validate_apic()?;
            let mut transport = self.transport.lock();
            let Some(packet) = transport.master_reply else {
                return Ok(true);
            };
            match self.master.publish(&packet) {
                Ok(()) => {}
                Err(error) if error == EBUSY || error == EAGAIN => return Ok(false),
                Err(error) => return Err(error),
            }
            transport.master_reply = None;
            // Queue ownership has transferred. Even a notification failure
            // must not enqueue this reply a second time.
            smp_ikc::notify(cpu)?;
            Ok(true)
        })
    }

    fn pump_master(&self) -> Result {
        let router = MasterRouter::new(smp_ikc::listeners());
        self.master.take_notification();
        for _ in 0..16 {
            if !self.flush_master()? {
                break;
            }
            let Some(packet) = self.master.next_packet()? else {
                break;
            };
            match router.route(&packet, ExecutionContext::Process).action {
                RouteAction::Accept(plan) => {
                    let offer = plan.offer();
                    let mut transport = self.transport.lock();
                    let result = self
                        .memory
                        .connect(offer.send_queue, CONTROL_QUEUE_BYTES, || {
                            super::accept_control_channel(
                                self.memory.extents(),
                                self.owner,
                                &self.cpus,
                                &mut transport.channels,
                                Some(self.data),
                                self.memory.direct_map,
                                self.master_receive,
                                self.master_send,
                                self.master_bytes,
                                offer,
                            )
                        })
                        .map_err(|error| error.to_errno());
                    let reply = plan.connect_reply(result).map_err(smp_ikc::master_error)?;
                    transport.master_reply = Some(BootMaster::encode(&reply.packet()));
                }
                RouteAction::SendConnectError(reply) => {
                    self.transport.lock().master_reply = Some(BootMaster::encode(&reply.packet()));
                }
                RouteAction::DeliverPacket { channel_cookie } => {
                    if !self.transport.lock().channels.iter().any(|entry| {
                        entry.channel.owner == self.owner && entry.channel.cookie == channel_cookie
                    }) {
                        return Err(EINVAL);
                    }
                }
                _ => {
                    pr_info!(
                        "IHK-SMP: unserviced continuing master os={} generation={} message={:x}\n",
                        self.owner.slot(),
                        self.owner.generation(),
                        packet.message
                    );
                    return Err(errno(-38));
                }
            }
        }
        Ok(())
    }

    fn pump_regular(&self) -> Result {
        for index in 0..self.cpus.len() + 1 {
            for _ in 0..16 {
                let (port, packet) = {
                    let mut transport = self.transport.lock();
                    let Some(entry) = transport.channels.get_mut(index) else {
                        break;
                    };
                    if entry.channel.owner != self.owner {
                        return Err(EIO);
                    }
                    if entry.pages.read64(56)? as u32 != entry.channel.guest_cpu {
                        return Err(EIO);
                    }
                    let packet = match entry.pending {
                        Some(packet) => packet,
                        None => {
                            let Some(packet) = entry.channel.next_packet()? else {
                                break;
                            };
                            entry.pending = Some(packet);
                            packet
                        }
                    };
                    (entry.channel.port, packet)
                };
                // No channel/tree/resource mutex spans reply completion or
                // metadata admission. The two workers cannot wait on each
                // other's tree lock during active callback removal.
                let result = self.dispatch(port, &packet);
                if result == Err(EAGAIN) {
                    // Admission did not acquire ownership. Keep this complete
                    // packet ahead of subsequent packets on the same channel;
                    // other channels and outgoing completions still progress.
                    break;
                }
                self.transport
                    .lock()
                    .channels
                    .get_mut(index)
                    .ok_or(EIO)?
                    .pending = None;
                if let Err(error) = result {
                    self.fail(error);
                }
            }
        }
        Ok(())
    }

    fn publish_remote(&self) -> Result {
        if !self.remote.queued() {
            return Ok(());
        }
        // The unchanged sysfs host path targets McKernel CPU rank zero over
        // its host-to-McKernel port-501 channel, not the port-503 request ring.
        let target = *self.cpus.first().ok_or(EIO)?;
        smp_cpu::with_runtime_target(self.owner, target, |cpu| {
            smp_ikc::validate_apic()?;
            let transport = self.transport.lock();
            let Some(entry) = transport
                .channels
                .iter()
                .find(|entry| entry.channel.port == 501 && entry.channel.guest_cpu == 0)
            else {
                // Keep the queued exchange owned until this channel's master
                // handshake completes. Nothing has been published yet.
                return Ok(());
            };
            match self.remote.publish(|packet| entry.channel.publish(packet)) {
                Ok(true) => smp_ikc::notify(cpu),
                Ok(false) => Ok(()),
                Err(error) if error == EBUSY || error == EAGAIN => Ok(()),
                Err(error) => Err(error),
            }
        })
    }

    fn publish_applications(&self) -> Result {
        let Some(guest_cpu) = self.application.queued_cpu() else {
            return Ok(());
        };
        let target = *self.cpus.get(guest_cpu as usize).ok_or(EIO)?;
        smp_cpu::with_runtime_target(self.owner, target, |cpu| {
            smp_ikc::validate_apic()?;
            let result = {
                let transport = self.transport.lock();
                let Some(entry) = transport.channels.iter().find(|entry| {
                    entry.channel.port == 501 && entry.channel.guest_cpu == guest_cpu as u32
                }) else {
                    return Ok(());
                };
                self.application
                    .publish(guest_cpu, |packet| entry.channel.publish(packet))
            };
            match result {
                Ok(true) => smp_ikc::notify(cpu),
                Ok(false) => Ok(()),
                Err(error) if error == EBUSY || error == EAGAIN => Ok(()),
                Err(error) => Err(error),
            }
        })
    }

    fn pump(&self) {
        self.procfs.advance();
        // A failure in one service must not prevent callback replies or
        // already-published exchanges from draining in the other service.
        for result in [
            self.pump_master(),
            self.pump_regular(),
            self.publish_remote(),
            self.publish_applications(),
            self.publish_syscalls(),
            self.application.advance(),
            self.publish_procfs(),
        ] {
            if let Err(error) = result {
                self.fail(error);
            }
        }
    }

    fn publish_procfs(&self) -> Result {
        let Some(guest_cpu) = self.procfs.queued_cpu() else {
            return Ok(());
        };
        let target = *self.cpus.get(guest_cpu as usize).ok_or(EIO)?;
        smp_cpu::with_runtime_target(self.owner, target, |cpu| {
            smp_ikc::validate_apic()?;
            let result = {
                let transport = self.transport.lock();
                let Some(entry) = transport.channels.iter().find(|entry| {
                    entry.channel.port == 501 && entry.channel.guest_cpu == guest_cpu as u32
                }) else {
                    return Ok(());
                };
                self.procfs
                    .publish(guest_cpu, |packet| entry.channel.publish(packet))
            };
            match result {
                Ok(true) => smp_ikc::notify(cpu),
                Ok(false) => Ok(()),
                Err(error) if error == EBUSY || error == EAGAIN => Ok(()),
                Err(error) => Err(error),
            }
        })
    }

    fn publish_syscalls(&self) -> Result {
        let Some((application, guest_cpu)) = self.application.syscall_cpu() else {
            return Ok(());
        };
        let target = *self.cpus.get(guest_cpu as usize).ok_or(EIO)?;
        let result = smp_cpu::with_runtime_target(self.owner, target, |cpu| {
            smp_ikc::validate_apic()?;
            let result = {
                let transport = self.transport.lock();
                let Some(entry) = transport.channels.iter().find(|entry| {
                    entry.channel.port == 501 && entry.channel.guest_cpu == guest_cpu as u32
                }) else {
                    return Ok(());
                };
                self.application
                    .publish_syscall(application, guest_cpu, |packet| {
                        entry.channel.publish(packet)
                    })
            };
            match result {
                Ok(true) => smp_ikc::notify(cpu),
                Ok(false) => Ok(()),
                Err(error) if error == EBUSY || error == EAGAIN => Ok(()),
                Err(error) => Err(error),
            }
        });
        // No transport/resource mutex spans Linux waiter wakeup.
        self.application.notify_syscalls();
        result
    }

    fn status(&self) -> u64 {
        // SAFETY: The aligned boot-parameter allocation is retained by the
        // original started owner. Guest status is shared, never Rust-borrowed.
        let value = unsafe { ptr::read_volatile(self.status_address as *const u64) };
        core::sync::atomic::fence(Ordering::Acquire);
        value
    }
}

#[derive(Clone, Copy)]
enum Role {
    Packets,
    Metadata,
}

struct Entry {
    runtime: Arc<Runtime>,
    entered: Arc<AtomicBool>,
    role: Role,
}

/// The callback owns its Box only if it actually enters. Linux may satisfy
/// kthread_stop before calling a freshly created task's callback.
unsafe extern "C" fn run(data: *mut core::ffi::c_void) -> i32 {
    // SAFETY: Thread owns this unique allocation until entry or joined stop.
    let entry = unsafe { Box::from_raw(data.cast::<Entry>()) };
    entry.entered.store(true, Ordering::Release);
    while !unsafe { bindings::kthread_should_stop() } {
        match entry.role {
            Role::Packets => entry.runtime.pump(),
            Role::Metadata => {
                if let Err(error) = entry.runtime.metadata() {
                    entry.runtime.fail(error);
                }
            }
        }
        // Polling also notices host-initiated show/store calls; waiting solely
        // for a guest IRQ would strand those outgoing exchanges. Yield even
        // during sustained metadata traffic so the worker stays bounded.
        unsafe { bindings::msleep(1) };
    }
    0
}

struct Thread {
    task: *mut bindings::task_struct,
    entry: *mut Entry,
    entered: Arc<AtomicBool>,
    activated: AtomicBool,
}

// SAFETY: The private task pointer is used only for once-only wake and joined
// stop. Its callback stays alive until that stop, including service failures.
unsafe impl Send for Thread {}
// SAFETY: Arc excludes destruction during wake; all shared flags are atomic.
unsafe impl Sync for Thread {}

impl Thread {
    fn new(runtime: Arc<Runtime>, role: Role) -> Result<Arc<Self>> {
        let entered = Arc::new(AtomicBool::new(false), GFP_KERNEL)?;
        let entry = Box::into_raw(Box::new(
            Entry {
                runtime,
                role,
                entered: entered.clone(),
            },
            GFP_KERNEL,
        )?);
        let name = match role {
            Role::Packets => kernel::c_str!("mck-sysfs-pump"),
            Role::Metadata => kernel::c_str!("mck-sysfs-meta"),
        };
        // SAFETY: A unique live callback context is transferred only on entry.
        // The stopped task cannot access it until the owned activation below.
        let task = unsafe {
            bindings::kthread_create_on_node(Some(run), entry.cast(), -1, name.as_char_ptr())
        };
        if task.is_null() || (-4095..0).contains(&(task as isize)) {
            // SAFETY: Creation failed; no callback can own this context.
            unsafe { drop(Box::from_raw(entry)) };
            return Err(if task.is_null() {
                ENOMEM
            } else {
                errno(task as isize as i32)
            });
        }
        Ok(Arc::new(
            Self {
                task,
                entry,
                entered,
                activated: AtomicBool::new(false),
            },
            GFP_KERNEL,
        )?)
    }

    fn activate(&self) {
        if !self.activated.swap(true, Ordering::AcqRel) {
            // SAFETY: This owned task remains stopped/live until joined Drop.
            unsafe { bindings::wake_up_process(self.task) };
        }
    }
}

impl Drop for Thread {
    fn drop(&mut self) {
        // SAFETY: This is the unique final task owner. Joining precedes any
        // callback context reclamation. Started storage currently retains it
        // until a real peer-stop and remote callback drain can be implemented.
        unsafe { bindings::kthread_stop(self.task) };
        if !self.entered.load(Ordering::Acquire) {
            // SAFETY: Joined Linux task never entered, so never took its Box.
            unsafe { drop(Box::from_raw(self.entry)) };
        }
    }
}

#[derive(Clone)]
pub(in super::super) struct Started {
    runtime: Arc<Runtime>,
    metadata: Arc<Thread>,
    packets: Arc<Thread>,
}

impl Started {
    pub(super) fn require_ready(&self) -> Result {
        let error = self.runtime.error.load(Ordering::Acquire);
        if error != 0 {
            return Err(errno(error));
        }
        if self.runtime.status() != 3
            || !self.packets.entered.load(Ordering::Acquire)
            || !self.metadata.entered.load(Ordering::Acquire)
        {
            return Err(EBUSY);
        }
        Ok(())
    }

    pub(super) fn first(&self, packet: &[u8; CONTROL_PACKET_BYTES]) {
        if let Err(error) = self.runtime.dispatch(503, packet) {
            self.runtime.fail(error);
        }
    }

    pub(in super::super) fn activate_and_wait(&self) -> Result {
        self.packets.activate();
        self.metadata.activate();
        self.runtime.procfs.activate();
        for _ in 0..3000 {
            let error = self.runtime.error.load(Ordering::Acquire);
            if error != 0 {
                return Err(errno(error));
            }
            if self.runtime.status() == 3
                && self.packets.entered.load(Ordering::Acquire)
                && self.metadata.entered.load(Ordering::Acquire)
            {
                pr_info!("IHK-SMP: full guest ready os={} generation={} status=3 sysfs_requests={} continuing_workers=2\n",
                    self.runtime.owner.slot(), self.runtime.owner.generation(),
                    self.runtime.completed.load(Ordering::Acquire));
                return Ok(());
            }
            // All CPU/device/topology/memory guards ended before activation.
            unsafe { bindings::msleep(10) };
        }
        pr_info!("IHK-SMP: continuing boot incomplete os={} generation={} status={} sysfs_requests={}; workers and resources retained\n",
            self.runtime.owner.slot(), self.runtime.owner.generation(), self.runtime.status(),
            self.runtime.completed.load(Ordering::Acquire));
        Err(errno(-110))
    }
}

pub(in super::super) struct Application {
    started: Started,
    token: application_rpc::Token,
}

impl Application {
    pub(super) fn new(started: Started, pid: i32) -> Result<Self> {
        let token = started.runtime.application.reserve(pid)?;
        Ok(Self { started, token })
    }

    pub(in super::super) fn cleanup(&self) -> Result {
        self.started.runtime.application.cleanup(self.token)
    }

    pub(in super::super) fn worker(&self, bytes: &mut [u8], open: bool) -> Result {
        self.started
            .runtime
            .application
            .worker(self.token, bytes, open)
    }

    pub(in super::super) fn wait_syscall(&self, bytes: &mut [u8]) -> Result {
        self.started
            .runtime
            .application
            .wait_syscall(self.token, bytes)
    }

    pub(in super::super) fn copied_syscall(&self, bytes: &[u8]) -> Result {
        self.started
            .runtime
            .application
            .copied_syscall(self.token, bytes)
    }

    pub(in super::super) fn return_syscall(&self, bytes: &mut [u8]) -> Result {
        let runtime = &self.started.runtime;
        runtime
            .application
            .return_syscall(self.token, bytes, |request, destination, bytes| {
                request
                    .authorize_return_copy(destination, bytes.len())
                    .map_err(errno)?;
                runtime.memory.application_copy(destination, bytes, true)
            })
    }

    pub(in super::super) fn prepare(&self, bytes: &mut [u8]) -> Result {
        let runtime = &self.started.runtime;
        runtime.application.prepare(
            self.token,
            bytes,
            runtime.cpus.len(),
            runtime.memory.direct_map,
        )
    }

    pub(in super::super) fn lookup(&self, bytes: &mut [u8]) -> Result {
        if bytes.len() != 32 {
            return Err(EINVAL);
        }
        let address = application_image::word(bytes, 0).map_err(errno)?;
        let access = application_image::word(bytes, 8).map_err(errno)?;
        if access & !3 != 0 {
            return Err(EINVAL);
        }
        let runtime = &self.started.runtime;
        runtime.application.with_prepared(self.token, |image| {
            let page = application_image::translate(image.page_table, address, |physical| {
                runtime
                    .memory
                    .application_word(physical)
                    .map_err(|error| error.to_errno())
            })
            .map_err(errno)?;
            if access & 1 != 0 && !page.writable || access & 2 != 0 && !page.executable {
                return Err(EACCES);
            }
            runtime
                .memory
                .application_range(page.physical & !4095, 4096)?;
            application_image::put_word(bytes, 16, page.physical).map_err(errno)?;
            application_image::put_word(
                bytes,
                24,
                u64::from(page.writable) | u64::from(page.executable) << 1,
            )
            .map_err(errno)
        })
    }

    pub(in super::super) fn transfer(&self, bytes: &mut [u8]) -> Result {
        if bytes.len() <= 16 {
            return Err(EINVAL);
        }
        let physical = application_image::word(bytes, 0).map_err(errno)?;
        let direction = application_image::word(bytes, 8).map_err(errno)?;
        if direction > 1 {
            return Err(EINVAL);
        }
        let runtime = &self.started.runtime;
        runtime.application.with_prepared(self.token, |image| {
            image.authorize_transfer(physical, bytes.len() - 16)?;
            runtime
                .memory
                .application_copy(physical, &mut bytes[16..], direction == 0)
        })
    }
}

impl Drop for Application {
    fn drop(&mut self) {
        // An unpublished registration cancels only its reserved slot. A caller
        // departing after publication cannot remove the continuing RPC owner.
        self.started.runtime.application.close(self.token);
    }
}

pub(super) fn prepare(
    map: &MemoryMap<MAX_EXTENTS>,
    owner: OsToken,
    direct_map: u64,
    prepared: &mut PreparedBoot,
    receive: u64,
    send: u64,
    queue_bytes: usize,
) -> Result<Started> {
    let data = prepared.sysfs.as_ref().and_then(Service::data).ok_or(EIO)?;
    if data.owner != owner || prepared.continuing.is_some() {
        return Err(EIO);
    }
    let master = prepared.master.as_ref().ok_or(EIO)?.clone();
    let mut cpus = Vec::with_capacity(prepared.cpus.len(), GFP_KERNEL)?;
    for &cpu in &prepared.cpus {
        cpus.push(cpu, GFP_KERNEL)?;
    }
    let mut fixed = Vec::with_capacity(4 + 2 * (cpus.len() + 1), GFP_KERNEL)?;
    for (physical, bytes) in [
        (receive, queue_bytes),
        (send, queue_bytes),
        (prepared.vdso_request, super::super::vdso_protocol::BYTES),
        (data.physical, data.bytes),
    ] {
        fixed.push(memory::Span::new(physical, bytes)?, GFP_KERNEL)?;
    }
    for entry in &prepared.channels {
        for physical in [entry.channel.receive_physical, entry.channel.send_physical] {
            fixed.push(
                memory::Span::new(physical, CONTROL_QUEUE_BYTES)?,
                GFP_KERNEL,
            )?;
        }
    }
    // SAFETY: BOOT already made original page/module ownership irreversible;
    // these exact-generation mappings are retained throughout every outcome.
    let memory = unsafe { memory::Memory::new(map, owner, direct_map, fixed)? };
    // SAFETY: Setup validated the unique response page and stored it before
    // acknowledgement. No prior continuing Remote exists for this OS.
    let remote = unsafe { Remote::new(data)? };
    let procfs = procfs::Remote::new(memory.clone())?;
    let procfs_service = procfs::Service::new(procfs.clone())?;
    let procfs_pending = Vec::with_capacity(METADATA_CAPACITY, GFP_KERNEL)?;
    let application = smp_application::Remote::new(owner, procfs.clone())?;
    let pending = Pending::new()?;
    let status_address = prepared.params.address + offset_of!(abi::IhkSmpBootParam, status) as u64;
    let runtime = Arc::pin_init(
        pin_init!(Runtime {
            owner, memory, cpus, data, remote, application, procfs, master,
            master_receive: receive, master_send: send, master_bytes: queue_bytes,
            status_address,
            error: AtomicI32::new(0), completed: AtomicU64::new(0), rejected: AtomicU64::new(0),
            transport <- new_mutex!(Transport { channels: Vec::new(), master_reply: None }),
            service <- new_mutex!(None),
            pending <- new_mutex!(pending),
            procfs_service <- new_mutex!(procfs_service),
            procfs_pending <- new_mutex!(procfs_pending),
        }),
        GFP_KERNEL,
    )?;
    let packets = Thread::new(runtime.clone(), Role::Packets)?;
    let metadata = Thread::new(runtime.clone(), Role::Metadata)?;
    let started = Started {
        runtime,
        metadata,
        packets,
    };
    // All fallible allocations and task creation finished. Moving a published
    // tree into a fallible constructor could otherwise destroy it on error.
    *started.runtime.service.lock() = prepared.sysfs.take();
    started.runtime.transport.lock().channels = core::mem::take(&mut prepared.channels);
    Ok(started)
}
