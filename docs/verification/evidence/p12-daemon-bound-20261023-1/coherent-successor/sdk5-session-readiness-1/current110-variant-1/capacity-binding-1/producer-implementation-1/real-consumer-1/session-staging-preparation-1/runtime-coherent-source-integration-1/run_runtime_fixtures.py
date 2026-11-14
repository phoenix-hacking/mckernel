"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-granted ordinary CPU6 fixture; publication is executed only in the captured child.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,resource
D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('accepted_owned_capture',H);h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
packet=json.loads((D/'NEXT-BOUND-MANIFEST-AND-HOOKS.NOT-RELEASED.json').read_text());manifest=packet['readonly_manifest_publication']['destination']
# Captured child exclusively publishes the authorized exact manifest input.
a=D/'attempt-1';a.mkdir()
for p in D.iterdir():
 if p.is_file():(a/p.name).write_bytes(p.read_bytes())
os.sched_setaffinity(0,{6});os.chdir(D)
for k,v in ((resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)):resource.setrlimit(k,(v,v))
c=a/'actual-runtime-cohort-fixture';c.mkdir();command={'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'fixture_runtime_cohort.py'),'--manifest',manifest],'purpose':__doc__,'shell':False}
h.write(c/'command.json',command);joined=h.owned_capture(command,c,90,lambda:None);h.write(c/'result.json',joined)
print(json.dumps(joined))
