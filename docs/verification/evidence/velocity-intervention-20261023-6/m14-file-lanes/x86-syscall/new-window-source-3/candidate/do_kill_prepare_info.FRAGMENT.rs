// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f06_do_kill_prepare_info_candidate {
    use core::mem::size_of;

    use crate::abi::{CInt, SigInfo};

    use super::EINVAL;

    /// Original do_kill signal range check and caller-owned default siginfo setup.
    ///
    /// # Safety
    /// Caller keeps original C `info0` storage in `fallback` alive throughout all
    /// synchronous group/direct signal deliveries. If `provided` is nonnull its
    /// bytes/lifetime remain the original consumer contract and are not read or
    /// written here. `selected` is a distinct writable C pointer local. On invalid
    /// signal this function writes neither the output nor fallback. On valid
    /// signal with NULL provided, fallback is suitably aligned, writable for a
    /// whole SigInfo and disjoint from selected; its entire object is initialized.
    #[no_mangle]
    pub unsafe extern "C" fn arch_do_kill_prepare_info_result(
        sig: CInt, provided: *mut SigInfo, fallback: *mut SigInfo,
        selected: *mut *mut SigInfo,
    ) -> CInt {
        if sig > 64 || sig < 0 {
            return -EINVAL;
        }
        if provided.is_null() {
            // SAFETY: original caller-owned local frame remains alive through
            // recursive do_kill; zero ALL payload/padding bytes, same as C memset.
            unsafe {
                crate::string::__inline_memset(fallback.cast(), 0, size_of::<SigInfo>());
                *selected = fallback;
                (*fallback).si_signo = sig;
                (*fallback).si_code = 0x80; // actual signal.h SI_KERNEL
            }
        } else {
            // SAFETY: store original borrowed pointer without dereference or copy.
            unsafe { *selected = provided };
        }
        0
    }
}
