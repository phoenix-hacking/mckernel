// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact three existing VDSO storage objects; no constructor or synchronization change.
use crate::abi::SizeT;
use crate::syscall_policy::ArchVdso;

// SAFETY: the pinned repr(C) ArchVdso contains only signed integers, i8 fields,
// integer arrays and raw pointers. Every field permits all-zero initialization,
// including null raw pointers; no reference, NonNull, enum or drop owner exists.
// This preserves the complete zero initialization of the former C static object.
// Callers retain their original raw-pointer publication and exclusion contract.
#[export_name = "mckernel_f06_vdso_state"]
pub static mut VDSO_STATE: ArchVdso = unsafe { core::mem::zeroed() };

#[export_name = "mckernel_f06_vdso_container_size"]
pub static mut CONTAINER_SIZE: SizeT = 0;

#[export_name = "mckernel_f06_vdso_offset"]
pub static mut VDSO_OFFSET: isize = 0;
