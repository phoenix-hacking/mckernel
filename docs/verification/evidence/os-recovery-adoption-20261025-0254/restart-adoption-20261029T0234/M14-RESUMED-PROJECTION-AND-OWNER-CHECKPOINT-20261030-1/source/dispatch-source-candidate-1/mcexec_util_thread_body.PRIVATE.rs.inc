#[no_mangle]
pub unsafe extern "C" fn mcexec_util_thread_body(
    _my_thread: *mut McexecThreadData,
    rp_rctx: c_ulong,
    remote_tid: c_int,
    pattr: c_ulong,
    uti_info: c_ulong,
    uti_desc_arg: c_ulong,
) -> c_long {
    let uti_desc = uti_desc_arg as *mut McexecUtiDesc;
    if uti_desc.is_null() {
        unsafe { mcexec_util_thread_missing_desc_bridge() };
        return -(EINVAL as c_long);
    }
    unsafe { mcexec_util_thread_desc_log_bridge(uti_desc as *mut c_void) };

    unsafe { mcexec_util_thread_barrier_init_bridge() };
    let mut tp: *mut McexecThreadData = core::ptr::null_mut();
    let mut rc = unsafe { mcexec_util_thread_create_worker_bridge(&mut tp) };
    if rc != 0 {
        unsafe { mcexec_util_thread_worker_error_bridge(rc) };
        return -(EINVAL as c_long);
    }
    unsafe { mcexec_util_thread_barrier_wait_bridge() };

    let worker_tid = if tp.is_null() {
        0
    } else {
        unsafe { (*tp).tid }
    };
    unsafe { mcexec_util_thread_worker_tid_log_bridge(worker_tid) };

    unsafe {
        (*uti_desc).fd = MCEXEC_FD;
    }

    rc = unsafe { syscall(888) as c_int };
    if rc != -1 {
        unsafe { mcexec_util_thread_intercept_warning_bridge(rc) };
    }

    let mut get_ctx_desc = McexecUtiGetCtxDesc {
        rp_rctx,
        rctx: unsafe { (*uti_desc).rctx.as_mut_ptr() as *mut c_void },
        lctx: unsafe { (*uti_desc).lctx.as_mut_ptr() as *mut c_void },
        uti_refill_tid: worker_tid,
        key: 0,
    };

    rc = unsafe {
        ioctl(
            MCEXEC_FD,
            MCEXEC_UP_UTI_GET_CTX,
            &mut get_ctx_desc as *mut McexecUtiGetCtxDesc as c_ulong,
        )
    };
    if rc != 0 {
        let errno_value = unsafe { *__errno_location() };
        unsafe { mcexec_util_thread_get_ctx_error_bridge(errno_value) };
        return -(errno_value as c_long);
    }

    unsafe {
        (*uti_desc).mck_tid = remote_tid;
        (*uti_desc).key = get_ctx_desc.key;
        (*uti_desc).pid = getpid();
        (*uti_desc).tid = gettid();
    }

    if core::mem::size_of::<McexecSyscallStruct>() * 11 > unsafe { MCEXEC_PAGE_SIZE as usize } {
        unsafe { mcexec_util_thread_param_large_bridge() };
        return -(ENOMEM as c_long);
    }

    if pattr != 0 {
        let cpu_set = unsafe { getenv(UTI_CPU_SET_ENV.as_ptr()) };
        let cpu_set_len = if cpu_set.is_null() {
            0
        } else {
            unsafe { strlen(cpu_set as *const u8) + 1 }
        };
        let mut attr_desc = McexecUtiAttrDesc {
            phys_attr: pattr,
            uti_cpu_set_str: cpu_set,
            uti_cpu_set_len: cpu_set_len,
        };

        rc = unsafe {
            ioctl(
                MCEXEC_FD,
                MCEXEC_UP_UTI_ATTR,
                &mut attr_desc as *mut McexecUtiAttrDesc as c_ulong,
            )
        };
        if rc != 0 {
            let errno_value = unsafe { *__errno_location() };
            unsafe { mcexec_util_thread_attr_error_bridge(errno_value) };
            return -(errno_value as c_long);
        }
    }

    unsafe {
        // Publish the borrowed guest-info span only after all preactivation
        // size/attribute checks succeed. This is not a host-drain acknowledgement.
        (*uti_desc).uti_info = uti_info;
        (*uti_desc).start_syscall_intercept = 1;
    }

    let mut switch_ctx_desc = McexecUtiSwitchCtxDesc {
        rctx: unsafe { (*uti_desc).rctx.as_mut_ptr() as *mut c_void },
        lctx: unsafe { (*uti_desc).lctx.as_mut_ptr() as *mut c_void },
    };
    rc = unsafe {
        mcexec_util_thread_switch_ctx_bridge(
            &mut switch_ctx_desc,
            (*uti_desc).lctx.as_mut_ptr() as *mut c_void,
            (*uti_desc).rctx.as_mut_ptr() as *mut c_void,
        )
    };
    if rc < 0 {
        unsafe { mcexec_util_thread_switch_failed_bridge(rc) };
        return rc as c_long;
    }

    unsafe { mcexec_util_thread_switch_returned_bridge(rc) };
    -(EINVAL as c_long)
}
