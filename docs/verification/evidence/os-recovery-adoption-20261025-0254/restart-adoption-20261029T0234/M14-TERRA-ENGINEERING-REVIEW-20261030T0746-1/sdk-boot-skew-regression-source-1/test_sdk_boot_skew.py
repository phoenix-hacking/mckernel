"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Synthetic actual-gate BOOTTIME conversion checks; no owner, subprocess, lease or Docker.
"""
import ast
import hashlib
import re
import types
import unittest
from pathlib import Path

SOURCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/sdk21-nonheld13-owner-source-1')


def fail(ok, message):
    if not ok:
        raise ValueError(message)


def gate_for(version, boot_limit):
    tree = ast.parse((SOURCE / ('sdk13_compile_image_owner.' + version + '.py')).read_text())
    names = {'_sdk13_containment_args', 'SDK13Containment'}
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == names
    # All source code executed is the selected gate and argument checker, with
    # every real external dependency replaced by deterministic local values.
    mono = iter([50.0, 60.0] if version == 'v8' else [60.0])
    clock = types.SimpleNamespace(monotonic=lambda: next(mono), time=lambda: 100.0,
                                  clock_gettime=lambda which: 200.0, CLOCK_BOOTTIME=7)
    policy = {'max_calls': 8, 'max_wall_seconds': 90, 'until_utc': 300.0,
              'until_boot': boot_limit, 'until_mono': 150.0}
    lease = types.SimpleNamespace(record={'pid': 42, 'starttime': 'birth',
                                         'request_core_sha256': 'core'}, load_owned=lambda: b'lease')
    env = {'_fail': fail, 're': re, 'SDK13_INSPECT_TEMPLATE': 'fmt', 'time': clock,
           '_sdk13_root': lambda ref, path: ({}, 'id'),
           '_sdk13_containment_policy': lambda release, request: policy,
           'SDK13_RELEASE': None, '_request_core_hash': lambda request: 'core',
           '_proc_starttime': lambda pid: 'birth', 'os': types.SimpleNamespace(getpid=lambda: 42),
           'hashlib': hashlib}
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[])),
                 '<synthetic-gate>', 'exec'), env)
    state = env['SDK13Containment'].__new__(env['SDK13Containment'])
    state.request = {'compile_only_release': 'ref'}
    state.authority = {'release': 'id'}
    state.lease, state.cid = lease, 'a' * 64
    state.started, state.calls, state.attested = 40.0, 0, False
    return state, ('inspect', '--format', 'fmt', state.cid)


class BootSkew(unittest.TestCase):
    def test_boot_cutoff_is_not_extended_by_late_monotonic_sample(self):
        old, args = gate_for('v7', 220.0)
        new, _ = gate_for('v8', 220.0)
        # BOOT sample 200 occurs between mono 50 and 60; using later mono
        # translates the deadline to 80, whereas the early anchor gives 70.
        self.assertEqual(old.gate(args)['absolute_deadline_mono'], 80.0)
        self.assertEqual(new.gate(args)['absolute_deadline_mono'], 70.0)
        self.assertEqual(new.calls, 1)

    def test_boot_budget_exhaustion_refuses_call(self):
        old, args = gate_for('v7', 208.0)
        new, _ = gate_for('v8', 208.0)
        self.assertEqual(old.gate(args)['absolute_deadline_mono'], 68.0)
        with self.assertRaisesRegex(ValueError, 'retirement window'):
            new.gate(args)
        self.assertEqual(new.calls, 0)


if __name__ == '__main__':
    unittest.main()
