#![no_std]

use core::ffi::{c_int, c_ulong, c_void};
use core::panic::PanicInfo;

unsafe extern "C" {
    static mut symbfd: *mut c_void;
    static mut nsyms: isize;
    static mut symtab: *mut *mut BfdSymbol;
    static mut mcfd: c_int;
    static mut nr_cpus: c_int;
    #[link_name = "clv"]
    static mut MCINSPECT_CLV: usize;
    #[link_name = "clv_size"]
    static mut MCINSPECT_CLV_SIZE: usize;
    static mut clv_runq_offset: usize;
    #[link_name = "thread_sched_list_offset"]
    static mut MCINSPECT_THREAD_SCHED_LIST_OFFSET: usize;
    static mut thread_proc_offset: usize;
    static mut process_pid_offset: usize;
    static mut stdout: *mut c_void;
    static mut stderr: *mut c_void;
    fn basename(path: *mut u8) -> *mut u8;
    fn malloc(size: usize) -> *mut c_void;
    fn perror(s: *const u8);
    fn fputs(s: *const u8, stream: *mut c_void) -> c_int;
    fn fprintf(stream: *mut c_void, fmt: *const u8, ...) -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn exit(status: c_int) -> !;
    fn bfd_openr(filename: *const u8, target: *const u8) -> *mut c_void;
    fn bfd_check_format(abfd: *mut c_void, format: c_int) -> c_int;
    fn bfd_perror(message: *const u8);
    fn mcinspect_bfd_get_symtab_upper_bound_bridge(abfd: *mut c_void) -> isize;
    fn mcinspect_bfd_canonicalize_symtab_bridge(
        abfd: *mut c_void,
        location: *mut *mut BfdSymbol,
    ) -> isize;
}

#[repr(C)]
struct IhkOsReadKaddrDesc {
    kaddr: usize,
    len: usize,
    ubuf: *mut c_void,
    flags: c_int,
}

#[repr(C)]
struct BfdSection {
    name: *const u8,
    id: u32,
    index: u32,
    next: *mut BfdSection,
    prev: *mut BfdSection,
    flags: u32,
    vma: usize,
}

#[repr(C)]
struct BfdSymbol {
    the_bfd: *mut c_void,
    name: *const u8,
    value: usize,
    flags: u32,
    section: *mut BfdSection,
}

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
const MCINSPECT_MAIN_CONTINUE: i32 = 0;
const MCINSPECT_MAIN_HELP: i32 = 1;
const MCINSPECT_MAIN_MISSING_KERNEL: i32 = 2;
const MCINSPECT_MAIN_NO_ACTION: i32 = 3;
const IHK_OS_READ_KADDR: c_ulong = 0x112a39;
const BFD_OBJECT: c_int = 1;

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

    if unsafe { *base } == 0 { path } else { base }
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

unsafe fn cstr_eq(lhs: *const u8, rhs: *const u8) -> bool {
    if lhs.is_null() || rhs.is_null() {
        return false;
    }

    let mut idx = 0usize;
    loop {
        let l = unsafe { *lhs.add(idx) };
        let r = unsafe { *rhs.add(idx) };
        if l != r {
            return false;
        }
        if l == 0 {
            return true;
        }
        idx += 1;
    }
}

const MCINSPECT_NOSYMBOL: usize = usize::MAX;

#[no_mangle]
pub unsafe extern "C" fn usage(argv: *mut *mut u8) {
    let prog = unsafe { basename(*argv) };
    let mut line = [0u8; 1024];
    if unsafe { mcinspect_usage_result(line.as_mut_ptr(), line.len(), prog) } >= 0 {
        unsafe {
            fputs(line.as_ptr(), stdout);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn lookup_bfd_symbol(name: *mut u8) -> usize {
    let count = unsafe {
        if nsyms < 0 || symtab.is_null() {
            return MCINSPECT_NOSYMBOL;
        }
        nsyms as usize
    };
    let mut idx = 0usize;
    while idx < count {
        let symbol = unsafe { *symtab.add(idx) };
        if !symbol.is_null() {
            let candidate = unsafe { (*symbol).name };
            if unsafe { cstr_eq(candidate, name as *const u8) } {
                let section = unsafe { (*symbol).section };
                if !section.is_null() {
                    return unsafe { (*section).vma.wrapping_add((*symbol).value) };
                }
            }
        }
        idx += 1;
    }

    MCINSPECT_NOSYMBOL
}

#[no_mangle]
pub unsafe extern "C" fn init_bfd_symbols(fname: *mut u8) -> c_int {
    let abfd = unsafe { bfd_openr(fname as *const u8, core::ptr::null()) };
    unsafe {
        symbfd = abfd;
    }
    if abfd.is_null() {
        unsafe {
            bfd_perror(b"bfd_openr\0".as_ptr());
        }
        return -1;
    }

    if unsafe { bfd_check_format(abfd, BFD_OBJECT) } == 0 {
        unsafe {
            bfd_perror(b"bfd_check_format\0".as_ptr());
        }
        return -1;
    }

    let needs = unsafe { mcinspect_bfd_get_symtab_upper_bound_bridge(abfd) };
    if needs < 0 {
        unsafe {
            bfd_perror(b"bfd_get_symtab_upper_bound\0".as_ptr());
        }
        return -1;
    }

    if needs == 0 {
        unsafe {
            fputs(b"no symbols\n\0".as_ptr(), stdout);
        }
        return -1;
    }

    let table = unsafe { malloc(needs as usize) } as *mut *mut BfdSymbol;
    if table.is_null() {
        unsafe {
            perror(b"malloc\0".as_ptr());
        }
        return -1;
    }
    unsafe {
        symtab = table;
    }

    let count = unsafe { mcinspect_bfd_canonicalize_symtab_bridge(abfd, table) };
    if count < 0 {
        unsafe {
            bfd_perror(b"bfd_canonicalize_symtab\0".as_ptr());
        }
        return -1;
    }
    unsafe {
        nsyms = count;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_read_kernel(addr: usize, len: usize, buf: *mut c_void, flags: c_int) {
    let mut desc = IhkOsReadKaddrDesc {
        kaddr: addr,
        len,
        ubuf: buf,
        flags,
    };

    if unsafe {
        ioctl(
            mcfd,
            IHK_OS_READ_KADDR,
            &mut desc as *mut IhkOsReadKaddrDesc,
        )
    } != 0
    {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: accessing kernel addr 0x%lx\n\0".as_ptr(),
                b"ihk_read_kernel\0".as_ptr(),
                addr,
            );
            exit(1);
        }
    }
}

unsafe fn read_kernel_usize(addr: usize) -> usize {
    let mut value = 0usize;
    unsafe {
        ihk_read_kernel(
            addr,
            core::mem::size_of::<usize>(),
            &mut value as *mut usize as *mut c_void,
            0,
        );
    }
    value
}

unsafe fn read_kernel_i32(addr: usize) -> c_int {
    let mut value = 0i32;
    unsafe {
        ihk_read_kernel(
            addr,
            core::mem::size_of::<i32>(),
            &mut value as *mut i32 as *mut c_void,
            0,
        );
    }
    value
}

#[no_mangle]
pub unsafe extern "C" fn find_proc(_dbg: *mut c_void, pid: c_int, rproc: *mut usize) -> c_int {
    let cpu_count = unsafe { nr_cpus };
    let mut cpu = 0i32;
    while cpu < cpu_count {
        let per_cpu =
            unsafe { mcinspect_cpu_local_base_result(MCINSPECT_CLV, MCINSPECT_CLV_SIZE, cpu) };
        let runq = unsafe { per_cpu.wrapping_add(clv_runq_offset) };
        let mut thread_sched_list = unsafe { read_kernel_usize(runq) };

        while thread_sched_list != runq {
            let thread = unsafe {
                mcinspect_thread_from_sched_list_result(
                    thread_sched_list,
                    MCINSPECT_THREAD_SCHED_LIST_OFFSET,
                )
            };
            let proc = unsafe { read_kernel_usize(thread.wrapping_add(thread_proc_offset)) };
            let ipid = unsafe { read_kernel_i32(proc.wrapping_add(process_pid_offset)) };
            if pid == ipid {
                if !rproc.is_null() {
                    unsafe {
                        *rproc = proc;
                    }
                }
                return 0;
            }
            thread_sched_list = unsafe { read_kernel_usize(thread_sched_list) };
        }

        cpu += 1;
    }

    -1
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
    let ptr = if ptr.is_null() {
        THREAD_UNKNOWN.as_ptr()
    } else {
        ptr
    };
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

fn usize_hex_width(value: usize) -> usize {
    if value == 0 {
        1
    } else {
        let bits = usize::BITS as usize - value.leading_zeros() as usize;
        (bits + 3) / 4
    }
}

unsafe fn write_usize_hex_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    value: usize,
    width: usize,
) -> bool {
    let digits = usize_hex_width(value).max(width);
    let mut pad = digits.saturating_sub(usize_hex_width(value));
    while pad != 0 {
        if !unsafe { write_byte_checked(buf, pos, buf_size, b' ') } {
            return false;
        }
        pad -= 1;
    }

    let mut shift = (usize_hex_width(value).saturating_sub(1)) * 4;
    loop {
        let digit = ((value >> shift) & 0xf) as u8;
        let byte = if digit < 10 {
            b'0' + digit
        } else {
            b'a' + (digit - 10)
        };
        if !unsafe { write_byte_checked(buf, pos, buf_size, byte) } {
            return false;
        }
        if shift == 0 {
            break;
        }
        shift -= 4;
    }
    true
}

unsafe fn write_cstr_width_checked(
    buf: *mut u8,
    pos: &mut usize,
    buf_size: usize,
    ptr: *const u8,
    width: usize,
) -> bool {
    let ptr = if ptr.is_null() {
        THREAD_UNKNOWN.as_ptr()
    } else {
        ptr
    };
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
pub unsafe extern "C" fn mcinspect_ps_header_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"CPU     TID    PID             Thread ST exe\n",
        ) && write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"-----------------------------------------------\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_thread_line_result(
    buf: *mut u8,
    buf_size: usize,
    cpu: i32,
    active_marker: *const u8,
    tid: i32,
    pid: i32,
    thread: usize,
    status: *const u8,
    comm: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_i64_width_checked(buf, &mut pos, buf_size, cpu as i64, 3)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_cstr_checked(buf, &mut pos, buf_size, active_marker)
            && write_i64_width_checked(buf, &mut pos, buf_size, tid as i64, 6)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_i64_width_checked(buf, &mut pos, buf_size, pid as i64, 6)
            && write_bytes_checked(buf, &mut pos, buf_size, b" 0x")
            && write_usize_hex_width_checked(buf, &mut pos, buf_size, thread, 16)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_cstr_width_checked(buf, &mut pos, buf_size, status, 2)
            && write_byte_checked(buf, &mut pos, buf_size, b' ')
            && write_cstr_checked(buf, &mut pos, buf_size, comm)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_usage_result(
    buf: *mut u8,
    buf_size: usize,
    prog: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"Usage: ")
            && write_cstr_checked(buf, &mut pos, buf_size, prog)
            && write_bytes_checked(buf, &mut pos, buf_size, b" <options>\n")
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"Inspect internal state of McKernel.\n",
            )
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"Mandatory arguments to long options are mandatory for short options too.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    --help                      Display this help message.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    --kernel PATH               Path to kernel image.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    --ps                        List processes running on LWK.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    --vtop                      Dump page tables.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    -v, --va ADDR               Dump page tables for ADDR only.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    -p, --pid PID               Use process PID for vtop.\n",
            )
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b"    --debug                     Enable debug mode.\n",
            )
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
            && write_bytes_checked(buf, &mut pos, buf_size, b"Examples: \n")
            && write_bytes_checked(buf, &mut pos, buf_size, b"    ")
            && write_cstr_checked(buf, &mut pos, buf_size, prog)
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b" --kernel=smp-x86/kernel/mckernel.img --ps\n    ",
            )
            && write_cstr_checked(buf, &mut pos, buf_size, prog)
            && write_bytes_checked(
                buf,
                &mut pos,
                buf_size,
                b" --kernel=smp-x86/kernel/mckernel.img --vtop --pid 100 --va 0x3fffff800000\n",
            )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_invalid_va_error_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"error: invalid VA? (expected format: 0xXXXX)\n\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_missing_kernel_error_result(
    buf: *mut u8,
    buf_size: usize,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"error: you must specify the kernel image\n\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_pid_line_result(buf: *mut u8, buf_size: usize, pid: i32) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"PID: ")
            && write_i64_decimal_checked(buf, &mut pos, buf_size, pid as i64)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_no_symbols_line_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe { write_bytes_checked(buf, &mut pos, buf_size, b"no symbols\n") };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_elf_image_error_result(
    buf: *mut u8,
    buf_size: usize,
    path: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"error: accessing ELF image ")
            && write_cstr_checked(buf, &mut pos, buf_size, path)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_open_os_device_error_result(
    buf: *mut u8,
    buf_size: usize,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"error: opening IHK OS device file\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_open_kernel_error_result(
    buf: *mut u8,
    buf_size: usize,
    path: *const u8,
) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(buf, &mut pos, buf_size, b"error: opening ")
            && write_cstr_checked(buf, &mut pos, buf_size, path)
            && write_byte_checked(buf, &mut pos, buf_size, b'\n')
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_info_error_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe {
        write_bytes_checked(
            buf,
            &mut pos,
            buf_size,
            b"error: accessing DWARF information\n",
        )
    };
    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    if ok { pos as i32 } else { -1 }
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

    if neg { value.saturating_neg() } else { value }
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
    if ps != 0 || vtop != 0 { 1 } else { 0 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_main_preflight_action_result(
    help: i32,
    kernel_path: *const u8,
    ps: i32,
    vtop: i32,
) -> i32 {
    if help != 0 {
        MCINSPECT_MAIN_HELP
    } else if kernel_path.is_null() {
        MCINSPECT_MAIN_MISSING_KERNEL
    } else if unsafe { mcinspect_need_action_result(ps, vtop) } == 0 {
        MCINSPECT_MAIN_NO_ACTION
    } else {
        MCINSPECT_MAIN_CONTINUE
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
    if value >= 0 { 1 } else { 0 }
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
    if pid != 0 { 1 } else { 0 }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_vtop_has_process_result(proc: usize) -> i32 {
    if proc != 0 { 1 } else { 0 }
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
