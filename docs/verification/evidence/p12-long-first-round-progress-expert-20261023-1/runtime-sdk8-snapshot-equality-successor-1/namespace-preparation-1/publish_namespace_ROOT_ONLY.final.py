"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-only fresh namespace and exact manifest publication. No runtime/release/cleanup.
Any failure preserves every created byte/path; no rollback or overwrite is attempted.
"""
from pathlib import Path
import fcntl,hashlib,json,os,stat,struct,sys,uuid
N=Path(__file__).resolve().parent;D=N.parent;F=N/'NAMESPACE-PUBLICATION.INPUTS.json'
assert os.getuid()==os.geteuid()==0 and sys.version.startswith('3.9.12 ')
def data(p):
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  a=os.fstat(fd);assert stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=1<<20
  raw=b''
  while True:
   b=os.read(fd,65536)
   if not b:break
   raw+=b;assert len(raw)<=1<<20
  z=os.fstat(fd);q=p.lstat();assert (a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns)==(q.st_dev,q.st_ino,q.st_size,q.st_mtime_ns,q.st_ctime_ns)
  return raw
 finally:os.close(fd)
def pin(p):
 raw=data(p);return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def fsyncdir(p):
 fd=os.open(p,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)
def exclusive(p,raw):
 fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fchown(f.fileno(),1000,1000);os.fsync(f.fileno())
 fsyncdir(p.parent)
def emit(p,v):exclusive(p,(json.dumps(v,sort_keys=True,indent=2)+'\n').encode())
def meta(p):
 s=p.lstat();return dict(path=str(p),device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink)
def mkdir(p,device):
 os.mkdir(p,0o700);os.chown(p,1000,1000);s=p.lstat();assert stat.S_ISDIR(s.st_mode) and s.st_dev==device and stat.S_IMODE(s.st_mode)==0o700 and s.st_uid==s.st_gid==1000;fsyncdir(p);fsyncdir(p.parent)
def mountline():
 lines=[]
 for line in Path('/proc/self/mountinfo').read_text().splitlines():
  f=line.split();i=f.index('-')
  if f[4]=='/home/holden/mckernel-work/scratch':lines.append((line,f,i))
 assert len(lines)==1;line,f,i=lines[0];assert f[i+1]=='ext4' and 'rw' in f[5].split(',') and f[i+2].startswith('/dev/loop')
 return line,f,i
input_bytes=data(F);assert hashlib.sha256(input_bytes).hexdigest()=='fe0e0ab2e44ed3cc7c5d1ce522cb184b326221c2c8a6a45eac752ca5d5ff1f2d'
plan=json.loads(input_bytes);assert plan['nonce']=='63bdc7731c34491eb430ddb34b094d5b'
for k in ['source_manifest','capsule_handoff','predecessor_namespace','predecessor_actual_publication']:assert pin(Path(plan[k]['path']))==plan[k]
manifest=data(Path(plan['source_manifest']['path']));assert len(manifest)==13073 and hashlib.sha256(manifest).hexdigest()=='9dfead8648d68c90e798973b384a1c41bc5493fe5390e237b4868ecfa4b33abe'
H=Path(plan['HOST_retention_base']);P=Path(plan['HOST_parent']);S=Path(plan['scratch_parent']);M=Path(plan['manifest_path']);R=Path(plan['release_path']);A=N/'ACTUAL-ROOT-NAMESPACE-PUBLICATION.json';W=D/'ROOT-SUCCESSOR-NAMESPACE.json'
assert P==H/'p' and M==S/'m.json' and R==S/'r.json'
for p in [H,P,S,M,R,A,W]:assert not os.path.lexists(p),'refuse occupied reserved/output path: '+str(p)
root=Path('/home/holden/mckernel-work');scratch=root/'scratch';back=Path(plan['expected_backing']);line,f,i=mountline();ss=scratch.lstat();bs=back.lstat();host=root.lstat();loop=Path(f[i+2]);ls=loop.stat()
assert stat.S_ISDIR(ss.st_mode) and stat.S_ISDIR(host.st_mode) and stat.S_ISREG(bs.st_mode) and bs.st_nlink==1 and bs.st_size==plan['expected_backing_bytes']
assert stat.S_ISBLK(ls.st_mode) and ls.st_rdev==ss.st_dev and f[2]==str(os.major(ss.st_dev))+':'+str(os.minor(ss.st_dev)) and host.st_dev!=ss.st_dev
lfd=os.open(loop,os.O_RDONLY|os.O_NOFOLLOW)
try:
 info=bytearray(232);fcntl.ioctl(lfd,0x4c05,info,True);dev,ino,rdev,offset,sizelimit,number,encrypt,keysize,flags=struct.unpack_from('=QQQQQIIII',info)
 assert dev==bs.st_dev and ino==bs.st_ino and offset==sizelimit==encrypt==keysize==0 and not flags&1
 sb=os.pread(lfd,1024,1024);assert len(sb)==1024 and sb[56:58]==b'\x53\xef';actual_uuid=str(uuid.UUID(bytes=sb[104:120]));assert actual_uuid==plan['expected_scratch_uuid']
 gap=max(0,bs.st_size-bs.st_blocks*512);hv=os.statvfs(root);sv=os.statvfs(scratch)
 capacity=dict(HOST_available=hv.f_bavail*hv.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=sv.f_bavail*sv.f_frsize,scratch_required=(12<<30)+679477248,full_backing_gap=gap)
 assert capacity['HOST_available']>=capacity['HOST_required'] and capacity['scratch_available']>=capacity['scratch_required']
 fresh=dict(mountinfo=line,mount_device=ss.st_dev,loop_path=str(loop),loop_block_rdev=ls.st_rdev,backing=meta(back),backing_bytes=bs.st_size,loop_backing_device=dev,loop_backing_inode=ino,offset=offset,sizelimit=sizelimit,flags=flags,uuid=actual_uuid,capacity=capacity)
 mkdir(H,host.st_dev);mkdir(P,host.st_dev);mkdir(S,ss.st_dev);exclusive(M,manifest)
 assert pin(M)==dict(path=str(M),sha256=plan['source_manifest']['sha256'],bytes=13073) and not os.path.lexists(R)
 assert scratch.lstat().st_dev==ss.st_dev and mountline()[0]==line and (back.lstat().st_dev,back.lstat().st_ino,back.lstat().st_size)==(bs.st_dev,bs.st_ino,bs.st_size)
 record=dict(scope=plan['scope'],status='ROOT_RESERVED_AND_ACTUAL_MANIFEST_PUBLISHED_NO_OWNER_OR_RELEASE',nonce=plan['nonce'],retention_base=meta(H),HOST_parent=meta(P),scratch_parent=meta(S),manifest_path=str(M),manifest=dict(pin(M),**{k:v for k,v in meta(M).items() if k!='path'}),release_path=str(R),release_exists=False,new_runtime_owner_not_created=True,heavy_lease_reserved=False,current_live_postjoin='ROOT_SUPPLIED_PRIOR_POSITIVE_PHYSICAL_AUTHORITY_a492',fresh_scratch_identity=fresh,source_manifest=plan['source_manifest'],actual_capsule_handoff=plan['capsule_handoff'],publication_source=pin(Path(__file__)),publication_inputs=pin(F),permanent_mutex_and_scratch21_mutated=False,runtime=False,release=None)
 emit(A,record)
 emit(W,dict(scope=plan['scope'],status='ACTUAL_ROOT_NAMESPACE_MANIFEST_PUBLISHED_NO_RUNTIME_RELEASE',author='/root',nonce=plan['nonce'],host_parent=str(P),host_identity=dict(device=meta(P)['device'],inode=meta(P)['inode'],uid=1000,gid=1000,mode='0700'),manifest_path=str(M),actual_manifest=record['manifest'],release_path=str(R),release=None,runtime=False,root_actual_namespace_record=pin(A),scratch_identity=fresh,positive_postjoin='ROOT_SUPPLIED_PRIOR_POSITIVE_PHYSICAL_AUTHORITY_a492'))
 print(json.dumps(dict(status=record['status'],namespace=pin(W),actual_record=pin(A),release_absent=not os.path.lexists(R),runtime=False)))
finally:os.close(lfd)
