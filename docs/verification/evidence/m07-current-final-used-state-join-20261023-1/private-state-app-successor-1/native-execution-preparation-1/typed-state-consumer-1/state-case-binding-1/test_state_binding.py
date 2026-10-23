"""Functional OS controlled binding fixtures only; no security testing or workload."""
import copy
import importlib.util
from pathlib import Path
import json
from unittest import mock
spec=importlib.util.spec_from_file_location("state_parser_tests",Path(__file__).with_name("test_typed_state.py"))
tests=importlib.util.module_from_spec(spec);spec.loader.exec_module(tests)
runner,TypedStateTests=tests.runner,tests.TypedStateTests
import unittest

PREFIX = 'os=0 generation=1 pid=256'
def trace():
    # TESTONLY same-PID waiter registration shape retained by old accepted M07.
    return '\n'.join(['application procfs published '+PREFIX+' tid=256',
      'application procfs published '+PREFIX+' tid=258',
      'application_syscall=delivered '+PREFIX+' worker=6 delivery=18 cpu=0 number=202',
      'application_syscall=returned '+PREFIX+' worker=6 delivery=18 cpu=0 value=0',
      'application procfs deleted '+PREFIX+' tid=258',
      'application_syscall=delivered '+PREFIX+' worker=5 delivery=19 cpu=0 number=231',
      'application procfs deleted '+PREFIX+' tid=256'])

class StateBindingTests(unittest.TestCase):
    def binding(self):
        return ({'case_id':runner.STATE_CASE_ID},
          {'argv':['/bin/mcexec','-t','1','0','/apps/app'], 'env':dict(runner.STATE_ENV),
           'oracle':{'stdout_typed':dict(runner.STATE_ORACLE)}},
          {'memory_mib':8192,'vcpus':4,'numa_nodes':2})
    def test_fixed_guest_logical_cpu_zero(self):
        runner._validate_state_case_binding(*self.binding())
        # Actual legacy validator with controlled artifact-resolution only.
        # Generic payload env remains exact even when a state case exists.
        baseline=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-readiness-runtime-failure-2/coherent-successor-preparation-1/actual-stage-successor-1/manifest.json')
        obj=json.loads(baseline.read_text());obj.pop('cleanup_profile',None)
        with mock.patch.object(runner,'_ref',side_effect=lambda row,name:row), mock.patch.object(runner,'_staging',return_value={}):
            runner._legacy_cleanup_validate_manifest(obj)
            obj['payload']['env']['PAIR_CPU']='0'
            with self.assertRaises(runner.DiagnosticError):runner._legacy_cleanup_validate_manifest(obj)
    def test_extra_env_and_host_cpu_confusion_refused(self):
        for cpu in ('1','2','00'):
            obj,payload,profile=self.binding();payload['env']['PAIR_CPU']=cpu
            with self.assertRaises(runner.DiagnosticError):runner._validate_state_case_binding(obj,payload,profile)
        obj,payload,profile=self.binding();payload['env']['OTHER']='x'
        with self.assertRaises(runner.DiagnosticError):runner._validate_state_case_binding(obj,payload,profile)
    def test_wrong_case_and_profile_refused(self):
        obj,payload,profile=self.binding();obj['case_id']='other'
        with self.assertRaises(runner.DiagnosticError):runner._validate_state_case_binding(obj,payload,profile)
        obj,payload,profile=self.binding();profile['vcpus']=2
        with self.assertRaises(runner.DiagnosticError):runner._validate_state_case_binding(obj,payload,profile)
    def test_wrong_payload_tail_refused(self):
        obj,payload,profile=self.binding();payload['argv'].append('threads')
        with self.assertRaises(runner.DiagnosticError):runner._validate_state_case_binding(obj,payload,profile)
    def test_exact_parent_waiter_trace(self):
        result=runner._check_state_thread_trace(trace(),PREFIX)
        self.assertEqual(result['waiter_tid'],258)
        lines=trace().splitlines();lines.insert(3,'application_syscall=return_route '+PREFIX+' worker=6 delivery=18 launcher_cpu=1 guest_cpu=0')
        serial='\n'.join(lines+['application retirement '+PREFIX+' token=1 errno=0','application_process=release '+PREFIX+' cleanup_errno=0'])
        runner._check_syscall_trace(serial,PREFIX)
        runner._check_state_thread_trace(serial,PREFIX)
        with self.assertRaises(runner.DiagnosticError):runner._check_syscall_trace(serial.replace('launcher_cpu=1 guest_cpu=0','launcher_cpu=2 guest_cpu=0'),PREFIX)
        with self.assertRaises(runner.DiagnosticError):runner._check_syscall_trace(serial.replace('cpu=0 number=202','cpu=1 number=202'),PREFIX)
    def test_missing_or_duplicate_or_foreign_registration_refused(self):
        for text in (trace().replace('application procfs deleted '+PREFIX+' tid=258',''),
                     trace()+'\napplication procfs published '+PREFIX+' tid=258',
                     trace().replace('tid=258','tid=259',1),
                     trace().replace('application procfs published '+PREFIX+' tid=258',
                                     'application procfs published os=0 generation=2 pid=256 tid=258')):
            with self.assertRaises(runner.DiagnosticError):runner._check_state_thread_trace(text,PREFIX)
    def test_waiter_after_parent_exit_refused(self):
        lines=trace().splitlines();lines[4],lines[5]=lines[5],lines[4]
        with self.assertRaises(runner.DiagnosticError):runner._check_state_thread_trace('\n'.join(lines),PREFIX)
    def test_futex_must_be_observed_inside_waiter_lifetime(self):
        with self.assertRaises(runner.DiagnosticError):runner._check_state_thread_trace(trace().replace('number=202','number=39'),PREFIX)

if __name__=='__main__':unittest.main(verbosity=2)
