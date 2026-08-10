use core::ffi::{c_char, c_void};
use core::mem::size_of;
use core::ptr::{null_mut, write_volatile};

use crate::abi::{
    CInt, CLong, CULong, IhkOsMonitor, RusagePercpu, SysfsBitmapParam, SysfsOps, IHK_MAX_NUM_CPUS,
    IHK_MAX_NUM_NUMA_NODES, IHK_MAX_NUM_PGSIZES,
};
use crate::ap::IhkMcCpuInfo;

const DUMP_LEVEL_USER_UNUSED_EXCLUDE: CULong = 24;
const IHK_MC_AP_CRITICAL: CInt = 1;
const IHK_MC_PG_KERNEL: CInt = 0;
const NS_PER_SEC: CLong = 1_000_000_000;
const PAGE_P2ALIGN: CInt = 0;
const PAGE_SHIFT: usize = 12;
const PAGE_SIZE: usize = 1 << PAGE_SHIFT;

#[repr(C, align(32))]
pub struct RusageGlobal {
    memory_stat_rss: [CLong; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [CLong; IHK_MAX_NUM_PGSIZES],
    rss_current: CLong,
    memory_max_usage: CULong,
    max_num_threads: CULong,
    num_threads: CULong,
    memory_kmem_usage: CULong,
    memory_kmem_max_usage: CULong,
    memory_numa_stat: [CULong; IHK_MAX_NUM_NUMA_NODES],
    cpu: [RusagePercpu; IHK_MAX_NUM_CPUS],
    total_memory: CULong,
    total_memory_usage: CULong,
    total_memory_max_usage: CULong,
    num_numa_nodes: CULong,
    num_processors: CULong,
    ns_per_tsc: CULong,
}

#[repr(align(64))]
#[allow(dead_code)]
pub struct InitData([CULong; 1024]);

type SyscallHandler = unsafe extern "C" fn(CInt, *mut c_void) -> CLong;

unsafe extern "C" {
    static mut allow_oversubscribe: CInt;
    static mut gettime_local_support: CInt;
    static mut idle_halt: CInt;
    static mut time_sharing: CInt;

    fn ap_init();
    fn ap_start();
    fn arch_init();
    fn arch_ready();
    fn arch_setup_vdso();
    fn arch_start_pvclock();
    fn cpu_enable_interrupt();
    fn cpu_local_var_init();
    fn cpu_pause();
    fn dynamic_debug_sysfs_setup();
    fn done_init();
    fn find_command_line(name: *const c_char) -> *mut c_char;
    fn futex_init();
    fn ihk_ikc_master_init();
    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut c_char,
        line: CInt,
    ) -> *mut c_void;
    fn ihk_mc_get_boot_time(tv_sec: *mut CULong, tv_nsec: *mut CULong, tsc: *mut CULong);
    fn ihk_mc_get_cpu_info() -> *mut IhkMcCpuInfo;
    fn ihk_mc_get_ikc_cpu(cpu: CInt) -> CInt;
    fn ihk_mc_get_ns_per_tsc() -> CULong;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_set_dump_level(level: CULong);
    fn ihk_mc_set_syscall_handler(handler: SyscallHandler);
    fn ihk_set_monitor(addr: CULong, size: CULong) -> CInt;
    fn ihk_set_multi_intr_mode_addr(addr: CULong) -> CInt;
    fn ihk_set_nmi_mode_addr(addr: CULong) -> CInt;
    fn ihk_get_kargs() -> *mut c_char;
    fn init_host_ikc2linux(ikc_cpu: CInt);
    fn init_host_ikc2mckernel();
    fn kmalloc_init();
    fn kprintf(fmt: *const c_char, ...) -> CInt;
    fn kputs(s: *const c_char);
    #[link_name = "panic"]
    fn kernel_panic(s: *const c_char) -> !;
    fn mem_init();
    fn numa_sysfs_setup();
    fn phys_to_virt(phys: CULong) -> *mut c_void;
    fn proc_init();
    fn sched_init();
    fn schedule();
    fn syscall(num: CInt, ctx: *mut c_void) -> CLong;
    fn sysfs_createf(
        ops: *mut SysfsOps,
        instance: *mut c_void,
        mode: CInt,
        path: *const c_char,
        ...
    ) -> CInt;
    fn sysfs_init();
    fn virt_to_phys(ptr: *mut c_void) -> CULong;

    #[cfg(enable_tofu)]
    fn tof_utofu_init_globals();
}

#[no_mangle]
pub static mut monitor: *mut IhkOsMonitor = null_mut();

#[no_mangle]
pub static mut rusage: RusageGlobal = RusageGlobal {
    memory_stat_rss: [0; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [0; IHK_MAX_NUM_PGSIZES],
    rss_current: 0,
    memory_max_usage: 0,
    max_num_threads: 0,
    num_threads: 0,
    memory_kmem_usage: 0,
    memory_kmem_max_usage: 0,
    memory_numa_stat: [0; IHK_MAX_NUM_NUMA_NODES],
    cpu: [RusagePercpu {
        user_tsc: 0,
        system_tsc: 0,
    }; IHK_MAX_NUM_CPUS],
    total_memory: 0,
    total_memory_usage: 0,
    total_memory_max_usage: 0,
    num_numa_nodes: 0,
    num_processors: 0,
    ns_per_tsc: 0,
};

#[no_mangle]
pub static mut mck_num_processors: *mut CInt = &raw mut crate::ap::num_processors;

#[no_mangle]
pub static mut data: InitData = InitData([0; 1024]);

#[no_mangle]
pub static mut multi_intr_mode: CInt = 0;

#[no_mangle]
pub static mut nmi_mode: CInt = 0;

#[no_mangle]
pub static mut host_ikc_inited: CInt = 0;

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr().cast::<c_char>()
}

unsafe fn handler_init() {
    ihk_mc_set_syscall_handler(syscall);
}

unsafe fn parse_decimal(ptr: *mut c_char) -> CULong {
    let mut p = ptr.cast::<u8>();
    let mut value = 0;
    while unsafe { *p }.is_ascii_digit() {
        value = value * 10 + unsafe { (*p - b'0') as CULong };
        p = unsafe { p.add(1) };
    }
    value
}

unsafe fn parse_kargs() {
    let key_dump_level = b"dump_level=\0";
    let mut dump_level = DUMP_LEVEL_USER_UNUSED_EXCLUDE;

    unsafe {
        kprintf(cstr(b"KCommand Line: %s\n\0"), ihk_get_kargs());
        crate::x86_setup::early_phase(b'j');
    }

    let ptr = unsafe { find_command_line(key_dump_level.as_ptr().cast::<c_char>()) };
    if !ptr.is_null() {
        dump_level = unsafe { parse_decimal(ptr.add(key_dump_level.len() - 1)) };
    }
    unsafe {
        ihk_mc_set_dump_level(dump_level);
        crate::x86_setup::early_phase(b'k');
    }

    if !unsafe { find_command_line(cstr(b"idle_halt\0")) }.is_null() {
        unsafe {
            idle_halt = 1;
        }
    }
    unsafe {
        crate::x86_setup::early_phase(b'l');
    }

    if !unsafe { find_command_line(cstr(b"allow_oversubscribe\0")) }.is_null() {
        unsafe {
            allow_oversubscribe = 1;
        }
    }
    unsafe {
        crate::x86_setup::early_phase(b'm');
    }

    if !unsafe { find_command_line(cstr(b"time_sharing\0")) }.is_null() {
        unsafe {
            time_sharing = 1;
        }
    }
    unsafe {
        crate::x86_setup::early_phase(b'n');
    }
}

unsafe fn time_init() {
    let mut tv_sec = 0;
    let mut tv_nsec = 0;
    let mut tsc = 0;

    unsafe {
        ihk_mc_get_boot_time(&mut tv_sec, &mut tv_nsec, &mut tsc);
    }
    let ns_per_kclock = unsafe { ihk_mc_get_ns_per_tsc() };

    unsafe {
        crate::x86_vsyscall::tod_data.origin.tv_sec = tv_sec as CLong;
        crate::x86_vsyscall::tod_data.origin.tv_nsec = tv_nsec as CLong;
    }

    if ns_per_kclock != 0 {
        unsafe {
            let clocks_per_sec = (1000 * NS_PER_SEC as CULong) / ns_per_kclock;
            crate::x86_vsyscall::tod_data.clocks_per_sec = clocks_per_sec;

            if clocks_per_sec == 0 {
                gettime_local_support = 0;
                return;
            }

            crate::x86_vsyscall::tod_data.origin.tv_sec -= (tsc / clocks_per_sec) as CLong;
            crate::x86_vsyscall::tod_data.origin.tv_nsec -=
                (NS_PER_SEC as CULong * (tsc % clocks_per_sec) / clocks_per_sec) as CLong;
            if crate::x86_vsyscall::tod_data.origin.tv_nsec < 0 {
                crate::x86_vsyscall::tod_data.origin.tv_sec -= 1;
                crate::x86_vsyscall::tod_data.origin.tv_nsec += NS_PER_SEC;
            }
        }
    }

    if ns_per_kclock == 0 {
        unsafe {
            gettime_local_support = 0;
        }
    }

    if unsafe { gettime_local_support } != 0 {
        unsafe {
            crate::x86_vsyscall::tod_data.do_local = 1;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn monitor_init() {
    unsafe {
        crate::x86_setup::early_phase(b'6');
    }
    let cpu_info = unsafe { ihk_mc_get_cpu_info() };
    if cpu_info.is_null() {
        unsafe {
            crate::x86_setup::early_panic();
            kernel_panic(cstr(b"PANIC: in monitor_init() ihk_mc_cpu_info is NULL.\0"));
        }
    }

    let bytes = size_of::<IhkOsMonitor>().wrapping_add(
        size_of::<crate::abi::IhkOsCpuMonitor>() * unsafe { (*cpu_info).ncpus as usize },
    );
    let pages = ((bytes + PAGE_SIZE - 1) >> PAGE_SHIFT) as CInt;
    unsafe {
        crate::x86_setup::early_phase(b'7');
    }
    let monitor_ptr = unsafe {
        _ihk_mc_alloc_aligned_pages_node(
            pages,
            PAGE_P2ALIGN,
            IHK_MC_AP_CRITICAL as CULong,
            -1,
            IHK_MC_PG_KERNEL,
            CULong::MAX,
            cstr(b"kernel/rust/init.rs\0").cast_mut(),
            line!() as CInt,
        )
    }
    .cast::<IhkOsMonitor>();
    unsafe {
        crate::x86_setup::early_phase(b'8');
        if monitor_ptr.is_null() {
            crate::x86_setup::early_panic();
            kernel_panic(cstr(b"PANIC: monitor_init() allocation failed.\0"));
        }
        if pages <= 0 {
            crate::x86_setup::early_panic();
            kernel_panic(cstr(b"PANIC: monitor_init() invalid page count.\0"));
        }
        let Some(span) = (pages as usize).checked_mul(PAGE_SIZE) else {
            crate::x86_setup::early_panic();
            kernel_panic(cstr(b"PANIC: monitor_init() page span overflow.\0"));
        };
        let probe_phys = virt_to_phys(monitor_ptr.cast::<c_void>());
        let canonical_ptr = phys_to_virt(probe_phys).cast::<u8>();
        kprintf(
            cstr(
                b"monitor_init: ptr=%lx phys=%lx canonical=%lx pages=%d bytes=%lu ncpus=%d\n\0",
            ),
            monitor_ptr as CULong,
            probe_phys,
            canonical_ptr as CULong,
            pages,
            bytes as CULong,
            (*cpu_info).ncpus,
        );
        crate::x86_setup::early_phase(b'.');
        write_volatile(canonical_ptr, 0);
        crate::x86_setup::early_phase(b':');
        write_volatile(canonical_ptr.add(span - 1), 0);
        crate::x86_setup::early_phase(b';');
        write_volatile(monitor_ptr.cast::<u8>(), 0);
        crate::x86_setup::early_phase(b'<');
        write_volatile(monitor_ptr.cast::<u8>().add(span - 1), 0);
        crate::x86_setup::early_phase(b'=');
        let raw_ptr = monitor_ptr.cast::<u8>();
        let mut offset = 0usize;
        while offset < span {
            write_volatile(raw_ptr.add(offset), 0);
            offset += 1;
        }
        crate::x86_setup::early_phase(b'>');
        (*monitor_ptr).num_processors = (*cpu_info).ncpus as CULong;
        crate::x86_setup::early_phase(b'/');
        monitor = monitor_ptr;
        crate::x86_setup::early_phase(b'9');
        let phys = virt_to_phys(monitor_ptr.cast::<c_void>());
        crate::x86_setup::early_phase(b'0');
        ihk_set_monitor(phys, bytes as CULong);
        crate::x86_setup::early_phase(b'+');
    }
}

unsafe fn multi_intr_init() {
    let phys = unsafe { virt_to_phys((&raw mut multi_intr_mode).cast::<c_void>()) };
    unsafe {
        ihk_set_multi_intr_mode_addr(phys);
    }
}

unsafe fn nmi_init() {
    let phys = unsafe { virt_to_phys((&raw mut nmi_mode).cast::<c_void>()) };
    unsafe {
        ihk_set_nmi_mode_addr(phys);
    }
}

unsafe fn uti_init() {}

unsafe fn rest_init() {
    unsafe {
        handler_init();
        crate::x86_setup::early_phase(b'M');
        ap_init();
        crate::x86_setup::early_phase(b'N');
        cpu_local_var_init();
        crate::x86_setup::early_phase(b'O');
        multi_intr_init();
        crate::x86_setup::early_phase(b'P');
        nmi_init();
        crate::x86_setup::early_phase(b'Q');
        uti_init();
        crate::x86_setup::early_phase(b'R');
        time_init();
        crate::x86_setup::early_phase(b'S');
        kmalloc_init();
        crate::x86_setup::early_phase(b'T');
        ihk_ikc_master_init();
        crate::x86_setup::early_phase(b'U');
        proc_init();
        crate::x86_setup::early_phase(b'V');
        sched_init();
        crate::x86_setup::early_phase(b'W');
    }
}

#[allow(dead_code)]
unsafe fn setup_remote_snooping_samples() {
    static mut LVALUE: CLong = 0xf123_4567_89ab_cde0u64 as CLong;
    static mut SVALUE: *const c_char = c"string(remote)".as_ptr();

    let mut error = unsafe {
        sysfs_createf(
            1usize as *mut SysfsOps,
            (&raw mut LVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/d32\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: d32\0"));
        }
    }

    error = unsafe {
        sysfs_createf(
            2usize as *mut SysfsOps,
            (&raw mut LVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/d64\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: d64\0"));
        }
    }

    error = unsafe {
        sysfs_createf(
            3usize as *mut SysfsOps,
            (&raw mut LVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/u32\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: u32\0"));
        }
    }

    error = unsafe {
        sysfs_createf(
            4usize as *mut SysfsOps,
            (&raw mut LVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/u64\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: u64\0"));
        }
    }

    error = unsafe {
        sysfs_createf(
            5usize as *mut SysfsOps,
            (&raw mut SVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/s\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: s\0"));
        }
    }

    let mut param = SysfsBitmapParam {
        nbits: 40,
        padding: 0,
        ptr: (&raw mut LVALUE).cast::<c_void>(),
    };
    error = unsafe {
        sysfs_createf(
            6usize as *mut SysfsOps,
            (&mut param as *mut SysfsBitmapParam).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/pbl\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: pbl\0"));
        }
    }

    param.nbits = 40;
    param.ptr = (&raw mut LVALUE).cast::<c_void>();
    error = unsafe {
        sysfs_createf(
            7usize as *mut SysfsOps,
            (&mut param as *mut SysfsBitmapParam).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/pb\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: pb\0"));
        }
    }

    error = unsafe {
        sysfs_createf(
            8usize as *mut SysfsOps,
            (&raw mut LVALUE).cast::<c_void>(),
            0o444,
            cstr(b"/sys/test/remote/u32K\0"),
        )
    };
    if error != 0 {
        unsafe {
            kernel_panic(cstr(b"setup_remote_snooping_samples: u32K\0"));
        }
    }
}

unsafe fn populate_sysfs() {
    unsafe {
        crate::ap::cpu_sysfs_setup();
        numa_sysfs_setup();
        dynamic_debug_sysfs_setup();
    }
}

unsafe fn post_init() {
    unsafe {
        cpu_enable_interrupt();
    }

    while unsafe { host_ikc_inited } == 0 {
        core::sync::atomic::compiler_fence(core::sync::atomic::Ordering::SeqCst);
        unsafe {
            cpu_pause();
        }
    }

    if !unsafe { find_command_line(cstr(b"hidos\0")) }.is_null() {
        let ikc_cpu = unsafe { ihk_mc_get_ikc_cpu(ihk_mc_get_processor_id()) };
        if ikc_cpu < 0 {
            unsafe {
                kprintf(
                    cstr(b"%s,ihk_mc_get_ikc_cpu failed\n\0"),
                    cstr(b"post_init\0"),
                );
            }
        }
        unsafe {
            init_host_ikc2mckernel();
            init_host_ikc2linux(ikc_cpu);
        }
    }

    unsafe {
        arch_setup_vdso();
        arch_start_pvclock();
        ap_start();
        sysfs_init();
        populate_sysfs();
    }
    #[cfg(enable_tofu)]
    unsafe {
        tof_utofu_init_globals();
    }
}

#[no_mangle]
pub unsafe extern "C" fn main() -> CInt {
    unsafe {
        arch_init();
        crate::x86_setup::early_phase(b'H');
        parse_kargs();
        crate::x86_setup::early_phase(b'I');
        mem_init();
        crate::x86_setup::early_phase(b'J');
        rest_init();
        crate::x86_setup::early_phase(b'X');
        arch_ready();
        crate::x86_setup::early_phase(b'Y');
        post_init();
        crate::x86_setup::early_phase(b'Z');
        futex_init();
        done_init();
        kputs(cstr(b"IHK/McKernel booted.\n\0"));
        schedule();
    }

    0
}
