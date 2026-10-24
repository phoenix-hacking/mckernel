// SPDX-License-Identifier: GPL-2.0
//! Inert C/Rust ABI witness compiled only through the exact pinned SDK Kbuild.
#![no_std]
extern crate kernel;
use core::mem::{align_of, offset_of, size_of};
use kernel::bindings as b;
const MM_INNER: usize = offset_of!(b::mm_struct, __bindgen_anon_1);
const _: () = assert!(size_of::<core::ffi::c_uint>() == 4);
/// Pinned Linux MM, VMA, static-key and jump-table layout vector.
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

/// Pinned rwsem count and verbose relative warning-table layout vector.
#[unsafe(no_mangle)]
pub static m15_rust_warning_layout: [usize; 12] = [
    1, size_of::<b::atomic_long_t>(), align_of::<b::atomic_long_t>(),
    offset_of!(b::rw_semaphore, count), offset_of!(b::atomic_long_t, counter),
    size_of::<b::bug_entry>(), offset_of!(b::bug_entry, bug_addr_disp),
    offset_of!(b::bug_entry, file_disp), offset_of!(b::bug_entry, line),
    offset_of!(b::bug_entry, flags), b::RWSEM_WRITER_LOCKED as usize,
    (b::BUGFLAG_WARNING | (b::TAINT_WARN << 8)) as usize,
];
