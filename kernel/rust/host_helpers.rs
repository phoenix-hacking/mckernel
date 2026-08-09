use core::{
    ffi::{c_char, c_void},
    mem::{align_of, offset_of, size_of, size_of_val},
    ptr::{read_volatile, write_volatile},
};

use crate::abi::{
    AddressSpace, CInt, CLong, CULong, CpuLocalVar, IhkOsCpuRegister, IkcScdPacket,
    IkcScdPacketCpuRw, IkcScdPacketSysfs, IkcScdPacketTraditional, PerfCtrlDesc, Process,
    ProcessVm, ProgramImageSection, ProgramLoadDesc, SigInfo, Thread, VmRange, Waitq,
    X86UserContext, PLD_NUMA_MASK_WORDS, PROCESS_NUMA_MASK_WORDS,
};

const EAGAIN: CInt = 11;
const EINVAL: CInt = 22;
const ENOMEM: CInt = 12;
const EFAULT: CInt = 14;
const IHK_OS_MONITOR_KERNEL_FREEZING: CInt = 8;
const IHK_OS_MONITOR_KERNEL_FROZEN: CInt = 9;
const PLD_MAGIC: CULong = 0xcafecafe44332211;
const HOST_PREPARE_MAX_SECTIONS: CInt = 16;
const HOST_PREPARE_PTHREAD_MAIN: &[u8; 7] = b"[main]\0";
const SCD_MSG_PREPARE_PROCESS: CInt = 0x01;
const SCD_MSG_PREPARE_PROCESS_ACKED: CInt = 0x02;
const SCD_MSG_SCHEDULE_PROCESS: CInt = 0x03;
const SCD_MSG_INIT_CHANNEL_ACKED: CInt = 0x06;
const SCD_MSG_SEND_SIGNAL: CInt = 0x07;
const SCD_MSG_CLEANUP_PROCESS: CInt = 0x09;
const SCD_MSG_PROCFS_REQUEST: CInt = 0x12;
const SCD_MSG_WAKE_UP_SYSCALL_THREAD: CInt = 0x14;
const SCD_MSG_PROCFS_RELEASE: CInt = 0x15;
const SCD_MSG_REMOTE_PAGE_FAULT: CInt = 0x18;
const SCD_MSG_REMOTE_PAGE_FAULT_ANSWER: CInt = 0x19;
const SCD_MSG_DEBUG_LOG: CInt = 0x20;
const SCD_MSG_SYSFS_REQ_SHOW: CInt = 0x3a;
const SCD_MSG_SYSFS_REQ_STORE: CInt = 0x3c;
const SCD_MSG_SYSFS_REQ_RELEASE: CInt = 0x3e;
const SCD_MSG_PERF_CTRL: CInt = 0x50;
const SCD_MSG_SEND_SIGNAL_ACK: CInt = 0x08;
const SCD_MSG_PERF_ACK: CInt = 0x51;
const SCD_MSG_CPU_RW_REG: CInt = 0x52;
const SCD_MSG_CPU_RW_REG_RESP: CInt = 0x53;
const SCD_MSG_CLEANUP_FD: CInt = 0x54;
const SCD_MSG_CLEANUP_PROCESS_RESP: CInt = 0x0a;
const SCD_MSG_CLEANUP_FD_RESP: CInt = 0x55;
const PTATTR_ACTIVE: CInt = 0x01;
const PTATTR_WRITABLE: CInt = 0x02;
const PERF_CTRL_SET: CInt = 0;
const PERF_CTRL_GET: CInt = 1;
const PERF_CTRL_ENABLE: CInt = 2;
const PERF_CTRL_DISABLE: CInt = 3;
const PERFCTR_USER_MODE: CInt = 0x01;
const PERFCTR_KERNEL_MODE: CInt = 0x02;
const IHK_MC_PERFCTR_DISABLE_INTERRUPT: CInt = 1;
const PERF_CTRL_EXCLUDE_USER: u32 = 1 << 2;
const PERF_CTRL_EXCLUDE_KERNEL: u32 = 1 << 3;
const HOST_INIT_IKC_LOG_ALLOC_ERROR: CInt = 1;
const HOST_INIT_IKC_LOG_TRY_CONNECT: CInt = 2;
const HOST_INIT_IKC_LOG_RETRY_DOT: CInt = 3;
const HOST_INIT_IKC_LOG_CONNECTED: CInt = 4;
const HOST_PREPARE_LOG_BROKEN_DESC: CInt = 1;
const HOST_PREPARE_LOG_INVALID_SECTIONS: CInt = 2;
const HOST_PREPARE_LOG_NUM_SECTIONS: CInt = 3;
const HOST_PREPARE_LOG_NUMA_BIND_ERROR: CInt = 4;
const HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR: CInt = 5;
const HOST_PREPARE_LOG_NUMA_POLICY: CInt = 6;
const HOST_PREPARE_LOG_PID_FLAGS: CInt = 7;
const HOST_PREPARE_LOG_RLIMIT: CInt = 8;
const HOST_PREPARE_LOG_PREPARE_ERROR: CInt = 9;
const HOST_PREPARE_LOG_NEW_PROCESS: CInt = 10;
const HOST_PREPARE_RANGES_LOG_AP_USER: CInt = 20;
const HOST_PREPARE_RANGES_LOG_ADD_FAILED: CInt = 21;
const HOST_PREPARE_RANGES_LOG_ALLOC_FAILED: CInt = 22;
const HOST_PREPARE_RANGES_LOG_PT_FAILED: CInt = 23;
const HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE: CInt = 24;
const HOST_PREPARE_ARGS_LOG_ALLOC_FAILED: CInt = 25;
const HOST_PREPARE_ARGS_LOG_ADD_FAILED: CInt = 26;
const HOST_PREPARE_ARGS_LOG_ARGS_MAP_FAILED: CInt = 27;
const HOST_PREPARE_ARGS_LOG_ENVS_MAP_FAILED: CInt = 28;
const HOST_PREPARE_ARGS_LOG_CMDLINE_ALLOC_FAILED: CInt = 29;
const HOST_PREPARE_ARGS_LOG_VDSO_FAILED: CInt = 30;
const HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED: CInt = 31;
const HOST_PREPARE_ARGS_LOG_CMDLINE: CInt = 32;
const VR_NONE: CULong = 0;
const VR_AP_USER: CULong = 0x4;
const VR_DEMAND_PAGING: CULong = 0x1000;
const VR_PRIVATE: CULong = 0x2000;
const VR_PROT_READ: CULong = 0x0001_0000;
const VR_PROT_WRITE: CULong = 0x0002_0000;
const VR_PROT_MASK: CULong = 0x0007_0000;
const PROT_EXEC: CInt = 0x04;
const NOPHYS: CULong = CULong::MAX;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const PAGE_MASK: CULong = !(PAGE_SIZE - 1);
const LARGE_PAGE_SHIFT: CInt = 21;
const LARGE_PAGE_SIZE: CULong = 1 << LARGE_PAGE_SHIFT;
const LARGE_PAGE_MASK: CULong = !(LARGE_PAGE_SIZE - 1);
const TASK_UNMAPPED_BASE: CULong = 0x0000_2aaa_aaa0_0000;
const USER_END: CULong = 0x0000_8000_0000_0000;
const LD_TASK_UNMAPPED_BASE: CULong = 0x0000_1555_5550_0000;
const PTATTR_NO_EXECUTE: CULong = 0x8000_0000_0000_0000;
const PTATTR_FOR_USER: CULong = 0x20000;
const IHK_MC_AP_NOWAIT: CULong = 0x000002;
const IHK_MC_AP_USER: CULong = 0x001000;
const IHK_MC_PG_USER: CInt = 1;
const PAGE_P2ALIGN: CInt = 0;
const IHK_UCR_PROGRAM_COUNTER: CInt = 2;
const MPOL_NO_BSS: CULong = 0x04;
const MPOL_BIND: CInt = 2;
const MPOL_MAX: CInt = 5;
const PF_POPULATE: CULong = 1 << 30;
const SIGCHLD: CInt = 17;
const PS_RUNNING: CInt = 0x1;
const PS_INTERRUPTIBLE: CInt = 0x2;
const HOST_RS_FILE: &[u8] = b"kernel/rust/host_helpers.rs\0";
const CHECK_MAP_MISSING_FMT: &[u8] = b"check_map: no mapping for 0x%lX\n\0";
const CHECK_MAP_HIT_FMT: &[u8] = b"check_map: 0x%lX -> 0x%lX\n\0";

extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn panic(msg: *const c_char) -> !;
    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn ihk_mc_pt_virt_to_phys(
        page_table: *mut c_void,
        virt: *mut c_void,
        phys: *mut CULong,
    ) -> CInt;
    fn add_process_memory_range(
        vm: *mut ProcessVm,
        start: CULong,
        end: CULong,
        phys: CULong,
        flag: CULong,
        memobj: *mut c_void,
        offset: CLong,
        pgshift: CInt,
        private_data: *mut c_void,
        range: *mut *mut VmRange,
    ) -> CInt;
    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flags: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut c_char,
        line: CInt,
    ) -> *mut c_void;
    fn _ihk_mc_free_pages(
        addr: *mut c_void,
        npages: CInt,
        is_user: CInt,
        file: *mut c_char,
        line: CInt,
    );
    fn virt_to_phys(addr: *mut c_void) -> CULong;
    fn arch_vrflag_to_ptattr(flag: CULong, fault: CULong, ptep: *mut c_void) -> CULong;
    fn ihk_mc_pt_set_range(
        page_table: *mut c_void,
        vm: *mut c_void,
        start: *mut c_void,
        end: *mut c_void,
        phys: CULong,
        attr: CULong,
        pgshift: CInt,
        range: *mut c_void,
        flags: CInt,
    ) -> CInt;
    fn ihk_mc_modify_user_context(uctx: *mut c_void, reg: CInt, value: CULong);
    fn arch_map_vdso(vm: *mut ProcessVm) -> CInt;
    fn init_process_stack(
        thread: *mut Thread,
        pn: *mut ProgramLoadDesc,
        at_base: CULong,
        argc: CInt,
        argv: *mut *mut i8,
        envc: CInt,
        env: *mut *mut i8,
    ) -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn get_this_cpu_local_var() -> *mut CpuLocalVar;
    fn ihk_mc_map_memory(os: *mut c_void, phys: CULong, size: CULong) -> CULong;
    fn ihk_mc_map_virtual(phys: CULong, npages: CInt, attr: CULong) -> *mut c_void;
    fn ihk_mc_unmap_virtual(addr: *mut c_void, npages: CInt);
    fn ihk_mc_unmap_memory(os: *mut c_void, phys: CULong, size: CULong);
    fn memcpy_long(dst: *mut c_void, src: *const c_void, size: usize) -> *mut c_void;
    fn memcpy(dst: *mut c_void, src: *const c_void, size: usize) -> *mut c_void;
    fn create_thread(entry: CULong, cpu_set: *mut CULong, cpu_set_size: CULong) -> *mut Thread;
    fn destroy_thread(thread: *mut Thread);
    fn ihk_mc_get_nr_numa_nodes() -> CInt;
    fn flush_tlb();
    #[cfg(enable_tofu)]
    fn tof_utofu_finalize();
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut c_void, opt: CInt) -> CInt;
    fn arch_cpu_read_write_register(desc: *mut IhkOsCpuRegister, op: CInt) -> CInt;
    fn terminate_host(pid: CInt, thread: *mut Thread);
    fn do_kill(
        thread: *mut Thread,
        pid: CInt,
        tid: CInt,
        sig: CInt,
        info: *mut SigInfo,
        ptracecont: CInt,
    ) -> CULong;
    fn debug_log(code: CLong);
    fn find_thread(pid: CInt, tid: CInt) -> *mut Thread;
    fn waitq_wakeup(waitq: *mut Waitq);
    fn thread_unlock(thread: *mut Thread);
    fn rdtsc() -> CULong;
    fn preempt_disable();
    fn preempt_enable();
    fn page_fault_process_vm(vm: *mut ProcessVm, addr: *mut c_void, reason: CULong);
    #[cfg(enable_profile)]
    fn profile_event_add(event: CInt, delta: CULong);
    fn ihk_ikc_connect(os: *mut c_void, param: *mut IhkIkcConnectParam) -> CInt;
    fn ihk_mc_delay_us(usec: CInt);
    fn ihk_ikc_set_regular_channel(os: *mut c_void, channel: *mut c_void, cpu: CInt);
    fn sched_wakeup_thread(thread: *mut Thread, valid_states: CInt) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn obtain_clone_cpuid(cpu_set: *mut crate::abi::CpuSet, use_last: CInt) -> CInt;
    fn ihk_mc_syscall_pc(uctx: *const X86UserContext) -> CULong;
    fn ihk_mc_syscall_sp(uctx: *const X86UserContext) -> CULong;
    fn chain_thread(thread: *mut Thread);
    fn chain_process(proc: *mut Process);
    fn runq_add_thread(thread: *mut Thread, cpuid: CInt);
    fn ihk_mc_perfctr_init_raw(counter: CInt, config: u32, mode: CInt) -> CInt;
    fn ihk_mc_perfctr_stop(counter_mask: CULong, flags: CInt) -> CInt;
    fn ihk_mc_perfctr_reset(counter: CInt) -> CInt;
    fn ihk_mc_perfctr_start(counter_mask: CULong) -> CInt;
    fn ihk_mc_perfctr_read(counter: CInt) -> CULong;
    fn process_cleanup_before_terminate(pid: CInt) -> CInt;
    fn process_cleanup_fd(pid: CInt, fd: CInt) -> CInt;
    fn process_procfs_request(packet: *mut IkcScdPacket) -> CInt;
    fn sysfss_packet_handler(
        channel: *mut c_void,
        msg: CInt,
        err: CInt,
        arg1: CLong,
        arg2: CLong,
        arg3: CLong,
    );
    fn ihk_ikc_release_packet(packet: *mut c_void);
    fn ihk_mc_get_nr_linux_cores() -> CInt;

    #[link_name = "num_processors"]
    static mut HOST_NUM_PROCESSORS: CInt;
}

#[inline(always)]
fn host_file_ptr() -> *mut c_char {
    HOST_RS_FILE.as_ptr() as *mut c_char
}

#[no_mangle]
pub static mut ikc2linuxs: *mut *mut c_void = core::ptr::null_mut();

pub type HostIkcPacketSendFn =
    Option<unsafe extern "C" fn(channel: *mut c_void, packet: *mut IkcScdPacket)>;
pub type HostIkcPacketHandlerFn = Option<
    unsafe extern "C" fn(channel: *mut c_void, packet: *mut c_void, os: *mut c_void) -> CInt,
>;
pub type HostIkcConnectFn = Option<unsafe extern "C" fn(param: *mut IhkIkcConnectParam) -> CInt>;
pub type HostDelayFn = Option<unsafe extern "C" fn(usec: CULong)>;
pub type HostSetCurrentIkc2linuxFn = Option<unsafe extern "C" fn(channel: *mut c_void)>;
pub type HostIkcSetRegularChannelFn = Option<unsafe extern "C" fn(channel: *mut c_void, cpu: CInt)>;
pub type HostInitIkcLogFn = Option<unsafe extern "C" fn(event: CInt)>;
pub type HostPanicFn = Option<unsafe extern "C" fn()>;
pub type HostMonitorStatusFn = Option<unsafe extern "C" fn(cpu: CInt) -> CInt>;
pub type HostPrepareProcessFn = Option<unsafe extern "C" fn(rphys: CULong) -> CInt>;
pub type HostPerfInitRawFn =
    Option<unsafe extern "C" fn(counter: CInt, config: u32, mode: CInt) -> CInt>;
pub type HostPerfStopFn = Option<unsafe extern "C" fn(counter_mask: CULong, flags: CInt) -> CInt>;
pub type HostPerfResetFn = Option<unsafe extern "C" fn(counter: CInt) -> CInt>;
pub type HostPerfStartFn = Option<unsafe extern "C" fn(counter_mask: CULong) -> CInt>;
pub type HostPerfReadFn = Option<unsafe extern "C" fn(counter: CInt) -> CULong>;
pub type HostPerfUnexpectedFn = Option<unsafe extern "C" fn()>;
pub type HostMapMemoryFn =
    Option<unsafe extern "C" fn(os: *mut c_void, phys: CULong, size: CULong) -> CULong>;
pub type HostMapVirtualFn =
    Option<unsafe extern "C" fn(phys: CULong, npages: CInt, attr: CInt) -> *mut c_void>;
pub type HostPrepareMapVirtualFn =
    Option<unsafe extern "C" fn(phys: CULong, npages: CInt, attr: CULong) -> *mut c_void>;
pub type HostUnmapVirtualFn = Option<unsafe extern "C" fn(addr: *mut c_void, npages: CInt)>;
pub type HostUnmapMemoryFn =
    Option<unsafe extern "C" fn(os: *mut c_void, phys: CULong, size: CULong)>;
pub type HostCpuRwRegisterFn = Option<unsafe extern "C" fn(desc: *mut c_void, op: CInt) -> CInt>;
pub type HostCleanupProcessFn = Option<unsafe extern "C" fn(pid: CInt) -> CInt>;
pub type HostTerminateHostFn = Option<unsafe extern "C" fn(pid: CInt, thread: *mut c_void)>;
pub type HostCleanupProcessLogFn = Option<unsafe extern "C" fn(pid: CInt, thread_arg: CULong)>;
pub type HostCleanupFdFn = Option<unsafe extern "C" fn(pid: CInt, fd: CInt) -> CInt>;
pub type HostCleanupFdLogFn = Option<unsafe extern "C" fn(pid: CInt, fd: CULong, err: CInt)>;
pub type HostDoKillFn =
    Option<unsafe extern "C" fn(pid: CInt, tid: CInt, sig: CInt, info: *mut c_void) -> CULong>;
pub type HostSendSignalLogFn =
    Option<unsafe extern "C" fn(pid: CInt, tid: CInt, sig: CInt, rc: CInt)>;
pub type HostFindThreadFn = Option<unsafe extern "C" fn(pid: CInt, tid: CInt) -> *mut c_void>;
pub type HostWakeupThreadFn = Option<unsafe extern "C" fn(thread: *mut c_void)>;
pub type HostThreadUnlockFn = Option<unsafe extern "C" fn(thread: *mut c_void)>;
pub type HostWakeSyscallLogFn = Option<unsafe extern "C" fn(tid: CInt, found: CInt)>;
pub type HostDebugLogFn = Option<unsafe extern "C" fn(code: CULong)>;
pub type HostDebugLogPrintFn = Option<unsafe extern "C" fn(code: CULong)>;
pub type HostThreadProfileEnabledFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> CInt>;
pub type HostTimestampFn = Option<unsafe extern "C" fn() -> CULong>;
pub type HostPreemptFn = Option<unsafe extern "C" fn()>;
pub type HostRemotePageFaultFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, fault_address: CULong, fault_reason: CULong)>;
pub type HostProfileEventFn = Option<unsafe extern "C" fn(event: CInt, delta: CULong)>;
pub type HostRemotePageFaultLogFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, fault_address: CULong, fault_reason: CULong)>;
pub type HostRemotePageFaultBodyFn =
    Option<unsafe extern "C" fn(request: *mut IkcScdPacket, err: CInt)>;
pub type HostAllocFn = Option<unsafe extern "C" fn(size: CULong, flags: CULong) -> *mut c_void>;
pub type HostFreeFn = Option<unsafe extern "C" fn(ptr: *mut c_void)>;
pub type HostPacketCopyFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *mut IkcScdPacket, size: CULong)>;
pub type HostCopyLongFn =
    Option<unsafe extern "C" fn(dst: *mut c_void, src: *const c_void, size: CULong)>;
pub type HostCreateThreadFn = Option<
    unsafe extern "C" fn(entry: CULong, cpu_set: *mut CULong, cpu_set_size: CULong) -> *mut Thread,
>;
pub type HostDestroyThreadFn = Option<unsafe extern "C" fn(thread: *mut Thread)>;
pub type HostPrepareRangesFn = Option<
    unsafe extern "C" fn(
        thread: *mut Thread,
        pn: *mut ProgramLoadDesc,
        p: *mut ProgramLoadDesc,
        attr: CULong,
        args: *mut i8,
        args_len: CInt,
        envs: *mut i8,
        envs_len: CInt,
    ) -> CInt,
>;
pub type HostNrNumaNodesFn = Option<unsafe extern "C" fn() -> CInt>;
pub type HostFlushTlbFn = Option<unsafe extern "C" fn()>;
pub type HostTofuFinalizeFn = Option<unsafe extern "C" fn()>;
pub type HostPrepareProcessLogFn =
    Option<unsafe extern "C" fn(event: CInt, arg0: CULong, arg1: CULong, arg2: CULong)>;
pub type HostPrepareAddRangeFn = Option<
    unsafe extern "C" fn(
        vm: *mut c_void,
        start: CULong,
        end: CULong,
        phys: CULong,
        flag: CULong,
        pgshift: CInt,
        rangep: *mut *mut c_void,
    ) -> CInt,
>;
pub type HostPrepareAllocPagesUserFn =
    Option<unsafe extern "C" fn(npages: CInt, flags: CULong, virt_addr: CULong) -> *mut c_void>;
pub type HostPrepareFreePagesUserFn = Option<unsafe extern "C" fn(addr: *mut c_void, npages: CInt)>;
pub type HostVirtToPhysFn = Option<unsafe extern "C" fn(addr: *mut c_void) -> CULong>;
pub type HostArchVrflagToPtattrFn =
    Option<unsafe extern "C" fn(flag: CULong, fault: CULong, ptep: *mut c_void) -> CULong>;
pub type HostPtSetRangeFn = Option<
    unsafe extern "C" fn(
        page_table: *mut c_void,
        vm: *mut c_void,
        start: CULong,
        end: CULong,
        phys: CULong,
        attr: CULong,
        pgshift: CInt,
        range: *mut c_void,
        flags: CInt,
    ) -> CInt,
>;
pub type HostModifyUserContextFn =
    Option<unsafe extern "C" fn(uctx: *mut c_void, reg: CInt, value: CULong)>;
pub type HostPrepareRangesLogFn =
    Option<unsafe extern "C" fn(event: CInt, arg0: CULong, arg1: CULong, arg2: CULong)>;
pub type HostArchMapVdsoFn = Option<unsafe extern "C" fn(vm: *mut c_void) -> CInt>;
pub type HostInitProcessStackFn = Option<
    unsafe extern "C" fn(
        thread: *mut c_void,
        pn: *mut ProgramLoadDesc,
        at_base: CULong,
        argc: CInt,
        argv: *mut *mut i8,
        envc: CInt,
        env: *mut *mut i8,
    ) -> CInt,
>;
pub type HostPrepareArgsLogFn =
    Option<unsafe extern "C" fn(event: CInt, arg0: CULong, arg1: CULong, arg2: CULong)>;
pub type HostBacklogFn = Option<unsafe extern "C" fn(arg: *mut c_void)>;
pub type HostRemotePageFaultDeferFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, arg: *mut c_void, backlog_fn: HostBacklogFn)>;
pub type HostSchedWakeupFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, valid_states: CInt) -> CInt>;
pub type HostRemotePageFaultMissingLogFn = Option<unsafe extern "C" fn(tid: CInt)>;
pub type HostThreadProcFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> *mut c_void>;
pub type HostCurrentCpuFn = Option<unsafe extern "C" fn() -> CInt>;
pub type HostThreadCpuAllowedFn =
    Option<unsafe extern "C" fn(thread: *mut c_void, cpuid: CInt) -> CInt>;
pub type HostThreadObtainCpuidFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> CInt>;
pub type HostProcPidFn = Option<unsafe extern "C" fn(proc: *mut c_void) -> CInt>;
pub type HostThreadRegFn = Option<unsafe extern "C" fn(thread: *mut c_void) -> CULong>;
pub type HostScheduleInvalidLogFn = Option<unsafe extern "C" fn(thread: *mut c_void)>;
pub type HostScheduleReceivedLogFn = Option<
    unsafe extern "C" fn(thread: *mut c_void, pid: CInt, pc: CULong, sp: CULong, cpuid: CInt),
>;
pub type HostScheduleNoCpuLogFn = Option<unsafe extern "C" fn()>;
pub type HostThreadSetTidFn = Option<unsafe extern "C" fn(thread: *mut c_void, tid: CInt)>;
pub type HostStatusSetFn = Option<unsafe extern "C" fn(object: *mut c_void, status: CInt)>;
pub type HostChainThreadFn = Option<unsafe extern "C" fn(thread: *mut c_void)>;
pub type HostChainProcessFn = Option<unsafe extern "C" fn(proc: *mut c_void)>;
pub type HostRunqAddThreadFn = Option<unsafe extern "C" fn(thread: *mut c_void, cpuid: CInt)>;
pub type HostScheduleQueuedLogFn =
    Option<unsafe extern "C" fn(pid: CInt, tid: CInt, cpuid: CInt, status: CInt)>;
pub type HostInitAckLogFn = Option<unsafe extern "C" fn()>;
pub type HostScheduleProcessLogFn = Option<unsafe extern "C" fn(arg: CULong)>;
pub type HostResponsePacketFn =
    Option<unsafe extern "C" fn(response_channel: *mut c_void, packet: *mut IkcScdPacket) -> CInt>;
pub type HostPacketDispatchFn = Option<unsafe extern "C" fn(packet: *mut IkcScdPacket) -> CInt>;
pub type HostRemotePageFaultDispatchFn =
    Option<unsafe extern "C" fn(packet: *mut IkcScdPacket, current_thread: *mut c_void) -> CInt>;
pub type HostProcfsRequestFn = Option<unsafe extern "C" fn(packet: *mut IkcScdPacket) -> CInt>;
pub type HostSysfsPacketFn = Option<
    unsafe extern "C" fn(
        channel: *mut c_void,
        msg: CInt,
        err: CInt,
        arg1: CLong,
        arg2: CLong,
        arg3: CLong,
    ),
>;
pub type HostUnknownPacketLogFn = Option<unsafe extern "C" fn(packet: *mut IkcScdPacket)>;
pub type HostReleasePacketFn = Option<unsafe extern "C" fn(packet: *mut IkcScdPacket)>;
pub type HostCurrentPtrFn = Option<unsafe extern "C" fn() -> *mut c_void>;

#[repr(C)]
pub struct HostScdDispatchOps {
    init_ack_log_fn: HostInitAckLogFn,
    prepare_process_fn: HostResponsePacketFn,
    schedule_process_fn: HostPacketDispatchFn,
    wake_syscall_thread_fn: HostPacketDispatchFn,
    remote_page_fault_fn: HostRemotePageFaultDispatchFn,
    send_signal_fn: HostResponsePacketFn,
    procfs_request_fn: HostProcfsRequestFn,
    cleanup_process_fn: HostResponsePacketFn,
    cleanup_fd_fn: HostResponsePacketFn,
    debug_log_fn: HostPacketDispatchFn,
    sysfs_packet_fn: HostSysfsPacketFn,
    perf_ctrl_fn: HostResponsePacketFn,
    cpu_rw_reg_fn: HostResponsePacketFn,
    unknown_packet_log_fn: HostUnknownPacketLogFn,
    release_packet_fn: HostReleasePacketFn,
}

#[no_mangle]
pub unsafe extern "C" fn host_ikc_packet_send_result(
    channel: *mut c_void,
    packet: *mut IkcScdPacket,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    let send = match send_fn {
        Some(send) => send,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    send(channel, packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_ikc_connect_result(
    param: *mut IhkIkcConnectParam,
    connect_fn: HostIkcConnectFn,
) -> CInt {
    let connect = match connect_fn {
        Some(connect) => connect,
        None => return -EINVAL,
    };

    connect(param)
}

#[no_mangle]
pub unsafe extern "C" fn host_delay_result(usec: CULong, delay_fn: HostDelayFn) -> CInt {
    let delay = match delay_fn {
        Some(delay) => delay,
        None => return -EINVAL,
    };

    delay(usec);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_set_current_ikc2linux_result(
    channel: *mut c_void,
    set_current_fn: HostSetCurrentIkc2linuxFn,
) -> CInt {
    let set_current = match set_current_fn {
        Some(set_current) => set_current,
        None => return -EINVAL,
    };

    set_current(channel);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_ikc_set_regular_channel_result(
    channel: *mut c_void,
    cpu: CInt,
    set_regular_fn: HostIkcSetRegularChannelFn,
) -> CInt {
    let set_regular = match set_regular_fn {
        Some(set_regular) => set_regular,
        None => return -EINVAL,
    };

    set_regular(channel, cpu);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_panic_result(panic_fn: HostPanicFn) -> CInt {
    let panic = match panic_fn {
        Some(panic) => panic,
        None => return -EINVAL,
    };

    panic();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ikc_log_result(event: CInt, log_fn: HostInitIkcLogFn) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(event);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_current_ptr_result(current_fn: HostCurrentPtrFn) -> *mut c_void {
    let current = match current_fn {
        Some(current) => current,
        None => return core::ptr::null_mut(),
    };

    current()
}

#[no_mangle]
pub unsafe extern "C" fn host_monitor_status_result(
    cpu: CInt,
    monitor_status_fn: HostMonitorStatusFn,
) -> CInt {
    let monitor_status = match monitor_status_fn {
        Some(monitor_status) => monitor_status,
        None => return -EINVAL,
    };

    monitor_status(cpu)
}

#[no_mangle]
pub unsafe extern "C" fn host_tofu_finalize_result(tofu_finalize_fn: HostTofuFinalizeFn) -> CInt {
    let tofu_finalize = match tofu_finalize_fn {
        Some(tofu_finalize) => tofu_finalize,
        None => return -EINVAL,
    };

    tofu_finalize();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_process_log_result(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    log_fn: HostPrepareProcessLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(event, arg0, arg1, arg2);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_ranges_log_result(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    log_fn: HostPrepareRangesLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(event, arg0, arg1, arg2);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_args_log_result(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    log_fn: HostPrepareArgsLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(event, arg0, arg1, arg2);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_process_result(
    rphys: CULong,
    prepare_fn: HostPrepareProcessFn,
) -> CInt {
    let prepare = match prepare_fn {
        Some(prepare) => prepare,
        None => return -EINVAL,
    };

    prepare(rphys)
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_ranges_result(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    attr: CULong,
    args: *mut i8,
    args_len: CInt,
    envs: *mut i8,
    envs_len: CInt,
    ranges_fn: HostPrepareRangesFn,
) -> CInt {
    let ranges = match ranges_fn {
        Some(ranges) => ranges,
        None => return -EINVAL,
    };

    ranges(thread, pn, p, attr, args, args_len, envs, envs_len)
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_process_result(
    pid: CInt,
    cleanup_fn: HostCleanupProcessFn,
) -> CInt {
    let cleanup = match cleanup_fn {
        Some(cleanup) => cleanup,
        None => return -EINVAL,
    };

    cleanup(pid)
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_fd_result(
    pid: CInt,
    fd: CInt,
    cleanup_fn: HostCleanupFdFn,
) -> CInt {
    let cleanup = match cleanup_fn {
        Some(cleanup) => cleanup,
        None => return -EINVAL,
    };

    cleanup(pid, fd)
}

#[no_mangle]
pub unsafe extern "C" fn host_map_memory_result(
    os: *mut c_void,
    phys: CULong,
    size: CULong,
    map_memory_fn: HostMapMemoryFn,
) -> CULong {
    let map_memory = match map_memory_fn {
        Some(map_memory) => map_memory,
        None => return 0,
    };

    map_memory(os, phys, size)
}

#[no_mangle]
pub unsafe extern "C" fn host_map_virtual_result(
    phys: CULong,
    npages: CInt,
    attr: CInt,
    map_virtual_fn: HostMapVirtualFn,
) -> *mut c_void {
    let map_virtual = match map_virtual_fn {
        Some(map_virtual) => map_virtual,
        None => return core::ptr::null_mut(),
    };

    map_virtual(phys, npages, attr)
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_map_virtual_result(
    phys: CULong,
    npages: CInt,
    attr: CULong,
    map_virtual_fn: HostPrepareMapVirtualFn,
) -> *mut c_void {
    let map_virtual = match map_virtual_fn {
        Some(map_virtual) => map_virtual,
        None => return core::ptr::null_mut(),
    };

    map_virtual(phys, npages, attr)
}

#[no_mangle]
pub unsafe extern "C" fn host_unmap_virtual_result(
    addr: *mut c_void,
    npages: CInt,
    unmap_virtual_fn: HostUnmapVirtualFn,
) -> CInt {
    let unmap_virtual = match unmap_virtual_fn {
        Some(unmap_virtual) => unmap_virtual,
        None => return -EINVAL,
    };

    unmap_virtual(addr, npages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_unmap_memory_result(
    os: *mut c_void,
    phys: CULong,
    size: CULong,
    unmap_memory_fn: HostUnmapMemoryFn,
) -> CInt {
    let unmap_memory = match unmap_memory_fn {
        Some(unmap_memory) => unmap_memory,
        None => return -EINVAL,
    };

    unmap_memory(os, phys, size);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_add_range_result(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut c_void,
    add_range_fn: HostPrepareAddRangeFn,
) -> CInt {
    let add_range = match add_range_fn {
        Some(add_range) => add_range,
        None => return -EINVAL,
    };

    add_range(vm, start, end, phys, flag, pgshift, rangep)
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_alloc_pages_user_result(
    npages: CInt,
    flags: CULong,
    virt_addr: CULong,
    alloc_pages_fn: HostPrepareAllocPagesUserFn,
) -> *mut c_void {
    let alloc_pages = match alloc_pages_fn {
        Some(alloc_pages) => alloc_pages,
        None => return core::ptr::null_mut(),
    };

    alloc_pages(npages, flags, virt_addr)
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_free_pages_user_result(
    addr: *mut c_void,
    npages: CInt,
    free_pages_fn: HostPrepareFreePagesUserFn,
) -> CInt {
    let free_pages = match free_pages_fn {
        Some(free_pages) => free_pages,
        None => return -EINVAL,
    };

    free_pages(addr, npages);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_virt_to_phys_result(
    addr: *mut c_void,
    virt_to_phys_fn: HostVirtToPhysFn,
) -> CULong {
    let virt_to_phys = match virt_to_phys_fn {
        Some(virt_to_phys) => virt_to_phys,
        None => return 0,
    };

    virt_to_phys(addr)
}

#[no_mangle]
pub unsafe extern "C" fn host_arch_vrflag_to_ptattr_result(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
    attr_fn: HostArchVrflagToPtattrFn,
) -> CULong {
    let attr = match attr_fn {
        Some(attr) => attr,
        None => return 0,
    };

    attr(flag, fault, ptep)
}

#[no_mangle]
pub unsafe extern "C" fn host_pt_set_range_result(
    page_table: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut c_void,
    flags: CInt,
    pt_set_range_fn: HostPtSetRangeFn,
) -> CInt {
    let pt_set_range = match pt_set_range_fn {
        Some(pt_set_range) => pt_set_range,
        None => return -EINVAL,
    };

    pt_set_range(
        page_table, vm, start, end, phys, attr, pgshift, range, flags,
    )
}

#[no_mangle]
pub unsafe extern "C" fn host_modify_user_context_result(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
    modify_fn: HostModifyUserContextFn,
) -> CInt {
    let modify = match modify_fn {
        Some(modify) => modify,
        None => return -EINVAL,
    };

    modify(uctx, reg, value);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_alloc_result(
    size: CULong,
    flags: CULong,
    alloc_fn: HostAllocFn,
) -> *mut c_void {
    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return core::ptr::null_mut(),
    };

    alloc(size, flags)
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_free_result(ptr: *mut c_void, free_fn: HostFreeFn) -> CInt {
    let free = match free_fn {
        Some(free) => free,
        None => return -EINVAL,
    };

    free(ptr);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_copy_long_result(
    dst: *mut c_void,
    src: *const c_void,
    size: CULong,
    copy_fn: HostCopyLongFn,
) -> CInt {
    let copy = match copy_fn {
        Some(copy) => copy,
        None => return -EINVAL,
    };

    copy(dst, src, size);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_create_thread_result(
    entry: CULong,
    cpu_set: *mut CULong,
    cpu_set_size: CULong,
    create_fn: HostCreateThreadFn,
) -> *mut Thread {
    let create = match create_fn {
        Some(create) => create,
        None => return core::ptr::null_mut(),
    };

    create(entry, cpu_set, cpu_set_size)
}

#[no_mangle]
pub unsafe extern "C" fn host_destroy_thread_result(
    thread: *mut Thread,
    destroy_fn: HostDestroyThreadFn,
) -> CInt {
    let destroy = match destroy_fn {
        Some(destroy) => destroy,
        None => return -EINVAL,
    };

    destroy(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_nr_numa_nodes_result(nr_numa_nodes_fn: HostNrNumaNodesFn) -> CInt {
    let nr_numa_nodes = match nr_numa_nodes_fn {
        Some(nr_numa_nodes) => nr_numa_nodes,
        None => return -EINVAL,
    };

    nr_numa_nodes()
}

#[no_mangle]
pub unsafe extern "C" fn host_flush_tlb_result(flush_tlb_fn: HostFlushTlbFn) -> CInt {
    let flush_tlb = match flush_tlb_fn {
        Some(flush_tlb) => flush_tlb,
        None => return -EINVAL,
    };

    flush_tlb();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_arch_map_vdso_result(
    vm: *mut c_void,
    arch_map_vdso_fn: HostArchMapVdsoFn,
) -> CInt {
    let arch_map_vdso = match arch_map_vdso_fn {
        Some(arch_map_vdso) => arch_map_vdso,
        None => return -EINVAL,
    };

    arch_map_vdso(vm)
}

#[no_mangle]
pub unsafe extern "C" fn host_init_process_stack_result(
    thread: *mut c_void,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
    init_stack_fn: HostInitProcessStackFn,
) -> CInt {
    let init_stack = match init_stack_fn {
        Some(init_stack) => init_stack,
        None => return -EINVAL,
    };

    init_stack(thread, pn, at_base, argc, argv, envc, env)
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_proc_result(
    thread: *mut c_void,
    thread_proc_fn: HostThreadProcFn,
) -> *mut c_void {
    let thread_proc = match thread_proc_fn {
        Some(thread_proc) => thread_proc,
        None => return core::ptr::null_mut(),
    };

    thread_proc(thread)
}

#[no_mangle]
pub unsafe extern "C" fn host_current_cpu_result(current_cpu_fn: HostCurrentCpuFn) -> CInt {
    let current_cpu = match current_cpu_fn {
        Some(current_cpu) => current_cpu,
        None => return -EINVAL,
    };

    current_cpu()
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_cpu_allowed_result(
    thread: *mut c_void,
    cpuid: CInt,
    cpu_allowed_fn: HostThreadCpuAllowedFn,
) -> CInt {
    let cpu_allowed = match cpu_allowed_fn {
        Some(cpu_allowed) => cpu_allowed,
        None => return -EINVAL,
    };

    cpu_allowed(thread, cpuid)
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_obtain_cpuid_result(
    thread: *mut c_void,
    obtain_cpuid_fn: HostThreadObtainCpuidFn,
) -> CInt {
    let obtain_cpuid = match obtain_cpuid_fn {
        Some(obtain_cpuid) => obtain_cpuid,
        None => return -EINVAL,
    };

    obtain_cpuid(thread)
}

#[no_mangle]
pub unsafe extern "C" fn host_proc_pid_result(
    proc: *mut c_void,
    proc_pid_fn: HostProcPidFn,
) -> CInt {
    let proc_pid = match proc_pid_fn {
        Some(proc_pid) => proc_pid,
        None => return -EINVAL,
    };

    proc_pid(proc)
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_reg_result(
    thread: *mut c_void,
    thread_reg_fn: HostThreadRegFn,
) -> CULong {
    let thread_reg = match thread_reg_fn {
        Some(thread_reg) => thread_reg,
        None => return 0,
    };

    thread_reg(thread)
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_invalid_log_result(
    thread: *mut c_void,
    log_fn: HostScheduleInvalidLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_received_log_result(
    thread: *mut c_void,
    pid: CInt,
    pc: CULong,
    sp: CULong,
    cpuid: CInt,
    log_fn: HostScheduleReceivedLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(thread, pid, pc, sp, cpuid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_no_cpu_log_result(log_fn: HostScheduleNoCpuLogFn) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_set_tid_result(
    thread: *mut c_void,
    tid: CInt,
    set_tid_fn: HostThreadSetTidFn,
) -> CInt {
    let set_tid = match set_tid_fn {
        Some(set_tid) => set_tid,
        None => return -EINVAL,
    };

    set_tid(thread, tid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_status_set_result(
    object: *mut c_void,
    status: CInt,
    status_set_fn: HostStatusSetFn,
) -> CInt {
    let status_set = match status_set_fn {
        Some(status_set) => status_set,
        None => return -EINVAL,
    };

    status_set(object, status);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_chain_thread_result(
    thread: *mut c_void,
    chain_thread_fn: HostChainThreadFn,
) -> CInt {
    let chain_thread = match chain_thread_fn {
        Some(chain_thread) => chain_thread,
        None => return -EINVAL,
    };

    chain_thread(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_chain_process_result(
    proc: *mut c_void,
    chain_process_fn: HostChainProcessFn,
) -> CInt {
    let chain_process = match chain_process_fn {
        Some(chain_process) => chain_process,
        None => return -EINVAL,
    };

    chain_process(proc);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_runq_add_thread_result(
    thread: *mut c_void,
    cpuid: CInt,
    runq_add_fn: HostRunqAddThreadFn,
) -> CInt {
    let runq_add = match runq_add_fn {
        Some(runq_add) => runq_add,
        None => return -EINVAL,
    };

    runq_add(thread, cpuid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_queued_log_result(
    pid: CInt,
    tid: CInt,
    cpuid: CInt,
    status: CInt,
    log_fn: HostScheduleQueuedLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(pid, tid, cpuid, status);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ack_log_result(log_fn: HostInitAckLogFn) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_process_log_result(
    request: *mut IkcScdPacket,
    log_fn: HostScheduleProcessLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };
    if request.is_null() {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    log((*request_body).arg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_profile_enabled_result(
    thread: *mut c_void,
    profile_enabled_fn: HostThreadProfileEnabledFn,
) -> CInt {
    let profile_enabled = match profile_enabled_fn {
        Some(profile_enabled) => profile_enabled,
        None => return -EINVAL,
    };

    profile_enabled(thread)
}

#[no_mangle]
pub unsafe extern "C" fn host_timestamp_result(timestamp_fn: HostTimestampFn) -> CULong {
    let timestamp = match timestamp_fn {
        Some(timestamp) => timestamp,
        None => return 0,
    };

    timestamp()
}

#[no_mangle]
pub unsafe extern "C" fn host_preempt_result(preempt_fn: HostPreemptFn) -> CInt {
    let preempt = match preempt_fn {
        Some(preempt) => preempt,
        None => return -EINVAL,
    };

    preempt();
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_process_result(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
    page_fault_fn: HostRemotePageFaultFn,
) -> CInt {
    let page_fault = match page_fault_fn {
        Some(page_fault) => page_fault,
        None => return -EINVAL,
    };

    page_fault(thread, fault_address, fault_reason);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_profile_event_result(
    event: CInt,
    delta: CULong,
    profile_event_fn: HostProfileEventFn,
) -> CInt {
    let profile_event = match profile_event_fn {
        Some(profile_event) => profile_event,
        None => return -EINVAL,
    };

    profile_event(event, delta);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_log_result(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
    log_fn: HostRemotePageFaultLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(thread, fault_address, fault_reason);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_alloc_result(
    size: CULong,
    flags: CULong,
    alloc_fn: HostAllocFn,
) -> *mut c_void {
    let alloc = match alloc_fn {
        Some(alloc) => alloc,
        None => return core::ptr::null_mut(),
    };

    alloc(size, flags)
}

#[no_mangle]
pub unsafe extern "C" fn host_packet_copy_result(
    dst: *mut c_void,
    src: *mut IkcScdPacket,
    size: CULong,
    copy_fn: HostPacketCopyFn,
) -> CInt {
    let copy = match copy_fn {
        Some(copy) => copy,
        None => return -EINVAL,
    };

    copy(dst, src, size);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_defer_result(
    thread: *mut c_void,
    arg: *mut c_void,
    backlog_fn: HostBacklogFn,
    defer_fn: HostRemotePageFaultDeferFn,
) -> CInt {
    let defer = match defer_fn {
        Some(defer) => defer,
        None => return -EINVAL,
    };
    if backlog_fn.is_none() {
        return -EINVAL;
    }

    defer(thread, arg, backlog_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_sched_wakeup_result(
    thread: *mut c_void,
    valid_states: CInt,
    wakeup_fn: HostSchedWakeupFn,
) -> CInt {
    let wakeup = match wakeup_fn {
        Some(wakeup) => wakeup,
        None => return -EINVAL,
    };

    wakeup(thread, valid_states)
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_missing_log_result(
    tid: CInt,
    log_fn: HostRemotePageFaultMissingLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(tid);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_cpu_rw_register_result(
    desc: *mut c_void,
    op: CInt,
    rw_register_fn: HostCpuRwRegisterFn,
) -> CInt {
    let rw_register = match rw_register_fn {
        Some(rw_register) => rw_register,
        None => return -EINVAL,
    };

    rw_register(desc, op)
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_process_log_result(
    pid: CInt,
    thread_arg: CULong,
    log_fn: HostCleanupProcessLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(pid, thread_arg);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_terminate_host_result(
    pid: CInt,
    thread: *mut c_void,
    terminate_fn: HostTerminateHostFn,
) -> CInt {
    let terminate = match terminate_fn {
        Some(terminate) => terminate,
        None => return -EINVAL,
    };

    terminate(pid, thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_fd_log_result(
    pid: CInt,
    fd: CULong,
    err: CInt,
    log_fn: HostCleanupFdLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(pid, fd, err);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_do_kill_result(
    pid: CInt,
    tid: CInt,
    sig: CInt,
    info: *mut c_void,
    do_kill_fn: HostDoKillFn,
) -> CULong {
    let do_kill = match do_kill_fn {
        Some(do_kill) => do_kill,
        None => return (-EINVAL as CLong) as CULong,
    };

    do_kill(pid, tid, sig, info)
}

#[no_mangle]
pub unsafe extern "C" fn host_send_signal_log_result(
    pid: CInt,
    tid: CInt,
    sig: CInt,
    rc: CInt,
    log_fn: HostSendSignalLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(pid, tid, sig, rc);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_find_thread_result(
    pid: CInt,
    tid: CInt,
    find_thread_fn: HostFindThreadFn,
) -> *mut c_void {
    let find_thread = match find_thread_fn {
        Some(find_thread) => find_thread,
        None => return core::ptr::null_mut(),
    };

    find_thread(pid, tid)
}

#[no_mangle]
pub unsafe extern "C" fn host_wakeup_thread_result(
    thread: *mut c_void,
    wakeup_fn: HostWakeupThreadFn,
) -> CInt {
    let wakeup = match wakeup_fn {
        Some(wakeup) => wakeup,
        None => return -EINVAL,
    };

    wakeup(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_thread_unlock_result(
    thread: *mut c_void,
    unlock_fn: HostThreadUnlockFn,
) -> CInt {
    let unlock = match unlock_fn {
        Some(unlock) => unlock,
        None => return -EINVAL,
    };

    unlock(thread);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_wake_syscall_log_result(
    tid: CInt,
    found: CInt,
    log_fn: HostWakeSyscallLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };

    log(tid, found);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_debug_log_result(code: CULong, debug_fn: HostDebugLogFn) -> CInt {
    let debug = match debug_fn {
        Some(debug) => debug,
        None => return -EINVAL,
    };

    debug(code);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_debug_log_print_result(
    code: CULong,
    print_fn: HostDebugLogPrintFn,
) -> CInt {
    let print = match print_fn {
        Some(print) => print,
        None => return -EINVAL,
    };

    print(code);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_init_raw_result(
    counter: CInt,
    config: u32,
    mode: CInt,
    init_raw_fn: HostPerfInitRawFn,
) -> CInt {
    let init_raw = match init_raw_fn {
        Some(init_raw) => init_raw,
        None => return -EINVAL,
    };

    init_raw(counter, config, mode)
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_stop_result(
    counter_mask: CULong,
    flags: CInt,
    stop_fn: HostPerfStopFn,
) -> CInt {
    let stop = match stop_fn {
        Some(stop) => stop,
        None => return -EINVAL,
    };

    stop(counter_mask, flags)
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_reset_result(counter: CInt, reset_fn: HostPerfResetFn) -> CInt {
    let reset = match reset_fn {
        Some(reset) => reset,
        None => return -EINVAL,
    };

    reset(counter)
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_start_result(
    counter_mask: CULong,
    start_fn: HostPerfStartFn,
) -> CInt {
    let start = match start_fn {
        Some(start) => start,
        None => return -EINVAL,
    };

    start(counter_mask)
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_read_result(counter: CInt, read_fn: HostPerfReadFn) -> CULong {
    let read = match read_fn {
        Some(read) => read,
        None => return 0,
    };

    read(counter)
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_unexpected_result(unexpected_fn: HostPerfUnexpectedFn) -> CInt {
    let unexpected = match unexpected_fn {
        Some(unexpected) => unexpected,
        None => return -EINVAL,
    };

    unexpected();
    0
}

#[repr(C)]
pub struct IhkIkcConnectParam {
    port: CInt,
    pkt_size: CInt,
    queue_size: CInt,
    magic: CInt,
    intr_cpu: CInt,
    handler: HostIkcPacketHandlerFn,
    channel: *mut c_void,
}

const _: () = {
    assert!(size_of::<IhkIkcConnectParam>() == 40);
    assert!(align_of::<IhkIkcConnectParam>() == 8);
    assert!(offset_of!(IhkIkcConnectParam, port) == 0);
    assert!(offset_of!(IhkIkcConnectParam, pkt_size) == 4);
    assert!(offset_of!(IhkIkcConnectParam, queue_size) == 8);
    assert!(offset_of!(IhkIkcConnectParam, magic) == 12);
    assert!(offset_of!(IhkIkcConnectParam, intr_cpu) == 16);
    assert!(offset_of!(IhkIkcConnectParam, handler) == 24);
    assert!(offset_of!(IhkIkcConnectParam, channel) == 32);
};

#[repr(C)]
struct HostMcctrlSignal {
    cond: CInt,
    sig: CInt,
    pid: CInt,
    tid: CInt,
    info: SigInfo,
}

unsafe fn zero_ikc_scd_packet(packet: *mut IkcScdPacket) {
    let words = size_of::<IkcScdPacket>() / size_of::<CULong>();
    let bytes = size_of::<IkcScdPacket>() % size_of::<CULong>();
    let wordp = packet.cast::<CULong>();
    let mut index = 0;

    while index < words {
        write_volatile(wordp.add(index), 0);
        index += 1;
    }

    let bytep = wordp.add(words).cast::<u8>();
    let mut byte = 0;
    while byte < bytes {
        write_volatile(bytep.add(byte), 0);
        byte += 1;
    }
}

unsafe fn host_prepare_desc_bytes(nsections: CInt) -> CULong {
    size_of::<ProgramLoadDesc>() as CULong
        + (size_of::<ProgramImageSection>() as CULong).wrapping_mul(nsections as CULong)
}

unsafe fn host_prepare_section(
    desc: *mut ProgramLoadDesc,
    index: CInt,
) -> *mut ProgramImageSection {
    desc.cast::<u8>()
        .add(size_of::<ProgramLoadDesc>())
        .cast::<ProgramImageSection>()
        .add(index as usize)
}

fn prot_to_vr_flag(prot: CInt) -> CULong {
    ((prot as CULong) << 16) & VR_PROT_MASK
}

fn vrflag_prot_to_maxprot(vrflag: CULong) -> CULong {
    (vrflag & VR_PROT_MASK) << 4
}

unsafe fn host_prepare_round_pages(
    addr: CULong,
    len: CULong,
    page_size: CULong,
    page_shift: CInt,
) -> CInt {
    (((addr & (page_size - 1))
        .wrapping_add(len)
        .wrapping_add(page_size - 1))
        >> page_shift) as CInt
}

unsafe fn host_prepare_copy_bytes(mut dst: *mut i8, mut src: *const i8, mut len: CULong) {
    while len != 0 {
        write_volatile(dst, read_volatile(src));
        dst = dst.add(1);
        src = src.add(1);
        len -= 1;
    }
}

unsafe fn host_prepare_set_mask_bit(mask: *mut CULong, bit: CInt) {
    let word = (bit as usize) / (CULong::BITS as usize);
    let shift = (bit as u32) % CULong::BITS;
    *mask.add(word) |= 1u64 << shift;
}

unsafe fn host_prepare_clear_process_numa_mask(mask: *mut CULong) {
    let mut word = 0usize;
    while word < PROCESS_NUMA_MASK_WORDS {
        write_volatile(mask.add(word), 0);
        word += 1;
    }
}

unsafe fn host_prepare_test_mask_bit(mask: *const CULong, bit: CInt) -> bool {
    let word = (bit as usize) / (CULong::BITS as usize);
    let shift = (bit as u32) % CULong::BITS;
    (*mask.add(word) & (1u64 << shift)) != 0
}

unsafe fn host_prepare_publish_numa_bind(
    vm: *mut ProcessVm,
    pn: *const ProgramLoadDesc,
    mpol_bind: CInt,
    nr_numa_nodes: CInt,
    log_fn: HostPrepareProcessLogFn,
) -> CInt {
    host_prepare_clear_process_numa_mask((*vm).numa_mask.as_mut_ptr());
    let mut bit = 0;
    while bit < CULong::BITS as CInt {
        if ((*pn).mpol_bind_mask & (1u64 << bit as u32)) != 0 {
            if bit >= nr_numa_nodes {
                if log_fn.is_some() {
                    let _ = host_prepare_process_log_result(
                        HOST_PREPARE_LOG_NUMA_BIND_ERROR,
                        bit as CULong,
                        0,
                        0,
                        log_fn,
                    );
                }
                return -EINVAL;
            }
            host_prepare_set_mask_bit((*vm).numa_mask.as_mut_ptr(), bit);
        }
        bit += 1;
    }
    (*vm).numa_mem_policy = mpol_bind;
    0
}

unsafe fn host_prepare_publish_numa_policy(
    vm: *mut ProcessVm,
    pn: *const ProgramLoadDesc,
    nr_numa_nodes: CInt,
    log_fn: HostPrepareProcessLogFn,
) -> CInt {
    (*vm).numa_mem_policy = (*pn).mpol_mode;
    host_prepare_clear_process_numa_mask((*vm).numa_mask.as_mut_ptr());

    let mut bit = 0;
    while bit < (PLD_NUMA_MASK_WORDS as CInt * CULong::BITS as CInt) {
        if host_prepare_test_mask_bit((*pn).mpol_nodemask.as_ptr(), bit) {
            if bit >= nr_numa_nodes {
                if log_fn.is_some() {
                    let _ = host_prepare_process_log_result(
                        HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR,
                        bit as CULong,
                        0,
                        0,
                        log_fn,
                    );
                }
                return -EINVAL;
            }
            host_prepare_set_mask_bit((*vm).numa_mask.as_mut_ptr(), bit);
        }
        bit += 1;
    }

    if log_fn.is_some() {
        let _ = host_prepare_process_log_result(
            HOST_PREPARE_LOG_NUMA_POLICY,
            (*vm).numa_mem_policy as CULong,
            (*vm).numa_mask[0],
            0,
            log_fn,
        );
    }
    0
}

unsafe fn host_prepare_publish_process_state(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    user_end: CULong,
    ld_task_unmapped_base: CULong,
    sigchld: CInt,
    mpol_max: CInt,
    mpol_bind: CInt,
    nr_numa_nodes: HostNrNumaNodesFn,
    tofu_finalize_fn: HostTofuFinalizeFn,
    log_fn: HostPrepareProcessLogFn,
) -> CInt {
    let proc = (*thread).proc;
    let vm = (*thread).vm;
    if proc.is_null() || vm.is_null() || (*vm).address_space.is_null() {
        return -EINVAL;
    }

    let mut index = 0usize;
    while index < HOST_PREPARE_PTHREAD_MAIN.len() {
        (*thread).pthread_routine[index] = HOST_PREPARE_PTHREAD_MAIN[index];
        index += 1;
    }

    (*proc).pid = (*pn).pid;
    let pids = ((*vm).address_space.cast::<u8>())
        .add(size_of::<AddressSpace>())
        .cast::<CInt>();
    *pids = (*pn).pid;
    (*proc).pgid = (*pn).pgid;
    (*proc).ruid = (*pn).cred[0];
    (*proc).euid = (*pn).cred[1];
    (*proc).suid = (*pn).cred[2];
    (*proc).fsuid = (*pn).cred[3];
    (*proc).rgid = (*pn).cred[4];
    (*proc).egid = (*pn).cred[5];
    (*proc).sgid = (*pn).cred[6];
    (*proc).fsgid = (*pn).cred[7];
    (*proc).termsig = sigchld;
    (*proc).mpol_flags = (*pn).mpol_flags;
    (*proc).mpol_threshold = (*pn).mpol_threshold as usize;
    (*proc).thp_disable = (*pn).thp_disable;
    (*proc).nr_processes = (*pn).nr_processes;
    (*proc).process_rank = (*pn).process_rank;
    (*proc).heap_extension = (*pn).heap_extension;

    if (*pn).mpol_bind_mask != 0 {
        if nr_numa_nodes.is_none() {
            return -EINVAL;
        }
        let rc = host_prepare_publish_numa_bind(
            vm,
            pn,
            mpol_bind,
            host_nr_numa_nodes_result(nr_numa_nodes),
            log_fn,
        );
        if rc != 0 {
            return rc;
        }
    } else if (*pn).mpol_mode != mpol_max {
        if nr_numa_nodes.is_none() {
            return -EINVAL;
        }
        let rc = host_prepare_publish_numa_policy(
            vm,
            pn,
            host_nr_numa_nodes_result(nr_numa_nodes),
            log_fn,
        );
        if rc != 0 {
            return rc;
        }
    }

    (*proc).enable_uti = (*pn).enable_uti;
    (*proc).uti_thread_rank = (*pn).uti_thread_rank;
    (*proc).uti_use_last_cpu = (*pn).uti_use_last_cpu;
    (*proc).straight_map = (*pn).straight_map;
    (*proc).straight_map_threshold = (*pn).straight_map_threshold;

    #[cfg(enable_tofu)]
    {
        (*proc).enable_tofu = (*pn).enable_tofu;
        if (*proc).enable_tofu != 0 {
            if tofu_finalize_fn.is_some() {
                let _ = host_tofu_finalize_result(tofu_finalize_fn);
            }
        }
    }
    #[cfg(not(enable_tofu))]
    {
        let _ = tofu_finalize_fn;
    }

    (*proc).mcexec_flags = (*pn).mcexec_flags;
    if log_fn.is_some() {
        let _ = host_prepare_process_log_result(
            HOST_PREPARE_LOG_PID_FLAGS,
            (*proc).pid as CULong,
            (*proc).mcexec_flags,
            0,
            log_fn,
        );
    }

    let src_rlimit = (*pn).rlimit.as_ptr();
    let dst_rlimit = (*proc).rlimit.as_mut_ptr();
    let mut rlimit_index = 0usize;
    while rlimit_index < (*pn).rlimit.len() {
        (*dst_rlimit.add(rlimit_index)).rlim_cur = (*src_rlimit.add(rlimit_index)).rlim_cur;
        (*dst_rlimit.add(rlimit_index)).rlim_max = (*src_rlimit.add(rlimit_index)).rlim_max;
        rlimit_index += 1;
    }
    if log_fn.is_some() {
        let _ = host_prepare_process_log_result(
            HOST_PREPARE_LOG_RLIMIT,
            (*proc).rlimit[3].rlim_cur,
            (*proc).rlimit[3].rlim_max,
            (*pn).stack_premap as CULong,
            log_fn,
        );
    }

    (*proc).profile = (*pn).profile;
    (*thread).profile = (*pn).profile;

    (*vm).region.user_start = (*pn).user_start;
    (*vm).region.user_end = (*pn).user_end;
    if (*vm).region.user_end > user_end {
        (*vm).region.user_end = user_end;
    }
    (*vm).region.map_start = ld_task_unmapped_base;
    (*vm).region.map_end = ld_task_unmapped_base;

    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_process_body_result(
    rphys: CULong,
    num_processors: CInt,
    attr: CULong,
    page_size: CULong,
    alloc_flags: CULong,
    user_end: CULong,
    ld_task_unmapped_base: CULong,
    sigchld: CInt,
    mpol_max: CInt,
    mpol_bind: CInt,
    monitor_status_fn: HostMonitorStatusFn,
    map_memory_fn: HostMapMemoryFn,
    map_virtual_fn: HostPrepareMapVirtualFn,
    unmap_virtual_fn: HostUnmapVirtualFn,
    unmap_memory_fn: HostUnmapMemoryFn,
    alloc_fn: HostAllocFn,
    free_fn: HostFreeFn,
    copy_long_fn: HostCopyLongFn,
    create_thread_fn: HostCreateThreadFn,
    destroy_thread_fn: HostDestroyThreadFn,
    prepare_ranges_fn: HostPrepareRangesFn,
    nr_numa_nodes_fn: HostNrNumaNodesFn,
    flush_tlb_fn: HostFlushTlbFn,
    tofu_finalize_fn: HostTofuFinalizeFn,
    log_fn: HostPrepareProcessLogFn,
) -> CInt {
    if monitor_status_fn.is_none()
        || map_memory_fn.is_none()
        || map_virtual_fn.is_none()
        || unmap_virtual_fn.is_none()
        || unmap_memory_fn.is_none()
        || alloc_fn.is_none()
        || free_fn.is_none()
        || copy_long_fn.is_none()
        || create_thread_fn.is_none()
        || destroy_thread_fn.is_none()
        || prepare_ranges_fn.is_none()
        || flush_tlb_fn.is_none()
        || page_size == 0
    {
        return -EINVAL;
    }

    let mut cpu = 0;
    while cpu < num_processors {
        let status = host_monitor_status_result(cpu, monitor_status_fn);
        if status == IHK_OS_MONITOR_KERNEL_FREEZING || status == IHK_OS_MONITOR_KERNEL_FROZEN {
            return -EAGAIN;
        }
        cpu += 1;
    }

    let fixed_desc_bytes = size_of::<ProgramLoadDesc>() as CULong
        + (size_of::<ProgramImageSection>() as CULong)
            .wrapping_mul(HOST_PREPARE_MAX_SECTIONS as CULong);
    let npages = ((rphys.wrapping_add(fixed_desc_bytes).wrapping_sub(1)) / page_size)
        .wrapping_sub(rphys / page_size)
        .wrapping_add(1) as CInt;

    let phys = host_map_memory_result(
        core::ptr::null_mut(),
        rphys,
        fixed_desc_bytes,
        map_memory_fn,
    );
    let p = host_prepare_map_virtual_result(phys, npages, attr, map_virtual_fn)
        .cast::<ProgramLoadDesc>();
    if p.is_null() {
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            phys,
            fixed_desc_bytes,
            unmap_memory_fn,
        );
        return -ENOMEM;
    }

    if (*p).magic != PLD_MAGIC {
        if log_fn.is_some() {
            let _ = host_prepare_process_log_result(HOST_PREPARE_LOG_BROKEN_DESC, 0, 0, 0, log_fn);
        }
        let _ = host_unmap_virtual_result(p.cast::<c_void>(), npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            phys,
            fixed_desc_bytes,
            unmap_memory_fn,
        );
        return -EFAULT;
    }

    let nsections = (*p).num_sections;
    if nsections > HOST_PREPARE_MAX_SECTIONS || nsections <= 0 {
        if log_fn.is_some() {
            let _ = host_prepare_process_log_result(
                HOST_PREPARE_LOG_INVALID_SECTIONS,
                nsections as CULong,
                0,
                0,
                log_fn,
            );
        }
        return -ENOMEM;
    }
    if log_fn.is_some() {
        let _ = host_prepare_process_log_result(
            HOST_PREPARE_LOG_NUM_SECTIONS,
            nsections as CULong,
            0,
            0,
            log_fn,
        );
    }

    let clone_bytes = host_prepare_desc_bytes(nsections);
    let pn =
        host_prepare_alloc_result(clone_bytes, alloc_flags, alloc_fn).cast::<ProgramLoadDesc>();
    if pn.is_null() {
        let _ = host_unmap_virtual_result(p.cast::<c_void>(), npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            phys,
            fixed_desc_bytes,
            unmap_memory_fn,
        );
        return -ENOMEM;
    }
    let _ = host_prepare_copy_long_result(
        pn.cast::<c_void>(),
        p.cast::<c_void>(),
        clone_bytes,
        copy_long_fn,
    );

    let thread = host_create_thread_result(
        (*p).entry,
        (*p).cpu_set.as_mut_ptr(),
        size_of_val(&(*p).cpu_set) as CULong,
        create_thread_fn,
    );
    if thread.is_null() {
        let _ = host_prepare_free_result(pn.cast::<c_void>(), free_fn);
        let _ = host_unmap_virtual_result(p.cast::<c_void>(), npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            phys,
            fixed_desc_bytes,
            unmap_memory_fn,
        );
        return -ENOMEM;
    }

    let mut error = host_prepare_publish_process_state(
        thread,
        pn,
        user_end,
        ld_task_unmapped_base,
        sigchld,
        mpol_max,
        mpol_bind,
        nr_numa_nodes_fn,
        tofu_finalize_fn,
        log_fn,
    );
    if error != 0 {
        return error;
    }

    error = host_prepare_ranges_result(
        thread,
        pn,
        p,
        attr,
        core::ptr::null_mut(),
        0,
        core::ptr::null_mut(),
        0,
        prepare_ranges_fn,
    );
    if error != 0 {
        if log_fn.is_some() {
            let _ = host_prepare_process_log_result(
                HOST_PREPARE_LOG_PREPARE_ERROR,
                error as CULong,
                0,
                0,
                log_fn,
            );
        }
        let _ = host_prepare_free_result(pn.cast::<c_void>(), free_fn);
        let _ = host_unmap_virtual_result(p.cast::<c_void>(), npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            phys,
            fixed_desc_bytes,
            unmap_memory_fn,
        );
        let _ = host_destroy_thread_result(thread, destroy_thread_fn);
        return -ENOMEM;
    }

    if log_fn.is_some() {
        let proc = (*thread).proc;
        let vm = (*thread).vm;
        let _ = host_prepare_process_log_result(
            HOST_PREPARE_LOG_NEW_PROCESS,
            proc as CULong,
            if proc.is_null() {
                0
            } else {
                (*proc).pid as CULong
            },
            if vm.is_null() {
                0
            } else {
                (*vm).address_space as CULong
            },
            log_fn,
        );
    }

    let _ = host_prepare_free_result(pn.cast::<c_void>(), free_fn);
    let _ = host_unmap_virtual_result(p.cast::<c_void>(), npages, unmap_virtual_fn);
    let _ = host_unmap_memory_result(
        core::ptr::null_mut(),
        phys,
        fixed_desc_bytes,
        unmap_memory_fn,
    );
    let _ = host_flush_tlb_result(flush_tlb_fn);

    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_ranges_sections_result(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    at_basep: *mut CULong,
    page_size: CULong,
    page_mask: CULong,
    large_page_size: CULong,
    large_page_mask: CULong,
    task_unmapped_base: CULong,
    page_shift: CInt,
    large_page_shift: CInt,
    alloc_nowait: CULong,
    alloc_user: CULong,
    mpol_no_bss: CULong,
    pf_populate: CULong,
    user_context_pc_reg: CInt,
    add_range_fn: HostPrepareAddRangeFn,
    alloc_pages_fn: HostPrepareAllocPagesUserFn,
    free_pages_fn: HostPrepareFreePagesUserFn,
    virt_to_phys_fn: HostVirtToPhysFn,
    arch_vrflag_to_ptattr_fn: HostArchVrflagToPtattrFn,
    pt_set_range_fn: HostPtSetRangeFn,
    modify_context_fn: HostModifyUserContextFn,
    log_fn: HostPrepareRangesLogFn,
) -> CInt {
    if thread.is_null()
        || pn.is_null()
        || p.is_null()
        || at_basep.is_null()
        || page_size == 0
        || add_range_fn.is_none()
        || alloc_pages_fn.is_none()
        || free_pages_fn.is_none()
        || virt_to_phys_fn.is_none()
        || arch_vrflag_to_ptattr_fn.is_none()
        || pt_set_range_fn.is_none()
    {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    if proc.is_null() {
        return -EINVAL;
    }
    let vm = (*proc).vm;
    if vm.is_null() || (*vm).address_space.is_null() {
        return -EINVAL;
    }

    let n = (*p).num_sections;
    (*vm).region.data_start = CULong::MAX;
    let aout_base = if (*pn).reloc != 0 {
        (*vm).region.map_end
    } else {
        0
    };
    let mut interp_obase = CULong::MAX;
    let mut interp_nbase = CULong::MAX;
    let mut i = 0;

    while i < n {
        let pn_sec = host_prepare_section(pn, i);
        let p_sec = host_prepare_section(p, i);
        let mut ap_flags = 0;

        if (*pn_sec).interp != 0 && interp_nbase == CULong::MAX {
            let interp_align = (*pn).interp_align;
            if interp_align == 0 {
                return -EINVAL;
            }
            interp_obase = (*pn_sec).vaddr;
            interp_obase = interp_obase.wrapping_sub(interp_obase % interp_align);
            interp_nbase = (*vm).region.map_end;
            interp_nbase = interp_nbase.wrapping_add(interp_align - 1) & !(interp_align - 1);
        }

        if (*pn_sec).interp != 0 {
            (*pn_sec).vaddr = (*pn_sec)
                .vaddr
                .wrapping_sub(interp_obase)
                .wrapping_add(interp_nbase);
            (*p_sec).vaddr = (*pn_sec).vaddr;
        } else {
            (*pn_sec).vaddr = (*pn_sec).vaddr.wrapping_add(aout_base);
            (*p_sec).vaddr = (*pn_sec).vaddr;
        }

        let start = (*pn_sec).vaddr & page_mask;
        let end = (*pn_sec)
            .vaddr
            .wrapping_add((*pn_sec).len)
            .wrapping_add(page_size - 1)
            & page_mask;
        let range_npages = (((*pn_sec).vaddr.wrapping_sub(start))
            .wrapping_add((*pn_sec).filesz)
            .wrapping_add(page_size - 1)
            >> page_shift) as CInt;
        let mut flags = VR_NONE | prot_to_vr_flag((*pn_sec).prot) | VR_DEMAND_PAGING;
        flags |= vrflag_prot_to_maxprot(flags);

        if i >= 1 && (*pn_sec).len >= (*pn).mpol_threshold && ((*pn).mpol_flags & mpol_no_bss) == 0
        {
            ap_flags = alloc_user;
            flags |= VR_AP_USER;
            if log_fn.is_some() {
                let _ = host_prepare_ranges_log_result(
                    HOST_PREPARE_RANGES_LOG_AP_USER,
                    i as CULong,
                    range_npages as CULong,
                    0,
                    log_fn,
                );
            }
        }

        let mut range_void: *mut c_void = core::ptr::null_mut();
        let mut error = host_prepare_add_range_result(
            vm.cast::<c_void>(),
            start,
            end,
            NOPHYS,
            flags,
            if (*pn_sec).len > large_page_size {
                large_page_shift
            } else {
                page_shift
            },
            &mut range_void,
            add_range_fn,
        );
        if error != 0 {
            if log_fn.is_some() {
                let _ = host_prepare_ranges_log_result(
                    HOST_PREPARE_RANGES_LOG_ADD_FAILED,
                    i as CULong,
                    error as CULong,
                    0,
                    log_fn,
                );
            }
            return error;
        }
        let range = range_void.cast::<VmRange>();
        if range.is_null() {
            return -EINVAL;
        }

        let up_v = host_prepare_alloc_pages_user_result(
            range_npages,
            alloc_nowait | ap_flags,
            start,
            alloc_pages_fn,
        );
        if up_v.is_null() {
            if log_fn.is_some() {
                let _ = host_prepare_ranges_log_result(
                    HOST_PREPARE_RANGES_LOG_ALLOC_FAILED,
                    i as CULong,
                    0,
                    0,
                    log_fn,
                );
            }
            return -ENOMEM;
        }

        let up = host_virt_to_phys_result(up_v, virt_to_phys_fn);
        let ptattr = host_arch_vrflag_to_ptattr_result(
            (*range).flag,
            pf_populate,
            core::ptr::null_mut(),
            arch_vrflag_to_ptattr_fn,
        );
        error = host_pt_set_range_result(
            (*(*vm).address_space).page_table,
            vm.cast::<c_void>(),
            (*range).start,
            (*range)
                .start
                .wrapping_add((range_npages as CULong).wrapping_mul(page_size)),
            up,
            ptattr,
            (*range).pgshift,
            range.cast::<c_void>(),
            0,
            pt_set_range_fn,
        );
        if error != 0 {
            if log_fn.is_some() {
                let _ = host_prepare_ranges_log_result(
                    HOST_PREPARE_RANGES_LOG_PT_FAILED,
                    i as CULong,
                    error as CULong,
                    0,
                    log_fn,
                );
            }
            let _ = host_prepare_free_pages_user_result(up_v, range_npages, free_pages_fn);
            return error;
        }

        (*p_sec).remote_pa = up;
        if (*pn_sec).interp != 0 {
            (*vm).region.map_end = end;
        } else if ((*pn_sec).prot & PROT_EXEC) != 0 {
            (*vm).region.text_start = start;
            (*vm).region.text_end = end;
        } else {
            if start < (*vm).region.data_start {
                (*vm).region.data_start = start;
            }
            if end > (*vm).region.data_end {
                (*vm).region.data_end = end;
            }
        }

        if aout_base != 0 {
            (*vm).region.map_end = end;
        }

        i += 1;
    }

    *at_basep = 0;
    if interp_nbase != CULong::MAX {
        *at_basep = interp_nbase.wrapping_sub(interp_obase);
        (*pn).entry = (*pn)
            .entry
            .wrapping_sub(interp_obase)
            .wrapping_add(interp_nbase);
        (*p).entry = (*pn).entry;
        if modify_context_fn.is_some() {
            let _ = host_modify_user_context_result(
                (*thread).uctx.cast::<c_void>(),
                user_context_pc_reg,
                (*pn).entry,
                modify_context_fn,
            );
        }
    }

    if aout_base != 0 {
        (*pn).at_phdr = (*pn).at_phdr.wrapping_add(aout_base);
        (*pn).at_entry = (*pn).at_entry.wrapping_add(aout_base);
    }

    (*vm).region.map_start = task_unmapped_base;
    (*vm).region.map_end = task_unmapped_base;
    (*vm).region.brk_start =
        ((*vm).region.data_end.wrapping_add(large_page_size - 1)) & large_page_mask;
    (*vm).region.brk_end = (*vm).region.brk_start;

    if (*vm).region.brk_start >= (*vm).region.map_start {
        if log_fn.is_some() {
            let _ = host_prepare_ranges_log_result(
                HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE,
                (*vm).region.data_end,
                (*vm).region.map_start,
                0,
                log_fn,
            );
        }
        return -ENOMEM;
    }

    (*vm).region.brk_end_allocated = (*vm).region.brk_end;
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_ranges_args_envs_result(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    attr: CULong,
    args: *mut i8,
    args_len: CInt,
    envs: *mut i8,
    envs_len: CInt,
    at_base: CULong,
    page_size: CULong,
    page_mask: CULong,
    page_shift: CInt,
    alloc_nowait: CULong,
    add_range_fn: HostPrepareAddRangeFn,
    alloc_pages_fn: HostPrepareAllocPagesUserFn,
    free_pages_fn: HostPrepareFreePagesUserFn,
    virt_to_phys_fn: HostVirtToPhysFn,
    map_memory_fn: HostMapMemoryFn,
    map_virtual_fn: HostPrepareMapVirtualFn,
    unmap_virtual_fn: HostUnmapVirtualFn,
    unmap_memory_fn: HostUnmapMemoryFn,
    copy_long_fn: HostCopyLongFn,
    alloc_fn: HostAllocFn,
    free_fn: HostFreeFn,
    flush_tlb_fn: HostFlushTlbFn,
    arch_map_vdso_fn: HostArchMapVdsoFn,
    init_stack_fn: HostInitProcessStackFn,
    log_fn: HostPrepareArgsLogFn,
) -> CInt {
    let _ = page_mask;
    if thread.is_null()
        || pn.is_null()
        || p.is_null()
        || page_size == 0
        || add_range_fn.is_none()
        || alloc_pages_fn.is_none()
        || free_pages_fn.is_none()
        || virt_to_phys_fn.is_none()
        || map_memory_fn.is_none()
        || map_virtual_fn.is_none()
        || unmap_virtual_fn.is_none()
        || unmap_memory_fn.is_none()
        || copy_long_fn.is_none()
        || alloc_fn.is_none()
        || free_fn.is_none()
        || flush_tlb_fn.is_none()
        || init_stack_fn.is_none()
    {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    if proc.is_null() {
        return -EINVAL;
    }
    let vm = (*proc).vm;
    if vm.is_null() || (*vm).address_space.is_null() {
        return -EINVAL;
    }
    let aspace = (*vm).address_space;

    let mut argenv_page_count = if args.is_null() {
        host_prepare_round_pages((*p).args as CULong, (*p).args_len, page_size, page_shift)
    } else {
        ((args_len as CULong).wrapping_add(page_size - 1) >> page_shift) as CInt
    };
    argenv_page_count += if envs.is_null() {
        host_prepare_round_pages((*p).envs as CULong, (*p).envs_len, page_size, page_shift)
    } else {
        ((envs_len as CULong).wrapping_add(page_size - 1) >> page_shift) as CInt
    };

    let addr = (*vm)
        .region
        .map_start
        .wrapping_sub(page_size.wrapping_mul(argenv_page_count as CULong));
    let end = addr.wrapping_add(page_size.wrapping_mul(argenv_page_count as CULong));

    let args_envs = host_prepare_alloc_pages_user_result(
        argenv_page_count,
        alloc_nowait,
        CULong::MAX,
        alloc_pages_fn,
    )
    .cast::<i8>();
    if args_envs.is_null() {
        if log_fn.is_some() {
            let _ = host_prepare_args_log_result(
                HOST_PREPARE_ARGS_LOG_ALLOC_FAILED,
                argenv_page_count as CULong,
                0,
                0,
                log_fn,
            );
        }
        return -ENOMEM;
    }

    let args_envs_p = host_virt_to_phys_result(args_envs.cast::<c_void>(), virt_to_phys_fn);
    let mut flags = VR_PROT_READ | VR_PROT_WRITE | VR_PRIVATE;
    flags |= vrflag_prot_to_maxprot(flags);
    let mut error = host_prepare_add_range_result(
        vm.cast::<c_void>(),
        addr,
        end,
        args_envs_p,
        flags,
        page_shift,
        core::ptr::null_mut(),
        add_range_fn,
    );
    if error != 0 {
        let _ = host_prepare_free_pages_user_result(
            args_envs.cast::<c_void>(),
            argenv_page_count,
            free_pages_fn,
        );
        if log_fn.is_some() {
            let _ = host_prepare_args_log_result(
                HOST_PREPARE_ARGS_LOG_ADD_FAILED,
                error as CULong,
                0,
                0,
                log_fn,
            );
        }
        return error;
    }

    let mut mapped_npages = 0;
    let mut mapped_phys = 0;
    let args_src = if args.is_null() {
        mapped_npages =
            host_prepare_round_pages((*p).args as CULong, (*p).args_len, page_size, page_shift);
        mapped_phys = host_map_memory_result(
            core::ptr::null_mut(),
            (*p).args as CULong,
            (*p).args_len,
            map_memory_fn,
        );
        let mapped =
            host_prepare_map_virtual_result(mapped_phys, mapped_npages, attr, map_virtual_fn)
                .cast::<i8>();
        if mapped.is_null() {
            if log_fn.is_some() {
                let _ = host_prepare_args_log_result(
                    HOST_PREPARE_ARGS_LOG_ARGS_MAP_FAILED,
                    mapped_phys,
                    0,
                    0,
                    log_fn,
                );
            }
            return -EFAULT;
        }
        mapped
    } else {
        (*p).args_len = args_len as CULong;
        args
    };

    let _ = host_prepare_copy_long_result(
        args_envs.cast::<c_void>(),
        args_src.cast::<c_void>() as *const c_void,
        (*p).args_len
            .wrapping_add(size_of::<CULong>() as CULong - 1),
        copy_long_fn,
    );
    if args.is_null() {
        let _ =
            host_unmap_virtual_result(args_src.cast::<c_void>(), mapped_npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            mapped_phys,
            (*p).args_len,
            unmap_memory_fn,
        );
    }
    let _ = host_flush_tlb_result(flush_tlb_fn);

    let env_src = if envs.is_null() {
        mapped_npages =
            host_prepare_round_pages((*p).envs as CULong, (*p).envs_len, page_size, page_shift);
        mapped_phys = host_map_memory_result(
            core::ptr::null_mut(),
            (*p).envs as CULong,
            (*p).envs_len,
            map_memory_fn,
        );
        let mapped =
            host_prepare_map_virtual_result(mapped_phys, mapped_npages, attr, map_virtual_fn)
                .cast::<i8>();
        if mapped.is_null() {
            if log_fn.is_some() {
                let _ = host_prepare_args_log_result(
                    HOST_PREPARE_ARGS_LOG_ENVS_MAP_FAILED,
                    mapped_phys,
                    0,
                    0,
                    log_fn,
                );
            }
            return -EFAULT;
        }
        mapped
    } else {
        (*p).envs_len = envs_len as CULong;
        envs
    };

    let envs_offset = ((*p)
        .args_len
        .wrapping_add(size_of::<CULong>() as CULong - 1))
        & !((size_of::<CULong>() as CULong) - 1);
    let _ = host_prepare_copy_long_result(
        args_envs.add(envs_offset as usize).cast::<c_void>(),
        env_src.cast::<c_void>() as *const c_void,
        (*p).envs_len
            .wrapping_add(size_of::<CULong>() as CULong - 1),
        copy_long_fn,
    );
    if envs.is_null() {
        let _ =
            host_unmap_virtual_result(env_src.cast::<c_void>(), mapped_npages, unmap_virtual_fn);
        let _ = host_unmap_memory_result(
            core::ptr::null_mut(),
            mapped_phys,
            (*p).envs_len,
            unmap_memory_fn,
        );
    }
    let _ = host_flush_tlb_result(flush_tlb_fn);

    let argc = *(args_envs.cast::<CLong>()) as CInt;
    let argv = args_envs.add(size_of::<CLong>()).cast::<*mut i8>();

    if !(*proc).saved_cmdline.is_null() {
        let _ = host_prepare_free_result((*proc).saved_cmdline.cast::<c_void>(), free_fn);
        write_volatile(
            core::ptr::addr_of_mut!((*proc).saved_cmdline),
            core::ptr::null_mut(),
        );
        write_volatile(core::ptr::addr_of_mut!((*proc).saved_cmdline_len), 0);
    }
    let argv_header_bytes =
        ((argc as CULong).wrapping_add(2)).wrapping_mul(size_of::<*mut i8>() as CULong);
    (*proc).saved_cmdline_len = (*p).args_len.wrapping_sub(argv_header_bytes) as CLong;
    (*proc).saved_cmdline =
        host_prepare_alloc_result((*proc).saved_cmdline_len as CULong, alloc_nowait, alloc_fn)
            .cast::<i8>();
    if (*proc).saved_cmdline.is_null() {
        if log_fn.is_some() {
            let _ = host_prepare_args_log_result(
                HOST_PREPARE_ARGS_LOG_CMDLINE_ALLOC_FAILED,
                (*proc).saved_cmdline_len as CULong,
                0,
                0,
                log_fn,
            );
        }
        return -ENOMEM;
    }
    if (*proc).saved_cmdline_len > 0 {
        host_prepare_copy_bytes(
            (*proc).saved_cmdline,
            args_envs.add(argv_header_bytes as usize).cast::<i8>(),
            (*proc).saved_cmdline_len as CULong,
        );
    }
    if log_fn.is_some() {
        let _ = host_prepare_args_log_result(
            HOST_PREPARE_ARGS_LOG_CMDLINE,
            (*proc).saved_cmdline as CULong,
            (*proc).saved_cmdline_len as CULong,
            0,
            log_fn,
        );
    }

    let mut i = 0;
    while i < argc {
        let slot = argv.add(i as usize);
        let value = read_volatile(slot) as CULong;
        write_volatile(slot, addr.wrapping_add(value) as *mut i8);
        i += 1;
    }

    let envc = *(args_envs.add(envs_offset as usize).cast::<CLong>()) as CInt;
    let env = args_envs
        .add(envs_offset as usize + size_of::<CLong>())
        .cast::<*mut i8>();
    i = 0;
    while i < envc {
        let slot = env.add(i as usize);
        let value = read_volatile(slot) as CULong;
        write_volatile(
            slot,
            addr.wrapping_add(envs_offset).wrapping_add(value) as *mut i8,
        );
        i += 1;
    }

    if (*pn).enable_vdso != 0 {
        if arch_map_vdso_fn.is_none() {
            return -EINVAL;
        }
        error = host_arch_map_vdso_result(vm.cast::<c_void>(), arch_map_vdso_fn);
        if error != 0 {
            if log_fn.is_some() {
                let _ = host_prepare_args_log_result(
                    HOST_PREPARE_ARGS_LOG_VDSO_FAILED,
                    error as CULong,
                    0,
                    0,
                    log_fn,
                );
            }
            return error;
        }
    } else {
        (*vm).vdso_addr = core::ptr::null_mut();
    }

    (*p).rprocess = thread as CULong;
    (*p).rpgtable = host_virt_to_phys_result((*aspace).page_table, virt_to_phys_fn);

    error = host_init_process_stack_result(
        thread.cast::<c_void>(),
        pn,
        at_base,
        argc,
        argv,
        envc,
        env,
        init_stack_fn,
    );
    if error != 0 {
        if log_fn.is_some() {
            let _ = host_prepare_args_log_result(
                HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED,
                error as CULong,
                0,
                0,
                log_fn,
            );
        }
        return error;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn host_schedule_process_request_result(
    request: *mut IkcScdPacket,
    proc_fn: HostThreadProcFn,
    current_cpu_fn: HostCurrentCpuFn,
    cpu_allowed_fn: HostThreadCpuAllowedFn,
    obtain_cpuid_fn: HostThreadObtainCpuidFn,
    proc_pid_fn: HostProcPidFn,
    pc_fn: HostThreadRegFn,
    sp_fn: HostThreadRegFn,
    invalid_log_fn: HostScheduleInvalidLogFn,
    received_log_fn: HostScheduleReceivedLogFn,
    no_cpu_log_fn: HostScheduleNoCpuLogFn,
    set_tid_fn: HostThreadSetTidFn,
    set_proc_status_fn: HostStatusSetFn,
    set_thread_status_fn: HostStatusSetFn,
    chain_thread_fn: HostChainThreadFn,
    chain_process_fn: HostChainProcessFn,
    runq_add_fn: HostRunqAddThreadFn,
    queued_log_fn: HostScheduleQueuedLogFn,
    running_status: CInt,
) -> CInt {
    if request.is_null()
        || proc_fn.is_none()
        || current_cpu_fn.is_none()
        || cpu_allowed_fn.is_none()
        || obtain_cpuid_fn.is_none()
        || proc_pid_fn.is_none()
        || set_tid_fn.is_none()
        || set_proc_status_fn.is_none()
        || set_thread_status_fn.is_none()
        || chain_thread_fn.is_none()
        || chain_process_fn.is_none()
        || runq_add_fn.is_none()
    {
        return -EINVAL;
    }

    let traditional = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let thread = (*traditional).arg as *mut c_void;
    let proc = if thread.is_null() {
        core::ptr::null_mut()
    } else {
        host_thread_proc_result(thread, proc_fn)
    };
    if thread.is_null() || proc.is_null() {
        if invalid_log_fn.is_some() {
            let _ = host_schedule_invalid_log_result(thread, invalid_log_fn);
        }
        return -EINVAL;
    }

    let mut cpuid = host_current_cpu_result(current_cpu_fn);
    let pid = host_proc_pid_result(proc, proc_pid_fn);
    if received_log_fn.is_some() {
        if pc_fn.is_none() || sp_fn.is_none() {
            return -EINVAL;
        }
        let pc = host_thread_reg_result(thread, pc_fn);
        let sp = host_thread_reg_result(thread, sp_fn);
        let _ = host_schedule_received_log_result(thread, pid, pc, sp, cpuid, received_log_fn);
    }

    if host_thread_cpu_allowed_result(thread, cpuid, cpu_allowed_fn) == 0 {
        cpuid = host_thread_obtain_cpuid_result(thread, obtain_cpuid_fn);
        if cpuid == -1 {
            if no_cpu_log_fn.is_some() {
                let _ = host_schedule_no_cpu_log_result(no_cpu_log_fn);
            }
            return -1;
        }
    }

    let _ = host_thread_set_tid_result(thread, pid, set_tid_fn);
    let _ = host_status_set_result(proc, running_status, set_proc_status_fn);
    let _ = host_status_set_result(thread, running_status, set_thread_status_fn);
    let _ = host_chain_thread_result(thread, chain_thread_fn);
    let _ = host_chain_process_result(proc, chain_process_fn);
    let _ = host_runq_add_thread_result(thread, cpuid, runq_add_fn);
    if queued_log_fn.is_some() {
        let _ = host_schedule_queued_log_result(pid, pid, cpuid, running_status, queued_log_fn);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_answer_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    err: CInt,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || send_fn.is_none() {
        return -EINVAL;
    }

    let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
    zero_ikc_scd_packet(packet.as_mut_ptr());
    let answer = packet.as_mut_ptr();
    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let answer_body = (&raw mut (*answer).body).cast::<IkcScdPacketTraditional>();

    (*answer).msg = SCD_MSG_REMOTE_PAGE_FAULT_ANSWER;
    (*answer_body).ref_ = (*request_body).ref_;
    (*answer_body).arg = (*request_body).arg;
    (*answer).err = err;
    (*answer).reply = (*request).reply;
    (*answer_body).pid = (*request_body).pid;
    let _ = host_ikc_packet_send_result(channel, answer, send_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_body_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    err: CInt,
    current_thread: *mut c_void,
    populate_flag: CULong,
    profile_event: CInt,
    profile_enabled_fn: HostThreadProfileEnabledFn,
    timestamp_fn: HostTimestampFn,
    preempt_disable_fn: HostPreemptFn,
    page_fault_fn: HostRemotePageFaultFn,
    preempt_enable_fn: HostPreemptFn,
    profile_event_fn: HostProfileEventFn,
    log_fn: HostRemotePageFaultLogFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || send_fn.is_none() {
        return -EINVAL;
    }

    if err != 0 {
        return host_remote_page_fault_answer_result(channel, request, err, send_fn);
    }

    if current_thread.is_null()
        || profile_enabled_fn.is_none()
        || preempt_disable_fn.is_none()
        || page_fault_fn.is_none()
        || preempt_enable_fn.is_none()
    {
        return -EINVAL;
    }

    let profiled = host_thread_profile_enabled_result(current_thread, profile_enabled_fn) != 0;
    let mut start = 0;
    if profiled {
        if timestamp_fn.is_none() || profile_event_fn.is_none() {
            return -EINVAL;
        }
        start = host_timestamp_result(timestamp_fn);
    }

    let remote_pf = (&raw mut (*request).body).cast::<crate::abi::IkcScdPacketRemotePageFault>();
    let reason = (*remote_pf).fault_reason | populate_flag;
    if log_fn.is_some() {
        let _ = host_remote_page_fault_log_result(
            current_thread,
            (*remote_pf).fault_address,
            reason,
            log_fn,
        );
    }

    let _ = host_preempt_result(preempt_disable_fn);
    let _ = host_remote_page_fault_process_result(
        current_thread,
        (*remote_pf).fault_address,
        reason,
        page_fault_fn,
    );
    let _ = host_preempt_result(preempt_enable_fn);

    if profiled {
        let _ = host_profile_event_result(
            profile_event,
            host_timestamp_result(timestamp_fn).wrapping_sub(start),
            profile_event_fn,
        );
    }

    host_remote_page_fault_answer_result(channel, request, err, send_fn)
}

#[no_mangle]
#[allow(clippy::too_many_arguments)]
pub unsafe extern "C" fn host_remote_page_fault_current_result(
    request: *mut IkcScdPacket,
    err: CInt,
    populate_flag: CULong,
    profile_event: CInt,
    response_channel_fn: HostCurrentPtrFn,
    current_thread_fn: HostCurrentPtrFn,
    profile_enabled_fn: HostThreadProfileEnabledFn,
    timestamp_fn: HostTimestampFn,
    preempt_disable_fn: HostPreemptFn,
    page_fault_fn: HostRemotePageFaultFn,
    preempt_enable_fn: HostPreemptFn,
    profile_event_fn: HostProfileEventFn,
    log_fn: HostRemotePageFaultLogFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if response_channel_fn.is_none() || current_thread_fn.is_none() {
        return -EINVAL;
    }

    host_remote_page_fault_body_result(
        host_current_ptr_result(response_channel_fn),
        request,
        err,
        host_current_ptr_result(current_thread_fn),
        populate_flag,
        profile_event,
        profile_enabled_fn,
        timestamp_fn,
        preempt_disable_fn,
        page_fault_fn,
        preempt_enable_fn,
        profile_event_fn,
        log_fn,
        send_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_body_dispatch_result(
    request: *mut IkcScdPacket,
    err: CInt,
    body_fn: HostRemotePageFaultBodyFn,
) -> CInt {
    let body = match body_fn {
        Some(body) => body,
        None => return -EINVAL,
    };
    if request.is_null() {
        return -EINVAL;
    }

    body(request, err);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_request_result(
    request: *mut IkcScdPacket,
    find_thread_fn: HostFindThreadFn,
    current_thread: *mut c_void,
    body_fn: HostRemotePageFaultBodyFn,
    alloc_fn: HostAllocFn,
    copy_fn: HostPacketCopyFn,
    defer_fn: HostRemotePageFaultDeferFn,
    wakeup_fn: HostSchedWakeupFn,
    unlock_fn: HostThreadUnlockFn,
    log_fn: HostRemotePageFaultMissingLogFn,
    backlog_fn: HostBacklogFn,
    packet_size: CULong,
    alloc_flags: CULong,
    interruptible_state: CInt,
) -> CInt {
    if request.is_null() || find_thread_fn.is_none() || body_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }

    let remote_pf = (&raw mut (*request).body).cast::<crate::abi::IkcScdPacketRemotePageFault>();
    let tid = (*remote_pf).fault_tid;
    let thread = host_find_thread_result(0, tid, find_thread_fn);
    if thread.is_null() {
        let _ = host_remote_page_fault_missing_log_result(tid, log_fn);
        let _ = host_remote_page_fault_body_dispatch_result(request, -EINVAL, body_fn);
        return 0;
    }

    if thread == current_thread {
        let _ = host_remote_page_fault_body_dispatch_result(request, 0, body_fn);
        let _ = host_thread_unlock_result(thread, unlock_fn);
        return 0;
    }

    if alloc_fn.is_none()
        || copy_fn.is_none()
        || defer_fn.is_none()
        || wakeup_fn.is_none()
        || backlog_fn.is_none()
    {
        return -EINVAL;
    }

    let deferred_arg = host_alloc_result(packet_size, alloc_flags, alloc_fn);
    if deferred_arg.is_null() {
        let _ = host_thread_unlock_result(thread, unlock_fn);
        return -ENOMEM;
    }

    let _ = host_packet_copy_result(deferred_arg, request, packet_size, copy_fn);
    let _ = host_remote_page_fault_defer_result(thread, deferred_arg, backlog_fn, defer_fn);
    let _ = host_sched_wakeup_result(thread, interruptible_state, wakeup_fn);
    let _ = host_thread_unlock_result(thread, unlock_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_traditional_reply_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    msg: CInt,
    err: CInt,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || send_fn.is_none() {
        return -EINVAL;
    }

    let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
    zero_ikc_scd_packet(packet.as_mut_ptr());
    let reply = packet.as_mut_ptr();
    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let reply_body = (&raw mut (*reply).body).cast::<IkcScdPacketTraditional>();

    (*reply).msg = msg;
    (*reply).err = err;
    (*reply_body).ref_ = (*request_body).ref_;
    (*reply_body).arg = (*request_body).arg;
    (*reply).reply = (*request).reply;
    let _ = host_ikc_packet_send_result(channel, reply, send_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_arg_reply_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    msg: CInt,
    err: CInt,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || send_fn.is_none() {
        return -EINVAL;
    }

    let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
    zero_ikc_scd_packet(packet.as_mut_ptr());
    let reply = packet.as_mut_ptr();
    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let reply_body = (&raw mut (*reply).body).cast::<IkcScdPacketTraditional>();

    (*reply).msg = msg;
    (*reply).err = err;
    (*reply_body).arg = (*request_body).arg;
    (*reply).reply = (*request).reply;
    let _ = host_ikc_packet_send_result(channel, reply, send_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_reply_only_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    msg: CInt,
    err: CInt,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || send_fn.is_none() {
        return -EINVAL;
    }

    let mut packet = core::mem::MaybeUninit::<IkcScdPacket>::uninit();
    zero_ikc_scd_packet(packet.as_mut_ptr());
    let reply = packet.as_mut_ptr();

    (*reply).msg = msg;
    (*reply).err = err;
    (*reply).reply = (*request).reply;
    let _ = host_ikc_packet_send_result(channel, reply, send_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_ctrl_result(
    desc: *mut PerfCtrlDesc,
    init_raw_fn: HostPerfInitRawFn,
    stop_fn: HostPerfStopFn,
    reset_fn: HostPerfResetFn,
    start_fn: HostPerfStartFn,
    read_fn: HostPerfReadFn,
    unexpected_fn: HostPerfUnexpectedFn,
) -> CInt {
    if desc.is_null() {
        return -EINVAL;
    }

    match (*desc).ctrl_type {
        PERF_CTRL_SET => {
            if init_raw_fn.is_none() || stop_fn.is_none() || reset_fn.is_none() {
                return -EINVAL;
            }
            let counter = &raw mut (*desc).body.counter;
            let mut mode = 0;
            if (*counter).flags & PERF_CTRL_EXCLUDE_KERNEL == 0 {
                mode |= PERFCTR_KERNEL_MODE;
            }
            if (*counter).flags & PERF_CTRL_EXCLUDE_USER == 0 {
                mode |= PERFCTR_USER_MODE;
            }

            let target = (*counter).target_cntr;
            let ret = host_perf_init_raw_result(
                target as CInt,
                (*counter).config as u32,
                mode,
                init_raw_fn,
            );
            if ret != 0 {
                return ret;
            }

            let ret = host_perf_stop_result((1u32.wrapping_shl(target)) as CULong, 0, stop_fn);
            if ret != 0 {
                return ret;
            }

            host_perf_reset_result(target as CInt, reset_fn)
        }
        PERF_CTRL_ENABLE => {
            if start_fn.is_none() {
                return -EINVAL;
            }
            host_perf_start_result((*desc).body.mask.target_cntr_mask, start_fn)
        }
        PERF_CTRL_DISABLE => {
            if stop_fn.is_none() {
                return -EINVAL;
            }
            host_perf_stop_result(
                (*desc).body.mask.target_cntr_mask,
                IHK_MC_PERFCTR_DISABLE_INTERRUPT,
                stop_fn,
            )
        }
        PERF_CTRL_GET => {
            if read_fn.is_none() {
                return -EINVAL;
            }
            let counter = &raw mut (*desc).body.counter;
            (*counter).read_value = host_perf_read_result((*counter).target_cntr as CInt, read_fn);
            0
        }
        _ => {
            if unexpected_fn.is_some() {
                let _ = host_perf_unexpected_result(unexpected_fn);
            }
            0
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn host_perf_ctrl_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    map_memory_fn: HostMapMemoryFn,
    map_virtual_fn: HostMapVirtualFn,
    unmap_virtual_fn: HostUnmapVirtualFn,
    unmap_memory_fn: HostUnmapMemoryFn,
    init_raw_fn: HostPerfInitRawFn,
    stop_fn: HostPerfStopFn,
    reset_fn: HostPerfResetFn,
    start_fn: HostPerfStartFn,
    read_fn: HostPerfReadFn,
    unexpected_fn: HostPerfUnexpectedFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null()
        || map_memory_fn.is_none()
        || map_virtual_fn.is_none()
        || unmap_virtual_fn.is_none()
        || unmap_memory_fn.is_none()
        || send_fn.is_none()
    {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let size = size_of::<PerfCtrlDesc>() as CULong;
    let phys = host_map_memory_result(
        core::ptr::null_mut(),
        (*request_body).arg,
        size,
        map_memory_fn,
    );
    let desc = host_map_virtual_result(phys, 1, PTATTR_WRITABLE | PTATTR_ACTIVE, map_virtual_fn)
        .cast::<PerfCtrlDesc>();
    let ret = host_perf_ctrl_result(
        desc,
        init_raw_fn,
        stop_fn,
        reset_fn,
        start_fn,
        read_fn,
        unexpected_fn,
    );

    if !desc.is_null() {
        let _ = host_unmap_virtual_result(desc.cast::<c_void>(), 1, unmap_virtual_fn);
    }
    let _ = host_unmap_memory_result(core::ptr::null_mut(), phys, size, unmap_memory_fn);

    let _ = host_arg_reply_result(channel, request, SCD_MSG_PERF_ACK, ret, send_fn);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn host_cpu_rw_reg_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    map_memory_fn: HostMapMemoryFn,
    map_virtual_fn: HostMapVirtualFn,
    unmap_virtual_fn: HostUnmapVirtualFn,
    unmap_memory_fn: HostUnmapMemoryFn,
    rw_register_fn: HostCpuRwRegisterFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null()
        || map_memory_fn.is_none()
        || map_virtual_fn.is_none()
        || unmap_virtual_fn.is_none()
        || unmap_memory_fn.is_none()
        || rw_register_fn.is_none()
        || send_fn.is_none()
    {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketCpuRw>();
    let size = size_of::<IhkOsCpuRegister>() as CULong;
    let phys = host_map_memory_result(
        core::ptr::null_mut(),
        (*request_body).pdesc,
        size,
        map_memory_fn,
    );
    let desc = host_map_virtual_result(phys, 1, PTATTR_WRITABLE | PTATTR_ACTIVE, map_virtual_fn);
    let ret = if desc.is_null() {
        -EINVAL
    } else {
        host_cpu_rw_register_result(desc, (*request_body).op, rw_register_fn)
    };

    if !desc.is_null() {
        let _ = host_unmap_virtual_result(desc, 1, unmap_virtual_fn);
    }
    let _ = host_unmap_memory_result(core::ptr::null_mut(), phys, size, unmap_memory_fn);

    let _ = host_reply_only_result(channel, request, SCD_MSG_CPU_RW_REG_RESP, ret, send_fn);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_process_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    cleanup_fn: HostCleanupProcessFn,
    terminate_fn: HostTerminateHostFn,
    log_fn: HostCleanupProcessLogFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || cleanup_fn.is_none() || terminate_fn.is_none() || send_fn.is_none() {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    if log_fn.is_some() {
        let _ = host_cleanup_process_log_result((*request_body).pid, (*request_body).arg, log_fn);
    }
    let ret = host_cleanup_process_result((*request_body).pid, cleanup_fn);
    let _ =
        host_traditional_reply_result(channel, request, SCD_MSG_CLEANUP_PROCESS_RESP, ret, send_fn);
    let _ = host_terminate_host_result(
        (*request_body).pid,
        (*request_body).arg as *mut c_void,
        terminate_fn,
    );
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_cleanup_fd_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    cleanup_fn: HostCleanupFdFn,
    log_fn: HostCleanupFdLogFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || cleanup_fn.is_none() || send_fn.is_none() {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let ret = host_cleanup_fd_result((*request_body).pid, (*request_body).arg as CInt, cleanup_fn);
    if log_fn.is_some() {
        let _ = host_cleanup_fd_log_result((*request_body).pid, (*request_body).arg, ret, log_fn);
    }
    let _ = host_traditional_reply_result(channel, request, SCD_MSG_CLEANUP_FD_RESP, ret, send_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_send_signal_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    map_memory_fn: HostMapMemoryFn,
    map_virtual_fn: HostMapVirtualFn,
    unmap_virtual_fn: HostUnmapVirtualFn,
    unmap_memory_fn: HostUnmapMemoryFn,
    do_kill_fn: HostDoKillFn,
    log_fn: HostSendSignalLogFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null()
        || map_memory_fn.is_none()
        || map_virtual_fn.is_none()
        || unmap_virtual_fn.is_none()
        || unmap_memory_fn.is_none()
        || do_kill_fn.is_none()
        || send_fn.is_none()
    {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let size = size_of::<HostMcctrlSignal>() as CULong;
    let phys = host_map_memory_result(
        core::ptr::null_mut(),
        (*request_body).arg,
        size,
        map_memory_fn,
    );
    let mapped = host_map_virtual_result(phys, 1, PTATTR_WRITABLE | PTATTR_ACTIVE, map_virtual_fn)
        .cast::<HostMcctrlSignal>();
    if mapped.is_null() {
        let _ = host_unmap_memory_result(core::ptr::null_mut(), phys, size, unmap_memory_fn);
        let _ = host_traditional_reply_result(
            channel,
            request,
            SCD_MSG_SEND_SIGNAL_ACK,
            -EINVAL,
            send_fn,
        );
        return -EINVAL;
    }

    let mut info = core::mem::MaybeUninit::<HostMcctrlSignal>::uninit();
    core::ptr::copy_nonoverlapping(mapped, info.as_mut_ptr(), 1);
    let _ = host_unmap_virtual_result(mapped.cast::<c_void>(), 1, unmap_virtual_fn);
    let _ = host_unmap_memory_result(core::ptr::null_mut(), phys, size, unmap_memory_fn);

    let signal = info.as_mut_ptr();
    let _ = host_traditional_reply_result(channel, request, SCD_MSG_SEND_SIGNAL_ACK, 0, send_fn);
    let rc = host_do_kill_result(
        (*signal).pid,
        (*signal).tid,
        (*signal).sig,
        (&raw mut (*signal).info).cast::<c_void>(),
        do_kill_fn,
    ) as CInt;
    if log_fn.is_some() {
        let _ =
            host_send_signal_log_result((*signal).pid, (*signal).tid, (*signal).sig, rc, log_fn);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_wake_syscall_thread_request_result(
    request: *mut IkcScdPacket,
    find_thread_fn: HostFindThreadFn,
    wakeup_fn: HostWakeupThreadFn,
    unlock_fn: HostThreadUnlockFn,
    log_fn: HostWakeSyscallLogFn,
) -> CInt {
    if request.is_null() || find_thread_fn.is_none() || wakeup_fn.is_none() || unlock_fn.is_none() {
        return -EINVAL;
    }

    let tid = (*request).body.ttid;
    let thread = host_find_thread_result(0, tid, find_thread_fn);
    if thread.is_null() {
        if log_fn.is_some() {
            let _ = host_wake_syscall_log_result(tid, 0, log_fn);
        }
        return -EINVAL;
    }

    if log_fn.is_some() {
        let _ = host_wake_syscall_log_result(tid, 1, log_fn);
    }
    let _ = host_wakeup_thread_result(thread, wakeup_fn);
    let _ = host_thread_unlock_result(thread, unlock_fn);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_debug_log_request_result(
    request: *mut IkcScdPacket,
    debug_fn: HostDebugLogFn,
    print_fn: HostDebugLogPrintFn,
) -> CInt {
    if request.is_null() || debug_fn.is_none() {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let code = (*request_body).arg;
    if print_fn.is_some() {
        let _ = host_debug_log_print_result(code, print_fn);
    }
    host_debug_log_result(code, debug_fn)
}

#[no_mangle]
pub unsafe extern "C" fn host_response_packet_result(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
    response_fn: HostResponsePacketFn,
) -> CInt {
    let response = match response_fn {
        Some(response) => response,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    response(response_channel, packet)
}

#[no_mangle]
pub unsafe extern "C" fn host_packet_dispatch_result(
    packet: *mut IkcScdPacket,
    dispatch_fn: HostPacketDispatchFn,
) -> CInt {
    let dispatch = match dispatch_fn {
        Some(dispatch) => dispatch,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    dispatch(packet)
}

#[no_mangle]
pub unsafe extern "C" fn host_remote_page_fault_dispatch_result(
    packet: *mut IkcScdPacket,
    current_thread: *mut c_void,
    dispatch_fn: HostRemotePageFaultDispatchFn,
) -> CInt {
    let dispatch = match dispatch_fn {
        Some(dispatch) => dispatch,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    dispatch(packet, current_thread)
}

#[no_mangle]
pub unsafe extern "C" fn host_procfs_packet_dispatch_result(
    packet: *mut IkcScdPacket,
    procfs_request_fn: HostProcfsRequestFn,
) -> CInt {
    let procfs_request = match procfs_request_fn {
        Some(procfs_request) => procfs_request,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    let _ = procfs_request(packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_scd_packet_dispatch_result(
    channel: *mut c_void,
    packet: *mut IkcScdPacket,
    response_channel: *mut c_void,
    current_thread: *mut c_void,
    ops: *const HostScdDispatchOps,
    _populate_flag: CULong,
    _profile_event: CInt,
    _packet_size: CULong,
    _alloc_flags: CULong,
    _interruptible_state: CInt,
    _running_status: CInt,
) -> CInt {
    if packet.is_null() || ops.is_null() {
        return -EINVAL;
    }

    let ops = &*ops;
    if ops.release_packet_fn.is_none() {
        return -EINVAL;
    }

    let ret = match (*packet).msg {
        SCD_MSG_INIT_CHANNEL_ACKED => {
            if ops.init_ack_log_fn.is_some() {
                let _ = host_init_ack_log_result(ops.init_ack_log_fn);
            }
            0
        }
        SCD_MSG_PREPARE_PROCESS => {
            if ops.prepare_process_fn.is_some() {
                let _ =
                    host_response_packet_result(response_channel, packet, ops.prepare_process_fn);
                0
            } else {
                -EINVAL
            }
        }
        SCD_MSG_SCHEDULE_PROCESS => host_packet_dispatch_result(packet, ops.schedule_process_fn),
        SCD_MSG_WAKE_UP_SYSCALL_THREAD => {
            host_packet_dispatch_result(packet, ops.wake_syscall_thread_fn)
        }
        SCD_MSG_REMOTE_PAGE_FAULT => {
            host_remote_page_fault_dispatch_result(packet, current_thread, ops.remote_page_fault_fn)
        }
        SCD_MSG_SEND_SIGNAL => {
            if ops.send_signal_fn.is_some() {
                let _ = host_response_packet_result(response_channel, packet, ops.send_signal_fn);
                0
            } else {
                -EINVAL
            }
        }
        SCD_MSG_PROCFS_REQUEST | SCD_MSG_PROCFS_RELEASE => {
            host_procfs_packet_dispatch_result(packet, ops.procfs_request_fn)
        }
        SCD_MSG_CLEANUP_PROCESS => {
            if ops.cleanup_process_fn.is_some() {
                let _ =
                    host_response_packet_result(response_channel, packet, ops.cleanup_process_fn);
                0
            } else {
                -EINVAL
            }
        }
        SCD_MSG_CLEANUP_FD => {
            if ops.cleanup_fd_fn.is_some() {
                let _ = host_response_packet_result(response_channel, packet, ops.cleanup_fd_fn);
                0
            } else {
                -EINVAL
            }
        }
        SCD_MSG_DEBUG_LOG => host_packet_dispatch_result(packet, ops.debug_log_fn),
        SCD_MSG_SYSFS_REQ_SHOW | SCD_MSG_SYSFS_REQ_STORE | SCD_MSG_SYSFS_REQ_RELEASE => {
            if ops.sysfs_packet_fn.is_some() {
                let request = (&raw mut (*packet).body).cast::<IkcScdPacketSysfs>();
                host_sysfs_packet_result(
                    channel,
                    (*packet).msg,
                    (*packet).err,
                    (*request).sysfs_arg1,
                    (*request).sysfs_arg2,
                    (*request).sysfs_arg3,
                    ops.sysfs_packet_fn,
                )
            } else {
                -EINVAL
            }
        }
        SCD_MSG_PERF_CTRL => {
            host_response_packet_result(response_channel, packet, ops.perf_ctrl_fn)
        }
        SCD_MSG_CPU_RW_REG => {
            if ops.cpu_rw_reg_fn.is_some() {
                let _ = host_response_packet_result(response_channel, packet, ops.cpu_rw_reg_fn);
                0
            } else {
                -EINVAL
            }
        }
        _ => {
            if ops.unknown_packet_log_fn.is_some() {
                let _ = host_unknown_packet_log_result(packet, ops.unknown_packet_log_fn);
            }
            0
        }
    };

    let _ = host_release_packet_result(packet, ops.release_packet_fn);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn host_prepare_process_request_result(
    channel: *mut c_void,
    request: *mut IkcScdPacket,
    prepare_fn: HostPrepareProcessFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if request.is_null() || prepare_fn.is_none() {
        return -EINVAL;
    }

    let request_body = (&raw mut (*request).body).cast::<IkcScdPacketTraditional>();
    let ret = host_prepare_process_result((*request_body).arg, prepare_fn);
    host_traditional_reply_result(
        channel,
        request,
        SCD_MSG_PREPARE_PROCESS_ACKED,
        ret,
        send_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn host_procfs_request_result(
    request: *mut IkcScdPacket,
    procfs_request_fn: HostProcfsRequestFn,
) -> CInt {
    let procfs_request = match procfs_request_fn {
        Some(procfs_request) => procfs_request,
        None => return -EINVAL,
    };
    if request.is_null() {
        return -EINVAL;
    }

    procfs_request(request)
}

#[no_mangle]
pub unsafe extern "C" fn host_sysfs_packet_result(
    channel: *mut c_void,
    msg: CInt,
    err: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
    sysfs_packet_fn: HostSysfsPacketFn,
) -> CInt {
    let sysfs_packet = match sysfs_packet_fn {
        Some(sysfs_packet) => sysfs_packet,
        None => return -EINVAL,
    };

    sysfs_packet(channel, msg, err, arg1, arg2, arg3);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_unknown_packet_log_result(
    packet: *mut IkcScdPacket,
    log_fn: HostUnknownPacketLogFn,
) -> CInt {
    let log = match log_fn {
        Some(log) => log,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    log(packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_release_packet_result(
    packet: *mut IkcScdPacket,
    release_packet_fn: HostReleasePacketFn,
) -> CInt {
    let release_packet = match release_packet_fn {
        Some(release_packet) => release_packet,
        None => return -EINVAL,
    };
    if packet.is_null() {
        return -EINVAL;
    }

    release_packet(packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_release_packet_dispatch_result(
    packet: *mut IkcScdPacket,
    release_packet_fn: HostReleasePacketFn,
) -> CInt {
    let release_packet = match release_packet_fn {
        Some(release_packet) => release_packet,
        None => return -EINVAL,
    };

    release_packet(packet);
    0
}

#[no_mangle]
pub unsafe extern "C" fn host_procfs_answer_current_result(
    request: *mut IkcScdPacket,
    err: CInt,
    response_channel_fn: HostCurrentPtrFn,
    send_fn: HostIkcPacketSendFn,
) -> CInt {
    if response_channel_fn.is_none() {
        return -EINVAL;
    }

    crate::object_helpers::procfs_answer_result(
        host_current_ptr_result(response_channel_fn),
        request,
        err,
        send_fn,
    )
}

#[no_mangle]
pub unsafe extern "C" fn host_syscall_packet_handler_result(
    channel: *mut c_void,
    packet: *mut c_void,
    os: *mut c_void,
    ops: *const HostScdDispatchOps,
    response_channel_fn: HostCurrentPtrFn,
    current_thread_fn: HostCurrentPtrFn,
    populate_flag: CULong,
    profile_event: CInt,
    packet_size: CULong,
    alloc_flags: CULong,
    interruptible_state: CInt,
    running_status: CInt,
) -> CInt {
    if response_channel_fn.is_none() || current_thread_fn.is_none() {
        return -EINVAL;
    }

    let _ = os;
    host_scd_packet_dispatch_result(
        channel,
        packet.cast::<IkcScdPacket>(),
        host_current_ptr_result(response_channel_fn),
        host_current_ptr_result(current_thread_fn),
        ops,
        populate_flag,
        profile_event,
        packet_size,
        alloc_flags,
        interruptible_state,
        running_status,
    )
}

#[no_mangle]
pub unsafe extern "C" fn host_dummy_packet_handler_result(
    channel: *mut c_void,
    packet: *mut c_void,
    os: *mut c_void,
    release_packet_fn: HostReleasePacketFn,
) -> CInt {
    let _ = channel;
    let _ = os;
    host_release_packet_dispatch_result(packet.cast::<IkcScdPacket>(), release_packet_fn)
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ikc2linux_result(
    linux_cpu: CInt,
    ikc2linuxsp: *mut *mut *mut c_void,
    nr_linux_cores: CInt,
    num_processors: CInt,
    packet_size: CULong,
    page_size: CULong,
    alloc_flags: CULong,
    alloc_fn: HostAllocFn,
    connect_fn: HostIkcConnectFn,
    delay_fn: HostDelayFn,
    set_current_fn: HostSetCurrentIkc2linuxFn,
    dummy_handler_fn: HostIkcPacketHandlerFn,
    log_fn: HostInitIkcLogFn,
    panic_fn: HostPanicFn,
) -> CInt {
    if ikc2linuxsp.is_null()
        || alloc_fn.is_none()
        || connect_fn.is_none()
        || delay_fn.is_none()
        || set_current_fn.is_none()
        || dummy_handler_fn.is_none()
    {
        return -EINVAL;
    }

    if (*ikc2linuxsp).is_null() {
        let table_bytes = size_of::<*mut c_void>() as CULong * nr_linux_cores as CULong;
        let table = host_alloc_result(table_bytes, alloc_flags, alloc_fn).cast::<*mut c_void>();
        if table.is_null() {
            let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_ALLOC_ERROR, log_fn);
            let _ = host_panic_result(panic_fn);
            return -ENOMEM;
        }
        core::ptr::write_bytes(table, 0, nr_linux_cores as usize);
        *ikc2linuxsp = table;
    }

    let channels = *ikc2linuxsp;
    let slot = channels.add(linux_cpu as usize);
    let mut channel = *slot;
    if channel.is_null() {
        let mut param = IhkIkcConnectParam {
            port: 503,
            pkt_size: packet_size as CInt,
            queue_size: 0,
            magic: 0x1129,
            intr_cpu: linux_cpu,
            handler: dummy_handler_fn,
            channel: core::ptr::null_mut(),
        };
        let mut queue_size = 4u64
            .wrapping_mul(num_processors as CULong)
            .wrapping_mul(packet_size);
        let min_queue_size = page_size.wrapping_mul(4);
        if queue_size < min_queue_size {
            queue_size = min_queue_size;
        }
        param.queue_size = queue_size as CInt;

        let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_TRY_CONNECT, log_fn);
        while host_ikc_connect_result(&mut param, connect_fn) != 0 {
            let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_RETRY_DOT, log_fn);
            let _ = host_delay_result(1000 * 1000, delay_fn);
        }
        let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_CONNECTED, log_fn);

        channel = param.channel;
        *slot = channel;
    }

    host_set_current_ikc2linux_result(channel, set_current_fn)
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ikc2mckernel_result(
    packet_size: CULong,
    page_size: CULong,
    processor_id: CInt,
    handler_fn: HostIkcPacketHandlerFn,
    connect_fn: HostIkcConnectFn,
    delay_fn: HostDelayFn,
    set_regular_fn: HostIkcSetRegularChannelFn,
    log_fn: HostInitIkcLogFn,
) -> CInt {
    if handler_fn.is_none()
        || connect_fn.is_none()
        || delay_fn.is_none()
        || set_regular_fn.is_none()
    {
        return -EINVAL;
    }

    let mut param = IhkIkcConnectParam {
        port: 501,
        pkt_size: packet_size as CInt,
        queue_size: page_size.wrapping_mul(4) as CInt,
        magic: 0x1329,
        intr_cpu: -1,
        handler: handler_fn,
        channel: core::ptr::null_mut(),
    };

    let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_TRY_CONNECT, log_fn);
    while host_ikc_connect_result(&mut param, connect_fn) != 0 {
        let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_RETRY_DOT, log_fn);
        let _ = host_delay_result(1000 * 1000, delay_fn);
    }
    let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_CONNECTED, log_fn);

    host_ikc_set_regular_channel_result(param.channel, processor_id, set_regular_fn)
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ikc2linux_public_result(
    linux_cpu: CInt,
    ikc2linuxsp: *mut *mut *mut c_void,
    nr_linux_cores: CInt,
    num_processors: CInt,
    packet_size: CULong,
    page_size: CULong,
    alloc_flags: CULong,
    alloc_fn: HostAllocFn,
    connect_fn: HostIkcConnectFn,
    delay_fn: HostDelayFn,
    set_current_fn: HostSetCurrentIkc2linuxFn,
    dummy_handler_fn: HostIkcPacketHandlerFn,
    log_fn: HostInitIkcLogFn,
    panic_fn: HostPanicFn,
) -> CInt {
    if alloc_fn.is_none() {
        let _ = host_panic_result(panic_fn);
        return -EINVAL;
    }
    if connect_fn.is_none() {
        let _ = host_panic_result(panic_fn);
        return -EINVAL;
    }
    if delay_fn.is_none() {
        let _ = host_panic_result(panic_fn);
        return -EINVAL;
    }
    if set_current_fn.is_none() {
        let _ = host_panic_result(panic_fn);
        return -EINVAL;
    }
    if ikc2linuxsp.is_null() || dummy_handler_fn.is_none() {
        let _ = host_panic_result(panic_fn);
        return -EINVAL;
    }

    if (*ikc2linuxsp).is_null() {
        let table_bytes = size_of::<*mut c_void>() as CULong * nr_linux_cores as CULong;
        let table = host_alloc_result(table_bytes, alloc_flags, alloc_fn).cast::<*mut c_void>();
        if table.is_null() {
            let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_ALLOC_ERROR, log_fn);
            let _ = host_panic_result(panic_fn);
            let _ = host_panic_result(panic_fn);
            return -ENOMEM;
        }
        core::ptr::write_bytes(table, 0, nr_linux_cores as usize);
        *ikc2linuxsp = table;
    }

    let channels = *ikc2linuxsp;
    let slot = channels.add(linux_cpu as usize);
    let mut channel = *slot;
    if channel.is_null() {
        let mut param = IhkIkcConnectParam {
            port: 503,
            pkt_size: packet_size as CInt,
            queue_size: 0,
            magic: 0x1129,
            intr_cpu: linux_cpu,
            handler: dummy_handler_fn,
            channel: core::ptr::null_mut(),
        };
        let mut queue_size = 4u64
            .wrapping_mul(num_processors as CULong)
            .wrapping_mul(packet_size);
        let min_queue_size = page_size.wrapping_mul(4);
        if queue_size < min_queue_size {
            queue_size = min_queue_size;
        }
        param.queue_size = queue_size as CInt;

        let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_TRY_CONNECT, log_fn);
        while host_ikc_connect_result(&mut param, connect_fn) != 0 {
            let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_RETRY_DOT, log_fn);
            let _ = host_delay_result(1000 * 1000, delay_fn);
        }
        let _ = host_init_ikc_log_result(HOST_INIT_IKC_LOG_CONNECTED, log_fn);

        channel = param.channel;
        *slot = channel;
    }

    host_set_current_ikc2linux_result(channel, set_current_fn)
}

#[no_mangle]
pub unsafe extern "C" fn host_init_ikc2mckernel_public_result(
    packet_size: CULong,
    page_size: CULong,
    processor_id: CInt,
    handler_fn: HostIkcPacketHandlerFn,
    connect_fn: HostIkcConnectFn,
    delay_fn: HostDelayFn,
    set_regular_fn: HostIkcSetRegularChannelFn,
    log_fn: HostInitIkcLogFn,
    panic_fn: HostPanicFn,
) -> CInt {
    let rc = host_init_ikc2mckernel_result(
        packet_size,
        page_size,
        processor_id,
        handler_fn,
        connect_fn,
        delay_fn,
        set_regular_fn,
        log_fn,
    );
    if rc != 0 {
        let _ = host_panic_result(panic_fn);
    }
    rc
}

#[no_mangle]
pub unsafe extern "C" fn check_mapping_for_proc(thread: *mut Thread, addr: CULong) {
    if thread.is_null() || (*thread).vm.is_null() || (*(*thread).vm).address_space.is_null() {
        let _ = kprintf(CHECK_MAP_MISSING_FMT.as_ptr().cast::<c_char>(), addr);
        return;
    }

    let mut phys = 0;
    let page_table = (*(*(*thread).vm).address_space).page_table;
    if ihk_mc_pt_virt_to_phys(page_table, addr as *mut c_void, &mut phys) != 0 {
        let _ = kprintf(CHECK_MAP_MISSING_FMT.as_ptr().cast::<c_char>(), addr);
    } else {
        let _ = kprintf(CHECK_MAP_HIT_FMT.as_ptr().cast::<c_char>(), addr, phys);
    }
}

unsafe extern "C" fn host_prepare_add_range_raw_bridge(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut c_void,
) -> CInt {
    let mut range: *mut VmRange = core::ptr::null_mut();
    let rc = add_process_memory_range(
        vm.cast::<ProcessVm>(),
        start,
        end,
        phys,
        flag,
        core::ptr::null_mut(),
        0,
        pgshift,
        core::ptr::null_mut(),
        &mut range,
    );
    if !rangep.is_null() {
        *rangep = range.cast::<c_void>();
    }
    rc
}

unsafe extern "C" fn host_prepare_add_range_bridge(
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    flag: CULong,
    pgshift: CInt,
    rangep: *mut *mut c_void,
) -> CInt {
    host_prepare_add_range_result(
        vm,
        start,
        end,
        phys,
        flag,
        pgshift,
        rangep,
        Some(host_prepare_add_range_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_alloc_pages_user_raw_bridge(
    npages: CInt,
    flags: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        flags,
        -1,
        IHK_MC_PG_USER,
        virt_addr,
        host_file_ptr(),
        line!() as CInt,
    )
}

unsafe extern "C" fn host_prepare_alloc_pages_user_bridge(
    npages: CInt,
    flags: CULong,
    virt_addr: CULong,
) -> *mut c_void {
    host_prepare_alloc_pages_user_result(
        npages,
        flags,
        virt_addr,
        Some(host_prepare_alloc_pages_user_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_free_pages_user_raw_bridge(addr: *mut c_void, npages: CInt) {
    _ihk_mc_free_pages(
        addr,
        npages,
        IHK_MC_PG_USER,
        host_file_ptr(),
        line!() as CInt,
    );
}

unsafe extern "C" fn host_prepare_free_pages_user_bridge(addr: *mut c_void, npages: CInt) {
    let _ = host_prepare_free_pages_user_result(
        addr,
        npages,
        Some(host_prepare_free_pages_user_raw_bridge),
    );
}

unsafe extern "C" fn host_prepare_virt_to_phys_raw_bridge(addr: *mut c_void) -> CULong {
    virt_to_phys(addr)
}

unsafe extern "C" fn host_prepare_virt_to_phys_bridge(addr: *mut c_void) -> CULong {
    host_virt_to_phys_result(addr, Some(host_prepare_virt_to_phys_raw_bridge))
}

unsafe extern "C" fn host_prepare_arch_vrflag_to_ptattr_raw_bridge(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
) -> CULong {
    arch_vrflag_to_ptattr(flag, fault, ptep)
}

unsafe extern "C" fn host_prepare_arch_vrflag_to_ptattr_bridge(
    flag: CULong,
    fault: CULong,
    ptep: *mut c_void,
) -> CULong {
    host_arch_vrflag_to_ptattr_result(
        flag,
        fault,
        ptep,
        Some(host_prepare_arch_vrflag_to_ptattr_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_pt_set_range_raw_bridge(
    page_table: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut c_void,
    flags: CInt,
) -> CInt {
    ihk_mc_pt_set_range(
        page_table,
        vm,
        start as *mut c_void,
        end as *mut c_void,
        phys,
        attr,
        pgshift,
        range,
        flags,
    )
}

unsafe extern "C" fn host_prepare_pt_set_range_bridge(
    page_table: *mut c_void,
    vm: *mut c_void,
    start: CULong,
    end: CULong,
    phys: CULong,
    attr: CULong,
    pgshift: CInt,
    range: *mut c_void,
    flags: CInt,
) -> CInt {
    host_pt_set_range_result(
        page_table,
        vm,
        start,
        end,
        phys,
        attr,
        pgshift,
        range,
        flags,
        Some(host_prepare_pt_set_range_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_modify_user_context_raw_bridge(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
) {
    ihk_mc_modify_user_context(uctx, reg, value);
}

unsafe extern "C" fn host_prepare_modify_user_context_bridge(
    uctx: *mut c_void,
    reg: CInt,
    value: CULong,
) {
    let _ = host_modify_user_context_result(
        uctx,
        reg,
        value,
        Some(host_prepare_modify_user_context_raw_bridge),
    );
}

unsafe extern "C" fn host_prepare_ranges_log_raw_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    let _ = arg2;
    match event {
        HOST_PREPARE_RANGES_LOG_AP_USER => {
            let _ = kprintf(
                b"%s: section: %lu size: %lu pages -> IHK_MC_AP_USER\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_ranges_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
                arg1,
            );
        }
        HOST_PREPARE_RANGES_LOG_ADD_FAILED => {
            let _ = kprintf(
                b"ERROR: adding memory range for ELF section %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        HOST_PREPARE_RANGES_LOG_ALLOC_FAILED => {
            let _ = kprintf(
                b"ERROR: alloc pages for ELF section %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        HOST_PREPARE_RANGES_LOG_PT_FAILED => {
            let _ = kprintf(
                b"%s: ihk_mc_pt_set_range failed. %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_ranges_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg1,
            );
        }
        HOST_PREPARE_RANGES_LOG_DATA_TOO_LARGE => {
            let _ = kprintf(
                b"%s: ERROR: data section is too large (end addr: %lx)\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_ranges_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        _ => {}
    }
}

unsafe extern "C" fn host_prepare_ranges_log_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    let _ = host_prepare_ranges_log_result(
        event,
        arg0,
        arg1,
        arg2,
        Some(host_prepare_ranges_log_raw_bridge),
    );
}

unsafe extern "C" fn host_prepare_arch_map_vdso_raw_bridge(vm: *mut c_void) -> CInt {
    arch_map_vdso(vm.cast::<ProcessVm>())
}

unsafe extern "C" fn host_prepare_arch_map_vdso_bridge(vm: *mut c_void) -> CInt {
    host_arch_map_vdso_result(vm, Some(host_prepare_arch_map_vdso_raw_bridge))
}

unsafe extern "C" fn host_prepare_init_stack_raw_bridge(
    thread: *mut c_void,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
) -> CInt {
    init_process_stack(thread.cast::<Thread>(), pn, at_base, argc, argv, envc, env)
}

unsafe extern "C" fn host_prepare_init_stack_bridge(
    thread: *mut c_void,
    pn: *mut ProgramLoadDesc,
    at_base: CULong,
    argc: CInt,
    argv: *mut *mut i8,
    envc: CInt,
    env: *mut *mut i8,
) -> CInt {
    host_init_process_stack_result(
        thread,
        pn,
        at_base,
        argc,
        argv,
        envc,
        env,
        Some(host_prepare_init_stack_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_args_log_raw_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    let _ = (arg1, arg2);
    match event {
        HOST_PREPARE_ARGS_LOG_ALLOC_FAILED => {
            let _ = kprintf(
                b"ERROR: allocating pages for args/envs\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_PREPARE_ARGS_LOG_ADD_FAILED => {
            let _ = kprintf(
                b"ERROR: adding memory range for args/envs\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_PREPARE_ARGS_LOG_VDSO_FAILED => {
            let _ = kprintf(
                b"ERROR: mapping vdso pages. %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        HOST_PREPARE_ARGS_LOG_INIT_STACK_FAILED => {
            let _ = kprintf(
                b"%s: error: init_process_stack failed with %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_args_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        HOST_PREPARE_ARGS_LOG_CMDLINE => {
            let _ = kprintf(
                b"%s: saved_cmdline: %s\n\0".as_ptr().cast::<c_char>(),
                b"host_prepare_args_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0 as *mut i8,
            );
        }
        _ => {}
    }
}

unsafe extern "C" fn host_prepare_args_log_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    let _ = host_prepare_args_log_result(
        event,
        arg0,
        arg1,
        arg2,
        Some(host_prepare_args_log_raw_bridge),
    );
}

unsafe extern "C" fn host_map_memory_raw_bridge(
    os: *mut c_void,
    phys: CULong,
    size: CULong,
) -> CULong {
    ihk_mc_map_memory(os, phys, size)
}

unsafe extern "C" fn host_map_memory_bridge(os: *mut c_void, phys: CULong, size: CULong) -> CULong {
    host_map_memory_result(os, phys, size, Some(host_map_memory_raw_bridge))
}

unsafe extern "C" fn host_prepare_map_virtual_raw_bridge(
    phys: CULong,
    npages: CInt,
    attr: CULong,
) -> *mut c_void {
    ihk_mc_map_virtual(phys, npages, attr)
}

unsafe extern "C" fn host_prepare_map_virtual_bridge(
    phys: CULong,
    npages: CInt,
    attr: CULong,
) -> *mut c_void {
    host_prepare_map_virtual_result(
        phys,
        npages,
        attr,
        Some(host_prepare_map_virtual_raw_bridge),
    )
}

unsafe extern "C" fn host_map_virtual_raw_bridge(
    phys: CULong,
    npages: CInt,
    attr: CInt,
) -> *mut c_void {
    ihk_mc_map_virtual(phys, npages, attr as CULong)
}

unsafe extern "C" fn host_map_virtual_bridge(
    phys: CULong,
    npages: CInt,
    attr: CInt,
) -> *mut c_void {
    host_map_virtual_result(phys, npages, attr, Some(host_map_virtual_raw_bridge))
}

unsafe extern "C" fn host_unmap_virtual_raw_bridge(addr: *mut c_void, npages: CInt) {
    ihk_mc_unmap_virtual(addr, npages);
}

unsafe extern "C" fn host_unmap_virtual_bridge(addr: *mut c_void, npages: CInt) {
    let _ = host_unmap_virtual_result(addr, npages, Some(host_unmap_virtual_raw_bridge));
}

unsafe extern "C" fn host_unmap_memory_raw_bridge(os: *mut c_void, phys: CULong, size: CULong) {
    ihk_mc_unmap_memory(os, phys, size);
}

unsafe extern "C" fn host_unmap_memory_bridge(os: *mut c_void, phys: CULong, size: CULong) {
    let _ = host_unmap_memory_result(os, phys, size, Some(host_unmap_memory_raw_bridge));
}

unsafe extern "C" fn host_prepare_free_raw_bridge(ptr: *mut c_void) {
    _kfree(ptr, host_file_ptr(), line!() as CInt);
}

unsafe extern "C" fn host_prepare_free_bridge(ptr: *mut c_void) {
    let _ = host_prepare_free_result(ptr, Some(host_prepare_free_raw_bridge));
}

unsafe extern "C" fn host_prepare_alloc_raw_bridge(size: CULong, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        host_file_ptr(),
        line!() as CInt,
    )
}

unsafe extern "C" fn host_prepare_alloc_bridge(size: CULong, flags: CULong) -> *mut c_void {
    host_prepare_alloc_result(size, flags, Some(host_prepare_alloc_raw_bridge))
}

unsafe extern "C" fn host_prepare_copy_long_raw_bridge(
    dst: *mut c_void,
    src: *const c_void,
    size: CULong,
) {
    let _ = memcpy_long(dst, src, size as usize);
}

unsafe extern "C" fn host_prepare_copy_long_bridge(
    dst: *mut c_void,
    src: *const c_void,
    size: CULong,
) {
    let _ = host_prepare_copy_long_result(dst, src, size, Some(host_prepare_copy_long_raw_bridge));
}

unsafe extern "C" fn host_prepare_create_thread_raw_bridge(
    entry: CULong,
    cpu_set: *mut CULong,
    cpu_set_size: CULong,
) -> *mut Thread {
    create_thread(entry, cpu_set, cpu_set_size)
}

unsafe extern "C" fn host_prepare_create_thread_bridge(
    entry: CULong,
    cpu_set: *mut CULong,
    cpu_set_size: CULong,
) -> *mut Thread {
    host_create_thread_result(
        entry,
        cpu_set,
        cpu_set_size,
        Some(host_prepare_create_thread_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_destroy_thread_raw_bridge(thread: *mut Thread) {
    destroy_thread(thread);
}

unsafe extern "C" fn host_prepare_destroy_thread_bridge(thread: *mut Thread) {
    let _ = host_destroy_thread_result(thread, Some(host_prepare_destroy_thread_raw_bridge));
}

unsafe extern "C" fn host_prepare_ranges_raw_bridge(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    attr: CULong,
    args: *mut i8,
    args_len: CInt,
    envs: *mut i8,
    envs_len: CInt,
) -> CInt {
    prepare_process_ranges_args_envs(thread, pn, p, attr, args, args_len, envs, envs_len)
}

unsafe extern "C" fn host_prepare_ranges_bridge(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    attr: CULong,
    args: *mut i8,
    args_len: CInt,
    envs: *mut i8,
    envs_len: CInt,
) -> CInt {
    host_prepare_ranges_result(
        thread,
        pn,
        p,
        attr,
        args,
        args_len,
        envs,
        envs_len,
        Some(host_prepare_ranges_raw_bridge),
    )
}

unsafe extern "C" fn host_prepare_nr_numa_nodes_raw_bridge() -> CInt {
    ihk_mc_get_nr_numa_nodes()
}

unsafe extern "C" fn host_prepare_nr_numa_nodes_bridge() -> CInt {
    host_nr_numa_nodes_result(Some(host_prepare_nr_numa_nodes_raw_bridge))
}

unsafe extern "C" fn host_prepare_flush_tlb_raw_bridge() {
    flush_tlb();
}

unsafe extern "C" fn host_prepare_flush_tlb_bridge() {
    let _ = host_flush_tlb_result(Some(host_prepare_flush_tlb_raw_bridge));
}

#[cfg(enable_tofu)]
unsafe extern "C" fn host_prepare_tofu_finalize_raw_bridge() {
    tof_utofu_finalize();
}

#[cfg(enable_tofu)]
unsafe extern "C" fn host_prepare_tofu_finalize_bridge() {
    let _ = host_tofu_finalize_result(Some(host_prepare_tofu_finalize_raw_bridge));
}

unsafe extern "C" fn host_prepare_process_log_raw_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    match event {
        HOST_PREPARE_LOG_BROKEN_DESC => {
            let _ = kprintf(
                b"%s: broken mcexec program_load_desc\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_PREPARE_LOG_INVALID_SECTIONS => {
            let _ = kprintf(
                b"%s: ERROR: ELF sections other than 1 to 16 ??\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_PREPARE_LOG_NUM_SECTIONS => {
            let _ = kprintf(b"# of sections: %lu\n\0".as_ptr().cast::<c_char>(), arg0);
        }
        HOST_PREPARE_LOG_NUMA_BIND_ERROR | HOST_PREPARE_LOG_NUMA_NODEMASK_ERROR => {
            let _ = kprintf(
                b"%s: error: NUMA id %lu is larger than mask size!\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
            );
        }
        HOST_PREPARE_LOG_NUMA_POLICY => {
            let _ = kprintf(
                b"%s: numa_mem_policy: %lu, numa_mask: %lu\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
                arg1,
            );
        }
        HOST_PREPARE_LOG_PID_FLAGS => {
            let _ = kprintf(
                b"%s: PID: %lu, flags: 0x%lx\n\0".as_ptr().cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
                arg1,
            );
        }
        HOST_PREPARE_LOG_RLIMIT => {
            let _ = kprintf(
                b"%s: rlim_cur: %ld, rlim_max: %ld, stack_premap: %ld\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"host_prepare_process_log_raw_bridge\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0,
                arg1,
                arg2,
            );
        }
        HOST_PREPARE_LOG_PREPARE_ERROR => {
            let _ = kprintf(
                b"error: preparing process ranges, args, envs, stack\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_PREPARE_LOG_NEW_PROCESS => {
            let _ = kprintf(
                b"new process : %p [%lu] / table : %p\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                arg0 as *mut c_void,
                arg1,
                arg2 as *mut c_void,
            );
        }
        _ => {}
    }
}

unsafe extern "C" fn host_prepare_process_log_bridge(
    event: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
) {
    let _ = host_prepare_process_log_result(
        event,
        arg0,
        arg1,
        arg2,
        Some(host_prepare_process_log_raw_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn prepare_process_ranges_args_envs(
    thread: *mut Thread,
    pn: *mut ProgramLoadDesc,
    p: *mut ProgramLoadDesc,
    attr: CULong,
    args: *mut i8,
    args_len: CInt,
    envs: *mut i8,
    envs_len: CInt,
) -> CInt {
    if thread.is_null() || (*thread).proc.is_null() || p.is_null() {
        return -EINVAL;
    }

    let proc = (*thread).proc;
    let mut at_base = 0;
    let n = (*p).num_sections;
    let mut error = host_prepare_ranges_sections_result(
        thread,
        pn,
        p,
        &mut at_base,
        PAGE_SIZE,
        PAGE_MASK,
        LARGE_PAGE_SIZE,
        LARGE_PAGE_MASK,
        TASK_UNMAPPED_BASE,
        PAGE_SHIFT,
        LARGE_PAGE_SHIFT,
        IHK_MC_AP_NOWAIT,
        IHK_MC_AP_USER,
        MPOL_NO_BSS,
        PF_POPULATE,
        IHK_UCR_PROGRAM_COUNTER,
        Some(host_prepare_add_range_bridge),
        Some(host_prepare_alloc_pages_user_bridge),
        Some(host_prepare_free_pages_user_bridge),
        Some(host_prepare_virt_to_phys_bridge),
        Some(host_prepare_arch_vrflag_to_ptattr_bridge),
        Some(host_prepare_pt_set_range_bridge),
        Some(host_prepare_modify_user_context_bridge),
        Some(host_prepare_ranges_log_bridge),
    );
    if error != 0 {
        return error;
    }

    error = host_prepare_ranges_args_envs_result(
        thread,
        pn,
        p,
        attr,
        args,
        args_len,
        envs,
        envs_len,
        at_base,
        PAGE_SIZE,
        PAGE_MASK,
        PAGE_SHIFT,
        IHK_MC_AP_NOWAIT,
        Some(host_prepare_add_range_bridge),
        Some(host_prepare_alloc_pages_user_bridge),
        Some(host_prepare_free_pages_user_bridge),
        Some(host_prepare_virt_to_phys_bridge),
        Some(host_map_memory_bridge),
        Some(host_prepare_map_virtual_bridge),
        Some(host_unmap_virtual_bridge),
        Some(host_unmap_memory_bridge),
        Some(host_prepare_copy_long_bridge),
        Some(host_prepare_alloc_bridge),
        Some(host_prepare_free_bridge),
        Some(host_prepare_flush_tlb_bridge),
        Some(host_prepare_arch_map_vdso_bridge),
        Some(host_prepare_init_stack_bridge),
        Some(host_prepare_args_log_bridge),
    );
    if error != 0 {
        return error;
    }

    let sp = if (*thread).uctx.is_null() {
        0
    } else {
        ihk_mc_syscall_sp((*thread).uctx)
    };
    let _ = kprintf(
        b"mcexec_v10: prepared pid=%d thread=%p entry=0x%lx sp=0x%lx sections=%d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        (*proc).pid,
        thread,
        (*p).entry,
        sp,
        n,
    );
    0
}

unsafe extern "C" fn host_prepare_monitor_status_raw_bridge(cpu: CInt) -> CInt {
    let clv = get_cpu_local_var(cpu);
    if clv.is_null() || (*clv).monitor.is_null() {
        return -EINVAL;
    }
    (*(*clv).monitor).status
}

unsafe extern "C" fn host_prepare_monitor_status_bridge(cpu: CInt) -> CInt {
    host_monitor_status_result(cpu, Some(host_prepare_monitor_status_raw_bridge))
}

unsafe fn host_process_msg_prepare_process(rphys: CULong) -> CInt {
    host_prepare_process_body_result(
        rphys,
        HOST_NUM_PROCESSORS,
        PTATTR_NO_EXECUTE | (PTATTR_WRITABLE as CULong) | PTATTR_FOR_USER,
        PAGE_SIZE,
        IHK_MC_AP_NOWAIT,
        USER_END,
        LD_TASK_UNMAPPED_BASE,
        SIGCHLD,
        MPOL_MAX,
        MPOL_BIND,
        Some(host_prepare_monitor_status_bridge),
        Some(host_map_memory_bridge),
        Some(host_prepare_map_virtual_bridge),
        Some(host_unmap_virtual_bridge),
        Some(host_unmap_memory_bridge),
        Some(host_prepare_alloc_bridge),
        Some(host_prepare_free_bridge),
        Some(host_prepare_copy_long_bridge),
        Some(host_prepare_create_thread_bridge),
        Some(host_prepare_destroy_thread_bridge),
        Some(host_prepare_ranges_bridge),
        Some(host_prepare_nr_numa_nodes_bridge),
        Some(host_prepare_flush_tlb_bridge),
        #[cfg(enable_tofu)]
        Some(host_prepare_tofu_finalize_bridge),
        #[cfg(not(enable_tofu))]
        None,
        Some(host_prepare_process_log_bridge),
    )
}

unsafe extern "C" fn syscall_channel_send(channel: *mut c_void, packet: *mut IkcScdPacket) {
    let _ = ihk_ikc_send(channel, packet.cast::<c_void>(), 0);
}

unsafe extern "C" fn host_ikc_packet_send_raw_bridge(
    channel: *mut c_void,
    packet: *mut IkcScdPacket,
) {
    syscall_channel_send(channel, packet);
}

unsafe extern "C" fn host_cpu_read_write_register_raw_bridge(desc: *mut c_void, op: CInt) -> CInt {
    arch_cpu_read_write_register(desc.cast::<IhkOsCpuRegister>(), op)
}

unsafe extern "C" fn host_cpu_read_write_register_bridge(desc: *mut c_void, op: CInt) -> CInt {
    host_cpu_rw_register_result(desc, op, Some(host_cpu_read_write_register_raw_bridge))
}

unsafe extern "C" fn host_cleanup_process_log_raw_bridge(pid: CInt, thread_arg: CULong) {
    let _ = kprintf(
        b"SCD_MSG_CLEANUP_PROCESS pid=%d, thread=0x%llx\n\0"
            .as_ptr()
            .cast::<c_char>(),
        pid,
        thread_arg,
    );
}

unsafe extern "C" fn host_cleanup_process_log_bridge(pid: CInt, thread_arg: CULong) {
    let _ =
        host_cleanup_process_log_result(pid, thread_arg, Some(host_cleanup_process_log_raw_bridge));
}

unsafe extern "C" fn host_terminate_host_raw_bridge(pid: CInt, thread: *mut c_void) {
    terminate_host(pid, thread.cast::<Thread>());
}

unsafe extern "C" fn host_terminate_host_bridge(pid: CInt, thread: *mut c_void) {
    let _ = host_terminate_host_result(pid, thread, Some(host_terminate_host_raw_bridge));
}

unsafe extern "C" fn host_cleanup_fd_log_raw_bridge(pid: CInt, fd: CULong, err: CInt) {
    let _ = kprintf(
        b"SCD_MSG_CLEANUP_FD pid=%d, fd=%d -> err: %d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        pid,
        fd as CInt,
        err,
    );
}

unsafe extern "C" fn host_cleanup_fd_log_bridge(pid: CInt, fd: CULong, err: CInt) {
    let _ = host_cleanup_fd_log_result(pid, fd, err, Some(host_cleanup_fd_log_raw_bridge));
}

unsafe extern "C" fn host_do_kill_raw_bridge(
    pid: CInt,
    tid: CInt,
    sig: CInt,
    info: *mut c_void,
) -> CULong {
    do_kill(
        core::ptr::null_mut(),
        pid,
        tid,
        sig,
        info.cast::<SigInfo>(),
        0,
    )
}

unsafe extern "C" fn host_do_kill_bridge(
    pid: CInt,
    tid: CInt,
    sig: CInt,
    info: *mut c_void,
) -> CULong {
    host_do_kill_result(pid, tid, sig, info, Some(host_do_kill_raw_bridge))
}

unsafe extern "C" fn host_send_signal_log_raw_bridge(pid: CInt, tid: CInt, sig: CInt, rc: CInt) {
    let _ = kprintf(
        b"SCD_MSG_SEND_SIGNAL: do_kill(pid=%d, tid=%d, sig=%d)=%d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        pid,
        tid,
        sig,
        rc,
    );
}

unsafe extern "C" fn host_send_signal_log_bridge(pid: CInt, tid: CInt, sig: CInt, rc: CInt) {
    let _ = host_send_signal_log_result(pid, tid, sig, rc, Some(host_send_signal_log_raw_bridge));
}

unsafe extern "C" fn host_find_thread_raw_bridge(pid: CInt, tid: CInt) -> *mut c_void {
    find_thread(pid, tid).cast::<c_void>()
}

unsafe extern "C" fn host_find_thread_bridge(pid: CInt, tid: CInt) -> *mut c_void {
    host_find_thread_result(pid, tid, Some(host_find_thread_raw_bridge))
}

unsafe extern "C" fn host_wakeup_scd_waitq_raw_bridge(thread: *mut c_void) {
    waitq_wakeup(&raw mut (*thread.cast::<Thread>()).scd_wq);
}

unsafe extern "C" fn host_wakeup_scd_waitq_bridge(thread: *mut c_void) {
    let _ = host_wakeup_thread_result(thread, Some(host_wakeup_scd_waitq_raw_bridge));
}

unsafe extern "C" fn host_thread_unlock_raw_bridge(thread: *mut c_void) {
    thread_unlock(thread.cast::<Thread>());
}

unsafe extern "C" fn host_thread_unlock_bridge(thread: *mut c_void) {
    let _ = host_thread_unlock_result(thread, Some(host_thread_unlock_raw_bridge));
}

unsafe extern "C" fn host_wake_syscall_log_raw_bridge(tid: CInt, found: CInt) {
    if found == 0 {
        let _ = kprintf(
            b"%s: WARNING: no thread for SCD reply? TID: %d\n\0"
                .as_ptr()
                .cast::<c_char>(),
            b"syscall_packet_handler\0".as_ptr().cast::<c_char>(),
            tid,
        );
    } else {
        let _ = kprintf(
            b"%s: SCD_MSG_WAKE_UP_SYSCALL_THREAD: waking up tid %d\n\0"
                .as_ptr()
                .cast::<c_char>(),
            b"syscall_packet_handler\0".as_ptr().cast::<c_char>(),
            tid,
        );
    }
}

unsafe extern "C" fn host_wake_syscall_log_bridge(tid: CInt, found: CInt) {
    let _ = host_wake_syscall_log_result(tid, found, Some(host_wake_syscall_log_raw_bridge));
}

unsafe extern "C" fn host_debug_log_raw_bridge(code: CULong) {
    debug_log(code as CLong);
}

unsafe extern "C" fn host_debug_log_bridge(code: CULong) {
    let _ = host_debug_log_result(code, Some(host_debug_log_raw_bridge));
}

unsafe extern "C" fn host_debug_log_print_raw_bridge(code: CULong) {
    let _ = kprintf(
        b"SCD_MSG_DEBUG_LOG code=%lx\n\0".as_ptr().cast::<c_char>(),
        code,
    );
}

unsafe extern "C" fn host_debug_log_print_bridge(code: CULong) {
    let _ = host_debug_log_print_result(code, Some(host_debug_log_print_raw_bridge));
}

unsafe extern "C" fn host_thread_profile_enabled_raw_bridge(thread: *mut c_void) -> CInt {
    #[cfg(enable_profile)]
    {
        (*thread.cast::<Thread>()).profile
    }
    #[cfg(not(enable_profile))]
    {
        let _ = thread;
        0
    }
}

unsafe extern "C" fn host_thread_profile_enabled_bridge(thread: *mut c_void) -> CInt {
    host_thread_profile_enabled_result(thread, Some(host_thread_profile_enabled_raw_bridge))
}

unsafe extern "C" fn host_timestamp_raw_bridge() -> CULong {
    #[cfg(enable_profile)]
    {
        rdtsc()
    }
    #[cfg(not(enable_profile))]
    {
        0
    }
}

unsafe extern "C" fn host_timestamp_bridge() -> CULong {
    host_timestamp_result(Some(host_timestamp_raw_bridge))
}

unsafe extern "C" fn host_preempt_disable_raw_bridge() {
    preempt_disable();
}

unsafe extern "C" fn host_preempt_disable_bridge() {
    let _ = host_preempt_result(Some(host_preempt_disable_raw_bridge));
}

unsafe extern "C" fn host_preempt_enable_raw_bridge() {
    preempt_enable();
}

unsafe extern "C" fn host_preempt_enable_bridge() {
    let _ = host_preempt_result(Some(host_preempt_enable_raw_bridge));
}

unsafe extern "C" fn host_remote_page_fault_process_raw_bridge(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
) {
    page_fault_process_vm(
        (*thread.cast::<Thread>()).vm,
        fault_address as *mut c_void,
        fault_reason,
    );
}

unsafe extern "C" fn host_remote_page_fault_process_bridge(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
) {
    let _ = host_remote_page_fault_process_result(
        thread,
        fault_address,
        fault_reason,
        Some(host_remote_page_fault_process_raw_bridge),
    );
}

unsafe extern "C" fn host_remote_page_fault_profile_event_raw_bridge(event: CInt, delta: CULong) {
    #[cfg(enable_profile)]
    {
        profile_event_add(event, delta);
    }
    #[cfg(not(enable_profile))]
    {
        let _ = (event, delta);
    }
}

unsafe extern "C" fn host_remote_page_fault_profile_event_bridge(event: CInt, delta: CULong) {
    let _ = host_profile_event_result(
        event,
        delta,
        Some(host_remote_page_fault_profile_event_raw_bridge),
    );
}

unsafe extern "C" fn host_remote_page_fault_log_raw_bridge(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
) {
    let t = thread.cast::<Thread>();
    let pid = if t.is_null() || (*t).proc.is_null() {
        0
    } else {
        (*(*t).proc).pid
    };
    let _ = kprintf(
        b"remote page fault,pid=%d,va=%lx,reason=%lx\n\0"
            .as_ptr()
            .cast::<c_char>(),
        pid,
        fault_address,
        fault_reason,
    );
}

unsafe extern "C" fn host_remote_page_fault_log_bridge(
    thread: *mut c_void,
    fault_address: CULong,
    fault_reason: CULong,
) {
    let _ = host_remote_page_fault_log_result(
        thread,
        fault_address,
        fault_reason,
        Some(host_remote_page_fault_log_raw_bridge),
    );
}

unsafe extern "C" fn host_alloc_raw_bridge(size: CULong, flags: CULong) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags as CInt,
        host_file_ptr(),
        line!() as CInt,
    )
}

unsafe extern "C" fn host_alloc_bridge(size: CULong, flags: CULong) -> *mut c_void {
    host_alloc_result(size, flags, Some(host_alloc_raw_bridge))
}

unsafe extern "C" fn host_ikc_connect_raw_bridge(param: *mut IhkIkcConnectParam) -> CInt {
    ihk_ikc_connect(core::ptr::null_mut(), param)
}

unsafe extern "C" fn host_delay_raw_bridge(usec: CULong) {
    ihk_mc_delay_us(usec as CInt);
}

unsafe extern "C" fn host_set_current_ikc2linux_raw_bridge(channel: *mut c_void) {
    let clv = get_this_cpu_local_var();
    if !clv.is_null() {
        (*clv).ikc2linux = channel;
    }
}

unsafe extern "C" fn host_set_regular_channel_raw_bridge(channel: *mut c_void, cpu: CInt) {
    ihk_ikc_set_regular_channel(core::ptr::null_mut(), channel, cpu);
}

unsafe extern "C" fn host_panic_raw_bridge() {
    panic(b"\0".as_ptr().cast::<c_char>());
}

unsafe extern "C" fn host_init_ikc2linux_log_raw_bridge(event: CInt) {
    match event {
        HOST_INIT_IKC_LOG_ALLOC_ERROR => {
            let _ = kprintf(
                b"%s: error: allocating Linux channels\n\0"
                    .as_ptr()
                    .cast::<c_char>(),
                b"init_host_ikc2linux\0".as_ptr().cast::<c_char>(),
            );
        }
        HOST_INIT_IKC_LOG_TRY_CONNECT => {
            let _ = kprintf(
                b"(ikc2linux) Trying to connect host ...\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_INIT_IKC_LOG_RETRY_DOT => {
            let _ = kprintf(b".\0".as_ptr().cast::<c_char>());
        }
        HOST_INIT_IKC_LOG_CONNECTED => {
            let _ = kprintf(b"connected.\n\0".as_ptr().cast::<c_char>());
        }
        _ => {}
    }
}

unsafe extern "C" fn host_init_ikc2mckernel_log_raw_bridge(event: CInt) {
    match event {
        HOST_INIT_IKC_LOG_TRY_CONNECT => {
            let _ = kprintf(
                b"(ikc2mckernel) Trying to connect host ...\0"
                    .as_ptr()
                    .cast::<c_char>(),
            );
        }
        HOST_INIT_IKC_LOG_RETRY_DOT => {
            let _ = kprintf(b".\0".as_ptr().cast::<c_char>());
        }
        HOST_INIT_IKC_LOG_CONNECTED => {
            let _ = kprintf(b"connected.\n\0".as_ptr().cast::<c_char>());
        }
        _ => {}
    }
}

unsafe extern "C" fn host_packet_copy_raw_bridge(
    dst: *mut c_void,
    src: *mut IkcScdPacket,
    size: CULong,
) {
    let _ = memcpy(dst, src.cast::<c_void>(), size as usize);
}

unsafe extern "C" fn host_packet_copy_bridge(
    dst: *mut c_void,
    src: *mut IkcScdPacket,
    size: CULong,
) {
    let _ = host_packet_copy_result(dst, src, size, Some(host_packet_copy_raw_bridge));
}

unsafe extern "C" fn host_remote_page_fault_defer_raw_bridge(
    thread: *mut c_void,
    arg: *mut c_void,
    backlog_fn: HostBacklogFn,
) {
    let thread = thread.cast::<Thread>();
    (*thread).rpf_arg = arg;
    (*thread).rpf_backlog = match backlog_fn {
        Some(func) => func as *mut c_void,
        None => core::ptr::null_mut(),
    };
}

unsafe extern "C" fn host_remote_page_fault_defer_bridge(
    thread: *mut c_void,
    arg: *mut c_void,
    backlog_fn: HostBacklogFn,
) {
    let _ = host_remote_page_fault_defer_result(
        thread,
        arg,
        backlog_fn,
        Some(host_remote_page_fault_defer_raw_bridge),
    );
}

unsafe extern "C" fn host_sched_wakeup_thread_raw_bridge(
    thread: *mut c_void,
    valid_states: CInt,
) -> CInt {
    sched_wakeup_thread(thread.cast::<Thread>(), valid_states)
}

unsafe extern "C" fn host_sched_wakeup_thread_bridge(
    thread: *mut c_void,
    valid_states: CInt,
) -> CInt {
    host_sched_wakeup_result(
        thread,
        valid_states,
        Some(host_sched_wakeup_thread_raw_bridge),
    )
}

unsafe extern "C" fn host_remote_page_fault_missing_log_raw_bridge(tid: CInt) {
    let _ = kprintf(
        b"%s: WARNING: no thread for remote pf %d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        b"host_remote_page_fault_missing_log_raw_bridge\0"
            .as_ptr()
            .cast::<c_char>(),
        tid,
    );
}

unsafe extern "C" fn host_remote_page_fault_missing_log_bridge(tid: CInt) {
    let _ = host_remote_page_fault_missing_log_result(
        tid,
        Some(host_remote_page_fault_missing_log_raw_bridge),
    );
}

unsafe extern "C" fn host_schedule_thread_proc_raw_bridge(thread: *mut c_void) -> *mut c_void {
    (*thread.cast::<Thread>()).proc.cast::<c_void>()
}

unsafe extern "C" fn host_schedule_thread_proc_bridge(thread: *mut c_void) -> *mut c_void {
    host_thread_proc_result(thread, Some(host_schedule_thread_proc_raw_bridge))
}

unsafe extern "C" fn host_schedule_current_cpu_raw_bridge() -> CInt {
    ihk_mc_get_processor_id()
}

unsafe extern "C" fn host_schedule_current_cpu_bridge() -> CInt {
    host_current_cpu_result(Some(host_schedule_current_cpu_raw_bridge))
}

unsafe extern "C" fn host_schedule_cpu_allowed_raw_bridge(
    thread: *mut c_void,
    cpuid: CInt,
) -> CInt {
    if cpuid < 0 {
        return 0;
    }
    let bits = &(*thread.cast::<Thread>()).cpu_set.bits;
    let word = (cpuid as usize) / (CULong::BITS as usize);
    if word >= bits.len() {
        return 0;
    }
    let bit = (cpuid as u32) % CULong::BITS;
    ((bits[word] & (1u64 << bit)) != 0) as CInt
}

unsafe extern "C" fn host_schedule_cpu_allowed_bridge(thread: *mut c_void, cpuid: CInt) -> CInt {
    host_thread_cpu_allowed_result(thread, cpuid, Some(host_schedule_cpu_allowed_raw_bridge))
}

unsafe extern "C" fn host_schedule_obtain_cpuid_raw_bridge(thread: *mut c_void) -> CInt {
    obtain_clone_cpuid(&raw mut (*thread.cast::<Thread>()).cpu_set, 0)
}

unsafe extern "C" fn host_schedule_obtain_cpuid_bridge(thread: *mut c_void) -> CInt {
    host_thread_obtain_cpuid_result(thread, Some(host_schedule_obtain_cpuid_raw_bridge))
}

unsafe extern "C" fn host_schedule_proc_pid_raw_bridge(proc: *mut c_void) -> CInt {
    (*proc.cast::<Process>()).pid
}

unsafe extern "C" fn host_schedule_proc_pid_bridge(proc: *mut c_void) -> CInt {
    host_proc_pid_result(proc, Some(host_schedule_proc_pid_raw_bridge))
}

unsafe extern "C" fn host_schedule_thread_pc_raw_bridge(thread: *mut c_void) -> CULong {
    let thread = thread.cast::<Thread>();
    if (*thread).uctx.is_null() {
        0
    } else {
        ihk_mc_syscall_pc((*thread).uctx)
    }
}

unsafe extern "C" fn host_schedule_thread_pc_bridge(thread: *mut c_void) -> CULong {
    host_thread_reg_result(thread, Some(host_schedule_thread_pc_raw_bridge))
}

unsafe extern "C" fn host_schedule_thread_sp_raw_bridge(thread: *mut c_void) -> CULong {
    let thread = thread.cast::<Thread>();
    if (*thread).uctx.is_null() {
        0
    } else {
        ihk_mc_syscall_sp((*thread).uctx)
    }
}

unsafe extern "C" fn host_schedule_thread_sp_bridge(thread: *mut c_void) -> CULong {
    host_thread_reg_result(thread, Some(host_schedule_thread_sp_raw_bridge))
}

unsafe extern "C" fn host_schedule_invalid_log_raw_bridge(thread: *mut c_void) {
    let _ = kprintf(
        b"mcexec_v10: schedule_process invalid thread=%p\n\0"
            .as_ptr()
            .cast::<c_char>(),
        thread,
    );
}

unsafe extern "C" fn host_schedule_invalid_log_bridge(thread: *mut c_void) {
    let _ = host_schedule_invalid_log_result(thread, Some(host_schedule_invalid_log_raw_bridge));
}

unsafe extern "C" fn host_schedule_received_log_raw_bridge(
    thread: *mut c_void,
    pid: CInt,
    pc: CULong,
    sp: CULong,
    cpuid: CInt,
) {
    let _ = kprintf(
        b"mcexec_v10: schedule_process received thread=%p pid=%d entry=0x%lx sp=0x%lx current_cpu=%d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        thread,
        pid,
        pc,
        sp,
        cpuid,
    );
}

unsafe extern "C" fn host_schedule_received_log_bridge(
    thread: *mut c_void,
    pid: CInt,
    pc: CULong,
    sp: CULong,
    cpuid: CInt,
) {
    let _ = host_schedule_received_log_result(
        thread,
        pid,
        pc,
        sp,
        cpuid,
        Some(host_schedule_received_log_raw_bridge),
    );
}

unsafe extern "C" fn host_schedule_no_cpu_log_raw_bridge() {
    let _ = kprintf(b"No CPU available\n\0".as_ptr().cast::<c_char>());
}

unsafe extern "C" fn host_schedule_no_cpu_log_bridge() {
    let _ = host_schedule_no_cpu_log_result(Some(host_schedule_no_cpu_log_raw_bridge));
}

unsafe extern "C" fn host_schedule_set_tid_raw_bridge(thread: *mut c_void, tid: CInt) {
    (*thread.cast::<Thread>()).tid = tid;
}

unsafe extern "C" fn host_schedule_set_tid_bridge(thread: *mut c_void, tid: CInt) {
    let _ = host_thread_set_tid_result(thread, tid, Some(host_schedule_set_tid_raw_bridge));
}

unsafe extern "C" fn host_schedule_set_proc_status_raw_bridge(proc: *mut c_void, status: CInt) {
    (*proc.cast::<Process>()).status = status;
}

unsafe extern "C" fn host_schedule_set_proc_status_bridge(proc: *mut c_void, status: CInt) {
    let _ = host_status_set_result(proc, status, Some(host_schedule_set_proc_status_raw_bridge));
}

unsafe extern "C" fn host_schedule_set_thread_status_raw_bridge(thread: *mut c_void, status: CInt) {
    (*thread.cast::<Thread>()).status = status;
}

unsafe extern "C" fn host_schedule_set_thread_status_bridge(thread: *mut c_void, status: CInt) {
    let _ = host_status_set_result(
        thread,
        status,
        Some(host_schedule_set_thread_status_raw_bridge),
    );
}

unsafe extern "C" fn host_schedule_chain_thread_raw_bridge(thread: *mut c_void) {
    chain_thread(thread.cast::<Thread>());
}

unsafe extern "C" fn host_schedule_chain_thread_bridge(thread: *mut c_void) {
    let _ = host_chain_thread_result(thread, Some(host_schedule_chain_thread_raw_bridge));
}

unsafe extern "C" fn host_schedule_chain_process_raw_bridge(proc: *mut c_void) {
    chain_process(proc.cast::<Process>());
}

unsafe extern "C" fn host_schedule_chain_process_bridge(proc: *mut c_void) {
    let _ = host_chain_process_result(proc, Some(host_schedule_chain_process_raw_bridge));
}

unsafe extern "C" fn host_schedule_runq_add_raw_bridge(thread: *mut c_void, cpuid: CInt) {
    runq_add_thread(thread.cast::<Thread>(), cpuid);
}

unsafe extern "C" fn host_schedule_runq_add_bridge(thread: *mut c_void, cpuid: CInt) {
    let _ = host_runq_add_thread_result(thread, cpuid, Some(host_schedule_runq_add_raw_bridge));
}

unsafe extern "C" fn host_schedule_queued_log_raw_bridge(
    pid: CInt,
    tid: CInt,
    cpuid: CInt,
    status: CInt,
) {
    let _ = kprintf(
        b"mcexec_v10: schedule_process queued pid=%d tid=%d cpu=%d status=%d\n\0"
            .as_ptr()
            .cast::<c_char>(),
        pid,
        tid,
        cpuid,
        status,
    );
}

unsafe extern "C" fn host_schedule_queued_log_bridge(
    pid: CInt,
    tid: CInt,
    cpuid: CInt,
    status: CInt,
) {
    let _ = host_schedule_queued_log_result(
        pid,
        tid,
        cpuid,
        status,
        Some(host_schedule_queued_log_raw_bridge),
    );
}

unsafe extern "C" fn host_perf_init_raw_bridge(counter: CInt, config: u32, mode: CInt) -> CInt {
    host_perf_init_raw_result(counter, config, mode, Some(ihk_mc_perfctr_init_raw))
}

unsafe extern "C" fn host_perf_stop_bridge(counter_mask: CULong, flags: CInt) -> CInt {
    host_perf_stop_result(counter_mask, flags, Some(ihk_mc_perfctr_stop))
}

unsafe extern "C" fn host_perf_reset_bridge(counter: CInt) -> CInt {
    host_perf_reset_result(counter, Some(ihk_mc_perfctr_reset))
}

unsafe extern "C" fn host_perf_start_bridge(counter_mask: CULong) -> CInt {
    host_perf_start_result(counter_mask, Some(ihk_mc_perfctr_start))
}

unsafe extern "C" fn host_perf_read_bridge(counter: CInt) -> CULong {
    host_perf_read_result(counter, Some(ihk_mc_perfctr_read))
}

unsafe extern "C" fn host_perf_unexpected_ctrl_type_raw_bridge() {
    let _ = kprintf(
        b"%s: SCD_MSG_PERF_CTRL unexpected ctrl_type\n\0"
            .as_ptr()
            .cast::<c_char>(),
        b"host_perf_unexpected_ctrl_type_raw_bridge\0"
            .as_ptr()
            .cast::<c_char>(),
    );
}

unsafe extern "C" fn host_perf_unexpected_ctrl_type_bridge() {
    let _ = host_perf_unexpected_result(Some(host_perf_unexpected_ctrl_type_raw_bridge));
}

unsafe extern "C" fn host_cleanup_process_raw_bridge(pid: CInt) -> CInt {
    process_cleanup_before_terminate(pid)
}

unsafe extern "C" fn host_cleanup_process_bridge(pid: CInt) -> CInt {
    host_cleanup_process_result(pid, Some(host_cleanup_process_raw_bridge))
}

unsafe extern "C" fn host_cleanup_fd_raw_bridge(pid: CInt, fd: CInt) -> CInt {
    process_cleanup_fd(pid, fd)
}

unsafe extern "C" fn host_cleanup_fd_bridge(pid: CInt, fd: CInt) -> CInt {
    host_cleanup_fd_result(pid, fd, Some(host_cleanup_fd_raw_bridge))
}

unsafe extern "C" fn host_init_channel_acked_log_print_bridge() {
    let _ = kprintf(b"SCD_MSG_INIT_CHANNEL_ACKED\n\0".as_ptr().cast::<c_char>());
}

unsafe extern "C" fn host_init_channel_acked_log_bridge() {
    let _ = host_init_ack_log_result(Some(host_init_channel_acked_log_print_bridge));
}

unsafe extern "C" fn host_schedule_process_log_print_bridge(arg: CULong) {
    let _ = kprintf(
        b"SCD_MSG_SCHEDULE_PROCESS: %lx\n\0"
            .as_ptr()
            .cast::<c_char>(),
        arg,
    );
}

unsafe extern "C" fn host_schedule_process_log_bridge(packet: *mut IkcScdPacket) {
    let _ = host_schedule_process_log_result(packet, Some(host_schedule_process_log_print_bridge));
}

unsafe extern "C" fn host_procfs_request_bridge(packet: *mut IkcScdPacket) -> CInt {
    host_procfs_request_result(packet, Some(process_procfs_request))
}

unsafe extern "C" fn host_sysfs_packet_handler_bridge(
    channel: *mut c_void,
    msg: CInt,
    err: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
) {
    sysfss_packet_handler(channel, msg, err, arg1, arg2, arg3);
}

unsafe extern "C" fn host_sysfs_packet_bridge(
    channel: *mut c_void,
    msg: CInt,
    err: CInt,
    arg1: CLong,
    arg2: CLong,
    arg3: CLong,
) {
    let _ = host_sysfs_packet_result(
        channel,
        msg,
        err,
        arg1,
        arg2,
        arg3,
        Some(host_sysfs_packet_handler_bridge),
    );
}

unsafe extern "C" fn host_unknown_packet_log_print_bridge(packet: *mut IkcScdPacket) {
    let traditional = (&raw mut (*packet).body).cast::<IkcScdPacketTraditional>();
    let _ = kprintf(
        b"syscall_pakcet_handler:unknown message (%d.%d.%d.%d.%d.%#lx)\n\0"
            .as_ptr()
            .cast::<c_char>(),
        (*packet).msg,
        (*traditional).ref_,
        (*traditional).osnum,
        (*traditional).pid,
        (*packet).err,
        (*traditional).arg,
    );
}

unsafe extern "C" fn host_unknown_packet_log_bridge(packet: *mut IkcScdPacket) {
    let _ = host_unknown_packet_log_result(packet, Some(host_unknown_packet_log_print_bridge));
}

unsafe extern "C" fn host_release_packet_raw_bridge(packet: *mut IkcScdPacket) {
    ihk_ikc_release_packet(packet.cast::<c_void>());
}

unsafe extern "C" fn host_release_packet_bridge(packet: *mut IkcScdPacket) {
    let _ = host_release_packet_result(packet, Some(host_release_packet_raw_bridge));
}

unsafe extern "C" fn host_current_ikc2linux_raw_bridge() -> *mut c_void {
    let clv = get_this_cpu_local_var();
    if clv.is_null() {
        core::ptr::null_mut()
    } else {
        (*clv).ikc2linux
    }
}

unsafe extern "C" fn host_current_thread_raw_bridge() -> *mut c_void {
    let clv = get_this_cpu_local_var();
    if clv.is_null() {
        core::ptr::null_mut()
    } else {
        (*clv).current.cast::<c_void>()
    }
}

#[no_mangle]
pub unsafe extern "C" fn send_procfs_answer(packet: *mut IkcScdPacket, err: CInt) {
    let _ = host_procfs_answer_current_result(
        packet,
        err,
        Some(host_current_ikc2linux_raw_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
}

unsafe fn do_remote_page_fault(packet: *mut IkcScdPacket, err: CInt) {
    let profile_event = 0;
    let _ = host_remote_page_fault_current_result(
        packet,
        err,
        PF_POPULATE,
        profile_event,
        Some(host_current_ikc2linux_raw_bridge),
        Some(host_current_thread_raw_bridge),
        Some(host_thread_profile_enabled_bridge),
        Some(host_timestamp_bridge),
        Some(host_preempt_disable_bridge),
        Some(host_remote_page_fault_process_bridge),
        Some(host_preempt_enable_bridge),
        Some(host_remote_page_fault_profile_event_bridge),
        Some(host_remote_page_fault_log_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
}

unsafe extern "C" fn do_remote_page_fault_bridge(request: *mut IkcScdPacket, err: CInt) {
    do_remote_page_fault(request, err);
}

unsafe extern "C" fn remote_page_fault(arg: *mut c_void) {
    do_remote_page_fault(arg.cast::<IkcScdPacket>(), 0);
}

unsafe extern "C" fn host_prepare_process_raw_bridge(rphys: CULong) -> CInt {
    host_process_msg_prepare_process(rphys)
}

unsafe extern "C" fn host_prepare_process_bridge(rphys: CULong) -> CInt {
    host_prepare_process_result(rphys, Some(host_prepare_process_raw_bridge))
}

unsafe extern "C" fn host_prepare_process_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    host_prepare_process_request_result(
        response_channel,
        packet,
        Some(host_prepare_process_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    )
}

unsafe extern "C" fn host_schedule_process_request_bridge(packet: *mut IkcScdPacket) -> CInt {
    host_schedule_process_log_bridge(packet);
    host_schedule_process_request_result(
        packet,
        Some(host_schedule_thread_proc_bridge),
        Some(host_schedule_current_cpu_bridge),
        Some(host_schedule_cpu_allowed_bridge),
        Some(host_schedule_obtain_cpuid_bridge),
        Some(host_schedule_proc_pid_bridge),
        Some(host_schedule_thread_pc_bridge),
        Some(host_schedule_thread_sp_bridge),
        Some(host_schedule_invalid_log_bridge),
        Some(host_schedule_received_log_bridge),
        Some(host_schedule_no_cpu_log_bridge),
        Some(host_schedule_set_tid_bridge),
        Some(host_schedule_set_proc_status_bridge),
        Some(host_schedule_set_thread_status_bridge),
        Some(host_schedule_chain_thread_bridge),
        Some(host_schedule_chain_process_bridge),
        Some(host_schedule_runq_add_bridge),
        Some(host_schedule_queued_log_bridge),
        PS_RUNNING,
    )
}

unsafe extern "C" fn host_wake_syscall_thread_request_bridge(packet: *mut IkcScdPacket) -> CInt {
    host_wake_syscall_thread_request_result(
        packet,
        Some(host_find_thread_bridge),
        Some(host_wakeup_scd_waitq_bridge),
        Some(host_thread_unlock_bridge),
        Some(host_wake_syscall_log_bridge),
    )
}

unsafe extern "C" fn host_remote_page_fault_request_bridge(
    packet: *mut IkcScdPacket,
    current_thread: *mut c_void,
) -> CInt {
    host_remote_page_fault_request_result(
        packet,
        Some(host_find_thread_bridge),
        current_thread,
        Some(do_remote_page_fault_bridge),
        Some(host_alloc_bridge),
        Some(host_packet_copy_bridge),
        Some(host_remote_page_fault_defer_bridge),
        Some(host_sched_wakeup_thread_bridge),
        Some(host_thread_unlock_bridge),
        Some(host_remote_page_fault_missing_log_bridge),
        Some(remote_page_fault),
        size_of::<IkcScdPacket>() as CULong,
        IHK_MC_AP_NOWAIT,
        PS_INTERRUPTIBLE,
    )
}

unsafe extern "C" fn host_send_signal_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    let _ = host_send_signal_request_result(
        response_channel,
        packet,
        Some(host_map_memory_bridge),
        Some(host_map_virtual_bridge),
        Some(host_unmap_virtual_bridge),
        Some(host_unmap_memory_bridge),
        Some(host_do_kill_bridge),
        Some(host_send_signal_log_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
    0
}

unsafe extern "C" fn host_cleanup_process_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    let _ = host_cleanup_process_request_result(
        response_channel,
        packet,
        Some(host_cleanup_process_bridge),
        Some(host_terminate_host_bridge),
        Some(host_cleanup_process_log_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
    0
}

unsafe extern "C" fn host_cleanup_fd_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    let _ = host_cleanup_fd_request_result(
        response_channel,
        packet,
        Some(host_cleanup_fd_bridge),
        Some(host_cleanup_fd_log_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
    0
}

unsafe extern "C" fn host_debug_log_request_bridge(packet: *mut IkcScdPacket) -> CInt {
    host_debug_log_request_result(
        packet,
        Some(host_debug_log_bridge),
        Some(host_debug_log_print_bridge),
    )
}

unsafe extern "C" fn host_perf_ctrl_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    host_perf_ctrl_request_result(
        response_channel,
        packet,
        Some(host_map_memory_bridge),
        Some(host_map_virtual_bridge),
        Some(host_unmap_virtual_bridge),
        Some(host_unmap_memory_bridge),
        Some(host_perf_init_raw_bridge),
        Some(host_perf_stop_bridge),
        Some(host_perf_reset_bridge),
        Some(host_perf_start_bridge),
        Some(host_perf_read_bridge),
        Some(host_perf_unexpected_ctrl_type_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    )
}

unsafe extern "C" fn host_cpu_rw_reg_request_bridge(
    response_channel: *mut c_void,
    packet: *mut IkcScdPacket,
) -> CInt {
    let _ = host_cpu_rw_reg_request_result(
        response_channel,
        packet,
        Some(host_map_memory_bridge),
        Some(host_map_virtual_bridge),
        Some(host_unmap_virtual_bridge),
        Some(host_unmap_memory_bridge),
        Some(host_cpu_read_write_register_bridge),
        Some(host_ikc_packet_send_raw_bridge),
    );
    0
}

static HOST_SCD_DISPATCH_OPS: HostScdDispatchOps = HostScdDispatchOps {
    init_ack_log_fn: Some(host_init_channel_acked_log_bridge),
    prepare_process_fn: Some(host_prepare_process_request_bridge),
    schedule_process_fn: Some(host_schedule_process_request_bridge),
    wake_syscall_thread_fn: Some(host_wake_syscall_thread_request_bridge),
    remote_page_fault_fn: Some(host_remote_page_fault_request_bridge),
    send_signal_fn: Some(host_send_signal_request_bridge),
    procfs_request_fn: Some(host_procfs_request_bridge),
    cleanup_process_fn: Some(host_cleanup_process_request_bridge),
    cleanup_fd_fn: Some(host_cleanup_fd_request_bridge),
    debug_log_fn: Some(host_debug_log_request_bridge),
    sysfs_packet_fn: Some(host_sysfs_packet_bridge),
    perf_ctrl_fn: Some(host_perf_ctrl_request_bridge),
    cpu_rw_reg_fn: Some(host_cpu_rw_reg_request_bridge),
    unknown_packet_log_fn: Some(host_unknown_packet_log_bridge),
    release_packet_fn: Some(host_release_packet_bridge),
};

unsafe extern "C" fn syscall_packet_handler(
    channel: *mut c_void,
    packet: *mut c_void,
    os: *mut c_void,
) -> CInt {
    let profile_event = 0;
    host_syscall_packet_handler_result(
        channel,
        packet,
        os,
        &raw const HOST_SCD_DISPATCH_OPS,
        Some(host_current_ikc2linux_raw_bridge),
        Some(host_current_thread_raw_bridge),
        PF_POPULATE,
        profile_event,
        size_of::<IkcScdPacket>() as CULong,
        IHK_MC_AP_NOWAIT,
        PS_INTERRUPTIBLE,
        PS_RUNNING,
    )
}

unsafe extern "C" fn dummy_packet_handler(
    channel: *mut c_void,
    packet: *mut c_void,
    os: *mut c_void,
) -> CInt {
    host_dummy_packet_handler_result(channel, packet, os, Some(host_release_packet_bridge))
}

#[no_mangle]
pub unsafe extern "C" fn init_host_ikc2linux(linux_cpu: CInt) {
    let _ = host_init_ikc2linux_public_result(
        linux_cpu,
        &raw mut ikc2linuxs,
        ihk_mc_get_nr_linux_cores(),
        HOST_NUM_PROCESSORS,
        size_of::<IkcScdPacket>() as CULong,
        PAGE_SIZE,
        IHK_MC_AP_NOWAIT,
        Some(host_alloc_raw_bridge),
        Some(host_ikc_connect_raw_bridge),
        Some(host_delay_raw_bridge),
        Some(host_set_current_ikc2linux_raw_bridge),
        Some(dummy_packet_handler),
        Some(host_init_ikc2linux_log_raw_bridge),
        Some(host_panic_raw_bridge),
    );
}

#[no_mangle]
pub unsafe extern "C" fn init_host_ikc2mckernel() {
    let _ = host_init_ikc2mckernel_public_result(
        size_of::<IkcScdPacket>() as CULong,
        PAGE_SIZE,
        ihk_mc_get_processor_id(),
        Some(syscall_packet_handler),
        Some(host_ikc_connect_raw_bridge),
        Some(host_delay_raw_bridge),
        Some(host_set_regular_channel_raw_bridge),
        Some(host_init_ikc2mckernel_log_raw_bridge),
        Some(host_panic_raw_bridge),
    );
}
