// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact candidate entry+actual ABI types. Callee is an explicit recorder stub;
// no target TLB/IRQ implementation is executed.
#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm};
unsafe extern "C" {
    fn remote_flush_tlb_array_cpumask(
        vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
    );
}
/// Preserve the original single-address stack-local handoff to the array entry.
///
/// # Safety
/// The caller retains vm under the original TLB contract. The initialized local
/// lives through the synchronous array call, just as the C unsigned-long local
/// did. The existing array/body completion and lock protocol must finish every
/// use before this local expires. This entry does not dereference vm or retain
/// an additional pointer; neither callback nor shared-vector ownership changes.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_cpumask(
    vm: *mut ProcessVm, addr: CULong, cpu_id: CInt,
) {
    let mut local_addr = addr;
    unsafe {
        remote_flush_tlb_array_cpumask(
            vm, core::ptr::addr_of_mut!(local_addr), 1, cpu_id,
        )
    }
}

#[no_mangle]
pub static M14_RUST_SINGLE_ABI:[usize;5]=[
    core::mem::size_of::<CInt>(),core::mem::size_of::<CULong>(),
    core::mem::align_of::<CULong>(),core::mem::size_of::<*mut ProcessVm>(),
    core::mem::size_of::<*mut CULong>(),
];
