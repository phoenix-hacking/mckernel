"""Functional-only synthetic keeper identity and adoption fixtures. UNRUN."""
import hashlib
import io
import os
import select
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).resolve().parent;sys.path.insert(0,str(base/'package'))
import install_issuer as subject
from ownership_latch import CustodyLatch


class FakeInstall:
    def __init__(self):self.events=[]
    def journal(self,fd,event):self.events.append(event)


class KeeperCases(unittest.TestCase):
    def test_adopted_installer_and_timer_are_both_directly_joined(self):
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [(71,select.POLLIN),(72,select.POLLIN)]
        latch=CustodyLatch('KEEPER_HELD');install=FakeInstall()
        template={'deadline_boot_ns':100,'deadline_mono_ns':100,'utc_cap_ns':100}
        with patch.object(subject.select,'poll',return_value=Poll()),\
             patch.object(subject.time,'clock_gettime_ns',return_value=1),\
             patch.object(subject.time,'monotonic_ns',return_value=1),patch.object(subject.time,'time_ns',return_value=1),\
             patch.object(subject.os,'waitpid',side_effect=[(50,0),(60,9)]):
            with self.assertRaises(subject.IssuerUnknown):subject.monitor_owned(latch,install,9,50,71,60,72,template)
        event=install.events[-1]
        self.assertEqual((event['timer_direct_wait_status'],event['installer_direct_wait_status']),(0,9))
        self.assertTrue(event['installer_pidfd_terminal']);self.assertFalse(event['private_group_empty']);self.assertFalse(event['retirement'])
    def test_timer_reap_never_implies_installer_direct_join(self):
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [(71,select.POLLIN),(72,select.POLLIN)]
        latch=CustodyLatch('KEEPER_HELD');install=FakeInstall()
        template={'deadline_boot_ns':100,'deadline_mono_ns':100,'utc_cap_ns':100}
        with patch.object(subject.select,'poll',return_value=Poll()),\
             patch.object(subject.time,'clock_gettime_ns',return_value=1),\
             patch.object(subject.time,'monotonic_ns',return_value=1),patch.object(subject.time,'time_ns',return_value=1),\
             patch.object(subject.os,'waitpid',side_effect=[(50,0),ChildProcessError()]):
            with self.assertRaises(subject.IssuerUnknown):subject.monitor_owned(latch,install,9,50,71,60,72,template)
        event=install.events[-1]
        self.assertIsNone(event['installer_direct_wait_status']);self.assertTrue(event['installer_pidfd_terminal'])
        self.assertFalse(event['private_group_empty']);self.assertFalse(event['complete_install_proof'])
    def test_private_group_rejects_campaign_actor_before_executable_read(self):
        rows={50:{'pid':50,'birth':12,'ppid':40,'pgrp':50,'sid':3},60:{'pid':60,'birth':13,'ppid':50,'pgrp':50,'sid':3}}
        prelim=types.SimpleNamespace(identity=lambda pid:dict(rows[pid]))
        ready={'pid':60,'birth':'13','parent_pid':50,'pgrp':50};actors=[{'pid':n} for n in range(6)]
        with patch.object(subject.os,'getpid',return_value=40),patch.object(subject.os,'getpgrp',return_value=20),\
             patch.object(subject.os,'getpgid',side_effect=lambda pid:50 if pid==2 else 20):
            with self.assertRaisesRegex(ValueError,'owner inside private group'):
                subject.verify_private_group(prelim,FakeInstall(),{'outer_pid':7},50,'12',ready,[],actors)

if __name__=='__main__':unittest.main()
