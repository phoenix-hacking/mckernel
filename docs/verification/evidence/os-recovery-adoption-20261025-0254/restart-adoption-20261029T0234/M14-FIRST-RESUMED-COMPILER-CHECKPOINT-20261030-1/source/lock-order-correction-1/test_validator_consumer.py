"""Functional source-only synthetic tests. UNRUN; no root, fork, or pidfd.
The fake consumer is patched only in the test, never a production entrypoint.
"""
import unittest
from unittest.mock import patch
import compositor
import validator_consumer
import validator_entry


class Session:
    def __init__(self,events,close_error=False):
        self.closed=False;self.events=events;self.close_error=close_error
    def close(self,owner):
        self.events.append('close')
        if self.close_error:raise OSError('synthetic uncertain close')
        self.closed=True


class Plan:
    def __init__(self,events,close_error=False):
        self.events=events;self.session=Session(events,close_error)
    def revalidate(self):
        if self.session.closed:raise RuntimeError('early close')
        self.events.append('revalidate')


class Owner:
    def __init__(self,events):self.events=events;self.state='HELD';self.saved=None
    def retain_session_unknown(self,session,plan=None):
        self.events.append('unknown');self.state='UNKNOWN_RETAINED';self.saved=(session,plan)


class ConsumerCases(unittest.TestCase):
    def test_live_during_consumer_and_terminal_close_order(self):
        events=[];plan=Plan(events);owner=Owner(events)
        def consumer(actual):
            self.assertIs(actual,plan);self.assertFalse(actual.session.closed)
            events.append('consume');actual.revalidate()
            return validator_consumer.SourceCollection(b'')
        with patch.object(validator_consumer,'consume',side_effect=consumer):
            result=validator_entry._consume_prepared(plan,owner)
            self.assertEqual(result.value,b'')
        self.assertEqual(events,['revalidate','consume','revalidate','revalidate','close'])
        self.assertTrue(plan.session.closed);self.assertEqual(owner.state,'HELD')
    def test_failure_preserves_plan_and_live_session(self):
        events=[];plan=Plan(events);owner=Owner(events)
        def consumer(actual):
            self.assertFalse(actual.session.closed);events.append('consume')
            raise RuntimeError('synthetic consumer failure')
        with patch.object(validator_consumer,'consume',side_effect=consumer):
            with self.assertRaises(RuntimeError):validator_entry._consume_prepared(plan,owner)
        self.assertEqual(events,['revalidate','consume','unknown'])
        self.assertIs(owner.saved[0],plan.session);self.assertIs(owner.saved[1],plan)
        self.assertFalse(plan.session.closed)
    def test_terminal_close_failure_is_unknown_no_retry(self):
        events=[];plan=Plan(events,True);owner=Owner(events)
        with patch.object(validator_consumer,'consume',return_value=validator_consumer.SourceCollection(b'')):
            with self.assertRaises(OSError):validator_entry._consume_prepared(plan,owner)
        self.assertEqual(events,['revalidate','revalidate','close','unknown'])
        self.assertIs(owner.saved[1],plan);self.assertEqual(owner.state,'UNKNOWN_RETAINED')
    def test_actual_consumer_stops_at_existing_source_gate(self):
        events=[];plan=Plan(events);owner=Owner(events)
        with patch.object(compositor,'_accept_source_binding',wraps=compositor._accept_source_binding) as gate,\
             patch.object(compositor,'_accept_effective_view') as effective,\
             patch.object(compositor,'_collect') as collect:
            with self.assertRaisesRegex(ValueError,'SOURCE_ONLY'):
                validator_entry._consume_prepared(plan,owner)
        gate.assert_called_once_with(plan);effective.assert_not_called();collect.assert_not_called()
        self.assertEqual(events,['revalidate','revalidate','unknown'])
        self.assertFalse(plan.session.closed)
    def test_stdout_data_record_is_canonical_and_bound(self):
        import base64,hashlib,json
        data=b'abc\x00';result=validator_consumer.SourceCollection(data)
        raw=validator_consumer.stdout_record(result,'a'*64)
        value=json.loads(raw)
        self.assertEqual(value,{'record_type':'source_collection_result_data_v1','authority':None,
            'nonce':'a'*64,'payload_length':4,'payload_sha256':hashlib.sha256(data).hexdigest(),
            'payload_base64':base64.b64encode(data).decode('ascii')})
        self.assertEqual(raw,(json.dumps(value,sort_keys=True,separators=(',',':'))+'\n').encode('ascii'))
    def test_stdout_refuses_oversize_with_actual_lengths(self):
        result=validator_consumer.SourceCollection(b'ab')
        with patch.object(validator_consumer,'MAX_RESULT_OUTPUT_BYTES',1):
            with self.assertRaisesRegex(ValueError,'payload length 2'):
                validator_consumer.stdout_record(result,'a'*64)
        with patch.object(validator_consumer,'MAX_RESULT_OUTPUT_BYTES',2):
            with self.assertRaisesRegex(ValueError,'record length .*payload length 2'):
                validator_consumer.stdout_record(result,'a'*64)

    def test_actual_emitter_partial_write_retains_operation(self):
        class Stream:
            def write(self,raw):return len(raw)-1
            def flush(self):raise AssertionError('short output must not flush')
        class Operation:
            session=object();plan=object();state='REGISTERED'
            def retain_session_unknown(self,session,plan):
                self.state='UNKNOWN_RETAINED';self.held=(session,plan)
        operation=Operation()
        with self.assertRaisesRegex(RuntimeError,'short diagnostic'):
            validator_entry.emit_stdout(validator_consumer.SourceCollection(b'ok'),operation,Stream(),'a'*64)
        self.assertEqual(operation.state,'UNKNOWN_RETAINED')
        self.assertEqual(operation.held,(operation.session,operation.plan))
    def test_actual_emitter_oversize_retains_operation(self):
        class Operation:
            session=object();plan=object();state='REGISTERED'
            def retain_session_unknown(self,session,plan):self.state='UNKNOWN_RETAINED'
        operation=Operation()
        with patch.object(validator_consumer,'MAX_RESULT_OUTPUT_BYTES',1):
            with self.assertRaisesRegex(ValueError,'payload length 2'):
                validator_entry.emit_stdout(validator_consumer.SourceCollection(b'ab'),operation,object(),'a'*64)
        self.assertEqual(operation.state,'UNKNOWN_RETAINED')

    def test_operation_retains_session_even_if_journal_publish_fails(self):
        events=[];plan=Plan(events)
        class Record:
            state='VERIFIED_HELD';fd=19;target_pid=7;target_birth='3'
            def retain_unknown(self,*args):
                self.state='UNKNOWN_RETAINED';raise OSError('synthetic publication failure')
        owner=compositor.OperationCustody(9,'a'*64);owner.record=Record()
        owner.retain_session_unknown(plan.session,plan)
        self.assertEqual(owner.state,'UNKNOWN_RETAINED');self.assertIs(owner.plan,plan)
        self.assertIn(owner,compositor._UNKNOWN_OWNERS)
        self.assertIsInstance(owner.publication_error,OSError)


if __name__=='__main__':unittest.main()
