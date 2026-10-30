"""Functional-only synthetic scoped custody/deadline fixtures. UNRUN."""
import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
base=Path(__file__).resolve().parent;sys.path.insert(0,str(base/'package'))
import install_source_closure as install
import install_watchdog as watchdog


class ScopeCases(unittest.TestCase):
    def receipt(self):
        return {'version':1,'record_type':'HOST_INSTALL_RESOURCE_CUSTODY_V1','scope':'ROOT_CODE_INSTALL_ONLY',
          'native_release':False,'native_currentfree':None,'no_unlisted_later_operation':'UNKNOWN','v2_birth':None,
          'retained_2gib_bytes':2147483648,'native12':'HELD','scratch21':'HELD','mutex27_4':'HELD',
          'boot_id':'boot','nonce':'a'*64,'issued_boot_ns':10,'expires_boot_ns':90,
          'host_available_bytes':20*1024**3,'host_floor_bytes':16*1024**3,'owner_release_sha256':'b'*64}
    def test_scoped_host_record_never_accepts_native_currentfree(self):
        value=self.receipt();raw=json.dumps(value).encode()
        release={'host_install_custody_sha256':hashlib.sha256(raw).hexdigest(),'boot_id':'boot','nonce':'a'*64,
                 'owner_release_sha256':'b'*64,'deadline_boot_ns':100}
        with patch.object(install,'root_file'),patch.object(install,'read_stable',return_value=raw),\
             patch.object(install.time,'clock_gettime_ns',return_value=20):
            self.assertEqual(install.verify_host_receipt(7,release)['native_currentfree'],None)
        value['native_currentfree']={'invented':True};raw=json.dumps(value).encode()
        release['host_install_custody_sha256']=hashlib.sha256(raw).hexdigest()
        with patch.object(install,'root_file'),patch.object(install,'read_stable',return_value=raw),\
             patch.object(install.time,'clock_gettime_ns',return_value=20):
            with self.assertRaises(ValueError):install.verify_host_receipt(7,release)


class DeadlineCases(unittest.TestCase):
    def test_owned_pidfd_term_kill_then_direct_join(self):
        class Poll:
            def __init__(self):self.count=0
            def register(self,*args):pass
            def poll(self,timeout):
                self.count+=1
                return [1] if self.count>=3 else []
        release={'term_grace_ns':1000000000,'kill_grace_ns':1000000000,'join_grace_ns':1000000000}
        times=iter((0,2000000000,4000000000));events=[]
        with patch.object(watchdog,'remaining_ns',return_value=3100000000),\
             patch.object(watchdog.select,'poll',return_value=Poll()),\
             patch.object(watchdog.time,'clock_gettime_ns',side_effect=lambda *args:next(times)),\
             patch.object(watchdog.pidfd_compat,'send_signal') as send,\
             patch.object(watchdog.os,'waitpid',return_value=(55,0)),\
             patch.object(install,'journal',side_effect=AssertionError('journal must not precede join')):
            self.assertEqual(watchdog.watch_owned_child(install,release,55,77,9,events),0)
        self.assertEqual([x.args for x in send.call_args_list],[(77,watchdog.signal.SIGTERM),(77,watchdog.signal.SIGKILL)])
    def test_insufficient_grace_attempts_pidfd_kill_then_unknown(self):
        class Poll:
            def register(self,*args):pass
            def poll(self,timeout):return []
        release={'term_grace_ns':1000000000,'kill_grace_ns':1000000000,'join_grace_ns':1000000000}
        with patch.object(watchdog,'remaining_ns',return_value=100),\
             patch.object(watchdog.select,'poll',return_value=Poll()),\
             patch.object(watchdog.pidfd_compat,'send_signal') as send:
            with self.assertRaises(TimeoutError):watchdog.watch_owned_child(install,release,55,77,9,[])
        send.assert_called_once_with(77,watchdog.signal.SIGKILL)

if __name__=='__main__':unittest.main()
