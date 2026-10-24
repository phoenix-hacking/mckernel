// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Initialized production globals/option table replace the last default C provider.
// Linux x86_64 glibc pthread storage ABI is checked against actual C headers.
use super::{c_int,c_long,c_ulong,c_void,McexecThreadData,ForkSyncContainer,McexecListHead};
use core::ptr::{addr_of_mut,null_mut};
#[repr(C,align(8))]
pub struct MutexStorage { bytes:[u8;40] }
#[repr(C,align(8))]
pub struct BarrierStorage { bytes:[u8;32] }
#[repr(C)]
pub struct GlobalRlimit { rlim_cur:c_ulong,rlim_max:c_ulong }
#[repr(C)]
pub struct GetOptOption {name:*const u8,has_arg:c_int,flag:*mut c_int,value:c_int}
#[no_mangle]
pub static mut mcosid:c_int=0;
#[no_mangle]
pub static mut fd:c_int=0;
#[no_mangle]
pub static mut ischild:c_int=0;
#[no_mangle]
pub static mut enable_vdso:c_int=1;
#[no_mangle]
pub static mut mpol_no_heap:c_int=0;
#[no_mangle]
pub static mut mpol_no_stack:c_int=0;
#[no_mangle]
pub static mut mpol_no_bss:c_int=0;
#[no_mangle]
pub static mut mpol_shm_premap:c_int=0;
#[no_mangle]
pub static mut no_bind_ikc_map:c_int=0;
#[no_mangle]
pub static mut straight_map:c_int=0;
#[no_mangle]
pub static mut profile:c_int=0;
#[no_mangle]
pub static mut disable_sched_yield:c_int=0;
#[no_mangle]
pub static mut uti_thread_rank:c_int=0;
#[no_mangle]
pub static mut uti_use_last_cpu:c_int=0;
#[no_mangle]
pub static mut enable_uti:c_int=0;
#[no_mangle]
pub static mut nr_processes:c_int=0;
#[no_mangle]
pub static mut nr_threads:c_int=-1;
#[no_mangle]
pub static mut master_tid:c_int=0;
#[no_mangle]
pub static mut ncpu:c_int=0;
#[no_mangle]
pub static mut nnodes:c_int=0;
#[no_mangle]
pub static mut n_threads:c_int=0;
#[no_mangle]
pub static mut overlay_fd_lock:c_int=0;
#[no_mangle]
pub static mut debug:c_int=cfg!(mcexec_debug) as c_int;
#[no_mangle]
pub static mut straight_map_threshold:c_ulong=1024*1024;
#[no_mangle]
pub static mut mpol_threshold:c_ulong=0;
#[no_mangle]
pub static mut heap_extension:c_ulong=c_ulong::MAX;
#[no_mangle]
pub static mut mcexec_flags:c_ulong=0;
#[no_mangle]
pub static mut page_size:c_ulong=0;
#[no_mangle]
pub static mut page_mask:c_ulong=0;
#[no_mangle]
pub static mut stack_premap:c_long=2*1024*1024;
#[no_mangle]
pub static mut stack_max:c_long=-1;
#[cfg(mcexec_enable_tofu)]
#[no_mangle]
pub static mut enable_tofu:c_int=0;
#[no_mangle]pub static mut exec_path:*mut u8=null_mut();
#[no_mangle]pub static mut altroot:*mut u8=null_mut();
#[no_mangle]pub static mut mpol_bind_nodes:*mut u8=null_mut();
#[no_mangle]pub static mut dma_buf:*mut u8=null_mut();
#[no_mangle]pub static mut thread_data:*mut McexecThreadData=null_mut();
#[no_mangle]pub static mut fork_sync_top:*mut ForkSyncContainer=null_mut();
#[no_mangle]pub static mut numa_nodes:*mut c_void=null_mut();
#[no_mangle]pub static mut cpu_set_size:usize=0;
#[no_mangle]pub static mut dev:[u8;64]=[0;64];
#[no_mangle]pub static mut rlim_stack:GlobalRlimit=GlobalRlimit{rlim_cur:0,rlim_max:0};
#[no_mangle]pub static mut lock:MutexStorage=MutexStorage{bytes:[0;40]};
#[no_mangle]pub static mut fork_sync_mutex:MutexStorage=MutexStorage{bytes:[0;40]};
#[no_mangle]pub static mut init_ready:BarrierStorage=BarrierStorage{bytes:[0;32]};
#[no_mangle]pub static mut uti_init_ready:BarrierStorage=BarrierStorage{bytes:[0;32]};
#[no_mangle]pub static mut mcexec_partition_cpu_set_storage:[c_ulong;16]=[0;16];
#[no_mangle]pub static mut overlay_fd_list:McexecListHead=McexecListHead{next:addr_of_mut!(overlay_fd_list),prev:addr_of_mut!(overlay_fd_list)};
#[cfg(mcexec_syscall_mod_call)]
#[no_mangle]pub static mut __glob_argc:c_int=-1;
#[cfg(mcexec_syscall_mod_call)]
#[no_mangle]pub static mut __glob_argv:*mut *mut u8=null_mut();

#[no_mangle]
pub static mut mcexec_options:[GetOptOption;20+cfg!(mcexec_enable_tofu) as usize]=[
 GetOptOption{name:b"disable-vdso\0".as_ptr(),has_arg:0,flag:addr_of_mut!(enable_vdso),value:0},
 GetOptOption{name:b"enable-vdso\0".as_ptr(),has_arg:0,flag:addr_of_mut!(enable_vdso),value:1},
 GetOptOption{name:b"profile\0".as_ptr(),has_arg:0,flag:addr_of_mut!(profile),value:1},
 GetOptOption{name:b"mpol-no-heap\0".as_ptr(),has_arg:0,flag:addr_of_mut!(mpol_no_heap),value:1},
 GetOptOption{name:b"mpol-no-stack\0".as_ptr(),has_arg:0,flag:addr_of_mut!(mpol_no_stack),value:1},
 GetOptOption{name:b"mpol-no-bss\0".as_ptr(),has_arg:0,flag:addr_of_mut!(mpol_no_bss),value:1},
 GetOptOption{name:b"mpol-shm-premap\0".as_ptr(),has_arg:0,flag:addr_of_mut!(mpol_shm_premap),value:1},
 GetOptOption{name:b"no-bind-ikc-map\0".as_ptr(),has_arg:0,flag:addr_of_mut!(no_bind_ikc_map),value:1},
 GetOptOption{name:b"mpol-threshold\0".as_ptr(),has_arg:1,flag:null_mut(),value:'M' as c_int},
 GetOptOption{name:b"enable-straight-map\0".as_ptr(),has_arg:0,flag:addr_of_mut!(straight_map),value:1},
 GetOptOption{name:b"straight-map-threshold\0".as_ptr(),has_arg:1,flag:null_mut(),value:'S' as c_int},
 GetOptOption{name:b"disable-sched-yield\0".as_ptr(),has_arg:0,flag:addr_of_mut!(disable_sched_yield),value:1},
 GetOptOption{name:b"extend-heap-by\0".as_ptr(),has_arg:1,flag:null_mut(),value:'h' as c_int},
 GetOptOption{name:b"stack-premap\0".as_ptr(),has_arg:1,flag:null_mut(),value:'s' as c_int},
 GetOptOption{name:b"uti-thread-rank\0".as_ptr(),has_arg:1,flag:null_mut(),value:'u' as c_int},
 GetOptOption{name:b"uti-use-last-cpu\0".as_ptr(),has_arg:0,flag:addr_of_mut!(uti_use_last_cpu),value:1},
 GetOptOption{name:b"enable-uti\0".as_ptr(),has_arg:0,flag:addr_of_mut!(enable_uti),value:1},
 #[cfg(mcexec_enable_tofu)]
 GetOptOption{name:b"enable-tofu\0".as_ptr(),has_arg:0,flag:addr_of_mut!(enable_tofu),value:1},
 GetOptOption{name:b"debug-mcexec\0".as_ptr(),has_arg:0,flag:addr_of_mut!(debug),value:1},
 GetOptOption{name:b"flags\0".as_ptr(),has_arg:1,flag:null_mut(),value:'f' as c_int},
 GetOptOption{name:core::ptr::null(),has_arg:0,flag:null_mut(),value:0},
];

#[cfg(mcexec_data_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_data_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<MutexStorage>(),core::mem::align_of::<MutexStorage>(),core::mem::size_of::<BarrierStorage>(),core::mem::align_of::<BarrierStorage>(),core::mem::size_of::<c_int>(),core::mem::align_of::<c_int>(),core::mem::size_of::<McexecListHead>(),core::mem::align_of::<McexecListHead>(),core::mem::size_of::<GetOptOption>(),core::mem::align_of::<GetOptOption>(),core::mem::offset_of!(GetOptOption,name),core::mem::offset_of!(GetOptOption,has_arg),core::mem::offset_of!(GetOptOption,flag),core::mem::offset_of!(GetOptOption,value),core::mem::size_of::<GlobalRlimit>(),core::mem::align_of::<GlobalRlimit>()];core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
