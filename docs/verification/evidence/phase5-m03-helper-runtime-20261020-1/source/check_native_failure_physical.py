"""Whole saved actual39cd projection and coupled assembly, no live snapshot."""
from pathlib import Path
import importlib.util,json,copy
D=Path(__file__).resolve().parent
def load(name):
 s=importlib.util.spec_from_file_location(name,D/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
p=load('native_failure_physical_projection');a=load('machine_assembly')
def refuses(call):
 try:call()
 except (AssertionError,ValueError):return
 raise AssertionError('negative accepted')
ctx=p.checked(p.CONTEXT_REF);ref=ctx['physical'];t=p.checked(ref)
actual=p.project(t,ref)
# Assembly inputs below model only temporal fields; no runtime document is published.
base=dict(execution_count=1,runtime_release=False,fresh_live_preflight=None,parent_identity={'model':'unchanged-parent'},exclusive_queue_predecessor=ref,terminal_cleanup_and_common_shared_release=a.predecessor_contract(ref))
snapshot=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=100,parent_identity=base['parent_identity'],terminal_acceptance=ref)
assert a.assemble(base,snapshot,101,{'model':'not-live-snapshot'})['runtime_release'] is True
wrong=copy.deepcopy(t);wrong['schema']='mckernel.independent-current-image.quarantine-recovery-physical.v1';refuses(lambda:p.kind(wrong))
status=p.checked(t['completed_statuses'][1]);row=copy.deepcopy(status['streams']['stderr']);row['metadata']['inode']+=1;refuses(lambda:p.captured_bytes(row))
wrong=copy.deepcopy(base);wrong['terminal_cleanup_and_common_shared_release']['ref']=dict(ref,sha256='0'*64);refuses(lambda:a.assemble(wrong,snapshot,101,{'model':'not-live-snapshot'}))
result=dict(status='PASS',cases=['whole_actual39cd_and_coupled_assembly','wrong_kind_refused','changed_actual_stream_identity_refused','changed_assembly_predecessor_refused'],actual_projection=actual,physical=ref,scope='saved physical retirement only; assembly temporal fields explicitly modeled; no runtime/native acceptance')
with (D/'physical-check-1'/'RESULT.json').open('x') as output:json.dump(result,output,indent=2);output.write('\n')
print(json.dumps(dict(status='PASS',cases=4)))
