// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ptr::{addr_of,addr_of_mut,null_mut,read,read_volatile};
use crate::abi::{CInt,CULong,SizeT,Process,ProcessVm};
use crate::debug::{Ddebug,kprintf};
use crate::syscall_policy::ArchVdso;

// The existing F06 producer supplies the original C filename. Retain exactly
// the CURRENT116 site identity, including its null fmt and initial flags0.
#[used]
#[link_section="__verbose"]
#[export_name="mckernel_f06_vdso_map_debug"]
pub static mut VDSO_MAP_DEBUG:Ddebug=Ddebug {
    file:concat!(env!("MCKERNEL_F06_RT_SIGRETURN_ORIGIN"),"\0").as_ptr().cast(),
    func:b"arch_vdso_map_log_bridge\0".as_ptr().cast(),
    fmt:core::ptr::null(),
    line_flags:3084,
};

unsafe extern "C" {
    fn arch_vdso_state_bridge(vdso:*mut *mut ArchVdso,size:*mut *mut SizeT,offset:*mut *mut isize);
}

/// Preserve the original event, argument, debug-gate and diagnostic behavior.
///
/// # Safety
/// For the mapped event only, nonnull vm and vm.proc must retain their original
/// valid, aligned ProcessVm/Process lifetimes and caller-owned exclusion. Other
/// events never access vm. The existing state bridge supplies the same stable
/// image-lifetime offset address; its read retains the original plain-load
/// semantics. No reference, allocation, hold/release, lock or error is added.
#[no_mangle]
pub unsafe extern "C" fn arch_vdso_map_log_bridge(
    event:CInt,error:CInt,vm:*mut ProcessVm,container:CULong,vdso_address:CULong,
    vdso_end:CULong,container_size:CULong,pages:CInt,
) {
    match event {
        1=>{
            // SAFETY: qualified32B/align8 descriptor; original eight-bit flags
            // reside at byte27. Keep its original updates/exclusion contract.
            if unsafe{read_volatile(addr_of!(VDSO_MAP_DEBUG).cast::<u8>().add(27))}!=0 {
                // SAFETY: immutable NUL string, no variadic arguments.
                unsafe{kprintf(b"arch_map_vdso(): not available\n\0".as_ptr().cast());}
            }
        }
        2=>{
            // SAFETY: exact original int32 argument for %d.
            unsafe{kprintf(b"ERROR: adding memory range for vdso. %d\n\0".as_ptr().cast(),error);}
        }
        3=>{
            // SAFETY: original null short circuit; caller retains both object
            // lifetimes. Read only the original proc pointer and int32 pid.
            let pid=unsafe{
                if vm.is_null(){-1}else{
                    let process=read(addr_of!((*vm).proc)).cast::<Process>();
                    if process.is_null(){-1}else{read(addr_of!((*process).pid))}
                }
            };
            let mut offset_address=null_mut();
            // SAFETY: exact existing optional-output ABI, writable local slot.
            // The qualified bridge always publishes the same nonnull static
            // offset address and does not alter its contents or ownership.
            let offset=unsafe{
                arch_vdso_state_bridge(null_mut(),null_mut(),addr_of_mut!(offset_address));
                read(offset_address) as CULong
            };
            // SAFETY: %d consumes int32 and five %lx consume unsigned long64;
            // signed ptrdiff_t converts modulo2^64, as in the original C cast.
            unsafe{kprintf(b"mcexec_v10: vdso_map pid=%d container=0x%lx vdso=0x%lx vdso_end=0x%lx offset=0x%lx size=0x%lx pages=%d\n\0".as_ptr().cast(),pid,container,vdso_address,vdso_end,offset,container_size,pages);}
        }
        4=>{
            // SAFETY: exact original int32 argument for %d.
            unsafe{kprintf(b"ihk_mc_pt_set_range failed. %d\n\0".as_ptr().cast(),error);}
        }
        5=>{
            // SAFETY: exact original int32 argument for %d.
            unsafe{kprintf(b"ERROR: adding memory range for vvar. %d\n\0".as_ptr().cast(),error);}
        }
        _=>{}
    }
}
