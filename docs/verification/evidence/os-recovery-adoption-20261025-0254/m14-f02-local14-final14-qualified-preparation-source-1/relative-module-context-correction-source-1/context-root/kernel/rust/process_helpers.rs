use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{copy_nonoverlapping, null_mut, write_volatile};
use core::sync::atomic::{AtomicI32, AtomicUsize, Ordering};

use crate::abi::{
    AbiListHead, AddressSpace, CInt, CLong, CULong, CpuLocalVar, CpuSet, IhkAtomic, IhkSpinlock,
    Mckfd, McsRwlockLock, Memobj, OffT, Process, ProcessHash, ProcessVm, ProgramLoadDesc, RLimit,
    ResourceSet, SigCommon, SigPending, SigStack, SizeT, Thread, ThreadHash, VmRange,
    VmRangeNumaPolicy, Waitq, AUXV_LEN, CPU_SET_MAX_CPUS, MCK_RLIM_MAX, PROCESS_HASH_SIZE,
    PROCESS_NUMA_MASK_BITS, VM_RANGE_CACHE_SIZE,
};
use crate::lock_helpers::McsRwlockNodeIrqsave;
use crate::page_alloc::IhkMcNumaNode;
use crate::rbtree::{
    rb_erase, rb_first, rb_insert_color, rb_link_node, rb_next, rb_prev, RbNode, RbRoot,
};

unsafe extern "C" {
    static mut process_vm_range_insert_debug: crate::debug::Ddebug;
    static process_dump_tree_enabled: CInt;
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn ihk_rwspinlock_init(lock: *mut c_void);
    fn ihk_rwspinlock_read_lock_noirq(lock: *mut c_void);
    fn ihk_rwspinlock_read_unlock_noirq(lock: *mut c_void);
    fn ihk_rwspinlock_write_lock_noirq(lock: *mut c_void);
    fn ihk_rwspinlock_write_unlock_noirq(lock: *mut c_void);
    fn ihk_mc_pt_create(flags: CULong) -> *mut c_void;
    fn mcs_rwlock_init(lock: *mut McsRwlockLock);
    fn __mcs_rwlock_writer_lock_noirq(lock: *mut McsRwlockLock, node: *mut c_void);
    fn __mcs_rwlock_writer_unlock_noirq(lock: *mut McsRwlockLock, node: *mut c_void);
    fn waitq_init(waitq: *mut Waitq);
    fn waitq_prepare_to_wait(waitq: *mut Waitq, entry: *mut c_void, state: CInt);
    fn waitq_finish_wait(waitq: *mut Waitq, entry: *mut c_void);
    fn ihk_mc_get_nr_numa_nodes() -> CInt;
    fn memobj_ref(obj: *mut Memobj) -> CInt;
    fn memobj_unref(obj: *mut Memobj) -> CInt;
    #[link_name = "num_processors"]
    static mut PROCESS_NUM_PROCESSORS: CInt;
    #[link_name = "resource_set_list"]
    static mut PROCESS_RESOURCE_SET_LIST: AbiListHead;
    #[link_name = "resource_set_lock"]
    static mut PROCESS_RESOURCE_SET_LOCK: McsRwlockLock;
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn ihk_mc_get_processor_id() -> CInt;
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn ihk_mc_get_numa_node_by_distance(i: CInt) -> *mut IhkMcNumaNode;
    fn ihk_numa_zero_free_pages(node: *mut IhkMcNumaNode);
    fn cpu_pause();
    fn ihk_mc_get_vector(vector_key: CInt) -> CInt;
    fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt;
    fn schedule();
    fn get_cpu_local_var(cpu_id: CInt) -> *mut CpuLocalVar;
    fn waitq_wakeup(waitq: *mut Waitq);
    fn hassigpending(thread: *mut Thread) -> *mut c_void;
    fn reset_cputime();
    fn rusage_num_threads_inc();
    fn xchg4(ptr: *mut CInt, value: CInt) -> CInt;
    fn set_timer(runq_locked: CInt);
    fn procfs_create_thread(thread: *mut Thread);
    fn procfs_delete_thread(thread: *mut Thread);
    fn flush_nfo_tlb_mm(vm: *mut ProcessVm);
    fn save_fp_regs(thread: *mut c_void) -> CInt;
    fn panic(msg: *const i8) -> !;
    fn process_alloc_bridge(size: CULong, flags: CULong) -> *mut c_void;
    fn process_free_all_ranges_bridge(vm: *mut c_void);
    fn process_free_vm_bridge(vm: *mut c_void);
    fn process_init_process_public_bridge(proc: *mut c_void, parent: *mut c_void) -> CInt;
    fn process_hold_thread_warn_bridge(thread: *mut c_void);
    fn process_optional_free_bridge(ptr: *mut c_void);
    fn process_policy_free_bridge(policy: *mut c_void);
    fn process_proc_init_panic_bridge();
    fn process_pt_destroy_bridge(page_table: *mut c_void);
    fn process_release_address_space_action_bridge(asp: *mut c_void);
    fn process_release_profile_bridge(proc: *mut c_void);
    fn process_free_thread_pages_bridge(thread: *mut c_void);
    fn process_mckfd_free_bridge(fdp: *mut c_void);
    fn process_mcs_writer_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_writer_unlock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_reader_lock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_mcs_reader_unlock_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_ptrace_mcs_lock_noirq_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_ptrace_mcs_unlock_noirq_bridge(lock_addr: CULong, node: *mut c_void);
    fn process_ptrace_alloc_debugreg_bridge(thread: *mut c_void) -> CInt;
    fn process_ptrace_clear_single_step_bridge(thread: *mut c_void);
    fn process_ptrace_hold_thread_bridge(thread: *mut c_void);
    fn process_ptrace_traceme_log_bridge(event: CInt, pid: CInt, value: CULong, error: CInt);
    fn process_hold_thread_bridge(thread: *mut c_void);
    fn process_default_ncpus_bridge() -> CInt;
    fn process_create_cpu_log_bridge(event: CInt, pid: CInt, cpu: CInt);
    fn process_create_thread_alloc_pages_bridge(npages: CInt, flags: CULong) -> *mut c_void;
    fn process_create_thread_address_space_bridge(nslots: CInt) -> *mut c_void;
    fn process_create_thread_release_address_space_bridge(asp: *mut c_void);
    fn process_create_thread_init_process_bridge(proc: *mut c_void, parent: *mut c_void) -> CInt;
    fn process_create_thread_init_vm_bridge(
        owner: *mut c_void,
        asp: *mut c_void,
        vm: *mut c_void,
    ) -> CInt;
    fn process_create_thread_init_user_bridge(
        thread: *mut c_void,
        stack_top: CULong,
        user_pc: CULong,
        user_sp: CULong,
    );
    fn process_memset_smp_phys_to_virt_bridge(phys: CULong) -> *mut c_void;
    fn process_memset_smp_memset_bridge(addr: *mut c_void, value: CInt, len: SizeT);
    fn process_memset_smp_log_bridge(
        event: CInt,
        cpu_index: CInt,
        nr_cpus: CInt,
        phys: CULong,
        len: SizeT,
        start: CULong,
        end: CULong,
    );
    fn process_memset_smp_virt_to_phys_bridge(addr: *mut c_void) -> CULong;
    fn process_memset_smp_call_bridge(
        cpu_set: *mut c_void,
        handler: *mut c_void,
        arg: *mut c_void,
    ) -> CInt;
    fn process_destroy_thread_release_tid_bridge(proc: *mut c_void, thread: *mut c_void);
    fn process_destroy_thread_replace_tid_bridge(
        proc: *mut c_void,
        thread: *mut c_void,
        new_tid: CInt,
    );
    fn release_fp_regs(thread: *mut c_void);
    fn process_release_thread_profile_bridge(thread: *mut c_void, proc: *mut c_void);
    fn process_vm_init_numa_log_bridge(numa_id: CInt);
    fn process_sched_init_context_bridge(thread: *mut c_void);
    fn process_sched_timer_init_bridge(cpu: CInt);
    fn process_access_ok_log_bridge(
        vm: *mut ProcessVm,
        verify_type: CInt,
        addr: CULong,
        len: SizeT,
        rc: CInt,
    );
    fn process_free_range_noirq_lock_bridge(lock_addr: CULong);
    fn process_free_range_noirq_unlock_bridge(lock_addr: CULong);
    fn process_remove_region_clear_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
    ) -> CInt;
    fn process_remove_region_log_bridge(vm: *mut ProcessVm, start: CULong, end: CULong);
    fn process_remove_range_split_bridge(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: CULong,
        splitp: *mut *mut VmRange,
    ) -> CInt;
    fn process_remove_range_xpmem_bridge(vm: *mut ProcessVm, range: *mut VmRange);
    fn process_remove_range_log_bridge(
        event: CInt,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
        range: *mut VmRange,
        error: CInt,
    );
    fn process_normal_fault_range_bridge(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        fault_addr: CULong,
        reason: CULong,
    ) -> CInt;
    fn process_populate_warn_bridge(
        vm: *mut ProcessVm,
        addr: CULong,
        reason: CULong,
        off: CULong,
        len: SizeT,
        error: CInt,
    );
    fn preempt_enable();
    fn preempt_disable();
    static mut process_remap_one_page_entry_debug: crate::debug::Ddebug;
    static mut process_remap_one_page_rss_debug: crate::debug::Ddebug;
    static mut process_remap_one_page_exit_debug: crate::debug::Ddebug;
    static process_remap_free_file: *const i8;
    static process_remap_free_line: CInt;
    fn phys_to_page(phys: CULong) -> *mut crate::page_helpers::Page;
    static mut process_sync_one_page_entry_debug: crate::debug::Ddebug;
    static mut process_sync_one_page_exit_debug: crate::debug::Ddebug;
    fn process_visit_pte_range_bridge(
        page_table: *mut c_void,
        start: CULong,
        end: CULong,
        pgshift: CInt,
        flags: CInt,
        visit_fn: *mut c_void,
        arg: *mut c_void,
    ) -> CInt;
    fn process_remap_range_log_bridge(
        event: CInt,
        vm: *mut ProcessVm,
        range: *mut VmRange,
        start: CULong,
        end: CULong,
        off: OffT,
        old_pgshift: CInt,
        error: CInt,
    );

    fn process_free_range_pt_free_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
        memobj: *mut c_void,
    ) -> CInt;
    fn process_invalidate_range_log_bridge(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        start: CULong,
        end: CULong,
        error: CInt,
    );
    fn process_pte_is_null_bridge(ptep: *mut c_void) -> CInt;
    fn process_pte_is_fileoff_bridge(ptep: *mut c_void, pgsize: SizeT) -> CInt;
    fn process_phys_to_page_bridge(phys: CULong) -> *mut c_void;
    fn process_page_offset_bridge(page: *mut c_void) -> OffT;
    fn process_pte_make_fileoff_bridge(off: OffT, pgsize: SizeT, ptep: *mut c_void);
    fn process_pte_xchg_bridge(ptep: *mut c_void, valp: *mut c_void);
    fn process_flush_tlb_single_bridge(addr: CULong);
    fn process_pgsize_to_tbllv_bridge(pgsize: SizeT) -> CInt;
    fn process_tbllv_to_contpgsize_bridge(level: CInt) -> SizeT;
    fn process_page_unmap_bridge(page: *mut c_void) -> CInt;
    fn process_panic_bridge(message: *const i8);
    fn process_memobj_invalidate_page_bridge(
        memobj: *mut Memobj,
        phys: CULong,
        pgsize: SizeT,
    ) -> CInt;
    fn process_invalidate_one_page_log_bridge(
        arg0: *mut c_void,
        page_table: *mut c_void,
        ptep: *mut c_void,
        pte_value: CULong,
        pgaddr: *mut c_void,
        pgshift: CInt,
        error: CInt,
    );
    fn process_memory_range_free_log_bridge(vm: *mut c_void, range: *mut c_void, error: CInt);
    fn process_flush_memory_log_bridge(vm: *mut c_void, range: *mut c_void, error: CInt);
    fn process_flush_memory_debug_bridge(vm: *mut c_void, event: CInt);
    fn process_range_public_log_bridge(
        event: CInt,
        vm: *mut c_void,
        range: *mut VmRange,
        start: CULong,
        end: CULong,
        error: CInt,
    );
    fn process_change_prot_attr_bridge(flag: CULong, fault: CULong, ptep: *mut c_void) -> CULong;
    fn process_change_prot_pt_change_bridge(
        page_table: *mut c_void,
        start: CULong,
        end: CULong,
        clrattr: CULong,
        setattr: CULong,
    ) -> CInt;
    fn process_change_prot_public_log_bridge(
        event: CInt,
        vm: *mut c_void,
        range: *mut VmRange,
        protflag: CULong,
        error: CInt,
    );
    fn process_update_page_table_attr_bridge(
        flag: CULong,
        fault: CULong,
        ptep: *mut c_void,
    ) -> CULong;
    fn process_update_page_table_set_range_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
        phys: CULong,
        attr: CULong,
        pgshift: CInt,
        range: *mut VmRange,
        flags: CInt,
    ) -> CInt;
    fn process_update_page_table_log_bridge(error: CInt);
    fn process_add_range_alloc_bridge(size: CULong) -> *mut VmRange;
    fn process_add_range_free_bridge(range: *mut VmRange);
    fn process_add_range_insert_bridge(vm: *mut c_void, range: *mut VmRange) -> CInt;
    fn process_add_range_update_bridge(
        vm: *mut c_void,
        range: *mut VmRange,
        phys: CULong,
        attr: CULong,
    ) -> CInt;
    fn process_add_range_remove_bridge(vm: *mut c_void, start: CULong, end: CULong);
    fn process_add_range_mark_xpmem_bridge(range: *mut VmRange);
    fn process_add_range_memclear_bridge(phys: CULong, bytes: CULong);
    fn process_add_range_log_bridge(event: CInt, rc: CInt, start: CULong, end: CULong);
    fn process_split_range_pt_split_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: *mut c_void,
    ) -> CInt;
    fn process_split_range_pt_log_bridge(error: CInt);
    fn process_split_shm_lookup_page_bridge(
        obj: *mut c_void,
        off: OffT,
        p2align: CInt,
        physp: *mut CULong,
        pflag: *mut CULong,
    ) -> CInt;
    fn process_split_shm_phys_to_page_bridge(phys: CULong) -> *mut c_void;
    fn process_split_shm_update_page_bridge(
        obj: *mut c_void,
        page_table: *mut c_void,
        page: *mut c_void,
        vaddr: *mut c_void,
    ) -> CInt;
    fn process_split_shm_log_bridge(event: CInt, error: CInt);
    fn process_split_page_pgshift_offset_bridge() -> CULong;
    fn process_split_range_alloc_bridge(size: CULong, flags: CULong) -> *mut VmRange;
    fn process_split_range_alloc_log_bridge(
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: CULong,
        splitp: *mut c_void,
    );
    fn process_split_range_insert_bridge(vm: *mut c_void, range: *mut VmRange) -> CInt;
    fn process_split_range_publish_log_bridge(error: CInt);
    fn process_split_range_public_log_bridge(
        event: CInt,
        vm: *mut ProcessVm,
        range: *mut VmRange,
        addr: CULong,
        splitp: *mut *mut VmRange,
        newrange: *mut VmRange,
        error: CInt,
    );
    #[cfg(enable_tofu)]
    fn process_split_range_tofu_init_bridge(range: *mut VmRange);
    #[cfg(enable_tofu)]
    fn process_split_range_tofu_split_bridge(
        vm: *mut ProcessVm,
        range_low: *mut VmRange,
        range_high: *mut VmRange,
        addr: CULong,
    );
    fn process_range_kfree_bridge(range: *mut VmRange);
    fn process_join_range_log_bridge(
        event: CInt,
        vm: *mut ProcessVm,
        surviving: *mut VmRange,
        merging: *mut VmRange,
        error: CInt,
    );
    #[cfg(enable_tofu)]
    fn process_join_range_tofu_bridge(
        vm: *mut c_void,
        surviving: *mut VmRange,
        merging: *mut VmRange,
    ) -> CInt;
}

const EINVAL: CInt = 22;
const EBUSY: CInt = 16;
const EACCES: CInt = 13;
const EFAULT: CInt = 14;
const ENOMEM: CInt = 12;
const E2BIG: CInt = 7;
const EPERM: CInt = 1;
const ENOENT: CInt = 2;
const ECANCELED: CInt = 125;
const ERESTART: CInt = 85;

const PAGE_SIZE: CULong = 4096;
const PAGE_SHIFT: CULong = 12;
const PF_WRITE: CULong = 1 << 1;
const PF_USER: CULong = 1 << 2;
const PF_INSTR: CULong = 1 << 4;
const PF_PATCH: CULong = 1 << 29;
const PF_POPULATE: CULong = 1 << 30;

const VERIFY_READ: CInt = 0;
const VERIFY_WRITE: CInt = 1;

const PS_EXITED: CInt = 0x10;
const PT_TRACED: CInt = 0x80;
const PT_TRACE_EXEC: CInt = 0x100;
const PT_TRACE_SYSCALL: CInt = 0x200;
const PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG: CInt = 1;
const PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG: CInt = 2;
const UTI_STATE_EPILOGUE: CInt = 3;
const PROCESS_TID_ACTION_NONE: CInt = 0;
const PROCESS_TID_ACTION_RELEASE: CInt = 1;
const PROCESS_TID_ACTION_REPLACE: CInt = 2;
const PROCESS_CREATE_CPU_LOG_INVALID: CInt = 1;
const PROCESS_CREATE_CPU_LOG_REQUESTED: CInt = 2;
const PROCESS_PTRACE_TRACEME_LOG_ENTER: CInt = 1;
const PROCESS_PTRACE_TRACEME_LOG_PARENT: CInt = 2;
const PROCESS_PTRACE_TRACEME_LOG_RETURN: CInt = 3;
const CLONE_VM: CInt = 0x0000_0100;
const CLONE_SIGHAND: CInt = 0x0000_0800;
const WNOWAIT: CInt = 0x0100_0000;
const LIST_POISON1: usize = 0x0010_0129;
const LIST_POISON2: usize = 0x0020_0229;
const MPOL_DEFAULT: CInt = 0;
const IHK_MC_AP_NOWAIT: CULong = 0x0000_02;
const CPU_SETSIZE: CInt = 1024;
const BITS_PER_BYTE: CULong = 8;
const KERNEL_STACK_NR_PAGES: CULong = 32;
const SCHED_NORMAL: CInt = 0;
const SS_DISABLE: CInt = 2;

const VR_RESERVED: CULong = 0x2;
const VR_STACK: CULong = 0x1;
const VR_AP_USER: CULong = 0x4;
const VR_IO_NOCACHE: CULong = 0x100;
const VR_REMOTE: CULong = 0x200;
const VR_WRITE_COMBINED: CULong = 0x400;
const VR_DONTFORK: CULong = 0x800;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_XPMEM: CULong = 0x4000_0000;
const VR_PROT_NONE: CULong = 0x0000_0000;
const VR_PROT_READ: CULong = 0x0001_0000;
const VR_PROT_WRITE: CULong = 0x0002_0000;
const VR_PROT_EXEC: CULong = 0x0004_0000;
const VR_PROT_MASK: CULong = 0x0007_0000;
const VR_MAXPROT_READ: CULong = 0x0010_0000;
const VR_MAXPROT_WRITE: CULong = 0x0020_0000;
const VR_MAXPROT_EXEC: CULong = 0x0040_0000;
const VR_MAXPROT_MASK: CULong = 0x0070_0000;
const NOPHYS: CULong = !0;
const HASH_SIZE: CInt = PROCESS_HASH_SIZE as CInt;

const MF_SHM: u32 = 0x40000;
const MF_HUGETLBFS: u32 = 0x100000;
const MF_ZEROFILL: u32 = 0x0010;
const VPTEF_SKIP_NULL: CInt = 0x0001;
const MCK_RLIMIT_STACK: usize = 15;
const IHK_UCR_STACK_POINTER: CInt = 1;
const AT_NULL: CULong = 0;
const AT_IGNORE: CULong = 1;
const AT_PHDR: CULong = 3;
const AT_PHENT: CULong = 4;
const AT_PHNUM: CULong = 5;
const AT_PAGESZ: CULong = 6;
const AT_BASE: CULong = 7;
const AT_FLAGS: CULong = 8;
const AT_ENTRY: CULong = 9;
const AT_UID: CULong = 11;
const AT_EUID: CULong = 12;
const AT_GID: CULong = 13;
const AT_EGID: CULong = 14;
const AT_HWCAP: CULong = 16;
const AT_CLKTCK: CULong = 17;
const AT_SECURE: CULong = 23;
const AT_RANDOM: CULong = 25;
const AT_HWCAP2: CULong = 26;
const AT_EXECFN: CULong = 31;
const AT_SYSINFO_EHDR: CULong = 33;

const PROCESS_ADD_RANGE_MAP_SKIP: CInt = 0;
const PROCESS_ADD_RANGE_MAP_UPDATE: CInt = 1;
const PROCESS_ADD_RANGE_MAP_MARK_XPMEM: CInt = 2;
const PROCESS_ADD_RANGE_MAP_DEMAND: CInt = 3;
const PROCESS_JOIN_RANGE_LOG_START: CInt = 1;
const PROCESS_JOIN_RANGE_LOG_DONE: CInt = 2;
const PROCESS_ADD_RANGE_LOG_ALLOC_FAILED: CInt = 1;
const PROCESS_ADD_RANGE_LOG_INSERT_FAILED: CInt = 2;
const PROCESS_ADD_RANGE_LOG_PREP_FAILED: CInt = 3;
const PROCESS_ADD_RANGE_LOG_DEMAND: CInt = 4;
const PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED: CInt = 5;
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP: CInt = 1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS: CInt = 2;
const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER: CInt = 1;
const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT: CInt = 2;
const PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER: CInt = 3;
const PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT: CInt = 4;
const PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER: CInt = 5;
const PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT: CInt = 6;
const PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER: CInt = 7;
const PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT: CInt = 8;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER: CInt = 1;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR: CInt = 2;
const PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT: CInt = 3;
const PROCESS_FREE_RANGE_PT_SKIP: CInt = 0;
const PROCESS_FREE_RANGE_PT_FREE: CInt = 1;
const PROCESS_FREE_RANGE_PT_CLEAR: CInt = 2;
const PROCESS_REMOVE_STRAIGHT_NO_CONVERT: CInt = 0;
const PROCESS_REMOVE_STRAIGHT_NEED_RANGE: CInt = 1;
const PROCESS_REMOVE_STRAIGHT_CONVERTED: CInt = 2;
const PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT: CInt = 1;
const PROCESS_REMOVE_RANGE_LOG_CONVERTED: CInt = 2;
const PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED: CInt = 3;
const PROCESS_REMOVE_RANGE_LOG_FREE_FAILED: CInt = 4;
const PROCESS_REMOVE_RANGE_LOG_DONE: CInt = 5;
const PROCESS_FREE_BODY_LOG_PLAN_FAILED: CInt = 1;
const PROCESS_FREE_BODY_LOG_PT_FREE_FAILED: CInt = 2;
const PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED: CInt = 3;
const PROCESS_FREE_BODY_LOG_TOFU_REMOVED: CInt = 4;
const PROCESS_FREE_BODY_LOG_FINALIZE_FAILED: CInt = 5;
const PROCESS_FREE_BODY_LOG_DONE: CInt = 6;
const PROCESS_REMAP_RANGE_LOG_PGSHIFT: CInt = 1;
const PROCESS_REMAP_RANGE_LOG_VISIT_FAILED: CInt = 2;
const PROCESS_INIT_STACK_LOG_SIZE: CInt = 1;
const PROCESS_INIT_STACK_LOG_AP_USER: CInt = 2;
const PROCESS_INIT_STACK_LOG_ALLOC_FAILED: CInt = 3;
const PROCESS_INIT_STACK_LOG_ADD_FAILED: CInt = 4;
const PROCESS_INIT_STACK_LOG_PT_FAILED: CInt = 5;
const PROCESS_INIT_STACK_LOG_AUXV: CInt = 6;
const PROCESS_INIT_STACK_LOG_SIZE_MISMATCH: CInt = 7;
const PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH: CInt = 8;
const PROCESS_INIT_STACK_LOG_INITIAL: CInt = 9;
const PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED: CInt = 1;
const PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED: CInt = 2;
const PROCESS_SPLIT_RANGE_LOG_START: CInt = 1;
const PROCESS_SPLIT_RANGE_LOG_DONE: CInt = 2;
const PROCESS_STATUS_RUNNING: CInt = 0x1;
const PROCESS_SCHED_INIT_PANIC: &[u8] = b"failed to initialize idle process state\0";

const PTATTR_ACTIVE: CULong = 0x01;
const PTATTR_WRITABLE: CULong = 0x02;
const PTATTR_USER: CULong = 0x04;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_UNCACHABLE: CULong = 0x10000;
const PTATTR_FOR_USER: CULong = 0x20000;
const PTATTR_WRITE_COMBINED: CULong = 0x40000;
const IHK_PTA_REMOTE: CULong = 0;

#[repr(C)]
pub struct ProcessInitStateOffsets {
    pub pid_offset: CULong,
    pub status_offset: CULong,
    pub parent_offset: CULong,
    pub ppid_parent_offset: CULong,
    pub pgid_offset: CULong,
    pub ruid_offset: CULong,
    pub euid_offset: CULong,
    pub suid_offset: CULong,
    pub fsuid_offset: CULong,
    pub rgid_offset: CULong,
    pub egid_offset: CULong,
    pub sgid_offset: CULong,
    pub fsgid_offset: CULong,
    pub mpol_flags_offset: CULong,
    pub mpol_threshold_offset: CULong,
    pub thp_disable_offset: CULong,
    pub rlimit_offset: CULong,
    pub rlimit_size: CULong,
    pub cpu_set_offset: CULong,
    pub cpu_set_size: CULong,
    pub enable_uti_offset: CULong,
}

#[repr(C)]
pub struct ProcessPtraceTracemeOffsets {
    pub thread_proc_offset: CULong,
    pub thread_report_proc_offset: CULong,
    pub thread_report_siblings_list_offset: CULong,
    pub thread_ptrace_offset: CULong,
    pub thread_ptrace_debugreg_offset: CULong,
    pub proc_pid_offset: CULong,
    pub proc_parent_offset: CULong,
    pub proc_main_thread_offset: CULong,
    pub proc_children_lock_offset: CULong,
    pub proc_threads_lock_offset: CULong,
    pub proc_ptraced_siblings_list_offset: CULong,
    pub proc_ptraced_children_list_offset: CULong,
    pub proc_report_threads_list_offset: CULong,
}

#[repr(C)]
pub struct ProcessPtraceAttachOffsets {
    pub thread_proc_offset: CULong,
    pub thread_report_proc_offset: CULong,
    pub thread_report_siblings_list_offset: CULong,
    pub thread_ptrace_debugreg_offset: CULong,
    pub proc_pid_offset: CULong,
    pub proc_parent_offset: CULong,
    pub proc_main_thread_offset: CULong,
    pub proc_children_lock_offset: CULong,
    pub proc_threads_lock_offset: CULong,
    pub proc_children_list_offset: CULong,
    pub proc_siblings_list_offset: CULong,
    pub proc_ptraced_siblings_list_offset: CULong,
    pub proc_ptraced_children_list_offset: CULong,
    pub proc_report_threads_list_offset: CULong,
}

#[repr(C)]
pub struct ProcessFindThreadOffsets {
    pub thread_hash_list_offset: CULong,
    pub thread_tid_offset: CULong,
    pub thread_proc_offset: CULong,
    pub proc_pid_offset: CULong,
}

#[repr(C)]
pub struct ProcessFindProcessOffsets {
    pub process_hash_list_offset: CULong,
    pub process_pid_offset: CULong,
}

type ProcessAddRangeAllocFn = unsafe extern "C" fn(CULong) -> *mut VmRange;
type ProcessAddRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessAddRangeInsertFn = unsafe extern "C" fn(*mut c_void, *mut VmRange) -> CInt;
type ProcessAddRangeUpdateFn =
    unsafe extern "C" fn(*mut c_void, *mut VmRange, CULong, CULong) -> CInt;
type ProcessAddRangeRemoveFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type ProcessAddRangeMarkXpmemFn = unsafe extern "C" fn(*mut VmRange);
type ProcessAddRangeMemclearFn = unsafe extern "C" fn(CULong, CULong);
type ProcessAddRangeLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CULong);
type ProcessVmRangeInsertLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, *mut VmRange);
type ProcessVmRangeInsertDumpFn = unsafe extern "C" fn(*mut c_void);
type ProcessRangePublicLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, CULong, CULong, CInt);
type ProcessChangeProtPublicLogFn =
    unsafe extern "C" fn(CInt, *mut c_void, *mut VmRange, CULong, CInt);
type ProcessAccessOkLogFn = unsafe extern "C" fn(*mut ProcessVm, CInt, CULong, SizeT, CInt);
type ProcessRangeMemobjRefFn = unsafe extern "C" fn(*mut c_void);
type ProcessSplitRangeInsertFn = unsafe extern "C" fn(*mut c_void, *mut VmRange) -> CInt;
type ProcessSplitRangeAllocFn = unsafe extern "C" fn(CULong, CULong) -> *mut VmRange;
type ProcessSplitRangeAllocLogFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, *mut c_void);
type ProcessSplitRangePublishLogFn = unsafe extern "C" fn(CInt);
type ProcessSplitRangePtSplitFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, *mut VmRange, *mut c_void) -> CInt;
type ProcessSplitRangePtLogFn = unsafe extern "C" fn(CInt);
type ProcessSplitShmLookupPageFn =
    unsafe extern "C" fn(*mut c_void, OffT, CInt, *mut CULong, *mut CULong) -> CInt;
type ProcessSplitShmPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessSplitShmUpdatePageFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, *mut c_void) -> CInt;
type ProcessSplitShmLogFn = unsafe extern "C" fn(CInt, CInt);
type ProcessJoinRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessJoinRangeTofuFn = unsafe extern "C" fn(*mut c_void, *mut VmRange, *mut VmRange) -> CInt;
type ProcessFreeRangePageSizeFn = unsafe extern "C" fn(SizeT, *mut SizeT) -> CInt;
type ProcessFreeRangePhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessFreeRangePagesFn = unsafe extern "C" fn(*mut c_void, CULong);
type ProcessFreeRangeClearMainFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type ProcessFreeRangeFreeFn = unsafe extern "C" fn(*mut VmRange);
type ProcessFreeRangePtFreeFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong, *mut c_void) -> CInt;
type ProcessFreeRangePtClearFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong) -> CInt;
type ProcessFreeRangeTofuRemoveFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange) -> CInt;
type ProcessFreeRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, *mut VmRange, CULong, CULong, CInt);
type ProcessVisitPteRangeFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CInt, CInt, *mut c_void, *mut c_void) -> CInt;
type ProcessCopyRangeLookupFn =
    unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> *mut VmRange;
type ProcessCopyRangeNextFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange) -> *mut VmRange;
type ProcessCopyUserRangesLogFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CLong);
type ProcessLookupPteFn =
    unsafe extern "C" fn(*mut c_void, CULong, CInt, *mut SizeT) -> *mut c_void;
type ProcessPteTestFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPtePgsizeTestFn = unsafe extern "C" fn(*mut c_void, SizeT) -> CInt;
type ProcessSplitContiguousPagesFn = unsafe extern "C" fn(*mut c_void, SizeT, u32) -> CInt;
type ProcessPteGetPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessPhysToPageFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessPageOffsetFn = unsafe extern "C" fn(*mut c_void) -> OffT;
type ProcessPteMakeFileoffFn = unsafe extern "C" fn(OffT, SizeT, *mut c_void);
type ProcessPteXchgFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessFlushTlbSingleFn = unsafe extern "C" fn(CULong);
type ProcessPgsizeToTbllvFn = unsafe extern "C" fn(SizeT) -> CInt;
type ProcessTbllvToContpgsizeFn = unsafe extern "C" fn(CInt) -> SizeT;
type ProcessPageUnmapFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPanicFn = unsafe extern "C" fn(*const i8);
type ProcessMemobjInvalidatePageFn = unsafe extern "C" fn(*mut Memobj, CULong, SizeT) -> CInt;
type ProcessInvalidateOnePageLogFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void, CULong, *mut c_void, CInt, CInt);
type ProcessSyncRangeLogFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong, CInt);
type ProcessRemapRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, *mut VmRange, CULong, CULong, OffT, CInt, CInt);
type ProcessMemoryRangeFreeFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMemoryRangeLogFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type ProcessMckfdCloseFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMckfdDupFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessMckfdFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessPolicyFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessDetachAddressSpaceFn = unsafe extern "C" fn(*mut c_void, CInt);
type ProcessReleaseProcessFn = unsafe extern "C" fn(*mut c_void);
type ProcessOptionalFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessReleaseFpRegsFn = unsafe extern "C" fn(*mut c_void);
type ProcessRefIncFn = unsafe extern "C" fn(*mut c_void, CULong);
type ProcessRefDecAndTestFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type ProcessDefaultNcpusFn = unsafe extern "C" fn() -> CInt;
type ProcessCreateCpuLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type ProcessHoldThreadWarnFn = unsafe extern "C" fn(*mut c_void);
type ProcessCurrentResourceSetFn = unsafe extern "C" fn() -> *mut c_void;
type ProcessResourceProcessActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessProcessActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessResourceSetActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessTidLogFn = unsafe extern "C" fn(CInt, *mut c_void, CInt);
type ProcessThreadProfileFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessThreadProcActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessThreadTidActionFn = unsafe extern "C" fn(*mut c_void, *mut c_void, CInt);
type ProcessVmActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessVmReleaseCheckedFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessMcsRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);
type ProcessAllocDebugregFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPtraceTracemeLogFn = unsafe extern "C" fn(CInt, CInt, CULong, CInt);
type ProcessSpinLockFn = unsafe extern "C" fn(CULong) -> CULong;
type ProcessSpinUnlockFn = unsafe extern "C" fn(CULong, CULong);
type ProcessFreeFn = unsafe extern "C" fn(*mut c_void);
type ProcessVmFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessAddressSpaceFreeCallback = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessAddressSpaceActionFn = unsafe extern "C" fn(*mut c_void);
type ProcessPtDestroyFn = unsafe extern "C" fn(*mut c_void);
type ProcessAllocFn = unsafe extern "C" fn(CULong, CULong) -> *mut c_void;
type ProcessPtCreateFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessRefSetFn = unsafe extern "C" fn(*mut c_void, CULong, CInt);
type ProcessSpinInitFn = unsafe extern "C" fn(CULong);
type ProcessRwlockInitFn = unsafe extern "C" fn(CULong);
type ProcessVmInitNumaLogFn = unsafe extern "C" fn(CInt);
type ProcessWaitqInitFn = unsafe extern "C" fn(CULong);
type ProcessMcsLockInitFn = unsafe extern "C" fn(CULong);
type ProcessAllocPagesFn = unsafe extern "C" fn(CInt, CULong) -> *mut c_void;
type ProcessCreateAddressSpaceFn = unsafe extern "C" fn(CInt) -> *mut c_void;
type ProcessReleaseAddressSpaceFn = unsafe extern "C" fn(*mut c_void);
type ProcessInitProcessFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type ProcessInitProcessVmFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt;
type ProcessInitUserProcessFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong);
type ProcessSchedInitContextFn = unsafe extern "C" fn(*mut c_void);
type ProcessSchedSaveFpFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessSchedTimerInitFn = unsafe extern "C" fn(CInt);
type ProcessVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessPhysToVirtFn = unsafe extern "C" fn(CULong) -> *mut c_void;
type ProcessMemsetFn = unsafe extern "C" fn(*mut c_void, CInt, SizeT);
type ProcessMemsetSmpLogFn = unsafe extern "C" fn(CInt, CInt, CInt, CULong, SizeT, CULong, CULong);
type ProcessSmpCallFn = unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt;

#[repr(C)]
struct ProcessMemsetSmpReq {
    phys: CULong,
    len: SizeT,
    val: CInt,
}

#[repr(C, align(64))]
struct McsRwlockNode {
    count: IhkAtomic,
    type_: i8,
    locked: i8,
    dmy1: i8,
    dmy2: i8,
    next: *mut McsRwlockNode,
}

const _: () = {
    use core::mem::{align_of, size_of};

    assert!(size_of::<McsRwlockNode>() == 64);
    assert!(align_of::<McsRwlockNode>() == 64);
    assert!(offset_of!(McsRwlockNode, count) == 0);
    assert!(offset_of!(McsRwlockNode, type_) == 4);
    assert!(offset_of!(McsRwlockNode, locked) == 5);
    assert!(offset_of!(McsRwlockNode, dmy1) == 6);
    assert!(offset_of!(McsRwlockNode, dmy2) == 7);
    assert!(offset_of!(McsRwlockNode, next) == 8);
};

#[repr(C)]
struct ProcessRemapArgs {
    off: OffT,
    start: CULong,
    memobj: *mut Memobj,
}

#[repr(C)]
struct ProcessSyncArgs {
    memobj: *mut Memobj,
}

const _: () = {
    use core::mem::{align_of, size_of};

    assert!(size_of::<ProcessRemapArgs>() == 24);
    assert!(align_of::<ProcessRemapArgs>() == 8);
    assert!(offset_of!(ProcessRemapArgs, off) == 0);
    assert!(offset_of!(ProcessRemapArgs, start) == 8);
    assert!(offset_of!(ProcessRemapArgs, memobj) == 16);
    assert!(size_of::<ProcessSyncArgs>() == 8);
    assert!(align_of::<ProcessSyncArgs>() == 8);
    assert!(offset_of!(ProcessSyncArgs, memobj) == 0);
};

type ProcessAttrFromVrflagFn = unsafe extern "C" fn(CULong, CULong, *mut c_void) -> CULong;
type ProcessNoirqLockFn = unsafe extern "C" fn(CULong);
type ProcessNoirqUnlockFn = unsafe extern "C" fn(CULong);
type ProcessPtChangeAttrFn =
    unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong, CULong) -> CInt;
type ProcessPtSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut VmRange,
    CInt,
) -> CInt;
type ProcessUpdatePageTableLogFn = unsafe extern "C" fn(CInt);
type ProcessFaultRangeFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong) -> CInt;
type ProcessZeroobjMatchFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type ProcessPageFaultVmFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> CInt;
type ProcessPreemptFn = unsafe extern "C" fn();
type ProcessPgioDispatchFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type ProcessPopulateWarnFn =
    unsafe extern "C" fn(*mut ProcessVm, CULong, CULong, CULong, SizeT, CInt);
type ProcessRemoveRangeSplitFn =
    unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, *mut *mut VmRange) -> CInt;
type ProcessRemoveRangeXpmemFn = unsafe extern "C" fn(*mut ProcessVm, *mut VmRange);
type ProcessRemoveRangeLogFn =
    unsafe extern "C" fn(CInt, *mut ProcessVm, CULong, CULong, *mut VmRange, CInt);
type ProcessRemoveRegionClearFn =
    unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong) -> CInt;
type ProcessRemoveRegionLogFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong);
type ProcessInitStackAllocAlignedFn =
    unsafe extern "C" fn(CInt, CInt, CULong, CULong) -> *mut c_void;
type ProcessInitStackFreePagesFn = unsafe extern "C" fn(*mut c_void, CInt);
type ProcessInitStackAddRangeFn = unsafe extern "C" fn(
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut *mut VmRange,
) -> CInt;
type ProcessInitStackVirtToPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ProcessInitStackPtSetRangeFn = unsafe extern "C" fn(
    *mut c_void,
    *mut ProcessVm,
    CULong,
    CULong,
    CULong,
    CULong,
    CInt,
    *mut VmRange,
    CInt,
) -> CInt;
type ProcessInitStackHwcapFn = unsafe extern "C" fn() -> CULong;
type ProcessInitStackModifyContextFn = unsafe extern "C" fn(*mut c_void, CInt, CULong);
type ProcessInitStackLogFn = unsafe extern "C" fn(CInt, *const CULong);

#[no_mangle]
pub extern "C" fn PROT_TO_VR_FLAG(prot: CULong) -> CULong {
    (prot << 16) & VR_PROT_MASK
}

#[no_mangle]
pub extern "C" fn VRFLAG_PROT_TO_MAXPROT(vrflag: CULong) -> CULong {
    (vrflag & VR_PROT_MASK) << 4
}

#[no_mangle]
pub extern "C" fn VRFLAG_MAXPROT_TO_PROT(vrflag: CULong) -> CULong {
    (vrflag & VR_MAXPROT_MASK) >> 4
}

#[no_mangle]
pub extern "C" fn __WEXITSTATUS(status: CInt) -> CInt {
    (status & 0xff00) >> 8
}

#[no_mangle]
pub extern "C" fn __WTERMSIG(status: CInt) -> CInt {
    status & 0x7f
}

#[no_mangle]
pub extern "C" fn __WSTOPSIG(status: CInt) -> CInt {
    __WEXITSTATUS(status)
}

#[no_mangle]
pub extern "C" fn __WIFEXITED(status: CInt) -> CInt {
    (__WTERMSIG(status) == 0) as CInt
}

#[no_mangle]
pub extern "C" fn __WIFSIGNALED(status: CInt) -> CInt {
    ((((status & 0x7f) + 1) as i8) >> 1 > 0) as CInt
}

#[no_mangle]
pub extern "C" fn __WIFSTOPPED(status: CInt) -> CInt {
    ((status & 0xff) == 0x7f) as CInt
}

#[no_mangle]
pub extern "C" fn process_hash(pid: CInt) -> CInt {
    pid % HASH_SIZE
}

#[no_mangle]
pub extern "C" fn thread_hash(tid: CInt) -> CInt {
    tid % HASH_SIZE
}

#[no_mangle]
pub unsafe extern "C" fn has_cap_ipc_lock(th: *mut Thread) -> CInt {
    ((*(*th).proc).euid == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn has_cap_sys_admin(th: *mut Thread) -> CInt {
    ((*(*th).proc).euid == 0) as CInt
}

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

#[inline(always)]
#[cfg(enable_tofu)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_init_result(
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
) -> CInt {
    if range.is_null() {
        return 0;
    }

    (*range).vm_rb_node.__rb_parent_color = core::ptr::addr_of_mut!((*range).vm_rb_node) as CULong;
    (*range).start = start;
    (*range).end = end;
    (*range).flag = flag;
    (*range).memobj = memobj;
    (*range).objoff = offset;
    (*range).pgshift = pgshift;
    (*range).private_data = private_data;
    (*range).straight_start = 0;
    #[cfg(enable_tofu)]
    init_list_head(&raw mut (*range).tofu_stag_list);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_mapping_result(
    phys: CULong,
    flag: CULong,
    range_flag: CULong,
    attrp: *mut CULong,
    memclearp: *mut CInt,
) -> CInt {
    let mut attr = 0;
    let action = if phys == NOPHYS {
        PROCESS_ADD_RANGE_MAP_SKIP
    } else if (flag & VR_REMOTE) != 0 {
        attr = IHK_PTA_REMOTE;
        PROCESS_ADD_RANGE_MAP_UPDATE
    } else if (flag & VR_IO_NOCACHE) != 0 {
        attr = PTATTR_UNCACHABLE;
        PROCESS_ADD_RANGE_MAP_UPDATE
    } else if (flag & VR_XPMEM) != 0 {
        PROCESS_ADD_RANGE_MAP_MARK_XPMEM
    } else if (flag & VR_DEMAND_PAGING) != 0 {
        PROCESS_ADD_RANGE_MAP_DEMAND
    } else if (range_flag & VR_PROT_MASK) == VR_PROT_NONE {
        PROCESS_ADD_RANGE_MAP_SKIP
    } else {
        PROCESS_ADD_RANGE_MAP_UPDATE
    };

    let memclear = phys != NOPHYS
        && (flag & (VR_REMOTE | VR_DEMAND_PAGING | VR_XPMEM)) == 0
        && (flag & VR_PROT_MASK) != VR_PROT_NONE;

    if !attrp.is_null() {
        *attrp = attr;
    }
    if !memclearp.is_null() {
        *memclearp = memclear as CInt;
    }

    action
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_alloc_result(
    range_size: CULong,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
) -> *mut VmRange {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };

    alloc(range_size)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessAddRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_insert_result(
    vm: *mut c_void,
    range: *mut VmRange,
    insert_fn: Option<ProcessAddRangeInsertFn>,
) -> CInt {
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };

    insert(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_update_result(
    vm: *mut c_void,
    range: *mut VmRange,
    phys: CULong,
    attr: CULong,
    update_fn: Option<ProcessAddRangeUpdateFn>,
) -> CInt {
    let Some(update) = update_fn else {
        return -EINVAL;
    };

    update(vm, range, phys, attr)
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_remove_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
) -> CInt {
    let Some(remove) = remove_fn else {
        return -EINVAL;
    };

    remove(vm, start, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_mark_xpmem_result(
    range: *mut VmRange,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
) -> CInt {
    let Some(mark_xpmem) = mark_xpmem_fn else {
        return -EINVAL;
    };

    mark_xpmem(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_memclear_result(
    phys: CULong,
    bytes: CULong,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
) -> CInt {
    let Some(memclear) = memclear_fn else {
        return -EINVAL;
    };

    memclear(phys, bytes);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_log_result(
    event: CInt,
    rc: CInt,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, rc, start, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_orchestrate_result(
    vm: *mut c_void,
    range_size: CULong,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
    rp: *mut *mut VmRange,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    update_fn: Option<ProcessAddRangeUpdateFn>,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(insert_fn) = insert_fn else {
        return -EINVAL;
    };
    let Some(update_fn) = update_fn else {
        return -EINVAL;
    };
    let Some(remove_fn) = remove_fn else {
        return -EINVAL;
    };
    let Some(mark_xpmem_fn) = mark_xpmem_fn else {
        return -EINVAL;
    };
    let Some(memclear_fn) = memclear_fn else {
        return -EINVAL;
    };

    let range = process_add_range_alloc_result(range_size, Some(alloc_fn));
    if range.is_null() {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_ALLOC_FAILED,
            -ENOMEM,
            start,
            end,
            log_fn,
        );
        return -ENOMEM;
    }

    process_add_range_init_result(
        range,
        start,
        end,
        flag,
        memobj,
        offset,
        pgshift,
        private_data,
    );

    let mut rc = process_add_range_insert_result(vm, range, Some(insert_fn));
    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_INSERT_FAILED,
            rc,
            start,
            end,
            log_fn,
        );
        let _ = process_add_range_free_result(range, Some(free_fn));
        return rc;
    }

    let mut map_attr = 0;
    let mut should_memclear = 0;
    let map_action = process_add_range_mapping_result(
        phys,
        flag,
        (*range).flag,
        &mut map_attr,
        &mut should_memclear,
    );
    if map_action == PROCESS_ADD_RANGE_MAP_UPDATE {
        rc = process_add_range_update_result(vm, range, phys, map_attr, Some(update_fn));
    } else if map_action == PROCESS_ADD_RANGE_MAP_MARK_XPMEM {
        let _ = process_add_range_mark_xpmem_result(range, Some(mark_xpmem_fn));
    } else if map_action == PROCESS_ADD_RANGE_MAP_DEMAND {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_DEMAND,
            0,
            (*range).start,
            (*range).end,
            log_fn,
        );
    }

    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_PREP_FAILED,
            rc,
            (*range).start,
            (*range).end,
            log_fn,
        );
        let _ = process_add_range_remove_result(vm, (*range).start, (*range).end, Some(remove_fn));
        let _ = process_add_range_free_result(range, Some(free_fn));
        return rc;
    }

    if should_memclear != 0 {
        let _ = process_add_range_memclear_result(phys, end - start, Some(memclear_fn));
    }

    if !rp.is_null() {
        *rp = range;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_add_range_public_body_result(
    vm: *mut c_void,
    range_size: CULong,
    user_start: CULong,
    user_end: CULong,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
    rp: *mut *mut VmRange,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    update_fn: Option<ProcessAddRangeUpdateFn>,
    remove_fn: Option<ProcessAddRangeRemoveFn>,
    mark_xpmem_fn: Option<ProcessAddRangeMarkXpmemFn>,
    memclear_fn: Option<ProcessAddRangeMemclearFn>,
    log_fn: Option<ProcessAddRangeLogFn>,
) -> CInt {
    let rc = process_add_range_bounds_result(user_start, user_end, start, end);
    if rc != 0 {
        let _ = process_add_range_log_result(
            PROCESS_ADD_RANGE_LOG_BOUNDS_FAILED,
            rc,
            start,
            end,
            log_fn,
        );
        return rc;
    }

    process_add_range_orchestrate_result(
        vm,
        range_size,
        start,
        end,
        phys,
        flag,
        memobj,
        offset,
        pgshift,
        private_data,
        rp,
        alloc_fn,
        free_fn,
        insert_fn,
        update_fn,
        remove_fn,
        mark_xpmem_fn,
        memclear_fn,
        log_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn add_process_memory_range(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    memobj: *mut c_void,
    offset: OffT,
    pgshift: CInt,
    private_data: *mut c_void,
    rp: *mut *mut VmRange,
) -> CInt {
    process_add_range_public_body_result(
        vm.cast::<c_void>(),
        core::mem::size_of::<VmRange>() as CULong,
        (*vm).region.user_start,
        (*vm).region.user_end,
        start,
        end,
        phys,
        flag,
        memobj,
        offset,
        pgshift,
        private_data,
        rp,
        Some(process_add_range_alloc_bridge),
        Some(process_add_range_free_bridge),
        Some(process_add_range_insert_bridge),
        Some(process_add_range_update_bridge),
        Some(process_add_range_remove_bridge),
        Some(process_add_range_mark_xpmem_bridge),
        Some(process_add_range_memclear_bridge),
        Some(process_add_range_log_bridge),
    )
}

#[inline(always)]
unsafe fn vm_range_rb_node(range: *mut VmRange) -> *mut RbNode {
    (&raw mut (*range).vm_rb_node).cast::<RbNode>()
}

#[inline(always)]
unsafe fn vm_range_from_rb_node(node: *mut RbNode) -> *mut VmRange {
    node.cast::<VmRange>()
}

/// Preserve the actual process.c log event and variadic ABI. Unknown events
/// do nothing; disabled success logging does not evaluate range fields. The
/// caller retains live ranges through the existing synchronous logger call.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_log_bridge(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
) {
    if event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP {
        let _ = kprintf(
            b"vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n\0".as_ptr().cast(),
            vm,
            (*newrange).start,
            (*newrange).end,
            (*newrange).flag,
            (*range).start,
            (*range).end,
            (*range).flag,
        );
    } else if event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS {
        let flags = core::ptr::read_volatile(
            core::ptr::addr_of!(process_vm_range_insert_debug.line_flags),
        ) >> 24;
        if flags != 0 {
            let _ = kprintf(
                b"vm_range_insert: %p,%p: %lx-%lx %x\n\0".as_ptr().cast(),
                vm,
                newrange,
                (*newrange).start,
                (*newrange).end,
                (*newrange).flag,
            );
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_log_result(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, newrange, range);
    0
}

// Same synchronous in-order diagnostic traversal as the displaced dtree.
// The existing VM/range exclusion keeps every visited node live. Field reads
// and the right-child load remain after left traversal and the logger call.
unsafe fn process_dump_tree_node(node: *mut RbNode, level: CInt) {
    if node.is_null() {
        return;
    }
    let range = vm_range_from_rb_node(node);
    process_dump_tree_node((*node).rb_left, level.wrapping_add(1));
    let _ = kprintf(
        b"dtree: %0*d, %p: %lx-%lx\n\0".as_ptr().cast(),
        level,
        0 as CInt,
        range,
        (*range).start,
        (*range).end,
    );
    process_dump_tree_node((*node).rb_right, level.wrapping_add(1));
}

/// Preserve DEBUG_PRINT_PROCESS gating without retaining C dump computation.
/// Disabled dumping never dereferences vm. Enabled dumping logs the header
/// before loading the root, then synchronously visits the borrowed live tree.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_dump_bridge(vm: *mut c_void) {
    if core::ptr::read_volatile(core::ptr::addr_of!(process_dump_tree_enabled)) == 0 {
        return;
    }
    let _ = kprintf(b"dump_tree %p\n\0".as_ptr().cast(), vm);
    let root = (*vm.cast::<ProcessVm>()).vm_range_tree.rb_node.cast::<RbNode>();
    process_dump_tree_node(root, 1);
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_dump_result(
    vm: *mut c_void,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    let Some(dump) = dump_fn else {
        return 0;
    };

    dump(vm);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_range_insert_result(
    root: *mut RbRoot,
    newrange: *mut VmRange,
    vm: *mut c_void,
    log_fn: Option<ProcessVmRangeInsertLogFn>,
    dump_fn: Option<ProcessVmRangeInsertDumpFn>,
) -> CInt {
    if root.is_null() || newrange.is_null() {
        return -EINVAL;
    }

    let mut link: *mut *mut RbNode = &raw mut (*root).rb_node;
    let mut parent: *mut RbNode = null_mut();

    while !(*link).is_null() {
        let current = *link;
        let range = vm_range_from_rb_node(current);

        parent = current;
        if (*newrange).end <= (*range).start {
            link = &raw mut (*current).rb_left;
        } else if (*newrange).start >= (*range).end {
            link = &raw mut (*current).rb_right;
        } else {
            let _ = process_vm_range_insert_log_result(
                PROCESS_VM_RANGE_INSERT_LOG_OVERLAP,
                vm,
                newrange,
                range,
                log_fn,
            );
            return -EFAULT;
        }
    }

    let _ = process_vm_range_insert_log_result(
        PROCESS_VM_RANGE_INSERT_LOG_SUCCESS,
        vm,
        newrange,
        null_mut(),
        log_fn,
    );
    let _ = process_vm_range_insert_dump_result(vm, dump_fn);

    let node = vm_range_rb_node(newrange);
    rb_link_node(node, parent, link);
    rb_insert_color(node, root);

    0
}

/// Own the selected process.c insertion entry in Rust. The caller holds the
/// existing VM range exclusion and supplies a live ProcessVm, exactly as for
/// the former C wrapper; the helper retains all tree mutation and error order.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert(
    vm: *mut ProcessVm,
    newrange: *mut VmRange,
) -> CInt {
    process_vm_range_insert_result(
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        newrange,
        vm.cast(),
        Some(vm_range_insert_log_bridge),
        Some(vm_range_insert_dump_bridge),
    )
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
pub unsafe extern "C" fn process_noirq_lock_result(
    lock_addr: CULong,
    lock_fn: Option<ProcessNoirqLockFn>,
) -> CInt {
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };

    lock(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_noirq_unlock_result(
    lock_addr: CULong,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
) -> CInt {
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unlock(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_change_attr_result(
    page_table: *mut c_void,
    start: CULong,
    end: CULong,
    clrattr: CULong,
    setattr: CULong,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
) -> CInt {
    let Some(change_attr) = change_attr_fn else {
        return -EINVAL;
    };

    change_attr(page_table, start, end, clrattr, setattr)
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_set_range_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut VmRange,
    flags: CInt,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
) -> CInt {
    let Some(pt_set_range) = pt_set_range_fn else {
        return -EINVAL;
    };

    pt_set_range(
        page_table, vm, start, end, phys, attr, pgshift, range, flags,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_log_result(
    error: CInt,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_zeroobj_match_result(
    memobj: *mut c_void,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
) -> CInt {
    let Some(zeroobj_match) = zeroobj_match_fn else {
        return -EINVAL;
    };

    zeroobj_match(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_fault_range_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    let Some(fault) = fault_fn else {
        return -EINVAL;
    };

    fault(vm, range, fault_addr, reason)
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
pub unsafe extern "C" fn process_lookup_memory_range_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    if vm.is_null() || end <= start {
        return null_mut();
    }

    let mut i = 0;
    let cache_base = (&raw mut (*vm).range_cache).cast::<*mut VmRange>();
    while i < crate::abi::VM_RANGE_CACHE_SIZE as CInt {
        let c_i = (i + (*vm).range_cache_ind) % crate::abi::VM_RANGE_CACHE_SIZE as CInt;
        let cached = *cache_base.add(c_i as usize);
        if !cached.is_null()
            && process_range_cache_hit_result((*cached).start, (*cached).end, start, end) != 0
        {
            return cached;
        }
        i += 1;
    }

    let mut node = (*vm).vm_range_tree.rb_node.cast::<RbNode>();
    let mut matched: *mut VmRange = null_mut();
    while !node.is_null() {
        let range = vm_range_from_rb_node(node);
        let relation =
            process_lookup_range_relation_result(start, end, (*range).start, (*range).end);
        if relation < -1 {
            matched = range;
            node = (*node).rb_left;
        } else if relation < 0 {
            node = (*node).rb_left;
        } else if relation > 0 {
            node = (*node).rb_right;
        } else {
            matched = range;
            break;
        }
    }

    if !matched.is_null() && end > (*matched).start {
        let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
        process_range_cache_store_result(
            cache,
            crate::abi::VM_RANGE_CACHE_SIZE as CInt,
            &raw mut (*vm).range_cache_ind,
            matched.cast(),
        );
    }

    matched
}

#[no_mangle]
pub unsafe extern "C" fn process_next_memory_range_body_result(
    range: *mut VmRange,
) -> *mut VmRange {
    if range.is_null() {
        return null_mut();
    }
    let node = rb_next(vm_range_rb_node(range));
    if node.is_null() {
        null_mut()
    } else {
        vm_range_from_rb_node(node)
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_previous_memory_range_body_result(
    range: *mut VmRange,
) -> *mut VmRange {
    if range.is_null() {
        return null_mut();
    }
    let node = rb_prev(vm_range_rb_node(range));
    if node.is_null() {
        null_mut()
    } else {
        vm_range_from_rb_node(node)
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_extend_up_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    newend: CULong,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    let next = process_next_memory_range_body_result(range);
    let error = process_extend_up_result(
        (*range).end,
        (*vm).region.user_end,
        (!next.is_null()) as CInt,
        if next.is_null() { 0 } else { (*next).start },
        newend,
    );
    if error != 0 {
        return error;
    }
    process_range_end_commit_result(range, newend);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_public_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(event, vm.cast(), range, start, end, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_lookup_memory_range_public_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER,
        vm,
        null_mut(),
        start,
        end,
        0,
        log_fn,
    );
    let matched = process_lookup_memory_range_body_result(vm, start, end);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT,
        vm,
        matched,
        start,
        end,
        0,
        log_fn,
    );
    matched
}

#[no_mangle]
pub unsafe extern "C" fn process_next_memory_range_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let start = if range.is_null() { 0 } else { (*range).start };
    let end = if range.is_null() { 0 } else { (*range).end };
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_NEXT_ENTER,
        vm,
        range,
        start,
        end,
        0,
        log_fn,
    );
    let next = process_next_memory_range_body_result(range);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_NEXT_EXIT,
        vm,
        next,
        start,
        end,
        0,
        log_fn,
    );
    next
}

#[no_mangle]
pub unsafe extern "C" fn process_previous_memory_range_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> *mut VmRange {
    let start = if range.is_null() { 0 } else { (*range).start };
    let end = if range.is_null() { 0 } else { (*range).end };
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_ENTER,
        vm,
        range,
        start,
        end,
        0,
        log_fn,
    );
    let prev = process_previous_memory_range_body_result(range);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_PREVIOUS_EXIT,
        vm,
        prev,
        start,
        end,
        0,
        log_fn,
    );
    prev
}

#[no_mangle]
pub unsafe extern "C" fn process_extend_up_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    newend: CULong,
    log_fn: Option<ProcessRangePublicLogFn>,
) -> CInt {
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_EXTEND_ENTER,
        vm,
        range,
        if range.is_null() { 0 } else { (*range).start },
        newend,
        0,
        log_fn,
    );
    let error = process_extend_up_body_result(vm, range, newend);
    let _ = process_range_public_log_result(
        PROCESS_RANGE_PUBLIC_LOG_EXTEND_EXIT,
        vm,
        range,
        if range.is_null() { 0 } else { (*range).start },
        newend,
        error,
        log_fn,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn lookup_process_memory_range(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    process_lookup_memory_range_public_result(vm, start, end, Some(process_range_public_log_bridge))
}

#[no_mangle]
pub unsafe extern "C" fn next_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
) -> *mut VmRange {
    process_next_memory_range_public_result(vm, range, Some(process_range_public_log_bridge))
}

#[no_mangle]
pub unsafe extern "C" fn previous_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
) -> *mut VmRange {
    process_previous_memory_range_public_result(vm, range, Some(process_range_public_log_bridge))
}

#[no_mangle]
pub unsafe extern "C" fn extend_up_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    newend: CULong,
) -> CInt {
    process_extend_up_public_result(vm, range, newend, Some(process_range_public_log_bridge))
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let newflag = process_change_prot_newflag_result((*range).flag, protflag);
    if (*range).flag == newflag {
        return 0;
    }

    if attr_fn.is_none() {
        return -EINVAL;
    }
    let mut clrattr = 0;
    let mut setattr = 0;
    process_attr_delta_result(
        process_attr_from_vrflag_result((*range).flag, PF_POPULATE, null_mut(), attr_fn),
        process_attr_from_vrflag_result(newflag, PF_POPULATE, null_mut(), attr_fn),
        &raw mut clrattr,
        &raw mut setattr,
    );

    if !(*range).memobj.is_null() && ((*range).flag & VR_PRIVATE) != 0 {
        let memobj = (*range).memobj.cast::<Memobj>();
        setattr = process_private_file_setattr_result(1, (*range).flag, (*memobj).flags, setattr);
        if clrattr == 0 && setattr == 0 {
            process_range_flag_commit_result(range, newflag);
            return 0;
        }
    }

    if lock_fn.is_none() || unlock_fn.is_none() || change_attr_fn.is_none() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let error = process_noirq_lock_result(lock_addr, lock_fn);
    if error != 0 {
        return error;
    }
    let error = process_pt_change_attr_result(
        (*address_space).page_table,
        (*range).start,
        (*range).end,
        clrattr,
        setattr,
        change_attr_fn,
    );
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if error != 0 && error != -ENOENT {
        return error;
    }

    process_range_flag_commit_result(range, newflag);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_public_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    error: CInt,
    log_fn: Option<ProcessChangeProtPublicLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(event, vm.cast(), range, protflag, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_change_prot_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    change_attr_fn: Option<ProcessPtChangeAttrFn>,
    log_fn: Option<ProcessChangeProtPublicLogFn>,
) -> CInt {
    let _ = process_change_prot_public_log_result(
        PROCESS_CHANGE_PROT_PUBLIC_LOG_ENTER,
        vm,
        range,
        protflag,
        0,
        log_fn,
    );
    let error = process_change_prot_body_result(
        vm,
        range,
        protflag,
        attr_fn,
        lock_fn,
        unlock_fn,
        change_attr_fn,
    );
    if error != 0 && error != -ENOENT {
        let _ = process_change_prot_public_log_result(
            PROCESS_CHANGE_PROT_PUBLIC_LOG_ERROR,
            vm,
            range,
            protflag,
            error,
            log_fn,
        );
    }
    let _ = process_change_prot_public_log_result(
        PROCESS_CHANGE_PROT_PUBLIC_LOG_EXIT,
        vm,
        range,
        protflag,
        error,
        log_fn,
    );
    error
}

#[no_mangle]
pub unsafe extern "C" fn change_prot_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    protflag: CULong,
) -> CInt {
    process_change_prot_public_result(
        vm,
        range,
        protflag,
        Some(process_change_prot_attr_bridge),
        Some(process_sched_noirq_lock_bridge),
        Some(process_sched_noirq_unlock_bridge),
        Some(process_change_prot_pt_change_bridge),
        Some(process_change_prot_public_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    phys: CULong,
    populate_fault: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    if attr_fn.is_none() || lock_fn.is_none() || unlock_fn.is_none() || pt_set_range_fn.is_none() {
        return -EINVAL;
    }

    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let attr = process_attr_from_vrflag_result((*range).flag, populate_fault, null_mut(), attr_fn);
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let irqstate = process_spin_lock_result(lock_addr, lock_fn);
    let error = process_pt_set_range_result(
        (*address_space).page_table,
        vm,
        (*range).start,
        (*range).end,
        phys,
        attr,
        (*range).pgshift,
        range,
        0,
        pt_set_range_fn,
    );
    let _ = process_spin_unlock_result(lock_addr, irqstate, unlock_fn);
    if error != 0 {
        let _ = process_update_page_table_log_result(error, log_fn);
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn process_update_page_table_public_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    phys: CULong,
    flag: CULong,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    pt_set_range_fn: Option<ProcessPtSetRangeFn>,
    log_fn: Option<ProcessUpdatePageTableLogFn>,
) -> CInt {
    let _ = flag;
    process_update_page_table_body_result(
        vm,
        range,
        phys,
        PF_POPULATE,
        attr_fn,
        lock_fn,
        unlock_fn,
        pt_set_range_fn,
        log_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn update_process_page_table(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    phys: CULong,
    flag: CULong,
) -> CInt {
    process_update_page_table_public_result(
        vm,
        range,
        phys,
        flag,
        Some(process_update_page_table_attr_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_update_page_table_set_range_bridge),
        Some(process_update_page_table_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_body_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
) -> CInt {
    if vm.is_null() {
        return -EFAULT;
    }

    let end = addr.wrapping_add(len as CULong);
    let mut range = process_lookup_memory_range_body_result(vm, addr, end);
    let mut rc = process_access_initial_result(
        (!range.is_null()) as CInt,
        if range.is_null() { 0 } else { (*range).start },
        addr,
    );
    if rc != 0 {
        return rc;
    }

    loop {
        rc = process_access_permission_result(verify_type, (*range).flag);
        if rc != 0 {
            return rc;
        }

        if end <= (*range).end {
            return 0;
        }

        let next = process_next_memory_range_body_result(range);
        rc = process_access_adjacent_result(
            (*range).end,
            (!next.is_null()) as CInt,
            if next.is_null() { 0 } else { (*next).start },
        );
        if rc != 0 {
            return rc;
        }
        range = next;
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_log_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
    error: CInt,
    log_fn: Option<ProcessAccessOkLogFn>,
) -> CInt {
    if let Some(log_fn) = log_fn {
        log_fn(vm, verify_type, addr, len, error);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_access_ok_public_result(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
    log_fn: Option<ProcessAccessOkLogFn>,
) -> CInt {
    let error = process_access_ok_body_result(vm, verify_type, addr, len);
    if error != 0 {
        let _ = process_access_ok_log_result(vm, verify_type, addr, len, error, log_fn);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn access_ok(
    vm: *mut ProcessVm,
    verify_type: CInt,
    addr: CULong,
    len: SizeT,
) -> CInt {
    process_access_ok_public_result(
        vm,
        verify_type,
        addr,
        len,
        Some(process_access_ok_log_bridge),
    )
}

#[inline(always)]
unsafe fn process_do_page_fault_vm_body_impl(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    if vm.is_null() || current_vm.is_null() {
        return -EFAULT;
    }

    if read_lock_fn.is_none()
        || read_unlock_fn.is_none()
        || write_lock_fn.is_none()
        || write_unlock_fn.is_none()
        || normal_fault_fn.is_none()
        || xpmem_fault_fn.is_none()
    {
        return -EINVAL;
    }

    let mut range: *mut VmRange = null_mut();

    if fault_addr >= (*current_vm).region.stack_start && fault_addr < (*current_vm).region.stack_end
    {
        range = process_lookup_memory_range_body_result(
            vm,
            (*current_vm).region.stack_end.wrapping_sub(1),
            (*current_vm).region.stack_end,
        );
        if range.is_null() {
            return -EFAULT;
        }

        if (*range).memobj.is_null() && fault_addr < (*range).start {
            let mut write_locked = 0;
            if (*current_vm).is_memory_range_lock_taken == -1
                || (*current_vm).is_memory_range_lock_taken != current_cpu
            {
                let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
                let error = process_noirq_lock_result(lock_addr, write_lock_fn);
                if error != 0 {
                    return error;
                }
                write_locked = 1;
            }

            process_range_stack_start_commit_result(range, fault_addr, (*range).pgshift);

            if write_locked != 0 {
                let _ = process_noirq_unlock_result(
                    (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
                    write_unlock_fn,
                );
            }
        }
    }

    let mut read_locked = 0;
    if (*current_vm).is_memory_range_lock_taken == -1
        || (*current_vm).is_memory_range_lock_taken != current_cpu
    {
        let error = process_noirq_lock_result(
            (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
            read_lock_fn,
        );
        if error != 0 {
            return error;
        }
        read_locked = 1;
    }

    let error;
    if (*vm).exiting != 0 {
        error = -ECANCELED;
        goto_unlock(read_locked, vm, read_unlock_fn);
        return error;
    }

    if range.is_null() {
        range = process_lookup_memory_range_body_result(vm, fault_addr, fault_addr.wrapping_add(1));
        if range.is_null() {
            error = -EFAULT;
            goto_unlock(read_locked, vm, read_unlock_fn);
            return error;
        }
    }

    if ((*range).flag & VR_PROT_MASK) == VR_PROT_NONE
        || (((reason & PF_WRITE) != 0 && (reason & PF_PATCH) == 0)
            && ((*range).flag & VR_PROT_WRITE) == 0)
        || ((reason & PF_INSTR) != 0 && ((*range).flag & VR_PROT_EXEC) == 0)
    {
        error = -EFAULT;
        goto_unlock(read_locked, vm, read_unlock_fn);
        return error;
    }

    let mut fault_reason = reason;
    if ((*range).flag & VR_PRIVATE) != 0 && !(*range).memobj.is_null() {
        if zeroobj_match_fn.is_none() {
            goto_unlock(read_locked, vm, read_unlock_fn);
            return -EINVAL;
        }
        if process_zeroobj_match_result((*range).memobj, zeroobj_match_fn) != 0 {
            fault_reason |= PF_POPULATE;
        }
    }

    error = if (*range).private_data.is_null() {
        process_fault_range_result(vm, range, fault_addr, fault_reason, normal_fault_fn)
    } else {
        process_fault_range_result(vm, range, fault_addr, fault_reason, xpmem_fault_fn)
    };

    goto_unlock(read_locked, vm, read_unlock_fn);
    error
}

#[no_mangle]
pub unsafe extern "C" fn process_do_page_fault_vm_body_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
) -> CInt {
    unsafe {
        process_do_page_fault_vm_body_impl(
            vm,
            current_vm,
            fault_addr,
            reason,
            current_cpu,
            read_lock_fn,
            read_unlock_fn,
            write_lock_fn,
            write_unlock_fn,
            zeroobj_match_fn,
            normal_fault_fn,
            xpmem_fault_fn,
        )
    }
}

unsafe fn goto_unlock(locked: CInt, vm: *mut ProcessVm, unlock_fn: Option<ProcessNoirqUnlockFn>) {
    if locked != 0 {
        let _ = process_noirq_unlock_result(
            (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong,
            unlock_fn,
        );
    }
}

unsafe fn process_dispatch_pending_pgio(
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    dispatch: ProcessPgioDispatchFn,
) {
    if thread.is_null() {
        return;
    }

    let fp_slot = thread
        .cast::<u8>()
        .add(pgio_fp_offset as usize)
        .cast::<*mut c_void>();
    let arg_slot = thread
        .cast::<u8>()
        .add(pgio_arg_offset as usize)
        .cast::<*mut c_void>();
    let fp = *fp_slot;
    if !fp.is_null() {
        dispatch(fp, *arg_slot);
        *fp_slot = null_mut();
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_dispatch_result(
    vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    fault_fn: Option<ProcessPageFaultVmFn>,
) -> CInt {
    let Some(fault) = fault_fn else {
        return -EINVAL;
    };

    fault(vm, fault_addr, reason)
}

#[no_mangle]
pub unsafe extern "C" fn process_preempt_result(preempt_fn: Option<ProcessPreemptFn>) -> CInt {
    let Some(preempt) = preempt_fn else {
        return -EINVAL;
    };

    preempt();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pgio_dispatch_pending_result(
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    let Some(dispatch) = dispatch_fn else {
        return -EINVAL;
    };

    process_dispatch_pending_pgio(thread, pgio_fp_offset, pgio_arg_offset, dispatch);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_warn_result(
    vm: *mut ProcessVm,
    addr: CULong,
    reason: CULong,
    off: CULong,
    len: SizeT,
    error: CInt,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    let Some(warn) = warn_fn else {
        return 0;
    };

    warn(vm, addr, reason, off, len, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_public_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    current_cpu: CInt,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    if preempt_enable_fn.is_none() || preempt_disable_fn.is_none() || pgio_dispatch_fn.is_none() {
        return -EINVAL;
    }

    loop {
        let error = unsafe {
            process_do_page_fault_vm_body_impl(
                vm,
                current_vm,
                fault_addr,
                reason,
                current_cpu,
                read_lock_fn,
                read_unlock_fn,
                write_lock_fn,
                write_unlock_fn,
                zeroobj_match_fn,
                normal_fault_fn,
                xpmem_fault_fn,
            )
        };
        if error != -ERESTART {
            return error;
        }

        unsafe {
            let _ = process_preempt_result(preempt_enable_fn);
            let _ = process_pgio_dispatch_pending_result(
                thread,
                pgio_fp_offset,
                pgio_arg_offset,
                pgio_dispatch_fn,
            );
            let _ = process_preempt_result(preempt_disable_fn);
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn page_fault_process_vm(
    fault_vm: *mut ProcessVm,
    fault_addr: *mut c_void,
    reason: CULong,
) -> CInt {
    let thread = (*get_this_cpu_local_var()).current;

    process_page_fault_vm_public_result(
        fault_vm,
        (*thread).vm,
        fault_addr as CULong,
        reason,
        ihk_mc_get_processor_id(),
        thread.cast::<c_void>(),
        offset_of!(Thread, pgio_fp) as CULong,
        offset_of!(Thread, pgio_arg) as CULong,
        Some(process_rw_read_lock_bridge),
        Some(process_rw_read_unlock_bridge),
        Some(process_rw_write_lock_bridge),
        Some(process_rw_write_unlock_bridge),
        Some(process_zeroobj_match_bridge),
        Some(process_normal_fault_range_bridge),
        Some(process_xpmem_fault_range_bridge),
        Some(preempt_enable),
        Some(preempt_disable),
        Some(process_pgio_dispatch_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_vm_retry_body_result(
    vm: *mut ProcessVm,
    fault_addr: CULong,
    reason: CULong,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    do_fault_fn: Option<ProcessPageFaultVmFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
) -> CInt {
    if do_fault_fn.is_none()
        || preempt_enable_fn.is_none()
        || preempt_disable_fn.is_none()
        || pgio_dispatch_fn.is_none()
    {
        return -EINVAL;
    }

    loop {
        let error = process_page_fault_vm_dispatch_result(vm, fault_addr, reason, do_fault_fn);
        if error != -ERESTART {
            return error;
        }

        let _ = process_preempt_result(preempt_enable_fn);
        let _ = process_pgio_dispatch_pending_result(
            thread,
            pgio_fp_offset,
            pgio_arg_offset,
            pgio_dispatch_fn,
        );
        let _ = process_preempt_result(preempt_disable_fn);
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_memory_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    len: SizeT,
    page_size: CULong,
    reason: CULong,
    page_fault_fn: Option<ProcessPageFaultVmFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    if page_fault_fn.is_none()
        || preempt_disable_fn.is_none()
        || preempt_enable_fn.is_none()
        || page_size == 0
    {
        return -EINVAL;
    }

    let end = start.wrapping_add(len as CULong);
    let _ = process_preempt_result(preempt_disable_fn);
    let mut addr = start;
    while addr < end {
        let error = process_page_fault_vm_dispatch_result(vm, addr, reason, page_fault_fn);
        if error != 0 {
            let _ = process_populate_warn_result(
                vm,
                addr,
                reason,
                addr.wrapping_sub(start),
                len,
                error,
                warn_fn,
            );
            let _ = process_preempt_result(preempt_enable_fn);
            return error;
        }
        addr = addr.wrapping_add(page_size);
    }

    let _ = process_preempt_result(preempt_enable_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_populate_memory_public_result(
    vm: *mut ProcessVm,
    current_vm: *mut ProcessVm,
    start: CULong,
    len: SizeT,
    page_size: CULong,
    reason: CULong,
    current_cpu: CInt,
    thread: *mut c_void,
    pgio_fp_offset: CULong,
    pgio_arg_offset: CULong,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    write_lock_fn: Option<ProcessNoirqLockFn>,
    write_unlock_fn: Option<ProcessNoirqUnlockFn>,
    zeroobj_match_fn: Option<ProcessZeroobjMatchFn>,
    normal_fault_fn: Option<ProcessFaultRangeFn>,
    xpmem_fault_fn: Option<ProcessFaultRangeFn>,
    preempt_disable_fn: Option<ProcessPreemptFn>,
    preempt_enable_fn: Option<ProcessPreemptFn>,
    pgio_dispatch_fn: Option<ProcessPgioDispatchFn>,
    warn_fn: Option<ProcessPopulateWarnFn>,
) -> CInt {
    if preempt_disable_fn.is_none()
        || preempt_enable_fn.is_none()
        || pgio_dispatch_fn.is_none()
        || page_size == 0
    {
        return -EINVAL;
    }

    let end = start.wrapping_add(len as CULong);
    let _ = process_preempt_result(preempt_disable_fn);

    let mut addr = start;
    while addr < end {
        let error = process_page_fault_vm_public_result(
            vm,
            current_vm,
            addr,
            reason,
            current_cpu,
            thread,
            pgio_fp_offset,
            pgio_arg_offset,
            read_lock_fn,
            read_unlock_fn,
            write_lock_fn,
            write_unlock_fn,
            zeroobj_match_fn,
            normal_fault_fn,
            xpmem_fault_fn,
            preempt_enable_fn,
            preempt_disable_fn,
            pgio_dispatch_fn,
        );
        if error != 0 {
            let _ = process_populate_warn_result(
                vm,
                addr,
                reason,
                addr.wrapping_sub(start),
                len,
                error,
                warn_fn,
            );
            let _ = process_preempt_result(preempt_enable_fn);
            return error;
        }
        addr = addr.wrapping_add(page_size);
    }

    let _ = process_preempt_result(preempt_enable_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn populate_process_memory(
    vm: *mut ProcessVm,
    start: *mut c_void,
    len: SizeT,
) -> CInt {
    let thread = (*get_this_cpu_local_var()).current;

    process_populate_memory_public_result(
        vm,
        (*thread).vm,
        start as CULong,
        len,
        PAGE_SIZE,
        PF_USER | PF_POPULATE,
        ihk_mc_get_processor_id(),
        thread.cast::<c_void>(),
        offset_of!(Thread, pgio_fp) as CULong,
        offset_of!(Thread, pgio_arg) as CULong,
        Some(process_rw_read_lock_bridge),
        Some(process_rw_read_unlock_bridge),
        Some(process_rw_write_lock_bridge),
        Some(process_rw_write_unlock_bridge),
        Some(process_zeroobj_match_bridge),
        Some(process_normal_fault_range_bridge),
        Some(process_xpmem_fault_range_bridge),
        Some(preempt_disable),
        Some(preempt_enable),
        Some(process_pgio_dispatch_bridge),
        Some(process_populate_warn_bridge),
    )
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
pub unsafe extern "C" fn process_memobj_ref_direct_result(memobj: *mut Memobj) -> CInt {
    if memobj.is_null() {
        return -EINVAL;
    }

    memobj_ref(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_memobj_unref_direct_result(memobj: *mut Memobj) -> CInt {
    if memobj.is_null() {
        return -EINVAL;
    }

    memobj_unref(memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_ref_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    let Some(memobj_ref) = memobj_ref_fn else {
        return -EINVAL;
    };

    memobj_ref(memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_ref_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    let Some(memobj_ref) = memobj_ref_fn else {
        return 0;
    };

    memobj_ref(memobj);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_ref_or_direct_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    if let Some(memobj_ref) = memobj_ref_fn {
        memobj_ref(memobj);
        return 0;
    }

    let _ = process_memobj_ref_direct_result(memobj.cast::<Memobj>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_memobj_unref_or_direct_result(
    memobj: *mut c_void,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }
    if let Some(memobj_unref) = memobj_unref_fn {
        memobj_unref(memobj);
        return 0;
    }

    let _ = process_memobj_unref_direct_result(memobj.cast::<Memobj>());
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_ref_or_direct_result(
    memobj: *mut c_void,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }

    process_range_memobj_ref_or_direct_result(memobj, memobj_ref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_range_optional_memobj_unref_or_direct_result(
    memobj: *mut c_void,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if memobj.is_null() {
        return 0;
    }

    process_range_memobj_unref_or_direct_result(memobj, memobj_unref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_insert_result(
    vm: *mut c_void,
    range: *mut VmRange,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
) -> CInt {
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };

    insert(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_publish_result(
    vm: *mut c_void,
    low: *mut VmRange,
    high: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
) -> CInt {
    if low.is_null() || high.is_null() {
        return -EINVAL;
    }
    if insert_fn.is_none() {
        return -EINVAL;
    }
    if !(*low).memobj.is_null() {
        let rc = process_range_memobj_ref_or_direct_result((*low).memobj, memobj_ref_fn);
        if rc != 0 {
            return rc;
        }
    }

    process_split_range_commit_result(low, addr);

    let rc = process_split_range_insert_result(vm, high, insert_fn);
    if rc != 0 {
        return rc;
    }

    if !splitp.is_null() {
        *splitp = high;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_alloc_init_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    splitp: *mut c_void,
    range_size: CULong,
    alloc_flags: CULong,
    errorp: *mut CInt,
    alloc_fn: Option<ProcessSplitRangeAllocFn>,
    log_fn: Option<ProcessSplitRangeAllocLogFn>,
) -> *mut VmRange {
    if errorp.is_null() {
        return null_mut();
    }
    *errorp = 0;

    let Some(alloc) = alloc_fn else {
        *errorp = -EINVAL;
        return null_mut();
    };
    if range.is_null() {
        *errorp = -EINVAL;
        return null_mut();
    }

    let newrange = alloc(range_size, alloc_flags);
    if newrange.is_null() {
        *errorp = -ENOMEM;
        if let Some(log) = log_fn {
            log(vm, range, addr, splitp);
        }
        return null_mut();
    }

    if process_split_range_init_result(range, newrange, addr) == 0 {
        *errorp = -EINVAL;
        return newrange;
    }

    newrange
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_publish_body_result(
    vm: *mut c_void,
    low: *mut VmRange,
    high: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    insert_fn: Option<ProcessSplitRangeInsertFn>,
    log_fn: Option<ProcessSplitRangePublishLogFn>,
) -> CInt {
    let rc =
        process_split_range_publish_result(vm, low, high, addr, splitp, memobj_ref_fn, insert_fn);
    if rc != 0 {
        if let Some(log) = log_fn {
            log(rc);
        }
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn process_split_range_pt_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    split_fn: Option<ProcessSplitRangePtSplitFn>,
    log_fn: Option<ProcessSplitRangePtLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    (*range).pgshift = process_split_pgshift_result((*range).pgshift, addr);

    let Some(split) = split_fn else {
        return -EINVAL;
    };
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let rc = split((*address_space).page_table, vm, range, addr as *mut c_void);
    if rc != 0 {
        if let Some(log) = log_fn {
            log(rc);
        }
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn process_split_shm_log_result(
    event: CInt,
    error: CInt,
    log_fn: Option<ProcessSplitShmLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_split_shm_update_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    page_pgshift_offset: CULong,
    lookup_page_fn: Option<ProcessSplitShmLookupPageFn>,
    phys_to_page_fn: Option<ProcessSplitShmPhysToPageFn>,
    update_page_fn: Option<ProcessSplitShmUpdatePageFn>,
    log_fn: Option<ProcessSplitShmLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let memobj = (*range).memobj;
    if memobj.is_null() {
        return 0;
    }
    if ((*memobj.cast::<Memobj>()).flags & MF_SHM) == 0 {
        return 0;
    }

    let (Some(lookup_page), Some(phys_to_page), Some(update_page)) =
        (lookup_page_fn, phys_to_page_fn, update_page_fn)
    else {
        return -EINVAL;
    };
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let mut phys = 0;
    let off = (*range)
        .objoff
        .wrapping_add(addr.wrapping_sub((*range).start) as OffT);
    let error = lookup_page(memobj, off, 0, &raw mut phys, null_mut());
    if error != 0 && error != -ENOENT {
        let _ = process_split_shm_log_result(PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED, error, log_fn);
        return error;
    }

    let page = phys_to_page(phys);
    if page.is_null() {
        return 0;
    }

    let pgshift = *(page
        .cast::<u8>()
        .wrapping_add(page_pgshift_offset as usize)
        .cast::<CInt>());
    let page_mask = !((1 as CULong).wrapping_shl(pgshift as u32).wrapping_sub(1));
    let error = update_page(
        memobj,
        (*address_space).page_table,
        page,
        (addr & page_mask) as *mut c_void,
    );
    if error != 0 {
        let _ = process_split_shm_log_result(PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED, error, log_fn);
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn split_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
) -> CInt {
    let mut error;
    let mut newrange = null_mut();

    process_split_range_public_log_bridge(
        PROCESS_SPLIT_RANGE_LOG_START,
        vm,
        range,
        addr,
        splitp,
        null_mut(),
        0,
    );

    error = process_split_range_pt_body_result(
        vm,
        range,
        addr,
        Some(process_split_range_pt_split_bridge),
        Some(process_split_range_pt_log_bridge),
    );
    if error != 0 {
        process_split_range_public_log_bridge(
            PROCESS_SPLIT_RANGE_LOG_DONE,
            vm,
            range,
            addr,
            splitp,
            newrange,
            error,
        );
        return error;
    }

    error = process_split_shm_update_body_result(
        vm,
        range,
        addr,
        process_split_page_pgshift_offset_bridge(),
        Some(process_split_shm_lookup_page_bridge),
        Some(process_split_shm_phys_to_page_bridge),
        Some(process_split_shm_update_page_bridge),
        Some(process_split_shm_log_bridge),
    );
    if error != 0 {
        process_split_range_public_log_bridge(
            PROCESS_SPLIT_RANGE_LOG_DONE,
            vm,
            range,
            addr,
            splitp,
            newrange,
            error,
        );
        return error;
    }

    newrange = process_split_range_alloc_init_body_result(
        vm,
        range,
        addr,
        splitp.cast::<c_void>(),
        size_of::<VmRange>() as CULong,
        IHK_MC_AP_NOWAIT,
        &raw mut error,
        Some(process_split_range_alloc_bridge),
        Some(process_split_range_alloc_log_bridge),
    );
    if error != 0 {
        process_split_range_public_log_bridge(
            PROCESS_SPLIT_RANGE_LOG_DONE,
            vm,
            range,
            addr,
            splitp,
            newrange,
            error,
        );
        return error;
    }

    #[cfg(enable_tofu)]
    {
        process_split_range_tofu_init_bridge(newrange);
        process_split_range_tofu_split_bridge(vm, range, newrange, addr);
    }

    error = process_split_range_publish_body_result(
        vm.cast::<c_void>(),
        range,
        newrange,
        addr,
        splitp,
        None,
        Some(process_split_range_insert_bridge),
        Some(process_split_range_publish_log_bridge),
    );
    if error != 0 {
        return error;
    }

    process_split_range_public_log_bridge(
        PROCESS_SPLIT_RANGE_LOG_DONE,
        vm,
        range,
        addr,
        splitp,
        newrange,
        error,
    );
    error
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
pub unsafe extern "C" fn process_join_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessJoinRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_tofu_result(
    vm: *mut c_void,
    surviving: *mut VmRange,
    merging: *mut VmRange,
    tofu_fn: Option<ProcessJoinRangeTofuFn>,
) -> CInt {
    let Some(tofu) = tofu_fn else {
        return 0;
    };

    tofu(vm, surviving, merging)
}

#[no_mangle]
pub unsafe extern "C" fn process_join_range_body_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    cache: *mut *mut c_void,
    cache_count: CInt,
    surviving: *mut VmRange,
    merging: *mut VmRange,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
    free_fn: Option<ProcessJoinRangeFreeFn>,
    tofu_fn: Option<ProcessJoinRangeTofuFn>,
) -> CInt {
    if root.is_null() || cache.is_null() {
        return -EINVAL;
    }
    if free_fn.is_none() {
        return -EINVAL;
    }

    let rc = process_join_range_prepare_result(surviving, merging);
    if rc != 0 {
        return rc;
    }

    if !(*merging).memobj.is_null() {
        let rc = process_range_memobj_unref_or_direct_result((*merging).memobj, memobj_unref_fn);
        if rc != 0 {
            return rc;
        }
    }

    rb_erase(vm_range_rb_node(merging), root);
    process_range_cache_replace_result(cache, cache_count, merging.cast(), surviving.cast());

    let tofu_rc = process_join_range_tofu_result(vm, surviving, merging, tofu_fn);
    if tofu_rc != 0 {
        return tofu_rc;
    }

    process_join_range_free_result(merging, free_fn)
}

#[no_mangle]
pub unsafe extern "C" fn join_process_memory_range(
    vm: *mut ProcessVm,
    surviving: *mut VmRange,
    merging: *mut VmRange,
) -> CInt {
    process_join_range_log_bridge(PROCESS_JOIN_RANGE_LOG_START, vm, surviving, merging, 0);
    let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
    #[cfg(enable_tofu)]
    let tofu_fn: Option<ProcessJoinRangeTofuFn> = Some(process_join_range_tofu_bridge);
    #[cfg(not(enable_tofu))]
    let tofu_fn: Option<ProcessJoinRangeTofuFn> = None;
    let error = process_join_range_body_result(
        vm.cast::<c_void>(),
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        cache,
        VM_RANGE_CACHE_SIZE as CInt,
        surviving,
        merging,
        None,
        Some(process_range_kfree_bridge),
        tofu_fn,
    );
    process_join_range_log_bridge(PROCESS_JOIN_RANGE_LOG_DONE, vm, surviving, merging, error);
    error
}

fn align_down(value: CULong, size: SizeT) -> CULong {
    value & !((size as CULong).wrapping_sub(1))
}

fn align_up(value: CULong, size: SizeT) -> CULong {
    value.wrapping_add(size as CULong).wrapping_sub(1) & !((size as CULong).wrapping_sub(1))
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_page_size_result(
    current: SizeT,
    nextp: *mut SizeT,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
) -> CInt {
    let Some(page_size) = page_size_fn else {
        return -EINVAL;
    };

    page_size(current, nextp)
}

unsafe fn plan_lower_free_bound(
    mut start: CULong,
    has_prev: CInt,
    prev_end: CULong,
    page_size_fn: ProcessFreeRangePageSizeFn,
    first_error: &mut CInt,
) -> CULong {
    let mut pgsize = SizeT::MAX;
    loop {
        let mut next = 0usize;
        let rc = process_free_range_page_size_result(pgsize, &mut next, Some(page_size_fn));
        if rc != 0 {
            if *first_error == 0 {
                *first_error = rc;
            }
            break;
        }
        pgsize = next;
        let candidate = align_down(start, pgsize);
        if has_prev == 0 || prev_end <= candidate {
            start = candidate;
            break;
        }
    }
    start
}

unsafe fn plan_upper_free_bound(
    mut end: CULong,
    has_next: CInt,
    next_start: CULong,
    page_size_fn: ProcessFreeRangePageSizeFn,
    first_error: &mut CInt,
) -> CULong {
    let mut pgsize = SizeT::MAX;
    loop {
        let mut next = 0usize;
        let rc = process_free_range_page_size_result(pgsize, &mut next, Some(page_size_fn));
        if rc != 0 {
            if *first_error == 0 {
                *first_error = rc;
            }
            break;
        }
        pgsize = next;
        let candidate = align_up(end, pgsize);
        if has_next == 0 || candidate <= next_start {
            end = candidate;
            break;
        }
    }
    end
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_plan_result(
    range: *const VmRange,
    straight_va: CULong,
    has_prev: CInt,
    prev_end: CULong,
    has_next: CInt,
    next_start: CULong,
    has_memobj: CInt,
    memobj_flags: u32,
    startp: *mut CULong,
    endp: *mut CULong,
    actionp: *mut CInt,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
) -> CInt {
    if range.is_null() || startp.is_null() || endp.is_null() || actionp.is_null() {
        return -EINVAL;
    }

    let mut start = (*range).start;
    let mut end = (*range).end;
    let mut action = PROCESS_FREE_RANGE_PT_SKIP;
    let mut first_error = 0;

    if (*range).straight_start == 0 && (*range).start != straight_va {
        if ((*range).flag & (VR_REMOTE | VR_IO_NOCACHE | VR_RESERVED)) != 0 {
            action = PROCESS_FREE_RANGE_PT_CLEAR;
        } else {
            let Some(page_size_fn) = page_size_fn else {
                return -EINVAL;
            };
            start =
                plan_lower_free_bound(start, has_prev, prev_end, page_size_fn, &mut first_error);
            end = plan_upper_free_bound(end, has_next, next_start, page_size_fn, &mut first_error);
            action = if has_memobj != 0 && (memobj_flags & MF_HUGETLBFS) != 0 {
                PROCESS_FREE_RANGE_PT_CLEAR
            } else {
                PROCESS_FREE_RANGE_PT_FREE
            };
        }
    }

    *startp = start;
    *endp = end;
    *actionp = action;
    first_error
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_finalize_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    cache: *mut *mut c_void,
    cache_count: CInt,
    range: *mut VmRange,
    straight_va: CULong,
    straight_lenp: *mut SizeT,
    straight_pa: CULong,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
    free_fn: Option<ProcessFreeRangeFreeFn>,
) -> CInt {
    if root.is_null() || cache.is_null() || range.is_null() || straight_lenp.is_null() {
        return -EINVAL;
    }
    if free_fn.is_none() {
        return -EINVAL;
    }

    let needs_straight_free = (*range).straight_start != 0;
    let straight_len = *straight_lenp;
    let is_main_straight = !needs_straight_free
        && (*range).start == straight_va
        && (*range).end == straight_va.wrapping_add(straight_len as CULong);

    if needs_straight_free && (phys_to_virt_fn.is_none() || free_pages_fn.is_none()) {
        return -EINVAL;
    }
    if is_main_straight && clear_main_fn.is_none() {
        return -EINVAL;
    }

    rb_erase(vm_range_rb_node(range), root);
    process_range_cache_replace_result(cache, cache_count, range.cast(), null_mut());

    if needs_straight_free {
        let phys = straight_pa.wrapping_add((*range).straight_start.wrapping_sub(straight_va));
        let addr = process_free_range_phys_to_virt_result(phys, phys_to_virt_fn);
        let pages = (*range).end.wrapping_sub((*range).start) >> PAGE_SHIFT;
        let rc = process_free_range_free_pages_result(addr, pages, free_pages_fn);
        if rc != 0 {
            return rc;
        }
    } else if is_main_straight {
        let _ =
            process_free_range_clear_main_result(vm, (*range).start, (*range).end, clear_main_fn);
        *straight_lenp = 0;
    }

    process_free_range_free_result(range, free_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_phys_to_virt_result(
    phys: CULong,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
) -> *mut c_void {
    let Some(phys_to_virt) = phys_to_virt_fn else {
        return null_mut();
    };

    phys_to_virt(phys)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_free_pages_result(
    addr: *mut c_void,
    pages: CULong,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
) -> CInt {
    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };

    free_pages(addr, pages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_clear_main_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
) -> CInt {
    let Some(clear_main) = clear_main_fn else {
        return -EINVAL;
    };

    clear_main(vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_free_result(
    range: *mut VmRange,
    free_fn: Option<ProcessFreeRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_free_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    memobj: *mut c_void,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
) -> CInt {
    let Some(pt_free) = pt_free_fn else {
        return -EINVAL;
    };

    pt_free(page_table, vm, start, end, memobj)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_pt_clear_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    pt_clear_fn: Option<ProcessFreeRangePtClearFn>,
) -> CInt {
    let Some(pt_clear) = pt_clear_fn else {
        return -EINVAL;
    };

    pt_clear(page_table, vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_tofu_remove_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    tofu_remove_fn: Option<ProcessFreeRangeTofuRemoveFn>,
) -> CInt {
    let Some(tofu_remove) = tofu_remove_fn else {
        return 0;
    };

    tofu_remove(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_range_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
    log_fn: Option<ProcessFreeRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, range, start, end, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_free_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    straight_va: CULong,
    straight_lenp: *mut SizeT,
    straight_pa: CULong,
    tofu_enabled: CInt,
    page_size_fn: Option<ProcessFreeRangePageSizeFn>,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
    memobj_unref_fn: Option<ProcessRangeMemobjRefFn>,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
    pt_clear_fn: Option<ProcessFreeRangePtClearFn>,
    tofu_remove_fn: Option<ProcessFreeRangeTofuRemoveFn>,
    phys_to_virt_fn: Option<ProcessFreeRangePhysToVirtFn>,
    free_pages_fn: Option<ProcessFreeRangePagesFn>,
    clear_main_fn: Option<ProcessFreeRangeClearMainFn>,
    free_fn: Option<ProcessFreeRangeFreeFn>,
    log_fn: Option<ProcessFreeRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || straight_lenp.is_null() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let start0 = (*range).start;
    let end0 = (*range).end;
    let mut start = start0;
    let mut end = end0;
    let prev = process_previous_memory_range_body_result(range);
    let next = process_next_memory_range_body_result(range);
    let has_memobj = !(*range).memobj.is_null();
    let memobj_flags = if has_memobj {
        (*(*range).memobj.cast::<Memobj>()).flags
    } else {
        0
    };
    let mut pt_action = PROCESS_FREE_RANGE_PT_SKIP;
    let mut error = process_free_range_pt_plan_result(
        range,
        straight_va,
        (!prev.is_null()) as CInt,
        if prev.is_null() { 0 } else { (*prev).end },
        (!next.is_null()) as CInt,
        if next.is_null() { 0 } else { (*next).start },
        has_memobj as CInt,
        memobj_flags,
        &raw mut start,
        &raw mut end,
        &raw mut pt_action,
        page_size_fn,
    );
    if error != 0 {
        let _ = process_free_range_log_result(
            PROCESS_FREE_BODY_LOG_PLAN_FAILED,
            vm,
            range,
            start,
            end,
            error,
            log_fn,
        );
    }

    if pt_action != PROCESS_FREE_RANGE_PT_SKIP {
        if lock_fn.is_none() || unlock_fn.is_none() {
            return -EINVAL;
        }
        let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;

        if pt_action == PROCESS_FREE_RANGE_PT_FREE {
            if pt_free_fn.is_none() {
                return -EINVAL;
            }
            let _ = process_noirq_lock_result(lock_addr, lock_fn);
            let _ =
                process_range_optional_memobj_ref_or_direct_result((*range).memobj, memobj_ref_fn);
            error = process_free_range_pt_free_result(
                (*address_space).page_table,
                vm,
                start,
                end,
                (*range).memobj,
                pt_free_fn,
            );
            let _ = process_range_optional_memobj_unref_or_direct_result(
                (*range).memobj,
                memobj_unref_fn,
            );
            let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
            if error != 0 && error != -ENOENT {
                let _ = process_free_range_log_result(
                    PROCESS_FREE_BODY_LOG_PT_FREE_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    error,
                    log_fn,
                );
            }
        } else if pt_action == PROCESS_FREE_RANGE_PT_CLEAR {
            if pt_clear_fn.is_none() {
                return -EINVAL;
            }
            let _ = process_noirq_lock_result(lock_addr, lock_fn);
            error = process_free_range_pt_clear_result(
                (*address_space).page_table,
                vm,
                start,
                end,
                pt_clear_fn,
            );
            let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
            if error != 0 && error != -ENOENT {
                let _ = process_free_range_log_result(
                    PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    error,
                    log_fn,
                );
            }
        }

        let _ =
            process_range_optional_memobj_unref_or_direct_result((*range).memobj, memobj_unref_fn);
    }

    if tofu_enabled != 0 {
        let entries = process_free_range_tofu_remove_result(vm, range, tofu_remove_fn);
        if entries > 0 {
            let _ = process_free_range_log_result(
                PROCESS_FREE_BODY_LOG_TOFU_REMOVED,
                vm,
                range,
                start0,
                end0,
                entries,
                log_fn,
            );
        }
    }

    let root = (&raw mut (*vm).vm_range_tree).cast::<RbRoot>();
    let cache = (&raw mut (*vm).range_cache).cast::<*mut c_void>();
    error = process_free_range_finalize_result(
        vm.cast(),
        root,
        cache,
        crate::abi::VM_RANGE_CACHE_SIZE as CInt,
        range,
        straight_va,
        straight_lenp,
        straight_pa,
        phys_to_virt_fn,
        free_pages_fn,
        clear_main_fn,
        free_fn,
    );
    if error != 0 {
        let _ = process_free_range_log_result(
            PROCESS_FREE_BODY_LOG_FINALIZE_FAILED,
            vm,
            range,
            start0,
            end0,
            error,
            log_fn,
        );
        return error;
    }

    let _ = process_free_range_log_result(
        PROCESS_FREE_BODY_LOG_DONE,
        vm,
        range,
        start0,
        end0,
        0,
        log_fn,
    );

    0
}

/// Own the actual former C sync callback. The caller retains the live PTE,
/// args/memobj and existing page-table exclusion for the synchronous visit.
/// Valid pgshift is the original supported 0..63 domain. No new error policy,
/// ownership transfer, allocation or lock is introduced.
/// Existing synchronous range-sync failure notification. No pointer is
/// dereferenced or retained; caller lock/ref/notification ordering is unchanged.
#[no_mangle]
pub unsafe extern "C" fn process_sync_range_log_bridge(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    error: CInt,
) {
    let _ = kprintf(
        b"sync_process_memory_range(%p,%p,%#lx,%#lx):visit failed%d\n\0".as_ptr().cast(),
        vm, range, start, end, error,
    );
}

#[no_mangle]
pub unsafe extern "C" fn sync_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut error = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_entry_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d)\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    if crate::pte_helpers::pte_is_null(pte) == 0
        && crate::pte_helpers::pte_is_fileoff(pte, pgsize) == 0
        && crate::pte_helpers::pte_is_dirty(pte, pgsize) != 0
    {
        crate::pte_helpers::pte_clear_dirty(pte, pgsize);
        crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);
        // Original ordering: read physical PTE after the TLB-effect callback,
        // then inspect zero-fill flags before the existing memobj operation.
        let phys = crate::pte_helpers::pte_get_phys(pte);
        let memobj = (*arg0.cast::<ProcessSyncArgs>()).memobj;
        if (*memobj).flags & MF_ZEROFILL == 0 {
            error = crate::object_helpers::memobj_flush_page(memobj, phys, pgsize);
            if error != 0 {
                let _ = kprintf(
                    b"sync_one_page(%p,%p,%p %#lx,%p,%d):flush failed. %d\n\0".as_ptr().cast(),
                    arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
                );
                crate::pte_helpers::pte_set_dirty(pte, pgsize);
            }
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_sync_one_page_exit_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"sync_one_page(%p,%p,%p %#lx,%p,%d):%d\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, error,
        );
    }
    error
}

/// Replace the actual former C remap visitor. The existing outer caller
/// keeps its page-table exclusion and memobj reference for the synchronous
/// visit; page_unmap owns its existing mapped-page/hash accounting. No new
/// lock, reference, ownership transfer or error policy is introduced.
#[no_mangle]
pub unsafe extern "C" fn remap_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    let args = arg0.cast::<ProcessRemapArgs>();
    let pgsize = (1 as SizeT).wrapping_shl(pgshift as u32);
    let pte = ptep.cast::<CULong>();
    let mut old_pte: CULong = 0;
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_entry_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d)\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift,
        );
    }
    // Preserve C's unsigned uintptr_t arithmetic and LP64 off_t conversion.
    // Both argument loads occur after the entry logger, as in the C body.
    let off = ((*args).off as CULong)
        .wrapping_add((pgaddr as CULong).wrapping_sub((*args).start)) as OffT;
    crate::pte_helpers::pte_make_fileoff(off, 0, pgsize, &raw mut old_pte);
    crate::pte_helpers::pte_xchg(pte, &raw mut old_pte);
    crate::x86_memory_helpers::flush_tlb_single(pgaddr as CULong);

    // All mapping-release decisions use the exchanged snapshot, never a PTE
    // subsequently published at ptep by the existing TLB/flush boundaries.
    if crate::pte_helpers::pte_is_null(&raw const old_pte) == 0
        && crate::pte_helpers::pte_is_fileoff(&raw const old_pte, pgsize) == 0
    {
        let phys = crate::pte_helpers::pte_get_phys(&raw const old_pte);
        if crate::pte_helpers::pte_is_dirty(&raw const old_pte, pgsize) != 0 {
            // The original remap visitor deliberately ignores this result.
            let _ = crate::object_helpers::memobj_flush_page((*args).memobj, phys, pgsize);
        }
        // Existing public phys_to_page provider retains its C forwarding
        // wrapper and Rust lookup implementation; it is explicit provider debt.
        let page = phys_to_page(phys);
        if !page.is_null() && crate::page_helpers::page_unmap(page) != 0 {
            let address = crate::x86_memory_helpers::phys_to_virt(phys);
            crate::mem_helpers::_ihk_mc_free_pages(
                address,
                (pgsize / PAGE_SIZE as SizeT) as CInt,
                1, // existing IHK_MC_PG_USER, checked against actual mm.h
                process_remap_free_file as *mut i8,
                process_remap_free_line,
            );
            if core::ptr::read_volatile(core::ptr::addr_of!(
                process_remap_one_page_rss_debug.line_flags
            )) >> 24 != 0 {
                // Original %ld payloads are the unsigned size_t values.
                let _ = kprintf(
                    b"%lx-,%s: calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                    phys, b"remap_one_page\0".as_ptr().cast::<i8>(), pgsize, pgsize,
                );
            }
            // Reload args->memobj after free/log callbacks, and retain C's
            // narrowing conversion from size_t to the provider's int pgsize.
            crate::mem_helpers::rusage_memory_stat_sub((*args).memobj, pgsize as CULong, pgsize as CInt);
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_remap_one_page_exit_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"remap_one_page(%p,%p,%p %#lx,%p,%d): %d\n\0".as_ptr().cast(),
            arg0, page_table, ptep, *pte, pgaddr, pgshift, 0 as CInt,
        );
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_sync_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessSyncRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let zero_fill = ((*memobj).flags & MF_ZEROFILL) != 0;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    if !zero_fill {
        let _ = process_memobj_ref_direct_result(memobj);
    }

    let error = visit(
        (*(*vm).address_space).page_table,
        start,
        end,
        (*range).pgshift,
        VPTEF_SKIP_NULL,
        visit_step_fn,
        arg,
    );

    if !zero_fill {
        let _ = process_memobj_unref_direct_result(memobj);
    }
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if error != 0 {
        if let Some(log) = log_fn {
            log(vm, range, start, end, error);
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn sync_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
) -> CInt {
    let memobj = if range.is_null() {
        null_mut()
    } else {
        (*range).memobj.cast::<Memobj>()
    };
    let mut args = ProcessSyncArgs { memobj };

    process_sync_memory_range_body_result(
        vm,
        range,
        start,
        end,
        (&mut args as *mut ProcessSyncArgs).cast(),
        sync_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_sync_range_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_remap_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    off: OffT,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessRemapRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    let _ = process_memobj_ref_direct_result(memobj);

    let pgshift = AtomicI32::from_ptr(&raw mut (*range).pgshift);
    let old_pgshift =
        match pgshift.compare_exchange(0, PAGE_SHIFT as CInt, Ordering::SeqCst, Ordering::SeqCst) {
            Ok(old) | Err(old) => old,
        };

    let error = if old_pgshift != 0 && old_pgshift != PAGE_SHIFT as CInt {
        let error = -E2BIG;
        if let Some(log) = log_fn {
            log(
                PROCESS_REMAP_RANGE_LOG_PGSHIFT,
                vm,
                range,
                start,
                end,
                off,
                old_pgshift,
                error,
            );
        }
        error
    } else {
        let error = visit(
            (*(*vm).address_space).page_table,
            start,
            end,
            (*range).pgshift,
            0,
            visit_step_fn,
            arg,
        );
        if error != 0 {
            if let Some(log) = log_fn {
                log(
                    PROCESS_REMAP_RANGE_LOG_VISIT_FAILED,
                    vm,
                    range,
                    start,
                    end,
                    off,
                    old_pgshift,
                    error,
                );
            }
        }
        error
    };

    let _ = process_memobj_unref_direct_result(memobj);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);
    error
}

#[no_mangle]
pub unsafe extern "C" fn remap_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    off: OffT,
) -> CInt {
    let memobj = if range.is_null() {
        null_mut()
    } else {
        (*range).memobj.cast::<Memobj>()
    };
    let mut args = ProcessRemapArgs { off, start, memobj };

    process_remap_memory_range_body_result(
        vm,
        range,
        start,
        end,
        off,
        (&mut args as *mut ProcessRemapArgs).cast(),
        remap_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_remap_range_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_invalidate_memory_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
    arg: *mut c_void,
    visit_step_fn: *mut c_void,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    lookup_pte_fn: Option<ProcessLookupPteFn>,
    pte_contiguous_fn: Option<ProcessPteTestFn>,
    pte_head_fn: Option<ProcessPtePgsizeTestFn>,
    pte_tail_fn: Option<ProcessPtePgsizeTestFn>,
    split_fn: Option<ProcessSplitContiguousPagesFn>,
    pt_free_fn: Option<ProcessFreeRangePtFreeFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    log_fn: Option<ProcessSyncRangeLogFn>,
) -> CInt {
    if vm.is_null() || range.is_null() || (*vm).address_space.is_null() || (*range).memobj.is_null()
    {
        return -EINVAL;
    }
    if lock_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }
    let Some(lookup_pte) = lookup_pte_fn else {
        return -EINVAL;
    };
    let Some(pte_contiguous) = pte_contiguous_fn else {
        return -EINVAL;
    };
    let Some(pte_head) = pte_head_fn else {
        return -EINVAL;
    };
    let Some(pte_tail) = pte_tail_fn else {
        return -EINVAL;
    };
    let Some(split) = split_fn else {
        return -EINVAL;
    };
    let Some(pt_free) = pt_free_fn else {
        return -EINVAL;
    };
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };

    let memobj = (*range).memobj.cast::<Memobj>();
    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<u8>() as CULong;
    let page_table = (*(*vm).address_space).page_table;
    let mut error = 0;
    let mut should_log = false;
    let mut pgsize: SizeT = 0;

    let _ = process_noirq_lock_result(lock_addr, lock_fn);
    let _ = process_memobj_ref_direct_result(memobj);

    let ptep = lookup_pte(page_table, start, 0, &raw mut pgsize);
    if !ptep.is_null() && pte_contiguous(ptep) != 0 && pte_head(ptep, pgsize) == 0 {
        error = split(ptep, pgsize, (*memobj).flags);
    }

    if error == 0 {
        pgsize = 0;
        let ptep = lookup_pte(page_table, end - 1, 0, &raw mut pgsize);
        if !ptep.is_null() && pte_contiguous(ptep) != 0 && pte_tail(ptep, pgsize) == 0 {
            error = split(ptep, pgsize, (*memobj).flags);
        }
    }

    if error == 0 {
        should_log = true;
        if ((*memobj).flags & MF_SHM) != 0 {
            error = pt_free(page_table, vm, start, end, memobj.cast::<c_void>());
        } else {
            error = visit(
                page_table,
                start,
                end,
                (*range).pgshift,
                VPTEF_SKIP_NULL,
                visit_step_fn,
                arg,
            );
        }
    }

    let _ = process_memobj_unref_direct_result(memobj);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    if should_log && error != 0 {
        if let Some(log) = log_fn {
            log(vm, range, start, end, error);
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn process_invalidate_one_page_body_result(
    arg: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
    pte_null_fn: Option<ProcessPteTestFn>,
    pte_fileoff_fn: Option<ProcessPtePgsizeTestFn>,
    pte_get_phys_fn: Option<ProcessPteGetPhysFn>,
    phys_to_page_fn: Option<ProcessPhysToPageFn>,
    page_offset_fn: Option<ProcessPageOffsetFn>,
    pte_make_fileoff_fn: Option<ProcessPteMakeFileoffFn>,
    pte_xchg_fn: Option<ProcessPteXchgFn>,
    flush_tlb_single_fn: Option<ProcessFlushTlbSingleFn>,
    pte_contiguous_fn: Option<ProcessPteTestFn>,
    pte_head_fn: Option<ProcessPtePgsizeTestFn>,
    pgsize_to_tbllv_fn: Option<ProcessPgsizeToTbllvFn>,
    tbllv_to_contpgsize_fn: Option<ProcessTbllvToContpgsizeFn>,
    page_unmap_fn: Option<ProcessPageUnmapFn>,
    panic_fn: Option<ProcessPanicFn>,
    memobj_invalidate_page_fn: Option<ProcessMemobjInvalidatePageFn>,
    log_fn: Option<ProcessInvalidateOnePageLogFn>,
) -> CInt {
    if arg.is_null() || ptep.is_null() || pgshift < 0 || pgshift as usize >= SizeT::BITS as usize {
        return -EINVAL;
    }
    let Some(pte_null) = pte_null_fn else {
        return -EINVAL;
    };
    let Some(pte_fileoff) = pte_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_get_phys) = pte_get_phys_fn else {
        return -EINVAL;
    };
    let Some(phys_to_page) = phys_to_page_fn else {
        return -EINVAL;
    };
    let Some(page_offset) = page_offset_fn else {
        return -EINVAL;
    };
    let Some(pte_make_fileoff) = pte_make_fileoff_fn else {
        return -EINVAL;
    };
    let Some(pte_xchg) = pte_xchg_fn else {
        return -EINVAL;
    };
    let Some(flush_tlb_single) = flush_tlb_single_fn else {
        return -EINVAL;
    };
    let Some(pte_contiguous) = pte_contiguous_fn else {
        return -EINVAL;
    };
    let Some(pte_head) = pte_head_fn else {
        return -EINVAL;
    };
    let Some(pgsize_to_tbllv) = pgsize_to_tbllv_fn else {
        return -EINVAL;
    };
    let Some(tbllv_to_contpgsize) = tbllv_to_contpgsize_fn else {
        return -EINVAL;
    };
    let Some(page_unmap) = page_unmap_fn else {
        return -EINVAL;
    };
    let Some(panic_call) = panic_fn else {
        return -EINVAL;
    };
    let Some(memobj_invalidate_page) = memobj_invalidate_page_fn else {
        return -EINVAL;
    };

    let range = *(arg.cast::<*mut VmRange>());
    if range.is_null() || (*range).memobj.is_null() {
        return -EINVAL;
    }

    let pgsize = 1usize << (pgshift as usize);
    if pte_null(ptep) != 0 || pte_fileoff(ptep, pgsize) != 0 {
        return 0;
    }

    let phys = pte_get_phys(ptep);
    let page = phys_to_page(phys);
    let linear_off = (*range)
        .objoff
        .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start) as OffT);
    let mut apte: CULong = 0;

    if !page.is_null() {
        let page_off = page_offset(page);

        if page_off != linear_off {
            pte_make_fileoff(page_off, pgsize, (&raw mut apte).cast::<c_void>());
        }
    }

    pte_xchg(ptep, (&raw mut apte).cast::<c_void>());
    flush_tlb_single(pgaddr as CULong);

    let memobj_pgsize = if pte_contiguous((&raw mut apte).cast::<c_void>()) != 0 {
        if pte_head(ptep, pgsize) != 0 {
            tbllv_to_contpgsize(pgsize_to_tbllv(pgsize))
        } else {
            return 0;
        }
    } else {
        pgsize
    };

    if !page.is_null() && page_unmap(page) != 0 {
        panic_call(b"invalidate_one_page\0".as_ptr().cast::<i8>());
    }

    let error = memobj_invalidate_page((*range).memobj.cast::<Memobj>(), phys, memobj_pgsize);
    if error != 0 {
        if let Some(log) = log_fn {
            log(
                arg,
                page_table,
                ptep,
                *(ptep.cast::<CULong>()),
                pgaddr,
                pgshift,
                error,
            );
        }
    }

    error
}

#[no_mangle]
pub unsafe extern "C" fn invalidate_one_page(
    arg0: *mut c_void,
    page_table: *mut c_void,
    ptep: *mut c_void,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    process_invalidate_one_page_body_result(
        arg0,
        page_table,
        ptep,
        pgaddr,
        pgshift,
        Some(process_pte_is_null_bridge),
        Some(process_pte_is_fileoff_bridge),
        Some(process_pte_get_phys_bridge),
        Some(process_phys_to_page_bridge),
        Some(process_page_offset_bridge),
        Some(process_pte_make_fileoff_bridge),
        Some(process_pte_xchg_bridge),
        Some(process_flush_tlb_single_bridge),
        Some(process_pte_is_contiguous_bridge),
        Some(process_page_is_contiguous_head_bridge),
        Some(process_pgsize_to_tbllv_bridge),
        Some(process_tbllv_to_contpgsize_bridge),
        Some(process_page_unmap_bridge),
        Some(process_panic_bridge),
        Some(process_memobj_invalidate_page_bridge),
        Some(process_invalidate_one_page_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn invalidate_process_memory_range(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    start: CULong,
    end: CULong,
) -> CInt {
    let mut args = range;

    process_invalidate_memory_range_body_result(
        vm,
        range,
        start,
        end,
        (&mut args as *mut *mut VmRange).cast(),
        invalidate_one_page as *mut c_void,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_lookup_pte_bridge),
        Some(process_pte_is_contiguous_bridge),
        Some(process_page_is_contiguous_head_bridge),
        Some(process_page_is_contiguous_tail_bridge),
        Some(process_split_contiguous_pages_bridge),
        Some(process_free_range_pt_free_bridge),
        Some(process_visit_pte_range_bridge),
        Some(process_invalidate_range_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_straight_convert_result(
    straight_va: CULong,
    straight_len: SizeT,
    range: *const VmRange,
    start: CULong,
    end: CULong,
    new_startp: *mut CULong,
    new_endp: *mut CULong,
    lenp: *mut CULong,
) -> CInt {
    if new_startp.is_null() || new_endp.is_null() || lenp.is_null() {
        return -EINVAL;
    }

    let len = end.wrapping_sub(start);
    *new_startp = start;
    *new_endp = end;
    *lenp = len;

    let straight_end = straight_va.wrapping_add(straight_len as CULong);
    let needs_conversion = straight_va != 0
        && start >= straight_va
        && end <= straight_end
        && !(start == straight_va && end == straight_end);
    if !needs_conversion {
        return PROCESS_REMOVE_STRAIGHT_NO_CONVERT;
    }
    if range.is_null() {
        return PROCESS_REMOVE_STRAIGHT_NEED_RANGE;
    }

    let range_len = (*range).end.wrapping_sub((*range).start);
    let range_straight_end = (*range).straight_start.wrapping_add(range_len);
    if (*range).straight_start != 0
        && start >= (*range).straight_start
        && start < range_straight_end
    {
        let new_start = (*range)
            .start
            .wrapping_add(start.wrapping_sub((*range).straight_start));
        *new_startp = new_start;
        *new_endp = new_start.wrapping_add(len);
        return PROCESS_REMOVE_STRAIGHT_CONVERTED;
    }

    PROCESS_REMOVE_STRAIGHT_NEED_RANGE
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_split_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    addr: CULong,
    splitp: *mut *mut VmRange,
    split_fn: Option<ProcessRemoveRangeSplitFn>,
) -> CInt {
    let Some(split) = split_fn else {
        return -EINVAL;
    };

    split(vm, range, addr, splitp)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_xpmem_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    xpmem_remove_fn: Option<ProcessRemoveRangeXpmemFn>,
) -> CInt {
    let Some(xpmem_remove) = xpmem_remove_fn else {
        return -EINVAL;
    };

    xpmem_remove(vm, range);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_free_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(vm.cast(), range.cast())
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_range_log_result(
    event: CInt,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    range: *mut VmRange,
    error: CInt,
    log_fn: Option<ProcessRemoveRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(event, vm, start, end, range, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_memory_range_body_result(
    vm: *mut ProcessVm,
    mut start: CULong,
    mut end: CULong,
    ro_freedp: *mut CInt,
    straight_va: CULong,
    straight_len: SizeT,
    split_fn: Option<ProcessRemoveRangeSplitFn>,
    xpmem_remove_fn: Option<ProcessRemoveRangeXpmemFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessRemoveRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(split_fn) = split_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    let mut converted_start = start;
    let mut converted_end = end;
    let mut len = end.wrapping_sub(start);
    let mut action = process_remove_straight_convert_result(
        straight_va,
        straight_len,
        core::ptr::null(),
        start,
        end,
        &mut converted_start,
        &mut converted_end,
        &mut len,
    );

    if action == PROCESS_REMOVE_STRAIGHT_NEED_RANGE {
        let mut range_iter = process_lookup_memory_range_body_result(vm, 0, CULong::MAX);
        let mut converted_range: *mut VmRange = null_mut();

        while !range_iter.is_null() {
            action = process_remove_straight_convert_result(
                straight_va,
                straight_len,
                range_iter,
                start,
                end,
                &mut converted_start,
                &mut converted_end,
                &mut len,
            );
            if action == PROCESS_REMOVE_STRAIGHT_CONVERTED {
                converted_range = range_iter;
                break;
            }
            range_iter = process_next_memory_range_body_result(range_iter);
        }

        if converted_range.is_null() {
            let _ = process_remove_range_log_result(
                PROCESS_REMOVE_RANGE_LOG_NO_STRAIGHT,
                vm,
                start,
                end,
                null_mut(),
                0,
                log_fn,
            );
            return 0;
        }

        let _ = process_remove_range_log_result(
            PROCESS_REMOVE_RANGE_LOG_CONVERTED,
            vm,
            converted_start,
            converted_end,
            converted_range,
            0,
            log_fn,
        );
        start = converted_start;
        end = converted_end;
    }

    let mut ro_freed = 0;
    let mut next = process_lookup_memory_range_body_result(vm, start, end);
    while !next.is_null() && (*next).start < end {
        let mut range = next;
        next = process_next_memory_range_body_result(range);

        let mut split_start = 0;
        let mut split_end = 0;
        let mut mark_ro_freed = 0;
        let mut remove_xpmem = 0;
        process_remove_range_step_result(
            (*range).start,
            (*range).end,
            start,
            end,
            (*range).flag,
            (*range).private_data as CULong,
            &mut split_start,
            &mut split_end,
            &mut mark_ro_freed,
            &mut remove_xpmem,
        );

        if split_start != 0 {
            let rc =
                process_remove_range_split_result(vm, range, start, &mut range, Some(split_fn));
            if rc != 0 {
                let _ = process_remove_range_log_result(
                    PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
                    vm,
                    start,
                    end,
                    range,
                    rc,
                    log_fn,
                );
                return rc;
            }
        }

        if split_end != 0 {
            let rc = process_remove_range_split_result(vm, range, end, null_mut(), Some(split_fn));
            if rc != 0 {
                let _ = process_remove_range_log_result(
                    PROCESS_REMOVE_RANGE_LOG_SPLIT_FAILED,
                    vm,
                    start,
                    end,
                    range,
                    rc,
                    log_fn,
                );
                return rc;
            }
        }

        if mark_ro_freed != 0 {
            ro_freed = 1;
        }

        if remove_xpmem != 0 {
            let rc = process_remove_range_xpmem_result(vm, range, xpmem_remove_fn);
            if rc != 0 {
                return rc;
            }
        }

        let rc = process_remove_range_free_result(vm, range, Some(free_fn));
        if rc != 0 {
            let _ = process_remove_range_log_result(
                PROCESS_REMOVE_RANGE_LOG_FREE_FAILED,
                vm,
                start,
                end,
                range,
                rc,
                log_fn,
            );
            return rc;
        }
    }

    if !ro_freedp.is_null() {
        *ro_freedp = ro_freed;
    }
    let _ = process_remove_range_log_result(
        PROCESS_REMOVE_RANGE_LOG_DONE,
        vm,
        start,
        end,
        null_mut(),
        ro_freed,
        log_fn,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn remove_process_memory_range(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    ro_freedp: *mut CInt,
) -> CInt {
    if vm.is_null() || (*vm).proc.is_null() {
        return -EINVAL;
    }

    let proc = (*vm).proc.cast::<Process>();
    process_remove_memory_range_body_result(
        vm,
        start,
        end,
        ro_freedp,
        (*proc).straight_va as CULong,
        (*proc).straight_len,
        Some(process_remove_range_split_bridge),
        Some(process_remove_range_xpmem_bridge),
        Some(process_memory_range_free_bridge),
        Some(process_remove_range_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_body_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    clear_fn: Option<ProcessRemoveRegionClearFn>,
    log_fn: Option<ProcessRemoveRegionLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }

    let rc = process_remove_region_alignment_result(start, end);
    if rc != 0 {
        return rc;
    }

    if lock_fn.is_none() || unlock_fn.is_none() || clear_fn.is_none() {
        return -EINVAL;
    }
    let address_space = (*vm).address_space;
    if address_space.is_null() {
        return -EINVAL;
    }

    let lock_addr = (&raw mut (*vm).page_table_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, lock_fn);
    if rc != 0 {
        return rc;
    }
    let _ =
        process_remove_region_clear_result((*address_space).page_table, vm, start, end, clear_fn);
    let _ = process_noirq_unlock_result(lock_addr, unlock_fn);

    process_remove_region_log_result(vm, start, end, log_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_clear_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    clear_fn: Option<ProcessRemoveRegionClearFn>,
) -> CInt {
    let Some(clear) = clear_fn else {
        return -EINVAL;
    };

    clear(page_table, vm, start, end)
}

#[no_mangle]
pub unsafe extern "C" fn process_remove_region_log_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    log_fn: Option<ProcessRemoveRegionLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(vm, start, end);
    0
}

#[no_mangle]
pub unsafe extern "C" fn remove_process_region(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> CInt {
    process_remove_region_body_result(
        vm,
        start,
        end,
        Some(process_free_range_noirq_lock_bridge),
        Some(process_free_range_noirq_unlock_bridge),
        Some(process_remove_region_clear_bridge),
        Some(process_remove_region_log_bridge),
    )
}

#[inline(always)]
unsafe fn process_init_stack_zero(mut ptr: *mut u8, mut len: CULong) {
    while len != 0 {
        write_volatile(ptr, 0);
        ptr = ptr.add(1);
        len -= 1;
    }
}

#[inline(always)]
unsafe fn process_init_stack_push(base: *mut CULong, s_ind: &mut isize, value: CULong) {
    write_volatile(base.offset(*s_ind), value);
    *s_ind -= 1;
}

#[inline(always)]
fn process_init_stack_sp(end: CULong, s_ind: isize) -> CULong {
    end.wrapping_add((s_ind as i64 as CULong).wrapping_mul(size_of::<CULong>() as CULong))
}

#[inline(always)]
unsafe fn process_init_stack_log_args(args: &mut MaybeUninit<[CULong; 12]>) -> *mut CULong {
    let ptr = args.as_mut_ptr().cast::<CULong>();
    let mut index = 0usize;
    while index < 12 {
        write_volatile(ptr.add(index), 0);
        index += 1;
    }
    ptr
}

macro_rules! process_init_stack_log {
    ($log_fn:expr, $event:expr $(, $index:literal => $value:expr)* $(,)?) => {{
        if $log_fn.is_some() {
            let mut args = MaybeUninit::<[CULong; 12]>::uninit();
            let args_ptr = process_init_stack_log_args(&mut args);
            $(
                write_volatile(args_ptr.add($index), $value as CULong);
            )*
            let _ = process_init_stack_log_result($event, args_ptr as *const CULong, $log_fn);
        }
    }};
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_alloc_aligned_result(
    npages: CInt,
    p2align: CInt,
    flags: CULong,
    virt_addr: CULong,
    alloc_aligned_fn: Option<ProcessInitStackAllocAlignedFn>,
) -> *mut c_void {
    let Some(alloc_aligned) = alloc_aligned_fn else {
        return null_mut();
    };

    alloc_aligned(npages, p2align, flags, virt_addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_free_pages_result(
    addr: *mut c_void,
    npages: CInt,
    free_pages_fn: Option<ProcessInitStackFreePagesFn>,
) -> CInt {
    let Some(free_pages) = free_pages_fn else {
        return -EINVAL;
    };

    free_pages(addr, npages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_add_range_result(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut VmRange,
    add_range_fn: Option<ProcessInitStackAddRangeFn>,
) -> CInt {
    let Some(add_range) = add_range_fn else {
        return -EINVAL;
    };

    add_range(vm, start, end, phys, flag, pgshift, rangep)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_virt_to_phys_result(
    addr: *mut c_void,
    virt_to_phys_fn: Option<ProcessInitStackVirtToPhysFn>,
) -> CULong {
    let Some(virt_to_phys) = virt_to_phys_fn else {
        return 0;
    };

    virt_to_phys(addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_attr_from_vrflag_result(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
) -> CULong {
    let Some(attr) = attr_fn else {
        return 0;
    };

    attr(flag, fault, ptep)
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_pt_set_range_result(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut VmRange,
    flags: CInt,
    pt_set_range_fn: Option<ProcessInitStackPtSetRangeFn>,
) -> CInt {
    let Some(pt_set_range) = pt_set_range_fn else {
        return -EINVAL;
    };

    pt_set_range(
        page_table, vm, start, end, phys, attr, pgshift, range, flags,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_hwcap_result(
    hwcap_fn: Option<ProcessInitStackHwcapFn>,
) -> CULong {
    let Some(hwcap) = hwcap_fn else {
        return 0;
    };

    hwcap()
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_modify_context_result(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
) -> CInt {
    let Some(modify_context) = modify_context_fn else {
        return -EINVAL;
    };

    modify_context(uctx, reg, value);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_log_result(
    event: CInt,
    args: *const CULong,
    log_fn: Option<ProcessInitStackLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return -EINVAL;
    };
    if args.is_null() {
        return -EINVAL;
    }

    log(event, args);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_stack_body_result(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
    page_size: CULong,
    page_shift: CInt,
    user_stack_page_mask: CULong,
    user_stack_page_shift: CInt,
    user_stack_prepage_size: CULong,
    stack_alloc_size_override: CULong,
    user_stack_page_p2align: CInt,
    alloc_nowait: CULong,
    alloc_user: CULong,
    mpol_no_stack: CULong,
    user_context_sp_reg: CInt,
    pf_populate: CULong,
    alloc_aligned_fn: Option<ProcessInitStackAllocAlignedFn>,
    free_pages_fn: Option<ProcessInitStackFreePagesFn>,
    add_range_fn: Option<ProcessInitStackAddRangeFn>,
    virt_to_phys_fn: Option<ProcessInitStackVirtToPhysFn>,
    attr_fn: Option<ProcessAttrFromVrflagFn>,
    pt_set_range_fn: Option<ProcessInitStackPtSetRangeFn>,
    hwcap_fn: Option<ProcessInitStackHwcapFn>,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
    log_fn: Option<ProcessInitStackLogFn>,
) -> CInt {
    if thread.is_null()
        || pn.is_null()
        || page_size == 0
        || page_shift < 0
        || user_stack_page_shift < 0
    {
        return -EINVAL;
    }
    if alloc_aligned_fn.is_none()
        || free_pages_fn.is_none()
        || add_range_fn.is_none()
        || virt_to_phys_fn.is_none()
        || attr_fn.is_none()
        || pt_set_range_fn.is_none()
        || hwcap_fn.is_none()
        || modify_context_fn.is_none()
    {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    let vm = (*thread).vm;
    if proc.is_null() || vm.is_null() || (*vm).address_space.is_null() {
        return -EINVAL;
    }

    let end = (*vm).region.user_end & user_stack_page_mask;
    let mut minsz = ((*pn).stack_premap as CULong).wrapping_add(user_stack_prepage_size - 1)
        & user_stack_page_mask;
    let maxsz = end.wrapping_sub((*vm).region.map_start) / 2;
    let mut size = (*proc).rlimit[MCK_RLIMIT_STACK].rlim_cur;
    if size > maxsz {
        size = maxsz;
    } else if size < minsz {
        size = minsz;
    }
    size = size.wrapping_add(user_stack_prepage_size - 1) & user_stack_page_mask;
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_SIZE,
        0 => (*pn).stack_premap as CULong,
        1 => (*proc).rlimit[MCK_RLIMIT_STACK].rlim_cur,
        2 => minsz,
        3 => size,
        4 => maxsz,
    );
    let start = end.wrapping_sub(minsz) & user_stack_page_mask;

    let ap_flag =
        if minsz >= (*proc).mpol_threshold as CULong && ((*proc).mpol_flags & mpol_no_stack) == 0 {
            alloc_user
        } else {
            0
        };
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_AP_USER,
        0 => size,
        1 => minsz,
        2 => ap_flag,
    );
    if stack_alloc_size_override != 0 {
        minsz = stack_alloc_size_override;
    }

    let stack_npages = (minsz >> (page_shift as u32)) as CInt;
    let stack = process_init_stack_alloc_aligned_result(
        stack_npages,
        user_stack_page_p2align,
        alloc_nowait | ap_flag,
        start,
        alloc_aligned_fn,
    );
    if stack.is_null() {
        process_init_stack_log!(log_fn, PROCESS_INIT_STACK_LOG_ALLOC_FAILED);
        return -ENOMEM;
    }
    process_init_stack_zero(stack.cast::<u8>(), minsz);

    let mut vrflag = VR_STACK | VR_DEMAND_PAGING | VR_PRIVATE;
    if (ap_flag & alloc_user) != 0 {
        vrflag |= VR_AP_USER;
    }
    vrflag |= ((*pn).stack_prot as CULong) << 16 & VR_PROT_MASK;
    vrflag |= VR_MAXPROT_READ | VR_MAXPROT_WRITE | VR_MAXPROT_EXEC;

    let mut range: *mut VmRange = null_mut();
    let mut error = process_init_stack_add_range_result(
        vm,
        start,
        end,
        NOPHYS,
        vrflag,
        user_stack_page_shift,
        &mut range,
        add_range_fn,
    );
    if error != 0 {
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_ADD_FAILED,
            0 => error as CULong,
        );
        return error;
    }
    if range.is_null() {
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        return -EINVAL;
    }

    let stack_phys = process_init_stack_virt_to_phys_result(stack, virt_to_phys_fn);
    let stack_attr = process_attr_from_vrflag_result(vrflag, pf_populate, null_mut(), attr_fn);
    error = process_init_stack_pt_set_range_result(
        (*(*vm).address_space).page_table,
        vm,
        end.wrapping_sub(minsz),
        end,
        stack_phys,
        stack_attr,
        user_stack_page_shift,
        range,
        0,
        pt_set_range_fn,
    );
    if error != 0 {
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_PT_FAILED,
            0 => end.wrapping_sub(minsz),
            1 => end,
            2 => stack as CULong,
            3 => error as CULong,
        );
        let _ = process_init_stack_free_pages_result(stack, stack_npages, free_pages_fn);
        return error;
    }

    let stack_populated_size = (16usize
        + AUXV_LEN * size_of::<CULong>()
        + (argc.wrapping_add(2) as usize).wrapping_mul(size_of::<CULong>())
        + (envc.wrapping_add(1) as usize).wrapping_mul(size_of::<CULong>()))
        as CULong;
    let p = stack.cast::<u8>().add(minsz as usize).cast::<CULong>();
    let mut s_ind: isize = -1;
    let mut stack_align_padding = 0u64;
    while ((stack as CULong)
        .wrapping_add(minsz)
        .wrapping_sub(stack_populated_size)
        .wrapping_sub(stack_align_padding)
        & (0x40 - 1))
        != 0
    {
        s_ind -= 1;
        stack_align_padding = stack_align_padding.wrapping_add(size_of::<CULong>() as CULong);
    }

    process_init_stack_push(p, &mut s_ind, 0x010101011);
    process_init_stack_push(p, &mut s_ind, 0x010101011);
    let at_rand = end
        .wrapping_add(((s_ind + 1) as i64 as CULong).wrapping_mul(size_of::<CULong>() as CULong));

    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_NULL);
    process_init_stack_push(p, &mut s_ind, if argc > 0 { *argv as CULong } else { 0 });
    process_init_stack_push(p, &mut s_ind, if argc > 0 { AT_EXECFN } else { AT_IGNORE });
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_HWCAP2);
    let ap_hwcap = process_init_stack_hwcap_result(hwcap_fn);
    process_init_stack_push(p, &mut s_ind, ap_hwcap);
    process_init_stack_push(
        p,
        &mut s_ind,
        if ap_hwcap != 0 { AT_HWCAP } else { AT_IGNORE },
    );
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_SECURE);
    process_init_stack_push(p, &mut s_ind, (*proc).egid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_EGID);
    process_init_stack_push(p, &mut s_ind, (*proc).rgid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_GID);
    process_init_stack_push(p, &mut s_ind, (*proc).euid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_EUID);
    process_init_stack_push(p, &mut s_ind, (*proc).ruid as CULong);
    process_init_stack_push(p, &mut s_ind, AT_UID);
    process_init_stack_push(p, &mut s_ind, (*pn).at_entry);
    process_init_stack_push(p, &mut s_ind, AT_ENTRY);
    process_init_stack_push(p, &mut s_ind, 0);
    process_init_stack_push(p, &mut s_ind, AT_FLAGS);
    process_init_stack_push(p, &mut s_ind, at_base);
    process_init_stack_push(p, &mut s_ind, AT_BASE);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phnum);
    process_init_stack_push(p, &mut s_ind, AT_PHNUM);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phent);
    process_init_stack_push(p, &mut s_ind, AT_PHENT);
    process_init_stack_push(p, &mut s_ind, (*pn).at_phdr);
    process_init_stack_push(p, &mut s_ind, AT_PHDR);
    process_init_stack_push(p, &mut s_ind, page_size);
    process_init_stack_push(p, &mut s_ind, AT_PAGESZ);
    process_init_stack_push(p, &mut s_ind, (*pn).at_clktck);
    process_init_stack_push(p, &mut s_ind, AT_CLKTCK);
    process_init_stack_push(p, &mut s_ind, at_rand);
    process_init_stack_push(p, &mut s_ind, AT_RANDOM);
    process_init_stack_push(p, &mut s_ind, (*vm).vdso_addr as CULong);
    process_init_stack_push(
        p,
        &mut s_ind,
        if !(*vm).vdso_addr.is_null() {
            AT_SYSINFO_EHDR
        } else {
            AT_IGNORE
        },
    );
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_AUXV,
        0 => (*proc).pid as CULong,
        1 => (*thread).tid as CULong,
        2 => (*pn).at_entry,
        3 => at_base,
        4 => (*pn).at_phdr,
        5 => (*vm).vdso_addr as CULong,
        6 => page_size,
        7 => at_rand,
        8 => end,
        9 => argc as CULong,
        10 => envc as CULong,
    );

    let aux_start = p.offset(s_ind + 1);
    let mut aux_index = 0usize;
    while aux_index < AUXV_LEN {
        write_volatile(
            &raw mut (*proc).saved_auxv[aux_index],
            *aux_start.add(aux_index),
        );
        aux_index += 1;
    }

    process_init_stack_push(p, &mut s_ind, 0);
    let mut arg_ind = envc - 1;
    while arg_ind > -1 {
        process_init_stack_push(p, &mut s_ind, *env.add(arg_ind as usize) as CULong);
        arg_ind -= 1;
    }
    process_init_stack_push(p, &mut s_ind, 0);
    arg_ind = argc - 1;
    while arg_ind > -1 {
        process_init_stack_push(p, &mut s_ind, *argv.add(arg_ind as usize) as CULong);
        arg_ind -= 1;
    }
    write_volatile(p.offset(s_ind), argc as CULong);

    let actual_stack = p.offset(s_ind) as *mut c_void;
    let expected_stack = (stack as CULong)
        .wrapping_add(minsz)
        .wrapping_sub(stack_populated_size)
        .wrapping_sub(stack_align_padding);
    if actual_stack as CULong != expected_stack {
        process_init_stack_log!(
            log_fn,
            PROCESS_INIT_STACK_LOG_SIZE_MISMATCH,
            0 => actual_stack as CULong,
            1 => expected_stack,
        );
    }
    if (actual_stack as CULong & (0x40 - 1)) != 0 {
        process_init_stack_log!(log_fn, PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH);
    }

    let user_sp = process_init_stack_sp(end, s_ind);
    let argv_null_i = s_ind + argc as isize + 1;
    let env0_i = argv_null_i + 1;
    let env_null_i = env0_i + envc as isize;
    let aux0_i = env_null_i + 1;
    process_init_stack_log!(
        log_fn,
        PROCESS_INIT_STACK_LOG_INITIAL,
        0 => (*proc).pid as CULong,
        1 => (*thread).tid as CULong,
        2 => user_sp,
        3 => *p.offset(s_ind),
        4 => if argc > 0 { *p.offset(s_ind + 1) } else { 0 },
        5 => *p.offset(argv_null_i),
        6 => if envc > 0 { *p.offset(env0_i) } else { 0 },
        7 => *p.offset(env_null_i),
        8 => *p.offset(aux0_i),
        9 => *p.offset(aux0_i + 1),
    );
    let _ = process_init_stack_modify_context_result(
        (*thread).uctx.cast::<c_void>(),
        if user_context_sp_reg == 0 {
            IHK_UCR_STACK_POINTER
        } else {
            user_context_sp_reg
        },
        user_sp,
        modify_context_fn,
    );
    (*vm).region.stack_end = end;
    (*vm).region.stack_start = end.wrapping_sub(size) & user_stack_page_mask;
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
pub unsafe extern "C" fn process_ref_dec_and_test_result(
    object: *mut c_void,
    ref_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
) -> CInt {
    if let Some(dec) = dec_fn {
        return dec(object, ref_offset);
    }

    process_ref_dec_and_test_direct_result(object, ref_offset)
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_set_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if let Some(ref_set) = ref_set_fn {
        ref_set(object, ref_offset, value);
        return 0;
    }

    process_ref_set_direct_result(object, ref_offset, value)
}

unsafe fn process_ref_atomic_at(
    object: *mut c_void,
    ref_offset: CULong,
) -> Option<&'static AtomicI32> {
    if object.is_null() {
        return None;
    }

    let atomic = object
        .cast::<u8>()
        .wrapping_add(ref_offset as usize)
        .cast::<IhkAtomic>();
    Some(AtomicI32::from_ptr(&raw mut (*atomic).counter))
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_inc_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    let _ = atomic.fetch_add(1, Ordering::SeqCst);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_dec_and_test_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    (atomic.fetch_sub(1, Ordering::SeqCst) - 1 == 0) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_set_direct_result(
    object: *mut c_void,
    ref_offset: CULong,
    value: CInt,
) -> CInt {
    let Some(atomic) = process_ref_atomic_at(object, ref_offset) else {
        return -EINVAL;
    };

    atomic.store(value, Ordering::SeqCst);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_alloc_result(
    size: CULong,
    flags: CULong,
    alloc_fn: Option<ProcessAllocFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };

    alloc(size, flags)
}

#[no_mangle]
pub unsafe extern "C" fn process_free_callback_result(
    ptr: *mut c_void,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(ptr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_create_result(
    flags: CULong,
    pt_create_fn: Option<ProcessPtCreateFn>,
) -> *mut c_void {
    let Some(pt_create) = pt_create_fn else {
        return null_mut();
    };

    pt_create(flags)
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_create_bridge(flags: CULong) -> *mut c_void {
    ihk_mc_pt_create(flags)
}

#[no_mangle]
pub unsafe extern "C" fn process_pt_destroy_result(
    page_table: *mut c_void,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
) -> CInt {
    let Some(pt_destroy) = pt_destroy_fn else {
        return -EINVAL;
    };

    pt_destroy(page_table);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_procfs_delete_thread_bridge(thread: *mut c_void) {
    procfs_delete_thread(thread.cast::<Thread>());
}

#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_bridge(thread: *mut c_void) {
    destroy_thread(thread.cast::<Thread>());
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_bridge(vm: *mut c_void) {
    release_process_vm(vm.cast::<ProcessVm>());
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_checked_bridge(vm: *mut c_void) -> CInt {
    release_process_vm_checked(vm.cast::<ProcessVm>())
}

#[no_mangle]
pub unsafe extern "C" fn process_flush_vm_bridge(vm: *mut c_void) {
    flush_nfo_tlb_mm(vm.cast::<ProcessVm>());
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_bridge(
    address_space: *mut c_void,
    pid: CInt,
) {
    detach_address_space(address_space.cast::<AddressSpace>(), pid);
}

#[no_mangle]
pub unsafe extern "C" fn process_release_process_bridge(proc: *mut c_void) {
    release_process(proc.cast::<Process>());
}

#[no_mangle]
pub unsafe extern "C" fn process_release_sigcommon_bridge(sigcommon: *mut c_void) {
    release_sigcommon(sigcommon.cast::<SigCommon>());
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_save_fp_bridge(thread: *mut c_void) -> CInt {
    save_fp_regs(thread)
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_init_panic_bridge() {
    panic(PROCESS_SCHED_INIT_PANIC.as_ptr().cast());
}

#[no_mangle]
pub unsafe extern "C" fn process_mcs_lock_init_bridge(lock_addr: CULong) {
    crate::lock_helpers::mcs_lock_init(lock_addr as *mut crate::lock_helpers::McsLockNode);
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_lock_bridge(lock_addr: CULong) -> CULong {
    __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock)
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong) {
    __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_noirq_lock_bridge(lock_addr: CULong) {
    __ihk_mc_spinlock_lock_noirq(lock_addr as *mut IhkSpinlock);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_noirq_unlock_bridge(lock_addr: CULong) {
    __ihk_mc_spinlock_unlock_noirq(lock_addr as *mut IhkSpinlock);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_rwlock_bridge(lock_addr: CULong, node_addr: CULong) {
    __mcs_rwlock_writer_lock_noirq(lock_addr as *mut McsRwlockLock, node_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_rwunlock_bridge(lock_addr: CULong, node_addr: CULong) {
    __mcs_rwlock_writer_unlock_noirq(lock_addr as *mut McsRwlockLock, node_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_vector_bridge(vector_key: CInt) -> CInt {
    ihk_mc_get_vector(vector_key)
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_interrupt_bridge(cpu: CInt, vector: CInt) {
    ihk_mc_interrupt_cpu(cpu, vector);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_schedule_bridge() {
    schedule();
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_cpu_local_bridge(cpu_id: CInt) -> CULong {
    get_cpu_local_var(cpu_id) as CULong
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_waitq_wakeup_bridge(waitq_addr: CULong) {
    waitq_wakeup(waitq_addr as *mut Waitq);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_waitq_init_bridge(waitq_addr: CULong) {
    waitq_init(waitq_addr as *mut Waitq);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_waitq_prepare_bridge(
    waitq_addr: CULong,
    entry_addr: CULong,
    status: CInt,
) {
    waitq_prepare_to_wait(waitq_addr as *mut Waitq, entry_addr as *mut c_void, status);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_waitq_finish_bridge(waitq_addr: CULong, entry_addr: CULong) {
    waitq_finish_wait(waitq_addr as *mut Waitq, entry_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_status_set_bridge(status_addr: CULong, status: CInt) {
    xchg4(status_addr as *mut CInt, status);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_set_timer_bridge(runq_locked: CInt) {
    set_timer(runq_locked);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_irq_save_bridge() -> CULong {
    cpu_disable_interrupt_save()
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_irq_restore_bridge(irqstate: CULong) {
    cpu_restore_interrupt(irqstate);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_zero_free_bridge() {
    ihk_numa_zero_free_pages(ihk_mc_get_numa_node_by_distance(0));
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_pause_bridge() {
    cpu_pause();
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_has_signal_bridge(thread_addr: CULong) -> CInt {
    (!hassigpending(thread_addr as *mut Thread).is_null()) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_reset_cputime_bridge() {
    reset_cputime();
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_procfs_create_thread_bridge(thread_addr: CULong) {
    procfs_create_thread(thread_addr as *mut Thread);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_counter_inc_bridge(counter_addr: CULong) -> CInt {
    (*(counter_addr as *mut AtomicI32)).fetch_add(1, Ordering::SeqCst) + 1
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_counter_dec_bridge(counter_addr: CULong) {
    (*(counter_addr as *mut AtomicUsize)).fetch_sub(1, Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_rusage_threads_inc_bridge() {
    rusage_num_threads_inc();
}

#[no_mangle]
pub unsafe extern "C" fn process_rw_read_lock_bridge(lock_addr: CULong) {
    ihk_rwspinlock_read_lock_noirq(lock_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_rw_read_unlock_bridge(lock_addr: CULong) {
    ihk_rwspinlock_read_unlock_noirq(lock_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_rw_write_lock_bridge(lock_addr: CULong) {
    ihk_rwspinlock_write_lock_noirq(lock_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_rw_write_unlock_bridge(lock_addr: CULong) {
    ihk_rwspinlock_write_unlock_noirq(lock_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_init_bridge(lock_addr: CULong) {
    ihk_mc_spinlock_init(lock_addr as *mut IhkSpinlock);
}

#[no_mangle]
pub unsafe extern "C" fn process_rwlock_init_bridge(lock_addr: CULong) {
    mcs_rwlock_init(lock_addr as *mut McsRwlockLock);
}

#[no_mangle]
pub unsafe extern "C" fn process_waitq_init_bridge(waitq_addr: CULong) {
    waitq_init(waitq_addr as *mut Waitq);
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_rwspin_init_bridge(lock_addr: CULong) {
    ihk_rwspinlock_init(lock_addr as *mut c_void);
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_init_result(
    lock_addr: CULong,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> CInt {
    let Some(spin_init) = spin_init_fn else {
        return -EINVAL;
    };

    spin_init(lock_addr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_free_cb_result(
    asp: *mut c_void,
    opt: *mut c_void,
    free_cb: Option<ProcessAddressSpaceFreeCallback>,
) -> CInt {
    let Some(free_cb) = free_cb else {
        return 0;
    };

    free_cb(asp, opt);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_address_space_action_result(
    asp: *mut c_void,
    action_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(asp);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_address_space_body_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    free_cb_offset: CULong,
    opt_offset: CULong,
    page_table_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if asp.is_null() {
        return -EINVAL;
    }
    let Some(pt_destroy_fn) = pt_destroy_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    if process_release_address_space_should_destroy_result(process_ref_dec_and_test_result(
        asp,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let base = asp.cast::<u8>();
    let free_cb = *(base
        .wrapping_add(free_cb_offset as usize)
        .cast::<Option<ProcessAddressSpaceFreeCallback>>());
    if process_release_address_space_should_run_free_cb_result(
        free_cb.map_or(0, |f| f as usize as CULong),
    ) != 0
    {
        let opt = *(base.wrapping_add(opt_offset as usize).cast::<*mut c_void>());
        if let Some(free_cb) = free_cb {
            let _ = process_address_space_free_cb_result(asp, opt, Some(free_cb));
        }
    }

    let page_table = *(base
        .wrapping_add(page_table_offset as usize)
        .cast::<*mut c_void>());
    let _ = process_pt_destroy_result(page_table, Some(pt_destroy_fn));
    let _ = process_free_callback_result(asp, Some(free_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_address_space_public_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    process_ref_hold_body_result(asp, refcount_offset, inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_release_address_space_public_result(
    asp: *mut c_void,
    refcount_offset: CULong,
    free_cb_offset: CULong,
    opt_offset: CULong,
    page_table_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    pt_destroy_fn: Option<ProcessPtDestroyFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    process_release_address_space_body_result(
        asp,
        refcount_offset,
        free_cb_offset,
        opt_offset,
        page_table_offset,
        dec_fn,
        pt_destroy_fn,
        free_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_body_result(
    asp: *mut c_void,
    pid: CInt,
    pids_offset: CULong,
    nslots_offset: CULong,
    release_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    if asp.is_null() {
        return -EINVAL;
    }
    let Some(release_fn) = release_fn else {
        return -EINVAL;
    };

    let base = asp.cast::<u8>();
    let pids = base.wrapping_add(pids_offset as usize).cast::<CInt>();
    let nslots = *(base.wrapping_add(nslots_offset as usize).cast::<CInt>());
    let detached = process_address_space_pid_detach_result(pids, nslots, pid);
    let _ = process_address_space_action_result(asp, Some(release_fn));
    detached
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_public_result(
    asp: *mut c_void,
    pid: CInt,
    pids_offset: CULong,
    nslots_offset: CULong,
    release_fn: Option<ProcessAddressSpaceActionFn>,
) -> CInt {
    process_detach_address_space_body_result(asp, pid, pids_offset, nslots_offset, release_fn)
}

#[no_mangle]
pub unsafe extern "C" fn create_address_space(
    _res: *mut ResourceSet,
    n: CInt,
) -> *mut AddressSpace {
    process_create_address_space_body_result(
        n,
        size_of::<AddressSpace>() as CULong,
        size_of::<CInt>() as CULong,
        IHK_MC_AP_NOWAIT,
        offset_of!(AddressSpace, page_table) as CULong,
        offset_of!(AddressSpace, refcount) as CULong,
        offset_of!(AddressSpace, cpu_set) as CULong,
        size_of::<CpuSet>() as CULong,
        offset_of!(AddressSpace, cpu_set_lock) as CULong,
        offset_of!(AddressSpace, nslots) as CULong,
        Some(process_alloc_bridge),
        Some(process_optional_free_bridge),
        Some(process_pt_create_bridge),
        None,
        Some(process_spin_init_bridge),
    )
    .cast()
}

#[no_mangle]
pub unsafe extern "C" fn hold_address_space(asp: *mut AddressSpace) {
    let _ = process_hold_address_space_public_result(
        asp.cast(),
        offset_of!(AddressSpace, refcount) as CULong,
        None,
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_address_space(asp: *mut AddressSpace) {
    let _ = process_release_address_space_public_result(
        asp.cast(),
        offset_of!(AddressSpace, refcount) as CULong,
        offset_of!(AddressSpace, free_cb) as CULong,
        offset_of!(AddressSpace, opt) as CULong,
        offset_of!(AddressSpace, page_table) as CULong,
        None,
        Some(process_pt_destroy_bridge),
        Some(process_optional_free_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn detach_address_space(asp: *mut AddressSpace, pid: CInt) {
    let _ = process_detach_address_space_public_result(
        asp.cast(),
        pid,
        size_of::<AddressSpace>() as CULong,
        offset_of!(AddressSpace, nslots) as CULong,
        Some(process_release_address_space_action_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn process_create_address_space_body_result(
    nslots: CInt,
    address_space_size: CULong,
    pid_slot_size: CULong,
    nowait_flag: CULong,
    page_table_offset: CULong,
    refcount_offset: CULong,
    cpu_set_offset: CULong,
    cpu_set_size: CULong,
    cpu_set_lock_offset: CULong,
    nslots_offset: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    pt_create_fn: Option<ProcessPtCreateFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> *mut c_void {
    if nslots < 0 {
        return null_mut();
    }
    let Some(alloc_fn) = alloc_fn else {
        return null_mut();
    };
    let Some(free_fn) = free_fn else {
        return null_mut();
    };
    let Some(pt_create_fn) = pt_create_fn else {
        return null_mut();
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return null_mut();
    };

    let total_size = address_space_size.wrapping_add(pid_slot_size.wrapping_mul(nslots as CULong));
    let asp = process_alloc_result(total_size, nowait_flag, Some(alloc_fn));
    if asp.is_null() {
        return null_mut();
    }

    let pt = process_pt_create_result(nowait_flag, Some(pt_create_fn));
    if pt.is_null() {
        let _ = process_free_callback_result(asp, Some(free_fn));
        return null_mut();
    }

    let mut offset = 0;
    while offset < total_size {
        write_volatile(asp.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }

    let base = asp.cast::<u8>();
    *(base.wrapping_add(nslots_offset as usize).cast::<CInt>()) = nslots;
    *(base
        .wrapping_add(page_table_offset as usize)
        .cast::<*mut c_void>()) = pt;
    let _ = process_ref_set_result(asp, refcount_offset, 1, ref_set_fn);

    let mut cpu_offset = 0;
    while cpu_offset < cpu_set_size {
        write_volatile(
            base.wrapping_add(cpu_set_offset as usize)
                .add(cpu_offset as usize),
            0,
        );
        cpu_offset = cpu_offset.wrapping_add(1);
    }
    let _ = process_spin_init_result(
        base.wrapping_add(cpu_set_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    asp
}

#[no_mangle]
pub extern "C" fn process_create_cpu_allowed_result(cpu: CInt, num_processors: CInt) -> CInt {
    (cpu >= 0 && cpu < num_processors) as CInt
}

#[no_mangle]
pub extern "C" fn process_create_use_default_cpu_set_result(cpu_set_empty: CInt) -> CInt {
    (cpu_set_empty != 0) as CInt
}

unsafe fn process_cpu_input_bit_is_set(cpu_set_addr: CULong, cpu: CULong) -> bool {
    if cpu_set_addr == 0 {
        return false;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CULong;
    let word = (cpu_set_addr as *const CULong).add((cpu / word_bits) as usize);
    let mask = 1u64.wrapping_shl((cpu % word_bits) as u32);
    (*word & mask) != 0
}

unsafe fn process_cpu_set_direct(cpu_set_addr: CULong, cpu: CInt, cpu_set_bits: CInt) -> CInt {
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, cpu, cpu_set_bits) {
        *word |= mask;
        1
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_create_cpu_sets_body_result(
    requested_cpu_set_addr: CULong,
    requested_bits: CULong,
    thread_cpu_set_addr: CULong,
    proc_cpu_set_addr: CULong,
    output_cpu_set_bits: CInt,
    num_processors: CInt,
    pid: CInt,
    default_ncpus_fn: Option<ProcessDefaultNcpusFn>,
    log_fn: Option<ProcessCreateCpuLogFn>,
) -> CInt {
    if thread_cpu_set_addr == 0 || proc_cpu_set_addr == 0 || output_cpu_set_bits <= 0 {
        return -EINVAL;
    }
    if requested_bits != 0 && requested_cpu_set_addr == 0 {
        return -EINVAL;
    }

    let mut selected = 0;
    let mut cpu = 0;
    while cpu < requested_bits {
        if process_cpu_input_bit_is_set(requested_cpu_set_addr, cpu) {
            let cpu_i = cpu as CInt;
            if process_create_cpu_allowed_result(cpu_i, num_processors) == 0 {
                if let Some(log) = log_fn {
                    log(PROCESS_CREATE_CPU_LOG_INVALID, pid, cpu_i);
                }
                return -EINVAL;
            }
            if let Some(log) = log_fn {
                log(PROCESS_CREATE_CPU_LOG_REQUESTED, pid, cpu_i);
            }
            selected += process_cpu_set_direct(thread_cpu_set_addr, cpu_i, output_cpu_set_bits);
            selected += process_cpu_set_direct(proc_cpu_set_addr, cpu_i, output_cpu_set_bits);
        }
        cpu = cpu.wrapping_add(1);
    }

    if process_create_use_default_cpu_set_result((selected == 0) as CInt) != 0 {
        let Some(default_ncpus) = default_ncpus_fn else {
            return -EINVAL;
        };
        let ncpus = default_ncpus();
        if ncpus < 0 {
            return -EINVAL;
        }

        let mut default_cpu = 0;
        while default_cpu < ncpus {
            selected +=
                process_cpu_set_direct(thread_cpu_set_addr, default_cpu, output_cpu_set_bits);
            selected += process_cpu_set_direct(proc_cpu_set_addr, default_cpu, output_cpu_set_bits);
            default_cpu += 1;
        }
    }

    selected / 2
}

unsafe fn process_list_head_init(head: *mut AbiListHead) {
    if head.is_null() {
        return;
    }

    (*head).next = head;
    (*head).prev = head;
}

#[no_mangle]
pub unsafe extern "C" fn process_allocated_object_zero_body_result(
    object: *mut c_void,
    object_size: CULong,
) -> CInt {
    if object.is_null() {
        return -EINVAL;
    }

    let mut offset = 0;
    while offset < object_size {
        write_volatile(object.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_init_body_result(
    vm: *mut ProcessVm,
    owner: *mut c_void,
    asp: *mut c_void,
    nr_numa_nodes: CInt,
    memory_lock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    numa_log_fn: Option<ProcessVmInitNumaLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(memory_lock_init_fn) = memory_lock_init_fn else {
        return -EINVAL;
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };

    memory_lock_init_fn((&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong);
    let _ = process_spin_init_result(
        (&raw mut (*vm).page_table_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    (*vm).refcount.counter = 1;
    (*vm).vm_range_tree.rb_node = null_mut();
    (*vm).vm_range_numa_policy_tree.rb_node = null_mut();
    (*vm).address_space = asp.cast();
    (*vm).proc = owner;
    (*vm).exiting = 0;

    let mask_base = (&raw mut (*vm).numa_mask).cast::<CULong>();
    let mut word = 0usize;
    while word < (*vm).numa_mask.len() {
        write_volatile(mask_base.add(word), 0);
        word += 1;
    }

    let bits_per_word = size_of::<CULong>() * 8;
    let mut node = 0;
    while node < nr_numa_nodes {
        if node as usize >= PROCESS_NUMA_MASK_BITS {
            if let Some(log_fn) = numa_log_fn {
                log_fn(node);
            }
            break;
        }
        let bit = node as usize;
        let wordp = mask_base.add(bit / bits_per_word);
        let current = core::ptr::read_volatile(wordp);
        write_volatile(wordp, current | (1u64 << (bit % bits_per_word)));
        node += 1;
    }
    (*vm).numa_mem_policy = MPOL_DEFAULT;

    let cache_base = (&raw mut (*vm).range_cache).cast::<*mut VmRange>();
    let mut cache_index = 0usize;
    while cache_index < VM_RANGE_CACHE_SIZE {
        write_volatile(cache_base.add(cache_index), null_mut());
        cache_index += 1;
    }
    (*vm).range_cache_ind = 0;

    #[cfg(enable_tofu)]
    {
        let _ = process_spin_init_result(
            (&raw mut (*vm).tofu_stag_lock).cast::<c_void>() as CULong,
            Some(spin_init_fn),
        );
        let mut tofu_index = 0usize;
        while tofu_index < crate::abi::TOFU_STAG_HASH_SIZE {
            process_list_head_init(&raw mut (*vm).tofu_stag_hash[tofu_index]);
            tofu_index += 1;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn init_process_vm(
    owner: *mut Process,
    asp: *mut AddressSpace,
    vm: *mut ProcessVm,
) -> CInt {
    process_vm_init_body_result(
        vm,
        owner.cast(),
        asp.cast(),
        ihk_mc_get_nr_numa_nodes(),
        Some(process_vm_rwspin_init_bridge),
        Some(process_spin_init_bridge),
        Some(process_vm_init_numa_log_bridge),
    )
}

unsafe fn process_new_resource_cleanup(
    res: *mut ResourceSet,
    phash: *mut ProcessHash,
    thash: *mut ThreadHash,
    pid1: *mut Process,
    free_fn: ProcessFreeFn,
) -> *mut c_void {
    if !res.is_null() {
        free_fn(res.cast());
    }
    if !phash.is_null() {
        free_fn(phash.cast());
    }
    if !thash.is_null() {
        free_fn(thash.cast());
    }
    if !pid1.is_null() {
        free_fn(pid1.cast());
    }
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_new_resource_set_body_result(
    resource_set_size: CULong,
    process_hash_size: CULong,
    thread_hash_size: CULong,
    process_size: CULong,
    nowait_flag: CULong,
    hash_size: CInt,
    init_pid: CInt,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    init_process_fn: Option<ProcessInitProcessFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> *mut c_void {
    let (Some(alloc_fn), Some(free_fn), Some(init_process_fn), Some(rwlock_init_fn)) =
        (alloc_fn, free_fn, init_process_fn, rwlock_init_fn)
    else {
        return null_mut();
    };
    if hash_size <= 0 || hash_size as usize > PROCESS_HASH_SIZE {
        return null_mut();
    }

    let res = alloc_fn(resource_set_size, nowait_flag).cast::<ResourceSet>();
    let phash = alloc_fn(process_hash_size, nowait_flag).cast::<ProcessHash>();
    let thash = alloc_fn(thread_hash_size, nowait_flag).cast::<ThreadHash>();
    let pid1 = alloc_fn(process_size, nowait_flag).cast::<Process>();
    if res.is_null() || phash.is_null() || thash.is_null() || pid1.is_null() {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }

    if process_allocated_object_zero_body_result(res.cast(), resource_set_size) < 0
        || process_allocated_object_zero_body_result(phash.cast(), process_hash_size) < 0
        || process_allocated_object_zero_body_result(thash.cast(), thread_hash_size) < 0
        || process_allocated_object_zero_body_result(pid1.cast(), process_size) < 0
    {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }

    process_list_head_init(&raw mut (*res).phys_mem_list);
    rwlock_init_fn((&raw mut (*res).phys_mem_lock).cast::<c_void>() as CULong);
    rwlock_init_fn((&raw mut (*res).cpu_set_lock).cast::<c_void>() as CULong);

    let mut i = 0usize;
    while i < hash_size as usize {
        process_list_head_init(&raw mut (*phash).list[i]);
        rwlock_init_fn((&raw mut (*phash).lock[i]).cast::<c_void>() as CULong);
        i += 1;
    }
    (*res).process_hash = phash;

    i = 0;
    while i < hash_size as usize {
        process_list_head_init(&raw mut (*thash).list[i]);
        rwlock_init_fn((&raw mut (*thash).lock[i]).cast::<c_void>() as CULong);
        i += 1;
    }
    (*res).thread_hash = thash;

    if init_process_fn(pid1.cast(), pid1.cast()) != 0 {
        return process_new_resource_cleanup(res, phash, thash, pid1, free_fn);
    }
    (*pid1).pid = init_pid;
    let hash = (init_pid as usize) % (hash_size as usize);
    process_list_add_tail_result(&raw mut (*pid1).hash_list, &raw mut (*phash).list[hash]);
    (*res).pid1 = pid1;

    res.cast()
}

#[no_mangle]
pub unsafe extern "C" fn new_resource_set() -> *mut ResourceSet {
    process_new_resource_set_body_result(
        size_of::<ResourceSet>() as CULong,
        size_of::<ProcessHash>() as CULong,
        size_of::<ThreadHash>() as CULong,
        size_of::<Process>() as CULong,
        IHK_MC_AP_NOWAIT,
        HASH_SIZE,
        1,
        Some(process_alloc_bridge),
        Some(process_optional_free_bridge),
        Some(process_init_process_public_bridge),
        Some(process_rwlock_init_bridge),
    )
    .cast()
}

#[no_mangle]
pub unsafe extern "C" fn process_memset_smp_handler_body_result(
    cpu_index: CInt,
    nr_cpus: CInt,
    phys: CULong,
    len: SizeT,
    value: CInt,
    phys_to_virt_fn: Option<ProcessPhysToVirtFn>,
    memset_fn: Option<ProcessMemsetFn>,
    log_fn: Option<ProcessMemsetSmpLogFn>,
) -> CInt {
    let (Some(phys_to_virt), Some(memset_cb)) = (phys_to_virt_fn, memset_fn) else {
        return -EINVAL;
    };
    if cpu_index < 0 || nr_cpus <= 0 {
        return -EINVAL;
    }

    let chunk = len / nr_cpus as SizeT;
    if chunk == 0 {
        if cpu_index == 0 {
            memset_cb(phys_to_virt(phys), value, len);
        }
        return 0;
    }

    let chunk_phys = chunk as CULong;
    let start = phys.wrapping_add((cpu_index as CULong).wrapping_mul(chunk_phys));
    let mut end = start.wrapping_add(chunk_phys);
    if cpu_index == nr_cpus - 1 {
        end = phys.wrapping_add(len as CULong);
    }

    memset_cb(phys_to_virt(start), value, end.wrapping_sub(start) as SizeT);
    if let Some(log) = log_fn {
        log(1, cpu_index, nr_cpus, phys, len, start, end);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_memset_smp_body_result(
    cpu_set: *mut c_void,
    addr: *mut c_void,
    value: CInt,
    len: SizeT,
    phys_slot: *mut CULong,
    len_slot: *mut SizeT,
    value_slot: *mut CInt,
    handler: *mut c_void,
    request: *mut c_void,
    virt_to_phys_fn: Option<ProcessVirtToPhysFn>,
    smp_call_fn: Option<ProcessSmpCallFn>,
) -> CInt {
    let (Some(virt_to_phys), Some(smp_call)) = (virt_to_phys_fn, smp_call_fn) else {
        return -EINVAL;
    };
    if phys_slot.is_null()
        || len_slot.is_null()
        || value_slot.is_null()
        || handler.is_null()
        || request.is_null()
    {
        return -EINVAL;
    }

    write_volatile(phys_slot, virt_to_phys(addr));
    write_volatile(len_slot, len);
    write_volatile(value_slot, value);
    smp_call(cpu_set, handler, request)
}

#[no_mangle]
pub unsafe extern "C" fn memset_smp_handler(
    cpu_index: CInt,
    nr_cpus: CInt,
    arg: *mut c_void,
) -> CInt {
    if arg.is_null() {
        return -EINVAL;
    }
    let req = arg.cast::<ProcessMemsetSmpReq>();
    process_memset_smp_handler_body_result(
        cpu_index,
        nr_cpus,
        (*req).phys,
        (*req).len,
        (*req).val,
        Some(process_memset_smp_phys_to_virt_bridge),
        Some(process_memset_smp_memset_bridge),
        Some(process_memset_smp_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn memset_smp(
    cpu_set: *mut CpuSet,
    s: *mut c_void,
    c: CInt,
    n: SizeT,
) -> *mut c_void {
    let mut req = MaybeUninit::<ProcessMemsetSmpReq>::uninit();
    let reqp = req.as_mut_ptr();
    let _ = process_memset_smp_body_result(
        cpu_set.cast(),
        s,
        c,
        n,
        &raw mut (*reqp).phys,
        &raw mut (*reqp).len,
        &raw mut (*reqp).val,
        memset_smp_handler as *const () as *mut c_void,
        reqp.cast(),
        Some(process_memset_smp_virt_to_phys_bridge),
        Some(process_memset_smp_call_bridge),
    );
    s
}

#[no_mangle]
pub unsafe extern "C" fn process_proc_init_body_result(
    resource_set: *mut c_void,
    resource_set_list: *mut AbiListHead,
    resource_set_lock_addr: CULong,
    num_processors: CInt,
    cpu_set_bits: CInt,
    path_size: CULong,
    nowait_flag: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> CInt {
    let (Some(alloc_fn), Some(rwlock_init_fn)) = (alloc_fn, rwlock_init_fn) else {
        return -EINVAL;
    };
    if resource_set.is_null() || resource_set_list.is_null() || path_size == 0 {
        return -EINVAL;
    }

    let res = resource_set.cast::<ResourceSet>();
    process_list_head_init(resource_set_list);
    rwlock_init_fn(resource_set_lock_addr);

    let cpu_set_addr = (&raw mut (*res).cpu_set).cast::<c_void>() as CULong;
    let mut cpu = 0;
    while cpu < num_processors {
        let _ = process_cpu_set_direct(cpu_set_addr, cpu, cpu_set_bits);
        cpu += 1;
    }

    let path = alloc_fn(path_size, nowait_flag).cast::<u8>();
    if path.is_null() {
        return -ENOMEM;
    }
    write_volatile(path, b'/');
    write_volatile(path, 0);
    (*res).path = path.cast::<i8>();
    process_list_add_tail_result(&raw mut (*res).list, resource_set_list);

    0
}

#[no_mangle]
pub unsafe extern "C" fn proc_init() {
    let res = new_resource_set();
    if res.is_null()
        || process_proc_init_body_result(
            res.cast(),
            &raw mut PROCESS_RESOURCE_SET_LIST,
            (&raw mut PROCESS_RESOURCE_SET_LOCK).cast::<c_void>() as CULong,
            PROCESS_NUM_PROCESSORS,
            CPU_SETSIZE,
            2,
            IHK_MC_AP_NOWAIT,
            Some(process_alloc_bridge),
            Some(process_rwlock_init_bridge),
        ) < 0
    {
        process_proc_init_panic_bridge();
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_sched_init_body_result(
    cpu_local_addr: CULong,
    resource_set_list: *mut AbiListHead,
    current_cpu: CInt,
    init_process_fn: Option<ProcessInitProcessFn>,
    memory_lock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    init_context_fn: Option<ProcessSchedInitContextFn>,
    save_fp_fn: Option<ProcessSchedSaveFpFn>,
    timer_init_fn: Option<ProcessSchedTimerInitFn>,
) -> CInt {
    let (
        Some(init_process_fn),
        Some(memory_lock_init_fn),
        Some(spin_init_fn),
        Some(init_context_fn),
        Some(save_fp_fn),
        Some(timer_init_fn),
    ) = (
        init_process_fn,
        memory_lock_init_fn,
        spin_init_fn,
        init_context_fn,
        save_fp_fn,
        timer_init_fn,
    )
    else {
        return -EINVAL;
    };
    if cpu_local_addr == 0 || resource_set_list.is_null() {
        return -EINVAL;
    }

    let cpu_local = cpu_local_addr as *mut CpuLocalVar;
    let first = (*resource_set_list).next;
    if first.is_null() || first == resource_set_list {
        return -ENOMEM;
    }
    let res = first.cast::<ResourceSet>();
    (*cpu_local).resource_set = res;

    let idle_thread = &raw mut (*cpu_local).idle;
    let idle_proc = &raw mut (*cpu_local).idle_proc;
    let idle_vm = &raw mut (*cpu_local).idle_vm;
    let idle_asp = &raw mut (*cpu_local).idle_asp;

    if process_allocated_object_zero_body_result(idle_thread.cast(), size_of::<Thread>() as CULong)
        < 0
        || process_allocated_object_zero_body_result(
            idle_vm.cast(),
            size_of::<ProcessVm>() as CULong,
        ) < 0
        || process_allocated_object_zero_body_result(
            idle_proc.cast(),
            size_of::<Process>() as CULong,
        ) < 0
    {
        return -EINVAL;
    }

    (*idle_thread).vm = idle_vm;
    (*idle_vm).address_space = idle_asp;
    (*idle_thread).proc = idle_proc;
    if init_process_fn(idle_proc.cast(), null_mut()) != 0 {
        return -EINVAL;
    }
    (*idle_proc).nohost = 1;
    (*idle_proc).vm = idle_vm;
    process_list_add_tail_result(
        &raw mut (*idle_thread).siblings_list,
        &raw mut (*idle_proc).children_list,
    );

    init_context_fn(idle_thread.cast());
    memory_lock_init_fn((&raw mut (*idle_vm).memory_range_lock).cast::<c_void>() as CULong);
    (*idle_vm).vm_range_tree.rb_node = null_mut();
    (*idle_vm).vm_range_numa_policy_tree.rb_node = null_mut();
    (*idle_proc).pid = 0;
    (*idle_thread).tid = current_cpu;

    process_list_head_init(&raw mut (*cpu_local).runq);
    (*cpu_local).runq_len = 0;
    process_spin_init_result(
        (&raw mut (*cpu_local).runq_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    process_list_head_init(&raw mut (*cpu_local).migq);
    process_spin_init_result(
        (&raw mut (*cpu_local).migq_lock).cast::<c_void>() as CULong,
        Some(spin_init_fn),
    );

    let _ = save_fp_fn(idle_thread.cast());
    timer_init_fn(current_cpu);
    0
}

#[no_mangle]
pub unsafe extern "C" fn sched_init() {
    if process_sched_init_body_result(
        get_this_cpu_local_var() as CULong,
        &raw mut PROCESS_RESOURCE_SET_LIST,
        ihk_mc_get_processor_id(),
        Some(process_init_process_public_bridge),
        Some(process_vm_rwspin_init_bridge),
        Some(process_spin_init_bridge),
        Some(process_sched_init_context_bridge),
        Some(process_sched_save_fp_bridge),
        Some(process_sched_timer_init_bridge),
    ) < 0
    {
        process_sched_init_panic_bridge();
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_init_state_body_result(
    process: *mut c_void,
    parent: *const c_void,
    offsets: *const ProcessInitStateOffsets,
    initial_pid: CInt,
    running_status: CInt,
) -> CInt {
    if process.is_null() || offsets.is_null() {
        return -EINVAL;
    }

    let proc = process.cast::<u8>();
    let offsets = &*offsets;
    *proc.add(offsets.pid_offset as usize).cast::<CInt>() = initial_pid;
    *proc.add(offsets.status_offset as usize).cast::<CInt>() = running_status;

    if parent.is_null() {
        return 0;
    }

    let pproc = parent.cast::<u8>();
    *proc
        .add(offsets.parent_offset as usize)
        .cast::<*const c_void>() = parent;
    *proc
        .add(offsets.ppid_parent_offset as usize)
        .cast::<*const c_void>() = parent;
    *proc.add(offsets.pgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.pgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.ruid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.ruid_offset as usize).cast::<CInt>();
    *proc.add(offsets.euid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.euid_offset as usize).cast::<CInt>();
    *proc.add(offsets.suid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.suid_offset as usize).cast::<CInt>();
    *proc.add(offsets.fsuid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.fsuid_offset as usize).cast::<CInt>();
    *proc.add(offsets.rgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.rgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.egid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.egid_offset as usize).cast::<CInt>();
    *proc.add(offsets.sgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.sgid_offset as usize).cast::<CInt>();
    *proc.add(offsets.fsgid_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.fsgid_offset as usize).cast::<CInt>();
    *proc
        .add(offsets.mpol_flags_offset as usize)
        .cast::<CULong>() = *pproc
        .add(offsets.mpol_flags_offset as usize)
        .cast::<CULong>();
    *proc
        .add(offsets.mpol_threshold_offset as usize)
        .cast::<CULong>() = *pproc
        .add(offsets.mpol_threshold_offset as usize)
        .cast::<CULong>();
    *proc.add(offsets.thp_disable_offset as usize).cast::<CInt>() = *pproc
        .add(offsets.thp_disable_offset as usize)
        .cast::<CInt>();
    copy_nonoverlapping(
        pproc.add(offsets.rlimit_offset as usize),
        proc.add(offsets.rlimit_offset as usize),
        offsets.rlimit_size as usize,
    );
    copy_nonoverlapping(
        pproc.add(offsets.cpu_set_offset as usize),
        proc.add(offsets.cpu_set_offset as usize),
        offsets.cpu_set_size as usize,
    );
    *proc.add(offsets.enable_uti_offset as usize).cast::<CInt>() =
        *pproc.add(offsets.enable_uti_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_links_body_result(
    process: *mut c_void,
    hash_list_offset: CULong,
    siblings_list_offset: CULong,
    ptraced_siblings_list_offset: CULong,
    update_lock_offset: CULong,
    report_threads_list_offset: CULong,
    threads_list_offset: CULong,
    children_list_offset: CULong,
    ptraced_children_list_offset: CULong,
    threads_lock_offset: CULong,
    children_lock_offset: CULong,
    coredump_lock_offset: CULong,
    mckfd_lock_offset: CULong,
    waitpid_q_offset: CULong,
    refcount_offset: CULong,
    monitoring_event_offset: CULong,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    waitq_init_fn: Option<ProcessWaitqInitFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };
    let Some(waitq_init_fn) = waitq_init_fn else {
        return -EINVAL;
    };
    let proc = process.cast::<u8>();
    process_list_head_init(proc.add(hash_list_offset as usize).cast::<AbiListHead>());
    process_list_head_init(
        proc.add(siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        proc.add(ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    rwlock_init_fn(proc.add(update_lock_offset as usize) as CULong);
    process_list_head_init(
        proc.add(report_threads_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(proc.add(threads_list_offset as usize).cast::<AbiListHead>());
    process_list_head_init(
        proc.add(children_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        proc.add(ptraced_children_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    rwlock_init_fn(proc.add(threads_lock_offset as usize) as CULong);
    rwlock_init_fn(proc.add(children_lock_offset as usize) as CULong);
    rwlock_init_fn(proc.add(coredump_lock_offset as usize) as CULong);
    let _ = process_spin_init_result(
        proc.add(mckfd_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    waitq_init_fn(proc.add(waitpid_q_offset as usize) as CULong);
    if process_ref_set_result(process, refcount_offset, 2, ref_set_fn) != 0 {
        return -EINVAL;
    }
    write_volatile(
        proc.add(monitoring_event_offset as usize)
            .cast::<*mut c_void>(),
        null_mut(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_init_profile_body_result(
    process: *mut c_void,
    profile_lock_offset: CULong,
    profile_events_offset: CULong,
    lock_init_fn: Option<ProcessMcsLockInitFn>,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }
    let Some(lock_init_fn) = lock_init_fn else {
        return -EINVAL;
    };

    let proc = process.cast::<u8>();
    lock_init_fn(proc.add(profile_lock_offset as usize) as CULong);
    write_volatile(
        proc.add(profile_events_offset as usize)
            .cast::<*mut c_void>(),
        null_mut(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn init_process(proc: *mut Process, parent: *mut Process) {
    let state_offsets = ProcessInitStateOffsets {
        pid_offset: offset_of!(Process, pid) as CULong,
        status_offset: offset_of!(Process, status) as CULong,
        parent_offset: offset_of!(Process, parent) as CULong,
        ppid_parent_offset: offset_of!(Process, ppid_parent) as CULong,
        pgid_offset: offset_of!(Process, pgid) as CULong,
        ruid_offset: offset_of!(Process, ruid) as CULong,
        euid_offset: offset_of!(Process, euid) as CULong,
        suid_offset: offset_of!(Process, suid) as CULong,
        fsuid_offset: offset_of!(Process, fsuid) as CULong,
        rgid_offset: offset_of!(Process, rgid) as CULong,
        egid_offset: offset_of!(Process, egid) as CULong,
        sgid_offset: offset_of!(Process, sgid) as CULong,
        fsgid_offset: offset_of!(Process, fsgid) as CULong,
        mpol_flags_offset: offset_of!(Process, mpol_flags) as CULong,
        mpol_threshold_offset: offset_of!(Process, mpol_threshold) as CULong,
        thp_disable_offset: offset_of!(Process, thp_disable) as CULong,
        rlimit_offset: offset_of!(Process, rlimit) as CULong,
        rlimit_size: size_of::<[RLimit; MCK_RLIM_MAX]>() as CULong,
        cpu_set_offset: offset_of!(Process, cpu_set) as CULong,
        cpu_set_size: size_of::<CpuSet>() as CULong,
        enable_uti_offset: offset_of!(Process, enable_uti) as CULong,
    };

    if process_init_state_body_result(
        proc.cast(),
        parent.cast(),
        &raw const state_offsets,
        -1,
        PROCESS_STATUS_RUNNING,
    ) < 0
    {
        process_panic_bridge(b"failed to initialize process state\0".as_ptr().cast());
    }

    if process_init_links_body_result(
        proc.cast(),
        offset_of!(Process, hash_list) as CULong,
        offset_of!(Process, siblings_list) as CULong,
        offset_of!(Process, ptraced_siblings_list) as CULong,
        offset_of!(Process, update_lock) as CULong,
        offset_of!(Process, report_threads_list) as CULong,
        offset_of!(Process, threads_list) as CULong,
        offset_of!(Process, children_list) as CULong,
        offset_of!(Process, ptraced_children_list) as CULong,
        offset_of!(Process, threads_lock) as CULong,
        offset_of!(Process, children_lock) as CULong,
        offset_of!(Process, coredump_lock) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Process, waitpid_q) as CULong,
        offset_of!(Process, refcount) as CULong,
        offset_of!(Process, monitoring_event) as CULong,
        Some(process_rwlock_init_bridge),
        Some(process_spin_init_bridge),
        Some(process_waitq_init_bridge),
        None,
    ) < 0
    {
        process_panic_bridge(b"failed to initialize process links\0".as_ptr().cast());
    }

    #[cfg(enable_profile)]
    {
        if process_init_profile_body_result(
            proc.cast(),
            offset_of!(Process, profile_lock) as CULong,
            offset_of!(Process, profile_events) as CULong,
            Some(process_mcs_lock_init_bridge),
        ) < 0
        {
            process_panic_bridge(
                b"failed to initialize process profile state\0"
                    .as_ptr()
                    .cast(),
            );
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_base_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    cpu_set_offset: CULong,
    cpu_set_size: CULong,
    in_kernel_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    let dst = thread.cast::<u8>();
    let src = origin.cast::<u8>();
    if cpu_set_size != 0 && crate::sched_helpers::sched_clone_affinity_inherit_result(
        dst.add(cpu_set_offset as usize) as usize,
        src.add(cpu_set_offset as usize) as usize,
        cpu_set_size as usize,
    ) < 0 {
        return -EINVAL;
    }
    *dst.add(in_kernel_offset as usize).cast::<CInt>() =
        *src.add(in_kernel_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_sched_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sched_policy_offset: CULong,
    sched_priority_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    let dst = thread.cast::<u8>();
    let src = origin.cast::<u8>();
    *dst.add(sched_policy_offset as usize).cast::<CInt>() =
        *src.add(sched_policy_offset as usize).cast::<CInt>();
    *dst.add(sched_priority_offset as usize).cast::<CInt>() =
        *src.add(sched_priority_offset as usize).cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sched_default_body_result(
    thread: *mut c_void,
    sched_policy_offset: CULong,
    default_policy: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(sched_policy_offset as usize)
        .cast::<CInt>() = default_policy;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_create_thread_link_state_body_result(
    thread: *mut c_void,
    process: *mut c_void,
    vm: *mut c_void,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
    process_vm_offset: CULong,
    process_main_thread_offset: CULong,
) -> CInt {
    if thread.is_null() || process.is_null() || vm.is_null() {
        return -EINVAL;
    }

    let thread_base = thread.cast::<u8>();
    let process_base = process.cast::<u8>();
    *thread_base
        .add(thread_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *thread_base
        .add(thread_proc_offset as usize)
        .cast::<*mut c_void>() = process;
    *process_base
        .add(process_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *process_base
        .add(process_main_thread_offset as usize)
        .cast::<*mut c_void>() = thread;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_exit_status_init_body_result(
    thread: *mut c_void,
    exit_status_offset: CULong,
    exit_status: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(exit_status_offset as usize)
        .cast::<CInt>() = exit_status;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_spin_sleep_init_body_result(
    thread: *mut c_void,
    spin_sleep_lock_offset: CULong,
    spin_sleep_offset: CULong,
    spin_init_fn: Option<ProcessSpinInitFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(spin_init_fn) = spin_init_fn else {
        return -EINVAL;
    };

    let thread_base = thread.cast::<u8>();
    let _ = process_spin_init_result(
        thread_base.add(spin_sleep_lock_offset as usize) as CULong,
        Some(spin_init_fn),
    );
    *thread_base.add(spin_sleep_offset as usize).cast::<CInt>() = 0;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigmask_copy_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sigmask_offset: CULong,
    sigmask_size: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(
        origin.cast::<u8>().add(sigmask_offset as usize),
        thread.cast::<u8>().add(sigmask_offset as usize),
        sigmask_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_profile_state_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    process: *const c_void,
    thread_profile_offset: CULong,
    process_profile_offset: CULong,
) -> CInt {
    if thread.is_null() || origin.is_null() || process.is_null() {
        return -EINVAL;
    }

    *thread
        .cast::<u8>()
        .add(thread_profile_offset as usize)
        .cast::<CInt>() = *origin
        .cast::<u8>()
        .add(thread_profile_offset as usize)
        .cast::<CInt>()
        | *process
            .cast::<u8>()
            .add(process_profile_offset as usize)
            .cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_process_termsig_body_result(
    process: *mut c_void,
    termsig_offset: CULong,
    termsig: CInt,
) -> CInt {
    if process.is_null() {
        return -EINVAL;
    }

    *process
        .cast::<u8>()
        .add(termsig_offset as usize)
        .cast::<CInt>() = termsig;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_saved_cmdline_body_result(
    process: *mut c_void,
    origin_process: *const c_void,
    saved_cmdline_len_offset: CULong,
    saved_cmdline_offset: CULong,
    nowait_flag: CULong,
    alloc_fn: Option<ProcessAllocFn>,
) -> CInt {
    if process.is_null() || origin_process.is_null() {
        return -EINVAL;
    }
    let Some(alloc_fn) = alloc_fn else {
        return -EINVAL;
    };

    let dst = process.cast::<u8>();
    let src = origin_process.cast::<u8>();
    let len = *src.add(saved_cmdline_len_offset as usize).cast::<CLong>();
    *dst.add(saved_cmdline_len_offset as usize).cast::<CLong>() = len;
    let cmdline = alloc_fn(len as CULong, nowait_flag);
    if cmdline.is_null() {
        return -ENOMEM;
    }
    if len != 0 {
        let src_cmdline = *src.add(saved_cmdline_offset as usize).cast::<*const u8>();
        copy_nonoverlapping(src_cmdline, cmdline.cast::<u8>(), len as usize);
    }
    *dst.add(saved_cmdline_offset as usize).cast::<*mut c_void>() = cmdline;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_vm_policy_body_result(
    dst_vm: *mut c_void,
    src_vm: *const c_void,
    numa_mask_offset: CULong,
    numa_mask_size: CULong,
    numa_mem_policy_offset: CULong,
    region_offset: CULong,
    region_size: CULong,
) -> CInt {
    if dst_vm.is_null() || src_vm.is_null() {
        return -EINVAL;
    }

    let dst = dst_vm.cast::<u8>();
    let src = src_vm.cast::<u8>();
    copy_nonoverlapping(
        src.add(numa_mask_offset as usize),
        dst.add(numa_mask_offset as usize),
        numa_mask_size as usize,
    );
    *dst.add(numa_mem_policy_offset as usize).cast::<CInt>() =
        *src.add(numa_mem_policy_offset as usize).cast::<CInt>();
    copy_nonoverlapping(
        src.add(region_offset as usize),
        dst.add(region_offset as usize),
        region_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_shared_vm_state_body_result(
    thread: *mut c_void,
    process: *mut c_void,
    vm: *mut c_void,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
) -> CInt {
    if thread.is_null() || process.is_null() || vm.is_null() {
        return -EINVAL;
    }

    let thread_base = thread.cast::<u8>();
    *thread_base
        .add(thread_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    *thread_base
        .add(thread_proc_offset as usize)
        .cast::<*mut c_void>() = process;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_sigcommon_share_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    sigcommon_offset: CULong,
    sigcommon_use_offset: CULong,
    ref_inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }
    let sigcommon = *origin
        .cast::<u8>()
        .add(sigcommon_offset as usize)
        .cast::<*mut c_void>();
    if sigcommon.is_null() {
        return -EINVAL;
    }
    *thread
        .cast::<u8>()
        .add(sigcommon_offset as usize)
        .cast::<*mut c_void>() = sigcommon;
    process_ref_inc_result(sigcommon, sigcommon_use_offset, ref_inc_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_sigcommon_action_copy_body_result(
    dst_sigcommon: *mut c_void,
    src_sigcommon: *const c_void,
    action_offset: CULong,
    action_size: CULong,
) -> CInt {
    if dst_sigcommon.is_null() || src_sigcommon.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(
        src_sigcommon.cast::<u8>().add(action_offset as usize),
        dst_sigcommon.cast::<u8>().add(action_offset as usize),
        action_size as usize,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_user_context_body_result(
    thread: *mut c_void,
    origin: *const c_void,
    uctx_offset: CULong,
    uctx_size: CULong,
    stack_pointer_reg: CInt,
    sp: CULong,
    program_counter_reg: CInt,
    pc: CULong,
    modify_context_fn: Option<ProcessInitStackModifyContextFn>,
) -> CInt {
    if thread.is_null() || origin.is_null() {
        return -EINVAL;
    }
    let Some(modify_context_fn) = modify_context_fn else {
        return -EINVAL;
    };

    let dst_uctx = *thread
        .cast::<u8>()
        .add(uctx_offset as usize)
        .cast::<*mut u8>();
    let src_uctx = *origin
        .cast::<u8>()
        .add(uctx_offset as usize)
        .cast::<*const u8>();
    if dst_uctx.is_null() || src_uctx.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(src_uctx, dst_uctx, uctx_size as usize);
    modify_context_fn(dst_uctx.cast::<c_void>(), stack_pointer_reg, sp);
    modify_context_fn(dst_uctx.cast::<c_void>(), program_counter_reg, pc);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_fork_profile_body_result(
    process: *mut c_void,
    origin_process: *const c_void,
    profile_offset: CULong,
) -> CInt {
    if process.is_null() || origin_process.is_null() {
        return -EINVAL;
    }

    *process
        .cast::<u8>()
        .add(profile_offset as usize)
        .cast::<CInt>() = *origin_process
        .cast::<u8>()
        .add(profile_offset as usize)
        .cast::<CInt>();
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_clone_on_fork_vm_body_result(
    cpu_local: *mut c_void,
    on_fork_vm_offset: CULong,
    vm: *mut c_void,
) -> CInt {
    if cpu_local.is_null() {
        return -EINVAL;
    }

    *cpu_local
        .cast::<u8>()
        .add(on_fork_vm_offset as usize)
        .cast::<*mut c_void>() = vm;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_copy_body_result(
    dst: *mut c_void,
    src: *const c_void,
    mckfd_size: CULong,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), mckfd_size as usize);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_range_metadata_body_result(
    dst: *mut VmRange,
    src: *const VmRange,
    memobj_ref_fn: Option<ProcessRangeMemobjRefFn>,
) -> CInt {
    if dst.is_null() || src.is_null() {
        return -EINVAL;
    }

    (*dst).vm_rb_node.__rb_parent_color = core::ptr::addr_of_mut!((*dst).vm_rb_node) as CULong;
    (*dst).start = (*src).start;
    (*dst).end = (*src).end;
    (*dst).flag = (*src).flag;
    (*dst).memobj = (*src).memobj;
    (*dst).objoff = (*src).objoff;
    (*dst).pgshift = (*src).pgshift;
    (*dst).private_data = (*src).private_data;
    (*dst).straight_start = (*src).straight_start;

    process_range_memobj_ref_or_direct_result((*dst).memobj, memobj_ref_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_pte_args_init_body_result(
    args: *mut c_void,
    new_vm_offset: CULong,
    new_vrflag_offset: CULong,
    range_offset: CULong,
    fault_addr_offset: CULong,
    vm: *mut c_void,
    vrflag: CULong,
    range: *mut c_void,
    fault_addr: CLong,
) -> CInt {
    if args.is_null() || vm.is_null() || range.is_null() {
        return -EINVAL;
    }

    let base = args.cast::<u8>();
    *base.add(new_vm_offset as usize).cast::<*mut c_void>() = vm;
    *base.add(new_vrflag_offset as usize).cast::<CULong>() = vrflag;
    *base.add(range_offset as usize).cast::<*mut c_void>() = range;
    *base.add(fault_addr_offset as usize).cast::<CLong>() = fault_addr;
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_pte_buffer_body_result(
    dst: *mut c_void,
    src: *const c_void,
    len: SizeT,
    wipe: CInt,
) -> CInt {
    if dst.is_null() || (wipe == 0 && src.is_null()) {
        return -EINVAL;
    }

    if wipe != 0 {
        core::ptr::write_bytes(dst.cast::<u8>(), 0, len);
    } else {
        copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), len);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_copy_user_ranges_body_result(
    vm: *mut ProcessVm,
    orgvm: *mut ProcessVm,
    range_size: CULong,
    _alloc_flags: CULong,
    copy_args: *mut c_void,
    new_vm_offset: CULong,
    new_vrflag_offset: CULong,
    range_offset: CULong,
    fault_addr_offset: CULong,
    copy_pte_fn: *mut c_void,
    visit_flags: CInt,
    read_lock_fn: Option<ProcessNoirqLockFn>,
    read_unlock_fn: Option<ProcessNoirqUnlockFn>,
    lookup_fn: Option<ProcessCopyRangeLookupFn>,
    next_fn: Option<ProcessCopyRangeNextFn>,
    alloc_fn: Option<ProcessAddRangeAllocFn>,
    free_fn: Option<ProcessAddRangeFreeFn>,
    insert_fn: Option<ProcessAddRangeInsertFn>,
    visit_fn: Option<ProcessVisitPteRangeFn>,
    free_range_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessCopyUserRangesLogFn>,
) -> CInt {
    if vm.is_null()
        || orgvm.is_null()
        || copy_args.is_null()
        || copy_pte_fn.is_null()
        || (*orgvm).address_space.is_null()
    {
        return -EINVAL;
    }

    let Some(read_lock) = read_lock_fn else {
        return -EINVAL;
    };
    let Some(read_unlock) = read_unlock_fn else {
        return -EINVAL;
    };
    let Some(lookup) = lookup_fn else {
        return -EINVAL;
    };
    let Some(next) = next_fn else {
        return -EINVAL;
    };
    let Some(alloc) = alloc_fn else {
        return -EINVAL;
    };
    let Some(free) = free_fn else {
        return -EINVAL;
    };
    let Some(insert) = insert_fn else {
        return -EINVAL;
    };
    let Some(visit) = visit_fn else {
        return -EINVAL;
    };
    let Some(free_range) = free_range_fn else {
        return -EINVAL;
    };

    let lock_addr = (&raw mut (*orgvm).memory_range_lock).cast::<c_void>() as CULong;
    let lock_rc = process_noirq_lock_result(lock_addr, Some(read_lock));
    if lock_rc != 0 {
        return lock_rc;
    }

    let mut error: CInt = 0;
    let mut src_range: *mut VmRange = null_mut();
    let mut last_insert: *mut VmRange = null_mut();

    loop {
        src_range = if src_range.is_null() {
            lookup(orgvm, 0, NOPHYS)
        } else {
            next(orgvm, src_range)
        };
        if src_range.is_null() {
            break;
        }

        if ((*src_range).flag & VR_DONTFORK) != 0 {
            continue;
        }

        let range = alloc(range_size);
        if range.is_null() {
            error = -1;
            break;
        }

        if process_copy_user_range_metadata_body_result(range, src_range, None) < 0 {
            free(range);
            error = -1;
            break;
        }

        let _ = insert(vm.cast::<c_void>(), range);
        last_insert = src_range;

        if process_copy_user_pte_args_init_body_result(
            copy_args,
            new_vm_offset,
            new_vrflag_offset,
            range_offset,
            fault_addr_offset,
            vm.cast::<c_void>(),
            (*range).flag,
            range.cast::<c_void>(),
            -1,
        ) < 0
        {
            error = -1;
            break;
        }

        error = visit(
            (*(*orgvm).address_space).page_table,
            (*range).start,
            (*range).end,
            (*range).pgshift,
            visit_flags,
            copy_pte_fn,
            copy_args,
        );
        if error != 0 {
            let fault_addr = *copy_args
                .cast::<u8>()
                .add(fault_addr_offset as usize)
                .cast::<CLong>();
            if fault_addr != -1 {
                if let Some(log) = log_fn {
                    log(orgvm, range, fault_addr);
                }
            }
            error = -1;
            break;
        }
    }

    if error != 0 && !last_insert.is_null() {
        src_range = lookup(orgvm, 0, NOPHYS);
        while !src_range.is_null() {
            if ((*src_range).flag & VR_DONTFORK) == 0 {
                let dest_range = lookup(vm, (*src_range).start, (*src_range).end);
                if !dest_range.is_null() {
                    let _ = process_memory_range_free_result(
                        vm.cast::<c_void>(),
                        dest_range.cast::<c_void>(),
                        Some(free_range),
                    );
                }
                if src_range == last_insert {
                    break;
                }
            }
            src_range = next(orgvm, src_range);
        }
    }

    let _ = process_noirq_unlock_result(lock_addr, Some(read_unlock));
    if error == 0 {
        0
    } else {
        -1
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_sigcommon_alloc_init_body_result(
    sigcommon_size: CULong,
    flags: CULong,
    use_offset: CULong,
    lock_offset: CULong,
    sigpending_offset: CULong,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    ref_set_fn: Option<ProcessRefSetFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> *mut c_void {
    let Some(alloc) = alloc_fn else {
        return null_mut();
    };
    let Some(free_fn) = free_fn else {
        return null_mut();
    };
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return null_mut();
    };

    let sigcommon = process_alloc_result(sigcommon_size, flags, Some(alloc));
    if sigcommon.is_null() {
        return null_mut();
    }

    let mut offset = 0;
    while offset < sigcommon_size {
        write_volatile(sigcommon.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }

    if process_ref_set_result(sigcommon, use_offset, 1, ref_set_fn) != 0 {
        let _ = process_free_callback_result(sigcommon, Some(free_fn));
        return null_mut();
    }
    rwlock_init_fn(sigcommon.cast::<u8>().add(lock_offset as usize) as CULong);
    process_list_head_init(
        sigcommon
            .cast::<u8>()
            .add(sigpending_offset as usize)
            .cast::<AbiListHead>(),
    );
    sigcommon
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigpending_init_body_result(
    thread: *mut c_void,
    lock_offset: CULong,
    sigpending_offset: CULong,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(rwlock_init_fn) = rwlock_init_fn else {
        return -EINVAL;
    };

    rwlock_init_fn(thread.cast::<u8>().add(lock_offset as usize) as CULong);
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(sigpending_offset as usize)
            .cast::<AbiListHead>(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_alloc_init_body_result(
    thread: *mut c_void,
    thread_size: CULong,
    refcount_offset: CULong,
    hash_list_offset: CULong,
    siblings_list_offset: CULong,
    ref_set_fn: Option<ProcessRefSetFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let mut offset = 0;
    while offset < thread_size {
        write_volatile(thread.cast::<u8>().add(offset as usize), 0);
        offset = offset.wrapping_add(1);
    }
    if process_ref_set_result(thread, refcount_offset, 2, ref_set_fn) != 0 {
        return -EINVAL;
    }
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(hash_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    process_list_head_init(
        thread
            .cast::<u8>()
            .add(siblings_list_offset as usize)
            .cast::<AbiListHead>(),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_sigstack_disable_body_result(
    thread: *mut c_void,
    sigstack_offset: CULong,
    sp_offset: CULong,
    flags_offset: CULong,
    size_offset: CULong,
    disable_flag: CInt,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    let sigstack = thread.cast::<u8>().add(sigstack_offset as usize);
    write_volatile(
        sigstack.add(sp_offset as usize).cast::<*mut c_void>(),
        null_mut(),
    );
    write_volatile(
        sigstack.add(flags_offset as usize).cast::<CInt>(),
        disable_flag,
    );
    write_volatile(sigstack.add(size_offset as usize).cast::<SizeT>(), 0);
    0
}

unsafe fn process_create_thread_cleanup(
    thread: *mut c_void,
    proc: *mut c_void,
    vm: *mut c_void,
    asp: *mut c_void,
    thread_sigcommon_offset: CULong,
    free_fn: ProcessFreeFn,
    release_address_space_fn: ProcessReleaseAddressSpaceFn,
    free_thread_fn: ProcessThreadActionFn,
) -> *mut c_void {
    if !proc.is_null() {
        let _ = process_free_callback_result(proc, Some(free_fn));
    }
    if !vm.is_null() {
        let _ = process_free_callback_result(vm, Some(free_fn));
    }
    if !asp.is_null() {
        release_address_space_fn(asp);
    }
    if !thread.is_null() {
        let sigcommon = *(thread
            .cast::<u8>()
            .add(thread_sigcommon_offset as usize)
            .cast::<*mut c_void>());
        if !sigcommon.is_null() {
            let _ = process_free_callback_result(sigcommon, Some(free_fn));
        }
        let _ = process_thread_action_result(thread, Some(free_thread_fn));
    }
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_create_thread_body_result(
    user_pc: CULong,
    requested_cpu_set_addr: CULong,
    requested_bits: CULong,
    thread_pages: CULong,
    thread_size: CULong,
    process_size: CULong,
    vm_size: CULong,
    nowait_flag: CULong,
    kernel_stack_bytes: CULong,
    cpu_set_bits: CInt,
    num_processors: CInt,
    sched_normal: CInt,
    ss_disable: CInt,
    current_cpu: CInt,
    parent_process: *mut c_void,
    process_pid_offset: CULong,
    thread_refcount_offset: CULong,
    thread_hash_list_offset: CULong,
    thread_siblings_list_offset: CULong,
    thread_cpu_set_offset: CULong,
    thread_sched_policy_offset: CULong,
    thread_sigcommon_offset: CULong,
    thread_sigpendinglock_offset: CULong,
    thread_sigpending_offset: CULong,
    thread_sigstack_offset: CULong,
    sigstack_sp_offset: CULong,
    sigstack_flags_offset: CULong,
    sigstack_size_offset: CULong,
    thread_vm_offset: CULong,
    thread_proc_offset: CULong,
    process_cpu_set_offset: CULong,
    process_vm_offset: CULong,
    process_main_thread_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_cpu_set_offset: CULong,
    address_space_cpu_set_lock_offset: CULong,
    thread_exit_status_offset: CULong,
    thread_spin_sleep_lock_offset: CULong,
    thread_spin_sleep_offset: CULong,
    sigcommon_size: CULong,
    sigcommon_use_offset: CULong,
    sigcommon_lock_offset: CULong,
    sigcommon_sigpending_offset: CULong,
    alloc_pages_fn: Option<ProcessAllocPagesFn>,
    alloc_fn: Option<ProcessAllocFn>,
    free_fn: Option<ProcessFreeFn>,
    create_address_space_fn: Option<ProcessCreateAddressSpaceFn>,
    release_address_space_fn: Option<ProcessReleaseAddressSpaceFn>,
    init_process_fn: Option<ProcessInitProcessFn>,
    init_process_vm_fn: Option<ProcessInitProcessVmFn>,
    init_user_process_fn: Option<ProcessInitUserProcessFn>,
    default_ncpus_fn: Option<ProcessDefaultNcpusFn>,
    cpu_log_fn: Option<ProcessCreateCpuLogFn>,
    rwlock_init_fn: Option<ProcessRwlockInitFn>,
    spin_init_fn: Option<ProcessSpinInitFn>,
    spin_lock_fn: Option<ProcessSpinLockFn>,
    spin_unlock_fn: Option<ProcessSpinUnlockFn>,
    free_thread_fn: Option<ProcessThreadActionFn>,
) -> *mut c_void {
    let (
        Some(alloc_pages_fn),
        Some(alloc_fn),
        Some(free_fn),
        Some(create_address_space_fn),
        Some(release_address_space_fn),
        Some(init_process_fn),
        Some(init_process_vm_fn),
        Some(init_user_process_fn),
        Some(rwlock_init_fn),
        Some(spin_init_fn),
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
        Some(free_thread_fn),
    ) = (
        alloc_pages_fn,
        alloc_fn,
        free_fn,
        create_address_space_fn,
        release_address_space_fn,
        init_process_fn,
        init_process_vm_fn,
        init_user_process_fn,
        rwlock_init_fn,
        spin_init_fn,
        spin_lock_fn,
        spin_unlock_fn,
        free_thread_fn,
    )
    else {
        return null_mut();
    };

    let thread = alloc_pages_fn(thread_pages as CInt, nowait_flag);
    if thread.is_null() {
        return null_mut();
    }
    if process_thread_alloc_init_body_result(
        thread,
        thread_size,
        thread_refcount_offset,
        thread_hash_list_offset,
        thread_siblings_list_offset,
        None,
    ) < 0
    {
        let _ = process_thread_action_result(thread, Some(free_thread_fn));
        return null_mut();
    }

    let proc = process_alloc_result(process_size, nowait_flag, Some(alloc_fn));
    let vm = process_alloc_result(vm_size, nowait_flag, Some(alloc_fn));
    let asp = create_address_space_fn(1);
    if proc.is_null() || vm.is_null() || asp.is_null() {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_allocated_object_zero_body_result(proc, process_size) < 0
        || process_allocated_object_zero_body_result(vm, vm_size) < 0
        || init_process_fn(proc, parent_process) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();
    let pid = *proc_base.add(process_pid_offset as usize).cast::<CInt>();
    if process_create_cpu_sets_body_result(
        requested_cpu_set_addr,
        requested_bits,
        thread_base.add(thread_cpu_set_offset as usize) as CULong,
        proc_base.add(process_cpu_set_offset as usize) as CULong,
        cpu_set_bits,
        num_processors,
        pid,
        default_ncpus_fn,
        cpu_log_fn,
    ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_thread_sched_default_body_result(thread, thread_sched_policy_offset, sched_normal)
        < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let sigcommon = process_sigcommon_alloc_init_body_result(
        sigcommon_size,
        nowait_flag,
        sigcommon_use_offset,
        sigcommon_lock_offset,
        sigcommon_sigpending_offset,
        Some(alloc_fn),
        Some(free_fn),
        None,
        Some(rwlock_init_fn),
    );
    *thread_base
        .add(thread_sigcommon_offset as usize)
        .cast::<*mut c_void>() = sigcommon;
    if sigcommon.is_null() {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    if process_thread_sigpending_init_body_result(
        thread,
        thread_sigpendinglock_offset,
        thread_sigpending_offset,
        Some(rwlock_init_fn),
    ) < 0
        || process_thread_sigstack_disable_body_result(
            thread,
            thread_sigstack_offset,
            sigstack_sp_offset,
            sigstack_flags_offset,
            sigstack_size_offset,
            ss_disable,
        ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    init_user_process_fn(
        thread,
        (thread as CULong).wrapping_add(kernel_stack_bytes),
        user_pc,
        0,
    );

    if process_create_thread_link_state_body_result(
        thread,
        proc,
        vm,
        thread_vm_offset,
        thread_proc_offset,
        process_vm_offset,
        process_main_thread_offset,
    ) < 0
        || init_process_vm_fn(proc, asp, vm) != 0
        || process_thread_exit_status_init_body_result(thread, thread_exit_status_offset, -1) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let asp_base = asp.cast::<u8>();
    let _ = process_cpu_set_update_body_result(
        asp_base.add(address_space_cpu_set_offset as usize) as CULong,
        asp_base.add(address_space_cpu_set_lock_offset as usize) as CULong,
        -1,
        current_cpu,
        num_processors,
        Some(spin_lock_fn),
        Some(spin_unlock_fn),
    );

    if process_thread_spin_sleep_init_body_result(
        thread,
        thread_spin_sleep_lock_offset,
        thread_spin_sleep_offset,
        Some(spin_init_fn),
    ) < 0
    {
        return process_create_thread_cleanup(
            thread,
            proc,
            vm,
            asp,
            thread_sigcommon_offset,
            free_fn,
            release_address_space_fn,
            free_thread_fn,
        );
    }

    let _ = vm_address_space_offset;
    thread
}

#[no_mangle]
pub unsafe extern "C" fn create_thread(
    user_pc: CULong,
    requested_cpu_set: *mut CULong,
    cpu_set_size: SizeT,
) -> *mut Thread {
    let cpu_local = get_this_cpu_local_var();
    let resource_set = (*cpu_local).resource_set;
    let parent_process = (*resource_set).pid1;

    process_create_thread_body_result(
        user_pc,
        requested_cpu_set as CULong,
        (cpu_set_size as CULong).wrapping_mul(BITS_PER_BYTE),
        KERNEL_STACK_NR_PAGES,
        size_of::<Thread>() as CULong,
        size_of::<Process>() as CULong,
        size_of::<ProcessVm>() as CULong,
        IHK_MC_AP_NOWAIT,
        KERNEL_STACK_NR_PAGES * PAGE_SIZE,
        CPU_SETSIZE,
        PROCESS_NUM_PROCESSORS,
        SCHED_NORMAL,
        SS_DISABLE,
        ihk_mc_get_processor_id(),
        parent_process.cast(),
        offset_of!(Process, pid) as CULong,
        offset_of!(Thread, refcount) as CULong,
        offset_of!(Thread, hash_list) as CULong,
        offset_of!(Thread, siblings_list) as CULong,
        offset_of!(Thread, cpu_set) as CULong,
        offset_of!(Thread, sched_policy) as CULong,
        offset_of!(Thread, sigcommon) as CULong,
        offset_of!(Thread, sigpendinglock) as CULong,
        offset_of!(Thread, sigpending) as CULong,
        offset_of!(Thread, sigstack) as CULong,
        offset_of!(SigStack, ss_sp) as CULong,
        offset_of!(SigStack, ss_flags) as CULong,
        offset_of!(SigStack, ss_size) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, proc) as CULong,
        offset_of!(Process, cpu_set) as CULong,
        offset_of!(Process, vm) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(AddressSpace, cpu_set) as CULong,
        offset_of!(AddressSpace, cpu_set_lock) as CULong,
        offset_of!(Thread, exit_status) as CULong,
        offset_of!(Thread, spin_sleep_lock) as CULong,
        offset_of!(Thread, spin_sleep) as CULong,
        size_of::<SigCommon>() as CULong,
        offset_of!(SigCommon, use_) as CULong,
        offset_of!(SigCommon, lock) as CULong,
        offset_of!(SigCommon, sigpending) as CULong,
        Some(process_create_thread_alloc_pages_bridge),
        Some(process_alloc_bridge),
        Some(process_optional_free_bridge),
        Some(process_create_thread_address_space_bridge),
        Some(process_create_thread_release_address_space_bridge),
        Some(process_create_thread_init_process_bridge),
        Some(process_create_thread_init_vm_bridge),
        Some(process_create_thread_init_user_bridge),
        Some(process_default_ncpus_bridge),
        Some(process_create_cpu_log_bridge),
        Some(process_rwlock_init_bridge),
        Some(process_spin_init_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_free_thread_pages_bridge),
    )
    .cast()
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
pub unsafe extern "C" fn process_mckfd_dup_result(
    fdp: *mut c_void,
    dup_fn: Option<ProcessMckfdDupFn>,
) -> CInt {
    let Some(dup) = dup_fn else {
        return 0;
    };

    dup(fdp, null_mut())
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
pub unsafe extern "C" fn process_sigpending_drain_free_result(
    head: *mut AbiListHead,
    list_offset: CULong,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if head.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    loop {
        let pending = process_sigpending_pop_front_result(head, list_offset);
        if pending.is_null() {
            break;
        }
        let _ = process_free_callback_result(pending, Some(free_fn));
        freed += 1;
    }

    freed
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
pub unsafe extern "C" fn process_ptrace_traceme_body_result(
    thread: *mut c_void,
    proc: *mut c_void,
    parent: *mut c_void,
    pid1: *mut c_void,
    offsets: *const ProcessPtraceTracemeOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    alloc_debugreg_fn: Option<ProcessAllocDebugregFn>,
    clear_single_step_fn: Option<ProcessThreadActionFn>,
    hold_thread_fn: Option<ProcessThreadActionFn>,
    log_fn: Option<ProcessPtraceTracemeLogFn>,
) -> CInt {
    if thread.is_null() || proc.is_null() || parent.is_null() || pid1.is_null() || offsets.is_null()
    {
        return -EFAULT;
    }

    let offsets = unsafe { &*offsets };
    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();
    let parent_base = parent.cast::<u8>();
    let pid = unsafe {
        *(proc_base
            .wrapping_add(offsets.proc_pid_offset as usize)
            .cast::<CInt>())
    };
    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_ENTER, pid, parent as CULong, 0) };
    }

    let ptrace_slot = thread_base
        .wrapping_add(offsets.thread_ptrace_offset as usize)
        .cast::<CInt>();
    if (unsafe { *ptrace_slot } & PT_TRACED) != 0 {
        return -EPERM;
    }
    if parent == pid1 {
        return -EPERM;
    }

    let parent_pid = unsafe {
        *(parent_base
            .wrapping_add(offsets.proc_pid_offset as usize)
            .cast::<CInt>())
    };
    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid, 0, 0) };
    }

    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    if lock_node.is_null() {
        return -EFAULT;
    }

    let main_thread = unsafe {
        *(proc_base
            .wrapping_add(offsets.proc_main_thread_offset as usize)
            .cast::<*mut c_void>())
    };
    if thread == main_thread {
        let children_lock =
            (parent as CULong).wrapping_add(offsets.proc_children_lock_offset as CULong);
        let ptraced_sibling = proc_base
            .wrapping_add(offsets.proc_ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let ptraced_children = parent_base
            .wrapping_add(offsets.proc_ptraced_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(children_lock, lock_node) };
        unsafe { process_list_add_tail_result(ptraced_sibling, ptraced_children) };
        unsafe { unlock(children_lock, lock_node) };
    }

    let report_proc = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_report_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    if report_proc.is_null() {
        let threads_lock = (parent as CULong).wrapping_add(offsets.proc_threads_lock_offset);
        let report_sibling = thread_base
            .wrapping_add(offsets.thread_report_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let report_threads = parent_base
            .wrapping_add(offsets.proc_report_threads_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(threads_lock, lock_node) };
        unsafe {
            process_thread_report_attach_result(
                thread,
                0,
                0,
                0,
                offsets.thread_report_proc_offset,
                parent,
                report_sibling,
                report_threads,
            );
        }
        unsafe { unlock(threads_lock, lock_node) };
    }

    unsafe { *ptrace_slot = PT_TRACED | PT_TRACE_EXEC };

    let debugreg = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_ptrace_debugreg_offset as usize)
            .cast::<*mut c_void>())
    };
    let mut error = 0;
    if debugreg.is_null() {
        let Some(alloc_debugreg) = alloc_debugreg_fn else {
            return -EFAULT;
        };
        error = unsafe { alloc_debugreg(thread) };
    }

    let Some(clear_single_step) = clear_single_step_fn else {
        return -EFAULT;
    };
    let Some(hold_thread) = hold_thread_fn else {
        return -EFAULT;
    };
    unsafe { clear_single_step(thread) };
    unsafe { hold_thread(thread) };

    if let Some(log) = log_fn {
        unsafe { log(PROCESS_PTRACE_TRACEME_LOG_RETURN, pid, 0, error) };
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn ptrace_traceme() -> CInt {
    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).current.is_null() || (*cpu).resource_set.is_null() {
        return -EFAULT;
    }

    let thread = (*cpu).current;
    let proc = (*thread).proc;
    let parent = if proc.is_null() {
        null_mut()
    } else {
        (*proc).parent
    };
    let pid1 = (*(*cpu).resource_set).pid1;
    let offsets = ProcessPtraceTracemeOffsets {
        thread_proc_offset: offset_of!(Thread, proc) as CULong,
        thread_report_proc_offset: offset_of!(Thread, report_proc) as CULong,
        thread_report_siblings_list_offset: offset_of!(Thread, report_siblings_list) as CULong,
        thread_ptrace_offset: offset_of!(Thread, ptrace) as CULong,
        thread_ptrace_debugreg_offset: offset_of!(Thread, ptrace_debugreg) as CULong,
        proc_pid_offset: offset_of!(Process, pid) as CULong,
        proc_parent_offset: offset_of!(Process, parent) as CULong,
        proc_main_thread_offset: offset_of!(Process, main_thread) as CULong,
        proc_children_lock_offset: offset_of!(Process, children_lock) as CULong,
        proc_threads_lock_offset: offset_of!(Process, threads_lock) as CULong,
        proc_ptraced_siblings_list_offset: offset_of!(Process, ptraced_siblings_list) as CULong,
        proc_ptraced_children_list_offset: offset_of!(Process, ptraced_children_list) as CULong,
        proc_report_threads_list_offset: offset_of!(Process, report_threads_list) as CULong,
    };
    let mut child_lock = MaybeUninit::<McsRwlockNode>::uninit();

    process_ptrace_traceme_body_result(
        thread.cast(),
        proc.cast(),
        parent.cast(),
        pid1.cast(),
        &offsets,
        child_lock.as_mut_ptr().cast(),
        Some(process_ptrace_mcs_lock_noirq_bridge),
        Some(process_ptrace_mcs_unlock_noirq_bridge),
        Some(process_ptrace_alloc_debugreg_bridge),
        Some(process_ptrace_clear_single_step_bridge),
        Some(process_ptrace_hold_thread_bridge),
        Some(process_ptrace_traceme_log_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_ptrace_attach_thread_body_result(
    thread: *mut c_void,
    proc: *mut c_void,
    offsets: *const ProcessPtraceAttachOffsets,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    alloc_debugreg_fn: Option<ProcessAllocDebugregFn>,
    clear_single_step_fn: Option<ProcessThreadActionFn>,
    hold_thread_fn: Option<ProcessThreadActionFn>,
    log_fn: Option<ProcessPtraceTracemeLogFn>,
) -> CInt {
    if thread.is_null() || proc.is_null() || offsets.is_null() || lock_node.is_null() {
        return -EFAULT;
    }
    let Some(lock) = lock_fn else {
        return -EFAULT;
    };
    let Some(unlock) = unlock_fn else {
        return -EFAULT;
    };
    let offsets = unsafe { &*offsets };
    let thread_base = thread.cast::<u8>();
    let proc_base = proc.cast::<u8>();

    let old_report_proc = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_report_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    let report_sibling = thread_base
        .wrapping_add(offsets.thread_report_siblings_list_offset as usize)
        .cast::<AbiListHead>();
    if !old_report_proc.is_null() {
        let old_threads_lock =
            (old_report_proc as CULong).wrapping_add(offsets.proc_threads_lock_offset);
        unsafe { lock(old_threads_lock, lock_node) };
        unsafe { process_list_detach_result(report_sibling) };
        unsafe { unlock(old_threads_lock, lock_node) };
    }

    let proc_threads_lock = (proc as CULong).wrapping_add(offsets.proc_threads_lock_offset);
    let proc_report_threads = proc_base
        .wrapping_add(offsets.proc_report_threads_list_offset as usize)
        .cast::<AbiListHead>();
    unsafe { lock(proc_threads_lock, lock_node) };
    unsafe {
        process_thread_report_attach_result(
            thread,
            0,
            0,
            0,
            offsets.thread_report_proc_offset,
            proc,
            report_sibling,
            proc_report_threads,
        );
    }
    unsafe { unlock(proc_threads_lock, lock_node) };

    let child = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_proc_offset as usize)
            .cast::<*mut c_void>())
    };
    if child.is_null() {
        return -EFAULT;
    }
    let child_base = child.cast::<u8>();
    let main_thread = unsafe {
        *(child_base
            .wrapping_add(offsets.proc_main_thread_offset as usize)
            .cast::<*mut c_void>())
    };
    if thread == main_thread {
        let parent = unsafe {
            *(child_base
                .wrapping_add(offsets.proc_parent_offset as usize)
                .cast::<*mut c_void>())
        };
        if parent.is_null() {
            return -EFAULT;
        }
        let parent_base = parent.cast::<u8>();
        let parent_pid = unsafe {
            *(parent_base
                .wrapping_add(offsets.proc_pid_offset as usize)
                .cast::<CInt>())
        };
        if let Some(log) = log_fn {
            unsafe { log(PROCESS_PTRACE_TRACEME_LOG_PARENT, parent_pid, 0, 0) };
        }
        let parent_children_lock =
            (parent as CULong).wrapping_add(offsets.proc_children_lock_offset);
        let child_sibling = child_base
            .wrapping_add(offsets.proc_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let child_ptraced_sibling = child_base
            .wrapping_add(offsets.proc_ptraced_siblings_list_offset as usize)
            .cast::<AbiListHead>();
        let parent_ptraced_children = parent_base
            .wrapping_add(offsets.proc_ptraced_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(parent_children_lock, lock_node) };
        unsafe { process_list_detach_result(child_sibling) };
        unsafe { process_list_add_tail_result(child_ptraced_sibling, parent_ptraced_children) };
        unsafe { unlock(parent_children_lock, lock_node) };

        let proc_children_lock = (proc as CULong).wrapping_add(offsets.proc_children_lock_offset);
        let proc_children = proc_base
            .wrapping_add(offsets.proc_children_list_offset as usize)
            .cast::<AbiListHead>();
        unsafe { lock(proc_children_lock, lock_node) };
        unsafe {
            process_ptrace_main_attach_reparent_result(
                child,
                offsets.proc_parent_offset,
                proc,
                child_sibling,
                proc_children,
            );
        }
        unsafe { unlock(proc_children_lock, lock_node) };
    }

    let debugreg = unsafe {
        *(thread_base
            .wrapping_add(offsets.thread_ptrace_debugreg_offset as usize)
            .cast::<*mut c_void>())
    };
    let mut error = 0;
    if debugreg.is_null() {
        let Some(alloc_debugreg) = alloc_debugreg_fn else {
            return -EFAULT;
        };
        error = unsafe { alloc_debugreg(thread) };
        if error < 0 {
            return error;
        }
    }

    let Some(hold_thread) = hold_thread_fn else {
        return -EFAULT;
    };
    let Some(clear_single_step) = clear_single_step_fn else {
        return -EFAULT;
    };
    unsafe { hold_thread(thread) };
    unsafe { clear_single_step(thread) };
    error
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

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_close_all_result(
    head: *mut c_void,
    next_offset: CULong,
    close_offset: CULong,
) -> CInt {
    let mut current = head;
    let mut closed = 0;

    while !current.is_null() {
        let base = current.cast::<u8>();
        let close_slot = base.wrapping_add(close_offset as usize);
        let close_cb = *(close_slot.cast::<Option<ProcessMckfdCloseFn>>());
        if let Some(close_cb) = close_cb {
            let _ = close_cb(current, core::ptr::null_mut());
            closed += 1;
        }

        current = *(base
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>());
    }

    closed
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_drain_free_result(
    headp: *mut *mut c_void,
    next_offset: CULong,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    if headp.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    let mut current = *headp;
    while !current.is_null() {
        let next_slot = current
            .cast::<u8>()
            .wrapping_add(next_offset as usize)
            .cast::<*mut c_void>();
        let next = *next_slot;
        *headp = next;
        *next_slot = core::ptr::null_mut();
        freed += process_mckfd_free_result(current, Some(free_fn));
        current = next;
    }

    freed
}

#[no_mangle]
pub unsafe extern "C" fn process_mckfd_free_result(
    fdp: *mut c_void,
    free_fn: Option<ProcessMckfdFreeFn>,
) -> CInt {
    let Some(free) = free_fn else {
        return 0;
    };

    free(fdp);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_free_result(
    vm: *mut c_void,
    range: *mut c_void,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
) -> CInt {
    if vm.is_null() || range.is_null() {
        return -EINVAL;
    }
    let Some(free) = free_fn else {
        return -EINVAL;
    };

    free(vm, range)
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_log_result(
    vm: *mut c_void,
    range: *mut c_void,
    error: CInt,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(vm, range, error);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_memory_range_free_all_result(
    vm: *mut c_void,
    root: *mut RbRoot,
    node_offset: CULong,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() || root.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut visited = 0;
    let mut node = rb_first(root);
    while !node.is_null() {
        let next = rb_next(node);
        let range = node
            .cast::<u8>()
            .wrapping_sub(node_offset as usize)
            .cast::<c_void>();
        let error = process_memory_range_free_result(vm, range, Some(free_fn));
        if error != 0 {
            let _ = process_memory_range_log_result(vm, range, error, log_fn);
        }
        visited += 1;
        node = next;
    }

    visited
}

#[no_mangle]
pub unsafe extern "C" fn process_flush_memory_body_result(
    vm: *mut ProcessVm,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };

    let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, Some(lock_fn));
    if rc != 0 {
        return rc;
    }
    (*vm).exiting = 1;

    let root = (&raw mut (*vm).vm_range_tree).cast::<RbRoot>();
    let mut attempted = 0;
    let mut node = rb_first(root);
    while !node.is_null() {
        let next = rb_next(node);
        let range = node.cast::<VmRange>();
        if !(*range).memobj.is_null() {
            let error = process_memory_range_free_result(
                vm.cast::<c_void>(),
                range.cast::<c_void>(),
                Some(free_fn),
            );
            attempted += 1;
            if error != 0 {
                let _ = process_memory_range_log_result(
                    vm.cast::<c_void>(),
                    range.cast::<c_void>(),
                    error,
                    log_fn,
                );
            }
        }
        node = next;
    }

    let _ = process_noirq_unlock_result(lock_addr, Some(unlock_fn));
    attempted
}

#[no_mangle]
pub unsafe extern "C" fn process_free_all_memory_ranges_body_result(
    vm: *mut ProcessVm,
    lock_fn: Option<ProcessNoirqLockFn>,
    unlock_fn: Option<ProcessNoirqUnlockFn>,
    free_fn: Option<ProcessMemoryRangeFreeFn>,
    log_fn: Option<ProcessMemoryRangeLogFn>,
) -> CInt {
    if vm.is_null() {
        return 0;
    }
    let Some(lock_fn) = lock_fn else {
        return 0;
    };
    let Some(unlock_fn) = unlock_fn else {
        return 0;
    };
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let lock_addr = (&raw mut (*vm).memory_range_lock).cast::<c_void>() as CULong;
    let rc = process_noirq_lock_result(lock_addr, Some(lock_fn));
    if rc != 0 {
        return rc;
    }
    let visited = process_memory_range_free_all_result(
        vm.cast::<c_void>(),
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        0,
        Some(free_fn),
        log_fn,
    );
    let _ = process_noirq_unlock_result(lock_addr, Some(unlock_fn));
    visited
}

#[inline(always)]
unsafe fn process_cpu_set_word(
    cpu_set_addr: CULong,
    cpu: CInt,
    cpu_set_bits: CInt,
) -> Option<(*mut CULong, CULong)> {
    if cpu_set_addr == 0 || cpu < 0 || cpu_set_bits <= 0 || cpu >= cpu_set_bits {
        return None;
    }

    let word_bits = (core::mem::size_of::<CULong>() * 8) as CInt;
    let word = (cpu / word_bits) as usize;
    let bit = (cpu % word_bits) as CULong;
    Some((
        (cpu_set_addr as *mut CULong).add(word),
        1u64.wrapping_shl(bit as u32),
    ))
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_set_update_body_result(
    cpu_set_addr: CULong,
    lock_addr: CULong,
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    if cpu_set_addr == 0 || lock_addr == 0 {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };

    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mut changed = 0;
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, clear_cpu, cpu_set_bits) {
        *word &= !mask;
        changed += 1;
    }
    if let Some((word, mask)) = process_cpu_set_word(cpu_set_addr, set_cpu, cpu_set_bits) {
        *word |= mask;
        changed += 1;
    }
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));
    changed
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_set_public_result(
    cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        -1,
        cpu,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_clear_public_result(
    cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        cpu,
        -1,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_cpu_clear_and_set_public_result(
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set_addr: CULong,
    lock_addr: CULong,
    cpu_set_bits: CInt,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    process_cpu_set_update_body_result(
        cpu_set_addr,
        lock_addr,
        clear_cpu,
        set_cpu,
        cpu_set_bits,
        lock_fn,
        unlock_fn,
    )
}

unsafe extern "C" fn process_cpu_set_spin_lock_direct(lock_addr: CULong) -> CULong {
    __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock)
}

unsafe extern "C" fn process_cpu_set_spin_unlock_direct(lock_addr: CULong, flags: CULong) {
    __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn cpu_set(cpu: CInt, cpu_set: *mut CpuSet, lock: *mut IhkSpinlock) {
    let _ = process_cpu_set_public_result(
        cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn cpu_clear(cpu: CInt, cpu_set: *mut CpuSet, lock: *mut IhkSpinlock) {
    let _ = process_cpu_clear_public_result(
        cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn cpu_clear_and_set(
    clear_cpu: CInt,
    set_cpu: CInt,
    cpu_set: *mut CpuSet,
    lock: *mut IhkSpinlock,
) {
    let _ = process_cpu_clear_and_set_public_result(
        clear_cpu,
        set_cpu,
        cpu_set as CULong,
        lock as CULong,
        CPU_SET_MAX_CPUS as CInt,
        Some(process_cpu_set_spin_lock_direct),
        Some(process_cpu_set_spin_unlock_direct),
    );
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_inc_result(
    object: *mut c_void,
    ref_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if let Some(inc) = inc_fn {
        inc(object, ref_offset);
        return 0;
    }

    process_ref_inc_direct_result(object, ref_offset)
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_thread_warn_result(
    thread: *mut c_void,
    warn_fn: Option<ProcessHoldThreadWarnFn>,
) -> CInt {
    let Some(warn) = warn_fn else {
        return 0;
    };

    warn(thread);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_ref_hold_body_result(
    object: *mut c_void,
    ref_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    if object.is_null() {
        return -EINVAL;
    }
    let rc = process_ref_inc_result(object, ref_offset, inc_fn);
    if rc != 0 {
        return rc;
    }
    1
}

#[no_mangle]
pub unsafe extern "C" fn hold_process(proc: *mut Process) {
    let _ =
        process_ref_hold_body_result(proc.cast(), offset_of!(Process, refcount) as CULong, None);
}

#[no_mangle]
pub unsafe extern "C" fn hold_process_vm(vm: *mut ProcessVm) {
    let _ =
        process_ref_hold_body_result(vm.cast(), offset_of!(ProcessVm, refcount) as CULong, None);
}

#[no_mangle]
pub unsafe extern "C" fn hold_sigcommon(sigcommon: *mut SigCommon) {
    let _ = process_ref_hold_body_result(
        sigcommon.cast(),
        offset_of!(SigCommon, use_) as CULong,
        None,
    );
}

#[no_mangle]
pub unsafe extern "C" fn hold_thread(thread: *mut Thread) -> CInt {
    let _ = process_hold_thread_body_result(
        thread.cast(),
        offset_of!(Thread, status) as CULong,
        offset_of!(Thread, refcount) as CULong,
        None,
        Some(process_hold_thread_warn_bridge),
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn chain_process(proc: *mut Process) {
    let _ = chain_process_checked(proc);
}

pub(crate) unsafe fn chain_process_checked(proc: *mut Process) -> CInt {
    if proc.is_null() || (*proc).parent.is_null() {
        return -EINVAL;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return -EINVAL;
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return -EINVAL;
    }
    let hash = process_hash((*proc).pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return -EINVAL;
    }

    let parent = (*proc).parent;
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    process_chain_process_body_result(
        &raw mut (*proc).siblings_list,
        &raw mut (*parent).children_list,
        (&raw mut (*parent).children_lock) as *mut _ as CULong,
        &raw mut (*proc).hash_list,
        &raw mut (*phash).list[hash as usize],
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
    )
}

/// The real wait body already removed the child-list entry while holding the
/// parent's children lock. Remove the retained process from hash discovery
/// before consuming the original wait-owned Process edge. Self links allow
/// the existing eventual final-release callbacks to observe no membership.
pub(crate) unsafe fn unpublish_waited_process(proc:*mut Process)->CInt {
    if proc.is_null(){return -EINVAL;}
    let local=get_this_cpu_local_var();
    if local.is_null()||(*local).resource_set.is_null(){return -EINVAL;}
    let phash=(*(*local).resource_set).process_hash;
    let hash=process_hash((*proc).pid);
    if phash.is_null()||hash<0||hash as usize>=PROCESS_HASH_SIZE{return -EINVAL;}
    let mut lock=MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let lock_addr=(&raw mut (*phash).lock[hash as usize])as CULong;
    process_mcs_writer_lock_bridge(lock_addr,lock.as_mut_ptr().cast());
    let entry=&raw mut (*proc).hash_list;
    let result=if process_list_is_linked_result(entry)==0{-EINVAL}else{
        process_list_detach_result(entry);(*entry).next=entry;(*entry).prev=entry;0
    };
    process_mcs_writer_unlock_bridge(lock_addr,lock.as_mut_ptr().cast());result
}

#[no_mangle]
pub unsafe extern "C" fn chain_thread(thread: *mut Thread) {
    let _ = chain_thread_checked(thread);
}

pub(crate) unsafe fn chain_thread_checked(thread: *mut Thread) -> CInt {
    if thread.is_null() || (*thread).proc.is_null() || (*thread).vm.is_null() {
        return -EINVAL;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return -EINVAL;
    }
    let thash = (*(*cpu).resource_set).thread_hash;
    if thash.is_null() {
        return -EINVAL;
    }
    let hash = thread_hash((*thread).tid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    let vm = (*thread).vm;
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    process_chain_thread_body_result(
        &raw mut (*thread).siblings_list,
        &raw mut (*proc).threads_list,
        (&raw mut (*proc).threads_lock) as *mut _ as CULong,
        &raw mut (*thread).hash_list,
        &raw mut (*thash).list[hash as usize],
        (&raw mut (*thash).lock[hash as usize]) as *mut _ as CULong,
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
        None,
    )
}

#[no_mangle]
pub unsafe extern "C" fn destroy_thread(thread: *mut Thread) {
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let _ = process_destroy_thread_body_result(
        thread.cast(),
        offset_of!(Thread, proc) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, cpu_id) as CULong,
        offset_of!(Thread, siblings_list) as CULong,
        offset_of!(Thread, uti_state) as CULong,
        offset_of!(Thread, uti_refill_tid) as CULong,
        offset_of!(Thread, sigpending) as CULong,
        offset_of!(Thread, sigcommon) as CULong,
        offset_of!(Process, threads_lock) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(AddressSpace, cpu_set) as CULong,
        offset_of!(AddressSpace, cpu_set_lock) as CULong,
        offset_of!(SigPending, list) as CULong,
        offset_of!(Thread, ptrace_debugreg) as CULong,
        offset_of!(Thread, ptrace_recvsig) as CULong,
        offset_of!(Thread, ptrace_sendsig) as CULong,
        offset_of!(Thread, fp_regs) as CULong,
        offset_of!(Thread, coredump_regs) as CULong,
        PROCESS_NUM_PROCESSORS,
        lock.as_mut_ptr().cast(),
        Some(process_mcs_writer_lock_bridge),
        Some(process_mcs_writer_unlock_bridge),
        Some(process_destroy_thread_hash_detach_bridge),
        Some(process_destroy_thread_time_account_bridge),
        Some(process_destroy_thread_release_tid_bridge),
        Some(process_destroy_thread_replace_tid_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_optional_free_bridge),
        Some(release_fp_regs),
        Some(process_release_sigcommon_bridge),
        Some(process_free_thread_pages_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_sigcommon(sigcommon: *mut SigCommon) {
    let _ = process_release_sigcommon_public_body_result(
        sigcommon.cast(),
        offset_of!(SigCommon, use_) as CULong,
        offset_of!(SigCommon, sigpending) as CULong,
        offset_of!(SigPending, list) as CULong,
        None,
        Some(process_optional_free_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_thread(thread: *mut Thread) {
    let _ = process_release_thread_body_result(
        thread.cast(),
        offset_of!(Thread, refcount) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, proc) as CULong,
        None,
        Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge),
        Some(process_destroy_thread_bridge),
        Some(process_release_vm_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_thread_checked(thread: *mut Thread) -> CInt {
    process_release_thread_checked_body_result(
        thread.cast(),
        offset_of!(Thread, refcount) as CULong,
        offset_of!(Thread, vm) as CULong,
        offset_of!(Thread, proc) as CULong,
        None,
        Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge),
        Some(process_destroy_thread_bridge),
        Some(process_release_vm_checked_bridge),
    )
}

/// Consume the retained runtime Thread edge once. Return 2 ONLY after the
/// actual Thread, VM and nested Process destructors report final destruction.
/// Any other result consumes possible edges but grants no retry or ACK.
pub(crate) unsafe fn release_thread_runtime_final_checked(thread:*mut Thread)->CInt {
    process_release_thread_checked_body_result(
        thread.cast(), offset_of!(Thread,refcount) as CULong,
        offset_of!(Thread,vm) as CULong, offset_of!(Thread,proc) as CULong,
        None, Some(process_release_thread_profile_bridge),
        Some(process_procfs_delete_thread_bridge), Some(process_destroy_thread_bridge),
        Some(process_release_vm_final_checked_bridge),
    )
}
unsafe extern "C" fn process_release_vm_final_checked_bridge(vm:*mut c_void)->CInt {
    release_process_vm_final_checked(vm.cast())
}
unsafe extern "C" fn process_release_process_final_checked_bridge(proc:*mut c_void)->CInt {
    release_process_checked(proc.cast())
}

#[no_mangle]
pub unsafe extern "C" fn flush_process_memory(vm: *mut ProcessVm) {
    process_flush_memory_debug_bridge(vm.cast(), 0);
    let _ = process_flush_memory_body_result(
        vm,
        Some(process_rw_write_lock_bridge),
        Some(process_rw_write_unlock_bridge),
        Some(process_memory_range_free_bridge),
        Some(process_flush_memory_log_bridge),
    );
    process_flush_memory_debug_bridge(vm.cast(), 1);
}

#[no_mangle]
pub unsafe extern "C" fn free_process_memory_ranges(vm: *mut ProcessVm) {
    let _ = process_free_all_memory_ranges_body_result(
        vm,
        Some(process_rw_write_lock_bridge),
        Some(process_rw_write_unlock_bridge),
        Some(process_memory_range_free_bridge),
        Some(process_memory_range_free_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn free_all_process_memory_range(vm: *mut ProcessVm) {
    let _ = process_free_all_memory_ranges_body_result(
        vm,
        Some(process_rw_write_lock_bridge),
        Some(process_rw_write_unlock_bridge),
        Some(process_memory_range_free_bridge),
        Some(process_memory_range_free_log_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_process(proc: *mut Process) {
    let _ = process_release_process_body_result(
        proc.cast(),
        offset_of!(Process, refcount) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        None,
        Some(process_current_resource_set_bridge),
        Some(process_release_hash_detach_bridge),
        Some(process_release_sibling_detach_bridge),
        Some(process_release_profile_bridge),
        Some(process_free_thread_pages_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_mckfd_free_bridge),
        Some(process_optional_free_bridge),
        Some(process_release_final_cleanup_bridge),
    );
}


// Additive checked wrapper: returns the existing actual destructor result.
#[no_mangle]
pub unsafe extern "C" fn release_process_checked(proc: *mut Process) -> CInt {
    process_release_process_body_result(
        proc.cast(),
        offset_of!(Process, refcount) as CULong,
        offset_of!(Process, tids) as CULong,
        offset_of!(Process, main_thread) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        None,
        Some(process_current_resource_set_bridge),
        Some(process_release_hash_detach_bridge),
        Some(process_release_sibling_detach_bridge),
        Some(process_release_profile_bridge),
        Some(process_free_thread_pages_bridge),
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_mckfd_free_bridge),
        Some(process_optional_free_bridge),
        Some(process_release_final_cleanup_bridge),
    )
}

#[no_mangle]
pub unsafe extern "C" fn release_process_vm(vm: *mut ProcessVm) {
    let _ = process_release_vm_body_result(
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        offset_of!(ProcessVm, proc) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        offset_of!(Mckfd, close_cb) as CULong,
        offset_of!(ProcessVm, free_cb) as CULong,
        offset_of!(ProcessVm, opt) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(Process, pid) as CULong,
        offset_of!(Process, vm) as CULong,
        offset_of!(ProcessVm, vm_range_numa_policy_tree) as CULong,
        offset_of!(VmRangeNumaPolicy, policy_rb_node) as CULong,
        None,
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_flush_vm_bridge),
        Some(process_free_all_ranges_bridge),
        Some(process_detach_address_space_bridge),
        Some(process_release_process_bridge),
        Some(process_policy_free_bridge),
        Some(process_free_vm_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn release_process_vm_checked(vm: *mut ProcessVm) -> CInt {
    process_release_vm_checked_body_result(
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        offset_of!(ProcessVm, proc) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        offset_of!(Mckfd, close_cb) as CULong,
        offset_of!(ProcessVm, free_cb) as CULong,
        offset_of!(ProcessVm, opt) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(Process, pid) as CULong,
        offset_of!(Process, vm) as CULong,
        offset_of!(ProcessVm, vm_range_numa_policy_tree) as CULong,
        offset_of!(VmRangeNumaPolicy, policy_rb_node) as CULong,
        None,
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_flush_vm_bridge),
        Some(process_free_all_ranges_bridge),
        Some(process_detach_address_space_bridge),
        Some(process_release_process_bridge),
        Some(process_policy_free_bridge),
        Some(process_free_vm_bridge),
    )
}

unsafe fn release_process_vm_final_checked(vm: *mut ProcessVm) -> CInt {
    let result = process_release_vm_checked_inner(
        vm.cast(),
        offset_of!(ProcessVm, refcount) as CULong,
        offset_of!(ProcessVm, proc) as CULong,
        offset_of!(Process, mckfd) as CULong,
        offset_of!(Process, mckfd_lock) as CULong,
        offset_of!(Mckfd, next) as CULong,
        offset_of!(Mckfd, close_cb) as CULong,
        offset_of!(ProcessVm, free_cb) as CULong,
        offset_of!(ProcessVm, opt) as CULong,
        offset_of!(ProcessVm, address_space) as CULong,
        offset_of!(Process, pid) as CULong,
        offset_of!(Process, vm) as CULong,
        offset_of!(ProcessVm, vm_range_numa_policy_tree) as CULong,
        offset_of!(VmRangeNumaPolicy, policy_rb_node) as CULong,
        None,
        Some(process_spin_lock_bridge),
        Some(process_spin_unlock_bridge),
        Some(process_flush_vm_bridge),
        Some(process_free_all_ranges_bridge),
        Some(process_detach_address_space_bridge),
        Some(ProcessReleaseRoute::FinalChecked(process_release_process_final_checked_bridge)),
        Some(process_policy_free_bridge),
        Some(process_free_vm_bridge),
    );
    match result { 0 => 0, 2 => 1, error if error < 0 => error, _ => -EBUSY }
}

#[no_mangle]
pub unsafe extern "C" fn thread_unlock(thread: *mut Thread) {
    if !thread.is_null() {
        release_thread(thread);
    }
}

#[no_mangle]
pub unsafe extern "C" fn find_thread(pid: CInt, tid: CInt) -> *mut Thread {
    if tid <= 0 {
        return null_mut();
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return null_mut();
    }
    let thash = (*(*cpu).resource_set).thread_hash;
    if thash.is_null() {
        return null_mut();
    }
    let hash = thread_hash(tid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return null_mut();
    }

    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let offsets = ProcessFindThreadOffsets {
        thread_hash_list_offset: offset_of!(Thread, hash_list) as CULong,
        thread_tid_offset: offset_of!(Thread, tid) as CULong,
        thread_proc_offset: offset_of!(Thread, proc) as CULong,
        proc_pid_offset: offset_of!(Process, pid) as CULong,
    };
    process_find_thread_body_result(
        &raw mut (*thash).list[hash as usize],
        (&raw mut (*thash).lock[hash as usize]) as *mut _ as CULong,
        lock.as_mut_ptr().cast(),
        pid,
        tid,
        &offsets,
        Some(process_mcs_reader_lock_bridge),
        Some(process_mcs_reader_unlock_bridge),
        Some(process_hold_thread_bridge),
    )
    .cast::<Thread>()
}

#[no_mangle]
pub unsafe extern "C" fn find_process(pid: CInt, lock: *mut McsRwlockNodeIrqsave) -> *mut Process {
    if pid <= 0 || lock.is_null() {
        return null_mut();
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return null_mut();
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return null_mut();
    }
    let hash = process_hash(pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return null_mut();
    }

    let offsets = ProcessFindProcessOffsets {
        process_hash_list_offset: offset_of!(Process, hash_list) as CULong,
        process_pid_offset: offset_of!(Process, pid) as CULong,
    };
    process_find_process_body_result(
        &raw mut (*phash).list[hash as usize],
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.cast(),
        pid,
        &offsets,
        Some(process_mcs_reader_lock_bridge),
        Some(process_mcs_reader_unlock_bridge),
    )
    .cast::<Process>()
}

#[no_mangle]
pub unsafe extern "C" fn process_unlock(proc: *mut Process, lock: *mut McsRwlockNodeIrqsave) {
    if proc.is_null() || lock.is_null() {
        return;
    }

    let cpu = get_this_cpu_local_var();
    if cpu.is_null() || (*cpu).resource_set.is_null() {
        return;
    }
    let phash = (*(*cpu).resource_set).process_hash;
    if phash.is_null() {
        return;
    }
    let hash = process_hash((*proc).pid);
    if hash < 0 || hash as usize >= PROCESS_HASH_SIZE {
        return;
    }

    let _ = process_unlock_found_process_result(
        proc.cast(),
        (&raw mut (*phash).lock[hash as usize]) as *mut _ as CULong,
        lock.cast(),
        Some(process_mcs_reader_unlock_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn process_hold_thread_body_result(
    thread: *mut c_void,
    status_offset: CULong,
    refcount_offset: CULong,
    inc_fn: Option<ProcessRefIncFn>,
    warn_fn: Option<ProcessHoldThreadWarnFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }

    let status = *(thread
        .cast::<u8>()
        .wrapping_add(status_offset as usize)
        .cast::<CInt>());
    if process_hold_thread_warn_exited_result(status) != 0 {
        let _ = process_hold_thread_warn_result(thread, warn_fn);
    }

    process_ref_hold_body_result(thread, refcount_offset, inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_result(
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
) -> *mut c_void {
    let Some(current_resource_set) = current_resource_set_fn else {
        return null_mut();
    };

    current_resource_set()
}

#[no_mangle]
pub unsafe extern "C" fn process_resource_process_action_result(
    resource_set: *mut c_void,
    process: *mut c_void,
    action_fn: Option<ProcessResourceProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set, process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_process_action_result(
    process: *mut c_void,
    action_fn: Option<ProcessProcessActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_resource_set_action_result(
    resource_set: *mut c_void,
    action_fn: Option<ProcessResourceSetActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(resource_set);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_action_result(
    thread: *mut c_void,
    action_fn: Option<ProcessThreadActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_thread_profile_result(
    thread: *mut c_void,
    process: *mut c_void,
    profile_fn: Option<ProcessThreadProfileFn>,
) -> CInt {
    let Some(profile) = profile_fn else {
        return 0;
    };

    profile(thread, process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_action_result(
    vm: *mut c_void,
    action_fn: Option<ProcessVmActionFn>,
) -> CInt {
    let Some(action) = action_fn else {
        return -EINVAL;
    };

    action(vm);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_policy_free_result(
    policy: *mut c_void,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    let Some(policy_free) = policy_free_fn else {
        return -EINVAL;
    };

    policy_free(policy);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_free_cb_result(
    vm: *mut c_void,
    opt: *mut c_void,
    free_cb: Option<ProcessVmFreeCallback>,
) -> CInt {
    let Some(free_cb) = free_cb else {
        return 0;
    };

    free_cb(vm, opt);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_lock_result(
    lock_addr: CULong,
    lock_fn: Option<ProcessSpinLockFn>,
) -> CULong {
    let Some(lock) = lock_fn else {
        return 0;
    };

    lock(lock_addr)
}

#[no_mangle]
pub unsafe extern "C" fn process_spin_unlock_result(
    lock_addr: CULong,
    irqstate: CULong,
    unlock_fn: Option<ProcessSpinUnlockFn>,
) -> CInt {
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    unlock(lock_addr, irqstate);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_process_body_result(
    proc: *mut c_void,
    refcount_offset: CULong,
    tids_offset: CULong,
    main_thread_offset: CULong,
    mckfd_offset: CULong,
    mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    current_resource_set_fn: Option<ProcessCurrentResourceSetFn>,
    hash_detach_fn: Option<ProcessResourceProcessActionFn>,
    sibling_detach_fn: Option<ProcessProcessActionFn>,
    profile_fn: Option<ProcessProcessActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    mckfd_free_fn: Option<ProcessMckfdFreeFn>,
    free_fn: Option<ProcessFreeFn>,
    final_cleanup_fn: Option<ProcessResourceSetActionFn>,
) -> CInt {
    if proc.is_null() {
        return -EINVAL;
    }
    let Some(current_resource_set_fn) = current_resource_set_fn else {
        return -EINVAL;
    };
    let Some(hash_detach_fn) = hash_detach_fn else {
        return -EINVAL;
    };
    let Some(sibling_detach_fn) = sibling_detach_fn else {
        return -EINVAL;
    };
    let Some(free_thread_pages_fn) = free_thread_pages_fn else {
        return -EINVAL;
    };
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(mckfd_free_fn) = mckfd_free_fn else {
        return -EINVAL;
    };
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    let Some(final_cleanup_fn) = final_cleanup_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        proc,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let resource_set = process_current_resource_set_result(Some(current_resource_set_fn));
    let _ = process_resource_process_action_result(resource_set, proc, Some(hash_detach_fn));
    let _ = process_process_action_result(proc, Some(sibling_detach_fn));

    let tids = field_ptr(proc, tids_offset);
    if !tids.is_null() {
        let _ = process_free_callback_result(tids, Some(free_fn));
    }

    if let Some(profile_fn) = profile_fn {
        let _ = process_process_action_result(proc, Some(profile_fn));
    }

    let main_thread = field_ptr(proc, main_thread_offset);
    if !main_thread.is_null() {
        let _ = process_thread_action_result(main_thread, Some(free_thread_pages_fn));
    }

    let lock_addr = (proc as CULong).wrapping_add(mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_headp = proc
        .cast::<u8>()
        .wrapping_add(mckfd_offset as usize)
        .cast::<*mut c_void>();
    process_mckfd_drain_free_result(mckfd_headp, mckfd_next_offset, Some(mckfd_free_fn));
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let _ = process_free_callback_result(proc, Some(free_fn));
    let _ = process_resource_set_action_result(resource_set, Some(final_cleanup_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_vm_policy_drain_free_result(
    root: *mut RbRoot,
    node_offset: CULong,
    free_fn: Option<ProcessPolicyFreeFn>,
) -> CInt {
    if root.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let mut freed = 0;
    loop {
        let node = rb_first(root);
        if node.is_null() {
            break;
        }
        let policy = node
            .cast::<u8>()
            .wrapping_sub(node_offset as usize)
            .cast::<c_void>();
        rb_erase(node, root);
        let _ = process_policy_free_result(policy, Some(free_fn));
        freed += 1;
    }

    freed
}

#[no_mangle]
pub unsafe extern "C" fn process_detach_address_space_pid_result(
    address_space: *mut c_void,
    pid: CInt,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
) -> CInt {
    let Some(detach) = detach_fn else {
        return -EINVAL;
    };

    detach(address_space, pid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_process_action_result(
    process: *mut c_void,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    let Some(release) = release_fn else {
        return -EINVAL;
    };

    release(process);
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_detach_process_result(
    vm: *mut c_void,
    address_space_offset: CULong,
    proc_offset: CULong,
    pid_offset: CULong,
    proc_vm_offset: CULong,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_fn: Option<ProcessReleaseProcessFn>,
) -> CInt {
    if vm.is_null() {
        return 0;
    }
    let (Some(detach_fn), Some(release_fn)) = (detach_fn, release_fn) else {
        return 0;
    };

    let vm_base = vm.cast::<u8>();
    let address_space = *(vm_base
        .wrapping_add(address_space_offset as usize)
        .cast::<*mut c_void>());
    let proc = *(vm_base
        .wrapping_add(proc_offset as usize)
        .cast::<*mut c_void>());
    if proc.is_null() {
        return 0;
    }

    let proc_base = proc.cast::<u8>();
    let pid = *(proc_base.wrapping_add(pid_offset as usize).cast::<CInt>());
    let _ = process_detach_address_space_pid_result(address_space, pid, Some(detach_fn));
    *(proc_base
        .wrapping_add(proc_vm_offset as usize)
        .cast::<*mut c_void>()) = core::ptr::null_mut();
    let _ = process_release_process_action_result(proc, Some(release_fn));
    1
}

/// Cache all inputs before the possibly final Process callback. The result is
/// the real callback result, never inferred from the former reference count.
unsafe fn process_release_vm_detach_final_checked(
    vm:*mut c_void,address_space_offset:CULong,proc_offset:CULong,
    pid_offset:CULong,proc_vm_offset:CULong,detach:ProcessDetachAddressSpaceFn,
    release:ProcessVmReleaseCheckedFn,
)->CInt {
    let address_space=field_ptr(vm,address_space_offset);
    let proc=field_ptr(vm,proc_offset);
    if proc.is_null(){return -EINVAL;}
    let pid=*(proc.cast::<u8>().add(pid_offset as usize).cast::<CInt>());
    let _=process_detach_address_space_pid_result(address_space,pid,Some(detach));
    *proc.cast::<u8>().add(proc_vm_offset as usize).cast::<*mut c_void>()=core::ptr::null_mut();
    release(proc)
}

#[no_mangle]
pub unsafe extern "C" fn process_release_fp_regs_result(
    thread: *mut c_void,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
) -> CInt {
    let Some(release_fp) = release_fp_fn else {
        return 0;
    };

    release_fp(thread);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_optional_cleanup_result(
    thread: *mut c_void,
    debugreg_offset: CULong,
    recvsig_offset: CULong,
    sendsig_offset: CULong,
    fp_regs_offset: CULong,
    coredump_regs_offset: CULong,
    free_fn: Option<ProcessOptionalFreeFn>,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
) -> CInt {
    if thread.is_null() {
        return 0;
    }
    let Some(free_fn) = free_fn else {
        return 0;
    };

    let base = thread.cast::<u8>();
    let mut actions = 0;
    for offset in [debugreg_offset, recvsig_offset, sendsig_offset] {
        let ptr = *(base.wrapping_add(offset as usize).cast::<*mut c_void>());
        if !ptr.is_null() {
            let _ = process_free_callback_result(ptr, Some(free_fn));
            actions += 1;
        }
    }

    let fp_regs = *(base
        .wrapping_add(fp_regs_offset as usize)
        .cast::<*mut c_void>());
    if !fp_regs.is_null() {
        actions += process_release_fp_regs_result(thread, release_fp_fn);
    }

    let coredump_regs = *(base
        .wrapping_add(coredump_regs_offset as usize)
        .cast::<*mut c_void>());
    let _ = process_free_callback_result(coredump_regs, Some(free_fn));
    actions + 1
}

#[inline]
unsafe fn field_ptr(base: *mut c_void, offset: CULong) -> *mut c_void {
    *(base
        .cast::<u8>()
        .wrapping_add(offset as usize)
        .cast::<*mut c_void>())
}

#[no_mangle]
pub unsafe extern "C" fn process_release_sigcommon_body_result(
    sigcommon: *mut c_void,
    dec_and_test: CInt,
    sigpending_empty: CInt,
    sigpending_offset: CULong,
    pending_list_offset: CULong,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if sigcommon.is_null() {
        return -EINVAL;
    }
    let Some(free_fn) = free_fn else {
        return -EINVAL;
    };
    if process_sigcommon_release_should_destroy_result(dec_and_test) == 0 {
        return 0;
    }

    if process_sigpending_cleanup_needed_result(sigpending_empty) != 0 {
        let head = sigcommon
            .cast::<u8>()
            .wrapping_add(sigpending_offset as usize)
            .cast::<AbiListHead>();
        loop {
            let pending = process_sigpending_pop_front_result(head, pending_list_offset);
            if pending.is_null() {
                break;
            }
            let _ = process_free_callback_result(pending, Some(free_fn));
        }
    }

    let _ = process_free_callback_result(sigcommon, Some(free_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_sigcommon_public_body_result(
    sigcommon: *mut c_void,
    use_offset: CULong,
    sigpending_offset: CULong,
    pending_list_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    free_fn: Option<ProcessFreeFn>,
) -> CInt {
    if sigcommon.is_null() {
        return -EINVAL;
    }
    let head = sigcommon
        .cast::<u8>()
        .wrapping_add(sigpending_offset as usize)
        .cast::<AbiListHead>();
    let sigpending_empty = ((*head).next == head) as CInt;
    process_release_sigcommon_body_result(
        sigcommon,
        process_ref_dec_and_test_result(sigcommon, use_offset, dec_fn),
        sigpending_empty,
        sigpending_offset,
        pending_list_offset,
        free_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn process_release_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    thread_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_release_slot_result(tids, index, tid_stride, tid_thread_offset) == 0 {
        return 0;
    }

    let _ = process_tid_log_result(thread_tid, thread, 0, log_fn);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_tid_log_result(
    old_tid: CInt,
    thread: *mut c_void,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    let Some(log) = log_fn else {
        return 0;
    };

    log(old_tid, thread, new_tid);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_replace_tid_body_result(
    tids: *mut c_void,
    nr_tids: CInt,
    tid_stride: CULong,
    tid_offset: CULong,
    tid_thread_offset: CULong,
    thread: *mut c_void,
    old_tid: CInt,
    new_tid: CInt,
    log_fn: Option<ProcessTidLogFn>,
) -> CInt {
    if tids.is_null() || thread.is_null() {
        return 0;
    }

    let index = process_tid_index_for_thread_result(
        tids,
        nr_tids,
        tid_stride,
        tid_thread_offset,
        thread as CULong,
    );
    if process_tid_index_found_result(index) == 0 {
        return 0;
    }
    if process_tid_replace_slot_result(
        tids,
        index,
        tid_stride,
        tid_offset,
        tid_thread_offset,
        new_tid,
    ) == 0
    {
        return 0;
    }

    let _ = process_tid_log_result(old_tid, thread, new_tid, log_fn);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_chain_process_body_result(
    siblings_entry: *mut AbiListHead,
    children_head: *mut AbiListHead,
    children_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if siblings_entry.is_null()
        || children_head.is_null()
        || hash_entry.is_null()
        || hash_head.is_null()
        || lock_node.is_null()
    {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return -EINVAL;
    };

    lock_fn(children_lock_addr, lock_node);
    process_list_add_tail_result(siblings_entry, children_head);
    unlock_fn(children_lock_addr, lock_node);

    lock_fn(hash_lock_addr, lock_node);
    process_list_add_tail_result(hash_entry, hash_head);
    unlock_fn(hash_lock_addr, lock_node);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_chain_thread_body_result(
    siblings_entry: *mut AbiListHead,
    threads_head: *mut AbiListHead,
    threads_lock_addr: CULong,
    hash_entry: *mut AbiListHead,
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    vm: *mut c_void,
    vm_refcount_offset: CULong,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    ref_inc_fn: Option<ProcessRefIncFn>,
) -> CInt {
    let rc = process_chain_process_body_result(
        siblings_entry,
        threads_head,
        threads_lock_addr,
        hash_entry,
        hash_head,
        hash_lock_addr,
        lock_node,
        lock_fn,
        unlock_fn,
    );
    if rc < 0 {
        return rc;
    }
    process_ref_inc_result(vm, vm_refcount_offset, ref_inc_fn)
}

#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_body_result(
    thread: *mut c_void,
    thread_proc_offset: CULong,
    thread_vm_offset: CULong,
    thread_cpu_id_offset: CULong,
    thread_siblings_list_offset: CULong,
    thread_uti_state_offset: CULong,
    thread_uti_refill_tid_offset: CULong,
    thread_sigpending_offset: CULong,
    thread_sigcommon_offset: CULong,
    proc_threads_lock_offset: CULong,
    proc_tids_offset: CULong,
    proc_main_thread_offset: CULong,
    vm_address_space_offset: CULong,
    address_space_cpu_set_offset: CULong,
    address_space_cpu_set_lock_offset: CULong,
    pending_list_offset: CULong,
    debugreg_offset: CULong,
    recvsig_offset: CULong,
    sendsig_offset: CULong,
    fp_regs_offset: CULong,
    coredump_regs_offset: CULong,
    cpu_set_bits: CInt,
    lock_node: *mut c_void,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    hash_detach_fn: Option<ProcessThreadActionFn>,
    time_account_fn: Option<ProcessThreadActionFn>,
    release_tid_fn: Option<ProcessThreadProcActionFn>,
    replace_tid_fn: Option<ProcessThreadTidActionFn>,
    cpu_lock_fn: Option<ProcessSpinLockFn>,
    cpu_unlock_fn: Option<ProcessSpinUnlockFn>,
    free_fn: Option<ProcessOptionalFreeFn>,
    release_fp_fn: Option<ProcessReleaseFpRegsFn>,
    release_sigcommon_fn: Option<ProcessThreadActionFn>,
    free_thread_pages_fn: Option<ProcessThreadActionFn>,
) -> CInt {
    if thread.is_null() || lock_node.is_null() {
        return -EINVAL;
    }
    let (
        Some(lock_fn),
        Some(unlock_fn),
        Some(hash_detach_fn),
        Some(time_account_fn),
        Some(release_tid_fn),
        Some(replace_tid_fn),
        Some(cpu_lock_fn),
        Some(cpu_unlock_fn),
        Some(free_fn),
        Some(release_sigcommon_fn),
        Some(free_thread_pages_fn),
    ) = (
        lock_fn,
        unlock_fn,
        hash_detach_fn,
        time_account_fn,
        release_tid_fn,
        replace_tid_fn,
        cpu_lock_fn,
        cpu_unlock_fn,
        free_fn,
        release_sigcommon_fn,
        free_thread_pages_fn,
    )
    else {
        return -EINVAL;
    };

    hash_detach_fn(thread);
    time_account_fn(thread);

    let proc = field_ptr(thread, thread_proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }
    let thread_base = thread.cast::<u8>();
    let threads_lock_addr = (proc as CULong).wrapping_add(proc_threads_lock_offset);

    lock_fn(threads_lock_addr, lock_node);
    let siblings = thread_base
        .wrapping_add(thread_siblings_list_offset as usize)
        .cast::<AbiListHead>();
    process_list_detach_result(siblings);

    let tids = field_ptr(proc, proc_tids_offset);
    let main_thread = field_ptr(proc, proc_main_thread_offset);
    let uti_state = *(thread_base
        .wrapping_add(thread_uti_state_offset as usize)
        .cast::<CInt>());
    match process_destroy_thread_tid_action_result(
        (!tids.is_null()) as CInt,
        (thread == main_thread) as CInt,
        uti_state,
    ) {
        PROCESS_TID_ACTION_REPLACE => {
            let new_tid = *(thread_base
                .wrapping_add(thread_uti_refill_tid_offset as usize)
                .cast::<CInt>());
            replace_tid_fn(proc, thread, new_tid);
        }
        PROCESS_TID_ACTION_RELEASE => release_tid_fn(proc, thread),
        _ => {}
    }

    let vm = field_ptr(thread, thread_vm_offset);
    if !vm.is_null() {
        let address_space = field_ptr(vm, vm_address_space_offset);
        if !address_space.is_null() {
            let cpu_id = *(thread_base
                .wrapping_add(thread_cpu_id_offset as usize)
                .cast::<CInt>());
            let cpu_set_addr = (address_space as CULong).wrapping_add(address_space_cpu_set_offset);
            let cpu_set_lock_addr =
                (address_space as CULong).wrapping_add(address_space_cpu_set_lock_offset);
            let _ = process_cpu_set_update_body_result(
                cpu_set_addr,
                cpu_set_lock_addr,
                cpu_id,
                -1,
                cpu_set_bits,
                Some(cpu_lock_fn),
                Some(cpu_unlock_fn),
            );
        }
    }

    let sigpending = thread_base
        .wrapping_add(thread_sigpending_offset as usize)
        .cast::<AbiListHead>();
    let sigpending_empty =
        ((!(*sigpending).next.is_null()) && (*sigpending).next == sigpending) as CInt;
    if process_sigpending_cleanup_needed_result(sigpending_empty) != 0 {
        let _ =
            process_sigpending_drain_free_result(sigpending, pending_list_offset, Some(free_fn));
    }

    let _ = process_destroy_thread_optional_cleanup_result(
        thread,
        debugreg_offset,
        recvsig_offset,
        sendsig_offset,
        fp_regs_offset,
        coredump_regs_offset,
        Some(free_fn),
        release_fp_fn,
    );

    let sigcommon = field_ptr(thread, thread_sigcommon_offset);
    release_sigcommon_fn(sigcommon);

    if process_thread_should_free_pages_result((thread == main_thread) as CInt) != 0 {
        free_thread_pages_fn(thread);
    }
    unlock_fn(threads_lock_addr, lock_node);
    1
}

#[inline]
unsafe fn process_list_container(entry: *mut AbiListHead, list_offset: CULong) -> *mut c_void {
    entry
        .cast::<u8>()
        .wrapping_sub(list_offset as usize)
        .cast::<c_void>()
}

#[no_mangle]
pub unsafe extern "C" fn process_find_thread_body_result(
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    pid: CInt,
    tid: CInt,
    offsets: *const ProcessFindThreadOffsets,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
    hold_fn: Option<ProcessThreadActionFn>,
) -> *mut c_void {
    if tid <= 0 {
        return null_mut();
    }
    if hash_head.is_null() || lock_node.is_null() || offsets.is_null() {
        return null_mut();
    }
    let (Some(lock_fn), Some(unlock_fn), Some(hold_fn)) = (lock_fn, unlock_fn, hold_fn) else {
        return null_mut();
    };
    let offsets = &*offsets;

    lock_fn(hash_lock_addr, lock_node);
    let mut match_pid = pid;
    loop {
        let mut entry = (*hash_head).next;
        while !entry.is_null() && entry != hash_head {
            let thread = process_list_container(entry, offsets.thread_hash_list_offset);
            let thread_base = thread.cast::<u8>();
            let thread_tid = *(thread_base
                .wrapping_add(offsets.thread_tid_offset as usize)
                .cast::<CInt>());
            if thread_tid == tid {
                let proc = field_ptr(thread, offsets.thread_proc_offset);
                let proc_pid = if proc.is_null() {
                    0
                } else {
                    *(proc
                        .cast::<u8>()
                        .wrapping_add(offsets.proc_pid_offset as usize)
                        .cast::<CInt>())
                };
                if match_pid <= 0 || proc_pid == match_pid {
                    hold_fn(thread);
                    unlock_fn(hash_lock_addr, lock_node);
                    return thread;
                }
            }
            entry = (*entry).next;
        }
        if match_pid > 0 && match_pid == tid {
            match_pid = 0;
            continue;
        }
        break;
    }

    unlock_fn(hash_lock_addr, lock_node);
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_find_process_body_result(
    hash_head: *mut AbiListHead,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    pid: CInt,
    offsets: *const ProcessFindProcessOffsets,
    lock_fn: Option<ProcessMcsRwlockFn>,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> *mut c_void {
    if pid <= 0 {
        return null_mut();
    }
    if hash_head.is_null() || lock_node.is_null() || offsets.is_null() {
        return null_mut();
    }
    let (Some(lock_fn), Some(unlock_fn)) = (lock_fn, unlock_fn) else {
        return null_mut();
    };
    let offsets = &*offsets;

    lock_fn(hash_lock_addr, lock_node);
    let mut entry = (*hash_head).next;
    while !entry.is_null() && entry != hash_head {
        let process = process_list_container(entry, offsets.process_hash_list_offset);
        let proc_pid = *(process
            .cast::<u8>()
            .wrapping_add(offsets.process_pid_offset as usize)
            .cast::<CInt>());
        if proc_pid == pid {
            return process;
        }
        entry = (*entry).next;
    }

    unlock_fn(hash_lock_addr, lock_node);
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn process_unlock_found_process_result(
    process: *mut c_void,
    hash_lock_addr: CULong,
    lock_node: *mut c_void,
    unlock_fn: Option<ProcessMcsRwlockFn>,
) -> CInt {
    if process.is_null() {
        return 0;
    }
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    unlock_fn(hash_lock_addr, lock_node);
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_thread_body_result(
    thread: *mut c_void,
    refcount_offset: CULong,
    vm_offset: CULong,
    proc_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    profile_fn: Option<ProcessThreadProfileFn>,
    procfs_delete_fn: Option<ProcessThreadActionFn>,
    destroy_thread_fn: Option<ProcessThreadActionFn>,
    release_vm_fn: Option<ProcessVmActionFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let Some(procfs_delete_fn) = procfs_delete_fn else {
        return -EINVAL;
    };
    let Some(destroy_thread_fn) = destroy_thread_fn else {
        return -EINVAL;
    };
    let Some(release_vm_fn) = release_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        thread,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let vm = field_ptr(thread, vm_offset);
    let proc = field_ptr(thread, proc_offset);
    let _ = process_thread_profile_result(thread, proc, profile_fn);
    let _ = process_thread_action_result(thread, Some(procfs_delete_fn));
    let _ = process_thread_action_result(thread, Some(destroy_thread_fn));
    let _ = process_vm_action_result(vm, Some(release_vm_fn));
    1
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_body_result(
    vm: *mut c_void,
    refcount_offset: CULong,
    proc_offset: CULong,
    proc_mckfd_offset: CULong,
    proc_mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    mckfd_close_offset: CULong,
    vm_free_cb_offset: CULong,
    vm_opt_offset: CULong,
    vm_address_space_offset: CULong,
    proc_pid_offset: CULong,
    proc_vm_offset: CULong,
    vm_policy_tree_offset: CULong,
    policy_node_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    flush_fn: Option<ProcessVmActionFn>,
    free_ranges_fn: Option<ProcessVmActionFn>,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_process_fn: Option<ProcessReleaseProcessFn>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let Some(lock_fn) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock_fn) = unlock_fn else {
        return -EINVAL;
    };
    let Some(flush_fn) = flush_fn else {
        return -EINVAL;
    };
    let Some(free_ranges_fn) = free_ranges_fn else {
        return -EINVAL;
    };
    let Some(free_vm_fn) = free_vm_fn else {
        return -EINVAL;
    };

    if process_ref_release_should_destroy_result(process_ref_dec_and_test_result(
        vm,
        refcount_offset,
        dec_fn,
    )) == 0
    {
        return 0;
    }

    let proc = field_ptr(vm, proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }

    let lock_addr = (proc as CULong).wrapping_add(proc_mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_head = field_ptr(proc, proc_mckfd_offset);
    process_mckfd_close_all_result(mckfd_head, mckfd_next_offset, mckfd_close_offset);
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let free_cb_slot = vm
        .cast::<u8>()
        .wrapping_add(vm_free_cb_offset as usize)
        .cast::<Option<ProcessVmFreeCallback>>();
    let free_cb = *free_cb_slot;
    if process_release_vm_should_run_free_cb_result(free_cb.map_or(0, |f| f as usize as CULong))
        != 0
    {
        let opt = field_ptr(vm, vm_opt_offset);
        let _ = process_vm_free_cb_result(vm, opt, free_cb);
    }

    let _ = process_vm_action_result(vm, Some(flush_fn));
    let _ = process_vm_action_result(vm, Some(free_ranges_fn));

    process_release_vm_detach_process_result(
        vm,
        vm_address_space_offset,
        proc_offset,
        proc_pid_offset,
        proc_vm_offset,
        detach_fn,
        release_process_fn,
    );

    let policy_root = vm
        .cast::<u8>()
        .wrapping_add(vm_policy_tree_offset as usize)
        .cast::<RbRoot>();
    process_vm_policy_drain_free_result(policy_root, policy_node_offset, policy_free_fn);
    let _ = process_free_callback_result(vm, Some(free_vm_fn));
    1
}

/// Additive final-destruction proof; legacy nonzero decrement policy is not
/// suitable here. Every result consumes at most the one selected reference.
/// Errors provide no retry or rollback authority over either input pointer.
#[no_mangle]
pub unsafe extern "C" fn process_release_thread_checked_body_result(
    thread: *mut c_void,
    refcount_offset: CULong,
    vm_offset: CULong,
    proc_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    profile_fn: Option<ProcessThreadProfileFn>,
    procfs_delete_fn: Option<ProcessThreadActionFn>,
    destroy_thread_fn: Option<ProcessThreadActionFn>,
    release_vm_fn: Option<ProcessVmReleaseCheckedFn>,
) -> CInt {
    if thread.is_null() {
        return -EINVAL;
    }
    let (Some(procfs_delete_fn), Some(destroy_thread_fn), Some(release_vm_fn)) =
        (procfs_delete_fn, destroy_thread_fn, release_vm_fn)
    else {
        return -EINVAL;
    };
    // Cache both pointers before any decrement or destructive callback.
    let vm = field_ptr(thread, vm_offset);
    let proc = field_ptr(thread, proc_offset);
    if vm.is_null() || proc.is_null() {
        return -EINVAL;
    }
    match process_ref_dec_and_test_result(thread, refcount_offset, dec_fn) {
        0 => return 0,
        1 => {},
        error if error < 0 => return error,
        _ => return -EINVAL,
    }
    let _ = process_thread_profile_result(thread, proc, profile_fn);
    procfs_delete_fn(thread);
    destroy_thread_fn(thread);
    // thread is dead. Only cached vm may be passed to the checked callback;
    // vm may also become dead before the callback returns.
    match release_vm_fn(vm) {
        0 => 1,
        1 => 2,
        error if error < 0 => error,
        _ => -EINVAL,
    }
}

#[no_mangle]
pub unsafe extern "C" fn process_release_vm_checked_body_result(
    vm: *mut c_void,
    refcount_offset: CULong,
    proc_offset: CULong,
    proc_mckfd_offset: CULong,
    proc_mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    mckfd_close_offset: CULong,
    vm_free_cb_offset: CULong,
    vm_opt_offset: CULong,
    vm_address_space_offset: CULong,
    proc_pid_offset: CULong,
    proc_vm_offset: CULong,
    vm_policy_tree_offset: CULong,
    policy_node_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    flush_fn: Option<ProcessVmActionFn>,
    free_ranges_fn: Option<ProcessVmActionFn>,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_process_fn: Option<ProcessReleaseProcessFn>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    process_release_vm_checked_inner(
        vm,
        refcount_offset,
        proc_offset,
        proc_mckfd_offset,
        proc_mckfd_lock_offset,
        mckfd_next_offset,
        mckfd_close_offset,
        vm_free_cb_offset,
        vm_opt_offset,
        vm_address_space_offset,
        proc_pid_offset,
        proc_vm_offset,
        vm_policy_tree_offset,
        policy_node_offset,
        dec_fn,
        lock_fn,
        unlock_fn,
        flush_fn,
        free_ranges_fn,
        detach_fn,
        release_process_fn.map(ProcessReleaseRoute::Existing),
        policy_free_fn,
        free_vm_fn,
    )
}

// Distinct Rust-only route: no legacy C callback or result encoding changes.
enum ProcessReleaseRoute {
    Existing(ProcessReleaseProcessFn),
    FinalChecked(ProcessVmReleaseCheckedFn),
}
unsafe fn process_release_vm_checked_inner(
    vm: *mut c_void,
    refcount_offset: CULong,
    proc_offset: CULong,
    proc_mckfd_offset: CULong,
    proc_mckfd_lock_offset: CULong,
    mckfd_next_offset: CULong,
    mckfd_close_offset: CULong,
    vm_free_cb_offset: CULong,
    vm_opt_offset: CULong,
    vm_address_space_offset: CULong,
    proc_pid_offset: CULong,
    proc_vm_offset: CULong,
    vm_policy_tree_offset: CULong,
    policy_node_offset: CULong,
    dec_fn: Option<ProcessRefDecAndTestFn>,
    lock_fn: Option<ProcessSpinLockFn>,
    unlock_fn: Option<ProcessSpinUnlockFn>,
    flush_fn: Option<ProcessVmActionFn>,
    free_ranges_fn: Option<ProcessVmActionFn>,
    detach_fn: Option<ProcessDetachAddressSpaceFn>,
    release_process_fn: Option<ProcessReleaseRoute>,
    policy_free_fn: Option<ProcessPolicyFreeFn>,
    free_vm_fn: Option<ProcessFreeFn>,
) -> CInt {
    if vm.is_null() {
        return -EINVAL;
    }
    let (Some(lock_fn), Some(unlock_fn), Some(flush_fn), Some(free_ranges_fn), Some(free_vm_fn)) =
        (lock_fn, unlock_fn, flush_fn, free_ranges_fn, free_vm_fn)
    else {
        return -EINVAL;
    };
    if detach_fn.is_none() || release_process_fn.is_none() || policy_free_fn.is_none() {
        return -EINVAL;
    }
    let proc = field_ptr(vm, proc_offset);
    if proc.is_null() {
        return -EINVAL;
    }
    match process_ref_dec_and_test_result(vm, refcount_offset, dec_fn) {
        0 => return 0,
        1 => {},
        error if error < 0 => return error,
        _ => return -EINVAL,
    }
    let lock_addr = (proc as CULong).wrapping_add(proc_mckfd_lock_offset);
    let irqstate = process_spin_lock_result(lock_addr, Some(lock_fn));
    let mckfd_head = field_ptr(proc, proc_mckfd_offset);
    process_mckfd_close_all_result(mckfd_head, mckfd_next_offset, mckfd_close_offset);
    let _ = process_spin_unlock_result(lock_addr, irqstate, Some(unlock_fn));

    let free_cb = *(vm.cast::<u8>().wrapping_add(vm_free_cb_offset as usize)
        .cast::<Option<ProcessVmFreeCallback>>());
    if let Some(free_cb) = free_cb {
        let opt = field_ptr(vm, vm_opt_offset);
        free_cb(vm, opt);
    }
    flush_fn(vm);
    free_ranges_fn(vm);
    let nested = match release_process_fn.unwrap() {
        ProcessReleaseRoute::Existing(release) => {
            process_release_vm_detach_process_result(
                vm, vm_address_space_offset, proc_offset, proc_pid_offset, proc_vm_offset,
                detach_fn, Some(release),
            );
            0 // Legacy callback cannot report final Process destruction.
        },
        ProcessReleaseRoute::FinalChecked(release) => process_release_vm_detach_final_checked(
            vm, vm_address_space_offset, proc_offset, proc_pid_offset, proc_vm_offset,
            detach_fn.unwrap(), release,
        ),
    };
    let policy_root = vm.cast::<u8>().wrapping_add(vm_policy_tree_offset as usize).cast::<RbRoot>();
    process_vm_policy_drain_free_result(policy_root, policy_node_offset, policy_free_fn);
    free_vm_fn(vm);
    // No read of either dead allocation follows the callbacks. Existing
    // callers retain their original 0/1 contract; only the distinct checked
    // route can report 2 for final VM AND nested Process destruction.
    if nested < 0 { nested } else if nested == 1 { 2 } else { 1 }
}

// This private callback preserves the existing optional dynamic-debug event.
#[used]
#[link_section = "__verbose"]
static mut RELEASE_TID_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"process_release_tid_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

extern "C" {
    fn kprintf(format: *const i8, ...) -> CInt;
}

unsafe extern "C" fn process_release_tid_log_bridge(
    tid: CInt, thread: *mut c_void, _new_tid: CInt,
) {
    let flags = unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(RELEASE_TID_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid %d has been released by %p\n\0".as_ptr().cast(),
                b"__release_tid\0".as_ptr().cast::<i8>(), tid, thread,
            );
        }
    }
}

const _: () = {
    assert!(offset_of!(Process, tids) == 256);
    assert!(offset_of!(Process, nr_tids) == 264);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(size_of::<crate::abi::McexecTid>() == 16);
    assert!(offset_of!(crate::abi::McexecTid, thread) == 8);
};

/// Release the first slot referring to this live thread under threads_lock.
///
/// Both pointers must be valid and live through the call. The caller holds the
/// owning process's threads_lock and excludes concurrent/reentrant slot changes.
/// `tids` is null or covers `nr_tids` entries when that count is positive.
/// The helper clears only the matched thread pointer, retaining the numeric TID,
/// and invokes diagnostics after the clear. This does not free thread storage.
#[no_mangle]
pub unsafe extern "C" fn __release_tid(proc: *mut Process, thread: *mut Thread) {
    let _ = unsafe {
        process_release_tid_body_result(
            (*proc).tids, (*proc).nr_tids,
            size_of::<crate::abi::McexecTid>() as CULong,
            offset_of!(crate::abi::McexecTid, thread) as CULong,
            thread.cast(), (*thread).tid, Some(process_release_tid_log_bridge),
        )
    };
}

// Reuse existing exported time operations; aliases avoid leaf-batch name clashes.
extern "C" {
    #[link_name = "tsc_to_ts"]
    fn process_teardown_tsc_to_ts(tsc: CULong, ts: *mut crate::abi::TimeSpec);
    #[link_name = "ts_add"]
    fn process_teardown_ts_add(dst: *mut crate::abi::TimeSpec, src: *const crate::abi::TimeSpec);
}

const _: () = {
    assert!(offset_of!(Thread, proc) == 4304);
    assert!(offset_of!(Thread, system_tsc) == 5040);
    assert!(offset_of!(Thread, user_tsc) == 5048);
    assert!(offset_of!(Process, update_lock) == 64);
    assert!(offset_of!(Process, stime) == 1296);
    assert!(offset_of!(Process, utime) == 1312);
    assert!(size_of::<crate::abi::TimeSpec>() == 16);
};

/// Accumulate both live thread clocks under the existing process update lock.
/// The thread and owning process remain valid and stable through synchronous
/// lock/time callbacks; this callback acquires and releases the same lock once.
/// Existing initialized clock-rate and timespec arithmetic preconditions apply.
#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_time_account_bridge(thread_arg: *mut c_void) {
    let thread = thread_arg.cast::<Thread>();
    let proc = unsafe { (*thread).proc };
    let mut updatelock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    let mut ats = MaybeUninit::<crate::abi::TimeSpec>::uninit();
    unsafe {
        process_mcs_writer_lock_bridge(
            core::ptr::addr_of_mut!((*proc).update_lock) as CULong,
            updatelock.as_mut_ptr().cast(),
        );
        process_teardown_tsc_to_ts((*thread).system_tsc, ats.as_mut_ptr());
        process_teardown_ts_add(core::ptr::addr_of_mut!((*(*thread).proc).stime), ats.as_ptr());
        process_teardown_tsc_to_ts((*thread).user_tsc, ats.as_mut_ptr());
        process_teardown_ts_add(core::ptr::addr_of_mut!((*(*thread).proc).utime), ats.as_ptr());
        process_mcs_writer_unlock_bridge(
            core::ptr::addr_of_mut!((*proc).update_lock) as CULong,
            updatelock.as_mut_ptr().cast(),
        );
    }
}

const _: () = {
    assert!(offset_of!(Thread, hash_list) == 0);
    assert!(offset_of!(Thread, tid) == 20);
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, thread_hash) == 32);
    assert!(offset_of!(ThreadHash, lock) == 1216);
    assert!(size_of::<ThreadHash>() == 5888);
    assert!(PROCESS_HASH_SIZE == 73);
};

/// Remove a final-destruction thread from its existing CPU resource-set hash.
/// The caller owns this live thread's teardown and excludes concurrent mutation
/// of its list-membership test until the existing hash lock is acquired. On the
/// linked path, CPU/resource-set/hash storage stays live and CPU binding stable;
/// TID is nonnegative and selects a valid existing bucket. Adjacent list nodes
/// stay valid under the hash writer lock. This is one-time detach: poisoned
/// list entries must not be passed again. No new lock or lifetime policy is added.
#[no_mangle]
pub unsafe extern "C" fn process_destroy_thread_hash_detach_bridge(thread_arg: *mut c_void) {
    let thread = thread_arg.cast::<Thread>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let entry = core::ptr::addr_of_mut!((*thread).hash_list);
        if process_list_is_linked_result(entry) != 0 {
            let resource_set = (*get_this_cpu_local_var()).resource_set;
            let hash = thread_hash((*thread).tid);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
            process_list_detach_result(entry);
            let lock_addr = core::ptr::addr_of_mut!((*(*resource_set).thread_hash).lock)
                .cast::<crate::abi::McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
        }
    }
}

// Preserve the existing optional dynamic-debug event, including its format bytes.
#[used]
#[link_section = "__verbose"]
static mut REPLACE_TID_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"process_replace_tid_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

unsafe extern "C" fn process_replace_tid_log_bridge(
    tid: CInt, thread: *mut c_void, new_tid: CInt,
) {
    let flags = unsafe {
        core::ptr::read_volatile(core::ptr::addr_of!(REPLACE_TID_DEBUG.line_flags)) >> 24
    };
    if flags != 0 {
        unsafe {
            kprintf(
                b"%s: tid %d (thread %p) has been relaced with tid %d\n\0".as_ptr().cast(),
                b"__find_and_replace_tid\0".as_ptr().cast::<i8>(), tid, thread, new_tid,
            );
        }
    }
}

const _: () = {
    assert!(offset_of!(Process, tids) == 256);
    assert!(offset_of!(Process, nr_tids) == 264);
    assert!(offset_of!(Thread, tid) == 20);
    assert!(size_of::<crate::abi::McexecTid>() == 16);
    assert!(offset_of!(crate::abi::McexecTid, tid) == 0);
    assert!(offset_of!(crate::abi::McexecTid, thread) == 8);
};

/// Replace the first slot owned by this live thread while threads_lock is held.
/// The caller keeps process, thread and its positive-count TID array live and
/// excludes concurrent or reentrant slot changes. Null tables are permitted.
/// The existing helper clears the matched pointer before writing the new numeric
/// TID, then logs; it never changes thread.tid or frees/references thread storage.
/// Unmatched entries, slot padding and later duplicate pointers are preserved.
#[no_mangle]
pub unsafe extern "C" fn __find_and_replace_tid(
    proc: *mut Process, thread: *mut Thread, new_tid: CInt,
) {
    let _ = unsafe {
        process_replace_tid_body_result(
            (*proc).tids, (*proc).nr_tids,
            size_of::<crate::abi::McexecTid>() as CULong,
            offset_of!(crate::abi::McexecTid, tid) as CULong,
            offset_of!(crate::abi::McexecTid, thread) as CULong,
            thread.cast(), (*thread).tid, new_tid, Some(process_replace_tid_log_bridge),
        )
    };
}

const _: () = {
    assert!(offset_of!(Process, hash_list) == 0);
    assert!(offset_of!(Process, parent) == 272);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(offset_of!(Process, siblings_list) == 384);
    assert!(offset_of!(Process, pid) == 456);
    assert!(offset_of!(ResourceSet, process_hash) == 24);
    assert!(offset_of!(ProcessHash, lock) == 1216);
    assert!(size_of::<McsRwlockLock>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(PROCESS_HASH_SIZE == 73);
};

/// Detach this final-release process from its resource-set hash under its bucket
/// writer lock. Both arguments and the selected hash/bucket remain live; pid is
/// nonnegative, and the caller excludes changes to this membership check until
/// lock acquisition. The existing list helper poisons the detached entry, which
/// must not be passed again. The cached hash and lock node match the C lifetime.
#[no_mangle]
pub unsafe extern "C" fn process_release_hash_detach_bridge(
    resource_set_arg: *mut c_void, proc_arg: *mut c_void,
) {
    let resource_set = resource_set_arg.cast::<ResourceSet>();
    let proc = proc_arg.cast::<Process>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let entry = core::ptr::addr_of_mut!((*proc).hash_list);
        if process_list_is_linked_result(entry) != 0 {
            let phash = (*resource_set).process_hash;
            let hash = process_hash((*proc).pid);
            let lock_addr = core::ptr::addr_of_mut!((*phash).lock)
                .cast::<McsRwlockLock>().add(hash as usize) as CULong;
            process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
            process_list_detach_result(entry);
            process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
        }
    }
}

/// Detach the final-release process from its parent's child list under the
/// existing parent children writer lock. Process, cached parent, list neighbors
/// and lock storage remain live for both synchronous callbacks; the caller owns
/// this one-time release and supplies initialized list membership. No reference
/// is acquired or freed here, and the parent's lifetime remains the caller's.
#[no_mangle]
pub unsafe extern "C" fn process_release_sibling_detach_bridge(proc_arg: *mut c_void) {
    let proc = proc_arg.cast::<Process>();
    let parent = unsafe { (*proc).parent };
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        let lock_addr = core::ptr::addr_of_mut!((*parent).children_lock) as CULong;
        process_mcs_writer_lock_bridge(lock_addr, lock.as_mut_ptr().cast());
        process_list_detach_result(core::ptr::addr_of_mut!((*proc).siblings_list));
        process_mcs_writer_unlock_bridge(lock_addr, lock.as_mut_ptr().cast());
    }
}

extern "C" {
    fn hugefileobj_cleanup();
    #[cfg(enable_tofu)]
    fn tof_utofu_finalize();
}

const _: () = {
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, pid1) == 320);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Read the current CPU's existing resource-set binding. The CPU-local pointer
/// returned by the existing ABI remains valid for this synchronous read. The
/// caller retains CPU affinity and owns the resource-set lifetime; this callback
/// neither obtains a reference nor interprets a possibly null resource-set value.
#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_bridge() -> *mut c_void {
    unsafe { (*get_this_cpu_local_var()).resource_set.cast() }
}

/// Perform existing last-child cleanup under pid1's children reader lock.
/// The resource set, pid1 process, initialized child-list head and lock storage
/// remain live, and pid1 stays stable throughout synchronous callbacks. The
/// cleanup callees retain their existing concurrency/ownership contracts. The
/// list-empty test is exactly head.next == head; no list mutation/free is added.
#[no_mangle]
pub unsafe extern "C" fn process_release_final_cleanup_bridge(resource_set_arg: *mut c_void) {
    let rset = resource_set_arg.cast::<ResourceSet>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        process_mcs_reader_lock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
        let head = core::ptr::addr_of_mut!((*(*rset).pid1).children_list);
        if (*head).next == head {
            #[cfg(enable_tofu)]
            tof_utofu_finalize();
            hugefileobj_cleanup();
        }
        process_mcs_reader_unlock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
    }
}

unsafe extern "C" {
    static mut process_page_fault_prepare_bounds_debug: crate::debug::Ddebug;
    fn ihk_mc_pt_lookup_pte(
        page_table: *mut c_void, virt: *mut c_void, pgshift: CInt,
        basep: *mut *mut c_void, sizep: *mut SizeT, p2alignp: *mut CInt,
    ) -> *mut CULong;
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_prepare_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep_out: *mut *mut CULong,
    pgaddr_out: *mut *mut c_void,
    pgsize_out: *mut SizeT,
    p2align_out: *mut CInt,
    error_out: *mut CInt,
) -> CInt {
    // Match the original valid borrowed inputs; add no NULL/error policy.
    __ihk_mc_spinlock_lock_noirq(
        &raw mut (*vm).page_table_lock,
    );
    *ptep_out = ihk_mc_pt_lookup_pte(
        (*(*vm).address_space).page_table,
        fault_addr as *mut c_void,
        (*range).pgshift,
        pgaddr_out, pgsize_out, p2align_out,
    );
    if reason & (1 | PF_PATCH) == 0 && !(*ptep_out).is_null()
        && crate::pte_helpers::pte_is_null(*ptep_out) == 0
        && crate::pte_helpers::pte_is_fileoff(*ptep_out, *pgsize_out) == 0
    {
        if crate::pte_helpers::pte_is_present(*ptep_out) == 0 {
            *error_out = -EFAULT;
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):PROT_NONE. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *error_out = 0;
        return 1;
    }
    if reason & 1 != 0 && ((*ptep_out).is_null()
        || crate::pte_helpers::pte_is_present(*ptep_out) == 0)
    {
        crate::x86_memory_helpers::flush_tlb_single(fault_addr);
        *error_out = 0;
        return 1;
    }
    if core::ptr::read_volatile(core::ptr::addr_of!(
        process_page_fault_prepare_bounds_debug.line_flags
    )) >> 24 != 0 {
        let _ = kprintf(
            b"%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\n\0".as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
            *pgaddr_out, (*range).start, (*range).end,
            (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong) as *mut c_void,
        );
    }
    while (*pgaddr_out as CULong) < (*range).start
        || (*range).end < (*pgaddr_out as CULong).wrapping_add(*pgsize_out as CULong)
    {
        *ptep_out = null_mut();
        *error_out = crate::x86_memory_helpers::arch_get_smaller_page_size(
            null_mut(), *pgsize_out, pgsize_out, p2align_out,
        );
        if *error_out != 0 {
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(pte) failed. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, (*range).flag,
                fault_addr, reason, *error_out,
            );
            return 1;
        }
        *pgaddr_out = (fault_addr & !((*pgsize_out as CULong).wrapping_sub(1))) as *mut c_void;
    }
    crate::pte_helpers::arch_adjust_allocate_page_size(
        (*(*vm).address_space).page_table, fault_addr, *ptep_out,
        pgaddr_out, pgsize_out,
    );
    0
}

// Memobj result publication; zeroobj owning-reference policy remains C.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_memobj_get_body_result(
    range: *mut VmRange,
    pgaddr: *mut c_void,
    fault_addr: CULong,
    ptep: *mut CULong,
    pgsize: SizeT,
    p2align: CInt,
    phys_out: *mut CULong,
    memobj_flag_out: *mut CULong,
    error_out: *mut CInt,
) -> CInt {
    *phys_out = NOPHYS;
    if (*range).memobj.is_null() {
        // The original no-memobj path does not overwrite flags or error.
        return 0;
    }
    let off = if ptep.is_null()
        || crate::pte_helpers::pte_is_fileoff(ptep, pgsize) == 0
    {
        ((*range).objoff as CULong)
            .wrapping_add((pgaddr as CULong).wrapping_sub((*range).start)) as OffT
    } else {
        crate::pte_helpers::pte_get_off(ptep, pgsize)
    };
    *error_out = crate::object_helpers::memobj_get_page(
        (*range).memobj.cast::<Memobj>(), off, p2align,
        phys_out, memobj_flag_out, fault_addr,
    );
    // The unchanged C caller owns zeroobj/panic/comparison handling. This
    // predicate preserves every positive/negative provider error unchanged.
    (*error_out != 0) as CInt
}

// Borrowed COW classification only; allocation and cleanup retain their owner.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_classify_body_result(
    range: *mut VmRange,
    reason: CULong,
    page: *mut c_void,
) -> CInt {
    let private_range = ((*range).flag & VR_PRIVATE) != 0;
    let patching_to_rdonly =
        (reason & PF_PATCH) != 0 && ((*range).flag & VR_PROT_WRITE) == 0;
    // Preserve the original OR, including its existing zeroobj behavior.
    // This port does not reinterpret it as the often-expected bitwise AND.
    let devfile_or_hugetlbfs_or_premap = page.is_null()
        && !(*range).memobj.is_null()
        && (((*(*range).memobj.cast::<Memobj>()).flags | 0x20000) == 0);
    // Original C evaluates this Page classification before the final private/
    // patch predicate. Preserve both short-circuit order and borrowed lifetime.
    let regfile_or_shm = !page.is_null()
        && (crate::page_helpers::page_is_in_memobj(
                page.cast::<crate::page_helpers::Page>()) != 0
            || crate::page_helpers::page_is_multi_mapped(
                page.cast::<crate::page_helpers::Page>()) != 0);
    ((private_range || patching_to_rdonly)
        && (devfile_or_hugetlbfs_or_premap || regfile_or_shm)) as CInt
}

// Complete region extension orchestration; existing providers retain ownership.
#[no_mangle]
pub unsafe extern "C" fn process_extend_region_body_result(
    vm: *mut ProcessVm,
    end_allocated: CULong,
    address: CULong,
    mut flag: CULong,
    page_size: SizeT,
    page_shift: CInt,
    page_mask: CULong,
    large_page_size: SizeT,
    large_page_mask: CULong,
    large_page_p2align: CULong,
    page_p2align: CULong,
    large_page_shift: CInt,
    mpol_no_heap: CULong,
    ap_nowait: CULong,
    ap_user: CULong,
    pg_user: CInt,
    file: *const i8,
    alloc_line: CInt,
    free_line: CInt,
    exists_debug: *mut crate::debug::Ddebug,
    alloc_debug: *mut crate::debug::Ddebug,
    success_debug: *mut crate::debug::Ddebug,
) -> CULong {
    let align_size = if (*(*vm).proc.cast::<Process>()).heap_extension > page_size as CULong {
        large_page_size
    } else { page_size };
    let align_mask = if (*(*vm).proc.cast::<Process>()).heap_extension > page_size as CULong {
        large_page_mask
    } else { page_mask };
    let align_p2align = if (*(*vm).proc.cast::<Process>()).heap_extension > page_size as CULong {
        large_page_p2align
    } else { page_p2align };
    let align_shift = if (*(*vm).proc.cast::<Process>()).heap_extension > page_size as CULong {
        large_page_shift
    } else { page_shift };
    let mut new_end_allocated =
        address.wrapping_add((page_size as CULong).wrapping_sub(1)) & page_mask;
    if new_end_allocated.wrapping_sub(end_allocated)
        < (*(*vm).proc.cast::<Process>()).heap_extension
    {
        new_end_allocated = end_allocated
            .wrapping_add((*(*vm).proc.cast::<Process>()).heap_extension)
            .wrapping_add((align_size as CULong).wrapping_sub(1)) & align_mask;
    }
    let range = lookup_process_memory_range(vm, end_allocated, new_end_allocated);
    if !range.is_null() {
        if core::ptr::read_volatile(core::ptr::addr_of!((*exists_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%s: warning: vm_range for extension already exists\n\0".as_ptr().cast(),
                b"extend_process_region\0".as_ptr().cast::<i8>(),
            );
        }
        return end_allocated;
    }
    let len = new_end_allocated.wrapping_sub(end_allocated) as SizeT;
    let npages = (len >> page_shift) as CInt;
    let p = if flag & VR_DEMAND_PAGING != 0 {
        null_mut()
    } else {
        let p = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            npages, align_p2align as CInt,
            ap_nowait | if (*(*vm).proc.cast::<Process>()).mpol_flags & mpol_no_heap == 0 {
                ap_user
            } else { 0 },
            -1, pg_user, end_allocated, file.cast_mut(), alloc_line,
        );
        if p.is_null() {
            if core::ptr::read_volatile(core::ptr::addr_of!((*alloc_debug).line_flags)) >> 24 != 0 {
                let _ = kprintf(
                    b"%s: warning: failed to allocate %d contiguous pages  (bytes: %lu, pgshift: %d), enabling demand paging\n\0".as_ptr().cast(),
                    b"extend_process_region\0".as_ptr().cast::<i8>(),
                    npages, len, align_p2align,
                );
            }
            flag |= VR_DEMAND_PAGING;
        }
        p
    };
    let phys = if p.is_null() { 0 } else {
        crate::x86_memory_helpers::virt_to_phys(p)
    };
    let rc = add_process_memory_range(
        vm, end_allocated, new_end_allocated, phys, flag, null_mut(),
        0, align_shift, null_mut(), null_mut(),
    );
    if rc != 0 {
        // The original error path frees even a NULL pointer from demand paging.
        // Do not infer a new NULL policy or transfer ownership on failure.
        crate::mem_helpers::_ihk_mc_free_pages(
            p, npages, pg_user, file.cast_mut(), free_line,
        );
        return end_allocated;
    }
    // Successful add owns any allocated pages; the caller must not free them.
    if core::ptr::read_volatile(core::ptr::addr_of!((*success_debug).line_flags)) >> 24 != 0 {
        let _ = kprintf(
            b"%s: new_end_allocated: 0x%lx, align_size: %lu, align_mask: %lx\n\0".as_ptr().cast(),
            b"extend_process_region\0".as_ptr().cast::<i8>(),
            new_end_allocated, align_size, align_mask,
        );
    }
    new_end_allocated
}

// COW post-copy RSS/unmap/result handoff under the original caller lock.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_commit_body_result(
    range: *mut VmRange,
    phys_out: *mut CULong,
    pgsize: SizeT,
    virt: *mut c_void,
    page_out: *mut *mut crate::page_helpers::Page,
    rss_add_debug: *mut crate::debug::Ddebug,
    rss_sub_debug: *mut crate::debug::Ddebug,
) {
    // The original caller still holds page_table_lock and owns the fresh copy.
    // The old Page reference is consumed only by the same existing unmap call.
    let old_phys = *phys_out;
    if crate::mem_helpers::rusage_memory_stat_add(
        range, old_phys, pgsize as CULong, pgsize as CInt,
    ) != 0 {
        if core::ptr::read_volatile(core::ptr::addr_of!((*rss_add_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%lx+,%s: COW-source pointed-to by only fileobj, calling memory_stat_rss_add(),pgsize=%ld\n\0".as_ptr().cast(),
                old_phys, b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), pgsize,
            );
        }
    }
    if !(*page_out).is_null() {
        if crate::page_helpers::page_unmap(*page_out) != 0 {
            if core::ptr::read_volatile(core::ptr::addr_of!((*rss_sub_debug).line_flags)) >> 24 != 0 {
                let _ = kprintf(
                    b"%lx-,%s: cow,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                    old_phys, b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), pgsize, pgsize,
                );
            }
            // Read memobj after unmap and its diagnostic, as in original C.
            crate::mem_helpers::rusage_memory_stat_sub(
                (*range).memobj.cast::<Memobj>(), pgsize as CULong, pgsize as CInt,
            );
        }
    }
    // Publish the same new physical result before the Page provider call.
    // Leave the old Page pointer visible until that call returns; no guessed
    // reference release, new-page unmap, free, lock change or success ACK.
    *phys_out = crate::x86_memory_helpers::virt_to_phys(virt);
    *page_out = phys_to_page(*phys_out);
}

// Single-PTE install/accounting/error handback to unchanged caller ownership.
type ProcessFaultSetPteFn = unsafe extern "C" fn(
    *mut c_void, *mut CULong, SizeT, CULong, CULong,
) -> CInt;

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_set_pte_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep: *mut CULong,
    pgsize: SizeT,
    phys: CULong,
    attr: CULong,
    error_out: *mut CInt,
    set_pte: ProcessFaultSetPteFn,
    rss_add_debug: *mut crate::debug::Ddebug,
    rss_skip_debug: *mut crate::debug::Ddebug,
    attr_debug: *mut crate::debug::Ddebug,
) -> CInt {
    // Original non-NULL, non-contiguous PTE branch only. The caller retains
    // its same lock, Page pointer, owning allocation and out: error cleanup.
    if (reason & PF_PATCH) == 0
        && crate::mem_helpers::rusage_memory_stat_add(
            range, phys, pgsize as CULong, pgsize as CInt,
        ) != 0
    {
        if core::ptr::read_volatile(core::ptr::addr_of!((*rss_add_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%lx+,%s: (on-demand paging && first map) || cow,calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n\0".as_ptr().cast(),
                phys, b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), phys, pgsize,
            );
        }
    } else {
        if core::ptr::read_volatile(core::ptr::addr_of!((*rss_skip_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%s: !calling memory_stat_rss_add(),phys=%lx,pgsize=%ld\n\0".as_ptr().cast(),
                b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), phys, pgsize,
            );
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!((*attr_debug).line_flags)) >> 24 != 0 {
        let _ = kprintf(
            b"%s: attr=%x\n\0".as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), attr,
        );
    }
    // Do not cache address_space/page_table before provider/log callbacks.
    // The same existing public set-PTE entry preserves its real diagnostics,
    // panic and selected Rust implementation; this port adds no C bridge.
    *error_out = set_pte((*(*vm).address_space).page_table, ptep, pgsize, phys, attr);
    if *error_out != 0 {
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_pte failed. %d\n\0".as_ptr().cast(),
            vm, (*range).start, (*range).end, (*range).flag,
            fault_addr, reason, *error_out,
        );
        return 1;
    }
    0
}

// Range-install/error and post-install TLB/success handback, same caller owner.
type ProcessFaultSetRangeFn = unsafe extern "C" fn(
    *mut c_void, *mut ProcessVm, *mut c_void, *mut c_void,
    CULong, CULong, CInt, *mut VmRange, CInt,
) -> CInt;

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_set_range_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    pgaddr: *mut c_void,
    pgsize: SizeT,
    phys: CULong,
    attr: CULong,
    error_out: *mut CInt,
    set_range: ProcessFaultSetRangeFn,
) -> CInt {
    // GNU C void-pointer addition is byte addition in the supported ABI.
    // Preserve address-bit wrapping without introducing Rust pointer.add
    // provenance/in-bounds requirements absent from this original mapping API.
    let end = (pgaddr as CULong).wrapping_add(pgsize as CULong) as *mut c_void;
    *error_out = set_range(
        (*(*vm).address_space).page_table, vm, pgaddr, end, phys, attr,
        (*range).pgshift, range, 1,
    );
    if *error_out != 0 {
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):set_range failed. %d\n\0".as_ptr().cast(),
            vm, (*range).start, (*range).end, (*range).flag,
            fault_addr, reason, *error_out,
        );
        return 1;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn process_page_fault_finish_body_result(
    fault_addr: CULong,
    error_out: *mut CInt,
    page_out: *mut *mut crate::page_helpers::Page,
) {
    // Same reviewed Rust/assembly TLB provider. The caller's original success
    // state is published only after it returns, never as a guessed ACK.
    crate::x86_memory_helpers::flush_tlb_single(fault_addr);
    *error_out = 0;
    *page_out = null_mut();
}

// Entire original out: unlock/stray-Page/RSS/diagnostic/return handoff.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_out_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    pgsize_ptr: *const SizeT,
    page: *mut crate::page_helpers::Page,
    error: CInt,
    stray_debug: *mut crate::debug::Ddebug,
    rss_sub_debug: *mut crate::debug::Ddebug,
    return_debug: *mut crate::debug::Ddebug,
) -> CInt {
    // Same unconditional unlock is first. Use the existing C-ABI declaration
    // with abi::IhkSpinlock, not a distinct module-private Rust lock type.
    __ihk_mc_spinlock_unlock_noirq(core::ptr::addr_of_mut!((*vm).page_table_lock));
    // Page==NULL and page_unmap==0 paths never read the caller's possibly
    // uninitialized size, exactly as original C. Merely borrowing its address
    // does not create an initialized-value requirement on those paths.
    if !page.is_null() {
        if core::ptr::read_volatile(core::ptr::addr_of!((*stray_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%s: out,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n\0".as_ptr().cast(),
                b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
                crate::page_helpers::page_to_phys(page),
                (*range).start, (*range).end, (*range).flag, fault_addr, reason,
            );
        }
        if crate::page_helpers::page_unmap(page) != 0 {
            if core::ptr::read_volatile(core::ptr::addr_of!((*rss_sub_debug).line_flags)) >> 24 != 0 {
                let _ = kprintf(
                    b"%lx-,%s: out,calling memory_stat_rss_sub(),size=%ld,pgsize=%ld\n\0".as_ptr().cast(),
                    // Keep the original fresh post-unmap physical read.
                    crate::page_helpers::page_to_phys(page),
                    b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), *pgsize_ptr, *pgsize_ptr,
                );
            }
            // The original obtains memobj only after unmap and its log.
            crate::mem_helpers::rusage_memory_stat_sub(
                (*range).memobj.cast::<Memobj>(), *pgsize_ptr as CULong, *pgsize_ptr as CInt,
            );
        }
    }
    if core::ptr::read_volatile(core::ptr::addr_of!((*return_debug).line_flags)) >> 24 != 0 {
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx): %d\n\0".as_ptr().cast(),
            vm, (*range).start, (*range).end, (*range).flag, fault_addr, reason, error,
        );
    }
    error
}

// Anonymous clear/profile/map handoff; allocation/install ownership unchanged.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_anon_clear_body_result(
    range: *mut VmRange,
    pgaddr: *mut c_void,
    pgsize: SizeT,
    virt: *mut c_void,
    original_page: *mut crate::page_helpers::Page,
    fault_addr: CULong,
    reason: CULong,
    phys_out: *mut CULong,
    profile_enabled: CInt,
    profile_event: CInt,
    clear_debug: *mut crate::debug::Ddebug,
    map_debug: *mut crate::debug::Ddebug,
) {
    // The original successful allocator/caller still owns virt and its size.
    // Do not allocate/free or convert the borrowed Page into an owning ref.
    if core::ptr::read_volatile(core::ptr::addr_of!((*clear_debug).line_flags)) >> 24 != 0 {
        let _ = kprintf(
            b"%s: clearing 0x%lx:%lu\n\0".as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(), pgaddr, pgsize,
        );
    }
    if profile_enabled != 0 {
        crate::profile::profile_event_add(profile_event, pgsize as u64);
    }
    // lib/include/string.h selects memset -> this same existing Rust export.
    // Retain its exact ordered volatile zero writes, not a new C/intrinsic path.
    let _ = crate::string::__inline_memset(virt, 0, pgsize);
    *phys_out = crate::x86_memory_helpers::virt_to_phys(virt);
    if !phys_to_page(*phys_out).is_null() {
        if core::ptr::read_volatile(core::ptr::addr_of!((*map_debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(
                b"%s: NOPHYS,phys=%lx,vmr(%lx-%lx),flag=%x,fa=%lx,reason=%x\n\0".as_ptr().cast(),
                b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
                // Preserve the original diagnostic's preexisting Page input.
                // Do not substitute the newly looked-up Page or physical value.
                crate::page_helpers::page_to_phys(original_page),
                (*range).start, (*range).end, (*range).flag, fault_addr, reason,
            );
        }
        // Original performs a second lookup after its diagnostic, then maps
        // that exact result. Do not cache first lookup or add a NULL guard.
        crate::page_helpers::page_map(phys_to_page(*phys_out));
    }
}

unsafe fn process_copy_pte_debug_enabled(debug: *mut crate::debug::Ddebug) -> bool {
    // SAFETY: Each pointer is an original persistent C descriptor supplied by the
    // selected entry. This raw load preserves the existing dynamic-debug contract.
    unsafe { core::ptr::read_volatile(core::ptr::addr_of!((*debug).line_flags)) >> 24 != 0 }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
unsafe extern "C" {
    static mut process_page_fault_page_state_debug: crate::debug::Ddebug;
}

/// Emit the original successful-PTE Page-state diagnostic.
///
/// # Safety
/// A non-NULL `page` remains borrowed, aligned and live under the unchanged fault
/// owner's page-table/memobj guards for this call. The persistent descriptor has
/// the original dynamic-debug storage/update contract. No reference is acquired
/// or released, and NULL is handled before calling either non-NULL Page provider.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_page_state_log_bridge(
    page: *mut crate::page_helpers::Page,
) {
    // SAFETY: The descriptor is persistent real C ABI data. Preserve the original
    // gate before any Page read, including the NULL/non-NULL provider branches.
    if !unsafe {
        process_copy_pte_debug_enabled(core::ptr::addr_of_mut!(process_page_fault_page_state_debug))
    } {
        return;
    }

    let (in_memobj, count) = if page.is_null() {
        (0, 0)
    } else {
        // SAFETY: The fault owner retains the original borrowed Page lifetime.
        // Both providers read only: mode predicate then one genuine SeqCst count
        // read. C leaves their relative evaluation order unspecified; neither
        // operation mutates the other's input or transfers ownership.
        unsafe {
            (
                crate::page_helpers::page_is_in_memobj(page),
                crate::page_helpers::page_get_count_atomic(page.cast_const()),
            )
        }
    };
    // SAFETY: Original format/function bytes and variadic types are retained,
    // including the original Page pointer argument associated with `%lx`.
    unsafe {
        let _ = kprintf(
            b"%s: non-NULL pte,page=%lx,page_is_in_memobj=%d,page->count=%d\n\0"
                .as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
            page,
            in_memobj,
            count,
        );
    }
}

const _: unsafe extern "C" fn(*mut crate::page_helpers::Page) =
    process_page_fault_page_state_log_bridge;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
unsafe extern "C" {
    static mut process_page_fault_pte_state_debug: crate::debug::Ddebug;
}

/// Emit the original pre-allocation PTE-state diagnostic.
///
/// # Safety
/// A non-NULL PTE is aligned and readable under the unchanged fault owner's
/// page-table guard. `pgsize` is the original lookup/adjustment result. The debug
/// descriptor remains persistent with its original flag-update contract.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_pte_state_log_bridge(
    ptep: *mut CULong,
    pgsize: SizeT,
) {
    // SAFETY: The descriptor is real persistent C data. No PTE load occurs until
    // the same dynamic-debug flag gate passes; NULL preserves both -1 values.
    if !unsafe {
        process_copy_pte_debug_enabled(core::ptr::addr_of_mut!(process_page_fault_pte_state_debug))
    } {
        return;
    }
    let (is_null, is_fileoff) = if ptep.is_null() {
        (-1, -1)
    } else {
        // SAFETY: The original owner still holds its page-table lock. Retain two
        // distinct genuine predicate loads, not a synthesized combined snapshot.
        // Their inputs are unchanged and neither predicate mutates the PTE.
        unsafe {
            (
                crate::pte_helpers::pte_is_null(ptep),
                crate::pte_helpers::pte_is_fileoff(ptep, pgsize),
            )
        }
    };
    // SAFETY: Preserve the original Page-table pointer vararg (including `%lx`),
    // both promoted C ints, format and owning C function string.
    unsafe {
        let _ = kprintf(
            b"%s: ptep=%lx,pte_is_null=%d,pte_is_fileoff=%d\n\0".as_ptr().cast(),
            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
            ptep,
            is_null,
            is_fileoff,
        );
    }
}

const _: unsafe extern "C" fn(*mut CULong, SizeT) = process_page_fault_pte_state_log_bridge;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact architecture enum value; genuine-header witness retains this binding.
const PROCESS_FAULT_PTATTR_DIRTY: CULong = 0x40;

/// Preserve the complete non-COW shared-mapping permission decision.
///
/// # Safety
/// `range` is the original live borrowed VM range under the unchanged fault
/// owner's guards. Call only on the original else branch after COW classification.
/// The return value is the same architecture PT-attribute bitset representation.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_shared_permission_body_result(
    range: *mut VmRange,
    mut attr: CULong,
) -> CULong {
    // SAFETY: The unchanged owner retains the range lifetime. Preserve the
    // original short-circuit order and both field reads; no references escape.
    if unsafe { (*range).flag } & VR_PRIVATE == 0
        && attr & PROCESS_FAULT_PTATTR_DIRTY == 0
        && unsafe { (*range).flag } & VR_STACK == 0
    {
        attr &= !PTATTR_WRITABLE;
    }
    attr
}

const _: unsafe extern "C" fn(*mut VmRange, CULong) -> CULong =
    process_page_fault_shared_permission_body_result;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
unsafe extern "C" {
    static mut process_page_fault_profile_path_debug: crate::debug::Ddebug;
    static mut process_page_fault_entry_debug: crate::debug::Ddebug;
}

/// Preserve the full original profile/path and ordinary entry diagnostics.
///
/// # Safety
/// The original fault caller supplies a live borrowed range/VM and the current
/// CPU/thread context. As in C, the current thread is non-NULL. If the profile
/// log is enabled, the caller keeps any selected memobj/path string live through
/// formatting. These are the original pre-page-table-lock lifetimes; this helper
/// adds no reference, lock, NULL policy, publication or ownership transfer.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_entry_log_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
) {
    // SAFETY: Call the existing current-CPU provider exactly once, before the
    // profile descriptor test, as C does. Preserve the real raw Thread borrow.
    let profiled = unsafe { (*(*get_this_cpu_local_var()).current).profile != 0 };
    if profiled
        && unsafe {
            process_copy_pte_debug_enabled(core::ptr::addr_of_mut!(
                process_page_fault_profile_path_debug
            ))
        }
    {
        // SAFETY: Preserve the original nested short-circuit raw loads and
        // memobj/path/private_data preference. No reference to uninitialized
        // memory is formed and no eager path load occurs before the debug gate.
        let path = unsafe {
            if !(*range).memobj.is_null()
                && !(*(*range).memobj.cast::<Memobj>()).path.is_null()
            {
                (*(*range).memobj.cast::<Memobj>()).path.cast_const()
            } else if !(*range).private_data.is_null() {
                b"XPMEM\0".as_ptr().cast::<i8>()
            } else {
                b"<unknown>\0".as_ptr().cast::<i8>()
            }
        };
        // SAFETY: Selected string stays borrowed/live through the original
        // variadic formatter; function and fault-address types are unchanged.
        unsafe {
            let _ = kprintf(
                b"%s: 0x%lx @ %s\n\0".as_ptr().cast(),
                b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
                fault_addr,
                path,
            );
        }
    }
    // SAFETY: This second descriptor is read after the entire profile event,
    // including its formatter callback, and independently of profile being zero.
    if unsafe {
        process_copy_pte_debug_enabled(core::ptr::addr_of_mut!(process_page_fault_entry_debug))
    } {
        // SAFETY: Preserve fresh post-profile-log range loads and exact original
        // pointer/unsigned-long variadic arguments. Do not cache them above.
        unsafe {
            let _ = kprintf(
                b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx)\n\0"
                    .as_ptr().cast(),
                vm,
                (*range).start,
                (*range).end,
                (*range).flag,
                fault_addr,
                reason,
            );
        }
    }
}

const _: unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong) =
    process_page_fault_entry_log_body_result;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Acquire the borrowed mapping Page and derive attributes in original order.
///
/// # Safety
/// The original fault owner retains the live range/PTE and page-table guard.
/// `page_out` points to writable raw Page-pointer storage owned by that caller;
/// this function initializes it without reading its prior value or making an
/// initialized `&mut` reference. The existing Page lookup may return NULL.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_mapping_state_body_result(
    range: *mut VmRange,
    phys: CULong,
    memobj_flag: CULong,
    reason: CULong,
    ptep: *mut CULong,
    page_out: *mut *mut crate::page_helpers::Page,
) -> CULong {
    // SAFETY: The same genuine physical-Page provider preserves its borrowed
    // return/lifetime semantics. Raw write publishes the original local Page
    // value before attribute conversion, without acquiring or releasing a ref.
    unsafe { core::ptr::write(page_out, phys_to_page(phys)) };
    // SAFETY: Load range flags only after Page lookup returns. The original
    // architecture entry receives the same OR flags, reason and PTE pointer;
    // its existing common-attribute dependency remains explicit provider debt.
    unsafe {
        crate::x86_memory_helpers::arch_vrflag_to_ptattr(
            (*range).flag | memobj_flag,
            reason,
            ptep,
        )
    }
}

const _: unsafe extern "C" fn(
    *mut VmRange, CULong, CULong, CULong, *mut CULong,
    *mut *mut crate::page_helpers::Page,
) -> CULong = process_page_fault_mapping_state_body_result;


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact held anonymous retry body4071bfa0 reused; no allocator reimplementation.
unsafe extern "C" {
    static process_page_fault_anon_alloc_file: *const i8;
    static process_page_fault_anon_alloc_line: CInt;
}

/// Execute the original anonymous allocation/shrink/retry transaction.
///
/// # Safety
/// The unchanged fault owner holds its page-table lock. Range, size/alignment,
/// PTE and address outputs are live initialized raw scalar/pointer storage from
/// the successful prepare stage. `virt_out` is writable original NULL storage;
/// `error_out` may be uninitialized and is read only after this helper writes it.
/// Success transfers exactly the existing allocation pointer to the original
/// clear/map tail; failure owns no allocation and leaves the lock for `out:`.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_anon_allocate_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep_out: *mut *mut CULong,
    pgaddr_out: *mut *mut c_void,
    pgsize_out: *mut SizeT,
    p2align_out: *mut CInt,
    virt_out: *mut *mut c_void,
    error_out: *mut CInt,
) -> CInt {
    // Existing caller owns the page-table lock throughout. No allocation has
    // succeeded on entry; success transfers its virtual pointer to that caller.
    loop {
        let npages = (*pgsize_out / PAGE_SIZE as SizeT) as CInt;
        *virt_out = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            npages, *p2align_out,
            IHK_MC_AP_NOWAIT | if (*range).flag & VR_AP_USER != 0 { 0x001000 } else { 0 },
            -1, 1, fault_addr,
            process_page_fault_anon_alloc_file as *mut i8,
            process_page_fault_anon_alloc_line,
        );
        if !(*virt_out).is_null() {
            return 0;
        }
        // Reload pgshift after the allocator, exactly as in the original.
        if (*range).pgshift == 0 && *pgsize_out != PAGE_SIZE as SizeT {
            *error_out = crate::x86_memory_helpers::arch_get_smaller_page_size(
                null_mut(), *pgsize_out, pgsize_out, p2align_out,
            );
            if *error_out != 0 {
                let _ = kprintf(
                    b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):arch_get_smaller_page_size(anon) failed. %d\n\0".as_ptr().cast(),
                    vm, (*range).start, (*range).end, (*range).flag,
                    fault_addr, reason, *error_out,
                );
                return 1;
            }
            // Unlike the prepare slice, the original clears ptep only AFTER
            // a successful shrink; on shrink failure it preserves old ptep.
            *ptep_out = null_mut();
            *pgaddr_out = (fault_addr & !((*pgsize_out as CULong).wrapping_sub(1))) as *mut c_void;
            continue;
        }
        *error_out = -ENOMEM;
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate new page. %d\n\0".as_ptr().cast(),
            vm, (*range).start, (*range).end, (*range).flag,
            fault_addr, reason, *error_out,
        );
        return 1;
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
unsafe extern "C" {
    static process_page_fault_cow_alloc_file: *const i8;
    static process_page_fault_cow_alloc_line: CInt;
}

/// Allocate the destination for the original dirty COW branch.
///
/// # Safety
/// The caller holds the unchanged fault page-table guard and live VM/range.
/// `page` is the original optional borrowed source Page and is only compared to
/// NULL here. `virt_out` is writable raw pointer storage which may be uninitialized;
/// `error_out` is writable raw signed-int storage which may be uninitialized.
/// Success initializes only the allocation output; failure initializes error and
/// retains source Page/lock ownership for the original `out:` cleanup.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_allocate_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    page: *mut crate::page_helpers::Page,
    pgsize: SizeT,
    p2align: CInt,
    fault_addr: CULong,
    reason: CULong,
    virt_out: *mut *mut c_void,
    error_out: *mut CInt,
) -> CInt {
    if page.is_null() {
        // SAFETY: Exact original warning precedes allocation and has no Page
        // dereference. Preserve its unconditional formatter call/return discard.
        unsafe {
            let _ = kprintf(
                b"%s: WARNING: cow on non-struct-page-managed page\n\0".as_ptr().cast(),
                b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
            );
        }
    }
    // C performs size_t division followed by the allocator's signed-int narrowing.
    let npages = (pgsize / PAGE_SIZE as SizeT) as CInt;
    // SAFETY: Reuse the existing allocator with exactly the original fixed flags,
    // current-owner static tracking identity and arguments. Do not acquire any
    // source-Page reference, or construct &mut to uninitialized output storage.
    let allocated = unsafe {
        crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            npages,
            p2align,
            IHK_MC_AP_NOWAIT,
            -1,
            1,
            fault_addr,
            process_page_fault_cow_alloc_file as *mut i8,
            process_page_fault_cow_alloc_line,
        )
    };
    // SAFETY: Raw initialize the same original C local before its NULL test.
    unsafe { core::ptr::write(virt_out, allocated) };
    if !allocated.is_null() {
        return 0;
    }
    // SAFETY: Failed allocator owns no destination; write original -ENOMEM before
    // logging. Reload range fields after warning/allocator callbacks, as C does.
    unsafe {
        core::ptr::write(error_out, -ENOMEM);
        let _ = kprintf(
            b"page_fault_process_memory_range(%p,%lx-%lx %lx,%lx,%lx):cannot allocate copy page. %d\n\0"
                .as_ptr().cast(),
            vm,
            (*range).start,
            (*range).end,
            (*range).flag,
            fault_addr,
            reason,
            *error_out,
        );
    }
    // Original caller takes goto out with unchanged source Page and lock.
    1
}

const _: unsafe extern "C" fn(
    *mut ProcessVm, *mut VmRange, *mut crate::page_helpers::Page, SizeT,
    CInt, CULong, CULong, *mut *mut c_void, *mut CInt,
) -> CInt = process_page_fault_cow_allocate_body_result;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Copy the COW data after the unchanged original C diagnostic completes.
///
/// # Safety
/// `destination` is the successful destination allocation owned by the unchanged
/// fault caller. The existing physical mapping provider yields a non-NULL source
/// readable for `length` bytes; the destination is writable for that length and
/// the ranges do not overlap. These are the original memcpy valid-input duties.
/// The source mapping/Page and destination stay live under the original owner's
/// guard until the unchanged commit/cleanup tail. No reference or ACK is added.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_copy_body_result(
    destination: *mut c_void,
    source_phys: CULong,
    length: SizeT,
) {
    // SAFETY: Perform a fresh original physical mapping lookup AFTER the C
    // diagnostic/its converter and formatter effects. Do not cache log arguments.
    let source = unsafe { crate::x86_memory_helpers::phys_to_virt(source_phys) };
    // SAFETY: Reuse the existing Rust buffer-copy body with wipe=0. On the
    // original memcpy valid-input domain both pointers are non-NULL, so its
    // validation cannot produce an error; no new error/NULL handling is invented.
    // The same intrinsic copies nonoverlapping bytes without ownership changes.
    let _ = unsafe {
        process_copy_user_pte_buffer_body_result(destination, source.cast_const(), length, 0)
    };
}

const _: unsafe extern "C" fn(*mut c_void, CULong, SizeT) =
    process_page_fault_cow_copy_body_result;

#[no_mangle]
pub unsafe extern "C" fn process_pte_get_phys_bridge(ptep: *mut c_void) -> CULong {
    crate::pte_helpers::pte_get_phys(ptep.cast::<CULong>())
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Complete the initialized fault's install, success publication and out cleanup.
///
/// # Safety
/// The original fault owner holds `vm.page_table_lock` on entry. The live VM,
/// range, initialized mapping arguments and optional borrowed Page satisfy the
/// unchanged set-PTE/range/finish/out providers' contracts. Callbacks are the
/// original synchronous architecture entries; descriptors are the same persistent
/// C objects. No earlier zero-object reference or COW-copy ownership is moved.
/// Every return has passed exactly once through the original out/unlock provider.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_install_finish_body_result(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
    ptep: *mut CULong,
    pgaddr: *mut c_void,
    pgsize: SizeT,
    phys: CULong,
    attr: CULong,
    page: *mut crate::page_helpers::Page,
    set_pte: ProcessFaultSetPteFn,
    set_range: ProcessFaultSetRangeFn,
    rss_add_debug: *mut crate::debug::Ddebug,
    rss_skip_debug: *mut crate::debug::Ddebug,
    attr_debug: *mut crate::debug::Ddebug,
    stray_debug: *mut crate::debug::Ddebug,
    rss_sub_debug: *mut crate::debug::Ddebug,
    return_debug: *mut crate::debug::Ddebug,
) -> CInt {
    // The original local error is uninitialized until an install provider writes
    // it. A raw output slot preserves that lifetime without inventing an &mut to
    // initialized storage or choosing a new default error. Page starts initialized.
    let mut error = MaybeUninit::<CInt>::uninit();
    let mut pending_page = page;
    let go_out;

    if !ptep.is_null() && crate::pte_helpers::pgsize_is_contiguous(pgsize) == 0 {
        // SAFETY: The original non-NULL/non-contiguous branch retains the lock
        // and the borrowed Page while its existing helper publishes error.
        go_out = unsafe {
            process_page_fault_set_pte_body_result(
                vm, range, fault_addr, reason, ptep, pgsize, phys, attr,
                error.as_mut_ptr(), set_pte, rss_add_debug, rss_skip_debug, attr_debug,
            )
        } != 0;
        if !go_out {
            // SAFETY: Successful PTE installation reaches the same gated Page
            // diagnostic before finish. The provider owns its NULL/count rules.
            unsafe { process_page_fault_page_state_log_bridge(pending_page) };
        }
    } else {
        // SAFETY: Preserve the original range branch, including its wrapped
        // end address, current range->pgshift read and downstream RSS policy.
        go_out = unsafe {
            process_page_fault_set_range_body_result(
                vm, range, fault_addr, reason, pgaddr, pgsize, phys, attr,
                error.as_mut_ptr(), set_range,
            )
        } != 0;
    }

    if !go_out {
        // SAFETY: The unchanged provider flushes TLB first, then publishes zero
        // error and a NULL Page. A failed install never reaches this operation.
        unsafe {
            process_page_fault_finish_body_result(
                fault_addr, error.as_mut_ptr(), core::ptr::addr_of_mut!(pending_page),
            );
        }
    }

    // SAFETY: Both install helpers write error on every return; finish rewrites
    // it on success. The original out provider unlocks first, then applies its
    // exact Page/unmap/RSS/log ordering. pgsize is initialized on this tail entry,
    // unlike earlier preparation exits, which still use the original C out label.
    unsafe {
        process_page_fault_out_body_result(
            vm, range, fault_addr, reason, core::ptr::addr_of!(pgsize), pending_page,
            error.assume_init(), stray_debug, rss_sub_debug, return_debug,
        )
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[repr(C)]
struct ProcessExtendRegionEntryConfig {
    page_size: SizeT,
    page_shift: CInt,
    page_mask: CULong,
    large_page_size: SizeT,
    large_page_mask: CULong,
    large_page_p2align: CULong,
    page_p2align: CULong,
    large_page_shift: CInt,
    mpol_no_heap: CULong,
    ap_nowait: CULong,
    ap_user: CULong,
    pg_user: CInt,
    file: *const i8,
    alloc_line: CInt,
    free_line: CInt,
    exists_debug: *mut crate::debug::Ddebug,
    alloc_debug: *mut crate::debug::Ddebug,
    success_debug: *mut crate::debug::Ddebug,
}

unsafe extern "C" {
    static process_extend_region_entry_config: ProcessExtendRegionEntryConfig;
}

/// Enter the existing complete Rust region-extension transaction at its public ABI.
///
/// # Safety
/// `vm` and its proc/address-space/range state satisfy the unchanged complete
/// body's original owner/guard contract. The config's scalar/pointer values are
/// statically initialized and immutable; pointed-to debug flags retain their
/// existing mutable descriptor contract. No reference/lock/ACK policy is added.
#[no_mangle]
pub unsafe extern "C" fn extend_process_region(
    vm: *mut ProcessVm,
    end_allocated: CULong,
    address: CULong,
    flag: CULong,
) -> CULong {
    // SAFETY: Take only the raw address of actual persistent C config data.
    let config = unsafe { core::ptr::addr_of!(process_extend_region_entry_config) };
    // SAFETY: Forward exactly the same arguments, C macro selections, tracking
    // source identities and mutable debug descriptor pointers. Existing Rust
    // allocation/range/map/rollback behavior is reused without a new algorithm.
    unsafe {
        process_extend_region_body_result(
            vm, end_allocated, address, flag,
            (*config).page_size,
            (*config).page_shift,
            (*config).page_mask,
            (*config).large_page_size,
            (*config).large_page_mask,
            (*config).large_page_p2align,
            (*config).page_p2align,
            (*config).large_page_shift,
            (*config).mpol_no_heap,
            (*config).ap_nowait,
            (*config).ap_user,
            (*config).pg_user,
            (*config).file,
            (*config).alloc_line,
            (*config).free_line,
            (*config).exists_debug,
            (*config).alloc_debug,
            (*config).success_debug,
        )
    }
}

const _: unsafe extern "C" fn(*mut ProcessVm, CULong, CULong, CULong) -> CULong =
    extend_process_region;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Select dirty COW allocation, or finish the original clean-COW permission update.
///
/// # Safety
/// `attr` is the fault owner's live initialized architecture enum scalar. Its
/// genuine included C header must match the existing CULong representation and
/// alignment. The caller retains this stack-local object and all Page/lock/ref
/// ownership. No callback, pointer escape or initialized &mut reference is added.
#[no_mangle]
pub unsafe extern "C" fn process_page_fault_cow_dirty_permission_body_result(
    attr: *mut CULong,
) -> CInt {
    // SAFETY: Read only the original initialized local. Preserve the original
    // clean-path second read/update and leave dirty-path storage untouched.
    let dirty = unsafe { core::ptr::read(attr) } & PROCESS_FAULT_PTATTR_DIRTY != 0;
    if !dirty {
        // SAFETY: The same unaliased caller-owned local is writable; no provider
        // call or ownership transition occurs between the original scalar reads.
        unsafe { core::ptr::write(attr, core::ptr::read(attr) & !PTATTR_WRITABLE) };
    }
    dirty as CInt
}

const _: unsafe extern "C" fn(*mut CULong) -> CInt =
    process_page_fault_cow_dirty_permission_body_result;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Config preserves C macro selection and addresses of unchanged static C callbacks.
// The existing183 Rust-adapter batch remains separately unqualified/unselected.
#[repr(C)]
struct ProcessInitStackEntryConfig {
    page_size: CULong,
    page_shift: CInt,
    user_stack_page_mask: CULong,
    user_stack_page_shift: CInt,
    user_stack_prepage_size: CULong,
    stack_alloc_size_override: CULong,
    user_stack_page_p2align: CInt,
    alloc_nowait: CULong,
    alloc_user: CULong,
    mpol_no_stack: CULong,
    user_context_sp_reg: CInt,
    pf_populate: CULong,
    alloc_aligned: ProcessInitStackAllocAlignedFn,
    free_pages: ProcessInitStackFreePagesFn,
    add_range: ProcessInitStackAddRangeFn,
    virt_to_phys: ProcessInitStackVirtToPhysFn,
    attr: ProcessAttrFromVrflagFn,
    pt_set_range: ProcessInitStackPtSetRangeFn,
    hwcap: ProcessInitStackHwcapFn,
    modify_context: ProcessInitStackModifyContextFn,
    log: ProcessInitStackLogFn,
}

unsafe extern "C" {
    static process_init_stack_entry_config: ProcessInitStackEntryConfig;
}

/// Enter the existing complete Rust initial-stack transaction at its public ABI.
///
/// # Safety
/// The original caller supplies the same live thread/program description and
/// argc/argv/envc/env pointer/count domains required by the existing body. This
/// entry creates no new references, locks, initialized output borrows or cleanup
/// policy. Static C configuration and all callback targets remain initialized and live.
/// Callback pointer fields preserve the original local C providers without an
/// extern-name import, visibility change or extra C computation.
#[no_mangle]
pub unsafe extern "C" fn init_process_stack(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
) -> CInt {
    let config = core::ptr::addr_of!(process_init_stack_entry_config);
    // SAFETY: Read only original statically initialized scalar selections and
    // forward the exact arguments/callbacks to the unchanged complete body.
    // Its existing error, allocation, mapping and context ownership is retained.
    unsafe {
        process_init_stack_body_result(
            thread, pn, at_base, argc, argv, envc, env,
            (*config).page_size,
            (*config).page_shift,
            (*config).user_stack_page_mask,
            (*config).user_stack_page_shift,
            (*config).user_stack_prepage_size,
            (*config).stack_alloc_size_override,
            (*config).user_stack_page_p2align,
            (*config).alloc_nowait,
            (*config).alloc_user,
            (*config).mpol_no_stack,
            (*config).user_context_sp_reg,
            (*config).pf_populate,
            Some((*config).alloc_aligned),
            Some((*config).free_pages),
            Some((*config).add_range),
            Some((*config).virt_to_phys),
            Some((*config).attr),
            Some((*config).pt_set_range),
            Some((*config).hwcap),
            Some((*config).modify_context),
            Some((*config).log),
        )
    }
}

const _: unsafe extern "C" fn(
    *mut Thread, *mut ProgramLoadDesc, CULong, CInt, *mut *mut i8, CInt, *mut *mut i8,
) -> CInt = init_process_stack;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Bind the genuine public set-range entry directly; no unqualified stack adapter is grafted.
unsafe extern "C" {
    #[link_name = "ihk_mc_pt_set_range"]
    fn process_copy_set_range_public(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: *mut c_void,
        end: *mut c_void,
        phys: CULong,
        attr: CULong,
        pgshift: CInt,
        range: *mut VmRange,
        flags: CInt,
    ) -> CInt;
}

// Exact private C struct copy_args. The source fixture compares all four offsets,
// size and alignment against the real C owner; no inferred offsets are used here.
#[repr(C)]
struct ProcessCopyPteArgs {
    new_vm: *mut ProcessVm,
    new_vrflag: CULong,
    range: *mut VmRange,
    fault_addr: CLong,
}

// Reuse the already selected identical process_copy_pte_debug_enabled helper.

/// Copy one defined-domain source PTE into the clone's destination address space.
///
/// # Safety
/// The original PTE visitor supplies its live arguments and synchronization guards.
/// On paths that access them, `arg0`, its VM/address-space/range, `src_ptep`, and
/// mapped buffers must satisfy the original C provider contracts for the call.
/// `pgshift` is in the original defined shift domain (0..usize::BITS). Page geometry,
/// flags, source tracking and six descriptors come from the actual selected C entry.
/// No reference, lock, Page ownership, or destination publication is added here.
#[no_mangle]
pub unsafe extern "C" fn process_copy_user_pte_body_result(
    arg0: *mut c_void,
    _src_pt: *mut c_void,
    src_ptep: *mut CULong,
    pgaddr: *mut c_void,
    pgshift: CInt,
    page_size: SizeT,
    page_shift: CInt,
    alloc_nowait: CULong,
    alloc_user: CInt,
    free_kernel: CInt,
    wipe_on_fork: CULong,
    file: *const i8,
    alloc_line: CInt,
    free_line: CInt,
    found_debug: *mut crate::debug::Ddebug,
    size_debug: *mut crate::debug::Ddebug,
    allocated_debug: *mut crate::debug::Ddebug,
    zeroed_debug: *mut crate::debug::Ddebug,
    copied_debug: *mut crate::debug::Ddebug,
    installed_debug: *mut crate::debug::Ddebug,
) -> CInt {
    let args = arg0.cast::<ProcessCopyPteArgs>();
    let mut pgsize = 1usize.wrapping_shl(pgshift as u32);
    let mut pgalign = pgshift.wrapping_sub(page_shift);
    let mut npages = 0;
    let mut virt = null_mut();

    // SAFETY: The unchanged visitor owns all borrowed state and guards through this
    // transaction. Raw accesses retain the original read/publication points; provider
    // calls retain their original ownership. No Rust reference extends an alias.
    unsafe {
        let error = 'transaction: {
            if crate::pte_helpers::pte_is_present(src_ptep) == 0 {
                break 'transaction 0;
            }
            let src_phys = crate::pte_helpers::pte_get_phys(src_ptep);
            if !(*(*args).range).memobj.is_null() && (*args).new_vrflag & VR_PRIVATE == 0 {
                break 'transaction 0;
            }
            let phys;
            let attr;
            if (*args).new_vrflag & VR_REMOTE != 0 {
                phys = src_phys;
                attr = crate::pte_helpers::pte_get_attr(src_ptep, pgsize);
            } else {
                if crate::pte_helpers::pte_is_contiguous(src_ptep) != 0 {
                    if crate::pte_helpers::page_is_contiguous_head(src_ptep, pgsize) == 0 {
                        break 'transaction 0;
                    }
                    let level = crate::pte_helpers::pgsize_to_tbllv(pgsize);
                    pgsize = crate::pte_helpers::tbllv_to_contpgsize(level);
                    pgalign = crate::pte_helpers::tbllv_to_contpgshift(level)
                        .wrapping_sub(page_shift);
                }
                if process_copy_pte_debug_enabled(found_debug) {
                    let _ = kprintf(b"copy_user_pte(): 0x%lx PTE found\n\0".as_ptr().cast(), pgaddr);
                }
                if process_copy_pte_debug_enabled(size_debug) {
                    // Preserve C's original size_t argument even for this %d format.
                    let _ = kprintf(b"copy_user_pte(): page size: %d\n\0".as_ptr().cast(), pgsize);
                }
                // The genuine selected C config supplies PAGE_SIZE > 0. Keep
                // its defined-domain quotient and the original evaluation point.
                // A malformed zero-size config returns the existing EINVAL policy
                // after the same gated logs and before allocation or publication.
                npages = match pgsize.checked_div(page_size) {
                    Some(pages) => pages as CInt,
                    None => break 'transaction -EINVAL,
                };
                virt = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
                    npages, pgalign, alloc_nowait, -1, alloc_user,
                    pgaddr as CULong, file.cast_mut(), alloc_line,
                );
                if virt.is_null() {
                    let _ = kprintf(
                        b"ERROR: copy_user_pte() allocating new page\n\0".as_ptr().cast(),
                    );
                    break 'transaction -ENOMEM;
                }
                phys = crate::x86_memory_helpers::virt_to_phys(virt);
                if process_copy_pte_debug_enabled(allocated_debug) {
                    let _ = kprintf(b"copy_user_pte(): phys page allocated\n\0".as_ptr().cast());
                }
                attr = crate::x86_memory_helpers::arch_vrflag_to_ptattr(
                    (*args).new_vrflag, PF_POPULATE, null_mut(),
                );
                let is_mckernel = crate::mem_helpers::is_mckernel_memory(
                    src_phys, src_phys.wrapping_add(pgsize as CULong),
                );
                let src_lphys;
                let src_kvirt;
                if is_mckernel != 0 {
                    src_lphys = 0;
                    src_kvirt = crate::x86_memory_helpers::phys_to_virt(src_phys);
                } else {
                    src_lphys = crate::x86_setup::ihk_mc_map_memory(
                        null_mut(), src_phys, pgsize as CULong,
                    );
                    src_kvirt = crate::mem_helpers::ihk_mc_map_virtual(src_lphys, 1, attr);
                }
                let copied = process_copy_user_pte_buffer_body_result(
                    virt, src_kvirt, pgsize, ((*args).new_vrflag & wipe_on_fork) as CInt,
                );
                if copied < 0 {
                    if is_mckernel == 0 {
                        crate::mem_helpers::ihk_mc_unmap_virtual(src_kvirt, 1);
                        crate::x86_setup::ihk_mc_unmap_memory(
                            null_mut(), src_lphys, pgsize as CULong,
                        );
                    }
                    break 'transaction -EINVAL;
                }
                if (*args).new_vrflag & wipe_on_fork != 0 {
                    if process_copy_pte_debug_enabled(zeroed_debug) {
                        let _ = kprintf(
                            b"%s(): memset OK\n\0".as_ptr().cast(),
                            b"copy_user_pte\0".as_ptr().cast::<i8>(),
                        );
                    }
                } else if process_copy_pte_debug_enabled(copied_debug) {
                    let _ = kprintf(
                        b"%s(): memcpy OK\n\0".as_ptr().cast(),
                        b"copy_user_pte\0".as_ptr().cast::<i8>(),
                    );
                }
                if is_mckernel == 0 {
                    crate::mem_helpers::ihk_mc_unmap_virtual(src_kvirt, 1);
                    crate::x86_setup::ihk_mc_unmap_memory(
                        null_mut(), src_lphys, pgsize as CULong,
                    );
                }
            }
            // Keep original pgshift even after contiguous-page pgsize adjustment.
            let new_vm = (*args).new_vm;
            let installed = process_copy_set_range_public(
                (*(*new_vm).address_space).page_table, new_vm, pgaddr,
                (pgaddr as CULong).wrapping_add(pgsize as CULong) as *mut c_void,
                phys, attr, pgshift, (*args).range, 0,
            );
            if installed != 0 {
                (*args).fault_addr = pgaddr as CLong;
                break 'transaction installed;
            }
            if process_copy_pte_debug_enabled(installed_debug) {
                let _ = kprintf(b"copy_user_pte(): new PTE set\n\0".as_ptr().cast());
            }
            // Only successful PTE publication transfers this fresh allocation.
            virt = null_mut();
            break 'transaction 0;
        };
        if !virt.is_null() {
            // Retain the original KERNEL free category despite USER allocation.
            crate::mem_helpers::_ihk_mc_free_pages(
                virt, npages, free_kernel, file.cast_mut(), free_line,
            );
        }
        error
    }
}

#[repr(C)]
struct ProcessCopyEntryConfig {
    page_size: SizeT,
    page_shift: CInt,
    nowait: CULong,
    user_category: CInt,
    kernel_category: CInt,
    wipe_on_fork: CULong,
    file: *const i8,
    alloc_line: CInt,
    free_line: CInt,
    visit_flags: CInt,
    found_debug: *mut crate::debug::Ddebug,
    size_debug: *mut crate::debug::Ddebug,
    allocated_debug: *mut crate::debug::Ddebug,
    zeroed_debug: *mut crate::debug::Ddebug,
    copied_debug: *mut crate::debug::Ddebug,
    installed_debug: *mut crate::debug::Ddebug,
}

unsafe extern "C" {
    static process_copy_entry_config: ProcessCopyEntryConfig;
}

/// Reuse the complete copy-PTE transaction at its actual visitor ABI.
///
/// # Safety
/// The original visitor retains live copy_args, VM/range/PTE/buffer and lock
/// contracts. Immutable C config holds exact scalars and six persistent local C
/// descriptors; no descriptor-name import, new reference or ownership ACK exists.
#[no_mangle]
pub unsafe extern "C" fn copy_user_pte(
    arg0: *mut c_void,
    src_pt: *mut c_void,
    src_ptep: *mut CULong,
    pgaddr: *mut c_void,
    pgshift: CInt,
) -> CInt {
    // SAFETY: Preserve every argument/constant/tracking/descriptor identity and
    // the same signed body result. Existing Rust body owns all copy/free/error order.
    unsafe {
        process_copy_user_pte_body_result(
            arg0, src_pt, src_ptep, pgaddr, pgshift,
            process_copy_entry_config.page_size, process_copy_entry_config.page_shift,
            process_copy_entry_config.nowait, process_copy_entry_config.user_category,
            process_copy_entry_config.kernel_category, process_copy_entry_config.wipe_on_fork,
            process_copy_entry_config.file, process_copy_entry_config.alloc_line,
            process_copy_entry_config.free_line,
            process_copy_entry_config.found_debug,
            process_copy_entry_config.size_debug,
            process_copy_entry_config.allocated_debug,
            process_copy_entry_config.zeroed_debug,
            process_copy_entry_config.copied_debug,
            process_copy_entry_config.installed_debug,
        )
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// Preserve the copy-range owner's existing range lookup callback.
///
/// # Safety
/// The caller supplies the same live VM and range-lock contract as the public
/// lookup operation. This adapter introduces no reference or ownership change.
#[no_mangle]
pub unsafe extern "C" fn process_copy_range_lookup_bridge(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
) -> *mut VmRange {
    // SAFETY: The existing owner supplies the unchanged public lookup arguments.
    unsafe { lookup_process_memory_range(vm, start, end) }
}

/// Emit the original copy-range failure diagnostic before the owner unwinds.
///
/// # Safety
/// `range` remains live and readable under the original owner guard for the call.
/// The VM handle and fault address retain their original C variadic types.
#[no_mangle]
pub unsafe extern "C" fn process_copy_user_ranges_log_bridge(
    orgvm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CLong,
) {
    // SAFETY: The original C callback required this live range. Static format bytes
    // and promoted pointer/unsigned-long/signed-long arguments match that callback.
    unsafe {
        let _ = kprintf(
            concat!(
                "ERROR: copy_user_ranges() ",
                "(%p,%lx-%lx %lx,%lx):get pgsize failed\n\0",
            ).as_ptr().cast::<i8>(),
            orgvm, (*range).start, (*range).end, (*range).flag, fault_addr,
        );
    }
}

/// Supply the complete original per-call copy arguments and callbacks to the owner.
///
/// # Safety
/// The two VMs, original PTE visitor callback and supplied constants satisfy the
/// unchanged range-copy provider contract. Its existing locks guard range state.
/// The private argument record is initialized only by that provider and stays live
/// until it returns; no `assume_init`, reference or ownership publication is added.
#[no_mangle]
pub unsafe extern "C" fn process_copy_user_ranges_entry_body_result(
    vm: *mut ProcessVm,
    orgvm: *mut ProcessVm,
    copy_pte_fn: *mut c_void,
    visit_flags: CInt,
    alloc_flags: CULong,
) -> CInt {
    let mut args = MaybeUninit::<ProcessCopyPteArgs>::uninit();
    // SAFETY: This is the same uninitialized private C argument storage. The real
    // owner writes its fields at their actual ABI offsets before invoking the PTE
    // visitor. All passed callbacks retain their exact provider/lock semantics.
    unsafe {
        process_copy_user_ranges_body_result(
            vm, orgvm, size_of::<VmRange>() as CULong, alloc_flags,
            args.as_mut_ptr().cast(),
            offset_of!(ProcessCopyPteArgs, new_vm) as CULong,
            offset_of!(ProcessCopyPteArgs, new_vrflag) as CULong,
            offset_of!(ProcessCopyPteArgs, range) as CULong,
            offset_of!(ProcessCopyPteArgs, fault_addr) as CULong,
            copy_pte_fn, visit_flags,
            Some(process_rw_read_lock_bridge), Some(process_rw_read_unlock_bridge),
            Some(process_copy_range_lookup_bridge), Some(next_process_memory_range),
            Some(process_add_range_alloc_bridge), Some(process_add_range_free_bridge),
            Some(process_add_range_insert_bridge), Some(process_visit_pte_range_bridge),
            Some(process_memory_range_free_bridge), Some(process_copy_user_ranges_log_bridge),
        )
    }
}

const _: ProcessCopyRangeLookupFn = process_copy_range_lookup_bridge;
const _: ProcessCopyUserRangesLogFn = process_copy_user_ranges_log_bridge;

/// Forward the original two-VM range copy through its unchanged complete owner.
///
/// # Safety
/// VM/range locks, visitor argument lifetime and child publication remain the
/// original synchronous provider obligations; no reference or ACK is introduced.
#[no_mangle]
pub unsafe extern "C" fn copy_user_ranges(vm: *mut ProcessVm, orgvm: *mut ProcessVm) -> CInt {
    // SAFETY: Same visitor ABI/function identity, flags and allocation category.
    // The original helper initializes and consumes its private copy arguments.
    unsafe {
        process_copy_user_ranges_entry_body_result(
            vm, orgvm, copy_user_pte as *const () as *mut c_void,
            process_copy_entry_config.visit_flags, process_copy_entry_config.nowait,
        )
    }
}

const _: unsafe extern "C" fn(*mut ProcessVm, *mut ProcessVm) -> CInt = copy_user_ranges;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
type ProcessCloneRangesFn = unsafe extern "C" fn(*mut ProcessVm, *mut ProcessVm) -> CInt;

// Private C constant-data ABI; the fixture compares every field's actual layout.
#[repr(C)]
struct ProcessCloneConfig {
    stack_pages: CInt,
    page_size: SizeT,
    page_align: CInt,
    nowait: CULong,
    kernel: CInt,
    ss_disable: CInt,
    sp_reg: CInt,
    pc_reg: CInt,
    file: *const i8,
    lines: [CInt; 5],
    debug: [*mut crate::debug::Ddebug; 5],
    modify_context: ProcessInitStackModifyContextFn,
    copy_ranges: ProcessCloneRangesFn,
}

unsafe extern "C" {
    #[link_name = "ihk_mc_init_user_process"]
    fn process_clone_init_user_process_public(
        context: *mut crate::abi::X86KernelContext,
        user_context: *mut *mut crate::abi::X86UserContext,
        stack_top: *mut c_void,
        pc: CULong,
        sp: CULong,
    );
    #[link_name = "copy_fp_regs"]
    fn process_clone_copy_fp_regs_public(origin: *mut Thread, thread: *mut Thread) -> CInt;
}

// Values retain the exact original fall-through order of the seven cleanup labels.
#[repr(u8)]
enum ProcessCloneCleanup {
    Thread = 0,
    Fp = 1,
    Process = 2,
    AddressSpace = 3,
    Vm = 4,
    CommandLine = 5,
    Mckfd = 6,
}

unsafe fn process_clone_fixed_log(debug: *mut crate::debug::Ddebug, format: *const i8) {
    // SAFETY: The caller supplies the original persistent descriptor and exact
    // terminated constant format. No ownership or reference escapes this call.
    unsafe {
        if core::ptr::read_volatile(core::ptr::addr_of!((*debug).line_flags)) >> 24 != 0 {
            let _ = kprintf(format);
        }
    }
}

/// Construct the original clone/fork thread transaction and its exact failure unwind.
///
/// # Safety
/// `org` and all reached origin state are live under the original clone caller's
/// ownership and guards. `config` is the matching immutable C static data, including
/// valid callback pointers, five tracking lines and five persistent descriptors.
/// Existing providers retain allocation, locking and reference semantics. This body
/// adds no release to a failure path, including the original shared-VM/sigcommon paths.
#[no_mangle]
pub unsafe extern "C" fn process_clone_thread_body_result(
    org: *mut Thread,
    pc: CULong,
    sp: CULong,
    clone_flags: CInt,
    config: *const ProcessCloneConfig,
) -> *mut Thread {
    let termsig = clone_flags & 0xff;
    let mut proc: *mut Process = null_mut();
    let mut asp: *mut AddressSpace = null_mut();

    // SAFETY: This is one original owner transaction. Every pointer access is tied
    // to its original successful allocation/provider step or the live origin.
    // Raw address expressions avoid introducing aliases or extending lock lifetimes.
    unsafe {
        let v = get_this_cpu_local_var();
        let thread = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            (*config).stack_pages, (*config).page_align, (*config).nowait, -1,
            (*config).kernel, CULong::MAX, (*config).file.cast_mut(), (*config).lines[0],
        ).cast::<Thread>();
        if thread.is_null() {
            return null_mut();
        }
        let cleanup = 'construct: {
            if process_thread_alloc_init_body_result(
                thread.cast(), size_of::<Thread>() as CULong,
                offset_of!(Thread, refcount) as CULong,
                offset_of!(Thread, hash_list) as CULong,
                offset_of!(Thread, siblings_list) as CULong, None,
            ) < 0 {
                break 'construct ProcessCloneCleanup::Thread;
            }
            if process_clone_thread_base_state_body_result(
                thread.cast(), org.cast(), offset_of!(Thread, cpu_set) as CULong,
                size_of::<CpuSet>() as CULong, offset_of!(Thread, in_kernel) as CULong,
            ) < 0 {
                break 'construct ProcessCloneCleanup::Thread;
            }
            process_clone_init_user_process_public(
                core::ptr::addr_of_mut!((*thread).ctx),
                core::ptr::addr_of_mut!((*thread).uctx),
                thread.cast::<u8>().add(
                    ((*config).stack_pages as SizeT).wrapping_mul((*config).page_size),
                ).cast(),
                pc, sp,
            );
            if save_fp_regs(org.cast()) != 0 {
                break 'construct ProcessCloneCleanup::Thread;
            }
            if process_clone_copy_fp_regs_public(org, thread) != 0 {
                break 'construct ProcessCloneCleanup::Fp;
            }
            crate::x86_cpu_helpers::arch_clone_thread(org.cast(), pc, sp, thread.cast());
            if process_clone_user_context_body_result(
                thread.cast(), org.cast(), offset_of!(Thread, uctx) as CULong,
                size_of::<crate::abi::X86UserContext>() as CULong,
                (*config).sp_reg, sp, (*config).pc_reg, pc, Some((*config).modify_context),
            ) < 0 {
                break 'construct ProcessCloneCleanup::Fp;
            }
            if process_clone_thread_sched_state_body_result(
                thread.cast(), org.cast(), offset_of!(Thread, sched_policy) as CULong,
                (offset_of!(Thread, sched_param)
                    + offset_of!(crate::abi::SchedParam, sched_priority)) as CULong,
            ) < 0 {
                break 'construct ProcessCloneCleanup::Fp;
            }
            if process_clone_shares_vm_result(clone_flags) != 0 {
                proc = (*org).proc;
                if process_clone_thread_shared_vm_state_body_result(
                    thread.cast(), proc.cast(), (*org).vm.cast(),
                    offset_of!(Thread, vm) as CULong, offset_of!(Thread, proc) as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Fp;
                }
                if process_thread_sigstack_disable_body_result(
                    thread.cast(), offset_of!(Thread, sigstack) as CULong,
                    offset_of!(SigStack, ss_sp) as CULong,
                    offset_of!(SigStack, ss_flags) as CULong,
                    offset_of!(SigStack, ss_size) as CULong, (*config).ss_disable,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Fp;
                }
            } else {
                proc = crate::mem_helpers::kmalloc_tracked(
                    size_of::<Process>() as CInt, (*config).nowait,
                    (*config).file.cast_mut(), (*config).lines[1],
                ).cast();
                if proc.is_null() {
                    break 'construct ProcessCloneCleanup::Fp;
                }
                if process_allocated_object_zero_body_result(
                    proc.cast(), size_of::<Process>() as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Process;
                }
                init_process(proc, (*org).proc);
                #[cfg(enable_profile)]
                if process_clone_fork_profile_body_result(
                    proc.cast(), (*org).proc.cast(), offset_of!(Process, profile) as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Process;
                }
                if process_clone_fork_process_termsig_body_result(
                    proc.cast(), offset_of!(Process, termsig) as CULong, termsig,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Process;
                }
                // Retain the second, fresh CPU-local lookup in the original C body.
                asp = create_address_space((*get_this_cpu_local_var()).resource_set, 1);
                if asp.is_null() {
                    break 'construct ProcessCloneCleanup::Process;
                }
                (*proc).vm = crate::mem_helpers::kmalloc_tracked(
                    size_of::<ProcessVm>() as CInt, (*config).nowait,
                    (*config).file.cast_mut(), (*config).lines[2],
                ).cast();
                if (*proc).vm.is_null() {
                    break 'construct ProcessCloneCleanup::AddressSpace;
                }
                if process_allocated_object_zero_body_result(
                    (*proc).vm.cast(), size_of::<ProcessVm>() as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::Vm;
                }
                if process_clone_fork_saved_cmdline_body_result(
                    proc.cast(), (*org).proc.cast(),
                    offset_of!(Process, saved_cmdline_len) as CULong,
                    offset_of!(Process, saved_cmdline) as CULong, (*config).nowait,
                    Some(process_alloc_bridge),
                ) != 0 {
                    break 'construct ProcessCloneCleanup::Vm;
                }
                process_clone_fixed_log(
                    (*config).debug[0], b"fork(): init_process_vm()\n\0".as_ptr().cast(),
                );
                if init_process_vm(proc, asp, (*proc).vm) != 0 {
                    break 'construct ProcessCloneCleanup::CommandLine;
                }
                if process_clone_fork_vm_policy_body_result(
                    (*proc).vm.cast(), (*org).vm.cast(),
                    offset_of!(ProcessVm, numa_mask) as CULong,
                    size_of::<[CULong; PROCESS_NUMA_MASK_BITS / 64]>() as CULong,
                    offset_of!(ProcessVm, numa_mem_policy) as CULong,
                    offset_of!(ProcessVm, region) as CULong,
                    size_of::<crate::abi::VmRegions>() as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::CommandLine;
                }
                if process_create_thread_link_state_body_result(
                    thread.cast(), proc.cast(), (*proc).vm.cast(),
                    offset_of!(Thread, vm) as CULong, offset_of!(Thread, proc) as CULong,
                    offset_of!(Process, vm) as CULong, offset_of!(Process, main_thread) as CULong,
                ) < 0 {
                    break 'construct ProcessCloneCleanup::CommandLine;
                }
                process_clone_fixed_log(
                    (*config).debug[1], b"fork(): copy_user_ranges()\n\0".as_ptr().cast(),
                );
                if process_clone_on_fork_vm_body_result(
                    v.cast(), offset_of!(CpuLocalVar, on_fork_vm) as CULong, (*proc).vm.cast(),
                ) < 0 {
                    break 'construct ProcessCloneCleanup::CommandLine;
                }
                if ((*config).copy_ranges)((*proc).vm, (*org).vm) != 0 {
                    let _ = process_clone_on_fork_vm_body_result(
                        v.cast(), offset_of!(CpuLocalVar, on_fork_vm) as CULong, null_mut(),
                    );
                    break 'construct ProcessCloneCleanup::CommandLine;
                }
                let _ = process_clone_on_fork_vm_body_result(
                    v.cast(), offset_of!(CpuLocalVar, on_fork_vm) as CULong, null_mut(),
                );
                let lock = core::ptr::addr_of_mut!((*proc).mckfd_lock) as CULong;
                let irqstate = process_spin_lock_result(lock, Some(process_spin_lock_bridge));
                let mut cur = (*(*org).proc).mckfd.cast::<Mckfd>();
                while !cur.is_null() {
                    let mckfd = crate::mem_helpers::kmalloc_tracked(
                        size_of::<Mckfd>() as CInt, (*config).nowait,
                        (*config).file.cast_mut(), (*config).lines[3],
                    ).cast::<Mckfd>();
                    if mckfd.is_null() {
                        let _ = process_spin_unlock_result(
                            lock, irqstate, Some(process_spin_unlock_bridge),
                        );
                        break 'construct ProcessCloneCleanup::Mckfd;
                    }
                    if process_mckfd_copy_body_result(
                        mckfd.cast(), cur.cast(), size_of::<Mckfd>() as CULong,
                    ) < 0 {
                        crate::mem_helpers::kfree_tracked(
                            mckfd.cast(), (*config).file.cast_mut(), (*config).lines[4],
                        );
                        let _ = process_spin_unlock_result(
                            lock, irqstate, Some(process_spin_unlock_bridge),
                        );
                        break 'construct ProcessCloneCleanup::Mckfd;
                    }
                    let _ = process_mckfd_push_head_result(
                        core::ptr::addr_of_mut!((*proc).mckfd), mckfd.cast(),
                    );
                    if process_mckfd_should_dup_result((*mckfd).dup_cb as CULong) != 0 {
                        let callback: ProcessMckfdDupFn = core::mem::transmute((*mckfd).dup_cb);
                        let _ = process_mckfd_dup_result(mckfd.cast(), Some(callback));
                    }
                    cur = (*cur).next;
                }
                let _ = process_spin_unlock_result(lock, irqstate, Some(process_spin_unlock_bridge));
                let _ = process_clone_copy_vm_thread_state_result(
                    (*thread).vm.cast(), (*org).vm.cast(),
                    offset_of!(ProcessVm, vdso_addr) as CULong,
                    offset_of!(ProcessVm, vvar_addr) as CULong, thread.cast(), org.cast(),
                    offset_of!(Thread, sigstack) as CULong, size_of::<SigStack>(),
                );
                process_clone_fixed_log(
                    (*config).debug[2], b"fork(): copy_user_ranges() OK\n\0".as_ptr().cast(),
                );
            }
            // From here, fork failures drain fork resources; CLONE_VM failures
            // deliberately enter the original FP-only path without invented unrefs.
            if process_clone_shares_sighand_result(clone_flags) != 0 {
                if process_clone_sigcommon_share_body_result(
                    thread.cast(), org.cast(), offset_of!(Thread, sigcommon) as CULong,
                    offset_of!(SigCommon, use_) as CULong, None,
                ) < 0 {
                    break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                        ProcessCloneCleanup::Fp
                    } else { ProcessCloneCleanup::Mckfd };
                }
            } else {
                process_clone_fixed_log(
                    (*config).debug[3], b"fork(): sigcommon\n\0".as_ptr().cast(),
                );
                (*thread).sigcommon = process_sigcommon_alloc_init_body_result(
                    size_of::<SigCommon>() as CULong, (*config).nowait,
                    offset_of!(SigCommon, use_) as CULong, offset_of!(SigCommon, lock) as CULong,
                    offset_of!(SigCommon, sigpending) as CULong,
                    Some(process_alloc_bridge), Some(process_optional_free_bridge), None,
                    Some(process_rwlock_init_bridge),
                );
                if (*thread).sigcommon.is_null() {
                    break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                        ProcessCloneCleanup::Fp
                    } else { ProcessCloneCleanup::Mckfd };
                }
                process_clone_fixed_log(
                    (*config).debug[4], b"fork(): sigshared\n\0".as_ptr().cast(),
                );
                if process_clone_sigcommon_action_copy_body_result(
                    (*thread).sigcommon, (*org).sigcommon,
                    offset_of!(SigCommon, action) as CULong,
                    size_of::<[crate::abi::KSigAction; 64]>() as CULong,
                ) < 0 {
                    break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                        ProcessCloneCleanup::Fp
                    } else { ProcessCloneCleanup::Mckfd };
                }
            }
            let _ = process_thread_sigpending_init_body_result(
                thread.cast(), offset_of!(Thread, sigpendinglock) as CULong,
                offset_of!(Thread, sigpending) as CULong, Some(process_rwlock_init_bridge),
            );
            if process_thread_sigmask_copy_body_result(
                thread.cast(), org.cast(), offset_of!(Thread, sigmask) as CULong,
                size_of::<crate::abi::SigSet>() as CULong,
            ) < 0 {
                break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                    ProcessCloneCleanup::Fp
                } else { ProcessCloneCleanup::Mckfd };
            }
            if process_thread_spin_sleep_init_body_result(
                thread.cast(), offset_of!(Thread, spin_sleep_lock) as CULong,
                offset_of!(Thread, spin_sleep) as CULong, Some(process_spin_init_bridge),
            ) < 0 {
                break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                    ProcessCloneCleanup::Fp
                } else { ProcessCloneCleanup::Mckfd };
            }
            #[cfg(enable_profile)]
            if process_clone_profile_state_body_result(
                thread.cast(), org.cast(), proc.cast(), offset_of!(Thread, profile) as CULong,
                offset_of!(Process, profile) as CULong,
            ) < 0 {
                break 'construct if process_clone_shares_vm_result(clone_flags) != 0 {
                    ProcessCloneCleanup::Fp
                } else { ProcessCloneCleanup::Mckfd };
            }
            return thread;
        } as u8;

        if cleanup >= ProcessCloneCleanup::Mckfd as u8 {
            let lock = core::ptr::addr_of_mut!((*proc).mckfd_lock) as CULong;
            let irqstate = process_spin_lock_result(lock, Some(process_spin_lock_bridge));
            let _ = process_mckfd_drain_free_result(
                core::ptr::addr_of_mut!((*proc).mckfd), offset_of!(Mckfd, next) as CULong,
                Some(process_mckfd_free_bridge),
            );
            let _ = process_spin_unlock_result(lock, irqstate, Some(process_spin_unlock_bridge));
            let _ = process_vm_action_result((*proc).vm.cast(), Some(process_free_all_ranges_bridge));
        }
        if cleanup >= ProcessCloneCleanup::CommandLine as u8 {
            let _ = process_free_callback_result(
                (*proc).saved_cmdline.cast(), Some(process_optional_free_bridge),
            );
        }
        if cleanup >= ProcessCloneCleanup::Vm as u8 {
            let _ = process_free_callback_result((*proc).vm.cast(), Some(process_optional_free_bridge));
        }
        if cleanup >= ProcessCloneCleanup::AddressSpace as u8 {
            let _ = process_pt_destroy_result((*asp).page_table, Some(process_pt_destroy_bridge));
            let _ = process_free_callback_result(asp.cast(), Some(process_optional_free_bridge));
        }
        if cleanup >= ProcessCloneCleanup::Process as u8 {
            let _ = process_free_callback_result(proc.cast(), Some(process_optional_free_bridge));
        }
        if cleanup >= ProcessCloneCleanup::Fp as u8 {
            let _ = process_release_fp_regs_result(thread.cast(), Some(release_fp_regs));
        }
        let _ = process_thread_action_result(thread.cast(), Some(process_free_thread_pages_bridge));
        null_mut()
    }
}

unsafe extern "C" {
    static process_clone_config: ProcessCloneConfig;
}

/// Use the unchanged complete Rust clone owner through the actual public ABI.
///
/// # Safety
/// Original source-thread, VM, allocator, shared-reference, lock and publication
/// contracts apply. Only the existing owner chooses cleanup; no ACK or release is
/// manufactured by this entry, including shared-VM failure paths.
#[no_mangle]
pub unsafe extern "C" fn clone_thread(
    org: *mut Thread,
    pc: CULong,
    sp: CULong,
    clone_flags: CInt,
) -> *mut Thread {
    // SAFETY: Exact original arguments and same config object address/body result.
    // No additional validation, initialization, reference, ACK or cleanup surrounds it.
    unsafe {
        process_clone_thread_body_result(
            org, pc, sp, clone_flags, core::ptr::addr_of!(process_clone_config),
        )
    }
}

const _: unsafe extern "C" fn(*mut Thread, CULong, CULong, CInt) -> *mut Thread = clone_thread;


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Reuse the existing eight-adapter183 bodies against the accepted supported-owner source.
unsafe extern "C" {
    static process_init_stack_alloc_file: *const i8;
    static process_init_stack_alloc_line: CInt;
    static process_init_stack_free_file: *const i8;
    static process_init_stack_free_line: CInt;
    static process_init_stack_user_category: CInt;
}

/// Forward the original tracked initial-stack allocation.
///
/// # Safety
/// The caller retains the original allocator admission, page geometry and hint contract.
/// The C tracking data has translation-unit lifetime and is immutable after initialization.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_alloc_aligned_bridge(
    npages: CInt,
    p2align: CInt,
    flags: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    // SAFETY: Preserve every original argument and the actual C category/file/line.
    // The existing allocator owns admission and any newly returned allocation.
    unsafe {
        crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
            npages, p2align, flags, -1, process_init_stack_user_category, virt_addr,
            process_init_stack_alloc_file.cast_mut(), process_init_stack_alloc_line,
        )
    }
}

/// Forward the original unconditional initial-stack free operation.
///
/// # Safety
/// The caller supplies the same owned allocation and page count as the original callback.
/// Null and unusual counts retain the existing provider policy; no new policy is added.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_free_pages_bridge(addr: *mut c_void, npages: CInt) {
    // SAFETY: This is the original synchronous ownership transfer to the free provider.
    // Immutable tracking strings remain live; the provider does not mutate their bytes.
    unsafe {
        crate::mem_helpers::_ihk_mc_free_pages(
            addr, npages, process_init_stack_user_category,
            process_init_stack_free_file.cast_mut(), process_init_stack_free_line,
        );
    }
}

/// Add the original initial-stack range and publish its provider result.
///
/// # Safety
/// The VM, range geometry and synchronization satisfy add_process_memory_range's contract.
/// A non-null rangep is writable for one pointer through this synchronous call.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_add_range_bridge(
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut VmRange,
) -> CInt {
    let mut range: *mut VmRange = null_mut();
    // SAFETY: The initialized local output stays live through the provider call.
    // Preserve output publication even when the provider returns an error.
    unsafe {
        let rc = add_process_memory_range(
            vm, start, end, phys, flag, null_mut(), 0, pgshift, null_mut(), &mut range,
        );
        if !rangep.is_null() {
            *rangep = range;
        }
        rc
    }
}

/// Translate the same borrowed initial-stack allocation address.
///
/// # Safety
/// addr satisfies the existing supported x86 translation provider's contract.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_virt_to_phys_bridge(addr: *mut c_void) -> CULong {
    // SAFETY: Same address, provider and returned physical-address ABI as the C callback.
    unsafe { crate::x86_memory_helpers::virt_to_phys(addr) }
}

/// Derive the original stack PTE attributes.
///
/// # Safety
/// ptep retains the original borrowed PTE validity/locking contract for this call.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_attr_bridge(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
) -> CULong {
    // SAFETY: Same flags, fault and raw PTE address; no reference or ownership is created.
    unsafe { crate::x86_memory_helpers::arch_vrflag_to_ptattr(flag, fault, ptep.cast()) }
}

/// Install the original initial-stack page-table range.
///
/// # Safety
/// All handles, range geometry and lock ownership satisfy the existing public set-range ABI.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_pt_set_range_bridge(
    page_table: *mut c_void,
    vm: *mut ProcessVm,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut VmRange,
    flags: CInt,
) -> CInt {
    // SAFETY: Reuse the already qualified alias for the exact public ihk_mc_pt_set_range.
    // Pointer casts, argument order, return value and provider ownership remain unchanged.
    unsafe {
        process_copy_set_range_public(
            page_table, vm, start as *mut c_void, end as *mut c_void,
            phys, attr, pgshift, range, flags,
        )
    }
}

/// Return the supported x86 architecture's exact hardware-capability value.
///
/// # Safety
/// This symbol is selected for the held x86 profile, whose actual hwcap.h returns zero.
#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_hwcap_bridge() -> CULong {
    0
}

/// Mutate the original borrowed user context through its existing Rust provider.
///
/// # Safety
/// uctx retains the original context validity, alignment and exclusive write contract.
/// Null and unknown-register behavior remain the existing provider's responsibility.
#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_modify_context_bridge(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
) {
    // SAFETY: This cast creates no reference or ownership; the provider performs
    // the same volatile context updates under the original caller's ownership.
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_modify_user_context(
            uctx.cast::<crate::abi::X86UserContext>(), reg, value,
        );
    }
}

const _: ProcessInitStackAllocAlignedFn = process_init_stack_alloc_aligned_bridge;
const _: ProcessInitStackFreePagesFn = process_init_stack_free_pages_bridge;
const _: ProcessInitStackAddRangeFn = process_init_stack_add_range_bridge;
const _: ProcessInitStackVirtToPhysFn = process_init_stack_virt_to_phys_bridge;
const _: ProcessAttrFromVrflagFn = process_init_stack_attr_bridge;
const _: ProcessInitStackPtSetRangeFn = process_init_stack_pt_set_range_bridge;
#[cfg(target_arch = "x86_64")]
const _: ProcessInitStackHwcapFn = process_init_stack_hwcap_bridge;
#[cfg(target_arch = "x86_64")]
const _: ProcessInitStackModifyContextFn = process_init_stack_modify_context_bridge;


unsafe extern "C" {
    static mut process_init_stack_log_size_debug: crate::debug::Ddebug;
    static mut process_init_stack_log_ap_user_debug: crate::debug::Ddebug;
}

/// Emit the existing initial-stack diagnostic event with its exact C varargs ABI.
///
/// # Safety
/// Non-null `args` must be readable and aligned for twelve `CULong` values for
/// this call, under the existing stack caller's ownership. The two C descriptors
/// have translation-unit lifetime and the existing dynamic-debug update contract.
#[no_mangle]
pub unsafe extern "C" fn process_init_stack_log_bridge(event: CInt, args: *const CULong) {
    // SAFETY: The callback's twelve-word input contract covers every original C
    // declaration, in order. Null selects zero without dereferencing or borrowing.
    let (arg0, arg1, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9, arg10, _arg11) = unsafe {
        if args.is_null() {
            (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        } else {
            (
                args.read(), args.add(1).read(), args.add(2).read(), args.add(3).read(),
                args.add(4).read(), args.add(5).read(), args.add(6).read(), args.add(7).read(),
                args.add(8).read(), args.add(9).read(), args.add(10).read(), args.add(11).read(),
            )
        }
    };
    let function = b"init_process_stack\0".as_ptr().cast::<i8>();

    // SAFETY: Format strings are static, terminated, and retain the exact original
    // promoted int/unsigned-long/pointer argument types and order. Descriptor raw
    // pointers refer to live C objects; reads create no references or ownership.
    unsafe {
        match event {
            PROCESS_INIT_STACK_LOG_SIZE => {
                let flags = core::ptr::read_volatile(core::ptr::addr_of!(
                    process_init_stack_log_size_debug.line_flags
                )) >> 24;
                if flags != 0 {
                    let _ = kprintf(
                        concat!(
                            "%s: stack_premap: %lu, rlim_cur: %lu, minsz: %lu, ",
                            "size: %lu, maxsz: %lx\n\0",
                        ).as_ptr().cast::<i8>(),
                        function, arg0, arg1, arg2, arg3, arg4,
                    );
                }
            }
            PROCESS_INIT_STACK_LOG_AP_USER => {
                let flags = core::ptr::read_volatile(core::ptr::addr_of!(
                    process_init_stack_log_ap_user_debug.line_flags
                )) >> 24;
                if flags != 0 {
                    let suffix = if arg2 != 0 {
                        b"(IHK_MC_AP_USER)\0".as_ptr().cast::<i8>()
                    } else {
                        b"\0".as_ptr().cast::<i8>()
                    };
                    let _ = kprintf(
                        b"%s: max size: %lu, mapped size: %lu %s\n\0".as_ptr().cast::<i8>(),
                        function, arg0, arg1, suffix,
                    );
                }
            }
            PROCESS_INIT_STACK_LOG_ALLOC_FAILED => {
                let _ = kprintf(
                    b"%s: error: couldn't allocate initial stack\n\0".as_ptr().cast::<i8>(),
                    function,
                );
            }
            PROCESS_INIT_STACK_LOG_ADD_FAILED => {
                let _ = kprintf(
                    b"%s: error addding process memory range: %d\n\0".as_ptr().cast::<i8>(),
                    function, arg0 as CInt,
                );
            }
            PROCESS_INIT_STACK_LOG_PT_FAILED => {
                let _ = kprintf(
                    b"init_process_stack:set range %lx-%lx %lx failed. %d\n\0"
                        .as_ptr().cast::<i8>(),
                    arg0, arg1, arg2, arg3 as CInt,
                );
            }
            PROCESS_INIT_STACK_LOG_AUXV => {
                let _ = kprintf(
                    concat!(
                        "mcexec_v10: auxv pid=%d tid=%d entry=0x%lx base=0x%lx phdr=0x%lx ",
                        "vdso=0x%lx pagesz=%lu at_random=0x%lx stack_top=0x%lx argc=%d envc=%d\n\0",
                    ).as_ptr().cast::<i8>(),
                    arg0 as CInt, arg1 as CInt, arg2, arg3, arg4, arg5, arg6, arg7, arg8,
                    arg9 as CInt, arg10 as CInt,
                );
            }
            PROCESS_INIT_STACK_LOG_SIZE_MISMATCH => {
                let _ = kprintf(
                    concat!(
                        "%s: WARNING: stack_populated_size mismatch (is AUXV_LEN up-to-date?): ",
                        "&p[s_ind]: %lu, computed: %lu\n\0",
                    ).as_ptr().cast::<i8>(),
                    function, arg0, arg1,
                );
            }
            PROCESS_INIT_STACK_LOG_ALIGN_MISMATCH => {
                let _ = kprintf(
                    b"%s: WARNING: stack alignment mismatch\n\0".as_ptr().cast::<i8>(), function,
                );
            }
            PROCESS_INIT_STACK_LOG_INITIAL => {
                let _ = kprintf(
                    concat!(
                        "mcexec_v10: initial_stack pid=%d tid=%d sp=0x%lx argc_slot=%lu ",
                        "argv0_slot=0x%lx argv_null=0x%lx env0_slot=0x%lx env_null=0x%lx ",
                        "aux0_tag=0x%lx aux0_val=0x%lx\n\0",
                    ).as_ptr().cast::<i8>(),
                    arg0 as CInt, arg1 as CInt, arg2, arg3, arg4, arg5, arg6, arg7, arg8, arg9,
                );
            }
            _ => {}
        }
    }
}

const _: ProcessInitStackLogFn = process_init_stack_log_bridge;


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// Forward the clone owner's original borrowed-context mutation.
///
/// # Safety
/// A non-null context remains live, aligned and exclusively writable through the
/// synchronous provider call. Existing null/unknown-register behavior is retained.
#[cfg(target_arch = "x86_64")]
#[no_mangle]
pub unsafe extern "C" fn process_user_context_modify_bridge(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
) {
    // SAFETY: Same borrowed raw context, integer selector and full unsigned-long value.
    unsafe {
        crate::x86_cpu_helpers::ihk_mc_modify_user_context(
            uctx.cast::<crate::abi::X86UserContext>(), reg, value,
        );
    }
}

#[cfg(target_arch = "x86_64")]
const _: ProcessInitStackModifyContextFn = process_user_context_modify_bridge;


// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// Forward the original XPMEM fault under the same borrowed range/VM guards.
///
/// # Safety
/// Handles, address and reason satisfy the existing XPMEM provider's borrowed/locking
/// contract. That provider retains every Page/reference/PTE/error/notification effect.
#[no_mangle]
pub unsafe extern "C" fn process_xpmem_fault_range_bridge(
    vm: *mut ProcessVm,
    range: *mut VmRange,
    fault_addr: CULong,
    reason: CULong,
) -> CInt {
    // SAFETY: Same raw pointer casts/full-width arguments and unchanged signed result.
    unsafe {
        crate::xpmem_helpers::xpmem_fault_process_memory_range(
            vm.cast(), range.cast(), fault_addr, reason,
        )
    }
}

/// Invoke the original saved pager callback with its unchanged opaque argument.
///
/// # Safety
/// fp is the original non-null live pgio_func_t callback, exactly void(void*).
/// Its code and arg remain valid through this synchronous call under the pager owner.
/// Null arg retains the callback's own policy; invalid fp was outside the C contract.
#[no_mangle]
pub unsafe extern "C" fn process_pgio_dispatch_bridge(fp: *mut c_void, arg: *mut c_void) {
    // SAFETY: The genuine real-header typedef and target function/data-pointer ABI
    // define the same original C cast/call. No guard, ACK, ref release or retry is added.
    unsafe {
        let dispatch: unsafe extern "C" fn(*mut c_void) = core::mem::transmute(fp);
        dispatch(arg);
    }
}

const _: unsafe extern "C" fn(*mut ProcessVm, *mut VmRange, CULong, CULong) -> CInt =
    process_xpmem_fault_range_bridge;
const _: unsafe extern "C" fn(*mut c_void, *mut c_void) = process_pgio_dispatch_bridge;

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

/// Print the existing process-hash view, omitting the resource set's pid1.
///
/// # Safety
/// `hash` and `pid1` come from the live current resource set. All bucket heads and
/// linked process/parent objects remain valid for this synchronous traversal.
/// With `locked`, the existing reader lock excludes list writers in each bucket;
/// otherwise the original debug caller must already exclude removal/reclamation.
/// Printed state fields retain the original diagnostic snapshot semantics.
unsafe fn process_debug_process_hash(
    hash: *mut ProcessHash,
    pid1: *mut Process,
    locked: bool,
) {
    let mut found: CInt = 0;
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    for bucket in 0..PROCESS_HASH_SIZE {
        // SAFETY: Fixed-size ABI arrays contain every bucket. The caller keeps
        // the hash, list members and parents live; lock scope matches C exactly.
        unsafe {
            let lock = core::ptr::addr_of_mut!((*hash).lock)
                .cast::<McsRwlockLock>()
                .add(bucket);
            if locked {
                process_mcs_reader_lock_bridge(lock as CULong, node.as_mut_ptr().cast());
            }
            let head = core::ptr::addr_of_mut!((*hash).list)
                .cast::<AbiListHead>()
                .add(bucket);
            let mut entry = (*head).next;
            while entry != head {
                let process = entry
                    .cast::<u8>()
                    .sub(offset_of!(Process, hash_list))
                    .cast::<Process>();
                if process != pid1 {
                    // The original signed count is representable for live hash
                    // contents; wrapping avoids adding a diagnostic panic path.
                    found = found.wrapping_add(1);
                    if locked {
                        kprintf(
                            b"pid=%d ppid=%d status=%d ref=%d\n\0".as_ptr().cast(),
                            (*process).pid,
                            (*(*process).ppid_parent).pid,
                            (*process).status,
                            (*process).refcount.counter,
                        );
                    } else {
                        kprintf(
                            b"pid=%d ppid=%d status=%d\n\0".as_ptr().cast(),
                            (*process).pid,
                            (*(*process).ppid_parent).pid,
                            (*process).status,
                        );
                    }
                }
                entry = (*entry).next;
            }
            if locked {
                process_mcs_reader_unlock_bridge(lock as CULong, node.as_mut_ptr().cast());
            }
        }
    }
    // SAFETY: Static NUL-terminated format and promoted CInt match C varargs.
    unsafe { kprintf(b"%d processes are found.\n\0".as_ptr().cast(), found) };
}

/// Print the existing thread-hash view in bucket and list order.
///
/// # Safety
/// The current resource set, hash, list members and owning processes remain
/// valid throughout. `locked` retains the original per-bucket reader locking;
/// the unlocked mode requires the original caller's stable diagnostic context.
unsafe fn process_debug_thread_hash(hash: *mut ThreadHash, locked: bool) {
    let mut found: CInt = 0;
    let mut node = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    for bucket in 0..PROCESS_HASH_SIZE {
        // SAFETY: The typed ABI arrays cover each bucket. Original list lifetime
        // and synchronization obligations above cover every raw pointer read.
        unsafe {
            let lock = core::ptr::addr_of_mut!((*hash).lock)
                .cast::<McsRwlockLock>()
                .add(bucket);
            if locked {
                process_mcs_reader_lock_bridge(lock as CULong, node.as_mut_ptr().cast());
            }
            let head = core::ptr::addr_of_mut!((*hash).list)
                .cast::<AbiListHead>()
                .add(bucket);
            let mut entry = (*head).next;
            while entry != head {
                let thread = entry
                    .cast::<u8>()
                    .sub(offset_of!(Thread, hash_list))
                    .cast::<Thread>();
                found = found.wrapping_add(1);
                if locked {
                    kprintf(
                        concat!(
                            "cpu=%d pid=%d tid=%d status=%d ",
                            "offload=%d ref=%d ptrace=%08x\n\0",
                        )
                        .as_ptr()
                        .cast(),
                        (*thread).cpu_id,
                        (*(*thread).proc).pid,
                        (*thread).tid,
                        (*thread).status,
                        (*thread).in_syscall_offload,
                        (*thread).refcount.counter,
                        (*thread).ptrace,
                    );
                } else {
                    kprintf(
                        b"cpu=%d pid=%d tid=%d status=%d\n\0".as_ptr().cast(),
                        (*thread).cpu_id,
                        (*(*thread).proc).pid,
                        (*thread).tid,
                        (*thread).status,
                    );
                }
                entry = (*entry).next;
            }
            if locked {
                process_mcs_reader_unlock_bridge(lock as CULong, node.as_mut_ptr().cast());
            }
        }
    }
    // SAFETY: Static NUL-terminated format and promoted CInt match C varargs.
    unsafe { kprintf(b"%d threads are found.\n\0".as_ptr().cast(), found) };
}

/// Emit the existing process/thread diagnostic selected by codes 1 through 4.
///
/// # Safety
/// The original debug entry context supplies a live CPU-local resource set and
/// keeps CPU/resource-set identity stable. Codes 1/2 retain each original reader
/// lock. Codes 3/4 retain the original unlocked traversal and require list-member
/// and parent/owner lifetimes to remain stable; no new protection is claimed.
#[no_mangle]
pub unsafe extern "C" fn debug_log(arg: CULong) {
    // SAFETY: The caller supplies the original live CPU/resource-set/hash state.
    // Raw pointers avoid creating shared references to concurrently observed
    // kernel storage. Helpers retain original output, ordering and lock scopes.
    unsafe {
        let resource_set = (*get_this_cpu_local_var()).resource_set;
        let processes = (*resource_set).process_hash;
        let threads = (*resource_set).thread_hash;
        let pid1 = (*resource_set).pid1;
        match arg {
            1 => process_debug_process_hash(processes, pid1, true),
            2 => process_debug_thread_hash(threads, true),
            3 => process_debug_process_hash(processes, pid1, false),
            4 => process_debug_thread_hash(threads, false),
            _ => {}
        }
    }
}

const _: unsafe extern "C" fn(CULong) = debug_log;

// The actual callback node/lock layouts used by this bridge are independently typed.
const _: () = {
    assert!(core::mem::size_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(core::mem::align_of::<McsRwlockNodeIrqsave>() == 64);
    assert!(core::mem::size_of::<McsRwlockLock>() == 64);
    assert!(core::mem::align_of::<McsRwlockLock>() == 64);
    assert!(PROCESS_HASH_SIZE == 73);
};

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_profile_providers {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::CInt;
    #[cfg(enable_profile)]
    use crate::abi::{Process, Thread};
    use crate::ap::IhkMcCpuInfo;

    use super::EINVAL;

    unsafe extern "C" {
        #[link_name = "ihk_mc_get_cpu_info"]
        fn current_cpu_info() -> *mut IhkMcCpuInfo;
    }

    const _: () = {
        assert!(size_of::<IhkMcCpuInfo>() == 40);
        assert!(align_of::<IhkMcCpuInfo>() == 8);
        assert!(offset_of!(IhkMcCpuInfo, ncpus) == 0);
    };

    /// Return the existing CPU-info count, or the original absent-info error.
    ///
    /// # Safety
    /// The platform getter supplies either null or a live, initialized CPU-info
    /// object whose count remains readable through this synchronous call. No
    /// ownership or reference changes occur; the original signed count is kept.
    #[no_mangle]
    pub unsafe extern "C" fn process_default_ncpus_bridge() -> CInt {
        // SAFETY: The getter and its existing initialized-object contract supply
        // the same nullable40-byte C-layout object as the original C provider.
        unsafe {
            let info = current_cpu_info();
            if info.is_null() {
                -EINVAL
            } else {
                (*info).ncpus
            }
        }
    }

    /// Accumulate a released thread's events before its existing deallocation.
    ///
    /// # Safety
    /// With profiling selected, the existing release owner preserves thread and
    /// process/event lifetimes until accumulation finishes, then grants the same
    /// one-time event deallocation. The existing providers retain their null
    /// handling and locks. Without profiling, both pointers remain unused.
    #[no_mangle]
    pub unsafe extern "C" fn process_release_thread_profile_bridge(
        thread: *mut c_void,
        proc: *mut c_void,
    ) {
        #[cfg(enable_profile)]
        // SAFETY: The original release callback owns this sequencing. Existing
        // providers borrow the same objects, then free the same event allocation;
        // no extra reset, free, reference, lock or event traversal is introduced.
        unsafe {
            crate::profile::profile_accumulate_events(
                thread.cast::<Thread>(),
                proc.cast::<Process>(),
            );
            crate::profile::profile_dealloc_thread_events(thread.cast::<Thread>());
        }
        #[cfg(not(enable_profile))]
        let _ = (thread, proc);
    }

    /// Print the released process's selected profile before its event teardown.
    ///
    /// # Safety
    /// With profiling selected, `proc_arg` is the original live process under its
    /// final-release owner. Profile state stays readable through the synchronous
    /// print/accumulation callback and the owner permits the existing one-time
    /// deallocation afterward. Without profiling, the pointer is not accessed.
    #[no_mangle]
    pub unsafe extern "C" fn process_release_profile_bridge(proc_arg: *mut c_void) {
        #[cfg(enable_profile)]
        // SAFETY: The caller retains the same process/event lifetimes and release
        // exclusivity as C. Existing Rust providers own all statistics, locking,
        // printing and deallocation, preserving their order and return handling.
        unsafe {
            let proc = proc_arg.cast::<Process>();
            if (*proc).profile != 0 {
                if (*proc).nr_processes != 0 {
                    let _ = crate::profile::profile_accumulate_and_print_job_events(proc);
                } else {
                    crate::profile::profile_print_proc_stats(proc);
                }
            }
            crate::profile::profile_dealloc_proc_events(proc);
        }
        #[cfg(not(enable_profile))]
        let _ = proc_arg;
    }

    const _: unsafe extern "C" fn() -> CInt = process_default_ncpus_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void) =
        process_release_thread_profile_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_release_profile_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_tracked_allocators {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong, VmRange};

    use super::IHK_MC_AP_NOWAIT;

    unsafe extern "C" {
        static process_tracked_allocator_source_file: *const i8;
        static process_alloc_bridge_source_line: CInt;
        static process_add_range_alloc_bridge_source_line: CInt;
        static process_mckfd_free_bridge_source_line: CInt;
        static process_policy_free_bridge_source_line: CInt;
        static process_optional_free_bridge_source_line: CInt;
        static process_free_vm_bridge_source_line: CInt;
        static process_range_kfree_bridge_source_line: CInt;
        static process_add_range_free_bridge_source_line: CInt;
    }

    /// Allocate through the same tracked allocator and source location.
    ///
    /// # Safety
    /// The existing caller supplies allocator-valid size/flags and observes the
    /// same nullable allocation result and ownership transfer as C. The narrowed
    /// signed size matches the original C int parameter conversion. Source
    /// metadata stays live and the allocator never modifies its file bytes.
    #[no_mangle]
    pub unsafe extern "C" fn process_alloc_bridge(size: CULong, flags: CULong) -> *mut c_void {
        // SAFETY: The same tracked allocator owns allocation and OOM reporting.
        // Readonly source metadata preserves the existing call-site diagnostic.
        unsafe {
            crate::mem_helpers::kmalloc_tracked(
                size as CInt,
                flags,
                process_tracked_allocator_source_file as *mut i8,
                process_alloc_bridge_source_line,
            )
        }
    }

    /// Allocate range storage with the original NOWAIT flag and trace location.
    ///
    /// # Safety
    /// The caller retains the original allocator size domain and must initialize
    /// the returned nullable raw storage before field access. No reference or
    /// initialized VmRange value is formed here; allocator ownership is unchanged.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_alloc_bridge(size: CULong) -> *mut VmRange {
        // SAFETY: Preserve original int narrowing and IHK_MC_AP_NOWAIT=2. The
        // existing allocator alone chooses/initializes allocation bookkeeping.
        unsafe {
            crate::mem_helpers::kmalloc_tracked(
                size as CInt,
                IHK_MC_AP_NOWAIT,
                process_tracked_allocator_source_file as *mut i8,
                process_add_range_alloc_bridge_source_line,
            )
            .cast::<VmRange>()
        }
    }

    /// Release the original final-owned descriptor allocation through tracking.
    ///
    /// # Safety
    /// The caller supplies exactly the pointer accepted by the existing tracked
    /// free contract, with exclusive final-release authority. Null forwarding and
    /// diagnostics retain the provider's existing policy; no new guard is added.
    #[no_mangle]
    pub unsafe extern "C" fn process_mckfd_free_bridge(fdp: *mut c_void) {
        // SAFETY: The caller owns the same allocation's final release; source
        // metadata is immutable and valid for this synchronous provider call.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                fdp,
                process_tracked_allocator_source_file as *mut i8,
                process_mckfd_free_bridge_source_line,
            );
        }
    }

    /// Release the original policy allocation without changing its free policy.
    ///
    /// # Safety
    /// `policy` satisfies the existing tracked-free provenance and final-owner
    /// obligations; null retains the original allocator's handling.
    #[no_mangle]
    pub unsafe extern "C" fn process_policy_free_bridge(policy: *mut c_void) {
        // SAFETY: Same pointer, ownership transfer and stable source metadata.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                policy,
                process_tracked_allocator_source_file as *mut i8,
                process_policy_free_bridge_source_line,
            );
        }
    }

    /// Forward the original optional allocation to its tracked free provider.
    ///
    /// # Safety
    /// The caller has the same nullable allocation provenance and final-release
    /// authority required by the existing provider. This adds no null filter.
    #[no_mangle]
    pub unsafe extern "C" fn process_optional_free_bridge(ptr: *mut c_void) {
        // SAFETY: The existing allocator owns the exact pointer/null handling.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                ptr,
                process_tracked_allocator_source_file as *mut i8,
                process_optional_free_bridge_source_line,
            );
        }
    }

    /// Release final-owned VM storage through its original tracked free site.
    ///
    /// # Safety
    /// The caller has completed VM teardown and supplies the same allocator-valid
    /// pointer with exclusive final ownership. Underlying null handling is kept.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_vm_bridge(vm: *mut c_void) {
        // SAFETY: Same allocation/provenance and one-time release contract as C.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                vm,
                process_tracked_allocator_source_file as *mut i8,
                process_free_vm_bridge_source_line,
            );
        }
    }

    /// Release range storage at the original merge-cleanup tracking location.
    ///
    /// # Safety
    /// The original range owner has detached/finished the range as required by
    /// the caller and grants the same one-time allocation free. No fields are read.
    #[no_mangle]
    pub unsafe extern "C" fn process_range_kfree_bridge(range: *mut VmRange) {
        // SAFETY: Raw conversion keeps the same allocation address and ownership.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                range.cast::<c_void>(),
                process_tracked_allocator_source_file as *mut i8,
                process_range_kfree_bridge_source_line,
            );
        }
    }

    /// Release the original add-range rollback allocation through tracking.
    ///
    /// # Safety
    /// The existing rollback owner supplies allocator-valid range storage and
    /// authorizes its final release. No new rollback or publication path is added.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_free_bridge(range: *mut VmRange) {
        // SAFETY: Preserve the caller's exact rollback pointer and trace site.
        unsafe {
            crate::mem_helpers::kfree_tracked(
                range.cast::<c_void>(),
                process_tracked_allocator_source_file as *mut i8,
                process_add_range_free_bridge_source_line,
            );
        }
    }

    const _: unsafe extern "C" fn(CULong, CULong) -> *mut c_void = process_alloc_bridge;
    const _: unsafe extern "C" fn(CULong) -> *mut VmRange = process_add_range_alloc_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_mckfd_free_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_policy_free_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_optional_free_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_free_vm_bridge;
    const _: unsafe extern "C" fn(*mut VmRange) = process_range_kfree_bridge;
    const _: unsafe extern "C" fn(*mut VmRange) = process_add_range_free_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_free_range_providers {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::{CInt, CULong, IhkSpinlock, Memobj, ProcessVm, SizeT, VmRange};

    const MF_XPMEM: u32 = 0x10000;

    // Both types describe the existing4-byte C ticket lock. The actual provider
    // module independently asserts its head/tail field offset0 and alignment4.
    // Raw casts below introduce no references or extra lock state/lifetimes.
    const _: () = {
        assert!(size_of::<IhkSpinlock>() == 4);
        assert!(align_of::<IhkSpinlock>() == 4);
        assert!(offset_of!(IhkSpinlock, head_tail) == 0);
        assert!(size_of::<crate::spinlock_helpers::IhkSpinlock>() == 4);
        assert!(align_of::<crate::spinlock_helpers::IhkSpinlock>() == 4);
    };

    /// Obtain the same next smaller page size without requesting p2alignment.
    ///
    /// # Safety
    /// The existing caller supplies the original supported page-size domain and
    /// writable output pointer. The actual architecture provider keeps its same
    /// error/output policy; both original optional arguments remain null.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_page_size_bridge(
        current: SizeT,
        nextp: *mut SizeT,
    ) -> CInt {
        // SAFETY: Original output/domain contract is forwarded unchanged.
        unsafe {
            crate::x86_memory_helpers::arch_get_smaller_page_size(
                null_mut(), current, nextp, null_mut(),
            )
        }
    }

    /// Translate the original physical address with the existing architecture map.
    ///
    /// # Safety
    /// The address satisfies the original phys_to_virt provider's supported map
    /// domain. This does not dereference, allocate or acquire the returned memory.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_phys_to_virt_bridge(phys: CULong) -> *mut c_void {
        // SAFETY: Same scalar domain and unchanged raw pointer translation.
        unsafe { crate::x86_memory_helpers::phys_to_virt(phys) }
    }

    /// Clear the same main page-table range under its existing noirq lock.
    ///
    /// # Safety
    /// The caller supplies a live VM/address space and the original valid range.
    /// The VM and page-table lock remain stable through lock, backend and unlock.
    /// Existing IRQ context and lock ordering apply; neither callback unwinds.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_clear_main_bridge(
        vm_arg: *mut c_void,
        start: CULong,
        end: CULong,
    ) -> CInt {
        let vm = vm_arg.cast::<ProcessVm>();
        // SAFETY: The actual C/ABI lock and Rust ticket-lock representations are
        // identical as asserted above. Exclusive access is provided by the same
        // original lock; no Rust reference to the VM or address space is formed.
        unsafe {
            let lock = core::ptr::addr_of_mut!((*vm).page_table_lock)
                .cast::<crate::spinlock_helpers::IhkSpinlock>();
            crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(lock);
            let error = crate::x86_memory_helpers::ihk_mc_pt_clear_range(
                (*(*vm).address_space).page_table,
                vm,
                start as *mut c_void,
                end as *mut c_void,
            );
            crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(lock);
            error
        }
    }

    /// Acquire the original caller-specified noirq ticket lock.
    ///
    /// # Safety
    /// The address is aligned/live writable C ticket-lock storage in the original
    /// allowed IRQ context and lock order, with exclusive ownership after return.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_noirq_lock_bridge(lock_addr: CULong) {
        // SAFETY: The caller's existing C lock storage has the exact asserted
        // representation; the raw cast changes no address, lifetime or state.
        unsafe {
            crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(
                lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
            );
        }
    }

    /// Release the same caller-owned noirq ticket-lock acquisition.
    ///
    /// # Safety
    /// The caller owns this exact lock's current acquisition and keeps the same
    /// live/aligned storage and IRQ context through its single matching release.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_noirq_unlock_bridge(lock_addr: CULong) {
        // SAFETY: Same lock address and ABI representation, no added acquisition.
        unsafe {
            crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(
                lock_addr as *mut crate::spinlock_helpers::IhkSpinlock,
            );
        }
    }

    /// Forward the existing page-table free operation and borrowed memobj.
    ///
    /// # Safety
    /// The original owner provides live page-table/VM/memobj state, valid range
    /// and backend-required lock/lifetime conditions. Existing free/error policy
    /// remains entirely with the same architecture provider.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_pt_free_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
        memobj: *mut c_void,
    ) -> CInt {
        // SAFETY: Exact original borrowed arguments and pointer conversions.
        unsafe {
            crate::x86_memory_helpers::ihk_mc_pt_free_range(
                page_table, vm, start as *mut c_void, end as *mut c_void, memobj.cast::<Memobj>(),
            )
        }
    }

    /// Forward the existing page-table clear operation without a new lock.
    ///
    /// # Safety
    /// The original caller preserves live page-table/VM state, valid range and
    /// the provider's existing ownership/lock contract through the synchronous call.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_range_pt_clear_bridge(
        page_table: *mut c_void,
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
    ) -> CInt {
        // SAFETY: Forward only; the caller retains existing synchronization.
        unsafe {
            crate::x86_memory_helpers::ihk_mc_pt_clear_range(
                page_table, vm, start as *mut c_void, end as *mut c_void,
            )
        }
    }

    /// Publish the original XPMEM accounting flag on the range's memobj.
    ///
    /// # Safety
    /// The range and nonnull memobj remain valid/writable under the original
    /// publication owner's exclusion of conflicting flag updates. This preserves
    /// the existing non-atomic read/OR/write and adds no lock or reference policy.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_mark_xpmem_bridge(range: *mut VmRange) {
        // SAFETY: Original caller owns this live flag publication; the same
        // actual u32 memobj field is modified without creating shared references.
        unsafe { (*(*range).memobj.cast::<Memobj>()).flags |= MF_XPMEM };
    }

    const _: unsafe extern "C" fn(SizeT, *mut SizeT) -> CInt = process_free_range_page_size_bridge;
    const _: unsafe extern "C" fn(CULong) -> *mut c_void = process_free_range_phys_to_virt_bridge;
    const _: unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt =
        process_free_range_clear_main_bridge;
    const _: unsafe extern "C" fn(CULong) = process_free_range_noirq_lock_bridge;
    const _: unsafe extern "C" fn(CULong) = process_free_range_noirq_unlock_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong, *mut c_void) -> CInt =
        process_free_range_pt_free_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut ProcessVm, CULong, CULong) -> CInt =
        process_free_range_pt_clear_bridge;
    const _: unsafe extern "C" fn(*mut VmRange) = process_add_range_mark_xpmem_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_lock_and_tid_providers {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{CInt, CULong, McsRwlockLock, Process, Thread};

    const _: () = {
        assert!(size_of::<McsRwlockLock>() == 64);
        assert!(align_of::<McsRwlockLock>() == 64);
        assert!(offset_of!(McsRwlockLock, slock) == 0);
        assert!(size_of::<crate::lock_helpers::McsRwlockLock>() == 64);
        assert!(align_of::<crate::lock_helpers::McsRwlockLock>() == 64);
        assert!(size_of::<crate::lock_helpers::McsRwlockNodeIrqsave>() == 64);
        assert!(align_of::<crate::lock_helpers::McsRwlockNodeIrqsave>() == 64);
    };

    /// Acquire the original IRQ-saving writer lock using the caller's node.
    ///
    /// # Safety
    /// `lock_addr` names aligned/live C MCS lock storage and `node` names the
    /// caller's aligned/writable IRQ-save node. The caller obeys existing lock
    /// ordering/IRQ context and preserves both through their matching unlock.
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_writer_lock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Actual C and Rust lock/node representations match the same
        // existing provider ABI. Raw casts preserve addresses without references;
        // the provider retains the original IRQ-save and acquisition operation.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_writer_lock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }

    /// Release the original writer acquisition and restore its node's IRQ state.
    ///
    /// # Safety
    /// The caller owns this exact acquisition and supplies the same live lock and
    /// original saved node, excluding competing node reuse until release finishes.
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_writer_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Same lock/node and one matching provider release; no new state
        // or IRQ restore is synthesized outside the actual lock implementation.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_writer_unlock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }

    /// Acquire the original IRQ-saving reader lock using the caller's node.
    ///
    /// # Safety
    /// The caller provides the same aligned/live lock and exclusive writable node
    /// storage required by the C bridge and retains them for the matching unlock.
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_reader_lock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Preserve the existing typed C representation and actual reader
        // provider selection, including its IRQ handling and synchronization.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_reader_lock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }

    /// Release the original reader acquisition with its original IRQ-save node.
    ///
    /// # Safety
    /// The caller owns the matching acquisition; lock/node storage remains live,
    /// aligned and protected against conflicting node mutation until return.
    #[no_mangle]
    pub unsafe extern "C" fn process_mcs_reader_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
        // SAFETY: Actual provider restores the same saved state from the same
        // caller node. No guard lifetime, lock count or pointer value changes.
        unsafe {
            crate::lock_helpers::__mcs_rwlock_reader_unlock(
                lock_addr as *mut crate::lock_helpers::McsRwlockLock,
                node.cast::<crate::lock_helpers::McsRwlockNodeIrqsave>(),
            );
        }
    }

    /// Retain the original thread reference through the existing public entry.
    ///
    /// # Safety
    /// The original caller satisfies hold_thread's lifetime/reference contract.
    /// Its original int result remains ignored by this void callback, as in C.
    #[no_mangle]
    pub unsafe extern "C" fn process_hold_thread_bridge(thread: *mut c_void) {
        // SAFETY: Same pointer and provider, without a new reference operation.
        unsafe {
            let _ = super::hold_thread(thread.cast::<Thread>());
        }
    }

    /// Forward the original final-thread TID release to the existing body.
    ///
    /// # Safety
    /// The process/thread and TID table remain live under the caller's original
    /// final-release exclusion and reference ownership throughout this callback.
    #[no_mangle]
    pub unsafe extern "C" fn process_destroy_thread_release_tid_bridge(
        proc: *mut c_void,
        thread: *mut c_void,
    ) {
        // SAFETY: Preserve exact objects and existing table/lock/lifecycle policy.
        unsafe { super::__release_tid(proc.cast::<Process>(), thread.cast::<Thread>()) };
    }

    /// Forward the existing TID replacement without adding lookup or lifetime work.
    ///
    /// # Safety
    /// The caller preserves the original process/thread/TID table lifetime and
    /// required exclusion; `new_tid` retains the existing provider's value domain.
    #[no_mangle]
    pub unsafe extern "C" fn process_destroy_thread_replace_tid_bridge(
        proc: *mut c_void,
        thread: *mut c_void,
        new_tid: CInt,
    ) {
        // SAFETY: Exact arguments reach the existing replacement operation once.
        unsafe {
            super::__find_and_replace_tid(proc.cast::<Process>(), thread.cast::<Thread>(), new_tid);
        }
    }

    const _: unsafe extern "C" fn(CULong, *mut c_void) = process_mcs_writer_lock_bridge;
    const _: unsafe extern "C" fn(CULong, *mut c_void) = process_mcs_writer_unlock_bridge;
    const _: unsafe extern "C" fn(CULong, *mut c_void) = process_mcs_reader_lock_bridge;
    const _: unsafe extern "C" fn(CULong, *mut c_void) = process_mcs_reader_unlock_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_hold_thread_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void) =
        process_destroy_thread_release_tid_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void, CInt) =
        process_destroy_thread_replace_tid_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_create_thread_providers {
    use core::ffi::c_void;

    use crate::abi::{
        AddressSpace, CInt, CULong, Process, ProcessVm, Thread, X86KernelContext, X86UserContext,
    };

    unsafe extern "C" {
        #[link_name = "ihk_mc_init_user_process"]
        fn initialize_user_context(
            context: *mut X86KernelContext,
            user_context: *mut *mut X86UserContext,
            stack_pointer: *mut c_void,
            new_pc: CULong,
            user_sp: CULong,
        );
    }

    /// Create address-space storage through the existing current resource set.
    ///
    /// # Safety
    /// The caller runs with the original live CPU-local/resource-set state and
    /// supplies the existing slot-count domain. CPU binding is stable while
    /// reading its resource set; that resource set stays live through creation.
    /// The same backend owns allocation/error policy and nullable ownership return.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_address_space_bridge(nslots: CInt) -> *mut c_void {
        // SAFETY: Same synchronous getter/read/builder sequence as C. Raw reads
        // create no reference and preserve the existing resource-set lifetime.
        unsafe {
            let resource_set = (*super::get_this_cpu_local_var()).resource_set;
            super::create_address_space(resource_set, nslots).cast::<c_void>()
        }
    }

    /// Release the same address-space reference through the existing Rust entry.
    ///
    /// # Safety
    /// The original owner supplies an address-space pointer/reference accepted by
    /// release_address_space and grants the same one-time reference release.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_release_address_space_bridge(asp: *mut c_void) {
        // SAFETY: Exact pointer and existing backend reference/cleanup policy.
        unsafe { super::release_address_space(asp.cast::<AddressSpace>()) };
    }

    /// Invoke the original process initializer and retain its void/zero convention.
    ///
    /// # Safety
    /// The creator exclusively owns the same writable process storage and valid
    /// parent relationship required by init_process. Existing initialization and
    /// invariant-failure behavior remain in that unchanged backend.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_init_process_bridge(
        proc: *mut c_void,
        parent: *mut c_void,
    ) -> CInt {
        // SAFETY: This adapter neither reads fields nor adds initialization work.
        unsafe { super::init_process(proc.cast::<Process>(), parent.cast::<Process>()) };
        0
    }

    /// Forward the original process/space/VM tuple and its exact initialization result.
    ///
    /// # Safety
    /// The creator keeps the process and address space live and exclusively owns
    /// writable VM storage under the initializer's original lifetime contract.
    /// Any subsequent rollback remains solely with the existing caller.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_init_vm_bridge(
        owner: *mut c_void,
        asp: *mut c_void,
        vm: *mut c_void,
    ) -> CInt {
        // SAFETY: Identical borrowed objects reach the same actual initializer;
        // no new lock, reference, reset, error translation or cleanup is added.
        unsafe {
            super::init_process_vm(
                owner.cast::<Process>(), asp.cast::<AddressSpace>(), vm.cast::<ProcessVm>(),
            )
        }
    }

    /// Initialize the same thread context and user-context pointer through its ABI entry.
    ///
    /// # Safety
    /// The creator owns live/writable thread context and uctx output storage and
    /// the original writable initial stack span. The existing architecture entry
    /// retains its frame geometry, assembly target and user PC/SP contracts.
    /// This adapter does not run the created user context or change FP handling.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_init_user_bridge(
        thread: *mut c_void,
        stack_top: CULong,
        user_pc: CULong,
        user_sp: CULong,
    ) {
        let thread = thread.cast::<Thread>();
        // SAFETY: Raw field-address computation preserves the exact original
        // context/output addresses without borrowing uninitialized thread data.
        // The unchanged, exported Rust architecture entry performs all writes.
        unsafe {
            initialize_user_context(
                core::ptr::addr_of_mut!((*thread).ctx),
                core::ptr::addr_of_mut!((*thread).uctx),
                stack_top as *mut c_void,
                user_pc,
                user_sp,
            );
        }
    }

    const _: unsafe extern "C" fn(CInt) -> *mut c_void = process_create_thread_address_space_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_create_thread_release_address_space_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt =
        process_create_thread_init_process_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void, *mut c_void) -> CInt =
        process_create_thread_init_vm_bridge;
    const _: unsafe extern "C" fn(*mut c_void, CULong, CULong, CULong) =
        process_create_thread_init_user_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_create_leafs {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong};

    unsafe extern "C" {
        static process_tracked_allocator_source_file: *const i8;
        static process_create_thread_alloc_pages_source_line: CInt;
        static mut process_create_cpu_debug: crate::debug::Ddebug;
    }

    /// Allocate the original creator stack pages through the existing tracked allocator.
    ///
    /// # Safety
    /// The caller supplies the allocator's original page-count/flags domain and
    /// takes ownership of the identical nullable raw allocation. Source metadata
    /// stays valid for tracking; no initialized Thread reference is formed here.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_thread_alloc_pages_bridge(
        npages: CInt, flags: CULong,
    ) -> *mut c_void {
        // SAFETY: Exact original x86 PAGE_P2ALIGN=0/IHK_MC_PG_KERNEL=0,
        // node=-1/virtual-address=-1 conversion and tracked source identity.
        // The genuine-header fixture binds the two architecture constants.
        unsafe {
            crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
                npages, 0, flags, -1, 0, CULong::MAX,
                process_tracked_allocator_source_file.cast_mut(),
                process_create_thread_alloc_pages_source_line,
            )
        }
    }

    /// Emit the original creator CPU diagnostics with the same dynamic selector.
    ///
    /// # Safety
    /// Called in the original logging context. The retained C descriptor lives in
    /// __verbose throughout kernel life and follows the existing dynamic-debug
    /// update/read policy. No process/thread ownership escapes this operation.
    #[no_mangle]
    pub unsafe extern "C" fn process_create_cpu_log_bridge(event: CInt, pid: CInt, cpu: CInt) {
        // SAFETY: Terminated static formats and exact promoted C int arguments;
        // packed line/flags use the already reviewed real Ddebug representation.
        unsafe {
            match event {
                super::PROCESS_CREATE_CPU_LOG_INVALID => {
                    let _ = super::kprintf(
                        b"%s: invalid CPU requested in initial cpu_set\n\0".as_ptr().cast(),
                        b"create_thread\0".as_ptr().cast::<i8>(),
                    );
                }
                super::PROCESS_CREATE_CPU_LOG_REQUESTED => {
                    let flags = core::ptr::read_volatile(
                        core::ptr::addr_of!(process_create_cpu_debug.line_flags),
                    ) >> 24;
                    if flags != 0 {
                        let _ = super::kprintf(
                            b"%s: pid: %d, CPU: %d\n\0".as_ptr().cast(),
                            b"create_thread\0".as_ptr().cast::<i8>(), pid, cpu,
                        );
                    }
                }
                _ => {}
            }
        }
    }

    const _: unsafe extern "C" fn(CInt, CULong) -> *mut c_void =
        process_create_thread_alloc_pages_bridge;
    const _: unsafe extern "C" fn(CInt, CInt, CInt) = process_create_cpu_log_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_thread_page_release {
    use core::ffi::c_void;
    use crate::abi::CInt;
    unsafe extern "C" {
        static process_tracked_allocator_source_file: *const i8;
        static process_free_thread_pages_source_line: CInt;
    }
    /// Release the creator's original stack allocation through its tracked backend.
    ///
    /// # Safety
    /// The original caller owns the same stack-page allocation and has completed
    /// all accesses/references whose lifetime ends at this release. The pointer,
    /// page-count/type, tracking metadata and backend null policy are unchanged.
    /// No pointer is dereferenced, inspected or accessed after this synchronous free.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_thread_pages_bridge(thread: *mut c_void) {
        // SAFETY: Original tracked free operation exactly once; the existing
        // backend owns null handling, tracking, locking and actual page release.
        unsafe {
            crate::mem_helpers::_ihk_mc_free_pages(
                thread, super::KERNEL_STACK_NR_PAGES as CInt, 0,
                process_tracked_allocator_source_file.cast_mut(),
                process_free_thread_pages_source_line,
            );
        }
    }
    const _: unsafe extern "C" fn(*mut c_void) = process_free_thread_pages_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_page_table_providers {
    use core::ffi::c_void;
    use crate::abi::{CInt,CULong,SizeT};

    /// Invoke the original single-address TLB invalidation entry.
    ///
    /// # Safety
    /// The caller retains the original privileged CPU/address-space and mapping
    /// synchronization context; this performs the same hardware operation once.
    #[no_mangle]
    pub unsafe extern "C" fn process_flush_tlb_single_bridge(addr:CULong) {
        // SAFETY: Exact address and unchanged architecture invalidation policy.
        unsafe { crate::x86_memory_helpers::flush_tlb_single(addr) };
    }

    /// Return the existing architecture's table level for the unchanged page size.
    ///
    /// # Safety
    /// Retains the existing C ABI callback contract; no memory is accessed here.
    #[no_mangle]
    pub unsafe extern "C" fn process_pgsize_to_tbllv_bridge(pgsize:SizeT)->CInt {
        crate::pte_helpers::pgsize_to_tbllv(pgsize)
    }

    /// Return the existing architecture's contiguous-page size for the same level.
    ///
    /// # Safety
    /// Retains the existing C ABI callback contract; unsupported-level policy
    /// belongs to the unchanged Rust architecture provider.
    #[no_mangle]
    pub unsafe extern "C" fn process_tbllv_to_contpgsize_bridge(level:CInt)->SizeT {
        crate::pte_helpers::tbllv_to_contpgsize(level)
    }

    /// Forward the borrowed page and exact unmap result to the existing Rust entry.
    ///
    /// # Safety
    /// The original owner keeps the page live under the original page-unmap
    /// locking/reference contract. This adapter adds no dereference, reference,
    /// return translation, free or new callback lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn process_page_unmap_bridge(page:*mut c_void)->CInt {
        // SAFETY: Raw cast preserves the exact existing C page pointer; the same
        // provider owns hash locking, map/reference changes and return semantics.
        unsafe { crate::page_helpers::page_unmap(page.cast::<crate::page_helpers::Page>()) }
    }
    const _:unsafe extern "C" fn(CULong)=process_flush_tlb_single_bridge;
    const _:unsafe extern "C" fn(SizeT)->CInt=process_pgsize_to_tbllv_bridge;
    const _:unsafe extern "C" fn(CInt)->SizeT=process_tbllv_to_contpgsize_bridge;
    const _:unsafe extern "C" fn(*mut c_void)->CInt=process_page_unmap_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_pte_bitops {
    use core::ffi::c_void;
    use crate::abi::{CInt,CLong,CULong,SizeT};

    /// Return the existing architecture's exact null-PTE predicate.
    ///
    /// # Safety
    /// ptep names a live aligned PTE under the original mapping caller's access
    /// and synchronization contract; the same provider performs the raw read.
    #[no_mangle]
    pub unsafe extern "C" fn process_pte_is_null_bridge(ptep:*mut c_void)->CInt {
        unsafe { crate::pte_helpers::pte_is_null(ptep.cast::<CULong>()) }
    }
    /// Return the original file-offset predicate for the same PTE/page-size pair.
    ///
    /// # Safety
    /// The original owner keeps this readable PTE live and its page-size domain
    /// valid under existing mapping exclusion; no reference is created here.
    #[no_mangle]
    pub unsafe extern "C" fn process_pte_is_fileoff_bridge(ptep:*mut c_void,pgsize:SizeT)->CInt {
        unsafe { crate::pte_helpers::pte_is_fileoff(ptep.cast::<CULong>(),pgsize) }
    }
    /// Write the original file-offset PTE with the same zero attribute argument.
    ///
    /// # Safety
    /// The caller exclusively owns aligned writable PTE storage under its
    /// original page-table locks; off/pgsize retain the existing provider domain.
    #[no_mangle]
    pub unsafe extern "C" fn process_pte_make_fileoff_bridge(off:CLong,pgsize:SizeT,ptep:*mut c_void) {
        unsafe { crate::pte_helpers::pte_make_fileoff(off,0,pgsize,ptep.cast::<CULong>()) };
    }
    /// Perform the same PTE exchange and return its old value through valp.
    ///
    /// # Safety
    /// The existing caller supplies aligned initialized PTE/val storage under
    /// its original synchronization. The unchanged backend retains its atomic
    /// ordering, alias behavior and writeback; this adds no subsequent access.
    #[no_mangle]
    pub unsafe extern "C" fn process_pte_xchg_bridge(ptep:*mut c_void,valp:*mut c_void) {
        unsafe { crate::pte_helpers::pte_xchg(ptep.cast::<CULong>(),valp.cast::<CULong>()) };
    }
    const _:unsafe extern "C" fn(*mut c_void)->CInt=process_pte_is_null_bridge;
    const _:unsafe extern "C" fn(*mut c_void,SizeT)->CInt=process_pte_is_fileoff_bridge;
    const _:unsafe extern "C" fn(CLong,SizeT,*mut c_void)=process_pte_make_fileoff_bridge;
    const _:unsafe extern "C" fn(*mut c_void,*mut c_void)=process_pte_xchg_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_page_object_providers {
    use core::ffi::c_void;
    use crate::abi::{CInt,CULong,Memobj,SizeT};

    /// Return the existing borrowed page lookup result without a new reference.
    ///
    /// # Safety
    /// The caller retains the original mapping/hash lifetime and synchronization
    /// duties after lookup unlocks. The backend owns the original hash lock and
    /// NULL result policy; this adapter acquires no page reference or storage.
    #[no_mangle]
    pub unsafe extern "C" fn process_phys_to_page_bridge(phys:CULong)->*mut c_void {
        unsafe { crate::mem_helpers::phys_to_page(phys).cast::<c_void>() }
    }

    /// Invoke the existing memobj invalidation dispatch and preserve its result.
    ///
    /// # Safety
    /// The original owner keeps memobj, its ops table and optional callback live
    /// throughout this synchronous dispatch, preserving the provider's original
    /// lock/reference contract and phys/pgsize domain. No callback escapes here.
    #[no_mangle]
    pub unsafe extern "C" fn process_memobj_invalidate_page_bridge(
        memobj:*mut Memobj,phys:CULong,pgsize:SizeT,
    )->CInt {
        unsafe { crate::object_helpers::memobj_invalidate_page(memobj,phys,pgsize) }
    }
    const _:unsafe extern "C" fn(CULong)->*mut c_void=process_phys_to_page_bridge;
    const _:unsafe extern "C" fn(*mut Memobj,CULong,SizeT)->CInt=process_memobj_invalidate_page_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_ptrace_providers {
    use core::ffi::c_void;
    use crate::abi::{CInt,CLong,CULong,Thread};
    use crate::lock_helpers::McsRwlockLock;

    /// Acquire the original noirq writer lock with the same opaque caller node.
    ///
    /// # Safety
    /// lock_addr names live aligned MCS lock storage and node is the original
    /// writable caller-owned noirq node. Original lock order and IRQ context
    /// persist through the matching release; this does not save/restore IRQs.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_mcs_lock_noirq_bridge(lock_addr:CULong,node:*mut c_void) {
        unsafe { crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(lock_addr as *mut McsRwlockLock,node) };
    }
    /// Release the original noirq writer acquisition using the same caller node.
    ///
    /// # Safety
    /// The caller owns this exact lock acquisition, keeps both objects live and
    /// retains original IRQ context; no IRQ-state or node lifetime is synthesized.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_mcs_unlock_noirq_bridge(lock_addr:CULong,node:*mut c_void) {
        unsafe { crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(lock_addr as *mut McsRwlockLock,node) };
    }
    /// Invoke the same existing Rust debug-register allocator and C int result.
    ///
    /// # Safety
    /// The original owner keeps Thread/debug-register state valid under the
    /// same ptrace exclusion. Allocation policy and nullable storage stay in
    /// the unchanged Rust backend. Its CLong result narrows as original C int.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_alloc_debugreg_bridge(thread:*mut c_void)->CInt {
        unsafe { crate::syscall_policy::alloc_debugreg(thread.cast::<Thread>()) as CInt }
    }
    /// Clear the same thread single-step state through the existing Rust entry.
    ///
    /// # Safety
    /// The original owner preserves Thread/user-context lifetime and ptrace
    /// exclusion. This adapter executes no hardware debug-register operation.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_clear_single_step_bridge(thread:*mut c_void) {
        unsafe { crate::syscall_policy::clear_single_step(thread.cast::<Thread>()) };
    }
    /// Acquire the original held Thread reference through the existing Rust entry.
    ///
    /// # Safety
    /// The original caller keeps the thread live and follows unchanged hold/
    /// retirement ownership rules; the original ignored C int result stays ignored.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_hold_thread_bridge(thread:*mut c_void) {
        let _=unsafe { super::hold_thread(thread.cast::<Thread>()) };
    }
    const _:unsafe extern "C" fn(*mut Thread)->CLong=crate::syscall_policy::alloc_debugreg;
    const _:unsafe extern "C" fn(*mut Thread)=crate::syscall_policy::clear_single_step;
    const _:unsafe extern "C" fn(*mut Thread)->CInt=super::hold_thread;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_ptrace_log {
    use core::ffi::c_void;
    use crate::abi::{CInt,CULong};
    unsafe extern "C" { static mut process_ptrace_traceme_debug:[crate::debug::Ddebug;3]; }

    /// Preserve the three original ptrace diagnostic selectors and argument types.
    ///
    /// # Safety
    /// Called in the original formatter context. The C descriptors remain live
    /// in __verbose with the same registry update/read discipline; integer and
    /// pointer arguments are only forwarded for formatting and never dereferenced.
    #[no_mangle]
    pub unsafe extern "C" fn process_ptrace_traceme_log_bridge(event:CInt,pid:CInt,value:CULong,error:CInt) {
        let index=match event {
            super::PROCESS_PTRACE_TRACEME_LOG_ENTER=>0,
            super::PROCESS_PTRACE_TRACEME_LOG_PARENT=>1,
            super::PROCESS_PTRACE_TRACEME_LOG_RETURN=>2,
            _=>return,
        };
        // SAFETY: A bounded index selects the persistent original record. Raw
        // addressing and the reviewed packed flags read create no Rust reference.
        unsafe {
            let record=core::ptr::addr_of!(process_ptrace_traceme_debug).cast::<crate::debug::Ddebug>().add(index);
            if core::ptr::read_volatile(core::ptr::addr_of!((*record).line_flags))>>24==0 { return; }
            match index {
                0=>{ let _=super::kprintf(b"ptrace_traceme,pid=%d,proc->parent=%p\n\0".as_ptr().cast(),pid,value as *mut c_void); }
                1=>{ let _=super::kprintf(b"ptrace_traceme,parent->pid=%d\n\0".as_ptr().cast(),pid); }
                _=>{ let _=super::kprintf(b"ptrace_traceme,returning,error=%d\n\0".as_ptr().cast(),error); }
            }
        }
    }
    const _:unsafe extern "C" fn(CInt,CInt,CULong,CInt)=process_ptrace_traceme_log_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_owned_page_offset {
    use core::ffi::c_void;
    use crate::abi::{CLong,OffT};
    /// Read the same live page's signed offset through its owning Rust type.
    ///
    /// # Safety
    /// The caller preserves the original page lifetime, alignment, readable
    /// offset and mapping exclusion. Only the same field value is returned;
    /// this adds no mapping/reference/lock state or post-retirement access.
    #[no_mangle]
    pub unsafe extern "C" fn process_page_offset_bridge(page:*mut c_void)->CLong {
        unsafe { crate::page_helpers::process_page_offset(page.cast::<crate::page_helpers::Page>()) }
    }
    const _:unsafe fn(*const crate::page_helpers::Page)->OffT=crate::page_helpers::process_page_offset;
    const _:unsafe extern "C" fn(*mut c_void)->CLong=process_page_offset_bridge;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_resource_lifecycle {
    use core::ffi::c_void;
    use crate::abi::{AddressSpace,CInt,Process,ProcessVm,Thread};
    /// Release the same VM ranges through their existing Rust lifecycle owner.
    ///
    /// # Safety
    /// The original caller owns the VM/range cleanup transition and keeps VM
    /// live under the existing locks/refcounts; no subsequent range use is added.
    #[no_mangle]
    pub unsafe extern "C" fn process_free_all_ranges_bridge(vm:*mut c_void) {
        unsafe { super::free_all_process_memory_range(vm.cast::<ProcessVm>()) };
    }
    /// Destroy the original page table through the existing architecture entry.
    ///
    /// # Safety
    /// The caller owns the original quiesced page table and has retired its
    /// users under existing address-space synchronization. Backend policy stays.
    #[no_mangle]
    pub unsafe extern "C" fn process_pt_destroy_bridge(page_table:*mut c_void) {
        unsafe { crate::x86_memory_helpers::ihk_mc_pt_destroy(page_table) };
    }
    /// Release the same address-space reference through its existing Rust owner.
    ///
    /// # Safety
    /// The caller owns the same releasable address-space reference and must not
    /// use freed state after its final release; this adds no reference operation.
    #[no_mangle]
    pub unsafe extern "C" fn process_release_address_space_action_bridge(asp:*mut c_void) {
        unsafe { super::release_address_space(asp.cast::<AddressSpace>()) };
    }
    /// Initialize the exact process/parent pair and keep the original zero result.
    ///
    /// # Safety
    /// Creator owns writable process storage and the same live parent relation
    /// accepted by the existing initializer. No rollback or policy is added.
    #[no_mangle]
    pub unsafe extern "C" fn process_init_process_public_bridge(proc:*mut c_void,parent:*mut c_void)->CInt {
        unsafe { super::init_process(proc.cast::<Process>(),parent.cast::<Process>()) };
        0
    }
    /// Enter the original fatal resource-set allocation error with the same text.
    ///
    /// # Safety
    /// Called only in the original fatal initialization context and same panic
    /// contract. The existing Rust panic entry never returns; no new recovery.
    #[no_mangle]
    pub unsafe extern "C" fn process_proc_init_panic_bridge() {
        unsafe { crate::abort::panic(b"no mem for resource_set\0".as_ptr().cast()) }
    }
    /// Preserve the original NUMA initialization diagnostic and ignored id.
    ///
    /// # Safety
    /// The caller preserves the original formatter context; no NUMA state is read
    /// or modified, and the supplied id remains ignored exactly as before.
    #[no_mangle]
    pub unsafe extern "C" fn process_vm_init_numa_log_bridge(_numa_id:CInt) {
        unsafe { let _=super::kprintf(b"%s: error: NUMA id is larger than mask size!\n\0".as_ptr().cast(),b"init_process_vm\0".as_ptr().cast::<i8>()); }
    }
    /// Warn using the same live Thread tid when the existing hold path requests it.
    ///
    /// # Safety
    /// Thread remains nonnull/live/readable under the hold caller's original
    /// exclusion. This reads only its existing tid field and acquires no ref.
    #[no_mangle]
    pub unsafe extern "C" fn process_hold_thread_warn_bridge(thread:*mut c_void) {
        unsafe { let _=super::kprintf(b"hold_thread: WARNING: already exited process,tid=%d\n\0".as_ptr().cast(),(*thread.cast::<Thread>()).tid); }
    }
    const _:unsafe extern "C" fn(*const i8)->! =crate::abort::panic;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_memory_diagnostics {
    use core::ffi::c_void;
    use crate::abi::{CInt,CULong,ProcessVm,SizeT,VmRange};

    /// Preserve the original range-free diagnostic and live range field reads.
    ///
    /// # Safety
    /// The existing caller keeps VM/range live and readable under its mapping
    /// exclusion while formatting; no state/reference/ownership changes here.
    #[no_mangle]
    pub unsafe extern "C" fn process_memory_range_free_log_bridge(vm:*mut ProcessVm,range:*mut VmRange,error:CInt) {
        unsafe { let _=super::kprintf(b"free_process_memory(%p):free range failed. %lx-%lx %d\n\0".as_ptr().cast(),vm,(*range).start,(*range).end,error); }
    }
    /// Preserve the original flush diagnostic and live range field reads.
    ///
    /// # Safety
    /// The same mapping owner keeps VM/range and their endpoints live/readable
    /// during this synchronous formatter call; no new lock/ref or release.
    #[no_mangle]
    pub unsafe extern "C" fn process_flush_memory_log_bridge(vm:*mut ProcessVm,range:*mut VmRange,error:CInt) {
        unsafe { let _=super::kprintf(b"flush_process_memory(%p):free range failed. %lx-%lx %d\n\0".as_ptr().cast(),vm,(*range).start,(*range).end,error); }
    }
    /// Preserve the existing invalidate-range formatter arguments in order.
    ///
    /// # Safety
    /// Called in the original formatter context; VM/range are formatted only,
    /// not dereferenced, and their owner retains the original pointer lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn process_invalidate_range_log_bridge(vm:*mut ProcessVm,range:*mut VmRange,start:CULong,end:CULong,error:CInt) {
        unsafe { let _=super::kprintf(b"invalidate_process_memory_range(%p,%p,%#lx,%#lx):visit failed%d\n\0".as_ptr().cast(),vm,range,start,end,error); }
    }
    /// Preserve the original one-page invalidate failure report and exact types.
    ///
    /// # Safety
    /// The original formatter context/lifetimes apply; raw pointers are forwarded
    /// solely as formatted values and never dereferenced by this adapter.
    #[no_mangle]
    pub unsafe extern "C" fn process_invalidate_one_page_log_bridge(arg0:*mut c_void,page_table:*mut c_void,ptep:*mut c_void,pte_value:CULong,pgaddr:*mut c_void,pgshift:CInt,error:CInt) {
        unsafe { let _=super::kprintf(b"invalidate_one_page(%p,%p,%p %#lx,%p,%d):invalidate failed. %d\n\0".as_ptr().cast(),arg0,page_table,ptep,pte_value,pgaddr,pgshift,error); }
    }
    /// Preserve the existing populate warning and its unsigned size/offset values.
    ///
    /// # Safety
    /// Original synchronous formatter context applies; no page fault, mapping or
    /// dereference is performed and no pointer lifetime or policy is extended.
    #[no_mangle]
    pub unsafe extern "C" fn process_populate_warn_bridge(vm:*mut ProcessVm,addr:CULong,reason:CULong,off:CULong,len:SizeT,error:CInt) {
        unsafe { let _=super::kprintf(b"%s: WARNING: page_fault_process_vm(): vm: %p, addr: %lx, reason: %lx, off: %lu, len: %lu returns %d\n\0".as_ptr().cast(),b"populate_process_memory\0".as_ptr().cast::<i8>(),vm,addr,reason,off,len,error); }
    }
    /// Preserve the existing rejected-request diagnostic and unsigned end wrap.
    ///
    /// # Safety
    /// Called in the original formatter context. VM remains ignored; no access
    /// decision or memory operation occurs. End arithmetic retains C modulo64.
    #[no_mangle]
    pub unsafe extern "C" fn process_access_ok_log_bridge(_vm:*mut ProcessVm,kind:CInt,addr:CULong,len:SizeT,rc:CInt) {
        unsafe { let _=super::kprintf(b"%s: refusing access for request 0x%llx-0x%llx %zu, type=%d, rc=%d\n\0".as_ptr().cast(),b"access_ok\0".as_ptr().cast::<i8>(),addr,addr.wrapping_add(len as CULong),len,kind,rc); }
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// Preserves the existing x86 adapter without retaining or dereferencing the pointer.
/// # Safety
/// The backend performs no memory access or ownership transfer on this architecture.
#[no_mangle]
pub unsafe extern "C" fn process_pte_is_contiguous_bridge(ptep: *mut core::ffi::c_void) -> CInt {
    crate::pte_helpers::pte_is_contiguous(ptep.cast())
}

/// Preserves the existing x86 adapter without retaining or dereferencing the pointer.
/// # Safety
/// The backend performs no memory access or ownership transfer on this architecture.
#[no_mangle]
pub unsafe extern "C" fn process_page_is_contiguous_head_bridge(ptep: *mut core::ffi::c_void, pgsize: SizeT) -> CInt {
    crate::pte_helpers::page_is_contiguous_head(ptep.cast(), pgsize)
}

/// Preserves the existing x86 adapter without retaining or dereferencing the pointer.
/// # Safety
/// The backend performs no memory access or ownership transfer on this architecture.
#[no_mangle]
pub unsafe extern "C" fn process_page_is_contiguous_tail_bridge(ptep: *mut core::ffi::c_void, pgsize: SizeT) -> CInt {
    crate::pte_helpers::page_is_contiguous_tail(ptep.cast(), pgsize)
}

/// Preserves the existing x86 adapter without retaining or dereferencing the pointer.
/// # Safety
/// The backend performs no memory access or ownership transfer on this architecture.
#[no_mangle]
pub unsafe extern "C" fn process_split_contiguous_pages_bridge(ptep: *mut core::ffi::c_void, pgsize: SizeT, memobj_flags: u32) -> CInt {
    unsafe { crate::x86_memory_helpers::split_contiguous_pages(ptep.cast(), pgsize, memobj_flags) }
}

/// Forwards the borrowed page table and optional output, preserving the two
/// deliberately absent lookup outputs. No ownership is transferred.
/// # Safety
/// The caller must satisfy the existing lookup lifetime/mapping requirements;
/// a nonnull pgsizep must remain writable for the synchronous lookup call.
#[no_mangle]
pub unsafe extern "C" fn process_lookup_pte_bridge(
    page_table: *mut core::ffi::c_void,
    addr: CULong,
    pgshift: CInt,
    pgsizep: *mut SizeT,
) -> *mut core::ffi::c_void {
    unsafe {
        crate::x86_memory_helpers::ihk_mc_pt_lookup_pte(
            page_table, addr as *mut core::ffi::c_void, pgshift,
            core::ptr::null_mut(), pgsizep, core::ptr::null_mut(),
        ).cast()
    }
}

/// Retains the original zero-object creation/reference acquisition and pointer
/// comparison. The existing caller retains its historical reference policy.
/// # Safety
/// The zero-object subsystem must satisfy its original initialization/locking
/// preconditions. This function never dereferences or retains memobj itself.
#[no_mangle]
pub unsafe extern "C" fn process_zeroobj_match_bridge(memobj: *mut core::ffi::c_void) -> CInt {
    unsafe {
        let mut obj = core::ptr::null_mut();
        if crate::zeroobj::zeroobj_create(&raw mut obj) != 0 {
            crate::abort::panic(b"DPFP: zeroobj_crate\0".as_ptr().cast());
        }
        (memobj == obj.cast()) as CInt
    }
}

unsafe extern "C" {
    static mut process_page_fault_anon_clear_debug: crate::debug::Ddebug;
    static mut process_page_fault_anon_map_debug: crate::debug::Ddebug;
    static mut process_page_fault_cow_rss_add_debug: crate::debug::Ddebug;
    static mut process_page_fault_cow_rss_sub_debug: crate::debug::Ddebug;
    static mut process_page_fault_set_pte_rss_add_debug: crate::debug::Ddebug;
    static mut process_page_fault_set_pte_rss_skip_debug: crate::debug::Ddebug;
    static mut process_page_fault_set_pte_attr_debug: crate::debug::Ddebug;
    static mut process_page_fault_out_stray_debug: crate::debug::Ddebug;
    static mut process_page_fault_out_rss_sub_debug: crate::debug::Ddebug;
    static mut process_page_fault_out_return_debug: crate::debug::Ddebug;
    static mut process_page_fault_cow_copy_debug: crate::debug::Ddebug;
    static process_page_fault_anon_clear_profile_event: CInt;
}

unsafe extern "C" fn process_fault_set_range_target(
    pt: *mut c_void, vm: *mut ProcessVm, start: *mut c_void, end: *mut c_void,
    phys: CULong, attr: CULong, pgshift: CInt, range: *mut VmRange, overwrite: CInt,
) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_set_range(
        pt, vm.cast(), start, end, phys, attr, pgshift, range.cast(), overwrite,
    ) }
}

/// Complete original page-fault orchestration over the existing Rust substeps.
/// # Safety
/// vm/range and their borrowed page table/object state must remain live under
/// the original caller's VM lock. Prepare takes the page-table lock. Every
/// nonfatal early exit calls out exactly once; install_finish owns final unlock.
/// Zero-object creation retains its original reference policy. Allocated pages
/// and mapped references retain the existing substeps' transfer/unwind rules.
#[no_mangle]
pub unsafe extern "C" fn page_fault_process_memory_range(
    vm: *mut ProcessVm, range: *mut VmRange, fault_addr: CULong, reason: CULong,
) -> CInt {
    unsafe {
        let mut ptep = core::ptr::null_mut();
        let mut pgaddr = core::ptr::null_mut();
        // Early prepare errors historically leave size uninitialized. The out
        // helper never reads it while page is null; keep that exact contract.
        let mut pgsize = core::mem::MaybeUninit::<SizeT>::uninit();
        let mut p2align = 0;
        let mut error = 0;
        let mut phys = 0;
        let mut page = core::ptr::null_mut();
        let mut memobj_flag = 0;
        process_page_fault_entry_log_body_result(vm, range, fault_addr, reason);
        'fault: {
            if process_page_fault_prepare_body_result(vm, range, fault_addr, reason,
                &raw mut ptep, &raw mut pgaddr, pgsize.as_mut_ptr(),
                &raw mut p2align, &raw mut error) != 0 { break 'fault; }
            process_page_fault_pte_state_log_bridge(ptep, pgsize.assume_init());
            if ptep.is_null() || crate::pte_helpers::pte_is_null(ptep) != 0
                || crate::pte_helpers::pte_is_fileoff(ptep, pgsize.assume_init()) != 0 {
                if process_page_fault_memobj_get_body_result(range, pgaddr,
                    fault_addr, ptep, pgsize.assume_init(), p2align,
                    &raw mut phys, &raw mut memobj_flag, &raw mut error) != 0 {
                    let mut obj = core::ptr::null_mut();
                    if crate::zeroobj::zeroobj_create(&raw mut obj) != 0 {
                        crate::abort::panic(b"PFPMR: zeroobj_crate\0".as_ptr().cast());
                    }
                    if (*range).memobj != obj.cast() { break 'fault; }
                }
                if phys == !0_u64 {
                    let mut virt = core::ptr::null_mut();
                    if process_page_fault_anon_allocate_body_result(vm, range,
                        fault_addr, reason, &raw mut ptep, &raw mut pgaddr,
                        pgsize.as_mut_ptr(), &raw mut p2align,
                        &raw mut virt, &raw mut error) != 0 { break 'fault; }
                    process_page_fault_anon_clear_body_result(range, pgaddr,
                        pgsize.assume_init(), virt, page, fault_addr, reason,
                        &raw mut phys, cfg!(enable_profile) as CInt,
                        process_page_fault_anon_clear_profile_event,
                        &raw mut process_page_fault_anon_clear_debug,
                        &raw mut process_page_fault_anon_map_debug);
                }
            } else { phys = process_pte_get_phys_bridge(ptep.cast()); }
            let mut attr = process_page_fault_mapping_state_body_result(range,
                phys, memobj_flag, reason, ptep, &raw mut page);
            if process_page_fault_cow_classify_body_result(range, reason, page.cast()) != 0 {
                if process_page_fault_cow_dirty_permission_body_result(&raw mut attr) != 0 {
                    let mut virt = core::ptr::null_mut();
                    if process_page_fault_cow_allocate_body_result(vm, range, page,
                        pgsize.assume_init(), p2align, fault_addr, reason,
                        &raw mut virt, &raw mut error) != 0 { break 'fault; }
                    if core::ptr::read_volatile(&raw const process_page_fault_cow_copy_debug.line_flags) >> 24 != 0 {
                        let _ = kprintf(b"%s: cow,copying virt:%lx<-%lx,phys:%lx<-%lx,pgsize=%lu\n\0".as_ptr().cast(),
                            b"page_fault_process_memory_range\0".as_ptr().cast::<i8>(),
                            virt, crate::x86_memory_helpers::phys_to_virt(phys),
                            crate::x86_memory_helpers::virt_to_phys(virt), phys,
                            pgsize.assume_init());
                    }
                    process_page_fault_cow_copy_body_result(virt, phys, pgsize.assume_init());
                    process_page_fault_cow_commit_body_result(range, &raw mut phys,
                        pgsize.assume_init(), virt, &raw mut page,
                        &raw mut process_page_fault_cow_rss_add_debug,
                        &raw mut process_page_fault_cow_rss_sub_debug);
                }
            } else { attr = process_page_fault_shared_permission_body_result(range, attr); }
            return process_page_fault_install_finish_body_result(vm, range,
                fault_addr, reason, ptep, pgaddr, pgsize.assume_init(), phys,
                attr, page, crate::x86_memory_helpers::ihk_mc_pt_set_pte,
                process_fault_set_range_target,
                &raw mut process_page_fault_set_pte_rss_add_debug,
                &raw mut process_page_fault_set_pte_rss_skip_debug,
                &raw mut process_page_fault_set_pte_attr_debug,
                &raw mut process_page_fault_out_stray_debug,
                &raw mut process_page_fault_out_rss_sub_debug,
                &raw mut process_page_fault_out_return_debug);
        }
        process_page_fault_out_body_result(vm, range, fault_addr, reason,
            pgsize.as_ptr(), page, error, &raw mut process_page_fault_out_stray_debug,
            &raw mut process_page_fault_out_rss_sub_debug,
            &raw mut process_page_fault_out_return_debug)
    }
}

mod remaining_free_range_entry {
    use super::*;
    use super::remaining_process_free_range_providers as providers;
    unsafe extern "C" {
        static process_tracked_allocator_source_file: *const i8;
        static process_free_range_pages_source_line: CInt;
        static mut process_free_range_body_debug: [crate::debug::Ddebug; 3];
        #[cfg(enable_tofu)]
        fn tofu_stag_range_remove_overlapping(vm: *mut ProcessVm, range: *mut VmRange) -> CInt;
    }

    // Raw bounded descriptor addresses avoid references to mutable C metadata.
    unsafe fn enabled(index: usize) -> bool {
        let descriptor = core::ptr::addr_of_mut!(process_free_range_body_debug)
            .cast::<crate::debug::Ddebug>().add(index);
        core::ptr::read_volatile(core::ptr::addr_of!((*descriptor).line_flags)) >> 24 != 0
    }

    /// Original tracked release; the backend retains null/locking/free policy.
    /// # Safety
    /// The caller owns the same final live page span and excludes later accesses.
    unsafe extern "C" fn free_pages(addr: *mut c_void, pages: CULong) {
        unsafe { crate::mem_helpers::_ihk_mc_free_pages(addr, pages as CInt, 0,
            process_tracked_allocator_source_file.cast_mut(),
            process_free_range_pages_source_line); }
    }

    /// Original callback formats and argument order, with no retained pointers.
    /// # Safety
    /// Events2/3 require a live range; other events preserve original null use.
    unsafe extern "C" fn log(event: CInt, vm: *mut ProcessVm, range: *mut VmRange,
        start: CULong, end: CULong, error: CInt) {
        unsafe { match event {
            PROCESS_FREE_BODY_LOG_PLAN_FAILED => { let _ = kprintf(
                b"free_process_memory_range:arch_get_smaller_page_size failed. %d\n\0".as_ptr().cast(), error); }
            PROCESS_FREE_BODY_LOG_PT_FREE_FAILED => { let _ = kprintf(
                b"free_process_memory_range(%p,%lx-%lx):ihk_mc_pt_free_range(%lx-%lx,%p) failed. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, start, end, (*range).memobj, error); }
            PROCESS_FREE_BODY_LOG_PT_CLEAR_FAILED => { let _ = kprintf(
                b"free_process_memory_range(%p,%lx-%lx):ihk_mc_pt_clear_range(%lx-%lx) failed. %d\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, start, end, error); }
            PROCESS_FREE_BODY_LOG_TOFU_REMOVED if enabled(0) => { let _ = kprintf(
                b"%s: removed %d Tofu stag entries for range 0x%lx:%lu\n\0".as_ptr().cast(),
                b"process_free_range_log_bridge\0".as_ptr().cast::<i8>(), error, start, end.wrapping_sub(start)); }
            PROCESS_FREE_BODY_LOG_FINALIZE_FAILED => { let _ = kprintf(
                b"free_process_memory_range(%p,%lx-%lx):finalize failed. %d\n\0".as_ptr().cast(), vm, start, end, error); }
            PROCESS_FREE_BODY_LOG_DONE if enabled(1) => { let _ = kprintf(
                b"free_process_memory_range(%p,%lx-%lx): 0\n\0".as_ptr().cast(), vm, start, end); }
            _ => {}
        } }
    }

    /// Complete existing free-range entry, preserving callback/ownership policy.
    /// # Safety
    /// vm/range/process stay live under original range exclusion. The existing
    /// body owns lock/unlock, range release and error handling; no references
    /// cross its callbacks, and this entry never accesses range after release.
    #[no_mangle]
    pub unsafe extern "C" fn process_memory_range_free_bridge(vm_arg: *mut c_void,
        range_arg: *mut c_void) -> CInt {
        unsafe {
            let vm = vm_arg.cast::<ProcessVm>();
            let range = range_arg.cast::<VmRange>();
            if enabled(2) { let _ = kprintf(
                b"free_process_memory_range(%p, 0x%lx - 0x%lx)\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end); }
            #[cfg(enable_tofu)]
            let (tofu_enabled, tofu_callback) = ((*(*vm).proc.cast::<Process>()).enable_tofu,
                Some(tofu_stag_range_remove_overlapping as ProcessFreeRangeTofuRemoveFn));
            #[cfg(not(enable_tofu))]
            let (tofu_enabled, tofu_callback) = (0, None);
            process_free_memory_range_body_result(vm, range,
                (*(*vm).proc.cast::<Process>()).straight_va as CULong,
                core::ptr::addr_of_mut!((*(*vm).proc.cast::<Process>()).straight_len),
                (*(*vm).proc.cast::<Process>()).straight_pa, tofu_enabled,
                Some(providers::process_free_range_page_size_bridge),
                Some(process_free_range_noirq_lock_bridge),
                Some(process_free_range_noirq_unlock_bridge), None, None,
                Some(process_free_range_pt_free_bridge),
                Some(providers::process_free_range_pt_clear_bridge), tofu_callback,
                Some(providers::process_free_range_phys_to_virt_bridge),
                Some(free_pages), Some(providers::process_free_range_clear_main_bridge),
                Some(process_range_kfree_bridge), Some(log))
        }
    }
}

use remaining_free_range_entry::process_memory_range_free_bridge;

mod remaining_process_idle_context {
    use super::*;
    unsafe extern "C" {
        static process_idle_offsets: crate::sched_helpers::SchedIdleOffsets;
        static process_idle_values: crate::sched_helpers::SchedIdleValues;
        static process_idle_callbacks: crate::sched_helpers::SchedIdleCallbacks;
        fn ihk_mc_init_context(context: *mut crate::abi::X86KernelContext,
            stack: *mut c_void, entry: Option<unsafe extern "C" fn()>);
    }

    /// Enter the existing Rust idle loop with the same captured CPU/monitor.
    /// # Safety
    /// This runs in the original per-CPU idle context for its entire lifetime.
    /// The static geometry/values/callbacks and CPU/monitor storage remain live;
    /// the existing loop retains its original IRQ/runqueue and halt obligations.
    #[no_mangle]
    pub unsafe extern "C" fn process_idle_entry() {
        unsafe {
            let local = get_this_cpu_local_var();
            let monitor = (*local).monitor;
            crate::sched_helpers::sched_idle_loop_body_result(local as usize,
                monitor as usize, core::ptr::addr_of!(process_idle_offsets),
                core::ptr::addr_of!(process_idle_values),
                core::ptr::addr_of!(process_idle_callbacks));
        }
    }

    /// Prepare the same Thread.ctx with NULL stack and the idle entry callback.
    /// # Safety
    /// thread_arg is the original live writable Thread under creator exclusion.
    /// No reference crosses the context provider; it retains all stack/context
    /// initialization policy. This adapter neither switches contexts nor frees.
    #[no_mangle]
    pub unsafe extern "C" fn process_sched_init_context_bridge(thread_arg: *mut c_void) {
        let thread = thread_arg.cast::<Thread>();
        unsafe { ihk_mc_init_context(core::ptr::addr_of_mut!((*thread).ctx),
            core::ptr::null_mut(), Some(process_idle_entry)); }
    }
}

mod remaining_process_timer_adapters {
    use super::*;
    /// Same IRQ-save spin-lock boundary, without an extra lock or IRQ operation.
    /// # Safety
    /// lock_addr is the original live aligned writable ticket lock, in the
    /// original IRQ context with its existing pairing/ownership contract.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_spin_lock_bridge(lock_addr: CULong) -> CULong {
        unsafe { super::process_spin_lock_bridge(lock_addr) }
    }
    /// Preserve the exact saved IRQ state of the paired original lock.
    /// # Safety
    /// The original caller holds the same lock and provides its saved state.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_spin_unlock_bridge(lock_addr: CULong, irqstate: CULong) {
        unsafe { super::process_spin_unlock_bridge(lock_addr, irqstate); }
    }
    /// Forward the original unsigned32 clocks to the existing timer code.
    /// # Safety
    /// The existing LAPIC/CPU privilege and MMIO mapping contract applies.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_lapic_enable_bridge(clocks: u32) {
        unsafe { crate::x86_cpu_helpers::lapic_timer_enable(clocks); }
    }
    /// Invoke the original disable once without changing timer policy.
    /// # Safety
    /// The existing LAPIC/CPU privilege and MMIO mapping contract applies.
    #[no_mangle]
    pub unsafe extern "C" fn process_timer_lapic_disable_bridge() {
        unsafe { crate::x86_cpu_helpers::lapic_timer_disable(); }
    }
}

mod remaining_process_page_table_shm_adapters {
    use core::ffi::c_void;

    use crate::abi::{CInt, CLong, CULong, Memobj, ProcessVm, VmRange};

    /// Preserve the existing architecture attribute conversion and PTE input.
    /// # Safety
    /// The original page-table owner keeps ptep live and aligned under the
    /// original VM/page-table lock and architecture provider's read contract.
    #[no_mangle]
    pub unsafe extern "C" fn process_update_page_table_attr_bridge(
        flag: CULong, fault: CULong, ptep: *mut c_void,
    ) -> CULong {
        unsafe { crate::x86_memory_helpers::arch_vrflag_to_ptattr(flag, fault, ptep.cast()) }
    }

    /// Reuse the complete set-range implementation with unchanged integer bits.
    /// # Safety
    /// The original caller owns the page-table/VM locks and keeps vm, range and
    /// all mapping inputs live throughout the synchronous traversal. No pointer
    /// or borrowed Rust reference is retained by this forwarding adapter.
    #[no_mangle]
    pub unsafe extern "C" fn process_update_page_table_set_range_bridge(
        page_table: *mut c_void, vm: *mut ProcessVm, start: CULong, end: CULong,
        phys: CULong, attr: CULong, pgshift: CInt, range: *mut VmRange, flags: CInt,
    ) -> CInt {
        unsafe {
            crate::x86_memory_helpers::ihk_mc_pt_set_range(
                page_table, vm.cast(), start as *mut c_void, end as *mut c_void,
                phys, attr, pgshift, range.cast(), flags,
            )
        }
    }

    /// Emit the original format and signed error without changing log policy.
    /// # Safety
    /// The original kernel logging context and kprintf synchronization apply.
    #[no_mangle]
    pub unsafe extern "C" fn process_update_page_table_log_bridge(error: CInt) {
        // SAFETY: The format is static NUL-terminated storage; its sole vararg is int.
        unsafe {
            let _ = super::kprintf(
                b"update_process_page_table:ihk_mc_pt_set_range failed. %d\n\0".as_ptr().cast(),
                error,
            );
        }
    }

    /// Dispatch the same optional memobj lookup operation and out parameters.
    /// # Safety
    /// The original owner keeps obj and its ops table live and synchronized.
    /// Both output pointers obey the original callback's alignment/writability
    /// contract; no reference is added and no callback or output pointer escapes.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_shm_lookup_page_bridge(
        obj: *mut Memobj, off: CLong, p2align: CInt,
        physp: *mut CULong, pflag: *mut CULong,
    ) -> CInt {
        unsafe { crate::object_helpers::memobj_lookup_page(obj, off, p2align, physp, pflag) }
    }

    /// Return the original borrowed page pointer without acquiring a reference.
    /// # Safety
    /// The original caller keeps hash storage and returned page storage live
    /// under the existing lookup-lock and mapping-ownership contract.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_shm_phys_to_page_bridge(phys: CULong) -> *mut c_void {
        unsafe { crate::mem_helpers::phys_to_page(phys).cast() }
    }

    /// Dispatch the same optional update operation with unchanged raw pointers.
    /// # Safety
    /// obj and its ops table remain live under the original synchronization;
    /// page_table, page and vaddr satisfy that callback's synchronous lifetime
    /// and mapping contract. This adapter creates no reference or ownership.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_shm_update_page_bridge(
        obj: *mut Memobj, page_table: *mut c_void, page: *mut c_void, vaddr: *mut c_void,
    ) -> CInt {
        unsafe { crate::object_helpers::memobj_update_page(obj, page_table, page, vaddr) }
    }
}

mod remaining_process_split_range_providers {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong, ProcessVm, VmRange};

    unsafe extern "C" {
        static process_tracked_allocator_source_file: *const i8;
        static process_split_range_alloc_source_line: CInt;
    }

    /// Preserve the original allocator's int narrowing and tracked call site.
    /// # Safety
    /// The original caller obeys the allocator flags/context contract and owns
    /// initialization, publication and eventual release of a non-null result.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_alloc_bridge(
        size: CULong, flags: CULong,
    ) -> *mut VmRange {
        unsafe {
            crate::mem_helpers::kmalloc_tracked(
                size as CInt, flags, process_tracked_allocator_source_file.cast_mut(),
                process_split_range_alloc_source_line,
            ).cast()
        }
    }

    /// Preserve allocation-error reporting without retaining caller storage.
    /// # Safety
    /// range is live and readable under the original VM range exclusion;
    /// vm and splitp are only formatted as raw pointers in the original context.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_alloc_log_bridge(
        vm: *mut ProcessVm, range: *mut VmRange, addr: CULong, splitp: *mut c_void,
    ) {
        unsafe {
            let _ = super::kprintf(
                b"split_process_memory_range(%p,%lx-%lx,%lx,%p):kmalloc failed\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, addr, splitp,
            );
        }
    }

    /// Preserve the public insertion-error format and signed status.
    /// # Safety
    /// The original kernel logging context and synchronization apply.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_publish_log_bridge(error: CInt) {
        unsafe {
            let _ = super::kprintf(
                b"%s: ERROR: could not insert range: %d\n\0".as_ptr().cast(),
                b"split_process_memory_range\0".as_ptr().cast::<i8>(), error,
            );
        }
    }

    /// Reuse the complete existing page-table split with the original pointers.
    /// # Safety
    /// The original caller holds VM/page-table exclusion and keeps vm/range
    /// and their backing memobj/mapping live throughout the synchronous split.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_pt_split_bridge(
        page_table: *mut c_void, vm: *mut ProcessVm, range: *mut VmRange, addr: *mut c_void,
    ) -> CInt {
        unsafe { crate::x86_memory_helpers::ihk_mc_pt_split(page_table, vm, range, addr) }
    }

    /// Preserve page-table split-error reporting and int vararg promotion.
    /// # Safety
    /// The original kernel logging context and synchronization apply.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_pt_log_bridge(error: CInt) {
        unsafe {
            let _ = super::kprintf(
                b"split_process_memory_range:ihk_mc_pt_split failed. %d\n\0".as_ptr().cast(), error,
            );
        }
    }

    /// Preserve both shared-memory errors and the silent unknown-event path.
    /// # Safety
    /// The original kernel logging context and synchronization apply.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_shm_log_bridge(event: CInt, error: CInt) {
        unsafe {
            let format: &[u8] = match event {
                super::PROCESS_SPLIT_SHM_LOG_LOOKUP_FAILED =>
                    b"%s: memobj_lookup_page failed. %d\n\0",
                super::PROCESS_SPLIT_SHM_LOG_UPDATE_FAILED =>
                    b"%s: memobj_update_page failed. %d\n\0",
                _ => return,
            };
            let _ = super::kprintf(format.as_ptr().cast(),
                b"split_process_memory_range\0".as_ptr().cast::<i8>(), error);
        }
    }

    /// Publish through the existing tree implementation without a new policy.
    /// # Safety
    /// The original caller holds the VM range writer exclusion and owns the
    /// live range's insertion and lifetime; the backend retains duplicate rules.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_insert_bridge(
        vm: *mut ProcessVm, range: *mut VmRange,
    ) -> CInt {
        unsafe { super::vm_range_insert(vm, range) }
    }
}

mod remaining_process_schedule_entry {
    use core::ffi::c_void;
    use core::mem::MaybeUninit;
    use core::sync::atomic::{AtomicI32, AtomicU32, Ordering};

    use crate::abi::{CInt, CULong, CpuLocalVar, IhkSpinlock, Thread, X86UserContext};
    use crate::sched_helpers::{SchedExitDebug, SchedRunqueueOffsets, SchedScheduleResult};

    unsafe extern "C" {
        static process_sched_runqueue_offsets: SchedRunqueueOffsets;
        static mut process_schedule_switch_debug: crate::debug::Ddebug;
        static process_schedule_exit_debug_input: *const SchedExitDebug;
        fn restore_fp_regs(thread: *mut Thread);
        fn arch_switch_context(prev: *mut Thread, next: *mut Thread) -> *mut Thread;
        fn ihk_mc_load_page_table(table: *mut c_void);
        fn arch_flush_icache_all();
        fn ihk_mc_syscall_pc(context: *const X86UserContext) -> CULong;
        fn ihk_mc_syscall_sp(context: *const X86UserContext) -> CULong;
        fn process_sched_runq_log_bridge(
            event: CInt, arg0: usize, arg1: usize, arg2: CInt, arg3: CInt,
        );
    }

    // The current real x86_64 ABI uses equal-width usize and unsigned long.
    // Keep distinct Rust callback types explicit instead of transmuting them.
    const _: [(); core::mem::size_of::<usize>()] = [(); core::mem::size_of::<CULong>()];

    unsafe extern "C" fn prepare_noirq_lock(addr: usize) {
        // SAFETY: The original preparation owns this live aligned runqueue lock.
        unsafe { super::process_sched_noirq_lock_bridge(addr as CULong); }
    }

    unsafe extern "C" fn prepare_noirq_unlock(addr: usize) {
        // SAFETY: Preparation holds the same lock and retains its pairing scope.
        unsafe { super::process_sched_noirq_unlock_bridge(addr as CULong); }
    }

    unsafe extern "C" fn prepare_has_signal(addr: usize) -> CInt {
        // SAFETY: Preparation keeps the original Thread/signal state live.
        unsafe { super::process_sched_has_signal_bridge(addr as CULong) }
    }

    // Per-CPU runqueue locks do not serialize this global diagnostic budget.
    // Reserve a slot before logging. Relaxed ordering coordinates only the
    // budget; this counter never publishes thread, VM or context state.
    static MCEXEC_V10_SCHEDULER_LOGS: AtomicU32 = AtomicU32::new(0);
    const _: [(); 4] = [(); core::mem::size_of::<AtomicU32>()];
    const _: [(); 4] = [(); core::mem::align_of::<AtomicU32>()];

    fn claim_scheduler_log_slot() -> bool {
        let mut observed = MCEXEC_V10_SCHEDULER_LOGS.load(Ordering::Relaxed);
        while observed < 32 {
            match MCEXEC_V10_SCHEDULER_LOGS.compare_exchange_weak(
                observed, observed + 1, Ordering::Relaxed, Ordering::Relaxed,
            ) {
                Ok(_) => return true,
                Err(actual) => observed = actual,
            }
        }
        false
    }

    /// Complete the original scheduler orchestration around the existing Rust
    /// admission, preparation, debug-register handoff and exit cleanup.
    ///
    /// # Safety
    /// Enter only in the original scheduler context. IRQ admission pins the
    /// live FP owner before runqueue mutation. Preparation either releases its
    /// exclusion or returns SWITCH while holding the runqueue lock. prev/next,
    /// their process/VM/address-space/context storage remain live through the
    /// architecture switch. That backend may resume on a different CPU; unlock
    /// and IRQ restoration must use fresh current-CPU pointers, while cleanup
    /// receives the original CPU pointer and owns last's release. No Rust
    /// reference spans a callback, context switch or release.
    #[no_mangle]
    pub unsafe extern "C" fn schedule() {
        unsafe {
            let irqstate = crate::sched_helpers::sched_schedule_fp_admit(super::PS_EXITED);
            let mut result = MaybeUninit::<SchedScheduleResult>::uninit();
            let action = crate::sched_helpers::sched_schedule_prepare_body_result(
                super::get_this_cpu_local_var() as usize,
                core::ptr::addr_of_mut!((*super::get_this_cpu_local_var()).idle) as usize,
                AtomicI32::from_ptr(core::ptr::addr_of_mut!(
                    (*super::get_this_cpu_local_var()).no_preempt.counter
                )).load(Ordering::SeqCst),
                1, 2, 1, 2, super::PS_EXITED, 1001, 1, 3,
                core::ptr::addr_of!(process_sched_runqueue_offsets), result.as_mut_ptr(),
                Some(super::process_sched_irq_save_bridge),
                Some(super::process_sched_irq_restore_bridge),
                Some(prepare_noirq_lock),
                Some(prepare_noirq_unlock),
                Some(super::process_sched_set_timer_bridge),
                Some(super::process_sched_reset_cputime_bridge),
                Some(prepare_has_signal),
                Some(process_sched_runq_log_bridge),
            );
            if action != 3 {
                super::cpu_restore_interrupt(irqstate);
                return;
            }
            // Preparation initializes every result field before returning SWITCH.
            let result = result.assume_init();
            let old_cpu = result.cpu_addr as *mut CpuLocalVar;
            (*old_cpu).runq_irqstate = irqstate;
            let prev = result.prev_thread_addr as *mut Thread;
            let next = result.next_thread_addr as *mut Thread;
            let prevpid = result.prevpid;
            if core::ptr::read_volatile(core::ptr::addr_of!(
                process_schedule_switch_debug.line_flags
            )) >> 24 != 0 {
                let _ = super::kprintf(
                    b"%s: %d => %d [ctx sws: %lu]\n\0".as_ptr().cast(),
                    b"schedule\0".as_ptr().cast::<i8>(),
                    if prev.is_null() { 0 } else { (*prev).tid },
                    if next.is_null() { 0 } else { (*next).tid },
                    (*super::get_this_cpu_local_var()).nr_ctx_switches,
                );
            }
            if !next.is_null()
                && next != core::ptr::addr_of_mut!((*super::get_this_cpu_local_var()).idle)
                && claim_scheduler_log_slot()
            {
                let _ = super::kprintf(
                    b"mcexec_v10: scheduler switch cpu=%d %d=>%d pid=%d rip=0x%lx sp=0x%lx status=%d runq_len=%d\n\0".as_ptr().cast(),
                    super::ihk_mc_get_processor_id(),
                    if prev.is_null() { -1 } else { (*prev).tid }, (*next).tid,
                    if (*next).proc.is_null() { -1 } else { (*(*next).proc).pid },
                    if (*next).uctx.is_null() { 0 } else { ihk_mc_syscall_pc((*next).uctx) },
                    if (*next).uctx.is_null() { 0 } else { ihk_mc_syscall_sp((*next).uctx) },
                    (*next).status, (*old_cpu).runq_len,
                );
            }
            crate::sched_helpers::sched_schedule_debug_handoff(prev, next);
            if next != core::ptr::addr_of_mut!((*super::get_this_cpu_local_var()).idle) {
                restore_fp_regs(next);
            }
            if !prev.is_null()
                && (*(*(*prev).vm).address_space).page_table
                    != (*(*(*next).vm).address_space).page_table
            {
                ihk_mc_load_page_table((*(*(*next).vm).address_space).page_table);
            }
            if !prev.is_null() && (*prev).proc != (*next).proc
                && next != core::ptr::addr_of_mut!((*super::get_this_cpu_local_var()).idle)
                && (prevpid != (*(*next).proc).pid
                    || prev != core::ptr::addr_of_mut!((*super::get_this_cpu_local_var()).idle))
            {
                arch_flush_icache_all();
            }
            let last = arch_switch_context(prev, next);
            // Reacquire CURRENT after a possibly migrating switch. Do not use
            // old_cpu for this lock address or its separately captured IRQ state.
            super::process_sched_noirq_unlock_bridge(core::ptr::addr_of_mut!(
                (*super::get_this_cpu_local_var()).runq_lock
            ) as CULong);
            super::cpu_restore_interrupt((*super::get_this_cpu_local_var()).runq_irqstate);
            crate::sched_helpers::sched_schedule_exit_cleanup(
                old_cpu, last, super::PS_EXITED, process_schedule_exit_debug_input,
            );
            // The original final old/current comparison has no external effect;
            // it performs no accesses to last or released thread storage.
        }
    }
}

mod remaining_process_memory_forwarding {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong, CpuSet, ProcessVm, SizeT, VmRange};

    type SmpHandler = unsafe extern "C" fn(CInt, CInt, *mut c_void) -> CInt;
    const _: [(); core::mem::size_of::<SmpHandler>()] =
        [(); core::mem::size_of::<*mut c_void>()];

    /// Return the existing architecture translation without changing mapping policy.
    /// # Safety
    /// phys lies in the original supported physical mapping domain; the caller
    /// retains the mapping/storage lifetime and dereference obligations.
    #[no_mangle]
    pub unsafe extern "C" fn process_memset_smp_phys_to_virt_bridge(phys: CULong) -> *mut c_void {
        unsafe { crate::x86_memory_helpers::phys_to_virt(phys) }
    }

    unsafe extern "C" {
        static process_memset_smp_fast_word_pattern: CInt;
    }

    /// Fill exactly the original span using its actual C-header-selected provider.
    /// # Safety
    /// addr identifies len writable bytes under the original memory ownership
    /// and exclusion. This creates no reference and touches nothing for len=0.
    #[no_mangle]
    pub unsafe extern "C" fn process_memset_smp_memset_bridge(
        addr: *mut c_void, value: CInt, len: SizeT,
    ) {
        unsafe {
            if process_memset_smp_fast_word_pattern != 0 {
                let _ = crate::string::__inline_memset(addr, value as CULong, len);
            } else {
                let _ = crate::string::memset(addr, value, len);
            }
        }
    }

    /// Preserve the existing reverse architecture translation.
    /// # Safety
    /// addr obeys the original supported virtual mapping domain and lifetime.
    #[no_mangle]
    pub unsafe extern "C" fn process_memset_smp_virt_to_phys_bridge(addr: *mut c_void) -> CULong {
        unsafe { crate::x86_memory_helpers::virt_to_phys(addr) }
    }

    /// Forward the original synchronous SMP request to its existing Rust owner.
    /// # Safety
    /// cpu_set is the original live aligned CpuSet or original null input.
    /// Non-null handler is a genuine current-target C function pointer with the
    /// SmpHandler signature, as supplied by memset_smp_handler. arg and all
    /// request storage remain live through the synchronous backend completion;
    /// this adapter neither retains them nor changes callback/rejection policy.
    #[no_mangle]
    pub unsafe extern "C" fn process_memset_smp_call_bridge(
        cpu_set: *mut c_void, handler: *mut c_void, arg: *mut c_void,
    ) -> CInt {
        unsafe {
            let callback = if handler.is_null() {
                None
            } else {
                // SAFETY: The original C (smp_func_t) cast has this same
                // caller-provided callable signature and target representation.
                Some(core::mem::transmute::<*mut c_void, SmpHandler>(handler))
            };
            crate::ap::smp_call_func(cpu_set.cast::<CpuSet>(), callback, arg)
        }
    }

    /// Use the existing VM tree insertion without a new ownership rule.
    /// # Safety
    /// vm/range are live under the original VM range writer exclusion; the
    /// original caller owns publication and the existing backend's error path.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_insert_bridge(
        vm: *mut ProcessVm, range: *mut VmRange,
    ) -> CInt {
        unsafe { super::vm_range_insert(vm, range) }
    }

    /// Preserve page-table update flags and signed error forwarding.
    /// # Safety
    /// vm/range and backing address space stay live under original VM/PT
    /// exclusion throughout the synchronous existing update implementation.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_update_bridge(
        vm: *mut ProcessVm, range: *mut VmRange, phys: CULong, attr: CULong,
    ) -> CInt {
        unsafe { super::update_process_page_table(vm, range, phys, attr) }
    }

    /// Retain the original discarded removal status and NULL accounting output.
    /// # Safety
    /// The existing owner provides a live VM/process and original range writer
    /// exclusion. The backend owns removal, storage release and all field use;
    /// this adapter performs no access to removed ranges after its return.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_remove_bridge(
        vm: *mut ProcessVm, start: CULong, end: CULong,
    ) {
        unsafe { let _ = super::remove_process_memory_range(vm, start, end, core::ptr::null_mut()); }
    }

    /// Preserve the existing split result and caller-owned range output.
    /// # Safety
    /// vm/range and splitp obey the original range writer/initialization
    /// contract; splitp is writable when required by the existing core. No
    /// callback or pointer escapes and no extra reference/allocation is added.
    #[no_mangle]
    pub unsafe extern "C" fn process_remove_range_split_bridge(
        vm: *mut ProcessVm, range: *mut VmRange, addr: CULong, splitp: *mut *mut VmRange,
    ) -> CInt {
        unsafe { super::split_process_memory_range(vm, range, addr, splitp) }
    }
}

mod remaining_process_range_page_table_providers {
    use core::ffi::c_void;

    use crate::abi::{CInt, CULong, ProcessVm};

    type VisitPte = unsafe extern "C" fn(
        *mut c_void, *mut c_void, *mut CULong, *mut c_void, CInt,
    ) -> CInt;
    const _: [(); core::mem::size_of::<VisitPte>()] =
        [(); core::mem::size_of::<*mut c_void>()];

    /// Preserve the existing architecture conversion and original PTE input.
    /// # Safety
    /// The original owner keeps ptep live/aligned under its existing VM/PT
    /// exclusion and architecture conversion provider's read contract.
    #[no_mangle]
    pub unsafe extern "C" fn process_change_prot_attr_bridge(
        flag: CULong, fault: CULong, ptep: *mut c_void,
    ) -> CULong {
        unsafe { crate::x86_memory_helpers::arch_vrflag_to_ptattr(flag, fault, ptep.cast()) }
    }

    /// Reuse the complete page-table attribute change without a new policy.
    /// # Safety
    /// page_table and every reached mapping remain live and correctly owned
    /// under the original VM/PT locks; raw start/end bits keep their old domain.
    #[no_mangle]
    pub unsafe extern "C" fn process_change_prot_pt_change_bridge(
        page_table: *mut c_void, start: CULong, end: CULong,
        clrattr: CULong, setattr: CULong,
    ) -> CInt {
        unsafe {
            crate::x86_memory_helpers::ihk_mc_pt_change_attr_range(
                page_table, start as *mut c_void, end as *mut c_void, clrattr, setattr,
            )
        }
    }

    /// Retain the original typed synchronous page-table visitor boundary.
    /// # Safety
    /// The original owner holds traversal/mapping exclusion and keeps the
    /// table and arg storage live through synchronous completion. A non-null
    /// visit_fn is a genuine current-target C function pointer of VisitPte's
    /// exact signature; null preserves the existing backend rejection policy.
    #[no_mangle]
    pub unsafe extern "C" fn process_visit_pte_range_bridge(
        page_table: *mut c_void, start: CULong, end: CULong,
        pgshift: CInt, flags: CInt, visit_fn: *mut c_void, arg: *mut c_void,
    ) -> CInt {
        unsafe {
            let visitor = if visit_fn.is_null() {
                None
            } else {
                // SAFETY: Same original C callback cast, with its callable
                // target representation and signature retained by the caller.
                Some(core::mem::transmute::<*mut c_void, VisitPte>(visit_fn))
            };
            crate::x86_memory_helpers::visit_pte_range(
                page_table, start as *mut c_void, end as *mut c_void,
                pgshift, flags, visitor, arg,
            )
        }
    }

    /// Preserve deferred freeing by invoking only the existing clear backend.
    /// # Safety
    /// The original owner keeps vm/table/mappings live under VM/PT exclusion.
    /// The backend retains clearing/accounting policy; this adapter adds no
    /// reference/free and does not access cleared storage after completion.
    #[no_mangle]
    pub unsafe extern "C" fn process_remove_region_clear_bridge(
        page_table: *mut c_void, vm: *mut ProcessVm, start: CULong, end: CULong,
    ) -> CInt {
        unsafe {
            crate::x86_memory_helpers::ihk_mc_pt_clear_range(
                page_table, vm, start as *mut c_void, end as *mut c_void,
            )
        }
    }
}

mod remaining_process_range_cleanup_panic {
    use crate::abi::{ProcessVm, VmRange};

    /// Preserve XPMEM's synchronous lifetime/lock owner and discarded status.
    /// # Safety
    /// vm/range are the original live objects under range removal exclusion.
    /// The existing XPMEM backend retains attachment/refcount/lock/cleanup
    /// policy. This adapter creates no reference and uses no removed storage
    /// after completion; it preserves the original deliberately ignored result.
    #[no_mangle]
    pub unsafe extern "C" fn process_remove_range_xpmem_bridge(
        vm: *mut ProcessVm, range: *mut VmRange,
    ) {
        unsafe {
            let _ = crate::xpmem_helpers::xpmem_remove_process_memory_range(vm.cast(), range.cast());
        }
    }

    /// Forward the exact original fatal diagnostic to the existing panic owner.
    /// # Safety
    /// message is the original live NUL-terminated kernel message. Call only
    /// where the existing panic/fail-stop contract applies; it does not return.
    #[no_mangle]
    pub unsafe extern "C" fn process_panic_bridge(message: *const i8) {
        unsafe { super::panic(message); }
    }
}

mod remaining_process_range_logs {
    use core::ptr::{addr_of, addr_of_mut, read_volatile};

    use crate::abi::{CInt, CULong, ProcessVm, VmRange};
    use crate::debug::Ddebug;

    unsafe extern "C" { static mut process_remaining_range_debug: [Ddebug; 8]; }

    /// The original writable C selectors stay live for the kernel lifetime.
    /// Raw bounded addresses avoid borrowing metadata across a logger call.
    unsafe fn enabled(index: usize) -> bool {
        unsafe {
            let descriptor = addr_of_mut!(process_remaining_range_debug).cast::<Ddebug>().add(index);
            read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0
        }
    }

    /// Preserve split entry/exit fields, nullable newrange and silent unknown events.
    /// # Safety
    /// When its selected event is enabled, range is live/readable under original
    /// range exclusion; non-null newrange is live for event2. Other pointers are
    /// only formatted. No pointer or reference is retained by this logger.
    #[no_mangle]
    pub unsafe extern "C" fn process_split_range_public_log_bridge(
        event: CInt, vm: *mut ProcessVm, range: *mut VmRange, addr: CULong,
        splitp: *mut *mut VmRange, newrange: *mut VmRange, error: CInt,
    ) {
        unsafe { match event {
            1 if enabled(0) => { let _ = super::kprintf(
                b"split_process_memory_range(%p,%lx-%lx,%lx,%p)\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, addr, splitp,
            ); }
            2 if enabled(1) => { let _ = super::kprintf(
                b"split_process_memory_range(%p,%lx-%lx,%lx,%p): %d %p %lx-%lx\n\0".as_ptr().cast(),
                vm, (*range).start, (*range).end, addr, splitp, error, newrange,
                if newrange.is_null() { 0 } else { (*newrange).start },
                if newrange.is_null() { 0 } else { (*newrange).end },
            ); }
            _ => {}
        } }
    }

    /// Preserve both original join formats and field-read scopes.
    /// # Safety
    /// Enabled events require live surviving; enabled event1 also requires live
    /// merging. Event2 only formats merging as a pointer, preserving null use.
    /// Original VM range exclusion and logging synchronization remain required.
    #[no_mangle]
    pub unsafe extern "C" fn process_join_range_log_bridge(
        event: CInt, vm: *mut ProcessVm, surviving: *mut VmRange,
        merging: *mut VmRange, error: CInt,
    ) {
        unsafe { match event {
            1 if enabled(2) => { let _ = super::kprintf(
                b"join_process_memory_range(%p,%lx-%lx,%lx-%lx)\n\0".as_ptr().cast(),
                vm, (*surviving).start, (*surviving).end, (*merging).start, (*merging).end,
            ); }
            2 if enabled(3) => { let _ = super::kprintf(
                b"join_process_memory_range(%p,%lx-%lx,%p): %d\n\0".as_ptr().cast(),
                vm, (*surviving).start, (*surviving).end, merging, error,
            ); }
            _ => {}
        } }
    }

    /// Preserve the original zero-event versus every-nonzero-event distinction.
    /// # Safety
    /// The existing logging context applies; vm is only formatted as a pointer.
    #[no_mangle]
    pub unsafe extern "C" fn process_flush_memory_debug_bridge(vm: *mut ProcessVm, event: CInt) {
        unsafe {
            if event == 0 {
                if enabled(4) { let _ = super::kprintf(
                    b"flush_process_memory(%p)\n\0".as_ptr().cast(), vm,
                ); }
            } else if enabled(5) { let _ = super::kprintf(
                b"flush_process_memory(%p):\n\0".as_ptr().cast(), vm,
            ); }
        }
    }

    /// Preserve unconditional errors, conditional traces and unsigned subtraction.
    /// # Safety
    /// A non-null range is live/readable for enabled converted event2; original
    /// range exclusion and logging context apply. Other pointers are only
    /// formatted, and unknown events do not read caller storage.
    #[no_mangle]
    pub unsafe extern "C" fn process_remove_range_log_bridge(
        event: CInt, vm: *mut ProcessVm, start: CULong, end: CULong,
        range: *mut VmRange, error: CInt,
    ) {
        unsafe { match event {
            1 => { let _ = super::kprintf(
                b"%s: WARNING: no straight mapping range found for 0x%lx\n\0".as_ptr().cast(),
                b"remove_process_memory_range\0".as_ptr().cast::<i8>(), start,
            ); }
            2 if enabled(6) => { let _ = super::kprintf(
                b"%s: straight range converted from 0x%lx:%lu -> 0x%lx:%lu\n\0".as_ptr().cast(),
                b"remove_process_memory_range\0".as_ptr().cast::<i8>(),
                if range.is_null() { start } else { (*range).straight_start },
                end.wrapping_sub(start), start, end.wrapping_sub(start),
            ); }
            3 => { let _ = super::kprintf(
                b"remove_process_memory_range(%p,%lx,%lx):split failed %d\n\0".as_ptr().cast(),
                vm, start, end, error,
            ); }
            4 => { let _ = super::kprintf(
                b"remove_process_memory_range(%p,%lx,%lx):free failed %d\n\0".as_ptr().cast(),
                vm, start, end, error,
            ); }
            5 if enabled(7) => { let _ = super::kprintf(
                b"remove_process_memory_range(%p,%lx,%lx): 0 %d\n\0".as_ptr().cast(),
                vm, start, end, error,
            ); }
            _ => {}
        } }
    }
}

mod remaining_process_memory_logs {
    use core::ptr::{addr_of, addr_of_mut, read_volatile};

    use crate::abi::{CInt, CLong, CULong, ProcessVm, SizeT, VmRange};
    use crate::debug::Ddebug;

    unsafe extern "C" { static mut process_remaining_memory_log_debug: [Ddebug; 5]; }

    // All callers use constant indices 0..5 into the original live selectors.
    unsafe fn enabled(index: usize) -> bool {
        unsafe {
            let descriptor = addr_of_mut!(process_remaining_memory_log_debug).cast::<Ddebug>().add(index);
            read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0
        }
    }

    /// Preserve allocation/insertion/preparation errors and the selected demand trace.
    /// # Safety
    /// The original kernel logging context and synchronization apply. Inputs
    /// are scalar values and static formats, with no caller storage retained.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_log_bridge(
        event: CInt, rc: CInt, start: CULong, end: CULong,
    ) {
        unsafe { match event {
            1 => { let _ = super::kprintf(
                b"%s: ERROR: allocating pages for range
 ".as_ptr().cast(),
                b"add_process_memory_range ".as_ptr().cast::<i8>(),
            ); }
            2 => { let _ = super::kprintf(
                b"%s: ERROR: could not insert range: %d
 ".as_ptr().cast(),
                b"add_process_memory_range ".as_ptr().cast::<i8>(), rc,
            ); }
            3 => { let _ = super::kprintf(
                b"%s: ERROR: preparing page tables
 ".as_ptr().cast(),
                b"add_process_memory_range ".as_ptr().cast::<i8>(),
            ); }
            4 if enabled(0) => { let _ = super::kprintf(
                b"%s: range: 0x%lx - 0x%lx is demand paging
 ".as_ptr().cast(),
                b"add_process_memory_range ".as_ptr().cast::<i8>(), start, end,
            ); }
            5 => { let _ = super::kprintf(
                b"%s: error: range %lx - %lx is not in user available area
 ".as_ptr().cast(),
                b"add_process_memory_range ".as_ptr().cast::<i8>(), start, end,
            ); }
            _ => {}
        } }
    }

    /// Preserve nullable range fields and conditional entry/exit versus always-error logs.
    /// # Safety
    /// Non-null range is live/readable under the original VM range exclusion
    /// when its event logs. vm is only formatted; no reference is retained.
    #[no_mangle]
    pub unsafe extern "C" fn process_change_prot_public_log_bridge(
        event: CInt, vm: *mut ProcessVm, range: *mut VmRange, protflag: CULong, error: CInt,
    ) {
        unsafe { match event {
            1 if enabled(1) => { let _ = super::kprintf(
                b"change_prot_process_memory_range(%p,%lx-%lx,%lx)
 ".as_ptr().cast(),
                vm, if range.is_null() { 0 } else { (*range).start },
                if range.is_null() { 0 } else { (*range).end }, protflag,
            ); }
            2 => { let _ = super::kprintf(
                b"change_prot_process_memory_range(%p,%lx-%lx,%lx):ihk_mc_pt_change_attr_range failed: %d
 ".as_ptr().cast(),
                vm, if range.is_null() { 0 } else { (*range).start },
                if range.is_null() { 0 } else { (*range).end }, protflag, error,
            ); }
            3 if enabled(2) => { let _ = super::kprintf(
                b"change_prot_process_memory_range(%p,%lx-%lx,%lx): %d
 ".as_ptr().cast(),
                vm, if range.is_null() { 0 } else { (*range).start },
                if range.is_null() { 0 } else { (*range).end }, protflag, error,
            ); }
            _ => {}
        } }
    }

    /// Keep both original remap errors, including the signed offset's vararg bits.
    /// # Safety
    /// The original logging context applies. vm/range are only formatted as
    /// raw pointers; unknown events do not access any caller storage.
    #[no_mangle]
    pub unsafe extern "C" fn process_remap_range_log_bridge(
        event: CInt, vm: *mut ProcessVm, range: *mut VmRange, start: CULong,
        end: CULong, off: CLong, old_pgshift: CInt, error: CInt,
    ) {
        unsafe { match event {
            1 => { let _ = super::kprintf(
                b"%s: pgshift is too big (%d)  failed:%d
 ".as_ptr().cast(),
                b"remap_process_memory_range ".as_ptr().cast::<i8>(), old_pgshift, error,
            ); }
            2 => { let _ = super::kprintf(
                b"remap_process_memory_range(%p,%p,%#lx,%#lx,%#lx):visit pte failed %d
 ".as_ptr().cast(),
                vm, range, start, end, off, error,
            ); }
            _ => {}
        } }
    }

    /// Preserve the single SMP memset diagnostic and its actual size_t argument.
    /// # Safety
    /// The original logging context applies. All values are scalars; no callback
    /// or mapping is invoked and unknown events remain silent.
    #[no_mangle]
    pub unsafe extern "C" fn process_memset_smp_log_bridge(
        event: CInt, cpu_index: CInt, nr_cpus: CInt, phys: CULong, len: SizeT,
        start: CULong, end: CULong,
    ) {
        unsafe {
            if event == 1 && enabled(3) { let _ = super::kprintf(
                b"%s: cpu_index: %d, nr_cpus: %d, phys: 0x%lx, len: %lu, p_s: 0x%lx, p_e: 0x%lx
 ".as_ptr().cast(),
                b"memset_smp_handler ".as_ptr().cast::<i8>(),
                cpu_index, nr_cpus, phys, len, start, end,
            ); }
        }
    }

    /// Keep the original source-function label and deferred-accounting diagnostic.
    /// # Safety
    /// The original logging context applies. vm is intentionally unused, and
    /// start/end are only formatted as the original unsigned long values.
    #[no_mangle]
    pub unsafe extern "C" fn process_remove_region_log_bridge(
        _vm: *mut ProcessVm, start: CULong, end: CULong,
    ) {
        unsafe {
            if enabled(4) { let _ = super::kprintf(
                b"%s: memory_stat_rss_sub() isn't called,start=%lx,end=%lx
 ".as_ptr().cast(),
                b"process_remove_region_log_bridge ".as_ptr().cast::<i8>(), start, end,
            ); }
        }
    }
}

mod remaining_process_range_scheduler_logs {
    use core::ptr::{addr_of, addr_of_mut, read_volatile};

    use crate::abi::{CInt, CULong, ProcessVm, Thread, VmRange};
    use crate::debug::Ddebug;

    unsafe extern "C" {
        static mut process_remaining_range_scheduler_debug: [Ddebug; 18];
    }

    // Every caller uses a constant index into the original C-owned selectors.
    unsafe fn enabled(index: usize) -> bool {
        // SAFETY: The retained 18-entry metadata array is live for the kernel
        // lifetime; selectors use the existing volatile dynamic-debug boundary.
        unsafe {
            let descriptor = addr_of_mut!(process_remaining_range_scheduler_debug)
                .cast::<Ddebug>().add(index);
            read_volatile(addr_of!((*descriptor).line_flags)) >> 24 != 0
        }
    }

    /// Preserve range lookup/neighbor/extension diagnostics and nullable fields.
    /// # Safety
    /// A non-null range must remain readable under the original VM exclusion
    /// when its event is enabled. vm is only formatted; no storage is retained.
    #[no_mangle]
    pub unsafe extern "C" fn process_range_public_log_bridge(
        event: CInt, vm: *mut ProcessVm, range: *mut VmRange,
        start: CULong, end: CULong, error: CInt,
    ) {
        // SAFETY: Read fields only after the matching live selector is enabled;
        // callers retain the original range lifetime across this synchronous log.
        unsafe {
            if !(1..=8).contains(&event) || !enabled((event - 1) as usize) {
                return;
            }
            match event {
                1 => { let _ = super::kprintf(
                    b"lookup_process_memory_range(%p,%lx,%lx)\n\0".as_ptr().cast(),
                    vm, start, end,
                ); }
                2 | 4 | 6 => {
                    let format = match event {
                        2 => b"lookup_process_memory_range(%p,%lx,%lx): %p %lx-%lx\n\0".as_ptr(),
                        4 => b"next_process_memory_range(%p,%lx-%lx): %p %lx-%lx\n\0".as_ptr(),
                        _ => b"previous_process_memory_range(%p,%lx-%lx): %p %lx-%lx\n\0".as_ptr(),
                    };
                    let _ = super::kprintf(format.cast(), vm, start, end, range,
                        if range.is_null() { 0 } else { (*range).start },
                        if range.is_null() { 0 } else { (*range).end });
                }
                3 => { let _ = super::kprintf(
                    b"next_process_memory_range(%p,%lx-%lx)\n\0".as_ptr().cast(), vm, start, end,
                ); }
                5 => { let _ = super::kprintf(
                    b"previous_process_memory_range(%p,%lx-%lx)\n\0".as_ptr().cast(), vm, start, end,
                ); }
                7 => { let _ = super::kprintf(
                    b"exntend_up_process_memory_range(%p,%p %#lx-%#lx,%#lx)\n\0".as_ptr().cast(),
                    vm, range, if range.is_null() { 0 } else { (*range).start },
                    if range.is_null() { 0 } else { (*range).end }, end,
                ); }
                8 => { let _ = super::kprintf(
                    b"exntend_up_process_memory_range(%p,%p %#lx-%#lx,%#lx):%d\n\0".as_ptr().cast(),
                    vm, range, if range.is_null() { 0 } else { (*range).start },
                    if range.is_null() { 0 } else { (*range).end }, end, error,
                ); }
                _ => {}
            }
        }
    }

    /// Preserve runqueue diagnostics, including guarded Thread field reads.
    /// # Safety
    /// For enabled WAKE_ENTRY, arg0 points to a live aligned Thread protected
    /// by the original wakeup/runqueue exclusion. The CPU getter must be valid
    /// in the caller's original scheduler context. No pointer is retained.
    #[no_mangle]
    pub unsafe extern "C" fn process_sched_runq_log_bridge(
        event: CInt, arg0: CULong, _arg1: CULong, arg2: CInt, arg3: CInt,
    ) {
        // SAFETY: All formats are static. Only the enabled wake-entry event
        // dereferences arg0, under the caller's original Thread lifetime.
        unsafe { match event {
            1 => { let _ = super::kprintf(b"no migration in IRQ context\n\0".as_ptr().cast()); }
            2 if enabled(8) => {
                let thread = arg0 as *const Thread;
                let _ = super::kprintf(
                    b"%s: proc->pid=%d, valid_states=%08x, proc->status=%08x, proc->cpu_id=%d,my cpu_id=%d\n\0".as_ptr().cast(),
                    b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2, arg3,
                    (*thread).status, (*thread).cpu_id, super::ihk_mc_get_processor_id(),
                );
            }
            3 if enabled(9) => { let _ = super::kprintf(
                b"%s: spin wakeup: cpu_id: %d\n\0".as_ptr().cast(),
                b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            4 if enabled(10) => { let _ = super::kprintf(
                b"%s: issuing IPI, thread->cpu_id=%d\n\0".as_ptr().cast(),
                b"__sched_wakeup_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            5 if enabled(11) => { let _ = super::kprintf(
                b"runq_add_proc(): tid %d added to CPU[%d]'s runq\n\0".as_ptr().cast(), arg2, arg3,
            ); }
            6 if enabled(12) => { let _ = super::kprintf(
                b"%s: idle_halt -> schedule()\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
            ); }
            7 if enabled(13) => { let _ = super::kprintf(
                b"%s: caught a lost wake-up!\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
            ); }
            // IHK_OS_MANYCORE maps ihk_ikc_get_processor_id to the same actual
            // ihk_mc_get_processor_id getter in ikc/ihk.h, as in sched_helpers.
            8 if enabled(14) => { let _ = super::kprintf(
                b"%s: woken while spinning, cpu: %d, do_schedule: %d\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
                super::ihk_mc_get_processor_id(), arg3,
            ); }
            9 if enabled(15) => { let _ = super::kprintf(
                b"%s: woken while sleeping, cpu: %d\n\0".as_ptr().cast(),
                b"spin_sleep_or_schedule\0".as_ptr().cast::<i8>(),
                super::ihk_mc_get_processor_id(),
            ); }
            10 => { let _ = super::kprintf(
                b"%s: WARNING can't schedule() while no preemption, cnt: %d\n\0".as_ptr().cast(),
                b"schedule\0".as_ptr().cast::<i8>(), arg2,
            ); }
            11 if enabled(16) => { let _ = super::kprintf(
                b"%s: clone_count is %d\n\0".as_ptr().cast(),
                b"runq_add_thread\0".as_ptr().cast::<i8>(), arg2,
            ); }
            _ => {}
        } }
    }

    /// Preserve migration's original label and signed CPU/TID arguments.
    /// # Safety
    /// Enter in the original logging context. thread_addr is intentionally
    /// unused; no Thread access, callback, lock operation or retained pointer.
    #[no_mangle]
    pub unsafe extern "C" fn process_sched_do_migrate_log_bridge(
        _thread_addr: CULong, tid: CInt, old_cpu_id: CInt, new_cpu_id: CInt,
    ) {
        // SAFETY: Original live selector and static format, scalar varargs only.
        unsafe {
            if enabled(17) { let _ = super::kprintf(
                b"%s: migrated TID %d from CPU %d to CPU %d\n\0".as_ptr().cast(),
                b"do_migrate\0".as_ptr().cast::<i8>(), tid, old_cpu_id, new_cpu_id,
            ); }
        }
    }
}

mod remaining_process_add_range_memclear {
    use core::ffi::c_void;

    use crate::abi::{CULong, SizeT};

    // The original C call converts unsigned long bytes to size_t. Both are
    // full-width on the current target, so this conversion preserves all bits.
    const _: [(); core::mem::size_of::<CULong>()] = [(); core::mem::size_of::<SizeT>()];

    type ArchMemclear = unsafe extern "C" fn(*mut c_void, CULong);
    const _: [(); core::mem::size_of::<Option<ArchMemclear>>()] =
        [(); core::mem::size_of::<*mut c_void>()];

    // Reuse this module's exact existing callback alias. Selected C rejects the
    // ARCH_MEMCLEAR variant; disabled selection retains its original C owner.
    #[cfg(process_verbose_local_companions)]
    mod final_metadata_owner {
        use super::ArchMemclear;

        #[no_mangle]
        pub(super) static process_add_range_arch_memclear_callback: Option<ArchMemclear> = None;
    }

    unsafe extern "C" {
        static process_add_range_arch_memclear_callback: Option<ArchMemclear>;
    }

    /// Clear the original physical allocation through its existing architecture provider.
    /// # Safety
    /// phys maps to bytes writable, exclusively owned ordinary RAM for the
    /// complete call. The architecture translation and optional existing clear
    /// callback retain their original mapping/alignment/lifetime requirements.
    /// No reference, allocation, mapping change or callback pointer is retained.
    #[no_mangle]
    pub unsafe extern "C" fn process_add_range_memclear_bridge(phys: CULong, bytes: CULong) {
        // SAFETY: The caller keeps the original allocation live. Translate once
        // before clearing, matching C. The read-only selector is initialized
        // from the actual ARCH_MEMCLEAR provider or NULL, never a guessed ABI.
        unsafe {
            let addr = crate::x86_memory_helpers::phys_to_virt(phys);
            if let Some(clear) = process_add_range_arch_memclear_callback {
                clear(addr, bytes);
            } else {
                super::process_memset_smp_memset_bridge(addr, 0, bytes as SizeT);
            }
        }
    }
}

mod remaining_process_conditional_scheduler {
    use core::sync::atomic::{AtomicI64, AtomicU64, Ordering};

    use crate::abi::{CInt, CLong, CULong};
    use crate::sched_helpers::SchedExitDebug;

    unsafe extern "C" {
        static process_sched_timer_configuration: [CInt; 2];
        static process_schedule_exit_debug_input: *const SchedExitDebug;
    }

    const _: [(); core::mem::size_of::<CULong>()] = [(); core::mem::size_of::<AtomicU64>()];
    const _: [(); core::mem::align_of::<CULong>()] = [(); core::mem::align_of::<AtomicU64>()];
    const _: [(); core::mem::size_of::<CLong>()] = [(); core::mem::size_of::<AtomicI64>()];
    const _: [(); core::mem::align_of::<CLong>()] = [(); core::mem::align_of::<AtomicI64>()];

    /// Enter the existing timer loop only on the actual configured timer CPU.
    /// # Safety
    /// Called from original scheduler initialization with its original CPU
    /// ownership. The existing timer initialization/loop retains all timer,
    /// wakeup and lifetime requirements; its return behavior is unchanged.
    #[no_mangle]
    pub unsafe extern "C" fn process_sched_timer_init_bridge(cpu: CInt) {
        // SAFETY: Actual C preprocessor constants, live read-only kernel data.
        // Existing Rust backends own all initialization and loop effects.
        unsafe {
            if process_sched_timer_configuration[0] != 0
                && cpu == process_sched_timer_configuration[1]
            {
                crate::timer::init_timers();
                crate::timer::wake_timers_loop();
            }
        }
    }

    /// Print the original optional rusage diagnostics after first-thread admission.
    /// # Safety
    /// The static descriptor is NULL when disabled, otherwise points to the
    /// original live accounting counters and exact page-size array bounds.
    /// Counters have native 64-bit alignment and use existing atomic accounting
    /// updates during runtime; initialization is complete before this callback.
    /// No reference or storage is retained across a log call.
    #[no_mangle]
    pub unsafe extern "C" fn process_sched_rusage_debug_bridge() {
        // SAFETY: Reuse the actual source-owned descriptor, without duplicating
        // private rusage layout. Independent Relaxed reads pair with existing
        // atomic counter updates; diagnostics do not publish state or promise
        // a coherent snapshot of all counters.
        unsafe {
            let debug = process_schedule_exit_debug_input;
            if debug.is_null()
                || AtomicU64::from_ptr((*debug).num_threads.cast_mut()).load(Ordering::Relaxed) != 1
            {
                return;
            }
            let total = AtomicU64::from_ptr((*debug).total_memory_usage.cast_mut())
                .load(Ordering::Relaxed);
            let _ = super::kprintf(b"total_memory_usage=%ld\n\0".as_ptr().cast(), total);
            let mut i = 0;
            while i < (*debug).page_sizes {
                let value = AtomicI64::from_ptr((*debug).memory_stat_rss.add(i as usize).cast_mut())
                    .load(Ordering::Relaxed);
                let _ = super::kprintf(b"memory_stat_rss[%d]=%ld\n\0".as_ptr().cast(), i, value);
                i += 1;
            }
            i = 0;
            while i < (*debug).page_sizes {
                let value = AtomicI64::from_ptr(
                    (*debug).memory_stat_mapped_file.add(i as usize).cast_mut(),
                ).load(Ordering::Relaxed);
                let _ = super::kprintf(
                    b"memory_stat_mapped_file[%d]=%ld\n\0".as_ptr().cast(), i, value,
                );
                i += 1;
            }
        }
    }
}

mod remaining_process_normal_fault_provider {
    use crate::abi::{CInt, CULong, ProcessVm, VmRange};

    /// Forward the original normal-range fault to the existing Rust core owner.
    /// # Safety
    /// vm/range and their original locks, mapping/backing-object lifetimes and
    /// fault-address/reason contracts remain valid for the synchronous core
    /// fault operation. The core owns all lock completion, result and error
    /// semantics; this leaf retains no reference or pointer after the call.
    #[no_mangle]
    pub unsafe extern "C" fn process_normal_fault_range_bridge(
        vm: *mut ProcessVm, range: *mut VmRange, fault_addr: CULong, reason: CULong,
    ) -> CInt {
        // SAFETY: Exact original pointer/scalar inputs and original core owner;
        // no extra lock, policy decision, error translation or side effect.
        unsafe { super::page_fault_process_memory_range(vm, range, fault_addr, reason) }
    }
}

#[cfg(process_global_storage_candidate)]
mod process_global_storage {
    use core::mem::{align_of, offset_of, size_of};
    use core::ptr::null_mut;

    use crate::abi::{AbiListHead, CInt, IhkSpinlock, McsRwlockLock};

    // Preserve the existing plain C int ABI and boot defaults. Initialization
    // owns writes before normal scheduler/application consumers observe these
    // flags; existing extern accesses retain their current synchronization.
    // Keep plain mutable storage: changing this to an AtomicI32, bool, or a
    // lazy initializer would change the original C/Rust access contract.
    const _: [(); 4] = [(); size_of::<CInt>()];
    const _: [(); 4] = [(); align_of::<CInt>()];

    #[no_mangle]
    pub static mut idle_halt: CInt = 0;

    #[no_mangle]
    pub static mut allow_oversubscribe: CInt = 0;

    #[no_mangle]
    pub static mut time_sharing: CInt = 1;

    // These are the existing owned ABI types, not replacement representations.
    // The independent genuine-header witness must qualify this exact profile.
    const _: [(); 4] = [(); size_of::<IhkSpinlock>()];
    const _: [(); 4] = [(); align_of::<IhkSpinlock>()];
    const _: [(); 0] = [(); offset_of!(IhkSpinlock, head_tail)];
    const _: [(); 64] = [(); size_of::<McsRwlockLock>()];
    const _: [(); 64] = [(); align_of::<McsRwlockLock>()];
    const _: [(); 0] = [(); offset_of!(McsRwlockLock, slock)];
    const _: [(); 16] = [(); size_of::<AbiListHead>()];
    const _: [(); 8] = [(); align_of::<AbiListHead>()];
    const _: [(); 0] = [(); offset_of!(AbiListHead, next)];
    const _: [(); 8] = [(); offset_of!(AbiListHead, prev)];

    // The genuine C list type has alignment 8, while its retained tentative
    // global symbol requires alignment 16. Preserve that storage requirement
    // around the unchanged owned type, with the original payload at offset 0.
    #[repr(C, align(16))]
    pub struct ResourceSetListStorage {
        head: AbiListHead,
    }

    const _: [(); 16] = [(); size_of::<ResourceSetListStorage>()];
    const _: [(); 16] = [(); align_of::<ResourceSetListStorage>()];
    const _: [(); 0] = [(); offset_of!(ResourceSetListStorage, head)];

    // Preserve original BSS state: NULL links, not an eagerly self-linked list.
    // Extern consumers still use AbiListHead at this exact exported address.
    // proc_init owns the original head/lock initialization and publication;
    // later mutation retains the existing resource_set_lock exclusion.
    #[export_name = "resource_set_list"]
    pub static mut RESOURCE_SET_LIST_STORAGE: ResourceSetListStorage = ResourceSetListStorage {
        head: AbiListHead { next: null_mut(), prev: null_mut() },
    };

    // Preserve the real 64-byte aligned MCS lock and its zero initial state.
    // The existing initializer and MCS bridge own all runtime lock operations.
    #[no_mangle]
    pub static mut resource_set_lock: McsRwlockLock = McsRwlockLock {
        slock: IhkSpinlock { head_tail: 0 },
    };

    // The original reservation lock's zero ticket state is valid before use.
    // Existing scheduler/affinity callers retain their IRQ and lock pairing.
    #[no_mangle]
    pub static mut runq_reservation_lock: IhkSpinlock = IhkSpinlock { head_tail: 0 };
}

// Own the qualified idle data with the existing paired storage selector.
// The accepted callback initializer and genuine ABI contracts remain unchanged.
#[cfg(process_global_storage_candidate)]
mod process_idle_callback_storage {
    use core::mem::{align_of, offset_of, size_of};
    use crate::abi::CULong;
    use crate::sched_helpers::SchedIdleCallbacks;

    // Reuse the existing callback representation. Its address-sized arguments
    // and the C unsigned-long arguments have the same supported LP64 ABI.
    // These are the exact ten existing symbol targets, with no new wrappers,
    // callback execution, initialization, lifetime or IRQ ownership changes.
    unsafe extern "C" {
        fn sched_idle_current_cpu_bridge() -> usize;
        fn process_spin_lock_bridge(lock_addr: usize) -> CULong;
        fn process_spin_unlock_bridge(lock_addr: usize, irqstate: CULong);
        fn cpu_enable_interrupt();
        fn cpu_disable_interrupt();
        fn schedule();
        fn sched_do_migrate_public();
        fn kmalloc_consolidate_free_list();
        fn process_sched_zero_free_bridge();
        fn cpu_safe_halt();
    }

    const _: [(); 8] = [(); size_of::<usize>()];
    const _: [(); 8] = [(); size_of::<CULong>()];
    const _: [(); 80] = [(); size_of::<SchedIdleCallbacks>()];
    const _: [(); 8] = [(); align_of::<SchedIdleCallbacks>()];
    const _: [(); 0] = [(); offset_of!(SchedIdleCallbacks, current_cpu)];
    const _: [(); 8] = [(); offset_of!(SchedIdleCallbacks, lock)];
    const _: [(); 16] = [(); offset_of!(SchedIdleCallbacks, unlock)];
    const _: [(); 24] = [(); offset_of!(SchedIdleCallbacks, enable_interrupt)];
    const _: [(); 32] = [(); offset_of!(SchedIdleCallbacks, disable_interrupt)];
    const _: [(); 40] = [(); offset_of!(SchedIdleCallbacks, schedule)];
    const _: [(); 48] = [(); offset_of!(SchedIdleCallbacks, migrate)];
    const _: [(); 56] = [(); offset_of!(SchedIdleCallbacks, consolidate)];
    const _: [(); 64] = [(); offset_of!(SchedIdleCallbacks, zero_free)];
    const _: [(); 72] = [(); offset_of!(SchedIdleCallbacks, safe_halt)];

    // Immutable companions to the already qualified idle callback owner.
    // Original CPU, thread and monitor constants are checked by the selected C ABI.
    mod layout_values_storage {
        use core::mem::{align_of, offset_of, size_of};

        use crate::abi::{CpuLocalVar, IhkOsCpuMonitor, Thread};
        use crate::sched_helpers::{SchedIdleOffsets, SchedIdleValues};

        const _: () = {
            assert!(size_of::<SchedIdleOffsets>() == 80);
            assert!(align_of::<SchedIdleOffsets>() == 8);
            assert!(size_of::<SchedIdleValues>() == 36);
            assert!(align_of::<SchedIdleValues>() == 4);
        };

        #[no_mangle]
        pub static process_idle_offsets: SchedIdleOffsets = SchedIdleOffsets {
            cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
            cpu_runq_irqstate_offset: offset_of!(CpuLocalVar, runq_irqstate),
            cpu_current_offset: offset_of!(CpuLocalVar, current),
            cpu_flags_offset: offset_of!(CpuLocalVar, flags),
            cpu_status_offset: offset_of!(CpuLocalVar, status),
            cpu_runq_offset: offset_of!(CpuLocalVar, runq),
            thread_sched_list_offset: offset_of!(Thread, sched_list),
            thread_status_offset: offset_of!(Thread, status),
            monitor_status_offset: offset_of!(IhkOsCpuMonitor, status),
            monitor_counter_offset: offset_of!(IhkOsCpuMonitor, counter),
        };

        #[no_mangle]
        pub static process_idle_values: SchedIdleValues = SchedIdleValues {
            cpu_running: 2,
            cpu_idle: 1,
            cpu_reserved: 3,
            thread_running: 1,
            thread_stopped: 0x20,
            thread_interruptible: 2,
            need_migrate: 2,
            monitor_idle: 1,
            monitor_kernel: 3,
        };
    }

    // Keep this immutable callback array in the original readonly-data class.
    // Object flags/RELA and final physical mapping require independent proof.
    #[no_mangle]
    #[link_section = ".rodata.process_idle_callbacks"]
    pub static process_idle_callbacks: SchedIdleCallbacks = SchedIdleCallbacks {
        current_cpu: sched_idle_current_cpu_bridge,
        lock: process_spin_lock_bridge,
        unlock: process_spin_unlock_bridge,
        enable_interrupt: cpu_enable_interrupt,
        disable_interrupt: cpu_disable_interrupt,
        schedule,
        migrate: sched_do_migrate_public,
        consolidate: kmalloc_consolidate_free_list,
        zero_free: process_sched_zero_free_bridge,
        safe_halt: cpu_safe_halt,
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact original process.c tracked-allocation diagnostic callsite identities.
// These immutable signed C-int objects use the already paired storage selector.
// The original C __FILE__ pointers and every mutable Ddebug selector stay unchanged.
#[cfg(process_global_storage_candidate)]
mod remaining_process_tracked_line_storage {
    use crate::abi::CInt;

    const _: () = {
        assert!(core::mem::size_of::<CInt>() == 4);
        assert!(core::mem::align_of::<CInt>() == 4);
    };

    #[no_mangle]
    pub static process_mckfd_free_bridge_source_line: CInt = 171;

    #[no_mangle]
    pub static process_policy_free_bridge_source_line: CInt = 253;

    #[no_mangle]
    pub static process_optional_free_bridge_source_line: CInt = 258;

    #[no_mangle]
    pub static process_alloc_bridge_source_line: CInt = 340;

    #[no_mangle]
    pub static process_free_vm_bridge_source_line: CInt = 561;

    #[no_mangle]
    pub static process_create_thread_alloc_pages_source_line: CInt = 788;

    #[no_mangle]
    pub static process_split_range_alloc_source_line: CInt = 1628;

    #[no_mangle]
    pub static process_range_kfree_bridge_source_line: CInt = 1817;

    #[no_mangle]
    pub static process_free_range_pages_source_line: CInt = 1873;

    #[no_mangle]
    pub static process_add_range_alloc_bridge_source_line: CInt = 2256;

    #[no_mangle]
    pub static process_add_range_free_bridge_source_line: CInt = 2261;

    #[no_mangle]
    pub static process_page_fault_anon_alloc_line: CInt = 3058;

    #[no_mangle]
    pub static process_free_thread_pages_source_line: CInt = 3501;
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// The same immutable timer descriptor, using the existing genuine Rust ABI types.
// This changes storage ownership only; no timer, lock, interrupt or list logic.
#[cfg(process_global_storage_candidate)]
mod remaining_process_timer_layout_storage {
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::{CpuLocalVar, Thread, Timer};
    use crate::sched_helpers::TimerRuntimeOffsets;

    const _: () = {
        assert!(size_of::<TimerRuntimeOffsets>() == 120);
        assert!(align_of::<TimerRuntimeOffsets>() == 8);
    };

    #[no_mangle]
    pub static process_timer_runtime_offsets: TimerRuntimeOffsets = TimerRuntimeOffsets {
        thread_status_offset: offset_of!(Thread, status),
        thread_sched_list_offset: offset_of!(Thread, sched_list),
        thread_spin_sleep_lock_offset: offset_of!(Thread, spin_sleep_lock),
        thread_spin_sleep_offset: offset_of!(Thread, spin_sleep),
        thread_itimer_enabled_offset: offset_of!(Thread, itimer_enabled),
        cpu_runq_lock_offset: offset_of!(CpuLocalVar, runq_lock),
        cpu_runq_offset: offset_of!(CpuLocalVar, runq),
        cpu_runq_len_offset: offset_of!(CpuLocalVar, runq_len),
        cpu_current_offset: offset_of!(CpuLocalVar, current),
        cpu_timer_enabled_offset: offset_of!(CpuLocalVar, timer_enabled),
        cpu_backlog_list_offset: offset_of!(CpuLocalVar, backlog_list),
        timer_timeout_offset: offset_of!(Timer, timeout),
        timer_waitq_offset: offset_of!(Timer, processes),
        timer_list_offset: offset_of!(Timer, list),
        timer_thread_offset: offset_of!(Timer, thread),
    };
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Four existing signed C-int runtime selectors. The selected C declarations bind
// the supported macro/enum values; unsupported dump/fast-memset variants fail
// their compile-time assertion rather than silently select a different policy.
#[cfg(process_global_storage_candidate)]
mod process_scalar_metadata_storage {
    use crate::abi::CInt;

    const _: () = {
        assert!(core::mem::size_of::<CInt>() == 4);
        assert!(core::mem::align_of::<CInt>() == 4);
    };

    #[no_mangle]
    pub static process_init_stack_user_category: CInt = 1;

    #[no_mangle]
    pub static process_page_fault_anon_clear_profile_event: CInt = if cfg!(enable_profile) { 4002 } else { 0 };

    #[no_mangle]
    pub static process_memset_smp_fast_word_pattern: CInt = 1;

    #[no_mangle]
    pub static process_dump_tree_enabled: CInt = 0;

}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Joint selection only: foreground owns all fourteen internal Ddebug definitions.
// These private configuration types contain immutable image-lifetime addresses.
// Sync shares the raw values only: no dereference, callback invocation, flag
// mutation or lifetime/allocator/VM ownership transfer is performed here.
#[cfg(process_verbose_local_companions)]
unsafe impl Sync for ProcessCloneConfig {}
#[cfg(process_verbose_local_companions)]
unsafe impl Sync for ProcessCopyEntryConfig {}
#[cfg(process_verbose_local_companions)]
unsafe impl Sync for ProcessExtendRegionEntryConfig {}

#[cfg(all(process_verbose_local_companions, not(process_verbose_data)))]
compile_error!("local debug companions require process_verbose_data");

#[cfg(process_verbose_local_companions)]
mod process_local14_config_storage {
    use super::{ProcessCloneConfig, ProcessCopyEntryConfig, ProcessExtendRegionEntryConfig};
    use crate::process_verbose_data::local;
    use core::ptr::addr_of_mut;

    // Same mandatory actual-C-argv binding and C __FILE__ assertion as foreground.
    // No Rust file!(), independent literal path, C pointer escape or new C owner.
    const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_PROCESS_C_FILE"), "\0").as_bytes();
    const _: () = assert!(SOURCE_FILE.len() > 1);

    #[no_mangle]
    pub(super) static process_clone_config: ProcessCloneConfig = ProcessCloneConfig {
        stack_pages: 32,
        page_size: 4096,
        page_align: 0,
        nowait: 2,
        kernel: 0,
        ss_disable: 2,
        sp_reg: 1,
        pc_reg: 2,
        file: SOURCE_FILE.as_ptr().cast(),
        lines: [1002, 1063, 1083, 1144, 1153],
        debug: [
            addr_of_mut!(local::process_clone_vm_debug),
            addr_of_mut!(local::process_clone_ranges_debug),
            addr_of_mut!(local::process_clone_ranges_ok_debug),
            addr_of_mut!(local::process_clone_sigcommon_debug),
            addr_of_mut!(local::process_clone_sigshared_debug),
        ],
        modify_context: super::process_user_context_modify_bridge,
        copy_ranges: super::copy_user_ranges,
    };

    #[no_mangle]
    pub(super) static process_copy_entry_config: ProcessCopyEntryConfig = ProcessCopyEntryConfig {
        page_size: 4096,
        page_shift: 12,
        nowait: 2,
        user_category: 1,
        kernel_category: 0,
        wipe_on_fork: 2147483648,
        file: SOURCE_FILE.as_ptr().cast(),
        alloc_line: 1464,
        free_line: 1520,
        visit_flags: 1,
        found_debug: addr_of_mut!(local::process_copy_pte_found_debug),
        size_debug: addr_of_mut!(local::process_copy_pte_size_debug),
        allocated_debug: addr_of_mut!(local::process_copy_pte_allocated_debug),
        zeroed_debug: addr_of_mut!(local::process_copy_pte_zeroed_debug),
        copied_debug: addr_of_mut!(local::process_copy_pte_copied_debug),
        installed_debug: addr_of_mut!(local::process_copy_pte_installed_debug),
    };

    #[no_mangle]
    pub(super) static process_extend_region_entry_config: ProcessExtendRegionEntryConfig = ProcessExtendRegionEntryConfig {
        page_size: 4096,
        page_shift: 12,
        page_mask: 18446744073709547520,
        large_page_size: 2097152,
        large_page_mask: 18446744073707454464,
        large_page_p2align: 9,
        page_p2align: 0,
        large_page_shift: 21,
        mpol_no_heap: 1,
        ap_nowait: 2,
        ap_user: 4096,
        pg_user: 1,
        file: SOURCE_FILE.as_ptr().cast(),
        alloc_line: 3408,
        free_line: 3423,
        exists_debug: addr_of_mut!(local::process_extend_region_exists_debug),
        alloc_debug: addr_of_mut!(local::process_extend_region_alloc_debug),
        success_debug: addr_of_mut!(local::process_extend_region_success_debug),
    };

}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// A future layer on the existing paired local-companion selection. C rejects
// unqualified feature variants; disabled selection retains every original cell.
#[cfg(process_verbose_local_companions)]
mod process_final_metadata_storage {
    use super::{CInt, ProcessInitStackEntryConfig};
    use crate::sched_helpers::SchedExitDebug;

    // The wrapper owns only immutable pointer-cell bits. It creates no reference
    // or safe dereference API and makes no claim about pointee mutability, lifetime
    // or synchronization. Existing consumers keep their raw-pointer contracts.
    #[repr(transparent)]
    pub(super) struct ReadonlyPointerCell<T>(*const T);
    // SAFETY: sharing this private cell only shares its immutable raw value.
    // All pointee access and mutation remain with the existing unsafe consumers.
    unsafe impl<T> Sync for ReadonlyPointerCell<T> {}

    const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_PROCESS_C_FILE"), "\0").as_bytes();
    const _: () = assert!(
        SOURCE_FILE.len() > 1,
        "process C filename must not be empty"
    );

    #[no_mangle]
    pub(super) static process_tracked_allocator_source_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_remap_free_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_remap_free_line: CInt = 2469;
    #[no_mangle]
    pub(super) static process_page_fault_cow_alloc_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_page_fault_cow_alloc_line: CInt = 3145;
    #[no_mangle]
    pub(super) static process_page_fault_anon_alloc_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_init_stack_alloc_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_init_stack_alloc_line: CInt = 3359;
    #[no_mangle]
    pub(super) static process_init_stack_free_file: ReadonlyPointerCell<i8> =
        ReadonlyPointerCell(SOURCE_FILE.as_ptr().cast());
    #[no_mangle]
    pub(super) static process_init_stack_free_line: CInt = 3364;

    // Existing repr(C) config and all nine actual Rust callback types are reused.
    #[no_mangle]
    pub(super) static process_init_stack_entry_config: ProcessInitStackEntryConfig =
        ProcessInitStackEntryConfig {
            page_size: super::PAGE_SIZE,
            page_shift: super::PAGE_SHIFT as CInt,
            user_stack_page_mask: 0xffff_ffff_ffe0_0000,
            user_stack_page_shift: 21,
            user_stack_prepage_size: 2_097_152,
            stack_alloc_size_override: 0,
            user_stack_page_p2align: 9,
            alloc_nowait: super::IHK_MC_AP_NOWAIT,
            alloc_user: 4096,
            mpol_no_stack: 2,
            user_context_sp_reg: super::IHK_UCR_STACK_POINTER,
            pf_populate: super::PF_POPULATE,
            alloc_aligned: super::process_init_stack_alloc_aligned_bridge,
            free_pages: super::process_init_stack_free_pages_bridge,
            add_range: super::process_init_stack_add_range_bridge,
            virt_to_phys: super::process_init_stack_virt_to_phys_bridge,
            attr: super::process_init_stack_attr_bridge,
            pt_set_range: super::process_init_stack_pt_set_range_bridge,
            hwcap: super::process_init_stack_hwcap_bridge,
            modify_context: super::process_init_stack_modify_context_bridge,
            log: super::process_init_stack_log_bridge,
        };

    // Selected C explicitly rejects TIMER_CPU_ID and RUSAGE_DEBUG variants.
    #[no_mangle]
    pub(super) static process_sched_timer_configuration: [CInt; 2] = [0, 0];
    #[no_mangle]
    pub(super) static process_schedule_exit_debug_input: ReadonlyPointerCell<SchedExitDebug> =
        ReadonlyPointerCell(core::ptr::null());
}
