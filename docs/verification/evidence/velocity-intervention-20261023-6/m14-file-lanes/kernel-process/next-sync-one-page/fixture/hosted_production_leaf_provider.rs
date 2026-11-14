// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code,non_snake_case)]
#[path="abi.ACTUAL.rs"] mod abi;
use abi::{CInt,CULong,SizeT,Memobj};
use core::ffi::c_void;
mod pte_helpers { include!("pte_providers.ACTUAL-RUST.inc"); }
mod object_helpers { include!("memobj_providers.ACTUAL-RUST.inc"); }
// HOST FIXTURE ONLY: actual invlpg cannot run in user mode. All logical
// PTE and memobj providers above remain the real Rust providers.
mod x86_memory_helpers {
 use crate::abi::CULong;
 extern "C" { fn fixture_tlb_effect(addr:CULong); }
 pub unsafe fn flush_tlb_single(addr:CULong) { fixture_tlb_effect(addr); }
}
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
#[repr(C)]
struct ProcessSyncArgs {
    memobj: *mut Memobj,
}
const MF_ZEROFILL:u32=0x10;
extern "C" {
 static process_sync_one_page_entry_debug:Ddebug;
 static process_sync_one_page_exit_debug:Ddebug;
 fn kprintf(format:*const i8,...) -> CInt;
}
/// Own the actual former C sync callback. The caller retains the live PTE,
/// args/memobj and existing page-table exclusion for the synchronous visit.
/// Valid pgshift is the original supported 0..63 domain. No new error policy,
/// ownership transfer, allocation or lock is introduced.
#[no_mangle]
pub unsafe extern "C" fn sync_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut error = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_entry_debug.line_flags,
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d)\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    if crate::pte_helpers::pte_is_null(pte) == 0
        && crate::pte_helpers::pte_is_fileoff(pte, pgsize) == 0
        && crate::pte_helpers::pte_is_dirty(pte, pgsize) != 0
    {
        crate::pte_helpers::pte_clear_dirty(pte, pgsize);
        crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);
        // Original ordering: read physical PTE after the TLB-effect callback,
        // then inspect zero-fill flags before the existing memobj operation.
        let phys = crate::pte_helpers::pte_get_phys(pte);
        let memobj = (*arg0.cast::<ProcessSyncArgs>()).memobj;
        if (*memobj).flags & MF_ZEROFILL == 0 {
            error = crate::object_helpers::memobj_flush_page(memobj, phys, pgsize);
            if error != 0 {
                let _ = kprintf(
                    b"sync_one_page(%p,%p,%p %#lx,%p,%d):flush failed. %d\n\0".as_ptr().cast(),
                    arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
                );
                crate::pte_helpers::pte_set_dirty(pte, pgsize);
            }
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_exit_debug.line_flags,
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
        );
    }
    error
}
