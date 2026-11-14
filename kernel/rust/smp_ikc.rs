use core::ffi::c_void;
use core::ptr::null_mut;
#[cfg(not(native_linux_irq_work_v6_12))]
use core::ptr::read_volatile;
use core::sync::atomic::{AtomicU32, Ordering};
#[cfg(native_linux_irq_work_v6_12)]
use core::sync::atomic::{AtomicU8, AtomicU64};

use crate::abi::{CInt, CULong};
use crate::llist::LListNode;
#[cfg(not(native_linux_irq_work_v6_12))]
use crate::llist::LListHead;
use crate::spinlock_helpers::IhkSpinlock;

const SMP_MAX_CPUS: usize = 512;
#[cfg(not(native_linux_irq_work_v6_12))]
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const IHK_GV_IKC: CInt = 1;
const IRQ_WORK_BUSY: CULong = 2;

/// Additive tail descriptor for native Linux irq-work slots.  It is never
/// inserted into `SmpBootParam`: callers place it after every variable boot
/// table, so the frozen header and CPU/memory tables retain their offsets.
/// The descriptor is published only after all retained slots are initialized.
#[repr(C, align(8))]
pub struct NativeIrqWorkDescriptor {
    pub magic: u32,
    pub version: u16,
    pub bytes: u16,
    pub generation: u64,
    pub slots_phys: u64,
    pub slots_count: u32,
    pub slots_stride: u32,
    pub state: AtomicU32,
    pub senders: IrqWorkSenderGate,
    pub reserved: [u32; 6],
}

pub const NATIVE_IRQ_WORK_MAGIC: u32 = 0x4d43_4957; // "MCIW"
pub const NATIVE_IRQ_WORK_VERSION: u16 = 1;
pub const NATIVE_IRQ_WORK_RELEASE_READY: u32 = 1;
pub const NATIVE_IRQ_WORK_SLOT_BYTES: u32 = 64;

impl NativeIrqWorkDescriptor {
    pub const fn unpublished(generation: u64, slots_phys: u64, slots_count: u32) -> Self {
        Self {
            magic: NATIVE_IRQ_WORK_MAGIC,
            version: NATIVE_IRQ_WORK_VERSION,
            bytes: core::mem::size_of::<Self>() as u16,
            generation,
            slots_phys,
            slots_count,
            slots_stride: NATIVE_IRQ_WORK_SLOT_BYTES,
            state: AtomicU32::new(0),
            senders: IrqWorkSenderGate::new(),
            reserved: [0; 6],
        }
    }

    /// The release store is deliberately separate from construction: all
    /// slot contents must be initialized before a consumer can acquire it.
    pub fn publish_release_ready(&self) {
        self.state.store(NATIVE_IRQ_WORK_RELEASE_READY, Ordering::Release);
    }

    pub fn checked_end(&self) -> Option<u64> {
        let bytes = (self.slots_count as u64).checked_mul(self.slots_stride as u64)?;
        self.slots_phys.checked_add(bytes)
    }

    pub fn validate_unpublished(&self, count: u32) -> bool {
        self.magic == NATIVE_IRQ_WORK_MAGIC
            && self.version == NATIVE_IRQ_WORK_VERSION
            && self.bytes as usize == core::mem::size_of::<Self>()
            && self.generation != 0
            && self.slots_count == count && count != 0 && count <= 512
            && self.slots_stride == NATIVE_IRQ_WORK_SLOT_BYTES
            && self.slots_phys % NATIVE_IRQ_WORK_SLOT_BYTES as u64 == 0
            && self.state.load(Ordering::Acquire) == 0
            && self.senders.control.load(Ordering::Acquire) == 0
            && self.reserved == [0; 6]
            && self.checked_end().is_some()
    }
}

/// Compute the additive descriptor address after all variable boot tables.
/// This helper intentionally takes the already-computed table end; it cannot
/// shift any fixed header or table by construction.
pub fn native_irq_work_descriptor_offset(tables_end: usize) -> Option<usize> {
    tables_end.checked_add(7)?.checked_div(8)?.checked_mul(8)
}

/// Sender admission count. A lease must survive BUSY acquisition, list
/// insertion, IPI result, and the final slot access. Close only blocks new
/// leases; it never unlinks a failed-delivery node or clears BUSY manually.
#[repr(transparent)]
pub struct IrqWorkSenderGate {
    control: AtomicU32,
}

pub struct IrqWorkSenderLease<'a> {
    gate: &'a IrqWorkSenderGate,
    stage: u8,
}

impl IrqWorkSenderGate {
    const CLOSED: u32 = 1 << 31;
    pub const fn new() -> Self {
        Self { control: AtomicU32::new(0) }
    }

    pub fn acquire(&self) -> Option<IrqWorkSenderLease<'_>> {
        let mut observed = self.control.load(Ordering::Acquire);
        loop {
            if observed & Self::CLOSED != 0 || observed & !Self::CLOSED == Self::CLOSED - 1 {
                return None;
            }
            match self.control.compare_exchange_weak(
                observed,
                observed + 1,
                Ordering::AcqRel,
                Ordering::Acquire,
            ) {
                Ok(_) => return Some(IrqWorkSenderLease { gate: self, stage: 0 }),
                Err(next) => observed = next,
            }
        }
    }

    pub fn begin_close(&self) {
        self.control.fetch_or(Self::CLOSED, Ordering::AcqRel);
    }

    pub fn can_drain(&self) -> bool {
        let control = self.control.load(Ordering::Acquire);
        control & Self::CLOSED != 0 && control & !Self::CLOSED == 0
    }
}

impl IrqWorkSenderLease<'_> {
    pub fn busy_acquired(&mut self) -> bool { self.stage == 0 && { self.stage = 1; true } }
    pub fn list_inserted(&mut self) -> bool { self.stage == 1 && { self.stage = 2; true } }
    pub fn ipi_result(&mut self, _result: CInt) -> bool { self.stage == 2 && { self.stage = 3; true } }
    pub fn slot_accessed(&mut self) -> bool { self.stage == 3 && { self.stage = 4; true } }
}

impl Drop for IrqWorkSenderLease<'_> {
    fn drop(&mut self) { self.gate.control.fetch_sub(1, Ordering::Release); }
}

const _: () = {
    assert!(core::mem::size_of::<NativeIrqWorkDescriptor>() == 64);
    assert!(core::mem::align_of::<NativeIrqWorkDescriptor>() == 8);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, generation) == 8);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, slots_phys) == 16);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, magic) == 0);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, version) == 4);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, bytes) == 6);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, slots_count) == 24);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, slots_stride) == 28);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, state) == 32);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, senders) == 36);
    assert!(core::mem::offset_of!(NativeIrqWorkDescriptor, reserved) == 40);
};

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
#[cfg(native_linux_irq_work_v6_12)]
static IRQ_WORK_GENERATION: AtomicU64 = AtomicU64::new(0);

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
#[cfg(not(native_linux_irq_work_v6_12))]
static IRQ_WORK_SENDERS: IrqWorkSenderGate = IrqWorkSenderGate::new();

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
    #[cfg(native_linux_irq_work_v6_12)]
    fn map_fixed_area(phys: CULong, size: CULong, flags: CULong) -> *mut c_void;
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
#[cfg(not(native_linux_irq_work_v6_12))]
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
                return if IRQ_WORK_PROCESSORS.load(Ordering::Relaxed) == count
                    && IRQ_WORK_GENERATION.load(Ordering::Acquire) != 0
                {
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
                let descriptor_size = core::mem::size_of::<NativeIrqWorkDescriptor>();
                if (*boot_param).param_size < descriptor_size as CInt {
                    IRQ_WORK_INITIALIZATION.store(0, Ordering::Release);
                    return -22;
                }
                let descriptor = (boot_param as *mut u8)
                    .add((*boot_param).param_size as usize - descriptor_size)
                    .cast::<NativeIrqWorkDescriptor>();
                if !(*descriptor).validate_unpublished(count)
                {
                    IRQ_WORK_INITIALIZATION.store(0, Ordering::Release);
                    return -22;
                }
                let bytes = match (*descriptor).checked_end() {
                    Some(end) => match end.checked_sub((*descriptor).slots_phys) {
                        Some(bytes) => bytes as usize,
                        None => 0,
                    },
                    None => 0,
                };
                let direct = (*boot_param)
                    .page_offset_base
                    .checked_add((*descriptor).slots_phys)
                    .filter(|direct| direct.checked_add(bytes as u64).is_some())
                    .ok_or(-22)
                    .unwrap_or(0);
                let work = if bytes == 64 * count as usize && direct != 0 {
                    map_fixed_area((*descriptor).slots_phys, bytes as u64, 0).cast::<LinuxIrqWork>()
                } else {
                    null_mut()
                };
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
                IRQ_WORK_GENERATION.store((*descriptor).generation, Ordering::Relaxed);
                (*descriptor).publish_release_ready();
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
    #[cfg(native_linux_irq_work_v6_12)]
    let gate = &(*(boot_param.cast::<u8>()
        .add((*boot_param).param_size as usize - 64)
        .cast::<NativeIrqWorkDescriptor>())).senders;
    #[cfg(not(native_linux_irq_work_v6_12))]
    let gate = &IRQ_WORK_SENDERS;
    let Some(mut sender) = gate.acquire() else { return -16 };
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
    if !sender.busy_acquired() { return -22; }
    let raised_list = (*boot_param)
        .ihk_ikc_cpu_raised_list
        .as_mut_ptr()
        .add(cpu as usize)
        .read();

    #[cfg(not(native_linux_irq_work_v6_12))]
    crate::llist::llist_add_batch(
        &raw mut (*work).llnode,
        &raw mut (*work).llnode,
        raised_list.cast::<LListHead>(),
    );
    #[cfg(native_linux_irq_work_v6_12)]
    {
        // The fixed-area alias is guest-only. Linux's list must contain the
        // retained allocation's Linux direct-map address, never that alias.
        let descriptor = &*boot_param.cast::<u8>()
            .add((*boot_param).param_size as usize - 64)
            .cast::<NativeIrqWorkDescriptor>();
        let linux_node = ((*boot_param).page_offset_base + descriptor.slots_phys
            + source_cpu as u64 * 64) as *mut LListNode;
        let head = &*raised_list.cast::<core::sync::atomic::AtomicPtr<LListNode>>();
        let mut old = head.load(Ordering::Acquire);
        loop {
            // llnode is the first word of Linux 6.12 irq_work.
            core::ptr::write(work.cast::<*mut LListNode>(), old);
            match head.compare_exchange_weak(old, linux_node, Ordering::AcqRel, Ordering::Acquire) {
                Ok(_) => break,
                Err(next) => old = next,
            }
        }
    }
    if !sender.list_inserted() { return -22; }

    let result = ihk_mc_ikc_arch_issue_host_ipi(cpu, (*boot_param).ihk_ikc_irq as CInt);
    if !sender.ipi_result(result) { return -22; }
    if !sender.slot_accessed() { return -22; }
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

/// Close admission for a generation before teardown. Existing senders retain
/// their leases; this entry intentionally does not drain, unlink, or reuse.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_irq_work_begin_close() {
    #[cfg(not(native_linux_irq_work_v6_12))]
    IRQ_WORK_SENDERS.begin_close();
    #[cfg(native_linux_irq_work_v6_12)]
    if IRQ_WORK_INITIALIZATION.load(Ordering::Acquire) == 2 {
        (*(boot_param.cast::<u8>()
            .add((*boot_param).param_size as usize - 64)
            .cast::<NativeIrqWorkDescriptor>())).senders.begin_close();
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
