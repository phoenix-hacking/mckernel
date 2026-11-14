"""One fixed original-five FD metadata observation; no replay/export/cleanup."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,stat
HERE=Path(__file__).resolve().parent
SUMMARY=HERE/'readback_observer.py'
SUMMARY_SHA = 'dcc6f7b00ebf0864ea70e9f91c3a0c33ca017aecd773d7f570a14ba11ed40fb3'
EXPECTED_HASHES = None
NAMES=('observer-result.json','observation.json','cleanup-release-draft.json','new-object-metadata.json','ownership.json')
def need(ok,why):
 if not ok:raise RuntimeError(why)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def load_expected_hashes(path,expected):
 p=Path(path);need(p.is_absolute() and p.resolve()==p,'exact hash-authority path required')
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<1048576,'bounded hash authority required');raw=os.read(fd,1048576);after=os.fstat(fd);named=p.lstat()
  need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in ['st_dev','st_ino','st_mode','st_size','st_mtime_ns','st_ctime_ns']),'hash authority FD changed')
 finally:os.close(fd)
 need(digest(raw)==expected,'exact hash authority digest differs');value=json.loads(raw)
 need(isinstance(value,dict) and set(value)==set(NAMES) and all(isinstance(h,str) and len(h)==64 and all(c in '0123456789abcdef' for c in h) for h in value.values()),'exactfive SHA256 scalars required')
 return value

def main():
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--expected-hashes',required=True);parser.add_argument('--expected-hashes-sha256',required=True);args=parser.parse_args()
 global EXPECTED_HASHES
 EXPECTED_HASHES=load_expected_hashes(args.expected_hashes,args.expected_hashes_sha256)
 need(isinstance(EXPECTED_HASHES,dict) and set(EXPECTED_HASHES)==set(NAMES),'PENDING_ACTUAL_ORIGINAL_FIVE_HASHES')
 need(os.getuid()==os.geteuid()==0,'exact root read-only metadata helper required')
 need(resource.getrlimit(resource.RLIMIT_AS)==(1073741824,1073741824),'exact inherited summary1GiB profile required')
 resource.setrlimit(resource.RLIMIT_CORE,(0,0))
 raw=SUMMARY.read_bytes();need(digest(raw)==SUMMARY_SHA,'exact accepted summary source required')
 s=importlib.util.spec_from_file_location('finite_original_summary',SUMMARY);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
 data=m.read_all();m.summarize(data);need({n:digest(data[n][0]) for n in NAMES}==EXPECTED_HASHES,'original five hash authority differs')
 parent=os.open(m.OUTPUT,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);rows=[]
 try:
  root=os.fstat(parent);need(root.st_uid==0 and stat.S_IMODE(root.st_mode)==0o700,'fixed output root metadata differs')
  for name in NAMES:
   fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=parent)
   try:
    before=os.fstat(fd);need(stat.S_ISREG(before.st_mode) and before.st_uid==0 and before.st_nlink==1 and 0<before.st_size<=128<<20,'bounded root single-link regular original required')
    with os.fdopen(os.dup(fd),'rb') as f:raw=f.read(before.st_size+1)
    after=os.fstat(fd);named=os.stat(name,dir_fd=parent,follow_symlinks=False)
    keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys),'original FD metadata raced')
    need(len(raw)==before.st_size and raw==data[name][0] and digest(raw)==EXPECTED_HASHES[name],'original bytes differ')
    rows.append(dict(path=str(m.OUTPUT/name),device=after.st_dev,inode=after.st_ino,uid=after.st_uid,gid=after.st_gid,mode=oct(stat.S_IMODE(after.st_mode)),nlink=after.st_nlink,size=after.st_size,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns,sha256=digest(raw)))
   finally:os.close(fd)
  need(os.stat(m.OUTPUT,follow_symlinks=False).st_ino==root.st_ino,'output root changed')
 finally:os.close(parent)
 need(m.read_all()==data,'original five changed across finite capture')
 result=dict(status='PASS_EXACT_ORIGINAL_FIVE_FD_METADATA_ONLY',nonce=m.NONCE,output=str(m.OUTPUT),members=5,objects=rows,summary_source_sha256=SUMMARY_SHA,file_sha256=EXPECTED_HASHES,observer_replayed=False,export_executed=False,cleanup_authorized=False,application_acceptance=False)
 out=(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode();need(len(out)<=1<<20,'finite metadata output bound');os.write(1,out)
if __name__=='__main__':main()
