// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Project callback bodies now in Rust; genuine libc handles platform ABI.
use super::{c_int,c_long,c_ulong,c_void,McexecSyscallWaitDesc,McexecTimespec};
unsafe extern "C" {
 static mut debug:c_int;static mut stdout:*mut c_void;
 fn printf(fmt:*const u8,...)->c_int;fn fflush(p:*mut c_void)->c_int;
 fn readlinkat(fd:c_int,path:*const u8,out:*mut u8,size:usize)->isize;
 fn fstatat(fd:c_int,path:*const u8,out:*mut c_void,flags:c_int)->c_int;
 fn stat(path:*const u8,out:*mut c_void)->c_int;
 fn faccessat(fd:c_int,path:*const u8,mode:c_int,flags:c_int)->c_int;
 fn getxattr(path:*const u8,name:*const u8,value:*mut c_void,size:usize)->isize;
 fn lgetxattr(path:*const u8,name:*const u8,value:*mut c_void,size:usize)->isize;
 fn openat(fd:c_int,path:*const u8,flags:c_int,...)->c_int;
 fn open(path:*const u8,flags:c_int,...)->c_int;
 fn setfsuid(uid:u32)->c_int;fn setfsgid(gid:u32)->c_int;
 fn setresuid(r:u32,e:u32,s:u32)->c_int;fn setresgid(r:u32,e:u32,s:u32)->c_int;
 fn setreuid(r:u32,e:u32)->c_int;fn setregid(r:u32,e:u32)->c_int;
 fn setuid(uid:u32)->c_int;fn setgid(gid:u32)->c_int;
 fn clock_gettime(clock:c_int,tv:*mut McexecTimespec)->c_int;
}
unsafe fn converted(ret:c_long)->c_long {super::mcexec_errno_return_result(ret,*super::__errno_location())}
#[no_mangle]
pub unsafe extern "C" fn mcexec_path_readlinkat_bridge(dirfd:c_int,path:*const u8,buf:*mut u8,size:usize) -> c_long {
 let ret=converted(readlinkat(dirfd,path,buf,size) as c_long);
 if debug!=0 {printf(b"mcexec_path_readlinkat_bridge: readlinkat: dirfd=%d, path=%s, buf=%s, ret=%ld\n\0".as_ptr(),dirfd,path,buf,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_readlink_bridge(path:*const u8,buf:*mut u8,size:usize) -> c_long {
 let ret=converted(super::readlink(path,buf,size) as c_long);
 if debug!=0 {printf(b"mcexec_path_readlink_bridge: readlink: path=%s, buf=%s, ret=%ld\n\0".as_ptr(),path,buf,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_fstatat_bridge(dirfd:c_int,path:*const u8,statbuf:*mut c_void,flags:c_int) -> c_long {
 let ret=converted(fstatat(dirfd,path,statbuf,flags) as c_long);
 if debug!=0 {printf(b"mcexec_path_fstatat_bridge: fstatat: dirfd=%d, pathname=%s, buf=%p, flags=%x, ret=%ld\n\0".as_ptr(),dirfd,path,statbuf,flags,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_stat_bridge(path:*const u8,statbuf:*mut c_void) -> c_long {
 let ret=converted(stat(path,statbuf) as c_long);
 if debug!=0 {printf(b"mcexec_path_stat_bridge: stat: path=%s, ret=%ld\n\0".as_ptr(),path,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_faccessat_bridge(dirfd:c_int,path:*const u8,mode:c_int,flags:c_int) -> c_long {
 let ret=converted(faccessat(dirfd,path,mode,flags) as c_long);
 if debug!=0 {printf(b"mcexec_path_faccessat_bridge: faccessat: dirfd=%d, pathname=%s, mode=%d, ret=%ld\n\0".as_ptr(),dirfd,path,mode,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_access_bridge(path:*const u8,mode:c_int) -> c_long {
 let ret=converted(super::access(path,mode) as c_long);
 if debug!=0 {printf(b"mcexec_path_access_bridge: access: path=%s, ret=%ld\n\0".as_ptr(),path,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_getxattr_bridge(path:*const u8,name:*const u8,value:*mut c_void,size:usize) -> c_long {
 let ret=converted(getxattr(path,name,value,size) as c_long);
 if debug!=0 {printf(b"mcexec_path_getxattr_bridge: getxattr: path=%s, name=%s, ret=%ld\n\0".as_ptr(),path,name,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_lgetxattr_bridge(path:*const u8,name:*const u8,value:*mut c_void,size:usize) -> c_long {
 let ret=converted(lgetxattr(path,name,value,size) as c_long);
 if debug!=0 {printf(b"mcexec_path_lgetxattr_bridge: lgetxattr: path=%s, name=%s, ret=%ld\n\0".as_ptr(),path,name,ret);fflush(stdout);}
 ret
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_openat_log_bridge(dirfd:c_int,path:*const u8,tid:c_int) {
 if debug!=0 {printf(b"mcexec_path_openat_log_bridge: openat: %d, %s,tid=%d\n\0".as_ptr(),dirfd,path,tid);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_open_log_bridge(path:*const u8) {
 if debug!=0 {printf(b"mcexec_path_open_log_bridge: open: %s\n\0".as_ptr(),path);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_openat_bridge(dirfd:c_int,path:*const u8,flags:c_ulong,mode:c_ulong) -> c_long {
 converted(openat(dirfd,path,flags as c_int,mode) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_path_open_bridge(path:*const u8,flags:c_ulong,mode:c_ulong) -> c_long {
 converted(open(path,flags as c_int,mode) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_get_bridge(fd:c_int,arg:c_ulong) -> c_long {
 converted(super::ioctl(fd,0x30a0290a as c_ulong,arg) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setfsuid_bridge(uid:c_ulong) -> c_long {
 setfsuid(uid as u32) as c_long
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setfsgid_bridge(gid:c_ulong) -> c_long {
 setfsgid(gid as u32) as c_long
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setresuid_bridge(a0:c_ulong,a1:c_ulong,a2:c_ulong) -> c_long {
 converted(setresuid(a0 as u32,a1 as u32,a2 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setresgid_bridge(a0:c_ulong,a1:c_ulong,a2:c_ulong) -> c_long {
 converted(setresgid(a0 as u32,a1 as u32,a2 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setreuid_bridge(a0:c_ulong,a1:c_ulong) -> c_long {
 converted(setreuid(a0 as u32,a1 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setregid_bridge(a0:c_ulong,a1:c_ulong) -> c_long {
 converted(setregid(a0 as u32,a1 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setuid_bridge(a0:c_ulong) -> c_long {
 converted(setuid(a0 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_cred_setgid_bridge(a0:c_ulong) -> c_long {
 converted(setgid(a0 as u32) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_raw_bridge(w:*const McexecSyscallWaitDesc) -> c_long {
 let sr=&(*w).sr;super::syscall(sr.number as c_long,sr.args[0],sr.args[1],sr.args[2],sr.args[3],sr.args[4],sr.args[5])
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_start_bridge(number:c_ulong) {
 if debug!=0 {printf(b"mcexec_do_generic_syscall_start_bridge: do_generic_syscall(%ld)\n\0".as_ptr(),number);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_done_bridge(number:c_ulong,ret:c_long) {
 if debug!=0 {printf(b"mcexec_do_generic_syscall_done_bridge: do_generic_syscall(%ld):%ld (%#lx)\n\0".as_ptr(),number,ret,ret);fflush(stdout);}
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_do_generic_syscall_bridge(w:*const McexecSyscallWaitDesc) -> c_long {
 super::mcexec_do_generic_syscall_body(w)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_perf_event_open_bridge() -> c_long {
 open(b"/dev/null\0".as_ptr(),0) as c_long
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_clock_gettime_bridge(clock:c_int,tv:*mut McexecTimespec) -> c_long {
 converted(clock_gettime(clock,tv) as c_long)
}

#[no_mangle]
pub unsafe extern "C" fn mcexec_clock_gettime_log_bridge(sec:c_long,nsec:c_long) {
 if debug!=0 {printf(b"mcexec_clock_gettime_log_bridge: clock_gettime=%016ld,%09ld\n\0".as_ptr(),sec,nsec);fflush(stdout);}
}
