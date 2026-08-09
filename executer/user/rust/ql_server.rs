#![no_std]

use core::ffi::{c_char, c_int, c_long, c_uint, c_void};
use core::mem::{size_of, MaybeUninit};
use core::ptr::null_mut;

const AF_UNIX: c_int = 1;
const SOCK_STREAM: c_int = 1;
const SIGINT: c_int = 2;
const SIGTERM: c_int = 15;
const SHUT_RDWR: c_int = 2;
const O_RDONLY: c_int = 0;
const O_WRONLY: c_int = 1;
const NALLOC: usize = 10;
const QL_BUF_MAX: usize = 256;
const QL_EXEC_END: c_int = b'E' as c_int;
const QL_RET_FINAL: c_int = b'F' as c_int;
const QL_RET_RESUME: c_int = b'R' as c_int;
const QL_COM_CONN: c_int = b'N' as c_int;
const QL_AB_END: c_int = b'A' as c_int;
const QL_MONITOR: c_int = 1;
const QL_MCEXEC_PRO: c_int = 2;
const QL_MPEXEC: c_int = 3;
const FD_SETSIZE: usize = 1024;
const NFDBITS: usize = 8 * size_of::<c_long>();

#[repr(C)]
struct SockAddr {
    sa_family: u16,
    sa_data: [c_char; 14],
}

#[repr(C)]
struct SockAddrUn {
    sun_family: u16,
    sun_path: [c_char; 108],
}

#[repr(C)]
struct FdSet {
    fds_bits: [c_long; FD_SETSIZE / NFDBITS],
}

#[repr(C)]
pub struct ClientFd {
    fd: c_int,
    client: c_int,
    name: *mut c_char,
    status: c_int,
}

#[no_mangle]
pub static mut listen_fd: c_int = -1;

#[no_mangle]
pub static mut file_path: [c_char; 1024] = [0; 1024];

static EMPTY: [u8; 1] = [0];

#[repr(C)]
struct File {
    _private: [u8; 0],
}

unsafe extern "C" {
    static mut stderr: *mut File;

    fn accept(sockfd: c_int, addr: *mut SockAddr, addrlen: *mut c_uint) -> c_int;
    fn bind(sockfd: c_int, addr: *const SockAddr, addrlen: c_uint) -> c_int;
    fn close(fd: c_int) -> c_int;
    fn exit(status: c_int) -> !;
    fn fork() -> c_int;
    fn fprintf(stream: *mut File, format: *const c_char, ...) -> c_int;
    fn free(ptr: *mut c_void);
    fn malloc(size: usize) -> *mut c_void;
    fn memcpy(dest: *mut c_void, src: *const c_void, n: usize) -> *mut c_void;
    fn mkdir(path: *const c_char, mode: c_uint) -> c_int;
    fn open(pathname: *const c_char, flags: c_int, ...) -> c_int;
    fn recv(sockfd: c_int, buf: *mut c_void, len: usize, flags: c_int) -> isize;
    fn realloc(ptr: *mut c_void, size: usize) -> *mut c_void;
    fn select(
        nfds: c_int,
        readfds: *mut FdSet,
        writefds: *mut FdSet,
        exceptfds: *mut FdSet,
        timeout: *mut c_void,
    ) -> c_int;
    fn send(sockfd: c_int, buf: *const c_void, len: usize, flags: c_int) -> isize;
    fn shutdown(sockfd: c_int, how: c_int) -> c_int;
    fn signal(signum: c_int, handler: unsafe extern "C" fn(c_int)) -> usize;
    fn socket(domain: c_int, type_: c_int, protocol: c_int) -> c_int;
    fn sprintf(s: *mut c_char, format: *const c_char, ...) -> c_int;
    fn stat(pathname: *const c_char, statbuf: *mut c_void) -> c_int;
    fn strcmp(s1: *const c_char, s2: *const c_char) -> c_int;
    fn strcpy(dest: *mut c_char, src: *const c_char) -> *mut c_char;
    fn strlen(s: *const c_char) -> usize;
    fn unlink(pathname: *const c_char) -> c_int;
    fn setsid() -> c_int;
    fn listen(sockfd: c_int, backlog: c_int) -> c_int;
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr().cast()
}

unsafe fn argv_at(argv: *mut *mut c_char, index: usize) -> *mut c_char {
    unsafe { *argv.add(index) }
}

unsafe fn fd_zero(set: *mut FdSet) {
    let mut i = 0;
    while i < (*set).fds_bits.len() {
        unsafe {
            (*set).fds_bits[i] = 0;
        }
        i += 1;
    }
}

unsafe fn fd_set(fd: c_int, set: *mut FdSet) {
    if fd < 0 || fd as usize >= FD_SETSIZE {
        return;
    }
    let word = fd as usize / NFDBITS;
    let bit = fd as usize % NFDBITS;
    unsafe {
        (*set).fds_bits[word] |= (1 as c_long) << bit;
    }
}

unsafe fn fd_clr(fd: c_int, set: *mut FdSet) {
    if fd < 0 || fd as usize >= FD_SETSIZE {
        return;
    }
    let word = fd as usize / NFDBITS;
    let bit = fd as usize % NFDBITS;
    unsafe {
        (*set).fds_bits[word] &= !((1 as c_long) << bit);
    }
}

unsafe fn fd_isset(fd: c_int, set: *const FdSet) -> bool {
    if fd < 0 || fd as usize >= FD_SETSIZE {
        return false;
    }
    let word = fd as usize / NFDBITS;
    let bit = fd as usize % NFDBITS;
    unsafe { ((*set).fds_bits[word] & ((1 as c_long) << bit)) != 0 }
}

unsafe fn recompute_maxfd(fd_list: *mut ClientFd, fd_size: usize, listen: c_int) -> c_int {
    let mut maxfd = listen;
    let mut i = 0usize;
    while i < fd_size {
        let fd = unsafe { (*fd_list.add(i)).fd };
        if fd > maxfd {
            maxfd = fd;
        }
        i += 1;
    }
    maxfd
}

unsafe fn empty_name() -> *mut c_char {
    EMPTY.as_ptr() as *mut c_char
}

unsafe fn free_name_if_needed(name: *mut c_char) {
    if !name.is_null() && unsafe { *name } != 0 {
        unsafe {
            free(name.cast());
        }
    }
}

unsafe fn close_entry(fd_list: *mut ClientFd, idx: usize, allset: *mut FdSet) {
    let entry = unsafe { fd_list.add(idx) };
    let fd = unsafe { (*entry).fd };
    unsafe {
        fd_clr(fd, allset);
        close(fd);
        free_name_if_needed((*entry).name);
        (*entry).fd = -1;
        (*entry).name = empty_name();
    }
}

unsafe fn init_entry(entry: *mut ClientFd) {
    unsafe {
        (*entry).fd = -1;
        (*entry).client = 0;
        (*entry).name = empty_name();
        (*entry).status = 0;
    }
}

unsafe fn find_slot(fd_list: *mut ClientFd, fd_size: usize) -> usize {
    let mut i = 0usize;
    while i < fd_size {
        if unsafe { (*fd_list.add(i)).fd } == -1 {
            return i;
        }
        i += 1;
    }
    fd_size
}

unsafe fn hex_value(ch: u8) -> Option<c_int> {
    match ch {
        b'0'..=b'9' => Some((ch - b'0') as c_int),
        b'a'..=b'f' => Some((ch - b'a' + 10) as c_int),
        b'A'..=b'F' => Some((ch - b'A' + 10) as c_int),
        _ => None,
    }
}

unsafe fn parse_size(buf: *const u8) -> c_int {
    let mut idx = 1usize;
    while unsafe { *buf.add(idx) } == b' ' {
        idx += 1;
    }
    let mut value = 0;
    while let Some(v) = unsafe { hex_value(*buf.add(idx)) } {
        value = (value << 4) + v;
        idx += 1;
    }
    value
}

#[no_mangle]
pub unsafe extern "C" fn check_ql_server(
    path: *mut c_char,
    file: *mut c_char,
    filep: *mut c_char,
) -> c_int {
    let mut st = [0u8; 256];
    unsafe {
        sprintf(filep, cstr(b"%s/%s\0"), path, file);
    }

    if unsafe { stat(filep, st.as_mut_ptr().cast()) } == 0 {
        unsafe {
            fprintf(
                stderr,
                cstr(b"socket file exests. %s\n\0"),
                filep as *const c_char,
            );
        }
        return 0;
    }

    if unsafe { stat(path, st.as_mut_ptr().cast()) } == 0 {
        unsafe {
            fprintf(stderr, cstr(b"dir(file) exests. %s %d\n\0"), path, 0);
        }
        return 1;
    }

    if unsafe { mkdir(path, 0o777) } == 0 {
        unsafe {
            fprintf(stderr, cstr(b"dir create. %s %d\n\0"), path, -1);
        }
        return 1;
    }

    unsafe {
        fprintf(stderr, cstr(b"mkdir error. %s %d\n\0"), path, -1);
    }
    0
}

#[no_mangle]
pub unsafe extern "C" fn terminate(rc: c_int) {
    if unsafe { listen_fd } >= 0 {
        unsafe {
            shutdown(listen_fd, SHUT_RDWR);
            close(listen_fd);
            unlink((&raw const file_path).cast::<c_char>());
        }
    }
    unsafe {
        exit(rc);
    }
}

#[no_mangle]
pub unsafe extern "C" fn s_fd_list(
    p_name: *mut c_char,
    client_type: c_int,
    fd_list: *mut ClientFd,
    fd_size: c_int,
) -> c_int {
    let mut i = 0;
    while i < fd_size {
        let entry = unsafe { fd_list.add(i as usize) };
        if unsafe {
            (*entry).client == client_type
                && !(*entry).name.is_null()
                && strcmp((*entry).name, p_name) == 0
                && (*entry).fd != -1
        } {
            break;
        }
        i += 1;
    }
    i
}

#[no_mangle]
pub unsafe extern "C" fn ql_recv(fd: c_int, buf: *mut *mut c_char) -> c_int {
    let mut l_buf = [0u8; QL_BUF_MAX];
    let rc = unsafe { recv(fd, l_buf.as_mut_ptr().cast(), QL_BUF_MAX, 0) };
    if rc <= 0 {
        return rc as c_int;
    }

    let ret = l_buf[0] as c_int;
    let size = unsafe { parse_size(l_buf.as_ptr()) } as usize;
    if size > 0 && !buf.is_null() {
        let out = unsafe { malloc(size + 1) }.cast::<u8>();
        if out.is_null() {
            return -1;
        }
        unsafe {
            memcpy(out.cast(), l_buf.as_ptr().add(7).cast(), size);
            *out.add(size) = 0;
            *buf = out.cast();
        }
    }
    ret
}

#[no_mangle]
pub unsafe extern "C" fn ql_send(fd: c_int, command: c_int, buf: *mut c_char) -> c_int {
    let size = if buf.is_null() {
        0
    } else {
        unsafe { strlen(buf) }
    };
    let alloc_len = size + 8;
    let lbuf = unsafe { malloc(alloc_len) }.cast::<c_char>();
    if lbuf.is_null() {
        return -1;
    }

    unsafe {
        if buf.is_null() {
            sprintf(lbuf, cstr(b"%c 0000\0"), command);
        } else {
            sprintf(lbuf, cstr(b"%c %04x %s\0"), command, size as c_uint, buf);
        }
    }
    let rc = unsafe { send(fd, lbuf.cast(), strlen(lbuf), 0) } as c_int;
    unsafe {
        free(lbuf.cast());
    }
    rc
}

unsafe fn handle_close(
    fd_list: *mut ClientFd,
    idx: usize,
    fd_size: usize,
    allset: *mut FdSet,
) -> c_int {
    unsafe {
        close_entry(fd_list, idx, allset);
        recompute_maxfd(fd_list, fd_size, listen_fd)
    }
}

unsafe fn handle_match_close(
    fd_list: *mut ClientFd,
    idx: usize,
    fd_size: usize,
    allset: *mut FdSet,
) -> c_int {
    unsafe { handle_close(fd_list, idx, fd_size, allset) }
}

#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut c_char) -> c_int {
    let mut i: usize;
    let mut j: usize;
    let mut fd: c_int;
    let mut rc: c_int = 0;
    let mut len: c_uint;
    let mut maxfd: c_int;
    let mut fd_size = NALLOC;
    let mut unix_addr = MaybeUninit::<SockAddrUn>::uninit();
    let mut rset = MaybeUninit::<FdSet>::uninit();
    let mut allset = MaybeUninit::<FdSet>::uninit();
    let null_buff = empty_name();

    if argc < 3 {
        unsafe {
            fprintf(stderr, cstr(b" few args \n\0"));
            exit(-1);
        }
    }

    i = 0;
    while i < 4096 {
        unsafe {
            close(i as c_int);
        }
        i += 1;
    }
    unsafe {
        open(cstr(b"/dev/null\0"), O_RDONLY);
        open(cstr(b"/dev/null\0"), O_WRONLY);
        open(cstr(b"/dev/null\0"), O_WRONLY);
    }

    if unsafe {
        check_ql_server(
            argv_at(argv, 1),
            argv_at(argv, 2),
            (&raw mut file_path).cast::<c_char>(),
        )
    } == 0
    {
        unsafe {
            fprintf(stderr, cstr(b"ql_server already exists.\n\0"));
            exit(-1);
        }
    }

    unsafe {
        signal(SIGINT, terminate);
        signal(SIGTERM, terminate);
        listen_fd = socket(AF_UNIX, SOCK_STREAM, 0);
    }
    if unsafe { listen_fd } < 0 {
        unsafe {
            fprintf(stderr, cstr(b"listen error.\n\0"));
            terminate(rc);
        }
    }

    unsafe {
        (*unix_addr.as_mut_ptr()).sun_family = AF_UNIX as u16;
        strcpy(
            (*unix_addr.as_mut_ptr()).sun_path.as_mut_ptr(),
            (&raw const file_path).cast::<c_char>(),
        );
        len = (size_of::<u16>() + strlen((*unix_addr.as_ptr()).sun_path.as_ptr()) + 1) as c_uint;
        rc = bind(listen_fd, unix_addr.as_ptr().cast::<SockAddr>(), len);
    }
    if rc < 0 {
        unsafe {
            terminate(rc);
        }
    }

    unsafe {
        if fork() != 0 {
            exit(0);
        }
        if fork() != 0 {
            exit(0);
        }
        setsid();
    }

    rc = unsafe { listen(listen_fd, 5) };
    if rc < 0 {
        unsafe {
            terminate(rc);
        }
    }

    unsafe {
        fd_zero(allset.as_mut_ptr());
        fd_set(listen_fd, allset.as_mut_ptr());
    }
    maxfd = unsafe { listen_fd };

    let mut fd_list = unsafe { malloc(size_of::<ClientFd>() * fd_size) }.cast::<ClientFd>();
    if fd_list.is_null() {
        unsafe {
            terminate(-1);
        }
    }
    i = 0;
    while i < fd_size {
        unsafe {
            init_entry(fd_list.add(i));
        }
        i += 1;
    }

    loop {
        unsafe {
            memcpy(
                rset.as_mut_ptr().cast(),
                allset.as_ptr().cast(),
                size_of::<FdSet>(),
            );
        }
        rc = unsafe {
            select(
                maxfd + 1,
                rset.as_mut_ptr(),
                null_mut(),
                null_mut(),
                null_mut(),
            )
        };
        if rc == -1 {
            unsafe {
                terminate(rc);
            }
        }

        if unsafe { fd_isset(listen_fd, rset.as_ptr()) } {
            len = size_of::<SockAddrUn>() as c_uint;
            fd = unsafe {
                accept(
                    listen_fd,
                    unix_addr.as_mut_ptr().cast::<SockAddr>(),
                    &mut len,
                )
            };
            if fd < 0 {
                unsafe {
                    terminate(fd);
                }
            }

            i = unsafe { find_slot(fd_list, fd_size) };
            if i >= fd_size {
                let new_size = fd_size + NALLOC;
                let new_list = unsafe {
                    realloc(fd_list.cast(), size_of::<ClientFd>() * new_size).cast::<ClientFd>()
                };
                if new_list.is_null() {
                    unsafe {
                        close(fd);
                        terminate(-1);
                    }
                }
                fd_list = new_list;
                j = fd_size;
                while j < new_size {
                    unsafe {
                        init_entry(fd_list.add(j));
                    }
                    j += 1;
                }
                fd_size = new_size;
            }
            unsafe {
                (*fd_list.add(i)).fd = fd;
                fd_set(fd, allset.as_mut_ptr());
            }
            if fd > maxfd {
                maxfd = fd;
            }
        }

        i = 0;
        while i < fd_size {
            if unsafe { (*fd_list.add(i)).fd } == -1 {
                i += 1;
                continue;
            }
            fd = unsafe { (*fd_list.add(i)).fd };
            if !unsafe { fd_isset(fd, rset.as_ptr()) } {
                i += 1;
                continue;
            }

            let mut buf: *mut c_char = null_mut();
            rc = unsafe { ql_recv(fd, &mut buf) };
            if rc < 0 {
                unsafe {
                    terminate(rc);
                }
            }
            if rc == 0 {
                maxfd = unsafe { handle_close(fd_list, i, fd_size, allset.as_mut_ptr()) };
                if maxfd == -1 {
                    unsafe {
                        terminate(rc);
                    }
                }
                i += 1;
                continue;
            }

            if rc == QL_EXEC_END {
                unsafe {
                    (*fd_list.add(i)).client = QL_MCEXEC_PRO;
                    (*fd_list.add(i)).name = buf;
                    (*fd_list.add(i)).status = QL_EXEC_END;
                }
                let s_indx =
                    unsafe { s_fd_list(buf, QL_MPEXEC, fd_list, fd_size as c_int) } as usize;
                if s_indx < fd_size {
                    unsafe {
                        ql_send((*fd_list.add(s_indx)).fd, QL_EXEC_END, null_mut());
                        maxfd = handle_match_close(fd_list, s_indx, fd_size, allset.as_mut_ptr());
                        if maxfd == -1 {
                            terminate(0);
                        }
                    }
                }
            } else if rc == QL_RET_RESUME {
                unsafe {
                    (*fd_list.add(i)).client = QL_MPEXEC;
                    (*fd_list.add(i)).name = buf;
                    (*fd_list.add(i)).status = QL_RET_RESUME;
                }
                let s_indx =
                    unsafe { s_fd_list(buf, QL_MCEXEC_PRO, fd_list, fd_size as c_int) } as usize;
                if s_indx < fd_size && unsafe { (*fd_list.add(s_indx)).status } == QL_EXEC_END {
                    unsafe {
                        ql_send((*fd_list.add(s_indx)).fd, QL_RET_RESUME, null_mut());
                        (*fd_list.add(s_indx)).status = QL_RET_RESUME;
                        maxfd = handle_match_close(fd_list, s_indx, fd_size, allset.as_mut_ptr());
                        if maxfd == -1 {
                            terminate(0);
                        }
                    }
                } else {
                    unsafe {
                        ql_send((*fd_list.add(i)).fd, QL_AB_END, null_mut());
                        maxfd = handle_match_close(fd_list, i, fd_size, allset.as_mut_ptr());
                        if maxfd == -1 {
                            terminate(0);
                        }
                    }
                }
            } else if rc == QL_COM_CONN {
                unsafe {
                    (*fd_list.add(i)).client = QL_MPEXEC;
                    (*fd_list.add(i)).name = buf;
                    (*fd_list.add(i)).status = QL_COM_CONN;
                }
                let s_indx =
                    unsafe { s_fd_list(buf, QL_MCEXEC_PRO, fd_list, fd_size as c_int) } as usize;
                if s_indx < fd_size {
                    unsafe {
                        ql_send((*fd_list.add(i)).fd, QL_EXEC_END, null_mut());
                        maxfd = handle_match_close(fd_list, i, fd_size, allset.as_mut_ptr());
                    }
                }
            } else if rc == QL_RET_FINAL {
                unsafe {
                    (*fd_list.add(i)).client = QL_MONITOR;
                    (*fd_list.add(i)).name = buf;
                    (*fd_list.add(i)).status = QL_RET_FINAL;
                }
                let mut s_indx =
                    unsafe { s_fd_list(buf, QL_MPEXEC, fd_list, fd_size as c_int) } as usize;
                if s_indx < fd_size {
                    unsafe {
                        ql_send((*fd_list.add(s_indx)).fd, QL_AB_END, null_mut());
                        let _ = handle_match_close(fd_list, s_indx, fd_size, allset.as_mut_ptr());
                    }
                }
                s_indx =
                    unsafe { s_fd_list(buf, QL_MCEXEC_PRO, fd_list, fd_size as c_int) } as usize;
                if s_indx < fd_size {
                    unsafe {
                        let _ = handle_match_close(fd_list, s_indx, fd_size, allset.as_mut_ptr());
                    }
                }
                unsafe {
                    maxfd = handle_match_close(fd_list, i, fd_size, allset.as_mut_ptr());
                    if maxfd == -1 {
                        terminate(0);
                    }
                }
            } else if !buf.is_null() {
                unsafe {
                    free_name_if_needed(buf);
                }
            }

            let _ = null_buff;
            i += 1;
        }
    }
}
