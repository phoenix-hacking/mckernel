"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One exact source/DATA postretirement successor, no live calls.
"""
from pathlib import Path
import json,hashlib,ast,difflib
D=Path(__file__).resolve().parent;A=D.parent;OLD=A/'M14-CONVERSION-FIRST-CURRENT-FRONTIER-PREPARATION-1/parent-ownership-correction-1';RET=A/'CONVERSION-FIRST-NORMAL-RETIREMENT-PREPARATION-1'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_bytes())
def write(n,v):(D/n).write_text(v if isinstance(v,str)else json.dumps(v,indent=2)+'\n')
def replace_function(s,name,new):
 n=next(x for x in ast.parse(s).body if isinstance(x,ast.FunctionDef)and x.name==name);lines=s.splitlines(keepends=True);return ''.join(lines[:n.lineno-1])+new+'\n'+''.join(lines[n.end_lineno:])
def main():
 assert not(D/'HISTORY-INPUTS.json').exists()
 pins=dict(previous_free=ref(OLD/'actual-independent-acceptance-1/CURRENT-FREE.ACTUAL.json'),root69_ledger=ref(A/'ROOT69-CONVERSION-FIRST-ADOPTION-1/ROOT69-NONCE-LEDGER.ACTUAL.json'),root69_boundary=ref(A/'ROOT69-CONVERSION-FIRST-ADOPTION-1/ROOT69-CURRENT-BOUNDARY.ACTUAL.json'),root70_pending_ledger=ref(A/'ROOT70-CONVERSION-BUILD-CUSTODY-1/ROOT70-NONCE-LEDGER.PENDING-CURRENT.json'),retirement_executor=ref(RET/'retire_exact_conversion_stopped_container.py'),retirement_result=ref(RET/'actual-retirement-conversion-root1/RESULT.json'),retirement_tool_closure=ref(RET/'ROOT-TOOL-PARENT-CLOSURE.ACTUAL.json'),actual_build_resource=ref(A/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1/ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.json'),artifact_acceptance=read(A/'ROOT70-CONVERSION-BUILD-CUSTODY-1/ROOT70-NONCE-LEDGER.PENDING-CURRENT.json')['conversion_first_build']['independent_artifact_acceptance']);pins['independent_retirement_acceptance']=ref(RET/'actual-independent-retirement-review-1/RETIREMENT-ACCEPTANCE.ACTUAL.json');write('HISTORY-INPUTS.json',pins)
 for name in ['FIXED-READONLY-INPUTS.json','prepare_readonly_operation.py']:(D/name).write_bytes((OLD/name).read_bytes())
 formatter=(D/'prepare_readonly_operation.py').read_text().replace('PREPARE_CONVERSION_FRONTIER_READONLY_OPERATION_SOURCE_DATA_ONLY','PREPARE_CONVERSION_POSTJOIN_READONLY_OPERATION_SOURCE_DATA_ONLY').replace("source_owners=['/root','/root/m14_integration_terra']","source_owners=['/root','/root/recovery_receipts']");write('prepare_readonly_operation.py',formatter)
 parent=(OLD/'root_capture_parent.py').read_text().replace('observe_conversion_frontier.py','observe_conversion_postjoin.py');write('root_capture_parent.py',parent)
 guard=(OLD/'readonly_operation_guard.py').read_text().replace("OPERATION='current-conversion-frontier-readonly'","OPERATION='conversion-first-postretirement-currentfree-readonly'")
 context='''def context_subjects(c):
 expected={'current_ledger','current_boundary','post119_current_free','nonce','source_authority','armed_controls','bootstrap_caps','readonly_source_closure'}
 need(set(c)==expected and c['armed_controls']==ARM and type(c['nonce'])is str and re.fullmatch('[0-9a-f]{32}',c['nonce']),'exact new readonly context')
 pins=decode((D/'HISTORY-INPUTS.json').read_bytes())
 need(c['current_ledger']==pins['root70_pending_ledger']and c['current_boundary']==pins['root69_boundary']and c['post119_current_free']==pins['previous_free'],'exact74pending boundary and historical Root69 free, not new free')
 for key in ('current_ledger','current_boundary','post119_current_free','source_authority','armed_controls','bootstrap_caps'):auth(c[key])
 ledger=read(c['current_ledger']);need(c['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']+ledger['reserved_unused_nonces']+ledger['used_readonly_operation_ids'],'unused distinct readonly ID')
 need(set(c['readonly_source_closure'])=={'observer','physical_adapter','capture_parent','history'},'exact four readonly sources')
 need(c['readonly_source_closure']==dict(observer=ref(D/'observe_conversion_postjoin.py'),physical_adapter=ref(D/'readonly_history_guard.py'),capture_parent=ref(D/'root_capture_parent.py'),history=ref(D/'postjoin_history.py')),'exact coherent postjoin source closure')
 for row in c['readonly_source_closure'].values():auth(row)
 history=load(c['readonly_source_closure']['history'],'pure_postretirement_history');actors,_,_=history.validate(read(c['source_authority']));need(len(actors)==230,'230rows225identities retained')
 subjects=fixed_subjects();subjects.update({'root:'+k:c[k]for k in ('current_ledger','current_boundary','post119_current_free','source_authority','armed_controls','bootstrap_caps')});subjects.update({'readonly:'+k:v for k,v in c['readonly_source_closure'].items()});subjects['history_inputs']=ref(D/'HISTORY-INPUTS.json');return subjects
'''
 guard=replace_function(guard,'context_subjects',context);write('readonly_operation_guard.py',guard)
 adapter=(OLD/'readonly_history_guard.py').read_text().replace(str(OLD/'readonly_operation_guard.py'),str(D/'readonly_operation_guard.py')).replace('29bc19df20118485418a96a2dd0fd9099ff550a5732a8dfcd402aa332b28d066',ref(D/'readonly_operation_guard.py')['sha256']);write('readonly_history_guard.py',adapter)
 obs=(OLD/'observe_conversion_frontier.py').read_text();line=next(x for x in obs.splitlines()if x.startswith('GUARD='));obs=obs.replace(line,'GUARD='+repr(ref(D/'readonly_operation_guard.py')))
 start=obs.index(" need(binding['current_free']==ACCEPTED_FREE");end=obs.index(" history_binding=read(binding['physical_history_binding'])",start)
 prelude=""" history=load(context['readonly_source_closure']['history'],'pure_actual_postretirement_frontier');actors,retire_receipts,pins=history.validate(read(context['source_authority']));previous_free=read(pins['previous_free'])
 checker=load(CHECKER,'retained_pure_postjoin_readers')
"""
 obs=obs[:start]+prelude+obs[end:];obs=obs.replace("executor,b,_,retirement=checker.validate_metadata();out=Path(binding['query_output_directory'])", "executor=history.load(pins['retirement_executor'],'actual_conversion_retirement_readers');b=executor.bindings();retirement=retire_receipts;out=Path(binding['query_output_directory'])")
 start=obs.index(' result=dict(historical);');end=obs.index('\n return result',start)
 result=""" result=dict(historical);result.pop('actual_latest_operation_postjoin_acceptance',None);result.pop('current_boundary',None);result.update(historical_root69_free=pins['previous_free'],historical_root69_boundary=pins['root69_boundary'],actual_root70_pending_ledger=pins['root70_pending_ledger'],actual_conversion_retirement=pins['retirement_result'],actual_retirement_caller_closure=pins['retirement_tool_closure'],current_free_candidate=True,independent_acceptance=False,current_physical_clearance_pending=True,complete_actual_actor_frontier=True,all_recorded_actors_absent=actors,old_readonly_client_status='UNKNOWN',unmeasured_source_tool_identities='UNKNOWN',unmeasured_resource1=previous_free['unmeasured_resource1'],unmeasured_resource1_limitations=previous_free['unmeasured_resource1_limitations'],unmeasured_post_root68_outer_tool_actor=previous_free['unmeasured_post_root68_outer_tool_actor'],unmeasured_retirement_outer_birth='UNKNOWN',unmeasured_build_Docker_client_births='UNKNOWN',current119_query_command_receipts=commands.receipts,current119_complete_process_report=report,query_clients=[dict(pid=r['pid'],birth=r['birth'])for r in records],observer_self=dict(pid=caller[0],birth=int(caller[1]),group=os.getpgrp()),observed_clocks=first,last_observed_clocks=last,fixed_cutoffs=list(limits),native_acceptance=False,runtime_authority=None)
"""
 obs=obs[:start]+result.rstrip()+obs[end:];obs=obs.replace('AUTHORIZE_ONE_CONVERSION_FRONTIER_READONLY_CAPTURE','AUTHORIZE_ONE_CONVERSION_POSTJOIN_READONLY_CAPTURE').replace('PASS_EXACT_CONVERSION_FRONTIER_READONLY_CAPTURE','PASS_EXACT_CONVERSION_POSTJOIN_READONLY_CAPTURE');write('observe_conversion_postjoin.py',obs)
 for name in ['root_capture_parent.py','readonly_operation_guard.py','readonly_history_guard.py','observe_conversion_postjoin.py']:ast.parse((D/name).read_bytes())
 custody=dict(schema='mckernel.root-conversion-postretirement-custody.v1',author=None,decision=None,history_inputs=ref(D/'HISTORY-INPUTS.json'),independent_retirement_acceptance=pins['independent_retirement_acceptance'],old_readonly_client_status='UNKNOWN',uninstrumented_source_tool_identities='UNKNOWN',no_unlisted_physical_or_custody_operations_since_retirement=None,current_free=False,runtime_authority=None);write('ROOT-CUSTODY.TEMPLATE.NOT-AUTHORITY.json',custody)
 intent=read(OLD/'ROOT-OPERATION-INTENT.TEMPLATE.NOT-AUTHORITY.json');intent['operation']='conversion-first-postretirement-currentfree-readonly';ctx=intent['context'];ctx.update(current_ledger=pins['root70_pending_ledger'],current_boundary=pins['root69_boundary'],post119_current_free=pins['previous_free'],nonce=None,source_authority=None,readonly_source_closure=dict(observer=ref(D/'observe_conversion_postjoin.py'),physical_adapter=ref(D/'readonly_history_guard.py'),capture_parent=ref(D/'root_capture_parent.py'),history=ref(D/'postjoin_history.py')));intent.pop('operation',None);intent.pop('source_owners',None);intent['decision']=None;write('ROOT-OPERATION-INTENT.TEMPLATE.NOT-AUTHORITY.json',intent)
 for name in ['ROOT-GUARD-BINDING.TEMPLATE.NOT-AUTHORITY.json','ROOT-OBSERVER-BINDING.TEMPLATE.NOT-AUTHORITY.json','INDEPENDENT-OBSERVER-REVIEW.TEMPLATE.NOT-AUTHORITY.json','RELEASE.TEMPLATE.NOT-AUTHORITY.json']:
  data=read(OLD/name)
  def route(v):
   if isinstance(v,list):return [route(x)for x in v]
   if isinstance(v,dict):
    if set(v)=={'path','bytes','sha256'}and v['path'].startswith(str(OLD)):
     target=D/Path(v['path']).relative_to(OLD);target=target.with_name('observe_conversion_postjoin.py')if target.name=='observe_conversion_frontier.py'else target
     return ref(target)if target.exists()else None
    return {k:route(x)for k,x in v.items()}
   if isinstance(v,str):return v.replace(str(OLD),str(D))
   return v
  data=route(data)
  if name=='ROOT-OBSERVER-BINDING.TEMPLATE.NOT-AUTHORITY.json':data.update(current_ledger=pins['root70_pending_ledger'],current_boundary=pins['root69_boundary'],current_free=pins['previous_free']);data.pop('post_root68_custody_supplement',None);data.pop('post_root68_resource1_custody_supplement',None)
  if name=='INDEPENDENT-OBSERVER-REVIEW.TEMPLATE.NOT-AUTHORITY.json':data.update(current_ledger=pins['root70_pending_ledger'],current_boundary=pins['root69_boundary'],current_free=pins['previous_free'])
  write(name,data)
 write('SOURCE-DELTA.patch',''.join(difflib.unified_diff((OLD/'observe_conversion_frontier.py').read_text().splitlines(True),obs.splitlines(True),fromfile='accepted_root69_observer',tofile='new_postretirement_observer')))
 print('SOURCE_DATA_ONLY_PREPARED')
if __name__=='__main__':main()
