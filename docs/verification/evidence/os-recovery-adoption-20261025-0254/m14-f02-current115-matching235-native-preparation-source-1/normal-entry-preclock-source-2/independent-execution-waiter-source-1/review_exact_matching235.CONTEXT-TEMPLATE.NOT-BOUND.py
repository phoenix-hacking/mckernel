"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite independent exact-case receipt waiter. No grant, bridge entry or workload.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import time

D = Path(__file__).resolve().parent
F = D.parent / 'root-adopted-matching115-process235-entry-2'
STATIC = F / 'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'
PUBLICATION = F / 'ACTUAL-STATIC-SOURCE-PUBLICATION.json'
AUTH = F / 'ROOT-CONDITIONAL-ONCE-ENTRY-AUTHORIZATION.json'
PENDING = F / 'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'
RESOURCE = F / 'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json'
JOIN = F / 'RESOURCE-1-CAPTURE-JOIN.json'
OUTPUT = F / 'ACTUAL-INDEPENDENT-NATIVE-EXECUTION-REVIEW.json'
STATIC_SHA = None
AUTH_SHA = None
BRIDGE_SHA = None
BINDER_SHA = '8ba9856c6793e15cfc850c0b1542fb9ff244be8d79816f0cb786ccc417d9de59'
NONCE = None
CASE = 'P-M06-01-process-exec-wait-235B'
IMAGE = 'de9fdd13b55a5a17158fa8247cc9351c1d9b1944a72c45bac9e4774473dca024'
REVIEWER = '/root/daemon_execution_review'
WAIT_SECONDS = 600


def need(ok, why):
    if not ok:
        raise ValueError(why)


def ref(path):
    raw = Path(path).read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def read(path):
    return json.loads(Path(path).read_bytes())


def checked(reference):
    need(ref(Path(reference['path'])) == reference, 'exact reference drift')
    return read(reference['path'])


def load(path, digest, name):
    need(ref(path)['sha256'] == digest, 'literal helper source')
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    need(module.__file__ == str(path) and module.__spec__.origin == str(path), 'literal import context')
    return module


def durable(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def cold(publication_sha):
    need(os.getuid() == os.geteuid() == 1000, 'independent ordinary reviewer UID')
    need(ref(STATIC)['sha256'] == STATIC_SHA and ref(AUTH)['sha256'] == AUTH_SHA,
         'sealed exact static and Root conditional authorization')
    need(ref(PUBLICATION)['sha256'] == publication_sha, 'exact Root publication')
    s, a, pub = read(STATIC), read(AUTH), read(PUBLICATION)
    need(s['nonce'] == a['nonce'] == NONCE and s['expected_case'] == a['case'] == CASE,
         'one exact case and nonce')
    need(s['expected_new_image_sha256'] == IMAGE and s['expected_guest_argv'] ==
         ['/bin/mcexec', '-t', '1', '0', '/apps/app'], 'matching115 image and original235 argv')
    need(s['collector']['sha256'] == 'ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c',
         'qualified original235 collector')
    need(len(bytes.fromhex(s['expected_oracle']['stdout_hex'])) == 235 and
         s['expected_oracle']['stderr_hex'] == '' and s['expected_oracle']['exit_code'] == 0,
         'unchanged original235 oracle')
    need(a['authorized'] is True and a['authorized_by'] == '/root' and
         a['maximum_invocations'] == 1 and a['reviewer'] == REVIEWER and
         a['static_bindings'] == ref(STATIC) and a['exact_argv'] == s['exact_argv'], 'Root conditional exact authority')
    need(pub['status'] == 'PASS_ACTUAL_PUSH_FETCH_AND_EXACT_NATIVE_STATIC_BLOBS' and
         ref(STATIC) in pub['files'], 'actual flat publication')
    for r in s['capture_sources'].values():
        need(ref(Path(r['path'])) == r and r in pub['files'], 'published exact helper')
    # Python observer source is authenticated as bytes, never JSON-decoded.
    need(ref(Path(s['current_observer_source']['path'])) == s['current_observer_source'],
         'cold raw observer source reference')
    for key in ('source_authority', 'case_capability', 'stage_map_acceptance', 'artifact_acceptance',
                'manifest', 'current_observer_schema', 'current_observer_source_review'):
        checked(s[key])  # These sealed subjects are actual JSON documents.
    ledger = checked(s['root_ledger35'])
    need(s['root_ledger35']['sha256'] == '0140dcb85e685cce3c23d7f76b50b05c092f0db4fa8b5f3e651c8467bfdf2f55' and
         len(ledger['consumed_nonces']) == 68 and NONCE not in
         ledger['consumed_nonces'] + ledger['reserved_abandoned_unconsumed_nonces'], 'actual Root57 unused nonce')
    need(ledger['latest_accepted_free_boundary'] == s['latest_serial_operation_physical_acceptance'],
         'latest genuine free boundary')
    free = checked(s['latest_serial_operation_physical_acceptance'])
    need(free['current_free'] is True and free['normal_owned_retirement'] is True, 'positive prior retirement')
    bridge = load(F / 'root_once_startup_entry.py', BRIDGE_SHA, 'review_only_literal_once_bridge')
    binder = load(F / 'bind_startup_resource.py', BINDER_SHA, 'review_only_literal_data_binder')
    need(a['bridge_sha256'] == BRIDGE_SHA, 'exact adopted bridge')
    return s, bridge, binder


def hot(s, bridge, binder, publication_sha):
    need(ref(PUBLICATION)['sha256'] == publication_sha, 'publication unchanged while waiting')
    _, packet, resource, refs = bridge.bind_inputs(AUTH_SHA)
    join = checked(packet['resource_output_retention'])
    need(join['returncode'] == 0 and join['direct_child_joined'] is True and
         join['streams_closed'] is True and join['stderr']['bytes'] == 0 and
         join['resource'] == refs['resource'], 'positive normal resource capture completion')
    need(join['argv'] == ['/home/holden/anaconda3/bin/python3', '-I', '-B',
         str(F / 'capture_fresh_startup_resource.py'), '--output-path', str(RESOURCE)], 'exact capture command')
    expected = binder.packet_for(s, refs['static'], resource, refs['resource'], refs['publication'])
    expected['resource_output_retention'] = packet['resource_output_retention']
    need(packet == expected, 'entire pending packet equals original data binder')
    physical = resource['current_physical_observation']
    schema = checked(s['current_observer_schema'])
    need(physical['status'] == schema['expected_status'] and
         physical[schema['ledger_key']] == s['root_ledger35'] and
         physical[schema['latest_free_key']] == s['latest_serial_operation_physical_acceptance'],
         'original exact observed Root57 schema and latest-free binding')
    checked(physical[schema['current_boundary_key']])
    need(resource['active_shared_records_absent'] is True and physical['active_shared_records_absent'] is True and
         physical['no_existing_heavy'] is True and physical['pids_current'] == 0,
         'observed original shared custody predicates')
    census = physical['group_membership_observation']
    need(not census['errors'] and len(physical['closed_exclusive_probes']) == 2, 'complete original census and mutex probes')
    for actor in physical['new_exact_actors']:
        need(not any(r['pid'] == actor['pid'] or r['pgrp'] == actor['pid'] for r in census['rows']),
             'exact observed retired actor and group')
    need(all(q['positive_wait'] and q['streams_closed'] for q in physical['current115_exact_CID_queries']),
         'positive observed exact retained CID queries')
    need(resource['memory']['MemAvailable'] >= 24 * 2**30 and
         list(resource['cgroup'].values()) == ['100000', '400000', '12884901888', '1', '512'], 'original memory and cgroup profile')
    capacity = resource['capacity']
    host = capacity.get('/home/holden/mckernel', capacity.get('host'))
    scratch = capacity.get('/home/holden/mckernel-work/scratch', capacity.get('scratch'))
    need(host >= 16 * 2**30 and scratch >= 12 * 2**30, 'original free floors')
    need(resource['running_container_observation']['returncode'] == 0 and
         not resource['running_container_observation']['stdout'].strip() and
         not resource['running_container_observation']['stderr'], 'observed no other heavy container')
    need({r['path'] for r in resource['fresh_directories']} == {str(F / 'CAPTURE'), s['attempt_parent']} and
         all(r['uid'] == r['gid'] == 1000 and r['mode'] == 16832 for r in resource['fresh_directories']),
         'exact fresh private directories')
    clamps = bridge.clamps_for(packet, resource)
    return packet, resource, refs, clamps


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument('--publication-sha256', required=True)
    args = parser.parse_args()
    need(len(args.publication_sha256) == 64 and all(x in '0123456789abcdef' for x in args.publication_sha256),
         'literal publication digest')
    for p in (OUTPUT, D / 'PREWARM.json', D / 'REFUSAL.json', D / 'COMPLETE.json', D / 'REVIEW.COMPLETE.tmp'):
        need(not p.exists(), 'one review invocation, no retry')
    s, bridge, binder = cold(args.publication_sha256)
    need(not any(p.exists() for p in (RESOURCE, PENDING, JOIN,
         F / 'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json')), 'actual waiter precedes capture')
    need(not any((F / n).exists() for n in ('ROOT-ONCE-ENTRY.CLAIM.json',
         'ROOT-ACTUAL-ONE-NATIVE-M15-STARTUP-GRANT.json', 'ROOT-ONCE-ENTRY.REFUSAL.json')), 'fresh original once context')
    clocks, cutoffs = bridge.guard_now()
    need(all(a < b for a, b in zip(clocks, cutoffs)), 'actual account and earlier fixed clocks')
    start = time.monotonic()
    birth = int(Path('/proc/self/stat').read_text().rsplit(')', 1)[1].split()[19])
    durable(D / 'PREWARM.json', dict(status='ACTUAL_FINITE_INDEPENDENT_REVIEW_WAITER_WAITING_NOT_APPROVED',
        pid=os.getpid(), starttime=birth, source=ref(Path(__file__)), nonce=NONCE, static=ref(STATIC),
        authorization=ref(AUTH), publication=ref(PUBLICATION), reviewed_clocks=clocks,
        fixed_cutoffs=list(cutoffs), wait_seconds_max=WAIT_SECONDS, native_or_grant_operations=0))
    # The existing binder writes this template only after closing the complete pending
    # packet. It is an existing writer-completion marker, never authority or a new gate.
    marker = F / 'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json'
    while not (marker.exists() and PENDING.exists() and JOIN.exists()):
        now = (time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME))
        need(time.monotonic() - start < WAIT_SECONDS and all(a < b for a, b in zip(now, cutoffs)), 'finite fixed wait expired')
        need(not (F / 'ROOT-ONCE-ENTRY.REFUSAL.json').exists(), 'original bridge refused')
        time.sleep(.1)
    packet, resource, refs, clamps = hot(s, bridge, binder, args.publication_sha256)
    review = dict(decision='PASS_EXECUTION', reviewer=REVIEWER, independent=True,
        implementation_ownership=False, maximum_invocations=1, nonce=NONCE,
        payload_sha256=refs['pending']['sha256'], pending_execution_packet=refs['pending'],
        exact_argv=packet['exact_argv'], static_bindings=refs['static'],
        fresh_resource_physical=refs['resource'], source_publication=refs['publication'],
        manifest=packet['manifest'], root_ledger35=packet['root_ledger35'],
        source_authority=packet['source_authority'], scope=__doc__.splitlines()[0],
        waiter_source=ref(Path(__file__)), actual_prewarm=ref(D / 'PREWARM.json'),
        original_binder_packet_reproduced=True, original_entry_clamps=clamps,
        current_observer_schema=s['current_observer_schema'],
        current_observer_source_review=s['current_observer_source_review'],
        current_free=s['latest_serial_operation_physical_acceptance'],
        expected_case=CASE, expected_image=IMAGE, native_acceptance=False,
        reviewer_workloads_queries_grants_cleanup=0)
    temporary = D / 'REVIEW.COMPLETE.tmp'
    durable(temporary, review)
    # Recheck all original source/current bindings and real guard/freshness AFTER
    # complete temporary receipt fsync and BEFORE publishing the atomic PASS.
    packet2, resource2, refs2, _ = hot(s, bridge, binder, args.publication_sha256)
    need(packet2 == packet and resource2 == resource and refs2 == refs, 'no evidence drift after fsync')
    need(not (F / 'ROOT-ONCE-ENTRY.CLAIM.json').exists(), 'no competing entry')
    os.link(temporary, OUTPUT)
    fd = os.open(F, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    durable(D / 'COMPLETE.json', dict(status='ATOMIC_EXACT_PASS_PUBLISHED_NO_WORKLOAD', review=ref(OUTPUT)))
    print(json.dumps(dict(decision='PASS_EXECUTION', review=ref(OUTPUT))))


if __name__ == '__main__':
    try:
        main()
    except BaseException as error:
        if not (D / 'REFUSAL.json').exists():
            durable(D / 'REFUSAL.json', dict(status='REFUSED_NO_RETRY_NO_APPROVAL',
                error=type(error).__name__ + ': ' + str(error), review_present=OUTPUT.exists()))
        raise
