#![no_std]
#![allow(dead_code)]
#[path="rust/abi.rs"] mod abi;
#[path="rust/page_helpers.rs"] mod page_helpers;
#[path="rust/llist.rs"] mod llist;
#[path="rust/rbtree.rs"] mod rbtree;
#[path="rust/string.rs"] mod string;
#[path="rust/mem_helpers.rs"] mod mem_helpers;
#[path="rust/object_helpers.rs"] mod object_helpers;
mod debug { include!("rust/actual-debug-type.inc"); }
// Unreachable boot hooks only; no tested accounting/dispatch body is replaced.
mod x86_setup { pub fn early_phase(_tag:u8) {} pub fn early_panic() { loop {} } }
#[path="rust/x86_memory_helpers.rs"] mod x86_memory_helpers;
#[no_mangle] pub extern "C" fn fixture_rusage_enabled()->i32 { cfg!(enable_rusage) as i32 }
#[no_mangle] pub extern "C" fn fixture_geometry(which:i32)->usize {
 match which {0=>core::mem::size_of::<mem_helpers::RusageGlobal>(),1=>core::mem::align_of::<mem_helpers::RusageGlobal>(),2=>core::mem::size_of::<abi::Memobj>(),3=>core::mem::size_of::<abi::MemobjOps>(),_=>0}
}
