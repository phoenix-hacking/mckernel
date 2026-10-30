#!/usr/bin/env python3
"""Synthetic descriptors and proofs only; never reads proc or creates a process."""
import copy,importlib.util,pathlib,types,unittest
from unittest.mock import patch
p=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('inner',p/'inner_retirement.successor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
anchor={'pid':10,'starttime':'100','pgrp':10,'session':10};root={'pid':11,'starttime':'200','pgrp':11,'session':11}
def row(pid,ppid,pgrp,session,start):
 raw=f'{pid} (fake) '+ ' '.join(['S',str(ppid),str(pgrp),str(session)]+['0']*15+[str(start)])
 return m.row(pid,raw)
def proof():
 one=row(1,0,1,1,1);a=row(10,1,10,10,100);r=row(11,10,11,11,200);mount=['1 2 0:1 / /proc rw - proc proc rw']
 pre={'phase':'pre_wait','boot_id':'boot','rows':[one,a,r],'errors':[],'tree':[11],'group':[11],'observer_uid':1000,'proc_mountinfo':mount}
 post={'phase':'post_wait','boot_id':'boot','rows':[one,a],'errors':[],'tree':[],'group':[],'observer_uid':1000,'proc_mountinfo':mount}
 def obs(n):return {'boot_id':'boot','observer':anchor,'monotonic_ns':n,'subreaper':{'get_rc':0,'value':1},'sigchld':0,'tasks':[{'tid':10,'raw_children':''}],'waitid':{'state':'ECHILD','errno':10}}
 return {'schema':'mckernel.process-retirement.v2','boot_id':'boot','identity':root,'known_identities':[root],'snapshots':[pre,post,post],'direct_wait':{'joined':True,'exit_code':0},'forced':False,'privileged_wrapper':False,'uncertainties':[],'retirement_proven':True,'containment':{'schema':'mckernel.subreaper-closure.v1','pre_launch':obs(100),'post_join':[obs(200),obs(300)]}}
def binding():return {'operation':m.INNER_OPERATION,'cid':'c'*64,'nonce':'n'*32,'profile_sha256':'a'*64,'driver_sha256':'b'*64,'observer_sha256':'d'*64,'host_authority_sha256':'f'*64,'caps_authority_sha256':'9'*64,'deadline_caps':{'utc':2000.,'boot':200.,'monotonic':100.},'boot_id':'boot','self_identity':anchor,'views':{'pid':[1,2],'mount':[3,4],'proc':[5,6]}}
# Nonce is hexadecimal, not a literal server identity.
def bnd():b=binding();b['nonce']='e'*32;return b
fds={'pid':20,'mount':21,'proc':22};stats={20:(1,2),21:(3,4),22:(5,6)};paths={'/proc/self/ns/pid':(1,2),'/proc/self/ns/mnt':(3,4),'/proc':(5,6)}
def st(pair):return types.SimpleNamespace(st_dev=pair[0],st_ino=pair[1])
class Tests(unittest.TestCase):
 def test_actual_predecessor_predicate_positive_and_negatives(self):
  good=proof();self.assertTrue(m.validate_proof(good))
  for kind in ('unknown','forced','orphan','waitable','order','anchor','no_final','hidden'):
   x=copy.deepcopy(good)
   if kind=='unknown':x['uncertainties']=['read failed']
   if kind=='forced':x['forced']=True
   if kind=='orphan':x['containment']['post_join'][0]['tasks'][0]['raw_children']='44 '
   if kind=='waitable':x['containment']['post_join'][1]['waitid']={'state':'WAITABLE_CHILD','errno':0}
   if kind=='order':x['containment']['post_join'][1]['monotonic_ns']=150
   if kind=='anchor':x['containment']['post_join'][0]['observer']['starttime']='changed'
   if kind=='no_final':x['snapshots'].pop()
   if kind=='hidden':x['snapshots'][0]['proc_mountinfo']=['1 2 0:1 / /proc rw,hidepid=2 - proc proc rw']
   with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError,IndexError)):m.validate_proof(x)
 def test_disabled_and_unbound_host_fail_before_any_observation(self):
  x=m.InnerConfigureOwner(bnd(),fds)
  with patch.object(m,'enable_subreaper',side_effect=AssertionError('must not run')):
   with self.assertRaisesRegex(ValueError,'disabled'):x.launch(['x'],'/',{},None,None)
   with patch.object(m,'INNER_DISABLED',False):
    with self.assertRaisesRegex(ValueError,'unbound'):x.launch(['x'],'/',{},None,None)
 def mocks(self,exchange,proof_obj=None):
  obs=[{'observer':anchor,'boot_id':'boot','monotonic_ns':100},{'observer':anchor,'boot_id':'boot','monotonic_ns':101}]
  class Child:
   pid=11
   def wait(self,timeout):return 0
  class Proof:
   def __init__(self,proc,privileged_wrapper,pre_launch):self.data={'identity':root,'uncertainties':[]}
   def observe(self,phase):pass
   def joined(self,code):return copy.deepcopy(proof_obj if proof_obj is not None else proof())
  return [patch.object(m,'INNER_DISABLED',False),patch.object(m,'_inner_source_sha256',return_value='d'*64),patch.object(m,'HOST_EXCHANGE',exchange),patch.object(m.os,'fstat',side_effect=lambda fd:st(stats[fd])),patch.object(m.os,'stat',side_effect=lambda path:st(paths[str(path)])),patch.object(m.os,'getpid',return_value=10),patch.object(m,'boot_id',return_value='boot'),patch.object(m,'current_identity',return_value=anchor),patch.object(m,'enable_subreaper',return_value=None),patch.object(m,'prepare_launch',side_effect=obs),patch.object(m.subprocess,'Popen',return_value=Child()),patch.object(m,'ProcessProof',Proof),patch.object(m.time,'monotonic',return_value=1.0),patch.object(m.time,'time',return_value=1000.0),patch.object(m.time,'clock_gettime',return_value=100.0)]
 def run_patches(self,patches,fn):
  from contextlib import ExitStack
  with ExitStack() as stack:
   for item in patches:stack.enter_context(item)
   return fn()
 def test_mocked_ready_and_proof_gates(self):
  phases=[]
  def exchange(phase,payload):phases.append(phase);return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake/cmake'],'/fake',{},None,None);return x.wait(10)
  got=self.run_patches(self.mocks(exchange),run);self.assertEqual(got['identity']['pid'],11);self.assertEqual(phases,['READY','PROOF']);self.assertEqual(x.state,'PROOF_ACKED_SOURCE_ONLY')
 def test_ack_mismatch_or_namespace_change_retains_unknown(self):
  def bad(phase,payload):return {'phase':phase,'payload':payload,'decision':'NACK','authority_sha256':'f'*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  with self.assertRaises(ValueError):self.run_patches(self.mocks(bad),lambda:x.launch(['/fake'],'/fake',{},None,None))
  self.assertEqual(x.state,'UNKNOWN')
  x=m.InnerConfigureOwner(bnd(),fds);x.binding['views']['pid']=[9,9]
  with self.assertRaises(ValueError):self.run_patches(self.mocks(bad),lambda:x.launch(['/fake'],'/fake',{},None,None))
  self.assertEqual(x.state,'UNKNOWN')
 def test_unfinished_or_failed_closure_blocks_host_proof_ack(self):
  phases=[]
  def exchange(phase,payload):phases.append(phase);return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  bad=proof();bad['containment']['post_join'][0]['tasks'][0]['raw_children']='44 '
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(10)
  with self.assertRaises(ValueError):self.run_patches(self.mocks(exchange,bad),run)
  self.assertEqual(x.state,'UNKNOWN');self.assertEqual(phases,['READY'])
 def test_host_authority_drift_blocks_completion(self):
  def exchange(phase,payload):return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':('f' if phase=='READY' else 'a')*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(10)
  with self.assertRaisesRegex(ValueError,'authority changed'):self.run_patches(self.mocks(exchange),run)
  self.assertEqual(x.state,'UNKNOWN')
 def test_source_hash_mismatch_blocks_prelaunch(self):
  def exchange(phase,payload):return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  x=m.InnerConfigureOwner(bnd(),fds);x.binding['observer_sha256']='a'*64
  with self.assertRaisesRegex(ValueError,'source binding'):self.run_patches(self.mocks(exchange),lambda:x.launch(['/fake'],'/fake',{},None,None))
  self.assertEqual(x.state,'UNKNOWN')
 def test_expired_wait_retains_unknown(self):
  def exchange(phase,payload):return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(1)
  with self.assertRaisesRegex(ValueError,'deadline'):self.run_patches(self.mocks(exchange),run)
  self.assertEqual(x.state,'UNKNOWN')
 def test_mismatched_direct_wait_proof_blocks_host_proof_ack(self):
  phases=[]
  def exchange(phase,payload):phases.append(phase);return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  bad=proof();bad['direct_wait']['exit_code']=5
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(10)
  with self.assertRaisesRegex(ValueError,'proof owner/wait'):self.run_patches(self.mocks(exchange,bad),run)
  self.assertEqual(x.state,'UNKNOWN');self.assertEqual(phases,['READY'])
 def test_unexpected_initial_authority_prevents_spawn(self):
  def exchange(phase,payload):return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'a'*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  with self.assertRaisesRegex(ValueError,'authority differs'):self.run_patches(self.mocks(exchange),lambda:x.launch(['/fake'],'/fake',{},None,None))
  self.assertEqual(x.state,'UNKNOWN');self.assertIsNone(x.process)
 def test_deadline_nan_infinity_widen_and_unbound_rejected(self):
  for name,value in [('utc',float('nan')),('boot',float('inf')),('monotonic',float('inf')),('utc',m.MAX_UTC+1),('monotonic',None),('boot',True)]:
   b=bnd();b['deadline_caps'][name]=value
   with self.subTest(name=name,value=value),self.assertRaises((ValueError,TypeError)):m._check_deadlines(b)
  for request in (float('nan'),float('inf'),-1,101):
   with self.subTest(request=request),patch.object(m.time,'time',return_value=1000.),patch.object(m.time,'clock_gettime',return_value=100.),patch.object(m.time,'monotonic',return_value=1.),self.assertRaises(ValueError):m._check_deadlines(bnd(),request)
 def test_callback_mutation_of_proof_is_rejected(self):
  phases=[]
  def exchange(phase,payload):
   phases.append(phase)
   if phase=='PROOF':payload['proof']['direct_wait']['exit_code']=9
   return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  x=m.InnerConfigureOwner(bnd(),fds)
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(10)
  with self.assertRaisesRegex(ValueError,'mutated payload'):self.run_patches(self.mocks(exchange),run)
  self.assertEqual(x.state,'UNKNOWN');self.assertEqual(phases,['READY','PROOF'])
 def test_callback_mutation_of_live_binding_is_rejected(self):
  x=m.InnerConfigureOwner(bnd(),fds)
  def exchange(phase,payload):
   if phase=='PROOF':x.binding['views']['pid']=[9,9]
   return {'phase':phase,'payload':payload,'decision':'ACK','authority_sha256':'f'*64}
  def run():x.launch(['/fake'],'/fake',{},None,None);return x.wait(10)
  with self.assertRaises(ValueError):self.run_patches(self.mocks(exchange),run)
  self.assertEqual(x.state,'UNKNOWN')
if __name__=='__main__':unittest.main(verbosity=2)
