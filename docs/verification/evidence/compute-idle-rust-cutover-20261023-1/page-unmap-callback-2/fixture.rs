#![allow(dead_code)]
mod abi { pub type CInt=i32; pub type CULong=u64; pub type OffT=i64; }
mod page_helpers;
use core::ffi::c_void;
use abi::CInt;
use page_helpers::Page;
unsafe extern "C" { fn page_unmap(page:*mut Page)->CInt; }
include!("callback.rs.inc");
#[no_mangle]
pub unsafe extern "C" fn actual_body(page:*mut Page, ret:CInt)->CInt {
    // Controlled orchestration isolates the unchanged production body behavior.
    static mut RET:CInt=0;
    unsafe extern "C" fn orchestrate(_: *mut Page,_:usize,_:CInt,_:u64,_:usize,_:Option<unsafe extern "C" fn(usize)->u64>,_:Option<unsafe extern "C" fn(usize,u64)>)->CInt { RET }
    RET=ret;
    page_helpers::page_unmap_body_result(page,0,0,0,0,None,None,Some(orchestrate),None)
}
