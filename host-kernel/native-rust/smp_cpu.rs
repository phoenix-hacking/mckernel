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
    sync::atomic::{AtomicBool, AtomicPtr, Ordering},
};
use kernel::{
    bindings, c_str,
    prelude::*,
    sync::{new_mutex, Mutex},
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
}

static BLOCK_ONLINE: [AtomicBool; SMP_MAX_CPUS] = [const { AtomicBool::new(false) }; SMP_MAX_CPUS];
static ALLOWED_TASK: [AtomicPtr<bindings::task_struct>; SMP_MAX_CPUS] =
    [const { AtomicPtr::new(ptr::null_mut()) }; SMP_MAX_CPUS];

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

struct CpuDevice(*mut bindings::device);

// SAFETY: The retained Linux reference can be released on any task. Access is
// exclusively under the policy mutex and Linux's device hotplug lock.
unsafe impl Send for CpuDevice {}

impl Drop for CpuDevice {
    fn drop(&mut self) {
        // SAFETY: This non-Copy value owns exactly one successful get_device.
        unsafe { bindings::put_device(self.0) };
    }
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
            self.devices[cpu] = Some(CpuDevice(device));
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
    fn verify_owned(&mut self, hotplug: &DeviceHotplugGuard) -> Result {
        if self.poisoned {
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
