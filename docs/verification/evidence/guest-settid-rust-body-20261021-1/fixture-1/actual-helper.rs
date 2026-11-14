#![no_std]
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{addr_of_mut,write};
pub type CInt = i32;
pub type CLong = i64;
pub type CULong = u64;
#[repr(C)]
pub struct SyscallRequest {
    pub rtid: CInt,
    pub ttid: CInt,
    pub valid: CULong,
    pub number: CULong,
    pub args: [CULong; 6],
}
type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type SyscallGetCpuFn = unsafe extern "C" fn() -> CInt;
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72);
    assert!(core::mem::align_of::<SyscallRequest>() == 8);
    assert!(core::mem::offset_of!(SyscallRequest, rtid) == 0);
    assert!(core::mem::offset_of!(SyscallRequest, ttid) == 4);
    assert!(core::mem::offset_of!(SyscallRequest, valid) == 8);
    assert!(core::mem::offset_of!(SyscallRequest, number) == 16);
    assert!(core::mem::offset_of!(SyscallRequest, args) == 24);
};
/// Complete gettid-pool request used by the CLONE_VM thread path.
///
/// # Safety
/// `request` must point to the caller's DMA-aligned, writable SyscallRequest
/// storage for this entire synchronous call. The callbacks must match their C
/// ABI and retain the existing do_syscall ownership/lifetime contract. `tids`
/// is translated even for zero count or a null pointer, as in the C fallback.
#[no_mangle]
pub unsafe extern "C" fn syscall_settid_body_result(
    request: *mut SyscallRequest,
    nr_tids: CInt,
    tids: *mut CInt,
    gettid_nr: CInt,
    virt_to_phys_fn: SyscallVirtToPhysFn,
    get_cpu_fn: SyscallGetCpuFn,
    syscall_fn: SyscallRequestCallFn,
    log_fn: unsafe extern "C" fn(CInt),
) -> CInt {
    // Zero every byte, including any representation padding, before fields.
    core::ptr::write_bytes(request.cast::<u8>(), 0, size_of::<SyscallRequest>());
    write(addr_of_mut!((*request).number), gettid_nr as CULong);
    write(addr_of_mut!((*request).args[4]), nr_tids as CULong);
    let tids_pa = virt_to_phys_fn(tids.cast::<c_void>());
    write(addr_of_mut!((*request).args[5]), tids_pa);
    let cpu = get_cpu_fn();
    // C assigns long do_syscall's return to int before checking its sign.
    let ret = syscall_fn(request, cpu) as CInt;
    if ret < 0 {
        log_fn(ret);
    }
    ret
}

