// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact proposed export + production ABI types; underlying body is a full-
// signature C recorder stub, not a claim of TLB algorithm/native execution.
#![no_std]
#![allow(dead_code)]
#[path="actual_abi.rs"] mod abi;
use abi::{CInt,CULong,ProcessVm,TlbFlushEntry};
type MemRdtscFn = unsafe extern "C" fn() -> CULong;
type MemCurrentCpuFn = unsafe extern "C" fn() -> CInt;
type MemGetVectorFn = unsafe extern "C" fn(CInt) -> CInt;
type MemInterruptCpuFn = unsafe extern "C" fn(CInt, CInt);
type MemNoirqLockFn = unsafe extern "C" fn(CULong);
type MemAtomicSetFn = unsafe extern "C" fn(CULong, CInt);
type MemAtomicIncFn = unsafe extern "C" fn(CULong);
type MemAtomicReadFn = unsafe extern "C" fn(CULong) -> CInt;
type MemFlushTlbSingleFn = unsafe extern "C" fn(CULong);
type MemFlushTlbAllFn = unsafe extern "C" fn();
type MemPauseFn = unsafe extern "C" fn();
unsafe extern "C" {

    // C owns the complete vector array; this names its first element only.
    // No array extent is invented: the immutable header geometry supplies it.
    #[link_name = "tlb_flush_vector"]
    static mut MEM_TLB_FLUSH_VECTOR_FIRST: TlbFlushEntry;
    static mem_remote_tlb_geometry: [CInt; 3];
    fn mem_tlb_rdtsc_bridge() -> CULong;
    fn mem_tlb_current_cpu_bridge() -> CInt;
    fn mem_tlb_get_vector_bridge(type_: CInt) -> CInt;
    fn mem_tlb_interrupt_cpu_bridge(cpu: CInt, vector: CInt);
    fn mem_tlb_noirq_lock_bridge(lock_addr: CULong);
    fn mem_tlb_noirq_unlock_bridge(lock_addr: CULong);
    fn mem_tlb_atomic_set_bridge(atomic_addr: CULong, value: CInt);
    fn mem_tlb_atomic_inc_bridge(atomic_addr: CULong);
    fn mem_tlb_atomic_read_bridge(atomic_addr: CULong) -> CInt;
    fn mem_tlb_flush_single_bridge(addr: CULong);
    fn mem_tlb_flush_all_bridge();
    fn mem_tlb_pause_bridge();

fn mem_remote_flush_tlb_array_body_result(
    vm: *mut ProcessVm,
    addr: *mut CULong,
    nr_addr: CInt,
    _cpu_id: CInt,
    tlb_flush_vector: *mut TlbFlushEntry,
    vector_size: CInt,
    vector_start: CInt,
    cpu_set_bits: CInt,
    rdtsc_fn: Option<MemRdtscFn>,
    current_cpu_fn: Option<MemCurrentCpuFn>,
    get_vector_fn: Option<MemGetVectorFn>,
    interrupt_cpu_fn: Option<MemInterruptCpuFn>,
    lock_fn: Option<MemNoirqLockFn>,
    unlock_fn: Option<MemNoirqLockFn>,
    atomic_set_fn: Option<MemAtomicSetFn>,
    atomic_inc_fn: Option<MemAtomicIncFn>,
    atomic_read_fn: Option<MemAtomicReadFn>,
    flush_single_fn: Option<MemFlushTlbSingleFn>,
    flush_all_fn: Option<MemFlushTlbAllFn>,
    pause_fn: Option<MemPauseFn>,
) -> CInt;
}
/// Keep the original synchronous TLB request and callback ownership boundary.
///
/// # Safety
/// The caller retains vm and the address array until the existing body returns.
/// Existing callbacks preserve current-CPU, vector, IRQ and lock semantics. C
/// owns the shared vector and immutable geometry; no pointer is retained by this
/// entry beyond the original body, and its integer return remains ignored.
#[no_mangle]
pub unsafe extern "C" fn remote_flush_tlb_array_cpumask(
    vm: *mut ProcessVm, addr: *mut CULong, nr_addr: CInt, cpu_id: CInt,
) {
    let geometry = unsafe { core::ptr::read(core::ptr::addr_of!(mem_remote_tlb_geometry)) };
    let _ = unsafe {
        mem_remote_flush_tlb_array_body_result(
            vm, addr, nr_addr, cpu_id,
            core::ptr::addr_of_mut!(MEM_TLB_FLUSH_VECTOR_FIRST),
            geometry[0], geometry[1], geometry[2],
            Some(mem_tlb_rdtsc_bridge), Some(mem_tlb_current_cpu_bridge),
            Some(mem_tlb_get_vector_bridge), Some(mem_tlb_interrupt_cpu_bridge),
            Some(mem_tlb_noirq_lock_bridge), Some(mem_tlb_noirq_unlock_bridge),
            Some(mem_tlb_atomic_set_bridge), Some(mem_tlb_atomic_inc_bridge),
            Some(mem_tlb_atomic_read_bridge), Some(mem_tlb_flush_single_bridge),
            Some(mem_tlb_flush_all_bridge), Some(mem_tlb_pause_bridge),
        )
    };
}

#[no_mangle]
pub static M14_RUST_TLB_LAYOUT:[usize;15]=[
 core::mem::size_of::<CInt>(),core::mem::align_of::<CInt>(),
 core::mem::size_of::<CULong>(),core::mem::size_of::<*mut ProcessVm>(),
 core::mem::size_of::<[CInt;3]>(),core::mem::align_of::<[CInt;3]>(),
 core::mem::size_of::<TlbFlushEntry>(),core::mem::align_of::<TlbFlushEntry>(),
 core::mem::offset_of!(TlbFlushEntry,vm),core::mem::offset_of!(TlbFlushEntry,addr),
 core::mem::offset_of!(TlbFlushEntry,nr_addr),core::mem::offset_of!(TlbFlushEntry,pending),
 core::mem::offset_of!(TlbFlushEntry,lock),abi::CPU_SET_WORDS*64,
 core::mem::size_of::<Option<MemRdtscFn>>()];
