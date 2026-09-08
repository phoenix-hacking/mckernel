// SPDX-License-Identifier: GPL-2.0
//! Native per-process executable ownership shared by the process's OS files.

use super::mcctrl_exec::Executable;
use core::{
    pin::Pin,
    ptr::{self, NonNull},
    sync::atomic::{AtomicPtr, Ordering},
};
use kernel::{
    bindings,
    prelude::*,
    sync::{new_mutex, Arc, Mutex},
};

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
    pid: ProcessId,
    #[pin]
    executable: Mutex<Option<Executable>>,
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
                slot, generation, pid, executable <- new_mutex!(None),
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
}
