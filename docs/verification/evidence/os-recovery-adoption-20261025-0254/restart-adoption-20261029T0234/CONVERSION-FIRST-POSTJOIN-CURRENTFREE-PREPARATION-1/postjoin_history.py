"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact Root70 retirement DATA/frontier successor, no live observations.
"""
from pathlib import Path
import json,hashlib,importlib.util
D=Path(__file__).resolve().parent

def need(v,msg):
 if not v:raise ValueError(msg)
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(r):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'}and ref(r['path'])==r,'exact history BYTEref');return json.loads(Path(r['path']).read_bytes())
def load(r,name):
 need(ref(r['path'])==r,'exact history source');s=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def validate(custody):
 pins=json.loads((D/'HISTORY-INPUTS.json').read_bytes())
 need(custody['author']=='/root'and custody['decision']=='BIND_EXACT_CONVERSION_POSTRETIREMENT_READONLY_CUSTODY'and custody['runtime_authority']is None and custody['current_free']is False,'Root postretirement custody is not free')
 need(custody['history_inputs']==ref(D/'HISTORY-INPUTS.json')and custody['old_readonly_client_status']==custody['uninstrumented_source_tool_identities']=='UNKNOWN'and custody['no_unlisted_physical_or_custody_operations_since_retirement']is True,'exact history/UNKNOWN/later-operation attestation')
 free=read(pins['previous_free']);ledger=read(pins['root70_pending_ledger']);prior=read(pins['root69_ledger']);entry=ledger['conversion_first_build'];result=read(pins['retirement_result']);closure=read(pins['retirement_tool_closure']);resource=read(pins['actual_build_resource']);artifact=read(pins['artifact_acceptance'])
 need(free['independent']is True and free['current_free']is True and len(free['next_full_postjoin_actor_frontier'])==212,'genuine historical Root69 independent free')
 need(ledger['author']=='/root'and ledger['current_physical_clearance_pending']is True and ledger['consumed_nonces']==prior['consumed_nonces']+['4709c9fae2c743a7acd662e93a663358']and len(ledger['consumed_nonces'])==74 and ledger['current_native_operation']==prior['current_native_operation'],'74consumed conversion boundary, native history unchanged')
 need(entry['container']==result['cid']=='a7fe0b67d129afc3868d329d65f68317b6aadee6bedd7bc76330a52cdd0ae7ef'and entry['command_returncodes']==[0,0,0]and entry['native_acceptance']is False and entry['unmeasured_docker_client_births']=='UNKNOWN'and entry['independent_artifact_acceptance']==pins['artifact_acceptance'],'exact actual conversion build/artifact scope')
 need(artifact['independent']is True and artifact['implementation_ownership']is False,'accepted actual artifact not new native credit')
 executor=load(pins['retirement_executor'],'pure_actual_conversion_retirement_result');b=executor.bindings();receipts=executor.validate_result(result,b)
 need(len(receipts)==14 and result['signals_sent']==0 and result['records_released']==[]and result['container_absent']is True,'actual normal retirement14clients, no signals/records release')
 need(closure['author']=='/root'and closure['decision']=='RECORD_ACTUAL_RETIREMENT_TOOL_TERMINAL_AND_EXACT_EXECUTOR_ABSENCE'and closure['result']==pins['retirement_result']and closure['tool_session']==23433 and closure['tool_returncode']==0 and closure['executor']==result['cleanup_actor']and closure['exact_executor_identity_absent']is True and closure['current_pid_birth']is None and closure['signals_sent']==0 and closure['records_released']==[]and closure['parent_outer_process_birth']=='UNKNOWN','actual Root retirement caller closure, no invented outer birth')
 need(closure['clients']==[dict(pid=r['pid'],birth=r['birth'],group=r['process_group'],returncode=r['returncode'],receipt=rr)for r,rr in zip(receipts,result['command_receipts'])],'same14actualrawclientjoins')
 need(custody['independent_retirement_acceptance']==pins['independent_retirement_acceptance'],'exact accepted69216 retirementref');acceptance=read(custody['independent_retirement_acceptance'])
 need(acceptance['independent']is True and acceptance['implementation_ownership']is False and acceptance['decision']=='PASS_EXACT_CONVERSION_FIRST_NORMAL_RETIREMENT_WITH_TYPED_ROOT_TOOL_CLOSURE'and acceptance['retirement_result']==pins['retirement_result']and acceptance['parent_closure']==pins['retirement_tool_closure']and acceptance['native_acceptance']is False,'genuine independent actual retirement acceptance required')
 actors=list(free['next_full_postjoin_actor_frontier']);holder=entry['holder'];runner=entry['runner'];collector=resource['actual_observations']['resource_collector'];actor=result['cleanup_actor']
 added=[dict(pid=holder['pid'],start=holder['starttime'],role='conversion_build_holder',group=None,fd=holder['fd']),dict(pid=runner['pid'],start=runner['start'],role='conversion_build_runner',group=None,fd=None),dict(pid=collector['pid'],start=collector['birth'],role='conversion_build_resource_collector',group=collector['process_group'],fd=None),dict(pid=actor['pid'],start=actor['birth'],role='conversion_retirement_executor',group=None,fd=actor['mutex_fd'])]+[dict(pid=r['pid'],start=r['birth'],role='conversion_retirement_raw_client',group=r['process_group'],fd=None)for r in receipts]
 need(len(added)==18 and len({(a['pid'],a['start'])for a in added})==18 and not {(a['pid'],a['start'])for a in added}&{(a['pid'],a['start'])for a in actors},'only18actual new measured identities')
 actors+=added;need(len(actors)==230 and len({(a['pid'],a['start'])for a in actors})==225,'212old+18new rows and5duplicates retained')
 return actors,receipts,pins
