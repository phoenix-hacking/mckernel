// SPDX-License-Identifier: GPL-2.0
//! Native per-process executable and application ownership across OS files.

use super::{application_image as image, mcctrl_exec::Executable, mcctrl_vm::Mirror};
use core::{
    ffi::c_void,
    pin::Pin,
    ptr::{self, NonNull},
    sync::atomic::{AtomicBool, AtomicPtr, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
    uaccess::UserSlice,
};

// SAFETY: IHK is the real namespaced module dependency. These operations use
// only kernel-owned output/connection storage and retain exact OS/backend owners.
extern "C" {
    fn ihk_os_application_open_v1(
        slot: u32,
        generation: u64,
        version: u32,
        pid: i32,
        output: *mut *mut c_void,
    ) -> i32;
    fn ihk_os_application_invoke_v1(
        context: *mut c_void,
        command: u32,
        buffer: *mut u8,
        bytes: usize,
    ) -> i64;
    fn ihk_os_application_close_v1(context: *mut c_void);
}

pub(super) struct Registration {
    context: NonNull<c_void>,
    slot: u32,
    generation: u64,
    pid: i32,
    armed: AtomicBool,
    operation: Pin<Box<Mutex<()>>>,
    mapping: Pin<Box<Mutex<Option<Arc<Mirror>>>>>,
    // Mirror files can outlive all mcos file bindings and their Process owner.
    // Retain the referenced PID independently for that complete lifetime.
    _pid: ProcessId,
}

// SAFETY: The IHK connection contract permits concurrent borrows and ownership
// transfer. Our process mutex publishes it; only its final destructor invokes it.
unsafe impl Send for Registration {}
// SAFETY: The IHK connection supports concurrent invocations. The operation
// mutex serializes image preparation; the mapping publication lock is short.
unsafe impl Sync for Registration {}

impl Registration {
    fn acquire(slot: u32, generation: u64, identity: ProcessId) -> Result<Arc<Self>> {
        let pid = identity.number()?;
        let operation = Box::pin_init(new_mutex!(()), GFP_KERNEL)?;
        let mapping = Box::pin_init(new_mutex!(None), GFP_KERNEL)?;
        let mut context = ptr::null_mut();
        // SAFETY: mcctrl pins IHK, and this output remains exclusively borrowed
        // until the checked open transfers its independently leased connection.
        kernel::error::to_result(unsafe {
            ihk_os_application_open_v1(
                slot,
                generation,
                super::application_abi::VERSION,
                pid,
                &mut context,
            )
        })?;
        Arc::new(Self {
            context: NonNull::new(context).ok_or(EIO)?,
            slot,
            generation,
            pid,
            armed: AtomicBool::new(false),
            operation,
            mapping,
            _pid: identity,
        }, GFP_KERNEL)
    }

    pub(super) fn invoke(&self, command: u32, bytes: &mut [u8]) -> Result {
        // SAFETY: This Arc retains the kernel connection through the exclusive
        // byte borrow. The backend copies any published work into its own pages.
        let status = unsafe { ihk_os_application_invoke_v1(self.context.as_ptr(), command, bytes.as_mut_ptr(), bytes.len()) };
        if status > 0 || status < -4095 { return Err(EIO); }
        kernel::error::to_result(status as i32).map(|_| ())
    }

    fn prepare_image(self: &Arc<Self>, argument: usize, compat: bool) -> Result<isize> {
        if compat { return Err(kernel::error::to_result(-95).unwrap_err()); }
        // This is an operation serializer, not a publication/OS lock. The
        // continuing service and VM faults do not need it to make progress.
        let _operation = self.operation.lock();
        if self.mapping.lock().is_some() { return Err(EBUSY); }
        let mut header = zero_bytes(image::HEADER)?;
        UserSlice::new(argument, header.len()).reader().read_slice(&mut header)?;
        let descriptor = image::descriptor_bytes(&header).map_err(errno)?;
        let args = image::word(&header, image::ARGS_LEN).map_err(errno)? as usize;
        let envs = image::word(&header, image::ENVS_LEN).map_err(errno)? as usize;
        if !(16..=image::MAX_FLAT_BYTES).contains(&args) || !(16..=image::MAX_FLAT_BYTES).contains(&envs) { return Err(errno(-7)); }
        let total = descriptor.checked_add(args).and_then(|n| n.checked_add(envs)).ok_or(errno(-75))?;
        let mut bytes = zero_bytes(total)?;
        bytes[..image::HEADER].copy_from_slice(&header);
        UserSlice::new(argument.checked_add(image::HEADER).ok_or(errno(-75))?, descriptor - image::HEADER)
            .reader().read_slice(&mut bytes[image::HEADER..descriptor])?;
        let argv = image::word(&header, image::ARGS).map_err(errno)? as usize;
        let envp = image::word(&header, image::ENVS).map_err(errno)? as usize;
        UserSlice::new(argv, args).reader().read_slice(&mut bytes[descriptor..descriptor + args])?;
        UserSlice::new(envp, envs).reader().read_slice(&mut bytes[descriptor + args..])?;
        bytes[image::PID..image::PID + 4].copy_from_slice(&self.pid.to_le_bytes());
        for (index, value) in super::mcctrl_exec::credential_values().iter().enumerate() {
            let offset = image::CREDENTIALS + index * 4;
            bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
        }
        image::put_word(&mut bytes, image::USER_START, 0).map_err(errno)?;
        image::put_word(&mut bytes, image::USER_END, image::USER_LIMIT).map_err(errno)?;
        // SAFETY: Exact scalar identities belong to our retained connection.
        let cpus = unsafe { super::ihk_os_topology_query_v1(self.slot, self.generation, super::abi::MCEXEC_UP_GET_CPU) };
        if cpus <= 0 { return Err(if cpus < 0 { errno(cpus as i32) } else { EINVAL }); }
        image::Input::parse(&bytes, cpus as usize).map_err(errno)?;
        let mirror = Mirror::reserve(self.clone())?;
        *self.mapping.lock() = Some(mirror.clone());
        image::put_word(&mut bytes, image::USER_END, mirror.end).map_err(errno)?;
        let result = image::Input::parse(&bytes, cpus as usize).map_err(errno)
            .and_then(|_| self.invoke(super::application_abi::PREPARE, &mut bytes));
        if let Err(error) = result {
            if mirror.unmap().is_ok() { *self.mapping.lock() = None; }
            return Err(error);
        }
        UserSlice::new(argument, descriptor).writer().write_slice(&bytes[..descriptor])?;
        pr_info!("application_image=prepared os={} generation={} pid={} sections={} cpu={}\n",
            self.slot, self.generation, self.pid, (descriptor - image::HEADER) / image::SECTION,
            image::integer(&bytes, image::CPU).map_err(errno)?);
        Ok(0)
    }

    fn transfer_image(&self, argument: usize, compat: bool) -> Result<isize> {
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.current()?;
        let mut descriptor = [0; 32];
        let length = if compat { 16 } else { 32 };
        UserSlice::new(argument, length).reader().read_slice(&mut descriptor[..length])?;
        let (physical, user, size, direction) = if compat {
            (u32::from_le_bytes(descriptor[0..4].try_into().unwrap()) as u64,
             u32::from_le_bytes(descriptor[4..8].try_into().unwrap()) as usize,
             u32::from_le_bytes(descriptor[8..12].try_into().unwrap()) as usize, descriptor[12])
        } else {
            (image::word(&descriptor, 0).map_err(errno)?, image::word(&descriptor, 8).map_err(errno)? as usize,
             image::word(&descriptor, 16).map_err(errno)? as usize, descriptor[24])
        };
        if size == 0 || size > image::MAX_FLAT_BYTES || direction > 1 { return Err(EINVAL); }
        user.checked_add(size).ok_or(errno(-75))?;
        physical.checked_add(size as u64).ok_or(errno(-75))?;
        let mut bytes = zero_bytes(16 + size)?;
        image::put_word(&mut bytes, 0, physical).map_err(errno)?;
        image::put_word(&mut bytes, 8, direction as u64).map_err(errno)?;
        if direction == 0 { UserSlice::new(user, size).reader().read_slice(&mut bytes[16..])?; }
        self.invoke(super::application_abi::TRANSFER, &mut bytes)?;
        if direction == 1 { UserSlice::new(user, size).writer().write_slice(&bytes[16..])?; }
        Ok(0)
    }

    fn clear_user_space(&self, argument: usize, compat: bool) -> Result<isize> {
        let mut bytes = [0; 16];
        let length = if compat { 8 } else { 16 };
        UserSlice::new(argument, length).reader().read_slice(&mut bytes[..length])?;
        let (start, end) = if compat {
            (u32::from_le_bytes(bytes[..4].try_into().unwrap()) as u64, u32::from_le_bytes(bytes[4..8].try_into().unwrap()) as u64)
        } else { (image::word(&bytes, 0).map_err(errno)?, image::word(&bytes, 8).map_err(errno)?) };
        let mirror = self.mapping.lock().clone().ok_or(EINVAL)?;
        mirror.clear(start, end)?;
        Ok(0)
    }
}

fn errno(code: i32) -> Error { kernel::error::to_result(code).err().unwrap_or(EIO) }

fn zero_bytes(length: usize) -> Result<Vec<u8>> {
    let mut bytes = Vec::with_capacity(length, GFP_KERNEL)?;
    for _ in 0..length { bytes.push(0, GFP_KERNEL)?; }
    Ok(bytes)
}

impl Drop for Registration {
    fn drop(&mut self) {
        if self.armed.load(Ordering::Acquire) {
            // SAFETY: The process's PID and this connection remain owned until
            // cleanup finishes. The continuing service owns any request whose
            // acknowledgement arrives after the bounded waiter has departed.
            let status = unsafe {
                ihk_os_application_invoke_v1(
                    self.context.as_ptr(),
                    super::application_abi::CLEANUP,
                    ptr::null_mut(),
                    0,
                )
            };
            pr_info!(
                "application_process=release os={} generation={} pid={} cleanup_errno={}\n",
                self.slot,
                self.generation,
                self.pid,
                status
            );
        }
        // SAFETY: Return exactly the successful connection after invocation.
        // A failed/racing publication remains unarmed and cancels only its own
        // reserved descriptor; it cannot clean up the winning registration.
        unsafe { ihk_os_application_close_v1(self.context.as_ptr()) };
    }
}

/// Linux's referenced thread-group PID, stable across namespace-number reuse
/// and leader replacement. The kernel owns the object's atomic reference count.
struct ProcessId(NonNull<bindings::pid>);

impl ProcessId {
    fn current() -> Result<Self> {
        // SAFETY: get_current is valid for this calling task; get_task_pid takes
        // its own reference under Linux's RCU protection before returning.
        let pid = unsafe {
            bindings::get_task_pid(bindings::get_current(), bindings::pid_type_PIDTYPE_TGID)
        };
        Ok(Self(NonNull::new(pid).ok_or(ESRCH)?))
    }
    fn same(&self, other: &Self) -> bool {
        self.0 == other.0
    }

    fn number(&self) -> Result<i32> {
        // SAFETY: The referenced PID and permanent initial namespace outlive
        // this call. The guest identity uses the host-global number, while the
        // process registry continues to distinguish referenced PID objects.
        let pid = unsafe {
            bindings::pid_nr_ns(self.0.as_ptr(), ptr::addr_of_mut!(bindings::init_pid_ns))
        };
        if pid <= 0 {
            return Err(ESRCH);
        }
        Ok(pid)
    }
}

// SAFETY: Linux permits owned PID references to move between tasks; the opaque
// object is accessed only by its exported reference operations and identity.
unsafe impl Send for ProcessId {}
unsafe impl Sync for ProcessId {}

impl Drop for ProcessId {
    fn drop(&mut self) {
        // SAFETY: Exactly one successful get_task_pid reference is released.
        unsafe { bindings::put_pid(self.0.as_ptr()) };
    }
}

#[pin_data]
struct Process {
    slot: u32,
    generation: u64,
    #[pin]
    executable: Mutex<Option<Executable>>,
    #[pin]
    registration: Mutex<Option<Arc<Registration>>>,
    // Field destruction closes the executable and application before this PID.
    pid: ProcessId,
}

impl Process {
    fn matches(&self, slot: u32, generation: u64, pid: &ProcessId) -> bool {
        self.slot == slot && self.generation == generation && self.pid.same(pid)
    }

    fn replace(&self, executable: Option<Executable>) -> bool {
        let old = core::mem::replace(&mut *self.executable.lock(), executable);
        let found = old.is_some();
        // The process lock protects publication only; VFS release runs after it.
        drop(old);
        found
    }
}

struct Entry {
    process: Arc<Process>,
    files: usize,
}

type Table = Mutex<Vec<Entry>>;
static PUBLISHED: AtomicPtr<Table> = AtomicPtr::new(ptr::null_mut());

pub(super) struct Registry(Pin<Box<Table>>);

impl Registry {
    pub(super) fn new() -> Result<Self> {
        let table = Box::pin_init(new_mutex!(Vec::new()), GFP_KERNEL)?;
        PUBLISHED
            .compare_exchange(
                ptr::null_mut(),
                ptr::from_ref(&*table).cast_mut(),
                Ordering::AcqRel,
                Ordering::Acquire,
            )
            .map_err(|_| EBUSY)?;
        Ok(Self(table))
    }
}

impl Drop for Registry {
    fn drop(&mut self) {
        // Every published process is held by at least one IHK-owned file
        // binding, whose mcctrl module reference excludes registry destruction.
        assert!(self.0.lock().is_empty());
        assert!(
            PUBLISHED.swap(ptr::null_mut(), Ordering::AcqRel) == ptr::from_ref(&*self.0).cast_mut()
        );
    }
}

fn table() -> &'static Table {
    let table = PUBLISHED.load(Ordering::Acquire);
    assert!(!table.is_null());
    // SAFETY: Only IHK-pinned mcctrl file callbacks and binding destructors call
    // this private helper; the owning Registry outlives all of those callers.
    unsafe { &*table }
}

struct Binding(Arc<Process>);

impl Binding {
    fn acquire(slot: u32, generation: u64, pid: ProcessId) -> Result<Self> {
        let mut entries = table().lock();
        for entry in &mut *entries {
            if entry.process.matches(slot, generation, &pid) {
                entry.files = entry
                    .files
                    .checked_add(1)
                    .ok_or_else(|| kernel::error::to_result(-75).unwrap_err())?;
                return Ok(Self(entry.process.clone()));
            }
        }
        let process = Arc::pin_init(
            try_pin_init!(Process {
                slot, generation, executable <- new_mutex!(None),
                registration <- new_mutex!(None), pid,
            }),
            GFP_KERNEL,
        )?;
        entries.push(
            Entry {
                process: process.clone(),
                files: 1,
            },
            GFP_KERNEL,
        )?;
        Ok(Self(process))
    }
}

impl Drop for Binding {
    fn drop(&mut self) {
        let removed = {
            let mut entries = table().lock();
            let index = entries
                .iter()
                .position(|entry| Arc::ptr_eq(&entry.process, &self.0))
                .expect("native process binding lost its registry entry");
            assert!(entries[index].files != 0);
            entries[index].files -= 1;
            if entries[index].files == 0 {
                Some(entries.swap_remove(index))
            } else {
                None
            }
        };
        // Both this binding and the removed entry retain the process until the
        // publication lock ends. Final executable/PID cleanup is outside it.
        drop(removed);
    }
}

pub(super) struct Context {
    pub(super) slot: u32,
    pub(super) generation: u64,
    bindings: Pin<Box<Mutex<Vec<Binding>>>>,
}

impl Context {
    pub(super) fn new(slot: u32, generation: u64) -> Result<Self> {
        Ok(Self {
            slot,
            generation,
            bindings: Box::pin_init(new_mutex!(Vec::new()), GFP_KERNEL)?,
        })
    }

    fn process(&self) -> Result<Arc<Process>> {
        let pid = ProcessId::current()?;
        let mut bindings = self.bindings.lock();
        for binding in &*bindings {
            if binding.0.pid.same(&pid) {
                return Ok(binding.0.clone());
            }
        }
        // Lock order: file bindings -> global process table; neither path takes
        // those locks while holding the per-process executable mutex.
        let binding = Binding::acquire(self.slot, self.generation, pid)?;
        let process = binding.0.clone();
        bindings.push(binding, GFP_KERNEL)?;
        Ok(process)
    }

    pub(super) fn open_executable(&self, argument: usize) -> Result<isize> {
        // All pathname reads, VFS hooks, exclusion and canonical-path checks
        // finish before acquiring any publication lock. Failure preserves the
        // process's previous executable and balances the temporary file owner.
        let executable = Executable::open(argument)?;
        self.process()?.replace(Some(executable));
        Ok(0)
    }

    pub(super) fn close_executable(&self) -> Result<isize> {
        let pid = ProcessId::current()?;
        let process = {
            let entries = table().lock();
            entries
                .iter()
                .find(|entry| entry.process.matches(self.slot, self.generation, &pid))
                .map(|entry| entry.process.clone())
        };
        // Preserve mcctrl_control_close_exec_body_result's unusual positive
        // EINVAL when no executable exists, including a repeated close.
        Ok(if process.is_some_and(|process| process.replace(None)) {
            0
        } else {
            22
        })
    }

    pub(super) fn create_process(&self, argument: usize, compat: bool) -> Result<isize> {
        if argument != 0 {
            // Legacy non-null CREATE_PPD also clears Linux mirror VMAs after
            // fork. Preserve real user-copy failures, but do not claim that VM
            // operation until its adapter exists. No registration is published.
            let mut descriptor = [0u8; 24];
            let bytes = if compat { 12 } else { 24 };
            UserSlice::new(argument, bytes)
                .reader()
                .read_slice(&mut descriptor[..bytes])?;
            return Err(kernel::error::to_result(-95).unwrap_err());
        }
        let process = self.process()?;
        if process.registration.lock().is_some() {
            return Err(EINVAL);
        }
        let pid = process.pid.number()?;
        let registration = Registration::acquire(self.slot, self.generation, ProcessId::current()?)?;
        {
            let mut published = process.registration.lock();
            if published.is_some() {
                return Err(EINVAL);
            }
            registration.armed.store(true, Ordering::Release);
            *published = Some(registration);
        }
        pr_info!(
            "application_process=registered os={} generation={} pid={}\n",
            self.slot,
            self.generation,
            pid
        );
        Ok(0)
    }

    fn registered(&self) -> Result<Arc<Registration>> {
        let process = self.process()?;
        let registration = process.registration.lock().clone().ok_or(EINVAL)?;
        Ok(registration)
    }

    pub(super) fn prepare_image(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.prepare_image(argument, compat)
    }

    pub(super) fn transfer_image(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.transfer_image(argument, compat)
    }

    pub(super) fn clear_user_space(&self, argument: usize, compat: bool) -> Result<isize> {
        self.registered()?.clear_user_space(argument, compat)
    }
}
