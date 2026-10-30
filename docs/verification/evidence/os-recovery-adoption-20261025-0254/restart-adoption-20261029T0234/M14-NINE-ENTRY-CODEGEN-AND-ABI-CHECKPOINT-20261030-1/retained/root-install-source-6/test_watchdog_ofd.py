"""Functional-only synthetic shared-description test. UNRUN; no real fork/flock."""
import hashlib
import json
import os
import stat
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

base=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'package'))
import graph_observations
import install_source_closure as install
import install_watchdog as subject

class ChildExit(BaseException):pass
class StopWait(BaseException):pass

class SharedDescriptionCases(unittest.TestCase):
    def test_watchdog_forks_same_lease_argument_without_child_flock(self):
        release={'purpose':'root-install-source-closure-v1','nonce':'a'*64,'controller_pid':88,
                 'controller_birth':'123','interpreter':{},'operation_root':{'device':1,'inode':2},'lease':{'device':3,'inode':4}}
        raw=b'synthetic-receipt';digest=hashlib.sha256(raw).hexdigest();calls=[]
        for key in ('controls_sha256','capacity_sha256','host_install_custody_sha256','owner_release_sha256'):release[key]=digest
        class Guard:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def fork_and_pin(self,record,child):
                try:child()
                except ChildExit:pass
                record.assigned(100);record.pin_pidfd(101);record.identified('456',101)
                return 100,101,'456'
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [1]
        fake_stat=types.SimpleNamespace(st_mode=stat.S_IFREG|0o600,st_uid=0)
        with patch.object(subject.os,'getuid',return_value=0),patch.object(subject.os,'geteuid',return_value=0),\
             patch.object(subject.os,'getpid',return_value=88),patch.object(subject.os,'getppid',return_value=87),\
             patch.object(subject.os,'getpgrp',return_value=20),patch.object(subject.os,'getpgid',return_value=20),patch.object(subject.os,'fstat',return_value=fake_stat),\
             patch.object(subject.os,'open',return_value=44),patch.object(subject.os,'fsync'),\
             patch.object(subject.os,'waitpid',return_value=(100,0)),patch.object(subject.os,'_exit',side_effect=ChildExit),\
             patch.object(subject.fcntl,'flock') as flock,patch.object(subject.obs,'process',return_value=('123',1,2)),\
             patch.object(subject,'check_time'),patch.object(subject,'require_launch_grace'),patch.object(subject,'watch_owned_child',return_value=0),patch.object(subject.select,'poll',return_value=Poll()),\
             patch.object(subject.signal,'pause',side_effect=StopWait),patch.object(subject.deferred_fork,'DeferredFork',Guard),\
             patch.object(install,'verify_release',return_value=release),patch.object(install,'verify_base_runtime'),patch.object(install,'verify_host_receipt'),patch.object(install,'root_file'),patch.object(install,'read_stable',return_value=raw),\
             patch.object(install,'dir_identity'),patch.object(install,'ident',return_value={'device':3,'inode':4}),\
             patch.object(install,'journal'),patch.object(install,'install',side_effect=lambda *args:calls.append(args)):
            with self.assertRaises(subject.WatchdogUnknown):
                subject.run(install,10,digest,11,12,13,14,15,16,17,18,19)
        flock.assert_called_once_with(14,subject.fcntl.LOCK_EX|subject.fcntl.LOCK_NB)
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][5],14)
    def test_graph_contract_is_package_local(self):
        self.assertEqual(graph_observations.CONTRACT_PATH,base/'package'/'parser'/'contract.json')


if __name__=='__main__':unittest.main()
