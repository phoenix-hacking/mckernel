#![no_std]

use core::ffi::{c_char, c_int, c_long, c_uint, c_ulong, c_void};
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{null_mut, read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicI32, AtomicU16, AtomicU32, AtomicUsize, Ordering};

const NUL: c_char = 0;
const IHK_OS_AUX_PERF_NUM: c_uint = 0x1129_0100;
const IHK_OS_AUX_PERF_SET: c_uint = 0x1129_0101;
const IHK_OS_AUX_PERF_GET: c_uint = 0x1129_0102;
const IHK_OS_AUX_PERF_ENABLE: c_uint = 0x1129_0103;
const IHK_OS_AUX_PERF_DISABLE: c_uint = 0x1129_0104;
const IHK_OS_AUX_PERF_DESTROY: c_uint = 0x1129_0105;
const IHK_OS_GETRUSAGE: c_uint = 0x1129_0106;
const MCEXEC_UP_PREPARE_IMAGE: c_uint = 0x30a0_2900;
const MCEXEC_UP_TRANSFER: c_uint = 0x30a0_2901;
const MCEXEC_UP_START_IMAGE: c_uint = 0x30a0_2902;
const MCEXEC_UP_WAIT_SYSCALL: c_uint = 0x30a0_2903;
const MCEXEC_UP_RET_SYSCALL: c_uint = 0x30a0_2904;
const MCEXEC_UP_LOAD_SYSCALL: c_uint = 0x30a0_2905;
const MCEXEC_UP_SEND_SIGNAL: c_uint = 0x30a0_2906;
const MCEXEC_UP_GET_CPU: c_uint = 0x30a0_2907;
const MCEXEC_UP_STRNCPY_FROM_USER: c_uint = 0x30a0_2908;
const MCEXEC_UP_GET_CRED: c_uint = 0x30a0_290a;
const MCEXEC_UP_GET_CREDV: c_uint = 0x30a0_290b;
const MCEXEC_UP_GET_NODES: c_uint = 0x30a0_290c;
const MCEXEC_UP_GET_CPUSET: c_uint = 0x30a0_290d;
const MCEXEC_UP_CREATE_PPD: c_uint = 0x30a0_290e;
const MCEXEC_UP_PREPARE_DMA: c_uint = 0x30a0_2910;
const MCEXEC_UP_FREE_DMA: c_uint = 0x30a0_2911;
const MCEXEC_UP_OPEN_EXEC: c_uint = 0x30a0_2912;
const MCEXEC_UP_CLOSE_EXEC: c_uint = 0x30a0_2913;
const MCEXEC_UP_SYS_MOUNT: c_uint = 0x30a0_2914;
const MCEXEC_UP_SYS_UMOUNT: c_uint = 0x30a0_2915;
const MCEXEC_UP_SYS_UNSHARE: c_uint = 0x30a0_2916;
const MCEXEC_UP_UTI_GET_CTX: c_uint = 0x30a0_2920;
const MCEXEC_UP_UTI_SWITCH_CTX: c_uint = 0x30a0_2921;
const MCEXEC_UP_SIG_THREAD: c_uint = 0x30a0_2922;
const MCEXEC_UP_SYSCALL_THREAD: c_uint = 0x30a0_2924;
const MCEXEC_UP_TERMINATE_THREAD: c_uint = 0x30a0_2925;
const MCEXEC_UP_GET_NUM_POOL_THREADS: c_uint = 0x30a0_2926;
const MCEXEC_UP_UTI_ATTR: c_uint = 0x30a0_2927;
const MCEXEC_UP_RELEASE_USER_SPACE: c_uint = 0x30a0_2928;
const MCEXEC_UP_DEBUG_LOG: c_uint = 0x4000_0000;
const SCD_MSG_DEBUG_LOG: c_int = 0x20;
const SCD_MSG_CPU_RW_REG: c_int = 0x52;
const SCD_MSG_SYSCALL_ONESIDE: c_int = 0x4;
const MCCTRL_OS_CPU_READ_REGISTER: c_int = 0;
const MCCTRL_IKC_INIT_LAST_CHANNEL_PORT: c_int = 502;
const NR_CLOSE: c_ulong = 3;
const NR_MMAP: c_ulong = 9;
const NR_MPROTECT: c_ulong = 10;
const NR_MUNMAP: c_ulong = 11;
const NR_SCHED_SETPARAM: c_ulong = 142;
const NR_EXIT_GROUP: c_ulong = 231;
const NR_MOVE_PAGES: c_ulong = 279;
const NR_COREDUMP: c_ulong = 999;
const SCHED_CHECK_SAME_OWNER_VALUE: c_ulong = 0x01;
const SCHED_CHECK_ROOT_VALUE: c_ulong = 0x02;
const SYSFS_SPECIAL_OPS_MIN: c_long = 1;
const SYSFS_SPECIAL_OPS_MAX: c_long = 1000;
const ETIME: c_int = 62;
const EPERM: c_int = 1;
const EINVAL: c_int = 22;
const EINTR: c_int = 4;
const ENOSPC: c_int = 28;
const ENOENT: c_int = 2;
const ENAMETOOLONG: c_int = 36;
const EFAULT: c_int = 14;
const ENOEXEC: c_int = 8;
const ENOMEM: c_int = 12;
const ENOSYS: c_int = 38;
const EIO: c_int = 5;
const ERESTART: c_int = 85;
const ERESTARTSYS: c_int = 512;
const FUTEX_WAIT: c_int = 0;
const FUTEX_WAKE: c_int = 1;
const FUTEX_REQUEUE: c_int = 3;
const FUTEX_CMP_REQUEUE: c_int = 4;
const FUTEX_WAKE_OP: c_int = 5;
const FUTEX_WAIT_BITSET: c_int = 9;
const FUTEX_WAKE_BITSET: c_int = 10;
const FUTEX_WAIT_REQUEUE_PI: c_int = 11;
const FUTEX_CMD_MASK: c_int = 0x7f;
const FUTEX_PRIVATE_FLAG: c_int = 128;
const FUTEX_CLOCK_REALTIME: c_int = 256;
const FUTEX_OP_SET_VALUE: c_int = 0;
const FUTEX_OP_ADD_VALUE: c_int = 1;
const FUTEX_OP_OR_VALUE: c_int = 2;
const FUTEX_OP_ANDN_VALUE: c_int = 3;
const FUTEX_OP_XOR_VALUE: c_int = 4;
const FUTEX_OP_OPARG_SHIFT_VALUE: c_int = 8;
const FUTEX_OP_CMP_EQ_VALUE: c_int = 0;
const FUTEX_OP_CMP_NE_VALUE: c_int = 1;
const FUTEX_OP_CMP_LT_VALUE: c_int = 2;
const FUTEX_OP_CMP_LE_VALUE: c_int = 3;
const FUTEX_OP_CMP_GT_VALUE: c_int = 4;
const FUTEX_OP_CMP_GE_VALUE: c_int = 5;
const JHASH_GOLDEN_RATIO: u32 = 0x9e37_79b9;
const FUTEX_WAIT_LABEL: &[u8] = b"FUTEX_WAIT\0";
const FUTEX_WAIT_BITSET_LABEL: &[u8] = b"FUTEX_WAIT_BITSET\0";
const FUTEX_WAKE_LABEL: &[u8] = b"FUTEX_WAKE\0";
const FUTEX_WAKE_OP_LABEL: &[u8] = b"FUTEX_WAKE_OP\0";
const FUTEX_WAKE_BITSET_LABEL: &[u8] = b"FUTEX_WAKE_BITSET\0";
const FUTEX_CMP_REQUEUE_LABEL: &[u8] = b"FUTEX_CMP_REQUEUE\0";
const FUTEX_REQUEUE_LABEL: &[u8] = b"FUTEX_REQUEUE (NOT IMPL!)\0";
const FUTEX_UNKNOWN_LABEL: &[u8] = b"unknown\0";
const TOFU_DEV_PREFIX: &[u8] = b"/proc/tofu/dev/";
const TOFU_CQ_PREFIX: &[u8] = b"/proc/tofu/dev/tni";
const DESIRED_USER_END: c_ulong = 0x8000_0000_0000;
const GAP_FOR_MCEXEC: c_ulong = 0x0080_0000_0000;
const PAGE_SHIFT: usize = 12;
const PAGE_SIZE: c_ulong = 1 << PAGE_SHIFT;
const VDSO_MAXPAGES: usize = 2;
const PTE_P: c_ulong = 0x001;
const PAGE_PWT: c_ulong = 1 << 3;
const PAGE_PCD: c_ulong = 1 << 4;
const PTE_PS: c_ulong = 0x080;
const PTE_PHYS_MASK: c_ulong = ((1u64 << 52) - 1) as c_ulong;
const BINPRM_PBUF_SIZE: c_ulong = 1024;
const ELFCLASS64: u8 = 2;
const ET_EXEC: u16 = 2;
const ET_DYN: u16 = 3;
const MCEXEC_WL_NAME: &[u8] = b"MCEXEC_WL";
const MSR_FS_BASE_NAME: &[u8] = b"save_tls_ctx\0";
const GET_TLS_CTX_NAME: &[u8] = b"get_tls_ctx\0";
const VDSO_IMAGE_64_NAME: &[u8] = b"vdso_image_64\0";
const VVAR_PAGE_NAME: &[u8] = b"__vvar_page\0";
const HPET_ADDRESS_NAME: &[u8] = b"hpet_address\0";
const HV_CLOCK_NAME: &[u8] = b"hv_clock\0";
const SYSFS_SNOOPING_OPS_D32_VALUE: usize = 1;
const SYSFS_SNOOPING_OPS_D64_VALUE: usize = 2;
const SYSFS_SNOOPING_OPS_U32_VALUE: usize = 3;
const SYSFS_SNOOPING_OPS_U64_VALUE: usize = 4;
const SYSFS_SNOOPING_OPS_S_VALUE: usize = 5;
const SYSFS_SNOOPING_OPS_PBL_VALUE: usize = 6;
const SYSFS_SNOOPING_OPS_PB_VALUE: usize = 7;
const SYSFS_SNOOPING_OPS_U32K_VALUE: usize = 8;
const SYSFS_NODE_DISTANCE_S_SIZE: usize = 1024;
const SYSFS_ERRNO_MAX: usize = 4095;

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
pub struct McPlistHead {
    prio_list: ListHead,
    node_list: ListHead,
}

#[repr(C)]
pub struct McPlistNode {
    prio: c_int,
    plist: McPlistHead,
}

#[repr(C)]
pub struct McctrlVdso {
    busy: c_long,
    vdso_npages: c_int,
    vvar_is_global: c_char,
    hpet_is_global: c_char,
    pvti_is_global: c_char,
    padding: c_char,
    vdso_physlist: [c_long; VDSO_MAXPAGES],
    vvar_virt: *mut c_void,
    vvar_phys: c_long,
    hpet_virt: *mut c_void,
    hpet_phys: c_long,
    pvti_virt: *mut c_void,
    pvti_phys: c_long,
    vgtod_virt: *mut c_void,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct TransUctx {
    cond: c_int,
    fregsize: c_int,
    rax: c_ulong,
    rbx: c_ulong,
    rcx: c_ulong,
    rdx: c_ulong,
    rsi: c_ulong,
    rdi: c_ulong,
    rbp: c_ulong,
    r8: c_ulong,
    r9: c_ulong,
    r10: c_ulong,
    r11: c_ulong,
    r12: c_ulong,
    r13: c_ulong,
    r14: c_ulong,
    r15: c_ulong,
    rflags: c_ulong,
    rip: c_ulong,
    rsp: c_ulong,
    fs: c_ulong,
}

#[repr(C)]
pub struct McctrlSpinlock {
    head_tail: AtomicU32,
}

#[repr(C, align(64))]
pub struct McctrlMcsRwlock {
    slock: McctrlSpinlock,
}

#[repr(C)]
pub struct McctrlRefcount {
    refs: AtomicI32,
}

#[repr(C)]
pub struct McctrlRbNode {
    parent_color: c_ulong,
    right: *mut McctrlRbNode,
    left: *mut McctrlRbNode,
}

#[repr(C)]
pub struct McctrlRbRoot {
    node: *mut McctrlRbNode,
}

#[repr(C)]
pub struct McctrlRvaToRpaCacheNode {
    node: McctrlRbNode,
    rva: c_ulong,
    rpa: c_ulong,
}

#[repr(C)]
pub struct SysfsmOps {
    show: Option<
        unsafe extern "C" fn(
            ops: *mut SysfsmOps,
            instance: *mut c_void,
            buf: *mut c_void,
            bufsize: usize,
        ) -> isize,
    >,
    store: Option<
        unsafe extern "C" fn(
            ops: *mut SysfsmOps,
            instance: *mut c_void,
            buf: *const c_void,
            bufsize: usize,
        ) -> isize,
    >,
    release: Option<unsafe extern "C" fn(ops: *mut SysfsmOps, instance: *mut c_void)>,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct SysfsHandle {
    handle: c_long,
}

#[repr(C)]
struct SysfsmBitmapParam {
    nbits: c_int,
    padding: c_int,
    ptr: *mut c_void,
}

static mut VDSO_IMAGE_64: *mut c_void = null_mut();
static mut MCCTRL_VVAR_PAGE: *mut c_void = null_mut();
static mut HPET_ADDRESS: *mut c_long = null_mut();
static mut HV_CLOCK: *mut *mut c_void = null_mut();
static mut SYSFS_LOCAL_LONG_VALUE: c_long = 0xf123_4567_89ab_cde0u64 as c_long;
static SYSFS_LOCAL_STRING_VALUE: &[u8] = b"string(local)\0";
static mut SYSFS_CPU_OFFLINE: c_ulong = 0;
static mut SYSFS_A_VALUE: c_int = 35;

#[no_mangle]
pub static mut show_int_ops: SysfsmOps = SysfsmOps {
    show: Some(show_int),
    store: None,
    release: None,
};

const MC_PLIST_PRIO_LIST_OFFSET: usize =
    offset_of!(McPlistNode, plist) + offset_of!(McPlistHead, prio_list);
const MC_PLIST_NODE_LIST_OFFSET: usize =
    offset_of!(McPlistNode, plist) + offset_of!(McPlistHead, node_list);

const _: () = {
    assert!(size_of::<ListHead>() == 16);
    assert!(align_of::<ListHead>() == 8);
    assert!(size_of::<McPlistHead>() == 32);
    assert!(align_of::<McPlistHead>() == 8);
    assert!(offset_of!(McPlistHead, prio_list) == 0);
    assert!(offset_of!(McPlistHead, node_list) == 16);
    assert!(size_of::<McPlistNode>() == 40);
    assert!(align_of::<McPlistNode>() == 8);
    assert!(offset_of!(McPlistNode, prio) == 0);
    assert!(offset_of!(McPlistNode, plist) == 8);
    assert!(size_of::<McctrlVdso>() == 88);
    assert!(offset_of!(McctrlVdso, vdso_physlist) == 16);
    assert!(offset_of!(McctrlVdso, vvar_virt) == 32);
    assert!(offset_of!(McctrlVdso, vgtod_virt) == 80);
    assert!(size_of::<TransUctx>() == 160);
    assert!(offset_of!(TransUctx, rsp) == 144);
    assert!(offset_of!(TransUctx, fs) == 152);
    assert!(size_of::<McctrlSpinlock>() == 4);
    assert!(align_of::<McctrlSpinlock>() == 4);
    assert!(offset_of!(McctrlSpinlock, head_tail) == 0);
    assert!(size_of::<McctrlMcsRwlock>() == 64);
    assert!(align_of::<McctrlMcsRwlock>() == 64);
    assert!(offset_of!(McctrlMcsRwlock, slock) == 0);
    assert!(size_of::<McctrlRefcount>() == 4);
    assert!(align_of::<McctrlRefcount>() == 4);
    assert!(offset_of!(McctrlRefcount, refs) == 0);
};

unsafe extern "C" {
    fn mcctrl_futex_pagefault_disable_bridge();
    fn mcctrl_futex_pagefault_enable_bridge();
    fn mcctrl_futex_get_user_u32_bridge(dest: *mut u32, from: *mut u32) -> c_int;
    fn mcctrl_futex_atomic_access_ok_bridge(uaddr: *mut c_int, size: c_ulong) -> c_int;
    fn mcctrl_futex_atomic_cmpxchg_inatomic_bridge(
        uaddr: *mut c_int,
        oldval: c_int,
        newval: c_int,
    ) -> c_int;
    fn mcctrl_futex_atomic_op_inuser_bridge(
        op: c_int,
        uaddr: *mut c_int,
        oparg: c_int,
        oldval: *mut c_int,
    ) -> c_int;
    fn mcctrl_futex_set_resp_bridge(uti_info: *mut c_void, uti_futex_resp: *mut c_void);
    fn mcctrl_futex_timeout_bridge(
        utime_addr: c_ulong,
        op: c_int,
        flags: c_int,
        timeout: *mut u64,
    ) -> c_int;
    fn mcctrl_futex_dispatch_bridge(
        uaddr: *mut u32,
        op: c_int,
        val: u32,
        timeout: u64,
        uaddr2: *mut u32,
        val2: u32,
        val3: u32,
        fshared: c_int,
        uti_info: *mut c_void,
    ) -> c_int;
    fn mcctrl_preempt_disable_bridge();
    fn mcctrl_preempt_enable_bridge();
    fn mcctrl_arch_kallsyms_lookup_bridge(name: *const c_char) -> *mut c_void;
    fn mcctrl_arch_vdso_size_bridge(image: *mut c_void) -> c_ulong;
    fn mcctrl_arch_vdso_data_bridge(image: *mut c_void) -> *mut u8;
    fn mcctrl_arch_vgtod_virt_bridge() -> *mut c_void;
    fn mcctrl_arch_virt_to_phys_bridge(ptr: *mut c_void) -> c_ulong;
    fn mcctrl_arch_wmb_bridge();
    fn mcctrl_arch_mutex_lock_reserve_bridge(usrdata: *mut c_void) -> c_int;
    fn mcctrl_arch_mutex_unlock_reserve_bridge(usrdata: *mut c_void);
    fn mcctrl_arch_mmap_write_lock_bridge();
    fn mcctrl_arch_mmap_write_unlock_bridge();
    fn mcctrl_arch_first_vma_start_bridge() -> c_ulong;
    fn mcctrl_arch_reserve_user_space_common_bridge(
        usrdata: *mut c_void,
        start: c_ulong,
        end: c_ulong,
    ) -> c_ulong;
    fn mcctrl_arch_is_err_value_bridge(value: c_ulong) -> c_int;
    fn mcctrl_arch_os_to_dev_bridge(os: *mut c_void) -> *mut c_void;
    fn mcctrl_arch_device_map_memory_bridge(
        dev: *mut c_void,
        phys: c_ulong,
        size: c_ulong,
    ) -> c_ulong;
    fn mcctrl_arch_device_map_virtual_bridge(
        dev: *mut c_void,
        phys: c_ulong,
        size: c_ulong,
    ) -> *mut c_void;
    fn mcctrl_arch_device_unmap_virtual_bridge(dev: *mut c_void, virt: *mut c_void, size: c_ulong);
    fn mcctrl_arch_device_unmap_memory_bridge(dev: *mut c_void, phys: c_ulong, size: c_ulong);
    fn mcctrl_arch_get_user_sp_bridge() -> *mut c_void;
    fn mcctrl_arch_set_user_sp_bridge(usp: *mut c_void);
    fn mcctrl_arch_restore_tls_bridge(addr: c_ulong);
    fn mcctrl_arch_copy_from_user_bridge(
        dst: *mut c_void,
        src: *const c_void,
        size: c_ulong,
    ) -> c_int;
    fn mcctrl_arch_read_fs_base_bridge() -> c_ulong;
    fn mcctrl_arch_pr_err_copy_from_user_bridge(func: *const c_char);
    fn mcctrl_binfmt_insert_bridge();
    fn mcctrl_binfmt_unregister_bridge();
    fn mcctrl_binfmt_os_alive_bridge() -> c_int;
    fn mcctrl_binfmt_envc_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_argc_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_inc_argc_bridge(bprm: *mut c_void);
    fn mcctrl_binfmt_p_bridge(bprm: *mut c_void) -> c_ulong;
    fn mcctrl_binfmt_buf_bridge(bprm: *mut c_void) -> *mut u8;
    fn mcctrl_binfmt_alloc_atomic_bridge(size: c_ulong) -> *mut c_void;
    fn mcctrl_binfmt_alloc_kernel_bridge(size: c_ulong) -> *mut c_void;
    fn mcctrl_binfmt_free_bridge(ptr: *mut c_void);
    fn mcctrl_binfmt_pr_alloc_pbuf_bridge();
    fn mcctrl_binfmt_path_bridge(
        bprm: *mut c_void,
        pbuf: *mut c_char,
        size: c_ulong,
    ) -> *const c_char;
    fn mcctrl_binfmt_get_user_arg_page_bridge(
        bprm: *mut c_void,
        page_out: *mut *mut c_void,
    ) -> c_int;
    fn mcctrl_binfmt_kmap_atomic_bridge(page: *mut c_void) -> *mut u8;
    fn mcctrl_binfmt_kunmap_atomic_bridge(addr: *mut c_void);
    fn mcctrl_binfmt_put_page_bridge(page: *mut c_void);
    fn mcctrl_binfmt_open_exec_bridge() -> *mut c_void;
    fn mcctrl_binfmt_ptr_is_err_bridge(ptr: *const c_void) -> c_int;
    fn mcctrl_binfmt_fput_bridge(file: *mut c_void);
    fn mcctrl_binfmt_remove_arg_zero_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_copy_interp_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_copy_mcexec_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_change_interp_bridge(bprm: *mut c_void) -> c_int;
    fn mcctrl_binfmt_dispatch_bridge(bprm: *mut c_void, file: *mut c_void) -> c_int;
}

const MCCTRL_TICKET_INC: u16 = 2;
const MCCTRL_TAIL_INC: u32 = (MCCTRL_TICKET_INC as u32) << 16;

#[inline(always)]
fn mcctrl_ticket_head(value: u32) -> u16 {
    value as u16
}

#[inline(always)]
fn mcctrl_ticket_tail(value: u32) -> u16 {
    (value >> 16) as u16
}

#[inline(always)]
unsafe fn mcctrl_head_atomic(lock: *mut McctrlSpinlock) -> *mut AtomicU16 {
    lock as *mut AtomicU16
}

unsafe fn c_byte(ptr: *const c_char, index: usize) -> u8 {
    *ptr.add(index) as u8
}

unsafe fn starts_with(ptr: *const c_char, prefix: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }

    let mut i = 0usize;
    while i < prefix.len() {
        if c_byte(ptr, i) != *prefix.as_ptr().add(i) {
            return false;
        }
        i += 1;
    }
    true
}

unsafe fn equals_bytes(ptr: *const c_char, bytes: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }

    let mut i = 0usize;
    while i < bytes.len() {
        if c_byte(ptr, i) != *bytes.as_ptr().add(i) {
            return false;
        }
        i += 1;
    }
    c_byte(ptr, i) == 0
}

unsafe fn contains_bytes(ptr: *const c_char, needle: &[u8]) -> bool {
    if ptr.is_null() {
        return false;
    }
    if needle.is_empty() {
        return true;
    }

    let mut i = 0usize;
    while c_byte(ptr, i) != 0 {
        let mut j = 0usize;
        while j < needle.len() && c_byte(ptr, i + j) != 0 {
            if c_byte(ptr, i + j) != *needle.as_ptr().add(j) {
                break;
            }
            j += 1;
        }
        if j == needle.len() {
            return true;
        }
        i += 1;
    }
    false
}

fn is_ascii_space(byte: u8) -> bool {
    matches!(byte, b' ' | b'\t' | b'\n' | b'\r' | 0x0b | 0x0c)
}

unsafe fn parse_i32_at(ptr: *const c_char, pos: &mut usize, out: *mut c_int) -> bool {
    if out.is_null() {
        return false;
    }

    let mut value = 0 as c_int;
    let mut digits = 0usize;
    while c_byte(ptr, *pos).is_ascii_digit() {
        value = value
            .wrapping_mul(10)
            .wrapping_add((c_byte(ptr, *pos) - b'0') as c_int);
        *pos += 1;
        digits += 1;
    }

    if digits == 0 {
        return false;
    }

    *out = value;
    true
}

unsafe fn llist_pop_first(head_addr: usize) -> usize {
    let head = &*(head_addr as *const AtomicUsize);
    let mut entry = head.load(Ordering::Acquire);

    loop {
        if entry == 0 {
            return 0;
        }

        let next = core::ptr::read_volatile(entry as *const usize);
        match head.compare_exchange(entry, next, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) => return entry,
            Err(current) => entry = current,
        }
    }
}

unsafe fn llist_add_first(head_addr: usize, node_addr: usize) {
    let head = &*(head_addr as *const AtomicUsize);
    let next_ptr = node_addr as *mut usize;
    let mut first = head.load(Ordering::Acquire);

    loop {
        core::ptr::write_volatile(next_ptr, first);
        match head.compare_exchange(first, node_addr, Ordering::AcqRel, Ordering::Acquire) {
            Ok(_) => return,
            Err(current) => first = current,
        }
    }
}

#[inline(always)]
unsafe fn mc_plist_from_prio(list: *mut ListHead) -> *mut McPlistNode {
    list.cast::<u8>()
        .sub(MC_PLIST_PRIO_LIST_OFFSET)
        .cast::<McPlistNode>()
}

#[inline(always)]
unsafe fn mc_plist_from_node(list: *mut ListHead) -> *mut McPlistNode {
    list.cast::<u8>()
        .sub(MC_PLIST_NODE_LIST_OFFSET)
        .cast::<McPlistNode>()
}

#[inline(always)]
unsafe fn mc_plist_prio_link(node: *mut McPlistNode) -> *mut ListHead {
    &raw mut (*node).plist.prio_list
}

#[inline(always)]
unsafe fn mc_plist_node_link(node: *mut McPlistNode) -> *mut ListHead {
    &raw mut (*node).plist.node_list
}

#[inline(always)]
unsafe fn list_head_init(list: *mut ListHead) {
    write_volatile(&mut (*list).next, list);
    write_volatile(&mut (*list).prev, list);
}

#[inline(always)]
unsafe fn list_is_empty(list: *mut ListHead) -> bool {
    read_volatile(&(*list).next) == list
}

#[inline(always)]
unsafe fn list_add_tail_link(new: *mut ListHead, head: *mut ListHead) {
    let prev = read_volatile(&(*head).prev);

    write_volatile(&mut (*head).prev, new);
    write_volatile(&mut (*new).next, head);
    write_volatile(&mut (*new).prev, prev);
    write_volatile(&mut (*prev).next, new);
}

#[inline(always)]
unsafe fn list_del_link(prev: *mut ListHead, next: *mut ListHead) {
    write_volatile(&mut (*next).prev, prev);
    write_volatile(&mut (*prev).next, next);
}

#[inline(always)]
unsafe fn list_del_init_link(entry: *mut ListHead) {
    list_del_link(read_volatile(&(*entry).prev), read_volatile(&(*entry).next));
    list_head_init(entry);
}

#[inline(always)]
unsafe fn list_move_tail_link(entry: *mut ListHead, head: *mut ListHead) {
    list_del_link(read_volatile(&(*entry).prev), read_volatile(&(*entry).next));
    list_add_tail_link(entry, head);
}

#[inline(always)]
fn align_down(value: c_ulong, align: c_ulong) -> c_ulong {
    value & !(align - 1)
}

#[no_mangle]
pub unsafe extern "C" fn arch_symbols_init() -> c_int {
    VDSO_IMAGE_64 = mcctrl_arch_kallsyms_lookup_bridge(VDSO_IMAGE_64_NAME.as_ptr().cast());
    if VDSO_IMAGE_64.is_null() {
        return -EFAULT;
    }

    MCCTRL_VVAR_PAGE = mcctrl_arch_kallsyms_lookup_bridge(VVAR_PAGE_NAME.as_ptr().cast());
    if MCCTRL_VVAR_PAGE.is_null() {
        return -EFAULT;
    }

    HPET_ADDRESS = mcctrl_arch_kallsyms_lookup_bridge(HPET_ADDRESS_NAME.as_ptr().cast()).cast();
    HV_CLOCK = mcctrl_arch_kallsyms_lookup_bridge(HV_CLOCK_NAME.as_ptr().cast()).cast();
    0
}

#[no_mangle]
pub unsafe extern "C" fn reserve_user_space(
    usrdata: *mut c_void,
    startp: *mut c_ulong,
    endp: *mut c_ulong,
) -> c_int {
    if mcctrl_arch_mutex_lock_reserve_bridge(usrdata) < 0 {
        return -1;
    }

    let mut end = DESIRED_USER_END;
    mcctrl_arch_mmap_write_lock_bridge();
    let first_vma_start = mcctrl_arch_first_vma_start_bridge();
    if first_vma_start != 0 {
        end = align_down(first_vma_start.wrapping_sub(GAP_FOR_MCEXEC), GAP_FOR_MCEXEC);
    }
    mcctrl_arch_mmap_write_unlock_bridge();

    let start = mcctrl_arch_reserve_user_space_common_bridge(usrdata, 0, end);
    mcctrl_arch_mutex_unlock_reserve_bridge(usrdata);

    if mcctrl_arch_is_err_value_bridge(start) != 0 {
        return start as c_int;
    }
    if !startp.is_null() {
        *startp = start;
    }
    if !endp.is_null() {
        *endp = end;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn get_vdso_info(os: *mut c_void, vdso_rpa: c_long) {
    let dev = mcctrl_arch_os_to_dev_bridge(os);
    let vdso_size = size_of::<McctrlVdso>() as c_ulong;
    let vdso_pa = mcctrl_arch_device_map_memory_bridge(dev, vdso_rpa as c_ulong, vdso_size);
    let vdso = mcctrl_arch_device_map_virtual_bridge(dev, vdso_pa, vdso_size).cast::<McctrlVdso>();

    let size = mcctrl_arch_vdso_size_bridge(VDSO_IMAGE_64);
    (*vdso).vdso_npages = (size >> PAGE_SHIFT) as c_int;
    if (*vdso).vdso_npages as usize > VDSO_MAXPAGES {
        (*vdso).vdso_npages = 0;
        mcctrl_arch_wmb_bridge();
        (*vdso).busy = 0;
        mcctrl_arch_device_unmap_virtual_bridge(dev, vdso.cast(), vdso_size);
        mcctrl_arch_device_unmap_memory_bridge(dev, vdso_pa, vdso_size);
        return;
    }

    let data = mcctrl_arch_vdso_data_bridge(VDSO_IMAGE_64);
    let physlist = (&raw mut (*vdso).vdso_physlist).cast::<c_long>();
    let mut i = 0usize;
    while i < (*vdso).vdso_npages as usize {
        write_volatile(
            physlist.add(i),
            mcctrl_arch_virt_to_phys_bridge(data.add(i * PAGE_SIZE as usize).cast()) as c_long,
        );
        i += 1;
    }

    (*vdso).vvar_is_global = 0;
    (*vdso).vvar_virt = (-(3 * PAGE_SIZE as isize)) as *mut c_void;
    (*vdso).vvar_phys = mcctrl_arch_virt_to_phys_bridge(MCCTRL_VVAR_PAGE) as c_long;

    if !HPET_ADDRESS.is_null() && *HPET_ADDRESS != 0 {
        (*vdso).hpet_is_global = 0;
        (*vdso).hpet_virt = (-(2 * PAGE_SIZE as isize)) as *mut c_void;
        (*vdso).hpet_phys = *HPET_ADDRESS;
    }

    if !HV_CLOCK.is_null() && !(*HV_CLOCK).is_null() {
        (*vdso).pvti_is_global = 0;
        (*vdso).pvti_virt = (-(PAGE_SIZE as isize)) as *mut c_void;
        (*vdso).pvti_phys = mcctrl_arch_virt_to_phys_bridge(*HV_CLOCK) as c_long;
    }

    (*vdso).vgtod_virt = mcctrl_arch_vgtod_virt_bridge();
    mcctrl_arch_wmb_bridge();
    (*vdso).busy = 0;

    mcctrl_arch_device_unmap_virtual_bridge(dev, vdso.cast(), vdso_size);
    mcctrl_arch_device_unmap_memory_bridge(dev, vdso_pa, vdso_size);
}

#[no_mangle]
pub unsafe extern "C" fn get_user_sp() -> *mut c_void {
    mcctrl_arch_get_user_sp_bridge()
}

#[no_mangle]
pub unsafe extern "C" fn set_user_sp(usp: *mut c_void) {
    mcctrl_arch_set_user_sp_bridge(usp);
}

#[no_mangle]
pub unsafe extern "C" fn restore_tls(addr: c_ulong) {
    mcctrl_arch_restore_tls_bridge(addr);
}

#[no_mangle]
pub unsafe extern "C" fn save_tls_ctx(ctx: *const c_void) {
    let mut kctx = MaybeUninit::<TransUctx>::uninit();

    if mcctrl_arch_copy_from_user_bridge(
        kctx.as_mut_ptr().cast(),
        ctx,
        size_of::<TransUctx>() as c_ulong,
    ) != 0
    {
        mcctrl_arch_pr_err_copy_from_user_bridge(MSR_FS_BASE_NAME.as_ptr().cast());
        return;
    }
    let mut kctx = kctx.assume_init();
    kctx.fs = mcctrl_arch_read_fs_base_bridge();
    let _ = kctx;
}

#[no_mangle]
pub unsafe extern "C" fn get_tls_ctx(ctx: *const c_void) -> c_ulong {
    let mut kctx = MaybeUninit::<TransUctx>::uninit();

    if mcctrl_arch_copy_from_user_bridge(
        kctx.as_mut_ptr().cast(),
        ctx,
        size_of::<TransUctx>() as c_ulong,
    ) != 0
    {
        mcctrl_arch_pr_err_copy_from_user_bridge(GET_TLS_CTX_NAME.as_ptr().cast());
        return 0;
    }
    let kctx = kctx.assume_init();
    kctx.fs
}

#[no_mangle]
pub unsafe extern "C" fn get_rsp_ctx(ctx: *mut c_void) -> c_ulong {
    (*ctx.cast::<TransUctx>()).rsp
}

#[no_mangle]
pub unsafe extern "C" fn translate_rva_to_rpa(
    os: *mut c_void,
    rpt: c_ulong,
    rva: c_ulong,
    rpap: *mut c_ulong,
    pgsizep: *mut c_ulong,
) -> c_int {
    let dev = mcctrl_arch_os_to_dev_bridge(os);
    let mut rpa = rpt;
    let mut offsh = 39usize;
    let mut i = 0usize;

    while i < 4 {
        let ix = ((rva >> offsh) & 0x1ff) as usize;
        let phys = mcctrl_arch_device_map_memory_bridge(dev, rpa, PAGE_SIZE);
        let pt = mcctrl_arch_device_map_virtual_bridge(dev, phys, PAGE_SIZE).cast::<c_ulong>();
        let pte = read_volatile(pt.add(ix));

        if pte & PTE_P == 0 {
            mcctrl_arch_device_unmap_virtual_bridge(dev, pt.cast(), PAGE_SIZE);
            mcctrl_arch_device_unmap_memory_bridge(dev, phys, PAGE_SIZE);
            return -EFAULT;
        }

        if pte & PTE_PS != 0 {
            let mut pgsize = 1u64.wrapping_shl(offsh as u32) as c_ulong;
            rpa = (pte & PTE_PHYS_MASK & !(pgsize - 1)) | (rva & (pgsize - 1));
            if offsh == 30 {
                pgsize = 1 << 21;
            }
            mcctrl_arch_device_unmap_virtual_bridge(dev, pt.cast(), PAGE_SIZE);
            mcctrl_arch_device_unmap_memory_bridge(dev, phys, PAGE_SIZE);
            if !rpap.is_null() {
                *rpap = rpa;
            }
            if !pgsizep.is_null() {
                *pgsizep = pgsize;
            }
            return 0;
        }

        rpa = pte & PTE_PHYS_MASK & !((1 << PAGE_SHIFT) - 1);
        offsh -= 9;
        mcctrl_arch_device_unmap_virtual_bridge(dev, pt.cast(), PAGE_SIZE);
        mcctrl_arch_device_unmap_memory_bridge(dev, phys, PAGE_SIZE);
        i += 1;
    }

    let pgsize = 1 << PAGE_SHIFT;
    rpa |= rva & (pgsize - 1);
    if !rpap.is_null() {
        *rpap = rpa;
    }
    if !pgsizep.is_null() {
        *pgsizep = pgsize;
    }
    0
}

#[no_mangle]
pub extern "C" fn arch_switch_ctx(_desc: *mut c_void) -> c_long {
    0
}

#[no_mangle]
pub unsafe extern "C" fn binfmt_mcexec_init() {
    mcctrl_binfmt_insert_bridge();
}

#[no_mangle]
pub unsafe extern "C" fn binfmt_mcexec_exit() {
    mcctrl_binfmt_unregister_bridge();
}

unsafe fn binfmt_is_elf64_exec(buf: *const u8) -> bool {
    if buf.is_null() {
        return false;
    }

    if read_volatile(buf) != 0x7f
        || read_volatile(buf.add(1)) != b'E'
        || read_volatile(buf.add(2)) != b'L'
        || read_volatile(buf.add(3)) != b'F'
    {
        return false;
    }

    let e_type = (read_volatile(buf.add(16)) as u16) | ((read_volatile(buf.add(17)) as u16) << 8);
    (e_type == ET_EXEC || e_type == ET_DYN) && read_volatile(buf.add(4)) == ELFCLASS64
}

unsafe fn binfmt_free_if_present(ptr: *mut c_void) {
    if !ptr.is_null() {
        mcctrl_binfmt_free_bridge(ptr);
    }
}

#[no_mangle]
pub unsafe extern "C" fn load_elf(bprm: *mut c_void) -> c_int {
    if mcctrl_binfmt_os_alive_bridge() == -1 {
        return -ENOEXEC;
    }

    let envc = mcctrl_binfmt_envc_bridge(bprm);
    if envc == 0 {
        return -ENOEXEC;
    }

    if !binfmt_is_elf64_exec(mcctrl_binfmt_buf_bridge(bprm).cast_const()) {
        return -ENOEXEC;
    }

    let pbuf = mcctrl_binfmt_alloc_atomic_bridge(BINPRM_PBUF_SIZE).cast::<c_char>();
    if pbuf.is_null() {
        mcctrl_binfmt_pr_alloc_pbuf_bridge();
        return -ENOMEM;
    }

    let path = mcctrl_binfmt_path_bridge(bprm, pbuf, BINPRM_PBUF_SIZE);
    if mcctrl_binfmt_skip_path_result(path) != 0 {
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return -ENOEXEC;
    }

    let argc = mcctrl_binfmt_argc_bridge(bprm);
    let mut env_mcexec_wl: *mut c_char = null_mut();
    let mut env_mcexec_wl_len = 0usize;
    let mut pass = 0;

    while pass < 2 {
        if pass == 1 && env_mcexec_wl_len != 0 {
            env_mcexec_wl = mcctrl_binfmt_alloc_kernel_bridge(env_mcexec_wl_len as c_ulong).cast();
            if env_mcexec_wl.is_null() {
                mcctrl_binfmt_free_bridge(pbuf.cast());
                return -ENOMEM;
            }
        }

        let mut p = mcctrl_binfmt_p_bridge(bprm);
        let mut mode: c_int = if argc == 0 { 1 } else { 0 };
        let mut i: c_int = 0;
        let mut mapped = false;
        let mut page: *mut c_void = null_mut();
        let mut addr: *mut u8 = null_mut();
        let mut off = 0usize;
        let mut capture_value = false;
        let mut name_len = 0usize;
        let mut name_match = true;
        let mut value_len = 0usize;

        while mode != 2 {
            if !mapped {
                off = (p & (PAGE_SIZE - 1)) as usize;
                if mcctrl_binfmt_get_user_arg_page_bridge(bprm, &raw mut page) <= 0 {
                    binfmt_free_if_present(env_mcexec_wl.cast());
                    mcctrl_binfmt_free_bridge(pbuf.cast());
                    return -EFAULT;
                }
                addr = mcctrl_binfmt_kmap_atomic_bridge(page);
                mapped = true;
            }

            let byte = read_volatile(addr.add(off));
            if byte != 0 {
                if mode == 1 {
                    if capture_value {
                        if pass == 1 && !env_mcexec_wl.is_null() {
                            write_volatile(env_mcexec_wl.add(value_len), byte as c_char);
                        }
                        value_len += 1;
                    } else if byte == b'=' {
                        if !(name_match && name_len == MCEXEC_WL_NAME.len()) {
                            capture_value = false;
                        } else {
                            capture_value = true;
                            value_len = 0;
                        }
                    } else {
                        if name_len >= MCEXEC_WL_NAME.len()
                            || byte != *MCEXEC_WL_NAME.as_ptr().add(name_len)
                        {
                            name_match = false;
                        }
                        name_len += 1;
                    }
                }
            } else {
                if mode == 1 && capture_value {
                    if pass == 0 {
                        env_mcexec_wl_len = value_len + 1;
                    } else if !env_mcexec_wl.is_null() {
                        write_volatile(env_mcexec_wl.add(value_len), NUL);
                    }
                }

                capture_value = false;
                name_len = 0;
                name_match = true;
                value_len = 0;
                i += 1;
                let count = if mode == 0 { argc } else { envc };
                if i == count {
                    i = 0;
                    mode += 1;
                }
            }

            off += 1;
            p = p.wrapping_add(1);
            if off == PAGE_SIZE as usize || mode == 2 {
                mcctrl_binfmt_kunmap_atomic_bridge(addr.cast());
                mcctrl_binfmt_put_page_bridge(page);
                mapped = false;
            }
        }

        pass += 1;
    }

    let reject = if !env_mcexec_wl.is_null() {
        (mcctrl_path_allowed_result(path, env_mcexec_wl.cast_const()) == 0) as c_int
    } else {
        1
    };

    binfmt_free_if_present(env_mcexec_wl.cast());
    if reject != 0 {
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return -ENOEXEC;
    }

    let file = mcctrl_binfmt_open_exec_bridge();
    if mcctrl_binfmt_ptr_is_err_bridge(file.cast_const()) != 0 {
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return -ENOEXEC;
    }

    let mut rc = mcctrl_binfmt_remove_arg_zero_bridge(bprm);
    if rc != 0 {
        mcctrl_binfmt_fput_bridge(file);
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return rc;
    }

    rc = mcctrl_binfmt_copy_interp_bridge(bprm);
    if rc < 0 {
        mcctrl_binfmt_fput_bridge(file);
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return rc;
    }
    mcctrl_binfmt_inc_argc_bridge(bprm);

    rc = mcctrl_binfmt_copy_mcexec_bridge(bprm);
    if rc != 0 {
        mcctrl_binfmt_fput_bridge(file);
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return rc;
    }
    mcctrl_binfmt_inc_argc_bridge(bprm);

    rc = mcctrl_binfmt_change_interp_bridge(bprm);
    if rc < 0 {
        mcctrl_binfmt_fput_bridge(file);
        mcctrl_binfmt_free_bridge(pbuf.cast());
        return rc;
    }

    mcctrl_binfmt_free_bridge(pbuf.cast());
    mcctrl_binfmt_dispatch_bridge(bprm, file)
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_head_init(head: *mut McPlistHead, _lock: *mut c_void) {
    list_head_init(&raw mut (*head).prio_list);
    list_head_init(&raw mut (*head).node_list);
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_head_init_raw(head: *mut McPlistHead, lock: *mut c_void) {
    mc_plist_head_init(head, lock);
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_node_init(node: *mut McPlistNode, prio: c_int) {
    (*node).prio = prio;
    mc_plist_head_init(&raw mut (*node).plist, null_mut());
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_head_empty(head: *const McPlistHead) -> c_int {
    list_is_empty(&raw mut (*(head as *mut McPlistHead)).node_list) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_node_empty(node: *const McPlistNode) -> c_int {
    mc_plist_head_empty(&raw const (*node).plist)
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_first(head: *const McPlistHead) -> *mut McPlistNode {
    mc_plist_from_node(read_volatile(&(*head).node_list.next))
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_add(node: *mut McPlistNode, head: *mut McPlistHead) {
    let head_prio = &raw mut (*head).prio_list;
    let head_node = &raw mut (*head).node_list;
    let mut cursor = read_volatile(&(*head_prio).next);

    while cursor != head_prio {
        let iter = mc_plist_from_prio(cursor);

        if (*node).prio < (*iter).prio {
            list_add_tail_link(mc_plist_prio_link(node), mc_plist_prio_link(iter));
            list_add_tail_link(mc_plist_node_link(node), mc_plist_node_link(iter));
            return;
        }

        if (*node).prio == (*iter).prio {
            let next_prio = read_volatile(&(*mc_plist_prio_link(iter)).next);
            let next_node = if next_prio == head_prio {
                head_node
            } else {
                mc_plist_node_link(mc_plist_from_prio(next_prio))
            };

            list_add_tail_link(mc_plist_node_link(node), next_node);
            return;
        }

        cursor = read_volatile(&(*cursor).next);
    }

    list_add_tail_link(mc_plist_prio_link(node), head_prio);
    list_add_tail_link(mc_plist_node_link(node), head_node);
}

#[no_mangle]
pub unsafe extern "C" fn mc_plist_del(node: *mut McPlistNode, _head: *mut McPlistHead) {
    if !list_is_empty(mc_plist_prio_link(node)) {
        let next = mc_plist_first(&raw const (*node).plist);

        list_move_tail_link(mc_plist_prio_link(next), mc_plist_prio_link(node));
        list_del_init_link(mc_plist_prio_link(node));
    }

    list_del_init_link(mc_plist_node_link(node));
}

#[no_mangle]
pub unsafe extern "C" fn refcount_set(r: *mut McctrlRefcount, n: c_uint) {
    (*r).refs.store(n as i32, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn refcount_read(r: *const McctrlRefcount) -> c_uint {
    (*r).refs.load(Ordering::SeqCst) as c_uint
}

#[no_mangle]
pub unsafe extern "C" fn refcount_add_not_zero(i: c_uint, r: *mut McctrlRefcount) -> bool {
    let refs = &(*r).refs;
    let delta = i as i32;
    let mut current = refs.load(Ordering::SeqCst);

    loop {
        if current == 0 {
            return false;
        }

        match refs.compare_exchange(
            current,
            current.wrapping_add(delta),
            Ordering::SeqCst,
            Ordering::SeqCst,
        ) {
            Ok(_) => return true,
            Err(observed) => current = observed,
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn refcount_add(i: c_uint, r: *mut McctrlRefcount) {
    let _ = (*r).refs.fetch_add(i as i32, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn refcount_inc_not_zero(r: *mut McctrlRefcount) -> bool {
    refcount_add_not_zero(1, r)
}

#[no_mangle]
pub unsafe extern "C" fn refcount_inc(r: *mut McctrlRefcount) {
    let _ = (*r).refs.fetch_add(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn refcount_sub_and_test(i: c_uint, r: *mut McctrlRefcount) -> bool {
    let old = (*r).refs.fetch_sub(i as i32, Ordering::SeqCst);
    old.wrapping_sub(i as i32) == 0
}

#[no_mangle]
pub unsafe extern "C" fn refcount_dec_and_test(r: *mut McctrlRefcount) -> bool {
    let old = (*r).refs.fetch_sub(1, Ordering::SeqCst);
    old.wrapping_sub(1) == 0
}

#[no_mangle]
pub unsafe extern "C" fn refcount_dec(r: *mut McctrlRefcount) {
    let _ = (*r).refs.fetch_sub(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn get_futex_value_locked(dest: *mut u32, from: *mut u32) -> c_int {
    mcctrl_futex_pagefault_disable_bridge();
    let ret = mcctrl_futex_get_user_u32_bridge(dest, from);
    mcctrl_futex_pagefault_enable_bridge();

    if ret != 0 {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_atomic_cmpxchg_inatomic(
    uaddr: *mut c_int,
    oldval: c_int,
    newval: c_int,
) -> c_int {
    if mcctrl_futex_atomic_access_ok_bridge(uaddr, size_of::<c_int>() as c_ulong) == 0 {
        return -EFAULT;
    }

    mcctrl_futex_atomic_cmpxchg_inatomic_bridge(uaddr, oldval, newval)
}

#[no_mangle]
pub unsafe extern "C" fn futex_atomic_op_inuser(encoded_op: c_int, uaddr: *mut c_int) -> c_int {
    let op = (encoded_op >> 28) & 7;
    let cmp = (encoded_op >> 24) & 15;
    let mut oparg = (encoded_op & 0x00fff000) >> 12;
    let cmparg = encoded_op & 0x0fff;
    let mut oldval = 0;

    if (encoded_op & (FUTEX_OP_OPARG_SHIFT_VALUE << 28)) != 0 {
        oparg = (1 as c_int).wrapping_shl(oparg as u32);
    }

    if mcctrl_futex_atomic_access_ok_bridge(uaddr, size_of::<c_int>() as c_ulong) == 0 {
        return -EFAULT;
    }

    let primitive_arg = match op {
        FUTEX_OP_SET_VALUE | FUTEX_OP_ADD_VALUE | FUTEX_OP_OR_VALUE | FUTEX_OP_XOR_VALUE => oparg,
        FUTEX_OP_ANDN_VALUE => !oparg,
        _ => return -ENOSYS,
    };

    let ret = mcctrl_futex_atomic_op_inuser_bridge(op, uaddr, primitive_arg, &mut oldval);
    if ret != 0 {
        return ret;
    }

    match cmp {
        FUTEX_OP_CMP_EQ_VALUE => (oldval == cmparg) as c_int,
        FUTEX_OP_CMP_NE_VALUE => (oldval != cmparg) as c_int,
        FUTEX_OP_CMP_LT_VALUE => (oldval < cmparg) as c_int,
        FUTEX_OP_CMP_GE_VALUE => (oldval >= cmparg) as c_int,
        FUTEX_OP_CMP_LE_VALUE => (oldval <= cmparg) as c_int,
        FUTEX_OP_CMP_GT_VALUE => (oldval > cmparg) as c_int,
        _ => -ENOSYS,
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_futex(
    n: c_int,
    arg0: c_ulong,
    arg1: c_ulong,
    arg2: c_ulong,
    arg3: c_ulong,
    arg4: c_ulong,
    arg5: c_ulong,
    uti_info: *mut c_void,
    uti_futex_resp: *mut c_void,
) -> c_long {
    let _ = n;
    let uaddr = arg0 as *mut u32;
    let mut op = arg1 as c_int;
    let val = arg2 as u32;
    let utime = arg3;
    let uaddr2 = arg4 as *mut u32;
    let val3 = arg5 as u32;
    let flags = op;
    let mut timeout = 0u64;
    let mut val2 = 0u32;
    let mut fshared = 1;

    mcctrl_futex_set_resp_bridge(uti_info, uti_futex_resp);

    if mcctrl_futex_is_private_result(op) != 0 {
        fshared = 0;
    }
    op = mcctrl_futex_cmd_result(op);

    if utime != 0 && mcctrl_futex_wait_uses_timeout_result(op) != 0 {
        let ret = mcctrl_futex_timeout_bridge(utime, op, flags, &mut timeout);
        if ret != 0 {
            return ret as c_long;
        }
    }

    if mcctrl_futex_arg3_is_val2_result(op) != 0 {
        val2 = arg3 as u32;
    }

    mcctrl_futex_dispatch_bridge(
        uaddr, op, val, timeout, uaddr2, val2, val3, fshared, uti_info,
    ) as c_long
}

#[inline(always)]
fn mc_jhash_mix(a: &mut u32, b: &mut u32, c: &mut u32) {
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 13;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(8);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 13;
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 12;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(16);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 5;
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 3;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(10);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 15;
}

#[no_mangle]
pub unsafe extern "C" fn mc_jhash2(k: *const u32, length: u32, initval: u32) -> u32 {
    let mut a = JHASH_GOLDEN_RATIO;
    let mut b = JHASH_GOLDEN_RATIO;
    let mut c = initval;
    let mut len = length;
    let mut p = k;

    while len >= 3 {
        a = a.wrapping_add(read_volatile(p));
        b = b.wrapping_add(read_volatile(p.add(1)));
        c = c.wrapping_add(read_volatile(p.add(2)));
        mc_jhash_mix(&mut a, &mut b, &mut c);
        p = p.add(3);
        len -= 3;
    }

    c = c.wrapping_add(length.wrapping_mul(4));
    if len >= 2 {
        b = b.wrapping_add(read_volatile(p.add(1)));
    }
    if len >= 1 {
        a = a.wrapping_add(read_volatile(p));
    }

    mc_jhash_mix(&mut a, &mut b, &mut c);
    c
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_spinlock_init(lock: *mut McctrlSpinlock) {
    (*lock).head_tail.store(0, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_lock_noirq(lock: *mut McctrlSpinlock) {
    mcctrl_preempt_disable_bridge();
    let ticket = (*lock)
        .head_tail
        .fetch_add(MCCTRL_TAIL_INC, Ordering::SeqCst);
    let wait_for = mcctrl_ticket_tail(ticket);

    if mcctrl_ticket_head(ticket) == wait_for {
        compiler_fence(Ordering::SeqCst);
        return;
    }

    loop {
        if mcctrl_ticket_head((*lock).head_tail.load(Ordering::Acquire)) == wait_for {
            compiler_fence(Ordering::SeqCst);
            return;
        }
        cpu_pause();
    }
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock_noirq(lock: *mut McctrlSpinlock) {
    let _ = (*mcctrl_head_atomic(lock)).fetch_add(MCCTRL_TICKET_INC, Ordering::SeqCst);
    mcctrl_preempt_enable_bridge();
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_lock(lock: *mut McctrlSpinlock) -> c_ulong {
    let flags = cpu_disable_interrupt_save();

    __ihk_mc_spinlock_lock_noirq(lock);
    flags
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_mc_spinlock_unlock(lock: *mut McctrlSpinlock, flags: c_ulong) {
    __ihk_mc_spinlock_unlock_noirq(lock);

    cpu_restore_interrupt(flags);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_rwlock_writer_lock_noirq(lock: *mut McctrlMcsRwlock) {
    __ihk_mc_spinlock_lock_noirq(&raw mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn mcs_rwlock_writer_unlock_noirq(lock: *mut McctrlMcsRwlock) {
    __ihk_mc_spinlock_unlock_noirq(&raw mut (*lock).slock);
}

#[no_mangle]
pub unsafe extern "C" fn cpu_restore_interrupt(flags: c_ulong) {
    core::arch::asm!(
        "push {flags}",
        "popfq",
        flags = in(reg) flags,
    );
}

#[no_mangle]
pub unsafe extern "C" fn cpu_pause() {
    core::arch::asm!("pause", options(nomem, nostack, preserves_flags));
}

#[no_mangle]
pub unsafe extern "C" fn cpu_disable_interrupt_save() -> c_ulong {
    let flags: c_ulong;

    core::arch::asm!(
        "pushfq",
        "pop {flags}",
        "cli",
        flags = out(reg) flags,
    );

    flags
}

#[no_mangle]
pub unsafe extern "C" fn cpu_enable_interrupt_save() -> c_ulong {
    let flags: c_ulong;

    core::arch::asm!(
        "pushfq",
        "pop {flags}",
        "sti",
        flags = out(reg) flags,
    );

    flags
}

unsafe fn atomic_i32_at(obj_addr: usize, offset: usize) -> &'static AtomicI32 {
    &*((obj_addr.wrapping_add(offset)) as *const AtomicI32)
}

#[no_mangle]
pub extern "C" fn mcctrl_align_wait_buf_result(size: usize) -> usize {
    size.wrapping_add(63) & !63usize
}

#[no_mangle]
pub extern "C" fn mcctrl_align_wait_buf(size: usize) -> usize {
    mcctrl_align_wait_buf_result(size)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_list_evict_result(len: c_int, max_len: c_int) -> c_int {
    (len >= max_len) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_list_evict(len: c_int, max_len: c_int) -> c_int {
    mcctrl_partition_list_evict_result(len, max_len)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_count_mismatch_result(
    existing: c_int,
    requested: c_int,
) -> c_int {
    (existing != requested) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_count_mismatch(existing: c_int, requested: c_int) -> c_int {
    mcctrl_partition_count_mismatch_result(existing, requested)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_join_allowed_result(joined: c_int, total: c_int) -> c_int {
    (joined < total) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_join_allowed(joined: c_int, total: c_int) -> c_int {
    mcctrl_partition_join_allowed_result(joined, total)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_last_process_result(left: c_int) -> c_int {
    (left == 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_last_process(left: c_int) -> c_int {
    mcctrl_partition_last_process_result(left)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_required_result(
    left: c_int,
    woke_any: c_int,
    woke_self: c_int,
) -> c_int {
    (left != 0 || (woke_any != 0 && woke_self == 0)) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_required(
    left: c_int,
    woke_any: c_int,
    woke_self: c_int,
) -> c_int {
    mcctrl_partition_wait_required_result(left, woke_any, woke_self)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_timeout_msecs_result(nr_processes: c_int) -> c_uint {
    10_000u32.wrapping_add((nr_processes as u32).wrapping_mul(100))
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wait_timeout_msecs(nr_processes: c_int) -> c_uint {
    mcctrl_partition_wait_timeout_msecs_result(nr_processes)
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wake_next_result(left: c_int) -> c_int {
    (left != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_partition_wake_next(left: c_int) -> c_int {
    mcctrl_partition_wake_next_result(left)
}

#[no_mangle]
pub extern "C" fn mcctrl_release_user_space_len_result(start: c_ulong, end: c_ulong) -> c_ulong {
    end.wrapping_sub(start)
}

#[no_mangle]
pub extern "C" fn mcctrl_release_user_space_len(start: c_ulong, end: c_ulong) -> c_ulong {
    mcctrl_release_user_space_len_result(start, end)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_zero_mckernel_pages_step_result(
    node_addr: c_ulong,
    to_zero_list_offset: c_ulong,
    zeroed_list_offset: c_ulong,
    nr_to_zero_pages_offset: c_ulong,
    free_chunk_addr_offset: c_ulong,
    free_chunk_size_offset: c_ulong,
    free_chunk_list_offset: c_ulong,
    free_chunk_sizeof: c_ulong,
    phys_to_virt_base: c_ulong,
    page_shift: c_uint,
    addr_out: *mut c_ulong,
    size_out: *mut c_ulong,
) -> c_int {
    if node_addr == 0 {
        return 0;
    }

    let llnode = llist_pop_first(node_addr.wrapping_add(to_zero_list_offset) as usize);
    if llnode == 0 {
        return 0;
    }

    let chunk = llnode.wrapping_sub(free_chunk_list_offset as usize);
    let addr = core::ptr::read_volatile(
        chunk.wrapping_add(free_chunk_addr_offset as usize) as *const c_ulong
    );
    let size = core::ptr::read_volatile(
        chunk.wrapping_add(free_chunk_size_offset as usize) as *const c_ulong
    );
    let zero_len = (size as usize).saturating_sub(free_chunk_sizeof as usize);

    if zero_len != 0 {
        let zero_ptr = phys_to_virt_base
            .wrapping_add(addr)
            .wrapping_add(free_chunk_sizeof) as *mut u8;
        let mut offset = 0usize;
        while offset < zero_len {
            core::ptr::write_volatile(zero_ptr.add(offset), 0);
            offset += 1;
        }
    }

    llist_add_first(node_addr.wrapping_add(zeroed_list_offset) as usize, llnode);
    compiler_fence(Ordering::SeqCst);
    atomic_i32_at(node_addr as usize, nr_to_zero_pages_offset as usize)
        .fetch_sub((size >> page_shift) as c_int, Ordering::SeqCst);

    if !addr_out.is_null() {
        core::ptr::write_volatile(addr_out, addr);
    }
    if !size_out.is_null() {
        core::ptr::write_volatile(size_out, size);
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_zero_mckernel_pages_finish_result(
    node_addr: c_ulong,
    zeroing_workers_offset: c_ulong,
) {
    if node_addr == 0 {
        return;
    }

    atomic_i32_at(node_addr as usize, zeroing_workers_offset as usize)
        .fetch_sub(1, Ordering::SeqCst);
}

#[no_mangle]
pub extern "C" fn mcctrl_control_request_needs_root_result(request: c_uint) -> c_int {
    matches!(
        request,
        IHK_OS_AUX_PERF_NUM
            | IHK_OS_AUX_PERF_SET
            | IHK_OS_AUX_PERF_GET
            | IHK_OS_AUX_PERF_ENABLE
            | IHK_OS_AUX_PERF_DISABLE
            | IHK_OS_AUX_PERF_DESTROY
    ) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_control_request_needs_root(request: c_uint) -> c_int {
    mcctrl_control_request_needs_root_result(request)
}

#[no_mangle]
pub extern "C" fn mcctrl_control_perm_result(request: c_uint, euid: c_uint) -> c_int {
    if mcctrl_control_request_needs_root_result(request) != 0 && euid != 0 {
        -EPERM
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_control_perm(request: c_uint, euid: c_uint) -> c_int {
    mcctrl_control_perm_result(request, euid)
}

type McctrlControlDispatchFn =
    unsafe extern "C" fn(os: c_ulong, arg: c_ulong, file: c_ulong) -> c_long;
type McctrlControlIkcSendFn =
    unsafe extern "C" fn(os: c_ulong, cpu: c_int, packet: *mut McctrlIkcScdPacket) -> c_int;
type McctrlControlGetPtrFn = unsafe extern "C" fn(os: c_ulong) -> *mut c_void;
type McctrlControlPtrFieldFn = unsafe extern "C" fn(ptr: *mut c_void) -> *mut c_void;
type McctrlControlPtrIntFn = unsafe extern "C" fn(ptr: *mut c_void) -> c_int;
type McctrlControlLogFn = unsafe extern "C" fn(stage: c_int);
type McctrlControlAllocFn = unsafe extern "C" fn(size: c_ulong) -> *mut c_void;
type McctrlControlFreeFn = unsafe extern "C" fn(ptr: *mut c_void);
type McctrlControlVirtToPhysFn = unsafe extern "C" fn(ptr: *mut c_void) -> c_ulong;
type McctrlControlCpuRegSendWaitFn = unsafe extern "C" fn(
    os: c_ulong,
    cpu: c_int,
    packet: *mut McctrlIkcScdPacket,
    timeout: c_long,
    do_free: *mut c_int,
    desc: *mut c_void,
) -> c_int;
type McctrlControlCpuRegErrorLogFn = unsafe extern "C" fn(stage: c_int, cpu: c_int, ret: c_int);
type McctrlControlCpuRegDoneLogFn =
    unsafe extern "C" fn(op: c_int, is_read: c_int, cpu: c_int, addr_ext: c_ulong, val: c_ulong);
type McctrlControlValidateOsFn = unsafe extern "C" fn(os: c_ulong) -> c_int;
type McctrlControlCurrentIntFn = unsafe extern "C" fn() -> c_int;
type McctrlControlCurrentTaskFn = unsafe extern "C" fn() -> *mut c_void;
type McctrlControlGetPpdFn =
    unsafe extern "C" fn(usrdata: *mut c_void, pid: c_int) -> *mut c_void;
type McctrlControlGetPtdFn =
    unsafe extern "C" fn(ppd: *mut c_void, task: *mut c_void) -> *mut c_void;
type McctrlControlPutFn = unsafe extern "C" fn(ptr: *mut c_void);
type McctrlControlPacketRefFn = unsafe extern "C" fn(packet: *mut c_void) -> c_int;
type McctrlControlChannelReadCpuFn =
    unsafe extern "C" fn(usrdata: *mut c_void, packet_ref: c_int) -> c_int;
type McctrlControlRequestCpuErrorLogFn =
    unsafe extern "C" fn(stage: c_int, os: c_ulong, pid: c_int, tid: c_int);
type McctrlControlRequestCpuPtdLogFn =
    unsafe extern "C" fn(stage: c_int, tid: c_int, ptd: *mut c_void);
type McctrlControlRequestCpuResultLogFn = unsafe extern "C" fn(os: c_ulong, cpu: c_int);

#[repr(C)]
pub struct McctrlControlDispatchOps {
    prepare_image: Option<McctrlControlDispatchFn>,
    transfer_image: Option<McctrlControlDispatchFn>,
    start_image: Option<McctrlControlDispatchFn>,
    wait_syscall: Option<McctrlControlDispatchFn>,
    ret_syscall: Option<McctrlControlDispatchFn>,
    load_syscall: Option<McctrlControlDispatchFn>,
    send_signal: Option<McctrlControlDispatchFn>,
    get_cpu: Option<McctrlControlDispatchFn>,
    create_ppd: Option<McctrlControlDispatchFn>,
    get_nodes: Option<McctrlControlDispatchFn>,
    get_cpuset: Option<McctrlControlDispatchFn>,
    strncpy_from_user: Option<McctrlControlDispatchFn>,
    open_exec: Option<McctrlControlDispatchFn>,
    close_exec: Option<McctrlControlDispatchFn>,
    prepare_dma: Option<McctrlControlDispatchFn>,
    free_dma: Option<McctrlControlDispatchFn>,
    get_cred: Option<McctrlControlDispatchFn>,
    get_credv: Option<McctrlControlDispatchFn>,
    sys_mount: Option<McctrlControlDispatchFn>,
    sys_umount: Option<McctrlControlDispatchFn>,
    sys_unshare: Option<McctrlControlDispatchFn>,
    uti_get_ctx: Option<McctrlControlDispatchFn>,
    uti_switch_ctx: Option<McctrlControlDispatchFn>,
    sig_thread: Option<McctrlControlDispatchFn>,
    syscall_thread: Option<McctrlControlDispatchFn>,
    terminate_thread: Option<McctrlControlDispatchFn>,
    release_user_space: Option<McctrlControlDispatchFn>,
    get_num_pool_threads: Option<McctrlControlDispatchFn>,
    uti_attr: Option<McctrlControlDispatchFn>,
    debug_log: Option<McctrlControlDispatchFn>,
    perf_num: Option<McctrlControlDispatchFn>,
    perf_set: Option<McctrlControlDispatchFn>,
    perf_get: Option<McctrlControlDispatchFn>,
    perf_enable: Option<McctrlControlDispatchFn>,
    perf_disable: Option<McctrlControlDispatchFn>,
    perf_destroy: Option<McctrlControlDispatchFn>,
    getrusage: Option<McctrlControlDispatchFn>,
}

unsafe fn mcctrl_call_control_dispatch(
    callback: Option<McctrlControlDispatchFn>,
    os: c_ulong,
    arg: c_ulong,
    file: c_ulong,
) -> c_long {
    match callback {
        Some(callback) => callback(os, arg, file),
        None => -(EINVAL as c_long),
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_dispatch_body_result(
    os: c_ulong,
    request: c_uint,
    arg: c_ulong,
    file: c_ulong,
    ops: *const McctrlControlDispatchOps,
) -> c_long {
    if ops.is_null() {
        return -(EINVAL as c_long);
    }

    let ops = &*ops;
    let callback = match request {
        MCEXEC_UP_PREPARE_IMAGE => ops.prepare_image,
        MCEXEC_UP_TRANSFER => ops.transfer_image,
        MCEXEC_UP_START_IMAGE => ops.start_image,
        MCEXEC_UP_WAIT_SYSCALL => ops.wait_syscall,
        MCEXEC_UP_RET_SYSCALL => ops.ret_syscall,
        MCEXEC_UP_LOAD_SYSCALL => ops.load_syscall,
        MCEXEC_UP_SEND_SIGNAL => ops.send_signal,
        MCEXEC_UP_GET_CPU => ops.get_cpu,
        MCEXEC_UP_CREATE_PPD => ops.create_ppd,
        MCEXEC_UP_GET_NODES => ops.get_nodes,
        MCEXEC_UP_GET_CPUSET => ops.get_cpuset,
        MCEXEC_UP_STRNCPY_FROM_USER => ops.strncpy_from_user,
        MCEXEC_UP_OPEN_EXEC => ops.open_exec,
        MCEXEC_UP_CLOSE_EXEC => ops.close_exec,
        MCEXEC_UP_PREPARE_DMA => ops.prepare_dma,
        MCEXEC_UP_FREE_DMA => ops.free_dma,
        MCEXEC_UP_GET_CRED => ops.get_cred,
        MCEXEC_UP_GET_CREDV => ops.get_credv,
        MCEXEC_UP_SYS_MOUNT => ops.sys_mount,
        MCEXEC_UP_SYS_UMOUNT => ops.sys_umount,
        MCEXEC_UP_SYS_UNSHARE => ops.sys_unshare,
        MCEXEC_UP_UTI_GET_CTX => ops.uti_get_ctx,
        MCEXEC_UP_UTI_SWITCH_CTX => ops.uti_switch_ctx,
        MCEXEC_UP_SIG_THREAD => ops.sig_thread,
        MCEXEC_UP_SYSCALL_THREAD => ops.syscall_thread,
        MCEXEC_UP_TERMINATE_THREAD => ops.terminate_thread,
        MCEXEC_UP_RELEASE_USER_SPACE => ops.release_user_space,
        MCEXEC_UP_GET_NUM_POOL_THREADS => ops.get_num_pool_threads,
        MCEXEC_UP_UTI_ATTR => ops.uti_attr,
        MCEXEC_UP_DEBUG_LOG => ops.debug_log,
        IHK_OS_AUX_PERF_NUM => ops.perf_num,
        IHK_OS_AUX_PERF_SET => ops.perf_set,
        IHK_OS_AUX_PERF_GET => ops.perf_get,
        IHK_OS_AUX_PERF_ENABLE => ops.perf_enable,
        IHK_OS_AUX_PERF_DISABLE => ops.perf_disable,
        IHK_OS_AUX_PERF_DESTROY => ops.perf_destroy,
        IHK_OS_GETRUSAGE => ops.getrusage,
        _ => return -(EINVAL as c_long),
    };

    mcctrl_call_control_dispatch(callback, os, arg, file)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_debug_log_body_result(
    os: c_ulong,
    arg: c_ulong,
    send: Option<McctrlControlIkcSendFn>,
) -> c_long {
    let Some(send) = send else {
        return -(EINVAL as c_long);
    };

    let mut packet = MaybeUninit::<McctrlIkcScdPacket>::zeroed();
    let packet = packet.assume_init_mut();
    packet.msg = SCD_MSG_DEBUG_LOG;
    packet.body.traditional.arg = arg;
    send(os, 0, packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_get_cpu_body_result(
    os: c_ulong,
    get_cpu_info: Option<McctrlControlGetPtrFn>,
    cpu_info_n_cpus: Option<McctrlControlPtrIntFn>,
    log_error: Option<McctrlControlLogFn>,
) -> c_long {
    let (Some(get_cpu_info), Some(cpu_info_n_cpus), Some(log_error)) =
        (get_cpu_info, cpu_info_n_cpus, log_error)
    else {
        return -(EINVAL as c_long);
    };

    let info = get_cpu_info(os);
    if info.is_null() {
        log_error(0);
        return -(EINVAL as c_long);
    }

    let n_cpus = cpu_info_n_cpus(info);
    if n_cpus < 1 {
        log_error(1);
        return -(EINVAL as c_long);
    }

    n_cpus as c_long
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_get_nodes_body_result(
    os: c_ulong,
    get_usrdata: Option<McctrlControlGetPtrFn>,
    usrdata_mem_info: Option<McctrlControlPtrFieldFn>,
    mem_info_n_nodes: Option<McctrlControlPtrIntFn>,
    log_error: Option<McctrlControlLogFn>,
) -> c_long {
    let (Some(get_usrdata), Some(usrdata_mem_info), Some(mem_info_n_nodes), Some(log_error)) =
        (get_usrdata, usrdata_mem_info, mem_info_n_nodes, log_error)
    else {
        return -(EINVAL as c_long);
    };

    let usrdata = get_usrdata(os);
    if usrdata.is_null() {
        log_error(0);
        return -(EINVAL as c_long);
    }

    let mem_info = usrdata_mem_info(usrdata);
    if mem_info.is_null() {
        log_error(1);
        return -(EINVAL as c_long);
    }

    mem_info_n_nodes(mem_info) as c_long
}

type McctrlInKernelReqFn =
    unsafe extern "C" fn(os: c_ulong, req: *mut McctrlSyscallRequest) -> c_long;
type McctrlInKernelClearPteFn = unsafe extern "C" fn(start: c_ulong, len: c_ulong) -> c_long;
type McctrlInKernelRemapFn =
    unsafe extern "C" fn(start: c_ulong, len: c_ulong, prot: c_int) -> c_long;
type McctrlInKernelZeroPagesFn = unsafe extern "C" fn(arg: c_ulong);
type McctrlInKernelWritecoreFn = unsafe extern "C" fn(
    os: c_ulong,
    rcoretable: c_ulong,
    chunks: c_int,
    offset: c_ulong,
    filename: c_ulong,
) -> c_long;
type McctrlInKernelSchedFn = unsafe extern "C" fn(arg: c_int) -> c_long;
type McctrlInKernelReturnFn =
    unsafe extern "C" fn(os: c_ulong, packet: *mut McctrlIkcScdPacket, ret: c_long, stid: c_int);
type McctrlInKernelReleaseFn = unsafe extern "C" fn(packet: *mut McctrlIkcScdPacket);

#[repr(C)]
pub struct McctrlInKernelSyscallOps {
    pager_irq: Option<McctrlInKernelReqFn>,
    pager: Option<McctrlInKernelReqFn>,
    clear_pte: Option<McctrlInKernelClearPteFn>,
    remap: Option<McctrlInKernelRemapFn>,
    zero_pages: Option<McctrlInKernelZeroPagesFn>,
    writecore: Option<McctrlInKernelWritecoreFn>,
    sched_same_owner: Option<McctrlInKernelSchedFn>,
    sched_root: Option<McctrlInKernelSchedFn>,
    tofu_close: Option<McctrlInKernelReqFn>,
    return_syscall: Option<McctrlInKernelReturnFn>,
    release_packet: Option<McctrlInKernelReleaseFn>,
}

unsafe fn mcctrl_set_ret_out(ret_out: *mut c_long, ret: c_long) {
    if !ret_out.is_null() {
        core::ptr::write_volatile(ret_out, ret);
    }
}

unsafe fn mcctrl_in_kernel_return_and_release(
    os: c_ulong,
    packet: *mut McctrlIkcScdPacket,
    ret: c_long,
    ops: &McctrlInKernelSyscallOps,
) -> c_int {
    let Some(return_syscall) = ops.return_syscall else {
        return -EINVAL;
    };
    let Some(release_packet) = ops.release_packet else {
        return -EINVAL;
    };

    return_syscall(os, packet, ret, 0);
    release_packet(packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_in_kernel_irq_syscall_body_result(
    os: c_ulong,
    packet: *mut McctrlIkcScdPacket,
    ops: *const McctrlInKernelSyscallOps,
    ret_out: *mut c_long,
) -> c_int {
    if packet.is_null() || ops.is_null() {
        return -EINVAL;
    }

    let ops = &*ops;
    let req = &mut (*packet).body.traditional.req as *mut McctrlSyscallRequest;
    let number = (*req).number;
    let ret = match number {
        NR_MMAP => {
            let Some(pager_irq) = ops.pager_irq else {
                return -EINVAL;
            };
            pager_irq(os, req)
        }
        _ => return -ENOSYS,
    };

    mcctrl_set_ret_out(ret_out, ret);
    if ret == -(ENOSYS as c_long) {
        return -ENOSYS;
    }

    let Some(return_syscall) = ops.return_syscall else {
        return -EINVAL;
    };
    return_syscall(os, packet, ret, 0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_in_kernel_syscall_body_result(
    os: c_ulong,
    packet: *mut McctrlIkcScdPacket,
    ops: *const McctrlInKernelSyscallOps,
    ret_out: *mut c_long,
) -> c_int {
    if packet.is_null() || ops.is_null() {
        return -EINVAL;
    }

    let ops = &*ops;
    let req = &mut (*packet).body.traditional.req as *mut McctrlSyscallRequest;
    let number = (*req).number;
    let args = (*req).args;
    let mut ret: c_long = -1;

    match number {
        NR_CLOSE => {
            if let Some(tofu_close) = ops.tofu_close {
                tofu_close(os, req);
            }
            mcctrl_set_ret_out(ret_out, ret);
            -ENOSYS
        }
        NR_MMAP => {
            let Some(pager) = ops.pager else {
                return -EINVAL;
            };
            ret = pager(os, req);
            mcctrl_set_ret_out(ret_out, ret);
            mcctrl_in_kernel_return_and_release(os, packet, ret, ops)
        }
        NR_MUNMAP => {
            let Some(clear_pte) = ops.clear_pte else {
                return -EINVAL;
            };
            ret = clear_pte(args[0], args[1]);
            mcctrl_set_ret_out(ret_out, ret);
            mcctrl_in_kernel_return_and_release(os, packet, ret, ops)
        }
        NR_MPROTECT => {
            let Some(remap) = ops.remap else {
                return -EINVAL;
            };
            ret = remap(args[0], args[1], args[2] as c_int);
            mcctrl_set_ret_out(ret_out, ret);
            mcctrl_in_kernel_return_and_release(os, packet, ret, ops)
        }
        NR_MOVE_PAGES => {
            let Some(zero_pages) = ops.zero_pages else {
                return -EINVAL;
            };
            zero_pages(args[0]);
            mcctrl_set_ret_out(ret_out, ret);
            let Some(release_packet) = ops.release_packet else {
                return -EINVAL;
            };
            release_packet(packet);
            0
        }
        NR_EXIT_GROUP => {
            mcctrl_set_ret_out(ret_out, ret);
            -ENOSYS
        }
        NR_COREDUMP => {
            let Some(writecore) = ops.writecore else {
                return -EINVAL;
            };
            ret = writecore(os, args[1], args[0] as c_int, args[2], args[3]);
            mcctrl_set_ret_out(ret_out, ret);
            mcctrl_in_kernel_return_and_release(os, packet, ret, ops)
        }
        NR_SCHED_SETPARAM => {
            ret = match args[0] {
                SCHED_CHECK_SAME_OWNER_VALUE => {
                    let Some(sched_same_owner) = ops.sched_same_owner else {
                        return -EINVAL;
                    };
                    sched_same_owner(args[1] as c_int)
                }
                SCHED_CHECK_ROOT_VALUE => {
                    let Some(sched_root) = ops.sched_root else {
                        return -EINVAL;
                    };
                    sched_root(args[1] as c_int)
                }
                _ => -1,
            };
            mcctrl_set_ret_out(ret_out, ret);
            mcctrl_in_kernel_return_and_release(os, packet, ret, ops)
        }
        _ => {
            mcctrl_set_ret_out(ret_out, ret);
            -ENOSYS
        }
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_cpu_register_copyback_result(op: c_int, read_op: c_int) -> c_int {
    (op == read_op) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_cpu_register_copyback(op: c_int, read_op: c_int) -> c_int {
    mcctrl_cpu_register_copyback_result(op, read_op)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_cpu_register_body_result(
    os: c_ulong,
    cpu: c_int,
    desc: *mut McctrlIhkOsCpuRegister,
    op: c_int,
    get_usrdata: Option<McctrlControlGetPtrFn>,
    usrdata_cpu_count: Option<McctrlControlPtrIntFn>,
    alloc_desc: Option<McctrlControlAllocFn>,
    free_desc: Option<McctrlControlFreeFn>,
    virt_to_phys: Option<McctrlControlVirtToPhysFn>,
    send_wait: Option<McctrlControlCpuRegSendWaitFn>,
    log_error: Option<McctrlControlCpuRegErrorLogFn>,
    log_done: Option<McctrlControlCpuRegDoneLogFn>,
) -> c_int {
    let (
        Some(get_usrdata),
        Some(usrdata_cpu_count),
        Some(alloc_desc),
        Some(free_desc),
        Some(virt_to_phys),
        Some(send_wait),
        Some(log_error),
        Some(log_done),
    ) = (
        get_usrdata,
        usrdata_cpu_count,
        alloc_desc,
        free_desc,
        virt_to_phys,
        send_wait,
        log_error,
        log_done,
    )
    else {
        return -EINVAL;
    };

    if desc.is_null() {
        return -EINVAL;
    }

    let usrdata = get_usrdata(os);
    if usrdata.is_null() {
        log_error(0, cpu, 0);
        return -EINVAL;
    }

    let n_cpus = usrdata_cpu_count(usrdata);
    if mcctrl_ikc_cpu_index_valid_result(cpu, n_cpus) == 0 {
        log_error(1, cpu, 0);
        return -EINVAL;
    }

    let local_desc =
        alloc_desc(size_of::<McctrlIhkOsCpuRegister>() as c_ulong) as *mut McctrlIhkOsCpuRegister;
    if local_desc.is_null() {
        log_error(2, cpu, 0);
        return -ENOMEM;
    }
    core::ptr::copy_nonoverlapping(desc, local_desc, 1);

    let mut packet = MaybeUninit::<McctrlIkcScdPacket>::zeroed();
    let packet = packet.assume_init_mut();
    packet.msg = SCD_MSG_CPU_RW_REG;
    packet.body.cpu_rw.op = op;
    packet.body.cpu_rw.pdesc = virt_to_phys(local_desc.cast::<c_void>());

    let mut do_free = 0;
    let ret = send_wait(
        os,
        cpu,
        packet,
        -10000,
        &mut do_free,
        local_desc.cast::<c_void>(),
    );
    if ret != 0 {
        log_error(3, cpu, ret);
        if do_free != 0 {
            free_desc(local_desc.cast::<c_void>());
        }
        return ret;
    }

    let is_read = mcctrl_cpu_register_copyback_result(op, MCCTRL_OS_CPU_READ_REGISTER);
    if is_read != 0 {
        (*desc).val = (*local_desc).val;
    }
    (*desc).sync.store(1, Ordering::SeqCst);
    log_done(op, is_read, cpu, (*desc).addr_ext, (*desc).val);

    if do_free != 0 {
        free_desc(local_desc.cast::<c_void>());
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_control_get_request_os_cpu_body_result(
    os: c_ulong,
    ret_cpu: *mut c_int,
    validate_os: Option<McctrlControlValidateOsFn>,
    get_usrdata: Option<McctrlControlGetPtrFn>,
    current_pid: Option<McctrlControlCurrentIntFn>,
    current_tid: Option<McctrlControlCurrentIntFn>,
    current_task: Option<McctrlControlCurrentTaskFn>,
    get_ppd: Option<McctrlControlGetPpdFn>,
    put_ppd: Option<McctrlControlPutFn>,
    get_ptd: Option<McctrlControlGetPtdFn>,
    put_ptd: Option<McctrlControlPutFn>,
    ptd_data: Option<McctrlControlPtrFieldFn>,
    packet_ref: Option<McctrlControlPacketRefFn>,
    channel_read_cpu: Option<McctrlControlChannelReadCpuFn>,
    log_error: Option<McctrlControlRequestCpuErrorLogFn>,
    log_ptd: Option<McctrlControlRequestCpuPtdLogFn>,
    log_result: Option<McctrlControlRequestCpuResultLogFn>,
) -> c_int {
    let (
        Some(validate_os),
        Some(get_usrdata),
        Some(current_pid),
        Some(current_tid),
        Some(current_task),
        Some(get_ppd),
        Some(put_ppd),
        Some(get_ptd),
        Some(put_ptd),
        Some(ptd_data),
        Some(packet_ref),
        Some(channel_read_cpu),
        Some(log_error),
        Some(log_ptd),
        Some(log_result),
    ) = (
        validate_os,
        get_usrdata,
        current_pid,
        current_tid,
        current_task,
        get_ppd,
        put_ppd,
        get_ptd,
        put_ptd,
        ptd_data,
        packet_ref,
        channel_read_cpu,
        log_error,
        log_ptd,
        log_result,
    )
    else {
        return -EINVAL;
    };

    if os == 0 || ret_cpu.is_null() || validate_os(os) != 0 {
        return -EINVAL;
    }

    let usrdata = get_usrdata(os);
    if usrdata.is_null() {
        log_error(0, os, 0, 0);
        return -EINVAL;
    }

    let pid = current_pid();
    let ppd = get_ppd(usrdata, pid);
    if ppd.is_null() {
        log_error(1, os, pid, 0);
        return -EINVAL;
    }

    let ptd = get_ptd(ppd, current_task());
    if ptd.is_null() {
        log_error(2, os, pid, current_tid());
        put_ppd(ppd);
        return -EINVAL;
    }

    let tid = current_tid();
    log_ptd(0, tid, ptd);
    let packet = ptd_data(ptd);
    if packet.is_null() {
        log_error(3, os, pid, tid);
        put_ptd(ptd);
        log_ptd(1, tid, ptd);
        put_ppd(ppd);
        return -EINVAL;
    }

    let cpu = channel_read_cpu(usrdata, packet_ref(packet));
    *ret_cpu = cpu;
    log_result(os, cpu);

    put_ptd(ptd);
    log_ptd(1, tid, ptd);
    put_ppd(ppd);
    0
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_free_addrs_owner_result(free_addrs_count: c_int) -> c_int {
    (free_addrs_count != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_free_addrs_owner(free_addrs_count: c_int) -> c_int {
    mcctrl_ikc_free_addrs_owner_result(free_addrs_count)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_desc_free_at_put_result(allocated_internally: c_int) -> c_int {
    (allocated_internally != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_desc_free_at_put(allocated_internally: c_int) -> c_int {
    mcctrl_ikc_desc_free_at_put_result(allocated_internally)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_mode_result(timeout: c_long) -> c_int {
    if timeout < 0 {
        -1
    } else if timeout > 0 {
        1
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_mode(timeout: c_long) -> c_int {
    mcctrl_ikc_wait_mode_result(timeout)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_busy_timeout_msecs_result(timeout: c_long) -> c_ulong {
    timeout.wrapping_neg() as c_ulong
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_busy_timeout_msecs(timeout: c_long) -> c_ulong {
    mcctrl_ikc_busy_timeout_msecs_result(timeout)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_abort_return_result(wait_ret: c_int) -> c_int {
    if wait_ret < 0 {
        wait_ret
    } else {
        -ETIME
    }
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_wait_abort_return(wait_ret: c_int) -> c_int {
    mcctrl_ikc_wait_abort_return_result(wait_ret)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_release_packet_after_handler_result(msg: c_int) -> c_int {
    (msg != SCD_MSG_SYSCALL_ONESIDE) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_release_packet_after_handler(msg: c_int) -> c_int {
    mcctrl_ikc_release_packet_after_handler_result(msg)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_nonnegative_result(cpu: c_int) -> c_int {
    (cpu >= 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_nonnegative(cpu: c_int) -> c_int {
    mcctrl_ikc_cpu_nonnegative_result(cpu)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_index_valid_result(cpu: c_int, num_channels: c_int) -> c_int {
    (cpu >= 0 && cpu < num_channels) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_index_valid(cpu: c_int, num_channels: c_int) -> c_int {
    mcctrl_ikc_cpu_index_valid_result(cpu, num_channels)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_linux_cpu_valid_result(linux_cpu: c_int, nr_cpu_ids: c_int) -> c_int {
    (linux_cpu <= nr_cpu_ids) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_linux_cpu_valid(linux_cpu: c_int, nr_cpu_ids: c_int) -> c_int {
    mcctrl_ikc_linux_cpu_valid_result(linux_cpu, nr_cpu_ids)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_init_uses_last_channel_result(port: c_int) -> c_int {
    (port == MCCTRL_IKC_INIT_LAST_CHANNEL_PORT) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_init_uses_last_channel(port: c_int) -> c_int {
    mcctrl_ikc_init_uses_last_channel_result(port)
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_count_valid_result(n_cpus: c_int) -> c_int {
    (n_cpus >= 1) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ikc_cpu_count_valid(n_cpus: c_int) -> c_int {
    mcctrl_ikc_cpu_count_valid_result(n_cpus)
}

const SCD_MSG_INIT_CHANNEL: c_int = 0x5;
const SCD_MSG_INIT_CHANNEL_ACKED: c_int = 0x6;
const SCD_MSG_PREPARE_PROCESS_ACKED: c_int = 0x2;
const SCD_MSG_SEND_SIGNAL_ACK: c_int = 0x8;
const SCD_MSG_CLEANUP_PROCESS_RESP: c_int = 0xa;
const SCD_MSG_GET_VDSO_INFO: c_int = 0xb;
const SCD_MSG_PROCFS_ANSWER: c_int = 0x13;
const SCD_MSG_REMOTE_PAGE_FAULT_ANSWER: c_int = 0x19;
const SCD_MSG_SYSFS_REQ_CREATE: c_int = 0x30;
const SCD_MSG_SYSFS_REQ_MKDIR: c_int = 0x32;
const SCD_MSG_SYSFS_REQ_SYMLINK: c_int = 0x34;
const SCD_MSG_SYSFS_REQ_LOOKUP: c_int = 0x36;
const SCD_MSG_SYSFS_REQ_UNLINK: c_int = 0x38;
const SCD_MSG_SYSFS_REQ_SHOW: c_int = 0x3a;
const SCD_MSG_SYSFS_RESP_SHOW: c_int = 0x3b;
const SCD_MSG_SYSFS_REQ_STORE: c_int = 0x3c;
const SCD_MSG_SYSFS_RESP_STORE: c_int = 0x3d;
const SCD_MSG_SYSFS_REQ_RELEASE: c_int = 0x3e;
const SCD_MSG_SYSFS_RESP_RELEASE: c_int = 0x3f;
const SCD_MSG_SYSFS_REQ_SETUP: c_int = 0x40;
const SCD_MSG_PROCFS_TID_CREATE: c_int = 0x44;
const SCD_MSG_PROCFS_TID_DELETE: c_int = 0x45;
const SCD_MSG_EVENTFD: c_int = 0x46;
const SCD_MSG_PERF_ACK: c_int = 0x51;
const SCD_MSG_CPU_RW_REG_RESP: c_int = 0x53;
const SCD_MSG_CLEANUP_FD_RESP: c_int = 0x55;
const SCD_MSG_FUTEX_WAKE: c_int = 0x60;
const IHK_IKC_DIRECTION_SEND: c_int = 0;
const IHK_IKC_DIRECTION_RECV: c_int = 1;
const MCCTRL_IKC2MCKERNEL_PORT: c_int = 501;
const MCCTRL_IKC2LINUX_PORT: c_int = 503;
const MCCTRL_IKC2MCKERNEL_MAGIC: c_int = 0x1329;
const MCCTRL_IKC2LINUX_MAGIC: c_int = 0x1129;

const PREPARE_IKC_CHANNELS_NAME: &[u8] = b"prepare_ikc_channels\0";
const DESTROY_IKC_CHANNELS_NAME: &[u8] = b"destroy_ikc_channels\0";
const MCCTRL_IKC_INIT_NAME: &[u8] = b"mcctrl_ikc_init\0";
const CONNECT_IKC2LINUX_NAME: &[u8] = b"connect_handler_ikc2linux\0";
const CONNECT_IKC2MCKERNEL_NAME: &[u8] = b"connect_handler_ikc2mckernel\0";
const MCCTRL_IKC_SEND_WAIT_NAME: &[u8] = b"mcctrl_ikc_send_wait\0";
const MCCTRL_IKC_SET_RECV_CPU_NAME: &[u8] = b"mcctrl_ikc_set_recv_cpu\0";
const SYSCALL_PACKET_HANDLER_NAME: &[u8] = b"syscall_packet_handler\0";
const DUMMY_PACKET_HANDLER_NAME: &[u8] = b"dummy_packet_handler\0";

#[repr(C)]
pub struct McctrlProcfsWorkPrefix {
    os: *mut c_void,
    msg: c_int,
    pid: c_int,
    arg: c_ulong,
    resp_pa: c_ulong,
}

type McctrlProcfsWorkAllocFn =
    Option<unsafe extern "C" fn(size: usize) -> *mut McctrlProcfsWorkPrefix>;
type McctrlProcfsWorkInitScheduleFn =
    Option<unsafe extern "C" fn(work: *mut McctrlProcfsWorkPrefix)>;
type McctrlProcfsAllocFailedFn = Option<unsafe extern "C" fn()>;
type McctrlProcfsGetIndexFn = Option<unsafe extern "C" fn(os: *mut c_void) -> c_int>;
type McctrlProcfsEntryFn = Option<unsafe extern "C" fn(osnum: c_int, pid: c_int, tid: c_int)>;
type McctrlProcfsOsToDevFn = Option<unsafe extern "C" fn(os: *mut c_void) -> *mut c_void>;
type McctrlProcfsMapMemoryFn =
    Option<unsafe extern "C" fn(dev: *mut c_void, phys: c_ulong, size: c_ulong) -> c_ulong>;
type McctrlProcfsMapVirtualFn = Option<
    unsafe extern "C" fn(
        dev: *mut c_void,
        phys: c_ulong,
        size: c_ulong,
        attr: *mut c_void,
        flags: c_int,
    ) -> *mut c_void,
>;
type McctrlProcfsUnmapVirtualFn =
    Option<unsafe extern "C" fn(dev: *mut c_void, virt: *mut c_void, size: c_ulong)>;
type McctrlProcfsUnmapMemoryFn =
    Option<unsafe extern "C" fn(dev: *mut c_void, phys: c_ulong, size: c_ulong)>;
type McctrlProcfsUnknownWorkFn = Option<unsafe extern "C" fn(msg: c_int, pid: c_int, arg: c_ulong)>;
type McctrlProcfsFreeWorkFn = Option<unsafe extern "C" fn(work: *mut c_void)>;
type McctrlProcfsFormatNameFn =
    Option<unsafe extern "C" fn(buf: *mut c_char, buflen: c_ulong, value: c_int) -> c_int>;
type McctrlProcfsFindEntryFn =
    Option<unsafe extern "C" fn(parent: *mut c_void, name: *const c_char) -> *mut c_void>;
type McctrlProcfsAddEntryFn = Option<
    unsafe extern "C" fn(parent: *mut c_void, name: *const c_char, mode: c_int) -> *mut c_void,
>;
type McctrlProcfsSetOsnumFn = Option<unsafe extern "C" fn(entry: *mut c_void, osnum: c_int)>;
type McctrlProcfsGetCredFn = Option<unsafe extern "C" fn(pid: c_int) -> *mut c_void>;
type McctrlProcfsLockFn = Option<unsafe extern "C" fn()>;
type McctrlProcfsOsLookupFn = Option<unsafe extern "C" fn(osnum: c_int) -> *mut c_void>;
type McctrlProcfsOsPidLookupFn =
    Option<unsafe extern "C" fn(osnum: c_int, pid: c_int) -> *mut c_void>;
type McctrlProcfsOsPidTidLookupFn =
    Option<unsafe extern "C" fn(osnum: c_int, pid: c_int, tid: c_int) -> *mut c_void>;
type McctrlProcfsAddEntriesCredFn =
    Option<unsafe extern "C" fn(parent: *mut c_void, cred: *mut c_void)>;
type McctrlProcfsAddEntriesFn = Option<unsafe extern "C" fn(parent: *mut c_void)>;
type McctrlProcfsAddTidCredFn =
    Option<unsafe extern "C" fn(osnum: c_int, pid: c_int, tid: c_int, cred: *mut c_void)>;
type McctrlProcfsDeleteEntryFn = Option<unsafe extern "C" fn(entry: *mut c_void)>;
type McctrlProcfsFindExeDataFn = Option<unsafe extern "C" fn(parent: *mut c_void) -> *mut c_void>;
type McctrlProcfsAddExeLinkFn =
    Option<unsafe extern "C" fn(parent: *mut c_void, target: *mut c_void, cred: *mut c_void)>;
type McctrlProcfsAddPidExeFn =
    Option<unsafe extern "C" fn(parent: *mut c_void, path: *const c_char) -> *mut c_void>;
type McctrlProcfsStoreExePathFn =
    Option<unsafe extern "C" fn(entry: *mut c_void, path: *const c_char)>;
type McctrlProcfsAddTaskExeLinksFn =
    Option<unsafe extern "C" fn(parent: *mut c_void, path: *const c_char)>;
type McctrlProcfsEntryOsnumFn = Option<unsafe extern "C" fn(entry: *mut c_void) -> c_int>;
type McctrlProcfsAllocFn = Option<unsafe extern "C" fn(size: usize) -> *mut c_void>;
type McctrlProcfsFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
type McctrlProcfsGetPathFn = Option<
    unsafe extern "C" fn(entry: *mut c_void, buf: *mut c_char, size: c_ulong) -> *const c_char,
>;
type McctrlProcfsInitBufferInfoFn = Option<
    unsafe extern "C" fn(
        info: *mut c_void,
        os: *mut c_void,
        pid: c_int,
        pa_null: c_ulong,
        path: *const c_char,
    ),
>;
type McctrlProcfsSetFilePrivateFn =
    Option<unsafe extern "C" fn(file: *mut c_void, data: *mut c_void)>;
type McctrlProcfsGetFilePrivateFn = Option<unsafe extern "C" fn(file: *mut c_void) -> *mut c_void>;
type McctrlProcfsInfoTopPaFn = Option<unsafe extern "C" fn(info: *mut c_void) -> c_ulong>;
type McctrlProcfsInfoOsFn = Option<unsafe extern "C" fn(info: *mut c_void) -> *mut c_void>;
type McctrlProcfsAllocReadFn = Option<unsafe extern "C" fn() -> *mut c_void>;
type McctrlProcfsInitReleaseReadFn =
    Option<unsafe extern "C" fn(read: *mut c_void, top_pa: c_ulong)>;
type McctrlProcfsSendReleaseFn =
    Option<unsafe extern "C" fn(os: *mut c_void, read: *mut c_void, do_free: *mut c_int) -> c_int>;
type McctrlProcfsReadRetFn = Option<unsafe extern "C" fn(read: *mut c_void) -> c_int>;
type McctrlProcfsReadPbufFn = Option<unsafe extern "C" fn(read: *mut c_void) -> c_ulong>;
type McctrlProcfsLogFn = Option<unsafe extern "C" fn()>;
type McctrlProcfsInfoPidFn = Option<unsafe extern "C" fn(info: *mut c_void) -> c_int>;
type McctrlProcfsInfoCurPaFn = Option<unsafe extern "C" fn(info: *mut c_void) -> c_ulong>;
type McctrlProcfsInfoPathFn = Option<unsafe extern "C" fn(info: *mut c_void) -> *const c_char>;
type McctrlProcfsInfoSetPaFn =
    Option<unsafe extern "C" fn(info: *mut c_void, top_pa: c_ulong, cur_pa: c_ulong)>;
type McctrlProcfsInfoSetCurPaFn = Option<unsafe extern "C" fn(info: *mut c_void, cur_pa: c_ulong)>;
type McctrlProcfsGetUsrdataFn = Option<unsafe extern "C" fn(os: *mut c_void) -> *mut c_void>;
type McctrlProcfsGetPerProcFn =
    Option<unsafe extern "C" fn(usrdata: *mut c_void, pid: c_int) -> *mut c_void>;
type McctrlProcfsPutPerProcFn = Option<unsafe extern "C" fn(ppd: *mut c_void)>;
type McctrlProcfsPpdCpuFn = Option<unsafe extern "C" fn(ppd: *mut c_void) -> c_int>;
type McctrlProcfsInitRequestReadFn =
    Option<unsafe extern "C" fn(read: *mut c_void, pbuf: c_ulong, path: *const c_char)>;
type McctrlProcfsSendRequestFn = Option<
    unsafe extern "C" fn(
        os: *mut c_void,
        cpu: c_int,
        pid: c_int,
        read: *mut c_void,
        do_free: *mut c_int,
    ) -> c_int,
>;
type McctrlProcfsBufferFieldFn = Option<unsafe extern "C" fn(buffer: *mut c_void) -> c_ulong>;
type McctrlProcfsCopyBufferToUserFn = Option<
    unsafe extern "C" fn(
        ubuf: *mut c_void,
        buffer: *mut c_void,
        offset: c_ulong,
        size: c_ulong,
    ) -> c_int,
>;
type McctrlProcfsPidLogFn = Option<unsafe extern "C" fn(pid: c_int)>;
type McctrlProcfsGetOrderFn = Option<unsafe extern "C" fn(count: c_ulong) -> c_int>;
type McctrlProcfsAllocPagesFn = Option<unsafe extern "C" fn(order: c_int) -> *mut c_void>;
type McctrlProcfsFreePagesFn = Option<unsafe extern "C" fn(ptr: *mut c_void, order: c_int)>;
type McctrlProcfsVirtToPhysFn = Option<unsafe extern "C" fn(ptr: *mut c_void) -> c_ulong>;
type McctrlProcfsInitReadWriteReadFn = Option<
    unsafe extern "C" fn(
        read: *mut c_void,
        pbuf: c_ulong,
        offset: c_long,
        count: c_int,
        read_write: c_int,
        path: *const c_char,
    ),
>;
type McctrlProcfsReadEofFn = Option<unsafe extern "C" fn(read: *mut c_void) -> c_int>;
type McctrlProcfsCopyKernelToUserFn =
    Option<unsafe extern "C" fn(ubuf: *mut c_void, kbuf: *mut c_void, size: c_ulong) -> c_int>;
type McctrlProcfsOsnumLogFn = Option<unsafe extern "C" fn(osnum: c_int)>;
type McctrlProcfsOsnumMismatchLogFn =
    Option<unsafe extern "C" fn(path_osnum: c_int, entry_osnum: c_int)>;

const PROCFS_TASK_NAME: &[u8] = b"task\0";
const PROCFS_DIR_MODE_0555: c_int = 0o040000 | 0o555;

#[repr(C)]
pub struct McctrlSysfsWorkPrefix {
    os: *mut c_void,
    msg: c_int,
    err: c_int,
    arg1: c_long,
    arg2: c_long,
}

#[repr(C)]
pub struct McctrlSysfsReqCreateParam {
    mode: c_int,
    error: c_int,
    client_ops: c_long,
    client_instance: c_long,
    path: [c_char; 1024],
    padding: c_int,
    busy: c_int,
}

#[repr(C)]
pub struct McctrlSysfsReqMkdirParam {
    error: c_int,
    padding: c_int,
    handle: c_long,
    path: [c_char; 1024],
    padding2: c_int,
    busy: c_int,
}

#[repr(C)]
pub struct McctrlSysfsReqSymlinkParam {
    error: c_int,
    padding: c_int,
    target: c_long,
    path: [c_char; 1024],
    padding2: c_int,
    busy: c_int,
}

#[repr(C)]
pub struct McctrlSysfsReqLookupParam {
    error: c_int,
    padding: c_int,
    handle: c_long,
    path: [c_char; 1024],
    padding2: c_int,
    busy: c_int,
}

#[repr(C)]
pub struct McctrlSysfsReqUnlinkParam {
    flags: c_int,
    error: c_int,
    path: [c_char; 1024],
    padding: c_int,
    busy: c_int,
}

type McctrlSysfsWorkAllocFn =
    Option<unsafe extern "C" fn(size: usize) -> *mut McctrlSysfsWorkPrefix>;
type McctrlSysfsWorkInitScheduleFn = Option<unsafe extern "C" fn(work: *mut McctrlSysfsWorkPrefix)>;
type McctrlSysfsAllocFailedFn = Option<unsafe extern "C" fn()>;
type McctrlSysfsRequestFn = Option<unsafe extern "C" fn(os: *mut c_void, arg: c_long)>;
type McctrlSysfsResponseFn =
    Option<unsafe extern "C" fn(os: *mut c_void, node: *mut c_void, result: c_long)>;
type McctrlSysfsReleaseResponseFn =
    Option<unsafe extern "C" fn(os: *mut c_void, node: *mut c_void, error: c_int)>;
type McctrlSysfsUnknownWorkFn =
    Option<unsafe extern "C" fn(msg: c_int, os: *mut c_void, arg1: c_long, arg2: c_long)>;
type McctrlSysfsFreeWorkFn = Option<unsafe extern "C" fn(work: *mut c_void)>;
type McctrlSysfsLocalAllocFn = Option<unsafe extern "C" fn(size: usize) -> *mut c_void>;
type McctrlSysfsLocalCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, size: usize)>;
type McctrlSysfsUnknownOpsFn = Option<unsafe extern "C" fn(ops: c_long)>;
type McctrlSysfsNodeLongFn = Option<unsafe extern "C" fn(node: *mut c_void) -> c_long>;
type McctrlSysfsNodeTypeFn = Option<unsafe extern "C" fn(node: *mut c_void) -> c_int>;
type McctrlSysfsFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
type McctrlSysfsLocalCreateFn =
    Option<unsafe extern "C" fn(os: *mut c_void, param: *mut McctrlSysfsReqCreateParam) -> c_int>;
type McctrlSysfsLocalMkdirFn =
    Option<unsafe extern "C" fn(os: *mut c_void, param: *mut McctrlSysfsReqMkdirParam) -> c_int>;
type McctrlSysfsLocalSymlinkFn =
    Option<unsafe extern "C" fn(os: *mut c_void, param: *mut McctrlSysfsReqSymlinkParam) -> c_int>;
type McctrlSysfsLocalLookupFn =
    Option<unsafe extern "C" fn(os: *mut c_void, param: *mut McctrlSysfsReqLookupParam) -> c_int>;
type McctrlSysfsLocalUnlinkFn =
    Option<unsafe extern "C" fn(os: *mut c_void, param: *mut McctrlSysfsReqUnlinkParam) -> c_int>;
type McctrlSysfsCleanupSpecialFn =
    Option<unsafe extern "C" fn(ops: *mut c_void, instance: *mut c_void)>;
type McctrlSysfsErrorFn = Option<unsafe extern "C" fn(error: c_int)>;
type McctrlSysfsSemDownFn = Option<unsafe extern "C" fn(sem: *mut c_void) -> c_int>;
type McctrlSysfsSemUpFn = Option<unsafe extern "C" fn(sem: *mut c_void)>;
type McctrlSysfsWaitReadyFn = Option<unsafe extern "C" fn(req: *mut c_void) -> c_int>;
type McctrlSysfsSetBusyFn = Option<unsafe extern "C" fn(req: *mut c_void, busy: c_int)>;
type McctrlSysfsSendFn = Option<
    unsafe extern "C" fn(
        os: *mut c_void,
        cpu: c_int,
        msg: c_int,
        arg1: c_long,
        arg2: c_long,
        arg3: c_long,
        err: c_int,
    ) -> c_int,
>;
type McctrlSysfsReqResultFn = Option<unsafe extern "C" fn(req: *mut c_void) -> c_long>;

const MCCTRL_SYSFS_REMOTE_STAGE_OK: c_int = 0;
const MCCTRL_SYSFS_REMOTE_STAGE_NOT_INIT: c_int = 1;
const MCCTRL_SYSFS_REMOTE_STAGE_DOWN: c_int = 2;
const MCCTRL_SYSFS_REMOTE_STAGE_WAIT0: c_int = 3;
const MCCTRL_SYSFS_REMOTE_STAGE_TOO_LARGE: c_int = 4;
const MCCTRL_SYSFS_REMOTE_STAGE_SEND: c_int = 5;
const MCCTRL_SYSFS_REMOTE_STAGE_WAIT: c_int = 6;
const MCCTRL_SYSFS_REMOTE_STAGE_RESULT: c_int = 7;

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_packet_handler_body_result(
    os: *mut c_void,
    msg: c_int,
    pid: c_int,
    arg: c_ulong,
    resp_pa: c_ulong,
    work_size: usize,
    alloc: McctrlProcfsWorkAllocFn,
    init_schedule: McctrlProcfsWorkInitScheduleFn,
    alloc_failed: McctrlProcfsAllocFailedFn,
) -> c_int {
    let (Some(alloc), Some(init_schedule), Some(alloc_failed)) =
        (alloc, init_schedule, alloc_failed)
    else {
        return -1;
    };

    let work = alloc(work_size);
    if work.is_null() {
        alloc_failed();
        return -1;
    }

    (*work).os = os;
    (*work).msg = msg;
    (*work).pid = pid;
    (*work).arg = arg;
    (*work).resp_pa = resp_pa;
    init_schedule(work);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_work_main_body_result(
    work: *mut McctrlProcfsWorkPrefix,
    int_size: c_ulong,
    get_index: McctrlProcfsGetIndexFn,
    add_tid: McctrlProcfsEntryFn,
    delete_tid: McctrlProcfsEntryFn,
    os_to_dev: McctrlProcfsOsToDevFn,
    map_memory: McctrlProcfsMapMemoryFn,
    map_virtual: McctrlProcfsMapVirtualFn,
    unmap_virtual: McctrlProcfsUnmapVirtualFn,
    unmap_memory: McctrlProcfsUnmapMemoryFn,
    unknown_work: McctrlProcfsUnknownWorkFn,
    free_work: McctrlProcfsFreeWorkFn,
) -> c_int {
    if work.is_null() {
        return -EINVAL;
    }

    let (Some(get_index), Some(add_tid), Some(delete_tid), Some(os_to_dev), Some(map_memory)) =
        (get_index, add_tid, delete_tid, os_to_dev, map_memory)
    else {
        if let Some(free_work) = free_work {
            free_work(work.cast::<c_void>());
        }
        return -EINVAL;
    };
    let (Some(map_virtual), Some(unmap_virtual), Some(unmap_memory), Some(unknown_work)) =
        (map_virtual, unmap_virtual, unmap_memory, unknown_work)
    else {
        if let Some(free_work) = free_work {
            free_work(work.cast::<c_void>());
        }
        return -EINVAL;
    };
    let Some(free_work) = free_work else {
        return -EINVAL;
    };

    let os = (*work).os;
    match (*work).msg {
        SCD_MSG_PROCFS_TID_CREATE => {
            let osnum = get_index(os);
            add_tid(osnum, (*work).pid, (*work).arg as c_int);

            let dev = os_to_dev(os);
            let phys = map_memory(dev, (*work).resp_pa, int_size);
            let done = map_virtual(dev, phys, int_size, null_mut(), 0).cast::<c_int>();
            *done = 1;
            unmap_virtual(dev, done.cast::<c_void>(), int_size);
            unmap_memory(dev, phys, int_size);
        }
        SCD_MSG_PROCFS_TID_DELETE => {
            let osnum = get_index(os);
            delete_tid(osnum, (*work).pid, (*work).arg as c_int);
        }
        _ => {
            unknown_work((*work).msg, (*work).pid, (*work).arg);
        }
    }

    free_work(work.cast::<c_void>());
    0
}

unsafe fn mcctrl_procfs_find_base_entry_impl(
    osnum: c_int,
    format_mcos: unsafe extern "C" fn(*mut c_char, c_ulong, c_int) -> c_int,
    find_entry: unsafe extern "C" fn(*mut c_void, *const c_char) -> *mut c_void,
) -> *mut c_void {
    let mut name = [NUL; 12];

    format_mcos(name.as_mut_ptr(), name.len() as c_ulong, osnum);
    find_entry(null_mut(), name.as_ptr())
}

unsafe fn mcctrl_procfs_find_pid_entry_impl(
    osnum: c_int,
    pid: c_int,
    format_mcos: unsafe extern "C" fn(*mut c_char, c_ulong, c_int) -> c_int,
    format_decimal: unsafe extern "C" fn(*mut c_char, c_ulong, c_int) -> c_int,
    find_entry: unsafe extern "C" fn(*mut c_void, *const c_char) -> *mut c_void,
) -> *mut c_void {
    let parent = mcctrl_procfs_find_base_entry_impl(osnum, format_mcos, find_entry);
    if parent.is_null() {
        return null_mut();
    }

    let mut name = [NUL; 12];
    format_decimal(name.as_mut_ptr(), name.len() as c_ulong, pid);
    find_entry(parent, name.as_ptr())
}

unsafe fn mcctrl_procfs_find_tid_entry_impl(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    format_mcos: unsafe extern "C" fn(*mut c_char, c_ulong, c_int) -> c_int,
    format_decimal: unsafe extern "C" fn(*mut c_char, c_ulong, c_int) -> c_int,
    find_entry: unsafe extern "C" fn(*mut c_void, *const c_char) -> *mut c_void,
) -> *mut c_void {
    let pid_entry =
        mcctrl_procfs_find_pid_entry_impl(osnum, pid, format_mcos, format_decimal, find_entry);
    if pid_entry.is_null() {
        return null_mut();
    }

    let task_entry = find_entry(pid_entry, PROCFS_TASK_NAME.as_ptr().cast::<c_char>());
    if task_entry.is_null() {
        return null_mut();
    }

    let mut name = [NUL; 12];
    format_decimal(name.as_mut_ptr(), name.len() as c_ulong, tid);
    find_entry(task_entry, name.as_ptr())
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_find_base_entry_body_result(
    osnum: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(find_entry)) = (format_mcos, find_entry) else {
        return null_mut();
    };

    mcctrl_procfs_find_base_entry_impl(osnum, format_mcos, find_entry)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_find_pid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    format_decimal: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(format_decimal), Some(find_entry)) =
        (format_mcos, format_decimal, find_entry)
    else {
        return null_mut();
    };

    mcctrl_procfs_find_pid_entry_impl(osnum, pid, format_mcos, format_decimal, find_entry)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_find_tid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    format_decimal: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(format_decimal), Some(find_entry)) =
        (format_mcos, format_decimal, find_entry)
    else {
        return null_mut();
    };

    mcctrl_procfs_find_tid_entry_impl(osnum, pid, tid, format_mcos, format_decimal, find_entry)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_get_base_entry_body_result(
    osnum: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
    add_entry: McctrlProcfsAddEntryFn,
    set_osnum: McctrlProcfsSetOsnumFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(find_entry), Some(add_entry)) =
        (format_mcos, find_entry, add_entry)
    else {
        return null_mut();
    };

    let mut name = [NUL; 12];
    format_mcos(name.as_mut_ptr(), name.len() as c_ulong, osnum);
    let mut entry = find_entry(null_mut(), name.as_ptr());
    if entry.is_null() {
        entry = add_entry(null_mut(), name.as_ptr(), PROCFS_DIR_MODE_0555);
        if !entry.is_null() {
            let Some(set_osnum) = set_osnum else {
                return null_mut();
            };
            set_osnum(entry, osnum);
        }
    }
    entry
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_get_pid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    format_decimal: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
    add_entry: McctrlProcfsAddEntryFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(format_decimal), Some(find_entry), Some(add_entry)) =
        (format_mcos, format_decimal, find_entry, add_entry)
    else {
        return null_mut();
    };

    let mut name = [NUL; 12];
    format_mcos(name.as_mut_ptr(), name.len() as c_ulong, osnum);
    let parent = find_entry(null_mut(), name.as_ptr());
    if parent.is_null() {
        return null_mut();
    }

    format_decimal(name.as_mut_ptr(), name.len() as c_ulong, pid);
    let mut entry = find_entry(parent, name.as_ptr());
    if entry.is_null() {
        entry = add_entry(parent, name.as_ptr(), PROCFS_DIR_MODE_0555);
    }
    entry
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_get_tid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    format_mcos: McctrlProcfsFormatNameFn,
    format_decimal: McctrlProcfsFormatNameFn,
    find_entry: McctrlProcfsFindEntryFn,
    add_entry: McctrlProcfsAddEntryFn,
) -> *mut c_void {
    let (Some(format_mcos), Some(format_decimal), Some(find_entry), Some(add_entry)) =
        (format_mcos, format_decimal, find_entry, add_entry)
    else {
        return null_mut();
    };

    let mut name = [NUL; 12];
    format_mcos(name.as_mut_ptr(), name.len() as c_ulong, osnum);
    let mut parent = find_entry(null_mut(), name.as_ptr());
    if parent.is_null() {
        return null_mut();
    }

    format_decimal(name.as_mut_ptr(), name.len() as c_ulong, pid);
    parent = find_entry(parent, name.as_ptr());
    if parent.is_null() {
        return null_mut();
    }

    parent = find_entry(parent, PROCFS_TASK_NAME.as_ptr().cast::<c_char>());
    if parent.is_null() {
        return null_mut();
    }

    format_decimal(name.as_mut_ptr(), name.len() as c_ulong, tid);
    let mut entry = find_entry(parent, name.as_ptr());
    if entry.is_null() {
        entry = add_entry(parent, name.as_ptr(), PROCFS_DIR_MODE_0555);
    }
    entry
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_add_tid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    get_cred: McctrlProcfsGetCredFn,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    find_pid: McctrlProcfsOsPidLookupFn,
    get_pid: McctrlProcfsOsPidLookupFn,
    add_pid_entries: McctrlProcfsAddEntriesCredFn,
    add_tid: McctrlProcfsAddTidCredFn,
) -> c_int {
    let (
        Some(get_cred),
        Some(lock),
        Some(unlock),
        Some(find_pid),
        Some(get_pid),
        Some(add_pid_entries),
        Some(add_tid),
    ) = (
        get_cred,
        lock,
        unlock,
        find_pid,
        get_pid,
        add_pid_entries,
        add_tid,
    )
    else {
        return -EINVAL;
    };

    let cred = get_cred(pid);
    if cred.is_null() {
        return 0;
    }

    lock();
    let mut parent = find_pid(osnum, pid);
    if parent.is_null() {
        parent = get_pid(osnum, pid);
        if !parent.is_null() {
            add_pid_entries(parent, cred);
        }
    }
    add_tid(osnum, pid, tid, cred);
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_add_tid_with_cred_body_result(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    cred: *mut c_void,
    get_tid: McctrlProcfsOsPidTidLookupFn,
    add_tid_entries: McctrlProcfsAddEntriesCredFn,
    find_exe_data: McctrlProcfsFindExeDataFn,
    add_exe_link: McctrlProcfsAddExeLinkFn,
) -> c_int {
    let (Some(get_tid), Some(add_tid_entries), Some(find_exe_data), Some(add_exe_link)) =
        (get_tid, add_tid_entries, find_exe_data, add_exe_link)
    else {
        return -EINVAL;
    };

    let parent = get_tid(osnum, pid, tid);
    if parent.is_null() {
        return 0;
    }

    add_tid_entries(parent, cred);
    let exe_data = find_exe_data(parent);
    if !exe_data.is_null() {
        add_exe_link(parent, exe_data, cred);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_add_pid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    get_cred: McctrlProcfsGetCredFn,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    get_pid: McctrlProcfsOsPidLookupFn,
    add_pid_entries: McctrlProcfsAddEntriesCredFn,
    add_tid: McctrlProcfsAddTidCredFn,
) -> c_int {
    let (
        Some(get_cred),
        Some(lock),
        Some(unlock),
        Some(get_pid),
        Some(add_pid_entries),
        Some(add_tid),
    ) = (get_cred, lock, unlock, get_pid, add_pid_entries, add_tid)
    else {
        return -EINVAL;
    };

    let cred = get_cred(pid);
    if cred.is_null() {
        return 0;
    }

    lock();
    let parent = get_pid(osnum, pid);
    add_pid_entries(parent, cred);
    add_tid(osnum, pid, pid, cred);
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_delete_tid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    tid: c_int,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    find_tid: McctrlProcfsOsPidTidLookupFn,
    delete_entry: McctrlProcfsDeleteEntryFn,
) -> c_int {
    let (Some(lock), Some(unlock), Some(find_tid), Some(delete_entry)) =
        (lock, unlock, find_tid, delete_entry)
    else {
        return -EINVAL;
    };

    lock();
    let entry = find_tid(osnum, pid, tid);
    if !entry.is_null() {
        delete_entry(entry);
    }
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_delete_pid_entry_body_result(
    osnum: c_int,
    pid: c_int,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    find_pid: McctrlProcfsOsPidLookupFn,
    delete_entry: McctrlProcfsDeleteEntryFn,
) -> c_int {
    let (Some(lock), Some(unlock), Some(find_pid), Some(delete_entry)) =
        (lock, unlock, find_pid, delete_entry)
    else {
        return -EINVAL;
    };

    lock();
    let entry = find_pid(osnum, pid);
    if !entry.is_null() {
        delete_entry(entry);
    }
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_init_body_result(
    osnum: c_int,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    get_base: McctrlProcfsOsLookupFn,
    add_base_entries: McctrlProcfsAddEntriesFn,
) -> c_int {
    let (Some(lock), Some(unlock), Some(get_base), Some(add_base_entries)) =
        (lock, unlock, get_base, add_base_entries)
    else {
        return -EINVAL;
    };

    lock();
    let parent = get_base(osnum);
    add_base_entries(parent);
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_exit_body_result(
    osnum: c_int,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    find_base: McctrlProcfsOsLookupFn,
    delete_entry: McctrlProcfsDeleteEntryFn,
) -> c_int {
    let (Some(lock), Some(unlock), Some(find_base), Some(delete_entry)) =
        (lock, unlock, find_base, delete_entry)
    else {
        return -EINVAL;
    };

    lock();
    let entry = find_base(osnum);
    if !entry.is_null() {
        delete_entry(entry);
    }
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_exe_link_body_result(
    osnum: c_int,
    pid: c_int,
    path: *const c_char,
    lock: McctrlProcfsLockFn,
    unlock: McctrlProcfsLockFn,
    find_pid: McctrlProcfsOsPidLookupFn,
    add_pid_exe: McctrlProcfsAddPidExeFn,
    store_exe_path: McctrlProcfsStoreExePathFn,
    add_task_exe_links: McctrlProcfsAddTaskExeLinksFn,
) -> c_int {
    let (
        Some(lock),
        Some(unlock),
        Some(find_pid),
        Some(add_pid_exe),
        Some(store_exe_path),
        Some(add_task_exe_links),
    ) = (
        lock,
        unlock,
        find_pid,
        add_pid_exe,
        store_exe_path,
        add_task_exe_links,
    )
    else {
        return -EINVAL;
    };

    lock();
    let parent = find_pid(osnum, pid);
    if !parent.is_null() {
        let entry = add_pid_exe(parent, path);
        if !entry.is_null() {
            store_exe_path(entry, path);
            add_task_exe_links(parent, path);
        }
    }
    unlock();
    0
}

unsafe fn c_strlen(ptr: *const c_char) -> usize {
    if ptr.is_null() {
        return 0;
    }

    let mut len = 0usize;
    while read_volatile(ptr.add(len)) != 0 {
        len += 1;
    }
    len
}

unsafe fn mcctrl_procfs_pid_from_path(path: *const c_char) -> c_int {
    if path.is_null() {
        return -1;
    }

    let mut pos = 0usize;
    while c_byte(path, pos) != 0 && c_byte(path, pos) != b'/' {
        pos += 1;
    }
    if c_byte(path, pos) != b'/' {
        return -1;
    }
    pos += 1;

    let mut pid = -1 as c_int;
    if parse_i32_at(path, &mut pos, &mut pid as *mut c_int) {
        pid
    } else {
        -1
    }
}

unsafe fn mcctrl_procfs_mcos_from_path(path: *const c_char, osnum_out: *mut c_int) -> bool {
    if path.is_null() || osnum_out.is_null() || !starts_with(path, b"mcos") {
        return false;
    }

    let mut pos = 4usize;
    if !parse_i32_at(path, &mut pos, osnum_out) {
        return false;
    }
    c_byte(path, pos) == b'/'
}

unsafe fn mcctrl_procfs_read_write_cleanup_result(
    ret: c_long,
    ppd: *mut c_void,
    kern_buffer: *mut c_void,
    order: c_int,
    read: *mut c_void,
    put_per_proc: unsafe extern "C" fn(*mut c_void),
    free_pages: unsafe extern "C" fn(*mut c_void, c_int),
    free_fn: unsafe extern "C" fn(*mut c_void),
) -> c_long {
    if !ppd.is_null() {
        put_per_proc(ppd);
    }
    if !kern_buffer.is_null() {
        free_pages(kern_buffer, order);
    }
    if !read.is_null() {
        free_fn(read);
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_lseek_body_result(
    current_pos: c_long,
    offset: c_long,
    orig: c_int,
    new_pos: *mut c_long,
) -> c_long {
    if new_pos.is_null() {
        return -EINVAL as c_long;
    }

    let pos = match orig {
        0 => offset,
        1 => current_pos.wrapping_add(offset),
        _ => return -EINVAL as c_long,
    };
    *new_pos = pos;
    pos
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_buff_open_body_result(
    entry: *mut c_void,
    file: *mut c_void,
    path_size: c_ulong,
    info_base_size: c_ulong,
    pa_null: c_ulong,
    entry_osnum: McctrlProcfsEntryOsnumFn,
    lookup_os: McctrlProcfsOsLookupFn,
    alloc: McctrlProcfsAllocFn,
    free_fn: McctrlProcfsFreeFn,
    get_path: McctrlProcfsGetPathFn,
    init_info: McctrlProcfsInitBufferInfoFn,
    set_file_private: McctrlProcfsSetFilePrivateFn,
) -> c_int {
    let (
        Some(entry_osnum),
        Some(lookup_os),
        Some(alloc),
        Some(free_fn),
        Some(get_path),
        Some(init_info),
        Some(set_file_private),
    ) = (
        entry_osnum,
        lookup_os,
        alloc,
        free_fn,
        get_path,
        init_info,
        set_file_private,
    )
    else {
        return -EINVAL;
    };

    let os = lookup_os(entry_osnum(entry));
    if os.is_null() {
        return -EINVAL;
    }

    let path_buf = alloc(path_size as usize) as *mut c_char;
    if path_buf.is_null() {
        return -ENOMEM;
    }

    let path = get_path(entry, path_buf, path_size);
    let pid = mcctrl_procfs_pid_from_path(path);
    let info_size = (info_base_size as usize)
        .wrapping_add(c_strlen(path))
        .wrapping_add(1);
    let info = alloc(info_size);
    if info.is_null() {
        free_fn(path_buf.cast::<c_void>());
        return -ENOMEM;
    }

    init_info(info, os, pid, pa_null, path);
    set_file_private(file, info);
    free_fn(path_buf.cast::<c_void>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_buff_release_body_result(
    file: *mut c_void,
    pa_null: c_ulong,
    get_file_private: McctrlProcfsGetFilePrivateFn,
    set_file_private: McctrlProcfsSetFilePrivateFn,
    info_top_pa: McctrlProcfsInfoTopPaFn,
    info_os: McctrlProcfsInfoOsFn,
    alloc_read: McctrlProcfsAllocReadFn,
    init_release_read: McctrlProcfsInitReleaseReadFn,
    send_release: McctrlProcfsSendReleaseFn,
    read_ret: McctrlProcfsReadRetFn,
    free_fn: McctrlProcfsFreeFn,
    timeout_log: McctrlProcfsLogFn,
) -> c_int {
    let (
        Some(get_file_private),
        Some(set_file_private),
        Some(info_top_pa),
        Some(info_os),
        Some(alloc_read),
        Some(init_release_read),
        Some(send_release),
        Some(read_ret),
        Some(free_fn),
        Some(timeout_log),
    ) = (
        get_file_private,
        set_file_private,
        info_top_pa,
        info_os,
        alloc_read,
        init_release_read,
        send_release,
        read_ret,
        free_fn,
        timeout_log,
    )
    else {
        return -EINVAL;
    };

    let info = get_file_private(file);
    if info.is_null() {
        return -EIO;
    }

    set_file_private(file, null_mut());
    let mut rc = 0;
    if info_top_pa(info) != pa_null {
        let mut read = alloc_read();
        if read.is_null() {
            free_fn(info);
            return -ENOMEM;
        }

        init_release_read(read, info_top_pa(info));
        let mut do_free = 0 as c_int;
        let mut ret = send_release(info_os(info), read, &mut do_free as *mut c_int);
        if do_free == 0 && ret >= 0 {
            ret = -EIO;
        }
        if ret < 0 {
            rc = ret;
            if ret == -ETIME {
                timeout_log();
            } else if ret == -ERESTARTSYS {
                rc = -ERESTART;
            }
            if do_free == 0 {
                read = null_mut();
            }
            if !read.is_null() {
                free_fn(read);
            }
            free_fn(info);
            return rc;
        }

        let rret = read_ret(read);
        if rret < 0 {
            rc = rret;
        } else {
            rc = 0;
        }
        free_fn(read);
    }

    free_fn(info);
    rc
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_buff_read_body_result(
    file: *mut c_void,
    ubuf: *mut c_void,
    nbytes: c_ulong,
    ppos: *mut c_long,
    pa_null: c_ulong,
    page_size: c_ulong,
    get_file_private: McctrlProcfsGetFilePrivateFn,
    info_os: McctrlProcfsInfoOsFn,
    info_pid: McctrlProcfsInfoPidFn,
    info_top_pa: McctrlProcfsInfoTopPaFn,
    info_cur_pa: McctrlProcfsInfoCurPaFn,
    info_path: McctrlProcfsInfoPathFn,
    info_set_top_cur: McctrlProcfsInfoSetPaFn,
    info_set_cur: McctrlProcfsInfoSetCurPaFn,
    get_usrdata: McctrlProcfsGetUsrdataFn,
    get_per_proc: McctrlProcfsGetPerProcFn,
    put_per_proc: McctrlProcfsPutPerProcFn,
    ppd_cpu: McctrlProcfsPpdCpuFn,
    alloc_read: McctrlProcfsAllocReadFn,
    init_request_read: McctrlProcfsInitRequestReadFn,
    send_request: McctrlProcfsSendRequestFn,
    read_ret: McctrlProcfsReadRetFn,
    read_pbuf: McctrlProcfsReadPbufFn,
    free_fn: McctrlProcfsFreeFn,
    os_to_dev: McctrlProcfsOsToDevFn,
    map_memory: McctrlProcfsMapMemoryFn,
    map_virtual: McctrlProcfsMapVirtualFn,
    unmap_virtual: McctrlProcfsUnmapVirtualFn,
    unmap_memory: McctrlProcfsUnmapMemoryFn,
    buffer_pos: McctrlProcfsBufferFieldFn,
    buffer_size: McctrlProcfsBufferFieldFn,
    buffer_next_pa: McctrlProcfsBufferFieldFn,
    copy_to_user: McctrlProcfsCopyBufferToUserFn,
    no_usrdata_log: McctrlProcfsLogFn,
    no_ppd_log: McctrlProcfsPidLogFn,
    timeout_log: McctrlProcfsLogFn,
) -> c_long {
    let (
        Some(get_file_private),
        Some(info_os),
        Some(info_pid),
        Some(info_top_pa),
        Some(info_cur_pa),
        Some(info_path),
        Some(info_set_top_cur),
        Some(info_set_cur),
        Some(get_usrdata),
        Some(get_per_proc),
        Some(put_per_proc),
        Some(ppd_cpu),
        Some(alloc_read),
        Some(init_request_read),
        Some(send_request),
        Some(read_ret),
        Some(read_pbuf),
        Some(free_fn),
        Some(os_to_dev),
        Some(map_memory),
        Some(map_virtual),
        Some(unmap_virtual),
        Some(unmap_memory),
        Some(buffer_pos),
        Some(buffer_size),
        Some(buffer_next_pa),
        Some(copy_to_user),
        Some(no_usrdata_log),
        Some(no_ppd_log),
        Some(timeout_log),
    ) = (
        get_file_private,
        info_os,
        info_pid,
        info_top_pa,
        info_cur_pa,
        info_path,
        info_set_top_cur,
        info_set_cur,
        get_usrdata,
        get_per_proc,
        put_per_proc,
        ppd_cpu,
        alloc_read,
        init_request_read,
        send_request,
        read_ret,
        read_pbuf,
        free_fn,
        os_to_dev,
        map_memory,
        map_virtual,
        unmap_virtual,
        unmap_memory,
        buffer_pos,
        buffer_size,
        buffer_next_pa,
        copy_to_user,
        no_usrdata_log,
        no_ppd_log,
        timeout_log,
    )
    else {
        return -EINVAL as c_long;
    };

    if ppos.is_null() {
        return -EINVAL as c_long;
    }

    let mut pos = *ppos;
    if nbytes == 0 || pos < 0 {
        return 0;
    }

    let info = get_file_private(file);
    if info.is_null() {
        return -EIO as c_long;
    }

    let os = info_os(info);
    let mut user = ubuf.cast::<u8>();
    let mut done = false;
    let mut copied: c_long = 0;

    if info_top_pa(info) == pa_null {
        let pid = info_pid(info);
        let usrdata = get_usrdata(os);
        if usrdata.is_null() {
            no_usrdata_log();
            return -EINVAL as c_long;
        }

        let mut ppd = null_mut();
        if pid > 0 {
            ppd = get_per_proc(usrdata, pid);
            if ppd.is_null() {
                no_ppd_log(pid);
                return -EINVAL as c_long;
            }
        }

        let mut read = alloc_read();
        if read.is_null() {
            if !ppd.is_null() {
                put_per_proc(ppd);
            }
            *ppos = pos;
            return -ENOMEM as c_long;
        }

        init_request_read(read, pa_null, info_path(info));
        let mut do_free = 0 as c_int;
        let cpu = if pid > 0 { ppd_cpu(ppd) } else { 0 };
        let mut ret = send_request(os, cpu, pid, read, &mut do_free as *mut c_int);
        if do_free == 0 && ret >= 0 {
            ret = -EIO;
        }

        if ret < 0 {
            copied = ret as c_long;
            if ret == -ETIME {
                timeout_log();
            } else if ret == -ERESTARTSYS {
                copied = -ERESTART as c_long;
            }
            if do_free == 0 {
                read = null_mut();
            }
            if !ppd.is_null() {
                put_per_proc(ppd);
            }
            if !read.is_null() {
                free_fn(read);
            }
            *ppos = pos;
            return copied;
        }

        let request_ret = read_ret(read);
        if request_ret < 0 {
            if !ppd.is_null() {
                put_per_proc(ppd);
            }
            free_fn(read);
            *ppos = pos;
            return request_ret as c_long;
        }

        let pbuf = read_pbuf(read);
        info_set_top_cur(info, pbuf, pbuf);
        if !ppd.is_null() {
            put_per_proc(ppd);
        }
        free_fn(read);
    }

    if info_cur_pa(info) == pa_null {
        info_set_cur(info, info_top_pa(info));
    }

    while !done && info_cur_pa(info) != pa_null {
        let cur_pa = info_cur_pa(info);
        let dev = os_to_dev(os);
        let phys = map_memory(dev, cur_pa, page_size);
        let buf = map_virtual(dev, phys, page_size, null_mut(), 0);
        let bstart = buffer_pos(buf) as c_long;
        let bend = bstart.wrapping_add(buffer_size(buf) as c_long);

        if pos < bstart {
            info_set_cur(info, info_top_pa(info));
        } else if pos >= bend {
            info_set_cur(info, buffer_next_pa(buf));
        } else {
            let bpos = (pos - bstart) as c_ulong;
            let mut bsize = (bend - pos) as c_ulong;
            let remaining = nbytes.wrapping_sub(copied as c_ulong);
            if bsize > remaining {
                bsize = remaining;
            }

            if copy_to_user(user.cast::<c_void>(), buf, bpos, bsize) != 0 {
                done = true;
                pos = *ppos;
                copied = -EFAULT as c_long;
            } else {
                user = user.add(bsize as usize);
                pos = pos.wrapping_add(bsize as c_long);
                copied = copied.wrapping_add(bsize as c_long);
                if copied as c_ulong == nbytes {
                    done = true;
                }
            }
        }

        unmap_virtual(dev, buf, page_size);
        unmap_memory(dev, phys, page_size);
    }

    *ppos = pos;
    copied
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_procfs_read_write_body_result(
    entry: *mut c_void,
    ubuf: *mut c_void,
    nbytes: c_ulong,
    ppos: *mut c_long,
    read_write: c_int,
    path_buf: *mut c_char,
    path_size: c_ulong,
    page_size: c_ulong,
    entry_osnum: McctrlProcfsEntryOsnumFn,
    get_path: McctrlProcfsGetPathFn,
    lookup_os: McctrlProcfsOsLookupFn,
    get_usrdata: McctrlProcfsGetUsrdataFn,
    get_per_proc: McctrlProcfsGetPerProcFn,
    put_per_proc: McctrlProcfsPutPerProcFn,
    ppd_cpu: McctrlProcfsPpdCpuFn,
    get_order: McctrlProcfsGetOrderFn,
    alloc_pages: McctrlProcfsAllocPagesFn,
    free_pages: McctrlProcfsFreePagesFn,
    virt_to_phys: McctrlProcfsVirtToPhysFn,
    alloc_read: McctrlProcfsAllocReadFn,
    init_read: McctrlProcfsInitReadWriteReadFn,
    send_request: McctrlProcfsSendRequestFn,
    read_ret: McctrlProcfsReadRetFn,
    read_eof: McctrlProcfsReadEofFn,
    free_fn: McctrlProcfsFreeFn,
    copy_to_user: McctrlProcfsCopyKernelToUserFn,
    bad_osnum_log: McctrlProcfsLogFn,
    osnum_mismatch_log: McctrlProcfsOsnumMismatchLogFn,
    no_os_log: McctrlProcfsOsnumLogFn,
    no_usrdata_log: McctrlProcfsOsnumLogFn,
    no_ppd_log: McctrlProcfsPidLogFn,
    alloc_error_log: McctrlProcfsLogFn,
    copy_error_log: McctrlProcfsLogFn,
    timeout_log: McctrlProcfsLogFn,
) -> c_long {
    let (
        Some(entry_osnum),
        Some(get_path),
        Some(lookup_os),
        Some(get_usrdata),
        Some(get_per_proc),
        Some(put_per_proc),
        Some(ppd_cpu),
        Some(get_order),
        Some(alloc_pages),
        Some(free_pages),
        Some(virt_to_phys),
        Some(alloc_read),
        Some(init_read),
        Some(send_request),
        Some(read_ret),
        Some(read_eof),
        Some(free_fn),
        Some(copy_to_user),
        Some(bad_osnum_log),
        Some(osnum_mismatch_log),
        Some(no_os_log),
        Some(no_usrdata_log),
        Some(no_ppd_log),
        Some(alloc_error_log),
        Some(copy_error_log),
        Some(timeout_log),
    ) = (
        entry_osnum,
        get_path,
        lookup_os,
        get_usrdata,
        get_per_proc,
        put_per_proc,
        ppd_cpu,
        get_order,
        alloc_pages,
        free_pages,
        virt_to_phys,
        alloc_read,
        init_read,
        send_request,
        read_ret,
        read_eof,
        free_fn,
        copy_to_user,
        bad_osnum_log,
        osnum_mismatch_log,
        no_os_log,
        no_usrdata_log,
        no_ppd_log,
        alloc_error_log,
        copy_error_log,
        timeout_log,
    )
    else {
        return -EINVAL as c_long;
    };

    if ppos.is_null() {
        return -EINVAL as c_long;
    }

    let mut count = nbytes;
    let mut offset = *ppos;
    if count == 0 || offset < 0 {
        return 0;
    }

    let path = get_path(entry, path_buf, path_size);
    let mut osnum = 0 as c_int;
    if !mcctrl_procfs_mcos_from_path(path, &mut osnum as *mut c_int) {
        bad_osnum_log();
        return -EINVAL as c_long;
    }

    let entry_osnum_value = entry_osnum(entry);
    if osnum != entry_osnum_value {
        osnum_mismatch_log(osnum, entry_osnum_value);
        return -EINVAL as c_long;
    }

    let pid = mcctrl_procfs_pid_from_path(path);
    let os = lookup_os(osnum);
    if os.is_null() {
        no_os_log(osnum);
        return -EINVAL as c_long;
    }

    let usrdata = get_usrdata(os);
    if usrdata.is_null() {
        no_usrdata_log(osnum);
        return -EINVAL as c_long;
    }

    let mut ppd = null_mut();
    if pid > 0 {
        ppd = get_per_proc(usrdata, pid);
        if ppd.is_null() {
            no_ppd_log(pid);
            return -EINVAL as c_long;
        }
    }

    let mut order = get_order(count);
    let mut kern_buffer = null_mut();
    while order >= 0 {
        kern_buffer = alloc_pages(order);
        if !kern_buffer.is_null() {
            break;
        }
        order -= 1;
    }

    if kern_buffer.is_null() {
        alloc_error_log();
        return mcctrl_procfs_read_write_cleanup_result(
            -ENOMEM as c_long,
            ppd,
            kern_buffer,
            order,
            null_mut(),
            put_per_proc,
            free_pages,
            free_fn,
        );
    }

    let copy_size = page_size.wrapping_mul(1usize.wrapping_shl(order as u32) as c_ulong);
    let pbuf = virt_to_phys(kern_buffer);
    let mut read = alloc_read();
    if read.is_null() {
        return mcctrl_procfs_read_write_cleanup_result(
            -ENOMEM as c_long,
            ppd,
            kern_buffer,
            order,
            read,
            put_per_proc,
            free_pages,
            free_fn,
        );
    }

    let mut copied = 0 as c_long;
    let mut user = ubuf.cast::<u8>();
    while count > 0 {
        let this_len = if count < copy_size { count } else { copy_size };
        let cpu = if pid > 0 { ppd_cpu(ppd) } else { 0 };
        let mut do_free = 0 as c_int;
        init_read(read, pbuf, offset, this_len as c_int, read_write, path);
        let mut ret = send_request(os, cpu, pid, read, &mut do_free as *mut c_int);
        if do_free == 0 && ret >= 0 {
            ret = -EIO;
        }
        if ret < 0 {
            let mut result = ret as c_long;
            if ret == -ETIME {
                timeout_log();
            } else if ret == -ERESTARTSYS {
                result = -ERESTART as c_long;
            }
            if do_free == 0 {
                read = null_mut();
            }
            return mcctrl_procfs_read_write_cleanup_result(
                result,
                ppd,
                kern_buffer,
                order,
                read,
                put_per_proc,
                free_pages,
                free_fn,
            );
        }

        let rret = read_ret(read);
        if rret > 0 {
            if read_write == 0
                && copy_to_user(user.cast::<c_void>(), kern_buffer, rret as c_ulong) != 0
            {
                copy_error_log();
                return mcctrl_procfs_read_write_cleanup_result(
                    -EFAULT as c_long,
                    ppd,
                    kern_buffer,
                    order,
                    read,
                    put_per_proc,
                    free_pages,
                    free_fn,
                );
            }

            user = user.add(rret as usize);
            offset = offset.wrapping_add(rret as c_long);
            copied = copied.wrapping_add(rret as c_long);
            count = count.wrapping_sub(rret as c_ulong);
        } else {
            if copied == 0 {
                copied = rret as c_long;
            }
            break;
        }

        if read_eof(read) != 0 {
            break;
        }
    }

    *ppos = offset;
    mcctrl_procfs_read_write_cleanup_result(
        copied,
        ppd,
        kern_buffer,
        order,
        read,
        put_per_proc,
        free_pages,
        free_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_packet_handler_body_result(
    os: *mut c_void,
    msg: c_int,
    err: c_int,
    arg1: c_long,
    arg2: c_long,
    work_size: usize,
    alloc: McctrlSysfsWorkAllocFn,
    init_schedule: McctrlSysfsWorkInitScheduleFn,
    alloc_failed: McctrlSysfsAllocFailedFn,
) -> c_int {
    let (Some(alloc), Some(init_schedule), Some(alloc_failed)) =
        (alloc, init_schedule, alloc_failed)
    else {
        return -EINVAL;
    };

    let work = alloc(work_size);
    if work.is_null() {
        alloc_failed();
        return -ENOMEM;
    }

    (*work).os = os;
    (*work).msg = msg;
    (*work).err = err;
    (*work).arg1 = arg1;
    (*work).arg2 = arg2;
    init_schedule(work);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_work_main_body_result(
    work: *mut McctrlSysfsWorkPrefix,
    req_setup: McctrlSysfsRequestFn,
    req_create: McctrlSysfsRequestFn,
    req_mkdir: McctrlSysfsRequestFn,
    req_symlink: McctrlSysfsRequestFn,
    req_lookup: McctrlSysfsRequestFn,
    req_unlink: McctrlSysfsRequestFn,
    resp_show: McctrlSysfsResponseFn,
    resp_store: McctrlSysfsResponseFn,
    resp_release: McctrlSysfsReleaseResponseFn,
    unknown_work: McctrlSysfsUnknownWorkFn,
    free_work: McctrlSysfsFreeWorkFn,
) -> c_int {
    if work.is_null() {
        return -EINVAL;
    }

    let Some(free_work) = free_work else {
        return -EINVAL;
    };

    let os = (*work).os;
    let result = match (*work).msg {
        SCD_MSG_SYSFS_REQ_SETUP => req_setup.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_REQ_CREATE => req_create.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_REQ_MKDIR => req_mkdir.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_REQ_SYMLINK => req_symlink.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_REQ_LOOKUP => req_lookup.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_REQ_UNLINK => req_unlink.map(|f| f(os, (*work).arg1)),
        SCD_MSG_SYSFS_RESP_SHOW => {
            resp_show.map(|f| f(os, (*work).arg1 as *mut c_void, (*work).arg2))
        }
        SCD_MSG_SYSFS_RESP_STORE => {
            resp_store.map(|f| f(os, (*work).arg1 as *mut c_void, (*work).arg2))
        }
        SCD_MSG_SYSFS_RESP_RELEASE => {
            resp_release.map(|f| f(os, (*work).arg1 as *mut c_void, (*work).err))
        }
        _ => unknown_work.map(|f| f((*work).msg, os, (*work).arg1, (*work).arg2)),
    };

    let ret = if result.is_some() { 0 } else { -EINVAL };
    free_work(work.cast::<c_void>());
    ret
}

#[inline(always)]
unsafe fn mcctrl_sysfs_remote_stage(stage_out: *mut c_int, stage: c_int) {
    if !stage_out.is_null() {
        *stage_out = stage;
    }
}

#[allow(clippy::too_many_arguments)]
unsafe fn mcctrl_sysfs_remote_common_body_result(
    node: *mut c_void,
    buf: *mut c_void,
    bufsize: usize,
    sysfs_buf: *mut c_void,
    sysfs_bufsize: usize,
    sysfs_os: *mut c_void,
    sem: *mut c_void,
    req: *mut c_void,
    client_ops: c_long,
    client_instance: c_long,
    is_store: bool,
    stage_out: *mut c_int,
    down: McctrlSysfsSemDownFn,
    up: McctrlSysfsSemUpFn,
    wait_ready: McctrlSysfsWaitReadyFn,
    set_busy: McctrlSysfsSetBusyFn,
    send: McctrlSysfsSendFn,
    req_lresult: McctrlSysfsReqResultFn,
    copy: McctrlSysfsLocalCopyFn,
) -> isize {
    let (Some(down), Some(up), Some(wait_ready), Some(set_busy), Some(send), Some(req_lresult)) =
        (down, up, wait_ready, set_busy, send, req_lresult)
    else {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_RESULT);
        return -(EINVAL as isize);
    };
    let Some(copy) = copy else {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_RESULT);
        return -(EINVAL as isize);
    };

    mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_OK);

    if sysfs_buf.is_null() {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_NOT_INIT);
        return if is_store { -(ENOSPC as isize) } else { 0 };
    }

    let mut error = down(sem);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_DOWN);
        return error as isize;
    }

    error = wait_ready(req);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_WAIT0);
        up(sem);
        return -(EINTR as isize);
    }

    if is_store {
        if bufsize > sysfs_bufsize {
            mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_TOO_LARGE);
            up(sem);
            return -(ENOSPC as isize);
        }
        copy(sysfs_buf, buf.cast_const(), bufsize);
    }

    let msg = if is_store {
        SCD_MSG_SYSFS_REQ_STORE
    } else {
        SCD_MSG_SYSFS_REQ_SHOW
    };
    let packet_err = if is_store { bufsize as c_int } else { 0 };

    set_busy(req, 1);
    error = send(
        sysfs_os,
        0,
        msg,
        node as c_long,
        client_ops,
        client_instance,
        packet_err,
    );
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_SEND);
        up(sem);
        return error as isize;
    }

    error = wait_ready(req);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_WAIT);
        up(sem);
        return -(EINTR as isize);
    }

    let ssize = req_lresult(req) as isize;
    if ssize < 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_RESULT);
        up(sem);
        return ssize;
    }

    if !is_store && ssize > 0 {
        copy(buf, sysfs_buf.cast_const(), ssize as usize);
    }

    up(sem);
    ssize
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcctrl_sysfs_remote_show_body_result(
    node: *mut c_void,
    buf: *mut c_void,
    bufsize: usize,
    sysfs_buf: *mut c_void,
    sysfs_os: *mut c_void,
    sem: *mut c_void,
    req: *mut c_void,
    client_ops: c_long,
    client_instance: c_long,
    stage_out: *mut c_int,
    down: McctrlSysfsSemDownFn,
    up: McctrlSysfsSemUpFn,
    wait_ready: McctrlSysfsWaitReadyFn,
    set_busy: McctrlSysfsSetBusyFn,
    send: McctrlSysfsSendFn,
    req_lresult: McctrlSysfsReqResultFn,
    copy: McctrlSysfsLocalCopyFn,
) -> isize {
    mcctrl_sysfs_remote_common_body_result(
        node,
        buf,
        bufsize,
        sysfs_buf,
        0,
        sysfs_os,
        sem,
        req,
        client_ops,
        client_instance,
        false,
        stage_out,
        down,
        up,
        wait_ready,
        set_busy,
        send,
        req_lresult,
        copy,
    )
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcctrl_sysfs_remote_store_body_result(
    node: *mut c_void,
    buf: *const c_void,
    bufsize: usize,
    sysfs_buf: *mut c_void,
    sysfs_bufsize: usize,
    sysfs_os: *mut c_void,
    sem: *mut c_void,
    req: *mut c_void,
    client_ops: c_long,
    client_instance: c_long,
    stage_out: *mut c_int,
    down: McctrlSysfsSemDownFn,
    up: McctrlSysfsSemUpFn,
    wait_ready: McctrlSysfsWaitReadyFn,
    set_busy: McctrlSysfsSetBusyFn,
    send: McctrlSysfsSendFn,
    req_lresult: McctrlSysfsReqResultFn,
    copy: McctrlSysfsLocalCopyFn,
) -> isize {
    mcctrl_sysfs_remote_common_body_result(
        node,
        buf.cast_mut(),
        bufsize,
        sysfs_buf,
        sysfs_bufsize,
        sysfs_os,
        sem,
        req,
        client_ops,
        client_instance,
        true,
        stage_out,
        down,
        up,
        wait_ready,
        set_busy,
        send,
        req_lresult,
        copy,
    )
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn mcctrl_sysfs_remote_release_body_result(
    node: *mut c_void,
    node_type: c_int,
    sysfs_buf: *mut c_void,
    sysfs_os: *mut c_void,
    sem: *mut c_void,
    req: *mut c_void,
    client_ops: c_long,
    client_instance: c_long,
    snt_file: c_int,
    stage_out: *mut c_int,
    down: McctrlSysfsSemDownFn,
    up: McctrlSysfsSemUpFn,
    wait_ready: McctrlSysfsWaitReadyFn,
    set_busy: McctrlSysfsSetBusyFn,
    send: McctrlSysfsSendFn,
) -> c_int {
    let (Some(down), Some(up), Some(wait_ready), Some(set_busy), Some(send)) =
        (down, up, wait_ready, set_busy, send)
    else {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_RESULT);
        return -EINVAL;
    };

    mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_OK);

    if node_type != snt_file || client_ops == 0 || sysfs_buf.is_null() {
        return 0;
    }

    let mut error = down(sem);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_DOWN);
        return error;
    }

    error = wait_ready(req);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_WAIT0);
        up(sem);
        return -EINTR;
    }

    set_busy(req, 1);
    error = send(
        sysfs_os,
        0,
        SCD_MSG_SYSFS_REQ_RELEASE,
        node as c_long,
        client_ops,
        client_instance,
        0,
    );
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_SEND);
        up(sem);
        return error;
    }

    error = wait_ready(req);
    if error != 0 {
        mcctrl_sysfs_remote_stage(stage_out, MCCTRL_SYSFS_REMOTE_STAGE_WAIT);
        up(sem);
        return -EINTR;
    }

    up(sem);
    0
}

fn mcctrl_sysfs_special_kind(client_ops: c_long) -> c_int {
    match client_ops as usize {
        SYSFS_SNOOPING_OPS_D32_VALUE
        | SYSFS_SNOOPING_OPS_D64_VALUE
        | SYSFS_SNOOPING_OPS_U32_VALUE
        | SYSFS_SNOOPING_OPS_U64_VALUE
        | SYSFS_SNOOPING_OPS_S_VALUE
        | SYSFS_SNOOPING_OPS_U32K_VALUE => 1,
        SYSFS_SNOOPING_OPS_PBL_VALUE | SYSFS_SNOOPING_OPS_PB_VALUE => 2,
        _ => 0,
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_local_show_body_result(
    instance: *mut c_void,
    buf: *mut c_void,
    bufsize: usize,
    page_size: usize,
    get_client_ops: McctrlSysfsNodeLongFn,
    get_client_instance: McctrlSysfsNodeLongFn,
) -> isize {
    let (Some(get_client_ops), Some(get_client_instance)) = (get_client_ops, get_client_instance)
    else {
        return -(EINVAL as isize);
    };

    let client_ops = get_client_ops(instance) as *mut SysfsmOps;
    if client_ops.is_null() {
        return -(ENOSPC as isize);
    }

    match (*client_ops).show {
        Some(show) => show(
            client_ops,
            get_client_instance(instance) as *mut c_void,
            buf,
            page_size,
        ),
        None => {
            let _ = bufsize;
            -(ENOSPC as isize)
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_local_store_body_result(
    instance: *mut c_void,
    buf: *const c_void,
    bufsize: usize,
    get_client_ops: McctrlSysfsNodeLongFn,
    get_client_instance: McctrlSysfsNodeLongFn,
) -> isize {
    let (Some(get_client_ops), Some(get_client_instance)) = (get_client_ops, get_client_instance)
    else {
        return -(EINVAL as isize);
    };

    let client_ops = get_client_ops(instance) as *mut SysfsmOps;
    if client_ops.is_null() {
        return -(ENOSPC as isize);
    }

    match (*client_ops).store {
        Some(store) => store(
            client_ops,
            get_client_instance(instance) as *mut c_void,
            buf,
            bufsize,
        ),
        None => -(ENOSPC as isize),
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_local_release_body_result(
    instance: *mut c_void,
    snt_file: c_int,
    get_node_type: McctrlSysfsNodeTypeFn,
    get_client_ops: McctrlSysfsNodeLongFn,
    get_client_instance: McctrlSysfsNodeLongFn,
) -> c_int {
    let (Some(get_node_type), Some(get_client_ops), Some(get_client_instance)) =
        (get_node_type, get_client_ops, get_client_instance)
    else {
        return -EINVAL;
    };

    if get_node_type(instance) != snt_file {
        return 0;
    }

    let client_ops = get_client_ops(instance) as *mut SysfsmOps;
    if client_ops.is_null() {
        return 0;
    }

    if let Some(release) = (*client_ops).release {
        release(client_ops, get_client_instance(instance) as *mut c_void);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_cleanup_special_local_create_body_result(
    instance: *mut c_void,
    free: McctrlSysfsFreeFn,
) -> c_int {
    let Some(free) = free else {
        return -EINVAL;
    };
    free(instance);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_setup_special_local_create_body_result(
    param: *mut McctrlSysfsReqCreateParam,
    local_ops_table: *const *mut SysfsmOps,
    bitmap_size: usize,
    alloc: McctrlSysfsLocalAllocFn,
    copy: McctrlSysfsLocalCopyFn,
    unknown_ops: McctrlSysfsUnknownOpsFn,
) -> c_int {
    if param.is_null() || local_ops_table.is_null() {
        return -EINVAL;
    }

    let client_ops = (*param).client_ops;
    match mcctrl_sysfs_special_kind(client_ops) {
        1 => {
            (*param).client_ops = *local_ops_table.add(client_ops as usize) as c_long;
            0
        }
        2 => {
            let (Some(alloc), Some(copy)) = (alloc, copy) else {
                return -EINVAL;
            };
            let bitmap = alloc(bitmap_size);
            if bitmap.is_null() {
                return -ENOMEM;
            }
            copy(
                bitmap,
                (*param).client_instance as *const c_void,
                bitmap_size,
            );
            (*param).client_ops = *local_ops_table.add(client_ops as usize) as c_long;
            (*param).client_instance = bitmap as c_long;
            0
        }
        _ => {
            if let Some(unknown_ops) = unknown_ops {
                unknown_ops(client_ops);
            }
            -EINVAL
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_createf_post_path_body_result(
    os: *mut c_void,
    param: *mut McctrlSysfsReqCreateParam,
    local_ops_table: *const *mut SysfsmOps,
    bitmap_size: usize,
    alloc: McctrlSysfsLocalAllocFn,
    copy: McctrlSysfsLocalCopyFn,
    unknown_ops: McctrlSysfsUnknownOpsFn,
    create_local: McctrlSysfsLocalCreateFn,
    cleanup_special: McctrlSysfsCleanupSpecialFn,
    setup_failed: McctrlSysfsErrorFn,
) -> c_int {
    if param.is_null() {
        return -EINVAL;
    }

    let special = sysfs_ops_is_special((*param).client_ops as *mut c_void);
    if special {
        let error = mcctrl_sysfs_setup_special_local_create_body_result(
            param,
            local_ops_table,
            bitmap_size,
            alloc,
            copy,
            unknown_ops,
        );
        if error != 0 {
            if let Some(setup_failed) = setup_failed {
                setup_failed(error);
            }
            return error;
        }
    }

    let Some(create_local) = create_local else {
        if special {
            if let Some(cleanup_special) = cleanup_special {
                cleanup_special(
                    (*param).client_ops as *mut c_void,
                    (*param).client_instance as *mut c_void,
                );
            }
        }
        return -EINVAL;
    };

    let error = create_local(os, param);
    if error != 0 && special {
        if let Some(cleanup_special) = cleanup_special {
            cleanup_special(
                (*param).client_ops as *mut c_void,
                (*param).client_instance as *mut c_void,
            );
        }
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_mkdirf_post_path_body_result(
    os: *mut c_void,
    param: *mut McctrlSysfsReqMkdirParam,
    mkdir_local: McctrlSysfsLocalMkdirFn,
) -> c_int {
    if param.is_null() {
        return -EINVAL;
    }
    let Some(mkdir_local) = mkdir_local else {
        return -EINVAL;
    };
    mkdir_local(os, param)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_symlinkf_post_path_body_result(
    os: *mut c_void,
    param: *mut McctrlSysfsReqSymlinkParam,
    symlink_local: McctrlSysfsLocalSymlinkFn,
) -> c_int {
    if param.is_null() {
        return -EINVAL;
    }
    let Some(symlink_local) = symlink_local else {
        return -EINVAL;
    };
    symlink_local(os, param)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_lookupf_post_path_body_result(
    os: *mut c_void,
    param: *mut McctrlSysfsReqLookupParam,
    lookup_local: McctrlSysfsLocalLookupFn,
) -> c_int {
    if param.is_null() {
        return -EINVAL;
    }
    let Some(lookup_local) = lookup_local else {
        return -EINVAL;
    };
    lookup_local(os, param)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_unlinkf_post_path_body_result(
    os: *mut c_void,
    param: *mut McctrlSysfsReqUnlinkParam,
    unlink_local: McctrlSysfsLocalUnlinkFn,
) -> c_int {
    if param.is_null() {
        return -EINVAL;
    }
    let Some(unlink_local) = unlink_local else {
        return -EINVAL;
    };
    unlink_local(os, param)
}

type IkcPacketHandler =
    Option<unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> c_int>;
type IkcConnectHandler = Option<unsafe extern "C" fn(*mut c_void) -> c_int>;

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIhkIkcPacketHeader {
    channel: *mut c_void,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlSyscallRequest {
    rtid: c_int,
    ttid: c_int,
    valid: c_ulong,
    number: c_ulong,
    args: [c_ulong; 6],
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIkcScdPacketTraditional {
    ref_: c_int,
    osnum: c_int,
    pid: c_int,
    arg: c_ulong,
    req: McctrlSyscallRequest,
    resp_pa: c_ulong,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIkcScdPacketSysfs {
    sysfs_arg1: c_long,
    sysfs_arg2: c_long,
    sysfs_arg3: c_long,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIkcScdPacketCpuRw {
    pdesc: c_ulong,
    op: c_int,
    resp: *mut c_void,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIkcScdPacketFutex {
    resp: *mut c_void,
    spin_sleep: *mut c_int,
}

#[repr(C)]
#[derive(Clone, Copy)]
struct McctrlIkcScdPacketRemotePageFault {
    target_cpu: c_int,
    fault_tid: c_int,
    fault_address: c_ulong,
    fault_reason: c_ulong,
}

#[repr(C)]
union McctrlIkcScdPacketBody {
    traditional: McctrlIkcScdPacketTraditional,
    sysfs: McctrlIkcScdPacketSysfs,
    ttid: c_int,
    cpu_rw: McctrlIkcScdPacketCpuRw,
    eventfd_type: c_int,
    futex: McctrlIkcScdPacketFutex,
    remote_page_fault: McctrlIkcScdPacketRemotePageFault,
}

#[repr(C)]
pub struct McctrlIkcScdPacket {
    header: McctrlIhkIkcPacketHeader,
    msg: c_int,
    err: c_int,
    reply: *mut c_void,
    body: McctrlIkcScdPacketBody,
}

#[repr(C)]
pub struct McctrlIhkOsCpuRegister {
    addr: c_ulong,
    val: c_ulong,
    addr_ext: c_ulong,
    sync: AtomicI32,
}

#[repr(C)]
struct McctrlIhkIkcListenParam {
    handler: IkcConnectHandler,
    port: c_int,
    ikc_direction: c_int,
    pkt_size: c_int,
    queue_size: c_int,
    magic: c_int,
}

const _: () = {
    assert!(size_of::<McctrlIhkIkcPacketHeader>() == 8);
    assert!(size_of::<McctrlSyscallRequest>() == 72);
    assert!(size_of::<McctrlIkcScdPacketTraditional>() == 104);
    assert!(size_of::<McctrlIkcScdPacket>() == 128);
    assert!(align_of::<McctrlIkcScdPacket>() == 8);
    assert!(offset_of!(McctrlIkcScdPacket, msg) == 8);
    assert!(offset_of!(McctrlIkcScdPacket, reply) == 16);
    assert!(offset_of!(McctrlIkcScdPacket, body) == 24);
    assert!(size_of::<McctrlIhkOsCpuRegister>() == 32);
    assert!(offset_of!(McctrlIhkOsCpuRegister, val) == 8);
    assert!(offset_of!(McctrlIhkOsCpuRegister, sync) == 24);
    assert!(size_of::<McctrlIhkIkcListenParam>() == 32);
};

unsafe extern "C" {
    fn ihk_host_validate_os(os: *mut c_void) -> c_int;
    fn ihk_host_os_get_usrdata(os: *mut c_void) -> *mut c_void;
    fn ihk_host_os_set_usrdata(os: *mut c_void, usrdata: *mut c_void);
    fn ihk_os_get_cpu_info(os: *mut c_void) -> *mut c_void;
    fn ihk_os_get_memory_info(os: *mut c_void) -> *mut c_void;
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut c_void, opt: c_int) -> c_int;
    fn ihk_ikc_channel_set_cpu(channel: *mut c_void, cpu: c_int);
    fn ihk_ikc_get_processor_id() -> c_int;
    fn ihk_ikc_release_packet(packet: *mut c_void);
    fn ihk_ikc_destroy_channel(channel: *mut c_void);
    fn ihk_ikc_listen_port(os: *mut c_void, param: *mut McctrlIhkIkcListenParam) -> c_int;
    fn ihk_os_eventfd(os: *mut c_void, eventfd_type: c_int);
    fn mcexec_syscall(ud: *mut c_void, packet: *mut McctrlIkcScdPacket) -> c_int;
    fn sysfsm_packet_handler(
        os: *mut c_void,
        msg: c_int,
        err: c_int,
        arg1: c_long,
        arg2: c_long,
    ) -> c_int;
    fn procfsm_packet_handler(
        os: *mut c_void,
        msg: c_int,
        pid: c_int,
        arg: c_ulong,
        resp_pa: c_ulong,
    ) -> c_int;
    fn mcctrl_futex_wake(packet: *mut McctrlIkcScdPacket);
    fn mcctrl_ikc_kmalloc_atomic_bridge(size: usize) -> *mut c_void;
    fn mcctrl_ikc_kfree_bridge(ptr: *mut c_void);
    fn mcctrl_ikc_wakeup_desc_size_bridge(free_addrs_count: c_int) -> usize;
    fn mcctrl_ikc_desc_set_free_addr_bridge(desc: *mut c_void, index: c_int, addr: *mut c_void);
    fn mcctrl_ikc_desc_set_free_addrs_count_bridge(desc: *mut c_void, count: c_int);
    fn mcctrl_ikc_desc_free_addrs_count_bridge(desc: *mut c_void) -> c_int;
    fn mcctrl_ikc_desc_free_addr_bridge(desc: *mut c_void, index: c_int) -> *mut c_void;
    fn mcctrl_ikc_desc_set_free_at_put_bridge(desc: *mut c_void, free_at_put: c_int);
    fn mcctrl_ikc_desc_free_at_put_bridge(desc: *mut c_void) -> c_int;
    fn mcctrl_ikc_desc_init_waitqueue_bridge(desc: *mut c_void);
    fn mcctrl_ikc_desc_refcount_set_bridge(desc: *mut c_void, count: c_uint);
    fn mcctrl_ikc_desc_refcount_dec_and_test_bridge(desc: *mut c_void) -> c_int;
    fn mcctrl_ikc_desc_list_add_bridge(usrdata: *mut c_void, desc: *mut c_void);
    fn mcctrl_ikc_desc_list_del_bridge(usrdata: *mut c_void, desc: *mut c_void);
    fn mcctrl_ikc_desc_set_err_bridge(desc: *mut c_void, err: c_int);
    fn mcctrl_ikc_desc_err_bridge(desc: *mut c_void) -> c_int;
    fn mcctrl_ikc_desc_set_status_bridge(desc: *mut c_void, status: c_int);
    fn mcctrl_ikc_desc_cmpxchg_status_bridge(desc: *mut c_void, old: c_int, new: c_int) -> c_int;
    fn mcctrl_ikc_desc_wake_bridge(desc: *mut c_void);
    fn mcctrl_ikc_wait_interruptible_bridge(desc: *mut c_void) -> c_int;
    fn mcctrl_ikc_wait_timeout_bridge(desc: *mut c_void, timeout: c_long) -> c_int;
    fn mcctrl_ikc_wait_busy_bridge(desc: *mut c_void, timeout_msecs: c_ulong) -> c_int;
    fn mcctrl_ikc_alloc_usrdata_bridge() -> *mut c_void;
    fn mcctrl_ikc_usrdata_set_info_bridge(
        usrdata: *mut c_void,
        os: *mut c_void,
        cpu_info: *mut c_void,
        mem_info: *mut c_void,
    );
    #[link_name = "panic"]
    fn kernel_panic(fmt: *const c_char, ...) -> !;
    fn snprintf(buf: *mut c_char, size: usize, fmt: *const c_char, ...) -> c_int;
    fn memset(dest: *mut c_void, value: c_int, size: usize) -> *mut c_void;
    fn sysfsm_createf(
        os: *mut c_void,
        ops: *mut SysfsmOps,
        instance: *mut c_void,
        mode: c_int,
        fmt: *const c_char,
        ...
    ) -> c_int;
    fn sysfsm_mkdirf(os: *mut c_void, dirhp: *mut SysfsHandle, fmt: *const c_char, ...) -> c_int;
    fn sysfsm_symlinkf(os: *mut c_void, targeth: SysfsHandle, fmt: *const c_char, ...) -> c_int;
    fn sysfsm_lookupf(os: *mut c_void, objhp: *mut SysfsHandle, fmt: *const c_char, ...) -> c_int;
    fn sysfsm_unlinkf(os: *mut c_void, flags: c_int, fmt: *const c_char, ...) -> c_int;
    fn mcctrl_sysfs_get_usrdata_bridge(os: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_usrdata_os_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_os_to_dev_bridge(os: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_warn_missing_usrdata_bridge(func: *const c_char);
    fn mcctrl_sysfs_log_error_bridge(where_: *const c_char, error: c_int);
    fn mcctrl_cpumap_clear_bridge(mask: *mut c_void);
    fn mcctrl_cpumap_test_cpu_bridge(cpu: c_int, mask: *const c_void) -> c_int;
    fn mcctrl_cpumap_set_cpu_bridge(cpu: c_int, mask: *mut c_void);
    fn mcctrl_usrdata_cpu_mapping_bridge(usrdata: *mut c_void) -> *const c_int;
    fn mcctrl_usrdata_cpu_hw_ids_bridge(usrdata: *mut c_void) -> *const c_int;
    fn mcctrl_usrdata_cpu_count_bridge(usrdata: *mut c_void) -> c_int;
    fn mcctrl_usrdata_numa_mapping_bridge(usrdata: *mut c_void) -> *const c_int;
    fn mcctrl_usrdata_numa_count_bridge(usrdata: *mut c_void) -> c_int;
    fn mcctrl_sysfs_cpu_online_bridge(usrdata: *mut c_void) -> *mut c_ulong;
    fn mcctrl_sysfs_cpu_online_size_bridge() -> usize;
    fn mcctrl_sysfs_cpu_longs_bridge() -> c_int;
    fn mcctrl_sysfs_bits_per_long_bridge() -> c_int;
    fn mcctrl_sysfs_nr_cpu_ids_bridge() -> c_int;
    fn mcctrl_sysfs_max_numnodes_bridge() -> c_int;
    fn mcctrl_sysfs_numa_online_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_numa_online_size_bridge() -> usize;
    fn mcctrl_sysfs_node_set_bridge(node: c_int, mask: *mut c_void);
    fn mcctrl_sysfs_alloc_cache_topology_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_alloc_cpu_topology_bridge(index: c_int, saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_alloc_node_topology_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_kfree_bridge(ptr: *mut c_void);
    fn mcctrl_sysfs_get_cpu_topology_bridge(dev: *mut c_void, hw_id: c_int) -> *mut c_void;
    fn mcctrl_sysfs_get_node_topology_bridge(dev: *mut c_void, node: c_int) -> *mut c_void;
    fn mcctrl_sysfs_saved_cpu_core_siblings_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_cpu_thread_siblings_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_cpu_first_cache_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_cpu_next_cache_bridge(
        saved: *mut c_void,
        cache: *mut c_void,
    ) -> *mut c_void;
    fn mcctrl_sysfs_saved_cache_shared_cpu_map_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_cache_index_bridge(saved: *mut c_void) -> c_int;
    fn mcctrl_sysfs_saved_cache_level_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_saved_cache_type_bridge(saved: *mut c_void) -> *mut c_char;
    fn mcctrl_sysfs_saved_cache_size_str_bridge(saved: *mut c_void) -> *mut c_char;
    fn mcctrl_sysfs_saved_cache_coherency_line_size_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_saved_cache_number_of_sets_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_saved_cache_physical_line_partition_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_saved_cache_ways_of_associativity_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_cache_saved_bridge(cache: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_cache_shared_cpu_map_bridge(cache: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_cpu_saved_bridge(cpu: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_cpu_mckernel_id_bridge(cpu: *mut c_void) -> c_int;
    fn mcctrl_sysfs_cpu_core_siblings_bridge(cpu: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_cpu_thread_siblings_bridge(cpu: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_cpu_physical_package_id_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_saved_cpu_core_id_bridge(saved: *mut c_void) -> *mut c_long;
    fn mcctrl_sysfs_add_cache_to_cpu_bridge(cpu: *mut c_void, cache: *mut c_void);
    fn mcctrl_sysfs_add_cpu_to_usrdata_bridge(usrdata: *mut c_void, cpu: *mut c_void);
    fn mcctrl_sysfs_first_cpu_topology_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_next_cpu_topology_bridge(usrdata: *mut c_void, cpu: *mut c_void)
        -> *mut c_void;
    fn mcctrl_sysfs_first_cpu_cache_bridge(cpu: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_next_cpu_cache_bridge(cpu: *mut c_void, cache: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_pop_cpu_cache_bridge(cpu: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_pop_cpu_topology_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_saved_node_cpumap_bridge(saved: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_node_cpumap_bridge(node: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_node_set_mckernel_id_bridge(node: *mut c_void, id: c_int);
    fn mcctrl_sysfs_node_mckernel_id_bridge(node: *mut c_void) -> c_int;
    fn mcctrl_sysfs_node_distance_string_bridge(node: *mut c_void) -> *mut c_char;
    fn mcctrl_sysfs_add_node_to_usrdata_bridge(usrdata: *mut c_void, node: *mut c_void);
    fn mcctrl_sysfs_first_node_topology_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_next_node_topology_bridge(
        usrdata: *mut c_void,
        node: *mut c_void,
    ) -> *mut c_void;
    fn mcctrl_sysfs_pop_node_topology_bridge(usrdata: *mut c_void) -> *mut c_void;
    fn mcctrl_sysfs_node_distance_bridge(from: c_int, to: c_int) -> c_int;
    fn mcctrl_sysfs_cpu_to_node_bridge(cpu: c_int) -> c_int;
    fn mcctrl_ikc_cpu_info_n_cpus_bridge(cpu_info: *mut c_void) -> c_int;
    fn mcctrl_ikc_nr_cpu_ids_bridge() -> c_int;
    fn mcctrl_ikc_alloc_channels_bridge(usrdata: *mut c_void, num_channels: c_int) -> c_int;
    fn mcctrl_ikc_alloc_ikc2linux_bridge(usrdata: *mut c_void, cpu_count: c_int) -> c_int;
    fn mcctrl_ikc_free_channels_bridge(usrdata: *mut c_void);
    fn mcctrl_ikc_free_ikc2linux_bridge(usrdata: *mut c_void);
    fn mcctrl_ikc_usrdata_init_sync_bridge(usrdata: *mut c_void);
    fn mcctrl_ikc_usrdata_num_channels_bridge(usrdata: *mut c_void) -> c_int;
    fn mcctrl_ikc_usrdata_channel_desc_bridge(usrdata: *mut c_void, cpu: c_int) -> *mut c_void;
    fn mcctrl_ikc_usrdata_set_channel_desc_bridge(
        usrdata: *mut c_void,
        cpu: c_int,
        channel: *mut c_void,
    );
    fn mcctrl_ikc_usrdata_ikc2linux_desc_bridge(usrdata: *mut c_void, cpu: c_int) -> *mut c_void;
    fn mcctrl_ikc_usrdata_set_ikc2linux_desc_bridge(
        usrdata: *mut c_void,
        cpu: c_int,
        channel: *mut c_void,
    );
    fn mcctrl_ikc_channel_port_bridge(channel: *mut c_void) -> c_int;
    fn mcctrl_ikc_channel_remote_os_bridge(channel: *mut c_void) -> *mut c_void;
    fn mcctrl_ikc_channel_send_write_cpu_bridge(channel: *mut c_void) -> c_int;
    fn mcctrl_ikc_channel_send_read_cpu_bridge(channel: *mut c_void) -> c_int;
    fn mcctrl_ikc_info_channel_bridge(param: *mut c_void) -> *mut c_void;
    fn mcctrl_ikc_info_set_packet_handler_bridge(param: *mut c_void, handler: IkcPacketHandler);
    fn mcctrl_ikc_drain_wakeup_descs_bridge(usrdata: *mut c_void);
    fn mcctrl_ikc_drain_part_exec_list_bridge(usrdata: *mut c_void);
    fn mcctrl_ikc_log_usrdata_missing_bridge(func: *const c_char);
    fn mcctrl_ikc_log_os_missing_bridge(func: *const c_char);
    fn mcctrl_ikc_log_warn_packet_bridge(func: *const c_char);
    fn mcctrl_ikc_log_invalid_linux_cpu_bridge(func: *const c_char, cpu: c_int);
    fn mcctrl_ikc_log_invalid_source_cpu_bridge(cpu: c_int);
    fn mcctrl_ikc_log_unknown_packet_bridge(packet: *mut McctrlIkcScdPacket);
    fn mcctrl_ikc_log_alloc_usrdata_failed_bridge(func: *const c_char);
    fn mcctrl_ikc_log_missing_cpu_mem_bridge(func: *const c_char);
    fn mcctrl_ikc_log_invalid_cpu_count_bridge(func: *const c_char);
    fn mcctrl_ikc_log_alloc_channels_failed_bridge();
    fn mcctrl_ikc_log_alloc_ikc2linux_failed_bridge();
    fn mcctrl_ikc_log_no_channel_bridge(func: *const c_char);
    fn mcctrl_ikc_log_send_failed_bridge(func: *const c_char, ret: c_int);
    fn mcctrl_ikc_log_desc_alloc_failed_bridge(func: *const c_char);
}

unsafe fn mcctrl_ikc_packet_ref(packet: *mut McctrlIkcScdPacket) -> c_int {
    unsafe { (*packet).body.traditional.ref_ }
}

unsafe fn mcctrl_ikc_packet_pid(packet: *mut McctrlIkcScdPacket) -> c_int {
    unsafe { (*packet).body.traditional.pid }
}

unsafe fn mcctrl_ikc_packet_arg(packet: *mut McctrlIkcScdPacket) -> c_ulong {
    unsafe { (*packet).body.traditional.arg }
}

unsafe fn mcctrl_ikc_packet_resp_pa(packet: *mut McctrlIkcScdPacket) -> c_ulong {
    unsafe { (*packet).body.traditional.resp_pa }
}

unsafe fn mcctrl_ikc_packet_eventfd_type(packet: *mut McctrlIkcScdPacket) -> c_int {
    unsafe { (*packet).body.eventfd_type }
}

unsafe fn zero_mcctrl_ikc_packet(packet: *mut McctrlIkcScdPacket) {
    unsafe { core::ptr::write_bytes(packet.cast::<u8>(), 0, size_of::<McctrlIkcScdPacket>()) };
}

unsafe fn mcctrl_ikc_desc_put(desc: *mut c_void, usrdata: *mut c_void, free_addrs: c_int) {
    if unsafe { mcctrl_ikc_desc_refcount_dec_and_test_bridge(desc) } == 0 {
        return;
    }

    unsafe { mcctrl_ikc_desc_list_del_bridge(usrdata, desc) };

    if free_addrs != 0 {
        let count = unsafe { mcctrl_ikc_desc_free_addrs_count_bridge(desc) };
        let mut i = 0;
        while i < count {
            let addr = unsafe { mcctrl_ikc_desc_free_addr_bridge(desc, i) };
            if !addr.is_null() {
                unsafe { mcctrl_ikc_kfree_bridge(addr) };
            }
            i += 1;
        }
    }

    if unsafe { mcctrl_ikc_desc_free_at_put_bridge(desc) } != 0 {
        unsafe { mcctrl_ikc_kfree_bridge(desc) };
    }
}

unsafe fn mcctrl_wakeup_cb_result(os: *mut c_void, packet: *mut McctrlIkcScdPacket) {
    let desc = unsafe { (*packet).reply };
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };

    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(MCCTRL_IKC_SEND_WAIT_NAME.as_ptr().cast()) };
        return;
    }

    unsafe { mcctrl_ikc_desc_set_err_bridge(desc, (*packet).err) };

    if unsafe { mcctrl_ikc_desc_cmpxchg_status_bridge(desc, 0, 1) } != 0 {
        unsafe { mcctrl_ikc_desc_put(desc, usrdata, 1) };
        return;
    }

    unsafe { mcctrl_ikc_desc_wake_bridge(desc) };
    unsafe { mcctrl_ikc_desc_put(desc, usrdata, 0) };
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_ikc_send_wait_array(
    os: *mut c_void,
    cpu: c_int,
    pisp: *mut McctrlIkcScdPacket,
    timeout: c_long,
    mut desc: *mut c_void,
    do_frees: *mut c_int,
    free_addrs_count: c_int,
    free_addrs: *mut *mut c_void,
) -> c_int {
    let alloc_desc = desc.is_null();
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(MCCTRL_IKC_SEND_WAIT_NAME.as_ptr().cast()) };
        return -EINVAL;
    }

    if mcctrl_ikc_free_addrs_owner_result(free_addrs_count) != 0 && !do_frees.is_null() {
        unsafe { *do_frees = 1 };
    }

    if alloc_desc {
        let size = unsafe { mcctrl_ikc_wakeup_desc_size_bridge(free_addrs_count) };
        desc = unsafe { mcctrl_ikc_kmalloc_atomic_bridge(size) };
    }
    if desc.is_null() {
        unsafe {
            mcctrl_ikc_log_desc_alloc_failed_bridge(MCCTRL_IKC_SEND_WAIT_NAME.as_ptr().cast())
        };
        return -ENOMEM;
    }

    unsafe {
        (*pisp).reply = desc;
    }

    let mut i = 0;
    while i < free_addrs_count {
        let addr = unsafe { *free_addrs.add(i as usize) };
        unsafe { mcctrl_ikc_desc_set_free_addr_bridge(desc, i, addr) };
        i += 1;
    }
    unsafe {
        mcctrl_ikc_desc_set_free_addrs_count_bridge(desc, free_addrs_count);
        mcctrl_ikc_desc_set_free_at_put_bridge(
            desc,
            mcctrl_ikc_desc_free_at_put_result(alloc_desc as c_int),
        );
        mcctrl_ikc_desc_init_waitqueue_bridge(desc);
        mcctrl_ikc_desc_refcount_set_bridge(desc, 2);
        mcctrl_ikc_desc_list_add_bridge(usrdata, desc);
        mcctrl_ikc_desc_set_err_bridge(desc, 0);
        mcctrl_ikc_desc_set_status_bridge(desc, 0);
    }

    let mut ret = unsafe { mcctrl_ikc_send(os, cpu, pisp) };
    if ret < 0 {
        unsafe {
            mcctrl_ikc_log_send_failed_bridge(MCCTRL_IKC_SEND_WAIT_NAME.as_ptr().cast(), ret);
            mcctrl_ikc_desc_put(desc, usrdata, 0);
            mcctrl_ikc_desc_put(desc, usrdata, 0);
        }
        return ret;
    }

    match mcctrl_ikc_wait_mode_result(timeout) {
        -1 => {
            ret = unsafe {
                mcctrl_ikc_wait_busy_bridge(desc, mcctrl_ikc_busy_timeout_msecs_result(timeout))
            };
        }
        1 => {
            ret = unsafe { mcctrl_ikc_wait_timeout_bridge(desc, timeout) };
        }
        _ => {
            ret = unsafe { mcctrl_ikc_wait_interruptible_bridge(desc) };
        }
    }

    if unsafe { mcctrl_ikc_desc_cmpxchg_status_bridge(desc, 0, 1) } == 0 {
        unsafe { mcctrl_ikc_desc_put(desc, usrdata, 0) };
        if !do_frees.is_null() {
            unsafe { *do_frees = 0 };
        }
        return mcctrl_ikc_wait_abort_return_result(ret);
    }

    ret = unsafe { mcctrl_ikc_desc_err_bridge(desc) };
    unsafe { mcctrl_ikc_desc_put(desc, usrdata, 0) };
    ret
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_ikc_send(
    os: *mut c_void,
    cpu: c_int,
    pisp: *mut McctrlIkcScdPacket,
) -> c_int {
    if os.is_null() || unsafe { ihk_host_validate_os(os) } != 0 || pisp.is_null() {
        return -EINVAL;
    }
    if mcctrl_ikc_cpu_nonnegative_result(cpu) == 0 {
        return -EINVAL;
    }

    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null()
        || mcctrl_ikc_cpu_index_valid_result(cpu, unsafe {
            mcctrl_ikc_usrdata_num_channels_bridge(usrdata)
        }) == 0
    {
        return -EINVAL;
    }

    let channel = unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, cpu) };
    if channel.is_null() {
        return -EINVAL;
    }
    unsafe { ihk_ikc_send(channel, pisp.cast::<c_void>(), 0) }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_ikc_send_msg(
    os: *mut c_void,
    cpu: c_int,
    msg: c_int,
    ref_: c_int,
    arg: c_ulong,
) -> c_int {
    if os.is_null() {
        return -EINVAL;
    }

    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null()
        || mcctrl_ikc_cpu_index_valid_result(cpu, unsafe {
            mcctrl_ikc_usrdata_num_channels_bridge(usrdata)
        }) == 0
    {
        return -EINVAL;
    }

    let channel = unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, cpu) };
    if channel.is_null() {
        return -EINVAL;
    }

    let mut packet = MaybeUninit::<McctrlIkcScdPacket>::uninit();
    unsafe {
        zero_mcctrl_ikc_packet(packet.as_mut_ptr());
        (*packet.as_mut_ptr()).msg = msg;
        (*packet.as_mut_ptr()).body.traditional.ref_ = ref_;
        (*packet.as_mut_ptr()).body.traditional.arg = arg;
        ihk_ikc_send(channel, packet.as_mut_ptr().cast::<c_void>(), 0)
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_ikc_set_recv_cpu(os: *mut c_void, cpu: c_int) -> c_int {
    if os.is_null() {
        return -EINVAL;
    }

    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe {
            mcctrl_ikc_log_usrdata_missing_bridge(MCCTRL_IKC_SET_RECV_CPU_NAME.as_ptr().cast())
        };
        return -EINVAL;
    }

    let channel = unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, cpu) };
    unsafe { ihk_ikc_channel_set_cpu(channel, ihk_ikc_get_processor_id()) };
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_ikc_is_valid_thread(os: *mut c_void, cpu: c_int) -> c_int {
    if os.is_null() {
        return 0;
    }

    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null()
        || mcctrl_ikc_cpu_index_valid_result(cpu, unsafe {
            mcctrl_ikc_usrdata_num_channels_bridge(usrdata)
        }) == 0
        || unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, cpu) }.is_null()
    {
        0
    } else {
        1
    }
}

unsafe fn mcctrl_ikc_init_result(
    os: *mut c_void,
    cpu: c_int,
    rphys: c_ulong,
    channel: *mut c_void,
) {
    if os.is_null() {
        unsafe { mcctrl_ikc_log_os_missing_bridge(MCCTRL_IKC_INIT_NAME.as_ptr().cast()) };
        return;
    }

    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(MCCTRL_IKC_INIT_NAME.as_ptr().cast()) };
        return;
    }

    let target_cpu = if mcctrl_ikc_init_uses_last_channel_result(unsafe {
        mcctrl_ikc_channel_port_bridge(channel)
    }) != 0
    {
        unsafe { mcctrl_ikc_usrdata_num_channels_bridge(usrdata) - 1 }
    } else {
        cpu
    };
    let target = unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, target_cpu) };
    if target.is_null() {
        unsafe { mcctrl_ikc_log_no_channel_bridge(MCCTRL_IKC_INIT_NAME.as_ptr().cast()) };
        return;
    }

    let mut packet = MaybeUninit::<McctrlIkcScdPacket>::uninit();
    unsafe {
        zero_mcctrl_ikc_packet(packet.as_mut_ptr());
        (*packet.as_mut_ptr()).msg = SCD_MSG_INIT_CHANNEL_ACKED;
        (*packet.as_mut_ptr()).body.traditional.ref_ = cpu;
        (*packet.as_mut_ptr()).body.traditional.arg = rphys;
        let _ = ihk_ikc_send(target, packet.as_mut_ptr().cast::<c_void>(), 0);
    }
}

unsafe extern "C" fn syscall_packet_handler(
    channel: *mut c_void,
    packet_raw: *mut c_void,
    os: *mut c_void,
) -> c_int {
    let packet = packet_raw.cast::<McctrlIkcScdPacket>();
    let msg = unsafe { (*packet).msg };
    let mut ret = 0;
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };

    if usrdata.is_null() {
        unsafe {
            mcctrl_ikc_log_usrdata_missing_bridge(SYSCALL_PACKET_HANDLER_NAME.as_ptr().cast())
        };
        ret = -EINVAL;
    } else {
        match msg {
            SCD_MSG_INIT_CHANNEL => unsafe {
                mcctrl_ikc_init_result(
                    os,
                    mcctrl_ikc_packet_ref(packet),
                    mcctrl_ikc_packet_arg(packet),
                    channel,
                );
            },
            SCD_MSG_PREPARE_PROCESS_ACKED
            | SCD_MSG_PERF_ACK
            | SCD_MSG_SEND_SIGNAL_ACK
            | SCD_MSG_PROCFS_ANSWER
            | SCD_MSG_REMOTE_PAGE_FAULT_ANSWER
            | SCD_MSG_CPU_RW_REG_RESP
            | SCD_MSG_CLEANUP_PROCESS_RESP
            | SCD_MSG_CLEANUP_FD_RESP => unsafe {
                mcctrl_wakeup_cb_result(os, packet);
            },
            SCD_MSG_SYSCALL_ONESIDE => unsafe {
                let _ = mcexec_syscall(usrdata, packet);
            },
            SCD_MSG_SYSFS_REQ_CREATE
            | SCD_MSG_SYSFS_REQ_MKDIR
            | SCD_MSG_SYSFS_REQ_SYMLINK
            | SCD_MSG_SYSFS_REQ_LOOKUP
            | SCD_MSG_SYSFS_REQ_UNLINK
            | SCD_MSG_SYSFS_REQ_SETUP
            | SCD_MSG_SYSFS_RESP_SHOW
            | SCD_MSG_SYSFS_RESP_STORE
            | SCD_MSG_SYSFS_RESP_RELEASE => unsafe {
                let sysfs = (*packet).body.sysfs;
                let _ = sysfsm_packet_handler(
                    os,
                    msg,
                    (*packet).err,
                    sysfs.sysfs_arg1,
                    sysfs.sysfs_arg2,
                );
            },
            SCD_MSG_PROCFS_TID_CREATE | SCD_MSG_PROCFS_TID_DELETE => unsafe {
                let _ = procfsm_packet_handler(
                    os,
                    msg,
                    mcctrl_ikc_packet_pid(packet),
                    mcctrl_ikc_packet_arg(packet),
                    mcctrl_ikc_packet_resp_pa(packet),
                );
            },
            SCD_MSG_GET_VDSO_INFO => unsafe {
                get_vdso_info(os, mcctrl_ikc_packet_arg(packet) as c_long);
            },
            SCD_MSG_EVENTFD => unsafe {
                mcctrl_eventfd(os, packet);
            },
            SCD_MSG_FUTEX_WAKE => unsafe {
                mcctrl_futex_wake(packet);
            },
            _ => unsafe {
                mcctrl_ikc_log_unknown_packet_bridge(packet);
            },
        }
    }

    if mcctrl_ikc_release_packet_after_handler_result(msg) != 0 {
        unsafe { ihk_ikc_release_packet(packet_raw) };
    }
    ret
}

unsafe extern "C" fn dummy_packet_handler(
    _channel: *mut c_void,
    packet_raw: *mut c_void,
    _os: *mut c_void,
) -> c_int {
    unsafe {
        mcctrl_ikc_log_warn_packet_bridge(DUMMY_PACKET_HANDLER_NAME.as_ptr().cast());
        ihk_ikc_release_packet(packet_raw);
    }
    0
}

unsafe extern "C" fn connect_handler_ikc2linux(param: *mut c_void) -> c_int {
    let channel = unsafe { mcctrl_ikc_info_channel_bridge(param) };
    let os = unsafe { mcctrl_ikc_channel_remote_os_bridge(channel) };
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(CONNECT_IKC2LINUX_NAME.as_ptr().cast()) };
        return -1;
    }

    let linux_cpu = unsafe { mcctrl_ikc_channel_send_write_cpu_bridge(channel) };
    if mcctrl_ikc_linux_cpu_valid_result(linux_cpu, unsafe { mcctrl_ikc_nr_cpu_ids_bridge() }) == 0
    {
        unsafe {
            mcctrl_ikc_log_invalid_linux_cpu_bridge(
                CONNECT_IKC2LINUX_NAME.as_ptr().cast(),
                linux_cpu,
            )
        };
        return -1;
    }

    unsafe {
        mcctrl_ikc_info_set_packet_handler_bridge(param, Some(syscall_packet_handler));
        mcctrl_ikc_usrdata_set_ikc2linux_desc_bridge(usrdata, linux_cpu, channel);
    }
    0
}

unsafe extern "C" fn connect_handler_ikc2mckernel(param: *mut c_void) -> c_int {
    let channel = unsafe { mcctrl_ikc_info_channel_bridge(param) };
    let os = unsafe { mcctrl_ikc_channel_remote_os_bridge(channel) };
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(CONNECT_IKC2MCKERNEL_NAME.as_ptr().cast()) };
        return 1;
    }

    let mck_cpu = unsafe { mcctrl_ikc_channel_send_read_cpu_bridge(channel) };
    if mcctrl_ikc_cpu_index_valid_result(mck_cpu, unsafe {
        mcctrl_ikc_usrdata_num_channels_bridge(usrdata)
    }) == 0
    {
        unsafe { mcctrl_ikc_log_invalid_source_cpu_bridge(mck_cpu) };
        return 1;
    }

    unsafe {
        mcctrl_ikc_info_set_packet_handler_bridge(param, Some(dummy_packet_handler));
        mcctrl_ikc_usrdata_set_channel_desc_bridge(usrdata, mck_cpu, channel);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn prepare_ikc_channels(os: *mut c_void) -> c_int {
    let usrdata = unsafe { mcctrl_ikc_alloc_usrdata_bridge() };
    if usrdata.is_null() {
        unsafe {
            mcctrl_ikc_log_alloc_usrdata_failed_bridge(PREPARE_IKC_CHANNELS_NAME.as_ptr().cast())
        };
        return -ENOMEM;
    }

    let mut ret = 0;
    let cpu_info = unsafe { ihk_os_get_cpu_info(os) };
    let mem_info = unsafe { ihk_os_get_memory_info(os) };
    unsafe { mcctrl_ikc_usrdata_set_info_bridge(usrdata, os, cpu_info, mem_info) };

    if cpu_info.is_null() || mem_info.is_null() {
        unsafe { mcctrl_ikc_log_missing_cpu_mem_bridge(PREPARE_IKC_CHANNELS_NAME.as_ptr().cast()) };
        ret = -EINVAL;
    } else {
        let n_cpus = unsafe { mcctrl_ikc_cpu_info_n_cpus_bridge(cpu_info) };
        if mcctrl_ikc_cpu_count_valid_result(n_cpus) == 0 {
            unsafe {
                mcctrl_ikc_log_invalid_cpu_count_bridge(PREPARE_IKC_CHANNELS_NAME.as_ptr().cast())
            };
            ret = -EINVAL;
        } else if unsafe { mcctrl_ikc_alloc_channels_bridge(usrdata, n_cpus) } != 0 {
            unsafe { mcctrl_ikc_log_alloc_channels_failed_bridge() };
            ret = -ENOMEM;
        } else if unsafe {
            mcctrl_ikc_alloc_ikc2linux_bridge(usrdata, mcctrl_ikc_nr_cpu_ids_bridge())
        } != 0
        {
            unsafe { mcctrl_ikc_log_alloc_ikc2linux_failed_bridge() };
            ret = -ENOMEM;
        }
    }

    if ret != 0 {
        unsafe {
            mcctrl_ikc_free_channels_bridge(usrdata);
            mcctrl_ikc_free_ikc2linux_bridge(usrdata);
            mcctrl_ikc_kfree_bridge(usrdata);
        }
        return ret;
    }

    unsafe {
        ihk_host_os_set_usrdata(os, usrdata);
        mcctrl_ikc_usrdata_init_sync_bridge(usrdata);
    }

    let mut lp_ikc2linux = McctrlIhkIkcListenParam {
        handler: Some(connect_handler_ikc2linux),
        port: MCCTRL_IKC2LINUX_PORT,
        ikc_direction: IHK_IKC_DIRECTION_RECV,
        pkt_size: size_of::<McctrlIkcScdPacket>() as c_int,
        queue_size: (PAGE_SIZE * 4) as c_int,
        magic: MCCTRL_IKC2LINUX_MAGIC,
    };
    let mut lp_ikc2mckernel = McctrlIhkIkcListenParam {
        handler: Some(connect_handler_ikc2mckernel),
        port: MCCTRL_IKC2MCKERNEL_PORT,
        ikc_direction: IHK_IKC_DIRECTION_SEND,
        pkt_size: size_of::<McctrlIkcScdPacket>() as c_int,
        queue_size: (PAGE_SIZE * 4) as c_int,
        magic: MCCTRL_IKC2MCKERNEL_MAGIC,
    };

    unsafe {
        let _ = ihk_ikc_listen_port(os, &mut lp_ikc2linux);
        let _ = ihk_ikc_listen_port(os, &mut lp_ikc2mckernel);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn __destroy_ikc_channel(_os: *mut c_void, _pmc: *mut c_void) {}

#[no_mangle]
pub unsafe extern "C" fn destroy_ikc_channels(os: *mut c_void) {
    let usrdata = unsafe { ihk_host_os_get_usrdata(os) };
    if usrdata.is_null() {
        unsafe { mcctrl_ikc_log_usrdata_missing_bridge(DESTROY_IKC_CHANNELS_NAME.as_ptr().cast()) };
        return;
    }

    unsafe { ihk_host_os_set_usrdata(os, null_mut()) };

    let num_channels = unsafe { mcctrl_ikc_usrdata_num_channels_bridge(usrdata) };
    let mut i = 0;
    while i < num_channels {
        let channel = unsafe { mcctrl_ikc_usrdata_channel_desc_bridge(usrdata, i) };
        if !channel.is_null() {
            unsafe { ihk_ikc_destroy_channel(channel) };
        }
        i += 1;
    }

    let nr_cpu_ids = unsafe { mcctrl_ikc_nr_cpu_ids_bridge() };
    i = 0;
    while i < nr_cpu_ids {
        let channel = unsafe { mcctrl_ikc_usrdata_ikc2linux_desc_bridge(usrdata, i) };
        if !channel.is_null() {
            unsafe { ihk_ikc_destroy_channel(channel) };
        }
        i += 1;
    }

    unsafe {
        mcctrl_ikc_drain_wakeup_descs_bridge(usrdata);
        mcctrl_ikc_free_channels_bridge(usrdata);
        mcctrl_ikc_free_ikc2linux_bridge(usrdata);
        mcctrl_ikc_drain_part_exec_list_bridge(usrdata);
        mcctrl_ikc_kfree_bridge(usrdata);
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_eventfd(os: *mut c_void, pisp: *mut McctrlIkcScdPacket) {
    unsafe { ihk_os_eventfd(os, mcctrl_ikc_packet_eventfd_type(pisp)) };
}

#[no_mangle]
pub extern "C" fn mcctrl_pte_is_write_combined_result(flags: c_ulong) -> c_int {
    ((flags & PAGE_PWT) != 0 && (flags & PAGE_PCD) == 0) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn xchg4(ptr: *mut c_int, x: c_int) -> c_int {
    if ptr.is_null() {
        return x;
    }
    let atomic = &*ptr.cast::<AtomicI32>();
    atomic.swap(x, Ordering::SeqCst)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_lwk_to_linux_index_result(
    mapping: *const c_int,
    count: c_int,
    index: c_int,
) -> c_int {
    if mapping.is_null() || index < 0 || index >= count {
        return -1;
    }

    *mapping.add(index as usize)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_linux_to_lwk_index_result(
    mapping: *const c_int,
    count: c_int,
    linux_id: c_int,
) -> c_int {
    if mapping.is_null() || count <= 0 {
        return -1;
    }

    let mut i = 0;
    while i < count {
        if *mapping.add(i as usize) == linux_id {
            return i;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_translate_cpumap_result(
    mapping: *const c_int,
    count: c_int,
    linmap: *const c_void,
    mckmap: *mut c_void,
    nr_cpu_ids: c_int,
) -> c_int {
    unsafe { mcctrl_cpumap_clear_bridge(mckmap) };

    let mut lincpu = 0;
    while lincpu < nr_cpu_ids {
        if unsafe { mcctrl_cpumap_test_cpu_bridge(lincpu, linmap) } != 0 {
            let mckcpu = unsafe { mcctrl_linux_to_lwk_index_result(mapping, count, lincpu) };

            if mckcpu >= 0 {
                unsafe { mcctrl_cpumap_set_cpu_bridge(mckcpu, mckmap) };
            }
        }
        lincpu += 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mckernel_cpu_2_linux_cpu(usrdata: *mut c_void, cpu_id: c_int) -> c_int {
    let mapping = unsafe { mcctrl_usrdata_cpu_mapping_bridge(usrdata) };
    let count = unsafe { mcctrl_usrdata_cpu_count_bridge(usrdata) };

    unsafe { mcctrl_lwk_to_linux_index_result(mapping, count, cpu_id) }
}

#[no_mangle]
pub unsafe extern "C" fn mckernel_cpu_2_hw_id(usrdata: *mut c_void, cpu_id: c_int) -> c_int {
    let hw_ids = unsafe { mcctrl_usrdata_cpu_hw_ids_bridge(usrdata) };
    let count = unsafe { mcctrl_usrdata_cpu_count_bridge(usrdata) };

    unsafe { mcctrl_lwk_to_linux_index_result(hw_ids, count, cpu_id) }
}

#[no_mangle]
pub unsafe extern "C" fn linux_cpu_2_mckernel_cpu(usrdata: *mut c_void, cpu_id: c_int) -> c_int {
    let mapping = unsafe { mcctrl_usrdata_cpu_mapping_bridge(usrdata) };
    let count = unsafe { mcctrl_usrdata_cpu_count_bridge(usrdata) };

    unsafe { mcctrl_linux_to_lwk_index_result(mapping, count, cpu_id) }
}

#[no_mangle]
pub unsafe extern "C" fn mckernel_numa_2_linux_numa(usrdata: *mut c_void, numa_id: c_int) -> c_int {
    let mapping = unsafe { mcctrl_usrdata_numa_mapping_bridge(usrdata) };
    let count = unsafe { mcctrl_usrdata_numa_count_bridge(usrdata) };

    unsafe { mcctrl_lwk_to_linux_index_result(mapping, count, numa_id) }
}

#[no_mangle]
pub unsafe extern "C" fn linux_numa_2_mckernel_numa(usrdata: *mut c_void, numa_id: c_int) -> c_int {
    let mapping = unsafe { mcctrl_usrdata_numa_mapping_bridge(usrdata) };
    let count = unsafe { mcctrl_usrdata_numa_count_bridge(usrdata) };

    unsafe { mcctrl_linux_to_lwk_index_result(mapping, count, numa_id) }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fill_sequential_bitset_result(
    bits: *mut c_ulong,
    bit_count: c_int,
    word_count: c_int,
    bits_per_word: c_int,
) {
    if bits.is_null() || bit_count < 0 || word_count <= 0 || bits_per_word <= 0 {
        return;
    }

    let mut word = 0;
    while word < word_count {
        core::ptr::write_volatile(bits.add(word as usize), 0);
        word += 1;
    }

    let limit = (word_count as c_long).wrapping_mul(bits_per_word as c_long);
    let mut bit = 0;
    while bit < bit_count && (bit as c_long) < limit {
        let word_index = bit / bits_per_word;
        let bit_index = bit % bits_per_word;
        let word_ptr = bits.add(word_index as usize);
        let value = core::ptr::read_volatile(word_ptr) | ((1 as c_ulong) << (bit_index as usize));
        core::ptr::write_volatile(word_ptr, value);
        bit += 1;
    }
}

const fn sysfs_special_ops(value: usize) -> *mut SysfsmOps {
    value as *mut SysfsmOps
}

fn sysfs_err_ptr(error: c_int) -> *mut c_void {
    error as isize as *mut c_void
}

fn sysfs_is_err(ptr: *mut c_void) -> bool {
    (ptr as usize) >= usize::MAX - SYSFS_ERRNO_MAX + 1
}

fn sysfs_ptr_err(ptr: *mut c_void) -> c_int {
    ptr as isize as c_int
}

unsafe fn sysfs_panic(message: &'static [u8]) -> ! {
    unsafe { kernel_panic(message.as_ptr().cast::<c_char>()) }
}

unsafe fn sysfs_panic_on(error: c_int, message: &'static [u8]) {
    if error != 0 {
        unsafe { sysfs_panic(message) };
    }
}

unsafe extern "C" fn show_int(
    _ops: *mut SysfsmOps,
    instance: *mut c_void,
    buf: *mut c_void,
    size: usize,
) -> isize {
    if instance.is_null() {
        return unsafe { snprintf(buf.cast::<c_char>(), size, b"%d\n\0".as_ptr().cast(), 0) }
            as isize;
    }

    unsafe {
        snprintf(
            buf.cast::<c_char>(),
            size,
            b"%d\n\0".as_ptr().cast(),
            *(instance.cast::<c_int>()),
        ) as isize
    }
}

#[no_mangle]
pub unsafe extern "C" fn setup_local_snooping_samples(os: *mut c_void) {
    let mut param = SysfsmBitmapParam {
        nbits: 40,
        padding: 0,
        ptr: (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
    };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D32_VALUE),
            (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/local/d32\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: d32\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/local/d64\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: d64\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_U32_VALUE),
            (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/local/u32\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: u32\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_U64_VALUE),
            (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/local/u64\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: u64\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_S_VALUE),
            SYSFS_LOCAL_STRING_VALUE.as_ptr().cast::<c_void>() as *mut c_void,
            0o444,
            b"/sys/test/local/s\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: s\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/test/local/pbl\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: pbl\0") };

    param.nbits = 40;
    param.ptr = (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>();
    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PB_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/test/local/pb\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: pb\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_U32K_VALUE),
            (&raw mut SYSFS_LOCAL_LONG_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/local/u32K\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"setup_local_snooping_samples: u32K\0") };
}

#[no_mangle]
pub unsafe extern "C" fn setup_local_snooping_files(os: *mut c_void) {
    let udp = unsafe { mcctrl_sysfs_get_usrdata_bridge(os) };
    if udp.is_null() {
        unsafe { sysfs_panic(b"setup_local_snooping_files: error: mcctrl_usrdata not found\n\0") };
    }

    let cpu_online = unsafe { mcctrl_sysfs_cpu_online_bridge(udp) };
    unsafe {
        memset(
            cpu_online.cast::<c_void>(),
            0,
            mcctrl_sysfs_cpu_online_size_bridge(),
        );
        mcctrl_fill_sequential_bitset(
            cpu_online,
            mcctrl_usrdata_cpu_count_bridge(udp),
            mcctrl_sysfs_cpu_longs_bridge(),
            mcctrl_sysfs_bits_per_long_bridge(),
        );
    }

    let mut param = SysfsmBitmapParam {
        nbits: unsafe { mcctrl_sysfs_cpu_longs_bridge() * mcctrl_sysfs_bits_per_long_bridge() },
        padding: 0,
        ptr: cpu_online.cast::<c_void>(),
    };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/cpu/online\0".as_ptr().cast(),
        )
    };
    unsafe {
        sysfs_panic_on(
            error,
            b"setup_local_snooping_files: devices/system/cpu/online\0",
        )
    };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/cpu/possible\0".as_ptr().cast(),
        )
    };
    unsafe {
        sysfs_panic_on(
            error,
            b"setup_local_snooping_files: devices/system/cpu/possible\0",
        )
    };

    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/cpu/present\0".as_ptr().cast(),
        )
    };
    unsafe {
        sysfs_panic_on(
            error,
            b"setup_local_snooping_files: devices/system/cpu/present\0",
        )
    };

    param.nbits = unsafe { mcctrl_sysfs_bits_per_long_bridge() };
    param.ptr = (&raw mut SYSFS_CPU_OFFLINE).cast::<c_void>();
    let error = unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/cpu/offline\0".as_ptr().cast(),
        )
    };
    unsafe {
        sysfs_panic_on(
            error,
            b"setup_local_snooping_files: devices/system/cpu/offline\0",
        )
    };
}

unsafe fn free_cpu_topology_one(cpu: *mut c_void) {
    loop {
        let cache = unsafe { mcctrl_sysfs_pop_cpu_cache_bridge(cpu) };
        if cache.is_null() {
            break;
        }
        unsafe { mcctrl_sysfs_kfree_bridge(cache) };
    }
    unsafe { mcctrl_sysfs_kfree_bridge(cpu) };
}

#[no_mangle]
pub unsafe extern "C" fn free_topology_info(os: *mut c_void) {
    let udp = unsafe { mcctrl_sysfs_get_usrdata_bridge(os) };
    if udp.is_null() {
        unsafe {
            mcctrl_sysfs_warn_missing_usrdata_bridge(b"free_topology_info\0".as_ptr().cast())
        };
        return;
    }

    loop {
        let node = unsafe { mcctrl_sysfs_pop_node_topology_bridge(udp) };
        if node.is_null() {
            break;
        }
        unsafe { mcctrl_sysfs_kfree_bridge(node) };
    }

    loop {
        let cpu = unsafe { mcctrl_sysfs_pop_cpu_topology_bridge(udp) };
        if cpu.is_null() {
            break;
        }
        unsafe { free_cpu_topology_one(cpu) };
    }
}

unsafe fn translate_cpumap(udp: *mut c_void, linmap: *const c_void, mckmap: *mut c_void) -> c_int {
    unsafe {
        mcctrl_translate_cpumap_result(
            mcctrl_usrdata_cpu_mapping_bridge(udp),
            mcctrl_usrdata_cpu_count_bridge(udp),
            linmap,
            mckmap,
            mcctrl_sysfs_nr_cpu_ids_bridge(),
        )
    }
}

unsafe fn get_cache_topology(
    _udp_cpu: *mut c_void,
    udp: *mut c_void,
    saved: *mut c_void,
) -> *mut c_void {
    let topo = unsafe { mcctrl_sysfs_alloc_cache_topology_bridge(saved) };
    if topo.is_null() {
        unsafe {
            mcctrl_sysfs_log_error_bridge(b"get_cache_topology:kmalloc\0".as_ptr().cast(), -ENOMEM)
        };
        return sysfs_err_ptr(-ENOMEM);
    }

    let error = unsafe {
        translate_cpumap(
            udp,
            mcctrl_sysfs_saved_cache_shared_cpu_map_bridge(saved),
            mcctrl_sysfs_cache_shared_cpu_map_bridge(topo),
        )
    };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_cache_topology:translate_cpumap\0".as_ptr().cast(),
                error,
            );
            mcctrl_sysfs_kfree_bridge(topo);
        }
        return sysfs_err_ptr(error);
    }

    topo
}

unsafe fn get_one_cpu_topology(udp: *mut c_void, index: c_int) -> *mut c_void {
    let os = unsafe { mcctrl_sysfs_usrdata_os_bridge(udp) };
    let dev = unsafe { mcctrl_sysfs_os_to_dev_bridge(os) };
    let saved =
        unsafe { mcctrl_sysfs_get_cpu_topology_bridge(dev, mckernel_cpu_2_hw_id(udp, index)) };
    let topology = unsafe { mcctrl_sysfs_alloc_cpu_topology_bridge(index, saved) };

    if topology.is_null() {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_cpu_topology:kmalloc\0".as_ptr().cast(),
                -ENOMEM,
            )
        };
        return sysfs_err_ptr(-ENOMEM);
    }
    if saved.is_null() {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_cpu_topology:ihk_device_get_cpu_topology\0"
                    .as_ptr()
                    .cast(),
                -ENOENT,
            );
            free_cpu_topology_one(topology);
        }
        return sysfs_err_ptr(-ENOENT);
    }

    let error = unsafe {
        translate_cpumap(
            udp,
            mcctrl_sysfs_saved_cpu_core_siblings_bridge(saved),
            mcctrl_sysfs_cpu_core_siblings_bridge(topology),
        )
    };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_cpu_topology:core_siblings\0".as_ptr().cast(),
                error,
            );
            free_cpu_topology_one(topology);
        }
        return sysfs_err_ptr(error);
    }

    let error = unsafe {
        translate_cpumap(
            udp,
            mcctrl_sysfs_saved_cpu_thread_siblings_bridge(saved),
            mcctrl_sysfs_cpu_thread_siblings_bridge(topology),
        )
    };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_cpu_topology:thread_siblings\0".as_ptr().cast(),
                error,
            );
            free_cpu_topology_one(topology);
        }
        return sysfs_err_ptr(error);
    }

    let mut saved_cache = unsafe { mcctrl_sysfs_saved_cpu_first_cache_bridge(saved) };
    while !saved_cache.is_null() {
        let cache = unsafe { get_cache_topology(topology, udp, saved_cache) };
        if sysfs_is_err(cache) {
            let error = sysfs_ptr_err(cache);
            unsafe {
                mcctrl_sysfs_log_error_bridge(
                    b"get_one_cpu_topology:get_cache_topology\0".as_ptr().cast(),
                    error,
                );
                free_cpu_topology_one(topology);
            }
            return sysfs_err_ptr(error);
        } else if cache.is_null() {
            unsafe { free_cpu_topology_one(topology) };
            return sysfs_err_ptr(-ENOENT);
        }

        unsafe { mcctrl_sysfs_add_cache_to_cpu_bridge(topology, cache) };
        saved_cache = unsafe { mcctrl_sysfs_saved_cpu_next_cache_bridge(saved, saved_cache) };
    }

    topology
}

unsafe fn get_cpu_topology(udp: *mut c_void) -> c_int {
    let mut index = 0;
    let count = unsafe { mcctrl_usrdata_cpu_count_bridge(udp) };

    while index < count {
        let topology = unsafe { get_one_cpu_topology(udp, index) };
        if sysfs_is_err(topology) {
            let error = sysfs_ptr_err(topology);
            unsafe {
                mcctrl_sysfs_log_error_bridge(
                    b"get_cpu_topology:get_one_cpu_topology\0".as_ptr().cast(),
                    error,
                );
            }
            return error;
        }

        unsafe { mcctrl_sysfs_add_cpu_to_usrdata_bridge(udp, topology) };
        index += 1;
    }

    0
}

unsafe fn setup_cpu_sysfs_cache_files(udp: *mut c_void, cpu: *mut c_void, cache: *mut c_void) {
    let prefix = b"/sys/devices/system/cpu\0";
    let os = unsafe { mcctrl_sysfs_usrdata_os_bridge(udp) };
    let cpu_number = unsafe { mcctrl_sysfs_cpu_mckernel_id_bridge(cpu) };
    let saved = unsafe { mcctrl_sysfs_cache_saved_bridge(cache) };
    let index = unsafe { mcctrl_sysfs_saved_cache_index_bridge(saved) };
    let mut param = SysfsmBitmapParam {
        nbits: unsafe { mcctrl_sysfs_nr_cpu_ids_bridge() },
        padding: 0,
        ptr: unsafe { mcctrl_sysfs_cache_shared_cpu_map_bridge(cache) },
    };

    unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            mcctrl_sysfs_saved_cache_level_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/level\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_S_VALUE),
            mcctrl_sysfs_saved_cache_type_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/type\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_S_VALUE),
            mcctrl_sysfs_saved_cache_size_str_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/size\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            mcctrl_sysfs_saved_cache_coherency_line_size_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/coherency_line_size\0"
                .as_ptr()
                .cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            mcctrl_sysfs_saved_cache_number_of_sets_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/number_of_sets\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            mcctrl_sysfs_saved_cache_physical_line_partition_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/physical_line_partition\0"
                .as_ptr()
                .cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D64_VALUE),
            mcctrl_sysfs_saved_cache_ways_of_associativity_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/ways_of_associativity\0"
                .as_ptr()
                .cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PB_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/shared_cpu_map\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/cache/index%d/shared_cpu_list\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
            index,
        );
    }
}

unsafe fn setup_cpu_sysfs_files(udp: *mut c_void, cpu: *mut c_void) {
    let prefix = b"/sys/devices/system/cpu\0";
    let os = unsafe { mcctrl_sysfs_usrdata_os_bridge(udp) };
    let saved = unsafe { mcctrl_sysfs_cpu_saved_bridge(cpu) };
    let cpu_number = unsafe { mcctrl_sysfs_cpu_mckernel_id_bridge(cpu) };
    let mut param = SysfsmBitmapParam {
        nbits: unsafe { mcctrl_sysfs_nr_cpu_ids_bridge() },
        padding: 0,
        ptr: unsafe { mcctrl_sysfs_cpu_core_siblings_bridge(cpu) },
    };

    unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D32_VALUE),
            mcctrl_sysfs_saved_cpu_physical_package_id_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/physical_package_id\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_D32_VALUE),
            mcctrl_sysfs_saved_cpu_core_id_bridge(saved).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/core_id\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PB_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/core_siblings\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/core_siblings_list\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
    }

    param.ptr = unsafe { mcctrl_sysfs_cpu_thread_siblings_bridge(cpu) };
    unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PB_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/thread_siblings\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"%s/cpu%d/topology/thread_siblings_list\0".as_ptr().cast(),
            prefix.as_ptr().cast::<c_char>(),
            cpu_number,
        );
    }

    let mut cache = unsafe { mcctrl_sysfs_first_cpu_cache_bridge(cpu) };
    while !cache.is_null() {
        unsafe { setup_cpu_sysfs_cache_files(udp, cpu, cache) };
        cache = unsafe { mcctrl_sysfs_next_cpu_cache_bridge(cpu, cache) };
    }
}

unsafe fn setup_cpus_sysfs_files(udp: *mut c_void) {
    let error = unsafe { get_cpu_topology(udp) };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"setup_cpus_sysfs_files:get_cpu_topology\0".as_ptr().cast(),
                error,
            )
        };
        return;
    }

    let mut cpu = unsafe { mcctrl_sysfs_first_cpu_topology_bridge(udp) };
    while !cpu.is_null() {
        unsafe { setup_cpu_sysfs_files(udp, cpu) };
        cpu = unsafe { mcctrl_sysfs_next_cpu_topology_bridge(udp, cpu) };
    }
}

unsafe fn get_one_node_topology(udp: *mut c_void, saved: *mut c_void) -> *mut c_void {
    let node = unsafe { mcctrl_sysfs_alloc_node_topology_bridge(saved) };
    if node.is_null() {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_node_topology:kmalloc\0".as_ptr().cast(),
                -ENOMEM,
            )
        };
        return sysfs_err_ptr(-ENOMEM);
    }

    let error = unsafe {
        translate_cpumap(
            udp,
            mcctrl_sysfs_saved_node_cpumap_bridge(saved),
            mcctrl_sysfs_node_cpumap_bridge(node),
        )
    };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"get_one_node_topology:translate_cpumap\0".as_ptr().cast(),
                error,
            );
            mcctrl_sysfs_kfree_bridge(node);
        }
        return sysfs_err_ptr(error);
    }

    node
}

unsafe fn get_node_topology(udp: *mut c_void) -> c_int {
    let os = unsafe { mcctrl_sysfs_usrdata_os_bridge(udp) };
    let dev = unsafe { mcctrl_sysfs_os_to_dev_bridge(os) };
    let mut node_id = 0;
    let count = unsafe { mcctrl_usrdata_numa_count_bridge(udp) };

    while node_id < count {
        let linux_node = unsafe { mckernel_numa_2_linux_numa(udp, node_id) };
        let saved = unsafe { mcctrl_sysfs_get_node_topology_bridge(dev, linux_node) };
        if sysfs_is_err(saved) {
            break;
        }
        if saved.is_null() {
            node_id += 1;
            continue;
        }

        let topology = unsafe { get_one_node_topology(udp, saved) };
        if sysfs_is_err(topology) {
            let error = sysfs_ptr_err(topology);
            unsafe {
                mcctrl_sysfs_log_error_bridge(
                    b"get_node_topology:get_one_node_topology\0".as_ptr().cast(),
                    error,
                )
            };
            return error;
        }

        unsafe {
            mcctrl_sysfs_node_set_mckernel_id_bridge(topology, node_id);
            mcctrl_sysfs_add_node_to_usrdata_bridge(udp, topology);
        }
        node_id += 1;
    }

    0
}

unsafe fn fill_node_distance_string(udp: *mut c_void, node: *mut c_void) {
    let distance = unsafe { mcctrl_sysfs_node_distance_string_bridge(node) };
    if distance.is_null() {
        return;
    }

    let from = unsafe { mcctrl_sysfs_node_mckernel_id_bridge(node) };
    let mut offset = 0usize;
    let count = unsafe { mcctrl_usrdata_numa_count_bridge(udp) };
    let mut target = 0;

    while target < count && offset < SYSFS_NODE_DISTANCE_S_SIZE {
        if target > 0 {
            let written = unsafe {
                snprintf(
                    distance.add(offset),
                    SYSFS_NODE_DISTANCE_S_SIZE - offset,
                    b"%s\0".as_ptr().cast(),
                    b" \0".as_ptr().cast::<c_char>(),
                )
            };
            if written > 0 {
                offset = offset.saturating_add(written as usize);
            }
        }

        let value = unsafe {
            mcctrl_sysfs_node_distance_bridge(
                mckernel_numa_2_linux_numa(udp, from),
                mckernel_numa_2_linux_numa(udp, target),
            )
        };
        let written = unsafe {
            snprintf(
                distance.add(offset),
                SYSFS_NODE_DISTANCE_S_SIZE - offset,
                b"%d\0".as_ptr().cast(),
                value,
            )
        };
        if written > 0 {
            offset = offset.saturating_add(written as usize);
        }
        target += 1;
    }
}

unsafe fn setup_node_files(udp: *mut c_void) -> c_int {
    let error = unsafe { get_node_topology(udp) };
    if error != 0 {
        unsafe {
            mcctrl_sysfs_log_error_bridge(
                b"setup_node_files:get_node_topology\0".as_ptr().cast(),
                error,
            )
        };
        return error;
    }

    let numa_online = unsafe { mcctrl_sysfs_numa_online_bridge(udp) };
    unsafe {
        memset(numa_online, 0, mcctrl_sysfs_numa_online_size_bridge());
    }
    let mut node_id = 0;
    let count = unsafe { mcctrl_usrdata_numa_count_bridge(udp) };
    while node_id < count {
        unsafe { mcctrl_sysfs_node_set_bridge(node_id, numa_online) };
        node_id += 1;
    }

    let os = unsafe { mcctrl_sysfs_usrdata_os_bridge(udp) };
    let mut param = SysfsmBitmapParam {
        nbits: unsafe { mcctrl_sysfs_max_numnodes_bridge() },
        padding: 0,
        ptr: numa_online,
    };
    unsafe {
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/node/online\0".as_ptr().cast(),
        );
        sysfsm_createf(
            os,
            sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
            (&raw mut param).cast::<c_void>(),
            0o444,
            b"/sys/devices/system/node/possible\0".as_ptr().cast(),
        );
    }

    let mut topology = unsafe { mcctrl_sysfs_first_node_topology_bridge(udp) };
    while !topology.is_null() {
        let mut node_handle = SysfsHandle { handle: 0 };
        let mut cpu_handle = SysfsHandle { handle: 0 };
        let node_num = unsafe { mcctrl_sysfs_node_mckernel_id_bridge(topology) };
        param.nbits = unsafe { mcctrl_sysfs_nr_cpu_ids_bridge() };
        param.ptr = unsafe { mcctrl_sysfs_node_cpumap_bridge(topology) };

        unsafe { fill_node_distance_string(udp, topology) };
        unsafe {
            sysfsm_createf(
                os,
                sysfs_special_ops(SYSFS_SNOOPING_OPS_S_VALUE),
                mcctrl_sysfs_node_distance_string_bridge(topology).cast::<c_void>(),
                0o444,
                b"/sys/devices/system/node/node%d/distance\0"
                    .as_ptr()
                    .cast(),
                node_num,
            );
            sysfsm_createf(
                os,
                sysfs_special_ops(SYSFS_SNOOPING_OPS_PB_VALUE),
                (&raw mut param).cast::<c_void>(),
                0o444,
                b"/sys/devices/system/node/node%d/cpumap\0".as_ptr().cast(),
                node_num,
            );
            sysfsm_createf(
                os,
                sysfs_special_ops(SYSFS_SNOOPING_OPS_PBL_VALUE),
                (&raw mut param).cast::<c_void>(),
                0o444,
                b"/sys/devices/system/node/node%d/cpulist\0".as_ptr().cast(),
                node_num,
            );
        }

        let error = unsafe {
            sysfsm_lookupf(
                os,
                &raw mut node_handle,
                b"/sys/devices/system/node/node%d\0".as_ptr().cast(),
                node_num,
            )
        };
        unsafe { sysfs_panic_on(error, b"sysfsm_lookupf(node)\0") };
        let error = unsafe {
            sysfsm_symlinkf(
                os,
                node_handle,
                b"/sys/bus/node/devices/node%d\0".as_ptr().cast(),
                node_num,
            )
        };
        unsafe { sysfs_panic_on(error, b"sysfsm_symlinkf(bus node)\0") };

        let mut cpu = 0;
        let cpu_count = unsafe { mcctrl_usrdata_cpu_count_bridge(udp) };
        while cpu < cpu_count {
            let linux_cpu = unsafe { mckernel_cpu_2_linux_cpu(udp, cpu) };
            let linux_node = unsafe { mcctrl_sysfs_cpu_to_node_bridge(linux_cpu) };
            if unsafe { linux_numa_2_mckernel_numa(udp, linux_node) } != node_num {
                cpu += 1;
                continue;
            }

            let error = unsafe {
                sysfsm_symlinkf(
                    os,
                    node_handle,
                    b"/sys/devices/system/cpu/cpu%d/node%d\0".as_ptr().cast(),
                    cpu,
                    node_num,
                )
            };
            unsafe { sysfs_panic_on(error, b"sysfsm_symlinkf(node in CPU)\0") };

            let error = unsafe {
                sysfsm_lookupf(
                    os,
                    &raw mut cpu_handle,
                    b"/sys/devices/system/cpu/cpu%d\0".as_ptr().cast(),
                    cpu,
                )
            };
            unsafe { sysfs_panic_on(error, b"sysfsm_lookupf(CPU in node)\0") };

            let error = unsafe {
                sysfsm_symlinkf(
                    os,
                    cpu_handle,
                    b"/sys/devices/system/node/node%d/cpu%d\0".as_ptr().cast(),
                    node_num,
                    cpu,
                )
            };
            unsafe { sysfs_panic_on(error, b"sysfsm_symlinkf(CPU in node)\0") };
            cpu += 1;
        }

        topology = unsafe { mcctrl_sysfs_next_node_topology_bridge(udp, topology) };
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn setup_sysfs_files(os: *mut c_void) {
    let udp = unsafe { mcctrl_sysfs_get_usrdata_bridge(os) };
    if udp.is_null() {
        unsafe { sysfs_panic(b"setup_sysfs_files: error: mcctrl_usrdata not found\n\0") };
    }

    let error = unsafe {
        sysfsm_mkdirf(
            os,
            null_mut::<SysfsHandle>(),
            b"/sys/test/x.dir\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_mkdir(x.dir)\0") };

    let error = unsafe {
        sysfsm_createf(
            os,
            &raw mut show_int_ops,
            (&raw mut SYSFS_A_VALUE).cast::<c_void>(),
            0o444,
            b"/sys/test/a.dir/a_value\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_createf\0") };

    let mut handle = SysfsHandle { handle: 0 };
    let error = unsafe {
        sysfsm_lookupf(
            os,
            &raw mut handle,
            b"/sys/test/%s\0".as_ptr().cast(),
            b"a.dir\0".as_ptr().cast::<c_char>(),
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_lookupf(a.dir)\0") };

    let error = unsafe {
        sysfsm_symlinkf(
            os,
            handle,
            b"/sys/test/%c.dir\0".as_ptr().cast(),
            b'L' as c_int,
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_symlinkf\0") };

    let error = unsafe {
        sysfsm_unlinkf(
            os,
            0,
            b"/sys/test/%s.dir\0".as_ptr().cast(),
            b"x\0".as_ptr().cast::<c_char>(),
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_unlinkf\0") };

    unsafe {
        setup_local_snooping_files(os);
        setup_cpus_sysfs_files(udp);
        let _ = setup_node_files(udp);
    }

    let error = unsafe {
        sysfsm_mkdirf(
            os,
            null_mut::<SysfsHandle>(),
            b"/sys/setup_complete\0".as_ptr().cast(),
        )
    };
    unsafe { sysfs_panic_on(error, b"sysfsm_mkdir(complete)\0") };
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_read_buffer_status_result(
    buf: *mut c_char,
    size: usize,
    bytes_read: c_long,
) -> c_int {
    if bytes_read < 0 {
        return bytes_read as c_int;
    }
    if buf.is_null() || bytes_read as usize >= size {
        return -ENOSPC;
    }

    *buf.add(bytes_read as usize) = NUL;
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_parse_long_result(
    buf: *const c_char,
    value_out: *mut c_long,
) -> c_int {
    if buf.is_null() || value_out.is_null() {
        return 0;
    }

    let mut pos = 0usize;
    while is_ascii_space(c_byte(buf, pos)) {
        pos += 1;
    }

    let mut negative = false;
    if c_byte(buf, pos) == b'-' {
        negative = true;
        pos += 1;
    } else if c_byte(buf, pos) == b'+' {
        pos += 1;
    }

    let mut saw_digit = false;
    let mut value = 0 as c_long;
    loop {
        let byte = c_byte(buf, pos);
        if !byte.is_ascii_digit() {
            break;
        }

        saw_digit = true;
        value = value.wrapping_mul(10).wrapping_add((byte - b'0') as c_long);
        pos += 1;
    }

    if !saw_digit {
        return 0;
    }

    *value_out = if negative {
        value.wrapping_neg()
    } else {
        value
    };
    1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pci_realpath_valid_result(path: *const c_char) -> c_int {
    starts_with(path, b"../../../devices/") as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_hash_result(ptr: c_ulong, mask: c_ulong) -> c_int {
    (ptr & mask) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_eq_result(a: c_ulong, b: c_ulong) -> c_int {
    (a == b) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_lookup_match_result(
    entry_filp: c_ulong,
    filp: c_ulong,
    entry_group_leader: c_ulong,
    group_leader: c_ulong,
) -> c_int {
    (entry_filp == filp && entry_group_leader == group_leader) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_remove_match_result(
    entry_filp: c_ulong,
    filp: c_ulong,
    entry_os: c_ulong,
    os: c_ulong,
    entry_group_leader: c_ulong,
    group_leader: c_ulong,
    entry_fd: c_int,
    fd: c_int,
) -> c_int {
    (entry_filp == filp && entry_os == os && entry_group_leader == group_leader && entry_fd == fd)
        as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_path_result(path: *const c_char) -> c_int {
    starts_with(path, TOFU_DEV_PREFIX) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_tofu_dev_tail_offset_result() -> usize {
    TOFU_DEV_PREFIX.len()
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_name_copy_result(
    dst: *mut c_char,
    dst_size: usize,
    path: *const c_char,
) {
    if dst.is_null() || dst_size == 0 || path.is_null() {
        return;
    }

    let src = path.add(TOFU_DEV_PREFIX.len());
    let mut i = 0usize;
    let mut pad = false;
    while i < dst_size {
        let byte = if pad { 0 } else { c_byte(src, i) };
        *dst.add(i) = byte as c_char;
        if byte == 0 {
            pad = true;
        }
        i += 1;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_cq_path_parse_result(
    path: *const c_char,
    tni_out: *mut c_int,
    cq_out: *mut c_int,
) -> c_int {
    if path.is_null() || tni_out.is_null() || cq_out.is_null() {
        return 0;
    }

    if !starts_with(path, TOFU_CQ_PREFIX) {
        return 0;
    }

    let mut pos = TOFU_CQ_PREFIX.len();
    if !parse_i32_at(path, &mut pos, tni_out) {
        return 0;
    }

    if c_byte(path, pos) != b'c' || c_byte(path, pos + 1) != b'q' {
        return 0;
    }
    pos += 2;

    if !parse_i32_at(path, &mut pos, cq_out) {
        return 0;
    }

    (c_byte(path, pos) == 0) as c_int
}

#[inline(always)]
fn sysfs_ops_is_special(ops: *mut c_void) -> bool {
    let value = ops as c_long;
    (SYSFS_SPECIAL_OPS_MIN..=SYSFS_SPECIAL_OPS_MAX).contains(&value)
}

#[no_mangle]
pub extern "C" fn is_special_sysfs_ops(ops: *mut c_void) -> c_int {
    sysfs_ops_is_special(ops) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_sysfs_inited_result(sysfs_buf: c_ulong) -> c_int {
    (sysfs_buf != 0) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_path_error_result(
    path: *const c_char,
    written: c_long,
    path_size: usize,
) -> c_int {
    if written as usize >= path_size {
        return -ENAMETOOLONG;
    }

    if path.is_null() || c_byte(path, 0) != b'/' {
        return -ENOENT;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_binfmt_skip_path_result(path: *const c_char) -> c_int {
    if path.is_null() {
        return 1;
    }

    let mut i = 0usize;
    let mut slash = usize::MAX;
    while c_byte(path, i) != 0 {
        if c_byte(path, i) == b'/' {
            slash = i;
        }
        i += 1;
    }
    if slash != usize::MAX {
        let tail = path.add(slash);
        return (equals_bytes(tail, b"/mcexec")
            || equals_bytes(tail, b"/ihkosctl")
            || equals_bytes(tail, b"/ihkconfig")) as c_int;
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_path_allowed_result(
    file: *const c_char,
    list: *const c_char,
) -> c_int {
    if file.is_null() || list.is_null() {
        return 0;
    }
    if *list == NUL {
        return 1;
    }

    let mut p = 0usize;
    while *list.add(p) != NUL {
        let mut q = p;
        while *list.add(q) != NUL && *list.add(q) != b':' as c_char {
            q += 1;
        }

        let mut end = q;
        while end > p && *list.add(end - 1) == b'/' as c_char {
            end -= 1;
        }

        let mut matched = true;
        let mut i = p;
        while i < end {
            if *file.add(i - p) != *list.add(i) {
                matched = false;
                break;
            }
            i += 1;
        }

        if matched && *file.add(end - p) == b'/' as c_char {
            return 1;
        }

        if *list.add(q) == NUL {
            break;
        }
        p = q + 1;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_treat_as_device_path_result(path: *const c_char) -> c_int {
    let ompi = starts_with(path, b"/tmp/ompi.");
    let dev_shm = starts_with(path, b"/dev/shm/");
    let ple = starts_with(path, b"/var/opt/FJSVtcs/ple/daemonif/")
        && !contains_bytes(path, b"dstore_sm.lock");

    (ompi || dev_shm || ple) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_should_populate_path_result(path: *const c_char) -> c_int {
    (starts_with(path, b"/tmp/ompi.")
        || starts_with(path, b"/dev/shm/")
        || starts_with(path, b"/var/opt/FJSVtcs/ple/daemonif/")) as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_tmpfs_result(name: *const c_char) -> c_int {
    equals_bytes(name, b"tmpfs") as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_proc_result(name: *const c_char) -> c_int {
    equals_bytes(name, b"proc") as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_special_char_device_result(major: u32, minor: u32) -> c_int {
    (major == 1 && (minor == 1 || minor == 5)) as c_int
}

unsafe fn write_decimal_name(
    buf: *mut c_char,
    buflen: usize,
    prefix: &[u8],
    value: c_int,
) -> c_int {
    if buf.is_null() || buflen == 0 {
        return -1;
    }

    let mut tmp = [0u8; 16];
    let negative = value < 0;
    let mut n = if negative {
        (-(value as i64)) as u64
    } else {
        value as u64
    };
    let mut digits = 0usize;

    loop {
        *tmp.as_mut_ptr().add(digits) = b'0' + (n % 10) as u8;
        digits += 1;
        n /= 10;
        if n == 0 {
            break;
        }
    }

    let sign_len = negative as usize;
    let total = prefix.len() + sign_len + digits;
    if total + 1 > buflen {
        return -1;
    }

    let mut pos = 0usize;
    while pos < prefix.len() {
        *buf.add(pos) = *prefix.as_ptr().add(pos) as c_char;
        pos += 1;
    }
    if negative {
        *buf.add(pos) = b'-' as c_char;
        pos += 1;
    }
    while digits > 0 {
        digits -= 1;
        *buf.add(pos) = *tmp.as_ptr().add(digits) as c_char;
        pos += 1;
    }
    *buf.add(pos) = NUL;
    pos as c_int
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_mcos_name_result(
    buf: *mut c_char,
    buflen: usize,
    osnum: c_int,
) -> c_int {
    write_decimal_name(buf, buflen, b"mcos", osnum)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_decimal_name_result(
    buf: *mut c_char,
    buflen: usize,
    value: c_int,
) -> c_int {
    write_decimal_name(buf, buflen, b"", value)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_cmd_result(op: c_int) -> c_int {
    op & FUTEX_CMD_MASK
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_is_private_result(op: c_int) -> c_int {
    ((op & FUTEX_PRIVATE_FLAG) != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_clock_realtime_result(op: c_int) -> c_int {
    ((op & FUTEX_CLOCK_REALTIME) != 0) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_realtime_cmd_valid_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT_REQUEUE_PI) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_wait_uses_timeout_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_WAIT_BITSET || cmd == FUTEX_WAIT) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_arg3_is_val2_result(cmd: c_int) -> c_int {
    (cmd == FUTEX_CMP_REQUEUE || cmd == FUTEX_WAKE_OP) as c_int
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_op_label_result(cmd: c_int) -> *const c_char {
    let label = match cmd {
        FUTEX_WAIT => FUTEX_WAIT_LABEL,
        FUTEX_WAIT_BITSET => FUTEX_WAIT_BITSET_LABEL,
        FUTEX_WAKE => FUTEX_WAKE_LABEL,
        FUTEX_WAKE_OP => FUTEX_WAKE_OP_LABEL,
        FUTEX_WAKE_BITSET => FUTEX_WAKE_BITSET_LABEL,
        FUTEX_CMP_REQUEUE => FUTEX_CMP_REQUEUE_LABEL,
        FUTEX_REQUEUE => FUTEX_REQUEUE_LABEL,
        _ => FUTEX_UNKNOWN_LABEL,
    };

    label.as_ptr() as *const c_char
}

type McctrlRbFirstFn = Option<unsafe extern "C" fn(root: *mut McctrlRbRoot) -> *mut McctrlRbNode>;
type McctrlRbEraseFn =
    Option<unsafe extern "C" fn(node: *mut McctrlRbNode, root: *mut McctrlRbRoot)>;
type McctrlRbLinkFn = Option<
    unsafe extern "C" fn(
        node: *mut McctrlRbNode,
        parent: *mut McctrlRbNode,
        link: *mut *mut McctrlRbNode,
    ),
>;
type McctrlRbInsertColorFn =
    Option<unsafe extern "C" fn(node: *mut McctrlRbNode, root: *mut McctrlRbRoot)>;
type McctrlCacheFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;

#[no_mangle]
pub unsafe extern "C" fn mcctrl_rva_to_rpa_cache_search_body_result(
    root: *mut McctrlRbRoot,
    rva: c_ulong,
) -> *mut McctrlRvaToRpaCacheNode {
    if root.is_null() {
        return null_mut();
    }

    let mut iter = (*root).node;
    while !iter.is_null() {
        let inode = iter.cast::<McctrlRvaToRpaCacheNode>();
        if rva == (*inode).rva {
            return inode;
        }
        iter = if rva < (*inode).rva {
            (*iter).left
        } else {
            (*iter).right
        };
    }

    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_rva_to_rpa_cache_insert_body_result(
    root: *mut McctrlRbRoot,
    cache_node: *mut McctrlRvaToRpaCacheNode,
    link_node: McctrlRbLinkFn,
    insert_color: McctrlRbInsertColorFn,
) -> c_int {
    let (Some(link_node), Some(insert_color)) = (link_node, insert_color) else {
        return -EINVAL;
    };
    if root.is_null() || cache_node.is_null() {
        return -EINVAL;
    }

    let mut link: *mut *mut McctrlRbNode = &raw mut (*root).node;
    let mut parent: *mut McctrlRbNode = null_mut();

    while !(*link).is_null() {
        let inode = (*link).cast::<McctrlRvaToRpaCacheNode>();
        parent = *link;

        if (*cache_node).rva == (*inode).rva {
            return -EINVAL;
        }

        link = if (*cache_node).rva < (*inode).rva {
            &raw mut (*(*link)).left
        } else {
            &raw mut (*(*link)).right
        };
    }

    link_node(&raw mut (*cache_node).node, parent, link);
    insert_color(&raw mut (*cache_node).node, root);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_futex_remove_process_body_result(
    root: *mut McctrlRbRoot,
    rb_first: McctrlRbFirstFn,
    rb_erase: McctrlRbEraseFn,
    free_node: McctrlCacheFreeFn,
) -> c_int {
    let (Some(rb_first), Some(rb_erase), Some(free_node)) = (rb_first, rb_erase, free_node) else {
        return -EINVAL;
    };
    if root.is_null() {
        return -EINVAL;
    }

    loop {
        let node = rb_first(root);
        if node.is_null() {
            break;
        }
        rb_erase(node, root);
        free_node(node.cast::<c_void>());
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_lwk_to_linux_index(
    mapping: *const c_int,
    count: c_int,
    index: c_int,
) -> c_int {
    mcctrl_lwk_to_linux_index_result(mapping, count, index)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_linux_to_lwk_index(
    mapping: *const c_int,
    count: c_int,
    linux_id: c_int,
) -> c_int {
    mcctrl_linux_to_lwk_index_result(mapping, count, linux_id)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fill_sequential_bitset(
    bits: *mut c_ulong,
    bit_count: c_int,
    word_count: c_int,
    bits_per_word: c_int,
) {
    mcctrl_fill_sequential_bitset_result(bits, bit_count, word_count, bits_per_word);
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_read_buffer_status(
    buf: *mut c_char,
    size: usize,
    bytes_read: c_long,
) -> c_int {
    mcctrl_read_buffer_status_result(buf, size, bytes_read)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_parse_long(buf: *const c_char, value_out: *mut c_long) -> c_int {
    mcctrl_parse_long_result(buf, value_out)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pci_realpath_valid(path: *const c_char) -> c_int {
    mcctrl_pci_realpath_valid_result(path)
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_hash(ptr: *const c_void, mask: c_ulong) -> c_int {
    mcctrl_ptr_hash_result(ptr as c_ulong, mask)
}

#[no_mangle]
pub extern "C" fn mcctrl_ptr_eq(a: *const c_void, b: *const c_void) -> c_int {
    mcctrl_ptr_eq_result(a as c_ulong, b as c_ulong)
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_lookup_match(
    entry_filp: *const c_void,
    filp: *const c_void,
    entry_group_leader: *const c_void,
    group_leader: *const c_void,
) -> c_int {
    mcctrl_file_to_pidfd_lookup_match_result(
        entry_filp as c_ulong,
        filp as c_ulong,
        entry_group_leader as c_ulong,
        group_leader as c_ulong,
    )
}

#[no_mangle]
pub extern "C" fn mcctrl_file_to_pidfd_remove_match(
    entry_filp: *const c_void,
    filp: *const c_void,
    entry_os: *const c_void,
    os: *const c_void,
    entry_group_leader: *const c_void,
    group_leader: *const c_void,
    entry_fd: c_int,
    fd: c_int,
) -> c_int {
    mcctrl_file_to_pidfd_remove_match_result(
        entry_filp as c_ulong,
        filp as c_ulong,
        entry_os as c_ulong,
        os as c_ulong,
        entry_group_leader as c_ulong,
        group_leader as c_ulong,
        entry_fd,
        fd,
    )
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_path(path: *const c_char) -> c_int {
    mcctrl_tofu_dev_path_result(path)
}

#[no_mangle]
pub extern "C" fn mcctrl_tofu_dev_tail_offset() -> c_ulong {
    mcctrl_tofu_dev_tail_offset_result() as c_ulong
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_dev_name_copy(
    dst: *mut c_char,
    dst_size: usize,
    path: *const c_char,
) {
    mcctrl_tofu_dev_name_copy_result(dst, dst_size, path);
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_tofu_cq_path_parse(
    path: *const c_char,
    tni_out: *mut c_int,
    cq_out: *mut c_int,
) -> c_int {
    mcctrl_tofu_cq_path_parse_result(path, tni_out, cq_out)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_sysfs_path_error(
    path: *const c_char,
    written: c_long,
    path_size: usize,
) -> c_int {
    mcctrl_sysfs_path_error_result(path, written, path_size)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_binfmt_skip_path(path: *const c_char) -> c_int {
    mcctrl_binfmt_skip_path_result(path)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_path_allowed(file: *const c_char, list: *const c_char) -> c_int {
    mcctrl_path_allowed_result(file, list)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_treat_as_device_path(path: *const c_char) -> c_int {
    mcctrl_pager_treat_as_device_path_result(path)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_pager_should_populate_path(path: *const c_char) -> c_int {
    mcctrl_pager_should_populate_path_result(path)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_tmpfs(name: *const c_char) -> c_int {
    mcctrl_fs_is_tmpfs_result(name)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_fs_is_proc(name: *const c_char) -> c_int {
    mcctrl_fs_is_proc_result(name)
}

#[no_mangle]
pub extern "C" fn mcctrl_special_char_device(major: c_uint, minor: c_uint) -> c_int {
    mcctrl_special_char_device_result(major, minor)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_mcos_name(
    buf: *mut c_char,
    buflen: usize,
    osnum: c_int,
) -> c_int {
    mcctrl_format_mcos_name_result(buf, buflen, osnum)
}

#[no_mangle]
pub unsafe extern "C" fn mcctrl_format_decimal_name(
    buf: *mut c_char,
    buflen: usize,
    value: c_int,
) -> c_int {
    mcctrl_format_decimal_name_result(buf, buflen, value)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_cmd(op: c_int) -> c_int {
    mcctrl_futex_cmd_result(op)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_is_private(op: c_int) -> c_int {
    mcctrl_futex_is_private_result(op)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_clock_realtime(op: c_int) -> c_int {
    mcctrl_futex_clock_realtime_result(op)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_realtime_cmd_valid(cmd: c_int) -> c_int {
    mcctrl_futex_realtime_cmd_valid_result(cmd)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_wait_uses_timeout(cmd: c_int) -> c_int {
    mcctrl_futex_wait_uses_timeout_result(cmd)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_arg3_is_val2(cmd: c_int) -> c_int {
    mcctrl_futex_arg3_is_val2_result(cmd)
}

#[no_mangle]
pub extern "C" fn mcctrl_futex_op_label(cmd: c_int) -> *const c_char {
    mcctrl_futex_op_label_result(cmd)
}
