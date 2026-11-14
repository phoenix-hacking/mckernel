"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure acceptance of recorded exact retirement and typed Root tool closure only.
"""
from pathlib import Path
import importlib.util,json,hashlib,time,math
D=Path(__file__).resolve().parent;P=D.parent;O=P/'actual-retirement-conversion-root1'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(Path(p).read_text())
rr=ref(O/'RESULT.json');assert rr['bytes']==9456 and rr['sha256']=='bc2df78168d34ef7c6b720766a03391668775d8e0847bb1130ff404e7958248d';result=read(rr['path']);pr=ref(P/'ROOT-TOOL-PARENT-CLOSURE.ACTUAL.json');assert pr['bytes']==8719 and pr['sha256']=='0750139aa9f7a7f5930ab5b733b01709b191d5181c28600014aef4d769400e21';parent=read(pr['path'])
spec=importlib.util.spec_from_file_location('independent_pure_actual_retirement_result',P/'retire_exact_conversion_stopped_container.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);b=m.bindings();start=time.monotonic();receipts=m.validate_result(result,b)
packet,protected,profile,claim,plan,terminal=m.validate_retained(b)
release=m.authenticated(result['release'],True);execution=m.authenticated(release['execution_review'],True);source=m.authenticated(release['source_review'],True);publication=m.authenticated(release['source_publication'],True);files=read(P/'RUNTIME-FILES.json')
assert execution['decision']=='PASS_EXECUTION'and execution['independent']is True and execution['implementation_ownership']is False
assert execution['release_payload']=={k:v for k,v in release.items()if k!='execution_review'}and execution['release_payload_sha256']==hashlib.sha256(m.canonical(execution['release_payload'])).hexdigest()
assert source['decision']=='PASS_SOURCE'and source['source_checkpoint']==release['source_checkpoint']==publication['commit']=='cc8627df8c26ae8e104dad341186dd907e10f059'
assert source['files']==release['files']==files and source['bindings']==release['bindings']==result['bindings']
assert publication['status'].startswith('PASS_FETCHED') and publication['runtime_authority']is None
published={x['actual']['path']:x['actual']for x in publication['rows']}
for row in files.values():assert published[row['path']]==row==ref(row['path'])
assert release['signals_allowed']==0 and release['records_released']==[] and release['maximum_invocations']==1 and release['billing_mode']=='included_only'and release['allow_prepaid_fallback']is False and release['credit_metadata_only']is True
assert m.authenticated(execution['actual_admission'],True)['no_unlisted_postbuild_physical_operation']is True
started=read(O/'STARTED.json');rm=read(O/'RM-ONCE-CLAIM.json');proof2=m.authenticated(result['proofs'][1],True)
assert started['pid']==result['cleanup_actor']['pid']==2647013 and started['birth']==result['cleanup_actor']['birth']==111953913
assert started['release']==result['release']==rm['release'] and started['bindings']==result['bindings']
assert rm['cid']==b['cid']and rm['nonce']==b['nonce']and rm['argv']==receipts[9]['argv']==m.PREFIX+['rm','--',b['cid']]and rm['preproof']==result['proofs'][1]
assert len(rm['clocks'])==3 and all(math.isfinite(x)and 0<x<c for x,c in zip(rm['clocks'],b['cutoffs']))and 0<=rm['clocks'][0]-proof2['clocks'][0]<=120
assert m.authenticated(receipts[4]['raw']['stdout'])==m.authenticated(packet['source_refs']['output:container.stdout'])and m.authenticated(receipts[4]['raw']['stderr'])==m.authenticated(packet['source_refs']['output:container.stderr'])
for row in protected['records']:
 if row['kind']=='file':m.authenticated({k:row[k]for k in ('path','bytes','sha256')})
 else:assert Path(row['path']).is_symlink()and str(Path(row['path']).readlink())==row['target']
for proofref in result['proofs']:
 safety=m.authenticated(proofref,True)['safety'];assert safety['MemAvailable_bytes']>=4<<30
safety=result['final_safety'];assert safety['MemAvailable_bytes']>=4<<30 and safety['mutex']==dict(device=27,inode=4,holder=2647013,fd=4)
assert safety['cgroup']=={'cpu/mckernel-dev/cpu.cfs_period_us':'100000','cpu/mckernel-dev/cpu.cfs_quota_us':'400000','memory/mckernel-dev/memory.limit_in_bytes':str(12<<30),'pids/mckernel-dev/pids.max':'512','pids/mckernel-dev/pids.current':'0'}
assert all(x in (None,[])for x in safety['container_cgroups'].values())
assert parent['schema']=='mckernel.root-conversion-retirement-tool-parent-closure.v1'and parent['author']=='/root'and parent['decision']=='RECORD_ACTUAL_RETIREMENT_TOOL_TERMINAL_AND_EXACT_EXECUTOR_ABSENCE'
assert parent['tool_session']==23433 and parent['tool_terminal_chunk']=='9be9a1'and parent['tool_returncode']==0
assert parent['executor']==result['cleanup_actor']and parent['result']==rr and parent['started']==ref(O/'STARTED.json')and parent['current_pid_birth']is None and parent['exact_executor_identity_absent']is True
assert parent['all14clients_positive_joined']is True and len(parent['clients'])==14
actors=[]
for a,r,refrow in zip(parent['clients'],receipts,result['command_receipts']):
 assert a==dict(pid=r['pid'],birth=r['birth'],group=r['pid'],returncode=r['returncode'],receipt=refrow)
 assert r['positive_wait4']and r['wait4_pid']==r['pid']and r['returncode']==0 and r['streams_closed']and r['group_absent']and not r['group_members']and not r['client_retirement_unproven']and r['signals_sent']==0
 actors.append(dict(pid=r['pid'],start=r['birth'],group=r['pid'],role='conversion_retirement_client',receipt=refrow))
assert parent['parent_outer_process_birth']=='UNKNOWN'and parent['signals_sent']==0 and parent['records_released']==[] and parent['current_free']is False and parent['runtime_authority']is None
assert result['original_Docker_actor_gaps']==b['actor_gaps']and result['own_fd_closed_only_after_result_on_normal_return']is True
report=dict(schema='mckernel.independent-conversion-first-actual-stopped-container-retirement-acceptance.v1',scope=m.SCOPE,decision='PASS_EXACT_CONVERSION_FIRST_NORMAL_RETIREMENT_WITH_TYPED_ROOT_TOOL_CLOSURE',reviewer='/root/recovery_review',independent=True,implementation_ownership=False,recorded_at=time.time(),result=rr,retirement_result=rr,release=result['release'],source_review=release['source_review'],execution_review=release['execution_review'],source_publication=release['source_publication'],source_checkpoint=release['source_checkpoint'],bindings=result['bindings'],runtime_files=files,parent_closure=pr,parent_closure_kind='ACTUAL_ROOT_TYPED_TOOL_TERMINAL_PLUS_EXACT_EXECUTOR_ABSENCE_NOT_RAW_PARENT_WAIT4',recorded_tool_session=23433,recorded_tool_terminal_chunk='9be9a1',recorded_tool_returncode=0,cleanup_actor=result['cleanup_actor'],prior_rows=212,prior_distinct_identities=207,build_known_actors=b['new_known_actors'],retirement_clients=actors,command_receipts=result['command_receipts'],proofs=result['proofs'],rm_once_claim=ref(O/'RM-ONCE-CLAIM.json'),started=ref(O/'STARTED.json'),cid=b['cid'],nonce=b['nonce'],container_absent=True,signals_sent=0,records_released=[],protected_originals=b['protected'],protected_records=len(protected['records']),protected_actual_outputs=packet['retained_actual_outputs'],pure_validate_result='PASS_EXACT_EXISTING_FUNCTION_WITH_ALL_RAW_PROOF_AND_ORDER_CHECKS',validation_seconds=time.monotonic()-start,mutex_closure_disposition='Accepted exact source complete=true normal-finally closes only owned FD4 before return0; Root records terminal0 and exact executor birth absent. This supports ordinary owned executor closure, not global mutex/custody clearance.',unknowns_preserved=b['actor_gaps']+['Retirement outer Root/tool process birth UNKNOWN; no parent PID/group or raw wait4 record invented.'],parent_positive_join_and_fresh_current_acceptance_required=True,current_free=False,native_acceptance=False,wholefile_retirement=False,C_retirement=False,runtime_authority=None,additional_runtime_queries=0,cleanup_replays=0)
p=D/'RETIREMENT-ACCEPTANCE.ACTUAL.json';tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(p);print(json.dumps(dict(acceptance=ref(p),raw_commands=len(receipts),protected_records=len(protected['records']),seconds=report['validation_seconds'])))
