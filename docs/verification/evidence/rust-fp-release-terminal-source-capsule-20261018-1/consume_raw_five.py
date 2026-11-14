"""Consume only the exact five hash-bound observer JSON tar members."""
import hashlib,io,json,os,stat,tarfile
from pathlib import Path
D=Path('/home/holden/mckernel-work/host-preparation/rust-fp-release-terminal-preparation-20261018-1');P=D;J=D
ARCHIVE=D/'dispatcher-raw-five.stdout'
NAMES=('observer-result.json','observation.json','cleanup-release-draft.json','new-object-metadata.json','ownership.json')
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()+b'\n'
def validate(raw,d):
 assert len(raw)<=32<<20
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:') as tar:
  members=tar.getmembers();assert [m.name for m in members]==list(NAMES)
  data={}
  for m in members:
   assert m.isfile() and m.type==tarfile.REGTYPE and not m.linkname and not m.pax_headers and m.sparse is None
   assert m.uid==m.gid==0 and m.mode==0o600 and 0<m.size<=32<<20
   b=tar.extractfile(m).read();assert len(b)==m.size and sha(b)==d['file_sha256'][m.name];data[m.name]=b
 values={n:json.loads(b) for n,b in data.items()}
 assert values['observer-result.json']==d['result'] and values['new-object-metadata.json']==d['new_object_metadata'] and values['ownership.json']==d['ownership']
 obs=values['observation.json'];draft=values['cleanup-release-draft.json']
 assert draft['status']=='NOT_RELEASED' and draft['observation']==obs
 assert sha(canon(obs))==d['cleanup_draft']['observation_canonical_sha256']
 assert {k:v for k,v in draft.items() if k!='observation'}=={k:v for k,v in d['cleanup_draft'].items() if k!='observation_canonical_sha256'}
 for k,v in d['observation'].items():
  if k=='inventories':assert {p:dict(entries=len(rows),canonical_sha256=sha(canon(rows))) for p,rows in obs[k].items()}==v
  else:assert obs[k]==v
 return data,values

def main():
 d=json.loads((J/'dispatcher-readback.stdout').read_bytes())
 st=json.loads((D/'dispatcher-raw-five.status.json').read_bytes());assert st['returncode']==0 and st['direct_child_joined'] is True
 assert not (D/'dispatcher-raw-five.stderr').read_bytes()
 assert ARCHIVE.stat().st_size<=32<<20
 data,values=validate(ARCHIVE.read_bytes(),d)
 dest=D/'raw-five-files';dest.mkdir(mode=0o700);assert dest.stat().st_uid==1000 and stat.S_IMODE(dest.stat().st_mode)==0o700
 for name in NAMES:
  fd=os.open(dest/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(data[name]);f.flush();os.fsync(f.fileno())
 report=dict(status='PASS_EXACT_RAW_FIVE_OBSERVER_FILES',archive_sha256=sha(ARCHIVE.read_bytes()),file_sha256={n:sha(data[n]) for n in NAMES},members=5,selected_rows=len(values['observation.json']['selected_files']),inventory_entries={p:len(rows) for p,rows in values['observation.json']['inventories'].items()},full_draft_restored=True,privileged_execution=False)
 with (D/'raw-five-join.json').open('x') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps(report))
if __name__=='__main__':main()
