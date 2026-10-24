"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare one complete GCC9/current78 batch job. No compiler/test/slot/canonical write.
"""
from pathlib import Path
import ast,difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;LANE=P.parent;ROOT=Path('/home/holden/mckernel');OLD=LANE/'production-consumer-preparation-1';UNION=LANE.parents[1]/'root-union-preparation-1';S=P/'source';O=P/'output-1';SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def fix(s,names):
 for name in names:
  old='process_'+name+'_debug.line_flags,';assert s.count(old)==1,old;s=s.replace(old,old[:-1],1)
 return s

def actual_function(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def main():
 oldr=json.loads((OLD/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json').read_text());oldc=json.loads((OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json').read_text())
 sync=LANE/'next-sync-one-page/bounded-source-correction-1';sr=sync/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json';assert pin(sr)['sha256']=='4e2d6368b15099b7c0b643b0051dfee419c6696840608793e52872953308e0d3';sactual=json.loads(sr.read_text());assert sactual['actual_commands']==16 and sactual['actual_original_C_Rust_comparisons']==795
 batch=LANE/'batch-source-preparation-1';pre_r=batch/'candidate/kernel/rust/process_helpers.rs';pre_c=batch/'candidate/kernel/process.c';assert pin(pre_r)['sha256']=='49f61c90967bf2d79324cbec946b3c22931b79d54638abf8fb3c647bf679b9b2';assert pin(pre_c)['sha256']=='7ab29dad607ac06e9548065f4395c6e870359558a2777844c1052d67e046ca13'
 corrected=fix(pre_r.read_text(),['sync_one_page_entry','sync_one_page_exit']);corrected=fix(corrected,['remap_one_page_entry','remap_one_page_rss','remap_one_page_exit'])
 assert actual_function((sync/'fixture/sync.ACTUAL-RUST-BODY.inc').read_text(),'pub unsafe extern "C" fn sync_one_page(')==actual_function(corrected,'pub unsafe extern "C" fn sync_one_page(')
 assert corrected.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 (P/'candidate/kernel/rust').mkdir(parents=True);(P/'patch').mkdir();(P/'fixture').mkdir()
 (P/'candidate/kernel/rust/process_helpers.rs').write_text(corrected);shutil.copy2(pre_c,P/'candidate/kernel/process.c')
 remap_template=LANE/'next-remap-one-page/sourcehandoff/prepare_source.py';(P/'fixture/prepare_remap.CORRECTED-TEMPLATE-NOT-EXECUTED.py').write_text(fix(remap_template.read_text(),['remap_one_page_entry','remap_one_page_rss','remap_one_page_exit']))
 remap_body=LANE/'next-remap-one-page/fixture/remap.ACTUAL-RUST.inc';(P/'fixture/remap.CORRECTED-RUST.inc').write_text(fix(remap_body.read_text(),['remap_one_page_entry','remap_one_page_rss','remap_one_page_exit']))
 shutil.copy2(sync/'fixture/sync.ACTUAL-RUST-BODY.inc',P/'fixture/sync.ACCEPTED-RUST.inc')
 for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']:
  original=(ROOT/rel).read_text();post=(P/'candidate'/rel).read_text();(P/'patch'/(Path(rel).name+'.CURRENT-CANONICAL.diff')).write_text(''.join(difflib.unified_diff(original.splitlines(True),post.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 (P/'patch/ONLY-FIVE-KNOWN-MACRO-COMMAS.diff').write_text(''.join(difflib.unified_diff(pre_r.read_text().splitlines(True),corrected.splitlines(True),fromfile='preserved-uncompiled-batch49f/process_helpers.rs',tofile='accepted-sync-plus-remap-syntax-correction/process_helpers.rs')))
 nm=UNION/'actual-six-C-partial-1/0/stdout';assert pin(nm)['sha256']=='bcc898048fb3d4f91a0746b9701a57de2710f30a4adeb7417eada0749f95a586';ncmd=json.loads((nm.parent/'command.json').read_text());assert ncmd['argv']==['/usr/bin/nm','-a','-S',str(UNION/'mckernel_rust.union.o')]
 rows=[l.split() for l in nm.read_text().splitlines() if l.split()];T={x[-1] for x in rows if x[-2]=='T'};U={x[-1] for x in rows if x[-2]=='U'};assert len(T)==3065 and len(U)==572
 addT=['process_sync_range_log_bridge','remap_one_page','sync_one_page'];addU=['process_remap_free_file','process_remap_free_line','process_remap_one_page_entry_debug','process_remap_one_page_exit_debug','process_remap_one_page_rss_debug','process_sync_one_page_entry_debug','process_sync_one_page_exit_debug'];assert set(addT)<=U and not set(addT)&T and not set(addU)&U and 'phys_to_page' in U
 S.mkdir();inputs={};changed=[]
 for key,row in sorted(oldr['source_inputs'].items()):
  canonical=pin(ROOT/key);accepted=pin(UNION/'source'/key);assert canonical['sha256']==accepted['sha256'] and canonical['bytes']==accepted['bytes'],('canonical drift from acceptedunion',key)
  take=P/'candidate/kernel/rust/process_helpers.rs' if key=='kernel/rust/process_helpers.rs' else ROOT/key;dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(take,dest)
  inputs[key]=dict(accepted_before=accepted,canonical_before=canonical,private=pin(dest),modified_target=key=='kernel/rust/process_helpers.rs')
  if inputs[key]['private']['sha256']!=accepted['sha256']:changed.append(key)
 assert changed==['kernel/rust/process_helpers.rs'] and len(inputs)==78
 assert inputs['kernel/rust/process_helpers.rs']['canonical_before']['sha256']=='70015d712c29e416881e2fbaccd67026ee15ac7eb915cb80e828485d6f34d71f'
 identity_rows=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in inputs.items()];identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
 accepted_refs=[pin(UNION/name) for name in ['CANONICAL-INTEGRATION.json','SOURCE-MERGE.json','RUST-COMMAND.json','actual-rust-union-1/RESULT.json','actual-six-C-partial-1/RESULT.json','actual-six-C-partial-1/0/command.json']]
 failure=dict(first_sync_source_failure=pin(LANE/'next-sync-one-page/sourcehandoff/PREFLIGHT-SUCCESSOR-FAILURE-1.json'),first_sync_stderr=pin(LANE/'next-sync-one-page/sourcehandoff/actual-first-candidate-capture-1/00-actual-Rust-fixture-body/stderr'),bounded_sync_accepted=pin(sr),known_remap_three_commas='Only the same known macro grammar correction; original uncompiled body7143/batchcd39 retained. No algorithm/compiler/vector change.',prior_dump_observer='c774 preserved with accepted84ef/e48c named-target correction',prior_E0428='2fb3/e9a retained; corrected accepted7a; existing kprintf declaration reused once',history_not_reset=True,next_unexpected_result='STOP_EXPERT_ESCALATION_NO_AUTOMATIC_CORRECTION_OR_RETRY')
 r=dict(oldr);r.update(status='COHERENT_CURRENT78_THREE_NEW_PROCESS_BODIES_SOURCE_READY_NO_GRANT',source_inputs=inputs,source_identity_rows=identity_rows,source_identity=identity,accepted_prior_Rust_symbols=pin(nm),accepted_prior_whole_join=pin(UNION/'actual-rust-union-1/RESULT.json'),accepted_prior_Rust_recipe=pin(UNION/'RUST-COMMAND.json'),accepted_union_refs=accepted_refs,only_private_override_from_current=changed,argv=[a.replace(str(OLD),str(P)) for a in oldr['argv']],expected_T_delta=dict(removed=[],added=sorted(addT),before=len(T),after=len(T)+3),expected_U_delta=dict(removed=sorted(addT),added=sorted(addU),before=len(U),after=len(U)-3+7),target_callbacks=addT,symbol_delta_source_basis='Exact accepted canonicalunion bareRust nm -a -S capture bcc89804: global T3065/U572; three actual C callbacks become Rust T and leave U; seven new C metadata data imports only. phys_to_page already an existing U and remains explicit debt.',failure_history=failure,accepted_sync795=pin(sr),canonical_refresh='All78 exactcurrentcanonical inputs match accepted integratedrootunion sources; process-only privatebatch override includes canonicaldump plus acceptedcorrectedsync and originalrange/remap with three knownremap grammar fixes.')
 assert [i for i,(a,b) in enumerate(zip(r['argv'],oldr['argv'])) if a!=b]==[46,47]
 write(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json',r)
 headers={};ch={}
 for key,row in oldc['canonical_headers'].items():
  now=pin(ROOT/key);assert now==row,('headerdrift',key);dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT/key,dest);headers[str(dest)]=pin(dest);ch[key]=now
 for name,row in oldc['headers'].items():
  if not name.startswith(str(OLD/'source')+'/'):assert pin(Path(name))==row;headers[name]=row
 assert len(headers)==73
 shutil.copy2(P/'candidate/kernel/process.c',S/'kernel/process.c');assert pin(ROOT/'kernel/process.c')['sha256']=='1ecbc287f2e704e738cc4e9fbe18289226b5aadadc9da88d226dc0ad0bb57234'
 witness=(OLD/'actual-process-debug-header-ABI.c').read_text()+'''#include <memobj.h>
#include <rusage_private.h>
struct actual_rfp_args { off_t off; uintptr_t start; struct memobj *memobj; };
extern int sync_one_page(void *,page_table_t,pte_t *,void *,int);
extern int remap_one_page(void *,page_table_t,pte_t *,void *,int);
extern void process_sync_range_log_bridge(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int);
typedef int (*actual_visit_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&sync_one_page),actual_visit_t)&&__builtin_types_compatible_p(__typeof__(&remap_one_page),actual_visit_t),"exact original five-argument visitor ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sync_range_log_bridge),void (*)(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int)),"exact range logger ABI");
_Static_assert(sizeof(struct actual_rfp_args)==24&&__alignof__(struct actual_rfp_args)==8&&__builtin_offsetof(struct actual_rfp_args,off)==0&&__builtin_offsetof(struct actual_rfp_args,start)==8&&__builtin_offsetof(struct actual_rfp_args,memobj)==16,"existing actual ProcessRemapArgs ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8,"actual existing Page provider ABI; remap accesses no Page fields");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page *(*)(uintptr_t)),"explicit existing C forwarding provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void (*)(void *,int,int,char *,int)),"exact tracked free signature/static file lifetime");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),void (*)(struct memobj *,unsigned long,int)),"original RSS size_t to int conversion boundary");
_Static_assert(IHK_MC_PG_USER==1,"original user-page accounting mode");
'''
 (P/'actual-process-debug-header-ABI.c').write_text(witness)
 c=dict(oldc);c.update(status='COMPLETE_GCC9_PROCESS_THREE_NEW_RUST_BODIES_SOURCE_READY_NO_GRANT',accepted_prior_complete_C_profile=pin(OLD/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),accepted_prior_whole_join=pin(OLD/'bounded-observer-correction-1/ACTUAL-OBSERVER-WHOLE-JOIN.json'),selected_C_argv=[a.replace(str(OLD),str(P)) for a in oldc['selected_C_argv']],private_source=pin(S/'kernel/process.c'),canonical_preimage=pin(ROOT/'kernel/process.c'),headers=headers,canonical_headers=ch,ABI_witness=pin(P/'actual-process-debug-header-ABI.c'),commands=[dict(row,argv=[a.replace(str(OLD),str(P)) for a in row['argv']],cwd=str(O),purpose=SCOPE+' '+row['name']+'; complete selected GCC9/current78 source batch only; no default image/native claim.') for row in oldc['commands']],retired_C_compute=['sync_one_page','remap_one_page','process_sync_range_log_bridge'],metadata_lines={'process_vm_range_insert_debug':2086,'process_sync_one_page_entry_debug':2546,'process_sync_one_page_exit_debug':2574,'process_remap_one_page_entry_debug':2448,'process_remap_one_page_rss_debug':2470,'process_remap_one_page_exit_debug':2476},tracked_free_line=2469,expected_partial='Unique Rust callback/export definitions, original actual Rust sync/remap caller bytes and full relocation lists preserved with one named visitor target each in allocated executable sections; existing two C vm_range_insert targets retained; C static metadata allocated and pointer relocations retained. Other whole-tree U honestly retained, including phys_to_page C provider.',failure_history=failure,accepted_sync795=pin(sr),expected_C_symbols='Retired three C function definitions and all allocated C target relocations absent; seven new typed metadata objects only, original dump gate/debug descriptor preserved. Debug-only rows/relocations do not imply live C computation.',allocated_relocation_rule='Require/compare only named function-span targets and allocated section relocations for runtime ownership; keep all complete raw rows and function relocation lists. No total-relocation cardinality or two-U oracle.')
 write(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json',c)
 write(P/'SOURCE-BATCH-AND-ACCEPTED-SYNC-QUALIFICATION.json',dict(scope=SCOPE,status='SOURCE_ONLY_CURRENT_CANONICAL_DUMP_PLUS_THREE_PRIVATE_PORTS',current_canonical={rel:pin(ROOT/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},private_postimages={rel:pin(P/'candidate'/rel) for rel in ['kernel/process.c','kernel/rust/process_helpers.rs']},accepted795=pin(sr),accepted_dump=pin(OLD/'bounded-observer-correction-1/OBSERVER-RESULT.json'),original_uncompiled_batch=pin(pre_r),syntax_only_delta=pin(P/'patch/ONLY-FIVE-KNOWN-MACRO-COMMAS.diff'),three_remap_syntax_fixes_and_accepted_sync_two=True,existing_C_provider_debt='Public phys_to_page C forwarding function, underlying lock/log/backend callbacks remain; native/default provider closure unproven by this job.',retained_data_debt='Original dump gate, VM insert debug, two sync debug, three remap debug and tracked-free filename/line static C objects.',fixture_replay=False,new_fixture_commands=0,compiler_jobs=0,CPU_reservations=0,source_correctness_claim=False,fullimage_native_claim=False))
 print(json.dumps(dict(scope=SCOPE,Rust=pin(P/'EXACT-CURRENT78-RUST-RECIPE.NOT-GRANTED.json'),C=pin(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-GRANTED.json'),source_identity=identity,post_Rust=pin(P/'candidate/kernel/rust/process_helpers.rs'),expected_T_delta=r['expected_T_delta'],expected_U_delta=r['expected_U_delta'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
