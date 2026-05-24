use core::mem::offset_of;
use core::ptr::null_mut;

use crate::abi::{AbiListHead, CInt, CULong, KmallocHeader};
use crate::string::strstr;

unsafe extern "C" {
    fn ihk_mc_get_nr_memory_chunks() -> CInt;
    fn ihk_mc_get_memory_chunk(
        id: CInt,
        start: *mut CULong,
        end: *mut CULong,
        numa_id: *mut CInt,
    ) -> CInt;
    fn ihk_get_kargs() -> *mut i8;
    fn ihk_mc_get_processor_id() -> CInt;
}

const KMALLOC_FRONT_MAGIC: u32 = 0x5c5c5c5c;
const KMALLOC_END_MAGIC: u32 = 0x6d6d6d6d;

#[inline(always)]
unsafe fn kmalloc_list(chunk: *mut KmallocHeader) -> *mut AbiListHead {
    (&raw mut (*chunk).link.list).cast::<AbiListHead>()
}

#[inline(always)]
unsafe fn list_to_kmalloc_header(node: *mut AbiListHead) -> *mut KmallocHeader {
    node.cast::<u8>()
        .sub(offset_of!(KmallocHeader, link))
        .cast::<KmallocHeader>()
}

#[inline(always)]
unsafe fn list_add(new: *mut AbiListHead, prev: *mut AbiListHead, next: *mut AbiListHead) {
    (*next).prev = new;
    (*new).next = next;
    (*new).prev = prev;
    (*prev).next = new;
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut AbiListHead, head: *mut AbiListHead) {
    list_add(new, (*head).prev, head);
}

#[inline(always)]
unsafe fn list_del(entry: *mut AbiListHead) {
    let next = (*entry).next;
    let prev = (*entry).prev;
    (*next).prev = prev;
    (*prev).next = next;
}

#[no_mangle]
pub unsafe extern "C" fn is_mckernel_memory(start: CULong, end: CULong) -> CInt {
    let mut i = 0;
    let nr_chunks = ihk_mc_get_nr_memory_chunks();

    while i < nr_chunks {
        let mut chunk_start: CULong = 0;
        let mut chunk_end: CULong = 0;
        let mut numa_id: CInt = 0;

        ihk_mc_get_memory_chunk(i, &mut chunk_start, &mut chunk_end, &mut numa_id);
        if chunk_start <= start && start < chunk_end && chunk_start <= end && end <= chunk_end {
            return 1;
        }
        i += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn phys_to_nid(p: CULong) -> CInt {
    let mut i = 0;
    let nr_chunks = ihk_mc_get_nr_memory_chunks();

    while i < nr_chunks {
        let mut start: CULong = 0;
        let mut end: CULong = 0;
        let mut numa_id: CInt = -1;

        ihk_mc_get_memory_chunk(i, &mut start, &mut end, &mut numa_id);
        if p >= start && p < end {
            return numa_id;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn find_command_line(name: *mut i8) -> *mut i8 {
    let cmdline = ihk_get_kargs();

    if cmdline.is_null() {
        return null_mut();
    }

    strstr(cmdline, name)
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_init_chunk_result(h: *mut KmallocHeader, size: CInt) {
    (*h).size = size;
    (*h).front_magic = KMALLOC_FRONT_MAGIC;
    (*h).end_magic = KMALLOC_END_MAGIC;
    (*h).cpu_id = ihk_mc_get_processor_id();
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_insert_chunk_result(
    free_list: *mut AbiListHead,
    chunk: *mut KmallocHeader,
) {
    let mut next_chunk: *mut KmallocHeader = null_mut();
    let mut node = (*free_list).next;

    while node != free_list {
        let chunk_iter = list_to_kmalloc_header(node);
        if (chunk as usize) < (chunk_iter as usize) {
            next_chunk = chunk_iter;
            break;
        }
        node = (*node).next;
    }

    if !next_chunk.is_null() {
        list_add_tail(kmalloc_list(chunk), kmalloc_list(next_chunk));
    } else {
        list_add_tail(kmalloc_list(chunk), free_list);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ___kmalloc_consolidate_list_result(list: *mut AbiListHead) {
    loop {
        let mut chunk_iter: *mut KmallocHeader = null_mut();
        let mut chunk: *mut KmallocHeader = null_mut();
        let mut next_chunk: *mut KmallocHeader = null_mut();
        let mut node = (*list).next;

        while node != list {
            let candidate = list_to_kmalloc_header(node);

            if !chunk_iter.is_null()
                && (chunk_iter as usize)
                    + core::mem::size_of::<KmallocHeader>()
                    + (*chunk_iter).size as usize
                    == candidate as usize
            {
                chunk = chunk_iter;
                next_chunk = candidate;
                break;
            }

            chunk_iter = candidate;
            node = (*node).next;
        }

        if chunk.is_null() {
            return;
        }

        (*chunk).size += (*next_chunk).size + core::mem::size_of::<KmallocHeader>() as CInt;
        list_del(kmalloc_list(next_chunk));
    }
}
