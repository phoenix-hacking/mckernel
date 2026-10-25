"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepared exact actual-bind CONFIG four-case wrapper; no execution until root CPU6 grant.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time

HERE=Path(__file__).resolve().parent
source=HERE/'publish_f4d_authority_overlay22.SOURCE17-FETCH-BOUND.py'
plan=HERE/'EXACT-TWENTYTWO-F4D-AUTHORITY-OVERLAY.SOURCE17-FETCH-BOUND.json'
for p,expected in [(source,'48f2d816749bb185423466d6cfd15f44deb9efef22e0c673b91965619dce314d'),(plan,'336eba12b3ac84b020139dec0188db6c337a42ad147cfee82406c5a85c3dc9bd')]:
    if hashlib.sha256(p.read_bytes()).hexdigest()!=expected:
        raise ValueError('exact root-granted source/plan hash changed')
if os.sched_getaffinity(0)!={6}:
    raise ValueError('root ordinary CPU6 grant binding required')
for kind,value in [(resource.RLIMIT_AS,512<<20),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,16<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:
    if resource.getrlimit(kind)!=(value,value):
        raise ValueError('exact ordinary resource envelope required')
helper=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=helper.read_bytes()
if hashlib.sha256(raw).hexdigest()!='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8':
    raise ValueError('reviewed h990 source changed')
functions={'need','write','hashed','stop','members','cpu_used','process_start','terminal_unreaped','wait_terminal','owned_capture'}
constants={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[]
for n in ast.parse(raw).body:
    if isinstance(n,(ast.Import,ast.ImportFrom)):
        nodes.append(n)
    elif isinstance(n,ast.FunctionDef) and n.name in functions:
        nodes.append(n)
    elif isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in n.targets):
        nodes.append(n)
if {n.name for n in nodes if isinstance(n,ast.FunctionDef)}!=functions:
    raise ValueError('exact reviewed capture closure')
h={'__file__':str(helper),'__name__':'executor_materialization_h990'}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(helper),'exec'),h)
capture=HERE/'actual-f4d-authority-overlay22-h990-1';capture.mkdir(mode=0o700)
command={'argv':['/usr/bin/python3','-I','-B',str(source),'--publish-overlay-once','48f2d816749bb185423466d6cfd15f44deb9efef22e0c673b91965619dce314d'],'scope':__doc__.splitlines()[0]}
h['write'](capture/'ROOT-GRANT.json',{'scope':command['scope'],'source_sha256':'48f2d816749bb185423466d6cfd15f44deb9efef22e0c673b91965619dce314d','plan_sha256':'336eba12b3ac84b020139dec0188db6c337a42ad147cfee82406c5a85c3dc9bd','CPU':6,'jobs':1,'AS_bytes':512<<20,'CPU_seconds':30,'wall_seconds':45,'cleanup_seconds':6,'FSIZE':16<<20,'NOFILE':256,'CORE':0,'scope_note':'Root granted finitef4d authorityoverlay22members16retirement, genuineSOURCE17/full11 sourcebound, no SDK/root/query/compiler/ownerimport/Docker/native.','compiler_or_owner_or_Docker_or_root_or_native_allowed':False})
h['write'](capture/'command.json',command)
for number in h['STOP_SIGNALS']:
    signal.signal(number,h['stop'])
start=time.monotonic();signal.setitimer(signal.ITIMER_REAL,45)
try:
    result=h['owned_capture'](command,capture,44,lambda:None)
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
result['whole_seconds']=time.monotonic()-start
result['total_CPU_seconds']=h['cpu_used']()
h['write'](capture/'status.json',result)
summary={key:result[key] for key in ('returncode','pid','start','direct_child_joined','group_absent','closed_streams','timed_out','error','retirement_error','whole_seconds','total_CPU_seconds')}
print(json.dumps(summary,indent=2))
raise SystemExit(0 if result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and not result['error'] and not result['retirement_error'] and result['total_CPU_seconds']<=30 else 1)
