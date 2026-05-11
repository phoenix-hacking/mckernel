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
};
