"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only final custody/current filesystem proof; --free adds two own nonblocking probes.
"""
from pathlib import Path
import os,json,time,hashlib,subprocess,importlib.util,sys,fcntl
E=Path(__file__).resolve().parent.parent;G=Path(__file__).resolve().parent
s=E/'scratch-growth-sdk7-110-to-142g-source-1/grow_scratch.py'
assert hashlib.sha256(s.read_bytes()).hexdigest()=='8229919524d803c3694aea42e85bb43d705228d7f78a8ce768704b613ce7608f'
spec=importlib.util.spec_from_file_location('readonly_helpers',s);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
contract=json.loads((G/'ROOT-ACTUAL-GROWTH-CONTRACT.json').read_bytes());preserved=m.file_manifest(contract)
oldids=[1281414,1281415,1281416,1281419,1289064,1289070,1289073]
assert all(not Path('/proc/'+str(p)).exists() for p in oldids)
free=sys.argv[1:]==['--free'];assert free or sys.argv[1:]==[]
lock=Path('/run/lock/mckernel-development.lock');meta=lock.lstat();assert (meta.st_dev,meta.st_ino,meta.st_uid,meta.st_gid,meta.st_nlink,meta.st_size,meta.st_mode)==(27,4,0,0,1,0,0o100644)
rows=[x for x in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in x.split()]
holder=None
if free:
 assert not rows and all(not Path('/proc/'+str(p)).exists() for p in [1294125,1294126,1294129])
else:
 p=Path('/proc/1294129');raw=(p/'stat').read_text();f=raw.rsplit(') ',1)[1].split();assert int(f[19])==85433672 and int(f[1])==1294126 and int(f[2])==1294125
 info=(p/'fdinfo/4').read_text();assert (os.stat(p/'fd/4').st_dev,os.stat(p/'fd/4').st_ino)==(27,4)
 assert len(rows)==1 and rows[0].split()[4]=='1281419'
 holder={'pid':1294129,'birth':85433672,'parent':1294126,'pgid':1294125,'fd':4,'raw_stat':raw,'fdinfo':info,'cmdline_hex':(p/'cmdline').read_bytes().hex(),'status':(p/'status').read_text()}
back=os.lstat(m.BACKING);assert dict(path=m.BACKING,**m.ident(back),uuid=m.UUID)==m.expected(m.NEW)
looproot=Path('/sys/block/loop36');loop={k:(looproot/k).read_text().strip() for k in ['size','loop/backing_file','loop/offset','loop/sizelimit','loop/autoclear','ro']};assert int(loop['size'])*512==m.NEW and loop['loop/backing_file']==m.BACKING
assert loop['loop/offset']==loop['loop/sizelimit']==loop['ro']=='0' and loop['loop/autoclear']=='1'
r=subprocess.run(['/usr/sbin/dumpe2fs','-h','/dev/loop36'],capture_output=True,text=True,timeout=30);assert r.returncode==0;fs=m.fs_fields(r.stdout);assert fs=={'uuid':m.UUID,'blocksize':4096,'blocks':37224448,'reserved':288358}
r2=subprocess.run(['/usr/bin/findmnt','-J','-T',m.MOUNT,'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],capture_output=True,text=True,timeout=10);assert r2.returncode==0
expected=json.loads((E/'ROOT-NEW18H-KEEPER-SUCCESSOR-PREPARATION-2/ROOT-ACTUAL-POSTJOIN-CURRENT-PHYSICAL.json').read_bytes())['mount'];assert json.loads(r2.stdout)['filesystems']==[expected]
census=[];exits=[]
for p in Path('/proc').iterdir():
 if not p.name.isdecimal():continue
 try:raw=(p/'stat').read_text();f=raw.rsplit(') ',1)[1].split();census.append({'pid':int(p.name),'pgrp':int(f[2]),'raw_stat':raw})
 except FileNotFoundError:
  assert not p.exists();exits.append(int(p.name))
assert not [x for x in census if x['pgrp'] in [1281414,1289064]]
if free:assert not [x for x in census if x['pgrp']==1294125]
probes=[]
if free:
 for i in range(2):
  fd=os.open(lock,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  try:
   assert (os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(27,4);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);probes.append({'index':i,'acquired':True,'closed':False,'lock_un_called':False})
  finally:os.close(fd)
  probes[-1]['closed']=True
 assert not [x for x in Path('/proc/locks').read_text().splitlines() if '00:1b:4' in x.split()]
capacity={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ['/home/holden/mckernel',m.MOUNT]};assert capacity['/home/holden/mckernel']>=16*2**30 and capacity[m.MOUNT]>=14091616256
print(json.dumps({'scope':__doc__.splitlines()[0],'observed_wall':time.time(),'mode':'free' if free else 'held','holder':holder,'global_lock_rows':rows,'probes':probes,'old_numeric_ids_absent':oldids,'all_process_rows':census,'confirmed_census_exits':exits,'backing':dict(path=m.BACKING,**m.ident(back)),'loop':loop,'geometry':fs,'dumpe2fs':{'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr},'mount':json.loads(r2.stdout),'preservation':preserved,'capacity':capacity,'filesystem_mutations':0},indent=2))
