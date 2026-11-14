#![allow(dead_code)]
#![cfg_attr(not(test), no_std)]

#[path = "../abi.rs"]
mod abi;
#[path = "../string.rs"]
mod string;

#[cfg(test)]
mod bcmp_tests {
    use crate::string::bcmp;
    use core::ffi::c_void;
    use core::ptr::null;

    #[test]
    fn empty_null_does_not_read() {
        let byte = 0xffu8;
        unsafe {
            assert_eq!(bcmp(null(), null(), 0), 0);
            assert_eq!(bcmp(null(), (&byte as *const u8).cast(), 0), 0);
            assert_eq!(bcmp((&byte as *const u8).cast(), null(), 0), 0);
        }
    }

    #[test]
    fn equal_and_mismatched_bytes() {
        let left = [0x00u8, 0x7f, 0x80, 0xff, 0x01];
        let mut right = left;
        unsafe {
            for n in 0..=left.len() {
                assert_eq!(bcmp(left.as_ptr().cast(), right.as_ptr().cast(), n), 0);
            }
            for index in 0..left.len() {
                right[index] ^= 0x80;
                assert_ne!(bcmp(left.as_ptr().cast(), right.as_ptr().cast(), left.len()), 0);
                assert_ne!(bcmp(right.as_ptr().cast(), left.as_ptr().cast(), left.len()), 0);
                assert_eq!(bcmp(left.as_ptr().cast(), right.as_ptr().cast(), index), 0);
                right[index] ^= 0x80;
            }
        }
    }

    #[cfg(all(target_os = "linux", target_arch = "x86_64"))]
    #[test]
    fn reads_stop_at_guard_boundary() {
        unsafe extern "C" {
            fn getpagesize() -> i32;
            fn mmap(addr: *mut c_void, len: usize, prot: i32, flags: i32,
                    fd: i32, offset: i64) -> *mut c_void;
            fn mprotect(addr: *mut c_void, len: usize, prot: i32) -> i32;
            fn munmap(addr: *mut c_void, len: usize) -> i32;
        }
        unsafe {
            let page = getpagesize() as usize;
            // Two independently guarded buffers detect reads past either end.
            let a = mmap(core::ptr::null_mut(), page * 2, 3, 0x22, -1, 0);
            let b = mmap(core::ptr::null_mut(), page * 2, 3, 0x22, -1, 0);
            assert_ne!(a as usize, usize::MAX);
            assert_ne!(b as usize, usize::MAX);
            let ap = a.cast::<u8>().add(page);
            let bp = b.cast::<u8>().add(page);
            assert_eq!(mprotect(ap.cast(), page, 0), 0);
            assert_eq!(mprotect(bp.cast(), page, 0), 0);
            assert_eq!(bcmp(ap.cast(), bp.cast(), 0), 0);
            for n in 1..=64 {
                for i in 0..n {
                    ap.sub(n).add(i).write(i as u8 ^ 0x80);
                    bp.sub(n).add(i).write(i as u8 ^ 0x80);
                }
                assert_eq!(bcmp(ap.sub(n).cast(), bp.sub(n).cast(), n), 0);
                bp.sub(1).write(0x7f);
                assert_ne!(bcmp(ap.sub(n).cast(), bp.sub(n).cast(), n), 0);
                assert_ne!(bcmp(bp.sub(n).cast(), ap.sub(n).cast(), n), 0);
            }
            assert_eq!(munmap(a, page * 2), 0);
            assert_eq!(munmap(b, page * 2), 0);
        }
    }
}
