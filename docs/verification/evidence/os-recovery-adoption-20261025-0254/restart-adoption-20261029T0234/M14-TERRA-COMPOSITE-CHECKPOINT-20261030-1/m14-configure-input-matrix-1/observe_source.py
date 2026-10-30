#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,os,pathlib,stat
p=pathlib.Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output/source/linux-6.12.0-211.44.1.el10_2/Makefile'); expected='96d61309de7b5a043f53f8203c05ea30c27808fc7db06b3503d98105f4fde6f6'
def i(s):return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
a=os.stat(p,follow_symlinks=False);assert stat.S_ISREG(a.st_mode);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
try:
 b=os.fstat(fd);assert i(a)==i(b);data=b''
 while True:
  chunk=os.read(fd,131072)
  if not chunk:break
  data+=chunk
 c=os.fstat(fd)
finally:os.close(fd)
d=os.stat(p,follow_symlinks=False);assert i(b)==i(c)==i(d);digest=hashlib.sha256(data).hexdigest();assert digest==expected
out={'scope':'single point-in-time file read; no full source membership or quiescence','path':str(p),'bytes':len(data),'sha256':digest,'identity':i(d),'historical_inventory_expected_sha256':expected}
pathlib.Path('LINUX-SOURCE-MAKEFILE.OBSERVED.json').write_text(json.dumps(out,indent=2)+'\n');print('PASS historical source Makefile SHA matches; bytes',len(data))
