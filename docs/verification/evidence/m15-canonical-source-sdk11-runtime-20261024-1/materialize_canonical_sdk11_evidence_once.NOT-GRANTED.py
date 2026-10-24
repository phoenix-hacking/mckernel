"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-owned ordinary finite evidence publication only: source tar, small bound
metadata/four adjacent sources, and nine actual current physical records.
No product, compiler, Docker, query, Git or native execution; no overwrite.
"""
from pathlib import Path,PurePosixPath
import gzip,hashlib,io,json,os,stat,sys,tarfile
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
SPEC={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/selected-source-1/publication-admission-preparation-1/canonical-publication-preparation-1/EXACT-FINITE-CANONICAL-EVIDENCE-PUBLICATION.json', 'sha256': 'd50c36fc408f7d4e29a89af4e5de3f535ebc6798d2f21f374a789f6b3e3bfcd3', 'bytes': 8913}
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
 need(os.getuid()==os.geteuid()==1000,'ordinary UID1000 publication')
 need(sys.argv[1:]==['--materialize-evidence-once',digest(Path(__file__).read_bytes())],'exact immutable helper argv')
 spec=json.loads(read(SPEC));destination=Path(spec['destination'])
 need(destination.parent.resolve()==destination.parent and not os.path.lexists(destination),'fresh canonical evidence directory')
 need(len(spec['files'])==17 and spec['target_members']==66 and spec['retirement_members']==9 and spec['adjacent_source_count']==4,'finite reviewed publication counts')
 inputs=json.loads(read(spec['source_manifest']));receipt=json.loads(read(spec['source_archive_receipt']))
 need(receipt['archive']==spec['source_archive'] and receipt['manifest']==spec['source_manifest'] and receipt['member_count']==66,'actual source archive receipt join')
 packed=read(spec['source_archive'])
 with gzip.GzipFile(fileobj=io.BytesIO(packed),mode='rb') as stream:
  tar=stream.read((32<<20)+1);need(len(tar)<32<<20 and not stream.read(1),'bounded complete source tar')
 with tarfile.open(fileobj=io.BytesIO(tar),mode='r:') as archive:
  members=archive.getmembers();need(len(members)==66 and {m.name for m in members}==set(inputs['members']),'exact66 member set')
  for member in members:
   path=PurePosixPath(member.name);need(member.isfile() and not path.is_absolute() and '..' not in path.parts,'regular relative source member')
   expected=inputs['members'][member.name];payload=archive.extractfile(member).read()
   need(len(payload)==expected['bytes'] and digest(payload)==expected['sha256'],'actual source tar member pin')
   need(payload==read(expected),'retained source member equals current original bytes')
 blobs={name:read(row) for name,row in spec['files'].items()}
 need(sum(len(b) for b in blobs.values())<32<<20,'bounded complete publication growth')
 destination.mkdir(mode=0o700);published={}
 for name,raw in sorted(blobs.items()):
  relative=PurePosixPath(name);need(not relative.is_absolute() and '..' not in relative.parts,'finite canonical output path')
  out=destination/name;out.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
  published[name]=publish(out,raw)
 for name,row in spec['files'].items():need(read(row)==blobs[name],'source postflight bytes')
 record=dict(scope=__doc__,status='PASS_FINITE_CANONICAL_SOURCE_EVIDENCE_MATERIALIZATION_ONLY',
  input_spec=SPEC,published=published,target_members=66,retirement_members=9,adjacent_sources=4,
  source_manifest_sha256=spec['source_manifest']['sha256'],source_archive_sha256=spec['source_archive']['sha256'],
  canonical_source_or_runtime_code_written=False,compiler_query_container_guest=False,
  commit=None,fetched_commit=None,tree=None,execution_release=False)
 result=publish(destination/'ACTUAL-PUBLICATION.json',(json.dumps(record,sort_keys=True,indent=2)+'\n').encode())
 print(json.dumps(dict(publication_receipt=result,**record),sort_keys=True))
if __name__=='__main__':main()
