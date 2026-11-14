// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_void;

/// Restore the caller's already prepared, aligned kernel XSAVE snapshot.
///
/// # Safety
/// The snapshot covers the configured XSAVE extent, is valid for the boot mask,
/// and retains the original XRSTOR CPU/exclusion and hardware-fault contract.
/// The kernel build excludes compiler-generated FP/SIMD use. Never HOST-call
/// this kernel-context entry as part of a source/code-generation check.
#[cfg(f06_rt_sigreturn_xrstor_candidate)]
#[no_mangle]
pub unsafe extern "C" fn arch_rt_sigreturn_xrstor_bridge(fpregs: *mut c_void) {
    unsafe {
        let mask = crate::x86_cpu_helpers::get_xsave_mask();
        crate::x86_cpu_helpers::x86_restore_xstate(fpregs.cast_const(), mask);
    }
}

// The writable public C array is consumed by diagnostic tools. Keep its actual
// data ABI, including the final uintptr_t(-1), rather than replacing it with a
// function or a read-only Rust constant.
#[cfg(f06_debug_constants_candidate)]
#[repr(C, align(32))]
pub struct F06DebugConstants {
    pub values: [usize; 12],
}

#[cfg(f06_debug_constants_candidate)]
#[no_mangle]
pub static mut debug_constants: F06DebugConstants = F06DebugConstants { values: [
    core::mem::size_of::<crate::abi::CpuLocalVar>(),
    core::mem::offset_of!(crate::abi::CpuLocalVar, current),
    core::mem::offset_of!(crate::abi::CpuLocalVar, runq),
    core::mem::offset_of!(crate::abi::CpuLocalVar, status),
    core::mem::offset_of!(crate::abi::CpuLocalVar, idle),
    core::mem::offset_of!(crate::abi::Thread, ctx),
    core::mem::offset_of!(crate::abi::Thread, sched_list),
    core::mem::offset_of!(crate::abi::Thread, proc),
    core::mem::offset_of!(crate::abi::Thread, status),
    core::mem::offset_of!(crate::abi::Process, pid),
    core::mem::offset_of!(crate::abi::Thread, tid),
    usize::MAX,
] };

#[cfg(f06_debug_constants_candidate)]
const _: () = {
    assert!(core::mem::size_of::<F06DebugConstants>() == 96);
    assert!(core::mem::align_of::<F06DebugConstants>() == 32);
    assert!(core::mem::offset_of!(F06DebugConstants, values) == 0);
};
