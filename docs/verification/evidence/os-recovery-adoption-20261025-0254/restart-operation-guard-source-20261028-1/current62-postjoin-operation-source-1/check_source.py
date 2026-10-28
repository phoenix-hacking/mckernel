"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Single-process CPU0/AS2GiB pure source checks. No live guard/query/operation call.
"""
import copy
import datetime
import importlib.util
import json
import os
from pathlib import Path
import resource
import tempfile

os.sched_setaffinity(0,{0})
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('guard62',HERE/'operation_window_guard62.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
OP='bfd-postjoin-current62'
positives=0
negatives=0

def fixture():
 subjects={'Root62observer':{'path':'/fixture/observer.py','bytes':1,'sha256':'0'*64}}
 s=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',
        operation=OP,decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',window_sha256=g.WINDOW_SHA256,
        first_prepared_window_sha256=g.WINDOW_SHA256,credit_run_id=g.RUN,credit_ceiling=g.CEILING,
        predecessor_cutoffs=None,operation_cutoffs=[1793253600,1035704.5689393478,1051042.6959879305],
        subjects=subjects,source_owners=['/root','/root/m14_compose','/root/bfd_route','/root/restart_guard'],
        minimum_cumulative_spent='22812.3311',guardian=dict(source=g.GUARDIAN_SOURCE.copy(),entrypoint='guard'))
 r=dict(schema='mckernel.independent-operation-window-review.v1',
        decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,reviewer='/root/reviewer62',
        operation=OP,successor=copy.deepcopy(s))
 return s,r,subjects

def validate(s,r,subjects,op=OP,clocks=(1793216000,997600,1013000)):
 return g.validate_operation(s,r,op,subjects,clocks,g.BOOT)

def reject(call):
 global negatives
 try:call()
 except (ValueError,KeyError,TypeError):negatives+=1
 else:raise AssertionError('negative source check accepted')

assert g.PREDECESSOR_CUTOFFS=={OP:None}
assert validate(*fixture())==(1793253600,1035704.5689393478,1051042.6959879305);positives+=1
assert g.GUARDIAN_SOURCE['sha256']=='48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18'
assert g.reference(Path(g.GUARDIAN_SOURCE['path']))==g.GUARDIAN_SOURCE;positives+=1
assert g.load_window()['boot_deadline']==1051044.6960026678;positives+=1
for op in ('current118-build','current116','bfd-current-default-two-tools'):
 reject(lambda op=op:validate(*fixture(),op=op))
for key,value in [('predecessor_cutoffs',[]),('predecessor_cutoffs',[1793165769,947874,963213]),
                  ('first_prepared_window_sha256','0'*64),('author',None),('credit_run_id','reset'),
                  ('credit_ceiling','57775'),('minimum_cumulative_spent','0'),
                  ('guardian',dict(source=dict(g.GUARDIAN_SOURCE,sha256='e8a117df7b80143fe3f095e23f2847462dde1e2f3b4fac331969ec6f3ac1ae2d'),entrypoint='guard'))]:
 s,r,subjects=fixture();s[key]=value;r['successor']=copy.deepcopy(s)
 reject(lambda:validate(s,r,subjects))
for i in range(3):
 s,r,subjects=fixture();s['operation_cutoffs'][i]+=1;r['successor']=copy.deepcopy(s)
 reject(lambda:validate(s,r,subjects))
 s,r,subjects=fixture();clocks=[1793216000,997600,1013000];clocks[i]=s['operation_cutoffs'][i]
 reject(lambda:validate(s,r,subjects,clocks=clocks))
s,r,subjects=fixture();reject(lambda:validate(s,r,{'wrong':subjects['Root62observer']}))
for owner in s['source_owners']:
 bad=copy.deepcopy(r);bad['reviewer']=owner;reject(lambda:validate(s,bad,subjects))
state=json.loads((g.PREDECESSOR.parent/'ACCOUNT-FIXTURE.json').read_bytes())
state['thread_id']='01a183ec-72e5-7400-8f48-b4efb8725520'
wall=datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp()+1
assert g.check_account_state(state,wall,'22812.3311')>0;positives+=1
for thread in ('01a18111-26a7-7ef2-bbd6-e33d1c8dc803','other'):
 bad=copy.deepcopy(state);bad['thread_id']=thread;reject(lambda:g.check_account_state(bad,wall,'22812.3311'))
for key in ('service_hold','policy_hold','auth_hold','billing_hold','stop_now'):
 bad=copy.deepcopy(state);bad[key]=True;reject(lambda:g.check_account_state(bad,wall,'22812.3311'))
reject(lambda:g.check_account_state(state,wall+180,'22812.3311'))
with tempfile.TemporaryDirectory(dir=HERE) as folder:
 folder=Path(folder);s,r,subjects=fixture()
 for name,value in [('successor',s),('review',r)]:
  (folder/(name+'.json')).write_text(json.dumps(value))
 config=dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation=OP,
             shared_guard=g.reference(HERE/'operation_window_guard62.py'),
             successor=g.reference(folder/'successor.json'),review=g.reference(folder/'review.json'),subjects=subjects)
 path=folder/'config.json';path.write_text(json.dumps(config))
 spec=importlib.util.spec_from_file_location('adapter62',HERE/'current62_guard_adapter.py')
 adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
 reject(adapter.current_cutoffs)
 adapter.configure(g.reference(path));assert adapter.current_cutoffs()==g.OPERATION_CUTOFFS;positives+=1
 reject(lambda:adapter.configure(g.reference(path)))
 path.write_text('{}');reject(adapter.current_cutoffs)
for path in HERE.glob('*.TEMPLATE.NOT-AUTHORITY.json'):
 t=json.loads(path.read_bytes())
 for key in ('author','decision','subjects','successor','reviewer','independent','review'):
  if key in t:assert t[key] is None,(path,key)
 positives+=1
print(json.dumps(dict(status='PASS_PURE_SOURCE_ONLY',positive_checks=positives,negative_checks=negatives,
                     affinity=sorted(os.sched_getaffinity(0)),jobs=1,address_space_bytes=resource.getrlimit(resource.RLIMIT_AS),
                     live_guard_calls=0,query_calls=0,subprocesses=0)))
