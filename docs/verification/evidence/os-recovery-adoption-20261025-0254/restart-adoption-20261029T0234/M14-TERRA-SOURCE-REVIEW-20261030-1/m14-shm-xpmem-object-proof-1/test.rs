use core::ffi::c_void;
type CInt=i32;
const MAP_SHARED:i32=1; const MAP_ANONYMOUS:i32=0x20;
const MF_SHM:i32=0x40000; const MF_SHMDT_OK:i32=0x2; const MF_IS_REMOVABLE:i32=0x4; const MF_XPMEM:u32=0x10000;
#[repr(C)] struct Memobj { flags:u32 }
#[repr(C)] struct VmRange { memobj:*mut c_void }
include!("actual-bodies.rs");
#[test] fn unindexed_mark_preserves_absence_of_shmdt() {
 let mut o=Memobj{flags:shmobj_initial_flags_result() as u32};
 let mut r=VmRange{memobj:(&mut o as *mut Memobj).cast()};
 unsafe {process_add_range_mark_xpmem_bridge(&mut r)};
 assert_eq!(o.flags,0x50000); assert_eq!(o.flags & MF_SHMDT_OK as u32,0);
}
#[test] fn indexed_object_mark_retains_both_bits_if_given() {
 let mut o=Memobj{flags:shmobj_indexed_flags_result(shmobj_initial_flags_result()) as u32};
 let mut r=VmRange{memobj:(&mut o as *mut Memobj).cast()};
 unsafe {process_add_range_mark_xpmem_bridge(&mut r)};
 assert_eq!(o.flags,0x50006);
}

#[test] fn xpmem_flags_choose_shared_branch() { assert_eq!(mmap_is_shared(MAP_SHARED|MAP_ANONYMOUS),1); assert_eq!(mmap_is_shared(MAP_ANONYMOUS),0); }
