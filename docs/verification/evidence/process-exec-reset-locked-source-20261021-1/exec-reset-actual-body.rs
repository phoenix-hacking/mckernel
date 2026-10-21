use core::ffi::c_void;
use core::mem::{size_of, offset_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut};
use core::sync::atomic::{AtomicPtr, AtomicUsize, Ordering};
#[path="/home/holden/mckernel/kernel/rust/abi.rs"] mod abi;
#[path="exec_reset_signal_state_current_v1.rs"] mod candidate;
use abi::{Thread, SigCommon, SigStack, KSigAction};
static CURRENT: AtomicPtr<Thread> = AtomicPtr::new(core::ptr::null_mut());
static CALLS: AtomicUsize = AtomicUsize::new(0);
static OBSERVATION_FAILURES: AtomicUsize = AtomicUsize::new(0);
unsafe extern "C" {
    fn exec_reset_c_reference(common: *mut c_void, stack: *mut c_void);
    fn c_action_offset() -> usize;
}
unsafe fn observed(common: *mut SigCommon, stack: *mut SigStack) {
    // The original order requires all caught handlers reset before the FP
    // callback and the old alternate stack still present during that call.
    for i in 0..64 {
        if (*common).action[i].sa.sa_handler as usize > 1 {
            OBSERVATION_FAILURES.fetch_add(1, Ordering::SeqCst);
        }
    }
    if (*stack).ss_sp as usize != 0x12345000 || (*stack).ss_flags != 1
        || (*stack).ss_size != 65536 || (*stack).padding != 0x5a5a5a5a {
        OBSERVATION_FAILURES.fetch_add(1, Ordering::SeqCst);
    }
    CALLS.fetch_add(1, Ordering::SeqCst);
}
#[no_mangle]
unsafe extern "C" fn clear_fp_regs() {
    let thread = CURRENT.load(Ordering::SeqCst);
    observed((*thread).sigcommon.cast(), addr_of_mut!((*thread).sigstack));
}
#[no_mangle]
unsafe extern "C" fn oracle_observe_fp(common: *mut c_void, stack: *mut c_void) {
    observed(common.cast(), stack.cast());
}
unsafe fn bytes<T>(p: *const T) -> Vec<u8> {
    core::slice::from_raw_parts(p.cast::<u8>(), size_of::<T>()).to_vec()
}
unsafe fn init(thread: *mut Thread, common: *mut SigCommon, seed: usize) {
    core::ptr::write_bytes(thread.cast::<u8>(), 0, size_of::<Thread>());
    core::ptr::write_bytes(common.cast::<u8>(), 0, size_of::<SigCommon>());
    (*thread).sigcommon = common.cast();
    (*thread).sigmask.val[0] = 0xdeadbeef98765432;
    (*thread).status = 1;
    (*thread).tid = 37;
    (*thread).sigstack.ss_sp = 0x12345000 as *mut c_void;
    (*thread).sigstack.ss_flags = 1;
    (*thread).sigstack.padding = 0x5a5a5a5a;
    (*thread).sigstack.ss_size = 65536;
    (*common).use_.counter = 7;
    for i in 0..64 {
        let handler = match seed {
            0 => 0, 1 => 1, 2 => 0x400000,
            _ => [0, 1, 0x400000, usize::MAX, 0x12345000][(i + seed) % 5],
        };
        (*common).action[i].sa.sa_handler = handler as *mut c_void;
        (*common).action[i].sa.sa_flags = (i as u64) << 32 | 0xfedcba98;
        (*common).action[i].sa.sa_restorer = (0x55550000 + i * 16) as *mut c_void;
        (*common).action[i].sa.sa_mask.val[0] = 0xabcdef0123456789 ^ i as u64;
    }
}
#[test]
fn actual_body_matches_literal_c_and_preserves_owners_and_order() {
    unsafe {
        assert_eq!(size_of::<KSigAction>(), 32);
        assert_eq!(size_of::<SigStack>(), 24);
        assert_eq!(offset_of!(SigCommon, action), c_action_offset());
        let mut rust_thread = Box::new(MaybeUninit::<Thread>::zeroed());
        let mut c_thread = Box::new(MaybeUninit::<Thread>::zeroed());
        let mut rust_common = Box::new(MaybeUninit::<SigCommon>::zeroed());
        let mut c_common = Box::new(MaybeUninit::<SigCommon>::zeroed());
        for seed in [0, 1, 2, 3, 7, 63, 64, 255] {
            let rt = rust_thread.as_mut_ptr(); let ct = c_thread.as_mut_ptr();
            let rc = rust_common.as_mut_ptr(); let cc = c_common.as_mut_ptr();
            init(rt, rc, seed); init(ct, cc, seed);
            let old_thread = bytes(rt); let old_common = bytes(rc);
            CALLS.store(0, Ordering::SeqCst); OBSERVATION_FAILURES.store(0, Ordering::SeqCst);
            CURRENT.store(rt, Ordering::SeqCst);
            candidate::exec_reset_signal_state_current_v1(rt);
            exec_reset_c_reference(cc.cast(), addr_of_mut!((*ct).sigstack).cast());
            assert_eq!(CALLS.load(Ordering::SeqCst), 2);
            assert_eq!(OBSERVATION_FAILURES.load(Ordering::SeqCst), 0);
            assert_eq!(bytes(rc), bytes(cc));
            assert_eq!(bytes(addr_of!((*rt).sigstack)), bytes(addr_of!((*ct).sigstack)));
            for i in 0..64 {
                let at = offset_of!(SigCommon, action) + i * size_of::<KSigAction>();
                let old = usize::from_ne_bytes(old_common[at..at+8].try_into().unwrap());
                assert_eq!((*rc).action[i].sa.sa_handler as usize, if old <= 1 { old } else { 0 });
            }
            let mut expected_common = old_common;
            for i in 0..64 {
                let at = offset_of!(SigCommon, action) + i * size_of::<KSigAction>();
                expected_common[at..at+8].copy_from_slice(&bytes(rc)[at..at+8]);
            }
            assert_eq!(bytes(rc), expected_common);
            let mut expected_thread = old_thread;
            let stack_at = offset_of!(Thread, sigstack);
            for (at, len) in [(offset_of!(SigStack, ss_sp), 8), (offset_of!(SigStack, ss_flags), 4), (offset_of!(SigStack, ss_size), 8)] {
                expected_thread[stack_at+at..stack_at+at+len].fill(0);
            }
            expected_thread[stack_at+offset_of!(SigStack, ss_flags)..stack_at+offset_of!(SigStack, ss_flags)+4]
                .copy_from_slice(&2i32.to_ne_bytes());
            assert_eq!(bytes(rt), expected_thread);
        }
        CURRENT.store(core::ptr::null_mut(), Ordering::SeqCst);
    }
}
