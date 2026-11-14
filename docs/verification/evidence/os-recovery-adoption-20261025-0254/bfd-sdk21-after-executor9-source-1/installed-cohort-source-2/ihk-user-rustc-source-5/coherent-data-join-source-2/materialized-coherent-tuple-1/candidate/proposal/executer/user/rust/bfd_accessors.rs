//! Rust implementation of the four former project C BFD macro wrappers.
//! Offsets come from the selected, pinned BFD header via a nonshipped witness.
#![no_std]
use core::ffi::{c_long, c_void};
include!(env!("MCKERNEL_BFD_LAYOUT_RS"));

#[cfg(not(all(target_arch = "x86_64", target_os = "linux", target_pointer_width = "64")))]
compile_error!("BFD accessor qualification covers x86_64 Linux LP64 only");
const _: [(); 8] = [(); core::mem::size_of::<c_long>()];
const _: [(); 8] = [(); core::mem::size_of::<*const c_void>()];
type Upper = unsafe extern "C" fn(*mut c_void) -> c_long;
type Canonicalize = unsafe extern "C" fn(*mut c_void, *mut *mut c_void) -> c_long;
const _: [(); 8] = [(); core::mem::size_of::<Upper>()];
const _: [(); 8] = [(); core::mem::size_of::<Canonicalize>()];

// Same preconditions as BFD_SEND: abfd denotes a live, properly initialized BFD,
// xvec denotes its live target, and the selected target callback is valid.
// Raw reads borrow neither object as Rust references and invent no ownership.
// The library receives the original pointers, including a null location if the
// caller supplied one. Its return value and BFD error state pass through intact.
unsafe fn upper(abfd: *mut c_void) -> c_long {
    let xvec = unsafe { abfd.cast::<u8>().add(BFD_XVEC_OFFSET).cast::<*const u8>().read() };
    let callback = unsafe { xvec.add(BFD_UPPER_OFFSET).cast::<Upper>().read() };
    unsafe { callback(abfd) }
}
unsafe fn canonicalize(abfd: *mut c_void, location: *mut *mut c_void) -> c_long {
    let xvec = unsafe { abfd.cast::<u8>().add(BFD_XVEC_OFFSET).cast::<*const u8>().read() };
    let callback = unsafe { xvec.add(BFD_CANONICALIZE_OFFSET).cast::<Canonicalize>().read() };
    unsafe { callback(abfd, location) }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_bfd_get_symtab_upper_bound_bridge(abfd: *mut c_void) -> c_long {
    unsafe { upper(abfd) }
}
#[no_mangle]
pub unsafe extern "C" fn eclair_bfd_get_symtab_upper_bound_bridge(abfd: *mut c_void) -> c_long {
    unsafe { upper(abfd) }
}
#[no_mangle]
pub unsafe extern "C" fn mcinspect_bfd_canonicalize_symtab_bridge(abfd: *mut c_void, location: *mut *mut c_void) -> c_long {
    unsafe { canonicalize(abfd, location) }
}
#[no_mangle]
pub unsafe extern "C" fn eclair_bfd_canonicalize_symtab_bridge(abfd: *mut c_void, location: *mut *mut c_void) -> c_long {
    unsafe { canonicalize(abfd, location) }
}
