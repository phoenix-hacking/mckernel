// IHK/McKernel mcps Rust wrapper, derived from mcps.in.
// Original author: Balazs Gerofi <bgerofi@riken.jp>, Copyright (C) 2019 RIKEN.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private Linux x86_64 candidate. Existing mcinspect Rust still owns --ps.
#![no_std]
#![no_main]
#[cfg(not(all(target_os = "linux", target_arch = "x86_64")))]
compile_error!("Candidate is bound to the selected Linux x86_64 profile");
use core::ffi::{c_char, c_int, c_void};
use core::ptr::{null, null_mut};
macro_rules! c { ($s:literal) => { concat!($s, "\0").as_ptr().cast::<c_char>() }; }
const PROGRAM: &[u8] = concat!(env!("MCPS_PREFIX"), "/bin/mcinspect\0").as_bytes();
const KERNEL: &[u8] = concat!("--kernel=", env!("MCPS_MCKERNELDIR"), "/mckernel.img\0").as_bytes();
extern "C" {
    static mut environ: *mut *mut c_char;
    static mut stderr: *mut c_void;
    fn posix_spawn(pid: *mut c_int, path: *const c_char,
        actions: *const c_void, attributes: *const c_void,
        argv: *const *mut c_char, envp: *const *mut c_char) -> c_int;
    fn waitpid(pid: c_int, status: *mut c_int, options: c_int) -> c_int;
    fn __errno_location() -> *mut c_int;
    fn strerror(error: c_int) -> *const c_char;
    fn strsignal(signal: c_int) -> *const c_char;
    fn opendir(path: *const c_char) -> *mut c_void;
    fn closedir(directory: *mut c_void) -> c_int;
    fn fprintf(stream: *mut c_void, fmt: *const c_char, ...) -> c_int;
    fn abort() -> !;
}
#[panic_handler]
fn panic(_: &core::panic::PanicInfo<'_>) -> ! { unsafe { abort() } }
#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut c_char) -> c_int {
    // The shipped script ignores all arguments. Do not forward user options.
    let arguments = [PROGRAM.as_ptr() as *mut c_char,
        KERNEL.as_ptr() as *mut c_char, c!("--ps") as *mut c_char, null_mut()];
    let mut pid = 0;
    let error = posix_spawn(&mut pid, PROGRAM.as_ptr().cast(), null(), null(),
        arguments.as_ptr(), environ);
    let name = if argc > 0 && !argv.is_null() && !(*argv).is_null() { *argv as *const c_char } else { c!("mcps") };
    if error != 0 {
        // Preserve C-locale shell launch diagnostics for the supported installed
        // executable, missing-file and ordinary permission-error cases.
        let mut message = strerror(error);
        let directory = opendir(PROGRAM.as_ptr().cast());
        if !directory.is_null() {
            closedir(directory);
            message = c!("Is a directory");
        }
        fprintf(stderr, c!("%s: line 10: %s: %s\n"), name,
            PROGRAM.as_ptr().cast::<c_char>(), message);
        return if error == 2 { 127 } else { 126 };
    }
    let mut status = 0;
    loop {
        let result = waitpid(pid, &mut status, 0);
        if result == pid { break; }
        if result < 0 && *__errno_location() == 4 { continue; }
        fprintf(stderr, c!("%s: waitpid: %s\n"), name, strerror(*__errno_location()));
        return 127;
    }
    let signal = status & 0x7f;
    if signal == 0 { return (status >> 8) & 0xff; }
    if signal != 0x7f {
        // The retained C-locale Bash oracle has two distinct notification
        // forms. Use the real waited-for child PID, actual signal and original
        // script command representation; no fixture names/values are consumed.
        // Other signal notifications/core-dump and inherited-disposition
        // parity remain explicitly unqualified in this bounded correction.
        let message = strsignal(signal);
        if signal == 15 && !message.is_null() {
            fprintf(stderr, c!("%s\n"), message);
        } else if signal == 9 && !message.is_null() {
            fprintf(stderr, c!("%s: line 10: %5d %-24s%s\n"), name, pid,
                message, c!("${BINDIR}/mcinspect --kernel=${KERNDIR}/mckernel.img --ps"));
        }
        return 128 + signal;
    }
    127
}
