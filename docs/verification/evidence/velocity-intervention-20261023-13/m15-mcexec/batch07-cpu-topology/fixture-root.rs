// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
mod mcexec_load_descriptor {
 use super::{c_int,c_long,c_ulong,c_void};
#[repr(C)]
pub struct Rlimit { pub rlim_cur:c_ulong, pub rlim_max:c_ulong }
#[repr(C)]
pub struct ImageSection {
 pub vaddr:c_ulong,
 pub len:c_ulong,
 pub remote_pa:c_ulong,
 pub filesz:c_ulong,
 pub offset:c_ulong,
 pub prot:c_int,
 pub interp:u8,
 pub padding:[u8;3],
 pub fp:*mut c_void,
}
#[repr(C)]
pub struct ProgramLoadDesc {
 pub magic:c_ulong,
 pub num_sections:c_int,
 pub cpu:c_int,
 pub pid:c_int,
 pub stack_prot:c_int,
 pub pgid:c_int,
 pub cred:[c_int;8],
 pub reloc:c_int,
 pub enable_vdso:i8,
 pub padding:[u8;7],
 pub entry:c_ulong,
 pub user_start:c_ulong,
 pub user_end:c_ulong,
 pub rprocess:c_ulong,
 pub rpgtable:c_ulong,
 pub at_phdr:c_ulong,
 pub at_phent:c_ulong,
 pub at_phnum:c_ulong,
 pub at_entry:c_ulong,
 pub at_clktck:c_ulong,
 pub args:*mut u8,
 pub args_len:c_ulong,
 pub envs:*mut u8,
 pub envs_len:c_ulong,
 pub rlimit:[Rlimit;20],
 pub interp_align:c_ulong,
 pub mpol_flags:c_ulong,
 pub mpol_threshold:c_ulong,
 pub heap_extension:c_ulong,
 pub stack_premap:c_long,
 pub mpol_bind_mask:c_ulong,
 pub mpol_mode:c_int,
 pub mpol_nodemask:[c_ulong;4],
 pub thp_disable:c_int,
 pub enable_uti:c_int,
 pub uti_thread_rank:c_int,
 pub uti_use_last_cpu:c_int,
 pub straight_map:c_int,
 pub straight_map_threshold:usize,
 #[cfg(mcexec_enable_tofu)]
 pub enable_tofu:c_int,
 pub mcexec_flags:c_ulong,
 pub nr_processes:c_int,
 pub process_rank:c_int,
 pub cpu_set:[c_ulong;16],
 pub profile:c_int,
 pub sections:[ImageSection;0],
}

}
unsafe extern "C" {
 #[link_name="fd"]static mut MCEXEC_FD:c_int;
 fn ioctl(fd:c_int,r:c_ulong,...)->c_int;
 fn getenv(n:*const u8)->*mut u8;
 fn strlen(p:*const u8)->usize;
 fn perror(p:*const u8);
 fn close(fd:c_int)->c_int;
}
#[path="mcexec_cpu_topology.rs"]mod mcexec_cpu_topology;
#[panic_handler]
fn panic(_: &core::panic::PanicInfo)->! {loop{}}
