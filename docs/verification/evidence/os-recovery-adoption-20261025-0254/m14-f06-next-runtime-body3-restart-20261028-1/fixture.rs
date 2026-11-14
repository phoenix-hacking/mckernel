// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Compile the complete candidate unchanged against the real snapshotted ABI;
// only the preexisting user-copy provider is replaced by a deterministic effect.
#![allow(dead_code, unexpected_cfgs)]
#[path = "abi.snapshot.rs"]
mod abi;
#[path = "f06_ptrace_xstate_copy_to.rs"]
mod candidate;
use core::ffi::c_void;
use core::mem::{align_of, offset_of, size_of};
use core::ptr::addr_of_mut;

#[repr(C)]
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct Trace {
    calls: u64,
    dst: u64,
    src: u64,
    bytes: u64,
    result: i32,
    padding: u32,
    written: u64,
}

unsafe extern "C" {
    fn original_arch_ptrace_xstate_copy_to_bridge(thread: u64, user: u64, bytes: usize) -> i64;
    fn fixture_reset(result: i32, valid_dst: u64, prefix: usize);
    fn fixture_read_trace(out: *mut Trace);
    fn fixture_copy_to_user(dst: *mut c_void, src: *const c_void, bytes: usize) -> i32;
}

mod x86_memory_helpers {
    use super::c_void;
    pub unsafe extern "C" fn copy_to_user(dst: *mut c_void, src: *const c_void, bytes: usize) -> i32 {
        // Test-only effect; real production source still calls its existing Rust provider.
        unsafe { super::fixture_copy_to_user(dst, src, bytes) }
    }
}

#[repr(align(64))]
struct ThreadStorage([u8; size_of::<abi::Thread>()]);
#[repr(align(64))]
struct Bytes([u8; 4096]);

#[test]
fn exact_original_c_and_rust_xstate_copy_to() {
    assert_eq!(size_of::<abi::Thread>(), 5568);
    assert_eq!(align_of::<abi::Thread>(), 64);
    assert_eq!(offset_of!(abi::Thread, fp_regs), 4784);
    assert_eq!(size_of::<abi::XsaveStruct>(), 1088);
    assert_eq!(align_of::<abi::XsaveStruct>(), 64);
    assert_eq!(size_of::<Trace>(), 48);
    // Raw aligned backing avoids a second modeled Thread layout or references
    // over kernel state. Only the original fp_regs pointer field is accessed.
    let mut thread_storage = Box::new(ThreadStorage([0; size_of::<abi::Thread>()]));
    let thread = thread_storage.0.as_mut_ptr().cast::<abi::Thread>();
    let mut source = Box::new(Bytes([0; 4096]));
    let mut destination = Box::new(Bytes([0; 4096]));
    for (i, byte) in source.0.iter_mut().enumerate() {
        *byte = ((i * 29 + 17) % 251) as u8;
    }
    let source_before = source.0;
    let initial = [0xA7u8; 4096];
    let sizes = [0usize, 1, 511, 512, 576, 1088, 1089, 1usize << 63, usize::MAX];
    let results = [i32::MIN, -513, -14, -12, -1, 0, 1, 14, i32::MAX];
    let prefixes = [0usize, 1, 19, 1088];
    let mut pairs = 0usize;
    for present in [false, true] {
        for bytes in sizes {
            for result in results {
                for user_kind in 0..3 {
                    for prefix in prefixes {
                        let fp = if present { source.0.as_mut_ptr().cast::<c_void>() }
                                 else { core::ptr::null_mut() };
                        unsafe { core::ptr::write(addr_of_mut!((*thread).fp_regs), fp); }
                        let thread_before = thread_storage.0;
                        let valid_dst = destination.0.as_mut_ptr() as u64;
                        let user = match user_kind {
                            0 => valid_dst,
                            1 => 0,
                            _ => 0xffff_ffff_ffff_f001,
                        };
                        destination.0 = initial;
                        unsafe { fixture_reset(result, valid_dst, prefix); }
                        let c_result = unsafe {
                            original_arch_ptrace_xstate_copy_to_bridge(thread as u64, user, bytes)
                        };
                        let mut c_trace = Trace::default();
                        unsafe { fixture_read_trace(&mut c_trace); }
                        let c_destination = destination.0;
                        assert_eq!(source.0, source_before, "C source remains borrowed");
                        assert_eq!(thread_storage.0, thread_before, "C Thread unchanged");

                        destination.0 = initial;
                        unsafe { fixture_reset(result, valid_dst, prefix); }
                        let rust_result = unsafe {
                            candidate::arch_ptrace_xstate_copy_to_bridge(thread as u64, user, bytes)
                        };
                        let mut rust_trace = Trace::default();
                        unsafe { fixture_read_trace(&mut rust_trace); }
                        let tag = (present, bytes, result, user_kind, prefix);
                        assert_eq!(rust_result, c_result, "return {tag:?}");
                        assert_eq!(rust_trace, c_trace, "provider order/args/result {tag:?}");
                        assert_eq!(destination.0, c_destination, "all destination bytes {tag:?}");
                        assert_eq!(source.0, source_before, "Rust source remains borrowed {tag:?}");
                        assert_eq!(thread_storage.0, thread_before, "Rust Thread unchanged {tag:?}");

                        // Independent expected behavior, including int32 sign extension,
                        // no copy on null FP state and no local user/count normalization.
                        let expected_result = if present { result as i64 } else { -12 };
                        assert_eq!(rust_result, expected_result, "independent return {tag:?}");
                        let written = if present && user_kind == 0 { bytes.min(prefix).min(4096) }
                                      else { 0 };
                        let expected_trace = if present {
                            Trace { calls: 1, dst: user, src: fp as u64, bytes: bytes as u64,
                                    result, padding: 0, written: written as u64 }
                        } else { Trace::default() };
                        assert_eq!(rust_trace, expected_trace, "independent effect {tag:?}");
                        let mut expected_destination = initial;
                        expected_destination[..written].copy_from_slice(&source_before[..written]);
                        assert_eq!(destination.0, expected_destination, "independent full canary {tag:?}");
                        pairs += 1;
                    }
                }
            }
        }
    }
    assert_eq!(pairs, 1944);
    println!("functional xstate-copy-to original-C/Rust pairs={pairs}; calls, sign extension, partial bytes and borrow/canaries checked");
}
