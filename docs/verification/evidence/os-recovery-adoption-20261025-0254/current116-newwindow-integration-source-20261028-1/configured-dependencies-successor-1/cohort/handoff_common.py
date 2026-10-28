"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,math,os,stat,time
SCOPE=__doc__
CUTOFFS=[1793253600.0, 1035706.5689547858, 1051044.6960026678]
BOOT='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
REVIEWER='/root/observerreview'
def need(v,m):
 if not v:raise ValueError(m)
def reference(p):
 p=Path(p);need(p.is_absolute() and not p.is_symlink(),'absolute regular reference')
 a=p.stat();need(stat.S_ISREG(a.st_mode),'regular reference');h=hashlib.sha256(p.read_bytes()).hexdigest();z=p.stat();need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns),'stable reference')
 return dict(path=str(p),bytes=z.st_size,sha256=h)
def verified_raw(r):
 need(isinstance(r,dict) and set(r)=={'path','bytes','sha256'},'exact byte reference')
 p=Path(r['path']);need(p.is_absolute() and not p.is_symlink(),'absolute regular reference')
 a=p.stat();need(stat.S_ISREG(a.st_mode),'regular reference')
 raw=p.read_bytes();z=p.stat()
 need((a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)==(z.st_dev,z.st_ino,z.st_size,z.st_mtime_ns,z.st_ctime_ns),'stable authenticated bytes')
 need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'exact authenticated raw bytes')
 return raw
def verify_ref(r):
 verified_raw(r);return Path(r['path']) # Byte-only; never JSON-decode a Python file.
def pairs(rows):
 d={}
 for k,v in rows:need(k not in d,'duplicate JSON key');d[k]=v
 return d
def reject_constant(value):raise ValueError('nonfinite JSON constant: '+value)
def finite_float(value):
 result=float(value);need(math.isfinite(result),'nonfinite JSON number');return result
def decode_object(raw):
 text=raw.decode('utf-8',errors='strict')
 v=json.loads(text,object_pairs_hook=pairs,parse_constant=reject_constant,parse_float=finite_float)
 need(isinstance(v,dict),'JSON object required');return v
def read_json(p):return decode_object(Path(p).read_bytes())
def read_json_ref(r):return decode_object(verified_raw(r))
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def clocks():
 need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'same actual boot')
 return [time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
def in_window(now,limits):need(len(now)==len(limits)==3 and all(n<c for n,c in zip(now,limits)),'earliest original clock clamp')
def atomic_json(path,value,before_publish=None):
 path=Path(path);tmp=path.with_name(path.name+'.complete-source-'+str(os.getpid()))
 raw=(json.dumps(value,indent=2)+'\n').encode();fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o400)
 try:
  view=memoryview(raw)
  while view:
   written=os.write(fd,view);need(written>0,'complete durable metadata write');view=view[written:]
  os.fsync(fd)
 finally:os.close(fd)
 # The final callback runs after all bytes are fsynced, immediately before
 # atomic O_EXCL publication. A stalled write cannot bypass final freshness.
 if before_publish is not None:before_publish()
 os.link(tmp,path) # Atomic O_EXCL publication; complete-source retained as evidence.
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return reference(path)
def no_launch(A):
 for n in ['OUTPUT','ACTUAL-INDEPENDENT-BUILD-EXECUTION-REVIEW.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','HOLDER/ROOT-BUILD-GRANT.READY.json','HOLDER/RUNNER.STARTED.json']:
  need(not os.path.lexists(A/n),'no prior launch/publication: '+n)
