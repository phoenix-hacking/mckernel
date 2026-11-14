// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Use actual crate::abi::{ProcessVm,Process} and crate::debug::Ddebug;
// no private Page type is copied or redefined.
#[used]
#[no_mangle]
pub static fixture_extend_actual_abi: [usize; 11] = [
    core::mem::size_of::<crate::abi::ProcessVm>(),
    core::mem::align_of::<crate::abi::ProcessVm>(),
    core::mem::offset_of!(crate::abi::ProcessVm,proc),
    core::mem::size_of::<crate::abi::Process>(),
    core::mem::align_of::<crate::abi::Process>(),
    core::mem::offset_of!(crate::abi::Process,mpol_flags),
    core::mem::offset_of!(crate::abi::Process,heap_extension),
    core::mem::size_of::<crate::abi::CULong>(),
    core::mem::size_of::<crate::abi::CULong>(),
    core::mem::size_of::<crate::debug::Ddebug>(),
    core::mem::align_of::<crate::debug::Ddebug>(),
];
