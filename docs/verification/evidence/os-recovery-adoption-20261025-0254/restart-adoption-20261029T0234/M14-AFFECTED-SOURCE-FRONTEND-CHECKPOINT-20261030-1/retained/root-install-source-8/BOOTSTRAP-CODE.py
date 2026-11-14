import hashlib,os,stat,sys,types,signal
EXPECTED_INSTALL='f347c6d5650a88756176526b1a7751b9e0a76768b4d51241844598b206b8e07b'
EXPECTED_ISSUER='2e1692241d40d473daa7ced0ed1113e065f50017e51aadf217187caede58a5a4'
EXPECTED_PRELIM='de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d'
EXPECTED_WAIT='e0c482277186aecc7e1b2912e9060bcf82fe8825657a973a991073189f74fa0b'
EXPECTED_COMPLETION='ce03649dfcd544abf434c8b7a2da9820bc363e50215d880585e9d49f41a10eb7'
PINS=(('ownership_latch','fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390'),('graph_observations','df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed'),('pidfd_compat','068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'),('pidfd_custody','3b22cac50183723456e6701031f00bdc446c04641c08c5864f1a379b5407686e'),('deferred_fork','b28d2f3483fb90c858479b65c9cebe6bd1b586c01902f004ec44964da6b4625f'))
if len(sys.argv)!=17:raise ValueError('exact bootstrap arguments required')
installer_path,issuer_path,completion_path,prelim_path,wait_path,intent_path,intent_sha,source_path,root_path,code_path,lease_path,closure_path,controls_path,capacity_path,host_custody_path,owner_path=sys.argv[1:]
hold=[]
def opened(path,flags):
 if not path.startswith('/') or '//' in path:raise ValueError('absolute path')
 parts=path.split('/')[1:]
 if not parts or any(x in ('','.','..') for x in parts):raise ValueError('path components')
 fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);hold.append(fd)
 for component in parts[:-1]:
  fd=os.open(component,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);hold.append(fd)
 fd=os.open(parts[-1],flags|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);hold.append(fd)
 return fd
def verified(fd,expected):
 before=os.fstat(fd)
 if not stat.S_ISREG(before.st_mode) or before.st_size>2097152:raise ValueError('source size')
 data=b''
 while len(data)<=2097152:
  chunk=os.read(fd,min(65536,2097153-len(data)))
  if not chunk:break
  data+=chunk
 after=os.fstat(fd)
 if ((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or len(data)!=before.st_size or hashlib.sha256(data).hexdigest()!=expected):raise ValueError('source bytes')
 return data
installer_fd=opened(installer_path,os.O_RDONLY);installer_raw=verified(installer_fd,EXPECTED_INSTALL)
wait_fd=opened(wait_path,os.O_RDONLY);wait_raw=verified(wait_fd,EXPECTED_WAIT)
issuer_fd=opened(issuer_path,os.O_RDONLY);issuer_raw=verified(issuer_fd,EXPECTED_ISSUER)
completion_fd=opened(completion_path,os.O_RDONLY);completion_raw=verified(completion_fd,EXPECTED_COMPLETION)
prelim_fd=opened(prelim_path,os.O_RDONLY);prelim_raw=verified(prelim_fd,EXPECTED_PRELIM)
source=opened(source_path,os.O_RDONLY|os.O_DIRECTORY)
for name,digest in PINS:
 if name in sys.modules:raise ValueError('module already loaded')
 fd=os.open(name+'.py',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=source);hold.append(fd)
 raw=verified(fd,digest);mod=types.ModuleType(name);mod.__file__=source_path+'/'+name+'.py';sys.modules[name]=mod
 exec(compile(raw,mod.__file__,'exec'),mod.__dict__)
install=types.ModuleType('install_source_closure');install.__file__=installer_path
install._BOOTSTRAP_INSTALLER_HASH=EXPECTED_INSTALL;install._BOOTSTRAP_SOURCE_FD=installer_fd;sys.modules[install.__name__]=install
exec(compile(installer_raw,installer_path,'exec'),install.__dict__)
prelim=types.ModuleType('reviewed_controller_reader');prelim.__file__=prelim_path;sys.modules[prelim.__name__]=prelim
exec(compile(prelim_raw,prelim_path,'exec'),prelim.__dict__)
completion=types.ModuleType('install_completion');completion.__file__=completion_path;sys.modules[completion.__name__]=completion
exec(compile(completion_raw,completion_path,'exec'),completion.__dict__)
issuer=types.ModuleType('install_issuer');issuer.__file__=issuer_path;sys.modules[issuer.__name__]=issuer
exec(compile(issuer_raw,issuer_path,'exec'),issuer.__dict__)
intent=opened(intent_path,os.O_RDONLY)
root=opened(root_path,os.O_RDONLY|os.O_DIRECTORY)
code=opened(code_path,os.O_RDONLY|os.O_DIRECTORY)
closure=opened(closure_path,os.O_RDONLY)
controls=opened(controls_path,os.O_RDONLY)
capacity=opened(capacity_path,os.O_RDONLY)
host_custody=opened(host_custody_path,os.O_RDONLY)
owner=opened(owner_path,os.O_RDONLY)
try:
 result,latch=issuer.run(install,prelim,intent,intent_sha,source,root,code,lease_path,closure,controls,capacity,host_custody,owner,wait_raw.decode('utf-8'))
 try:
  import json
  raw=(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
  if os.write(1,raw)!=len(raw):raise OSError('short result capture')
 except BaseException as error:
  latch.fail(error)
  while True:signal.pause()
 if not result['operation_lease_fd_closed']:
  while True:signal.pause()
except issuer.IssuerUnknown as failure:
 # Hold the actual latch/FD references; an external Root owner owns retirement.
 while True:signal.pause()
