#![no_std]

use core::panic::PanicInfo;

const KIB: u64 = 1024;
const MIB: u64 = KIB * 1024;
const GIB: u64 = MIB * 1024;
const ULONG_MAX: u64 = u64::MAX;

const MPOL_NO_HEAP: u64 = 0x01;
const MPOL_NO_STACK: u64 = 0x02;
const MPOL_NO_BSS: u64 = 0x04;
const MPOL_SHM_PREMAP: u64 = 0x08;

const DIRENT32_OFF_OFFSET: usize = core::mem::size_of::<usize>();
const DIRENT32_RECLEN_OFFSET: usize = core::mem::size_of::<usize>() * 2;
const DIRENT32_NAME_OFFSET: usize = DIRENT32_RECLEN_OFFSET + core::mem::size_of::<u16>();
const DIRENT64_OFF_OFFSET: usize = core::mem::size_of::<u64>();
const DIRENT64_RECLEN_OFFSET: usize = core::mem::size_of::<u64>() + core::mem::size_of::<i64>();
const DIRENT64_NAME_OFFSET: usize =
    DIRENT64_RECLEN_OFFSET + core::mem::size_of::<u16>() + core::mem::size_of::<u8>();

unsafe fn cstr_bytes<'a>(ptr: *const u8) -> &'a [u8] {
    if ptr.is_null() {
        return &[];
    }

    let mut len = 0usize;
    while unsafe { *ptr.add(len) } != 0 {
        len += 1;
    }
    unsafe { core::slice::from_raw_parts(ptr, len) }
}

fn is_space(b: u8) -> bool {
    matches!(b, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

fn byte_at(bytes: &[u8], idx: usize) -> u8 {
    unsafe { *bytes.as_ptr().add(idx) }
}

fn has_prefix_at(bytes: &[u8], start: usize, prefix: &[u8]) -> bool {
    if start > bytes.len() || bytes.len() - start < prefix.len() {
        return false;
    }

    let mut idx = 0usize;
    while idx < prefix.len() {
        if byte_at(bytes, start + idx) != byte_at(prefix, idx) {
            return false;
        }
        idx += 1;
    }
    true
}

fn parse_decimal_segment(bytes: &[u8], mut idx: usize) -> Option<usize> {
    while idx < bytes.len() && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }
    if idx < bytes.len() {
        let sign = byte_at(bytes, idx);
        if sign == b'-' || sign == b'+' {
            idx += 1;
        }
    }

    let first_digit = idx;
    while idx < bytes.len() && byte_at(bytes, idx).is_ascii_digit() {
        idx += 1;
    }
    if idx == first_digit {
        None
    } else {
        Some(idx)
    }
}

fn atol_prefix(bytes: &[u8]) -> i64 {
    let mut idx = 0usize;
    while idx < bytes.len() && is_space(bytes[idx]) {
        idx += 1;
    }

    let mut neg = false;
    if idx < bytes.len() {
        if bytes[idx] == b'-' {
            neg = true;
            idx += 1;
        } else if bytes[idx] == b'+' {
            idx += 1;
        }
    }

    let mut value = 0i64;
    while idx < bytes.len() && bytes[idx].is_ascii_digit() {
        value = value
            .saturating_mul(10)
            .saturating_add((bytes[idx] - b'0') as i64);
        idx += 1;
    }

    if neg {
        value.saturating_neg()
    } else {
        value
    }
}

fn atobytes_bytes(bytes: &[u8]) -> u64 {
    if bytes.is_empty() {
        return 0;
    }

    let last = bytes[bytes.len() - 1];
    let (number, mult) = match last {
        b'k' | b'K' => (&bytes[..bytes.len() - 1], KIB),
        b'm' | b'M' => (&bytes[..bytes.len() - 1], MIB),
        b'g' | b'G' => (&bytes[..bytes.len() - 1], GIB),
        _ => (bytes, 1),
    };

    (atol_prefix(number) as u64).wrapping_mul(mult)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_atobytes_result(string: *const u8) -> u64 {
    atobytes_bytes(unsafe { cstr_bytes(string) })
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_stack_arg_result(
    string: *const u8,
    stack_premap: *mut i64,
    stack_max: *mut i64,
) {
    let bytes = unsafe { cstr_bytes(string) };
    let comma = bytes.iter().position(|&b| b == b',');
    let (first, rest) = match comma {
        Some(pos) => (&bytes[..pos], Some(&bytes[pos + 1..])),
        None => (bytes, None),
    };

    if !first.is_empty() && !stack_premap.is_null() {
        unsafe {
            *stack_premap = atobytes_bytes(first) as i64;
        }
    }

    if let Some(second_and_more) = rest {
        let second_end = second_and_more
            .iter()
            .position(|&b| b == b',')
            .unwrap_or(second_and_more.len());
        let second = &second_and_more[..second_end];
        if !second.is_empty() && !stack_max.is_null() {
            unsafe {
                *stack_max = atobytes_bytes(second) as i64;
            }
        }
    }
}

#[no_mangle]
pub extern "C" fn mcexec_default_heap_extension_result(heap_extension: u64, page_size: u64) -> u64 {
    if heap_extension == ULONG_MAX {
        page_size
    } else {
        heap_extension
    }
}

#[no_mangle]
pub extern "C" fn mcexec_default_thread_count_result(
    nr_threads: i32,
    omp_present: i32,
    omp_threads: i32,
    nr_processes: i32,
    ncpu: i32,
) -> i32 {
    if nr_threads > 0 {
        nr_threads
    } else if omp_present != 0 {
        omp_threads + 4
    } else if nr_processes > 0 && nr_processes < ncpu {
        let result = (ncpu / nr_processes) + 4;
        if result == 0 {
            2
        } else {
            result
        }
    } else if nr_processes == ncpu {
        1
    } else {
        ncpu
    }
}

#[no_mangle]
pub extern "C" fn mcexec_mpol_flags_result(
    no_heap: i32,
    no_stack: i32,
    no_bss: i32,
    shm_premap: i32,
) -> u64 {
    let mut flags = 0u64;
    if no_heap != 0 {
        flags |= MPOL_NO_HEAP;
    }
    if no_stack != 0 {
        flags |= MPOL_NO_STACK;
    }
    if no_bss != 0 {
        flags |= MPOL_NO_BSS;
    }
    if shm_premap != 0 {
        flags |= MPOL_SHM_PREMAP;
    }
    flags
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_stack_max_result(
    stack_max: i64,
    rlim_cur: *mut u64,
    rlim_max: *mut u64,
) {
    if stack_max == -1 || rlim_cur.is_null() || rlim_max.is_null() {
        return;
    }

    let stack_max = stack_max as u64;
    unsafe {
        *rlim_cur = stack_max;
        if *rlim_max != ULONG_MAX && *rlim_max < *rlim_cur {
            *rlim_max = *rlim_cur;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_is_proc_task_leaf_path_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };

    let self_prefix = b"/proc/self/task/";
    if has_prefix_at(bytes, 0, self_prefix) {
        if let Some(idx) = parse_decimal_segment(bytes, self_prefix.len()) {
            if idx < bytes.len() && byte_at(bytes, idx) == b'/' && idx + 1 < bytes.len() {
                return 1;
            }
        }
    }

    let proc_prefix = b"/proc/";
    if !has_prefix_at(bytes, 0, proc_prefix) {
        return 0;
    }

    let Some(pid_end) = parse_decimal_segment(bytes, proc_prefix.len()) else {
        return 0;
    };
    let task_prefix = b"/task/";
    if !has_prefix_at(bytes, pid_end, task_prefix) {
        return 0;
    }

    let tid_start = pid_end + task_prefix.len();
    if let Some(tid_end) = parse_decimal_segment(bytes, tid_start) {
        if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' && tid_end + 1 < bytes.len() {
            return 1;
        }
    }

    0
}

unsafe fn read_u16(ptr: *const u8, offset: usize) -> u16 {
    unsafe { *((ptr.add(offset)) as *const u16) }
}

unsafe fn add_mut(ptr: *mut u8, offset: usize) -> *mut u8 {
    unsafe { ptr.add(offset) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_reclen_result(dirp: *const u8) -> u16 {
    if dirp.is_null() {
        return 0;
    }
    unsafe { read_u16(dirp, DIRENT32_RECLEN_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_name_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT32_NAME_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent32_off_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT32_OFF_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_reclen_result(dirp: *const u8) -> u16 {
    if dirp.is_null() {
        return 0;
    }
    unsafe { read_u16(dirp, DIRENT64_RECLEN_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_name_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT64_NAME_OFFSET) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_dirent64_off_result(dirp: *mut u8) -> *mut u8 {
    if dirp.is_null() {
        return core::ptr::null_mut();
    }
    unsafe { add_mut(dirp, DIRENT64_OFF_OFFSET) }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
