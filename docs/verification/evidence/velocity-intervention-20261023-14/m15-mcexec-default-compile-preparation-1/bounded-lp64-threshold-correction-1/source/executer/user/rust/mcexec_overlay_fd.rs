// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Port of selected overlay FD callbacks. Platform libc/pthread providers remain external.
use super::{McexecListHead, PATH_MAX, ENOMEM, ENOENT, c_int, c_void};
use core::ptr::{addr_of_mut, copy_nonoverlapping};

#[repr(C)]
pub struct OverlayFd {
    pub fd: c_int,
    pub getdents_fd: c_int,
    pub linux_fd: c_int,
    pub link: McexecListHead,
    pub linux_path: [u8; PATH_MAX],
    pub mck_path: [u8; PATH_MAX],
    pub pathlen: usize,
    pub mck_dirents: *mut u8,
    pub mck_dirents_size: usize,
    pub linux_dirents: *mut u8,
    pub linux_dirents_size: usize,
}
unsafe extern "C" {
    static mut overlay_fd_list: McexecListHead;
    static mut overlay_fd_lock: c_int;
    static mut debug: c_int;
    static mut stdout: *mut c_void;
    static mut stderr: *mut c_void;
    fn pthread_spin_lock(lock: *mut c_int) -> c_int;
    fn pthread_spin_unlock(lock: *mut c_int) -> c_int;
    fn fprintf(stream: *mut c_void, format: *const u8, ...) -> c_int;
    fn printf(format: *const u8, ...) -> c_int;
    fn fflush(stream: *mut c_void) -> c_int;
    fn open(path: *const u8, flags: c_int, ...) -> c_int;
}

unsafe fn lock() { pthread_spin_lock(addr_of_mut!(overlay_fd_lock)); }
unsafe fn unlock() { pthread_spin_unlock(addr_of_mut!(overlay_fd_lock)); }
unsafe fn entry(link: *mut McexecListHead) -> *mut OverlayFd {
    link.cast::<u8>().sub(core::mem::offset_of!(OverlayFd, link)).cast()
}
unsafe fn find_unlocked(fd: c_int) -> *mut OverlayFd {
    let head = addr_of_mut!(overlay_fd_list);
    let mut link = (*head).next;
    while link != head {
        let ofd = entry(link);
        if (*ofd).fd == fd { return ofd; }
        link = (*link).next;
    }
    core::ptr::null_mut()
}
// Equivalent to strncpy(dst, src, PATH_MAX), including zero padding.
unsafe fn copy_path(dst: *mut u8, src: *const u8) {
    let mut ended = false;
    for i in 0..PATH_MAX {
        let value = if ended { 0 } else { *src.add(i) };
        *dst.add(i) = value;
        ended |= value == 0;
    }
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_addfd_publish_bridge(
    fd: c_int, linux_path: *const u8, mck_path: *const u8, pathlen: usize,
) -> c_int {
    let ofd = super::malloc(core::mem::size_of::<OverlayFd>()).cast::<OverlayFd>();
    if ofd.is_null() {
        fprintf(stderr, b"overlay_addfd: out of memory\n\0".as_ptr());
        return -ENOMEM;
    }
    (*ofd).fd = fd;
    (*ofd).getdents_fd = -1;
    (*ofd).linux_fd = -1;
    (*ofd).mck_dirents = core::ptr::null_mut();
    (*ofd).mck_dirents_size = 0;
    (*ofd).linux_dirents = core::ptr::null_mut();
    (*ofd).linux_dirents_size = 0;
    (*ofd).pathlen = pathlen;
    copy_path(addr_of_mut!((*ofd).linux_path).cast(), linux_path);
    copy_path(addr_of_mut!((*ofd).mck_path).cast(), mck_path);
    lock();
    super::mcexec_overlay_list_add_body(addr_of_mut!((*ofd).link), addr_of_mut!(overlay_fd_list));
    unlock();
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_delfd_bridge(fd: c_int) {
    lock();
    let ofd = find_unlocked(fd);
    if !ofd.is_null() {
        super::mcexec_overlay_list_del_body(addr_of_mut!((*ofd).link));
        if (*ofd).getdents_fd != -1 { super::close((*ofd).getdents_fd); }
        if (*ofd).linux_fd != -1 { super::close((*ofd).linux_fd); }
        super::free((*ofd).mck_dirents);
        super::free((*ofd).linux_dirents);
        super::free(ofd.cast());
    }
    unlock();
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_find_bridge(fd: c_int) -> *mut c_void {
    lock();
    let ofd = find_unlocked(fd);
    if !ofd.is_null() && debug != 0 {
        printf(b"mcexec_overlay_getdents_find_bridge: found overlay cache entry (%s)\n\0".as_ptr(), addr_of_mut!((*ofd).linux_path).cast::<u8>());
        fflush(stdout);
    }
    unlock();
    ofd.cast()
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_hide_orig_bridge(opaque: *mut c_void) -> c_int {
    if opaque.is_null() { return 0; }
    let ofd = opaque.cast::<OverlayFd>();
    let path = addr_of_mut!((*ofd).linux_path).cast::<u8>();
    let bytes = super::cstr_bytes(path);
    (bytes.starts_with(b"/proc") && bytes.ends_with(b"task")) as c_int
}

macro_rules! accessor {
    ($name:ident, $field:ident, $type:ty) => {
        #[no_mangle]
        pub unsafe extern "C" fn $name(opaque: *mut c_void) -> $type {
            (*opaque.cast::<OverlayFd>()).$field
        }
    };
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_linux_path_bridge(opaque: *mut c_void) -> *const u8 {
    addr_of_mut!((*opaque.cast::<OverlayFd>()).linux_path).cast()
}
accessor!(mcexec_overlay_getdents_pathlen_bridge, pathlen, usize);
accessor!(mcexec_overlay_getdents_mck_dirents_bridge, mck_dirents, *mut u8);
accessor!(mcexec_overlay_getdents_mck_size_bridge, mck_dirents_size, usize);
accessor!(mcexec_overlay_getdents_linux_dirents_bridge, linux_dirents, *mut u8);
accessor!(mcexec_overlay_getdents_linux_size_bridge, linux_dirents_size, usize);

unsafe fn lazy_fd(ofd: *mut OverlayFd, linux: bool) -> c_int {
    let fd = if linux { addr_of_mut!((*ofd).linux_fd) } else { addr_of_mut!((*ofd).getdents_fd) };
    let path = if linux { addr_of_mut!((*ofd).linux_path).cast::<u8>() } else { addr_of_mut!((*ofd).mck_path).cast::<u8>() };
    if *fd == -1 {
        *fd = open(path, 0o200000); // O_RDONLY | O_DIRECTORY, Linux x86_64.
        if *fd < 0 {
            let error = *super::__errno_location();
            if error != ENOENT {
                fprintf(stderr, b"overlay_getdents: could not open %s: %d\n\0".as_ptr(), path, error);
            }
            return -error;
        }
    }
    *fd
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_mck_fd_bridge(opaque: *mut c_void) -> c_int {
    lazy_fd(opaque.cast(), false)
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_linux_fd_bridge(opaque: *mut c_void) -> c_int {
    lazy_fd(opaque.cast(), true)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_append_mck_bridge(
    opaque: *mut c_void, dirp: *const u8, len: usize, is64: c_int,
) -> c_int {
    let ofd = opaque.cast::<OverlayFd>();
    // Reference parity: no new overflow policy in this batch.
    let size = (*ofd).mck_dirents_size.wrapping_add(len);
    let newbuf = super::realloc((*ofd).mck_dirents, size);
    if newbuf.is_null() {
        fprintf(stderr, b"overlay_getdents: not enough memory (%zd)\0".as_ptr(), size);
        return -ENOMEM;
    }
    (*ofd).mck_dirents = newbuf;
    copy_nonoverlapping(dirp, newbuf.add((*ofd).mck_dirents_size), len);
    let rc = super::mcexec_dirent_rewrite_offsets_result(newbuf, (*ofd).mck_dirents_size, size, 0, is64);
    if rc < 0 { return rc; }
    (*ofd).mck_dirents_size = size;
    0
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_getdents_append_linux_bridge(
    opaque: *mut c_void, dirp: *const u8, len: usize, is64: c_int, old_ret: c_int,
) -> c_int {
    let ofd = opaque.cast::<OverlayFd>();
    let size = (*ofd).linux_dirents_size.wrapping_add(len);
    let newbuf = super::realloc((*ofd).linux_dirents, size);
    if newbuf.is_null() {
        fprintf(stderr, b"overlay_getdents: not enough memory (%zd)\0".as_ptr(), size);
        return old_ret;
    }
    (*ofd).linux_dirents = newbuf;
    copy_nonoverlapping(dirp, newbuf.add((*ofd).linux_dirents_size), len);
    (*ofd).linux_dirents_size = size;
    let rc = super::mcexec_dirent_rewrite_offsets_result(newbuf, 0, size, (*ofd).mck_dirents_size, is64);
    if rc < 0 { return rc; }
    0
}

#[cfg(mcexec_overlay_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_overlay_fixture_abi(out: *mut usize) {
    let values = [core::mem::size_of::<OverlayFd>(), core::mem::align_of::<OverlayFd>(),
        core::mem::offset_of!(OverlayFd, link), core::mem::offset_of!(OverlayFd, linux_path),
        core::mem::offset_of!(OverlayFd, mck_path), core::mem::offset_of!(OverlayFd, pathlen),
        core::mem::offset_of!(OverlayFd, mck_dirents), core::mem::offset_of!(OverlayFd, mck_dirents_size),
        core::mem::offset_of!(OverlayFd, linux_dirents), core::mem::offset_of!(OverlayFd, linux_dirents_size)];
    core::ptr::copy_nonoverlapping(values.as_ptr(), out, values.len());
}
