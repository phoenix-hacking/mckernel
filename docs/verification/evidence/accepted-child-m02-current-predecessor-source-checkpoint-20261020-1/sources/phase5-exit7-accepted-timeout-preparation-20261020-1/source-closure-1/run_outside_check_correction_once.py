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
CAPTURE = HERE / 'actual-outside-check-correction-1'
HELPER = Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
PINS = {
    'checker-correction-proposal.json': '8b9354b5bc78e83f877eb12ae4960300d8d402e2a4ce0f4f1213ec557a356ff2',
    'successor-proposal.json': '46ae09aac64b21e1ce5ceac7e049f3a761975baa55607459e21f02b2e8cdbb0a',
    'source-pins.json': 'dbb3c23a6920c164cc5773927812b8282d4deb9555bdd012c4d0410ffbe0be5f',
    'check_outside_owner_correction.py': 'be8b2fdbfb95bfefdd7eae683eebcf74638e9f575d1e6c3730e669c039231435',
    'native_diagnostic_container_owner.py': '5a6f6fb51043438d438d01f37e8d0705857036536b7dba1c235dbd89e05dd1ff',
    'binding.json': '009664e3a5845b9c87423adaf38c5a33a10c5de3bf08f413e5d6b159de89c967',
    'FINAL-SEVEN-ROOT-CALL-DATA.json': '1a99b6404eb65dfeb01364d97648d031b53d08a14f4003070001c50f941b2c25',
}

def main():
    assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
    assert resource.getrlimit(resource.RLIMIT_AS) == (1 << 30, 1 << 30)
    assert resource.getrlimit(resource.RLIMIT_CPU) == (30, 30)
    assert resource.getrlimit(resource.RLIMIT_FSIZE) == (32 << 20, 32 << 20)
    assert resource.getrlimit(resource.RLIMIT_CORE) == (0, 0)
    assert resource.getrlimit(resource.RLIMIT_NOFILE) == (256, 256)
    helperbytes = HELPER.read_bytes()
    assert len(helperbytes) == 14753 and hashlib.sha256(helperbytes).hexdigest() == HELPER_SHA and HELPER.stat().st_mode == 33152
    for name, digest in PINS.items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    used = state['last_rate_limits']['primary']['usedPercent']
    assert used < 100
    mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
    assert mem >= 5 << 30
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
    command = {'argv': ['/usr/bin/python3', '-I', '-B', str(HERE / 'check_outside_owner_correction.py')]}
    module.write(CAPTURE / 'command.json', command)
    def limits():
        os.sched_setaffinity(0, {6})
        for which, value in ((resource.RLIMIT_AS, 1 << 30), (resource.RLIMIT_CPU, 10),
                (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_CORE, 0), (resource.RLIMIT_NOFILE, 256)):
            resource.setrlimit(which, (value, value))
    started = time.monotonic()
    record = module.owned_capture(command, CAPTURE, wall_seconds=15, limits=limits)
    module.write(CAPTURE / 'status.json', record)
    ok = (record['returncode'] == 0 and record['direct_child_joined'] and record['group_absent'] and
        not record['timed_out'] and record['error'] is None and record['retirement_error'] is None and
        record['closed_streams'] and record['captures']['stderr']['size'] == 0)
    whole = dict(status='PASS_WHOLE_SOURCE_NO_EFFECT_PREFLIGHT_ONLY' if ok else 'FAIL_PRESERVE_FIRST_FAILURE',
        record=record, elapsed_seconds=time.monotonic() - started, CPU6_released_after_return=True,
        native_timeout_acceptance=False, runtime_release=None)
    module.write(CAPTURE / 'whole.json', whole)
    print(json.dumps(dict(status=whole['status'], elapsed_seconds=whole['elapsed_seconds'], capture=str(CAPTURE))))
    return 0 if ok else 1

if __name__ == '__main__':
    raise SystemExit(main())
