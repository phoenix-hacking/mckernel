"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root37 one-correction admission source preparation; no operational calls.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;P=D.parent;CAND=P.parent;E=D.parents[3]
PREV=CAND/'root36-admission-preparation-source-1'
ROOT=E.parents[3]
A=E/'ROOT-CURRENT113-CORRECTED-SCALAR4-NEXT4-BUILD-ADMISSION-1'
R=E/'ROOT-CURRENT113-ABI-PRIVATE-CORRECTION-BUILD-ADMISSION-1'
LEDGER=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER37.json'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(Path(p).read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def write(n,b):
 p=D/n;p.parent.mkdir(parents=True,exist_ok=True)
 if isinstance(b,str):b=b.encode()
 if p.exists():assert p.read_bytes()==b,n
 else:
  with p.open('xb') as f:f.write(b)
  p.chmod(0o400)
 return p

def save(n,x):return write(n,json.dumps(x,indent=2)+'\n')
def once(s,a,b):assert s.count(a)==1,(a,s.count(a));return s.replace(a,b,1)
assert ref(LEDGER)['sha256']=='b6ed7c321b348e90e13a51607d88af09893ab760e3decdd4d16d000a130155e8' and ref(LEDGER)['bytes']==4591
ledger=read(LEDGER);FREE=auth(ledger['latest_accepted_free_boundary']);assert ref(FREE)['sha256']=='070e0f2c4f367da3444f30300bfbeb193af6d1bb7cc6cda663a1cb154bfe9f13'
assert ref(P/'PROFILE.SOURCE-ONLY.json')['sha256']=='388c3c364f6c981a5749b058f59f94684091a12f381f785aab181508388bad05'
p=read(P/'PROFILE.SOURCE-ONLY.json');origin=p['origin_source_materialization'];assert origin['actual_producer_receipt']['sha256'].startswith('2c419c64')
assert len(p['exact_commands'])==4 and sum(not x['replace'] for x in p['inputs']['objects'])==8
assert not R.exists()
# Reuse exact Root36 current observer (28 native controls), add only failed-build facts.
observer='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exact Root37 successor: original28controls plus two positively joined build actors.
Retained failed container must remain stopped exit1, not be treated as absent.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path(%r)
FREE=Path(%r)
BASE=Path(%r)
REFS=%r

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r;return Path(r['path'])
def read(p):return json.loads(Path(p).read_bytes())
def observe():
 assert os.getuid()==os.geteuid()==1000
 for r in REFS:auth(r)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE) and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_CURRENT113_FAILED_RUST_COMMAND_TERMINATION_AND_CURRENT_FREE_PERMANENT_MUTEX' and review['normal_owned_retirement'] is True and review['current_free'] is True
 assert review['actual_failure']['error_code']=='E0616' and review['actual_failure']['no_passing_current113_compiler_prefix'] is True
 for key in ['holder_tool_result','local_terminal','runner_join','container_terminal']:auth(review[key])
 assert review['positive_termination']['local_holder_positive_join'] is True and review['positive_termination']['runner_positive_join'] is True
 spec=importlib.util.spec_from_file_location('root37_retained_root36_observer',BASE)
 module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 original=module.observe()
 # Original Root36/28controls/25clients/lease and global current contract unchanged.
 assert original['exact25clients_reaped'] is True
 old=review['fresh_current']['prior_native_28_controls_absent'];new=review['fresh_current']['new_holder_and_runner_absent']
 assert len(old)==28 and len(new)==2 and original['known_numeric_controls_absent']==old
 extra=[r['pid'] for r in new]
 assert all(not Path('/proc',str(pid)).exists() for pid in extra)
 census=original['group_membership_observation'];assert not census['errors'] and not any(r['pgrp'] in extra for r in census['rows'])
 queries=[]
 for retained in review['fresh_current']['exact_new_container_queries']:
  argv=retained['argv'];child=subprocess.run(argv,capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and not child.stderr
  if argv[4]=='inspect':
   values=json.loads(child.stdout);assert len(values)==1 and values[0]['Id']==review['container']
   assert values[0]['State']==review['positive_termination']['container_state']
   assert values[0]['State']['Running'] is False and values[0]['State']['Pid']==0 and values[0]['State']['ExitCode']==1 and values[0]['State']['OOMKilled'] is False
  else:assert child.stdout==retained['stdout']
  queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==3 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT37_FAILED113_RETAINED_CONTAINER_CURRENT_OBSERVATION_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root37=ref(LEDGER),accepted_failed_build_retirement=ref(FREE),original_observer=ref(BASE),original_observation=original,known_numeric_controls_absent=old+extra,new_build_actors_absent=new,group_membership_observation=census,retained_stopped_container=review['container'],retained_container_exit=1,exact_container_queries=queries,closed_exclusive_probes=original['closed_exclusive_probes'],artifact_acceptance=False,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
'''%(str(LEDGER),str(FREE),str(PREV/'observe_root36_current.py'),[ref(LEDGER),ref(FREE),ref(PREV/'observe_root36_current.py')])
write('observe_root37_current.py',observer)
capture=(PREV/'capture_resources.py').read_text();capture=once(capture,"OBSERVER=D/'observe_root36_current.py'","OBSERVER=D/'observe_root37_current.py'")
capture=once(capture,"OBSERVER_SHA='"+ref(PREV/'observe_root36_current.py')['sha256']+"'","OBSERVER_SHA='"+ref(D/'observe_root37_current.py')['sha256']+"'")
oldledger=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER36.json';oldfree=auth(read(oldledger)['latest_accepted_free_boundary'])
capture=once(capture,repr(ref(oldledger)),repr(ref(LEDGER)));capture=once(capture,repr(ref(oldfree)),repr(ref(FREE)))
write('capture_resources.py',capture)
for n in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(n,(P/n).read_bytes())
materializer=(PREV/'materialize_admission.py').read_text()
materializer=once(materializer,"P=Path("+repr(str(CAND/'final-scope-source-1'))+")","P=Path("+repr(str(P))+")")
materializer=once(materializer,'MATERIALIZE_REVIEWED_CURRENT113_STATIC_INPUTS_AND_HOLDER_ONLY','MATERIALIZE_REVIEWED_CURRENT113_ABI_CORRECTION_STATIC_INPUTS_AND_HOLDER_ONLY')
materializer=once(materializer,repr(ref(oldledger)),repr(ref(LEDGER)));materializer=once(materializer,repr(ref(oldfree)),repr(ref(FREE)))
materializer=once(materializer,'ROOT_SOURCE_ADOPTED_CURRENT113_CORRECTED_SCALAR4_NEXT4_NOT_BUILT','ROOT_SOURCE_ADOPTED_CURRENT113_ABI_PRIVATE_CORRECTION_NOT_BUILT')
materializer=once(materializer," origin=read(auth(b['actual_origin_producer']))\n"," assert b['actual_origin_producer']=="+repr(origin['actual_producer_receipt'])+"\n origin=read(auth(b['actual_origin_producer']))\n")
materializer=once(materializer,"'b027f2a5d1f2ef909638056815f6a066561df2dcd7a9a9532e9d0304a583bfe1'","'388c3c364f6c981a5749b058f59f94684091a12f381f785aab181508388bad05'")
old=""" preview=next(row['postimage'] for row in profile['inputs']['postimages'] if row.get('source_preview_not_runtime_producer'))
 assert preview['bytes']==header['bytes'] and preview['sha256']==header['sha256']
 for row in profile['inputs']['postimages']:
  if row['postimage']==preview:
   row['postimage']=header;row.pop('source_preview_not_runtime_producer');row['actual_origin_producer_receipt']=b['actual_origin_producer']
 for row in profile['cohort_source_bindings']:
  if row['postimage']==preview:row['postimage']=header
 profile['source_preparation_current_context']=dict(runtime_authority=None,Root36=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],actual_admission_required=True)
"""
new=""" assert not any(row.get('source_preview_not_runtime_producer') for row in profile['inputs']['postimages'])
 assert next(row['postimage'] for row in profile['inputs']['postimages'] if row['relative']=='kernel/rust/f06-origin/f06_rt_sigreturn_origin.h')==header
 assert profile['origin_source_materialization']['actual_producer_receipt']==b['actual_origin_producer']
 profile['source_preparation_current_context']=dict(runtime_authority=None,Root37=b['nonce_ledger'],accepted_current_free=b['native_custody_clearance'],actual_admission_required=True)
"""
materializer=once(materializer,old,new)
materializer=once(materializer," export['qualified_readonly_files']=[header if row==preview else row for row in export['qualified_readonly_files']]\n"," assert header in export['qualified_readonly_files']\n")
write('materialize_admission.py',materializer)
# Exactly one canonical leaf adoption; all former failed113 canonical source remains.
leaf='kernel/rust/f06_clone_ptrace_provider_abi.rs';source=ref(P/'candidate'/leaf)
save('ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,required_Root_status='ROOT_SOURCE_ADOPTED_CURRENT113_ABI_PRIVATE_CORRECTION_NOT_BUILT',files=[dict(relative=leaf,canonical_path=str(ROOT/leaf),current_preimage=ref(ROOT/leaf),private_source=source)],correction_count=1,actual_Root_adoption=None,retained_original_failure=ref(P/'ORIGINAL-FAILURE-AND-ONE-CORRECTION.json')))
bindings=read(PREV/'ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json');bindings.update(status='ROOT37_ONE_CORRECTION_TEMPLATE_NOT_AUTHORITY',admission=str(R),nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),expected_actual_decision='MATERIALIZE_REVIEWED_CURRENT113_ABI_CORRECTION_STATIC_INPUTS_AND_HOLDER_ONLY',source_adoption=None,independent_source_profile_review=None,actual_origin_producer=origin['actual_producer_receipt'],actual_generated_header=origin['actual_generated_header'],actual_origin_binding=origin['actual_origin_binding'],actual_Rust_environment=origin['actual_Rust_environment'],actual_CMake_origin=origin['actual_CMake_origin'])
save('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',bindings)
resource=read(PREV/'ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json');resource.update(nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),schema_label='Original BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES schema retained; corrected113fourcommands/118sources/8retained, failedRust+3unrun, stopped363375preserved')
save('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',resource)
py='/home/holden/anaconda3/bin/python3'
entries=[dict(phase='Root static metadata materialization after actual one-leafadoption and realbindings; existingorigin reused',argv=[py,'-I','-B',str(D/'materialize_admission.py'),'--root-bindings',str(D/'ROOT-ACTUAL-BINDINGS-1.json')]),dict(phase='Fresh physical/current capture BEFORE holder',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--physical-output',str(R/'ROOT-PREHOLDER-PHYSICAL-1.json')]),dict(phase='Exact actual holder-only entry after sourcepublication/bootstrapgrant',argv=[py,'-I','-B',str(R/'hold_and_run_build_only.py'),'--bootstrap-grant',str(R/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')]),dict(phase='Held resources and pending execution input after actual holderREADY',argv=[py,'-I','-B',str(D/'capture_resources.py'),'--admission',str(R),'--root-input',str(R/'ROOT-ACTUAL-RESOURCE-INPUT-1.json')]),dict(phase='Existing publisher after independent exact executionPASS, within original120s resources',argv_prefix=[py,'-I','-B',str(R/'publish_approved_ready.py'),str(R)],final_argument='actual approved pending-input SHA256 from independent execution review',actual_final_argument=None,actual_pending_input_path=str(R/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json'),no_automatic_approval=True),dict(phase='Holder consumes published one-use READY once and runs same four commands',existing_READY_path=str(R/'HOLDER/ROOT-BUILD-GRANT.READY.json'),extra_launch_command_required=False)]
save('COMPLETE-ROOT-ENTRY-RESOURCE-PUBLISHER-SEQUENCE.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,status='ALL_COMMAND_PREFIXES_AND_DYNAMIC_ROOT_INPUT_BINDINGS_PREWRITTEN_NOT_EXECUTED',planned_admission=str(R),phases=entries,actual_four_compiler_commands=p['exact_commands'],passed_prefix=0,required_commands=4,first_failed_Rust_command=0,unrun_suffix=[1,2,3],origin_producer_replay=False,resource_maximum_age_seconds=120,Root_required_before_capture=['actual independent source/helperPASS','exact correctedleafsourceadoption','fresh newnonce/actualRootbindings','static sourcepublication/fetchverification before holder'],Root_required_after_holder=['actualresourceinput/currentreservedfacts','exact independent executionPASS with actual pendinginput SHA','invoke existingpublisher with that approvedSHA; no fabricated approval'],all_actual_calls=0))
helpers=[]
for n in ['observe_root37_current.py','capture_resources.py','materialize_admission.py','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 oldpath=PREV/('observe_root36_current.py' if n=='observe_root37_current.py' else n)
 ast.parse((D/n).read_text(),filename=n)
 diff=write('helper-diffs/'+n+'.diff',''.join(difflib.unified_diff(oldpath.read_text().splitlines(keepends=True),(D/n).read_text().splitlines(keepends=True),fromfile='Root36/'+oldpath.name,tofile='Root37-correction/'+n)))
 helpers.append(dict(name=n,predecessor=ref(oldpath),successor=ref(D/n),diff=ref(diff)))
save('HELPER-DERIVATION.json',dict(scope=SCOPE,runtime_authority=None,helpers=helpers,scope_limit='Original machinery; retainedRoot36observer plus exact two failedbuild actors/stoppedcontainer checks only. Reuse actualorigin and118sourceclosure, oneleafcorrection. No new gate/framework.',all_actual_calls=0))
save('CLOSED-ROOT37-CONTEXT.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,Root37=ref(LEDGER),latest_accepted_free=ref(FREE),failed_source_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),one_corrected_profile=ref(P/'PROFILE.SOURCE-ONLY.json'),corrected_leaf=source,one_correction=ref(P/'ORIGINAL-FAILURE-AND-ONE-CORRECTION.json'),existing_defining_witness=ref(P/'EXACT-EXISTING-ABI-WITNESS.json'),source_map=p['inputs']['source_directory_exports'][0]['manifest'],genuine_origin_reused=origin['actual_producer_receipt'],actual_new_nonce=None,actual_Root_source_adoption=None,actual_source_publication=None,actual_resource_authority=None,actual_holder=None,actual_output_root=None,actual_execution_review=None,actual_release=None,retained_failed_container=read(FREE)['container'],retained_failed_container_exit=1,passed_prefix=0,fixed_three_clock_cutoffs=p['fixed_three_clock_cutoffs'],all_actual_calls=0,preserved_preparation_failure=ref(P/'PREPARATION-FIRST-FAILURE.json')))
files=[ref(q) for q in D.rglob('*') if q.is_file() and q.name not in ['prepare_source.py','PREPARATION-MANIFEST.json','SOURCE-READY.json']]
external=[ref(P/'PROFILE.SOURCE-ONLY.json'),ref(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json'),ref(P/'SOURCE-READY.json'),p['inputs']['source_directory_exports'][0]['manifest'],ref(p['reuse_descriptor']),ref(LEDGER),ref(FREE),origin['actual_producer_receipt'],origin['actual_generated_header']]
for row in external:auth(row)
save('PREPARATION-MANIFEST.json',dict(scope=SCOPE,runtime_authority=None,status='ROOT37_CORRECTED113_ADMISSION_SOURCE_ONLY',files=files,external_inputs=external,all_actual_calls=0))
save('SOURCE-READY.json',dict(scope=SCOPE,status='ROOT37_SINGLE_CORRECTED113_RETRY_ADMISSION_SOURCE_READY_NOT_RELEASED',runtime_authority=None,manifest=ref(D/'PREPARATION-MANIFEST.json'),closed_context=ref(D/'CLOSED-ROOT37-CONTEXT.NOT-AUTHORITY.json'),helper_derivation=ref(D/'HELPER-DERIVATION.json'),adoption_inputs=ref(D/'ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json'),complete_sequence=ref(D/'COMPLETE-ROOT-ENTRY-RESOURCE-PUBLISHER-SEQUENCE.NOT-GRANTED.json'),profile=ref(P/'PROFILE.SOURCE-ONLY.json'),Root37=ref(LEDGER),latest_free=ref(FREE),commands=4,new_objects=3,retained_objects=8,Rust_sources=118,passed_prefix=0,correction_count=1,genuine_origin_reused=origin['actual_producer_receipt'],all_actual_calls=0,canonical_or_Git_edits=0))
print(json.dumps(dict(status='ROOT37_CORRECTION_ADMISSION_SOURCE_READY_NO_OPERATIONS',ready=ref(D/'SOURCE-READY.json'),manifest=ref(D/'PREPARATION-MANIFEST.json'))))
