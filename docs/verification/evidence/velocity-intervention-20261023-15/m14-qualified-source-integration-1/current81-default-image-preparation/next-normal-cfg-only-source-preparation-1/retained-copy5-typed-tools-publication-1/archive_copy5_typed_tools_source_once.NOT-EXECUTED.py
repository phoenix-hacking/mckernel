"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite reviewed normal-builder source retention; no compiler/tree/object/owner/query entry.
"""
from pathlib import Path
import os,stat,json,hashlib,gzip,tarfile,io
D=Path(__file__).parent
P=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/final-copy-bound-sdk-marker-continuation-1/bounded-generated-object-directory-correction-1/final-copy2-bound-runtime-and-admission-1/publication-admission-preparation-1/missing-native-fork-executor-dependency-diagnosis-1/current-executor-target-only-retained-suffix-1/final-copy3-bound-executor-runtime-and-admission-1/publication-admission-preparation-1/native-owned-fork-option-selection-source-successor-1/retained-current-syscall-relink-preparation-1/bounded-typed-tool-cache-correction-1/publication-admission-preparation-1/SOURCE-RETENTION.COPY5.ACTUAL-PURE.EXACT-MEMBERS.json')
raw=P.read_bytes();assert hashlib.sha256(raw).hexdigest()=='8083cc6ef065a12de5594b829f97f0202ee3348075fffd1714818f1ec169b871';m=json.loads(raw);assert len(m['members'])==21
FIELDS=('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns')
def read(r, maximum=33554432):
 p=Path(r['path']);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size==r['bytes']<=maximum
  chunks=[]
  while True:
   q=os.read(fd,65536)
   if not q:break
   chunks.append(q)
  b=b''.join(chunks);after=os.fstat(fd);named=p.lstat();assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in FIELDS);assert len(b)==r['bytes'] and hashlib.sha256(b).hexdigest()==r['sha256'];return b
 finally:os.close(fd)
def put(p,b):
 assert len(b)<33554432;fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(b);f.flush();os.fsync(f.fileno())
 return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
archive=D/'COPY5-TYPED-TOOLS-SOURCE.tar.gz';request=D/'image-request.TYPED-TOOLS.COPY5-BOUND.json.gz';receipt=D/'SOURCE-RETENTION.json';assert all(not os.path.lexists(p) for p in [archive,request,receipt]);data={n:read(r) for n,r in m['members'].items()};bio=io.BytesIO()
with gzip.GzipFile(fileobj=bio,mode='wb',filename='',mtime=0) as g:
 with tarfile.open(fileobj=g,mode='w',format=tarfile.USTAR_FORMAT) as t:
  for name,b in sorted(data.items()):
   i=tarfile.TarInfo(name);i.size=len(b);i.mode=0o600;i.uid=i.gid=0;i.mtime=0;t.addfile(i,io.BytesIO(b))
a=put(archive,bio.getvalue());raw_request=read(m['raw_request'], maximum=m['raw_request']['bytes']);rg=io.BytesIO()
with gzip.GzipFile(fileobj=rg,mode='wb',filename='',mtime=0) as g:g.write(raw_request)
r=put(request,rg.getvalue());assert gzip.decompress(rg.getvalue())==raw_request
with tarfile.open(fileobj=io.BytesIO(bio.getvalue()),mode='r:gz') as t:
 assert len(t.getmembers())==21
 for name,b in data.items():assert t.extractfile(name).read()==b
out={'scope':__doc__,'status':'PASS_FINITE_COPY5_SOURCE_AND_EXACT_REQUEST_RETENTION_ONLY','members':m['members'],'member_count':21,'archive':a,'request_gzip':r,'request_raw':m['raw_request'],'materialized_tree_included':False,'objects_included':False,'actual_request_validation_reused':True,'no_new_build':True};z=put(receipt,(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n').encode());print(json.dumps({'archive':a,'request_gzip':r,'receipt':z}))
