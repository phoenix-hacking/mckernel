"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure profile/grant/resource/no-replay policy controls; no compiler or fixture runs.
"""
import copy,importlib.util,json
from pathlib import Path
import unittest
from unittest.mock import patch
HERE=Path(__file__).resolve().parent

def module(name,file):
 spec=importlib.util.spec_from_file_location(name,HERE/file);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
r=module('runner','run_new12h_host.py');a=module('admission','admission_new12h.py')
class PolicyControls(unittest.TestCase):
 def setUp(self):
  self.p=json.loads((HERE/'PROFILE.NOT-GRANTED.json').read_bytes())
 def test_exact_tencommand_profile_and_all_input_pins(self):
  r.validate_profile(self.p);r.verify(self.p['inputs']+[x['plan'] for x in self.p['leaves']])
  self.assertEqual(len(self.p['commands']),10)
 def test_old_host19_profile_cannot_enter(self):
  old=HERE.parent/'m14-ready-host-batch-20261027-1/PROFILE.NOT-GRANTED.json'
  with self.assertRaises(ValueError):r.validate_profile(json.loads(old.read_bytes()))
 def test_stale_window_resource_and_argv_mutations(self):
  for key,value in [('goal','old'),('fixed_cutoffs',[1793100290,882395,897734]),('fixed_deadline_UTC','2026-10-27T11:24:50Z')]:
   p=copy.deepcopy(self.p);p[key]=value
   with self.assertRaises(ValueError):r.validate_profile(p)
  for key,value in [('cpu',7),('jobs',2),('AS_bytes',2**32),('CPU_seconds_each',61),('wall_seconds_each',91),('aggregate_jobs',8)]:
   p=copy.deepcopy(self.p);p['resources'][key]=value
   with self.assertRaises(ValueError):r.validate_profile(p)
  p=copy.deepcopy(self.p);p['commands'][0]['argv'].append('different')
  with self.assertRaises(ValueError):r.validate_profile(p)
 def test_memory_cpu_and_capacity_floors(self):
  args=[a.MIN_MEMORY,{6},18*2**30,12*2**30,2*2**30];a.resource_checks(*args)
  for index,value in [(0,a.MIN_MEMORY-1),(1,{6,7}),(1,{7}),(2,18*2**30-1),(3,12*2**30-1)]:
   bad=args.copy();bad[index]=value
   with self.assertRaises(ValueError):a.resource_checks(*bad)
 def grant(self):
  return dict(task_id=self.p['task_id'],profile_sha256='profile',runner_sha256='runner',goal=r.THREAD,
   fixed_deadline_UTC=self.p['fixed_deadline_UTC'],fixed_cutoffs=r.CUTOFFS,resources=self.p['resources'],authorized=True,
   authorized_by='Root',cpu6_exclusive=True,other_cpu6_jobs=0,nonce='a'*32,issued_wall=1000,expires_wall=1100,
   reserved_jobs_other=4,reserved_GiB_other='12',heavy_jobs_current=1,
   cpu6_exclusion_observation={'path':'/mock/exclusion.json','bytes':0,'sha256':'mock'})
 def check_grant(self,grant,now=1001,observation=None):
  observed=observation or dict(goal=r.THREAD,cpu=6,ordinary_jobs_live=0,authorized_by='Root',observed_wall=1000)
  with patch.object(r,'verify'),patch.object(Path,'read_bytes',return_value=json.dumps(observed).encode()):
   r.validate_grant(grant,self.p,'profile','runner',now)
 def test_exact_fresh_root_grant(self):self.check_grant(self.grant())
 def test_reject_absent_stale_foreign_or_overbudget_grant(self):
  for key,value in [('authorized',False),('authorized_by','worker'),('nonce',''),('profile_sha256','old'),('runner_sha256','old'),('goal','old'),('cpu6_exclusive',False),('other_cpu6_jobs',1),('issued_wall',800),('expires_wall',1001),('reserved_jobs_other',7),('reserved_GiB_other','19.662'),('heavy_jobs_current',2)]:
   with self.subTest(key=key):
    grant=self.grant();grant[key]=value
    with self.assertRaises(ValueError):self.check_grant(grant)
 def test_cpu6_observation_must_be_current_exclusive_root(self):
  original=dict(goal=r.THREAD,cpu=6,ordinary_jobs_live=0,authorized_by='Root',observed_wall=1000)
  for key,value in [('goal','old'),('cpu',7),('ordinary_jobs_live',1),('authorized_by','worker'),('observed_wall',800)]:
   observed=dict(original);observed[key]=value
   with self.assertRaises(ValueError):self.check_grant(self.grant(),observation=observed)
 def test_leaf_ranges_and_output_growth_are_bounded(self):
  p=copy.deepcopy(self.p);p['leaves'][0]['last']-=1
  with self.assertRaises(ValueError):r.validate_profile(p)
  p=copy.deepcopy(self.p);p['host_growth_reserve_bytes']=0
  with self.assertRaises(ValueError):r.validate_profile(p)
if __name__=='__main__':unittest.main(verbosity=2)
