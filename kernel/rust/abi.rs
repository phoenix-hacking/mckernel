#![allow(dead_code)]

use core::ffi::c_void;

pub type CInt = i32;
pub type CLong = i64;
pub type CULong = u64;
pub type SizeT = usize;
pub type OffT = i64;

pub const MCK_RLIM_MAX: usize = 20;
pub const PLD_CPU_SET_MAX_CPUS: usize = 1024;
pub const PLD_CPU_SET_SIZE: usize = PLD_CPU_SET_MAX_CPUS / (8 * core::mem::size_of::<CULong>());
pub const PLD_PROCESS_NUMA_MASK_BITS: usize = 256;
pub const PLD_NUMA_MASK_WORDS: usize =
    PLD_PROCESS_NUMA_MASK_BITS / (core::mem::size_of::<CULong>() * 8);
pub const CPU_SET_MAX_CPUS: usize = 1024;
pub const CPU_SET_WORDS: usize = CPU_SET_MAX_CPUS / (core::mem::size_of::<CULong>() * 8);
pub const PROCESS_HASH_SIZE: usize = 73;
pub const PROCESS_NUMA_MASK_BITS: usize = 256;
pub const PROCESS_NUMA_MASK_WORDS: usize =
    PROCESS_NUMA_MASK_BITS / (core::mem::size_of::<CULong>() * 8);
pub const VM_RANGE_CACHE_SIZE: usize = 4;
pub const AUXV_LEN: usize = 38;
pub const PATH_MAX: usize = 4096;
pub const PTHREAD_ROUTINE_LEN: usize = PATH_MAX + 64;
pub const IHK_MAX_NUM_PGSIZES: usize = 8;
pub const IHK_MAX_NUM_NUMA_NODES: usize = 1024;
pub const IHK_MAX_NUM_CPUS: usize = 1024;
#[cfg(enable_tofu)]
pub const TOFU_STAG_HASH_SIZE: usize = 4;

#[repr(C)]
pub struct RLimit {
    pub rlim_cur: u64,
    pub rlim_max: u64,
}

#[repr(C)]
pub struct ProgramImageSection {
    pub vaddr: CULong,
    pub len: CULong,
    pub remote_pa: CULong,
    pub filesz: CULong,
    pub offset: CULong,
    pub prot: CInt,
    pub interp: u8,
    pub padding: [u8; 3],
    pub fp: *mut c_void,
}

#[repr(C)]
pub struct ProgramLoadDesc {
    pub magic: CULong,
    pub num_sections: CInt,
    pub cpu: CInt,
    pub pid: CInt,
    pub stack_prot: CInt,
    pub pgid: CInt,
    pub cred: [CInt; 8],
    pub reloc: CInt,
    pub enable_vdso: i8,
    pub padding: [i8; 7],
    pub entry: CULong,
    pub user_start: CULong,
    pub user_end: CULong,
    pub rprocess: CULong,
    pub rpgtable: CULong,
    pub at_phdr: CULong,
    pub at_phent: CULong,
    pub at_phnum: CULong,
    pub at_entry: CULong,
    pub at_clktck: CULong,
    pub args: *mut i8,
    pub args_len: CULong,
    pub envs: *mut i8,
    pub envs_len: CULong,
    pub rlimit: [RLimit; MCK_RLIM_MAX],
    pub interp_align: CULong,
    pub mpol_flags: CULong,
    pub mpol_threshold: CULong,
    pub heap_extension: CULong,
    pub stack_premap: CLong,
    pub mpol_bind_mask: CULong,
    pub mpol_mode: CInt,
    pub mpol_nodemask: [CULong; PLD_NUMA_MASK_WORDS],
    pub thp_disable: CInt,
    pub enable_uti: CInt,
    pub uti_thread_rank: CInt,
    pub uti_use_last_cpu: CInt,
    pub straight_map: CInt,
    pub straight_map_threshold: SizeT,
    #[cfg(enable_tofu)]
    pub enable_tofu: CInt,
    pub mcexec_flags: CULong,
    pub nr_processes: CInt,
    pub process_rank: CInt,
    pub cpu_set: [CULong; PLD_CPU_SET_SIZE],
    pub profile: CInt,
}

#[repr(C)]
pub struct SyscallRequest {
    pub rtid: CInt,
    pub ttid: CInt,
    pub valid: CULong,
    pub number: CULong,
    pub args: [CULong; 6],
}

#[repr(C)]
pub struct SyscallResponse {
    pub ttid: CInt,
    pub stid: CInt,
    pub status: CULong,
    pub req_thread_status: CULong,
    pub ret: CLong,
    pub fault_address: CULong,
    pub pde_data: *mut c_void,
}

#[repr(C)]
pub struct IhkIkcPacketHeader {
    pub channel: *mut c_void,
}

#[repr(C)]
pub struct IkcScdPacketTraditional {
    pub ref_: CInt,
    pub osnum: CInt,
    pub pid: CInt,
    pub arg: CULong,
    pub req: SyscallRequest,
    pub resp_pa: CULong,
}

#[repr(C)]
pub struct IkcScdPacketSysfs {
    pub sysfs_arg1: CLong,
    pub sysfs_arg2: CLong,
    pub sysfs_arg3: CLong,
}

#[repr(C)]
pub struct IkcScdPacketCpuRw {
    pub pdesc: CULong,
    pub op: CInt,
    pub resp: *mut c_void,
}

#[repr(C)]
pub struct IkcScdPacketFutex {
    pub resp: *mut c_void,
    pub spin_sleep: *mut CInt,
}

#[repr(C)]
pub struct IkcScdPacketRemotePageFault {
    pub target_cpu: CInt,
    pub fault_tid: CInt,
    pub fault_address: CULong,
    pub fault_reason: CULong,
}

#[repr(C)]
pub union IkcScdPacketBody {
    pub traditional: core::mem::ManuallyDrop<IkcScdPacketTraditional>,
    pub sysfs: core::mem::ManuallyDrop<IkcScdPacketSysfs>,
    pub ttid: CInt,
    pub cpu_rw: core::mem::ManuallyDrop<IkcScdPacketCpuRw>,
    pub eventfd_type: CInt,
    pub futex: core::mem::ManuallyDrop<IkcScdPacketFutex>,
    pub remote_page_fault: core::mem::ManuallyDrop<IkcScdPacketRemotePageFault>,
}

#[repr(C)]
pub struct IkcScdPacket {
    pub header: IhkIkcPacketHeader,
    pub msg: CInt,
    pub err: CInt,
    pub reply: *mut c_void,
    pub body: IkcScdPacketBody,
}

#[repr(C)]
pub struct X86BasicRegs {
    pub r15: CULong,
    pub r14: CULong,
    pub r13: CULong,
    pub r12: CULong,
    pub rbp: CULong,
    pub rbx: CULong,
    pub r11: CULong,
    pub r10: CULong,
    pub r9: CULong,
    pub r8: CULong,
    pub rax: CULong,
    pub rcx: CULong,
    pub rdx: CULong,
    pub rsi: CULong,
    pub rdi: CULong,
    pub orig_rax: CULong,
    pub rip: CULong,
    pub cs: CULong,
    pub rflags: CULong,
    pub rsp: CULong,
    pub ss: CULong,
}

#[repr(C)]
pub struct X86Sregs {
    pub fs_base: CULong,
    pub gs_base: CULong,
    pub ds: CULong,
    pub es: CULong,
    pub fs: CULong,
    pub gs: CULong,
}

#[repr(C)]
pub struct X86UserContext {
    pub sr: X86Sregs,
    pub is_gpr_valid: u8,
    pub is_sr_valid: u8,
    pub spare_flags6: u8,
    pub spare_flags5: u8,
    pub spare_flags4: u8,
    pub spare_flags3: u8,
    pub spare_flags2: u8,
    pub spare_flags1: u8,
    pub gpr: X86BasicRegs,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct AbiListHead {
    pub next: *mut AbiListHead,
    pub prev: *mut AbiListHead,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct AbiRbNode {
    pub __rb_parent_color: CULong,
    pub rb_right: *mut AbiRbNode,
    pub rb_left: *mut AbiRbNode,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct AbiRbRoot {
    pub rb_node: *mut AbiRbNode,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkAtomic {
    pub counter: CInt,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkSpinlock {
    pub head_tail: u32,
}

#[repr(C, align(4))]
#[derive(Clone, Copy)]
pub struct IhkRwSpinlock {
    pub v: IhkAtomic,
}

#[repr(C, align(64))]
pub struct McsRwlockLock {
    pub slock: IhkSpinlock,
}

#[repr(C)]
pub struct CpuSet {
    pub bits: [CULong; CPU_SET_WORDS],
}

#[repr(C)]
pub struct TimeSpec {
    pub tv_sec: CLong,
    pub tv_nsec: CLong,
}

#[repr(C)]
pub struct TimeVal {
    pub tv_sec: CLong,
    pub tv_usec: CLong,
}

#[repr(C)]
pub struct ITimerVal {
    pub it_interval: TimeVal,
    pub it_value: TimeVal,
}

#[repr(C)]
pub struct Waitq {
    pub lock: IhkSpinlock,
    pub waitq: AbiListHead,
}

#[repr(C)]
pub struct Timer {
    pub timeout: CULong,
    pub processes: Waitq,
    pub list: AbiListHead,
    pub thread: *mut c_void,
}

#[repr(C)]
pub struct X86KernelContext {
    pub rsp: CULong,
    pub rbp: CULong,
    pub rbx: CULong,
    pub rsi: CULong,
    pub rdi: CULong,
    pub r12: CULong,
    pub r13: CULong,
    pub r14: CULong,
    pub r15: CULong,
    pub rflags: CULong,
    pub rsp0: CULong,
}

#[repr(C)]
pub struct SigSet {
    pub val: [CULong; 1],
}

#[repr(C)]
pub struct SigStack {
    pub ss_sp: *mut c_void,
    pub ss_flags: CInt,
    pub padding: CInt,
    pub ss_size: SizeT,
}

#[repr(C)]
pub struct KSigAction {
    pub sa_handler: *mut c_void,
    pub sa_flags: CULong,
    pub sa_restorer: *mut c_void,
    pub sa_mask: SigSet,
}

#[repr(C)]
pub struct SigInfo {
    pub raw: [CULong; 16],
}

#[repr(C)]
pub struct SchedParam {
    pub sched_priority: CInt,
}

#[repr(C, align(64))]
pub struct McsLockNode {
    pub locked: CULong,
    pub next: *mut McsLockNode,
    pub irqsave: CULong,
}

#[repr(C)]
pub struct PlistHead {
    pub prio_list: AbiListHead,
    pub node_list: AbiListHead,
}

#[repr(C)]
pub struct PlistNode {
    pub prio: CInt,
    pub plist: PlistHead,
}

#[repr(C)]
pub struct FutexKey {
    pub opaque: [CULong; 3],
}

#[repr(C)]
pub struct FutexQ {
    pub list: PlistNode,
    pub task: *mut c_void,
    pub lock_ptr: *mut IhkSpinlock,
    pub key: FutexKey,
    pub requeue_pi_key: *mut FutexKey,
    pub bitset: u32,
    pub uti_futex_resp: *mut c_void,
    pub linux_cpu: CInt,
    pub th_spin_sleep: *mut c_void,
    pub th_status: *mut c_void,
    pub th_spin_sleep_lock: *mut c_void,
    pub proc_status: *mut c_void,
    pub proc_update_lock: *mut c_void,
    pub runq_lock: *mut c_void,
    pub clv_flags: *mut c_void,
    pub intr_id: CInt,
    pub intr_vector: CInt,
    pub th_spin_sleep_pa: CULong,
    pub th_status_pa: CULong,
    pub th_spin_sleep_lock_pa: CULong,
    pub proc_status_pa: CULong,
    pub proc_update_lock_pa: CULong,
    pub runq_lock_pa: CULong,
    pub clv_flags_pa: CULong,
}

#[repr(C)]
pub struct ResourceSet {
    pub list: AbiListHead,
    pub path: *mut i8,
    pub process_hash: *mut ProcessHash,
    pub thread_hash: *mut ThreadHash,
    pub phys_mem_list: AbiListHead,
    pub phys_mem_lock: McsRwlockLock,
    pub cpu_set: CpuSet,
    pub cpu_set_lock: McsRwlockLock,
    pub pid1: *mut Process,
}

#[repr(C)]
pub struct ProcessHash {
    pub list: [AbiListHead; PROCESS_HASH_SIZE],
    pub lock: [McsRwlockLock; PROCESS_HASH_SIZE],
}

#[repr(C)]
pub struct ThreadHash {
    pub list: [AbiListHead; PROCESS_HASH_SIZE],
    pub lock: [McsRwlockLock; PROCESS_HASH_SIZE],
}

#[repr(C)]
pub struct AddressSpace {
    pub page_table: *mut c_void,
    pub opt: *mut c_void,
    pub free_cb: Option<unsafe extern "C" fn(*mut AddressSpace, *mut c_void)>,
    pub refcount: IhkAtomic,
    pub cpu_set: CpuSet,
    pub cpu_set_lock: IhkSpinlock,
    pub nslots: CInt,
}

#[repr(C)]
pub struct VmRange {
    pub vm_rb_node: AbiRbNode,
    pub start: CULong,
    pub end: CULong,
    pub flag: CULong,
    pub straight_start: CULong,
    pub memobj: *mut c_void,
    pub objoff: OffT,
    pub pgshift: CInt,
    pub padding: CInt,
    #[cfg(enable_tofu)]
    pub tofu_stag_list: AbiListHead,
    pub private_data: *mut c_void,
}

#[repr(C)]
pub struct VmRangeNumaPolicy {
    pub policy_rb_node: AbiRbNode,
    pub start: CULong,
    pub end: CULong,
    pub numa_mask: [CULong; PROCESS_NUMA_MASK_WORDS],
    pub numa_mem_policy: CInt,
    pub il_prev: CInt,
}

#[repr(C)]
pub struct VmRegions {
    pub vm_start: CULong,
    pub vm_end: CULong,
    pub text_start: CULong,
    pub text_end: CULong,
    pub data_start: CULong,
    pub data_end: CULong,
    pub brk_start: CULong,
    pub brk_end: CULong,
    pub brk_end_allocated: CULong,
    pub map_start: CULong,
    pub map_end: CULong,
    pub stack_start: CULong,
    pub stack_end: CULong,
    pub user_start: CULong,
    pub user_end: CULong,
}

#[repr(C)]
pub struct ProcessVm {
    pub address_space: *mut AddressSpace,
    pub vm_range_tree: AbiRbRoot,
    pub region: VmRegions,
    pub proc: *mut c_void,
    pub opt: *mut c_void,
    pub free_cb: Option<unsafe extern "C" fn(*mut ProcessVm, *mut c_void)>,
    pub vdso_addr: *mut c_void,
    pub vvar_addr: *mut c_void,
    pub page_table_lock: IhkSpinlock,
    pub memory_range_lock: IhkRwSpinlock,
    pub is_memory_range_lock_taken: CInt,
    pub refcount: IhkAtomic,
    pub exiting: CInt,
    pub currss: CLong,
    pub numa_mask: [CULong; PROCESS_NUMA_MASK_WORDS],
    pub numa_mem_policy: CInt,
    pub il_prev: CInt,
    pub vm_range_numa_policy_tree: AbiRbRoot,
    pub range_cache: [*mut VmRange; VM_RANGE_CACHE_SIZE],
    pub range_cache_ind: CInt,
    pub swapinfo: *mut c_void,
    #[cfg(enable_tofu)]
    pub tofu_stag_lock: IhkSpinlock,
    #[cfg(enable_tofu)]
    pub tofu_stag_hash: [AbiListHead; TOFU_STAG_HASH_SIZE],
}

#[repr(C)]
pub struct Process {
    pub hash_list: AbiListHead,
    pub update_lock: McsRwlockLock,
    pub vm: *mut ProcessVm,
    pub threads_list: AbiListHead,
    pub report_threads_list: AbiListHead,
    pub main_thread: *mut Thread,
    pub threads_lock: McsRwlockLock,
    pub tids: *mut c_void,
    pub nr_tids: CInt,
    pub parent: *mut Process,
    pub ppid_parent: *mut Process,
    pub children_list: AbiListHead,
    pub ptraced_children_list: AbiListHead,
    pub children_lock: McsRwlockLock,
    pub siblings_list: AbiListHead,
    pub ptraced_siblings_list: AbiListHead,
    pub refcount: IhkAtomic,
    pub status: CInt,
    pub group_exit_status: CULong,
    pub waitpid_q: Waitq,
    pub pid: CInt,
    pub pgid: CInt,
    pub ruid: CInt,
    pub euid: CInt,
    pub suid: CInt,
    pub fsuid: CInt,
    pub rgid: CInt,
    pub egid: CInt,
    pub sgid: CInt,
    pub fsgid: CInt,
    pub execed: CInt,
    pub nohost: CInt,
    pub nowait: CInt,
    pub rlimit: [RLimit; MCK_RLIM_MAX],
    pub saved_auxv: [CULong; AUXV_LEN],
    pub saved_cmdline: *mut i8,
    pub saved_cmdline_len: CLong,
    pub cpu_set: CpuSet,
    pub termsig: CInt,
    pub mckfd_lock: IhkSpinlock,
    pub mckfd: *mut c_void,
    pub stime: TimeSpec,
    pub utime: TimeSpec,
    pub stime_children: TimeSpec,
    pub utime_children: TimeSpec,
    pub maxrss: CLong,
    pub maxrss_children: CLong,
    pub mpol_flags: CULong,
    pub mpol_threshold: SizeT,
    pub heap_extension: CULong,
    pub mpol_bind_mask: CULong,
    pub mpol_mode: CInt,
    pub enable_uti: CInt,
    pub uti_thread_rank: CInt,
    pub uti_use_last_cpu: CInt,
    pub clone_count: CInt,
    pub thp_disable: CInt,
    pub straight_map: CInt,
    #[cfg(enable_tofu)]
    pub enable_tofu: CInt,
    pub straight_map_threshold: SizeT,
    pub mcexec_flags: CULong,
    pub perf_status: CInt,
    pub monitoring_event: *mut c_void,
    pub profile: CInt,
    pub profile_lock: McsLockNode,
    pub profile_events: *mut c_void,
    pub profile_elapsed_ts: CULong,
    pub nr_processes: CInt,
    pub process_rank: CInt,
    pub straight_va: *mut c_void,
    pub straight_len: SizeT,
    pub straight_pa: CULong,
    pub coredump_barrier_count: CInt,
    pub coredump_barrier_count2: CInt,
    pub coredump_lock: McsRwlockLock,
    #[cfg(enable_tofu)]
    pub fd_pde_data: [*mut c_void; 1024],
    #[cfg(enable_tofu)]
    pub fd_path: [*mut i8; 1024],
}

#[repr(C)]
pub struct Thread {
    pub hash_list: AbiListHead,
    pub cpu_id: CInt,
    pub tid: CInt,
    pub pthread_routine: [u8; PTHREAD_ROUTINE_LEN],
    pub status: CInt,
    pub exit_status: CInt,
    pub signal_flags: CInt,
    pub termsig: CInt,
    pub vm: *mut ProcessVm,
    pub ctx: X86KernelContext,
    pub uctx: *mut X86UserContext,
    pub proc: *mut Process,
    pub siblings_list: AbiListHead,
    pub sched_list: AbiListHead,
    pub sched_policy: CInt,
    pub sched_param: SchedParam,
    pub spin_sleep_lock: IhkSpinlock,
    pub spin_sleep: CInt,
    pub report_proc: *mut Process,
    pub report_siblings_list: AbiListHead,
    pub ptrace: CInt,
    pub ptrace_eventmsg: CULong,
    pub ptrace_saved_uctx: X86UserContext,
    pub ptrace_saved_uctx_valid: CInt,
    pub refcount: IhkAtomic,
    pub clear_child_tid: *mut CInt,
    pub tlsblock_base: CULong,
    pub tlsblock_limit: CULong,
    pub cpu_set: CpuSet,
    pub fp_regs: *mut c_void,
    pub in_syscall_offload: CInt,
    pub profile: CInt,
    pub profile_events: *mut c_void,
    pub profile_start_ts: CULong,
    pub profile_elapsed_ts: CULong,
    pub sigcommon: *mut c_void,
    pub sigmask: SigSet,
    pub sigstack: SigStack,
    pub sigpending: AbiListHead,
    pub sigpendinglock: McsRwlockLock,
    pub sigevent: CInt,
    pub pgio_fp: *mut c_void,
    pub pgio_arg: *mut c_void,
    pub ptrace_debugreg: *mut CULong,
    pub ptrace_recvsig: *mut c_void,
    pub ptrace_sendsig: *mut c_void,
    pub system_tsc: CULong,
    pub user_tsc: CULong,
    pub base_tsc: CULong,
    pub times_update: CInt,
    pub in_kernel: CInt,
    pub itimer_enabled: CInt,
    pub itimer_virtual: ITimerVal,
    pub itimer_prof: ITimerVal,
    pub itimer_virtual_value: TimeSpec,
    pub itimer_prof_value: TimeSpec,
    pub scd_wq: Waitq,
    pub clone_pthread_start_routine: CULong,
    pub uti_state: CInt,
    pub mod_clone: CInt,
    pub mod_clone_arg: *mut c_void,
    pub parent_cpuid: CInt,
    pub uti_refill_tid: CInt,
    pub futex_q: FutexQ,
    pub pmc_alloc_map: CULong,
    pub extra_reg_alloc_map: CULong,
    pub coredump_regs: *mut c_void,
    pub coredump_wq: Waitq,
    pub coredump_status: CInt,
    pub rpf_backlog: *mut c_void,
    pub rpf_arg: *mut c_void,
    #[cfg(enable_tofu)]
    pub fd_path_in_open: *mut i8,
}

#[repr(C)]
pub struct Mckfd {
    pub next: *mut Mckfd,
    pub fd: CInt,
    pub padding: CInt,
    pub data: CLong,
    pub opt: *mut c_void,
    pub read_cb: *mut c_void,
    pub ioctl_cb: *mut c_void,
    pub mmap_cb: *mut c_void,
    pub close_cb: *mut c_void,
    pub fcntl_cb: *mut c_void,
    pub dup_cb: *mut c_void,
}

#[repr(C)]
pub struct SigCommon {
    pub lock: McsRwlockLock,
    pub use_: IhkAtomic,
    pub padding: CInt,
    pub action: [KSigAction; 64],
    pub sigpending: AbiListHead,
}

#[repr(C)]
pub struct SigPending {
    pub list: AbiListHead,
    pub sigmask: SigSet,
    pub info: SigInfo,
    pub ptracecont: CInt,
    pub interrupted: CInt,
}

#[repr(C)]
pub struct McexecTid {
    pub tid: CInt,
    pub padding: CInt,
    pub thread: *mut Thread,
}

#[repr(C)]
pub struct IhkOsCpuRegister {
    pub addr: CULong,
    pub val: CULong,
    pub addr_ext: CULong,
    pub sync: IhkAtomic,
}

#[repr(C)]
pub struct IhkOsCpuMonitor {
    pub status: CInt,
    pub status_bak: CInt,
    pub counter: CULong,
    pub ocounter: CULong,
}

#[repr(C)]
pub struct IhkOsMonitor {
    pub num_processors: CULong,
    pub reserve: [CULong; 128],
    pub cpu: [IhkOsCpuMonitor; 0],
}

#[repr(C)]
pub struct IhkOsRusage {
    pub memory_stat_rss: [CULong; IHK_MAX_NUM_PGSIZES],
    pub memory_stat_mapped_file: [CULong; IHK_MAX_NUM_PGSIZES],
    pub memory_max_usage: CULong,
    pub memory_kmem_usage: CULong,
    pub memory_kmem_max_usage: CULong,
    pub memory_numa_stat: [CULong; IHK_MAX_NUM_NUMA_NODES],
    pub cpuacct_stat_system: CULong,
    pub cpuacct_stat_user: CULong,
    pub cpuacct_usage: CULong,
    pub cpuacct_usage_percpu: [CULong; IHK_MAX_NUM_CPUS],
    pub num_threads: CInt,
    pub max_num_threads: CInt,
}

#[repr(C)]
pub struct IhkRegisterDeviceData {
    pub name: *mut i8,
    pub ops: *mut c_void,
    pub priv_: *mut c_void,
    pub flag: CInt,
}

#[repr(C)]
pub struct IhkRegisterOsData {
    pub name: *mut i8,
    pub ops: *mut c_void,
    pub priv_: *mut c_void,
    pub flag: CInt,
}

#[repr(C)]
pub struct IhkMemRegion {
    pub start: CULong,
    pub size: CULong,
}

#[repr(C)]
pub struct IhkMemInfo {
    pub n_available: CInt,
    pub n_fixed: CInt,
    pub n_mappable: CInt,
    pub available: *mut IhkMemRegion,
    pub fixed: *mut IhkMemRegion,
    pub mappable: *mut IhkMemRegion,
    pub n_numa_nodes: CInt,
    pub numa_mapping: *mut CInt,
}

#[repr(C)]
pub struct IhkCpuInfo {
    pub n_cpus: CInt,
    pub mapping: *mut CInt,
    pub hw_ids: *mut CInt,
    pub ikc_map: *mut CInt,
    pub ikc_mapped: CInt,
}

const fn assert_eq_usize(left: usize, right: usize) {
    assert!(left == right);
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert_eq_usize(size_of::<RLimit>(), 16);
    assert_eq_usize(size_of::<ProgramImageSection>(), 56);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<ProgramLoadDesc>(), 776);
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<ProgramLoadDesc>(), 784);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(ProgramLoadDesc, profile), 768);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(ProgramLoadDesc, profile), 776);

    assert_eq_usize(size_of::<SyscallRequest>(), 72);
    assert_eq_usize(offset_of!(SyscallRequest, args), 24);
    assert_eq_usize(size_of::<SyscallResponse>(), 48);
    assert_eq_usize(size_of::<IhkIkcPacketHeader>(), 8);
    assert_eq_usize(size_of::<IkcScdPacketTraditional>(), 104);
    assert_eq_usize(size_of::<IkcScdPacket>(), 128);
    assert_eq_usize(align_of::<IkcScdPacket>(), 8);

    assert_eq_usize(size_of::<X86BasicRegs>(), 168);
    assert_eq_usize(size_of::<X86Sregs>(), 48);
    assert_eq_usize(size_of::<X86UserContext>(), 224);
    assert_eq_usize(offset_of!(X86UserContext, gpr), 56);

    assert_eq_usize(size_of::<AbiListHead>(), 16);
    assert_eq_usize(align_of::<AbiListHead>(), 8);
    assert_eq_usize(offset_of!(AbiListHead, prev), 8);
    assert_eq_usize(size_of::<AbiRbNode>(), 24);
    assert_eq_usize(align_of::<AbiRbNode>(), 8);
    assert_eq_usize(offset_of!(AbiRbNode, rb_right), 8);
    assert_eq_usize(offset_of!(AbiRbNode, rb_left), 16);
    assert_eq_usize(size_of::<AbiRbRoot>(), 8);
    assert_eq_usize(align_of::<AbiRbRoot>(), 8);
    assert_eq_usize(size_of::<IhkAtomic>(), 4);
    assert_eq_usize(align_of::<IhkAtomic>(), 4);
    assert_eq_usize(offset_of!(IhkAtomic, counter), 0);
    assert_eq_usize(size_of::<IhkSpinlock>(), 4);
    assert_eq_usize(align_of::<IhkSpinlock>(), 4);
    assert_eq_usize(offset_of!(IhkSpinlock, head_tail), 0);
    assert_eq_usize(size_of::<IhkRwSpinlock>(), 4);
    assert_eq_usize(align_of::<IhkRwSpinlock>(), 4);
    assert_eq_usize(offset_of!(IhkRwSpinlock, v), 0);
    assert_eq_usize(size_of::<McsRwlockLock>(), 64);
    assert_eq_usize(align_of::<McsRwlockLock>(), 64);
    assert_eq_usize(offset_of!(McsRwlockLock, slock), 0);
    assert_eq_usize(size_of::<CpuSet>(), 128);
    assert_eq_usize(align_of::<CpuSet>(), 8);
    assert_eq_usize(size_of::<TimeSpec>(), 16);
    assert_eq_usize(size_of::<ITimerVal>(), 32);
    assert_eq_usize(size_of::<Waitq>(), 24);
    assert_eq_usize(offset_of!(Waitq, waitq), 8);
    assert_eq_usize(size_of::<Timer>(), 56);
    assert_eq_usize(offset_of!(Timer, processes), 8);
    assert_eq_usize(offset_of!(Timer, list), 32);
    assert_eq_usize(offset_of!(Timer, thread), 48);
    assert_eq_usize(size_of::<X86KernelContext>(), 88);
    assert_eq_usize(size_of::<SigSet>(), 8);
    assert_eq_usize(size_of::<SigStack>(), 24);
    assert_eq_usize(offset_of!(SigStack, ss_size), 16);
    assert_eq_usize(size_of::<KSigAction>(), 32);
    assert_eq_usize(size_of::<SigInfo>(), 128);
    assert_eq_usize(size_of::<McsLockNode>(), 64);
    assert_eq_usize(align_of::<McsLockNode>(), 64);
    assert_eq_usize(offset_of!(McsLockNode, next), 8);
    assert_eq_usize(offset_of!(McsLockNode, irqsave), 16);
    assert_eq_usize(size_of::<PlistHead>(), 32);
    assert_eq_usize(size_of::<PlistNode>(), 40);
    assert_eq_usize(size_of::<FutexKey>(), 24);
    assert_eq_usize(size_of::<FutexQ>(), 232);
    assert_eq_usize(offset_of!(FutexQ, key), 56);
    assert_eq_usize(offset_of!(FutexQ, bitset), 88);
    assert_eq_usize(offset_of!(FutexQ, th_spin_sleep), 112);
    assert_eq_usize(offset_of!(FutexQ, intr_id), 168);
    assert_eq_usize(offset_of!(FutexQ, th_spin_sleep_pa), 176);

    assert_eq_usize(size_of::<ResourceSet>(), 384);
    assert_eq_usize(align_of::<ResourceSet>(), 64);
    assert_eq_usize(offset_of!(ResourceSet, path), 16);
    assert_eq_usize(offset_of!(ResourceSet, process_hash), 24);
    assert_eq_usize(offset_of!(ResourceSet, phys_mem_lock), 64);
    assert_eq_usize(offset_of!(ResourceSet, cpu_set), 128);
    assert_eq_usize(offset_of!(ResourceSet, pid1), 320);

    assert_eq_usize(size_of::<ProcessHash>(), 5888);
    assert_eq_usize(align_of::<ProcessHash>(), 64);
    assert_eq_usize(offset_of!(ProcessHash, list), 0);
    assert_eq_usize(offset_of!(ProcessHash, lock), 1216);
    assert_eq_usize(size_of::<ThreadHash>(), 5888);
    assert_eq_usize(align_of::<ThreadHash>(), 64);
    assert_eq_usize(offset_of!(ThreadHash, lock), 1216);

    assert_eq_usize(size_of::<AddressSpace>(), 168);
    assert_eq_usize(align_of::<AddressSpace>(), 8);
    assert_eq_usize(offset_of!(AddressSpace, page_table), 0);
    assert_eq_usize(offset_of!(AddressSpace, free_cb), 16);
    assert_eq_usize(offset_of!(AddressSpace, refcount), 24);
    assert_eq_usize(offset_of!(AddressSpace, cpu_set), 32);
    assert_eq_usize(offset_of!(AddressSpace, cpu_set_lock), 160);
    assert_eq_usize(offset_of!(AddressSpace, nslots), 164);

    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<VmRange>(), 88);
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<VmRange>(), 104);
    assert_eq_usize(align_of::<VmRange>(), 8);
    assert_eq_usize(offset_of!(VmRange, vm_rb_node), 0);
    assert_eq_usize(offset_of!(VmRange, start), 24);
    assert_eq_usize(offset_of!(VmRange, straight_start), 48);
    assert_eq_usize(offset_of!(VmRange, memobj), 56);
    assert_eq_usize(offset_of!(VmRange, objoff), 64);
    assert_eq_usize(offset_of!(VmRange, pgshift), 72);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(VmRange, private_data), 80);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(VmRange, tofu_stag_list), 80);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(VmRange, private_data), 96);

    assert_eq_usize(size_of::<VmRangeNumaPolicy>(), 80);
    assert_eq_usize(align_of::<VmRangeNumaPolicy>(), 8);
    assert_eq_usize(offset_of!(VmRangeNumaPolicy, policy_rb_node), 0);
    assert_eq_usize(offset_of!(VmRangeNumaPolicy, start), 24);
    assert_eq_usize(offset_of!(VmRangeNumaPolicy, numa_mask), 40);
    assert_eq_usize(offset_of!(VmRangeNumaPolicy, numa_mem_policy), 72);
    assert_eq_usize(offset_of!(VmRangeNumaPolicy, il_prev), 76);

    assert_eq_usize(size_of::<VmRegions>(), 120);
    assert_eq_usize(align_of::<VmRegions>(), 8);
    assert_eq_usize(offset_of!(VmRegions, brk_start), 48);
    assert_eq_usize(offset_of!(VmRegions, brk_end_allocated), 64);
    assert_eq_usize(offset_of!(VmRegions, map_start), 72);
    assert_eq_usize(offset_of!(VmRegions, stack_start), 88);
    assert_eq_usize(offset_of!(VmRegions, user_start), 104);

    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<ProcessVm>(), 304);
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<ProcessVm>(), 376);
    assert_eq_usize(align_of::<ProcessVm>(), 8);
    assert_eq_usize(offset_of!(ProcessVm, address_space), 0);
    assert_eq_usize(offset_of!(ProcessVm, vm_range_tree), 8);
    assert_eq_usize(offset_of!(ProcessVm, region), 16);
    assert_eq_usize(offset_of!(ProcessVm, proc), 136);
    assert_eq_usize(offset_of!(ProcessVm, free_cb), 152);
    assert_eq_usize(offset_of!(ProcessVm, vdso_addr), 160);
    assert_eq_usize(offset_of!(ProcessVm, page_table_lock), 176);
    assert_eq_usize(offset_of!(ProcessVm, memory_range_lock), 180);
    assert_eq_usize(offset_of!(ProcessVm, refcount), 188);
    assert_eq_usize(offset_of!(ProcessVm, currss), 200);
    assert_eq_usize(offset_of!(ProcessVm, numa_mask), 208);
    assert_eq_usize(offset_of!(ProcessVm, vm_range_numa_policy_tree), 248);
    assert_eq_usize(offset_of!(ProcessVm, range_cache), 256);
    assert_eq_usize(offset_of!(ProcessVm, range_cache_ind), 288);
    assert_eq_usize(offset_of!(ProcessVm, swapinfo), 296);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(ProcessVm, tofu_stag_lock), 304);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(ProcessVm, tofu_stag_hash), 312);

    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<Process>(), 1728);
    assert_eq_usize(align_of::<Process>(), 64);
    assert_eq_usize(offset_of!(Process, vm), 128);
    assert_eq_usize(offset_of!(Process, threads_list), 136);
    assert_eq_usize(offset_of!(Process, main_thread), 168);
    assert_eq_usize(offset_of!(Process, parent), 272);
    assert_eq_usize(offset_of!(Process, refcount), 416);
    assert_eq_usize(offset_of!(Process, status), 420);
    assert_eq_usize(offset_of!(Process, group_exit_status), 424);
    assert_eq_usize(offset_of!(Process, waitpid_q), 432);
    assert_eq_usize(offset_of!(Process, pid), 456);
    assert_eq_usize(offset_of!(Process, rlimit), 512);
    assert_eq_usize(offset_of!(Process, cpu_set), 1152);
    assert_eq_usize(offset_of!(Process, mckfd_lock), 1284);
    assert_eq_usize(offset_of!(Process, stime), 1296);
    assert_eq_usize(offset_of!(Process, maxrss), 1360);
    assert_eq_usize(offset_of!(Process, straight_map), 1432);
    assert_eq_usize(offset_of!(Process, perf_status), 1456);
    assert_eq_usize(offset_of!(Process, monitoring_event), 1464);
    assert_eq_usize(offset_of!(Process, profile), 1472);
    assert_eq_usize(offset_of!(Process, nr_processes), 1616);
    assert_eq_usize(offset_of!(Process, straight_va), 1624);
    assert_eq_usize(offset_of!(Process, coredump_lock), 1664);

    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<Thread>(), 5568);
    assert_eq_usize(align_of::<Thread>(), 64);
    assert_eq_usize(offset_of!(Thread, cpu_id), 16);
    assert_eq_usize(offset_of!(Thread, status), 4184);
    assert_eq_usize(offset_of!(Thread, vm), 4200);
    assert_eq_usize(offset_of!(Thread, ctx), 4208);
    assert_eq_usize(offset_of!(Thread, proc), 4304);
    assert_eq_usize(offset_of!(Thread, sched_list), 4328);
    assert_eq_usize(offset_of!(Thread, sched_policy), 4344);
    assert_eq_usize(offset_of!(Thread, spin_sleep_lock), 4352);
    assert_eq_usize(offset_of!(Thread, report_proc), 4360);
    assert_eq_usize(offset_of!(Thread, ptrace), 4384);
    assert_eq_usize(offset_of!(Thread, ptrace_saved_uctx), 4400);
    assert_eq_usize(offset_of!(Thread, refcount), 4628);
    assert_eq_usize(offset_of!(Thread, clear_child_tid), 4632);
    assert_eq_usize(offset_of!(Thread, cpu_set), 4656);
    assert_eq_usize(offset_of!(Thread, sigcommon), 4824);
    assert_eq_usize(offset_of!(Thread, sigmask), 4832);
    assert_eq_usize(offset_of!(Thread, sigstack), 4840);
    assert_eq_usize(offset_of!(Thread, sigpending), 4864);
    assert_eq_usize(offset_of!(Thread, scd_wq), 5176);
    assert_eq_usize(offset_of!(Thread, futex_q), 5232);
    assert_eq_usize(offset_of!(Thread, pmc_alloc_map), 5464);
    assert_eq_usize(offset_of!(Thread, coredump_regs), 5480);
    assert_eq_usize(offset_of!(Thread, rpf_backlog), 5520);

    assert_eq_usize(size_of::<Mckfd>(), 80);
    assert_eq_usize(offset_of!(Mckfd, fd), 8);
    assert_eq_usize(offset_of!(Mckfd, data), 16);
    assert_eq_usize(offset_of!(Mckfd, read_cb), 32);
    assert_eq_usize(offset_of!(Mckfd, dup_cb), 72);
    assert_eq_usize(size_of::<SigCommon>(), 2176);
    assert_eq_usize(align_of::<SigCommon>(), 64);
    assert_eq_usize(offset_of!(SigCommon, use_), 64);
    assert_eq_usize(offset_of!(SigCommon, action), 72);
    assert_eq_usize(offset_of!(SigCommon, sigpending), 2120);
    assert_eq_usize(size_of::<SigPending>(), 160);
    assert_eq_usize(offset_of!(SigPending, sigmask), 16);
    assert_eq_usize(offset_of!(SigPending, info), 24);
    assert_eq_usize(offset_of!(SigPending, ptracecont), 152);
    assert_eq_usize(size_of::<McexecTid>(), 16);
    assert_eq_usize(offset_of!(McexecTid, thread), 8);

    assert_eq_usize(size_of::<IhkOsCpuRegister>(), 32);
    assert_eq_usize(offset_of!(IhkOsCpuRegister, val), 8);
    assert_eq_usize(offset_of!(IhkOsCpuRegister, sync), 24);
    assert_eq_usize(size_of::<IhkOsCpuMonitor>(), 24);
    assert_eq_usize(offset_of!(IhkOsCpuMonitor, counter), 8);
    assert_eq_usize(size_of::<IhkOsMonitor>(), 1032);
    assert_eq_usize(offset_of!(IhkOsMonitor, cpu), 1032);
    assert_eq_usize(size_of::<IhkOsRusage>(), 16568);
    assert_eq_usize(offset_of!(IhkOsRusage, memory_max_usage), 128);
    assert_eq_usize(offset_of!(IhkOsRusage, cpuacct_usage_percpu), 8368);
    assert_eq_usize(offset_of!(IhkOsRusage, num_threads), 16560);
    assert_eq_usize(size_of::<IhkRegisterDeviceData>(), 32);
    assert_eq_usize(offset_of!(IhkRegisterDeviceData, ops), 8);
    assert_eq_usize(offset_of!(IhkRegisterDeviceData, flag), 24);
    assert_eq_usize(size_of::<IhkRegisterOsData>(), 32);
    assert_eq_usize(offset_of!(IhkRegisterOsData, ops), 8);
    assert_eq_usize(offset_of!(IhkRegisterOsData, flag), 24);
    assert_eq_usize(size_of::<IhkMemRegion>(), 16);
    assert_eq_usize(size_of::<IhkMemInfo>(), 56);
    assert_eq_usize(offset_of!(IhkMemInfo, available), 16);
    assert_eq_usize(offset_of!(IhkMemInfo, numa_mapping), 48);
    assert_eq_usize(size_of::<IhkCpuInfo>(), 40);
    assert_eq_usize(offset_of!(IhkCpuInfo, mapping), 8);
    assert_eq_usize(offset_of!(IhkCpuInfo, ikc_mapped), 32);
};
