#![no_std]

use core::ffi::c_void;
#[cfg(mckernel_crash_x86_64)]
use core::ffi::{c_int, c_long};
use core::panic::PanicInfo;

const VR_STACK: usize = 0x1;
const VR_PRIVATE: usize = 0x2000;
const VR_PROT_READ: usize = 0x0001_0000;
const VR_PROT_WRITE: usize = 0x0002_0000;
const VR_PROT_EXEC: usize = 0x0004_0000;

const PS_RUNNING: i32 = 0x1;
const PS_INTERRUPTIBLE: i32 = 0x2;
const PS_UNINTERRUPTIBLE: i32 = 0x4;
const PS_ZOMBIE: i32 = 0x8;
const PS_STOPPED: i32 = 0x20;
const STR_PID: i32 = 0x1;
const STR_TASK: i32 = 0x2;
const STR_INVALID: i32 = 0x4;
const LINUX_PAGE_OFFSET_BASE_NAME: [u8; 23] = *b"linux_page_offset_base\0";
const X86_KERNEL_PHYS_BASE_NAME: [u8; 21] = *b"x86_kernel_phys_base\0";

static STATUS_RUNNING: [u8; 3] = *b"RU\0";
static STATUS_INTERRUPTIBLE: [u8; 3] = *b"IN\0";
static STATUS_UNINTERRUPTIBLE: [u8; 3] = *b"UN\0";
static STATUS_ZOMBIE: [u8; 2] = *b"Z\0";
static STATUS_STOPPED: [u8; 2] = *b"T\0";
static STATUS_UNKNOWN: [u8; 3] = *b"??\0";

static PGSHIFT_4K: [u8; 3] = *b"4K\0";
static PGSHIFT_64K: [u8; 4] = *b"64K\0";
static PGSHIFT_2M: [u8; 3] = *b"2M\0";
static PGSHIFT_512M: [u8; 5] = *b"512M\0";
static PGSHIFT_1G: [u8; 3] = *b"1G\0";
static PGSHIFT_16G: [u8; 4] = *b"16G\0";
static PGSHIFT_512G: [u8; 5] = *b"512G\0";
static PGSHIFT_4T: [u8; 3] = *b"4T\0";
static PGSHIFT_32P: [u8; 4] = *b"32P\0";
static EMPTY: [u8; 1] = *b"\0";

type MckCrashReadUlongFn = unsafe extern "C" fn(addr: usize, out: *mut usize) -> i32;
type MckCrashReadIntFn = unsafe extern "C" fn(addr: usize, out: *mut i32) -> i32;
type MckCrashLookupPidFn =
    unsafe extern "C" fn(pid: usize, thash: usize, thread_out: *mut usize) -> i32;
type MckCrashGetSymbolFn = unsafe extern "C" fn(name: *const u8) -> usize;

#[cfg(mckernel_crash_x86_64)]
unsafe extern "C" {
    static mut LINUX_PAGE_OFFSET: usize;
    #[link_name = "x86_kernel_phys_base"]
    static mut X86_KERNEL_PHYS_BASE_CRASH: usize;
    static mck_crash_map_kernel_start: usize;
    static mck_crash_map_fixed_start: usize;
    static mck_crash_map_st_start: usize;

    fn kvtop(task: *mut c_void, vaddr: usize, paddr: *mut usize, verbose: c_int) -> c_int;
    fn readmem(
        addr: u64,
        memtype: c_int,
        buffer: *mut c_void,
        size: c_long,
        type_: *mut u8,
        error_handle: usize,
    ) -> c_int;
}

unsafe fn cstr_len(ptr: *const u8) -> usize {
    if ptr.is_null() {
        return 0;
    }

    let mut len = 0usize;
    while unsafe { *ptr.add(len) } != 0 {
        len += 1;
    }
    len
}

unsafe fn write_byte_checked(buf: *mut u8, pos: &mut usize, buf_size: usize, byte: u8) -> bool {
    if *pos + 1 >= buf_size {
        return false;
    }
    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
    true
}

unsafe fn write_lit_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    lit: *const u8,
) -> bool {
    let mut idx = 0usize;
    loop {
        let byte = unsafe { *lit.add(idx) };
        if byte == 0 {
            return true;
        }
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        idx += 1;
    }
}

unsafe fn write_usize_hex_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: usize,
) -> bool {
    let mut seen = false;
    let mut shift = core::mem::size_of::<usize>() * 8;

    while shift > 0 {
        shift -= 4;
        let digit = ((value >> shift) & 0xf) as u8;
        if digit != 0 || seen || shift == 0 {
            seen = true;
            let ch = if digit < 10 {
                b'0' + digit
            } else {
                b'a' + digit - 10
            };
            if !unsafe { write_byte_checked(buf, pos, buf_size, ch) } {
                return false;
            }
        }
    }
    true
}

unsafe fn write_i32_decimal_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: i32,
    width: usize,
) -> bool {
    let negative = value < 0;
    let mut mag = if negative {
        -(value as i64)
    } else {
        value as i64
    } as u64;
    let mut digits = 1usize;
    let mut scan = mag;
    while scan >= 10 {
        digits += 1;
        scan /= 10;
    }

    let total = digits + negative as usize;
    let mut pad = width.saturating_sub(total);
    while pad > 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b' ') } {
            return false;
        }
        pad -= 1;
    }
    if negative && !unsafe { write_byte_checked(buf, pos, buf_size, b'-') } {
        return false;
    }

    let mut divisor = 1u64;
    for _ in 1..digits {
        divisor *= 10;
    }
    while divisor > 0 {
        let digit = (mag / divisor) as u8;
        if !unsafe { write_byte_checked(buf, pos, buf_size, b'0' + digit) } {
            return false;
        }
        mag %= divisor;
        divisor /= 10;
    }
    true
}

unsafe fn write_usize_decimal_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    mut value: usize,
) -> bool {
    let mut digits = 1usize;
    let mut scan = value;
    while scan >= 10 {
        digits += 1;
        scan /= 10;
    }

    let mut divisor = 1usize;
    for _ in 1..digits {
        divisor *= 10;
    }
    while divisor > 0 {
        let digit = (value / divisor) as u8;
        if !unsafe { write_byte_checked(buf, pos, buf_size, b'0' + digit) } {
            return false;
        }
        value %= divisor;
        divisor /= 10;
    }
    true
}

unsafe fn write_usize_hex_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: usize,
    width: usize,
) -> bool {
    let max_nibbles = core::mem::size_of::<usize>() * 2;
    let significant = if value == 0 {
        1
    } else {
        max_nibbles - (value.leading_zeros() as usize / 4)
    };
    let digits = width.max(significant).min(max_nibbles);

    for idx in (0..digits).rev() {
        let digit = ((value >> (idx * 4)) & 0xf) as u8;
        let ch = if digit < 10 {
            b'0' + digit
        } else {
            b'a' + digit - 10
        };
        if !unsafe { write_byte_checked(buf, pos, buf_size, ch) } {
            return false;
        }
    }
    true
}

unsafe fn append_flag_label(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    label: *const u8,
    written_flags: &mut usize,
) -> bool {
    if *written_flags > 0 && !unsafe { write_byte_checked(buf, pos, buf_size, b'|') } {
        return false;
    }
    if !unsafe { write_lit_checked(buf, pos, buf_size, label) } {
        return false;
    }
    *written_flags += 1;
    true
}

unsafe fn copy_cstr_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    src: *const u8,
) -> bool {
    if src.is_null() {
        return true;
    }

    let mut idx = 0usize;
    loop {
        let byte = unsafe { *src.add(idx) };
        if byte == 0 {
            return true;
        }
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        idx += 1;
    }
}

unsafe fn copy_cstr_right_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    src: *const u8,
    width: usize,
) -> bool {
    let mut pad = width.saturating_sub(unsafe { cstr_len(src) });
    while pad > 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b' ') } {
            return false;
        }
        pad -= 1;
    }
    unsafe { copy_cstr_checked(buf, pos, buf_size, src) }
}

unsafe fn finish_cstr_checked(buf: *mut u8, pos: usize, buf_size: usize) {
    if buf_size == 0 {
        return;
    }
    let term = if pos < buf_size { pos } else { buf_size - 1 };
    unsafe {
        *buf.add(term) = 0;
    }
}

unsafe fn basename_ptr(path: *const u8) -> *const u8 {
    if path.is_null() {
        return path;
    }

    let len = unsafe { cstr_len(path) };
    let mut idx = len;
    while idx > 0 {
        idx -= 1;
        if unsafe { *path.add(idx) } == b'/' {
            return unsafe { path.add(idx + 1) };
        }
    }
    path
}

fn decimal_value(byte: u8) -> Option<usize> {
    if byte.is_ascii_digit() {
        Some((byte - b'0') as usize)
    } else {
        None
    }
}

fn hex_value(byte: u8) -> Option<usize> {
    if byte.is_ascii_digit() {
        Some((byte - b'0') as usize)
    } else if (b'a'..=b'f').contains(&byte) {
        Some((byte - b'a' + 10) as usize)
    } else if (b'A'..=b'F').contains(&byte) {
        Some((byte - b'A' + 10) as usize)
    } else {
        None
    }
}

unsafe fn parse_cstr_decimal(ptr: *const u8) -> Option<usize> {
    if ptr.is_null() {
        return None;
    }

    let mut idx = 0usize;
    let mut value = 0usize;
    let mut seen = false;
    loop {
        let byte = unsafe { *ptr.add(idx) };
        if byte == 0 {
            return seen.then_some(value);
        }
        let digit = decimal_value(byte)?;
        value = value.saturating_mul(10).saturating_add(digit);
        seen = true;
        idx += 1;
    }
}

unsafe fn parse_cstr_hex(ptr: *const u8) -> Option<usize> {
    if ptr.is_null() {
        return None;
    }

    let mut idx = 0usize;
    if unsafe { *ptr } == b'0' {
        let second = unsafe { *ptr.add(1) };
        if second == b'x' || second == b'X' {
            idx = 2;
        }
    }

    let mut value = 0usize;
    let mut seen = false;
    loop {
        let byte = unsafe { *ptr.add(idx) };
        if byte == 0 {
            return seen.then_some(value);
        }
        let digit = hex_value(byte)?;
        value = value.saturating_mul(16).saturating_add(digit);
        seen = true;
        idx += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_x86_direct_phys_result(
    addr: usize,
    linux_page_offset: usize,
    x86_kernel_phys_base: usize,
    map_kernel_start: usize,
    map_fixed_start: usize,
    map_st_start: usize,
    phys_out: *mut usize,
) -> i32 {
    if phys_out.is_null() || linux_page_offset == usize::MAX || x86_kernel_phys_base == usize::MAX {
        return 0;
    }

    let phys = if addr >= map_kernel_start && addr < map_kernel_start.wrapping_add(0x4000) {
        addr.wrapping_sub(map_kernel_start)
            .wrapping_add(x86_kernel_phys_base)
    } else if addr >= linux_page_offset {
        addr.wrapping_sub(linux_page_offset)
    } else if addr >= map_fixed_start {
        addr.wrapping_sub(map_fixed_start)
    } else if addr >= map_st_start {
        addr.wrapping_sub(map_st_start)
    } else {
        return 0;
    };

    unsafe {
        *phys_out = phys;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcreadmem_x86_addr_result(
    addr: usize,
    linux_page_offset: usize,
    x86_kernel_phys_base: usize,
    map_kernel_start: usize,
    map_fixed_start: usize,
    map_st_start: usize,
    translated_out: *mut usize,
) -> i32 {
    if translated_out.is_null()
        || linux_page_offset == usize::MAX
        || x86_kernel_phys_base == usize::MAX
    {
        return 0;
    }

    let mut phys = 0usize;
    if unsafe {
        mck_crash_x86_direct_phys_result(
            addr,
            linux_page_offset,
            x86_kernel_phys_base,
            map_kernel_start,
            map_fixed_start,
            map_st_start,
            &mut phys,
        )
    } != 0
    {
        unsafe {
            *translated_out = phys.wrapping_add(linux_page_offset);
        }
        return 1;
    }

    unsafe {
        *translated_out = addr;
    }
    2
}

#[cfg(mckernel_crash_x86_64)]
#[no_mangle]
pub unsafe extern "C" fn mcreadmem(
    addr: u64,
    memtype: c_int,
    buffer: *mut c_void,
    size: c_long,
    type_: *mut u8,
    error_handle: usize,
) -> c_int {
    let mut translated = addr as usize;
    let linux_page_offset = unsafe { LINUX_PAGE_OFFSET };
    let x86_base = unsafe { X86_KERNEL_PHYS_BASE_CRASH };

    if linux_page_offset != usize::MAX && x86_base != usize::MAX {
        let mut out = 0usize;
        let action = unsafe {
            mck_crash_mcreadmem_x86_addr_result(
                translated,
                linux_page_offset,
                x86_base,
                mck_crash_map_kernel_start,
                mck_crash_map_fixed_start,
                mck_crash_map_st_start,
                &mut out,
            )
        };
        if action == 1 {
            translated = out;
        } else if action == 2 {
            let mut phys = 0usize;
            unsafe {
                kvtop(core::ptr::null_mut(), translated, &mut phys, 0);
            }
            translated = phys.wrapping_add(linux_page_offset);
        }
    }

    unsafe {
        readmem(
            translated as u64,
            memtype,
            buffer,
            size,
            type_,
            error_handle,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_thread_status_label_result(status: i32) -> *const u8 {
    if status == PS_RUNNING {
        STATUS_RUNNING.as_ptr()
    } else if status == PS_INTERRUPTIBLE {
        STATUS_INTERRUPTIBLE.as_ptr()
    } else if status == PS_UNINTERRUPTIBLE {
        STATUS_UNINTERRUPTIBLE.as_ptr()
    } else if status == PS_ZOMBIE {
        STATUS_ZOMBIE.as_ptr()
    } else if status == PS_STOPPED {
        STATUS_STOPPED.as_ptr()
    } else {
        STATUS_UNKNOWN.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_vr_perm_result(buf: *mut u8, flag: usize) -> i32 {
    if buf.is_null() {
        return 0;
    }

    unsafe {
        *buf.add(0) = if flag & VR_PROT_READ != 0 { b'r' } else { b'-' };
        *buf.add(1) = if flag & VR_PROT_WRITE != 0 {
            b'w'
        } else {
            b'-'
        };
        *buf.add(2) = if flag & VR_PROT_EXEC != 0 { b'x' } else { b'-' };
        *buf.add(3) = if flag & VR_PRIVATE != 0 { b'p' } else { b'-' };
        *buf.add(4) = 0;
    }
    4
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_default_path_result(
    buf: *mut u8,
    buf_size: usize,
    start: usize,
    end: usize,
    flag: usize,
    vdso_addr: usize,
    vvar_addr: usize,
    brk_start: usize,
    brk_end_allocated: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        if start == vdso_addr {
            write_lit_checked(buf, &mut pos, buf_size, b"[vdso]\0".as_ptr())
        } else if start == vvar_addr {
            write_lit_checked(buf, &mut pos, buf_size, b"[vsyscall]\0".as_ptr())
        } else if flag & VR_STACK != 0 {
            write_lit_checked(buf, &mut pos, buf_size, b"[stack]\0".as_ptr())
        } else if start >= brk_start && end <= brk_end_allocated {
            write_lit_checked(buf, &mut pos, buf_size, b"[heap]\0".as_ptr())
        } else {
            true
        }
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_child_pos_result(
    dst: *mut u8,
    dst_size: usize,
    src: *const u8,
    side: u8,
) -> i32 {
    if dst.is_null() || dst_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        copy_cstr_checked(dst, &mut pos, dst_size, src)
            && write_byte_checked(dst, &mut pos, dst_size, b'/')
            && write_byte_checked(dst, &mut pos, dst_size, side)
    };
    unsafe {
        finish_cstr_checked(dst, pos, dst_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_root_pos_result(dst: *mut u8, dst_size: usize) -> i32 {
    if dst.is_null() || dst_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe { write_lit_checked(dst, &mut pos, dst_size, b"root\0".as_ptr()) };
    unsafe {
        finish_cstr_checked(dst, pos, dst_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_pgshift_label_result(pgshift: i32) -> *const u8 {
    if pgshift == 12 {
        PGSHIFT_4K.as_ptr()
    } else if pgshift == 16 {
        PGSHIFT_64K.as_ptr()
    } else if pgshift == 21 {
        PGSHIFT_2M.as_ptr()
    } else if pgshift == 29 {
        PGSHIFT_512M.as_ptr()
    } else if pgshift == 30 {
        PGSHIFT_1G.as_ptr()
    } else if pgshift == 34 {
        PGSHIFT_16G.as_ptr()
    } else if pgshift == 39 {
        PGSHIFT_512G.as_ptr()
    } else if pgshift == 42 {
        PGSHIFT_4T.as_ptr()
    } else if pgshift == 55 {
        PGSHIFT_32P.as_ptr()
    } else {
        core::ptr::null()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_symbol_value_cmd_result(
    dst: *mut u8,
    dst_size: usize,
    name: *const u8,
) -> i32 {
    if dst.is_null() || dst_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(dst, &mut pos, dst_size, b"printf \"%p\", &\0".as_ptr())
            && copy_cstr_checked(dst, &mut pos, dst_size, name)
    };
    unsafe {
        finish_cstr_checked(dst, pos, dst_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_add_symbol_file_cmd_result(
    dst: *mut u8,
    dst_size: usize,
    filename: *const u8,
) -> i32 {
    if dst.is_null() || dst_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(dst, &mut pos, dst_size, b"add-symbol-file \0".as_ptr())
            && copy_cstr_checked(dst, &mut pos, dst_size, filename)
            && write_lit_checked(dst, &mut pos, dst_size, b" 0\0".as_ptr())
    };
    unsafe {
        finish_cstr_checked(dst, pos, dst_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_kmsg_first_part_result(head: i32, tail: i32, len: i32) -> usize {
    if len <= 0 || head < 0 || tail < 0 || head > len || tail > len {
        return 0;
    }

    if tail < head {
        (len - head) as usize
    } else {
        (tail - head) as usize
    }
}

type MckCrashReadStringFn = unsafe extern "C" fn(addr: usize, buf: *mut u8, len: i32) -> i32;
type MckCrashReadI32Fn = unsafe extern "C" fn(addr: usize, out: *mut i32) -> i32;
type MckCrashGetBufFn = unsafe extern "C" fn(len: i32) -> *mut u8;
type MckCrashFreeBufFn = unsafe extern "C" fn(buf: *mut u8);
type MckCrashWriteStringFn = unsafe extern "C" fn(msg: *const u8);
type MckCrashRegisterExtensionFn = unsafe extern "C" fn(command_table: *mut c_void);

#[no_mangle]
pub unsafe extern "C" fn mck_crash_kmsg_read_body_result(
    kmsg_buf_str: usize,
    head: i32,
    tail: i32,
    len: i32,
    msg: *mut u8,
    read_fn: MckCrashReadStringFn,
) -> i32 {
    if msg.is_null()
        || len <= 0
        || head < 0
        || tail < 0
        || head > len
        || tail > len
        || (read_fn as usize) == 0
    {
        return 0;
    }

    let first_len = mck_crash_kmsg_first_part_result(head, tail, len) as i32;
    if unsafe { read_fn(kmsg_buf_str.wrapping_add(head as usize), msg, first_len) } == 0 {
        return 0;
    }

    if mck_crash_kmsg_wrap_result(head, tail) != 0
        && unsafe { read_fn(kmsg_buf_str, msg.add(first_len as usize), tail) } == 0
    {
        return 0;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_cmd_mckmsg_body_result(
    kmsg_buf: usize,
    kmsg_buf_str_offset: isize,
    kmsg_buf_head_offset: isize,
    kmsg_buf_tail_offset: isize,
    kmsg_buf_len_offset: isize,
    read_i32_fn: MckCrashReadI32Fn,
    getbuf_fn: MckCrashGetBufFn,
    freebuf_fn: MckCrashFreeBufFn,
    read_string_fn: MckCrashReadStringFn,
    write_string_fn: MckCrashWriteStringFn,
) -> i32 {
    if (read_i32_fn as usize) == 0
        || (getbuf_fn as usize) == 0
        || (freebuf_fn as usize) == 0
        || (read_string_fn as usize) == 0
        || (write_string_fn as usize) == 0
    {
        return -2;
    }

    let mut head = 0i32;
    let mut tail = 0i32;
    let mut len = 0i32;
    if unsafe {
        read_i32_fn(
            kmsg_buf.wrapping_add(kmsg_buf_head_offset as usize),
            &mut head,
        )
    } == 0
        || unsafe {
            read_i32_fn(
                kmsg_buf.wrapping_add(kmsg_buf_tail_offset as usize),
                &mut tail,
            )
        } == 0
        || unsafe {
            read_i32_fn(
                kmsg_buf.wrapping_add(kmsg_buf_len_offset as usize),
                &mut len,
            )
        } == 0
    {
        return 0;
    }

    if len <= 0 {
        return -2;
    }

    let msg = unsafe { getbuf_fn(len) };
    if msg.is_null() {
        return -2;
    }

    let kmsg_buf_str = kmsg_buf.wrapping_add(kmsg_buf_str_offset as usize);
    let read_ok = unsafe {
        mck_crash_kmsg_read_body_result(kmsg_buf_str, head, tail, len, msg, read_string_fn)
    };
    if read_ok == 0 {
        unsafe {
            freebuf_fn(msg);
        }
        return -1;
    }

    unsafe {
        write_string_fn(msg);
        freebuf_fn(msg);
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_cmd_mcinfo_body_result(
    linux_page_offset: usize,
    write_string_fn: Option<MckCrashWriteStringFn>,
) -> i32 {
    let Some(write_string_fn) = write_string_fn else {
        return -2;
    };

    let mut buf = [0u8; 64];
    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf.as_mut_ptr(),
            &mut pos,
            buf.len(),
            b"LINUX_PAGE_OFFSET: 0x\0".as_ptr(),
        ) && write_usize_hex_checked(buf.as_mut_ptr(), &mut pos, buf.len(), linux_page_offset)
            && write_byte_checked(buf.as_mut_ptr(), &mut pos, buf.len(), b'\n')
    };
    if !ok {
        return -2;
    }
    unsafe {
        finish_cstr_checked(buf.as_mut_ptr(), pos, buf.len());
        write_string_fn(buf.as_ptr());
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_extension_init_body_result(
    command_table: *mut c_void,
    register_fn: Option<MckCrashRegisterExtensionFn>,
) -> i32 {
    let Some(register_fn) = register_fn else {
        return -2;
    };
    if command_table.is_null() {
        return -2;
    }

    unsafe {
        register_fn(command_table);
    }
    0
}

#[no_mangle]
pub extern "C" fn mck_crash_extension_fini_body_result() -> i32 {
    0
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_thread_comm_result(
    saved_cmdline: *const u8,
    is_idle: i32,
) -> *const u8 {
    if is_idle != 0 {
        b"idle\0".as_ptr()
    } else if saved_cmdline.is_null() {
        EMPTY.as_ptr()
    } else {
        unsafe { basename_ptr(saved_cmdline) }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcps_line_result(
    buf: *mut u8,
    buf_size: usize,
    is_active: i32,
    tid: i32,
    pid: i32,
    ppid: i32,
    cpu: i32,
    thread: usize,
    status: *const u8,
    comm: *const u8,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_byte_checked(
            buf,
            &mut pos,
            buf_size,
            if is_active != 0 { b'>' } else { b' ' },
        ) && write_i32_decimal_width_checked(buf, &mut pos, buf_size, tid, 6)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_i32_decimal_width_checked(buf, &mut pos, buf_size, pid, 6)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_i32_decimal_width_checked(buf, &mut pos, buf_size, ppid, 6)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_i32_decimal_width_checked(buf, &mut pos, buf_size, cpu, 3)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, thread, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && copy_cstr_right_width_checked(buf, &mut pos, buf_size, status, 2)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && copy_cstr_checked(buf, &mut pos, buf_size, comm)
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcps_header_result(buf: *mut u8, buf_size: usize) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"    TID    PID   PPID CPU THREAD           ST COMM\0".as_ptr(),
        )
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcmem_line_result(
    buf: *mut u8,
    buf_size: usize,
    start: usize,
    end: usize,
    perm: *const u8,
    memobj: usize,
    path: *const u8,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_usize_hex_width_checked(buf, &mut pos, buf_size, start, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b'-')
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, end, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && copy_cstr_checked(buf, &mut pos, buf_size, perm)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, end.wrapping_sub(start), 8)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, memobj, 16)
            && write_lit_checked(buf, &mut pos, buf_size, b"   \0".as_ptr())
            && copy_cstr_checked(buf, &mut pos, buf_size, path)
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcmem_process_line_result(
    buf: *mut u8,
    buf_size: usize,
    pid: usize,
    thread: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"Memory mapping for process \0".as_ptr(),
        ) && write_usize_decimal_checked(buf, &mut pos, buf_size, pid)
            && write_lit_checked(buf, &mut pos, buf_size, b" / \0".as_ptr())
            && write_usize_hex_checked(buf, &mut pos, buf_size, thread)
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcmem_header_result(buf: *mut u8, buf_size: usize) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"START            END              PERM SIZE     MEMOBJ            BACKING FILE\0"
                .as_ptr(),
        )
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_mcvtop_header_result(buf: *mut u8, buf_size: usize) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"VIRT             PHYS             SIZE FLAGS\0".as_ptr(),
        )
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_pte_line_result(
    buf: *mut u8,
    buf_size: usize,
    virt: usize,
    phys: usize,
    size_label: *const u8,
    flags: *const u8,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_usize_hex_width_checked(buf, &mut pos, buf_size, virt, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, phys, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && copy_cstr_right_width_checked(buf, &mut pos, buf_size, size_label, 4)
            && write_lit_checked(buf, &mut pos, buf_size, b" (\0".as_ptr())
            && copy_cstr_checked(buf, &mut pos, buf_size, flags)
            && write_byte_checked(buf, &mut pos, buf_size, b')')
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_pte_raw_line_result(
    buf: *mut u8,
    buf_size: usize,
    pte: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(buf, &mut pos, buf_size, b"PTE: \0".as_ptr())
            && write_usize_hex_checked(buf, &mut pos, buf_size, pte)
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_pte_not_found_result(
    buf: *mut u8,
    buf_size: usize,
    addr: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"Couldn't find valid PTE for 0x\0".as_ptr(),
        ) && write_usize_hex_checked(buf, &mut pos, buf_size, addr)
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_memory_range_header_result(
    buf: *mut u8,
    buf_size: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe { write_lit_checked(buf, &mut pos, buf_size, b"\nMemory range:\0".as_ptr()) };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_parse_context_values_result(
    input: *const u8,
    badaddr: usize,
    decimal_out: *mut usize,
    hex_out: *mut usize,
) -> i32 {
    if input.is_null() || decimal_out.is_null() || hex_out.is_null() {
        return 0;
    }

    let decimal = unsafe { parse_cstr_decimal(input) };
    let hex = unsafe { parse_cstr_hex(input) };
    unsafe {
        *decimal_out = decimal.unwrap_or(badaddr);
        *hex_out = hex.unwrap_or(badaddr);
    }

    (decimal.is_some() as i32) | ((hex.is_some() as i32) << 1)
}

#[no_mangle]
pub extern "C" fn mck_crash_pid_hash_head_result(
    thash: usize,
    pid: usize,
    hash_size: usize,
    list_head_size: usize,
) -> usize {
    if hash_size == 0 {
        return thash;
    }
    thash.wrapping_add((pid % hash_size).wrapping_mul(list_head_size))
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_context_lookup_body_result(
    input: *const u8,
    badaddr: usize,
    clv: usize,
    clv_resource_set_offset: isize,
    resource_set_thread_hash_offset: isize,
    thread_tid_offset: isize,
    pid_out: *mut usize,
    thread_out: *mut usize,
    read_ulong_fn: Option<MckCrashReadUlongFn>,
    read_int_fn: Option<MckCrashReadIntFn>,
    lookup_pid_fn: Option<MckCrashLookupPidFn>,
) -> i32 {
    if input.is_null() {
        return STR_INVALID;
    }

    let mut dvalue = badaddr;
    let mut hvalue = badaddr;
    unsafe {
        mck_crash_parse_context_values_result(input, badaddr, &mut dvalue, &mut hvalue);
    }

    if let (Some(read_ulong), Some(lookup_pid)) = (read_ulong_fn, lookup_pid_fn) {
        let mut rset = 0usize;
        let mut thash = 0usize;
        if unsafe {
            read_ulong(
                clv.wrapping_add(clv_resource_set_offset as usize),
                &mut rset,
            )
        } != 0
            && unsafe {
                read_ulong(
                    rset.wrapping_add(resource_set_thread_hash_offset as usize),
                    &mut thash,
                )
            } != 0
        {
            let mut found_thread = 0usize;
            if dvalue != badaddr && unsafe { lookup_pid(dvalue, thash, &mut found_thread) } != 0 {
                unsafe {
                    if !pid_out.is_null() {
                        *pid_out = dvalue;
                    }
                    if !thread_out.is_null() {
                        *thread_out = found_thread;
                    }
                }
                return STR_PID;
            }

            if hvalue != badaddr && unsafe { lookup_pid(hvalue, thash, &mut found_thread) } != 0 {
                unsafe {
                    if !pid_out.is_null() {
                        *pid_out = hvalue;
                    }
                    if !thread_out.is_null() {
                        *thread_out = found_thread;
                    }
                }
                return STR_PID;
            }
        }
    }

    if hvalue != badaddr {
        if let Some(read_int) = read_int_fn {
            let mut tid = 0i32;
            if unsafe { read_int(hvalue.wrapping_add(thread_tid_offset as usize), &mut tid) } != 0 {
                unsafe {
                    if !thread_out.is_null() {
                        *thread_out = hvalue;
                    }
                    if !pid_out.is_null() {
                        *pid_out = tid as usize;
                    }
                }
                return STR_TASK;
            }
        }
    }

    STR_INVALID
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_parse_hex_addr_result(
    input: *const u8,
    badaddr: usize,
    addr_out: *mut usize,
) -> i32 {
    if input.is_null() || addr_out.is_null() {
        return 0;
    }

    let parsed = unsafe { parse_cstr_hex(input) };
    unsafe {
        *addr_out = parsed.unwrap_or(badaddr);
    }
    parsed.is_some() as i32
}

#[no_mangle]
pub extern "C" fn mck_crash_same_boot_result(
    old_boot_param_pa: usize,
    old_boot_sec: usize,
    old_boot_nsec: usize,
    new_boot_param_pa: usize,
    new_boot_sec: usize,
    new_boot_nsec: usize,
) -> i32 {
    (old_boot_param_pa == new_boot_param_pa
        && old_boot_sec == new_boot_sec
        && old_boot_nsec == new_boot_nsec) as i32
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_x86_arch_init_body_result(
    linux_page_offset_out: *mut usize,
    x86_kernel_phys_base_out: *mut usize,
    get_symbol_fn: MckCrashGetSymbolFn,
) {
    if !linux_page_offset_out.is_null() {
        unsafe {
            *linux_page_offset_out = get_symbol_fn(LINUX_PAGE_OFFSET_BASE_NAME.as_ptr());
        }
    }
    if !x86_kernel_phys_base_out.is_null() {
        unsafe {
            *x86_kernel_phys_base_out = get_symbol_fn(X86_KERNEL_PHYS_BASE_NAME.as_ptr());
        }
    }
}

#[no_mangle]
pub extern "C" fn mck_crash_range_filter_result(
    start: usize,
    end: usize,
    match_addr: usize,
) -> i32 {
    if match_addr == usize::MAX {
        return 0;
    }
    if start > match_addr {
        return 1;
    }
    if end <= match_addr {
        return -1;
    }
    0
}

#[no_mangle]
pub extern "C" fn mck_crash_x86_pte_is_type_page_result(
    pte: usize,
    level: i32,
    page_pse: usize,
) -> i32 {
    (level == 1 || ((level == 2 || level == 3) && (pte & page_pse) != 0)) as i32
}

#[no_mangle]
pub extern "C" fn mck_crash_arm64_pte_is_type_page_result(
    pte: usize,
    level: i32,
    pte_type_mask: usize,
    pte_type_page: usize,
    pmd_type_mask: usize,
    pmd_type_sect: usize,
) -> i32 {
    if level == 1 {
        (pte & pte_type_mask == pte_type_page) as i32
    } else {
        (pte & pmd_type_mask == pmd_type_sect) as i32
    }
}

#[no_mangle]
pub extern "C" fn mck_crash_ptl_shift_result(
    level: i32,
    l1: i32,
    l2: i32,
    l3: i32,
    l4: i32,
) -> i32 {
    match level {
        1 => l1,
        2 => l2,
        3 => l3,
        4 => l4,
        _ => -1,
    }
}

#[no_mangle]
pub extern "C" fn mck_crash_pte_phys_result(
    pte: usize,
    virt: usize,
    pgshift: i32,
    mask: usize,
) -> usize {
    let offset_mask = if pgshift <= 0 || pgshift >= usize::BITS as i32 {
        0
    } else {
        (1usize << pgshift) - 1
    };
    (pte & mask).wrapping_add(virt & offset_mask)
}

#[no_mangle]
pub extern "C" fn mck_crash_x86_sign_extend_result(virt: usize) -> usize {
    if virt >= 0x0000_8000_0000_0000usize {
        virt | 0xffff_0000_0000_0000usize
    } else {
        virt
    }
}

#[no_mangle]
pub extern "C" fn mck_crash_pte_should_skip_result(
    pte: usize,
    prev_pte: usize,
    attr_mask: usize,
    pgshift: i32,
    prev_pgshift: i32,
    virt: usize,
    prev_virt: usize,
) -> i32 {
    if pgshift < 0 || pgshift >= usize::BITS as i32 {
        return 0;
    }
    let step = 1usize << pgshift;
    ((pte & attr_mask) == (prev_pte & attr_mask)
        && pgshift == prev_pgshift
        && virt == prev_virt.wrapping_add(step)) as i32
}

#[no_mangle]
pub extern "C" fn mck_crash_pte_lookup_range_result(
    addr: usize,
    virt: usize,
    index: usize,
    level_shift: i32,
    nonfixed_mask: usize,
) -> i32 {
    if level_shift < 0 || level_shift >= usize::BITS as i32 {
        return 0;
    }

    let masked_addr = addr & nonfixed_mask;
    let masked_virt = virt & nonfixed_mask;
    let next = masked_virt.wrapping_add((index + 1) << level_shift);
    if masked_addr >= next {
        return 1;
    }

    let current = masked_virt.wrapping_add(index << level_shift);
    if masked_addr < current {
        return -1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_x86_pte_flags_result(
    buf: *mut u8,
    buf_size: usize,
    pte: usize,
    rw: usize,
    user: usize,
    pwt: usize,
    pcd: usize,
    accessed: usize,
    dirty: usize,
    global: usize,
    nx: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let mut written_flags = 0usize;
    let ok = unsafe {
        (pte & rw == 0
            || append_flag_label(
                buf,
                &mut pos,
                buf_size,
                b"RW\0".as_ptr(),
                &mut written_flags,
            ))
            && (pte & user == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"USER\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & pwt == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"PWT\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & pcd == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"PCD\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & accessed == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"ACCESSED\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & dirty == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"DIRTY\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & global == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"GLOBAL\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & nx == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"NX\0".as_ptr(),
                    &mut written_flags,
                ))
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mck_crash_arm64_pte_flags_result(
    buf: *mut u8,
    buf_size: usize,
    pte: usize,
    valid: usize,
    user: usize,
    rdonly: usize,
    shared: usize,
    af: usize,
    ng: usize,
    pxn: usize,
    uxn: usize,
    dirty: usize,
    special: usize,
    write: usize,
    cont: usize,
    prot_none: usize,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let mut written_flags = 0usize;
    let ok = unsafe {
        (pte & valid == 0
            || append_flag_label(
                buf,
                &mut pos,
                buf_size,
                b"VALID\0".as_ptr(),
                &mut written_flags,
            ))
            && (pte & user == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"USER\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & rdonly == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"RDONLY\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & shared == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"SHARED\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & af == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"AF\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & ng == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"NG\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & pxn == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"PXN\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & uxn == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"UXN\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & dirty == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"DIRTY\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & special == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"SPECIAL\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & write == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"WRITE\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & cont == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"CONT\0".as_ptr(),
                    &mut written_flags,
                ))
            && (pte & prot_none == 0
                || append_flag_label(
                    buf,
                    &mut pos,
                    buf_size,
                    b"PROT_NONE\0".as_ptr(),
                    &mut written_flags,
                ))
            && (written_flags != 0 || write_usize_hex_checked(buf, &mut pos, buf_size, pte))
    };
    unsafe {
        finish_cstr_checked(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub extern "C" fn mck_crash_kmsg_wrap_result(head: i32, tail: i32) -> i32 {
    (tail < head) as i32
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
