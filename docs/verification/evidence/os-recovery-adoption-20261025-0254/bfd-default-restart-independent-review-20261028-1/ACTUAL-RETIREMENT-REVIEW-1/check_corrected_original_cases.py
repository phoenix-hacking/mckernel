"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent rerun of original two effect scenarios through corrected real transport.
No command subprocess, guardian, flock or Docker effect is permitted.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import tempfile
import types
from unittest.mock import patch

os.sched_setaffinity(0, {0})
resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
O = Path(__file__).resolve().parent
E = O.parents[1]
D = E / 'bfd-default-build-normal-retirement-preparation-20261028-1/executor-source-1'
source = D / 'retire_exact_bfd_stopped_container.py'
assert hashlib.sha256(source.read_bytes()).hexdigest() == '0a262aa55a6da2165d98093b9c3583f2fa1efa77799cd4bb20a627e0da9b193c'
spec = importlib.util.spec_from_file_location('review_corrected_retirement', source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
b = m.bindings()
profile = m.authenticated(m.authenticated(b['packet'], True)['source_refs']['PROFILE.SOURCE-ONLY.json'], True)

with tempfile.TemporaryDirectory(prefix='TEST_ONLY_corrected_age_', dir=O) as temp:
    t = Path(temp)
    now = [1793218000.0, 1000000.0, 1015000.0]
    pre = m.write_new(t / 'TEST_ONLY_PREPROOF.json', dict(TEST_ONLY=True, present=True,
        label='PREINSPECT-2', clocks=list(now)))
    claim = m.write_new(t / 'TEST_ONLY_CLAIM.json', dict(TEST_ONLY=True, preproof=pre))
    cls, namespace = m.transport(b)
    client = cls(t, m.Stop())
    delayed = []
    def delayed_safe():
        if not delayed:
            now[0] += 121
            delayed.append(True)
        return dict(clocks=list(now))
    fake = types.SimpleNamespace(b=b, profile=profile, rm_claimed=True,
        rm_invoked=False, rm_claim_reference=claim, rm_preproof_reference=pre,
        safe=delayed_safe, commands=client, stop=m.Stop(),
        guard=types.SimpleNamespace(guard=lambda: list(now)))
    client.before_popen = lambda argv: m.Actual.before_spawn(fake, argv)
    with patch.object(m.subprocess, 'Popen', side_effect=AssertionError('no stale spawn')) as spawn, \
         patch.object(m.time, 'time', side_effect=lambda: now[0]), \
         patch.object(m.time, 'monotonic', side_effect=lambda: now[1]), \
         patch.object(m.time, 'clock_gettime', side_effect=lambda clock: now[2]), \
         patch.object(os, 'killpg') as signal:
        try:
            m.Actual.call(fake, ['rm', '--', b['cid']])
        except m.Refusal as error:
            assert 'final pre-Popen original120s' in str(error)
        else:
            raise AssertionError('121s original preproof must refuse')
        spawn.assert_not_called()
        signal.assert_not_called()
    assert client.raw_child is None and client.children == []

with tempfile.TemporaryDirectory(prefix='TEST_ONLY_corrected_birth_', dir=O) as temp:
    cls, namespace = m.transport(b)
    client = cls(Path(temp), m.Stop())
    process = types.SimpleNamespace(pid=999997, returncode=None)
    with patch.object(m.subprocess, 'Popen', return_value=process) as spawn, \
         patch.object(m, 'Wait4Child', side_effect=m.Refusal('TEST_ONLY birth unavailable')), \
         patch.object(os, 'killpg') as signal:
        try:
            client.exact(m.PREFIX + ['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
        except m.Refusal:
            pass
        else:
            raise AssertionError('expected substituted birth failure')
        spawn.assert_called_once()
        signal.assert_not_called()
    assert client.children == [] and client.raw_child is process
    assert client.client_retirement_unproven is True
    assert client.unresolved_spawn['pid'] == 999997
    assert m.must_retain_custody(types.SimpleNamespace(mutated=False, commands=client))
    with patch.object(m.subprocess, 'Popen', side_effect=AssertionError('no later retry')) as retry:
        try:
            client.exact(m.PREFIX + ['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
        except m.Refusal as error:
            assert 'prior command uncertainty' in str(error)
        else:
            raise AssertionError('prior uncertainty must remain latched')
        retry.assert_not_called()

print(json.dumps(dict(status='PASS_BOTH_ORIGINAL_RETIREMENT_REVIEW_CASES_CORRECTED',
    old_121s_stall_now_prevents_spawn=True,
    old_successful_spawn_birth_gap_now_retains_raw_child_and_custody=True,
    prior_uncertainty_prevents_later_command=True,
    actual_guard_query_lock_Docker_signal_operations=0), indent=2))
