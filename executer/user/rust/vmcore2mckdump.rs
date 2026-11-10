// Derived from vmcore2mckdump.in COPYRIGHT FUJITSU LIMITED 2017-2018.
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private source candidate. Dump production stays in existing Rust converter.
// Intended behavior (requires reviewed converter-ack.patch): clean conversation,
// clean crash exit, exact fresh-file acknowledgment, and atomic publication.
use std::ffi::{CString, OsStr, OsString};
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::os::fd::{AsRawFd, FromRawFd};
use std::os::unix::ffi::{OsStrExt, OsStringExt};
use std::os::unix::fs::{MetadataExt, OpenOptionsExt};
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, ExitStatus, Stdio};
use std::mem::MaybeUninit;
use std::time::{Duration, Instant};
use std::os::raw::{c_int, c_long, c_short, c_uint, c_ulong, c_void};
#[cfg(not(all(target_arch="x86_64", target_os="linux", target_pointer_width="64")))]
compile_error!("vmcore session custody requires the qualified Linux/x86_64 LP64 ABI");
const PREFIX: &str = env!("VMCORE_INSTALLDIR");
const ARCH: &str = env!("VMCORE_ARCH");
const CRASH: &str = env!("VMCORE_CRASH");
const TIMEOUT_MS: &str = env!("VMCORE_PROMPT_TIMEOUT_MS");
const PROMPT: &[u8] = b"crash>";
const ACK: &[u8] = b"MCKERNEL_LDUMP2MCDUMP_SUCCESS ";
#[repr(C)]
struct PollFd { fd: c_int, events: c_short, revents: c_short }
#[link(name = "util")]
extern "C" { fn openpty(master: *mut c_int, slave: *mut c_int, name: *mut u8, term: *const c_void, win: *const c_void) -> c_int; }
extern "C" {
    fn setsid() -> c_int;
    fn ioctl(fd: c_int, request: c_ulong, ...) -> c_int;
    fn poll(fds: *mut PollFd, count: c_ulong, timeout: c_int) -> c_int;
    fn kill(pid: c_int, signal: c_int) -> c_int;
    fn syscall(number: c_long, ...) -> c_long;
    fn prctl(option: c_int, ...) -> c_int;
    fn waitid(which: c_uint, id: c_uint, info: *mut WaitInfo, options: c_int) -> c_int;
    fn waitpid(pid: c_int, status: *mut c_int, options: c_int) -> c_int;
}
fn literal_path(path: &OsStr) -> bool {
    !path.is_empty() && path.as_bytes().iter().all(|b| b.is_ascii_alphanumeric() || b"/._:+,@%=-".contains(b))
}
fn uname_release() -> OsString {
    // Original command substitution runs before any CLI validation and ignores
    // uname's exit status. Keep stderr inherited and strip trailing LFs only.
    match Command::new("uname").arg("-r").stderr(Stdio::inherit()).output() {
        Ok(mut output) => {
            while output.stdout.last() == Some(&b'\n') { output.stdout.pop(); }
            OsString::from_vec(output.stdout)
        }
        Err(error) => { eprintln!("uname: {error}"); OsString::new() }
    }
}
struct Staging { path: PathBuf, identity: (u64, u64), committed: bool }
impl Staging {
    fn create(output: &Path) -> io::Result<Self> {
        let parent = output.parent().filter(|p| !p.as_os_str().is_empty()).unwrap_or(Path::new("."));
        for index in 0..100u32 {
            let path = parent.join(format!(".vmcore2mckdump-{}-{index}.tmp", std::process::id()));
            match OpenOptions::new().create_new(true).write(true).mode(0o666).open(&path) {
                Ok(file) => { let m = file.metadata()?; return Ok(Self { path, identity: (m.dev(), m.ino()), committed: false }); }
                Err(e) if e.kind() == io::ErrorKind::AlreadyExists => continue,
                Err(e) => return Err(e),
            }
        }
        Err(io::Error::new(io::ErrorKind::AlreadyExists, "no unused output staging name"))
    }
    fn publish(&mut self, output: &Path) -> io::Result<()> {
        let metadata = fs::symlink_metadata(&self.path)?;
        if !metadata.is_file() || metadata.len() == 0 || (metadata.dev(), metadata.ino()) != self.identity {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "fresh acknowledged output is absent, empty, or changed identity"));
        }
        // Preserve an existing regular output's permission bits on success.
        // Existing bytes remain untouched until this atomic path publication.
        if let Ok(old) = fs::metadata(output) { if old.is_file() { fs::set_permissions(&self.path, old.permissions())?; } }
        fs::rename(&self.path, output)?;
        self.committed = true;
        Ok(())
    }
}
impl Drop for Staging {
    fn drop(&mut self) {
        if !self.committed {
            if let Ok(m) = fs::symlink_metadata(&self.path) {
                if m.is_file() && (m.dev(), m.ino()) == self.identity {
                    eprintln!("vmcore2mckdump: retained incomplete output {}", self.path.display());
                }
            }
        }
    }
}
// Linux/x86_64 UAPI and glibc declarations are bound by the nonshipped ABI
// witness. waitid writes opaque siginfo_t storage; no siginfo fields are read.
const SYS_PIDFD_OPEN: c_long = 434;
const SYS_PIDFD_SEND_SIGNAL: c_long = 424;
const PR_SET_CHILD_SUBREAPER: c_int = 36;
const PR_GET_CHILD_SUBREAPER: c_int = 37;
const P_ALL: c_uint = 0;
const P_PIDFD: c_uint = 3;
const WNOHANG: c_int = 1;
const WEXITED: c_int = 4;
const WNOWAIT: c_int = 0x01000000;
const SIGKILL: c_int = 9;
const ESRCH: c_int = 3;
const ECHILD: c_int = 10;
const POLLIN: c_short = 0x001;
const POLLERR: c_short = 0x008;
const POLLNVAL: c_short = 0x020;
#[repr(C, align(8))]
struct WaitInfo { bytes: [u8; 128] }
fn observe_child(which: c_uint, id: c_uint, options: c_int) -> io::Result<()> {
    let mut info = MaybeUninit::<WaitInfo>::uninit();
    if unsafe { waitid(which, id, info.as_mut_ptr(), options) } < 0 {
        return Err(io::Error::last_os_error());
    }
    Ok(())
}
struct ChildScope { previous: c_int, restored: bool }
impl ChildScope {
    fn acquire() -> io::Result<Self> {
        // This standalone, single-threaded command has already waited for uname.
        // Refuse preexisting children rather than consuming another owner's wait.
        match observe_child(P_ALL, 0, WEXITED | WNOWAIT | WNOHANG) {
            Err(e) if e.raw_os_error() == Some(ECHILD) => {},
            Err(e) => return Err(e),
            Ok(()) => return Err(io::Error::new(io::ErrorKind::Other, "preexisting child outside crash session")),
        }
        let mut previous = 0;
        if unsafe { prctl(PR_GET_CHILD_SUBREAPER, &mut previous as *mut c_int, 0 as c_ulong, 0 as c_ulong, 0 as c_ulong) } < 0 {
            return Err(io::Error::last_os_error());
        }
        if previous != 0 && previous != 1 {
            return Err(io::Error::new(io::ErrorKind::InvalidData, "unknown subreaper setting"));
        }
        if previous == 0 && unsafe { prctl(PR_SET_CHILD_SUBREAPER, 1 as c_ulong, 0 as c_ulong, 0 as c_ulong, 0 as c_ulong) } < 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(Self { previous, restored: previous == 1 })
    }
    fn restore(&mut self) -> io::Result<()> {
        if !self.restored {
            if unsafe { prctl(PR_SET_CHILD_SUBREAPER, self.previous as c_ulong, 0 as c_ulong, 0 as c_ulong, 0 as c_ulong) } < 0 {
                return Err(io::Error::last_os_error());
            }
            self.restored = true;
        }
        Ok(())
    }
}
impl Drop for ChildScope {
    fn drop(&mut self) {
        if let Err(e) = self.restore() { eprintln!("vmcore2mckdump: subreaper restoration unproved: {e}"); }
    }
}
struct Session {
    child: Child, master: File, pending: Vec<u8>, line: Vec<u8>, wanted_ack: Vec<u8>, acknowledged: bool, eof: bool,
    pidfd: Option<File>, pidfd_verified: bool, leader_reaped: bool, retirement_started: bool,
    cleanup_timeout: Duration, scope: ChildScope,
}
impl Session {
    fn spawn(vmlinux: &OsStr, infile: &OsStr, outfile: &OsStr, staging: &Path, timeout: Duration) -> io::Result<Self> {
        let scope = ChildScope::acquire()?;
        let mut master = -1; let mut slave = -1;
        if unsafe { openpty(&mut master, &mut slave, std::ptr::null_mut(), std::ptr::null(), std::ptr::null()) } != 0 { return Err(io::Error::last_os_error()); }
        let master = unsafe { File::from_raw_fd(master) };
        let slave = unsafe { File::from_raw_fd(slave) };
        let mut command = Command::new(CRASH);
        command.arg(vmlinux).arg(infile)
            .env("VMLINUX", vmlinux).env("INSTALLDIR", PREFIX).env("INFILE", infile).env("OUTFILE", outfile)
            .stdin(Stdio::from(slave.try_clone()?)).stdout(Stdio::from(slave.try_clone()?)).stderr(Stdio::from(slave));
        unsafe {
            command.pre_exec(|| {
                if setsid() < 0 { return Err(io::Error::last_os_error()); }
                if ioctl(0, 0x540eu64 as c_ulong, 0 as c_int) < 0 { return Err(io::Error::last_os_error()); }
                Ok(())
            });
        }
        let child = command.spawn()?;
        let mut wanted_ack = ACK.to_vec(); wanted_ack.extend_from_slice(staging.as_os_str().as_bytes());
        let mut session = Self {
            child, master, pending: Vec::new(), line: Vec::new(), wanted_ack, acknowledged: false, eof: false,
            pidfd: None, pidfd_verified: false, leader_reaped: false, retirement_started: false,
            cleanup_timeout: timeout, scope,
        };
        let raw = unsafe { syscall(SYS_PIDFD_OPEN, session.child.id() as c_int, 0 as c_uint) };
        if raw < 0 { return Err(io::Error::last_os_error()); }
        session.pidfd = Some(unsafe { File::from_raw_fd(raw as c_int) });
        let fd = session.pidfd.as_ref().unwrap().as_raw_fd();
        // A pidfd opened after spawn is not used for signalling until waitid
        // proves that it still refers to this command's own waitable child.
        observe_child(P_PIDFD, fd as c_uint, WEXITED | WNOWAIT | WNOHANG)?;
        session.pidfd_verified = true;
        Ok(session)
    }
    fn receive(&mut self, deadline: Instant) -> io::Result<()> {
        if self.eof { return Err(io::Error::new(io::ErrorKind::UnexpectedEof, "crash PTY closed")); }
        let left = deadline.saturating_duration_since(Instant::now());
        if left.is_zero() { return Err(io::Error::new(io::ErrorKind::TimedOut, "crash prompt deadline")); }
        let mut descriptor = PollFd { fd: self.master.as_raw_fd(), events: 1, revents: 0 };
        let ready = unsafe { poll(&mut descriptor, 1, left.as_millis().min(c_int::MAX as u128).max(1) as c_int) };
        if ready < 0 {
            let e = io::Error::last_os_error(); if e.kind() == io::ErrorKind::Interrupted { return Ok(()); } return Err(e);
        }
        if ready == 0 { return Err(io::Error::new(io::ErrorKind::TimedOut, "crash prompt deadline")); }
        let mut buffer = [0u8; 8192];
        let n = match self.master.read(&mut buffer) {
            Ok(0) => { self.eof = true; return Ok(()); }
            Ok(n) => n,
            Err(e) if e.raw_os_error() == Some(5) => { self.eof = true; return Ok(()); }
            Err(e) if e.kind() == io::ErrorKind::Interrupted => return Ok(()),
            Err(e) => return Err(e),
        };
        io::stdout().write_all(&buffer[..n])?; io::stdout().flush()?;
        self.pending.extend_from_slice(&buffer[..n]);
        for b in &buffer[..n] {
            if *b == b'\n' {
                while self.line.last() == Some(&b'\r') { self.line.pop(); }
                if self.line == self.wanted_ack { self.acknowledged = true; }
                self.line.clear();
            } else if self.line.len() <= self.wanted_ack.len() + 1 { self.line.push(*b); }
        }
        Ok(())
    }
    fn prompt(&mut self, timeout: Duration) -> io::Result<()> {
        let deadline = Instant::now() + timeout;
        loop {
            if let Some(i) = self.pending.windows(PROMPT.len()).position(|p| p == PROMPT) { self.pending.drain(..i + PROMPT.len()); return Ok(()); }
            if self.pending.len() > PROMPT.len() - 1 { let n = self.pending.len() - (PROMPT.len() - 1); self.pending.drain(..n); }
            self.receive(deadline)?;
        }
    }
    fn send(&mut self, bytes: &[u8]) -> io::Result<()> { self.master.write_all(bytes) }
    fn leader_exited(&self) -> io::Result<bool> {
        if !self.pidfd_verified {
            return Err(io::Error::new(io::ErrorKind::Other, "crash pidfd ownership unproved"));
        }
        let mut fd = PollFd { fd: self.pidfd.as_ref().unwrap().as_raw_fd(), events: POLLIN, revents: 0 };
        let ready = unsafe { poll(&mut fd, 1, 0) };
        if ready < 0 { return Err(io::Error::last_os_error()); }
        if fd.revents & (POLLERR | POLLNVAL) != 0 {
            return Err(io::Error::new(io::ErrorKind::Other, "crash pidfd poll failed"));
        }
        Ok(fd.revents & POLLIN != 0)
    }
    fn retire(&mut self, deadline: Instant) -> io::Result<ExitStatus> {
        self.retirement_started = true;
        if !self.pidfd_verified || self.leader_reaped {
            return Err(io::Error::new(io::ErrorKind::Other, "crash retirement identity unproved"));
        }
        let fd = self.pidfd.as_ref().unwrap().as_raw_fd();
        if !self.leader_exited()? {
            if unsafe { syscall(SYS_PIDFD_SEND_SIGNAL, fd, SIGKILL, std::ptr::null::<c_void>(), 0 as c_uint) } < 0 {
                let e = io::Error::last_os_error();
                if e.raw_os_error() != Some(ESRCH) { return Err(e); }
            }
            while !self.leader_exited()? {
                if Instant::now() >= deadline { return Err(io::Error::new(io::ErrorKind::TimedOut, "crash retirement deadline")); }
                std::thread::sleep(Duration::from_millis(1));
            }
        }
        // WNOWAIT is the positive proof that the original leader remains owned
        // and unreaped. Only now can its numeric private PGID be signalled.
        observe_child(P_PIDFD, fd as c_uint, WEXITED | WNOWAIT)?;
        if unsafe { kill(-(self.child.id() as c_int), SIGKILL) } < 0 {
            let e = io::Error::last_os_error();
            if e.raw_os_error() != Some(ESRCH) { return Err(e); }
        }
        let status = self.child.wait()?;
        self.leader_reaped = true;
        loop {
            let mut child_status = 0;
            let joined = unsafe { waitpid(-1, &mut child_status, WNOHANG) };
            if joined > 0 { continue; }
            if joined < 0 {
                let e = io::Error::last_os_error();
                if e.raw_os_error() == Some(ECHILD) { self.scope.restore()?; return Ok(status); }
                if e.kind() != io::ErrorKind::Interrupted { return Err(e); }
            }
            if Instant::now() >= deadline { return Err(io::Error::new(io::ErrorKind::TimedOut, "crash descendants retirement deadline")); }
            std::thread::sleep(Duration::from_millis(1));
        }
    }
    fn finish(&mut self, timeout: Duration) -> io::Result<()> {
        let deadline = Instant::now() + timeout;
        loop {
            if self.leader_exited()? {
                // Drain the final protocol bytes without consuming leader
                // ownership. The existing configured deadline bounds the drain.
                while !self.eof {
                    let short = (Instant::now() + Duration::from_millis(20)).min(deadline);
                    match self.receive(short) { Ok(()) => {}, Err(e) if e.kind() == io::ErrorKind::TimedOut => break, Err(e) => return Err(e) }
                }
                let status = self.retire(deadline)?;
                if !status.success() { return Err(io::Error::new(io::ErrorKind::Other, format!("crash failed: {status}"))); }
                return Ok(());
            }
            if self.eof {
                if Instant::now() >= deadline { return Err(io::Error::new(io::ErrorKind::TimedOut, "crash exit deadline")); }
                std::thread::sleep(Duration::from_millis(1));
                continue;
            }
            self.receive(deadline)?;
            self.pending.clear();
        }
    }
}
impl Drop for Session {
    fn drop(&mut self) {
        // One retirement attempt. Never signal a numeric group after leader
        // reap or after any identity/wait failure; the outer owner retains it.
        if !self.retirement_started {
            if let Err(e) = self.retire(Instant::now() + self.cleanup_timeout) {
                eprintln!("vmcore2mckdump: session retirement unproved: {e}");
            }
        }
    }
}
fn convert(vmlinux: &OsStr, infile: &OsStr, outfile: &OsStr) -> io::Result<()> {
    if !literal_path(infile) || !literal_path(outfile) || !literal_path(OsStr::new(PREFIX)) {
        return Err(io::Error::new(io::ErrorKind::InvalidInput, "review nonliteral path quoting against crash before enabling it"));
    }
    let arch = if ARCH == "x86_64" { "x86" } else { ARCH };
    let timeout = Duration::from_millis(TIMEOUT_MS.parse::<u64>().map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "invalid configured timeout"))?);
    if timeout.is_zero() { return Err(io::Error::new(io::ErrorKind::InvalidInput, "zero configured timeout")); }
    let mut staging = Staging::create(Path::new(outfile))?;
    // CString check is independent of shell/Tcl syntax; no interpreter executes.
    let _ = CString::new(staging.path.as_os_str().as_bytes()).map_err(|_| io::Error::new(io::ErrorKind::InvalidInput, "NUL output path"))?;
    let mut session = Session::spawn(vmlinux, infile, outfile, &staging.path, timeout)?;
    let mut spawn = b"spawn ".to_vec(); spawn.extend_from_slice(CRASH.as_bytes()); spawn.push(b' '); spawn.extend_from_slice(vmlinux.as_bytes()); spawn.push(b' '); spawn.extend_from_slice(infile.as_bytes()); spawn.extend_from_slice(b"\r\n");
    io::stdout().write_all(&spawn)?; io::stdout().flush()?;
    let commands = [format!("mod -s ihk_smp_{arch} {PREFIX}/kmod/ihk-smp-{arch}.ko\n"),
        format!("extend {PREFIX}/lib/ldump2mcdump.so\n"),
        format!("ldump2mcdump 0 -o {}\n", staging.path.display()),
        format!("extend -u {PREFIX}/lib/ldump2mcdump.so\n"), "quit\n".to_string()];
    for command in commands { session.prompt(timeout)?; session.send(command.as_bytes())?; }
    session.finish(timeout)?;
    if !session.acknowledged { return Err(io::Error::new(io::ErrorKind::InvalidData, "no matched converter close acknowledgment")); }
    staging.publish(Path::new(outfile))
}
fn run() -> c_int {
    let release = uname_release();
    let mut vmlinux = OsString::from("/usr/lib/debug/lib/modules/"); vmlinux.push(release); vmlinux.push("/vmlinux");
    let args: Vec<OsString> = std::env::args_os().collect();
    let infile = args.get(1).map(OsString::as_os_str).unwrap_or(OsStr::new(""));
    let outfile = args.get(2).map(OsString::as_os_str).unwrap_or(OsStr::new(""));
    if infile.is_empty() || outfile.is_empty() || args.get(3).is_some_and(|x| !x.is_empty()) {
        eprintln!("usage: vmcore2mckdump <vmcore> <mckdump>"); return 1;
    }
    if !Path::new(infile).is_file() {
        let mut stderr = io::stderr(); let _ = stderr.write_all(infile.as_bytes()); let _ = stderr.write_all(b": not found\n"); return 1;
    }
    if ARCH.is_empty() { println!("ARCH_NAME is empty."); return 1; }
    match convert(&vmlinux, infile, outfile) {
        Ok(()) => { println!("mcdump: {} is extracted.", outfile.to_string_lossy()); 0 }
        Err(error) => { eprintln!("vmcore2mckdump: {error}"); println!("Error: failed to extract mcdump."); 1 }
    }
}
fn main() { std::process::exit(run()); }
