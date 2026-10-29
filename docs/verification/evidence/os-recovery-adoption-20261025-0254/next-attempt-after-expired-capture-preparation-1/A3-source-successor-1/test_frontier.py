"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Genuine base/A2 receipts, explicitly hypothetical future raw captures in TEMP only.
No observe/guard/command call; only proc effect leaves are substituted.
"""
from pathlib import Path
import copy
import importlib.util
import json
import tempfile
import unittest
from unittest.mock import patch

D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('A3_exact_frontier_source',D/'typed_current_boundary.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
ACTORS=[dict(pid=2198978,birth=102765089,role='A2_unlaunched_holder',group=None,fd=3),dict(pid=2198306,birth=102756246,role='A2_finite_waiter',group=2198306,fd=None),dict(pid=2199449,birth=102772979,role='A2_held_capture_child',group=2199449,fd=None),dict(pid=2199448,birth=102772975,role='A2_held_wrapper',group=None,fd=None),dict(pid=2198340,birth=102760320,role='A2_physical_capture_child',group=2198340,fd=None),dict(pid=2198339,birth=102760316,role='A2_physical_wrapper',group=None,fd=None)]

def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n');return c.ref(path)

def frontier_fixture(root):
    p=c.FRONTIER_INPUTS
    f=dict(schema='mckernel.current118.closed-unlaunched-frontier.v1',author='/root',decision='BIND_COMPLETE_POST_ROOT63_CLOSED_UNLAUNCHED_FRONTIER',base_ledger=p['base_ledger'],base_free=p['base_free'],base_current_bindings=p['base_current_bindings'],evidence_packet=p['evidence_packet'],abandoned_nonces=[p['abandoned_nonce']],actors=copy.deepcopy(ACTORS),all_post_base_custody_and_reservations_listed=True,root_attests_no_unlisted_post_base_operation=True,recorded_epoch=1793231369.7204006,runtime_authority=None)
    return f,write(root/'TEST_ONLY-frontier.json',f)

def typed_fixture(root):
    f,fr=frontier_fixture(root);consumer=c.ref(D/'observe_current63_current118.py');core=c.ref(D/'typed_current_boundary.py');selection=c.ref(D/'UPSTREAM-SELECTION.SOURCE-ONLY.json')
    current=c.checked(c.FRONTIER_INPUTS['base_current_bindings'])
    schema=c.ref(D/'OBSERVER-SCHEMA.CURRENT63-CURRENT118.SOURCE-ONLY.json')
    sr=write(root/'TEST_ONLY-schema-review.json',dict(independent=True,decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',reviewed_observer_schema=schema))
    boundary=write(root/'TEST_ONLY-boundary.json',dict(author='/root',decision='BIND_EXISTING_REVIEWED_CURRENT_BUILD_BOUNDARY',root_attests_exact_current_boundary=True,nonce_ledger=current['ledger'],native_custody_clearance=current['latest_free'],observer=consumer,observer_schema=schema,observer_schema_review=sr,independent_current_boundary_review=sr))
    module,_,_=c.upstream(selection)
    out=root/'TEST_ONLY-future-observation';out.mkdir()
    release=write(root/'TEST_ONLY-readonly.json',dict(author='/root',decision='AUTHORIZE_ONE_CURRENT118_TYPED_CURRENT63_REOBSERVATION',maximum_invocations=1,consumer=consumer,core=core,accepted_current_bindings=c.FRONTIER_INPUTS['base_current_bindings'],output_directory=str(out),capture_scope=module.capture_scope(),closed_unlaunched_frontier=fr))
    review=dict(independent=True,implementation_ownership=False,decision='PASS_EXACT_CURRENT118_TYPED_POST_BFD_BOUNDARY',consumer=consumer,core=core,upstream_selection=selection,accepted_current_bindings=c.FRONTIER_INPUTS['base_current_bindings'],current_boundary=boundary,readonly_release=release,closed_unlaunched_frontier=fr)
    rr=write(root/'TEST_ONLY-data-review.json',review)
    binding=dict(schema='mckernel.current118.accepted-post-BFD-boundary.v1',author='/root',decision='BIND_CURRENT118_TO_ACCEPTED_POST_BFD_ROOT63',runtime_authority=None,phase='accepted_current',upstream_selection=selection,accepted_current_bindings=c.FRONTIER_INPUTS['base_current_bindings'],current_boundary=boundary,readonly_release=release,independent_review=rr,closed_unlaunched_frontier=fr)
    br=write(root/'TEST_ONLY-typed-binding.json',binding)
    reservation=c.checked(c.FRONTIER_INPUTS['reservation'])
    root_context=dict(typed_current_boundary_binding=br,nonce_ledger=current['ledger'],native_custody_clearance=current['latest_free'],current_boundary=boundary,closed_unlaunched_frontier=fr,next_attempt_reservation=c.FRONTIER_INPUTS['reservation'],nonce=reservation['nonce'],admission=reservation['admission'])
    return dict(frontier=f,frontier_ref=fr,consumer=consumer,core=core,selection=selection,binding=binding,binding_ref=br,root_context=root_context,module=module)

def future_capture(root,frontier,module,mutate=None,stale=False):
    free=c.checked(c.FRONTIER_INPUTS['base_free']);value=copy.deepcopy(c.checked(free['actual_postjoin_observation']))
    delta=frontier['recorded_epoch']+2-value['observed_clocks'][0]
    if not stale:
        for key in ['observed_clocks','last_observed_clocks']:value[key]=[clock+delta for clock in value[key]]
    records=[]
    for index,receipt in enumerate(value['query_command_receipts']):
        row=copy.deepcopy(c.checked(receipt))
        if not stale:
            row['started_epoch']+=delta;row['finished_epoch']+=delta
        if index in (0,4):
            report=copy.deepcopy(value['complete_process_reports'][0 if index==0 else 1])
            if mutate:mutate(report)
            stdout=root/('TEST_ONLY-census-'+str(index)+'.stdout');stdout.write_text(json.dumps(report))
            row['raw']['stdout']=c.ref(stdout)
            value['complete_process_reports'][0 if index==0 else 1]=report
        rr=write(root/('TEST_ONLY-query-'+str(index)+'.json'),row);records.append(rr)
        if index in (1,2,3):value['BFD_exact_absence_queries'][index-1]['command_receipt']=rr
    value['query_command_receipts']=records
    return value

class Proc:
    def __init__(self,path,exists,locks):self.path=path;self.present=exists;self.locks=locks
    def exists(self):return self.path in self.present
    def read_text(self):
        assert self.path=='/proc/locks';return self.locks

def proc_effects(present=(),locks=''):
    def factory(*parts):
        p=Path(*parts)
        return Proc(str(p),set(present),locks)if str(p).startswith('/proc')else p
    return patch.object(c,'Path',side_effect=factory)

class Frontier(unittest.TestCase):
    def test_genuine_A2_frontier_and_new_A3_root_context(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-positive-',dir=D)as directory:
            f=typed_fixture(Path(directory));context=c.validate_root_context(f['root_context'],f['selection'],f['consumer'],f['core'])
            self.assertEqual(context['frontier']['actors'],ACTORS)
            self.assertEqual(len(context['ledger']['consumed_nonces']),71)
            self.assertNotIn('1d3f2239b2884cedbd9e7dbe248ae1aa',context['ledger']['consumed_nonces'])
    def test_missing_stale_or_incomplete_frontier_rejected(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-bad-frontier-',dir=D)as directory:
            root=Path(directory);f=typed_fixture(root);current=c.checked(c.FRONTIER_INPUTS['base_current_bindings'])
            mutations=[lambda x:x.__setitem__('author',None),lambda x:x.__setitem__('base_free',c.FRONTIER_INPUTS['base_ledger']),lambda x:x.__setitem__('all_post_base_custody_and_reservations_listed',False),lambda x:x.__setitem__('root_attests_no_unlisted_post_base_operation',False),lambda x:x['actors'].pop(),lambda x:x.__setitem__('recorded_epoch',1793220000),lambda x:x.__setitem__('abandoned_nonces',[])]
            for i,mutate in enumerate(mutations):
                bad=copy.deepcopy(f['frontier']);mutate(bad)
                with self.assertRaises((ValueError,KeyError)):c.validate_closed_unlaunched_frontier(write(root/('TEST_ONLY-bad-frontier-'+str(i)+'.json'),bad),current)
            bad=dict(f['binding']);bad.pop('closed_unlaunched_frontier')
            with self.assertRaises(KeyError):c.validate_typed(write(root/'TEST_ONLY-missing-frontier.json',bad),f['selection'],f['consumer'],f['core'])
            review=c.checked(f['binding']['independent_review']);review.pop('closed_unlaunched_frontier')
            bad=dict(f['binding'],independent_review=write(root/'TEST_ONLY-old-data-review.json',review))
            with self.assertRaises(KeyError):c.validate_typed(write(root/'TEST_ONLY-stale-review-binding.json',bad),f['selection'],f['consumer'],f['core'])
            release=c.checked(f['binding']['readonly_release']);release.pop('closed_unlaunched_frontier')
            release_ref=write(root/'TEST_ONLY-old-readonly.json',release);review=c.checked(f['binding']['independent_review']);review['readonly_release']=release_ref
            bad=dict(f['binding'],readonly_release=release_ref,independent_review=write(root/'TEST_ONLY-new-review-old-delegation.json',review))
            with self.assertRaises(KeyError):c.validate_typed(write(root/'TEST_ONLY-stale-readonly-binding.json',bad),f['selection'],f['consumer'],f['core'])
    def test_abandoned_or_consumed_nonce_and_missing_reservation_rejected(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-nonces-',dir=D)as directory:
            f=typed_fixture(Path(directory))
            for nonce in ['1d3f2239b2884cedbd9e7dbe248ae1aa','faac1b4804174de5800c58d61ba98004']:
                bad=dict(f['root_context'],nonce=nonce)
                with self.assertRaises(ValueError):c.validate_root_context(bad,f['selection'],f['consumer'],f['core'])
            bad=dict(f['root_context']);bad.pop('next_attempt_reservation')
            with self.assertRaises(KeyError):c.validate_root_context(bad,f['selection'],f['consumer'],f['core'])
    def test_fresh_complete_raw_census_passes_with_proc_leaves_only(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-fresh-',dir=D)as directory:
            root=Path(directory);f=typed_fixture(root);value=future_capture(root,f['frontier'],f['module'])
            with proc_effects():result=c.validate_fresh_closed_unlaunched(value,f['frontier'],f['module'])
            self.assertEqual(result['proc_snapshots'],4);self.assertTrue(result['old_holder_FD3_absent'])
            self.assertTrue(result['inherited_holder_wrapper_groups_absence_not_claimed'])
    def test_stale_capture_missing_raw_or_old_holder_FD_lock_rejected(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-stale-',dir=D)as directory:
            root=Path(directory);f=typed_fixture(root);value=future_capture(root,f['frontier'],f['module'],stale=True)
            with proc_effects(),self.assertRaises(ValueError):c.validate_fresh_closed_unlaunched(value,f['frontier'],f['module'])
            value=future_capture(root,f['frontier'],f['module']);missing=copy.deepcopy(value);missing['query_command_receipts'].pop()
            with proc_effects(),self.assertRaises(ValueError):c.validate_fresh_closed_unlaunched(missing,f['frontier'],f['module'])
            for present,locks in [(['/proc/2198978/fd/3'],''),([], '1: FLOCK ADVISORY WRITE 2198978 00:1b:4 0 EOF\n')]:
                with proc_effects(present,locks),self.assertRaises(ValueError):c.validate_fresh_closed_unlaunched(value,f['frontier'],f['module'])
    def test_every_live_A2_PID_and_known_group_rejected(self):
        with tempfile.TemporaryDirectory(prefix='TEST_ONLY-A3-live-',dir=D)as directory:
            root=Path(directory);f=typed_fixture(root)
            for index,actor in enumerate(ACTORS):
                sub=root/('TEST_ONLY-live-'+str(index));sub.mkdir()
                def live(report,actor=actor):
                    for snapshot in report['snapshots']:snapshot.append([actor['pid'],1,str(actor['birth'])]);snapshot.sort()
                    for group in report['groups']:group.append([actor['pid'],1,str(actor['birth']),actor['group']or 1,1]);group.sort()
                value=future_capture(sub,f['frontier'],f['module'],live)
                with proc_effects(),self.assertRaises(ValueError):c.validate_fresh_closed_unlaunched(value,f['frontier'],f['module'])
            for index,group_id in enumerate([2198306,2199449,2198340]):
                sub=root/('TEST_ONLY-group-'+str(index));sub.mkdir()
                def livegroup(report):
                    for snapshot in report['snapshots']:snapshot.append([9999900,1,'100']);snapshot.sort()
                    for group in report['groups']:group.append([9999900,1,'100',group_id,group_id]);group.sort()
                value=future_capture(sub,f['frontier'],f['module'],livegroup)
                with proc_effects(),self.assertRaises(ValueError):c.validate_fresh_closed_unlaunched(value,f['frontier'],f['module'])

if __name__=='__main__':unittest.main(verbosity=2)
