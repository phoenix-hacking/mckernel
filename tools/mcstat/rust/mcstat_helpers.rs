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
const IHK_OS_MONITOR_KERNEL_FREEZING: i32 = 6;
const IHK_OS_MONITOR_KERNEL_FROZEN: i32 = 7;
const IHK_OS_MONITOR_KERNEL_THAW: i32 = 8;
const IHK_OS_MONITOR_PANIC: i32 = 9;

static MB: &[u8; 3] = b"MB\0";
static GB: &[u8; 3] = b"GB\0";
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

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
