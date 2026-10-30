// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compiles the two copied candidate bodies unmodified, with controlled providers.
mod abi {
    use core::ffi::c_void;
    pub type CLong = i64;
    pub type CULong = u64;
    pub type SizeT = usize;
    #[repr(C)]
    pub struct Thread { pub fp_regs: *mut c_void }
}
mod x86_memory_helpers {
    use core::ffi::c_void;
    use std::sync::Mutex;
    #[derive(Clone, Copy, Debug, PartialEq)]
    pub struct Call { pub dst: usize, pub src: usize, pub len: usize, pub direction: u8 }
    pub static STATE: Mutex<(Option<Call>, usize, i32)> = Mutex::new((None, 0, 0));
    unsafe fn copy(dst: *mut c_void, src: *const c_void, len: usize, direction: u8) -> i32 {
        let mut s = STATE.lock().unwrap();
        s.0 = Some(Call { dst: dst as usize, src: src as usize, len, direction });
        let n = s.1.min(len);
        if n != 0 { unsafe { core::ptr::copy_nonoverlapping(src.cast::<u8>(), dst.cast::<u8>(), n) }; }
        s.2
    }
    pub unsafe fn copy_to_user(dst: *mut c_void, src: *const c_void, len: usize) -> i32 {
        unsafe { copy(dst, src, len, 1) }
    }
    pub unsafe fn copy_from_user(dst: *mut c_void, src: *const c_void, len: usize) -> i32 {
        unsafe { copy(dst, src, len, 2) }
    }
}
#[path = "f06_ptrace_xstate_copy_to.rs"] mod to;
#[path = "f06_ptrace_xstate_copy_from.rs"] mod from;
use abi::Thread;
use x86_memory_helpers::{Call, STATE};

#[test]
fn candidate_bridges_transfer_and_preserve_provider_results() {
    for direction in [1u8, 2] {
        let mut fp = [11u8, 22, 33, 44, 55, 66];
        let mut user = [91u8, 92, 93, 94, 95, 96];
        let mut thread = Thread { fp_regs: fp.as_mut_ptr().cast() };
        let thread_addr = (&mut thread as *mut Thread) as u64;
        let user_addr = user.as_mut_ptr() as u64;
        let fp_addr = fp.as_ptr() as usize;
        let invoke = |count| unsafe {
            if direction == 1 { to::arch_ptrace_xstate_copy_to_bridge(thread_addr, user_addr, count) }
            else { from::arch_ptrace_xstate_copy_from_bridge(thread_addr, user_addr, count) }
        };
        let expected_call = |len| Call {
            dst: if direction == 1 { user_addr as usize } else { fp_addr },
            src: if direction == 1 { fp_addr } else { user_addr as usize },
            len, direction,
        };
        *STATE.lock().unwrap() = (None, 4, 0);
        assert_eq!(invoke(4), 0);
        assert_eq!(STATE.lock().unwrap().0, Some(expected_call(4)));
        if direction == 1 { assert_eq!(user, [11, 22, 33, 44, 95, 96]); }
        else { assert_eq!(fp, [91, 92, 93, 94, 55, 66]); }
        // Provider may alter only a prefix even on a negative return.
        fp = [1, 2, 3, 4, 5, 6]; user = [7, 8, 9, 10, 11, 12];
        *STATE.lock().unwrap() = (None, 2, -14);
        assert_eq!(invoke(5), -14);
        assert_eq!(STATE.lock().unwrap().0, Some(expected_call(5)));
        if direction == 1 { assert_eq!(user, [1, 2, 9, 10, 11, 12]); }
        else { assert_eq!(fp, [7, 8, 3, 4, 5, 6]); }
        *STATE.lock().unwrap() = (None, 0, i32::MIN);
        assert_eq!(invoke(0), i32::MIN as i64);
        assert_eq!(STATE.lock().unwrap().0, Some(expected_call(0)));
        // A positive provider return is also widened without normalization.
        *STATE.lock().unwrap() = (None, 0, 37);
        assert_eq!(invoke(3), 37);
        assert_eq!(STATE.lock().unwrap().0, Some(expected_call(3)));
        thread.fp_regs = core::ptr::null_mut();
        assert!(thread.fp_regs.is_null());
        *STATE.lock().unwrap() = (None, 0, 37);
        assert_eq!(invoke(3), -12);
        assert!(STATE.lock().unwrap().0.is_none());
    }
}
