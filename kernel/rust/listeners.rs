use core::{
    ffi::{c_char, c_void},
    ptr::{null_mut, read_volatile},
};

use crate::abi::{CInt, CULong, IhkIkcPacketHeader, IkcScdPacket};

const PTATTR_UNCACHABLE: CULong = 0x10000;
const TEST_PORT: CInt = 500;
const TEST_MAGIC: CInt = 0x29;
const TEST_QUEUE_SIZE: CInt = 4096;
const MAP_SIZE: CULong = 4 * 1024 * 1024;
const MAP_VIRT_SIZE: CULong = 4 * 1024;

const TEST_SUM_FMT: &[u8] = b"%ld, %ld\n\0";
const TEST_MSG_FMT: &[u8] = b"Test msg : %x, %x\n\0";
const TEST_NOSPACE_FMT: &[u8] = b"Test msg : Not enough space\n\0";
const TEST_CPU_FMT: &[u8] = b"Packet, I am %d.\n\0";

#[repr(C)]
struct IkcTestPacket {
    header: IhkIkcPacketHeader,
    msg: u32,
    param1: u32,
}

#[repr(C)]
pub struct IhkIkcChannelDesc {
    _private: [u8; 0],
}

type IkcPacketHandler =
    Option<unsafe extern "C" fn(*mut IhkIkcChannelDesc, *mut c_void, *mut c_void) -> CInt>;

#[repr(C)]
struct IhkIkcChannelInfo {
    channel: *mut IhkIkcChannelDesc,
    packet_handler: IkcPacketHandler,
}

#[repr(C)]
struct IhkIkcListenParam {
    handler: Option<unsafe extern "C" fn(*mut IhkIkcChannelInfo) -> CInt>,
    port: CInt,
    ikc_direction: CInt,
    pkt_size: CInt,
    queue_size: CInt,
    magic: CInt,
}

extern "C" {
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_map_memory(os: *mut c_void, phys: CULong, size: CULong) -> CULong;
    fn ihk_mc_map_virtual(phys: CULong, size: CULong, attr: CULong) -> *mut CULong;
    fn ihk_mc_unmap_virtual(virt: *mut CULong, size: CULong);
    fn ihk_mc_unmap_memory(os: *mut c_void, phys: CULong, size: CULong);
    fn ihk_ikc_send(c: *mut c_void, packet: *mut IkcScdPacket, flags: CInt) -> CInt;
    fn ihk_ikc_listen_port(os: *mut c_void, param: *mut IhkIkcListenParam) -> CInt;
}

#[inline(always)]
fn read_tsc() -> CULong {
    let high: u32;
    let low: u32;
    unsafe {
        core::arch::asm!("rdtsc", out("eax") low, out("edx") high, options(nomem, nostack));
    }
    ((high as CULong) << 32) | low as CULong
}

#[no_mangle]
pub unsafe extern "C" fn testmem(v: *mut c_void, size: CULong) {
    let mut i = 0;
    let mut sum: CULong = 0;
    let p = v.cast::<u8>();

    while i < size {
        sum = sum.wrapping_add(read_volatile(p.add(i as usize).cast::<CULong>()));
        i += 8;
    }

    let st = read_tsc();
    i = 0;
    while i < size {
        sum = sum.wrapping_add(read_volatile(p.add(i as usize).cast::<CULong>()));
        i += 64;
    }
    let ed = read_tsc();

    kprintf(TEST_SUM_FMT.as_ptr().cast(), ed.wrapping_sub(st), sum);
}

unsafe extern "C" fn test_packet_handler(
    c: *mut IhkIkcChannelDesc,
    packet: *mut c_void,
    _os: *mut c_void,
) -> CInt {
    let packet = packet.cast::<IkcTestPacket>();

    if (*packet).msg == 0x1111_0011 {
        kprintf(TEST_MSG_FMT.as_ptr().cast(), (*packet).msg);
        let addr = ((*packet).param1 as CULong) << 12;
        let phys = ihk_mc_map_memory(null_mut(), addr, MAP_SIZE);
        let virt = ihk_mc_map_virtual(phys, MAP_VIRT_SIZE, PTATTR_UNCACHABLE);
        if virt.is_null() {
            ihk_mc_unmap_memory(null_mut(), phys, MAP_SIZE);
            kprintf(TEST_NOSPACE_FMT.as_ptr().cast());
            return 0;
        }
        testmem(virt.cast::<c_void>(), MAP_SIZE);
        ihk_mc_unmap_virtual(virt, MAP_VIRT_SIZE);
        ihk_mc_unmap_memory(null_mut(), phys, MAP_SIZE);
    } else if (*packet).msg == 0x1111_0012 {
        let mut response = IkcTestPacket {
            header: IhkIkcPacketHeader {
                channel: null_mut(),
            },
            msg: 0x1111_0013,
            param1: 0,
        };
        let mut i = 0;
        while i < 10 {
            ihk_ikc_send(
                c.cast::<c_void>(),
                (&raw mut response).cast::<IkcScdPacket>(),
                0,
            );
            i += 1;
        }
    } else if (*packet).msg == 0x1111_001a {
        kprintf(TEST_CPU_FMT.as_ptr().cast(), ihk_mc_get_processor_id());
    }

    0
}

unsafe extern "C" fn test_handler(param: *mut IhkIkcChannelInfo) -> CInt {
    (*param).packet_handler = Some(test_packet_handler);
    0
}

#[no_mangle]
pub unsafe extern "C" fn mc_ikc_test_init() {
    let mut param = IhkIkcListenParam {
        handler: Some(test_handler),
        port: TEST_PORT,
        ikc_direction: 0,
        pkt_size: core::mem::size_of::<IkcTestPacket>() as CInt,
        queue_size: TEST_QUEUE_SIZE,
        magic: TEST_MAGIC,
    };

    ihk_ikc_listen_port(null_mut(), &raw mut param);
}
