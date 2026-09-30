#!/usr/bin/env python3
"""Separately reviewed, archive-bound retirement for stopped f021 evidence."""
import argparse, hashlib, json, os, stat, subprocess, tarfile, tempfile, io
from pathlib import Path

REPO=Path('/home/holden/mckernel'); SCRATCH=Path('/home/holden/mckernel-work/scratch')
SOURCE=SCRATCH/'native-exact-build-evidence-f021bdee-scratch-8'; SOURCE_ID='1831:6684763'
ARCHIVE=Path('/home/holden/mckernel-work/retained-exact-candidates/native-exact-build-evidence-f021bdee-scratch-8-20260930.tar.gz'); ARCHIVE_ID='66306:47496368'; ARCHIVE_SIZE=68378647; ARCHIVE_SHA='ac7d20264bc870e5ec0529a6c7b820840a008d4e9667950cdb8f44ca9c1313d0'
MAP=Path('/home/holden/mckernel-work/retained-exact-candidates/native-exact-build-evidence-f021bdee-scratch-8-20260930.map.json'); MAP_ID='66306:47496380'; MAP_SIZE=109775078; MAP_SHA='23e418e1b3cc135d59b2abb171040c36b8f081dbf673bb6f6564cf4a8bdfc2f9'
RESULT=MAP.parent/'native-exact-build-evidence-f021bdee-scratch-8-retirement-20260930.result.json'
FAILURE=REPO/'docs/verification/evidence/native-exact-build-f021bdee-scratch8-export-allowlist-failure-20260930.json'; FAILURE_SHA='2c40c821d23b0e79bba0eb2e151b47f8c99f5ffc60e36c1e93c97b692f1a59c6'
PROTECTED=[SCRATCH/'native-exact-build-output-f021bdee-scratch-8',SCRATCH/'mckernel-exact-candidate-f021bdee-scratch-8',SCRATCH/'native-exact-build-request-f021bdee-scratch-8.json',SCRATCH/'native-exact-inputs-f021bdee-scratch-8.json',SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8-terminal.json',SCRATCH/'native-exact-candidate-preparation-f021bdee-scratch-8.log',SCRATCH/'native-exact-metadata-backup-f021bdee-scratch-8',SCRATCH/'native-exact-metadata-evidence-f021bdee-scratch-8',SCRATCH/'native-exact-candidate-operational-exclusion-selfdigest-13.json']
CONTAINER={'id':'b34323f6c4352e8bae669d006e11076a64a5734ed165a6ce866bd4e7aa04c001','name':'mckernel-exact-d01624939ead44118fc2352bc4d83860','state':'exited','exit_code':1}
def die(x): raise SystemExit('FAIL_CLOSED: '+x)
def validate_container_json(d):
 try: state=d['State']
 except Exception: die('protected container missing state')
 if str(d.get('Name','')).lstrip('/')!=CONTAINER['name'] or state.get('Running') or state.get('OOMKilled') or state.get('Pid') or state.get('ExitCode')!=CONTAINER['exit_code'] or state.get('Status')!=CONTAINER['state']: die('protected container identity/state')
def digest(p):
 h=hashlib.sha256(); fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); f=os.fdopen(fd,'rb')
 with f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()
def bound_bytes(p,ident,size,sha):
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW); st=os.fstat(fd)
 if (f'{st.st_dev}:{st.st_ino}',st.st_size)!=(ident,size): os.close(fd); die('bound identity')
 data=b''
 while True:
  b=os.read(fd,1<<20)
  if not b: break
  data+=b
 st2=os.fstat(fd); os.close(fd)
 if (st2.st_dev,st2.st_ino,st2.st_size)!=(st.st_dev,st.st_ino,st.st_size) or hashlib.sha256(data).hexdigest()!=sha: die('bound replacement/hash')
 return data
def bound(p,ident,size,sha):
 st=os.lstat(p)
 if (f'{st.st_dev}:{st.st_ino}',st.st_size,digest(p))!=(ident,size,sha): die('bound artifact changed: '+str(p))
def guard():
 if not SOURCE.is_dir() or SOURCE.is_symlink(): die('source missing/linked')
 st=SOURCE.stat()
 if f'{st.st_dev}:{st.st_ino}'!=SOURCE_ID: die('source identity changed')
 bound_bytes(ARCHIVE,ARCHIVE_ID,ARCHIVE_SIZE,ARCHIVE_SHA); bound_bytes(MAP,MAP_ID,MAP_SIZE,MAP_SHA)
 if digest(FAILURE)!=FAILURE_SHA: die('failure changed')
 for p in PROTECTED:
  if os.path.lexists(p) and p.resolve()==SOURCE.resolve(): die('protected alias')
 p=subprocess.run(['sudo','-A','lsof','-nP','-w','+D',str(SOURCE)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,check=False)
 if p.returncode not in (0,1) or p.stderr.strip() or (p.returncode==0 and [x for x in p.stdout.splitlines() if x and not x.startswith('COMMAND')]) or (p.returncode==1 and p.stdout.strip()): die('lsof census')
 p=subprocess.run(['findmnt','-T',str(SOURCE),'-o','SOURCE,FSTYPE,MAJ:MIN,TARGET'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,check=False)
 lines=[x.split() for x in p.stdout.splitlines() if x.strip() and not x.startswith('SOURCE')]
 if p.returncode or lines != [['/dev/loop39','ext4','7:39','/home/holden/mckernel-work/scratch']]: die('mount census')
 p=subprocess.run(['sudo','-A','docker','inspect',CONTAINER['id']],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=15,check=False)
 if p.returncode: die('docker census')
 try: d=json.loads(p.stdout)[0]
 except Exception: die('docker census malformed')
 validate_container_json(d)
 return True
def snapshot():
 rows=[]
 for d,dirs,files in os.walk(SOURCE,topdown=True,followlinks=False):
  dirs.sort(); files.sort(); ds=os.lstat(d); rel='.' if Path(d)==SOURCE else str(Path(d).relative_to(SOURCE));
  if not stat.S_ISDIR(ds.st_mode) or ds.st_nlink<2: die('bad directory')
  rows.append({'path':rel,'type':'dir','mode':stat.S_IMODE(ds.st_mode),'uid':ds.st_uid,'gid':ds.st_gid,'mtime_ns':ds.st_mtime_ns,'size':0})
  for n in list(dirs):
   p=Path(d)/n
   if p.is_symlink():
    st=os.lstat(p); rows.append({'path':str(p.relative_to(SOURCE)),'type':'symlink','mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':0,'linkname':os.readlink(p)}); dirs.remove(n)
  for n in list(files):
   p=Path(d)/n; st=os.lstat(p); rel=str(p.relative_to(SOURCE))
   if stat.S_ISLNK(st.st_mode): rows.append({'path':rel,'type':'symlink','mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':0,'linkname':os.readlink(p)}); continue
   if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1: die('special/hardlink member')
   rows.append({'path':rel,'type':'file','mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':st.st_size,'sha256':digest(p)})
 return rows
def verify():
 guard(); record=json.loads(bound_bytes(MAP,MAP_ID,MAP_SIZE,MAP_SHA)); rows=record.get('members',[])
 if record.get('status')!='ARCHIVE_PASS' or len(rows)!=286318: die('map release/member count')
 if sum(x.get('type')=='file' for x in rows)!=285811 or sum(x.get('type')=='dir' for x in rows)!=452 or sum(x.get('type')=='symlink' for x in rows)!=55: die('map type counts')
 fresh=snapshot()
 if fresh!=rows: die('source differs from archived map')
 expected={x['path']:x for x in rows}
 try:
  with tarfile.open(fileobj=io.BytesIO(bound_bytes(ARCHIVE,ARCHIVE_ID,ARCHIVE_SIZE,ARCHIVE_SHA)),mode='r:gz') as tf:
   ms=tf.getmembers()
   if [x.name for x in ms]!=list(expected): die('archive closure')
   for m in ms:
    r=expected[m.name]
    if r['type']=='dir' and not m.isdir(): die('dir type')
    if r['type']=='symlink' and (not m.issym() or m.linkname!=r['linkname']): die('symlink type/link')
    if (m.mode&0o7777,m.uid,m.gid,int(m.mtime))!=(r['mode'],r['uid'],r['gid'],int(r['mtime_ns']/1e9)): die('tar metadata')
    if r['type']=='file' and (not m.isfile() or m.size!=r['size'] or hashlib.sha256(tf.extractfile(m).read()).hexdigest()!=r['sha256']): die('file hash')
 except (OSError,tarfile.TarError) as e: die('archive unreadable: '+str(e))
 return record
def live_identity():
 rows={}
 for d,dirs,files in os.walk(SOURCE,topdown=True,followlinks=False):
  for p in [Path(d)]+[Path(d)/n for n in dirs+files]:
   st=os.lstat(p); rel='.' if p==SOURCE else str(p.relative_to(SOURCE)); row={'dev':st.st_dev,'ino':st.st_ino,'mode':stat.S_IMODE(st.st_mode),'uid':st.st_uid,'gid':st.st_gid,'mtime_ns':st.st_mtime_ns,'size':st.st_size,'nlink':st.st_nlink,'type':'dir' if stat.S_ISDIR(st.st_mode) else 'symlink' if stat.S_ISLNK(st.st_mode) else 'file'}
   if row['type']=='symlink': row['linkname']=os.readlink(p)
   if row['type']=='file': row['sha256']=digest(p)
   rows[rel]=row
 return rows
def write_temp_result(result):
 data=(json.dumps(result,sort_keys=True)+'\n').encode(); fd,tmp=tempfile.mkstemp(prefix='.f021-retire-',dir=RESULT.parent); ident=os.fstat(fd); view=memoryview(data)
 while view:
  n=os.write(fd,view)
  if n<=0: die('short result write')
  view=view[n:]
 os.fsync(fd); os.close(fd); st=os.lstat(tmp)
 if (st.st_dev,st.st_ino)!=(ident.st_dev,ident.st_ino) or not stat.S_ISREG(st.st_mode) or st.st_nlink!=1: die('result temp identity')
 return Path(tmp),ident
def complete_write(fd,data):
 view=memoryview(data)
 while view:
  n=os.write(fd,view)
  if n<=0: die('short result write')
  view=view[n:]
def fixed_payloads(prepared,passed):
 a=(json.dumps(prepared,sort_keys=True)+'\n').encode(); b=(json.dumps(passed,sort_keys=True)+'\n').encode(); size=max(len(a),len(b)); return a.ljust(size,b' '),b.ljust(size,b' ')
def retire():
 record=verify()
 pre=live_identity(); rootst=os.lstat(SOURCE)
 if f'{rootst.st_dev}:{rootst.st_ino}'!=SOURCE_ID or live_identity()!=pre: die('entry changed before delete')
 if os.path.lexists(RESULT): die('result collision before delete')
 prepared,passed=fixed_payloads({'schema':'mckernel.f021-evidence-retirement.v1','status':'RETIRE_PREPARED','archive_sha256':ARCHIVE_SHA,'map_sha256':MAP_SHA,'source_identity':SOURCE_ID},{'schema':'mckernel.f021-evidence-retirement.v1','status':'RETIRE_PASS','archive_sha256':ARCHIVE_SHA,'map_sha256':MAP_SHA,'source_identity':SOURCE_ID,'members':len(record['members'])})
 fd=os.open(RESULT,os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_RDWR,0o600); result_ident=os.fstat(fd); complete_write(fd,prepared); os.fsync(fd); d=os.open(RESULT.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
 expected=pre
 parent=os.open(SOURCE.parent,os.O_DIRECTORY|os.O_NOFOLLOW); name=SOURCE.name; root=os.open(name,os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent); rr=expected.get('.') or pre['.']; rs=os.fstat(root)
 if (rs.st_dev,rs.st_ino,rs.st_uid,rs.st_gid,stat.S_IMODE(rs.st_mode))!=(rr['dev'],rr['ino'],rr['uid'],rr['gid'],rr['mode']): die('root fd replacement')
 def check(fd,n,rel,post=False):
  r=expected.get(rel); st=os.lstat(n,dir_fd=fd)
  if r is None or (st.st_dev,st.st_ino,st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode))!=(r['dev'],r['ino'],r['uid'],r['gid'],r['mode']): die('entry replacement: '+rel)
  if not post and (st.st_mtime_ns,st.st_size,st.st_nlink)!=(r['mtime_ns'],r['size'],r['nlink']): die('entry metadata replacement: '+rel)
  if r['type']=='dir' and not stat.S_ISDIR(st.st_mode): die('entry type: '+rel)
  if r['type']=='symlink' and (not stat.S_ISLNK(st.st_mode) or os.readlink(os.path.join('/proc/self/fd',str(fd),n))!=r['linkname']): die('symlink replacement: '+rel)
  if r['type']=='file':
   if not stat.S_ISREG(st.st_mode) or st.st_nlink!=1 or st.st_size!=r['size']: die('file replacement: '+rel)
   q=os.open(n,os.O_RDONLY|os.O_NOFOLLOW,dir_fd=fd); h=hashlib.sha256()
   while True:
    b=os.read(q,1<<20)
    if not b: break
    h.update(b)
   os.close(q)
   if h.hexdigest()!=r['sha256']: die('file content replacement: '+rel)
 def rm(fd,prefix=''):
  for n in os.listdir(fd):
   rel=f'{prefix}/{n}' if prefix else n; check(fd,n,rel)
   st=os.lstat(n,dir_fd=fd)
   if stat.S_ISDIR(st.st_mode) and not stat.S_ISLNK(st.st_mode): child=os.open(n,os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd); rm(child,rel); check(fd,n,rel,True); os.close(child); os.rmdir(n,dir_fd=fd)
   else: os.unlink(n,dir_fd=fd)
   os.fsync(fd)
 rm(root); rs2=os.fstat(root)
 if (rs2.st_dev,rs2.st_ino)!=(rs.st_dev,rs.st_ino) or os.listdir(root): die('root changed/not empty')
 os.close(root); os.rmdir(name,dir_fd=parent); os.fsync(parent); os.close(parent)
 if SOURCE.exists(): die('root remains after deletion')
 cur=os.lstat(RESULT)
 if (cur.st_dev,cur.st_ino)!=(result_ident.st_dev,result_ident.st_ino): die('result reservation replaced')
 os.lseek(fd,0,os.SEEK_SET); complete_write(fd,passed); os.ftruncate(fd,len(passed)); os.fsync(fd); os.lseek(fd,0,os.SEEK_SET)
 if json.loads(os.read(fd,len(passed)).rstrip())['status']!='RETIRE_PASS': die('final result verification')
 os.close(fd); d=os.open(RESULT.parent,os.O_DIRECTORY); os.fsync(d); os.close(d)
 return {'schema':'mckernel.f021-evidence-retirement.v1','status':'RETIRE_PASS','archive_sha256':ARCHIVE_SHA,'map_sha256':MAP_SHA,'source_identity':SOURCE_ID,'members':len(record['members'])}
def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--audit',action='store_true'); ap.add_argument('--retire',action='store_true'); a=ap.parse_args()
 if (a.audit+a.retire)!=1: ap.error('choose one mode')
 print(json.dumps({'status':'AUDIT_PASS','verified':len(verify()['members'])},sort_keys=True) if a.audit else json.dumps(retire(),sort_keys=True))
if __name__=='__main__': main()
