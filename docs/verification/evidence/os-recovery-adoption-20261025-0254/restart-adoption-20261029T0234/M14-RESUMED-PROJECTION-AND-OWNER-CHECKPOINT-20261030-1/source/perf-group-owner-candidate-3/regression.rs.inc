// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// UNRUN. Future harness includes the exact owner module and genuine rbtree/ABI,
// supplies controlled lock bridges and admits a reviewed execution profile.
#[cfg(test)] mod regression {
    use super::*;
    use core::{mem::MaybeUninit,ptr::{addr_of_mut,null_mut}};
    unsafe fn event(p:*mut FullMcPerfEvent) {
        core::ptr::write_bytes(p.cast::<u8>(),0,core::mem::size_of::<FullMcPerfEvent>());
        let h=addr_of_mut!((*p).sibling_list); (*h).next=h; (*h).prev=h;
        let e=addr_of_mut!((*p).group_entry); (*e).next=e; (*e).prev=e;
    }
    fn callbacks()->ExpectedCallbacks {ExpectedCallbacks {read:1usize as _,ioctl:2usize as _,mmap:3usize as _,close:4usize as _,fcntl:5usize as _}}
    fn registration()->Registration { Registration {node:crate::rbtree::RbNode {__rb_parent_color:0,rb_right:null_mut(),rb_left:null_mut()},
        descriptor:null_mut(),event:null_mut(),group:null_mut(),generation:0,active:false} }
    #[test] fn clone_after_unregister_and_quarantine_own_inputs() { unsafe {
        let mut em=MaybeUninit::<FullMcPerfEvent>::uninit(); let e=em.as_mut_ptr(); event(e);
        let mut om=MaybeUninit::<EventOwner>::uninit(); let o=om.as_mut_ptr();
        let mut gm=MaybeUninit::<GroupOwner>::uninit(); let g=gm.as_mut_ptr();
        assert!(init_event(o,e).is_ok()); let pending=match init_group(g,o) {Ok(p)=>p,_=>panic!()};
        let mut pm=MaybeUninit::<Process>::uninit(); let p=pm.as_mut_ptr();
        addr_of_mut!((*p).mckfd_lock).write(IhkSpinlock{head_tail:0});
        let mut dm=MaybeUninit::<Mckfd>::zeroed(); let d=dm.as_mut_ptr(); let cb=callbacks();
        (*d).fd=42; (*d).data=e as usize as _; (*d).read_cb=cb.read; (*d).ioctl_cb=cb.ioctl;
        (*d).mmap_cb=cb.mmap; (*d).close_cb=cb.close; (*d).fcntl_cb=cb.fcntl;
        let mut reg=registration(); let lock=addr_of_mut!((*p).mckfd_lock).cast();
        let irq=super::super::syscall_mckfd_lock_bridge(lock);
        let lease=match commit_standalone_locked(pending) {Ok(x)=>x,_=>panic!()};
        let key=match register_descriptor_locked(d,&mut reg,lease,cb) {Ok(x)=>x,_=>panic!()};
        addr_of_mut!((*p).mckfd).write(d.cast());
        let clone=match duplicate_registered_locked(d,key) {Ok(x)=>x,_=>panic!()};
        let removed=match unregister_descriptor_locked(d,key) {Ok(x)=>x,_=>panic!()};
        (*p).mckfd=null_mut();
        assert!(duplicate_registered_locked(d,key).is_err());
        super::super::syscall_mckfd_unlock_bridge(lock,irq);
        assert!(matches!(finish_detach(removed),DetachOutcome::Final {..}));
        let unpub=match abort_unpublished_lease(clone) {Ok(x)=>x,_=>panic!()};
        let batch=match finish_detach(unpub) {DetachOutcome::Final {batch,..}=>batch,_=>panic!()};
        assert_eq!(batch.event_count,1); assert_eq!(batch.events[0],o); assert_eq!(batch.group,g);
    } }
    #[test] fn prior_finalizer_survives_rejected_release_preflight() { unsafe {
        let mut em=MaybeUninit::<FullMcPerfEvent>::uninit(); let e=em.as_mut_ptr(); event(e);
        let mut om=MaybeUninit::<EventOwner>::uninit(); let o=om.as_mut_ptr();
        let mut gm=MaybeUninit::<GroupOwner>::uninit(); let g=gm.as_mut_ptr();
        assert!(init_event(o,e).is_ok()); let pending=match init_group(g,o) {Ok(p)=>p,_=>panic!()};
        let prior_event=1usize as *mut EventOwner; let mut prior=FinalBatch::empty();
        prior.events[0]=prior_event; prior.event_count=1;
        // Deliberately violate the final leader invariant to exercise custody;
        // no production race or real failure is asserted by this fixture.
        (*o).descriptors=1;
        let before_e=(*o).references.load(Ordering::Acquire); let before_g=(*g).references.load(Ordering::Acquire);
        let c=match release_edges(pending.pin.event,pending.pin.group,prior) {ReleaseOutcome::Quarantined(c)=>c,_=>panic!()};
        assert_eq!(c.batch.events[0],prior_event); assert_eq!(c.batch.event_count,1);
        assert!(c.event_edge==EdgeState::Live && c.group_edge==EdgeState::Live);
        assert_eq!((*o).references.load(Ordering::Acquire),before_e); assert_eq!((*g).references.load(Ordering::Acquire),before_g);
    } }
    #[test] fn merge_failure_returns_both_finalizer_owners() {
        let mut a=FinalBatch::empty(); let mut b=FinalBatch::empty();
        a.group=1usize as *mut GroupOwner; b.group=2usize as *mut GroupOwner;
        match a.merge(b) {Err((a,b))=>{assert_eq!(a.group as usize,1); assert_eq!(b.group as usize,2)}, _=>panic!()}
    }
}
