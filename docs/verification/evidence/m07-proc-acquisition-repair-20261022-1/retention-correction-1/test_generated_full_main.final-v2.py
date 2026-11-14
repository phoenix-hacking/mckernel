"""Full actual-main fixture. Functional OS/Rust migration only; no security testing.
Substitutions: typed finite fixture DATA/paths, fixture mutex synthetic dev/inode27:4 (inside diagnosticdir), diagnosticdir UID/GID0,
root UID/resource calls, boot read, process-read PROC_CODE, fixed subprocess
Docker/findmnt responses. No receipt, case, descriptor, inventory, draft or
serialization oracle is mocked. No cleanup, root command or Docker is executed.
"""
from pathlib import Path
import ast,contextlib,copy,fcntl,hashlib,importlib.util,io,json,os,stat,subprocess,types
from unittest.mock import patch
D=Path(__file__).parent
G=D/'coupled/bound-terminal-proc-v2-source-4'
ENGINE=G/'cleanup_pass_image.py'
PRODUCTION_CASE_SHA='2fddb9c8b56efe95c90ed154eca97fb5673f9e8f36bc0ab033f52322883f646c'
EXPECTED_PATH_COUNT=88
EXPECTED_ROLE_COUNT=97
def sha(b):return hashlib.sha256(b).hexdigest()
def canon(v):return json.dumps(v,sort_keys=True,separators=(',',':')).encode()
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

class RetainedAttempt:
 def __init__(self,label):self.label=label;self.path=D/('retained-fixture-'+label+'-final-proc-v2-4');self.stage='new'
 def record(self,stage,**values):
  self.stage=stage;path=self.path/('stage-%02d.json'%len(list(self.path.glob('stage-*.json'))))
  with path.open('x') as out:json.dump(dict(label=self.label,stage=stage,location=str(self.path),**values),out,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
 def __enter__(self):self.path.mkdir(mode=0o700);self.record('attempt-created');return self
 def __exit__(self,kind,error,tb):
  if error is not None:self.record('UNEXPECTED_FAILURE',previous_stage=self.stage,error_type=kind.__name__,error=str(error))
  return False

def test(label,negative=None):
 with RetainedAttempt(label) as attempt:
  tmp=str(attempt.path)
  root=Path(tmp);prep=root/'diagnosticdir';prep.mkdir(mode=0o700);diagnosticdir=prep;ns=root/'namespace';ns.mkdir(mode=0o700)
  output=ns/'owner-work';evidence=ns/'owner-evidence'
  for p in (output,evidence):p.mkdir(mode=0o700)
  capture=root/'guard-capture';capture.mkdir(mode=0o700)
  observer_output=prep/'root-observation-fixture-full-main-1'
  lock=diagnosticdir/'mutex';lock.touch(mode=0o644);lock.chmod(0o644)
  m=load(ENGINE,'fixture_engine_data');m.ROOT=root;m.NAMESPACE=ns;m.OUTPUT=output;m.EVIDENCE=evidence;m.ATTEMPT=ns/'common';m.SHARED=root/'shared';m.LEASE=ns/'lease';m.REQUEST=ns/'request';m.TERMINAL=evidence/'owner';m.ROOT_LOCK=lock
  m.ARCHIVE_NAMES=('common.archive','shared.archive');m.PLAN=root/'plan';m.JOURNAL=root/'journal';m.CAPTURE=root/'logcapture';m.QUARANTINE=root/'quarantine';m.MUTEX=root/'txmutex'
  m.NAMESPACE_ANCESTRY=m.namespace_ancestry();s=ns.stat();m.NAMESPACE_BINDING=dict(device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)
  source=root/'materialized';source.mkdir(mode=0o700);backup=root/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup';backup.mkdir(mode=0o700)
  source_id=dict(path=str(source),dev=source.stat().st_dev,inode=source.stat().st_ino,uid=1000,gid=1000,mode=0o700,file_type=stat.S_IFDIR)
  source_binding=dict(candidate_identity_scope='base_git_commit_only',candidate_sha=m.IMAGE_CANDIDATE,source_root=str(source),source_identity=source_id,source_derivative_sha256='a'*64,materialization_sha256='b'*64)
  raw=(G/'PASS-CASE-STATIC.json').read_bytes();assert sha(raw)==PRODUCTION_CASE_SHA;original=json.loads(raw);assert original['finite_unique_path_count']==EXPECTED_PATH_COUNT and original['finite_role_count']==EXPECTED_ROLE_COUNT;case=copy.deepcopy(original);target=case['target'];pids=tuple(400+i for i in range(8));boot='fixture-boot'
  mapping={p:root/'finite'/('%03d'%i) for i,p in enumerate(original['finite_unique_paths'])}
  special={'request':m.REQUEST,'owner_receipt':m.TERMINAL,'container_log':evidence/'attempt/container.log','driver_receipt':output/'evidence/receipt.json','guard_result':capture/'guard-result.json'}
  for i in range(8):
   for kind in ('status.json','stdout','stderr'):special[f'client:{i}:{kind}']=capture/('command-%02d'%i)/kind
  for role,path in special.items():mapping[original['finite_roles'][role]['path']]=path
  paths={role:mapping[ref['path']] for role,ref in original['finite_roles'].items()}
  def write(p,value):
   p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_bytes(value if isinstance(value,bytes) else canon(value));p.chmod(0o600)
  def ref(p):return dict(path=str(p),sha256=sha(p.read_bytes()),bytes=p.stat().st_size)
  for p in mapping.values():write(p,b'finite fixture data')
  inspect=dict(Id=target['container_id'],Name='/'+target['container_name'],Image=target['image_id'],Path='/usr/bin/python3',Args=['/driver.py'],Config=dict(Labels={'mckernel.owner':target['owner_nonce']}),HostConfig={},Mounts=[],State=dict(Status='exited',Running=False,Pid=0,ExitCode=0))
  write(paths['terminal_inspection'],inspect)
  owner=dict(schema='mckernel.native-exact-mckernel-image-container-receipt.v1',status='PASS',retired=True,terminal_container_retained=True,cleanup_separately_required=True,candidate_sha=m.IMAGE_CANDIDATE,terminal_container_info=inspect,exit_code=0,**{k:target[k] for k in ('container_id','container_name','owner_nonce')})
  write(paths['owner_receipt'],owner)
  guard=dict(owner_status='PASS',owner_receipt_sha256=ref(paths['owner_receipt'])['sha256'],container_id=target['container_id'],retired=True,retained_for_separate_cleanup=True,interrupted_signal=None);write(paths['guard_result'],guard)
  join=dict(status='PASS_ORDINARY_GUARD_POSTJOIN_READBACK_ONLY',root27_4_reacquired_after_join=True,guard_direct_joined=True,common_shared_and_container_retained_for_separate_cleanup=True,cleanup_authorized=False,container_id=target['container_id'],owner_receipt_sha256=ref(paths['owner_receipt'])['sha256'],guard_result_sha256=ref(paths['guard_result'])['sha256']);write(paths['guard_postjoin'],join)
  for i in range(8):write(paths[f'client:{i}:status.json'],dict(state='exited',exit_code=0,pid=pids[i]))
  request=dict(schema='mckernel.native-exact-mckernel-image-container-request.v1',**source_binding,backup_root=str(backup),work_root=str(output),owner_evidence_root=str(evidence),output_root=str(output/'output'),evidence_root=str(output/'evidence'),attempt_root=str(evidence/'attempt'),lease_path=str(m.LEASE),common_exclusion_path=str(m.ATTEMPT));write(m.REQUEST,request);m.REQUEST_SHA=ref(m.REQUEST)['sha256']
  for p in (m.ATTEMPT,m.SHARED):write(p,dict(pid=target['owner_pid'],starttime=target['owner_starttime'],boot_id=boot,inode=0,dev=p.parent.stat().st_dev))
  records={}
  for role,p in [('common',m.ATTEMPT),('shared',m.SHARED)]:
   data=json.loads(p.read_bytes());data['inode']=p.stat().st_ino;write(p,data);records[role]=m.observe_identity(p)
  artifact=dict(schema='mckernel.current-numa-scheduler.production-image-artifact-review.v1',status='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE',decision='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY',implementation_ownership=False,reviewer='fixture-independent-reviewer',physical_clearance=False,producer_receipt=ref(paths['driver_receipt']),source_derivative_sha256='a'*64,materialization_sha256='b'*64);write(paths['artifact_acceptance'],artifact)
  retirement=dict(schema='mckernel.numa-current-image.retained-terminal-postjoin-review.v1',status='PASS_ACTUAL_IMAGE_TERMINAL_RETAINED_POSTJOIN_SCOPE_ONLY',build_status='PASS',retired=True,terminal_container_retained=True,cleanup_separately_required=True,physical_release=False,record_release_complete=False,request_lease_absent=True,outer_direct_joined=True,outer_group_absent=True,root_mutex_reacquired_after_guard_join=True,exact_terminal_exit0_nonOOM_PID0=True,closed_saved_host_client_count=8,source_derivative_sha256='a'*64,materialization_sha256='b'*64,retained_ownership=records,**{k:target[k] for k in ('container_id','container_name','owner_nonce','owner_pid','owner_starttime')})
  for key,role in [('owner_receipt','owner_receipt'),('guard_result','guard_result'),('outer_status','outer_status'),('inner_status','inner_status'),('terminal_fresh_inspect','terminal_inspection')]:retirement[key]=ref(paths[role])
  write(paths['retained_physical'],retirement)
  case['finite_roles']={k:ref(p) for k,p in paths.items()};case['finite_unique_paths']=sorted({str(p) for p in paths.values()});case['finite_unique_path_count']=EXPECTED_PATH_COUNT
  case['current_live_postjoin']=case['finite_roles']['guard_postjoin'];case['artifact_acceptance']=case['finite_roles']['artifact_acceptance'];case['source_identity']=source_binding
  case['full_original_record_authority']=[dict(role=role,full_descriptor=row,sha256=row['sha256'],record=json.loads(Path(row['path']).read_bytes())) for role,row in records.items()]
  m.CURRENT_TYPED_REQUEST=source_binding
  # Actual embedded acquisition code remains unchanged; only proc reads are provided.
  # Fixture engine changes are exclusively explicit DATA assignments; algorithms remain exact.
  constants=('ROOT','NAMESPACE','OUTPUT','EVIDENCE','ATTEMPT','SHARED','LEASE','REQUEST','REQUEST_SHA','TERMINAL','ROOT_LOCK','ARCHIVE_NAMES','PLAN','JOURNAL','CAPTURE','QUARANTINE','MUTEX','NAMESPACE_ANCESTRY','NAMESPACE_BINDING','CURRENT_TYPED_REQUEST')
  fixture_engine=prep/'fixture_engine.py';engine_text=ENGINE.read_text()+'\n# Explicit unprivileged fixture DATA follows.\n'
  for key in constants:
   value=getattr(m,key);engine_text+=key+' = '+('Path('+repr(str(value))+')' if isinstance(value,Path) else repr(value))+'\n'
  write(fixture_engine,engine_text.encode());casepath=prep/'case.json'
  refusal_stage='schema'
  if negative:negative(case,paths,m)
  write(casepath,case)
  o=load(G/'observe_current_pass_image_retirement.py','observer_'+label)
  for k,v in dict(PREP=prep,OUTPUT=observer_output,ROOT=root,CAPTURE=capture,SOURCE=fixture_engine,SOURCE_SHA=sha(fixture_engine.read_bytes()),TEST=Path(__file__).resolve(),TEST_SHA=sha(Path(__file__).resolve().read_bytes()),FAILURE_CASE=casepath,FAILURE_CASE_SHA=sha(casepath.read_bytes()),RETIREMENT=paths['retained_physical'],RETIREMENT_SHA=sha(paths['retained_physical'].read_bytes()),BOOT=boot,PIDS=pids,CURRENT_EXPECTED_SOURCE=source_binding,NONCE='fixture-full-main-1').items():setattr(o,k,v)
  # Exact release and independent source/execution review joins remain real.
  reviews=[]
  for kind in ('source_review','execution_review'):
   p=prep/(kind+'.json');value=dict(status='PASS',reviewer='fixture-independent-reviewer',implementation_ownership=False,observer_sha256=sha(Path(o.__file__).read_bytes()),cleanup_source_sha256=o.SOURCE_SHA,cleanup_tests_sha256=o.TEST_SHA);reviews.append((p,value))
  release=dict(schema='mckernel.phase5.current-pass-image.readonly-observation-release.v1',status='PASS_EXECUTION_RELEASE',cleanup_authorized=False,fetched_source_verified=True,git_commit='0'*40,git_tree='0'*40,nonce=o.NONCE,output=str(o.OUTPUT),observer_sha256=sha(Path(o.__file__).read_bytes()),cleanup_source_sha256=o.SOURCE_SHA,cleanup_tests_sha256=o.TEST_SHA,retirement_sha256=o.RETIREMENT_SHA,failure_case_sha256=o.FAILURE_CASE_SHA,observer_command=o.OBSERVATION_COMMAND,resource_profile=o.OBSERVATION_PROFILE,author='fixture-author')
  write(reviews[0][0],reviews[0][1]);release['source_review']={k:v for k,v in ref(reviews[0][0]).items() if k!='bytes'}
  reviews[1][1]['reviewed_observation_payload_sha256']=sha(o.canonical_payload(release));write(reviews[1][0],reviews[1][1]);release['execution_review']={k:v for k,v in ref(reviews[1][0]).items() if k!='bytes'}
  releasepath=prep/'release.json';write(releasepath,release)
  real_stat=os.stat;real_fstat=os.fstat;real_lstat=os.lstat;real_path_stat=Path.stat;real_path_lstat=Path.lstat;real_read=Path.read_text
  def model(meta,p):
   if p==lock or p==diagnosticdir or diagnosticdir in p.parents:
    fields={k:getattr(meta,k) for k in dir(meta) if k.startswith('st_')}
    if p==diagnosticdir or diagnosticdir in p.parents:fields.update(st_uid=0,st_gid=0)
    if p==lock:fields.update(st_dev=27,st_ino=4)
    return types.SimpleNamespace(**fields)
   return meta
  def fstat(fd):return model(real_fstat(fd),Path(os.readlink('/proc/self/fd/'+str(fd))))
  def stat_call(p,*a,dir_fd=None,**kw):
   path=Path(p)
   if not path.is_absolute():path=(Path(os.readlink('/proc/self/fd/'+str(dir_fd))) if dir_fd is not None else Path.cwd())/path
   return model(real_stat(p,*a,dir_fd=dir_fd,**kw),path)
  def lstat_call(p,*a,dir_fd=None,**kw):
   path=Path(p)
   if not path.is_absolute():path=(Path(os.readlink('/proc/self/fd/'+str(dir_fd))) if dir_fd is not None else Path.cwd())/path
   return model(real_lstat(p,*a,dir_fd=dir_fd,**kw),path)
  def path_stat_call(p,*a,**kw):
   path=p if p.is_absolute() else Path.cwd()/p
   return model(real_path_stat(p,*a,**kw),path)
  def path_lstat_call(p,*a,**kw):
   path=p if p.is_absolute() else Path.cwd()/p
   return model(real_path_lstat(p,*a,**kw),path)
  def read_text(p,*a,**kw):return boot if str(p)=='/proc/sys/kernel/random/boot_id' else real_read(p,*a,**kw)
  calls=[]
  real_open=open;real_listdir=os.listdir;real_readlink=os.readlink
  live_pid=os.getpid();live_start=Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode()
  def proc_stat(pid):
   fields=[b'0']*50;fields[0]=b'S';fields[1]=b'0' if pid==1 else b'1';fields[19]=str(live_start if pid==live_pid else pid).encode()
   return str(pid).encode()+b' (fixture) '+b' '.join(fields)+b'\n'
  def proc_open(path,mode='r',*args,**kwargs):
   if path=='/proc/sys/kernel/random/boot_id':return io.StringIO(boot)
   if isinstance(path,str) and path.startswith('/proc/') and path.split('/')[2].isdigit():
    pid=int(path.split('/')[2]);part=path.split('/')[3]
    return io.BytesIO(proc_stat(pid) if part=='stat' else b'fixture\0')
   return real_open(path,mode,*args,**kwargs)
  def proc_listdir(path):return ['1',str(live_pid)]+(['30'] if label=='proc-publisher' else []) if path=='/proc' else real_listdir(path)
  def proc_readlink(path):
   if path=='/proc/30/exe' and label=='proc-publisher':return '/usr/bin/make'
   if isinstance(path,str) and path.startswith('/proc/') and path.endswith('/exe'):return '/usr/bin/fixture'
   return real_readlink(path)
  def command(argv,**kw):
   calls.append(argv)
   if label=='final-inventory-drift' and argv[0]=='/usr/bin/docker' and argv[2]=='ps' and sum(a[0]=='/usr/bin/docker' and a[2]=='ps' for a in calls)==2:write(output/'late-drift',b'externally changed fixture output')
   if argv[0]=='/usr/bin/findmnt':value=dict(filesystems=[dict(uuid=m.UUID,target=str(root),fstype='ext4',options='rw,nodev,nosuid')])
   elif argv[0]=='/usr/bin/docker' and argv[2]=='ps':value=dict(ID=target['container_id'],Names=target['container_name'],Labels='mckernel.owner='+target['owner_nonce'],State='exited')
   elif argv[0]=='/usr/bin/docker' and argv[2]=='inspect':value=[inspect]
   else:raise AssertionError('nonfixture command:'+repr(argv))
   return subprocess.CompletedProcess(argv,0,canon(value)+b'\n',b'')
  with contextlib.ExitStack() as stack:
   for p in (patch('builtins.open',proc_open),patch.object(os,'listdir',proc_listdir),patch.object(os,'readlink',proc_readlink),patch.object(os,'getuid',return_value=0),patch.object(os,'geteuid',return_value=0),patch.object(o.resource,'setrlimit'),patch.object(os,'fstat',fstat),patch.object(os,'stat',stat_call),patch.object(os,'lstat',lstat_call),patch.object(Path,'stat',path_stat_call),patch.object(Path,'lstat',path_lstat_call),patch.object(Path,'read_text',read_text),patch.object(subprocess,'run',command)):stack.enter_context(p)
   attempt.record('before-generated-observer-main',generated_observer=str(G/'observe_current_pass_image_retirement.py'))
   try:
    with contextlib.redirect_stdout(io.StringIO()):o.main(['--git-commit','0'*40,'--git-tree','0'*40,'--observation-release',str(releasepath),'--observation-release-sha256',sha(releasepath.read_bytes())])
   except Exception as exc:
    if negative is None:raise
    expected='concurrent-build-or-cleanup-publisher' if label=='proc-publisher' else (('exact sorted distinct role path union required' if label in ('missing-path','extra-path','duplicate-path') else 'finite-case:') if label not in ('descriptor-drift','incomplete-client-ledger','final-inventory-drift') else {'descriptor-drift':'closed PASS role bytes differ','incomplete-client-ledger':'all exact current original clients required','final-inventory-drift':'preserved output metadata changed'}[label])
    assert expected in str(exc),(label,str(exc))
    assert observer_output.exists()==(label in ('descriptor-drift','incomplete-client-ledger','final-inventory-drift','proc-publisher')),(label,'refusal stage')
    assert not (observer_output/'observer-result.json').exists(),label
    assert not (observer_output/'cleanup-release-draft.json').exists(),label
    if label=='proc-publisher':
     retained=json.loads((observer_output/'process-00.json').read_bytes());assert retained['schema']=='fp-save-image.proc.v2' and retained['publishers']==[[30,'30','/usr/bin/make']]
    with lock.open('rb') as stream:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(stream,fcntl.LOCK_UN)
    attempt.record('EXPECTED_REFUSAL',reason=str(exc),output_directory_created=observer_output.exists(),success_outputs_absent=True,lock_reacquired=True)
    return dict(location=str(attempt.path),label=label,status='REFUSED',reason=str(exc),output_directory_created=observer_output.exists(),lock_reacquired=True)
   attempt.record('generated-observer-main-returned',output=str(observer_output))
   assert negative is None,('negative accepted',label)
   summary=load(G/'readback_observer.py','summary_fixture');summary.OUTPUT=observer_output;summary.NONCE=o.NONCE
   data=summary.read_all();result=summary.summarize(data)
   assert result['status']=='PASS_EXACT_FINITE_OBSERVER_READBACK_ONLY'
   retained=[json.loads(f.read_bytes()) for f in observer_output.glob('process-*.json')];assert retained and all(r['schema']=='fp-save-image.proc.v2' and len(r['snapshots'])==2 and r['acquisition']['attempts'] for r in retained)
   post=load(G/'postjoin_readback.py','post_fixture');actual,objects=post.finite_metadata_consumer(m,o,data['observation.json'][1]);assert len(actual)==EXPECTED_PATH_COUNT and objects()==actual
   attempt.record('generated-postjoin-consumer-returned',generated_postjoin=str(G/'postjoin_readback.py'),finite_objects=len(actual),summary_validated=True)
   scalar=copy.deepcopy(case);scalar['finite_unique_paths']=EXPECTED_PATH_COUNT;scalarpath=prep/'postjoin-scalar-case.json';write(scalarpath,scalar);o.FAILURE_CASE=scalarpath;o.FAILURE_CASE_SHA=sha(scalarpath.read_bytes())
   try:post.finite_metadata_consumer(m,o,data['observation.json'][1])
   except RuntimeError as exc:
    assert 'scalar schema refused' in str(exc);attempt.record('EXPECTED_POSTJOIN_SCALAR_REFUSAL',reason=str(exc),case=str(scalarpath))
   else:raise AssertionError('postjoin accepted scalar schema')
   o.FAILURE_CASE=casepath;o.FAILURE_CASE_SHA=sha(casepath.read_bytes())
   with lock.open('rb') as stream:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(stream,fcntl.LOCK_UN)
   attempt.record('PASS_COMPLETE_FIXTURE',finite_objects=len(actual),finite_roles=EXPECTED_ROLE_COUNT,lock_reacquired=True)
   return dict(location=str(attempt.path),label=label,status='PASS_FULL_ACTUAL_MAIN_RETURN_AND_POSTJOIN_FINITE_CONSUMER',finite_objects=len(actual),finite_roles=EXPECTED_ROLE_COUNT,summary_validated=True,fixed_command_count=len(calls),lock_reacquired=True)

def mutate_path_union(case,kind):
 if kind=='missing':case['finite_unique_paths'].pop()
 elif kind=='extra':case['finite_unique_paths'].append('/extra')
 else:case['finite_unique_paths'].append(case['finite_unique_paths'][0])
 case['finite_unique_path_count']=len(case['finite_unique_paths'])

def main():
 results=[test('positive'),test('proc-publisher',lambda c,p,m:None)]
 (D/'FULL-MAIN-PROC-V2-RESULTS.json').write_text(json.dumps(dict(status='PASS',scope='actual main, summary and finite postjoin fixture; no physical clearance',results=results),indent=2)+'\n')
 print(json.dumps(results,sort_keys=True))
if __name__=='__main__':main()
