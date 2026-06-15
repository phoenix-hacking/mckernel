use core::{
    ffi::{c_char, c_void},
    mem::{offset_of, size_of},
    ptr::{null_mut, read_volatile},
    sync::atomic::{fence, AtomicI32, Ordering},
};

use crate::abi::{
    AbiListHead, Backlog, CInt, CULong, CpuLocalVar, IhkMcMemoryArea, IhkOsMonitor, IhkSpinlock,
    Process, ProcessVm, RusagePercpu, Thread, IHK_MAX_NUM_CPUS, IHK_MAX_NUM_NUMA_NODES,
    IHK_MAX_NUM_PGSIZES,
};

const ENOMEM: CInt = 12;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const IHK_MC_AP_CRITICAL: CInt = 0x000001;
const PAGE_SHIFT: usize = 12;
const PAGE_SIZE: usize = 1 << PAGE_SHIFT;
const CPU_FLAG_NEED_RESCHED: u32 = 0x1;
const CLS_FILE: &[u8] = b"kernel/rust/cls.rs\0";

#[repr(C)]
struct RusageGlobal {
    memory_stat_rss: [i64; IHK_MAX_NUM_PGSIZES],
    memory_stat_mapped_file: [i64; IHK_MAX_NUM_PGSIZES],
    rss_current: i64,
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

extern "C" {
    static num_processors: CInt;
    static mut monitor: *mut IhkOsMonitor;
    static mut rusage: RusageGlobal;

    fn ihk_mc_get_processor_id() -> CInt;
    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn _ihk_mc_alloc_aligned_pages_node(
        size: CInt,
        align: CInt,
        flags: CULong,
        zero: CInt,
        node: CInt,
        virt: CULong,
        file: *mut c_char,
        line: CInt,
    ) -> *mut c_void;
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, irqstate: CULong);
    fn set_timer(runq_locked: CInt);
}

#[no_mangle]
pub static mut clv: *mut CpuLocalVar = null_mut();

#[no_mangle]
pub static mut cpu_local_var_initialized: CInt = 0;

#[inline(always)]
fn file_ptr() -> *mut c_char {
    CLS_FILE.as_ptr() as *mut c_char
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn list_empty(head: *mut AbiListHead) -> bool {
    read_volatile(&(*head).next) == head
}

#[inline(always)]
unsafe fn list_add_tail(new: *mut AbiListHead, head: *mut AbiListHead) {
    let prev = read_volatile(&(*head).prev);
    (*new).next = head;
    (*new).prev = prev;
    (*prev).next = new;
    (*head).prev = new;
}

#[inline(always)]
unsafe fn list_del(entry: *mut AbiListHead) {
    let prev = read_volatile(&(*entry).prev);
    let next = read_volatile(&(*entry).next);
    (*prev).next = next;
    (*next).prev = prev;
    init_list_head(entry);
}

#[inline(always)]
unsafe fn backlog_from_list(entry: *mut AbiListHead) -> *mut Backlog {
    entry
        .cast::<u8>()
        .sub(offset_of!(Backlog, list))
        .cast::<Backlog>()
}

#[inline(always)]
unsafe fn atomic_counter(counter: *mut crate::abi::IhkAtomic) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*counter).counter)
}

#[inline(always)]
unsafe fn this_cpu_local_var() -> *mut CpuLocalVar {
    get_cpu_local_var(ihk_mc_get_processor_id())
}

#[no_mangle]
pub unsafe extern "C" fn cpu_local_var_init() {
    let bytes = size_of::<CpuLocalVar>() * (num_processors as usize);
    let nr_pages = (bytes + PAGE_SIZE - 1) >> PAGE_SHIFT;
    let base = _ihk_mc_alloc_aligned_pages_node(
        nr_pages as CInt,
        0,
        IHK_MC_AP_CRITICAL as CULong,
        0,
        -1,
        0,
        file_ptr(),
        line!() as CInt,
    )
    .cast::<CpuLocalVar>();

    clv = base;
    core::ptr::write_bytes(base.cast::<u8>(), 0, nr_pages * PAGE_SIZE);

    let monitor_cpu = monitor
        .cast::<u8>()
        .add(size_of::<IhkOsMonitor>())
        .cast::<crate::abi::IhkOsCpuMonitor>();
    let rusage_cpu = core::ptr::addr_of_mut!(rusage.cpu).cast::<RusagePercpu>();

    let mut cpu = 0;
    while cpu < num_processors {
        let v = base.add(cpu as usize);
        (*v).monitor = monitor_cpu.add(cpu as usize);
        (*v).rusage = rusage_cpu.add(cpu as usize);
        init_list_head(&raw mut (*v).smp_func_req_list);
        init_list_head(&raw mut (*v).backlog_list);
        #[cfg(enable_per_cpu_alloc_cache)]
        {
            (*v).free_chunks.rb_node = null_mut();
        }
        cpu += 1;
    }

    cpu_local_var_initialized = 1;
    fence(Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar {
    clv.add(id as usize)
}

#[no_mangle]
pub unsafe extern "C" fn get_this_cpu_local_var() -> *mut CpuLocalVar {
    this_cpu_local_var()
}

#[no_mangle]
pub unsafe extern "C" fn preempt_enable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_sub(1, Ordering::SeqCst);
    }
}

#[no_mangle]
pub unsafe extern "C" fn preempt_disable() {
    if cpu_local_var_initialized != 0 {
        let v = this_cpu_local_var();
        atomic_counter(&raw mut (*v).no_preempt).fetch_add(1, Ordering::SeqCst);
    }
}

#[no_mangle]
pub unsafe extern "C" fn add_backlog(
    func: Option<unsafe extern "C" fn(*mut c_void) -> CInt>,
    arg: *mut c_void,
) -> CInt {
    let Some(func) = func else {
        return -ENOMEM;
    };
    let bl = _kmalloc(
        size_of::<Backlog>() as CInt,
        IHK_MC_AP_NOWAIT,
        file_ptr(),
        line!() as CInt,
    )
    .cast::<Backlog>();
    if bl.is_null() {
        return -ENOMEM;
    }

    init_list_head(&raw mut (*bl).list);
    (*bl).func = Some(func);
    (*bl).arg = arg;

    let v = this_cpu_local_var();
    let mut irqstate = __ihk_mc_spinlock_lock(&raw mut (*v).backlog_lock);
    list_add_tail(&raw mut (*bl).list, &raw mut (*v).backlog_list);
    __ihk_mc_spinlock_unlock(&raw mut (*v).backlog_lock, irqstate);

    irqstate = __ihk_mc_spinlock_lock(&raw mut (*v).runq_lock);
    (*v).flags |= CPU_FLAG_NEED_RESCHED;
    __ihk_mc_spinlock_unlock(&raw mut (*v).runq_lock, irqstate);
    set_timer(0);
    0
}

#[no_mangle]
pub unsafe extern "C" fn do_backlog() {
    let v = this_cpu_local_var();
    let mut local = AbiListHead {
        next: null_mut(),
        prev: null_mut(),
    };
    init_list_head(&raw mut local);

    let mut irqstate = __ihk_mc_spinlock_lock(&raw mut (*v).backlog_lock);
    while !list_empty(&raw mut (*v).backlog_list) {
        let entry = read_volatile(&(*(&raw mut (*v).backlog_list)).next);
        list_del(entry);
        list_add_tail(entry, &raw mut local);
    }
    __ihk_mc_spinlock_unlock(&raw mut (*v).backlog_lock, irqstate);

    while !list_empty(&raw mut local) {
        let entry = read_volatile(&local.next);
        let bl = backlog_from_list(entry);
        list_del(entry);

        let retry = match (*bl).func {
            Some(func) => func((*bl).arg) != 0,
            None => false,
        };
        if retry {
            irqstate = __ihk_mc_spinlock_lock(&raw mut (*v).backlog_lock);
            list_add_tail(&raw mut (*bl).list, &raw mut (*v).backlog_list);
            __ihk_mc_spinlock_unlock(&raw mut (*v).backlog_lock, irqstate);
        } else {
            _kfree(bl.cast::<c_void>(), file_ptr(), line!() as CInt);
        }
    }
}

#[cfg(enable_fugaku_hacks)]
#[no_mangle]
pub unsafe extern "C" fn get_this_cpu_runq_lock() -> *mut IhkSpinlock {
    &raw mut (*this_cpu_local_var()).runq_lock
}

const _: () = {
    let _ = size_of::<Thread>();
    let _ = size_of::<Process>();
    let _ = size_of::<ProcessVm>();
    let _ = size_of::<IhkMcMemoryArea>();
};
