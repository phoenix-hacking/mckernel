# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,os
R=Path('/home/holden/mckernel'); D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall/next-vdso-global-pages-1'); F=D/'fixture-source-only-1';F.mkdir(mode=0o700)
def put(n,s):
 p=F/n;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_text(s);return desc(p)
def desc(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def block(s,needle):
 start=s.index(needle);a=s.index('{',start);depth=1;i=a+1
 while depth:
  if s[i]=='{':depth+=1
  if s[i]=='}':depth-=1
  i+=1
 return s[start:i]
C=(R/'arch/x86_64/kernel/syscall.c').read_text(); S=(R/'kernel/rust/syscall_policy.rs').read_text();M=(R/'kernel/rust/x86_memory_helpers.rs').read_text();P=(R/'kernel/rust/x86_cpu_helpers.rs').read_text();DBG=(R/'kernel/rust/debug.rs').read_text()
orig=block(C,'int vdso_map_global_pages(void)');cs=block(C,'struct vdso {')+';';rs='#[repr(C)]\n'+block(S,'pub struct ArchVdso {');db='#[repr(C)]\n'+block(DBG,'pub struct Ddebug {')
put('actual_original_vdso_map_global_pages.inc',orig+'\n');put('actual_vdso_layout.inc','#define VDSO_MAXPAGES 2\n'+cs+'\n')
headers=['arch/x86_64/kernel/include/arch-memory.h','arch/x86_64/kernel/include/ihk/types.h','arch/x86_64/kernel/include/errno.h','lib/include/generic-errno.h','lib/include/types.h','lib/include/ihk/debug.h','kernel/include/lwk/compiler.h','kernel/include/lwk/compiler-gcc.h'];hp=[]
for rel in headers:
 p=F/'headers'/rel;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_bytes((R/rel).read_bytes());hp.append(dict(origin=desc(R/rel),copy=desc(p)))
put('actual_real_abi.h','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
#include <ihk/debug.h>
#include "actual_vdso_layout.inc"
_Static_assert(sizeof(long)==8 && sizeof(void*)==8 && sizeof(int)==4, "LP64");
_Static_assert(sizeof(struct vdso)==88, "actual vdso");
_Static_assert(__builtin_offsetof(struct vdso,vvar_virt)==32, "vvar slot");
_Static_assert(__builtin_offsetof(struct vdso,hpet_virt)==48, "hpet slot");
_Static_assert(__builtin_offsetof(struct vdso,pvti_virt)==64, "pvti slot");
_Static_assert(sizeof(enum ihk_mc_pt_attribute)==8, "real PTattribute ABI");
_Static_assert(PTATTR_ACTIVE==1 && PTATTR_USER==4 && PTATTR_NO_EXECUTE==0x8000000000000000UL && PTATTR_UNCACHABLE==0x10000, "real attrs");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8, "real debug ABI");
''')
put('original_C_unit.c','''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "actual_real_abi.h"
extern struct vdso vdso;
extern void *pvti;
extern int pvti_npages;
extern int arch_setup_pvclock(void);
extern unsigned long virt_to_phys(void *);
extern int ihk_mc_pt_set_page(void *,void *,unsigned long,enum ihk_mc_pt_attribute);
#define vdso_map_global_pages original_C_vdso_map_global_pages
#include "actual_original_vdso_map_global_pages.inc"
''')
# Selected functions/structs copied exactly; only their surrounding imports and controlled providers differ.
setup=block(P,'pub unsafe extern "C" fn x86_arch_setup_pvclock_body_result(')
phys=block(M,'pub unsafe extern "C" fn x86_virt_to_phys_body_result(')
page=block(M,'pub unsafe extern "C" fn ihk_mc_pt_set_page(')
state=block(S,'unsafe fn arch_vdso_state()')
frag=(D/'candidate/syscall_policy.vdso_map_global_pages.FRAGMENT.rs').read_text()
rust='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,private_interfaces,non_snake_case)]
use core::ffi::c_void;
use core::ptr::{read_volatile,write_volatile,addr_of,addr_of_mut,null_mut};
type CInt=i32;type CLong=i64;type CULong=u64;type SizeT=u64;
const EFAULT:CInt=14;const EINVAL:CInt=22;const ENOMEM:CInt=12;
const PAGE_SIZE:CULong=4096;
const PTATTR_ACTIVE:CULong=1;const PTATTR_USER:CULong=4;
const PTATTR_NO_EXECUTE:CULong=0x8000000000000000;const PTATTR_UNCACHABLE:CULong=0x10000;
extern "C" {
 fn arch_vdso_state_bridge(v:*mut *mut ArchVdso,s:*mut *mut SizeT,o:*mut *mut isize);
 fn fixture_setup()->CInt;
 fn fixture_phys(p:*mut c_void)->CULong;
 fn kprintf(p:*const i8,...)->CInt;
}
'''+rs+'\nmod debug {\n'+db+'\n}\n'+state+'''
// Only provider adapters below are fixture controlled; exact production bodies follow.
mod x86_cpu_helpers {
 use super::*;
 type X86GetIntFn=unsafe extern "C" fn()->CInt;
 type X86AllocAlignedPagesNodeFn=unsafe extern "C" fn(CInt,CInt,CULong,CInt,CInt,CULong,*mut i8,CInt)->*mut c_void;
 type X86CpuLogFn=unsafe extern "C" fn(CInt);
 #[no_mangle]
'''+setup+'''
 pub unsafe extern "C" fn arch_setup_pvclock()->CInt { unsafe {fixture_setup()} }
}
mod x86_memory_helpers {
 use super::*;
 type X86AddrLogFn=unsafe extern "C" fn(CInt,CULong);
 const X86_ADDR_LOG_KERNEL:CInt=1;const X86_ADDR_LOG_STRAIGHT:CInt=2;
 extern "C" { fn x86_pt_set_page_bridge(pt:*mut c_void,virt:CULong,phys:CULong,attr:CULong)->CInt; }
 #[no_mangle]
'''+phys+'\n#[no_mangle]\n'+page+'''
 pub unsafe extern "C" fn virt_to_phys(p:*mut c_void)->CULong { unsafe {fixture_phys(p)} }
}
'''+frag
put('selected_Rust_unit.rs',rust)
manifest=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='FIXTURE_SOURCE_ONLY_NOT_SECOND_READY_COHORT_NO_RUNNER_OR_GRANT',actual_result=None,production_queue='private-current78-F06 bd6c/3e2e remains sole ready job',origins=[desc(R/x) for x in ['arch/x86_64/kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/rust/debug.rs','kernel/rust/x86_memory_helpers.rs','kernel/rust/x86_cpu_helpers.rs']],actual_headers=hp,exact_Rust_functions=['arch_vdso_state','x86_arch_setup_pvclock_body_result','x86_virt_to_phys_body_result','ihk_mc_pt_set_page'],candidate=desc(D/'candidate/syscall_policy.vdso_map_global_pages.FRAGMENT.rs'),controls=['page-table bridge records mappings; no hardware page tables','pvclock available/allocation callbacks operate only on bounded fixture buffers; no MSR/CPU/real allocator','virt translation exact Rust arithmetic with declared test ranges; no physical access','global state bridge exposes live C struct and stable fixture slots; no kernel lifetime qualification'],all_outputs=[])
(F/'SOURCE-PREPARATION.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
print(desc(F/'SOURCE-PREPARATION.json'))
