// SPDX-License-Identifier: GPL-2.0
// Source-only witness: exact retained SDK kernel.rmeta and saved rustc flags.
#![no_std]
extern crate kernel;
use core::mem::{align_of, offset_of, size_of};
use kernel::bindings as b;
const MM_INNER: usize = offset_of!(b::mm_struct, __bindgen_anon_1);
const _: () = assert!(size_of::<core::ffi::c_uint>() == 4);
#[unsafe(no_mangle)]
pub static m15_rust_mm_layout: [usize; 23] = [
    1,
    size_of::<b::mm_struct>(), align_of::<b::mm_struct>(),
    MM_INNER + offset_of!(b::mm_struct__bindgen_ty_1, mmap_lock),
    MM_INNER + offset_of!(b::mm_struct__bindgen_ty_1, mm_lock_seq),
    size_of::<b::seqcount_t>(), align_of::<b::seqcount_t>(), offset_of!(b::seqcount_t, sequence),
    size_of::<b::vm_area_struct>(), align_of::<b::vm_area_struct>(),
    offset_of!(b::vm_area_struct, vm_mm),
    offset_of!(b::vm_area_struct, vm_lock_seq),
    offset_of!(b::vm_area_struct, vm_lock),
    size_of::<b::vma_lock>(), offset_of!(b::vma_lock, lock),
    size_of::<b::rw_semaphore>(), align_of::<b::rw_semaphore>(),
    size_of::<b::tracepoint>(), align_of::<b::tracepoint>(),
    offset_of!(b::tracepoint, key), size_of::<b::static_key>(),
    offset_of!(b::static_key, enabled), size_of::<b::jump_entry>(),
];
