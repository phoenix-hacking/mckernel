// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Opaque shared-list copy borrows. No callback/data bytes establish perf kind.
use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::mem::{size_of, MaybeUninit};
use core::ptr::{addr_of, null_mut, write};
use crate::abi::{CInt, CULong, Mckfd, Process};
use crate::waitq::{Waitq, WaitqEntry, waitq_init, waitq_init_entry,
    waitq_prepare_to_wait, waitq_finish_wait, waitq_wakeup};
use super::descriptors::Locked;

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const EBADF: CInt = 9;
const EBUSY: CInt = 16;
const PS_UNINTERRUPTIBLE: CInt = 4;
const FILE: &[u8] = concat!(file!(), "\0").as_bytes();
unsafe extern "C" { fn schedule(); }

struct Record {
    next: *mut Record,
    next_free: *mut Record,
    process: *mut Process,
    node: *mut Mckfd,
    generation: u64,
    readers: usize,
    references: usize,
    registered: bool,
    closing: bool,
    retired: bool,
    failure: CInt,
    queue: MaybeUninit<Waitq>,
}
struct Registry { first: *mut Record, deferred: *mut Record, generation: u64 }
struct Cell(UnsafeCell<Registry>);
unsafe impl Sync for Cell {}
static REGISTRY: Cell = Cell(UnsafeCell::new(Registry {
    first: null_mut(), deferred: null_mut(), generation: 1,
}));

unsafe fn state(_r: &mut Locked) -> &mut Registry { unsafe { &mut *REGISTRY.0.get() } }
unsafe fn find_node(node: *mut Mckfd, r: &mut Locked) -> *mut Record {
    let mut row = unsafe { state(r).first };
    while !row.is_null() {
        if unsafe { (*row).node == node } { return row; }
        row = unsafe { (*row).next };
    }
    null_mut()
}
unsafe fn release(row: *mut Record, r: &mut Locked) {
    let n = unsafe { (*row).references }.checked_sub(1).expect("copy metadata released twice");
    unsafe { (*row).references = n };
    if n == 0 {
        assert!(!unsafe { (*row).registered } && unsafe { (*row).readers == 0 });
        let registry = unsafe { state(r) };
        unsafe { (*row).retired = true; (*row).next_free = registry.deferred; registry.deferred = row; }
    }
}
unsafe fn unregister(row: *mut Record, r: &mut Locked) {
    assert!(unsafe { (*row).registered && (*row).readers == 0 });
    let registry = unsafe { state(r) };
    let mut link = &mut registry.first as *mut *mut Record;
    while unsafe { *link } != row {
        assert!(!unsafe { *link }.is_null(), "copy registry identity missing");
        link = unsafe { &mut (**link).next };
    }
    unsafe {
        *link = (*row).next; (*row).next = null_mut();
        (*row).registered = false; (*row).retired = true;
        release(row, r); // Only the registry metadata reference, not a reader.
    }
}
unsafe fn remember_failure(row: *mut Record, error: CInt) {
    // A failed close/drain does not authorize a callback, free, retry or new
    // copy. The registry retains its opaque identity and original first error.
    unsafe {
        (*row).closing = true;
        if (*row).failure == 0 { (*row).failure = error; }
    }
}

pub(super) struct PreparedBorrow { record: *mut Record }
pub(super) struct CopyPin { record: *mut Record, generation: u64 }
pub(super) struct CloseBorrow { record: *mut Record, generation: u64 }

impl PreparedBorrow {
    /// Allocate only in the real constructor process context, outside P/R.
    /// Queue initialization uses its final stable address before visibility.
    pub(super) unsafe fn allocate(flags: CULong) -> Result<Self, CInt> {
        let bytes = CInt::try_from(size_of::<Record>()).map_err(|_| -EINVAL)?;
        let row = unsafe { crate::mem_helpers::kmalloc_tracked(bytes, flags,
            FILE.as_ptr().cast_mut().cast(), line!() as CInt) }.cast::<Record>();
        if row.is_null() { return Err(-ENOMEM); }
        unsafe {
            write(row, Record { next: null_mut(), next_free: null_mut(), process: null_mut(),
                node: null_mut(), generation: 0, readers: 0, references: 1,
                registered: false, closing: false, retired: false, failure: 0,
                queue: MaybeUninit::uninit() });
            waitq_init((*row).queue.as_mut_ptr());
        }
        Ok(Self { record: row })
    }

    /// Actual parent P protects the real list membership and node lifetime.
    /// The caller also holds its real checked-positive parent VM snapshot ref.
    /// No allocation/wait/finalizer occurs here. Unused preparation and every
    /// CopyPin drop only AFTER P/R unlock; a node is opaque throughout.
    pub(super) unsafe fn acquire_locked(&mut self, process: *mut Process,
        node: *mut Mckfd, r: &mut Locked) -> Result<CopyPin, CInt> {
        if process.is_null() || node.is_null() { return Err(-EINVAL); }
        let existing = unsafe { find_node(node, r) };
        if !existing.is_null() {
            if unsafe { (*existing).process != process || (*existing).retired } { return Err(-EINVAL); }
            let failure = unsafe { (*existing).failure };
            if failure != 0 { return Err(failure); }
            if unsafe { (*existing).closing } { return Err(-EBADF); }
            let readers = unsafe { (*existing).readers }.checked_add(1).ok_or(-EINVAL)?;
            let references = unsafe { (*existing).references }.checked_add(1).ok_or(-EINVAL)?;
            if unsafe { (*existing).references == 0 || (*existing).generation == 0 } { return Err(-EINVAL); }
            unsafe { (*existing).readers = readers; (*existing).references = references; }
            return Ok(CopyPin { record: existing, generation: unsafe { (*existing).generation } });
        }
        if self.record.is_null() { return Err(-EINVAL); }
        let registry = unsafe { state(r) };
        let next = registry.generation.checked_add(1).ok_or(-EINVAL)?;
        if registry.generation == 0 { return Err(-EINVAL); }
        let row = self.record;
        // Never move/reinitialize its already self-linked genuine Waitq.
        unsafe {
            (*row).process = process; (*row).node = node;
            (*row).generation = registry.generation; (*row).readers = 1;
            (*row).references = 2; // Registry plus this actual reader metadata pin.
            (*row).registered = true; (*row).next = registry.first;
            registry.first = row; registry.generation = next;
        }
        self.record = null_mut();
        Ok(CopyPin { record: row, generation: unsafe { (*row).generation } })
    }
}
impl Drop for PreparedBorrow {
    fn drop(&mut self) {
        if !self.record.is_null() {
            let mut r = unsafe { Locked::take() };
            unsafe { release(self.record, &mut r) };
        }
    }
}
impl Drop for CopyPin {
    fn drop(&mut self) {
        let row = self.record;
        let wake = {
            let mut r = unsafe { Locked::take() };
            assert!(unsafe { (*row).generation == self.generation && (*row).references > 0 });
            let n = unsafe { (*row).readers }.checked_sub(1).expect("copy reader released twice");
            unsafe { (*row).readers = n };
            if n == 0 && !unsafe { (*row).closing } {
                // No close owner exists. Only metadata is detached; this never
                // unlinks/frees the actual descriptor or invokes its callback.
                unsafe { unregister(row, &mut r) };
            }
            n == 0
        };
        // The CopyPin metadata reference is STILL live while this wake runs.
        // A closing waiter can observe readers0 and finish, but cannot free the
        // queue beneath this final wake: release our metadata reference LAST.
        if wake { unsafe { waitq_wakeup((*row).queue.as_mut_ptr()) }; }
        let mut r = unsafe { Locked::take() };
        unsafe { release(row, &mut r) };
    }
}

/// Actual ordinary-close lookup still owns P and will unlink BEFORE unlock.
/// This is only an opaque lifetime marker, never a semantic perf-kind result.
pub(super) unsafe fn mark_close_under_p(process: *mut Process,
    node: *mut Mckfd) -> Result<Option<CloseBorrow>, CInt> {
    if process.is_null() || node.is_null() { return Err(-EINVAL); }
    let mut r = unsafe { Locked::take() };
    let row = unsafe { find_node(node, &mut r) };
    if row.is_null() { return Ok(None); }
    if unsafe { (*row).process != process || (*row).retired } { return Err(-EINVAL); }
    let failure = unsafe { (*row).failure };
    if failure != 0 { return Err(failure); }
    if unsafe { (*row).closing } { return Err(-EBUSY); }
    let references = unsafe { (*row).references }.checked_add(1).ok_or(-EINVAL)?;
    if unsafe { (*row).references == 0 } { return Err(-EINVAL); }
    unsafe { (*row).references = references; (*row).closing = true; }
    Ok(Some(CloseBorrow { record: row, generation: unsafe { (*row).generation } }))
}

struct WaitRegistration { queue: *mut Waitq, entry: *mut WaitqEntry }
impl Drop for WaitRegistration {
    fn drop(&mut self) { unsafe { waitq_finish_wait(self.queue, self.entry) }; }
}
impl CloseBorrow {
    unsafe fn wait_readers(&self) -> Result<(), CInt> {
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        if cpu.is_null() { return Err(-EINVAL); }
        let current = unsafe { addr_of!((*cpu).current).read() };
        if current.is_null() || unsafe { addr_of!((*current).proc).read() != (*self.record).process } {
            return Err(-EINVAL);
        }
        {
            let _r = unsafe { Locked::take() };
            if unsafe { (*self.record).failure != 0 } { return Err(unsafe { (*self.record).failure }); }
            if unsafe { (*self.record).readers == 0 } { return Ok(()); }
        }
        let mut entry = core::pin::pin!(MaybeUninit::<WaitqEntry>::uninit());
        let entry_ptr = unsafe { entry.as_mut().get_unchecked_mut() }.as_mut_ptr();
        let queue = unsafe { (*self.record).queue.as_mut_ptr() };
        unsafe { waitq_init_entry(entry_ptr, current.cast::<c_void>()) };
        let registration = WaitRegistration { queue, entry: entry_ptr };
        loop {
            // Register before checking the predicate; the final real CopyPin
            // cannot lose this wake or let metadata refs become reader counts.
            unsafe { waitq_prepare_to_wait(queue, entry_ptr, PS_UNINTERRUPTIBLE) };
            let ready = {
                let _r = unsafe { Locked::take() };
                let failure = unsafe { (*self.record).failure };
                if failure != 0 { return Err(failure); }
                unsafe { (*self.record).readers == 0 }
            };
            if ready { drop(registration); return Ok(()); }
            unsafe { schedule() };
        }
    }

    /// Only outside P/R/S/hash/update/IRQ/runqueue exclusion, on the original
    /// ordinary-close Process/Thread route AFTER real list unlink. Success is
    /// permission only for that caller's original callback/free; this module
    /// never performs a backend, descriptor or host operation itself.
    pub(super) unsafe fn wait_unlinked(mut self) -> Result<(), CInt> {
        let row = self.record;
        if let Err(error) = unsafe { self.wait_readers() } {
            let _r = unsafe { Locked::take() };
            unsafe { remember_failure(row, error) };
            return Err(error);
        }
        let mut r = unsafe { Locked::take() };
        if unsafe { (*row).generation != self.generation || !(*row).registered
            || !(*row).closing || (*row).retired || (*row).readers != 0 } {
            unsafe { remember_failure(row, -EINVAL) };
            return Err(-EINVAL);
        }
        let failure = unsafe { (*row).failure };
        if failure != 0 { return Err(failure); }
        unsafe { unregister(row, &mut r) };
        self.record = null_mut();
        unsafe { release(row, &mut r) };
        Ok(())
    }
}
impl Drop for CloseBorrow {
    fn drop(&mut self) {
        if !self.record.is_null() {
            // Failure/abandonment keeps the registry's closing ownership; no
            // retry or callback/free permission follows from a dropped guard.
            let mut r = unsafe { Locked::take() };
            unsafe { remember_failure(self.record, -EINVAL); release(self.record, &mut r); }
        }
    }
}

/// The caller's checked-positive VM snapshot ref excludes live readers at this
/// real final drain. This path may hold P: never wait/allocate/free/call backend.
/// An active-reader/close mismatch retains the first error and its opaque node;
/// caller must preserve it rather than pretend that final free became safe.
pub(super) unsafe fn retire_before_free(node: *mut Mckfd) -> Result<bool, CInt> {
    if node.is_null() { return Err(-EINVAL); }
    let mut r = unsafe { Locked::take() };
    let row = unsafe { find_node(node, &mut r) };
    if row.is_null() { return Ok(false); }
    let failure = unsafe { (*row).failure };
    if failure != 0 { return Err(failure); }
    if unsafe { (*row).readers != 0 || (*row).closing } {
        unsafe { remember_failure(row, -EBUSY) };
        return Err(-EBUSY);
    }
    unsafe { (*row).closing = true; unregister(row, &mut r) };
    Ok(true)
}

/// Actual process-context safe point, outside P/R and all callback exclusions.
/// Only metadata with zero refs/readers and no registered/queued users is freed.
/// No raw Process/node dereference, host offload or original callback occurs.
pub(super) unsafe fn drain_deferred() {
    let mut row = {
        let mut r = unsafe { Locked::take() };
        let registry = unsafe { state(&mut r) };
        let first = registry.deferred; registry.deferred = null_mut(); first
    };
    while !row.is_null() {
        let next = unsafe { (*row).next_free };
        assert!(unsafe { (*row).retired && !(*row).registered
            && (*row).references == 0 && (*row).readers == 0 });
        unsafe { crate::mem_helpers::kfree_tracked(row.cast(),
            FILE.as_ptr().cast_mut().cast(), line!() as CInt) };
        row = next;
    }
}
