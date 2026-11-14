import json,hashlib,subprocess,os,sys,time
from pathlib import Path
N=Path(__file__).resolve().parent
review_path,review_sha=sys.argv[1:]
assert hashlib.sha256(Path(review_path).read_bytes()).hexdigest()==review_sha
raw=(N/'native-late-selected-payload-latest-failed2-retired-2.json').read_bytes();assert hashlib.sha256(raw).hexdigest()=='6f590a1bed21f79ce7008bad88ac9600815aec2dda04abad11e105a6a2892e0d'
d=json.loads(raw);env=os.environ.copy();env.update(d['environment'])
a=d['commands']['root_snapshot']['argv'];a=[{'PENDING_ACTUAL_INDEPENDENT_STATIC_REVIEW_PATH':review_path,'PENDING_ACTUAL_INDEPENDENT_STATIC_REVIEW_SHA256':review_sha}.get(x,x)for x in a]
with(N/'snapshot-command.stdout').open('xb')as o,(N/'snapshot-command.stderr').open('xb')as e:
 t=time.monotonic();r=subprocess.run(a,cwd=N,env=env,stdout=o,stderr=e)
(N/'snapshot-command.status.json').write_text(json.dumps(dict(argv=a,returncode=r.returncode,direct_child_joined=True,elapsed_seconds=time.monotonic()-t))+'\n')
assert r.returncode==0,'snapshot refused; preserve captures'
s=N/'root-live-preflight-1.json';p=N/'root-snapshot-publication-1.json'
a=d['commands']['unprivileged_late_data_assembly']['argv'];a=[{'PENDING_ACTUAL_FRESH_SNAPSHOT_SHA256':hashlib.sha256(s.read_bytes()).hexdigest(),'PENDING_ACTUAL_ROOT_PUBLICATION_SHA256':hashlib.sha256(p.read_bytes()).hexdigest()}.get(x,x)for x in a]
with(N/'assembly-command.stdout').open('xb')as o,(N/'assembly-command.stderr').open('xb')as e:
 t=time.monotonic();r=subprocess.run(a,cwd=N,env=env,stdout=o,stderr=e)
(N/'assembly-command.status.json').write_text(json.dumps(dict(argv=a,returncode=r.returncode,direct_child_joined=True,elapsed_seconds=time.monotonic()-t))+'\n')
assert r.returncode==0,'assembly refused; preserve captures'
m=N/'machine-execution-release-1.json';print(json.dumps(dict(status='JOINED_SNAPSHOT_AND_ASSEMBLY',machine_path=str(m),machine_sha256=hashlib.sha256(m.read_bytes()).hexdigest(),snapshot_age=time.time()-json.loads(s.read_bytes())['time_epoch'])))
