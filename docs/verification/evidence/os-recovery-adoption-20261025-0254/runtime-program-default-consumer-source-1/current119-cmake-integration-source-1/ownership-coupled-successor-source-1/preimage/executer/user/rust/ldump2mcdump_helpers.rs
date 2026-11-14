#![no_std]

use core::panic::PanicInfo;

#[cfg(ldump2_full_body)]
use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong, c_ulonglong, c_void};
#[cfg(ldump2_full_body)]
use core::mem::{size_of, MaybeUninit};
#[cfg(ldump2_full_body)]
use core::ptr::{addr_of, addr_of_mut, null, null_mut};

const BITS_PER_LONG: usize = core::mem::size_of::<usize>() * 8;
#[cfg(ldump2_full_body)]
const PATH_MAX: usize = 4096;
#[cfg(ldump2_full_body)]
const HOST_NAME_MAX: usize = 64;
#[cfg(ldump2_full_body)]
const PHYSMEM_NAME_SIZE: usize = 32;
#[cfg(ldump2_full_body)]
const MAXARGS: usize = 100;
#[cfg(ldump2_full_body)]
const TRUE: c_int = 1;
#[cfg(ldump2_full_body)]
const KVADDR: c_int = 0x1;
#[cfg(ldump2_full_body)]
const FAULT_ON_ERROR: c_ulong = 0x1;
#[cfg(ldump2_full_body)]
const RETURN_ON_ERROR: c_ulong = 0x2;
#[cfg(ldump2_full_body)]
const BFD_OBJECT: c_int = 1;
#[cfg(ldump2_full_body)]
const SEC_ALLOC: c_uint = 0x1;
#[cfg(ldump2_full_body)]
const SEC_HAS_CONTENTS: c_uint = 0x100;
#[cfg(ldump2_full_body)]
const PAGE_SHIFT: c_int = 12;
#[cfg(ldump2_full_body)]
const LARGE_PAGE_SHIFT: c_ulong = 21;
#[cfg(ldump2_full_body)]
const LARGE_PAGE_SIZE: c_ulong = 1 << LARGE_PAGE_SHIFT;
#[cfg(ldump2_full_body)]
const LARGE_PAGE_MASK: c_ulong = !(LARGE_PAGE_SIZE - 1);
#[cfg(ldump2_full_body)]
const MCDUMP_DEFAULT_FILENAME: &[u8] = b"mcdump\0";
#[cfg(ldump2_full_body)]
const DUMP_MEM_SYMBOL: &[u8] = b"dump_page_set_addr\0";
#[cfg(ldump2_full_body)]
const BOOTSTRAP_MEM_SYMBOL: &[u8] = b"dump_bootstrap_mem_start\0";
#[cfg(ldump2_full_body)]
const EMPTY: &[u8] = b"\0";
#[cfg(ldump2_full_body)]
const OPTION_SPEC: &[u8] = b"o:\0";
#[cfg(ldump2_full_body)]
const USAGE_BAD_ARGS: &[u8] = b"argument error\0";
#[cfg(ldump2_full_body)]
const USAGE_LINE: &[u8] = b"ldump2mcdump os_index [-o file_name]\n\0";
#[cfg(ldump2_full_body)]
const COUNT_CHUNKS_FAILED: &[u8] = b"counting dump memory chunks failed\n\0";
#[cfg(ldump2_full_body)]
const BUILD_CHUNKS_FAILED: &[u8] = b"building dump memory chunks failed\n\0";
#[cfg(ldump2_full_body)]
const ALLOC_MEM_BUFFER: &[u8] = b"allocating mem buffer: \0";
#[cfg(ldump2_full_body)]
const ALLOC_MALLOC: &[u8] = b"malloc\0";
#[cfg(ldump2_full_body)]
const INVALID_PHYSMEM: &[u8] = b"invalid physmem section name\n\0";
#[cfg(ldump2_full_body)]
const READMEM_ERROR: &[u8] = b"readmem error(%d)\n\0";
#[cfg(ldump2_full_body)]
const BFD_FOPEN: &[u8] = b"bfd_fopen\0";
#[cfg(ldump2_full_body)]
const BFD_SET_FORMAT: &[u8] = b"bfd_set_format\0";
#[cfg(ldump2_full_body)]
const TIME_NAME: &[u8] = b"time\0";
#[cfg(ldump2_full_body)]
const LOCALTIME_NAME: &[u8] = b"localtime\0";
#[cfg(ldump2_full_body)]
const BFD_MAKE_DATE: &[u8] = b"bfd_make_section_anyway(date)\0";
#[cfg(ldump2_full_body)]
const BFD_MAKE_HOSTNAME: &[u8] = b"bfd_make_section_anyway(hostname)\0";
#[cfg(ldump2_full_body)]
const BFD_MAKE_USER: &[u8] = b"bfd_make_section_anyway(user)\0";
#[cfg(ldump2_full_body)]
const BFD_MAKE_PHYSCHUNKS: &[u8] = b"bfd_make_section_anyway(physchunks)\0";
#[cfg(ldump2_full_body)]
const BFD_MAKE_PHYSMEM: &[u8] = b"bfd_make_section_anyway(physmem)\0";
#[cfg(ldump2_full_body)]
const BFD_SET_SECTION_SIZE: &[u8] = b"bfd_set_section_size\0";
#[cfg(ldump2_full_body)]
const BFD_SET_SECTION_FLAGS: &[u8] = b"bfd_set_setction_flags\0";
#[cfg(ldump2_full_body)]
const BFD_SET_CONTENTS_DATE: &[u8] = b"bfd_set_section_contents(date)\0";
#[cfg(ldump2_full_body)]
const BFD_SET_CONTENTS_HOSTNAME: &[u8] = b"bfd_set_section_contents(hostname)\0";
#[cfg(ldump2_full_body)]
const BFD_SET_CONTENTS_USER: &[u8] = b"bfd_set_section_contents(user)\0";
#[cfg(ldump2_full_body)]
const BFD_SET_CONTENTS_PHYSCHUNKS: &[u8] = b"bfd_set_section_contents(physchunks)\0";
#[cfg(ldump2_full_body)]
const BFD_GET_PHYSMEM: &[u8] = b"err bfd_get_section_by_name(physmem_name)\0";
#[cfg(ldump2_full_body)]
const BFD_SET_CONTENTS_PHYSMEM: &[u8] = b"bfd_set_section_contents(physmem)\0";
#[cfg(ldump2_full_body)]
const BFD_CLOSE: &[u8] = b"bfd_close\0";
#[cfg(ldump2_full_body)]
const SECTION_DATE: &[u8] = b"date\0";
#[cfg(ldump2_full_body)]
const SECTION_HOSTNAME: &[u8] = b"hostname\0";
#[cfg(ldump2_full_body)]
const SECTION_USER: &[u8] = b"user\0";
#[cfg(ldump2_full_body)]
const SECTION_PHYSCHUNKS: &[u8] = b"physchunks\0";
#[cfg(ldump2_full_body)]
const CMD_NAME: &[u8] = b"ldump2mcdump\0";
#[cfg(ldump2_full_body)]
const HELP_SHORT: &[u8] = b"dump format conversion\0";
#[cfg(ldump2_full_body)]
const HELP_ARGS: &[u8] = b"<os_index> [-o <file_name>]\0";
#[cfg(ldump2_full_body)]
const HELP_TEXT: &[u8] = b"  This command converts the McKernel dump file format.\0";
#[cfg(ldump2_full_body)]
const HELP_EXAMPLE: &[u8] = b"\nEXAMPLE\0";
#[cfg(ldump2_full_body)]
const HELP_ALL: &[u8] = b" ldump2mcdump all command arguments:\n\0";
#[cfg(ldump2_full_body)]
const HELP_COMMAND: &[u8] = b"    crash>ldump2mcdump 0 -o /tmp/mcdump\0";

#[repr(C)]
#[cfg(ldump2_full_body)]
struct CommandTableEntry {
    name: *mut c_char,
    func: Option<unsafe extern "C" fn()>,
    help_data: *mut *mut c_char,
    flags: c_ulong,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct IhkDumpPage {
    start: c_ulong,
    map_count: c_ulong,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct IhkDumpPageSet {
    completion_flag: c_uint,
    count: c_uint,
    page_size: c_ulong,
    phy_page: c_ulong,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct DumpMemChunks {
    nr_chunks: c_int,
    kernel_base: c_ulong,
    phys_start: c_ulong,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct Bfd {
    _private: [u8; 0],
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct ASection {
    name: *const c_char,
    id: c_uint,
    index: c_uint,
    next: *mut ASection,
    prev: *mut ASection,
    flags: c_uint,
    bitfields: c_uint,
    vma: c_ulong,
    lma: c_ulong,
    size: c_ulong,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct File {
    _private: [u8; 0],
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct Tm {
    _private: [u8; 0],
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct Passwd {
    pw_name: *mut c_char,
}

#[repr(C)]
#[cfg(ldump2_full_body)]
struct MachdepTable {
    flags: c_ulong,
    kvbase: c_ulong,
}

#[cfg(ldump2_full_body)]
unsafe extern "C" {
    static mut argcnt: c_int;
    static mut args: [*mut c_char; MAXARGS];
    static mut optarg: *mut c_char;
    static mut fp: *mut File;
    static mut stderr: *mut File;
    static mut machdep: *mut MachdepTable;

    fn register_extension(table: *mut CommandTableEntry);
    fn symbol_value(name: *mut c_char) -> c_ulong;
    fn readmem(
        addr: c_ulonglong,
        type_: c_int,
        buf: *mut c_void,
        size: c_long,
        msg: *mut c_char,
        flags: c_ulong,
    ) -> c_int;
    fn getopt(argc: c_int, argv: *mut *mut c_char, optstring: *const c_char) -> c_int;
    fn strcpy(dst: *mut c_char, src: *const c_char) -> *mut c_char;
    fn strlen(s: *const c_char) -> usize;
    fn memset(s: *mut c_void, c: c_int, n: usize) -> *mut c_void;
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn perror(s: *const c_char);
    fn fprintf(stream: *mut File, format: *const c_char, ...) -> c_int;
    fn gethostname(name: *mut c_char, len: usize) -> c_int;
    fn getuid() -> c_uint;
    fn getpwuid(uid: c_uint) -> *mut Passwd;
    fn time(tloc: *mut c_long) -> c_long;
    fn localtime(timep: *const c_long) -> *mut Tm;
    fn asctime(tm: *const Tm) -> *mut c_char;

    fn bfd_init();
    fn bfd_fopen(
        filename: *const c_char,
        target: *const c_char,
        mode: *const c_char,
        fd: c_int,
    ) -> *mut Bfd;
    fn bfd_perror(message: *const c_char);
    fn bfd_set_format(abfd: *mut Bfd, format: c_int) -> c_int;
    fn bfd_make_section_anyway(abfd: *mut Bfd, name: *const c_char) -> *mut ASection;
    fn bfd_set_section_size(abfd: *mut Bfd, section: *mut ASection, size: c_ulong) -> c_int;
    fn bfd_set_section_flags(abfd: *mut Bfd, section: *mut ASection, flags: c_uint) -> c_int;
    fn bfd_get_section_by_name(abfd: *mut Bfd, name: *const c_char) -> *mut ASection;
    fn bfd_set_section_contents(
        abfd: *mut Bfd,
        section: *mut ASection,
        data: *const c_void,
        offset: c_long,
        count: c_ulong,
    ) -> c_int;
    fn bfd_close(abfd: *mut Bfd) -> c_int;
}

#[no_mangle]
#[cfg(ldump2_full_body)]
pub static mut help_ldump2mcdump: [*mut c_char; 8] = [0 as *mut c_char; 8];

#[cfg(ldump2_full_body)]
static mut COMMAND_TABLE: [CommandTableEntry; 2] = [
    CommandTableEntry {
        name: 0 as *mut c_char,
        func: None,
        help_data: 0 as *mut *mut c_char,
        flags: 0,
    },
    CommandTableEntry {
        name: 0 as *mut c_char,
        func: None,
        help_data: 0 as *mut *mut c_char,
        flags: 0,
    },
];

#[used]
#[cfg(ldump2_full_body)]
#[link_section = ".init_array"]
static LDUMP2MCDUMP_INIT_ARRAY: unsafe extern "C" fn() = ldump2mcdump_init;

#[used]
#[cfg(ldump2_full_body)]
#[link_section = ".fini_array"]
static LDUMP2MCDUMP_FINI_ARRAY: unsafe extern "C" fn() = ldump2mcdump_fini;

#[repr(C)]
pub struct DumpMemChunk {
    addr: usize,
    size: usize,
}

#[inline(always)]
#[cfg(ldump2_full_body)]
fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr().cast()
}

#[inline(always)]
#[cfg(ldump2_full_body)]
fn cstr_mut(bytes: &'static [u8]) -> *mut c_char {
    bytes.as_ptr() as *mut c_char
}

#[inline(always)]
#[cfg(ldump2_full_body)]
unsafe fn ptov(addr: c_ulong) -> c_ulong {
    if machdep.is_null() {
        addr
    } else {
        addr.wrapping_add((*machdep).kvbase)
    }
}

#[inline(always)]
#[cfg(ldump2_full_body)]
unsafe fn dump_chunks_ptr(mem_chunks: *mut DumpMemChunks) -> *mut DumpMemChunk {
    mem_chunks
        .cast::<u8>()
        .add(size_of::<DumpMemChunks>())
        .cast::<DumpMemChunk>()
}

#[inline(always)]
#[cfg(ldump2_full_body)]
unsafe fn dump_chunk(mem_chunks: *mut DumpMemChunks, index: usize) -> *mut DumpMemChunk {
    dump_chunks_ptr(mem_chunks).add(index)
}

#[inline(always)]
#[cfg(ldump2_full_body)]
unsafe fn set_section_vma(section: *mut ASection, vma: c_ulong) {
    if !section.is_null() {
        (*section).vma = vma;
        (*section).lma = vma;
        (*section).bitfields |= 1;
    }
}

#[cfg(ldump2_full_body)]
unsafe fn make_section(
    abfd: *mut Bfd,
    name: *const c_char,
    size: c_ulong,
    flags: c_uint,
    make_err: &'static [u8],
) -> *mut ASection {
    let scn = bfd_make_section_anyway(abfd, name);
    if scn.is_null() {
        bfd_perror(cstr(make_err));
        return null_mut();
    }
    if bfd_set_section_size(abfd, scn, size) == 0 {
        bfd_perror(cstr(BFD_SET_SECTION_SIZE));
        return null_mut();
    }
    if bfd_set_section_flags(abfd, scn, flags) == 0 {
        bfd_perror(cstr(BFD_SET_SECTION_FLAGS));
        return null_mut();
    }
    scn
}

fn bit_is_set(map: &[usize], bit: usize) -> bool {
    let word = bit / BITS_PER_LONG;
    let shift = bit % BITS_PER_LONG;

    unsafe { *map.as_ptr().add(word) & (1usize << shift) != 0 }
}

unsafe fn map_slice<'a>(map: *const usize, map_count: usize) -> Option<&'a [usize]> {
    if map.is_null() {
        if map_count == 0 {
            Some(&[])
        } else {
            None
        }
    } else {
        Some(unsafe { core::slice::from_raw_parts(map, map_count) })
    }
}

#[no_mangle]
pub unsafe extern "C" fn ldump2_count_chunks_result(map: *const usize, map_count: usize) -> i32 {
    let Some(map) = (unsafe { map_slice(map, map_count) }) else {
        return -1;
    };
    let total_bits = map_count.saturating_mul(BITS_PER_LONG);
    let mut bit = 0usize;
    let mut chunks = 0usize;
    let mut in_chunk = false;

    while bit < total_bits {
        if bit_is_set(map, bit) {
            if !in_chunk {
                chunks = chunks.saturating_add(1);
                if chunks > i32::MAX as usize {
                    return -1;
                }
                in_chunk = true;
            }
        } else {
            in_chunk = false;
        }
        bit += 1;
    }

    chunks as i32
}

#[no_mangle]
pub unsafe extern "C" fn ldump2_fill_chunks_result(
    chunks: *mut DumpMemChunk,
    max_chunks: usize,
    start: usize,
    map: *const usize,
    map_count: usize,
    page_shift: i32,
) -> i32 {
    if chunks.is_null() && max_chunks != 0 {
        return -1;
    }
    if page_shift < 0 || page_shift as u32 >= usize::BITS {
        return -1;
    }

    let Some(map) = (unsafe { map_slice(map, map_count) }) else {
        return -1;
    };
    let total_bits = map_count.saturating_mul(BITS_PER_LONG);
    let shift = page_shift as u32;
    let mut bit = 0usize;
    let mut chunk_count = 0usize;
    let mut run_start = 0usize;
    let mut run_len = 0usize;

    while bit < total_bits {
        if bit_is_set(map, bit) {
            if run_len == 0 {
                run_start = bit;
            }
            run_len = run_len.wrapping_add(1);
        } else if run_len != 0 {
            if chunk_count >= max_chunks {
                return -1;
            }
            unsafe {
                *chunks.add(chunk_count) = DumpMemChunk {
                    addr: start.wrapping_add(run_start.wrapping_shl(shift)),
                    size: run_len.wrapping_shl(shift),
                };
            }
            chunk_count += 1;
            run_len = 0;
        }
        bit += 1;
    }

    if run_len != 0 {
        if chunk_count >= max_chunks {
            return -1;
        }
        unsafe {
            *chunks.add(chunk_count) = DumpMemChunk {
                addr: start.wrapping_add(run_start.wrapping_shl(shift)),
                size: run_len.wrapping_shl(shift),
            };
        }
        chunk_count += 1;
    }

    if chunk_count > i32::MAX as usize {
        -1
    } else {
        chunk_count as i32
    }
}

fn write_byte(buf: *mut u8, pos: &mut usize, size: usize, byte: u8) -> bool {
    if *pos + 1 >= size {
        return false;
    }

    unsafe {
        *buf.add(*pos) = byte;
    }
    *pos += 1;
    true
}

fn write_decimal(buf: *mut u8, pos: &mut usize, size: usize, value: i32) -> bool {
    let mut v = if value < 0 {
        if !write_byte(buf, pos, size, b'-') {
            return false;
        }
        value.wrapping_neg() as u32
    } else {
        value as u32
    };

    if v == 0 {
        return write_byte(buf, pos, size, b'0');
    }

    let divisors = [
        1_000_000_000u32,
        100_000_000u32,
        10_000_000u32,
        1_000_000u32,
        100_000u32,
        10_000u32,
        1_000u32,
        100u32,
        10u32,
        1u32,
    ];
    let mut started = false;
    let mut idx = 0usize;

    while idx < divisors.len() {
        let divisor = unsafe { *divisors.as_ptr().add(idx) };
        let mut digit = 0u8;
        while v >= divisor {
            v -= divisor;
            digit += 1;
        }
        if digit != 0 || started {
            if !write_byte(buf, pos, size, b'0' + digit) {
                return false;
            }
            started = true;
        }
        idx += 1;
    }

    true
}

#[no_mangle]
pub unsafe extern "C" fn ldump2_physmem_name_result(
    buf: *mut u8,
    buf_size: usize,
    index: i32,
) -> i32 {
    if buf.is_null() || buf_size == 0 {
        return -1;
    }

    let mut pos = 0usize;
    for byte in b"physmem" {
        if !write_byte(buf, &mut pos, buf_size, *byte) {
            return -1;
        }
    }
    if !write_decimal(buf, &mut pos, buf_size, index) {
        return -1;
    }

    unsafe {
        *buf.add(pos) = 0;
    }
    pos as i32
}

#[no_mangle]
#[cfg(ldump2_full_body)]
pub unsafe extern "C" fn ldump2mcdump_init() {
    let help = addr_of_mut!(help_ldump2mcdump).cast::<*mut c_char>();
    *help.add(0) = cstr_mut(CMD_NAME);
    *help.add(1) = cstr_mut(HELP_SHORT);
    *help.add(2) = cstr_mut(HELP_ARGS);
    *help.add(3) = cstr_mut(HELP_TEXT);
    *help.add(4) = cstr_mut(HELP_EXAMPLE);
    *help.add(5) = cstr_mut(HELP_ALL);
    *help.add(6) = cstr_mut(HELP_COMMAND);
    *help.add(7) = null_mut();

    let table = addr_of_mut!(COMMAND_TABLE).cast::<CommandTableEntry>();
    (*table.add(0)).name = cstr_mut(CMD_NAME);
    (*table.add(0)).func = Some(cmd_ldump2mcdump);
    (*table.add(0)).help_data = help;
    (*table.add(0)).flags = 0;
    (*table.add(1)).name = null_mut();
    (*table.add(1)).func = None;
    (*table.add(1)).help_data = null_mut();
    (*table.add(1)).flags = 0;

    register_extension(table);
}

#[no_mangle]
#[cfg(ldump2_full_body)]
pub unsafe extern "C" fn ldump2mcdump_fini() {}

#[cfg(ldump2_full_body)]
unsafe fn read_or_return(addr: c_ulong, buf: *mut c_void, size: usize, flags: c_ulong) -> c_int {
    readmem(
        addr as c_ulonglong,
        KVADDR,
        buf,
        size as c_long,
        cstr_mut(EMPTY),
        flags,
    )
}

#[cfg(ldump2_full_body)]
unsafe fn read_dump_pages(
    dump_page_set: *const IhkDumpPageSet,
    mem_chunks: *mut DumpMemChunks,
    count_only: bool,
    mem_num: *mut c_int,
) -> c_int {
    let mut ihk_dump_page_addr = ptov((*dump_page_set).phy_page);
    let mut i = 0u32;
    let mut index: c_int = 0;
    let mut total: c_int = 0;

    while i < (*dump_page_set).count {
        let mut ihk_dump_page = MaybeUninit::<IhkDumpPage>::uninit();
        read_or_return(
            ihk_dump_page_addr,
            ihk_dump_page.as_mut_ptr().cast::<c_void>(),
            size_of::<IhkDumpPage>(),
            FAULT_ON_ERROR,
        );
        let ihk_dump_page = ihk_dump_page.assume_init();
        let map_size = size_of::<c_ulong>().wrapping_mul(ihk_dump_page.map_count as usize);
        let map_buf = malloc(map_size).cast::<c_ulong>();
        if map_buf.is_null() {
            perror(cstr(ALLOC_MEM_BUFFER));
            return -1;
        }

        memset(map_buf.cast::<c_void>(), 0, map_size);
        read_or_return(
            ihk_dump_page_addr.wrapping_add(size_of::<IhkDumpPage>() as c_ulong),
            map_buf.cast::<c_void>(),
            map_size,
            FAULT_ON_ERROR,
        );

        let chunk_count = if count_only {
            ldump2_count_chunks_result(map_buf.cast::<usize>(), ihk_dump_page.map_count as usize)
        } else {
            ldump2_fill_chunks_result(
                dump_chunk(mem_chunks, index as usize),
                (*mem_num - index) as usize,
                ihk_dump_page.start as usize,
                map_buf.cast::<usize>(),
                ihk_dump_page.map_count as usize,
                PAGE_SHIFT,
            )
        };

        free(map_buf.cast::<c_void>());

        if count_only {
            if chunk_count < 0 || chunk_count > c_int::MAX - total {
                fprintf(stderr, cstr(COUNT_CHUNKS_FAILED));
                return -1;
            }
            total += chunk_count;
        } else {
            if chunk_count < 0 || chunk_count > *mem_num - index {
                fprintf(stderr, cstr(BUILD_CHUNKS_FAILED));
                return -1;
            }
            index += chunk_count;
        }

        ihk_dump_page_addr = ihk_dump_page_addr
            .wrapping_add(size_of::<IhkDumpPage>() as c_ulong)
            .wrapping_add(map_size as c_ulong);
        i += 1;
    }

    if count_only {
        *mem_num = total;
    } else {
        (*mem_chunks).nr_chunks = index;
    }

    0
}

#[no_mangle]
#[cfg(ldump2_full_body)]
pub unsafe extern "C" fn cmd_ldump2mcdump() {
    static mut PATH: [c_char; PATH_MAX] = [0; PATH_MAX];
    static mut HNAME: [c_char; HOST_NAME_MAX + 1] = [0; HOST_NAME_MAX + 1];

    let abfd: *mut Bfd;
    let buf: *mut c_void;
    let mem_chunks: *mut DumpMemChunks;
    let mut opt: c_int;

    if argcnt < 2 {
        perror(cstr(USAGE_BAD_ARGS));
        return;
    }

    strcpy(
        addr_of_mut!(PATH).cast::<c_char>(),
        cstr(MCDUMP_DEFAULT_FILENAME),
    );

    loop {
        opt = getopt(
            argcnt,
            addr_of_mut!(args).cast::<*mut c_char>(),
            cstr(OPTION_SPEC),
        );
        if opt == -1 {
            break;
        }
        match opt as u8 {
            b'o' => {
                strcpy(addr_of_mut!(PATH).cast::<c_char>(), optarg);
            }
            _ => {
                fprintf(stderr, cstr(USAGE_LINE));
                return;
            }
        }
    }

    let symbol_dump_page_set = symbol_value(cstr_mut(DUMP_MEM_SYMBOL));
    let mut dump_page_set_addr: c_ulong = 0;
    read_or_return(
        symbol_dump_page_set,
        addr_of_mut!(dump_page_set_addr).cast::<c_void>(),
        size_of::<c_ulong>(),
        FAULT_ON_ERROR,
    );

    let mut dump_page_set = MaybeUninit::<IhkDumpPageSet>::uninit();
    read_or_return(
        dump_page_set_addr,
        dump_page_set.as_mut_ptr().cast::<c_void>(),
        size_of::<IhkDumpPageSet>(),
        FAULT_ON_ERROR,
    );
    let dump_page_set = dump_page_set.assume_init();

    let mut mem_num: c_int = 0;
    if read_dump_pages(&dump_page_set, null_mut(), true, &raw mut mem_num) != 0 {
        return;
    }

    let mem_size = size_of::<DumpMemChunks>()
        .wrapping_add(size_of::<DumpMemChunk>().wrapping_mul(mem_num as usize));
    mem_chunks = malloc(mem_size).cast::<DumpMemChunks>();
    if mem_chunks.is_null() {
        perror(cstr(ALLOC_MEM_BUFFER));
        return;
    }
    memset(mem_chunks.cast::<c_void>(), 0, mem_size);

    if read_dump_pages(&dump_page_set, mem_chunks, false, &raw mut mem_num) != 0 {
        return;
    }

    let symbol_bootstrap_mem = symbol_value(cstr_mut(BOOTSTRAP_MEM_SYMBOL));
    let mut bootstrap_mem: c_ulong = 0;
    read_or_return(
        symbol_bootstrap_mem,
        addr_of_mut!(bootstrap_mem).cast::<c_void>(),
        size_of::<c_ulong>(),
        FAULT_ON_ERROR,
    );
    (*mem_chunks).kernel_base = bootstrap_mem
        .wrapping_add(LARGE_PAGE_SIZE * 2)
        .wrapping_sub(1)
        & LARGE_PAGE_MASK;

    let mut phys_size: c_ulong = 0;
    let mut i = 0usize;
    while i < (*mem_chunks).nr_chunks as usize {
        phys_size = phys_size.wrapping_add((*dump_chunk(mem_chunks, i)).size as c_ulong);
        i += 1;
    }
    let _ = phys_size;

    let bsize: usize = 0x100000;
    buf = malloc(bsize);
    if buf.is_null() {
        perror(cstr(ALLOC_MALLOC));
        return;
    }

    bfd_init();
    abfd = bfd_fopen(
        addr_of_mut!(PATH).cast::<c_char>(),
        null(),
        cstr(b"w\0"),
        -1,
    );
    if abfd.is_null() {
        bfd_perror(cstr(BFD_FOPEN));
        return;
    }
    if bfd_set_format(abfd, BFD_OBJECT) == 0 {
        bfd_perror(cstr(BFD_SET_FORMAT));
        return;
    }

    let t = time(null_mut());
    if t == -1 {
        perror(cstr(TIME_NAME));
        return;
    }
    let tm = localtime(addr_of!(t));
    if tm.is_null() {
        perror(cstr(LOCALTIME_NAME));
        return;
    }
    let date = asctime(tm);
    let mut date_len: c_ulong = 0;
    if !date.is_null() {
        date_len = strlen(date).wrapping_sub(1) as c_ulong;
        if make_section(
            abfd,
            cstr(SECTION_DATE),
            date_len,
            SEC_HAS_CONTENTS,
            BFD_MAKE_DATE,
        )
        .is_null()
        {
            return;
        }
    }

    let mut hostname_len: c_ulong = 0;
    if gethostname(addr_of_mut!(HNAME).cast::<c_char>(), HOST_NAME_MAX + 1) == 0 {
        hostname_len = strlen(addr_of_mut!(HNAME).cast::<c_char>()) as c_ulong;
        if make_section(
            abfd,
            cstr(SECTION_HOSTNAME),
            hostname_len,
            SEC_HAS_CONTENTS,
            BFD_MAKE_HOSTNAME,
        )
        .is_null()
        {
            return;
        }
    }

    let pw = getpwuid(getuid());
    let mut user_len: c_ulong = 0;
    if !pw.is_null() {
        user_len = strlen((*pw).pw_name) as c_ulong;
        if make_section(
            abfd,
            cstr(SECTION_USER),
            user_len,
            SEC_HAS_CONTENTS,
            BFD_MAKE_USER,
        )
        .is_null()
        {
            return;
        }
    }

    if make_section(
        abfd,
        cstr(SECTION_PHYSCHUNKS),
        mem_size as c_ulong,
        SEC_ALLOC | SEC_HAS_CONTENTS,
        BFD_MAKE_PHYSCHUNKS,
    )
    .is_null()
    {
        return;
    }

    i = 0;
    while i < (*mem_chunks).nr_chunks as usize {
        let physmem_name_buf = malloc(PHYSMEM_NAME_SIZE).cast::<c_char>();
        if physmem_name_buf.is_null() {
            perror(cstr(ALLOC_MALLOC));
            return;
        }
        memset(physmem_name_buf.cast::<c_void>(), 0, PHYSMEM_NAME_SIZE);
        if ldump2_physmem_name_result(physmem_name_buf.cast::<u8>(), PHYSMEM_NAME_SIZE, i as i32)
            < 0
        {
            fprintf(stderr, cstr(INVALID_PHYSMEM));
            return;
        }
        let chunk = dump_chunk(mem_chunks, i);
        let scn = make_section(
            abfd,
            physmem_name_buf,
            (*chunk).size as c_ulong,
            SEC_ALLOC | SEC_HAS_CONTENTS,
            BFD_MAKE_PHYSMEM,
        );
        if scn.is_null() {
            return;
        }
        set_section_vma(scn, (*chunk).addr as c_ulong);
        i += 1;
    }

    let mut scn = bfd_get_section_by_name(abfd, cstr(SECTION_DATE));
    if !scn.is_null()
        && bfd_set_section_contents(abfd, scn, date.cast::<c_void>(), 0, date_len) == 0
    {
        bfd_perror(cstr(BFD_SET_CONTENTS_DATE));
        return;
    }

    scn = bfd_get_section_by_name(abfd, cstr(SECTION_HOSTNAME));
    if !scn.is_null()
        && bfd_set_section_contents(
            abfd,
            scn,
            addr_of_mut!(HNAME).cast::<c_void>(),
            0,
            hostname_len,
        ) == 0
    {
        bfd_perror(cstr(BFD_SET_CONTENTS_HOSTNAME));
        return;
    }

    scn = bfd_get_section_by_name(abfd, cstr(SECTION_USER));
    if !scn.is_null()
        && !pw.is_null()
        && bfd_set_section_contents(abfd, scn, (*pw).pw_name.cast::<c_void>(), 0, user_len) == 0
    {
        bfd_perror(cstr(BFD_SET_CONTENTS_USER));
        return;
    }

    scn = bfd_get_section_by_name(abfd, cstr(SECTION_PHYSCHUNKS));
    if !scn.is_null()
        && bfd_set_section_contents(
            abfd,
            scn,
            mem_chunks.cast::<c_void>(),
            0,
            mem_size as c_ulong,
        ) == 0
    {
        bfd_perror(cstr(BFD_SET_CONTENTS_PHYSCHUNKS));
        return;
    }

    let mut physmem_name = [0 as c_char; PHYSMEM_NAME_SIZE];
    i = 0;
    while i < (*mem_chunks).nr_chunks as usize {
        let chunk = dump_chunk(mem_chunks, i);
        let mut phys_offset: c_ulong = 0;
        memset(
            physmem_name.as_mut_ptr().cast::<c_void>(),
            0,
            PHYSMEM_NAME_SIZE,
        );
        if ldump2_physmem_name_result(
            physmem_name.as_mut_ptr().cast::<u8>(),
            PHYSMEM_NAME_SIZE,
            i as i32,
        ) < 0
        {
            fprintf(stderr, cstr(INVALID_PHYSMEM));
            return;
        }
        scn = bfd_get_section_by_name(abfd, physmem_name.as_ptr());
        if scn.is_null() {
            bfd_perror(cstr(BFD_GET_PHYSMEM));
            return;
        }

        let end = ((*chunk).addr as c_ulong).wrapping_add((*chunk).size as c_ulong);
        let mut addr = (*chunk).addr as c_ulong;
        while addr < end {
            let mut cpsize = end.wrapping_sub(addr) as usize;
            if cpsize > bsize {
                cpsize = bsize;
            }
            memset(buf, 0, cpsize);
            let read_mem_ret =
                read_or_return(ptov(addr), buf, cpsize, FAULT_ON_ERROR | RETURN_ON_ERROR);
            if read_mem_ret == TRUE {
                if bfd_set_section_contents(
                    abfd,
                    scn,
                    buf,
                    phys_offset as c_long,
                    cpsize as c_ulong,
                ) == 0
                {
                    bfd_perror(cstr(BFD_SET_CONTENTS_PHYSMEM));
                    return;
                }
                phys_offset = phys_offset.wrapping_add(cpsize as c_ulong);
            } else {
                fprintf(fp, cstr(READMEM_ERROR), read_mem_ret);
            }
            addr = addr.wrapping_add(cpsize as c_ulong);
        }
        i += 1;
    }

    if bfd_close(abfd) == 0 {
        bfd_perror(cstr(BFD_CLOSE));
        return;
    }

    free(buf);
    free(mem_chunks.cast::<c_void>());
}

#[panic_handler]
fn panic(_info: &PanicInfo) -> ! {
    loop {
        core::hint::spin_loop();
    }
}
