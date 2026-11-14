"""Private no-effect owner/export consumer fixtures. Never run a probe or emit proof."""
import copy,hashlib,importlib.util,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
C=Path(__file__).resolve().parents[2];sys.path.insert(0,str(C/'scripts'))
import probe_contract as pc
import export_probe as ex
import native_running_external_modules_owner as own
PREP=json.loads((C/'preparation.json').read_text())

def model():
 refs={n:dict(path='/fixture/'+n+'.json',sha256=hashlib.sha256(n.encode()).hexdigest()) for n in ex.ROLES};raw={}
 req=dict(image_id=pc.IMAGE,preparation=refs['preparation'],candidate_root='/fixture/work',input_root='/fixture/probe',nonce='a'*32,boot_id='fixture',lease_path='/fixture/lease',common_exclusion_path='/fixture/common')
 cmd=own.COMMAND;cfg=dict(Image=pc.IMAGE,User='1000:1000',Entrypoint=['/usr/bin/timeout'],Cmd=cmd,Labels={'mckernel.owner':req['nonce']})
 host=dict(Memory=12884901888,MemorySwap=12884901888,NanoCpus=4000000000,CpusetCpus='2-5',PidsLimit=512,NetworkMode='none',IpcMode='private',ReadonlyRootfs=True,CapDrop=['ALL'],Init=True,SecurityOpt=['no-new-privileges'],AutoRemove=False,RestartPolicy={'Name':'no','MaximumRetryCount':0},Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'})
 mounts=[dict(Type='bind',Source=req['input_root'],Destination='/probe',RW=False),dict(Type='bind',Source=req['candidate_root'],Destination='/work',RW=True)]
 inspect=dict(Id='b'*64,Name='/mckernel-external-'+req['nonce'],Image=pc.IMAGE,Config=cfg,HostConfig=host,Mounts=mounts,Path='/usr/bin/timeout',Args=cmd)
 terminal=copy.deepcopy(inspect);terminal['State']=dict(Status='exited',Pid=0,Running=False,OOMKilled=False,ExitCode=0)
 group=dict(empty=True,surviving_members=[],status_path='/fixture/client.status.json');raw[group['status_path']]=json.dumps(dict(state='exited',exit_code=0)).encode()
 post=dict(container_absent=True,all_clients_reaped=True,compiler_status='PASS',absence=dict(absent=True,container_id='b'*64,name='mckernel-external-'+req['nonce'],nonce=req['nonce'],queries=['name','label','id']),client_group_checks=[group],admission_client_group_checks=[group])
 records=[];record_values={}
 for label,path in [('lease',req['lease_path']),('common',req['common_exclusion_path']),('shared','/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock')]:
  record={'fixture':label};data=json.dumps(record).encode();raw['/fixture/'+label+'.record.raw']=data;record_values[label]=record;records.append(dict(path=path,record=record,size=len(data),sha256=pc.digest(data)))
 sources={'scripts/native_running_external_modules_owner.py':'c'*64}
 release=dict(schema='mckernel.native-running-external-modules-release.v1',status='PASS_EXECUTION_RELEASE',request=refs['request'],nonce=req['nonce'],boot_id=req['boot_id'],source_sha256=sources)
 owner=dict(schema='mckernel.native-running-external-modules-owner-receipt.v1',request=req,authority=dict(request=refs['request'],source_sha256=sources),status='PASS',build_status='PASS',wait_exit_code=0,retired=True,cleanup_status='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE',cleanup_separately_required=False,terminal_container_retained=False,terminal_container_info_current=True,target_build=False,probe_result_sha256=refs['inner_result']['sha256'],probe_evidence={'fixture_join':True},container_id='b'*64,container_name='mckernel-external-'+req['nonce'],image_inspect=dict(Id=pc.IMAGE,Architecture='amd64'),postflight=post,operation_lease=record_values['lease'],common_record=record_values['common'],shared_record=record_values['shared'])
 # The exact actual path requirement is exercised with the fixed fixture root.
 refs['inner_result']['path']='/fixture/work/evidence/probe-result.json'
 values=dict(request=req,preparation={'source_rows':PREP['source_rows']},owner_receipt=owner,inner_result=dict(make_sha256='d'*64,make_version='GNU Make fixture'),inspect_before=inspect,inspect_terminal=terminal,postflight=post,ownership_archive=dict(request=refs['request'],source_sha256=sources,nonce=req['nonce'],postflight=post,records=records),release_authorized=dict(status='POSTFLIGHT_RELEASE_AUTHORIZED',nonce=req['nonce'],archive_sha256=refs['ownership_archive']['sha256'],records=records),release_complete=dict(status='OWNED_RECORDS_RELEASED',nonce=req['nonce'],archive_sha256=refs['ownership_archive']['sha256']),execution_release=release)
 raw['/fixture/owner.stdout']=json.dumps(owner).encode();raw['/fixture/owner.stderr']=b''
 argv=['/home/holden/anaconda3/bin/python3','-B','/fixture/scripts/native_running_external_modules_owner.py','--request',refs['request']['path'],'--request-sha256',refs['request']['sha256'],'--release',refs['execution_release']['path'],'--release-sha256',refs['execution_release']['sha256']]
 values['dispatch_status']=dict(returncode=0,direct_child_joined=True,owned_group_absent=True,request=refs['request'],release=refs['execution_release'],owner_sha256='c'*64,argv=argv,captures={r:dict(path='/fixture/owner.'+r,bytes=len(raw['/fixture/owner.'+r]),sha256=pc.digest(raw['/fixture/owner.'+r])) for r in ('stdout','stderr')})
 review=dict(decision='PASS_ACTUAL_PINNED_MAKE_PIPE_PROBE_AND_RETIREMENT',implementation_ownership=False,reviewer='fixture-reviewer',author='fixture-author',inputs=refs)
 binding=dict(schema='mckernel.pinned-make-proof-export.v1',inputs=refs,independent_review=dict(path='/fixture/review.json',sha256='e'*64))
 values_by_path={refs[k]['path']:v for k,v in values.items()};values_by_path['/fixture/review.json']=review
 return binding,values,values_by_path,raw

class NoEffect(unittest.TestCase):
 def test_exact_two_file_capsule_and_unchanged_probe(self):
  self.assertEqual({p.name for p in (C/'probe-capsule').iterdir()},{'Makefile','probe.py'})
  for n,r in PREP['source_rows'].items():self.assertEqual(pc.digest((C/'probe-capsule'/n).read_bytes()),r['sha256'])
  self.assertIn('image_identity_authenticated=False',(C/'probe-capsule/probe.py').read_text())
 def test_actual_owner_command_and_profile(self):
  b,v,by,raw=model();r=v['request'];r['candidate_root']='/fixture/work';r['input_root']='/fixture/probe'
  self.assertEqual(own.mounts(r),[('/fixture/probe','/probe',True),('/fixture/work','/work',False)])
  a=own.create_args(r,'x','a'*32);self.assertEqual(a[-(len(own.COMMAND)+3):],['--entrypoint','/usr/bin/timeout',pc.IMAGE,*own.COMMAND]);self.assertEqual(sum(x=='--mount' for x in a),2)
  x=v['inspect_before']
  with patch.object(own.host,'check_profile',return_value=None):
   own.profile(x,r,'mckernel-external-'+r['nonce'],r['nonce'],'b'*64)
   bad=copy.deepcopy(x);bad['Config']['Entrypoint']=['/usr/bin/python3']
   with self.assertRaises(own.Refusal):own.profile(bad,r,'mckernel-external-'+r['nonce'],r['nonce'],'b'*64)
 def test_actual_owner_cli_and_load_preparation_source_guards(self):
  import io,types
  root=Path(os.environ['MCKERNEL_PROBE_FIXTURE_ROOT'])/'request';root.mkdir(parents=True,mode=0o700)
  req=copy.deepcopy(json.loads((C.parent/'request-draft.json').read_text())['request']);nonce=req['nonce'];work=root/('nsd-c-'+nonce);work.mkdir(mode=0o700)
  for n in ('home','tmp'):(work/n).mkdir(mode=0o700)
  req.update(candidate_root=str(work),owner_evidence_root=str(root/('nsd-o-'+nonce)),request_path=str(root/'request.json'),lease_path=str(root/'lease'),common_exclusion_path=str(root/'common'))
  rp=root/'request.json';rp.write_text(json.dumps(req))
  ctx=[patch.object(own,'ROOT',root),patch.object(own,'LEASE',root/'lease'),patch.object(own,'COMMON',root/'common'),patch.object(own.shared,'SHARED_HEAVY_LOCK_PATH',str(root/'shared')),patch.object(own.image,'COMMON_EXCLUSION',str(root/'imagecommon')),patch.object(own.host,'OPERATIONAL_EXCLUSION_PATH',str(root/'hostcommon')),patch.object(own,'live_admission',return_value={'fixture_no_host_effect':True}),patch.object(own,'measure',return_value={'fixture_no_resource_admission':True}),patch.object(own,'validate_historical_report',return_value={'fixture_no_root_observer':True})]
  import contextlib
  with contextlib.ExitStack() as stack:
   for x in ctx:stack.enter_context(x)
   result=own.validate_request(req,rp,historical_observe=lambda:{'fixture':True});self.assertIn('historical_leases',result)
   bad=copy.deepcopy(req);bad['image_id']='wrong'
   with self.assertRaises(own.Refusal):own.validate_request(bad,rp,historical_observe=lambda:{})
   bad=copy.deepcopy(req);bad['timeout']=1800
   with self.assertRaises(own.Refusal):own.validate_request(bad,rp,historical_observe=lambda:{})
   # The real load/bound preparation and actualtwo source sizes/hashes above
   # were consumed. Root/lease/observer/resource effects alone were stubbed.
  with patch.object(sys,'argv',['owner','--request',str(rp),'--request-sha256','a'*64,'--release','/fixture/release.json','--release-sha256','b'*64]),patch.object(own,'guarded_execute',return_value={'status':'PASS','fixture_only':True}) as no_effect,patch('sys.stdout',new_callable=io.StringIO):
   self.assertEqual(own.main(),0);self.assertEqual(no_effect.call_args.args,(rp,'a'*64,Path('/fixture/release.json'),'b'*64))
 def test_actual_inner_status_streams_source_bytes_and_schema(self):
  work=Path(os.environ['MCKERNEL_PROBE_FIXTURE_ROOT'])/'inner';e=work/'evidence';e.mkdir(parents=True,mode=0o700)
  def put(n,value):
   p=e/n;p.write_bytes(value if isinstance(value,bytes) else (json.dumps(value)+'\n').encode());return p
  statuses={}
  for label,argv,out in [('make-version',['/usr/bin/make','--version'],b'GNU Make fixture only\n'),('recursive-pipe',pc.ARGV,b'fixture recipe only\n')]:
   captures={}
   for role,data in [('stdout',out),('stderr',b'')]:
    put(label+'.'+role,data);captures[role]=dict(path='/work/evidence/'+label+'.'+role,bytes=len(data),sha256=pc.digest(data))
   status=dict(argv=argv,returncode=0,direct_child_joined=True,owned_group_absent=True,timed_out=False,cleanup_actions=[],captures=captures);put(label+'.status.json',status);statuses[label]=status
  children=[]
  for i,label in enumerate(('a','b')):
   ends=[dict(fd=3,access_mode=0,link='pipe:[42]',inode=42),dict(fd=4,access_mode=1,link='pipe:[42]',inode=42)]
   row=dict(label=label,pid=10+i,parent_pid=20+i,makelevel=2,pipe_jobserver_observed=True,endpoints=ends,makeflags='-j2 --jobserver-auth=3,4');put('child-'+label+'.json',row);children.append(row)
  inner=dict(fixture_data_only=True,status='PASS_RECURSIVE_MAKE_PIPE_OBSERVATION',image_id=pc.IMAGE,image_identity_authenticated=False,observation_only=True,native_acceptance=False,target_build=False,make_path='/usr/bin/make',argv=pc.ARGV,returncode=0,direct_child_joined=True,pipe_jobserver_observed=True,fifo_count=0,make_sha256='d'*64,make_version='GNU Make fixture only\n',source_refs=PREP['source_rows'],make_version_status=statuses['make-version'],make_status=statuses['recursive-pipe'],children=children)
  put('probe-result.json',inner);value=pc.validate_inner(inner,work,PREP['source_rows']);self.assertEqual(value['source_rows'],PREP['source_rows'])
  bad=copy.deepcopy(inner);bad['source_refs']['probe.py']['bytes']+=1
  with self.assertRaises(ValueError):pc.validate_inner(bad,work,PREP['source_rows'])
  (e/'recursive-pipe.stdout').write_bytes(b'corrupted fixture')
  with self.assertRaises(ValueError):pc.validate_inner(inner,work,PREP['source_rows'])
 def test_export_actual_outer_join_in_memory_only(self):
  b,v,by,raw=model()
  with patch.object(pc,'bound',side_effect=lambda r:by[r['path']]),patch.object(pc,'read',side_effect=lambda p,*args:raw[str(p)]),patch.object(pc,'validate_inner',return_value={'fixture_join':True}):
   value=ex.validate(b);self.assertEqual(value['status'],'PASS_PINNED_MAKE_PIPE_RECIPE');self.assertFalse(value['driver_build_authority'])
  # No exporter write function is invoked; this is synthetic in-memory data.
 def test_export_negative_review_image_retirement_and_join(self):
  changes=[lambda v,by:by['/fixture/review.json'].update(reviewer='fixture-author'),lambda v,by:v['owner_receipt'].update(retired=False),lambda v,by:v['inspect_terminal']['Config'].update(Image='wrong'),lambda v,by:v['dispatch_status'].update(direct_child_joined=False),lambda v,by:v['release_complete'].update(status='PENDING'),lambda v,by:v['dispatch_status'].update(owner_sha256='wrong'),lambda v,by:v['postflight']['client_group_checks'][0].update(empty=False)]
  for mutate in changes:
   b,v,by,raw=model();mutate(v,by)
   with patch.object(pc,'bound',side_effect=lambda r:by[r['path']]),patch.object(pc,'read',side_effect=lambda p,*args:raw[str(p)]),patch.object(pc,'validate_inner',return_value={'fixture_join':True}):
    with self.assertRaises(ValueError):ex.validate(b)
 def test_export_refuses_before_any_output_without_actual_review(self):
  b,v,by,raw=model();by['/fixture/review.json']['decision']='SOURCE_ONLY'
  with patch.object(pc,'bound',side_effect=lambda r:b if r['path']=='/fixture/binding.json' else by[r['path']]),patch.object(ex.os,'open',side_effect=AssertionError('unexpected proof output')):
   with self.assertRaises(ValueError):ex.export(Path('/fixture/binding.json'),'f'*64,Path('/fixture/output'))
 def test_owner_retirement_methods_reused(self):
  import ast
  old=Path('/home/holden/mckernel-work/scratch/native-cpu-reacquire-module-preparation-20261017-1/final/capsule/scripts/native_running_external_modules_owner.py').read_text();new=(C/'scripts/native_running_external_modules_owner.py').read_text()
  def funcs(s):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(s).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
  a,z=funcs(old),funcs(new);changed={n for n in a if a[n]!=z[n]};self.assertEqual(changed,{'mounts','profile','live_admission','measure','validate_request','create_args','run_owner','authenticate'})
  for n in ('release_owned_records','positive_clients','BoundDocker','guarded_execute','ExternalDocker','HistoricalObserverClient'):self.assertEqual(a[n],z[n])
if __name__=='__main__':unittest.main(verbosity=2)
