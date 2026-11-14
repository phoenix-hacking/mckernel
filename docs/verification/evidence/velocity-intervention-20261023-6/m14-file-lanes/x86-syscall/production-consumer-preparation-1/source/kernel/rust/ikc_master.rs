use core::ffi::c_void;
use core::ptr::{copy_nonoverlapping, null_mut, write_bytes};

use crate::abi::{CInt, CULong, IhkSpinlock};
use crate::ikc_manycore::{
    call_arch_master_packet_handler, ihk_ikc_get_master_wait_list, ihk_ikc_get_master_wait_lock,
    ihk_ikc_send, ihk_ikc_wait_init, ihk_ikc_wait_master, ihk_ikc_wake_master, IhkIkcMasterPacket,
    IhkIkcMasterWaitStruct,
};
use crate::ikc_queue::{
    ihk_ikc_channel_set_cpu, ihk_ikc_create_channel, ihk_ikc_disable_channel,
    ihk_ikc_enable_channel, ihk_ikc_free_channel, ihk_ikc_queue_is_empty, ihk_ikc_recv_handler,
    ihk_ikc_release_packet, ihk_ikc_set_remote_queue, ikc_channel_enabled, IhkIkcChannelDesc,
    IkcPacketHandler, IKC_FLAG_DESTROYING, IKC_FLAG_DESTROY_ACKED, IKC_FLAG_ENABLED,
};
use crate::list_helpers::{list_add_tail, list_del, ListHead, INIT_LIST_HEAD};

const EBUSY: CInt = 16;
const ECONNREFUSED: CInt = 111;
const ECONNABORTED: CInt = 103;
const EINVAL: CInt = 22;
const EINTR: CInt = 4;
const ENOENT: CInt = 2;
const ENOMEM: CInt = 12;

const IHK_IKC_MAX_PORT: usize = 512;
const IHK_IKC_DIRECTION_RECV: CInt = 1;
const IHK_IKC_MASTER_MSG_CONNECT: u32 = 0x2000_0001;
const IHK_IKC_MASTER_MSG_CONNECT_REPLY: u32 = 0x2000_0002;
const IHK_IKC_MASTER_MSG_DISCONNECT: u32 = 0x2000_0008;
const IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL: u32 = 0x2000_0010;

#[repr(C)]
pub struct IhkIkcListenParam {
    pub handler: Option<unsafe extern "C" fn(*mut IhkIkcChannelInfo) -> CInt>,
    pub port: CInt,
    pub ikc_direction: CInt,
    pub pkt_size: CInt,
    pub queue_size: CInt,
    pub magic: CInt,
}

#[repr(C)]
pub struct IhkIkcConnectParam {
    pub port: CInt,
    pub pkt_size: CInt,
    pub queue_size: CInt,
    pub magic: CInt,
    pub intr_cpu: CInt,
    pub handler: IkcPacketHandler,
    pub channel: *mut IhkIkcChannelDesc,
}

#[repr(C)]
pub struct IhkIkcChannelInfo {
    pub channel: *mut IhkIkcChannelDesc,
    pub packet_handler: IkcPacketHandler,
}

static mut LISTENER_LOCK_RAW: u32 = 0;
static mut LISTENERS: [*mut IhkIkcListenParam; IHK_IKC_MAX_PORT] = [null_mut(); IHK_IKC_MAX_PORT];

unsafe extern "C" {
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, flags: CULong);
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_ikc_get_master_channel(os: *mut c_void) -> *mut IhkIkcChannelDesc;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn virt_to_phys(virt: *mut c_void) -> CULong;
}

#[inline(always)]
unsafe fn listener_lock() -> *mut IhkSpinlock {
    (&raw mut LISTENER_LOCK_RAW).cast::<IhkSpinlock>()
}

#[inline(always)]
unsafe fn listener_entry(port: CInt) -> *mut *mut IhkIkcListenParam {
    (&raw mut LISTENERS)
        .cast::<*mut IhkIkcListenParam>()
        .add(port as usize)
}

#[inline(always)]
unsafe fn wait_from_list(node: *mut ListHead) -> *mut IhkIkcMasterWaitStruct {
    (node as *mut u8)
        .sub(core::mem::offset_of!(IhkIkcMasterWaitStruct, list))
        .cast::<IhkIkcMasterWaitStruct>()
}

unsafe fn ikc_master_send(
    os: *mut c_void,
    msg: u32,
    ref_: u32,
    a1: u64,
    a2: u64,
    a3: u64,
    a4: u64,
    a5: u64,
) -> CInt {
    let mut packet = IhkIkcMasterPacket {
        header_channel: null_mut(),
        msg,
        ref_,
        param: [a1, a2, a3, a4, a5],
    };
    let channel = ihk_ikc_get_master_channel(os);

    ihk_ikc_send(channel, (&raw mut packet).cast::<c_void>(), 0)
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_listen_port(
    _os: *mut c_void,
    param: *mut IhkIkcListenParam,
) -> CInt {
    if param.is_null() {
        return -EINVAL;
    }

    let port = (*param).port;
    if port < 0 || port as usize >= IHK_IKC_MAX_PORT {
        return -EINVAL;
    }

    let lock = listener_lock();
    let flags = __ihk_mc_spinlock_lock(lock);
    let entry = listener_entry(port);
    if !(*entry).is_null() {
        __ihk_mc_spinlock_unlock(lock, flags);
        return -EBUSY;
    }
    *entry = param;
    __ihk_mc_spinlock_unlock(lock, flags);

    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_accept(
    cm: *mut IhkIkcChannelDesc,
    param: *mut IhkIkcListenParam,
    packet_size: CULong,
    rq: *mut CULong,
    sq: *mut CULong,
    newc: *mut *mut IhkIkcChannelDesc,
    remote_channel_va: CULong,
    magic: CInt,
    intr_cpu: CInt,
) -> CInt {
    if param.is_null() {
        return -ECONNREFUSED;
    }
    let Some(handler) = (*param).handler else {
        return -ECONNREFUSED;
    };
    if (*param).magic != magic {
        return -ECONNREFUSED;
    }
    if packet_size != (*param).pkt_size as CULong {
        return -ECONNABORTED;
    }

    let channel = ihk_ikc_create_channel(
        (*cm).remote_os,
        (*param).port,
        (*param).pkt_size,
        (*param).queue_size as CULong,
        rq,
        sq,
        0,
    );
    if channel.is_null() {
        return -ENOMEM;
    }

    let mut info = IhkIkcChannelInfo {
        channel,
        packet_handler: None,
    };

    if (*param).ikc_direction == IHK_IKC_DIRECTION_RECV {
        ihk_ikc_channel_set_cpu(channel, intr_cpu);
        crate::ikc_manycore::ihk_ikc_set_regular_channel((*cm).remote_os, channel, intr_cpu);
    }

    let ret = handler((&raw mut info).cast::<IhkIkcChannelInfo>());
    if ret != 0 {
        ihk_ikc_free_channel(channel);
        return ret;
    }

    (*channel).handler = info.packet_handler;
    (*channel).remote_channel_va = remote_channel_va;
    *newc = channel;
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_master_channel_packet_handler(
    channel: *mut IhkIkcChannelDesc,
    raw_packet: *mut c_void,
    os: *mut c_void,
) -> CInt {
    if channel.is_null() || raw_packet.is_null() {
        return -EINVAL;
    }

    let packet = raw_packet.cast::<IhkIkcMasterPacket>();
    let mut ret = 0;

    match (*packet).msg {
        IHK_IKC_MASTER_MSG_PACKET_ON_CHANNEL => {
            let regular = (*packet).param[3] as *mut IhkIkcChannelDesc;
            if regular.is_null() {
                ret = -ENOENT;
            } else {
                if os.is_null()
                    && (*(*regular).recv.queue).read_cpu != ihk_mc_get_processor_id() as u32
                {
                    kprintf(
                        c"%s: %p is for CPU %d\n".as_ptr().cast(),
                        c"ihk_ikc_master_channel_packet_handler".as_ptr(),
                        virt_to_phys(regular.cast::<c_void>()) as *mut c_void,
                        (*(*regular).recv.queue).read_cpu,
                    );
                }
                if ikc_channel_enabled(regular)
                    && ihk_ikc_queue_is_empty((*regular).recv.queue) == 0
                {
                    ihk_ikc_recv_handler(regular, (*regular).handler, os, 0);
                }
            }
        }
        IHK_IKC_MASTER_MSG_CONNECT => {
            let port = ((*packet).param[0] & 0xffff_ffff) as CInt;
            let mut new_channel: *mut IhkIkcChannelDesc = null_mut();
            let mut rq = (*packet).param[1] as CULong;
            let mut sq = (*packet).param[2] as CULong;
            let remote_channel_va = (*packet).param[3] as CULong;
            let r;

            if port < 0 || port as usize >= IHK_IKC_MAX_PORT {
                r = EINVAL;
            } else {
                let lock = listener_lock();
                let flags = __ihk_mc_spinlock_lock(lock);
                let entry = listener_entry(port);
                r = ihk_ikc_accept(
                    channel,
                    *entry,
                    (*packet).param[0] >> 32,
                    &raw mut rq,
                    &raw mut sq,
                    &raw mut new_channel,
                    remote_channel_va,
                    (*packet).param[4] as CInt,
                    ((*packet).param[4] >> 32) as CInt,
                );
                __ihk_mc_spinlock_unlock(lock, flags);
            }

            if r != 0 {
                ikc_master_send(
                    os,
                    IHK_IKC_MASTER_MSG_CONNECT_REPLY,
                    (*packet).ref_,
                    (-(r as i64)) as u64,
                    0,
                    0,
                    0,
                    0,
                );
            } else {
                (*new_channel).remote_channel_id = (*packet).ref_ as CInt;
                ihk_ikc_enable_channel(new_channel);
                ikc_master_send(
                    os,
                    IHK_IKC_MASTER_MSG_CONNECT_REPLY,
                    (*packet).ref_,
                    0,
                    rq,
                    remote_channel_va,
                    new_channel as u64,
                    0,
                );
            }
        }
        IHK_IKC_MASTER_MSG_CONNECT_REPLY => {
            ret = ihk_ikc_master_reply_handler(os, packet);
        }
        IHK_IKC_MASTER_MSG_DISCONNECT => {
            let new_channel = (*packet).param[3] as *mut IhkIkcChannelDesc;
            if new_channel.is_null() {
                ret = -ENOENT;
            } else {
                let flags = __ihk_mc_spinlock_lock(&raw mut (*new_channel).recv.lock);
                (*new_channel).flag |= IKC_FLAG_DESTROY_ACKED;
                __ihk_mc_spinlock_unlock(&raw mut (*new_channel).recv.lock, flags);

                if (*new_channel).flag & IKC_FLAG_DESTROYING == 0 {
                    ihk_ikc_disconnect(new_channel);
                }

                ret = ihk_ikc_master_reply_handler(os, packet);
            }
        }
        _ => {
            ret = call_arch_master_packet_handler(os, channel, raw_packet);
        }
    }

    ihk_ikc_release_packet(raw_packet.cast());
    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_wait_reply_prepare(
    os: *mut c_void,
    wait: *mut IhkIkcMasterWaitStruct,
    msg: u32,
    ref_: u32,
) {
    INIT_LIST_HEAD(&raw mut (*wait).list);
    (*wait).msg = msg;
    (*wait).ref_ = ref_;
    (*wait).status = 0;
    write_bytes(&raw mut (*wait).res, 0, 1);
    ihk_ikc_wait_init((&raw mut (*wait).wait).cast::<c_void>());

    let list = ihk_ikc_get_master_wait_list(os);
    let lock = ihk_ikc_get_master_wait_lock(os);
    let flags = __ihk_mc_spinlock_lock(lock);
    list_add_tail(&raw mut (*wait).list, list);
    __ihk_mc_spinlock_unlock(lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_wait_finish(os: *mut c_void, wait: *mut IhkIkcMasterWaitStruct) {
    let lock = ihk_ikc_get_master_wait_lock(os);
    let flags = __ihk_mc_spinlock_lock(lock);
    list_del(&raw mut (*wait).list);
    __ihk_mc_spinlock_unlock(lock, flags);
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_master_reply_handler(
    os: *mut c_void,
    packet: *mut IhkIkcMasterPacket,
) -> CInt {
    let list = ihk_ikc_get_master_wait_list(os);
    let lock = ihk_ikc_get_master_wait_lock(os);
    let flags = __ihk_mc_spinlock_lock(lock);
    let mut node = (*list).next;

    while node != list {
        let next = (*node).next;
        let wait = wait_from_list(node);
        if (*wait).msg == (*packet).msg && (*wait).ref_ == (*packet).ref_ {
            copy_nonoverlapping(packet, &raw mut (*wait).res, 1);
            (*wait).status = 1;
            ihk_ikc_wake_master(wait);
        }
        node = next;
    }

    __ihk_mc_spinlock_unlock(lock, flags);
    0
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_connect(os: *mut c_void, param: *mut IhkIkcConnectParam) -> CInt {
    if param.is_null() {
        return -EINVAL;
    }

    let mut rq: CULong = 0;
    let mut sq: CULong = 0;
    let channel = ihk_ikc_create_channel(
        os,
        (*param).port,
        (*param).pkt_size,
        (*param).queue_size as CULong,
        &raw mut rq,
        &raw mut sq,
        0,
    );
    if channel.is_null() {
        return -ENOMEM;
    }

    let ref_ = (*channel).channel_id as u32;
    let mut wait = IhkIkcMasterWaitStruct {
        list: ListHead {
            next: null_mut(),
            prev: null_mut(),
        },
        wait: null_mut(),
        status: 0,
        msg: 0,
        ref_: 0,
        res: IhkIkcMasterPacket {
            header_channel: null_mut(),
            msg: 0,
            ref_: 0,
            param: [0; 5],
        },
    };

    ihk_ikc_wait_reply_prepare(os, &raw mut wait, IHK_IKC_MASTER_MSG_CONNECT_REPLY, ref_);

    if ikc_master_send(
        os,
        IHK_IKC_MASTER_MSG_CONNECT,
        ref_,
        (((*param).pkt_size as u64) << 32) | ((*param).port as u32 as u64),
        sq,
        rq,
        channel as u64,
        (((*param).intr_cpu as u64) << 32) | ((*param).magic as u32 as u64),
    ) == 0
    {
        let ret = ihk_ikc_wait_master(&raw mut wait);
        ihk_ikc_wait_finish(os, &raw mut wait);

        if ret != 0 {
            ihk_ikc_free_channel(channel);
            return -EINTR;
        } else if wait.res.param[0] != 0 {
            ihk_ikc_free_channel(channel);
            return -(wait.res.param[0] as CInt);
        }

        ihk_ikc_set_remote_queue(
            &raw mut (*channel).send,
            os,
            wait.res.param[1] as CULong,
            (*param).queue_size as CULong,
        );
        (*channel).remote_channel_id = (*channel).send.cache.channel_id as CInt;
        (*channel).remote_channel_va = wait.res.param[3];
        (*channel).handler = (*param).handler;
        (*(*channel).send.queue).write_cpu = (*(*channel).recv.queue).read_cpu;
        (*channel).send.intr_cpu = (*param).intr_cpu as u32;
        ihk_ikc_enable_channel(channel);
    } else {
        ihk_ikc_wait_finish(os, &raw mut wait);
        ihk_ikc_free_channel(channel);
        return -EBUSY;
    }

    (*param).channel = channel;
    0
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_send_disconnect(channel: *mut IhkIkcChannelDesc) -> CInt {
    ikc_master_send(
        (*channel).remote_os,
        IHK_IKC_MASTER_MSG_DISCONNECT,
        (*channel).remote_channel_id as u32,
        (*channel).channel_id as u64,
        0,
        0,
        (*channel).remote_channel_va,
        0,
    )
}

#[no_mangle]
pub unsafe extern "C" fn __ihk_wait_for_disconnect_ack(channel: *mut IhkIkcChannelDesc) -> CInt {
    let os = (*channel).remote_os;
    let mut wait = IhkIkcMasterWaitStruct {
        list: ListHead {
            next: null_mut(),
            prev: null_mut(),
        },
        wait: null_mut(),
        status: 0,
        msg: 0,
        ref_: 0,
        res: IhkIkcMasterPacket {
            header_channel: null_mut(),
            msg: 0,
            ref_: 0,
            param: [0; 5],
        },
    };

    ihk_ikc_wait_reply_prepare(
        os,
        &raw mut wait,
        IHK_IKC_MASTER_MSG_DISCONNECT,
        (*channel).channel_id as u32,
    );

    if __ihk_send_disconnect(channel) != 0 {
        ihk_ikc_wait_finish(os, &raw mut wait);
        return -EBUSY;
    }

    let ret = if (*channel).flag & IKC_FLAG_DESTROY_ACKED == 0 {
        ihk_ikc_wait_master(&raw mut wait)
    } else {
        0
    };
    ihk_ikc_wait_finish(os, &raw mut wait);

    ret
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_disconnect(channel: *mut IhkIkcChannelDesc) -> CInt {
    if channel.is_null() {
        return -EINVAL;
    }

    let flags = __ihk_mc_spinlock_lock(&raw mut (*channel).lock);
    (*channel).flag &= !IKC_FLAG_ENABLED;
    if (*channel).flag & IKC_FLAG_DESTROYING != 0 {
        __ihk_mc_spinlock_unlock(&raw mut (*channel).lock, flags);
        return -EBUSY;
    }
    (*channel).flag |= IKC_FLAG_DESTROYING;
    let channel_flags = (*channel).flag;
    __ihk_mc_spinlock_unlock(&raw mut (*channel).lock, flags);

    if channel_flags & IKC_FLAG_DESTROY_ACKED == 0 {
        __ihk_wait_for_disconnect_ack(channel)
    } else {
        __ihk_send_disconnect(channel)
    }
}

#[no_mangle]
pub unsafe extern "C" fn ihk_ikc_destroy_channel(channel: *mut IhkIkcChannelDesc) {
    if channel.is_null() {
        return;
    }
    ihk_ikc_disable_channel(channel);
    ihk_ikc_free_channel(channel);
}
