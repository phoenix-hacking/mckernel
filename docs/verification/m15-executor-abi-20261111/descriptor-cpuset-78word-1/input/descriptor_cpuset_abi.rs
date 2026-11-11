// Source-only ABI data witness; no main, callbacks, allocation or native operation.
#![no_std]
use core::ffi::{c_int,c_long,c_ulong,c_void};
#[cfg(mcexec_enable_tofu)]
compile_error!("This witness is bound only to the qualified ENABLE_TOFU=OFF profile");
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

#[repr(C)]
struct GetCpuSetArg {
 nr_processes:c_int,req_cpu_list:*mut u8,req_cpu_list_len:c_int,
 process_rank:*mut c_int,ppid:c_int,cpu_set:*mut c_void,cpu_set_size:usize,
 target_core:*mut c_int,mcexec_linux_numa:*mut c_int,mcexec_cpu_set:*mut c_void,
 mcexec_cpu_set_size:usize,ikc_mapped:*mut c_int,
}

#[used]
#[no_mangle]
pub static m15_f02_descriptor_cpuset_abi: [u64; 78] = [
    1, // 0 witness_version
    core::mem::size_of::<c_ulong>() as u64, // 1 sizeof(unsigned long)
    core::mem::size_of::<c_int>() as u64, // 2 sizeof(int)
    core::mem::size_of::<c_int>() as u64, // 3 sizeof(pid_t)
    core::mem::size_of::<usize>() as u64, // 4 sizeof(size_t)
    core::mem::size_of::<*mut c_void>() as u64, // 5 sizeof(void*)
    core::mem::size_of::<ProgramLoadDesc>() as u64, // 6 sizeof(program_load_desc)
    core::mem::align_of::<ProgramLoadDesc>() as u64, // 7 alignof(program_load_desc)
    core::mem::offset_of!(ProgramLoadDesc, magic) as u64, // 8 program_load_desc::magic
    core::mem::offset_of!(ProgramLoadDesc, num_sections) as u64, // 9 program_load_desc::num_sections
    core::mem::offset_of!(ProgramLoadDesc, cpu) as u64, // 10 program_load_desc::cpu
    core::mem::offset_of!(ProgramLoadDesc, pid) as u64, // 11 program_load_desc::pid
    core::mem::offset_of!(ProgramLoadDesc, stack_prot) as u64, // 12 program_load_desc::stack_prot
    core::mem::offset_of!(ProgramLoadDesc, pgid) as u64, // 13 program_load_desc::pgid
    core::mem::offset_of!(ProgramLoadDesc, cred) as u64, // 14 program_load_desc::cred
    core::mem::offset_of!(ProgramLoadDesc, reloc) as u64, // 15 program_load_desc::reloc
    core::mem::offset_of!(ProgramLoadDesc, enable_vdso) as u64, // 16 program_load_desc::enable_vdso
    core::mem::offset_of!(ProgramLoadDesc, padding) as u64, // 17 program_load_desc::padding
    core::mem::offset_of!(ProgramLoadDesc, entry) as u64, // 18 program_load_desc::entry
    core::mem::offset_of!(ProgramLoadDesc, user_start) as u64, // 19 program_load_desc::user_start
    core::mem::offset_of!(ProgramLoadDesc, user_end) as u64, // 20 program_load_desc::user_end
    core::mem::offset_of!(ProgramLoadDesc, rprocess) as u64, // 21 program_load_desc::rprocess
    core::mem::offset_of!(ProgramLoadDesc, rpgtable) as u64, // 22 program_load_desc::rpgtable
    core::mem::offset_of!(ProgramLoadDesc, at_phdr) as u64, // 23 program_load_desc::at_phdr
    core::mem::offset_of!(ProgramLoadDesc, at_phent) as u64, // 24 program_load_desc::at_phent
    core::mem::offset_of!(ProgramLoadDesc, at_phnum) as u64, // 25 program_load_desc::at_phnum
    core::mem::offset_of!(ProgramLoadDesc, at_entry) as u64, // 26 program_load_desc::at_entry
    core::mem::offset_of!(ProgramLoadDesc, at_clktck) as u64, // 27 program_load_desc::at_clktck
    core::mem::offset_of!(ProgramLoadDesc, args) as u64, // 28 program_load_desc::args
    core::mem::offset_of!(ProgramLoadDesc, args_len) as u64, // 29 program_load_desc::args_len
    core::mem::offset_of!(ProgramLoadDesc, envs) as u64, // 30 program_load_desc::envs
    core::mem::offset_of!(ProgramLoadDesc, envs_len) as u64, // 31 program_load_desc::envs_len
    core::mem::offset_of!(ProgramLoadDesc, rlimit) as u64, // 32 program_load_desc::rlimit
    core::mem::offset_of!(ProgramLoadDesc, interp_align) as u64, // 33 program_load_desc::interp_align
    core::mem::offset_of!(ProgramLoadDesc, mpol_flags) as u64, // 34 program_load_desc::mpol_flags
    core::mem::offset_of!(ProgramLoadDesc, mpol_threshold) as u64, // 35 program_load_desc::mpol_threshold
    core::mem::offset_of!(ProgramLoadDesc, heap_extension) as u64, // 36 program_load_desc::heap_extension
    core::mem::offset_of!(ProgramLoadDesc, stack_premap) as u64, // 37 program_load_desc::stack_premap
    core::mem::offset_of!(ProgramLoadDesc, mpol_bind_mask) as u64, // 38 program_load_desc::mpol_bind_mask
    core::mem::offset_of!(ProgramLoadDesc, mpol_mode) as u64, // 39 program_load_desc::mpol_mode
    core::mem::offset_of!(ProgramLoadDesc, mpol_nodemask) as u64, // 40 program_load_desc::mpol_nodemask
    core::mem::offset_of!(ProgramLoadDesc, thp_disable) as u64, // 41 program_load_desc::thp_disable
    core::mem::offset_of!(ProgramLoadDesc, enable_uti) as u64, // 42 program_load_desc::enable_uti
    core::mem::offset_of!(ProgramLoadDesc, uti_thread_rank) as u64, // 43 program_load_desc::uti_thread_rank
    core::mem::offset_of!(ProgramLoadDesc, uti_use_last_cpu) as u64, // 44 program_load_desc::uti_use_last_cpu
    core::mem::offset_of!(ProgramLoadDesc, straight_map) as u64, // 45 program_load_desc::straight_map
    core::mem::offset_of!(ProgramLoadDesc, straight_map_threshold) as u64, // 46 program_load_desc::straight_map_threshold
    core::mem::offset_of!(ProgramLoadDesc, mcexec_flags) as u64, // 47 program_load_desc::mcexec_flags
    core::mem::offset_of!(ProgramLoadDesc, nr_processes) as u64, // 48 program_load_desc::nr_processes
    core::mem::offset_of!(ProgramLoadDesc, process_rank) as u64, // 49 program_load_desc::process_rank
    core::mem::offset_of!(ProgramLoadDesc, cpu_set) as u64, // 50 program_load_desc::cpu_set
    core::mem::offset_of!(ProgramLoadDesc, profile) as u64, // 51 program_load_desc::profile
    core::mem::offset_of!(ProgramLoadDesc, sections) as u64, // 52 program_load_desc::sections
    core::mem::size_of::<ImageSection>() as u64, // 53 sizeof(program_image_section)
    core::mem::align_of::<ImageSection>() as u64, // 54 alignof(program_image_section)
    core::mem::offset_of!(ImageSection, vaddr) as u64, // 55 program_image_section::vaddr
    core::mem::offset_of!(ImageSection, len) as u64, // 56 program_image_section::len
    core::mem::offset_of!(ImageSection, remote_pa) as u64, // 57 program_image_section::remote_pa
    core::mem::offset_of!(ImageSection, filesz) as u64, // 58 program_image_section::filesz
    core::mem::offset_of!(ImageSection, offset) as u64, // 59 program_image_section::offset
    core::mem::offset_of!(ImageSection, prot) as u64, // 60 program_image_section::prot
    core::mem::offset_of!(ImageSection, interp) as u64, // 61 program_image_section::interp
    core::mem::offset_of!(ImageSection, padding) as u64, // 62 program_image_section::padding
    core::mem::offset_of!(ImageSection, fp) as u64, // 63 program_image_section::fp
    core::mem::size_of::<GetCpuSetArg>() as u64, // 64 sizeof(get_cpu_set_arg)
    core::mem::align_of::<GetCpuSetArg>() as u64, // 65 alignof(get_cpu_set_arg)
    core::mem::offset_of!(GetCpuSetArg, nr_processes) as u64, // 66 get_cpu_set_arg::nr_processes
    core::mem::offset_of!(GetCpuSetArg, req_cpu_list) as u64, // 67 get_cpu_set_arg::req_cpu_list
    core::mem::offset_of!(GetCpuSetArg, req_cpu_list_len) as u64, // 68 get_cpu_set_arg::req_cpu_list_len
    core::mem::offset_of!(GetCpuSetArg, process_rank) as u64, // 69 get_cpu_set_arg::process_rank
    core::mem::offset_of!(GetCpuSetArg, ppid) as u64, // 70 get_cpu_set_arg::ppid
    core::mem::offset_of!(GetCpuSetArg, cpu_set) as u64, // 71 get_cpu_set_arg::cpu_set
    core::mem::offset_of!(GetCpuSetArg, cpu_set_size) as u64, // 72 get_cpu_set_arg::cpu_set_size
    core::mem::offset_of!(GetCpuSetArg, target_core) as u64, // 73 get_cpu_set_arg::target_core
    core::mem::offset_of!(GetCpuSetArg, mcexec_linux_numa) as u64, // 74 get_cpu_set_arg::mcexec_linux_numa
    core::mem::offset_of!(GetCpuSetArg, mcexec_cpu_set) as u64, // 75 get_cpu_set_arg::mcexec_cpu_set
    core::mem::offset_of!(GetCpuSetArg, mcexec_cpu_set_size) as u64, // 76 get_cpu_set_arg::mcexec_cpu_set_size
    core::mem::offset_of!(GetCpuSetArg, ikc_mapped) as u64, // 77 get_cpu_set_arg::ikc_mapped
];
