#![allow(dead_code,static_mut_refs)]
mod abi;
use core::ffi::c_void;
use core::mem::size_of;
use core::ptr::{write,read_volatile,write_volatile,copy_nonoverlapping};
use abi::{CInt,CLong,CULong,SizeT,ProcessVm,VmRange,VmRangeNumaPolicy,PROCESS_NUMA_MASK_WORDS};
const EINVAL: CInt = 22;
const EFAULT: CInt = 14;
const PROCESS_NUMA_MASK_BITS: CULong = 256;
const MPOL_DEFAULT: CInt = 0;
const MPOL_PREFERRED: CInt = 1;
const MPOL_BIND: CInt = 2;
const MPOL_INTERLEAVE: CInt = 3;
const MPOL_F_NODE: CInt = 1 << 0;
const MPOL_F_ADDR: CInt = 1 << 1;
const MPOL_F_MEMS_ALLOWED: CInt = 1 << 2;
const GET_MEMPOLICY_LOG_CLAMPED: CInt = 1;
const GET_MEMPOLICY_LOG_INVALID_RANGE: CInt = 2;
type SyscallCopyToUserFn = unsafe extern "C" fn(CULong, *const u8, SizeT) -> CLong;
type SyscallGetMempolicyLogFn = unsafe extern "C" fn(CInt, CULong, CInt);
type SyscallRwlockFn = unsafe extern "C" fn(*mut c_void);
type SyscallLookupNodeFn = unsafe extern "C" fn(*mut ProcessVm, *mut c_void) -> CInt;
type SyscallLookupRangeFn = unsafe extern "C" fn(*mut ProcessVm, CULong, CULong) -> *mut VmRange;
type SyscallPolicySearchFn = unsafe extern "C" fn(*mut ProcessVm, CULong) -> *mut VmRangeNumaPolicy;
pub extern "C" fn mempolicy_nodemask_bits_is_clamped(maxnode: CULong) -> CInt {
    if maxnode != 0 && ((maxnode.wrapping_add(7) & !7) > PROCESS_NUMA_MASK_BITS) {
        1
    } else {
        0
    }
}
unsafe fn policy_mask_zero(mask: *mut CULong) {
    let mut word = 0usize;
    while word < PROCESS_NUMA_MASK_WORDS {
        write_volatile(mask.add(word), 0);
        word += 1;
    }
}
unsafe fn policy_mask_set(mask: *mut CULong, bit: CInt) {
    if bit < 0 || bit as CULong >= PROCESS_NUMA_MASK_BITS {
        return;
    }
    let shift = (bit as usize) % (size_of::<CULong>() * 8);
    let word = (bit as usize) / (size_of::<CULong>() * 8);
    let value = read_volatile(mask.add(word)) | ((1 as CULong) << shift);
    write_volatile(mask.add(word), value);
}
unsafe fn policy_mask_set_all_nodes(mask: *mut CULong, nr_numa_nodes: CInt) {
    policy_mask_zero(mask);
    let mut bit = 0;
    while bit < nr_numa_nodes && (bit as CULong) < PROCESS_NUMA_MASK_BITS {
        policy_mask_set(mask, bit);
        bit += 1;
    }
}
pub unsafe extern "C" fn get_mempolicy_validate(
    addr: CULong,
    flags: CInt,
    process_policy: CInt,
    maxnode: CULong,
    nr_numa_nodes: CInt,
    nodemask_bitsp: *mut CULong,
) -> CInt {
    write(nodemask_bitsp, 0);

    if ((flags & MPOL_F_ADDR) == 0 && addr != 0)
        || (flags & !(MPOL_F_ADDR | MPOL_F_NODE | MPOL_F_MEMS_ALLOWED)) != 0
        || ((flags & MPOL_F_NODE) != 0
            && (flags & MPOL_F_ADDR) == 0
            && process_policy == MPOL_INTERLEAVE)
    {
        return -EINVAL;
    }

    if (flags & MPOL_F_ADDR) != 0 && addr == 0 {
        return -EFAULT;
    }

    if maxnode != 0 {
        if maxnode < nr_numa_nodes as CULong {
            return -EINVAL;
        }

        let mut nodemask_bits = maxnode.wrapping_add(7) & !7;
        if nodemask_bits > PROCESS_NUMA_MASK_BITS {
            nodemask_bits = PROCESS_NUMA_MASK_BITS;
        }
        write(nodemask_bitsp, nodemask_bits);
    }

    0
}
pub unsafe extern "C" fn get_mempolicy_body_result(
    mode_addr: CULong,
    nodemask_addr: CULong,
    maxnode: CULong,
    addr: CULong,
    flags: CInt,
    vm: *mut ProcessVm,
    nr_numa_nodes: CInt,
    copy_to_fn: Option<SyscallCopyToUserFn>,
    lookup_node_fn: Option<SyscallLookupNodeFn>,
    read_lock_fn: Option<SyscallRwlockFn>,
    read_unlock_fn: Option<SyscallRwlockFn>,
    lookup_range_fn: Option<SyscallLookupRangeFn>,
    policy_search_fn: Option<SyscallPolicySearchFn>,
    log_fn: Option<SyscallGetMempolicyLogFn>,
) -> CLong {
    if vm.is_null() {
        return -(EFAULT as CLong);
    }

    let mut nodemask_bits: CULong = 0;
    let process_policy = (*vm).numa_mem_policy;
    let error = get_mempolicy_validate(
        addr,
        flags,
        process_policy,
        maxnode,
        nr_numa_nodes,
        &mut nodemask_bits,
    );
    if error != 0 {
        return error as CLong;
    }

    if mempolicy_nodemask_bits_is_clamped(maxnode) != 0 {
        if let Some(log) = log_fn {
            log(GET_MEMPOLICY_LOG_CLAMPED, addr, nodemask_bits as CInt);
        }
    }

    let Some(copy_to) = copy_to_fn else {
        return -(EINVAL as CLong);
    };

    if (flags & MPOL_F_NODE) != 0 && (flags & MPOL_F_ADDR) != 0 {
        let Some(lookup_node) = lookup_node_fn else {
            return -(EINVAL as CLong);
        };
        let nid = lookup_node(vm, addr as *mut c_void);
        if copy_to(
            mode_addr,
            (&nid as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        ) != 0
        {
            return -(EFAULT as CLong);
        }
        return 0;
    }

    if flags == MPOL_F_MEMS_ALLOWED {
        if nodemask_addr != 0
            && copy_to(
                nodemask_addr,
                (*vm).numa_mask.as_ptr().cast::<u8>(),
                (nodemask_bits >> 3) as SizeT,
            ) != 0
        {
            return -(EFAULT as CLong);
        }
        return 0;
    }

    let mut range_policy_snapshot: Option<CInt> = None;
    let mut range_mask_snapshot = [0 as CULong; PROCESS_NUMA_MASK_WORDS];
    if (flags & MPOL_F_ADDR) != 0 {
        let (Some(read_lock), Some(read_unlock), Some(lookup_range), Some(policy_search)) = (
            read_lock_fn,
            read_unlock_fn,
            lookup_range_fn,
            policy_search_fn,
        ) else {
            return -(EINVAL as CLong);
        };
        let lock = core::ptr::addr_of_mut!((*vm).memory_range_lock) as *mut c_void;
        read_lock(lock);
        let range = lookup_range(vm, addr, addr.wrapping_add(1));
        if range.is_null() {
            if let Some(log) = log_fn {
                log(GET_MEMPOLICY_LOG_INVALID_RANGE, addr, 0);
            }
            read_unlock(lock);
            return -(EFAULT as CLong);
        }

        let range_policy = policy_search(vm, addr);
        if !range_policy.is_null() {
            // The tree owns this policy and a writer may free it after unlock.
            // Snapshot only kernel values here; user copies remain unlocked.
            let policy = (*range_policy).numa_mem_policy;
            if nodemask_addr != 0 && policy != MPOL_DEFAULT {
                copy_nonoverlapping(
                    core::ptr::addr_of!((*range_policy).numa_mask).cast::<u8>(),
                    range_mask_snapshot.as_mut_ptr().cast::<u8>(),
                    (nodemask_bits >> 3) as SizeT,
                );
            }
            range_policy_snapshot = Some(policy);
        }
        read_unlock(lock);
    }

    let policy = match range_policy_snapshot {
        Some(policy) => policy,
        None => (*vm).numa_mem_policy,
    };

    if mode_addr != 0
        && copy_to(
            mode_addr,
            (&policy as *const CInt).cast::<u8>(),
            size_of::<CInt>(),
        ) != 0
    {
        return -(EFAULT as CLong);
    }

    if nodemask_addr != 0 && policy != MPOL_DEFAULT {
        let mask = if range_policy_snapshot.is_some() {
            range_mask_snapshot.as_ptr()
        } else {
            (*vm).numa_mask.as_ptr()
        };
        if copy_to(
            nodemask_addr,
            mask.cast::<u8>(),
            (nodemask_bits >> 3) as SizeT,
        ) != 0
        {
            return -(EFAULT as CLong);
        }
    }

    0
}

static mut FAIL_COPY:bool=false;
static mut COPIES:usize=0;
static mut BYTES:usize=0;
static mut LOG_CALLS:usize=0;
static mut LOG_EVENT:CInt=0;
static mut LOG_VALUE:CInt=0;
unsafe extern "C" fn log(event:CInt,_:CULong,value:CInt){LOG_CALLS+=1;LOG_EVENT=event;LOG_VALUE=value;}
unsafe extern "C" fn copy_to(addr:CULong,src:*const u8,len:SizeT)->CLong {
 COPIES+=1;BYTES=len;
 if FAIL_COPY{return 1;}
 if len!=0{copy_nonoverlapping(src,addr as *mut u8,len);}0
}
unsafe fn call(vm:&mut ProcessVm,nodes:CInt,max:CULong,flags:CInt,fail:bool)->(CLong,[u64;6],usize,usize){
 let mut mask=[0x137bd9958db6ff4du64,0,0,0,0,0x137bd9958db6ff4du64];
 COPIES=0;BYTES=0;FAIL_COPY=fail;LOG_CALLS=0;LOG_EVENT=0;LOG_VALUE=0;
 let rc=get_mempolicy_body_result(0,mask[1..].as_mut_ptr() as CULong,max,0,flags,vm,nodes,Some(copy_to),None,None,None,None,None,Some(log));
 assert_eq!(mask[0],0x137bd9958db6ff4d);assert_eq!(mask[5],0x137bd9958db6ff4d);
 (rc,mask,COPIES,BYTES)
}
fn main(){unsafe{
 assert_eq!(core::mem::offset_of!(ProcessVm,numa_mask),208);
 let mut count=0;
 for (nodes,expected) in [(1,[1,0,0,0]),(4,[15,0,0,0]),(65,[u64::MAX,1,0,0]),(256,[u64::MAX;4])]{
  for mode in [MPOL_DEFAULT,MPOL_PREFERRED,MPOL_BIND,MPOL_INTERLEAVE]{
   for original in [[0;4],[1,0,0,0],[u64::MAX;4]]{
    let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=mode;vm.numa_mask=original;
    let (rc,got,copies,bytes)=call(&mut vm,nodes,256,MPOL_F_MEMS_ALLOWED,false);
    assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,32);
    let wanted=if cfg!(allowed_candidate){expected}else{original};assert_eq!(&got[1..5],&wanted);
    assert_eq!(vm.numa_mem_policy,mode);assert_eq!(vm.numa_mask,original);
    count+=1;
   }
  }
 }
 // Preserve exact original equivalence vector: BIND mask0x1234/nodes4/max257.
 let mut original:ProcessVm=core::mem::zeroed();original.numa_mem_policy=MPOL_BIND;original.numa_mask=[0x1234,0,0,0];
 let (rc,mask,copies,bytes)=call(&mut original,4,257,MPOL_F_MEMS_ALLOWED,false);
 assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,32);assert_eq!(LOG_CALLS,1);assert_eq!(LOG_EVENT,1);assert_eq!(LOG_VALUE,256);
 assert_eq!(mask[1],if cfg!(allowed_candidate){0xf}else{0x1234});assert_eq!(original.numa_mask,[0x1234,0,0,0]);assert_eq!(original.numa_mem_policy,MPOL_BIND);
 let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=MPOL_DEFAULT;
 let (rc,mask,_,bytes)=call(&mut vm,1,256,MPOL_F_MEMS_ALLOWED,true);assert_eq!(rc,-14);assert_eq!(mask[1..5],[0;4]);assert_eq!(bytes,32);
 let (rc,mask,copies,_)=call(&mut vm,4,1,MPOL_F_MEMS_ALLOWED,false);assert_eq!(rc,-22);assert_eq!(copies,0);assert_eq!(mask[1..5],[0;4]);
 let (rc,mask,copies,bytes)=call(&mut vm,1,0,MPOL_F_MEMS_ALLOWED,false);assert_eq!(rc,0);assert_eq!(copies,1);assert_eq!(bytes,0);assert_eq!(mask[1..5],[0;4]);
 // Ordinary nondefault policy queries continue returning the process policy mask.
 for mode in [MPOL_PREFERRED,MPOL_BIND,MPOL_INTERLEAVE]{
  let mut vm:ProcessVm=core::mem::zeroed();vm.numa_mem_policy=mode;vm.numa_mask=[5,0,0,0];
  let mut modeout=-1;let mut mask=[0u64;4];COPIES=0;FAIL_COPY=false;
  let rc=get_mempolicy_body_result((&mut modeout as *mut CInt) as CULong,mask.as_mut_ptr() as CULong,256,0,0,&mut vm,4,Some(copy_to),None,None,None,None,None,None);
  assert_eq!(rc,0);assert_eq!(modeout,mode);assert_eq!(mask,[5,0,0,0]);assert_eq!(COPIES,2);
 }
 println!("PASS actual_body allowed_cases={} copyfault/maxnode/guards/policy_preservation=true candidate={}",count,cfg!(allowed_candidate));
}}
