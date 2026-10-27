"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite Root34 heavy admission/source preparation only. No guard/observer execution.
"""
import ast,copy,difflib,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;E=D.parents[1]
S=D.parent/'next4-scalar4-logical-line-hold-successor-source-1'
C=E/'current110-host19-production-preparation-source-1/resource-and-qualifier-preparation-1'
ROOT=E.parents[3]
R=E/'ROOT-CURRENT113-NEXT4-SCALAR4-BUILD-ADMISSION-1'
LEDGER=E/'ROOT-NEW12H-ACTUAL-ADMISSION-1/ROOT-CURRENT-NONCE-LEDGER34.json'
FREE=E/'f05-v2-root-export-and-native-preparation-source-1/root-adopted-native-entry-4/independent-postjoin-review-1/REVIEW.json'
BASE=E/'daemon-final-ring-suffix-source-1/new12h-operation-preparation-1/resource-observer-window-correction-source-1/check_postnative_current_new12h.py'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def read(p):return json.loads(p.read_text())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
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
assert ref(LEDGER)['sha256']=='c817825d68c8aa736acb9dbe05296b3dec9e40f574dc1a3bf7ef4bfa95bf8f88'
assert ref(FREE)['sha256']=='bf19e5a464ce05f49657acce7e598ce1125d8bf913c85631d5883190290e4890'
assert read(LEDGER)['latest_accepted_free_boundary']==ref(FREE)
assert read(FREE)['decision']=='PASS_POSITIVE_ROOT4_NATIVE_OWNER_RETIREMENT_AND_CURRENT_FREE'
assert read(FREE)['owned_client_retirement']['count']==25
assert not R.exists(),'fresh planned admission directory only'
# Reuse the unchanged reviewed global observer; add only exact Root4/Root34 facts.
observer='''"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite Root34 successor around the original reviewed current-availability observer.
No cleanup, release, workload, signals or new global observer implementation.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess,time
LEDGER=Path(%r)
FREE=Path(%r)
BASE=Path(%r)
REFS=%r

def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def auth(row):assert ref(row['path'])==row;return Path(row['path'])
def observe():
 assert os.getuid()==os.geteuid()==1000
 for row in REFS:auth(row)
 ledger=read(LEDGER);review=read(FREE)
 assert ledger['latest_accepted_free_boundary']==ref(FREE)
 assert ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_POSITIVE_ROOT4_NATIVE_OWNER_RETIREMENT_AND_CURRENT_FREE' and review['normal_owned_retirement'] is True and review['current_free'] is True
 retired=review['owned_client_retirement'];assert retired['count']==25 and retired['all_exact_reaped'] is True and len(retired['commands'])==25
 assert all(v['command']['reaped'] is True and v['command']['returncode']==v['returncode'] for v in retired['commands'].values())
 snapshot=read(auth(review['evidence']['retained_owner_and_guest_snapshot']))
 result=snapshot['owner_records']['result.json']
 assert result['status']=='FAIL' and result['absence_verified'] is True and result['lease_retained'] is False
 assert result['container']==review['container'] and result['secondary']==[]
 spec=importlib.util.spec_from_file_location('root34_unchanged_reviewed_baseline',BASE)
 baseline=importlib.util.module_from_spec(spec);spec.loader.exec_module(baseline)
 physical=baseline.observe()
 # The original bounded global census and closed permanent-mutex probes are reused.
 absent=review['fresh_current']['all_owned_pids_and_groups_absent']
 assert len(absent)==28 and all(not Path('/proc',str(pid)).exists() for pid in absent)
 census=physical['group_membership_observation']
 assert not census['errors'] and not any(r['pgrp'] in absent for r in census['rows'])
 assert len(physical['closed_exclusive_probes'])==2
 queries=[]
 for retained in review['fresh_current']['container_queries']:
  argv=retained['argv']
  assert argv[0:4]==['sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
  child=subprocess.run(argv,capture_output=True,text=True,timeout=15)
  assert child.returncode==retained['returncode'] and child.stdout==retained['stdout'] and child.stderr==retained['stderr']
  queries.append(dict(argv=argv,returncode=child.returncode,stdout=child.stdout,stderr=child.stderr,positive_wait=True,streams_closed=True))
 assert len(queries)==5 and Path('/sys/fs/cgroup/pids/mckernel-dev/pids.current').read_text().strip()=='0'
 return dict(status='PASS_ROOT34_EXACT_POSTROOT4_CURRENT_OBSERVATION_PENDING_ROOT_ACCEPTANCE',scope=review['scope'],runtime_authority=None,observed_at=time.time(),Root34=ref(LEDGER),accepted_native_retirement=ref(FREE),exact25clients_reaped=True,exact_container_absent=review['container'],known_numeric_controls_absent=absent,group_membership_observation=census,closed_exclusive_probes=physical['closed_exclusive_probes'],lease_released_retained_result=result,docker_observations=queries,unchanged_reviewed_global_observer=ref(BASE),unchanged_baseline_observation=physical,native_acceptance=False)
if __name__=='__main__':print(json.dumps(observe(),indent=2))
'''%(str(LEDGER),str(FREE),str(BASE),[ref(LEDGER),ref(FREE),ref(BASE)])
write('observe_root34_current.py',observer)
# Existing capture protocol and original resource predicates, current exact observer/118sources.
capture=(C/'capture_resources.py').read_text()
capture=once(capture,"D=Path(__file__).resolve().parent;E=D.parents[1]","D=Path(__file__).resolve().parent;E=Path("+repr(str(E))+")")
capture=once(capture,"OBSERVER=E/'daemon-final-ring-suffix-source-1/new12h-operation-preparation-1/resource-observer-window-correction-source-1/check_postnative_current_new12h.py'","OBSERVER=D/'observe_root34_current.py'")
capture=once(capture,"OBSERVER_SHA='2b7362126fbe70475a208e40df9eb56fa12df0993d83d0aa9b9a22a36638481c'","OBSERVER_SHA='"+ref(D/'observe_root34_current.py')['sha256']+"'")
capture=once(capture,"assert len(runner.source_directory_postimages(profile))==112","assert len(runner.source_directory_postimages(profile))==118")
# Pin current ledger and clearance while preserving original decision schema labels.
needle=" ledger=read(auth(inputs['nonce_ledger']))\n"
capture=once(capture,needle,needle+" assert inputs['nonce_ledger']=="+repr(ref(LEDGER))+"\n assert inputs['native_custody_clearance']=="+repr(ref(FREE))+"\n")
write('capture_resources.py',capture)
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:write(name,(S/name).read_bytes())
# Finite materializer adaptation of existing canonical workflow; Root supplies real facts.
materializer=(C/'materialize_admission.py').read_text()
materializer=once(materializer,"D=Path(__file__).resolve().parent;P=D.parent;E=D.parents[1]","D=Path(__file__).resolve().parent;P=Path("+repr(str(S))+");E=Path("+repr(str(E))+")")
materializer=once(materializer,"MATERIALIZE_REVIEWED_CURRENT110_STATIC_INPUTS_AND_HOLDER_ONLY","MATERIALIZE_REVIEWED_CURRENT113_STATIC_INPUTS_AND_HOLDER_ONLY")
needle=" ledger=read(auth(b['nonce_ledger']))\n"
materializer=once(materializer,needle,needle+" assert b['nonce_ledger']=="+repr(ref(LEDGER))+"\n assert b['native_custody_clearance']=="+repr(ref(FREE))+"\n")
old=""" adoption=read(b['source_adoption']['path'])
 assert adoption['status']=='PASS_ROOT_EXACT_NINE_SOURCE_ADOPTION_ONLY'
 for row in adoption['files']:assert ref(row['destination'])['sha256']==row['candidate']['sha256']
 for row in read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']:
  assert ref(row['original']['path'])==row['original'] and ref(row['snapshot']['path'])==row['snapshot']
"""
new=""" adoption=read(b['source_adoption']['path'])
 assert adoption['author']=='/root' and adoption['status']=='ROOT_SOURCE_ADOPTED_CURRENT113_NEXT4_SCALAR4_NOT_BUILT'
 for row in adoption['files']:
  assert ref(row['canonical']['path'])==row['canonical']
  assert ref(row['private_source']['path'])==row['private_source']
  assert row['canonical']['sha256']==row['private_source']['sha256']
 for row in read(P/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')['files']:
  assert ref(row['snapshot']['path'])==row['snapshot']
  assert ref(E.parents[3]/'kernel/rust'/row['relative'])['sha256']==row['snapshot']['sha256']
 origin=read(auth(b['actual_origin_producer']))
 assert origin['author']=='/root' and origin['returncode']==0 and origin['direct_child_joined'] is True and origin['streams_closed'] is True
 header=b['actual_generated_header'];auth(header);assert origin['actual_header']==header
 context=read(auth(b['actual_origin_binding']));environment=read(auth(b['actual_Rust_environment']));auth(b['actual_CMake_origin'])
 template=read(P/'PROFILE.SOURCE-ONLY.json')
 assert context['command']==template['exact_commands'][3]
 assert context['source_sha256']==ref(P/'candidate/arch/x86_64/kernel/syscall.c')['sha256']
 assert context['profile_sha256']==ref(P/'candidate/scripts/f06_origin_command_profile.json')['sha256']
 assert environment=={'MCKERNEL_F06_RT_SIGRETURN_ORIGIN':'/src/arch/x86_64/kernel/syscall.c'}
 assert template['exact_commands'][0]['argv'].count('MCKERNEL_F06_RT_SIGRETURN_ORIGIN=/src/arch/x86_64/kernel/syscall.c')==1
"""
materializer=once(materializer,old,new)
needle=" profile['native_custody_clearance']=b['native_custody_clearance']\n"
inject=""" preview=next(r['postimage'] for r in profile['inputs']['postimages'] if r.get('source_preview_not_runtime_producer'))
 assert preview['sha256']==header['sha256'] and preview['bytes']==header['bytes']
 for row in profile['inputs']['postimages']:
  if row['postimage']==preview:
   row['postimage']=header;row.pop('source_preview_not_runtime_producer');row['actual_origin_producer_receipt']=b['actual_origin_producer']
 for row in profile['cohort_source_bindings']:
  if row['postimage']==preview:row['postimage']=header
 profile['actual_root_adoption']=b['source_adoption']
 profile['origin_source_materialization'].update(status='ACTUAL_CURRENT113_ORIGIN_PRODUCER_BOUND',actual_producer_receipt=b['actual_origin_producer'],actual_generated_header=header,actual_origin_binding=b['actual_origin_binding'],actual_Rust_environment=b['actual_Rust_environment'],actual_CMake_origin=b['actual_CMake_origin'])
"""
materializer=once(materializer,needle,needle+inject)
needle=" export=read(P/'INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json')\n"
materializer=once(materializer,needle,needle+" export['qualified_readonly_files']=[header if row==preview else row for row in export['qualified_readonly_files']]\n export['actual_origin_producer_receipt']=b['actual_origin_producer']\n")
write('materialize_admission.py',materializer)
# Exact candidate adoption list; no actual receipt, grant, nonce or resource is minted.
p=read(S/'PROFILE.SOURCE-ONLY.json');m=read(S/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')
adopt=[]
for row in p['inputs']['postimages']:
 if row['relative'].endswith('f06_rt_sigreturn_origin.h'):continue
 adopt.append((row['relative'],row['postimage']))
for row in m['files']:
 if row['kind']!='unchanged adopted CURRENT112 source':adopt.append(('kernel/rust/'+row['relative'],row['snapshot']))
adopt += [('scripts/derive_f06_origin.py',ref(S/'candidate/scripts/derive_f06_origin.py')),('scripts/f06_origin_command_profile.json',ref(S/'candidate/scripts/f06_origin_command_profile.json'))]
adoption_inputs=[]
for relative,candidate in adopt:
 canonical=ROOT/relative
 adoption_inputs.append(dict(relative=relative,canonical_path=str(canonical),current_preimage=ref(canonical) if canonical.exists() else None,private_source=candidate))
save('ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json',dict(scope=SCOPE,runtime_authority=None,required_Root_status='ROOT_SOURCE_ADOPTED_CURRENT113_NEXT4_SCALAR4_NOT_BUILT',files=adoption_inputs,actual_source_adoption=None,source_review_required=True,original_LOCK4_excluded=True))
save('ROOT-BINDINGS.TEMPLATE.NOT-AUTHORITY.json',dict(scope=SCOPE,status='TEMPLATE_NO_ACTUAL_AUTHORITY',author=None,decision=None,maximum_invocations=1,root_attests_exact_UID1000_readonly_exports=None,nonce=None,admission=str(R),preparation_manifest=None,nonce_ledger=ref(LEDGER),native_custody_clearance=ref(FREE),independent_source_profile_review=None,source_adoption=None,actual_origin_producer=None,actual_generated_header=None,actual_origin_binding=None,actual_Rust_environment=None,actual_CMake_origin=None))
save('ROOT-RESOURCE-INPUT.TEMPLATE.NOT-AUTHORITY.json',dict(scope=SCOPE,status='TEMPLATE_ONLY_NO_AUTHORITY',author=None,decision=None,schema_label='BIND_CURRENT110_ACTUAL_HELD_BUILD_RESOURCES retained original reviewed schema; actual1135commands/118sources',maximum_invocations=1,root_attests_only_intervening_holder_preparation=None,nonce=None,request_sha256=None,profile=None,request=None,nonce_ledger=ref(LEDGER),source_publication=None,physical_observation=None,native_custody_clearance=ref(FREE),runner=None,worker=None,input_export_authority=None,other_reserved_memory_bytes=None,other_reserved_pids=None,aggregate_pid_budget=None))
origin=read(S/'NEW-ORIGIN-PRODUCER.NOT-GRANTED.json')
python='/home/holden/anaconda3/bin/python3'
commands=[dict(phase='Root source-only origin producer, after source review/actual authorisation',argv=origin['argv']),dict(phase='Root static materialization only after real adoption/origin receipts and bindings',argv=[python,'-I','-B',str(D/'materialize_admission.py'),'--root-bindings',str(D/'ROOT-ACTUAL-BINDINGS-1.json')]),dict(phase='Fresh current read-only physical capture BEFORE holder, under Root authority',argv=[python,'-I','-B',str(D/'capture_resources.py'),'--physical-output',str(R/'ROOT-PREHOLDER-PHYSICAL-1.json')]),dict(phase='Holder-only entry AFTER Root binds actual bootstrap grant/sourcepublication; waits for separately grantedGO',argv=[python,'-I','-B',str(R/'hold_and_run_build_only.py'),'--bootstrap-grant',str(R/'ROOT-HOLDER-BOOTSTRAP-GRANT.json')]),dict(phase='Held resource capture only after actual holderREADY/current Root input',argv=[python,'-I','-B',str(D/'capture_resources.py'),'--admission',str(R),'--root-input',str(R/'ROOT-ACTUAL-RESOURCE-INPUT-1.json')])]
# Check the exact retained CLI spelling from source without entering it.
assert "'--bootstrap-grant'" in (D/'hold_and_run_build_only.py').read_text()
save('EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json',dict(scope=SCOPE,runtime_authority=None,status='ORDERED_LITERAL_PROPOSAL_NOT_EXECUTED_NO_FUTURE_RECORDS_FABRICATED',planned_admission=str(R),commands=commands,source_binding_required_before_physical_capture=True,actual_origin_producer=0,actual_materialization=0,actual_holder=0,actual_resource_capture=0,actual_compiler=0,publication_and_independent_execution_review='Root separately binds exact static fetch/publication and actual heldresource inputs, then reviewerPASS and one-use grant/GO. No READY or grant fabricated here.',fresh_resource_age_seconds=120,first_failure_preserved_no_replay=True))
files=[ref(x) for x in D.iterdir() if x.is_file() and x.name not in ['PREPARATION-MANIFEST.json','SOURCE-READY.json','prepare_source.py']]
external=[ref(S/n) for n in ['PROFILE.SOURCE-ONLY.json','INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json','RUST-SUBTREE-CLOSED-SOURCE-MAP.json','FROZEN-FIVE-COMMAND-SEVEN-INPUT-REUSE.json','NEW-ORIGIN-PRODUCER.NOT-GRANTED.json']]+[ref(LEDGER),ref(FREE),ref(BASE)]
for path in D.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
save('PREPARATION-MANIFEST.json',dict(scope=SCOPE,runtime_authority=None,status='SOURCE_ONLY_ROOT34_ADMISSION_PREPARATION',files=files,external_inputs=external,Root34=ref(LEDGER),latest_retirement=ref(FREE),new_framework=False,unchanged_global_observer=ref(BASE),actual_calls=dict(guard=0,observer=0,producer=0,materialization=0,holder=0,compiler=0)))
save('SOURCE-READY.json',dict(scope=SCOPE,status='ROOT34_CURRENT113_ADMISSION_SOURCE_PREPARATION_READY_NOT_RELEASED',runtime_authority=None,manifest=ref(D/'PREPARATION-MANIFEST.json'),source_profile=ref(S/'PROFILE.SOURCE-ONLY.json'),entry_commands=ref(D/'EXACT-ROOT-ENTRY-COMMANDS.NOT-GRANTED.json'),adoption_inputs=ref(D/'ROOT-ADOPTION-INPUTS.NOT-AUTHORITY.json'),Root34=ref(LEDGER),latest_retirement=ref(FREE),commands=5,new_objects=4,retained_objects=7,Rust_sources=118,source_review_required_before_use=True,all_actual_operations=0,canonical_edits=0,Git_operations=0))
print(json.dumps(dict(status='ROOT34_ADMISSION_SOURCE_ONLY_READY',ready=ref(D/'SOURCE-READY.json'),manifest=ref(D/'PREPARATION-MANIFEST.json'),actual_operations=0)))
