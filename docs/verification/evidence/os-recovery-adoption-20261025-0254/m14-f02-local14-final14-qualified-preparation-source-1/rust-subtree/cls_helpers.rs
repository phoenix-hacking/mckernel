use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::write_bytes;
use core::sync::atomic::{fence, AtomicI32, Ordering};

use crate::abi::{AbiListHead, CInt, CpuLocalVar, IhkOsCpuMonitor, RusagePercpu};

const PAGE_SHIFT: usize = 12;
const PAGE_SIZE: usize = 1 << PAGE_SHIFT;
const IHK_MC_AP_CRITICAL: CInt = 0x000001;

type ClsAllocPagesFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;

unsafe extern "C" {
    static mut clv: *mut CpuLocalVar;
    static mut cpu_local_var_initialized: CInt;

    fn ihk_mc_get_processor_id() -> CInt;
}

#[inline(always)]
unsafe fn init_list_head(head: *mut AbiListHead) {
    (*head).next = head;
    (*head).prev = head;
}

#[inline(always)]
unsafe fn atomic_counter(counter: *mut crate::abi::IhkAtomic) -> &'static AtomicI32 {
    AtomicI32::from_ptr(&raw mut (*counter).counter)
}

#[no_mangle]
pub unsafe extern "C" fn cpu_local_var_init_result(
    num_processors: CInt,
    monitor_cpu: *mut IhkOsCpuMonitor,
    rusage_cpu: *mut RusagePercpu,
    alloc_pages: Option<ClsAllocPagesFn>,
) {
    let alloc_pages = match alloc_pages {
        Some(alloc_pages) => alloc_pages,
        None => return,
    };
    let bytes = size_of::<CpuLocalVar>() * (num_processors as usize);
    let nr_pages = (bytes + PAGE_SIZE - 1) >> PAGE_SHIFT;
    let base = alloc_pages(nr_pages as CInt, IHK_MC_AP_CRITICAL).cast::<CpuLocalVar>();

    clv = base;
    write_bytes(base.cast::<u8>(), 0, nr_pages * PAGE_SIZE);

    let mut cpu = 0;
    while cpu < num_processors {
        let v = base.add(cpu as usize);

        (*v).monitor = monitor_cpu.add(cpu as usize);
        (*v).rusage = rusage_cpu.add(cpu as usize);
        init_list_head(&raw mut (*v).smp_func_req_list);
        init_list_head(&raw mut (*v).backlog_list);
        #[cfg(enable_per_cpu_alloc_cache)]
        {
            (*v).free_chunks.rb_node = core::ptr::null_mut();
        }

        cpu += 1;
    }

    cpu_local_var_initialized = 1;
    fence(Ordering::SeqCst);
}

#[no_mangle]
pub unsafe extern "C" fn get_cpu_local_var_result(id: CInt) -> *mut CpuLocalVar {
    clv.add(id as usize)
}

#[no_mangle]
pub unsafe extern "C" fn preempt_enable_result() {
    if cpu_local_var_initialized != 0 {
        let cpu = ihk_mc_get_processor_id();
        let v = get_cpu_local_var_result(cpu);
        atomic_counter(&raw mut (*v).no_preempt).fetch_sub(1, Ordering::SeqCst);
    }
}

#[no_mangle]
pub unsafe extern "C" fn preempt_disable_result() {
    if cpu_local_var_initialized != 0 {
        let cpu = ihk_mc_get_processor_id();
        let v = get_cpu_local_var_result(cpu);
        atomic_counter(&raw mut (*v).no_preempt).fetch_add(1, Ordering::SeqCst);
    }
}
