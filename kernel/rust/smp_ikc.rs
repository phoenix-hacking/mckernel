use core::ffi::c_void;
use core::ptr::{null_mut, read_volatile};

use crate::abi::{CInt, CULong};
use crate::llist::{LListHead, LListNode};
use crate::spinlock_helpers::IhkSpinlock;

const SMP_MAX_CPUS: usize = 512;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const IHK_GV_IKC: CInt = 1;
const IRQ_WORK_BUSY: CULong = 2;

#[repr(C)]
pub struct LinuxIrqWork {
    flags: CULong,
    llnode: LListNode,
    func: Option<unsafe extern "C" fn(*mut LinuxIrqWork)>,
    padding: [i8; 40],
}

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
    fn kprintf(format: *const i8, ...) -> CInt;
    fn cpu_pause();
    fn ihk_mc_ikc_init_first_local(
        channel: *mut IhkIkcChannelDesc,
        handler: IkcPacketHandler,
    ) -> CInt;
    fn ihk_mc_ikc_arch_issue_host_ipi(cpu: CInt, vector: CInt) -> CInt;
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<LinuxIrqWork>() == 64);
    assert!(align_of::<LinuxIrqWork>() == 8);
    assert!(offset_of!(LinuxIrqWork, llnode) == 8);
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

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_interrupt_host(cpu: CInt, _vector: CInt) -> CInt {
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

    let work = per_cpu_irq_work.add(crate::x86_local::ihk_mc_get_processor_id() as usize);
    while read_volatile(&(*work).flags) & IRQ_WORK_BUSY != 0 {
        cpu_pause();
    }

    (*work).flags = IRQ_WORK_BUSY;
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

    ihk_mc_ikc_arch_issue_host_ipi(cpu, (*boot_param).ihk_ikc_irq as CInt);
    0
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
