"""Exact finite post-direct-wait observer readback; no cleanup or Docker."""
import hashlib,json,os,stat
from pathlib import Path
OUTPUT = Path('/home/holden/mckernel-work/host-preparation/evening-four-leaf-production-20261019-1/heavy-proposal-1/terminal-preparation-1/root-observation-four-leaf-observation-cardinality-correction-1')
NONCE = 'four-leaf-observation-cardinality-correction-1'
NAMES=('observer-result.json','observation.json','cleanup-release-draft.json','new-object-metadata.json','ownership.json')
def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()+b'\n'
def digest(b):return hashlib.sha256(b).hexdigest()
def read_all():
 assert not any(p.is_symlink() for p in (OUTPUT,*OUTPUT.parents))
 parent=os.open(OUTPUT,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
 try:
  root=os.fstat(parent);assert stat.S_ISDIR(root.st_mode) and root.st_uid==0 and stat.S_IMODE(root.st_mode)==0o700
  data={};total=0
  for name in NAMES:
   fd=os.open(name,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
   try:
    before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_uid==0 and before.st_nlink==1 and 0<before.st_size<=128<<20
    total+=before.st_size;assert total<=256<<20
    with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(before.st_size+1)
    after=os.fstat(fd);fresh=os.stat(name,dir_fd=parent,follow_symlinks=False)
    fields=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    assert len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(fresh,k) for k in fields)
    data[name]=(raw,json.loads(raw))
   finally:os.close(fd)
  assert os.stat(OUTPUT,follow_symlinks=False).st_ino==root.st_ino
  return data
 finally:os.close(parent)
def summarize(data):
 result=data['observer-result.json'][1];observation=data['observation.json'][1];draft=data['cleanup-release-draft.json'][1];metadata=data['new-object-metadata.json'][1];owner=data['ownership.json'][1]
 assert result['status']=='PASS_READ_ONLY_OBSERVATION_ONLY' and result['nonce']==owner['nonce']==NONCE and result['cleanup_executed'] is False
 assert result['observation_sha256']==digest(data['observation.json'][0])
 assert result['cleanup_release_draft_sha256']==digest(data['cleanup-release-draft.json'][0])
 assert draft['status']=='NOT_RELEASED' and draft['observation']==observation
 draft_summary={k:v for k,v in draft.items() if k!='observation'}
 draft_summary['observation_canonical_sha256']=digest(canonical(observation))
 return dict(status='PASS_EXACT_FINITE_OBSERVER_READBACK_ONLY',nonce=NONCE,cleanup_authorized=False,application_acceptance=False,file_sha256={n:digest(data[n][0]) for n in NAMES},result=result,ownership=owner,cleanup_draft=draft_summary,new_object_metadata=metadata,observation=dict(selected_files=observation['selected_files'],inventories={p:dict(entries=len(rows),canonical_sha256=digest(canonical(rows))) for p,rows in observation['inventories'].items()},mount=observation['mount'],root_lock=observation['root_lock'],target=observation['target'],client_ledger=observation['client_ledger'],request_lease_absent=observation['request_lease_absent']))
if __name__=='__main__':
 assert os.getuid()==os.geteuid()==0
 raw=canonical(summarize(read_all()));assert len(raw)<=1<<20
 os.write(1,raw)
