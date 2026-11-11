// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private, unwired perf ownership candidate; actual source review precedes selection.
// This sleepable gate belongs ONLY to process-context host numeric-FD forwarding.

use core::cell::UnsafeCell;
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::marker::PhantomData;
use core::ptr::{addr_of, write};
use core::sync::atomic::{AtomicBool, Ordering};
use crate::abi::CInt;
use crate::waitq::{Waitq, WaitqEntry, waitq_init, waitq_init_entry,
    waitq_prepare_to_wait, waitq_finish_wait, waitq_wakeup};

const EINVAL: CInt = 22;
const EBADF: CInt = 9;
// Exact selected kernel/include/process.h:68, not a new scheduler state.
const PS_UNINTERRUPTIBLE: CInt = 0x4;
unsafe extern "C" { fn schedule(); }

/// Heap/owner-record-pinned storage. Initialization finishes before publication.
/// Its enclosing live DescriptorPin retains it while ANY waiter/guard uses it.
pub(super) struct ForwardGate {
    busy: AtomicBool,
    closing: AtomicBool,
    queue: UnsafeCell<MaybeUninit<Waitq>>,
}

// Only the two atomic state fields and genuine internally locked Waitq are shared.
unsafe impl Sync for ForwardGate {}
unsafe impl Send for ForwardGate {}

pub(crate) struct ForwardGuard<'a> { gate: &'a ForwardGate, not_send: PhantomData<*mut ()> }
impl Drop for ForwardGuard<'_> {
    fn drop(&mut self) {
        self.gate.busy.store(false, Ordering::Release);
        // No P/R/state lock is held. Only this gate's actual waiters are woken.
        unsafe { waitq_wakeup((*self.gate.queue.get()).as_mut_ptr()) };
    }
}

struct WaitRegistration { queue: *mut Waitq, entry: *mut WaitqEntry }
impl Drop for WaitRegistration {
    fn drop(&mut self) {
        // The pinned stack entry remains valid until the original wait primitive
        // has restored PS_RUNNING and removed it from this exact queue.
        unsafe { waitq_finish_wait(self.queue, self.entry) };
    }
}

impl ForwardGate {
    /// # Safety
    /// `output` is fresh, writable, aligned, final-address owner-record storage;
    /// it cannot move after this function initializes the actual queue list.
    pub(super) unsafe fn initialize_at(output: *mut Self) {
        unsafe {
            write(output, Self { busy: AtomicBool::new(false),
                closing: AtomicBool::new(false),
                queue: UnsafeCell::new(MaybeUninit::uninit()) });
            waitq_init((*(*output).queue.get()).as_mut_ptr());
        }
    }

    /// Called while genuine P/R removal excludes a later managed lookup.
    pub(super) fn mark_closing(&self) {
        self.closing.store(true, Ordering::Release);
    }

    fn try_take(&self, close: bool) -> Result<bool, CInt> {
        if !close && self.closing.load(Ordering::Acquire) { return Err(-EBADF); }
        if self.busy.compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed).is_err() {
            return Ok(false);
        }
        // A close may have won after the initial check but before this CAS.
        // Reject BEFORE any remote numeric-FD call, then let close acquire G.
        if !close && self.closing.load(Ordering::Acquire) {
            self.busy.store(false, Ordering::Release);
            unsafe { waitq_wakeup((*self.queue.get()).as_mut_ptr()) };
            return Err(-EBADF);
        }
        Ok(true)
    }

    /// # Safety
    /// Caller is an actual live process-context Thread, may schedule, holds the
    /// owning descriptor pin, and holds NO P/R/S/IRQ/runqueue exclusion. Never
    /// call this gate from VM-close-under-P, scheduler, IRQ or exit accounting.
    unsafe fn acquire(&self, close: bool) -> Result<ForwardGuard<'_>, CInt> {
        match self.try_take(close) {
            Ok(true) => return Ok(ForwardGuard { gate: self, not_send: PhantomData }),
            Err(error) => return Err(error),
            Ok(false) => {},
        }
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        if cpu.is_null() { return Err(-EINVAL); }
        let current = unsafe { addr_of!((*cpu).current).read() };
        if current.is_null() { return Err(-EINVAL); }
        let mut entry = core::pin::pin!(MaybeUninit::<WaitqEntry>::uninit());
        let entry_ptr = unsafe { entry.as_mut().get_unchecked_mut() }.as_mut_ptr();
        let queue = unsafe { (*self.queue.get()).as_mut_ptr() };
        unsafe { waitq_init_entry(entry_ptr, current.cast::<c_void>()) };
        let registered = WaitRegistration { queue, entry: entry_ptr };
        loop {
            // Registration and status publication precede the condition check.
            // Thus an owner releasing G cannot lose this waiter's wakeup.
            unsafe { waitq_prepare_to_wait(queue, entry_ptr, PS_UNINTERRUPTIBLE) };
            match self.try_take(close) {
                Ok(true) => {
                    drop(registered);
                    return Ok(ForwardGuard { gate: self, not_send: PhantomData });
                },
                Err(error) => return Err(error),
                Ok(false) => unsafe { schedule() },
            }
        }
    }

    /// # Safety
    /// Same actual process-context/pin/no-lock obligations as acquire().
    pub(super) unsafe fn forward(&self) -> Result<ForwardGuard<'_>, CInt> {
        unsafe { self.acquire(false) }
    }

    /// # Safety
    /// The actual descriptor was removed/marked Closing once under P/R and P/R
    /// have been released. Caller owns that one close token and its descriptor
    /// pin. It invokes the genuine host close exactly once while this guard is
    /// held, propagates its actual signed result, then consumes the close token.
    pub(super) unsafe fn close(&self) -> Result<ForwardGuard<'_>, CInt> {
        if !self.closing.load(Ordering::Acquire) { return Err(-EINVAL); }
        unsafe { self.acquire(true) }
    }
}
