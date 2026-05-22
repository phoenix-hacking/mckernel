#![no_std]

use core::panic::PanicInfo;

const PS_RUNNING: i32 = 0x1;
const PS_INTERRUPTIBLE: i32 = 0x2;
const PS_UNINTERRUPTIBLE: i32 = 0x4;
const PS_ZOMBIE: i32 = 0x8;
const PS_EXITED: i32 = 0x10;
const PS_STOPPED: i32 = 0x20;

const MCINSPECT_DWARF_FORM_UNSIGNED: i32 = 1;
const MCINSPECT_DWARF_FORM_SIGNED: i32 = 2;
const MCINSPECT_DWARF_FORM_LOCLIST: i32 = 3;
const MCINSPECT_DWARF_FORM_EXPRLOC: i32 = 4;
const MCINSPECT_DWARF_FORM_UNSUPPORTED: i32 = -1;

static STATUS_RUNNING: &[u8] = b"R\0";
static STATUS_INTERRUPTIBLE: &[u8] = b"IN\0";
static STATUS_UNINTERRUPTIBLE: &[u8] = b"UN\0";
static STATUS_ZOMBIE: &[u8] = b"Z\0";
static STATUS_EXITED: &[u8] = b"E\0";
static STATUS_STOPPED: &[u8] = b"S\0";
static STATUS_UNKNOWN: &[u8] = b"U\0";
static THREAD_ACTIVE: &[u8] = b">\0";
static THREAD_INACTIVE: &[u8] = b" \0";
static THREAD_IDLE: &[u8] = b"(idle)\0";
static THREAD_UNKNOWN: &[u8] = b"(unknown)\0";

fn is_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

fn ascii_lower(byte: u8) -> u8 {
    if byte.is_ascii_uppercase() {
        byte + 32
    } else {
        byte
    }
}

unsafe fn cstr_case_eq(lhs: *const u8, rhs: *const u8) -> bool {
    if lhs.is_null() || rhs.is_null() {
        return false;
    }

    let mut idx = 0usize;
    loop {
        let l = unsafe { *lhs.add(idx) };
        let r = unsafe { *rhs.add(idx) };

        if ascii_lower(l) != ascii_lower(r) {
            return false;
        }
        if l == 0 {
            return true;
        }

        idx += 1;
    }
}

unsafe fn cstr_basename(path: *const u8) -> *const u8 {
    if path.is_null() {
        return THREAD_UNKNOWN.as_ptr();
    }

    let mut ptr = path;
    let mut base = path;
    loop {
        let byte = unsafe { *ptr };
        if byte == 0 {
            break;
        }
        if byte == b'/' {
            base = unsafe { ptr.add(1) };
        }
        ptr = unsafe { ptr.add(1) };
    }

    if unsafe { *base } == 0 {
        path
    } else {
        base
    }
}

fn hex_value(byte: u8) -> Option<usize> {
    match byte {
        b'0'..=b'9' => Some((byte - b'0') as usize),
        b'a'..=b'f' => Some((byte - b'a' + 10) as usize),
        b'A'..=b'F' => Some((byte - b'A' + 10) as usize),
        _ => None,
    }
}

unsafe fn write_byte(buf: *mut u8, pos: &mut usize, byte: u8) {
    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
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

#[no_mangle]
pub unsafe extern "C" fn mcinspect_thread_status_label_result(status: i32) -> *const u8 {
    if status == PS_RUNNING {
        STATUS_RUNNING.as_ptr()
    } else if status == PS_INTERRUPTIBLE {
        STATUS_INTERRUPTIBLE.as_ptr()
    } else if status == PS_UNINTERRUPTIBLE {
        STATUS_UNINTERRUPTIBLE.as_ptr()
    } else if status == PS_ZOMBIE {
        STATUS_ZOMBIE.as_ptr()
    } else if status == PS_EXITED {
        STATUS_EXITED.as_ptr()
    } else if status == PS_STOPPED {
        STATUS_STOPPED.as_ptr()
    } else {
        STATUS_UNKNOWN.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_thread_active_marker_result(active: i32) -> *const u8 {
    if active != 0 {
        THREAD_ACTIVE.as_ptr()
    } else {
        THREAD_INACTIVE.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_thread_comm_result(
    cmd_line: *const u8,
    is_idle: i32,
) -> *const u8 {
    if !cmd_line.is_null() {
        unsafe { cstr_basename(cmd_line) }
    } else if is_idle != 0 {
        THREAD_IDLE.as_ptr()
    } else {
        THREAD_UNKNOWN.as_ptr()
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_parse_pid_result(arg: *const u8) -> i32 {
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
pub unsafe extern "C" fn mcinspect_parse_vtop_addr_result(arg: *const u8, out: *mut usize) -> i32 {
    if out.is_null() {
        return -1;
    }

    if arg.is_null() {
        return -1;
    }

    let mut ptr = arg;
    let mut byte = unsafe { *ptr };
    while byte != 0 && is_space(byte) {
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    if byte == b'0' {
        let next = unsafe { *ptr.add(1) };
        if next == b'x' || next == b'X' {
            ptr = unsafe { ptr.add(2) };
            byte = unsafe { *ptr };
        }
    }

    let mut saw_digit = false;
    let mut value = 0usize;
    while byte != 0 {
        let Some(digit) = hex_value(byte) else {
            break;
        };
        saw_digit = true;
        value = value.wrapping_mul(16).wrapping_add(digit);
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    if !saw_digit || value == 0 {
        return -1;
    }

    unsafe {
        *out = value;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_need_action_result(ps: i32, vtop: i32) -> i32 {
    if ps != 0 || vtop != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_mcos_path_result(path: *mut u8, index: i32) -> i32 {
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
pub unsafe extern "C" fn mcinspect_dwarf_size_form_action_result(
    form: u32,
    data1: u32,
    data2: u32,
    data4: u32,
    data8: u32,
    udata: u32,
    sdata: u32,
) -> i32 {
    if form == data1 || form == data2 || form == data4 || form == data8 || form == udata {
        MCINSPECT_DWARF_FORM_UNSIGNED
    } else if form == sdata {
        MCINSPECT_DWARF_FORM_SIGNED
    } else {
        MCINSPECT_DWARF_FORM_LOCLIST
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_signed_nonnegative_result(value: i64) -> i32 {
    if value >= 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_plus_uconst_expr_result(
    len: isize,
    cents: isize,
    atom: u32,
    plus_uconst: u32,
) -> i32 {
    if len == 1 && cents == 1 && atom == plus_uconst {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_named_tag_match_result(
    tag: u32,
    expected_tag: u32,
    name: *const u8,
    expected_name: *const u8,
) -> i32 {
    if tag == expected_tag && unsafe { cstr_case_eq(name, expected_name) } {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_addr_form_action_result(
    form: u32,
    block1: u32,
    block2: u32,
    block4: u32,
    block: u32,
    data4: u32,
    data8: u32,
    sec_offset: u32,
    exprloc: u32,
) -> i32 {
    if form == block1
        || form == block2
        || form == block4
        || form == block
        || form == data4
        || form == data8
        || form == sec_offset
    {
        MCINSPECT_DWARF_FORM_LOCLIST
    } else if form == exprloc {
        MCINSPECT_DWARF_FORM_EXPRLOC
    } else {
        MCINSPECT_DWARF_FORM_UNSUPPORTED
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_addr_expr_result(
    len: isize,
    cents: isize,
    atom: u32,
    op_addr: u32,
) -> i32 {
    if len == 1 && cents == 1 && atom == op_addr {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_cpu_local_base_result(
    clv: usize,
    clv_size: usize,
    cpu: i32,
) -> usize {
    clv.wrapping_add(clv_size.wrapping_mul(cpu as usize))
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_thread_from_sched_list_result(
    thread_sched_list: usize,
    thread_sched_list_offset: usize,
) -> usize {
    thread_sched_list.wrapping_sub(thread_sched_list_offset)
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_mcvtop_should_lookup_proc_result(pid: i32) -> i32 {
    if pid != 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_vtop_has_process_result(proc: usize) -> i32 {
    if proc != 0 {
        1
    } else {
        0
    }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
