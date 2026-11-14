"""Functional-only R3 note-binding fixture; UNRUN, no processes or signals."""
import importlib.util
import types
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('test_r3_control_stop',HERE/'control_stop.py')
stop=importlib.util.module_from_spec(spec);spec.loader.exec_module(stop)


class FailureBinding(unittest.TestCase):
    def test_exact_two_error_notes_bind_keeper_and_parent(self):
        common={'record_type':'ROOT_INSTALL_FAILURE_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY','authority':None,
          'native_release':False,'native_currentfree':None,'outcome':'UNKNOWN','errno':None,'message_policy':'exact_fixed',
          'root_parent':{'pid':stop.ROOT,'birth':stop.ROOT_BIRTH},'keeper':{'pid':stop.KEEPER,'birth':stop.KEEPER_BIRTH}}
        first=dict(common,role='keeper',stage='child_entry',error_class='ValueError',error_message='directory ancestry is not root controlled')
        second=dict(common,role='root_parent',stage='lease_handoff',error_class='Unknown',error_message='custody channel lost')
        raw=stop.canonical(first)+stop.canonical(second);capture={'stderr':{'device':8,'inode':9}}
        with mock.patch.object(stop,'checked',return_value=raw),mock.patch.object(stop.os,'stat',return_value=types.SimpleNamespace(st_dev=8,st_ino=9)):
            self.assertEqual(stop.failure_notes(capture),[first,second])
            changed=dict(first,keeper={'pid':stop.KEEPER+1,'birth':stop.KEEPER_BIRTH})
            with mock.patch.object(stop,'checked',return_value=stop.canonical(changed)+stop.canonical(second)):
                with self.assertRaises(ValueError):stop.failure_notes(capture)


if __name__=='__main__':unittest.main()
