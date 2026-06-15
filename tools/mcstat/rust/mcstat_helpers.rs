#![no_std]

use core::panic::PanicInfo;

const MIB100: u64 = 100 * 1024 * 1024;
const MIB: u64 = 1024 * 1024;
const GIB: u64 = 1024 * 1024 * 1024;

const IHK_OS_MONITOR_NOT_BOOT: i32 = 0;
const IHK_OS_MONITOR_IDLE: i32 = 1;
const IHK_OS_MONITOR_USER: i32 = 2;
const IHK_OS_MONITOR_KERNEL: i32 = 3;
const IHK_OS_MONITOR_KERNEL_HEAVY: i32 = 4;
const IHK_OS_MONITOR_KERNEL_OFFLOAD: i32 = 5;
const IHK_OS_MONITOR_KERNEL_FREEZING: i32 = 8;
const IHK_OS_MONITOR_KERNEL_FROZEN: i32 = 9;
const IHK_OS_MONITOR_KERNEL_THAW: i32 = 10;
const IHK_OS_MONITOR_PANIC: i32 = 99;

const IHK_OS_STATUS_NOT_BOOTED: i32 = 0;
const IHK_OS_STATUS_BOOTING: i32 = 2;
const IHK_OS_STATUS_BOOTED: i32 = 3;
const IHK_OS_STATUS_READY: i32 = 4;
const IHK_OS_STATUS_RUNNING: i32 = 5;
const IHK_OS_STATUS_FREEZING: i32 = 6;
const IHK_OS_STATUS_FROZEN: i32 = 7;
const IHK_OS_STATUS_SHUTDOWN: i32 = 8;
const IHK_OS_STATUS_FAILED: i32 = 9;
const IHK_OS_STATUS_HUNGUP: i32 = 10;

const MCSTAT_MODE_STATS: i32 = 0;
const MCSTAT_MODE_CPU: i32 = 1;
const MCSTAT_MODE_STATUS: i32 = 2;
const MCSTAT_LOOP_DONE: i32 = 1;
const MCSTAT_LOOP_REPRINT: i32 = 2;

static MB: &[u8; 3] = b"MB\0";
static GB: &[u8; 3] = b"GB\0";
static NONE: &[u8; 5] = b"None\0";
static BOOTING_STATUS: &[u8; 8] = b"Booting\0";
static BOOTED: &[u8; 7] = b"Booted\0";
static READY: &[u8; 6] = b"Ready\0";
static RUNNING: &[u8; 8] = b"Running\0";
static FREEZING_STATUS: &[u8; 9] = b"Freezing\0";
static FROZEN_STATUS: &[u8; 7] = b"Frozen\0";
static SHUTDOWN: &[u8; 9] = b"Shutdown\0";
static PANIC_STATUS: &[u8; 6] = b"Panic\0";
static HANGUP: &[u8; 7] = b"Hangup\0";
static BOOT: &[u8; 5] = b"boot\0";
static IDLE: &[u8; 5] = b"idle\0";
static USER_MODE: &[u8; 10] = b"user mode\0";
static KERNEL_MODE: &[u8; 12] = b"kernel mode\0";
static OFFLOAD: &[u8; 8] = b"offload\0";
static FREEZING: &[u8; 9] = b"freezing\0";
static FROZEN: &[u8; 7] = b"frozen\0";
static THAW: &[u8; 5] = b"thaw\0";
static PANIC: &[u8; 6] = b"panic\0";
static EMPTY: &[u8; 1] = b"\0";
static UNKNOWN: &[u8; 8] = b"Unknown\0";

fn is_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
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

unsafe fn write_byte(buf: *mut u8, pos: &mut usize, byte: u8) {
    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
}

unsafe fn write_byte_checked(buf: *mut u8, pos: &mut usize, buf_size: usize, byte: u8) -> bool {
    if buf.is_null() || *pos + 1 >= buf_size {
        return false;
    }
    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
    true
}

unsafe fn finish_cstr(buf: *mut u8, pos: usize, buf_size: usize) {
    if !buf.is_null() && buf_size != 0 {
        let term = if pos < buf_size { pos } else { buf_size - 1 };
        unsafe {
            *buf.add(term) = 0;
        }
    }
}

unsafe fn write_bytes_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    bytes: &[u8],
) -> bool {
    let mut idx = 0usize;
    while idx < bytes.len() {
        if !unsafe { write_byte_checked(buf, pos, buf_size, *bytes.as_ptr().add(idx)) } {
            return false;
        }
        idx += 1;
    }
    true
}

unsafe fn write_cstr_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    ptr: *const u8,
) -> bool {
    let ptr = if ptr.is_null() { UNKNOWN.as_ptr() } else { ptr };
    let mut idx = 0usize;
    loop {
        let byte = unsafe { *ptr.add(idx) };
        if byte == 0 {
            return true;
        }
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        idx += 1;
    }
}

unsafe fn write_i64_decimal_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: i64,
) -> bool {
    let mut value = value;
    if value < 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b'-') } {
            return false;
        }
        value = value.wrapping_neg();
    }

    let mut value = value as u64;
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
        if !unsafe { write_byte_checked(buf, pos, buf_size, *digits.as_ptr().add(count)) } {
            return false;
        }
    }
    true
}

fn i64_decimal_width(value: i64) -> usize {
    let negative = value < 0;
    let mut mag = if negative {
        value.wrapping_neg() as u64
    } else {
        value as u64
    };
    let mut digits = 1usize;
    while mag >= 10 {
        digits += 1;
        mag /= 10;
    }
    digits + usize::from(negative)
}

unsafe fn write_i64_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: i64,
    width: usize,
) -> bool {
    let mut pad = width.saturating_sub(i64_decimal_width(value));
    while pad != 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b' ') } {
            return false;
        }
        pad -= 1;
    }
    unsafe { write_i64_decimal_checked(buf, pos, buf_size, value) }
}

unsafe fn write_cstr_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    ptr: *const u8,
    width: usize,
) -> bool {
    let ptr = if ptr.is_null() { UNKNOWN.as_ptr() } else { ptr };
    let mut pad = width.saturating_sub(unsafe { cstr_len(ptr) });
    while pad != 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b' ') } {
            return false;
        }
        pad -= 1;
    }
    unsafe { write_cstr_checked(buf, pos, buf_size, ptr) }
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

unsafe fn sum_ulongs(values: *const u64, count: i32) -> u64 {
    if values.is_null() || count <= 0 {
        return 0;
    }

    let mut total = 0u64;
    let mut idx = 0usize;
    while idx < count as usize {
        total = total.wrapping_add(unsafe { *values.add(idx) });
        idx += 1;
    }
    total
}

#[no_mangle]
pub extern "C" fn mcstat_memory_scale_result(max_usage: u64) -> u64 {
    if max_usage < MIB100 {
        MIB
    } else {
        GIB
    }
}

#[no_mangle]
pub extern "C" fn mcstat_memory_unit_result(max_usage: u64) -> *const u8 {
    if max_usage < MIB100 {
        MB.as_ptr()
    } else {
        GB.as_ptr()
    }
}

#[no_mangle]
pub extern "C" fn mcstat_update_counter_result(counter: u8) -> u8 {
    (counter + 1) % 10
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_parse_i32_result(arg: *const u8) -> i32 {
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
pub unsafe extern "C" fn mcstat_mcos_path_result(path: *mut u8, index: i32) -> i32 {
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
pub unsafe extern "C" fn mcstat_memory_total_result(values: *const u64, count: i32) -> u64 {
    unsafe { sum_ulongs(values, count) }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_memory_current_result(
    kmem_usage: u64,
    numa_values: *const u64,
    count: i32,
) -> u64 {
    kmem_usage.wrapping_add(unsafe { sum_ulongs(numa_values, count) })
}

#[no_mangle]
pub extern "C" fn mcstat_memory_max_result(kmem_max_usage: u64, user_max_usage: u64) -> u64 {
    kmem_max_usage.wrapping_add(user_max_usage)
}

#[no_mangle]
pub extern "C" fn mcstat_monstatus_result(status: i32) -> *const u8 {
    match status {
        IHK_OS_MONITOR_NOT_BOOT => BOOT.as_ptr(),
        IHK_OS_MONITOR_IDLE => IDLE.as_ptr(),
        IHK_OS_MONITOR_USER => USER_MODE.as_ptr(),
        IHK_OS_MONITOR_KERNEL | IHK_OS_MONITOR_KERNEL_HEAVY => KERNEL_MODE.as_ptr(),
        IHK_OS_MONITOR_KERNEL_OFFLOAD => OFFLOAD.as_ptr(),
        IHK_OS_MONITOR_KERNEL_FREEZING => FREEZING.as_ptr(),
        IHK_OS_MONITOR_KERNEL_FROZEN => FROZEN.as_ptr(),
        IHK_OS_MONITOR_KERNEL_THAW => THAW.as_ptr(),
        IHK_OS_MONITOR_PANIC => PANIC.as_ptr(),
        _ => EMPTY.as_ptr(),
    }
}

#[no_mangle]
pub extern "C" fn mcstat_os_status_result(status: i32) -> *const u8 {
    match status {
        IHK_OS_STATUS_NOT_BOOTED => NONE.as_ptr(),
        IHK_OS_STATUS_BOOTING => BOOTING_STATUS.as_ptr(),
        IHK_OS_STATUS_BOOTED => BOOTED.as_ptr(),
        IHK_OS_STATUS_READY => READY.as_ptr(),
        IHK_OS_STATUS_RUNNING => RUNNING.as_ptr(),
        IHK_OS_STATUS_FREEZING => FREEZING_STATUS.as_ptr(),
        IHK_OS_STATUS_FROZEN => FROZEN_STATUS.as_ptr(),
        IHK_OS_STATUS_SHUTDOWN => SHUTDOWN.as_ptr(),
        IHK_OS_STATUS_FAILED => PANIC_STATUS.as_ptr(),
        IHK_OS_STATUS_HUNGUP => HANGUP.as_ptr(),
        _ => core::ptr::null(),
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_statistics_header_result(
    buf: *mut u8,
    buf_size: usize,
    unit: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"------- memory (")
            && write_cstr_checked(buf, &mut pos, buf_size, unit)
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b") ------- ------- tsc ------ --- thread ---\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    total  current      max    system     user current max\n",
            )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_status_line_result(
    buf: *mut u8,
    buf_size: usize,
    status: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"McKernel status: ")
            && write_cstr_checked(buf, &mut pos, buf_size, status)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_osusage_header_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok =
        unsafe { write_bytes_checked(buf, &mut pos, buf_size, b"--cpu-- --status-- --count--\n") };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_cpu_usage_line_result(
    buf: *mut u8,
    buf_size: usize,
    cpu: i32,
    status: *const u8,
    counter: i64,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_i64_width_checked(buf, &mut pos, buf_size, cpu as i64, 6)
            && write_bytes_checked(buf, &mut pos, buf_size, b": ")
            && write_cstr_width_checked(buf, &mut pos, buf_size, status, 10)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_i64_width_checked(buf, &mut pos, buf_size, counter, 9)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_cpuacct_line_result(
    buf: *mut u8,
    buf_size: usize,
    cpu: i32,
    usage: i64,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"cpuacct_usage_percpu[")
            && write_i64_decimal_checked(buf, &mut pos, buf_size, cpu as i64)
            && write_bytes_checked(buf, &mut pos, buf_size, b"] = ")
            && write_i64_decimal_checked(buf, &mut pos, buf_size, usage)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_usage_line_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"Usage: mcstat [-h|-n|-s] [delay [count]]\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_main_plan_result(
    sflag: i32,
    cflag: i32,
    optind: i32,
    argc: i32,
    delay_arg: *const u8,
    count_arg: *const u8,
    delay: *mut i32,
    count: *mut i32,
) -> i32 {
    if delay.is_null() || count.is_null() {
        return MCSTAT_MODE_STATS;
    }

    unsafe {
        *delay = 0;
        *count = 1;
    }

    if optind < argc {
        unsafe {
            *delay = mcstat_parse_i32_result(delay_arg);
            *count = if optind + 1 < argc {
                mcstat_parse_i32_result(count_arg)
            } else {
                -1
            };
        }
    }

    if sflag != 0 {
        MCSTAT_MODE_STATUS
    } else if cflag != 0 {
        MCSTAT_MODE_CPU
    } else {
        MCSTAT_MODE_STATS
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcstat_loop_control_result(
    once: i32,
    count: *mut i32,
    show: *mut u8,
) -> i32 {
    if count.is_null() || show.is_null() {
        return MCSTAT_LOOP_DONE;
    }

    unsafe {
        if *count > 0 {
            *count -= 1;
            if *count == 0 {
                return MCSTAT_LOOP_DONE;
            }
        }

        if once == 0 {
            *show = (*show + 1) % 10;
            if *show == 0 {
                return MCSTAT_LOOP_REPRINT;
            }
        }
    }

    0
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
