use core::mem::transmute;
use crate::abi::{CInt,CULong,SizeT,Memobj};
type MemobjPageOpFn = unsafe extern "C" fn(*mut Memobj, CULong, SizeT) -> CInt;
#[no_mangle]
pub extern "C" fn memobj_op_present_result(op: CULong) -> CInt {
    (op != 0) as CInt
}
#[no_mangle]
pub extern "C" fn memobj_default_page_op_result() -> CInt {
    0
}
#[no_mangle]
pub unsafe extern "C" fn memobj_invalidate_page(
    obj: *mut Memobj,
    phys: CULong,
    pgsize: SizeT,
) -> CInt {
    let op = (*(*obj).ops).invalidate_page;
    if memobj_op_present_result(op as CULong) != 0 {
        let invalidate_page: MemobjPageOpFn = transmute(op);
        return invalidate_page(obj, phys, pgsize);
    }
    memobj_default_page_op_result()
}
