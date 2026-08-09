#![feature(c_variadic)]
#![no_std]

use core::ffi::{c_int, c_ulong, c_void};
use core::panic::PanicInfo;

#[no_mangle]
pub unsafe extern "C" fn eclair_dprintf(_fmt: *const u8, _args: ...) -> i32 {
    0
}

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

const ECLAIR_PACKET_STEP_NONE: i32 = 0;
const ECLAIR_PACKET_STEP_INTERRUPT: i32 = 1;
const ECLAIR_PACKET_STEP_READY: i32 = 2;
const ECLAIR_PACKET_STEP_BAD: i32 = 3;
const ECLAIR_PACKET_STEP_ERROR: i32 = 4;
const ECLAIR_REMOTE_ACTION_NONE: i32 = 0;
const ECLAIR_REMOTE_ACTION_NMI: i32 = 1;
const ECLAIR_REMOTE_ACTION_CONTINUE: i32 = 2;
const ECLAIR_PURE_COMMAND_NOT_HANDLED: isize = -1;
const ECLAIR_PURE_COMMAND_PARSE_ERROR: isize = -2;
const ECLAIR_PURE_COMMAND_INVALID_TID: isize = -3;
const ECLAIR_PURE_COMMAND_BUFFER_ERROR: isize = -4;
const BFD_OBJECT: c_int = 1;
const O_RDONLY: c_int = 0;
const ECLAIR_OPTIONS_OPEN_LINE: i32 = 1774;
static DEFAULT_KERNEL_PATH: &[u8] = b"./mckernel.img\0";
static DEFAULT_DUMP_PATH: &[u8] = b"./mcdump\0";
const CPU_TID_BASE: i32 = 1_000_000;
const ARCH_CLV_SPAN_NAME: &[u8] = b"x86_cpu_local_variables_span\0";
const ARCH_NAME: &[u8] = b"i386:x86-64\0";
const ARCH_REGS: usize = 21;
const PANIC_REGS_OFFSET: usize = 288;
const SC_PAGESIZE: c_int = 30;
const PF_INET: c_int = 2;
const SOCK_STREAM: c_int = 1;
const SOMAXCONN: c_int = 4096;

const CPU_LOCAL_VAR_SIZE: usize = 0;
const CURRENT_OFFSET: usize = 1;
const RUNQ_OFFSET: usize = 2;
const CPU_STATUS_OFFSET: usize = 3;
const IDLE_THREAD_OFFSET: usize = 4;
const CTX_OFFSET: usize = 5;
const SCHED_LIST_OFFSET: usize = 6;
const PROC_OFFSET: usize = 7;
const STATUS_OFFSET: usize = 8;
const PID_OFFSET: usize = 9;
const TID_OFFSET: usize = 10;

#[repr(C)]
pub struct EclairThreadInfo {
    next: *mut EclairThreadInfo,
    status: i32,
    pid: i32,
    tid: i32,
    cpu: i32,
    lcpu: i32,
    idle: i32,
    process: usize,
    clv: usize,
    arch_clv: usize,
}

#[repr(C)]
pub struct EclairOptions {
    cpu: u8,
    help: u8,
    kernel_path: *mut u8,
    dump_path: *mut u8,
    log_path: *mut u8,
    interactive: c_int,
    os_id: c_int,
    mcos_fd: c_int,
    print_idle: c_int,
}

#[repr(C)]
struct DumpMemChunk {
    addr: c_ulong,
    size: c_ulong,
}

#[repr(C)]
pub struct DumpMemChunksHeader {
    nr_chunks: c_int,
    kernel_base: c_ulong,
    phys_start: c_ulong,
}

#[repr(C)]
struct DumpArgs {
    cmd: c_int,
    level: u32,
    start: isize,
    size: isize,
    buf: *mut c_void,
    spare: [*mut c_void; 4],
}

#[repr(C)]
struct InAddr {
    s_addr: u32,
}

#[repr(C)]
struct SockAddrIn {
    sin_family: u16,
    sin_port: u16,
    sin_addr: InAddr,
    sin_zero: [u8; 8],
}

#[no_mangle]
pub static mut nsyms: isize = 0;
#[no_mangle]
pub static mut symtab: *mut *mut BfdSymbol = core::ptr::null_mut();
#[no_mangle]
pub static mut opt: EclairOptions = EclairOptions {
    cpu: 0,
    help: 0,
    kernel_path: core::ptr::null_mut(),
    dump_path: core::ptr::null_mut(),
    log_path: core::ptr::null_mut(),
    interactive: 0,
    os_id: 0,
    mcos_fd: -1,
    print_idle: 0,
};
#[no_mangle]
pub static mut symbfd: *mut c_void = core::ptr::null_mut();
#[no_mangle]
pub static mut dumpbfd: *mut c_void = core::ptr::null_mut();
#[no_mangle]
pub static mut mem_chunks: *mut DumpMemChunksHeader = core::ptr::null_mut();
#[no_mangle]
pub static mut PHYS_OFFSET: c_ulong = 0;
#[no_mangle]
pub static mut MAP_KERNEL_START: c_ulong = 0;
#[no_mangle]
pub static mut kernel_base: c_ulong = 0;
#[no_mangle]
pub static mut debug_constants: [usize; DEBUG_CONSTANTS_LEN] = [0; DEBUG_CONSTANTS_LEN];
#[no_mangle]
pub static mut remote_running: c_int = 0;
#[no_mangle]
pub static mut gdbpid: i32 = 0;

static mut TIHEAD: *mut EclairThreadInfo = core::ptr::null_mut();
static mut TITAILP: *mut *mut EclairThreadInfo = core::ptr::null_mut();
static mut CURR_THREAD: *mut EclairThreadInfo = core::ptr::null_mut();
static mut NUM_PROCESSORS: c_int = -1;
static mut F_DONE: c_int = 0;
static mut SOCK_FD: c_int = -1;
static mut IFP: *mut c_void = core::ptr::null_mut();
static mut OFP: *mut c_void = core::ptr::null_mut();

unsafe extern "C" {
    fn arch_setup_constants(fd: c_int) -> c_int;
    fn arch_read_kregs(ctx: c_ulong, kregs: *mut c_void) -> c_int;
    fn print_kregs(rbp: *mut u8, rbp_size: usize, kregs: *const c_void) -> c_int;
    fn virt_to_phys(va: usize) -> usize;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn perror(s: *const u8);
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn bfd_openr(filename: *const u8, target: *const u8) -> *mut c_void;
    fn bfd_fopen(filename: *const u8, target: *const u8, mode: *const u8, fd: c_int)
        -> *mut c_void;
    fn bfd_check_format(abfd: *mut c_void, format: c_int) -> c_int;
    fn eclair_bfd_get_symtab_upper_bound_bridge(abfd: *mut c_void) -> isize;
    fn eclair_bfd_canonicalize_symtab_bridge(
        abfd: *mut c_void,
        location: *mut *mut BfdSymbol,
    ) -> isize;
    fn bfd_get_section_by_name(abfd: *mut c_void, name: *const u8) -> *mut c_void;
    fn bfd_get_section_contents(
        abfd: *mut c_void,
        section: *mut c_void,
        location: *mut c_void,
        offset: isize,
        count: usize,
    ) -> c_int;
    fn bfd_perror(message: *const u8);
    fn printf(fmt: *const u8, ...) -> i32;
    fn fprintf(stream: *mut c_void, fmt: *const u8, ...) -> i32;
    fn getopt(argc: c_int, argv: *mut *mut u8, optstring: *const u8) -> c_int;
    static mut optarg: *mut u8;
    static mut optind: c_int;
    fn open(path: *const u8, oflag: c_int, ...) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn exit(status: c_int) -> !;
    fn kill(pid: i32, sig: i32) -> i32;
    static mut stderr: *mut c_void;
    fn sysconf(name: c_int) -> isize;
    fn signal(signum: c_int, handler: unsafe extern "C" fn(c_int)) -> usize;
    fn socket(domain: c_int, type_: c_int, protocol: c_int) -> c_int;
    fn listen(sockfd: c_int, backlog: c_int) -> c_int;
    fn getsockname(sockfd: c_int, addr: *mut c_void, addrlen: *mut u32) -> c_int;
    fn ntohs(netshort: u16) -> u16;
    fn fork() -> i32;
    fn execlp(file: *const u8, arg0: *const u8, ...) -> c_int;
    fn accept(sockfd: c_int, addr: *mut c_void, addrlen: *mut u32) -> c_int;
    fn fdopen(fd: c_int, mode: *const u8) -> *mut c_void;
    fn fgetc(stream: *mut c_void) -> c_int;
    fn fputc(c: c_int, stream: *mut c_void) -> c_int;
    fn fflush(stream: *mut c_void) -> c_int;
}

#[repr(C)]
pub struct BfdSection {
    name: *const u8,
    id: u32,
    index: u32,
    next: *mut BfdSection,
    prev: *mut BfdSection,
    flags: u32,
    vma: usize,
}

#[repr(C)]
pub struct BfdSymbol {
    the_bfd: *mut c_void,
    name: *const u8,
    value: usize,
    flags: u32,
    section: *mut BfdSection,
}

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

const ECLAIR_NOSYMBOL: usize = usize::MAX;
const ECLAIR_NOPHYS: usize = usize::MAX;
const PHYSMEM_NAME_SIZE: usize = 32;
const IHK_OS_DUMP: c_ulong = 0x112a06;
const DUMP_NMI: c_int = 1;
const DUMP_READ: c_int = 3;
const DUMP_SET_LEVEL: c_int = 6;
const DUMP_QUERY_NUM_MEM_AREAS: c_int = 7;
const DUMP_QUERY_MEM_AREAS: c_int = 8;
const DUMP_NMI_CONT: c_int = 10;
const DUMP_LEVEL_ALL: u32 = 0;
const SIGINT_CONST: i32 = 2;
const DEBUG_CONSTANTS_LEN: usize = 12;

#[no_mangle]
pub unsafe extern "C" fn lookup_symbol(name: *mut u8) -> usize {
    let Some(needle) = (unsafe { cstr_bytes(name as *const u8) }) else {
        return ECLAIR_NOSYMBOL;
    };

    let count = unsafe {
        if nsyms < 0 || symtab.is_null() {
            return ECLAIR_NOSYMBOL;
        }
        nsyms as usize
    };
    let mut idx = 0usize;
    while idx < count {
        let symbol = unsafe { *symtab.add(idx) };
        if !symbol.is_null() {
            let sym_name = unsafe { (*symbol).name };
            if let Some(candidate) = unsafe { cstr_bytes(sym_name) } {
                if bytes_eq(candidate, needle) {
                    let section = unsafe { (*symbol).section };
                    if !section.is_null() {
                        return unsafe { (*section).vma.wrapping_add((*symbol).value) };
                    }
                }
            }
        }
        idx += 1;
    }

    ECLAIR_NOSYMBOL
}

unsafe fn dump_mem_chunk_at(chunks: *mut DumpMemChunksHeader, idx: usize) -> *const DumpMemChunk {
    unsafe {
        (chunks as *const u8)
            .add(core::mem::size_of::<DumpMemChunksHeader>())
            .cast::<DumpMemChunk>()
            .add(idx)
    }
}

unsafe fn read_physmem(pa: usize, buf: *mut c_void, size: usize) -> c_int {
    let chunks = unsafe { mem_chunks };
    let mut chunk_index = 0usize;
    let mut found = false;
    let mut offset = 0isize;

    if !chunks.is_null() {
        let nr_chunks = unsafe { (*chunks).nr_chunks };
        if nr_chunks > 0 {
            while chunk_index < nr_chunks as usize {
                let chunk = unsafe { dump_mem_chunk_at(chunks, chunk_index) };
                let addr = unsafe { (*chunk).addr as usize };
                let chunk_size = unsafe { (*chunk).size as usize };
                if addr <= pa && pa.wrapping_add(size) <= addr.wrapping_add(chunk_size) {
                    offset = pa.wrapping_sub(addr) as isize;
                    found = true;
                    break;
                }
                chunk_index += 1;
            }
        }
    }

    if !found {
        let mut line = [0u8; 96];
        let n = unsafe { eclair_read_physmem_invalid_result(line.as_mut_ptr(), line.len(), pa) };
        if n >= 0 {
            unsafe {
                printf(b"%s\n\0".as_ptr(), line.as_ptr());
            }
        } else {
            unsafe {
                printf(b"read_physmem: invalid addr 0x%lx\n\0".as_ptr(), pa);
            }
        }
        return 1;
    }

    let mut physmem_name = [0u8; PHYSMEM_NAME_SIZE];
    unsafe {
        eclair_physmem_name_result(physmem_name.as_mut_ptr(), chunk_index as c_int);
    }

    let dump = unsafe { dumpbfd };
    let section = unsafe { bfd_get_section_by_name(dump, physmem_name.as_ptr()) };
    if section.is_null() {
        unsafe {
            bfd_perror(b"read_physmem:bfd_get_section_by_name(physmem)\0".as_ptr());
        }
        return 1;
    }

    let ok = unsafe { bfd_get_section_contents(dump, section, buf, offset, size) };
    if ok == 0 {
        unsafe {
            bfd_perror(b"read_physmem:bfd_get_section_contents\0".as_ptr());
        }
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn read_mem(va: usize, buf: *mut c_void, size: usize) -> c_int {
    let pa = unsafe { virt_to_phys(va) };
    if pa == ECLAIR_NOPHYS {
        return 1;
    }

    let error = if unsafe { opt.interactive } != 0 {
        let mut args = DumpArgs {
            cmd: DUMP_READ,
            level: 0,
            start: pa as isize,
            size: size as isize,
            buf,
            spare: [core::ptr::null_mut(); 4],
        };
        unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) }
    } else {
        unsafe { read_physmem(pa, buf, size) }
    };

    if error != 0 {
        unsafe {
            perror(b"read_mem:read_physmem\0".as_ptr());
        }
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn read_64(va: usize, buf: *mut c_void) -> i32 {
    unsafe { read_mem(va, buf, core::mem::size_of::<u64>()) }
}

#[no_mangle]
pub unsafe extern "C" fn read_32(va: usize, buf: *mut c_void) -> i32 {
    unsafe { read_mem(va, buf, core::mem::size_of::<u32>()) }
}

#[no_mangle]
pub unsafe extern "C" fn read_symbol_64(name: *mut u8, buf: *mut c_void) -> i32 {
    let va = unsafe { lookup_symbol(name) };
    if va == ECLAIR_NOSYMBOL {
        let mut line = [0u8; 128];
        let n = unsafe {
            eclair_lookup_failed_result(
                line.as_mut_ptr(),
                line.len(),
                b"read_symbol_64\0".as_ptr(),
                name as *const u8,
            )
        };
        if n >= 0 {
            unsafe {
                printf(b"%s\n\0".as_ptr(), line.as_ptr());
            }
        } else {
            unsafe {
                printf(
                    b"read_symbol_64(%s):lookup_symbol failed\n\0".as_ptr(),
                    name as *const u8,
                );
            }
        }
        return 1;
    }

    let error = unsafe { read_64(va, buf) };
    if error != 0 {
        unsafe {
            printf(
                b"read_symbol_64(%s):read_64(%#lx) failed\0".as_ptr(),
                name as *const u8,
                va,
            );
        }
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn print_bin(
    buf: *mut u8,
    buf_size: usize,
    data: *mut c_void,
    size: usize,
) -> isize {
    unsafe { eclair_print_bin_result(buf, buf_size, data as *const u8, size) }
}

#[no_mangle]
pub unsafe extern "C" fn intr_handler(_dummy: i32) {
    let pid = unsafe { gdbpid };
    unsafe {
        kill(pid, SIGINT_CONST);
    }
}

#[no_mangle]
pub unsafe extern "C" fn print_usage() {
    let mut line = [0u8; 128];
    let n = unsafe { eclair_usage_result(line.as_mut_ptr(), line.len()) };
    if n >= 0 {
        unsafe {
            fprintf(stderr, b"%s\n\0".as_ptr(), line.as_ptr());
        }
    } else {
        unsafe {
            fprintf(
                stderr,
                b"usage: eclair [-ch] [-d <mcdump>] [-k <kernel.img>]\n\0".as_ptr(),
            );
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn apply_remote_action(action: i32, continue_error: *const u8) -> i32 {
    let cmd = match action {
        ECLAIR_REMOTE_ACTION_NONE => return 0,
        ECLAIR_REMOTE_ACTION_NMI => DUMP_NMI,
        ECLAIR_REMOTE_ACTION_CONTINUE => DUMP_NMI_CONT,
        _ => return -1,
    };

    let mut args = DumpArgs {
        cmd,
        level: 0,
        start: 0,
        size: 0,
        buf: core::ptr::null_mut(),
        spare: [core::ptr::null_mut(); 4],
    };
    let error = unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) };
    if error != 0 {
        let message = if action == ECLAIR_REMOTE_ACTION_NMI || continue_error.is_null() {
            b"DUMP_NMI\0".as_ptr()
        } else {
            continue_error
        };
        unsafe {
            perror(message);
        }
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn setup_symbols(fname: *mut u8) -> c_int {
    let abfd = unsafe { bfd_openr(fname as *const u8, core::ptr::null()) };
    unsafe {
        symbfd = abfd;
    }
    if abfd.is_null() {
        unsafe {
            bfd_perror(b"bfd_openr\0".as_ptr());
        }
        return 1;
    }

    if unsafe { bfd_check_format(abfd, BFD_OBJECT) } == 0 {
        unsafe {
            bfd_perror(b"bfd_check_format\0".as_ptr());
        }
        return 1;
    }

    let needs = unsafe { eclair_bfd_get_symtab_upper_bound_bridge(abfd) };
    if needs < 0 {
        unsafe {
            bfd_perror(b"bfd_get_symtab_upper_bound\0".as_ptr());
        }
        return 1;
    }

    if needs == 0 {
        unsafe {
            printf(b"no symbols\n\0".as_ptr());
        }
        return 1;
    }

    let table = unsafe { malloc(needs as usize) } as *mut *mut BfdSymbol;
    if table.is_null() {
        unsafe {
            perror(b"malloc\0".as_ptr());
        }
        return 1;
    }
    unsafe {
        symtab = table;
    }

    let count = unsafe { eclair_bfd_canonicalize_symtab_bridge(abfd, table) };
    if count < 0 {
        unsafe {
            bfd_perror(b"bfd_canonicalize_symtab\0".as_ptr());
        }
        return 1;
    }
    unsafe {
        nsyms = count;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn setup_dump_interactive() -> c_int {
    let mut args = DumpArgs {
        cmd: DUMP_SET_LEVEL,
        level: DUMP_LEVEL_ALL,
        start: 0,
        size: 0,
        buf: core::ptr::null_mut(),
        spare: [core::ptr::null_mut(); 4],
    };
    if unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) } != 0 {
        unsafe {
            perror(b"DUMP_SET_LEVEL\0".as_ptr());
        }
        return 1;
    }

    args.cmd = DUMP_NMI;
    if unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) } != 0 {
        unsafe {
            perror(b"DUMP_NMI\0".as_ptr());
        }
        return 1;
    }

    unsafe {
        remote_running = 0;
    }

    args.cmd = DUMP_QUERY_NUM_MEM_AREAS;
    args.size = 0;
    if unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) } != 0 {
        unsafe {
            perror(b"DUMP_QUERY_NUM_MEM_AREAS\0".as_ptr());
        }
        return 1;
    }

    let mem_size = args.size as usize;
    let chunks = unsafe { malloc(mem_size) } as *mut DumpMemChunksHeader;
    if chunks.is_null() {
        unsafe {
            perror(b"allocating mem_chunks\0".as_ptr());
        }
        return 1;
    }
    unsafe {
        core::ptr::write_bytes(chunks.cast::<u8>(), 0, mem_size);
        mem_chunks = chunks;
    }

    args.cmd = DUMP_QUERY_MEM_AREAS;
    args.buf = chunks.cast::<c_void>();
    if unsafe { ioctl(opt.mcos_fd, IHK_OS_DUMP, &mut args as *mut DumpArgs) } != 0 {
        unsafe {
            perror(b"DUMP_QUERY_MEM_AREAS\0".as_ptr());
        }
        return 1;
    }

    unsafe {
        kernel_base = (*chunks).kernel_base;
        PHYS_OFFSET = (*chunks).phys_start;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn setup_dump(_fname: *mut u8) -> c_int {
    let dump = unsafe {
        bfd_fopen(
            opt.dump_path as *const u8,
            core::ptr::null(),
            b"r\0".as_ptr(),
            -1,
        )
    };
    unsafe {
        dumpbfd = dump;
    }
    if dump.is_null() {
        unsafe {
            bfd_perror(b"bfd_fopen\0".as_ptr());
        }
        return 1;
    }

    if unsafe { bfd_check_format(dump, BFD_OBJECT) } == 0 {
        unsafe {
            bfd_perror(b"bfd_check_format\0".as_ptr());
        }
        return 1;
    }

    let physchunks = unsafe { bfd_get_section_by_name(dump, b"physchunks\0".as_ptr()) };
    if physchunks.is_null() {
        unsafe {
            bfd_perror(b"bfd_get_section_by_name\0".as_ptr());
        }
        return 1;
    }

    let mut info = DumpMemChunksHeader {
        nr_chunks: 0,
        kernel_base: 0,
        phys_start: 0,
    };
    if unsafe {
        bfd_get_section_contents(
            dump,
            physchunks,
            (&mut info as *mut DumpMemChunksHeader).cast::<c_void>(),
            0,
            core::mem::size_of::<DumpMemChunksHeader>(),
        )
    } == 0
    {
        unsafe {
            bfd_perror(b"read_physmem:bfd_get_section_contents(mem_size)\0".as_ptr());
        }
        return 1;
    }

    let mem_size = core::mem::size_of::<DumpMemChunksHeader>()
        .wrapping_add(core::mem::size_of::<DumpMemChunk>().wrapping_mul(info.nr_chunks as usize));
    let chunks = unsafe { malloc(mem_size) } as *mut DumpMemChunksHeader;
    if chunks.is_null() {
        unsafe {
            perror(b"allocating mem chunks descriptor: \0".as_ptr());
        }
        return 1;
    }

    if unsafe { bfd_get_section_contents(dump, physchunks, chunks.cast::<c_void>(), 0, mem_size) }
        == 0
    {
        unsafe {
            bfd_perror(b"read_physmem:bfd_get_section_contents(mem_chunks)\0".as_ptr());
        }
        return 1;
    }

    unsafe {
        mem_chunks = chunks;
        kernel_base = (*chunks).kernel_base;
        PHYS_OFFSET = (*chunks).phys_start;
    }

    let mut idx = 0usize;
    while idx < info.nr_chunks as usize {
        let mut physmem_name = [0u8; PHYSMEM_NAME_SIZE];
        unsafe {
            eclair_physmem_name_result(physmem_name.as_mut_ptr(), idx as c_int);
        }
        let section = unsafe { bfd_get_section_by_name(dump, physmem_name.as_ptr()) };
        if section.is_null() {
            unsafe {
                bfd_perror(b"read_physmem:bfd_get_section_by_name(physmem)\0".as_ptr());
            }
            return 1;
        }
        idx += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn setup_constants() -> c_int {
    if unsafe { arch_setup_constants(opt.mcos_fd) } != 0 {
        unsafe {
            fprintf(stderr, b"error: setting up arch constants\n\0".as_ptr());
        }
        return 1;
    }

    let va = unsafe { lookup_symbol(b"debug_constants\0".as_ptr() as *mut u8) };
    if va == ECLAIR_NOSYMBOL {
        unsafe {
            perror(b"debug_constants\0".as_ptr());
        }
        return 1;
    }

    let constants = core::ptr::addr_of_mut!(debug_constants).cast::<c_void>();
    if unsafe {
        read_mem(
            va,
            constants,
            core::mem::size_of::<[usize; DEBUG_CONSTANTS_LEN]>(),
        )
    } != 0
    {
        unsafe {
            perror(b"debug_constants\0".as_ptr());
        }
        return 1;
    }

    0
}

unsafe fn debug_const(index: usize) -> usize {
    unsafe {
        *core::ptr::addr_of!(debug_constants)
            .cast::<usize>()
            .add(index)
    }
}

unsafe fn reset_thread_list() {
    let mut current = unsafe { TIHEAD };
    while !current.is_null() {
        let next = unsafe { (*current).next };
        unsafe {
            free(current.cast::<c_void>());
        }
        current = next;
    }

    unsafe {
        TIHEAD = core::ptr::null_mut();
        TITAILP = core::ptr::addr_of_mut!(TIHEAD);
        CURR_THREAD = core::ptr::null_mut();
    }
}

unsafe fn append_thread(thread: *mut EclairThreadInfo) {
    unsafe {
        if TITAILP.is_null() {
            TITAILP = core::ptr::addr_of_mut!(TIHEAD);
        }
        *TITAILP = thread;
        TITAILP = core::ptr::addr_of_mut!((*thread).next);
        if CURR_THREAD.is_null() {
            CURR_THREAD = thread;
        }
    }
}

unsafe fn alloc_thread() -> *mut EclairThreadInfo {
    let thread =
        unsafe { malloc(core::mem::size_of::<EclairThreadInfo>()) as *mut EclairThreadInfo };
    if !thread.is_null() {
        unsafe {
            core::ptr::write_bytes(
                thread.cast::<u8>(),
                0,
                core::mem::size_of::<EclairThreadInfo>(),
            );
        }
    }
    thread
}

unsafe fn read_symbol_usize(name: &'static [u8], value: *mut usize) -> c_int {
    unsafe { read_symbol_64(name.as_ptr() as *mut u8, value.cast::<c_void>()) }
}

#[no_mangle]
pub unsafe extern "C" fn setup_threads() -> c_int {
    let mut raw_processors = 0usize;
    if unsafe { read_symbol_usize(b"num_processors\0", &mut raw_processors) } != 0 {
        unsafe {
            perror(b"num_processors\0".as_ptr());
        }
        return 1;
    }
    unsafe {
        NUM_PROCESSORS = raw_processors as c_int;
    }

    let mut locals = 0usize;
    if unsafe { read_symbol_usize(b"locals\0", &mut locals) } != 0 {
        unsafe {
            perror(b"locals\0".as_ptr());
        }
        return 1;
    }

    let mut locals_span = 0usize;
    if unsafe { read_symbol_usize(ARCH_CLV_SPAN_NAME, &mut locals_span) } != 0 {
        let page_size = unsafe { sysconf(SC_PAGESIZE) };
        locals_span = if page_size > 0 {
            page_size as usize
        } else {
            4096
        };
    }

    let mut clv = 0usize;
    if unsafe { read_symbol_usize(b"clv\0", &mut clv) } != 0 {
        unsafe {
            perror(b"clv\0".as_ptr());
        }
        return 1;
    }

    unsafe {
        reset_thread_list();
    }

    let processors = unsafe { NUM_PROCESSORS };
    let mut cpu = 0;
    while cpu < processors {
        let v = clv.wrapping_add(cpu as usize * unsafe { debug_const(CPU_LOCAL_VAR_SIZE) });
        let mut current = 0usize;
        if unsafe {
            read_64(
                v.wrapping_add(debug_const(CURRENT_OFFSET)),
                (&mut current as *mut usize).cast::<c_void>(),
            )
        } != 0
        {
            unsafe {
                perror(b"current\0".as_ptr());
            }
            return 1;
        }

        let head = v.wrapping_add(unsafe { debug_const(RUNQ_OFFSET) });
        let mut entry = 0usize;
        if unsafe { read_64(head, (&mut entry as *mut usize).cast::<c_void>()) } != 0 {
            unsafe {
                perror(b"runq head\0".as_ptr());
            }
            return 1;
        }

        while entry != head {
            let thread_addr = entry.wrapping_sub(unsafe { debug_const(SCHED_LIST_OFFSET) });
            let mut proc_addr = 0usize;
            let mut status = 0i32;
            let mut pid = 0i32;
            let mut tid = 0i32;

            if unsafe {
                read_64(
                    thread_addr.wrapping_add(debug_const(PROC_OFFSET)),
                    (&mut proc_addr as *mut usize).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"proc\0".as_ptr());
                }
                return 1;
            }
            if unsafe {
                read_32(
                    thread_addr.wrapping_add(debug_const(STATUS_OFFSET)),
                    (&mut status as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"status\0".as_ptr());
                }
                return 1;
            }
            if unsafe {
                read_32(
                    proc_addr.wrapping_add(debug_const(PID_OFFSET)),
                    (&mut pid as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"pid\0".as_ptr());
                }
                return 1;
            }
            if unsafe {
                read_32(
                    thread_addr.wrapping_add(debug_const(TID_OFFSET)),
                    (&mut tid as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"tid\0".as_ptr());
                }
                return 1;
            }

            let ti = unsafe { alloc_thread() };
            if ti.is_null() {
                unsafe {
                    perror(b"malloc\0".as_ptr());
                }
                return 1;
            }
            unsafe {
                (*ti).status = status;
                (*ti).pid = pid;
                (*ti).tid = tid;
                (*ti).cpu = if thread_addr == current { cpu } else { -1 };
                (*ti).lcpu = cpu;
                (*ti).process = thread_addr;
                (*ti).idle = 0;
                (*ti).clv = v;
                (*ti).arch_clv = locals.wrapping_add(locals_span.wrapping_mul(cpu as usize));
                append_thread(ti);
            }

            if unsafe { read_64(entry, (&mut entry as *mut usize).cast::<c_void>()) } != 0 {
                unsafe {
                    perror(b"process2\0".as_ptr());
                }
                return 1;
            }
        }

        cpu += 1;
    }

    if unsafe { opt.print_idle } != 0 {
        let mut cpu = 0;
        while cpu < processors {
            let v = clv.wrapping_add(cpu as usize * unsafe { debug_const(CPU_LOCAL_VAR_SIZE) });
            let mut current = 0usize;
            if unsafe {
                read_64(
                    v.wrapping_add(debug_const(CURRENT_OFFSET)),
                    (&mut current as *mut usize).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"current\0".as_ptr());
                }
                return 1;
            }

            let thread_addr = v.wrapping_add(unsafe { debug_const(IDLE_THREAD_OFFSET) });
            let mut proc_addr = 0usize;
            let mut status = 0i32;
            let mut tid = 0i32;
            if unsafe {
                read_64(
                    thread_addr.wrapping_add(debug_const(PROC_OFFSET)),
                    (&mut proc_addr as *mut usize).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"proc\0".as_ptr());
                }
                return 1;
            }
            if unsafe {
                read_32(
                    thread_addr.wrapping_add(debug_const(STATUS_OFFSET)),
                    (&mut status as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"status\0".as_ptr());
                }
                return 1;
            }
            if unsafe {
                read_32(
                    thread_addr.wrapping_add(debug_const(TID_OFFSET)),
                    (&mut tid as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"tid\0".as_ptr());
                }
                return 1;
            }

            let ti = unsafe { alloc_thread() };
            if ti.is_null() {
                unsafe {
                    perror(b"malloc\0".as_ptr());
                }
                return 1;
            }
            unsafe {
                (*ti).status = status;
                (*ti).pid = 1;
                (*ti).tid = 2_000_000_000i32.wrapping_add(tid);
                (*ti).cpu = if thread_addr == current { cpu } else { -1 };
                (*ti).lcpu = cpu;
                (*ti).process = thread_addr;
                (*ti).idle = 1;
                (*ti).clv = v;
                (*ti).arch_clv = locals.wrapping_add(locals_span.wrapping_mul(cpu as usize));
                append_thread(ti);
            }

            cpu += 1;
        }
    }

    if unsafe { TIHEAD.is_null() } {
        unsafe {
            printf(b"No threads found, forcing CPU mode.\n\0".as_ptr());
            opt.cpu = 1;
        }
    }

    if unsafe { opt.cpu } != 0 {
        let mut cpu = 0;
        while cpu < processors {
            let v = clv.wrapping_add(cpu as usize * unsafe { debug_const(CPU_LOCAL_VAR_SIZE) });
            let mut status = 0i32;
            if unsafe {
                read_32(
                    v.wrapping_add(debug_const(CPU_STATUS_OFFSET)),
                    (&mut status as *mut i32).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"cpu.status\0".as_ptr());
                }
                return 1;
            }
            if status == 0 {
                cpu += 1;
                continue;
            }

            let mut current = 0usize;
            if unsafe {
                read_64(
                    v.wrapping_add(debug_const(CURRENT_OFFSET)),
                    (&mut current as *mut usize).cast::<c_void>(),
                )
            } != 0
            {
                unsafe {
                    perror(b"current\0".as_ptr());
                }
                return 1;
            }

            let ti = unsafe { alloc_thread() };
            if ti.is_null() {
                unsafe {
                    perror(b"malloc\0".as_ptr());
                }
                return 1;
            }
            unsafe {
                (*ti).status = status << 16;
                (*ti).pid = CPU_TID_BASE + cpu;
                (*ti).tid = CPU_TID_BASE + cpu;
                (*ti).cpu = cpu;
                (*ti).lcpu = cpu;
                (*ti).process = current;
                (*ti).idle = 1;
                (*ti).clv = v;
                (*ti).arch_clv = locals.wrapping_add(locals_span.wrapping_mul(cpu as usize));
                append_thread(ti);
            }

            cpu += 1;
        }
    }

    if unsafe { TIHEAD.is_null() } {
        unsafe {
            printf(b"thread not found\n\0".as_ptr());
        }
        return 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn start_gdb() -> c_int {
    if unsafe { opt.interactive } != 0 {
        unsafe {
            signal(SIGINT_CONST, intr_handler);
        }
    }

    unsafe {
        SOCK_FD = socket(PF_INET, SOCK_STREAM, 0);
        if SOCK_FD < 0 {
            perror(b"socket\0".as_ptr());
            return 1;
        }
        if listen(SOCK_FD, SOMAXCONN) != 0 {
            perror(b"listen\0".as_ptr());
            return 1;
        }
    }

    let mut sin = SockAddrIn {
        sin_family: 0,
        sin_port: 0,
        sin_addr: InAddr { s_addr: 0 },
        sin_zero: [0; 8],
    };
    let mut slen = core::mem::size_of::<SockAddrIn>() as u32;
    if unsafe {
        getsockname(
            SOCK_FD,
            (&mut sin as *mut SockAddrIn).cast::<c_void>(),
            &mut slen,
        )
    } != 0
    {
        unsafe {
            perror(b"getsockname\0".as_ptr());
        }
        return 1;
    }

    unsafe {
        gdbpid = fork();
        if gdbpid == -1 {
            perror(b"fork\0".as_ptr());
            return 1;
        }
        if gdbpid == 0 {
            let mut target = [0u8; 32];
            eclair_gdb_target_result(
                target.as_mut_ptr(),
                target.len(),
                ntohs(sin.sin_port) as u32,
            );
            execlp(
                b"gdb\0".as_ptr(),
                b"eclair\0".as_ptr(),
                b"-q\0".as_ptr(),
                b"-ex\0".as_ptr(),
                b"set prompt (eclair) \0".as_ptr(),
                b"-ex\0".as_ptr(),
                target.as_ptr(),
                opt.kernel_path as *const u8,
                b"-ex\0".as_ptr(),
                b"set pagination off\0".as_ptr(),
                core::ptr::null::<u8>(),
            );
            perror(b"execlp\0".as_ptr());
            return 3;
        }

        let ss = accept(SOCK_FD, core::ptr::null_mut(), core::ptr::null_mut());
        if ss < 0 {
            perror(b"accept\0".as_ptr());
            return 1;
        }
        IFP = fdopen(ss, b"r\0".as_ptr());
        if IFP.is_null() {
            perror(b"fdopen(r)\0".as_ptr());
            return 1;
        }
        OFP = fdopen(ss, b"r+\0".as_ptr());
        if OFP.is_null() {
            perror(b"fdopen(r+)\0".as_ptr());
            return 1;
        }
    }

    0
}

unsafe fn response_left(res: *mut u8, rbp: *mut u8, res_size: usize) -> usize {
    let used = (rbp as usize).wrapping_sub(res as usize);
    res_size.saturating_sub(used)
}

unsafe fn bump_response_ptr(rbp: &mut *mut u8, n: isize) -> bool {
    if n < 0 {
        return false;
    }
    unsafe {
        *rbp = (*rbp).add(n as usize);
    }
    true
}

unsafe fn handle_remote_command(cmd_kind: i32, rbp: &mut *mut u8, res: *mut u8, res_size: usize) {
    let mut remote_action = 0;
    let mut next_remote_running = 0;
    let mut set_done = 0;
    if unsafe {
        eclair_remote_command_plan_result(
            cmd_kind,
            opt.interactive,
            remote_running,
            &mut remote_action,
            &mut next_remote_running,
            &mut set_done,
        )
    } != 0
    {
        return;
    }
    if unsafe { apply_remote_action(remote_action, b"DUMP_NMI_CONT for continue\0".as_ptr()) } != 0
    {
        return;
    }
    unsafe {
        remote_running = next_remote_running;
    }
    let n = unsafe {
        eclair_simple_response_result(
            *rbp,
            response_left(res, *rbp, res_size),
            cmd_kind,
            opt.interactive,
            remote_running,
        )
    };
    unsafe {
        bump_response_ptr(rbp, n);
    }
    if cmd_kind == ECLAIR_CMD_DETACH {
        unsafe {
            F_DONE = set_done;
        }
    }
}

unsafe fn report_pure_command_error(p: *const u8, result: isize, error_tid: i32, error_kind: i32) {
    if result == ECLAIR_PURE_COMMAND_PARSE_ERROR {
        unsafe {
            if error_kind == ECLAIR_CMD_HG {
                printf(b"cannot parse 'Hg' cmd: \"%s\"\n\0".as_ptr(), p.add(2));
            } else if error_kind == ECLAIR_CMD_THREAD_ALIVE {
                printf(b"cannot parse 'T' cmd: \"%s\"\n\0".as_ptr(), p.add(1));
            } else if error_kind == ECLAIR_CMD_QTHREAD_EXTRA_INFO {
                printf(
                    b"cannot parse 'qThreadExtraInfo' cmd: \"%s\"\n\0".as_ptr(),
                    p.add(17),
                );
            }
        }
    } else if result == ECLAIR_PURE_COMMAND_INVALID_TID {
        unsafe {
            printf(b"invalid tid %#x\n\0".as_ptr(), error_tid);
        }
    }
}

unsafe fn command_regs(rbp: &mut *mut u8, res: *mut u8, res_size: usize) {
    let current = unsafe { CURR_THREAD };
    if current.is_null() {
        return;
    }
    if unsafe { (*current).cpu } < 0 {
        let mut kregs = [0usize; 11];
        let ctx = unsafe { (*current).process.wrapping_add(debug_const(CTX_OFFSET)) };
        if unsafe { arch_read_kregs(ctx as c_ulong, kregs.as_mut_ptr().cast::<c_void>()) } != 0 {
            unsafe {
                perror(b"arch_read_kregs\0".as_ptr());
            }
            return;
        }
        let n = unsafe {
            print_kregs(
                *rbp,
                response_left(res, *rbp, res_size),
                kregs.as_ptr().cast(),
            )
        };
        unsafe {
            bump_response_ptr(rbp, n as isize);
        }
    } else {
        let mut regs = [0usize; ARCH_REGS];
        let addr = unsafe { (*current).arch_clv.wrapping_add(PANIC_REGS_OFFSET) };
        if unsafe {
            read_mem(
                addr,
                regs.as_mut_ptr().cast::<c_void>(),
                core::mem::size_of::<[usize; ARCH_REGS]>(),
            )
        } != 0
        {
            unsafe {
                perror(b"read_mem\0".as_ptr());
            }
            return;
        }
        let n = unsafe {
            print_bin(
                *rbp,
                response_left(res, *rbp, res_size),
                regs.as_mut_ptr().cast::<c_void>(),
                core::mem::size_of::<[usize; ARCH_REGS]>().wrapping_sub(4),
            )
        };
        unsafe {
            bump_response_ptr(rbp, n);
        }
    }
}

unsafe fn command_memory(p: *const u8, rbp: &mut *mut u8, res: *mut u8, res_size: usize) {
    let mut start = 0usize;
    let mut size = 0usize;
    if unsafe { eclair_parse_memory_request_result(p, &mut start, &mut size) } != 0 {
        return;
    }

    let end = start.wrapping_add(size);
    let mut addr = start;
    while addr < end {
        let mut byte = 0u8;
        if unsafe { read_mem(addr, (&mut byte as *mut u8).cast::<c_void>(), 1) } != 0 {
            byte = 0;
        }
        let n = unsafe {
            print_bin(
                *rbp,
                response_left(res, *rbp, res_size),
                (&mut byte as *mut u8).cast::<c_void>(),
                1,
            )
        };
        if !unsafe { bump_response_ptr(rbp, n) } {
            return;
        }
        addr = addr.wrapping_add(1);
    }
}

#[no_mangle]
pub unsafe extern "C" fn command(cmd: *const u8, res: *mut u8, res_size: usize) {
    if res.is_null() || res_size == 0 {
        return;
    }
    let mut rbp = res;
    let p = cmd;
    let cmd_kind = unsafe { eclair_gdb_command_kind_result(p, opt.interactive) };
    let mut error_tid = 0;
    let mut error_kind = cmd_kind;

    let n = unsafe {
        eclair_pure_command_response_result(
            p,
            cmd_kind,
            rbp,
            response_left(res, rbp, res_size),
            TIHEAD,
            core::ptr::addr_of_mut!(CURR_THREAD),
            opt.interactive,
            remote_running,
            MAP_KERNEL_START as usize,
            ARCH_NAME.as_ptr(),
            &mut error_tid,
            &mut error_kind,
        )
    };
    if n >= 0 {
        unsafe {
            bump_response_ptr(&mut rbp, n);
            finish_cstr(res, rbp as usize - res as usize, res_size);
        }
        return;
    }
    if n != ECLAIR_PURE_COMMAND_NOT_HANDLED {
        unsafe {
            report_pure_command_error(p, n, error_tid, error_kind);
            finish_cstr(res, rbp as usize - res as usize, res_size);
        }
        return;
    }

    match cmd_kind {
        ECLAIR_CMD_VCTRLC | ECLAIR_CMD_CTRLC | ECLAIR_CMD_CONTINUE | ECLAIR_CMD_DETACH => unsafe {
            handle_remote_command(cmd_kind, &mut rbp, res, res_size);
        },
        ECLAIR_CMD_REGS => unsafe {
            command_regs(&mut rbp, res, res_size);
        },
        ECLAIR_CMD_MEMORY => unsafe {
            command_memory(p, &mut rbp, res, res_size);
        },
        ECLAIR_CMD_QFTHREADINFO => unsafe {
            if opt.interactive != 0 {
                if setup_threads() != 0 {
                    perror(b"setup_threads\0".as_ptr());
                    exit(1);
                }
            }
            let n = eclair_thread_list_result(rbp, response_left(res, rbp, res_size), TIHEAD);
            bump_response_ptr(&mut rbp, n);
        },
        _ => {}
    }

    unsafe {
        finish_cstr(res, rbp as usize - res as usize, res_size);
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
pub unsafe extern "C" fn eclair_packet_step_result(
    input: i32,
    interactive: i32,
    mode: *mut i32,
    sum: *mut u8,
    check: *mut u8,
    lbuf: *mut u8,
    lbuf_size: usize,
    lpos: *mut usize,
    cbuf: *mut u8,
    cbuf_size: usize,
) -> i32 {
    if mode.is_null()
        || sum.is_null()
        || check.is_null()
        || lbuf.is_null()
        || lpos.is_null()
        || cbuf.is_null()
        || lbuf_size == 0
        || cbuf_size < 3
    {
        return ECLAIR_PACKET_STEP_ERROR;
    }

    let byte = input as u8;
    let state = unsafe { *mode };
    match state {
        0 => {
            if byte == b'$' {
                unsafe {
                    *mode = 1;
                    *sum = 0;
                    *lpos = 0;
                    *lbuf = 0;
                }
            } else if interactive != 0 && byte == 0x03 {
                let mut pos = 0usize;
                let ok = unsafe { write_lit_checked(lbuf, &mut pos, lbuf_size, b"Ctrl-C\0") };
                unsafe {
                    finish_cstr(lbuf, pos, lbuf_size);
                    *lpos = pos;
                    *mode = 0;
                }
                if ok {
                    return ECLAIR_PACKET_STEP_INTERRUPT;
                }
                return ECLAIR_PACKET_STEP_ERROR;
            }
            ECLAIR_PACKET_STEP_NONE
        }
        1 => {
            if byte == b'#' {
                let pos = unsafe { *lpos };
                unsafe {
                    finish_cstr(lbuf, pos, lbuf_size);
                    *mode = 2;
                }
                return ECLAIR_PACKET_STEP_NONE;
            }

            let pos = unsafe { *lpos };
            if pos + 1 >= lbuf_size {
                unsafe {
                    *mode = 0;
                    finish_cstr(lbuf, pos, lbuf_size);
                }
                return ECLAIR_PACKET_STEP_ERROR;
            }
            unsafe {
                *sum = (*sum).wrapping_add(byte);
                *lbuf.add(pos) = byte;
                *lpos = pos + 1;
                finish_cstr(lbuf, pos + 1, lbuf_size);
            }
            ECLAIR_PACKET_STEP_NONE
        }
        2 => {
            unsafe {
                *cbuf = byte;
                *mode = 3;
            }
            ECLAIR_PACKET_STEP_NONE
        }
        3 => {
            unsafe {
                *cbuf.add(1) = byte;
                *cbuf.add(2) = 0;
            }
            let parsed = unsafe { eclair_parse_packet_checksum_result(cbuf, check) };
            unsafe {
                *mode = 0;
            }
            if parsed != 0 || unsafe { *check != *sum } {
                ECLAIR_PACKET_STEP_BAD
            } else {
                ECLAIR_PACKET_STEP_READY
            }
        }
        _ => {
            unsafe {
                *mode = 0;
            }
            ECLAIR_PACKET_STEP_NONE
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn eclair_remote_command_plan_result(
    cmd_kind: i32,
    interactive: i32,
    remote_running_state: i32,
    action: *mut i32,
    next_remote_running: *mut i32,
    set_done: *mut i32,
) -> i32 {
    if action.is_null() || next_remote_running.is_null() || set_done.is_null() {
        return -1;
    }

    unsafe {
        *action = ECLAIR_REMOTE_ACTION_NONE;
        *next_remote_running = remote_running_state;
        *set_done = 0;
    }

    match cmd_kind {
        ECLAIR_CMD_VCTRLC | ECLAIR_CMD_CTRLC => {
            if interactive != 0 && remote_running_state != 0 {
                unsafe {
                    *action = ECLAIR_REMOTE_ACTION_NMI;
                    *next_remote_running = 0;
                }
            }
            0
        }
        ECLAIR_CMD_CONTINUE => {
            if interactive != 0 && remote_running_state == 0 {
                unsafe {
                    *action = ECLAIR_REMOTE_ACTION_CONTINUE;
                    *next_remote_running = 1;
                }
            }
            0
        }
        ECLAIR_CMD_DETACH => {
            unsafe {
                *set_done = 1;
            }
            if interactive != 0 && remote_running_state == 0 {
                unsafe {
                    *action = ECLAIR_REMOTE_ACTION_CONTINUE;
                    *next_remote_running = 1;
                }
            }
            0
        }
        _ => -1,
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
pub unsafe extern "C" fn options(argc: c_int, argv: *mut *mut u8) {
    unsafe {
        opt = EclairOptions {
            cpu: 0,
            help: 0,
            kernel_path: DEFAULT_KERNEL_PATH.as_ptr() as *mut u8,
            dump_path: DEFAULT_DUMP_PATH.as_ptr() as *mut u8,
            log_path: core::ptr::null_mut(),
            interactive: 0,
            os_id: 0,
            mcos_fd: -1,
            print_idle: 0,
        };
        optind = 1;
        optarg = core::ptr::null_mut();
    }

    loop {
        let c = unsafe { getopt(argc, argv, b"ilcd:hk:o:\0".as_ptr()) };
        if c < 0 {
            break;
        }

        match c as u8 {
            b'h' | b'?' => unsafe {
                opt.help = 1;
            },
            b'c' => unsafe {
                opt.cpu = 1;
            },
            b'k' => unsafe {
                opt.kernel_path = optarg;
            },
            b'd' => unsafe {
                opt.dump_path = optarg;
            },
            b'i' => unsafe {
                opt.interactive = 1;
            },
            b'o' => unsafe {
                opt.os_id = eclair_parse_i32_result(optarg);
            },
            b'l' => unsafe {
                opt.print_idle = 1;
            },
            _ => {}
        }
    }

    if unsafe { optind < argc } {
        unsafe {
            opt.help = 1;
        }
    }

    if unsafe { opt.interactive != 0 } {
        let mut path = [0u8; 128];
        unsafe {
            eclair_mcos_path_result(path.as_mut_ptr(), opt.os_id);
            opt.mcos_fd = open(path.as_ptr(), O_RDONLY);
            if opt.mcos_fd < 0 {
                let errno_value = *__errno_location();
                let mut line = [0u8; 256];
                if eclair_open_mcos_error_result(
                    line.as_mut_ptr(),
                    line.len(),
                    b"eclair.c\0".as_ptr(),
                    ECLAIR_OPTIONS_OPEN_LINE,
                    opt.os_id,
                    errno_value,
                ) >= 0
                {
                    fprintf(stderr, b"%s\n\0".as_ptr(), line.as_ptr());
                } else {
                    fprintf(
                        stderr,
                        b"%s:%d error: opening /dev/mcos%d, errno: %d\n\0".as_ptr(),
                        b"eclair.c\0".as_ptr(),
                        ECLAIR_OPTIONS_OPEN_LINE,
                        opt.os_id,
                        errno_value,
                    );
                }
                exit(1);
            }
        }
    }
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
    remote_running_state: i32,
) -> *const u8 {
    if interactive != 0 && remote_running_state != 0 {
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
    remote_running_state: i32,
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
                if interactive != 0 && remote_running_state != 0 {
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

#[no_mangle]
pub unsafe extern "C" fn eclair_thread_lookup_result(
    head: *mut EclairThreadInfo,
    tid: i32,
) -> *mut EclairThreadInfo {
    let mut current = head;
    while !current.is_null() {
        if unsafe { (*current).tid } == tid {
            return current;
        }
        current = unsafe { (*current).next };
    }
    core::ptr::null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn eclair_thread_list_result(
    buf: *mut u8,
    buf_size: usize,
    head: *mut EclairThreadInfo,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    let mut first = true;
    let mut current = head;
    while !current.is_null() {
        let tid = unsafe { (*current).tid as u32 as usize };
        let ok = unsafe {
            write_byte_checked(buf, &mut pos, buf_size, if first { b'm' } else { b',' })
                && write_hex_usize_checked(buf, &mut pos, buf_size, tid)
        };
        if !ok {
            unsafe {
                finish_cstr(buf, pos, buf_size);
            }
            return -1;
        }
        first = false;
        current = unsafe { (*current).next };
    }

    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    pos as isize
}

#[no_mangle]
pub unsafe extern "C" fn eclair_thread_extra_info_hex_result(
    buf: *mut u8,
    buf_size: usize,
    head: *mut EclairThreadInfo,
    tid: i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let thread = unsafe { eclair_thread_lookup_result(head, tid) };
    if thread.is_null() {
        unsafe {
            finish_cstr(buf, 0, buf_size);
        }
        return -2;
    }

    let thread_ref = unsafe { &*thread };
    let mut info = [0u8; 64];
    if unsafe {
        eclair_thread_extra_info_result(
            info.as_mut_ptr(),
            info.len(),
            thread_ref.pid,
            thread_ref.status,
            thread_ref.idle,
            thread_ref.lcpu,
            thread_ref.cpu,
        )
    } < 0
    {
        unsafe {
            finish_cstr(buf, 0, buf_size);
        }
        return -1;
    }

    let mut pos = 0usize;
    let mut idx = 0usize;
    while idx < info.len() {
        let byte = unsafe { *info.as_ptr().add(idx) };
        if byte == 0 {
            break;
        }
        if !unsafe { write_hex_byte_checked(buf, &mut pos, buf_size, byte) } {
            unsafe {
                finish_cstr(buf, pos, buf_size);
            }
            return -1;
        }
        idx += 1;
    }

    unsafe {
        finish_cstr(buf, pos, buf_size);
    }
    pos as isize
}

#[no_mangle]
pub unsafe extern "C" fn eclair_pure_command_response_result(
    cmd: *const u8,
    cmd_kind: i32,
    buf: *mut u8,
    buf_size: usize,
    head: *mut EclairThreadInfo,
    current_thread_slot: *mut *mut EclairThreadInfo,
    interactive: i32,
    remote_running_state: i32,
    map_kernel_start: usize,
    arch: *const u8,
    error_tid: *mut i32,
    error_kind: *mut i32,
) -> isize {
    if buf.is_null() || buf_size == 0 {
        return ECLAIR_PURE_COMMAND_BUFFER_ERROR;
    }
    if !error_tid.is_null() {
        unsafe {
            *error_tid = 0;
        }
    }
    if !error_kind.is_null() {
        unsafe {
            *error_kind = cmd_kind;
        }
    }

    match cmd_kind {
        ECLAIR_CMD_QSUPPORTED
        | ECLAIR_CMD_HC
        | ECLAIR_CMD_VCONT_QUERY
        | ECLAIR_CMD_STOP_QUERY
        | ECLAIR_CMD_QATTACHED
        | ECLAIR_CMD_TARGET_XML
        | ECLAIR_CMD_QTSTATUS
        | ECLAIR_CMD_MEMORY_MAP
        | ECLAIR_CMD_QSTHREADINFO => {}
        ECLAIR_CMD_QC => {
            if current_thread_slot.is_null() || unsafe { (*current_thread_slot).is_null() } {
                return ECLAIR_PURE_COMMAND_NOT_HANDLED;
            }
        }
        ECLAIR_CMD_QFTHREADINFO => {
            if interactive != 0 {
                return ECLAIR_PURE_COMMAND_NOT_HANDLED;
            }
        }
        ECLAIR_CMD_HG | ECLAIR_CMD_THREAD_ALIVE | ECLAIR_CMD_QTHREAD_EXTRA_INFO => {}
        _ => return ECLAIR_PURE_COMMAND_NOT_HANDLED,
    }

    if cmd_kind == ECLAIR_CMD_HG {
        if current_thread_slot.is_null() {
            return ECLAIR_PURE_COMMAND_NOT_HANDLED;
        }
        let Some(bytes) = (unsafe { cstr_bytes(cmd) }) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let Some((tid, _end)) = parse_hex_usize_prefix(subslice(bytes, 2, bytes.len())) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let tid = tid as i32;
        if tid != 0 {
            let thread = unsafe { eclair_thread_lookup_result(head, tid) };
            if thread.is_null() {
                if !error_tid.is_null() {
                    unsafe {
                        *error_tid = tid;
                    }
                }
                return ECLAIR_PURE_COMMAND_INVALID_TID;
            }
            unsafe {
                *current_thread_slot = thread;
            }
        }
        let n = unsafe {
            eclair_simple_response_result(
                buf,
                buf_size,
                ECLAIR_CMD_HG,
                interactive,
                remote_running_state,
            )
        };
        return if n < 0 {
            ECLAIR_PURE_COMMAND_BUFFER_ERROR
        } else {
            n
        };
    }

    if cmd_kind == ECLAIR_CMD_THREAD_ALIVE {
        let Some(bytes) = (unsafe { cstr_bytes(cmd) }) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let Some((tid, _end)) = parse_hex_usize_prefix(subslice(bytes, 1, bytes.len())) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let tid = tid as i32;
        if unsafe { eclair_thread_lookup_result(head, tid) }.is_null() {
            if !error_tid.is_null() {
                unsafe {
                    *error_tid = tid;
                }
            }
            return ECLAIR_PURE_COMMAND_INVALID_TID;
        }
        let n = unsafe {
            eclair_simple_response_result(
                buf,
                buf_size,
                ECLAIR_CMD_THREAD_ALIVE,
                interactive,
                remote_running_state,
            )
        };
        return if n < 0 {
            ECLAIR_PURE_COMMAND_BUFFER_ERROR
        } else {
            n
        };
    }

    if cmd_kind == ECLAIR_CMD_QTHREAD_EXTRA_INFO {
        let Some(bytes) = (unsafe { cstr_bytes(cmd) }) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let Some((tid, _end)) = parse_hex_usize_prefix(subslice(bytes, 17, bytes.len())) else {
            return ECLAIR_PURE_COMMAND_PARSE_ERROR;
        };
        let tid = tid as i32;
        let n = unsafe { eclair_thread_extra_info_hex_result(buf, buf_size, head, tid) };
        if n == -2 {
            if !error_tid.is_null() {
                unsafe {
                    *error_tid = tid;
                }
            }
            return ECLAIR_PURE_COMMAND_INVALID_TID;
        }
        return if n < 0 {
            ECLAIR_PURE_COMMAND_BUFFER_ERROR
        } else {
            n
        };
    }

    if cmd_kind == ECLAIR_CMD_QFTHREADINFO {
        let n = unsafe { eclair_thread_list_result(buf, buf_size, head) };
        return if n < 0 {
            ECLAIR_PURE_COMMAND_BUFFER_ERROR
        } else {
            n
        };
    }

    match cmd_kind {
        ECLAIR_CMD_HC | ECLAIR_CMD_VCONT_QUERY | ECLAIR_CMD_STOP_QUERY => {
            let n = unsafe {
                eclair_simple_response_result(
                    buf,
                    buf_size,
                    cmd_kind,
                    interactive,
                    remote_running_state,
                )
            };
            if n < 0 {
                ECLAIR_PURE_COMMAND_BUFFER_ERROR
            } else {
                n
            }
        }
        ECLAIR_CMD_QSUPPORTED
        | ECLAIR_CMD_QC
        | ECLAIR_CMD_QATTACHED
        | ECLAIR_CMD_TARGET_XML
        | ECLAIR_CMD_QTSTATUS
        | ECLAIR_CMD_MEMORY_MAP
        | ECLAIR_CMD_QSTHREADINFO => {
            let current_tid =
                if current_thread_slot.is_null() || unsafe { (*current_thread_slot).is_null() } {
                    0
                } else {
                    unsafe { (**current_thread_slot).tid }
                };
            let n = unsafe {
                eclair_static_response_result(
                    buf,
                    buf_size,
                    cmd_kind,
                    current_tid,
                    map_kernel_start,
                    arch,
                )
            };
            if n < 0 {
                ECLAIR_PURE_COMMAND_BUFFER_ERROR
            } else {
                n
            }
        }
        _ => ECLAIR_PURE_COMMAND_NOT_HANDLED,
    }
}

#[cfg(eclair_full_body)]
#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut u8) -> c_int {
    let mut lbuf = [0u8; 1024];
    let mut rbuf = [0u8; 8192];
    let mut cbuf = [0u8; 3];
    let mut framebuf = [0u8; 9000];

    unsafe {
        options(argc, argv);
        if eclair_banner_result(
            framebuf.as_mut_ptr(),
            framebuf.len(),
            opt.interactive,
            opt.dump_path,
        ) >= 0
        {
            printf(b"%s\n\0".as_ptr(), framebuf.as_ptr());
        } else {
            printf(
                b"eclair 0.20160314 %s%s\n\0".as_ptr(),
                if opt.interactive != 0 {
                    b"live debug mode\0".as_ptr()
                } else {
                    b"using dump file: \0".as_ptr()
                },
                if opt.interactive != 0 {
                    b"\0".as_ptr() as *mut u8
                } else {
                    opt.dump_path
                },
            );
        }

        if opt.help != 0 {
            print_usage();
            return 2;
        }

        if setup_symbols(opt.kernel_path) != 0 {
            perror(b"setup_symbols\0".as_ptr());
            print_usage();
            return 1;
        }

        let setup_dump_error = if opt.interactive != 0 {
            setup_dump_interactive()
        } else {
            setup_dump(opt.dump_path)
        };
        if setup_dump_error != 0 {
            perror(b"setup_dump\0".as_ptr());
            print_usage();
            return 1;
        }

        if setup_constants() != 0 {
            perror(b"setup_constants\0".as_ptr());
            return 1;
        }

        if setup_threads() != 0 {
            perror(b"setup_threads\0".as_ptr());
            return 1;
        }

        if start_gdb() != 0 {
            perror(b"start_gdb\0".as_ptr());
            return 1;
        }
    }

    let mut mode = 0i32;
    let mut sum = 0u8;
    let mut check = 0u8;
    let mut lpos = 0usize;

    while unsafe { F_DONE } == 0 {
        let c = unsafe { fgetc(IFP) };
        if c < 0 {
            break;
        }

        match unsafe {
            eclair_packet_step_result(
                c,
                opt.interactive,
                &mut mode,
                &mut sum,
                &mut check,
                lbuf.as_mut_ptr(),
                lbuf.len(),
                &mut lpos,
                cbuf.as_mut_ptr(),
                cbuf.len(),
            )
        } {
            ECLAIR_PACKET_STEP_INTERRUPT | ECLAIR_PACKET_STEP_READY => unsafe {
                fputc(b'+' as c_int, OFP);
                command(lbuf.as_ptr(), rbuf.as_mut_ptr(), rbuf.len());
                sum = eclair_response_checksum_result(rbuf.as_ptr());
                if eclair_packet_frame_result(framebuf.as_mut_ptr(), framebuf.len(), rbuf.as_ptr())
                    < 0
                {
                    break;
                }
                fprintf(OFP, b"%s\0".as_ptr(), framebuf.as_ptr());
                fflush(OFP);
            },
            ECLAIR_PACKET_STEP_BAD => unsafe {
                fputc(b'-' as c_int, OFP);
            },
            ECLAIR_PACKET_STEP_ERROR => break,
            _ => {}
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
