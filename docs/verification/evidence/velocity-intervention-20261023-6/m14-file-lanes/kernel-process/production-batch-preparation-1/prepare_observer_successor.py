"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-approved pre-execution observer correction only; original9d/4df unrun immutable.
"""
from pathlib import Path
import ast,difflib,hashlib,json
P=Path(__file__).resolve().parent;SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def function(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  depth+=(text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]
def main():
 original=P/'run_production_batch_once.py';ready0=P/'EXECUTABLE-READY.NOT-GRANTED.json';assert pin(original)['sha256']=='4df71eb00dc8e62f1a2a410726396fa3c2b1df762137d9b916db67775de030a7';assert pin(ready0)['sha256']=='9d024616970e655e6497c5fa4ca094a8f2669073ae9650c525e7c53d3fb460bb'
 assert not (P/'output-1').exists() and not (P/'actual-production-capture-1').exists() and not (P/'PRODUCTION-FIRST-FAILURE-1.json').exists()
 evidence=P/'PREEXEC-FULLRUST-CALLER-RELOCATION-SOURCE-BLOCKER.json';assert pin(evidence)['sha256']=='953f9d37fa4637657b4de8bf555710fe1edb5895dbae21e698d4fa6eff9d2304'
 current=(P/'source/kernel/rust/process_helpers.rs').read_text();prior=(P.parent/'production-consumer-preparation-1/source/kernel/rust/process_helpers.rs').read_text()
 contexts={}
 for name in ['sync_process_memory_range','process_sync_memory_range_body_result','remap_process_memory_range','process_remap_memory_range_body_result']:
  marker='pub unsafe extern "C" fn '+name+'(';a=function(current,marker);b=function(prior,marker);assert a==b,name;contexts[name]=dict(bytes=len(a.encode()),sha256=hashlib.sha256(a.encode()).hexdigest(),unchanged_from_previous_accepted_dump_fullcrate=True)
 source=function(current,'pub unsafe extern "C" fn process_sync_memory_range_body_result(')
 assert 'let zero_fill =' in source and source.count('if !zero_fill {')==2 and 'let error = visit(' in source and 'process_memobj_ref_direct_result' in source and 'process_memobj_unref_direct_result' in source
 s=original.read_text().replace("READY=P/'EXECUTABLE-READY.NOT-GRANTED.json'","READY=P/'EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json'",1)
 s=s.replace('PRODUCTION-FIRST-FAILURE-1.json','PRODUCTION-OBSERVER-SUCCESSOR-FAILURE-1.json')
 token="_,refs=function(rust,caller);named=[ref for ref in refs if ref['symbol']==target];assert len(named)==1,(caller,named,refs)"
 assert s.count(token)==1;s=s.replace(token,"_,refs=function(rust,caller);named=[ref for ref in refs if ref['symbol']==target];assert named,(caller,named,refs)",1)
 token="named=[ref for ref in arefs if ref['symbol']==target];assert len(named)==1,(caller,named,arefs)"
 assert s.count(token)==1;s=s.replace(token,"named=[ref for ref in arefs if ref['symbol']==target]\n    if source is rust:assert named,(caller,named,arefs)\n    else:assert len(named)==1,(caller,named,arefs)",1)
 token="full_relocations=arefs,named_target_relocations=named)";assert s.count(token)==1;s=s.replace(token,"full_relocations=arefs,named_target_relocations=named,actual_named_target_count=len(named))",1)
 ast.parse(s);driver=P/'run_production_batch_observer_successor_once.py';driver.write_text(s)
 patch=P/'PREEXEC-OBSERVER-SUCCESSOR-ONLY.diff';patch.write_text(''.join(difflib.unified_diff(original.read_text().splitlines(True),s.splitlines(True),fromfile='preserved/run_production_batch_once.py',tofile='run_production_batch_observer_successor_once.py')))
 qualification=dict(scope=SCOPE,status='ROOT_APPROVED_PREEXEC_OBSERVER_ONLY_SUCCESSOR_NO_PRODUCT_OR_EXECUTION_CHANGE',authority='Root approved exact fullcallerbytes plus complete allocated relocation-list object-to-partial equality; Rust named targets nonempty and record actual count, Cvm_range exact1 each/global2 remains. No assumption future optimized count equals prior2.',original_ready=pin(ready0),original_driver=pin(original),retained_actual_two_reference_evidence=pin(evidence),bounded_excerpt=pin(P/'PREEXEC-ACCEPTED-FULLRUST-SYNC-CALLER-REFS.txt'),current_source=pin(P/'source/kernel/rust/process_helpers.rs'),actual_caller_and_owner_identities=contexts,source_branch_context='The unchanged sync owner tests MF_ZEROFILL and conditionally retains/releases memobj around the visit. Previous fullproduction codegen duplicated the callback address across zero-fill/retained-memobj visit paths; standalone consumer had one. New codegen count is observed and reported, not assumed.',exact_preserved_predicates=['Full source/ABI/provider/global T/U checks','All complete caller bytes and full relocation-list equality, including GOT/other address machinery','At least one named target within each actual allocated executable Rust caller span; report every target and count','Exactly one vm_range_insert target per two existing actual C callers and wholepartial2','795 accepted sync evidence reused without replay; remap/log404 remains unrun'],delta=pin(patch),compiler_jobs=0,CPU_reservations=0,original14argv_unchanged=True,product_source_unchanged=True,remap_log404_unrun=True)
 q=P/'ROOT-APPROVED-PREEXEC-OBSERVER-CORRECTION.json';write(q,qualification)
 ready=json.loads(ready0.read_text());ready.update(status='ONE_PROCESS_BATCH_PRODUCTION_PREEXEC_OBSERVER_SUCCESSOR_READY_NO_GRANT_OR_JOB',driver=pin(driver),predecessor_unrun_ready=pin(ready0),predecessor_unrun_driver=pin(original),observer_qualification=pin(q),Rust_caller_target_rule='Nonempty named targets in actual allocated executable function spans, with actual counts recorded. Full bytes and complete relocation equality preserved; no future optimized count assumption.',C_caller_target_rule='Unchanged exact1 vm_range_insert target per actual C caller and wholepartial2.',requires='Root creates ROOT-GRANT.json exact scope/CPU6/ordinary_jobs1 and this successor ready SHA before one granted ordinary job. All14 compiler/tool argv and source/oracles/profile unchanged. First actual unexpected result STOPexpert, no automatic retry.',evidence_bindings=ready['evidence_bindings']+[pin(q),pin(evidence),pin(P/'PREEXEC-ACCEPTED-FULLRUST-SYNC-CALLER-REFS.txt')],compiler_jobs=0,CPU_reservations=0)
 new=P/'EXECUTABLE-READY.OBSERVER-SUCCESSOR.NOT-GRANTED.json';write(new,ready)
 write(P/'ROOT-GRANT.OBSERVER-SUCCESSOR.EXAMPLE-NOT-AUTHORITY.json',dict(scope=SCOPE,CPU=6,ordinary_jobs=1,ready_sha256=pin(new)['sha256']))
 assert pin(original)==qualification['original_driver'] and pin(ready0)==qualification['original_ready']
 print(json.dumps(dict(scope=SCOPE,ready=pin(new),driver=ready['driver'],Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],qualification=pin(q),exact_command=['/home/holden/anaconda3/bin/python3',str(driver)],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
