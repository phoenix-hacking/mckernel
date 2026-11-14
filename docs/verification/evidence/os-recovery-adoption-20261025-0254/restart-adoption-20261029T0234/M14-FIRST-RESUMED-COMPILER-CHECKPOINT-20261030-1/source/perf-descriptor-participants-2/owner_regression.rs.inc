// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// UNRUN. Include inside candidate owner module with genuine ABI/rbtree and a
// controlled allocator/lock harness. All fixture cases must run serially.
#[cfg(test)] mod review_regression {
    use super::*;
    use core::{mem::MaybeUninit,ptr::{addr_of_mut,null_mut}};
    #[test] fn unaligned_registration_never_writes_and_returns_exact_raw() {unsafe {
        let bytes=std::boxed::Box::leak(std::boxed::Box::new([0xacu8;256]));
        let align=core::mem::align_of::<Registration>(); assert!(align>1);
        let base=bytes.as_mut_ptr();let off=if (base as usize)%align==0 {1} else {0};
        let raw=base.add(off).cast::<c_void>();let before=*bytes;
        match initialize_registration_allocation(raw) {
            Err(RegistrationAllocationError::Misaligned {raw:p})=>assert_eq!(p,raw),_=>panic!("expected exact raw allocation")
        }
        assert_eq!(*bytes,before);
    }}
    #[test] fn overflow_does_not_unlink_descriptor_or_report_absence() {unsafe {
        use super::super::perf_descriptor_participants as part;
        let mut nodes=std::vec::Vec::new();
        for i in 0..(2*usize::BITS as usize+1) {
            nodes.push(std::boxed::Box::new(Registration {node:crate::rbtree::RbNode {__rb_parent_color:0,rb_left:null_mut(),rb_right:null_mut()},
                descriptor:(i+1) as *mut Mckfd,event:null_mut(),group:null_mut(),generation:1,active:true}));
        }
        for i in 0..nodes.len()-1 {let next=addr_of_mut!(nodes[i+1].node);nodes[i].node.rb_right=next;}
        let pm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Process>::uninit()));let proc=pm.as_mut_ptr();
        addr_of_mut!((*proc).mckfd_lock).write(IhkSpinlock {head_tail:0});
        let dm=std::boxed::Box::leak(std::boxed::Box::new(MaybeUninit::<Mckfd>::zeroed()));let d=dm.as_mut_ptr();(*d).fd=17;
        addr_of_mut!((*proc).mckfd).write(d.cast());
        let registry=core::ptr::addr_of_mut!(PERF_REGISTRY);let previous=(*registry).root.rb_node;
        assert!(previous.is_null()); (*registry).root.rb_node=addr_of_mut!(nodes[0].node);
        let result=part::detach_for_close(proc,17,part::reserve_record().unwrap());
        (*registry).root.rb_node=previous;
        assert_eq!(result,Err(-EOVERFLOW));assert_eq!((*proc).mckfd,d.cast());
    }}
}
