#!/usr/bin/env python3
"""Finite root read-only quarantine FD diagnostic. No lock acquisition or effects.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import base64,errno,hashlib,json,os,stat,time
from pathlib import Path
S=Path('/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1')
RELEASE=S/'cleanup-execution-release.json'
RELEASE_SHA='e95ee126d683bcb548b48fc70e6995d32d117e7e225b3142e4a22015014e034a'
ROOT_LOCK=Path('/run/lock/mckernel-development.lock')
CAP=1<<20
TOTAL_RAW=8<<20
remaining=TOTAL_RAW

def ident(s):
 return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,nlink=s.st_nlink,uid=s.st_uid,gid=s.st_gid,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def error(e):
 return dict(type=type(e).__name__,errno=getattr(e,'errno',None),errno_name=errno.errorcode.get(getattr(e,'errno',None)),message=str(e)[:1024])
def bounded(fd,cap):
 chunks=[];left=cap+1
 while left:
  b=os.read(fd,min(left,65536))
  if not b:break
  chunks.append(b);left-=len(b)
 raw=b''.join(chunks)
 if len(raw)>cap:raise ValueError('bounded read limit exceeded')
 return raw

def snapshot(path,hash_only=False,json_expected=False):
 global remaining
 path=Path(path);row=dict(path=str(path),nonfinal_snapshot=True);fd=None
 try:
  before=os.lstat(path);row['named_before']=ident(before)
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  fs=os.fstat(fd);row['fd_before']=ident(fs)
  if not(stat.S_ISREG(fs.st_mode) or stat.S_ISDIR(fs.st_mode)):raise ValueError('only regular file or directory allowed')
  if ident(before)!=ident(fs):raise ValueError('named/FD initial full9 identity differs')
  if stat.S_ISDIR(fs.st_mode):
   names=[]
   with os.scandir(fd) as entries:
    for entry in entries:
     if len(names)>=32:raise ValueError('directory entry bound exceeded')
     names.append(entry.name)
   row.update(kind='directory',entries=sorted(names),empty_sentinel=(len(names)==0))
  elif hash_only:
   h=hashlib.sha256();count=0
   while True:
    block=os.read(fd,65536)
    if not block:break
    count+=len(block)
    if count>128*(1<<20):raise ValueError('capture streaming bound exceeded')
    h.update(block)
   row.update(kind='regular_hash_only',bytes=count,sha256=h.hexdigest(),raw_exported=False)
  else:
   raw=bounded(fd,min(CAP,remaining));remaining-=len(raw)
   row.update(kind='regular',bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),raw_base64=base64.b64encode(raw).decode(),raw_complete=True)
   if json_expected:
    try:
     value=json.loads(raw);row['json_parse']=dict(status='PASS',type=type(value).__name__)
     if len(raw)<=65536:row['parsed_json']=value
    except (ValueError,UnicodeError) as exc:row['json_parse']=dict(status='PARSE_ERROR',error=error(exc))
  row['fd_after']=ident(os.fstat(fd));row['named_after']=ident(os.lstat(path))
  row['stable_full9']=(row['named_before']==row['fd_before']==row['fd_after']==row['named_after'])
 except BaseException as exc:
  row['error']=error(exc)
  if fd is not None:
   try:row['fd_after']=ident(os.fstat(fd))
   except OSError as end:row['fd_after_error']=error(end)
   try:row['named_after']=ident(os.lstat(path))
   except OSError as end:row['named_after_error']=error(end)
 finally:
  if fd is not None:os.close(fd)
 return row

def proc_bytes(path,cap=CAP):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:return bounded(fd,cap)
 finally:os.close(fd)

def selected_holder(mutex):
 report=dict(lock_device=27,lock_inode=4,holders=[],process_scope='Only actual /proc/locks 27:4 holder; no process census')
 try:
  raw=proc_bytes('/proc/locks');lines=[]
  for line in raw.decode('ascii').splitlines():
   parts=line.split()
   if '->' in parts:continue
   if len(parts)<6:continue
   dev=parts[5].split(':')
   if len(dev)==3 and int(dev[0],16)==os.major(27) and int(dev[1],16)==os.minor(27) and int(dev[2])==4:
    pid=int(parts[4]);lines.append(dict(line=line,pid=pid))
  report['selected_lock_lines']=lines
  if len(lines)>1:raise ValueError('unexpected multiple holder records')
  for item in lines:
   pid=item['pid'];p=Path('/proc')/str(pid);holder=dict(pid=pid,relevant_fds=[])
   try:
    first=proc_bytes(p/'stat',65536);start=first.rsplit(b') ',1)[1].split()[19].decode();holder['starttime']=start
    holder['stat_before']=first.decode('utf-8','backslashreplace')
    for name in ['cmdline','status']:
     b=proc_bytes(p/name,65536);holder[name]=dict(raw_base64=base64.b64encode(b).decode(),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
    holder['exe']=os.readlink(p/'exe')
    names=[]
    with os.scandir(p/'fd') as entries:
     for entry in entries:
      if len(names)>=512:raise ValueError('holder FD bound exceeded')
      names.append(entry.name)
    for name in names:
     try:
      link=os.readlink(p/'fd'/name)
      if link not in (str(ROOT_LOCK),str(ROOT_LOCK)+' (deleted)',str(mutex),str(mutex)+' (deleted)'):continue
      b=proc_bytes(p/'fdinfo'/name,65536)
      holder['relevant_fds'].append(dict(fd=name,target=link,target_identity=ident(os.stat(p/'fd'/name)),fdinfo_raw_base64=base64.b64encode(b).decode(),fdinfo_bytes=len(b),fdinfo_sha256=hashlib.sha256(b).hexdigest()))
     except OSError as exc:holder.setdefault('fd_races',[]).append(dict(fd=name,error=error(exc)))
    last=proc_bytes(p/'stat',65536);holder['stat_after']=last.decode('utf-8','backslashreplace');holder['same_birth']=last.rsplit(b') ',1)[1].split()[19].decode()==start
   except BaseException as exc:holder['error']=error(exc)
   report['holders'].append(holder)
 except BaseException as exc:report['error']=error(exc)
 return report

def main():
 if os.getuid()!=0 or os.geteuid()!=0:raise RuntimeError('reviewed root read-only invocation required')
 begin=time.time_ns();release=snapshot(RELEASE,json_expected=True)
 if release.get('sha256')!=RELEASE_SHA or not release.get('stable_full9'):raise RuntimeError('same final release exact bytes/FD identity required')
 value=json.loads(base64.b64decode(release['raw_base64']));paths=value['transaction_paths']
 if len(paths)!=7 or len(set(paths))!=7:raise RuntimeError('exact seven released transaction paths required')
 records=[x['path'] for x in value['observation']['retained_exclusions']]
 if len(records)!=2 or len(set(records))!=2:raise RuntimeError('exact common/shared released ownership paths required')
 rows=[snapshot(p,hash_only=(i==3),json_expected=(i in (0,1,2,4))) for i,p in enumerate(paths)]
 owners=[snapshot(p,json_expected=True) for p in records]
 active=[snapshot(S/'actual-cleanup-capture-1'/n,json_expected=(n=='child-start.json')) for n in ['child-start.json','stdout','stderr']]
 holder=selected_holder(paths[0])
 engine=snapshot(S/'cleanup_pass_image.py')
 target_matches=(len(holder.get('holders',[]))==1 and holder['holders'][0].get('pid')==2761636 and holder['holders'][0].get('starttime')=='40670236' and holder['holders'][0].get('same_birth') is True)
 print(json.dumps(dict(schema='mckernel.cleanup-quarantine-readonly-diagnostic.v1',status='READ_ONLY_DIAGNOSTIC_NOT_RETIREMENT',started_ns=begin,finished_ns=time.time_ns(),release=release,transaction_paths=rows,original_ownership_paths=owners,actual_lock_holder=holder,active_capture_nonfinal=active,cleanup_source=engine,expected_holder_matches=target_matches,expected_holder=dict(pid=2761636,starttime='40670236'),lock_acquired=False,mutation=False,signals_sent=False,engine_imported=False,cleanup_authority=False),sort_keys=True))
if __name__=='__main__':main()
