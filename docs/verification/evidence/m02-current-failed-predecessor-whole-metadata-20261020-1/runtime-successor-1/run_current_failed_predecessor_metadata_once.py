#!/usr/bin/env python3
"""Exact ordinary once caller; execution requires root dispatcher's external grant."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CAPTURE = HERE / 'actual-current-metadata-nineteen-capture-1'
HELPER = Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
PINS = {'/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/current_m02_contract.py': '5900686a474d8f9a707a899343ae94c16fdb3f25cf77263d00ca73883e2d4f68', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/CURRENT-SOURCE-CONTEXT.json': 'e112a92964f687f1d570ca0f8d415a107c3697602e21a69492f0b8d6d1230b02', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/bind_m03_handshake_native_packet.py': '582914664e9a4b872c6375be6201cc6e2e585be7b44fdbf406c74b1fac5a39f2', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/root_manual_snapshot_m03.py': '774fa7920e8f93a932aafc770b4251bebb53362643741166f546b22e83bc1ee9', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/materialize_current_m02_once.py': '452b69fce80c33aab99ebbcc9e8f68360c6145dc3554294442bd3bd528790f85', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/review_final_205_release.py': '8ebb8f92ccb5ebe40a6a98fd11f937e1ce4c2a88a3f426e10dcfe26df8bcb2e5', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/current-sources/machine_assembly_caller.py': 'd5ce0f360e4511c38681ce83624c35ea729d0006c3ec03774ab9aef007034103', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/prepare_current_parent_once.py': '3090c90149091d40c8d03fac115c384d143d7bfa7a124409f37a5b078ae5c172', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/runtime-successor-1/CURRENT-CASE-DATA.reader-bound.json': '678009047eb99461a40e2674075951ff3dc615453f93192036a9b5d3ea7271cc', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/native_child_failure_physical_projection.py': '7e07f1ba42ad08c32d4351024e38c50e9f32f8a006b00f48cee7955d73786c82', '/home/holden/mckernel-work/host-preparation/phase5-exit7-accepted-timeout-preparation-20261020-1/runtime-data-preparation-1/correction-1/next-predecessor-preparation-1/CURRENT-CHILD-FAILURE-CONTEXT.json': 'efded3e8c1d34026b81227c90cb6ac7f2f3eecae39c4175b6bc67f9872631253'}

def main():
    assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
    assert resource.getrlimit(resource.RLIMIT_AS) == (2 << 30, 2 << 30)
    assert resource.getrlimit(resource.RLIMIT_CPU) == (35, 35)
    assert resource.getrlimit(resource.RLIMIT_FSIZE) == (32 << 20, 32 << 20)
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
    assert resource.getrlimit(resource.RLIMIT_NOFILE) == (256, 256)
    assert len(sys.argv) == 5, 'STATIC_REVIEW SHA256 FETCHED_SOURCE_PROOF SHA256'
    helperbytes = HELPER.read_bytes()
    assert len(helperbytes) == 14753 and hashlib.sha256(helperbytes).hexdigest() == HELPER_SHA and HELPER.stat().st_mode == 33152
    for name, digest in PINS.items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    used = state['last_rate_limits']['primary']['usedPercent']
    assert used < 100
    mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    assert mem >= 10 << 30
    hoststat, scratchstat = os.statvfs(HERE), os.statvfs('/home/holden/mckernel-work/scratch')
    hostfree = hoststat.f_bavail * hoststat.f_frsize
    scratchfree = scratchstat.f_bavail * scratchstat.f_frsize
    assert hostfree >= (16 << 30) + (64 << 20) and scratchfree >= (12 << 30) + (1 << 20)
    assert not os.path.lexists(CAPTURE)
    spec = importlib.util.spec_from_file_location('m02_exact_outside_owned_capture_990807_once', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    CAPTURE.mkdir(mode=0o700)
    module.write(CAPTURE / 'admission.json', dict(cpu=6, usage_percent=used, mem_available=mem,
        host_free=hostfree, scratch_free=scratchfree, source_pins=PINS,
        helper_sha256=HELPER_SHA, external_root_CPU6_and_aggregate_grant_required=True))
    command = {'argv': ['/usr/bin/python3', '-I', '-B', str(HERE / 'current-sources/materialize_current_m02_once.py')] + sys.argv[1:]}
    module.write(CAPTURE / 'command.json', command)
    def limits():
        os.sched_setaffinity(0, {6})
        for which, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 20),
                (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, 256)):
            resource.setrlimit(which, (value, value))
    started = time.monotonic()
    record = module.owned_capture(command, CAPTURE, wall_seconds=30, limits=limits)
    module.write(CAPTURE / 'status.json', record)
    ok = (record['returncode'] == 0 and record['direct_child_joined'] and record['group_absent'] and
        not record['timed_out'] and record['error'] is None and record['retirement_error'] is None and
        record['closed_streams'] and record['captures']['stderr']['size'] == 0)
    whole = dict(status='PASS_CURRENT_METADATA_NINETEEN_COMMAND_ONLY' if ok else 'FAIL_PRESERVE_FIRST_FAILURE',
        record=record, elapsed_seconds=time.monotonic() - started, CPU6_released_after_return=True,
        native_timeout_acceptance=False, runtime_release=None)
    module.write(CAPTURE / 'whole.json', whole)
    print(json.dumps(dict(status=whole['status'], elapsed_seconds=whole['elapsed_seconds'], capture=str(CAPTURE))))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
