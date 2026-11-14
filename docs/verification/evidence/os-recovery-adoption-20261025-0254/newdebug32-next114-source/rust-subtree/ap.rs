use core::ffi::{c_char, c_void};
use core::mem::{offset_of, size_of};
use core::ptr::{null_mut, read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicI32, Ordering};

use crate::abi::{
    AbiListHead, CInt, CULong, CpuLocalVar, CpuSet, IhkAtomic, IhkSpinlock, McsLockNode, SSizeT,
    SizeT, SmpFuncCallData, SmpFuncCallRequest, SysfsHandle, SysfsOps,
};
use crate::list_helpers::{list_add_tail, list_del, list_empty, ListHead};

const EINVAL: CInt = 22;
const EIO: CInt = 5;
const ENOMEM: CInt = 12;
const ENOSPC: CInt = 28;
const IHK_MC_AP_CRITICAL: CInt = 0x000001;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const ONLINE: CInt = 0;

#[repr(C)]
pub(crate) struct IhkMcCpuInfo {
    pub(crate) ncpus: CInt,
    pub(crate) hw_ids: *mut CInt,
    pub(crate) nodes: *mut CInt,
    pub(crate) linux_cpu_ids: *mut CInt,
    pub(crate) ikc_cpus: *mut CInt,
}

#[repr(C)]
struct FakeCpuInfo {
    online: CInt,
}

#[repr(C)]
struct FakeCpuInfoOps {
    member: CInt,
    ops: SysfsOps,
}

#[no_mangle]
pub static mut num_processors: CInt = 1;

static mut AP_STOP: CInt = 1;

#[no_mangle]
pub static mut ap_syscall_semaphore: McsLockNode = McsLockNode {
    locked: 0,
    next: null_mut(),
    irqsave: 0,
};

#[no_mangle]
pub static mut show_int_ops: SysfsOps = SysfsOps {
    show: Some(show_int),
    store: None,
    release: None,
};

static mut FAKE_CPU_INFOS: *mut FakeCpuInfo = null_mut();

static mut SHOW_FCI_ONLINE: FakeCpuInfoOps = FakeCpuInfoOps {
    member: ONLINE,
    ops: SysfsOps {
        show: Some(show_fake_cpu_info),
        store: Some(store_fake_cpu_info),
        release: None,
    },
};

const _: () = {
    assert!(size_of::<IhkMcCpuInfo>() == 40);
    assert!(offset_of!(IhkMcCpuInfo, hw_ids) == 8);
    assert!(offset_of!(IhkMcCpuInfo, nodes) == 16);
    assert!(offset_of!(IhkMcCpuInfo, ikc_cpus) == 32);
    assert!(size_of::<FakeCpuInfo>() == 4);
    assert!(offset_of!(FakeCpuInfoOps, ops) == 8);
};

unsafe extern "C" {
    #[link_name = "panic"]
    fn kernel_panic(message: *const c_char) -> !;

    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn _kfree(ptr: *mut c_void, file: *mut c_char, line: CInt);
    fn arch_start_pvclock();
    fn cpu_pause();
    fn find_command_line(name: *const c_char) -> *mut c_char;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn ihk_atomic_dec(v: *mut IhkAtomic);
    fn ihk_atomic_set(v: *mut IhkAtomic, i: CInt);
    fn ihk_mc_boot_cpu(cpuid: CInt, pc: CULong);
    fn ihk_mc_get_cpu_info() -> *mut IhkMcCpuInfo;
    fn ihk_mc_get_hardware_processor_id() -> CInt;
    fn ihk_mc_get_ikc_cpu(id: CInt) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_get_smp_handler_irq() -> CInt;
    fn ihk_mc_init_ap();
    fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt;
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn init_delay();
    fn init_host_ikc2linux(ikc_cpu: CInt);
    fn init_host_ikc2mckernel();
    fn init_tick();
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn kmalloc_init();
    fn mc_ikc_test_init();
    fn mcs_lock_init(node: *mut McsLockNode);
    fn mcs_lock_lock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn mcs_lock_unlock_noirq(lock: *mut McsLockNode, node: *mut McsLockNode);
    fn sched_init();
    fn schedule();
    fn sync_tick();
    fn sysfs_createf(
        ops: *mut SysfsOps,
        instance: *mut c_void,
        mode: CInt,
        fmt: *const c_char,
        ...
    ) -> CInt;
    fn sysfs_lookupf(objhp: *mut SysfsHandle, fmt: *const c_char, ...) -> CInt;
    fn sysfs_symlinkf(targeth: SysfsHandle, fmt: *const c_char, ...) -> CInt;
}

#[inline(always)]
fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr().cast()
}

#[inline(always)]
unsafe fn kmalloc(size: usize, flags: CInt) -> *mut c_void {
    unsafe {
        _kmalloc(
            size as CInt,
            flags,
            cstr(b"kernel/rust/ap.rs\0") as *mut c_char,
            line!() as CInt,
        )
    }
}

#[inline(always)]
unsafe fn kfree(ptr: *mut c_void) {
    unsafe {
        _kfree(
            ptr,
            cstr(b"kernel/rust/ap.rs\0") as *mut c_char,
            line!() as CInt,
        );
    }
}

#[inline(always)]
unsafe fn list_head(entry: *mut AbiListHead) -> *mut ListHead {
    entry.cast()
}

#[inline(always)]
unsafe fn smp_func_req(req_list: *mut AbiListHead) -> *mut SmpFuncCallRequest {
    (req_list as usize).wrapping_sub(offset_of!(SmpFuncCallRequest, list))
        as *mut SmpFuncCallRequest
}

#[inline(always)]
fn cpu_set_has(cpu_set: &CpuSet, cpu: CInt) -> bool {
    if cpu < 0 {
        return false;
    }
    let cpu = cpu as usize;
    let word = cpu / (size_of::<CULong>() * 8);
    let bit = cpu % (size_of::<CULong>() * 8);
    word < cpu_set.bits.len() && ((cpu_set.bits[word] >> bit) & 1) != 0
}

unsafe extern "C" fn ap_wait() {
    unsafe {
        init_tick();
        while read_volatile(&raw const AP_STOP) != 0 {
            compiler_fence(Ordering::SeqCst);
            cpu_pause();
        }
        sync_tick();

        kmalloc_init();
        sched_init();
        arch_start_pvclock();

        if !find_command_line(cstr(b"hidos\0")).is_null() {
            let mut mcs_node: McsLockNode = core::mem::zeroed();
            let ikc_cpu = ihk_mc_get_ikc_cpu(ihk_mc_get_processor_id());
            if ikc_cpu < 0 {
                kprintf(
                    cstr(b"%s,ihk_mc_get_ikc_cpu failed\n\0"),
                    cstr(b"ap_wait\0"),
                );
            }
            mcs_lock_lock_noirq(&raw mut ap_syscall_semaphore, &raw mut mcs_node);
            init_host_ikc2mckernel();
            init_host_ikc2linux(ikc_cpu);
            mcs_lock_unlock_noirq(&raw mut ap_syscall_semaphore, &raw mut mcs_node);
        }

        mc_ikc_test_init();
        schedule();
    }
}

#[no_mangle]
pub unsafe extern "C" fn ap_start() {
    unsafe {
        init_tick();
        mcs_lock_init(&raw mut ap_syscall_semaphore);
        write_volatile(&raw mut AP_STOP, 0);
        sync_tick();
    }
}

#[no_mangle]
pub unsafe extern "C" fn ap_init() {
    unsafe {
        ihk_mc_init_ap();
        init_delay();

        let cpu_info = ihk_mc_get_cpu_info();
        let bsp_hw_id = ihk_mc_get_hardware_processor_id();
        if cpu_info.is_null() {
            return;
        }

        let mut bsp_cpu_id = 0;
        let mut i = 0;
        while i < (*cpu_info).ncpus {
            if *(*cpu_info).hw_ids.add(i as usize) == bsp_hw_id {
                bsp_cpu_id = i;
                break;
            }
            i += 1;
        }

        kprintf(
            cstr(b"BSP: %d (HW ID: %d @ NUMA %d)\n\0"),
            bsp_cpu_id,
            bsp_hw_id,
            *(*cpu_info).nodes,
        );

        i = 0;
        while i < (*cpu_info).ncpus {
            let hw_id = *(*cpu_info).hw_ids.add(i as usize);
            if hw_id != bsp_hw_id {
                ihk_mc_boot_cpu(hw_id, ap_wait as *const () as usize as CULong);
                num_processors += 1;
            }
            i += 1;
        }
        kprintf(cstr(b"BSP: booted %d AP CPUs\n\0"), (*cpu_info).ncpus - 1);
    }
}

unsafe extern "C" fn show_int(
    _ops: *mut SysfsOps,
    instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> SSizeT {
    unsafe {
        crate::numparse::snprintf(buf.cast(), size, cstr(b"%d\n\0"), *(instance as *mut CInt))
            as SSizeT
    }
}

unsafe extern "C" fn show_fake_cpu_info(
    ops0: *mut SysfsOps,
    instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> SSizeT {
    unsafe {
        let ops =
            (ops0 as usize).wrapping_sub(offset_of!(FakeCpuInfoOps, ops)) as *mut FakeCpuInfoOps;
        let info = instance as *mut FakeCpuInfo;
        let mut n = match (*ops).member {
            ONLINE => crate::numparse::snprintf(buf.cast(), size, cstr(b"%d\n\0"), (*info).online)
                as SSizeT,
            _ => -(EINVAL as SSizeT),
        };

        if (n as usize) >= size {
            n = -(ENOSPC as SSizeT);
        }
        n
    }
}

unsafe extern "C" fn store_fake_cpu_info(
    ops0: *mut SysfsOps,
    instance: *mut c_void,
    buf: *mut c_void,
    size: SizeT,
) -> SSizeT {
    unsafe {
        let ops =
            (ops0 as usize).wrapping_sub(offset_of!(FakeCpuInfoOps, ops)) as *mut FakeCpuInfoOps;
        let info = instance as *mut FakeCpuInfo;
        match (*ops).member {
            ONLINE => {
                kprintf(
                    cstr(b"NYI:store_fake_cpu_info(%p,%p,%p,%ld): online %d --> \"%.*s\"\n\0"),
                    ops0,
                    instance,
                    buf,
                    size as CULong,
                    (*info).online,
                    size as CInt,
                    buf,
                );
                size as SSizeT
            }
            _ => -(EIO as SSizeT),
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn cpu_sysfs_setup() {
    unsafe {
        let mut error = sysfs_createf(
            &raw mut show_int_ops,
            &raw mut num_processors as *mut c_void,
            0o444,
            cstr(b"/sys/devices/system/cpu/num_processors\0"),
        );
        if error != 0 {
            kernel_panic(cstr(
                b"cpu_sysfs_setup:sysfs_createf(num_processors) failed\n\0",
            ));
        }

        let info = kmalloc(
            size_of::<FakeCpuInfo>().wrapping_mul(num_processors as usize),
            IHK_MC_AP_CRITICAL,
        ) as *mut FakeCpuInfo;
        let mut cpu = 0;
        while cpu < num_processors {
            write_volatile(&raw mut (*info.add(cpu as usize)).online, 1);
            cpu += 1;
        }
        FAKE_CPU_INFOS = info;

        cpu = 0;
        while cpu < num_processors {
            error = sysfs_createf(
                &raw mut SHOW_FCI_ONLINE.ops,
                FAKE_CPU_INFOS.add(cpu as usize).cast(),
                0o644,
                cstr(b"/sys/devices/system/cpu/cpu%d/online\0"),
                cpu,
            );
            if error != 0 {
                kernel_panic(cstr(b"cpu_sysfs_setup:sysfs_createf failed\n\0"));
            }

            let mut targeth = SysfsHandle { handle: 0 };
            error = sysfs_lookupf(&mut targeth, cstr(b"/sys/devices/system/cpu/cpu%d\0"), cpu);
            if error != 0 {
                kernel_panic(cstr(b"cpu_sysfs_setup:sysfs_lookupf failed\n\0"));
            }

            let targeth_driver = SysfsHandle {
                handle: targeth.handle,
            };
            error = sysfs_symlinkf(targeth, cstr(b"/sys/bus/cpu/devices/cpu%d\0"), cpu);
            if error != 0 {
                kernel_panic(cstr(b"cpu_sysfs_setup:sysfs_symlinkf failed\n\0"));
            }

            error = sysfs_symlinkf(
                targeth_driver,
                cstr(b"/sys/bus/cpu/drivers/processor/cpu%d\0"),
                cpu,
            );
            if error != 0 {
                kernel_panic(cstr(b"cpu_sysfs_setup:sysfs_symlinkf failed\n\0"));
            }

            cpu += 1;
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn smp_func_call_handler() {
    unsafe {
        loop {
            let mut req: *mut SmpFuncCallRequest = null_mut();
            let mut reqs_left = 0;
            let local = get_cpu_local_var(ihk_mc_get_processor_id());
            let flags = __ihk_mc_spinlock_lock(&raw mut (*local).smp_func_req_lock);

            if list_empty(list_head(&raw mut (*local).smp_func_req_list)) == 0 {
                req = smp_func_req((*local).smp_func_req_list.next);
                list_del(list_head(&raw mut (*req).list));
                reqs_left =
                    (list_empty(list_head(&raw mut (*local).smp_func_req_list)) == 0) as CInt;
            }

            __ihk_mc_spinlock_unlock(&raw mut (*local).smp_func_req_lock, flags);

            if !req.is_null() {
                let sfcd = (*req).sfcd;
                if let Some(func) = (*sfcd).func {
                    (*req).ret = func((*req).cpu_index, (*sfcd).nr_cpus, (*sfcd).arg);
                }
                ihk_atomic_dec(&raw mut (*sfcd).cpus_left);
            }

            if reqs_left == 0 {
                break;
            }
        }
    }
}

#[no_mangle]
pub unsafe extern "C" fn smp_call_func(
    cpu_set: *mut CpuSet,
    func: Option<unsafe extern "C" fn(CInt, CInt, *mut c_void) -> CInt>,
    arg: *mut c_void,
) -> CInt {
    unsafe {
        if cpu_set.is_null() || func.is_none() {
            return -EINVAL;
        }

        let cpu_set_copy = read_volatile(cpu_set);
        let mut nr_cpus = 0;
        let mut cpu = 0;
        let mut call_on_this_cpu = 0;
        let max_nr_cpus = 4;
        let current_cpu = ihk_mc_get_processor_id();

        while cpu < 1024 {
            if cpu_set_has(&cpu_set_copy, cpu) {
                if cpu == current_cpu {
                    call_on_this_cpu = 1;
                }
                nr_cpus += 1;
                if nr_cpus == max_nr_cpus {
                    break;
                }
            }
            cpu += 1;
        }

        if nr_cpus == 0 {
            return -EINVAL;
        }

        let reqs = kmalloc(
            size_of::<SmpFuncCallRequest>().wrapping_mul(nr_cpus as usize),
            IHK_MC_AP_NOWAIT,
        ) as *mut SmpFuncCallRequest;
        if reqs.is_null() {
            return -ENOMEM;
        }

        kprintf(
            cstr(b"%s: interrupting %d CPUs for SMP call..\n\0"),
            cstr(b"smp_call_func\0"),
            nr_cpus,
        );

        let mut sfcd = SmpFuncCallData {
            nr_cpus,
            cpus_left: IhkAtomic { counter: 0 },
            func,
            arg,
        };
        ihk_atomic_set(
            &mut sfcd.cpus_left,
            nr_cpus - if call_on_this_cpu != 0 { 1 } else { 0 },
        );
        compiler_fence(Ordering::SeqCst);

        let mut cpu_index = 0;
        let mut this_cpu_index = 0;
        cpu = 0;
        while cpu < 1024 {
            if cpu_set_has(&cpu_set_copy, cpu) {
                let req = reqs.add(cpu_index as usize);
                (*req).cpu_index = cpu_index;
                (*req).ret = 0;

                if cpu == current_cpu {
                    this_cpu_index = cpu_index;
                    cpu_index += 1;
                    if cpu_index == max_nr_cpus {
                        break;
                    }
                    cpu += 1;
                    continue;
                }

                (*req).sfcd = &mut sfcd;
                let target = get_cpu_local_var(cpu);
                let flags = __ihk_mc_spinlock_lock(&raw mut (*target).smp_func_req_lock);
                list_add_tail(
                    list_head(&raw mut (*req).list),
                    list_head(&raw mut (*target).smp_func_req_list),
                );
                __ihk_mc_spinlock_unlock(&raw mut (*target).smp_func_req_lock, flags);

                ihk_mc_interrupt_cpu(cpu, ihk_mc_get_smp_handler_irq());

                cpu_index += 1;
                if cpu_index == max_nr_cpus {
                    break;
                }
            }
            cpu += 1;
        }

        if call_on_this_cpu != 0 {
            if let Some(f) = func {
                (*reqs.add(this_cpu_index as usize)).ret = f(this_cpu_index, nr_cpus, arg);
            }
        }

        while AtomicI32::from_ptr(&mut sfcd.cpus_left.counter).load(Ordering::Acquire) > 0 {
            cpu_pause();
        }

        let mut ret = 0;
        cpu_index = 0;
        while cpu_index < nr_cpus {
            let req_ret = (*reqs.add(cpu_index as usize)).ret;
            if req_ret != 0 {
                ret = req_ret;
                break;
            }
            cpu_index += 1;
        }

        if ret == 0 {
            kprintf(
                cstr(b"%s: all CPUs finished SMP call successfully\n\0"),
                cstr(b"smp_call_func\0"),
            );
        }

        kfree(reqs.cast());
        ret
    }
}
