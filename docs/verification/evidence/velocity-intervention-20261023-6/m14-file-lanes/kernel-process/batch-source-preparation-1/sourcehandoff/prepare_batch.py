"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Coherent process-source batch and smallest remaining-body fixture extension only.
No executable recipe/driver/cohort/slot/compiler; frozen sync queue is immutable.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parents[1];LANE=P.parent;ROOT=Path('/home/holden/mckernel');F=P/'fixture-extension';H=P/'sourcehandoff';SYNC=LANE/'next-sync-one-page';REMAP=LANE/'next-remap-one-page';LOG=LANE/'next-sync-range-log'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def item(s,marker):
 start=s.index(marker);brace=s.index('{',start);end=brace+1;depth=1
 while depth:
  depth+=(s[end]=='{')-(s[end]=='}');end+=1
 return s[start:end]
def fn(s,name):return '#[no_mangle]\n'+item(s,'pub unsafe extern "C" fn '+name+'(')+'\n'
def line(s,marker):return s[:s.index(marker)].count('\n')+1
def main():
 pre={'kernel/process.c':'08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45','kernel/rust/process_helpers.rs':'d04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d'}
 post={'kernel/process.c':'7ab29dad607ac06e9548065f4395c6e870359558a2777844c1052d67e046ca13','kernel/rust/process_helpers.rs':'49f61c90967bf2d79324cbec946b3c22931b79d54638abf8fb3c647bf679b9b2'}
 for rel,sha in pre.items():assert pin(ROOT/rel)['sha256']==sha
 for rel,sha in post.items():assert pin(REMAP/'candidate'/rel)['sha256']==sha
 frozen={'EXECUTABLE-READY.NOT-GRANTED.json':'9a64c27953f622dac3eac1f1d65c95b80ae8f2d558e83f951016ba1ac8aa43be','EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json':'1391be5c805be84a46e570d70c5e680ce26f3173c33504ad948205afffa2475d','run_owned_first_candidate.py':'b619922e059f0a685136235e2f22e4c633b9ec7a313e71fda9f0c1d55cdf4b37'}
 for name,sha in frozen.items():assert pin(SYNC/'sourcehandoff'/name)['sha256']==sha
 (P/'candidate/kernel/rust').mkdir(parents=True);(P/'patch').mkdir()
 for rel in pre:
  dest=P/'candidate'/rel;shutil.copy2(REMAP/'candidate'/rel,dest)
  (P/'patch'/(Path(rel).name+'.diff')).write_text(''.join(difflib.unified_diff((ROOT/rel).read_text().splitlines(True),dest.read_text().splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 c=(ROOT/'kernel/process.c').read_text();candidate=(P/'candidate/kernel/process.c').read_text();rust=(P/'candidate/kernel/rust/process_helpers.rs').read_text()
 for marker in ['void vm_range_insert_dump_bridge(','int sync_one_page(','void process_sync_range_log_bridge(','int remap_one_page(','static void dtree(','static void dump_tree(']:assert item(c,marker)==item(candidate,marker),marker
 assert rust.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 for name in ['vm_range_insert_dump_bridge','sync_one_page','process_sync_range_log_bridge','remap_one_page']:assert rust.count('pub unsafe extern "C" fn '+name+'(')==1,name
 # Extend existing real PTE providers, never fork their implementation or the
 # queued driver. Existing six PTE operations and memobj dispatch are imports
 # supplied by the future accepted retained sync actual_provider.o.
 pte=(ROOT/'kernel/rust/pte_helpers.rs').read_text();prefix=pte[:pte.index('extern "C" {')]
 pt=prefix+item(pte,'unsafe fn pte_store(')+'\n'+fn(pte,'pte_make_fileoff')+fn(pte,'pte_xchg')+'''extern "C" {
 pub fn pte_is_null(ptep:*const CULong)->CInt;
 pub fn pte_is_fileoff(ptep:*const CULong,pgsize:SizeT)->CInt;
 pub fn pte_is_dirty(ptep:*const CULong,pgsize:SizeT)->CInt;
 pub fn pte_get_phys(ptep:*const CULong)->CULong;
}
'''
 (F/'pte_exchange_extension.ACTUAL.rs.inc').write_text(pt)
 page=(ROOT/'kernel/rust/page_helpers.rs').read_text();page_layout=''
 for marker in ['struct ListHead {','struct IhkAtomic {','struct IhkAtomic64 {','pub struct Page {']:page_layout+='#[repr(C)]\n'+item(page,marker)+'\n'
 ddebug=item((ROOT/'kernel/rust/debug.rs').read_text(),'pub struct Ddebug {')
 args='#[repr(C)]\n'+item(rust,'struct ProcessRemapArgs {')+'\n'
 remap=(REMAP/'fixture/remap.ACTUAL-RUST.inc').read_text().replace('fn remap_one_page(','fn fixture_rust_remap_one_page(',1)
 log=(LOG/'fixture/log.ACTUAL-RUST.inc').read_text().replace('fn process_sync_range_log_bridge(','fn fixture_rust_process_sync_range_log_bridge(',1)
 provider='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// SOURCE-ONLY extension: link retained accepted sync actual_provider.o later.
#![no_std]
#![allow(dead_code,non_snake_case)]
#[path="ABI_PATH"] mod abi;
use core::ffi::c_void;
use abi::{CInt,CULong,OffT,SizeT,Memobj,ProcessVm,VmRange};
const PAGE_SIZE:CULong=4096;
#[repr(C)]
'''.replace('ABI_PATH',str(SYNC/'fixture/abi.ACTUAL.rs'))+ddebug+'\n'+args+'''
mod pte_helpers { include!("pte_exchange_extension.ACTUAL.rs.inc"); }
mod object_helpers {
 use crate::abi::{CInt,CULong,SizeT,Memobj};
 extern "C" { pub fn memobj_flush_page(obj:*mut Memobj,phys:CULong,pgsize:SizeT)->CInt; }
}
// Explicit typed host effect adapters. These do not claim to execute native
// TLB/mapping, page hash/unmap, allocator/tracking or RSS provider algorithms.
mod page_helpers {
 use crate::abi::{CInt,CULong,OffT};
 PAGE_LAYOUT
 extern "C" { fn fixture_page_unmap_effect(page:*mut Page)->CInt; }
 pub unsafe fn page_unmap(page:*mut Page)->CInt { fixture_page_unmap_effect(page) }
}
mod x86_memory_helpers {
 use core::ffi::c_void;use crate::abi::CULong;
 extern "C" { fn fixture_tlb_effect(address:CULong);fn fixture_phys_to_virt_effect(phys:CULong)->*mut c_void; }
 pub unsafe fn flush_tlb_single(address:CULong) { fixture_tlb_effect(address); }
 pub unsafe fn phys_to_virt(phys:CULong)->*mut c_void { fixture_phys_to_virt_effect(phys) }
}
mod mem_helpers {
 use core::ffi::c_void;use crate::abi::{CInt,CULong,Memobj};
 extern "C" { fn fixture_free_effect(ptr:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt);fn fixture_rss_effect(obj:*mut Memobj,size:CULong,pgsize:CInt); }
 pub unsafe fn _ihk_mc_free_pages(ptr:*mut c_void,n:CInt,user:CInt,file:*mut i8,line:CInt) { fixture_free_effect(ptr,n,user,file,line); }
 pub unsafe fn rusage_memory_stat_sub(obj:*mut Memobj,size:CULong,pgsize:CInt) { fixture_rss_effect(obj,size,pgsize); }
}
extern "C" {
 static mut process_remap_one_page_entry_debug:Ddebug;
 static mut process_remap_one_page_rss_debug:Ddebug;
 static mut process_remap_one_page_exit_debug:Ddebug;
 static process_remap_free_file:*const i8;
 static process_remap_free_line:CInt;
 fn phys_to_page(phys:CULong)->*mut page_helpers::Page;
 fn kprintf(format:*const i8,...)->CInt;
}
'''.replace('PAGE_LAYOUT',page_layout)+remap+'\n'+log+'''
#[no_mangle]
pub unsafe extern "C" fn fixture_remap_layout(out:*mut CULong) {
 use core::mem::{size_of,align_of,offset_of};
 let data=[size_of::<ProcessRemapArgs>(),align_of::<ProcessRemapArgs>(),offset_of!(ProcessRemapArgs,off),offset_of!(ProcessRemapArgs,start),offset_of!(ProcessRemapArgs,memobj),size_of::<page_helpers::Page>(),size_of::<Ddebug>()];
 for (index,value) in data.iter().enumerate() { *out.add(index)=*value as CULong; }
}
'''
 (F/'remaining_provider.rs').write_text(provider)
 logical=str(REMAP.parent/'next-sync-range-log/candidate/kernel/process.c');original=(REMAP/'fixture/original_remap.ACTUAL-C.inc').read_text();source=(LOG/'candidate/kernel/process.c').read_text();startline=line(source,'int remap_one_page(');free_line=line(source,'_ihk_mc_free_pages(phys_to_virt(phys), pgsize/PAGE_SIZE, IHK_MC_PG_USER, __FILE__, __LINE__);')
 metadata=(REMAP/'fixture/remap.ACTUAL-C-METADATA.inc').read_text();args_c=item(source,'struct rfp_args {')+';\n'
 template=(F/'remaining_parity.c.in').read_text();text=template.replace('/* ACTUAL RFP ARGS HERE */',args_c).replace('/* ACTUAL C METADATA WITH LOGICAL FILE HERE */','#line 1 '+json.dumps(logical)+'\n'+metadata+'\n#line 1 "remaining_parity.c"')
 text=text.replace('/* ACTUAL ORIGINAL REMAP CALLBACK HERE */','#line '+str(startline)+' '+json.dumps(logical)+'\n'+original+'\n#line 1 "remaining_parity.c"').replace('/* ACTUAL ORIGINAL RANGE LOGGER HERE */',(LOG/'fixture/original_log.ACTUAL-C.inc').read_text())
 text=text.replace('LOGICAL_FILE_LITERAL',json.dumps(logical)).replace('FREE_LINE_VALUE',str(free_line));assert free_line==2469
 (F/'remaining_parity.c').write_text(text)
 # Compile-only ABI witness source; no compiler invocation/recipe is created.
 witness='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <rusage_private.h>
#include <ihk/debug.h>
RFP_ARGS
extern int remap_one_page(void *,page_table_t,pte_t *,void *,int);
extern void process_sync_range_log_bridge(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int);
typedef int (*original_visit_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&remap_one_page),original_visit_t),"unchanged remap callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sync_range_log_bridge),void (*)(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int)),"unchanged range logger ABI");
_Static_assert(sizeof(struct rfp_args)==24&&__alignof__(struct rfp_args)==8&&__builtin_offsetof(struct rfp_args,off)==0&&__builtin_offsetof(struct rfp_args,start)==8&&__builtin_offsetof(struct rfp_args,memobj)==16,"actual ProcessRemapArgs ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8,"actual existing Page ABI; no remap field access");
_Static_assert(sizeof(struct ddebug)==32&&sizeof(pte_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,"supported diagnostic/PTE/vararg widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page *(*)(uintptr_t)),"named existing C provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void (*)(void *,int,int,char *,int)),"tracked free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),void (*)(struct memobj *,unsigned long,int)),"RSS CInt narrowing ABI");
_Static_assert(IHK_MC_PG_USER==1,"same original user page accounting mode");
'''.replace('RFP_ARGS',args_c)
 (F/'actual_remaining_header_ABI.c').write_text(witness)
 fixture=dict(scope=SCOPE,status='SOURCE_ONLY_REMAINING_BODY_FIXTURE_EXTENSION_NO_RECIPE_DRIVER_OR_JOB',sources={name:pin(F/name) for name in ['remaining_provider.rs','remaining_parity.c','pte_exchange_extension.ACTUAL.rs.inc','actual_remaining_header_ABI.c']},reuse_frozen_sync_provider=dict(ready=pin(SYNC/'sourcehandoff/EXECUTABLE-READY.NOT-GRANTED.json'),required_future_object=str(SYNC/'output-first-candidate-1/actual_provider.o'),qualification='Must bind the object from root completed accepted795 receipt before any extension run. No object/proof assumed now, no sync tests replayed.'),real_algorithm_providers='Retained sync PTE predicates/phys/atomic helpers and typed memobj dispatch; this source adds real unchanged pte_make_fileoff and pte_xchg bodies only.',host_effect_models=['TLB instruction effect','phys_to_page lookup return and page_unmap result','phys_to_virt address translation','tracked free side effect and RSS subtraction'],planned_comparisons=dict(remap_default4KiB_matrix=192,remap_2MiB_1GiB_provider_domains=32,ordered_mutation_cases=120,range_log_signed_unsigned_pointer_varargs=60,total=404),oracles='Independently expected fileoff encoding, captured-old-PTE release decision, full event tape/final live PTE; flush error ignored; absent page/unmap0/nonzero branches, free/RSS cardinality and order; entry/TLB/flush/lookup/unmap/free/RSSdebug/RSS/exit mutation points; static tracked-free file+line2469 via explicit logical source directives; all three debug gates; exact variadic pointer/UL/int payloads and ignored logger returns; real structure layout witness.',unproven='No extension compile/link/parity/header ABI result; controlled page/free/RSS adapters do not validate existing provider algorithms, locks/refcounts, native instructions or whole-crate/default image.',execution_argv_prepared=0,drivers_created=0,compiler_jobs=0,test_jobs=0,CPU_reservations=0)
 write(H/'FIXTURE-EXTENSION-SOURCE-ONLY.json',fixture)
 rows=[pin(P/'candidate'/rel) for rel in pre];identity=hashlib.sha256(json.dumps([[p['sha256'],p['bytes']] for p in rows],separators=(',',':')).encode()).hexdigest()
 manifest=dict(scope=SCOPE,status='COHESIVE_PRIVATE_FOUR_BODY_PRODUCTION_SOURCE_BATCH_NOT_COMPILED_OR_EXECUTABLE_READY',selected_bodies=['vm_range_insert_dump_bridge plus dtree/dump_tree computation','sync_one_page','process_sync_range_log_bridge','remap_one_page'],canonical_preimages={rel:pin(ROOT/rel) for rel in pre},private_postimages={rel:pin(P/'candidate'/rel) for rel in pre},patches={rel:pin(P/'patch'/(Path(rel).name+'.diff')) for rel in pre},batch_source_identity=identity,identity_qualification='Two-file source bundle identity only, not a full78 production cohort or linked artifact.',source_lineage=[pin(LANE/'sourcehandoff/SOURCE-CANDIDATE-AND-ABI.json'),pin(SYNC/'sourcehandoff/SOURCE-NEXT-BODY.json'),pin(LOG/'sourcehandoff/SOURCE-NEXT-BODY.json'),pin(REMAP/'sourcehandoff/SOURCE-NEXT-BODY.json')],accepted_dump_production=pin(LANE/'production-consumer-preparation-1/bounded-observer-correction-1/OBSERVER-RESULT.json'),only_executable_queue={name:pin(SYNC/'sourcehandoff'/name) for name in frozen},frozen_sync_inputs_unmodified=True,fixture_extension=pin(H/'FIXTURE-EXTENSION-SOURCE-ONLY.json'),fallback='Exact original source bodies preserved byte-for-byte in C fallback, including original dtree/dump_tree; selected C adds only original gate/debug/tracked-free static identity data. No new C helper computation.',ownership='Existing actual Rust sync/remap owner helpers, VM PT exclusion and memobj ref/unref order unchanged. Remap still captures atomic old PTE, ignores flush errors, unmaps/frees only last mapping then logs/subtracts RSS, no page access after unmap/free. Range logger remains after owner unlock and sync failure only. No new references/locks/ACKs.',ABI_and_provider_limits='Exact original C/Rust full signatures retained; ProcessRemapArgs and Page source layout bound with uncompiled header witness. Public phys_to_page C forwarding provider remains explicit debt (Rust lookup underneath), plus existing backend lock/log/free callbacks; static C identity data retained. Host fixture adapters do not prove native/provider algorithms.',prior_failure_history='E0428 2fb3/e9a correctedaccepted7a; original retained-GOT observerc774 plus accepted84ef/e48c; source-extraction prep failure retained under sync. No histories reset or new tests attempted.',requires='Root complete queued sync fixture and independently review batch/extension, stage coherent pending provider sources, then bind a fresh full production cohort before any batch compile. Root owns canonical integration and full default/native validation.',compiler_jobs=0,test_jobs=0,CPU_reservations=0,executable_recipes_created=0,drivers_created=0,canonical_or_shared_mutations=0,source_correctness_claim=False,fullcrate_default_native_file_credit=False)
 write(H/'COHESIVE-PRODUCTION-SOURCE-BATCH.json',manifest)
 for name,sha in frozen.items():assert pin(SYNC/'sourcehandoff'/name)['sha256']==sha
 print(json.dumps(dict(scope=SCOPE,batch=pin(H/'COHESIVE-PRODUCTION-SOURCE-BATCH.json'),fixture_extension=pin(H/'FIXTURE-EXTENSION-SOURCE-ONLY.json'),postimages=manifest['private_postimages'],compiler_jobs=0,test_jobs=0,CPU_reservations=0,drivers_created=0),indent=2))
if __name__=='__main__':main()
