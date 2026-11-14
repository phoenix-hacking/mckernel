use core::ffi::c_void;
use core::ptr::{copy_nonoverlapping, null_mut, write_bytes};
use core::sync::atomic::{compiler_fence, AtomicU64, Ordering};

use crate::abi::{CInt, CULong, IhkSpinlock};
use crate::list_helpers::{list_add_tail, list_del, ListHead, INIT_LIST_HEAD};

pub const IKC_FLAG_ENABLED: CInt = 1;
pub const IKC_FLAG_DESTROYING: CInt = 2;
pub const IKC_FLAG_DESTROY_ACKED: CInt = 4;
pub const IKC_FLAG_STATUS_MASK: CInt = 7;
pub const IKC_FLAG_NO_COPY: CInt = 0x10;
pub const IKC_NO_NOTIFY: CInt = 0x100;
const IHK_IKC_WRITE_QUEUE_RETRY: CInt = 128;
const PAGE_SHIFT: CInt = 12;
const PAGE_SIZE: CULong = 1 << PAGE_SHIFT;
const IHK_IKC_QUEUE_PT_ATTR: CULong = 0x8000_0000_0000_0002;

pub type IkcPacketHandler =
    Option<unsafe extern "C" fn(*mut IhkIkcChannelDesc, *mut c_void, *mut c_void) -> CInt>;

#[repr(C)]
#[derive(Clone, Copy)]
pub struct IhkIkcQueueHead {
    pub id: u32,
    pub type_: u16,
    pub pktsize: u16,
    pub pktcount: u32,
    pub flag: u32,
    pub read_off: u64,
    pub max_read_off: u64,
    pub write_off: u64,
    pub queue_size: u64,
    pub channel_id: u32,
    pub read_cpu: u32,
    pub write_cpu: u32,
    pub dummy2: u32,
}

#[repr(C)]
pub struct IhkIkcQueueDesc {
    pub queue: *mut IhkIkcQueueHead,
    pub cache: IhkIkcQueueHead,
    pub qrphys: CULong,
    pub qphys: CULong,
    pub lock: IhkSpinlock,
    pub intr_cpu: u32,
}

#[repr(C)]
pub struct IhkIkcPacketHeader {
    pub channel: *mut IhkIkcChannelDesc,
}

#[repr(C)]
pub struct IhkIkcFreePacket {
    pub header: IhkIkcPacketHeader,
    pub list: ListHead,
}

#[repr(C)]
pub struct IhkIkcChannelDesc {
    pub list_all: ListHead,
    pub remote_os: *mut c_void,
    pub remote_channel_id: CInt,
    pub remote_channel_va: u64,
    pub master: *mut IhkIkcChannelDesc,
    pub port: CInt,
    pub channel_id: CInt,
    pub recv: IhkIkcQueueDesc,
    pub send: IhkIkcQueueDesc,
    pub lock: IhkSpinlock,
    pub flag: CInt,
    pub handler: IkcPacketHandler,
    pub packet_pool: ListHead,
    pub packet_pool_lock: IhkSpinlock,
}

unsafe extern "C" {
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn cpu_disable_interrupt_save() -> CULong;
    fn cpu_restore_interrupt(flags: CULong);
    fn ihk_mc_spinlock_init(lock: *mut IhkSpinlock);
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_map_memory(os: *mut c_void, phys: CULong, size: CULong) -> CULong;
    fn ihk_mc_unmap_memory(os: *mut c_void, phys: CULong, size: CULong);
    fn ihk_mc_map_virtual(phys: CULong, size: CULong, attr: CULong) -> *mut CULong;
    fn ihk_mc_unmap_virtual(virt: *mut CULong, size: CULong);
    fn ihk_ikc_get_channel_list(os: *mut c_void) -> *mut ListHead;
    fn ihk_ikc_get_channel_list_lock(os: *mut c_void) -> *mut IhkSpinlock;
    fn ihk_ikc_get_master_channel(os: *mut c_void) -> *mut IhkIkcChannelDesc;
    fn ihk_ikc_get_unique_channel_id(os: *mut c_void) -> CInt;
    fn ihk_ikc_alloc_queue(qpages: CInt) -> *mut IhkIkcQueueHead;
    fn ihk_ikc_free_queue(q: *mut IhkIkcQueueHead);
    fn ihk_ikc_malloc(size: CInt) -> *mut c_void;
    fn ihk_ikc_free(ptr: *mut c_void);
    fn ihk_ikc_send_interrupt(channel: *mut IhkIkcChannelDesc) -> CInt;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn virt_to_phys(virt: *mut c_void) -> CULong;
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<IhkIkcQueueHead>() == 64);
    assert!(align_of::<IhkIkcQueueHead>() == 8);
    assert!(size_of::<IhkIkcQueueDesc>() == 96);
    assert!(offset_of!(IhkIkcQueueDesc, intr_cpu) == 92);
    assert!(offset_of!(IhkIkcFreePacket, list) == 8);
    assert!(offset_of!(IhkIkcChannelDesc, recv) == 56);
    assert!(offset_of!(IhkIkcChannelDesc, send) == 152);
    assert!(offset_of!(IhkIkcChannelDesc, packet_pool) == 264);
};

#[inline(always)]
unsafe fn atomic_u64(slot: *mut u64) -> *mut AtomicU64 {
    slot.cast::<AtomicU64>()
}

#[inline(always)]
unsafe fn cmpxchg_u64(slot: *mut u64, old: u64, new: u64) -> u64 {
    match (*atomic_u64(slot)).compare_exchange(old, new, Ordering::SeqCst, Ordering::SeqCst) {
        Ok(value) | Err(value) => value,
    }
}

#[inline(always)]
unsafe fn memcpyl(dest: *mut c_void, src: *const c_void, len: usize) {
    let words = len / core::mem::size_of::<CULong>();
    copy_nonoverlapping(src.cast::<CULong>(), dest.cast::<CULong>(), words);
}

#[inline(always)]
unsafe fn rem_u64_nonzero(value: u64, divisor: u64) -> u64 {
    let quotient: u64;
    let remainder: u64;

    core::arch::asm!(
        "xor edx, edx",
        "div {divisor}",
        divisor = in(reg) divisor,
        inlateout("rax") value => quotient,
        out("rdx") remainder,
        options(nostack),
    );
    let _ = quotient;
    remainder
}

#[inline(always)]
unsafe fn queue_packet_offset(q: *mut IhkIkcQueueHead, index: u64) -> Option<usize> {
    let count = (*q).pktcount as u64;
    if count == 0 {
        return None;
    }
    Some(
        core::mem::size_of::<IhkIkcQueueHead>()
            + (rem_u64_nonzero(index, count) * (*q).pktsize as u64) as usize,
    )
}

#[inline(always)]
pub unsafe fn ikc_channel_enabled(channel: *mut IhkIkcChannelDesc) -> bool {
    ((*channel).flag & IKC_FLAG_STATUS_MASK) == IKC_FLAG_ENABLED
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_channel_enabled(channel: *mut IhkIkcChannelDesc) -> CInt {
    unsafe { ikc_channel_enabled(channel) as CInt }
}

#[inline(always)]
unsafe fn packet_from_list(node: *mut ListHead) -> *mut IhkIkcFreePacket {
    (node as *mut u8)
        .sub(core::mem::offset_of!(IhkIkcFreePacket, list))
        .cast::<IhkIkcFreePacket>()
}

#[inline(always)]
unsafe fn queue_pages_from_size(qsize: CULong) -> CInt {
    ((qsize + PAGE_SIZE - 1) >> PAGE_SHIFT) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_init_queue(
    q: *mut IhkIkcQueueHead,
    id: CInt,
    type_: CInt,
    size: CInt,
    packetsize: CInt,
) -> CInt {
    if q.is_null() {
        return -22;
    }
    if packetsize <= 0 || size < core::mem::size_of::<IhkIkcQueueHead>() as CInt {
        return -22;
    }

    write_bytes(q, 0, 1);
    let packet_size = packetsize as usize;
    (*q).id = id as u32;
    (*q).type_ = type_ as u16;
    (*q).pktsize = packetsize as u16;
    (*q).pktcount =
        ((size as usize - core::mem::size_of::<IhkIkcQueueHead>()) / packet_size) as u32;
    (*q).queue_size = (*q).pktsize as u64 * (*q).pktcount as u64;
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_queue_is_empty(q: *mut IhkIkcQueueHead) -> CInt {
    if q.is_null() {
        return -22;
    }
    ((*q).read_off == (*q).max_read_off) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_queue_is_full(q: *mut IhkIkcQueueHead) -> CInt {
    if q.is_null() {
        return -22;
    }

    let read = (*q).read_off;
    let write = (*q).write_off;
    compiler_fence(Ordering::SeqCst);

    (write.wrapping_sub(read) == ((*q).pktcount as u64).wrapping_sub(1)) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_read_queue(
    q: *mut IhkIkcQueueHead,
    packet: *mut c_void,
    _flag: CInt,
) -> CInt {
    if q.is_null() || packet.is_null() {
        return -22;
    }
    if (*q).pktcount == 0 {
        return -22;
    }

    loop {
        let read = (*q).read_off;
        let max_read = (*q).max_read_off;
        compiler_fence(Ordering::SeqCst);

        if read == max_read {
            return -1;
        }
        if cmpxchg_u64(&raw mut (*q).read_off, read, read.wrapping_add(1)) != read {
            continue;
        }

        let Some(offset) = queue_packet_offset(q, read) else {
            return -22;
        };
        memcpyl(
            packet,
            (q as *const u8).add(offset).cast::<c_void>(),
            (*q).pktsize as usize,
        );
        return 0;
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_read_queue_handler(
    q: *mut IhkIkcQueueHead,
    channel: *mut IhkIkcChannelDesc,
    handler: IkcPacketHandler,
    harg: *mut c_void,
    _flag: CInt,
) -> CInt {
    if q.is_null() {
        return -22;
    }
    if (*q).pktcount == 0 {
        return -22;
    }
    let Some(handler) = handler else {
        return -22;
    };

    loop {
        let read = (*q).read_off;
        let max_read = (*q).max_read_off;
        compiler_fence(Ordering::SeqCst);

        if read == max_read {
            return -1;
        }
        if cmpxchg_u64(&raw mut (*q).read_off, read, read.wrapping_add(1)) != read {
            continue;
        }

        let Some(offset) = queue_packet_offset(q, read) else {
            return -22;
        };
        handler(channel, (q as *mut u8).add(offset).cast::<c_void>(), harg);
        return 0;
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_write_queue(
    q: *mut IhkIkcQueueHead,
    packet: *mut c_void,
    _flag: CInt,
) -> CInt {
    if q.is_null() || packet.is_null() {
        return -22;
    }
    if (*q).pktcount == 0 {
        return -22;
    }

    let mut attempt = 0;
    loop {
        let read = (*q).read_off;
        let write = (*q).write_off;
        compiler_fence(Ordering::SeqCst);

        if write.wrapping_sub(read) == ((*q).pktcount as u64).wrapping_sub(1) {
            attempt += 1;
            if attempt > IHK_IKC_WRITE_QUEUE_RETRY {
                kprintf(
                    c"%s: queue %p r: %llu, w: %llu is full\n".as_ptr().cast(),
                    c"ihk_ikc_write_queue".as_ptr(),
                    virt_to_phys(q.cast::<c_void>()),
                    read,
                    write,
                );
                return -16;
            }
            continue;
        }
        if cmpxchg_u64(&raw mut (*q).write_off, write, write.wrapping_add(1)) != write {
            continue;
        }

        let Some(offset) = queue_packet_offset(q, write) else {
            return -22;
        };
        memcpyl(
            (q as *mut u8).add(offset).cast::<c_void>(),
            packet,
            (*q).pktsize as usize,
        );

        while cmpxchg_u64(&raw mut (*q).max_read_off, write, write.wrapping_add(1)) != write {}

        return 0;
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_init_desc(
    channel: *mut IhkIkcChannelDesc,
    remote_os: *mut c_void,
    port: CInt,
    recvq: *mut IhkIkcQueueHead,
    sendq: *mut IhkIkcQueueHead,
    packet_handler: IkcPacketHandler,
    master: *mut IhkIkcChannelDesc,
) {
    let all_list = ihk_ikc_get_channel_list(remote_os);
    let all_lock = ihk_ikc_get_channel_list_lock(remote_os);

    INIT_LIST_HEAD(&raw mut (*channel).list_all);
    INIT_LIST_HEAD(&raw mut (*channel).packet_pool);

    (*channel).remote_os = remote_os;
    (*channel).port = port;
    (*channel).channel_id = ihk_ikc_get_unique_channel_id(remote_os);
    (*channel).recv.queue = recvq;
    (*channel).send.queue = sendq;

    if !recvq.is_null() {
        (*recvq).channel_id = (*channel).channel_id as u32;
        (*recvq).read_cpu = ihk_mc_get_processor_id() as u32;
        (*channel).recv.cache = *recvq;
    }
    if !sendq.is_null() {
        (*channel).remote_channel_id = (*channel).send.cache.channel_id as CInt;
        (*sendq).write_cpu = ihk_mc_get_processor_id() as u32;
        (*channel).send.cache = *sendq;
    }
    (*channel).handler = packet_handler;
    (*channel).master = master;

    ihk_mc_spinlock_init(&raw mut (*channel).recv.lock);
    ihk_mc_spinlock_init(&raw mut (*channel).send.lock);
    ihk_mc_spinlock_init(&raw mut (*channel).packet_pool_lock);

    let flags = __ihk_mc_spinlock_lock(all_lock);
    list_add_tail(&raw mut (*channel).list_all, all_list);
    __ihk_mc_spinlock_unlock(all_lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_alloc_packet(
    channel: *mut IhkIkcChannelDesc,
) -> *mut IhkIkcFreePacket {
    let mut packet = null_mut::<IhkIkcFreePacket>();

    let flags = __ihk_mc_spinlock_lock(&raw mut (*channel).packet_pool_lock);
    let head = &raw mut (*channel).packet_pool;
    let first = (*head).next;
    if first != head {
        packet = packet_from_list(first);
        list_del(&raw mut (*packet).list);
    }
    __ihk_mc_spinlock_unlock(&raw mut (*channel).packet_pool_lock, flags);

    while packet.is_null() {
        packet = ihk_ikc_malloc((*(*channel).recv.queue).pktsize as CInt).cast();
        if packet.is_null() {
            kprintf(
                c"%s: ERROR allocating packet, retrying\n".as_ptr().cast(),
                c"ihk_ikc_alloc_packet".as_ptr(),
            );
        }
    }

    packet
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_release_packet(packet: *mut IhkIkcFreePacket) {
    if packet.is_null() {
        return;
    }

    let channel = (*packet).header.channel;
    if channel.is_null() {
        kprintf(
            c"%s: WARNING: channel of packet (%p) is NULL\n"
                .as_ptr()
                .cast(),
            c"ihk_ikc_release_packet".as_ptr(),
            packet,
        );
        ihk_ikc_free(packet.cast::<c_void>());
        return;
    }

    let flags = __ihk_mc_spinlock_lock(&raw mut (*channel).packet_pool_lock);
    list_add_tail(&raw mut (*packet).list, &raw mut (*channel).packet_pool);
    __ihk_mc_spinlock_unlock(&raw mut (*channel).packet_pool_lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_channel_set_cpu(channel: *mut IhkIkcChannelDesc, cpu: CInt) {
    (*(*channel).send.queue).write_cpu = cpu as u32;
    (*(*channel).recv.queue).read_cpu = cpu as u32;
}

#[no_mangle]
pub extern "C" fn ihk_os_to_dev(_os: *mut c_void) -> *mut c_void {
    null_mut()
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_map_virtual(
    _dev: *mut c_void,
    phys: CULong,
    npages: CInt,
    attr: CULong,
) -> *mut c_void {
    ihk_mc_map_virtual(phys, npages as CULong, attr).cast()
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_unmap_virtual(_dev: *mut c_void, virt: *mut c_void, npages: CInt) {
    ihk_mc_unmap_virtual(virt.cast::<CULong>(), npages as CULong);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_set_remote_queue(
    queue: *mut IhkIkcQueueDesc,
    os: *mut c_void,
    remote_phys: CULong,
    qsize: CULong,
) -> CInt {
    let qpages = queue_pages_from_size(qsize);

    ihk_mc_spinlock_init(&raw mut (*queue).lock);
    (*queue).qrphys = remote_phys;
    (*queue).qphys = ihk_mc_map_memory(os, (*queue).qrphys, qpages as CULong * PAGE_SIZE);
    (*queue).queue =
        ihk_mc_map_virtual((*queue).qphys, qpages as CULong, IHK_IKC_QUEUE_PT_ATTR).cast();
    (*queue).cache = *(*queue).queue;

    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_create_channel(
    os: *mut c_void,
    port: CInt,
    packet_size: CInt,
    qsize: CULong,
    rq: *mut CULong,
    sq: *mut CULong,
    flag: CInt,
) -> *mut IhkIkcChannelDesc {
    let qpages = queue_pages_from_size(qsize);
    let desc =
        ihk_ikc_malloc((core::mem::size_of::<IhkIkcChannelDesc>() + packet_size as usize) as CInt)
            .cast::<IhkIkcChannelDesc>();
    if desc.is_null() {
        return null_mut();
    }

    write_bytes(desc, 0, 1);
    (*desc).flag = flag;

    let recvq = if *rq == 0 {
        let queue = ihk_ikc_alloc_queue(qpages);
        if queue.is_null() {
            ihk_ikc_free(desc.cast::<c_void>());
            return null_mut();
        }

        ihk_ikc_init_queue(
            queue,
            1,
            port,
            (PAGE_SIZE * qpages as CULong) as CInt,
            packet_size,
        );
        *rq = virt_to_phys(queue.cast::<c_void>());
        (*desc).recv.qrphys = 0;
        (*desc).recv.qphys = *rq;
        queue
    } else {
        let phys = ihk_mc_map_memory(os, *rq, qpages as CULong * PAGE_SIZE);
        (*desc).recv.qrphys = *rq;
        (*desc).recv.qphys = phys;
        ihk_mc_map_virtual(phys, qpages as CULong, IHK_IKC_QUEUE_PT_ATTR).cast::<IhkIkcQueueHead>()
    };

    let sendq = if *sq != 0 {
        let phys = ihk_mc_map_memory(os, *sq, qpages as CULong * PAGE_SIZE);
        (*desc).send.qrphys = *sq;
        (*desc).send.qphys = phys;
        ihk_mc_map_virtual(phys, qpages as CULong, IHK_IKC_QUEUE_PT_ATTR).cast::<IhkIkcQueueHead>()
    } else {
        null_mut()
    };

    ihk_ikc_init_desc(
        desc,
        os,
        port,
        recvq,
        sendq,
        None,
        ihk_ikc_get_master_channel(os),
    );

    desc
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_free_channel(desc: *mut IhkIkcChannelDesc) {
    let os = (*desc).remote_os;
    let lock = ihk_ikc_get_channel_list_lock(os);

    let flags = __ihk_mc_spinlock_lock(lock);
    list_del(&raw mut (*desc).list_all);
    __ihk_mc_spinlock_unlock(lock, flags);

    let flags = __ihk_mc_spinlock_lock(&raw mut (*desc).packet_pool_lock);
    let head = &raw mut (*desc).packet_pool;
    let mut node = (*head).next;
    while node != head {
        let next = (*node).next;
        let packet = packet_from_list(node);
        list_del(&raw mut (*packet).list);
        ihk_ikc_free(packet.cast::<c_void>());
        node = next;
    }
    __ihk_mc_spinlock_unlock(&raw mut (*desc).packet_pool_lock, flags);

    if !(*desc).recv.queue.is_null() {
        let qpages = queue_pages_from_size(
            (*(*desc).recv.queue).queue_size + core::mem::size_of::<IhkIkcQueueHead>() as CULong,
        );
        if (*desc).recv.qrphys != 0 {
            ihk_mc_unmap_virtual((*desc).recv.queue.cast::<CULong>(), qpages as CULong);
            ihk_mc_unmap_memory(os, (*desc).recv.qphys, qpages as CULong);
        } else {
            ihk_ikc_free_queue((*desc).recv.queue);
        }
    }

    if !(*desc).send.queue.is_null() {
        let qpages = queue_pages_from_size(
            (*(*desc).send.queue).queue_size + core::mem::size_of::<IhkIkcQueueHead>() as CULong,
        );
        if (*desc).send.qrphys != 0 {
            ihk_mc_unmap_virtual((*desc).send.queue.cast::<CULong>(), qpages as CULong);
            ihk_mc_unmap_memory(os, (*desc).send.qphys, qpages as CULong);
        } else {
            ihk_ikc_free_queue((*desc).send.queue);
        }
    }

    ihk_ikc_free(desc.cast::<c_void>());
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_recv(
    channel: *mut IhkIkcChannelDesc,
    packet: *mut c_void,
    opt: CInt,
) -> CInt {
    if channel.is_null() || packet.is_null() {
        return -22;
    }

    let flags = cpu_disable_interrupt_save();
    let ret = if ikc_channel_enabled(channel) {
        let r = ihk_ikc_read_queue((*channel).recv.queue, packet, opt);
        if r == 0 {
            (*packet.cast::<IhkIkcPacketHeader>()).channel = channel;
        }
        if opt & IKC_NO_NOTIFY == 0 {
            ihk_ikc_notify_remote_read(channel);
        }
        r
    } else {
        -22
    };
    cpu_restore_interrupt(flags);

    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_recv_handler(
    channel: *mut IhkIkcChannelDesc,
    handler: IkcPacketHandler,
    harg: *mut c_void,
    opt: CInt,
) -> CInt {
    if channel.is_null() {
        kprintf(
            c"%s: ERROR: channel doesn't exist\n".as_ptr().cast(),
            c"ihk_ikc_recv_handler".as_ptr(),
        );
        return -22;
    }

    let packet = ihk_ikc_alloc_packet(channel).cast::<c_void>();
    if packet.is_null() {
        kprintf(
            c"%s: error allocating packet\n".as_ptr().cast(),
            c"ihk_ikc_recv_handler".as_ptr(),
        );
        return -12;
    }

    let ret = ihk_ikc_recv(channel, packet, opt | IKC_NO_NOTIFY);
    if ret != 0 {
        kprintf(
            c"%s: WARNING: ihk_ikc_recv returned %d%s\n".as_ptr().cast(),
            c"ihk_ikc_recv_handler".as_ptr(),
            ret,
            if ret == -1 {
                c" (empty queue)".as_ptr()
            } else {
                c"".as_ptr()
            },
        );
        ihk_ikc_release_packet(packet.cast::<IhkIkcFreePacket>());
        return ret;
    }

    if let Some(handler) = handler {
        handler(channel, packet, harg);
    }

    if (*channel).flag & IKC_FLAG_NO_COPY != 0 {
        ihk_ikc_notify_remote_read(channel);
    }

    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_notify_remote_read(channel: *mut IhkIkcChannelDesc) {
    ihk_ikc_send_interrupt(channel);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_notify_remote_write(channel: *mut IhkIkcChannelDesc) {
    ihk_ikc_send_interrupt(channel);
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_ikc_enable_channel(channel: *mut IhkIkcChannelDesc) {
    (*channel).flag |= IKC_FLAG_ENABLED;
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_ikc_disable_channel(channel: *mut IhkIkcChannelDesc) {
    (*channel).flag &= !IKC_FLAG_ENABLED;
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_enable_channel(channel: *mut IhkIkcChannelDesc) {
    let flags = __ihk_mc_spinlock_lock(&raw mut (*channel).recv.lock);
    __ihk_ikc_enable_channel(channel);
    __ihk_mc_spinlock_unlock(&raw mut (*channel).recv.lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_disable_channel(channel: *mut IhkIkcChannelDesc) {
    let flags = __ihk_mc_spinlock_lock(&raw mut (*channel).recv.lock);
    __ihk_ikc_disable_channel(channel);
    __ihk_mc_spinlock_unlock(&raw mut (*channel).recv.lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_find_channel(os: *mut c_void, id: CInt) -> *mut IhkIkcChannelDesc {
    let lock = ihk_ikc_get_channel_list_lock(os);
    let channels = ihk_ikc_get_channel_list(os);
    let flags = __ihk_mc_spinlock_lock(lock);

    let mut node = (*channels).next;
    while node != channels {
        let channel = node.cast::<IhkIkcChannelDesc>();
        if (*channel).channel_id == id {
            __ihk_mc_spinlock_unlock(lock, flags);
            return channel;
        }
        node = (*node).next;
    }
    __ihk_mc_spinlock_unlock(lock, flags);

    null_mut()
}
