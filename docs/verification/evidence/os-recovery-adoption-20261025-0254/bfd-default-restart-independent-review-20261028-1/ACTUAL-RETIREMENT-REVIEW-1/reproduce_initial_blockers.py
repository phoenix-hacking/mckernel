"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure two-effect reproduction against preserved e38f source; no subprocess is spawned.
"""
from pathlib import Path
import hashlib
import importlib.machinery
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
source = O / 'retire_exact_bfd_stopped_container.py.INITIAL-SNAPSHOT'
assert hashlib.sha256(source.read_bytes()).hexdigest() == 'e38f917bc6cfd78485e79ed9f0c231b54a6af132e3674ff275517706dc2d2b6c'
loader = importlib.machinery.SourceFileLoader('preserved_initial_retirement', str(source))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
m.D = D
m.SELF = D / 'retire_exact_bfd_stopped_container.py'
b = m.bindings()
profile = m.authenticated(m.authenticated(b['packet'], True)['source_refs']['PROFILE.SOURCE-ONLY.json'], True)

# The initial call path permits a validly stopped CID rm after safe() stalls
# beyond the saved preproof age; the effects are only a local list append.
now = [1793218000.0]
effects = []
def delayed_safe():
    now[0] += 121
    return dict(clocks=[now[0], 1000000, 1015000])
def would_spawn(argv, *args, **kwargs):
    effects.append(dict(argv=argv, preproof_age=now[0] - 1793218000))
    return types.SimpleNamespace(returncode=0, stdout=b['cid'], stderr='')
fake = types.SimpleNamespace(b=b, profile=profile, rm_claimed=True, rm_invoked=False,
    safe=delayed_safe, command_started=False,
    commands=types.SimpleNamespace(exact=would_spawn, client_retirement_unproven=False))
m.Actual.call(fake, ['rm', '--', b['cid']])
assert len(effects) == 1 and effects[0]['preproof_age'] == 121

# Underlying Popen succeeds, then wrapper birth setup fails. Initial source
# leaves both the tracked-child list and uncertainty latch empty/false.
with tempfile.TemporaryDirectory(prefix='TEST_ONLY_initial_spawn_gap_', dir=O) as temp:
    cls, namespace = m.transport(b)
    client = cls(Path(temp), m.Stop())
    fake_process = types.SimpleNamespace(pid=999997, returncode=None)
    spawns = []
    def substituted_popen(*args, **kwargs):
        spawns.append(fake_process.pid)
        return fake_process
    with patch.object(m.subprocess, 'Popen', side_effect=substituted_popen), \
         patch.object(m, 'Wait4Child', side_effect=m.Refusal('TEST_ONLY birth unavailable')):
        try:
            client.exact(m.PREFIX + ['ps', '-a', '--no-trunc', '--format', '{{json .}}'])
        except m.Refusal:
            pass
        else:
            raise AssertionError('expected substituted birth failure')
    assert spawns == [999997]
    assert client.children == [] and client.client_retirement_unproven is False
    pre_mutation_main_would_close_lock = not client.client_retirement_unproven

print(json.dumps(dict(status='REPRODUCED_TWO_INITIAL_SOURCE_RELEASE_BLOCKERS',
    preserved_source_sha256='e38f917bc6cfd78485e79ed9f0c231b54a6af132e3674ff275517706dc2d2b6c',
    post_preproof_stall_reaches_substituted_rm=effects,
    successful_substituted_spawn_untracked_after_birth_error=True,
    initial_main_would_release_premutation_custody=pre_mutation_main_would_close_lock,
    actual_process_lock_guard_Docker_mutations=0), indent=2))
