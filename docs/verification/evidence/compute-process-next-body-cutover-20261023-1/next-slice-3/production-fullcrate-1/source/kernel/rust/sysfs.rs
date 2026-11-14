use core::{
    ffi::c_void,
    mem::size_of,
    ptr::null_mut,
    sync::atomic::{fence, Ordering},
};

use crate::abi::{
    CInt, CLong, CULong, CpuLocalVar, IkcScdPacket, SizeT, SysfsBitmapParam, SysfsHandle, SysfsOps,
    SysfsReqCreateParam, SysfsReqLookupParam, SysfsReqMkdirParam, SysfsReqSetupParam,
    SysfsReqSymlinkParam, SysfsReqUnlinkParam,
};

const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const ENOENT: CInt = 2;
const ENAMETOOLONG: CInt = 36;
const PAGE_P2ALIGN: CInt = 0;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_KERNEL: CInt = 0;
const SYSFS_PATH_MAX: SizeT = 1024;
const SYSFS_SPECIAL_OPS_MIN: CLong = 1;
const SYSFS_SPECIAL_OPS_MAX: CLong = 1000;
const SCD_MSG_SYSFS_REQ_CREATE: CInt = 0x30;
const SCD_MSG_SYSFS_REQ_MKDIR: CInt = 0x32;
const SCD_MSG_SYSFS_REQ_SYMLINK: CInt = 0x34;
const SCD_MSG_SYSFS_REQ_LOOKUP: CInt = 0x36;
const SCD_MSG_SYSFS_REQ_UNLINK: CInt = 0x38;
const SYSFS_REQUEST_LOG_SEND_ERROR: CInt = 1;
const SYSFS_REQUEST_LOG_RESPONSE_ERROR: CInt = 2;
const SYSFS_INIT_STAGE_SIZE: CInt = 1;
const SYSFS_INIT_STAGE_DATA_ALLOC: CInt = 2;
const SYSFS_INIT_STAGE_PARAM_ALLOC: CInt = 3;
const SYSFS_INIT_STAGE_REQUEST: CInt = 4;
const SYSFS_REQUEST_PHASE_SEND: CInt = 1;
const SYSFS_REQUEST_PHASE_RESPONSE: CInt = 2;
const SYSFSS_REQ_LOG_CALLBACK_ERROR: CInt = 1;
const SYSFSS_REQ_LOG_SEND_ERROR: CInt = 2;
const SYSFSS_REQ_LOG_PACKET_ERROR: CInt = 3;
const SYSFSS_REQ_LOG_DEBUG: CInt = 4;

const FILE: &[u8] = b"kernel/rust/sysfs.rs\0";
const ALLOC_FAILED_FMT: &[u8] = b"%s:allocate_pages failed. %d\n\0";
const CREATE_SETUP_FAILED_FMT: &[u8] = b"sysfs_createf:setup_special_create failed. %d\n\0";
const SETUP_UNKNOWN_OPS_FMT: &[u8] = b"setup_special_create:unknown ops %#lx\n\0";
const TOO_LONG_FMT: &[u8] = b"%s:vsnprintf failed. %d\n\0";
const NOT_ABSOLUTE_FMT: &[u8] = b"%s:not an absolute path. %d\n\0";
const CREATE_FINAL_FMT: &[u8] = b"sysfs_createf(%p,%p,%#o,%s,...): %d\n\0";
const MKDIR_FINAL_FMT: &[u8] = b"sysfs_mkdirf(%p,%s,...): %d\n\0";
const SYMLINK_FINAL_FMT: &[u8] = b"sysfs_symlinkf(%#lx,%s,...): %d\n\0";
const LOOKUP_FINAL_FMT: &[u8] = b"sysfs_lookupf(%p,%s,...): %d\n\0";
const UNLINK_FINAL_FMT: &[u8] = b"sysfs_unlinkf(%#x,%s,...): %d\n\0";
const CREATE_NAME: &[u8] = b"sysfs_createf\0";
const MKDIR_NAME: &[u8] = b"sysfs_mkdirf\0";
const SYMLINK_NAME: &[u8] = b"sysfs_symlinkf\0";
const LOOKUP_NAME: &[u8] = b"sysfs_lookupf\0";
const UNLINK_NAME: &[u8] = b"sysfs_unlinkf\0";
const SEND_CREATE_FMT: &[u8] = b"sysfs_createf:ihk_ikc_send failed. %d\n\0";
const SEND_MKDIR_FMT: &[u8] = b"sysfs_mkdirf:ihk_ikc_send failed. %d\n\0";
const SEND_SYMLINK_FMT: &[u8] = b"sysfs_symlinkf:ihk_ikc_send failed. %d\n\0";
const SEND_LOOKUP_FMT: &[u8] = b"sysfs_lookupf:ihk_ikc_send failed. %d\n\0";
const SEND_UNLINK_FMT: &[u8] = b"sysfs_unlinkf:ihk_ikc_send failed. %d\n\0";
const RESP_CREATE_FMT: &[u8] = b"sysfs_createf:SCD_MSG_SYSFS_REQ_CREATE failed. %d\n\0";
const RESP_MKDIR_FMT: &[u8] = b"sysfs_mkdirf:SCD_MSG_SYSFS_REQ_MKDIR failed. %d\n\0";
const RESP_SYMLINK_FMT: &[u8] = b"sysfs_symlinkf:SCD_MSG_SYSFS_REQ_SYMLINK failed. %d\n\0";
const RESP_LOOKUP_FMT: &[u8] = b"sysfs_lookupf:SCD_MSG_SYSFS_REQ_LOOKUP failed. %d\n\0";
const RESP_UNLINK_FMT: &[u8] = b"sysfs_unlinkf:SCD_MSG_SYSFS_REQ_UNLINK failed. %d\n\0";
const SHOW_CALLBACK_FMT: &[u8] = b"sysfss_req_show:->show failed. %ld\n\0";
const SHOW_SEND_FMT: &[u8] = b"sysfss_req_show:ihk_ikc_send failed. %d\n\0";
const SHOW_PACKET_FMT: &[u8] = b"sysfss_req_show(%#lx,%p,%p): %d %d\n\0";
const SHOW_DEBUG_FMT: &[u8] = b"sysfss_req_show(%#lx,%p,%p): %d %d %ld\n\0";
const STORE_CALLBACK_FMT: &[u8] = b"sysfss_req_store:->store failed. %ld\n\0";
const STORE_SEND_FMT: &[u8] = b"sysfss_req_store:ihk_ikc_send failed. %d\n\0";
const STORE_PACKET_FMT: &[u8] = b"sysfss_req_store(%#lx,%p,%p,%d): %d %d\n\0";
const STORE_DEBUG_FMT: &[u8] = b"sysfss_req_store(%#lx,%p,%p,%d): %d %d %ld\n\0";
const RELEASE_SEND_FMT: &[u8] = b"sysfss_req_release:ihk_ikc_send failed. %d\n\0";
const RELEASE_PACKET_FMT: &[u8] = b"sysfss_req_release(%#lx,%p,%p): %d %d\n\0";
const RELEASE_DEBUG_FMT: &[u8] = b"sysfss_req_release(%#lx,%p,%p): %d %d\n\0";
const UNKNOWN_PACKET_FMT: &[u8] =
    b"sysfss_packet_handler:unknown message. msg %d error %d arg1 %#lx arg2 %#lx arg3 %#lx\n\0";
const INIT_SIZE_FMT: &[u8] = b"sysfs_init:struct sysfs_*_req_param too large. %d\n\0";
const INIT_DATA_ALLOC_FMT: &[u8] = b"sysfs_init:allocate_pages(buf) failed. %d\n\0";
const INIT_PARAM_ALLOC_FMT: &[u8] = b"sysfs_init:allocate_pages(param) failed. %d\n\0";
const INIT_SEND_FMT: &[u8] = b"sysfs_init:ihk_ikc_send failed. %d\n\0";
const INIT_RESP_FMT: &[u8] = b"sysfs_init:SCD_MSG_SYSFS_REQ_SETUP failed. %d\n\0";
const INIT_FINAL_FMT: &[u8] = b"sysfs_init(): %d\n\0";
const INIT_SIZE_PANIC: &[u8] = b"struct sysfs_*_req_param too large\0";
const INIT_PANIC: &[u8] = b"sysfs_init\0";

static mut SYSFS_DATA_BUFSIZE: SizeT = 0;
static mut SYSFS_DATA_BUF: *mut c_void = null_mut();

unsafe extern "C" {
    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void;
    fn _ihk_mc_free_pages(ptr: *mut c_void, npages: CInt, is_user: CInt, file: *mut i8, line: CInt);
    fn virt_to_phys(v: *mut c_void) -> CULong;
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut IkcScdPacket, flags: CInt) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar;
    fn cpu_pause();
    fn kprintf(format: *const i8, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(format: *const i8) -> !;
}

#[inline(always)]
fn file_ptr() -> *mut i8 {
    FILE.as_ptr() as *mut i8
}

#[inline(always)]
unsafe fn alloc_pages(npages: CInt, flags: CULong) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flags,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        file_ptr(),
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn free_pages(ptr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(ptr, npages, IHK_MC_PG_KERNEL, file_ptr(), line!() as CInt);
}

#[inline(always)]
unsafe fn current_ikc2linux() -> *mut c_void {
    let cpu = ihk_mc_get_processor_id();
    let local = get_cpu_local_var_result(cpu);
    if local.is_null() {
        null_mut()
    } else {
        (*local).ikc2linux
    }
}

#[inline(always)]
fn sysfs_ops_is_special(ops: *mut c_void) -> bool {
    let value = ops as CLong;
    (SYSFS_SPECIAL_OPS_MIN..=SYSFS_SPECIAL_OPS_MAX).contains(&value)
}

#[no_mangle]
pub extern "C" fn is_special_sysfs_ops(ops: *mut c_void) -> CInt {
    sysfs_ops_is_special(ops) as CInt
}

#[inline(always)]
unsafe fn format_path(path: *mut i8, fmt: *const i8, args: &mut core::ffi::VaList<'_>) -> CInt {
    crate::numparse::vsnprintf_va_list_result(path, SYSFS_PATH_MAX, fmt, args)
}

#[inline(always)]
unsafe fn validate_path(func: &[u8], n: CInt, path: *const i8) -> CInt {
    let error = crate::object_helpers::sysfs_path_error_result(
        n as CLong,
        (!path.is_null() && *path == b'/' as i8) as CInt,
        SYSFS_PATH_MAX,
    );
    if error == -ENAMETOOLONG {
        kprintf(TOO_LONG_FMT.as_ptr().cast(), func.as_ptr(), error);
    } else if error == -ENOENT {
        kprintf(NOT_ABSOLUTE_FMT.as_ptr().cast(), func.as_ptr(), error);
    }
    error
}

unsafe extern "C" fn sysfss_show_bridge(
    ops0: *mut c_void,
    instance: *mut c_void,
    buf: *mut c_void,
    bufsize: SizeT,
) -> CLong {
    let ops = ops0.cast::<SysfsOps>();
    if ops.is_null() {
        return -(EINVAL as CLong);
    }
    match (*ops).show {
        Some(show) => show(ops, instance, buf, bufsize) as CLong,
        None => -(EINVAL as CLong),
    }
}

unsafe extern "C" fn sysfss_store_bridge(
    ops0: *mut c_void,
    instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> CLong {
    let ops = ops0.cast::<SysfsOps>();
    if ops.is_null() {
        return -(EINVAL as CLong);
    }
    match (*ops).store {
        Some(store) => store(ops, instance, buf, size) as CLong,
        None => -(EINVAL as CLong),
    }
}

unsafe extern "C" fn sysfss_release_bridge(ops0: *mut c_void, instance: *mut c_void) {
    let ops = ops0.cast::<SysfsOps>();
    if !ops.is_null() {
        if let Some(release) = (*ops).release {
            release(ops, instance);
        }
    }
}

unsafe extern "C" fn sysfss_send_bridge(msg: CInt, err: CInt, arg1: CLong, arg2: CLong) -> CInt {
    let mut packet: IkcScdPacket = core::mem::zeroed();
    let prep = crate::object_helpers::sysfss_packet_prepare_result(
        &mut packet as *mut IkcScdPacket,
        msg,
        err,
        arg1,
        arg2,
    );
    if prep != 0 {
        return prep;
    }
    ihk_ikc_send(current_ikc2linux(), &mut packet as *mut IkcScdPacket, 0)
}

unsafe extern "C" fn sysfs_request_send_bridge(msg: CInt, arg1: CLong) -> CInt {
    let mut packet: IkcScdPacket = core::mem::zeroed();
    let prep = crate::object_helpers::sysfs_request_packet_prepare_result(
        &mut packet as *mut IkcScdPacket,
        msg,
        arg1,
    );
    if prep != 0 {
        return prep;
    }
    ihk_ikc_send(current_ikc2linux(), &mut packet as *mut IkcScdPacket, 0)
}

unsafe extern "C" fn sysfs_request_pause_bridge() {
    cpu_pause();
}

unsafe extern "C" fn sysfs_request_barrier_bridge() {
    fence(Ordering::SeqCst);
}

unsafe extern "C" fn sysfs_init_alloc_bridge(npages: CInt, flags: CULong) -> *mut c_void {
    alloc_pages(npages, flags)
}

unsafe extern "C" fn sysfs_init_free_bridge(addr: *mut c_void, npages: CInt) {
    free_pages(addr, npages);
}

unsafe extern "C" fn sysfs_init_phys_bridge(addr: *mut c_void) -> CLong {
    virt_to_phys(addr) as CLong
}

unsafe fn setup_special_create(
    param: *mut SysfsReqCreateParam,
    pbp: *mut SysfsBitmapParam,
) -> CInt {
    let error = crate::object_helpers::sysfs_setup_special_create_result(
        param,
        pbp,
        Some(sysfs_init_phys_bridge),
    );
    if error != 0 {
        kprintf(SETUP_UNKNOWN_OPS_FMT.as_ptr().cast(), (*param).client_ops);
    }
    error
}

unsafe fn request_and_free(msg: CInt, param: *mut c_void, handlep: *mut CLong) -> CInt {
    crate::object_helpers::sysfs_request_logged_result(
        msg,
        param,
        virt_to_phys(param) as CLong,
        Some(sysfs_request_send_bridge),
        Some(sysfs_request_pause_bridge),
        Some(sysfs_request_barrier_bridge),
        handlep,
        Some(sysfs_public_request_log_bridge),
        null_mut(),
    )
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_createf(
    ops: *mut SysfsOps,
    instance: *mut c_void,
    mode: CInt,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    let param = alloc_pages(1, IHK_MC_AP_NOWAIT).cast::<SysfsReqCreateParam>();
    let mut error: CInt;
    let mut asbp = SysfsBitmapParam {
        nbits: 0,
        padding: 0,
        ptr: null_mut(),
    };

    if param.is_null() {
        error = -ENOMEM;
        kprintf(
            ALLOC_FAILED_FMT.as_ptr().cast(),
            CREATE_NAME.as_ptr(),
            error,
        );
        kprintf(
            CREATE_FINAL_FMT.as_ptr().cast(),
            ops,
            instance,
            mode,
            fmt,
            error,
        );
        return error;
    }

    (*param).client_ops = ops as CLong;
    (*param).client_instance = instance as CLong;
    (*param).mode = mode;
    (*param).busy = 1;

    let n = format_path((*param).path.as_mut_ptr(), fmt, &mut args);
    error = validate_path(CREATE_NAME, n, (*param).path.as_ptr());
    if error == 0 && sysfs_ops_is_special(ops.cast::<c_void>()) {
        error = setup_special_create(param, &mut asbp as *mut SysfsBitmapParam);
        if error != 0 {
            kprintf(CREATE_SETUP_FAILED_FMT.as_ptr().cast(), error);
        }
    }
    if error == 0 {
        error = request_and_free(SCD_MSG_SYSFS_REQ_CREATE, param.cast::<c_void>(), null_mut());
    }

    free_pages(param.cast::<c_void>(), 1);
    if error != 0 {
        kprintf(
            CREATE_FINAL_FMT.as_ptr().cast(),
            ops,
            instance,
            mode,
            fmt,
            error,
        );
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_mkdirf(
    dirhp: *mut SysfsHandle,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    let param = alloc_pages(1, IHK_MC_AP_NOWAIT).cast::<SysfsReqMkdirParam>();
    let mut error: CInt;

    if param.is_null() {
        error = -ENOMEM;
        kprintf(ALLOC_FAILED_FMT.as_ptr().cast(), MKDIR_NAME.as_ptr(), error);
        kprintf(MKDIR_FINAL_FMT.as_ptr().cast(), dirhp, fmt, error);
        return error;
    }

    (*param).busy = 1;
    let n = format_path((*param).path.as_mut_ptr(), fmt, &mut args);
    error = validate_path(MKDIR_NAME, n, (*param).path.as_ptr());
    if error == 0 {
        error = request_and_free(
            SCD_MSG_SYSFS_REQ_MKDIR,
            param.cast::<c_void>(),
            dirhp.cast::<CLong>(),
        );
    }

    free_pages(param.cast::<c_void>(), 1);
    if error != 0 {
        kprintf(MKDIR_FINAL_FMT.as_ptr().cast(), dirhp, fmt, error);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_symlinkf(
    targeth: SysfsHandle,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    let param = alloc_pages(1, IHK_MC_AP_NOWAIT).cast::<SysfsReqSymlinkParam>();
    let mut error: CInt;

    if param.is_null() {
        error = -ENOMEM;
        kprintf(
            ALLOC_FAILED_FMT.as_ptr().cast(),
            SYMLINK_NAME.as_ptr(),
            error,
        );
        kprintf(
            SYMLINK_FINAL_FMT.as_ptr().cast(),
            targeth.handle,
            fmt,
            error,
        );
        return error;
    }

    (*param).target = targeth.handle;
    (*param).busy = 1;
    let n = format_path((*param).path.as_mut_ptr(), fmt, &mut args);
    error = validate_path(SYMLINK_NAME, n, (*param).path.as_ptr());
    if error == 0 {
        error = request_and_free(
            SCD_MSG_SYSFS_REQ_SYMLINK,
            param.cast::<c_void>(),
            null_mut(),
        );
    }

    free_pages(param.cast::<c_void>(), 1);
    if error != 0 {
        kprintf(
            SYMLINK_FINAL_FMT.as_ptr().cast(),
            targeth.handle,
            fmt,
            error,
        );
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_lookupf(
    objhp: *mut SysfsHandle,
    fmt: *const i8,
    mut args: ...
) -> CInt {
    let param = alloc_pages(1, IHK_MC_AP_NOWAIT).cast::<SysfsReqLookupParam>();
    let mut error: CInt;

    if param.is_null() {
        error = -ENOMEM;
        kprintf(
            ALLOC_FAILED_FMT.as_ptr().cast(),
            LOOKUP_NAME.as_ptr(),
            error,
        );
        kprintf(LOOKUP_FINAL_FMT.as_ptr().cast(), objhp, fmt, error);
        return error;
    }

    (*param).busy = 1;
    let n = format_path((*param).path.as_mut_ptr(), fmt, &mut args);
    error = validate_path(LOOKUP_NAME, n, (*param).path.as_ptr());
    if error == 0 {
        error = request_and_free(
            SCD_MSG_SYSFS_REQ_LOOKUP,
            param.cast::<c_void>(),
            objhp.cast::<CLong>(),
        );
    }

    free_pages(param.cast::<c_void>(), 1);
    if error != 0 {
        kprintf(LOOKUP_FINAL_FMT.as_ptr().cast(), objhp, fmt, error);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_unlinkf(flags: CInt, fmt: *const i8, mut args: ...) -> CInt {
    let param = alloc_pages(1, IHK_MC_AP_NOWAIT).cast::<SysfsReqUnlinkParam>();
    let mut error: CInt;

    if param.is_null() {
        error = -ENOMEM;
        kprintf(
            ALLOC_FAILED_FMT.as_ptr().cast(),
            UNLINK_NAME.as_ptr(),
            error,
        );
        kprintf(UNLINK_FINAL_FMT.as_ptr().cast(), flags, fmt, error);
        return error;
    }

    (*param).flags = flags;
    (*param).busy = 1;
    let n = format_path((*param).path.as_mut_ptr(), fmt, &mut args);
    error = validate_path(UNLINK_NAME, n, (*param).path.as_ptr());
    if error == 0 {
        error = request_and_free(SCD_MSG_SYSFS_REQ_UNLINK, param.cast::<c_void>(), null_mut());
    }

    free_pages(param.cast::<c_void>(), 1);
    if error != 0 {
        kprintf(UNLINK_FINAL_FMT.as_ptr().cast(), flags, fmt, error);
    }
    error
}

unsafe extern "C" fn sysfs_public_request_log_bridge(event: CInt, msg: CInt, error: CInt) {
    let fmt = match (event, msg) {
        (SYSFS_REQUEST_LOG_SEND_ERROR, SCD_MSG_SYSFS_REQ_CREATE) => SEND_CREATE_FMT,
        (SYSFS_REQUEST_LOG_SEND_ERROR, SCD_MSG_SYSFS_REQ_MKDIR) => SEND_MKDIR_FMT,
        (SYSFS_REQUEST_LOG_SEND_ERROR, SCD_MSG_SYSFS_REQ_SYMLINK) => SEND_SYMLINK_FMT,
        (SYSFS_REQUEST_LOG_SEND_ERROR, SCD_MSG_SYSFS_REQ_LOOKUP) => SEND_LOOKUP_FMT,
        (SYSFS_REQUEST_LOG_SEND_ERROR, SCD_MSG_SYSFS_REQ_UNLINK) => SEND_UNLINK_FMT,
        (SYSFS_REQUEST_LOG_RESPONSE_ERROR, SCD_MSG_SYSFS_REQ_CREATE) => RESP_CREATE_FMT,
        (SYSFS_REQUEST_LOG_RESPONSE_ERROR, SCD_MSG_SYSFS_REQ_MKDIR) => RESP_MKDIR_FMT,
        (SYSFS_REQUEST_LOG_RESPONSE_ERROR, SCD_MSG_SYSFS_REQ_SYMLINK) => RESP_SYMLINK_FMT,
        (SYSFS_REQUEST_LOG_RESPONSE_ERROR, SCD_MSG_SYSFS_REQ_LOOKUP) => RESP_LOOKUP_FMT,
        (SYSFS_REQUEST_LOG_RESPONSE_ERROR, SCD_MSG_SYSFS_REQ_UNLINK) => RESP_UNLINK_FMT,
        _ => return,
    };
    kprintf(fmt.as_ptr().cast(), error);
}

unsafe fn sysfs_op_addr<T>(op: Option<T>) -> CULong {
    core::mem::transmute_copy::<Option<T>, CULong>(&op)
}

unsafe fn sysfss_req_show(nodeh: CLong, ops: *mut SysfsOps, instance: *mut c_void) {
    crate::object_helpers::sysfss_req_show_logged_result(
        nodeh,
        ops.cast::<c_void>(),
        instance,
        SYSFS_DATA_BUF,
        SYSFS_DATA_BUFSIZE,
        if ops.is_null() {
            0
        } else {
            sysfs_op_addr((*ops).show)
        },
        Some(sysfss_show_bridge),
        Some(sysfss_send_bridge),
        Some(sysfss_req_show_log_bridge),
        null_mut(),
        null_mut(),
    );
}

unsafe extern "C" fn sysfss_req_show_log_bridge(
    event: CInt,
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    size: SizeT,
    error: CInt,
    packet_err: CInt,
    ssize: CLong,
) {
    match event {
        SYSFSS_REQ_LOG_CALLBACK_ERROR => {
            kprintf(SHOW_CALLBACK_FMT.as_ptr().cast(), ssize);
        }
        SYSFSS_REQ_LOG_SEND_ERROR => {
            kprintf(SHOW_SEND_FMT.as_ptr().cast(), error);
        }
        SYSFSS_REQ_LOG_PACKET_ERROR => {
            kprintf(
                SHOW_PACKET_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                error,
                packet_err,
            );
        }
        SYSFSS_REQ_LOG_DEBUG => {
            kprintf(
                SHOW_DEBUG_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                error,
                packet_err,
                ssize,
            );
        }
        _ => {}
    }
    let _ = size;
}

unsafe fn sysfss_req_store(nodeh: CLong, ops: *mut SysfsOps, instance: *mut c_void, size: SizeT) {
    crate::object_helpers::sysfss_req_store_logged_result(
        nodeh,
        ops.cast::<c_void>(),
        instance,
        SYSFS_DATA_BUF,
        size,
        if ops.is_null() {
            0
        } else {
            sysfs_op_addr((*ops).store)
        },
        Some(sysfss_store_bridge),
        Some(sysfss_send_bridge),
        Some(sysfss_req_store_log_bridge),
        null_mut(),
        null_mut(),
    );
}

unsafe extern "C" fn sysfss_req_store_log_bridge(
    event: CInt,
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    size: SizeT,
    error: CInt,
    packet_err: CInt,
    ssize: CLong,
) {
    match event {
        SYSFSS_REQ_LOG_CALLBACK_ERROR => {
            kprintf(STORE_CALLBACK_FMT.as_ptr().cast(), ssize);
        }
        SYSFSS_REQ_LOG_SEND_ERROR => {
            kprintf(STORE_SEND_FMT.as_ptr().cast(), error);
        }
        SYSFSS_REQ_LOG_PACKET_ERROR => {
            kprintf(
                STORE_PACKET_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                size,
                error,
                packet_err,
            );
        }
        SYSFSS_REQ_LOG_DEBUG => {
            kprintf(
                STORE_DEBUG_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                size,
                error,
                packet_err,
                ssize,
            );
        }
        _ => {}
    }
}

unsafe fn sysfss_req_release(nodeh: CLong, ops: *mut SysfsOps, instance: *mut c_void) {
    crate::object_helpers::sysfss_req_release_logged_result(
        nodeh,
        ops.cast::<c_void>(),
        instance,
        if ops.is_null() {
            0
        } else {
            sysfs_op_addr((*ops).release)
        },
        Some(sysfss_release_bridge),
        Some(sysfss_send_bridge),
        Some(sysfss_req_release_log_bridge),
        null_mut(),
    );
}

unsafe extern "C" fn sysfss_req_release_log_bridge(
    event: CInt,
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    size: SizeT,
    error: CInt,
    packet_err: CInt,
    ssize: CLong,
) {
    match event {
        SYSFSS_REQ_LOG_SEND_ERROR => {
            kprintf(RELEASE_SEND_FMT.as_ptr().cast(), error);
        }
        SYSFSS_REQ_LOG_PACKET_ERROR => {
            kprintf(
                RELEASE_PACKET_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                error,
                packet_err,
            );
        }
        SYSFSS_REQ_LOG_DEBUG => {
            kprintf(
                RELEASE_DEBUG_FMT.as_ptr().cast(),
                nodeh,
                ops,
                instance,
                error,
                packet_err,
            );
        }
        _ => {}
    }
    let _ = (size, ssize);
}

unsafe extern "C" fn sysfss_packet_show_bridge(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
) {
    sysfss_req_show(nodeh, ops.cast::<SysfsOps>(), instance);
}

unsafe extern "C" fn sysfss_packet_store_bridge(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
    size: SizeT,
) {
    sysfss_req_store(nodeh, ops.cast::<SysfsOps>(), instance, size);
}

unsafe extern "C" fn sysfss_packet_release_bridge(
    nodeh: CLong,
    ops: *mut c_void,
    instance: *mut c_void,
) {
    sysfss_req_release(nodeh, ops.cast::<SysfsOps>(), instance);
}

unsafe extern "C" fn sysfss_packet_unknown_bridge(
    msg: CInt,
    error: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
) {
    kprintf(
        UNKNOWN_PACKET_FMT.as_ptr().cast(),
        msg,
        error,
        arg1,
        arg2,
        arg3,
    );
}

#[no_mangle]
pub unsafe extern "C" fn sysfss_packet_handler(
    ch: *mut c_void,
    msg: CInt,
    error: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
) {
    let _ = ch;
    crate::object_helpers::sysfss_packet_handler_logged_result(
        msg,
        error,
        arg1,
        arg2,
        arg3,
        Some(sysfss_packet_show_bridge),
        Some(sysfss_packet_store_bridge),
        Some(sysfss_packet_release_bridge),
        Some(sysfss_packet_unknown_bridge),
        null_mut(),
    );
}

#[no_mangle]
pub unsafe extern "C" fn sysfs_init() {
    let mut stage: CInt = 0;
    let mut phase: CInt = 0;

    let error = crate::object_helpers::sysfs_init_body_result(
        size_of::<SysfsReqCreateParam>(),
        size_of::<SysfsReqMkdirParam>(),
        size_of::<SysfsReqSymlinkParam>(),
        size_of::<SysfsReqLookupParam>(),
        size_of::<SysfsReqUnlinkParam>(),
        size_of::<SysfsReqSetupParam>(),
        &raw mut SYSFS_DATA_BUF,
        &raw mut SYSFS_DATA_BUFSIZE,
        Some(sysfs_init_alloc_bridge),
        Some(sysfs_init_free_bridge),
        Some(sysfs_init_phys_bridge),
        Some(sysfs_request_send_bridge),
        Some(sysfs_request_pause_bridge),
        Some(sysfs_request_barrier_bridge),
        &mut stage as *mut CInt,
        &mut phase as *mut CInt,
    );

    if error != 0 {
        if stage == SYSFS_INIT_STAGE_SIZE {
            kprintf(INIT_SIZE_FMT.as_ptr().cast(), error);
            kernel_panic(INIT_SIZE_PANIC.as_ptr().cast());
        } else if stage == SYSFS_INIT_STAGE_DATA_ALLOC {
            kprintf(INIT_DATA_ALLOC_FMT.as_ptr().cast(), error);
        } else if stage == SYSFS_INIT_STAGE_PARAM_ALLOC {
            kprintf(INIT_PARAM_ALLOC_FMT.as_ptr().cast(), error);
        } else if stage == SYSFS_INIT_STAGE_REQUEST && phase == SYSFS_REQUEST_PHASE_SEND {
            kprintf(INIT_SEND_FMT.as_ptr().cast(), error);
        } else if stage == SYSFS_INIT_STAGE_REQUEST && phase == SYSFS_REQUEST_PHASE_RESPONSE {
            kprintf(INIT_RESP_FMT.as_ptr().cast(), error);
        }
        kprintf(INIT_FINAL_FMT.as_ptr().cast(), error);
        kernel_panic(INIT_PANIC.as_ptr().cast());
    }
}
