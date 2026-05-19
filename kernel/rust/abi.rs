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
};
