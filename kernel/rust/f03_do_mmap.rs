// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete current ordinary-x86 do_mmap orchestration. Other C profiles retain
// their original entry. No effect endpoint is replaced by a test callback.
#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12,
    enable_profile, not(enable_tofu), not(enable_fugaku_hacks))))]
compile_error!("do_mmap requires its paired ordinary x86/Linux6.12/PROFILE profile");

use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};
use core::sync::atomic::{AtomicI32, Ordering};

use crate::abi::{CInt, CLong, CULong, Mckfd, Memobj, MemobjOps, OffT,
    Process, ProcessVm, ShmidDs, SizeT, Thread, VmRange, X86UserContext};
use crate::debug::{kprintf, Ddebug};
use crate::syscall_policy as policy;

const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const MAP_SHARED: CInt = 1;
const MAP_FIXED: CInt = 0x10;
const MAP_ANONYMOUS: CInt = 0x20;
const MAP_LOCKED: CInt = 0x2000;
const MAP_POPULATE: CInt = 0x8000;
const MAP_STACK: CInt = 0x20000;
const PROT_READ: CInt = 1;
const PROT_WRITE: CInt = 2;
const PROT_EXEC: CInt = 4;
const VR_AP_USER: CInt = 4;
const VR_DEMAND_PAGING: CInt = 0x1000;
const VR_PROT_MASK: CInt = 0x70000;
const VR_MEMTYPE_UC: CInt = 0x01000000;
const VR_MEMTYPE_MASK: CInt = 0x0f000000;
const MF_ZEROFILL: u32 = 0x10;
const MF_DEV_FILE: u32 = 0x2000;
const MF_PREMAP: u32 = 0x8000;
const MF_XPMEM: u32 = 0x10000;
const MF_HUGETLBFS: u32 = 0x100000;
const MPOL_NO_STACK: CULong = 2;
const MPOL_SHM_PREMAP: CULong = 8;
const PF_POPULATE: CULong = 1 << 30;
const IHK_MC_AP_NOWAIT: CULong = 2;
const IHK_MC_AP_USER: CULong = 0x1000;
const IHK_MC_PG_USER: CInt = 1;
const EINVAL: CInt = 22;
const ESRCH: CInt = 3;

unsafe extern "C" {
    static anon_on_demand: CInt;
    fn do_munmap(addr: *mut c_void, len: SizeT, holding_lock: CInt) -> CInt;
    fn f03_do_mmap_smaller_page_v2(size: SizeT, p2align: *mut CInt) -> CInt;
}

// These are the real source-origin/debug inputs already supplied to the current
// PROFILE-on outer-syscall producer. The paired selector has the same requirement.
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_bytes();
const NAME: &[u8] = b"do_mmap\0";
const DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("do_mmap requires the actual C DDEBUG default"),
};
const fn record(line: u32) -> Ddebug {
    Ddebug { file: SOURCE_FILE.as_ptr().cast(), func: NAME.as_ptr().cast(),
        fmt: core::ptr::null(), line_flags: line | (DEBUG_FLAGS << 24) }
}
// Original selected #line5838 maps physical6062 to5838. Inactive #line5847,
// FUGAKU/TOFU and #if0 macros are excluded by the paired ordinary-x86 selector.
#[used]
#[link_section = "__verbose"]
static mut MMAP_DEBUG: [Ddebug; 14] = [
    record(5945), record(6090), record(6269), record(6332),
    record(6414), record(6417), record(6439), record(6462),
    record(6469), record(6481), record(6503), record(6537),
    record(6582), record(6658),
];
unsafe fn debug(index: usize) -> bool {
    let entry = addr_of!(MMAP_DEBUG).cast::<Ddebug>().add(index);
    read_volatile(addr_of!((*entry).line_flags)) >> 24 != 0
}

// Matching C assertions live in the selected source guard. These are typed
// existing ABI structures, not offsets projected through an invented layout.
const _: () = {
    assert!(size_of::<SizeT>() == 8 && align_of::<SizeT>() == 8);
    assert!(size_of::<CULong>() == 8 && align_of::<CULong>() == 8);
    assert!(size_of::<Memobj>() == 56 && align_of::<Memobj>() == 8);
    assert!(offset_of!(Memobj, status) == 12 && offset_of!(Memobj, size) == 16);
    assert!(offset_of!(Memobj, pages) == 32 && offset_of!(Memobj, nr_pages) == 40);
    assert!(offset_of!(Memobj, path) == 48 && offset_of!(MemobjOps, free) == 0);
    assert!(size_of::<ShmidDs>() == 112 && offset_of!(ShmidDs, init_pgshift) == 108);
    assert!(offset_of!(ShmidDs, shm_segsz) == 48);
    assert!(offset_of!(ProcessVm, memory_range_lock) == 180);
    assert!(offset_of!(VmRange, straight_start) == 48 && offset_of!(VmRange, memobj) == 56);
    assert!(offset_of!(Mckfd, mmap_cb) == 48 && size_of::<Mckfd>() == 80);
    assert!(size_of::<X86UserContext>() == 224);
    assert!(size_of::<crate::abi::IhkRwSpinlock>() == 4);
    assert!(align_of::<crate::abi::IhkRwSpinlock>() == 4);
    assert!(offset_of!(crate::abi::IhkRwSpinlock, v) == 0);
    assert!(offset_of!(crate::abi::IhkAtomic, counter) == 0);
    assert!(offset_of!(Thread, vm) == 4200 && offset_of!(Thread, proc) == 4304);
    assert!(offset_of!(Process, vm) == 128 && offset_of!(Process, mckfd_lock) == 1284);
    assert!(offset_of!(Process, mckfd) == 1288 && offset_of!(Process, mpol_flags) == 1376);
    assert!(offset_of!(Process, mpol_threshold) == 1384 && offset_of!(Process, thp_disable) == 1428);
    assert!(offset_of!(Process, straight_map) == 1432 && offset_of!(Process, straight_map_threshold) == 1440);
    assert!(offset_of!(Process, straight_va) == 1624 && offset_of!(Process, straight_len) == 1632);
    assert!(offset_of!(Process, straight_pa) == 1640);
};

unsafe fn object_unref(object: *mut Memobj) {
    // The real refcount helper consumes the common repr(C) memobj prefix.
    let _ = crate::refcount_helpers::memobj_unref(object.cast());
}

// The genuine noirq writer owns one preempt-disable count. Convert its exclusive
// counter to one reader without a zero/unlocked interval or preempt-enable gap.
// Existing reader unlock later consumes that same count. New readers acquire
// from this Release; writers require zero and cannot retire this range early.
// Safety: caller exclusively owns the actual writer lock, no other lock flavor.
unsafe fn downgrade_write_to_reader(lock: *mut crate::abi::IhkRwSpinlock) {
    AtomicI32::from_ptr(addr_of_mut!((*lock).v.counter)).store(1, Ordering::Release);
}

/// Own the complete selected mapping transaction, including straight mappings.
///
/// # Safety
/// Current CPU/thread/VM/process, file descriptors and private_data have their
/// original kernel lifetimes and context. Range/page-table/host operations obey
/// the original provider contracts. Successful add_range transfers local backing
/// ownership to the real range; no RAII reference spans an offload or release.
/// This entry is never HOST-run with fabricated VMs, pages or mapping callbacks.
#[no_mangle]
pub unsafe extern "C" fn do_mmap(
    addr0: CULong, len: SizeT, prot: CInt, flags: CInt, fd: CInt,
    off0: OffT, vrf0: CInt, private_data: *mut c_void,
) -> CLong {
    let thread = (*crate::cls::get_this_cpu_local_var()).current;
    let proc = (*thread).proc;
    let region = addr_of_mut!((*(*thread).vm).region);
    let mut addr = addr0;
    if debug(0) {
        kprintf(b"do_mmap(%lx,%lx,%x,%x,%d,%lx)\n\0".as_ptr().cast(),
            addr0, len, prot, flags, fd, off0);
    }

    // The exact already-selected MCKFD body retains lock/borrow/callback ordering.
    if flags & MAP_ANONYMOUS == 0 {
        let offsets = policy::SyscallMckfdOffsets {
            thread_proc_offset: offset_of!(Thread, proc),
            proc_mckfd_lock_offset: offset_of!(Process, mckfd_lock),
            proc_mckfd_offset: offset_of!(Process, mckfd),
            mckfd_next_offset: offset_of!(Mckfd, next),
            mckfd_fd_offset: offset_of!(Mckfd, fd),
            mckfd_read_cb_offset: offset_of!(Mckfd, read_cb),
            mckfd_ioctl_cb_offset: offset_of!(Mckfd, ioctl_cb),
            mckfd_close_cb_offset: offset_of!(Mckfd, close_cb),
            mckfd_fcntl_cb_offset: offset_of!(Mckfd, fcntl_cb),
        };
        let mut ctx: X86UserContext = core::mem::zeroed();
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg0(&mut ctx, addr0);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg1(&mut ctx, len as CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg2(&mut ctx, prot as CLong as CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg3(&mut ctx, flags as CLong as CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg4(&mut ctx, fd as CLong as CULong);
        crate::x86_cpu_helpers::ihk_mc_syscall_set_arg5(&mut ctx, off0 as CULong);
        let mut handled = 0;
        let result = policy::do_mmap_mckfd_dispatch_body_result(thread.cast(), flags,
            fd, (&mut ctx as *mut X86UserContext).cast(), &mut handled,
            &offsets, offset_of!(Mckfd, mmap_cb), Some(policy::syscall_mckfd_lock_bridge),
            Some(policy::syscall_mckfd_unlock_bridge));
        if handled != 0 { return result; }
    }
    crate::x86_memory_helpers::flush_nfo_tlb();

    // Original best-effort initialization. Each failure clears straight_va and
    // falls through to the ordinary mapping; no new rollback or error return.
    if (*proc).straight_map != 0 && (*proc).straight_va.is_null() {
        'straight: {
            let mut start = CULong::MAX;
            let mut end: CULong = 0;
            let mut i = 0;
            while i < crate::x86_setup::ihk_mc_get_nr_memory_chunks() {
                let mut a = 0;
                let mut b = 0;
                let _ = crate::x86_setup::ihk_mc_get_memory_chunk(i, &mut a, &mut b, null_mut());
                if start > a { start = a; }
                if end < b { end = b; }
                i += 1;
            }
            kprintf(b"%s: straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n\0".as_ptr().cast(),
                NAME.as_ptr(), start, end);
            let mut query_psize: SizeT = PAGE_SIZE as SizeT;
            let mut alignment = 0;
            let error = crate::x86_memory_helpers::arch_get_smaller_page_size(null_mut(),
                end.wrapping_sub(start) as SizeT, &mut query_psize, &mut alignment);
            if error != 0 {
                kprintf(b"%s: arch_get_smaller_page_size failed: %d\n\0".as_ptr().cast(), NAME.as_ptr(), error);
                break 'straight;
            }
            // Preserve the actual C override, even when a larger page exists.
            let psize: CULong = 1 << 29;
            alignment = 29 - PAGE_SHIFT;
            kprintf(b"%s: using page shift: %d, psize: %lu\n\0".as_ptr().cast(),
                NAME.as_ptr(), PAGE_SHIFT + alignment, psize);
            start &= !(psize - 1);
            end = end.wrapping_add(psize - 1) & !(psize - 1);
            kprintf(b"%s: aligned straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n\0".as_ptr().cast(),
                NAME.as_ptr(), start, end);
            (*proc).straight_len = end.wrapping_sub(start) as SizeT;
            let error = policy::f03_search_free_space_v1((*proc).straight_len,
                PAGE_SHIFT + alignment, addr_of_mut!((*proc).straight_va).cast());
            if error != 0 {
                kprintf(b"%s: search_free_space() failed: %d\n\0".as_ptr().cast(), NAME.as_ptr(), error);
                (*proc).straight_va = null_mut();
                break 'straight;
            }
            if debug(1) {
                kprintf(b"%s: straight_va: 0x%lx to be used\n\0".as_ptr().cast(), NAME.as_ptr(), (*proc).straight_va);
            }
            let protection = crate::process_helpers::PROT_TO_VR_FLAG((PROT_READ | PROT_WRITE) as CULong);
            let protection = protection | crate::process_helpers::VRFLAG_PROT_TO_MAXPROT(protection)
                | VR_DEMAND_PAGING as CULong;
            let mut range: *mut VmRange = null_mut();
            if crate::process_helpers::add_process_memory_range((*proc).vm,
                (*proc).straight_va as CULong,
                ((*proc).straight_va as CULong).wrapping_add((*proc).straight_len as CULong),
                CULong::MAX, protection, null_mut(), 0, PAGE_SHIFT + alignment,
                private_data, &mut range) != 0 {
                kprintf(b"%s: error: adding straight memory range \n\0".as_ptr().cast(), NAME.as_ptr());
                (*proc).straight_va = null_mut();
                break 'straight;
            }
            kprintf(b"%s: straight_va: 0x%lx, range->pgshift: %d, range OK\n\0".as_ptr().cast(),
                NAME.as_ptr(), (*proc).straight_va, (*range).pgshift);
            let attr = crate::x86_memory_helpers::arch_vrflag_to_ptattr((*range).flag, PF_POPULATE, null_mut());
            let error = crate::x86_memory_helpers::ihk_mc_pt_set_range(
                (*(*(*proc).vm).address_space).page_table, (*proc).vm.cast(),
                (*range).start as *mut c_void, (*range).end as *mut c_void,
                start, attr, (*range).pgshift, range.cast(), 0);
            if error != 0 {
                kprintf(b"%s: ihk_mc_pt_set_range() failed: %d\n\0".as_ptr().cast(), NAME.as_ptr(), error);
                (*proc).straight_va = null_mut();
                break 'straight;
            }
            (*region).map_end = ((*proc).straight_va as CULong).wrapping_add((*proc).straight_len as CULong);
            (*proc).straight_pa = start;
            kprintf(b"%s: straight mapping: 0x%lx:%lu @ 0x%lx, psize: %lu, straight_map_threshold: %lu\n\0".as_ptr().cast(),
                NAME.as_ptr(), (*proc).straight_va, (*proc).straight_len,
                (*proc).straight_pa, psize, (*proc).straight_map_threshold);
        }
    }

    let mut pgshift = 0;
    let mut p2align = 0;
    let mut p: *mut c_void = null_mut();
    let mut npages: CLong = 0;
    let mut object: *mut Memobj = null_mut();
    let mut range: *mut VmRange = null_mut();
    let mut vrflags: CInt = 0;
    let mut ro_vma_mapped = false;
    let mut write_locked = false;
    let mut populated_mapping = false;
    let mut populate_len: SizeT = 0;
    let mut error = 'mapping: {
        let error = policy::do_mmap_page_size_body_result(flags, vrf0 as CLong as CULong,
            (*proc).thp_disable, len, &mut pgshift, &mut p2align,
            Some(crate::x86_setup::ihk_mc_get_linux_default_huge_page_shift),
            Some(f03_do_mmap_smaller_page_v2));
        if error != 0 {
            kprintf(b"do_mmap:arch_get_smaller_page_size failed. %d\n\0".as_ptr().cast(), error);
            break 'mapping error;
        }
        crate::lock_helpers::ihk_rwspinlock_write_lock_noirq(addr_of_mut!((*(*thread).vm).memory_range_lock).cast());
        write_locked = true;
        if flags & MAP_FIXED != 0 && !(*proc).straight_va.is_null()
            && addr >= (*proc).straight_va as CULong
            && addr.wrapping_add(len as CULong) <= ((*proc).straight_va as CULong).wrapping_add((*proc).straight_len as CULong) {
            kprintf(b"%s: can't map MAP_FIXED into straight mapping\n\0".as_ptr().cast(), NAME.as_ptr());
            break 'mapping -EINVAL;
        }
        if flags & MAP_FIXED != 0 {
            let error = do_munmap(addr as *mut c_void, len, 1);
            if error != 0 {
                kprintf(b"do_mmap:do_munmap(%lx,%lx) failed. %d\n\0".as_ptr().cast(), addr, len, error);
                break 'mapping error;
            }
        } else if flags & MAP_ANONYMOUS != 0 {
            let error = policy::f03_search_free_space_v1(len, PAGE_SHIFT + p2align, &mut addr);
            if error != 0 {
                kprintf(b"%s: error: search_free_space(%lx,%lx,%lx) failed. %d\n\0".as_ptr().cast(),
                    NAME.as_ptr(), len, (PAGE_SHIFT + p2align) as CLong, addr, error);
                break 'mapping error;
            }
        }
        vrflags = policy::mmap_base_vrflags(prot, flags, vrf0 as CLong as CULong, anon_on_demand) as CInt;
        if policy::mmap_populated_mapping_result(flags) != 0 {
            if debug(2) {
                kprintf(b"%s: 0x%lx:%lu %s%s|\n\0".as_ptr().cast(), NAME.as_ptr(), addr, len,
                    if flags & MAP_POPULATE != 0 { b"|MAP_POPULATE\0".as_ptr() } else { b"\0".as_ptr() },
                    if flags & MAP_LOCKED != 0 { b"|MAP_LOCKED\0".as_ptr() } else { b"\0".as_ptr() });
            }
            populated_mapping = true;
        }
        if policy::mmap_should_set_host_ro(flags, prot, 1) != 0 {
            let error = policy::set_host_vma_body_result(addr, len, PROT_READ | PROT_EXEC, 1);
            if error != 0 {
                kprintf(b"do_mmap:set_host_vma failed. %d\n\0".as_ptr().cast(), error);
                break 'mapping error;
            }
            ro_vma_mapped = true;
        }
        let mut phys: CULong = 0;
        let mut straight_phys: CULong = 0;
        let mut off: OffT = 0;
        let mut maxprot = PROT_READ | PROT_WRITE | PROT_EXEC;
        if flags & MAP_ANONYMOUS == 0 {
            off = off0;
            let mut error = crate::fileobj::fileobj_create(fd, &mut object, &mut maxprot, flags, addr0);
            if !object.is_null() && !(*object).path.is_null()
                && crate::string::strncmp((*object).path, b"/dev/shm/ucx_posix\0".as_ptr().cast(), 18) == 0 {
                kprintf(b"%s: mmap flags: %lx, path: %s, memobj->flags: %lx, pgshift: %d, p2align: %d -> FIXING page size\n\0".as_ptr().cast(),
                    NAME.as_ptr(), flags as CLong, (*object).path, (*object).flags as CULong, pgshift, p2align);
                pgshift = PAGE_SHIFT;
                p2align = 0;
                populated_mapping = true;
            }
            if error == 0 { crate::profile::profile_event_add(4012, len as u64); }
            if error == -ESRCH {
                if debug(3) { kprintf(b"do_mmap:hit non VREG\n\0".as_ptr().cast()); }
                vrflags = (vrflags & !VR_MEMTYPE_MASK) | VR_MEMTYPE_UC;
                error = crate::devobj::devobj_create(fd, len, off, &mut object, &mut maxprot,
                    prot, flags & (MAP_POPULATE | MAP_LOCKED));
                if error == 0 {
                    crate::profile::profile_event_add(4013, len as u64);
                    if !(*object).path.is_null()
                        && (crate::string::strncmp(b"/tmp/ompi.\0".as_ptr().cast(), (*object).path, 10) == 0
                        || crate::string::strncmp(b"/dev/shm/\0".as_ptr().cast(), (*object).path, 9) == 0) {
                        pgshift = PAGE_SHIFT;
                        p2align = 0;
                        populated_mapping = true;
                    }
                }
            }
            if error != 0 {
                kprintf(b"%s: error: file mapping failed, fd: %d, error: %d\n\0".as_ptr().cast(), NAME.as_ptr(), fd, error);
                break 'mapping error;
            }
            if !object.is_null() && (*object).flags & MF_HUGETLBFS != 0 {
                let error = crate::hugefileobj::hugefileobj_create(object, len, off, &mut pgshift, addr0);
                if error != 0 {
                    let free: unsafe extern "C" fn(*mut Memobj) = core::mem::transmute((*(*object).ops).free);
                    free(object);
                    // The real free callback destroys the allocation: common
                    // cleanup must not subsequently unref the retired pointer.
                    object = null_mut();
                    kprintf(b"%s: error creating hugetlbfs memobj, fd: %d, error: %d\n\0".as_ptr().cast(), NAME.as_ptr(), fd, error);
                    break 'mapping error;
                }
                p2align = pgshift - PAGE_SHIFT;
            }
            if flags & MAP_FIXED == 0 {
                let error = policy::f03_search_free_space_v1(len, PAGE_SHIFT + p2align, &mut addr);
                if error != 0 {
                    kprintf(b"do_mmap:search_free_space(%lx,%lx,%d) failed. %d\n\0".as_ptr().cast(),
                        len, (*region).map_end, p2align, error);
                    break 'mapping error;
                }
            }
            if policy::mmap_should_set_host_ro(flags, prot, 0) != 0 {
                let error = policy::set_host_vma_body_result(addr, len, PROT_READ | PROT_EXEC, 1);
                if error != 0 {
                    kprintf(b"do_mmap:set_host_vma failed. %d\n\0".as_ptr().cast(), error);
                    break 'mapping error;
                }
                ro_vma_mapped = true;
            }
            if (*object).flags & MF_HUGETLBFS != 0 {
                if debug(4) { kprintf(b"Created hugefileobj %p (%d:%x %llx-%llx, fd %d, pgshift %d)\n\0".as_ptr().cast(),
                    object, len as CInt, off as u32, addr, addr.wrapping_add(len as CULong), fd, pgshift); }
            } else if (*object).flags & MF_DEV_FILE != 0 && debug(5) {
                kprintf(b"%s: device fd: %d off: %lu mapping at %p - %p\n\0".as_ptr().cast(),
                    NAME.as_ptr(), fd, off, addr, addr.wrapping_add(len as CULong));
            }
        } else if vrflags & VR_DEMAND_PAGING == 0 && flags & MAP_SHARED == 0 && vrflags & VR_PROT_MASK != 0 {
            npages = (len >> PAGE_SHIFT) as CLong;
            let ap_flag = if (flags & MAP_STACK == 0 && len >= (*(*thread).proc).mpol_threshold)
                || (flags & MAP_STACK != 0 && (*(*thread).proc).mpol_flags & MPOL_NO_STACK == 0) { IHK_MC_AP_USER } else { 0 };
            if ap_flag != 0 { vrflags |= VR_AP_USER; }
            p = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(npages as CInt, p2align,
                IHK_MC_AP_NOWAIT | ap_flag, -1, IHK_MC_PG_USER, addr0,
                SOURCE_FILE.as_ptr().cast_mut().cast(), 6437);
            if p.is_null() {
                if debug(6) { kprintf(b"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n\0".as_ptr().cast(),
                    NAME.as_ptr(), npages as CInt, (npages as CULong).wrapping_mul(PAGE_SIZE), p2align); }
                vrflags |= VR_DEMAND_PAGING;
                populated_mapping = false;
                crate::profile::profile_event_add(4011, len as u64);
                let error = crate::zeroobj::zeroobj_create(&mut object);
                if error != 0 {
                    kprintf(b"%s: zeroobj_create failed, error: %d\n\0".as_ptr().cast(), NAME.as_ptr(), error);
                    break 'mapping error;
                }
            } else {
                crate::profile::profile_event_add(4008, len as u64);
                if debug(7) { kprintf(b"%s: 0x%x:%lu MAP_ANONYMOUS allocated %d pages, p2align: %lx\n\0".as_ptr().cast(),
                    NAME.as_ptr(), addr as u32, len, npages as CInt, p2align as CLong); }
                phys = crate::x86_memory_helpers::virt_to_phys(p);
            }
        } else if policy::mmap_is_shared(flags) != 0 {
            if debug(8) { kprintf(b"%s: MAP_SHARED,flags=%x,len=%ld\n\0".as_ptr().cast(), NAME.as_ptr(), flags, len); }
            let mut ads: ShmidDs = core::mem::zeroed();
            ads.shm_segsz = len;
            ads.shm_perm.mode = 0o1000;
            ads.init_pgshift = PAGE_SHIFT + p2align;
            let error = crate::shmobj::shmobj_create(&mut ads, &mut object);
            if error != 0 {
                kprintf(b"do_mmap:shmobj_create failed. %d\n\0".as_ptr().cast(), error);
                break 'mapping error;
            }
        } else {
            if debug(9) { kprintf(b"%s: anon&demand-paging\n\0".as_ptr().cast(), NAME.as_ptr()); }
            let error = crate::zeroobj::zeroobj_create(&mut object);
            if error != 0 {
                kprintf(b"do_mmap:zeroobj_create failed. %d\n\0".as_ptr().cast(), error);
                break 'mapping error;
            }
        }
        maxprot = policy::mmap_update_private_maxprot(flags, maxprot);
        let mut denied = 0;
        let error = policy::mmap_prot_denied_result(prot, maxprot, &mut denied);
        if error != 0 {
            kprintf(b"do_mmap:denied %x. %x %x\n\0".as_ptr().cast(), denied, prot, maxprot);
            break 'mapping error;
        }
        vrflags |= policy::mmap_maxprot_to_vrflags(maxprot) as CInt;
        if policy::mmap_should_force_straight(flags, (*proc).straight_map, phys, len, (*proc).straight_map_threshold) != 0 {
            if debug(10) { kprintf(b"%s: range 0x%lx:%lu will be straight, addding VR_DEMAND\n\0".as_ptr().cast(), NAME.as_ptr(), addr, len); }
            vrflags |= VR_DEMAND_PAGING;
            straight_phys = phys;
            phys = 0;
            crate::profile::profile_event_add(4009, len as u64);
        } else if flags & MAP_ANONYMOUS != 0 && (*proc).straight_map != 0 && flags & MAP_FIXED == 0 && phys != 0 {
            if (*(*crate::cls::get_this_cpu_local_var()).current).profile != 0 {
                kprintf(b"%s: contiguous but not straight? len: %lu\n\0".as_ptr().cast(), NAME.as_ptr(), len);
            }
            crate::profile::profile_event_add(4010, len as u64);
        }
        let error = crate::process_helpers::add_process_memory_range((*thread).vm, addr,
            addr.wrapping_add(len as CULong), phys, vrflags as CLong as CULong,
            object.cast(), off, pgshift, private_data, &mut range);
        if error != 0 {
            kprintf(b"%s: add_process_memory_range failed for 0x%lx:%lu flags: %lx, vrflags: %lx, pgshift: %d, error: %d\n\0".as_ptr().cast(),
                NAME.as_ptr(), addr, addr.wrapping_add(len as CULong), flags as CLong, vrflags as CLong, pgshift, error);
            break 'mapping error;
        }
        if straight_phys != 0 {
            (*range).straight_start = ((*proc).straight_va as CULong).wrapping_add(straight_phys.wrapping_sub((*proc).straight_pa));
            if debug(11) { kprintf(b"%s: range 0x%lx:%lu is straight starting at 0x%lx\n\0".as_ptr().cast(),
                NAME.as_ptr(), addr, len, (*range).straight_start); }
            crate::string::__inline_memset(crate::x86_memory_helpers::phys_to_virt(straight_phys), 0, len);
        }
        populate_len = if object.is_null() { len } else { core::cmp::min(len, (*object).size) };
        if flags & MAP_ANONYMOUS == 0 {
            if crate::atomic_helpers::atomic_cmpxchg4(addr_of_mut!((*object).status), 1, 0) == 1 {
                populated_mapping = true;
            }
            if (*object).flags & MF_PREMAP != 0 && (*proc).mpol_flags & MPOL_SHM_PREMAP != 0 {
                if (*object).flags & MF_ZEROFILL != 0 {
                    let attr = crate::x86_memory_helpers::arch_vrflag_to_ptattr((*range).flag, PF_POPULATE, null_mut());
                    let mut i: CInt = 0;
                    while i < (*object).nr_pages {
                        let start = (*range).start.wrapping_add((i as CLong as CULong).wrapping_mul(PAGE_SIZE));
                        let error = crate::x86_memory_helpers::ihk_mc_pt_set_range(
                            (*(*(*proc).vm).address_space).page_table, (*proc).vm.cast(),
                            start as *mut c_void, start.wrapping_add(PAGE_SIZE) as *mut c_void,
                            crate::x86_memory_helpers::virt_to_phys(*(*object).pages.add(i as usize)),
                            attr, PAGE_SHIFT, range.cast(), 0);
                        if error != 0 {
                            kprintf(b"%s: ERROR: mapping %d page of pre-mapped file\n\0".as_ptr().cast(), NAME.as_ptr(), i);
                        }
                        i = i.wrapping_add(1);
                    }
                    if debug(12) { kprintf(b"%s: memobj 0x%lx pre-mapped\n\0".as_ptr().cast(), NAME.as_ptr(), object); }
                } else { populated_mapping = true; }
            }
        }
        // Original successful add-range ownership transfer. Later errors do not
        // roll back or free the published physical pages/memobj as local state.
        p = null_mut();
        object = null_mut();
        ro_vma_mapped = false;
        0
    };

    // Three source-confirmed error repairs: never dereference an absent output
    // range during host rollback, never unlock a write lock not yet acquired,
    // and never unref a hugefile object already destroyed by its real free hook.
    if ro_vma_mapped && (range.is_null() || (*range).straight_start == 0) {
        let _ = policy::set_host_vma_body_result(addr, len, PROT_READ | PROT_WRITE | PROT_EXEC, 1);
    }
    if write_locked {
        // Keep the just-published range alive into the original read phase;
        // dropping writer then reacquiring reader admits a concurrent free.
        downgrade_write_to_reader(addr_of_mut!((*(*thread).vm).memory_range_lock));
    } else {
        // Page-size failure never acquired a writer and owns no range pointer.
        crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(addr_of_mut!((*(*thread).vm).memory_range_lock).cast());
    }
    if error == 0 && !range.is_null() && !(*range).memobj.is_null()
        && (*(*range).memobj.cast::<Memobj>()).flags & MF_XPMEM != 0 {
        error = crate::xpmem_helpers::xpmem_update_process_page_table((*thread).vm.cast(), range.cast());
        if error != 0 {
            kprintf(b"%s: xpmem_update_process_page_table(): vm: %p, range: %lx-%lx failed %d\n\0".as_ptr().cast(),
                NAME.as_ptr(), (*thread).vm, (*range).start, (*range).end, error);
        }
    }
    // No VmRange borrow survives the reader unlock. Population looks up through
    // the real VM/address provider, and return/logging use these scalar snapshots.
    let straight_start = if error == 0 { (*range).straight_start } else { 0 };
    let should_populate = error == 0 && populated_mapping
        && vrflags & VR_PROT_MASK != 0 && straight_start == 0;
    crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(addr_of_mut!((*(*thread).vm).memory_range_lock).cast());
    if should_populate {
        let result = crate::process_helpers::populate_process_memory((*thread).vm, addr as *mut c_void, populate_len);
        if result != 0 {
            kprintf(b"%s: WARNING: populate_process_memory(): vm: %p, addr: %p, len: %d (flags: %s%s) failed %d\n\0".as_ptr().cast(),
                NAME.as_ptr(), (*thread).vm, addr, len as CInt,
                if flags & MAP_POPULATE != 0 { b"MAP_POPULATE \0".as_ptr() } else { b"\0".as_ptr() },
                if flags & MAP_LOCKED != 0 { b"MAP_LOCKED \0".as_ptr() } else { b"\0".as_ptr() }, result);
            // Original Linux-like policy: population failure is ignored. The
            // unlocked range may have changed, so do not invent an unmap here.
        }
    }
    if !p.is_null() && npages > 0 {
        crate::mem_helpers::_ihk_mc_free_pages(p, npages as CInt, IHK_MC_PG_USER,
            SOURCE_FILE.as_ptr().cast_mut().cast(), 6651);
    }
    if !object.is_null() { object_unref(object); }
    if debug(13) {
        kprintf(b"%s: 0x%lx:%8lu, (req: 0x%lx:%lu), prot: %x, flags: %x, fd: %d, off: %lu, error: %ld, addr: 0x%lx\n\0".as_ptr().cast(),
            NAME.as_ptr(), addr, len, addr0, len, prot, flags, fd, off0, error as CLong, addr);
    }
    if error == 0 {
        if straight_start != 0 { straight_start as CLong } else { addr as CLong }
    } else { error as CLong }
}

const _: unsafe extern "C" fn(CULong, SizeT, CInt, CInt, CInt, OffT, CInt, *mut c_void) -> CLong = do_mmap;
