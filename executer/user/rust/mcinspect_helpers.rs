#![no_std]

use core::ffi::{c_int, c_ulong, c_void};
use core::panic::PanicInfo;

unsafe extern "C" {
    #[cfg(not(mcinspect_full_body))]
    static mut symbfd: *mut c_void;
    #[cfg(not(mcinspect_full_body))]
    static mut nsyms: isize;
    #[cfg(not(mcinspect_full_body))]
    static mut symtab: *mut *mut BfdSymbol;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "debug"]
    static mut MCINSPECT_DEBUG: c_int;
    #[cfg(not(mcinspect_full_body))]
    static mut mcfd: c_int;
    #[cfg(not(mcinspect_full_body))]
    static mut nr_cpus: c_int;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "help"]
    static mut MCINSPECT_HELP: c_int;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "ps"]
    static mut MCINSPECT_PS: c_int;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "vtop"]
    static mut MCINSPECT_VTOP: c_int;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "pid"]
    static mut MCINSPECT_PID: c_int;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "vtop_addr"]
    static mut MCINSPECT_VTOP_ADDR: usize;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "clv"]
    static mut MCINSPECT_CLV: usize;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "clv_size"]
    static mut MCINSPECT_CLV_SIZE: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut clv_runq_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut clv_idle_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut clv_current_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut thread_tid_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    #[link_name = "thread_sched_list_offset"]
    static mut MCINSPECT_THREAD_SCHED_LIST_OFFSET: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut thread_proc_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut thread_status_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut process_pid_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut process_vm_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut process_saved_cmdline_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut process_saved_cmdline_len_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut vm_address_space_offset: usize;
    #[cfg(not(mcinspect_full_body))]
    static mut address_space_page_table_offset: usize;
    static mut stdout: *mut c_void;
    static mut stderr: *mut c_void;
    fn basename(path: *mut u8) -> *mut u8;
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn memset(ptr: *mut c_void, value: c_int, size: usize) -> *mut c_void;
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
    #[cfg(mcinspect_full_body)]
    #[link_name = "optarg"]
    static mut GETOPT_OPTARG: *mut u8;
    #[cfg(mcinspect_full_body)]
    fn open(path: *const u8, flags: c_int, ...) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn close(fd: c_int) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn getopt_long(
        argc: c_int,
        argv: *mut *mut u8,
        shortopts: *const u8,
        longopts: *const GetoptOption,
        longindex: *mut c_int,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_init(
        fd: c_int,
        access: u64,
        errhand: *mut c_void,
        errarg: *mut c_void,
        dbg: *mut *mut c_void,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_finish(dbg: *mut c_void, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_next_cu_header_c(
        dbg: *mut c_void,
        is_info: c_int,
        cu_length: *mut u64,
        cu_version: *mut u16,
        cu_abbrev_offset: *mut u64,
        cu_pointer_size: *mut u16,
        cu_offset_size: *mut u16,
        cu_extension_size: *mut u16,
        type_signature: *mut DwarfSig8,
        type_offset: *mut u64,
        cu_next_offset: *mut u64,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_siblingof(
        dbg: *mut c_void,
        die: *mut c_void,
        sibling: *mut *mut c_void,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_child(die: *mut c_void, child: *mut *mut c_void, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_tag(die: *mut c_void, tag: *mut u16, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_diename(die: *mut c_void, name: *mut *mut u8, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_get_TAG_name(value: c_int, out: *mut *const u8) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_attr(
        die: *mut c_void,
        attr: u16,
        returned_attr: *mut *mut c_void,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_attrlist(
        die: *mut c_void,
        attrbuf: *mut *mut *mut c_void,
        attrcount: *mut i64,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_whatform(attr: *mut c_void, form: *mut u16, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_whatform_direct(attr: *mut c_void, form: *mut u16, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_whatattr(attr: *mut c_void, attr_num: *mut u16, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_formudata(attr: *mut c_void, value: *mut u64, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_formsdata(attr: *mut c_void, value: *mut i64, error: *mut *mut c_void) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_loclist_n(
        attr: *mut c_void,
        locdescs: *mut *mut *mut DwarfLocdesc,
        len: *mut i64,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_formexprloc(
        attr: *mut c_void,
        exprlen: *mut u64,
        block_ptr: *mut *mut c_void,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_get_die_address_size(
        die: *mut c_void,
        address_size: *mut u16,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_loclist_from_expr_a(
        dbg: *mut c_void,
        expression: *mut c_void,
        expression_length: u64,
        address_size: u16,
        locdescs: *mut *mut DwarfLocdesc,
        len: *mut i64,
        error: *mut *mut c_void,
    ) -> c_int;
    #[cfg(mcinspect_full_body)]
    fn dwarf_errmsg(error: *mut c_void) -> *const u8;
    #[cfg(mcinspect_full_body)]
    fn dwarf_dealloc(dbg: *mut c_void, space: *mut c_void, type_: u64);
    #[cfg(not(mcinspect_full_body))]
    fn mcinspect_print_ps_header_bridge();
    #[cfg(not(mcinspect_full_body))]
    fn mcinspect_read_usize_bridge(addr: usize, out: *mut usize);
    #[cfg(not(mcinspect_full_body))]
    fn mcinspect_get_swapper_page_table_bridge(dbg: *mut c_void, out: *mut usize);
    #[cfg(not(mcinspect_full_body))]
    fn mcinspect_print_init_pt_bridge(init_pt: usize);
    #[cfg(not(mcinspect_full_body))]
    fn print_thread(cpu: c_int, thread: usize, idle: usize, active: c_int);
}

#[repr(C)]
struct IhkOsReadKaddrDesc {
    kaddr: usize,
    len: usize,
    ubuf: *mut c_void,
    flags: c_int,
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

#[cfg(mcinspect_full_body)]
#[repr(C)]
pub struct GetoptOption {
    name: *const u8,
    has_arg: c_int,
    flag: *mut c_int,
    val: c_int,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfSig8 {
    signature: [u8; 8],
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfLoc {
    lr_atom: u8,
    lr_number: u64,
    lr_number2: u64,
    lr_offset: u64,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfLocdesc {
    ld_lopc: u64,
    ld_hipc: u64,
    ld_cents: u16,
    ld_s: *mut DwarfLoc,
    ld_from_loclist: u8,
    ld_section_offset: u64,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfSizeArg {
    name: *const u8,
    sizep: *mut usize,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfStructFieldOffsetArg {
    struct_name: *const u8,
    field_name: *const u8,
    offp: *mut usize,
}

#[cfg(mcinspect_full_body)]
#[repr(C)]
struct DwarfGlobalVarAddrArg {
    variable: *const u8,
    addrp: *mut usize,
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut symbfd: *mut c_void = core::ptr::null_mut();
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut nsyms: isize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut symtab: *mut *mut BfdSymbol = core::ptr::null_mut();
#[cfg(mcinspect_full_body)]
#[export_name = "debug"]
pub static mut MCINSPECT_DEBUG: c_int = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut mcfd: c_int = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut nr_cpus: c_int = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "help"]
pub static mut MCINSPECT_HELP: c_int = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "ps"]
pub static mut MCINSPECT_PS: c_int = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "vtop"]
pub static mut MCINSPECT_VTOP: c_int = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "pid"]
pub static mut MCINSPECT_PID: c_int = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "vtop_addr"]
pub static mut MCINSPECT_VTOP_ADDR: usize = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "clv"]
pub static mut MCINSPECT_CLV: usize = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "clv_size"]
pub static mut MCINSPECT_CLV_SIZE: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut clv_runq_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut clv_idle_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut clv_current_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut thread_tid_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[export_name = "thread_sched_list_offset"]
pub static mut MCINSPECT_THREAD_SCHED_LIST_OFFSET: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut thread_proc_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut thread_status_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut process_pid_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut process_vm_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut process_saved_cmdline_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut process_saved_cmdline_len_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut vm_address_space_offset: usize = 0;
#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut address_space_page_table_offset: usize = 0;

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub static mut mcinspect_options: [GetoptOption; 8] = [
    GetoptOption {
        name: b"kernel\0".as_ptr(),
        has_arg: 1,
        flag: core::ptr::null_mut(),
        val: b'k' as c_int,
    },
    GetoptOption {
        name: b"ps\0".as_ptr(),
        has_arg: 0,
        flag: core::ptr::addr_of_mut!(MCINSPECT_PS),
        val: 1,
    },
    GetoptOption {
        name: b"help\0".as_ptr(),
        has_arg: 0,
        flag: core::ptr::addr_of_mut!(MCINSPECT_HELP),
        val: 1,
    },
    GetoptOption {
        name: b"debug\0".as_ptr(),
        has_arg: 0,
        flag: core::ptr::addr_of_mut!(MCINSPECT_DEBUG),
        val: 1,
    },
    GetoptOption {
        name: b"vtop\0".as_ptr(),
        has_arg: 0,
        flag: core::ptr::addr_of_mut!(MCINSPECT_VTOP),
        val: 1,
    },
    GetoptOption {
        name: b"va\0".as_ptr(),
        has_arg: 1,
        flag: core::ptr::null_mut(),
        val: b'v' as c_int,
    },
    GetoptOption {
        name: b"pid\0".as_ptr(),
        has_arg: 1,
        flag: core::ptr::null_mut(),
        val: b'p' as c_int,
    },
    GetoptOption {
        name: core::ptr::null(),
        has_arg: 0,
        flag: core::ptr::null_mut(),
        val: 0,
    },
];

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
#[cfg(mcinspect_full_body)]
const IHK_OS_READ_KADDR_VIRT: c_int = 0;
#[cfg(mcinspect_full_body)]
const O_RDONLY: c_int = 0;
#[cfg(mcinspect_full_body)]
const DW_DLV_NO_ENTRY: c_int = -1;
#[cfg(mcinspect_full_body)]
const DW_DLV_OK: c_int = 0;
#[cfg(mcinspect_full_body)]
const DW_DLV_ERROR: c_int = 1;
#[cfg(mcinspect_full_body)]
const DW_DLC_READ: u64 = 0;
#[cfg(mcinspect_full_body)]
const DW_DLA_STRING: u64 = 0x01;
#[cfg(mcinspect_full_body)]
const DW_DLA_DIE: u64 = 0x08;
#[cfg(mcinspect_full_body)]
const DW_DLA_ATTR: u64 = 0x0a;
#[cfg(mcinspect_full_body)]
const DW_DLA_LIST: u64 = 0x0f;
#[cfg(mcinspect_full_body)]
const DW_TAG_MEMBER: u16 = 0x0d;
#[cfg(mcinspect_full_body)]
const DW_TAG_STRUCTURE_TYPE: u16 = 0x13;
#[cfg(mcinspect_full_body)]
const DW_TAG_VARIABLE: u16 = 0x34;
#[cfg(mcinspect_full_body)]
const DW_FORM_BLOCK2: u16 = 0x03;
#[cfg(mcinspect_full_body)]
const DW_FORM_BLOCK4: u16 = 0x04;
#[cfg(mcinspect_full_body)]
const DW_FORM_DATA2: u16 = 0x05;
#[cfg(mcinspect_full_body)]
const DW_FORM_DATA4: u16 = 0x06;
#[cfg(mcinspect_full_body)]
const DW_FORM_DATA8: u16 = 0x07;
#[cfg(mcinspect_full_body)]
const DW_FORM_BLOCK: u16 = 0x09;
#[cfg(mcinspect_full_body)]
const DW_FORM_BLOCK1: u16 = 0x0a;
#[cfg(mcinspect_full_body)]
const DW_FORM_DATA1: u16 = 0x0b;
#[cfg(mcinspect_full_body)]
const DW_FORM_SDATA: u16 = 0x0d;
#[cfg(mcinspect_full_body)]
const DW_FORM_UDATA: u16 = 0x0f;
#[cfg(mcinspect_full_body)]
const DW_FORM_SEC_OFFSET: u16 = 0x17;
#[cfg(mcinspect_full_body)]
const DW_FORM_EXPRLOC: u16 = 0x18;
#[cfg(mcinspect_full_body)]
const DW_AT_LOCATION: u16 = 0x02;
#[cfg(mcinspect_full_body)]
const DW_AT_BYTE_SIZE: u16 = 0x0b;
#[cfg(mcinspect_full_body)]
const DW_AT_DATA_MEMBER_LOCATION: u16 = 0x38;
#[cfg(mcinspect_full_body)]
const DW_OP_ADDR: u32 = 0x03;
#[cfg(mcinspect_full_body)]
const DW_OP_PLUS_UCONST: u32 = 0x23;

type McinspectFindProcFn =
    unsafe extern "C" fn(dbg: *mut c_void, pid: c_int, rproc: *mut usize) -> c_int;
type McinspectGetSwapperFn = unsafe extern "C" fn(dbg: *mut c_void, out: *mut usize);
type McinspectReadUsizeFn = unsafe extern "C" fn(addr: usize, out: *mut usize);
type McinspectPrintUsizeFn = unsafe extern "C" fn(value: usize);
type McinspectPrintThreadFn =
    unsafe extern "C" fn(cpu: c_int, thread: usize, idle: usize, active: c_int);
type McinspectUsageFn = unsafe extern "C" fn(argv: *mut *mut u8);
type McinspectInitBfdFn = unsafe extern "C" fn(fname: *mut u8) -> c_int;
type McinspectOpenReadonlyFn = unsafe extern "C" fn(path: *const u8) -> c_int;
type McinspectDwarfInitFn =
    unsafe extern "C" fn(fd: c_int, dbg: *mut *mut c_void, err: *mut *mut c_void) -> c_int;
type McinspectInitGlobalsFn = unsafe extern "C" fn(dbg: *mut c_void);
type McinspectDwarfCommandFn = unsafe extern "C" fn(dbg: *mut c_void) -> c_int;
type McinspectMcvtopFn =
    unsafe extern "C" fn(dbg: *mut c_void, pid: c_int, vtop_addr: usize) -> c_int;
type McinspectDwarfFinishFn =
    unsafe extern "C" fn(dbg: *mut c_void, err: *mut *mut c_void) -> c_int;
type McinspectCloseFn = unsafe extern "C" fn(fd: c_int) -> c_int;
type McinspectGetoptLongFn = unsafe extern "C" fn(
    argc: c_int,
    argv: *mut *mut u8,
    shortopts: *const u8,
    longopts: *const c_void,
    optarg_out: *mut *mut u8,
) -> c_int;
#[cfg(mcinspect_full_body)]
type DwarfWalkFn =
    unsafe extern "C" fn(dbg: *mut c_void, die: *mut c_void, arg: *mut c_void) -> c_int;

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

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_open_readonly_bridge(path: *const u8) -> c_int {
    unsafe { open(path, O_RDONLY) }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_init_read_bridge(
    fd: c_int,
    dbg: *mut *mut c_void,
    error: *mut *mut c_void,
) -> c_int {
    if unsafe {
        dwarf_init(
            fd,
            DW_DLC_READ,
            core::ptr::null_mut(),
            core::ptr::null_mut(),
            dbg,
            error,
        )
    } == DW_DLV_OK
    {
        0
    } else {
        -1
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_dwarf_finish_bridge(
    dbg: *mut c_void,
    error: *mut *mut c_void,
) -> c_int {
    unsafe { dwarf_finish(dbg, error) }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_close_bridge(fd: c_int) -> c_int {
    unsafe { close(fd) }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_getopt_long_bridge(
    argc: c_int,
    argv: *mut *mut u8,
    shortopts: *const u8,
    longopts: *const c_void,
    optarg_out: *mut *mut u8,
) -> c_int {
    let opt = unsafe {
        getopt_long(
            argc,
            argv,
            shortopts,
            longopts.cast::<GetoptOption>(),
            core::ptr::null_mut(),
        )
    };
    if !optarg_out.is_null() {
        unsafe {
            *optarg_out = GETOPT_OPTARG;
        }
    }
    opt
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_print_ps_header_bridge() {
    let mut header = [0u8; 128];
    if unsafe { mcinspect_ps_header_result(header.as_mut_ptr(), header.len()) } >= 0 {
        unsafe {
            fputs(header.as_ptr(), stdout);
        }
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_read_usize_bridge(addr: usize, out: *mut usize) {
    if !out.is_null() {
        unsafe {
            *out = read_kernel_usize(addr);
        }
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_print_init_pt_bridge(init_pt: usize) {
    unsafe {
        fprintf(
            stdout,
            b"%s: init_pt: 0x%lx\n\0".as_ptr(),
            b"mcvtop\0".as_ptr(),
            init_pt,
        );
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn print_thread(cpu: c_int, thread: usize, idle: usize, active: c_int) {
    let tid = unsafe { read_kernel_i32(thread.wrapping_add(thread_tid_offset)) };
    let proc = unsafe { read_kernel_usize(thread.wrapping_add(thread_proc_offset)) };
    let status = unsafe { read_kernel_i32(thread.wrapping_add(thread_status_offset)) };
    let pid = unsafe { read_kernel_i32(proc.wrapping_add(process_pid_offset)) };
    let cmd_line_len =
        unsafe { read_kernel_usize(proc.wrapping_add(process_saved_cmdline_len_offset)) };
    let mut cmd_line: *mut c_void = core::ptr::null_mut();
    let mut comm =
        unsafe { mcinspect_thread_comm_result(core::ptr::null(), (thread == idle) as i32) };

    if cmd_line_len != 0 {
        cmd_line = unsafe { malloc(cmd_line_len.saturating_add(1)) };
        if cmd_line.is_null() {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: allocating cmdline\n\0".as_ptr(),
                    b"print_thread\0".as_ptr(),
                );
                exit(1);
            }
        }
        unsafe {
            memset(cmd_line, 0, cmd_line_len.saturating_add(1));
        }
        let cmd_line_addr =
            unsafe { read_kernel_usize(proc.wrapping_add(process_saved_cmdline_offset)) };
        unsafe {
            ihk_read_kernel(
                cmd_line_addr,
                cmd_line_len,
                cmd_line,
                IHK_OS_READ_KADDR_VIRT,
            );
        }
        comm = unsafe {
            mcinspect_thread_comm_result(cmd_line.cast_const().cast(), (thread == idle) as i32)
        };
    }

    let mut line = [0u8; 128];
    let marker = unsafe { mcinspect_thread_active_marker_result(active) };
    let status_label = unsafe { mcinspect_thread_status_label_result(status) };
    if unsafe {
        mcinspect_thread_line_result(
            line.as_mut_ptr(),
            line.len(),
            cpu,
            marker,
            tid,
            pid,
            thread,
            status_label,
            comm,
        )
    } >= 0
    {
        unsafe {
            fputs(line.as_ptr(), stdout);
        }
    } else {
        unsafe {
            fprintf(
                stdout,
                b"%3d %s%6d %6d 0x%16lx %2s %s\n\0".as_ptr(),
                cpu,
                marker,
                tid,
                pid,
                thread,
                status_label,
                comm,
            );
        }
    }

    if !cmd_line.is_null() {
        unsafe {
            free(cmd_line);
        }
    }
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_walk_tree_internal(dbg: *mut c_void, func: DwarfWalkFn, arg: *mut c_void) -> c_int {
    let mut is_info = 0;
    while is_info < 2 {
        let mut cu_length = 0u64;
        let mut cu_version = 0u16;
        let mut cu_abbrev_offset = 0u64;
        let mut cu_pointer_size = 0u16;
        let mut cu_offset_size = 0u16;
        let mut cu_extension_size = 0u16;
        let mut type_signature = DwarfSig8 { signature: [0; 8] };
        let mut type_offset = 0u64;
        let mut cu_next_offset = 0u64;
        let mut err: *mut c_void = core::ptr::null_mut();
        let mut rc = unsafe {
            dwarf_next_cu_header_c(
                dbg,
                is_info,
                &mut cu_length,
                &mut cu_version,
                &mut cu_abbrev_offset,
                &mut cu_pointer_size,
                &mut cu_offset_size,
                &mut cu_extension_size,
                &mut type_signature,
                &mut type_offset,
                &mut cu_next_offset,
                &mut err,
            )
        };

        while rc != DW_DLV_NO_ENTRY {
            if rc != DW_DLV_OK {
                unsafe {
                    fprintf(
                        stderr,
                        b"error: dwarf_next_cu_header_c: %d %s\n\0".as_ptr(),
                        rc,
                        dwarf_errmsg(err),
                    );
                }
                return -1;
            }

            let mut unit: *mut c_void = core::ptr::null_mut();
            rc = unsafe { dwarf_siblingof(dbg, core::ptr::null_mut(), &mut unit, &mut err) };
            if rc != DW_DLV_OK {
                unsafe {
                    fprintf(
                        stderr,
                        b"error: dwarf_siblingof failed: %d %s\n\0".as_ptr(),
                        rc,
                        dwarf_errmsg(err),
                    );
                }
                return -1;
            }

            if unsafe { MCINSPECT_DEBUG } != 0 {
                unsafe {
                    dwarf_debug_print_die(dbg, unit, 0);
                }
            }

            let mut die: *mut c_void = core::ptr::null_mut();
            rc = unsafe { dwarf_child(unit, &mut die, &mut err) };
            if rc == DW_DLV_ERROR {
                unsafe {
                    fprintf(
                        stderr,
                        b"dwarf_child error: %d %s\n\0".as_ptr(),
                        rc,
                        dwarf_errmsg(err),
                    );
                }
                return -1;
            }

            while !die.is_null() {
                if unsafe { MCINSPECT_DEBUG } != 0 {
                    unsafe {
                        dwarf_debug_print_die(dbg, die, 1);
                    }
                }

                rc = unsafe { func(dbg, die, arg) };
                if rc == DW_DLV_OK {
                    return 0;
                }

                let mut next: *mut c_void = core::ptr::null_mut();
                rc = unsafe { dwarf_siblingof(dbg, die, &mut next, &mut err) };
                unsafe {
                    dwarf_dealloc(dbg, die, DW_DLA_DIE);
                }
                if rc != DW_DLV_OK {
                    break;
                }
                die = next;
            }

            rc = unsafe {
                dwarf_next_cu_header_c(
                    dbg,
                    is_info,
                    &mut cu_length,
                    &mut cu_version,
                    &mut cu_abbrev_offset,
                    &mut cu_pointer_size,
                    &mut cu_offset_size,
                    &mut cu_extension_size,
                    &mut type_signature,
                    &mut type_offset,
                    &mut cu_next_offset,
                    &mut err,
                )
            };
        }

        is_info += 1;
    }

    -1
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_debug_print_die(dbg: *mut c_void, die: *mut c_void, indent: c_int) {
    let mut err: *mut c_void = core::ptr::null_mut();
    let mut name: *mut u8 = core::ptr::null_mut();
    let mut tag = 0u16;
    let mut tag_name: *const u8 = core::ptr::null();

    let rc = unsafe { dwarf_diename(die, &mut name, &mut err) };
    if rc != DW_DLV_OK && rc != DW_DLV_NO_ENTRY {
        unsafe {
            fprintf(
                stderr,
                b"error: dwarf_diename error: %d %s\n\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return;
    }

    if unsafe { dwarf_tag(die, &mut tag, &mut err) } != DW_DLV_OK {
        if !name.is_null() {
            unsafe {
                dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
            }
        }
        return;
    }
    if unsafe { dwarf_get_TAG_name(tag as c_int, &mut tag_name) } != DW_DLV_OK {
        tag_name = b"<unknown>\0".as_ptr();
    }

    unsafe {
        fprintf(
            stdout,
            if indent != 0 {
                b"    %p <%d> %s: %s\n\0".as_ptr()
            } else {
                b"%p <%d> %s: %s\n\0".as_ptr()
            },
            die,
            tag as c_int,
            tag_name,
            if name.is_null() {
                b"<no name>\0".as_ptr()
            } else {
                name as *const u8
            },
        );
    }
    if !name.is_null() {
        unsafe {
            dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
        }
    }
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_get_size_rust(
    dbg: *mut c_void,
    die: *mut c_void,
    psize: *mut usize,
    perr: *mut *mut c_void,
) -> c_int {
    let mut attr: *mut c_void = core::ptr::null_mut();
    let mut form = 0u16;
    let rc = unsafe { dwarf_attr(die, DW_AT_BYTE_SIZE, &mut attr, perr) };
    if rc != DW_DLV_OK {
        return rc;
    }

    let rc = unsafe { dwarf_whatform(attr, &mut form, perr) };
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: getting whatform: %s\n\0".as_ptr(),
                b"dwarf_get_size\0".as_ptr(),
                dwarf_errmsg(*perr),
            );
        }
        return rc;
    }

    let form_action = unsafe {
        mcinspect_dwarf_size_form_action_result(
            form as u32,
            DW_FORM_DATA1 as u32,
            DW_FORM_DATA2 as u32,
            DW_FORM_DATA4 as u32,
            DW_FORM_DATA8 as u32,
            DW_FORM_UDATA as u32,
            DW_FORM_SDATA as u32,
        )
    };
    let size = if form_action == MCINSPECT_DWARF_FORM_UNSIGNED {
        let mut value = 0u64;
        unsafe {
            dwarf_formudata(attr, &mut value, core::ptr::null_mut());
        }
        value as usize
    } else if form_action == MCINSPECT_DWARF_FORM_SIGNED {
        let mut value = 0i64;
        unsafe {
            dwarf_formsdata(attr, &mut value, core::ptr::null_mut());
        }
        if unsafe { mcinspect_dwarf_signed_nonnegative_result(value) } == 0 {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported negative size\n\0".as_ptr(),
                    b"dwarf_get_size\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        value as usize
    } else {
        let mut locdescs: *mut *mut DwarfLocdesc = core::ptr::null_mut();
        let mut len = 0i64;
        if unsafe { dwarf_loclist_n(attr, &mut locdescs, &mut len, perr) } == DW_DLV_ERROR {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported member size\n\0".as_ptr(),
                    b"dwarf_get_size\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        let desc = unsafe { *locdescs };
        let loc = unsafe { (*desc).ld_s };
        if unsafe {
            mcinspect_dwarf_plus_uconst_expr_result(
                len as isize,
                (*desc).ld_cents as isize,
                (*loc).lr_atom as u32,
                DW_OP_PLUS_UCONST,
            )
        } == 0
        {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported location expression\n\0".as_ptr(),
                    b"dwarf_get_size\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        unsafe { (*loc).lr_number as usize }
    };

    unsafe {
        dwarf_dealloc(dbg, attr, DW_DLA_ATTR);
        *psize = size;
    }
    DW_DLV_OK
}

#[cfg(mcinspect_full_body)]
unsafe extern "C" fn dwarf_size_cb(dbg: *mut c_void, die: *mut c_void, arg: *mut c_void) -> c_int {
    let ds = arg.cast::<DwarfSizeArg>();
    let mut err: *mut c_void = core::ptr::null_mut();
    let mut name: *mut u8 = core::ptr::null_mut();
    let rc = unsafe { dwarf_diename(die, &mut name, &mut err) };
    if rc == DW_DLV_NO_ENTRY {
        return DW_DLV_NO_ENTRY;
    }
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: dwarf_diename: %d %s\n\0".as_ptr(),
                b"dwarf_size\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return rc;
    }
    if name.is_null() || !unsafe { cstr_case_eq(name as *const u8, (*ds).name) } {
        if !name.is_null() {
            unsafe {
                dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
            }
        }
        return DW_DLV_NO_ENTRY;
    }

    let mut size = 0usize;
    let rc = unsafe { dwarf_get_size_rust(dbg, die, &mut size, &mut err) };
    if rc == DW_DLV_OK {
        unsafe {
            *(*ds).sizep = size;
        }
    } else if rc != DW_DLV_NO_ENTRY {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: getting size: %s\n\0".as_ptr(),
                b"dwarf_size\0".as_ptr(),
                dwarf_errmsg(err),
            );
        }
    }
    unsafe {
        dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
    }
    rc
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_type_size(dbg: *mut c_void, name: *const u8) -> usize {
    let mut size = 0usize;
    let mut arg = DwarfSizeArg {
        name,
        sizep: &mut size,
    };
    if unsafe {
        dwarf_walk_tree_internal(dbg, dwarf_size_cb, (&mut arg as *mut DwarfSizeArg).cast())
    } != DW_DLV_OK
    {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: finding size of %s\n\0".as_ptr(),
                b"init_globals\0".as_ptr(),
                name,
            );
            exit(1);
        }
    }
    size
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_get_offset_rust(
    dbg: *mut c_void,
    die: *mut c_void,
    poffset: *mut usize,
    perr: *mut *mut c_void,
) -> c_int {
    let mut attr: *mut c_void = core::ptr::null_mut();
    let mut form = 0u16;
    let rc = unsafe { dwarf_attr(die, DW_AT_DATA_MEMBER_LOCATION, &mut attr, perr) };
    if rc != DW_DLV_OK {
        return rc;
    }
    let rc = unsafe { dwarf_whatform(attr, &mut form, perr) };
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: getting whatform: %s\n\0".as_ptr(),
                b"dwarf_get_offset\0".as_ptr(),
                dwarf_errmsg(*perr),
            );
        }
        return rc;
    }

    let form_action = unsafe {
        mcinspect_dwarf_size_form_action_result(
            form as u32,
            DW_FORM_DATA1 as u32,
            DW_FORM_DATA2 as u32,
            DW_FORM_DATA4 as u32,
            DW_FORM_DATA8 as u32,
            DW_FORM_UDATA as u32,
            DW_FORM_SDATA as u32,
        )
    };
    let offset = if form_action == MCINSPECT_DWARF_FORM_UNSIGNED {
        let mut value = 0u64;
        unsafe {
            dwarf_formudata(attr, &mut value, core::ptr::null_mut());
        }
        value as usize
    } else if form_action == MCINSPECT_DWARF_FORM_SIGNED {
        let mut value = 0i64;
        unsafe {
            dwarf_formsdata(attr, &mut value, core::ptr::null_mut());
        }
        if unsafe { mcinspect_dwarf_signed_nonnegative_result(value) } == 0 {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported negative offset\n\0".as_ptr(),
                    b"dwarf_get_offset\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        value as usize
    } else {
        let mut locdescs: *mut *mut DwarfLocdesc = core::ptr::null_mut();
        let mut len = 0i64;
        if unsafe { dwarf_loclist_n(attr, &mut locdescs, &mut len, perr) } == DW_DLV_ERROR {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported member offset\n\0".as_ptr(),
                    b"dwarf_get_offset\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        let desc = unsafe { *locdescs };
        let loc = unsafe { (*desc).ld_s };
        if unsafe {
            mcinspect_dwarf_plus_uconst_expr_result(
                len as isize,
                (*desc).ld_cents as isize,
                (*loc).lr_atom as u32,
                DW_OP_PLUS_UCONST,
            )
        } == 0
        {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported location expression\n\0".as_ptr(),
                    b"dwarf_get_offset\0".as_ptr(),
                );
            }
            return DW_DLV_ERROR;
        }
        unsafe { (*loc).lr_number as usize }
    };

    unsafe {
        dwarf_dealloc(dbg, attr, DW_DLA_ATTR);
        *poffset = offset;
    }
    DW_DLV_OK
}

#[cfg(mcinspect_full_body)]
unsafe extern "C" fn dwarf_struct_field_offset_cb(
    dbg: *mut c_void,
    die: *mut c_void,
    arg: *mut c_void,
) -> c_int {
    let dsfo = arg.cast::<DwarfStructFieldOffsetArg>();
    let mut err: *mut c_void = core::ptr::null_mut();
    let mut tag = 0u16;
    let mut name: *mut u8 = core::ptr::null_mut();
    let rc = unsafe { dwarf_tag(die, &mut tag, &mut err) };
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: dwarf_tag: %d %s\n\0".as_ptr(),
                b"dwarf_struct_field_offset\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return rc;
    }
    let rc = unsafe { dwarf_diename(die, &mut name, &mut err) };
    if rc == DW_DLV_NO_ENTRY {
        return DW_DLV_NO_ENTRY;
    }
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: dwarf_diename: %d %s\n\0".as_ptr(),
                b"dwarf_struct_field_offset\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return rc;
    }
    if unsafe {
        mcinspect_dwarf_named_tag_match_result(
            tag as u32,
            DW_TAG_STRUCTURE_TYPE as u32,
            name,
            (*dsfo).struct_name,
        )
    } == 0
    {
        unsafe {
            dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
        }
        return DW_DLV_NO_ENTRY;
    }
    unsafe {
        dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
    }

    let mut child: *mut c_void = core::ptr::null_mut();
    let rc = unsafe { dwarf_child(die, &mut child, &mut err) };
    if rc == DW_DLV_ERROR {
        unsafe {
            fprintf(
                stderr,
                b"%s: dwarf_child error: %d %s\n\0".as_ptr(),
                b"dwarf_struct_field_offset\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return DW_DLV_NO_ENTRY;
    }

    while !child.is_null() {
        let mut child_name: *mut u8 = core::ptr::null_mut();
        let mut child_tag = 0u16;
        let name_rc = unsafe { dwarf_diename(child, &mut child_name, &mut err) };
        if name_rc != DW_DLV_OK && name_rc != DW_DLV_NO_ENTRY {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: dwarf_diename: %d %s\n\0".as_ptr(),
                    b"dwarf_struct_field_offset\0".as_ptr(),
                    name_rc,
                    dwarf_errmsg(err),
                );
            }
            return name_rc;
        }
        let tag_rc = unsafe { dwarf_tag(child, &mut child_tag, &mut err) };
        if tag_rc != DW_DLV_OK {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: dwarf_tag: %d %s\n\0".as_ptr(),
                    b"dwarf_struct_field_offset\0".as_ptr(),
                    tag_rc,
                    dwarf_errmsg(err),
                );
            }
            return tag_rc;
        }

        let matched = unsafe {
            mcinspect_dwarf_named_tag_match_result(
                child_tag as u32,
                DW_TAG_MEMBER as u32,
                child_name,
                (*dsfo).field_name,
            )
        } != 0;
        if !child_name.is_null() {
            unsafe {
                dwarf_dealloc(dbg, child_name.cast(), DW_DLA_STRING);
            }
        }
        if matched {
            let mut offset = 0usize;
            let off_rc = unsafe { dwarf_get_offset_rust(dbg, child, &mut offset, &mut err) };
            if off_rc != DW_DLV_OK && off_rc != DW_DLV_NO_ENTRY {
                unsafe {
                    fprintf(
                        stderr,
                        b"%s: error: getting dwarf attr offset: %s\n\0".as_ptr(),
                        b"dwarf_struct_field_offset\0".as_ptr(),
                        dwarf_errmsg(err),
                    );
                }
                return off_rc;
            }
            unsafe {
                *(*dsfo).offp = offset;
                dwarf_dealloc(dbg, child, DW_DLA_DIE);
            }
            return DW_DLV_OK;
        }

        let mut next: *mut c_void = core::ptr::null_mut();
        let sib_rc = unsafe { dwarf_siblingof(dbg, child, &mut next, &mut err) };
        unsafe {
            dwarf_dealloc(dbg, child, DW_DLA_DIE);
        }
        if sib_rc != DW_DLV_OK {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: dwarf_siblingof: %d %s\n\0".as_ptr(),
                    b"dwarf_struct_field_offset\0".as_ptr(),
                    sib_rc,
                    dwarf_errmsg(err),
                );
            }
            return DW_DLV_NO_ENTRY;
        }
        child = next;
    }

    DW_DLV_NO_ENTRY
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_struct_field_offset(
    dbg: *mut c_void,
    struct_name: *const u8,
    field_name: *const u8,
) -> usize {
    let mut offset = 0usize;
    let mut arg = DwarfStructFieldOffsetArg {
        struct_name,
        field_name,
        offp: &mut offset,
    };
    if unsafe {
        dwarf_walk_tree_internal(
            dbg,
            dwarf_struct_field_offset_cb,
            (&mut arg as *mut DwarfStructFieldOffsetArg).cast(),
        )
    } != DW_DLV_OK
    {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: finding %s in struct %s\n\0".as_ptr(),
                b"init_globals\0".as_ptr(),
                field_name,
                struct_name,
            );
            exit(1);
        }
    }
    offset
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_get_address_rust(
    dbg: *mut c_void,
    die: *mut c_void,
    paddr: *mut usize,
    perr: *mut *mut c_void,
) -> c_int {
    let mut atcnt = 0i64;
    let mut atlist: *mut *mut c_void = core::ptr::null_mut();
    let mut rc = unsafe { dwarf_attrlist(die, &mut atlist, &mut atcnt, perr) };
    if rc == DW_DLV_ERROR {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: getting attrlist: %s\n\0".as_ptr(),
                b"dwarf_get_address\0".as_ptr(),
                dwarf_errmsg(*perr),
            );
        }
        return rc;
    }
    if rc == DW_DLV_NO_ENTRY {
        return rc;
    }

    let mut found = false;
    let mut addr = 0usize;
    let mut i = 0i64;
    while i < atcnt {
        let attr = unsafe { *atlist.add(i as usize) };
        let mut attr_i = 0u16;
        rc = unsafe { dwarf_whatattr(attr, &mut attr_i, perr) };
        if rc != DW_DLV_OK {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: getting attr: %s\n\0".as_ptr(),
                    b"dwarf_get_address\0".as_ptr(),
                    dwarf_errmsg(*perr),
                );
            }
            break;
        }
        if attr_i != DW_AT_LOCATION {
            i += 1;
            continue;
        }
        unsafe {
            fprintf(
                stdout,
                b"%s: DW_AT_location\n\0".as_ptr(),
                b"dwarf_get_address\0".as_ptr(),
            );
        }

        let mut form = 0u16;
        rc = unsafe { dwarf_whatform(attr, &mut form, perr) };
        if rc != DW_DLV_OK {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: getting whatform: %s\n\0".as_ptr(),
                    b"dwarf_get_address\0".as_ptr(),
                    dwarf_errmsg(*perr),
                );
            }
            break;
        }
        let mut directform = 0u16;
        unsafe {
            dwarf_whatform_direct(attr, &mut directform, perr);
        }

        let form_action = unsafe {
            mcinspect_dwarf_addr_form_action_result(
                form as u32,
                DW_FORM_BLOCK1 as u32,
                DW_FORM_BLOCK2 as u32,
                DW_FORM_BLOCK4 as u32,
                DW_FORM_BLOCK as u32,
                DW_FORM_DATA4 as u32,
                DW_FORM_DATA8 as u32,
                DW_FORM_SEC_OFFSET as u32,
                DW_FORM_EXPRLOC as u32,
            )
        };

        if form_action == MCINSPECT_DWARF_FORM_LOCLIST {
            let mut locdescs: *mut *mut DwarfLocdesc = core::ptr::null_mut();
            let mut len = 0i64;
            if unsafe { dwarf_loclist_n(attr, &mut locdescs, &mut len, perr) } == DW_DLV_ERROR {
                unsafe {
                    fprintf(
                        stderr,
                        b"%s: dwarf_loclist_n: %s\n\0".as_ptr(),
                        b"dwarf_get_address\0".as_ptr(),
                        dwarf_errmsg(*perr),
                    );
                }
                rc = DW_DLV_ERROR;
                break;
            }
            let desc = unsafe { *locdescs };
            let loc = unsafe { (*desc).ld_s };
            if unsafe {
                mcinspect_dwarf_addr_expr_result(
                    len as isize,
                    (*desc).ld_cents as isize,
                    (*loc).lr_atom as u32,
                    DW_OP_ADDR,
                )
            } == 0
            {
                unsafe {
                    fprintf(
                        stderr,
                        b"%s: unsupported addr expression\n\0".as_ptr(),
                        b"dwarf_get_address\0".as_ptr(),
                    );
                }
                rc = DW_DLV_ERROR;
                break;
            }
            addr = unsafe { (*loc).lr_number as usize };
        } else if form_action == MCINSPECT_DWARF_FORM_EXPRLOC {
            let mut address_size = 0u16;
            let mut expr: *mut c_void = core::ptr::null_mut();
            let mut expr_len = 0u64;
            let mut locdesc: *mut DwarfLocdesc = core::ptr::null_mut();
            let mut len = 0i64;
            rc = unsafe { dwarf_formexprloc(attr, &mut expr_len, &mut expr, perr) };
            if rc != DW_DLV_OK {
                unsafe {
                    fprintf(
                        stderr,
                        if rc == DW_DLV_NO_ENTRY {
                            b"%s: dwarf_formexprloc: no entry?\n\0".as_ptr()
                        } else {
                            b"%s: dwarf_formexprloc(): %s\n\0".as_ptr()
                        },
                        b"dwarf_get_address\0".as_ptr(),
                        dwarf_errmsg(*perr),
                    );
                }
                break;
            }
            rc = unsafe { dwarf_get_die_address_size(die, &mut address_size, perr) };
            if rc != DW_DLV_OK {
                unsafe {
                    fprintf(
                        stderr,
                        if rc == DW_DLV_NO_ENTRY {
                            b"%s: dwarf_get_die_address_size: no entry?\n\0".as_ptr()
                        } else {
                            b"%s: dwarf_get_die_address_size: %s\n\0".as_ptr()
                        },
                        b"dwarf_get_address\0".as_ptr(),
                        dwarf_errmsg(*perr),
                    );
                }
                break;
            }
            rc = unsafe {
                dwarf_loclist_from_expr_a(
                    dbg,
                    expr,
                    expr_len,
                    address_size,
                    &mut locdesc,
                    &mut len,
                    perr,
                )
            };
            if rc != DW_DLV_OK {
                unsafe {
                    fprintf(
                        stderr,
                        if rc == DW_DLV_NO_ENTRY {
                            b"%s: dwarf_loclist_from_expr_a: no entry?\n\0".as_ptr()
                        } else {
                            b"%s: dwarf_loclist_from_expr_a: %s\n\0".as_ptr()
                        },
                        b"dwarf_get_address\0".as_ptr(),
                        dwarf_errmsg(*perr),
                    );
                }
                break;
            }
            let loc = unsafe { (*locdesc).ld_s };
            if unsafe {
                mcinspect_dwarf_addr_expr_result(
                    len as isize,
                    (*locdesc).ld_cents as isize,
                    (*loc).lr_atom as u32,
                    DW_OP_ADDR,
                )
            } == 0
            {
                unsafe {
                    fprintf(
                        stderr,
                        b"%s: unsupported addr expression\n\0".as_ptr(),
                        b"dwarf_get_address\0".as_ptr(),
                    );
                }
                rc = DW_DLV_ERROR;
                break;
            }
            addr = unsafe { (*loc).lr_number as usize };
        } else {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: unsupported form type?\n\0".as_ptr(),
                    b"dwarf_get_address\0".as_ptr(),
                );
            }
            rc = DW_DLV_ERROR;
            break;
        }

        found = true;
        break;
    }

    let mut j = 0i64;
    while j < atcnt {
        unsafe {
            dwarf_dealloc(dbg, *atlist.add(j as usize), DW_DLA_ATTR);
        }
        j += 1;
    }
    unsafe {
        dwarf_dealloc(dbg, atlist.cast(), DW_DLA_LIST);
    }

    if found {
        unsafe {
            *paddr = addr;
        }
        if unsafe { MCINSPECT_DEBUG } != 0 {
            unsafe {
                fprintf(
                    stdout,
                    b"%s: addr: 0x%lx\n\0".as_ptr(),
                    b"dwarf_get_address\0".as_ptr(),
                    addr,
                );
            }
        }
        DW_DLV_OK
    } else if rc == DW_DLV_ERROR {
        DW_DLV_ERROR
    } else {
        DW_DLV_NO_ENTRY
    }
}

#[cfg(mcinspect_full_body)]
unsafe extern "C" fn dwarf_global_var_addr_cb(
    dbg: *mut c_void,
    die: *mut c_void,
    arg: *mut c_void,
) -> c_int {
    let gva = arg.cast::<DwarfGlobalVarAddrArg>();
    let mut err: *mut c_void = core::ptr::null_mut();
    let mut tag = 0u16;
    let mut name: *mut u8 = core::ptr::null_mut();
    let rc = unsafe { dwarf_tag(die, &mut tag, &mut err) };
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: dwarf_tag: %d %s\n\0".as_ptr(),
                b"dwarf_global_var_addr\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return rc;
    }
    let rc = unsafe { dwarf_diename(die, &mut name, &mut err) };
    if rc == DW_DLV_NO_ENTRY {
        return DW_DLV_NO_ENTRY;
    }
    if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: dwarf_diename: %d %s\n\0".as_ptr(),
                b"dwarf_global_var_addr\0".as_ptr(),
                rc,
                dwarf_errmsg(err),
            );
        }
        return rc;
    }
    if unsafe {
        mcinspect_dwarf_named_tag_match_result(
            tag as u32,
            DW_TAG_VARIABLE as u32,
            name,
            (*gva).variable,
        )
    } == 0
    {
        unsafe {
            dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
        }
        return DW_DLV_NO_ENTRY;
    }

    unsafe {
        fprintf(
            stdout,
            b"%s: inspecting %s\n\0".as_ptr(),
            b"dwarf_global_var_addr\0".as_ptr(),
            name,
        );
    }
    let mut addr = 0usize;
    let rc = unsafe { dwarf_get_address_rust(dbg, die, &mut addr, &mut err) };
    if rc == DW_DLV_NO_ENTRY {
        unsafe {
            fprintf(
                stdout,
                b"%s: inspecting %s -> DW_DLV_NO_ENTRY for addr?\n\0".as_ptr(),
                b"dwarf_global_var_addr\0".as_ptr(),
                name,
            );
        }
    } else if rc != DW_DLV_OK {
        unsafe {
            fprintf(
                stderr,
                b"%s: error: getting dwarf addr location: %s\n\0".as_ptr(),
                b"dwarf_global_var_addr\0".as_ptr(),
                dwarf_errmsg(err),
            );
        }
    } else {
        unsafe {
            *(*gva).addrp = addr;
        }
    }
    unsafe {
        dwarf_dealloc(dbg, name.cast(), DW_DLA_STRING);
    }
    rc
}

#[cfg(mcinspect_full_body)]
unsafe fn dwarf_variable_address(dbg: *mut c_void, variable: *const u8) -> usize {
    let mut addr = unsafe { lookup_bfd_symbol(variable as *mut u8) };
    if addr == MCINSPECT_NOSYMBOL {
        let mut arg = DwarfGlobalVarAddrArg {
            variable,
            addrp: &mut addr,
        };
        if unsafe {
            dwarf_walk_tree_internal(
                dbg,
                dwarf_global_var_addr_cb,
                (&mut arg as *mut DwarfGlobalVarAddrArg).cast(),
            )
        } != DW_DLV_OK
        {
            unsafe {
                fprintf(
                    stderr,
                    b"%s: error: finding addr of %s\n\0".as_ptr(),
                    b"init_globals\0".as_ptr(),
                    variable,
                );
                exit(1);
            }
        }
    }
    addr
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_init_globals_bridge(dbg: *mut c_void) {
    unsafe {
        mcinspect_init_globals_body_result(
            dwarf_variable_address(dbg, b"mck_num_processors\0".as_ptr()),
            dwarf_variable_address(dbg, b"clv\0".as_ptr()),
            dwarf_type_size(dbg, b"cpu_local_var\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"cpu_local_var\0".as_ptr(), b"runq\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"cpu_local_var\0".as_ptr(), b"idle\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"cpu_local_var\0".as_ptr(), b"current\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"thread\0".as_ptr(), b"tid\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"thread\0".as_ptr(), b"proc\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"thread\0".as_ptr(), b"status\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"thread\0".as_ptr(), b"sched_list\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"process\0".as_ptr(), b"pid\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"process\0".as_ptr(), b"saved_cmdline\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"process\0".as_ptr(), b"saved_cmdline_len\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"process\0".as_ptr(), b"vm\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"process_vm\0".as_ptr(), b"address_space\0".as_ptr()),
            dwarf_struct_field_offset(dbg, b"address_space\0".as_ptr(), b"page_table\0".as_ptr()),
        );
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn mcinspect_get_swapper_page_table_bridge(
    dbg: *mut c_void,
    out: *mut usize,
) {
    if !out.is_null() {
        let addr = unsafe { dwarf_variable_address(dbg, b"swapper_page_table\0".as_ptr()) };
        unsafe {
            *out = read_kernel_usize(addr);
        }
    }
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

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcinspect_init_globals_body_result(
    mck_num_processors_addr: usize,
    clv_addr: usize,
    cpu_local_var_size: usize,
    clv_runq: usize,
    clv_idle: usize,
    clv_current: usize,
    thread_tid: usize,
    thread_proc: usize,
    thread_status: usize,
    thread_sched_list: usize,
    process_pid: usize,
    process_saved_cmdline: usize,
    process_saved_cmdline_len: usize,
    process_vm: usize,
    vm_address_space: usize,
    address_space_page_table: usize,
) -> c_int {
    let num_processors_addr = unsafe { read_kernel_usize(mck_num_processors_addr) };
    unsafe {
        nr_cpus = read_kernel_i32(num_processors_addr);
        MCINSPECT_CLV = read_kernel_usize(clv_addr);
        MCINSPECT_CLV_SIZE = cpu_local_var_size;
        clv_runq_offset = clv_runq;
        clv_idle_offset = clv_idle;
        clv_current_offset = clv_current;
        thread_tid_offset = thread_tid;
        thread_proc_offset = thread_proc;
        thread_status_offset = thread_status;
        MCINSPECT_THREAD_SCHED_LIST_OFFSET = thread_sched_list;
        process_pid_offset = process_pid;
        process_saved_cmdline_offset = process_saved_cmdline;
        process_saved_cmdline_len_offset = process_saved_cmdline_len;
        process_vm_offset = process_vm;
        vm_address_space_offset = vm_address_space;
        address_space_page_table_offset = address_space_page_table;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_mcvtop_body_result(
    dbg: *mut c_void,
    pid: c_int,
    _vtop_addr: usize,
    find_proc_fn: Option<McinspectFindProcFn>,
    get_swapper_page_table_fn: Option<McinspectGetSwapperFn>,
    read_usize_fn: Option<McinspectReadUsizeFn>,
    print_init_pt_fn: Option<McinspectPrintUsizeFn>,
) -> c_int {
    let (
        Some(find_proc_fn),
        Some(get_swapper_page_table_fn),
        Some(read_usize_fn),
        Some(print_init_pt_fn),
    ) = (
        find_proc_fn,
        get_swapper_page_table_fn,
        read_usize_fn,
        print_init_pt_fn,
    )
    else {
        return -22;
    };

    let mut proc = 0usize;
    if pid != 0 && unsafe { find_proc_fn(dbg, pid, &mut proc) } < 0 {
        return -1;
    }

    let mut init_pt = 0usize;
    unsafe {
        get_swapper_page_table_fn(dbg, &mut init_pt);
        print_init_pt_fn(init_pt);
    }

    if proc != 0 {
        let mut vm = 0usize;
        let mut ap = 0usize;
        let mut pt = 0usize;
        unsafe {
            read_usize_fn(proc.wrapping_add(process_vm_offset), &mut vm);
            read_usize_fn(vm.wrapping_add(vm_address_space_offset), &mut ap);
            read_usize_fn(ap.wrapping_add(address_space_page_table_offset), &mut pt);
        }
        let _ = pt;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_mcps_body_result(
    read_usize_fn: Option<McinspectReadUsizeFn>,
    print_thread_fn: Option<McinspectPrintThreadFn>,
) -> c_int {
    let (Some(read_usize_fn), Some(print_thread_fn)) = (read_usize_fn, print_thread_fn) else {
        return -22;
    };

    let cpu_count = unsafe { nr_cpus };
    let mut cpu = 0i32;
    while cpu < cpu_count {
        let per_cpu =
            unsafe { mcinspect_cpu_local_base_result(MCINSPECT_CLV, MCINSPECT_CLV_SIZE, cpu) };
        let runq = unsafe { per_cpu.wrapping_add(clv_runq_offset) };
        let idle = unsafe { per_cpu.wrapping_add(clv_idle_offset) };
        let mut current = 0usize;
        let mut thread_sched_list = 0usize;

        unsafe {
            read_usize_fn(per_cpu.wrapping_add(clv_current_offset), &mut current);
            read_usize_fn(
                per_cpu.wrapping_add(clv_runq_offset),
                &mut thread_sched_list,
            );
            print_thread_fn(cpu, current, idle, 1);
        }

        while thread_sched_list != runq {
            let thread = unsafe {
                mcinspect_thread_from_sched_list_result(
                    thread_sched_list,
                    MCINSPECT_THREAD_SCHED_LIST_OFFSET,
                )
            };
            if thread != current {
                unsafe {
                    print_thread_fn(cpu, thread, idle, 0);
                }
            }
            unsafe {
                read_usize_fn(thread_sched_list, &mut thread_sched_list);
            }
        }

        if current != idle {
            unsafe {
                print_thread_fn(cpu, idle, idle, 0);
            }
        }

        cpu += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcps(_dbg: *mut c_void) -> c_int {
    let mut header = [0u8; 128];
    if unsafe { mcinspect_ps_header_result(header.as_mut_ptr(), header.len()) } >= 0 {
        unsafe {
            fputs(header.as_ptr(), stdout);
        }
    } else {
        unsafe {
            mcinspect_print_ps_header_bridge();
        }
    }

    unsafe { mcinspect_mcps_body_result(Some(mcinspect_read_usize_bridge), Some(print_thread)) }
}

#[no_mangle]
pub unsafe extern "C" fn mcvtop(dbg: *mut c_void, pid: c_int, vtop_addr: usize) -> c_int {
    unsafe {
        mcinspect_mcvtop_body_result(
            dbg,
            pid,
            vtop_addr,
            Some(find_proc),
            Some(mcinspect_get_swapper_page_table_bridge),
            Some(mcinspect_read_usize_bridge),
            Some(mcinspect_print_init_pt_bridge),
        )
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_no_symbols_line_result(buf: *mut u8, buf_size: usize) -> i32 {
    let mut pos = 0usize;
    let ok = unsafe { write_bytes_checked(buf, &mut pos, buf_size, b"no symbols\n") };
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
    }
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
    if ok {
        pos as i32
    } else {
        -1
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
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcinspect_main_body_result(
    argv: *mut *mut u8,
    help: c_int,
    kernel_path: *mut u8,
    ps: c_int,
    vtop: c_int,
    pid: c_int,
    vtop_addr: usize,
    usage_fn: Option<McinspectUsageFn>,
    init_bfd_symbols_fn: Option<McinspectInitBfdFn>,
    open_readonly_fn: Option<McinspectOpenReadonlyFn>,
    dwarf_init_fn: Option<McinspectDwarfInitFn>,
    init_globals_fn: Option<McinspectInitGlobalsFn>,
    mcps_fn: Option<McinspectDwarfCommandFn>,
    mcvtop_fn: Option<McinspectMcvtopFn>,
    dwarf_finish_fn: Option<McinspectDwarfFinishFn>,
    close_fn: Option<McinspectCloseFn>,
) -> c_int {
    let (
        Some(usage_fn),
        Some(init_bfd_symbols_fn),
        Some(open_readonly_fn),
        Some(dwarf_init_fn),
        Some(init_globals_fn),
        Some(mcps_fn),
        Some(mcvtop_fn),
        Some(dwarf_finish_fn),
        Some(close_fn),
    ) = (
        usage_fn,
        init_bfd_symbols_fn,
        open_readonly_fn,
        dwarf_init_fn,
        init_globals_fn,
        mcps_fn,
        mcvtop_fn,
        dwarf_finish_fn,
        close_fn,
    )
    else {
        return -22;
    };

    let preflight =
        unsafe { mcinspect_main_preflight_action_result(help, kernel_path.cast_const(), ps, vtop) };
    if preflight == MCINSPECT_MAIN_HELP {
        unsafe {
            usage_fn(argv);
        }
        return 0;
    }
    if preflight == MCINSPECT_MAIN_MISSING_KERNEL {
        let mut line = [0u8; 128];
        if unsafe { mcinspect_missing_kernel_error_result(line.as_mut_ptr(), line.len()) } >= 0 {
            unsafe {
                fputs(line.as_ptr(), stderr);
            }
        }
        unsafe {
            usage_fn(argv);
        }
        return 1;
    }
    if preflight == MCINSPECT_MAIN_NO_ACTION {
        let mut line = [0u8; 64];
        if unsafe { mcinspect_pid_line_result(line.as_mut_ptr(), line.len(), pid) } >= 0 {
            unsafe {
                fputs(line.as_ptr(), stdout);
            }
        }
        unsafe {
            usage_fn(argv);
        }
        return 1;
    }

    if unsafe { init_bfd_symbols_fn(kernel_path) } < 0 {
        let mut line = [0u8; 1024];
        if unsafe { mcinspect_elf_image_error_result(line.as_mut_ptr(), line.len(), kernel_path) }
            >= 0
        {
            unsafe {
                fputs(line.as_ptr(), stderr);
            }
        }
        return 1;
    }

    let mut mcos_path = [0u8; 64];
    unsafe {
        mcinspect_mcos_path_result(mcos_path.as_mut_ptr(), 0);
        mcfd = open_readonly_fn(mcos_path.as_ptr());
    }
    if unsafe { mcfd } < 0 {
        let mut line = [0u8; 128];
        if unsafe { mcinspect_open_os_device_error_result(line.as_mut_ptr(), line.len()) } >= 0 {
            unsafe {
                fputs(line.as_ptr(), stderr);
            }
        }
        return 1;
    }

    let dwarffd = unsafe { open_readonly_fn(kernel_path.cast_const()) };
    if dwarffd < 0 {
        let mut line = [0u8; 1024];
        if unsafe { mcinspect_open_kernel_error_result(line.as_mut_ptr(), line.len(), kernel_path) }
            >= 0
        {
            unsafe {
                fputs(line.as_ptr(), stderr);
            }
        }
        return 1;
    }

    let mut dbg: *mut c_void = core::ptr::null_mut();
    let mut error: *mut c_void = core::ptr::null_mut();
    if unsafe { dwarf_init_fn(dwarffd, &mut dbg, &mut error) } != 0 {
        let mut line = [0u8; 128];
        if unsafe { mcinspect_dwarf_info_error_result(line.as_mut_ptr(), line.len()) } >= 0 {
            unsafe {
                fputs(line.as_ptr(), stderr);
            }
        }
        return 1;
    }

    unsafe {
        init_globals_fn(dbg);
        if ps != 0 {
            mcps_fn(dbg);
        }
        if vtop != 0 {
            mcvtop_fn(dbg, pid, vtop_addr);
        }
        dwarf_finish_fn(dbg, &mut error);
        close_fn(dwarffd);
        close_fn(mcfd);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_option_body_result(
    opt: c_int,
    optarg: *mut u8,
    kernel_path_out: *mut *mut u8,
    vtop_addr_out: *mut usize,
    pid_out: *mut c_int,
    argv: *mut *mut u8,
    usage_fn: Option<McinspectUsageFn>,
) -> c_int {
    if opt == b'k' as c_int {
        if kernel_path_out.is_null() {
            return -22;
        }
        unsafe {
            *kernel_path_out = optarg;
        }
        return 0;
    }

    if opt == b'v' as c_int {
        if vtop_addr_out.is_null() {
            return -22;
        }
        if unsafe { mcinspect_parse_vtop_addr_result(optarg, vtop_addr_out) } != 0 {
            let mut line = [0u8; 128];
            if unsafe { mcinspect_invalid_va_error_result(line.as_mut_ptr(), line.len()) } >= 0 {
                unsafe {
                    fputs(line.as_ptr(), stderr);
                }
            }
            if let Some(usage_fn) = usage_fn {
                unsafe {
                    usage_fn(argv);
                }
            }
            return -1;
        }
        return 0;
    }

    if opt == b'p' as c_int {
        if pid_out.is_null() {
            return -22;
        }
        unsafe {
            *pid_out = mcinspect_parse_pid_result(optarg);
        }
        return 0;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcinspect_option_loop_body_result(
    argc: c_int,
    argv: *mut *mut u8,
    shortopts: *const u8,
    longopts: *const c_void,
    kernel_path_out: *mut *mut u8,
    vtop_addr_out: *mut usize,
    pid_out: *mut c_int,
    getopt_long_fn: Option<McinspectGetoptLongFn>,
    usage_fn: Option<McinspectUsageFn>,
) -> c_int {
    let Some(getopt_long_fn) = getopt_long_fn else {
        return -22;
    };

    if argv.is_null()
        || shortopts.is_null()
        || kernel_path_out.is_null()
        || vtop_addr_out.is_null()
        || pid_out.is_null()
    {
        return -22;
    }

    loop {
        let mut current_optarg: *mut u8 = core::ptr::null_mut();
        let opt = unsafe { getopt_long_fn(argc, argv, shortopts, longopts, &mut current_optarg) };
        if opt == -1 {
            return 0;
        }
        if unsafe {
            mcinspect_option_body_result(
                opt,
                current_optarg,
                kernel_path_out,
                vtop_addr_out,
                pid_out,
                argv,
                usage_fn,
            )
        } != 0
        {
            return -1;
        }
    }
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcinspect_main_entry_result(
    argc: c_int,
    argv: *mut *mut u8,
    shortopts: *const u8,
    longopts: *const c_void,
    getopt_long_fn: Option<McinspectGetoptLongFn>,
    usage_fn: Option<McinspectUsageFn>,
    init_bfd_symbols_fn: Option<McinspectInitBfdFn>,
    open_readonly_fn: Option<McinspectOpenReadonlyFn>,
    dwarf_init_fn: Option<McinspectDwarfInitFn>,
    init_globals_fn: Option<McinspectInitGlobalsFn>,
    mcps_fn: Option<McinspectDwarfCommandFn>,
    mcvtop_fn: Option<McinspectMcvtopFn>,
    dwarf_finish_fn: Option<McinspectDwarfFinishFn>,
    close_fn: Option<McinspectCloseFn>,
) -> c_int {
    let (
        Some(getopt_long_fn),
        Some(usage_fn),
        Some(init_bfd_symbols_fn),
        Some(open_readonly_fn),
        Some(dwarf_init_fn),
        Some(init_globals_fn),
        Some(mcps_fn),
        Some(mcvtop_fn),
        Some(dwarf_finish_fn),
        Some(close_fn),
    ) = (
        getopt_long_fn,
        usage_fn,
        init_bfd_symbols_fn,
        open_readonly_fn,
        dwarf_init_fn,
        init_globals_fn,
        mcps_fn,
        mcvtop_fn,
        dwarf_finish_fn,
        close_fn,
    )
    else {
        return -22;
    };

    if argv.is_null() || shortopts.is_null() {
        return -22;
    }

    unsafe {
        MCINSPECT_DEBUG = 0;
        mcfd = -1;
        MCINSPECT_HELP = 0;
        MCINSPECT_PS = 0;
        MCINSPECT_VTOP = 0;
        MCINSPECT_VTOP_ADDR = usize::MAX;
        MCINSPECT_PID = 0;
    }

    let mut kernel_path: *mut u8 = core::ptr::null_mut();
    if unsafe {
        mcinspect_option_loop_body_result(
            argc,
            argv,
            shortopts,
            longopts,
            &mut kernel_path,
            core::ptr::addr_of_mut!(MCINSPECT_VTOP_ADDR),
            core::ptr::addr_of_mut!(MCINSPECT_PID),
            Some(getopt_long_fn),
            Some(usage_fn),
        )
    } != 0
    {
        return 1;
    }

    unsafe {
        mcinspect_main_body_result(
            argv,
            MCINSPECT_HELP,
            kernel_path,
            MCINSPECT_PS,
            MCINSPECT_VTOP,
            MCINSPECT_PID,
            MCINSPECT_VTOP_ADDR,
            Some(usage_fn),
            Some(init_bfd_symbols_fn),
            Some(open_readonly_fn),
            Some(dwarf_init_fn),
            Some(init_globals_fn),
            Some(mcps_fn),
            Some(mcvtop_fn),
            Some(dwarf_finish_fn),
            Some(close_fn),
        )
    }
}

#[cfg(mcinspect_full_body)]
#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut u8) -> c_int {
    unsafe {
        mcinspect_main_entry_result(
            argc,
            argv,
            b"+k:v:p:\0".as_ptr(),
            core::ptr::addr_of!(mcinspect_options).cast(),
            Some(mcinspect_getopt_long_bridge),
            Some(usage),
            Some(init_bfd_symbols),
            Some(mcinspect_open_readonly_bridge),
            Some(mcinspect_dwarf_init_read_bridge),
            Some(mcinspect_init_globals_bridge),
            Some(mcps),
            Some(mcvtop),
            Some(mcinspect_dwarf_finish_bridge),
            Some(mcinspect_close_bridge),
        )
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
