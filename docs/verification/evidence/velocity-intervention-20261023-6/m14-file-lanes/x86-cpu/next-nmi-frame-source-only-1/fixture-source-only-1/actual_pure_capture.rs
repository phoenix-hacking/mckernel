#![no_std]
use core::ffi::c_void;
#[path="actual_abi.rs"] mod abi;
use abi::CULong;
extern "C" { fn fixture_nmi_capture_flags()->CULong; }

/// Preserve the complete existing NMI frame rewrite. The caller owns a live,
/// aligned writable span of at least 27 C unsigned-long words. This forward
/// overlapping copy and the final five fields exactly match the C producer;
/// the supplied function is stored as a return address and is never invoked.
#[no_mangle]
pub unsafe extern "C" fn rust_mod_nmi_pure(
    nmi_ctx: *mut c_void,
    func: Option<unsafe extern "C" fn()>,
) {
    let flags: CULong;
    // Same pushfq/pop read used by existing cpu_interrupt_disabled. Default
    // memory/flags clobbers retain the original C "memory","cc" barrier.
    flags = unsafe { fixture_nmi_capture_flags() };
    let words = nmi_ctx.cast::<CULong>();
    let mut i = 0usize;
    while i < 22 {
        let value = unsafe { words.add(i + 5).read() };
        unsafe { words.add(i).write(value); }
        i += 1;
    }
    let return_address = func.map_or(0, |entry| entry as CULong);
    unsafe {
        words.add(22).write(return_address);
        words.add(23).write(0x20);
        // Actual registers.h RFLAGS_IF=(1<<9); same mask is already used by
        // existing Rust cpu_interrupt_disabled. No IRQ state is changed here.
        words.add(24).write(flags & !(1 << 9));
        words.add(25).write(words.add(27) as CULong);
        words.add(26).write(0x28);
    }
}

// This fixture-only data export uses real ABI types, never a 27-word model.
#[no_mangle]
pub static M14_RUST_NMI_HEADER_ABI:[usize;12]=[
 core::mem::size_of::<CULong>(),core::mem::align_of::<CULong>(),
 core::mem::size_of::<*mut c_void>(),core::mem::size_of::<Option<unsafe extern "C" fn()>>(),
 core::mem::size_of::<abi::X86BasicRegs>(),core::mem::offset_of!(abi::X86BasicRegs,rip),
 core::mem::offset_of!(abi::X86BasicRegs,cs),core::mem::offset_of!(abi::X86BasicRegs,rflags),
 core::mem::offset_of!(abi::X86BasicRegs,rsp),core::mem::offset_of!(abi::X86BasicRegs,ss),
 core::mem::size_of::<abi::X86UserContext>(),core::mem::offset_of!(abi::X86UserContext,gpr)];
