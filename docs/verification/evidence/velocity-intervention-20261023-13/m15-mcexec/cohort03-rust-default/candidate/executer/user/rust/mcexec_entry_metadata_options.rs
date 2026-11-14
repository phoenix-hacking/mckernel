// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use super::{c_int,c_ulong,c_void};
use core::ptr::addr_of_mut;
include!(env!("MCEXEC_BUILDID_RS"));
static mut QUERY_RESULT:[u8;BUILD_ID.len()]=[0;BUILD_ID.len()];
#[repr(C)]struct UnshareDesc {flags:c_ulong}
#[repr(C)]struct MountDesc {dev:*const u8,dir:*const u8,kind:*const u8,flags:c_ulong,data:*mut c_void}
unsafe extern "C" {
 static mut debug:c_int;static mut stdout:*mut c_void;static mut stderr:*mut c_void;
 static mut mcexec_partition_cpu_set_storage:[c_ulong;16];
 fn printf(fmt:*const u8,...)->c_int;fn fprintf(f:*mut c_void,fmt:*const u8,...)->c_int;fn fflush(f:*mut c_void)->c_int;
 #[cfg(mcexec_syscall_mod_call)]fn mc_cmd_server_init()->c_int;
 #[cfg(mcexec_syscall_mod_call)]fn mc_cmd_server_exit();
 #[cfg(all(mcexec_syscall_mod_call,mcexec_cmd_dcfa))]fn ibmic_cmd_server_init()->c_int;
 #[cfg(all(mcexec_syscall_mod_call,mcexec_cmd_dcfa))]fn ibmic_cmd_server_exit();
 #[cfg(all(mcexec_syscall_mod_call,mcexec_cmd_dcfampi))]fn dcfampi_cmd_server_init()->c_int;
 #[cfg(all(mcexec_syscall_mod_call,mcexec_cmd_dcfampi))]fn dcfampi_cmd_server_exit();
 #[cfg(mcexec_bind_mount)]fn isunshare()->c_int;
 #[cfg(mcexec_bind_mount)]fn strerror(error:c_int)->*const u8;
 #[cfg(mcexec_debug)]fn numa_num_possible_cpus()->c_int;
 #[cfg(mcexec_debug)]fn sched_getaffinity(pid:c_int,n:usize,set:*mut c_void)->c_int;
 #[cfg(mcexec_debug)]fn exit(code:c_int)->!;
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_buildid_size_bridge()->usize {BUILD_ID.len()}
#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_buildid_bridge()->*const u8 {BUILD_ID.as_ptr()}
#[no_mangle]
pub unsafe extern "C" fn mcexec_opendev_query_result_bridge()->*mut u8 {
 let result=addr_of_mut!(QUERY_RESULT).cast::<u8>();core::ptr::write_bytes(result,0,BUILD_ID.len());result
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_exit_cmd_servers_bridge() {
 #[cfg(mcexec_syscall_mod_call)] {
  #[cfg(mcexec_cmd_dcfa)] {ibmic_cmd_server_exit();}
  #[cfg(mcexec_cmd_dcfampi)] {dcfampi_cmd_server_exit();}
  mc_cmd_server_exit();if debug!=0 {printf(b"mcexec_exit_cmd_servers_bridge: mccmd server exited\n\0".as_ptr());fflush(stdout);}
 }
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_main_cmd_servers_init_bridge()->c_int {
 #[cfg(mcexec_syscall_mod_call)] {
  if mc_cmd_server_init()!=0 {fprintf(stderr,b"Error: cmd server init failed\n\0".as_ptr());return 1;}
  #[cfg(mcexec_cmd_dcfa)] {if ibmic_cmd_server_init()!=0 {fprintf(stderr,b"Error: Failed to initialize ibmic_cmd_server.\n\0".as_ptr());return -1;}}
  #[cfg(mcexec_cmd_dcfampi)] {if dcfampi_cmd_server_init()!=0 {fprintf(stderr,b"Error: Failed to initialize dcfampi_cmd_server.\n\0".as_ptr());return -1;}}
  if debug!=0 {printf(b"mcexec_main_cmd_servers_init_bridge: mccmd server initialized\n\0".as_ptr());fflush(stdout);}
 }0
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_main_bind_mount_bridge()->c_int {
 #[cfg(mcexec_bind_mount)] {
  let error=isunshare();
  if error==0 {
   let unshare=UnshareDesc {flags:0x20000};
   if super::ioctl(super::MCEXEC_FD,MCEXEC_SYS_UNSHARE,&unshare as *const UnshareDesc as c_ulong)!=0 {
    fprintf(stderr,b"Error: Failed to unshare. (%s)\n\0".as_ptr(),strerror(*super::__errno_location()));return 1;
   }
   let mount=MountDesc {dev:core::ptr::null(),dir:b"/\0".as_ptr(),kind:core::ptr::null(),flags:0x40000|0x4000,data:core::ptr::null_mut()};
   if super::ioctl(super::MCEXEC_FD,MCEXEC_SYS_MOUNT,&mount as *const MountDesc as c_ulong)!=0 {
    fprintf(stderr,b"Error: Failed to privatize mounts. (%s)\n\0".as_ptr(),strerror(*super::__errno_location()));return 1;
   }
  } else if error == -1 {return 1;}
 }0
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_debug_ikc_binding_bridge() {
 #[cfg(mcexec_debug)] {
  let mut i=0;
  while i<numa_num_possible_cpus() {
   if i>=0&&i<1024&&mcexec_partition_cpu_set_storage[i as usize/64]&(1u64<<(i%64))!=0 {
    if debug!=0 {printf(b"mcexec_partition_debug_ikc_binding_bridge: PID %d bound to CPU %d\n\0".as_ptr(),super::getpid(),i);fflush(stdout);}
   }i+=1;
  }
 }
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_debug_numa_binding_bridge() {
 #[cfg(mcexec_debug)] {
  let mut cpuset=[0u64;16];let mut affinity=[0u8;8192];let mut used=0;
  if sched_getaffinity(0,128,cpuset.as_mut_ptr().cast())!=0 {super::perror(b"Error sched_getaffinity\0".as_ptr());exit(1);}
  for i in 0..512 {
   if cpuset[i/64]&(1u64<<(i%64))!=0 {
    affinity[used]=b' ';used+=1;used+=super::write_i32_decimal(affinity.as_mut_ptr().add(used),i as c_int);affinity[used]=0;
   }
  }
  if debug!=0 {printf(b"mcexec_partition_debug_numa_binding_bridge: PID: %d affinity: %s\n\0".as_ptr(),super::getpid(),affinity.as_ptr());fflush(stdout);}
 }
}
#[cfg(not(mcexec_entry_fixture))]
#[no_mangle]
pub unsafe extern "C" fn main(argc:c_int,argv:*mut *mut u8)->c_int {super::mcexec_main_body(argc,argv)}
#[cfg(mcexec_entry_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_main_entry_fixture(argc:c_int,argv:*mut *mut u8)->c_int {super::mcexec_main_body(argc,argv)}

#[cfg(mcexec_bind_mount)]
const MCEXEC_SYS_UNSHARE:c_ulong=0x30a02916;

#[cfg(mcexec_bind_mount)]
const MCEXEC_SYS_MOUNT:c_ulong=0x30a02914;

#[cfg(mcexec_entry_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_entry_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<UnshareDesc>(),core::mem::align_of::<UnshareDesc>(),core::mem::size_of::<MountDesc>(),core::mem::align_of::<MountDesc>(),core::mem::offset_of!(MountDesc,dev),core::mem::offset_of!(MountDesc,dir),core::mem::offset_of!(MountDesc,kind),core::mem::offset_of!(MountDesc,flags),core::mem::offset_of!(MountDesc,data)];core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
