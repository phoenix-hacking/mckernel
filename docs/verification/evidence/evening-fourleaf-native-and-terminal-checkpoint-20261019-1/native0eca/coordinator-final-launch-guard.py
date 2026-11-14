import os,sys,json,hashlib,time
from pathlib import Path
review_path,review_sha=sys.argv[1:]
raw=Path(review_path).read_bytes();assert hashlib.sha256(raw).hexdigest()==review_sha
r=json.loads(raw)
assert r['schema']=='mckernel.independent-fourleaf-native-exact-machine-release-review.v1'
assert r['decision']=='PASS_EXACT_FOURLEAF0ECA_MACHINE_RELEASE_AND_OWNER_INVOCATION'
m=r['machine_release'];raw=Path(m['path']).read_bytes();assert len(raw)==m['bytes']and hashlib.sha256(raw).hexdigest()==m['sha256']
d=json.loads(raw);assert hashlib.sha256((json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()==r['machine_projection_sha256']
a=['/home/holden/anaconda3/bin/python3','-I','-B',str(Path(m['path']).parent/'dispatch-runtime.py'),'--release',m['path'],'--release-sha256',m['sha256']]
assert a==r['allowed_argv']
f=d['fresh_live_preflight'];raw=Path(f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'];snap=json.loads(raw)
assert snap['time_epoch']==r['snapshot_time_epoch']and 0<=time.time()-snap['time_epoch']<=60
os.execve(a[0],a,os.environ.copy())
