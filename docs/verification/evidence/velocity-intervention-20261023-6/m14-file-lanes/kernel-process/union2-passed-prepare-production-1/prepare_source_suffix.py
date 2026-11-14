"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Rebase only passed prepare96 and F01 getter consumer on canonical union2.
Root owns the single future union3 Rust compile. No compiler or CPU reservation.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;L=P.parent;ROOT=Path('/home/holden/mckernel')
U=L.parents[1]/'root-union-preparation-2'
OLD=L/'production-batch-preparation-1/bounded-source-correction-1'
HELD=L/'next-page-fault-prepare/preexec-lock-binding-correction-1'
PASSED=L/'next-page-fault-prepare/bounded-reference-context-correction-1/sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'
F01=L.parent/'kernel-mem/page-offset-typed-provider-source-only-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def put(p,s):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:f.write(s)
def write(p,j):put(p,json.dumps(j,indent=2)+'\n')
def function(s,marker):
 a=s.index(marker);br=s.index('{',a);e=br+1;depth=1
 while depth:depth+=(s[e]=='{')-(s[e]=='}');e+=1
 return s[a:e]
def main():
 assert pin(ROOT/'kernel/process.c')['sha256']=='7ab29dad607ac06e9548065f4395c6e870359558a2777844c1052d67e046ca13'
 assert pin(ROOT/'kernel/rust/process_helpers.rs')['sha256']=='5bf085bfa3f60217abacbda380e80d35d2fd56922c0e82f82dbab1d5fe09d4d1'
 assert pin(PASSED)['sha256']=='c8802d6c1da564b06528a22dd3f15ef86abf9cfb82754d47ea053583661a2276'
 accepted=json.loads(PASSED.read_text());assert accepted['actual_original_C_Rust_comparisons']==96
 current={rel:pin(ROOT/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']}
 c=(ROOT/'kernel/process.c').read_text();r=(ROOT/'kernel/rust/process_helpers.rs').read_text()
 assert (U/'source/kernel/process.c').read_text()==c and (U/'source/kernel/rust/process_helpers.rs').read_text()==r
 original=(HELD/'fixture/original_page_fault_prepare.ACTUAL-C-BLOCK.inc').read_text().rstrip('\n')
 assert c.count(original)==1
 body=(HELD/'fixture/page_fault_prepare.ACTUAL-RUST.inc').read_text()
 assert 'crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(' not in body
 assert '__ihk_mc_spinlock_lock_noirq(' in body
 getter=(HELD/'fixture/page_offset.PROCESS-ADAPTER-ONLY.rs.inc').read_text()
 original_getter=function(c,'long process_page_offset_bridge(')
 c=c.replace(original_getter,'#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nlong process_page_offset_bridge(void *);\n#else\n'+original_getter+'\n#endif',1)
 bounds='dkprintf("%s: pgaddr=%lx,range->start=%lx,range->end=%lx,pgaddr+pgsize=%lx\\n"'
 line=(ROOT/'kernel/process.c').read_text()[:(ROOT/'kernel/process.c').read_text().index(bounds)].count('\n')+1
 metadata=(HELD/'fixture/actual_C_metadata.inc').read_text()
 oldline=json.loads((HELD.parent/'sourcehandoff/SOURCE-NEXT-BODY.json').read_text())['bounds_debug_original_line']
 assert metadata.count('.line = '+str(oldline)+',')==1
 metadata=metadata.replace('.line = '+str(oldline)+',','.line = '+str(line)+',',1)
 selection=(HELD/'fixture/actual_C_selection.inc').read_text().rstrip('\n')
 assert original in selection
 c=c.replace(original,selection,1)
 c=c.replace('int page_fault_process_memory_range(',metadata+'\nint page_fault_process_memory_range(',1)
 declaration='    fn process_page_offset_bridge(page: *mut c_void) -> OffT;\n'
 assert r.count(declaration)==1;r=r.replace(declaration,'',1)
 extern='''unsafe extern "C" {
    static mut process_page_fault_prepare_bounds_debug: crate::debug::Ddebug;
    fn ihk_mc_pt_lookup_pte(
        page_table: *mut c_void, virt: *mut c_void, pgshift: CInt,
        basep: *mut *mut c_void, sizep: *mut SizeT, p2alignp: *mut CInt,
    ) -> *mut CULong;
}
'''
 assert 'fn ihk_mc_pt_lookup_pte(' not in r and 'fn process_page_fault_prepare_body_result(' not in r
 assert r.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 r+='\n// Passed preparation slice; Page offset read remains F01-owned.\n'+getter+'\n'+extern+'\n'+body
 # No anonymous allocator or other untested callback ports enter this union3
 # proposal: all nine prior invalidation callback declarations stay unchanged.
 for name in ['process_memobj_invalidate_page_bridge','process_invalidate_one_page_log_bridge','process_pte_make_fileoff_bridge','process_pte_xchg_bridge','process_pte_is_null_bridge','process_pte_is_fileoff_bridge','process_pte_get_phys_bridge','process_pgsize_to_tbllv_bridge','process_tbllv_to_contpgsize_bridge']:
  assert 'pub unsafe extern "C" fn '+name+'(' not in r,name
  assert function(c,('uintptr_t ' if name=='process_pte_get_phys_bridge' else 'size_t ' if name=='process_tbllv_to_contpgsize_bridge' else 'void ' if name in ['process_invalidate_one_page_log_bridge','process_pte_make_fileoff_bridge','process_pte_xchg_bridge'] else 'int ')+name+'(')==function((ROOT/'kernel/process.c').read_text(),('uintptr_t ' if name=='process_pte_get_phys_bridge' else 'size_t ' if name=='process_tbllv_to_contpgsize_bridge' else 'void ' if name in ['process_invalidate_one_page_log_bridge','process_pte_make_fileoff_bridge','process_pte_xchg_bridge'] else 'int ')+name+'(')
 assert 'process_page_fault_anon_allocate_body_result' not in r
 for rel,pre,post in [('kernel/process.c',(ROOT/'kernel/process.c').read_text(),c),('kernel/rust/process_helpers.rs',(ROOT/'kernel/rust/process_helpers.rs').read_text(),r)]:
  put(P/'candidate'/rel,post)
  put(P/'patch'/(Path(rel).name+'.CURRENT-UNION2.diff'),''.join(difflib.unified_diff(pre.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 put(P/'fragments/passed_prepare.ACTUAL-RUST.inc',body)
 put(P/'fragments/F01_offset_PROCESS-ADAPTER.inc',getter)
 put(P/'fragments/original_prepare.ACTUAL-C.inc',original+'\n')
 put(P/'fragments/selected_prepare.ACTUAL-C.inc',selection+'\n')
 put(P/'fragments/static_bounds_metadata.ACTUAL-C.inc',metadata)
 pc=json.loads((OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text())
 headers={}
 for path,row in pc['headers'].items():
  if path.startswith(str(OLD/'source')+'/'):
   dest=P/'source'/Path(path).relative_to(OLD/'source');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest);headers[str(dest)]=pin(dest)
  else:headers[path]=row
 shutil.copy2(P/'candidate/kernel/process.c',P/'source/kernel/process.c')
 witness='''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
#include <page.h>
#include <ihk/debug.h>
extern int process_page_fault_prepare_body_result(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *);
extern long process_page_offset_bridge(void *);
extern off_t page_get_offset(const struct page *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_fault_prepare_body_result),int (*)(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *)),"exact prepare borrowed output ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_offset_bridge),long (*)(void *)),"unchanged offset callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct page *)0)->offset),off_t)&&__builtin_types_compatible_p(long,off_t),"actual signed field/return ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8&&__builtin_offsetof(struct page,offset)==64,"existing F01 Page layout, no new field layout");
_Static_assert(sizeof(struct ddebug)==32&&sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(uint64_t)==8&&sizeof(int)==4,"actual supported metadata/output widths");
_Static_assert(PF_PROT==1&&PF_PATCH==(1UL<<29),"same fault reason masks");
'''
 put(P/'actual-process-ABI.c',witness)
 O=P/'output-production-suffix-1';commands=[]
 for row in pc['commands'][4:11]:
  row=dict(row)
  row['argv']=[a.replace(str(OLD),str(P)).replace(str(P/'actual-process-debug-header-ABI.c'),str(P/'actual-process-ABI.c')).replace(str(P/'output-1'),str(O)) for a in row['argv']]
  row['cwd']=str(O);row['purpose']=SCOPE+' current-union2 C/TU/ABI suffix, one root-owned future Rust object; no native/default claim.';commands.append(row)
 # Full Rust object/source proof is intentionally absent. Root must publish a
 # coherent union3 successor binding before any commands can be released.
 conditional=[
  dict(name='07-root-union3-Rust-and-process-partial-link',argv=['/usr/bin/ld','-r',str(O/'process.c.o'),'__ROOT_UNION3_RUST_OBJECT_NOT_BOUND__','-o',str(O/'process-union3-partial.o')],cwd=str(O)),
  dict(name='08-root-union3-partial-NM',argv=['/usr/bin/nm','-a','-S',str(O/'process-union3-partial.o')],cwd=str(O)),
  dict(name='09-root-union3-partial-ELF',argv=['/usr/bin/readelf','-SWr',str(O/'process-union3-partial.o')],cwd=str(O))]
 for row in conditional:row['purpose']=SCOPE+' allocated production consumer only after genuine root-union3 binding; source/object/proof currently NULL.'
 providers=json.loads((F01/'SOURCE-ONLY-TYPED-PROVIDER-HANDOFF.json').read_text())
 suffix=dict(scope=SCOPE,status='SOURCE_READY_CURRENT_UNION2_PRODUCTION_SUFFIX_REQUIRES_ROOT_UNION3_BINDING',
  canonical_preimages=current,postimages={rel:pin(P/'candidate'/rel) for rel in current},
  root_union2_integration=pin(U/'CANONICAL-INTEGRATION.json'),root_union2_source_merge=pin(U/'SOURCE-MERGE.json'),
  root_union2_full78_manifest=pin(U/'FULL78-SOURCE-MANIFEST.json'),
  F01_typed_provider_handoff=pin(F01/'SOURCE-ONLY-TYPED-PROVIDER-HANDOFF.json'),F01_required_source=providers['candidate'],F01_actual_provider_compile=None,
  ROOT_UNION3_source_merge=None,ROOT_UNION3_full78_source_proof=None,ROOT_UNION3_Rust_object=None,ROOT_UNION3_actual_compile_wholejoin=None,
  root_central_Rust_compile_authority='Root owns exactly one coherent fullcrate compile; this F02 suffix invokes no Rust compiler.',
  passed_prepare96=pin(PASSED),passed_prepare_Rust_body=pin(P/'fragments/passed_prepare.ACTUAL-RUST.inc'),
  headers=headers,current_canonical_headers=pc['canonical_headers'],tools=pc['tools'],ABI_witness=pin(P/'actual-process-ABI.c'),
  actual_C_source=pin(P/'source/kernel/process.c'),bounds_debug_original_current_line=line,
  C_commands=commands,conditional_ROOT_UNION3_partial_commands=conditional,
  exact_algorithms_unchanged='Prepare helper exactly passed96 body; F01 adapter exactly held borrowed read. No nine untested invalidate callbacks or anonymous allocation source port included.',
  allocated_consumer_predicates=[
   'Selected CPP has prepare Rust call and no C offset getter definition; C original prepare block excluded, full original fallback remains under else.',
   'Actual whole C TU defines page_fault_process_memory_range, has no process_page_offset_bridge computation, imports prepare helper; allocated refs to helper occur inside real page_fault_process_memory_range span, observed count recorded.',
   'Bounds descriptor is allocated __verbose32B, exact current original line/flags0/fmtNULL, static file/function pointer relocations0,8.',
   'Genuine root Rust object uniquely defines prepare helper, offset bridge and F01 page_get_offset; source proof must bind exact F02+F01 postimages before link.',
   'Partial uniquely resolves new entries/descriptor; full actual C page-fault caller bytes and complete relocation lists equal Cobject-to-partial, new named helper targets nonempty. Full Rust new entry bytes/complete refs equal object-to-partial; no raw2U or guessed optimized call count.',
   'All actual raw U/provider references retained honestly; other page-fault C tail, lookup C provider and backend/lock callbacks remain debt.'],
  actual_compile=None,actual_C_object=None,actual_partial=None,compiler_jobs=0,CPU_reservations=0,canonical_mutations=0,native_default_credit=False)
 write(P/'EXACT-CURRENT-UNION2-PRODUCTION-SUFFIX.ROOT-UNION3-NULL.json',suffix)
 ready=dict(scope=SCOPE,status='IMMUTABLE_SOURCE_READY_PENDING_ROOT_CENTRAL_UNION3_NOT_EXECUTABLE',
  suffix=pin(P/'EXACT-CURRENT-UNION2-PRODUCTION-SUFFIX.ROOT-UNION3-NULL.json'),
  postimages=suffix['postimages'],root_union2=suffix['root_union2_integration'],
  accepted96=suffix['passed_prepare96'],F01_dependency=suffix['F01_typed_provider_handoff'],
  ROOT_UNION3_source_merge=None,ROOT_UNION3_Rust_object=None,ROOT_UNION3_source_proof=None,actual_result=None,
  requires='Root creates a coherent successor source/object/wholejoin binding and exact execution grant. Do not execute placeholder partial argv or treat NULL as ACK.',
  one_ready_production_suffix=True,compiler_jobs=0,CPU_reservations=0,no_unproven_anonymous_allocation=True,native_default_credit=False)
 write(P/'ROOT-READY.CURRENT-UNION2-PREPARE-AND-F01-CONSUMER.json',ready)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'ROOT-READY.CURRENT-UNION2-PREPARE-AND-F01-CONSUMER.json'),suffix=ready['suffix'],postimages=ready['postimages'],bounds_line=line,compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
