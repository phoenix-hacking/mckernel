from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,subprocess
repo=Path('/home/holden/mckernel');out=Path('/home/holden/mckernel-work/scratch/stability-20260913-1/github-checkpoint11.json')
assert not out.exists()
r={'status':'RUNNING','started_utc':datetime.now(timezone.utc).isoformat(),'files':[],'scope':'Exact committed blobs fetched from GitHub, plus contemporaneous worktree equality or explicitly recorded subsequent changes'}
def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],timeout=180)
try:
 commit=git('rev-parse','HEAD').decode().strip();branch=git('branch','--show-current').decode().strip();r.update(commit=commit,branch=branch)
 r['fetch_output']=git('fetch','--no-tags','origin',branch).decode();fetched=git('rev-parse','FETCH_HEAD').decode().strip();assert fetched==commit;r['fetched_commit']=fetched
 paths=git('diff-tree','--no-commit-id','--name-only','-r','-z',commit).split(b'\0')
 for raw in paths:
  if not raw:continue
  path=raw.decode();data=git('show',commit+':'+path);remote=git('show','FETCH_HEAD:'+path);assert data==remote
  live=(repo/path).read_bytes();row={'path':path,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'fetched_exact':True,'worktree_exact':live==data}
  if live!=data:row.update(worktree_sha256=hashlib.sha256(live).hexdigest(),committed_prefix=live.startswith(data))
  r['files'].append(row)
 r['status']='PASS_COMMITTED_BLOBS'
except BaseException as e:r.update(status='FAIL',error=str(e));raise
finally:
 r['finished_utc']=datetime.now(timezone.utc).isoformat();out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');print(r['status'],len(r['files']),r.get('commit'))
