// SPDX-License-Identifier: GPL-2.0-only
//! Exact timeout/countdown/target-VM copy bodies with controlled providers.
#![allow(dead_code)]
#[path = "abi.rs"]
mod abi;
#[path = "native_futex.rs"]
mod actual_native_futex;
use abi::{CInt, CULong, TimeSpec};
use core::{mem::{offset_of, size_of}, ptr::{read_volatile, write_volatile}};
use std::cell::{Cell, RefCell};

thread_local! {
    static CLOCK: Cell<u64> = const { Cell::new(0) };
    static SCHEDULES: Cell<u32> = const { Cell::new(0) };
    static SLEEP: Cell<usize> = const { Cell::new(0) };
    static TIMESTAMP: Cell<(i64,i64)> = const { Cell::new((0,0)) };
    static COPY_COUNT: Cell<usize> = const { Cell::new(0) };
    static COPY_FAIL: Cell<bool> = const { Cell::new(false) };
    static COPY_TAMPER: Cell<bool> = const { Cell::new(false) };
    static QUEUE_TIMEOUTS: RefCell<Vec<u64>> = const { RefCell::new(Vec::new()) };
    static PUTS: Cell<u32> = const { Cell::new(0) };
}
mod native_futex {
    pub(crate) use crate::actual_native_futex::timeout;
    pub(crate) fn ticks_now() -> u64 { super::CLOCK.get() }
}
mod native_vdso {
    pub(crate) fn clock(_:i32)->Option<crate::abi::TimeSpec> { None }
}
include!("timer-bodies.rs");

unsafe extern "C" fn copy_timeout(dst: *mut u8, src: u64, size: usize) -> i64 {
    COPY_COUNT.set(COPY_COUNT.get()+1);
    assert_eq!(size, 16);
    if COPY_FAIL.get() || src != 0x10000 { return -14; }
    let (tv_sec,tv_nsec)=TIMESTAMP.get();
    unsafe { (dst as *mut TimeSpec).write(TimeSpec {tv_sec,tv_nsec}); }
    if COPY_TAMPER.get() { TIMESTAMP.set((-1,-1)); }
    0
}
fn timeout(flags:i32, pointer:u64, clock:Result<TimeSpec,i64>, scale:u64)->Result<u64,i64> {
    COPY_COUNT.set(0);
    unsafe { actual_native_futex::timeout(flags,pointer,0,Some(copy_timeout), |_| {
        match &clock { Ok(ts)=>Ok(TimeSpec {tv_sec:ts.tv_sec,tv_nsec:ts.tv_nsec}),Err(e)=>Err(*e) }
    }, || Ok(scale)) }
}

#[test]
fn exact_pinned_linux_time_vectors() {
    let input=std::fs::read("vectors.bin").unwrap();
    let reference=std::fs::read_to_string("linux-reference.log").unwrap();
    let lines:Vec<_>=reference.lines().collect();
    assert_eq!(input.len(),lines.len()*40);
    for (index,row) in input.chunks_exact(40).enumerate() {
        let word=|offset:usize|i64::from_le_bytes(row[offset..offset+8].try_into().unwrap());
        let ts=TimeSpec {tv_sec:word(8),tv_nsec:word(16)};
        let now=TimeSpec {tv_sec:word(24),tv_nsec:word(32)};
        let expected:Vec<i128>=lines[index].split_whitespace().map(|x|x.parse().unwrap()).collect();
        assert_eq!(expected[0],index as i128);
        let actual=actual_native_futex::nanoseconds(&ts).and_then(|target|actual_native_futex::remaining(word(0) as i32,target,&now));
        match actual { Ok(left)=>assert_eq!((0,left as i128),(expected[1],expected[2]),"vector {index}"),Err(e)=>assert_eq!(e as i128,expected[1],"vector {index}") }
    }
    assert!(lines.len()>=200);
}

#[test]
fn copy_once_validation_precedence_and_snapshot() {
    assert_eq!(size_of::<TimeSpec>(),16);
    COPY_FAIL.set(true);
    assert_eq!(timeout(256,0x10000,Err(-5),1000),Err(-14));
    assert_eq!(COPY_COUNT.get(),1);
    COPY_FAIL.set(false);TIMESTAMP.set((-1,0));
    assert_eq!(timeout(256,0x10000,Err(-5),1000),Err(-22));
    TIMESTAMP.set((1,0));
    assert_eq!(timeout(256,0x10000,Err(-5),1000),Err(-38));
    COPY_TAMPER.set(true);
    assert_eq!(timeout(0,0x10000,Ok(TimeSpec{tv_sec:10,tv_nsec:0}),1000),Ok(1_000_000_000));
    assert_eq!(COPY_COUNT.get(),1);assert_eq!(TIMESTAMP.get(),(-1,-1));
    COPY_TAMPER.set(false);
    for ts in [(-1,0),(0,-1),(0,1_000_000_000)] {
        TIMESTAMP.set(ts);assert_eq!(timeout(9,0x10000,Err(-5),1000),Err(-22));
    }
}

#[test]
fn no_timeout_expired_and_capabilities_are_distinct() {
    assert_eq!(timeout(0,0,Err(-5),0),Ok(0));assert_eq!(COPY_COUNT.get(),0);
    TIMESTAMP.set((0,0));
    assert_eq!(timeout(0,0x10000,Ok(TimeSpec{tv_sec:10,tv_nsec:0}),1000),Ok(1));
    assert_eq!(timeout(9,0x10000,Ok(TimeSpec{tv_sec:10,tv_nsec:0}),1000),Ok(1));
    assert_eq!(timeout(9,0x10000,Err(-95),1000),Err(-95));
    assert_eq!(timeout(5,0,Err(-5),1000),Err(-95));
    assert_eq!(timeout(6,0,Err(-5),1000),Err(-38));
    assert_eq!(timeout(1,0xBAD,Err(-5),1000),Ok(0));assert_eq!(COPY_COUNT.get(),0);
}

#[test]
fn scaling_never_wraps_or_selects_infinite() {
    for nanos in [0,1,999,1_000_000_000,i64::MAX as u64,u64::MAX] {
        for scale in [1,10,333,1000,1001,u64::MAX] {
            let actual=actual_native_futex::timer_ticks(nanos,scale).unwrap();
            let n=nanos as u128*1000;let d=scale as u128;
            let exact=(n/d+u128::from(n%d!=0)).clamp(1,i64::MAX as u128);
            assert_eq!(actual as u128,exact);
        }
    }
    assert_eq!(actual_native_futex::timer_ticks(1,0),Err(-22));
}

#[test]
fn complete_word_range_rejects_kernel_wrap_and_misalignment() {
    assert_eq!(actual_native_futex::word_range(0x1000,0x1000,0x2000),Ok(()));
    assert_eq!(actual_native_futex::word_range(0x1ffc,0x1000,0x2000),Ok(()));
    for addr in [0,0x2000,u64::MAX-3,0xffff800000000000] {
        assert_eq!(actual_native_futex::word_range(addr,0x1000,0x2000),Err(-14));
    }
    assert_eq!(actual_native_futex::word_range(0x1fff,0x1000,0x2000),Err(-22));
}

mod selected_policy {
    use crate::abi::{CInt,CLong,CULong,TimeSpec};
    use core::{mem::MaybeUninit,ptr::{write,write_volatile}};
    use super::copy_timeout as syscall_copy_from_user_bridge;
    include!("policy-bodies.rs");
    thread_local! {static DISPATCH: std::cell::Cell<(i32,u64,u32)> = const { std::cell::Cell::new((-1,0,0)) };}
    unsafe extern "C" fn clock(n:i32,id:i32,ts:*mut TimeSpec)->i32 {assert_eq!(n,202);assert_eq!(id,1);unsafe{ts.write(TimeSpec{tv_sec:10,tv_nsec:0})};0}
    unsafe extern "C" fn scale()->u64 {1000}
    unsafe extern "C" fn dispatch(_:u64,op:i32,_:u32,timeout:u64,_:u64,val2:u32,_:u32,_:i32)->i32 {DISPATCH.set((op,timeout,val2));-11}
    fn call(op:u64,arg3:u64)->i64 {unsafe{do_futex_body_result(202,0x2000,op,1,arg3,0x3000,1,0,0,Some(clock),None,None,Some(scale),Some(dispatch),None)}}
    #[test]
    fn selected_native_entry_copies_timeout_and_preserves_requeue_count() {
        super::COPY_FAIL.set(false);super::COPY_TAMPER.set(false);super::TIMESTAMP.set((0,0));super::COPY_COUNT.set(0);
        assert_eq!(call(0,0x10000),-11);assert_eq!(super::COPY_COUNT.get(),1);assert_eq!(DISPATCH.get(),(0,1,0));
        assert_eq!(call(3,7),-11);assert_eq!(DISPATCH.get(),(3,0,7));
        DISPATCH.set((-1,0,0));assert_eq!(call(5,7),-95);assert_eq!(DISPATCH.get(),(-1,0,0));
    }
}

#[repr(C)] struct TimerThread {status:i32,sleep:i32,lock:u64}
#[repr(C)] struct TimerCpu {lock:u64,len:usize}
unsafe extern "C" fn tsc()->u64 {CLOCK.get()}
unsafe extern "C" fn lock(_:usize)->u64 {0}
unsafe extern "C" fn unlock(_:usize,_:u64) {}
unsafe extern "C" fn set_status(p:usize,v:i32) {unsafe{(p as *mut i32).write(v)}}
unsafe extern "C" fn schedule() {SCHEDULES.set(SCHEDULES.get()+1);assert!(SCHEDULES.get()<100);CLOCK.set(CLOCK.get().wrapping_add(40));}
unsafe extern "C" fn zero_free() {}
unsafe extern "C" fn pause() {CLOCK.set(CLOCK.get().wrapping_add(7));}
fn offsets()->TimerRuntimeOffsets {
    let mut result:TimerRuntimeOffsets=unsafe{core::mem::zeroed()};
    result.thread_status_offset=offset_of!(TimerThread,status);result.thread_spin_sleep_offset=offset_of!(TimerThread,sleep);
    result.thread_spin_sleep_lock_offset=offset_of!(TimerThread,lock);result.cpu_runq_lock_offset=offset_of!(TimerCpu,lock);result.cpu_runq_len_offset=offset_of!(TimerCpu,len);result
}
fn timer(initial:u64,clock:u64,runnable:usize)->(u64,TimerThread) {
    CLOCK.set(clock);SCHEDULES.set(0);
    let mut thread=TimerThread{status:2,sleep:1,lock:0};let mut cpu=TimerCpu{lock:0,len:runnable};
    let result=unsafe{timer_schedule_timeout_body_result(&mut thread as *mut _ as usize,&mut cpu as *mut _ as usize,initial,100,&offsets(),Some(tsc),Some(lock),Some(unlock),Some(set_status),Some(schedule),Some(zero_free),Some(pause))};
    (result,thread)
}
#[test]
fn countdown_expires_while_other_threads_remain_runnable() {
    let (left,thread)=timer(100,0,2);assert_eq!(left,0);assert_eq!(thread.sleep,0);assert_eq!(SCHEDULES.get(),3);
}
#[test]
fn countdown_handles_short_wait_and_tsc_wrap() {
    let (left,thread)=timer(1,0,1);assert_eq!(left,0);assert_eq!(thread.sleep,0);assert_eq!(CLOCK.get(),7);
    let (left,thread)=timer(100,u64::MAX-50,2);assert_eq!(left,0);assert_eq!(thread.sleep,0);assert_eq!(SCHEDULES.get(),3);
}

#[repr(C)] struct Q {bitset:u32,pad:u32,pi:usize,uti:usize,key:usize}
unsafe extern "C" fn setup(_:usize,_:u32,_:i32,_:usize,hb:usize)->i32 {unsafe{(hb as *mut usize).write(1)};0}
unsafe extern "C" fn queued(_:usize,_:usize,timeout:u64)->i64 {QUEUE_TIMEOUTS.with(|v|v.borrow_mut().push(timeout));CLOCK.set(CLOCK.get()+40);if timeout<=40{0}else{(timeout-40) as i64}}
unsafe extern "C" fn unqueue(_:usize)->i32 {1}
unsafe extern "C" fn no_signal(_:usize)->i32 {0}
unsafe extern "C" fn put(_:i32,_:usize) {PUTS.set(PUTS.get()+1)}
unsafe extern "C" fn log(_:i32,_:usize,_:i32,_:i32) {}
#[test]
fn spurious_retry_retains_one_overall_deadline() {
    CLOCK.set(0);PUTS.set(0);QUEUE_TIMEOUTS.with(|v|v.borrow_mut().clear());
    let mut q=Q{bitset:0,pad:0,pi:0,uti:0,key:0};let mut tid=9i32;
    let result=unsafe{futex_wait_body_result(0x1000,0,1,100,!0,&mut q as *mut _ as usize,&mut tid as *mut _ as usize,0,offset_of!(Q,bitset),offset_of!(Q,pi),offset_of!(Q,uti),offset_of!(Q,key),0,Some(setup),Some(queued),Some(unqueue),Some(no_signal),Some(put),Some(log))};
    assert_eq!(result,-110);assert_eq!(PUTS.get(),3);QUEUE_TIMEOUTS.with(|v|assert_eq!(&*v.borrow(),&[100,60,20]));
}

mod target_copy {
    use crate::abi::{CInt, CULong, SizeT};
    use core::{ffi::c_void, ptr::{read_volatile,write_volatile}};
    use std::cell::{Cell,RefCell};
    include!("copy-bodies.rs");
    thread_local! {
        static PAGES: RefCell<[Vec<u8>;2]> = RefCell::new([vec![0x5a;4096],vec![0xa5;4096]]);
        static PERMISSIONS: Cell<[bool;2]> = const { Cell::new([true,true]) };
        static FAULTED: RefCell<Vec<(usize,usize,u64)>> = const { RefCell::new(Vec::new()) };
    }
    unsafe extern "C" fn fault(vm:*mut c_void,addr:*mut c_void,reason:u64)->i32 {
        assert_eq!(vm as usize,2);assert_eq!(reason,0x40000006);
        let index=match addr as usize {0x1000=>0,0x2000=>1,_=>return -14};
        FAULTED.with(|v|v.borrow_mut().push((vm as usize,addr as usize,reason)));
        if PERMISSIONS.get()[index] {0}else{-14}
    }
    unsafe extern "C" fn vtop(pt:*mut c_void,addr:*const c_void,pa:*mut u64)->i32 {
        assert_eq!(pt as usize,3);let address=addr as u64;
        let base=match address & !4095 {0x1000=>0x8000,0x2000=>0xd000,_=>return -14};
        unsafe{pa.write(base+(address&4095))};0
    }
    unsafe extern "C" fn is_memory(_:u64,_:u64)->i32 {1}
    unsafe extern "C" fn map(_:u64,_:i32,_:u64)->*mut c_void {panic!("unexpected device map")}
    unsafe extern "C" fn unmap(_:*mut c_void,_:i32) {panic!("unexpected device unmap")}
    unsafe extern "C" fn direct(pa:u64)->*mut c_void {
        let (index,base)=if (0x8000..0x9000).contains(&pa){(0,0x8000)}else{assert!((0xd000..0xe000).contains(&pa));(1,0xd000)};
        PAGES.with(|v|unsafe{v.borrow_mut()[index].as_mut_ptr().add((pa-base) as usize).cast()})
    }
    fn reset() {PAGES.with(|v|{v.borrow_mut()[0].fill(0x5a);v.borrow_mut()[1].fill(0xa5)});FAULTED.with(|v|v.borrow_mut().clear());}
    fn store(address:u64)->i32 {
        let tid=0x12345678u32;
        unsafe{x86_process_vm_copy_result(2usize as *mut c_void,3usize as *mut c_void,address,&tid as *const _ as u64,4,0x1000,0x3000,0x40000006,X86_USER_COPY_WRITE,Some(fault),Some(vtop),Some(is_memory),Some(map),Some(unmap),Some(direct),None)}
    }
    #[test]
    fn child_tid_span_uses_each_virtual_page_and_child_owner() {
        PERMISSIONS.set([true,true]);
        for address in [0x1000,0x1ffc,0x1ffd,0x1ffe,0x1fff] {
            reset();assert_eq!(store(address),0);
            PAGES.with(|v|{let pages=v.borrow();let all:Vec<u8>=pages.iter().flatten().copied().collect();let mut expected=[vec![0x5a;4096],vec![0xa5;4096]].concat();let offset=(address-0x1000) as usize;expected[offset..offset+4].copy_from_slice(&0x12345678u32.to_le_bytes());assert_eq!(all,expected);});
            FAULTED.with(|v|assert!(v.borrow().iter().all(|entry|entry.0==2)));
        }
    }
    #[test]
    fn child_tid_permission_or_span_failure_has_no_canary_write() {
        for permissions in [[false,true],[true,false],[false,false]] {
            PERMISSIONS.set(permissions);reset();assert_eq!(store(0x1fff),-14);
            PAGES.with(|v|{let p=v.borrow();assert!(p[0].iter().all(|x|*x==0x5a));assert!(p[1].iter().all(|x|*x==0xa5));});
        }
        PERMISSIONS.set([true,true]);reset();assert_eq!(store(0x2fff),-14);assert_eq!(store(u64::MAX-2),-14);FAULTED.with(|v|assert!(v.borrow().is_empty()));
    }
}
