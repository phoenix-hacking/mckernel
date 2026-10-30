import hashlib,json,os,stat,sys,types
CONTROL='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-current-control-stop-1/control_stop.py'
CONTROL_SHA='9b62caf7e5e0b47e7bb714248445150d09618b554fcdb19d112ae1b9af678e14'
COMPAT='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-10/package/pidfd_compat.py'
COMPAT_SHA='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
held=[]
def source(path,expected):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);held.append(fd)
 st=os.fstat(fd)
 if not stat.S_ISREG(st.st_mode) or st.st_size>2097152:raise ValueError('source bound')
 raw=b''
 while len(raw)<=2097152:
  b=os.read(fd,min(65536,2097153-len(raw)))
  if not b:break
  raw+=b
 after=os.fstat(fd)
 if len(raw)!=st.st_size or len(raw)>2097152 or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or hashlib.sha256(raw).hexdigest()!=expected:raise ValueError('source bytes')
 return raw
def module(name,path,raw):
 obj=types.ModuleType(name);obj.__file__=path;sys.modules[name]=obj
 exec(compile(raw,path,'exec'),obj.__dict__);return obj
if len(sys.argv)!=3:raise ValueError('exact stop release arguments')
release_path,release_sha=sys.argv[1:]
if len(release_sha)!=64 or any(c not in '0123456789abcdef' for c in release_sha):raise ValueError('release SHA')
compat=module('pidfd_compat',COMPAT,source(COMPAT,COMPAT_SHA))
control=module('owned_control_stop',CONTROL,source(CONTROL,CONTROL_SHA))
raw=control.bounded(release_path,65536)
if hashlib.sha256(raw).hexdigest()!=release_sha:raise ValueError('release hash')
release=json.loads(raw,object_pairs_hook=control.unique)
if control.canonical(release)!=raw:raise ValueError('canonical release bytes required')
control.guarded_run(compat,release,release_sha)
