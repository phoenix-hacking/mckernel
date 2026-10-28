"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Offline independent first-arm fixtures; no controller, account, signal or subprocess actions.
"""
import copy, importlib.util, json, tempfile, unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1')
spec=importlib.util.spec_from_file_location('reviewed_guardian',BASE/'armed-controller/bridge.py')
b=importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
CONFIG=json.loads((BASE/'armed-controller/CONFIG.json').read_bytes())
CHAIN=json.loads((BASE/'GUARDIAN-PROPOSAL.json').read_bytes())['chain']
NOW=b.DEADLINE-3600
class EndOfflineLoop(BaseException):pass
class FirstArmTests(unittest.TestCase):
 def fixture(self, change=lambda c,s:None):
  cfg=copy.deepcopy(CONFIG)
  state=dict(thread_id=b.THREAD,phase='running',goal={'status':'active'},stop_reason=None,
   heartbeat_at=datetime.fromtimestamp(NOW,timezone.utc).isoformat(),settings={'billing':{'mode':'prepaid_credits','credit_budget':cfg['initial_credit_budget']}},
   credit_budget={'id':cfg['credit_run_id'],'budget':cfg['initial_credit_budget']})
  change(cfg,state)
  with tempfile.TemporaryDirectory() as tmp:
   private=Path(tmp)/'private'; private.mkdir(); campaign=Path(tmp)/'campaign';campaign.mkdir()
   (campaign/'state.json').write_text(json.dumps(state));(campaign/'watcher.json').write_text('{}')
   with patch.object(b,'HERE',private),patch.object(b,'CAMPAIGN',campaign),patch.object(b,'verify_packet',return_value={}),patch.object(b,'bind',return_value=copy.deepcopy(CHAIN)),patch.object(b,'old_gone',return_value=False),patch.object(b,'leases_free',return_value=False),patch.object(b.time,'time',return_value=NOW),patch.object(b.time,'clock_gettime',return_value=100),patch.object(b.time,'monotonic',return_value=100),patch.object(b.time,'sleep',side_effect=EndOfflineLoop),patch.object(b,'stop_worker') as stop,patch.object(b.subprocess,'Popen') as spawn:
    try:b.run(cfg,'review-packet')
    except EndOfflineLoop:pass
    finally:stop.assert_not_called();spawn.assert_not_called()
   return json.loads((private/'journal.json').read_bytes()) if (private/'journal.json').exists() else None
 def test_first_arm_adopts_existing_finite_prepaid_watcher_without_spawn(self):
  j=self.fixture();self.assertTrue(j['credit_started']);self.assertTrue(j['initial_prepaid_guard']);self.assertTrue(j['original_finite']);self.assertEqual(j['replacement'],CHAIN);self.assertEqual(j['credit_run_id'],'7f4af94a83b14cc08f97401f5891d965');self.assertLessEqual(j['boot_deadline'],CONFIG['window']['boot_deadline']);self.assertEqual(j['last_action'],'WAIT_EXISTING_CREDIT_WATCHER')
 def test_first_arm_rejects_changed_credit_id(self):
  with self.assertRaisesRegex(ValueError,'credit guard identity/budget'):self.fixture(lambda c,s:s['credit_budget'].update(id='a'*32))
 def test_first_arm_rejects_changed_budget(self):
  with self.assertRaisesRegex(ValueError,'credit guard identity/budget'):self.fixture(lambda c,s:s['credit_budget'].update(budget='57775'))
 def test_first_arm_rejects_changed_actual_watcher_birth(self):
  with self.assertRaisesRegex(ValueError,'clock/lineage'):self.fixture(lambda c,s:c['initial_watch_clock'].update(watcher_start='other'))
 def test_adopted_credit_watcher_never_restarts_after_exit(self):
  self.assertEqual(b.decide({'thread_id':b.THREAD},dict(credit_started=True),NOW,True,True,'state'),'STOP_CREDIT_WATCHER_EXIT_NO_RESTART')
 def test_forward_wall_tightens_and_rollback_does_not_restore_boot_cap(self):
  shortened=b.tighten_cutoff(3700,b.DEADLINE-20,100)
  self.assertEqual(shortened,120);self.assertEqual(b.tighten_cutoff(shortened,NOW,101),120)
if __name__=='__main__':unittest.main(verbosity=2)
