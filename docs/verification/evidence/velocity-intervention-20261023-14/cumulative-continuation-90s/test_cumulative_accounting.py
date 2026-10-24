"""Proposed host accounting fixture only. NOT EXECUTED; no native acceptance.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import copy
import unittest
import cumulative_accounting as c

def receipt(kind,profile,durations,nonce):
    rows=[];at=1
    for i,work in enumerate(durations):
        rows.append(dict(round=i,complete=True,start_ns=at,end_ns=at+work+2,apps=[dict(pid=i*2+1,started_ns=at+1,reaped_ns=at+work+1,finished_ns=at+work+2),dict(pid=i*2+2,started_ns=at+1,reaped_ns=at+work+1,finished_ns=at+work+2)]));at+=work+3
    return dict(kind=kind,profile=copy.deepcopy(profile),completed_rounds=rows,verified_work_ns=sum(durations),verified_launches=2*len(rows),nonce=nonce,segment_id=nonce,evidence_sha256=nonce*64,artifact_bindings=dict(kernel='10972',modules=['SDK8'],apps=['app0','app1'],launcher='dca025'),original_terminal_status='FAIL' if kind.startswith('failed') else 'SEGMENT_PASS',excluded_failing_round=len(rows))

def inputs():
    # Actual old sum represented by valid synthetic <=10s mixed rounds for unit accounting.
    old=[7_000_000_000]*502+[5_690_949_712]
    return receipt('failed-session-completed-prefix',c.PREFIX_PROFILE,old,'a'),receipt('completed-short-segment',c.SHORT_PROFILE,[9_000_000_000]*10,'b')

class AccountingFixture(unittest.TestCase):
    def test_exact_remaining_and90s(self):
        self.assertEqual(c.REMAINING_NS,80_309_050_288)
        old,new=inputs();got=c.combine(old,new,lambda _:True)
        self.assertEqual(got['actual_mixed_work_ns'],3_609_690_949_712)
        self.assertFalse(got['uninterrupted_pass']);self.assertEqual(got['original_single_session_status'],'FAIL')
    def test_mismatch_profile_duplicate_failing_wall_and_missing_proof(self):
        mutations=[lambda p,s:s['artifact_bindings'].update(kernel='different'),lambda p,s:s['profile'].update(version=1),lambda p,s:s.update(segment_id=p['segment_id']),lambda p,s:s.update(nonce=p['nonce']),lambda p,s:s.update(evidence_sha256=p['evidence_sha256']),lambda p,s:s['completed_rounds'][0].update(complete=False),lambda p,s:s['completed_rounds'][1].update(round=0),lambda p,s:s.update(verified_work_ns=s['completed_rounds'][-1]['end_ns']),lambda p,s:s['completed_rounds'][-1].update(end_ns=600_000_000_001)]
        for change in mutations:
            with self.subTest(change=change):
                p,s=copy.deepcopy(inputs());change(p,s)
                with self.assertRaises(c.AccountingError):c.combine(p,s,lambda _:True)
        p,s=inputs()
        with self.assertRaises(c.AccountingError):c.combine(p,s,lambda _:False)
    def test_no_prefix_counter_only_credit(self):
        p,s=inputs();p['verified_work_ns']+=1
        with self.assertRaises(c.AccountingError):c.combine(p,s,lambda _:True)
    def test_short_below_target_rejected(self):
        p,s=inputs();s=receipt('completed-short-segment',c.SHORT_PROFILE,[8_000_000_000]*10,'b')
        with self.assertRaises(c.AccountingError):c.combine(p,s,lambda _:True)

if __name__=='__main__':unittest.main()
