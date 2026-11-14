"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only NEW-window consumer. An explicit reviewed operation successor is mandatory.
This module grants no execution, resources, nonce, cleanup or controller authority.
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
PREDECESSOR = E / 'operation-account-window-new12h-source-1/actual_account_window.py'
PREDECESSOR_SHA256 = '8bf26bae56a019876c6a1463945733c85be5016d21ac5f6f955c29fd131a8cbe'
WINDOW = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/ACTUAL-WINDOW.json')
WINDOW_SHA256 = '0bfb54bff698f53c744d797e2f57db94db08cd20120da70566d555fa6c1e320e'
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
RUN = '7f4af94a83b14cc08f97401f5891d965'
CEILING = '57774.852125'
THREAD = '01a18582-1fc6-77b1-bfb6-15c86483f579'
# Preserve legacy API clock order: epoch, MONOTONIC, BOOTTIME.
CUTOFFS = (1793253600.0, 1035706.5689547858, 1051044.6960026678)
OPERATION_CUTOFFS = (1793253600.0, 1035704.5689393478, 1051042.6959879305)
GUARDIAN_SOURCE = {'bytes': 13603, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-PIPELINE-CONTROL-BINDING-PREPARATION-1/new-guardian-source-1/guardian_guard.py', 'sha256': '5af549bdf87a248a76bfe4e96de2ddc8c20435f3bafff5397ca7a9557ca68df4'}
PREDECESSOR_CUTOFFS = {
    'current118-postjoin-current64': None,
}


def need(ok, why):
    if not ok:
        raise ValueError(why)


def no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        need(key not in out, 'duplicate JSON key')
        out[key] = value
    return out


def decode(raw):
    def constant(value):
        raise ValueError('nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=no_duplicates, parse_constant=constant)


def reference(path):
    path = Path(path)
    need(path.is_absolute() and not path.is_symlink() and path.is_file(), 'absolute regular byte subject')
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def authenticated(ref, declared_json=False):
    need(type(ref) is dict and set(ref) == {'path', 'bytes', 'sha256'}, 'exact byte reference')
    raw = Path(ref['path']).read_bytes()
    need(reference(ref['path']) == ref and len(raw) == ref['bytes']
         and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'authenticated subject bytes')
    return decode(raw) if declared_json else raw


def load_predecessor():
    need(hashlib.sha256(PREDECESSOR.read_bytes()).hexdigest() == PREDECESSOR_SHA256,
         'historical cumulative account semantics unchanged')
    spec = importlib.util.spec_from_file_location('historical_account_semantics_only', PREDECESSOR)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_window():
    raw = WINDOW.read_bytes()
    need(hashlib.sha256(raw).hexdigest() == WINDOW_SHA256, 'actual new window bytes')
    window = decode(raw)
    need(window['status'] == 'ACTUAL_AUTHORIZED_LAUNCH_WINDOW'
         and window['window_id'] == 'until-20261028-2300-pacific-1793166745'
         and window['boot_id'] == BOOT and window['credit_run_id'] == RUN
         and window['credit_ceiling'] == CEILING
         and (window['deadline_epoch'], window['monotonic_deadline'], window['boot_deadline']) == CUTOFFS,
         'immutable actual NEW window')
    return window


def triplet(values):
    need(type(values) in (list, tuple) and len(values) == 3
         and all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values),
         'three finite clocks in epoch/monotonic/boottime order')
    return tuple(values)


def validate_operation(successor, review, operation, subjects, clocks, boot_id=BOOT):
    """Pure binding check; successful return does not authorize execution."""
    clocks = triplet(clocks)
    need(operation in PREDECESSOR_CUTOFFS and boot_id == BOOT, 'known operation and same boot')
    need(successor['schema'] == 'mckernel.explicit-new-window-operation-successor.v1'
         and successor['author'] == '/root' and successor['operation'] == operation
         and successor['decision'] == 'EXPLICIT_OPERATION_WINDOW_SUCCESSOR'
         and successor['window_sha256'] == WINDOW_SHA256
         and successor['credit_run_id'] == RUN and successor['credit_ceiling'] == CEILING,
         'explicit Root operation successor required')
    need(operation == 'current118-postjoin-current64' and successor['predecessor_cutoffs'] is None
         and successor['first_prepared_window_sha256'] == WINDOW_SHA256,
         'new postjoin62 operation has no fictitious expired predecessor grant')
    limits = triplet(successor['operation_cutoffs'])
    need(all(0 < limit <= maximum for limit, maximum in zip(limits, OPERATION_CUTOFFS)), 'operation only within NEW window')
    need(all(now < limit for now, limit in zip(clocks, limits)), 'strict earliest operation cutoff')
    need(successor['subjects'] == subjects and type(subjects) is dict and bool(subjects), 'exact consumer source closure')
    need(review['schema'] == 'mckernel.independent-operation-window-review.v1'
         and review['decision'] == 'PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR'
         and review['independent'] is True and review['reviewer'].startswith('/root/')
         and review['reviewer'] not in successor['source_owners']
         and review['operation'] == operation and review['successor'] == successor,
         'independent exact operation successor review')
    need(successor['source_owners'] and '/root' in successor['source_owners'], 'explicit source ownership')
    # A Root supplied cumulative floor may tighten the historical floor, never reset it.
    old = load_predecessor()
    need(old.MIN_SPENT <= old.amount(successor['minimum_cumulative_spent']) < old.BUDGET,
         'preserved cumulative debit floor')
    need(successor['guardian'] == {'source': GUARDIAN_SOURCE, 'entrypoint': 'guard'},
         'exact reviewed restart guardian binding required')
    return limits


def check_account_state(state, wall, minimum_cumulative_spent):
    """Pure cumulative/account check using unchanged historical balance semantics."""
    old = load_predecessor()
    # Explicit current-launcher identity successor; all other account predicates
    # remain the byte-pinned predecessor's unchanged implementation.
    need(state['thread_id'] == THREAD, 'actual NEW launcher thread identity')
    old.THREAD = THREAD
    result = old.check_account_state(state, wall)
    floor = old.amount(minimum_cumulative_spent)
    need(old.MIN_SPENT <= floor <= old.amount(state['credit_budget']['spent']),
         'no cumulative debit rollback')
    return result


def guard(operation, successor_ref, review_ref, expected_subjects):
    """Read-only actual preconditions. Caller must separately enforce execution release."""
    old = load_predecessor()
    clocks = [old.time.time(), old.time.monotonic(), old.time.clock_gettime(old.time.CLOCK_BOOTTIME)]
    load_window()
    successor = authenticated(successor_ref, declared_json=True)
    review = authenticated(review_ref, declared_json=True)
    validate_operation(successor, review, operation, expected_subjects, clocks,
                       Path('/proc/sys/kernel/random/boot_id').read_text().strip())
    for subject in expected_subjects.values():
        authenticated(subject)  # Source and binary subjects remain BYTES.
    state = decode(old.STATE.read_bytes())
    check_account_state(state, clocks[0], successor['minimum_cumulative_spent'])
    # Guardian checks must use its reviewed read-only guard, authenticated as bytes.
    guardian = successor['guardian']
    need(set(guardian) == {'source', 'entrypoint'}, 'exact fresh guardian adapter')
    source = guardian['source']
    authenticated(source)
    need(guardian['entrypoint'] == 'guard', 'only reviewed read-only guardian entrypoint')
    spec = importlib.util.spec_from_file_location('new_window_reviewed_guardian', source['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    guardian_clocks = triplet(module.guard())
    limits = triplet(successor['operation_cutoffs'])
    need(all(a <= b < limit for a, b, limit in zip(clocks, guardian_clocks, limits)),
         'fresh guardian checked inside earliest operation clamps')
    return list(guardian_clocks)
