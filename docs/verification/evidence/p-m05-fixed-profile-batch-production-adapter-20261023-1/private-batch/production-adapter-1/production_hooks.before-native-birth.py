"""Pinned P05 Production Hooks: authenticate bytes, hand off27:4, stop on uncertainty.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No execution release is installed. Future artifact/first-restoration slots stay null.
"""
from pathlib import Path
import base64,fcntl,hashlib,importlib.util,json,os,re,resource,signal,stat,subprocess,time
HERE=Path(__file__).resolve().parent
CAPTURE=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
CAPTURE_SHA='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
NATIVE_CAPTURE=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/capture_native199_owner.py')
NATIVE_CAPTURE_SHA='e41eecb6a3f2eeb37338b82233241dc3f9659f529103f5c300bfe17ea420d3cf'
MUTEX='/run/lock/mckernel-development.lock';SCRATCH=Path('/home/holden/mckernel-work/scratch');HOST=Path('/home/holden')
SCRATCH_UUID='2a5768c8-718d-4914-bdc0-6b32c5a92a52'
OLD_MODULES={'daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c','50f6e2bc822dcff45b99aa2fc8da2c00e1469c3d0d10f1ec510ae82aea80e581','bff603a5d7ff1a9a3498bf0fe32b2c017170764d17d0d42103e82539576824af'}
CANONICAL=[str(SCRATCH/n) for n in ('native-running-external-modules.lease.json','native-running-external-modules-operational-exclusion.json','native-exact-candidate-operational-exclusion-scratch18-image-1.json','mckernel-heavy-operation.lock')]+['/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/'+n for n in ('common-exclusion.json','lease.json')]
PYTHON='/home/holden/anaconda3/bin/python3';SHA=re.compile('[0-9a-f]{64}\\Z');NONCE=re.compile('[0-9a-f]{32}\\Z')
def need(ok,reason):
 if not ok:raise ValueError(reason)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def encoded(x):return json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def strict(raw):
 def pairs(rows):
  out={}
  for k,v in rows:need(k not in out,'duplicate JSON key');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda _:need(False,'nonfinite JSON'))
def source_module(path,pin):
 need(digest(Path(path).read_bytes())==pin,'pinned source drift');s=importlib.util.spec_from_file_location('p05_production_'+Path(path).stem,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def before_snapshot(serial):
 rows=[]
 for line in serial.splitlines():
  if line.startswith('ND_REBOOT_CHUNK '):
   r=strict(line[len('ND_REBOOT_CHUNK '):])
   if r['name']=='before':rows.append(r)
 out=bytearray()
 for r in rows:need(type(r['offset']) is int and r['offset']==len(out),'ordered before snapshot chunks');out.extend(bytes.fromhex(r['hex']));need(len(out)<262144,'bounded before snapshot')
 need(bool(rows),'before snapshot producer absent');return bytes(out)

class LiveOS:
 """Only OS effects; capture implementations are the accepted existing sources."""
 def __init__(self):
  self.native_process=None;self.last_identity={};self.capture=source_module(CAPTURE,CAPTURE_SHA)
  for sig in self.capture.STOP_SIGNALS:signal.signal(sig,self.capture.stop)
 def now(self):return time.monotonic_ns()
 def read(self,path,maximum=16<<20):
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=maximum,'bounded singlelink FD');raw=os.read(fd,maximum+1);b=os.fstat(fd);named=Path(path).lstat();keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns');need(len(raw)==a.st_size and all(getattr(a,k)==getattr(b,k)==getattr(named,k) for k in keys),'stable FD bytes');self.last_identity[str(path)]={'device':b.st_dev,'inode':b.st_ino,'uid':b.st_uid,'gid':b.st_gid,'nlink':b.st_nlink,'mode':oct(stat.S_IMODE(b.st_mode)),'mtime_ns':b.st_mtime_ns,'ctime_ns':b.st_ctime_ns};return raw
  finally:os.close(fd)
 def claim(self,path,value):
  directory=Path(path).parent;s=directory.lstat();need(stat.S_ISDIR(s.st_mode) and not directory.is_symlink() and s.st_uid==os.geteuid() and stat.S_IMODE(s.st_mode)==0o700,'private exclusive release namespace');self.capture.write(Path(path),value)
 def mutex(self):
  fd=os.open(MUTEX,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  try:
   s=os.fstat(fd);need(stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1 and (s.st_dev,s.st_ino)==(27,4),'permanent mutex identity');fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);return fd
  except BaseException:os.close(fd);raise
 def unlock(self,handle):os.close(handle)
 def facts(self):
  absent=[]
  for p in CANONICAL:
   try:Path(p).lstat()
   except FileNotFoundError:absent.append(p)
  src=Path('/dev/disk/by-uuid')/SCRATCH_UUID;s=src.stat();need(stat.S_ISBLK(s.st_mode) and s.st_rdev==SCRATCH.stat().st_dev,'fresh scratch UUID identity')
  def free(p):s=os.statvfs(p);return s.f_bavail*s.f_frsize
  mem=dict((r.split(':',1)[0],r.split(':',1)[1].strip()) for r in Path('/proc/meminfo').read_text().splitlines())
  return {'canonical_absent':absent,'scratch_uuid':SCRATCH_UUID,'host_free':free(HOST),'scratch_free':free(SCRATCH),'memory_available':int(mem['MemAvailable'].split()[0])*1024,'affinity':sorted(os.sched_getaffinity(0)),'AS':list(resource.getrlimit(resource.RLIMIT_AS)),'FSIZE':list(resource.getrlimit(resource.RLIMIT_FSIZE)),'NPROC':list(resource.getrlimit(resource.RLIMIT_NPROC))}
 def native(self,operation_ref,operation,timeout):
  need(self.native_process is None,'native owner already retained');need(digest(self.read(NATIVE_CAPTURE))==NATIVE_CAPTURE_SHA,'native capture source pin')
  argv=['/usr/bin/taskset','-c','7',PYTHON,'-I','-B',str(NATIVE_CAPTURE),'--operation',operation_ref['path'],'--sha256',operation_ref['sha256']]
  self.native_process=subprocess.Popen(argv,stdin=subprocess.DEVNULL,start_new_session=True,close_fds=True)
  # Never timeout-kill a root owner. Keep the process object on uncertainty.
  code=self.native_process.wait(timeout=timeout);self.native_process=None;need(code==0,'native capture transport failed')
  return strict(self.read(Path(operation['capture_directory'])/'status.json'))
 def readonly(self,argv,path,role):
  Path(path).mkdir(mode=0o700)
  def limits():
   os.sched_setaffinity(0,{7});resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30));resource.setrlimit(resource.RLIMIT_CPU,(30 if role=='export' else 10,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(32<<20 if role=='export' else 1<<20,)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
  return self.capture.owned_capture({'argv':argv},Path(path),35 if role=='export' else 15,limits)

def authenticate_capture(io,capture,native=False):
 if native:
  need(capture.get('status')=='PASS' and capture.get('returncode')==0 and capture.get('direct_child_joined') is True and capture.get('streams_closed') is True and capture.get('process_group_absent') is True,'actual native capture retirement');descriptors={n:capture[n] for n in ('stdout','stderr')}
 else:
  need(capture.get('returncode')==0 and capture.get('direct_child_joined') is True and capture.get('closed_streams') is True and capture.get('group_absent') is True and not capture.get('timed_out') and not capture.get('error') and not capture.get('retirement_error') and capture.get('remaining_group_members')==[],'actual readonly capture retirement');descriptors=capture['captures']
 data={}
 for n,ref in descriptors.items():
  raw=io.read(ref['path']);size=ref.get('size',ref.get('bytes'));need(type(size) is int and len(raw)==size and digest(raw)==ref['sha256'],'owned capture stream FD hash/length');need(all(ref.get(k)==v for k,v in io.last_identity[str(ref['path'])].items()) and set(io.last_identity[str(ref['path'])])=={'device','inode','uid','gid','nlink','mode','mtime_ns','ctime_ns'},'owned capture FD identity');data[n]=raw
 need(data['stderr']==b'','capture stderr');return data

def authenticate_owner(raw,case,profile,native):
 export=strict(raw);root=str(Path(case['attempt_parent']).with_name(Path(case['attempt_parent']).name+'.owner-'+case['nonce']))
 need(export.get('status')=='READONLY_EXACT_CLOSED_OWNER_EVIDENCE_EXPORT' and export.get('root')==root and export.get('root_mutations')==0,'exact readonly exported root')
 ident=export['root_identity'];need(ident['uid']==ident['gid']==0 and ident['mode']==0o700 and type(ident['inode']) is int and ident['inode']>0,'owned root identity')
 files={};total=0
 for row in export['files']:
  name=row['name'];need(type(name) is str and name not in files and '/' not in name and name not in ('.','..'),'unique owner file');blob=base64.b64decode(row['base64'],validate=True);info=row['identity'];need(row['source_path']==root+'/'+name and stat.S_ISREG(info['st_mode']) and info['st_nlink']==1 and info['st_size']==len(blob) and info['st_uid']==info['st_gid']==0 and digest(blob)==row['sha256'],'actual exported owner bytes');files[name]=blob;total+=len(blob)
 need(total==export['total_source_bytes']<=8<<20,'complete bounded owner export')
 owner=strict(files['owner.json']);terminal=strict(files['result.json']);inner=strict(files['inner-result.json']);cid=terminal['container']
 need(SHA.fullmatch(cid) and owner['nonce']==case['nonce'] and owner['name']=='mckernel-native-diagnostic-'+case['nonce'] and owner['attempt']==str(Path(case['attempt_parent'])/('attempt-'+case['nonce'])) and owner['owner_sha256']==profile['owner_sha256'],'actual owner invocation')
 need(owner['lock']['dev']==27 and owner['lock']['ino']==4 and owner['lock']['uid']==0 and owner['lock']['nlink']==1 and owner['outer']['pgid']==owner['outer']['sid']==native['pid'] and type(owner['outer']['proc_starttime']) is int and owner['outer']['proc_starttime']>0,'actual mutex handoff and root outer capture')
 need(terminal['status']=='PROTOCOL_PASS' and terminal['absence_verified'] is True and terminal['lease_retained'] is False and terminal['failure'] is None and terminal['secondary']==[] and terminal['secondary_omitted']==0,'owner terminal closure')
 need(inner['status']=='PROTOCOL_PASS' and inner['cleanup']=={'reaped':True,'errors':[]} and inner['capture_errors']==[],'actual inner QEMU reap')
 q=inner['qemu_evidence'];observation=inner['observation'];need(q==observation['qemu_evidence'] and q['argv']==inner['admitted_qemu_argv'] and type(q['returncode']) is int and q['returncode'] in (0,-15,-9) and q['pid']==q['pgid']==q['sid'] and q['starttime_ticks']>0,'actual QEMU identity/retirement')
 need(observation['serial'].encode()==files['serial.log'] and observation['debugcon'].encode()==files['debugcon.log'],'actual observation bytes')
 for name,ref in strict(files['capture-bindings.json']).items():need(name in files and len(files[name])==ref['size'] and digest(files[name])==ref['sha256'],'actual captured guest file join')
 commands=[]
 for name in sorted(files):
  if re.fullmatch(r'[0-9]{3}-[^/]+\.json',name):
   row=strict(files[name]);r=row['command'];need(r['reaped'] is True and type(r['pid']) is int and r['pid']>0 and r['pgid']==r['pid'] and r['proc_starttime']>0 and r['returncode']==row['returncode'] and row['failure'] is None,'actual Docker client reap');commands.append((name,row))
 need(commands and [int(n[:3]) for n,_ in commands]==list(range(1,len(commands)+1)) and len({r['command']['pid'] for _,r in commands})==len(commands),'complete distinct contiguous Docker command journal')
 for name,row in commands:need(name[:-5]+'.stdout' in files and name[:-5]+'.stderr' in files,'complete Docker command streams')
 creates=[(n,r) for n,r in commands if r['argv'][3]=='create'];need(len(creates)==1,'one actual container create')
 need(files[creates[0][0][:-5]+'.stdout']==(cid+'\n').encode(),'actual created container identity')
 create=creates[0][1]['argv'];need(create[create.index('--manifest-sha256')+1]==profile['manifest']['sha256'] and create[create.index('--owner-sha256')+1]==profile['owner_sha256'] and create[create.index('--nonce')+1]==case['nonce'],'actual current manifest/source in container argv')
 removed=[(i,n,r) for i,(n,r) in enumerate(commands) if r['argv'][3:]==['rm','--force',cid]];need(len(removed)==1 and removed[0][2]['returncode']==0,'actual exact container removal');i=removed[0][0]
 inspected=[(n,r) for n,r in commands[:i] if r['argv'][3:]==['inspect',cid] and r['returncode']==0];need(bool(inspected),'actual pre-remove inspection');actual_inspect=strict(files[inspected[-1][0][:-5]+'.stdout']);need(type(actual_inspect) is list and len(actual_inspect)==1 and actual_inspect[0]['Id']==cid,'actual inspected container identity')
 state=strict(files['state.json']);need(actual_inspect[0]['State']==state,'actual inspected terminal state join');need(state['Pid']==0 and state['Running'] is False and state['OOMKilled'] is False and state['Status']=='exited','actual container process exit')
 filters=['name=^/'+owner['name']+'$','label=mckernel.native-diagnostic.owner='+case['nonce'],'id='+cid]
 for filter_value in filters:
  matches=[(n,r) for n,r in commands[i+1:] if r['argv']==['/usr/bin/sudo','-A','/usr/bin/docker','ps','-aq','--no-trunc','--filter',filter_value]];need(len(matches)==1 and matches[0][1]['returncode']==0,'actual postremove query');stem=matches[0][0][:-5];need(files[stem+'.stdout']==files[stem+'.stderr']==b'','actual postremove empty streams')
 return {'files':files,'inner':inner,'container':cid,'docker_clients':len(commands),'owner':owner}

class ProductionHooks:
 def __init__(self,batch,profile,cases,release_ref,binding_ref,output_root,io=None):
  self.batch=batch;self.profile=profile;self.cases=cases;self.io=LiveOS() if io is None else io;self.output=Path(output_root);self.index=0;self.context=None;self.previous=None;self.claimed=False
  self.binding=self._ref(binding_ref);self.release=self._ref(release_ref);need(self.release['output_root']==str(self.output) and self.output.is_absolute(),'one released output/use-record namespace');need(self.release['adapter_sha256']==digest(Path(__file__).read_bytes()) and self.release['batch_source_sha256']==digest(Path(batch.__file__).read_bytes()),'pinned production hook/batch source')
  need(self.release['status']=='PASS_EXECUTION' and self.release['nonces']==[c['nonce'] for c in cases] and 1<=len(cases)<=32 and len(set(self.release['nonces']))==len(cases),'single exact ordered batch release')
  need(len(self.release['operation_refs'])==len(cases) and len({r['path'] for r in self.release['operation_refs']})==len(cases),'one unique operation per nonce')
  need(self.release['profile_sha256']==profile['_sha256'] and self.release['binding_sha256']==binding_ref['sha256'] and self.release['operations']==[{'nonce':c['nonce'],'command_sha256':digest(json.dumps(c['command'],separators=(',',':')).encode())} for c in cases],'exact released commands/profile')
 def _ref(self,ref):
  need(type(ref) is dict and set(ref)=={'path','sha256'},'pinned file reference');raw=self.io.read(ref['path']);need(digest(raw)==ref['sha256'],'pinned production binding drift');return strict(raw)
 def _future_ready(self):
  for key in ('profile_sha256','sdk_acceptance','launcher_acceptance','first_complete_restoration','artifact_tuple'):
   need(self.binding.get(key) is not None,'future production profile unbound: '+key)
  need(self.binding['profile_sha256']==self.profile['_sha256'] and set(r['sha256'] for r in self.profile['_manifest']['modules'])!=OLD_MODULES,'old20352 profile/cycle cannot transfer')
  tuple_value={'modules':[{k:r[k] for k in ('sha256','size')} for r in self.profile['_manifest']['modules']],'launcher':{k:self.profile['_manifest']['artifacts']['mcexec'][k] for k in ('sha256','size')}}
  need(encoded(tuple_value)==encoded(self.binding['artifact_tuple']),'fixed complete future artifact tuple')
  for key in ('sdk_acceptance','launcher_acceptance','first_complete_restoration'):
   proof=self._ref(self.binding[key]);need(proof.get('profile_sha256')==self.profile['_sha256'] and proof.get('artifact_tuple_sha256')==digest(encoded(tuple_value)) and proof.get('accepted') is True,'matching future acceptance: '+key)
  need(self.release['export_source_sha256']==digest((HERE/'export_closed_owner.py').read_bytes()),'pinned readonly producer')
 def identity(self,c):return {'nonce':c['nonce'],'profile_sha256':self.profile['_sha256'],'command_sha256':digest(json.dumps(c['command'],separators=(',',':')).encode())}
 def _facts(self):
  facts=self.io.facts();need(facts['canonical_absent']==CANONICAL and facts['scratch_uuid']==SCRATCH_UUID,'actual six canonical records/UUID')
  limits=self.release['resources'];need(limits['host_required']>=16<<30 and limits['scratch_required']>=12<<30 and limits['memory_required']>=14<<30,'reviewed resource floors')
  need(facts['host_free']>=limits['host_required'] and facts['scratch_free']>=limits['scratch_required'] and facts['memory_available']>=limits['memory_required'],'fresh full-growth aggregate headroom')
  need(facts['affinity']==[7] and facts['AS']==[2<<30,2<<30] and facts['FSIZE']==[32<<20,32<<20] and facts['NPROC']==self.release['inherited_NPROC'],'actual fixed parent profile/NPROC');return facts
 def admit(self,case,previous):
  self._future_ready();need(self.index<len(self.cases) and case==self.cases[self.index] and self.context is None,'serial next exact operation');need(previous==self.previous,'actual previous qualified/physical retirement chain')
  if not self.claimed:self.io.claim(self.output/'batch-release-used.json',{'release_sha256':digest(encoded(self.release)),'nonces':self.release['nonces']});self.claimed=True
  lock=self.io.mutex()
  try:facts=self._facts();now=self.io.now();self.context={'case':case,'lock':lock,'facts':facts,'native':None,'execution':None,'qualified':False}
  except BaseException:self.io.unlock(lock);raise
  r=self.identity(case);r.update({k:True for k in self.batch.PARENT_CHECKS});r.update(resource_profile_sha256=digest(encoded(self.profile['resource_profile'])),permanent_mutex_identity=[27,4],observed_ns=now,expires_ns=now+30_000_000_000,previous_retirement_sha256=None if previous is None else previous['sha256'],expected_epochs=[[0,1,1],[0,2,2]]);return r
 def _readonly(self,case,role,tail):
  prefix=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu='+('30:30' if role=='export' else '10:10'),'--fsize='+('33554432:33554432' if role=='export' else '1048576:1048576'),'--core=0:0','--']
  record=self.io.readonly(prefix+tail,self.output/(case['nonce']+'-'+role),role);return authenticate_capture(self.io,record)
 def execute(self,case,admission):
  ctx=self.context;need(ctx is not None and ctx['case']==case and ctx['lock'] is not None,'actual admitted mutex')
  try:self._facts();need(self.io.now()<admission['expires_ns'],'actual admission deadline before handoff')
  except BaseException:self.io.unlock(ctx['lock']);ctx['lock']=None;ctx['admission_aborted']=True;raise
  self.io.unlock(ctx['lock']);ctx['lock']=None
  op_ref=self.release['operation_refs'][self.index];op=self._ref(op_ref);need(op['argv']==case['command'] and op['nonce']==case['nonce'] and op['profile']==self.profile['resource_profile'] and op['cpu']==7 and op['stream_cap_bytes']==32<<20,'fixed actual native operation')
  native=self.io.native(op_ref,op,case['timeout_seconds']);need(native['argv']==case['command'],'actual native captured command');authenticate_capture(self.io,native,True);ctx['native']=native
  exported=self._readonly(case,'export',['/usr/bin/sudo','-A',PYTHON,'-I','-B',str(HERE/'export_closed_owner.py'),'--parent',case['attempt_parent'],'--nonce',case['nonce'],'--owner-sha256',self.profile['owner_sha256']])
  owner=authenticate_owner(exported['stdout'],case,self.profile,native);ctx['owner']=owner
  result=self.identity(case);result.update(returncode=native['returncode'],owner_status=owner['inner']['status'],admission_sha256=digest(encoded(admission)),observation=owner['inner']['observation'],kernel_before=before_snapshot(owner['inner']['observation']['serial']));ctx['execution']=result
  ctx['qualified']=self.batch.evaluate_semantics(self.profile,result)['qualifies_first_restore_reboot'];return result
 def retire(self,case):
  ctx=self.context;need(ctx is not None and ctx['case']==case and ctx['native'] is not None and ctx.get('owner') is not None,'uncertain owner retained; no automatic export/retry/kill')
  lock=self.io.mutex()
  try:
   self._facts();cid=ctx['owner']['container'];filters=['name=^/mckernel-native-diagnostic-'+case['nonce']+'$','label=mckernel.native-diagnostic.owner='+case['nonce'],'id='+cid]
   for i,value in enumerate(filters):need(self._readonly(case,'query'+str(i),['/usr/bin/sudo','-A','/usr/bin/docker','ps','-aq','--no-trunc','--filter',value])['stdout']==b'','actual fresh name/label/ID absence')
   self._facts();r=self.identity(case);r.update({k:True for k in self.batch.RETIRE_CHECKS});r.update(lease_retained=False,retired_ns=self.io.now(),permanent_mutex_identity=[27,4],authenticated_owner_files=len(ctx['owner']['files']),authenticated_docker_reaps=ctx['owner']['docker_clients']);receipt={'receipt':r,'sha256':digest(encoded(r))}
   if ctx['qualified']:self.previous=receipt;self.index+=1;self.context=None
   return r
  finally:self.io.unlock(lock)
