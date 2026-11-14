# Functional M14 source-only phase-zero literal; independent review required.
import hashlib,json,os,stat,sys
BASE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1'
V10=BASE+'/root-install-source-10'
P0=BASE+'/root-install-phase0-v10-source-2/phase0.py'
PRELIM=BASE+'/postjoin-daemon-metadata-observer-source-1/root_parent_preliminary.py'
PROOF=BASE+'/timeout-known-role-proof-1/PROOF.json'
PHASE_SHA='d1e70e5bad642974c84a9eb926861385420ef1f713d1743d2029a79cdf46c119'
CLOSURE_SHA='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'
def unique(pairs):
 out={}
 for key,value in pairs:
  if key in out:raise ValueError('duplicate admission key')
  out[key]=value
 return out
if len(sys.argv)!=4:raise ValueError('admission digest, expert-review path and digest required')
admission_sha,review_path,review_sha=sys.argv[1:]
if any(len(x)!=64 or any(c not in '0123456789abcdef' for c in x) for x in (admission_sha,review_sha)):raise ValueError('sha256 required')
raw=sys.stdin.buffer.read(2097153)
if len(raw)>2097152 or hashlib.sha256(raw).hexdigest()!=admission_sha:raise ValueError('admission bytes differ')
request=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite')))
sys.argv=['<phase0-v10>',V10+'/install_source_closure.py',V10+'/install_issuer.py',V10+'/install_completion.py',PRELIM,V10+'/WAIT-INSTALL-CODE.py',PROOF,review_path,review_sha,'unused','unused',V10+'/package','unused','unused','unused','unused','unused','unused','unused','unused']
import hashlib,os,stat,sys,types,signal
EXPECTED_INSTALL='7a6ecfc875758a60dd3c6641b87a53cf9780af1a6473f9826d38b0b0509e76da'
EXPECTED_ISSUER='18196891bdd58e29488c70a780f589787103b17c1f44e1a6e6b9de94f2985edd'
EXPECTED_PRELIM='de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d'
EXPECTED_WAIT='d8191218fde3da7972a4af4b37511af3ee6cb82bb106c42e1ed3c6466c58cbe4'
EXPECTED_COMPLETION='87092d1fa2a30b8fa1609c9692dd4dbd95953de518d8d846fbaeb2d6fe714e23'
EXPECTED_TIMEOUT_PROOF='2e7b538161bed50275f36befa2011344ccebc0370a4b2a6bcb4fed76235066f2'
PINS=(('ownership_latch','fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390'),('graph_observations','df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed'),('pidfd_compat','068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'),('pidfd_custody','3b22cac50183723456e6701031f00bdc446c04641c08c5864f1a379b5407686e'),('deferred_fork','b28d2f3483fb90c858479b65c9cebe6bd1b586c01902f004ec44964da6b4625f'))
if len(sys.argv)!=20:raise ValueError('exact bootstrap arguments required')
installer_path,issuer_path,completion_path,prelim_path,wait_path,timeout_proof_path,review_path,review_sha,intent_path,intent_sha,source_path,root_path,code_path,lease_path,closure_path,controls_path,capacity_path,host_custody_path,owner_path=sys.argv[1:]
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
proof_fd=opened(timeout_proof_path,os.O_RDONLY);proof_raw=verified(proof_fd,EXPECTED_TIMEOUT_PROOF)
if len(review_sha)!=64 or any(c not in '0123456789abcdef' for c in review_sha):raise ValueError('expert review digest')
review_fd=opened(review_path,os.O_RDONLY);review_raw=verified(review_fd,review_sha)
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

# The prelude deliberately does not claim the selected unprivileged review is
# already root immutable. Phase zero seals the exact held bytes first, then sets
# the model pins from those sealed bytes and the verified held source/toolproof.
phase_fd=opened(P0,os.O_RDONLY);phase_raw=verified(phase_fd,PHASE_SHA)
closure_fd=opened(V10+'/SOURCE-CLOSURE.json',os.O_RDONLY);closure_raw=verified(closure_fd,CLOSURE_SHA)
pins={'issuer_sha256':hashlib.sha256(issuer_raw).hexdigest(),'completion_sha256':hashlib.sha256(completion_raw).hexdigest(),'timeout_proof_sha256':hashlib.sha256(proof_raw).hexdigest()}
phase={'__name__':'__phase0__'}
exec(compile(phase_raw,P0,'exec'),phase)
phase['run'](request,install,issuer,prelim,completion,closure_raw,wait_raw,review_raw,pins)
