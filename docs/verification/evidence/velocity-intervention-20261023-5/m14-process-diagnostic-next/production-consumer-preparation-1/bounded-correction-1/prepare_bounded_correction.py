"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
The sole authorized E0428 source correction; prepare only, no compiler/test grant.
"""
from pathlib import Path
import difflib,hashlib,json,shutil
P=Path(__file__).resolve().parent;PREVIOUS=P.parent;B=PREVIOUS.parent;ROOT=Path('/home/holden/mckernel');S=P/'source';O=P/'output-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(path,value):
 with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
def item(text,marker):
 start=text.index(marker);brace=text.index('{',start);end=brace+1;depth=1
 while depth:
  if text[end]=='{':depth+=1
  if text[end]=='}':depth-=1
  end+=1
 return text[start:end]
def main():
 oldready=PREVIOUS/'PRODUCTION-CONSUMER-READY.json';oldfailure=PREVIOUS/'PRODUCTION-FIRST-FAILURE-1.json';stderr=PREVIOUS/'actual-production-capture-1/00-current78-production-Rust-compile/stderr'
 assert pin(oldready)['sha256']=='4208ef4073968c6dda4a5771b3e7513c1f28937625ec75633879fb3f81535201'
 assert pin(oldfailure)['sha256']=='2fb3a2294e4347bc7eced2aee91ef259778c079779bcbfa5e8f61eda3fb17698'
 assert pin(stderr)['sha256']=='e9a1a83c79078bfecf6bfd2e63cca2705fa1dbfbe16ad7afff3e830d093e0425'
 S.mkdir();(P/'candidate').mkdir();(P/'patch').mkdir()
 oldsource=B/'candidate/process_helpers.rs';original=oldsource.read_text();decl='    fn kprintf(format: *const i8, ...) -> CInt;\n'
 assert original.count(decl)==2
 assert original.splitlines()[19]+'\n'==decl
 corrected=original.replace(decl,'',1);assert corrected.count(decl)==1
 assert corrected.replace('unsafe extern "C" {\n','unsafe extern "C" {\n'+decl,1)==original
 marker='pub unsafe extern "C" fn vm_range_insert_log_bridge('
 assert item(original,marker)==item(corrected,marker)
 canonical=(ROOT/'kernel/rust/process_helpers.rs').read_text();assert canonical.count(decl)==1
 # The sole remaining declaration is the identical original module declaration,
 # outside any cfg gate, before the existing release-TID log callback.
 existing='extern "C" {\n'+decl+'}\n\nunsafe extern "C" fn process_release_tid_log_bridge('
 assert existing in canonical and existing in corrected
 target=P/'candidate/process_helpers.rs';target.write_text(corrected)
 shutil.copy2(B/'candidate/process.c',P/'candidate/process.c')
 assert pin(P/'candidate/process.c')['sha256']=='08c238a08066a6eda5f346bbd6e6f87333bd505d8d598276dc9c52cd43568a45'
 (P/'patch/SOLE-E0428-CORRECTION.diff').write_text(''.join(difflib.unified_diff(original.splitlines(True),corrected.splitlines(True),fromfile='failed17c927/process_helpers.rs',tofile='corrected/process_helpers.rs')))
 (P/'patch/CANONICAL-TO-CORRECTED-PROCESS-RUST.diff').write_text(''.join(difflib.unified_diff(canonical.splitlines(True),corrected.splitlines(True),fromfile='a/kernel/rust/process_helpers.rs',tofile='b/kernel/rust/process_helpers.rs')))
 oldr=json.loads((PREVIOUS/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json').read_text());oldc=json.loads((PREVIOUS/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.NOT-EXECUTED.json').read_text())
 inputs={};changed=[];canonical_changes=[]
 for key,row in sorted(oldr['source_inputs'].items()):
  src=ROOT/key;now=pin(src)
  if now['sha256']!=row['canonical_before']['sha256']:canonical_changes.append(key)
  assert now==row['canonical_before'],('unexpected_current_canonical_input',key)
  take=target if key=='kernel/rust/process_helpers.rs' else src
  dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(take,dest)
  after=pin(dest)
  if after['sha256']!=row['private']['sha256']:changed.append(key)
  inputs[key]=dict(accepted_before=row['accepted_before'],canonical_before=now,private=after,failed_cohort_private=row['private'],modified_target=key=='kernel/rust/process_helpers.rs')
 assert changed==['kernel/rust/process_helpers.rs'] and not canonical_changes
 identity_rows=[[key,row['private']['sha256'],row['private']['bytes']] for key,row in inputs.items()];identity=hashlib.sha256(json.dumps(identity_rows,separators=(',',':')).encode()).hexdigest()
 rust=dict(oldr);rust['source_inputs']=inputs;rust['source_identity_rows']=identity_rows;rust['source_identity']=identity
 rust['status']='SOLE_BOUNDED_E0428_CORRECTION_SOURCE_READY_NO_EXECUTION_GRANT'
 rust['argv']=[arg.replace(str(PREVIOUS/'source'),str(S)).replace(str(PREVIOUS/'output-1'),str(O)) for arg in oldr['argv']]
 assert [i for i,(a,b) in enumerate(zip(rust['argv'],oldr['argv'])) if a!=b]==[46,47]
 rust['failure_history']=dict(family='log-callback-fullcrate-duplicate-kprintf-declaration',first_failure=pin(oldfailure),compiler_stderr=pin(stderr),failed_recipe=pin(PREVIOUS/'EXACT-CURRENT78-RUST-RECIPE.NOT-EXECUTED.json'),failed_source=pin(oldsource),failed_candidates=1,bounded_correction=1,correction_executed=False,next_unexpected_result='STOP_EXPERT_ESCALATION_NO_FURTHER_RETRY')
 rust['sole_source_delta']='Remove only added identical top-level kprintf extern declaration; existing unconditional canonical declaration provides the same C variadic binding.'
 write(P/'EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json',rust)
 headers={};canonical_headers={}
 for key,row in oldc['canonical_headers'].items():
  src=ROOT/key;now=pin(src);assert now==row,key
  dest=S/key;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest);headers[str(dest)]=pin(dest);canonical_headers[key]=now
 for name,row in oldc['headers'].items():
  if not name.startswith(str(PREVIOUS/'source')+'/'):headers[name]=row
 assert len(headers)==73
 shutil.copy2(P/'candidate/process.c',S/'kernel/process.c');shutil.copy2(PREVIOUS/'actual-process-debug-header-ABI.c',P/'actual-process-debug-header-ABI.c')
 c=dict(oldc);c['status']='SOLE_BOUNDED_E0428_CORRECTION_READY_NO_EXECUTION_GRANT';c['headers']=headers;c['canonical_headers']=canonical_headers;c['private_source']=pin(S/'kernel/process.c');c['ABI_witness']=pin(P/'actual-process-debug-header-ABI.c')
 c['selected_C_argv']=[arg.replace(str(PREVIOUS),str(P)) for arg in oldc['selected_C_argv']]
 c['commands']=[dict(row,argv=[arg.replace(str(PREVIOUS),str(P)) for arg in row['argv']],cwd=str(O)) for row in oldc['commands']]
 assert c['commands'][0]['argv']==rust['argv'] and len(c['commands'])==14
 c['failure_history']=rust['failure_history'];c['predicates_unchanged']=True
 write(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json',c)
 qualification=dict(scope=SCOPE,status='SOURCE_ONLY_DECLARATION_QUALIFICATION_NOT_PRODUCTION_ACCEPTANCE',first_fullcrate_failure=pin(oldfailure),first_error=pin(stderr),first_failed_fullmodule=pin(oldsource),corrected_fullmodule=pin(target),C08c_unchanged=pin(P/'candidate/process.c'),removed_line=20,exact_removed_bytes=decl,remaining_declaration='Identical unconditional existing canonical module extern before process_release_tid_log_bridge; canonicalline11593.',remaining_declaration_count=1,callback_body_unchanged=True,callback_body_sha256=hashlib.sha256(item(corrected,marker).encode()).hexdigest(),accepted_original_1101_leaf_receipt=pin(B/'sourcehandoff/ACTUAL-FIRST-CANDIDATE-WHOLE-JOIN.json'),leaf_scope='The accepted actual Rust leaf compiled a body extraction with exactly one necessary standalone kprintf declaration and test-only callback symbol. It proved the body/ABI/consumer behavior, but did not compile all process_helpers.rs declarations. That narrower acceptance is unchanged.',unchanged_source_algorithm=True,unchanged_fixture_1101=True,unchanged_C_and_debug_ABI=True,unchanged_all_T_U_metadata_relocation_and_link_predicates=True,expected_T_delta=rust['expected_T_delta'],expected_U_delta=rust['expected_U_delta'],test_executed=False,compiler_executed=False,CPU_reserved=False,next_unexpected_result='STOP_EXPERT_ESCALATION_NO_FURTHER_RETRY')
 write(P/'SOLE-DECLARATION-CORRECTION-AND-LEAF-SCOPE.json',qualification)
 ready=dict(scope=SCOPE,status='EXECUTABLE_READY_SOLE_BOUNDED_CORRECTION_NO_GRANT_OR_JOB',old_ready_preserved=pin(oldready),old_failure_preserved=pin(oldfailure),old_error_preserved=pin(stderr),Rust_recipe=pin(P/'EXACT-CURRENT78-RUST-RECIPE.CORRECTED-NOT-GRANTED.json'),C_recipe=pin(P/'EXACT-SELECTED-GCC9-PROCESS-CONSUMER.CORRECTED-NOT-GRANTED.json'),qualification=pin(P/'SOLE-DECLARATION-CORRECTION-AND-LEAF-SCOPE.json'),source_count=78,source_identity=identity,canonical_inputs_changed_from_failed_cohort=canonical_changes,private_inputs_changed_from_failed_cohort=changed,corrected_Rust=pin(target),unchanged_C=pin(P/'candidate/process.c'),unchanged_T_U_expectations=dict(T=rust['expected_T_delta'],U=rust['expected_U_delta']),prepared_commands=14,profile=rust['profile'],accepted_actual_1101_leaf_scope_preserved=True,failure_family=dict(family='E0428_duplicate_kprintf',failed_candidates=1,bounded_corrections_prepared=1,bounded_corrections_executed=0,further_unexpected_result='expert escalation; no third attempt'),compiler_jobs=0,CPU_reservations=0,canonical_or_frozen15_writes=0,production_link_native_credit=False,requires='Exact new root grant and fresh cohort/profile/headroom preflight before sole corrected attempt; no old O_EXCL producer/output/attempt reuse.')
 write(P/'EXECUTABLE-READY.CORRECTED-NOT-GRANTED.json',ready)
 mirror=ROOT/'docs/verification/evidence/velocity-intervention-20261023-5/m14-process-diagnostic-next/production-consumer-preparation-1/bounded-correction-1';shutil.copytree(P,mirror,dirs_exist_ok=True)
 print(json.dumps(dict(scope=SCOPE,ready=pin(P/'EXECUTABLE-READY.CORRECTED-NOT-GRANTED.json'),Rust_recipe=ready['Rust_recipe'],C_recipe=ready['C_recipe'],corrected_Rust=ready['corrected_Rust'],source_identity=identity,expected_U_delta=rust['expected_U_delta'],compiler_jobs=0,CPU_reservations=0),indent=2))
if __name__=='__main__':main()
