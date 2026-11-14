#[no_mangle]
pub unsafe extern "C" fn rdmsr(index: CUInt) -> CULong {
    let high: u32;
    let low: u32;

    core::arch::asm!(
        "rdmsr",
        lateout("edx") high,
        lateout("eax") low,
        in("ecx") index,
        options(nomem, nostack, preserves_flags),
    );

    ((high as CULong) << 32) | (low as CULong)
}
