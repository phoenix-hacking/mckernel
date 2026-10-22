"""Fixed current failed-owner file reads only; no Docker, census or mutation."""
import os,stat,json,base64
from pathlib import Path
P=Path('/home/holden/mckernel-work/scratch/m07p-261021-2/t.owner-05807dbcbbdf46989fee0f5f57b632a2')
assert os.geteuid()==0 and os.sched_getaffinity(0)=={0}
assert P.resolve(strict=True)==P and stat.S_ISDIR(P.lstat().st_mode)
entries=sorted(os.listdir(P));assert len(entries)<=256
selected=['owner.json','result.json','state.json']+[n for n in entries if len(n.split('-',1)[0])==3 and n[:3].isdigit() and n[3:] in ('-start.json','-start.stdout','-start.stderr')]
keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
rows=[];total=0
for name in selected:
 p=P/name
 try:
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 except FileNotFoundError:
  rows.append(dict(path=str(p),absent=True));continue
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_size<=65536
  raw=os.read(fd,65537);after=os.fstat(fd);named=os.lstat(p)
  assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys)
  assert len(raw)==before.st_size;total+=len(raw);assert total<=262144
  rows.append(dict(path=str(p),identity={k:getattr(before,k) for k in keys},raw_base64=base64.b64encode(raw).decode()))
 finally:os.close(fd)
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',operation='FIXED_FAILED_M07_OWNER_MINIMUM_READ_ONLY',evidence_root=str(P),selected_files=selected,total_bytes=total,rows=rows),sort_keys=True))
