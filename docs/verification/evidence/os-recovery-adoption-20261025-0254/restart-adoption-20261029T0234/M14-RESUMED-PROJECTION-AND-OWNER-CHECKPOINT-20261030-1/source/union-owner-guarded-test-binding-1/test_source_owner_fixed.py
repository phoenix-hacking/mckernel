"""Unrun synthetic tests, no runtime authority or real immutable changes.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import os
import hashlib
import stat
import sys
import types
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock

# These are reviewed source bindings, not authority to run the fixture.  Compile
# exactly the verified bytes instead of verifying a path and importing it later.
HERE=Path(os.path.abspath(__file__)).parent
SIBLING=HERE.parent
def held_bytes(path,sha):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  before=os.fstat(fd)
  if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>1<<20:raise ValueError('fixture dependency identity')
  chunks=[];size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   chunks.append(block);size+=len(block)
   if size>1<<20:raise ValueError('fixture dependency size')
  after=os.fstat(fd);named=os.stat(path,follow_symlinks=False)
  fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  if size!=before.st_size or any(getattr(before,k)!=getattr(after,k) or getattr(before,k)!=getattr(named,k) for k in fields):raise ValueError('fixture dependency changed')
  raw=b''.join(chunks)
  if hashlib.sha256(raw).hexdigest()!=sha:raise ValueError('fixture dependency digest')
  return raw
 finally:os.close(fd)

loader_path=HERE/'verified_owner_loader.py'
loader_bytes=held_bytes(loader_path,'cec6e9506f29f07584ec5304c8deeb532a9d255be842b2faa55957c97a1f5c29')
verified_owner_loader=types.ModuleType('fixture_verified_owner_loader');verified_owner_loader.__file__=str(loader_path)
exec(compile(loader_bytes,str(loader_path),'exec'),verified_owner_loader.__dict__)
root_stat=os.stat(HERE,follow_symlinks=False)
union_owner,LOADED_BUNDLE=verified_owner_loader.load(HERE,{'device':root_stat.st_dev,'inode':root_stat.st_ino,'kind':'directory'})
source_freeze=sys.modules['source_freeze'];split_inventory=sys.modules['split_inventory']
GRAPH_PATH=SIBLING/'authenticated-adapter-successor-1'/'graph_observations.py'
GRAPH_BYTES=held_bytes(GRAPH_PATH,'c708c1bd87dd88a125644e02f8a1afcebdb568966b46d66a0de9f7e59df43da8')
CONSUMER_PATH=SIBLING/'adapter-readiness-expert-1'/'union_server_guarded.py'
CONSUMER_BYTES=held_bytes(CONSUMER_PATH,'3f96123f1a62ed427235c59f802452811522f62d5c5b4e5d84385c392a54a229')

class Inventory(unittest.TestCase):
 def test_fd_inventory_matches_shared_graph_row_digest(self):
  graph=types.ModuleType('fixture_graph_observations');graph.__file__=str(GRAPH_PATH)
  exec(compile(GRAPH_BYTES,str(GRAPH_PATH),'exec'),graph.__dict__)
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'a').mkdir();(root/'a').chmod(0o700)
   (root/'a'/'nested').write_bytes(b'x');(root/'a'/'nested').chmod(0o600)
   (root/'z').write_bytes(b'y');(root/'z').chmod(0o600);os.symlink('a',root/'link')
   members={'a':{'type':'directory','mode':0o700},
            'a/nested':{'type':'file','mode':0o600,'bytes':1,'sha256':hashlib.sha256(b'x').hexdigest()},
            'z':{'type':'file','mode':0o600,'bytes':1,'sha256':hashlib.sha256(b'y').hexdigest()},
            'link':{'type':'symlink','mode':os.lstat(root/'link').st_mode&0o7777,'target':'a'}}
   fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with mock.patch.object(split_inventory,'require_immutable'):
     _,actual=split_inventory.snapshot(fd,members)
    self.assertEqual(actual,graph.inventory(str(root)))
   finally:os.close(fd)
 def test_full_membership_rejects_extra_empty_directory_and_bytes_drift(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'dir').mkdir();(root/'dir').chmod(0o700)
   f=root/'dir'/'file';f.write_bytes(b'a');f.chmod(0o600)
   import hashlib
   entries={'dir':{'type':'directory','mode':0o700},
            'dir/file':{'type':'file','mode':0o600,'bytes':1,'sha256':hashlib.sha256(b'a').hexdigest()}}
   fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with mock.patch.object(split_inventory,'require_immutable'):
     observed,digest=split_inventory.snapshot(fd,entries)
     self.assertEqual(set(observed['entries']),set(entries));self.assertEqual(len(digest),64)
     (root/'extra').mkdir()
     with self.assertRaises(ValueError):split_inventory.snapshot(fd,entries)
     (root/'extra').rmdir();f.write_bytes(b'b')
     with self.assertRaises(ValueError):split_inventory.snapshot(fd,entries)
   finally:os.close(fd)
 def test_symlink_is_literal_and_extra_file_never_ignored(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);os.symlink('target',root/'link');fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   try:
    with mock.patch.object(split_inventory,'require_immutable'):
     mode=os.lstat(root/'link').st_mode&0o7777
     split_inventory.snapshot(fd,{'link':{'type':'symlink','mode':mode,'target':'target'}})
     with self.assertRaises(ValueError):split_inventory.snapshot(fd,{'link':{'type':'symlink','mode':mode,'target':'different'}})
   finally:os.close(fd)

class Unknown(unittest.TestCase):
 def test_partial_intent_retains_unknown_and_publishes_to_parent(self):
  obj=object.__new__(union_owner.UnionOwner);obj.intent=True;obj.created=False;obj.parentfd=3
  obj.state_lock=threading.RLock();obj.unknown_latched=False
  obj.lease=mock.Mock(nonce='a'*64)
  with mock.patch.object(union_owner,'durable') as durable:
   obj._unknown(OSError('partial'))
  self.assertEqual(obj.state,'UNKNOWN_RETAINED');self.assertEqual(durable.call_args.args[1],'SOURCE-UNKNOWN-'+'a'*64+'.json')
 def test_failed_unknown_publication_is_explicit(self):
  obj=object.__new__(union_owner.UnionOwner);obj.intent=True;obj.created=False;obj.parentfd=3
  obj.state_lock=threading.RLock();obj.unknown_latched=False
  obj.lease=mock.Mock(nonce='a'*64)
  with mock.patch.object(union_owner,'durable',side_effect=OSError('fsync')):
   with self.assertRaises(union_owner.UnknownPublicationError):obj._unknown(ValueError('original'))
  self.assertEqual(obj.state,'UNKNOWN_RETAINED')
 def test_revalidation_requires_two_matching_real_observations(self):
  obj=object.__new__(union_owner.UnionOwner)
  first={'/work':{'path':'/w','identity':{'device':1,'inode':2,'kind':'directory'},'inventory_sha256':'a'*64}}
  second={'/work':{'path':'/w','identity':{'device':1,'inode':3,'kind':'directory'},'inventory_sha256':'a'*64}}
  obj.lease=mock.Mock();obj._local_targets=mock.Mock(side_effect=[first,second])
  with self.assertRaises(ValueError):obj._revalidate()
  self.assertEqual(obj._local_targets.call_count,2)

class ImmutableActions(unittest.TestCase):
 def test_guard_loss_prevents_flag_mutation(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);root.chmod(0o700);fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
   doc={'base_root_mode':'0700','base_members':[],'additions':[]}
   try:
    with mock.patch.object(source_freeze.fcntl,'ioctl') as ioctl:
     with self.assertRaises(ValueError):source_freeze.freeze_union(fd,doc,lambda:False,lambda row:None)
     ioctl.assert_not_called()
   finally:os.close(fd)

class LoaderBinding(unittest.TestCase):
 def test_pinned_bytes_and_named_identity_reject_replacement(self):
  import hashlib
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);path=root/'module.py';path.write_bytes(b'fixture')
   rootfd=verified_owner_loader.open_dir(root)
   fd,raw,identity=verified_owner_loader.open_bound(rootfd,'module.py',hashlib.sha256(b'fixture').hexdigest())
   try:
    rootst=os.fstat(rootfd)
    bundle=verified_owner_loader.PinnedBundle([rootfd],[(rootfd,'module.py',fd,identity,hashlib.sha256(raw).hexdigest())],[(str(root),rootfd,(rootst.st_dev,rootst.st_ino))])
    self.assertIs(bundle.verify(),True)
    path.rename(root/'saved');path.write_bytes(b'fixture')
    with self.assertRaises(ValueError):bundle.verify()
   finally:os.close(fd);os.close(rootfd)

class FramedLease(unittest.TestCase):
 def test_operation_root_commitment_binds_identity_and_lease(self):
  root={'device':1,'inode':2,'kind':'directory'}
  original=union_owner.operation_commitment('b'*64,'a'*64,root)
  self.assertNotEqual(original,union_owner.operation_commitment('b'*64,'a'*64,dict(root,inode=3)))
  self.assertNotEqual(original,union_owner.operation_commitment('c'*64,'a'*64,root))
  self.assertNotEqual(original,union_owner.operation_commitment('b'*64,'d'*64,root))
 def test_fresh_observation_and_cross_bound_request_required(self):
  client=object.__new__(union_owner.LeaseChannel);client.protocol=union_owner.read_protocol()
  client.pid=1;client.birth='1';client.nonce='a'*64;client.lease_sha='b'*64;client.custody_sha='c'*64
  client.deadline_boot=100;client.seq=0;client.sock=mock.Mock();client._peer=mock.Mock();client._clocks=mock.Mock()
  observed={'operation':'union-lease-check','lease_sha256':client.lease_sha,'custody_sha256':client.custody_sha,'nonce':client.nonce,'targets':{}}
  payload={'observation':observed}
  response={'status':'HELD','observed_boot_ns':10_050_000_000,'request_sha256':union_owner.digest(payload),'observation_sha256':union_owner.digest(observed)}
  envelope=client.protocol['envelope']('union','union-lease-check',client.nonce,1,client.lease_sha,client.custody_sha,response)
  with mock.patch.dict(client.protocol,{'send':mock.Mock(),'receive':mock.Mock(return_value=envelope)}),mock.patch.object(union_owner.time,'clock_gettime_ns',side_effect=[10_000_000_000,10_100_000_000]):
   self.assertIs(client.request('union-lease-check',{}),True)
  client.seq=0;response['observed_boot_ns']=1
  stale=client.protocol['envelope']('union','union-lease-check',client.nonce,1,client.lease_sha,client.custody_sha,response)
  with mock.patch.dict(client.protocol,{'send':mock.Mock(),'receive':mock.Mock(return_value=stale)}),mock.patch.object(union_owner.time,'clock_gettime_ns',side_effect=[10_000_000_000,10_100_000_000]):
   with self.assertRaises(ValueError):client.request('union-lease-check',{})

class ReadyAndEpoch(unittest.TestCase):
 def test_real_receipt_producer_matches_actual_consumer_mode(self):
  import ast,hashlib,stat
  parent=CONSUMER_PATH
  raw=CONSUMER_BYTES
  self.assertEqual(hashlib.sha256(raw).hexdigest(),'3f96123f1a62ed427235c59f802452811522f62d5c5b4e5d84385c392a54a229')
  tree=ast.parse(raw,str(parent))
  fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_receipt_meta')
  env={'stat':stat};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(parent),'exec'),env)
  with tempfile.TemporaryDirectory() as tmp:
   parentfd=os.open(tmp,os.O_RDONLY|os.O_DIRECTORY)
   path=Path(tmp)/'receipt';data=b'{}\n';path.write_bytes(data);path.chmod(0o600)
   real_fstat=os.fstat
   class RootStat:
    def __init__(self,st):self.st=st
    def __getattr__(self,name):return 0 if name=='st_uid' else getattr(self.st,name)
   try:
    with mock.patch.object(union_owner.os,'fstat',side_effect=lambda fd:RootStat(real_fstat(fd))):
     actual=union_owner.receipt_identity(parentfd,'receipt',hashlib.sha256(data).hexdigest(),data)
    expected=env['_receipt_meta'](RootStat(path.stat()))
    self.assertEqual({k:v for k,v in actual.items() if k!='sha256'},expected)
    self.assertEqual(actual['mode'],0o600)
   finally:os.close(parentfd)
 def owner(self):
  obj=object.__new__(union_owner.UnionOwner);obj.state='PREPARING';obj.ready=False
  obj.io_lock=threading.Lock();obj.state_lock=threading.RLock();obj.unknown_latched=False
  obj.lease=mock.Mock(spec=union_owner.LeaseChannel)
  obj.lease.nonce='a'*64;obj.lease.lease_sha='b'*64;obj.lease.custody_sha='c'*64
  obj.lease.assert_live.return_value=True
  obj.lease.seq=0
  obj.lease.observation.side_effect=lambda op,rows:{'operation':op,'lease_sha256':'b'*64,'custody_sha256':'c'*64,'nonce':'a'*64,'targets':rows}
  obj._revalidate=mock.Mock(return_value=True);obj._local_targets=mock.Mock(return_value={'/work':{'identity':'fixture'}})
  return obj
 def result(self):
  return {'status':'PROVISIONAL_HELD_SOURCE_ONLY','nonce':'a'*64,'lease_sha256':'b'*64,
          'custody_sha256':'c'*64,'targets':{'/work':{'identity':'fixture'}}}
 def test_paused_prepare_never_commits_until_post_accept_checks(self):
  obj=self.owner();result=self.result();entered=threading.Event();resume=threading.Event();events=[];errors=[]
  obj._revalidate.side_effect=lambda:events.append('revalidate') or True
  def send(operation,rows,**kwargs):
   obj.lease.seq+=1
   if operation=='union-owner-prepare':
    self.assertEqual(obj.state,'PREPARING');self.assertFalse(obj.ready)
    entered.set();self.assertTrue(resume.wait(2));events.append('accepted')
    return {'status':'ACCEPTED','fixture':'accept'}
   self.assertEqual(operation,'union-owner-commit');self.assertEqual(obj.lease.seq,2)
   self.assertEqual(obj.state,'HELD');self.assertTrue(obj.ready)
   self.assertGreaterEqual(obj.lease.assert_live.call_count,2)
   self.assertEqual(set(kwargs['transcript']),{'prepare_request_sha256','prepare_accept_sha256'})
   events.append('commit');return True
  obj.lease.request.side_effect=send
  def run():
   try:obj._announce_ready(4,result,'SOURCE-SUCCESS-'+'a'*64+'.json','d'*64)
   except BaseException as e:errors.append(e)
  with mock.patch.object(union_owner,'receipt_identity',return_value={'inode':9}),mock.patch.object(union_owner,'ident',return_value={'device':1,'inode':2,'kind':'directory'}),mock.patch.object(union_owner,'proc_birth',return_value='77'):
   thread=threading.Thread(target=run);thread.start();self.assertTrue(entered.wait(2))
   self.assertFalse(obj.ready);self.assertNotIn('commit',events)
   resume.set();thread.join(2);self.assertFalse(thread.is_alive())
  self.assertEqual(errors,[]);self.assertEqual(events,['revalidate','accepted','commit']);self.assertTrue(obj.ready)
 def test_post_accept_failure_never_commits_and_unknown_is_sticky(self):
  obj=self.owner();obj.intent=True;obj.created=True;obj.parentfd=4
  obj._local_targets.side_effect=[self.result()['targets'],ValueError('drift after acceptance')]
  def send(operation,rows,**kwargs):
   obj.lease.seq+=1
   self.assertEqual(operation,'union-owner-prepare');return {'status':'ACCEPTED'}
  obj.lease.request.side_effect=send
  with mock.patch.object(union_owner,'receipt_identity',return_value={'inode':9}),mock.patch.object(union_owner,'ident',return_value={'device':1,'inode':2,'kind':'directory'}),mock.patch.object(union_owner,'proc_birth',return_value='77'),mock.patch.object(union_owner,'durable'):
   try:obj._announce_ready(4,self.result(),'SOURCE-SUCCESS-'+'a'*64+'.json','d'*64)
   except ValueError as exc:obj._unknown(exc)
   else:self.fail('expected post-accept failure')
  self.assertEqual(obj.lease.request.call_count,1);self.assertEqual(obj.state,'UNKNOWN_RETAINED')
  self.assertGreaterEqual(obj.lease.assert_live.call_count,1)
  self.assertFalse(obj.ready);self.assertTrue(obj.unknown_latched);obj.lease.revoke.assert_called_once()
 def test_ready_missing_durable_receipt_never_sends(self):
  obj=self.owner()
  with mock.patch.object(union_owner,'receipt_identity',side_effect=FileNotFoundError):
   with self.assertRaises(FileNotFoundError):obj._announce_ready(4,self.result(),'SOURCE-SUCCESS-'+'a'*64+'.json','d'*64)
  self.assertEqual(obj.state,'PREPARING');self.assertFalse(obj.ready);obj.lease.request.assert_not_called()
 def test_unknown_revokes_existing_readiness(self):
  obj=self.owner();obj.state='HELD';obj.ready=True;obj.intent=True;obj.created=True;obj.parentfd=4
  with mock.patch.object(union_owner,'durable'):
   obj._unknown(OSError('lease lost'))
  self.assertEqual(obj.state,'UNKNOWN_RETAINED');self.assertFalse(obj.ready);obj.lease.revoke.assert_called_once()
 def test_epoch_rejects_named_inode_change_without_full_rehash(self):
  obj=self.owner();obj.freeze=mock.Mock();obj.freeze.epoch_check=mock.Mock()
  obj.held_paths={'/p':(3,())};good={'device':1,'inode':2,'kind':'directory'}
  obj.epoch_paths={'/p':(good,8)};obj.targets={t:('/x',5,{},True) for t in union_owner.SPLITS}
  obj.lease.assert_live=mock.Mock(return_value=True)
  with mock.patch.object(union_owner,'ident',side_effect=[good,dict(good,inode=3)]),mock.patch.object(union_owner,'mount_id',return_value=8),mock.patch.object(union_owner.m,'_revalidate_destination_parent'),mock.patch.object(union_owner.m,'_absolute_dir',return_value=4),mock.patch.object(union_owner.os,'close'),mock.patch.object(union_owner,'require_immutable'):
   with self.assertRaises(ValueError):obj._epoch_guard()
  obj._local_targets.assert_not_called()

if __name__=='__main__':unittest.main(verbosity=2)
