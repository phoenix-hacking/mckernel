//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Actual two entry bodies/ABI/time arithmetic; all OS/CPU effects controlled externally.
#![no_std]
#![feature(core_intrinsics)]
use core::ffi::c_void;
use core::mem::{MaybeUninit,offset_of,size_of,align_of};
use core::ptr::{addr_of,addr_of_mut,copy_nonoverlapping};
mod abi;
use abi::{CInt,CLong,CULong,CpuLocalVar,Thread,TimeSpec,TimeVal,TodData,ITimerVal,Process,IhkOsCpuMonitor,RusagePercpu};
const NS_PER_SEC:CLong=1_000_000_000;
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 static mut gettime_local_support:CInt;
 static mut tod_data:TodData;
 #[link_name="fixture_disable_irq"] fn cpu_disable_interrupt_save()->CULong;
 #[link_name="fixture_restore_irq"] fn cpu_restore_interrupt(flags:CULong);
 fn fixture_rdtsc()->CULong;
 fn fixture_set_timer(runq_locked:CInt);
 #[link_name="fixture_do_kill"] fn syscall_do_kill_thread_bridge(thread:*mut c_void,pid:CInt,tid:CInt,sig:CInt,info:*const abi::SigInfo,ptracecont:CInt)->CLong;
}
mod cls {unsafe extern "C" {pub static mut clv:*mut crate::abi::CpuLocalVar;}}
mod x86_cpu_helpers {pub unsafe fn rdtsc()->crate::abi::CULong{super::fixture_rdtsc()}}
mod sched_helpers {pub unsafe fn set_timer(n:crate::abi::CInt){super::fixture_set_timer(n)}}
mod timer {
 use crate::abi::{TimeSpec,TimeVal};
 const NS_PER_SEC:i64=1_000_000_000;const US_PER_SEC:i64=1_000_000;
 include!("ts_add.UNCHANGED-RUST.inc");
 include!("ts_to_tv.UNCHANGED-RUST.inc");
 include!("tv_sub.UNCHANGED-RUST.inc");
}
include!("tsc_to_ts.UNCHANGED-RUST.inc");
include!("cputime.RUST-FRAGMENT.rs.inc");
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_layout(out:*mut usize)->usize {
 let values=[size_of::<Thread>(),align_of::<Thread>(),offset_of!(Thread,base_tsc),offset_of!(Thread,user_tsc),offset_of!(Thread,system_tsc),offset_of!(Thread,times_update),offset_of!(Thread,in_kernel),offset_of!(Thread,itimer_enabled),offset_of!(Thread,itimer_virtual),offset_of!(Thread,itimer_prof),offset_of!(Thread,itimer_virtual_value),offset_of!(Thread,itimer_prof_value),offset_of!(Thread,proc),offset_of!(Thread,tid),size_of::<CpuLocalVar>(),align_of::<CpuLocalVar>(),offset_of!(CpuLocalVar,current),offset_of!(CpuLocalVar,idle),offset_of!(CpuLocalVar,monitor),offset_of!(CpuLocalVar,rusage),size_of::<IhkOsCpuMonitor>(),align_of::<IhkOsCpuMonitor>(),offset_of!(IhkOsCpuMonitor,status),offset_of!(IhkOsCpuMonitor,status_bak),offset_of!(IhkOsCpuMonitor,counter),offset_of!(IhkOsCpuMonitor,ocounter),size_of::<RusagePercpu>(),align_of::<RusagePercpu>(),offset_of!(RusagePercpu,user_tsc),offset_of!(RusagePercpu,system_tsc),size_of::<Process>(),align_of::<Process>(),offset_of!(Process,pid),size_of::<ITimerVal>(),align_of::<ITimerVal>(),offset_of!(ITimerVal,it_interval),offset_of!(ITimerVal,it_value),size_of::<TimeSpec>(),align_of::<TimeSpec>(),offset_of!(TimeSpec,tv_sec),offset_of!(TimeSpec,tv_nsec),size_of::<TimeVal>(),align_of::<TimeVal>(),offset_of!(TimeVal,tv_sec),offset_of!(TimeVal,tv_usec),size_of::<TodData>(),align_of::<TodData>(),offset_of!(TodData,clocks_per_sec)];
 copy_nonoverlapping(values.as_ptr(),out,values.len());values.len()
}
