use core::mem::transmute;
use crate::abi::{CInt,CULong,OffT,Memobj};
const ENXIO:CInt=6;
type MemobjGetPageFn =
    unsafe extern "C" fn(*mut Memobj, OffT, CInt, *mut CULong, *mut CULong, CULong) -> CInt;
#[no_mangle]
pub extern "C" fn memobj_op_present_result(op: CULong) -> CInt {
    (op != 0) as CInt
}
#[no_mangle]
pub extern "C" fn memobj_missing_page_op_result() -> CInt {
    -ENXIO
}
#[no_mangle]
pub unsafe extern "C" fn memobj_get_page(
    obj: *mut Memobj,
    off: OffT,
    p2align: CInt,
    physp: *mut CULong,
    pflag: *mut CULong,
    virt_addr: CULong,
) -> CInt {
    let op = (*(*obj).ops).get_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let get_page: MemobjGetPageFn = transmute(op);
        return get_page(obj, off, p2align, physp, pflag, virt_addr);
    }
    memobj_missing_page_op_result()
}
