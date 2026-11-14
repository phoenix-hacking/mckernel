"""Functional source/metadata-only validation; no security testing.

Unprivileged genuine e49 configure with completed-common alias. No Transaction,
proc census, root subprocess, actor FD, custody transfer or cleanup is permitted.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import time

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('actual_phase_readonly', HERE / 'phase_bootstrap.SOURCE-ONLY.py')
phase = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase)
started = time.monotonic()
result = dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
              validation='genuine-original-e49-configure-with-explicit-completed-common-archive-alias',
              uid=os.getuid(), runtime_execution=False, root_calls=False, transaction=False,
              census=False, actor_fd_access=False, actor_retirement=False, production_mutations=False)
try:
    if os.getuid() != 1000 or os.geteuid() != 1000:
        raise RuntimeError('requires ordinary UID1000 source-only profile')
    p = phase.adoption()
    m = phase.original_engine(p)
    forbidden = []
    def no_runtime(*args, **kwargs):
        forbidden.append('runtime-entrypoint')
        raise RuntimeError('source-only-runtime-entrypoint-forbidden')
    for name in ('Transaction', 'recover', 'census', 'run_privileged', 'run_privileged_large',
                 'root_command', 'docker', 'process_absent', 'dead_caller_absent'):
        setattr(m, name, no_runtime)
    original = m.configure
    bound = phase.configure_phase_aware(p, m)
    result.update(status='PASS_GENUINE_UNPRIVILEGED_PHASE_CONFIGURE',
                  selected_rows=len(m.PROTECTED), original_configure_function_unchanged=m.configure is original,
                  original_release_sha256=p.RELEASE_SHA,
                  original_release_canonical_sha256=p.digest(m.canonical(m.RELEASE)),
                  original_plan_canonical_sha256=p.digest(m.canonical(bound['plan'])),
                  common_alias_calls=bound['common_alias_calls'], runtime_entrypoint_calls=forbidden,
                  readers_restored_to_original_source=(m.observe_identity.__code__.co_filename == str(p.SOURCE)
                                                        and m.read_bounded.__code__.co_filename == str(p.SOURCE)))
except BaseException as error:
    result.update(status='SOURCE_READONLY_REFUSAL',error=type(error).__name__+': '+str(error))
finally:
    result['elapsed_seconds']=time.monotonic()-started
print(json.dumps(result,sort_keys=True,indent=2))
raise SystemExit(0 if result['status'].startswith('PASS_') else 1)
