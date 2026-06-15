use core::ffi::c_void;
use core::ptr::{null_mut, write_bytes};
use core::sync::atomic::{compiler_fence, AtomicI32, Ordering};

use crate::abi::{CInt, CULong, IhkSpinlock};
use crate::ikc_queue::{
    ihk_ikc_notify_remote_write, ihk_ikc_queue_is_empty, ihk_ikc_recv_handler, ihk_ikc_write_queue,
    ikc_channel_enabled, IhkIkcChannelDesc, IhkIkcQueueHead, IkcPacketHandler, IKC_NO_NOTIFY,
};
use crate::list_helpers::{ListHead, INIT_LIST_HEAD};

const IHK_GV_IKC: CInt = 1;
const IHK_MC_PG_KERNEL: CInt = 0;
const PAGE_P2ALIGN: CInt = 0;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;

#[repr(C)]
struct IhkMcInterruptHandler {
    list: ListHead,
    func: Option<unsafe extern "C" fn(*mut c_void)>,
    priv_: *mut c_void,
}

unsafe extern "C" {
    static mut num_processors: CInt;
    static mut arch_master_channel_packet_handler: IkcPacketHandler;

    fn _ihk_mc_alloc_aligned_pages_node(
        npages: CInt,
        p2align: CInt,
        flag: CULong,
        node: CInt,
        is_user: CInt,
        virt_addr: CULong,
        file: *mut i8,
        line: CInt,
    ) -> *mut c_void;
    fn _ihk_mc_free_pages(ptr: *mut c_void, npages: CInt, is_user: CInt, file: *mut i8, line: CInt);
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn cpu_pause();
    fn ihk_mc_allocate(size: CInt, flag: CInt) -> *mut c_void;
    fn ihk_mc_free(ptr: *mut c_void);
    fn ihk_mc_get_master_channel() -> *mut IhkIkcChannelDesc;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_get_vector(type_: CInt) -> CInt;
    fn ihk_mc_register_interrupt_handler(vector: CInt, handler: *mut IhkMcInterruptHandler)
        -> CInt;
    fn ihk_mc_unregister_interrupt_handler(
        vector: CInt,
        handler: *mut IhkMcInterruptHandler,
    ) -> CInt;
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn kprintf(format: *const i8, ...) -> CInt;
    #[link_name = "panic"]
    fn kernel_panic(format: *const i8) -> !;
    fn smp_func_call_handler();
}

static mut IHK_IKC_CHANNELS_LOCK: *mut IhkSpinlock = null_mut();
static mut IHK_IKC_CHANNELS: *mut ListHead = null_mut();
static mut REGULAR_CHANNELS: *mut *mut IhkIkcChannelDesc = null_mut();
static CHANNEL_ID: AtomicI32 = AtomicI32::new(0);

static mut IHK_IKC_HANDLER: IhkMcInterruptHandler = IhkMcInterruptHandler {
    list: ListHead {
        next: null_mut(),
        prev: null_mut(),
    },
    func: Some(ihk_ikc_interrupt_handler),
    priv_: null_mut(),
};

static mut WAIT_LIST: ListHead = ListHead {
    next: null_mut(),
    prev: null_mut(),
};
static mut WAIT_LOCK_RAW: u32 = 0;

#[repr(C)]
pub struct IhkIkcMasterPacket {
    pub header_channel: *mut IhkIkcChannelDesc,
    pub msg: u32,
    pub ref_: u32,
    pub param: [u64; 5],
}

#[repr(C)]
pub struct IhkIkcMasterWaitStruct {
    pub list: ListHead,
    pub wait: *mut c_void,
    pub status: CInt,
    pub msg: u32,
    pub ref_: u32,
    pub res: IhkIkcMasterPacket,
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkMcInterruptHandler>() == 32);
    assert!(align_of::<IhkMcInterruptHandler>() == 8);
    assert!(offset_of!(IhkMcInterruptHandler, func) == 16);
    assert!(size_of::<IhkIkcMasterPacket>() == 56);
    assert!(offset_of!(IhkIkcMasterPacket, param) == 16);
    assert!(size_of::<IhkIkcMasterWaitStruct>() == 96);
    assert!(offset_of!(IhkIkcMasterWaitStruct, res) == 40);
};

unsafe impl Sync for IhkMcInterruptHandler {}

#[inline(always)]
unsafe fn ensure_wait_list_init() {
    let wait = &raw mut WAIT_LIST;
    if (*wait).next.is_null() {
        INIT_LIST_HEAD(wait);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_channel_list(_os: *mut c_void) -> *mut ListHead {
    IHK_IKC_CHANNELS.add(ihk_mc_get_processor_id() as usize)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_channel_list_lock(_os: *mut c_void) -> *mut IhkSpinlock {
    IHK_IKC_CHANNELS_LOCK.add(ihk_mc_get_processor_id() as usize)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_regular_channel(
    _os: *mut c_void,
    cpu: CInt,
) -> *mut IhkIkcChannelDesc {
    if cpu < 0 || cpu >= num_processors {
        return null_mut();
    }
    *REGULAR_CHANNELS.add(cpu as usize)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_set_regular_channel(
    _os: *mut c_void,
    channel: *mut IhkIkcChannelDesc,
    cpu: CInt,
) {
    if cpu >= 0 && cpu < num_processors {
        *REGULAR_CHANNELS.add(cpu as usize) = channel;
    }
}

unsafe extern "C" fn ihk_ikc_interrupt_handler(_priv: *mut c_void) {
    if ihk_mc_get_processor_id() == 0 {
        let master = ihk_ikc_get_master_channel(null_mut());
        if !master.is_null() {
            while ikc_channel_enabled(master)
                && ihk_ikc_queue_is_empty((*master).recv.queue) == 0
                && (*(*master).recv.queue).read_cpu == ihk_mc_get_processor_id() as u32
            {
                ihk_ikc_recv_handler(master, (*master).handler, null_mut(), 0);
            }
        }
    }

    let regular = ihk_ikc_get_regular_channel(null_mut(), ihk_mc_get_processor_id());
    if !regular.is_null() {
        while ikc_channel_enabled(regular)
            && ihk_ikc_queue_is_empty((*regular).recv.queue) == 0
            && (*(*regular).recv.queue).read_cpu == ihk_mc_get_processor_id() as u32
        {
            ihk_ikc_recv_handler(regular, (*regular).handler, null_mut(), 0);
        }
    }

    smp_func_call_handler();
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_send(
    channel: *mut IhkIkcChannelDesc,
    packet: *mut c_void,
    opt: CInt,
) -> CInt {
    if channel.is_null() || packet.is_null() {
        return -22;
    }

    let flags = cpu_disable_interrupt_save();
    let ret;

    loop {
        if ikc_channel_enabled(channel) {
            let rc = ihk_ikc_write_queue((*channel).send.queue, packet, opt);
            if rc != 0 {
                kprintf(
                    c"%s: couldn't append packet -> retrying\n".as_ptr().cast(),
                    c"ihk_ikc_send".as_ptr(),
                );
                continue;
            }
            if opt & IKC_NO_NOTIFY == 0 {
                ihk_ikc_notify_remote_write(channel);
            }
            ret = rc;
        } else {
            ret = -22;
        }
        break;
    }

    cpu_restore_interrupt(flags);
    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_master_channel(_os: *mut c_void) -> *mut IhkIkcChannelDesc {
    ihk_mc_get_master_channel()
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_system_init(_os: *mut c_void) {
    INIT_LIST_HEAD(&raw mut IHK_IKC_HANDLER.list);
    ihk_mc_register_interrupt_handler(ihk_mc_get_vector(IHK_GV_IKC), &raw mut IHK_IKC_HANDLER);

    IHK_IKC_CHANNELS = ihk_ikc_malloc(
        core::mem::size_of::<ListHead>().wrapping_mul(num_processors as usize) as CInt,
    )
    .cast::<ListHead>();
    IHK_IKC_CHANNELS_LOCK = ihk_ikc_malloc(
        core::mem::size_of::<IhkSpinlock>().wrapping_mul(num_processors as usize) as CInt,
    )
    .cast::<IhkSpinlock>();
    REGULAR_CHANNELS = ihk_ikc_malloc(
        core::mem::size_of::<*mut IhkIkcChannelDesc>().wrapping_mul(num_processors as usize)
            as CInt,
    )
    .cast::<*mut IhkIkcChannelDesc>();

    if IHK_IKC_CHANNELS.is_null() || IHK_IKC_CHANNELS_LOCK.is_null() || REGULAR_CHANNELS.is_null() {
        kprintf(
            c"%s: error allocating channels list\n".as_ptr().cast(),
            c"ihk_ikc_system_init".as_ptr(),
        );
        kernel_panic(c"".as_ptr().cast());
    }

    write_bytes(REGULAR_CHANNELS, 0, num_processors as usize);

    let mut cpu = 0;
    while cpu < num_processors {
        INIT_LIST_HEAD(IHK_IKC_CHANNELS.add(cpu as usize));
        ihk_mc_spinlock_init(IHK_IKC_CHANNELS_LOCK.add(cpu as usize));
        cpu += 1;
    }
    ensure_wait_list_init();
    ihk_mc_spinlock_init((&raw mut WAIT_LOCK_RAW).cast::<IhkSpinlock>());
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_system_exit(_os: *mut c_void) {
    ihk_mc_unregister_interrupt_handler(ihk_mc_get_vector(IHK_GV_IKC), &raw mut IHK_IKC_HANDLER);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_alloc_queue(qpages: CInt) -> *mut IhkIkcQueueHead {
    _ihk_mc_alloc_aligned_pages_node(
        qpages,
        PAGE_P2ALIGN,
        0,
        -1,
        IHK_MC_PG_KERNEL,
        !0,
        c"ikc_manycore.rs".as_ptr() as *mut i8,
        line!() as CInt,
    )
    .cast::<IhkIkcQueueHead>()
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_free_queue(q: *mut IhkIkcQueueHead) {
    _ihk_mc_free_pages(
        q.cast::<c_void>(),
        ((core::mem::size_of::<IhkIkcQueueHead>() as CULong + (*q).queue_size + PAGE_SIZE - 1)
            >> PAGE_SHIFT) as CInt,
        IHK_MC_PG_KERNEL,
        c"ikc_manycore.rs".as_ptr() as *mut i8,
        line!() as CInt,
    );
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_malloc(size: CInt) -> *mut c_void {
    ihk_mc_allocate(size, 0)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_free(ptr: *mut c_void) {
    ihk_mc_free(ptr);
}

#[no_mangle]
pub unsafe extern "C" fn call_arch_master_packet_handler(
    os: *mut c_void,
    channel: *mut IhkIkcChannelDesc,
    packet: *mut c_void,
) -> CInt {
    if let Some(handler) = arch_master_channel_packet_handler {
        handler(channel, packet, os)
    } else {
        -22
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_master_wait_list(_os: *mut c_void) -> *mut ListHead {
    ensure_wait_list_init();
    &raw mut WAIT_LIST
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_get_master_wait_lock(_os: *mut c_void) -> *mut IhkSpinlock {
    (&raw mut WAIT_LOCK_RAW).cast::<IhkSpinlock>()
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_wait_init(_wait: *mut c_void) {}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_wait_master(wait: *mut IhkIkcMasterWaitStruct) -> CInt {
    while (*wait).status == 0 {
        cpu_pause();
        compiler_fence(Ordering::SeqCst);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_wake_master(wait: *mut IhkIkcMasterWaitStruct) {
    (*wait).status = 1;
}

#[no_mangle]
pub extern "C" fn ihk_ikc_get_unique_channel_id(_os: *mut c_void) -> CInt {
    CHANNEL_ID.fetch_add(1, Ordering::SeqCst) + 1
}
