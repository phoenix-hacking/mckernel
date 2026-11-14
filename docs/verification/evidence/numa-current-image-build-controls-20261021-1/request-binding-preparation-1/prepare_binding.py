#!/usr/bin/env python3
"""Prepare source-bound DATA proposals only; never run/import build authorities.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import argparse
import hashlib
import json
from pathlib import Path

P = Path(__file__).resolve().parent.parent
OLD = Path('/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/owned-fork-pin-successor-1/coupled-current-pin-correction-1/control-successor-1')
COMPILER = Path('/home/holden/mckernel-work/host-preparation/numa-current-whole-consumer-compile-preparation-20261021-1/independent-review-1')
PINS = {
    OLD / 'image-request.json': '77bad32386d159cae2de3ef7b404e4fe818f9cc5ad2ce8b58af32515a2d02233',
    OLD / 'native_exact_current_optin_image_guard.py': '68820d05f5c6e7cdc726e62d983891f83387706b4d945e2ba991c0762356f97d',
    P / 'SOURCE-UNBOUND-REQUEST-DELTA-PROPOSAL.json': '304a8410d4890e3008f7d2333ceef782e9701e799b0060d45c8bcaa162db9169',
    P / 'FUTURE-GUARD-AND-LINK-BINDING-DELTA.json': '91572ce1513c6767f9291ec4edf56bee7448438009f95f3e8456b09317d42ec9',
    P / 'actual-whole-validators-capture-1/actual-source-acceptance.json': '604da9bacb7fa214fe148ca473462646167634b025274fecc5fdb5a4f436d033',
    P / 'actual-whole-validators-capture-1/whole.json': '574b11d915e0a0a5082b9c985dbebf30d4f3e3e72367284de9c05ed5c2c123fc',
    P / 'WHOLE-ACTUAL-SOURCE-VALIDATOR-RESULT.json': 'd2de8beedbcc10065ea40bbfbbbc1a6af3af6e0a58d0569f695eef33b3ba09fe',
    P / 'source-materialization-1/materialization-receipt.json': 'af7d8f9a7edd6bac31f220d793190875ba572e28d42e0df7b382da9447b79a4e',
    COMPILER / 'actual-six-stage-artifact-acceptance.json': 'e8b4284c1579a7a9c455a08f081056644002e929c846a5aeca684600c9d2bb4e',
    COMPILER / 'actual-six-stage-physical-retirement-acceptance.json': 'dae7598be1216bc26d82c03f61b730d59382f5f59aa071ac4746a2f17eefa0de',
}


def demand(ok, message):
    if not ok:
        raise ValueError(message)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True,
                        help='fresh dispatcher-owned DATA proposal directory; not runtime work root')
    args = parser.parse_args()
    raw = {}
    for path, pin in PINS.items():
        data = path.read_bytes()
        demand(hashlib.sha256(data).hexdigest() == pin, 'changed finite input: ' + str(path))
        raw[path] = data
    def doc(path):
        return json.loads(raw[path])
    def ref(path):
        return {'path': str(path), 'sha256': PINS[path], 'bytes': len(raw[path])}
    base = doc(OLD / 'image-request.json')
    delta = doc(P / 'SOURCE-UNBOUND-REQUEST-DELTA-PROPOSAL.json')
    acceptance = doc(P / 'actual-whole-validators-capture-1/actual-source-acceptance.json')
    receipt = doc(P / 'source-materialization-1/materialization-receipt.json')
    demand(acceptance['source_entries'] == receipt['source_entries'] == 6959, '6959 source entries')
    demand(acceptance['tracked_symlinks'] == receipt['tracked_symlinks'] == 49, '49 source symlinks')
    demand(acceptance['source_identity'] == {'device': 66306, 'inode': 48406208,
           'uid': 1000, 'gid': 1000, 'mode': '0700'}, 'accepted source identity')
    request = dict(base)
    request.update(delta['set_fields'])
    request['source_identity'] = {'dev': 66306, 'inode': 48406208, 'uid': 1000,
        'gid': 1000, 'mode': 448, 'file_type': 16384, 'path': request['source_root']}
    for key in ('source_derivative_sha256', 'materialization_sha256'):
        demand(request[key] == acceptance[key] == receipt[key], 'source binding: ' + key)
    # The old owner's disk_identity points at its old source but is separately
    # authenticated by the existing runtime owner. Do not guess its successor.
    demand(request['disk_identity'] is None and request['backup_identity'] is None,
           'late runtime identity must remain explicitly unbound')
    demand(base['memory_allocation_roots'].count(base['source_root']) == 1,
           'unique source memory-allocation root')
    request['memory_allocation_roots'] = [request['source_root'] if p == base['source_root'] else p
                                         for p in base['memory_allocation_roots']]
    demand(request['mounts'] == base['mounts'] and request['path_dirs'] == base['path_dirs'],
           'container namespace and PATH must be unchanged')
    demand(request['native_fork_owned_transaction'] is True, 'existing diagnostic opt-in retained')
    changed = [k for k in base if request[k] != base[k]]
    added = [k for k in request if k not in base]
    demand(not added, 'no request-schema field additions')
    guard = doc(P / 'FUTURE-GUARD-AND-LINK-BINDING-DELTA.json')
    guard['status'] = 'DATA_ONLY_SOURCE_BOUND_RUNTIME_AND_RELEASE_UNBOUND'
    guard['source_materialization_acceptance'] = ref(P / 'actual-whole-validators-capture-1/actual-source-acceptance.json')
    guard['source_validator_whole'] = ref(P / 'actual-whole-validators-capture-1/whole.json')
    guard['source_validator_result'] = ref(P / 'WHOLE-ACTUAL-SOURCE-VALIDATOR-RESULT.json')
    guard['compiler_acceptance'] = ref(COMPILER / 'actual-six-stage-artifact-acceptance.json')
    guard['actual_physical'] = ref(COMPILER / 'actual-six-stage-physical-retirement-acceptance.json')
    guard['future_latest_physical'] = None
    guard['runtime_binding_acceptance'] = None
    guard['bound_request_basis'] = None
    guard['independent_execution_review'] = None
    guard['fetched_source_control_publication'] = None
    guard['fresh_admission_and_release'] = None
    guard['guard_source_schema_adaptation'] = {
        'source_status': acceptance['status'],
        'source_receipt': 'Read source acceptance.receipt via its exact reference, not old source_receipt field.',
        'ordinary_materialization': 'Read source acceptance.closed_capture and require actual direct closure; not old actual_evidence[0].',
        'source_identity': 'Translate accepted device/mode0700 to request dev/mode448; retain path/file_type and all identity comparisons.',
        'ordinary_validators': 'Require separately bound validator whole direct exit0/closed streams/join/group absent, result owned positive and affinity source gates; do not claim affinity compile PASS.',
        'runtime': 'New independently accepted runtime adapter/owner/request basis required; never reuse old runtime_ref or basis_ref.',
        'self_and_sources': 'Rebind SELF, SOURCES and local image-owner import directory to actual new control paths with exact hashes.',
        'unchanged': 'Preserve authentication, independent release, development mutex, UUID, positive retirement, exact mounts/profile, lease and publication bodies.'}
    diff = {'status': 'DATA_ONLY_NOT_EXECUTABLE_REQUEST_OR_GUARD',
            'scope': delta['scope'], 'request_changed_fields': changed,
            'request_new_fields': added, 'mount_destinations_changed': False,
            'path_dirs_changed': False,
            'host_mount_source_fields_changed': ['source_root', 'source_manifest', 'gitlink_manifest',
                'driver_path', 'provenance_path', 'work_root'],
            'memory_allocation_root_change': {'old': base['source_root'], 'new': request['source_root']},
            'unchanged_inventory_fields': ['backup_inventory', 'toolchain_roots', 'toolchain_manifest',
                'toolchain_manifest_sha256', 'toolchain_lock_sha256', 'host_git'],
            'unbound': ['disk_identity', 'backup_identity', 'fresh disk_admission host_device/scratch_device',
                'runtime binding and source-bound request-basis acceptance', 'guard SELF/SOURCES/import path',
                'fresh aggregate/UUID/ownership/service/included100% admission',
                'source/control fetched publication', 'latest physical retirement', 'independent execution release'],
            'input_refs': [ref(p) for p in PINS]}
    args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
    for name, value in [('request-SOURCE-BOUND-DATA-ONLY.json', request),
                        ('guard-BINDING-DATA-ONLY.json', guard), ('finite-diff.json', diff)]:
        with (args.output / name).open('x') as stream:
            json.dump(value, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
            stream.write('\n')
    print('DATA_ONLY_SOURCE_BOUND_PROPOSAL_WRITTEN_NO_EXECUTION_RELEASE')


if __name__ == '__main__':
    main()
