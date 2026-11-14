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
CAPTURE = HERE / 'actual-current-contract-source-check-1'
HELPER = Path('/home/holden/mckernel-work/host-preparation/current-host-pair-205-launch-expansion-20261020-1/failure-diagnostic-1/route-proof-correction-1/stage-preparation-1/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
PINS = {'CURRENT-COMPLETE-METADATA-PATH-PROPOSAL.json': 'b25ec76dd33fc1c96fd35d55245435dc11829e060c02f2004e4ad4889f9e8b9f', 'CURRENT-CASE-DATA.reader-bound.json': '6e0d8ff35828340d9b0037d40b07074363ffb9e68e13359bbd49863f3e5174d4', 'current-sources/bind_m03_handshake_native_packet.py': 'bcc41b68feb6573fd4fb24bcd57ba50f76a395f7a6cb4f58552acd3cf3dd9fb4', 'current-sources/check_current_contract_source_once.py': '4f45780a989bbf605686690ee37d028d194af972ffc65bbf47662708fc8efac1', 'current-sources/materialize_current_m02_once.py': '8e567c6a50b6ed5ac5ceb32eb95781686dfcdf7f10de02974f0402c578354f20', 'current-sources/review_final_205_release.py': '8ebb8f92ccb5ebe40a6a98fd11f937e1ce4c2a88a3f426e10dcfe26df8bcb2e5', 'current-sources/machine_assembly_caller.py': 'd5ce0f360e4511c38681ce83624c35ea729d0006c3ec03774ab9aef007034103', 'current-sources/run_final19_once.py': 'ded2516a81df29a957eb0bb82c540b9d463eeb2ca53d98cc0906a27bfd774458', 'current-sources/root_manual_snapshot_m03.py': '3f14e3ada437de13dc50d5d149d171250364c0e09f82fbf7d294f9f9d877d348', 'current-sources/current_m02_contract.py': 'f2d783fed6ee013da0523cff7eb8172c27f38bbf9eeef14e33e44a96ac7c3ea2', 'current-sources/CURRENT-SOURCE-CONTEXT.json': 'c5505116a991f4fd22bc62d295c30a0c72f0beea0951500938cd2bf5b318e8d6'}

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
    command = {'argv': ['/usr/bin/python3', '-I', '-B', str(HERE / 'current-sources/check_current_contract_source_once.py')]}
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
