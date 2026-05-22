#![no_std]

use core::panic::PanicInfo;

const PS_RUNNING: i32 = 0x01;
const PS_INTERRUPTIBLE: i32 = 0x02;
const PS_UNINTERRUPTIBLE: i32 = 0x04;
const PS_STOPPED: i32 = 0x20;
const PS_TRACED: i32 = 0x40;
const CS_IDLE: i32 = 0x010000;
const CS_RUNNING: i32 = 0x020000;
const CS_RESERVED: i32 = 0x030000;

static REPLY_OK: &[u8] = b"OK\0";
static REPLY_S02: &[u8] = b"S02\0";
static REPLY_S12: &[u8] = b"S12\0";
static REPLY_VCONT_C: &[u8] = b"vCont;c\0";
static REPLY_EMPTY: &[u8] = b"\0";

const ECLAIR_CMD_QSUPPORTED: i32 = 1;
const ECLAIR_CMD_HG: i32 = 2;
const ECLAIR_CMD_HC: i32 = 3;
const ECLAIR_CMD_VCTRLC: i32 = 4;
const ECLAIR_CMD_CTRLC: i32 = 5;
const ECLAIR_CMD_VCONT_QUERY: i32 = 6;
const ECLAIR_CMD_CONTINUE: i32 = 7;
const ECLAIR_CMD_STOP_QUERY: i32 = 8;
const ECLAIR_CMD_QC: i32 = 9;
const ECLAIR_CMD_QATTACHED: i32 = 10;
const ECLAIR_CMD_TARGET_XML: i32 = 11;
const ECLAIR_CMD_DETACH: i32 = 12;
const ECLAIR_CMD_REGS: i32 = 13;
const ECLAIR_CMD_MEMORY: i32 = 14;
const ECLAIR_CMD_QTSTATUS: i32 = 15;
const ECLAIR_CMD_MEMORY_MAP: i32 = 16;
const ECLAIR_CMD_THREAD_ALIVE: i32 = 17;
const ECLAIR_CMD_QFTHREADINFO: i32 = 18;
const ECLAIR_CMD_QSTHREADINFO: i32 = 19;
const ECLAIR_CMD_QTHREAD_EXTRA_INFO: i32 = 20;

fn is_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

unsafe fn cstr_bytes<'a>(ptr: *const u8) -> Option<&'a [u8]> {
    if ptr.is_null() {
        return None;
    }

    let mut len = 0usize;
    while unsafe { *ptr.add(len) } != 0 {
        len += 1;
    }
    Some(unsafe { core::slice::from_raw_parts(ptr, len) })
}

fn byte_at(bytes: &[u8], idx: usize) -> u8 {
    unsafe { *bytes.as_ptr().add(idx) }
}

fn subslice(bytes: &[u8], start: usize, end: usize) -> &[u8] {
    unsafe { core::slice::from_raw_parts(bytes.as_ptr().add(start), end - start) }
}

fn bytes_eq(bytes: &[u8], literal: &[u8]) -> bool {
    if bytes.len() != literal.len() {
        return false;
    }

    let mut idx = 0usize;
    while idx < bytes.len() {
        if byte_at(bytes, idx) != byte_at(literal, idx) {
            return false;
        }
        idx += 1;
    }
    true
}

fn bytes_starts_with(bytes: &[u8], literal: &[u8]) -> bool {
    if bytes.len() < literal.len() {
        return false;
    }

    let mut idx = 0usize;
    while idx < literal.len() {
        if byte_at(bytes, idx) != byte_at(literal, idx) {
            return false;
        }
        idx += 1;
    }
    true
}

fn hex_value(byte: u8) -> Option<usize> {
    match byte {
        b'0'..=b'9' => Some((byte - b'0') as usize),
        b'a'..=b'f' => Some((byte - b'a' + 10) as usize),
        b'A'..=b'F' => Some((byte - b'A' + 10) as usize),
        _ => None,
    }
}

fn parse_hex_usize_prefix(bytes: &[u8]) -> Option<(usize, usize)> {
    let mut idx = 0usize;
    while idx < bytes.len() && is_space(byte_at(bytes, idx)) {
        idx += 1;
    }

    if idx + 1 < bytes.len()
        && byte_at(bytes, idx) == b'0'
        && (byte_at(bytes, idx + 1) == b'x' || byte_at(bytes, idx + 1) == b'X')
    {
        idx += 2;
    }

    let start = idx;
    let mut value = 0usize;
    while idx < bytes.len() {
        let Some(digit) = hex_value(byte_at(bytes, idx)) else {
            break;
        };
        value = value.wrapping_mul(16).wrapping_add(digit);
        idx += 1;
    }

    if idx == start {
        None
    } else {
        Some((value, idx))
    }
}

fn hex_digit(nibble: u8) -> u8 {
    if nibble < 10 {
        b'0' + nibble
    } else {
        b'a' + (nibble - 10)
    }
}

unsafe fn write_byte(buf: *mut u8, pos: &mut usize, byte: u8) {
    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
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

unsafe fn write_lit_checked(buf: *mut u8, pos: &mut usize, buf_size: usize, lit: &[u8]) -> bool {
    let mut i = 0usize;
    while i < lit.len() {
        let byte = unsafe { *lit.as_ptr().add(i) };
        if byte == 0 {
            return true;
        }
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        i += 1;
    }
    true
}

unsafe fn write_cstr_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    ptr: *const u8,
) -> bool {
    let Some(bytes) = (unsafe { cstr_bytes(ptr) }) else {
        return false;
    };

    let mut idx = 0usize;
    while idx < bytes.len() {
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte_at(bytes, idx)) } {
            return false;
        }
        idx += 1;
    }
    true
}

unsafe fn finish_cstr(buf: *mut u8, pos: usize, buf_size: usize) {
    if buf_size == 0 {
        return;
    }
    let term = if pos < buf_size { pos } else { buf_size - 1 };
    unsafe {
        *buf.add(term) = 0;
    }
}

unsafe fn write_i32_decimal(buf: *mut u8, pos: &mut usize, value: i32) {
    let mut value64 = value as i64;
    if value64 < 0 {
        unsafe {
            write_byte(buf, pos, b'-');
        }
        value64 = value64.wrapping_neg();
    }

    let mut value = value64 as u64;
    if value == 0 {
        unsafe {
            write_byte(buf, pos, b'0');
        }
        return;
    }

    let mut digits = [0u8; 20];
    let mut count = 0usize;
    while value != 0 {
        unsafe {
            *digits.as_mut_ptr().add(count) = b'0' + (value % 10) as u8;
        }
        count += 1;
        value /= 10;
    }

    while count != 0 {
        count -= 1;
        let digit = unsafe { *digits.as_ptr().add(count) };
        unsafe {
            write_byte(buf, pos, digit);
        }
    }
}

unsafe fn write_i32_decimal_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: i32,
) -> bool {
    let mut value64 = value as i64;
    if value64 < 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b'-') } {
            return false;
        }
        value64 = value64.wrapping_neg();
    }

    let mut value = value64 as u64;
    if value == 0 {
        return unsafe { write_byte_checked(buf, pos, buf_size, b'0') };
    }

    let mut digits = [0u8; 20];
    let mut count = 0usize;
    while value != 0 {
        unsafe {
            *digits.as_mut_ptr().add(count) = b'0' + (value % 10) as u8;
        }
        count += 1;
        value /= 10;
    }

    while count != 0 {
        count -= 1;
        let digit = unsafe { *digits.as_ptr().add(count) };
        if !unsafe { write_byte_checked(buf, pos, buf_size, digit) } {
            return false;
        }
    }
    true
}

unsafe fn write_u16_decimal_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    mut value: u32,
) -> bool {
    if value == 0 {
        return unsafe { write_byte_checked(buf, pos, buf_size, b'0') };
    }

    let mut digits = [0u8; 10];
    let mut count = 0usize;
    while value != 0 {
        unsafe {
            *digits.as_mut_ptr().add(count) = b'0' + (value % 10) as u8;
        }
        count += 1;
        value /= 10;
    }

    while count != 0 {
        count -= 1;
        let digit = unsafe { *digits.as_ptr().add(count) };
        if !unsafe { write_byte_checked(buf, pos, buf_size, digit) } {
            return false;
        }
    }
    true
}

unsafe fn write_hex_i32_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: i32,
) -> bool {
    let value = value as u32;
    if value == 0 {
        return unsafe { write_byte_checked(buf, pos, buf_size, b'0') };
    }
    if !unsafe { write_lit_checked(buf, pos, buf_size, b"0x\0") } {
        return false;
    }

    let mut shift = 28i32;
    while shift > 0 && ((value >> shift) & 0xf) == 0 {
        shift -= 4;
    }
    while shift >= 0 {
        let digit = hex_digit(((value >> shift) & 0xf) as u8);
        if !unsafe { write_byte_checked(buf, pos, buf_size, digit) } {
            return false;
        }
        shift -= 4;
    }
    true
}

unsafe fn write_hex_usize_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: usize,
) -> bool {
    if value == 0 {
        return unsafe { write_byte_checked(buf, pos, buf_size, b'0') };
    }

    let mut shift = (usize::BITS as i32) - 4;
    while shift > 0 && ((value >> shift) & 0xf) == 0 {
        shift -= 4;
    }
    while shift >= 0 {
        let digit = hex_digit(((value >> shift) & 0xf) as u8);
        if !unsafe { write_byte_checked(buf, pos, buf_size, digit) } {
            return false;
        }
        shift -= 4;
    }
    true
}

unsafe fn write_hex_byte(buf: *mut u8, pos: &mut usize, byte: u8) {
    unsafe {
        write_byte(buf, pos, hex_digit(byte >> 4));
        write_byte(buf, pos, hex_digit(byte & 0xf));
    }
}

unsafe fn write_hex_byte_checked(buf: *mut u8, pos: &mut usize, buf_size: usize, byte: u8) -> bool {
    unsafe {
        write_byte_checked(buf, pos, buf_size, hex_digit(byte >> 4))
            && write_byte_checked(buf, pos, buf_size, hex_digit(byte & 0xf))
    }
}

unsafe fn write_arch_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    arch: *const u8,
) -> bool {
    if arch.is_null() {
        return false;
    }

    let mut ptr = arch;
    let mut byte = unsafe { *ptr };
    while byte != 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }
    true
}

#[no_mangle]
pub unsafe extern "C" fn eclair_parse_i32_result(arg: *const u8) -> i32 {
    if arg.is_null() {
        return 0;
    }

    let mut ptr = arg;
    let mut byte = unsafe { *ptr };
    while byte != 0 && is_space(byte) {
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    let mut neg = false;
    if byte == b'-' {
        neg = true;
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    } else if byte == b'+' {
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    let mut value = 0i32;
    while byte.is_ascii_digit() {
        value = value
            .saturating_mul(10)
            .saturating_add((byte - b'0') as i32);
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    if neg {
        value.saturating_neg()
    } else {
        value
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_gdb_command_kind_result(cmd: *const u8, interactive: i32) -> i32 {
    let Some(bytes) = (unsafe { cstr_bytes(cmd) }) else {
        return 0;
    };

    if bytes_starts_with(bytes, b"qSupported") {
        ECLAIR_CMD_QSUPPORTED
    } else if bytes_starts_with(bytes, b"Hg") {
        ECLAIR_CMD_HG
    } else if bytes_starts_with(bytes, b"Hc") {
        ECLAIR_CMD_HC
    } else if interactive != 0 && bytes_eq(bytes, b"vCtrlC") {
        ECLAIR_CMD_VCTRLC
    } else if interactive != 0 && bytes_eq(bytes, b"Ctrl-C") {
        ECLAIR_CMD_CTRLC
    } else if bytes_eq(bytes, b"vCont?") {
        ECLAIR_CMD_VCONT_QUERY
    } else if bytes_eq(bytes, b"c") {
        ECLAIR_CMD_CONTINUE
    } else if bytes_eq(bytes, b"?") {
        ECLAIR_CMD_STOP_QUERY
    } else if bytes_eq(bytes, b"qC") {
        ECLAIR_CMD_QC
    } else if bytes_eq(bytes, b"qAttached") {
        ECLAIR_CMD_QATTACHED
    } else if bytes_starts_with(bytes, b"qXfer:features:read:target.xml:") {
        ECLAIR_CMD_TARGET_XML
    } else if bytes_eq(bytes, b"D") {
        ECLAIR_CMD_DETACH
    } else if bytes_eq(bytes, b"g") {
        ECLAIR_CMD_REGS
    } else if bytes_starts_with(bytes, b"m") {
        ECLAIR_CMD_MEMORY
    } else if bytes_eq(bytes, b"qTStatus") {
        ECLAIR_CMD_QTSTATUS
    } else if bytes_starts_with(bytes, b"qXfer:memory-map:read::") {
        ECLAIR_CMD_MEMORY_MAP
    } else if bytes_starts_with(bytes, b"T") {
        ECLAIR_CMD_THREAD_ALIVE
    } else if bytes_eq(bytes, b"qfThreadInfo") {
        ECLAIR_CMD_QFTHREADINFO
    } else if bytes_eq(bytes, b"qsThreadInfo") {
        ECLAIR_CMD_QSTHREADINFO
    } else if bytes_starts_with(bytes, b"qThreadExtraInfo,") {
        ECLAIR_CMD_QTHREAD_EXTRA_INFO
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_parse_hex_i32_result(arg: *const u8, out: *mut i32) -> i32 {
    if out.is_null() {
        return -1;
    }
    let Some(bytes) = (unsafe { cstr_bytes(arg) }) else {
        return -1;
    };
    let Some((value, _end)) = parse_hex_usize_prefix(bytes) else {
        return -1;
    };

    unsafe {
        *out = value as i32;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn eclair_parse_memory_request_result(
    cmd: *const u8,
    start_out: *mut usize,
    size_out: *mut usize,
) -> i32 {
    if start_out.is_null() || size_out.is_null() {
        return -1;
    }
    let Some(bytes) = (unsafe { cstr_bytes(cmd) }) else {
        return -1;
    };
    if !bytes_starts_with(bytes, b"m") {
        return -1;
    }

    let Some((start, end)) = parse_hex_usize_prefix(subslice(bytes, 1, bytes.len())) else {
        return -1;
    };
    if end + 1 >= bytes.len() || byte_at(bytes, end + 1) != b',' {
        return -1;
    }

    let Some((size, _size_end)) = parse_hex_usize_prefix(subslice(bytes, end + 2, bytes.len()))
    else {
        return -1;
    };
    unsafe {
        *start_out = start;
        *size_out = size;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn eclair_response_checksum_result(payload: *const u8) -> u8 {
    if payload.is_null() {
        return 0;
    }

    let mut ptr = payload;
    let mut sum = 0u8;
    let mut byte = unsafe { *ptr };
    while byte != 0 {
        sum = sum.wrapping_add(byte);
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }
    sum
}

#[no_mangle]
pub unsafe extern "C" fn eclair_parse_packet_checksum_result(hex: *const u8, out: *mut u8) -> i32 {
    if hex.is_null() || out.is_null() {
        return -1;
    }

    let hi = unsafe { *hex };
    let lo = unsafe { *hex.add(1) };
    let Some(hi) = hex_value(hi) else {
        return -1;
    };
    let Some(lo) = hex_value(lo) else {
        return -1;
    };

    unsafe {
        *out = ((hi << 4) | lo) as u8;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn eclair_interrupt_command_result(buf: *mut u8, buf_size: usize) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe { write_lit_checked(buf, &mut pos, buf_size, b"Ctrl-C\0") };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_physmem_name_result(path: *mut u8, index: i32) -> i32 {
    if path.is_null() {
        return 0;
    }

    let mut pos = 0usize;
    unsafe {
        write_byte(path, &mut pos, b'p');
        write_byte(path, &mut pos, b'h');
        write_byte(path, &mut pos, b'y');
        write_byte(path, &mut pos, b's');
        write_byte(path, &mut pos, b'm');
        write_byte(path, &mut pos, b'e');
        write_byte(path, &mut pos, b'm');
        write_i32_decimal(path, &mut pos, index);
        *path.add(pos) = 0;
    }
    pos as i32
}

#[no_mangle]
pub unsafe extern "C" fn eclair_mcos_path_result(path: *mut u8, index: i32) -> i32 {
    if path.is_null() {
        return 0;
    }

    let mut pos = 0usize;
    unsafe {
        write_byte(path, &mut pos, b'/');
        write_byte(path, &mut pos, b'd');
        write_byte(path, &mut pos, b'e');
        write_byte(path, &mut pos, b'v');
        write_byte(path, &mut pos, b'/');
        write_byte(path, &mut pos, b'm');
        write_byte(path, &mut pos, b'c');
        write_byte(path, &mut pos, b'o');
        write_byte(path, &mut pos, b's');
        write_i32_decimal(path, &mut pos, index);
        *path.add(pos) = 0;
    }
    pos as i32
}

#[no_mangle]
pub unsafe extern "C" fn eclair_print_hex_result(
    buf: *mut u8,
    buf_size: usize,
    str_ptr: *const u8,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    if str_ptr.is_null() {
        return -1;
    }

    let mut pos = 0usize;
    let mut ptr = str_ptr;
    let mut byte = unsafe { *ptr };
    while byte != 0 {
        if pos + 2 >= buf_size {
            return -1;
        }
        unsafe {
            write_hex_byte(buf, &mut pos, byte);
        }
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }
    unsafe {
        *buf.add(pos) = 0;
    }
    pos as isize
}

#[no_mangle]
pub unsafe extern "C" fn eclair_print_bin_result(
    buf: *mut u8,
    buf_size: usize,
    data: *const u8,
    size: usize,
) -> isize {
    if buf.is_null() || data.is_null() || buf_size == 0 {
        return -1;
    }

    let needed = size.saturating_mul(2);
    if needed >= buf_size {
        return -1;
    }

    let mut pos = 0usize;
    let mut idx = 0usize;
    while idx < size {
        if pos + 2 >= buf_size {
            return -1;
        }
        unsafe {
            write_hex_byte(buf, &mut pos, *data.add(idx));
        }
        idx += 1;
    }
    unsafe {
        *buf.add(pos) = 0;
    }
    pos as isize
}

#[no_mangle]
pub unsafe extern "C" fn eclair_hc_reply_result(interactive: i32) -> *const u8 {
    if interactive != 0 {
        REPLY_OK.as_ptr()
    } else {
        REPLY_S02.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_continue_reply_result(interactive: i32) -> *const u8 {
    if interactive != 0 {
        REPLY_OK.as_ptr()
    } else {
        REPLY_S02.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_stop_reply_result(
    interactive: i32,
    remote_running: i32,
) -> *const u8 {
    if interactive != 0 && remote_running != 0 {
        REPLY_S12.as_ptr()
    } else {
        REPLY_S02.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_vcont_reply_result(interactive: i32) -> *const u8 {
    if interactive != 0 {
        REPLY_VCONT_C.as_ptr()
    } else {
        REPLY_EMPTY.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_simple_response_result(
    buf: *mut u8,
    buf_size: usize,
    cmd_kind: i32,
    interactive: i32,
    remote_running: i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        match cmd_kind {
            ECLAIR_CMD_HG | ECLAIR_CMD_VCTRLC | ECLAIR_CMD_DETACH | ECLAIR_CMD_THREAD_ALIVE => {
                write_lit_checked(buf, &mut pos, buf_size, b"OK\0")
            }
            ECLAIR_CMD_CTRLC => write_lit_checked(buf, &mut pos, buf_size, b"S02\0"),
            ECLAIR_CMD_HC | ECLAIR_CMD_CONTINUE => {
                if interactive != 0 {
                    write_lit_checked(buf, &mut pos, buf_size, b"OK\0")
                } else {
                    write_lit_checked(buf, &mut pos, buf_size, b"S02\0")
                }
            }
            ECLAIR_CMD_STOP_QUERY => {
                if interactive != 0 && remote_running != 0 {
                    write_lit_checked(buf, &mut pos, buf_size, b"S12\0")
                } else {
                    write_lit_checked(buf, &mut pos, buf_size, b"S02\0")
                }
            }
            ECLAIR_CMD_VCONT_QUERY => {
                if interactive != 0 {
                    write_lit_checked(buf, &mut pos, buf_size, b"vCont;c\0")
                } else {
                    true
                }
            }
            _ => false,
        }
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_gdb_target_result(
    buf: *mut u8,
    buf_size: usize,
    port: u32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(buf, &mut pos, buf_size, b"target remote :\0")
            && write_u16_decimal_checked(buf, &mut pos, buf_size, port)
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_packet_frame_result(
    buf: *mut u8,
    buf_size: usize,
    payload: *const u8,
) -> isize {
    if buf.is_null() || buf_size == 0 || payload.is_null() {
        return -1;
    }

    let checksum = unsafe { eclair_response_checksum_result(payload) };
    let mut pos = 0usize;
    let ok = unsafe {
        write_byte_checked(buf, &mut pos, buf_size, b'$')
            && write_cstr_checked(buf, &mut pos, buf_size, payload)
            && write_byte_checked(buf, &mut pos, buf_size, b'#')
            && write_hex_byte_checked(buf, &mut pos, buf_size, checksum)
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_banner_result(
    buf: *mut u8,
    buf_size: usize,
    interactive: i32,
    dump_path: *const u8,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(buf, &mut pos, buf_size, b"eclair 0.20160314 \0")
            && if interactive != 0 {
                write_lit_checked(buf, &mut pos, buf_size, b"live debug mode\0")
            } else {
                write_lit_checked(buf, &mut pos, buf_size, b"using dump file: \0")
                    && write_cstr_checked(buf, &mut pos, buf_size, dump_path)
            }
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_usage_result(buf: *mut u8, buf_size: usize) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(
            buf,
            &mut pos,
            buf_size,
            b"usage: eclair [-ch] [-d <mcdump>] [-k <kernel.img>]\0",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_open_mcos_error_result(
    buf: *mut u8,
    buf_size: usize,
    file: *const u8,
    line: i32,
    os_id: i32,
    errno: i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_cstr_checked(buf, &mut pos, buf_size, file)
            && write_lit_checked(buf, &mut pos, buf_size, b":\0")
            && write_i32_decimal_checked(buf, &mut pos, buf_size, line)
            && write_lit_checked(buf, &mut pos, buf_size, b" error: opening /dev/mcos\0")
            && write_i32_decimal_checked(buf, &mut pos, buf_size, os_id)
            && write_lit_checked(buf, &mut pos, buf_size, b", errno: \0")
            && write_i32_decimal_checked(buf, &mut pos, buf_size, errno)
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_read_physmem_invalid_result(
    buf: *mut u8,
    buf_size: usize,
    pa: usize,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_lit_checked(buf, &mut pos, buf_size, b"read_physmem: invalid addr 0x\0")
            && write_hex_usize_checked(buf, &mut pos, buf_size, pa)
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_lookup_failed_result(
    buf: *mut u8,
    buf_size: usize,
    func: *const u8,
    name: *const u8,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        write_cstr_checked(buf, &mut pos, buf_size, func)
            && write_lit_checked(buf, &mut pos, buf_size, b"(\0")
            && write_cstr_checked(buf, &mut pos, buf_size, name)
            && write_lit_checked(buf, &mut pos, buf_size, b"):lookup_symbol failed\0")
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_thread_extra_info_result(
    buf: *mut u8,
    buf_size: usize,
    pid: i32,
    status: i32,
    idle: i32,
    lcpu: i32,
    cpu: i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let mut ok = unsafe {
        write_lit_checked(buf, &mut pos, buf_size, b"PID \0")
            && write_i32_decimal_checked(buf, &mut pos, buf_size, pid)
            && write_lit_checked(buf, &mut pos, buf_size, b", \0")
    };

    if ok {
        ok = unsafe {
            if status & PS_RUNNING != 0 {
                (idle == 0 || write_lit_checked(buf, &mut pos, buf_size, b"idle \0"))
                    && write_lit_checked(buf, &mut pos, buf_size, b"running on CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, lcpu)
            } else if status & (PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE) != 0 {
                (idle == 0 || write_lit_checked(buf, &mut pos, buf_size, b"idle \0"))
                    && write_lit_checked(buf, &mut pos, buf_size, b"waiting on CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, lcpu)
            } else if status & PS_STOPPED != 0 {
                (idle == 0 || write_lit_checked(buf, &mut pos, buf_size, b"idle \0"))
                    && write_lit_checked(buf, &mut pos, buf_size, b"stopped on CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, lcpu)
            } else if status & PS_TRACED != 0 {
                (idle == 0 || write_lit_checked(buf, &mut pos, buf_size, b"idle \0"))
                    && write_lit_checked(buf, &mut pos, buf_size, b"traced on CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, lcpu)
            } else if status == CS_IDLE {
                write_lit_checked(buf, &mut pos, buf_size, b"CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, cpu)
                    && write_lit_checked(buf, &mut pos, buf_size, b" idle\0")
            } else if status == CS_RUNNING {
                write_lit_checked(buf, &mut pos, buf_size, b"CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, cpu)
                    && write_lit_checked(buf, &mut pos, buf_size, b" running\0")
            } else if status == CS_RESERVED {
                write_lit_checked(buf, &mut pos, buf_size, b"CPU \0")
                    && write_i32_decimal_checked(buf, &mut pos, buf_size, cpu)
                    && write_lit_checked(buf, &mut pos, buf_size, b" reserved\0")
            } else {
                write_lit_checked(buf, &mut pos, buf_size, b"status=\0")
                    && write_hex_i32_checked(buf, &mut pos, buf_size, status)
            }
        };
    }

    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_static_response_result(
    buf: *mut u8,
    buf_size: usize,
    cmd_kind: i32,
    current_tid: i32,
    map_kernel_start: usize,
    arch: *const u8,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        match cmd_kind {
            ECLAIR_CMD_QSUPPORTED => {
                write_lit_checked(buf, &mut pos, buf_size, b"PacketSize=1024\0")
                    && write_lit_checked(buf, &mut pos, buf_size, b";qXfer:features:read+\0")
            }
            ECLAIR_CMD_QC => {
                write_lit_checked(buf, &mut pos, buf_size, b"QC\0")
                    && write_hex_usize_checked(buf, &mut pos, buf_size, current_tid as u32 as usize)
            }
            ECLAIR_CMD_QATTACHED => write_lit_checked(buf, &mut pos, buf_size, b"1\0"),
            ECLAIR_CMD_TARGET_XML => {
                write_lit_checked(
                    buf,
                    &mut pos,
                    buf_size,
                    b"l<target version=\"1.0\"><architecture>\0",
                ) && write_arch_checked(buf, &mut pos, buf_size, arch)
                    && write_lit_checked(buf, &mut pos, buf_size, b"</architecture></target>\0")
            }
            ECLAIR_CMD_QTSTATUS => write_lit_checked(buf, &mut pos, buf_size, b"T0;tnotrun:0\0"),
            ECLAIR_CMD_MEMORY_MAP => {
                write_lit_checked(
                    buf,
                    &mut pos,
                    buf_size,
                    b"l<memory-map><memory type=\"rom\" start=\"0x\0",
                ) && write_hex_usize_checked(buf, &mut pos, buf_size, map_kernel_start)
                    && write_lit_checked(
                        buf,
                        &mut pos,
                        buf_size,
                        b"\" length=\"0x27000\"/></memory-map>\0",
                    )
            }
            ECLAIR_CMD_QSTHREADINFO => write_lit_checked(buf, &mut pos, buf_size, b"l\0"),
            _ => false,
        }
    };

    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_thread_list_entry_result(
    buf: *mut u8,
    buf_size: usize,
    first: i32,
    tid: i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let ok = unsafe {
        (if first != 0 {
            write_byte_checked(buf, &mut pos, buf_size, b'm')
        } else {
            write_byte_checked(buf, &mut pos, buf_size, b',')
        }) && write_hex_usize_checked(buf, &mut pos, buf_size, tid as u32 as usize)
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as isize
    } else {
        -1
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
