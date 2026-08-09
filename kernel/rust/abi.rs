#![allow(dead_code)]

use core::ffi::c_void;

pub type CInt = i32;
pub type CLong = i64;
pub type CULong = u64;
pub type SizeT = usize;
pub type SSizeT = isize;
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
pub const PROCFS_NAME_MAX: usize = 768;
pub const SYSFS_PATH_MAX: usize = 1024;
pub const EI_NIDENT: usize = 16;
pub const ELF_PRARGSZ: usize = 80;
pub const ELF_NGREG64: usize = 27;
pub const UTI_MAX_NUMA_DOMAINS: usize = 1024;
pub const UTI_NUMA_SET_WORDS: usize = (UTI_MAX_NUMA_DOMAINS + core::mem::size_of::<u64>() * 8 - 1)
    / (core::mem::size_of::<u64>() * 8);
#[cfg(enable_tofu)]
pub const TOFU_STAG_HASH_SIZE: usize = 4;

#[repr(C)]
pub struct RLimit {
    pub rlim_cur: u64,
    pub rlim_max: u64,
}

#[repr(C)]
pub struct UserDesc {
    pub entry_number: u32,
    pub base_addr: u32,
    pub limit: u32,
    pub flags: u32,
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
pub struct PagerCreateResult {
    pub handle: CULong,
    pub maxprot: CInt,
    pub flags: u32,
    pub size: SizeT,
    pub pgshift: CInt,
    pub path: [i8; PATH_MAX],
}

#[repr(C)]
pub struct PagerMapResult {
    pub handle: CULong,
    pub maxprot: CInt,
    pub padding: [i8; 4],
    pub path: [i8; PATH_MAX],
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
pub struct IkcScdInitParam {
    pub request_page: CULong,
    pub response_page: CULong,
    pub doorbell_page: CULong,
    pub post_page: CULong,
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
pub struct SyscallPost {
    pub v: [CULong; 8],
}

#[repr(C)]
pub struct Coretable {
    pub len: OffT,
    pub addr: CULong,
}

#[repr(C)]
pub struct Elf64Ehdr {
    pub e_ident: [u8; EI_NIDENT],
    pub e_type: u16,
    pub e_machine: u16,
    pub e_version: u32,
    pub e_entry: u64,
    pub e_phoff: u64,
    pub e_shoff: u64,
    pub e_flags: u32,
    pub e_ehsize: u16,
    pub e_phentsize: u16,
    pub e_phnum: u16,
    pub e_shentsize: u16,
    pub e_shnum: u16,
    pub e_shstrndx: u16,
}

#[repr(C)]
pub struct Elf64Phdr {
    pub p_type: u32,
    pub p_flags: u32,
    pub p_offset: u64,
    pub p_vaddr: u64,
    pub p_paddr: u64,
    pub p_filesz: u64,
    pub p_memsz: u64,
    pub p_align: u64,
}

#[repr(C)]
pub struct ElfCoreNote {
    pub namesz: u32,
    pub descsz: u32,
    pub type_: u32,
}

#[repr(C)]
pub struct ElfSiginfo {
    pub si_signo: CInt,
    pub si_code: CInt,
    pub si_errno: CInt,
}

#[repr(C)]
pub struct Prstatus64Timeval {
    pub tv_sec: u64,
    pub tv_usec: u64,
}

#[repr(C)]
pub struct ElfPrstatus64 {
    pub pr_info: ElfSiginfo,
    pub pr_cursig: i16,
    pub pr_sigpend: u64,
    pub pr_sighold: u64,
    pub pr_pid: CInt,
    pub pr_ppid: CInt,
    pub pr_pgrp: CInt,
    pub pr_sid: CInt,
    pub pr_utime: Prstatus64Timeval,
    pub pr_stime: Prstatus64Timeval,
    pub pr_cutime: Prstatus64Timeval,
    pub pr_cstime: Prstatus64Timeval,
    pub pr_reg: [u64; ELF_NGREG64],
    pub pr_fpvalid: CInt,
}

#[repr(C)]
pub struct ElfPrpsinfo64 {
    pub pr_state: i8,
    pub pr_sname: i8,
    pub pr_zomb: i8,
    pub pr_nice: i8,
    pub pr_flag: u64,
    pub pr_uid: u32,
    pub pr_gid: u32,
    pub pr_pid: CInt,
    pub pr_ppid: CInt,
    pub pr_pgrp: CInt,
    pub pr_sid: CInt,
    pub pr_fname: [i8; 16],
    pub pr_psargs: [i8; ELF_PRARGSZ],
}

#[repr(C)]
pub struct Iovec {
    pub iov_base: *mut c_void,
    pub iov_len: SizeT,
}

#[repr(C)]
pub struct ProcfsRead {
    pub pbuf: CULong,
    pub offset: CULong,
    pub count: CInt,
    pub eof: CInt,
    pub ret: CInt,
    pub newcpu: CInt,
    pub readwrite: CInt,
    pub fname: [i8; PROCFS_NAME_MAX],
}

#[repr(C)]
pub struct ProcfsFile {
    pub status: CInt,
    pub mode: CInt,
    pub fname: [i8; PROCFS_NAME_MAX],
}

#[repr(C)]
pub struct SysfsReqCreateParam {
    pub mode: CInt,
    pub error: CInt,
    pub client_ops: CLong,
    pub client_instance: CLong,
    pub path: [i8; SYSFS_PATH_MAX],
    pub padding: CInt,
    pub busy: CInt,
}

#[repr(C)]
pub struct SysfsReqMkdirParam {
    pub error: CInt,
    pub padding: CInt,
    pub handle: CLong,
    pub path: [i8; SYSFS_PATH_MAX],
    pub padding2: CInt,
    pub busy: CInt,
}

#[repr(C)]
pub struct SysfsReqSymlinkParam {
    pub error: CInt,
    pub padding: CInt,
    pub target: CLong,
    pub path: [i8; SYSFS_PATH_MAX],
    pub padding2: CInt,
    pub busy: CInt,
}

#[repr(C)]
pub struct SysfsReqLookupParam {
    pub error: CInt,
    pub padding: CInt,
    pub handle: CLong,
    pub path: [i8; SYSFS_PATH_MAX],
    pub padding2: CInt,
    pub busy: CInt,
}

#[repr(C)]
pub struct SysfsReqUnlinkParam {
    pub flags: CInt,
    pub error: CInt,
    pub path: [i8; SYSFS_PATH_MAX],
    pub padding: CInt,
    pub busy: CInt,
}

#[repr(C)]
pub struct SysfsReqSetupParam {
    pub error: CInt,
    pub padding: CInt,
    pub buf_rpa: CLong,
    pub bufsize: CLong,
    pub padding3: [i8; SYSFS_PATH_MAX],
    pub padding2: CInt,
    pub busy: CInt,
}

pub type SysfsShowFn = Option<
    unsafe extern "C" fn(
        ops: *mut SysfsOps,
        instance: *mut c_void,
        buf: *mut c_void,
        bufsize: SizeT,
    ) -> SSizeT,
>;
pub type SysfsStoreFn = Option<
    unsafe extern "C" fn(
        ops: *mut SysfsOps,
        instance: *mut c_void,
        buf: *mut c_void,
        bufsize: SizeT,
    ) -> SSizeT,
>;
pub type SysfsReleaseFn = Option<unsafe extern "C" fn(ops: *mut SysfsOps, instance: *mut c_void)>;

#[repr(C)]
pub struct SysfsOps {
    pub show: SysfsShowFn,
    pub store: SysfsStoreFn,
    pub release: SysfsReleaseFn,
}

#[repr(C)]
pub struct SysfsHandle {
    pub handle: CLong,
}

#[repr(C)]
pub struct SysfsBitmapParam {
    pub nbits: CInt,
    pub padding: CInt,
    pub ptr: *mut c_void,
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

#[repr(C, packed)]
pub struct X86DescPtr {
    pub size: u16,
    pub address: u64,
}

#[repr(C, packed)]
pub struct Tss64 {
    pub reserved0: u32,
    pub rsp0: CULong,
    pub rsp1: CULong,
    pub rsp2: CULong,
    pub reserved1: u32,
    pub reserved2: u32,
    pub ist: [CULong; 7],
    pub reserved3: u32,
    pub reserved4: u32,
    pub reserved5: u16,
    pub iomap_address: u16,
}

#[repr(C, packed)]
pub struct X86CpuLocalVariables {
    pub processor_id: CULong,
    pub apic_id: CULong,
    pub kernel_stack: CULong,
    pub user_stack: CULong,
    pub gdt_ptr: X86DescPtr,
    pub pad: [u16; 3],
    pub gdt: [u64; 16],
    pub tss: Tss64,
    pub paniced: CULong,
    pub panic_regs: [u64; 21],
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct I387RipRdp {
    pub rip: CULong,
    pub rdp: CULong,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct I387FipFcs {
    pub fip: u32,
    pub fcs: u32,
    pub foo: u32,
    pub fos: u32,
}

#[repr(C)]
pub union I387IpUnion {
    pub rip_rdp: I387RipRdp,
    pub fip_fcs: I387FipFcs,
}

#[repr(C, align(16))]
pub struct I387FxsaveStruct {
    pub cwd: u16,
    pub swd: u16,
    pub twd: u16,
    pub fop: u16,
    pub ip: I387IpUnion,
    pub mxcsr: u32,
    pub mxcsr_mask: u32,
    pub st_space: [u32; 32],
    pub xmm_space: [u32; 64],
    pub padding: [u32; 12],
    pub sw_reserved: [u32; 12],
}

#[repr(C)]
pub struct YmmhStruct {
    pub ymmh_space: [u32; 64],
}

#[repr(C)]
pub struct LwpStruct {
    pub reserved: [u8; 128],
}

#[repr(C, packed)]
#[derive(Clone, Copy)]
pub struct BndReg {
    pub lower_bound: CULong,
    pub upper_bound: CULong,
}

#[repr(C, packed)]
pub struct BndCsr {
    pub bndcfgu: CULong,
    pub bndstatus: CULong,
}

#[repr(C, packed)]
pub struct XsaveHdrStruct {
    pub xstate_bv: CULong,
    pub xcomp_bv: CULong,
    pub reserved: [CULong; 6],
}

#[repr(C, align(64))]
pub struct XsaveStruct {
    pub i387: I387FxsaveStruct,
    pub xsave_hdr: XsaveHdrStruct,
    pub ymmh: YmmhStruct,
    pub lwp: LwpStruct,
    pub bndreg: [BndReg; 4],
    pub bndcsr: BndCsr,
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
pub struct IhkAtomic64 {
    pub counter64: CLong,
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

#[repr(C)]
pub union IhkRwlockInner {
    pub lock: CLong,
    pub parts: IhkRwlockParts,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkRwlockParts {
    pub read: u32,
    pub write: CInt,
}

#[repr(C)]
pub struct IhkRwlock {
    pub lock: IhkRwlockInner,
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
pub struct RUsage {
    pub ru_utime: TimeVal,
    pub ru_stime: TimeVal,
    pub ru_maxrss: CLong,
    pub ru_ixrss: CLong,
    pub ru_idrss: CLong,
    pub ru_isrss: CLong,
    pub ru_minflt: CLong,
    pub ru_majflt: CLong,
    pub ru_nswap: CLong,
    pub ru_inblock: CLong,
    pub ru_oublock: CLong,
    pub ru_msgsnd: CLong,
    pub ru_msgrcv: CLong,
    pub ru_nsignals: CLong,
    pub ru_nvcsw: CLong,
    pub ru_nivcsw: CLong,
}

#[repr(C)]
pub struct SysInfo {
    pub uptime: CLong,
    pub loads: [CULong; 3],
    pub totalram: CULong,
    pub freeram: CULong,
    pub sharedram: CULong,
    pub bufferram: CULong,
    pub totalswap: CULong,
    pub freeswap: CULong,
    pub procs: u16,
    pub padding: [u8; 6],
    pub totalhigh: CULong,
    pub freehigh: CULong,
    pub mem_unit: u32,
    pub tail_padding: u32,
}

#[repr(C)]
pub struct TodData {
    pub do_local: i8,
    pub padding: [i8; 7],
    pub version: IhkAtomic64,
    pub clocks_per_sec: CULong,
    pub origin: TimeSpec,
}

#[repr(C)]
pub struct ITimerVal {
    pub it_interval: TimeVal,
    pub it_value: TimeVal,
}

#[repr(C)]
pub struct ProfileEvent {
    pub cnt: u32,
    pub tsc: u64,
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
pub struct SigAction {
    pub sa_handler: *mut c_void,
    pub sa_flags: CULong,
    pub sa_restorer: *mut c_void,
    pub sa_mask: SigSet,
}

#[repr(C)]
pub struct KSigAction {
    pub sa: SigAction,
}

#[repr(C)]
pub struct SigStack {
    pub ss_sp: *mut c_void,
    pub ss_flags: CInt,
    pub padding: CInt,
    pub ss_size: SizeT,
}

#[repr(C)]
pub union SigVal {
    pub sival_int: CInt,
    pub sival_ptr: *mut c_void,
}

#[repr(C)]
pub struct SigInfoKill {
    pub si_pid: CInt,
    pub si_uid: CInt,
}

#[repr(C)]
pub struct SigInfoTimer {
    pub si_tid: CInt,
    pub si_overrun: CInt,
    pub si_sigval: SigVal,
}

#[repr(C)]
pub struct SigInfoRt {
    pub si_pid: CInt,
    pub si_uid: CInt,
    pub si_sigval: SigVal,
}

#[repr(C)]
pub struct SigInfoChild {
    pub si_pid: CInt,
    pub si_uid: CInt,
    pub si_status: CInt,
    pub padding: CInt,
    pub si_utime: CLong,
    pub si_stime: CLong,
}

#[repr(C)]
pub struct SigInfoFault {
    pub si_addr: *mut c_void,
}

#[repr(C)]
pub struct SigInfoPoll {
    pub si_band: CLong,
    pub si_fd: CInt,
}

#[repr(C)]
pub union SigInfoFields {
    pub pad: [CInt; 28],
    pub kill: core::mem::ManuallyDrop<SigInfoKill>,
    pub timer: core::mem::ManuallyDrop<SigInfoTimer>,
    pub rt: core::mem::ManuallyDrop<SigInfoRt>,
    pub sigchld: core::mem::ManuallyDrop<SigInfoChild>,
    pub sigfault: core::mem::ManuallyDrop<SigInfoFault>,
    pub sigpoll: core::mem::ManuallyDrop<SigInfoPoll>,
}

#[repr(C)]
pub struct SigInfo {
    pub si_signo: CInt,
    pub si_errno: CInt,
    pub si_code: CInt,
    pub padding: CInt,
    pub sifields: SigInfoFields,
}

#[repr(C)]
pub struct SignalfdSigInfo {
    pub ssi_signo: u32,
    pub ssi_errno: CInt,
    pub ssi_code: CInt,
    pub ssi_pid: u32,
    pub ssi_uid: u32,
    pub ssi_fd: CInt,
    pub ssi_tid: u32,
    pub ssi_band: u32,
    pub ssi_overrun: u32,
    pub ssi_trapno: u32,
    pub ssi_status: CInt,
    pub ssi_int: CInt,
    pub ssi_ptr: CULong,
    pub ssi_utime: CULong,
    pub ssi_stime: CULong,
    pub ssi_addr: CULong,
    pub ssi_addr_lsb: u16,
    pub pad: [u8; 46],
}

#[repr(C)]
pub struct SchedParam {
    pub sched_priority: CInt,
}

#[repr(C)]
pub struct UserFpRegsStruct {
    pub cwd: u16,
    pub swd: u16,
    pub ftw: u16,
    pub fop: u16,
    pub rip: CULong,
    pub rdp: CULong,
    pub mxcsr: u32,
    pub mxcr_mask: u32,
    pub st_space: [u32; 32],
    pub xmm_space: [u32; 64],
    pub padding: [u32; 24],
}

#[repr(C)]
pub struct UserRegsStruct {
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
    pub eflags: CULong,
    pub rsp: CULong,
    pub ss: CULong,
    pub fs_base: CULong,
    pub gs_base: CULong,
    pub ds: CULong,
    pub es: CULong,
    pub fs: CULong,
    pub gs: CULong,
}

#[repr(C)]
pub struct User {
    pub regs: UserRegsStruct,
    pub u_fpvalid: CInt,
    pub padding: CInt,
    pub i387: UserFpRegsStruct,
    pub u_tsize: CULong,
    pub u_dsize: CULong,
    pub u_ssize: CULong,
    pub start_code: CULong,
    pub start_stack: CULong,
    pub signal: CLong,
    pub reserved: CInt,
    pub padding2: CInt,
    pub u_ar0: *mut UserRegsStruct,
    pub u_fpstate: *mut UserFpRegsStruct,
    pub magic: CULong,
    pub u_comm: [i8; 32],
    pub u_debugreg: [CULong; 8],
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
pub struct FutexHashBucket {
    pub lock: IhkSpinlock,
    pub padding: CInt,
    pub chain: PlistHead,
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
pub struct CpuMapping {
    pub cpu_number: CInt,
    pub hw_id: CInt,
}

#[repr(C)]
pub struct GetCpuMappingReq {
    pub busy: CInt,
    pub error: CInt,
    pub buf_rpa: CLong,
    pub buf_elems: CInt,
    pub padding: CInt,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct PerfCtrlCounter {
    pub target_cntr: u32,
    pub padding: u32,
    pub config: CULong,
    pub read_value: CULong,
    pub flags: u32,
    pub tail_padding: u32,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct PerfCtrlMask {
    pub target_cntr_mask: CULong,
}

#[repr(C)]
pub union PerfCtrlBody {
    pub counter: PerfCtrlCounter,
    pub mask: PerfCtrlMask,
}

#[repr(C)]
pub struct PerfCtrlDesc {
    pub ctrl_type: CInt,
    pub err: CInt,
    pub body: PerfCtrlBody,
}

#[repr(C)]
pub struct UtiAttr {
    pub numa_set: [u64; UTI_NUMA_SET_WORDS],
    pub flags: u64,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct UtiCtxRefill {
    pub uti_refill_tid: CInt,
}

#[repr(C)]
pub union UtiCtx {
    pub ctx: [i8; 4096],
    pub refill: UtiCtxRefill,
}

#[repr(C)]
pub struct MovePagesSmpReq {
    pub count: CULong,
    pub user_virt_addr: *mut *const c_void,
    pub user_status: *mut CInt,
    pub user_nodes: *const CInt,
    pub virt_addr: *mut *mut c_void,
    pub status: *mut CInt,
    pub ptep: *mut *mut c_void,
    pub nodes: *mut CInt,
    pub nodes_ready: CInt,
    pub nr_pages: *mut CInt,
    pub dst_phys: *mut CULong,
    pub proc: *mut c_void,
    pub phase_done: IhkAtomic,
    pub phase_ret: CInt,
}

#[repr(C)]
pub struct Kref {
    pub refcount: IhkAtomic,
}

#[repr(C)]
pub struct RbAugmentCallbacks {
    pub propagate: *mut c_void,
    pub copy: *mut c_void,
    pub rotate: *mut c_void,
}

#[repr(C)]
#[derive(Clone, Copy)]
pub struct FtraceBranchCounts {
    pub correct: CULong,
    pub incorrect: CULong,
}

#[repr(C)]
pub union FtraceBranchUnion {
    pub counts: FtraceBranchCounts,
    pub miss_hit: [CULong; 2],
}

#[repr(C)]
pub struct FtraceBranchData {
    pub func: *const i8,
    pub file: *const i8,
    pub line: u32,
    pub padding: u32,
    pub data: FtraceBranchUnion,
}

#[repr(C)]
pub struct FtraceLikelyData {
    pub data: FtraceBranchData,
    pub constant: CULong,
}

#[repr(C)]
pub struct MemobjOps {
    pub free: *mut c_void,
    pub get_page: *mut c_void,
    pub copy_page: *mut c_void,
    pub flush_page: *mut c_void,
    pub invalidate_page: *mut c_void,
    pub lookup_page: *mut c_void,
    pub update_page: *mut c_void,
}

#[repr(C)]
pub struct Memobj {
    pub ops: *mut MemobjOps,
    pub flags: u32,
    pub status: u32,
    pub size: SizeT,
    pub refcnt: IhkAtomic,
    pub padding: CInt,
    pub pages: *mut *mut c_void,
    pub nr_pages: CInt,
    pub padding2: CInt,
    pub path: *mut i8,
}

#[repr(C)]
pub struct IpcPerm {
    pub key: CInt,
    pub uid: u32,
    pub gid: u32,
    pub cuid: u32,
    pub cgid: u32,
    pub mode: u16,
    pub padding: [u8; 2],
    pub seq: u16,
    pub padding2: [u8; 22],
}

#[repr(C)]
pub struct ShmidDs {
    pub shm_perm: IpcPerm,
    pub shm_segsz: SizeT,
    pub shm_atime: CLong,
    pub shm_dtime: CLong,
    pub shm_ctime: CLong,
    pub shm_cpid: CInt,
    pub shm_lpid: CInt,
    pub shm_nattch: u64,
    pub padding: [u8; 12],
    pub init_pgshift: CInt,
}

#[repr(C)]
pub struct ShmObj {
    pub memobj: Memobj,
    pub index: CInt,
    pub pgshift: CInt,
    pub real_segsz: SizeT,
    pub user: *mut ShmLockUser,
    pub ds: ShmidDs,
    pub page_list: AbiListHead,
    pub page_list_lock: IhkSpinlock,
    pub padding: CInt,
    pub chain: AbiListHead,
}

#[repr(C)]
pub struct ShmInfoLimit {
    pub shmmax: u64,
    pub shmmin: u64,
    pub shmmni: u64,
    pub shmseg: u64,
    pub shmall: u64,
    pub padding: [u8; 32],
}

#[repr(C)]
pub struct ShmInfo {
    pub used_ids: i32,
    pub padding: [u8; 4],
    pub shm_tot: u64,
    pub shm_rss: u64,
    pub shm_swp: u64,
    pub swap_attempts: u64,
    pub swap_successes: u64,
}

#[repr(C)]
pub struct ShmLockUser {
    pub ruid: u32,
    pub padding: CInt,
    pub locked: SizeT,
    pub chain: AbiListHead,
}

pub type XpmemSegid = CLong;
pub type XpmemApid = CLong;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct XpmemId {
    pub tgid: CInt,
    pub uniq: u32,
}

#[repr(C)]
pub union XpmemIdValue {
    pub xpmem_id: XpmemId,
    pub segid: XpmemSegid,
    pub apid: XpmemApid,
}

#[repr(C, align(64))]
pub struct XpmemHashlist {
    pub lock: McsRwlockLock,
    pub list: AbiListHead,
}

#[repr(C, align(64))]
pub struct XpmemThreadGroupPrefix {
    pub lock: IhkSpinlock,
    pub tgid: CInt,
    pub uid: u32,
    pub gid: u32,
    pub flags: CInt,
    pub uniq_segid: IhkAtomic,
    pub uniq_apid: IhkAtomic,
    pub padding: [u8; 36],
    pub seg_list_lock: McsRwlockLock,
    pub seg_list: AbiListHead,
    pub refcnt: IhkAtomic,
    pub n_pinned: IhkAtomic,
    pub tg_hashlist: AbiListHead,
    pub group_leader: *mut Thread,
    pub vm: *mut ProcessVm,
}

#[repr(C)]
pub struct XpmemSegment {
    pub lock: IhkSpinlock,
    pub padding: CInt,
    pub segid: XpmemSegid,
    pub vaddr: CULong,
    pub size: SizeT,
    pub permit_type: CInt,
    pub padding2: CInt,
    pub permit_value: *mut c_void,
    pub flags: CInt,
    pub refcnt: IhkAtomic,
    pub tg: *mut XpmemThreadGroupPrefix,
    pub ap_list: AbiListHead,
    pub seg_list: AbiListHead,
}

#[repr(C)]
pub struct XpmemAccessPermit {
    pub lock: IhkSpinlock,
    pub padding: CInt,
    pub apid: XpmemApid,
    pub mode: CInt,
    pub flags: CInt,
    pub refcnt: IhkAtomic,
    pub padding2: CInt,
    pub seg: *mut XpmemSegment,
    pub tg: *mut XpmemThreadGroupPrefix,
    pub att_list: AbiListHead,
    pub ap_list: AbiListHead,
    pub ap_hashlist: AbiListHead,
}

#[repr(C, align(64))]
pub struct XpmemPartitionPrefix {
    pub n_opened: IhkAtomic,
    pub padding: [u8; 60],
}

#[repr(C)]
pub struct XpmemPerm {
    pub uid: u32,
    pub gid: u32,
    pub mode: CULong,
}

#[repr(C)]
pub struct XpmemAttachment {
    pub at_lock: IhkRwSpinlock,
    pub padding: CInt,
    pub vaddr: CULong,
    pub at_vaddr: CULong,
    pub at_size: SizeT,
    pub at_vmr: *mut VmRange,
    pub flags: CInt,
    pub refcnt: IhkAtomic,
    pub ap: *mut XpmemAccessPermit,
    pub att_list: AbiListHead,
    pub vm: *mut ProcessVm,
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
#[derive(Clone, Copy)]
pub struct RusagePercpu {
    pub user_tsc: CULong,
    pub system_tsc: CULong,
}

#[repr(C)]
pub struct IhkMcMemoryArea {
    pub start: CULong,
    pub size: CULong,
    pub type_: CInt,
}

#[repr(C)]
pub struct IhkMcMemoryNode {
    pub node: CInt,
    pub nareas: CInt,
    pub areas: *mut IhkMcMemoryArea,
}

#[repr(C)]
pub struct IhkMcPaOps {
    pub alloc_page:
        Option<unsafe extern "C" fn(CInt, CInt, CInt, CInt, CInt, CULong) -> *mut c_void>,
    pub free_page: Option<unsafe extern "C" fn(*mut c_void, CInt, CInt)>,
    pub alloc: Option<unsafe extern "C" fn(CInt, CInt) -> *mut c_void>,
    pub free: Option<unsafe extern "C" fn(*mut c_void)>,
}

#[repr(C, align(64))]
pub struct TlbFlushEntry {
    pub vm: *mut ProcessVm,
    pub addr: *mut CULong,
    pub nr_addr: CInt,
    pub pending: IhkAtomic,
    pub lock: IhkSpinlock,
}

#[repr(C)]
pub struct IhkMcPageCacheHeader {
    pub next: *mut IhkMcPageCacheHeader,
}

#[repr(C)]
pub struct KmallocCacheHeader {
    pub next: *mut KmallocCacheHeader,
}

#[repr(C)]
pub union KmallocHeaderLink {
    pub list: core::mem::ManuallyDrop<AbiListHead>,
    pub cache: *mut KmallocCacheHeader,
}

#[repr(C)]
pub struct KmallocHeader {
    pub front_magic: u32,
    pub cpu_id: CInt,
    pub link: KmallocHeaderLink,
    pub size: CInt,
    pub end_magic: u32,
}

#[repr(C)]
pub struct SmpFuncCallData {
    pub nr_cpus: CInt,
    pub cpus_left: IhkAtomic,
    pub func: Option<unsafe extern "C" fn(CInt, CInt, *mut c_void) -> CInt>,
    pub arg: *mut c_void,
}

#[repr(C)]
pub struct SmpFuncCallRequest {
    pub sfcd: *mut SmpFuncCallData,
    pub cpu_index: CInt,
    pub ret: CInt,
    pub list: AbiListHead,
}

#[repr(C)]
pub struct Backlog {
    pub list: AbiListHead,
    pub func: Option<unsafe extern "C" fn(*mut c_void) -> CInt>,
    pub arg: *mut c_void,
}

#[repr(C, align(64))]
pub struct CpuLocalVar {
    pub free_list: AbiListHead,
    pub remote_free_list: AbiListHead,
    pub remote_free_list_lock: IhkSpinlock,
    pub idle: Thread,
    pub idle_proc: Process,
    pub idle_vm: ProcessVm,
    pub idle_asp: AddressSpace,
    pub runq_lock: IhkSpinlock,
    pub runq_irqstate: CULong,
    pub current: *mut Thread,
    pub kernel_mode_pf_regs: *mut c_void,
    pub prevpid: CInt,
    pub runq: AbiListHead,
    pub runq_len: SizeT,
    pub runq_reserved: SizeT,
    pub ikc2linux: *mut c_void,
    pub resource_set: *mut ResourceSet,
    pub status: CInt,
    pub fs: CInt,
    pub pending_free_pages: AbiListHead,
    pub flags: u32,
    pub migq_lock: IhkSpinlock,
    pub migq: AbiListHead,
    pub in_interrupt: CInt,
    pub in_page_fault: CInt,
    pub no_preempt: IhkAtomic,
    pub timer_enabled: CInt,
    pub nr_ctx_switches: CULong,
    pub kmalloc_initialized: CInt,
    pub monitor: *mut IhkOsCpuMonitor,
    pub rusage: *mut RusagePercpu,
    pub smp_func_req_lock: IhkSpinlock,
    pub smp_func_req_list: AbiListHead,
    pub on_fork_vm: *mut ProcessVm,
    pub backlog_lock: IhkSpinlock,
    pub backlog_list: AbiListHead,
    pub uti_futex_resp: *mut c_void,
    #[cfg(enable_per_cpu_alloc_cache)]
    pub free_chunks: AbiRbRoot,
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
    assert_eq_usize(size_of::<UserDesc>(), 16);
    assert_eq_usize(offset_of!(UserDesc, base_addr), 4);
    assert_eq_usize(offset_of!(UserDesc, limit), 8);
    assert_eq_usize(size_of::<ProgramImageSection>(), 56);
    assert_eq_usize(size_of::<PagerCreateResult>(), 4128);
    assert_eq_usize(offset_of!(PagerCreateResult, maxprot), 8);
    assert_eq_usize(offset_of!(PagerCreateResult, flags), 12);
    assert_eq_usize(offset_of!(PagerCreateResult, size), 16);
    assert_eq_usize(offset_of!(PagerCreateResult, pgshift), 24);
    assert_eq_usize(offset_of!(PagerCreateResult, path), 28);
    assert_eq_usize(size_of::<PagerMapResult>(), 4112);
    assert_eq_usize(offset_of!(PagerMapResult, maxprot), 8);
    assert_eq_usize(offset_of!(PagerMapResult, padding), 12);
    assert_eq_usize(offset_of!(PagerMapResult, path), 16);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<ProgramLoadDesc>(), 776);
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<ProgramLoadDesc>(), 784);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(ProgramLoadDesc, profile), 768);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(ProgramLoadDesc, profile), 776);

    assert_eq_usize(size_of::<IkcScdInitParam>(), 32);
    assert_eq_usize(offset_of!(IkcScdInitParam, response_page), 8);
    assert_eq_usize(offset_of!(IkcScdInitParam, post_page), 24);
    assert_eq_usize(size_of::<SyscallRequest>(), 72);
    assert_eq_usize(offset_of!(SyscallRequest, args), 24);
    assert_eq_usize(size_of::<SyscallResponse>(), 48);
    assert_eq_usize(size_of::<SyscallPost>(), 64);
    assert_eq_usize(size_of::<Coretable>(), 16);
    assert_eq_usize(offset_of!(Coretable, addr), 8);
    assert_eq_usize(size_of::<Elf64Ehdr>(), 64);
    assert_eq_usize(offset_of!(Elf64Ehdr, e_phoff), 32);
    assert_eq_usize(offset_of!(Elf64Ehdr, e_ehsize), 52);
    assert_eq_usize(size_of::<Elf64Phdr>(), 56);
    assert_eq_usize(offset_of!(Elf64Phdr, p_offset), 8);
    assert_eq_usize(offset_of!(Elf64Phdr, p_filesz), 32);
    assert_eq_usize(size_of::<ElfCoreNote>(), 12);
    assert_eq_usize(offset_of!(ElfCoreNote, type_), 8);
    assert_eq_usize(size_of::<ElfSiginfo>(), 12);
    assert_eq_usize(offset_of!(ElfSiginfo, si_code), 4);
    assert_eq_usize(offset_of!(ElfSiginfo, si_errno), 8);
    assert_eq_usize(size_of::<Prstatus64Timeval>(), 16);
    assert_eq_usize(size_of::<ElfPrstatus64>(), 336);
    assert_eq_usize(offset_of!(ElfPrstatus64, pr_sigpend), 16);
    assert_eq_usize(offset_of!(ElfPrstatus64, pr_utime), 48);
    assert_eq_usize(offset_of!(ElfPrstatus64, pr_reg), 112);
    assert_eq_usize(offset_of!(ElfPrstatus64, pr_fpvalid), 328);
    assert_eq_usize(size_of::<ElfPrpsinfo64>(), 136);
    assert_eq_usize(offset_of!(ElfPrpsinfo64, pr_flag), 8);
    assert_eq_usize(offset_of!(ElfPrpsinfo64, pr_pid), 24);
    assert_eq_usize(offset_of!(ElfPrpsinfo64, pr_fname), 40);
    assert_eq_usize(offset_of!(ElfPrpsinfo64, pr_psargs), 56);
    assert_eq_usize(size_of::<Iovec>(), 16);
    assert_eq_usize(offset_of!(Iovec, iov_len), 8);
    assert_eq_usize(size_of::<ProcfsRead>(), 808);
    assert_eq_usize(offset_of!(ProcfsRead, offset), 8);
    assert_eq_usize(offset_of!(ProcfsRead, count), 16);
    assert_eq_usize(offset_of!(ProcfsRead, fname), 36);
    assert_eq_usize(size_of::<ProcfsFile>(), 776);
    assert_eq_usize(offset_of!(ProcfsFile, fname), 8);
    assert_eq_usize(size_of::<SysfsReqCreateParam>(), 1056);
    assert_eq_usize(offset_of!(SysfsReqCreateParam, client_ops), 8);
    assert_eq_usize(offset_of!(SysfsReqCreateParam, path), 24);
    assert_eq_usize(offset_of!(SysfsReqCreateParam, busy), 1052);
    assert_eq_usize(size_of::<SysfsReqMkdirParam>(), 1048);
    assert_eq_usize(offset_of!(SysfsReqMkdirParam, handle), 8);
    assert_eq_usize(offset_of!(SysfsReqMkdirParam, path), 16);
    assert_eq_usize(offset_of!(SysfsReqMkdirParam, busy), 1044);
    assert_eq_usize(size_of::<SysfsReqSymlinkParam>(), 1048);
    assert_eq_usize(offset_of!(SysfsReqSymlinkParam, target), 8);
    assert_eq_usize(offset_of!(SysfsReqSymlinkParam, path), 16);
    assert_eq_usize(offset_of!(SysfsReqSymlinkParam, busy), 1044);
    assert_eq_usize(size_of::<SysfsReqLookupParam>(), 1048);
    assert_eq_usize(offset_of!(SysfsReqLookupParam, handle), 8);
    assert_eq_usize(offset_of!(SysfsReqLookupParam, path), 16);
    assert_eq_usize(offset_of!(SysfsReqLookupParam, busy), 1044);
    assert_eq_usize(size_of::<SysfsReqUnlinkParam>(), 1040);
    assert_eq_usize(offset_of!(SysfsReqUnlinkParam, path), 8);
    assert_eq_usize(offset_of!(SysfsReqUnlinkParam, busy), 1036);
    assert_eq_usize(size_of::<SysfsReqSetupParam>(), 1056);
    assert_eq_usize(offset_of!(SysfsReqSetupParam, buf_rpa), 8);
    assert_eq_usize(offset_of!(SysfsReqSetupParam, padding3), 24);
    assert_eq_usize(offset_of!(SysfsReqSetupParam, busy), 1052);
    assert_eq_usize(size_of::<SysfsOps>(), 24);
    assert_eq_usize(offset_of!(SysfsOps, show), 0);
    assert_eq_usize(offset_of!(SysfsOps, store), 8);
    assert_eq_usize(offset_of!(SysfsOps, release), 16);
    assert_eq_usize(size_of::<SysfsHandle>(), 8);
    assert_eq_usize(size_of::<SysfsBitmapParam>(), 16);
    assert_eq_usize(offset_of!(SysfsBitmapParam, ptr), 8);
    assert_eq_usize(size_of::<IhkIkcPacketHeader>(), 8);
    assert_eq_usize(size_of::<IkcScdPacketTraditional>(), 104);
    assert_eq_usize(size_of::<IkcScdPacket>(), 128);
    assert_eq_usize(align_of::<IkcScdPacket>(), 8);

    assert_eq_usize(size_of::<X86BasicRegs>(), 168);
    assert_eq_usize(size_of::<X86Sregs>(), 48);
    assert_eq_usize(size_of::<X86UserContext>(), 224);
    assert_eq_usize(offset_of!(X86UserContext, gpr), 56);
    assert_eq_usize(size_of::<X86DescPtr>(), 10);
    assert_eq_usize(align_of::<X86DescPtr>(), 1);
    assert_eq_usize(offset_of!(X86DescPtr, address), 2);
    assert_eq_usize(size_of::<Tss64>(), 104);
    assert_eq_usize(align_of::<Tss64>(), 1);
    assert_eq_usize(offset_of!(Tss64, rsp0), 4);
    assert_eq_usize(offset_of!(Tss64, ist), 36);
    assert_eq_usize(offset_of!(Tss64, iomap_address), 102);
    assert_eq_usize(size_of::<X86CpuLocalVariables>(), 456);
    assert_eq_usize(align_of::<X86CpuLocalVariables>(), 1);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, kernel_stack), 16);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, gdt_ptr), 32);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, gdt), 48);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, tss), 176);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, paniced), 280);
    assert_eq_usize(offset_of!(X86CpuLocalVariables, panic_regs), 288);
    assert_eq_usize(size_of::<I387FxsaveStruct>(), 512);
    assert_eq_usize(align_of::<I387FxsaveStruct>(), 16);
    assert_eq_usize(offset_of!(I387FxsaveStruct, ip), 8);
    assert_eq_usize(offset_of!(I387FxsaveStruct, mxcsr), 24);
    assert_eq_usize(offset_of!(I387FxsaveStruct, st_space), 32);
    assert_eq_usize(offset_of!(I387FxsaveStruct, xmm_space), 160);
    assert_eq_usize(offset_of!(I387FxsaveStruct, sw_reserved), 464);
    assert_eq_usize(size_of::<YmmhStruct>(), 256);
    assert_eq_usize(size_of::<LwpStruct>(), 128);
    assert_eq_usize(size_of::<BndReg>(), 16);
    assert_eq_usize(align_of::<BndReg>(), 1);
    assert_eq_usize(offset_of!(BndReg, upper_bound), 8);
    assert_eq_usize(size_of::<BndCsr>(), 16);
    assert_eq_usize(offset_of!(BndCsr, bndstatus), 8);
    assert_eq_usize(size_of::<XsaveHdrStruct>(), 64);
    assert_eq_usize(offset_of!(XsaveHdrStruct, xcomp_bv), 8);
    assert_eq_usize(size_of::<XsaveStruct>(), 1088);
    assert_eq_usize(align_of::<XsaveStruct>(), 64);
    assert_eq_usize(offset_of!(XsaveStruct, xsave_hdr), 512);
    assert_eq_usize(offset_of!(XsaveStruct, ymmh), 576);
    assert_eq_usize(offset_of!(XsaveStruct, lwp), 832);
    assert_eq_usize(offset_of!(XsaveStruct, bndreg), 960);
    assert_eq_usize(offset_of!(XsaveStruct, bndcsr), 1024);

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
    assert_eq_usize(size_of::<IhkAtomic64>(), 8);
    assert_eq_usize(align_of::<IhkAtomic64>(), 8);
    assert_eq_usize(offset_of!(IhkAtomic64, counter64), 0);
    assert_eq_usize(size_of::<IhkSpinlock>(), 4);
    assert_eq_usize(align_of::<IhkSpinlock>(), 4);
    assert_eq_usize(offset_of!(IhkSpinlock, head_tail), 0);
    assert_eq_usize(size_of::<IhkRwSpinlock>(), 4);
    assert_eq_usize(align_of::<IhkRwSpinlock>(), 4);
    assert_eq_usize(offset_of!(IhkRwSpinlock, v), 0);
    assert_eq_usize(size_of::<IhkRwlock>(), 8);
    assert_eq_usize(align_of::<IhkRwlock>(), 8);
    assert_eq_usize(size_of::<McsRwlockLock>(), 64);
    assert_eq_usize(align_of::<McsRwlockLock>(), 64);
    assert_eq_usize(offset_of!(McsRwlockLock, slock), 0);
    assert_eq_usize(size_of::<CpuSet>(), 128);
    assert_eq_usize(align_of::<CpuSet>(), 8);
    assert_eq_usize(size_of::<TimeSpec>(), 16);
    assert_eq_usize(size_of::<TimeVal>(), 16);
    assert_eq_usize(offset_of!(TimeVal, tv_usec), 8);
    assert_eq_usize(size_of::<RUsage>(), 144);
    assert_eq_usize(offset_of!(RUsage, ru_stime), 16);
    assert_eq_usize(offset_of!(RUsage, ru_maxrss), 32);
    assert_eq_usize(offset_of!(RUsage, ru_nivcsw), 136);
    assert_eq_usize(size_of::<SysInfo>(), 112);
    assert_eq_usize(offset_of!(SysInfo, loads), 8);
    assert_eq_usize(offset_of!(SysInfo, procs), 80);
    assert_eq_usize(offset_of!(SysInfo, totalhigh), 88);
    assert_eq_usize(offset_of!(SysInfo, mem_unit), 104);
    assert_eq_usize(size_of::<TodData>(), 40);
    assert_eq_usize(offset_of!(TodData, version), 8);
    assert_eq_usize(offset_of!(TodData, clocks_per_sec), 16);
    assert_eq_usize(offset_of!(TodData, origin), 24);
    assert_eq_usize(size_of::<ITimerVal>(), 32);
    assert_eq_usize(offset_of!(ITimerVal, it_value), 16);
    assert_eq_usize(size_of::<ProfileEvent>(), 16);
    assert_eq_usize(offset_of!(ProfileEvent, tsc), 8);
    assert_eq_usize(size_of::<Waitq>(), 24);
    assert_eq_usize(offset_of!(Waitq, waitq), 8);
    assert_eq_usize(size_of::<Timer>(), 56);
    assert_eq_usize(offset_of!(Timer, processes), 8);
    assert_eq_usize(offset_of!(Timer, list), 32);
    assert_eq_usize(offset_of!(Timer, thread), 48);
    assert_eq_usize(size_of::<X86KernelContext>(), 88);
    assert_eq_usize(offset_of!(X86KernelContext, rflags), 72);
    assert_eq_usize(offset_of!(X86KernelContext, rsp0), 80);
    assert_eq_usize(size_of::<SigSet>(), 8);
    assert_eq_usize(size_of::<SigAction>(), 32);
    assert_eq_usize(offset_of!(SigAction, sa_flags), 8);
    assert_eq_usize(offset_of!(SigAction, sa_restorer), 16);
    assert_eq_usize(offset_of!(SigAction, sa_mask), 24);
    assert_eq_usize(size_of::<KSigAction>(), 32);
    assert_eq_usize(offset_of!(KSigAction, sa), 0);
    assert_eq_usize(size_of::<SigStack>(), 24);
    assert_eq_usize(offset_of!(SigStack, ss_flags), 8);
    assert_eq_usize(offset_of!(SigStack, ss_size), 16);
    assert_eq_usize(size_of::<SigVal>(), 8);
    assert_eq_usize(size_of::<SigInfoFields>(), 112);
    assert_eq_usize(size_of::<SigInfo>(), 128);
    assert_eq_usize(offset_of!(SigInfo, si_errno), 4);
    assert_eq_usize(offset_of!(SigInfo, si_code), 8);
    assert_eq_usize(offset_of!(SigInfo, sifields), 16);
    assert_eq_usize(size_of::<SignalfdSigInfo>(), 128);
    assert_eq_usize(offset_of!(SignalfdSigInfo, ssi_ptr), 48);
    assert_eq_usize(offset_of!(SignalfdSigInfo, ssi_addr_lsb), 80);
    assert_eq_usize(size_of::<UserFpRegsStruct>(), 512);
    assert_eq_usize(offset_of!(UserFpRegsStruct, rip), 8);
    assert_eq_usize(offset_of!(UserFpRegsStruct, st_space), 32);
    assert_eq_usize(offset_of!(UserFpRegsStruct, xmm_space), 160);
    assert_eq_usize(size_of::<UserRegsStruct>(), 216);
    assert_eq_usize(offset_of!(UserRegsStruct, rip), 128);
    assert_eq_usize(offset_of!(UserRegsStruct, fs_base), 168);
    assert_eq_usize(size_of::<User>(), 912);
    assert_eq_usize(offset_of!(User, i387), 224);
    assert_eq_usize(offset_of!(User, u_ar0), 792);
    assert_eq_usize(offset_of!(User, u_debugreg), 848);
    assert_eq_usize(size_of::<McsLockNode>(), 64);
    assert_eq_usize(align_of::<McsLockNode>(), 64);
    assert_eq_usize(offset_of!(McsLockNode, next), 8);
    assert_eq_usize(offset_of!(McsLockNode, irqsave), 16);
    assert_eq_usize(size_of::<PlistHead>(), 32);
    assert_eq_usize(size_of::<PlistNode>(), 40);
    assert_eq_usize(size_of::<FutexHashBucket>(), 40);
    assert_eq_usize(offset_of!(FutexHashBucket, chain), 8);
    assert_eq_usize(size_of::<FutexKey>(), 24);
    assert_eq_usize(size_of::<FutexQ>(), 232);
    assert_eq_usize(offset_of!(FutexQ, key), 56);
    assert_eq_usize(offset_of!(FutexQ, bitset), 88);
    assert_eq_usize(offset_of!(FutexQ, th_spin_sleep), 112);
    assert_eq_usize(offset_of!(FutexQ, intr_id), 168);
    assert_eq_usize(offset_of!(FutexQ, th_spin_sleep_pa), 176);

    assert_eq_usize(size_of::<CpuMapping>(), 8);
    assert_eq_usize(offset_of!(CpuMapping, hw_id), 4);
    assert_eq_usize(size_of::<GetCpuMappingReq>(), 24);
    assert_eq_usize(offset_of!(GetCpuMappingReq, buf_rpa), 8);
    assert_eq_usize(offset_of!(GetCpuMappingReq, buf_elems), 16);
    assert_eq_usize(size_of::<PerfCtrlCounter>(), 32);
    assert_eq_usize(offset_of!(PerfCtrlCounter, config), 8);
    assert_eq_usize(offset_of!(PerfCtrlCounter, read_value), 16);
    assert_eq_usize(offset_of!(PerfCtrlCounter, flags), 24);
    assert_eq_usize(size_of::<PerfCtrlBody>(), 32);
    assert_eq_usize(size_of::<PerfCtrlDesc>(), 40);
    assert_eq_usize(offset_of!(PerfCtrlDesc, body), 8);
    assert_eq_usize(size_of::<UtiAttr>(), 136);
    assert_eq_usize(offset_of!(UtiAttr, flags), 128);
    assert_eq_usize(size_of::<UtiCtx>(), 4096);
    assert_eq_usize(size_of::<MovePagesSmpReq>(), 104);
    assert_eq_usize(offset_of!(MovePagesSmpReq, user_virt_addr), 8);
    assert_eq_usize(offset_of!(MovePagesSmpReq, ptep), 48);
    assert_eq_usize(offset_of!(MovePagesSmpReq, nodes_ready), 64);
    assert_eq_usize(offset_of!(MovePagesSmpReq, nr_pages), 72);
    assert_eq_usize(offset_of!(MovePagesSmpReq, proc), 88);
    assert_eq_usize(offset_of!(MovePagesSmpReq, phase_done), 96);
    assert_eq_usize(offset_of!(MovePagesSmpReq, phase_ret), 100);

    assert_eq_usize(size_of::<Kref>(), 4);
    assert_eq_usize(size_of::<RbAugmentCallbacks>(), 24);
    assert_eq_usize(offset_of!(RbAugmentCallbacks, copy), 8);
    assert_eq_usize(offset_of!(RbAugmentCallbacks, rotate), 16);
    assert_eq_usize(size_of::<FtraceBranchData>(), 40);
    assert_eq_usize(offset_of!(FtraceBranchData, line), 16);
    assert_eq_usize(offset_of!(FtraceBranchData, data), 24);
    assert_eq_usize(size_of::<FtraceLikelyData>(), 48);
    assert_eq_usize(offset_of!(FtraceLikelyData, constant), 40);
    assert_eq_usize(size_of::<MemobjOps>(), 56);
    assert_eq_usize(offset_of!(MemobjOps, get_page), 8);
    assert_eq_usize(offset_of!(MemobjOps, update_page), 48);
    assert_eq_usize(size_of::<Memobj>(), 56);
    assert_eq_usize(offset_of!(Memobj, flags), 8);
    assert_eq_usize(offset_of!(Memobj, refcnt), 24);
    assert_eq_usize(offset_of!(Memobj, pages), 32);
    assert_eq_usize(offset_of!(Memobj, path), 48);
    assert_eq_usize(size_of::<IpcPerm>(), 48);
    assert_eq_usize(offset_of!(IpcPerm, seq), 24);
    assert_eq_usize(size_of::<ShmidDs>(), 112);
    assert_eq_usize(offset_of!(ShmidDs, init_pgshift), 108);
    assert_eq_usize(size_of::<ShmObj>(), 232);
    assert_eq_usize(offset_of!(ShmObj, index), 56);
    assert_eq_usize(offset_of!(ShmObj, ds), 80);
    assert_eq_usize(offset_of!(ShmObj, chain), 216);
    assert_eq_usize(size_of::<ShmInfoLimit>(), 72);
    assert_eq_usize(offset_of!(ShmInfoLimit, padding), 40);
    assert_eq_usize(size_of::<ShmInfo>(), 48);
    assert_eq_usize(offset_of!(ShmInfo, shm_tot), 8);
    assert_eq_usize(offset_of!(ShmInfo, swap_successes), 40);
    assert_eq_usize(size_of::<ShmLockUser>(), 32);
    assert_eq_usize(offset_of!(ShmLockUser, locked), 8);
    assert_eq_usize(offset_of!(ShmLockUser, chain), 16);
    assert_eq_usize(size_of::<XpmemId>(), 8);
    assert_eq_usize(size_of::<XpmemIdValue>(), 8);
    assert_eq_usize(align_of::<XpmemIdValue>(), 8);
    assert_eq_usize(size_of::<XpmemHashlist>(), 128);
    assert_eq_usize(align_of::<XpmemHashlist>(), 64);
    assert_eq_usize(offset_of!(XpmemHashlist, list), 64);
    assert_eq_usize(size_of::<XpmemThreadGroupPrefix>(), 192);
    assert_eq_usize(align_of::<XpmemThreadGroupPrefix>(), 64);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, seg_list_lock), 64);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, seg_list), 128);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, refcnt), 144);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, tg_hashlist), 152);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, group_leader), 168);
    assert_eq_usize(offset_of!(XpmemThreadGroupPrefix, vm), 176);
    assert_eq_usize(size_of::<XpmemSegment>(), 96);
    assert_eq_usize(offset_of!(XpmemSegment, segid), 8);
    assert_eq_usize(offset_of!(XpmemSegment, permit_value), 40);
    assert_eq_usize(offset_of!(XpmemSegment, tg), 56);
    assert_eq_usize(offset_of!(XpmemSegment, seg_list), 80);
    assert_eq_usize(size_of::<XpmemAccessPermit>(), 96);
    assert_eq_usize(offset_of!(XpmemAccessPermit, apid), 8);
    assert_eq_usize(offset_of!(XpmemAccessPermit, seg), 32);
    assert_eq_usize(offset_of!(XpmemAccessPermit, att_list), 48);
    assert_eq_usize(offset_of!(XpmemAccessPermit, ap_hashlist), 80);
    assert_eq_usize(size_of::<XpmemPartitionPrefix>(), 64);
    assert_eq_usize(align_of::<XpmemPartitionPrefix>(), 64);
    assert_eq_usize(size_of::<XpmemPerm>(), 16);
    assert_eq_usize(offset_of!(XpmemPerm, mode), 8);
    assert_eq_usize(size_of::<XpmemAttachment>(), 80);
    assert_eq_usize(offset_of!(XpmemAttachment, vaddr), 8);
    assert_eq_usize(offset_of!(XpmemAttachment, at_vmr), 32);
    assert_eq_usize(offset_of!(XpmemAttachment, refcnt), 44);
    assert_eq_usize(offset_of!(XpmemAttachment, att_list), 56);
    assert_eq_usize(offset_of!(XpmemAttachment, vm), 72);

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
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<Process>(), 18112);
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
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(Process, enable_tofu), 1436);
    assert_eq_usize(offset_of!(Process, perf_status), 1456);
    assert_eq_usize(offset_of!(Process, monitoring_event), 1464);
    assert_eq_usize(offset_of!(Process, profile), 1472);
    assert_eq_usize(offset_of!(Process, nr_processes), 1616);
    assert_eq_usize(offset_of!(Process, straight_va), 1624);
    assert_eq_usize(offset_of!(Process, coredump_lock), 1664);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(Process, fd_pde_data), 1728);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(Process, fd_path), 9920);

    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<Thread>(), 5568);
    #[cfg(enable_tofu)]
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
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(Thread, fd_path_in_open), 5536);

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
    assert_eq_usize(size_of::<RusagePercpu>(), 16);
    assert_eq_usize(offset_of!(RusagePercpu, system_tsc), 8);
    assert_eq_usize(size_of::<IhkMcMemoryArea>(), 24);
    assert_eq_usize(offset_of!(IhkMcMemoryArea, type_), 16);
    assert_eq_usize(size_of::<IhkMcMemoryNode>(), 16);
    assert_eq_usize(offset_of!(IhkMcMemoryNode, areas), 8);
    assert_eq_usize(size_of::<IhkMcPaOps>(), 32);
    assert_eq_usize(offset_of!(IhkMcPaOps, free_page), 8);
    assert_eq_usize(offset_of!(IhkMcPaOps, alloc), 16);
    assert_eq_usize(offset_of!(IhkMcPaOps, free), 24);
    assert_eq_usize(size_of::<TlbFlushEntry>(), 64);
    assert_eq_usize(align_of::<TlbFlushEntry>(), 64);
    assert_eq_usize(offset_of!(TlbFlushEntry, addr), 8);
    assert_eq_usize(offset_of!(TlbFlushEntry, nr_addr), 16);
    assert_eq_usize(offset_of!(TlbFlushEntry, pending), 20);
    assert_eq_usize(offset_of!(TlbFlushEntry, lock), 24);
    assert_eq_usize(size_of::<IhkMcPageCacheHeader>(), 8);
    assert_eq_usize(offset_of!(IhkMcPageCacheHeader, next), 0);
    assert_eq_usize(size_of::<KmallocCacheHeader>(), 8);
    assert_eq_usize(size_of::<KmallocHeader>(), 32);
    assert_eq_usize(offset_of!(KmallocHeader, cpu_id), 4);
    assert_eq_usize(offset_of!(KmallocHeader, link), 8);
    assert_eq_usize(offset_of!(KmallocHeader, size), 24);
    assert_eq_usize(offset_of!(KmallocHeader, end_magic), 28);
    assert_eq_usize(size_of::<SmpFuncCallData>(), 24);
    assert_eq_usize(offset_of!(SmpFuncCallData, cpus_left), 4);
    assert_eq_usize(offset_of!(SmpFuncCallData, func), 8);
    assert_eq_usize(offset_of!(SmpFuncCallData, arg), 16);
    assert_eq_usize(size_of::<SmpFuncCallRequest>(), 32);
    assert_eq_usize(offset_of!(SmpFuncCallRequest, cpu_index), 8);
    assert_eq_usize(offset_of!(SmpFuncCallRequest, list), 16);
    assert_eq_usize(size_of::<Backlog>(), 32);
    assert_eq_usize(offset_of!(Backlog, func), 16);
    assert_eq_usize(offset_of!(Backlog, arg), 24);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(size_of::<CpuLocalVar>(), 8128);
    #[cfg(enable_tofu)]
    assert_eq_usize(size_of::<CpuLocalVar>(), 24576);
    assert_eq_usize(align_of::<CpuLocalVar>(), 64);
    assert_eq_usize(offset_of!(CpuLocalVar, idle), 64);
    assert_eq_usize(offset_of!(CpuLocalVar, idle_proc), 5632);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, idle_vm), 7360);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, idle_vm), 23744);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, idle_asp), 7664);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, idle_asp), 24120);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, current), 7848);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, current), 24304);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, runq), 7872);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, runq), 24328);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, status), 7920);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, status), 24376);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, pending_free_pages), 7928);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, pending_free_pages), 24384);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, migq), 7952);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, migq), 24408);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, no_preempt), 7976);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, no_preempt), 24432);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, monitor), 8000);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, monitor), 24456);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, rusage), 8008);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, rusage), 24464);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, smp_func_req_list), 8024);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, smp_func_req_list), 24480);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, backlog_list), 8056);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, backlog_list), 24512);
    #[cfg(not(enable_tofu))]
    assert_eq_usize(offset_of!(CpuLocalVar, uti_futex_resp), 8072);
    #[cfg(enable_tofu)]
    assert_eq_usize(offset_of!(CpuLocalVar, uti_futex_resp), 24528);
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
