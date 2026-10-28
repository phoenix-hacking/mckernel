// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Pure mocked FP lifecycle; never calls usercopy, allocation or FP hardware.
extern crate core;
mod abi {pub type CInt=i32;pub type CLong=i64;pub type CULong=u64;pub type SizeT=usize;}
#[path="f06_native_signal_restore_fp.rs"] mod production;
use core::ffi::c_void;
#[repr(C)]
#[derive(PartialEq,Eq)]
struct Snapshot {storage:[u8;65536+128],events:[u64;96],count:u64}
unsafe extern "C" {
 fn fixture_configured()->i32;
 fn fixture_bytes(provided:i32,configured:i32)->i64;
 fn fixture_reset_fp()->i64;
 fn fixture_alloc(bytes:usize)->*mut c_void;
 fn fixture_copy(dest:*mut c_void,src:*const c_void,bytes:usize)->i32;
 fn fixture_mask()->u64;
 fn fixture_mxcsr()->u32;
 fn fixture_validate(buf:*const u8,bytes:usize,configured:i32,mask:u64,mxcsr:u32)->i64;
 fn fixture_restore(buf:*const u8,mask:u64)->i64;
 fn fixture_free(ptr:*mut c_void);
 fn fixture_reset(bytes:i64,alloc:i32,copy:i32,validate:i64,restore:i64,align:i32);
 fn fixture_run_c(user:u64)->i64;
 fn fixture_snapshot(out:*mut Snapshot);
}
fn snapshot()->Box<Snapshot> {
 // Allocate the large canary snapshot directly on heap; no kernel callback runs.
 let mut out=Box::<Snapshot>::new_uninit();
 unsafe {fixture_snapshot(out.as_mut_ptr());out.assume_init()}
}
#[test]
fn original_complete_ownership_flow_matches() {
 let mut cases=0;
 for user in [0,0x123456780000_u64] {for bytes in [-22,512,576,65536_i64] {for alloc in [0,1] {
 for copy in [0,1,-1] {for validate in [0,-22_i64] {for restore in [0,-14_i64] {for align in [0,1,63] {
  unsafe {fixture_reset(bytes,alloc,copy,validate,restore,align)};
  let c=unsafe {fixture_run_c(user)};let expected=snapshot();
  unsafe {fixture_reset(bytes,alloc,copy,validate,restore,align)};
  let r=unsafe {production::restore_fp_body(user,512,fixture_configured,fixture_bytes,fixture_reset_fp,
   fixture_alloc,fixture_copy,fixture_mask,fixture_mxcsr,fixture_validate,fixture_restore,fixture_free)};
  let actual=snapshot();
  assert_eq!(r,c,"return user{user}/bytes{bytes}/alloc{alloc}/copy{copy}/validate{validate}/restore{restore}/align{align}");
  assert!(actual==expected,"complete event arguments/order and buffer/canaries differ");
  // Independent lifecycle checks: configured first, reset short circuit, one
  // exact original allocation free only after successful nonnull allocation.
  assert_eq!(actual.events[0],1);
  let frees=actual.events[..actual.count as usize].windows(2)
   .filter(|pair|pair[0]==10 && pair[1]!=0).count();
  assert_eq!(frees,usize::from(user!=0 && bytes>=0 && alloc==0));
  if user==0 {assert_eq!(actual.count,3);assert_eq!(actual.events[2],3);}
  cases+=1;
 }}}}}}}
 assert_eq!(cases,576);
 println!("PASS signal-return FP C/Rust complete lifecycle576 pairs; exact original pointer/free/order/error/alignment/full-buffer-canaries");
}
