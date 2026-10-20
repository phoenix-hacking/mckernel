from pathlib import Path
import json,hashlib,time,subprocess,importlib.util
D=Path(__file__).resolve().parent;O=D/'cli-check-1'
s=importlib.util.spec_from_file_location('assembly',D/'machine_assembly_caller.py');a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
ref={'model':'disposable CLI temporal fixture, not execution authority'}
base=dict(execution_count=1,runtime_release=False,fresh_live_preflight=None,parent_identity={'model':'disposable'},exclusive_queue_predecessor=ref,terminal_cleanup_and_common_shared_release=a.predecessor_contract(ref))
snap=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=time.time(),parent_identity=base['parent_identity'],terminal_acceptance=ref)
def write(name,value):
 p=O/name;raw=(json.dumps(value)+'\n').encode();p.write_bytes(raw);return p,hashlib.sha256(raw).hexdigest()
b,bsha=write('modeled-base.json',base);n,nsha=write('modeled-snapshot.json',snap)
argv=['/home/holden/anaconda3/bin/python3.9','-I','-B',str(D/'machine_assembly_caller.py'),str(b),bsha,str(n),str(O/'modeled-output.json'),None]
# This is the actual accepted seven-caller late-slot operation.
argv[-1]=nsha
p=subprocess.run(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
assert not p.stderr;summary=json.loads(p.stdout);raw=(O/'modeled-output.json').read_bytes();assert summary==dict(path=str(O/'modeled-output.json'),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
assert json.loads(raw)['fresh_live_preflight']==dict(path=str(n),sha256=nsha,bytes=n.stat().st_size)
write('RESULT.json',dict(status='PASS',cases=1,scope='disposable modeled CLI only, no actual snapshot or execution authority',actual_argv=argv,summary=summary))
print(json.dumps(dict(status='PASS',cases=1)))
