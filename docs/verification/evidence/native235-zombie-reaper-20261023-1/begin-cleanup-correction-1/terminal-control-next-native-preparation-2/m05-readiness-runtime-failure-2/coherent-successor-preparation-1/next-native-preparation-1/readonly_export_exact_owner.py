from pathlib import Path
import base64,hashlib,json,os,stat
ROOT=Path('/home/holden/mckernel-work/native-runs/m05h2/p.owner-efb4312b2dc644519320ccc24fa1219c')
s=ROOT.lstat();assert stat.S_ISDIR(s.st_mode) and not ROOT.is_symlink() and s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o700
names=sorted(os.listdir(ROOT));assert len(names)<=4096
rows=[];total=0
for name in names:
 assert name not in('.','..') and '/' not in name
 fd=os.open(str(ROOT/name),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 with os.fdopen(fd,'rb') as f:
  before=os.fstat(f.fileno());assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=8*2**20
  total+=before.st_size;assert total<=8*2**20
  raw=f.read(before.st_size+1);after=os.fstat(f.fileno());named=(ROOT/name).lstat()
  keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
  assert len(raw)==before.st_size and all(getattr(before,k)==getattr(after,k)==getattr(named,k)for k in keys)
 rows.append(dict(name=name,source_path=str(ROOT/name),identity={k:getattr(after,k)for k in keys},sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode()))
assert sorted(os.listdir(ROOT))==names
encoded=json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='READONLY_EXACT_CLOSED_OWNER_EVIDENCE_EXPORT',root=str(ROOT),root_identity=dict(dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode)),files=rows,total_source_bytes=total,root_mutations=0),sort_keys=True,separators=(',',':'))
assert len(encoded.encode())+1<=16*2**20
print(encoded)
