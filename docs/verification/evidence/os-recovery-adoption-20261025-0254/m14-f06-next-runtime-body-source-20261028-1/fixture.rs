// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Standalone HOST pure oracle driver. Compile --test and link oracle.o; no guest.
#![allow(dead_code)]
extern crate core;
use core::ffi::c_void;
#[repr(C)]
pub struct ArchVdso {
    busy: i64, vdso_npages: i32,
    vvar_is_global: i8, hpet_is_global: i8, pvti_is_global: i8, padding: i8,
    vdso_physlist: [i64;2], vvar_virt:*mut c_void, vvar_phys:i64,
    hpet_virt:*mut c_void,hpet_phys:i64,pvti_virt:*mut c_void,pvti_phys:i64,vgtod_virt:*mut c_void,
}
mod abi {
    pub type CInt=i32;
    pub type CULong=u64;
    #[repr(C)]
    pub struct IkcScdPacket {pub header:u64,pub msg:i32,pub err:i32,pub reply:u64,pub body:[u8;104]}
}
#[path="f06_vdso_info.rs"]
mod f06_vdso_info;
#[derive(Debug,PartialEq,Eq)]
#[repr(C)]
struct Snapshot { state:[u8;88],events:[i64;64],event_count:u64,pauses:i32,sends:i32,preps:i32,physical_calls:i32 }
unsafe extern "C" {
    fn fixture_physical(p:*mut c_void)->u64;
    fn fixture_prepare(p:*mut abi::IkcScdPacket,msg:i32,arg:u64)->i32;
    fn fixture_send(ch:*mut c_void,p:*mut abi::IkcScdPacket,flags:i32)->i32;
    fn fixture_pause();
    fn fixture_log(event:i32,error:i32);
    fn fixture_reset(p:i32,s:i32,delay:i32,n:i32);
    fn fixture_state()->*mut ArchVdso;
    fn fixture_channel()->*mut c_void;
    fn fixture_run_c()->i32;
    fn fixture_snapshot(out:*mut Snapshot);
}
fn snapshot()->Snapshot {
    let mut out=core::mem::MaybeUninit::<Snapshot>::uninit();
    unsafe { fixture_snapshot(out.as_mut_ptr());out.assume_init() }
}
#[test]
fn complete_original_flow_matches_rust() {
    assert_eq!(core::mem::size_of::<ArchVdso>(),88);
    assert_eq!(core::mem::align_of::<ArchVdso>(),8);
    assert_eq!(core::mem::offset_of!(ArchVdso,busy),0);
    assert_eq!(core::mem::offset_of!(ArchVdso,vdso_npages),8);
    assert_eq!(core::mem::offset_of!(ArchVdso,vgtod_virt),80);
    assert_eq!(core::mem::size_of::<abi::IkcScdPacket>(),128);
    assert_eq!(core::mem::offset_of!(abi::IkcScdPacket,msg),8);
    assert_eq!(core::mem::offset_of!(abi::IkcScdPacket,body)+16,40);
    let errors=[0,-1,-22,i32::MIN,i32::MAX];
    let mut cases=0;
    for prep in errors { for send in errors { for delay in [0,1,2,17] { for pages in [0,2,-1,i32::MIN,i32::MAX] {
        unsafe { fixture_reset(prep,send,delay,pages) };
        let c=unsafe { fixture_run_c() };let expected=snapshot();
        unsafe { fixture_reset(prep,send,delay,pages) };
        let r=unsafe { f06_vdso_info::vdso_info_body(fixture_state(),fixture_channel(),fixture_physical,
            fixture_prepare,fixture_send,fixture_pause,fixture_log) };let actual=snapshot();
        assert_eq!(r,c,"return {prep}/{send}/{delay}/{pages}");
        assert_eq!(actual,expected,"state/log/effects {prep}/{send}/{delay}/{pages}");
        assert_eq!(actual.preps,1);assert_eq!(actual.physical_calls,1);
        assert_eq!(actual.sends,if prep==0 {1}else{0});
        assert_eq!(actual.pauses,if prep==0 && send==0 {delay}else{0});
        cases+=1;
    }}}}
    assert_eq!(cases,500);
    println!("PASS actual original C vs Rust complete reset/prepare/send/volatile-poll/error/log equivalence: {cases} cases");
}
