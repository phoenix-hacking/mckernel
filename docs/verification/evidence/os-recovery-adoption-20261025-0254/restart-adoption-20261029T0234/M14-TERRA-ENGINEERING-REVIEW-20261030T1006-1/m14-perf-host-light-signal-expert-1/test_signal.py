#!/usr/bin/env python3
"""Synthetic gates and fake children only; no real proc or process observer."""
import copy,hashlib,importlib.util,json,pathlib,signal,unittest
from contextlib import ExitStack
from unittest.mock import patch
p=pathlib.Path(__file__).parent;spec=importlib.util.spec_from_file_location('owner',p/'perf_owner.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
anchor={'pid':10,'starttime':'100','pgrp':10,'session':10}
def row(pid,ppid,pgrp,session,start):
 return m.row(pid,f'{pid} (synthetic) '+' '.join(['S',str(ppid),str(pgrp),str(session)]+['0']*15+[str(start)]))
def proof(pid,code):
 root={'pid':pid,'starttime':'200','pgrp':pid,'session':pid};one=row(1,0,1,1,1);a=row(10,1,10,10,100);c=row(pid,10,pid,pid,200);mount=['1 2 0:1 / /proc rw - proc proc rw']
 pre={'phase':'pre_wait','boot_id':'boot','rows':[one,a,c],'errors':[],'tree':[pid],'group':[pid],'observer_uid':1000,'proc_mountinfo':mount};post={'phase':'post_wait','boot_id':'boot','rows':[one,a],'errors':[],'tree':[],'group':[],'observer_uid':1000,'proc_mountinfo':mount}
 def obs(n):return {'boot_id':'boot','observer':anchor,'monotonic_ns':n,'subreaper':{'get_rc':0,'value':1},'sigchld':0,'tasks':[{'tid':10,'raw_children':''}],'waitid':{'state':'ECHILD','errno':10}}
 return {'schema':'mckernel.process-retirement.v2','boot_id':'boot','identity':root,'known_identities':[root],'snapshots':[pre,post,post],'direct_wait':{'joined':True,'exit_code':code},'forced':False,'privileged_wrapper':False,'uncertainties':[],'retirement_proven':True,'containment':{'schema':'mckernel.subreaper-closure.v1','pre_launch':obs(100),'post_join':[obs(200),obs(300)]}}
def binding():return {'phases':[{'phase':'perf_compile','argv':['/fake/compiler','--pinned'],'cwd':'/fake','env':{}},{'phase':'perf_fixture','argv':['/fake/fixture'],'cwd':'/fake','env':{}}],'deadline_caps':{'utc':2000.,'boot':200.,'monotonic':100.},'deadline_mono':10.}
def digest(b):return hashlib.sha256(m._canon(b)).hexdigest()
streams={'perf_compile':(None,None),'perf_fixture':(None,None)}
class Tests(unittest.TestCase):
 def test_source_disabled(self):
  with patch.object(m,'enable_subreaper',side_effect=AssertionError('real proc forbidden')):
   with self.assertRaisesRegex(ValueError,'disabled'):m.PerfLightOwner().run(streams)
 def invoke(self,kind):
  x=m.PerfLightOwner();b=binding();calls=[];children=[];reentry=[];mask=set()
  def sigmask(how,signals):
   previous=set(mask)
   if how==signal.SIG_BLOCK:mask.update(signals)
   else:mask.clear();mask.update(signals)
   calls.append(('mask',how,frozenset(signals)))
   return previous
  class Child:
   def __init__(self,pid):self.pid=pid;self.waits=0
   def wait(self,timeout):self.waits+=1;return 0
  def pre():
   if kind=='stop_after_pre':x._signal(signal.SIGTERM,None)
   return {'synthetic':True}
  def popen(argv,**kw):
   assert mask==set(m.PERF_STOP_SIGNALS)
   calls.append(('spawn',argv));assert callable(kw['preexec_fn'])
   if kind=='restore_child_mask':
    kw['preexec_fn']();assert not mask;calls.append(('child-mask-restored',));mask.update(m.PERF_STOP_SIGNALS)
   if kind=='signal_during_spawn':x._signal(signal.SIGTERM,None)
   c=Child(11+len(children));children.append(c);return c
  class Proof:
   def __init__(self,child,privileged_wrapper,pre_launch):
    assert mask==set(m.PERF_STOP_SIGNALS);calls.append(('identity',child.pid));self.child=child
    if kind=='proof_failure':raise RuntimeError('synthetic proof failure')
    self.data={'identity':{'pid':child.pid,'starttime':'200'},'uncertainties':[]}
   def observe(self,phase):pass
   def joined(self,code):return proof(self.child.pid,code)
  def authority(provided):
   if kind=='authority_false':return False
   if kind=='authority_none':return None
   if kind=='reentrant':
    try:x.run(streams)
    except BaseException as e:reentry.append(str(e))
   if kind=='mutate_profile':provided['phases'][0]['argv'].append('--unexpected')
   return True
  def watchdog(provided):
   return None if kind=='watchdog_none' else False if kind=='watchdog_false' else True
  if kind=='bad_deadline':b['deadline_mono']=float('nan')
  if kind=='widen_deadline':b['deadline_mono']=101.
  if kind=='late_utc':b['deadline_caps']['utc']=m.PERF_MAX_UTC+1
  patches=[patch.object(m,'PERF_LIGHT_DISABLED',False),patch.object(m,'PERF_LIGHT_BINDING',b),patch.object(m,'PERF_LIGHT_BINDING_SHA256',digest(b) if kind!='bad_deadline' else 'f'*64),patch.object(m,'PERF_LIGHT_AUTHORITY',authority),patch.object(m,'PERF_LIGHT_WATCHDOG',watchdog),patch.object(m.signal,'signal',return_value=signal.SIG_DFL),patch.object(m.signal,'pthread_sigmask',side_effect=sigmask),patch.object(m.signal,'sigpending',return_value={signal.SIGTERM} if kind=='pending_before' else set()),patch.object(m,'enable_subreaper',return_value=None),patch.object(m,'prepare_launch',side_effect=pre),patch.object(m.subprocess,'Popen',side_effect=popen),patch.object(m,'ProcessProof',Proof),patch.object(m.time,'time',return_value=1000.),patch.object(m.time,'clock_gettime',return_value=100.),patch.object(m.time,'monotonic',return_value=1.)]
  with ExitStack() as stack:
   for a in patches:stack.enter_context(a)
   try:result=x.run(streams);error=None
   except BaseException as e:result=None;error=e
  return x,calls,children,reentry,result,error
 def test_success_requires_exact_two_fake_phases(self):
  x,calls,children,_,result,error=self.invoke('success');self.assertIn('finalization unresolved',str(error));self.assertEqual(x.state,'UNKNOWN');self.assertEqual([r['phase'] for r in x.results],list(m.PERF_LIGHT_PHASES));self.assertEqual(len(children),2)
 def test_false_none_gates_and_binding_mutation_fail_without_spawn(self):
  for kind in ('authority_false','authority_none','watchdog_false','watchdog_none','mutate_profile'):
   with self.subTest(kind=kind):
    x,calls,_,_,_,error=self.invoke(kind);self.assertIsNotNone(error);self.assertEqual(x.state,'UNKNOWN');self.assertFalse([c for c in calls if c[0]=='spawn'])
 def test_reentrant_claim_prevents_duplicate_spawn(self):
  x,calls,children,reentry,_,error=self.invoke('reentrant');self.assertIn('finalization unresolved',str(error));self.assertTrue(reentry);self.assertTrue(all('single-use' in s for s in reentry));self.assertEqual(sum(c[0]=='spawn' for c in calls),2)
 def test_stop_after_gate_and_spawn_assignment(self):
  x,calls,children,_,_,error=self.invoke('stop_after_pre');self.assertIsNotNone(error);self.assertEqual(x.state,'UNKNOWN');self.assertFalse([c for c in calls if c[0]=='spawn'])
  x,calls,children,_,_,error=self.invoke('signal_during_spawn');self.assertIsNotNone(error);self.assertEqual(x.state,'UNKNOWN');self.assertEqual(len(children),1);self.assertIn(('identity',11),calls);self.assertEqual(children[0].waits,0)
 def test_mock_child_restores_preexisting_mask(self):
  x,calls,_,_,_,error=self.invoke('restore_child_mask');self.assertIn('finalization unresolved',str(error));self.assertEqual(sum(c[0]=='child-mask-restored' for c in calls),2);self.assertEqual(x.state,'UNKNOWN')
 def test_pending_signal_blocks_spawn_and_proof_failure_preserves_pid(self):
  x,calls,children,_,_,error=self.invoke('pending_before');self.assertIn('stop pending before spawn',str(error));self.assertFalse(children);self.assertEqual(x.state,'UNKNOWN')
  x,calls,children,_,_,error=self.invoke('proof_failure');self.assertIn('synthetic proof failure',str(error));self.assertEqual(x.state,'UNKNOWN');self.assertTrue(x.handoff['spawn_attempted']);self.assertEqual(x.handoff['pid'],11);self.assertIsNone(x.handoff['identity']);self.assertIs(x.child,children[0]);self.assertEqual(children[0].waits,0)
 def test_stop_during_spawn_retains_bound_identity_and_mask_restores(self):
  x,calls,children,_,_,error=self.invoke('signal_during_spawn');self.assertIsNotNone(error);self.assertEqual(x.state,'UNKNOWN');self.assertEqual(x.handoff['pid'],11);self.assertEqual(x.handoff['identity'],{'pid':11,'starttime':'200'});self.assertIs(x.child,children[0]);self.assertEqual(calls[-1][0],'mask');self.assertEqual(calls[-1][1],signal.SIG_SETMASK)
 def test_nonfinite_widened_deadline_fails(self):
  for kind in ('bad_deadline','widen_deadline','late_utc'):
   with self.subTest(kind=kind):
    x,calls,_,_,_,error=self.invoke(kind);self.assertIsNotNone(error);self.assertEqual(x.state,'UNKNOWN');self.assertFalse([c for c in calls if c[0]=='spawn'])
  for value in (float('nan'),float('inf'),-1,True):
   self.assertFalse(m._positive_finite(value))
 def test_exact_binding_digest_refuses_unreviewed_command(self):
  bound=binding();expected=digest(bound);bound['phases'][0]['argv'].append('--changed')
  with patch.object(m,'PERF_LIGHT_BINDING',bound),patch.object(m,'PERF_LIGHT_BINDING_SHA256',expected),self.assertRaisesRegex(ValueError,'hash differs'):m._binding_check()
if __name__=='__main__':unittest.main(verbosity=2)
