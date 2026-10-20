// Supported x86_64/4KiB-page diagnostic. Oracle frozen before compilation.
// No protection fault handler, fork, pointer guessing or kernel implementation.
use std::io::{self, Write};
use std::os::raw::{c_int, c_void};
use std::ptr;

extern "C" {
    fn getpagesize() -> c_int;
    fn mmap(address: *mut c_void, length: usize, protection: c_int,
            flags: c_int, fd: c_int, offset: i64) -> *mut c_void;
    fn mprotect(address: *mut c_void, length: usize, protection: c_int) -> c_int;
    fn munmap(address: *mut c_void, length: usize) -> c_int;
    fn __errno_location() -> *mut c_int;
}
const PROT_NONE: c_int = 0;
const PROT_READ: c_int = 1;
const PROT_WRITE: c_int = 2;
const MAP_PRIVATE_ANONYMOUS: c_int = 0x02 | 0x20;
const EINVAL: c_int = 22;
const EXPECTED: &[u8] = b"mprotect_unaligned rejected=1 errno=22 unchanged=1 writable=1 unmapped=1\n";

fn require(ok: bool, reason: &'static str) -> io::Result<()> {
    if ok { Ok(()) } else { Err(io::Error::new(io::ErrorKind::Other, reason)) }
}
fn pattern(offset: usize) -> u8 { ((offset * 29) ^ (offset >> 8)) as u8 }

fn run() -> io::Result<()> {
    let page = unsafe { getpagesize() };
    require(page == 4096, "unsupported page geometry")?;
    let page = page as usize;
    let length = page * 2;
    let allocation = unsafe {
        mmap(ptr::null_mut(), length, PROT_READ | PROT_WRITE,
             MAP_PRIVATE_ANONYMOUS, -1, 0)
    };
    if allocation == (-1isize) as *mut c_void { return Err(io::Error::last_os_error()); }
    require(!allocation.is_null(), "unexpected zero mapping address")?;
    let base = allocation.cast::<u8>();
    // The original allocation remains process-owned throughout every check.
    // On failure, exit nonzero without inventing successful release or retrying.
    // The native owner must still prove actual process/OS retirement separately.
    for offset in 0..length {
        unsafe { ptr::write_volatile(base.add(offset), pattern(offset)); }
    }
    let errno = unsafe { __errno_location() };
    require(!errno.is_null(), "missing errno location")?;
    unsafe { *errno = 0; }
    let result = unsafe { mprotect(base.add(1).cast(), page, PROT_NONE) };
    let observed_errno = unsafe { *errno };
    require(result == -1 && observed_errno == EINVAL,
            "unaligned mprotect did not refuse with EINVAL")?;
    // Catch an implementation that reports EINVAL after changing accessibility
    // or bytes. These are real accesses, not an errno-only success condition.
    for offset in 0..length {
        require(unsafe { ptr::read_volatile(base.add(offset)) } == pattern(offset),
                "failed protection changed original data")?;
    }
    for offset in [0, page, length - 1] {
        let changed = pattern(offset) ^ 0xa5;
        unsafe { ptr::write_volatile(base.add(offset), changed); }
        require(unsafe { ptr::read_volatile(base.add(offset)) } == changed,
                "original mapping no longer writable")?;
    }
    if unsafe { munmap(allocation, length) } != 0 {
        return Err(io::Error::last_os_error());
    }
    // No pointer access after the one checked successful release.
    let mut stdout = io::stdout().lock();
    stdout.write_all(EXPECTED)?;
    stdout.flush()
}
fn main() {
    if let Err(error) = run() {
        let _ = writeln!(io::stderr().lock(), "mprotect_unaligned failure: {error}");
        std::process::exit(1);
    }
}
