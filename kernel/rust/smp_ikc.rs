use core::ffi::c_void;
use core::ptr::null_mut;
#[cfg(not(native_linux_irq_work_v6_12))]
use core::ptr::read_volatile;
#[cfg(native_linux_irq_work_v6_12)]
use core::sync::atomic::{AtomicU32, AtomicU8, Ordering};

use crate::abi::{CInt, CULong};
use crate::llist::{LListHead, LListNode};
use crate::spinlock_helpers::IhkSpinlock;

const SMP_MAX_CPUS: usize = 512;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const IHK_GV_IKC: CInt = 1;
const IRQ_WORK_BUSY: CULong = 2;

#[repr(C)]
#[cfg(not(native_linux_irq_work_v6_12))]
pub struct LinuxIrqWork {
    flags: CULong,
    llnode: LListNode,
    func: Option<unsafe extern "C" fn(*mut LinuxIrqWork)>,
    padding: [i8; 40],
}

/// Linux 6.12's irq_work header, retained in the guest's 64-byte slot.
/// The trailing padding is private; Linux's node, callback and irqwait fields
/// must match the pinned control kernel before publishing any work item.
#[repr(C)]
#[cfg(native_linux_irq_work_v6_12)]
pub struct LinuxIrqWork {
    llnode: LListNode,
    flags: AtomicU32,
    source: u16,
    destination: u16,
    func: Option<unsafe extern "C" fn(*mut LinuxIrqWork)>,
    irqwait: *mut c_void,
    padding: [u8; 32],
}

#[cfg(native_linux_irq_work_v6_12)]
static IRQ_WORK_INITIALIZATION: AtomicU8 = AtomicU8::new(0);
#[cfg(native_linux_irq_work_v6_12)]
static IRQ_WORK_PROCESSORS: AtomicU32 = AtomicU32::new(0);

#[repr(C)]
struct SmpBootParamPrefix {
    start: CULong,
    end: CULong,
    status: CULong,
    param_size: CInt,
    _pad0: CInt,
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
    ikc_irq_work_func: Option<unsafe extern "C" fn(*mut LinuxIrqWork)>,
    ihk_ikc_irq: u32,
}

type IkcPacketHandler =
    Option<unsafe extern "C" fn(*mut IhkIkcChannelDesc, *mut c_void, *mut c_void) -> CInt>;

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
struct IhkIkcQueueHead {
    id: u32,
    type_: u16,
    pktsize: u16,
    pktcount: u32,
    flag: u32,
    read_off: u64,
    max_read_off: u64,
    write_off: u64,
    queue_size: u64,
    channel_id: u32,
    read_cpu: u32,
    write_cpu: u32,
    dummy2: u32,
}

#[repr(C)]
struct IhkIkcQueueDesc {
    queue: *mut IhkIkcQueueHead,
    cache: IhkIkcQueueHead,
    qrphys: CULong,
    qphys: CULong,
    lock: IhkSpinlock,
    intr_cpu: u32,
}

#[repr(C)]
pub struct IhkIkcChannelDesc {
    list_all: ListHead,
    remote_os: *mut c_void,
    remote_channel_id: CInt,
    remote_channel_va: u64,
    master: *mut IhkIkcChannelDesc,
    port: CInt,
    channel_id: CInt,
    recv: IhkIkcQueueDesc,
    send: IhkIkcQueueDesc,
    lock: IhkSpinlock,
    flag: CInt,
    handler: IkcPacketHandler,
    packet_pool: ListHead,
    packet_pool_lock: IhkSpinlock,
}

#[no_mangle]
pub static mut per_cpu_irq_work: *mut LinuxIrqWork = null_mut();

unsafe extern "C" {
    static mut boot_param: *mut SmpBootParamPrefix;
    static mut num_processors: CInt;

    fn _kmalloc(size: CInt, flags: CInt, file: *mut i8, line: CInt) -> *mut c_void;
    #[cfg(not(native_linux_irq_work_v6_12))]
    fn kprintf(format: *const i8, ...) -> CInt;
    fn cpu_pause();
    fn ihk_mc_ikc_init_first_local(
        channel: *mut IhkIkcChannelDesc,
        handler: IkcPacketHandler,
    ) -> CInt;
    fn ihk_mc_ikc_arch_issue_host_ipi(cpu: CInt, vector: CInt) -> CInt;

    #[cfg(native_linux_irq_work_v6_12)]
    fn cpu_disable_interrupt_save() -> CULong;
    #[cfg(native_linux_irq_work_v6_12)]
    fn cpu_restore_interrupt(flags: CULong);
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<LinuxIrqWork>() == 64);
    assert!(align_of::<LinuxIrqWork>() == 8);
    assert!(offset_of!(LinuxIrqWork, func) == 16);
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        assert!(offset_of!(LinuxIrqWork, flags) == 0);
        assert!(offset_of!(LinuxIrqWork, llnode) == 8);
    }
    #[cfg(native_linux_irq_work_v6_12)]
    {
        assert!(offset_of!(LinuxIrqWork, llnode) == 0);
        assert!(offset_of!(LinuxIrqWork, flags) == 8);
        assert!(offset_of!(LinuxIrqWork, source) == 12);
        assert!(offset_of!(LinuxIrqWork, destination) == 14);
        assert!(offset_of!(LinuxIrqWork, irqwait) == 24);
    }
    assert!(size_of::<IhkIkcQueueHead>() == 64);
    assert!(size_of::<IhkIkcQueueDesc>() == 96);
    assert!(offset_of!(IhkIkcQueueDesc, intr_cpu) == 92);
    assert!(offset_of!(IhkIkcChannelDesc, send) == 152);
};

#[inline(always)]
unsafe fn kmalloc(size: usize, flags: CInt) -> *mut c_void {
    _kmalloc(
        size as CInt,
        flags,
        c"smp_ikc.rs".as_ptr() as *mut i8,
        line!() as CInt,
    )
}

#[cfg(native_linux_irq_work_v6_12)]
unsafe fn initialize_native_irq_work(count: u32) -> CInt {
    loop {
        match IRQ_WORK_INITIALIZATION.load(Ordering::Acquire) {
            2 => {
                return if IRQ_WORK_PROCESSORS.load(Ordering::Relaxed) == count {
                    0
                } else {
                    -22
                };
            }
            0 => {
                if IRQ_WORK_INITIALIZATION
                    .compare_exchange(0, 1, Ordering::AcqRel, Ordering::Acquire)
                    .is_err()
                {
                    continue;
                }
                // One initializer owns this unpublished allocation. The
                // bounded count fits the allocator's signed size argument.
                let work = kmalloc(64 * count as usize, IHK_MC_AP_NOWAIT).cast::<LinuxIrqWork>();
                if work.is_null() {
                    IRQ_WORK_INITIALIZATION.store(0, Ordering::Release);
                    return -12;
                }
                // Null pointers, None callbacks and zero atomic flags have
                // valid representations. Initialize Linux's irqwait as well
                // as the private padding before any list can see these slots.
                core::ptr::write_bytes(work, 0, count as usize);
                for index in 0..count as usize {
                    (*work.add(index)).func = (*boot_param).ikc_irq_work_func;
                }
                per_cpu_irq_work = work;
                IRQ_WORK_PROCESSORS.store(count, Ordering::Relaxed);
                IRQ_WORK_INITIALIZATION.store(2, Ordering::Release);
                return 0;
            }
            _ => cpu_pause(),
        }
    }
}

#[cfg(native_linux_irq_work_v6_12)]
struct NativeInterruptGuard(CULong);

#[cfg(native_linux_irq_work_v6_12)]
impl Drop for NativeInterruptGuard {
    fn drop(&mut self) {
        // SAFETY: This stack-local guard restores this CPU's saved flags;
        // it never leaves ihk_mc_interrupt_host or crosses a scheduling point.
        unsafe { cpu_restore_interrupt(self.0) };
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_interrupt_host(cpu: CInt, _vector: CInt) -> CInt {
    // The NOWAIT allocator already supports IRQ-disabled callers. Exclude
    // nested senders before claiming initialization, too: otherwise an IRQ
    // on the initializing CPU could spin forever waiting for its caller.
    // This entry point is not used from NMI context. Linux services work on
    // a separate assigned host CPU, so disabling local IRQs does not prevent
    // completion of a previously published slot.
    #[cfg(native_linux_irq_work_v6_12)]
    let _interrupts = NativeInterruptGuard(cpu_disable_interrupt_save());
    #[cfg(native_linux_irq_work_v6_12)]
    let source_cpu = {
        if boot_param.is_null()
            || cpu < 0
            || cpu as usize >= SMP_MAX_CPUS
            || num_processors <= 0
            || num_processors as usize > SMP_MAX_CPUS
        {
            return -22;
        }
        let source = crate::x86_local::ihk_mc_get_processor_id();
        if source < 0
            || source >= num_processors
            || (*boot_param).ikc_irq_work_func.is_none()
            || (*boot_param).ihk_ikc_cpu_raised_list[cpu as usize].is_null()
        {
            return -22;
        }
        let result = initialize_native_irq_work(num_processors as u32);
        if result != 0 {
            return result;
        }
        source as usize
    };
    #[cfg(not(native_linux_irq_work_v6_12))]
    if per_cpu_irq_work.is_null() {
        per_cpu_irq_work = kmalloc(
            core::mem::size_of::<LinuxIrqWork>().wrapping_mul(num_processors as usize),
            IHK_MC_AP_NOWAIT,
        )
        .cast();

        if per_cpu_irq_work.is_null() {
            kprintf(
                c"%s: error: allocating IKC Linux IRQ work\n"
                    .as_ptr()
                    .cast(),
                c"ihk_mc_interrupt_host".as_ptr(),
            );
            return -12;
        }

        let mut id = 0;
        while id < num_processors {
            let work = per_cpu_irq_work.add(id as usize);
            (*work).func = (*boot_param).ikc_irq_work_func;
            (*work).flags = 0;
            id += 1;
        }

        kprintf(c"Using Linux work IRQ for IKC IPI.\n".as_ptr().cast());
    }

    #[cfg(not(native_linux_irq_work_v6_12))]
    let source_cpu = crate::x86_local::ihk_mc_get_processor_id() as usize;
    let work = per_cpu_irq_work.add(source_cpu);
    #[cfg(not(native_linux_irq_work_v6_12))]
    while read_volatile(&(*work).flags) & IRQ_WORK_BUSY != 0 {
        cpu_pause();
    }

    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        (*work).flags = IRQ_WORK_BUSY;
    }
    #[cfg(native_linux_irq_work_v6_12)]
    loop {
        let flags = (*work).flags.load(Ordering::Acquire);
        if flags & IRQ_WORK_BUSY as u32 == 0
            && (*work)
                .flags
                .compare_exchange(
                    flags,
                    IRQ_WORK_BUSY as u32,
                    Ordering::AcqRel,
                    Ordering::Acquire,
                )
                .is_ok()
        {
            break;
        }
        cpu_pause();
    }
    let raised_list = (*boot_param)
        .ihk_ikc_cpu_raised_list
        .as_mut_ptr()
        .add(cpu as usize)
        .read();

    crate::llist::llist_add_batch(
        &raw mut (*work).llnode,
        &raw mut (*work).llnode,
        raised_list.cast::<LListHead>(),
    );

    let result = ihk_mc_ikc_arch_issue_host_ipi(cpu, (*boot_param).ihk_ikc_irq as CInt);
    #[cfg(native_linux_irq_work_v6_12)]
    {
        result
    }
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        let _ = result;
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_ikc_init_first(
    channel: *mut IhkIkcChannelDesc,
    packet_handler: IkcPacketHandler,
) -> CInt {
    ihk_mc_ikc_init_first_local(channel, packet_handler)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_send_interrupt(channel: *mut IhkIkcChannelDesc) -> CInt {
    ihk_mc_interrupt_host((*channel).send.intr_cpu as CInt, IHK_GV_IKC)
}
