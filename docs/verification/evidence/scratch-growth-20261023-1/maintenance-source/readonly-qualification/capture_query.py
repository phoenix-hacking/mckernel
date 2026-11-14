#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Dispatcher-only candidate envelope; no execution release is embedded. One fixed
READ-ONLY privileged metadata query through the existing accepted owned_capture.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
HELPER = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
QUERY = HERE / 'query_installed.py'
QUERY_SHA = 'f0db6e0338cb5e8b806cc2a0fd926fc7ccde1b79adfce0b9bfaf48d1eae255cf'
CAPTURE = Path('/home/holden/mckernel-work/host-preparation/scratch-growth-20261023-1/readonly-qualification-attempt-1')
ARGV = ['/usr/bin/sudo', '-A', '/usr/bin/taskset', '-c', '7', '/usr/bin/prlimit',
        '--as=2147483648:2147483648', '--cpu=30:30', '--fsize=8388608:8388608',
        '--core=0:0', '--nofile=256:256', '--', '/home/holden/anaconda3/bin/python3', '-I', '-B', str(QUERY)]
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


def main():
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {7},
         'existing ordinary CPU7 capture parent required')
    need(hashlib.sha256(HELPER.read_bytes()).hexdigest() == HELPER_SHA, 'accepted owned_capture helper source')
    spec = importlib.util.spec_from_file_location('accepted_owned_capture', HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)  # Never invoke this helper's unrelated main.
    source = helper.hashed(QUERY, 1 << 20)
    need(source['sha256'] == QUERY_SHA, 'frozen query source changed')
    need(CAPTURE.parent.resolve() == CAPTURE.parent and not os.path.lexists(CAPTURE),
         'fresh one-shot metadata capture namespace required')
    CAPTURE.mkdir(mode=0o700)
    command = dict(scope=SCOPE, argv=ARGV, wall_seconds=35, query_sha256=QUERY_SHA,
                   helper_sha256=HELPER_SHA, root_mutation_allowed=False)
    helper.write(CAPTURE / 'command.json', command)
    record = helper.owned_capture({'argv': ARGV}, CAPTURE, 35, lambda: None)
    helper.write(CAPTURE / 'receipt.json', record)
    need(record['returncode'] == 0 and record['direct_child_joined'] is True
         and record['group_absent'] is True and record['closed_streams'] is True
         and not record['timed_out'] and record['error'] is None and record['retirement_error'] is None,
         'readonly query/capture not positively closed; preserve and stop')
    streams = {name: helper.hashed(CAPTURE / name, maximum) for name, maximum in
               [('stdout', 8 << 20), ('stderr', 1 << 20)]}
    helper.write(CAPTURE / 'closed-streams.json', streams)
    report = json.loads((CAPTURE / 'stdout').read_text())
    need(report.get('status') == 'PASS_READONLY_INSTALLED_METADATA_NOT_VENDOR_SOURCE_QUALIFICATION'
         and report.get('vendor_source_qualification') is False
         and report.get('mutation_performed') is False
         and report.get('stock_resize2fs_fallback_risk_explicitly_accepted') is None,
         'metadata evidence only; no false qualification or operation acceptance')
    result = dict(status='PASS_CLOSED_READONLY_QUALIFICATION_METADATA', scope=SCOPE,
                  capture=str(CAPTURE), streams=streams, vendor_source_qualification=False,
                  root_mutation_released=False, stock_resize2fs_fallback_risk_explicitly_accepted=None)
    helper.write(CAPTURE / 'result.json', result)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
