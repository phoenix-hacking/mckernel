// SPDX-License-Identifier: GPL-2.0-only
//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Generic supervisor extracted from qualified F05 source61bdd82d; startup
//! omits case-specific observer code and preserves all actual process ownership.
pub type Check<T> = Result<T, String>;
use std::ffi::{c_char, c_int, c_void, CString};
use std::fs::{File, OpenOptions};
use std::os::fd::AsRawFd;
use std::os::unix::fs::OpenOptionsExt;

pub const MS: u64 = 1_000_000;
pub const STREAM_LIMIT: usize = 1024;
pub const PAYLOAD_ENV: &[&str] = &["PATH=/usr/bin:/bin", "COKERNEL_PATH=/apps"];
pub const HELPER_ENV: &[&str] = &["PATH=/bin:/sbin:/usr/bin:/usr/sbin", "LC_ALL=C"];
const EINTR: i32 = 4;
const ECHILD: i32 = 10;
const EAGAIN: i32 = 11;
const ESRCH: i32 = 3;
const EACCES: i32 = 13;
const O_CLOEXEC: i32 = 0x80000;
const O_NONBLOCK: i32 = 0x800;

#[repr(C)]
pub struct Timespec {
    pub seconds: i64,
    pub nanos: i64,
}
#[repr(C)]
struct PollFd {
    fd: c_int,
    events: i16,
    returned: i16,
}
const _: [(); 16] = [(); std::mem::size_of::<Timespec>()];
const _: [(); 8] = [(); std::mem::align_of::<Timespec>()];
const _: [(); 8] = [(); std::mem::size_of::<PollFd>()];
const _: [(); 4] = [(); std::mem::align_of::<PollFd>()];
unsafe extern "C" {
    fn __errno_location() -> *mut c_int;
    fn clock_gettime(clock: c_int, time: *mut Timespec) -> c_int;
    fn pipe2(pipe: *mut c_int, flags: c_int) -> c_int;
    fn fcntl(fd: c_int, command: c_int, ...) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn fork() -> c_int;
    fn setpgid(pid: c_int, group: c_int) -> c_int;
    fn dup2(old: c_int, new: c_int) -> c_int;
    fn open(path: *const c_char, flags: c_int, ...) -> c_int;
    fn chdir(path: *const c_char) -> c_int;
    fn execve(path: *const c_char, argv: *const *const c_char, env: *const *const c_char) -> c_int;
    fn _exit(status: c_int) -> !;
    fn read(fd: c_int, data: *mut c_void, count: usize) -> isize;
    fn write(fd: c_int, data: *const c_void, count: usize) -> isize;
    fn kill(pid: c_int, signal: c_int) -> c_int;
    fn waitid(which: c_int, pid: u32, info: *mut c_void, options: c_int) -> c_int;
    fn waitpid(pid: c_int, status: *mut c_int, options: c_int) -> c_int;
    fn poll(fds: *mut PollFd, count: usize, timeout: c_int) -> c_int;
    fn opendir(path: *const c_char) -> *mut c_void;
    fn readdir(directory: *mut c_void) -> *const c_void;
    fn closedir(directory: *mut c_void) -> c_int;
    pub fn nanosleep(time: *const Timespec, rest: *mut Timespec) -> c_int;
}
fn errno() -> i32 {
    // libc gives this thread's initialized errno slot; no pointer is retained.
    unsafe { *__errno_location() }
}
pub fn now_ns() -> u64 {
    let mut time = Timespec {
        seconds: 0,
        nanos: 0,
    };
    // Fixed Linux CLOCK_MONOTONIC and an exclusively borrowed output structure.
    if unsafe { clock_gettime(1, &mut time) } != 0 || time.seconds < 0 || time.nanos < 0 {
        return 0;
    }
    (time.seconds as u64)
        .checked_mul(1_000_000_000)
        .and_then(|v| v.checked_add(time.nanos as u64))
        .unwrap_or(0)
}
pub fn bounded_deadline(requested: u64, outer: u64, reserve: u64) -> u64 {
    requested.min(outer.saturating_sub(reserve))
}
/// Original Cstartup retirement: readable empty numeric procfs namespace within
/// the same5s absolute deadline. This is not the separate F05 lifecycle proof.
pub fn startup_retirement_ready(current: u64, end: u64, namespace: Check<bool>) -> Check<bool> {
    if current == 0 || current >= end {
        return Err("original post-reap retirement deadline".into());
    }
    namespace
}
pub fn sleep_ms(ms: u64) {
    let time = Timespec {
        seconds: (ms / 1000) as i64,
        nanos: ((ms % 1000) * MS) as i64,
    };
    // A signal may shorten pacing; the next turn always checks the same deadline.
    unsafe {
        nanosleep(&time, std::ptr::null_mut());
    }
}

#[derive(Default, Clone)]
pub struct Stream {
    pub data: Vec<u8>,
    pub observed: u64,
    pub eof_ns: u64,
    pub eof: bool,
}
#[derive(Clone)]
pub struct ResultRecord {
    pub out: Stream,
    pub err: Stream,
    pub status: i32,
    pub fault: bool,
    pub timeout: bool,
    pub clean: bool,
    pub child_stage: i32,
    pub child_errno: i32,
    pub started: u64,
    pub reaped: u64,
    pub finished: u64,
}
impl Default for ResultRecord {
    fn default() -> Self {
        Self {
            out: Stream::default(),
            err: Stream::default(),
            status: -1,
            fault: false,
            timeout: false,
            clean: false,
            child_stage: 0,
            child_errno: 0,
            started: 0,
            reaped: 0,
            finished: 0,
        }
    }
}
impl Stream {
    pub fn append(&mut self, bytes: &[u8]) -> Check<()> {
        let kept = bytes.len().min(STREAM_LIMIT - self.data.len());
        self.data.extend_from_slice(&bytes[..kept]);
        self.observed = self
            .observed
            .checked_add(bytes.len() as u64)
            .ok_or("stream counter overflow")?;
        Ok(())
    }
}
fn drain(fd: i32, stream: &mut Stream, deadline: u64) -> Check<()> {
    let mut bytes = [0; 512];
    for _ in 0..4 {
        if stream.eof {
            break;
        }
        let now = now_ns();
        if now == 0 {
            return Err("stream clock unavailable".into());
        }
        if now >= deadline {
            break;
        }
        // The pipe descriptor remains owned by supervise; bytes has this capacity.
        let count = unsafe { read(fd, bytes.as_mut_ptr().cast(), bytes.len()) };
        if count > 0 {
            stream.append(&bytes[..count as usize])?;
        } else if count == 0 {
            stream.eof = true;
            stream.eof_ns = now_ns();
        } else if errno() == EAGAIN {
            break;
        } else if errno() != EINTR {
            return Err(format!("capture pipe read errno {}", errno()));
        }
    }
    Ok(())
}
struct Pipes([[i32; 2]; 3]);
impl Drop for Pipes {
    fn drop(&mut self) {
        for pair in self.0 {
            for fd in pair {
                if fd >= 0 {
                    unsafe {
                        close(fd);
                    }
                }
            }
        }
    }
}
fn make_pipe() -> Check<[i32; 2]> {
    let mut pair = [-1; 2];
    // pipe2 initializes exactly two descriptor slots. Every success transfers
    // descriptors to this function, then to Pipes; failure closes both here.
    unsafe {
        if pipe2(pair.as_mut_ptr(), O_CLOEXEC) != 0 {
            return Err("pipe2 failed".into());
        }
        let configure = (|| {
            for fd in &mut pair {
                if *fd < 3 {
                    let promoted = fcntl(*fd, 1030, 3); // F_DUPFD_CLOEXEC
                    if promoted < 0 {
                        return Err("pipe descriptor promotion failed".into());
                    }
                    close(*fd);
                    *fd = promoted;
                }
            }
            let flags = fcntl(pair[0], 3); // F_GETFL
            if flags < 0 || fcntl(pair[0], 4, flags | O_NONBLOCK) < 0 {
                return Err("pipe nonblocking configuration failed".into());
            }
            Ok(())
        })();
        if let Err(error) = configure {
            close(pair[0]);
            close(pair[1]);
            return Err(error);
        }
    }
    Ok(pair)
}
unsafe fn child_abort(fd: i32, stage: i32) -> ! {
    let fault = [stage, errno()];
    loop {
        let n = write(fd, fault.as_ptr().cast(), 8);
        if n >= 0 || errno() != EINTR {
            break;
        }
    }
    _exit(126)
}
/// Only an unreaped leader pins both the PID and its process-group number.
/// Positive leader reap or lost child custody irreversibly removes authority.
struct LeaderOwnership {
    pid: i32,
    unreaped: bool,
}
impl LeaderOwnership {
    fn new(pid: i32) -> Self {
        Self {
            pid,
            unreaped: true,
        }
    }
    fn positive_reap(&mut self, pid: i32) {
        if pid == self.pid {
            self.unreaped = false;
        }
    }
    fn no_children(&mut self) {
        self.unreaped = false;
    }
    fn signal_with(&self, signal: i32, mut operation: impl FnMut(i32, i32) -> bool) -> bool {
        if !self.unreaped {
            return false;
        }
        let group = operation(-self.pid, signal);
        let leader = operation(self.pid, signal);
        group && leader
    }
    fn signal(&self, signal: i32) -> bool {
        self.signal_with(signal, |target, signal| {
            // The guard above pins both numbers through these two calls.
            unsafe { kill(target, signal) == 0 || errno() == ESRCH }
        })
    }
}

/// Real /bin/mcexec remains the direct child, with the exact old argv/env/cwd.
/// This is the existing 10s deadline, TERM at stop, KILL after100ms, and 2s reap
/// reserve. This fixed startup build omits the F05 observer entirely: the
/// qualified predecessor's constant observer=None hooks have no operation.
pub fn supervise(
    path: &str,
    argv: &[&str],
    env: &[&str],
    cwd: Option<&str>,
    timeout_ms: u64,
    outer: u64,
) -> ResultRecord {
    let mut result = ResultRecord::default();
    result.started = now_ns();
    let operation = (|| -> Check<()> {
        if result.started == 0 {
            return Err("supervisor monotonic clock unavailable".into());
        }
        let limit = bounded_deadline(result.started + timeout_ms * MS, outer, 2000 * MS);
        if limit <= result.started {
            result.timeout = true;
            return Err("no application deadline reserve".into());
        }
        let path = CString::new(path).map_err(|_| "NUL executable path")?;
        let args: Vec<_> = argv
            .iter()
            .map(|s| CString::new(*s))
            .collect::<Result<_, _>>()
            .map_err(|_| "NUL argv")?;
        let environment: Vec<_> = env
            .iter()
            .map(|s| CString::new(*s))
            .collect::<Result<_, _>>()
            .map_err(|_| "NUL env")?;
        let mut ap: Vec<_> = args.iter().map(|s| s.as_ptr()).collect();
        ap.push(std::ptr::null());
        let mut ep: Vec<_> = environment.iter().map(|s| s.as_ptr()).collect();
        ep.push(std::ptr::null());
        let cwd = cwd.map(CString::new).transpose().map_err(|_| "NUL cwd")?;
        let mut pipes = Pipes([[-1; 2]; 3]);
        for pair in &mut pipes.0 {
            *pair = make_pipe()?;
        }
        // No threads exist. The child uses only async-signal-safe libc calls,
        // prebuilt CStrings and stack storage, then execve/_exit without Drop.
        let child = unsafe { fork() };
        if child < 0 {
            return Err("fork failed".into());
        }
        if child == 0 {
            unsafe {
                if setpgid(0, 0) != 0 {
                    child_abort(pipes.0[2][1], 1);
                }
                if dup2(pipes.0[0][1], 1) < 0 || dup2(pipes.0[1][1], 2) < 0 {
                    child_abort(pipes.0[2][1], 2);
                }
                for (index, pair) in pipes.0.iter().enumerate() {
                    close(pair[0]);
                    if index != 2 {
                        close(pair[1]);
                    }
                }
                let nullfd = open(b"/dev/null\0".as_ptr().cast(), O_CLOEXEC);
                if nullfd < 0 || dup2(nullfd, 0) < 0 {
                    child_abort(pipes.0[2][1], 3);
                }
                if nullfd != 0 {
                    close(nullfd);
                } else if fcntl(0, 2, 0) != 0 {
                    child_abort(pipes.0[2][1], 3);
                }
                if let Some(cwd) = &cwd {
                    if chdir(cwd.as_ptr()) != 0 {
                        child_abort(pipes.0[2][1], 4);
                    }
                }
                execve(path.as_ptr(), ap.as_ptr(), ep.as_ptr());
                child_abort(pipes.0[2][1], 5);
            }
        }
        let mut leader = LeaderOwnership::new(child);
        for pair in &mut pipes.0 {
            unsafe {
                close(pair[1]);
            }
            pair[1] = -1;
        }
        if unsafe { setpgid(child, child) } != 0 && ![EACCES, ESRCH].contains(&errno()) {
            result.fault = true;
        }
        let mut setup = [0u8; 9];
        let mut setup_n = 0;
        let mut setup_eof = false;
        let mut stopping = false;
        let mut killed = false;
        let mut ready = false;
        let mut stop_at = 0;
        loop {
            let now = now_ns();
            if now == 0 {
                result.fault = true;
                leader.signal(9);
                break;
            }
            if !ready && leader.unreaped {
                // Linux x86_64 siginfo_t is128bytes, si_pid at offset16. Use
                // u64 alignment and read only that field after waitid success.
                let mut info = [0u64; 16];
                if unsafe {
                    waitid(
                        1,
                        child as u32,
                        info.as_mut_ptr().cast(),
                        4 | 1 | 0x01000000,
                    )
                } != 0
                {
                    if errno() != EINTR {
                        result.fault = true;
                    }
                } else {
                    ready = (info[2] as u32) == child as u32;
                }
            }
            if !stopping && (ready || now >= limit || result.fault) {
                result.timeout = !ready && now >= limit;
                stopping = true;
                stop_at = now;
                if !leader.signal(15) {
                    result.fault = true;
                }
            }
            if stopping && !killed && now - stop_at >= 100 * MS {
                if !leader.signal(9) {
                    result.fault = true;
                }
                killed = true;
            }
            if stopping && now - stop_at >= 2000 * MS {
                result.fault = true;
                break;
            }
            let drain_end = if stopping { stop_at + 2000 * MS } else { limit };
            if drain(pipes.0[0][0], &mut result.out, drain_end).is_err()
                || drain(pipes.0[1][0], &mut result.err, drain_end).is_err()
            {
                result.fault = true;
            }
            if !setup_eof {
                let n = unsafe {
                    read(
                        pipes.0[2][0],
                        setup[setup_n..].as_mut_ptr().cast(),
                        setup.len() - setup_n,
                    )
                };
                if n > 0 {
                    setup_n += n as usize;
                    if setup_n == setup.len() {
                        result.fault = true;
                    }
                } else if n == 0 {
                    setup_eof = true;
                } else if ![EAGAIN, EINTR].contains(&errno()) {
                    result.fault = true;
                }
            }
            // Each positive leader reap irreversibly removes signal authority,
            // including clock/error branches at the start of all later turns.
            if killed {
                loop {
                    let mut status = 0;
                    let pid = unsafe { waitpid(-1, &mut status, 1) };
                    if pid > 0 {
                        // Drop signal authority BEFORE reading the reap clock:
                        // clock failure on this or any later turn cannot signal.
                        leader.positive_reap(pid);
                        if pid == child {
                            result.status = status;
                            result.reaped = now_ns();
                        }
                    } else {
                        if pid < 0 && errno() == ECHILD {
                            leader.no_children();
                            result.clean = true;
                            if result.status == -1 {
                                result.fault = true;
                            }
                        } else if pid < 0 && errno() != EINTR {
                            result.fault = true;
                        }
                        break;
                    }
                }
                if result.clean && result.out.eof && result.err.eof && setup_eof {
                    break;
                }
            }
            let mut fds = pipes.0.map(|pair| PollFd {
                fd: pair[0],
                events: 1,
                returned: 0,
            });
            if unsafe { poll(fds.as_mut_ptr(), 3, 5) } < 0 && errno() != EINTR {
                result.fault = true;
            }
        }
        if setup_n == 8 {
            result.child_stage = i32::from_ne_bytes(setup[..4].try_into().unwrap());
            result.child_errno = i32::from_ne_bytes(setup[4..8].try_into().unwrap());
            result.fault = true;
        } else if setup_n != 0 || !setup_eof {
            result.fault = true;
        }
        Ok(())
    })();
    if operation.is_err() {
        result.fault = true;
    }
    result.finished = now_ns();
    result
}

pub fn write_all_bounded(fd: i32, mut bytes: &[u8], outer: u64) -> Check<()> {
    let start = now_ns();
    if start == 0 {
        return Err("publication clock unavailable".into());
    }
    let end = bounded_deadline(start + 2000 * MS, outer, 0);
    while !bytes.is_empty() {
        let now = now_ns();
        if now == 0 || now >= end {
            return Err("bounded publication deadline".into());
        }
        let n = unsafe { write(fd, bytes.as_ptr().cast(), bytes.len()) };
        if n > 0 {
            bytes = &bytes[n as usize..];
        } else if n < 0 && [EINTR, EAGAIN].contains(&errno()) {
            let mut descriptor = PollFd {
                fd,
                events: 4,
                returned: 0,
            };
            if unsafe { poll(&mut descriptor, 1, 5) } < 0 && errno() != EINTR {
                return Err("publication poll failed".into());
            }
        } else {
            return Err("publication write failed".into());
        }
    }
    Ok(())
}
pub fn write_frame_once(fd: i32, bytes: &[u8]) -> Check<()> {
    if bytes.is_empty() || bytes.len() > 4096 {
        return Err("report exceeds PIPE_BUF".into());
    }
    loop {
        let n = unsafe { write(fd, bytes.as_ptr().cast(), bytes.len()) };
        if n < 0 && errno() == EINTR {
            continue;
        }
        return if n == bytes.len() as isize {
            Ok(())
        } else {
            Err("single report write incomplete".into())
        };
    }
}
pub fn save(path: &str, bytes: &[u8], outer: u64) -> Check<()> {
    let file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(path)
        .map_err(|e| format!("exclusive evidence file {path}: {e}"))?;
    write_all_bounded(file.as_raw_fd(), bytes, outer)?;
    close_file(file)
}
pub fn close_file(file: File) -> Check<()> {
    // Explicit close reports errors just as the predecessor does. Ownership
    // transfers exactly once; never retry close after an ambiguous close error.
    use std::os::fd::IntoRawFd;
    if unsafe { close(file.into_raw_fd()) } != 0 {
        return Err("owned descriptor close failed".into());
    }
    Ok(())
}

pub fn retired_at(path: &str) -> Check<bool> {
    let path = CString::new(path).map_err(|_| "NUL procfs path")?;
    // Preserve the predecessor's readdir AND closedir error checks. The
    // supported Linux x86_64 dirent has d_name at byte19. Read only its first
    // byte while this directory's readdir record remains valid, before the next
    // call. No entry pointer or directory handle escapes this function.
    unsafe {
        let directory = opendir(path.as_ptr());
        if directory.is_null() {
            return Err(format!("procfs directory open errno {}", errno()));
        }
        let mut empty = true;
        *__errno_location() = 0;
        loop {
            let entry = readdir(directory);
            if entry.is_null() {
                break;
            }
            if (*entry.cast::<u8>().add(19)).is_ascii_digit() {
                empty = false;
            }
        }
        let read_error = errno();
        let close_error = closedir(directory);
        if read_error != 0 || close_error != 0 {
            return Err(format!(
                "procfs directory read/close error {read_error}/{close_error}"
            ));
        }
        Ok(empty)
    }
}
pub fn procfs_empty() -> Check<bool> {
    retired_at("/proc/mcos0")
}

#[cfg(test)]
mod leader_ownership_tests {
    use super::LeaderOwnership;
    #[test]
    fn positive_leader_reap_forbids_signals_on_every_later_clock_or_error_branch() {
        let mut leader = LeaderOwnership::new(254);
        let mut calls = Vec::new();
        assert!(leader.signal_with(15, |pid, sig| {
            calls.push((pid, sig));
            true
        }));
        assert_eq!(calls, [(-254, 15), (254, 15)]);
        leader.positive_reap(254);
        calls.clear();
        for signal in [9, 15, 9] {
            assert!(!leader.signal_with(signal, |pid, sig| {
                calls.push((pid, sig));
                true
            }));
        }
        assert!(calls.is_empty());
    }
    #[test]
    fn descendant_reap_keeps_leader_pin_but_echild_removes_all_signal_authority() {
        let mut leader = LeaderOwnership::new(254);
        leader.positive_reap(257);
        let mut calls = Vec::new();
        assert!(leader.signal_with(9, |pid, sig| {
            calls.push((pid, sig));
            true
        }));
        assert_eq!(calls, [(-254, 9), (254, 9)]);
        leader.no_children();
        calls.clear();
        assert!(!leader.signal_with(9, |pid, sig| {
            calls.push((pid, sig));
            true
        }));
        assert!(calls.is_empty());
    }
}
