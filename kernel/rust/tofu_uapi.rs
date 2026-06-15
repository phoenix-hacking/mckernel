#![allow(non_snake_case)]

use core::ffi::c_void;

type CInt = i32;
type CLong = i64;
type CULong = u64;
type PhysAddr = u64;

const TOF_RSC_TNI0_TOQ0: CInt = 0;
const TOF_RSC_TNI0_TCQ0: CInt = 72;
const TOF_RSC_TNI0_MRQ0: CInt = 144;
const TOF_RSC_TNI0_PBQ: CInt = 216;
const TOF_RSC_TNI0_PRQ: CInt = 222;
const TOF_RSC_TNI0_STEERINGTABLE0: CInt = 228;
const TOF_RSC_TNI0_MBTABLE0: CInt = 297;
const TOF_ICC_RH_LEN: CULong = 8;
const TOF_ICC_ECRC_LEN: CULong = 4;
const TOF_ICC_FRAME_ALIGN: CULong = 32;
const TOF_ICC_FRAME_LEN_MIN: CULong = TOF_ICC_RH_LEN + (2 + 1) * TOF_ICC_FRAME_ALIGN;
const TOF_ICC_REG_PA: PhysAddr = 0x40000000;
const TOF_ICC_TOQ_DESC_SIZE: CInt = 1 << 5;
const TOF_ICC_TCQ_DESC_SIZE: CInt = 1 << 3;
const TOF_ICC_MRQ_DESC_SIZE: CInt = 1 << 5;
const TOF_ICC_PBQ_DESC_SIZE: CInt = 1 << 3;
const TOF_ICC_PRQ_DESC_SIZE: CInt = 1 << 3;
const EINVAL: CInt = 22;
const EFAULT: CInt = 14;
const ENOENT: CInt = 2;
const ENOSPC: CInt = 28;
const EPERM: CInt = 1;
const EBUSY: CInt = 16;
const ENOTTY: CInt = 25;
const ETIMEDOUT: CInt = 110;
const ENOTSUPP: CInt = 524;
const TOF_TRANS_START_MASK: CULong = (1_u64 << 36) - 1;
const TOF_TRANS_LEN_MASK: CULong = (1_u64 << 27) - 1;
const TOF_ICC_STEERING_READONLY_SHIFT: u32 = 6;
const TOF_ICC_STEERING_ENABLE_SHIFT: u32 = 7;
const TOF_ICC_STEERING_MBVA_SHIFT: u32 = 8;
const TOF_ICC_STEERING_MBVA_MASK: CULong = (1_u64 << 32) - 1;
const TOF_ICC_STEERING_MBID_SHIFT: u32 = 48;
const TOF_ICC_STEERING_MBID_MASK: CULong = (1_u64 << 16) - 1;
const TOF_ICC_STEERING_MUT_MASK: CULong = (1_u64 << TOF_ICC_STEERING_READONLY_SHIFT)
    | (1_u64 << TOF_ICC_STEERING_ENABLE_SHIFT)
    | (TOF_ICC_STEERING_MBVA_MASK << TOF_ICC_STEERING_MBVA_SHIFT)
    | (TOF_ICC_STEERING_MBID_MASK << TOF_ICC_STEERING_MBID_SHIFT);
const TOF_ICC_MB_PS_MASK: CULong = (1_u64 << 3) - 1;
const TOF_ICC_MB_ENABLE_SHIFT: u32 = 7;
const TOF_ICC_MB_IPA_SHIFT: u32 = 8;
const TOF_ICC_MB_IPA_MASK: CULong = (1_u64 << 32) - 1;
const TOF_ICC_MB_MUT_MASK: CULong = TOF_ICC_MB_PS_MASK
    | (1_u64 << TOF_ICC_MB_ENABLE_SHIFT)
    | (TOF_ICC_MB_IPA_MASK << TOF_ICC_MB_IPA_SHIFT);
const TOF_ICC_MBPT_ENABLE_SHIFT: u32 = 7;
const TOF_ICC_MBPT_IPA_SHIFT: u32 = 12;
const TOF_ICC_MBPT_IPA_MASK: CULong = (1_u64 << 28) - 1;
const TOF_ICC_MBPT_MUT_MASK: CULong =
    (1_u64 << TOF_ICC_MBPT_ENABLE_SHIFT) | (TOF_ICC_MBPT_IPA_MASK << TOF_ICC_MBPT_IPA_SHIFT);
const TOF_ICC_REG_BGS_SIGNAL_MASK_SIG_RECV: CULong = 1_u64 << 63;
const TOF_ICC_REG_BGS_SIGNAL_MASK_TLP_RECV: CULong = 1_u64 << 62;
const TOF_ICC_REG_BGS_SIGNAL_MASK_SIG_SEND: CULong = 1_u64 << 61;
const TOF_ICC_REG_BGS_SIGNAL_MASK_TLP_SEND: CULong = 1_u64 << 60;
const TOF_ICC_REG_BGS_LOCAL_LINK_BGID_RECV: CULong = 0x0000003f00000000;
const TOF_ICC_REG_BGS_LOCAL_LINK_BGID_SEND: CULong = 0x000000000000003f;
const TOF_ICC_REG_BGS_REMOTE_LINK_BG_ADDRESS_RECV: CULong = 0x0fffffff00000000;
const TOF_ICC_REG_BGS_REMOTE_LINK_BG_ADDRESS_SEND: CULong = 0x00000000ffffffff;
const TOF_ICC_REG_BGS_ENABLE: CLong = 0x0;
const TOF_ICC_REG_BGS_STATE: CLong = 0x30;
const TOF_ICC_REG_BGS_STATE_ENABLE: CULong = 1;
const TOF_ICC_REG_BGS_SIGNAL_MASK: CLong = 0x58;
const TOF_ICC_REG_BGS_LOCAL_LINK: CLong = 0x60;
const TOF_ICC_REG_BGS_REMOTE_LINK: CLong = 0x68;
const TOF_ICC_REG_BGS_SUBNET_SIZE: CLong = 0x70;
const TOF_ICC_REG_BGS_GPID_BSEQ: CLong = 0x78;
const TOF_ICC_REG_BGS_BCH_MASK: CLong = 0x800;
const TOF_ICC_REG_BGS_BCH_MASK_STATUS: CLong = 0x808;
const TOF_ICC_REG_BGS_BCH_MASK_STATUS_RUN: CULong = 1_u64 << 63;
const TOF_ICC_REG_BGS_BCH_NOTICE_IPA: CLong = 0x810;
const TOF_ICC_REG_BGS_BCH_MASK_MASK: CULong = 1_u64 << 63;

#[repr(C)]
pub struct TofuUtofuTransList {
    prev: i16,
    next: i16,
    pgszbits: u8,
    mbpt: *mut c_void,
}

#[repr(C)]
pub struct TofuTransTable {
    steering: CULong,
    mbpt: CULong,
}

#[repr(C)]
pub struct TofuAddr {
    pa: u8,
    pb: u8,
    pc: u8,
    x: u8,
    y: u8,
    z: u8,
    a: u8,
    b: u8,
    c: u8,
}

#[repr(C)]
pub struct TofuSetBg {
    tni: CInt,
    gate: CInt,
    source_lgate: CInt,
    source_raddr: TofuAddr,
    source_rtni: CInt,
    source_rgate: CInt,
    dest_lgate: CInt,
    dest_raddr: TofuAddr,
    dest_rtni: CInt,
    dest_rgate: CInt,
}

#[repr(C)]
pub struct TofuEnableBch {
    addr: *mut c_void,
    bseq: CInt,
    num: CInt,
    bgs: *const TofuSetBg,
}

#[repr(C)]
pub struct TofuFreeStags {
    num: u16,
    stags: *mut CInt,
}

#[repr(C)]
pub struct TofuAllocStag {
    flags: u32,
    stag: CInt,
    offset: CULong,
    va: *mut c_void,
    len: CULong,
}

#[repr(C)]
pub struct TofuGlobals {
    tof_ib_stag_lock_addr: CULong,
    tof_ib_stag_list_addr: CULong,
    tof_ib_stag_list_Rp_addr: CULong,
    tof_ib_stag_list_Wp_addr: CULong,
    tof_ib_mbpt_mem_addr: CULong,
    tof_ib_steering_addr: CULong,
    tof_ib_mb_addr: CULong,
    tof_core_cq_addr: CULong,
    tof_core_bg_addr: CULong,
    tof_utofu_bg_addr: CULong,
    tof_utofu_handler_bg_signal_addr: CULong,
    linux_vmalloc_start: CULong,
    linux_vmalloc_end: CULong,
}

type TofuAtomicSetFn = unsafe extern "C" fn(*mut c_void, CULong);
type TofuLockFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type TofuUnlockFn = unsafe extern "C" fn(*mut c_void, CULong);
type TofuWmbFn = unsafe extern "C" fn();
type TofuBgUnsetFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type TofuBgUnregisterFn = unsafe extern "C" fn(CInt, CInt);
type TofuSignalHandlerFn = unsafe extern "C" fn(CInt, CInt, CULong, CULong);
type TofuCoreBgGetFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type TofuCoreBgPublishFn = unsafe extern "C" fn(*mut c_void, CULong, u32);
type TofuCoreBgLockFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type TofuCoreBgUnlockFn = unsafe extern "C" fn(*mut c_void, CULong);
type TofuCoreBgFn = unsafe extern "C" fn(*mut c_void);
type TofuCoreBgRegFn = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type TofuWriteqFn = unsafe extern "C" fn(CULong, *mut c_void, CLong);
type TofuReadqSpinFn = unsafe extern "C" fn(*mut c_void, CLong, CULong, CULong, CULong) -> CInt;
type TofuUtofuBgGetFn = unsafe extern "C" fn(CInt, CInt) -> *mut c_void;
type TofuUtofuBgMetaFn = unsafe extern "C" fn(*mut c_void, *mut CULong, *mut u32, *mut u8) -> CInt;
type TofuUtofuBgSetEnabledFn = unsafe extern "C" fn(*mut c_void, u8);
type TofuCoreSetBgFn = unsafe extern "C" fn(*const TofuSetBg, CULong, u32, u32) -> CInt;
type TofuBchBgmaskSetFn = unsafe extern "C" fn(*mut c_void, CInt, CInt) -> CInt;
type TofuRegisterSignalBgFn = unsafe extern "C" fn(CInt, CInt, Option<TofuSignalHandlerFn>);
type TofuUnsetBgPtrFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type TofuCoreDisableBchFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type TofuUnsetBgByIdFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
type TofuErrorLogFn = unsafe extern "C" fn(CInt);
type TofuBarrierFn = unsafe extern "C" fn();
type TofuBchDeviceLogFn = unsafe extern "C" fn(*mut c_void);
type TofuDisableBchPtrFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type TofuPathKindFn = unsafe extern "C" fn(*const c_void) -> CInt;
type TofuReleaseDeviceFn = unsafe extern "C" fn(*mut c_void);
type TofuReleaseLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type TofuReleaseFdFn = unsafe extern "C" fn(*mut c_void, CInt);
type TofuIoctlFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type TofuTimestampFn = unsafe extern "C" fn() -> CULong;
type TofuProfileEventFn = unsafe extern "C" fn(CInt, CULong);
type TofuUnknownIoctlLogFn = unsafe extern "C" fn(CInt);
type TofuCopyStagsFn = unsafe extern "C" fn(*mut CInt, *const CInt, CULong) -> CInt;
type TofuCopyReqOutFn = unsafe extern "C" fn(*mut c_void, *const TofuFreeStags) -> CInt;
type TofuFreeOneStagFn = unsafe extern "C" fn(*mut c_void, CInt) -> CInt;
type TofuRemoveStagRangeFn = unsafe extern "C" fn(CInt);
type TofuFreeStagsLogOutFn = unsafe extern "C" fn(*mut c_void, u16, *mut CInt, CInt);
type TofuFreeStagQueryFn = unsafe extern "C" fn(*mut c_void, CInt) -> CInt;
type TofuFreeStagFn = unsafe extern "C" fn(*mut c_void, CInt);
type TofuFreeStagProfileFn = unsafe extern "C" fn(*mut c_void, CInt);
type TofuEnableBchFn = unsafe extern "C" fn(CInt, CInt, CULong) -> CInt;
type TofuSetBgFn = unsafe extern "C" fn(*mut c_void, *const TofuSetBg, CInt, u32) -> CInt;
type TofuUnsetBgUserFn = unsafe extern "C" fn(*const TofuSetBg) -> CInt;
type TofuGetGlobalsFn = unsafe extern "C" fn() -> *mut c_void;
type TofuGlobalsPtrFn = unsafe extern "C" fn(*const c_void);
type TofuInitLockFn = unsafe extern "C" fn(CInt, CInt);
type TofuCurrentEnabledFn = unsafe extern "C" fn() -> CInt;
type TofuClearRangeFn = unsafe extern "C" fn(*mut c_void, *mut c_void) -> CInt;
type TofuVoidFn = unsafe extern "C" fn();
type TofuCqRegFn = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type TofuCacheflushTimeoutFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type TofuCacheflushLogFn = unsafe extern "C" fn(CInt, CInt, CInt);
type TofuPanicFn = unsafe extern "C" fn();
type TofuCalcMbptstartFn = unsafe extern "C" fn(CLong, CLong, CULong, u8, *mut CULong) -> CInt;
type TofuAllocMbptFn = unsafe extern "C" fn(*mut c_void, CULong, *mut *mut c_void, CInt) -> CInt;
type TofuSetMbptMetaFn = unsafe extern "C" fn(*mut c_void, CULong, CULong);
type TofuMbptIovaFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type TofuUpdateMbptEntriesFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong, u32, CULong, CInt) -> CInt;
type TofuFreeMbptFn = unsafe extern "C" fn(*mut c_void, *mut c_void);
type TofuEnableMbFn = unsafe extern "C" fn(*mut c_void, CInt, CULong, u8, CULong);
type TofuEnableSteeringFn = unsafe extern "C" fn(*mut c_void, CInt, CULong, CULong, CInt);
type TofuTransEnableFn =
    unsafe extern "C" fn(*mut c_void, CInt, CULong, CULong, CULong, CULong, u8, *mut c_void);
type TofuDeviceToCqFn = unsafe extern "C" fn(*mut c_void) -> *mut c_void;
type TofuCurrentVmFn = unsafe extern "C" fn() -> *mut c_void;
type TofuCopyAllocStagInFn = unsafe extern "C" fn(*mut TofuAllocStag, CULong) -> CInt;
type TofuCopyAllocStagOutFn = unsafe extern "C" fn(CULong, *const TofuAllocStag) -> CInt;
type TofuUcqEnabledFn = unsafe extern "C" fn(*mut c_void) -> CInt;
type TofuUcqStagEnabledFn = unsafe extern "C" fn(*mut c_void, CInt) -> CInt;
type TofuVmLockFn = unsafe extern "C" fn(*mut c_void);
type TofuRangeLookupFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> *mut c_void;
type TofuStackFaultableFn = unsafe extern "C" fn(*mut c_void, CULong, CULong) -> CInt;
type TofuPageFaultFn = unsafe extern "C" fn(*mut c_void, CULong) -> CInt;
type TofuPagesizeLockedFn = unsafe extern "C" fn(CULong, CULong, *mut u8, CInt) -> CInt;
type TofuCqLockFn = unsafe extern "C" fn(*mut c_void);
type TofuTransSearchFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, u8, CInt) -> CInt;
type TofuReserveStagFn = unsafe extern "C" fn(*mut c_void, CInt) -> CInt;
type TofuAllocNewSteeringFn =
    unsafe extern "C" fn(*mut c_void, CInt, CULong, CULong, u8, CULong, CInt) -> CInt;
type TofuGetMbptStartFn = unsafe extern "C" fn(*mut c_void, CInt) -> CULong;
type TofuRangeInsertFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong, *mut c_void, CInt);
type TofuReleaseCqDisabledLogFn = unsafe extern "C" fn(CInt, CInt);
type TofuReleaseCqDrainFn = unsafe extern "C" fn(*mut c_void, CInt);
type TofuReleaseCqDoneLogFn = unsafe extern "C" fn(*mut c_void);

const TOFU_RELEASE_KIND_CQ: CInt = 1;
const TOFU_RELEASE_KIND_BCH: CInt = 2;
const TOFU_FREE_STAG_PROFILE_PRE: CInt = 1;
const TOFU_FREE_STAG_PROFILE_CQFLUSH: CInt = 2;
const TOFU_FREE_STAG_PROFILE_DEALLOC: CInt = 3;
const TOFU_FREE_STAG_PROFILE_TOTAL: CInt = 4;

#[inline(always)]
fn tni_cqid_index(base: CInt, tni: CInt, cqid: CInt) -> CInt {
    base + tni * 12 + cqid
}

#[inline(always)]
fn size_bits(size: CInt) -> CInt {
    size.wrapping_mul(2).wrapping_add(11)
}

#[inline(always)]
fn size_from_index(size: CInt) -> CInt {
    1_i32.wrapping_shl(size_bits(size) as u32)
}

#[inline(always)]
fn tni_resource_pa(base: PhysAddr, tni: CInt, id: CInt) -> PhysAddr {
    base.wrapping_add((tni as PhysAddr).wrapping_mul(0x1000000))
        .wrapping_add((id as PhysAddr).wrapping_mul(0x10000))
}

#[inline(always)]
fn tofu_round_up(x: CULong, y: CULong) -> CULong {
    (x.wrapping_sub(1) | y.wrapping_sub(1)).wrapping_add(1)
}

#[inline(always)]
fn tofu_align_down(x: CULong, y: CULong) -> CULong {
    x & !y.wrapping_sub(1)
}

#[inline(always)]
fn tofu_align_up(x: CULong, y: CULong) -> CULong {
    tofu_align_down(x.wrapping_add(y.wrapping_sub(1)), y)
}

#[inline(always)]
fn tofu_trans_entry_value(
    start: CULong,
    len: CULong,
    pgszbits: u8,
    page_shift: CInt,
    ps_code_64kb: CInt,
    ps_code_2mb: CInt,
) -> CULong {
    if page_shift < 0 || page_shift >= 64 {
        return 0;
    }

    let shift = page_shift as u32;
    let ps_code = if pgszbits as CInt == page_shift {
        ps_code_64kb
    } else {
        ps_code_2mb
    };

    ((start >> shift) & TOF_TRANS_START_MASK)
        | (((len >> shift) & TOF_TRANS_LEN_MASK) << 36)
        | (((ps_code as CULong) & 1) << 63)
}

#[inline(always)]
fn valid_shift(shift: CInt) -> Option<u32> {
    if (0..64).contains(&shift) {
        Some(shift as u32)
    } else {
        None
    }
}

#[inline(always)]
fn trans_entry_start(entry: CULong, page_shift: CInt) -> CULong {
    let Some(shift) = valid_shift(page_shift) else {
        return 0;
    };
    (entry & TOF_TRANS_START_MASK) << shift
}

#[inline(always)]
fn trans_entry_len(entry: CULong, page_shift: CInt) -> CULong {
    let Some(shift) = valid_shift(page_shift) else {
        return 0;
    };
    ((entry >> 36) & TOF_TRANS_LEN_MASK) << shift
}

#[inline(always)]
unsafe fn read_u64(ptr: *const c_void) -> CULong {
    unsafe { core::ptr::read_volatile(ptr as *const CULong) }
}

#[inline(always)]
unsafe fn write_u64(ptr: *mut c_void, value: CULong) {
    unsafe {
        core::ptr::write_volatile(ptr as *mut CULong, value);
    }
}

#[inline(always)]
fn set_field(word: CULong, mask: CULong, shift: u32, value: CULong) -> CULong {
    (word & !(mask << shift)) | ((value & mask) << shift)
}

#[inline(always)]
fn tofu_mask_set(val: CULong, mask: CULong) -> CULong {
    let shift = mask & (!mask).wrapping_add(1);
    val.wrapping_mul(shift) & mask
}

#[inline(always)]
fn subnet_field(subnet: CULong, shift: u32) -> CInt {
    ((subnet >> shift) & 0x3f) as CInt
}

#[inline(always)]
fn subnet_axis_includes(n: CInt, s: CInt, l: CInt, p: CInt) -> bool {
    if l == 0 {
        p < n
    } else {
        let adjusted = if p < s { p + n } else { p };
        adjusted < s + l
    }
}

#[inline(always)]
fn subnet_includes(subnet: CULong, px: u8, py: u8, pz: u8) -> bool {
    let lz = subnet_field(subnet, 0);
    let sz = subnet_field(subnet, 6);
    let nz = subnet_field(subnet, 12);
    let ly = subnet_field(subnet, 18);
    let sy = subnet_field(subnet, 24);
    let ny = subnet_field(subnet, 30);
    let lx = subnet_field(subnet, 36);
    let sx = subnet_field(subnet, 42);
    let nx = subnet_field(subnet, 48);

    subnet_axis_includes(nx, sx, lx, px as CInt)
        && subnet_axis_includes(ny, sy, ly, py as CInt)
        && subnet_axis_includes(nz, sz, lz, pz as CInt)
}

#[inline(always)]
unsafe fn pack_remote_bg(addr: *const TofuAddr, tni: CULong, gate: CLong) -> Option<CULong> {
    if addr.is_null() {
        return None;
    }

    let addr = unsafe { &*addr };
    Some(
        ((gate as CULong) & 0x3f)
            | ((tni & 0x7) << 6)
            | (((addr.c as CULong) & 0x1) << 9)
            | (((addr.b as CULong) & 0x3) << 10)
            | (((addr.a as CULong) & 0x1) << 12)
            | (((addr.z as CULong) & 0x1f) << 13)
            | (((addr.y as CULong) & 0x1f) << 18)
            | (((addr.x as CULong) & 0x1f) << 23)
            | (((addr.pc as CULong) & 0x1) << 28)
            | (((addr.pb as CULong) & 0x3) << 29)
            | (((addr.pa as CULong) & 0x1) << 31),
    )
}

#[no_mangle]
pub extern "C" fn TOF_RSC_TOQ(tni: CInt, cqid: CInt) -> CInt {
    tni_cqid_index(TOF_RSC_TNI0_TOQ0, tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_RSC_TCQ(tni: CInt, cqid: CInt) -> CInt {
    tni_cqid_index(TOF_RSC_TNI0_TCQ0, tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_RSC_MRQ(tni: CInt, cqid: CInt) -> CInt {
    tni_cqid_index(TOF_RSC_TNI0_MRQ0, tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_RSC_PBQ(tni: CInt) -> CInt {
    TOF_RSC_TNI0_PBQ + tni
}

#[no_mangle]
pub extern "C" fn TOF_RSC_PRQ(tni: CInt) -> CInt {
    TOF_RSC_TNI0_PRQ + tni
}

#[no_mangle]
pub extern "C" fn TOF_RSC_STT(tni: CInt, cqid: CInt) -> CInt {
    tni_cqid_index(TOF_RSC_TNI0_STEERINGTABLE0, tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_RSC_MBT(tni: CInt, cqid: CInt) -> CInt {
    tni_cqid_index(TOF_RSC_TNI0_MBTABLE0, tni, cqid)
}

#[no_mangle]
pub extern "C" fn GENMASK(h: CInt, l: CInt) -> CULong {
    if h < l || l < 0 || h >= 64 {
        return 0;
    }

    (!0_u64).wrapping_shl(l as u32) & (!0_u64).wrapping_shr((63 - h) as u32)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_TLP_LEN(len: CInt) -> CInt {
    len.wrapping_add(1)
        .wrapping_mul(TOF_ICC_FRAME_ALIGN as CInt)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_FRAME_LEN(len: CInt) -> CInt {
    (TOF_ICC_RH_LEN as CInt).wrapping_add(TOF_ICC_TLP_LEN(len))
}

#[no_mangle]
pub extern "C" fn TOF_ICC_TOQ_SIZE_BITS(size: CInt) -> CInt {
    size_bits(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_TOQ_SIZE(size: CInt) -> CInt {
    size_from_index(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_TOQ_LEN(size: CInt) -> CInt {
    TOF_ICC_TOQ_SIZE(size).wrapping_mul(TOF_ICC_TOQ_DESC_SIZE)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_TCQ_LEN(size: CInt) -> CInt {
    TOF_ICC_TOQ_SIZE(size).wrapping_mul(TOF_ICC_TCQ_DESC_SIZE)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_MRQ_SIZE_BITS(size: CInt) -> CInt {
    size_bits(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_MRQ_SIZE(size: CInt) -> CInt {
    size_from_index(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_MRQ_LEN(size: CInt) -> CInt {
    TOF_ICC_MRQ_SIZE(size).wrapping_mul(TOF_ICC_MRQ_DESC_SIZE)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PBQ_SIZE_BITS(size: CInt) -> CInt {
    size_bits(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PBQ_SIZE(size: CInt) -> CInt {
    size_from_index(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PBQ_LEN(size: CInt) -> CInt {
    TOF_ICC_PBQ_SIZE(size).wrapping_mul(TOF_ICC_PBQ_DESC_SIZE)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PRQ_SIZE_BITS(size: CInt) -> CInt {
    size_bits(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PRQ_SIZE(size: CInt) -> CInt {
    size_from_index(size)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_PRQ_LEN(size: CInt) -> CInt {
    TOF_ICC_PRQ_SIZE(size).wrapping_mul(TOF_ICC_PRQ_DESC_SIZE)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_MB_PS_ENCODE(bits: CInt) -> CInt {
    if bits % 9 == 3 {
        bits / 9 - 1
    } else {
        bits / 13 + 3
    }
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_CQ_PA(tni: CInt, cqid: CInt) -> PhysAddr {
    tni_resource_pa(TOF_ICC_REG_PA, tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_BCH_PA(tni: CInt, bgid: CInt) -> PhysAddr {
    tni_resource_pa(TOF_ICC_REG_PA.wrapping_add(0x0000e00000), tni, bgid)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_CQS_PA(tni: CInt, cqid: CInt) -> PhysAddr {
    tni_resource_pa(TOF_ICC_REG_PA.wrapping_add(0x0000400000), tni, cqid)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_BGS_PA(tni: CInt, bgid: CInt) -> PhysAddr {
    tni_resource_pa(TOF_ICC_REG_PA.wrapping_add(0x0000800000), tni, bgid)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TNI_PA(tni: CInt) -> PhysAddr {
    TOF_ICC_REG_PA
        .wrapping_add(0x0000c00000)
        .wrapping_add((tni as PhysAddr).wrapping_mul(0x1000000))
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_PORT_PA(port: CInt) -> PhysAddr {
    TOF_ICC_REG_PA
        .wrapping_add(0x0006000000)
        .wrapping_add((port as PhysAddr).wrapping_mul(0x1000))
}

#[no_mangle]
pub extern "C" fn TOF_ICC_XB_TC_DATA_CYCLE_COUNT(tni: CInt) -> CInt {
    tni.wrapping_mul(0x10)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_XB_TC_WAIT_CYCLE_COUNT(tni: CInt) -> CInt {
    tni.wrapping_mul(0x10).wrapping_add(0x8)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_XB_TD_DATA_CYCLE_COUNT(tnr: CInt) -> CInt {
    tnr.wrapping_mul(0x10).wrapping_add(0x60)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_XB_TD_WAIT_CYCLE_COUNT(tnr: CInt) -> CInt {
    tnr.wrapping_mul(0x10).wrapping_add(0x68)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TD_TLP_FILTER(tnr: CInt) -> CInt {
    tnr.wrapping_mul(0x10).wrapping_add(0x10)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TD_SETTINGS(tnr: CInt) -> CInt {
    tnr.wrapping_mul(0x10).wrapping_add(0x18)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_VMS(tni: CInt, vmsid: CInt) -> CInt {
    tni.wrapping_mul(0x100)
        .wrapping_add(vmsid.wrapping_mul(0x8))
        .wrapping_add(0x100)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_VMS_CQ00(tni: CInt) -> CInt {
    tni.wrapping_mul(0x100).wrapping_add(0x180)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_VMS_BG00(tni: CInt) -> CInt {
    tni.wrapping_mul(0x100).wrapping_add(0x1a0)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_VMS_BG16(tni: CInt) -> CInt {
    tni.wrapping_mul(0x100).wrapping_add(0x1a8)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_VMS_BG32(tni: CInt) -> CInt {
    tni.wrapping_mul(0x100).wrapping_add(0x1b0)
}

#[no_mangle]
pub extern "C" fn TOF_ICC_REG_TOFU_TNI_MSI_BASE(tni: CInt) -> CInt {
    tni.wrapping_mul(0x100).wrapping_add(0x1c0)
}

#[no_mangle]
pub extern "C" fn tof_icc_get_framelen(len: CInt) -> CInt {
    let frame_len = TOF_ICC_RH_LEN.wrapping_add(tofu_round_up(
        (len as CULong).wrapping_add(TOF_ICC_ECRC_LEN),
        TOF_ICC_FRAME_ALIGN,
    ));

    if frame_len < TOF_ICC_FRAME_LEN_MIN {
        TOF_ICC_FRAME_LEN_MIN as CInt
    } else {
        frame_len as CInt
    }
}

#[no_mangle]
pub extern "C" fn tofu_indexed_2d_ptr_body_result(
    base: *mut c_void,
    major: CInt,
    minor: CInt,
    major_limit: CInt,
    minor_limit: CInt,
    elem_size: CULong,
) -> *mut c_void {
    if (major as u32) >= major_limit as u32 || (minor as u32) >= minor_limit as u32 {
        return core::ptr::null_mut();
    }

    let index = (major as usize)
        .wrapping_mul(minor_limit as usize)
        .wrapping_add(minor as usize);
    let offset = index.wrapping_mul(elem_size as usize);
    (base as usize).wrapping_add(offset) as *mut c_void
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_calc_mbptstart_body_result(
    start: CLong,
    _end: CLong,
    _mbpt_npages: CULong,
    _pgszbits: u8,
    mbptstart: *mut CULong,
) -> CInt {
    if mbptstart.is_null() {
        return -EINVAL;
    }
    unsafe {
        *mbptstart = start as CULong;
    }
    0
}

#[no_mangle]
pub extern "C" fn tofu_ib_dmaaddr_pack_result(stag: u32, offset: u32) -> CULong {
    ((stag as CULong) << 32) | offset as CULong
}

#[no_mangle]
pub extern "C" fn tofu_ib_dmaaddr_stag_result(dmaaddr: CULong) -> u32 {
    (dmaaddr >> 32) as u32
}

#[no_mangle]
pub unsafe extern "C" fn tofu_ib_stag_alloc_body_result(
    list: *const i16,
    read_pos: *mut CInt,
    write_pos: *const CInt,
    max_stag: CInt,
) -> i16 {
    if list.is_null() || read_pos.is_null() || write_pos.is_null() || max_stag <= 0 {
        return -(EINVAL as i16);
    }

    let rp = unsafe { *read_pos };
    let wp = unsafe { *write_pos };
    if rp == wp {
        return -(ENOENT as i16);
    }
    if rp < 0 || rp >= max_stag || wp < 0 || wp >= max_stag {
        return -(EINVAL as i16);
    }

    let ret = unsafe { *list.add(rp as usize) };
    unsafe {
        *read_pos = (rp + 1) % max_stag;
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn tofu_ib_stag_free_body_result(
    list: *mut i16,
    read_pos: *const CInt,
    write_pos: *mut CInt,
    stag: i16,
    max_stag: CInt,
) -> CInt {
    if list.is_null() || read_pos.is_null() || write_pos.is_null() || max_stag <= 0 {
        return -EINVAL;
    }

    let rp = unsafe { *read_pos };
    let wp = unsafe { *write_pos };
    if rp < 0 || rp >= max_stag || wp < 0 || wp >= max_stag {
        return -EINVAL;
    }

    let next = (wp + 1) % max_stag;
    if next != rp {
        unsafe {
            *list.add(wp as usize) = stag;
            *write_pos = next;
        }
        return 1;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_mru_delete_body_result(
    mru: *mut TofuUtofuTransList,
    mruhead: *mut CInt,
    stag: CInt,
    empty_stag: CInt,
) -> CInt {
    if mru.is_null() || mruhead.is_null() || stag < 0 {
        return -EINVAL;
    }

    let entry = unsafe { mru.add(stag as usize) };
    let prev = unsafe { (*entry).prev as CInt };
    let next = unsafe { (*entry).next as CInt };
    if prev == empty_stag || next == empty_stag {
        return 0;
    }

    if prev == stag {
        unsafe {
            *mruhead = empty_stag;
        }
    } else {
        unsafe {
            if *mruhead == stag {
                *mruhead = next;
            }
            (*mru.add(prev as usize)).next = next as i16;
            (*mru.add(next as usize)).prev = prev as i16;
        }
    }

    unsafe {
        (*entry).prev = empty_stag as i16;
        (*entry).next = empty_stag as i16;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_unset_bg_body_result(
    enabled: *mut u8,
    tni: CInt,
    bgid: CInt,
    unset_fn: Option<TofuBgUnsetFn>,
    unregister_fn: Option<TofuBgUnregisterFn>,
) -> CInt {
    if enabled.is_null() {
        return -EINVAL;
    }

    if unsafe { *enabled } != 0 {
        let Some(unset) = unset_fn else {
            return -EINVAL;
        };
        let Some(unregister) = unregister_fn else {
            return -EINVAL;
        };

        unsafe {
            let _ = unset(tni, bgid);
            *enabled = 0;
            unregister(tni, bgid);
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_bg_links_body_result(
    source_lgate: CLong,
    source_raddr: *const TofuAddr,
    source_rtni: CULong,
    source_rgate: CLong,
    dest_lgate: CLong,
    dest_raddr: *const TofuAddr,
    dest_rtni: CULong,
    dest_rgate: CLong,
    sigmask_out: *mut CULong,
    locallink_out: *mut CULong,
    remotelink_out: *mut CULong,
) -> CInt {
    if sigmask_out.is_null() || locallink_out.is_null() || remotelink_out.is_null() {
        return -EINVAL;
    }

    let mut sigmask = 0;
    let mut locallink = 0;
    let mut remotelink = 0;

    if source_lgate >= 0 {
        locallink |= tofu_mask_set(source_lgate as CULong, TOF_ICC_REG_BGS_LOCAL_LINK_BGID_RECV);
    } else {
        sigmask |= TOF_ICC_REG_BGS_SIGNAL_MASK_SIG_RECV;
    }

    if source_rgate >= 0 {
        let Some(bgaddr) = (unsafe { pack_remote_bg(source_raddr, source_rtni, source_rgate) })
        else {
            return -EINVAL;
        };
        remotelink |= tofu_mask_set(bgaddr, TOF_ICC_REG_BGS_REMOTE_LINK_BG_ADDRESS_RECV);
    } else {
        sigmask |= TOF_ICC_REG_BGS_SIGNAL_MASK_TLP_RECV;
    }

    if dest_lgate >= 0 {
        locallink |= tofu_mask_set(dest_lgate as CULong, TOF_ICC_REG_BGS_LOCAL_LINK_BGID_SEND);
    } else {
        sigmask |= TOF_ICC_REG_BGS_SIGNAL_MASK_SIG_SEND;
    }

    if dest_rgate >= 0 {
        let Some(bgaddr) = (unsafe { pack_remote_bg(dest_raddr, dest_rtni, dest_rgate) }) else {
            return -EINVAL;
        };
        remotelink |= tofu_mask_set(bgaddr, TOF_ICC_REG_BGS_REMOTE_LINK_BG_ADDRESS_SEND);
    } else {
        sigmask |= TOF_ICC_REG_BGS_SIGNAL_MASK_TLP_SEND;
    }

    unsafe {
        *sigmask_out = sigmask;
        *locallink_out = locallink;
        *remotelink_out = remotelink;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_set_bg_after_copy_body_result(
    ubch: *mut c_void,
    req: *const TofuSetBg,
    kuid: CInt,
    bseq: u32,
    ntni: CInt,
    nbgs: CInt,
    get_bg_fn: Option<TofuUtofuBgGetFn>,
    meta_fn: Option<TofuUtofuBgMetaFn>,
    set_enabled_fn: Option<TofuUtofuBgSetEnabledFn>,
    set_bg_fn: Option<TofuCoreSetBgFn>,
    bgmask_set_fn: Option<TofuBchBgmaskSetFn>,
    register_signal_fn: Option<TofuRegisterSignalBgFn>,
    signal_handler: Option<TofuSignalHandlerFn>,
    error_log_fn: Option<TofuErrorLogFn>,
) -> CInt {
    let _ = kuid;
    if ubch.is_null() || req.is_null() || ntni < 0 || !(0..=64).contains(&nbgs) {
        return -EINVAL;
    }
    let Some(get_bg) = get_bg_fn else {
        return -EINVAL;
    };
    let Some(read_meta) = meta_fn else {
        return -EINVAL;
    };
    let Some(set_enabled) = set_enabled_fn else {
        return -EINVAL;
    };
    let Some(set_bg) = set_bg_fn else {
        return -EINVAL;
    };
    let Some(set_bgmask) = bgmask_set_fn else {
        return -EINVAL;
    };
    let Some(register_signal) = register_signal_fn else {
        return -EINVAL;
    };
    let Some(log_error) = error_log_fn else {
        return -EINVAL;
    };

    let req_ref = unsafe { &*req };
    let ubg = unsafe { get_bg(req_ref.tni, req_ref.gate) };
    if ubg.is_null() {
        unsafe {
            log_error(-EINVAL);
        }
        return -EINVAL;
    }

    if req_ref.tni < 0 || req_ref.tni >= ntni || req_ref.gate < 0 || req_ref.gate >= nbgs {
        unsafe {
            log_error(-EINVAL);
        }
        return -EINVAL;
    }

    let mut subnet = 0;
    let mut gpid = 0;
    let mut enabled = 0;
    let ret = unsafe { read_meta(ubg, &mut subnet, &mut gpid, &mut enabled) };
    if ret < 0 {
        return ret;
    }

    let invalid_source = req_ref.source_lgate >= nbgs
        || (req_ref.source_rgate >= 0
            && (!subnet_includes(
                subnet,
                req_ref.source_raddr.x,
                req_ref.source_raddr.y,
                req_ref.source_raddr.z,
            ) || req_ref.source_rtni < 0
                || req_ref.source_rtni >= ntni
                || req_ref.source_rgate >= nbgs));
    let invalid_dest = req_ref.dest_lgate >= nbgs
        || (req_ref.dest_rgate >= 0
            && (!subnet_includes(
                subnet,
                req_ref.dest_raddr.x,
                req_ref.dest_raddr.y,
                req_ref.dest_raddr.z,
            ) || req_ref.dest_rtni < 0
                || req_ref.dest_rtni >= ntni
                || req_ref.dest_rgate >= nbgs));
    if invalid_source || invalid_dest {
        unsafe {
            log_error(-EINVAL);
        }
        return -EINVAL;
    }

    if enabled != 0 {
        return -EBUSY;
    }

    let ret = unsafe { set_bg(req, subnet, bseq, gpid) };
    if ret < 0 {
        unsafe {
            log_error(ret);
        }
        return ret;
    }

    unsafe {
        set_enabled(ubg, 1);
    }
    let ret = unsafe { set_bgmask(ubch, req_ref.tni, req_ref.gate) };
    if ret < 0 {
        return ret;
    }
    unsafe {
        register_signal(req_ref.tni, req_ref.gate, signal_handler);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_unset_bg_after_copy_body_result(
    req: *const TofuSetBg,
    get_bg_fn: Option<TofuUtofuBgGetFn>,
    unset_bg_fn: Option<TofuUnsetBgPtrFn>,
) -> CInt {
    if req.is_null() {
        return -EINVAL;
    }
    let Some(get_bg) = get_bg_fn else {
        return -EINVAL;
    };
    let Some(unset_bg) = unset_bg_fn else {
        return -EINVAL;
    };

    let req_ref = unsafe { &*req };
    let bg = unsafe { get_bg(req_ref.tni, req_ref.gate) };
    if bg.is_null() {
        return -EINVAL;
    }

    unsafe { unset_bg(bg) }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_set_bg_body_result(
    setbg: *const TofuSetBg,
    subnet: CULong,
    bseq: u32,
    gpid: u32,
    timeout: CULong,
    get_bg_fn: Option<TofuCoreBgGetFn>,
    publish_fn: Option<TofuCoreBgPublishFn>,
    lock_fn: Option<TofuCoreBgLockFn>,
    unlock_fn: Option<TofuCoreBgUnlockFn>,
    reset_irqmask_fn: Option<TofuCoreBgFn>,
    reset_irqmask_imc_fn: Option<TofuCoreBgFn>,
    bgs_reg_fn: Option<TofuCoreBgRegFn>,
    writeq_fn: Option<TofuWriteqFn>,
    wmb_fn: Option<TofuBarrierFn>,
    readq_spin_fn: Option<TofuReadqSpinFn>,
) -> CInt {
    if setbg.is_null() {
        return -EINVAL;
    }
    let Some(get_bg) = get_bg_fn else {
        return -EINVAL;
    };
    let Some(publish) = publish_fn else {
        return -EINVAL;
    };
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };
    let Some(reset_irqmask) = reset_irqmask_fn else {
        return -EINVAL;
    };
    let Some(reset_irqmask_imc) = reset_irqmask_imc_fn else {
        return -EINVAL;
    };
    let Some(bgs_reg_of) = bgs_reg_fn else {
        return -EINVAL;
    };
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };
    let Some(readq_spin) = readq_spin_fn else {
        return -EINVAL;
    };

    let req = unsafe { &*setbg };
    let bg = unsafe { get_bg(req.tni, req.gate) };
    if bg.is_null() {
        return -EINVAL;
    }

    let flags = unsafe { lock(bg) };
    unsafe {
        publish(bg, subnet, gpid);
        reset_irqmask(bg);
        reset_irqmask_imc(bg);
    }

    let mut sigmask = 0;
    let mut locallink = 0;
    let mut remotelink = 0;
    let ret = unsafe {
        tofu_core_bg_links_body_result(
            req.source_lgate as CLong,
            &req.source_raddr,
            req.source_rtni as CULong,
            req.source_rgate as CLong,
            req.dest_lgate as CLong,
            &req.dest_raddr,
            req.dest_rtni as CULong,
            req.dest_rgate as CLong,
            &mut sigmask,
            &mut locallink,
            &mut remotelink,
        )
    };
    if ret < 0 {
        unsafe {
            unlock(bg, flags);
        }
        return ret;
    }

    let bgs_reg = unsafe { bgs_reg_of(bg) };
    unsafe {
        writeq(sigmask, bgs_reg, TOF_ICC_REG_BGS_SIGNAL_MASK);
        writeq(locallink, bgs_reg, TOF_ICC_REG_BGS_LOCAL_LINK);
        writeq(remotelink, bgs_reg, TOF_ICC_REG_BGS_REMOTE_LINK);
        writeq(subnet, bgs_reg, TOF_ICC_REG_BGS_SUBNET_SIZE);
        writeq(
            ((gpid as CULong) << 24) | (bseq as CULong),
            bgs_reg,
            TOF_ICC_REG_BGS_GPID_BSEQ,
        );
        wmb();
        writeq(1, bgs_reg, TOF_ICC_REG_BGS_ENABLE);
    }

    let ret = unsafe {
        if readq_spin(
            bgs_reg,
            TOF_ICC_REG_BGS_STATE,
            TOF_ICC_REG_BGS_STATE_ENABLE,
            TOF_ICC_REG_BGS_STATE_ENABLE,
            timeout,
        ) == 0
        {
            -ETIMEDOUT
        } else {
            0
        }
    };
    unsafe {
        unlock(bg, flags);
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_register_signal_bg_body_result(
    slot: *mut Option<TofuSignalHandlerFn>,
    lock_arg: *mut c_void,
    handler: Option<TofuSignalHandlerFn>,
    lock_fn: Option<TofuLockFn>,
    unlock_fn: Option<TofuUnlockFn>,
) -> CInt {
    if slot.is_null() {
        return -EINVAL;
    }
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    let flags = unsafe { lock(lock_arg) };
    unsafe {
        *slot = handler;
        unlock(lock_arg, flags);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_enable_bch_body_result(
    bch_reg: *const c_void,
    bgs_reg: *mut c_void,
    dma_ipa: CULong,
    dma_align: CULong,
    timeout: CULong,
    writeq_fn: Option<TofuWriteqFn>,
    readq_spin_fn: Option<TofuReadqSpinFn>,
) -> CInt {
    if bch_reg.is_null() || dma_align == 0 || (dma_ipa & dma_align.wrapping_sub(1)) != 0 {
        return -EINVAL;
    }
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };
    let Some(readq_spin) = readq_spin_fn else {
        return -EINVAL;
    };

    unsafe {
        writeq(dma_ipa, bgs_reg, TOF_ICC_REG_BGS_BCH_NOTICE_IPA);
        writeq(0, bgs_reg, TOF_ICC_REG_BGS_BCH_MASK);
        if readq_spin(
            bgs_reg,
            TOF_ICC_REG_BGS_BCH_MASK_STATUS,
            TOF_ICC_REG_BGS_BCH_MASK_STATUS_RUN,
            0,
            timeout,
        ) == 0
        {
            return -ETIMEDOUT;
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_bch_disable_locked_body_result(
    bch_reg: *const c_void,
    bgs_reg: *mut c_void,
    writeq_fn: Option<TofuWriteqFn>,
) -> CInt {
    if bch_reg.is_null() {
        return -EINVAL;
    }
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };

    unsafe {
        writeq(
            TOF_ICC_REG_BGS_BCH_MASK_MASK,
            bgs_reg,
            TOF_ICC_REG_BGS_BCH_MASK,
        );
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_bg_disable_body_result(
    bgs_reg: *mut c_void,
    writeq_fn: Option<TofuWriteqFn>,
) -> CInt {
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };

    unsafe {
        writeq(0, bgs_reg, TOF_ICC_REG_BGS_ENABLE);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_disable_bch_body_result(
    enabled: *mut u8,
    tni: CInt,
    bgid: CInt,
    bgmask: *const CULong,
    ntni: CInt,
    nbgs: CInt,
    disable_fn: Option<TofuCoreDisableBchFn>,
    unset_fn: Option<TofuUnsetBgByIdFn>,
    error_log_fn: Option<TofuErrorLogFn>,
    mb_fn: Option<TofuBarrierFn>,
) -> CInt {
    if enabled.is_null() || bgmask.is_null() || ntni < 0 || !(0..=64).contains(&nbgs) {
        return -EINVAL;
    }
    if unsafe { *enabled } == 0 {
        return -EPERM;
    }
    let Some(disable_bch) = disable_fn else {
        return -EINVAL;
    };
    let Some(unset_bg) = unset_fn else {
        return -EINVAL;
    };
    let Some(smp_mb) = mb_fn else {
        return -EINVAL;
    };

    let ret = unsafe { disable_bch(tni, bgid) };
    if ret < 0 {
        if let Some(log_error) = error_log_fn {
            unsafe {
                log_error(ret);
            }
        }
        return ret;
    }

    for mask_tni in 0..ntni {
        let mask = unsafe { *bgmask.add(mask_tni as usize) };
        for mask_bgid in 0..nbgs {
            if ((mask >> (mask_bgid as u32)) & 1) != 0 {
                let ret = unsafe { unset_bg(mask_tni, mask_bgid) };
                if ret < 0 {
                    return ret;
                }
            }
        }
    }

    unsafe {
        *enabled = 0;
        smp_mb();
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_bch_device_disable_body_result(
    dev: *mut c_void,
    device_offset: CULong,
    log_fn: Option<TofuBchDeviceLogFn>,
    disable_fn: Option<TofuDisableBchPtrFn>,
) -> CInt {
    if dev.is_null() {
        return -EINVAL;
    }
    let Some(log) = log_fn else {
        return -EINVAL;
    };
    let Some(disable_bch) = disable_fn else {
        return -EINVAL;
    };

    let bg = (dev as *mut u8).wrapping_sub(device_offset as usize) as *mut c_void;
    unsafe {
        log(bg);
        disable_bch(bg)
    }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_init_globals_body_result(
    get_globals_fn: Option<TofuGetGlobalsFn>,
    publish_fn: Option<TofuGlobalsPtrFn>,
    unavailable_log_fn: Option<TofuVoidFn>,
    globals_log_fn: Option<TofuGlobalsPtrFn>,
    clear_caches_fn: Option<TofuVoidFn>,
    init_lock_fn: Option<TofuInitLockFn>,
    tni_count: CInt,
    cq_count: CInt,
    done_log_fn: Option<TofuVoidFn>,
) -> CInt {
    if tni_count < 0 || cq_count < 0 {
        return -EINVAL;
    }
    let Some(get_globals) = get_globals_fn else {
        return -EINVAL;
    };
    let Some(log_unavailable) = unavailable_log_fn else {
        return -EINVAL;
    };
    let Some(publish) = publish_fn else {
        return -EINVAL;
    };
    let Some(log_globals) = globals_log_fn else {
        return -EINVAL;
    };
    let Some(clear_caches) = clear_caches_fn else {
        return -EINVAL;
    };
    let Some(init_lock) = init_lock_fn else {
        return -EINVAL;
    };
    let Some(log_done) = done_log_fn else {
        return -EINVAL;
    };

    let globals = unsafe { get_globals() };
    if globals.is_null() {
        unsafe {
            log_unavailable();
        }
        return 0;
    }

    unsafe {
        publish(globals as *const c_void);
        log_globals(globals as *const c_void);
        clear_caches();
    }
    for tni in 0..tni_count {
        for cq in 0..cq_count {
            unsafe {
                init_lock(tni, cq);
            }
        }
    }
    unsafe {
        log_done();
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_finalize_body_result(
    get_globals_fn: Option<TofuGetGlobalsFn>,
    current_enabled_fn: Option<TofuCurrentEnabledFn>,
    scan_stags_fn: Option<TofuVoidFn>,
    scan_done_log_fn: Option<TofuVoidFn>,
    clear_range_fn: Option<TofuClearRangeFn>,
) -> CInt {
    let Some(get_globals) = get_globals_fn else {
        return -EINVAL;
    };
    let Some(current_enabled) = current_enabled_fn else {
        return -EINVAL;
    };
    let Some(scan_stags) = scan_stags_fn else {
        return -EINVAL;
    };
    let Some(log_scan_done) = scan_done_log_fn else {
        return -EINVAL;
    };
    let Some(clear_range) = clear_range_fn else {
        return -EINVAL;
    };

    let globals = unsafe { get_globals() };
    if globals.is_null() {
        return 0;
    }

    if unsafe { current_enabled() } != 0 {
        unsafe {
            scan_stags();
            log_scan_done();
        }
    }

    let globals_ref = unsafe { &*(globals as *const TofuGlobals) };
    unsafe {
        clear_range(
            globals_ref.linux_vmalloc_start as *mut c_void,
            globals_ref.linux_vmalloc_end as *mut c_void,
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_cacheflush_timeout_body_result(
    get_cq_fn: Option<TofuCoreBgGetFn>,
    cqs_reg_fn: Option<TofuCqRegFn>,
    writeq_fn: Option<TofuWriteqFn>,
    wmb_fn: Option<TofuVoidFn>,
    log_fn: Option<TofuCacheflushLogFn>,
    ntni: CInt,
    ncqs: CInt,
    kcqid: CInt,
    steering_disabled: CInt,
    steering_enable_offset: CLong,
) -> CInt {
    if ntni < 0 || ncqs < 0 {
        return -EINVAL;
    }
    let Some(get_cq) = get_cq_fn else {
        return -EINVAL;
    };
    let Some(cqs_reg) = cqs_reg_fn else {
        return -EINVAL;
    };
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };
    let Some(log) = log_fn else {
        return -EINVAL;
    };

    for tni in 0..ntni {
        for cqid in 0..ncqs {
            if cqid == kcqid {
                continue;
            }

            let cq = unsafe { get_cq(tni, cqid) };
            if cq.is_null() {
                return -EINVAL;
            }
            let cqs = unsafe { cqs_reg(cq) };
            if cqs.is_null() {
                return -EINVAL;
            }

            if steering_disabled != 0 {
                unsafe {
                    writeq(0, cqs, steering_enable_offset);
                    wmb();
                }
            }
            unsafe {
                log(1, tni, cqid);
            }
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_core_cq_cacheflush_body_result(
    cq: *mut c_void,
    tni: CInt,
    cqid: CInt,
    cqs_reg_fn: Option<TofuCqRegFn>,
    writeq_fn: Option<TofuWriteqFn>,
    readq_spin_fn: Option<TofuReadqSpinFn>,
    timeout_fn: Option<TofuCacheflushTimeoutFn>,
    log_fn: Option<TofuCacheflushLogFn>,
    panic_fn: Option<TofuPanicFn>,
    panic_disabled: CInt,
    first_timeout: CULong,
    second_timeout: CULong,
    cache_flush_offset: CLong,
    status_offset: CLong,
    busy_mask: CULong,
) -> CInt {
    if cq.is_null() {
        return -EINVAL;
    }
    let Some(cqs_reg) = cqs_reg_fn else {
        return -EINVAL;
    };
    let Some(writeq) = writeq_fn else {
        return -EINVAL;
    };
    let Some(readq_spin) = readq_spin_fn else {
        return -EINVAL;
    };
    let Some(timeout) = timeout_fn else {
        return -EINVAL;
    };
    let Some(log) = log_fn else {
        return -EINVAL;
    };
    let Some(panic_cb) = panic_fn else {
        return -EINVAL;
    };

    let cqs = unsafe { cqs_reg(cq) };
    if cqs.is_null() {
        return -EINVAL;
    }

    unsafe {
        writeq(1, cqs, cache_flush_offset);
    }
    if unsafe { readq_spin(cqs, status_offset, busy_mask, 0, first_timeout) } == 0 {
        unsafe {
            log(0, tni, cqid);
        }
        if panic_disabled != 0 {
            let ret = unsafe { timeout(cq) };
            if ret < 0 {
                return ret;
            }
            if unsafe { readq_spin(cqs, status_offset, busy_mask, 0, second_timeout) } == 0 {
                unsafe {
                    log(0, tni, cqid);
                    panic_cb();
                }
            }
        } else {
            unsafe {
                panic_cb();
            }
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_alloc_new_steering_body_result(
    ucq: *mut c_void,
    stag: CInt,
    start: CULong,
    end: CULong,
    pgszbits: u8,
    plus_mbva: CULong,
    readonly: CInt,
    blank_mbva: CULong,
    page_size: CULong,
    mbpt_entry_size: CULong,
    profile_enabled: CInt,
    profile_alloc_event: CInt,
    profile_update_event: CInt,
    profile_total_event: CInt,
    calc_mbptstart_fn: Option<TofuCalcMbptstartFn>,
    alloc_mbpt_fn: Option<TofuAllocMbptFn>,
    set_mbpt_meta_fn: Option<TofuSetMbptMetaFn>,
    mbpt_iova_fn: Option<TofuMbptIovaFn>,
    update_mbpt_entries_fn: Option<TofuUpdateMbptEntriesFn>,
    free_mbpt_fn: Option<TofuFreeMbptFn>,
    enable_mb_fn: Option<TofuEnableMbFn>,
    enable_steering_fn: Option<TofuEnableSteeringFn>,
    trans_enable_fn: Option<TofuTransEnableFn>,
    raw_rc_fn: Option<TofuErrorLogFn>,
    timestamp_fn: Option<TofuTimestampFn>,
    profile_event_fn: Option<TofuProfileEventFn>,
) -> CInt {
    if ucq.is_null()
        || stag < 0
        || end < start
        || page_size == 0
        || mbpt_entry_size == 0
        || pgszbits as u32 >= CULong::BITS
    {
        return -EINVAL;
    }

    let Some(calc_mbptstart) = calc_mbptstart_fn else {
        return -EINVAL;
    };
    let Some(alloc_mbpt) = alloc_mbpt_fn else {
        return -EINVAL;
    };
    let Some(set_mbpt_meta) = set_mbpt_meta_fn else {
        return -EINVAL;
    };
    let Some(mbpt_iova) = mbpt_iova_fn else {
        return -EINVAL;
    };
    let Some(update_mbpt_entries) = update_mbpt_entries_fn else {
        return -EINVAL;
    };
    let Some(free_mbpt) = free_mbpt_fn else {
        return -EINVAL;
    };
    let Some(enable_mb) = enable_mb_fn else {
        return -EINVAL;
    };
    let Some(enable_steering) = enable_steering_fn else {
        return -EINVAL;
    };
    let Some(trans_enable) = trans_enable_fn else {
        return -EINVAL;
    };
    let Some(raw_rc) = raw_rc_fn else {
        return -EINVAL;
    };

    let (timestamp, profile_event) = if profile_enabled != 0 {
        let Some(timestamp) = timestamp_fn else {
            return -EINVAL;
        };
        let Some(profile_event) = profile_event_fn else {
            return -EINVAL;
        };
        (Some(timestamp), Some(profile_event))
    } else {
        (None, None)
    };

    let pgsz = 1_u64 << pgszbits;
    let npages = (end - start) >> pgszbits;
    let entries_per_page = page_size / mbpt_entry_size;
    if entries_per_page == 0 {
        return -EINVAL;
    }
    let mbpt_npages = ((npages + entries_per_page - 1) / entries_per_page) * entries_per_page;

    let mut ts = 0;
    let mut ts_rolling = 0;
    if let Some(timestamp) = timestamp {
        ts = unsafe { timestamp() };
        ts_rolling = ts;
    }

    let mut mbptstart = 0;
    let mut ret = unsafe {
        calc_mbptstart(
            start as CLong,
            end as CLong,
            mbpt_npages,
            pgszbits,
            &mut mbptstart,
        )
    };
    if ret < 0 {
        unsafe {
            raw_rc(ret);
        }
        return ret;
    }

    let mut mbpt = core::ptr::null_mut();
    ret = unsafe { alloc_mbpt(ucq, mbpt_npages, &mut mbpt, stag) };
    if ret < 0 {
        unsafe {
            raw_rc(ret);
        }
        return ret;
    }
    if mbpt.is_null() {
        unsafe {
            raw_rc(-EINVAL);
        }
        return -EINVAL;
    }

    unsafe {
        set_mbpt_meta(mbpt, mbptstart, pgsz);
    }
    if let (Some(timestamp), Some(profile_event)) = (timestamp, profile_event) {
        let now = unsafe { timestamp() };
        unsafe {
            profile_event(profile_alloc_event, now.wrapping_sub(ts_rolling));
        }
        ts_rolling = unsafe { timestamp() };
    }

    let ix = ((start.wrapping_sub(mbptstart)) >> pgszbits) as u32;
    ret = unsafe { update_mbpt_entries(ucq, mbpt, start, end, ix, pgsz, readonly) };
    if ret < 0 {
        unsafe {
            raw_rc(ret);
            free_mbpt(ucq, mbpt);
        }
        return ret;
    }

    let mbva = if plus_mbva == blank_mbva {
        0
    } else {
        start.wrapping_sub(mbptstart).wrapping_add(plus_mbva)
    };
    let iova = unsafe { mbpt_iova(mbpt) };
    unsafe {
        enable_mb(ucq, stag, iova, pgszbits, mbpt_npages);
        enable_steering(
            ucq,
            stag,
            mbva,
            end.wrapping_sub(mbptstart).wrapping_sub(mbva),
            readonly,
        );
        trans_enable(
            ucq,
            stag,
            start,
            end - start,
            mbptstart,
            mbpt_npages * mbpt_entry_size,
            pgszbits,
            mbpt,
        );
    }

    if let (Some(timestamp), Some(profile_event)) = (timestamp, profile_event) {
        let now = unsafe { timestamp() };
        unsafe {
            profile_event(profile_update_event, now.wrapping_sub(ts_rolling));
            profile_event(profile_total_event, timestamp().wrapping_sub(ts));
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_ioctl_alloc_stag_body_result(
    dev: *mut c_void,
    arg: CULong,
    special_stag: CInt,
    alloc_lpg_flag: u32,
    blank_mbva: CULong,
    page_size: CULong,
    page_shift: u8,
    special_align: CULong,
    dev_to_cq_fn: Option<TofuDeviceToCqFn>,
    current_vm_fn: Option<TofuCurrentVmFn>,
    copyin_fn: Option<TofuCopyAllocStagInFn>,
    copyout_fn: Option<TofuCopyAllocStagOutFn>,
    ucq_enabled_fn: Option<TofuUcqEnabledFn>,
    steering_enabled_fn: Option<TofuUcqStagEnabledFn>,
    vm_read_lock_fn: Option<TofuVmLockFn>,
    vm_read_unlock_fn: Option<TofuVmLockFn>,
    lookup_range_fn: Option<TofuRangeLookupFn>,
    stack_faultable_fn: Option<TofuStackFaultableFn>,
    page_fault_fn: Option<TofuPageFaultFn>,
    pagesize_locked_fn: Option<TofuPagesizeLockedFn>,
    cq_lock_fn: Option<TofuCqLockFn>,
    cq_unlock_fn: Option<TofuCqLockFn>,
    trans_search_fn: Option<TofuTransSearchFn>,
    reserve_stag_fn: Option<TofuReserveStagFn>,
    release_stag_fn: Option<TofuFreeStagFn>,
    alloc_new_steering_fn: Option<TofuAllocNewSteeringFn>,
    get_mbpt_start_fn: Option<TofuGetMbptStartFn>,
    range_insert_fn: Option<TofuRangeInsertFn>,
) -> CInt {
    if dev.is_null()
        || special_stag <= 0
        || page_size == 0
        || special_align == 0
        || page_shift as u32 >= CULong::BITS
    {
        return -EINVAL;
    }

    let Some(dev_to_cq) = dev_to_cq_fn else {
        return -EINVAL;
    };
    let Some(current_vm) = current_vm_fn else {
        return -EINVAL;
    };
    let Some(copyin) = copyin_fn else {
        return -EINVAL;
    };
    let Some(copyout) = copyout_fn else {
        return -EINVAL;
    };
    let Some(ucq_enabled) = ucq_enabled_fn else {
        return -EINVAL;
    };
    let Some(steering_enabled) = steering_enabled_fn else {
        return -EINVAL;
    };
    let Some(vm_read_lock) = vm_read_lock_fn else {
        return -EINVAL;
    };
    let Some(vm_read_unlock) = vm_read_unlock_fn else {
        return -EINVAL;
    };
    let Some(lookup_range) = lookup_range_fn else {
        return -EINVAL;
    };
    let Some(stack_faultable) = stack_faultable_fn else {
        return -EINVAL;
    };
    let Some(page_fault) = page_fault_fn else {
        return -EINVAL;
    };
    let Some(pagesize_locked) = pagesize_locked_fn else {
        return -EINVAL;
    };
    let Some(cq_lock) = cq_lock_fn else {
        return -EINVAL;
    };
    let Some(cq_unlock) = cq_unlock_fn else {
        return -EINVAL;
    };
    let Some(trans_search) = trans_search_fn else {
        return -EINVAL;
    };
    let Some(reserve_stag) = reserve_stag_fn else {
        return -EINVAL;
    };
    let Some(release_stag) = release_stag_fn else {
        return -EINVAL;
    };
    let Some(alloc_new_steering) = alloc_new_steering_fn else {
        return -EINVAL;
    };
    let Some(get_mbpt_start) = get_mbpt_start_fn else {
        return -EINVAL;
    };
    let Some(range_insert) = range_insert_fn else {
        return -EINVAL;
    };

    let ucq = unsafe { dev_to_cq(dev) };
    if ucq.is_null() {
        return -EINVAL;
    }
    if unsafe { ucq_enabled(ucq) } == 0 {
        return -EPERM;
    }

    let mut req = TofuAllocStag {
        flags: 0,
        stag: 0,
        offset: 0,
        va: core::ptr::null_mut(),
        len: 0,
    };
    let mut ret = unsafe { copyin(&mut req, arg) };
    if ret < 0 {
        return ret;
    }

    if req.stag < -1 || req.stag >= special_stag || req.va.is_null() || req.len == 0 {
        return -EINVAL;
    }
    if req.stag >= 0 && unsafe { steering_enabled(ucq, req.stag) } != 0 {
        return -EBUSY;
    }

    let vm = unsafe { current_vm() };
    if vm.is_null() {
        return -EINVAL;
    }

    let readonly = (req.flags & 1) as CInt;
    let va = req.va as CULong;
    let mut final_ret;

    loop {
        unsafe {
            vm_read_lock(vm);
        }

        let mut start = tofu_align_down(va, page_size);
        let mut end = tofu_align_up(va.wrapping_add(req.len), page_size);
        let range = unsafe { lookup_range(vm, start, end) };
        if range.is_null() {
            if unsafe { stack_faultable(vm, start, end) } != 0 {
                unsafe {
                    vm_read_unlock(vm);
                }
                if unsafe { page_fault(vm, start) } < 0 {
                    final_ret = -EINVAL;
                    break;
                }
                continue;
            }

            unsafe {
                vm_read_unlock(vm);
            }
            final_ret = -EINVAL;
            break;
        }

        let mut pgszbits = page_shift;
        if (req.flags & alloc_lpg_flag) != 0 {
            ret = unsafe { pagesize_locked(va, req.len, &mut pgszbits, readonly) };
            if ret < 0 {
                unsafe {
                    vm_read_unlock(vm);
                }
                return ret;
            }
        }

        if pgszbits as u32 >= CULong::BITS {
            unsafe {
                vm_read_unlock(vm);
            }
            return -EINVAL;
        }
        let pgsz = 1_u64 << pgszbits;
        start = tofu_align_down(va, pgsz);
        end = tofu_align_up(va.wrapping_add(req.len), pgsz);

        unsafe {
            cq_lock(ucq);
        }

        if req.stag < 0 {
            let mut stag = unsafe { trans_search(ucq, start, end, pgszbits, readonly) };
            if stag < 0 {
                stag = unsafe { reserve_stag(ucq, readonly) };
                if stag < 0 {
                    unsafe {
                        cq_unlock(ucq);
                        vm_read_unlock(vm);
                    }
                    return -ENOSPC;
                }

                ret = unsafe {
                    alloc_new_steering(ucq, stag, start, end, pgszbits, blank_mbva, readonly)
                };
                if ret < 0 {
                    unsafe {
                        release_stag(ucq, stag);
                    }
                }
            } else {
                ret = 0;
            }

            req.stag = stag;
            req.offset = va.wrapping_sub(unsafe { get_mbpt_start(ucq, stag) });
        } else {
            if unsafe { steering_enabled(ucq, req.stag) } != 0 {
                unsafe {
                    cq_unlock(ucq);
                    vm_read_unlock(vm);
                }
                return -EBUSY;
            }

            let plus_mbva = tofu_align_down(va, special_align).wrapping_sub(start);
            ret = unsafe {
                alloc_new_steering(ucq, req.stag, start, end, pgszbits, plus_mbva, readonly)
            };
            req.offset = va & special_align.wrapping_sub(1);
        }

        unsafe {
            cq_unlock(ucq);
        }

        if ret == 0 {
            unsafe {
                range_insert(vm, range, start, end, ucq, req.stag);
            }
        }

        unsafe {
            vm_read_unlock(vm);
        }
        final_ret = ret;
        break;
    }

    if final_ret == 0 {
        let out_ret = unsafe { copyout(arg, &req) };
        if out_ret < 0 {
            final_ret = out_ret;
        }
    }

    final_ret
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_release_cq_body_result(
    ucq: *mut c_void,
    enabled: CInt,
    tni: CInt,
    cqid: CInt,
    num_stag: CInt,
    disabled_log_fn: Option<TofuReleaseCqDisabledLogFn>,
    drain_ranges_fn: Option<TofuReleaseCqDrainFn>,
    free_stag_fn: Option<TofuFreeStagFn>,
    done_log_fn: Option<TofuReleaseCqDoneLogFn>,
) -> CInt {
    if ucq.is_null() || num_stag < 0 {
        return -EINVAL;
    }
    let Some(disabled_log) = disabled_log_fn else {
        return -EINVAL;
    };
    let Some(drain_ranges) = drain_ranges_fn else {
        return -EINVAL;
    };
    let Some(free_stag) = free_stag_fn else {
        return -EINVAL;
    };
    let Some(done_log) = done_log_fn else {
        return -EINVAL;
    };

    let do_free = if enabled != 0 {
        1
    } else {
        unsafe {
            disabled_log(tni, cqid);
        }
        0
    };

    unsafe {
        drain_ranges(ucq, do_free);
    }

    if do_free != 0 {
        for stag in 0..num_stag {
            unsafe {
                free_stag(ucq, stag);
            }
        }
    }

    unsafe {
        done_log(ucq);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_release_fd_body_result(
    enable_tofu: u8,
    fd_data: *mut c_void,
    fd_path: *const c_void,
    pid: CInt,
    fd: CInt,
    path_kind_fn: Option<TofuPathKindFn>,
    release_cq_fn: Option<TofuReleaseDeviceFn>,
    release_bch_fn: Option<TofuReleaseDeviceFn>,
    log_fn: Option<TofuReleaseLogFn>,
) -> CInt {
    if enable_tofu == 0 || fd_data.is_null() || fd_path.is_null() {
        return 0;
    }
    let Some(path_kind) = path_kind_fn else {
        return -EINVAL;
    };
    let Some(release_cq) = release_cq_fn else {
        return -EINVAL;
    };
    let Some(release_bch) = release_bch_fn else {
        return -EINVAL;
    };

    match unsafe { path_kind(fd_path) } {
        TOFU_RELEASE_KIND_CQ => unsafe {
            if let Some(log) = log_fn {
                log(pid, fd, TOFU_RELEASE_KIND_CQ);
            }
            release_cq(fd_data);
        },
        TOFU_RELEASE_KIND_BCH => unsafe {
            if let Some(log) = log_fn {
                log(pid, fd, TOFU_RELEASE_KIND_BCH);
            }
            release_bch(fd_data);
        },
        _ => {}
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_release_fds_body_result(
    enable_tofu: u8,
    proc: *mut c_void,
    max_fd: CInt,
    release_fd_fn: Option<TofuReleaseFdFn>,
) -> CInt {
    if enable_tofu == 0 {
        return 0;
    }
    if proc.is_null() || max_fd < 0 {
        return -EINVAL;
    }
    let Some(release_fd) = release_fd_fn else {
        return -EINVAL;
    };

    for fd in 0..max_fd {
        unsafe {
            release_fd(proc, fd);
        }
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_unlocked_ioctl_body_result(
    fd: CInt,
    cmd: u32,
    arg: CULong,
    max_fd: CInt,
    fd_data: *mut c_void,
    alloc_cmd: u32,
    free_cmd: u32,
    enable_bch_cmd: u32,
    disable_bch_cmd: u32,
    profile_enabled: u8,
    profile_alloc_event: CInt,
    profile_free_event: CInt,
    alloc_fn: Option<TofuIoctlFn>,
    free_fn: Option<TofuIoctlFn>,
    enable_bch_fn: Option<TofuIoctlFn>,
    disable_bch_fn: Option<TofuIoctlFn>,
    timestamp_fn: Option<TofuTimestampFn>,
    profile_event_fn: Option<TofuProfileEventFn>,
    unknown_log_fn: Option<TofuUnknownIoctlLogFn>,
) -> CLong {
    if fd < 0 || max_fd < 0 || fd >= max_fd || fd_data.is_null() {
        return -(ENOTSUPP as CLong);
    }

    let mut start = 0;
    if profile_enabled != 0 {
        let Some(timestamp) = timestamp_fn else {
            return -(EINVAL as CLong);
        };
        start = unsafe { timestamp() };
    }

    let (ret, profile_event) = if cmd == alloc_cmd {
        let Some(call) = alloc_fn else {
            return -(EINVAL as CLong);
        };
        (unsafe { call(fd_data, arg) }, Some(profile_alloc_event))
    } else if cmd == free_cmd {
        let Some(call) = free_fn else {
            return -(EINVAL as CLong);
        };
        (unsafe { call(fd_data, arg) }, Some(profile_free_event))
    } else if cmd == enable_bch_cmd {
        let Some(call) = enable_bch_fn else {
            return -(EINVAL as CLong);
        };
        (unsafe { call(fd_data, arg) }, None)
    } else if cmd == disable_bch_cmd {
        let Some(call) = disable_bch_fn else {
            return -(EINVAL as CLong);
        };
        (unsafe { call(fd_data, arg) }, None)
    } else {
        if let Some(log_unknown) = unknown_log_fn {
            unsafe {
                log_unknown(fd);
            }
        }
        return -(ENOTSUPP as CLong);
    };

    if profile_enabled != 0 {
        if let Some(event) = profile_event {
            let Some(timestamp) = timestamp_fn else {
                return -(EINVAL as CLong);
            };
            let Some(profile_event_add) = profile_event_fn else {
                return -(EINVAL as CLong);
            };
            let elapsed = unsafe { timestamp() }.wrapping_sub(start);
            unsafe {
                profile_event_add(event, elapsed);
            }
        }
    }

    ret as CLong
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_free_stags_after_req_copy_body_result(
    ucq: *mut c_void,
    req: *mut TofuFreeStags,
    arg: *mut c_void,
    staging: *mut CInt,
    max_stags: CInt,
    copyin_stags_fn: Option<TofuCopyStagsFn>,
    copyout_stags_fn: Option<TofuCopyStagsFn>,
    copyout_req_fn: Option<TofuCopyReqOutFn>,
    free_one_fn: Option<TofuFreeOneStagFn>,
    remove_range_fn: Option<TofuRemoveStagRangeFn>,
    raw_rc_fn: Option<TofuErrorLogFn>,
    log_out_fn: Option<TofuFreeStagsLogOutFn>,
) -> CInt {
    if ucq.is_null() || req.is_null() || arg.is_null() || staging.is_null() || max_stags < 0 {
        return -EINVAL;
    }
    let Some(copyin_stags) = copyin_stags_fn else {
        return -EINVAL;
    };
    let Some(copyout_stags) = copyout_stags_fn else {
        return -EINVAL;
    };
    let Some(copyout_req) = copyout_req_fn else {
        return -EINVAL;
    };
    let Some(free_one) = free_one_fn else {
        return -EINVAL;
    };
    let Some(remove_range) = remove_range_fn else {
        return -EINVAL;
    };

    let req_ref = unsafe { &mut *req };
    if (req_ref.num as CInt) > max_stags || req_ref.stags.is_null() {
        return -EINVAL;
    }

    if unsafe { copyin_stags(staging, req_ref.stags as *const CInt, req_ref.num as CULong) } != 0 {
        if let Some(raw_rc) = raw_rc_fn {
            unsafe {
                raw_rc(-EFAULT);
            }
        }
        return -EFAULT;
    }

    let mut no_free_count: CInt = 0;
    let mut idx: CInt = 0;
    while idx < req_ref.num as CInt {
        let stag = unsafe { *staging.add(idx as usize) };
        let ret = unsafe { free_one(ucq, stag) };
        unsafe {
            remove_range(stag);
        }

        if ret == 0 {
            unsafe {
                *staging.add(idx as usize) = -1;
            }
        } else if ret == -ENOENT {
            no_free_count += 1;
            idx += 1;
            continue;
        } else {
            req_ref.num = idx.wrapping_sub(no_free_count) as u16;
            if unsafe { copyout_stags(req_ref.stags, staging, req_ref.num as CULong) } != 0 {
                if let Some(raw_rc) = raw_rc_fn {
                    unsafe {
                        raw_rc(-EFAULT);
                    }
                }
                return -EFAULT;
            }
            if unsafe { copyout_req(arg, req as *const TofuFreeStags) } != 0 {
                return -EFAULT;
            }
            return ret;
        }

        idx += 1;
    }

    req_ref.num = idx.wrapping_sub(no_free_count) as u16;
    if unsafe { copyout_stags(req_ref.stags, staging, req_ref.num as CULong) } != 0 {
        if let Some(raw_rc) = raw_rc_fn {
            unsafe {
                raw_rc(-EFAULT);
            }
        }
        return -EFAULT;
    }
    if unsafe { copyout_req(arg, req as *const TofuFreeStags) } != 0 {
        return -EFAULT;
    }

    if let Some(log_out) = log_out_fn {
        unsafe {
            log_out(ucq, req_ref.num, req_ref.stags, no_free_count);
        }
    }

    if no_free_count > 0 {
        -ENOENT
    } else {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_free_stag_body_result(
    ucq: *mut c_void,
    stag: CInt,
    num_stag: CInt,
    steering_enabled_fn: Option<TofuFreeStagQueryFn>,
    kref_is_mckernel_fn: Option<TofuFreeStagQueryFn>,
    non_mckernel_log_fn: Option<TofuFreeStagFn>,
    disable_entries_fn: Option<TofuFreeStagFn>,
    trans_disable_fn: Option<TofuFreeStagFn>,
    wmb_fn: Option<TofuBarrierFn>,
    profile_state: *mut c_void,
    profile_fn: Option<TofuFreeStagProfileFn>,
    cacheflush_fn: Option<TofuFreeStagQueryFn>,
    kref_put_fn: Option<TofuFreeStagFn>,
    clear_mbpt_fn: Option<TofuFreeStagFn>,
    dealloc_log_fn: Option<TofuFreeStagFn>,
) -> CInt {
    if ucq.is_null() || num_stag < 0 || stag < 0 || stag >= num_stag {
        return -EINVAL;
    }
    let Some(steering_enabled) = steering_enabled_fn else {
        return -EINVAL;
    };
    let Some(kref_is_mckernel) = kref_is_mckernel_fn else {
        return -EINVAL;
    };
    let Some(disable_entries) = disable_entries_fn else {
        return -EINVAL;
    };
    let Some(trans_disable) = trans_disable_fn else {
        return -EINVAL;
    };
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };
    let Some(cacheflush) = cacheflush_fn else {
        return -EINVAL;
    };
    let Some(kref_put) = kref_put_fn else {
        return -EINVAL;
    };
    let Some(clear_mbpt) = clear_mbpt_fn else {
        return -EINVAL;
    };

    let enabled = unsafe { steering_enabled(ucq, stag) };
    if enabled < 0 {
        return -EINVAL;
    }
    if enabled == 0 {
        return -ENOENT;
    }

    if unsafe { kref_is_mckernel(ucq, stag) } == 0 {
        if let Some(log) = non_mckernel_log_fn {
            unsafe {
                log(ucq, stag);
            }
        }
        return -EINVAL;
    }

    unsafe {
        disable_entries(ucq, stag);
        trans_disable(ucq, stag);
        wmb();
        if let Some(profile) = profile_fn {
            profile(profile_state, TOFU_FREE_STAG_PROFILE_PRE);
        }
    }

    let _ = unsafe { cacheflush(ucq, stag) };

    unsafe {
        if let Some(profile) = profile_fn {
            profile(profile_state, TOFU_FREE_STAG_PROFILE_CQFLUSH);
        }
        kref_put(ucq, stag);
        clear_mbpt(ucq, stag);
        if let Some(log) = dealloc_log_fn {
            log(ucq, stag);
        }
        if let Some(profile) = profile_fn {
            profile(profile_state, TOFU_FREE_STAG_PROFILE_DEALLOC);
            profile(profile_state, TOFU_FREE_STAG_PROFILE_TOTAL);
        }
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_enable_bch_precheck_body_result(
    bgid: CInt,
    enabled: *const u8,
    max_bchs: CInt,
) -> CInt {
    if enabled.is_null() || max_bchs < 0 {
        return -EINVAL;
    }
    if bgid >= max_bchs {
        return -ENOTTY;
    }
    if unsafe { *enabled } != 0 {
        return -EBUSY;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_enable_bch_request_validate_result(
    req: *const TofuEnableBch,
    dma_align: CULong,
    bseq_size: CULong,
) -> CInt {
    if req.is_null() || dma_align == 0 || bseq_size == 0 {
        return -EINVAL;
    }

    let req_ref = unsafe { &*req };
    if req_ref.num < 0
        || req_ref.bgs.is_null()
        || req_ref.addr.is_null()
        || ((req_ref.addr as CULong) & dma_align.wrapping_sub(1)) != 0
        || (req_ref.bseq as u32 as CULong) >= bseq_size
    {
        return -EINVAL;
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_enable_bch_commit_body_result(
    ubg: *mut c_void,
    enabled: *mut u8,
    tni: CInt,
    bgid: CInt,
    req: *const TofuEnableBch,
    ipa: CULong,
    bgmask: *mut CULong,
    ntni: CInt,
    iova: *mut CULong,
    kuid: CInt,
    enable_fn: Option<TofuEnableBchFn>,
    set_bg_fn: Option<TofuSetBgFn>,
    disable_fn: Option<TofuCoreDisableBchFn>,
    unset_bg_fn: Option<TofuUnsetBgUserFn>,
    error_log_fn: Option<TofuErrorLogFn>,
) -> CInt {
    if ubg.is_null()
        || enabled.is_null()
        || req.is_null()
        || bgmask.is_null()
        || iova.is_null()
        || ntni < 0
    {
        return -EINVAL;
    }
    let Some(enable_bch) = enable_fn else {
        return -EINVAL;
    };
    let Some(set_bg) = set_bg_fn else {
        return -EINVAL;
    };
    let Some(disable_bch) = disable_fn else {
        return -EINVAL;
    };
    let Some(unset_bg) = unset_bg_fn else {
        return -EINVAL;
    };
    let Some(log_error) = error_log_fn else {
        return -EINVAL;
    };

    let req_ref = unsafe { &*req };
    if req_ref.num < 0 || req_ref.bgs.is_null() {
        return -EINVAL;
    }

    for idx in 0..ntni {
        unsafe {
            *bgmask.add(idx as usize) = 0;
        }
    }

    let ret = unsafe { enable_bch(tni, bgid, ipa) };
    if ret < 0 {
        unsafe {
            log_error(ret);
            let _ = disable_bch(tni, bgid);
        }
        return ret;
    }

    let mut idx = 0;
    while idx < req_ref.num {
        let bg = unsafe { req_ref.bgs.add(idx as usize) };
        let ret = unsafe { set_bg(ubg, bg, kuid, req_ref.bseq as u32) };
        if ret < 0 {
            unsafe {
                log_error(ret);
                let _ = disable_bch(tni, bgid);
            }
            while idx > 0 {
                idx -= 1;
                let bg = unsafe { req_ref.bgs.add(idx as usize) };
                unsafe {
                    let _ = unset_bg(bg);
                }
            }
            return ret;
        }
        idx += 1;
    }

    unsafe {
        *enabled = 1;
        *iova = ipa;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_mru_insert_body_result(
    mru: *mut TofuUtofuTransList,
    mruhead: *mut CInt,
    stag: CInt,
    pgszbits: u8,
    mbpt: *mut c_void,
    empty_stag: CInt,
) -> CInt {
    if mru.is_null() || mruhead.is_null() || stag < 0 {
        return -EINVAL;
    }

    let entry = unsafe { mru.add(stag as usize) };
    unsafe {
        (*entry).pgszbits = pgszbits;
        (*entry).mbpt = mbpt;
    }

    if unsafe { *mruhead } == empty_stag {
        unsafe {
            (*entry).prev = stag as i16;
            (*entry).next = stag as i16;
        }
    } else {
        let next = unsafe { *mruhead };
        let prev = unsafe { (*mru.add(next as usize)).prev as CInt };
        unsafe {
            (*entry).prev = prev as i16;
            (*entry).next = next as i16;
            (*mru.add(prev as usize)).next = stag as i16;
            (*mru.add(next as usize)).prev = stag as i16;
        }
    }

    unsafe {
        *mruhead = stag;
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_disable_body_result(
    table_slot: *mut c_void,
    mru: *mut TofuUtofuTransList,
    mruhead: *mut CInt,
    stag: CInt,
    empty_stag: CInt,
    atomic_set_fn: Option<TofuAtomicSetFn>,
) -> CInt {
    if table_slot.is_null() || mru.is_null() || mruhead.is_null() || stag < 0 {
        return -EINVAL;
    }
    let Some(atomic_set) = atomic_set_fn else {
        return -EINVAL;
    };

    unsafe {
        atomic_set(table_slot, 0);
        tofu_utofu_trans_mru_delete_body_result(mru, mruhead, stag, empty_stag)
    }
}

#[no_mangle]
pub extern "C" fn tofu_utofu_trans_entry_pack_result(
    start: CULong,
    len: CULong,
    pgszbits: u8,
    page_shift: CInt,
    ps_code_64kb: CInt,
    ps_code_2mb: CInt,
) -> CULong {
    tofu_trans_entry_value(start, len, pgszbits, page_shift, ps_code_64kb, ps_code_2mb)
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_table_steering_start_result(
    table_slot: *const TofuTransTable,
    page_shift: CInt,
) -> CULong {
    if table_slot.is_null() {
        return 0;
    }
    unsafe { trans_entry_start((*table_slot).steering, page_shift) }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_table_steering_len_result(
    table_slot: *const TofuTransTable,
    page_shift: CInt,
) -> CULong {
    if table_slot.is_null() {
        return 0;
    }
    unsafe { trans_entry_len((*table_slot).steering, page_shift) }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_table_mbpt_start_result(
    table_slot: *const TofuTransTable,
    page_shift: CInt,
) -> CULong {
    if table_slot.is_null() {
        return 0;
    }
    unsafe { trans_entry_start((*table_slot).mbpt, page_shift) }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_table_mbpt_len_result(
    table_slot: *const TofuTransTable,
    page_shift: CInt,
) -> CULong {
    if table_slot.is_null() {
        return 0;
    }
    unsafe { trans_entry_len((*table_slot).mbpt, page_shift) }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_steering_enable_body_result(
    entry: *mut c_void,
    stag: CInt,
    mbva: CULong,
    length: CULong,
    readonly: CInt,
    wmb_fn: Option<TofuWmbFn>,
) -> CInt {
    if entry.is_null() || stag < 0 {
        return -EINVAL;
    }
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };

    let mut word = unsafe { read_u64(entry) } & !TOF_ICC_STEERING_MUT_MASK;
    if readonly != 0 {
        word |= 1_u64 << TOF_ICC_STEERING_READONLY_SHIFT;
    }
    word |= (mbva >> 8 & TOF_ICC_STEERING_MBVA_MASK) << TOF_ICC_STEERING_MBVA_SHIFT;
    word |= ((stag as CULong) & TOF_ICC_STEERING_MBID_MASK) << TOF_ICC_STEERING_MBID_SHIFT;

    unsafe {
        core::ptr::write_volatile((entry as *mut CULong).add(1), length);
        write_u64(entry, word);
        wmb();
        write_u64(entry, word | (1_u64 << TOF_ICC_STEERING_ENABLE_SHIFT));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_steering_entry_is_enabled_result(entry: *const c_void) -> CInt {
    if entry.is_null() {
        return 0;
    }
    let word = unsafe { read_u64(entry) };
    ((word >> TOF_ICC_STEERING_ENABLE_SHIFT) & 1) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_steering_disable_entry_body_result(entry: *mut c_void) -> CInt {
    if entry.is_null() {
        return -EINVAL;
    }
    let word = unsafe { read_u64(entry) };
    unsafe {
        write_u64(entry, word & !(1_u64 << TOF_ICC_STEERING_ENABLE_SHIFT));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_reserve_stag_body_result(
    steering: *const c_void,
    special_stag: CInt,
    num_stag: CInt,
    readonly: CInt,
    entry_size: CULong,
) -> CInt {
    if steering.is_null() || special_stag < 0 || num_stag < special_stag || entry_size == 0 {
        return -EINVAL;
    }

    let mut stag = special_stag + ((readonly != 0) as CInt);
    while stag < num_stag {
        let entry = unsafe {
            (steering as *const u8).add((stag as usize).wrapping_mul(entry_size as usize))
                as *const c_void
        };
        if unsafe { tofu_icc_steering_entry_is_enabled_result(entry) } == 0 {
            return stag;
        }
        stag += 2;
    }

    -1
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_mb_enable_body_result(
    entry: *mut c_void,
    iova: CULong,
    pgszbits: u8,
    npages: CULong,
    wmb_fn: Option<TofuWmbFn>,
) -> CInt {
    if entry.is_null() {
        return -EINVAL;
    }
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };

    let mut word = unsafe { read_u64(entry) } & !TOF_ICC_MB_MUT_MASK;
    word = set_field(
        word,
        TOF_ICC_MB_PS_MASK,
        0,
        TOF_ICC_MB_PS_ENCODE(pgszbits as CInt) as CULong,
    );
    word = set_field(word, TOF_ICC_MB_IPA_MASK, TOF_ICC_MB_IPA_SHIFT, iova >> 8);

    unsafe {
        core::ptr::write_volatile((entry as *mut CULong).add(1), npages);
        write_u64(entry, word);
        wmb();
        write_u64(entry, word | (1_u64 << TOF_ICC_MB_ENABLE_SHIFT));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_mb_disable_entry_body_result(entry: *mut c_void) -> CInt {
    if entry.is_null() {
        return -EINVAL;
    }
    let word = unsafe { read_u64(entry) };
    unsafe {
        write_u64(entry, word & !(1_u64 << TOF_ICC_MB_ENABLE_SHIFT));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_mbpt_disable_entry_body_result(entry: *mut c_void) -> CULong {
    if entry.is_null() {
        return 0;
    }
    let word = unsafe { read_u64(entry) };
    if ((word >> TOF_ICC_MBPT_ENABLE_SHIFT) & 1) == 0 {
        return 0;
    }

    let ipa = ((word >> TOF_ICC_MBPT_IPA_SHIFT) & TOF_ICC_MBPT_IPA_MASK) << 12;
    unsafe {
        write_u64(entry, word & !TOF_ICC_MBPT_MUT_MASK);
    }
    ipa
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_mbpt_enable_entry_body_result(
    entry: *mut c_void,
    iova: CULong,
    wmb_fn: Option<TofuWmbFn>,
) -> CInt {
    if entry.is_null() {
        return -EINVAL;
    }
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };

    let mut word = unsafe { read_u64(entry) } & !TOF_ICC_MBPT_MUT_MASK;
    word = set_field(
        word,
        TOF_ICC_MBPT_IPA_MASK,
        TOF_ICC_MBPT_IPA_SHIFT,
        iova >> 12,
    );
    unsafe {
        write_u64(entry, word);
        wmb();
        write_u64(entry, word | (1_u64 << TOF_ICC_MBPT_ENABLE_SHIFT));
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn tofu_icc_mbpt_entry_is_enabled_result(entry: *const c_void) -> CInt {
    if entry.is_null() {
        return 0;
    }
    let word = unsafe { read_u64(entry) };
    ((word >> TOF_ICC_MBPT_ENABLE_SHIFT) & 1) as CInt
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_search_body_result(
    table: *const TofuTransTable,
    mru: *const TofuUtofuTransList,
    mruhead: CInt,
    start: CULong,
    end: CULong,
    pgszbits: u8,
    readonly: CInt,
    exact_address_match: CInt,
    empty_stag: CInt,
    special_stag: CInt,
    max_stag: CInt,
    page_shift: CInt,
) -> CInt {
    if table.is_null()
        || mru.is_null()
        || max_stag <= 0
        || special_stag < 0
        || mruhead < empty_stag
        || page_shift < 0
        || page_shift >= 64
    {
        return -EINVAL;
    }
    if mruhead == empty_stag {
        return -ENOENT;
    }
    if mruhead < 0 || mruhead >= max_stag {
        return -EINVAL;
    }

    let want_readonly = (readonly != 0) as CInt;
    let exact = (exact_address_match & 1) != 0;
    let mut stag = mruhead;
    let mut visited = 0;

    loop {
        if stag < 0 || stag >= max_stag {
            return -EINVAL;
        }

        let table_slot = unsafe { table.add(stag as usize) };
        let stag_start = unsafe { trans_entry_start((*table_slot).steering, page_shift) };
        let stag_end =
            stag_start.wrapping_add(unsafe { trans_entry_len((*table_slot).steering, page_shift) });
        let entry = unsafe { mru.add(stag as usize) };
        let entry_pgszbits = unsafe { (*entry).pgszbits };

        if stag >= special_stag
            && (stag & 1) == want_readonly
            && entry_pgszbits == pgszbits
            && ((exact && stag_start == start && stag_end == end)
                || (!exact && stag_start <= start && end <= stag_end))
        {
            return stag;
        }

        stag = unsafe { (*entry).next as CInt };
        visited += 1;
        if stag == mruhead {
            break;
        }
        if visited >= max_stag {
            return -EINVAL;
        }
    }

    -ENOENT
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_update_body_result(
    table_slot: *mut TofuTransTable,
    mru: *mut TofuUtofuTransList,
    mruhead: *mut CInt,
    lock_arg: *mut c_void,
    stag: CInt,
    start: CULong,
    len: CULong,
    pgszbits: u8,
    mbpt: *mut c_void,
    empty_stag: CInt,
    page_shift: CInt,
    ps_code_64kb: CInt,
    ps_code_2mb: CInt,
    atomic_set_fn: Option<TofuAtomicSetFn>,
    lock_fn: Option<TofuLockFn>,
    unlock_fn: Option<TofuUnlockFn>,
) -> CInt {
    if table_slot.is_null() || mru.is_null() || mruhead.is_null() || lock_arg.is_null() || stag < 0
    {
        return -EINVAL;
    }
    let Some(atomic_set) = atomic_set_fn else {
        return -EINVAL;
    };
    let Some(lock) = lock_fn else {
        return -EINVAL;
    };
    let Some(unlock) = unlock_fn else {
        return -EINVAL;
    };

    let steering =
        tofu_trans_entry_value(start, len, pgszbits, page_shift, ps_code_64kb, ps_code_2mb);
    unsafe {
        atomic_set(table_slot as *mut c_void, steering);
        let flags = lock(lock_arg);
        let mut ret = tofu_utofu_trans_mru_delete_body_result(mru, mruhead, stag, empty_stag);
        if ret == 0 {
            ret = tofu_utofu_trans_mru_insert_body_result(
                mru, mruhead, stag, pgszbits, mbpt, empty_stag,
            );
        }
        unlock(lock_arg, flags);
        ret
    }
}

#[no_mangle]
pub unsafe extern "C" fn tofu_utofu_trans_enable_body_result(
    table_slot: *mut TofuTransTable,
    mru: *mut TofuUtofuTransList,
    mruhead: *mut CInt,
    lock_arg: *mut c_void,
    stag: CInt,
    start: CULong,
    len: CULong,
    mbptstart: CULong,
    mbptlen: CULong,
    pgszbits: u8,
    mbpt: *mut c_void,
    empty_stag: CInt,
    page_shift: CInt,
    ps_code_64kb: CInt,
    ps_code_2mb: CInt,
    atomic_set_fn: Option<TofuAtomicSetFn>,
    wmb_fn: Option<TofuWmbFn>,
    lock_fn: Option<TofuLockFn>,
    unlock_fn: Option<TofuUnlockFn>,
) -> CInt {
    if table_slot.is_null() || mru.is_null() || mruhead.is_null() || lock_arg.is_null() || stag < 0
    {
        return -EINVAL;
    }
    let Some(wmb) = wmb_fn else {
        return -EINVAL;
    };

    let mbpt_entry = tofu_trans_entry_value(
        mbptstart,
        mbptlen,
        pgszbits,
        page_shift,
        ps_code_64kb,
        ps_code_2mb,
    );
    unsafe {
        (*table_slot).mbpt = mbpt_entry;
        wmb();
        tofu_utofu_trans_update_body_result(
            table_slot,
            mru,
            mruhead,
            lock_arg,
            stag,
            start,
            len,
            pgszbits,
            mbpt,
            empty_stag,
            page_shift,
            ps_code_64kb,
            ps_code_2mb,
            atomic_set_fn,
            lock_fn,
            unlock_fn,
        )
    }
}
