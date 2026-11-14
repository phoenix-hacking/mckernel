//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Reuse shared CPU/MEM/IKC parsers; retain original allocation and error ordering.

use core::ffi::{c_char, c_int, c_void};
use core::ptr::null_mut;
use super::accepted_cpu_memory::ihklib_memory_os::IhkMemChunk;
use super::ihklib_ikc::IhkIkcReq;
use super::ikc_map::IhkIkcCpuMap;

// The original exposes __FILE__/__LINE__ inside caller-owned diagnostic buffers.
// Bind those exact selected-C producer origins; do not guess paths or silently
// substitute Rust line locations when claiming byte-equivalent diagnostics.
mod origins {
    include!(env!("MCKERNEL_IHKLIB_DIAGNOSTIC_ORIGINS_RS"));
}

unsafe extern "C" {
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn free(pointer: *mut c_void);
    fn sprintf(output: *mut c_char, format: *const c_char, ...) -> c_int;
    fn snprintf(output: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn ihk_reserve_cpu(index: c_int, cpus: *mut c_int, count: c_int) -> c_int;
    fn ihk_reserve_mem(index: c_int, chunks: *mut IhkMemChunk, count: c_int) -> c_int;
}

unsafe fn diagnostic(output: *mut c_char, operation: usize, result: c_int) {
    if !output.is_null() {
        // SAFETY: caller supplies the original sufficiently large error buffer.
        // Source-bound origins provide NUL file/name bytes and the selected C
        // int line. Format retains the original unbounded sprintf ABI contract.
        unsafe {
            sprintf(
                output,
                b"%s:%d: %s failed with %d\n\0".as_ptr().cast(),
                origins::FILE.as_ptr().cast::<c_char>(),
                origins::LINES[operation],
                origins::OPERATIONS[operation].as_ptr().cast::<c_char>(),
                result,
            );
        }
    }
}

unsafe fn cpu(index: c_int, list: *mut c_char, error: *mut c_char, assign: bool) -> c_int {
    // SAFETY: the shared parser borrows the caller's stable NUL string or NULL.
    let count = unsafe { super::ihklib_cli_parsers::cpu_str2count(list) };
    if count <= 0 {
        return -22;
    }
    // SAFETY: positive int count and int element size fit LP64; original argument
    // ordering is sizeof(int), count. The returned allocation is exclusively owned.
    let cpus: *mut c_int = unsafe {
        calloc(core::mem::size_of::<c_int>(), count as usize)
    }.cast();
    if cpus.is_null() {
        return -12;
    }
    // SAFETY: array capacity is count and input is unchanged since the count pass.
    let parsed = unsafe { super::ihklib_cli_parsers::cpu_array(list, count, cpus) };
    let result = if parsed < 0 {
        -22
    } else {
        // SAFETY: both public providers borrow count initialized CPU slots only
        // synchronously; selected function and diagnostic origin match the C body.
        let value = unsafe {
            if assign {
                super::os_cpu::ihk_os_assign_cpu(index, cpus, count)
            } else {
                ihk_reserve_cpu(index, cpus, count)
            }
        };
        if value != 0 {
            // SAFETY: caller error capacity and generated original origins apply.
            unsafe { diagnostic(error, if assign { 2 } else { 0 }, value) };
        }
        value
    };
    // SAFETY: the synchronous providers never take ownership of the CPU array.
    unsafe { free(cpus.cast()) };
    result
}

unsafe fn chunks(list: *mut c_char, output: *mut IhkMemChunk) -> c_int {
    // SAFETY: use the original second count pass over the same stable input.
    let count = unsafe { super::ihklib_cli_parsers::mem_str2count(list) };
    if count <= 0 {
        return count;
    }
    // SAFETY: positive count bounds these arrays. Both allocations deliberately
    // use sizeof(unsigned long), including the original overallocated int nodes.
    let sizes: *mut usize = unsafe {
        calloc(core::mem::size_of::<usize>(), count as usize)
    }.cast();
    if sizes.is_null() {
        return -12;
    }
    // SAFETY: independent allocation with the same original argument ordering.
    let nodes: *mut c_int = unsafe {
        calloc(core::mem::size_of::<usize>(), count as usize)
    }.cast();
    let result = if nodes.is_null() {
        -12
    } else {
        // SAFETY: caller keeps input stable and both arrays have count capacity.
        let parsed = unsafe { super::ihklib_cli_parsers::mem_array(list, sizes, nodes) };
        if parsed < 0 {
            parsed
        } else {
            for i in 0..count as usize {
                // SAFETY: caller supplies count output chunks; parser populated
                // both arrays according to the original successful count pass.
                unsafe {
                    (*output.add(i)).size = sizes.add(i).read() as core::ffi::c_ulong;
                    (*output.add(i)).numa_node_number = nodes.add(i).read();
                }
            }
            0
        }
    };
    // SAFETY: sizes and nodes are distinct owned arrays or NULL; result captured.
    unsafe { free(sizes.cast()); free(nodes.cast()); }
    result
}

/// Reserve CPU resources from the existing shared string grammar.
///
/// # Safety
/// list is NULL or a stable readable NUL string; error is NULL or a sufficiently
/// large writable original diagnostic buffer. Device/provider ABI must hold.
#[no_mangle]
pub unsafe extern "C" fn _ihk_reserve_cpu_str(
    index: c_int, list: *mut c_char, error: *mut c_char,
) -> c_int {
    // SAFETY: caller supplies the exact string/buffer/provider contracts above.
    unsafe { cpu(index, list, error, false) }
}

/// Assign CPUs using the same parser and allocation contract as CPU reservation.
///
/// # Safety
/// list is NULL or stable readable NUL storage; error is NULL or sufficiently
/// large writable diagnostic storage. OS lifetime remains caller-owned.
#[no_mangle]
pub unsafe extern "C" fn _ihk_os_assign_cpu_str(
    index: c_int, list: *mut c_char, error: *mut c_char,
) -> c_int {
    // SAFETY: same shared grammar and capacities, selecting the existing OS API.
    unsafe { cpu(index, list, error, true) }
}

/// Reserve memory chunks without introducing a second memory parser.
///
/// # Safety
/// list is NULL or a stable NUL string; error is NULL or a sufficiently large
/// writable diagnostic buffer. The selected public reserve provider borrows data.
#[no_mangle]
pub unsafe extern "C" fn _ihk_reserve_mem_str(
    index: c_int, list: *mut c_char, error: *mut c_char,
) -> c_int {
    // SAFETY: the shared existing parser takes the original stable caller input.
    let count = unsafe { super::ihklib_cli_parsers::mem_str2count(list) };
    if count <= 0 {
        return -22;
    }
    // SAFETY: positive count and 16-byte LP64 chunks fit usize without overflow.
    let memory: *mut IhkMemChunk = unsafe {
        calloc(core::mem::size_of::<IhkMemChunk>(), count as usize)
    }.cast();
    if memory.is_null() {
        return -12;
    }
    // SAFETY: input remains stable; output capacity is exactly first count pass.
    let parsed = unsafe { chunks(list, memory) };
    let result = if parsed < 0 {
        parsed
    } else {
        // SAFETY: provider borrows this owned initialized chunk array synchronously.
        let value = unsafe { ihk_reserve_mem(index, memory, count) };
        if value != 0 {
            // SAFETY: supplied output capacity and selected original origins hold.
            unsafe { diagnostic(error, 1, value) };
        }
        value
    };
    // SAFETY: this function retains exclusive ownership throughout the provider call.
    unsafe { free(memory.cast()) };
    result
}

/// Convert an IKC string to the public pair array and set the map.
///
/// # Safety
/// list is NULL or stable NUL storage; error is NULL or sufficiently large
/// writable diagnostic storage. OS instance lifetime remains caller-owned.
#[no_mangle]
pub unsafe extern "C" fn _ihk_os_set_ikc_map_str(
    index: c_int, list: *mut c_char, error: *mut c_char,
) -> c_int {
    // SAFETY: reuse the passed IKC parser with the original input unchanged.
    let count = unsafe { super::ihklib_ikc::ikc_str2count(list) };
    if count <= 0 {
        return -22;
    }
    // SAFETY: count is a positive int; allocation sizes fit usize on LP64.
    let src: *mut c_int = unsafe {
        calloc(core::mem::size_of::<c_int>(), count as usize)
    }.cast();
    if src.is_null() {
        return -12;
    }
    // SAFETY: independent destination array, with the original allocation ordering.
    let dst: *mut c_int = unsafe {
        calloc(core::mem::size_of::<c_int>(), count as usize)
    }.cast();
    let mut pairs: *mut IhkIkcCpuMap = null_mut();
    let result = (|| {
        if dst.is_null() {
            return -12;
        }
        let mut req = IhkIkcReq { src_cpus: src, dst_cpus: dst, num_cpus: count };
        // SAFETY: the existing request wrapper calls the same sole IKC parser;
        // its count write is local metadata and both live arrays have capacity.
        let parsed = unsafe { super::ihklib_ikc::ikc_str2req(list, count, &mut req) };
        if parsed < 0 {
            // SAFETY: same shared bounded eprintf logger and exact one-int message.
            unsafe {
                super::ihklib_cli_parsers::log(|text, size| {
                    snprintf(text, size,
                        b"_ihk_os_set_ikc_map_str: ikc_str2array failed with %d\n\0"
                            .as_ptr().cast(), parsed);
                });
            }
            return -22;
        }
        // SAFETY: pair count and 8-byte records fit usize; arrays remain owned.
        pairs = unsafe { calloc(core::mem::size_of::<IhkIkcCpuMap>(), count as usize) }.cast();
        if pairs.is_null() {
            return -12;
        }
        for i in 0..count as usize {
            // SAFETY: all arrays are allocated for count entries; stable-input
            // parser contract fills the counted source/destination elements.
            unsafe {
                (*pairs.add(i)).src_cpu = src.add(i).read();
                (*pairs.add(i)).dst_cpu = dst.add(i).read();
            }
        }
        // SAFETY: synchronous map setter borrows the populated pairs, retaining FDs.
        let value = unsafe { super::ikc_map::ihk_os_set_ikc_map(index, pairs, count) };
        if value != 0 {
            // SAFETY: supplied diagnostic capacity and source-bound origins apply.
            unsafe { diagnostic(error, 3, value) };
        }
        value
    })();
    // SAFETY: distinct arrays or NULL; no provider takes their ownership. Preserve
    // source,destination,pairs free order even after allocation/parser failure.
    unsafe { free(src.cast()); free(dst.cast()); free(pairs.cast()); }
    result
}
