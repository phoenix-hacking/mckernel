
#[cfg(test)]
pub(crate) mod offload_tests {
    use super::*;
    use crate::abi::{CpuLocalVar, Process, ProcessVm, SyscallRequest, SyscallResponse, Thread};
    use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
    static EXPECTED_REQUEST: AtomicUsize = AtomicUsize::new(0);
    static EXPECTED_ARGS: std::sync::Mutex<[u64; 6]> = std::sync::Mutex::new([0; 6]);
    static TRANSPORT_RESULT: AtomicI64 = AtomicI64::new(-5);
    static RECEIPT: AtomicUsize = AtomicUsize::new(0);
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
            (*parent).refcount.counter = 1; (*parent).tid = 19; (*parent).cpu_id = 0;
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


    pub(crate) unsafe fn transport(request: *mut SyscallRequest, cpu: i32) -> i64 {
        assert_eq!(request as usize, EXPECTED_REQUEST.load(Ordering::SeqCst));
        assert_eq!((*request).args, *EXPECTED_ARGS.lock().unwrap());
        assert_eq!(cpu, 0);
        let actual = TRANSPORT_RESULT.load(Ordering::SeqCst);
        if RECEIPT.load(Ordering::SeqCst) == 0 { return actual; }
        let thread = (*crate::cls::get_this_cpu_local_var()).current;
        (*request).rtid = (*thread).tid; (*request).ttid = 0; (*request).valid = 0;
        let mut handles = [Handle::EMPTY; registry::CAPACITY];
        registry::snapshot_handles(&mut handles);
        let handle = handles.into_iter().find(|h| {
            if h.epoch == 0 { return false; }
            registry::visit(*h, |p| i32::from(p.as_ref().request == request as usize)) == 1
        }).expect("actual escaped request is discoverable");
        assert_eq!(registry::visit(handle, |mut pointer| {
            let c = pointer.as_mut(); let frame = &mut c.bytes;
            frame.fill(0); frame[..8].copy_from_slice(b"MCFKW001");
            frame[8..12].copy_from_slice(&[1, 0, 40, 0]);
            frame[12..16].copy_from_slice(&128u32.to_le_bytes());
            frame[16..20].copy_from_slice(&1u32.to_le_bytes());
            super::super::put(frame, 24, 1); super::super::put(frame, 32, actual as u64);
            frame[40..44].copy_from_slice(&3u32.to_le_bytes());
            frame[44..48].copy_from_slice(&(actual as i32).to_le_bytes());
            for (at, value) in [(48, 7), (56, c.parent as u64), (64, 8), (72, 9),
                (80, c.child as u64), (88, 0x9000), (96, c.root), (104, c.start),
                (112, c.length), (120, c.nonce)] { super::super::put(frame, at, value); }
            0
        }), 0);
        let mut response: SyscallResponse = core::mem::zeroed();
        response.ret = actual; response.stid = 17; response.status = 1;
        // The unchanged production observer, its Acquire helper and first-receipt
        // parser consume this adapter response; no direct phase/identity injection.
        super::super::observe_fork_control_reply(request, &mut response, cpu, thread);
        actual
    }

    unsafe fn setup<'a>(objects: &Objects, request: &'a mut SyscallRequest, actual: i64,
        receipt: bool) -> EscapedFork<'a> {
        EXPECTED_REQUEST.store(request as *mut _ as usize, Ordering::SeqCst);
        TRANSPORT_RESULT.store(actual, Ordering::SeqCst);
        RECEIPT.store(usize::from(receipt), Ordering::SeqCst);
        let owner = PrivateFork::create(request, objects.acquire()).ok().expect("private owner");
        *EXPECTED_ARGS.lock().unwrap() = owner.request.as_ref().args;
        owner.begin().ok().expect("actual begin")
    }
    unsafe fn assert_retained(objects: &Objects, owner: RetainedFork, frees: usize) {
        assert!(!owner.caller_cleanup_allowed());
        assert!(matches!(registry::cancel(owner.handle()), Err(EBUSY)));
        assert_eq!(registry::visit(owner.handle(), |pointer| {
            let credits = pointer.as_ref().owned_credits.as_ref().expect("durable credits");
            assert_eq!(credits.parent.as_ptr(), objects.parent);
            assert_eq!(credits.child.as_ptr(), objects.child);
            assert_eq!(credits.process.as_ptr(), objects.process);
            assert_eq!(credits.vm.as_ptr(), objects.vm); assert_eq!(credits.reserved_cpu, 1);
            0
        }), 0);
        drop(owner);
        assert_eq!(objects.counts(), [2, 2, 2, 2]);
        assert_eq!(crate::mem_helpers::frees(), frees);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst), 0);
    }
    #[test]
    fn owned_offload_negative_retains_same_request_and_all_credits() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, -5, false);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, Some(-5)); assert_eq!(owner.error, -5);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("negative result cannot be successful observation"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_actual_observer_positive_still_retains() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, 123, true);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::ReceiptObserved { child_pid, owner } => {
                assert_eq!(child_pid, 123); assert_eq!(owner.error, 0);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("actual observer receipt should be reported"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_positive_without_receipt_is_uncertain() { unsafe {
        let objects = Objects::new(); let mut request = request();
        let escaped = setup(&objects, &mut request, 123, false);
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, Some(123)); assert_eq!(owner.error, super::super::EPROTO);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("scalar result cannot invent a receipt"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls + 1);
    } }
    #[test]
    fn owned_offload_postbegin_refusal_retains_but_prebegin_cancel_returns() { unsafe {
        let objects = Objects::new(); let mut request1 = request();
        let owner = PrivateFork::create(&mut request1, objects.acquire()).ok().unwrap();
        let returned = owner.cancel().ok().expect("actual private cancellation");
        assert_eq!(returned.child.as_ptr(), objects.child);
        assert_eq!(returned.process.as_ptr(), objects.process);
        assert_eq!(returned.vm.as_ptr(), objects.vm); assert_eq!(returned.reserved_cpu, 1);
        assert_eq!(objects.counts(), [1, 2, 2, 2]);
        let mut request2 = request();
        let mut escaped = setup(&objects, &mut request2, 123, false);
        escaped.request.as_mut().args[4] ^= 8;
        let calls = crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        let frees = crate::mem_helpers::frees();
        match escaped.offload() {
            OwnedOffloadReturn::Uncertain { actual, owner } => {
                assert_eq!(actual, None); assert_eq!(owner.error, EACCES);
                assert_retained(&objects, owner, frees);
            }, _ => panic!("changed request refused before actual transport"),
        }
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst), calls);
    } }
}
