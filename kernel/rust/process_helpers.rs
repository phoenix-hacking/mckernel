use core::ffi::c_void;
use core::ptr::copy_nonoverlapping;

use crate::abi::{AbiListHead, CInt, CULong, VmRange};

const EINVAL: CInt = 22;
const EACCES: CInt = 13;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;
const EPERM: CInt = 1;

const PAGE_SIZE: CULong = 4096;

const VERIFY_READ: CInt = 0;
const VERIFY_WRITE: CInt = 1;

const PS_EXITED: CInt = 0x10;
const PT_TRACE_SYSCALL: CInt = 0x200;
const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;
const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;
const UTI_STATE_EPILOGUE: CInt = 3;
const PROCESS_TID_ACTION_NONE: CInt = 0;
const PROCESS_TID_ACTION_RELEASE: CInt = 1;
const PROCESS_TID_ACTION_REPLACE: CInt = 2;
const CLONE_VM: CInt = 0x0000_0100;
const CLONE_SIGHAND: CInt = 0x0000_0800;
const WNOWAIT: CInt = 0x0100_0000;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;

const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_WRITE_COMBINED: CULong = 0x400;
const VR_PRIVATE: CULong = 0x2000;
const VR_PROT_NONE: CULong = 0x0000_0000;
const VR_PROT_READ: CULong = 0x0001_0000;
const VR_PROT_WRITE: CULong = 0x0002_0000;
const VR_PROT_EXEC: CULong = 0x0004_0000;
const VR_PROT_MASK: CULong = 0x0007_0000;

const MF_HUGETLBFS: u32 = 0x100000;

const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PTATTR_USER: CULong = 0x04;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_FOR_USER: CULong = 0x20000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const IHK_PTA_REMOTE: CULong = 0;

#[no_mangle]
pub extern "C" fn common_vrflag_to_ptattr(
    flag: CULong,
    _fault: CULong,
    _ptep: *mut c_void,
) -> CULong {
    let mut attr = PTATTR_USER | PTATTR_FOR_USER;

    if (flag & VR_REMOTE) != 0 {
        attr |= IHK_PTA_REMOTE;
    } else if (flag & VR_IO_NOCACHE) != 0 {
        attr |= PTATTR_UNCACHABLE;
    }

    if (flag & VR_PROT_MASK) != VR_PROT_NONE {
        attr |= PTATTR_ACTIVE;
    }

    if (flag & VR_PROT_WRITE) != 0 {
        attr |= PTATTR_WRITABLE;
    }

    if (flag & VR_PROT_EXEC) == 0 {
        attr |= PTATTR_NO_EXECUTE;
    }

    if (flag & VR_WRITE_COMBINED) != 0 {
        attr |= PTATTR_WRITE_COMBINED;
    }

    attr
}

#[no_mangle]
pub extern "C" fn process_split_pgshift_result(pgshift: CInt, addr: CULong) -> CInt {
    if pgshift > 0
        && (pgshift as usize) < CULong::BITS as usize
        && (addr & ((1u64 << pgshift) - 1)) != 0
    {
        0
    } else {
        pgshift
    }
}

#[no_mangle]
pub extern "C" fn process_add_range_bounds_result(
    user_start: CULong,
    user_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    if start < user_start || user_end < end {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_extend_up_result(
    current_end: CULong,
    user_end: CULong,
    has_next: CInt,
    next_start: CULong,
    newend: CULong,
) -> CInt {
    if newend <= current_end {
        -EINVAL
    } else if user_end < newend {
        -EPERM
    } else if has_next != 0 && next_start < newend {
        -ENOMEM
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_change_prot_newflag_result(oldflag: CULong, protflag: CULong) -> CULong {
    (oldflag & !VR_PROT_MASK) | (protflag & VR_PROT_MASK)
}

#[no_mangle]
pub unsafe extern "C" fn process_attr_delta_result(
    oldattr: CULong,
    newattr: CULong,
    clrattrp: *mut CULong,
    setattrp: *mut CULong,
) {
    *clrattrp = oldattr & !newattr;
    *setattrp = newattr & !oldattr;
}

#[no_mangle]
pub extern "C" fn process_private_file_setattr_result(
    has_memobj: CInt,
    range_flags: CULong,
    memobj_flags: u32,
    setattr: CULong,
) -> CULong {
    if has_memobj != 0 && (range_flags & VR_PRIVATE) != 0 && (memobj_flags & MF_HUGETLBFS) == 0 {
        setattr & !PTATTR_WRITABLE
    } else {
        setattr
    }
}

#[no_mangle]
pub extern "C" fn process_remove_region_alignment_result(start: CULong, end: CULong) -> CInt {
    if (start & (PAGE_SIZE - 1)) != 0 || (end & (PAGE_SIZE - 1)) != 0 {
        -EINVAL
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_initial_result(
    has_range: CInt,
    range_start: CULong,
    addr: CULong,
) -> CInt {
    if has_range == 0 || range_start > addr {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_adjacent_result(
    range_end: CULong,
    has_next: CInt,
    next_start: CULong,
) -> CInt {
    if has_next == 0 || range_end != next_start {
        -EFAULT
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_access_permission_result(verify_type: CInt, flags: CULong) -> CInt {
    if (verify_type == VERIFY_WRITE && (flags & VR_PROT_WRITE) == 0)
        || (verify_type == VERIFY_READ && (flags & VR_PROT_READ) == 0)
    {
        -EACCES
    } else {
        0
    }
}

#[no_mangle]
pub extern "C" fn process_range_cache_hit_result(
    cache_start: CULong,
    cache_end: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    (cache_start <= start && cache_end >= end) as CInt
}

#[no_mangle]
pub extern "C" fn process_lookup_range_relation_result(
    start: CULong,
    end: CULong,
    range_start: CULong,
    range_end: CULong,
) -> CInt {
    if end <= range_start {
        -1
    } else if start >= range_end {
        1
    } else if start < range_start {
        -2
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_range_cache_replace_result(
    cache: *mut *mut c_void,
    count: CInt,
    from: *mut c_void,
    to: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || from.is_null() {
        return 0;
    }

    let mut replaced = 0;
    let mut i = 0;
    while i < count {
        let slot = unsafe { cache.add(i as usize) };
        if unsafe { *slot == from } {
            unsafe {
                *slot = to;
            }
            replaced += 1;
        }
        i += 1;
    }

    replaced
}

#[no_mangle]
pub unsafe extern "C" fn process_range_cache_store_result(
    cache: *mut *mut c_void,
    count: CInt,
    indexp: *mut CInt,
    match_range: *mut c_void,
) -> CInt {
    if cache.is_null() || count <= 0 || indexp.is_null() || match_range.is_null() {
        return -EINVAL;
    }

    let new_index = unsafe { (*indexp - 1 + count) % count };
    unsafe {
        *indexp = new_index;
        *cache.add(new_index as usize) = match_range;
    }
    new_index
}

#[no_mangle]
pub unsafe extern "C" fn process_range_end_commit_result(
    range: *mut VmRange,
    newend: CULong,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    unsafe {
        (*range).end = newend;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_range_flag_commit_result(
    range: *mut VmRange,
    newflag: CULong,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    unsafe {
        (*range).flag = newflag;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_range_stack_start_commit_result(
    range: *mut VmRange,
    fault_addr: CULong,
    pgshift: CInt,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    let new_start = if pgshift > 0 && (pgshift as usize) < CULong::BITS as usize {
        fault_addr & !((1u64 << pgshift) - 1)
    } else if pgshift == 0 {
        fault_addr & !(PAGE_SIZE - 1)
    } else {
        return 0;
    };

    unsafe {
        (*range).start = new_start;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_step_result(
    range_start: CULong,
    range_end: CULong,
    remove_start: CULong,
    remove_end: CULong,
    range_flags: CULong,
    private_data: CULong,
    split_startp: *mut CInt,
    split_endp: *mut CInt,
    ro_freedp: *mut CInt,
    xpmem_removep: *mut CInt,
) {
    if !split_startp.is_null() {
        unsafe {
            *split_startp = (range_start < remove_start) as CInt;
        }
    }
    if !split_endp.is_null() {
        unsafe {
            *split_endp = (remove_end < range_end) as CInt;
        }
    }
    if !ro_freedp.is_null() {
        unsafe {
            *ro_freedp = ((range_flags & VR_PROT_WRITE) == 0) as CInt;
        }
    }
    if !xpmem_removep.is_null() {
        unsafe {
            *xpmem_removep = (private_data != 0) as CInt;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_init_result(
    low: *const VmRange,
    high: *mut VmRange,
    addr: CULong,
) -> CInt {
    if low.is_null() || high.is_null() {
        return 0;
    }

    (*high).start = addr;
    (*high).straight_start = if (*low).straight_start != 0 {
        (*low)
            .straight_start
            .wrapping_add(addr.wrapping_sub((*low).start))
    } else {
        0
    };
    (*high).end = (*low).end;
    (*high).flag = (*low).flag;
    (*high).pgshift = (*low).pgshift;
    (*high).private_data = (*low).private_data;

    if !(*low).memobj.is_null() {
        (*high).memobj = (*low).memobj;
        (*high).objoff = (*low)
            .objoff
            .wrapping_add(addr.wrapping_sub((*low).start) as i64);
    } else {
        core::ptr::write_volatile(
            core::ptr::addr_of_mut!((*high).memobj),
            core::ptr::null_mut(),
        );
        core::ptr::write_volatile(core::ptr::addr_of_mut!((*high).objoff), 0);
    }

    1
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_commit_result(low: *mut VmRange, addr: CULong) {
    if !low.is_null() {
        (*low).end = addr;
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_prepare_result(
    surviving: *mut VmRange,
    merging: *const VmRange,
) -> CInt {
    if surviving.is_null() || merging.is_null() {
        return -EINVAL;
    }

    if (*surviving).end != (*merging).start
        || (*surviving).flag != (*merging).flag
        || (*surviving).memobj != (*merging).memobj
    {
        return -EINVAL;
    }

    if !(*surviving).memobj.is_null() {
        let len = (*surviving).end.wrapping_sub((*surviving).start);
        let endoff = (*surviving).objoff.wrapping_add(len as i64);
        if endoff != (*merging).objoff {
            return -EINVAL;
        }
    }

    (*surviving).end = (*merging).end;
    0
}

#[no_mangle]
pub extern "C" fn process_ref_release_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_address_space_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_address_space_should_run_free_cb_result(
    free_cb_addr: CULong,
) -> CInt {
    (free_cb_addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_create_cpu_allowed_result(cpu: CInt, num_processors: CInt) -> CInt {
    (cpu >= 0 && cpu < num_processors) as CInt
}

#[no_mangle]
pub extern "C" fn process_create_use_default_cpu_set_result(cpu_set_empty: CInt) -> CInt {
    (cpu_set_empty != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_pid_detach_result(
    pids: *mut CInt,
    nslots: CInt,
    pid: CInt,
) -> CInt {
    if pids.is_null() || nslots <= 0 {
        return -1;
    }

    let mut i = 0;
    while i < nslots {
        let slot = pids.add(i as usize);
        if *slot == pid {
            *slot = 0;
            return i;
        }
        i += 1;
    }

    -1
}

#[no_mangle]
pub extern "C" fn process_clone_shares_vm_result(clone_flags: CInt) -> CInt {
    ((clone_flags & CLONE_VM) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_clone_shares_sighand_result(clone_flags: CInt) -> CInt {
    ((clone_flags & CLONE_SIGHAND) != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_mckfd_should_dup_result(dup_cb_addr: CULong) -> CInt {
    (dup_cb_addr != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_copy_vm_thread_state_result(
    dst_vm: *mut c_void,
    src_vm: *const c_void,
    vdso_offset: CULong,
    vvar_offset: CULong,
    dst_thread: *mut c_void,
    src_thread: *const c_void,
    sigstack_offset: CULong,
    sigstack_size: usize,
) -> CInt {
    if dst_vm.is_null() || src_vm.is_null() || dst_thread.is_null() || src_thread.is_null() {
        return 0;
    }

    let dvm = dst_vm.cast::<u8>();
    let svm = src_vm.cast::<u8>();
    let dthread = dst_thread.cast::<u8>();
    let sthread = src_thread.cast::<u8>();

    *(dvm.add(vdso_offset as usize).cast::<*mut c_void>()) =
        *(svm.add(vdso_offset as usize).cast::<*mut c_void>());
    *(dvm.add(vvar_offset as usize).cast::<*mut c_void>()) =
        *(svm.add(vvar_offset as usize).cast::<*mut c_void>());
    copy_nonoverlapping(
        sthread.add(sigstack_offset as usize),
        dthread.add(sigstack_offset as usize),
        sigstack_size,
    );

    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_index_for_thread_result(
    tids: *const c_void,
    nr_tids: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
    thread_addr: CULong,
) -> CInt {
    if tids.is_null() || nr_tids <= 0 || entry_stride == 0 || thread_addr == 0 {
        return -1;
    }

    let base = tids.cast::<u8>();
    let stride = entry_stride as usize;
    let offset = thread_offset as usize;

    for index in 0..(nr_tids as usize) {
        let entry = base.add(index.saturating_mul(stride).saturating_add(offset));
        let stored = *(entry.cast::<CULong>());
        if stored == thread_addr {
            return index as CInt;
        }
    }

    -1
}

#[no_mangle]
pub extern "C" fn process_tid_index_found_result(index: CInt) -> CInt {
    (index >= 0) as CInt
}

fn checked_entry_addr(
    base: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    member_offset: CULong,
) -> Option<*mut u8> {
    if base.is_null() || index < 0 || entry_stride == 0 {
        return None;
    }

    let offset = (index as usize)
        .checked_mul(entry_stride as usize)?
        .checked_add(member_offset as usize)?;
    Some(base.cast::<u8>().wrapping_add(offset))
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_release_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    thread_offset: CULong,
) -> CInt {
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_replace_slot_result(
    tids: *mut c_void,
    index: CInt,
    entry_stride: CULong,
    tid_offset: CULong,
    thread_offset: CULong,
    new_tid: CInt,
) -> CInt {
    let Some(tid_slot) = checked_entry_addr(tids, index, entry_stride, tid_offset) else {
        return 0;
    };
    let Some(thread_slot) = checked_entry_addr(tids, index, entry_stride, thread_offset) else {
        return 0;
    };

    *(thread_slot.cast::<CULong>()) = 0;
    *(tid_slot.cast::<CInt>()) = new_tid;
    1
}

#[no_mangle]
pub extern "C" fn process_sigpending_cleanup_needed_result(list_empty: CInt) -> CInt {
    (list_empty == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_sigpending_pop_front_result(
    head: *mut AbiListHead,
    list_offset: CULong,
) -> *mut c_void {
    if head.is_null() {
        return core::ptr::null_mut();
    }

    let first = (*head).next;
    if first.is_null() || first == head {
        return core::ptr::null_mut();
    }

    let next = (*first).next;
    (*head).next = next;
    if !next.is_null() {
        (*next).prev = head;
    }
    (*first).next = LIST_POISON1 as *mut AbiListHead;
    (*first).prev = LIST_POISON2 as *mut AbiListHead;

    first.cast::<u8>().wrapping_sub(list_offset as usize).cast()
}

#[no_mangle]
pub unsafe extern "C" fn process_list_is_linked_result(entry: *const AbiListHead) -> CInt {
    if entry.is_null() {
        return 0;
    }

    let next = (*entry).next;
    (!next.is_null() && next != entry.cast_mut()) as CInt
}

unsafe fn list_detach(entry: *mut AbiListHead) -> bool {
    if entry.is_null() {
        return false;
    }

    let prev = (*entry).prev;
    let next = (*entry).next;
    if prev.is_null() || next.is_null() || next == entry {
        return false;
    }

    (*next).prev = prev;
    (*prev).next = next;
    (*entry).next = LIST_POISON1 as *mut AbiListHead;
    (*entry).prev = LIST_POISON2 as *mut AbiListHead;
    true
}

#[no_mangle]
pub unsafe extern "C" fn process_list_detach_result(entry: *mut AbiListHead) {
    let _ = list_detach(entry);
}

#[no_mangle]
pub unsafe extern "C" fn process_list_detach_counted_result(
    entry: *mut AbiListHead,
    lenp: *mut CULong,
) -> CInt {
    if lenp.is_null() || !list_detach(entry) {
        return 0;
    }

    *lenp = (*lenp).wrapping_sub(1);
    1
}

unsafe fn list_add_tail(entry: *mut AbiListHead, head: *mut AbiListHead) -> bool {
    if entry.is_null() || head.is_null() {
        return false;
    }

    let prev = (*head).prev;
    if prev.is_null() {
        return false;
    }

    (*entry).next = head;
    (*entry).prev = prev;
    (*prev).next = entry;
    (*head).prev = entry;
    true
}

#[no_mangle]
pub unsafe extern "C" fn process_list_add_tail_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) {
    let _ = list_add_tail(entry, head);
}

#[no_mangle]
pub unsafe extern "C" fn process_list_add_tail_counted_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
    lenp: *mut CULong,
) -> CInt {
    if lenp.is_null() || !list_add_tail(entry, head) {
        return 0;
    }

    *lenp = (*lenp).wrapping_add(1);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_list_move_tail_result(
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) -> CInt {
    if entry.is_null() || head.is_null() {
        return 0;
    }
    if !list_detach(entry) {
        return 0;
    }
    list_add_tail(entry, head) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_list_del_init_result(entry: *mut AbiListHead) -> CInt {
    if entry.is_null() {
        return 0;
    }

    let prev = (*entry).prev;
    let next = (*entry).next;
    if prev.is_null() || next.is_null() {
        return 0;
    }

    if next != entry {
        (*next).prev = prev;
        (*prev).next = next;
    }
    (*entry).next = entry;
    (*entry).prev = entry;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_child_reparent_result(
    child: *mut c_void,
    ppid_parent_offset: CULong,
    parent_offset: CULong,
    new_parent: *mut c_void,
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
    update_parent: CInt,
) -> CInt {
    if child.is_null() || new_parent.is_null() || entry.is_null() || head.is_null() {
        return 0;
    }

    let base = child.cast::<u8>();
    *(base
        .wrapping_add(ppid_parent_offset as usize)
        .cast::<*mut c_void>()) = new_parent;
    if update_parent != 0 {
        *(base
            .wrapping_add(parent_offset as usize)
            .cast::<*mut c_void>()) = new_parent;
    }

    process_list_move_tail_result(entry, head)
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_report_attach_result(
    thread: *mut c_void,
    termsig_offset: CULong,
    update_termsig: CInt,
    termsig: CInt,
    report_proc_offset: CULong,
    report_proc: *mut c_void,
    entry: *mut AbiListHead,
    head: *mut AbiListHead,
) -> CInt {
    if thread.is_null() || report_proc.is_null() || entry.is_null() || head.is_null() {
        return 0;
    }

    let base = thread.cast::<u8>();
    if update_termsig != 0 {
        *(base.wrapping_add(termsig_offset as usize).cast::<CInt>()) = termsig;
    }
    *(base
        .wrapping_add(report_proc_offset as usize)
        .cast::<*mut c_void>()) = report_proc;

    list_add_tail(entry, head) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_report_detach_result(
    thread: *mut c_void,
    report_proc_offset: CULong,
    report_proc: *mut c_void,
    entry: *mut AbiListHead,
) -> CInt {
    if thread.is_null() || entry.is_null() {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(report_proc_offset as usize)
        .cast::<*mut c_void>()) = report_proc;
    list_detach(entry) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_main_detach_reparent_result(
    process: *mut c_void,
    parent_offset: CULong,
    parent: *mut c_void,
    ptraced_entry: *mut AbiListHead,
    sibling_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
) -> CInt {
    if process.is_null()
        || parent.is_null()
        || ptraced_entry.is_null()
        || sibling_entry.is_null()
        || children_head.is_null()
    {
        return 0;
    }
    let _ = list_detach(ptraced_entry);
    if !list_add_tail(sibling_entry, children_head) {
        return 0;
    }

    *(process
        .cast::<u8>()
        .wrapping_add(parent_offset as usize)
        .cast::<*mut c_void>()) = parent;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_main_attach_reparent_result(
    process: *mut c_void,
    parent_offset: CULong,
    parent: *mut c_void,
    sibling_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
) -> CInt {
    if process.is_null() || parent.is_null() || sibling_entry.is_null() || children_head.is_null() {
        return 0;
    }
    if !list_add_tail(sibling_entry, children_head) {
        return 0;
    }

    *(process
        .cast::<u8>()
        .wrapping_add(parent_offset as usize)
        .cast::<*mut c_void>()) = parent;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_termsig_clear_result(
    thread: *mut c_void,
    termsig_offset: CULong,
    clear_termsig: CInt,
) -> CInt {
    if thread.is_null() || clear_termsig == 0 {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(termsig_offset as usize)
        .cast::<CInt>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_cleanup_result(
    thread: *mut c_void,
    ptrace_offset: CULong,
    saved_valid_offset: CULong,
    debugreg_offset: CULong,
) -> *mut c_void {
    if thread.is_null() {
        return core::ptr::null_mut();
    }

    let base = thread.cast::<u8>();
    let debugreg_slot = base
        .wrapping_add(debugreg_offset as usize)
        .cast::<*mut c_void>();
    let debugreg = *debugreg_slot;
    *(base.wrapping_add(ptrace_offset as usize).cast::<CInt>()) = 0;
    *(base
        .wrapping_add(saved_valid_offset as usize)
        .cast::<CInt>()) = 0;
    *debugreg_slot = core::ptr::null_mut();
    debugreg
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_saved_context_clear_result(
    thread: *mut c_void,
    saved_valid_offset: CULong,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    *(thread
        .cast::<u8>()
        .wrapping_add(saved_valid_offset as usize)
        .cast::<CInt>()) = 0;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_trace_syscall_update_result(
    thread: *mut c_void,
    ptrace_offset: CULong,
    trace_syscall: CInt,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    let ptrace = thread
        .cast::<u8>()
        .wrapping_add(ptrace_offset as usize)
        .cast::<CInt>();
    *ptrace &= !PT_TRACE_SYSCALL;
    if trace_syscall != 0 {
        *ptrace |= PT_TRACE_SYSCALL;
    }
    *ptrace
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_ptrace_pending_signal_take_result(
    thread: *mut c_void,
    sendsig_offset: CULong,
    recvsig_offset: CULong,
    source: CInt,
) -> *mut c_void {
    if thread.is_null() {
        return core::ptr::null_mut();
    }

    let base = thread.cast::<u8>();
    let slot = if source == PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG {
        base.wrapping_add(sendsig_offset as usize)
            .cast::<*mut c_void>()
    } else if source == PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG {
        base.wrapping_add(recvsig_offset as usize)
            .cast::<*mut c_void>()
    } else {
        return core::ptr::null_mut();
    };

    let pending = *slot;
    *slot = core::ptr::null_mut();
    pending
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_signal_flags_reap_result(
    thread: *mut c_void,
    signal_flags_offset: CULong,
    options: CInt,
    clear_mask: CInt,
) -> CInt {
    if thread.is_null() {
        return 0;
    }

    let signal_flags = thread
        .cast::<u8>()
        .wrapping_add(signal_flags_offset as usize)
        .cast::<CInt>();
    if (options & WNOWAIT) == 0 {
        *signal_flags &= !clear_mask;
    }
    *signal_flags
}

#[no_mangle]
pub unsafe extern "C" fn process_wait_exit_status_reap_result(
    object: *mut c_void,
    exit_status_offset: CULong,
    options: CInt,
) -> CInt {
    if object.is_null() {
        return 0;
    }

    let exit_status = object
        .cast::<u8>()
        .wrapping_add(exit_status_offset as usize)
        .cast::<CInt>();
    if (options & WNOWAIT) == 0 {
        *exit_status = 0;
    }
    *exit_status
}

#[no_mangle]
pub extern "C" fn process_optional_ptr_should_free_result(ptr_addr: CULong) -> CInt {
    (ptr_addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_hold_thread_warn_exited_result(status: CInt) -> CInt {
    (status == PS_EXITED) as CInt
}

#[no_mangle]
pub extern "C" fn process_sigcommon_release_should_destroy_result(dec_and_test: CInt) -> CInt {
    (dec_and_test != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_destroy_thread_tid_action_result(
    has_tids: CInt,
    is_main_thread: CInt,
    uti_state: CInt,
) -> CInt {
    if has_tids == 0 {
        PROCESS_TID_ACTION_NONE
    } else if uti_state == UTI_STATE_EPILOGUE {
        PROCESS_TID_ACTION_REPLACE
    } else if is_main_thread == 0 {
        PROCESS_TID_ACTION_RELEASE
    } else {
        PROCESS_TID_ACTION_NONE
    }
}

#[no_mangle]
pub extern "C" fn process_thread_should_free_pages_result(is_main_thread: CInt) -> CInt {
    (is_main_thread == 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_vm_should_run_free_cb_result(free_cb_addr: CULong) -> CInt {
    (free_cb_addr != 0) as CInt
}

#[no_mangle]
pub extern "C" fn process_release_mckfd_should_close_result(close_cb_addr: CULong) -> CInt {
    (close_cb_addr != 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_push_head_result(
    headp: *mut *mut c_void,
    entry: *mut c_void,
) -> CInt {
    if headp.is_null() || entry.is_null() {
        return 0;
    }

    let next_slot = entry.cast::<*mut c_void>();
    *next_slot = *headp;
    *headp = entry;
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_pop_head_result(headp: *mut *mut c_void) -> *mut c_void {
    if headp.is_null() {
        return core::ptr::null_mut();
    }

    let current = *headp;
    if current.is_null() {
        return core::ptr::null_mut();
    }

    let next_slot = current.cast::<*mut c_void>();
    *headp = *next_slot;
    *next_slot = core::ptr::null_mut();
    current
}
