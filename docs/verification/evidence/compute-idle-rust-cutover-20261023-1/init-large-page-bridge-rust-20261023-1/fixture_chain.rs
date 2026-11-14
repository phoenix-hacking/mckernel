#![no_std]
use core::ffi::c_void;
type CULong=u64;
type CInt=i32;
const PTATTR_ACTIVE:CULong=0x01;
const PTATTR_LARGEPAGE:CULong=0x80;
extern "C" { fn x86_pt_set_page_bridge(pt:*mut c_void,virt:CULong,phys:CULong,attr:CULong)->CInt; }
#[no_mangle]
pub unsafe extern "C" fn set_pt_large_page(
    pt: *mut c_void,
    virt: *mut c_void,
    phys: CULong,
    attr: CULong,
) -> CInt {
    unsafe {
        x86_pt_set_page_bridge(
            pt,
            virt as CULong,
            phys,
            attr | PTATTR_LARGEPAGE | PTATTR_ACTIVE,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn x86_init_normal_set_large_bridge(
    pt: *mut c_void,
    virt: CULong,
    phys: CULong,
    attr: CULong,
) -> CInt {
    // x86_64's ihk_mc_pt_attribute has the same u64 ABI as CULong.
    unsafe { set_pt_large_page(pt, virt as *mut c_void, phys, attr) }
}
