// SPDX-License-Identifier: GPL-2.0
//
// Checked by scripts/x86_64_shared_abi.py against the frozen McKernel/IHK C ABI.
// `--check` rejects value, layout, source-byte, or provenance drift.

//! Canonical shared x86_64 wire and userspace ABI definitions.
//!
//! This module deliberately contains data contracts only.  Queue algorithms,
//! pointer dereferences, ioctl dispatch, and ownership policy belong to their
//! consumers.  Flexible-array members are represented by their fixed prefix.

use core::ffi::c_void;

#[cfg(not(target_arch = "x86_64"))]
compile_error!("McKernel's canonical native ABI currently supports x86_64 only");
#[cfg(not(target_endian = "little"))]
compile_error!("McKernel's canonical x86_64 ABI requires little endian");
#[cfg(not(target_pointer_width = "64"))]
compile_error!("McKernel's canonical x86_64 ABI requires 64-bit pointers");

pub const ABI_POINTER_BITS: u32 = 64;
pub const ABI_LONG_BITS: u32 = 64;
pub const ABI_LITTLE_ENDIAN: bool = true;
pub const COMPAT_IOCTL_TRANSLATION_PRESENT: bool = false;

pub const IHK_OS_STATUS_NOT_BOOTED: i32 = 0;
pub const IHK_OS_STATUS_LOADING: i32 = 1;
pub const IHK_OS_STATUS_BOOTING: i32 = 2;
pub const IHK_OS_STATUS_BOOTED: i32 = 3;
pub const IHK_OS_STATUS_READY: i32 = 4;
pub const IHK_OS_STATUS_RUNNING: i32 = 5;
pub const IHK_OS_STATUS_FREEZING: i32 = 6;
pub const IHK_OS_STATUS_FROZEN: i32 = 7;
pub const IHK_OS_STATUS_SHUTDOWN: i32 = 8;
pub const IHK_OS_STATUS_FAILED: i32 = 9;
pub const IHK_OS_STATUS_HUNGUP: i32 = 10;
pub const IHK_OS_STATUS_COUNT: i32 = 11;

pub const IHK_DEVICE_CREATE_OS: u32 = 0x0011_2900;
pub const IHK_DEVICE_DESTROY_OS: u32 = 0x0011_2901;
pub const IHK_DEVICE_RESERVE_CPU: u32 = 0x0011_2902;
pub const IHK_DEVICE_RELEASE_CPU: u32 = 0x0011_2903;
pub const IHK_DEVICE_RESERVE_MEM: u32 = 0x0011_2904;
pub const IHK_DEVICE_RELEASE_MEM: u32 = 0x0011_2905;
pub const IHK_DEVICE_QUERY_CPU: u32 = 0x0011_2906;
pub const IHK_DEVICE_QUERY_MEM: u32 = 0x0011_2907;
pub const IHK_DEVICE_GET_KMSG_BUF: u32 = 0x0011_2908;
pub const IHK_DEVICE_READ_KMSG_BUF: u32 = 0x0011_2909;
pub const IHK_DEVICE_RELEASE_KMSG_BUF: u32 = 0x0011_290a;
pub const IHK_DEVICE_GET_BUILDID: u32 = 0x0011_290b;
pub const IHK_DEVICE_GET_NUM_CPUS: u32 = 0x0011_290c;
pub const IHK_DEVICE_RELEASE_MEM_PARTIALLY: u32 = 0x0011_290d;
pub const IHK_DEVICE_DETECT_HUNGUP: u32 = 0x0011_290f;

pub const IHK_OS_LOAD: u32 = 0x0011_2a00;
pub const IHK_OS_BOOT: u32 = 0x0011_2a01;
pub const IHK_OS_SHUTDOWN: u32 = 0x0011_2a02;
pub const IHK_OS_QUERY_STATUS: u32 = 0x0011_2a03;
pub const IHK_OS_SET_KARGS: u32 = 0x0011_2a04;
pub const IHK_OS_QUERY_FREE_MEM: u32 = 0x0011_2a05;
pub const IHK_OS_DUMP: u32 = 0x0011_2a06;
pub const IHK_OS_ALLOC_CPU: u32 = 0x0011_2a10;
pub const IHK_OS_ALLOC_MEM: u32 = 0x0011_2a11;
pub const IHK_OS_RESERVE_CPU: u32 = 0x0011_2a12;
pub const IHK_OS_RESERVE_MEM: u32 = 0x0011_2a13;
pub const IHK_OS_STATUS: u32 = 0x0011_2a14;
pub const IHK_OS_REGISTER_EVENT: u32 = 0x0011_2a15;
pub const IHK_OS_EVENTFD: u32 = 0x0011_2a16;
pub const IHK_OS_READ_KMSG: u32 = 0x0011_2a20;
pub const IHK_OS_CLEAR_KMSG: u32 = 0x0011_2a21;
pub const IHK_OS_ASSIGN_CPU: u32 = 0x0011_2a22;
pub const IHK_OS_RELEASE_CPU: u32 = 0x0011_2a23;
pub const IHK_OS_ASSIGN_MEM: u32 = 0x0011_2a24;
pub const IHK_OS_RELEASE_MEM: u32 = 0x0011_2a25;
pub const IHK_OS_QUERY_CPU: u32 = 0x0011_2a26;
pub const IHK_OS_QUERY_MEM: u32 = 0x0011_2a27;
pub const IHK_OS_SET_IKC_MAP: u32 = 0x0011_2a28;
pub const IHK_OS_GET_IKC_MAP: u32 = 0x0011_2a29;
pub const IHK_OS_FREEZE: u32 = 0x0011_2a30;
pub const IHK_OS_THAW: u32 = 0x0011_2a31;
pub const IHK_OS_GET_USAGE: u32 = 0x0011_2a32;
pub const IHK_OS_GET_CPU_USAGE: u32 = 0x0011_2a33;
pub const IHK_OS_GET_NUM_NUMA_NODES: u32 = 0x0011_2a34;
pub const IHK_OS_NOTIFY_HUNGUP: u32 = 0x0011_2a35;
pub const IHK_OS_GET_BUILDID: u32 = 0x0011_2a37;
pub const IHK_OS_GET_NUM_CPUS: u32 = 0x0011_2a38;
pub const IHK_OS_READ_KADDR: u32 = 0x0011_2a39;
pub const IHK_OS_AUX_PERF_NUM: u32 = 0x1129_0100;
pub const IHK_OS_AUX_PERF_SET: u32 = 0x1129_0101;
pub const IHK_OS_AUX_PERF_GET: u32 = 0x1129_0102;
pub const IHK_OS_AUX_PERF_ENABLE: u32 = 0x1129_0103;
pub const IHK_OS_AUX_PERF_DISABLE: u32 = 0x1129_0104;
pub const IHK_OS_AUX_PERF_DESTROY: u32 = 0x1129_0105;
pub const IHK_OS_GETRUSAGE: u32 = 0x1129_0106;
pub const FLAG_IHK_OS_SHUTDOWN_FORCE: u32 = 0x4000_0000;

pub const MCEXEC_UP_PREPARE_IMAGE: u32 = 0x30a0_2900;
pub const MCEXEC_UP_TRANSFER: u32 = 0x30a0_2901;
pub const MCEXEC_UP_START_IMAGE: u32 = 0x30a0_2902;
pub const MCEXEC_UP_WAIT_SYSCALL: u32 = 0x30a0_2903;
pub const MCEXEC_UP_RET_SYSCALL: u32 = 0x30a0_2904;
pub const MCEXEC_UP_LOAD_SYSCALL: u32 = 0x30a0_2905;
pub const MCEXEC_UP_SEND_SIGNAL: u32 = 0x30a0_2906;
pub const MCEXEC_UP_GET_CPU: u32 = 0x30a0_2907;
pub const MCEXEC_UP_STRNCPY_FROM_USER: u32 = 0x30a0_2908;
pub const MCEXEC_UP_GET_CRED: u32 = 0x30a0_290a;
pub const MCEXEC_UP_GET_CREDV: u32 = 0x30a0_290b;
pub const MCEXEC_UP_GET_NODES: u32 = 0x30a0_290c;
pub const MCEXEC_UP_GET_CPUSET: u32 = 0x30a0_290d;
pub const MCEXEC_UP_CREATE_PPD: u32 = 0x30a0_290e;
pub const MCEXEC_UP_PREPARE_DMA: u32 = 0x30a0_2910;
pub const MCEXEC_UP_FREE_DMA: u32 = 0x30a0_2911;
pub const MCEXEC_UP_OPEN_EXEC: u32 = 0x30a0_2912;
pub const MCEXEC_UP_CLOSE_EXEC: u32 = 0x30a0_2913;
pub const MCEXEC_UP_SYS_MOUNT: u32 = 0x30a0_2914;
pub const MCEXEC_UP_SYS_UMOUNT: u32 = 0x30a0_2915;
pub const MCEXEC_UP_SYS_UNSHARE: u32 = 0x30a0_2916;
pub const MCEXEC_UP_UTI_GET_CTX: u32 = 0x30a0_2920;
pub const MCEXEC_UP_UTI_SWITCH_CTX: u32 = 0x30a0_2921;
pub const MCEXEC_UP_SIG_THREAD: u32 = 0x30a0_2922;
pub const MCEXEC_UP_SYSCALL_THREAD: u32 = 0x30a0_2924;
pub const MCEXEC_UP_TERMINATE_THREAD: u32 = 0x30a0_2925;
pub const MCEXEC_UP_GET_NUM_POOL_THREADS: u32 = 0x30a0_2926;
pub const MCEXEC_UP_UTI_ATTR: u32 = 0x30a0_2927;
pub const MCEXEC_UP_RELEASE_USER_SPACE: u32 = 0x30a0_2928;
pub const MCEXEC_UP_DEBUG_LOG: u32 = 0x4000_0000;
pub const MCEXEC_UP_TRANSFER_TO_REMOTE: u32 = 0;
pub const MCEXEC_UP_TRANSFER_FROM_REMOTE: u32 = 1;

pub const IKC_FLAG_ENABLED: u32 = 1;
pub const IKC_FLAG_DESTROYING: u32 = 2;
pub const IKC_FLAG_DESTROY_ACKED: u32 = 4;
pub const IKC_FLAG_STATUS_MASK: u32 = 7;
pub const IKC_FLAG_NO_COPY: u32 = 0x10;
pub const IKC_NO_NOTIFY: u32 = 0x100;
pub const IHK_IKC_MAX_PORT: u32 = 512;
pub const IHK_IKC_MASTER_MSG_INIT_ACK: u32 = 0x1020_3010;
pub const IHK_IKC_MASTER_MSG_CONNECT: u32 = 0x2000_0001;
pub const IHK_IKC_MASTER_MSG_CONNECT_REPLY: u32 = 0x2000_0002;
pub const IHK_IKC_MASTER_MSG_DISCONNECT: u32 = 0x2000_0008;
pub const IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL: u32 = 0x2000_0010;

pub const SCD_MSG_PREPARE_PROCESS: i32 = 0x01;
pub const SCD_MSG_PREPARE_PROCESS_ACKED: i32 = 0x02;
pub const SCD_MSG_SCHEDULE_PROCESS: i32 = 0x03;
pub const SCD_MSG_SYSCALL_ONESIDE: i32 = 0x04;
pub const SCD_MSG_INIT_CHANNEL: i32 = 0x05;
pub const SCD_MSG_INIT_CHANNEL_ACKED: i32 = 0x06;
pub const SCD_MSG_SEND_SIGNAL: i32 = 0x07;
pub const SCD_MSG_SEND_SIGNAL_ACK: i32 = 0x08;
pub const SCD_MSG_CLEANUP_PROCESS: i32 = 0x09;
pub const SCD_MSG_CLEANUP_PROCESS_RESP: i32 = 0x0a;
pub const SCD_MSG_GET_VDSO_INFO: i32 = 0x0b;
pub const SCD_MSG_GET_CPU_MAPPING: i32 = 0x0c;
pub const SCD_MSG_REPLY_GET_CPU_MAPPING: i32 = 0x0d;
pub const SCD_MSG_PROCFS_CREATE: i32 = 0x10;
pub const SCD_MSG_PROCFS_DELETE: i32 = 0x11;
pub const SCD_MSG_PROCFS_REQUEST: i32 = 0x12;
pub const SCD_MSG_PROCFS_ANSWER: i32 = 0x13;
pub const SCD_MSG_WAKE_UP_SYSCALL_THREAD: i32 = 0x14;
pub const SCD_MSG_PROCFS_RELEASE: i32 = 0x15;
pub const SCD_MSG_REMOTE_PAGE_FAULT: i32 = 0x18;
pub const SCD_MSG_REMOTE_PAGE_FAULT_ANSWER: i32 = 0x19;
pub const SCD_MSG_DEBUG_LOG: i32 = 0x20;
pub const SCD_MSG_SYSFS_REQ_CREATE: i32 = 0x30;
pub const SCD_MSG_SYSFS_REQ_MKDIR: i32 = 0x32;
pub const SCD_MSG_SYSFS_REQ_SYMLINK: i32 = 0x34;
pub const SCD_MSG_SYSFS_REQ_LOOKUP: i32 = 0x36;
pub const SCD_MSG_SYSFS_REQ_UNLINK: i32 = 0x38;
pub const SCD_MSG_SYSFS_REQ_SHOW: i32 = 0x3a;
pub const SCD_MSG_SYSFS_RESP_SHOW: i32 = 0x3b;
pub const SCD_MSG_SYSFS_REQ_STORE: i32 = 0x3c;
pub const SCD_MSG_SYSFS_RESP_STORE: i32 = 0x3d;
pub const SCD_MSG_SYSFS_REQ_RELEASE: i32 = 0x3e;
pub const SCD_MSG_SYSFS_RESP_RELEASE: i32 = 0x3f;
pub const SCD_MSG_SYSFS_REQ_SETUP: i32 = 0x40;
pub const SCD_MSG_SYSFS_RESP_SETUP: i32 = 0x41;
pub const SCD_MSG_PROCFS_TID_CREATE: i32 = 0x44;
pub const SCD_MSG_PROCFS_TID_DELETE: i32 = 0x45;
pub const SCD_MSG_EVENTFD: i32 = 0x46;
pub const SCD_MSG_PERF_CTRL: i32 = 0x50;
pub const SCD_MSG_PERF_ACK: i32 = 0x51;
pub const SCD_MSG_CPU_RW_REG: i32 = 0x52;
pub const SCD_MSG_CPU_RW_REG_RESP: i32 = 0x53;
pub const SCD_MSG_CLEANUP_FD: i32 = 0x54;
pub const SCD_MSG_CLEANUP_FD_RESP: i32 = 0x55;
pub const SCD_MSG_FUTEX_WAKE: i32 = 0x60;

pub const IHK_KMSG_SIZE: usize = (4 << 20) - 4096;
pub const IHK_MAX_NUM_NUMA_NODES: usize = 1024;
pub const IHK_MAX_NUM_CPUS: usize = 1024;
pub const IHK_MAX_NUM_PGSIZES: usize = 8;
pub const SMP_MAX_CPUS: usize = 512;
pub const PERF_EXTRA_REG_MAX: usize = 10;

#[repr(C)]
pub struct DumpMemChunk {
    pub addr: u64,
    pub size: u64,
}

#[repr(C)]
pub struct DumpMemChunksPrefix {
    pub nr_chunks: i32,
    pub kernel_base: u64,
    pub phys_start: u64,
}

#[repr(C)]
pub struct DumpArgs {
    pub cmd: i32,
    pub level: u32,
    pub start: i64,
    pub size: i64,
    pub buf: *mut c_void,
    pub spare: [*mut c_void; 4],
}

#[repr(C)]
pub struct IhkCpuRequest {
    pub cpus: *mut i32,
    pub num_cpus: i32,
}

#[repr(C)]
pub struct IhkMemoryRequest {
    pub sizes: *mut usize,
    pub numa_ids: *mut i32,
    pub num_chunks: i32,
    pub min_chunk_size: i32,
    pub max_size_ratio_all: i32,
    pub timeout: i32,
}

#[repr(C)]
pub struct IhkIkcRequest {
    pub src_cpus: *mut i32,
    pub dst_cpus: *mut i32,
    pub num_cpus: i32,
}

#[repr(C)]
pub struct IhkOsIoctlEventfdDesc {
    pub fd: i32,
    pub eventfd_type: i32,
}

#[repr(C)]
pub struct IhkOsReadKernelAddressDesc {
    pub kernel_address: u64,
    pub length: u64,
    pub user_buffer: *mut c_void,
    pub flags: i32,
}

#[repr(C)]
pub struct IhkDeviceGetKmsgBufDesc {
    pub os_index: i32,
    pub handle: *mut c_void,
}

#[repr(C)]
pub struct IhkDeviceReadKmsgBufDesc {
    pub handle: *mut c_void,
    pub shift: i32,
    pub buffer: *mut u8,
}

#[repr(C)]
pub struct IhkIkcQueueHead {
    pub id: u32,
    pub type_: u16,
    pub packet_size: u16,
    pub packet_count: u32,
    pub flags: u32,
    pub read_offset: u64,
    pub max_read_offset: u64,
    pub write_offset: u64,
    pub queue_size: u64,
    pub channel_id: u32,
    pub read_cpu: u32,
    pub write_cpu: u32,
    pub reserved: u32,
}

#[repr(C)]
pub struct IhkIkcPacketHeader {
    pub channel: *mut c_void,
}

#[repr(C)]
pub struct IhkIkcMasterPacket {
    pub header: IhkIkcPacketHeader,
    pub message: u32,
    pub reference: u32,
    pub parameters: [u64; 5],
}

#[repr(C)]
pub struct SyscallRequest {
    pub requesting_tid: i32,
    pub target_tid: i32,
    pub valid: u64,
    pub number: u64,
    pub args: [u64; 6],
}

#[repr(C)]
pub struct IkcScdTraditionalPayload {
    pub reference: i32,
    pub os_number: i32,
    pub pid: i32,
    pub argument: u64,
    pub request: SyscallRequest,
    pub response_physical_address: u64,
}

#[repr(C)]
pub union IkcScdPayload {
    pub traditional: core::mem::ManuallyDrop<IkcScdTraditionalPayload>,
    pub sysfs: [i64; 3],
    pub wake_target_tid: i32,
    pub raw: [u64; 13],
}

#[repr(C)]
pub struct IkcScdPacket {
    pub header: IhkIkcPacketHeader,
    pub message: i32,
    pub error: i32,
    pub reply: *mut c_void,
    pub payload: IkcScdPayload,
}

#[repr(C)]
pub struct IhkKmsgBuffer {
    pub lock: i32,
    pub tail: i32,
    pub length: i32,
    pub head: i32,
    pub padding: [u8; 4080],
    pub bytes: [u8; IHK_KMSG_SIZE],
}

#[repr(C)]
pub struct IhkOsCpuMonitor {
    pub status: i32,
    pub previous_status: i32,
    pub counter: u64,
    pub previous_counter: u64,
}

#[repr(C)]
pub struct IhkOsMonitorPrefix {
    pub num_processors: u64,
    pub reserve: [u64; 128],
}

#[repr(C)]
pub struct IhkOsRusage {
    pub memory_stat_rss: [u64; IHK_MAX_NUM_PGSIZES],
    pub memory_stat_mapped_file: [u64; IHK_MAX_NUM_PGSIZES],
    pub memory_max_usage: u64,
    pub memory_kmem_usage: u64,
    pub memory_kmem_max_usage: u64,
    pub memory_numa_stat: [u64; IHK_MAX_NUM_NUMA_NODES],
    pub cpuacct_stat_system: u64,
    pub cpuacct_stat_user: u64,
    pub cpuacct_usage: u64,
    pub cpuacct_usage_percpu: [u64; IHK_MAX_NUM_CPUS],
    pub num_threads: i32,
    pub max_num_threads: i32,
}

#[repr(C)]
pub struct IhkSmpCoreSet {
    pub set: [u64; 8],
}

#[repr(C)]
pub struct IhkSmpBootParamCpu {
    pub numa_id: i32,
    pub hardware_id: i32,
    pub linux_cpu_id: i32,
    pub ikc_cpu: i32,
}

#[repr(C)]
pub struct IhkSmpBootParamMemoryChunk {
    pub start: u64,
    pub end: u64,
    pub numa_id: i32,
}

#[repr(C)]
pub struct IhkSmpBootParamNumaNode {
    pub memory_type: i32,
    pub linux_numa_id: i32,
}

#[repr(C)]
pub struct IhkDumpPagePrefix {
    pub start: u64,
    pub map_count: u64,
}

#[repr(C)]
pub struct IhkDumpPageSet {
    pub completion_flag: u32,
    pub count: u32,
    pub page_size: u64,
    pub physical_page: u64,
}

/// Frozen x86_64 boot prefix with `IHK_IKC_USE_LINUX_WORK_IRQ` and
/// `ENABLE_PERF`, matching the legacy build profile used by the converter.
#[repr(C)]
pub struct IhkSmpBootParam {
    pub start: u64,
    pub end: u64,
    pub status: u64,
    pub parameter_size: i32,
    pub bootstrap_memory_end: u64,
    pub message_buffer: u64,
    pub message_buffer_size: u64,
    pub master_ikc_queue_receive: u64,
    pub master_ikc_queue_send: u64,
    pub monitor: u64,
    pub monitor_size: u64,
    pub rusage: u64,
    pub rusage_size: u64,
    pub nmi_mode_address: u64,
    pub multi_interrupt_mode_address: u64,
    pub mckernel_do_futex: u64,
    pub linux_kernel_page_table_physical: u64,
    pub page_offset_base: u64,
    pub dma_address: u64,
    pub identity_table: u64,
    pub nanoseconds_per_tsc: u64,
    pub boot_tsc: u64,
    pub boot_seconds: u64,
    pub boot_nanoseconds: u64,
    pub ikc_cpu_raised_list: [*mut c_void; SMP_MAX_CPUS],
    pub ikc_irq_work_function: *mut c_void,
    pub ikc_irq: u32,
    pub ikc_irq_apic_ids: [u32; SMP_MAX_CPUS],
    pub kernel_args: [u8; 256],
    pub nr_linux_cpus: i32,
    pub nr_cpus: i32,
    pub nr_numa_nodes: i32,
    pub nr_memory_chunks: i32,
    pub os_number: i32,
    pub dump_level: u32,
    pub linux_default_huge_page_shift: i32,
    pub dump_page_set: IhkDumpPageSet,
    pub hardware_event_map: [u64; 10],
    pub hardware_cache_event_ids: [u64; 42],
    pub hardware_cache_extra_registers: [u64; 42],
    pub nr_extra_registers: u32,
    pub extra_register_event: [u32; PERF_EXTRA_REG_MAX],
    pub extra_register_msr: [u32; PERF_EXTRA_REG_MAX],
    pub extra_register_valid_mask: [u64; PERF_EXTRA_REG_MAX],
    pub extra_register_index: [i32; PERF_EXTRA_REG_MAX],
}

macro_rules! assert_layout {
    ($ty:ty, $size:expr, $align:expr $(, $field:ident => $offset:expr)* $(,)?) => {
        const _: () = {
            assert!(core::mem::size_of::<$ty>() == $size);
            assert!(core::mem::align_of::<$ty>() == $align);
            $(assert!(core::mem::offset_of!($ty, $field) == $offset);)*
        };
    };
}

assert_layout!(DumpMemChunk, 16, 8, addr => 0, size => 8);
assert_layout!(DumpMemChunksPrefix, 24, 8, nr_chunks => 0, kernel_base => 8, phys_start => 16);
assert_layout!(DumpArgs, 64, 8, cmd => 0, level => 4, start => 8, size => 16, buf => 24, spare => 32);
assert_layout!(IhkCpuRequest, 16, 8, cpus => 0, num_cpus => 8);
assert_layout!(IhkMemoryRequest, 32, 8, sizes => 0, numa_ids => 8, num_chunks => 16, min_chunk_size => 20, max_size_ratio_all => 24, timeout => 28);
assert_layout!(IhkIkcRequest, 24, 8, src_cpus => 0, dst_cpus => 8, num_cpus => 16);
assert_layout!(IhkOsIoctlEventfdDesc, 8, 4, fd => 0, eventfd_type => 4);
assert_layout!(IhkOsReadKernelAddressDesc, 32, 8, kernel_address => 0, length => 8, user_buffer => 16, flags => 24);
assert_layout!(IhkDeviceGetKmsgBufDesc, 16, 8, os_index => 0, handle => 8);
assert_layout!(IhkDeviceReadKmsgBufDesc, 24, 8, handle => 0, shift => 8, buffer => 16);
assert_layout!(IhkIkcQueueHead, 64, 8, id => 0, type_ => 4, packet_size => 6, packet_count => 8, flags => 12, read_offset => 16, max_read_offset => 24, write_offset => 32, queue_size => 40, channel_id => 48, read_cpu => 52, write_cpu => 56, reserved => 60);
assert_layout!(IhkIkcPacketHeader, 8, 8, channel => 0);
assert_layout!(IhkIkcMasterPacket, 56, 8, header => 0, message => 8, reference => 12, parameters => 16);
assert_layout!(SyscallRequest, 72, 8, requesting_tid => 0, target_tid => 4, valid => 8, number => 16, args => 24);
assert_layout!(IkcScdTraditionalPayload, 104, 8, reference => 0, os_number => 4, pid => 8, argument => 16, request => 24, response_physical_address => 96);
assert_layout!(IkcScdPayload, 104, 8, traditional => 0, sysfs => 0, wake_target_tid => 0, raw => 0);
assert_layout!(IkcScdPacket, 128, 8, header => 0, message => 8, error => 12, reply => 16, payload => 24);
assert_layout!(IhkKmsgBuffer, 4 << 20, 4, lock => 0, tail => 4, length => 8, head => 12, padding => 16, bytes => 4096);
assert_layout!(IhkOsCpuMonitor, 24, 8, status => 0, previous_status => 4, counter => 8, previous_counter => 16);
assert_layout!(IhkOsMonitorPrefix, 1032, 8, num_processors => 0, reserve => 8);
assert_layout!(IhkOsRusage, 16568, 8, memory_stat_rss => 0, memory_stat_mapped_file => 64, memory_max_usage => 128, memory_kmem_usage => 136, memory_kmem_max_usage => 144, memory_numa_stat => 152, cpuacct_stat_system => 8344, cpuacct_stat_user => 8352, cpuacct_usage => 8360, cpuacct_usage_percpu => 8368, num_threads => 16560, max_num_threads => 16564);
assert_layout!(IhkSmpCoreSet, 64, 8, set => 0);
assert_layout!(IhkSmpBootParamCpu, 16, 4, numa_id => 0, hardware_id => 4, linux_cpu_id => 8, ikc_cpu => 12);
assert_layout!(IhkSmpBootParamMemoryChunk, 24, 8, start => 0, end => 8, numa_id => 16);
assert_layout!(IhkSmpBootParamNumaNode, 8, 4, memory_type => 0, linux_numa_id => 4);
assert_layout!(IhkDumpPagePrefix, 16, 8, start => 0, map_count => 8);
assert_layout!(IhkDumpPageSet, 24, 8, completion_flag => 0, count => 4, page_size => 8, physical_page => 16);
assert_layout!(IhkSmpBootParam, 7616, 8, start => 0, end => 8, status => 16, parameter_size => 24, bootstrap_memory_end => 32, message_buffer => 40, message_buffer_size => 48, master_ikc_queue_receive => 56, master_ikc_queue_send => 64, monitor => 72, monitor_size => 80, rusage => 88, rusage_size => 96, nmi_mode_address => 104, multi_interrupt_mode_address => 112, mckernel_do_futex => 120, linux_kernel_page_table_physical => 128, page_offset_base => 136, dma_address => 144, identity_table => 152, nanoseconds_per_tsc => 160, boot_tsc => 168, boot_seconds => 176, boot_nanoseconds => 184, ikc_cpu_raised_list => 192, ikc_irq_work_function => 4288, ikc_irq => 4296, ikc_irq_apic_ids => 4300, kernel_args => 6348, nr_linux_cpus => 6604, nr_cpus => 6608, nr_numa_nodes => 6612, nr_memory_chunks => 6616, os_number => 6620, dump_level => 6624, linux_default_huge_page_shift => 6628, dump_page_set => 6632, hardware_event_map => 6656, hardware_cache_event_ids => 6736, hardware_cache_extra_registers => 7072, nr_extra_registers => 7408, extra_register_event => 7412, extra_register_msr => 7452, extra_register_valid_mask => 7496, extra_register_index => 7576);

const _: () = {
    assert!(ABI_POINTER_BITS == usize::BITS);
    assert!(u32::from_le_bytes([0x00, 0x29, 0x11, 0x00]) == IHK_DEVICE_CREATE_OS);
    assert!(u32::from_le_bytes([0x00, 0x29, 0xa0, 0x30]) == MCEXEC_UP_PREPARE_IMAGE);
    assert!(u32::from_le_bytes([0x10, 0x30, 0x20, 0x10]) == IHK_IKC_MASTER_MSG_INIT_ACK);
};
