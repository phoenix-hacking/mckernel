"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure initial-operation/ABI-contract tests; no live guards or subprocesses.
"""
import copy
import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('operation118',HERE/'operation_window_guard118.py')
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)


def fixture():
    subjects={'source_map118':{'path':'/fixture/source-map118.json','bytes':1,'sha256':'0'*64}}
    s=dict(schema='mckernel.explicit-new-window-operation-successor.v1',author='/root',
           operation='current118-build',decision='EXPLICIT_OPERATION_WINDOW_SUCCESSOR',
           window_sha256='0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e',
           first_prepared_window_sha256='0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e',
           credit_run_id='7f4af94a83b14cc08f97401f5891d965',credit_ceiling='57774.852125',
           predecessor_cutoffs=None,operation_cutoffs=[1793253600,1035704.5689393478,1051042.6959879305],
           subjects=subjects,source_owners=['/root','/root/m14_compose','/root/restart_guard'],
           minimum_cumulative_spent='22812.3311',guardian={'source':g.GUARDIAN_SOURCE.copy(),'entrypoint':'guard'})
    r=dict(schema='mckernel.independent-operation-window-review.v1',
           decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR',independent=True,
           reviewer='/root/independent118',operation='current118-build',successor=copy.deepcopy(s))
    return s,r,subjects


class Initial118(unittest.TestCase):
    def validate(self,s,r,subjects,operation='current118-build',clocks=(1793216000,997600,1013000)):
        return g.validate_operation(s,r,operation,subjects,clocks,g.BOOT)

    def test_initial_operation_no_fabricated_predecessor(self):
        self.assertEqual(g.PREDECESSOR_CUTOFFS,{'current118-build':None})
        self.assertEqual(self.validate(*fixture()),(1793253600,1035704.5689393478,1051042.6959879305))
        for op in ('current116','current117-build','original227'):
            with self.assertRaises(ValueError):self.validate(*fixture(),operation=op)
        for old in ([],[1793165769,947874.5689514667,963213.695968197],False,{},'None'):
            s,r,subjects=fixture();s['predecessor_cutoffs']=old;r['successor']=copy.deepcopy(s)
            with self.assertRaises(ValueError):self.validate(s,r,subjects)

    def test_changed_successor_controls(self):
        changes=[('author',None),('decision',None),('operation','current117-build'),
                 ('first_prepared_window_sha256','0'*64),('window_sha256','0'*64),
                 ('credit_run_id','reset'),('credit_ceiling','57775'),
                 ('minimum_cumulative_spent','0'),('minimum_cumulative_spent','57774.852125')]
        for key,value in changes:
            s,r,subjects=fixture();s[key]=value;r['successor']=copy.deepcopy(s)
            with self.subTest(key=key),self.assertRaises(ValueError):self.validate(s,r,subjects)

    def test_strict_tighter_cutoffs(self):
        for i in range(3):
            s,r,subjects=fixture();s['operation_cutoffs'][i]+=1;r['successor']=copy.deepcopy(s)
            with self.assertRaises(ValueError):self.validate(s,r,subjects)
            s,r,subjects=fixture();clocks=list((1793216000,997600,1013000));clocks[i]=s['operation_cutoffs'][i]
            with self.assertRaises(ValueError):self.validate(s,r,subjects,clocks=clocks)
        s,r,subjects=fixture();s['operation_cutoffs']=[1793253500,1035700,1051040];r['successor']=copy.deepcopy(s)
        self.assertEqual(self.validate(s,r,subjects),(1793253500,1035700,1051040))

    def test_exact_review_subjects_and_ownership(self):
        s,r,subjects=fixture()
        for reviewer in ('/root','/root/m14_compose','/root/restart_guard'):
            bad=copy.deepcopy(r);bad['reviewer']=reviewer
            with self.assertRaises(ValueError):self.validate(s,bad,subjects)
        bad=copy.deepcopy(r);bad['independent']=False
        with self.assertRaises(ValueError):self.validate(s,bad,subjects)
        with self.assertRaises(ValueError):self.validate(s,r,{'different':subjects['source_map118']})
        bad=copy.deepcopy(s);bad['subjects']={};review=copy.deepcopy(r);review['successor']=copy.deepcopy(bad)
        with self.assertRaises(ValueError):self.validate(bad,review,{})
        bad=copy.deepcopy(r);bad['successor']['minimum_cumulative_spent']='22813'
        with self.assertRaises(ValueError):self.validate(s,bad,subjects)

    def test_exact_reviewed_restart_guardian(self):
        self.assertEqual(g.GUARDIAN_SOURCE['sha256'],'48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18')
        self.assertEqual(g.reference(Path(g.GUARDIAN_SOURCE['path'])),g.GUARDIAN_SOURCE)
        s,r,subjects=fixture()
        mutations=[{'source':dict(g.GUARDIAN_SOURCE,sha256='e8a117df7b80143fe3f095e23f2847462dde1e2f3b4fac331969ec6f3ac1ae2d'),'entrypoint':'guard'},
                   {'source':dict(g.GUARDIAN_SOURCE,path='/old/guardian_guard.py'),'entrypoint':'guard'},
                   {'source':g.GUARDIAN_SOURCE,'entrypoint':'control'},{}]
        for guardian in mutations:
            bad=copy.deepcopy(s);bad['guardian']=guardian;review=copy.deepcopy(r);review['successor']=copy.deepcopy(bad)
            with self.assertRaises(ValueError):self.validate(bad,review,subjects)

    def test_account_thread_and_unchanged_cumulative_predicates(self):
        state=json.loads((g.PREDECESSOR.parent/'ACCOUNT-FIXTURE.json').read_bytes())
        state['thread_id']='01a183ec-72e5-7400-8f48-b4efb8725520'
        wall=datetime.datetime.fromisoformat(state['heartbeat_at']).timestamp()+1
        self.assertGreater(g.check_account_state(state,wall,'22812.3311'),0)
        for thread in ('01a18111-26a7-7ef2-bbd6-e33d1c8dc803','old'):
            bad=copy.deepcopy(state);bad['thread_id']=thread
            with self.assertRaises(ValueError):g.check_account_state(bad,wall,'22812.3311')
        for key in ('service_hold','policy_hold','auth_hold','billing_hold','stop_now'):
            bad=copy.deepcopy(state);bad[key]=True
            with self.assertRaises(ValueError):g.check_account_state(bad,wall,'22812.3311')
        bad=copy.deepcopy(state);bad['credit_budget']['spent']='0'
        with self.assertRaises(ValueError):g.check_account_state(bad,wall,'22812.3311')
        with self.assertRaises(ValueError):g.check_account_state(state,wall+180,'22812.3311')

    def test_adapter_schema_without_live_guard(self):
        with tempfile.TemporaryDirectory(dir=HERE) as directory:
            directory=Path(directory);s,r,subjects=fixture()
            for name,value in [('successor',s),('review',r)]:
                (directory/(name+'.json')).write_text(json.dumps(value))
            config=dict(schema='mckernel.sealed-operation-guard-adapter-config.v1',operation='current118-build',
                        shared_guard=g.reference(HERE/'operation_window_guard118.py'),
                        successor=g.reference(directory/'successor.json'),review=g.reference(directory/'review.json'),subjects=subjects)
            path=directory/'config.json';path.write_text(json.dumps(config))
            spec=importlib.util.spec_from_file_location('adapter118',HERE/'current118_guard_adapter.py')
            adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
            with self.assertRaises(ValueError):adapter.current_cutoffs()
            adapter.configure(g.reference(path));self.assertEqual(adapter.current_cutoffs(),g.OPERATION_CUTOFFS)
            with self.assertRaises(ValueError):adapter.configure(g.reference(path))
            path.write_text('{}')
            with self.assertRaises(ValueError):adapter.current_cutoffs()

    def test_immutable_window_and_non_authority_template(self):
        self.assertEqual((g.load_window()['deadline_epoch'],g.load_window()['monotonic_deadline'],g.load_window()['boot_deadline']),
                         (1793253600,1035706.5689547858,1051044.6960026678))
        t=json.loads((HERE/'ROOT118-OPERATION-SUCCESSOR.TEMPLATE.NOT-AUTHORITY.json').read_bytes())
        self.assertIsNone(t['author']);self.assertIsNone(t['decision']);self.assertIsNone(t['predecessor_cutoffs'])
        self.assertIsNone(t['runtime_authority']);self.assertTrue(t['template_source_only_no_authority'])
        _,r,subjects=fixture()
        with self.assertRaises(ValueError):self.validate(t,r,subjects)


if __name__=='__main__':unittest.main(verbosity=2)
