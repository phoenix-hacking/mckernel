"""Pure fake-backend operation ownership tests; no child or physical process."""
import unittest
import custody_protocol as c
from scoped_owner import OperationOwner, scoped_watchdog_tick

class Fake:
 def __init__(self):
  self.parent={'pid':10,'birth':100,'ppid':2,'pgid':10,'sid':2}
  self.child={'pid':11,'birth':101,'ppid':10,'pgid':10,'sid':2}
  self.nonce='a'*32;self.events=[c.make_event(self.nonce,'PARENT_READY',self.parent,None),c.make_event(self.nonce,'IMAGE_READY',self.parent,self.child)]
  self.calls=[];self.clock=1;self.stop=False;self.fail={};self.signals=[]
 def get(self,name,default=True):
  self.calls.append(name)
  value=self.fail.get(name,default)
  if isinstance(value,BaseException):raise value
  return value
 def now(self):return self.clock
 def stop_state(self):return self.stop
 def current_admission(self):return self.get('admission')
 def watchdog_live(self):return self.get('watchdog_live')
 def fork_held_parent(self,deadline):return self.get('fork',{'parent':self.parent,'pinned':'pinned-handle'})
 def parent_fork_binding(self,parent):return self.get('parent_binding')
 def parent_go_control(self,parent):return self.get('parent_go_control')
 def publish_parent_start(self,parent):return self.get('parent_start')
 def watchdog_adopt_parent(self,parent,pinned,deadline):return self.get('watchdog_parent')
 def prepare_and_verify_release(self,parent,deadline):return self.get('release')
 def release_parent_go(self,parent):return self.get('parent_go')
 def receive_event(self,deadline):return self.get('event',self.events.pop(0))
 def image_fork_binding(self,parent,child):return self.get('image_binding')
 def held_go_control(self,phase,parent,child):return self.get('held_'+phase)
 def observe_owned_group(self,parent,child):
  ids={r['pid']:r for r in (parent,child) if r is not None}
  return self.get('observe',(ids,sorted(ids)))
 def publish_custody(self,record):return self.get('publish_'+record['event']['phase'])
 def watchdog_adopt(self,record,deadline):return self.get('watchdog_'+record['event']['phase'])
 def send_ack(self,ack):return self.get('send_ack')
 def read_bound_held_image(self,parent,deadline):return self.get('bound_image',self.child)
 def direct_wait_parent(self,parent,deadline):return self.get('wait',{'pid':10,'exit_status':0,'reaped':True})
 def streams_closed_and_captured(self):return self.get('streams')
 def descendant_retirement_proven(self,parent,child):return self.get('descendant_retirement')
 def final_evidence_durable(self,joined):return self.get('final_evidence')
 def retain_unknown(self,status,error,parent,child):self.calls.append(('retain',status,error,parent,child))
 def record_unknown(self,reason):self.calls.append(('unknown',reason))
 def pinned_identity_is_exact(self,pinned):return self.get('pinned_exact')
 def signal_exact_pinned(self,pinned):self.signals.append(pinned)

class OwnerTests(unittest.TestCase):
 def run_owner(self,f):return OperationOwner(f,f.nonce,50).run()
 def test_success_requires_every_positive_binding_and_wait(self):
  f=Fake();result=self.run_owner(f)
  self.assertEqual(result['status'],'CANDIDATE_OBSERVATION')
  for x in ('parent_binding','watchdog_parent','release','parent_go','image_binding','held_IMAGE_READY','wait','streams','descendant_retirement','final_evidence'):
   self.assertIn(x,f.calls)
  self.assertLess(f.calls.index('publish_IMAGE_READY'),f.calls.index('watchdog_IMAGE_READY'))
  self.assertLess(f.calls.index('watchdog_IMAGE_READY'),f.calls.index('send_ack',f.calls.index('watchdog_IMAGE_READY')))
 def test_repeat_run_preserves_prior_unknown_and_never_reforks(self):
  f=Fake();f.fail['fork']=OSError('uncertain fork');owner=OperationOwner(f,f.nonce,50)
  first=owner.run();retained=[x for x in f.calls if isinstance(x,tuple) and x[0]=='retain']
  second=owner.run()
  self.assertEqual(first['status'],'UNKNOWN_OWNERSHIP_RETAINED')
  self.assertEqual(second['status'],first['status']);self.assertEqual(second['error'],'OWNER_ALREADY_USED')
  self.assertEqual(owner.state,'UNKNOWN_OWNERSHIP_RETAINED');self.assertEqual(f.calls.count('fork'),1)
  self.assertEqual([x for x in f.calls if isinstance(x,tuple) and x[0]=='retain'],retained)
 def test_repeat_run_preserves_pre_fork_denial_and_candidate(self):
  for denial in (False,True):
   f=Fake()
   if denial:f.fail['admission']=False
   owner=OperationOwner(f,f.nonce,50);first=owner.run();before=list(f.calls);second=owner.run()
   self.assertEqual(second['status'],first['status']);self.assertEqual(f.calls,before)
 def test_reentrant_run_cannot_repeat_inflight_fork(self):
  f=Fake();owner=OperationOwner(f,f.nonce,50);inner=[]
  def fork(deadline):
   f.calls.append('fork');inner.append(owner.run());raise OSError('unknown fork')
  f.fork_held_parent=fork
  first=owner.run()
  self.assertEqual(first['status'],'UNKNOWN_OWNERSHIP_RETAINED')
  self.assertEqual(inner[0]['status'],'FORK_OUTCOME_UNCERTAIN');self.assertEqual(f.calls.count('fork'),1)
 def test_no_admission_means_no_fork(self):
  f=Fake();f.fail['admission']=False
  self.assertEqual(self.run_owner(f)['status'],'DENIED_BEFORE_FORK');self.assertNotIn('fork',f.calls)
 def test_fork_exception_is_unknown_even_without_identity(self):
  f=Fake();f.fail['fork']=OSError('uncertain fork')
  self.assertEqual(self.run_owner(f)['status'],'UNKNOWN_OWNERSHIP_RETAINED')
  self.assertIsNone(next(x for x in f.calls if isinstance(x,tuple) and x[0]=='retain')[3]);self.assertEqual(f.signals,[])
 def test_failed_binding_or_watchdog_prevents_parent_go(self):
  for key in ('parent_binding','parent_go_control','parent_start','watchdog_parent','release'):
   f=Fake();f.fail[key]=False
   with self.subTest(key=key):
    self.assertEqual(self.run_owner(f)['status'],'UNKNOWN_OWNERSHIP_RETAINED');self.assertNotIn('parent_go',f.calls)
 def test_held_image_or_watchdog_failure_never_sends_image_ack(self):
  for key in ('image_binding','held_IMAGE_READY','publish_IMAGE_READY','watchdog_IMAGE_READY'):
   f=Fake();f.fail[key]=False
   with self.subTest(key=key):
    self.assertEqual(self.run_owner(f)['status'],'UNKNOWN_OWNERSHIP_RETAINED')
    self.assertEqual(f.calls.count('send_ack'),1)
 def test_event_child_cannot_replace_independently_bound_child(self):
  f=Fake();f.fail['bound_image']=dict(f.child,birth=999)
  self.assertEqual(self.run_owner(f)['status'],'UNKNOWN_OWNERSHIP_RETAINED');self.assertEqual(f.calls.count('send_ack'),1)
 def test_missing_wait_stream_or_retirement_never_promotes(self):
  for key,value in (('wait',{'pid':10,'exit_status':0,'reaped':False}),('wait',{'pid':10,'exit_status':True,'reaped':True}),('streams',False),('descendant_retirement',False),('final_evidence',False)):
   f=Fake();f.fail[key]=value
   with self.subTest(key=key,value=value):self.assertEqual(self.run_owner(f)['status'],'UNKNOWN_OWNERSHIP_RETAINED')
 def test_stop_deadline_or_unknown_stop_prevents_fork(self):
  for attr,value in (('stop',True),('stop',None),('clock',50)):
   f=Fake();setattr(f,attr,value)
   with self.subTest(attr=attr,value=value):self.assertEqual(self.run_owner(f)['status'],'DENIED_BEFORE_FORK');self.assertNotIn('fork',f.calls)
 def test_watchdog_signals_only_exact_pinned_handle_and_retains_unknown(self):
  for pinned,exact,expected in (('handle',True,['handle']),('handle',False,[]),(None,True,[])):
   f=Fake();f.clock=50;f.fail['pinned_exact']=exact
   with self.subTest(pinned=pinned,exact=exact):
    self.assertEqual(scoped_watchdog_tick(f,50,pinned),'UNKNOWN_OWNERSHIP_RETAINED');self.assertEqual(f.signals,expected);self.assertTrue(any(isinstance(x,tuple) and x[0]=='unknown' for x in f.calls))
 def test_watchdog_healthy_tick_does_not_signal(self):
  f=Fake();self.assertEqual(scoped_watchdog_tick(f,50,'handle'),'CONTINUE');self.assertEqual(f.signals,[])

if __name__=='__main__':unittest.main(verbosity=2)
