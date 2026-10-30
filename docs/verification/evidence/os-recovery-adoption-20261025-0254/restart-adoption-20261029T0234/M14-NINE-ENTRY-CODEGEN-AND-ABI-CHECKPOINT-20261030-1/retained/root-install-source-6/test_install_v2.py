"""Functional-only synthetic installer fixtures. UNRUN; no root or actual IO."""
import unittest
from unittest.mock import patch
import install_source_closure as subject


class WriterCloseCases(unittest.TestCase):
    def test_success_records_close_before_verified_output(self):
        events=[];held=[71]
        def event(fd,value):events.append(value['state'])
        def close(fd):self.assertNotIn(fd,held);events.append('close')
        with patch.object(subject,'_HELD',held),patch.object(subject,'journal',side_effect=event),\
             patch.object(subject.signal,'pthread_sigmask',return_value=set()),\
             patch.object(subject.os,'close',side_effect=close):
            subject.finish_writer(71,9,'a.py',{'device':1,'inode':2})
        self.assertEqual(events,['BEFORE_WRITER_CLOSE','close','WRITER_CLOSED'])
        self.assertEqual(held,[])
    def test_uncertain_close_never_retains_or_retries_numeric_fd(self):
        events=[];held=[72]
        def event(fd,value):events.append(value)
        with patch.object(subject,'_HELD',held),patch.object(subject,'journal',side_effect=event),\
             patch.object(subject.signal,'pthread_sigmask',return_value=set()),\
             patch.object(subject.os,'close',side_effect=OSError('synthetic')) as close:
            with self.assertRaises(OSError):subject.finish_writer(72,9,'a.py',{'device':1,'inode':2})
        close.assert_called_once_with(72);self.assertEqual(held,[])
        self.assertEqual(events[-1]['state'],'WRITER_CLOSURE_UNKNOWN')
        self.assertTrue(events[-1]['do_not_use_or_retry'])


if __name__=='__main__':unittest.main()
