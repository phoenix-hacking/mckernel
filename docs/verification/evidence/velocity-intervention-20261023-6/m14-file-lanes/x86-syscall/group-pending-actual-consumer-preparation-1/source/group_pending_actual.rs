// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,unused_imports)]
mod abi; mod lock_helpers; mod spinlock_helpers; mod list_helpers; mod string; mod mem_helpers;
use core::mem::{size_of,align_of,offset_of,MaybeUninit};
use core::ptr::null_mut;
use abi::{Thread,Process,SigInfo,AbiListHead,CInt,CULong,SizeT};
use lock_helpers::McsRwlockNodeIrqsave;
const ESRCH:CInt=3; const ENOMEM:CInt=12;
const SIGKILL:CInt=9; const SIGSTOP:CInt=19; const IHK_MC_AP_NOWAIT:CULong=2;
include!("group.FRAGMENT.rs"); include!("pending.FRAGMENT.rs");
include!("arena_bindings.rs");
#[no_mangle] pub extern "C" fn fixture_group_pending_actual_Rust_ABI(i:usize)->usize {
 let v=[size_of::<Thread>(),align_of::<Thread>(),size_of::<Process>(),align_of::<Process>(),size_of::<abi::ProcessHash>(),offset_of!(abi::ProcessHash,list),offset_of!(abi::ProcessHash,lock),abi::PROCESS_HASH_SIZE,size_of::<abi::SigPending>(),offset_of!(abi::SigPending,info),offset_of!(abi::SigPending,ptracecont),offset_of!(abi::SigPending,interrupted),size_of::<SigInfo>(),size_of::<abi::KmallocHeader>(),offset_of!(abi::CpuLocalVar,free_list),offset_of!(Thread,sigevent),offset_of!(Process,hash_list),size_of::<abi::McsRwlockLock>()];v[i]
}
