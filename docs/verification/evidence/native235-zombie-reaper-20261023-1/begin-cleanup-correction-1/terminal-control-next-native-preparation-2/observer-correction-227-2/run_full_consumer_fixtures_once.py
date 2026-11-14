# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import importlib.util,json,hashlib,os
P=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted_owned_capture',H);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
source=json.loads((P/'SOURCE-CANDIDATE-EXPERT-CORRECTION.json').read_text());assert hashlib.sha256((P/'native_diagnostic.py').read_bytes()).hexdigest()==source['candidate_sha256'];assert hashlib.sha256((P/'test_full_consumer.py').read_bytes()).hexdigest()==source['fixture_sha256']
argv=['/usr/bin/taskset','--cpu-list','0','/usr/bin/prlimit','--as=2147483648','--cpu=60','--core=0','--fsize=33554432','--nofile=256','--','/home/holden/anaconda3/bin/python3','-I','-B',str(P/'test_full_consumer.py')]
out=P/'actual-full-consumer-fixtures-2';out.mkdir(mode=0o700)
command=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',argv=argv,source=source,host_envelope='Old451c fixture retains its explicit modeled envelope; new6e2fc958 actual full observation uses its real collected host timestamps unchanged. Tests grant no native acceptance.')
m.write(out/'command.json',command)
result=m.owned_capture(command,out,90,lambda:None);m.write(out/'status.json',result)
print(json.dumps({k:result[k]for k in ['returncode','direct_child_joined','group_absent','closed_streams','seconds','error','retirement_error']}))
if result['returncode']!=0 or not result['direct_child_joined']or not result['group_absent']or result['error']or result['retirement_error']:raise SystemExit(1)
