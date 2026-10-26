"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Invoke the existing990 owned-capture API for one independently released read-only query.
"""
from pathlib import Path
import json,hashlib,types,resource,os
A=Path(__file__).resolve().parent
source=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
m=types.ModuleType('existing_owned_capture');m.__file__=str(source);exec(compile(raw,str(source),'exec'),m.__dict__)
command=json.loads((A/'QUERY-COMMAND.EXACT.json').read_bytes());P=A/'QUERY-CAPTURE';P.mkdir(mode=0o700)
def limits():
 os.sched_setaffinity(0,{2,3,4,5});resource.setrlimit(resource.RLIMIT_AS,(2147483648,2147483648));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
result=m.owned_capture(command,P,30,limits)
raw=(P/'stdout').read_bytes();result['stdout']=dict(path=str(P/'stdout'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest());result['capture_helper']=dict(path=str(source),bytes=len(source.read_bytes()),sha256=hashlib.sha256(source.read_bytes()).hexdigest());result['joined']=result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None
with (A/'QUERY-WHOLE-JOIN.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps({k:result[k] for k in ['pid','returncode','direct_child_joined','group_absent','closed_streams','error','retirement_error','timed_out','seconds']}),flush=True)
