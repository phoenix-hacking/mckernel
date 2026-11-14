"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,os,stat,time
SCOPE=__doc__
CUTOFFS=[1793165769.0,947874.5689514667,963213.695968197]
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
REVIEWER='/root/custody_release_review'
def need(v,m):
 if not v:raise ValueError(m)
def reference(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink(),'absolute regular reference')
 a=p.stat();need(stat.S_ISREG(a.st_mode),'regular reference');h=hashlib.sha256(p.read_bytes()).hexdigest();z=p.stat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns),'stable reference')
 return dict(path=str(p),bytes=z.st_size,sha256=h)
def verify_ref(r):
 need(isinstance(r,dict) and set(r)=={'path','bytes','sha256'} and reference(r['path'])==r,'exact unchanged bytes');return Path(r['path'])
def pairs(rows):
 d={}
 for k,v in rows:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def read_json(p):
 v=json.loads(Path(p).read_bytes(),object_pairs_hook=pairs);need(isinstance(v,dict),'JSON object required');return v
def read_json_ref(r):return read_json(verify_ref(r))
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def clocks():
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'same actual boot')
 return [time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
def in_window(now,limits):need(len(now)==len(limits)==3 and all(n<c for n,c in zip(now,limits)),'earliest original clock clamp')
def atomic_json(path,value):
 path=Path(path);tmp=path.with_name(path.name+'.complete-source-'+str(os.getpid()))
 raw=(json.dumps(value,indent=2)+'\n').encode();fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
 try:
  view=memoryview(raw)
  while view:
   written=os.write(fd,view);need(written>0,'complete durable metadata write');view=view[written:]
  os.fsync(fd)
 finally:os.close(fd)
 os.link(tmp,path) # Atomic O_EXCL publication; complete-source retained as evidence.
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return reference(path)
def no_launch(A):
 for n in ['OUTPUT','ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','HOLDER/ROOT-BUILD-GRANT.READY.json','HOLDER/RUNNER.STARTED.json']:
  need(not os.path.lexists(A/n),'no prior launch/publication: '+n)
