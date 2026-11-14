    // Same public Rust/reviewed-assembly providers used by the original C adapters.
    fn rdtsc() -> CULong;
    fn flush_tlb_single(addr: CULong);
    fn flush_tlb();
    fn cpu_pause();

/// Exact existing timestamp instruction provider; no serialization is added.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_rdtsc_bridge() -> CULong {
    unsafe { rdtsc() }
}

/// The same privileged invalidation provider consumes all address bits once.
/// Caller owns the original CPU/IRQ/address-space execution context.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_single_bridge(addr: CULong) {
    unsafe { flush_tlb_single(addr) }
}

/// Preserve the existing CR3 flush provider and its instruction/memory ordering.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_flush_all_bridge() {
    unsafe { flush_tlb() }
}

/// Exact existing PAUSE provider; no yield, sleep, or completion is invented.
#[no_mangle]
pub unsafe extern "C" fn mem_tlb_pause_bridge() {
    unsafe { cpu_pause() }
}

