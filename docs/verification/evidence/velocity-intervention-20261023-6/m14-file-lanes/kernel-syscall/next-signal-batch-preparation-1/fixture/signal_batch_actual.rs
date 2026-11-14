//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Exact three candidate bodies plus unchanged helpers/ABI; controlled callback effects only.
#![no_std]
use core::ffi::c_void;
use core::mem::{offset_of,size_of,align_of,MaybeUninit};
use core::ptr::{addr_of,addr_of_mut,write_volatile,read_volatile,copy_nonoverlapping,null_mut};
mod abi;
use abi::{AbiListHead,CInt,CLong,CULong,SizeT,Thread,SigCommon,SigSet,KSigAction,CpuLocalVar,IhkOsCpuMonitor};
const EINVAL:CInt=22;const EFAULT:CInt=14;const EINTR:CInt=4;
const SIGKILL:CInt=9;const SIGSTOP:CInt=19;const NSIG:CInt=64;
const SIGKILL_MASK:CULong=1<<8;const SIGSTOP_MASK:CULong=1<<18;
const IHK_OS_MONITOR_KERNEL_HEAVY:CInt=4;
const PS_INTERRUPTIBLE:CInt=2;const PS_RUNNING:CInt=1;const CPU_FLAG_NEED_RESCHED:u32=1;
type SyscallSigcommonLockFn=unsafe extern "C" fn(*mut c_void,*mut c_void);
type SyscallSigactionForwardFn=unsafe extern "C" fn(CInt,*const c_void)->CLong;
unsafe extern "C" {
 fn get_this_cpu_local_var()->*mut CpuLocalVar;
 #[link_name="fixture_disable_irq"] fn cpu_disable_interrupt_save()->CULong;
 #[link_name="fixture_restore_irq"] fn cpu_restore_interrupt(v:CULong);
 #[link_name="fixture_schedule"] fn schedule();
 #[link_name="fixture_pause"] fn cpu_pause();
 fn fixture_writer_lock(lock:*mut c_void,node:*mut c_void);
 fn fixture_writer_unlock(lock:*mut c_void,node:*mut c_void);
 fn fixture_runq_lock(lock:*mut c_void);
 fn fixture_runq_unlock(lock:*mut c_void);
}
unsafe fn current_thread_ptr()->*mut Thread{(*get_this_cpu_local_var()).current}
mod lock_helpers {
 #[repr(C,align(64))] pub struct McsRwlockNodeIrqsave{pub irqsave:u64}
 pub unsafe fn __mcs_rwlock_writer_lock(lock:*mut crate::abi::McsRwlockLock,node:*mut McsRwlockNodeIrqsave){super::fixture_writer_lock(lock.cast(),node.cast())}
 pub unsafe fn __mcs_rwlock_writer_unlock(lock:*mut crate::abi::McsRwlockLock,node:*mut McsRwlockNodeIrqsave){super::fixture_writer_unlock(lock.cast(),node.cast())}
}
use lock_helpers::McsRwlockNodeIrqsave;
mod spinlock_helpers {
 pub unsafe fn __ihk_mc_spinlock_lock_noirq(lock:*mut crate::abi::IhkSpinlock){super::fixture_runq_lock(lock.cast())}
 pub unsafe fn __ihk_mc_spinlock_unlock_noirq(lock:*mut crate::abi::IhkSpinlock){super::fixture_runq_unlock(lock.cast())}
}
mod process_helpers {
 use crate::abi::AbiListHead;
 const LIST_POISON1:usize=0x0010_0129;const LIST_POISON2:usize=0x0020_0229;
 include!("process_list_detach.UNCHANGED-RUST.inc");
}
include!("sigaction_validate.UNCHANGED-RUST.inc");
include!("sigsuspend_prepare_mask.UNCHANGED-RUST.inc");
include!("sigsuspend_pending_matches.UNCHANGED-RUST.inc");
include!("do_sigaction_body_result.UNCHANGED-RUST.inc");
include!("pending_mask.EXACT-RUST.inc");
include!("sigsuspend.EXACT-RUST.inc");
include!("do_sigaction.EXACT-RUST.inc");
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_layout(out:*mut usize)->usize {
 let a=[size_of::<Thread>(),align_of::<Thread>(),offset_of!(Thread,status),offset_of!(Thread,sigcommon),offset_of!(Thread,sigmask),offset_of!(Thread,sigpending),offset_of!(Thread,sigpendinglock),offset_of!(Thread,sigevent),size_of::<SigCommon>(),align_of::<SigCommon>(),offset_of!(SigCommon,lock),offset_of!(SigCommon,action),offset_of!(SigCommon,sigpending),size_of::<abi::SigPending>(),align_of::<abi::SigPending>(),offset_of!(abi::SigPending,list),offset_of!(abi::SigPending,sigmask),offset_of!(abi::SigPending,info),size_of::<CpuLocalVar>(),align_of::<CpuLocalVar>(),offset_of!(CpuLocalVar,runq_lock),offset_of!(CpuLocalVar,current),offset_of!(CpuLocalVar,flags),offset_of!(CpuLocalVar,monitor),size_of::<IhkOsCpuMonitor>(),offset_of!(IhkOsCpuMonitor,status),size_of::<KSigAction>(),align_of::<KSigAction>(),offset_of!(KSigAction,sa),size_of::<McsRwlockNodeIrqsave>(),align_of::<McsRwlockNodeIrqsave>(),size_of::<SigSet>(),size_of::<abi::McsRwlockLock>(),align_of::<abi::McsRwlockLock>()];
 copy_nonoverlapping(a.as_ptr(),out,a.len());a.len()
}
