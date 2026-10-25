"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One source/currentauthority metadata overlay, no archive/provider/compiler/query/Git calls.
"""
from pathlib import Path,PurePosixPath
import hashlib,json,os,stat,sys
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
SPEC = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-user-rustc-source-4/fresh-suffix-static-cohort-source-1/EXACT-TWENTYTWO-F4D-AUTHORITY-OVERLAY.SOURCE17-FETCH-BOUND.json', 'bytes': 11876, 'sha256': '336eba12b3ac84b020139dec0188db6c337a42ad147cfee82406c5a85c3dc9bd'}
def need(v,m):
 if not v:raise ValueError(m)

def digest(b):return hashlib.sha256(b).hexdigest()

def read(ref):
 p=Path(ref['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1,'regular singlelink source/data input')
  blocks=[];size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   size+=len(block);need(size<=32<<20,'bounded source/data input');blocks.append(block)
  raw=b''.join(blocks);after=os.fstat(fd);named=p.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS) and size==after.st_size,'stable9 source/data identity (atime excluded)')
  need(digest(raw)==ref['sha256'] and len(raw)==ref['bytes'],'source/data pin '+str(p));return raw
 finally:os.close(fd)

def publish(path,raw,mode=0o600):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,mode)
 try:
  os.fchmod(fd,mode)
  with os.fdopen(fd,'wb',closefd=False) as f:f.write(raw);f.flush();os.fsync(fd)
 finally:os.close(fd)
 parent=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(parent)
 finally:os.close(parent)
 return dict(path=str(path),sha256=digest(raw),bytes=len(raw))

def main():
 need(os.getuid()==os.geteuid()==1000,'ordinary publication UID')
 need(sys.argv[1:]==['--publish-overlay-once',digest(Path(__file__).read_bytes())],'exact sourcebound argv')
 spec=json.loads(read(SPEC));destination=Path(spec['destination'])
 need(len(spec['files'])==spec['member_count']==22 and spec['retirement_members']==16,'finite small overlay counts')
 need(destination.parent.resolve()==destination.parent and not os.path.lexists(destination),'fresh exact canonical overlay')
 blobs={name:read(row) for name,row in spec['files'].items()};need(sum(map(len,blobs.values()))<32<<20,'bounded overlay growth')
 destination.mkdir(mode=0o700);published={}
 for name,raw in sorted(blobs.items()):
  rel=PurePosixPath(name);need(not rel.is_absolute() and '..' not in rel.parts,'finite relative overlay path')
  out=destination/name;out.parent.mkdir(mode=0o700,parents=True,exist_ok=True);published[name]=publish(out,raw)
 for name,row in spec['files'].items():need(read(row)==blobs[name],'source metadata postflight')
 result=dict(status='PASS_FINITE_INSTALL_CURRENT_AUTHORITY_OVERLAY_ONLY',input_spec=SPEC,published=published,base_source_proof=spec['base_source_proof'],member_count=22,retirement_members=16,source_archive_rebuilt=False,query_or_compiler_executed=False,execution_release=False)
 record=publish(destination/'ACTUAL-OVERLAY-PUBLICATION.json',(json.dumps(result,sort_keys=True,indent=2)+'\n').encode());print(json.dumps(dict(receipt=record,**result),sort_keys=True))
if __name__=='__main__':main()
