// SPDX-License-Identifier: GPL-2.0
// Selected x86_64 Linux/McKernel application diagnostic, not a kernel provider.
// The unreaped child PID owns every cleanup signal target. An external owning
// process-group supervisor is mandatory; no native execution is released here.
#[cfg(not(all(target_os = "linux", target_arch = "x86_64", target_pointer_width = "64")))]
compile_error!("this frozen libc ABI is Linux x86_64 LP64 only");

use std::ffi::{CStr, CString, OsString};
use std::os::raw::{c_char, c_int, c_void};
use std::os::unix::ffi::OsStrExt;
use std::path::PathBuf;

const EINTR: i32 = 4;
const ECHILD: i32 = 10;
const EAGAIN: i32 = 11;
const ENOENT: i32 = 2;
const ESRCH: i32 = 3;
const WNOHANG: i32 = 1;
const O_NONBLOCK: i32 = 0x800;
const O_CLOEXEC: i32 = 0x80000;
const SIGCHLD: i32 = 17;
const SIGKILL: i32 = 9;
const POLLIN: i16 = 1;
const POLLOUT: i16 = 4;
const POLLHUP: i16 = 16;
const CHILD_OK: &[u8] = b"child exec success token=fixed-v1\n";
const CHILD_ERROR: &[u8] = b"child exec error errno=ENOENT state=37 unchanged=1\n";
const MISSING: &[u8] = b"/missing/frozen-executable\0";

#[repr(C)]
struct Timespec { sec: i64, nsec: i64 }
#[repr(C)]
struct PollFd { fd: c_int, events: i16, revents: i16 }

unsafe extern "C" {
    fn fork() -> c_int;
    fn execve(path: *const c_char, args: *const *const c_char, env: *const *const c_char) -> c_int;
    fn waitpid(pid: c_int, status: *mut c_int, options: c_int) -> c_int;
    fn pipe2(fds: *mut c_int, flags: c_int) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn dup2(old: c_int, new: c_int) -> c_int;
    fn read(fd: c_int, bytes: *mut c_void, count: usize) -> isize;
    fn write(fd: c_int, bytes: *const c_void, count: usize) -> isize;
    fn poll(fds: *mut PollFd, count: usize, timeout: c_int) -> c_int;
    fn clock_gettime(clock: c_int, value: *mut Timespec) -> c_int;
    fn kill(pid: c_int, signal: c_int) -> c_int;
    fn signal(signal: c_int, handler: usize) -> usize;
    fn __errno_location() -> *mut c_int;
    fn _exit(status: c_int) -> !;
    static mut environ: *const *const c_char;
}

fn errno() -> i32 { unsafe { *__errno_location() } }
fn now() -> Option<u64> {
    let mut time = Timespec { sec: 0, nsec: 0 };
    if unsafe { clock_gettime(1, &mut time) } != 0 || time.sec < 0 || !(0..1_000_000_000).contains(&time.nsec) { return None; }
    (time.sec as u64).checked_mul(1_000_000_000)?.checked_add(time.nsec as u64)
}
fn before(deadline: u64) -> bool { now().is_some_and(|value| value < deadline) }
fn pause(fd: i32, events: i16) -> bool {
    let mut item = PollFd { fd, events, revents: 0 };
    unsafe { poll(&mut item, 1, 10) >= 0 || errno() == EINTR }
}
fn raw_write(fd: i32, bytes: &[u8], deadline: u64) -> bool {
    let mut offset = 0;
    while offset < bytes.len() && before(deadline) {
        let count = unsafe { write(fd, bytes[offset..].as_ptr().cast(), bytes.len() - offset) };
        if count > 0 { offset += count as usize; }
        else if count < 0 && errno() == EINTR { continue; }
        else if count < 0 && errno() == EAGAIN && pause(fd, POLLOUT) { continue; }
        else { return false; }
    }
    offset == bytes.len()
}

struct ChildOwner { pid: i32, reader: i32, writer: i32, owned: bool, reaped: bool, status: i32 }
impl ChildOwner {
    fn close_reader(&mut self) -> bool {
        let fd = std::mem::replace(&mut self.reader, -1);
        fd < 0 || unsafe { close(fd) == 0 }
    }
    fn close_writer(&mut self) -> bool {
        let fd = std::mem::replace(&mut self.writer, -1);
        fd < 0 || unsafe { close(fd) == 0 }
    }
    fn reap_nonblocking(&mut self) -> Result<(), &'static str> {
        if self.reaped { return Ok(()); }
        let result = unsafe { waitpid(self.pid, &mut self.status, WNOHANG) };
        if result == self.pid { self.reaped = true; self.owned = false; }
        else if result < 0 && errno() != EINTR {
            if errno() == ECHILD { self.owned = false; }
            return Err("waitpid");
        }
        Ok(())
    }
    fn retire(&mut self) -> bool {
        if self.reaped || self.pid < 0 { return true; }
        if !self.owned { return false; }
        if unsafe { kill(self.pid, SIGKILL) } != 0 && errno() != ESRCH { return false; }
        let Some(end) = now().and_then(|value| value.checked_add(2_000_000_000)) else { return false; };
        while before(end) {
            if self.reap_nonblocking().is_err() { return false; }
            if self.reaped { return true; }
            if !pause(-1, 0) { return false; }
        }
        false
    }
}
impl Drop for ChildOwner {
    fn drop(&mut self) {
        self.close_reader(); self.close_writer();
        if !self.retire() { eprintln!("process-exec-wait cleanup_unproven=1 child={}", self.pid); }
    }
}

struct Observation { pid: i32, status: i32, code: i32, bytes: usize }

fn run_case(executable: &CStr, missing: bool, deadline: u64) -> Result<Observation, &'static str> {
    let mut pipes = [-1; 2];
    if unsafe { pipe2(pipes.as_mut_ptr(), O_NONBLOCK | O_CLOEXEC) } != 0 { return Err("pipe2"); }
    let mut child = ChildOwner { pid: -1, reader: pipes[0], writer: pipes[1], owned: false, reaped: false, status: -1 };
    let argv = [b"process-exec-child\0".as_ptr().cast(), b"--child\0".as_ptr().cast(), b"fixed-token\0".as_ptr().cast(), std::ptr::null()];
    let env = [b"PATH=/usr/bin:/bin\0".as_ptr().cast(), b"LC_ALL=C\0".as_ptr().cast(), b"PRACTICAL_EXEC_TOKEN=fixed-v1\0".as_ptr().cast(), std::ptr::null()];
    let pid = unsafe { fork() };
    if pid < 0 { return Err("fork"); }
    if pid == 0 {
        // No allocation, stdio, formatting or Rust destructors after fork.
        unsafe {
            if close(pipes[0]) != 0 || dup2(pipes[1], 1) < 0 || close(pipes[1]) != 0 { _exit(94); }
            let private_state = 37;
            let filename = if missing { MISSING.as_ptr().cast() } else { executable.as_ptr() };
            let result = execve(filename, argv.as_ptr(), env.as_ptr());
            let saved_errno = *__errno_location();
            if missing && result == -1 && saved_errno == ENOENT && private_state == 37 && raw_write(1, CHILD_ERROR, deadline) { _exit(42); }
            _exit(96);
        }
    }
    child.pid = pid; child.owned = true;
    if !child.close_writer() { return Err("parent close writer"); }
    let marker = if missing { CHILD_ERROR } else { CHILD_OK };
    let mut bytes = [0u8; 128];
    let mut kept = 0;
    let mut eof = false;
    while !child.reaped || !eof {
        if !before(deadline) { return Err("capture deadline"); }
        if !eof {
            if kept == bytes.len() { return Err("child output overflow"); }
            let count = unsafe { read(child.reader, bytes[kept..].as_mut_ptr().cast(), bytes.len() - kept) };
            if count > 0 { kept += count as usize; }
            else if count == 0 { eof = true; }
            else if errno() != EINTR && errno() != EAGAIN { return Err("read child"); }
        }
        child.reap_nonblocking()?;
        if (!child.reaped || !eof) && !pause(child.reader, POLLIN | POLLHUP) { return Err("poll child"); }
    }
    let expected = if missing { 42 } else { 37 };
    if child.status & 0x7f != 0 || (child.status >> 8) & 0xff != expected || &bytes[..kept] != marker { return Err("child result"); }
    if !child.close_reader() { return Err("parent close reader"); }
    loop {
        if !before(deadline) { return Err("second wait deadline"); }
        let mut status = -1;
        let result = unsafe { waitpid(pid, &mut status, WNOHANG) };
        let saved = errno();
        if result == -1 && saved == EINTR { continue; }
        if result != -1 || saved != ECHILD { return Err("second wait ECHILD"); }
        break;
    }
    if !raw_write(1, marker, deadline) { return Err("forward child marker"); }
    Ok(Observation { pid, status: child.status, code: expected, bytes: kept })
}

fn child_mode(args: &[OsString]) -> i32 {
    if args.len() != 3 || args[0] != "process-exec-child" || args[1] != "--child" || args[2] != "fixed-token" { return 90; }
    let expected: [&[u8]; 3] = [b"PATH=/usr/bin:/bin", b"LC_ALL=C", b"PRACTICAL_EXEC_TOKEN=fixed-v1"];
    unsafe {
        let env = environ;
        if env.is_null() { return 91; }
        for (index, value) in expected.iter().enumerate() {
            let pointer = *env.add(index);
            if pointer.is_null() || CStr::from_ptr(pointer).to_bytes() != *value { return 91; }
        }
        if !(*env.add(3)).is_null() { return 92; }
    }
    let Some(deadline) = now().and_then(|value| value.checked_add(2_000_000_000)) else { return 93; };
    if raw_write(1, CHILD_OK, deadline) { 37 } else { 93 }
}

fn parent(args: &[OsString]) -> Result<(), &'static str> {
    let observation = if args.len() == 1 { None } else if args.len() == 3 && args[1] == "--observations" { Some(PathBuf::from(&args[2])) } else { return Err("parent arguments"); };
    let path = args[0].as_bytes();
    if !path.starts_with(b"/") || path.len() > 4095 { return Err("absolute executable path"); }
    let executable = CString::new(path).map_err(|_| "executable NUL")?;
    // This disposable parent owns its SIGCHLD policy. Waitpid works even when
    // SIGCHLD is blocked; no signal delivery is used as a reaping oracle.
    if unsafe { signal(SIGCHLD, 0) } == usize::MAX { return Err("SIGCHLD policy"); }
    let deadline = now().and_then(|value| value.checked_add(6_000_000_000)).ok_or("clock")?;
    if !raw_write(1, b"parent start\n", deadline) { return Err("parent start"); }
    let success = run_case(&executable, false, deadline)?;
    if !raw_write(1, b"parent wait success exit=37 eof=1 reaped=1 echild=1\n", deadline) { return Err("success output"); }
    let error = run_case(&executable, true, deadline)?;
    if !raw_write(1, b"parent wait error exit=42 eof=1 reaped=1 echild=1\nparent complete children=2 owned=0\n", deadline) { return Err("error output"); }
    if let Some(path) = observation {
        let data = format!("{{\"parent_pid\":{},\"children\":[{{\"pid\":{},\"wait_status\":{},\"exit_code\":{},\"captured_bytes\":{},\"eof\":true,\"reaped\":true,\"second_wait_errno\":10,\"owned_after\":false}},{{\"pid\":{},\"wait_status\":{},\"exit_code\":{},\"captured_bytes\":{},\"eof\":true,\"reaped\":true,\"second_wait_errno\":10,\"owned_after\":false}}],\"owned_children\":0}}\n", std::process::id(), success.pid, success.status, success.code, success.bytes, error.pid, error.status, error.code, error.bytes);
        use std::io::Write;
        let mut file = std::fs::OpenOptions::new().write(true).create_new(true).open(path).map_err(|_| "create observations")?;
        file.write_all(data.as_bytes()).and_then(|_| file.sync_all()).map_err(|_| "write observations")?;
    }
    Ok(())
}

fn main() {
    let args: Vec<OsString> = std::env::args_os().collect();
    if args.get(1).is_some_and(|arg| arg == "--child") { std::process::exit(child_mode(&args)); }
    if let Err(stage) = parent(&args) { eprintln!("process-exec-wait failure stage={stage} errno={}", errno()); std::process::exit(1); }
}
