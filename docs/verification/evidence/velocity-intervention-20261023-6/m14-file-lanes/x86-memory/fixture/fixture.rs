#![no_std]
#![allow(dead_code)]
#[path = "../sourcehandoff/baseline/abi.rs"] mod abi;
#[path = "../sourcehandoff/baseline/page_helpers.rs"] mod page_helpers;
// Exact production Ddebug layout used by unrelated retained module statics;
// the selected L2 callback has no debug descriptor or conditional flag.
mod debug {
    #[repr(C)]
    pub struct Ddebug { pub file: *const i8, pub func: *const i8,
                        pub fmt: *const i8, pub line_flags: u32 }
}
#[path = "../candidate/kernel/rust/x86_memory_helpers.rs"] mod x86_memory_helpers;
// Unreachable boot diagnostics outside this hosted L2 callback call graph.
mod x86_setup { pub fn early_phase(_tag: u8) {} pub fn early_panic() { loop {} } }
