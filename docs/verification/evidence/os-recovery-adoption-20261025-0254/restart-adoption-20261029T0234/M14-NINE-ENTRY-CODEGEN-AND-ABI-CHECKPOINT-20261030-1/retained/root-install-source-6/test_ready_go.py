"""Functional-only synthetic READY/GO fixtures. UNRUN, no root/fork/signal."""
import hashlib
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'package'))
import install_issuer as subject
import install_source_closure as install

class ReadyGoCases(unittest.TestCase):
    def test_known_outer_caller_verified_through_sudo_chain(self):
        rows={20:{'pid':20,'birth':5,'ppid':10},10:{'pid':10,'birth':3,'ppid':1}}
        prelim=types.SimpleNamespace(identity=lambda pid:dict(rows[pid]))
        with patch.object(subject.os,'getppid',return_value=20):
            subject.require_outer_ancestor(prelim,10,'3')
            with self.assertRaises(ValueError):subject.require_outer_ancestor(prelim,10,'4')
    def test_frame_reader_handles_short_read_and_deadline(self):
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [1]
        with patch.object(subject.select,'poll',return_value=Poll()),\
             patch.object(subject.time,'clock_gettime_ns',return_value=1),\
             patch.object(subject.os,'read',side_effect=[b'a',b'bc']):
            self.assertEqual(subject.read_exact(7,3,10),b'abc')
        with patch.object(subject.select,'poll',return_value=Poll()),\
             patch.object(subject.time,'clock_gettime_ns',return_value=10):
            with self.assertRaises(TimeoutError):subject.read_exact(7,1,10)
    def test_live_control_byte_change_refuses_go(self):
        a=b'controls';b=b'capacity';rows={str(install):None}
        prelim=types.SimpleNamespace(CONTROLS='c',CAPACITY='p',
            read_bound=lambda path,limit:(a if path=='c' else b,{}),
            strict_json=lambda raw:{},controller_checks=lambda *args:{'boot_id':'boot','boot_deadline':20,'monotonic_deadline':20,'deadline':20})
        template={'controls_sha256':hashlib.sha256(a).hexdigest(),'capacity_sha256':'0'*64,
                  'boot_id':'boot','deadline_boot_ns':10,'deadline_mono_ns':10,'utc_cap_ns':10}
        with patch.object(subject,'bounds'):
            with self.assertRaisesRegex(ValueError,'control bytes changed'):subject.fresh_controls(prelim,template,install,10,{})


if __name__=='__main__':unittest.main()
