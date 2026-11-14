// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
const _:()={assert!(core::mem::size_of::<core::ffi::c_ulong>()==8);assert!(core::mem::size_of::<usize>()==8);};
// Exact uprotocol.h selected Linux x86_64 ABI; fixture compares every field offset.
use super::{c_int,c_long,c_ulong,c_void};
use core::ptr::addr_of_mut;
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
unsafe extern "C" {
 static mut debug:c_int;
 static mut stdout:*mut c_void;
 fn printf(fmt:*const u8,...)->c_int;
 fn fflush(f:*mut c_void)->c_int;
 fn getrlimit(resource:c_int,limit:*mut Rlimit)->c_int;
 fn numa_parse_nodestring_all(nodes:*const u8)->*mut c_void;
 fn numa_max_possible_node()->c_int;
 fn numa_bitmask_isbitset(mask:*const c_void,node:u32)->c_int;
}
unsafe fn section(d:*mut ProgramLoadDesc,index:c_int)->*mut ImageSection {
 addr_of_mut!((*d).sections).cast::<ImageSection>().offset(index as isize)
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_load_alloc_desc_bridge(nsections:c_int) -> *mut ProgramLoadDesc {
 let size=core::mem::size_of::<ProgramLoadDesc>().wrapping_add(core::mem::size_of::<ImageSection>().wrapping_mul(nsections as usize));
 let desc=super::malloc(size).cast::<ProgramLoadDesc>();
 if desc.is_null() { return desc; }
 core::ptr::write_bytes(desc.cast::<u8>(),0,size);
 (*desc).magic=0xcafecafe44332211;
 (*desc).num_sections=nsections;
 (*desc).stack_prot=7;
 desc
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_publish_main_section_bridge(desc:*mut ProgramLoadDesc,index:c_int,vaddr:c_ulong,filesz:c_ulong,offset:c_ulong,len:c_ulong,prot:c_int,fp:*mut c_void) {
 let s=section(desc,index);
 (*s).vaddr=vaddr;(*s).filesz=filesz;(*s).offset=offset;(*s).len=len;(*s).interp=0;(*s).fp=fp;(*s).prot=prot;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_publish_interp_section_bridge(desc:*mut ProgramLoadDesc,index:c_int,vaddr:c_ulong,filesz:c_ulong,offset:c_ulong,len:c_ulong,prot:c_int,fp:*mut c_void) {
 let s=section(desc,index);
 (*s).vaddr=vaddr;(*s).filesz=filesz;(*s).offset=offset;(*s).len=len;(*s).interp=1;(*s).fp=fp;(*s).prot=prot;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_cred_bridge(desc:*mut ProgramLoadDesc) -> *mut c_int {
 addr_of_mut!((*desc).cred).cast()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_clk_tck_bridge() -> c_long {
 super::sysconf(2) // _SC_CLK_TCK on pinned Linux glibc.
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_load_finalize_desc_bridge(desc:*mut ProgramLoadDesc,pid:c_int,pgid:c_int,reloc:c_int,entry:c_ulong,at_phdr:c_ulong,at_phent:c_ulong,at_phnum:c_ulong,at_entry:c_ulong,at_clktck:c_ulong,stack_prot:c_int) {
 (*desc).pid=pid;
 (*desc).pgid=pgid;
 (*desc).reloc=reloc;
 (*desc).entry=entry;
 (*desc).at_phdr=at_phdr;
 (*desc).at_phent=at_phent;
 (*desc).at_phnum=at_phnum;
 (*desc).at_entry=at_entry;
 (*desc).at_clktck=at_clktck;
 (*desc).stack_prot=stack_prot;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_program_load_desc_size_bridge() -> usize {
 core::mem::size_of::<ProgramLoadDesc>()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_program_image_section_size_bridge() -> usize {
 core::mem::size_of::<ImageSection>()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_set_num_sections_bridge(desc:*mut ProgramLoadDesc,value:c_int) {
 (*desc).num_sections=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_set_entry_bridge(desc:*mut ProgramLoadDesc,value:c_ulong) {
 (*desc).entry=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_set_interp_align_bridge(desc:*mut ProgramLoadDesc,value:c_ulong) {
 (*desc).interp_align=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_set_args_len_bridge(desc:*mut ProgramLoadDesc,value:c_ulong) {
 (*desc).args_len=value;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_num_sections_bridge(desc:*const ProgramLoadDesc) -> c_int {
 (*desc).num_sections
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_cpu_bridge(desc:*const ProgramLoadDesc) -> c_int {
 (*desc).cpu
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_pid_bridge(desc:*const ProgramLoadDesc) -> c_int {
 (*desc).pid
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_entry_bridge(desc:*const ProgramLoadDesc) -> c_ulong {
 (*desc).entry
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_rprocess_bridge(desc:*const ProgramLoadDesc) -> c_ulong {
 (*desc).rprocess
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_vaddr_bridge(desc:*const ProgramLoadDesc,index:c_int) -> c_ulong {
 (*section(desc.cast_mut(),index)).vaddr
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_len_bridge(desc:*const ProgramLoadDesc,index:c_int) -> c_ulong {
 (*section(desc.cast_mut(),index)).len
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_remote_pa_bridge(desc:*const ProgramLoadDesc,index:c_int) -> c_ulong {
 (*section(desc.cast_mut(),index)).remote_pa
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_filesz_bridge(desc:*const ProgramLoadDesc,index:c_int) -> c_ulong {
 (*section(desc.cast_mut(),index)).filesz
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_offset_bridge(desc:*const ProgramLoadDesc,index:c_int) -> c_ulong {
 (*section(desc.cast_mut(),index)).offset
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_section_fp_bridge(desc:*const ProgramLoadDesc,index:c_int) -> *mut c_void {
 (*section(desc.cast_mut(),index)).fp
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_publish_cpu_rank_bridge(desc:*mut ProgramLoadDesc,target_core:c_int,process_rank:c_int) {
 (*desc).cpu=target_core;(*desc).process_rank=process_rank;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_partition_publish_rank_bridge(desc:*mut ProgramLoadDesc,process_rank:c_int) {
 (*desc).process_rank=process_rank;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_publish_mpol_base_bridge(desc:*mut ProgramLoadDesc,profile:c_int,nr_processes:c_int,flags:c_ulong,threshold:c_ulong,heap_ext:c_ulong,pld_mpol_max:c_int) {
 (*desc).profile=profile;(*desc).nr_processes=nr_processes;(*desc).mpol_flags=flags;(*desc).mpol_threshold=threshold;
 (*desc).heap_extension=heap_ext;(*desc).mpol_bind_mask=0;(*desc).mpol_mode=pld_mpol_max;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_apply_bind_nodes_bridge(desc:*mut ProgramLoadDesc,nodes:*const u8) {
 let mask=numa_parse_nodestring_all(nodes);
 if !mask.is_null() {
   let mut node:c_int=0;
   while node<=numa_max_possible_node() {
     if numa_bitmask_isbitset(mask,node as u32)!=0 {
       // C 1UL<<node is defined only for node<64. Wrapping is an explicit
       // extension outside that reference domain, not C parity evidence.
       (*desc).mpol_bind_mask |= 1u64.wrapping_shl(node as u32);
     }
     node=node.wrapping_add(1);
   }
 } // Reference retains mask allocation; no silent ownership policy change.
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_apply_ompi_policy_bridge(desc:*mut ProgramLoadDesc,mode:c_int,nodemask_action:c_int) {
 (*desc).mpol_mode=mode;
 if nodemask_action==1 || nodemask_action==2 {
   super::mcexec_numa_local_body(addr_of_mut!((*desc).cpu_set).cast(),addr_of_mut!((*desc).mpol_nodemask).cast(),(nodemask_action==2) as c_int);
 } else if nodemask_action==3 { super::mcexec_numa_all_body(addr_of_mut!((*desc).mpol_nodemask).cast()); }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_publish_runtime_flags_bridge(desc:*mut ProgramLoadDesc,enable_uti:c_int,uti_thread_rank:c_int,uti_use_last_cpu:c_int,thp_disable:c_int,straight_map:c_int,straight_map_threshold:c_ulong,enable_tofu:c_int,mcexec_flags:c_ulong) {
 (*desc).enable_uti=enable_uti;(*desc).uti_thread_rank=uti_thread_rank;(*desc).uti_use_last_cpu=uti_use_last_cpu;(*desc).thp_disable=thp_disable;
 (*desc).straight_map=straight_map;(*desc).straight_map_threshold=straight_map_threshold as usize;
 #[cfg(mcexec_enable_tofu)] { (*desc).enable_tofu=enable_tofu; }
 #[cfg(not(mcexec_enable_tofu))] { let _=enable_tofu; }
 if mcexec_flags!=0 { (*desc).mcexec_flags=mcexec_flags; }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_set_execve1_runtime_bridge(desc:*mut ProgramLoadDesc,vdso:c_int,rlim_cur:c_ulong,rlim_max:c_ulong,prem:c_long) {
 (*desc).enable_vdso=vdso as i8;
 // Original execve uses host RLIMIT_STACK=3, distinct from main MCK index15.
 (*desc).rlimit[3].rlim_cur=rlim_cur;(*desc).rlimit[3].rlim_max=rlim_max;(*desc).stack_premap=prem;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_main_stack_publish_bridge(desc:*mut ProgramLoadDesc,cur:c_ulong,max:c_ulong,prem:c_long) {
 (*desc).rlimit[15].rlim_cur=cur;(*desc).rlimit[15].rlim_max=max;(*desc).stack_premap=prem;
 if debug!=0 { printf(b"mcexec_main_stack_publish_bridge: desc->rlimit[MCK_RLIMIT_STACK]=%ld,%ld\n\0".as_ptr(),cur,max);fflush(stdout); }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_snapshot_rlimits_bridge(desc:*mut ProgramLoadDesc) {
 // (host resource, McKernel slot), all defined in selected Linux glibc headers.
 let resources=[9,4,0,2,1,10,8,12,13,7,6,5,14,15,11,3];
 for (slot,resource) in resources.into_iter().enumerate() { getrlimit(resource,addr_of_mut!((*desc).rlimit[slot])); }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_publish_env_bridge(desc:*mut ProgramLoadDesc,envs_len:c_int,envs:*mut u8) {
 (*desc).envs_len=envs_len as c_ulong;(*desc).envs=envs;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_publish_args_cpu_bridge(desc:*mut ProgramLoadDesc,args_len:c_ulong,args:*mut u8,cpu:c_int,vdso:c_int) {
 (*desc).args_len=args_len;(*desc).args=args;(*desc).cpu=cpu;(*desc).enable_vdso=vdso as i8;
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_clear_flags_bridge(desc:*mut ProgramLoadDesc) {
 (*desc).mcexec_flags=0;
}

#[cfg(mcexec_desc_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_desc_fixture_abi(out:*mut usize)->usize {
 let values=[core::mem::size_of::<ProgramLoadDesc>(),core::mem::align_of::<ProgramLoadDesc>(),core::mem::size_of::<ImageSection>(),core::mem::align_of::<ImageSection>(),
 core::mem::offset_of!(ProgramLoadDesc,magic),
 core::mem::offset_of!(ProgramLoadDesc,num_sections),
 core::mem::offset_of!(ProgramLoadDesc,cpu),
 core::mem::offset_of!(ProgramLoadDesc,pid),
 core::mem::offset_of!(ProgramLoadDesc,stack_prot),
 core::mem::offset_of!(ProgramLoadDesc,pgid),
 core::mem::offset_of!(ProgramLoadDesc,cred),
 core::mem::offset_of!(ProgramLoadDesc,reloc),
 core::mem::offset_of!(ProgramLoadDesc,enable_vdso),
 core::mem::offset_of!(ProgramLoadDesc,padding),
 core::mem::offset_of!(ProgramLoadDesc,entry),
 core::mem::offset_of!(ProgramLoadDesc,user_start),
 core::mem::offset_of!(ProgramLoadDesc,user_end),
 core::mem::offset_of!(ProgramLoadDesc,rprocess),
 core::mem::offset_of!(ProgramLoadDesc,rpgtable),
 core::mem::offset_of!(ProgramLoadDesc,at_phdr),
 core::mem::offset_of!(ProgramLoadDesc,at_phent),
 core::mem::offset_of!(ProgramLoadDesc,at_phnum),
 core::mem::offset_of!(ProgramLoadDesc,at_entry),
 core::mem::offset_of!(ProgramLoadDesc,at_clktck),
 core::mem::offset_of!(ProgramLoadDesc,args),
 core::mem::offset_of!(ProgramLoadDesc,args_len),
 core::mem::offset_of!(ProgramLoadDesc,envs),
 core::mem::offset_of!(ProgramLoadDesc,envs_len),
 core::mem::offset_of!(ProgramLoadDesc,rlimit),
 core::mem::offset_of!(ProgramLoadDesc,interp_align),
 core::mem::offset_of!(ProgramLoadDesc,mpol_flags),
 core::mem::offset_of!(ProgramLoadDesc,mpol_threshold),
 core::mem::offset_of!(ProgramLoadDesc,heap_extension),
 core::mem::offset_of!(ProgramLoadDesc,stack_premap),
 core::mem::offset_of!(ProgramLoadDesc,mpol_bind_mask),
 core::mem::offset_of!(ProgramLoadDesc,mpol_mode),
 core::mem::offset_of!(ProgramLoadDesc,mpol_nodemask),
 core::mem::offset_of!(ProgramLoadDesc,thp_disable),
 core::mem::offset_of!(ProgramLoadDesc,enable_uti),
 core::mem::offset_of!(ProgramLoadDesc,uti_thread_rank),
 core::mem::offset_of!(ProgramLoadDesc,uti_use_last_cpu),
 core::mem::offset_of!(ProgramLoadDesc,straight_map),
 core::mem::offset_of!(ProgramLoadDesc,straight_map_threshold),
 #[cfg(mcexec_enable_tofu)]
 core::mem::offset_of!(ProgramLoadDesc,enable_tofu),
 core::mem::offset_of!(ProgramLoadDesc,mcexec_flags),
 core::mem::offset_of!(ProgramLoadDesc,nr_processes),
 core::mem::offset_of!(ProgramLoadDesc,process_rank),
 core::mem::offset_of!(ProgramLoadDesc,cpu_set),
 core::mem::offset_of!(ProgramLoadDesc,profile),
 core::mem::offset_of!(ProgramLoadDesc,sections),
 core::mem::offset_of!(ImageSection,vaddr),
 core::mem::offset_of!(ImageSection,len),
 core::mem::offset_of!(ImageSection,remote_pa),
 core::mem::offset_of!(ImageSection,filesz),
 core::mem::offset_of!(ImageSection,offset),
 core::mem::offset_of!(ImageSection,prot),
 core::mem::offset_of!(ImageSection,interp),
 core::mem::offset_of!(ImageSection,padding),
 core::mem::offset_of!(ImageSection,fp),
 ];
 core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());values.len()
}
