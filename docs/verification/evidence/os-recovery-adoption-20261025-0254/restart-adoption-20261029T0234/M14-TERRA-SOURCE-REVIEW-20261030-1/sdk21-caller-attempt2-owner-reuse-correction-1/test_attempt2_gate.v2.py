"""Synthetic comparisons only; no live proc, daemon, Docker or child process."""
import copy
import unittest
import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('attempt2_gate_v2', Path(__file__).with_name('attempt2_gate.v2.py'))
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Gate(unittest.TestCase):
    def setUp(self):
        self.rows = {'guardian':(4,1), 'monitor':(5,1), 'watcher':(2,1),
                     'worker':(3,2), 'server':(6,3)}
        self.receipt = {'thread_id':m.THREAD, 'caps':dict(m.CAPS), 'native_release':False,
                        'binding':{k:{'pid':p,'ppid':q,'start':str(100+p),'state':'S'}
                                   for k,(p,q) in self.rows.items()}}
        self.supervisor = {'pid':1,'ppid':9,'start':'101'}
        self.observed = copy.deepcopy(self.receipt['binding'])
        self.observed['supervisor'] = dict(self.supervisor, state='S')
    def check(self, **kw):
        args = dict(receipt=self.receipt, supervisor=self.supervisor, observed=self.observed,
                    now=1, boot=1, mono=1, boot_id=m.CAPS['boot_id'], stopped=False)
        args.update(kw)
        return m.check_controls(**args)
    def test_matching_current_attempt(self):
        self.assertTrue(self.check())
    def test_historical_receipt_or_looser_caps_rejected(self):
        for change in ({'thread_id':'01a18a76-4f1e-7900-8ed6-127394e93689'},
                       {'caps':dict(m.CAPS, boot_deadline=1571569.6959267766,
                                     monotonic_deadline=1556231.5688797957)}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.check(receipt=dict(self.receipt, **change))
    def test_changed_supervisor_or_birth_rejected(self):
        for role in ('supervisor', 'monitor'):
            observed=copy.deepcopy(self.observed); observed[role]['start']='999'
            with self.subTest(role=role), self.assertRaises(ValueError): self.check(observed=observed)
    def test_deadline_and_stop_rejected(self):
        for changes in ({'stopped':True}, {'boot':m.CAPS['boot_deadline']},
                        {'mono':m.CAPS['monotonic_deadline']}, {'now':m.CAPS['deadline']},
                        {'boot_id':'different'}, {'now':float('nan')}, {'boot':float('inf')}, {'boot':-1}, {'mono':0},
                        {'stopped':None}, {'stopped':0}, {'stopped':''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError): self.check(**changes)
    def test_boolean_and_float_live_identity_aliases_rejected(self):
        for field,value in (('pid',True),('pid',5.0),('ppid',True),('ppid',1.0)):
            observed=copy.deepcopy(self.observed); observed['monitor'][field]=value
            with self.subTest(field=field,value=value), self.assertRaises(ValueError): self.check(observed=observed)
    def test_missing_duplicate_zombie_or_wrong_parent_rejected(self):
        for variant in ('missing','duplicate','zombie','parent'):
            observed=copy.deepcopy(self.observed); receipt=copy.deepcopy(self.receipt)
            if variant=='missing': del observed['monitor']
            elif variant=='duplicate': receipt['binding']['monitor']['pid']=4; observed['monitor']['pid']=4
            elif variant=='zombie': observed['monitor']['state']='Z'
            else: receipt['binding']['monitor']['ppid']=9; observed['monitor']['ppid']=9
            with self.subTest(variant=variant), self.assertRaises(ValueError): self.check(receipt=receipt, observed=observed)

if __name__=='__main__': unittest.main(verbosity=2)
