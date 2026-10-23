from pathlib import Path
import base64,hashlib,json,os,stat
ROOT=Path('/home/holden/mckernel-work/native-runs/l12b1/p.owner-dfbb3adb1c7d45b689a899140f3afffc')
s=ROOT.lstat();assert stat.S_ISDIR(s.st_mode) and not ROOT.is_symlink() and s.st_uid==s.st_gid==0 and stat.S_IMODE(s.st_mode)==0o700
all_names=sorted(os.listdir(ROOT));assert len(all_names)<=4096
names=['001-ps.json', '002-ps.json', '003-image.json', '004-create.json', '004-create.stdout', '005-ps.json', '006-ps.json', '007-ps.json', '008-inspect.json', '009-start.json', '010-wait.json', '011-inspect.json', '012-ps.json', '013-ps.json', '014-ps.json', '015-inspect.json', '015-inspect.stdout', '016-stop.json', '017-kill.json', '017-kill.stderr', '018-wait.json', '018-wait.stdout', '019-inspect.json', '019-inspect.stdout', '020-rm.json', '020-rm.stdout', '021-ps.json', '021-ps.stderr', '021-ps.stdout', '022-ps.json', '022-ps.stderr', '022-ps.stdout', '023-ps.json', '023-ps.stderr', '023-ps.stdout', 'owner.json', 'result.json']
assert set(names)<=set(all_names)
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
assert sorted(os.listdir(ROOT))==all_names
encoded=json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='READONLY_EXACT_CLOSED_OWNER_EVIDENCE_EXPORT',root=str(ROOT),root_identity=dict(dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode)),files=rows,total_source_bytes=total,root_mutations=0),sort_keys=True,separators=(',',':'))
assert len(encoded.encode())+1<=16*2**20
print(encoded)
