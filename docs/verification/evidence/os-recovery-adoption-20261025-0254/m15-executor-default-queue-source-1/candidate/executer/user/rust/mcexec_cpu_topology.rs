// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Requires batch04's exact descriptor type; CPU macros now implemented in Rust.
use super::{c_int,c_ulong,c_void};
use super::mcexec_load_descriptor::ProgramLoadDesc;
use core::ptr::{addr_of_mut,read,write_bytes};
#[repr(C,align(8))]
struct StatStorage { bytes:[u8;144] }
#[repr(C)]
struct GetCpuSetArg {
 nr_processes:c_int,req_cpu_list:*mut u8,req_cpu_list_len:c_int,
 process_rank:*mut c_int,ppid:c_int,cpu_set:*mut c_void,cpu_set_size:usize,
 target_core:*mut c_int,mcexec_linux_numa:*mut c_int,mcexec_cpu_set:*mut c_void,
 mcexec_cpu_set_size:usize,ikc_mapped:*mut c_int,
}
unsafe extern "C" {
 static mut ncpu:c_int;static mut nnodes:c_int;static mut numa_nodes:*mut u8;
 static mut cpu_set_size:usize;static mut mcexec_partition_cpu_set_storage:[c_ulong;16];
 static mut debug:c_int;static mut stdout:*mut c_void;static mut stderr:*mut c_void;
 fn printf(fmt:*const u8,...)->c_int;fn fprintf(f:*mut c_void,fmt:*const u8,...)->c_int;fn fflush(f:*mut c_void)->c_int;
 fn snprintf(buf:*mut u8,size:usize,fmt:*const u8,...)->c_int;
 fn stat(path:*const u8,out:*mut StatStorage)->c_int;
 fn getppid()->c_int;
 fn sched_setaffinity(pid:c_int,size:usize,set:*const c_void)->c_int;
 fn numa_run_on_node(node:c_int)->c_int;
}
unsafe fn node_ptr(nodes:*mut u8,size:usize,node:c_int)->*mut c_ulong {
 nodes.add((node as usize).wrapping_mul(size)).cast()
}
unsafe fn cpu_isset(cpu:c_int,size:usize,set:*const c_ulong)->c_int {
 let cpu=cpu as usize;
 if cpu/8>=size {return 0;}
 ((*set.add(cpu/64)&(1u64<<(cpu%64)))!=0) as c_int
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_node_cpu_isset_bridge(node:c_int,cpu:c_int) -> c_int {
 cpu_isset(cpu,cpu_set_size,node_ptr(numa_nodes,cpu_set_size,node))
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_get_cpu_bridge() -> c_int {
 super::ioctl(super::MCEXEC_FD,0x30a02907 as c_ulong,0 as c_int)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_get_nodes_bridge() -> c_int {
 super::ioctl(super::MCEXEC_FD,0x30a0290c as c_ulong,0 as c_int)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_no_cpu_bridge() {
 fprintf(stderr,b"No CPU found.\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_no_numa_node_bridge() {
 fprintf(stderr,b"No numa node found.\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_alloc_nodes_error_bridge() {
 fprintf(stderr,b"Error allocating nodes cpu sets\n\0".as_ptr());
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_cpu_alloc_size_bridge(cpu_count:c_int) -> usize {
 (cpu_count as usize).wrapping_add(63)/64*8
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_publish_topology_bridge(cpu_count:c_int,node_count:c_int,node_set_size:usize,nodes:*mut c_void) {
 ncpu=cpu_count;nnodes=node_count;cpu_set_size=node_set_size;numa_nodes=nodes.cast();
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_numa_node_zero_bridge(nodes:*mut c_void,node_set_size:usize,node_id:c_int) {
 write_bytes(node_ptr(nodes.cast(),node_set_size,node_id).cast::<u8>(),0,node_set_size);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_node_cpu_exists_bridge(node_id:c_int,cpu:c_int) -> c_int {
 let mut buf=[0u8;4096];let mut sb:StatStorage=core::mem::zeroed();
 snprintf(buf.as_mut_ptr(),buf.len(),b"/sys/class/mcos/mcos0/sys/devices/system/node/node%d/cpu%d\0".as_ptr(),node_id,cpu);
 (stat(buf.as_ptr(),addr_of_mut!(sb))==0) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_numa_node_set_cpu_bridge(nodes:*mut c_void,node_set_size:usize,node_id:c_int,cpu:c_int) {
 let cpu=cpu as usize;
 if cpu/8<node_set_size {let word=node_ptr(nodes.cast(),node_set_size,node_id).add(cpu/64);*word|=1u64<<(cpu%64);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_cpu_in_node_bridge(cpu:c_int,node:c_int) -> c_int {
 if node<0||node>=nnodes||cpu<0||cpu>=ncpu {return 0;}
 cpu_isset(cpu,cpu_set_size,node_ptr(numa_nodes,cpu_set_size,node))
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_get_cpuset_bridge(desc:*mut ProgramLoadDesc,nr_processes:c_int,target_core:*mut c_int,process_rank:*mut c_int,mcexec_linux_numa:*mut c_int,ikc_mapped:*mut c_int) -> c_int {
 write_bytes(addr_of_mut!(mcexec_partition_cpu_set_storage).cast::<u8>(),0,128);
 let mut arg=GetCpuSetArg {nr_processes,req_cpu_list:core::ptr::null_mut(),req_cpu_list_len:0,
 process_rank,ppid:getppid(),cpu_set:addr_of_mut!((*desc).cpu_set).cast(),cpu_set_size:128,
 target_core,mcexec_linux_numa,mcexec_cpu_set:addr_of_mut!(mcexec_partition_cpu_set_storage).cast(),mcexec_cpu_set_size:128,ikc_mapped};
 if !super::getenv(b"FLIB_AFFINITY_ON_PROCESS\0".as_ptr()).is_null() {
  arg.req_cpu_list=super::getenv(b"FLIB_AFFINITY_ON_PROCESS\0".as_ptr());
  arg.req_cpu_list_len=super::strlen(arg.req_cpu_list).wrapping_add(1) as c_int;
  if debug!=0 {printf(b"mcexec_partition_get_cpuset_bridge: main: requesting CPUs: %s\n\0".as_ptr(),arg.req_cpu_list);fflush(stdout);}
 }
 super::ioctl(super::MCEXEC_FD,0x30a0290d as c_ulong,addr_of_mut!(arg))
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_get_cpuset_failed_bridge() {
 super::perror(b"getting CPU set for partitioned execution\0".as_ptr());super::close(super::MCEXEC_FD);
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_sched_setaffinity_bridge() -> c_int {
 sched_setaffinity(0,128,addr_of_mut!(mcexec_partition_cpu_set_storage).cast())
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_numa_run_bridge(node:c_int) -> c_int {
 numa_run_on_node(node)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_local_cpu_log_bridge(cpu:c_int) {
 if debug!=0 {printf(b"mcexec_numa_local_cpu_log_bridge: %d belongs to local set\n\0".as_ptr(),cpu);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_numa_node_cpu_log_bridge(cpu:c_int,node:c_int) {
 if debug!=0 {printf(b"mcexec_numa_node_cpu_log_bridge: %d belongs to node %d\n\0".as_ptr(),cpu,node);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_process_thread_plan_flib_log_bridge(count:c_int) {
 if debug!=0 {printf(b"mcexec_process_thread_plan_flib_log_bridge: main: using FLIB_NUM_PROCESS_ON_NODE: %d\n\0".as_ptr(),count);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_rank_log_bridge(rank:c_int,cpu:c_int) {
 if debug!=0 {printf(b"mcexec_partition_rank_log_bridge: main: rank: %d, target CPU: %d\n\0".as_ptr(),rank,cpu);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_sched_setaffinity_warning_bridge() {
 if debug!=0 {printf(b"mcexec_partition_sched_setaffinity_warning_bridge: WARNING: couldn't bind to mcexec_cpu_set\n\0".as_ptr());fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_numa_run_warning_bridge(node:c_int) {
 if debug!=0 {printf(b"mcexec_partition_numa_run_warning_bridge: WARNING: couldn't bind to NUMA %d\n\0".as_ptr(),node);fflush(stdout);}
}

#[cfg(mcexec_topology_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_topology_fixture_abi(out:*mut usize)->usize {
 let values=[core::mem::size_of::<StatStorage>(),core::mem::align_of::<StatStorage>(),128,8,core::mem::size_of::<GetCpuSetArg>(),core::mem::align_of::<GetCpuSetArg>(),
 core::mem::offset_of!(GetCpuSetArg,nr_processes),
 core::mem::offset_of!(GetCpuSetArg,req_cpu_list),
 core::mem::offset_of!(GetCpuSetArg,req_cpu_list_len),
 core::mem::offset_of!(GetCpuSetArg,process_rank),
 core::mem::offset_of!(GetCpuSetArg,ppid),
 core::mem::offset_of!(GetCpuSetArg,cpu_set),
 core::mem::offset_of!(GetCpuSetArg,cpu_set_size),
 core::mem::offset_of!(GetCpuSetArg,target_core),
 core::mem::offset_of!(GetCpuSetArg,mcexec_linux_numa),
 core::mem::offset_of!(GetCpuSetArg,mcexec_cpu_set),
 core::mem::offset_of!(GetCpuSetArg,mcexec_cpu_set_size),
 core::mem::offset_of!(GetCpuSetArg,ikc_mapped),
 ];core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());values.len()
}
