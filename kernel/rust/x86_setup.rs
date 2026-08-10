use core::ffi::{c_char, c_void};
use core::mem::{align_of, offset_of, size_of};
use core::ptr::{null_mut, write_unaligned};

use crate::abi::{CInt, CULong};

const PAGE_SHIFT: usize = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const SMP_MAX_CPUS: usize = 512;
const ENOENT: CInt = 2;
const EINVAL: CInt = 22;

const IHK_MC_GMA_MAP_START: CInt = 0;
const IHK_MC_GMA_MAP_END: CInt = 1;
const IHK_MC_GMA_AVAIL_START: CInt = 2;
const IHK_MC_GMA_AVAIL_END: CInt = 3;
const IHK_MC_GMA_HEAP_START: CInt = 4;
const IHK_MC_NR_RESERVED_AREAS: CInt = 5;
const IHK_MC_RESERVED_AREA_START: CInt = 6;
const IHK_MC_RESERVED_AREA_END: CInt = 7;

const IHK_GV_IKC: CInt = 1;
const IHK_GV_QUERY_FREE_MEM: CInt = 2;
const IHK_TLB_FLUSH_IRQ_VECTOR_START: CInt = 68;
const IHK_TLB_FLUSH_IRQ_VECTOR_END: CInt = IHK_TLB_FLUSH_IRQ_VECTOR_START + 64;

const PERF_COUNT_HW_MAX: usize = 10;
const PERF_COUNT_HW_CACHE_MAX: usize = 7;
const PERF_COUNT_HW_CACHE_OP_MAX: usize = 3;
const PERF_COUNT_HW_CACHE_RESULT_MAX: usize = 2;
const PERF_EXTRA_REG_MAX: usize = 10;
const PERFCTR_MAX_TYPE: usize = 25;

const APT_TYPE_L1D_REQUEST: usize = 12;
const APT_TYPE_L1I_REQUEST: usize = 13;
const APT_TYPE_LLC_MISS: usize = 15;
const APT_TYPE_DTLB_MISS: usize = 16;
const APT_TYPE_ITLB_MISS: usize = 17;
const APT_TYPE_STALL: usize = 18;
const APT_TYPE_CYCLE: usize = 19;
const APT_TYPE_INSTRUCTIONS: usize = 20;
const APT_TYPE_L1D_MISS: usize = 21;
const APT_TYPE_L1I_MISS: usize = 22;
const APT_TYPE_L2_MISS: usize = 23;

const TURBO_NEEDLE: &[u8] = b"turbo\0";
const BOOT_PARAM_SIZE_FMT: &[u8] = b"boot_param_size: %lu\n\0";
const NS_PER_TSC_FMT: &[u8] = b"ns_per_tsc: %lu\n\0";
const STARTED_MSG: &[u8] = b"IHK/McKernel started.\n\0";
const RAISED_LIST_ERROR: &[u8] = b"error: mapping Linux IRQ raised list head\n\0";
const EMPTY_PANIC: &[u8] = b"\0";

const BOOT_STACK_SIZE: usize = 64 * 1024;

#[repr(C, align(4096))]
struct BootStack([u8; BOOT_STACK_SIZE]);

#[repr(C)]
pub struct IhkMcCpuInfo {
    ncpus: CInt,
    hw_ids: *mut CInt,
    nodes: *mut CInt,
    linux_cpu_ids: *mut CInt,
    ikc_cpus: *mut CInt,
}

#[repr(C)]
struct IhkSmpBootParamCpu {
    numa_id: CInt,
    hw_id: CInt,
    linux_cpu_id: CInt,
    ikc_cpu: CInt,
}

#[repr(C)]
struct IhkSmpBootParamMemoryChunk {
    start: CULong,
    end: CULong,
    numa_id: CInt,
}

#[repr(C)]
struct IhkSmpBootParamNumaNode {
    type_: CInt,
    linux_numa_id: CInt,
}

#[repr(C)]
pub struct IhkDumpPage {
    start: CULong,
    map_count: CULong,
}

#[repr(C)]
pub struct IhkDumpPageSet {
    completion_flag: u32,
    count: u32,
    page_size: CULong,
    phy_page: CULong,
}

#[repr(C)]
pub struct SmpBootParam {
    start: CULong,
    end: CULong,
    status: CULong,
    param_size: CInt,
    bootstrap_mem_end: CULong,
    msg_buffer: CULong,
    msg_buffer_size: CULong,
    mikc_queue_recv: CULong,
    mikc_queue_send: CULong,
    monitor: CULong,
    monitor_size: CULong,
    rusage: CULong,
    rusage_size: CULong,
    nmi_mode_addr: CULong,
    multi_intr_mode_addr: CULong,
    mckernel_do_futex: CULong,
    linux_kernel_pgt_phys: CULong,
    page_offset_base: CULong,
    dma_address: CULong,
    ident_table: CULong,
    ns_per_tsc: CULong,
    boot_tsc: CULong,
    boot_sec: CULong,
    boot_nsec: CULong,
    ihk_ikc_cpu_raised_list: [*mut c_void; SMP_MAX_CPUS],
    ikc_irq_work_func: *mut c_void,
    ihk_ikc_irq: u32,
    ihk_ikc_irq_apicids: [u32; SMP_MAX_CPUS],
    kernel_args: [c_char; 256],
    nr_linux_cpus: CInt,
    nr_cpus: CInt,
    nr_numa_nodes: CInt,
    nr_memory_chunks: CInt,
    osnum: CInt,
    dump_level: u32,
    linux_default_huge_page_shift: CInt,
    dump_page_set: IhkDumpPageSet,
    #[cfg(enable_perf)]
    hw_event_map: [CULong; PERF_COUNT_HW_MAX],
    #[cfg(enable_perf)]
    hw_cache_event_ids: [CULong;
        PERF_COUNT_HW_CACHE_MAX * PERF_COUNT_HW_CACHE_OP_MAX * PERF_COUNT_HW_CACHE_RESULT_MAX],
    #[cfg(enable_perf)]
    hw_cache_extra_regs: [CULong;
        PERF_COUNT_HW_CACHE_MAX * PERF_COUNT_HW_CACHE_OP_MAX * PERF_COUNT_HW_CACHE_RESULT_MAX],
    #[cfg(enable_perf)]
    nr_extra_regs: u32,
    #[cfg(enable_perf)]
    ereg_event: [u32; PERF_EXTRA_REG_MAX],
    #[cfg(enable_perf)]
    ereg_msr: [u32; PERF_EXTRA_REG_MAX],
    #[cfg(enable_perf)]
    ereg_valid_mask: [CULong; PERF_EXTRA_REG_MAX],
    #[cfg(enable_perf)]
    ereg_idx: [CInt; PERF_EXTRA_REG_MAX],
}

const _: () = {
    assert!(size_of::<IhkMcCpuInfo>() == 40);
    assert!(align_of::<IhkMcCpuInfo>() == 8);
    assert!(offset_of!(IhkMcCpuInfo, hw_ids) == 8);
    assert!(size_of::<IhkSmpBootParamCpu>() == 16);
    assert!(size_of::<IhkSmpBootParamMemoryChunk>() == 24);
    assert!(size_of::<IhkSmpBootParamNumaNode>() == 8);
    assert!(size_of::<IhkDumpPageSet>() == 24);
    assert!(offset_of!(SmpBootParam, param_size) == 24);
    assert!(offset_of!(SmpBootParam, bootstrap_mem_end) == 32);
    assert!(offset_of!(SmpBootParam, ihk_ikc_cpu_raised_list) == 192);
    assert!(offset_of!(SmpBootParam, ihk_ikc_irq) == 4296);
    assert!(offset_of!(SmpBootParam, kernel_args) == 6348);
    assert!(offset_of!(SmpBootParam, dump_page_set) == 6632);
};

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut boot_param_pa: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut boot_param: *mut SmpBootParam = null_mut();
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut boot_param_size: CInt = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut bootstrap_mem_end: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut linux_page_offset_base: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut x86_kernel_phys_base: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut ap_trampoline: CULong = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut ihk_ikc_irq: u32 = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut ihk_ikc_irq_apicid: u32 = 0;
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut dump_page: *mut IhkDumpPage = null_mut();

static mut STACK: BootStack = BootStack([0; 8192]);
static mut IHK_CPU_INFO: *mut IhkMcCpuInfo = null_mut();

static mut PERF_MAP_NEHALEM: [u32; PERFCTR_MAX_TYPE + 1] = {
    let mut map = [u32::MAX; PERFCTR_MAX_TYPE + 1];
    map[APT_TYPE_INSTRUCTIONS] = 0xc0;
    map[APT_TYPE_L1D_REQUEST] = 0x143;
    map[APT_TYPE_L1I_REQUEST] = 0x380;
    map[APT_TYPE_L1D_MISS] = 0x151;
    map[APT_TYPE_L1I_MISS] = 0x280;
    map[APT_TYPE_L2_MISS] = 0xaa24;
    map[APT_TYPE_LLC_MISS] = 0x412e;
    map[APT_TYPE_DTLB_MISS] = 0x149;
    map[APT_TYPE_ITLB_MISS] = 0x185;
    map[APT_TYPE_STALL] = 0x180010e;
    map[APT_TYPE_CYCLE] = 0x3c;
    map[PERFCTR_MAX_TYPE] = u32::MAX;
    map
};

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub static mut x86_march_perfmap: *mut u32 = core::ptr::addr_of_mut!(PERF_MAP_NEHALEM) as *mut u32;

unsafe extern "C" {
    static mut kmsg_buf: *mut c_void;
    static mut no_turbo: CInt;
    static mut x86_issue_ipi: Option<unsafe extern "C" fn(CInt, CInt)>;

    fn main();
    fn setup_x86_phase1();
    fn setup_x86_phase2();
    fn init_boot_processor_local();
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn virt_to_phys(virt: *mut c_void) -> CULong;
    fn early_alloc_pages(npages: CInt) -> *mut c_void;
    fn get_last_early_heap() -> *mut c_void;
    fn map_fixed_area(phys: CULong, size: CULong, flags: CULong) -> *mut c_void;
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn kmsg_init();
    fn kputs(msg: *const c_char);
    fn strstr(haystack: *const c_char, needle: *const c_char) -> *mut c_char;
    fn panic(msg: *const c_char) -> !;
    fn cpu_pause();
    fn builtin_mc_dma_init(cfg_addr: CULong);
}

#[inline(always)]
unsafe fn barrier() {
    core::arch::asm!("", options(nostack, preserves_flags));
}

#[inline(always)]
unsafe fn boot_param_ref() -> &'static mut SmpBootParam {
    &mut *boot_param
}

#[inline(always)]
unsafe fn cpu_table() -> *mut IhkSmpBootParamCpu {
    boot_param.add(1).cast::<IhkSmpBootParamCpu>()
}

#[inline(always)]
unsafe fn numa_table() -> *mut IhkSmpBootParamNumaNode {
    cpu_table().add((*boot_param).nr_cpus as usize).cast()
}

#[inline(always)]
unsafe fn memory_chunk_table() -> *mut IhkSmpBootParamMemoryChunk {
    numa_table()
        .add((*boot_param).nr_numa_nodes as usize)
        .cast()
}

#[inline(always)]
unsafe fn distance_table() -> *mut CInt {
    memory_chunk_table()
        .add((*boot_param).nr_memory_chunks as usize)
        .cast()
}

#[cfg(not(mckernel_equivalence))]
static mut EARLY_PHASE: u8 = b'?';

#[cfg(not(mckernel_equivalence))]
#[inline(always)]
unsafe fn debugcon_byte(value: u8) {
    core::arch::asm!(
        "out 0xe9, al",
        in("al") value,
        options(nostack, preserves_flags),
    );
}

#[cfg(not(mckernel_equivalence))]
#[inline(always)]
pub(crate) unsafe fn early_phase(phase: u8) {
    core::ptr::write_volatile(&raw mut EARLY_PHASE, phase);
    debugcon_byte(phase);
    debugcon_byte(b'\n');
}

#[cfg(mckernel_equivalence)]
#[inline(always)]
pub(crate) unsafe fn early_phase(_phase: u8) {}

#[cfg(not(mckernel_equivalence))]
pub(crate) unsafe fn early_panic() {
    let phase = core::ptr::read_volatile(&raw const EARLY_PHASE);
    debugcon_byte(b'!');
    debugcon_byte(phase);
    debugcon_byte(b'\n');
}

#[cfg(mckernel_equivalence)]
pub(crate) unsafe fn early_panic() {}

#[inline(never)]
unsafe extern "C" fn arch_start_on_stack() -> ! {
    early_phase(b'A');
    init_boot_processor_local();
    early_phase(b'B');
    main();

    loop {
        core::hint::spin_loop();
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_start(
    param_addr: CULong,
    phys_address: CULong,
    ap_trampoline_start: CULong,
) -> ! {
    x86_kernel_phys_base = phys_address;
    boot_param = phys_to_virt(param_addr).cast();
    boot_param_pa = param_addr;
    ap_trampoline = ap_trampoline_start;
    ihk_ikc_irq = (*boot_param).ihk_ikc_irq;
    bootstrap_mem_end = (*boot_param).bootstrap_mem_end;
    boot_param_size = (*boot_param).param_size;
    linux_page_offset_base = (*boot_param).page_offset_base;

    early_phase(b'@');
    let stack_top = (&raw mut STACK.0).cast::<u8>().add(size_of::<BootStack>());
    core::arch::asm!(
        "mov rsp, {stack_top}",
        "call {entry}",
        "ud2",
        stack_top = in(reg) stack_top,
        entry = sym arch_start_on_stack,
        options(noreturn),
    )
}

unsafe fn build_ihk_cpu_info() {
    let cpu_count = (*boot_param).nr_cpus as usize;
    let alloc_size =
        size_of::<IhkMcCpuInfo>().wrapping_add(cpu_count.wrapping_mul(size_of::<*mut CInt>() * 4));
    let pages = (alloc_size.wrapping_add(PAGE_SIZE as usize - 1) >> PAGE_SHIFT) as CInt;

    IHK_CPU_INFO = early_alloc_pages(pages).cast();
    (*IHK_CPU_INFO).hw_ids = IHK_CPU_INFO.add(1).cast();
    (*IHK_CPU_INFO).nodes = (*IHK_CPU_INFO).hw_ids.add(cpu_count);
    (*IHK_CPU_INFO).linux_cpu_ids = (*IHK_CPU_INFO).nodes.add(cpu_count);
    (*IHK_CPU_INFO).ikc_cpus = (*IHK_CPU_INFO).linux_cpu_ids.add(cpu_count);

    let mut bp_cpu = cpu_table();
    let mut i = 0usize;
    while i < cpu_count {
        *(*IHK_CPU_INFO).hw_ids.add(i) = (*bp_cpu).hw_id;
        *(*IHK_CPU_INFO).nodes.add(i) = (*bp_cpu).numa_id;
        *(*IHK_CPU_INFO).linux_cpu_ids.add(i) = (*bp_cpu).linux_cpu_id;
        *(*IHK_CPU_INFO).ikc_cpus.add(i) = (*bp_cpu).ikc_cpu;
        bp_cpu = bp_cpu.add(1);
        i += 1;
    }

    (*IHK_CPU_INFO).ncpus = (*boot_param).nr_cpus;

    let mut linux_cpu = 0usize;
    let raised_list =
        core::ptr::addr_of_mut!((*boot_param).ihk_ikc_cpu_raised_list).cast::<*mut c_void>();
    while linux_cpu < (*boot_param).nr_linux_cpus as usize {
        let phys = *raised_list.add(linux_cpu) as CULong;
        let mapped = map_fixed_area(phys, PAGE_SIZE, 0);
        *raised_list.add(linux_cpu) = mapped;
        if mapped.is_null() {
            kprintf(RAISED_LIST_ERROR.as_ptr().cast());
            panic(EMPTY_PANIC.as_ptr().cast());
        }
        linux_cpu += 1;
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_numa_id() -> CInt {
    if !IHK_CPU_INFO.is_null() {
        *(*IHK_CPU_INFO)
            .nodes
            .add(crate::x86_local::ihk_mc_get_processor_id() as usize)
    } else {
        0
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_init() {
    let mut msg_buffer = 0;
    let mut msg_buffer_size = 0;

    (*boot_param).status = 1;
    early_phase(b'C');

    if !strstr(
        (*boot_param).kernel_args.as_ptr(),
        TURBO_NEEDLE.as_ptr().cast(),
    )
    .is_null()
    {
        no_turbo = 0;
    }
    early_phase(b'D');

    setup_x86_phase1();
    early_phase(b'E');
    kprintf(
        BOOT_PARAM_SIZE_FMT.as_ptr().cast(),
        boot_param_size as CULong,
    );

    boot_param = map_fixed_area(boot_param_pa, boot_param_size as CULong, 0).cast();
    dump_page = map_fixed_area(
        (*boot_param).dump_page_set.phy_page,
        (*boot_param).dump_page_set.page_size,
        0,
    )
    .cast();
    early_phase(b'F');

    ihk_get_kmsg_buf(&mut msg_buffer, &mut msg_buffer_size);
    kmsg_buf = map_fixed_area(msg_buffer, msg_buffer_size, 0);
    kmsg_init();
    early_phase(b'G');
    kputs(STARTED_MSG.as_ptr().cast());

    setup_x86_phase2();
    kprintf(NS_PER_TSC_FMT.as_ptr().cast(), (*boot_param).ns_per_tsc);
    build_ihk_cpu_info();
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_ready() {
    (*boot_param).status = 2;
    barrier();
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn done_init() {
    (*boot_param).status = 3;
    barrier();
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_set_mikc_queue(rq: *mut c_void, wq: *mut c_void) {
    (*boot_param).mikc_queue_recv = virt_to_phys(wq);
    (*boot_param).mikc_queue_send = virt_to_phys(rq);
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_memory_address(type_: CInt, _opt: CInt) -> CULong {
    match type_ {
        IHK_MC_GMA_MAP_START | IHK_MC_GMA_AVAIL_START => (*boot_param).start,
        IHK_MC_GMA_MAP_END | IHK_MC_GMA_AVAIL_END => (*boot_param).end,
        IHK_MC_GMA_HEAP_START => virt_to_phys(get_last_early_heap()),
        IHK_MC_NR_RESERVED_AREAS => 0,
        IHK_MC_RESERVED_AREA_START | IHK_MC_RESERVED_AREA_END => (-(ENOENT as isize)) as CULong,
        _ => (-(ENOENT as isize)) as CULong,
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_cpu_info() -> *mut IhkMcCpuInfo {
    IHK_CPU_INFO
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn get_transit_page_table() -> CULong {
    (*boot_param).ident_table
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn __reserve_arch_pages(
    _start: CULong,
    _end: CULong,
    _cb: Option<unsafe extern "C" fn(CULong, CULong, CInt)>,
) {
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_ikc_arch_issue_host_ipi(cpu: CInt, vector: CInt) -> CInt {
    if let Some(issue_ipi) = x86_issue_ipi {
        issue_ipi(ihk_mc_get_apicid(cpu), vector);
    }
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_vector(type_: CInt) -> CInt {
    match type_ {
        IHK_GV_IKC => 0xd1,
        IHK_GV_QUERY_FREE_MEM => 200,
        IHK_TLB_FLUSH_IRQ_VECTOR_START..IHK_TLB_FLUSH_IRQ_VECTOR_END => type_,
        _ => -ENOENT,
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_ns_per_tsc() -> CULong {
    (*boot_param).ns_per_tsc
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_boot_time(
    tv_sec: *mut CULong,
    tv_nsec: *mut CULong,
    tsc: *mut CULong,
) {
    *tv_sec = (*boot_param).boot_sec;
    *tv_nsec = (*boot_param).boot_nsec;
    *tsc = (*boot_param).boot_tsc;
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_get_kargs() -> *mut c_char {
    (*boot_param).kernel_args.as_mut_ptr()
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_get_kmsg_buf(addr: *mut CULong, size: *mut CULong) -> CInt {
    *addr = (*boot_param).msg_buffer;
    *size = (*boot_param).msg_buffer_size;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_set_monitor(addr: CULong, size: CULong) -> CInt {
    let bp = boot_param_ref();
    bp.monitor = addr;
    bp.monitor_size = size;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_set_rusage(addr: CULong, size: CULong) -> CInt {
    let bp = boot_param_ref();
    bp.rusage = addr;
    bp.rusage_size = size;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_set_multi_intr_mode_addr(addr: CULong) -> CInt {
    (*boot_param).multi_intr_mode_addr = addr;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_set_nmi_mode_addr(addr: CULong) -> CInt {
    (*boot_param).nmi_mode_addr = addr;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_set_mckernel_do_futex(addr: CULong) -> CInt {
    (*boot_param).mckernel_do_futex = addr;
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_map_memory(
    _os: *mut c_void,
    phys: CULong,
    _size: CULong,
) -> CULong {
    phys
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_unmap_memory(_os: *mut c_void, _phys: CULong, _size: CULong) {}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_setup_dma() {}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_nr_numa_nodes() -> CInt {
    (*boot_param).nr_numa_nodes
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_numa_node(
    id: CInt,
    linux_numa_id: *mut CInt,
    type_: *mut CInt,
) -> CInt {
    if id < 0 || id >= (*boot_param).nr_numa_nodes {
        return -1;
    }

    let node = numa_table().add(id as usize);
    if !linux_numa_id.is_null() {
        *linux_numa_id = (*node).linux_numa_id;
    }
    if !type_.is_null() {
        *type_ = (*node).type_;
    }
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_numa_distance(i: CInt, j: CInt) -> CInt {
    if i < 0 || i >= (*boot_param).nr_numa_nodes || j < 0 || j >= (*boot_param).nr_numa_nodes {
        return -1;
    }

    *distance_table().add((i * (*boot_param).nr_numa_nodes + j) as usize)
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_nr_memory_chunks() -> CInt {
    (*boot_param).nr_memory_chunks
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_linux_default_huge_page_shift() -> CInt {
    (*boot_param).linux_default_huge_page_shift
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_memory_chunk(
    id: CInt,
    start: *mut CULong,
    end: *mut CULong,
    numa_id: *mut CInt,
) -> CInt {
    if id < 0 || id >= (*boot_param).nr_memory_chunks {
        return -1;
    }

    let chunk = memory_chunk_table().add(id as usize);
    if !start.is_null() {
        *start = (*chunk).start;
    }
    if !end.is_null() {
        *end = (*chunk).end;
    }
    if !numa_id.is_null() {
        *numa_id = (*chunk).numa_id;
    }
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_nr_cores() -> CInt {
    (*boot_param).nr_cpus
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_nr_linux_cores() -> CInt {
    (*boot_param).nr_linux_cpus
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_osnum() -> CInt {
    (*boot_param).osnum
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_core(
    id: CInt,
    linux_core_id: *mut CULong,
    apic_id: *mut CULong,
    numa_id: *mut CInt,
) -> CInt {
    if id < 0 || id >= (*boot_param).nr_cpus {
        return -1;
    }

    let idx = id as usize;
    if !linux_core_id.is_null() {
        *linux_core_id = *(*IHK_CPU_INFO).linux_cpu_ids.add(idx) as CULong;
    }
    if !apic_id.is_null() {
        *apic_id = *(*IHK_CPU_INFO).hw_ids.add(idx) as CULong;
    }
    if !numa_id.is_null() {
        *numa_id = *(*IHK_CPU_INFO).nodes.add(idx);
    }
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_ikc_cpu(id: CInt) -> CInt {
    if id < 0 || id >= (*boot_param).nr_cpus || IHK_CPU_INFO.is_null() {
        return -1;
    }

    *(*IHK_CPU_INFO).ikc_cpus.add(id as usize)
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_apicid(linux_core_id: CInt) -> CInt {
    let apicids = core::ptr::addr_of!((*boot_param).ihk_ikc_irq_apicids).cast::<u32>();
    *apicids.add(linux_core_id as usize) as CInt
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_linux_kernel_pgt() -> *mut c_void {
    phys_to_virt((*boot_param).linux_kernel_pgt_phys)
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn arch_delay(us: CInt) {
    let tsc = crate::x86_cpu_helpers::rdtsc().wrapping_add(333u64.wrapping_mul(us as CULong));
    while crate::x86_cpu_helpers::rdtsc() < tsc {
        cpu_pause();
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn x86_set_warm_reset(ip: CULong, first_page_va: *mut c_char) {
    core::arch::asm!("out 0x70, al", in("al") 0x0f_u8, options(nomem, nostack, preserves_flags));
    core::arch::asm!("out 0x71, al", in("al") 0x0a_u8, options(nomem, nostack, preserves_flags));

    write_unaligned(first_page_va.add(0x469).cast::<u16>(), (ip >> 4) as u16);
    write_unaligned(first_page_va.add(0x467).cast::<u16>(), (ip & 0xf) as u16);
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_dma_init() {
    builtin_mc_dma_init((*boot_param).dma_address);
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_set_dump_level(level: u32) {
    (*boot_param).dump_level = level;
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_dump_level() -> u32 {
    (*boot_param).dump_level
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_dump_page_set() -> *mut IhkDumpPageSet {
    &raw mut (*boot_param).dump_page_set
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_dump_page() -> *mut IhkDumpPage {
    dump_page
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_id(hw_config: CULong, hw_config_ext: CULong) -> CInt {
    let ereg_event = core::ptr::addr_of!((*boot_param).ereg_event).cast::<u32>();
    let ereg_valid_mask = core::ptr::addr_of!((*boot_param).ereg_valid_mask).cast::<CULong>();
    let mut i = 0usize;
    while i < (*boot_param).nr_extra_regs as usize {
        if *ereg_event.add(i) as CULong == (hw_config & 0xffff) {
            if hw_config_ext & !*ereg_valid_mask.add(i) != 0 {
                return -EINVAL;
            }
            return i as CInt;
        }
        i += 1;
    }
    -1
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_id(
    _hw_config: CULong,
    _hw_config_ext: CULong,
) -> CInt {
    0
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_idx(id: CInt) -> CInt {
    let ereg_idx = core::ptr::addr_of!((*boot_param).ereg_idx).cast::<CInt>();
    *ereg_idx.add(id as usize)
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_idx(_id: CInt) -> CInt {
    0
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_msr(id: CInt) -> u32 {
    let ereg_msr = core::ptr::addr_of!((*boot_param).ereg_msr).cast::<u32>();
    *ereg_msr.add(id as usize)
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_msr(_id: CInt) -> u32 {
    0
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_event(id: CInt) -> CULong {
    let ereg_event = core::ptr::addr_of!((*boot_param).ereg_event).cast::<u32>();
    *ereg_event.add(id as usize) as CULong
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_get_extra_reg_event(_id: CInt) -> CULong {
    0
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_event_map(hw_event: CULong) -> CULong {
    let hw_event_map = core::ptr::addr_of!((*boot_param).hw_event_map).cast::<CULong>();
    *hw_event_map.add(hw_event as usize)
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_event_map(_hw_event: CULong) -> CULong {
    0
}

#[inline(always)]
fn cache_index(type_: usize, op: usize, result: usize) -> usize {
    (type_ * PERF_COUNT_HW_CACHE_OP_MAX * PERF_COUNT_HW_CACHE_RESULT_MAX)
        + (op * PERF_COUNT_HW_CACHE_RESULT_MAX)
        + result
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_cache_event_map(hw_cache_event: CULong) -> CULong {
    let type_ = ((hw_cache_event >> 0) & 0xff) as usize;
    if type_ >= PERF_COUNT_HW_CACHE_MAX {
        return 0;
    }
    let op = ((hw_cache_event >> 8) & 0xff) as usize;
    if op >= PERF_COUNT_HW_CACHE_OP_MAX {
        return 0;
    }
    let result = ((hw_cache_event >> 16) & 0xff) as usize;
    if result >= PERF_COUNT_HW_CACHE_RESULT_MAX {
        return 0;
    }

    let hw_cache_event_ids = core::ptr::addr_of!((*boot_param).hw_cache_event_ids).cast::<CULong>();
    let value = *hw_cache_event_ids.add(cache_index(type_, op, result));
    if value == CULong::MAX {
        0
    } else {
        value
    }
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_cache_event_map(_hw_cache_event: CULong) -> CULong {
    0
}

#[cfg(enable_perf)]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_cache_extra_reg_map(hw_cache_event: CULong) -> CULong {
    let type_ = ((hw_cache_event >> 0) & 0xff) as usize;
    if type_ >= PERF_COUNT_HW_CACHE_MAX {
        return 0;
    }
    let op = ((hw_cache_event >> 8) & 0xff) as usize;
    if op >= PERF_COUNT_HW_CACHE_OP_MAX {
        return 0;
    }
    let result = ((hw_cache_event >> 16) & 0xff) as usize;
    if result >= PERF_COUNT_HW_CACHE_RESULT_MAX {
        return 0;
    }

    let hw_cache_extra_regs =
        core::ptr::addr_of!((*boot_param).hw_cache_extra_regs).cast::<CULong>();
    let value = *hw_cache_extra_regs.add(cache_index(type_, op, result));
    if value == CULong::MAX {
        0
    } else {
        value
    }
}

#[cfg(not(enable_perf))]
#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_hw_cache_extra_reg_map(_hw_cache_event: CULong) -> CULong {
    0
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_raw_event_map(raw_event: CULong) -> CULong {
    #[cfg(enable_perf)]
    {
        raw_event
    }
    #[cfg(not(enable_perf))]
    {
        let _ = raw_event;
        0
    }
}

#[cfg_attr(not(mckernel_equivalence), no_mangle)]
pub unsafe extern "C" fn ihk_mc_validate_event(hw_config: CULong) -> CInt {
    #[cfg(enable_perf)]
    {
        (hw_config != 0) as CInt
    }
    #[cfg(not(enable_perf))]
    {
        let _ = hw_config;
        0
    }
}
