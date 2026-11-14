"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read exact published final release through unmodified production validator with real clock/boot. No workload.
"""
import hashlib,importlib.util,json,os,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent
assert len(sys.argv)==3 and sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12) and os.getuid()==os.geteuid()==1000
p=Path(sys.argv[1]);assert str(p)=='/home/holden/mckernel-work/scratch/p12s5l2/r.json'
spec=importlib.util.spec_from_file_location('exact_production_release_consumer',D/'source/long_transport.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
raw=g.stable(p);assert g.digest(raw)==sys.argv[2];v=json.loads(raw);payload=g.canonical({k:x for k,x in v.items() if k!='independent_review'})
value=g.validate_release(str(p),sys.argv[2],'/home/holden/mckernel-work/scratch/p12s5l2/m.json','dfbb3adb1c7d45b689a899140f3afffc','/home/holden/mckernel-work/native-runs/l12b1/p')
out=D/'actual-final-release-consumer-1';out.mkdir(mode=0o700)
for name,b in [('exact-final-release.json',raw),('exact-payload.canonical',payload)]:
 with (out/name).open('xb') as f:f.write(b)
r=dict(scope=__doc__,status='PASS_ACTUAL_FINAL_SERIALIZED_RELEASE_FULL_PRODUCTION_CONSUMER',release_path=str(p),release_sha256=g.digest(raw),canonical_payload_sha256=g.digest(payload),canonical_terminal_byte=payload[-1],real_clock=True,real_boot=True,production_source_sha256=g.digest((D/'source/long_transport.py').read_bytes()),at_unix=time.time(),expires_unix=value['expires_unix'],root=0,Docker=0,owner=0,workload=0,execution_release=False,native_acceptance=False)
with (out/'RESULT.json').open('x') as f:json.dump(r,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(r,sort_keys=True))
