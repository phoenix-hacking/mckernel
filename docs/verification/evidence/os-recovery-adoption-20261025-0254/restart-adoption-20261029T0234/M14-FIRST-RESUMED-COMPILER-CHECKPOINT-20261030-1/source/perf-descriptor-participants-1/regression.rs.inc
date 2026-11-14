// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNRUN actual-body source. A future approved harness must include
// candidate-3 owner/core + real ABI/rbtree and controlled allocator/lock bridges.
// Callback symbols are the actual selected Rust providers and are not invoked.
#[cfg(test)] mod regression {
    use super::*;
    use core::{mem::MaybeUninit,ptr::{addr_of_mut,null_mut}};
    unsafe fn fresh_event(p:*mut FullMcPerfEvent,counter:CInt) {
        core::ptr::write_bytes(p.cast::<u8>(),0,size_of::<FullMcPerfEvent>());
        let h=addr_of_mut!((*p).sibling_list);(*h).next=h;(*h).prev=h;
        let x=addr_of_mut!((*p).group_entry);(*x).next=x;(*x).prev=x;(*p).counter_id=counter;
    }
    unsafe fn process(p:*mut Process) {addr_of_mut!((*p).mckfd_lock).write(IhkSpinlock {head_tail:0});addr_of_mut!((*p).mckfd).write(null_mut());}
    unsafe fn desc(p:*mut Mckfd,fd:CInt,event:*mut FullMcPerfEvent) {
        core::ptr::write_bytes(p.cast::<u8>(),0,size_of::<Mckfd>());let c=callbacks();
        (*p).fd=fd;(*p).padding=-1;(*p).data=event as usize as CLong;(*p).read_cb=c.read;
        (*p).ioctl_cb=c.ioctl;(*p).mmap_cb=c.mmap;(*p).close_cb=c.close;(*p).fcntl_cb=c.fcntl;
    }
    #[test] fn member_fd_leader_first_and_retained_close() {unsafe {
        let pm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Process>::uninit()));let p=pm.as_mut_ptr();process(p);
        let lm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<FullMcPerfEvent>::uninit()));let l=lm.as_mut_ptr();fresh_event(l,1);
        let mm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<FullMcPerfEvent>::uninit()));let m=mm.as_mut_ptr();fresh_event(m,2);
        let ld=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::uninit()));let ld=ld.as_mut_ptr();desc(ld,10,l);
        let md=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::uninit()));let md=md.as_mut_ptr();desc(md,11,m);
        let lr=match owner::allocate_registration(){Ok(x)=>x,_=>panic!()};
        let mr=match owner::allocate_registration(){Ok(x)=>x,_=>panic!()};
        let prep=match prepare_standalone(l,reserve_record().unwrap()){Ok(x)=>x,_=>panic!()};
        assert_eq!(commit_standalone_and_publish(p,ld,lr,prep),Ok(10));
        let group=acquire_open_group(p,10).unwrap();assert!(!group_fd_is_member(&group));
        let mo=allocate_sidecar::<owner::EventOwner>().unwrap();assert!(owner::init_event(mo,m).is_ok());
        assert_eq!(publish_member_reserved(p,&group,mo,md,mr,reserve_record().unwrap()),Ok(11));
        let member=acquire_open_group(p,11).unwrap();assert!(group_fd_is_member(&member));
        let retained_before=RETAIN_HEAD;
        let spare=allocate_sidecar::<owner::EventOwner>().unwrap();
        let spare_m=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<FullMcPerfEvent>::uninit()));let spare_event=spare_m.as_mut_ptr();fresh_event(spare_event,3);
        assert!(owner::init_event(spare,spare_event).is_ok());
        let spare_d=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::uninit()));let spare_d=spare_d.as_mut_ptr();desc(spare_d,12,spare_event);
        let spare_reg=owner::allocate_registration().unwrap();
        assert_eq!(publish_member_reserved(p,&member,spare,spare_d,spare_reg,reserve_record().unwrap()),Err(-EINVAL));
        assert_ne!(RETAIN_HEAD,retained_before);
        match &(*RETAIN_HEAD).payload {Payload::MemberRejected {member,..}=>assert_eq!(*member,spare),_=>panic!()}
        release_open_group(member);
        assert_eq!(detach_for_close(p,10,reserve_record().unwrap()),Ok(true));
        assert_eq!((*m).group_leader,l);assert_eq!((*l).nr_siblings,1);
        release_open_group(group);
        assert_eq!(detach_for_close(p,11,reserve_record().unwrap()),Ok(true));
        match &(*RETAIN_HEAD).payload {Payload::Close {descriptor,outcome:owner::DetachOutcome::Final {batch,..}}=>{
            assert_eq!(*descriptor,md);assert_eq!(batch.event_count,2);assert!(!batch.group.is_null());},_=>panic!()}
    }}
    #[test] fn clone_failure_owns_unwind_and_source_can_close() {unsafe {
        let pm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Process>::uninit()));let p=pm.as_mut_ptr();process(p);
        let cm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Process>::uninit()));let child=cm.as_mut_ptr();process(child);
        let em=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<FullMcPerfEvent>::uninit()));let e=em.as_mut_ptr();fresh_event(e,1);
        let sm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::uninit()));let src=sm.as_mut_ptr();desc(src,20,e);
        let dm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::uninit()));let dst=dm.as_mut_ptr();
        let reg=owner::allocate_registration().unwrap();
        let prep=match prepare_standalone(e,reserve_record().unwrap()){Ok(x)=>x,_=>panic!()};
        assert_eq!(commit_standalone_and_publish(p,src,reg,prep),Ok(20));
        let child_reg=owner::allocate_registration().unwrap();
        // Deliberately substitute a callback to force registration failure after
        // the generation-validated clone increment; this is fixture corruption,
        // not an assertion that a real race has been observed.
        (*src).read_cb=99usize as *mut c_void;
        assert_eq!(clone_registered(p,child,src,dst,child_reg,reserve_record().unwrap()),Err(-EINVAL));
        match &(*RETAIN_HEAD).payload {Payload::CloneAbort {descriptor,registration,..}=>{
            assert_eq!(*descriptor,dst);assert_eq!(*registration,child_reg)},_=>panic!()}
        assert!((*child).mckfd.is_null());
        assert_eq!(detach_for_close(p,20,reserve_record().unwrap()),Ok(true));
    }}
}
