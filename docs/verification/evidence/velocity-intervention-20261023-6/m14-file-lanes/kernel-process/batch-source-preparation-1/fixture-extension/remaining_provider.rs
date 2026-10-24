// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// SOURCE-ONLY extension: link retained accepted sync actual_provider.o later.
#![no_std]
#![allow(dead_code,non_snake_case)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-process/next-sync-one-page/fixture/abi.ACTUAL.rs"] mod abi;
use core::ffi::c_void;
use abi::{CInt,CULong,OffT,SizeT,Memobj,ProcessVm,VmRange};
const PAGE_SIZE:CULong=4096;
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
#[repr(C)]
struct ProcessRemapArgs {
    off: OffT,
    start: CULong,
    memobj: *mut Memobj,
}

mod pte_helpers { include!("pte_exchange_extension.ACTUAL.rs.inc"); }
mod object_helpers {
 use crate::abi::{CInt,CULong,SizeT,Memobj};
 extern "C" { pub fn memobj_flush_page(obj:*mut Memobj,phys:CULong,pgsize:SizeT)->CInt; }
}
// Explicit typed host effect adapters. These do not claim to execute native
// TLB/mapping, page hash/unmap, allocator/tracking or RSS provider algorithms.
mod page_helpers {
 use crate::abi::{CInt,CULong,OffT};
 #[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}
#[repr(C)]
struct IhkAtomic {
    counter: CInt,
}
#[repr(C)]
struct IhkAtomic64 {
    counter64: i64,
}
#[repr(C)]
pub struct Page {
    list: ListHead,
    hash: ListHead,
    mode: u8,
    phys: CULong,
    count: IhkAtomic,
    mapped: IhkAtomic64,
    offset: OffT,
    pgshift: CInt,
}

 extern "C" { fn fixture_page_unmap_effect(page:*mut Page)->CInt; }
 pub unsafe fn page_unmap(page:*mut Page)->CInt { fixture_page_unmap_effect(page) }
}
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::CULong;
 extern "C" { fn fixture_tlb_effect(address:CULong);fn fixture_phys_to_virt_effect(phys:CULong)->*mut c_void; }
 pub unsafe fn flush_tlb_single(address:CULong) { fixture_tlb_effect(address); }
 pub unsafe fn phys_to_virt(phys:CULong)->*mut c_void { fixture_phys_to_virt_effect(phys) }
}
mod mem_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,CULong,Memobj};
 extern "C" { fn fixture_free_effect(ptr:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt);fn fixture_rss_effect(obj:*mut Memobj,size:CULong,pgsize:CInt); }
 pub unsafe fn _ihk_mc_free_pages(ptr:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt) { fixture_free_effect(ptr,n,user,file,line); }
 pub unsafe fn rusage_memory_stat_sub(obj:*mut Memobj,size:CULong,pgsize:CInt) { fixture_rss_effect(obj,size,pgsize); }
}
extern "C" {
 static mut process_remap_one_page_entry_debug:Ddebug;
 static mut process_remap_one_page_rss_debug:Ddebug;
 static mut process_remap_one_page_exit_debug:Ddebug;
 static process_remap_free_file:*const i8;
 static process_remap_free_line:CInt;
 fn phys_to_page(phys:CULong)->*mut page_helpers::Page;
 fn kprintf(format:*const i8,...)->CInt;
}
/// Replace the actual former C remap visitor. The existing outer caller
/// keeps its page-table exclusion and memobj reference for the synchronous
/// visit; page_unmap owns its existing mapped-page/hash accounting. No new
/// lock, reference, ownership transfer or error policy is introduced.
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_remap_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let args = arg0.cast::<ProcessRemapArgs>();
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut old_pte: CULong = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_entry_debug.line_flags,
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d)\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    // Preserve C's unsigned uintptr_t arithmetic and LP64 off_t conversion.
    // Both argument loads occur after the entry logger, as in the C body.
    let off = ((*args).off as CULong)
        .wrapping_add((pgaddr as CULong).wrapping_sub((*args).start)) as OffT;
    crate::pte_helpers::pte_make_fileoff(off, 0, pgsize, &raw mut old_pte);
    crate::pte_helpers::pte_xchg(pte, &raw mut old_pte);
    crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);

    // All mapping-release decisions use the exchanged snapshot, never a PTE
    // subsequently published at ptep by the existing TLB/flush boundaries.
    if crate::pte_helpers::pte_is_null(&raw const old_pte) == 0
        && crate::pte_helpers::pte_is_fileoff(&raw const old_pte, pgsize) == 0
    {
        let phys = crate::pte_helpers::pte_get_phys(&raw const old_pte);
        if crate::pte_helpers::pte_is_dirty(&raw const old_pte, pgsize) != 0 {
            // The original remap visitor deliberately ignores this result.
            let _ = crate::object_helpers::memobj_flush_page((*args).memobj, phys, pgsize);
        }
        // Existing public phys_to_page provider retains its C forwarding
        // wrapper and Rust lookup implementation; it is explicit provider debt.
        let page = phys_to_page(phys);
        if !page.is_null() && crate::page_helpers::page_unmap(page) != 0 {
            let address = crate::x86_memory_helpers::phys_to_virt(phys);
            crate::mem_helpers::_ihk_mc_free_pages(
                address,
                (pgsize / PAGE_SIZE as SizeT) as CInt,
                1, // existing IHK_MC_PG_USER, checked against actual mm.h
                process_remap_free_file as *mut i8,
                process_remap_free_line,
            );
            if core::ptr::read_volatile(core::ptr::addr_of!(
                process_remap_one_page_rss_debug.line_flags,
            )) >> 24 != 0 {
                // Original %ld payloads are the unsigned size_t values.
                let _ = kprintf(
                    b"%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                    phys, b"remap_one_page\0".as_ptr().cast::<i8>(), pgsize, pgsize,
                );
            }
            // Reload args->memobj after free/log callbacks, and retain C's
            // narrowing conversion from size_t to the provider's int pgsize.
            crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize, pgsize as CInt);
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_exit_debug.line_flags,
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d): %d\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, 0 as CInt,
        );
    }
    0
}

/// Existing synchronous range-sync failure notification. No pointer is
/// dereferenced or retained; caller lock/ref/notification ordering is unchanged.
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_process_sync_range_log_bridge(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
) {
    let _ = kprintf(
        b"sync_process_memory_range(%p,%p,%#lx,%#lx):visit failed%d\n\0".as_ptr().cast(),
        vm, range, start, end, error,
    );
}

#[no_mangle]
pub unsafe extern "C" fn fixture_remap_layout(out:*mut CULong) {
 use core::mem::{size_of,align_of,offset_of};
 let data=[size_of::<ProcessRemapArgs>(),align_of::<ProcessRemapArgs>(),offset_of!(ProcessRemapArgs,off),offset_of!(ProcessRemapArgs,start),offset_of!(ProcessRemapArgs,memobj),size_of::<page_helpers::Page>(),size_of::<Ddebug>()];
 for (index,value) in data.iter().enumerate() { *out.add(index)=*value as CULong; }
}
