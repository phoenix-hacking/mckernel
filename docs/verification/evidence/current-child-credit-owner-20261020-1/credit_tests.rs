
#[cfg(test)]
mod credit_tests {
    use super::*;
    use crate::abi::{CpuLocalVar, Process, ProcessVm, SyscallRequest, Thread};

    struct Objects {
        parent: *mut Thread, child: *mut Thread, process: *mut Process,
        vm: *mut ProcessVm,
    }
    impl Objects {
        unsafe fn new() -> Self {
            // Each C-ABI object is a distinct real full production layout.
            // Escaped/error owners retain these allocations; the fixture never
            // frees a static arena or invents a guest reset/terminal release.
            let parent = Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
            let child = Box::into_raw(Box::new(core::mem::zeroed::<Thread>()));
            let parent_proc = Box::into_raw(Box::new(core::mem::zeroed::<Process>()));
            let parent_vm = Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
            let process = Box::into_raw(Box::new(core::mem::zeroed::<Process>()));
            let vm = Box::into_raw(Box::new(core::mem::zeroed::<ProcessVm>()));
            let local = Box::into_raw(Box::new(core::mem::zeroed::<CpuLocalVar>()));
            (*parent).proc = parent_proc; (*parent).vm = parent_vm;
            (*parent).refcount.counter = 1;
            (*parent_proc).vm = parent_vm; (*parent_proc).main_thread = parent;
            (*parent_vm).proc = parent_proc.cast();
            (*child).proc = process; (*child).vm = vm; (*child).cpu_id = 1;
            (*child).refcount.counter = 2;
            (*process).parent = parent_proc; (*process).main_thread = child;
            (*process).vm = vm; (*process).refcount.counter = 2;
            (*vm).proc = process.cast(); (*vm).refcount.counter = 2;
            (*local).current = parent; crate::cls::set(local);
            Self { parent, child, process, vm }
        }
        unsafe fn counts(&self) -> [i32; 4] {
            [(*self.parent).refcount.counter, (*self.child).refcount.counter,
             (*self.process).refcount.counter, (*self.vm).refcount.counter]
        }
        unsafe fn acquire(&self) -> ChildCredits {
            ChildCredits::acquire(self.parent, self.child, 1).ok().expect("authentic current private child")
        }
    }
    fn request() -> SyscallRequest {
        let mut request: SyscallRequest = unsafe { core::mem::zeroed() };
        request.number = 56;
        request.args = [0, 0x1000, 0x2000, 0x4000, 0xa000, 0xb000];
        request
    }

    #[test]
    fn child_credit_begin_and_uncertainty_retain_all() { unsafe {
        let objects = Objects::new();
        let credits = objects.acquire();
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        let mut request = request();
        let owner = PrivateFork::create(&mut request, credits).ok().expect("private carrier");
        let escaped = owner.begin().ok().expect("actual registry begin");
        let handle = escaped.handle();
        assert_eq!(registry::visit(handle, |pointer| {
            let credits = pointer.as_ref().owned_credits.as_ref().expect("same durable credit owner");
            assert_eq!(credits.parent.as_ptr(), objects.parent);
            assert_eq!(credits.child.as_ptr(), objects.child);
            assert_eq!(credits.process.as_ptr(), objects.process);
            assert_eq!(credits.vm.as_ptr(), objects.vm);
            assert_eq!(credits.reserved_cpu, 1);
            0
        }), 0);
        assert_eq!(super::super::process_fork_guest_carrier_cancel_current_v1(handle), EBUSY);
        let frees = crate::mem_helpers::frees();
        let retained = escaped.retain_after_return(-5);
        assert_eq!(retained.handle(), handle);
        assert_eq!(retained.error, -5);
        assert!(!retained.caller_cleanup_allowed());
        assert!(matches!(registry::cancel(handle), Err(EBUSY)));
        assert_eq!(crate::mem_helpers::frees(), frees);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        drop(retained);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), 0);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst), 0);
    } }

    #[test]
    fn child_credit_cancel_restores_and_returns_once() { unsafe {
        let objects = Objects::new();
        let mut request = request(); let original = request.args;
        let credits = objects.acquire();
        let owner = PrivateFork::create(&mut request, credits).ok().expect("private carrier");
        let handle = owner.handle;
        assert_eq!(owner.request.as_ref().args[5], super::super::MARKER);
        let frees = crate::mem_helpers::frees();
        let returned = owner.cancel().ok().expect("prebegin cancellation");
        assert_eq!(returned.child.as_ptr(), objects.child);
        assert_eq!(returned.process.as_ptr(), objects.process);
        assert_eq!(returned.vm.as_ptr(), objects.vm);
        assert_eq!(returned.reserved_cpu, 1);
        assert_eq!(request.args, original);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        assert_eq!(crate::mem_helpers::frees(), frees + 1);
        assert!(matches!(registry::cancel(handle), Err(-2)));
        drop(returned);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst), 0);
    } }

    #[test]
    fn child_credit_refusals_and_legacy_path_preserved() { unsafe {
        let objects = Objects::new();
        assert!(matches!(ChildCredits::acquire(objects.parent, objects.child, 2), Err(EACCES)));
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        (*objects.parent).refcount.counter = 0;
        assert!(matches!(ChildCredits::acquire(objects.parent, objects.child, 1), Err(EBUSY)));
        (*objects.parent).refcount.counter = i32::MAX;
        assert!(matches!(ChildCredits::acquire(objects.parent, objects.child, 1), Err(EOVERFLOW)));
        assert_eq!(objects.counts(), [i32::MAX, 2, 2, 2]);
        (*objects.parent).refcount.counter = 1;
        let credits = objects.acquire();
        let mut bad = request(); bad.number = 57; let original = bad.args;
        let failure = PrivateFork::create(&mut bad, credits).err().expect("wrong number refused");
        assert_eq!(failure.error, EINVAL); assert_eq!(bad.args, original);
        let returned = failure.credits.cancel_unpublished().ok().expect("unchanged precreate credits");
        assert_eq!(returned.child.as_ptr(), objects.child);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        let mut legacy = request(); let mut handle = Handle::EMPTY;
        assert_eq!(super::super::process_fork_guest_carrier_create_current_v1(
            &mut legacy, objects.parent, objects.child, &mut handle), 0);
        assert_eq!(super::super::process_fork_guest_carrier_cancel_current_v1(handle), 0);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        let mut other = request();
        let mut owner = PrivateFork::create(&mut other, objects.acquire()).ok().expect("private carrier");
        owner.request.as_mut().args[4] ^= 8;
        let changed = owner.request.as_ref().args;
        let frees = crate::mem_helpers::frees();
        let failure = owner.cancel().err().expect("wrong fullrequest refused");
        assert_eq!(failure.error, EACCES);
        assert_eq!(failure.owner.request.as_ref().args, changed);
        assert_eq!(crate::mem_helpers::frees(), frees);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        drop(failure);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), 0);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst), 0);
    } }
}
