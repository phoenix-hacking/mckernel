"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted one bounded include-resolution correction; C/link/fixture suffix only.
"""
from pathlib import Path
import ast
import hashlib
import json
import os
import resource
import signal
import sys

D=Path(__file__).resolve().parent
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
RUST=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
def pin(p):
    raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,sort_keys=True);f.write('\n')
assert pin(RUST)['sha256']=='028fd60b0e0add5505c661cd3ccde91393d615c8729bd95d94ab1e91409b36a1'
assert pin(Path('/usr/bin/cc'))['sha256']=='6cb2d84ccd9fd3485d4e47ba032e626be65692601c38fad46866a6b565f3100f'
assert pin(HELPER)['sha256']=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
manifest=json.loads((D/'PARITY-FIXTURE-SOURCE-HANDOFF.HOLD.json').read_text())
for row in manifest['files']:assert pin(Path(row['path']))['sha256']==row['sha256'],row
functions={'need','write','hashed','stop','cpu_used','members','process_start','terminal_unreaped','wait_terminal','owned_capture'}
assignments={'FIELDS','stopping','CENSUS_SOURCE','CENSUS_SHA','_CENSUS','STOP_SIGNALS'}
nodes=[n for n in ast.parse(HELPER.read_bytes()).body if isinstance(n,(ast.Import,ast.ImportFrom)) or isinstance(n,ast.FunctionDef) and n.name in functions or isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in assignments for t in n.targets)]
ns={'__file__':str(HELPER)}
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(HELPER),'exec'),ns)
assert pin(Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-1/actual-parity-output-1/libio_parity.a')) == {'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-1/actual-parity-output-1/libio_parity.a', 'bytes': 20700860, 'sha256': '5425d9677b428c1a3ee0cba539c60acd7518e9192f64c7d6e3791996c29c9111'}
O=D/'actual-parity-output-correction-1';O.mkdir(mode=0o700)
CAP=D/'actual-parity-capture-correction-1';CAP.mkdir(mode=0o700)
os.environ['TMPDIR']=str(O)
os.environ['RUST_MIN_STACK']='2097152'
os.sched_setaffinity(0,{6})
os.chdir(O)
for sig in ns['STOP_SIGNALS']:signal.signal(sig,ns['stop'])
commands=[('00-Rust-fixture-staticlib',[str(RUST),'--edition=2021','--crate-type=staticlib','--crate-name','io_parity','--cfg','f03_io_diagnostic_callbacks_candidate','-C','opt-level=1','-C','panic=abort',str(D/'parity.rs'),'-o',str(O/'libio_parity.a')],60,90),
('01-C-original-link',['/usr/bin/cc','-std=gnu11','-O1','-Wall','-Wextra','-Werror','-I','/home/holden/mckernel/lib/include',str(D/'parity.c'),str(O/'libio_parity.a'),'-ldl','-lpthread','-lm','-o',str(O/'parity')],60,90),
('02-actual-original-C-Rust-parity',[str(O/'parity')],10,15)]
commands=commands[1:]
commands[0][1][commands[0][1].index('-I')]='-idirafter'
commands[0][1][commands[0][1].index(str(O/'libio_parity.a'))]='/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-1/actual-parity-output-1/libio_parity.a'
records=[]
try:
    write(CAP/'profile.json',dict(scope=SCOPE,authority='Root COPY7 accepted; explicit single bounded include-resolution correction grant; CPU6 onejob ordinary suffix only.',CPU=6,jobs=1,AS=2<<30,FSIZE=32<<20,NOFILE=256,STACK=2<<20,core=0,compiler_CPU=60,compiler_wall=90,fixture_CPU=10,fixture_wall=15,retirement=6,Rust=pin(RUST),C=pin(Path('/usr/bin/cc')),helper=pin(HELPER),driver=pin(Path(__file__)),source_manifest=pin(D/'PARITY-FIXTURE-SOURCE-HANDOFF.HOLD.json')))
    for name,argv,cpu,wall in commands:
        cap=CAP/name;cap.mkdir(mode=0o700)
        command=dict(scope=SCOPE,purpose='Functional diagnostic original-C/Rust parity only; no security testing: '+name,argv=argv,cwd=str(O))
        write(cap/'command.json',command)
        def limits():
            os.sched_setaffinity(0,{6})
            for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,cpu),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:resource.setrlimit(k,(v,v))
        joined=ns['owned_capture'](command,cap,wall,limits)
        write(cap/'whole-join.json',joined)
        records.append(dict(name=name,command=pin(cap/'command.json'),join=joined))
        assert joined['returncode']==0 and joined['direct_child_joined'] and joined['group_absent'] and joined['closed_streams'] and joined['error'] is None and joined['retirement_error'] is None and not joined['timed_out'],joined
    assert (CAP/'02-actual-original-C-Rust-parity/stdout').read_text()=='PASS controlled diagnostic parity 375 vectors plus 2 null-context wrappers\n'
    result=dict(scope=SCOPE,status='PASS_CONTROLLED_ACTUAL_ORIGINAL_C_RUST_DIAGNOSTIC_PARITY',vectors=375,null_contexts=2,records=records,CPU6_released=True,canonical_edits=False,full_actual_C_TU=False,native=False,default=False,file_retired=False,objects=[pin(Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-1/actual-parity-output-1/libio_parity.a')),pin(O/'parity')],reused_Rust_archive=pin(Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/new-window-source-1/actual-parity-output-1/libio_parity.a')),include_resolution_only_correction=True)
    write(D/'ACTUAL-PARITY-CORRECTION-RESULT-1.json',result)
    print(json.dumps(dict(status=result['status'],CPU6_released=True,receipt=pin(D/'ACTUAL-PARITY-CORRECTION-RESULT-1.json'))))
except BaseException as exc:
    result=dict(scope=SCOPE,status='STOP_FIRST_UNEXPECTED_RESULT_NO_RETRY',error=type(exc).__name__+': '+str(exc),records=records,CPU6_released=all(r['join']['direct_child_joined'] and r['join']['group_absent'] and r['join']['closed_streams'] for r in records))
    write(D/'ACTUAL-PARITY-CORRECTION-FAILURE-1.json',result)
    print(json.dumps(result));raise
