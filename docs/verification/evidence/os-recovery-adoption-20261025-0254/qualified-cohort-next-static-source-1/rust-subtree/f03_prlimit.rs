// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// New private complete prlimit body. The retained four-initialized/six-read
// forwarding HOLD is preserved; production selection remains OFF until review.
use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of_mut, copy_nonoverlapping, write_bytes};
use crate::abi::{CInt, CLong, CULong, McsRwlockLock, Process, ProcessHash, RLimit,
                 SyscallRequest, PROCESS_HASH_SIZE};
const EINVAL: CInt=22;
const EFAULT: CInt=14;
const ESRCH: CInt=3;
const SYS_PRLIMIT64: CInt=302;

pub type CopyFrom=unsafe extern "C" fn(*mut u8,CULong,usize)->CLong;
pub type CopyTo=unsafe extern "C" fn(CULong,*const u8,usize)->CLong;
pub type Forward4=unsafe extern "C" fn(CInt,CInt,CULong,CULong)->CLong;
pub type NoirqLock=unsafe extern "C" fn(*mut McsRwlockLock,*mut c_void);
pub type RequestCall=unsafe extern "C" fn(*mut SyscallRequest,CInt)->CLong;
pub type GenericForward=unsafe extern "C" fn(*mut SyscallRequest,CInt,CULong,CULong,CULong,CULong,CULong,CULong,CInt,Option<RequestCall>)->CLong;
#[repr(C)]
pub struct PrlimitProviders {
    pub copy_from:CopyFrom,
    pub copy_to:CopyTo,
    pub forward4:Forward4,
    pub current_pid:unsafe extern "C" fn()->CInt,
    pub irq_save:unsafe extern "C" fn()->CULong,
    pub irq_restore:unsafe extern "C" fn(CULong),
    pub hash:extern "C" fn(CInt)->CInt,
    pub reader_lock:NoirqLock,
    pub reader_unlock:NoirqLock,
    pub writer_lock:NoirqLock,
    pub writer_unlock:NoirqLock,
}
// Actual selected noirq node storage is 64-byte sized/aligned. The real-header
// ABI witness must match this local opaque storage before production selection.
#[repr(C,align(64))]
struct PrlimitNode { bytes:[MaybeUninit<u8>;64] }

/// # Safety
/// phash retains the original sampled resource-set hash for this synchronous
/// call. Providers retain the actual current-thread/usercopy/IRQ/noirq-lock
/// contracts. The hash-reader remains held through update lock, usercopy and
/// update; no process reference is invented or released by this body.
#[no_mangle]
pub unsafe extern "C" fn f03_prlimit_body_result(
    mut pid:CInt,resource:CInt,new_addr:CULong,old_addr:CULong,
    phash:*mut ProcessHash,p:*const PrlimitProviders,
)->CInt {
    let Some(p)=p.as_ref() else { return -EINVAL; };
    let mut ret=crate::rlimit_helpers::prlimit_validate_resource(resource);
    if ret!=0 { return ret; }
    let mut new_limit=MaybeUninit::<RLimit>::uninit();
    if new_addr!=0 {
        if (p.copy_from)(new_limit.as_mut_ptr().cast(),new_addr,size_of::<RLimit>())!=0 { return -EFAULT; }
        ret=crate::rlimit_helpers::prlimit_validate_new_limit((*new_limit.as_ptr()).rlim_cur,(*new_limit.as_ptr()).rlim_max);
        if ret!=0 { return ret; }
        if crate::rlimit_helpers::prlimit_linux_update_needed(resource)!=0 {
            // The C original narrows long into int before testing its sign.
            ret=(p.forward4)(pid,resource,new_addr,old_addr) as CInt;
            if ret<0 { return ret; }
        }
    }
    let mcresource=crate::rlimit_helpers::prlimit_to_mckernel_resource(resource);
    if mcresource<0 { return (p.forward4)(pid,resource,new_addr,old_addr) as CInt; }
    if pid==0 { pid=(p.current_pid)(); }
    let irqstate=(p.irq_save)();
    let hash=(p.hash)(pid);
    // The accepted process lookup already rejects invalid signed hash indexes.
    // Define the same ESRCH result here instead of forming an out-of-bounds
    // Rust pointer for the old C negative-pid undefined domain.
    if hash<0 || hash as usize>=PROCESS_HASH_SIZE {
        (p.irq_restore)(irqstate);return -ESRCH;
    }
    let mut exist=MaybeUninit::<PrlimitNode>::uninit();
    let mut update=MaybeUninit::<PrlimitNode>::uninit();
    let hash_lock=addr_of_mut!((*phash).lock[hash as usize]);
    (p.reader_lock)(hash_lock,exist.as_mut_ptr().cast());
    let head=addr_of_mut!((*phash).list[hash as usize]);
    let mut cursor=(*head).next;
    let mut proc=core::ptr::null_mut::<Process>();
    while cursor!=head {
        let candidate=cursor.cast::<u8>().sub(offset_of!(Process,hash_list)).cast::<Process>();
        if (*candidate).pid==pid { proc=candidate;break; }
        cursor=(*cursor).next;
    }
    if proc.is_null() {
        (p.reader_unlock)(hash_lock,exist.as_mut_ptr().cast());
        (p.irq_restore)(irqstate);return -ESRCH;
    }
    let update_lock=addr_of_mut!((*proc).update_lock);
    if new_addr!=0 { (p.writer_lock)(update_lock,update.as_mut_ptr().cast()); }
    else { (p.reader_lock)(update_lock,update.as_mut_ptr().cast()); }
    let limit=addr_of_mut!((*proc).rlimit).cast::<RLimit>().add(mcresource as usize);
    ret=0;
    if old_addr!=0 && (p.copy_to)(old_addr,limit.cast(),size_of::<RLimit>())!=0 { ret=-EFAULT; }
    if ret==0 && new_addr!=0 {
        copy_nonoverlapping(new_limit.as_ptr().cast::<u8>(),limit.cast::<u8>(),size_of::<RLimit>());
    }
    if new_addr!=0 { (p.writer_unlock)(update_lock,update.as_mut_ptr().cast()); }
    else { (p.reader_unlock)(update_lock,update.as_mut_ptr().cast()); }
    (p.reader_unlock)(hash_lock,exist.as_mut_ptr().cast());
    (p.irq_restore)(irqstate);
    ret
}

/// # Safety
/// Caller supplies private writable naturally aligned SyscallRequest storage
/// through the synchronous call. Explicit initialized request construction
/// repairs the separately retained partial-context HOLD; it is not old parity
/// evidence for unspecified args4/5. The four named syscall values are exact.
#[no_mangle]
pub unsafe extern "C" fn f03_prlimit_forward_request_result(
    request:*mut SyscallRequest,pid:CInt,resource:CInt,new_addr:CULong,old_addr:CULong,
    cpu:CInt,build:GenericForward,call:RequestCall,
)->CLong {
    if request.is_null() { return -(EINVAL as CLong); }
    write_bytes(request.cast::<u8>(),0,size_of::<SyscallRequest>());
    build(request,SYS_PRLIMIT64,pid as CULong,resource as CULong,new_addr,old_addr,0,0,cpu,Some(call))
}

#[cfg(not(f03_prlimit_fixture))]
mod production {
    use super::*;
    unsafe extern "C" {
        fn cpu_disable_interrupt_save()->CULong;
        fn cpu_restore_interrupt(flags:CULong);
        fn ihk_mc_get_processor_id()->CInt;
        fn do_syscall(request:*mut SyscallRequest,cpu:CInt)->CLong;
    }
    unsafe extern "C" fn current_pid()->CInt {
        let thread=(*crate::cls::get_this_cpu_local_var()).current;
        (*(*thread).proc).pid
    }
    unsafe extern "C" fn forward4(pid:CInt,resource:CInt,new_addr:CULong,old_addr:CULong)->CLong {
        let mut request=MaybeUninit::<SyscallRequest>::uninit();
        f03_prlimit_forward_request_result(request.as_mut_ptr(),pid,resource,new_addr,old_addr,
            ihk_mc_get_processor_id(),crate::syscall_policy::syscall_generic_forwarding_body_result,do_syscall)
    }
    unsafe extern "C" fn reader_lock(lock:*mut McsRwlockLock,node:*mut c_void) {
        crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(lock.cast(),node);
    }
    unsafe extern "C" fn reader_unlock(lock:*mut McsRwlockLock,node:*mut c_void) {
        crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(lock.cast(),node);
    }
    unsafe extern "C" fn writer_lock(lock:*mut McsRwlockLock,node:*mut c_void) {
        crate::lock_helpers::__mcs_rwlock_writer_lock_noirq(lock.cast(),node);
    }
    unsafe extern "C" fn writer_unlock(lock:*mut McsRwlockLock,node:*mut c_void) {
        crate::lock_helpers::__mcs_rwlock_writer_unlock_noirq(lock.cast(),node);
    }
    static PROVIDERS:PrlimitProviders=PrlimitProviders {
        copy_from:crate::syscall_policy::syscall_copy_from_user_bridge,
        copy_to:crate::syscall_policy::syscall_copy_to_user_bridge,forward4,current_pid,
        irq_save:cpu_disable_interrupt_save,irq_restore:cpu_restore_interrupt,
        hash:crate::process_helpers::process_hash,reader_lock,reader_unlock,writer_lock,writer_unlock,
    };
    /// # Safety
    /// Original current-CPU/resource-set/process/usercopy lifetimes apply.
    #[no_mangle]
    pub unsafe extern "C" fn syscall_do_prlimit64_bridge(pid:CInt,resource:CInt,new_addr:CULong,old_addr:CULong)->CLong {
        let cpu=crate::cls::get_this_cpu_local_var();
        let phash=(*(*cpu).resource_set).process_hash;
        f03_prlimit_body_result(pid,resource,new_addr,old_addr,phash,&PROVIDERS) as CLong
    }
}

#[cfg(f03_prlimit_fixture)]
#[no_mangle]
pub static F03_PRLIMIT_ABI:[CULong;44]=[
    (size_of::<RLimit>()) as CULong,
    (core::mem::align_of::<RLimit>()) as CULong,
    (offset_of!(RLimit,rlim_cur)) as CULong,
    (offset_of!(RLimit,rlim_max)) as CULong,
    (size_of::<Process>()) as CULong,
    (offset_of!(Process,hash_list)) as CULong,
    (offset_of!(Process,update_lock)) as CULong,
    (offset_of!(Process,pid)) as CULong,
    (offset_of!(Process,rlimit)) as CULong,
    (size_of::<ProcessHash>()) as CULong,
    (core::mem::align_of::<ProcessHash>()) as CULong,
    (offset_of!(ProcessHash,list)) as CULong,
    (offset_of!(ProcessHash,lock)) as CULong,
    (size_of::<McsRwlockLock>()) as CULong,
    (size_of::<crate::abi::AbiListHead>()) as CULong,
    (PROCESS_HASH_SIZE) as CULong,
    (size_of::<PrlimitNode>()) as CULong,
    (core::mem::align_of::<PrlimitNode>()) as CULong,
    (size_of::<SyscallRequest>()) as CULong,
    (core::mem::align_of::<SyscallRequest>()) as CULong,
    (offset_of!(SyscallRequest,rtid)) as CULong,
    (offset_of!(SyscallRequest,ttid)) as CULong,
    (offset_of!(SyscallRequest,valid)) as CULong,
    (offset_of!(SyscallRequest,number)) as CULong,
    (offset_of!(SyscallRequest,args)) as CULong,
    (size_of::<PrlimitProviders>()) as CULong,
    (core::mem::align_of::<PrlimitProviders>()) as CULong,
    (offset_of!(PrlimitProviders,copy_from)) as CULong,
    (offset_of!(PrlimitProviders,copy_to)) as CULong,
    (offset_of!(PrlimitProviders,forward4)) as CULong,
    (offset_of!(PrlimitProviders,current_pid)) as CULong,
    (offset_of!(PrlimitProviders,irq_save)) as CULong,
    (offset_of!(PrlimitProviders,irq_restore)) as CULong,
    (offset_of!(PrlimitProviders,hash)) as CULong,
    (offset_of!(PrlimitProviders,reader_lock)) as CULong,
    (offset_of!(PrlimitProviders,reader_unlock)) as CULong,
    (offset_of!(PrlimitProviders,writer_lock)) as CULong,
    (offset_of!(PrlimitProviders,writer_unlock)) as CULong,
    (offset_of!(crate::abi::CpuLocalVar,current)) as CULong,
    (offset_of!(crate::abi::CpuLocalVar,resource_set)) as CULong,
    (offset_of!(crate::abi::ResourceSet,process_hash)) as CULong,
    (offset_of!(crate::abi::Thread,proc)) as CULong,
    (core::mem::align_of::<crate::abi::CpuLocalVar>()) as CULong,
    (SYS_PRLIMIT64 as usize) as CULong
];
