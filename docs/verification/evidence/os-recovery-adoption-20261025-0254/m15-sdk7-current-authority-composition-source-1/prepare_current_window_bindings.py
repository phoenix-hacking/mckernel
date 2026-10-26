"""Static M15 metadata only; no clocks, runtime imports, grants or commands executed."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

WINDOW = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/'
              'new-18-hour-window-1/parent-handoff/WINDOW.json')
ORIGIN = Path('/home/holden/mckernel-work/host-preparation/daemon-sdk7-new18h-source-1/'
              'CONSUMER.NEXT18H.PENDING.json')
ORIGIN_SHA = '6d8ba10f30546fa9aceeca6c76da7f0c9fe050963f0e7d78dfbdc99cc6823c2d'
LABELS = ('linux-ABI', 'libudev-ABI', 'selected-configure', 'selected-build',
          'daemon-dynamic', 'daemon-imports', 'daemon-loader')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def ref(path):
    raw = Path(path).read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def validate_window(window):
    require(type(window['start_epoch']) is int and type(window['deadline_epoch']) is int,
            'integer consumed wall boundary required')
    for start, end in (('start_epoch', 'deadline_epoch'), ('start_boot', 'boot_deadline'),
                       ('start_monotonic', 'monotonic_deadline')):
        require(type(window[start]) in (int, float) and type(window[end]) in (int, float)
                and math.isfinite(window[start]) and math.isfinite(window[end])
                and window[end] == window[start] + 64800, 'fixed consumed clock pair differs')
    require(datetime.fromisoformat(window['deadline_utc']).timestamp() == window['deadline_epoch'],
            'consumed UTC differs')
    return window


def bindings(origin, request, window, window_ref):
    validate_window(window)
    require(tuple(row['label'] for row in origin['seven_commands']) == LABELS,
            'exact existing seven-command sequence required')
    profile = {'cpus': '2-5', 'jobs': 1, 'memory_bytes': 12 * 2**30,
               'memory_swap_bytes': 12 * 2**30, 'network': 'none', 'pids': 512}
    require(origin['profile'] == profile, 'established heavy profile differs')
    packet = copy.deepcopy(origin)
    packet.update(schema='mckernel.daemon7.current-window.static-bindings.v1',
                  status='STATIC_BINDINGS_NOT_EXECUTABLE_QUERY_OR_RELEASE', source_only=True,
                  window={'id': window['window_id'],
                          'start': datetime.fromtimestamp(window['start_epoch'], timezone.utc).isoformat(),
                          'deadline': window['deadline_utc']},
                  consumed_parent_window=window_ref, consumed_parent_clocks=copy.deepcopy(window),
                  current_physical=None, aggregate=None, pending_release_base=None,
                  query_release=None, SDK_execution_release=None,
                  clock_boot_cutoff=window['boot_deadline'],
                  clock_monotonic_cutoff=window['monotonic_deadline'],
                  request=None, publication=None, source_refresh_review=None,
                  typed_current_authority=None, actual_admission=None,
                  actual_nonce=None, actual_owned_capture=None, runtime_authority=None)
    pending = copy.deepcopy(request)
    for key in ('nonce', 'candidate_root', 'candidate_identity', 'owner_evidence_root',
                'output_parent_identity', 'input_identity', 'basis_identity', 'backing_identity'):
        pending[key] = None
    pending.update(status='STATIC_REQUEST_TEMPLATE_NOT_A_RUNTIME_REQUEST',
                   request_path=None, boot_id=window['boot_id'], current_physical=None,
                   parent_window=window_ref, fresh_resources=None,
                   owned_capture=None, runtime_authority=None)
    query = {'status': 'STATIC_QUERY_BINDINGS_NOT_A_QUERY_RELEASE', 'packet': None,
             'window': packet['window'], 'consumed_parent_window': window_ref,
             'wall_deadline_epoch': window['deadline_epoch'],
             'boot_deadline': window['boot_deadline'],
             'monotonic_deadline': window['monotonic_deadline'], 'boot_id': window['boot_id'],
             'profile': profile, 'current_physical': None, 'typed_current_authority': None,
             'actual_parent_aggregate_environment_GiB': None,
             'query_source_origin': origin['refresh_sources']['query'],
             'source_binding_adapter': None,
             'no_intervening_serialized_operation': None, 'owned_capture': None,
             'runtime_authority': None, 'execution_release': False}
    fill = {'status': 'STATIC_FILL_BINDINGS_NOT_AN_EXECUTION_PAYLOAD', 'packet': None,
            'request': None, 'actual_nonce': None, 'current_physical': None,
            'typed_current_authority': None, 'query': None, 'query_join': None,
            'authenticated_query_export': None, 'publication': None,
            'independent_metadata_review': None, 'execution_review': None,
            'resource_reservation': None, 'runtime_authority': None,
            'fill_source_origin': origin['refresh_sources']['fill'],
            'fill_schema_source_origin': origin['refresh_sources']['fill_schema'],
            'parent_window': window_ref, 'execution_release': False}
    require(packet['seven_commands'] == origin['seven_commands']
            and packet['provider'] == origin['provider']
            and packet['source27'] == origin['source27']
            and packet['full11_map'] == origin['full11_map'], 'retained compiler/source tuple changed')
    return {'PACKET.CURRENT-WINDOW.STATIC.json': packet,
            'REQUEST.CURRENT-WINDOW.TEMPLATE.NOT-RELEASED.json': pending,
            'QUERY.CURRENT-WINDOW.TEMPLATE.NOT-RELEASED.json': query,
            'FILL.CURRENT-WINDOW.TEMPLATE.NOT-RELEASED.json': fill}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--emit-static', type=Path)
    mode.add_argument('--check-static', type=Path)
    args = parser.parse_args()
    require(ref(ORIGIN)['sha256'] == ORIGIN_SHA, 'retained source27 consumer changed')
    origin = json.loads(ORIGIN.read_text())
    require(ref(Path(origin['request']['path'])) == origin['request'], 'retained request changed')
    request = json.loads(Path(origin['request']['path']).read_text())
    window = json.loads(WINDOW.read_text())
    require(window['deadline_epoch'] == 1793100290, 'current fixed deadline changed')
    result = bindings(origin, request, window, ref(WINDOW))
    if args.check_static:
        for name, value in result.items():
            require(json.loads((args.check_static / name).read_text()) == value,
                    'emitted static binding differs: ' + name)
        print('PASS_STATIC_CURRENT_WINDOW_SOURCE_EQUIVALENCE_NO_RUNTIME')
        return
    args.emit_static.mkdir(mode=0o700, exist_ok=False)
    for name, value in result.items():
        with (args.emit_static / name).open('x') as stream:
            stream.write(json.dumps(value, indent=2) + '\n')


if __name__ == '__main__':
    main()
