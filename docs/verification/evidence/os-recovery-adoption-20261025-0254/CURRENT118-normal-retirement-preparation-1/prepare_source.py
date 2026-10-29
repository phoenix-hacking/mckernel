"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Deterministic narrow CURRENT118 specialization of reviewed normal retirement5f95.
Reads declared records only. Does not query, guard, lock, launch or remove anything.
"""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).resolve().parent
E=D.parent
A=E/'ROOT-CURRENT118-CLEARPTE-SIGNALFP-BUILD-ADMISSION-3'
BASE=E/'bfd-default-build-normal-retirement-preparation-20261028-1/executor-source-1/image-metadata-profile-correction-source-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(path):
 path=Path(path).resolve();raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(path):return json.loads(Path(path).read_bytes())
def put(name,data):
 path=D/name;assert not path.exists(),str(path)
 path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');return ref(path)
def replace(old,new):
 global code
 assert code.count(old)==1,old;code=code.replace(old,new)
base=ref(BASE/'retire_exact_bfd_stopped_container.py')
assert base['sha256']=='5f95df84f57db66d6f01e9583a2f51281000dff6c58bfd7cb287849000fc7694'
b=read(BASE/'BINDINGS.json');profile=read(A/'PROFILE.SOURCE-ONLY.json');claim=read(A/'OUTPUT/claim.json');terminal=read(A/'OUTPUT/terminal.json')
plan=read(A/'OUTPUT/plan.json');result=read(A/'OUTPUT/work/evidence/worker-result.json')
assert len(result['commands'])==len(plan['commands'])==len(profile['exact_commands'])==4
source_refs={n:ref(A/n) for n in ['run_build_only.py','hold_and_run_build_only.py','build_only_worker.py','PROFILE.SOURCE-ONLY.json','ROOT-HOLDER-BOOTSTRAP-GRANT.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json','ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json','ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json']}
for n in ['RUNNER.STARTED.json','RUNNER.JOINED.json','HOLDER.READY.json','BUILD-LOCAL-TERMINAL.json','runner.stdout','runner.stderr']:source_refs['holder:'+n]=ref(A/'HOLDER'/n)
for n in ['terminal.json','container.stdout','container.stderr','container.cid','claim.json','plan.json']:source_refs['output:'+n]=ref(A/'OUTPUT'/n)
source_refs['worker_result']=ref(A/'OUTPUT/work/evidence/worker-result.json')
mounts=[]
for n,arg in enumerate(claim['argv']):
 if arg!='--mount':continue
 options=claim['argv'][n+1].split(',');kv=dict(x.split('=',1) for x in options if '=' in x)
 assert kv['type']=='bind' and set(kv)=={'type','source','target'} and set(options)-set(x for x in options if '=' in x)<= {'readonly'}
 mounts.append(dict(Source=kv['source'],Destination=kv['target'],RW='readonly' not in options))
assert mounts[0]==dict(Source=str(A/'OUTPUT/work'),Destination='/work',RW=True)
assert all(not r['RW'] for r in mounts[1:]) and len({r['Destination'] for r in mounts})==len(mounts)
declared=[]
for cmd in result['commands']:
 out=cmd['output'];assert out['path'].startswith('/work/');r=ref(A/'OUTPUT/work'/out['path'][6:]);assert r['bytes']==out['bytes'] and r['sha256']==out['sha256'];declared.append(r)
join=ref(E/'restart-adoption-20261028T1911/CURRENT118-FRESH-A3-1/ACTUAL-HOLDER-TOOL-JOIN.json')
assert join['sha256']=='967945842af3d5e8ba183d35d9ae0880bcb226f98e6855fd6cbd5460df8727e4'
free=read(Path(profile['native_custody_clearance']['path']));observation=read(Path(free['actual_postjoin_observation']['path']))
actors=list(observation['all_recorded_actors_absent']);assert len(actors)==87
actors.append(dict(pid=observation['observer_self']['pid'],start=observation['observer_self']['birth'],role='Root63_capture_actor'))
actors.extend(dict(pid=x['pid'],start=x['birth'],role='Root63_capture_query_client') for x in observation['query_clients']);assert len(actors)==93
frontier=profile['source_preparation_current_context']['closed_unlaunched_frontier'] if 'closed_unlaunched_frontier' in profile['source_preparation_current_context'] else ref(E/'restart-adoption-20261028T1911/CURRENT118-FRESH-A3-1/ROOT-CLOSED-UNLAUNCHED-FRONTIER.ACTUAL.json')
closed=read(frontier['path']);assert len(closed['actors'])==6
actors.extend(dict(pid=x['pid'],start=x['birth'],role=x['role']) for x in closed['actors']);assert len(actors)==99
actual_actors_ref=ref(E/'CURRENT118-postbuild-current-successor-preparation-1/ACTUAL-CURRENT118-RECORDED-ACTORS.json')
actual_actors=read(actual_actors_ref['path']);new=[dict(pid=x['pid'],start=x['birth'],role=x['role']) for x in actual_actors['actual_A3_actor_rows']];assert len(new)==10
finite_names=['FINITE-STARTED.json','FINITE-JOINED.json','physical.CHILD-STARTED.json','held.CHILD-STARTED.json','ROOT-PHYSICAL-CAPTURE.COMPLETE.json','ROOT-HELD-CAPTURE.COMPLETE.json','FINITE-COMPLETION.PASS.json','INDEPENDENT-FINITE-REVIEW.PASS.json','PREWARM_READY.json']
evidence=[ref(A/'FINITE-REVIEW-HANDOFF'/n) for n in finite_names]+[ref(Path(free['actual_postjoin_observation']['path'])),profile['native_custody_clearance'],frontier,actual_actors_ref,join]
evidence.extend(x['receipt'] for x in actual_actors['actual_A3_actor_rows'] if 'receipt' in x)
protected_records=list(source_refs.values())+declared+[join]+evidence
unique={r['path']:r for r in protected_records}
protected=put('PROTECTED-ORIGINALS.json',dict(scope=SCOPE,status='DATA_ONLY_RETAIN_ALL_ORIGINALS',roots=[str(A),str(A/'OUTPUT/work')],records=[dict(kind='file',**r) for r in unique.values()],declared_build_outputs=declared,failed_source_evidence=[frontier,closed['evidence_packet']],mutation_of_any_original=False,runtime_authority=None,retention='All artifacts, logs, scratch, source and prior failed namespaces remain. Only exact stopped OCI CID may be removed under separate release; no output deletion or exhaustive artifact inventory is authorized.'))
packet=put('NORMAL-RETIREMENT-PACKET.json',dict(scope=SCOPE,schema='mckernel.current118-build.normal-retirement-preparation.v1',status='SOURCE_DATA_NOT_EXECUTION_RELEASE',runtime_authority=None,nonce=profile['actual_nonce'],nonce_consumed_once=True,container_id=terminal['container'],container_name=claim['argv'][claim['argv'].index('--name')+1],output_root=str(A/'OUTPUT'),cohort=str(A),source_refs=source_refs,expected_mounts=mounts,declared_build_outputs=declared,protected_originals=protected,actual_commands=result['commands'],terminal_state=terminal['state'],shared_custody=dict(permanent_mutex='/run/lock/mckernel-development.lock',device=27,inode=4,holder_fd=3,lease_records_created=[],shared_records_created=[],owner_records_created=[],records_authorized_for_release=[],container_owner_label_added=False),proposed_mutation_argv=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock','rm','--',terminal['container']],parent_tool_join=join,normal_retirement_only=True,native_acceptance=False,fullfile_acceptance=False))
for k in ['failed_cleanup_attempt','failed_cleanup_attempt2','actual_pending_ledger_after_attempt2']:b.pop(k,None)
b.update(packet=packet,protected=protected,base_reviewed_executor=base,prior_observer=free['observer'],prior_actors=actors,new_known_actors=new,actor_evidence=evidence,parent_tool_join=join,actor_gaps=actual_actors['unknown_births_not_filled'],cid=terminal['container'],name=claim['argv'][claim['argv'].index('--name')+1],nonce=profile['actual_nonce'],output_root_parent=str(D),prior_ledger=closed['base_ledger'],holder_pid=2222137,holder_birth=103142320,runner_pid=2222194,runner_birth=103142571,finite_pid=2221500,finite_birth=103138098,command_count=4,working_directory='/work/output/build/kernel',ledger_key='current118_build',operation='CURRENT118_A3_FOUR_COMMAND_BUILD_ONLY_NOT_NATIVE',approved_creation_argv=source_refs['output:claim.json'],root63_history_is_historical=True)
binding=put('BINDINGS.json',b)
code=Path(base['path']).read_text()
code=code.replace('Single custom-BFD','Single CURRENT118 A3').replace('BFD','CURRENT118').replace('bfd-default-build','current118-build').replace('retire_exact_bfd_stopped_container.py','retire_exact_current118_stopped_container.py')
replace("BINDINGS_SHA='83c104435ed34b7137f3ff7e84e4e5569130114e9fd1bab95311d9cd54da3aba'","BINDINGS_SHA='"+binding['sha256']+"'")
replace("claim['pid']==2124454","claim['pid']==b['runner_pid']")
replace("len(result['commands'])==3,'exact three-command plan/profile'","len(result['commands'])==len(plan['commands'])==b['command_count'],'exact four-command plan/profile'")
replace("pid=2124365,starttime=101427979","pid=b['holder_pid'],starttime=b['holder_birth']")
replace("pid=2124454,starttime=101432667","pid=b['runner_pid'],starttime=b['runner_birth']")
replace("parent['session_id']==94204","parent['session_id']==3240")
replace("parent['actual_tool_response']['chunk_id']=='8c21ed'","parent['actual_tool_response']['chunk_id']=='69d894'")
start=code.index('def expected_mounts(');end=code.index('\ndef validate_profile(',start)
code=code[:start]+"def expected_mounts(p,profile):\n # Frozen finite mount declaration parsed from the original approved claim.\n # The complete original pure Docker argv builder is independently rerun below.\n return copy.deepcopy(p['expected_mounts'])\n"+code[end:]
replace("c['WorkingDir']=='/work'","c['WorkingDir']==b['working_directory']")
replace('normal.OWNER_PID=2124365','normal.OWNER_PID=b[\'holder_pid\']')
replace('forbidden=set(normal.WAITER_PIDS)|{2124454}',"forbidden=set(normal.WAITER_PIDS)|{b['runner_pid']}")
replace("prior=authenticated(authenticated(b['packet'],True)['source_refs']['PROFILE.SOURCE-ONLY.json'],True)['actual_root_ledger']","prior=b['prior_ledger']")
replace("ledger.get('bfd_default_build',{})","ledger.get(b['ledger_key'],{})")
replace("build.get('operation')=='CURRENT118_CURRENT_DEFAULT_THREE_COMMAND_BUILD_ONLY_NOT_NATIVE'","build.get('operation')==b['operation']")
replace("('primitive','normal','backend','guardian','prior_observer','packet','protected')","('primitive','normal','backend','guardian','prior_observer','packet','protected','base_reviewed_executor')")
ast.parse(code)
out=D/'retire_exact_current118_stopped_container.py';assert not out.exists();out.write_text(code)
(D/'MINIMAL-SOURCE-DIFF.patch').write_text(''.join(difflib.unified_diff(Path(base['path']).read_text().splitlines(True),code.splitlines(True),fromfile=base['path'],tofile=str(out))))
print(json.dumps(dict(executor=ref(out),bindings=binding,packet=packet,protected=protected,history_rows=len(actors),new_rows=len(new),declared_outputs=len(declared))))
