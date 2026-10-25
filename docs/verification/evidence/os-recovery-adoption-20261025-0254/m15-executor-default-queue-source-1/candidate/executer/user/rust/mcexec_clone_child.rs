// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Linux x86_64 glibc sem_t ABI is checked against the original C fixture.
use super::{c_int,c_long,c_ulong,c_void,ForkSyncContainer,McexecSyscallWaitDesc};
use core::ptr::{addr_of_mut,null_mut,read_volatile};
#[repr(C)]
struct FullForkSync { status:c_int, success:c_int, sem:[u64;4] }
#[repr(C)]
struct RpgtableDesc { rpgtable:usize, start:usize, len:usize }
unsafe extern "C" {
 static mut fork_sync_mutex:c_void;
 static mut ischild:c_int;
 static mut debug:c_int;
 static mut stdout:*mut c_void;
 static mut stderr:*mut c_void;
 fn pthread_mutex_lock(p:*mut c_void)->c_int;
 fn pthread_mutex_unlock(p:*mut c_void)->c_int;
 fn pthread_mutex_init(p:*mut c_void,a:*const c_void)->c_int;
 fn mmap(p:*mut c_void,n:usize,prot:c_int,flags:c_int,fd:c_int,off:c_long)->*mut c_void;
 fn munmap(p:*mut c_void,n:usize)->c_int;
 fn sem_init(p:*mut c_void,shared:c_int,value:u32)->c_int;
 fn sem_trywait(p:*mut c_void)->c_int;
 fn sem_post(p:*mut c_void)->c_int;
 fn sem_destroy(p:*mut c_void)->c_int;
 fn fork()->c_int;
 fn waitpid(pid:c_int,status:*mut c_int,options:c_int)->c_int;
 fn getppid()->c_int;
 fn sched_yield()->c_int;
 fn exit(status:c_int)->!;
 fn fprintf(p:*mut c_void,fmt:*const u8,...)->c_int;
 fn printf(fmt:*const u8,...)->c_int;
 fn fflush(p:*mut c_void)->c_int;
 fn strerror(error:c_int)->*const u8;
}
unsafe fn semaphore(fs:*mut FullForkSync)->*mut c_void { addr_of_mut!((*fs).sem).cast() }
#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_lock_bridge() { pthread_mutex_lock(addr_of_mut!(fork_sync_mutex)); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_unlock_bridge() { pthread_mutex_unlock(addr_of_mut!(fork_sync_mutex)); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_munmap_bridge(fs:*mut c_void) { munmap(fs,core::mem::size_of::<FullForkSync>()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_fork_sync_free_bridge(node:*mut c_void) { super::free(node.cast()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_alloc_fork_sync_bridge()->*mut c_void {
 let fs=mmap(null_mut(),core::mem::size_of::<FullForkSync>(),3,0x21,-1,0).cast::<FullForkSync>();
 if fs as usize==usize::MAX { return null_mut(); }
 core::ptr::write_bytes(fs.cast::<u8>(),0,core::mem::size_of::<FullForkSync>());
 sem_init(semaphore(fs),1,0);
 fs.cast()
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_alloc_container_bridge()->*mut c_void {
 let node=super::malloc(core::mem::size_of::<ForkSyncContainer>());
 if !node.is_null() { core::ptr::write_bytes(node,0,core::mem::size_of::<ForkSyncContainer>()); }
 node.cast()
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_fork_bridge()->c_int { fork() }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_fork_failed_bridge() { fprintf(stderr,b"fork(): error forking child process\n\0".as_ptr()); }

#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_child_bridge(w:*const McexecSyscallWaitDesc,sync:*mut c_void)->c_long {
 let fs=sync.cast::<FullForkSync>();
 let mut ret:c_int=1;
 ischild=1;
 super::close(super::MCEXEC_FD);
 super::MCEXEC_FD=super::mcexec_opendev_body();
 if super::MCEXEC_FD<0 {
   (*fs).status = -*super::__errno_location();
   fprintf(stderr,b"ERROR: opening %s\n\0".as_ptr(),super::mcexec_opendev_dev_bridge());
 } else {
   let mut rpt=RpgtableDesc { start:(*w).sr.args[1] as usize,len:(*w).sr.args[2] as usize,rpgtable:(*w).sr.args[3] as usize };
   if super::ioctl(super::MCEXEC_FD,0x30a0290e as c_ulong,addr_of_mut!(rpt) as c_ulong)!=0 {
     (*fs).status = -*super::__errno_location();
     fprintf(stderr,b"ERROR: creating PPD %s\n\0".as_ptr(),super::mcexec_opendev_dev_bridge());
   } else {
     super::init_sigaction();
     super::MCEXEC_THREAD_DATA=null_mut();
     if debug!=0 {
       printf(b"mcexec_clone_child_bridge: pid(%d): signals and syscall threads OK\n\0".as_ptr(),super::getpid());fflush(stdout);
     }
     ret=super::ioctl(super::MCEXEC_FD,0x30a02926 as c_ulong);
     if ret<0 { fprintf(stderr,b"Error: obtaining thread pool count\n\0".as_ptr()); }
     if ret==1 { super::MCEXEC_N_THREADS=4; }
     ret=super::init_worker_threads(super::MCEXEC_FD);
     if ret!=0 {
       fprintf(stderr,b"mcexec_clone_child_bridge: Error: creating worker threads: %s\n\0".as_ptr(),strerror(-ret));
       super::close(super::MCEXEC_FD);
       exit(1);
     }
   }
 }
 // This cleanup intentionally runs after open/PPD failures but not worker failure.
 let mut fp=super::MCEXEC_FORK_SYNC_TOP;
 while !fp.is_null() {
   let next=(*fp).next;
   if !(*fp).fs.is_null() && (*fp).fs.cast::<FullForkSync>()!=fs {
     munmap((*fp).fs.cast(),core::mem::size_of::<FullForkSync>());
   }
   super::free(fp.cast());
   fp=next;
 }
 super::MCEXEC_FORK_SYNC_TOP=null_mut();
 sem_post(semaphore(fs));
 if (*fs).status!=0 { exit(1); }
 pthread_mutex_init(addr_of_mut!(fork_sync_mutex),core::ptr::null());
 while getppid()!=1 && read_volatile(addr_of_mut!((*fs).success))==0 { sched_yield(); }
 if read_volatile(addr_of_mut!((*fs).success))==0 { exit(1); }
 sem_destroy(semaphore(fs));
 munmap(fs.cast(),core::mem::size_of::<FullForkSync>());
 super::mcexec_join_all_threads_body();
 ret as c_long
}
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_sem_trywait_bridge(fs:*mut c_void)->c_int { sem_trywait(semaphore(fs.cast())) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_waitpid_nohang_bridge(pid:c_int)->c_int { let mut status=0;waitpid(pid,addr_of_mut!(status),1) }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_sched_yield_bridge() { sched_yield(); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_child_after_fork_failed_bridge() { fprintf(stderr,b"fork(): error with child process after fork\n\0".as_ptr()); }
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_sem_destroy_bridge(fs:*mut c_void) { sem_destroy(semaphore(fs.cast())); }

#[cfg(mcexec_clone_fixture)]
#[no_mangle]
pub unsafe extern "C" fn mcexec_clone_fixture_abi(out:*mut usize) {
 let values=[core::mem::size_of::<FullForkSync>(),core::mem::align_of::<FullForkSync>(),core::mem::offset_of!(FullForkSync,sem),core::mem::size_of::<ForkSyncContainer>(),core::mem::align_of::<ForkSyncContainer>(),core::mem::offset_of!(ForkSyncContainer,next),core::mem::offset_of!(ForkSyncContainer,fs),core::mem::size_of::<RpgtableDesc>(),core::mem::offset_of!(RpgtableDesc,start),core::mem::offset_of!(RpgtableDesc,len)];
 core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
