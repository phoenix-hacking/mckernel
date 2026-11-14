"""One frozen M07 typed-stdout case; original observation is never rewritten."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

CASE_ID = 'vector.remaining-components-preservation'
BASE = Path('/home/holden/mckernel/scripts/application-tests/native_diagnostic.py')
BASE_SHA = '1b43934aacf63f21082448a99dd7237759387411200ced997aa2a16700505e5e'
PARSER = Path('/home/holden/mckernel-work/host-preparation/M07-current-profile-next-observation-preparation-20261021-1/remaining-components-functional-case-preparation-20261022-1/joint-mpx-exact-fault-correction-1/current053d-stage-preparation-1/ordinary-normalization-runtime-integration-1/runtime-source-1/remaining_stdout.py')
PARSER_SHA = 'ee31daf16f59f8ce2e37a2df3e359f25299539b5400d043c5471ab08a0bd137a'
MANIFEST = Path('/home/holden/mckernel-work/scratch/m07ra-261022-1/manifest.json')
MANIFEST_SHA = 'fbf0f19ef7beace55555cd1bf401ae9a4cefcbcfa1efe234ac1ce01eac8d3824'
SENTINEL = b'REMAINING_TYPED_OUTPUT_V1\n'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(name, path, expected):
    if digest(path) != expected:
        raise ValueError('M07 source identity drift: ' + str(path))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def binding(manifest_path, expected_sha):
    nd = load('m07_original_nd', BASE, BASE_SHA)
    try:
        nd._need(str(manifest_path) == str(MANIFEST) and expected_sha == MANIFEST_SHA,
                 'M07 frozen manifest identity')
        nd._need(digest(MANIFEST) == MANIFEST_SHA, 'M07 manifest source drift')
        parser = load('m07_enabled_stdout', PARSER, PARSER_SHA)
        frozen = nd.load_manifest(str(MANIFEST))
        nd._need(frozen['case_id'] == CASE_ID, 'M07 case only')
        oracle = frozen['payload']['oracle']
        nd._need(set(oracle) == {'stdout_hex','stderr_hex','exit_code'} and
                 oracle['stdout_hex'] == SENTINEL.hex() and
                 oracle['stderr_hex'] == '' and type(oracle['exit_code']) is int and
                 oracle['exit_code'] == 0, 'M07 frozen oracle sentinel')
        return nd, parser, frozen
    except Exception as error:
        raise nd.DiagnosticError('M07 binding: '+str(error)) from error


def case_evaluate(manifest, observation):
    nd, parser, frozen = binding(str(MANIFEST), MANIFEST_SHA)
    try:
        # Both runner and owner provide strict immutable normalized plans.
        nd._need(nd._same_plan(nd._freeze(nd._thaw(manifest)), nd._freeze(nd._thaw(frozen))), 'M07 original manifest plan changed')
        serial = observation['serial']
        nd._need(type(serial) is str, 'M07 serial type')
        rows = [line[len('ND_PAYLOAD '):] for line in serial.splitlines()
                if line.startswith('ND_PAYLOAD ')]
        nd._need(len(rows) == 1 and len(rows[0]) <= nd.MAX_JSON, 'M07 unique payload')
        report = json.loads(rows[0], object_pairs_hook=nd._pairs)
        nd._keys(report, ('argv','cwd','env','raw_wait_status','started_ns','reaped_ns',
                          'finished_ns','streams','procfs_empty'))
        raw = report['raw_wait_status']
        nd._need(type(raw) is int and 0 <= raw <= 65535 and os.WIFEXITED(raw) and
                 os.WEXITSTATUS(raw) in (0,2), 'M07 raw exited zero')
        nd._keys(report['streams'], ('stdout','stderr'))
        streams = report['streams']; decoded = {}
        for name in ('stdout','stderr'):
            row = streams[name]
            nd._keys(row, ('hex','eof','truncated','observed','retained','discarded','limit','eof_ns'))
            nd._need(type(row['hex']) is str and re.fullmatch(r'(?:[0-9a-f]{2})*',row['hex']),
                     'M07 lowercase stream hex')
            decoded[name] = bytes.fromhex(row['hex'])
        exposure = parser.validate_capture(decoded['stdout'],decoded['stderr'],os.WEXITSTATUS(raw),
            stdout_eof=streams['stdout']['eof'],stderr_eof=streams['stderr']['eof'],
            stdout_discarded=streams['stdout']['discarded'],stderr_discarded=streams['stderr']['discarded'],
            stdout_truncated=streams['stdout']['truncated'],stderr_truncated=streams['stderr']['truncated'])
        local_manifest = nd._thaw(nd._freeze(frozen))
        local_manifest['payload']['oracle']['stdout_hex'] = streams['stdout']['hex']
        local_manifest['payload']['oracle']['exit_code'] = os.WEXITSTATUS(raw)
        # Only this local expected-byte field changes AFTER typed validation.
        # Base checks original accounting, lifecycle and every observation byte.
        result = nd.evaluate(local_manifest, observation)
        nd._need(not exposure['unmet_safe_seed_prerequisite'], 'M07 remaining STOP exit2: unmet safe-seed prerequisite; zero credit')
        nd._need(not exposure['all_inapplicable'], 'M07 remaining all-inapplicable: completed observation; zero credit')
        result['case_validation'] = dict(parser_sha256=PARSER_SHA,
            stdout_sha256=hashlib.sha256(decoded['stdout']).hexdigest(),
            exposure=exposure,scope='M07 remaining actual component preservation rows only; no whole-M07 acceptance')
        return result
    except Exception as error:
        raise nd.DiagnosticError('M07 case: '+str(error)) from error
