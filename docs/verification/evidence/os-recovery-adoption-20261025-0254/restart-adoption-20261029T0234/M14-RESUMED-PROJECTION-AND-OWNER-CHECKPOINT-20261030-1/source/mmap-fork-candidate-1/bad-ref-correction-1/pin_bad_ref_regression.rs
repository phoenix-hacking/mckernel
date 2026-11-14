// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Unexecuted regression source for exact proposed counter helper.
const EINVAL:i32=22;
mod actual { type CInt=i32; include!("pin-counter.PRIVATE.rs.inc");
    pub fn pin(c:&core::sync::atomic::AtomicI32)->Result<(),i32>{pin_live_counter(c)} }
#[test] fn bad_refs_never_change_the_counter(){
    use core::sync::atomic::{AtomicI32,Ordering};
    for value in [0,-1,i32::MIN,i32::MAX]{
        let counter=AtomicI32::new(value);
        assert_eq!(actual::pin(&counter),Err(if value==i32::MAX{-75}else{-EINVAL}));
        assert_eq!(counter.load(Ordering::SeqCst),value);
    }
}
#[test] fn good_ref_acquires_exactly_one_pin(){
    use core::sync::atomic::{AtomicI32,Ordering};
    for value in [1,2,255,i32::MAX-1]{
        let counter=AtomicI32::new(value);
        assert_eq!(actual::pin(&counter),Ok(()));
        assert_eq!(counter.load(Ordering::SeqCst),value+1);
    }
}
