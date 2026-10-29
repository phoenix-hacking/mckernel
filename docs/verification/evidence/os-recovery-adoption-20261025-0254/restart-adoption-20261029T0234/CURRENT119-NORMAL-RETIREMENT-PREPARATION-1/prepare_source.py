"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bounded CURRENT119 source/DATA preparation only; no proc/Docker/guard operations.
"""
from pathlib import Path
import json,hashlib,difflib,copy
D=Path(__file__).resolve().parent;A=D.parent;B=A/'ROOT-CURRENT119-BUILD-ADMISSION-1';OLD=A/'M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/monotone-census-negative-facts-source-1';P=A/'M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1';G=P/'recovery-quota-confirmation-binding-1/actual-control-binding-2/guardian_guard.py'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def write(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
assert not (D/'NORMAL-RETIREMENT-PACKET.json').exists()
grant=read(B/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json');profile=read(Path(grant['profile']['path']));runner=Path(grant['runner']['path']);worker=Path(grant['worker']['path']);holder=read(B/'HOLDER/HOLDER.READY.json');joined=read(B/'HOLDER/RUNNER.JOINED.json');claim=read(B/'OUTPUT/claim.json');terminal=read(B/'OUTPUT/terminal.json');result=read(B/'OUTPUT/work/evidence/worker-result.json');assert terminal['container']=='593abb2a8d66817d66c6a530341db17fa7873a42f390d3693792556f4b15cd24'and terminal['returncode']==0
refs={'PROFILE.SOURCE-ONLY.json':grant['profile'],'run_build_only.py':ref(runner),'build_only_worker.py':ref(worker),'hold_and_run_build_only.py':holder['source'],'worker_result':ref(B/'OUTPUT/work/evidence/worker-result.json')}
for f in ['ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','ROOT-HOLDER-BOOTSTRAP-GRANT.json','ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.R2.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json','ROOT-ACTUAL-STATIC-SOURCE-PUBLICATION.json']:refs[f]=ref(B/f)
for f in ['claim.json','plan.json','terminal.json','container.stdout','container.stderr','container.cid']:refs['output:'+f]=ref(B/'OUTPUT'/f)
for f in ['HOLDER.READY.json','RUNNER.STARTED.json','RUNNER.JOINED.json','BUILD-LOCAL-TERMINAL.json']:refs['holder:'+f]=ref(B/'HOLDER'/f)
mounts=[]
for i,x in enumerate(claim['argv']):
 if x!='--mount':continue
 parts=claim['argv'][i+1].split(',');pairs=dict(x.split('=',1)for x in parts if '='in x);assert pairs['type']=='bind';mounts.append(dict(Source=pairs['source'],Destination=pairs['target'],RW='readonly'not in parts))
outputs=[]
for command in result['commands']:
 r=command['output'];assert r['path'].startswith('/work/');p=B/'OUTPUT/work'/r['path'][6:];actual=ref(p);assert actual['bytes']==r['bytes']and actual['sha256']==r['sha256'];outputs.append(actual)
packet=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',schema='mckernel.current119-build.normal-retirement-preparation.v1',status='SOURCE_DATA_NOT_EXECUTION_RELEASE',runtime_authority=None,nonce=grant['nonce'],nonce_consumed_once=True,container_id=terminal['container'],container_name='current119-build-build-only-'+grant['nonce'],output_root=str(B/'OUTPUT'),cohort=str(runner.parent),source_refs=refs,expected_mounts=mounts,retained_actual_outputs=outputs,native_custody_unchanged=True)
write('NORMAL-RETIREMENT-PACKET.json',packet)
records=[dict(kind='file',**r)for r in refs.values()]+[dict(kind='file',**r)for r in outputs]
write('PROTECTED-ORIGINALS.json',dict(scope=packet['scope'],status='DATA_ONLY_RETAIN_ALL_ORIGINALS',roots=[str(B),str(B/'OUTPUT/work')],records=records,failed_source_evidence=[],no_current118_artifact_rejection_inferred=True))
b=read(OLD/'BINDINGS.json');capture_ref=read(Path(grant['native_custody_clearance']['path']))['actual_postjoin_observation'];capture=read(Path(capture_ref['path']));prior=list(capture['all_recorded_actors_absent'])
# Keep every accepted historical actor, original UNKNOWN labels and known groups;
# append actual postjoin observer/query identities rather than replacing history.
prior.append(dict(pid=capture['observer_self']['pid'],start=capture['observer_self']['birth'],role='accepted_CURRENT118_capture_observer',group=capture['observer_self']['group'],fd=None))
for row in capture['query_clients']:prior.append(dict(pid=row['pid'],start=row['birth'],role='accepted_CURRENT118_capture_query',group=row['pid'],fd=None))
b.update(packet=ref(D/'NORMAL-RETIREMENT-PACKET.json'),protected=ref(D/'PROTECTED-ORIGINALS.json'),guardian=ref(G),prior_observer=read(Path(grant['native_custody_clearance']['path']))['reviewed_observer'],prior_ledger=profile['source_preparation_current_context']['current_ledger'],parent_tool_join=None,parent_tool_session_id=63230,parent_tool_chunk_id=None,cutoffs=profile['fixed_three_clock_cutoffs'],cid=terminal['container'],name=packet['container_name'],nonce=grant['nonce'],holder_pid=holder['holder']['pid'],holder_birth=holder['holder']['starttime'],runner_pid=joined['pid'],runner_birth=joined['starttime'],finite_pid=None,finite_birth=None,command_count=4,ledger_key='current119_build',operation='CURRENT119_A3_FOUR_COMMAND_BUILD_ONLY_NOT_NATIVE',output_root_parent=str(D),approved_creation_argv=ref(B/'OUTPUT/claim.json'),prior_actors=prior,new_known_actors=[dict(pid=holder['holder']['pid'],start=holder['holder']['starttime'],role='CURRENT119_build_holder',group=None,fd=3),dict(pid=joined['pid'],start=joined['starttime'],role='CURRENT119_build_runner',group=None,fd=None)],actor_evidence=[capture_ref,grant['native_custody_clearance'],ref(B/'HOLDER/HOLDER.READY.json'),ref(B/'HOLDER/RUNNER.STARTED.json'),ref(B/'HOLDER/RUNNER.JOINED.json'),ref(B/'HOLDER/BUILD-LOCAL-TERMINAL.json')],root63_history_is_historical=True)
for k in ['failed_current118_retirement_attempt']:b.pop(k,None)
write('BINDINGS.TEMPLATE.NOT-AUTHORITY.json',b)
s=(OLD/'retire_exact_current118_stopped_container.py').read_text();new=s.replace('CURRENT118','CURRENT119').replace('mckernel.current118-build','mckernel.current119-build').replace("SELF=D/'retire_exact_current118_stopped_container.py'","SELF=D/'retire_exact_current119_stopped_container.py'")
new=new.replace("BINDINGS_SHA='feebbf1e0cecb7d6605d2e92f1288b969e5251419bb4d327c8b012d1221b97cd'","BINDINGS_SHA=None  # Materialize only after genuine Root parent join and typed ledger.")
new=new.replace("parent['session_id']==3240","parent['session_id']==b['parent_tool_session_id']").replace("parent['actual_tool_response']['chunk_id']=='69d894'","parent['actual_tool_response']['chunk_id']==b['parent_tool_chunk_id']")
# Historical ledger metadata remains immutable; it is never a live credit grant.
needle="need(r['cutoffs']==b['cutoffs'] and r['credit_run_id']"
assert new.count(needle)==1
new=new.replace(needle,"need(r['billing_mode']=='included_only' and r['allow_prepaid_fallback'] is False and r['credit_metadata_only'] is True,'weekly only; historical credit is not spending authority')\n "+needle)
(D/'retire_exact_current119_stopped_container.UNBOUND.py').write_text(new)
(D/'MINIMAL-119-SOURCE.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),new.splitlines(True),fromfile=str(OLD/'retire_exact_current118_stopped_container.py'),tofile=str(D/'retire_exact_current119_stopped_container.UNBOUND.py'))))
write('MISSING-ROOT-DATA.json',dict(parent_tool_join=None,parent_tool_chunk_id=None,current_typed_consumed119_ledger=None,actual_source_publication=None,independent_source_review=None,independent_execution_review=None,actual_release=None,output_namespace='actual-retirement-current119-root1',no_runtime_authority=True))
print('actual packet/protected/templates ready, no execution')
