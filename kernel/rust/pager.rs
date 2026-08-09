use core::{
    ffi::c_void,
    mem::{size_of, zeroed},
    ptr::{null_mut, write_bytes},
};

use crate::{
    abi::{
        CInt, CLong, CULong, CpuLocalVar, ProcessVm, SizeT, Thread, VmRange, VmRegions,
        X86UserContext,
    },
    object_helpers::{
        pager_addrpair_size_result, pager_arealist_count_add_result,
        pager_arealist_tail_room_result, pager_arealist_write_result,
        pager_copy_fault_error_result, pager_copy_fault_retry_result, pager_copy_size_error_result,
        pager_fault_addr_result, pager_fd_valid_result, pager_file_pos_result,
        pager_io_short_result, pager_linux_io_advance_result, pager_linux_io_complete_result,
        pager_linux_io_first_result, pager_linux_io_next_buf_result,
        pager_linux_io_remaining_result, pager_linux_io_retry_result, pager_linux_io_stop_result,
        pager_mlock_container_empty_result, pager_mlock_more_result, pager_mlock_needs_next_result,
        pager_mlock_next_count_result, pager_mlock_next_start_result,
        pager_mlock_reset_count_result, pager_myalloc_fits_result,
        pager_myalloc_next_alloced_result, pager_pagein_data_pos_result, pager_pageout_args_result,
        pager_range_locked_result, pager_read_chunk_size_result, pager_should_unlink_swap_result,
        pager_skip_anon_range_result, pager_skip_physical_removal_result,
    },
};

const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;

const PAGE_SIZE: SizeT = 1 << 12;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;

const O_RDONLY: CInt = 0o0000000;
const O_RDWR: CInt = 0o0000002;
const O_CREAT: CInt = 0o0000100;
const O_TRUNC: CInt = 0o0001000;
const SEEK_SET: CInt = 0;
const SEEK_CUR: CInt = 1;

const NR_READ: CInt = 0;
const NR_WRITE: CInt = 1;
const NR_CLOSE: CInt = 3;
const NR_LSEEK: CInt = 8;
const NR_MMAP: CInt = 9;
const NR_MUNMAP: CInt = 11;
const NR_MLOCK: CInt = 149;
const NR_MUNLOCK: CInt = 150;
const NR_OPENAT: CInt = 257;
const NR_UNLINKAT: CInt = 263;

const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_POPULATE: CULong = 1 << 30;
const PAGER_REQ_MLOCK_LIST: CULong = 0x0008;

const AT_FDCWD: CLong = -100;
const UDATA_BUFSIZE: SizeT = PAGE_SIZE;
const MLOCKADDRS_SIZE: usize = 128;
const SWAP_HLEN: SizeT = 16;
const MCKERNEL_SWAP: [u8; SWAP_HLEN] = *b"McKernel swap\0\0\0";
const MCKERNEL_SWAP_VERSION: [u8; SWAP_HLEN] = *b"1.8.0\0\0\0\0\0\0\0\0\0\0\0";

const FILE: &[u8] = b"kernel/rust/pager.rs\0";
const REGION_FMT: &[u8] = b"\t%016lx:%016lx (%lx)\n\0";
const REGION_HEAD_FMT: &[u8] = b"%s:\n\0";
const AFTER_PAGEIN: &[u8] = b"after pagin\0";
const PAGEIN_OPEN_FMT: &[u8] = b"do_pagein: Cannot open file: %s\n\0";
const PAGEIN_READ_ERR_FMT: &[u8] = b"pagein: read error: return(%lx) size(%lx)\n\0";
const PAGEOUT_ALLOC_FMT: &[u8] = b"do_pageout: Cannot allocate working memory in kmalloc\n\0";
const PAGEOUT_PIN_FMT: &[u8] = b"do_pageout: Cannot pin buf (%p) down\n\0";
const PAGEOUT_USER_AREA_FMT: &[u8] =
    b"do_pageout: user buffer area is needed more than %d byte\n\0";
const PAGEOUT_OPEN_FMT: &[u8] = b"do_pageout: Cannot open/create file: %s\n\0";
const PAGEOUT_START_FMT: &[u8] = b"do_pageout: start(%ld) range->end(%ld)\n\0";
const SWAP_LABEL: &[u8] = b"SWAP\0";
const MLOCK_LABEL: &[u8] = b"MLOCK\0";
const AREALIST_HEAD_FMT: &[u8] = b"%s: %d\n\0";
const AREALIST_ENTRY_FMT: &[u8] = b"\t%p -- %p\n\0";
const CANNOT_GET_PHYS_FMT: &[u8] = b"Cannot get phys\n\0";
const PAGEOUT_FILE_ENT_FMT: &[u8] =
    b"do_pageout: ERROR file ent(%d) != list ent(%d) in swap_area\n\0";
const SKIP_REMOVAL_FMT: &[u8] = b"skipping physical memory removal\n\0";
const REMOVE_PHYS_FMT: &[u8] = b"removing physical memory\n\0";
const FREE_RANGE_ERR_FMT: &[u8] = b"ihk_mc_pt_clear_range returns: %d\n\0";
const MUNMAP_ERR_FMT: &[u8] = b"do_pageout: Cannot munmap: %lx len(%lx)\n\0";
const PAGEOUT_WRITE_ERR_FMT: &[u8] = b"do_pageout: write error: %d\n\0";
const PAGEOUT_NOMEM_FMT: &[u8] = b"do_pageout: cannot allocate working memory\n\0";

#[repr(C)]
#[derive(Clone, Copy)]
struct AddrPair {
    start: CULong,
    end: CULong,
    flag: CULong,
}

#[repr(C)]
struct AreaEnt {
    next: *mut AreaEnt,
    count: CInt,
    pair: [AddrPair; MLOCKADDRS_SIZE],
}

#[repr(C)]
struct AreaList {
    head: *mut AreaEnt,
    tail: *mut AreaEnt,
    count: CInt,
}

#[repr(C)]
struct MlockCntnr {
    from: *mut AreaEnt,
    ccount: CInt,
    cur: *mut AreaEnt,
}

#[repr(C)]
struct SwapHeader {
    magic: [u8; SWAP_HLEN],
    version: [u8; SWAP_HLEN],
    count_sarea: u32,
    count_marea: u32,
}

#[repr(C)]
struct SwapAreaInfo {
    start: CULong,
    end: CULong,
    pos: CULong,
    flag: CULong,
}

#[repr(C)]
pub struct SwapInfo {
    swphdr: *mut SwapHeader,
    swap_info: *mut SwapAreaInfo,
    mlock_info: *mut SwapAreaInfo,
    swap_area: AreaList,
    mlock_area: AreaList,
    mlock_container: MlockCntnr,
    swapfname: *mut i8,
    udata_buf: *mut i8,
    user_buf: *mut c_void,
    ubuf_size: SizeT,
    ubuf_alloced: SizeT,
}

unsafe extern "C" {
    fn _kmalloc(size: CInt, flags: CInt, file: *mut i8, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut i8, line: CInt);
    fn copy_from_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    fn copy_to_user(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    fn strlen(s: *const i8) -> SizeT;
    fn strlen_user(s: *const i8) -> CInt;
    fn strcpy_from_user(dst: *mut i8, src: *const i8) -> CInt;
    fn sys_mlock(n: CInt, ctx: *mut X86UserContext) -> CLong;
    fn sys_munlock(n: CInt, ctx: *mut X86UserContext) -> CLong;
    fn syscall_generic_forwarding(n: CInt, ctx: *mut X86UserContext) -> CLong;
    fn ihk_mc_pt_virt_to_phys_size(
        pt: *mut c_void,
        virt: *mut c_void,
        phys: *mut CULong,
        psize: *mut CULong,
    ) -> CInt;
    fn ihk_mc_pt_virt_to_phys(pt: *mut c_void, virt: *mut c_void, phys: *mut CULong) -> CInt;
    fn page_fault_process_vm(vm: *mut ProcessVm, addr: *mut c_void, reason: CULong) -> CInt;
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn lookup_process_memory_range(vm: *mut ProcessVm, start: CULong, end: CULong) -> *mut VmRange;
    fn next_process_memory_range(vm: *mut ProcessVm, range: *mut VmRange) -> *mut VmRange;
    fn ihk_mc_pt_free_range(
        pt: *mut c_void,
        vm: *mut ProcessVm,
        start: *mut c_void,
        end: *mut c_void,
        opt: *mut c_void,
    ) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar;
    fn kprintf(format: *const i8, ...) -> CInt;
}

#[inline(always)]
fn file_ptr() -> *mut i8 {
    FILE.as_ptr() as *mut i8
}

#[inline(always)]
unsafe fn kernel_alloc(size: SizeT) -> *mut c_void {
    _kmalloc(
        size as CInt,
        IHK_MC_AP_NOWAIT as CInt,
        file_ptr(),
        line!() as CInt,
    )
}

#[inline(always)]
unsafe fn kernel_alloc_i(size: CInt) -> *mut c_void {
    _kmalloc(size, IHK_MC_AP_NOWAIT as CInt, file_ptr(), line!() as CInt)
}

#[inline(always)]
unsafe fn kernel_free(ptr: *mut c_void) {
    _kfree(ptr, file_ptr(), line!() as CInt);
}

#[inline(always)]
unsafe fn current_thread() -> *mut Thread {
    let cpu = ihk_mc_get_processor_id();
    let cpu_local = get_cpu_local_var_result(cpu);
    if cpu_local.is_null() {
        null_mut()
    } else {
        (*cpu_local).current
    }
}

unsafe fn area_print(_region: *mut VmRegions) {}

#[no_mangle]
pub unsafe extern "C" fn myalloc_finalize(si: *mut SwapInfo) {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = (*si).user_buf as CULong;
    ctx.gpr.rsi = (*si).ubuf_size as CULong;
    let _ = sys_munlock(NR_MUNLOCK, &raw mut ctx);
}

#[no_mangle]
pub unsafe extern "C" fn myalloc(si: *mut SwapInfo, sz: SizeT) -> *mut c_void {
    let mut p = null_mut();

    if pager_myalloc_fits_result((*si).ubuf_alloced, sz, (*si).ubuf_size) != 0 {
        p = (*si)
            .user_buf
            .cast::<u8>()
            .add((*si).ubuf_alloced)
            .cast::<c_void>();
        (*si).ubuf_alloced = pager_myalloc_next_alloced_result((*si).ubuf_alloced, sz);
    }
    p
}

#[no_mangle]
pub unsafe extern "C" fn myfree(_p: *mut c_void) {}

unsafe fn myalloc_init(si: *mut SwapInfo, p: *mut c_void, sz: SizeT) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = p as CULong;
    ctx.gpr.rsi = sz as CULong;
    let cc = sys_mlock(NR_MLOCK, &raw mut ctx);
    if cc < 0 {
        return cc as CInt;
    }
    (*si).user_buf = p;
    (*si).ubuf_size = sz;
    (*si).ubuf_alloced = 0;
    0
}

unsafe fn linux_open(fname: *mut i8, flag: CInt, mode: CInt) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = AT_FDCWD as CULong;
    ctx.gpr.rsi = fname as CULong;
    ctx.gpr.rdx = flag as CULong;
    ctx.gpr.r10 = mode as CULong;
    syscall_generic_forwarding(NR_OPENAT, &raw mut ctx) as CInt
}

unsafe fn linux_unlink(fname: *mut i8) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = AT_FDCWD as CULong;
    ctx.gpr.rsi = fname as CULong;
    ctx.gpr.rdx = 0;
    syscall_generic_forwarding(NR_UNLINKAT, &raw mut ctx) as CInt
}

unsafe fn linux_read(fd: CInt, mut buf: *mut c_void, mut count: SizeT) -> CLong {
    let mut ctx: X86UserContext = zeroed();
    let count0 = count;
    let mut sz: CLong = 0;

    ctx.gpr.rdi = fd as CULong;
    loop {
        ctx.gpr.rsi = buf as CULong;
        ctx.gpr.rdx = count as CULong;
        let sz0 = syscall_generic_forwarding(NR_READ, &raw mut ctx);
        if pager_linux_io_retry_result(sz0) != 0 {
            continue;
        }
        if pager_linux_io_stop_result(sz0) != 0 {
            if pager_linux_io_first_result(sz) != 0 {
                sz = sz0;
            }
            break;
        }
        sz = pager_linux_io_advance_result(sz, sz0);
        if pager_linux_io_complete_result(sz, count0) != 0 {
            break;
        }
        count = pager_linux_io_remaining_result(count, sz0);
        buf = pager_linux_io_next_buf_result(buf as CULong, sz0) as *mut c_void;
    }
    sz
}

unsafe fn linux_write(fd: CInt, mut buf: *mut c_void, mut count: SizeT) -> CLong {
    let mut ctx: X86UserContext = zeroed();
    let count0 = count;
    let mut sz: CLong = 0;

    ctx.gpr.rdi = fd as CULong;
    loop {
        ctx.gpr.rsi = buf as CULong;
        ctx.gpr.rdx = count as CULong;
        let sz0 = syscall_generic_forwarding(NR_WRITE, &raw mut ctx);
        if pager_linux_io_retry_result(sz0) != 0 {
            continue;
        }
        if pager_linux_io_stop_result(sz0) != 0 {
            if pager_linux_io_first_result(sz) != 0 {
                sz = sz0;
            }
            break;
        }
        sz = pager_linux_io_advance_result(sz, sz0);
        if pager_linux_io_complete_result(sz, count0) != 0 {
            break;
        }
        count = pager_linux_io_remaining_result(count, sz0);
        buf = pager_linux_io_next_buf_result(buf as CULong, sz0) as *mut c_void;
    }
    sz
}

unsafe fn linux_lseek(fd: CInt, off: CLong, whence: CInt) -> CLong {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = fd as CULong;
    ctx.gpr.rsi = off as CULong;
    ctx.gpr.rdx = whence as CULong;
    syscall_generic_forwarding(NR_LSEEK, &raw mut ctx)
}

unsafe fn linux_close(fd: CInt) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = fd as CULong;
    syscall_generic_forwarding(NR_CLOSE, &raw mut ctx) as CInt
}

unsafe fn linux_munmap(addr: *mut c_void, len: SizeT, flag: CInt) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = addr as CULong;
    ctx.gpr.rsi = len as CULong;
    ctx.gpr.rdx = flag as CULong;
    syscall_generic_forwarding(NR_MUNMAP, &raw mut ctx) as CInt
}

unsafe fn pager_open(si: *mut SwapInfo, fname: *mut i8, flag: CInt, mode: CInt) -> CInt {
    let len = strlen(fname).wrapping_add(1);
    let _ = copy_to_user(
        (*si).udata_buf.cast::<c_void>(),
        fname.cast::<c_void>(),
        len,
    );
    linux_open((*si).udata_buf, flag, mode)
}

unsafe fn pager_unlink(si: *mut SwapInfo, fname: *mut i8) -> CInt {
    let len = strlen(fname).wrapping_add(1);
    let _ = copy_to_user(
        (*si).udata_buf.cast::<c_void>(),
        fname.cast::<c_void>(),
        len,
    );
    linux_unlink((*si).udata_buf)
}

unsafe fn pager_copy_from_user(
    dst: *mut c_void,
    from: *mut c_void,
    size: SizeT,
    vm: *mut ProcessVm,
) -> CInt {
    let ret = pager_copy_size_error_result(size);
    if ret != 0 {
        return ret;
    }

    let mut faulted = 0;
    loop {
        let mut psize: CULong = 0;
        let mut rphys: CULong = 0;
        let ret = ihk_mc_pt_virt_to_phys_size(
            (*(*vm).address_space).page_table,
            dst,
            &raw mut rphys,
            &raw mut psize,
        );

        if ret == 0 {
            let virt = phys_to_virt(rphys);
            return copy_from_user(virt, from.cast::<c_void>(), size);
        }

        let reason = PF_POPULATE | PF_WRITE | PF_USER;
        let addr = pager_fault_addr_result(dst as CULong) as *mut c_void;

        if pager_copy_fault_retry_result(faulted) == 0 {
            return -EFAULT;
        }
        let fault_ret = page_fault_process_vm(vm, addr, reason);
        let fault_ret = pager_copy_fault_error_result(fault_ret);
        if fault_ret != 0 {
            return fault_ret;
        }
        faulted = 1;
    }
}

unsafe fn pager_read(
    si: *mut SwapInfo,
    fd: CInt,
    start: *mut c_void,
    size: SizeT,
    vm: *mut ProcessVm,
) -> CLong {
    let mut off: SizeT = 0;

    while off < size {
        let sz = pager_read_chunk_size_result(off, size);
        let rs = linux_read(fd, (*si).udata_buf.cast::<c_void>(), sz);
        if rs != sz as CLong {
            return rs;
        }

        let dst = start.cast::<u8>().add(off).cast::<c_void>();
        let rs = pager_copy_from_user(dst, (*si).udata_buf.cast::<c_void>(), sz, vm);
        if rs != 0 {
            return rs as CLong;
        }
        off = off.wrapping_add(sz);
    }
    off as CLong
}

unsafe fn pager_write(fd: CInt, start: *mut c_void, size: SizeT) -> CLong {
    linux_write(fd, start, size)
}

unsafe fn mlocklist_req(start: CULong, end: CULong, addr: *mut AddrPair, nent: CInt) -> CInt {
    let mut ctx: X86UserContext = zeroed();

    ctx.gpr.rdi = PAGER_REQ_MLOCK_LIST;
    ctx.gpr.rsi = start;
    ctx.gpr.rdx = end;
    ctx.gpr.r10 = addr as CULong;
    ctx.gpr.r8 = nent as CULong;
    syscall_generic_forwarding(NR_MMAP, &raw mut ctx) as CInt
}

unsafe fn mlocklist_morereq(si: *mut SwapInfo, start: *mut CULong) -> CInt {
    let ent = (*si).mlock_area.tail;
    let mut went: AreaEnt = zeroed();
    let _ = copy_from_user(
        (&raw mut went).cast::<c_void>(),
        ent.cast::<c_void>(),
        size_of::<AreaEnt>(),
    );

    let tail_pair = went.pair.as_ptr().add(went.count as usize);
    if pager_mlock_more_result((*tail_pair).start) == 0 {
        return 0;
    }
    *start = pager_mlock_next_start_result((*tail_pair).end);
    1
}

unsafe fn arealist_alloc(si: *mut SwapInfo, areap: *mut AreaList) -> CInt {
    let ent = myalloc(si, size_of::<AreaEnt>());
    (*areap).head = ent.cast::<AreaEnt>();
    (*areap).tail = ent.cast::<AreaEnt>();
    if (*areap).head.is_null() {
        return -ENOMEM;
    }

    let went: AreaEnt = zeroed();
    let _ = copy_to_user(
        (*areap).head.cast::<c_void>(),
        (&went as *const AreaEnt).cast::<c_void>(),
        size_of::<AreaEnt>(),
    );
    0
}

unsafe fn arealist_init(si: *mut SwapInfo) -> CInt {
    let cc = arealist_alloc(si, &raw mut (*si).swap_area);
    if cc < 0 {
        return cc;
    }
    arealist_alloc(si, &raw mut (*si).mlock_area)
}

unsafe fn arealist_free(area: *mut AreaList) {
    let mut tmp = (*area).head;
    while !tmp.is_null() {
        let next = (*tmp).next;
        myfree(tmp.cast::<c_void>());
        tmp = next;
    }
    write_bytes(area.cast::<u8>(), 0, size_of::<AreaList>());
}

unsafe fn arealist_get(si: *mut SwapInfo, pair: *mut *mut AddrPair, area: *mut AreaList) -> CInt {
    let tail = (*area).tail;
    let room = pager_arealist_tail_room_result((*tail).count);
    if room != 0 {
        if !pair.is_null() {
            *pair = (*tail).pair.as_mut_ptr().add((*tail).count as usize);
        }
        return room;
    }

    let tmp = myalloc(si, size_of::<AreaEnt>()).cast::<AreaEnt>();
    if tmp.is_null() {
        return -1;
    }
    let wtmp: AreaEnt = zeroed();
    let _ = copy_to_user(
        tmp.cast::<c_void>(),
        (&wtmp as *const AreaEnt).cast::<c_void>(),
        size_of::<AreaEnt>(),
    );
    let _ = copy_to_user(
        (&raw mut (*(*area).tail).next).cast::<c_void>(),
        (&tmp as *const *mut AreaEnt).cast::<c_void>(),
        size_of::<*mut AreaEnt>(),
    );

    (*area).tail = tmp;
    if !pair.is_null() {
        *pair = (*(*area).tail).pair.as_mut_ptr();
    }
    MLOCKADDRS_SIZE as CInt
}

unsafe fn arealist_update(cnt: CInt, area: *mut AreaList) {
    let mut i: CInt = 0;
    let _ = copy_from_user(
        (&raw mut i).cast::<c_void>(),
        (&raw mut (*(*area).tail).count).cast::<c_void>(),
        size_of::<CInt>(),
    );
    i = pager_arealist_count_add_result(i, cnt);
    let _ = copy_to_user(
        (&raw mut (*(*area).tail).count).cast::<c_void>(),
        (&i as *const CInt).cast::<c_void>(),
        size_of::<CInt>(),
    );
    (*area).count = pager_arealist_count_add_result((*area).count, cnt);
}

unsafe fn arealist_add(
    si: *mut SwapInfo,
    start: CULong,
    end: CULong,
    flag: CULong,
    area: *mut AreaList,
) -> CInt {
    let mut addr: *mut AddrPair = null_mut();

    let cc = arealist_get(si, &raw mut addr, area);
    if cc < 0 {
        return -1;
    }
    let waddr = AddrPair { start, end, flag };
    let _ = copy_to_user(
        addr.cast::<c_void>(),
        (&waddr as *const AddrPair).cast::<c_void>(),
        size_of::<AddrPair>(),
    );
    arealist_update(1, area);
    0
}

unsafe fn arealist_preparewrite(
    areap: *mut AreaList,
    info: *mut SwapAreaInfo,
    off: CLong,
    vm: *mut ProcessVm,
    flag: CInt,
) -> CInt {
    let mut ent = (*areap).head;
    let mut count: CInt = 0;
    let mut totsz: CLong = 0;
    let pt = (*(*vm).address_space).page_table;

    while !ent.is_null() {
        let mut went: AreaEnt = zeroed();
        let _ = copy_from_user(
            (&raw mut went).cast::<c_void>(),
            ent.cast::<c_void>(),
            size_of::<AreaEnt>(),
        );

        let mut i: CInt = 0;
        while i < went.count {
            let idx = i as usize;
            let went_pair = went.pair.as_ptr().add(idx);
            let out = info.add(count as usize);
            let sz = pager_addrpair_size_result((*went_pair).start, (*went_pair).end);

            let _ = copy_to_user(
                (&raw mut (*out).start).cast::<c_void>(),
                (&raw const (*went_pair).start).cast::<c_void>(),
                size_of::<CULong>(),
            );
            let _ = copy_to_user(
                (&raw mut (*out).end).cast::<c_void>(),
                (&raw const (*went_pair).end).cast::<c_void>(),
                size_of::<CULong>(),
            );
            let _ = copy_to_user(
                (&raw mut (*out).flag).cast::<c_void>(),
                (&raw const (*went_pair).flag).cast::<c_void>(),
                size_of::<CULong>(),
            );

            let mut pos: CULong = if flag != 0 {
                pager_file_pos_result(off, totsz) as CULong
            } else {
                let mut phys: CULong = 0;
                let ent_pair = (*ent).pair.as_ptr().add(idx);
                if ihk_mc_pt_virt_to_phys(pt, (*ent_pair).start as *mut c_void, &raw mut phys) != 0
                {
                    kprintf(CANNOT_GET_PHYS_FMT.as_ptr().cast());
                }
                phys
            };
            let _ = copy_to_user(
                (&raw mut (*out).pos).cast::<c_void>(),
                (&raw mut pos).cast::<c_void>(),
                size_of::<CULong>(),
            );
            totsz = totsz.wrapping_add(sz);
            count = count.wrapping_add(1);
            i = i.wrapping_add(1);
        }
        ent = (*ent).next;
    }
    count
}

unsafe fn arealist_write(fd: CInt, info: *mut SwapAreaInfo, count: CInt) -> CLong {
    let written = linux_write(
        fd,
        info.cast::<c_void>(),
        size_of::<SwapAreaInfo>().wrapping_mul(count as SizeT),
    );
    pager_arealist_write_result(written, count, size_of::<SwapAreaInfo>())
}

unsafe fn arealist_print(msg: *const i8, areap: *mut AreaList, count: CInt) {
    let mut ent = (*areap).head;
    kprintf(AREALIST_HEAD_FMT.as_ptr().cast(), msg, count);
    while !ent.is_null() {
        let mut i: CInt = 0;
        while i < (*ent).count {
            let pair = (*ent).pair.as_ptr().add(i as usize);
            kprintf(
                AREALIST_ENTRY_FMT.as_ptr().cast(),
                (*pair).start as *mut c_void,
                (*pair).end as *mut c_void,
            );
            i = i.wrapping_add(1);
        }
        ent = (*ent).next;
    }
}

unsafe fn mlockcntnr_sethead(si: *mut SwapInfo) -> CInt {
    let cnt = arealist_get(si, null_mut(), &raw mut (*si).mlock_area);
    if cnt < 0 {
        return -1;
    }
    (*si).mlock_container.from = (*si).mlock_area.tail;
    (*si).mlock_container.cur = (*si).mlock_area.tail;
    (*si).mlock_container.ccount = (*(*si).mlock_area.tail).count;
    0
}

unsafe fn mlockcntnr_isempty(si: *mut SwapInfo) -> CInt {
    pager_mlock_container_empty_result(
        (*si).mlock_container.from as CULong,
        (*si).mlock_area.tail as CULong,
        (*si).mlock_container.ccount,
        (*(*si).mlock_area.tail).count,
    )
}

unsafe fn mlockcntnr_addrent(si: *mut SwapInfo, laddr: *mut AddrPair) -> CInt {
    if pager_mlock_needs_next_result(
        (*si).mlock_container.ccount,
        (*(*si).mlock_container.cur).count,
    ) != 0
    {
        let tmp = (*(*si).mlock_container.cur).next;
        if tmp.is_null() {
            return 0;
        }
        (*si).mlock_container.cur = tmp;
        (*si).mlock_container.ccount = pager_mlock_reset_count_result();
    }
    let pair = (*(*si).mlock_container.cur)
        .pair
        .as_ptr()
        .add(((*si).mlock_container.ccount - 1) as usize);
    *laddr = *pair;
    (*si).mlock_container.ccount = pager_mlock_next_count_result((*si).mlock_container.ccount);
    1
}

#[no_mangle]
pub unsafe extern "C" fn print_region(msg: *mut i8, vm: *mut ProcessVm) {
    let mut next = lookup_process_memory_range(vm, 0, CULong::MAX);

    kprintf(REGION_HEAD_FMT.as_ptr().cast(), msg);
    while !next.is_null() {
        let range = next;
        next = next_process_memory_range(vm, range);
        if !(*range).memobj.is_null() {
            continue;
        }
        kprintf(
            REGION_FMT.as_ptr().cast(),
            (*range).start,
            (*range).end,
            (*range).flag,
        );
    }
}

#[no_mangle]
pub unsafe extern "C" fn do_pagein(_flag: CInt) -> CInt {
    let thread = current_thread();
    let vm = (*thread).vm;
    let si = (*vm).swapinfo.cast::<SwapInfo>();

    let fd = pager_open(si, (*si).swapfname, O_RDONLY, 0);
    let _ = pager_unlink(si, (*si).swapfname);
    if fd < 0 {
        kprintf(PAGEIN_OPEN_FMT.as_ptr().cast(), (*si).swapfname);
        return fd;
    }

    let pos = pager_pagein_data_pos_result(
        (*(*si).swphdr).count_sarea,
        (*(*si).swphdr).count_marea,
        size_of::<SwapHeader>(),
        size_of::<SwapAreaInfo>(),
    );
    let _ = linux_lseek(fd, pos, SEEK_SET);

    let mut i: u32 = 0;
    while i < (*(*si).swphdr).count_sarea {
        let info = (*si).swap_info.add(i as usize);
        let sz = pager_addrpair_size_result((*info).start, (*info).end);
        let rs = pager_read(si, fd, (*info).start as *mut c_void, sz as SizeT, vm);
        if rs != sz {
            let _ = linux_close(fd);
            kprintf(PAGEIN_READ_ERR_FMT.as_ptr().cast(), rs, sz);
            (*vm).swapinfo = null_mut();
            kernel_free((*si).swapfname.cast::<c_void>());
            kernel_free(si.cast::<c_void>());
            return -1;
        }
        i = i.wrapping_add(1);
    }

    let _ = linux_close(fd);
    print_region(AFTER_PAGEIN.as_ptr() as *mut i8, vm);
    (*vm).swapinfo = null_mut();
    kernel_free((*si).swapfname.cast::<c_void>());
    kernel_free(si.cast::<c_void>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn do_pageout(
    fname: *mut i8,
    buf: *mut c_void,
    size: SizeT,
    flag: CInt,
) -> CInt {
    let thread = current_thread();
    let vm = (*thread).vm;
    let region = &raw mut (*vm).region;
    let mut fd: CInt = -1;

    let mut cc = pager_pageout_args_result(
        fname as CULong,
        buf as CULong,
        size,
        (*region).user_start,
        (*region).user_end,
    ) as CLong;
    if cc != 0 {
        return cc as CInt;
    }

    let si = kernel_alloc(size_of::<SwapInfo>()).cast::<SwapInfo>();
    if si.is_null() {
        kprintf(PAGEOUT_ALLOC_FMT.as_ptr().cast());
        return -ENOMEM;
    }
    write_bytes(si.cast::<u8>(), 0, size_of::<SwapInfo>());

    cc = myalloc_init(si, buf, size) as CLong;
    if cc < 0 {
        kernel_free(si.cast::<c_void>());
        kprintf(PAGEOUT_PIN_FMT.as_ptr().cast(), buf);
        return cc as CInt;
    }

    (*si).udata_buf = myalloc(si, UDATA_BUFSIZE).cast::<i8>();
    (*si).swapfname = kernel_alloc_i(strlen_user(fname).wrapping_add(1)).cast::<i8>();
    if (*si).swapfname.is_null() {
        kernel_free(si.cast::<c_void>());
        kprintf(PAGEOUT_ALLOC_FMT.as_ptr().cast());
        return -ENOMEM;
    }
    if strcpy_from_user((*si).swapfname, fname) != 0 {
        cc = -(EFAULT as CLong);
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }
    cc = arealist_init(si) as CLong;
    if cc < 0 {
        kprintf(
            PAGEOUT_USER_AREA_FMT.as_ptr().cast(),
            (UDATA_BUFSIZE + size_of::<AreaEnt>() * 2) as CInt,
        );
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }

    let name_len = strlen((*si).swapfname).wrapping_add(1);
    let _ = copy_to_user(
        (*si).udata_buf.cast::<c_void>(),
        (*si).swapfname.cast::<c_void>(),
        name_len,
    );
    fd = linux_open((*si).udata_buf, O_RDWR | O_CREAT | O_TRUNC, 0o600);
    if fd < 0 {
        kprintf(PAGEOUT_OPEN_FMT.as_ptr().cast(), fname);
        cc = fd as CLong;
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }
    area_print(region);

    let mut next = lookup_process_memory_range(vm, 0, CULong::MAX);
    while !next.is_null() {
        let range = next;
        next = next_process_memory_range(vm, range);
        if pager_skip_anon_range_result(
            (!(*range).memobj.is_null()) as CInt,
            (*range).start,
            (*region).text_start,
            (*region).stack_start,
            (*region).user_start,
            (*region).user_end,
            (*range).flag,
        ) != 0
        {
            continue;
        }

        if pager_range_locked_result((*range).flag) != 0 {
            cc = arealist_add(
                si,
                (*range).start,
                (*range).end,
                (*range).flag,
                &raw mut (*si).mlock_area,
            ) as CLong;
            if cc < 0 {
                return pageout_nomem(si, vm, fd);
            }
            continue;
        }

        let mut start = (*range).start;
        let end = (*range).end;
        cc = mlockcntnr_sethead(si) as CLong;
        if cc < 0 {
            return pageout_nomem(si, vm, fd);
        }

        loop {
            let mut addr: *mut AddrPair = null_mut();
            cc = arealist_get(si, &raw mut addr, &raw mut (*si).mlock_area) as CLong;
            if cc < 0 {
                return pageout_nomem(si, vm, fd);
            }
            cc = mlocklist_req(start, end, addr, cc as CInt) as CLong;
            arealist_update(cc as CInt, &raw mut (*si).mlock_area);
            if mlocklist_morereq(si, &raw mut start) == 0 {
                break;
            }
        }

        if mlockcntnr_isempty(si) != 0 {
            cc = arealist_add(
                si,
                (*range).start,
                (*range).end,
                (*range).flag,
                &raw mut (*si).swap_area,
            ) as CLong;
            if cc < 0 {
                return pageout_nomem(si, vm, fd);
            }
        } else {
            start = (*range).start;
            while start < (*range).end {
                let mut laddr: AddrPair = zeroed();
                if mlockcntnr_addrent(si, &raw mut laddr) == 0 {
                    cc = arealist_add(
                        si,
                        start,
                        (*range).end,
                        (*range).flag,
                        &raw mut (*si).swap_area,
                    ) as CLong;
                    if cc < 0 {
                        return pageout_nomem(si, vm, fd);
                    }
                    break;
                }
                if start < laddr.start {
                    cc = arealist_add(
                        si,
                        start,
                        laddr.start,
                        (*range).flag,
                        &raw mut (*si).swap_area,
                    ) as CLong;
                    if cc < 0 {
                        return pageout_nomem(si, vm, fd);
                    }
                }
                start = laddr.end;
                kprintf(
                    PAGEOUT_START_FMT.as_ptr().cast(),
                    start as CLong,
                    (*range).end as CLong,
                );
                break;
            }
        }
    }

    arealist_print(
        SWAP_LABEL.as_ptr().cast(),
        &raw mut (*si).swap_area,
        (*si).swap_area.count,
    );
    arealist_print(
        MLOCK_LABEL.as_ptr().cast(),
        &raw mut (*si).mlock_area,
        (*si).mlock_area.count,
    );

    (*si).swap_info = myalloc(
        si,
        size_of::<SwapAreaInfo>().wrapping_mul((*si).swap_area.count as SizeT),
    )
    .cast::<SwapAreaInfo>();
    (*si).mlock_info = myalloc(
        si,
        size_of::<SwapAreaInfo>().wrapping_mul((*si).mlock_area.count as SizeT),
    )
    .cast::<SwapAreaInfo>();
    if (*si).swap_info.is_null() || (*si).mlock_info.is_null() {
        return pageout_nomem(si, vm, fd);
    }

    (*si).swphdr = myalloc(si, size_of::<SwapHeader>()).cast::<SwapHeader>();
    let _ = copy_to_user(
        (&raw mut (*(*si).swphdr).magic).cast::<c_void>(),
        MCKERNEL_SWAP.as_ptr().cast::<c_void>(),
        SWAP_HLEN,
    );
    let _ = copy_to_user(
        (&raw mut (*(*si).swphdr).version).cast::<c_void>(),
        MCKERNEL_SWAP_VERSION.as_ptr().cast::<c_void>(),
        SWAP_HLEN,
    );
    let count_sarea = (*si).swap_area.count as u32;
    let count_marea = (*si).mlock_area.count as u32;
    let _ = copy_to_user(
        (&raw mut (*(*si).swphdr).count_sarea).cast::<c_void>(),
        (&count_sarea as *const u32).cast::<c_void>(),
        size_of::<u32>(),
    );
    let _ = copy_to_user(
        (&raw mut (*(*si).swphdr).count_marea).cast::<c_void>(),
        (&count_marea as *const u32).cast::<c_void>(),
        size_of::<u32>(),
    );

    cc = pager_write(fd, (*si).swphdr.cast::<c_void>(), size_of::<SwapHeader>());
    if cc != size_of::<SwapHeader>() as CLong {
        cc = pager_io_short_result(cc);
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }

    let mut pos = linux_lseek(fd, 0, SEEK_CUR);
    pos = pager_file_pos_result(
        pos,
        size_of::<SwapAreaInfo>() as CLong
            * ((*si).swap_area.count as CLong + (*si).mlock_area.count as CLong),
    );
    cc = arealist_preparewrite(&raw mut (*si).swap_area, (*si).swap_info, pos, vm, 1) as CLong;
    if cc != (*si).swap_area.count as CLong {
        kprintf(
            PAGEOUT_FILE_ENT_FMT.as_ptr().cast(),
            cc as CInt,
            (*si).swap_area.count,
        );
    }
    cc = arealist_preparewrite(&raw mut (*si).mlock_area, (*si).mlock_info, 0, vm, 0) as CLong;
    if cc != (*si).mlock_area.count as CLong {
        kprintf(
            PAGEOUT_FILE_ENT_FMT.as_ptr().cast(),
            cc as CInt,
            (*si).mlock_area.count,
        );
    }

    cc = arealist_write(fd, (*si).swap_info, (*si).swap_area.count);
    if cc < 0 {
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }
    cc = arealist_write(fd, (*si).mlock_info, (*si).mlock_area.count);
    if cc < 0 {
        pageout_err(si, vm, fd, cc);
        return cc as CInt;
    }

    let mut i: CInt = 0;
    while i < (*si).swap_area.count {
        let mut sw_info: SwapAreaInfo = zeroed();
        let _ = copy_from_user(
            (&raw mut sw_info).cast::<c_void>(),
            (*si).swap_info.add(i as usize).cast::<c_void>(),
            size_of::<SwapAreaInfo>(),
        );
        let sz = pager_addrpair_size_result(sw_info.start, sw_info.end);
        cc = pager_write(fd, sw_info.start as *mut c_void, sz as SizeT);
        if cc != sz {
            cc = pager_io_short_result(cc);
            pageout_err(si, vm, fd, cc);
            return cc as CInt;
        }
        i = i.wrapping_add(1);
    }

    if pager_skip_physical_removal_result(flag) != 0 {
        kprintf(SKIP_REMOVAL_FMT.as_ptr().cast());
        return goto_free_exit(si, vm, fd, cc);
    }
    kprintf(REMOVE_PHYS_FMT.as_ptr().cast());

    i = 0;
    while i < (*si).swap_area.count {
        let mut sw_info: SwapAreaInfo = zeroed();
        let _ = copy_from_user(
            (&raw mut sw_info).cast::<c_void>(),
            (*si).swap_info.add(i as usize).cast::<c_void>(),
            size_of::<SwapAreaInfo>(),
        );
        cc = ihk_mc_pt_free_range(
            (*(*vm).address_space).page_table,
            vm,
            sw_info.start as *mut c_void,
            sw_info.end as *mut c_void,
            null_mut(),
        ) as CLong;
        if cc < 0 {
            kprintf(FREE_RANGE_ERR_FMT.as_ptr().cast(), cc as CInt);
        }
        i = i.wrapping_add(1);
    }

    let _ = linux_close(fd);
    fd = -1;

    i = 0;
    while i < (*si).swap_area.count {
        let mut sw_info: SwapAreaInfo = zeroed();
        let _ = copy_from_user(
            (&raw mut sw_info).cast::<c_void>(),
            (*si).swap_info.add(i as usize).cast::<c_void>(),
            size_of::<SwapAreaInfo>(),
        );
        let sz = pager_addrpair_size_result(sw_info.start, sw_info.end);
        cc = linux_munmap(sw_info.start as *mut c_void, sz as SizeT, 0) as CLong;
        if cc < 0 {
            kprintf(
                MUNMAP_ERR_FMT.as_ptr().cast(),
                (*(*si).swap_info.add(i as usize)).start,
                sz,
            );
        }
        i = i.wrapping_add(1);
    }

    cc = 0;
    goto_free_exit(si, vm, fd, cc)
}

unsafe fn pageout_nomem(si: *mut SwapInfo, vm: *mut ProcessVm, fd: CInt) -> CInt {
    kprintf(PAGEOUT_NOMEM_FMT.as_ptr().cast());
    goto_free_exit(si, vm, fd, -(ENOMEM as CLong))
}

unsafe fn pageout_err(si: *mut SwapInfo, vm: *mut ProcessVm, fd: CInt, cc: CLong) -> CInt {
    kprintf(PAGEOUT_WRITE_ERR_FMT.as_ptr().cast(), cc as CInt);
    goto_free_exit(si, vm, fd, cc)
}

unsafe fn goto_free_exit(si: *mut SwapInfo, vm: *mut ProcessVm, fd: CInt, cc: CLong) -> CInt {
    if pager_fd_valid_result(fd) != 0 {
        let _ = linux_close(fd);
    }
    arealist_free(&raw mut (*si).mlock_area);
    arealist_free(&raw mut (*si).swap_area);

    if pager_should_unlink_swap_result(cc) != 0 {
        let _ = pager_unlink(si, (*si).swapfname);
        kernel_free((*si).swapfname.cast::<c_void>());
        kernel_free(si.cast::<c_void>());
    } else {
        (*vm).swapinfo = si.cast::<c_void>();
    }
    cc as CInt
}
