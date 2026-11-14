"""Fixed current failed-owner file reads only; no Docker, census or mutation."""
import os,stat,json,base64
from pathlib import Path
P=Path('/home/holden/mckernel-work/scratch/m07p-261021-4/t.owner-e2262e4b52334b71a1eb0a274215abfc')
A=Path('/home/holden/mckernel-work/scratch/m07p-261021-4/t/attempt-e2262e4b52334b71a1eb0a274215abfc')
assert os.geteuid()==0 and os.sched_getaffinity(0)=={0}
assert P.resolve(strict=True)==P and stat.S_ISDIR(P.lstat().st_mode)
assert A.resolve(strict=True)==A and stat.S_ISDIR(A.lstat().st_mode)
entries=sorted(os.listdir(P));assert len(entries)<=256
start_files=[n for n in entries if len(n.split('-',1)[0])==3 and n[:3].isdigit() and n[3:] in ('-start.json','-start.stdout','-start.stderr')]
assert len(start_files)<=3
owner_files=['owner.json','result.json','state.json']+start_files
cause_files=['result.json','first-failure.jsonl','serial.log','debugcon.log','qemu.stderr']
selected=[str(P/name) for name in owner_files]+[str(A/name) for name in cause_files]
keys=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
rows=[];total=0
for name in selected:
 p=Path(name)
 try:
  fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 except FileNotFoundError:
  rows.append(dict(path=str(p),absent=True));continue
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_size<=131072
  raw=os.read(fd,131073);after=os.fstat(fd);named=os.lstat(p)
  assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys)
  assert len(raw)==before.st_size;total+=len(raw);assert total<=262144
  rows.append(dict(path=str(p),identity={k:getattr(before,k) for k in keys},raw_base64=base64.b64encode(raw).decode()))
 finally:os.close(fd)
print(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',operation='FIXED_FAILED_M07_OWNER_AND_FIVE_CAUSE_FILES_READ_ONLY',evidence_roots=[str(P),str(A)],selected_files=selected,total_bytes=total,rows=rows),sort_keys=True))
