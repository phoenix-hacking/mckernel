//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private continuation; selected Linux x86_64 LP64, PAGE_SIZE=4096, WITH_KRM=OFF.
//! The original CPU fixture remains the sole executable-ready queue.
use core::ffi::{c_char, c_int, c_ulong, c_void};
#[cfg(ihklib_fugaku_hacks)]
compile_error!("Qualify the selected memory defaults before enabling Fugaku hacks");
#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkMemChunk { pub size: c_ulong, pub numa_node_number: c_int }
#[repr(C)]
#[derive(Clone, Copy)]
pub struct ReserveMemConf {
    pub balanced_enable: c_int, pub balanced_best_effort: c_int,
    pub balanced_variance_limit: c_int, pub min_chunk_size: c_int,
    pub max_size_ratio_all: c_int, pub timeout: c_int,
}
#[repr(C)]
struct MemReq {
    sizes: *mut usize, numa_ids: *mut c_int, num_chunks: c_int,
    min_chunk_size: c_int, max_size_ratio_all: c_int, timeout: c_int,
}
// Exact selected glibc Linux x86_64 dirent ABI, pending actual selected-header check.
// Only d_name is consumed, just as the original readdir + strncmp + atoi path.
#[repr(C)]
struct Dirent { ino: u64, off: i64, reclen: u16, kind: u8, name: [c_char; 256] }
const _: () = {
    assert!(core::mem::size_of::<IhkMemChunk>() == 16);
    assert!(core::mem::offset_of!(IhkMemChunk, numa_node_number) == 8);
    assert!(core::mem::size_of::<c_ulong>() == 8);
    assert!(core::mem::offset_of!(Dirent, name) == 19);
};
unsafe extern "C" {
    static mut reserve_mem_conf: ReserveMemConf;
    fn ihk_get_num_reserved_mem_chunks(index: c_int) -> c_int;
    fn ihk_query_mem(index: c_int, chunks: *mut IhkMemChunk, count: c_int) -> c_int;
    fn ihk_release_mem(index: c_int, chunks: *mut IhkMemChunk, count: c_int) -> c_int;
    fn calloc(count: usize, size: usize) -> *mut c_void;
    fn free(p: *mut c_void);
    fn access(path: *const c_char, mode: c_int) -> c_int;
    fn snprintf(out: *mut c_char, size: usize, format: *const c_char, ...) -> c_int;
    fn printf(format: *const c_char, ...) -> c_int;
    fn ioctl(fd: c_int, command: c_ulong, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn geteuid() -> u32;
    fn opendir(path: *const c_char) -> *mut c_void;
    fn readdir(dir: *mut c_void) -> *mut Dirent;
    fn closedir(dir: *mut c_void) -> c_int;
    fn strncmp(a: *const c_char, b: *const c_char, count: usize) -> c_int;
    fn atoi(s: *const c_char) -> c_int;
}
const DEFAULT_CONF: ReserveMemConf = ReserveMemConf { balanced_enable: 0, balanced_best_effort: 0,
    balanced_variance_limit: 0, min_chunk_size: 4096, max_size_ratio_all: 98, timeout: 30 };
unsafe fn errno_negative() -> c_int { unsafe { -*__errno_location() } }
unsafe fn readable(index: c_int) -> c_int {
    let mut path = [0 as c_char; 4096];
    unsafe { snprintf(path.as_mut_ptr(), path.len(), b"/dev/mcd%d\0".as_ptr().cast(), index); }
    if unsafe { access(path.as_ptr(), 4) } != 0 { unsafe { errno_negative() } } else { 0 }
}
#[no_mangle]
pub unsafe extern "C" fn ihk_get_num_os_instances(_index: c_int) -> c_int {
    // No access(/dev/mcosN): preserve ihkmond collision avoidance and root-only ordering.
    if unsafe { geteuid() } != 0 { return -13; }
    let dir = unsafe { opendir(b"/dev\0".as_ptr().cast()) };
    if dir.is_null() { return unsafe { errno_negative() }; }
    let mut count: c_int = 0;
    loop {
        let entry = unsafe { readdir(dir) };
        if entry.is_null() { break; }
        if unsafe { strncmp((*entry).name.as_ptr(), b"mcos\0".as_ptr().cast(), 4) } == 0 {
            count = count.wrapping_add(1);
        }
    }
    unsafe { closedir(dir); }
    count
}
#[no_mangle]
pub unsafe extern "C" fn ihk_get_os_instances(index: c_int, indices: *mut c_int, requested: c_int) -> c_int {
    let ret = unsafe { readable(index) };
    if ret != 0 { return ret; }
    let count = unsafe { ihk_get_num_os_instances(index) };
    if count < 0 { return count; }
    if count != requested { return -22; }
    if indices.is_null() { return -14; }
    let dir = unsafe { opendir(b"/dev\0".as_ptr().cast()) };
    if dir.is_null() { return unsafe { errno_negative() }; }
    let mut slot = 0usize;
    loop {
        let entry = unsafe { readdir(dir) };
        if entry.is_null() { break; }
        if unsafe { strncmp((*entry).name.as_ptr(), b"mcos\0".as_ptr().cast(), 4) } == 0 {
            unsafe { indices.add(slot).write(atoi((*entry).name.as_ptr().add(4))); }
            slot += 1;
        }
    }
    unsafe { closedir(dir); }
    0
}
#[no_mangle]
pub unsafe extern "C" fn ihk_reserve_mem(index: c_int, chunks: *mut IhkMemChunk, count: c_int) -> c_int {
    let mut storage = core::mem::MaybeUninit::<MemReq>::zeroed();
    let req = unsafe { &mut *storage.as_mut_ptr() };
    let mut fd = -1;
    let mut release = false;
    let mut chunks_reserved: *mut IhkMemChunk = core::ptr::null_mut();
    let mut reserved: *mut usize = core::ptr::null_mut();
    // Configuration setters are not concurrent with this call in the original C ABI.
    let config = unsafe { core::ptr::addr_of!(reserve_mem_conf).read() };
    let result = (|| -> c_int {
        let ret = unsafe { readable(index) };
        if ret != 0 { return ret; }
        if count < 0 || count > 2048 { return -22; }
        if count != 0 && chunks.is_null() { return -14; }
        if count == 0 { return 0; }
        req.sizes = unsafe { calloc(count as usize, core::mem::size_of::<usize>()).cast() };
        if req.sizes.is_null() { return -12; }
        req.numa_ids = unsafe { calloc(count as usize, core::mem::size_of::<c_int>()).cast() };
        if req.numa_ids.is_null() { return -12; }
        let mut total_requested = 0usize;
        for i in 0..count as usize {
            let chunk = unsafe { chunks.add(i).read() };
            unsafe {
                if config.balanced_enable != 0 {
                    req.sizes.add(i).write(usize::MAX);
                    total_requested = total_requested.wrapping_add(chunk.size as usize);
                } else { req.sizes.add(i).write(chunk.size as usize); }
                req.numa_ids.add(i).write(chunk.numa_node_number);
            }
        }
        req.num_chunks = count;
        req.min_chunk_size = config.min_chunk_size;
        req.max_size_ratio_all = config.max_size_ratio_all;
        req.timeout = config.timeout;
        fd = unsafe { super::ihklib_device_open(index) };
        if fd < 0 {
            unsafe { printf(b"ihk_reserve_mem: ihklib_device_open returned %d\n\0".as_ptr().cast(), fd); }
            return fd;
        }
        if unsafe { ioctl(fd, 0x112904 as c_ulong, req as *mut MemReq) } != 0 {
            return unsafe { errno_negative() };
        }
        unsafe { close(fd); } fd = -1;
        if config.balanced_enable == 0 { return 0; }
        release = true;
        let n = unsafe { ihk_get_num_reserved_mem_chunks(index) };
        // Signed negative count converts to size_t before calloc, matching C.
        chunks_reserved = unsafe { calloc(n as usize, core::mem::size_of::<IhkMemChunk>()).cast() };
        if chunks_reserved.is_null() { return -12; }
        if unsafe { ihk_query_mem(index, chunks_reserved, n) } != 0 { return -22; }
        reserved = unsafe { calloc(1024, core::mem::size_of::<usize>()).cast() };
        if reserved.is_null() { return -12; }
        for i in 0..n as usize {
            let chunk = unsafe { chunks_reserved.add(i).read() };
            let p = unsafe { reserved.offset(chunk.numa_node_number as isize) };
            unsafe { p.write(p.read().wrapping_add(chunk.size as usize)); }
        }
        let mut nodes = 0usize; let mut total_avail = 0usize;
        for i in 0..1024 {
            let amount = unsafe { reserved.add(i).read() };
            if amount != 0 { nodes += 1; }
            total_avail = total_avail.wrapping_add(amount);
        }
        if total_avail < total_requested {
            if config.balanced_best_effort != 0 { total_requested = total_avail; }
            else { return -12; }
        }
        const ALIGN: usize = 1 << 20;
        if config.balanced_best_effort != 0 { total_requested = (total_requested / (nodes * ALIGN)) * (nodes * ALIGN); }
        let average = ((total_requested / nodes).wrapping_add(ALIGN - 1) / ALIGN).wrapping_mul(ALIGN);
        let mut compensate_nodes = 0usize; let mut missing = 0usize; let mut excess = 0usize;
        for i in 0..1024 {
            let amount = unsafe { reserved.add(i).read() };
            if amount == 0 { continue; }
            if amount > average { compensate_nodes += 1; excess = excess.wrapping_add(amount - average); }
            else { missing = missing.wrapping_add(average - amount); }
        }
        if missing > excess { return -12; }
        // Preserve the original C pointer replacement/lifetime; see SOURCE-DEBT note.
        req.sizes = unsafe { calloc(1024, core::mem::size_of::<usize>()).cast() };
        if req.sizes.is_null() { return -12; }
        req.numa_ids = unsafe { calloc(1024, core::mem::size_of::<c_int>()).cast() };
        if req.numa_ids.is_null() { return -12; }
        let compensation = ((missing / compensate_nodes).wrapping_add(ALIGN - 1) / ALIGN).wrapping_mul(ALIGN);
        let mut release_nodes = 0usize; let mut missing2 = 0usize;
        // C accumulates total_excess2 only for diagnostics; DEBUG is off in selected profile.
        for i in 0..1024 {
            let amount = unsafe { reserved.add(i).read() };
            if amount <= average { continue; }
            let cap = average.wrapping_add(compensation);
            if amount > cap { release_nodes += 1; }
            else { missing2 = missing2.wrapping_add(cap - amount); }
        }
        let compensation2 = ((missing2 / release_nodes).wrapping_add(ALIGN - 1) / ALIGN).wrapping_mul(ALIGN);
        let cap = average.wrapping_add(compensation).wrapping_add(compensation2);
        let mut min = usize::MAX; let mut max = 0usize;
        for i in 0..1024 {
            let amount = unsafe { reserved.add(i).read() };
            unsafe { req.numa_ids.add(i).write(i as c_int); }
            let amount_release = if amount > cap { amount.wrapping_sub(cap) } else { 0 };
            unsafe { req.sizes.add(i).write(amount_release); }
            if amount > 0 {
                let after = amount.wrapping_sub(amount_release);
                if after < min { min = after; } if after > max { max = after; }
            }
        }
        let variance = average.wrapping_mul(config.balanced_variance_limit as usize) / 100;
        if max.wrapping_sub(average) > variance || average.wrapping_sub(min) > variance { return -12; }
        req.num_chunks = 1024;
        fd = unsafe { super::ihklib_device_open(index) };
        if fd < 0 { return fd; }
        if unsafe { ioctl(fd, 0x11290d as c_ulong, req as *mut MemReq) } != 0 { return unsafe { errno_negative() }; }
        unsafe { close(fd); } fd = -1; release = false;
        0
    })();
    // Exactly the original one-shot ordering, including reset on argument/access failures.
    unsafe { core::ptr::addr_of_mut!(reserve_mem_conf).write(DEFAULT_CONF); }
    if release {
        let mut all = IhkMemChunk { size: c_ulong::MAX, numa_node_number: 0 };
        unsafe { ihk_release_mem(index, &mut all, 1); }
    }
    if fd >= 0 { unsafe { close(fd); } }
    unsafe { free(req.sizes.cast()); free(req.numa_ids.cast()); }
    // Original code reads balanced_enable AFTER reset, so these frees are normally skipped.
    // Keep that behavior visible as unqualified source debt; do not claim leak-free acceptance.
    if unsafe { core::ptr::addr_of!(reserve_mem_conf.balanced_enable).read() } != 0 {
        unsafe { free(chunks_reserved.cast()); free(reserved.cast()); }
    }
    result
}
