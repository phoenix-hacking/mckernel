// Changed-family observations through actual candidate bodies. Platform/host
// adapters remain exactly those of the accepted fixture, not native authority.
#[test]fn panic_free_actual_runtime_publication_and_final_ack_release_once(){unsafe{
 let baseline=mem_helpers::live();let(out,parent,child)=run(20);
 assert_eq!((out.disposition,out.error),(3,900));
 exit_before_switch(child);actual_reap(parent,child);
 assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
 exit_after_switch(child);
 assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),1);
 assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(4,1,1,1,1,0));
 assert_eq!((*parent).refcount.counter,1);assert_eq!(mem_helpers::live(),baseline);
 assert!(fork_control_registry::visit(out.handle,|_|0)<0);
 assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
 assert_eq!(CALLS.load(Ordering::SeqCst),4);
}}
#[test]fn panic_free_missing_actual_start_receipt_retains_graph_without_publication(){unsafe{
 let(out,parent,child)=run(2);assert_eq!(out.disposition,1);assert_eq!(out.error,-5);
 assert_eq!(QUEUED.load(Ordering::SeqCst),0);assert_eq!(CALLS.load(Ordering::SeqCst),2);
 assert_eq!((*child).refcount.counter,2);assert_eq!((*(*child).vm).refcount.counter,1);
 assert_eq!((*parent).refcount.counter,2);assert_eq!(CPU.load(Ordering::SeqCst),0);
 assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
}}
#[test]fn panic_free_refused_ack_preserves_parent_and_requests_without_retry(){unsafe{
 let baseline=mem_helpers::live();let(out,parent,child)=run(23);
 exit_before_switch(child);actual_reap(parent,child);exit_after_switch(child);
 assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
 assert_eq!((CALLS.load(Ordering::SeqCst),THREAD.load(Ordering::SeqCst),VM.load(Ordering::SeqCst),PROCESS.load(Ordering::SeqCst),PAGES.load(Ordering::SeqCst),CPU.load(Ordering::SeqCst)),(4,1,1,1,1,0));
 // Child is already dead. Only the retained parent/registry/request ownership
 // may be inspected, never the former child or its VM/Process storage.
 assert_eq!((*parent).refcount.counter,2);assert!(mem_helpers::live()>baseline);
 assert_eq!(fork_control_registry::visit(out.handle,|_|0),0);
 assert_eq!(fork_control_guest::runnable::process_fork_runtime_drain_current_v1(),0);
 assert_eq!(CALLS.load(Ordering::SeqCst),4);
}}
#[test]fn panic_free_zz_registry_full_capacity_snapshot_private_cancel_and_busy(){unsafe{
 use fork_control_registry as registry;use core::ptr::NonNull;
 // Pure registry address adapter: each boxed word supplies a distinct live
 // address, never dereferenced as a Carrier and never used as MM/ACK rights.
 let private=NonNull::new(Box::into_raw(Box::new(0usize)).cast()).unwrap();
 let handle=registry::insert(private).unwrap();
 assert_eq!(registry::cancel(handle),Ok(private));
 assert_eq!(registry::begin(handle),Err(-2));
 drop(Box::from_raw(private.as_ptr().cast::<usize>()));
 let mut retained_addresses=Vec::new();
 loop{
  let pointer=NonNull::new(Box::into_raw(Box::new(0usize)).cast()).unwrap();
  match registry::insert(pointer){
   Ok(h)=>{
    assert_eq!(registry::begin(h),Ok(pointer));
    assert_eq!(registry::visit(h,|seen|{
     assert_eq!(seen,pointer);assert_eq!(registry::visit(h,|_|99),-16);7
    }),7);
    retained_addresses.push(pointer);
   },
   Err((code,pointer))=>{assert_eq!(code,-28);drop(Box::from_raw(pointer.as_ptr().cast::<usize>()));break;}
  }
 }
 let mut out=[registry::Handle::EMPTY;registry::CAPACITY];
 assert_eq!(registry::snapshot_handles(&mut out),registry::CAPACITY);
 assert!(out.iter().all(|h|h.epoch!=0));
 let mut slots=out.iter().map(|h|h.slot).collect::<Vec<_>>();slots.sort();slots.dedup();
 assert_eq!(slots.len(),registry::CAPACITY);
 // Registry still names these addresses until this isolated fixture exits.
 core::mem::forget(retained_addresses);
}}
