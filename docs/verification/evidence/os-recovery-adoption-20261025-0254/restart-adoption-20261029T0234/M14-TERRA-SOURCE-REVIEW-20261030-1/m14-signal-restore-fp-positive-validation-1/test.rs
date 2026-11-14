// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod abi { pub type CInt=i32; pub type CLong=i64; pub type CULong=u64; pub type SizeT=usize; }
#[path="f06_native_signal_restore_fp.rs"] mod candidate;
use core::ffi::c_void;
use std::sync::Mutex;
#[derive(Debug, Clone, PartialEq)]
enum Call { Configured, Bytes(i32,i32), Reset, Alloc(usize), Copy(usize,usize,usize), Mask, Mxcsr, Validate(usize,usize,i32,u64,u32), Restore(usize,u64), Free(usize) }
struct State { calls: Vec<Call>, bytes: i64, alloc: usize, copy: i32, validate: i64, restore: i64 }
static STATE: Mutex<State> = Mutex::new(State { calls: Vec::new(), bytes: 80, alloc: 0, copy: 0, validate: 0, restore: 0 });
static mut STORAGE: [u8; 256] = [0; 256];
const MASK:u64=0x1122334455667788;
unsafe extern "C" fn configured()->i32 { STATE.lock().unwrap().calls.push(Call::Configured); 512 }
unsafe extern "C" fn bytes(s:i32,c:i32)->i64 { let mut x=STATE.lock().unwrap(); x.calls.push(Call::Bytes(s,c)); x.bytes }
unsafe extern "C" fn reset()->i64 { STATE.lock().unwrap().calls.push(Call::Reset); -44 }
unsafe extern "C" fn alloc(n:usize)->*mut c_void { let mut x=STATE.lock().unwrap(); x.calls.push(Call::Alloc(n)); x.alloc as *mut c_void }
unsafe extern "C" fn copy(d:*mut c_void,s:*const c_void,n:usize)->i32 { let mut x=STATE.lock().unwrap(); x.calls.push(Call::Copy(d as usize,s as usize,n)); x.copy }
unsafe extern "C" fn mask()->u64 { STATE.lock().unwrap().calls.push(Call::Mask); MASK }
unsafe extern "C" fn mxcsr()->u32 { STATE.lock().unwrap().calls.push(Call::Mxcsr); 0xface }
unsafe extern "C" fn validate(p:*const u8,n:usize,c:i32,m:u64,x:u32)->i64 { let mut s=STATE.lock().unwrap(); s.calls.push(Call::Validate(p as usize,n,c,m,x)); s.validate }
unsafe extern "C" fn restore(p:*const u8,m:u64)->i64 { let mut s=STATE.lock().unwrap(); s.calls.push(Call::Restore(p as usize,m)); s.restore }
unsafe extern "C" fn free(p:*mut c_void) { STATE.lock().unwrap().calls.push(Call::Free(p as usize)); }
fn run(user:u64, configured_bytes:i64, alloc_result:usize, copy_result:i32, valid_result:i64, restore_result:i64)->(i64,Vec<Call>) {
    *STATE.lock().unwrap()=State { calls:Vec::new(),bytes:configured_bytes,alloc:alloc_result,copy:copy_result,validate:valid_result,restore:restore_result };
    let r=unsafe { candidate::restore_fp_body(user, 777, configured, bytes, reset, alloc, copy, mask, mxcsr, validate, restore, free) };
    let c=STATE.lock().unwrap().calls.clone(); (r,c)
}
#[test]
fn lifecycle_paths_match_original_c() {
    let base=core::ptr::addr_of_mut!(STORAGE) as usize + 1;
    let aligned=(base+63)&!63;
    assert!(aligned >= base && aligned+80 <= base+255);
    let prefix=vec![Call::Configured,Call::Bytes(777,512),Call::Alloc(143),Call::Copy(aligned,0x1234,80)];
    assert_eq!(run(0,80,base,0,0,0),(-44,vec![Call::Configured,Call::Reset]));
    assert_eq!(run(0x1234,-22,base,0,0,0),(-22,vec![Call::Configured,Call::Bytes(777,512)]));
    assert_eq!(run(0x1234,80,0,0,0,0),(-12,vec![Call::Configured,Call::Bytes(777,512),Call::Alloc(143)]));
    for error in [-14,1] { let mut calls=prefix.clone(); calls.push(Call::Free(base)); assert_eq!(run(0x1234,80,base,error,0,0),(-14,calls)); }
    let mut through_validation=prefix.clone(); through_validation.extend([Call::Mask,Call::Mxcsr,Call::Validate(aligned,80,512,MASK,0xface)]);
    let mut reject=through_validation.clone(); reject.push(Call::Free(base));
    assert_eq!(run(0x1234,80,base,0,-22,0),(-22,reject.clone()));
    // Positive nonzero validation results also skip restore and pass through.
    assert_eq!(run(0x1234,80,base,0,17,0),(17,reject));
    for result in [-5,0] { let mut calls=through_validation.clone(); calls.extend([Call::Restore(aligned,MASK),Call::Free(base)]); assert_eq!(run(0x1234,80,base,0,0,result),(result,calls)); }
    // A zero-byte validation result remains a legal callback result and still allocates.
    let mut zero=vec![Call::Configured,Call::Bytes(777,512),Call::Alloc(63),Call::Copy(aligned,0x1234,0),Call::Mask,Call::Mxcsr,Call::Validate(aligned,0,512,MASK,0xface),Call::Restore(aligned,MASK),Call::Free(base)];
    assert_eq!(run(0x1234,0,base,0,0,0),(0,zero.clone())); zero.clear();
}
