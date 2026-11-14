
#[cfg(test)]
pub(crate) mod caller_tests {
    use super::*;
    use crate::abi::{CpuLocalVar, Process, ProcessVm, SyscallRequest, SyscallResponse, Thread};
    use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
    static TRANSPORT_RESULT:AtomicI64=AtomicI64::new(-5);
    static RECEIPT:AtomicUsize=AtomicUsize::new(0);
    unsafe extern "C" {
        fn invoke_actual_owned_caller_branch(parent:*mut Thread,child:*mut Thread,cpu:i32)->i64;
        fn reset_caller_probe();
        fn caller_probe_counts(index:u32)->u64;
    }
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
            assert_eq!(crate::process_helpers::process_thread_alloc_init_body_result(
                child.cast(), core::mem::size_of::<Thread>() as u64,
                core::mem::offset_of!(Thread, refcount) as u64,
                core::mem::offset_of!(Thread, hash_list) as u64,
                core::mem::offset_of!(Thread, siblings_list) as u64, None), 0);
            assert_eq!((*child).cpu_id, 0);
            (*child).proc = process; (*child).vm = vm;
            (*process).parent = parent_proc; (*process).main_thread = child;
            (*process).vm = vm; (*process).refcount.counter = 2;
            (*vm).proc = process.cast(); (*vm).refcount.counter = 2;
            let address_space = Box::into_raw(Box::new(core::mem::zeroed::<crate::abi::AddressSpace>()));
            (*address_space).page_table = 0x4000usize as *mut core::ffi::c_void;
            (*vm).address_space = address_space;
            (*vm).region.user_start = 0x1000; (*vm).region.user_end = 0x3000;
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


    unsafe fn find_handle_for_request(request:*mut SyscallRequest)->Handle {
        let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
        handles.into_iter().find(|handle| handle.epoch!=0 && registry::visit(*handle,|p|
            i32::from(p.as_ref().request==request as usize))==1).expect("same request in durable registry")
    }
    pub(crate) unsafe fn transport(request: *mut SyscallRequest, cpu: i32) -> i64 {
        assert_eq!((&(*request).args)[..4], [0, 0x1000, 0x2000, 0x4000]);
        let handle = find_handle_for_request(request);
        assert_eq!(registry::visit(handle, |pointer| {
            let c = pointer.as_ref();
            assert_eq!(c.owned_request.as_ref().unwrap().request.as_ptr(), request);
            let credits = c.owned_credits.as_ref().unwrap();
            assert_eq!(credits.reserved_cpu, 1); assert_eq!(credits.private_child_cpu, 0);
            0
        }), 0);
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


    unsafe fn execute(objects:&Objects,actual:i64,receipt:bool)->i64 {
        reset_caller_probe(); TRANSPORT_RESULT.store(actual,Ordering::SeqCst);
        RECEIPT.store(usize::from(receipt),Ordering::SeqCst);
        invoke_actual_owned_caller_branch(objects.parent,objects.child,1)
    }
    unsafe fn assert_c_flow(destroy:u64) {
        assert_eq!(caller_probe_counts(0),destroy,"destroy_thread branch");
        assert_eq!(caller_probe_counts(1),destroy,"old refcount reset branch");
        assert_eq!(caller_probe_counts(2),destroy,"release_cpuid branch");
        assert_eq!(caller_probe_counts(3),0,"positive chain/runq continuation forbidden");
    }
    unsafe fn assert_retained(objects:&Objects) {
        let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
        let handle=handles.into_iter().find(|h|h.epoch!=0 && registry::visit(*h,|p|
            i32::from(p.as_ref().child==objects.child as usize && p.as_ref().owned_credits.is_some()))==1)
            .expect("actual caller owns durable carrier");
        assert_eq!(registry::visit(handle,|p|{
            let c=p.as_ref();let credits=c.owned_credits.as_ref().unwrap();
            assert_eq!(credits.child.as_ptr(),objects.child);assert_eq!(credits.vm.as_ptr(),objects.vm);
            assert_eq!(credits.reserved_cpu,1);assert_eq!(credits.private_child_cpu,0);
            let request=c.owned_request.as_ref().unwrap().request;
            assert_eq!(request.as_ptr()as usize,c.request);assert_eq!(request.as_ref().args[..4],[0,0x1000,0x2000,0x4000]);
            0
        }),0);
        assert!(matches!(registry::cancel(handle),Err(EBUSY)));
        assert_eq!(objects.counts(),[2,2,2,2]);assert_eq!((*objects.child).cpu_id,0);
        assert_eq!(crate::DESTRUCTORS.load(Ordering::SeqCst),0);
    }
    #[test]
    fn caller_reserved_cpu_differs_from_unpublished_cpu_negative_retains() {unsafe{
        let objects=Objects::new();let frees=crate::mem_helpers::frees();
        assert_eq!(execute(&objects,-5,false),-5);assert_c_flow(0);assert_retained(&objects);
        assert_eq!(crate::mem_helpers::frees(),frees);
    }}
    #[test]
    fn caller_positive_observer_still_bypasses_cleanup_and_publication() {unsafe{
        let objects=Objects::new();assert_eq!(execute(&objects,123,true),i64::from(EBUSY));
        assert_c_flow(0);assert_retained(&objects);
    }}
    #[test]
    fn caller_positive_scalar_without_receipt_stays_retained() {unsafe{
        let objects=Objects::new();assert_eq!(execute(&objects,123,false),i64::from(super::super::EPROTO));
        assert_c_flow(0);assert_retained(&objects);
    }}
    #[test]
    fn caller_request_allocation_failure_keeps_c_cleanup() {unsafe{
        let objects=Objects::new();let calls=crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        crate::mem_helpers::fail_next(core::mem::size_of::<SyscallRequest>());
        assert_eq!(execute(&objects,-5,false),i64::from(super::super::ENOMEM));assert_c_flow(1);
        assert_eq!(objects.counts(),[1,2,2,2]);assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst),calls);
    }}
    #[test]
    fn caller_carrier_allocation_failure_frees_request_before_c_cleanup() {unsafe{
        let objects=Objects::new();let frees=crate::mem_helpers::frees();
        let slots=crate::mem_helpers::live_request_slots();
        crate::mem_helpers::fail_next(core::mem::size_of::<super::super::Carrier>());
        assert_eq!(execute(&objects,-5,false),i64::from(super::super::ENOMEM));assert_c_flow(1);
        assert_eq!(objects.counts(),[1,2,2,2]);assert_eq!(crate::mem_helpers::frees(),frees+1);
        assert_eq!(crate::mem_helpers::live_request_slots(),slots);
    }}
    #[test]
    fn caller_pretransfer_child_state_refusal_frees_private_allocations() {unsafe{
        let objects=Objects::new();(*objects.child).cpu_id=7;
        let frees=crate::mem_helpers::frees();let slots=crate::mem_helpers::live_request_slots();
        let calls=crate::OFFLOAD_CALLS.load(Ordering::SeqCst);
        assert_eq!(execute(&objects,-5,false),i64::from(EACCES));assert_c_flow(1);
        assert_eq!(objects.counts(),[1,2,2,2]);assert_eq!(crate::mem_helpers::frees(),frees+2);
        assert_eq!(crate::mem_helpers::live_request_slots(),slots);
        assert_eq!(crate::OFFLOAD_CALLS.load(Ordering::SeqCst),calls);
    }}
}
