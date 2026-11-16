//! M14-06-05 native consumer. Run only on the admitted matching x86_64 guest.
//! The parent creates exactly one child with fork; no exec or external target.
use std::ffi::{c_int, c_long, c_void};
use std::io;
use std::ptr::{null, null_mut};

#[repr(C)]
struct Iovec { base: *mut c_void, len: usize }
unsafe extern "C" {
    fn fork() -> c_int;
    fn pipe(p: *mut c_int) -> c_int;
    fn read(fd: c_int, p: *mut c_void, n: usize) -> isize;
    fn write(fd: c_int, p: *const c_void, n: usize) -> isize;
    fn close(fd: c_int) -> c_int;
    fn waitpid(pid: c_int, status: *mut c_int, options: c_int) -> c_int;
    fn waitid(kind: c_int, id: u32, info: *mut c_void, options: c_int) -> c_int;
    fn signal(signum: c_int, handler: usize) -> usize;
    fn mmap(addr: *mut c_void, n: usize, prot: c_int, flags: c_int, fd: c_int, off: i64) -> *mut c_void;
    fn mprotect(addr: *mut c_void, n: usize, prot: c_int) -> c_int;
    fn munmap(addr: *mut c_void, n: usize) -> c_int;
    fn sysconf(name: c_int) -> c_long;
    fn syscall(n: c_long, ...) -> c_long;
    fn _exit(status: c_int) -> !;
}
const READV: c_long = 310;
const WRITEV: c_long = 311;
const MOVE_PAGES: c_long = 279;
const EFAULT: i32 = 14;
const EINVAL: i32 = 22;
const ESRCH: i32 = 3;
const EINTR: i32 = 4;
const SC_PAGESIZE: c_int = 30; // Linux/glibc _SC_PAGESIZE, not a kernel ABI.
const PROT_READ: c_int = 1;
const PROT_WRITE: c_int = 2;
const MAP_PRIVATE: c_int = 2;
const MAP_ANONYMOUS: c_int = 0x20;

fn error(s: &str) -> String { format!("{s}: {}", io::Error::last_os_error()) }
fn errno() -> i32 { io::Error::last_os_error().raw_os_error().unwrap_or(-1) }
unsafe fn close_fd(fd: &mut c_int) {
    if *fd >= 0 { let old = *fd; *fd = -1; let _ = unsafe { close(old) }; }
}
unsafe fn transfer(fd: c_int, ptr: *mut u8, len: usize, writing: bool) -> bool {
    let mut done = 0;
    while done < len {
        let n = if writing { unsafe { write(fd, ptr.add(done).cast(), len - done) } }
                else { unsafe { read(fd, ptr.add(done).cast(), len - done) } };
        if n < 0 && errno() == EINTR { continue; }
        if n <= 0 { return false; }
        done += n as usize;
    }
    true
}
unsafe fn map(n: usize) -> *mut u8 {
    unsafe { mmap(null_mut(), n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0).cast() }
}
fn failed_map(p: *mut u8) -> bool { p as isize == -1 }

// Raw libc calls only after fork; no stdio, allocation, or destructor in child.
unsafe fn child(mut command: c_int, mut result: c_int, page: usize) -> ! {
    let p = unsafe { map(page * 2) };
    if failed_map(p) { unsafe { _exit(10) } }
    unsafe {
        std::ptr::copy_nonoverlapping(b"abcdefgh".as_ptr(), p, 8);
        std::ptr::copy_nonoverlapping(b"IJKLMNOP".as_ptr(), p.add(64), 8);
        if mprotect(p.add(page).cast(), page, 0) != 0 { _exit(11); }
        let mut address = p as usize;
        if !transfer(result, (&mut address as *mut usize).cast(), std::mem::size_of::<usize>(), true) { _exit(12); }
        let mut cmd = 0u8;
        if !transfer(command, &mut cmd, 1, false) || cmd != b'V' { _exit(13); }
        let good = std::slice::from_raw_parts(p.add(16), 8) == b"12345678";
        let mut response = if good { b'Y' } else { b'N' };
        if !transfer(result, &mut response, 1, true) { _exit(14); }
        if !transfer(command, &mut cmd, 1, false) || cmd != b'X' { _exit(15); }
        if munmap(p.cast(), page * 2) != 0 { _exit(16); }
        close_fd(&mut command);
        close_fd(&mut result);
        _exit(if good { 0 } else { 17 });
    }
}
struct Child { pid: c_int, command: c_int, result: c_int, reaped: bool }
impl Child {
    fn wait(&mut self) -> Result<(), String> {
        if self.reaped { return Err("child already reaped".into()); }
        let mut status = 0;
        loop {
            let rc = unsafe { waitpid(self.pid, &mut status, 0) };
            if rc == self.pid { self.reaped = true; break; }
            if rc < 0 && errno() == EINTR { continue; }
            return Err(error("waitpid"));
        }
        if status != 0 { return Err(format!("child wait status {status:#x}")); }
        Ok(())
    }
}
impl Drop for Child {
    fn drop(&mut self) {
        unsafe { close_fd(&mut self.command); close_fd(&mut self.result); }
        if !self.reaped { let _ = self.wait(); }
    }
}
struct Mapping { p: *mut u8, len: usize }
impl Drop for Mapping { fn drop(&mut self) { unsafe { let _ = munmap(self.p.cast(), self.len); } } }

fn call_vm(number: c_long, pid: c_int, local: &[Iovec], remote: &[Iovec], flags: usize) -> (c_long, i32) {
    let rc = unsafe { syscall(number, pid, local.as_ptr(), local.len(), remote.as_ptr(), remote.len(), flags) };
    (rc, if rc == -1 { errno() } else { 0 })
}
fn check(test: &str, yes: bool) -> Result<(), String> {
    if !yes { return Err(format!("FAIL {test}")); }
    println!("PASS {test}"); Ok(())
}
fn run() -> Result<(), String> {
    let page = unsafe { sysconf(SC_PAGESIZE) };
    if page < 4096 || page > 1_048_576 || !(page as usize).is_power_of_two() { return Err(format!("invalid page size {page}")); }
    let page = page as usize;
    // Ignore SIGPIPE so an early child failure reaches the owned wait path.
    if unsafe { signal(13, 1) } == usize::MAX { return Err(error("signal SIGPIPE")); }
    let mut cmd = [-1; 2]; let mut res = [-1; 2];
    if unsafe { pipe(cmd.as_mut_ptr()) } != 0 { return Err(error("command pipe")); }
    if unsafe { pipe(res.as_mut_ptr()) } != 0 {
        unsafe { close_fd(&mut cmd[0]); close_fd(&mut cmd[1]); }
        return Err(error("result pipe"));
    }
    let pid = unsafe { fork() };
    if pid < 0 {
        let e = error("fork");
        unsafe { close_fd(&mut cmd[0]); close_fd(&mut cmd[1]); close_fd(&mut res[0]); close_fd(&mut res[1]); }
        return Err(e);
    }
    if pid == 0 {
        unsafe { close_fd(&mut cmd[1]); close_fd(&mut res[0]); child(cmd[0], res[1], page); }
    }
    unsafe { close_fd(&mut cmd[0]); close_fd(&mut res[1]); }
    let mut child = Child { pid, command: cmd[1], result: res[0], reaped: false };
    let mut remote_base = 0usize;
    if !unsafe { transfer(child.result, (&mut remote_base as *mut usize).cast(), std::mem::size_of::<usize>(), false) } {
        return Err(error("read child mapping address"));
    }
    if remote_base == 0 { return Err("child returned null mapping".into()); }
    let mut local = [0u8; 16];
    let mut lv = [Iovec { base: local.as_mut_ptr().cast(), len: 16 }];
    let rv = [Iovec { base: remote_base as *mut c_void, len: 8 }, Iovec { base: (remote_base + 64) as *mut c_void, len: 8 }];
    let got = call_vm(READV, pid, &lv, &rv, 0);
    check("read-discontiguous-vectors", got == (16, 0) && &local == b"abcdefghIJKLMNOP")?;
    let mut payload = *b"12345678";
    let input = [Iovec { base: payload.as_mut_ptr().cast(), len: 8 }];
    let dest = [Iovec { base: (remote_base + 16) as *mut c_void, len: 8 }];
    check("write-target", call_vm(WRITEV, pid, &input, &dest, 0) == (8, 0))?;
    let mut v = b'V';
    if !unsafe { transfer(child.command, &mut v, 1, true) && transfer(child.result, &mut v, 1, false) } { return Err(error("child verify exchange")); }
    check("child-observes-write", v == b'Y')?;
    local.fill(0x5a); lv[0].len = 8;
    let denied = [Iovec { base: remote_base as *mut c_void, len: 4 }, Iovec { base: (remote_base + page) as *mut c_void, len: 4 }];
    let got = call_vm(READV, pid, &lv, &denied, 0);
    check("later-denied-vector", got == (-1, EFAULT) && &local[..4] == b"abcd" && local[4..8] == [0x5a; 4])?;
    check("invalid-flags", call_vm(READV, pid, &lv, &denied, 1) == (-1, EINVAL))?;
    let p = unsafe { map(page) };
    if failed_map(p) { return Err(error("local mmap")); }
    let map = Mapping { p, len: page };
    unsafe { p.write_volatile(7) };
    let pages = [p as *const c_void]; let mut status = [-999i32];
    let rc = unsafe { syscall(MOVE_PAGES, 0i32, 1usize, pages.as_ptr(), null::<c_int>(), status.as_mut_ptr(), 0i32) };
    check("move-pages-query", rc == 0 && status[0] >= 0)?;
    println!("move-pages first-node={}", status[0]); status[0] = -999;
    let rc = unsafe { syscall(MOVE_PAGES, 0i32, 1usize, pages.as_ptr(), null::<c_int>(), status.as_mut_ptr(), 0i32) };
    check("move-pages-repeat", rc == 0 && status[0] >= 0)?;
    let rc = unsafe { syscall(MOVE_PAGES, pid, 1usize, pages.as_ptr(), null::<c_int>(), status.as_mut_ptr(), 0i32) };
    check("move-pages-foreign-pid-policy", rc == -1 && errno() == EINVAL)?;
    drop(map);
    let mut x = b'X';
    if !unsafe { transfer(child.command, &mut x, 1, true) } { return Err(error("send child exit")); }
    unsafe { close_fd(&mut child.command); }
    let mut byte = 0u8;
    // EOF observes child descriptor closure while it remains our unreaped child,
    // preventing PID reuse before this last target-lifetime check.
    let eof = loop { let n = unsafe { read(child.result, (&mut byte as *mut u8).cast(), 1) }; if n < 0 && errno() == EINTR { continue; } break n; };
    check("child-exit-eof", eof == 0)?;
    // WNOWAIT observes the actual exit without relinquishing the PID.
    let mut info = [0u64; 16];
    loop {
        let rc = unsafe { waitid(1, pid as u32, info.as_mut_ptr().cast(), 4 | 0x01000000) };
        if rc == 0 { break; }
        if errno() != EINTR { return Err(error("waitid WNOWAIT")); }
    }
    check("exited-target", call_vm(READV, pid, &lv, &denied, 0) == (-1, ESRCH))?;
    unsafe { close_fd(&mut child.result); }
    child.wait()?;
    println!("PASS child-reaped"); Ok(())
}
fn main() { if let Err(e) = run() { eprintln!("{e}"); std::process::exit(1); } }
