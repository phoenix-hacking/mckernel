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

const MPOL_NODEMASK_NONE: i32 = 0;
const MPOL_NODEMASK_LOCAL: i32 = 1;
const MPOL_NODEMASK_NONLOCAL: i32 = 2;
const MPOL_NODEMASK_ALL: i32 = 3;

const EINVAL: i32 = 22;
const ENAMETOOLONG: i32 = 36;

static LD_MCK_SYSCALL_INTERCEPT: &[u8] = b"libmck_syscall_intercept.so";
static LD_SCHED_YIELD: &[u8] = b"libsched_yield.so.1.0.0";
static LD_QLFORT: &[u8] = b"libqlfort.so";
static PROC_PREFIX: &[u8] = b"/proc/";
static SYS_PREFIX: &[u8] = b"/sys/";
static DEV_XPMEM: &[u8] = b"/dev/xpmem";
static LIBUTI: &[u8] = b"libuti.so";
static PROC_SELF_PREFIX: &[u8] = b"/proc/self";
static SYS_MCOS_PREFIX: &[u8] = b"/sys/devices/virtual/mcos/mcos";
static OBJDUMP_RPATH_PREFIX: &[u8] = b"objdump -x ";
static OBJDUMP_RPATH_SUFFIX: &[u8] = b" | awk '/RPATH/ { print $2 }'";

const DIRENT32_OFF_OFFSET: usize = core::mem::size_of::<usize>();
const DIRENT32_RECLEN_OFFSET: usize = core::mem::size_of::<usize>() * 2;
const DIRENT32_NAME_OFFSET: usize = DIRENT32_RECLEN_OFFSET + core::mem::size_of::<u16>();
const DIRENT64_OFF_OFFSET: usize = core::mem::size_of::<u64>();
const DIRENT64_RECLEN_OFFSET: usize = core::mem::size_of::<u64>() + core::mem::size_of::<i64>();
const DIRENT64_NAME_OFFSET: usize =
    DIRENT64_RECLEN_OFFSET + core::mem::size_of::<u16>() + core::mem::size_of::<u8>();

unsafe extern "C" {
    fn free(ptr: *mut u8);
    fn malloc(size: usize) -> *mut u8;
    fn strcmp(s1: *const u8, s2: *const u8) -> i32;
    fn strtol(nptr: *const u8, endptr: *mut *mut u8, base: i32) -> i64;
    fn strtoul(nptr: *const u8, endptr: *mut *mut u8, base: i32) -> u64;
}

#[repr(C)]
pub struct EnvListEntry {
    str_ptr: *mut u8,
    name: *mut u8,
    value: *mut u8,
    next: *mut EnvListEntry,
}

unsafe fn cstr_bytes<'a>(ptr: *const u8) -> &'a [u8] {
    if ptr.is_null() {
        return &[];
    }

    let len = unsafe { cstr_len(ptr) };
    unsafe { core::slice::from_raw_parts(ptr, len) }
}

unsafe fn cstr_len(ptr: *const u8) -> usize {
    let mut len = 0usize;
    while unsafe { *ptr.add(len) } != 0 {
        len += 1;
    }
    len
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

fn has_exact_bytes(bytes: &[u8], expected: &[u8]) -> bool {
    bytes.len() == expected.len() && has_prefix_at(bytes, 0, expected)
}

fn contains_byte(bytes: &[u8], needle: u8) -> bool {
    let mut idx = 0usize;
    while idx < bytes.len() {
        if byte_at(bytes, idx) == needle {
            return true;
        }
        idx += 1;
    }
    false
}

fn path_boundary(bytes: &[u8], prefix_len: usize) -> bool {
    bytes.len() == prefix_len || byte_at(bytes, prefix_len) == b'/'
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

fn parse_i32_segment(bytes: &[u8], mut idx: usize) -> Option<(i32, usize)> {
    while idx < bytes.len() && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }

    let mut neg = false;
    if idx < bytes.len() {
        let sign = byte_at(bytes, idx);
        if sign == b'-' {
            neg = true;
            idx += 1;
        } else if sign == b'+' {
            idx += 1;
        }
    }

    let first_digit = idx;
    let mut value = 0i32;
    while idx < bytes.len() {
        let ch = byte_at(bytes, idx);
        if !ch.is_ascii_digit() {
            break;
        }
        value = value.saturating_mul(10).saturating_add((ch - b'0') as i32);
        idx += 1;
    }
    if idx == first_digit {
        return None;
    }

    if neg {
        Some((value.saturating_neg(), idx))
    } else {
        Some((value, idx))
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

fn atoi_segment(bytes: &[u8], start: usize, end: usize) -> i32 {
    let mut idx = start;
    while idx < end && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }

    let mut neg = false;
    if idx < end {
        let sign = byte_at(bytes, idx);
        if sign == b'-' {
            neg = true;
            idx += 1;
        } else if sign == b'+' {
            idx += 1;
        }
    }

    let mut value = 0i32;
    while idx < end {
        let ch = byte_at(bytes, idx);
        if !ch.is_ascii_digit() {
            break;
        }
        value = value.saturating_mul(10).saturating_add((ch - b'0') as i32);
        idx += 1;
    }

    if neg {
        value.saturating_neg()
    } else {
        value
    }
}

fn next_comma_token(bytes: &[u8], cursor: &mut usize) -> Option<(usize, usize)> {
    while *cursor < bytes.len() && byte_at(bytes, *cursor) == b',' {
        *cursor += 1;
    }
    if *cursor >= bytes.len() {
        return None;
    }

    let start = *cursor;
    while *cursor < bytes.len() && byte_at(bytes, *cursor) != b',' {
        *cursor += 1;
    }
    let end = *cursor;
    Some((start, end))
}

fn decimal_len_i32(value: i32) -> usize {
    if value == 0 {
        return 1;
    }

    let mut len = 0usize;
    let mut val = value as i64;
    if val < 0 {
        len += 1;
        val = -val;
    }
    while val > 0 {
        len += 1;
        val /= 10;
    }
    len
}

unsafe fn write_i32_decimal(dst: *mut u8, value: i32) -> usize {
    let mut out = dst;
    let mut val = value as i64;

    if val == 0 {
        unsafe {
            *out = b'0';
        }
        return 1;
    }

    if val < 0 {
        unsafe {
            *out = b'-';
            out = out.add(1);
        }
        val = -val;
    }

    let mut tmp = [0u8; 20];
    let mut digits = 0usize;
    while val > 0 {
        unsafe {
            *tmp.as_mut_ptr().add(digits) = b'0' + (val % 10) as u8;
        }
        digits += 1;
        val /= 10;
    }

    let mut idx = digits;
    while idx > 0 {
        idx -= 1;
        unsafe {
            *out = *tmp.as_ptr().add(idx);
            out = out.add(1);
        }
    }
    if value < 0 {
        digits + 1
    } else {
        digits
    }
}

unsafe fn copy_bytes(dst: *mut u8, src: &[u8]) -> *mut u8 {
    let mut out = dst;
    let mut idx = 0usize;
    while idx < src.len() {
        unsafe {
            *out = byte_at(src, idx);
            out = out.add(1);
        }
        idx += 1;
    }
    out
}

unsafe fn write_nul(dst: *mut u8) {
    unsafe {
        *dst = 0;
    }
}

unsafe fn write_joined_path(prefix: *const u8, path: *const u8, out: *mut u8, size: usize) -> i32 {
    if prefix.is_null() || path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let prefix_bytes = unsafe { cstr_bytes(prefix) };
    let path_bytes = unsafe { cstr_bytes(path) };
    let Some(total) = prefix_bytes
        .len()
        .checked_add(1)
        .and_then(|v| v.checked_add(path_bytes.len()))
    else {
        return -ENAMETOOLONG;
    };

    if total >= size || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix_bytes);
        *dst = b'/';
        dst = dst.add(1);
        dst = copy_bytes(dst, path_bytes);
        write_nul(dst);
    }
    total as i32
}

unsafe fn bytes_range<'a>(bytes: &[u8], start: usize, end: usize) -> &'a [u8] {
    unsafe { core::slice::from_raw_parts(bytes.as_ptr().add(start), end - start) }
}

fn last_slash_pos(bytes: &[u8]) -> Option<usize> {
    let mut idx = bytes.len();
    while idx > 0 {
        idx -= 1;
        if byte_at(bytes, idx) == b'/' {
            return Some(idx);
        }
    }
    None
}

unsafe fn write_prefixed_i32_path(
    out: *mut u8,
    size: usize,
    prefix: &[u8],
    id: i32,
    suffix: &[u8],
) -> i32 {
    let total = prefix.len() + decimal_len_i32(id) + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix);
        let written = write_i32_decimal(dst, id);
        dst = dst.add(written);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

unsafe fn write_prefixed_i32_i32_path(
    out: *mut u8,
    size: usize,
    prefix: &[u8],
    first: i32,
    middle: &[u8],
    second: i32,
    suffix: &[u8],
) -> i32 {
    let total = prefix.len()
        + decimal_len_i32(first)
        + middle.len()
        + decimal_len_i32(second)
        + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, prefix);
        let written = write_i32_decimal(dst, first);
        dst = dst.add(written);
        dst = copy_bytes(dst, middle);
        let written = write_i32_decimal(dst, second);
        dst = dst.add(written);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

fn find_subslice(bytes: &[u8], needle: &[u8]) -> Option<usize> {
    if needle.is_empty() || bytes.len() < needle.len() {
        return None;
    }

    let mut pos = 0usize;
    while pos + needle.len() <= bytes.len() {
        if has_prefix_at(bytes, pos, needle) {
            return Some(pos);
        }
        pos += 1;
    }
    None
}

unsafe fn dup_cstr(src: *const u8) -> *mut u8 {
    let bytes = unsafe { cstr_bytes(src) };
    let dst = unsafe { malloc(bytes.len() + 1) };
    if dst.is_null() {
        return core::ptr::null_mut();
    }

    let mut idx = 0usize;
    while idx < bytes.len() {
        unsafe {
            *dst.add(idx) = byte_at(bytes, idx);
        }
        idx += 1;
    }
    unsafe {
        *dst.add(idx) = 0;
    }
    dst
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_build_ld_preload_result(
    libdir: *const u8,
    existing: *const u8,
    enable_uti: i32,
    disable_sched_yield: i32,
    enable_qlmpi: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if libdir.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let libdir_bytes = unsafe { cstr_bytes(libdir) };
    let existing_bytes = if existing.is_null() {
        &[]
    } else {
        unsafe { cstr_bytes(existing) }
    };

    let mut entries = 0usize;
    let mut required = 0usize;
    let mut add_entry_len = |entry_len: usize| {
        if entries > 0 {
            required += 1;
        }
        required += entry_len;
        entries += 1;
    };

    if enable_uti != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_MCK_SYSCALL_INTERCEPT.len());
    }
    if disable_sched_yield != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_SCHED_YIELD.len());
    }
    if enable_qlmpi != 0 {
        add_entry_len(libdir_bytes.len() + 1 + LD_QLFORT.len());
    }
    if !existing.is_null() {
        if entries > 0 {
            required += 1;
        }
        required += existing_bytes.len();
    }

    if required >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    let mut written_entries = 0usize;
    unsafe fn append_entry(
        dst: &mut *mut u8,
        written_entries: &mut usize,
        libdir: &[u8],
        name: &[u8],
    ) {
        if *written_entries > 0 {
            unsafe {
                **dst = b':';
                *dst = (*dst).add(1);
            }
        }
        unsafe {
            *dst = copy_bytes(*dst, libdir);
            **dst = b'/';
            *dst = (*dst).add(1);
            *dst = copy_bytes(*dst, name);
        }
        *written_entries += 1;
    }

    if enable_uti != 0 {
        unsafe {
            append_entry(
                &mut dst,
                &mut written_entries,
                libdir_bytes,
                LD_MCK_SYSCALL_INTERCEPT,
            );
        }
    }
    if disable_sched_yield != 0 {
        unsafe {
            append_entry(&mut dst, &mut written_entries, libdir_bytes, LD_SCHED_YIELD);
        }
    }
    if enable_qlmpi != 0 {
        unsafe {
            append_entry(&mut dst, &mut written_entries, libdir_bytes, LD_QLFORT);
        }
    }
    if !existing.is_null() {
        if written_entries > 0 {
            unsafe {
                *dst = b':';
                dst = dst.add(1);
            }
        }
        dst = unsafe { copy_bytes(dst, existing_bytes) };
    }
    unsafe {
        write_nul(dst);
    }
    required as i32
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
pub unsafe extern "C" fn mcexec_parse_int_base0_full_result(
    string: *const u8,
    require_positive: i32,
    result: *mut i32,
) -> i32 {
    if string.is_null() || result.is_null() {
        return -22;
    }

    let mut end: *mut u8 = core::ptr::null_mut();
    let value = unsafe { strtol(string, &mut end, 0) };
    if end.is_null() || unsafe { *end } != 0 {
        return -22;
    }
    if require_positive != 0 && value <= 0 {
        return -22;
    }

    unsafe {
        *result = value as i32;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_atoi_result(string: *const u8) -> i32 {
    if string.is_null() {
        return 0;
    }
    unsafe { strtol(string, core::ptr::null_mut(), 10) as i32 }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_strtoul_hex_result(string: *const u8) -> u64 {
    if string.is_null() {
        return 0;
    }
    unsafe { strtoul(string, core::ptr::null_mut(), 16) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_optional_mcosid_result(
    string: *const u8,
    result: *mut i32,
) -> i32 {
    if string.is_null() || result.is_null() {
        return 0;
    }

    let bytes = unsafe { cstr_bytes(string) };
    if bytes.is_empty() || !byte_at(bytes, 0).is_ascii_digit() {
        return 0;
    }

    unsafe {
        *result = strtol(string, core::ptr::null_mut(), 10) as i32;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_env_list_count_result(head: *const EnvListEntry) -> i32 {
    let mut count = 0i32;
    let mut current = head;

    while !current.is_null() {
        count = count.saturating_add(1);
        current = unsafe { (*current).next };
    }
    count
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_search_env_list_result(
    head: *mut EnvListEntry,
    name: *const u8,
) -> *mut EnvListEntry {
    let mut current = head;

    while !current.is_null() {
        let current_name = unsafe { (*current).name as *const u8 };
        if !name.is_null() && !current_name.is_null() && unsafe { strcmp(name, current_name) } == 0
        {
            return current;
        }
        current = unsafe { (*current).next };
    }
    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_add_env_list_result(
    headp: *mut *mut EnvListEntry,
    add_string: *mut u8,
) -> i32 {
    if headp.is_null() || add_string.is_null() {
        return -22;
    }

    let name = unsafe { dup_cstr(add_string) };
    if name.is_null() {
        return -12;
    }

    let mut idx = 0usize;
    while unsafe { *name.add(idx) } != 0 && unsafe { *name.add(idx) } != b'=' {
        idx += 1;
    }
    if unsafe { *name.add(idx) } != b'=' {
        unsafe {
            free(name);
        }
        return -22;
    }

    unsafe {
        *name.add(idx) = 0;
    }
    let value = unsafe { name.add(idx + 1) };

    let head = unsafe { *headp };
    if !head.is_null() {
        let exist = unsafe { mcexec_search_env_list_result(head, name) };
        if !exist.is_null() {
            unsafe {
                free(name);
            }
            return 0;
        }
    }

    let current = unsafe { malloc(core::mem::size_of::<EnvListEntry>()) as *mut EnvListEntry };
    if current.is_null() {
        unsafe {
            free(name);
        }
        return -12;
    }

    unsafe {
        (*current).str_ptr = add_string;
        (*current).name = name;
        (*current).value = value;
        (*current).next = head;
        *headp = current;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_destroy_env_list_result(head: *mut EnvListEntry) {
    let mut current = head;
    while !current.is_null() {
        let next = unsafe { (*current).next };
        unsafe {
            free((*current).name);
            free(current as *mut u8);
        }
        current = next;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_create_local_environ_result(
    inc_list: *mut EnvListEntry,
) -> *mut *mut u8 {
    let count = unsafe { mcexec_env_list_count_result(inc_list) };
    let slots = (count as usize).saturating_add(1);
    let local_env = unsafe { malloc(core::mem::size_of::<*mut u8>() * slots) as *mut *mut u8 };
    if local_env.is_null() {
        return core::ptr::null_mut();
    }
    unsafe {
        *local_env.add(count as usize) = core::ptr::null_mut();
    }

    let mut current = inc_list;
    let mut idx = 0usize;
    while !current.is_null() {
        let dup = unsafe { dup_cstr((*current).str_ptr) };
        if dup.is_null() {
            unsafe {
                *local_env.add(idx) = core::ptr::null_mut();
                mcexec_destroy_local_environ_result(local_env);
            }
            return core::ptr::null_mut();
        }
        unsafe {
            *local_env.add(idx) = dup;
            current = (*current).next;
        }
        idx += 1;
    }
    local_env
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_destroy_local_environ_result(local_env: *mut *mut u8) {
    if local_env.is_null() {
        return;
    }

    let mut idx = 0usize;
    while unsafe { !(*local_env.add(idx)).is_null() } {
        unsafe {
            free(*local_env.add(idx));
            *local_env.add(idx) = core::ptr::null_mut();
        }
        idx += 1;
    }
    unsafe {
        free(local_env as *mut u8);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_shift_flib_affinity_result(
    affinity: *const u8,
    shift: i32,
) -> *mut u8 {
    if affinity.is_null() {
        return core::ptr::null_mut();
    }
    let bytes = unsafe { cstr_bytes(affinity) };

    let mut cursor = 0usize;
    let mut tokens = 0usize;
    let mut out_len = 0usize;
    while let Some((start, end)) = next_comma_token(bytes, &mut cursor) {
        let shifted = atoi_segment(bytes, start, end).saturating_sub(shift);
        if tokens > 0 {
            out_len += 1;
        }
        out_len += decimal_len_i32(shifted);
        tokens += 1;
    }

    let result = unsafe { malloc(out_len + 1) };
    if result.is_null() {
        return core::ptr::null_mut();
    }

    cursor = 0;
    tokens = 0;
    let mut out = result;
    while let Some((start, end)) = next_comma_token(bytes, &mut cursor) {
        let shifted = atoi_segment(bytes, start, end).saturating_sub(shift);
        if tokens > 0 {
            unsafe {
                *out = b',';
                out = out.add(1);
            }
        }
        let written = unsafe { write_i32_decimal(out, shifted) };
        unsafe {
            out = out.add(written);
        }
        tokens += 1;
    }
    unsafe {
        *out = 0;
    }
    result
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_rlimit_stack_env_result(
    env: *const u8,
    cur: *mut u64,
    max: *mut u64,
) -> i32 {
    if env.is_null() || cur.is_null() || max.is_null() {
        return 1;
    }
    let bytes = unsafe { cstr_bytes(env) };
    let mut cursor = 0usize;

    let Some((cur_start, cur_end)) = next_comma_token(bytes, &mut cursor) else {
        return 1;
    };
    let cur_value = atobytes_bytes(unsafe { bytes_range(bytes, cur_start, cur_end) });
    if cur_value == 0 {
        return 2;
    }

    let Some((max_start, max_end)) = next_comma_token(bytes, &mut cursor) else {
        return 4;
    };
    let max_value = atobytes_bytes(unsafe { bytes_range(bytes, max_start, max_end) });
    if max_value == 0 {
        return 5;
    }

    unsafe {
        *cur = cur_value;
        *max = max_value;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_apply_saved_stack_limit_result(
    mut saved_cur: u64,
    saved_max: u64,
    rlim_cur: *mut u64,
    rlim_max: *mut u64,
) {
    if rlim_cur.is_null() || rlim_max.is_null() {
        return;
    }

    if saved_cur > saved_max {
        saved_cur = saved_max;
    }
    unsafe {
        if saved_max > *rlim_max {
            *rlim_max = saved_max;
        }
        if saved_cur > *rlim_cur {
            *rlim_cur = saved_cur;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_addfd_prepare_result(
    path: *const u8,
    mcosid: i32,
    linux_path: *mut u8,
    linux_size: usize,
    mck_path: *mut u8,
    mck_size: usize,
    pathlen: *mut usize,
) -> i32 {
    if path.is_null()
        || linux_path.is_null()
        || mck_path.is_null()
        || pathlen.is_null()
        || linux_size == 0
        || mck_size == 0
    {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let prefix = if has_prefix_at(bytes, 0, PROC_PREFIX) {
        &PROC_PREFIX[..PROC_PREFIX.len() - 1]
    } else if has_prefix_at(bytes, 0, SYS_PREFIX) {
        &SYS_PREFIX[..SYS_PREFIX.len() - 1]
    } else {
        return 0;
    };

    let mut mcos_buf = [0u8; 32];
    let mut mcos_out = mcos_buf.as_mut_ptr();
    unsafe {
        mcos_out = copy_bytes(mcos_out, b"mcos");
        let len = write_i32_decimal(mcos_out, mcosid);
        mcos_out = mcos_out.add(len);
        write_nul(mcos_out);
    }
    let mcos_len = unsafe { mcos_out.offset_from(mcos_buf.as_ptr()) as usize };
    let mcos = unsafe { core::slice::from_raw_parts(mcos_buf.as_ptr(), mcos_len) };
    let Some(mcos_pos) = find_subslice(bytes, mcos) else {
        return 0;
    };
    let real_path = unsafe { bytes_range(bytes, mcos_pos + mcos_len, bytes.len()) };

    let linux_len = prefix.len() + real_path.len();
    if linux_len >= linux_size || bytes.len() >= mck_size {
        return -ENAMETOOLONG;
    }

    let mut out = linux_path;
    unsafe {
        out = copy_bytes(out, prefix);
        out = copy_bytes(out, real_path);
        write_nul(out);

        out = copy_bytes(mck_path, bytes);
        write_nul(out);
        *pathlen = linux_len;
    }
    1
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
pub unsafe extern "C" fn mcexec_ompi_mpol_policy_result(
    mpol: *const u8,
    mpol_default: i32,
    mpol_interleave: i32,
    mpol_bind: i32,
    mpol_preferred: i32,
    mode: *mut i32,
    nodemask_action: *mut i32,
) -> i32 {
    if mpol.is_null() || mode.is_null() || nodemask_action.is_null() {
        return 0;
    }
    let bytes = unsafe { cstr_bytes(mpol) };

    let (selected_mode, action) = if has_prefix_at(bytes, 0, b"localalloc") {
        (mpol_default, MPOL_NODEMASK_NONE)
    } else if has_prefix_at(bytes, 0, b"interleave_local") {
        (mpol_interleave, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"interleave_nonlocal") {
        (mpol_interleave, MPOL_NODEMASK_NONLOCAL)
    } else if has_prefix_at(bytes, 0, b"interleave_all") {
        (mpol_interleave, MPOL_NODEMASK_ALL)
    } else if has_prefix_at(bytes, 0, b"bind_local") {
        (mpol_bind, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"bind_nonlocal") {
        (mpol_bind, MPOL_NODEMASK_NONLOCAL)
    } else if has_prefix_at(bytes, 0, b"bind_all") {
        (mpol_bind, MPOL_NODEMASK_ALL)
    } else if has_prefix_at(bytes, 0, b"prefer_local") {
        (mpol_preferred, MPOL_NODEMASK_LOCAL)
    } else if has_prefix_at(bytes, 0, b"prefer_nonlocal") {
        (mpol_preferred, MPOL_NODEMASK_NONLOCAL)
    } else {
        return 0;
    };

    unsafe {
        *mode = selected_mode;
        *nodemask_action = action;
    }
    1
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
pub unsafe extern "C" fn mcexec_path_is_absolute_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    (!bytes.is_empty() && byte_at(bytes, 0) == b'/') as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_is_single_component_exec_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    let dot_prefixed = !bytes.is_empty() && byte_at(bytes, 0) == b'.';
    (!dot_prefixed && !contains_byte(bytes, b'/')) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_len_less_than_result(path: *const u8, limit: usize) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    (bytes.len() < limit) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_copy_path_result(
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if bytes.len() >= size || bytes.len() > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, bytes);
        write_nul(dst);
    }
    bytes.len() as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_path_result(
    prefix: *const u8,
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    unsafe { write_joined_path(prefix, path, out, size) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_objdump_rpath_cmd_result(
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let path_bytes = unsafe { cstr_bytes(path) };
    let Some(total) = OBJDUMP_RPATH_PREFIX
        .len()
        .checked_add(path_bytes.len())
        .and_then(|v| v.checked_add(OBJDUMP_RPATH_SUFFIX.len()))
    else {
        return -ENAMETOOLONG;
    };

    if total >= size || total > i32::MAX as usize {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, OBJDUMP_RPATH_PREFIX);
        dst = copy_bytes(dst, path_bytes);
        dst = copy_bytes(dst, OBJDUMP_RPATH_SUFFIX);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_getpath_execveat_prepare_result(
    dirfd: i32,
    filename: *const u8,
    flags: i32,
    at_fdcwd: i32,
    at_empty_path: i32,
    at_symlink_nofollow: i32,
    pathbuf: *mut u8,
    size: usize,
    check_symlink: *mut i32,
) -> i32 {
    if filename.is_null() || pathbuf.is_null() || check_symlink.is_null() {
        return EINVAL;
    }

    unsafe {
        *check_symlink = if flags & at_symlink_nofollow != 0 {
            1
        } else {
            0
        };
    }

    let filename_bytes = unsafe { cstr_bytes(filename) };
    let dev_fd = b"/dev/fd/";
    let absolute_or_cwd =
        !filename_bytes.is_empty() && byte_at(filename_bytes, 0) == b'/' || dirfd == at_fdcwd;
    let empty_path = flags & at_empty_path != 0 && filename_bytes.is_empty();

    let total_len = if absolute_or_cwd {
        filename_bytes.len()
    } else if empty_path {
        dev_fd.len() + decimal_len_i32(dirfd)
    } else {
        dev_fd.len() + decimal_len_i32(dirfd) + 1 + filename_bytes.len()
    };

    if total_len >= size {
        return ENAMETOOLONG;
    }

    let mut out = pathbuf;
    if absolute_or_cwd {
        out = unsafe { copy_bytes(out, filename_bytes) };
    } else {
        out = unsafe { copy_bytes(out, dev_fd) };
        let written = unsafe { write_i32_decimal(out, dirfd) };
        unsafe {
            out = out.add(written);
        }
        if !empty_path {
            unsafe {
                *out = b'/';
                out = out.add(1);
            }
            out = unsafe { copy_bytes(out, filename_bytes) };
        }
    }
    unsafe {
        *out = 0;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_mcos_device_path_result(
    out: *mut u8,
    size: usize,
    mcosid: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    unsafe { write_prefixed_i32_path(out, size, b"/dev/mcos", mcosid, b"") }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_proc_self_fd_path_result(
    out: *mut u8,
    size: usize,
    dirfd: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    unsafe { write_prefixed_i32_path(out, size, b"/proc/self/fd/", dirfd, b"") }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_join_path_inplace_result(
    path: *mut u8,
    size: usize,
    leaf: *const u8,
) -> i32 {
    if path.is_null() || leaf.is_null() || size == 0 {
        return -EINVAL;
    }

    let base_len = unsafe { cstr_len(path as *const u8) };
    let leaf_bytes = unsafe { cstr_bytes(leaf) };
    let mut base_end = base_len;
    if base_end > 0 && unsafe { *path.add(base_end - 1) } == b'/' {
        base_end -= 1;
    }

    let total = base_end + 1 + leaf_bytes.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = unsafe { path.add(base_end) };
    unsafe {
        *dst = b'/';
        dst = dst.add(1);
        dst = copy_bytes(dst, leaf_bytes);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_is_dev_xpmem_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    has_exact_bytes(bytes, DEV_XPMEM) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_has_libuti_result(path: *const u8) -> i32 {
    let bytes = unsafe { cstr_bytes(path) };
    find_subslice(bytes, LIBUTI).is_some() as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_uti_path_result(
    libdir: *const u8,
    path: *const u8,
    out: *mut u8,
    size: usize,
) -> i32 {
    if libdir.is_null() || path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let libdir_bytes = unsafe { cstr_bytes(libdir) };
    let path_bytes = unsafe { cstr_bytes(path) };
    let basename_start = match last_slash_pos(path_bytes) {
        Some(pos) => pos + 1,
        None => 0,
    };
    let basename = unsafe { bytes_range(path_bytes, basename_start, path_bytes.len()) };
    let middle = b"/mck/";
    let total = libdir_bytes.len() + middle.len() + basename.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, libdir_bytes);
        dst = copy_bytes(dst, middle);
        dst = copy_bytes(dst, basename);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_proc_self_path_result(
    path: *const u8,
    mcosid: i32,
    pid: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if !has_prefix_at(bytes, 0, PROC_SELF_PREFIX) || !path_boundary(bytes, PROC_SELF_PREFIX.len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, PROC_SELF_PREFIX.len(), bytes.len()) };
    unsafe { write_prefixed_i32_i32_path(out, size, b"/proc/mcos", mcosid, b"/", pid, suffix) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_proc_path_result(
    path: *const u8,
    mcosid: i32,
    out: *mut u8,
    size: usize,
) -> i32 {
    if path.is_null() || out.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    if !has_prefix_at(bytes, 0, b"/proc") || !path_boundary(bytes, b"/proc".len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, b"/proc".len(), bytes.len()) };
    unsafe { write_prefixed_i32_path(out, size, b"/proc/mcos", mcosid, suffix) }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_sys_path_result(
    path: *const u8,
    mcosid: i32,
    out: *mut u8,
    size: usize,
    mapped_offset: *mut usize,
) -> i32 {
    if path.is_null() || out.is_null() || mapped_offset.is_null() || size == 0 {
        return -EINVAL;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let sys_root = b"/sys";
    if !has_prefix_at(bytes, 0, sys_root) || !path_boundary(bytes, sys_root.len()) {
        return 0;
    }

    let suffix = unsafe { bytes_range(bytes, sys_root.len(), bytes.len()) };
    let mcos_digits = decimal_len_i32(mcosid);
    let mapped_start_len = SYS_MCOS_PREFIX.len() + mcos_digits;
    let sys_prefix = b"/sys/";
    let total = mapped_start_len + sys_prefix.len() + suffix.len();
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, SYS_MCOS_PREFIX);
        let written = write_i32_decimal(dst, mcosid);
        dst = dst.add(written);
        *mapped_offset = mapped_start_len;
        dst = copy_bytes(dst, sys_prefix);
        dst = copy_bytes(dst, suffix);
        write_nul(dst);
    }
    total as i32
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_normalize_overlay_path_result(
    path: *mut u8,
    len_out: *mut usize,
) -> i32 {
    if path.is_null() || len_out.is_null() {
        return -EINVAL;
    }

    let len = unsafe { cstr_len(path as *const u8) };
    let mut read = 0usize;
    let mut write = 0usize;
    let mut prev_slash = false;

    while read < len {
        let ch = unsafe { *path.add(read) };
        if ch == b'/' {
            if prev_slash {
                read += 1;
                continue;
            }
            prev_slash = true;
        } else {
            prev_slash = false;
        }
        unsafe {
            *path.add(write) = ch;
        }
        read += 1;
        write += 1;
    }

    while write > 0 && unsafe { *path.add(write - 1) } == b'/' {
        write -= 1;
    }

    unsafe {
        *path.add(write) = 0;
        *len_out = write;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_parse_proc_task_ids_result(
    path: *const u8,
    current_pid: i32,
    pid_out: *mut i32,
    tid_out: *mut i32,
) -> i32 {
    if path.is_null() || pid_out.is_null() || tid_out.is_null() {
        return 0;
    }

    let bytes = unsafe { cstr_bytes(path) };
    let self_task_prefix = b"/proc/self/task/";
    if has_prefix_at(bytes, 0, self_task_prefix) {
        if let Some((tid, tid_end)) = parse_i32_segment(bytes, self_task_prefix.len()) {
            if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' {
                unsafe {
                    *pid_out = current_pid;
                    *tid_out = tid;
                }
                return 1;
            }
        }
    }

    let proc_prefix = b"/proc/";
    if !has_prefix_at(bytes, 0, proc_prefix) {
        return 0;
    }

    let Some((pid, pid_end)) = parse_i32_segment(bytes, proc_prefix.len()) else {
        return 0;
    };
    let task_prefix = b"/task/";
    if !has_prefix_at(bytes, pid_end, task_prefix) {
        return 0;
    }

    let tid_start = pid_end + task_prefix.len();
    if let Some((tid, tid_end)) = parse_i32_segment(bytes, tid_start) {
        if tid_end < bytes.len() && byte_at(bytes, tid_end) == b'/' {
            unsafe {
                *pid_out = pid;
                *tid_out = tid;
            }
            return 1;
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_proc_task_check_path_result(
    out: *mut u8,
    size: usize,
    mcosid: i32,
    pid: i32,
    tid: i32,
) -> i32 {
    if out.is_null() || size == 0 {
        return -EINVAL;
    }

    let total = b"/proc/mcos".len()
        + decimal_len_i32(mcosid)
        + 1
        + decimal_len_i32(pid)
        + b"/task/".len()
        + decimal_len_i32(tid);
    if total >= size {
        return -ENAMETOOLONG;
    }

    let mut dst = out;
    unsafe {
        dst = copy_bytes(dst, b"/proc/mcos");
        let written = write_i32_decimal(dst, mcosid);
        dst = dst.add(written);
        *dst = b'/';
        dst = dst.add(1);
        let written = write_i32_decimal(dst, pid);
        dst = dst.add(written);
        dst = copy_bytes(dst, b"/task/");
        let written = write_i32_decimal(dst, tid);
        dst = dst.add(written);
        write_nul(dst);
    }
    total as i32
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
