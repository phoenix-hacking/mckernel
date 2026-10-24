// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// libc owns kernel signal ABI adaptation; Rust owns project action/lifecycle logic.
use super::{c_int,c_long,c_ulong,c_void};
use core::ptr::{addr_of_mut,null_mut};
#[repr(C)]
struct SigSet { bits:[c_ulong;16] }
#[repr(C)]
struct SigAction { handler:usize, mask:SigSet, flags:c_int, restorer:usize }
#[repr(C,align(8))]
struct SigInfo { bytes:[u8;128] }
unsafe extern "C" {
 static mut master_tid:c_int;
 static mut debug:c_int;
 static mut stdout:*mut c_void;
 static mut stderr:*mut c_void;
 fn sigaction(sig:c_int,action:*const SigAction,old:*mut SigAction)->c_int;
 fn sigemptyset(set:*mut SigSet)->c_int;
 fn sigdelset(set:*mut SigSet,sig:c_int)->c_int;
 fn sigprocmask(how:c_int,set:*const SigSet,old:*mut SigSet)->c_int;
 fn waitid(kind:c_int,pid:u32,info:*mut SigInfo,options:c_int)->c_int;
 fn write(fd:c_int,buf:*const c_void,size:usize)->isize;
 fn signal(sig:c_int,handler:usize)->usize;
 fn kill(pid:c_int,sig:c_int)->c_int;
 fn sleep(seconds:u32)->u32;
 fn pause()->c_int;
 fn exit(code:c_int)->!;
 fn isatty(fd:c_int)->c_int;
 fn fprintf(stream:*mut c_void,format:*const u8,...)->c_int;
 fn printf(format:*const u8,...)->c_int;
 fn fflush(stream:*mut c_void)->c_int;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_sendsig_si_pid_bridge(info:*const c_void)->c_int { info.cast::<u8>().add(16).cast::<c_int>().read() }
#[no_mangle]
pub unsafe extern "C" fn mcexec_sendsig_si_signo_bridge(info:*const c_void)->c_int { info.cast::<c_int>().read() }
#[no_mangle]
pub unsafe extern "C" fn mcexec_sendsig_default_action_bridge(sig:c_int) {
 signal(sig,0);kill(super::getpid(),sig);loop { sleep(1); }
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_act_signalfd4_write_bridge(fd:c_int,info:*const c_void,len:usize)->isize { write(fd,info,len) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_act_signalfd4_write_error_bridge() { fprintf(stderr,b"error: writing sigpipe\n\0".as_ptr()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_act_sigaction_install_bridge(sig:c_int,ignored:c_int) {
 let mut act:SigAction=core::mem::zeroed();
 if ignored!=0 { act.handler=1; } else {act.handler=super::sendsig as usize;act.flags=4;}
 sigaction(sig,&act,null_mut());
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_act_sigprocmask_apply_bridge(mask:c_ulong) {
 let mut set:SigSet=core::mem::zeroed();
 sigemptyset(addr_of_mut!(set));
 set.bits[0]=mask;
 sigdelset(addr_of_mut!(set),23); // LOCALSIG == SIGURG.
 sigprocmask(2,&set,null_mut()); // SIG_SETMASK.
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_sigaction_set_master_tid_bridge(tid:c_int) { master_tid=tid; }
#[no_mangle]
pub unsafe extern "C" fn mcexec_init_sigaction_install_bridge(sig:c_int) {
 // Deliberate defined extension: a failed query leaves zeros instead of the
 // original uninitialized C struct. Defined successful-query behavior is parity.
 let mut act:SigAction=core::mem::zeroed();
 sigaction(sig,core::ptr::null(),addr_of_mut!(act));
 act.handler=super::sendsig as usize;
 act.flags=(act.flags & !0x10000000)|4; // clear SA_RESTART, set SA_SIGINFO.
 sigaction(sig,&act,null_mut());
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_waitid_pid_bridge(pid:c_int,opt:c_int,errno_out:*mut c_int)->c_int {
 let mut info:SigInfo=core::mem::zeroed();
 let mut ret;
 loop {
   ret=waitid(1,pid as u32,addr_of_mut!(info),opt); // P_PID.
   if ret!=-1 || *super::__errno_location()!=4 { break; }
 }
 if !errno_out.is_null() { *errno_out=*super::__errno_location(); }
 if ret==0 {ret=mcexec_sendsig_si_pid_bridge(addr_of_mut!(info).cast());}
 ret
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_wait4_error_bridge(pid:c_ulong,ret:c_int,error:c_int) { fprintf(stderr,b"ERROR: waiting for %lu rc=%d errno=%d\n\0".as_ptr(),pid,ret,error); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_debug_bridge(status:c_ulong,cpu:c_int) {
 if debug!=0 {printf(b"mcexec_exit_debug_bridge: __NR_exit/__NR_exit_group: %ld (cpu_id: %d)\n\0".as_ptr(),status,cpu);fflush(stdout);}
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_isatty_bridge(fd:c_int)->c_int { isatty(fd) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_report_signal_bridge(sig:c_int) {fprintf(stderr,b"Terminate by signal %d\n\0".as_ptr(),sig);}
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_report_status_bridge(term:c_int) {
 if debug!=0 {printf(b"mcexec_exit_report_status_bridge: Exit status: %d\n\0".as_ptr(),term);fflush(stdout);}
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_replay_signal_bridge(sig:c_int) {signal(sig,0);kill(super::getpid(),sig);pause();}
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_process_bridge(term:c_int) {exit(term);}
#[cfg(mcexec_signal_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_signal_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<SigInfo>(),core::mem::align_of::<SigInfo>(),0,16,
 core::mem::size_of::<SigAction>(),core::mem::align_of::<SigAction>(),core::mem::offset_of!(SigAction,handler),core::mem::offset_of!(SigAction,mask),core::mem::offset_of!(SigAction,flags),core::mem::offset_of!(SigAction,restorer),core::mem::size_of::<SigSet>(),core::mem::align_of::<SigSet>()];
 core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
