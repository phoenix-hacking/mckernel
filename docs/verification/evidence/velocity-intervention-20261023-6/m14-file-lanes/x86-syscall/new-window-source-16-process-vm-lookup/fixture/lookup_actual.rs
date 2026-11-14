// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;
use abi::{CULong,ProcessVm,VmRange};
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
#[path="/home/holden/mckernel/kernel/rust/rbtree.rs"] mod rbtree;
mod process_helpers;
include!("../candidate/process-vm-lookup.FRAGMENT.rs");
#[no_mangle] pub extern "C" fn fixture_lookup_ABI(i:usize)->usize {use core::mem::{size_of,align_of,offset_of}; let a=[size_of::<ProcessVm>(),align_of::<ProcessVm>(),size_of::<VmRange>(),align_of::<VmRange>(),offset_of!(ProcessVm,vm_range_tree),offset_of!(ProcessVm,range_cache),offset_of!(ProcessVm,range_cache_ind),offset_of!(VmRange,vm_rb_node),offset_of!(VmRange,start),offset_of!(VmRange,end),size_of::<abi::AbiRbNode>(),abi::VM_RANGE_CACHE_SIZE];a[i]}
