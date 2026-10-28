"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Single custom-BFD stopped-container retirement. Source-only until exact Root release.
Reuse existing transport/census/lock primitives; never signal or release old records.
"""
from pathlib import Path
import argparse,ast,copy,hashlib,importlib.util,json,math,os,re,resource,signal,stat,subprocess,time,types,uuid
D=Path(__file__).resolve().parent
BINDINGS_SHA='fa92f810ea19d5b8cd2d4d6f16e2f7d9b34a0647f4a2999652ce55ce01fd4dea'
SELF=D/'retire_exact_bfd_stopped_container.py'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PREFIX=['/usr/bin/sudo','-A','/usr/bin/docker','--host=unix:///var/run/docker.sock']
LOCK=Path('/run/lock/mckernel-development.lock')

class Refusal(RuntimeError):pass

def need(ok,why):
 if not ok:raise Refusal(why)
def canonical(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def strict(raw):
 def pairs(items):
  out={}
  for k,v in items:need(k not in out,'duplicate JSON key');out[k]=v
  return out
 return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda value:(_ for _ in ()).throw(Refusal('nonfinite JSON')))
def reference(path):
 path=Path(path);need(path.is_absolute() and not path.is_symlink(),'absolute regular byte subject')
 for parent in path.parents:need(not parent.is_symlink() and parent.is_dir(),'ordinary byte-subject ancestry')
 a=path.stat();need(stat.S_ISREG(a.st_mode),'regular byte subject');raw=path.read_bytes();z=path.stat()
 keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')
 need(all(getattr(a,k)==getattr(z,k) for k in keys) and len(raw)==a.st_size,'stable byte subject')
 return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def authenticated(r,declared_json=False):
 need(type(r)is dict and set(r)=={'path','bytes','sha256'} and reference(r['path'])==r,'exact byte reference')
 raw=Path(r['path']).read_bytes();need(len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'],'authenticated bytes')
 return strict(raw) if declared_json else raw

def load(r,name):
 authenticated(r);s=importlib.util.spec_from_file_location(name,r['path']);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def bindings():
 need(reference(D/'BINDINGS.json')['sha256']==BINDINGS_SHA,'frozen BFD retirement bindings')
 b=strict((D/'BINDINGS.json').read_bytes());need(b['scope']==SCOPE and b['runtime_authority'] is None,'source binding is not authority');return b

def validate_retained(b):
 p=authenticated(b['packet'],True);protected=authenticated(b['protected'],True)
 for r in p['source_refs'].values():authenticated(r)
 for r in protected['failed_source_evidence']:authenticated(r)
 refs=p['source_refs'];profile=authenticated(refs['PROFILE.SOURCE-ONLY.json'],True);claim=authenticated(refs['output:claim.json'],True);plan=authenticated(refs['output:plan.json'],True);terminal=authenticated(refs['output:terminal.json'],True);result=authenticated(refs['worker_result'],True)
 need(p['container_id']==b['cid'] and p['container_name']==b['name'] and p['nonce']==b['nonce'],'exact single BFD identity')
 need(claim['native_authority'] is False and claim['pid']==2124454 and claim['grant']==refs['ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'],'actual BFD claim')
 need(terminal['returncode']==0 and terminal['container']==b['cid'] and terminal['default_native_retirement_acceptance'] is False,'actual terminal only')
 need(plan['source_profile']==refs['PROFILE.SOURCE-ONLY.json'] and plan['commands']==profile['exact_commands'] and len(result['commands'])==3,'exact three-command plan/profile')
 for n,(actual,expected) in enumerate(zip(result['commands'],plan['commands'])):
  need(actual['index']==n and actual['returncode']==0 and actual['argv']==expected['argv'] and actual['cwd']==expected['cwd'],'actual command argv/cwd/returncode')
 holder=authenticated(refs['holder:HOLDER.READY.json'],True)['holder'];joined=authenticated(refs['holder:RUNNER.JOINED.json'],True);local=authenticated(refs['holder:BUILD-LOCAL-TERMINAL.json'],True)
 need(holder==local['holder']==dict(path=str(LOCK),pid=2124365,starttime=101427979,device=27,inode=4,fd=3),'actual holder FD3 identity')
 need(joined==dict(pid=2124454,starttime=101432667,returncode=0,joined=True) and local['returncode']==0 and local['joined'] is True and local['container_terminal_or_no_launch'] is True,'positive actual holder/runner terminal')
 parent=authenticated(b['parent_tool_join'],True)
 need(parent['author']=='/root' and parent['decision']=='ROOT_ATTESTS_OBSERVED_ACTUAL_TOOL_SESSION_JOIN' and parent['session_id']==94204 and parent['returncode']==0 and parent['joined'] is True and parent['actual_tool_response']['chunk_id']=='8c21ed' and parent['actual_tool_response']['exit_code']==0,'saved actual Root tool join attestation')
 for r in b['actor_evidence']:authenticated(r)
 return p,protected,profile,claim,plan,terminal

def expected_mounts(p,profile):
 inp=profile['inputs'];rows=[dict(Source=p['output_root']+'/work',Destination='/work',RW=True)]
 rows.extend([dict(Source=inp['source_export_root'],Destination='/src',RW=False),dict(Source=inp['assets_root'],Destination='/candidate',RW=False)])
 rows.extend(dict(Source=r['host_path'],Destination=r['container_path'],RW=False) for r in inp['toolchain_mounts'])
 rows.extend([dict(Source=p['cohort']+'/build_only_worker.py',Destination='/build-only-worker.py',RW=False),dict(Source=p['output_root']+'/plan.json',Destination='/build-only-plan.json',RW=False)])
 return rows

def validate_profile(item,image,b,p,profile,claim,terminal):
 """Disjoint custom profile; no SDK owner-label predicate is removed or reused."""
 need(type(item)is dict and item['Id']==b['cid'] and item['Name']=='/'+b['name'] and item['State']==terminal['state'],'exact fresh stopped ID/name/all state fields')
 st=item['State'];need(st['Status']=='exited' and st['Running'] is False and st['Pid']==0 and st['ExitCode']==0 and not any(st[k] for k in ('Paused','Restarting','OOMKilled','Dead')) and st['Error']=='','normal exit0/Pid0/noOOM')
 image_id=profile['inputs']['image'];need(image['Id']==item['Image']==image_id,'exact immutable OCI image')
 c=item['Config'];h=item['HostConfig'];need(c['Image']==image_id and c['User']=='1000:1000' and c['WorkingDir']=='/work' and c['Entrypoint']==['/usr/bin/python3'] and c['Cmd']==['-I','-B','/build-only-worker.py','/build-only-plan.json'],'exact actual user/entry/command/workdir')
 need(c.get('Labels')==image['Config'].get('Labels') and (c.get('Labels') or {}).get('mckernel.owner') is None and c.get('Env')==image['Config'].get('Env'),'unchanged image labels/env; no fabricated owner label')
 need(c.get('OpenStdin') is False and c.get('Tty') is False and c.get('StdinOnce') is False,'no interactive stdin/tty')
 fixed=dict(ReadonlyRootfs=True,Privileged=False,AutoRemove=False,NetworkMode='none',CpusetCpus='2-5',CpusetMems='',Memory=12<<30,MemorySwap=12<<30,PidsLimit=512,CgroupParent='',PidMode='',IpcMode='private',UTSMode='',UsernsMode='',CpuShares=0,CpuPeriod=0,CpuQuota=0,NanoCpus=0)
 for k,v in fixed.items():need(type(h.get(k))is type(v) and h[k]==v,'exact OCI resource/namespace '+k)
 need(h.get('CapDrop')==['ALL'] and h.get('CapAdd') in (None,[]) and h.get('SecurityOpt')==['no-new-privileges'],'exact reviewed capability/options profile')
 for k in ('Devices','DeviceRequests','DeviceCgroupRules','VolumesFrom','Links','Binds','PortBindings'):
  need(h.get(k) in (None,[],{}),'no extra OCI '+k)
 need(h.get('Tmpfs')=={'/tmp':'rw,nosuid,nodev,size=1073741824,mode=1777'},'exact reviewed tmpfs')
 expected=expected_mounts(p,profile);actual=[]
 for row in item['Mounts']:
  if row.get('Type')=='tmpfs':need(row['Destination']=='/tmp' and row.get('Source','')=='' and row['RW'] is True,'only exact configured /tmp tmpfs');continue
  need(row.get('Type')=='bind' and row.get('Propagation')=='rprivate','exact ordinary bind propagation')
  actual.append({k:row[k] for k in ('Source','Destination','RW')})
 need(sorted(actual,key=lambda x:x['Destination'])==sorted(expected,key=lambda x:x['Destination']),'complete exact OCI source/mount/access map')
 declared=h.get('Mounts');need(type(declared)is list and len(declared)==len(expected),'exact declared OCI bind count')
 for row in declared:
  need(row['Type']=='bind','only declared bind mounts');match=next((x for x in expected if x['Destination']==row['Target']),None)
  need(match is not None and row['Source']==match['Source'] and row.get('ReadOnly',False)==(not match['RW']) and row.get('Consistency','')=='','exact OCI declared mount')
 need(len({r['Destination'] for r in actual})==len(actual) and len({r['Target'] for r in declared})==len(declared),'no duplicate OCI mounts')
 # Reuse original pure argv construction to bind claim to the immutable mount/plan data.
 runner=load(p['source_refs']['run_build_only.py'],'actual_BFD_pure_argv_builder')
 mountrows=[dict(host=r['Source'],target=r['Destination'],readonly=not r['RW']) for r in expected if r['Destination']!='/work']
 need(runner.docker_argv(profile,b['name'],mountrows,Path(p['output_root']))==claim['argv'],'actual Docker claim argv unchanged')
 return True

def validate_inventory(raw,b,present):
 rows=[strict(line) for line in raw.splitlines() if line];seen=set();found=[]
 for r in rows:
  need(type(r)is dict and re.fullmatch('[0-9a-f]{64}',r.get('ID','')) and r['ID'] not in seen and type(r.get('Names'))is str and type(r.get('Labels'))is str and r.get('State') in ('created','restarting','running','removing','paused','exited','dead'),'complete ordinary container inventory shape')
  seen.add(r['ID']);need(r['State'] not in ('running','restarting','paused','removing'),'no active container/heavy overlap')
  if r['ID']==b['cid'] or r['Names']==b['name']:found.append(r)
 need((len(found)==1 and found[0]['ID']==b['cid'] and found[0]['Names']==b['name'] and found[0]['State']=='exited') if present else not found,'exact BFD presence/absence')
 return rows

def process_source(normal,p):
 code=normal.PROC_CODE
 edits={"rows=[]; publishers=[]; found=False":"rows=[]; publishers=[]; groups=[]; found=False","rows.append([pid,ppid,str(start)])":"rows.append([pid,ppid,str(start)]); groups.append([pid,ppid,str(start),int(fields[2]),int(fields[3])])","return sorted(rows),publishers":"return sorted(rows),publishers,sorted(groups)","first,pubs1=snapshot(); second,pubs2=snapshot()":"first,pubs1,groups1=snapshot(); second,pubs2,groups2=snapshot()","'snapshots':[first,second]":"'snapshots':[first,second], 'groups':[groups1,groups2]"}
 for old,new in edits.items():need(code.count(old)==1,'unchanged full census anchor');code=code.replace(old,new)
 anchor='    for arg in argv:\n';need(code.count(anchor)==1,'exact publisher extension anchor')
 paths=[p['cohort']+'/run_build_only.py',p['cohort']+'/hold_and_run_build_only.py',str(SELF)]
 # Self is excluded by unchanged caller predicate; another cleanup at same source is a publisher.
 code=code.replace(anchor,'    if any(path in argv for path in '+repr(paths)+'): return True\n'+anchor)
 return code

def validate_process(report,normal,b,challenge,caller,command_pids):
 need(type(report)is dict and 'groups' in report,'complete group-extended normal census')
 base={k:v for k,v in report.items() if k!='groups'};normal.BOOT_ID=b['boot'];normal.OWNER_PID=2124365;normal.WAITER_PIDS=tuple(sorted({a['pid'] for a in b['prior_actors']+b['new_known_actors']}|set(command_pids)))
 normal.validate_process_report(base,challenge,caller) # Every unchanged normal predicate runs.
 need(len(report['groups'])==2,'two full group snapshots')
 forbidden=set(normal.WAITER_PIDS)|{2124454}
 for basic,groups in zip(report['snapshots'],report['groups']):
  need(type(groups)is list and len(groups)==len(basic),'complete group rows')
  need([r[:3] for r in groups]==basic,'same full process/group snapshots')
  for row in groups:
   need(len(row)==5 and all(type(row[i])is int and row[i]>=0 for i in (0,1,3,4)) and row[2].isdigit(),'typed process/group/session row')
   need(row[0] not in forbidden and row[3] not in forbidden and row[4] not in forbidden,'all known actor/client PID/groups/sessions absent')
 return True

def validate_result(value,b):
 """Pure authenticated success consumer for the separate postjoin observer."""
 need(value['schema']=='mckernel.bfd-default-build.stopped-container-retirement.result.v1' and value['status']=='PASS_EXACT_BFD_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT' and value['scope']==SCOPE,'exact BFD stopped retirement result schema/status')
 need(value['cid']==b['cid'] and value['nonce']==b['nonce'] and value['container_absent'] is True and value['signals_sent']==0 and value['records_released']==[],'exact once stopped-CID retirement result')
 need(value['bindings']==reference(D/'BINDINGS.json') and value['protected_originals']==b['protected'] and value['native_acceptance'] is False and value['fullfile_acceptance'] is False and value['parent_positive_join_and_fresh_current_acceptance_required'] is True,'result has exact source/data and remains pending postjoin')
 authenticated(value['release'])
 receipts=[authenticated(r,True) for r in value['command_receipts']]
 need(receipts and all(r['positive_wait4'] is True and r['wait4_pid']==r['pid'] and type(r['birth'])is int and r['birth']>0 and r['returncode']==0 and r['wait4_status']==0 and r['group_absent'] is True and not r['group_members'] and r['streams_closed'] is True and r['client_retirement_unproven'] is False and r['signals_sent']==0 for r in receipts),'all exact command birth/wait4/group/stream proofs')
 actor=value['cleanup_actor'];need(type(actor['pid'])is int and actor['pid']>0 and type(actor['birth'])is int and actor['birth']>0,'exact cleanup actor PID/birth')
 packet,protected,profile,claim,plan,terminal=validate_retained(b);normal=load(b['normal'],'pure_result_normal_predicates');code=process_source(normal,packet)
 roles=['PROC',['ps','-a','--no-trunc','--format','{{json .}}'],['inspect','--type','container',b['cid']],['image','inspect',profile['inputs']['image']],['logs','--',b['cid']],'PROC',['ps','-a','--no-trunc','--format','{{json .}}'],['inspect','--type','container',b['cid']],['image','inspect',profile['inputs']['image']],['rm','--',b['cid']],['ps','--all','--quiet','--no-trunc','--filter','id='+b['cid']],['ps','--all','--quiet','--no-trunc','--filter','name=^/'+b['name']+'$'],'PROC',['ps','-a','--no-trunc','--format','{{json .}}']]
 need(len(receipts)==len(roles),'complete exact executor command sequence')
 for r,role in zip(receipts,roles):
  argv=r['argv']
  if role=='PROC':need(len(argv)==10 and argv[:7]==['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B','-c',code] and re.fullmatch('[0-9a-f]{32}',argv[7]) and argv[8:]==[str(actor['pid']),str(actor['birth'])],'exact full census caller/code argv')
  else:need(argv==PREFIX+role,'exact ordered stopped-container command argv')
 removes=[r for r in receipts if r['argv']==PREFIX+['rm','--',b['cid']]]
 need(len(removes)==1,'exactly one rm command receipt')
 for r in receipts:
  need(set(r['raw'])=={'stdout','stderr','status.json'},'complete immutable raw command capture')
  for rawref in r['raw'].values():authenticated(rawref)
  status=authenticated(r['raw']['status.json'],True);need(status['state']=='exited' and status['pid']==r['pid'] and status['exit_code']==r['returncode'] and status['argv']==r['argv'],'same exact raw command status')
  need(all(type(r[k])in (int,float) and math.isfinite(r[k]) and r[k]>=0 for k in ('wall_seconds','user_cpu_seconds','system_cpu_seconds','peak_rss_kib')),'finite measured command resource accounting')
 proofs=[authenticated(r,True) for r in value['proofs']]
 need([x['label'] for x in proofs]==['PREINSPECT-1','PREINSPECT-2','POSTPROOF'] and [x['present'] for x in proofs]==[True,True,False],'exact preinspect/commit/postproof chain')
 for proof,index,end in zip(proofs,[0,5,12],[4,9,14]):
  need(proof['schema']=='mckernel.bfd-default-build.retirement-proof.v1' and proof['cid']==b['cid'] and proof['nonce']==b['nonce'] and proof['command_receipts']==value['command_receipts'][:end],'same exact proof identity/cumulative command closure')
  process_raw=authenticated(receipts[index]['raw']['stdout']);need(strict(process_raw)==proof['process'],'actual raw full process proof')
  validate_process(proof['process'],normal,b,receipts[index]['argv'][7],[actor['pid'],str(actor['birth'])],[r['pid'] for r in receipts[:index]])
  inventory_raw=authenticated(receipts[index+1]['raw']['stdout']);need(validate_inventory(inventory_raw,b,proof['present'])==proof['inventory'],'actual raw complete container proof')
  if proof['present']:
   need(strict(authenticated(receipts[index+2]['raw']['stdout']))==proof['container'] and strict(authenticated(receipts[index+3]['raw']['stdout']))==proof['image'],'actual raw container/image profile proof')
   need(len(proof['container'])==len(proof['image'])==1,'one exact OCI profile');validate_profile(proof['container'][0],proof['image'][0],b,packet,profile,claim,terminal)
  else:need(proof['container'] is None and proof['image'] is None,'postproof is exact absence, never stale inspect')
  need(len(proof['clocks'])==3 and all(type(x)in (int,float) and math.isfinite(x) and 0<=x<c for x,c in zip(proof['clocks'],b['cutoffs'])),'proof within current earliest clamps')
 need(0<=receipts[9]['started_epoch']-proofs[1]['clocks'][0]<=120,'actual rm followed fresh preproof')
 need(authenticated(receipts[9]['raw']['stdout']).strip()==b['cid'].encode() and authenticated(receipts[9]['raw']['stderr'])==b'','exact raw rm response')
 for index in (10,11):need(authenticated(receipts[index]['raw']['stdout'])==authenticated(receipts[index]['raw']['stderr'])==b'','exact raw CID/name absence')
 return receipts

class Wait4Child:
 """Adapt existing transport wait API, retaining exact positive wait4 accounting."""
 def __init__(self,process,capture,clock=time,wait4=os.wait4):
  self.process=process;self.pid=process.pid;self.capture=Path(capture);self.clock=clock;self.wait4=wait4;self.returncode=None
  self.started=clock.monotonic();raw=(Path('/proc')/str(self.pid)/'stat').read_bytes();fields=raw.rpartition(b') ')[2].split()
  need(len(fields)>=20,'new command birth unavailable');self.birth=int(fields[19]);self.record=dict(pid=self.pid,birth=self.birth,process_group=self.pid,started_epoch=clock.time(),started_monotonic=self.started,positive_wait4=False)
 def reap(self):
  if self.returncode is not None:return self.returncode
  pid,status,usage=self.wait4(self.pid,os.WNOHANG)
  if pid:
   need(pid==self.pid,'exact direct wait4 child');self.returncode=os.waitstatus_to_exitcode(status);self.process.returncode=self.returncode
   self.record.update(positive_wait4=True,wait4_pid=pid,wait4_status=status,returncode=self.returncode,finished_epoch=self.clock.time(),wall_seconds=self.clock.monotonic()-self.started,user_cpu_seconds=usage.ru_utime,system_cpu_seconds=usage.ru_stime,peak_rss_kib=usage.ru_maxrss)
  return self.returncode
 def poll(self):return self.reap()
 def wait(self,timeout=None):
  end=None if timeout is None else self.clock.monotonic()+timeout
  while True:
   code=self.reap()
   if code is not None:return code
   if end is not None and self.clock.monotonic()>=end:raise subprocess.TimeoutExpired('exact captured command',timeout)
   time.sleep(.005)


def transport(b):
 """AST reuse of existing capture transport; failure handler sends no signals."""
 raw=authenticated(b['backend']);tree=ast.parse(raw);names={'docker_env','atomic','digest','Docker'}
 nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
 need(len(nodes)==4,'four exact existing transport units')
 ns=dict(Path=Path,json=json,os=os,uuid=uuid,signal=signal,time=time,subprocess=subprocess,hashlib=hashlib)
 for n in tree.body:
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id in ('ENV','SUDO_DOCKER_PREFIX') for t in n.targets):exec(compile(ast.Module(body=[n],type_ignores=[]),b['backend']['path'],'exec'),ns)
 exec(compile(ast.Module(body=nodes,type_ignores=[]),b['backend']['path'],'exec'),ns)
 Base=ns['Docker']
 class Commands(Base):
  def __init__(self,out,stop):
   super().__init__(out/'commands.log',stop,sudo=True);self.command_prefix=();self.children=[];self.receipts=[];self.out=out
   self.before_popen=None;self.raw_child=None;self.unresolved_spawn=None;self.current_failed=False;self.group_scan_failed=False
   def popen(argv,**kwargs):
    capture=Path(kwargs['stdout'].name).parent
    # Base.call has completed starting-status/log fsync and opened both captures.
    # Caller hook does all further admission I/O, then its final clocks; there
    # is no application I/O between that last check and this actual Popen.
    if self.before_popen is not None:self.before_popen(argv)
    child=subprocess.Popen(argv,**kwargs)
    # A successful raw spawn owns custody BEFORE birth/wrapper/receipt work.
    self.raw_child=child;self.client_retirement_unproven=True
    self.unresolved_spawn=dict(pid=child.pid,birth=None,argv=argv,capture=str(capture),successful_Popen=True)
    wrapped=Wait4Child(child,capture);self.unresolved_spawn['birth']=wrapped.record['birth'];wrapped.streams=(kwargs['stdout'],kwargs['stderr']);self.children.append(wrapped)
    # Keep the raw child + uncertainty latch until its durable JOIN is sealed.
    return wrapped
   ns['subprocess']=types.SimpleNamespace(Popen=popen,TimeoutExpired=subprocess.TimeoutExpired,CompletedProcess=subprocess.CompletedProcess)
  def _surviving_group_members(self,pgid):
   members=[]
   for path in Path('/proc').glob('[0-9]*/stat'):
    try:
     fields=path.read_text().rsplit(')',1)[1].split();need(len(fields)>=20,'complete new-client group stat')
     if int(fields[2])==pgid or int(fields[3])==pgid:members.append(int(path.parent.name))
    except FileNotFoundError:continue
    except (PermissionError,ValueError,IndexError,Refusal):self.group_scan_failed=True;self.client_retirement_unproven=True
   return members
  def _record_client_exit(self,code,status):
   Base._record_client_exit(self,code,status)
   if code is None or code<0:self.current_failed=True;self.client_retirement_unproven=True;status['client_retirement_unproven']=True
  def _retire_client(self,process,status):
   # Deliberately replace inherited TERM/KILL with uncertainty retention only.
   self.current_failed=True;self.client_retirement_unproven=True;status['no_signals_sent']=True
   if process is not None:status['unresolved_client_pid']=process.pid;process.poll()
  def exact(self,argv,timeout=30,check=True):
   prior=len(self.children);prior_uncertain=self.client_retirement_unproven
   need(not prior_uncertain and self.raw_child is None,'prior command uncertainty cannot be cleared by a later child')
   self.current_failed=False;self.group_scan_failed=False
   try:return self.call(argv,timeout=timeout,check=check)
   finally:
    if len(self.children)>prior:
     child=self.children[-1];members=self._surviving_group_members(child.pid);r=dict(child.record)
     r.update(argv=argv,group_members=members,group_absent=not members and not self.group_scan_failed,streams_closed=all(f.closed for f in child.streams),signals_sent=0)
     unproven=prior_uncertain or self.current_failed or self.group_scan_failed or not r['positive_wait4'] or bool(members) or not r['streams_closed']
     r['client_retirement_unproven']=unproven
     r['raw']={name:reference(child.capture/name) for name in ('stdout','stderr','status.json')}
     ns['atomic'](child.capture/'JOIN-WAIT4.json',r)
     for path in (child.capture,self.log):
      fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
      try:os.fsync(fd)
      finally:os.close(fd)
     self.receipts.append(reference(child.capture/'JOIN-WAIT4.json'))
     if not unproven:self.raw_child=None;self.unresolved_spawn=None;self.client_retirement_unproven=False
     else:self.client_retirement_unproven=True
    elif self.raw_child is not None:
     # Birth/wrapper construction failed after a successful raw spawn. The
     # inherited status may have no pid; preserve this honest gap separately.
     self.client_retirement_unproven=True
     try:write_new(Path(self.unresolved_spawn['capture'])/'UNWRAPPED-SPAWN.json',dict(scope=SCOPE,unknown_birth=True,signals_sent=0,**self.unresolved_spawn))
     except BaseException:pass

 return Commands,ns

def write_new(path,value):
 raw=canonical(value);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o400)
 try:
  view=memoryview(raw)
  while view:n=os.write(fd,view);need(n>0,'complete metadata write');view=view[n:]
  os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
 try:os.fsync(fd)
 finally:os.close(fd)
 return reference(path)

def validate_release(r,b,files):
 need(r['schema']=='mckernel.bfd-default-build.stopped-container-retirement.release.v1' and r['author']=='/root' and r['decision']=='GRANT_ONE_EXACT_STOPPED_BFD_CONTAINER_RETIREMENT' and type(r['maximum_invocations'])is int and r['maximum_invocations']==1,'exact Root one-shot stopped-container release')
 need(r['bindings']==reference(D/'BINDINGS.json') and r['files']==files and r['parent_tool_join']==b['parent_tool_join'],'exact consumed source/data/actual join closure')
 need(r['cid']==b['cid'] and r['nonce']==b['nonce'] and r['signals_allowed']==0 and r['records_released']==[],'exact stopped CID only; no signals/record release')
 need(r['cutoffs']==b['cutoffs'] and r['credit_run_id']=='7f4af94a83b14cc08f97401f5891d965' and r['credit_ceiling']=='57774.852125' and r['minimum_cumulative_spent']=='22812.3311','immutable clock/credit limits')
 need(r['Root_attests_no_unlisted_intervening_operation'] is True and r['actual_account_identity_operation_admission_accepted'] is True,'Root fresh operation/identity/admission attestations')
 ledger=authenticated(r['current_ledger'],True);prior=authenticated(authenticated(b['packet'],True)['source_refs']['PROFILE.SOURCE-ONLY.json'],True)['actual_root_ledger'];old=authenticated(prior,True)
 need(ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True and ledger['consumed_nonces']==old['consumed_nonces']+[b['nonce']] and ledger['current_physical_clearance_pending'] is True and ledger['current_native_operation']==old['current_native_operation'],'actual typed consumed-build boundary; old free remains historical')
 build=ledger.get('bfd_default_build',{});packet=authenticated(b['packet'],True);expected_refs=packet['source_refs']
 need(build.get('operation')=='BFD_CURRENT_DEFAULT_THREE_COMMAND_BUILD_ONLY_NOT_NATIVE' and build.get('nonce')==b['nonce'] and build.get('container_id')==b['cid'],'typed exact ordinary BFD ledger extension')
 for key,sourcekey in [('profile','PROFILE.SOURCE-ONLY.json'),('actual_grant','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json'),('container_claim','output:claim.json'),('plan','output:plan.json'),('worker_result','worker_result'),('terminal','output:terminal.json'),('holder_ready','holder:HOLDER.READY.json'),('runner_join','holder:RUNNER.JOINED.json'),('holder_local_terminal','holder:BUILD-LOCAL-TERMINAL.json')]:need(build.get(key)==expected_refs[sourcekey],'typed exact BFD ledger '+key)
 need(build.get('actual_holder_tool_join_receipt')==b['parent_tool_join'],'actual saved tool join in current ledger')
 source=authenticated(r['source_review'],True)
 need(source['decision']=='PASS_SOURCE' and source['independent'] is True and source['implementation_ownership'] is False and source['files']==files and source['bindings']==r['bindings'] and source['reviewer'] not in ('/root','/root/bfd_route') and source['source_checkpoint']==r['source_checkpoint'],'independent exact source/data review')
 need(re.fullmatch('[a-f0-9]{40}',r['source_checkpoint']) and r['fetched_source_verified'] is True,'actual fetched source checkpoint')
 publication=authenticated(r['source_publication'],True);need(publication['status'].startswith('PASS_FETCHED') and publication['commit']==r['source_checkpoint'] and publication['runtime_authority'] is None,'actual fetched publication receipt')
 published={row['actual']['path']:row['actual'] for row in publication['rows']}
 for row in files.values():need(published.get(row['path'])==row,'exact published runtime closure')
 execution=authenticated(r['execution_review'],True);payload={k:v for k,v in r.items() if k!='execution_review'}
 need(execution['decision']=='PASS_EXECUTION' and execution['independent'] is True and execution['implementation_ownership'] is False and execution['reviewer'] not in ('/root','/root/bfd_route') and execution['release_payload_sha256']==hashlib.sha256(canonical(payload)).hexdigest(),'independent exact execution review')
 out=Path(r['output']);need(out.parent==D and re.fullmatch('actual-retirement-[A-Za-z0-9_-]+',out.name) and not os.path.lexists(out),'fresh confined retirement metadata only')
 return out

class Actual:
 def __init__(self,b,r,out,stop):
  self.b=b;self.r=r;self.out=out;self.stop=stop;self.m=load(b['primitive'],'unchanged_normal_lock_primitive');self.normal=load(b['normal'],'unchanged_normal_process_predicates');self.guard=load(b['guardian'],'actual_restart_guard_source');self.m.LOCK=LOCK;self.m.proc_bytes=self.proc_bytes
  self.p,self.protected,self.profile,self.claim,self.plan,self.terminal=validate_retained(b);self.fd=None;self.mutated=False;self.command_started=False;self.proofs=[];self.rm_claimed=False;self.rm_invoked=False
  cls,self.ns=transport(b);self.commands=cls(out,stop);self.commands.before_popen=self.before_spawn
 def proc_bytes(self,path,maximum=1<<20):
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
  try:
   data=bytearray()
   while True:
    raw=os.read(fd,min(65536,maximum+1-len(data)))
    if not raw:return bytes(data)
    data.extend(raw);need(len(data)<=maximum,'bounded proc bytes')
  finally:os.close(fd)
 def acquire(self):self.fd=self.m.acquire_root_lock()
 def safe(self):
  self.stop.check();now=self.guard.guard();need(all(a<c for a,c in zip(now,self.b['cutoffs'])),'earliest current control cutoff')
  need(self.fd is not None,'exclusive cleanup custody');s=os.fstat(self.fd);n=LOCK.lstat()
  need(stat.S_ISREG(s.st_mode) and (s.st_dev,s.st_ino,s.st_uid,s.st_gid,stat.S_IMODE(s.st_mode),s.st_nlink,s.st_size)==(27,4,0,0,0o644,1,0) and (n.st_dev,n.st_ino)==(27,4),'same permanent27:4 opened and named inode')
  self.m.require_lock_holder(os.getpid())
  validate_retained(self.b)
  for row in self.protected['records']:
   if row['kind']=='file':authenticated({k:row[k] for k in ('path','bytes','sha256')})
   else:need(Path(row['path']).is_symlink() and str(Path(row['path']).readlink())==row['target'],'retained symlink unchanged')
  for key,floor in [('/home/holden/mckernel',16<<30),('/home/holden/mckernel-work/scratch',12<<30)]:
   v=os.statvfs(key);need(v.f_bavail*v.f_frsize>=floor,'unchanged storage floor')
  memory={line.split(':',1)[0]:line.split(':',1)[1].strip().split()[0] for line in self.proc_bytes('/proc/meminfo').decode().splitlines() if ':' in line}
  need(int(memory['MemAvailable'])*1024>=4<<30,'preserved4GiB host memory reserve')
  cg={}
  for key,expected in [('cpu/mckernel-dev/cpu.cfs_period_us','100000'),('cpu/mckernel-dev/cpu.cfs_quota_us','400000'),('memory/mckernel-dev/memory.limit_in_bytes',str(12<<30)),('pids/mckernel-dev/pids.max','512'),('pids/mckernel-dev/pids.current','0')]:
   value=self.proc_bytes('/sys/fs/cgroup/'+key).decode().strip();need(value==expected,'unchanged host cgroup '+key);cg[key]=value
  # Stopped-container cgroups may already be absent. Existing exact candidates
  # must have zero tasks; the complete process census also rules out live clients.
  container_cgroups={}
  for controller in ('cpu','memory','pids'):
   for suffix in ('docker/'+self.b['cid'],'system.slice/docker-'+self.b['cid']+'.scope'):
    path=Path('/sys/fs/cgroup')/controller/suffix
    if path.exists():
     need(not path.is_symlink() and path.is_dir(),'ordinary exact Docker cgroup')
     tasks=self.proc_bytes(path/'tasks').decode().strip();need(tasks=='','stopped-container cgroup has no tasks');container_cgroups[str(path)]=[]
    else:container_cgroups[str(path)]=None
  return dict(clocks=now,MemAvailable_bytes=int(memory['MemAvailable'])*1024,cgroup=cg,container_cgroups=container_cgroups,mutex=dict(device=27,inode=4,holder=os.getpid(),fd=self.fd))
 def before_spawn(self,argv):
  # This callback is invoked by the reused transport after all its capture
  # open/status/log/fsync work. All our source/guard/protected/proof I/O also
  # precedes the final direct clock/stop test below.
  self.safe()
  preproof=None
  if argv==PREFIX+['rm','--',self.b['cid']]:
   need(self.rm_claimed and self.rm_invoked,'one exact preclaimed removal')
   claim=authenticated(self.rm_claim_reference,True);preproof=authenticated(self.rm_preproof_reference,True)
   need(claim['preproof']==self.rm_preproof_reference and preproof['present'] is True and preproof['label']=='PREINSPECT-2','exact durable precommit proof')
  self.guard.guard() # All actual account/identity/guardian I/O finishes here.
  self.stop.check()
  now=[time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
  need(all(a<c for a,c in zip(now,self.b['cutoffs'])),'final pre-Popen earliest cutoff')
  if preproof is not None:need(0<=now[0]-preproof['clocks'][0]<=120,'final pre-Popen original120s freshness')
  # Return directly to Popen: no application read/write/fsync follows this test.
 def call(self,args,check=True,root_process=False):
  if root_process:
   need(len(args)==5 and args[0]=='-c' and args[1]==process_source(self.normal,self.p) and re.fullmatch('[0-9a-f]{32}',args[2]) and args[3:]==[str(os.getpid()),self.m.proc_stat(os.getpid())[19]],'only exact existing full-process census command')
  else:
   allowed=[['ps','-a','--no-trunc','--format','{{json .}}'],['inspect','--type','container',self.b['cid']],['image','inspect',self.profile['inputs']['image']],['logs','--',self.b['cid']],['rm','--',self.b['cid']]]
   allowed.extend([['ps','--all','--quiet','--no-trunc','--filter',q] for q in ('id='+self.b['cid'],'name=^/'+self.b['name']+'$')])
   need(args in allowed,'only exact finite BFD retirement command argv')
   if args[0]=='rm':
    need(self.rm_claimed and not self.rm_invoked,'exact once-claimed stopped CID removal only');self.rm_invoked=True
  self.safe();self.command_started=True
  argv=(['/usr/bin/sudo','-A','/usr/bin/python3','-I','-B',*args] if root_process else PREFIX+args)
  result=self.commands.exact(argv,30,check=check);need(not self.commands.client_retirement_unproven,'all new command clients positively retired without signals');return result
 def census(self,label,present):
  safety=self.safe();challenge=uuid.uuid4().hex;caller=[os.getpid(),self.m.proc_stat(os.getpid())[19]]
  prior_pids=[self.commands.children[i].pid for i in range(len(self.commands.children))]
  process=self.call(['-c',process_source(self.normal,self.p),challenge,str(caller[0]),caller[1]],root_process=True)
  report=strict(process.stdout);validate_process(report,self.normal,self.b,challenge,caller,prior_pids)
  inventory=self.call(['ps','-a','--no-trunc','--format','{{json .}}']);rows=validate_inventory(inventory.stdout,self.b,present)
  inspected=None;image=None
  if present:
   inspected=strict(self.call(['inspect','--type','container',self.b['cid']]).stdout);image=strict(self.call(['image','inspect',self.profile['inputs']['image']]).stdout)
   need(type(inspected)is list and len(inspected)==1 and type(image)is list and len(image)==1,'one exact container/image inspect')
   validate_profile(inspected[0],image[0],self.b,self.p,self.profile,self.claim,self.terminal)
  proof=dict(schema='mckernel.bfd-default-build.retirement-proof.v1',label=label,scope=SCOPE,cid=self.b['cid'],nonce=self.b['nonce'],present=present,safety=safety,process=report,inventory=rows,container=inspected,image=image,command_receipts=list(self.commands.receipts),clocks=self.safe()['clocks'])
  r=write_new(self.out/(label+'.json'),proof);self.proofs.append(r);return proof,r
 def logs(self):
  result=self.call(['logs','--',self.b['cid']]);refs=self.p['source_refs']
  need(result.stdout.encode()==authenticated(refs['output:container.stdout']) and result.stderr.encode()==authenticated(refs['output:container.stderr']),'exact retained stopped-container log streams')
 def claim_once(self,proof):
  now=self.safe()['clocks'];need(0<=now[0]-proof['clocks'][0]<=120,'fresh exact precommit proof within120s')
  self.rm_preproof_reference=self.proofs[-1]
  self.rm_claim_reference=write_new(self.out/'RM-ONCE-CLAIM.json',dict(scope=SCOPE,cid=self.b['cid'],nonce=self.b['nonce'],release=self.r['_reference'],preproof=self.rm_preproof_reference,argv=PREFIX+['rm','--',self.b['cid']],clocks=now))
  now=self.safe()['clocks'];need(0<=now[0]-proof['clocks'][0]<=120,'postfsync precommit proof within120s');self.rm_claimed=True
 def remove(self):
  self.mutated=True;result=self.call(['rm','--',self.b['cid']]);need(result.returncode==0 and result.stdout.strip()==self.b['cid'] and result.stderr=='','exact stopped CID removed once')
 def absence(self):
  for query in ('id='+self.b['cid'],'name=^/'+self.b['name']+'$'):
   r=self.call(['ps','--all','--quiet','--no-trunc','--filter',query]);need(r.stdout=='' and r.stderr=='','exact CID/name absent')
 def finish(self):
  final=self.safe();receipts=[authenticated(r,True) for r in self.commands.receipts]
  need(receipts and all(x['positive_wait4'] and x['returncode']==0 and x['group_absent'] and x['streams_closed'] and not x['client_retirement_unproven'] and x['signals_sent']==0 for x in receipts),'every exact command PID/birth/wait4/group/stream accounting')
  value=dict(schema='mckernel.bfd-default-build.stopped-container-retirement.result.v1',status='PASS_EXACT_BFD_STOPPED_CONTAINER_RETIRED_PENDING_POSTJOIN_CURRENT',scope=SCOPE,cid=self.b['cid'],nonce=self.b['nonce'],container_absent=True,signals_sent=0,records_released=[],protected_originals=self.b['protected'],release=self.r['_reference'],bindings=reference(D/'BINDINGS.json'),proofs=self.proofs,command_receipts=self.commands.receipts,cleanup_actor=dict(pid=os.getpid(),birth=int(self.m.proc_stat(os.getpid())[19]),mutex_fd=self.fd),final_safety=final,own_fd_closed_only_after_result_on_normal_return=True,parent_positive_join_and_fresh_current_acceptance_required=True,native_acceptance=False,fullfile_acceptance=False,original_Docker_actor_gaps=self.b['actor_gaps'])
  return write_new(self.out/'RESULT.json',value)
 def close(self):
  if self.fd is not None:os.close(self.fd);self.fd=None
 def uncertain(self,error):
  try:write_new(self.out/'UNCERTAIN.json',dict(scope=SCOPE,error=repr(error),pid=os.getpid(),birth=self.m.proc_stat(os.getpid())[19],permanent_mutex=[27,4],commit_attempted=self.mutated,unknown_successful_spawn=self.commands.unresolved_spawn,commands=self.commands.receipts,signals_sent=0,automatic_replay=False))
  except BaseException:pass
  self.m.QUARANTINE=self.out/'QUARANTINE.json';self.m.quarantine_hold(self.fd)

def transaction(ops):
 """Same real order exercised by pure substituted-effect tests."""
 ops.acquire();ops.safe();ops.census('PREINSPECT-1',True);ops.logs();proof,_=ops.census('PREINSPECT-2',True)
 ops.claim_once(proof);ops.remove();ops.absence();ops.census('POSTPROOF',False);return ops.finish()

def must_retain_custody(ops):
 return ops is not None and (ops.mutated or ops.commands.client_retirement_unproven or ops.commands.raw_child is not None)

class Stop:
 def __init__(self):self.requested=[]
 def receive(self,number,frame):self.requested.append(number)
 def check(self):need(not self.requested,'new external stop; no subsequent command')

def main():
 parser=argparse.ArgumentParser(description=__doc__,allow_abbrev=False);parser.add_argument('--release',type=Path,required=True);parser.add_argument('--release-sha256',required=True);parser.add_argument('--execute',action='store_true');a=parser.parse_args();need(a.execute,'explicit independently released execution only')
 need((os.getuid(),os.geteuid(),os.getgid(),os.getegid())==(1000,1000,1000,1000) and os.sched_getaffinity(0)=={0},'ordinary UID1000/CPU0 one-job adapter')
 for kind,wanted in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:need(resource.getrlimit(kind)==(wanted,wanted),'exact reviewed execution rlimit')
 b=bindings();validate_retained(b);rr=reference(a.release);need(rr['sha256']==a.release_sha256,'exact actual release bytes');r=authenticated(rr,True)
 files=dict(executor=reference(SELF),bindings=reference(D/'BINDINGS.json'))
 files.update({k:b[k] for k in ('primitive','normal','backend','guardian','prior_observer','packet','protected')})
 out=validate_release(r,b,files);r['_reference']=rr;stop=Stop();previous={}
 for number in (signal.SIGHUP,signal.SIGINT,signal.SIGTERM,signal.SIGQUIT):previous[number]=signal.signal(number,stop.receive)
 out.mkdir(mode=0o700);ops=None;complete=False
 try:
  ops=Actual(b,r,out,stop);write_new(out/'STARTED.json',dict(scope=SCOPE,pid=os.getpid(),birth=int(ops.m.proc_stat(os.getpid())[19]),release=rr,bindings=files['bindings']))
  result=transaction(ops);complete=True;print(json.dumps(dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=result)));return 0
 except BaseException as exc:
  if must_retain_custody(ops):ops.uncertain(exc)
  raise
 finally:
  if ops is not None and (complete or not must_retain_custody(ops)):ops.close()
  for number,handler in previous.items():signal.signal(number,handler)

if __name__=='__main__':raise SystemExit(main())
