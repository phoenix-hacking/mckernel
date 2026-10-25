// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#[path = "../source/kernel/rust/abi.rs"]
mod abi;
#[used]
#[no_mangle]
#[link_section = ".process_debug_abi"]
pub static PROCESS_DEBUG_RUST_ABI: [usize; 29] = [
    core::mem::size_of::<abi::McsRwlockLock>(),
    core::mem::align_of::<abi::McsRwlockLock>(),
    64,
    64,
    abi::PROCESS_HASH_SIZE,
    core::mem::offset_of!(abi::CpuLocalVar, resource_set),
    core::mem::offset_of!(abi::ResourceSet, process_hash),
    core::mem::offset_of!(abi::ResourceSet, thread_hash),
    core::mem::offset_of!(abi::ResourceSet, pid1),
    core::mem::offset_of!(abi::ProcessHash, list),
    core::mem::offset_of!(abi::ProcessHash, lock),
    core::mem::offset_of!(abi::ThreadHash, list),
    core::mem::offset_of!(abi::ThreadHash, lock),
    core::mem::offset_of!(abi::Process, hash_list),
    core::mem::offset_of!(abi::Process, ppid_parent),
    core::mem::offset_of!(abi::Process, refcount),
    core::mem::offset_of!(abi::Process, status),
    core::mem::offset_of!(abi::Process, pid),
    core::mem::offset_of!(abi::Thread, hash_list),
    core::mem::offset_of!(abi::Thread, proc),
    core::mem::offset_of!(abi::Thread, cpu_id),
    core::mem::offset_of!(abi::Thread, tid),
    core::mem::offset_of!(abi::Thread, status),
    core::mem::offset_of!(abi::Thread, in_syscall_offload),
    core::mem::offset_of!(abi::Thread, refcount),
    core::mem::offset_of!(abi::Thread, ptrace),
    core::mem::offset_of!(abi::AbiListHead, next),
    core::mem::size_of::<abi::IhkAtomic>(),
    core::mem::offset_of!(abi::IhkAtomic, counter),
];
