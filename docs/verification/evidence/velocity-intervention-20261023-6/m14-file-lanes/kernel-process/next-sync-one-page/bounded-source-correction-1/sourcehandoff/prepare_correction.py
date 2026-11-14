"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Sole bounded source correction for Rust1.92 addr_of trailing-comma grammar.
Prepare only; original source/ready/failures are immutable and no job is run.
"""
from pathlib import Path
import ast,difflib,hashlib,json,shutil
B=Path(__file__).resolve().parents[1];H=B/'sourcehandoff';OLD=B.parent;OH=OLD/'sourcehandoff';ROOT=Path('/home/holden/mckernel');SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def correct(s):
 for name in ('entry','exit'):
  token='process_sync_one_page_'+name+'_debug.line_flags,';assert s.count(token)==1;s=s.replace(token,token[:-1],1)
 return s

def main():
 first=OH/'PREFLIGHT-SUCCESSOR-FAILURE-1.json';stderr=OH/'actual-first-candidate-capture-1/00-actual-Rust-fixture-body/stderr';outer=OH/'root-actual-sync-preflight-successor-1/RESULT.json';rf=OH/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json';original_driver=OH/'run_owned_preflight_successor_once.py';oldready=OH/'EXECUTABLE-READY.PREFLIGHT-SUCCESSOR.NOT-GRANTED.json'
 assert pin(first)['sha256']=='0d9014ccab0f3df777cf250d44e61c0f2558361e5307f60e24d5ac976f3b1885';assert pin(stderr)['sha256']=='04931f5e28951a781b9f7939fc453385f133dda2ac04eec56dd9b785482f6c80';assert pin(rf)['sha256']=='1391be5c805be84a46e570d70c5e680ce26f3173c33504ad948205afffa2475d'
 failure=json.loads(first.read_text());assert len(failure['records'])==1 and failure['durable_objects']=={} and failure['CPU6_released'];join=failure['records'][0]['join'];assert join['returncode']==1 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams'] and join['error'] is None and join['retirement_error'] is None
 canonical={'kernel/process.c':pin(ROOT/'kernel/process.c'),'kernel/rust/process_helpers.rs':pin(ROOT/'kernel/rust/process_helpers.rs')};assert canonical['kernel/process.c']['sha256']=='1ecbc287f2e704e738cc4e9fbe18289226b5aadadc9da88d226dc0ad0bb57234';assert canonical['kernel/rust/process_helpers.rs']['sha256']=='70015d712c29e416881e2fbaccd67026ee15ac7eb915cb80e828485d6f34d71f'
 recipe=json.loads(rf.read_text());assert len(recipe['commands'])==16
 (B/'candidate/kernel/rust').mkdir(parents=True);(B/'patch').mkdir();shutil.copytree(OLD/'fixture',B/'fixture')
 shutil.copy2(OLD/'candidate/kernel/process.c',B/'candidate/kernel/process.c');oldrust=OLD/'candidate/kernel/rust/process_helpers.rs';post=correct(oldrust.read_text());(B/'candidate/kernel/rust/process_helpers.rs').write_text(post)
 changes=[]
 for rel in ['candidate/kernel/rust/process_helpers.rs','fixture/sync.ACTUAL-RUST-BODY.inc','fixture/actual_provider.rs','fixture/hosted_production_leaf_provider.rs']:
  before=(OLD/rel).read_text();after=correct(before)
  if rel.startswith('fixture/'):(B/rel).write_text(after)
  assert after.replace('process_sync_one_page_entry_debug.line_flags\n','process_sync_one_page_entry_debug.line_flags,\n',1).replace('process_sync_one_page_exit_debug.line_flags\n','process_sync_one_page_exit_debug.line_flags,\n',1)==before
  changes.append(dict(relative=rel,before=pin(OLD/rel),after=pin(B/rel),removed_bytes=2,only_two_commas=True))
  (B/'patch'/(Path(rel).name+'.ONLY-TWO-COMMAS.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='preserved-failed/'+rel,tofile='bounded-correction/'+rel)))
 template=correct((OH/'prepare_sync_source.py').read_text());(H/'prepare_sync_source.CORRECTED-TEMPLATE-NOT-EXECUTED.py').write_text(template)
 # Constructor template is preserved as source derivation evidence; the bounded
 # corrector above materializes this exact packet, so no old producer is rerun.
 (H/'template-qualification.txt').write_text(SCOPE+'\nArchived original generator template with only the same two commas removed; not executed or relocated as a producer. All other bytes unchanged.\n')
 for rel in canonical:
  before=(ROOT/rel).read_text();after=(B/'candidate'/rel).read_text();(B/'patch'/(Path(rel).name+'.CURRENT-CANONICAL-TO-CORRECTED.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
 # Source body and both fixtures are the identical corrected algorithm, with
 # only the accepted standalone fixture entry renaming in actual_provider.rs.
 body=(B/'fixture/sync.ACTUAL-RUST-BODY.inc').read_text();assert body in post
 assert body.replace('fn sync_one_page(','fn fixture_rust_sync_one_page(',1) in (B/'fixture/actual_provider.rs').read_text();assert body in (B/'fixture/hosted_production_leaf_provider.rs').read_text()
 assert pin(B/'candidate/kernel/process.c') ['sha256']==pin(OLD/'candidate/kernel/process.c')['sha256']
 assert post.count('    fn kprintf(format: *const i8, ...) -> CInt;')==1
 histories=[pin(first),pin(stderr),pin(outer),pin(original_driver),pin(oldready),pin(OH/'FIRST-CANDIDATE-FAILURE-1.json'),pin(OH/'root-actual-sync-first-1/RESULT.json'),pin(OH/'ROOT-GRANT.json')]
 for record in failure['records']:
  histories.append(pin(Path(record['command']['path'])))
  for row in record['join']['captures'].values():histories.append(pin(Path(row['path'])))
 history=dict(scope=SCOPE,family='Rust1.92_addr_of_macro_trailing_comma',first_real_compiler_failure=pin(first),first_compiler_stderr=pin(stderr),first_root_outer_join=pin(outer),first_failed_compiler_commands=1,bounded_source_corrections_prepared=1,bounded_source_corrections_executed=0,missing_grant_setup_historical_separate=pin(OH/'FIRST-CANDIDATE-FAILURE-1.json'),prior_E0428_family_preserved='2fb3/e9a correctedaccepted7a; no new kprintf declaration',next_unexpected_result='STOP_EXPERT_ESCALATION_NO_FURTHER_CORRECTION_OR_THIRD_COMPILE')
 source_relation=dict(scope=SCOPE,status='EXACT_CURRENT_ACCEPTED_CANONICAL_DUMP_TO_CORRECTED_SYNC_RELATION',authority='Root reports independently reviewed11-file canonical union integrated; process1ecbc287/process_helpers70015d71 are accepted dump-only canonical. Older08c/d04 references remain historical preimages, not current assertions.',current_canonical_preimages=canonical,corrected_postimages={rel:pin(B/'candidate'/rel) for rel in canonical},original_failed_candidate=pin(oldrust),source_delta=changes,corrected_generator_template=pin(H/'prepare_sync_source.CORRECTED-TEMPLATE-NOT-EXECUTED.py'),C_algorithm_and_fallback_unchanged=True,Rust_algorithm_signature_oracles_unchanged=True,original795_comparisons_still_planned=True,source_correctness_claim=False)
 write(H/'SOURCE-CORRECTION-AND-CURRENT-CANONICAL-RELATION.json',source_relation)
 # New source/output/capture roots only. Never reuse failed output/attempts.
 commands=[]
 for row in recipe['commands']:
  argv=[arg.replace(str(OLD),str(B)) for arg in row['argv']];assert len(argv)==len(row['argv'])
  for before,after in zip(row['argv'],argv):assert before==after or before.startswith(str(OLD)) and after==before.replace(str(OLD),str(B))
  commands.append(dict(row,argv=argv,cwd=str(B/'output-first-candidate-1')))
 bindings={}
 for rel,row in recipe['input_bindings'].items():
  assert pin(Path(row['path']))==row,row['path']
  if rel.startswith(('candidate/','fixture/')):bindings[rel]=pin(B/rel)
  else:bindings['preserved-derivation/'+rel]=row
 bindings['bounded-source-corrector']=pin(Path(__file__));bindings['corrected-derivation-template']=pin(H/'prepare_sync_source.CORRECTED-TEMPLATE-NOT-EXECUTED.py');bindings['current-canonical-relation']=pin(H/'SOURCE-CORRECTION-AND-CURRENT-CANONICAL-RELATION.json')
 updated=dict(recipe);updated.update(status='SOLE_BOUNDED_ADDR_OF_SOURCE_CORRECTION_FROZEN_NO_GRANT',commands=commands,input_bindings=bindings,current_canonical_source_preimages=canonical,failure_history=history,predecessor_recipe=pin(rf),only_source_algorithm_delta='Remove only unsupported trailing comma from each sync entry/exit addr_of place expression; no new behavior, compiler flags, ABI, fixture vector or oracle.',old_command_namespace_never_reused=True)
 newrf=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.BOUNDED-CORRECTION.NOT-GRANTED.json';write(newrf,updated)
 driver=original_driver.read_text().replace("RF=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.NOT-GRANTED.json'","RF=H/'EXACT-FUNCTIONAL-FIXTURE-AND-CONSUMER.BOUNDED-CORRECTION.NOT-GRANTED.json'",1).replace("READY=H/'EXECUTABLE-READY.PREFLIGHT-SUCCESSOR.NOT-GRANTED.json'","READY=H/'EXECUTABLE-READY.BOUNDED-CORRECTION.NOT-GRANTED.json'",1)
 driver=driver.replace('PREFLIGHT-SUCCESSOR-FAILURE-1.json','BOUNDED-SOURCE-CORRECTION-FAILURE-1.json').replace('STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY','STOP_EXPERT_ESCALATION_NO_FURTHER_CORRECTION_OR_THIRD_COMPILE')
 marker=" for row in [*r['input_bindings'].values(),*r['tools'].values(),";assert driver.count(marker)==1;driver=driver.replace(marker," for row in [*r['current_canonical_source_preimages'].values(),*r['input_bindings'].values(),*r['tools'].values(),",1)
 ast.parse(driver);dp=H/'run_owned_bounded_source_correction_once.py';dp.write_text(driver)
 (B/'patch/DRIVER-BOUND-CORRECTION.diff').write_text(''.join(difflib.unified_diff(original_driver.read_text().splitlines(True),driver.splitlines(True),fromfile='preserved/run_owned_preflight_successor_once.py',tofile='run_owned_bounded_source_correction_once.py')))
 ready=json.loads(oldready.read_text());ready.update(status='SOLE_BOUNDED_SYNC_ADDR_OF_SOURCE_CORRECTION_READY_NO_GRANT_OR_JOB',recipe=pin(newrf),driver=pin(dp),source_body=pin(H/'SOURCE-CORRECTION-AND-CURRENT-CANONICAL-RELATION.json'),source_dependencies='Current accepted canonical dump1ec/700 to this corrected sync-only successor; no stale08c/d04 current assertion.',postimages=source_relation['corrected_postimages'],preflight_history_bindings=histories,setup_qualification=pin(H/'SOURCE-CORRECTION-AND-CURRENT-CANONICAL-RELATION.json'),predecessor_missing_grant_failure=pin(OH/'FIRST-CANDIDATE-FAILURE-1.json'),supersedes_execution_ready_only=pin(oldready),historical_preflight_no_source_failure=True,first_real_source_failure=pin(first),failure_history=history,successor_failure_path=str(H/'BOUNDED-SOURCE-CORRECTION-FAILURE-1.json'),unchanged16argv=False,unchanged16argv_except_fresh_source_output_paths=True,unchanged_source_and_oracles=False,only_two_removed_macro_commas=True,oracles_and_795_vectors_unchanged=True,current_canonical_preconditions=canonical,requires='Root creates this namespace sourcehandoff/ROOT-GRANT.json bound to exact newready/scope/CPU6/ordinary_jobs1 before sole bounded attempt. Fresh admission and h990/AST checks remain; first further unexpected result escalates without another correction/compile.',compiler_jobs=0,CPU_reservations=0)
 newready=H/'EXECUTABLE-READY.BOUNDED-CORRECTION.NOT-GRANTED.json';write(newready,ready)
 write(H/'ROOT-GRANT.BOUNDED-CORRECTION.EXAMPLE-NOT-AUTHORITY.json',dict(scope=SCOPE,CPU=6,ordinary_jobs=1,ready_sha256=pin(newready)['sha256']))
 write(H/'DOWNSTREAM-UNCOMPILED-SOURCE-QUALIFICATION.json',dict(scope=SCOPE,old_batch='cd392790 source-only four-body batch remains immutable and uncompiled',known_blocker='It inherits the two failed sync addr_of trailing commas and remap has three analogous trailing commas. Before future fullbatch compile, root must consume corrected sync and adopt corresponding source-only remap grammar correction; no fullbatch ready or proof exists.',downstream_sources_changed=False,compiler_jobs=0,CPU_reservations=0))
 for row in histories:assert pin(Path(row['path']))==row
 print(json.dumps(dict(scope=SCOPE,ready=pin(newready),recipe=pin(newrf),driver=pin(dp),source_relation=pin(H/'SOURCE-CORRECTION-AND-CURRENT-CANONICAL-RELATION.json'),postimages=ready['postimages'],exact_command=['/home/holden/anaconda3/bin/python3',str(dp)],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
