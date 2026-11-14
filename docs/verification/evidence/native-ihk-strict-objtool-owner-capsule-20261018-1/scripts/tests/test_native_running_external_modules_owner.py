"""Actual IHK owner request/profile/receipt bodies; synthetic fixture sources and modeled physical admission."""
from pathlib import Path
import copy,hashlib,importlib.util,json,resource,sys,tempfile,unittest
from unittest import mock
resource.setrlimit(resource.RLIMIT_AS,(1024**3,1024**3));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
S=Path(__file__).resolve().parents[1];sys.path.insert(0,str(S))
import native_running_external_modules_owner as m
AUTH=json.loads(m.AUTHORITY.read_text());PREP=json.loads(m.PREPARATION.read_text())
OLD=Path('/home/holden/mckernel-work/scratch/nsd-c-acc3b42f42e5dc087ce8ac605f8f4961/modules/ihk.ko')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Tests(unittest.TestCase):
 def patch(self,obj,key,value):
  p=mock.patch.object(obj,key,value);p.start();self.addCleanup(p.stop)
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(dir=str(S.parents[1]),prefix='ihk-fixture-');self.addCleanup(tmp.cleanup);self.root=Path(tmp.name)
  for name,val in [('ROOT',self.root),('LEASE',self.root/'lease'),('COMMON',self.root/'common')]:self.patch(m,name,val)
  self.patch(m.shared,'SHARED_HEAVY_LOCK_PATH',str(self.root/'shared'));self.patch(m.image,'COMMON_EXCLUSION',str(self.root/'image-common'));self.patch(m.host,'OPERATIONAL_EXCLUSION_PATH',str(self.root/'legacy'))
  self.nonce='d'*32;self.c=self.root/('nsd-c-'+self.nonce);self.i=self.root/('nsd-i-'+self.nonce)
  for name in ['modules','home','tmp']:(self.c/name).mkdir(parents=True)
  (self.i/'driver-packet').mkdir(parents=True);self.auth=copy.deepcopy(AUTH);rows=[]
  for row in AUTH['source_files']:
   path=self.c/'modules'/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(('synthetic-fixture:'+row['path']).encode());rows.append(dict(row,bytes=path.stat().st_size,sha256=digest(path)))
  self.auth['source_files']=rows;self.prep=copy.deepcopy(PREP);self.prep['closure']=rows
  ap=self.root/'authority.json';ap.write_text(json.dumps(self.auth));pp=self.root/'preparation.json';pp.write_text(json.dumps(self.prep))
  for name,val in [('AUTHORITY',ap),('AUTHORITY_SHA',digest(ap)),('PREPARATION',pp),('PREPARATION_SHA',digest(pp))]:self.patch(m,name,val)
  (self.i/'preparation.json').write_bytes(pp.read_bytes());(self.i/'driver-packet/ihk_objtool_consumer.py').write_bytes(m.DRIVER.read_bytes());(self.i/'driver-packet/module-source-authority.json').write_bytes(ap.read_bytes())
  self.rp=self.root/'request.json';self.rp.write_text('{}')
  self.q=dict(schema='mckernel.native-running-external-modules-request.v1',candidate_sha=m.CANDIDATE,image_id=m.IMAGE,nonce=self.nonce,request_path=str(self.rp),preparation=dict(path=str(pp),sha256=m.PREPARATION_SHA),driver=dict(path=str(m.DRIVER),sha256=digest(m.DRIVER)),input_root=str(self.i),candidate_root=str(self.c),owner_evidence_root=str(self.root/('nsd-o-'+self.nonce)),lease_path=str(m.LEASE),common_exclusion_path=str(m.COMMON),basis_identity={},candidate_identity={},input_identity={},boot_id=m.BOOT,timeout=1800,disk_budget_bytes=512<<20,capture_budget_bytes=64<<20,terminal_policy='remove-owned-terminal')
  for key in ['live_admission','measure','validate_historical_report']:self.patch(m,key,mock.Mock(return_value={'explicitly':'modeled root/mount/resource/historical boundary'}))
 def valid(self):return m.validate_request(self.q,self.rp,historical_observe=lambda:{'modeled':'root'})
 def receipt(self):
  d=self.c/'modules';(d/'ihk.ko').write_bytes(OLD.read_bytes());(d/'modules.order').write_text('/candidate/modules/ihk.o\n');(d/'.ihk.o.cmd').write_text('modeled artifact command boundary\n')
  sp=importlib.util.spec_from_file_location('real_retained_modinfo',m.REFERENCE_DRIVER);p=importlib.util.module_from_spec(sp);sp.loader.exec_module(p)
  return dict(status='PASS_IHK_STRICT_TOOL_CONSUMER_ONLY',make_returncode=0,module_acceptance=False,three_module_acceptance=False,native_acceptance=False,artifact=dict(bytes=(d/'ihk.ko').stat().st_size,sha256=digest(d/'ihk.ko')),command_sha256=digest(d/'.ihk.o.cmd'),modinfo=p.modinfo(d/'ihk.ko'))
 def consume(self,r):return m.consume_pilot_receipt(self.q,r,self.prep)
 def info(self):
  name='mckernel-external-'+self.nonce;cid='c'*64
  hc=dict(m.host.LIMITS,Privileged=False,ReadonlyRootfs=True,CapDrop=['ALL'],SecurityOpt=['no-new-privileges'],Init=True,PidMode='',IpcMode='private',Devices=[],DeviceRequests=[],Binds=[],CapAdd=[],CgroupParent='',Tmpfs={'/tmp':'rw,nodev,nosuid,size=256m'},AutoRemove=False,RestartPolicy={'Name':'no','MaximumRetryCount':0})
  return dict(Id=cid,Name='/'+name,Image=m.IMAGE,Path='/usr/bin/python3',Args=m.COMMAND,Config=dict(User='1000:1000',Entrypoint=['/usr/bin/python3'],Cmd=m.COMMAND,Labels={'mckernel.owner':self.nonce}),State=dict(Status='created',Running=False,Pid=0),HostConfig=hc,Mounts=[dict(Source=s,Destination=t,RW=not ro,Type='bind') for s,t,ro in m.mounts(self.q)]),name,cid
 def test_request_positive(self):self.assertIn('historical_leases',self.valid())
 def test_request_missing_source(self):
  (self.c/'modules/ihk.rs').unlink()
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_extra_source(self):
  (self.c/'modules/held-smp.rs').write_text('extra')
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_wrong_source(self):
  (self.c/'modules/ihk.rs').write_text('changed')
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_wrong_driver(self):
  (self.i/'driver-packet/ihk_objtool_consumer.py').write_text('changed')
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_extra_input(self):
  (self.i/'extra').write_text('extra')
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_conflicting_token(self):
  Path(m.shared.SHARED_HEAVY_LOCK_PATH).write_text('foreign')
  with self.assertRaises(m.Refusal):self.valid()
 def test_request_wrong_tool(self):
  path=self.root/'wrong-tool';path.write_text('wrong');self.patch(m,'TOOL',path)
  with self.assertRaises(m.Refusal):self.valid()
 def test_profile_positive(self):
  info,name,cid=self.info();m.profile(info,self.q,name,self.nonce,cid);self.assertEqual(len(info['Mounts']),7)
 def test_profile_missing_mount(self):
  info,name,cid=self.info();info['Mounts'].pop()
  with self.assertRaises(m.Refusal):m.profile(info,self.q,name,self.nonce,cid)
 def test_profile_extra_mount(self):
  info,name,cid=self.info();info['Mounts'].append(dict(Source='/extra',Destination='/extra',Type='bind',RW=False))
  with self.assertRaises(m.Refusal):m.profile(info,self.q,name,self.nonce,cid)
 def test_profile_wrong_tool(self):
  info,name,cid=self.info();next(q for q in info['Mounts'] if q['Destination']=='/accepted-tool/objtool-after')['Source']='/wrong'
  with self.assertRaises(m.Refusal):m.profile(info,self.q,name,self.nonce,cid)
 def test_profile_writable_tool(self):
  info,name,cid=self.info();next(q for q in info['Mounts'] if q['Destination']=='/accepted-tool/objtool-after')['RW']=True
  with self.assertRaises(m.Refusal):m.profile(info,self.q,name,self.nonce,cid)
 def test_receipt_positive(self):
  p=self.consume(self.receipt());self.assertEqual(p['compiled_modules'],['ihk']);self.assertFalse(p['matched_three_module_set'])
 def test_receipt_missing_artifact(self):
  r=self.receipt();(self.c/'modules/ihk.ko').unlink()
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_extra_artifact(self):
  r=self.receipt();(self.c/'modules/mcctrl.ko').write_text('not accepted')
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_wrong_artifact(self):
  r=self.receipt();r['artifact']['sha256']='a'*64
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_wrong_source(self):
  r=self.receipt();(self.c/'modules/ihk.rs').write_text('changed')
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_wrong_status(self):
  r=self.receipt();r['status']='BUILD_ARTIFACT_CHECKS_PASS'
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_three_module_promotion(self):
  r=self.receipt();r['three_module_acceptance']=True
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_wrong_command(self):
  r=self.receipt();r['command_sha256']='a'*64
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_receipt_wrong_modinfo(self):
  r=self.receipt();r['modinfo']['name']='mcctrl'
  with self.assertRaises(m.Refusal):self.consume(r)
 def test_unpublished_release_refused(self):
  r=dict(schema='mckernel.native-running-external-modules-release.v1',status='PASS_EXECUTION_RELEASE',execution_count=1,request=dict(path=str(self.rp),sha256='a'*64),nonce=self.nonce,boot_id=m.BOOT,fetched_source_verified=False,terminal_policy='remove-owned-terminal')
  with mock.patch.object(m,'bound',side_effect=[self.q,r]):
   with self.assertRaises(m.Refusal):m.authenticate(self.rp,'a'*64,self.root/'release','b'*64)
if __name__=='__main__':unittest.main(verbosity=2)
