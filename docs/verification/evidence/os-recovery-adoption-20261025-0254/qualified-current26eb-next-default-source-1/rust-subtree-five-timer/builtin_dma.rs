use core::ffi::c_void;

use crate::abi::{CInt, CULong};
use crate::spinlock_helpers::IhkSpinlock;

const BUILTIN_DMA_CHANNELS: usize = 2;
const BUILTIN_DMA_DESC_PARAM1_INTR: CInt = 0x1000_0000;
const PAGE_SIZE: CULong = 4096;

#[repr(C)]
struct BuiltinDmaDesc {
    type_: CInt,
    param1: CInt,
    param2: *mut c_void,
    param3: *mut c_void,
    param4: CULong,
}

#[repr(C)]
struct BuiltinDmaChannel {
    desc_ptr: CULong,
    len: CULong,
    head: CULong,
    tail: CULong,
    lock: IhkSpinlock,
}

#[repr(C)]
struct BuiltinDmaConfig {
    channels: [BuiltinDmaChannel; BUILTIN_DMA_CHANNELS],
    doorbell: CULong,
    status: CULong,
}

#[repr(C)]
pub struct IhkDmaRequest {
    src_os: *mut c_void,
    src_phys: CULong,
    dest_os: *mut c_void,
    dest_phys: CULong,
    size: CULong,
    callback: Option<unsafe extern "C" fn(*mut c_void)>,
    priv_: *mut c_void,
    notify_os: *mut c_void,
    notify: *mut CULong,
}

static mut BUILTIN_MC_DMA_CONFIG: *mut BuiltinDmaConfig = core::ptr::null_mut();
static mut DESC_PTRS: [*mut BuiltinDmaDesc; BUILTIN_DMA_CHANNELS] =
    [core::ptr::null_mut(); BUILTIN_DMA_CHANNELS];

unsafe extern "C" {
    fn map_fixed_area(phys: CULong, size: CULong, flags: CULong) -> *mut c_void;
    fn kprintf(format: *const i8, ...) -> CInt;
    fn ihk_mc_get_hardware_processor_id() -> CInt;
}

const _: () = {
    use core::mem::{align_of, offset_of, size_of};

    assert!(size_of::<BuiltinDmaDesc>() == 32);
    assert!(align_of::<BuiltinDmaDesc>() == 8);
    assert!(size_of::<BuiltinDmaChannel>() == 40);
    assert!(offset_of!(BuiltinDmaChannel, lock) == 32);
    assert!(size_of::<BuiltinDmaConfig>() == 96);
    assert!(size_of::<IhkDmaRequest>() == 72);
    assert!(offset_of!(IhkDmaRequest, src_phys) == 8);
    assert!(offset_of!(IhkDmaRequest, notify) == 64);
};

#[inline(always)]
unsafe fn next(channel: *mut BuiltinDmaChannel, mut cursor: CULong) -> CULong {
    cursor = cursor.wrapping_add(1);
    if cursor >= (*channel).len {
        cursor = 0;
    }
    cursor
}

#[inline(always)]
unsafe fn desc_check_room(channel: *mut BuiltinDmaChannel, ndesc: CInt) -> bool {
    let h = (*channel).head as CInt;
    let mut t = (*channel).tail as CInt;

    if t <= h {
        t = t.wrapping_add((*channel).len as CInt);
    }

    h.wrapping_add(ndesc) < t
}

#[no_mangle]
pub unsafe extern "C" fn builtin_mc_dma_init(cfg_addr: CULong) {
    BUILTIN_MC_DMA_CONFIG = map_fixed_area(
        cfg_addr,
        core::mem::size_of::<BuiltinDmaConfig>() as CULong,
        0,
    )
    .cast();

    kprintf(c"DMA Config: %lx".as_ptr().cast(), cfg_addr);
    let mut i = 0;
    while i < BUILTIN_DMA_CHANNELS {
        DESC_PTRS[i] =
            map_fixed_area((*BUILTIN_MC_DMA_CONFIG).channels[i].desc_ptr, PAGE_SIZE, 0).cast();
        kprintf(
            c" (%lx)".as_ptr().cast(),
            (*BUILTIN_MC_DMA_CONFIG).channels[i].desc_ptr,
        );
        i += 1;
    }
    kprintf(c"\n".as_ptr().cast());
}

#[no_mangle]
pub unsafe extern "C" fn ihk_mc_dma_request(_channel: CInt, req: *mut IhkDmaRequest) -> CInt {
    let mut ndesc = 1;
    let c = &raw mut (*BUILTIN_MC_DMA_CONFIG).channels[1];

    if (*req).callback.is_some() || !(*req).notify.is_null() {
        ndesc += 1;
    }

    let flags = crate::spinlock_helpers::__ihk_mc_spinlock_lock(&raw mut (*c).lock);

    if !desc_check_room(c, ndesc) {
        crate::spinlock_helpers::__ihk_mc_spinlock_unlock(&raw mut (*c).lock, flags);
        return -16;
    }

    let mut h = (*c).head;
    let desc_head = DESC_PTRS[1];
    let mut desc = desc_head.add(h as usize);
    (*desc).type_ = 1;
    (*desc).param1 = 0;
    (*desc).param2 = (*req).src_phys as *mut c_void;
    (*desc).param3 = (*req).dest_phys as *mut c_void;
    (*desc).param4 = (*req).size;

    h = next(c, h);

    if ndesc > 1 {
        desc = desc_head.add(h as usize);
        (*desc).type_ = 2;
        (*desc).param1 = 0;

        if (*req).callback.is_some() {
            (*desc).param1 = ihk_mc_get_hardware_processor_id() | BUILTIN_DMA_DESC_PARAM1_INTR;
        } else if !(*req).notify.is_null() {
            (*desc).param2 = (*req).notify.cast();
            (*desc).param4 = (*req).priv_ as CULong;
        }
        h = next(c, h);
    }

    (*c).head = h;
    crate::spinlock_helpers::__ihk_mc_spinlock_unlock(&raw mut (*c).lock, flags);
    (*BUILTIN_MC_DMA_CONFIG).doorbell = 1;
    0
}
