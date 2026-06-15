#![no_std]

use core::ffi::{c_char, c_int, c_uint, c_void};
use core::mem::{self, MaybeUninit};

const AF_UNIX: c_int = 1;
const SOCK_STREAM: c_int = 1;
const SIGINT: c_int = 2;
const SIGTERM: c_int = 15;
const SHUT_RDWR: c_int = 2;
const BUF_MAX: usize = 256;
const QL_AB_END: c_char = b'A' as c_char;

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

#[no_mangle]
pub static mut fd: c_int = -1;

unsafe extern "C" {
    fn close(fd: c_int) -> c_int;
    fn connect(sockfd: c_int, addr: *const SockAddr, addrlen: c_uint) -> c_int;
    fn exit(status: c_int) -> !;
    fn recv(sockfd: c_int, buf: *mut c_void, len: usize, flags: c_int) -> isize;
    fn send(sockfd: c_int, buf: *const c_void, len: usize, flags: c_int) -> isize;
    fn shutdown(sockfd: c_int, how: c_int) -> c_int;
    fn signal(signum: c_int, handler: unsafe extern "C" fn(c_int)) -> usize;
    fn socket(domain: c_int, type_: c_int, protocol: c_int) -> c_int;
    fn sprintf(s: *mut c_char, format: *const c_char, ...) -> c_int;
    fn strcmp(s1: *const c_char, s2: *const c_char) -> c_int;
    fn strcpy(dst: *mut c_char, src: *const c_char) -> *mut c_char;
    fn strlen(s: *const c_char) -> usize;
}

fn cstr(bytes: &'static [u8]) -> *const c_char {
    bytes.as_ptr() as *const c_char
}

unsafe fn argv_at(argv: *mut *mut c_char, index: usize) -> *mut c_char {
    unsafe { *argv.add(index) }
}

unsafe fn terminate_process(rc: c_int) -> ! {
    if unsafe { fd } >= 0 {
        unsafe {
            shutdown(fd, SHUT_RDWR);
            close(fd);
        }
    }
    unsafe { exit(rc) }
}

unsafe extern "C" fn terminate_signal(rc: c_int) {
    unsafe {
        terminate_process(rc);
    }
}

#[no_mangle]
pub unsafe extern "C" fn main(argc: c_int, argv: *mut *mut c_char) -> c_int {
    let mut rc: c_int = -1;
    let mut unix_addr = MaybeUninit::<SockAddrUn>::uninit();
    let mut buf = MaybeUninit::<[c_char; BUF_MAX]>::uninit();

    unsafe {
        signal(SIGINT, terminate_signal);
        signal(SIGTERM, terminate_signal);
    }

    if argc < 5 {
        return rc;
    }

    unsafe {
        fd = socket(AF_UNIX, SOCK_STREAM, 0);
    }
    if unsafe { fd } < 0 {
        unsafe {
            terminate_process(rc);
        }
    }

    unsafe {
        (*unix_addr.as_mut_ptr()).sun_family = AF_UNIX as u16;
        strcpy(
            (*unix_addr.as_mut_ptr()).sun_path.as_mut_ptr(),
            argv_at(argv, 4),
        );

        let len = mem::size_of::<u16>() + strlen((*unix_addr.as_ptr()).sun_path.as_ptr()) + 1;
        rc = connect(fd, unix_addr.as_ptr() as *const SockAddr, len as c_uint);
    }
    if rc < 0 {
        unsafe {
            terminate_process(rc);
        }
    }

    unsafe {
        let command = argv_at(argv, 1);
        if *command != 0 {
            let payload = argv_at(argv, 3);
            sprintf(
                buf.as_mut_ptr() as *mut c_char,
                cstr(b"%s %04x %s\0"),
                command,
                strlen(payload) as c_uint,
                payload,
            );
            rc = send(
                fd,
                buf.as_ptr() as *const c_void,
                strlen(buf.as_ptr() as *const c_char) + 1,
                0,
            ) as c_int;
            if rc < 0 {
                terminate_process(rc);
            }
        }
    }

    unsafe {
        if strcmp(argv_at(argv, 2), cstr(b"-n\0")) != 0 {
            rc = recv(fd, buf.as_mut_ptr() as *mut c_void, BUF_MAX, 0) as c_int;
            if rc < 0 {
                terminate_process(rc);
            }
            let first = *(buf.as_ptr() as *const c_char);
            if first == *argv_at(argv, 2) {
                terminate_process(0);
            }
            if first == QL_AB_END {
                terminate_process(-2);
            }
        }
    }

    unsafe {
        terminate_process(0);
    }
}
