use core::ffi::{c_char, c_int, c_void};
use core::mem;
use core::ptr::write_bytes;

use crate::abi::CULong;

const IHK_MC_AP_CRITICAL: c_int = 0x1;
const IHK_IKC_MASTER_MSG_INIT_ACK: u32 = 0x1020_3010;
const MIKC_ALLOC_FILE: &[u8] = b"kernel/rust/mikc.rs\0";
const PAGE_SIZE: usize = 4096;
const PAGE_P2ALIGN: c_int = 0;
const IHK_MC_PG_KERNEL: c_int = 0;

type IkcPacketHandler =
    unsafe extern "C" fn(*mut IhkIkcChannelDesc, *mut c_void, *mut c_void) -> c_int;

#[repr(C)]
struct ListHead {
    next: *mut ListHead,
    prev: *mut ListHead,
}

#[repr(C)]
struct IhkSpinlock {
    head_tail: u32,
}

#[repr(C)]
struct IhkIkcQueueHead {
    id: u32,
    ty: u16,
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
    qrphys: usize,
    qphys: usize,
    lock: IhkSpinlock,
    intr_cpu: u32,
}

#[repr(C)]
pub struct IhkIkcChannelDesc {
    list_all: ListHead,
    remote_os: *mut c_void,
    remote_channel_id: c_int,
    remote_channel_va: u64,
    master: *mut IhkIkcChannelDesc,
    port: c_int,
    channel_id: c_int,
    recv: IhkIkcQueueDesc,
    send: IhkIkcQueueDesc,
    lock: IhkSpinlock,
    flag: c_int,
    handler: Option<IkcPacketHandler>,
    packet_pool: ListHead,
    packet_pool_lock: IhkSpinlock,
}

#[repr(C)]
struct IhkIkcPacketHeader {
    channel: *mut IhkIkcChannelDesc,
}

#[repr(C)]
struct IhkIkcMasterPacket {
    header: IhkIkcPacketHeader,
    msg: u32,
    ref_: u32,
    param: [u64; 5],
}

static mut MCHANNEL: *mut IhkIkcChannelDesc = core::ptr::null_mut();

#[no_mangle]
pub static mut arch_master_channel_packet_handler: Option<IkcPacketHandler> = None;

unsafe extern "C" {
    static mut host_ikc_inited: c_int;
    static mut num_processors: c_int;

    fn ihk_mc_ikc_init_first(channel: *mut IhkIkcChannelDesc, handler: IkcPacketHandler) -> c_int;
    fn ihk_ikc_system_init(os: *mut c_void);
    fn _ihk_mc_alloc_aligned_pages_node(
        npages: c_int,
        p2align: c_int,
        flag: CULong,
        node: c_int,
        is_user: c_int,
        virt_addr: CULong,
        file: *mut i8,
        line: c_int,
    ) -> *mut c_void;
    fn ihk_ikc_init_queue(
        queue: *mut IhkIkcQueueHead,
        id: c_int,
        ty: c_int,
        size: c_int,
        packetsize: c_int,
    ) -> c_int;
    fn ihk_ikc_init_desc(
        channel: *mut IhkIkcChannelDesc,
        remote_os: *mut c_void,
        channel_id: c_int,
        recv_queue: *mut IhkIkcQueueHead,
        send_queue: *mut IhkIkcQueueHead,
        packet_handler: Option<IkcPacketHandler>,
        master: *mut IhkIkcChannelDesc,
    );
    fn ihk_ikc_enable_channel(channel: *mut IhkIkcChannelDesc);
    fn ihk_ikc_master_channel_packet_handler(
        channel: *mut IhkIkcChannelDesc,
        packet: *mut c_void,
        arg: *mut c_void,
    ) -> c_int;
    fn arch_set_mikc_queue(recv_queue: *mut c_void, send_queue: *mut c_void);
    fn kprintf(format: *const c_char, ...) -> c_int;
    fn _kmalloc(size: c_int, flags: c_int, file: *mut i8, line: c_int) -> *mut c_void;
}

#[inline(always)]
unsafe fn kernel_alloc(size: usize) -> *mut c_void {
    _kmalloc(
        size as c_int,
        IHK_MC_AP_CRITICAL,
        MIKC_ALLOC_FILE.as_ptr() as *mut i8,
        line!() as c_int,
    )
}

#[inline(always)]
unsafe fn alloc_pages(npages: c_int) -> *mut c_void {
    _ihk_mc_alloc_aligned_pages_node(
        npages,
        PAGE_P2ALIGN,
        IHK_MC_AP_CRITICAL as CULong,
        -1,
        IHK_MC_PG_KERNEL,
        CULong::MAX,
        MIKC_ALLOC_FILE.as_ptr() as *mut i8,
        line!() as c_int,
    )
}

unsafe extern "C" fn master_channel_packet_handler(
    _channel: *mut IhkIkcChannelDesc,
    packet: *mut c_void,
    _arg: *mut c_void,
) -> c_int {
    let packet = packet as *mut IhkIkcMasterPacket;

    if !packet.is_null() && unsafe { (*packet).msg } == IHK_IKC_MASTER_MSG_INIT_ACK {
        unsafe {
            kprintf(b"Master channel init acked.\n\0".as_ptr() as *const c_char);
            host_ikc_inited = 1;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_master_init() {
    let size = mem::size_of::<IhkIkcChannelDesc>() + mem::size_of::<IhkIkcMasterPacket>();
    let channel = unsafe { kernel_alloc(size) as *mut IhkIkcChannelDesc };

    unsafe {
        MCHANNEL = channel;
        ihk_mc_ikc_init_first(MCHANNEL, master_channel_packet_handler);
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_get_master_channel() -> *mut IhkIkcChannelDesc {
    unsafe { MCHANNEL }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_ikc_init_first_local(
    channel: *mut IhkIkcChannelDesc,
    packet_handler: Option<IkcPacketHandler>,
) -> c_int {
    unsafe {
        ihk_ikc_system_init(core::ptr::null_mut());
        write_bytes(channel as *mut u8, 0, mem::size_of::<IhkIkcChannelDesc>());

        let queue_pages =
            ((4usize * num_processors as usize * mem::size_of::<IhkIkcMasterPacket>())
                + (PAGE_SIZE - 1))
                / PAGE_SIZE;
        let recv_queue = alloc_pages(queue_pages as c_int) as *mut IhkIkcQueueHead;
        let send_queue = alloc_pages(queue_pages as c_int) as *mut IhkIkcQueueHead;
        let queue_size = (queue_pages * PAGE_SIZE) as c_int;
        let packet_size = mem::size_of::<IhkIkcMasterPacket>() as c_int;

        ihk_ikc_init_queue(recv_queue, 0, 0, queue_size, packet_size);
        ihk_ikc_init_queue(send_queue, 0, 0, queue_size, packet_size);

        arch_master_channel_packet_handler = packet_handler;

        ihk_ikc_init_desc(
            channel,
            core::ptr::null_mut(),
            0,
            recv_queue,
            send_queue,
            Some(ihk_ikc_master_channel_packet_handler),
            channel,
        );
        ihk_ikc_enable_channel(channel);
        arch_set_mikc_queue(recv_queue as *mut c_void, send_queue as *mut c_void);
    }

    0
}
