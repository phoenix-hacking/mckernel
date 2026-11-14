"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,importlib.util,json,os,resource,signal,shutil,time
D=Path(__file__).resolve().parent
HELP=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(HELP.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec=importlib.util.spec_from_file_location('capture',HELP);cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,cap.stop)
os.sched_setaffinity(0,{0})
for k,v in [(resource.RLIMIT_AS,536870912),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,134217728),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
recipe=json.loads((D/'CAPSULE-RECIPE.json').read_bytes());assert hashlib.sha256((D/'CAPSULE-RECIPE.json').read_bytes()).hexdigest()=='4ba317940b7c97b83b2c4aaa7e166512a30bce08aefb56b8ef9f55fc1696e6e1'
A=D/'actual-stage-1';A.mkdir(mode=0o700)
def write(path,obj):cap.write(path,obj)
def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
capacity={'host_available':free('/home/holden/mckernel-work/host-preparation'),'scratch_available':free('/home/holden/mckernel-work/scratch'),'host_threshold':140534349824,'scratch_threshold':13899923456,'mem_available_line':next(x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:'))}
write(A/'capacity.json',capacity)
assert capacity['host_available']>=capacity['host_threshold'] and capacity['scratch_available']>=capacity['scratch_threshold'],'capacity floors'
for row in recipe['source_cohort']:assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()==row['sha256'],row['path']
results=[]
for name,argv in [('overlay',recipe['command']),('consumer',['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'validate_actual.py')])]:
 c=A/(name+'-capture');c.mkdir(mode=0o700);command={'argv':argv,'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'};write(c/'command.json',command)
 result=cap.owned_capture(command,c,120,lambda:None);write(c/'RESULT.json',result);results.append(result)
 assert result['returncode']==0 and result['direct_child_joined'] and result['group_absent'] and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,(name,result)
 if name=='overlay':
  raw=(c/'stdout').read_bytes();metadata=json.loads(raw);fd=os.open(A/'overlay-manifest.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
  m=json.loads((D/'manifest.PENDING.json').read_bytes())
  for key,fn in [('derived_initramfs','lifecycle.cpio.gz'),('overlay_manifest','overlay-manifest.json')]:
   p=A/fn;s=p.stat();m['staging'][key]={'path':str(p),'sha256':metadata['output_sha256'] if key=='derived_initramfs' else hashlib.sha256(raw).hexdigest(),'size':s.st_size,'mode':s.st_mode}
  write(A/'manifest.json',m)
write(A/'FINAL-RESULT.json',{'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_ACTUAL_OVERLAY_AND_TYPED_FULL_MANIFEST','commands':results,'validation':json.loads((A/'VALIDATION.json').read_bytes()),'native_result':None,'cpu0_released':True})
print(json.dumps({'status':'PASS','seconds':[r['seconds'] for r in results],'cpu0_released':True}))
