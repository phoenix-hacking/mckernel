"""Five bounded saved-evidence witnesses; no live collector or release."""
from pathlib import Path
import copy,importlib.util,json
D=Path(__file__).resolve().parent
def load(name):
 s=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def refuses(call):
 try:call()
 except (AssertionError,ValueError):return
 raise AssertionError('negative accepted')
p=load('native_positive_physical_projection');a=load('machine_assembly_caller');c=load('root_manual_snapshot_m03')
ctx=p.checked(p.CONTEXT_REF);ref=ctx['physical'];t=p.checked(ctx['physical_FD']);overlay=json.loads((D/'PROPOSED-CALLER-BINDING-OVERLAY.json').read_bytes())
c.terminal_joins(t,overlay)
wrong=copy.deepcopy(t);wrong['schema']='mckernel.independent-current-v6-sdk.actual-physical-retirement.v1';refuses(lambda:p.kind(wrong))
wrong=copy.deepcopy(ctx['physical_FD']);wrong['inode']+=1;refuses(lambda:p.read_bytes(wrong))
raw={k:p.captured_bytes(v) for k,v in t['archived_record_FDs'].items()};owner=p.tar_members(raw['owner'],100);attempt=p.tar_members(raw['attempt'],6);result=json.loads(raw['result'])
wrong=copy.deepcopy(t);badowner=copy.deepcopy(owner);name='./001-ps.json';client=json.loads(badowner[name]);client['command']['sid']+=1;badowner[name]=json.dumps(client).encode();wrong['docker_clients'][0]['command']=client['command']
refuses(lambda:p.ownership_join(wrong,badowner,attempt,result))
base=dict(execution_count=1,runtime_release=False,fresh_live_preflight=None,parent_identity={'model':'unchanged-parent'},exclusive_queue_predecessor=ref,terminal_cleanup_and_common_shared_release=a.predecessor_contract(ref))
snapshot=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=100,parent_identity=base['parent_identity'],terminal_acceptance=ref)
assert a.assemble(base,snapshot,101,{'model':'not-live-snapshot'})['runtime_release'] is True
wrong=copy.deepcopy(base);wrong['terminal_cleanup_and_common_shared_release']['ref']=dict(ref,sha256='0'*64);refuses(lambda:a.assemble(wrong,snapshot,101,{'model':'not-live-snapshot'}))
result=dict(status='PASS',cases=['genuine_complete_6f42_native_positive_through_existing_terminal_caller','SDK_kind_refused','changed_full_report_FD_identity_refused','self_consistent_changed_client_host_SID_refused','modeled_assembly_positive_and_changed_predecessor_refused'],physical=ref,actual_projection=overlay['physical_predecessor'],actual_projection_calls=1,M03_source_tuple_changes=[],scope='Saved native-positive physical retirement only; temporal assembly fields modeled; no semantic/native/module/app acceptance or live snapshot')
with (D/'ordinary-check-1'/'RESULT.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print(json.dumps(dict(status='PASS',witnesses=5,actual_projection_calls=1)))
