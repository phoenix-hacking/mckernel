"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic accounting-only fixture source, NOT RUN; never qualifies real evidence.
"""
import copy
import unittest
import cumulative_accounting as c
from test_cumulative_accounting import inputs,fixture_qualifier

def uart_inputs():
    prefix,short=inputs()
    short.update(original_terminal_status='FAIL',original_failure_reason='trace exact bytes/cap',original_result_sha256='c'*64)
    adj=dict(schema='p12.uart-onlcr-offline-adjudication.v1',original_terminal_status='FAIL',
        original_failure_reason='trace exact bytes/cap',adjudicated_terminal_status='SEGMENT_PASS',
        transport_decoding='uniform_CRLF_to_LF',replay_status='PROTOCOL_PASS',
        raw_capture_sha256=short['evidence_sha256'],original_result_sha256='c'*64,
        manifest_sha256='d'*64,original_consumer_sha256='e'*64,successor_consumer_sha256='f'*64,
        unchanged_pair_checker_sha256='1'*64,raw_trace_sha256='2'*64,
        decoded_trace_sha256='3'*64,replay_evidence_sha256='4'*64)
    short['offline_adjudication']=adj
    return prefix,short

def uart_qualifier(receipt):
    proof=fixture_qualifier(receipt)
    if receipt['kind']=='completed-short-segment':
        proof['offline_adjudication']=copy.deepcopy(receipt['offline_adjudication'])
    return proof

class OfflineAdjudicationFixture(unittest.TestCase):
    def test_original_success_remains_accepted(self):
        prefix,short=inputs();result=c.combine(prefix,short,fixture_qualifier)
        self.assertEqual(result['short_original_terminal_status'],'SEGMENT_PASS')
        self.assertEqual(result['short_adjudicated_terminal_status'],'SEGMENT_PASS')
        self.assertIsNone(result['short_offline_adjudication'])
    def test_raw_failure_without_qualified_adjudication_rejected(self):
        prefix,short=uart_inputs()
        with self.assertRaises(c.AccountingError):c.combine(prefix,short,fixture_qualifier)
        short.pop('offline_adjudication')
        with self.assertRaises(c.AccountingError):c.combine(prefix,short,fixture_qualifier)
    def test_uart_strict_replay_preserves_both_statuses(self):
        prefix,short=uart_inputs();result=c.combine(prefix,short,uart_qualifier)
        self.assertEqual(result['status'],'CUMULATIVE_PASS')
        self.assertEqual(result['short_original_terminal_status'],'FAIL')
        self.assertEqual(result['short_adjudicated_terminal_status'],'SEGMENT_PASS')
        self.assertEqual(result['short_offline_adjudication'],short['offline_adjudication'])
        self.assertEqual(short['original_terminal_status'],'FAIL')
        self.assertEqual(result['original_single_session_status'],'FAIL')
        self.assertFalse(result['uninterrupted_pass'])
    def test_wrong_capture_replay_binding_and_reason_rejected(self):
        for field,value in [('raw_capture_sha256','9'*64),('original_result_sha256','9'*64),
                            ('original_failure_reason','different failure'),('transport_decoding','drop_CR_anywhere'),
                            ('replay_status','FAIL'),('replay_evidence_sha256','not-a-hash')]:
            with self.subTest(field=field):
                prefix,short=uart_inputs();short['offline_adjudication'][field]=value
                with self.assertRaises(c.AccountingError):c.combine(prefix,short,uart_qualifier)
        prefix,short=uart_inputs();short['original_failure_reason']='different failure'
        with self.assertRaises(c.AccountingError):c.combine(prefix,short,uart_qualifier)
        prefix,short=uart_inputs()
        def mismatched_independent_replay(receipt):
            proof=uart_qualifier(receipt)
            if 'offline_adjudication' in proof:proof['offline_adjudication']['replay_evidence_sha256']='9'*64
            return proof
        with self.assertRaises(c.AccountingError):c.combine(prefix,short,mismatched_independent_replay)

if __name__=='__main__':unittest.main()
