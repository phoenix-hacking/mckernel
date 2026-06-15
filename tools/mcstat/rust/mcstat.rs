#![no_std]

use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong, c_void};
use core::mem;
use core::panic::PanicInfo;

const MAX_CPUS: usize = 256;
const IHK_MAX_NUM_NUMA_NODES: usize = 1024;
const IHK_MAX_NUM_CPUS: usize = 1024;
const IHK_MAX_NUM_PGSIZES: usize = 8;

const MIB100: c_ulong = 100 * 1024 * 1024;
const MIB: c_ulong = 1024 * 1024;
const GIB: c_ulong = 1024 * 1024 * 1024;

const ENOMEM: c_int = 12;
const EINVAL: c_int = 22;
const O_RDONLY: c_int = 0;

const IHK_OS_STATUS: c_ulong = 0x112a14;
const IHK_OS_GET_CPU_USAGE: c_ulong = 0x112a33;

const IHK_OS_STATUS_NOT_BOOTED: c_int = 0;
const IHK_OS_STATUS_BOOTING: c_int = 2;
const IHK_OS_STATUS_BOOTED: c_int = 3;
const IHK_OS_STATUS_READY: c_int = 4;
const IHK_OS_STATUS_RUNNING: c_int = 5;
const IHK_OS_STATUS_FREEZING: c_int = 6;
const IHK_OS_STATUS_FROZEN: c_int = 7;
const IHK_OS_STATUS_SHUTDOWN: c_int = 8;
const IHK_OS_STATUS_FAILED: c_int = 9;
const IHK_OS_STATUS_HUNGUP: c_int = 10;
const IHK_OS_STATUS_COUNT: c_int = 11;

const IHK_OS_MONITOR_NOT_BOOT: c_int = 0;
const IHK_OS_MONITOR_IDLE: c_int = 1;
const IHK_OS_MONITOR_USER: c_int = 2;
const IHK_OS_MONITOR_KERNEL: c_int = 3;
const IHK_OS_MONITOR_KERNEL_HEAVY: c_int = 4;
const IHK_OS_MONITOR_KERNEL_OFFLOAD: c_int = 5;
const IHK_OS_MONITOR_KERNEL_FREEZING: c_int = 8;
const IHK_OS_MONITOR_KERNEL_FROZEN: c_int = 9;
const IHK_OS_MONITOR_KERNEL_THAW: c_int = 10;
const IHK_OS_MONITOR_PANIC: c_int = 99;

#[repr(C)]
struct File {
    _private: [u8; 0],
}

#[repr(C)]
struct IhkOsRusage {
    memory_stat_rss: [c_ulong; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [c_ulong; IHK_MAX_NUM_PGSIZES],
    memory_max_usage: c_ulong,
    memory_kmem_usage: c_ulong,
    memory_kmem_max_usage: c_ulong,
    memory_numa_stat: [c_ulong; IHK_MAX_NUM_NUMA_NODES],
    cpuacct_stat_system: c_ulong,
    cpuacct_stat_user: c_ulong,
    cpuacct_usage: c_ulong,
    cpuacct_usage_percpu: [c_ulong; IHK_MAX_NUM_CPUS],
    num_threads: c_int,
    max_num_threads: c_int,
}

#[repr(C)]
struct IhkOsCpuMonitor {
    status: c_int,
    status_bak: c_int,
    counter: c_ulong,
    ocounter: c_ulong,
}

struct MyRusage {
    rusage: IhkOsRusage,
    memory_total: c_ulong,
    memory_cur_usage: c_ulong,
    memory_max_usage: c_ulong,
}

unsafe extern "C" {
    static mut optind: c_int;
    static mut stderr: *mut File;

    fn __errno_location() -> *mut c_int;
    fn calloc(nmemb: usize, size: usize) -> *mut c_void;
    fn close(fd: c_int) -> c_int;
    fn exit(status: c_int) -> !;
    fn free(ptr: *mut c_void);
    fn fprintf(stream: *mut File, format: *const c_char, ...) -> c_int;
    fn getopt(argc: c_int, argv: *mut *mut c_char, optstring: *const c_char) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn open(pathname: *const c_char, flags: c_int, ...) -> c_int;
    fn printf(format: *const c_char, ...) -> c_int;
    fn sleep(seconds: c_uint) -> c_uint;
    fn strerror(errnum: c_int) -> *const c_char;

    fn ihk_os_get_num_numa_nodes(index: c_int) -> c_int;
    fn ihk_os_getrusage(index: c_int, rusage: *mut IhkOsRusage, size_rusage: usize) -> c_int;
    fn ihk_os_query_total_mem(
        os_index: c_int,
        memtotal: *mut c_ulong,
        num_numa_nodes: c_int,
    ) -> c_int;
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {}
}

unsafe fn errno() -> c_int {
    unsafe { *__errno_location() }
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr() as *const c_char
}

unsafe fn write_byte(buf: *mut c_char, pos: &mut usize, byte: u8) {
    unsafe {
        *buf.add(*pos) = byte as c_char;
    }
    *pos += 1;
}

unsafe fn write_i32_decimal(buf: *mut c_char, pos: &mut usize, value: c_int) {
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
        unsafe {
            write_byte(buf, pos, *digits.as_ptr().add(count));
        }
    }
}

unsafe fn parse_i32(arg: *const c_char) -> c_int {
    if arg.is_null() {
        return 0;
    }

    let mut ptr = arg as *const u8;
    let mut byte = unsafe { *ptr };
    while matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c) {
        ptr = unsafe { ptr.add(1) };
        byte = unsafe { *ptr };
    }

    let mut negative = false;
    if byte == b'-' {
        negative = true;
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

    if negative {
        value.saturating_neg()
    } else {
        value
    }
}

unsafe fn devopen(idx: c_int) -> c_int {
    let mut path = [0 as c_char; 128];
    let mut pos = 0usize;

    unsafe {
        write_byte(path.as_mut_ptr(), &mut pos, b'/');
        write_byte(path.as_mut_ptr(), &mut pos, b'd');
        write_byte(path.as_mut_ptr(), &mut pos, b'e');
        write_byte(path.as_mut_ptr(), &mut pos, b'v');
        write_byte(path.as_mut_ptr(), &mut pos, b'/');
        write_byte(path.as_mut_ptr(), &mut pos, b'm');
        write_byte(path.as_mut_ptr(), &mut pos, b'c');
        write_byte(path.as_mut_ptr(), &mut pos, b'o');
        write_byte(path.as_mut_ptr(), &mut pos, b's');
        write_i32_decimal(path.as_mut_ptr(), &mut pos, idx);
        *path.as_mut_ptr().add(pos) = 0;
        open(path.as_ptr(), O_RDONLY)
    }
}

fn memory_scale(max_usage: c_ulong) -> c_ulong {
    if max_usage < MIB100 {
        MIB
    } else {
        GIB
    }
}

fn memory_unit(max_usage: c_ulong) -> *const c_char {
    if max_usage < MIB100 {
        cstr(b"MB\0")
    } else {
        cstr(b"GB\0")
    }
}

unsafe fn usage() {
    unsafe {
        fprintf(
            stderr,
            cstr(b"Usage: mcstat [-h|-n|-s] [delay [count]]\n\0"),
        );
    }
}

unsafe fn statistics_header(unit: *const c_char) {
    unsafe {
        printf(
            cstr(b"------- memory (%s) ------- ------- tsc ------ --- thread ---\n\0"),
            unit,
        );
        printf(cstr(
            b"    total  current      max    system     user current max\n\0",
        ));
    }
}

unsafe fn mygetrusage(idx: c_int, rbp: *mut MyRusage) -> c_int {
    let mut rc = unsafe {
        ihk_os_getrusage(
            idx,
            core::ptr::addr_of_mut!((*rbp).rusage),
            mem::size_of::<IhkOsRusage>(),
        )
    };
    if rc != 0 {
        unsafe {
            printf(
                cstr(b"%s: error: ihk_os_getrusage: %s\n\0"),
                cstr(b"mygetrusage\0"),
                strerror(-rc),
            );
        }
        return rc;
    }

    let num_numa_nodes = unsafe { ihk_os_get_num_numa_nodes(idx) };
    if num_numa_nodes <= 0 {
        unsafe {
            printf(
                cstr(b"%s: error: ihk_os_get_num_numa_nodes: %d\n\0"),
                cstr(b"mygetrusage\0"),
                num_numa_nodes,
            );
        }
        return if num_numa_nodes < 0 {
            num_numa_nodes
        } else {
            -EINVAL
        };
    }

    let memtotal =
        unsafe { calloc(num_numa_nodes as usize, mem::size_of::<c_ulong>()) as *mut c_ulong };
    if memtotal.is_null() {
        unsafe {
            printf(
                cstr(b"%s: error: assigining memory\n\0"),
                cstr(b"mygetrusage\0"),
            );
        }
        return -ENOMEM;
    }

    rc = unsafe { ihk_os_query_total_mem(idx, memtotal, num_numa_nodes) };
    if rc != 0 {
        unsafe {
            printf(
                cstr(b"%s: error: ihk_os_query_total_mem: %s\n\0"),
                cstr(b"mygetrusage\0"),
                strerror(-rc),
            );
            free(memtotal as *mut c_void);
        }
        return rc;
    }

    let mut total = 0 as c_ulong;
    let mut idx_node = 0usize;
    while idx_node < num_numa_nodes as usize {
        total = total.wrapping_add(unsafe { *memtotal.add(idx_node) });
        idx_node += 1;
    }

    let mut current = unsafe { (*rbp).rusage.memory_kmem_usage };
    idx_node = 0;
    while idx_node < num_numa_nodes as usize {
        current =
            current.wrapping_add(unsafe { *(*rbp).rusage.memory_numa_stat.as_ptr().add(idx_node) });
        idx_node += 1;
    }

    unsafe {
        (*rbp).memory_total = total;
        (*rbp).memory_cur_usage = current;
        (*rbp).memory_max_usage = (*rbp)
            .rusage
            .memory_kmem_max_usage
            .wrapping_add((*rbp).rusage.memory_max_usage);
        free(memtotal as *mut c_void);
    }

    0
}

unsafe fn mcstatistics(idx: c_int, once: c_int, delay: c_int, mut count: c_int) {
    let mut rbuf: MyRusage = unsafe { mem::zeroed() };
    let mut show = 0u8;

    if unsafe { mygetrusage(idx, &mut rbuf) } < 0 {
        unsafe {
            printf(cstr(b"Device has not been created.\n\0"));
            exit(-1);
        }
    }

    let scale = memory_scale(rbuf.rusage.memory_max_usage);
    let unit = memory_unit(rbuf.rusage.memory_max_usage);
    unsafe {
        statistics_header(unit);
    }

    loop {
        unsafe {
            printf(
                cstr(b"%9.3f%9.3f%9.3f %9ld%9ld %7d %3d\n\0"),
                (rbuf.memory_total as f64) / (scale as f64),
                (rbuf.memory_cur_usage as f64) / (scale as f64),
                (rbuf.memory_max_usage as f64) / (scale as f64),
                rbuf.rusage.cpuacct_stat_system as c_long,
                rbuf.rusage.cpuacct_stat_user as c_long,
                rbuf.rusage.num_threads,
                rbuf.rusage.max_num_threads,
            );
        }

        if count > 0 {
            count -= 1;
            if count == 0 {
                break;
            }
        }

        unsafe {
            sleep(delay as c_uint);
        }
        if unsafe { mygetrusage(idx, &mut rbuf) } < 0 {
            unsafe {
                printf(cstr(b"Device is now invisible.\n\0"));
            }
            break;
        }
        if once == 0 {
            show = (show + 1) % 10;
            if show == 0 {
                unsafe {
                    statistics_header(unit);
                }
            }
        }
    }

    let mut cpu = 0usize;
    while cpu < rbuf.rusage.max_num_threads as usize {
        let usage = unsafe { *rbuf.rusage.cpuacct_usage_percpu.as_ptr().add(cpu) };
        unsafe {
            printf(
                cstr(b"cpuacct_usage_percpu[%d] = %ld\n\0"),
                cpu as c_int,
                usage as c_long,
            );
        }
        cpu += 1;
    }
}

fn os_status(status: c_int) -> *const c_char {
    match status {
        IHK_OS_STATUS_NOT_BOOTED => cstr(b"None\0"),
        IHK_OS_STATUS_BOOTING => cstr(b"Booting\0"),
        IHK_OS_STATUS_BOOTED => cstr(b"Booted\0"),
        IHK_OS_STATUS_READY => cstr(b"Ready\0"),
        IHK_OS_STATUS_RUNNING => cstr(b"Running\0"),
        IHK_OS_STATUS_FREEZING => cstr(b"Freezing\0"),
        IHK_OS_STATUS_FROZEN => cstr(b"Frozen\0"),
        IHK_OS_STATUS_SHUTDOWN => cstr(b"Shutdown\0"),
        IHK_OS_STATUS_FAILED => cstr(b"Panic\0"),
        IHK_OS_STATUS_HUNGUP => cstr(b"Hangup\0"),
        _ => core::ptr::null(),
    }
}

unsafe fn mcstatus(idx: c_int, delay: c_int, mut count: c_int) -> c_int {
    loop {
        let fd = unsafe { devopen(idx) };
        let mut rc;

        if fd == -1 {
            rc = unsafe { -errno() };
            unsafe {
                printf(cstr(b"Device not found\n\0"));
            }
        } else {
            rc = unsafe { ioctl(fd, IHK_OS_STATUS, 0 as c_int) };
            if rc == -1 {
                rc = unsafe { -errno() };
                unsafe {
                    printf(
                        cstr(b"%s: error: IHK_OS_STATUS: %s\n\0"),
                        cstr(b"mcstatus\0"),
                        strerror(-rc),
                    );
                    close(fd);
                }
                break rc;
            }

            unsafe {
                close(fd);
            }

            if rc < 0 && rc >= IHK_OS_STATUS_COUNT {
                unsafe {
                    printf(
                        cstr(b"%s: error: status (%d) out of range\n\0"),
                        cstr(b"mcstatus\0"),
                        rc,
                    );
                }
                rc = -EINVAL;
                break rc;
            }

            let status = os_status(rc);
            unsafe {
                printf(
                    cstr(b"McKernel status: %s\n\0"),
                    if status.is_null() {
                        cstr(b"Unknown\0")
                    } else {
                        status
                    },
                );
            }
        }

        if count > 0 {
            count -= 1;
            if count == 0 {
                break rc;
            }
        }
        unsafe {
            sleep(delay as c_uint);
        }
    }
}

fn monstatus(status: c_int) -> *const c_char {
    match status {
        IHK_OS_MONITOR_NOT_BOOT => cstr(b"boot\0"),
        IHK_OS_MONITOR_IDLE => cstr(b"idle\0"),
        IHK_OS_MONITOR_USER => cstr(b"user mode\0"),
        IHK_OS_MONITOR_KERNEL | IHK_OS_MONITOR_KERNEL_HEAVY => cstr(b"kernel mode\0"),
        IHK_OS_MONITOR_KERNEL_OFFLOAD => cstr(b"offload\0"),
        IHK_OS_MONITOR_KERNEL_FREEZING => cstr(b"freezing\0"),
        IHK_OS_MONITOR_KERNEL_FROZEN => cstr(b"frozen\0"),
        IHK_OS_MONITOR_KERNEL_THAW => cstr(b"thaw\0"),
        IHK_OS_MONITOR_PANIC => cstr(b"panic\0"),
        _ => cstr(b"\0"),
    }
}

unsafe fn osusage_header() {
    unsafe {
        printf(cstr(b"--cpu-- --status-- --count--\n\0"));
    }
}

unsafe fn mcosusage(idx: c_int, once: c_int, delay: c_int, mut count: c_int) {
    let mut rbuf: MyRusage = unsafe { mem::zeroed() };
    let mut show = 0u8;
    let mut mon: [IhkOsCpuMonitor; MAX_CPUS] = unsafe { mem::zeroed() };

    if unsafe { mygetrusage(idx, &mut rbuf) } < 0 {
        unsafe {
            printf(cstr(b"Device has not been created.\n\0"));
        }
    }

    let ncpus = rbuf.rusage.max_num_threads;
    unsafe {
        osusage_header();
    }

    loop {
        let fd = unsafe { devopen(idx) };
        if fd < 0 {
            unsafe {
                printf(cstr(b"Devide is not created\n\0"));
            }
        } else {
            let rc = unsafe { ioctl(fd, IHK_OS_GET_CPU_USAGE, mon.as_mut_ptr() as *mut c_void) };
            unsafe {
                close(fd);
            }
            if rc != 0 {
                unsafe {
                    printf(cstr(b"ioctl error(IHK_OS_GET_CPU_USAGE)\n\0"));
                }
                break;
            }

            let mut cpu = 0usize;
            while cpu < ncpus as usize {
                let entry = unsafe { mon.as_ptr().add(cpu) };
                unsafe {
                    printf(
                        cstr(b"%6d: %10s %9ld\n\0"),
                        cpu as c_int,
                        monstatus((*entry).status),
                        (*entry).counter as c_long,
                    );
                }
                cpu += 1;
            }
        }

        if count > 0 {
            count -= 1;
            if count == 0 {
                break;
            }
        }
        unsafe {
            sleep(delay as c_uint);
        }
        if once == 0 {
            show = (show + 1) % 10;
            if show == 0 {
                unsafe {
                    osusage_header();
                }
            }
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut c_char) -> c_int {
    let mut opt;
    let idx = 0;
    let mut sflag = 0;
    let mut cflag = 0;
    let mut once = 0;
    let mut delay = 0;
    let mut count = 1;

    if argc > 1 {
        loop {
            opt = unsafe { getopt(argc, argv, cstr(b"chns\0")) };
            if opt == -1 {
                break;
            }

            match opt as u8 {
                b'c' => cflag = 1,
                b'h' => unsafe {
                    usage();
                    exit(0);
                },
                b'n' => once = 1,
                b's' => sflag = 1,
                _ => {}
            }
        }
    }

    let optind_value = unsafe { optind };
    if optind_value < argc {
        delay = unsafe { parse_i32(*argv.add(optind_value as usize)) };
        if optind_value + 1 < argc {
            count = unsafe { parse_i32(*argv.add((optind_value + 1) as usize)) };
        } else {
            count = -1;
        }
    }

    if sflag != 0 {
        let rc = unsafe { mcstatus(idx, delay, count) };
        if rc < 0 {
            return rc;
        }
    } else if cflag != 0 {
        unsafe {
            mcosusage(idx, once, delay, count);
        }
    } else {
        unsafe {
            mcstatistics(idx, once, delay, count);
        }
    }

    0
}
