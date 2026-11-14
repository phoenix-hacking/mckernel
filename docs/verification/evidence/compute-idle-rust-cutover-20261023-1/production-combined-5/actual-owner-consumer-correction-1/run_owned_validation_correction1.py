"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One reviewed CPU6 ordinary pure-validation capture; no build, root or Docker.
"""
import ast,hashlib,json,os
from pathlib import Path
D=Path(__file__).resolve().parent
SOURCE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
body=[]
for n in ast.parse(raw,str(SOURCE)).body:
 if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets):body.append(n)
ns={'__file__':str(SOURCE)};exec(compile(ast.Module(body=body,type_ignores=[]),str(SOURCE),'exec'),ns)
command={'argv':['/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=2147483648','--cpu=60','--fsize=33554432','--nofile=256','--core=0','/home/holden/anaconda3/bin/python3','-I','-B',str(D/'test_actual_pure_validator.py')]}
cap=D/'pure-validator-capture-correction1';cap.mkdir(mode=0o700)
ns['write'](cap/'command.json',command)
result=ns['owned_capture'](command,cap,90,lambda:None)
ns['write'](cap/'whole-join.json',result)
assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,result
print(json.dumps(result,sort_keys=True))
