"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source materialization; no compiler, tests or subprocess. Freeze genuine provider bodies.
"""
from pathlib import Path
import re,json,hashlib,shutil
P=Path(__file__).resolve().parent;F=P/'fixture';K=Path('/home/holden/mckernel');B=P.parent.parent
records=[]
def pin(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def put(p,s):
 with p.open('x') as f:f.write(s)
def item(path,kind,name):
 s=path.read_text();pat=r'(?m)^(?:pub(?:\([^)]*\))? )?(?:unsafe )?(?:extern "C" )?'+kind+r' '+re.escape(name)+r'\b';m=re.search(pat,s);assert m,(path,name)
 start=m.start()
 while start and s[:start].splitlines()[-1].startswith('#['):start=s.rfind('\n',0,start-1)+1
 j=s.index('{',m.end());d=1;i=j+1
 while d:
  if s[i]=='{':d+=1
  elif s[i]=='}':d-=1
  i+=1
 if s[i:i+1]=='\n':i+=1
 t=s[start:i];records.append(dict(source=pin(path),name=name,bytes=len(t.encode()),sha256=hashlib.sha256(t.encode()).hexdigest(),exact_text=t));return t
rust=K/'kernel/rust'
put(F/'abi.rs',(rust/'abi.rs').read_text())
put(F/'rbtree.inc',item(rust/'rbtree.rs','struct','RbNode'))
ls=['IhkRwSpinlock','__ihk_rwspinlock_read_lock','__ihk_rwspinlock_read_unlock','ihk_rwspinlock_read_lock_noirq','ihk_rwspinlock_read_unlock_noirq']
lock='use core::sync::atomic::{AtomicI32,Ordering};\nconst IHK_RWSPINLOCK_WRITELOCKED:i32=0xff<<24;\nextern "C" {fn preempt_disable();fn preempt_enable();fn cpu_pause();}\n'
for n in ls:lock+=item(rust/'lock_helpers.rs','struct' if n=='IhkRwSpinlock' else 'fn',n)
put(F/'lock.inc',lock)
ps=['vm_range_from_rb_node','process_range_cache_hit_result','process_lookup_range_relation_result','process_range_cache_store_result','process_lookup_memory_range_body_result','process_range_public_log_result','process_lookup_memory_range_public_result','lookup_process_memory_range']
proc='use crate::abi::{CInt,CULong,VmRange,ProcessVm};\nuse crate::rbtree::RbNode;use core::ffi::c_void;use core::ptr::null_mut;\nconst PROCESS_RANGE_PUBLIC_LOG_LOOKUP_ENTER:CInt=1;const PROCESS_RANGE_PUBLIC_LOG_LOOKUP_EXIT:CInt=2;\ntype ProcessRangePublicLogFn=unsafe extern "C" fn(CInt,*mut c_void,*mut VmRange,CULong,CULong,CInt);\nextern "C" {fn process_range_public_log_bridge(event:CInt,vm:*mut c_void,range:*mut VmRange,start:CULong,end:CULong,error:CInt);}\n'
for n in ps:proc+=item(rust/'process_helpers.rs','fn',n)
put(F/'process.inc',proc)
ss=['read_char','write_char','char_diff','strlen','strcpy','strcmp','memset']
string='use crate::abi::{CInt,CULong,SizeT};use core::ffi::c_void;use core::ptr::{read_volatile,write_volatile};\n'
for n in ss:string+=item(rust/'string.rs','fn',n)
put(F/'string.inc',string)
mem='use crate::abi::{AbiListHead,CInt,CULong,IhkAtomic,IhkSpinlock};use crate::string::{strlen,strcmp,strcpy};\nuse core::ffi::c_void;use core::ptr::null_mut;use core::mem::{size_of,offset_of};use core::sync::atomic::{AtomicI32,Ordering};\nconst IHK_MC_AP_NOWAIT:CULong=2;\n'
s=(rust/'mem_helpers.rs').read_text()
for line in s.splitlines():
 if line.startswith('const PAGEALLOC_TRACK_'):mem+=line+'\n'
start=s.index('type MemPageallocBaseAllocFn =');end=s.index('type MemPageallocInvalidFreeFn',start)
mem+=s[start:end]
mem+='type MemKmallocSpinLockFn=unsafe extern "C" fn(CULong)->CULong;\ntype MemKmallocSpinUnlockFn=unsafe extern "C" fn(CULong,CULong);\n'
mem+='extern "C" {\n'+s[s.index('    fn mem_pagealloc_track_base_alloc_bridge('):s.index('    fn mem_pagealloc_track_base_free_bridge(')]
start=s.index('    fn mem_pagealloc_track_meta_alloc_bridge(');end=s.index('    fn mem_pagealloc_track_noirq_lock_bridge(',start);mem+=s[start:end]
start=s.index('    fn mem_pagealloc_track_spin_init_bridge(');end=s.index('    fn mem_pagealloc_invalid_free_bridge(',start);mem+=s[start:end]
start=s.index('    #[link_name = "memdebug"]');end=s.index('    #[link_name = "kmalloc_track_hash"]',start);mem+=s[start:end]+'}\n'
ms=['PageallocTrackAddrEntry','PageallocTrackEntry','list_add','list_add_after','init_list_head','pagealloc_track_hash','pagealloc_addr_hash','pagealloc_track_entry_alloc_count','pagealloc_track_entry_from_hash','pagealloc_track_log','pagealloc_entry_addr_list_lock','pagealloc_rehash_addr_entry','pagealloc_track_find_entry_result','pagealloc_track_alloc_result','pagealloc_track_hash_ptr','pagealloc_track_locks_ptr','pagealloc_addr_hash_ptr','pagealloc_addr_locks_ptr','_ihk_mc_alloc_aligned_pages_node']
for n in ms:mem+=item(rust/'mem_helpers.rs','struct' if n.startswith('Pagealloc') else 'fn',n)
put(F/'mem.inc',mem)
admission=B/'next-exec-filename-admission-source-1/filename_admission.RUST-FRAGMENT.rs.inc';descriptor=B/'next-exec-descriptor-init-source-1/descriptor_init.RUST-FRAGMENT.rs.inc'
layout=['size_of::<ProcessVm>()','align_of::<ProcessVm>()','offset_of!(ProcessVm,memory_range_lock)','offset_of!(ProcessVm,vm_range_tree)','offset_of!(ProcessVm,range_cache)','offset_of!(ProcessVm,range_cache_ind)','size_of::<VmRange>()','align_of::<VmRange>()','offset_of!(VmRange,vm_rb_node)','offset_of!(VmRange,start)','offset_of!(VmRange,end)','offset_of!(VmRange,flag)','size_of::<abi::IhkRwSpinlock>()','size_of::<abi::IhkSpinlock>()','size_of::<abi::IhkAtomic>()','size_of::<abi::AbiListHead>()']
main='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
mod abi;
use abi::{CInt,CULong,ProcessVm,VmRange};use core::ffi::c_void;
use core::mem::{size_of,align_of,offset_of};
const EFAULT:CInt=14;const ENOMEM:CInt=12;
extern "C" {fn kprintf(format:*const i8,...)->CInt;}
mod rbtree {include!("rbtree.inc");}
mod lock_helpers {include!("lock.inc");}
mod process_helpers {include!("process.inc");}
mod string {include!("string.inc");}
mod mem_helpers {include!("mem.inc");}
'''+admission.read_text()+descriptor.read_text()+'''
#[no_mangle] pub unsafe extern "C" fn f03_admission_descriptor_layout(out:*mut usize)->usize {
 let v=['''+','.join(layout)+'''];core::ptr::copy_nonoverlapping(v.as_ptr(),out,v.len());v.len()
}
'''
put(F/'admission_descriptor_actual.rs',main)
put(P/'GENUINE-PROVIDER-BODY-EXTRACTIONS.json',json.dumps(dict(scope=__doc__,records=records,frozen_entry_fragments=[pin(admission),pin(descriptor)],actual_ABI=pin(rust/'abi.rs'),private_ABI=pin(F/'abi.rs'),no_modified_provider_bodies=True),indent=2,sort_keys=True)+'\n')
