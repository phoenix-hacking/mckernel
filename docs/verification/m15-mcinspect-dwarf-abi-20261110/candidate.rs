#![no_std]
#![deny(warnings)]
#![allow(dead_code)]
use core::ffi::{c_int, c_void};
include!("/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/diagnostic-abi-tests-1/output/c_layout.rs");

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfSig8 {
    signature: [u8; 8],
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfLoc {
    lr_atom: u8,
    lr_number: u64,
    lr_number2: u64,
    lr_offset: u64,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfLocdesc {
    ld_lopc: u64,
    ld_hipc: u64,
    ld_cents: u16,
    ld_s: *mut DwarfLoc,
    ld_from_loclist: u8,
    ld_section_offset: u64,
}

unsafe extern "C" {
    #[cfg(mcinspect_full_body)]
    fn dwarf_get_TAG_name(value: core::ffi::c_uint, out: *mut *const u8) -> c_int;
}

unsafe extern "C" {
    #[cfg(mcinspect_full_body)]
    fn dwarf_next_cu_header_c(
        dbg: *mut c_void,
        is_info: c_int,
        cu_length: *mut u64,
        cu_version: *mut u16,
        cu_abbrev_offset: *mut u64,
        cu_pointer_size: *mut u16,
        cu_offset_size: *mut u16,
        cu_extension_size: *mut u16,
        type_signature: *mut DwarfSig8,
        type_offset: *mut u64,
        cu_next_offset: *mut u64,
        error: *mut *mut c_void,
    ) -> c_int;
}

unsafe extern "C" {
    #[cfg(mcinspect_full_body)]
    fn dwarf_loclist_n(
        attr: *mut c_void,
        locdescs: *mut *mut *mut DwarfLocdesc,
        len: *mut i64,
        error: *mut *mut c_void,
    ) -> c_int;
}

const _: [(); C_SIG_SIZE] = [(); core::mem::size_of::<DwarfSig8>()];
const _: [(); C_SIG_ALIGN] = [(); core::mem::align_of::<DwarfSig8>()];
const _: [(); C_SIG_SIGNATURE_OFFSET] = [(); core::mem::offset_of!(DwarfSig8, signature)];
const _: [(); C_SIG_SIGNATURE_SIZE] = [(); core::mem::size_of::<[u8; 8]>()];
const _: [(); C_SIG_SIGNATURE_ALIGN] = [(); core::mem::align_of::<[u8; 8]>()];
const _: [(); C_LOC_SIZE] = [(); core::mem::size_of::<DwarfLoc>()];
const _: [(); C_LOC_ALIGN] = [(); core::mem::align_of::<DwarfLoc>()];
const _: [(); C_LOC_LR_ATOM_OFFSET] = [(); core::mem::offset_of!(DwarfLoc, lr_atom)];
const _: [(); C_LOC_LR_ATOM_SIZE] = [(); core::mem::size_of::<u8>()];
const _: [(); C_LOC_LR_ATOM_ALIGN] = [(); core::mem::align_of::<u8>()];
const _: [(); C_LOC_LR_NUMBER_OFFSET] = [(); core::mem::offset_of!(DwarfLoc, lr_number)];
const _: [(); C_LOC_LR_NUMBER_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_LOC_LR_NUMBER_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_LOC_LR_NUMBER2_OFFSET] = [(); core::mem::offset_of!(DwarfLoc, lr_number2)];
const _: [(); C_LOC_LR_NUMBER2_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_LOC_LR_NUMBER2_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_LOC_LR_OFFSET_OFFSET] = [(); core::mem::offset_of!(DwarfLoc, lr_offset)];
const _: [(); C_LOC_LR_OFFSET_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_LOC_LR_OFFSET_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_DESC_SIZE] = [(); core::mem::size_of::<DwarfLocdesc>()];
const _: [(); C_DESC_ALIGN] = [(); core::mem::align_of::<DwarfLocdesc>()];
const _: [(); C_DESC_LD_LOPC_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_lopc)];
const _: [(); C_DESC_LD_LOPC_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_DESC_LD_LOPC_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_DESC_LD_HIPC_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_hipc)];
const _: [(); C_DESC_LD_HIPC_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_DESC_LD_HIPC_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_DESC_LD_CENTS_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_cents)];
const _: [(); C_DESC_LD_CENTS_SIZE] = [(); core::mem::size_of::<u16>()];
const _: [(); C_DESC_LD_CENTS_ALIGN] = [(); core::mem::align_of::<u16>()];
const _: [(); C_DESC_LD_S_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_s)];
const _: [(); C_DESC_LD_S_SIZE] = [(); core::mem::size_of::<*mut DwarfLoc>()];
const _: [(); C_DESC_LD_S_ALIGN] = [(); core::mem::align_of::<*mut DwarfLoc>()];
const _: [(); C_DESC_LD_FROM_LOCLIST_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_from_loclist)];
const _: [(); C_DESC_LD_FROM_LOCLIST_SIZE] = [(); core::mem::size_of::<u8>()];
const _: [(); C_DESC_LD_FROM_LOCLIST_ALIGN] = [(); core::mem::align_of::<u8>()];
const _: [(); C_DESC_LD_SECTION_OFFSET_OFFSET] = [(); core::mem::offset_of!(DwarfLocdesc, ld_section_offset)];
const _: [(); C_DESC_LD_SECTION_OFFSET_SIZE] = [(); core::mem::size_of::<u64>()];
const _: [(); C_DESC_LD_SECTION_OFFSET_ALIGN] = [(); core::mem::align_of::<u64>()];
const _: [(); C_UINT_SIZE] = [(); core::mem::size_of::<core::ffi::c_uint>()];
const _: [(); C_UINT_ALIGN] = [(); core::mem::align_of::<core::ffi::c_uint>()];
const _: unsafe extern "C" fn(core::ffi::c_uint, *mut *const u8) -> c_int = dwarf_get_TAG_name;
const _: unsafe extern "C" fn(*mut c_void, *mut *mut *mut DwarfLocdesc, *mut i64, *mut *mut c_void) -> c_int = dwarf_loclist_n;
const _: unsafe extern "C" fn(*mut c_void, c_int, *mut u64, *mut u16, *mut u64, *mut u16, *mut u16, *mut u16, *mut DwarfSig8, *mut u64, *mut u64, *mut *mut c_void) -> c_int = dwarf_next_cu_header_c;
unsafe fn source_bound_tag_promotion() {
    let tag: u16 = 0;
    let mut tag_name: *const u8 = core::ptr::null();
    let _ = unsafe { dwarf_get_TAG_name(tag as core::ffi::c_uint, &mut tag_name) };
}
