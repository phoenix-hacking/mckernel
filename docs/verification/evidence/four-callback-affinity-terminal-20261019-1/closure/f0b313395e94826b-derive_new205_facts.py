"""New205-only mechanical joins over the exact fifteen completed captures.
No decoder/tool/root/copy execution. Independent optimized-source association is
required as a separately pinned actual-data report; it is never inferred from a
source function string or inherited03a witness offsets.
"""
from pathlib import Path
import hashlib,importlib.util,json,re,sys
B=Path(__file__).resolve().parent;A=B.parent
ALGORITHM=Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/terminal-preparation-1/remaining-only-late-binding-1/facts-correction-1/postbuild_future_facts_corrected.py')
ALGORITHM_SHA='380e4d8c7ac1360a2694a34cb037c748bdaa31948da7948686add983f5b825fe'
REQUEST_SHA='902f482227f3510c86a2624fa9f255abb3d0c82996191f4e3ca4c227877765f8'
SYMBOLS=('sched_clone_affinity_snapshot_result','sched_clone_affinity_inherit_result','sched_setaffinity_body_result','process_clone_thread_base_state_body_result')
def checked(ref):
 data=Path(ref['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==ref['sha256'] and ('bytes' not in ref or len(data)==ref['bytes']);return data
def load(ref):return json.loads(checked(ref))
def main():
 assert len(sys.argv)==4,'bindingpath bindingsha256 freshfactsoutput'
 raw=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[2];x=json.loads(raw);assert x['schema']=='mckernel.new205.actual-fifteen-facts-bindings.v1' and x['request']['sha256']==REQUEST_SHA
 request=load(x['request']);assert request['source_root']==str(A/'materialized-source')
 boundary=json.loads((B/'AFFINITY-PRODUCTION-BOUNDARY-EXACT.json').read_bytes())
 for name,pin in boundary['actual_source_pins'].items():assert hashlib.sha256((Path(request['source_root'])/name).read_bytes()).hexdigest()==pin['sha256']
 assert hashlib.sha256(ALGORITHM.read_bytes()).hexdigest()==ALGORITHM_SHA
 spec=importlib.util.spec_from_file_location('new205_completed_capture_primitives',ALGORITHM);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
 release=load(x['resolved_release']);m=old.base_adapter(x['accepted_base_facts_source'],release['descriptor_facts_producer'])
 plan,captures,completion=m.validate_completion(Path(x['plan']['path']),x['plan']['sha256'],Path(x['resolved_release']['path']),x['resolved_release']['sha256'],Path(x['completion']['path']),x['completion']['sha256'])
 assert len(plan['operations'])==15 and release['request']=={'path':x['request']['path'],'sha256':REQUEST_SHA,'bytes':x['request']['bytes']}
 compiler=x['compiler_boundary'];assert set(compiler)=={'process_checks','affinity_checks','full_crates','layout_vectors'}
 assert compiler['process_checks']['path']==str(A/'owner-work/evidence/release-tid-production-checks.json') and compiler['affinity_checks']['path']==str(A/'owner-work/evidence/clone-affinity-production-checks.json')
 process=load(compiler['process_checks']);affinity=load(compiler['affinity_checks'])
 assert process['status']=='PASS' and process['actual_C_ABI_assertions']==110 and process['full_native_legacy_crates_reused'] is True and all(r['exit_code']==0 for r in process['checks'])
 assert affinity['status']=='PASS' and affinity['layout_cells']==27 and affinity['actual_syscall_C_assertions_selected']==10 and affinity['actual_syscall_C_assertions_fallback']==8 and affinity['old_compiled_inputs_adopted'] is False and affinity['fresh_native_legacy_fullcrates_reused_once'] is True and set(affinity['symbols'])==set(SYMBOLS) and all(r['exit_code']==0 for r in affinity['checks'])
 assert set(compiler['full_crates'])=={'native','legacy'} and set(compiler['layout_vectors'])=={'selected-syscall','fallback-syscall','actual-rust-layout'}
 for mode,ref in compiler['full_crates'].items():
  assert ref['path']==str(A/'owner-work/output/build/release-fp-regs-production'/(mode+'-mckernel_rust.o'));checked(ref)
 layouts=[]
 for name,ref in compiler['layout_vectors'].items():
  assert ref['path']==str(A/'owner-work/output/build/clone-affinity-production'/(name+'.bin'));blob=checked(ref);assert len(blob)==216;layouts.append(blob)
 assert layouts[0]==layouts[1]==layouts[2] and hashlib.sha256(layouts[0]).hexdigest()==affinity['layout_bytes_sha256']
 # Unique exports and selected/fallback C semantics remain the actual C110 proof's
 # responsibility. These are independent final-image/full-Rust observations.
 for symbol in SYMBOLS:
  for index in (7,10):
   rows=m.nm_rows(captures[index]);assert len([r for r in rows if r[2]==symbol and r[1]=='T'])==1 and not [r for r in rows if r[2]==symbol and r[1]=='U']
 callbacks=old.actual_callback_facts(m,captures)
 nms={kind:m.nm_rows(captures[i]) for kind,i in [('selected',1),('fallback',4),('rust',7),('image',10)]}
 for symbol in ('__release_tid','__find_and_replace_tid','process_destroy_thread_time_account_bridge','process_destroy_thread_hash_detach_bridge'):
  for kind,rows in nms.items():
   assert len([r for r in rows if r[1]=='T' and r[2]==symbol])==(0 if kind=='selected' else 1)
   assert len([r for r in rows if r[1]=='U' and r[2]==symbol])==int(kind=='selected' and symbol in ('__release_tid','__find_and_replace_tid'))
  assert not re.search(r'\b(?:[xyz]mm[0-9]+|st\([0-7]\)|xsave\w*|xrstor\w*)\b',m.body(captures[8],symbol))
 source=(Path(request['source_root'])/'kernel/rust/process_helpers.rs').read_text()
 body=re.search(r'pub unsafe extern "C" fn release_process\(proc: \*mut Process\) \{\n(.*?)\n\}',source,re.S);assert body
 arguments=body[1].split('process_release_process_body_result(',1)[1].rsplit(');',1)[0];arguments=[line.strip().rstrip(',') for line in arguments.splitlines() if line.strip()]
 assert len(arguments)==18 and all(arguments[index]=='Some('+symbol+')' for symbol,index in zip(old.SYMBOLS,old.ARGUMENT_INDICES))
 source_argument_map=dict(zip(old.SYMBOLS,old.ARGUMENT_INDICES))
 # Derive size and relocation cardinality from THIS actual ELF symbol/body;
 # keep complete relocated-object == linked-image byte comparison.
 projections=[]
 for symbol,disasm,symbols in [('release_process',8,9),('process_destroy_thread_release_tid_bridge',2,3),('process_destroy_thread_replace_tid_bridge',2,3)]:
  start,size=old.function_symbol(captures[symbols],symbol);_,relocs,_=old.raw_function(m,captures[disasm],symbol,start,size)
  proof,_=old.projected_body(m,captures,symbol,disasm,symbols,size,len(relocs));projections.append(proof)
 descriptors=old.descriptor_facts(m,captures,{o['index']:o for o in plan['operations']})
 assert x['image_disassembly']['path']==next(o['stdout_path'] for o in plan['operations'] if o['index']==11) and checked(x['image_disassembly']).decode()==captures[11]
 association=load(x['independent_source_associations'])
 assert association['schema']=='mckernel.new205.independent-linked-source-associations.v1' and association['decision']=='PASS_NEW205_LINKED_SOURCE_ASSOCIATIONS'
 assert association['implementation_ownership'] is False and association['reviewer'] not in ('rust_next_teardown_leaf','/root/rust_next_teardown_leaf')
 assert association['request']==x['request'] and association['completion']==x['completion'] and association['image_disassembly']==x['image_disassembly'] and association['actual_source_pins']==boundary['actual_source_pins']
 expected={SYMBOLS[0]:'do_fork',SYMBOLS[1]:'do_fork',SYMBOLS[2]:'sys_sched_setaffinity',SYMBOLS[3]:'clone_thread'};witnesses=association['affinity_default_linked_callers'];assert len(witnesses)==4 and {w['target'] for w in witnesses}==set(SYMBOLS)
 for witness in witnesses:
  caller=witness['caller'];assert caller==expected[witness['target']]
  start,size=old.function_symbol(captures[12],caller);data,relocs,instructions=old.raw_function(m,captures[11],caller,start,size);assert not relocs
  assert witness['image_start']==start and witness['size']==size and witness['body_sha256']==hashlib.sha256(data).hexdigest()
  target=next(r for r in m.nm_rows(captures[10]) if r[2]==witness['target'] and r[1]=='T');assert int(target[0])==witness['target_address']
  call=witness['callsite'];assert instructions[call['offset']]==call['instruction'] and re.match(r'^(callq?|jmpq?)\b',call['instruction'])
  assert call['decoded_target']==witness['target_address']
  # Any indirect target/register dataflow is separately independently decoded;
  # all recorded instructions must exist verbatim inside the exact hashed body.
  for row in call['register_dataflow']:assert instructions[row['offset']]==row['instruction']
 assert association['whole_optimized_four_callback_source_association']['order']==['current_resource_set','hash_detach','sibling_detach','final_cleanup']
 assert association['whole_optimized_four_callback_source_association']['linked_body_sha256']==projections[0]['linked_bytes_sha256']
 result={'schema':'mckernel.new205.actual-fifteen-mechanical-facts.v1','status':'PASS_NEW205_FIFTEEN_COMPLETION_AND_MECHANICAL_FACTS_ONLY','phase':'complete_mechanical_postbuild','request':x['request'],'completion':x['completion'],'compiler_boundary':x['compiler_boundary'],'independent_source_associations':x['independent_source_associations'],'actual_source_pins':boundary['actual_source_pins'],'four_callbacks':callbacks,'source_argument_map':source_argument_map,'relocated_body_projections':projections,'descriptors':descriptors,'affinity_default_linked_callers':witnesses,'original_full_syscall_DWARF_gap':'OPEN_NO_REPLAY_NO_WAIVER','production_artifact_acceptance':False,'native_acceptance':False,'compute_C_retirement':False}
 with Path(sys.argv[3]).open('x') as f:json.dump(result,f,sort_keys=True,indent=2);f.write('\n')
 print('PASS new20515completion+mechanicalfacts only; no native/physical/retirement credit')
if __name__=='__main__':main()
