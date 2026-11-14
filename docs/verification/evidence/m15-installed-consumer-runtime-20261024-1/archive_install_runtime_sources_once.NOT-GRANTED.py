"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One finite actual COPY5 source archive. No compiler/container/query/object inputs.
Stable9 reads and exclusive fsync publication reuse accepted actual publisher.
"""
from pathlib import Path, PurePosixPath
import gzip,hashlib,io,json,os,stat,sys,tarfile
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')

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
    need(os.getuid()==os.geteuid()==1000,'ordinary source publication UID')
    need(sys.argv[1:]==['--archive-once',digest(Path(__file__).read_bytes())],'exact source command pin')
    manifest_ref={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/EXACT-INSTALL-RUNTIME-SOURCE-INPUTS.json', 'sha256': 'f3ac08c2d56ca537dc09ff9fd11d2bbb14c89af2b337fec4bbafe774cedeb3b5', 'bytes': 12130}
    raw=read(manifest_ref);manifest=json.loads(raw)
    need(manifest['member_count']==15 and manifest['no_object_or_binary_build_outputs'] is True,'fixed actual source-only membership')
    names=sorted(manifest['members'])
    need(len(names)==len(set(names))==15,'unique fixed archive members')
    output=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/publication-admission-preparation-1/SOURCE-ONLY-SELECTED-INSTALL-RUNTIME.tar.gz')
    need(not os.path.lexists(output),'fresh exclusive source archive')
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w',format=tarfile.USTAR_FORMAT) as archive:
        for name in names:
            path=PurePosixPath(name)
            need(not path.is_absolute() and '..' not in path.parts and str(path)==name,'finite relative archive name')
            member=manifest['members'][name];payload=read(member)
            info=tarfile.TarInfo(name);info.size=len(payload);info.mode=0o600;info.mtime=0;info.uid=info.gid=0;info.uname=info.gname=''
            archive.addfile(info,io.BytesIO(payload))
    tar=buf.getvalue();need(len(tar)<32<<20,'fixed raw source archive bound')
    packed=gzip.compress(tar,mtime=0);need(len(packed)<32<<20,'source archive F32 bound')
    # Every source/data read is revalidated before exclusive publication.
    for name in names:read(manifest['members'][name])
    read(manifest_ref)
    result=publish(output,packed)
    receipt=dict(scope=__doc__,status='ACTUAL_SELECTED_INSTALL_RUNTIME_SOURCE_ARCHIVE_ONLY_NOT_RUNTIME_RELEASE',archive=result,manifest=manifest_ref,members=manifest['members'],member_count=15,uncompressed_bytes=len(tar),source_objects_included=False,compiler_container_query_guest=False)
    record=publish(output.with_suffix(output.suffix+'.receipt.json'),(json.dumps(receipt,sort_keys=True,separators=(',',':'))+'\n').encode())
    print(json.dumps(dict(status=receipt['status'],archive=result,receipt=record),sort_keys=True))
if __name__=='__main__':main()
