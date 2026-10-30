"""Functional McKernel-only synthetic profile/monitor regressions. UNRUN.
No real root, fork, signal, pidfd operation, or workload.
"""
import hashlib
import json
import signal
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
EXPECTED_BOOTSTRAP='40d470de1538548a4c4a3075f867257dc550f89b7c1593a3e75c76eca0edc87a'
EXPECTED_ISSUER='18196891bdd58e29488c70a780f589787103b17c1f44e1a6e6b9de94f2985edd'
EXPECTED_COMPLETION='87092d1fa2a30b8fa1609c9692dd4dbd95953de518d8d846fbaeb2d6fe714e23'
EXPECTED_CLOSURE='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def load_subject():
    if digest(BASE/'install_issuer.py')!=EXPECTED_ISSUER or digest(BASE/'install_completion.py')!=EXPECTED_COMPLETION or digest(BASE/'SOURCE-CLOSURE.json')!=EXPECTED_CLOSURE:
        raise ValueError('frozen monitor source changed')
    closure=json.loads((BASE/'SOURCE-CLOSURE.json').read_bytes())
    pinned={row['name']:row['sha256'] for row in closure['files']}
    for name in ('ownership_latch.py','graph_observations.py','pidfd_compat.py','pidfd_custody.py','deferred_fork.py'):
        if digest(BASE/'package'/name)!=pinned[name]:raise ValueError('frozen monitor dependency changed')
    sys.path.insert(0,str(BASE/'package'));sys.path.insert(0,str(BASE))
    import install_issuer
    import install_completion
    from ownership_latch import CustodyLatch
    return install_issuer,install_completion,CustodyLatch


class ProfileCases(unittest.TestCase):
    def test_complete_argv_and_exact_pinned_python_literal(self):
        profile=json.loads((HERE/'INSTALL-PROFILE.SOURCE-ONLY.json').read_bytes())
        original=json.loads((BASE/'INSTALL-PROFILE.SOURCE-ONLY.json').read_bytes())
        source=(BASE/'BOOTSTRAP-CODE.py').read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),EXPECTED_BOOTSTRAP)
        self.assertEqual(profile['bootstrap_literal_sha256'],EXPECTED_BOOTSTRAP)
        prefix=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','6','/usr/bin/prlimit',
                '--as=1073741824:1073741824','--cpu=60:60','--fsize=33554432:33554432',
                '--nofile=256:256','--core=0:0','--','/usr/bin/python3','-I','-B','-c']
        suffix=['<INSTALLER_SOURCE_PATH>','<ISSUER_SOURCE_PATH>','<COMPLETION_SOURCE_PATH>',
          '<PRELIM_READER_SOURCE_PATH>','<WAIT_LITERAL_PATH>','<TIMEOUT_PROOF_PATH>',
          '<ROOT_IMMUTABLE_EXPERT_REVIEW_PATH>','<EXPERT_REVIEW_SHA256>',
          '<ROOT_IMMUTABLE_START_INTENT_PATH>','<START_INTENT_SHA256>','<SOURCE_PACKAGE_PATH>',
          '<PRIVATE_OPERATION_ROOT_PATH>','<TRAVERSABLE_CODE_PARENT_PATH>','<LEASE_PATH>',
          '<SOURCE_CLOSURE_PATH>','<CONTROLS_RECEIPT_PATH>','<CAPACITY_RECEIPT_PATH>',
          '<HOST_INSTALL_CUSTODY_PATH>','<OWNER_RELEASE_PATH>']
        self.assertEqual(profile['outer_argv_template'],prefix+[source.decode('utf-8')]+suffix)
        self.assertEqual({k:v for k,v in profile.items() if k!='outer_argv_template'},
                         {k:v for k,v in original.items() if k!='outer_argv_template'})


class MonitorCases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.subject,cls.completion,cls.latch_type=load_subject()
    def invoke(self,events,waits):
        class Poll:
            def register(self,*args):pass
            def unregister(self,*args):pass
            def poll(self,*args):return events
        latch=self.latch_type('KEEPER_HELD')
        with patch.object(self.subject.select,'poll',return_value=Poll()),\
             patch.object(self.completion,'remaining',return_value=100),\
             patch.object(self.subject.os,'waitpid',side_effect=waits) as wait:
            result=self.subject.monitor_owned(latch,object(),9,50,71,60,72,{},10)
        return result,wait
    def test_timer_zero_and_same_installer_terminal_with_echild(self):
        result,wait=self.invoke([(71,self.subject.select.POLLIN),(72,self.subject.select.POLLHUP)],[(50,0),ChildProcessError()])
        self.assertEqual(result,{'timer_direct_wait_status':0,'installer_pidfd_terminal':True,'installer_direct_wait_status':None})
        self.assertEqual([call.args for call in wait.call_args_list],[(50,self.subject.os.WNOHANG),(60,self.subject.os.WNOHANG)])
    def test_nonzero_timer_is_unknown(self):
        with self.assertRaises(self.subject.IssuerUnknown):
            self.invoke([(71,self.subject.select.POLLIN),(72,self.subject.select.POLLIN)],[(50,256),ChildProcessError()])
    def test_signaled_timer_is_unknown(self):
        with self.assertRaises(self.subject.IssuerUnknown):
            self.invoke([(71,self.subject.select.POLLIN),(72,self.subject.select.POLLIN)],[(50,signal.SIGTERM),ChildProcessError()])
    def test_adopted_installer_nonzero_is_unknown(self):
        with self.assertRaises(self.subject.IssuerUnknown):
            self.invoke([(71,self.subject.select.POLLIN),(72,self.subject.select.POLLIN)],[(50,0),(60,256)])
    def test_pidfd_poll_error_never_performs_wait(self):
        poll_error = self.subject.select.POLLERR
        class Poll:
            def register(self,*args):pass
            def poll(self,*args):return [(72,poll_error)]
        latch=self.latch_type('KEEPER_HELD')
        with patch.object(self.subject.select,'poll',return_value=Poll()),\
             patch.object(self.completion,'remaining',return_value=100),\
             patch.object(self.subject.os,'waitpid') as wait:
            with self.assertRaises(self.subject.IssuerUnknown):
                self.subject.monitor_owned(latch,object(),9,50,71,60,72,{},10)
        wait.assert_not_called()


if __name__=='__main__':unittest.main()
