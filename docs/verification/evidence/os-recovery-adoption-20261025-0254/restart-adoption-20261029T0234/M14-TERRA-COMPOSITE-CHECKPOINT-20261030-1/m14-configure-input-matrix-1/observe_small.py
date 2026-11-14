#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Bounded read-only observations of six specific small files, no tree walk.
import hashlib,json,os,pathlib,stat
build=pathlib.Path('/home/holden/mckernel-work/scratch/mckernel-exact-candidate-scratch-22-authority3-output/build')
nightly=pathlib.Path('/home/holden/mckernel-work/scratch/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu')
checks=[(build/'include/config/kernel.release','42bb1d3c01816ca5d716e59ce1b50f1b96be1e5643d866486b0f6db098d2725a'),(build/'include/generated/utsrelease.h','46ec981be727b5e16bad989d768363964e8d4362fecb7661ee0bacdead15bbf0'),(build/'.config','106055ad26cfc19373b1bc52e1dcc24b3eaa7c48125c451be029898b8f696474'),(build/'Makefile','7344ad310cc73d258ae43ba8b4c61d2f3a31b56f23b4be971c1a0588508e7f80'),(build/'include/generated/autoconf.h','99d4fc58db2ad5a515e8af210b9b5fd2be624039dcffd1fa0f2e9fca320c2ca3'),(nightly/'bin/rustc','70ebcbbaa352a2d0ef5401eea226b0e61320840430b5c15ad016fb3dc8b54e09')]
def identity(s):return {'device':s.st_dev,'inode':s.st_ino,'mode':s.st_mode,'uid':s.st_uid,'gid':s.st_gid,'size':s.st_size,'mtime_ns':s.st_mtime_ns,'ctime_ns':s.st_ctime_ns}
records=[]
for p,expected in checks:
 before=os.stat(p,follow_symlinks=False);assert stat.S_ISREG(before.st_mode)
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  opened=os.fstat(fd);assert identity(before)==identity(opened)
  chunks=[]
  while True:
   b=os.read(fd,1024*1024)
   if not b:break
   chunks.append(b)
  data=b''.join(chunks);after=os.fstat(fd)
 finally:os.close(fd)
 final=os.stat(p,follow_symlinks=False);assert identity(opened)==identity(after)==identity(final)
 digest=hashlib.sha256(data).hexdigest();assert digest==expected,(str(p),digest)
 row={'path':str(p),'bytes':len(data),'sha256':digest,'identity':identity(final),'inventory_expected_sha256':expected}
 if p.name in ('kernel.release','utsrelease.h'):row['ascii']=data.decode('ascii')
 records.append(row)
out={'scope':'point-in-time six-file reads only; no tree walk, lease, quiescence or physical use authority','retained_inventory_reference':'four-callback-affinity-image-preparation-20261019-1/image-request.json historical sha256 902f482227f3510c86a2624fa9f255abb3d0c82996191f4e3ca4c227877765f8 from retained actual-preparation-bindings; not rehashed in this pass','files':records,'total_bytes':sum(x['bytes'] for x in records)}
pathlib.Path('SIX-FILE-OBSERVATIONS.json').write_text(json.dumps(out,indent=2)+'\n')
print('PASS: six individual stable-read SHA matches; bytes',out['total_bytes'])
