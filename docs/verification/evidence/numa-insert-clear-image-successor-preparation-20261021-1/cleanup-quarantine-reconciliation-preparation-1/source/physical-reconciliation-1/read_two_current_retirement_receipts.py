#!/usr/bin/env python3
"""Read exactly two known root retirement receipts; no effects or census.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import base64,hashlib,json,os,stat
from pathlib import Path
BASE=Path('/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-quarantine-reconciliation-preparation-1/records/actual-root-retirement-1')
COMPLETE_SHA='2dc61852874e32c0c3bd706e2175e150abcbb35a4cbdb63a70ce3a8cd7be9067'
CAP=1<<20

def full9(s):return dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,nlink=s.st_nlink,uid=s.st_uid,gid=s.st_gid,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def need(ok,why):
 if not ok:raise RuntimeError(why)
def directory(path):
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:
  for part in path.parts[1:]:
   child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
  return fd
 except BaseException:os.close(fd);raise

def snapshot(parent,name,expected):
 fd=None;row=dict(path=str(BASE/name))
 try:
  before=full9(os.stat(name,dir_fd=parent,follow_symlinks=False));fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);first=full9(os.fstat(fd))
  row.update(named_before=before,fd_before=first)
  need(stat.S_ISREG(first['mode']) and first['uid']==first['gid']==0 and first['nlink']==1 and stat.S_IMODE(first['mode'])==0o600 and before==first,'exact root regular/full9 shape')
  parts=[];count=0
  while True:
   block=os.read(fd,min(65536,CAP+1-count))
   if not block:break
   count+=len(block);need(count<=CAP,'receipt exceeds1MiB');parts.append(block)
  raw=b''.join(parts);h=hashlib.sha256(raw).hexdigest();row.update(bytes=len(raw),sha256=h,raw_base64=base64.b64encode(raw).decode(),raw_complete=True)
  row['fd_after']=full9(os.fstat(fd));row['named_after']=full9(os.stat(name,dir_fd=parent,follow_symlinks=False));row['stable_full9']=row['named_before']==row['fd_before']==row['fd_after']==row['named_after']
  need(row['stable_full9'] and h==expected,'receipt exacthash/full9 drift')
  value=json.loads(raw);row['parsed_json']=value;row['status']='PASS_EXACT_ROOT_RECEIPT_READ_ONLY';return row,value
 except BaseException as exc:
  row['status']='REFUSED_READ_ONLY';row['error']=dict(type=type(exc).__name__,errno=getattr(exc,'errno',None),message=str(exc)[:1024]);return row,None
 finally:
  if fd is not None:os.close(fd)

def main():
 need(os.getuid()==os.geteuid()==0,'released root readonly invocation required');fd=directory(BASE)
 try:
  parent=full9(os.fstat(fd));need(parent['uid']==parent['gid']==0 and stat.S_IMODE(parent['mode'])==0o700,'root0700 receipt directory')
  complete,c=snapshot(fd,'complete.json',COMPLETE_SHA);prepared=None;p=None
  if c is not None:
   need(c.get('status')=='COMPLETE_IDLE_HOLDER_RETIREMENT_ONLY' and c.get('target',{}).get('pid')==2761636 and c['target'].get('starttime')=='40670236','current complete scope/birth')
   prepared,p=snapshot(fd,'prepared.json',c['prepared_sha256'])
   if p is not None:need(p.get('status')=='PREPARED_EXACT_PROCESS_RETIREMENT_ONLY' and p.get('target')==c['target'],'prepared/currenttarget scope')
  print(json.dumps(dict(schema='mckernel.exact-two-root-retirement-receipt-export.v1',status='PASS_READ_ONLY_TWO_RECEIPTS' if c is not None and p is not None else 'REFUSED_READ_ONLY',directory=parent,complete=complete,prepared=prepared,root_lock_acquired=False,signals_sent=False,mutation=False,census=False,cleanup_authority=False),sort_keys=True))
 finally:os.close(fd)
if __name__=='__main__':main()
