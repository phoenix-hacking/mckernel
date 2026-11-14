#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Dispatcher-granted CPU0 ordinary selected-memory TU check; no production claim.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import time

HERE=Path(__file__).resolve().parent
HOST=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/memory-combined-preparation-1')
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def main():
    started=time.monotonic()
    assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0}
    for limit,pair in ((resource.RLIMIT_AS,(2<<30,2<<30)),(resource.RLIMIT_CPU,(60,60)),
                       (resource.RLIMIT_FSIZE,(32<<20,32<<20)),(resource.RLIMIT_CORE,(0,0)),
                       (resource.RLIMIT_NOFILE,(256,256))):
        assert resource.getrlimit(limit)==pair,'exact granted inherited resource envelope'
    pins={HELPER:'990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8',
          HERE/'NEXT-CONSUMER-COMMANDS.json':'d49bbfcbbe8bbd556bebc88ffd211d698a47ae1df4ba9678c4d84b41309f3c65',
          HERE/'check_selected_memory_tu.py':'89187bc47cf14c94acc7bf88056fc0290d9006ba582d8615999dac948bf387c4'}
    for path,expected in pins.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,'frozen authorized source changed'
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    used=state['last_rate_limits']['primary']['usedPercent'];assert used<100,'included usage stop'
    host=os.statvfs(HOST);scratch=os.statvfs('/home/holden/mckernel-work/scratch')
    assert host.f_bavail*host.f_frsize >= (16<<30)+(64<<20),'HOSTfloor+64MiB new ordinary growth'
    assert scratch.f_bavail*scratch.f_frsize >= 12<<30,'scratch readonly floor'
    command=json.loads((HERE/'NEXT-CONSUMER-COMMANDS.json').read_text())['ordinary_host_only']['command']
    capture=HOST/'ordinary-selected-memory-capture-1';capture.mkdir(mode=0o700)
    spec=importlib.util.spec_from_file_location('approved_memory_capture',HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    helper.write(capture/'command.json',dict(scope=SCOPE,argv=command,source_pins={str(p):s for p,s in pins.items()}))
    helper.write(capture/'admission.json',dict(scope=SCOPE,cpu=0,usage_percent=used,
        HOST_available_bytes=host.f_bavail*host.f_frsize,scratch_available_bytes=scratch.f_bavail*scratch.f_frsize,
        root_grant='exact prepared completeTU ordinary GCC9 ABI/PP/nm/readelf; one job AS2GiB/CPU60/wall90+6/FSIZE32MiB/NOFILE256/core0'))
    receipt=helper.owned_capture({'argv':command},capture,90,lambda:None)
    helper.write(capture/'status.json',receipt)
    positive=(receipt['returncode']==0 and receipt['direct_child_joined'] and receipt['group_absent']
              and receipt['closed_streams'] and not receipt['timed_out'] and receipt['error'] is None
              and receipt['retirement_error'] is None and receipt['captures']['stderr']['size']==0
              and receipt['captures']['stdout']['size']<=8<<20 and helper.cpu_used()<=60)
    inner=HOST/'ordinary-selected-memory-tuple-attempt-1/result.json'
    result=dict(scope=SCOPE,status='PASS_ORDINARY_COMPLETE_MEMORY_TU_AND_POSITIVE_GROUP_JOIN' if positive else 'FAIL_PRESERVE_STOP',
        capture=receipt,seconds=time.monotonic()-started,whole_CPU_seconds=helper.cpu_used(),
        inner_result=json.loads(inner.read_text()) if inner.exists() else None,
        pinned_production=False,full_production_Rust=False,default_image_link=False,native=False)
    helper.write(HOST/'ORDINARY-SELECTED-MEMORY-RESULT-1.json',result)
    print(json.dumps(result,sort_keys=True))
    return 0 if positive else 1


if __name__=='__main__':
    raise SystemExit(main())
