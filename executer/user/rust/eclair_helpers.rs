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
struct DumpMemChunksHeader {
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

unsafe extern "C" {
    static mut nsyms: isize;
    static mut symtab: *mut *mut BfdSymbol;
    static mut opt: EclairOptions;
    static mut symbfd: *mut c_void;
    static mut dumpbfd: *mut c_void;
    static mut mem_chunks: *mut DumpMemChunksHeader;
    fn virt_to_phys(va: usize) -> usize;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn perror(s: *const u8);
    fn malloc(size: usize) -> *mut c_void;
    fn bfd_openr(filename: *const u8, target: *const u8) -> *mut c_void;
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
    fn kill(pid: i32, sig: i32) -> i32;
    static mut stderr: *mut c_void;
    static mut gdbpid: i32;
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
const DUMP_NMI_CONT: c_int = 10;
const SIGINT_CONST: i32 = 2;

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

    if neg { value.saturating_neg() } else { value }
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
    if ok { pos as isize } else { -1 }
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
    remote_running: i32,
    action: *mut i32,
    next_remote_running: *mut i32,
    set_done: *mut i32,
) -> i32 {
    if action.is_null() || next_remote_running.is_null() || set_done.is_null() {
        return -1;
    }

    unsafe {
        *action = ECLAIR_REMOTE_ACTION_NONE;
        *next_remote_running = remote_running;
        *set_done = 0;
    }

    match cmd_kind {
        ECLAIR_CMD_VCTRLC | ECLAIR_CMD_CTRLC => {
            if interactive != 0 && remote_running != 0 {
                unsafe {
                    *action = ECLAIR_REMOTE_ACTION_NMI;
                    *next_remote_running = 0;
                }
            }
            0
        }
        ECLAIR_CMD_CONTINUE => {
            if interactive != 0 && remote_running == 0 {
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
            if interactive != 0 && remote_running == 0 {
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    if ok { pos as isize } else { -1 }
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
    remote_running: i32,
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
            eclair_simple_response_result(buf, buf_size, ECLAIR_CMD_HG, interactive, remote_running)
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
                remote_running,
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
                eclair_simple_response_result(buf, buf_size, cmd_kind, interactive, remote_running)
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

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
