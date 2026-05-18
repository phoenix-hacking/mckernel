use core::ptr::null_mut;

use crate::abi::{CInt, CULong};
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
