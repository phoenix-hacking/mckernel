"""Synthetic private-group integration; no actual process or physical effect."""
import importlib.util
from pathlib import Path
import unittest
from unittest import mock
import custody_protocol as c

p=Path(__file__).with_name('daemon_image_parent.attempt2.py')
spec=importlib.util.spec_from_file_location('private_parent',p)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class Integration(unittest.TestCase):
 def setUp(self):
  self.parent={'pid':10,'birth':100,'ppid':2,'pgid':10,'sid':2}
  self.child={'pid':11,'birth':101,'ppid':10,'pgid':10,'sid':2}
  self.release={'parent_pgid':10,'parent_sid':2,'outer_group_identities':[]}
  self.token={'release':[1]*10};self.nonce='a'*32
 def baseline(self,release=None,parent=None,members=None):
  parent=self.parent if parent is None else parent
  release=self.release if release is None else release
  members=[10] if members is None else members
  with mock.patch.object(m,'bound_document',return_value=release),mock.patch.object(m,'proc_identity',return_value=parent),mock.patch.object(m,'members',return_value=members):
   return m.group_baseline(self.token,parent)
 def go(self,child=None,baseline=None,members=None,ids=None):
  child=self.child if child is None else child
  baseline={} if baseline is None else baseline
  members=[10,11] if members is None else members
  ids={10:self.parent,11:self.child} if ids is None else ids
  with mock.patch.object(m,'parent_custody_gate',return_value=True),mock.patch.object(m,'proc_identity',side_effect=lambda pid:ids[pid]),mock.patch.object(m,'members',return_value=members),mock.patch.object(m.signal,'sigpending',return_value=set()),mock.patch.object(m.time,'monotonic',return_value=1),mock.patch.object(m.os,'write',return_value=1) as write:
   try:result=m.release_held_gate(self.token,self.parent,child,baseline,99,50)
   except BaseException as exc:return exc,write.call_count
   return result,write.call_count
 def test_one_profile_through_parent_group_ack_and_go(self):
  baseline=self.baseline();self.assertEqual(baseline,{})
  outer=c.OuterProtocol(self.nonce,self.parent,50);published=[]
  for phase,child in (('PARENT_READY',None),('IMAGE_READY',self.child)):
   event=c.make_event(self.nonce,phase,self.parent,child)
   identities={r['pid']:r for r in (self.parent,child) if r is not None}
   ack=outer.accept(event,child,lambda:1,lambda:False,lambda:True,lambda:True,lambda:(identities,sorted(identities)),published.append)
   self.assertEqual(ack,c.canonical(c.ack_for(event))+b'\n')
  result,writes=self.go(baseline=baseline)
  self.assertIs(result,True);self.assertEqual(writes,1);self.assertEqual(len(published),2)
 def test_parent_without_private_leader_or_with_outer_actor_rejected(self):
  with self.assertRaises(ValueError): self.baseline(parent=dict(self.parent,pgid=2))
  with self.assertRaises(ValueError): self.baseline(release=dict(self.release,outer_group_identities=[{'pid':2}]))
  with self.assertRaises(ValueError): self.baseline(members=[2,10])
  result,writes=self.go(baseline={2:{'pid':2}});self.assertIsInstance(result,ValueError);self.assertEqual(writes,0)
 def test_go_denied_when_parent_gate_is_not_explicit_true(self):
  for result in (False,None,0,1,{}):
   with self.subTest(result=result),mock.patch.object(m,'parent_custody_gate',return_value=result),mock.patch.object(m.os,'write') as write:
    with self.assertRaises(ValueError):
     m.release_held_gate(self.token,self.parent,self.child,{},99,50)
    write.assert_not_called()
 def test_group_drift_or_escaped_child_never_gets_go(self):
  for change in ({'members':[10,11,12]},{'child':dict(self.child,pgid=11)},
                 {'ids':{10:self.parent,11:dict(self.child,birth=999)}},
                 {'child':dict(self.child,ppid=2)}):
   with self.subTest(change=change):
    result,writes=self.go(**change);self.assertIsInstance(result,ValueError);self.assertEqual(writes,0)

if __name__=='__main__': unittest.main(verbosity=2)
