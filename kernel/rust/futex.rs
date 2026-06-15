use core::ffi::{c_char, c_void};
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{null_mut, read_volatile, write_volatile};

use crate::abi::{
    CInt, CULong, CpuLocalVar, FutexHashBucket, FutexKey, FutexQ, IhkSpinlock, IkcScdPacket,
    IkcScdPacketFutex, PlistHead, PlistNode, Process, ProcessVm, Thread,
};

const EINVAL: CInt = 22;
const EFAULT: CInt = 14;
const ENOSYS: CInt = 38;
const FUTEX_HASHBITS: CInt = 8;
const FUT_OFF_MMSHARED: usize = 2;
const FUTEX_OP_SET_VALUE: CInt = 0;
const FUTEX_OP_ADD_VALUE: CInt = 1;
const FUTEX_OP_OR_VALUE: CInt = 2;
const FUTEX_OP_ANDN_VALUE: CInt = 3;
const FUTEX_OP_XOR_VALUE: CInt = 4;
const FUTEX_OP_OPARG_SHIFT_VALUE: CInt = 8;
const FUTEX_OP_CMP_EQ_VALUE: CInt = 0;
const FUTEX_OP_CMP_NE_VALUE: CInt = 1;
const FUTEX_OP_CMP_LT_VALUE: CInt = 2;
const FUTEX_OP_CMP_LE_VALUE: CInt = 3;
const FUTEX_OP_CMP_GT_VALUE: CInt = 4;
const FUTEX_OP_CMP_GE_VALUE: CInt = 5;
const IHK_GV_IKC: CInt = 1;
const IHK_MC_AP_NOWAIT: CInt = 0x000002;
const PF_WRITE: CInt = 1 << 1;
const PF_USER: CInt = 1 << 2;
const PF_POPULATE: CInt = 1 << 30;
const PS_RUNNING: CInt = 0x1;
const PS_INTERRUPTIBLE: CInt = 0x2;
const PS_UNINTERRUPTIBLE: CInt = 0x4;
const PS_NORMAL: CInt = PS_INTERRUPTIBLE | PS_UNINTERRUPTIBLE;
const SCD_MSG_FUTEX_WAKE: CInt = 0x60;
const JHASH_GOLDEN_RATIO: u32 = 0x9e37_79b9;

const FUTEX_GET_KEY_LOG_VTOP_FAILED: CInt = 1;

const FUTEX_HASH_BUCKET_CHAIN_OFFSET: usize = offset_of!(FutexHashBucket, chain);
const FUTEX_HASH_BUCKET_LOCK_OFFSET: usize = offset_of!(FutexHashBucket, lock);
const FUTEX_KEY_WORD_OFFSET: usize = 0;
const FUTEX_KEY_PTR_OFFSET: usize = size_of::<CULong>();
const FUTEX_KEY_OFFSET_OFFSET: usize = size_of::<CULong>() * 2;
const IKC_PACKET_FUTEX_RESP_OFFSET: usize =
    offset_of!(IkcScdPacket, body) + offset_of!(IkcScdPacketFutex, resp);
const IKC_PACKET_FUTEX_SPIN_SLEEP_OFFSET: usize =
    offset_of!(IkcScdPacket, body) + offset_of!(IkcScdPacketFutex, spin_sleep);

#[repr(C)]
struct FutexRequeueScanContext {
    hb1: *mut FutexHashBucket,
    hb2: *mut FutexHashBucket,
    key2: *mut FutexKey,
}

#[no_mangle]
pub static mut futex_queues: *mut FutexHashBucket = null_mut();

#[no_mangle]
#[allow(non_snake_case)]
pub extern "C" fn FUTEX_OP(op: CInt, oparg: CInt, cmp: CInt, cmparg: CInt) -> CInt {
    let encoded = (((op as u32) & 0x0f) << 28)
        | (((cmp as u32) & 0x0f) << 24)
        | (((oparg as u32) & 0x0fff) << 12)
        | ((cmparg as u32) & 0x0fff);

    encoded as CInt
}

#[no_mangle]
pub unsafe extern "C" fn get_futex_value_locked(dest: *mut u32, from: *mut u32) -> CInt {
    unsafe {
        let value = read_volatile(from);
        write_volatile(dest, value);
    }

    0
}

#[no_mangle]
pub unsafe extern "C" fn futex_atomic_cmpxchg_inatomic(
    uaddr: *mut CInt,
    oldval: CInt,
    newval: CInt,
) -> CInt {
    if unsafe { futex_atomic_access_ok_bridge(uaddr, size_of::<CInt>()) } == 0 {
        return -EFAULT;
    }

    unsafe { futex_atomic_cmpxchg_inatomic_bridge(uaddr, oldval, newval) }
}

#[no_mangle]
pub unsafe extern "C" fn futex_atomic_op_inuser(encoded_op: CInt, uaddr: *mut CInt) -> CInt {
    let op = (encoded_op >> 28) & 7;
    let cmp = (encoded_op >> 24) & 15;
    let mut oparg = (encoded_op & 0x00fff000) >> 12;
    let cmparg = encoded_op & 0x0fff;
    let mut oldval = 0;

    if (encoded_op & (FUTEX_OP_OPARG_SHIFT_VALUE << 28)) != 0 {
        oparg = (1 as CInt).wrapping_shl(oparg as u32);
    }

    if unsafe { futex_atomic_access_ok_bridge(uaddr, size_of::<CInt>()) } == 0 {
        return -EFAULT;
    }

    let primitive_arg = match op {
        FUTEX_OP_SET_VALUE | FUTEX_OP_ADD_VALUE | FUTEX_OP_OR_VALUE | FUTEX_OP_XOR_VALUE => oparg,
        FUTEX_OP_ANDN_VALUE => !oparg,
        _ => return -ENOSYS,
    };

    let ret = unsafe { futex_atomic_op_inuser_bridge(op, uaddr, primitive_arg, &mut oldval) };
    if ret != 0 {
        return ret;
    }

    match cmp {
        FUTEX_OP_CMP_EQ_VALUE => (oldval == cmparg) as CInt,
        FUTEX_OP_CMP_NE_VALUE => (oldval != cmparg) as CInt,
        FUTEX_OP_CMP_LT_VALUE => (oldval < cmparg) as CInt,
        FUTEX_OP_CMP_GE_VALUE => (oldval >= cmparg) as CInt,
        FUTEX_OP_CMP_LE_VALUE => (oldval <= cmparg) as CInt,
        FUTEX_OP_CMP_GT_VALUE => (oldval > cmparg) as CInt,
        _ => -ENOSYS,
    }
}

unsafe extern "C" {
    static mut idle_halt: CInt;
    static mut ikc2linuxs: *mut *mut c_void;

    fn _kmalloc(size: CInt, flags: CInt, file: *mut c_char, line: CInt) -> *mut c_void;
    fn __ihk_mc_spinlock_lock(lock: *mut IhkSpinlock) -> CULong;
    fn __ihk_mc_spinlock_unlock(lock: *mut IhkSpinlock, irqstate: CULong);
    fn __ihk_mc_spinlock_lock_noirq(lock: *mut IhkSpinlock);
    fn __ihk_mc_spinlock_unlock_noirq(lock: *mut IhkSpinlock);
    fn futex_atomic_access_ok_bridge(uaddr: *mut CInt, size: usize) -> CInt;
    fn futex_atomic_cmpxchg_inatomic_bridge(uaddr: *mut CInt, oldval: CInt, newval: CInt) -> CInt;
    fn futex_atomic_op_inuser_bridge(
        op: CInt,
        uaddr: *mut CInt,
        oparg: CInt,
        oldval: *mut CInt,
    ) -> CInt;
    fn get_cpu_local_var(id: CInt) -> *mut CpuLocalVar;
    fn hassigpending(thread: *mut Thread) -> *mut c_void;
    fn ihk_ikc_send(channel: *mut c_void, packet: *mut IkcScdPacket, flags: CInt) -> CInt;
    fn ihk_mc_get_interrupt_id(cpu_id: CInt) -> CInt;
    fn ihk_mc_get_processor_id() -> CInt;
    fn ihk_mc_get_vector(vector_key: CInt) -> CInt;
    fn ihk_mc_pt_virt_to_phys(pt: *mut c_void, virt: *mut c_void, phys: *mut CULong) -> CInt;
    fn kprintf(format: *const c_char, ...) -> CInt;
    fn page_fault_process_vm(vm: *mut ProcessVm, addr: *mut c_void, reason: CULong) -> CInt;
    fn sched_wakeup_thread(thread: *mut c_void, valid_states: CInt) -> CInt;
    fn schedule_timeout(timeout: u64) -> u64;
    fn spin_sleep_or_schedule();
    fn virt_to_phys(ptr: *mut c_void) -> CULong;
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr().cast()
}

unsafe fn current_cpu_local() -> *mut CpuLocalVar {
    unsafe { get_cpu_local_var(ihk_mc_get_processor_id()) }
}

unsafe fn current_thread() -> *mut Thread {
    let local = unsafe { current_cpu_local() };
    if local.is_null() {
        null_mut()
    } else {
        unsafe { (*local).current }
    }
}

#[no_mangle]
pub unsafe extern "C" fn get_futex_queues() -> *mut FutexHashBucket {
    unsafe { futex_queues }
}

unsafe extern "C" fn futex_kmalloc_bridge(size: usize, flag: CInt) -> usize {
    unsafe {
        _kmalloc(
            size as CInt,
            flag,
            cstr(b"kernel/rust/futex.rs\0") as *mut c_char,
            line!() as CInt,
        ) as usize
    }
}

#[inline(always)]
fn jhash_mix(a: &mut u32, b: &mut u32, c: &mut u32) {
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 13;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(8);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 13;
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 12;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(16);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 5;
    *a = a.wrapping_sub(*b);
    *a = a.wrapping_sub(*c);
    *a ^= *c >> 3;
    *b = b.wrapping_sub(*c);
    *b = b.wrapping_sub(*a);
    *b ^= a.wrapping_shl(10);
    *c = c.wrapping_sub(*a);
    *c = c.wrapping_sub(*b);
    *c ^= *b >> 15;
}

#[no_mangle]
pub unsafe extern "C" fn mc_jhash2(k: *const u32, length: u32, initval: u32) -> u32 {
    let mut a = JHASH_GOLDEN_RATIO;
    let mut b = JHASH_GOLDEN_RATIO;
    let mut c = initval;
    let mut len = length;
    let mut p = k;

    while len >= 3 {
        unsafe {
            a = a.wrapping_add(read_volatile(p));
            b = b.wrapping_add(read_volatile(p.add(1)));
            c = c.wrapping_add(read_volatile(p.add(2)));
            p = p.add(3);
        }
        jhash_mix(&mut a, &mut b, &mut c);
        len -= 3;
    }

    c = c.wrapping_add(length.wrapping_mul(4));
    if len >= 2 {
        unsafe {
            b = b.wrapping_add(read_volatile(p.add(1)));
        }
    }
    if len >= 1 {
        unsafe {
            a = a.wrapping_add(read_volatile(p));
        }
    }
    jhash_mix(&mut a, &mut b, &mut c);
    c
}

unsafe extern "C" fn futex_key_hash_bridge(key_addr: usize) -> u32 {
    let offset =
        unsafe { read_volatile(key_addr.wrapping_add(FUTEX_KEY_OFFSET_OFFSET) as *const CInt) };
    unsafe { mc_jhash2(key_addr as *const u32, 4, offset as u32) }
}

unsafe fn hash_futex(key: *mut FutexKey) -> *mut FutexHashBucket {
    unsafe {
        crate::sched_helpers::futex_hash_bucket_result(
            key as usize,
            futex_queues as usize,
            FUTEX_HASHBITS,
            size_of::<FutexHashBucket>(),
            Some(futex_key_hash_bridge),
        ) as *mut FutexHashBucket
    }
}

unsafe extern "C" fn futex_wake_hash_key_bridge(key_addr: usize) -> usize {
    unsafe { hash_futex(key_addr as *mut FutexKey) as usize }
}

unsafe extern "C" fn futex_key_refs_bridge(_key_addr: usize) {}

unsafe extern "C" fn futex_get_key_vtop_bridge(
    mm_addr: usize,
    uaddr: usize,
    phys_out_addr: usize,
) -> CInt {
    let mm = mm_addr as *mut ProcessVm;
    unsafe {
        ihk_mc_pt_virt_to_phys(
            (*(*mm).address_space).page_table,
            uaddr as *mut c_void,
            phys_out_addr as *mut CULong,
        )
    }
}

unsafe extern "C" fn futex_get_key_fault_bridge(mm_addr: usize, uaddr: usize, flags: CInt) -> CInt {
    unsafe {
        page_fault_process_vm(
            mm_addr as *mut ProcessVm,
            uaddr as *mut c_void,
            flags as CULong,
        )
    }
}

unsafe extern "C" fn futex_get_key_log_bridge(event: CInt) {
    if event == FUTEX_GET_KEY_LOG_VTOP_FAILED {
        unsafe {
            kprintf(cstr(
                b"error: get_futex_key() virt to phys translation failed\n\0",
            ));
        }
    }
}

unsafe fn get_futex_key(uaddr: *mut u32, fshared: CInt, key: *mut FutexKey) -> CInt {
    let thread = unsafe { current_thread() };
    if thread.is_null() {
        return -EINVAL;
    }
    let mm = unsafe { (*thread).vm };

    unsafe {
        crate::sched_helpers::futex_get_key_result(
            uaddr as usize,
            fshared,
            key as usize,
            mm as usize,
            FUTEX_KEY_WORD_OFFSET,
            FUTEX_KEY_PTR_OFFSET,
            FUTEX_KEY_OFFSET_OFFSET,
            FUT_OFF_MMSHARED,
            PF_POPULATE | PF_WRITE | PF_USER,
            Some(futex_key_refs_bridge),
            Some(futex_get_key_vtop_bridge),
            Some(futex_get_key_fault_bridge),
            Some(futex_get_key_log_bridge),
        )
    }
}

unsafe extern "C" fn futex_get_key_call_bridge(
    uaddr: usize,
    fshared: CInt,
    key_addr: usize,
) -> CInt {
    unsafe { get_futex_key(uaddr as *mut u32, fshared, key_addr as *mut FutexKey) }
}

unsafe extern "C" fn futex_put_key_call_bridge(_fshared: CInt, _key_addr: usize) {}

unsafe extern "C" fn futex_wake_linux_channel_bridge(linux_cpu: CInt) -> usize {
    unsafe { *ikc2linuxs.add(linux_cpu as usize) as usize }
}

unsafe extern "C" fn futex_wake_send_bridge(channel_addr: usize, packet_addr: usize) -> CInt {
    unsafe {
        ihk_ikc_send(
            channel_addr as *mut c_void,
            packet_addr as *mut IkcScdPacket,
            0,
        )
    }
}

unsafe extern "C" fn futex_wake_thread_bridge(thread_addr: usize, status: CInt) {
    unsafe {
        let _ = sched_wakeup_thread(thread_addr as *mut c_void, status);
    }
}

unsafe extern "C" fn futex_wake_log_bridge(
    _event: CInt,
    _thread_addr: usize,
    _uti_futex_resp: usize,
    _linux_cpu: CInt,
    _channel_addr: usize,
    _rc: CInt,
) {
}

unsafe fn wake_futex(q: *mut FutexQ) {
    let mut packet = MaybeUninit::<IkcScdPacket>::uninit();
    let local = unsafe { current_cpu_local() };
    let fallback_channel = if local.is_null() {
        0
    } else {
        unsafe { (*local).ikc2linux as usize }
    };

    unsafe {
        crate::sched_helpers::futex_wake_orchestrate_result(
            q as usize,
            offset_of!(FutexQ, list),
            offset_of!(PlistNode, plist),
            offset_of!(FutexQ, lock_ptr),
            offset_of!(FutexQ, task),
            offset_of!(FutexQ, uti_futex_resp),
            offset_of!(FutexQ, linux_cpu),
            offset_of!(Thread, spin_sleep),
            packet.as_mut_ptr() as usize,
            offset_of!(IkcScdPacket, msg),
            IKC_PACKET_FUTEX_RESP_OFFSET,
            IKC_PACKET_FUTEX_SPIN_SLEEP_OFFSET,
            SCD_MSG_FUTEX_WAKE,
            fallback_channel,
            PS_NORMAL,
            Some(futex_wake_linux_channel_bridge),
            Some(futex_wake_send_bridge),
            Some(futex_wake_thread_bridge),
            Some(futex_wake_log_bridge),
        );
    }
}

unsafe extern "C" fn futex_wake_scan_bridge(q_addr: usize) {
    unsafe {
        wake_futex(q_addr as *mut FutexQ);
    }
}

unsafe extern "C" fn futex_wake_lock_bridge(lock_addr: usize) -> CULong {
    unsafe { __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock) }
}

unsafe extern "C" fn futex_wake_unlock_bridge(lock_addr: usize, irqstate: CULong) {
    unsafe {
        __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, irqstate);
    }
}

unsafe extern "C" fn futex_wake_atomic_op_bridge(op: CInt, uaddr: usize) -> CInt {
    unsafe { futex_atomic_op_inuser(op, uaddr as *mut CInt) }
}

unsafe extern "C" fn futex_hb_lock_bridge(lock_addr: usize) {
    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock_addr as *mut IhkSpinlock);
    }
}

unsafe extern "C" fn futex_hb_unlock_bridge(lock_addr: usize) {
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock_addr as *mut IhkSpinlock);
    }
}

unsafe fn futex_wake(uaddr: *mut u32, fshared: CInt, nr_wake: CInt, bitset: u32) -> CInt {
    let mut key = FutexKey { opaque: [0; 3] };

    unsafe {
        crate::sched_helpers::futex_wake_body_result(
            uaddr as usize,
            fshared,
            nr_wake,
            bitset,
            &raw mut key as usize,
            FUTEX_HASH_BUCKET_LOCK_OFFSET,
            FUTEX_HASH_BUCKET_CHAIN_OFFSET,
            offset_of!(FutexQ, list),
            offset_of!(FutexQ, key),
            offset_of!(FutexQ, bitset),
            FUTEX_KEY_WORD_OFFSET,
            FUTEX_KEY_PTR_OFFSET,
            FUTEX_KEY_OFFSET_OFFSET,
            Some(futex_get_key_call_bridge),
            Some(futex_wake_hash_key_bridge),
            Some(futex_wake_lock_bridge),
            Some(futex_wake_unlock_bridge),
            Some(futex_put_key_call_bridge),
            Some(futex_wake_scan_bridge),
        )
    }
}

unsafe fn futex_wake_op(
    uaddr1: *mut u32,
    fshared: CInt,
    uaddr2: *mut u32,
    nr_wake: CInt,
    nr_wake2: CInt,
    op: CInt,
) -> CInt {
    let mut key1 = FutexKey { opaque: [0; 3] };
    let mut key2 = FutexKey { opaque: [0; 3] };

    unsafe {
        crate::sched_helpers::futex_wake_op_body_result(
            uaddr1 as usize,
            fshared,
            uaddr2 as usize,
            nr_wake,
            nr_wake2,
            op,
            &raw mut key1 as usize,
            &raw mut key2 as usize,
            FUTEX_HASH_BUCKET_LOCK_OFFSET,
            FUTEX_HASH_BUCKET_CHAIN_OFFSET,
            offset_of!(FutexQ, list),
            offset_of!(FutexQ, key),
            offset_of!(FutexQ, bitset),
            FUTEX_KEY_WORD_OFFSET,
            FUTEX_KEY_PTR_OFFSET,
            FUTEX_KEY_OFFSET_OFFSET,
            Some(futex_get_key_call_bridge),
            Some(futex_wake_hash_key_bridge),
            Some(futex_hb_lock_bridge),
            Some(futex_hb_unlock_bridge),
            Some(futex_wake_atomic_op_bridge),
            Some(futex_put_key_call_bridge),
            Some(futex_wake_scan_bridge),
        )
    }
}

unsafe fn requeue_futex(
    q: *mut FutexQ,
    hb1: *mut FutexHashBucket,
    hb2: *mut FutexHashBucket,
    key2: *mut FutexKey,
) {
    unsafe {
        crate::sched_helpers::futex_requeue_move_result(
            q as usize,
            offset_of!(FutexQ, list),
            offset_of!(FutexQ, lock_ptr),
            &raw mut (*hb1).chain as usize,
            &raw mut (*hb2).chain as usize,
            &raw mut (*hb2).lock as usize,
            0,
        );
        crate::sched_helpers::futex_requeue_key_update_result(
            q as usize,
            offset_of!(FutexQ, key),
            key2 as usize,
            size_of::<FutexKey>(),
            Some(futex_key_refs_bridge),
        );
    }
}

unsafe extern "C" fn futex_requeue_wake_bridge(q_addr: usize, _ctx_addr: usize) {
    unsafe {
        wake_futex(q_addr as *mut FutexQ);
    }
}

unsafe extern "C" fn futex_requeue_move_bridge(q_addr: usize, ctx_addr: usize) {
    let ctx = ctx_addr as *mut FutexRequeueScanContext;
    unsafe {
        requeue_futex(q_addr as *mut FutexQ, (*ctx).hb1, (*ctx).hb2, (*ctx).key2);
    }
}

unsafe extern "C" fn futex_wait_get_value_bridge(value_addr: usize, uaddr: usize) -> CInt {
    unsafe { get_futex_value_locked(value_addr as *mut u32, uaddr as *mut u32) }
}

unsafe extern "C" fn futex_unqueue_drop_key_refs_bridge(_key_addr: usize) {}

unsafe fn futex_requeue(
    uaddr1: *mut u32,
    fshared: CInt,
    uaddr2: *mut u32,
    nr_wake: CInt,
    nr_requeue: CInt,
    cmpval: *mut u32,
    requeue_pi: CInt,
) -> CInt {
    let mut key1 = FutexKey { opaque: [0; 3] };
    let mut key2 = FutexKey { opaque: [0; 3] };
    let mut requeue_ctx = FutexRequeueScanContext {
        hb1: null_mut(),
        hb2: null_mut(),
        key2: null_mut(),
    };

    let _ = requeue_pi;
    unsafe {
        crate::sched_helpers::futex_requeue_body_result(
            uaddr1 as usize,
            fshared,
            uaddr2 as usize,
            nr_wake,
            nr_requeue,
            cmpval as usize,
            &raw mut key1 as usize,
            &raw mut key2 as usize,
            &raw mut requeue_ctx as usize,
            FUTEX_HASH_BUCKET_LOCK_OFFSET,
            FUTEX_HASH_BUCKET_CHAIN_OFFSET,
            offset_of!(FutexQ, list),
            offset_of!(FutexQ, key),
            FUTEX_KEY_WORD_OFFSET,
            FUTEX_KEY_PTR_OFFSET,
            FUTEX_KEY_OFFSET_OFFSET,
            offset_of!(FutexRequeueScanContext, hb1),
            offset_of!(FutexRequeueScanContext, hb2),
            offset_of!(FutexRequeueScanContext, key2),
            Some(futex_get_key_call_bridge),
            Some(futex_wake_hash_key_bridge),
            Some(futex_hb_lock_bridge),
            Some(futex_hb_unlock_bridge),
            Some(futex_wait_get_value_bridge),
            Some(futex_put_key_call_bridge),
            Some(futex_unqueue_drop_key_refs_bridge),
            Some(futex_requeue_wake_bridge),
            Some(futex_requeue_move_bridge),
        )
    }
}

unsafe fn queue_lock(q: *mut FutexQ) -> *mut FutexHashBucket {
    let hb = unsafe { hash_futex(&raw mut (*q).key) };
    unsafe {
        crate::sched_helpers::futex_queue_lock_ptr_store_result(
            q as usize,
            offset_of!(FutexQ, lock_ptr),
            &raw mut (*hb).lock as usize,
        );
        __ihk_mc_spinlock_lock_noirq(&raw mut (*hb).lock);
    }
    hb
}

unsafe fn queue_unlock(_q: *mut FutexQ, hb: *mut FutexHashBucket) {
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(&raw mut (*hb).lock);
    }
}

unsafe extern "C" fn futex_wait_queue_lock_bridge(q_addr: usize) -> usize {
    unsafe { queue_lock(q_addr as *mut FutexQ) as usize }
}

unsafe extern "C" fn futex_virt_to_phys_bridge(addr: usize) -> CULong {
    unsafe { virt_to_phys(addr as *mut c_void) }
}

unsafe extern "C" fn futex_interrupt_id_bridge(cpu_id: CInt) -> CInt {
    unsafe { ihk_mc_get_interrupt_id(cpu_id) }
}

unsafe extern "C" fn futex_vector_bridge(vector_key: CInt) -> CInt {
    unsafe { ihk_mc_get_vector(vector_key) }
}

unsafe extern "C" fn futex_wait_queue_unlock_bridge(q_addr: usize, hb_addr: usize) {
    unsafe {
        queue_unlock(q_addr as *mut FutexQ, hb_addr as *mut FutexHashBucket);
    }
}

unsafe extern "C" fn futex_unqueue_lock_bridge(lock_addr: usize) {
    unsafe {
        __ihk_mc_spinlock_lock_noirq(lock_addr as *mut IhkSpinlock);
    }
}

unsafe extern "C" fn futex_unqueue_unlock_bridge(lock_addr: usize) {
    unsafe {
        __ihk_mc_spinlock_unlock_noirq(lock_addr as *mut IhkSpinlock);
    }
}

unsafe extern "C" fn futex_wait_spin_lock_bridge(lock_addr: usize) -> CULong {
    unsafe { __ihk_mc_spinlock_lock(lock_addr as *mut IhkSpinlock) }
}

unsafe extern "C" fn futex_wait_spin_unlock_bridge(lock_addr: usize, irqstate: CULong) {
    unsafe {
        __ihk_mc_spinlock_unlock(lock_addr as *mut IhkSpinlock, irqstate);
    }
}

unsafe fn queue_me(q: *mut FutexQ, hb: *mut FutexHashBucket) {
    let local = unsafe { current_cpu_local() };
    let thread = if local.is_null() {
        null_mut()
    } else {
        unsafe { (*local).current }
    };
    if local.is_null() || thread.is_null() {
        return;
    }

    unsafe {
        crate::sched_helpers::futex_queue_me_result(
            q as usize,
            offset_of!(FutexQ, list),
            offset_of!(FutexQ, task),
            offset_of!(FutexQ, th_spin_sleep_pa),
            offset_of!(FutexQ, th_status_pa),
            offset_of!(FutexQ, th_spin_sleep_lock_pa),
            offset_of!(FutexQ, proc_status_pa),
            offset_of!(FutexQ, proc_update_lock_pa),
            offset_of!(FutexQ, runq_lock_pa),
            offset_of!(FutexQ, clv_flags_pa),
            offset_of!(FutexQ, intr_id),
            offset_of!(FutexQ, intr_vector),
            &raw mut (*hb).chain as usize,
            &raw mut (*hb).lock as usize,
            10,
            0,
            thread as usize,
            offset_of!(Thread, spin_sleep),
            offset_of!(Thread, status),
            offset_of!(Thread, spin_sleep_lock),
            offset_of!(Thread, proc),
            offset_of!(Thread, cpu_id),
            offset_of!(Process, status),
            offset_of!(Process, update_lock),
            &raw mut (*local).runq_lock as usize,
            &raw mut (*local).flags as usize,
            IHK_GV_IKC,
            Some(futex_virt_to_phys_bridge),
            Some(futex_interrupt_id_bridge),
            Some(futex_vector_bridge),
            Some(futex_hb_unlock_bridge),
        );
    }
}

unsafe extern "C" fn futex_wait_queue_me_bridge(q_addr: usize, hb_addr: usize) {
    unsafe {
        queue_me(q_addr as *mut FutexQ, hb_addr as *mut FutexHashBucket);
    }
}

unsafe extern "C" fn futex_wait_schedule_timeout_bridge(timeout: u64) -> i64 {
    unsafe { schedule_timeout(timeout) as i64 }
}

unsafe extern "C" fn futex_wait_schedule_direct_bridge() {
    unsafe {
        spin_sleep_or_schedule();
    }
}

unsafe extern "C" fn futex_wait_queue_log_bridge(_event: CInt, _thread_addr: usize, _tid: CInt) {}

unsafe fn unqueue_me(q: *mut FutexQ) -> CInt {
    unsafe {
        crate::sched_helpers::futex_unqueue_me_result(
            q as usize,
            offset_of!(FutexQ, lock_ptr),
            offset_of!(FutexQ, list),
            offset_of!(PlistNode, plist),
            offset_of!(FutexQ, key),
            Some(futex_unqueue_lock_bridge),
            Some(futex_unqueue_unlock_bridge),
            Some(futex_unqueue_drop_key_refs_bridge),
        )
    }
}

unsafe fn futex_wait_queue_me(hb: *mut FutexHashBucket, q: *mut FutexQ, timeout: u64) -> i64 {
    let thread = unsafe { current_thread() };
    if thread.is_null() {
        return -(EINVAL as i64);
    }

    unsafe {
        crate::sched_helpers::futex_wait_queue_me_result(
            hb as usize,
            q as usize,
            offset_of!(FutexQ, list),
            offset_of!(PlistNode, plist),
            offset_of!(PlistHead, node_list),
            thread as usize,
            offset_of!(Thread, status),
            offset_of!(Thread, spin_sleep),
            offset_of!(Thread, spin_sleep_lock),
            offset_of!(Thread, tid),
            idle_halt,
            timeout,
            PS_INTERRUPTIBLE,
            PS_RUNNING,
            Some(futex_wait_spin_lock_bridge),
            Some(futex_wait_spin_unlock_bridge),
            Some(futex_wait_queue_me_bridge),
            Some(futex_wait_schedule_timeout_bridge),
            Some(futex_wait_schedule_direct_bridge),
            Some(futex_wait_queue_log_bridge),
        )
    }
}

unsafe fn futex_wait_setup(
    uaddr: *mut u32,
    val: u32,
    fshared: CInt,
    q: *mut FutexQ,
    hb: *mut *mut FutexHashBucket,
) -> CInt {
    let mut hb_addr = 0usize;
    let ret = unsafe {
        crate::sched_helpers::futex_wait_setup_result(
            uaddr as usize,
            val,
            fshared,
            q as usize,
            &raw mut hb_addr,
            offset_of!(FutexQ, key),
            size_of::<FutexKey>(),
            Some(futex_get_key_call_bridge),
            Some(futex_wait_queue_lock_bridge),
            Some(futex_wait_get_value_bridge),
            Some(futex_wait_queue_unlock_bridge),
            Some(futex_put_key_call_bridge),
        )
    };
    if ret == 0 {
        unsafe {
            *hb = hb_addr as *mut FutexHashBucket;
        }
    }
    ret
}

unsafe extern "C" fn futex_wait_setup_body_bridge(
    uaddr: usize,
    val: u32,
    fshared: CInt,
    q_addr: usize,
    hb_out_addr: usize,
) -> CInt {
    let mut hb: *mut FutexHashBucket = null_mut();
    let ret = unsafe {
        futex_wait_setup(
            uaddr as *mut u32,
            val,
            fshared,
            q_addr as *mut FutexQ,
            &raw mut hb,
        )
    };
    if ret == 0 && hb_out_addr != 0 {
        unsafe {
            write_volatile(hb_out_addr as *mut usize, hb as usize);
        }
    }
    ret
}

unsafe extern "C" fn futex_wait_queue_body_bridge(
    hb_addr: usize,
    q_addr: usize,
    timeout: u64,
) -> i64 {
    unsafe {
        futex_wait_queue_me(
            hb_addr as *mut FutexHashBucket,
            q_addr as *mut FutexQ,
            timeout,
        )
    }
}

unsafe extern "C" fn futex_wait_unqueue_body_bridge(q_addr: usize) -> CInt {
    unsafe { unqueue_me(q_addr as *mut FutexQ) }
}

unsafe extern "C" fn futex_wait_has_signal_bridge(thread_addr: usize) -> CInt {
    unsafe { (!hassigpending(thread_addr as *mut Thread).is_null()) as CInt }
}

unsafe extern "C" fn futex_wait_log_bridge(
    _event: CInt,
    _thread_addr: usize,
    _tid: CInt,
    _ret: CInt,
) {
}

unsafe extern "C" fn futex_wait_timestamp_bridge() -> usize {
    let low: u32;
    let high: u32;

    unsafe {
        core::arch::asm!(
            "rdtsc",
            out("eax") low,
            out("edx") high,
            options(nomem, nostack, preserves_flags)
        );
    }
    (((high as u64) << 32) | low as u64) as usize
}

unsafe extern "C" fn futex_wait_body_entry_bridge(
    uaddr: usize,
    fshared: CInt,
    val: u32,
    timeout: u64,
    bitset: u32,
    q_addr: usize,
    thread_addr: usize,
    uti_futex_resp: usize,
) -> CInt {
    unsafe {
        crate::sched_helpers::futex_wait_body_result(
            uaddr,
            fshared,
            val,
            timeout,
            bitset,
            q_addr,
            thread_addr,
            uti_futex_resp,
            offset_of!(FutexQ, bitset),
            offset_of!(FutexQ, requeue_pi_key),
            offset_of!(FutexQ, uti_futex_resp),
            offset_of!(FutexQ, key),
            offset_of!(Thread, tid),
            Some(futex_wait_setup_body_bridge),
            Some(futex_wait_queue_body_bridge),
            Some(futex_wait_unqueue_body_bridge),
            Some(futex_wait_has_signal_bridge),
            Some(futex_put_key_call_bridge),
            Some(futex_wait_log_bridge),
        )
    }
}

unsafe fn futex_wait(
    uaddr: *mut u32,
    fshared: CInt,
    val: u32,
    timeout: u64,
    bitset: u32,
    clockrt: CInt,
) -> CInt {
    let mut lq = MaybeUninit::<FutexQ>::uninit();
    let q = lq.as_mut_ptr();
    let thread = unsafe { current_thread() };
    let local = unsafe { current_cpu_local() };
    let uti_futex_resp = if local.is_null() {
        0
    } else {
        unsafe { (*local).uti_futex_resp as usize }
    };

    #[cfg(enable_profile)]
    let profile_enabled = 1;
    #[cfg(not(enable_profile))]
    let profile_enabled = 0;

    let _ = clockrt;
    if thread.is_null() {
        return -EINVAL;
    }

    unsafe {
        crate::sched_helpers::futex_wait_entry_result(
            uaddr as usize,
            fshared,
            val,
            timeout,
            bitset,
            q as usize,
            thread as usize,
            uti_futex_resp,
            profile_enabled,
            offset_of!(Thread, profile),
            offset_of!(Thread, profile_start_ts),
            offset_of!(Thread, profile_elapsed_ts),
            Some(futex_wait_timestamp_bridge),
            Some(futex_wait_body_entry_bridge),
        )
    }
}

unsafe extern "C" fn futex_dispatch_wait_bridge(
    uaddr: usize,
    fshared: CInt,
    val: u32,
    timeout: u64,
    val3: u32,
    clockrt: CInt,
) -> CInt {
    unsafe { futex_wait(uaddr as *mut u32, fshared, val, timeout, val3, clockrt) }
}

unsafe extern "C" fn futex_dispatch_wake_bridge(
    uaddr: usize,
    fshared: CInt,
    val: u32,
    val3: u32,
) -> CInt {
    unsafe { futex_wake(uaddr as *mut u32, fshared, val as CInt, val3) }
}

unsafe extern "C" fn futex_dispatch_requeue_bridge(
    uaddr: usize,
    fshared: CInt,
    uaddr2: usize,
    val: u32,
    val2: u32,
    cmpval_present: CInt,
    cmpval: u32,
    requeue_pi: CInt,
) -> CInt {
    let mut local_cmpval = cmpval;
    let cmpval_ptr = if cmpval_present != 0 {
        &raw mut local_cmpval
    } else {
        null_mut()
    };

    unsafe {
        futex_requeue(
            uaddr as *mut u32,
            fshared,
            uaddr2 as *mut u32,
            val as CInt,
            val2 as CInt,
            cmpval_ptr,
            requeue_pi,
        )
    }
}

unsafe extern "C" fn futex_dispatch_wake_op_bridge(
    uaddr: usize,
    fshared: CInt,
    uaddr2: usize,
    val: u32,
    val2: u32,
    val3: u32,
) -> CInt {
    unsafe {
        futex_wake_op(
            uaddr as *mut u32,
            fshared,
            uaddr2 as *mut u32,
            val as CInt,
            val2 as CInt,
            val3 as CInt,
        )
    }
}

unsafe extern "C" fn futex_dispatch_invalid_bridge(cmd: CInt) {
    unsafe {
        kprintf(cstr(b"futex() invalid cmd: %d \n\0"), cmd);
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex(
    uaddr: *mut u32,
    op: CInt,
    val: u32,
    timeout: u64,
    uaddr2: *mut u32,
    val2: u32,
    val3: u32,
    fshared: CInt,
) -> CInt {
    unsafe {
        crate::sched_helpers::futex_dispatch_result(
            op,
            uaddr as usize,
            val,
            timeout,
            uaddr2 as usize,
            val2,
            val3,
            fshared,
            Some(futex_dispatch_wait_bridge),
            Some(futex_dispatch_wake_bridge),
            Some(futex_dispatch_requeue_bridge),
            Some(futex_dispatch_wake_op_bridge),
            Some(futex_dispatch_invalid_bridge),
        )
    }
}

#[no_mangle]
pub unsafe extern "C" fn futex_init() -> CInt {
    let ret = unsafe {
        crate::sched_helpers::futex_init_table_result(
            &raw mut futex_queues as usize,
            FUTEX_HASHBITS,
            size_of::<FutexHashBucket>(),
            IHK_MC_AP_NOWAIT,
            Some(futex_kmalloc_bridge),
            FUTEX_HASH_BUCKET_LOCK_OFFSET,
            0,
            FUTEX_HASH_BUCKET_CHAIN_OFFSET,
            offset_of!(PlistHead, prio_list),
            offset_of!(PlistHead, node_list),
            0,
            0,
        )
    };
    if ret < 0 {
        ret
    } else {
        0
    }
}
