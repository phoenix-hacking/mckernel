use core::{
    ffi::{c_char, c_void},
    mem::{offset_of, size_of, MaybeUninit},
    ptr::{copy_nonoverlapping, null, null_mut},
};

use crate::{
    abi::{
        CInt, CLong, CULong, CpuLocalVar, IkcScdPacket, IkcScdPacketTraditional, Memobj, Process,
        ProcessVm, ProcfsRead, SizeT, Thread, VmRange,
    },
    lock_helpers::McsRwlockNodeIrqsave,
    object_helpers::{
        procfs_backlog_result, procfs_bitmask_next_offset_result, procfs_comm_basename_result,
        procfs_comm_name_result, procfs_default_count_result, procfs_entry_kind_result,
        procfs_finish_request_result, procfs_lock_failed_action_result, procfs_lock_retry_result,
        procfs_locked_size_body_result, procfs_maps_body_result, procfs_mem_copy_body_result,
        procfs_osnum_match_result, procfs_pagemap_body_result, procfs_pagemap_range_result,
        procfs_pbuf_is_empty_result, procfs_pid_simple_entry_body_result,
        procfs_pointer_present_result, procfs_release_request_result, procfs_remote_count_result,
        procfs_remote_npages_result, procfs_root_entry_body_result, procfs_root_matched_result,
        procfs_stat_body_result, procfs_status_body_result, procfs_task_missing_terminal_result,
        procfs_thread_ctl_result, procfs_thread_stat_state_result, procfs_thread_tid_result,
        ProcfsBuffer, ProcfsStatBodyInput, ProcfsStatusBodyInput,
    },
};

const EIO: CInt = 5;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_PG_KERNEL: CInt = 0;
const PAGE_P2ALIGN: CInt = 0;
const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PROCFS_ENTRY_MCKERNEL: CInt = 1;
const PROCFS_ENTRY_STAT: CInt = 2;
const PROCFS_ENTRY_MEM: CInt = 4;
const PROCFS_ENTRY_MAPS: CInt = 5;
const PROCFS_ENTRY_PAGEMAP: CInt = 6;
const PROCFS_ENTRY_STATUS: CInt = 7;
const PROCFS_ENTRY_AUXV: CInt = 8;
const PROCFS_ENTRY_CMDLINE: CInt = 9;
const PROCFS_ENTRY_COMM: CInt = 10;
const PROCFS_LOCK_ACTION_BACKLOG: CInt = 1;
const PROCFS_RANGE_FIELD_START: CInt = 1;
const PROCFS_RANGE_FIELD_END: CInt = 2;
const PROCFS_RANGE_FIELD_FLAG: CInt = 3;
const SCD_MSG_PROCFS_TID_CREATE: CInt = 0x44;
const SCD_MSG_PROCFS_TID_DELETE: CInt = 0x45;
const BITMASKS_BUF_SIZE: SizeT = 2048;
const PROCESS_NUMA_MASK_BITS: CInt = 256;
const CPU_SETSIZE: CInt = 1024;

const FILE: &[u8] = b"kernel/rust/procfs.rs\0";
const MCOS_FMT: &[u8] = b"mcos%d/\0";
const PID_FMT: &[u8] = b"%d/\0";
const TASK_FMT: &[u8] = b"task/%d/\0";
const EXE: &[u8] = b"exe\0";
const NO_PROCFS_READ: &[u8] =
    b"ERROR: process_procfs_request: got a null procfs_read structure.\n\0";
const NULL_BUFFER: &[u8] = b"ERROR: process_procfs_request: got a null buffer.\n\0";
const OSNUM_MISMATCH: &[u8] =
    b"ERROR: process_procfs_request osnum mismatch (we are %d != requested %d)\n\0";
const NO_PID: &[u8] = b"process_procfs_request: no such pid %d\n\0";
const NO_TID: &[u8] = b"process_procfs_request: no such tid %d-%d\n\0";
const UNSUPPORTED_ROOT: &[u8] = b"unsupported procfs entry: %s\n\0";
const BITMASK_ALLOC_ERROR: &[u8] =
    b"process_procfs_request: error allocating /proc/self/status bitmaks buffer\n\0";
const UNSUPPORTED_TASK: &[u8] = b"unsupported procfs entry: %d/task/%d/%s\n\0";
const UNSUPPORTED_PID: &[u8] = b"unsupported procfs entry: %d/%s\n\0";

unsafe extern "C" {
    static num_processors: CInt;

    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut c_char,
        line: CInt,
    ) -> *mut c_void;
    fn _ihk_mc_free_pages(
        ptr: *mut c_void,
        npages: CInt,
        is_user: CInt,
        file: *mut c_char,
        line: CInt,
    );
    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn ihk_mc_get_osnum() -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar;
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut IkcScdPacket, flags: CInt) -> CInt;
    fn cpu_pause();
    fn virt_to_phys(ptr: *mut c_void) -> CULong;
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn ihk_mc_map_memory(os: *mut c_void, phys: CULong, size: CULong) -> CULong;
    fn ihk_mc_unmap_memory(os: *mut c_void, phys: CULong, size: CULong);
    fn ihk_mc_map_virtual(phys: CULong, npages: CULong, attr: CULong) -> *mut CULong;
    fn ihk_mc_unmap_virtual(ptr: *mut CULong, npages: CULong);
    fn page_fault_process_vm(vm: *mut ProcessVm, offset: *mut c_void, reason: CULong) -> CInt;
    fn ihk_mc_pt_virt_to_phys(
        page_table: *mut c_void,
        offset: *mut c_void,
        physp: *mut CULong,
    ) -> CInt;
    fn is_mckernel_memory(start: CULong, end: CULong) -> CInt;
    fn ihk_mc_pt_virt_to_pagemap(page_table: *mut c_void, addr: CULong) -> CULong;
    fn find_process(pid: CInt, lock: *mut McsRwlockNodeIrqsave) -> *mut Process;
    fn process_unlock(proc: *mut Process, lock: *mut McsRwlockNodeIrqsave);
    fn hold_thread(thread: *mut Thread) -> CInt;
    fn release_thread(thread: *mut Thread);
    fn hold_process(proc: *mut Process);
    fn release_process(proc: *mut Process);
    fn hold_process_vm(vm: *mut ProcessVm);
    fn release_process_vm(vm: *mut ProcessVm);
    fn lookup_process_memory_range(vm: *mut ProcessVm, start: CULong, end: CULong) -> *mut VmRange;
    fn next_process_memory_range(vm: *mut ProcessVm, range: *mut VmRange) -> *mut VmRange;
    fn __mcs_rwlock_reader_lock(lock: *mut c_void, node: *mut McsRwlockNodeIrqsave);
    fn __mcs_rwlock_reader_unlock(lock: *mut c_void, node: *mut McsRwlockNodeIrqsave);
    fn ihk_rwspinlock_read_trylock_noirq(lock: *mut c_void) -> CInt;
    fn ihk_rwspinlock_read_unlock_noirq(lock: *mut c_void);
    fn bitmap_scnprintf(buf: *mut c_char, len: u32, src: *const CULong, nbits: CInt) -> CInt;
    fn bitmap_scnlistprintf(buf: *mut c_char, len: u32, src: *const CULong, nbits: CInt) -> CInt;
    fn send_procfs_answer(packet: *mut IkcScdPacket, err: CInt);
    fn add_backlog(
        func: Option<unsafe extern "C" fn(*mut c_void) -> CInt>,
        arg: *mut c_void,
    ) -> CInt;
    fn sscanf(buf: *const c_char, fmt: *const c_char, ...) -> CInt;
    fn strchr(buf: *const c_char, c: CInt) -> *mut c_char;
}

#[inline(always)]
fn file_ptr() -> *mut c_char {
    FILE.as_ptr() as *mut c_char
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
unsafe fn kernel_alloc(size: SizeT, flags: CULong) -> *mut c_void {
    _kmalloc(size as CInt, flags as CInt, file_ptr(), line!() as CInt)
}

#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, file_ptr(), line!() as CInt);
}

unsafe extern "C" fn procfs_buf_page_alloc_bridge(npages: CInt, flags: CULong) -> *mut c_void {
    alloc_pages(npages, flags)
}

unsafe extern "C" fn procfs_buf_phys_bridge(pbuf: *mut ProcfsBuffer) -> CULong {
    virt_to_phys(pbuf.cast::<c_void>())
}

unsafe extern "C" fn buf_alloc(phys: *mut CULong, pos: CLong) -> *mut ProcfsBuffer {
    crate::object_helpers::procfs_buf_alloc_result(
        phys,
        pos,
        Some(procfs_buf_page_alloc_bridge),
        Some(procfs_buf_phys_bridge),
        IHK_MC_AP_NOWAIT,
    )
}

unsafe extern "C" fn procfs_buf_phys_to_virt_bridge(phys: CULong) -> *mut ProcfsBuffer {
    phys_to_virt(phys).cast::<ProcfsBuffer>()
}

unsafe extern "C" fn procfs_buf_free_page_bridge(pbuf: *mut ProcfsBuffer) {
    free_pages(pbuf.cast::<c_void>(), 1);
}

unsafe fn buf_free(phys: CULong) {
    let _ = crate::object_helpers::procfs_buf_release_result(
        phys,
        Some(procfs_buf_phys_to_virt_bridge),
        Some(procfs_buf_free_page_bridge),
    );
}

unsafe extern "C" fn procfs_thread_phys_bridge(addr: *mut c_void) -> CULong {
    virt_to_phys(addr)
}

unsafe extern "C" fn procfs_thread_send_bridge(
    channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    ihk_ikc_send(channel, packet, 0)
}

unsafe extern "C" fn procfs_thread_pause_bridge() {
    cpu_pause();
}

unsafe extern "C" fn procfs_buf_free_top_bridge(top: *mut ProcfsBuffer) {
    buf_free(virt_to_phys(top.cast::<c_void>()));
}

unsafe extern "C" fn procfs_buf_copy_bridge(
    dst: *mut c_void,
    src: *const c_void,
    len: SizeT,
) -> *mut c_void {
    copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), len);
    dst
}

unsafe extern "C" fn procfs_mem_page_fault_bridge(
    vm: *mut c_void,
    offset: CULong,
    reason: CULong,
) -> CInt {
    page_fault_process_vm(vm.cast::<ProcessVm>(), offset as *mut c_void, reason)
}

unsafe extern "C" fn procfs_mem_virt_to_phys_bridge(
    page_table: *mut c_void,
    offset: CULong,
    physp: *mut CULong,
) -> CInt {
    ihk_mc_pt_virt_to_phys(page_table, offset as *mut c_void, physp)
}

unsafe extern "C" fn procfs_mem_is_memory_bridge(start: CULong, end: CULong) -> CInt {
    is_mckernel_memory(start, end)
}

unsafe extern "C" fn procfs_mem_phys_to_virt_bridge(phys: CULong) -> *mut c_void {
    phys_to_virt(phys)
}

unsafe extern "C" fn procfs_pagemap_value_bridge(page_table: *mut c_void, addr: CULong) -> CULong {
    ihk_mc_pt_virt_to_pagemap(page_table, addr)
}

unsafe extern "C" fn procfs_range_ulong_bridge(range: *mut c_void, field: CInt) -> CULong {
    let range = range.cast::<VmRange>();
    if range.is_null() {
        return 0;
    }
    match field {
        PROCFS_RANGE_FIELD_START => (*range).start,
        PROCFS_RANGE_FIELD_END => (*range).end,
        PROCFS_RANGE_FIELD_FLAG => (*range).flag,
        _ => 0,
    }
}

unsafe extern "C" fn procfs_range_path_bridge(range: *mut c_void) -> *const u8 {
    let range = range.cast::<VmRange>();
    if range.is_null() || (*range).memobj.is_null() {
        return null();
    }
    let memobj = (*range).memobj.cast::<Memobj>();
    if (*memobj).path.is_null() {
        null()
    } else {
        (*memobj).path.cast::<u8>()
    }
}

unsafe extern "C" fn procfs_range_next_bridge(vm: *mut c_void, range: *mut c_void) -> *mut c_void {
    next_process_memory_range(vm.cast::<ProcessVm>(), range.cast::<VmRange>()).cast::<c_void>()
}

unsafe extern "C" fn procfs_backlog_alloc_bridge(size: CULong, flags: CULong) -> *mut c_void {
    kernel_alloc(size as SizeT, flags)
}

unsafe extern "C" fn procfs_backlog_copy_bridge(
    dst: *mut c_void,
    src: *mut IkcScdPacket,
    size: CULong,
) {
    copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), size as SizeT);
}

unsafe extern "C" fn procfs_backlog_add_bridge(
    backlog_fn: Option<unsafe extern "C" fn(*mut c_void) -> CInt>,
    arg: *mut c_void,
) -> CInt {
    add_backlog(backlog_fn, arg)
}

unsafe extern "C" fn procfs_backlog_free_bridge(arg: *mut c_void) {
    kernel_free(arg);
}

unsafe fn procfs_thread_ctl(thread: *mut Thread, msg: CInt) {
    let cpu = ihk_mc_get_processor_id();
    let local = get_cpu_local_var_result(cpu);
    let channel = if local.is_null() {
        null_mut()
    } else {
        (*local).ikc2linux
    };
    let mut packet = MaybeUninit::<IkcScdPacket>::uninit();
    let mut done = 0;

    let _ = procfs_thread_ctl_result(
        channel,
        packet.as_mut_ptr(),
        &mut done,
        msg,
        ihk_mc_get_osnum(),
        (*thread).cpu_id,
        (*(*thread).proc).pid,
        (*thread).tid,
        Some(procfs_thread_phys_bridge),
        Some(procfs_thread_send_bridge),
        Some(procfs_thread_pause_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn procfs_create_thread(thread: *mut Thread) {
    procfs_thread_ctl(thread, SCD_MSG_PROCFS_TID_CREATE);
}

#[no_mangle]
pub unsafe extern "C" fn procfs_delete_thread(thread: *mut Thread) {
    procfs_thread_ctl(thread, SCD_MSG_PROCFS_TID_DELETE);
}

unsafe fn procfs_backlog(_vm: *mut ProcessVm, rpacket: *mut IkcScdPacket) -> CInt {
    procfs_backlog_result(
        rpacket,
        Some(do_procfs_backlog),
        Some(procfs_backlog_alloc_bridge),
        Some(procfs_backlog_copy_bridge),
        Some(procfs_backlog_add_bridge),
        Some(procfs_backlog_free_bridge),
        size_of::<IkcScdPacket>() as CULong,
        IHK_MC_AP_NOWAIT,
    )
}

unsafe fn thread_from_siblings(node: *mut crate::abi::AbiListHead) -> *mut Thread {
    (node as *mut u8)
        .sub(offset_of!(Thread, siblings_list))
        .cast::<Thread>()
}

unsafe fn count_threads(proc: *mut Process) -> CInt {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut count = 0;

    __mcs_rwlock_reader_lock(
        (&raw mut (*proc).threads_lock).cast::<c_void>(),
        lock.as_mut_ptr(),
    );
    let head = &raw mut (*proc).threads_list;
    let mut node = (*head).next;
    while node != head {
        count += 1;
        node = (*node).next;
    }
    __mcs_rwlock_reader_unlock(
        (&raw mut (*proc).threads_lock).cast::<c_void>(),
        lock.as_mut_ptr(),
    );
    count
}

unsafe fn find_proc_thread(proc: *mut Process, tid: CInt) -> (*mut Thread, *mut Thread) {
    let mut tlock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut first: *mut Thread = null_mut();
    let mut found: *mut Thread = null_mut();

    __mcs_rwlock_reader_lock(
        (&raw mut (*proc).threads_lock).cast::<c_void>(),
        tlock.as_mut_ptr(),
    );
    let head = &raw mut (*proc).threads_list;
    let mut node = (*head).next;
    while node != head {
        let thread = thread_from_siblings(node);
        if (*thread).tid == tid {
            found = thread;
            break;
        }
        if first.is_null() {
            first = thread;
        }
        node = (*node).next;
    }
    if !found.is_null() {}
    __mcs_rwlock_reader_unlock(
        (&raw mut (*proc).threads_lock).cast::<c_void>(),
        tlock.as_mut_ptr(),
    );

    (found, first)
}

unsafe fn lock_failed(
    result: *mut CInt,
    vm: *mut ProcessVm,
    rpacket: *mut IkcScdPacket,
    errp: *mut CInt,
) -> CInt {
    if procfs_lock_failed_action_result(result as CULong) == PROCFS_LOCK_ACTION_BACKLOG {
        let error = procfs_backlog(vm, rpacket);
        if error != 0 {
            *errp = error;
            return -1;
        }
    } else if !result.is_null() {
        *result = procfs_lock_retry_result();
    }
    1
}

unsafe fn process_procfs_request_inner(rpacket: *mut IkcScdPacket, result: *mut CInt) -> CInt {
    let rpacket_body = (&raw mut (*rpacket).body).cast::<IkcScdPacketTraditional>();
    let rarg = (*rpacket_body).arg;
    let mut pbuf_phys: CULong = 0;
    let mut thread: *mut Thread = null_mut();
    let mut proc: *mut Process = null_mut();
    let mut vm: *mut ProcessVm = null_mut();
    let r: *mut ProcfsRead;
    let osnum = ihk_mc_get_osnum();
    let mut rosnum: CInt = 0;
    let mut pid: CInt = 0;
    let tid: CInt;
    let mut ans: CInt = -EIO;
    let eof: CInt = 0;
    let buf: *mut c_void;
    let mut p: *mut c_char = null_mut();
    let mut vbuf: *mut c_void = null_mut();
    let mut tmp: *mut c_void = null_mut();
    let mut proc_lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut count: CInt;
    let mut npages: CInt = 0;
    let mut readwrite: CInt = 0;
    let mut err: CInt = -EIO;
    let mut buf_top: *mut ProcfsBuffer = null_mut();
    let mut buf_cur: *mut ProcfsBuffer = null_mut();

    let parg = ihk_mc_map_memory(null_mut(), rarg, size_of::<ProcfsRead>() as CULong);
    r = ihk_mc_map_virtual(parg, 1, PTATTR_WRITABLE | PTATTR_ACTIVE).cast::<ProcfsRead>();
    if r.is_null() {
        ihk_mc_unmap_memory(null_mut(), parg, size_of::<ProcfsRead>() as CULong);
        kprintf(NO_PROCFS_READ.as_ptr().cast());
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if crate::object_helpers::procfs_is_release_result((*rpacket).msg) != 0 {
        err = procfs_release_request_result(
            r,
            Some(procfs_buf_phys_to_virt_bridge),
            Some(procfs_buf_free_page_bridge),
        );
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if procfs_pbuf_is_empty_result((*r).pbuf) != 0 {
        tmp = alloc_pages(1, IHK_MC_AP_NOWAIT);
        if tmp.is_null() {
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        buf = tmp;
        count = procfs_default_count_result();
    } else {
        pbuf_phys = ihk_mc_map_memory(null_mut(), (*r).pbuf, (*r).count as CULong);
        count = procfs_remote_count_result(pbuf_phys, (*r).count);
        npages = procfs_remote_npages_result(count);
        vbuf = ihk_mc_map_virtual(pbuf_phys, npages as CULong, PTATTR_WRITABLE | PTATTR_ACTIVE)
            .cast::<c_void>();
        if vbuf.is_null() {
            ihk_mc_unmap_memory(null_mut(), pbuf_phys, (*r).count as CULong);
            kprintf(NULL_BUFFER.as_ptr().cast());
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        buf = vbuf;
        readwrite = (*r).readwrite;
        count = (*r).count;
    }

    let offset = (*r).offset;
    let ret = sscanf((*r).fname.as_ptr(), MCOS_FMT.as_ptr().cast(), &mut rosnum);
    if procfs_root_matched_result(ret) != 0 {
        if procfs_osnum_match_result(osnum, rosnum) == 0 {
            kprintf(OSNUM_MISMATCH.as_ptr().cast(), osnum, rosnum);
            goto_end(r, ans, eof, buf_top, &mut err);
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
    } else {
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    let slash = strchr((*r).fname.as_ptr(), b'/' as CInt);
    if !slash.is_null() {
        p = slash.add(1);
    }

    let ret = sscanf(p, PID_FMT.as_ptr().cast(), &mut pid);
    if ret == 1 {
        let mut parsed_tid = 0;
        let task_matches: CInt;
        proc = find_process(pid, proc_lock.as_mut_ptr());
        if proc.is_null() {
            kprintf(NO_PID.as_ptr().cast(), pid);
            goto_end(r, ans, eof, buf_top, &mut err);
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        let first_slash = strchr(p, b'/' as CInt);
        if !first_slash.is_null() {
            p = first_slash.add(1);
        }
        task_matches = sscanf(p, TASK_FMT.as_ptr().cast(), &mut parsed_tid);
        if task_matches == 1 {
            let slash1 = strchr(p, b'/' as CInt);
            if !slash1.is_null() {
                let slash2 = strchr(slash1.add(1), b'/' as CInt);
                if !slash2.is_null() {
                    p = slash2.add(1);
                }
            }
        }
        tid = procfs_thread_tid_result(task_matches, parsed_tid, pid);

        let (found, fallback) = find_proc_thread(proc, tid);
        if found.is_null() {
            kprintf(NO_TID.as_ptr().cast(), pid, tid);
            if procfs_task_missing_terminal_result(task_matches) != 0 {
                process_unlock(proc, proc_lock.as_mut_ptr());
                goto_end(r, ans, eof, buf_top, &mut err);
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            thread = fallback;
        } else {
            thread = found;
        }
        if !thread.is_null() {
            let _ = hold_thread(thread);
        }

        hold_process(proc);
        vm = (*proc).vm;
        if procfs_pointer_present_result(vm as CULong) != 0 {
            hold_process_vm(vm);
        }
        process_unlock(proc, proc_lock.as_mut_ptr());
    } else {
        let kind = procfs_entry_kind_result(p.cast::<u8>());
        match kind {
            PROCFS_ENTRY_MCKERNEL => {
                let ret = procfs_root_entry_body_result(
                    PROCFS_ENTRY_MCKERNEL,
                    concat!(env!("MCKERNEL_RUST_VERSION"), "\0").as_ptr(),
                    concat!(env!("MCKERNEL_RUST_BUILDID"), "\0").as_ptr(),
                    0,
                    count,
                    &mut buf_top,
                    &mut buf_cur,
                    Some(buf_alloc),
                    Some(procfs_buf_free_top_bridge),
                    Some(procfs_buf_copy_bridge),
                );
                if ret < 0 {
                    err = ret;
                    goto_cleanup(
                        rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                    );
                    return err;
                }
                ans = 0;
                goto_end(r, ans, eof, buf_top, &mut err);
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            PROCFS_ENTRY_STAT => {
                let ret = procfs_root_entry_body_result(
                    PROCFS_ENTRY_STAT,
                    null(),
                    null(),
                    num_processors,
                    count,
                    &mut buf_top,
                    &mut buf_cur,
                    Some(buf_alloc),
                    Some(procfs_buf_free_top_bridge),
                    Some(procfs_buf_copy_bridge),
                );
                if ret < 0 {
                    err = ret;
                    goto_cleanup(
                        rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                    );
                    return err;
                }
                ans = 0;
                goto_end(r, ans, eof, buf_top, &mut err);
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            _ => {
                kprintf(UNSUPPORTED_ROOT.as_ptr().cast(), p);
                goto_end(r, ans, eof, buf_top, &mut err);
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
        }
    }

    let kind = procfs_entry_kind_result(p.cast::<u8>());
    if kind == PROCFS_ENTRY_MEM {
        let pt = (*(*vm).address_space).page_table;
        ans = procfs_mem_copy_body_result(
            vm.cast::<c_void>(),
            pt,
            buf,
            offset,
            (*r).count as CULong,
            readwrite,
            Some(procfs_mem_page_fault_bridge),
            Some(procfs_mem_virt_to_phys_bridge),
            Some(procfs_mem_is_memory_bridge),
            Some(procfs_mem_phys_to_virt_bridge),
            Some(procfs_buf_copy_bridge),
        );
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if kind == PROCFS_ENTRY_MAPS {
        if ihk_rwspinlock_read_trylock_noirq((&raw mut (*vm).memory_range_lock).cast()) == 0 {
            let action = lock_failed(result, vm, rpacket, &mut err);
            if action < 0 {
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        let range = lookup_process_memory_range(vm, 0, CULong::MAX);
        ans = procfs_maps_body_result(
            vm.cast::<c_void>(),
            range.cast::<c_void>(),
            (*vm).vdso_addr as CULong,
            (*vm).vvar_addr as CULong,
            (*vm).region.brk_start,
            (*vm).region.brk_end_allocated,
            count,
            &mut buf_top,
            &mut buf_cur,
            Some(buf_alloc),
            Some(procfs_buf_free_top_bridge),
            Some(procfs_buf_copy_bridge),
            Some(procfs_range_ulong_bridge),
            Some(procfs_range_path_bridge),
            Some(procfs_range_next_bridge),
        );
        ihk_rwspinlock_read_unlock_noirq((&raw mut (*vm).memory_range_lock).cast());
        if ans < 0 {
            err = ans;
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        ans = 0;
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if kind == PROCFS_ENTRY_PAGEMAP {
        let mut start: CULong = 0;
        let mut end: CULong = 0;
        let pt = (*(*(*proc).vm).address_space).page_table;
        ans = procfs_pagemap_range_result(offset, count, &mut start, &mut end);
        if ans != 0 {
            goto_end(r, ans, eof, buf_top, &mut err);
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        if ihk_rwspinlock_read_trylock_noirq((&raw mut (*vm).memory_range_lock).cast()) == 0 {
            let action = lock_failed(result, vm, rpacket, &mut err);
            if action < 0 {
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        ans = procfs_pagemap_body_result(
            pt,
            buf.cast::<CULong>(),
            start,
            end,
            count,
            Some(procfs_pagemap_value_bridge),
        );
        ihk_rwspinlock_read_unlock_noirq((&raw mut (*vm).memory_range_lock).cast());
        if ans < 0 {
            err = ans;
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if kind == PROCFS_ENTRY_STATUS {
        let bitmasks = kernel_alloc(BITMASKS_BUF_SIZE, IHK_MC_AP_NOWAIT).cast::<c_char>();
        if bitmasks.is_null() {
            kprintf(BITMASK_ALLOC_ERROR.as_ptr().cast());
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        if ihk_rwspinlock_read_trylock_noirq((&raw mut (*vm).memory_range_lock).cast()) == 0 {
            let action = lock_failed(result, vm, rpacket, &mut err);
            kernel_free(bitmasks.cast());
            if action < 0 {
                goto_cleanup(
                    rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
                );
                return err;
            }
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        let range = lookup_process_memory_range(vm, 0, CULong::MAX);
        let lockedsize = procfs_locked_size_body_result(
            vm.cast::<c_void>(),
            range.cast::<c_void>(),
            Some(procfs_range_ulong_bridge),
            Some(procfs_range_next_bridge),
        );
        ihk_rwspinlock_read_unlock_noirq((&raw mut (*vm).memory_range_lock).cast());

        let mut bitmasks_offset: CInt = 0;
        let cpu_bitmask = bitmasks.add(bitmasks_offset as usize);
        bitmasks_offset = procfs_bitmask_next_offset_result(
            bitmasks_offset,
            bitmap_scnprintf(
                cpu_bitmask,
                (BITMASKS_BUF_SIZE - bitmasks_offset as SizeT) as u32,
                (*thread).cpu_set.bits.as_ptr(),
                num_processors,
            ),
        );
        let cpu_list = bitmasks.add(bitmasks_offset as usize);
        bitmasks_offset = procfs_bitmask_next_offset_result(
            bitmasks_offset,
            bitmap_scnlistprintf(
                cpu_list,
                (BITMASKS_BUF_SIZE - bitmasks_offset as SizeT) as u32,
                (*thread).cpu_set.bits.as_ptr(),
                CPU_SETSIZE,
            ),
        );
        let numa_bitmask = bitmasks.add(bitmasks_offset as usize);
        bitmasks_offset = procfs_bitmask_next_offset_result(
            bitmasks_offset,
            bitmap_scnprintf(
                numa_bitmask,
                (BITMASKS_BUF_SIZE - bitmasks_offset as SizeT) as u32,
                (*(*proc).vm).numa_mask.as_ptr(),
                PROCESS_NUMA_MASK_BITS,
            ),
        );
        let numa_list = bitmasks.add(bitmasks_offset as usize);
        let _ = procfs_bitmask_next_offset_result(
            bitmasks_offset,
            bitmap_scnlistprintf(
                numa_list,
                (BITMASKS_BUF_SIZE - bitmasks_offset as SizeT) as u32,
                (*(*proc).vm).numa_mask.as_ptr(),
                PROCESS_NUMA_MASK_BITS,
            ),
        );
        let input = ProcfsStatusBodyInput {
            pid: (*proc).pid,
            ruid: (*proc).ruid,
            euid: (*proc).euid,
            suid: (*proc).suid,
            fsuid: (*proc).fsuid,
            rgid: (*proc).rgid,
            egid: (*proc).egid,
            sgid: (*proc).sgid,
            fsgid: (*proc).fsgid,
            status: (*proc).status,
            nr_threads: count_threads(proc),
            lockedsize,
            cpu_bitmask: cpu_bitmask.cast::<u8>(),
            cpu_list: cpu_list.cast::<u8>(),
            numa_bitmask: numa_bitmask.cast::<u8>(),
            numa_list: numa_list.cast::<u8>(),
        };
        let ret = procfs_status_body_result(
            &input,
            count,
            &mut buf_top,
            &mut buf_cur,
            Some(buf_alloc),
            Some(procfs_buf_free_top_bridge),
            Some(procfs_buf_copy_bridge),
        );
        kernel_free(bitmasks.cast());
        if ret < 0 {
            err = ret;
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        ans = 0;
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if kind == PROCFS_ENTRY_AUXV || kind == PROCFS_ENTRY_CMDLINE || kind == PROCFS_ENTRY_COMM {
        let ret = procfs_pid_simple_entry_body_result(
            kind,
            (*proc).saved_auxv.as_ptr().cast::<c_void>(),
            (*proc).saved_cmdline.cast::<u8>(),
            (*proc).saved_cmdline_len as u32,
            EXE.as_ptr(),
            &mut buf_top,
            &mut buf_cur,
            Some(buf_alloc),
            Some(procfs_buf_free_top_bridge),
            Some(procfs_buf_copy_bridge),
        );
        if ret < 0 {
            err = ret;
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        ans = 0;
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if kind == PROCFS_ENTRY_STAT {
        let basename = procfs_comm_basename_result((*proc).saved_cmdline as CULong);
        let comm = procfs_comm_name_result(EXE.as_ptr() as CULong, basename) as *const u8;
        let state = procfs_thread_stat_state_result((*thread).status, (*thread).in_syscall_offload);
        let parent = (*(*thread).proc).ppid_parent;
        let input = ProcfsStatBodyInput {
            tid: (*thread).tid,
            comm,
            state,
            ppid: if parent.is_null() { 0 } else { (*parent).pid },
            pid: (*(*thread).proc).pid,
            nr_threads: count_threads(proc),
            cpu_id: (*thread).cpu_id,
        };
        let ret = procfs_stat_body_result(
            &input,
            count,
            &mut buf_top,
            &mut buf_cur,
            Some(buf_alloc),
            Some(procfs_buf_free_top_bridge),
            Some(procfs_buf_copy_bridge),
        );
        if ret < 0 {
            err = ret;
            goto_cleanup(
                rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
            );
            return err;
        }
        ans = 0;
        goto_end(r, ans, eof, buf_top, &mut err);
        goto_cleanup(
            rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
        );
        return err;
    }

    if !thread.is_null() {
        kprintf(UNSUPPORTED_TASK.as_ptr().cast(), pid, tid, p);
    } else {
        kprintf(UNSUPPORTED_PID.as_ptr().cast(), pid, p);
    }
    goto_end(r, ans, eof, buf_top, &mut err);
    goto_cleanup(
        rpacket, err, vbuf, npages, pbuf_phys, r, parg, tmp, proc, thread, vm,
    );
    err
}

unsafe fn goto_end(
    r: *mut ProcfsRead,
    ans: CInt,
    eof: CInt,
    buf_top: *mut ProcfsBuffer,
    err: *mut CInt,
) {
    *err = procfs_finish_request_result(r, ans, eof, buf_top, Some(procfs_buf_phys_bridge));
}

#[allow(clippy::too_many_arguments)]
unsafe fn goto_cleanup(
    rpacket: *mut IkcScdPacket,
    err: CInt,
    vbuf: *mut c_void,
    npages: CInt,
    pbuf_phys: CULong,
    r: *mut ProcfsRead,
    parg: CULong,
    tmp: *mut c_void,
    proc: *mut Process,
    thread: *mut Thread,
    vm: *mut ProcessVm,
) {
    send_procfs_answer(rpacket, err);
    if !vbuf.is_null() {
        ihk_mc_unmap_virtual(vbuf.cast::<CULong>(), npages as CULong);
        if !r.is_null() {
            ihk_mc_unmap_memory(null_mut(), pbuf_phys, (*r).count as CULong);
        }
    }
    if !r.is_null() {
        ihk_mc_unmap_virtual(r.cast::<CULong>(), 1);
        ihk_mc_unmap_memory(null_mut(), parg, size_of::<ProcfsRead>() as CULong);
    }
    if !tmp.is_null() {
        free_pages(tmp, 1);
    }
    if !proc.is_null() {
        release_process(proc);
    }
    if !thread.is_null() {
        release_thread(thread);
    }
    if !vm.is_null() {
        release_process_vm(vm);
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_procfs_request(rpacket: *mut IkcScdPacket) -> CInt {
    process_procfs_request_inner(rpacket, null_mut())
}

unsafe extern "C" fn do_procfs_backlog(arg: *mut c_void) -> CInt {
    let rpacket = arg.cast::<IkcScdPacket>();
    let mut result = 0;

    let ret = process_procfs_request_inner(rpacket, &mut result);
    if result == 0 {
        kernel_free(arg);
    }
    ret
}
