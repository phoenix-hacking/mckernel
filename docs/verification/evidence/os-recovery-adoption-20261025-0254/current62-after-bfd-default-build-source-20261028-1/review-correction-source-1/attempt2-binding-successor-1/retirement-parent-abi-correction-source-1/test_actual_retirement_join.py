"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine successful RESULT and actual Root direct-parent receipt; no live effects.
"""
from pathlib import Path
import copy
import json
import tempfile
import unittest
import observe_current62_bfd_postjoin as m

D=Path(__file__).resolve().parent
E=Path(m.PINS['prior_ledger']['path']).parent.parent
RESULT=E/'bfd-default-build-normal-retirement-preparation-20261028-1/executor-source-1/image-metadata-profile-correction-source-1/actual-retirement-root3-faac/RESULT.json'
JOIN=E/'restart-adoption-20261028T1911/BFD-RETIREMENT-RELEASE-3/ACTUAL-RETIREMENT.PARENT-JOIN.json'

class ActualRetirementJoin(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.executor=m.load(m.PINS['retirement_executor'],'pure_actual_successful_retirement_join')
  cls.result=m.ref(RESULT);cls.join=m.ref(JOIN)
 def test_genuine_root_join_and_all14_clients_no_inherited_group_claim(self):
  b,value,receipts,actors=m.validate_retirement(self.executor,self.result,self.join)
  self.assertEqual(value['cleanup_actor'],dict(pid=2158579,birth=102053058,mutex_fd=4))
  self.assertEqual(len(receipts),14);self.assertEqual(len(actors),15)
  self.assertIsNone(actors[0]['group']);self.assertTrue(actors[0]['inherited_parent_group_absence_not_claimed'])
  self.assertNotIn('process_group_absent',m.checked(self.join))
  self.assertEqual([(row['pid'],row['start'])for row in actors[1:]],[(row['pid'],row['birth'])for row in receipts])
 def test_changed_identity_wait_streams_or_published_RESULT_rejected(self):
  original=m.checked(self.join)
  mutations=[('pid',2158580),('birth','102053059'),('returncode',1),('positive_direct_parent_wait',False),('parent_streams_closed',False)]
  with tempfile.TemporaryDirectory(prefix='TEST_ONLY-actual-join-',dir=D)as directory:
   root=Path(directory)
   for index,(key,value)in enumerate(mutations):
    bad=copy.deepcopy(original);bad[key]=value;path=root/('TEST_ONLY-bad-'+str(index)+'.json');path.write_text(json.dumps(bad))
    with self.assertRaises(ValueError):m.validate_retirement(self.executor,self.result,m.ref(path))
   for key,text in [('stdout',json.dumps(dict(status='RETIREMENT_COMPLETE_PENDING_PARENT_JOIN_AND_FRESH_CURRENT',result=m.PINS['actual_pending_root62']))),('stderr','TEST_ONLY unexpected bytes')]:
    raw=root/('TEST_ONLY-'+key);raw.write_text(text);bad=copy.deepcopy(original);bad[key]=m.ref(raw);path=root/('TEST_ONLY-bad-'+key+'.json');path.write_text(json.dumps(bad))
    with self.assertRaises(ValueError):m.validate_retirement(self.executor,self.result,m.ref(path))
 def test_generic_capture_parent_stays_strict(self):
  with self.assertRaises(KeyError):m.validate_parent_join(m.checked(self.join),dict(pid=2158579,birth=102053058))
  good=dict(pid=700001,starttime=200,returncode=0,positive_direct_wait_join=True,streams_closed=True,process_group_absent=True,remaining_group_members=[],group_observation_errors=[])
  m.validate_parent_join(good,dict(pid=700001,birth=200))
  for key,value in [('process_group_absent',False),('remaining_group_members',[700002]),('group_observation_errors',['TEST_ONLY'])]:
   bad=dict(good);bad[key]=value
   with self.assertRaises(ValueError):m.validate_parent_join(bad,dict(pid=700001,birth=200))

if __name__=='__main__':unittest.main(verbosity=2)
