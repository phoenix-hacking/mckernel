#![no_std]
#![allow(dead_code,unused_imports)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/passed-six-provider-current-union-production-preparation-1/source/kernel/rust/abi.rs"] mod abi;
use abi::{CInt,CULong,SizeT};
use core::ffi::c_void;
mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
}
const _: () = {
 assert!(core::mem::size_of::<debug::Ddebug>()==32);
 assert!(core::mem::align_of::<debug::Ddebug>()==8);
 assert!(core::mem::offset_of!(debug::Ddebug,line_flags)==24);
};
const PTL2_SHIFT: i32 = 21;
const PTL3_SHIFT: i32 = 30;
const X86_CLEAR_EFFECT_FREE_ANON: CInt = 2;
const X86_CLEAR_EFFECT_XPMEM_KEEP: CInt = 3;
const X86_CLEAR_EFFECT_FREE_UNMAPPED: CInt = 4;
const X86_CLEAR_EFFECT_CHILD_FREE: CInt = 5;
const X86_CLEAR_RANGE_LOG_SPLIT: CInt = 8;
const X86_CLEAR_RANGE_LOG_LARGE_PHYS: CInt = 9;
unsafe extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
    fn _ihk_mc_free_pages(ptr: *mut c_void, npages: CInt, is_user: CInt, file: *mut i8, line: CInt);
    static x86_pt_free_pages_file: [i8; 1];
    static x86_pt_free_pages_line: CInt;
    static x86_pt_free_pages_flag: CInt;
    static mut x86_clear_effect_child_free_debug: crate::debug::Ddebug;
    static mut x86_clear_effect_free_anon_debug: crate::debug::Ddebug;
    static mut x86_clear_effect_free_unmapped_debug: crate::debug::Ddebug;
    static mut x86_clear_effect_xpmem_keep_debug: crate::debug::Ddebug;
    static mut x86_clear_range_large_phys_debug: crate::debug::Ddebug;
}
#[no_mangle]
pub unsafe extern "C" fn x86_pt_free_pages_bridge(pt: *mut c_void, nr_pages: CInt) {
    unsafe {
        _ihk_mc_free_pages(
            pt, nr_pages, x86_pt_free_pages_flag,
            core::ptr::addr_of!(x86_pt_free_pages_file).cast::<i8>() as *mut i8,
            x86_pt_free_pages_line,
        );
    }
}
#[no_mangle]
pub unsafe extern "C" fn x86_clear_effect_log_bridge(
    event: CInt, base: CULong, phys: CULong, pgsize: SizeT,
) {
    unsafe {
        match event {
            X86_CLEAR_EFFECT_FREE_ANON => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_free_anon_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx-,%s: freed anonymous page,base=%lx,size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                        phys, b"x86_clear_effect_log_bridge\0".as_ptr().cast::<i8>(), base, pgsize, pgsize,
                    );
                }
            }
            X86_CLEAR_EFFECT_XPMEM_KEEP => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_xpmem_keep_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: XPMEM attach,phys=%lx\n\0".as_ptr().cast(),
                        b"x86_clear_effect_log_bridge\0".as_ptr().cast::<i8>(), phys);
                }
            }
            X86_CLEAR_EFFECT_FREE_UNMAPPED => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_free_unmapped_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(
                        b"%lx-,%s: freed unmapped memobj page,base=%lx,size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                        phys, b"x86_clear_effect_log_bridge\0".as_ptr().cast::<i8>(), base, pgsize, pgsize,
                    );
                }
            }
            X86_CLEAR_EFFECT_CHILD_FREE => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_effect_child_free_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: freed child page table at base=%lx,size=%ld\n\0".as_ptr().cast(),
                        b"x86_clear_effect_log_bridge\0".as_ptr().cast::<i8>(), base, pgsize);
                }
            }
            _ => {}
        }
    }
}
#[no_mangle]
pub unsafe extern "C" fn x86_clear_range_log_bridge(
    event: CInt, args: *mut c_void, ptep: *mut CULong, base: CULong,
    start: CULong, end: CULong, error: CInt, level_shift: CInt, phys: CULong,
) {
    let name = match level_shift {
        PTL2_SHIFT => b"clear_range_l2\0".as_ptr().cast::<i8>(),
        PTL3_SHIFT => b"clear_range_l3\0".as_ptr().cast::<i8>(),
        _ => b"clear_range_l4\0".as_ptr().cast::<i8>(),
    };
    unsafe {
        match event {
            X86_CLEAR_RANGE_LOG_SPLIT => {
                let _ = kprintf(b"%s(%p,%p,%lx,%lx,%lx):split page. %d\n\0".as_ptr().cast(),
                    name, args, ptep, base, start, end, error);
            }
            X86_CLEAR_RANGE_LOG_LARGE_PHYS => {
                if core::ptr::read_volatile(core::ptr::addr_of!(x86_clear_range_large_phys_debug.line_flags)) >> 24 != 0 {
                    let _ = kprintf(b"%s: phys=%ld, pte_get_phys(&old),PTL3_SIZE\n\0".as_ptr().cast(), name, phys);
                }
            }
            _ => {}
        }
    }
}
