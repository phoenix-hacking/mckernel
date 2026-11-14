import hashlib,json,os,stat,sys,types
SOURCE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/usr-bin-functional-mode-repair-1/mode_repair.py'
SOURCE_SHA='2d2dc33884f82deca9ad00b37d8d36e0298b282126110c0158e370ef9818287c'
PRELIM='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/postjoin-daemon-metadata-observer-source-1/root_parent_preliminary.py'
PRELIM_SHA='de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d'
held=[]
def verified(path,expected):
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
if len(sys.argv)!=6:raise ValueError('exact repair release arguments')
release_path,release_sha,review_path,capture_device,capture_inode=sys.argv[1:]
if len(release_sha)!=64 or any(c not in '0123456789abcdef' for c in release_sha) or not capture_device.isdigit() or not capture_inode.isdigit():raise ValueError('actual release/capture binding')
prelim=module('repair_prelim',PRELIM,verified(PRELIM,PRELIM_SHA))
repair=module('functional_mode_repair',SOURCE,verified(SOURCE,SOURCE_SHA))
raw=repair.read_small(release_path,65536)
if hashlib.sha256(raw).hexdigest()!=release_sha:raise ValueError('release hash')
release=json.loads(raw,object_pairs_hook=repair.unique)
if repair.canon(release)!=raw:raise ValueError('canonical release required')
repair.guarded_repair(prelim,release,release_sha,int(capture_device),int(capture_inode),review_path)
