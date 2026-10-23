#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Granted CPU6 actual-body permission fixture through approved whole-group capture.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import resource
import time

D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/correction1')
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def main():
    assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
    for number,pair in ((resource.RLIMIT_AS,(2<<30,2<<30)),(resource.RLIMIT_CPU,(30,30)),
        (resource.RLIMIT_FSIZE,(32<<20,32<<20)),(resource.RLIMIT_NOFILE,(256,256)),(resource.RLIMIT_CORE,(0,0))):
        assert resource.getrlimit(number)==pair
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
    state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    used={name:entry['usedPercent'] for name,entry in state['last_rate_limits'].items()
          if isinstance(entry,dict) and 'usedPercent' in entry}
    assert used and all(type(x) in (int,float) and x<100 for x in used.values()),'included usage stop'
    spec=importlib.util.spec_from_file_location('permission_owned_capture',HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    capture=H/'actual-permission-capture-1';capture.mkdir(mode=0o700)
    fixture=D/'test_actual_capture_permission.py'
    command={'scope':SCOPE,'argv':['/home/holden/anaconda3/bin/python3','-I','-B',str(fixture)],
        'fixture':helper.hashed(fixture,1<<20),'source_binding':helper.hashed(D/'CAP-CORRECTION-SOURCE-BINDING.json',1<<20),
        'ordinary_profile':'CPU6 onejob/AS2GiB/CPU30/FSIZE32MiB/NOFILE256/core0; inherited NPROC unchanged',
        'wall_seconds':32,'overall_wall_ceiling_with_approved_cleanup_seconds':38,
        'stricter_work_window_reason':'Reuse unchanged helper cleanup within granted35+3 overall envelope.',
        'usage_percent':used,'production_compile_or_root':False}
    helper.write(capture/'command.json',command)
    receipt=helper.owned_capture(command,capture,32,lambda:None)
    helper.write(capture/'status.json',receipt)
    positive=(receipt['returncode']==0 and receipt['direct_child_joined'] and receipt['group_absent']
        and receipt['closed_streams'] and not receipt['timed_out'] and receipt['error'] is None
        and receipt['retirement_error'] is None and receipt['captures']['stderr']['size']==0)
    result=dict(scope=SCOPE,status='PASS_ACTUAL_PERMISSION_FIXTURE_AND_WHOLE_JOIN' if positive else 'FAIL_STOP_PRESERVE_EXPERT',
        receipt=receipt,whole_CPU_seconds=helper.cpu_used(),
        result_path=str(H/'actual-permission-fixture-1/result.json'),
        compilers=0,builds=0,root_Docker_guests=0)
    helper.write(H/'ACTUAL-PERMISSION-WHOLE-JOIN.json',result)
    print(json.dumps(result,sort_keys=True))
    return 0 if positive else 1

if __name__=='__main__':raise SystemExit(main())
