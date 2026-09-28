// SPDX-License-Identifier: GPL-2.0
//! Linux CPU reservation adapter for the existing SMP transaction policy.
//!
//! Policy and journals stay in `smp_resource`. Linux owns hotplug execution.
//! Large workspaces live in module storage, protected by one sleepable mutex.
//! This first adapter supports CPUs present and online at module load. Physical
//! eject, suspend and CPU topology replacement still require production tests.

use core::{
    cell::UnsafeCell,
    marker::PhantomData,
    pin::Pin,
    ptr,
    sync::atomic::{AtomicBool, AtomicPtr, AtomicU32, AtomicU64, Ordering},
};
use kernel::{
    bindings, c_str,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
    uaccess::UserSlice,
};

use super::smp_resource::{
    CpuChange, CpuEffectCause, CpuState, CpuTable, HostCpuHotplug, HostCpuSnapshot, OsToken,
    SMP_MAX_CPUS,
};

#[allow(dead_code, unreachable_pub)]
#[path = "abi/x86_64.rs"]
mod abi;

// SAFETY: The exact selected x86_64 kernel exports this Linux C ABI function.
// Its declaration is absent from rust/bindings/bindings_helper.h's include
// closure. No project-owned C implementation is linked into this module.
extern "C" {
    fn default_cpu_present_to_apicid(cpu: i32) -> u32;
    /// The pending native x86 wrapper brackets the existing INIT
    /// assert/deassert sequence with the required Linux preemption handling.
    /// It is an attempted reset only: it does not send SIPI or establish that
    /// Linux has reclaimed a CPU.
    fn native_reset_secondary_cpu_via_init(phys_apicid: u32);
}

static BLOCK_ONLINE: [AtomicBool; SMP_MAX_CPUS] = [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
static ALLOWED_TASK: [AtomicPtr<bindings::task_struct>; SMP_MAX_CPUS] =
    [const { AtomicPtr::new(ptr::null_mut()) }; SMP_MAX_CPUS];
static BOOT_IRQ_TARGET_USERS: AtomicU32 = AtomicU32::new(0);
static BOOT_IRQ_GENERATIONS: [AtomicU64; 64] = [const { AtomicU64::new(0) }; 64];
static BOOT_IRQ_EVENTS: [AtomicU64; 64] = [const { AtomicU64::new(0) }; 64];
static BOOT_MASTER: [AtomicPtr<super::smp_ikc::BootMaster>; 64] =
    [const { AtomicPtr::new(ptr::null_mut()) }; 64];

// SAFETY: Registered at AP_ONLINE_DYN, before irreversible target teardown.
// The CPUHP callback uses only one bounded atomic and never a resource mutex.
unsafe extern "C" fn allow_cpu_offline(cpu: u32) -> i32 {
    if cpu == 0 && BOOT_IRQ_TARGET_USERS.load(Ordering::Acquire) != 0 {
        EBUSY.to_errno()
    } else {
        0
    }
}

// SAFETY: Each monomorphized identity belongs to one pinned OS slot. A started
// route cannot retire until guest senders stop and Linux drains every work
// node. Hard IRQ drains bounded packets; no sleepable lock is acquired.
unsafe extern "C" fn boot_irq_callback<const SLOT: usize>(_work: *mut core::ffi::c_void) {
    let generation = BOOT_IRQ_GENERATIONS[SLOT].load(Ordering::Acquire);
    if generation != 0 {
        BOOT_IRQ_EVENTS[SLOT].fetch_add(1, Ordering::Release);
        let master = BOOT_MASTER[SLOT].load(Ordering::Acquire);
        if !master.is_null() {
            // SAFETY: Publication follows permanent retention in started boot
            // storage. A started generation cannot retire or reuse this slot.
            let master = unsafe { &*master };
            if master.owner().generation() == generation && master.owner().slot() as usize == SLOT {
                master.interrupt();
            }
        }
    }
}

macro_rules! boot_irq_callbacks {
    ($($slot:literal),* $(,)?) => {
        [$(boot_irq_callback::<$slot> as unsafe extern "C" fn(*mut core::ffi::c_void)),*]
    };
}

const BOOT_IRQ_CALLBACKS: [unsafe extern "C" fn(*mut core::ffi::c_void); 64] = boot_irq_callbacks!(
    0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25,
    26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,
    50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63,
);

/// Unstarted route owner. Active/uncertain boot retains this value without
/// dropping it; generation reuse requires a separate sender-stop/drain proof.
pub(super) struct BootIrqRoute {
    owner: OsToken,
}

impl BootIrqRoute {
    pub(super) fn new(owner: OsToken, topology: &BootTopology<'_>) -> Result<Self> {
        super::smp_ikc::validate_apic()?;
        if !topology.host_cpu(0)?.online {
            return Err(ENODEV);
        }
        BOOT_IRQ_GENERATIONS[owner.slot() as usize]
            .compare_exchange(0, owner.generation(), Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| EBUSY)?;
        // At most 64 routes exist; the CPU read guard excludes teardown until
        // this counter has made the persistent CPUHP veto visible.
        BOOT_IRQ_TARGET_USERS.fetch_add(1, Ordering::Release);
        BOOT_IRQ_EVENTS[owner.slot() as usize].store(0, Ordering::Relaxed);
        Ok(Self { owner })
    }

    pub(super) fn callback(&self) -> *mut core::ffi::c_void {
        BOOT_IRQ_CALLBACKS[self.owner.slot() as usize] as *const () as *mut core::ffi::c_void
    }

    pub(super) fn events(&self) -> u64 {
        BOOT_IRQ_EVENTS[self.owner.slot() as usize].load(Ordering::Acquire)
    }

    // SAFETY: master is already in stable heap storage retained permanently by
    // this started boot. It cannot be dropped before sender stop and IRQ drain.
    pub(super) unsafe fn publish_master(&self, master: &super::smp_ikc::BootMaster) -> Result {
        if master.owner() != self.owner {
            return Err(EINVAL);
        }
        BOOT_MASTER[self.owner.slot() as usize]
            .compare_exchange(
                ptr::null_mut(),
                (master as *const super::smp_ikc::BootMaster).cast_mut(),
                Ordering::Release,
                Ordering::Acquire,
            )
            .map_err(|_| EBUSY)?;
        Ok(())
    }
}

impl Drop for BootIrqRoute {
    fn drop(&mut self) {
        // This destructor is reachable only before any CPU-start effect.
        // No guest work can still refer to the slot or this module callback.
        assert_eq!(
            BOOT_IRQ_GENERATIONS[self.owner.slot() as usize].swap(0, Ordering::AcqRel),
            self.owner.generation()
        );
        assert!(BOOT_IRQ_TARGET_USERS.fetch_sub(1, Ordering::AcqRel) > 0);
    }
}

/// CPUHP_BP_PREPARE_DYN runs on the initiating task before target CPU bringup.
/// It must never acquire the policy mutex: our own device transition holds it.
// SAFETY: Linux invokes this scalar callback while its registered state and
// module are live. Only bounded atomics and the current-task identity are read.
unsafe extern "C" fn allow_cpu_online(cpu: u32) -> i32 {
    let cpu = cpu as usize;
    if cpu >= SMP_MAX_CPUS || !BLOCK_ONLINE[cpu].load(Ordering::Acquire) {
        return 0;
    }
    // SAFETY: get_current returns the live task executing this callback. The
    // pointer is compared only; neither pointer is dereferenced or retained.
    let current = unsafe { bindings::get_current() };
    if ALLOWED_TASK[cpu].load(Ordering::Acquire) == current {
        0
    } else {
        EBUSY.to_errno()
    }
}

/// Scope-bound permission also covers Linux's internal rollback after an error.
struct TransitionTask(usize);

impl TransitionTask {
    fn new(cpu: usize) -> Self {
        // SAFETY: This task remains live until the synchronous hotplug call
        // and this guard end. The pointer is never dereferenced by a callback.
        let current = unsafe { bindings::get_current() };
        ALLOWED_TASK[cpu].store(current, Ordering::Release);
        Self(cpu)
    }
}

impl Drop for TransitionTask {
    fn drop(&mut self) {
        ALLOWED_TASK[self.0].store(ptr::null_mut(), Ordering::Release);
    }
}

/// Ordinary Linux device hotplug exclusion, kept on its acquiring task.
struct DeviceHotplugGuard(PhantomData<*mut ()>);

impl DeviceHotplugGuard {
    fn lock() -> Self {
        // SAFETY: Called in sleepable module-init/ioctl context after the policy
        // mutex. Neither CPU read-side nor device lock is already held here.
        unsafe { bindings::lock_device_hotplug() };
        Self(PhantomData)
    }
}

impl Drop for DeviceHotplugGuard {
    fn drop(&mut self) {
        // SAFETY: Non-Send, non-Copy guard balances the lock on this task.
        unsafe { bindings::unlock_device_hotplug() };
    }
}

struct CpuReadGuard(PhantomData<*mut ()>);

impl CpuReadGuard {
    fn lock() -> Self {
        // SAFETY: Sleepable read-side topology observation only. This guard is
        // dropped before device_online/offline can acquire the CPU write side.
        unsafe { bindings::cpus_read_lock() };
        Self(PhantomData)
    }
}

impl Drop for CpuReadGuard {
    fn drop(&mut self) {
        // SAFETY: Exactly the acquiring task releases the read-side lock.
        unsafe { bindings::cpus_read_unlock() };
    }
}

struct CpuDevice(*mut bindings::device, Arc<super::smp_topology::Cpu>);

// SAFETY: The retained Linux reference can be released on any task. Access is
// exclusively under the policy mutex and Linux's device hotplug lock.
unsafe impl Send for CpuDevice {}

impl Drop for CpuDevice {
    fn drop(&mut self) {
        // SAFETY: This non-Copy value owns exactly one successful get_device.
        unsafe { bindings::put_device(self.0) };
    }
}

/// A journal-only view of the `CpuDevice` reference retained by `CpuContext`.
///
/// `CpuDevice` owns the successful `get_device`; this wrapper never owns or
/// releases that reference.  The pointer is only compared or passed back to
/// Linux while `CpuContext` is held by its pinned mutex and the device-hotplug
/// exclusion is live.  Thus moving the journal with the context cannot create
/// concurrent device access or outlive the retained `CpuDevice`.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct RetainedCpuDevice(*mut bindings::device);

// SAFETY: See the type invariant above. The raw pointer is an identity token,
// not an independently accessible or owned device reference.
unsafe impl Send for RetainedCpuDevice {}
// SAFETY: Shared journal observations require the same CpuContext mutex and
// device-hotplug exclusion; the wrapper itself is never dereferenced.
unsafe impl Sync for RetainedCpuDevice {}

impl RetainedCpuDevice {
    const fn empty() -> Self {
        Self(ptr::null_mut())
    }

    fn is_null(self) -> bool {
        self.0.is_null()
    }
}

/// The first irreversible stage that made a shutdown target uncertain.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ShutdownCpuFailureStage {
    None,
    PreResetValidation,
    DeviceOnline,
    PostOnlineValidation,
}

/// Irreversible progress for one retained AP during shutdown reclamation.
///
/// This intentionally does not share `CpuChange`: ordinary reserve/return
/// transactions compensate a failed device transition, while an INIT attempt
/// must retain every owner until a later, explicit reconciliation proves the
/// physical state. The journal lives in the static CPU context, so recording
/// a target or an error cannot allocate after shutdown has closed admission.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct ShutdownCpuJournal {
    owner_slot: u32,
    owner_generation: u64,
    cpu: u32,
    apic_id: u32,
    numa_node: u32,
    device: RetainedCpuDevice,
    recorded: bool,
    reset_attempted: bool,
    online_attempted: bool,
    /// Exact `device_online` status, retained even when a positive no-op is
    /// normalized to EIO for the fail-closed public result.
    online_status: i32,
    online: bool,
    retained: bool,
    first_failure_stage: ShutdownCpuFailureStage,
    first_failure: i32,
}

impl ShutdownCpuJournal {
    const fn empty() -> Self {
        Self {
            owner_slot: 0,
            owner_generation: 0,
            cpu: 0,
            apic_id: 0,
            numa_node: 0,
            device: RetainedCpuDevice::empty(),
            recorded: false,
            reset_attempted: false,
            online_attempted: false,
            online_status: 0,
            online: false,
            retained: false,
            first_failure_stage: ShutdownCpuFailureStage::None,
            first_failure: 0,
        }
    }

    fn record(
        &mut self,
        owner: OsToken,
        cpu: usize,
        snapshot: HostCpuSnapshot,
        device: *mut bindings::device,
    ) {
        *self = Self {
            owner_slot: owner.slot(),
            owner_generation: owner.generation(),
            cpu: cpu as u32,
            apic_id: snapshot.hardware_id,
            numa_node: snapshot.numa_node,
            device: RetainedCpuDevice(device),
            recorded: true,
            reset_attempted: false,
            online_attempted: false,
            online_status: 0,
            online: false,
            retained: false,
            first_failure_stage: ShutdownCpuFailureStage::None,
            first_failure: 0,
        };
    }

    fn matches_owner(&self, owner: OsToken) -> bool {
        self.recorded
            && self.owner_slot == owner.slot()
            && self.owner_generation == owner.generation()
    }

    fn reset_attempted(&mut self) {
        self.reset_attempted = true;
    }

    fn online(&mut self) {
        self.online = true;
    }

    fn online_attempted(&mut self) {
        self.online_attempted = true;
    }

    fn online_status(&mut self, status: i32) {
        self.online_status = status;
    }

    fn retain(&mut self, stage: ShutdownCpuFailureStage, failure: i32) {
        self.retained = true;
        if self.first_failure == 0 {
            self.first_failure_stage = stage;
            self.first_failure = failure;
        }
    }
}

fn shutdown_journal_blocks_ordinary_use(journal: &[ShutdownCpuJournal]) -> bool {
    journal.iter().any(|record| record.recorded)
}

pub(super) struct ResourceModulePin;

impl ResourceModulePin {
    pub(super) fn acquire() -> Result<Self> {
        // SAFETY: This is our resident module descriptor. An open control file
        // already pins it while acquiring the longer reservation reference.
        if unsafe { bindings::try_module_get(super::THIS_MODULE.as_ptr()) } {
            Ok(Self)
        } else {
            Err(ENODEV)
        }
    }
}

impl Drop for ResourceModulePin {
    fn drop(&mut self) {
        // SAFETY: Each successful acquisition is balanced once, while an open
        // file still pins this executing code. Uncertain CPU or memory resources
        // retain this owner in their context and cannot reach module teardown.
        unsafe { bindings::module_put(super::THIS_MODULE.as_ptr()) };
    }
}

struct CpuContext {
    table: CpuTable<SMP_MAX_CPUS>,
    journal: [CpuChange; SMP_MAX_CPUS],
    shutdown_journal: [ShutdownCpuJournal; SMP_MAX_CPUS],
    requests: [usize; SMP_MAX_CPUS],
    requested: [bool; SMP_MAX_CPUS],
    devices: [Option<CpuDevice>; SMP_MAX_CPUS],
    pin: Option<ResourceModulePin>,
    poisoned: bool,
}

impl CpuContext {
    const fn new() -> Self {
        Self {
            table: CpuTable::new(),
            journal: [CpuChange::empty(); SMP_MAX_CPUS],
            shutdown_journal: [ShutdownCpuJournal::empty(); SMP_MAX_CPUS],
            requests: [0; SMP_MAX_CPUS],
            requested: [false; SMP_MAX_CPUS],
            devices: [const { None }; SMP_MAX_CPUS],
            pin: None,
            poisoned: false,
        }
    }

    fn initialize(&mut self) -> Result {
        let _hotplug = DeviceHotplugGuard::lock();
        let _topology = CpuReadGuard::lock();
        // SAFETY: nr_cpu_ids is initialized before module loading and stable
        // under CPU hotplug read exclusion. We implement the frozen 512 limit.
        let limit = unsafe { bindings::nr_cpu_ids } as usize;
        if limit == 0 || limit > SMP_MAX_CPUS {
            return Err(EINVAL);
        }
        for cpu in 0..limit {
            let snapshot = match observed_cpu(cpu, &_topology, &_hotplug) {
                Ok(snapshot) if snapshot.online => snapshot,
                _ => continue,
            };
            // SAFETY: Both guards remain held through the complete capture.
            // Own this before offline clears Linux's core ID and sibling maps.
            let topology = unsafe { super::smp_topology::capture(cpu)? };
            if topology.apic_id != snapshot.hardware_id {
                return Err(EIO);
            }
            let topology = Arc::new(topology, GFP_KERNEL)?;
            // SAFETY: Both topology/device hotplug locks protect discovery.
            // get_device retains the live device before either lock is dropped.
            let device = unsafe { bindings::get_cpu_device(cpu as u32) };
            if device.is_null() {
                return Err(ENODEV);
            }
            // SAFETY: The non-null CPU device remains live under the two
            // guards. Retain it before discovery exclusion ends.
            let device = unsafe { bindings::get_device(device) };
            if device.is_null() {
                return Err(ENODEV);
            }
            self.devices[cpu] = Some(CpuDevice(device, topology));
            self.table
                .add_online_cpu(cpu, snapshot.hardware_id, snapshot.numa_node)
                .map_err(|_| EINVAL)?;
        }
        if self.devices[0].is_none() {
            return Err(ENODEV);
        }
        Ok(())
    }

    fn available(&self) -> usize {
        self.table.count_state(CpuState::Available)
    }

    fn has_owned_cpu(&self) -> bool {
        (0..SMP_MAX_CPUS).any(|cpu| {
            self.table.slot(cpu).map_or(true, |slot| {
                !matches!(slot.state(), CpuState::Online | CpuState::Absent)
            })
        })
    }

    /// Refuse further published results if owned hardware lost its identity.
    /// The existing pin and online veto stay held until explicit reconciliation.
    /// A shutdown journal is itself an uncertain physical transition: ordinary
    /// ioctls, boot and release paths must never treat a later online bit as a
    /// return to the previous lifecycle. Only shutdown reconciliation below
    /// deliberately bypasses this ordinary-operation fence.
    fn verify_owned(&mut self, hotplug: &DeviceHotplugGuard) -> Result {
        if self.poisoned || shutdown_journal_blocks_ordinary_use(&self.shutdown_journal) {
            self.poisoned = true;
            return Err(EIO);
        }
        let mut host = LinuxCpuBatch {
            devices: &self.devices,
            _hotplug: hotplug,
        };
        for cpu in 0..SMP_MAX_CPUS {
            let slot = self.table.slot(cpu).map_err(|_| EIO)?;
            match slot.state() {
                CpuState::Online | CpuState::Absent => continue,
                CpuState::Available | CpuState::Assigned => {
                    let expected = HostCpuSnapshot {
                        hardware_id: slot.hardware_id(),
                        numa_node: slot.numa_node(),
                        online: false,
                    };
                    if host.observe(cpu) == Ok(expected) {
                        continue;
                    }
                }
                _ => {}
            }
            self.poisoned = true;
            return Err(EIO);
        }
        Ok(())
    }

    /// Retain every recorded CPU after an INIT attempt or uncertain re-online.
    /// This is deliberately stronger than ordinary hotplug failure handling:
    /// no compensation can prove that a reset AP resumed its McKernel state.
    fn retain_shutdown_failure(
        &mut self,
        count: usize,
        stage: ShutdownCpuFailureStage,
        failure: Error,
    ) -> Error {
        for record in &mut self.shutdown_journal[..count] {
            if record.recorded {
                record.retain(stage, failure.to_errno());
            }
        }
        self.poisoned = true;
        failure
    }

    /// Complete every fallible lookup before the first journal write. Once a
    /// record exists, every later error must retain and poison the complete
    /// selected set; this preflight includes a missing retained device.
    fn prevalidate_shutdown_targets(
        &self,
        owner: OsToken,
        count: usize,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let read = CpuReadGuard::lock();
        for index in 0..count {
            let cpu = self.requests[index];
            let slot = self.table.slot(cpu).map_err(|_| EIO)?;
            let device = self
                .devices
                .get(cpu)
                .and_then(Option::as_ref)
                .ok_or(ENODEV)?;
            // SAFETY: The two guards stabilize this retained CPU-device
            // association before the first irreversible journal record.
            let current = unsafe { bindings::get_cpu_device(cpu as u32) };
            let actual = observed_cpu(cpu, &read, hotplug)?;
            if device.0.is_null()
                || current != device.0
                || device.1.linux_id as usize != cpu
                || slot.state() != CpuState::Assigned
                || slot.owner() != Some(owner)
                || slot.hardware_id() != device.1.apic_id
                || slot.numa_node() != actual.numa_node
                || actual.hardware_id != device.1.apic_id
                || actual.online
            {
                return Err(EIO);
            }
        }
        Ok(())
    }

    /// Validate one journaled target against the same retained Linux device,
    /// exact APIC/NUMA identity, canonical assignment and required online bit.
    /// Caller holds both device-hotplug and CPU read-side exclusion.
    fn validate_shutdown_target(
        &self,
        owner: OsToken,
        record: ShutdownCpuJournal,
        expected_online: bool,
        topology: &CpuReadGuard,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        let cpu = record.cpu as usize;
        if !record.matches_owner(owner) || cpu == 0 || cpu >= SMP_MAX_CPUS {
            return Err(EIO);
        }
        let slot = self.table.slot(cpu).map_err(|_| EIO)?;
        let retained = self.devices.get(cpu).and_then(Option::as_ref).ok_or(EIO)?;
        // SAFETY: The two guards stabilize the CPU-device association. The
        // record was captured from this retained, get_device-owned pointer.
        let current = unsafe { bindings::get_cpu_device(cpu as u32) };
        if record.device.is_null()
            || current != record.device.0
            || retained.0 != record.device.0
            || retained.1.linux_id as usize != cpu
            || retained.1.apic_id != record.apic_id
            || slot.state() != CpuState::Assigned
            || slot.owner() != Some(owner)
            || slot.hardware_id() != record.apic_id
            || slot.numa_node() != record.numa_node
        {
            return Err(EIO);
        }
        let actual = observed_cpu(cpu, topology, hotplug)?;
        if actual.hardware_id != record.apic_id
            || actual.numa_node != record.numa_node
            || actual.online != expected_online
        {
            return Err(EIO);
        }
        Ok(())
    }

    /// Reset each exact, already-offline assigned AP and require Linux to
    /// synchronously re-online that same CPU. This primitive is intentionally
    /// not wired to the v5 shutdown callback: it never releases CPU table,
    /// memory, IRQ or module ownership and therefore cannot claim a guest is
    /// stopped or resources are reclaimable on its own.
    fn shutdown_reset_and_reonline(
        &mut self,
        owner: OsToken,
        hotplug: &DeviceHotplugGuard,
    ) -> Result {
        if self.poisoned || shutdown_journal_blocks_ordinary_use(&self.shutdown_journal) {
            self.poisoned = true;
            return Err(EIO);
        }
        let count = self
            .table
            .assigned_cpus(owner, &mut self.requests)
            .map_err(|_| EIO)?;
        if count == 0 {
            return Err(EINVAL);
        }

        self.prevalidate_shutdown_targets(owner, count, hotplug)?;

        // The complete canonical device/identity preflight above finished
        // before the first record. Record every target before any reset or
        // online effect, so every later error has a complete retention set.
        // The stored device pointer is held live by CpuDevice's get_device
        // reference until a separate, successful lifecycle release.
        for index in 0..count {
            let cpu = self.requests[index];
            let slot = self
                .table
                .slot(cpu)
                .unwrap_or_else(|_| panic!("shutdown CPU prevalidation lost a canonical slot"));
            let device = self.devices[cpu]
                .as_ref()
                .unwrap_or_else(|| panic!("shutdown CPU prevalidation lost a retained device"));
            self.shutdown_journal[index].record(
                owner,
                cpu,
                HostCpuSnapshot {
                    hardware_id: slot.hardware_id(),
                    numa_node: slot.numa_node(),
                    online: false,
                },
                device.0,
            );
        }

        {
            let read = CpuReadGuard::lock();
            for index in 0..count {
                let record = self.shutdown_journal[index];
                if self
                    .validate_shutdown_target(owner, record, false, &read, hotplug)
                    .is_err()
                {
                    return Err(self.retain_shutdown_failure(
                        count,
                        ShutdownCpuFailureStage::PreResetValidation,
                        EIO,
                    ));
                }
            }
            for index in 0..count {
                let record = &mut self.shutdown_journal[index];
                // SAFETY: CPU read exclusion fixes this validated APIC target.
                // The pending native wrapper owns its exact preemption bracket
                // and returns before this Rust code can reach device_online.
                unsafe { native_reset_secondary_cpu_via_init(record.apic_id) };
                record.reset_attempted();
            }
        }

        // CPU read-side exclusion is gone here. The wrapper's preemption
        // bracket also ended before it returned. Linux's synchronous
        // device_online is sleepable and may invoke CPUHP paths.
        for index in 0..count {
            let record = self.shutdown_journal[index];
            let _permission = TransitionTask::new(record.cpu as usize);
            self.shutdown_journal[index].online_attempted();
            // SAFETY: Device-hotplug exclusion and the retained journal device
            // identity serialize the exact Linux transition. Positive/no-op is
            // rejected just as strictly as a negative Linux errno.
            let status = unsafe { bindings::device_online(record.device.0) };
            self.shutdown_journal[index].online_status(status);
            if status != 0 {
                let failure = if status < 0 {
                    kernel::error::to_result(status).unwrap_err()
                } else {
                    EIO
                };
                return Err(self.retain_shutdown_failure(
                    count,
                    ShutdownCpuFailureStage::DeviceOnline,
                    failure,
                ));
            }
            let read = CpuReadGuard::lock();
            if self
                .validate_shutdown_target(owner, record, true, &read, hotplug)
                .is_err()
            {
                return Err(self.retain_shutdown_failure(
                    count,
                    ShutdownCpuFailureStage::PostOnlineValidation,
                    EIO,
                ));
            }
            self.shutdown_journal[index].online();
        }
        Ok(())
    }

    fn request_cpus(&mut self, request: &CpuRequest) -> Result<usize> {
        self.requested.fill(false);
        let mut reader = UserSlice::new(request.array, request.count * 4).reader();
        for _ in 0..request.count {
            let cpu = reader.read::<i32>()?;
            if cpu <= 0 || cpu as usize >= SMP_MAX_CPUS {
                return Err(EINVAL);
            }
            self.requested[cpu as usize] = true;
        }
        let mut count = 0;
        for cpu in 1..SMP_MAX_CPUS {
            if self.requested[cpu] {
                self.requests[count] = cpu;
                count += 1;
            }
        }
        Ok(count)
    }

    fn change(&mut self, request: &CpuRequest, reserve: bool) -> Result<isize> {
        if request.count == 0 {
            return Ok(0);
        }
        let count = self.request_cpus(request)?;
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        let newly_pinned = self.pin.is_none();
        if newly_pinned {
            self.pin = Some(ResourceModulePin::acquire()?);
        }
        let result = (|| {
            let transaction = if reserve {
                self.table
                    .prepare_reserve(&self.requests[..count], &mut self.journal)
            } else {
                self.table
                    .prepare_return_to_host(&self.requests[..count], &mut self.journal)
            }
            .map_err(|_| EINVAL)?;
            // Block unsolicited online attempts before the first effect. Our
            // task gets scope-bound permission for each forward/inverse call.
            for &cpu in &self.requests[..count] {
                BLOCK_ONLINE[cpu].store(true, Ordering::Release);
            }
            if reserve {
                let _read = CpuReadGuard::lock();
                // SAFETY: The read guard excludes every topology transition.
                let online = unsafe { super::smp_topology::CpuMask::online()? };
                for &cpu in &self.requests[..count] {
                    let saved = &self.devices[cpu].as_ref().ok_or(ENODEV)?.1;
                    // SAFETY: The same guard retains the complete online data.
                    let current = unsafe { super::smp_topology::capture(cpu)? };
                    if !saved.matches_current(&current, &online) {
                        return Err(EIO);
                    }
                }
                // End CPU read exclusion before device_offline takes its writer.
            }
            let mut host = LinuxCpuBatch {
                devices: &self.devices,
                _hotplug: &hotplug,
            };
            transaction.execute_hotplug(&mut host).map_err(|failure| {
                if failure.quarantined {
                    self.poisoned = true;
                }
                match failure.cause {
                    CpuEffectCause::Host { error, .. } => error,
                    CpuEffectCause::Policy(_) => EINVAL,
                    CpuEffectCause::StateMismatch { .. } => EIO,
                }
            })
        })();
        for &cpu in &self.requests[..count] {
            let owned = self.table.slot(cpu).map_or(true, |slot| {
                !matches!(slot.state(), CpuState::Online | CpuState::Absent)
            });
            BLOCK_ONLINE[cpu].store(owned, Ordering::Release);
        }
        if !self.poisoned && !self.has_owned_cpu() {
            self.pin.take();
        }
        result.map(|()| 0)
    }

    fn query(&mut self, request: &CpuRequest) -> Result<isize> {
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        let count = self.available();
        if count != request.count {
            return Err(EINVAL);
        }
        // Do not hold Linux's global device lock across faulting userspace I/O.
        // The policy mutex and CPUHP veto retain reservation ownership.
        drop(hotplug);
        let mut writer = UserSlice::new(request.array, count * 4).writer();
        for cpu in 0..SMP_MAX_CPUS {
            if self.table.slot(cpu).map_err(|_| EIO)?.state() == CpuState::Available {
                writer.write(&(cpu as i32))?;
            }
        }
        UserSlice::new(request.count_address, 4)
            .writer()
            .write(&(count as i32))?;
        Ok(0)
    }

    fn change_os(&mut self, owner: OsToken, request: &CpuRequest, assign: bool) -> Result<isize> {
        // A retained shutdown journal is an uncertain physical transition.
        // Fence it before either changing memory's unstarted boot storage or
        // accepting a zero-count success: a later ordinary assign/release
        // must never make those retained owners look releasable again.
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        drop(hotplug);
        super::smp_memory::retire_os_boot(owner)?;
        if request.count == 0 {
            return Ok(0);
        }
        // Preserve input order: it defines the McKernel logical CPU rank.
        // The shared policy rejects duplicates and checks the whole request.
        let mut reader = UserSlice::new(request.array, request.count * 4).reader();
        for index in 0..request.count {
            let cpu = reader.read::<i32>()?;
            if cpu <= 0 || cpu as usize >= SMP_MAX_CPUS {
                return Err(EINVAL);
            }
            self.requests[index] = cpu as usize;
        }
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        drop(hotplug);
        let mut transaction = if assign {
            self.table
                .prepare_assign(owner, &self.requests[..request.count], &mut self.journal)
        } else {
            self.table
                .prepare_release(owner, &self.requests[..request.count], &mut self.journal)
        }
        .map_err(|_| EINVAL)?;
        // These are initial-state ownership transfers; Linux CPUs remain
        // offline, retained by their existing device owners and CPUHP veto.
        transaction.begin_external_effects().map_err(|_| EIO)?;
        transaction
            .commit()
            .unwrap_or_else(|_| panic!("OS CPU publication invariant violated"));
        Ok(0)
    }

    fn query_os(&mut self, owner: OsToken, request: Option<&CpuRequest>) -> Result<isize> {
        let hotplug = DeviceHotplugGuard::lock();
        self.verify_owned(&hotplug)?;
        drop(hotplug);
        let count = self
            .table
            .assigned_cpus(owner, &mut self.requests)
            .map_err(|_| EIO)?;
        let Some(request) = request else {
            return Ok(count as isize);
        };
        if request.count != count {
            return Err(EINVAL);
        }
        let mut writer = UserSlice::new(request.array, count * 4).writer();
        for &cpu in &self.requests[..count] {
            writer.write(&(cpu as i32))?;
        }
        UserSlice::new(request.count_address, 4)
            .writer()
            .write(&(count as i32))?;
        Ok(0)
    }
}

/// Caller holds CpuReadGuard. No references to mutable Linux masks escape.
fn observed_cpu(
    cpu: usize,
    _topology: &CpuReadGuard,
    _hotplug: &DeviceHotplugGuard,
) -> Result<HostCpuSnapshot> {
    // SAFETY: The caller holds CPU read-side exclusion. Bounds are checked
    // before reading mask words; x86_64 mask words and unsigned long are u64.
    unsafe {
        if cpu >= SMP_MAX_CPUS || cpu >= bindings::nr_cpu_ids as usize {
            return Err(EINVAL);
        }
        let word = cpu / 64;
        let mask = 1_u64 << (cpu % 64);
        let present = ptr::read_volatile(ptr::addr_of!(bindings::__cpu_present_mask.bits[word]));
        if present & mask == 0 {
            return Err(ENODEV);
        }
        let online = ptr::read_volatile(ptr::addr_of!(bindings::__cpu_online_mask.bits[word]));
        let hardware_id = default_cpu_present_to_apicid(cpu as i32);
        let device = bindings::get_cpu_device(cpu as u32);
        if device.is_null() {
            return Err(ENODEV);
        }
        // get_cpu_device returns the embedded device of Linux's struct cpu.
        // register_cpu and change_cpu_under_node maintain this node_id; its
        // lifetime and updates are excluded by the guards supplied above.
        let cpu_device = kernel::container_of!(device, bindings::cpu, dev);
        let node = ptr::read_volatile(ptr::addr_of!((*cpu_device).node_id));
        if hardware_id == u32::MAX || node < 0 {
            return Err(ENODEV);
        }
        Ok(HostCpuSnapshot {
            hardware_id,
            numa_node: node as u32,
            online: online & mask != 0,
        })
    }
}

struct LinuxCpuBatch<'a> {
    devices: &'a [Option<CpuDevice>; SMP_MAX_CPUS],
    _hotplug: &'a DeviceHotplugGuard,
}

impl HostCpuHotplug for LinuxCpuBatch<'_> {
    type Error = Error;

    fn observe(&mut self, cpu: usize) -> Result<HostCpuSnapshot> {
        let retained = self
            .devices
            .get(cpu)
            .and_then(Option::as_ref)
            .ok_or(ENODEV)?;
        let _topology = CpuReadGuard::lock();
        // SAFETY: Device-hotplug and CPU read guards protect discovery. The
        // retained reference keeps the original allocation alive for comparison.
        let current = unsafe { bindings::get_cpu_device(cpu as u32) };
        if current != retained.0 {
            return Err(ENODEV);
        }
        observed_cpu(cpu, &_topology, self._hotplug)
    }

    fn set_online(&mut self, cpu: usize, online: bool) -> Result {
        let retained = self
            .devices
            .get(cpu)
            .and_then(Option::as_ref)
            .ok_or(ENODEV)?;
        let _permission = TransitionTask::new(cpu);
        // SAFETY: The batch owns device_hotplug_lock and a retained reference;
        // CPU read-side exclusion has ended before either writer operation.
        let status = unsafe {
            if online {
                bindings::device_online(retained.0)
            } else {
                bindings::device_offline(retained.0)
            }
        };
        if status > 0 {
            return kernel::error::to_result(-(bindings::EALREADY as i32));
        }
        kernel::error::to_result(status)
    }
}

struct CpuRequest {
    array: usize,
    count: usize,
    count_address: usize,
}

impl CpuRequest {
    fn read(argument: usize, compat: bool) -> Result<Self> {
        let size = if compat {
            8
        } else {
            core::mem::size_of::<abi::IhkCpuRequest>()
        };
        let mut bytes = [0_u8; 16];
        UserSlice::new(argument, size)
            .reader()
            .read_slice(&mut bytes[..size])?;
        let (array, offset) = if compat {
            (
                u32::from_ne_bytes(bytes[..4].try_into().map_err(|_| EINVAL)?) as usize,
                4,
            )
        } else {
            (
                u64::from_ne_bytes(bytes[..8].try_into().map_err(|_| EINVAL)?) as usize,
                8,
            )
        };
        let count = i32::from_ne_bytes(bytes[offset..offset + 4].try_into().map_err(|_| EINVAL)?);
        if count < 0 || count as usize > SMP_MAX_CPUS || (count != 0 && array == 0) {
            return Err(EINVAL);
        }
        Ok(Self {
            array,
            count: count as usize,
            count_address: argument.checked_add(offset).ok_or(EFAULT)?,
        })
    }
}

struct ContextStorage(UnsafeCell<CpuContext>);
// SAFETY: Module init exclusively transfers the static context to its single
// pinned mutex. No subsequent code accesses this UnsafeCell directly.
unsafe impl Sync for ContextStorage {}
static CONTEXT: ContextStorage = ContextStorage(UnsafeCell::new(CpuContext::new()));
type ContextMutex = Mutex<&'static mut CpuContext>;
static PUBLISHED: AtomicPtr<ContextMutex> = AtomicPtr::new(ptr::null_mut());

pub(super) struct CpuController {
    mutex: Pin<Box<ContextMutex>>,
    hotplug_state: i32,
    irq_target_state: i32,
}

impl CpuController {
    /// Called once by module init, before the control device is published.
    pub(super) fn new() -> Result<Self> {
        // SAFETY: Module initialization is exclusive and this is the sole
        // access path to CONTEXT. Only its small reference moves onto the stack.
        let context = unsafe { &mut *CONTEXT.0.get() };
        let mutex = Box::pin_init(new_mutex!(context), GFP_KERNEL)?;
        let mut controller = Self {
            mutex,
            hotplug_state: -1,
            irq_target_state: -1,
        };
        controller.mutex.lock().initialize()?;
        // SAFETY: Callback/name remain resident until unregister under CPUHP
        // exclusion. No existing CPUs are invoked; policy starts unreserved.
        let state = unsafe {
            bindings::__cpuhp_setup_state(
                bindings::cpuhp_state_CPUHP_BP_PREPARE_DYN,
                c_str!("mckernel/cpu:prepare").as_char_ptr(),
                false,
                Some(allow_cpu_online),
                None,
                false,
            )
        };
        kernel::error::to_result(state)?;
        controller.hotplug_state = state;
        // SAFETY: This early teardown veto is resident until unregister. The
        // atomic route users are published under CPU read-side exclusion.
        let state = unsafe {
            bindings::__cpuhp_setup_state(
                bindings::cpuhp_state_CPUHP_AP_ONLINE_DYN,
                c_str!("mckernel/irq:online").as_char_ptr(),
                false,
                None,
                Some(allow_cpu_offline),
                false,
            )
        };
        kernel::error::to_result(state)?;
        controller.irq_target_state = state;
        PUBLISHED.store(
            (&*controller.mutex as *const ContextMutex).cast_mut(),
            Ordering::Release,
        );
        Ok(controller)
    }
}

impl Drop for CpuController {
    fn drop(&mut self) {
        PUBLISHED.store(ptr::null_mut(), Ordering::Release);
        if self.irq_target_state >= 0 {
            // SAFETY: OS and reservation module pins exclude this destructor
            // while any route remains; removal drains Linux CPUHP callbacks.
            unsafe { bindings::__cpuhp_remove_state(self.irq_target_state, false) };
        }
        if self.hotplug_state >= 0 {
            // SAFETY: Module teardown has no open control files or resource
            // pins. Linux removes and drains the callback under its CPU locks.
            unsafe { bindings::__cpuhp_remove_state(self.hotplug_state, false) };
        }
        let mut context = self.mutex.lock();
        for device in &mut context.devices {
            device.take();
        }
    }
}

pub(super) fn handles(command: u32) -> bool {
    matches!(
        command,
        abi::IHK_DEVICE_RESERVE_CPU
            | abi::IHK_DEVICE_RELEASE_CPU
            | abi::IHK_DEVICE_QUERY_CPU
            | abi::IHK_DEVICE_GET_NUM_CPUS
    )
}

/// The invoking miscdevice file pins THIS_MODULE throughout this call.
pub(super) fn ioctl(command: u32, argument: usize, compat: bool) -> Result<isize> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: Publication precedes misc_register. The file's module reference
    // prevents CpuController destruction until this call and file release end.
    let mut context = unsafe { &*published }.lock();
    if command == abi::IHK_DEVICE_GET_NUM_CPUS {
        let hotplug = DeviceHotplugGuard::lock();
        context.verify_owned(&hotplug)?;
        return Ok(context.available() as isize);
    }
    let request = CpuRequest::read(argument, compat)?;
    match command {
        abi::IHK_DEVICE_RESERVE_CPU => context.change(&request, true),
        abi::IHK_DEVICE_RELEASE_CPU => context.change(&request, false),
        abi::IHK_DEVICE_QUERY_CPU => context.query(&request),
        _ => Err(EINVAL),
    }
}

pub(super) fn handles_os(command: u32) -> bool {
    matches!(
        command,
        abi::IHK_OS_ASSIGN_CPU
            | abi::IHK_OS_RELEASE_CPU
            | abi::IHK_OS_QUERY_CPU
            | abi::IHK_OS_GET_NUM_CPUS
    )
}

/// Called only while IHK's OS object pins SMP and holds the operation lock.
pub(super) fn os_ioctl(
    owner: OsToken,
    command: u32,
    argument: usize,
    compat: bool,
) -> Result<isize> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The OS object's ProviderModule keeps the controller resident
    // throughout this checked callback; no context borrow escapes its lock.
    let mut context = unsafe { &*published }.lock();
    if command == abi::IHK_OS_GET_NUM_CPUS {
        return context.query_os(owner, None);
    }
    let request = CpuRequest::read(argument, compat)?;
    match command {
        abi::IHK_OS_ASSIGN_CPU => context.change_os(owner, &request, true),
        abi::IHK_OS_RELEASE_CPU => context.change_os(owner, &request, false),
        abi::IHK_OS_QUERY_CPU => context.query_os(owner, Some(&request)),
        _ => Err(EINVAL),
    }
}

/// Bounded native AP reset/re-online primitive for the later shutdown path.
///
/// The caller must already hold the exact OS operation/lease and have closed
/// admission. This is deliberately not registered as a v5 shutdown callback:
/// it only journals physical CPU reset/re-online proof and retains all logical,
/// memory, IRQ and module ownership for the remaining shutdown stages.
#[allow(dead_code)] // Intentionally unwired until the v5 STOP/ACK drain owns it.
pub(super) fn shutdown_reset_and_reonline(owner: OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: A future synchronous backend callback must retain the provider
    // module and exact owner lease through this operation. No journal reference
    // escapes the policy mutex or the device-hotplug exclusion.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    context.shutdown_reset_and_reonline(owner, &hotplug)
}

/// Release both resource classes before the exclusive OS destruction returns.
/// CPU lock precedes memory lock; both preflights finish before either commit.
pub(super) fn release_os_resources(owner: OsToken) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: IHK's DestroyGuard and ProviderModule pin this callback and its
    // controller until both classes have been returned to the reserved pool.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    context.verify_owned(&hotplug)?;
    drop(hotplug);
    let count = context
        .table
        .assigned_cpus(owner, &mut context.requests)
        .map_err(|_| EIO)?;
    if count == 0 {
        return super::smp_memory::release_os_resources(owner, || {});
    }
    let mut transaction = context
        .table
        .prepare_release(owner, &context.requests[..count], &mut context.journal)
        .map_err(|_| EIO)?;
    transaction.begin_external_effects().map_err(|_| EIO)?;
    // Memory calls commit_cpu only after its complete preflight, while both
    // context locks remain held. No fallible operation follows that callback.
    let mut cpu_transaction = Some(transaction);
    let result = super::smp_memory::release_os_resources(owner, || {
        cpu_transaction
            .take()
            .unwrap()
            .commit()
            .unwrap_or_else(|_| panic!("OS CPU cleanup invariant violated"));
    });
    if let Some(transaction) = cpu_transaction {
        // Memory preparation failed before any ownership changed. CPU's
        // external phase consisted only of logical preflight, so compensation
        // requires no Linux hotplug operation and restores the original table.
        transaction.compensated_rollback().map_err(|_| EIO)?;
    }
    result
}

/// Preserve CPU -> memory lock order while checking the first load prerequisite.
/// The IHK operation lock excludes resource calls for this OS during file read.
pub(super) fn load_os_image(owner: OsToken, image: &[u8]) -> Result {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The calling OS lease and provider-module owner pin this context;
    // no CPU or memory guard escapes the synchronous load callback.
    let mut context = unsafe { &*published }.lock();
    if context.query_os(owner, None)? == 0 {
        return Err(EINVAL);
    }
    super::smp_memory::load_os_image(owner, image)
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(super) struct BootCpu {
    pub(super) linux_id: u32,
    pub(super) hardware_id: u32,
    pub(super) numa_node: u32,
}

/// The guards cannot escape their acquiring task. Only this module constructs
/// a topology, after checking the canonical exact-generation CPU assignments.
pub(super) struct BootTopology<'a> {
    cpus: Vec<BootCpu>,
    saved: Vec<Arc<super::smp_topology::Cpu>>,
    linux_cpus: usize,
    hotplug: &'a DeviceHotplugGuard,
    read: &'a CpuReadGuard,
}

impl BootTopology<'_> {
    pub(super) fn cpus(&self) -> &[BootCpu] {
        &self.cpus
    }
    pub(super) fn saved(&self) -> &[Arc<super::smp_topology::Cpu>] {
        &self.saved
    }
    pub(super) fn linux_cpus(&self) -> usize {
        self.linux_cpus
    }
    pub(super) fn host_cpu(&self, cpu: usize) -> Result<HostCpuSnapshot> {
        observed_cpu(cpu, self.read, self.hotplug)
    }
}

fn with_boot_topology<T>(
    owner: OsToken,
    operation: impl FnOnce(&BootTopology<'_>) -> Result<T>,
) -> Result<T> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The IHK lease and provider module owner pin this synchronous
    // backend call and its published CPU context through operation completion.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    context.verify_owned(&hotplug)?;
    let read = CpuReadGuard::lock();
    let count = context
        .table
        .assigned_cpus(owner, &mut context.requests)
        .map_err(|_| EIO)?;
    if count == 0 {
        return Err(EINVAL);
    }
    let mut cpus = Vec::with_capacity(count, GFP_KERNEL)?;
    let mut saved = Vec::with_capacity(count, GFP_KERNEL)?;
    for &cpu in &context.requests[..count] {
        let slot = context.table.slot(cpu).map_err(|_| EIO)?;
        let actual = observed_cpu(cpu, &read, &hotplug)?;
        if actual.online
            || slot.owner() != Some(owner)
            || actual.hardware_id != slot.hardware_id()
            || actual.numa_node != slot.numa_node()
            || actual.hardware_id > i32::MAX as u32
        {
            return Err(EIO);
        }
        cpus.push(
            BootCpu {
                linux_id: cpu as u32,
                hardware_id: actual.hardware_id,
                numa_node: actual.numa_node,
            },
            GFP_KERNEL,
        )?;
        let snapshot = &context.devices[cpu].as_ref().ok_or(EIO)?.1;
        if snapshot.linux_id as usize != cpu || snapshot.apic_id != actual.hardware_id {
            return Err(EIO);
        }
        saved.push(snapshot.clone(), GFP_KERNEL)?;
    }
    // SAFETY: Linux fixes this bound under the retained CPU read guard.
    let linux_cpus = unsafe { bindings::nr_cpu_ids } as usize;
    operation(&BootTopology {
        cpus,
        saved,
        linux_cpus,
        hotplug: &hotplug,
        read: &read,
    })
}

pub(super) fn prepare_os_boot(
    owner: OsToken,
    kmsg: u64,
    kmsg_bytes: u64,
    trampoline: u64,
) -> Result {
    with_boot_topology(owner, |topology| {
        super::smp_memory::prepare_os_boot(owner, topology, kmsg, kmsg_bytes, trampoline)
    })
}

pub(super) fn start_os_boot(owner: OsToken) -> Result {
    let service = with_boot_topology(owner, |topology| {
        super::smp_memory::start_os_boot(owner, topology)
    })?;
    // The continuing send path revalidates its CPU under these same guards.
    // It must never wait for us while BOOT waits for its sysfs completions.
    service.activate_and_wait()
}

/// A short send-only borrow of the original assigned CPU/device identity.
/// The caller's retained started storage and resource module pins outlive it.
pub(super) fn with_runtime_target<T>(
    owner: OsToken,
    expected: BootCpu,
    operation: impl FnOnce(u32) -> Result<T>,
) -> Result<T> {
    let published = PUBLISHED.load(Ordering::Acquire);
    if published.is_null() {
        return Err(ENODEV);
    }
    // SAFETY: The continuing owner retains the module and original reservation.
    let mut guard = unsafe { &*published }.lock();
    let context = &mut **guard;
    let hotplug = DeviceHotplugGuard::lock();
    context.verify_owned(&hotplug)?;
    let read = CpuReadGuard::lock();
    let cpu = expected.linux_id as usize;
    let slot = context.table.slot(cpu).map_err(|_| EIO)?;
    let actual = observed_cpu(cpu, &read, &hotplug)?;
    if slot.state() != CpuState::Assigned
        || slot.owner() != Some(owner)
        || actual.online
        || actual.hardware_id != expected.hardware_id
        || actual.numa_node != expected.numa_node
        || context.devices.get(cpu).and_then(Option::as_ref).is_none()
    {
        return Err(EIO);
    }
    operation(expected.linux_id)
}
