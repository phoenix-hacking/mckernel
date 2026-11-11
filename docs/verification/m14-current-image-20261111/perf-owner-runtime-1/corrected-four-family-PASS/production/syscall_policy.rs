// HOST dependency projection: every function/type item below is copied byte-for-byte
// from the pinned whole-candidate source. Only the final lower bindings and test
// child module declarations are HOST-only. No production ownership body is replaced.
use core::ffi::c_void;
use core::ptr::{self,addr_of,addr_of_mut,null_mut,read_volatile,write_volatile};
use core::mem::{align_of,size_of,offset_of,MaybeUninit};
use crate::abi::*;
type SyscallFindProcessFn = unsafe extern "C" fn(CInt, *mut c_void) -> *mut c_void;
type SyscallProcessUnlockFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
const ENOENT: CInt = 2;

unsafe extern "C" {
 static f03_mckfd_alloc_origin_file_v1:i8; static f03_mckfd_alloc_origin_line_v1:CInt;
 static f03_mckfd_free_origin_file_v1:i8; static f03_mckfd_free_origin_line_v1:CInt;
}
type SyscallCopyFromUserFn = unsafe extern "C" fn(*mut u8, CULong, SizeT) -> CLong;

type SyscallCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;

type SyscallForwardContextFn = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;

type SyscallPolicyAllocFn = unsafe extern "C" fn(SizeT, CULong) -> *mut c_void;

type SyscallMckfdLockFn = unsafe extern "C" fn(*mut c_void) -> CLong;

type SyscallMckfdUnlockFn = unsafe extern "C" fn(*mut c_void, CLong);

type SyscallMckfdLongFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CLong;

type SyscallMckfdIntFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;

type SyscallMckfdFreeFn = unsafe extern "C" fn(*mut c_void);

type SyscallAtomic64ReadFn = unsafe extern "C" fn(*mut c_void) -> CLong;

type SyncChildPerfReadFn = unsafe extern "C" fn(CInt) -> CULong;

type SyncChildAtomic64SetFn = unsafe extern "C" fn(*mut c_void, CLong);

type PerfEventUpdateFn = unsafe extern "C" fn(*mut c_void) -> CULong;

type PerfReadAttrFlagsFn =
    unsafe extern "C" fn(*const c_void, *mut CInt, *mut CInt, *mut CInt) -> CInt;

type PerfReadValueFn = unsafe extern "C" fn(*mut c_void) -> CULong;

type PerfReadDispatchFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CLong;

type PerfEventVoidFn = unsafe extern "C" fn(*mut c_void);

type PerfEventIntFn = unsafe extern "C" fn(*mut c_void) -> CInt;

type PerfCounterExtraSetFn = unsafe extern "C" fn(*mut c_void) -> CInt;

type PerfCounterInitRawFn = unsafe extern "C" fn(CInt, CULong, CInt) -> CInt;

type PerfCounterAttrFlagsFn = unsafe extern "C" fn(*const c_void, *mut CInt, *mut CInt) -> CInt;

type PerfCounterMaskCheckFn = unsafe extern "C" fn(CULong) -> CInt;

type PerfCounterStartFn = unsafe extern "C" fn(CULong) -> CInt;

type PerfCounterStopFn = unsafe extern "C" fn(CULong, CInt) -> CInt;

type PerfCounterAllocFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;

type PerfOpenSyscallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;

type PerfOpenAllocEventFn = unsafe extern "C" fn(*mut *mut c_void, *mut c_void) -> CInt;

type PerfAttrFreqFn = unsafe extern "C" fn(*const c_void) -> CInt;

type PerfDoMmapFn =
    unsafe extern "C" fn(CULong, SizeT, CInt, CInt, CInt, CLong, CInt, *mut c_void) -> CLong;

type PerfEventMapFn = unsafe extern "C" fn(CULong) -> CULong;

type PerfEventValidateFn = unsafe extern "C" fn(CULong) -> CInt;

type PerfExtraRegIdFn = unsafe extern "C" fn(CULong, CULong) -> CInt;

type PerfExtraRegMsrFn = unsafe extern "C" fn(CInt) -> u32;

type PerfExtraRegIdxFn = unsafe extern "C" fn(CInt) -> CInt;

type PerfHwEventInitFn = unsafe extern "C" fn(*mut c_void) -> CInt;

const EINVAL: CInt = 22;

const ENOMEM: CInt = 12;

const EFAULT: CInt = 14;

const EIO: CInt = 5;

const EBADF: CInt = 9;

const ENOSYS: CInt = 38;

const PERF_STOP_EVENT_CAPACITY: usize = 65;

const SYNC_CHILD_EVENT_ACTION_NONE: CInt = 0;

const SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL: CInt = 1;

const SYNC_CHILD_EVENT_ACTION_SET_COUNT: CInt = 2;

const F03_PERF_ALLOC_ORIGIN_LINE_V1: CInt = 21404;

const F03_PERF_FREE_ORIGIN_LINE_V1: CInt = 21410;

unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

unsafe fn wait_list_entry(node: *mut AbiListHead, offset: SizeT) -> *mut u8 {
    (node as *mut u8).wrapping_sub(offset)
}

#[no_mangle]
pub extern "C" fn sync_child_event_needed_result(
    has_event: CInt,
    inherit: CInt,
    pid: CInt,
) -> CInt {
    (has_event != 0 && (inherit != 0 || pid != 0)) as CInt
}

#[no_mangle]
pub extern "C" fn sync_child_event_pid_action_result(pid: CInt) -> CInt {
    if pid == 0 {
        SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL
    } else if pid > 0 {
        SYNC_CHILD_EVENT_ACTION_SET_COUNT
    } else {
        SYNC_CHILD_EVENT_ACTION_NONE
    }
}

unsafe fn sync_child_event_apply_action(
    event: *mut u8,
    action: CInt,
    counter_id_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    read_fn: SyncChildPerfReadFn,
    set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if action == SYNC_CHILD_EVENT_ACTION_CHILD_TOTAL {
        let counter_id = read_volatile(field_ptr::<CInt>(event, counter_id_offset));
        let count = read_fn(counter_id);
        let total_ptr = field_ptr::<CULong>(event, child_count_total_offset);
        let total = read_volatile(total_ptr).wrapping_add(count);
        write_volatile(total_ptr, total);
        return 0;
    }

    if action == SYNC_CHILD_EVENT_ACTION_SET_COUNT {
        let Some(set_count) = set_fn else {
            return -EINVAL as CLong;
        };
        let counter_id = read_volatile(field_ptr::<CInt>(event, counter_id_offset));
        let count = read_fn(counter_id);
        set_count(field_ptr::<c_void>(event, count_offset), count as CLong);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn sync_child_event_body_result(
    event: *mut c_void,
    inherit: CInt,
    pid: CInt,
    group_leader_offset: SizeT,
    event_pid_offset: SizeT,
    counter_id_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    read_fn: Option<SyncChildPerfReadFn>,
    set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if sync_child_event_needed_result(!event.is_null() as CInt, inherit, pid) == 0 {
        return 0;
    }
    let Some(read) = read_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let leader_pid = read_volatile(field_ptr::<CInt>(leader_base, event_pid_offset));
    let leader_action = sync_child_event_pid_action_result(leader_pid);
    if leader_action == SYNC_CHILD_EVENT_ACTION_NONE {
        return 0;
    }

    let rc = sync_child_event_apply_action(
        leader_base,
        leader_action,
        counter_id_offset,
        count_offset,
        child_count_total_offset,
        read,
        set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let sub_action = sync_child_event_pid_action_result(pid);
    if sub_action == SYNC_CHILD_EVENT_ACTION_NONE {
        return 0;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = sync_child_event_apply_action(
            sub,
            sub_action,
            counter_id_offset,
            count_offset,
            child_count_total_offset,
            read,
            set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_value_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    exclude_user: CInt,
    exclude_kernel: CInt,
    inherit: CInt,
    event_pid_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    update_fn: Option<PerfEventUpdateFn>,
    atomic_read_fn: Option<SyscallAtomic64ReadFn>,
) -> CULong {
    if event.is_null() || thread.is_null() {
        return 0;
    }
    let Some(atomic_read) = atomic_read_fn else {
        return 0;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let stopped_user = read_volatile(field_ptr::<CLong>(event_base, stopped_user_tsc_offset));
    let cur_user = if stopped_user != 0 {
        stopped_user as CULong
    } else {
        read_volatile(field_ptr::<CULong>(thread_base, thread_user_tsc_offset))
    };
    let stopped_system = read_volatile(field_ptr::<CLong>(event_base, stopped_system_tsc_offset));
    let cur_system = if stopped_system != 0 {
        stopped_system as CULong
    } else {
        read_volatile(field_ptr::<CULong>(thread_base, thread_system_tsc_offset))
    };

    let mut pmc_count = 0u64;
    let pid = read_volatile(field_ptr::<CInt>(event_base, event_pid_offset));
    if pid == 0 {
        let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
        if use_invariant != 0 {
            if exclude_user == 0 {
                let base = read_volatile(field_ptr::<CLong>(event_base, base_user_tsc_offset));
                let accum = read_volatile(field_ptr::<CLong>(event_base, user_accum_count_offset));
                pmc_count = pmc_count
                    .wrapping_add(cur_user.wrapping_sub(base as CULong))
                    .wrapping_add(accum as CULong);
            }
            if exclude_kernel == 0 {
                let base = read_volatile(field_ptr::<CLong>(event_base, base_system_tsc_offset));
                let accum =
                    read_volatile(field_ptr::<CLong>(event_base, system_accum_count_offset));
                pmc_count = pmc_count
                    .wrapping_add(cur_system.wrapping_sub(base as CULong))
                    .wrapping_add(accum as CULong);
            }
        } else if let Some(update) = update_fn {
            let _ = update(event);
        }
    }

    let mut rtn_count = (atomic_read(field_ptr::<c_void>(event_base, count_offset)) as CULong)
        .wrapping_add(pmc_count);
    if inherit != 0 {
        rtn_count = rtn_count.wrapping_add(read_volatile(field_ptr::<CULong>(
            event_base,
            child_count_total_offset,
        )));
    }

    rtn_count
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_read_value_entry_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    event_attr_offset: SizeT,
    event_pid_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    attr_flags_fn: Option<PerfReadAttrFlagsFn>,
    update_fn: Option<PerfEventUpdateFn>,
    atomic_read_fn: Option<SyscallAtomic64ReadFn>,
) -> CULong {
    if event.is_null() || thread.is_null() {
        return 0;
    }
    let Some(attr_flags) = attr_flags_fn else {
        return 0;
    };

    let event_base = event.cast::<u8>();
    let mut exclude_user = 0;
    let mut exclude_kernel = 0;
    let mut inherit = 0;
    let attr_rc = attr_flags(
        field_ptr::<c_void>(event_base, event_attr_offset).cast_const(),
        core::ptr::addr_of_mut!(exclude_user),
        core::ptr::addr_of_mut!(exclude_kernel),
        core::ptr::addr_of_mut!(inherit),
    );
    if attr_rc != 0 {
        return 0;
    }

    perf_event_read_value_body_result(
        event,
        thread,
        exclude_user,
        exclude_kernel,
        inherit,
        event_pid_offset,
        use_invariant_tsc_offset,
        count_offset,
        child_count_total_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        update_fn,
        atomic_read_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_one_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    read_value_fn: Option<PerfReadValueFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(read_value) = read_value_fn else {
        return -EINVAL as CLong;
    };
    let Some(copy_to) = copy_to_fn else {
        return -EINVAL as CLong;
    };

    let values = [read_value(event)];
    let size = size_of::<CULong>();
    if copy_to(buf_addr, values.as_ptr().cast::<u8>(), size) != 0 {
        return -EFAULT as CLong;
    }

    size as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_read_group_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    group_leader_offset: SizeT,
    nr_siblings_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    read_value_fn: Option<PerfReadValueFn>,
    copy_to_fn: Option<SyscallCopyToUserFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(read_value) = read_value_fn else {
        return -EINVAL as CLong;
    };
    let Some(copy_to) = copy_to_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let leader_count = read_value(leader);
    let nr_siblings = read_volatile(field_ptr::<CInt>(leader_base, nr_siblings_offset));
    let values = [1u64.wrapping_add(nr_siblings as CULong), leader_count];
    let mut ret = 2 * size_of::<CULong>();
    if copy_to(buf_addr, values.as_ptr().cast::<u8>(), ret) != 0 {
        return -EFAULT as CLong;
    }

    let value_size = size_of::<CULong>();
    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset).cast::<c_void>();
        let value = [read_value(sub)];
        if copy_to(
            buf_addr.wrapping_add(ret as CULong),
            value.as_ptr().cast::<u8>(),
            value_size,
        ) != 0
        {
            return -EFAULT as CLong;
        }
        ret = ret.wrapping_add(value_size);
        node = next;
    }

    ret as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_read_body_result(
    event: *mut c_void,
    buf_addr: CULong,
    read_format: CULong,
    group_flag: CULong,
    read_group_fn: Option<PerfReadDispatchFn>,
    read_one_fn: Option<PerfReadDispatchFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    if (read_format & group_flag) != 0 {
        let Some(read_group) = read_group_fn else {
            return -EINVAL as CLong;
        };
        return read_group(event, read_format, buf_addr);
    }

    let Some(read_one) = read_one_fn else {
        return -EINVAL as CLong;
    };
    read_one(event, read_format, buf_addr)
}

#[no_mangle]
pub unsafe extern "C" fn perf_counter_set_body_result(
    event: *mut c_void,
    exclude_kernel: CInt,
    exclude_user: CInt,
    counter_id: CInt,
    hw_config: CULong,
    extra_reg_reg_offset: SizeT,
    kernel_mode: CInt,
    user_mode: CInt,
    set_extra_fn: Option<PerfCounterExtraSetFn>,
    init_raw_fn: Option<PerfCounterInitRawFn>,
) -> CInt {
    if event.is_null() {
        return -EINVAL;
    }
    let Some(init_raw) = init_raw_fn else {
        return -EINVAL;
    };

    let mut mode = 0;
    if exclude_kernel == 0 {
        mode |= kernel_mode;
    }
    if exclude_user == 0 {
        mode |= user_mode;
    }

    let event_base = event.cast::<u8>();
    let extra_reg = read_volatile(field_ptr::<u32>(event_base, extra_reg_reg_offset));
    if extra_reg != 0 {
        let Some(set_extra) = set_extra_fn else {
            return -EINVAL;
        };
        if set_extra(event) != 0 {
            return -1;
        }
    }

    init_raw(counter_id, hw_config, mode)
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_counter_set_entry_body_result(
    event: *mut c_void,
    event_attr_offset: SizeT,
    event_counter_id_offset: SizeT,
    event_hw_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    kernel_mode: CInt,
    user_mode: CInt,
    attr_flags_fn: Option<PerfCounterAttrFlagsFn>,
    set_extra_fn: Option<PerfCounterExtraSetFn>,
    init_raw_fn: Option<PerfCounterInitRawFn>,
) -> CInt {
    if event.is_null() {
        return -EINVAL;
    }
    let Some(attr_flags) = attr_flags_fn else {
        return -EINVAL;
    };

    let event_base = event.cast::<u8>();
    let mut exclude_kernel = 0;
    let mut exclude_user = 0;
    let attr_rc = attr_flags(
        field_ptr::<c_void>(event_base, event_attr_offset).cast_const(),
        core::ptr::addr_of_mut!(exclude_kernel),
        core::ptr::addr_of_mut!(exclude_user),
    );
    if attr_rc != 0 {
        return attr_rc;
    }

    let counter_id = read_volatile(field_ptr::<CInt>(event_base, event_counter_id_offset));
    let hw_config = read_volatile(field_ptr::<CULong>(event_base, event_hw_config_offset));
    perf_counter_set_body_result(
        event,
        exclude_kernel,
        exclude_user,
        counter_id,
        hw_config,
        extra_reg_reg_offset,
        kernel_mode,
        user_mode,
        set_extra_fn,
        init_raw_fn,
    )
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_start_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_mask: &mut CULong,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    inactive_state: CInt,
    active_state: CInt,
    mask_check: PerfCounterMaskCheckFn,
    set_period_fn: Option<PerfEventIntFn>,
    counter_set_fn: Option<PerfEventIntFn>,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    let state = read_volatile(field_ptr::<CInt>(event_base, state_offset));
    if bit == 0 || mask_check(bit) == 0 || state != inactive_state {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user_ptr = field_ptr::<CLong>(event_base, stopped_user_tsc_offset);
        let base_user_ptr = field_ptr::<CLong>(event_base, base_user_tsc_offset);
        let user_accum_ptr = field_ptr::<CLong>(event_base, user_accum_count_offset);
        let stopped_user = read_volatile(stopped_user_ptr);
        if stopped_user != 0 {
            let base_user = read_volatile(base_user_ptr);
            let accum = read_volatile(user_accum_ptr);
            write_volatile(
                user_accum_ptr,
                accum.wrapping_add(stopped_user.wrapping_sub(base_user)),
            );
            write_volatile(stopped_user_ptr, 0);
        }
        write_volatile(
            base_user_ptr,
            read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset)),
        );

        let stopped_system_ptr = field_ptr::<CLong>(event_base, stopped_system_tsc_offset);
        let base_system_ptr = field_ptr::<CLong>(event_base, base_system_tsc_offset);
        let system_accum_ptr = field_ptr::<CLong>(event_base, system_accum_count_offset);
        let stopped_system = read_volatile(stopped_system_ptr);
        if stopped_system != 0 {
            let base_system = read_volatile(base_system_ptr);
            let accum = read_volatile(system_accum_ptr);
            write_volatile(
                system_accum_ptr,
                accum.wrapping_add(stopped_system.wrapping_sub(base_system)),
            );
            write_volatile(stopped_system_ptr, 0);
        }
        write_volatile(
            base_system_ptr,
            read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset)),
        );
    } else {
        let Some(set_period) = set_period_fn else {
            return -EINVAL as CLong;
        };
        let Some(counter_set) = counter_set_fn else {
            return -EINVAL as CLong;
        };
        set_period(event_base.cast::<c_void>());
        counter_set(event_base.cast::<c_void>());
        *counter_mask |= bit;
    }

    write_volatile(field_ptr::<CInt>(event_base, state_offset), active_state);
    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_start_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    thread_proc_offset: SizeT,
    proc_perf_status_offset: SizeT,
    inactive_state: CInt,
    active_state: CInt,
    pp_count: CInt,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    set_period_fn: Option<PerfEventIntFn>,
    counter_set_fn: Option<PerfEventIntFn>,
    counter_start_fn: Option<PerfCounterStartFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let mut counter_mask = 0;
    let rc = perf_start_apply_event_result(
        leader_base,
        thread_base,
        &mut counter_mask,
        counter_id_offset,
        state_offset,
        use_invariant_tsc_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        inactive_state,
        active_state,
        mask_check,
        set_period_fn,
        counter_set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_start_apply_event_result(
            sub,
            thread_base,
            &mut counter_mask,
            counter_id_offset,
            state_offset,
            use_invariant_tsc_offset,
            base_user_tsc_offset,
            stopped_user_tsc_offset,
            user_accum_count_offset,
            base_system_tsc_offset,
            stopped_system_tsc_offset,
            system_accum_count_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            inactive_state,
            active_state,
            mask_check,
            set_period_fn,
            counter_set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    if counter_mask != 0 {
        let Some(counter_start) = counter_start_fn else {
            return -EINVAL as CLong;
        };
        counter_start(counter_mask);
    }

    let proc = read_volatile(field_ptr::<*mut c_void>(thread_base, thread_proc_offset));
    if proc.is_null() {
        return -EINVAL as CLong;
    }
    write_volatile(
        field_ptr::<CInt>(proc.cast::<u8>(), proc_perf_status_offset),
        pp_count,
    );

    0
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_reset_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_id_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    mask_check: PerfCounterMaskCheckFn,
    read_value_fn: Option<PerfReadValueFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    if bit == 0 || mask_check(bit) == 0 {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user = read_volatile(field_ptr::<CLong>(event_base, stopped_user_tsc_offset));
        let user_base = if stopped_user != 0 {
            stopped_user
        } else {
            read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset))
        };
        write_volatile(
            field_ptr::<CLong>(event_base, base_user_tsc_offset),
            user_base,
        );
        write_volatile(field_ptr::<CLong>(event_base, user_accum_count_offset), 0);

        let stopped_system =
            read_volatile(field_ptr::<CLong>(event_base, stopped_system_tsc_offset));
        let system_base = if stopped_system != 0 {
            stopped_system
        } else {
            read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset))
        };
        write_volatile(
            field_ptr::<CLong>(event_base, base_system_tsc_offset),
            system_base,
        );
        write_volatile(field_ptr::<CLong>(event_base, system_accum_count_offset), 0);
    } else {
        let Some(read_value) = read_value_fn else {
            return -EINVAL as CLong;
        };
        let Some(atomic_set) = atomic_set_fn else {
            return -EINVAL as CLong;
        };
        read_value(event_base.cast::<c_void>());
        atomic_set(field_ptr::<c_void>(event_base, count_offset), 0);
    }

    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_reset_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    base_user_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    user_accum_count_offset: SizeT,
    base_system_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    system_accum_count_offset: SizeT,
    count_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    read_value_fn: Option<PerfReadValueFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let rc = perf_reset_apply_event_result(
        leader_base,
        thread_base,
        counter_id_offset,
        use_invariant_tsc_offset,
        base_user_tsc_offset,
        stopped_user_tsc_offset,
        user_accum_count_offset,
        base_system_tsc_offset,
        stopped_system_tsc_offset,
        system_accum_count_offset,
        count_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        mask_check,
        read_value_fn,
        atomic_set_fn,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_reset_apply_event_result(
            sub,
            thread_base,
            counter_id_offset,
            use_invariant_tsc_offset,
            base_user_tsc_offset,
            stopped_user_tsc_offset,
            user_accum_count_offset,
            base_system_tsc_offset,
            stopped_system_tsc_offset,
            system_accum_count_offset,
            count_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            mask_check,
            read_value_fn,
            atomic_set_fn,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    0
}

#[allow(clippy::too_many_arguments)]
unsafe fn perf_stop_apply_event_result(
    event_base: *mut u8,
    thread_base: *mut u8,
    counter_mask: &mut CULong,
    stop_events: &mut [*mut c_void; PERF_STOP_EVENT_CAPACITY],
    stop_event_idx: &mut usize,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    active_state: CInt,
    inactive_state: CInt,
    mask_check: PerfCounterMaskCheckFn,
) -> CLong {
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let bit = perf_event_bit_result(counter_id);
    let state = read_volatile(field_ptr::<CInt>(event_base, state_offset));
    if bit == 0 || mask_check(bit) == 0 || state != active_state {
        return 0;
    }

    let use_invariant = read_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset));
    if use_invariant != 0 {
        let stopped_user_ptr = field_ptr::<CLong>(event_base, stopped_user_tsc_offset);
        if read_volatile(stopped_user_ptr) == 0 {
            write_volatile(
                stopped_user_ptr,
                read_volatile(field_ptr::<CLong>(thread_base, thread_user_tsc_offset)),
            );
        }

        let stopped_system_ptr = field_ptr::<CLong>(event_base, stopped_system_tsc_offset);
        if read_volatile(stopped_system_ptr) == 0 {
            write_volatile(
                stopped_system_ptr,
                read_volatile(field_ptr::<CLong>(thread_base, thread_system_tsc_offset)),
            );
        }
    } else {
        if *stop_event_idx >= PERF_STOP_EVENT_CAPACITY {
            return -EINVAL as CLong;
        }
        *counter_mask |= bit;
        stop_events[*stop_event_idx] = event_base.cast::<c_void>();
        *stop_event_idx += 1;
    }

    write_volatile(field_ptr::<CInt>(event_base, state_offset), inactive_state);
    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_stop_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    group_leader_offset: SizeT,
    sibling_list_offset: SizeT,
    group_entry_offset: SizeT,
    counter_id_offset: SizeT,
    state_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    stopped_user_tsc_offset: SizeT,
    stopped_system_tsc_offset: SizeT,
    thread_user_tsc_offset: SizeT,
    thread_system_tsc_offset: SizeT,
    thread_proc_offset: SizeT,
    proc_monitoring_event_offset: SizeT,
    proc_perf_status_offset: SizeT,
    active_state: CInt,
    inactive_state: CInt,
    pp_none: CInt,
    stop_flags: CInt,
    mask_check_fn: Option<PerfCounterMaskCheckFn>,
    counter_stop_fn: Option<PerfCounterStopFn>,
    update_fn: Option<PerfEventUpdateFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(mask_check) = mask_check_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let leader = read_volatile(field_ptr::<*mut c_void>(event_base, group_leader_offset));
    if leader.is_null() {
        return -EINVAL as CLong;
    }

    let leader_base = leader.cast::<u8>();
    let mut counter_mask = 0;
    let mut stop_events = [core::ptr::null_mut::<c_void>(); PERF_STOP_EVENT_CAPACITY];
    let mut stop_event_idx = 0usize;
    let rc = perf_stop_apply_event_result(
        leader_base,
        thread_base,
        &mut counter_mask,
        &mut stop_events,
        &mut stop_event_idx,
        counter_id_offset,
        state_offset,
        use_invariant_tsc_offset,
        stopped_user_tsc_offset,
        stopped_system_tsc_offset,
        thread_user_tsc_offset,
        thread_system_tsc_offset,
        active_state,
        inactive_state,
        mask_check,
    );
    if rc != 0 {
        return rc;
    }

    let head = field_ptr::<AbiListHead>(leader_base, sibling_list_offset);
    let mut node = (*head).next;
    while !node.is_null() && node != head {
        let next = (*node).next;
        let sub = wait_list_entry(node, group_entry_offset);
        let rc = perf_stop_apply_event_result(
            sub,
            thread_base,
            &mut counter_mask,
            &mut stop_events,
            &mut stop_event_idx,
            counter_id_offset,
            state_offset,
            use_invariant_tsc_offset,
            stopped_user_tsc_offset,
            stopped_system_tsc_offset,
            thread_user_tsc_offset,
            thread_system_tsc_offset,
            active_state,
            inactive_state,
            mask_check,
        );
        if rc != 0 {
            return rc;
        }
        node = next;
    }

    if counter_mask != 0 {
        let Some(counter_stop) = counter_stop_fn else {
            return -EINVAL as CLong;
        };
        let Some(update) = update_fn else {
            return -EINVAL as CLong;
        };
        counter_stop(counter_mask, stop_flags);
        for stop_event in stop_events.iter().take(stop_event_idx) {
            if !stop_event.is_null() {
                update(*stop_event);
            }
        }
    }

    let proc = read_volatile(field_ptr::<*mut c_void>(thread_base, thread_proc_offset));
    if proc.is_null() {
        return -EINVAL as CLong;
    }
    let proc_base = proc.cast::<u8>();
    write_volatile(
        field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset),
        core::ptr::null_mut(),
    );
    write_volatile(
        field_ptr::<CInt>(proc_base, proc_perf_status_offset),
        pp_none,
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_ioctl_body_result(
    event: *mut c_void,
    current_proc: *mut c_void,
    lock_arg: *mut c_void,
    cmd: CULong,
    inherit: CInt,
    enable_cmd: CULong,
    disable_cmd: CULong,
    reset_cmd: CULong,
    refresh_cmd: CULong,
    pp_reset: CInt,
    event_pid_offset: SizeT,
    proc_monitoring_event_offset: SizeT,
    proc_perf_status_offset: SizeT,
    start_fn: Option<PerfEventVoidFn>,
    stop_fn: Option<PerfEventVoidFn>,
    reset_fn: Option<PerfEventVoidFn>,
    find_fn: Option<SyscallFindProcessFn>,
    unlock_fn: Option<SyscallProcessUnlockFn>,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    let event_base = event.cast::<u8>();
    let pid = read_volatile(field_ptr::<CInt>(event_base, event_pid_offset));

    if cmd == enable_cmd {
        if pid == 0 {
            if current_proc.is_null() {
                return -EINVAL as CLong;
            }
            let Some(start) = start_fn else {
                return -EINVAL as CLong;
            };
            let proc_base = current_proc.cast::<u8>();
            write_volatile(
                field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset),
                event,
            );
            start(event);
        } else if pid > 0 {
            let Some(find) = find_fn else {
                return -EINVAL as CLong;
            };
            let Some(unlock) = unlock_fn else {
                return -EINVAL as CLong;
            };
            let proc = find(pid, lock_arg);
            if proc.is_null() {
                return -EINVAL as CLong;
            }
            let proc_base = proc.cast::<u8>();
            let monitoring = field_ptr::<*mut c_void>(proc_base, proc_monitoring_event_offset);
            if read_volatile(monitoring).is_null() {
                write_volatile(monitoring, event);
                write_volatile(
                    field_ptr::<CInt>(proc_base, proc_perf_status_offset),
                    pp_reset,
                );
            }
            unlock(proc, lock_arg);
        }
        return 0;
    }

    if cmd == disable_cmd {
        if pid == 0 {
            let Some(stop) = stop_fn else {
                return -EINVAL as CLong;
            };
            stop(event);
        }
        return 0;
    }

    if cmd == reset_cmd {
        let Some(reset) = reset_fn else {
            return -EINVAL as CLong;
        };
        reset(event);
        return 0;
    }

    if cmd == refresh_cmd {
        if inherit != 0 {
            return -EINVAL as CLong;
        }
        return 0;
    }

    -1
}

fn perf_event_bit_result(index: CInt) -> CULong {
    if index < 0 || index >= (size_of::<CULong>() * 8) as CInt {
        0
    } else {
        1u64 << (index as u32)
    }
}

#[no_mangle]
pub unsafe extern "C" fn perf_close_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    counter_id_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    thread_extra_reg_alloc_map_offset: SizeT,
    free_fn: Option<SyscallMckfdFreeFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(free) = free_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let thread_base = thread.cast::<u8>();
    let counter_id = read_volatile(field_ptr::<CInt>(event_base, counter_id_offset));
    let pmc_map = field_ptr::<CULong>(thread_base, thread_pmc_alloc_map_offset);
    let pmc_mask = !perf_event_bit_result(counter_id);
    write_volatile(pmc_map, read_volatile(pmc_map) & pmc_mask);

    if read_volatile(field_ptr::<CInt>(event_base, extra_reg_reg_offset)) != 0 {
        let idx = read_volatile(field_ptr::<CInt>(event_base, extra_reg_idx_offset));
        let extra_map = field_ptr::<CULong>(thread_base, thread_extra_reg_alloc_map_offset);
        let extra_mask = !perf_event_bit_result(idx);
        write_volatile(extra_map, read_volatile(extra_map) & extra_mask);
    }

    free(event);
    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_fcntl_body_result(
    sfd: *mut c_void,
    ctx: *mut c_void,
    cmd: CInt,
    arg: CLong,
    fcntl_nr: CInt,
    set_sig_cmd: CInt,
    _setown_ex_cmd: CInt,
    mckfd_sig_no_offset: SizeT,
    forward_fn: Option<SyscallForwardContextFn>,
) -> CLong {
    if sfd.is_null() {
        return -EINVAL as CLong;
    }
    let Some(forward) = forward_fn else {
        return -EINVAL as CLong;
    };

    if cmd == set_sig_cmd {
        write_volatile(
            field_ptr::<CInt>(sfd.cast::<u8>(), mckfd_sig_no_offset),
            arg as CInt,
        );
    }

    forward(fcntl_nr, ctx)
}

#[no_mangle]
pub unsafe extern "C" fn perf_mmap_body_result(
    addr0: CULong,
    len0: SizeT,
    prot: CInt,
    flags: CInt,
    fd: CInt,
    off0: CLong,
    map_anonymous: CInt,
    prot_write: CInt,
    data_head_offset: SizeT,
    capabilities_offset: SizeT,
    cap_user_rdpmc_mask: CULong,
    do_mmap_fn: Option<PerfDoMmapFn>,
) -> CLong {
    let Some(do_mmap) = do_mmap_fn else {
        return -EINVAL as CLong;
    };

    let rc = do_mmap(
        addr0,
        len0,
        prot | prot_write,
        flags | map_anonymous,
        fd,
        off0,
        0,
        core::ptr::null_mut(),
    );

    // Defined-error successor: the actual mapping error is not a page pointer.
    // Preserve its exact errno and perform no metadata access on this branch.
    if rc < 0 {
        return rc;
    }

    // SAFETY: The caller/provider must supply the original positive, writable,
    // aligned mapping spanning both real metadata fields. No ownership is added.
    let page = rc as CULong as *mut u8;
    write_volatile(field_ptr::<CULong>(page, data_head_offset), 16);
    let capabilities = field_ptr::<CULong>(page, capabilities_offset);
    write_volatile(
        capabilities,
        read_volatile(capabilities) | cap_user_rdpmc_mask,
    );

    rc
}

#[no_mangle]
pub extern "C" fn perf_event_open_validate_body_result(
    cpu: CInt,
    flags: CULong,
    attr_type: CULong,
    read_format: CULong,
    freq: CInt,
    sample_period: CULong,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
) -> CInt {
    let mut unsupported = cpu > 0 || flags > 0;

    if attr_type != raw_type && attr_type != hardware_type && attr_type != hw_cache_type {
        unsupported = true;
    }
    if (read_format & unsupported_read_format_mask) != 0 {
        unsupported = true;
    }

    if freq != 0 {
        unsupported = true;
    } else if (sample_period & sample_period_sign_bit) != 0 {
        return -EINVAL;
    }

    if unsupported {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_init_body_result(
    event: *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    ref_cpu_cycles_config: CULong,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
) -> CLong {
    if event.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(atomic_set) = atomic_set_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    let attr_base = attr.cast::<u8>();
    let mut i = 0;
    while i < event_size {
        write_volatile(event_base.add(i), 0);
        i += 1;
    }

    i = 0;
    let attr_dst = event_base.add(event_attr_offset);
    while i < attr_size {
        write_volatile(attr_dst.add(i), read_volatile(attr_base.add(i)));
        i += 1;
    }

    let group_entry = field_ptr::<AbiListHead>(event_base, group_entry_offset);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).next), group_entry);
    write_volatile(core::ptr::addr_of_mut!((*group_entry).prev), group_entry);
    let sibling_list = field_ptr::<AbiListHead>(event_base, sibling_list_offset);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).next), sibling_list);
    write_volatile(core::ptr::addr_of_mut!((*sibling_list).prev), sibling_list);

    write_volatile(
        field_ptr::<CULong>(event_base, sample_freq_offset),
        attr_sample_freq,
    );
    write_volatile(field_ptr::<CInt>(event_base, nr_siblings_offset), 0);
    atomic_set(event_base.add(count_offset).cast::<c_void>(), 0);
    write_volatile(field_ptr::<CULong>(event_base, child_count_total_offset), 0);
    write_volatile(
        field_ptr::<*mut c_void>(event_base, parent_offset),
        core::ptr::null_mut(),
    );

    let sample_period = if attr_freq != 0 && attr_sample_freq != 0 {
        1
    } else {
        attr_sample_period
    };
    write_volatile(
        field_ptr::<CULong>(event_base, hw_sample_period_offset),
        sample_period,
    );
    write_volatile(
        field_ptr::<CULong>(event_base, hw_last_period_offset),
        sample_period,
    );
    atomic_set(
        event_base.add(hw_period_left_offset).cast::<c_void>(),
        sample_period as CLong,
    );

    if attr_type == hardware_type && attr_config == ref_cpu_cycles_config {
        write_volatile(field_ptr::<CInt>(event_base, use_invariant_tsc_offset), 1);
        return 1;
    }

    0
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_map_body_result(
    event_out: *mut *mut c_void,
    event: *mut c_void,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || event.is_null() {
        return -EINVAL as CLong;
    }
    let Some(validate_event) = validate_event_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_id) = extra_reg_id_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_msr) = extra_reg_msr_fn else {
        return -EINVAL as CLong;
    };
    let Some(extra_reg_idx) = extra_reg_idx_fn else {
        return -EINVAL as CLong;
    };
    let Some(hw_event_init) = hw_event_init_fn else {
        return -EINVAL as CLong;
    };
    let mut extra_config = 0;
    let val = if attr_type == hardware_type {
        let Some(hw_event_map) = hw_event_map_fn else {
            return -EINVAL as CLong;
        };
        hw_event_map(attr_config)
    } else if attr_type == hw_cache_type {
        let Some(hw_cache_event_map) = hw_cache_event_map_fn else {
            return -EINVAL as CLong;
        };
        let Some(hw_cache_extra_reg_map) = hw_cache_extra_reg_map_fn else {
            return -EINVAL as CLong;
        };
        let mapped = hw_cache_event_map(attr_config);
        extra_config = hw_cache_extra_reg_map(attr_config);
        mapped
    } else if attr_type == raw_type {
        let Some(raw_event_map) = raw_event_map_fn else {
            return -EINVAL as CLong;
        };
        raw_event_map(attr_config)
    } else {
        return -EINVAL as CLong;
    };

    if validate_event(val) == 0 {
        return -ENOENT as CLong;
    }

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CULong>(event_base, hw_config_offset), val);
    write_volatile(
        field_ptr::<CULong>(event_base, hw_config_ext_offset),
        extra_config,
    );

    let ereg_id = extra_reg_id(val, extra_config);
    if ereg_id >= 0 {
        write_volatile(
            field_ptr::<CULong>(event_base, extra_reg_config_offset),
            extra_config,
        );
        write_volatile(
            field_ptr::<u32>(event_base, extra_reg_reg_offset),
            extra_reg_msr(ereg_id),
        );
        write_volatile(
            field_ptr::<CInt>(event_base, extra_reg_idx_offset),
            extra_reg_idx(ereg_id),
        );
    }

    let ret = hw_event_init(event);
    if ret == 0 {
        write_volatile(event_out, event);
    }
    ret as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_alloc_body_result(
    event_out: *mut *mut c_void,
    attr: *const c_void,
    event_size: SizeT,
    attr_size: SizeT,
    alloc_flags: CULong,
    event_attr_offset: SizeT,
    group_entry_offset: SizeT,
    sibling_list_offset: SizeT,
    sample_freq_offset: SizeT,
    nr_siblings_offset: SizeT,
    count_offset: SizeT,
    child_count_total_offset: SizeT,
    parent_offset: SizeT,
    hw_sample_period_offset: SizeT,
    hw_last_period_offset: SizeT,
    hw_period_left_offset: SizeT,
    use_invariant_tsc_offset: SizeT,
    hw_config_offset: SizeT,
    hw_config_ext_offset: SizeT,
    extra_reg_config_offset: SizeT,
    extra_reg_reg_offset: SizeT,
    extra_reg_idx_offset: SizeT,
    attr_type: CULong,
    attr_config: CULong,
    attr_freq: CInt,
    attr_sample_freq: CULong,
    attr_sample_period: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    raw_type: CULong,
    ref_cpu_cycles_config: CULong,
    alloc_fn: Option<SyscallPolicyAllocFn>,
    free_fn: Option<SyscallMckfdFreeFn>,
    atomic_set_fn: Option<SyncChildAtomic64SetFn>,
    hw_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_event_map_fn: Option<PerfEventMapFn>,
    hw_cache_extra_reg_map_fn: Option<PerfEventMapFn>,
    raw_event_map_fn: Option<PerfEventMapFn>,
    validate_event_fn: Option<PerfEventValidateFn>,
    extra_reg_id_fn: Option<PerfExtraRegIdFn>,
    extra_reg_msr_fn: Option<PerfExtraRegMsrFn>,
    extra_reg_idx_fn: Option<PerfExtraRegIdxFn>,
    hw_event_init_fn: Option<PerfHwEventInitFn>,
) -> CLong {
    if event_out.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(alloc) = alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(free) = free_fn else {
        return -EINVAL as CLong;
    };

    let event = alloc(event_size, alloc_flags);
    if event.is_null() {
        return -ENOMEM as CLong;
    }

    let init = perf_event_alloc_init_body_result(
        event,
        attr,
        event_size,
        attr_size,
        event_attr_offset,
        group_entry_offset,
        sibling_list_offset,
        sample_freq_offset,
        nr_siblings_offset,
        count_offset,
        child_count_total_offset,
        parent_offset,
        hw_sample_period_offset,
        hw_last_period_offset,
        hw_period_left_offset,
        use_invariant_tsc_offset,
        attr_type,
        attr_config,
        attr_freq,
        attr_sample_freq,
        attr_sample_period,
        hardware_type,
        ref_cpu_cycles_config,
        atomic_set_fn,
    );
    if init < 0 {
        free(event);
        return init;
    }
    if init > 0 {
        write_volatile(event_out, event);
        return 0;
    }

    let ret = perf_event_alloc_map_body_result(
        event_out,
        event,
        hw_config_offset,
        hw_config_ext_offset,
        extra_reg_config_offset,
        extra_reg_reg_offset,
        extra_reg_idx_offset,
        attr_type,
        attr_config,
        hardware_type,
        hw_cache_type,
        raw_type,
        hw_event_map_fn,
        hw_cache_event_map_fn,
        hw_cache_extra_reg_map_fn,
        raw_event_map_fn,
        validate_event_fn,
        extra_reg_id_fn,
        extra_reg_msr_fn,
        extra_reg_idx_fn,
        hw_event_init_fn,
    );
    if ret != 0 {
        free(event);
    }
    ret
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_group_body_result(
    event: *mut c_void,
    proc: *mut c_void,
    group_fd: CInt,
    counter_idx: CInt,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
) -> CLong {
    if event.is_null() {
        return -EINVAL as CLong;
    }

    let event_base = event.cast::<u8>();
    let leader = if group_fd == -1 {
        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            event,
        );
        write_volatile(field_ptr::<CULong>(event_base, event_pmc_status_offset), 0);
        event
    } else {
        if proc.is_null() {
            return -EINVAL as CLong;
        }

        let mut cur = read_volatile(field_ptr::<*mut c_void>(
            proc.cast::<u8>(),
            proc_mckfd_offset,
        ));
        let mut found = core::ptr::null_mut::<c_void>();
        while !cur.is_null() {
            let cur_base = cur.cast::<u8>();
            if read_volatile(field_ptr::<CInt>(cur_base, mckfd_fd_offset)) == group_fd {
                let data = read_volatile(field_ptr::<CLong>(cur_base, mckfd_data_offset));
                found = data as usize as *mut c_void;
                break;
            }
            cur = read_volatile(field_ptr::<*mut c_void>(cur_base, mckfd_next_offset));
        }
        if found.is_null() {
            return -EINVAL as CLong;
        }

        write_volatile(
            field_ptr::<*mut c_void>(event_base, event_group_leader_offset),
            found,
        );

        let leader_base = found.cast::<u8>();
        let entry = field_ptr::<AbiListHead>(event_base, event_group_entry_offset);
        let head = field_ptr::<AbiListHead>(leader_base, event_sibling_list_offset);
        let prev = read_volatile(core::ptr::addr_of!((*head).prev));
        if prev.is_null() {
            return -EINVAL as CLong;
        }
        write_volatile(core::ptr::addr_of_mut!((*entry).next), head);
        write_volatile(core::ptr::addr_of_mut!((*entry).prev), prev);
        write_volatile(core::ptr::addr_of_mut!((*prev).next), entry);
        write_volatile(core::ptr::addr_of_mut!((*head).prev), entry);

        let nr_siblings = field_ptr::<CInt>(leader_base, event_nr_siblings_offset);
        write_volatile(nr_siblings, read_volatile(nr_siblings).wrapping_add(1));
        found
    };

    let leader_base = leader.cast::<u8>();
    let pmc_status = field_ptr::<CULong>(leader_base, event_pmc_status_offset);
    write_volatile(
        pmc_status,
        read_volatile(pmc_status) | perf_event_bit_result(counter_idx),
    );

    0
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_counter_body_result(
    event: *mut c_void,
    thread: *mut c_void,
    pid: CInt,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
) -> CLong {
    if event.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(counter_alloc) = counter_alloc_fn else {
        return -EINVAL as CLong;
    };

    let event_base = event.cast::<u8>();
    write_volatile(field_ptr::<CInt>(event_base, event_pid_offset), pid);
    let counter_idx = counter_alloc(thread, event);
    if counter_idx < 0 {
        return counter_idx as CLong;
    }
    write_volatile(
        field_ptr::<CInt>(event_base, event_counter_id_offset),
        counter_idx,
    );

    counter_idx as CLong
}

#[no_mangle]
pub unsafe extern "C" fn perf_event_open_linux_fd_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    counter_idx: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    thread_pmc_alloc_map_offset: SizeT,
    syscall_fn: Option<PerfOpenSyscallFn>,
) -> CLong {
    if request.is_null() || thread.is_null() {
        return -EINVAL as CLong;
    }
    let Some(syscall) = syscall_fn else {
        return -EINVAL as CLong;
    };

    write_volatile(
        core::ptr::addr_of_mut!((*request).number),
        perf_event_open_nr as CULong,
    );
    write_volatile(core::ptr::addr_of_mut!((*request).args[0]), 0);
    // SAFETY: The caller owns this fresh, unpublished request. The selected
    // Linux consumer ignores these five arguments; IDs and valid remain owned
    // by the unchanged offload preparation/publication chain.
    unsafe {
        write_volatile(core::ptr::addr_of_mut!((*request).args[1]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[2]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[3]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[4]), 0);
        write_volatile(core::ptr::addr_of_mut!((*request).args[5]), 0);
    }
    let fd = syscall(request, cpu);
    if fd < 0 {
        return fd;
    }

    let thread_base = thread.cast::<u8>();
    let pmc_map = field_ptr::<CULong>(thread_base, thread_pmc_alloc_map_offset);
    write_volatile(
        pmc_map,
        read_volatile(pmc_map) | perf_event_bit_result(counter_idx),
    );

    fd
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_mckfd_publish_body_result(
    sfd: *mut c_void,
    event: *mut c_void,
    proc: *mut c_void,
    fd: CInt,
    proc_mckfd_lock_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_data_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if sfd.is_null() || event.is_null() || proc.is_null() {
        return -EINVAL as CLong;
    }
    if read_fn.is_none()
        || ioctl_fn.is_none()
        || mmap_fn.is_none()
        || close_fn.is_none()
        || fcntl_fn.is_none()
    {
        return -EINVAL as CLong;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL as CLong;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL as CLong;
    };

    let sfd_base = sfd.cast::<u8>();
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_fd_offset), fd);
    write_volatile(field_ptr::<CInt>(sfd_base, mckfd_sig_no_offset), -1);
    write_volatile(
        field_ptr::<CLong>(sfd_base, mckfd_data_offset),
        event as isize as CLong,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_read_cb_offset),
        read_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_ioctl_cb_offset),
        ioctl_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdLongFn>>(sfd_base, mckfd_mmap_cb_offset),
        mmap_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_close_cb_offset),
        close_fn,
    );
    write_volatile(
        field_ptr::<Option<SyscallMckfdIntFn>>(sfd_base, mckfd_fcntl_cb_offset),
        fcntl_fn,
    );

    let proc_base = proc.cast::<u8>();
    let lock_ptr = field_ptr::<c_void>(proc_base, proc_mckfd_lock_offset);
    let irqstate = lock(lock_ptr);
    let headp = field_ptr::<*mut c_void>(proc_base, proc_mckfd_offset);
    let old_head = read_volatile(headp);
    write_volatile(
        field_ptr::<*mut c_void>(sfd_base, mckfd_next_offset),
        old_head,
    );
    write_volatile(headp, sfd);
    unlock(lock_ptr, irqstate);

    fd as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    pid: CInt,
    group_fd: CInt,
    perf_event_open_nr: CInt,
    cpu: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    #[cfg(f03_perf_owner_protocol)]
    {
        // Actual selected inputs/types are forwarded unchanged. The new module
        // owns publication, genuine routing and every transaction rollback.
        return unsafe { crate::f03_perf_owner::open_from_body(crate::f03_perf_owner::Open {
            request,
            thread,
            proc,
            attr,
            pid,
            group_fd,
            perf_event_open_nr,
            cpu,
            mckfd_size,
            mckfd_alloc_flags,
            event_pid_offset,
            event_counter_id_offset,
            proc_mckfd_offset,
            mckfd_next_offset,
            mckfd_fd_offset,
            mckfd_data_offset,
            event_group_leader_offset,
            event_sibling_list_offset,
            event_group_entry_offset,
            event_nr_siblings_offset,
            event_pmc_status_offset,
            thread_pmc_alloc_map_offset,
            proc_mckfd_lock_offset,
            mckfd_sig_no_offset,
            mckfd_read_cb_offset,
            mckfd_ioctl_cb_offset,
            mckfd_mmap_cb_offset,
            mckfd_close_cb_offset,
            mckfd_fcntl_cb_offset,
            event_alloc_fn,
            counter_alloc_fn,
            syscall_fn,
            mckfd_alloc_fn,
            read_fn,
            ioctl_fn,
            mmap_fn,
            close_fn,
            fcntl_fn,
            lock_fn,
            unlock_fn,
        }) };
    }

    if request.is_null() || thread.is_null() || proc.is_null() || attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(event_alloc) = event_alloc_fn else {
        return -EINVAL as CLong;
    };
    let Some(mckfd_alloc) = mckfd_alloc_fn else {
        return -EINVAL as CLong;
    };

    let mut event = core::ptr::null_mut::<c_void>();
    let mut ret = event_alloc(core::ptr::addr_of_mut!(event), attr);
    if ret != 0 {
        return ret as CLong;
    }

    let counter_idx = perf_event_open_counter_body_result(
        event,
        thread,
        pid,
        event_pid_offset,
        event_counter_id_offset,
        counter_alloc_fn,
    );
    if counter_idx < 0 {
        return counter_idx;
    }

    let group_rc = perf_event_open_group_body_result(
        event,
        proc,
        group_fd,
        counter_idx as CInt,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
    );
    if group_rc != 0 {
        return group_rc;
    }

    let fd = perf_event_open_linux_fd_body_result(
        request,
        thread,
        counter_idx as CInt,
        perf_event_open_nr,
        cpu,
        thread_pmc_alloc_map_offset,
        syscall_fn,
    );
    if fd < 0 {
        return fd;
    }

    let sfd = mckfd_alloc(mckfd_size, mckfd_alloc_flags);
    if sfd.is_null() {
        return -ENOMEM as CLong;
    }

    ret = perf_event_open_mckfd_publish_body_result(
        sfd,
        event,
        proc,
        fd as CInt,
        proc_mckfd_lock_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_sig_no_offset,
        mckfd_data_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    ) as CInt;
    ret as CLong
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn perf_event_open_entry_body_result(
    request: *mut SyscallRequest,
    thread: *mut c_void,
    proc: *mut c_void,
    attr: *mut c_void,
    user_attr_addr: CULong,
    attr_size: SizeT,
    attr_type_offset: SizeT,
    attr_read_format_offset: SizeT,
    attr_sample_period_offset: SizeT,
    pid: CInt,
    validation_cpu: CInt,
    group_fd: CInt,
    flags: CULong,
    linux_cpu: CInt,
    raw_type: CULong,
    hardware_type: CULong,
    hw_cache_type: CULong,
    unsupported_read_format_mask: CULong,
    sample_period_sign_bit: CULong,
    perf_event_open_nr: CInt,
    mckfd_size: SizeT,
    mckfd_alloc_flags: CULong,
    event_pid_offset: SizeT,
    event_counter_id_offset: SizeT,
    proc_mckfd_offset: SizeT,
    mckfd_next_offset: SizeT,
    mckfd_fd_offset: SizeT,
    mckfd_data_offset: SizeT,
    event_group_leader_offset: SizeT,
    event_sibling_list_offset: SizeT,
    event_group_entry_offset: SizeT,
    event_nr_siblings_offset: SizeT,
    event_pmc_status_offset: SizeT,
    thread_pmc_alloc_map_offset: SizeT,
    proc_mckfd_lock_offset: SizeT,
    mckfd_sig_no_offset: SizeT,
    mckfd_read_cb_offset: SizeT,
    mckfd_ioctl_cb_offset: SizeT,
    mckfd_mmap_cb_offset: SizeT,
    mckfd_close_cb_offset: SizeT,
    mckfd_fcntl_cb_offset: SizeT,
    copy_from_fn: Option<SyscallCopyFromUserFn>,
    attr_freq_fn: Option<PerfAttrFreqFn>,
    event_alloc_fn: Option<PerfOpenAllocEventFn>,
    counter_alloc_fn: Option<PerfCounterAllocFn>,
    syscall_fn: Option<PerfOpenSyscallFn>,
    mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
    read_fn: Option<SyscallMckfdLongFn>,
    ioctl_fn: Option<SyscallMckfdIntFn>,
    mmap_fn: Option<SyscallMckfdLongFn>,
    close_fn: Option<SyscallMckfdIntFn>,
    fcntl_fn: Option<SyscallMckfdIntFn>,
    lock_fn: Option<SyscallMckfdLockFn>,
    unlock_fn: Option<SyscallMckfdUnlockFn>,
) -> CLong {
    if attr.is_null() {
        return -EINVAL as CLong;
    }
    let Some(copy_from_user) = copy_from_fn else {
        return -EINVAL as CLong;
    };
    let Some(attr_freq) = attr_freq_fn else {
        return -EINVAL as CLong;
    };

    if copy_from_user(attr.cast::<u8>(), user_attr_addr, attr_size) != 0 {
        return -EFAULT as CLong;
    }

    let attr_base = attr.cast::<u8>();
    let attr_type = read_volatile(field_ptr::<u32>(attr_base, attr_type_offset)) as CULong;
    let read_format = read_volatile(field_ptr::<CULong>(attr_base, attr_read_format_offset));
    let sample_period = read_volatile(field_ptr::<CULong>(attr_base, attr_sample_period_offset));
    let freq = attr_freq(attr.cast_const());

    let ret = perf_event_open_validate_body_result(
        validation_cpu,
        flags,
        attr_type,
        read_format,
        freq,
        sample_period,
        raw_type,
        hardware_type,
        hw_cache_type,
        unsupported_read_format_mask,
        sample_period_sign_bit,
    );
    if ret != 0 {
        return ret as CLong;
    }

    perf_event_open_body_result(
        request,
        thread,
        proc,
        attr,
        pid,
        group_fd,
        perf_event_open_nr,
        linux_cpu,
        mckfd_size,
        mckfd_alloc_flags,
        event_pid_offset,
        event_counter_id_offset,
        proc_mckfd_offset,
        mckfd_next_offset,
        mckfd_fd_offset,
        mckfd_data_offset,
        event_group_leader_offset,
        event_sibling_list_offset,
        event_group_entry_offset,
        event_nr_siblings_offset,
        event_pmc_status_offset,
        thread_pmc_alloc_map_offset,
        proc_mckfd_lock_offset,
        mckfd_sig_no_offset,
        mckfd_read_cb_offset,
        mckfd_ioctl_cb_offset,
        mckfd_mmap_cb_offset,
        mckfd_close_cb_offset,
        mckfd_fcntl_cb_offset,
        event_alloc_fn,
        counter_alloc_fn,
        syscall_fn,
        mckfd_alloc_fn,
        read_fn,
        ioctl_fn,
        mmap_fn,
        close_fn,
        fcntl_fn,
        lock_fn,
        unlock_fn,
    )
}


mod f03_sync_child_layout_v2 {
 use crate::abi::{CInt,CLong,CULong,IhkAtomic64,AbiListHead};
 use crate::f03_perf_attr_callbacks::PerfEventAttr;
 use crate::x86_perfctr::HwPerfEventExtra;
 use core::mem::{size_of,align_of,offset_of};
 #[repr(C)]
 pub struct HwPerfEvent {
  pub prev_count:IhkAtomic64,pub sample_period:u64,pub last_period:u64,pub period_left:IhkAtomic64,
 }
 // Complete genuine runtime mc_perf_event, distinct from x86_perfctr's128B prefix.
 // Used only for constants/layout witnesses; never constructs a borrowed whole C event.
 #[repr(C)]
 pub struct FullMcPerfEvent {
  pub attr:PerfEventAttr,pub extra_reg:HwPerfEventExtra,pub hw_config:CULong,pub hw_config_ext:CULong,
  pub state:CInt,pub cpu_id:CInt,pub counter_id:CInt,pub count:IhkAtomic64,
  pub child_count_total:CULong,pub pmc_status:CULong,pub sample_freq:CULong,
  pub parent:*mut FullMcPerfEvent,pub group_leader:*mut FullMcPerfEvent,
  pub sibling_list:AbiListHead,pub nr_siblings:CInt,pub pid:CInt,pub group_entry:AbiListHead,
  pub use_invariant_tsc:CInt,pub base_user_tsc:CLong,pub stopped_user_tsc:CLong,pub user_accum_count:CLong,
  pub base_system_tsc:CLong,pub stopped_system_tsc:CLong,pub system_accum_count:CLong,pub hw:HwPerfEvent,
 }
 // Rust-owned runtime offset array: no replacement C data object is introduced.
 #[no_mangle]
 pub static f03_sync_child_offsets_v1:[CULong;8]=[
  (offset_of!(FullMcPerfEvent,attr)+offset_of!(PerfEventAttr,flags)) as CULong,
  offset_of!(FullMcPerfEvent,pid) as CULong,
  offset_of!(FullMcPerfEvent,group_leader) as CULong,
  offset_of!(FullMcPerfEvent,counter_id) as CULong,
  offset_of!(FullMcPerfEvent,count) as CULong,
  offset_of!(FullMcPerfEvent,child_count_total) as CULong,
  offset_of!(FullMcPerfEvent,sibling_list) as CULong,
  offset_of!(FullMcPerfEvent,group_entry) as CULong,
 ];
 #[cfg(f03_sync_child_fixture)]
 #[no_mangle]
 pub static F03_SYNC_CHILD_LAYOUT_ABI:[CULong;49]=[
  (size_of::<FullMcPerfEvent>()) as CULong,
  (align_of::<FullMcPerfEvent>()) as CULong,
  (offset_of!(FullMcPerfEvent,attr)) as CULong,
  (offset_of!(FullMcPerfEvent,extra_reg)) as CULong,
  (offset_of!(FullMcPerfEvent,hw_config)) as CULong,
  (offset_of!(FullMcPerfEvent,hw_config_ext)) as CULong,
  (offset_of!(FullMcPerfEvent,state)) as CULong,
  (offset_of!(FullMcPerfEvent,cpu_id)) as CULong,
  (offset_of!(FullMcPerfEvent,counter_id)) as CULong,
  (offset_of!(FullMcPerfEvent,count)) as CULong,
  (offset_of!(FullMcPerfEvent,child_count_total)) as CULong,
  (offset_of!(FullMcPerfEvent,pmc_status)) as CULong,
  (offset_of!(FullMcPerfEvent,sample_freq)) as CULong,
  (offset_of!(FullMcPerfEvent,parent)) as CULong,
  (offset_of!(FullMcPerfEvent,group_leader)) as CULong,
  (offset_of!(FullMcPerfEvent,sibling_list)) as CULong,
  (offset_of!(FullMcPerfEvent,nr_siblings)) as CULong,
  (offset_of!(FullMcPerfEvent,pid)) as CULong,
  (offset_of!(FullMcPerfEvent,group_entry)) as CULong,
  (offset_of!(FullMcPerfEvent,use_invariant_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,base_user_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,stopped_user_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,user_accum_count)) as CULong,
  (offset_of!(FullMcPerfEvent,base_system_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,stopped_system_tsc)) as CULong,
  (offset_of!(FullMcPerfEvent,system_accum_count)) as CULong,
  (offset_of!(FullMcPerfEvent,hw)) as CULong,
  (size_of::<HwPerfEvent>()) as CULong,
  (align_of::<HwPerfEvent>()) as CULong,
  (offset_of!(HwPerfEvent,prev_count)) as CULong,
  (offset_of!(HwPerfEvent,sample_period)) as CULong,
  (offset_of!(HwPerfEvent,last_period)) as CULong,
  (offset_of!(HwPerfEvent,period_left)) as CULong,
  (size_of::<HwPerfEventExtra>()) as CULong,
  (align_of::<HwPerfEventExtra>()) as CULong,
  (offset_of!(HwPerfEventExtra,config)) as CULong,
  (offset_of!(HwPerfEventExtra,reg)) as CULong,
  (offset_of!(HwPerfEventExtra,idx)) as CULong,
  (size_of::<PerfEventAttr>()) as CULong,
  (align_of::<PerfEventAttr>()) as CULong,
  (offset_of!(PerfEventAttr,flags)) as CULong,
  (offset_of!(PerfEventAttr,sample_type)) as CULong,
  (offset_of!(PerfEventAttr,read_format)) as CULong,
  (size_of::<IhkAtomic64>()) as CULong,
  (align_of::<IhkAtomic64>()) as CULong,
  (size_of::<AbiListHead>()) as CULong,
  (align_of::<AbiListHead>()) as CULong,
  (offset_of!(AbiListHead,next)) as CULong,
  (offset_of!(AbiListHead,prev)) as CULong,
 ];

}

mod f03_perf_counter_control_v1 {
    use core::ffi::c_void;
    use core::mem::offset_of;

    use crate::abi::{CInt, Process, SizeT, Thread};

    use super::{
        perf_counter_set_entry_body_result, perf_reset_body_result, perf_start_body_result,
        perf_stop_body_result, PerfCounterAttrFlagsFn, PerfCounterExtraSetFn,
        PerfCounterInitRawFn, PerfCounterMaskCheckFn, PerfCounterStartFn, PerfCounterStopFn,
        PerfEventIntFn, PerfEventUpdateFn, PerfReadValueFn, SyncChildAtomic64SetFn,
    };

    #[repr(C)]
    pub(super) struct EventLayout {
        pub(super) group_leader: SizeT,
        pub(super) sibling_list: SizeT,
        pub(super) group_entry: SizeT,
        pub(super) counter_id: SizeT,
        pub(super) state: SizeT,
        pub(super) use_invariant_tsc: SizeT,
        pub(super) base_user_tsc: SizeT,
        pub(super) stopped_user_tsc: SizeT,
        pub(super) user_accum_count: SizeT,
        pub(super) base_system_tsc: SizeT,
        pub(super) stopped_system_tsc: SizeT,
        pub(super) system_accum_count: SizeT,
        pub(super) count: SizeT,
        pub(super) attr: SizeT,
        pub(super) hw_config: SizeT,
        pub(super) extra_reg_reg: SizeT,
        pub(super) kernel_mode: CInt,
        pub(super) user_mode: CInt,
        pub(super) inactive_state: CInt,
        pub(super) active_state: CInt,
        pub(super) pp_count: CInt,
        pub(super) pp_none: CInt,
    }

    #[repr(C)]
    pub(super) struct Providers {
        pub(super) attr_flags: Option<PerfCounterAttrFlagsFn>,
        pub(super) extra_set: Option<PerfCounterExtraSetFn>,
        pub(super) init_raw: Option<PerfCounterInitRawFn>,
        pub(super) mask_check: Option<PerfCounterMaskCheckFn>,
        pub(super) set_period: Option<PerfEventIntFn>,
        pub(super) counter_start: Option<PerfCounterStartFn>,
        pub(super) counter_stop: Option<PerfCounterStopFn>,
        pub(super) event_update: Option<PerfEventUpdateFn>,
        pub(super) read_value: Option<PerfReadValueFn>,
        pub(super) atomic_set: Option<SyncChildAtomic64SetFn>,
    }

    unsafe extern "C" {
        pub(super) static f03_perf_event_layout_v1: EventLayout;
        pub(super) static f03_perf_counter_providers_v1: Providers;
    }

    unsafe fn current_thread() -> *mut Thread {
        // SAFETY: Same live current CPU-local lookup as the original entries.
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        unsafe { (*cpu).current }
    }

    unsafe extern "C" fn counter_set(event: *mut c_void) -> CInt {
        // SAFETY: Complete start helper supplies the same live event it owns.
        unsafe { perf_counter_set(event) }
    }

    /// Configure the original complete counter body through genuine providers.
    ///
    /// # Safety
    /// Event must obey the original perf lifetime and hardware-access contracts.
    /// Actual C header data supplies all offsets/bitfield boundaries and modes;
    /// no private Rust layout or getter is invented for the perf event structure.
    #[no_mangle]
    pub unsafe extern "C" fn perf_counter_set(event: *mut c_void) -> CInt {
        // SAFETY: Immutable source-bound actual C offset/provider data, cfg-matched.
        unsafe {
            perf_counter_set_entry_body_result(
                event, f03_perf_event_layout_v1.attr, f03_perf_event_layout_v1.counter_id,
                f03_perf_event_layout_v1.hw_config, f03_perf_event_layout_v1.extra_reg_reg,
                f03_perf_event_layout_v1.kernel_mode, f03_perf_event_layout_v1.user_mode,
                f03_perf_counter_providers_v1.attr_flags,
                f03_perf_counter_providers_v1.extra_set,
                f03_perf_counter_providers_v1.init_raw,
            )
        }
    }

    /// Start the original leader/sibling transaction and ignore its result as C did.
    ///
    /// # Safety
    /// Event/group/current thread ownership and counter programming serialization
    /// must match the original complete helper. No extra ref or lock is introduced.
    #[no_mangle]
    pub unsafe extern "C" fn perf_start(event: *mut c_void) {
        let thread = unsafe { current_thread() };
        // SAFETY: Real layouts, original providers and unchanged full helper order.
        let _ = unsafe {
            perf_start_body_result(
                event, thread.cast(), f03_perf_event_layout_v1.group_leader,
                f03_perf_event_layout_v1.sibling_list, f03_perf_event_layout_v1.group_entry,
                f03_perf_event_layout_v1.counter_id, f03_perf_event_layout_v1.state,
                f03_perf_event_layout_v1.use_invariant_tsc,
                f03_perf_event_layout_v1.base_user_tsc,
                f03_perf_event_layout_v1.stopped_user_tsc,
                f03_perf_event_layout_v1.user_accum_count,
                f03_perf_event_layout_v1.base_system_tsc,
                f03_perf_event_layout_v1.stopped_system_tsc,
                f03_perf_event_layout_v1.system_accum_count,
                offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
                offset_of!(Thread, proc), offset_of!(Process, perf_status),
                f03_perf_event_layout_v1.inactive_state, f03_perf_event_layout_v1.active_state,
                f03_perf_event_layout_v1.pp_count,
                f03_perf_counter_providers_v1.mask_check,
                f03_perf_counter_providers_v1.set_period, Some(counter_set),
                f03_perf_counter_providers_v1.counter_start,
            )
        };
    }

    /// Reset complete original leader/sibling state and keep the original void ABI.
    ///
    /// # Safety
    /// Actual event/group lifetime, accounting and atomic backend contracts apply.
    /// Complete helper and existing value reader preserve original effect order.
    #[no_mangle]
    pub unsafe extern "C" fn perf_reset(event: *mut c_void) {
        let thread = unsafe { current_thread() };
        // SAFETY: Actual C event offsets and genuine Thread layout/provider data.
        let _ = unsafe {
            perf_reset_body_result(
                event, thread.cast(), f03_perf_event_layout_v1.group_leader,
                f03_perf_event_layout_v1.sibling_list, f03_perf_event_layout_v1.group_entry,
                f03_perf_event_layout_v1.counter_id, f03_perf_event_layout_v1.use_invariant_tsc,
                f03_perf_event_layout_v1.base_user_tsc,
                f03_perf_event_layout_v1.stopped_user_tsc,
                f03_perf_event_layout_v1.user_accum_count,
                f03_perf_event_layout_v1.base_system_tsc,
                f03_perf_event_layout_v1.stopped_system_tsc,
                f03_perf_event_layout_v1.system_accum_count, f03_perf_event_layout_v1.count,
                offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
                f03_perf_counter_providers_v1.mask_check,
                f03_perf_counter_providers_v1.read_value,
                f03_perf_counter_providers_v1.atomic_set,
            )
        };
    }

    /// Stop the original bounded group transaction with its unchanged void result.
    ///
    /// # Safety
    /// Complete helper retains its existing group bounds, state and hardware
    /// serialization requirements. Its fixed stop-event capacity is unchanged.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_stop_v1(event: *mut c_void) {
        let thread = unsafe { current_thread() };
        // SAFETY: Exact real offsets/providers and original active/inactive states.
        let _ = unsafe {
            perf_stop_body_result(
                event, thread.cast(), f03_perf_event_layout_v1.group_leader,
                f03_perf_event_layout_v1.sibling_list, f03_perf_event_layout_v1.group_entry,
                f03_perf_event_layout_v1.counter_id, f03_perf_event_layout_v1.state,
                f03_perf_event_layout_v1.use_invariant_tsc,
                f03_perf_event_layout_v1.stopped_user_tsc,
                f03_perf_event_layout_v1.stopped_system_tsc,
                offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
                offset_of!(Thread, proc), offset_of!(Process, monitoring_event),
                offset_of!(Process, perf_status), f03_perf_event_layout_v1.active_state,
                f03_perf_event_layout_v1.inactive_state, f03_perf_event_layout_v1.pp_none,
                0, f03_perf_counter_providers_v1.mask_check,
                f03_perf_counter_providers_v1.counter_stop,
                f03_perf_counter_providers_v1.event_update,
            )
        };
    }

    /// Genuine callback adapters retain the existing ioctl dispatch ABI.
    ///
    /// # Safety
    /// The actual ioctl helper supplies a live event under its original ownership.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_start_bridge_v1(event: *mut c_void) {
        unsafe { perf_start(event) };
    }

    /// # Safety
    /// Same original event/group ownership as the complete stop transaction.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_stop_bridge_v1(event: *mut c_void) {
        unsafe { f03_perf_stop_v1(event) };
    }

    /// # Safety
    /// Same original event/group ownership as the complete reset transaction.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_reset_bridge_v1(event: *mut c_void) {
        unsafe { perf_reset(event) };
    }

#[export_name="f03_perf_event_layout_v1"]
static HOST_CONTROL_LAYOUT:EventLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 EventLayout{group_leader:offset_of!(E,group_leader),sibling_list:offset_of!(E,sibling_list),group_entry:offset_of!(E,group_entry),counter_id:offset_of!(E,counter_id),state:offset_of!(E,state),use_invariant_tsc:offset_of!(E,use_invariant_tsc),base_user_tsc:offset_of!(E,base_user_tsc),stopped_user_tsc:offset_of!(E,stopped_user_tsc),user_accum_count:offset_of!(E,user_accum_count),base_system_tsc:offset_of!(E,base_system_tsc),stopped_system_tsc:offset_of!(E,stopped_system_tsc),system_accum_count:offset_of!(E,system_accum_count),count:offset_of!(E,count),attr:offset_of!(E,attr),hw_config:offset_of!(E,hw_config),extra_reg_reg:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,reg),kernel_mode:2,user_mode:1,inactive_state:0,active_state:1,pp_count:2,pp_none:0}
};
#[export_name="f03_perf_counter_providers_v1"]
static HOST_CONTROL_PROVIDERS:Providers=Providers{attr_flags:Some(crate::f03_perf_attr_callbacks::f03_perf_counter_attr_flags_v1),extra_set:Some(crate::host_perf_bindings::extra_set),init_raw:Some(crate::host_perf_bindings::init_raw),mask_check:Some(crate::x86_perfctr::ihk_mc_perf_counter_mask_check),set_period:Some(crate::host_perf_bindings::set_period),counter_start:Some(crate::host_perf_bindings::start),counter_stop:Some(crate::host_perf_bindings::stop),event_update:Some(crate::host_perf_bindings::event_update),read_value:Some(super::f03_perf_read_entries_v1::f03_perf_read_value_bridge_v1),atomic_set:Some(crate::host_perf_bindings::atomic_set)};

}

mod f03_perf_descriptor_entries_v1 {
    use core::ffi::c_void;
    use core::mem::offset_of;

    use crate::abi::{CInt, CLong, Mckfd, SizeT, Thread, X86UserContext};

    use super::{
        perf_close_body_result, perf_fcntl_body_result, syscall_mckfd_free_bridge,
        SyscallForwardContextFn,
    };

    #[repr(C)]
    pub(super) struct CloseLayout {
        pub(super) counter_id: SizeT,
        pub(super) extra_reg_reg: SizeT,
        pub(super) extra_reg_idx: SizeT,
        pub(super) fcntl_nr: CInt,
        pub(super) forward: Option<SyscallForwardContextFn>,
    }

    unsafe extern "C" {
        pub(super) static f03_perf_descriptor_layout_v1: CloseLayout;
    }

    /// Close the actual event and release its original counter allocation maps.
    ///
    /// # Safety
    /// sfd must be the live descriptor supplied to the original close operation.
    /// Its event and current-thread map ownership must obey original synchronization.
    /// The genuine tracked-free provider consumes the event exactly as before.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_close_v1(
        sfd: *mut Mckfd, _ctx: *mut X86UserContext,
    ) -> CInt {
        // SAFETY: Actual descriptor field and live current CPU-local/thread lookup.
        // ctx remains unused; no descriptor data clearing or extra ref is invented.
        let event = unsafe { (*sfd).data } as *mut c_void;
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        let thread = unsafe { (*cpu).current };
        unsafe {
            perf_close_body_result(
                event, thread.cast(), f03_perf_descriptor_layout_v1.counter_id,
                f03_perf_descriptor_layout_v1.extra_reg_reg,
                f03_perf_descriptor_layout_v1.extra_reg_idx,
                offset_of!(Thread, pmc_alloc_map), offset_of!(Thread, extra_reg_alloc_map),
                Some(syscall_mckfd_free_bridge),
            ) as CInt
        }
    }

    /// Apply original signal-number state before forwarding the initialized context.
    ///
    /// # Safety
    /// sfd and ctx must be genuine live callback inputs. ctx contains the initialized
    /// full syscall registers; this entry does not construct a partial context.
    /// Existing forwarding retains its original ownership and return/error behavior.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_fcntl_v1(
        sfd: *mut Mckfd, ctx: *mut X86UserContext,
    ) -> CInt {
        // SAFETY: Read only the original two argument registers through real getters.
        let cmd = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) } as CInt;
        let arg = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) } as CLong;
        unsafe {
            perf_fcntl_body_result(
                sfd.cast(), ctx.cast(), cmd, arg, f03_perf_descriptor_layout_v1.fcntl_nr,
                10, 0xf, offset_of!(Mckfd, padding), f03_perf_descriptor_layout_v1.forward,
            ) as CInt
        }
    }

#[export_name="f03_perf_descriptor_layout_v1"]
static HOST_DESCRIPTOR_LAYOUT:CloseLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 CloseLayout{counter_id:offset_of!(E,counter_id),extra_reg_reg:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,reg),extra_reg_idx:offset_of!(E,extra_reg)+offset_of!(crate::x86_perfctr::HwPerfEventExtra,idx),fcntl_nr:72,forward:Some(crate::host_perf_bindings::context_forward)}
};

}

mod f03_perf_read_entries_v1 {
    use core::ffi::c_void;
    use core::mem::offset_of;

    use crate::abi::{CInt, CLong, CULong, Mckfd, SizeT, Thread, X86UserContext};

    use super::{
        perf_event_read_group_body_result, perf_event_read_one_body_result,
        perf_event_read_value_entry_body_result, perf_read_body_result,
        syscall_copy_to_user_bridge, PerfEventUpdateFn, PerfReadAttrFlagsFn,
        SyscallAtomic64ReadFn,
    };

    #[repr(C)]
    pub(super) struct ReadLayout {
        pub(super) attr: SizeT,
        pub(super) pid: SizeT,
        pub(super) use_invariant_tsc: SizeT,
        pub(super) count: SizeT,
        pub(super) child_count_total: SizeT,
        pub(super) base_user_tsc: SizeT,
        pub(super) stopped_user_tsc: SizeT,
        pub(super) user_accum_count: SizeT,
        pub(super) base_system_tsc: SizeT,
        pub(super) stopped_system_tsc: SizeT,
        pub(super) system_accum_count: SizeT,
        pub(super) group_leader: SizeT,
        pub(super) nr_siblings: SizeT,
        pub(super) sibling_list: SizeT,
        pub(super) group_entry: SizeT,
        pub(super) read_format: SizeT,
        pub(super) group_flag: CULong,
    }

    #[repr(C)]
    pub(super) struct ReadProviders {
        pub(super) attr_flags: Option<PerfReadAttrFlagsFn>,
        pub(super) update: Option<PerfEventUpdateFn>,
        pub(super) atomic_read: Option<SyscallAtomic64ReadFn>,
    }

    unsafe extern "C" {
        pub(super) static f03_perf_read_layout_v1: ReadLayout;
        pub(super) static f03_perf_read_providers_v1: ReadProviders;
    }

    /// Read the actual event accounting through the complete existing Rust body.
    ///
    /// # Safety
    /// The event, its parent/group and current thread must obey original perf
    /// lifetime and synchronization contracts. Actual C data retains bitfield,
    /// event-update and atomic-read providers; no guessed perf layout is read.
    #[no_mangle]
    pub unsafe extern "C" fn perf_event_read_value(event: *mut c_void) -> CULong {
        // SAFETY: Same live current thread and actual C layout/provider authority.
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        let thread = unsafe { (*cpu).current };
        unsafe {
            perf_event_read_value_entry_body_result(
                event, thread.cast(), f03_perf_read_layout_v1.attr,
                f03_perf_read_layout_v1.pid, f03_perf_read_layout_v1.use_invariant_tsc,
                f03_perf_read_layout_v1.count, f03_perf_read_layout_v1.child_count_total,
                f03_perf_read_layout_v1.base_user_tsc,
                f03_perf_read_layout_v1.stopped_user_tsc,
                f03_perf_read_layout_v1.user_accum_count,
                f03_perf_read_layout_v1.base_system_tsc,
                f03_perf_read_layout_v1.stopped_system_tsc,
                f03_perf_read_layout_v1.system_accum_count,
                offset_of!(Thread, user_tsc), offset_of!(Thread, system_tsc),
                f03_perf_read_providers_v1.attr_flags,
                f03_perf_read_providers_v1.update, f03_perf_read_providers_v1.atomic_read,
            )
        }
    }

    /// # Safety
    /// Callback receives the same live event owned by its complete helper caller.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_value_bridge_v1(event: *mut c_void) -> CULong {
        unsafe { perf_event_read_value(event) }
    }

    /// Read the original group stream, retaining original int result truncation.
    ///
    /// # Safety
    /// Group/list ownership and user destination obey original helper contracts.
    /// The real usercopy endpoint consumes buf; this entry does not dereference it.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_group_v1(
        event: *mut c_void, _read_format: CULong, buf: *mut i8,
    ) -> CInt {
        // SAFETY: Original complete group iterator and actual header offsets.
        unsafe {
            perf_event_read_group_body_result(
                event, buf as CULong, f03_perf_read_layout_v1.group_leader,
                f03_perf_read_layout_v1.nr_siblings, f03_perf_read_layout_v1.sibling_list,
                f03_perf_read_layout_v1.group_entry, Some(f03_perf_read_value_bridge_v1),
                Some(syscall_copy_to_user_bridge),
            ) as CInt
        }
    }

    /// Read one original event word and retain its int return ABI.
    ///
    /// # Safety
    /// Original live-event and actual usercopy destination requirements apply.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_one_v1(
        event: *mut c_void, _read_format: CULong, buf: *mut i8,
    ) -> CInt {
        unsafe {
            perf_event_read_one_body_result(
                event, buf as CULong, Some(f03_perf_read_value_bridge_v1),
                Some(syscall_copy_to_user_bridge),
            ) as CInt
        }
    }

    /// # Safety
    /// Same genuine event/list and destination contracts as the group entry.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_group_bridge_v1(
        event: *mut c_void, read_format: CULong, buf_addr: CULong,
    ) -> CLong {
        // SAFETY: Preserve the original int intermediary before long extension.
        unsafe { f03_perf_read_group_v1(event, read_format, buf_addr as *mut i8) as CLong }
    }

    /// # Safety
    /// Same genuine event and destination contracts as the one-word entry.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_one_bridge_v1(
        event: *mut c_void, read_format: CULong, buf_addr: CULong,
    ) -> CLong {
        unsafe { f03_perf_read_one_v1(event, read_format, buf_addr as *mut i8) as CLong }
    }

    /// Decode the original descriptor/user argument and select the complete reader.
    ///
    /// # Safety
    /// sfd/ctx must be actual live callback inputs with a live perf event. Its
    /// read_format field must be initialized and synchronized under the original
    /// contract. No descriptor/event reference or new NULL acceptance is added.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_read_v1(
        sfd: *mut Mckfd, ctx: *mut X86UserContext,
    ) -> CLong {
        #[cfg(f03_perf_owner_protocol)]
        { return unsafe{crate::f03_perf_owner::descriptor_read(sfd,ctx)}; }

        // SAFETY: Same actual register/long descriptor storage as the C entry.
        let buf_addr = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) };
        let count = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) };
        let event = unsafe { (*sfd).data } as *mut c_void;
        // SAFETY: Genuine C header offset into the initialized event attr field.
        let read_format = unsafe {
            event.cast::<u8>().add(f03_perf_read_layout_v1.read_format).cast::<CULong>().read()
        };
        let mut required = core::mem::size_of::<CULong>() as CULong;
        if read_format & f03_perf_read_layout_v1.group_flag != 0 {
            // SAFETY: The same live leader/count fields used by the group reader.
            let leader = unsafe {
                event.cast::<u8>().add(f03_perf_read_layout_v1.group_leader)
                    .cast::<*mut c_void>().read()
            };
            if leader.is_null() {
                return -super::EINVAL as CLong;
            }
            let nr_siblings = unsafe {
                leader.cast::<u8>().add(f03_perf_read_layout_v1.nr_siblings)
                    .cast::<CInt>().read()
            };
            if nr_siblings < 0 {
                return -super::EINVAL as CLong;
            }
            // Widen before adding the group header and leader value.
            required = (nr_siblings as CULong + 2) * core::mem::size_of::<CULong>() as CULong;
        }
        if count < required {
            return -super::EINVAL as CLong;
        }
        unsafe {
            perf_read_body_result(
                event, buf_addr, read_format, f03_perf_read_layout_v1.group_flag,
                Some(f03_perf_read_group_bridge_v1), Some(f03_perf_read_one_bridge_v1),
            )
        }
    }

#[export_name="f03_perf_read_layout_v1"]
static HOST_READ_LAYOUT:ReadLayout={
 use super::f03_sync_child_layout_v2::FullMcPerfEvent as E;
 ReadLayout{attr:offset_of!(E,attr),pid:offset_of!(E,pid),use_invariant_tsc:offset_of!(E,use_invariant_tsc),count:offset_of!(E,count),child_count_total:offset_of!(E,child_count_total),base_user_tsc:offset_of!(E,base_user_tsc),stopped_user_tsc:offset_of!(E,stopped_user_tsc),user_accum_count:offset_of!(E,user_accum_count),base_system_tsc:offset_of!(E,base_system_tsc),stopped_system_tsc:offset_of!(E,stopped_system_tsc),system_accum_count:offset_of!(E,system_accum_count),group_leader:offset_of!(E,group_leader),nr_siblings:offset_of!(E,nr_siblings),sibling_list:offset_of!(E,sibling_list),group_entry:offset_of!(E,group_entry),read_format:offset_of!(E,attr)+offset_of!(crate::f03_perf_attr_callbacks::PerfEventAttr,read_format),group_flag:8}
};
#[export_name="f03_perf_read_providers_v1"]
static HOST_READ_PROVIDERS:ReadProviders=ReadProviders{attr_flags:Some(crate::f03_perf_attr_callbacks::f03_perf_read_attr_flags_v1),update:Some(crate::host_perf_bindings::event_update),atomic_read:Some(crate::host_perf_bindings::atomic_read)};

}

mod f03_perf_mmap_entry_v1 {
    use crate::abi::{CInt, CLong, CULong, Mckfd, SizeT, X86UserContext};
    use super::{perf_mmap_body_result, PerfDoMmapFn};

    // Actual C headers supply constants and offsets; no duplicated perf-page ABI.
    #[repr(C)]
    struct MmapBinding {
        map_anonymous: CInt,
        prot_write: CInt,
        data_head: SizeT,
        capabilities: SizeT,
        cap_user_rdpmc: CULong,
        do_mmap: Option<PerfDoMmapFn>,
    }

    unsafe extern "C" {
        static f03_perf_mmap_binding_v1: MmapBinding;
    }

    /// Invoke the existing complete Rust mapping transaction with the original ABI.
    ///
    /// # Safety
    /// `ctx` is the genuine live syscall context. The existing mmap provider owns
    /// allocation, synchronization and mapping lifetime. A nonnegative result must
    /// name the writable mapping covering both actual perf-page metadata fields,
    /// exactly as required by the original callback. `sfd` remains unused.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_mmap_v1(
        _sfd: *mut Mckfd,
        ctx: *mut X86UserContext,
    ) -> CLong {
        // SAFETY: Read the same six actual registers in their original order.
        let addr = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx) };
        let len = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) } as SizeT;
        let prot = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) } as CInt;
        let flags = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx) } as CInt;
        let fd = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx) } as CInt;
        let off = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg5(ctx) } as CLong;
        // SAFETY: Immutable, cfg-matched header/provider data; existing Rust body
        // retains negative errors without metadata access and owns success writes.
        unsafe {
            let binding = &f03_perf_mmap_binding_v1;
            perf_mmap_body_result(
                addr, len, prot, flags, fd, off,
                binding.map_anonymous, binding.prot_write,
                binding.data_head, binding.capabilities,
                binding.cap_user_rdpmc, binding.do_mmap,
            )
        }
    }

#[export_name="f03_perf_mmap_binding_v1"]
static HOST_MMAP_BINDING:MmapBinding=MmapBinding{map_anonymous:0x20,prot_write:2,data_head:core::mem::offset_of!(crate::host_perf_bindings::PerfMmapPage,data_head),capabilities:core::mem::offset_of!(crate::host_perf_bindings::PerfMmapPage,capabilities),cap_user_rdpmc:1u64<<2,do_mmap:Some(crate::host_perf_bindings::do_mmap)};

}

mod f03_perf_alloc_entry_v1 {
    use core::{ffi::c_void,mem::{offset_of,size_of}};
    use crate::abi::{CInt,CLong,CULong,SizeT};
    use crate::f03_perf_attr_callbacks::PerfEventAttr;
    use crate::x86_perfctr::HwPerfEventExtra;
    use super::f03_sync_child_layout_v2::{FullMcPerfEvent,HwPerfEvent};
    use super::{perf_event_alloc_body_result,SyscallPolicyAllocFn,SyscallMckfdFreeFn,
        SyncChildAtomic64SetFn,PerfEventMapFn,PerfEventValidateFn,PerfExtraRegIdFn,
        PerfExtraRegMsrFn,PerfExtraRegIdxFn,PerfHwEventInitFn};

    #[repr(C)]
    struct PerfAllocationBinding {
        alloc_flags:CULong,hardware_type:CULong,cache_type:CULong,raw_type:CULong,reference_cycles:CULong,
        allocate:Option<SyscallPolicyAllocFn>,release:Option<SyscallMckfdFreeFn>,
        atomic_set:Option<SyncChildAtomic64SetFn>,hardware_map:Option<PerfEventMapFn>,
        cache_map:Option<PerfEventMapFn>,cache_extra_map:Option<PerfEventMapFn>,raw_map:Option<PerfEventMapFn>,
        validate:Option<PerfEventValidateFn>,extra_id:Option<PerfExtraRegIdFn>,
        extra_msr:Option<PerfExtraRegMsrFn>,extra_index:Option<PerfExtraRegIdxFn>,initialize:Option<PerfHwEventInitFn>,
    }
    unsafe extern "C" { static f03_perf_allocation_binding_v1:PerfAllocationBinding; }

    /// Keep the original event allocation, initialized bytes and publication protocol.
    ///
    /// # Safety
    /// Nonnull attributes are aligned, initialized genuine perf_event_attr objects
    /// retained during this synchronous call; nonnull output is writable pointer
    /// storage. Providers retain their existing allocation/lifetime contracts.
    /// The complete existing Rust body releases a failed allocation exactly once
    /// and publishes output only on success. This entry does not own a live PMU.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_event_allocate_v1(output:*mut *mut c_void,attribute:*mut c_void)->CInt {
        let attribute=attribute.cast::<PerfEventAttr>();
        let (event_type,config,frequency,sample_frequency,sample_period)=if attribute.is_null() {
            (0,0,0,0,0)
        } else {
            // SAFETY: Raw scalar/union reads preserve the original initialized C
            // bitfield allocation unit, without borrowing a whole foreign object.
            unsafe { ((*attribute).type_ as CULong,(*attribute).config,
                (((*attribute).flags>>PerfEventAttr::FREQUENCY_SHIFT)&1) as CInt,
                (*attribute).sampling.sample_freq,(*attribute).sampling.sample_period) }
        };
        unsafe {
            let binding=&f03_perf_allocation_binding_v1;
            perf_event_alloc_body_result(output,attribute.cast(),size_of::<FullMcPerfEvent>(),size_of::<PerfEventAttr>(),
                binding.alloc_flags,offset_of!(FullMcPerfEvent,attr),offset_of!(FullMcPerfEvent,group_entry),
                offset_of!(FullMcPerfEvent,sibling_list),offset_of!(FullMcPerfEvent,sample_freq),
                offset_of!(FullMcPerfEvent,nr_siblings),offset_of!(FullMcPerfEvent,count),
                offset_of!(FullMcPerfEvent,child_count_total),offset_of!(FullMcPerfEvent,parent),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,sample_period),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,last_period),
                offset_of!(FullMcPerfEvent,hw)+offset_of!(HwPerfEvent,period_left),
                offset_of!(FullMcPerfEvent,use_invariant_tsc),offset_of!(FullMcPerfEvent,hw_config),
                offset_of!(FullMcPerfEvent,hw_config_ext),offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,config),
                offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,reg),
                offset_of!(FullMcPerfEvent,extra_reg)+offset_of!(HwPerfEventExtra,idx),
                event_type,config,frequency,sample_frequency,sample_period,
                binding.hardware_type,binding.cache_type,binding.raw_type,binding.reference_cycles,
                binding.allocate,binding.release,binding.atomic_set,binding.hardware_map,binding.cache_map,
                binding.cache_extra_map,binding.raw_map,binding.validate,binding.extra_id,binding.extra_msr,
                binding.extra_index,binding.initialize) as CInt
        }
    }

#[export_name="f03_perf_allocation_binding_v1"]
static HOST_ALLOCATION_BINDING:PerfAllocationBinding=PerfAllocationBinding{alloc_flags:2,hardware_type:0,cache_type:3,raw_type:4,reference_cycles:9,allocate:Some(super::perf_event_alloc_kmalloc_bridge),release:Some(super::perf_event_alloc_free_bridge),atomic_set:Some(crate::host_perf_bindings::atomic_set),hardware_map:Some(crate::host_perf_bindings::hardware_map),cache_map:Some(crate::host_perf_bindings::cache_map),cache_extra_map:Some(crate::host_perf_bindings::cache_extra_map),raw_map:Some(crate::host_perf_bindings::raw_map),validate:Some(crate::host_perf_bindings::validate),extra_id:Some(crate::host_perf_bindings::extra_id),extra_msr:Some(crate::host_perf_bindings::extra_msr),extra_index:Some(crate::host_perf_bindings::extra_index),initialize:Some(super::perf_event_alloc_hw_init_bridge)};

}

mod f03_perf_counter_allocate_v1 {
    use core::ffi::c_void;
    use crate::abi::{CInt,Thread};

    /// Retain the callback ABI while reusing the complete existing Rust provider.
    ///
    /// # Safety
    /// The original internal caller retains its nonnull live thread/event for
    /// the synchronous provider call. The existing allocator keeps its own
    /// thread/counter-state contract. This adapter accesses no object field and
    /// introduces no ownership, lock, hardware action, failure or rollback.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_counter_allocate_v1(thread:*mut c_void,event:*mut c_void)->CInt {
        // SAFETY: Preserve both original pointer values, typed thread cast and
        // exact signed-int result. The original provider is not reimplemented.
        unsafe{crate::x86_perfctr::ihk_mc_perfctr_alloc(thread.cast::<Thread>(),event)}
    }
}

pub unsafe extern "C" fn syscall_mckfd_lock_bridge(lock: *mut c_void) -> CLong {
    // SAFETY: The actual lock provider owns IRQ save, ticket acquisition and preemption.
    // The unsigned-to-signed cast retains the original x86_64 C long bit pattern.
    (unsafe { crate::spinlock_helpers::__ihk_mc_spinlock_lock(lock.cast()) }) as CLong
}

pub unsafe extern "C" fn syscall_mckfd_unlock_bridge(lock: *mut c_void, irqstate: CLong) {
    // SAFETY: Casting back restores all original saved bits; the existing provider
    // owns ticket release, preemption enable and IRQ restoration in original order.
    unsafe { crate::spinlock_helpers::__ihk_mc_spinlock_unlock(lock.cast(), irqstate as CULong) };
}

pub unsafe extern "C" fn syscall_alloc_bridge(size: SizeT, flags: CULong) -> *mut c_void {
    // SAFETY: The existing allocator owns allocation and OOM logging. Declarative C
    // data gives the same file/call-site line; its static string is not mutated here.
    unsafe {
        crate::mem_helpers::kmalloc_tracked(
            size as CInt,
            flags,
            core::ptr::addr_of!(f03_mckfd_alloc_origin_file_v1).cast_mut(),
            f03_mckfd_alloc_origin_line_v1,
        )
    }
}

pub unsafe extern "C" fn syscall_mckfd_free_bridge(fdp: *mut c_void) {
    // SAFETY: No allocation is constructed, pointer dereferenced or release suppressed
    // here. The original tracked provider consumes the same pointer and origin data.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            fdp,
            core::ptr::addr_of!(f03_mckfd_free_origin_file_v1).cast_mut(),
            f03_mckfd_free_origin_line_v1,
        )
    };
}

pub unsafe extern "C" fn perf_event_alloc_kmalloc_bridge(size: SizeT, flags: CULong) -> *mut c_void {
    unsafe { crate::mem_helpers::kmalloc_tracked(size as CInt, flags,
        core::ptr::addr_of!(f03_mckfd_alloc_origin_file_v1).cast_mut(),
        F03_PERF_ALLOC_ORIGIN_LINE_V1) }
}

pub unsafe extern "C" fn perf_event_alloc_free_bridge(event: *mut c_void) {
    unsafe { crate::mem_helpers::kfree_tracked(event,
        core::ptr::addr_of!(f03_mckfd_alloc_origin_file_v1).cast_mut(),
        F03_PERF_FREE_ORIGIN_LINE_V1) };
}

pub unsafe extern "C" fn f03_sync_child_count_set_v2(count: *mut c_void, value: CLong) {
    // SAFETY: Keep the existing atomic64 SeqCst store and original signed value.
    unsafe { crate::atomic_helpers::ihk_atomic64_set(count.cast(), value) };
}

unsafe extern "C" fn f03_process_cleanup_find(pid: CInt, lock: *mut c_void) -> *mut c_void {
    // SAFETY: Full helper supplies its actual writable MCS IRQ-save node. Genuine
    // lookup retains the original process-hash read-lock scope until paired unlock.
    unsafe { crate::process_helpers::find_process(pid, lock.cast()).cast() }
}

unsafe extern "C" fn f03_process_cleanup_unlock(proc: *mut c_void, lock: *mut c_void) {
    // SAFETY: Actual process/node pair from the genuine lookup, released once by
    // the unchanged complete helper. This does not invent a process reference.
    unsafe { crate::process_helpers::process_unlock(proc.cast(), lock.cast()) };
}

#[path="f03_perf_owner.rs"] pub(crate) mod f03_perf_owner;

pub unsafe extern "C" fn f03_sync_child_perf_read_v2(counter_id: CInt) -> CULong {
    // SAFETY: Exact original signed selector, genuine provider and unsigned result.
    unsafe { crate::x86_perfctr::ihk_mc_perfctr_read(counter_id) }
}


include!("../common_bindings.rs");

pub unsafe extern "C" fn perf_event_alloc_hw_init_bridge(event: *mut c_void) -> CInt {
    unsafe { crate::x86_perfctr::hw_perf_event_init(event.cast()) }
}

