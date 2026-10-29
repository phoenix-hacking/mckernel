// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete supported (non-Fugaku/non-attached-MIC) orchestration proposal. Unselected.
#[cfg(all(f03_do_mmap_supported_candidate, not(enable_fugaku_hacks)))]
mod f03_mmap_whole_v1 {
    use core::ffi::c_void;
    use core::mem::{offset_of, size_of};
    use core::ptr::{addr_of, addr_of_mut, null_mut, read_volatile};

    use crate::abi::{CInt, CLong, CULong, Memobj, OffT, Process, ShmidDs, SizeT, VmRange};
    use crate::debug::Ddebug;

    use super::{
        do_mmap_mckfd_dispatch_body_result, do_mmap_page_size_body_result,
        f03_search_free_space_v1, mmap_base_vrflags, mmap_is_shared,
        mmap_maxprot_to_vrflags, mmap_populated_mapping_result, mmap_prot_denied_result,
        mmap_should_force_straight, mmap_should_set_host_ro, mmap_update_private_maxprot,
        set_host_vma_body_result, syscall_mckfd_lock_bridge, syscall_mckfd_offsets,
        syscall_mckfd_unlock_bridge, MAP_ANONYMOUS, MAP_FIXED, MAP_LOCKED, MAP_POPULATE,
        MAP_SHARED, PAGE_SHIFT, PAGE_SIZE, PROT_EXEC, PROT_READ, PROT_WRITE,
        VR_DEMAND_PAGING, VR_PROT_MASK, f03_do_mmap_smaller_page_v2,
    };

    // Named indices refer to the same genuine C constants, never guessed values.
    const VR_MEMTYPE_MASK: usize = 0;
    const VR_MEMTYPE_UC: usize = 1;
    const VR_AP_USER: usize = 2;
    const MF_HUGETLBFS: usize = 3;
    const MF_DEV_FILE: usize = 4;
    const MF_PREMAP: usize = 5;
    const MF_ZEROFILL: usize = 6;
    const MF_XPMEM: usize = 7;
    const MPOL_NO_STACK: usize = 8;
    const MPOL_SHM_PREMAP: usize = 9;
    const AP_USER: usize = 10;
    const AP_NOWAIT: usize = 11;
    const PG_USER: usize = 12;
    const SHM_DEST: usize = 13;
    const PF_POPULATE: usize = 14;
    const NOPHYS: usize = 15;
    const OBJ_PREFETCH: usize = 16;
    const OBJ_READY: usize = 17;
    const PROFILE_FILE: usize = 18;
    const PROFILE_DEVICE: usize = 19;
    const PROFILE_NO_CONTIG: usize = 20;
    const PROFILE_CONTIG: usize = 21;
    const PROFILE_STRAIGHT: usize = 22;
    const PROFILE_NOT_STRAIGHT: usize = 23;
    const MAP_STACK: usize = 24;
    const VR_PROT_NONE: usize = 25;
    const PAGE_P2ALIGN: usize = 26;

    #[repr(C)]
    struct MemobjFreePrefix {
        free: unsafe extern "C" fn(*mut Memobj),
    }

    unsafe extern "C" {
        static f03_mmap_constants_v1: [CULong; 27];
        static f03_mmap_source_file_v1: i8;
        static f03_mmap_allocate_line_v1: CInt;
        static f03_mmap_free_line_v1: CInt;
        static mut f03_mmap_debug_v1: [Ddebug; 14];
        static mut anon_on_demand: CInt;
        fn kprintf(format: *const i8, ...) -> CInt;
        // Actual preserved C do_munmap transaction; this does not assert its held
        // partial-host-context contract or invent a new endpoint/reference.
        #[link_name = "do_munmap"]
        fn original_do_munmap(address: *mut c_void, length: SizeT, held: CInt) -> CInt;
        // Typed first-memobj prefix of the actual selected Rust refcount provider.
        #[link_name = "memobj_unref"]
        fn original_memobj_unref(object: *mut Memobj) -> CInt;
    }

    macro_rules! debug {
        ($index:expr, $format:expr $(, $value:expr)* $(,)?) => {{
            // SAFETY: Genuine static Ddebug record and original scalar/pointer
            // variadic operands. This conditional preserves debug argument timing.
            unsafe {
                if read_volatile(addr_of!(f03_mmap_debug_v1[$index].line_flags)) >> 24 != 0 {
                    kprintf($format.as_ptr().cast() $(, $value)*);
                }
            }
        }};
    }

    unsafe fn profile(event: usize, length: SizeT) {
        #[cfg(enable_profile)]
        unsafe {
            crate::profile::profile_event_add(f03_mmap_constants_v1[event] as CInt, length as u64);
        }
        #[cfg(not(enable_profile))]
        let _ = (event, length);
    }

    /// Preserve the existing straight-map setup and its original partial failures.
    ///
    /// # Safety
    /// Current process/VM and boot chunk data have their original initialization
    /// lifetime. This retains the old caller's serialization requirement; it does
    /// not manufacture a VM lock, rollback a published range or ACK a host mapping.
    unsafe fn initialize_straight(process: *mut Process, private_data: *mut c_void) {
        // SAFETY: Raw process/VM fields remain live through this synchronous setup.
        unsafe {
            if (*process).straight_map == 0 || !(*process).straight_va.is_null() {
                return;
            }
            let mut first = CULong::MAX;
            let mut last = 0;
            let mut alignment = f03_mmap_constants_v1[PAGE_P2ALIGN] as CInt;
            let mut page_size = PAGE_SIZE as SizeT;
            let chunks = crate::x86_setup::ihk_mc_get_nr_memory_chunks();
            for index in 0..chunks {
                // The genuine chunk provider initializes both fields on valid indices.
                let mut start = 0;
                let mut end = 0;
                let _ = crate::x86_setup::ihk_mc_get_memory_chunk(
                    index, addr_of_mut!(start), addr_of_mut!(end), null_mut(),
                );
                first = first.min(start);
                last = last.max(end);
            }
            kprintf(c"%s: straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n".as_ptr(),
                c"do_mmap".as_ptr(), first, last);
            let error = crate::x86_memory_helpers::arch_get_smaller_page_size(
                null_mut(), last.wrapping_sub(first) as SizeT,
                addr_of_mut!(page_size), addr_of_mut!(alignment),
            );
            if error != 0 {
                kprintf(c"%s: arch_get_smaller_page_size failed: %d\n".as_ptr(),
                    c"do_mmap".as_ptr(), error);
                return;
            }
            // Preserve the original forced 512 MiB choice AFTER the fallible query.
            page_size = 1 << 29;
            alignment = 29 - PAGE_SHIFT as CInt;
            kprintf(c"%s: using page shift: %d, psize: %lu\n".as_ptr(),
                c"do_mmap".as_ptr(), alignment + PAGE_SHIFT as CInt, page_size);
            first &= !(page_size as CULong - 1);
            last = last.wrapping_add(page_size as CULong - 1) & !(page_size as CULong - 1);
            kprintf(c"%s: aligned straight_pa_start: 0x%lx, straight_pa_end: 0x%lx\n".as_ptr(),
                c"do_mmap".as_ptr(), first, last);
            (*process).straight_len = last.wrapping_sub(first) as SizeT;
            let mut start = (*process).straight_va as CULong;
            let error = f03_search_free_space_v1(
                (*process).straight_len, PAGE_SHIFT as CInt + alignment, addr_of_mut!(start),
            );
            (*process).straight_va = start as *mut c_void;
            if error != 0 {
                kprintf(c"%s: search_free_space() failed: %d\n".as_ptr(),
                    c"do_mmap".as_ptr(), error);
                (*process).straight_va = null_mut();
                return;
            }
            debug!(1, b"%s: straight_va: 0x%lx to be used\n\0",
                c"do_mmap".as_ptr(), start);
            let vm = (*process).vm;
            let flags = super::prot_to_vr_flag(PROT_READ | PROT_WRITE);
            let flags = flags | super::vrflag_prot_to_maxprot(flags) | VR_DEMAND_PAGING;
            let mut range = null_mut();
            let error = crate::process_helpers::add_process_memory_range(
                vm, start, start.wrapping_add((*process).straight_len as CULong),
                f03_mmap_constants_v1[NOPHYS], flags, null_mut(), 0,
                PAGE_SHIFT as CInt + alignment, private_data, addr_of_mut!(range),
            );
            if error != 0 {
                kprintf(c"%s: error: adding straight memory range \n".as_ptr(),
                    c"do_mmap".as_ptr());
                (*process).straight_va = null_mut();
                return;
            }
            kprintf(c"%s: straight_va: 0x%lx, range->pgshift: %d, range OK\n".as_ptr(),
                c"do_mmap".as_ptr(), start, (*range).pgshift);
            let attr = crate::x86_memory_helpers::arch_vrflag_to_ptattr(
                (*range).flag, f03_mmap_constants_v1[PF_POPULATE], null_mut(),
            );
            let error = crate::x86_memory_helpers::ihk_mc_pt_set_range(
                (*(*vm).address_space).page_table, vm.cast(), (*range).start as *mut c_void,
                (*range).end as *mut c_void, first, attr, (*range).pgshift, range.cast(), 0,
            );
            if error != 0 {
                kprintf(c"%s: ihk_mc_pt_set_range() failed: %d\n".as_ptr(),
                    c"do_mmap".as_ptr(), error);
                (*process).straight_va = null_mut();
                return;
            }
            (*vm).region.map_end = start.wrapping_add((*process).straight_len as CULong);
            (*process).straight_pa = first;
            kprintf(concat!("%s: straight mapping: 0x%lx:%lu @ 0x%lx, ",
                "psize: %lu, straight_map_threshold: %lu\n\0").as_ptr().cast(),
                c"do_mmap".as_ptr(), start, (*process).straight_len, first, page_size,
                (*process).straight_map_threshold);
        }
    }

    /// Map one complete region using the supported original transaction.
    ///
    /// # Safety
    /// Current thread/process/VM and configured boot data are genuine live objects.
    /// Arguments obey the same aligned user-span/provider contracts as C do_mmap.
    /// Synchronous providers may not retain local output pointers. A successful
    /// add_range supplies a live range under the existing VM lifetime protocol.
    /// The preserved mckfd dispatch and host-mirror providers still require their
    /// separate lifetime/context qualification; this source is not selected yet.
    #[export_name = "do_mmap"]
    pub unsafe extern "C" fn f03_do_mmap_supported_v1(
        addr0: CULong,
        len0: SizeT,
        prot: CInt,
        flags: CInt,
        fd: CInt,
        off0: OffT,
        vrf0: CInt,
        private_data: *mut c_void,
    ) -> CLong {
        // SAFETY: Current CPU-local object and its running thread are provided by
        // the original syscall entry; no extra thread or VM reference is minted.
        let thread = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
        let process = unsafe { (*thread).proc };
        let vm = unsafe { (*thread).vm };
        let lock = unsafe { addr_of_mut!((*vm).memory_range_lock) };
        let mut address = addr0;
        let length = len0;
        let mut populate_length = 0;
        let mut page_alignment = 0;
        let mut page_shift = 0;
        let mut allocation = null_mut();
        let mut pages: CLong = 0;
        let mut object: *mut Memobj = null_mut();
        let mut range: *mut VmRange = null_mut();
        let mut vrflags: CInt = 0;
        let mut populated = false;
        let mut host_ro_established = false;
        let mut write_locked = false;

        debug!(0, b"do_mmap(%lx,%lx,%x,%x,%d,%lx)\n\0",
            addr0, len0, prot, flags, fd, off0);
        if flags & MAP_ANONYMOUS == 0 {
            // SAFETY: Exactly one fully initialized context; original dispatch sees
            // all six registers. Descriptor callback lifetime remains explicit HOLD.
            let result = unsafe {
                let mut context = core::mem::zeroed::<crate::abi::X86UserContext>();
                context.gpr.rdi = addr0;
                context.gpr.rsi = len0 as CULong;
                context.gpr.rdx = prot as CULong;
                context.gpr.r10 = flags as CULong;
                context.gpr.r8 = fd as CULong;
                context.gpr.r9 = off0 as CULong;
                let offsets = syscall_mckfd_offsets();
                let mut handled = 0;
                let result = do_mmap_mckfd_dispatch_body_result(
                    thread.cast(), flags, fd, addr_of_mut!(context).cast(),
                    addr_of_mut!(handled), addr_of!(offsets),
                    offset_of!(crate::abi::Mckfd, mmap_cb),
                    Some(syscall_mckfd_lock_bridge), Some(syscall_mckfd_unlock_bridge),
                );
                (handled, result)
            };
            if result.0 != 0 {
                return result.1;
            }
        }
        crate::x86_memory_helpers::flush_nfo_tlb();
        // SAFETY: Same original straight-map prephase and partial mutation order.
        unsafe { initialize_straight(process, private_data) };

        let mut error = 'mapping: {
            // SAFETY: These local outputs remain live across synchronous callbacks.
            let result = unsafe {
                do_mmap_page_size_body_result(
                    flags, vrf0 as CLong as CULong, (*process).thp_disable, length,
                    addr_of_mut!(page_shift), addr_of_mut!(page_alignment),
                    Some(crate::x86_setup::ihk_mc_get_linux_default_huge_page_shift),
                    Some(f03_do_mmap_smaller_page_v2),
                )
            };
            if result != 0 {
                unsafe {
                    kprintf(c"do_mmap:arch_get_smaller_page_size failed. %d\n".as_ptr(), result);
                }
                break 'mapping result;
            }
            // SAFETY: Genuine VM reader/writer-lock storage has the same 4-byte
            // nominal ABI as the owned Rust lock provider. Track acquisition before
            // any branch can enter cleanup; never unlock an unacquired lock.
            unsafe { crate::lock_helpers::ihk_rwspinlock_write_lock_noirq(lock.cast()) };
            write_locked = true;
            let straight = unsafe { (*process).straight_va as CULong };
            let straight_length = unsafe { (*process).straight_len as CULong };
            if flags & MAP_FIXED != 0 && straight != 0 && address >= straight
                && address.wrapping_add(length as CULong) <= straight.wrapping_add(straight_length)
            {
                unsafe {
                    kprintf(c"%s: can't map MAP_FIXED into straight mapping\n".as_ptr(),
                        c"do_mmap".as_ptr());
                }
                break 'mapping -super::EINVAL;
            }
            if flags & MAP_FIXED != 0 {
                // SAFETY: Existing C transaction receives the real held-lock flag.
                let result = unsafe { original_do_munmap(address as *mut c_void, length, 1) };
                if result != 0 {
                    unsafe {
                        kprintf(c"do_mmap:do_munmap(%lx,%lx) failed. %d\n".as_ptr(),
                            address, length, result);
                    }
                    break 'mapping result;
                }
            } else if flags & MAP_ANONYMOUS != 0 {
                let result = unsafe {
                    f03_search_free_space_v1(
                        length, PAGE_SHIFT as CInt + page_alignment, addr_of_mut!(address),
                    )
                };
                if result != 0 {
                    unsafe {
                        kprintf(c"%s: error: search_free_space(%lx,%lx,%lx) failed. %d\n".as_ptr(),
                            c"do_mmap".as_ptr(), length, PAGE_SHIFT as CInt + page_alignment,
                            address, result);
                    }
                    break 'mapping result;
                }
            }
            // Preserve C int narrowing after the u64 policy helper returns.
            vrflags = unsafe {
                mmap_base_vrflags(prot, flags, vrf0 as CLong as CULong, anon_on_demand) as CInt
            };
            populated = mmap_populated_mapping_result(flags) != 0;
            if populated {
                debug!(2, b"%s: 0x%lx:%lu %s%s|\n\0", c"do_mmap".as_ptr(), address, length,
                    if flags & MAP_POPULATE != 0 { c"|MAP_POPULATE" } else { c"" }.as_ptr(),
                    if flags & MAP_LOCKED != 0 { c"|MAP_LOCKED" } else { c"" }.as_ptr());
            }
            if mmap_should_set_host_ro(flags, prot, 1) != 0 {
                let result = set_host_vma_body_result(address, length, PROT_READ | PROT_EXEC, 1);
                if result != 0 {
                    unsafe { kprintf(c"do_mmap:set_host_vma failed. %d\n".as_ptr(), result) };
                    break 'mapping result;
                }
                // This records successful provider return only, never a new host ACK.
                host_ro_established = true;
            }
            let mut physical: CULong = 0;
            let mut straight_physical: CLong = 0;
            let mut offset: OffT = 0;
            let mut maximum = PROT_READ | PROT_WRITE | PROT_EXEC;
            if flags & MAP_ANONYMOUS == 0 {
                offset = off0;
                let mut result = unsafe {
                    crate::fileobj::fileobj_create(
                        fd, addr_of_mut!(object), addr_of_mut!(maximum), flags, addr0,
                    )
                };
                // SAFETY: A creator-provided path is a live terminated string while
                // its object is retained locally. strncmp follows only that contract.
                unsafe {
                    if !object.is_null() && !(*object).path.is_null()
                        && crate::string::strncmp(
                            (*object).path, c"/dev/shm/ucx_posix".as_ptr(), 18,
                        ) == 0
                    {
                        kprintf(concat!("%s: mmap flags: %lx, path: %s, memobj->flags: %lx, ",
                            "pgshift: %d, p2align: %d -> FIXING page size\n\0").as_ptr().cast(),
                            c"do_mmap".as_ptr(), flags, (*object).path, (*object).flags,
                            page_shift, page_alignment);
                        page_shift = PAGE_SHIFT as CInt;
                        page_alignment = f03_mmap_constants_v1[PAGE_P2ALIGN] as CInt;
                        populated = true;
                    }
                    if result == 0 {
                        profile(PROFILE_FILE, length);
                    }
                }
                if result == -super::ESRCH {
                    debug!(3, b"do_mmap:hit non VREG\n\0");
                    // Original non-Fugaku device mapping always chooses uncached.
                    unsafe {
                        vrflags &= !(f03_mmap_constants_v1[VR_MEMTYPE_MASK] as CInt);
                        vrflags |= f03_mmap_constants_v1[VR_MEMTYPE_UC] as CInt;
                        result = crate::devobj::devobj_create(
                            fd, length, offset, addr_of_mut!(object), addr_of_mut!(maximum),
                            prot, flags & (MAP_POPULATE | MAP_LOCKED),
                        );
                        if result == 0 {
                            profile(PROFILE_DEVICE, length);
                            if !(*object).path.is_null()
                                && (crate::string::strncmp(
                                    c"/tmp/ompi.".as_ptr(), (*object).path, 10,
                                ) == 0 || crate::string::strncmp(
                                    c"/dev/shm/".as_ptr(), (*object).path, 9,
                                ) == 0)
                            {
                                page_shift = PAGE_SHIFT as CInt;
                                page_alignment = f03_mmap_constants_v1[PAGE_P2ALIGN] as CInt;
                                populated = true;
                            }
                        }
                    }
                }
                if result != 0 {
                    unsafe {
                        kprintf(c"%s: error: file mapping failed, fd: %d, error: %d\n".as_ptr(),
                            c"do_mmap".as_ptr(), fd, result);
                    }
                    break 'mapping result;
                }
                unsafe {
                    if !object.is_null() && (*object).flags & f03_mmap_constants_v1[MF_HUGETLBFS]
                        as u32 != 0
                    {
                        result = crate::hugefileobj::hugefileobj_create(
                            object, length, offset, addr_of_mut!(page_shift), addr0,
                        );
                        if result != 0 {
                            // Real memobj_ops.free consumes the locally owned node.
                            // Clear ownership before common cleanup; never unref it twice.
                            let free = (*(*object).ops.cast::<MemobjFreePrefix>()).free;
                            free(object);
                            object = null_mut();
                            kprintf(concat!("%s: error creating hugetlbfs memobj, ",
                                "fd: %d, error: %d\n\0").as_ptr().cast(),
                                c"do_mmap".as_ptr(), fd, result);
                            break 'mapping result;
                        }
                        page_alignment = page_shift - PAGE_SHIFT as CInt;
                    }
                }
                if flags & MAP_FIXED == 0 {
                    result = unsafe {
                        f03_search_free_space_v1(
                            length, PAGE_SHIFT as CInt + page_alignment, addr_of_mut!(address),
                        )
                    };
                }
                if result != 0 {
                    unsafe {
                        kprintf(c"do_mmap:search_free_space(%lx,%lx,%d) failed. %d\n".as_ptr(),
                            length, (*vm).region.map_end, page_alignment, result);
                    }
                    break 'mapping result;
                }
                if mmap_should_set_host_ro(flags, prot, 0) != 0 {
                    result = set_host_vma_body_result(address, length, PROT_READ | PROT_EXEC, 1);
                    if result != 0 {
                        unsafe { kprintf(c"do_mmap:set_host_vma failed. %d\n".as_ptr(), result) };
                        break 'mapping result;
                    }
                    host_ro_established = true;
                }
                unsafe {
                    if (*object).flags & f03_mmap_constants_v1[MF_HUGETLBFS] as u32 != 0 {
                        debug!(4, concat!("Created hugefileobj %p (%d:%x %llx-%llx, ",
                            "fd %d, pgshift %d)\n\0").as_bytes(),
                            object, length, offset, address,
                            address.wrapping_add(length as CULong), fd, page_shift);
                    } else if (*object).flags & f03_mmap_constants_v1[MF_DEV_FILE] as u32 != 0 {
                        debug!(5, b"%s: device fd: %d off: %lu mapping at %p - %p\n\0",
                            c"do_mmap".as_ptr(), fd, offset, address as *mut c_void,
                            address.wrapping_add(length as CULong) as *mut c_void);
                    }
                }
            } else if vrflags as CULong & VR_DEMAND_PAGING == 0 && flags & MAP_SHARED == 0
                && vrflags as CULong & VR_PROT_MASK
                    != unsafe { f03_mmap_constants_v1[VR_PROT_NONE] }
            {
                pages = (length >> PAGE_SHIFT) as CLong;
                let user = unsafe {
                    (flags & f03_mmap_constants_v1[MAP_STACK] as CInt == 0
                        && length >= (*process).mpol_threshold)
                        || (flags & f03_mmap_constants_v1[MAP_STACK] as CInt != 0
                            && (*process).mpol_flags & f03_mmap_constants_v1[MPOL_NO_STACK] == 0)
                };
                unsafe {
                    let allocation_flags = if user { f03_mmap_constants_v1[AP_USER] } else { 0 };
                    if user {
                        vrflags |= f03_mmap_constants_v1[VR_AP_USER] as CInt;
                    }
                    allocation = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
                        pages as CInt, page_alignment,
                        f03_mmap_constants_v1[AP_NOWAIT] | allocation_flags, -1,
                        f03_mmap_constants_v1[PG_USER] as CInt, addr0,
                        addr_of!(f03_mmap_source_file_v1).cast_mut(), f03_mmap_allocate_line_v1,
                    );
                    if allocation.is_null() {
                        debug!(6, concat!("%s: warning: failed to allocate %d contiguous pages ",
                            " (bytes: %lu, pgshift: %d), enabling demand paging\n\0").as_bytes(),
                            c"do_mmap".as_ptr(), pages,
                            pages.wrapping_mul(PAGE_SIZE as CLong), page_alignment);
                        vrflags |= VR_DEMAND_PAGING as CInt;
                        populated = false;
                        profile(PROFILE_NO_CONTIG, length);
                        let result = crate::zeroobj::zeroobj_create(addr_of_mut!(object));
                        if result != 0 {
                            kprintf(c"%s: zeroobj_create failed, error: %d\n".as_ptr(),
                                c"do_mmap".as_ptr(), result);
                            break 'mapping result;
                        }
                    } else {
                        profile(PROFILE_CONTIG, length);
                        debug!(7, concat!("%s: 0x%x:%lu MAP_ANONYMOUS ",
                            "allocated %d pages, p2align: %lx\n\0").as_bytes(),
                            c"do_mmap".as_ptr(), address, length, pages, page_alignment);
                        physical = crate::x86_memory_helpers::virt_to_phys(allocation);
                    }
                }
            } else if mmap_is_shared(flags) != 0 {
                debug!(8, b"%s: MAP_SHARED,flags=%x,len=%ld\n\0",
                    c"do_mmap".as_ptr(), flags, length);
                // SAFETY: Complete zero initialization, followed by the same three
                // explicit fields; the real creator retains no stack descriptor.
                unsafe {
                    let mut descriptor = core::mem::zeroed::<ShmidDs>();
                    descriptor.shm_segsz = length;
                    descriptor.shm_perm.mode = f03_mmap_constants_v1[SHM_DEST] as u16;
                    descriptor.init_pgshift = PAGE_SHIFT as CInt + page_alignment;
                    let result = crate::shmobj::shmobj_create(
                        addr_of_mut!(descriptor), addr_of_mut!(object),
                    );
                    if result != 0 {
                        kprintf(c"do_mmap:shmobj_create failed. %d\n".as_ptr(), result);
                        break 'mapping result;
                    }
                }
            } else {
                debug!(9, b"%s: anon&demand-paging\n\0", c"do_mmap".as_ptr());
                let result = unsafe { crate::zeroobj::zeroobj_create(addr_of_mut!(object)) };
                if result != 0 {
                    unsafe { kprintf(c"do_mmap:zeroobj_create failed. %d\n".as_ptr(), result) };
                    break 'mapping result;
                }
            }

            maximum = mmap_update_private_maxprot(flags, maximum);
            let mut denied = 0;
            let result = unsafe { mmap_prot_denied_result(prot, maximum, addr_of_mut!(denied)) };
            if result != 0 {
                unsafe {
                    kprintf(c"do_mmap:denied %x. %x %x\n".as_ptr(), denied, prot, maximum);
                }
                break 'mapping result;
            }
            vrflags |= mmap_maxprot_to_vrflags(maximum) as CInt;
            if unsafe {
                mmap_should_force_straight(
                    flags, (*process).straight_map, physical, length,
                    (*process).straight_map_threshold,
                )
            } != 0 {
                debug!(10, b"%s: range 0x%lx:%lu will be straight, addding VR_DEMAND\n\0",
                    c"do_mmap".as_ptr(), address, length);
                vrflags |= VR_DEMAND_PAGING as CInt;
                straight_physical = physical as CLong;
                physical = 0;
                unsafe { profile(PROFILE_STRAIGHT, length) };
            } else if flags & MAP_ANONYMOUS != 0 && unsafe { (*process).straight_map } != 0
                && flags & MAP_FIXED == 0 && physical != 0
            {
                #[cfg(enable_profile)]
                unsafe {
                    if (*process).profile != 0 {
                        kprintf(c"%s: contiguous but not straight? len: %lu\n".as_ptr(),
                            c"do_mmap".as_ptr(), length);
                    }
                    profile(PROFILE_NOT_STRAIGHT, length);
                }
            }
            let result = unsafe {
                crate::process_helpers::add_process_memory_range(
                    vm, address, address.wrapping_add(length as CULong), physical,
                    vrflags as CLong as CULong, object.cast(), offset, page_shift,
                    private_data, addr_of_mut!(range),
                )
            };
            if result != 0 {
                unsafe {
                    kprintf(concat!("%s: add_process_memory_range failed for 0x%lx:%lu",
                        " flags: %lx, vrflags: %lx, pgshift: %d, error: %d\n\0").as_ptr().cast(),
                        c"do_mmap".as_ptr(), address, address.wrapping_add(length as CULong),
                        flags, vrflags, page_shift, result);
                }
                break 'mapping result;
            }
            // SAFETY: Successful add_range returned the actual linked range. Its
            // VM/lock ownership and optional straight allocation remain genuine.
            unsafe {
                if straight_physical != 0 {
                    (*range).straight_start = ((*process).straight_va as CULong)
                        .wrapping_add(
                            (straight_physical as CULong).wrapping_sub((*process).straight_pa),
                        );
                    debug!(11, b"%s: range 0x%lx:%lu is straight starting at 0x%lx\n\0",
                        c"do_mmap".as_ptr(), address, length, (*range).straight_start);
                    let mapping = crate::x86_memory_helpers::phys_to_virt(
                        straight_physical as CULong,
                    );
                    crate::string::memset(mapping, 0, length);
                }
                populate_length = if object.is_null() {
                    length
                } else {
                    length.min((*object).size)
                };
                if flags & MAP_ANONYMOUS == 0 {
                    if crate::atomic_helpers::atomic_cmpxchg4(
                        addr_of_mut!((*object).status),
                        f03_mmap_constants_v1[OBJ_PREFETCH] as u32,
                        f03_mmap_constants_v1[OBJ_READY] as u32,
                    ) == f03_mmap_constants_v1[OBJ_PREFETCH]
                    {
                        populated = true;
                    }
                    if (*object).flags & f03_mmap_constants_v1[MF_PREMAP] as u32 != 0
                        && (*process).mpol_flags & f03_mmap_constants_v1[MPOL_SHM_PREMAP] != 0
                    {
                        if (*object).flags & f03_mmap_constants_v1[MF_ZEROFILL] as u32 != 0 {
                            let attr = crate::x86_memory_helpers::arch_vrflag_to_ptattr(
                                (*range).flag, f03_mmap_constants_v1[PF_POPULATE],
                                null_mut(),
                            );
                            for index in 0..(*object).nr_pages {
                                let start = (*range).start
                                    .wrapping_add((index as CULong).wrapping_mul(PAGE_SIZE));
                                let page = (*object).pages.add(index as usize).read();
                                let physical = crate::x86_memory_helpers::virt_to_phys(page);
                                let result = crate::x86_memory_helpers::ihk_mc_pt_set_range(
                                    (*(*vm).address_space).page_table, vm.cast(),
                                    start as *mut c_void,
                                    start.wrapping_add(PAGE_SIZE) as *mut c_void,
                                    physical, attr, PAGE_SHIFT as CInt, range.cast(), 0,
                                );
                                if result != 0 {
                                    // Retain original per-page logging/continue policy.
                                    kprintf(
                                        c"%s: ERROR: mapping %d page of pre-mapped file\n".as_ptr(),
                                        c"do_mmap".as_ptr(), index);
                                }
                            }
                            debug!(12, b"%s: memobj 0x%lx pre-mapped\n\0",
                                c"do_mmap".as_ptr(), object);
                        } else {
                            populated = true;
                        }
                    }
                }
            }
            // Ownership has moved into the successful range, as in original C.
            allocation = null_mut();
            object = null_mut();
            host_ro_established = false;
            break 'mapping 0;
        };

        // Root-authorized defined-failure extension: no absent-range dereference.
        // Only a successful earlier host-mirror return creates this unwind need.
        // This neither fabricates ACK nor upgrades the partial-context provider.
        let straight_return = unsafe {
            if range.is_null() { 0 } else { (*range).straight_start }
        };
        let has_straight_range = straight_return != 0;
        if host_ro_established && !has_straight_range {
            let _ = set_host_vma_body_result(
                address, length, PROT_READ | PROT_WRITE | PROT_EXEC, 1,
            );
        }
        if write_locked {
            // SAFETY: The only matching acquired write guard, released exactly once.
            unsafe { crate::lock_helpers::ihk_rwspinlock_write_unlock_noirq(lock.cast()) };
        }
        // Retain original reader-lock phase and XPMEM error precedence after unlock.
        unsafe { crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(lock.cast()) };
        unsafe {
            if error == 0 && !range.is_null() && !(*range).memobj.is_null() {
                let range_object = (*range).memobj.cast::<Memobj>();
                if (*range_object).flags & f03_mmap_constants_v1[MF_XPMEM] as u32 != 0 {
                    error = crate::xpmem_helpers::xpmem_update_process_page_table(
                        vm.cast(), range.cast(),
                    );
                    if error != 0 {
                        kprintf(concat!("%s: xpmem_update_process_page_table(): ",
                            "vm: %p, range: %lx-%lx failed %d\n\0").as_ptr().cast(),
                            c"do_mmap".as_ptr(), vm, (*range).start, (*range).end, error);
                    }
                }
            }
        }
        unsafe { crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock.cast()) };
        // The inherited source accesses the successful range after reader unlock.
        // Its cross-thread pin/VM protocol remains a genuine explicit HOLD.
        if error == 0 && populated && vrflags as CULong & VR_PROT_MASK
                    != unsafe { f03_mmap_constants_v1[VR_PROT_NONE] }
            && !has_straight_range
        {
            let result = unsafe {
                crate::process_helpers::populate_process_memory(
                    vm, address as *mut c_void, populate_length,
                )
            };
            if result != 0 {
                unsafe {
                    kprintf(concat!("%s: WARNING: populate_process_memory(): ",
                        "vm: %p, addr: %p, len: %d (flags: %s%s) failed %d\n\0").as_ptr().cast(),
                        c"do_mmap".as_ptr(), vm, address as *mut c_void, length,
                        if flags & MAP_POPULATE != 0 {
                            c"MAP_POPULATE "
                        } else { c"" }.as_ptr(),
                        if flags & MAP_LOCKED != 0 {
                            c"MAP_LOCKED "
                        } else { c"" }.as_ptr(), result);
                }
                // Preserve the original Linux-like ignored population failure policy.
                // No rollback or new success acknowledgement is invented.
                error = 0;
            }
        }
        unsafe {
            if !allocation.is_null() && pages > 0 {
                crate::mem_helpers::_ihk_mc_free_pages(
                    allocation, pages as CInt, f03_mmap_constants_v1[PG_USER] as CInt,
                    addr_of!(f03_mmap_source_file_v1).cast_mut(), f03_mmap_free_line_v1,
                );
            }
            if !object.is_null() {
                let _ = original_memobj_unref(object);
            }
        }
        debug!(13, concat!("%s: 0x%lx:%8lu, (req: 0x%lx:%lu), prot: %x, flags: %x, ",
            "fd: %d, off: %lu, error: %ld, addr: 0x%lx\n\0").as_bytes(),
            c"do_mmap".as_ptr(), address, length, addr0, len0, prot, flags,
            fd, off0, error, address);
        if error != 0 {
            error as CLong
        } else if has_straight_range {
            // No range dereference is needed after releasing the reader guard.
            // A scalar copy was taken while the write guard still protected it.
            straight_return as CLong
        } else {
            address as CLong
        }
    }

    // Compiler-only real-layout witness, no runtime getter or ownership claim.
    #[no_mangle]
    #[used]
    pub static f03_do_mmap_Rust_ABI_v1: [CULong; 52] = [
        size_of::<crate::abi::Thread>() as CULong,
        core::mem::align_of::<crate::abi::Thread>() as CULong,
        offset_of!(crate::abi::Thread, proc) as CULong,
        offset_of!(crate::abi::Thread, vm) as CULong,
        size_of::<crate::abi::Process>() as CULong,
        core::mem::align_of::<crate::abi::Process>() as CULong,
        offset_of!(crate::abi::Process, vm) as CULong,
        offset_of!(crate::abi::Process, straight_map) as CULong,
        offset_of!(crate::abi::Process, straight_va) as CULong,
        offset_of!(crate::abi::Process, straight_len) as CULong,
        offset_of!(crate::abi::Process, straight_pa) as CULong,
        offset_of!(crate::abi::Process, straight_map_threshold) as CULong,
        offset_of!(crate::abi::Process, thp_disable) as CULong,
        offset_of!(crate::abi::Process, mpol_flags) as CULong,
        offset_of!(crate::abi::Process, mpol_threshold) as CULong,
        offset_of!(crate::abi::Process, profile) as CULong,
        size_of::<crate::abi::ProcessVm>() as CULong,
        core::mem::align_of::<crate::abi::ProcessVm>() as CULong,
        offset_of!(crate::abi::ProcessVm, address_space) as CULong,
        offset_of!(crate::abi::ProcessVm, region) as CULong,
        offset_of!(crate::abi::ProcessVm, memory_range_lock) as CULong,
        size_of::<crate::abi::VmRegions>() as CULong,
        core::mem::align_of::<crate::abi::VmRegions>() as CULong,
        offset_of!(crate::abi::VmRegions, map_end) as CULong,
        size_of::<crate::abi::AddressSpace>() as CULong,
        core::mem::align_of::<crate::abi::AddressSpace>() as CULong,
        offset_of!(crate::abi::AddressSpace, page_table) as CULong,
        size_of::<crate::abi::VmRange>() as CULong,
        core::mem::align_of::<crate::abi::VmRange>() as CULong,
        offset_of!(crate::abi::VmRange, start) as CULong,
        offset_of!(crate::abi::VmRange, end) as CULong,
        offset_of!(crate::abi::VmRange, flag) as CULong,
        offset_of!(crate::abi::VmRange, straight_start) as CULong,
        offset_of!(crate::abi::VmRange, memobj) as CULong,
        offset_of!(crate::abi::VmRange, pgshift) as CULong,
        size_of::<crate::abi::Memobj>() as CULong,
        core::mem::align_of::<crate::abi::Memobj>() as CULong,
        offset_of!(crate::abi::Memobj, ops) as CULong,
        offset_of!(crate::abi::Memobj, flags) as CULong,
        offset_of!(crate::abi::Memobj, status) as CULong,
        offset_of!(crate::abi::Memobj, size) as CULong,
        offset_of!(crate::abi::Memobj, pages) as CULong,
        offset_of!(crate::abi::Memobj, nr_pages) as CULong,
        offset_of!(crate::abi::Memobj, path) as CULong,
        size_of::<crate::abi::ShmidDs>() as CULong,
        core::mem::align_of::<crate::abi::ShmidDs>() as CULong,
        offset_of!(crate::abi::ShmidDs, shm_perm) as CULong,
        offset_of!(crate::abi::ShmidDs, shm_segsz) as CULong,
        offset_of!(crate::abi::ShmidDs, init_pgshift) as CULong,
        size_of::<crate::abi::IpcPerm>() as CULong,
        core::mem::align_of::<crate::abi::IpcPerm>() as CULong,
        offset_of!(crate::abi::IpcPerm, mode) as CULong,
    ];
}
