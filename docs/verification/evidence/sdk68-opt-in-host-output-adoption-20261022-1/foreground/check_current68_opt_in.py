"""Targeted flag-flow checks only; no compiler, Docker, guest or root work.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Run only after the coordinator grants the ordinary CPU/RAM profile.
"""
from pathlib import Path
import copy
import importlib.util
import json
import shlex
import tempfile
import unittest
from unittest.mock import patch

D = Path(__file__).resolve().parent
P = D / 'source/docs/verification/evidence/current68-host-control-sdk-preparation-20261022-1.json'
SPEC = importlib.util.spec_from_file_location(
    'isolated_current68_opt_in', D / 'source/scripts/native_running_external_modules_offline.py')
driver = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(driver)
CFG = 'mckernel_current_fork_adoption_opt_in'


class OptInFlow(unittest.TestCase):
    def setUp(self):
        self.manifest = driver.load_preparation(P)

    def test_pinned_preparation_reaches_exact_make_plan(self):
        plan = driver.plan(self.manifest)
        self.assertIs(self.manifest['host_fork_adoption_opt_in'], True)
        self.assertEqual(plan['argv'][-3:], ['--jobserver-style=pipe', '-j2', 'modules'])
        self.assertEqual(plan['argv'].count('MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=1'), 1)
        self.assertEqual(len(driver.EXACT_SOURCE_MAP), 68)
        self.assertFalse(plan['execution_release'])

    def test_invalid_make_modes_and_overrides_refuse(self):
        for kind in ('missing-mode', 'missing-flag', 'wrong-flag', 'duplicate-flag', 'override'):
            with self.subTest(kind=kind):
                value = copy.deepcopy(self.manifest)
                if kind == 'missing-mode':
                    value.pop('host_fork_adoption_opt_in')
                elif kind == 'missing-flag':
                    value['proposed_external_command'].remove('MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=1')
                elif kind == 'wrong-flag':
                    argv = value['proposed_external_command']
                    argv[argv.index('MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=1')] = 'MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=0'
                elif kind == 'duplicate-flag':
                    value['proposed_external_command'].insert(-3, 'MCKERNEL_CURRENT_FORK_ADOPTION_OPT_IN=1')
                else:
                    value['environment']['KRUSTFLAGS'] = '--cfg arbitrary'
                with self.assertRaises(ValueError):
                    driver.plan(value)

    def fixture(self, root, flags):
        candidate, inputs = root / 'candidate', root / 'inputs'
        (candidate / 'modules').mkdir(parents=True)
        inputs.mkdir()
        (inputs / 'preparation.json').write_bytes(P.read_bytes())
        argv = ['/usr/bin/rustc', '--crate-name', 'mcctrl_rust',
                '--emit=obj=/candidate/modules/mcctrl_rust.o',
                '/candidate/modules/mcctrl_rust.rs'] + flags
        deps = ''.join('  /candidate/modules/' + name + ' \\\n'
                       for name in driver.EXACT_DEPENDENCIES['mcctrl'])
        (candidate / 'modules/.mcctrl_rust.o.cmd').write_text(
            'source_x := /candidate/modules/mcctrl_rust.rs\n'
            'savedcmd_x := ' + shlex.join(argv) + '\n'
            'deps_x := \\\n' + deps)
        return candidate, inputs

    def test_actual_cmd_consumer_accepts_bound_enabled_mode(self):
        with tempfile.TemporaryDirectory(prefix='flag-positive-', dir=D) as temp:
            candidate, inputs = self.fixture(Path(temp), ['--check-cfg', 'cfg(' + CFG + ')', '--cfg', CFG])
            result = driver.source_bindings('mcctrl', candidate, inputs)
            self.assertEqual(result['sources'], sorted(driver.EXACT_DEPENDENCIES['mcctrl']))

    def test_actual_cmd_consumer_refuses_missing_and_ambiguous_cfg(self):
        flags = {
            'missing-cfg': ['--check-cfg', 'cfg(' + CFG + ')'],
            'missing-registration': ['--cfg', CFG],
            'duplicate-cfg': ['--check-cfg', 'cfg(' + CFG + ')', '--cfg', CFG, '--cfg', CFG],
            'noncanonical-cfg': ['--check-cfg', 'cfg(' + CFG + ')', '--cfg=' + CFG],
        }
        for kind, arguments in flags.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory(prefix='flag-refusal-', dir=D) as temp:
                candidate, inputs = self.fixture(Path(temp), arguments)
                with self.assertRaises(ValueError):
                    driver.source_bindings('mcctrl', candidate, inputs)


if __name__ == '__main__':
    def forbidden(*args, **kwargs):
        raise AssertionError('No subprocess permitted in targeted flag-flow checks')
    with patch.object(driver.subprocess, 'run', forbidden), patch.object(driver.subprocess, 'check_output', forbidden):
        unittest.main()
