//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Runs the actual private constructor bodies against a synchronous scalar observer.
//! No host transaction, mapping, response or lifetime acceptance is represented.
#![allow(non_snake_case)]
use std::sync::Mutex;
mod abi {
    pub type CInt = i32;
    pub type CLong = i64;
    pub type CULong = u64;
    #[repr(C)]
    pub struct SyscallRequest {
        pub rtid: CInt, pub ttid: CInt, pub valid: CULong,
        pub number: CULong, pub args: [CULong; 6],
    }
}
#[path = "postimage/kernel/rust/f03_request_constructors.rs"]
mod constructors;
struct Expected { number: u64, args: [u64; 6], result: i64, calls: usize }
static EXPECTED: Mutex<Option<Expected>> = Mutex::new(None);
unsafe fn ihk_mc_get_processor_id() -> i32 { 3 }
unsafe fn do_syscall(request: *mut abi::SyscallRequest, cpu: i32) -> i64 {
    assert_eq!(cpu, 3);
    let mut state = EXPECTED.lock().unwrap();
    let expected = state.as_mut().unwrap();
    // Caller only owns number+args: inspect no uninitialized ID/valid bytes.
    unsafe {
        assert_eq!(std::ptr::addr_of!((*request).number).read(), expected.number);
        for i in 0..6 {
            assert_eq!(std::ptr::addr_of!((*request).args).cast::<u64>().add(i).read(), expected.args[i]);
        }
        // Model the existing sender's own writes, never a caller prerequisite.
        std::ptr::addr_of_mut!((*request).rtid).write(71);
        std::ptr::addr_of_mut!((*request).ttid).write(0);
        std::ptr::addr_of_mut!((*request).valid).write(0);
    }
    expected.calls += 1;
    expected.result
}
fn expect(number: i32, args: [u64;6], result: i64) {
    *EXPECTED.lock().unwrap() = Some(Expected { number:number as u64,args,result,calls:0 });
}
fn done() { assert_eq!(EXPECTED.lock().unwrap().as_ref().unwrap().calls, 1); }
#[test]
fn actual_constructors_preserve_defined_arguments_and_conversions() {
    // A single sequential test keeps observer ownership deterministic.
    for number in [201,228,96,35,142,36,122,123,802] {
        for callback in [constructors::syscall_do_syscall2_bridge,
                         constructors::syscall_policy_do_syscall2_bridge] {
            expect(number,[u64::MAX,1<<63,0,0,0,0],i64::MIN);
            assert_eq!(unsafe { callback(number,u64::MAX,1<<63) },i64::MIN); done();
        }
    }
    for number in [11,38] {
        for callback in [constructors::syscall_do_syscall3_bridge,
                         constructors::syscall_policy_do_syscall3_bridge] {
            expect(number,[u64::MAX,1<<63,7,0,0,0],-1);
            assert_eq!(unsafe { callback(number,u64::MAX,1<<63,7) },-1); done();
        }
    }
    for pid in [i32::MIN,-1,0,i32::MAX] {
        for options in [i32::MIN,-1,0,i32::MAX] {
            let ret=0x1234_5678_ffff_ff80u64 as i64;
            expect(61,[pid as u64,0,options as u64,0,0,0],ret);
            assert_eq!(unsafe { constructors::wait_host_wait4_bridge(pid,options) },ret as i32); done();
        }
    }
}
