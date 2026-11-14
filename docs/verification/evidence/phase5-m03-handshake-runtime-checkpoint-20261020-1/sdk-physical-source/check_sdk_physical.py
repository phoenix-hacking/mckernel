"""Five bounded witnesses. Model temporal fields only; publish no release."""
from pathlib import Path
import copy,importlib.util,json
D=Path(__file__).resolve().parent
def load(name):
 s=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def refuses(call):
 try:call()
 except (AssertionError,ValueError):return
 raise AssertionError('negative accepted')
p=load('sdk_physical_projection');a=load('machine_assembly_caller');c=load('root_manual_snapshot_m03')
ctx=p.checked(p.CONTEXT_REF);ref=ctx['physical'];t=p.checked(ctx['physical_FD']);overlay=json.loads((D/'PROPOSED-CALLER-BINDING-OVERLAY.json').read_bytes())
# Actual native caller invokes SDK project exactly once; no live collector.
c.terminal_joins(t,overlay)
wrong=copy.deepcopy(t);wrong['schema']='mckernel.independent-actual-m03-native-failure-physical-retirement-review.v1';refuses(lambda:p.kind(wrong))
wrong=copy.deepcopy(ctx['raw_record_FDs'][0]);wrong['inode']+=1;refuses(lambda:p.read_bytes(wrong))
receipt=p.checked(t['owner_receipt']);archive=p.checked(t['ownership_archive']);authorized=p.checked(t['record_release_authorized']);complete=p.checked(t['record_release_complete']);outer=p.checked(t['outer_status'])
wrong=copy.deepcopy(archive);badctx=copy.deepcopy(ctx);badauth=copy.deepcopy(authorized)
# Preserve equal data copies, then reject against genuine saved raw contents.
for rows in (wrong['records'],badctx['archived_owned_records'],badauth['records']):rows[0]['record']['nonce']='0'*32
refuses(lambda:p.record_join(t,badctx,receipt,wrong,badauth,complete,outer))
base=dict(execution_count=1,runtime_release=False,fresh_live_preflight=None,parent_identity={'model':'unchanged-parent'},exclusive_queue_predecessor=ref,terminal_cleanup_and_common_shared_release=a.predecessor_contract(ref))
snapshot=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=100,parent_identity=base['parent_identity'],terminal_acceptance=ref)
assert a.assemble(base,snapshot,101,{'model':'not-live-snapshot'})['runtime_release'] is True
wrong=copy.deepcopy(base);wrong['terminal_cleanup_and_common_shared_release']['ref']=dict(ref,sha256='0'*64);refuses(lambda:a.assemble(wrong,snapshot,101,{'model':'not-live-snapshot'}))
result=dict(status='PASS',cases=['whole_actual_SDK_through_existing_native_terminal_caller','wrong_kind_refused','changed_full_raw_FD_identity_refused','changed_whole_raw_record_refused','modeled_assembly_positive_and_changed_predecessor_refused'],physical=ref,actual_projection=overlay['physical_predecessor'],actual_projection_calls=1,M03_source_tuple_changes=[],scope='Saved SDK physical retirement only; temporal assembly fields explicitly modeled; no runtime/native/module/app acceptance or live snapshot')
with (D/'ordinary-check-1'/'RESULT.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print(json.dumps(dict(status='PASS',witnesses=5,actual_projection_calls=1)))
