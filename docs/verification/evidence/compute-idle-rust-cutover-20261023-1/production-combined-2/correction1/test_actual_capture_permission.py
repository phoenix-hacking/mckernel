#!/usr/bin/python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual runner/M14 function bodies, real child limits/commands; no production compiler.
"""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import os
import resource
import signal
import subprocess
import time
import types

D=Path(__file__).resolve().parent
H=Path('/home/holden/mckernel-work/host-preparation/compute-idle-rust-cutover-20261023-1/production-combined-2/correction1')
HELPER=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def main():
    assert os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
    assert resource.getrlimit(resource.RLIMIT_AS)==(2<<30,2<<30)
    assert resource.getrlimit(resource.RLIMIT_CPU)==(30,30)
    assert resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20)
    assert resource.getrlimit(resource.RLIMIT_NOFILE)==(256,256)
    assert resource.getrlimit(resource.RLIMIT_CORE)==(0,0)
    bind=json.loads((D/'CAP-CORRECTION-SOURCE-BINDING.json').read_text())
    old=Path(bind['old_driver']['path']).read_bytes();new=Path(bind['new_driver']['path']).read_bytes()
    assert hashlib.sha256(old).hexdigest()==bind['old_driver']['sha256']
    assert hashlib.sha256(new).hexdigest()==bind['new_driver']['sha256']
    assert hashlib.sha256(HELPER.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
    spec=importlib.util.spec_from_file_location('approved_permission_census',HELPER)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    work=H/'actual-permission-fixture-1';work.mkdir()
    children=[];tests=[];commands=[]
    def tracked_popen(*args,**kwargs):
        child=subprocess.Popen(*args,**kwargs)
        children.append(dict(process=child,pid=child.pid,start=helper.process_start(child.pid),argv=args[0]))
        return child
    proxy=types.SimpleNamespace(Popen=tracked_popen,TimeoutExpired=subprocess.TimeoutExpired)
    def extract(data):
        tree=ast.parse(data.decode());names={'ImageBuildError','_signal_requested','_check_signal','_fsync_file',
            '_group_alive','_stop_group','_fail','_sha256','_run_process','_m14_observe'}
        selected=[n for n in tree.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
        assert {n.name for n in selected}==names
        ns=dict(Path=Path,hashlib=hashlib,os=os,resource=resource,signal=signal,subprocess=proxy,
                time=time,_ACTIVE_LATCH=None,MAX_TIMEOUT=19800)
        exec(compile(ast.Module(body=selected,type_ignores=[]),str(work/'actual-driver-body.py'),'exec'),ns)
        return ns,{n.name:ast.dump(n,include_attributes=False) for n in selected}
    before,old_ast=extract(old);after,new_ast=extract(new)
    assert old_ast['_run_process']==new_ast['_run_process']
    assert old_ast['_m14_observe']!=new_ast['_m14_observe']
    env=dict(os.environ,LC_ALL='C')
    def child_for_cap(cap):
        expected=(32<<20) if cap is None else cap
        code='import resource; a=resource.getrlimit(resource.RLIMIT_FSIZE); assert a==('+str(expected)+','+str(expected)+'),a; print("PASS_CHILD_FSIZE_'+str(expected)+'")'
        return ['/usr/bin/python3','-I','-B','-c',code]
    # Expected regression: the frozen original fails BEFORE launching its command.
    count=len(children)
    try:before['_m14_observe'](child_for_cap(1<<20),'original32-rejected',work,{},env,2,commands)
    except before['ImageBuildError'] as e:assert str(e)=='bounded release export capture'
    else:raise AssertionError('frozen original unexpectedly allowed32MiB')
    assert len(children)==count
    tests.append(dict(case='original_M14_32MiB_refused_before_launch',pass_=True))
    # The corrected CALLSITE and ORIGINAL RUNNER launch a real child whose
    # kernel-enforced FSIZE pair is exactly the unchanged admitted1MiB.
    stdout=after['_m14_observe'](child_for_cap(1<<20),'corrected1MiB-permitted',work,{},env,2,commands)
    assert stdout=='PASS_CHILD_FSIZE_1048576\n'
    tests.append(dict(case='corrected_M14_1MiB_real_child_limit_and_command',pass_=True))
    baseline=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o')
    reloc=after['_m14_observe'](['/usr/bin/readelf','-rW',str(baseline)],'actual-baseline-process-relocations',work,{},env,2,commands)
    assert 'Relocation section' in reloc and len(reloc.encode()) < 1<<20
    tests.append(dict(case='real_baseline_process_relocation_output_fits1MiB',pass_=True,bytes=len(reloc.encode())))
    for cap in (None,4096):
        label='normal-none' if cap is None else 'normal4096'
        rc=after['_run_process'](child_for_cap(cap),work,env,work/(label+'.stdout'),work/(label+'.stderr'),2,label,output_fsize=cap)
        assert rc==0
        tests.append(dict(case=label+'_unchanged_real_child_limit',pass_=True))
    # General runner admission is untouched for ALL unrelated callers.
    for i,cap in enumerate((0,-1,1048577,32<<20,True,False,'1048576',1.0)):
        count=len(children)
        try:after['_run_process'](child_for_cap(4096),work,env,work/('invalid'+str(i)+'.stdout'),work/('invalid'+str(i)+'.stderr'),2,'invalid',output_fsize=cap)
        except after['ImageBuildError'] as e:assert str(e)=='bounded release export capture'
        else:raise AssertionError('unrelated invalid cap allowed: '+repr(cap))
        assert len(children)==count
        tests.append(dict(case='unrelated_invalid_cap_'+repr(cap),pass_=True))
    joined=[]
    for entry in children:
        child=entry.pop('process')
        assert child.returncode==0 and not helper.members(child.pid)
        entry.update(returncode=child.returncode,direct_child_joined=True,whole_group_absent=True)
        joined.append(entry)
    result=dict(scope=SCOPE,status='PASS_ACTUAL_M14_PERMISSION_BODY_AND_UNCHANGED_RUNNER_CAP',
        cases=len(tests),real_commands=len(children),tests=tests,children=joined,command_rows=commands,
        actual_runner_body_unchanged=True,admitted_selected_M14_cap_bytes=1<<20,
        unrelated_guard_remains_max1MiB=True,production_compilers=0,root_Docker_guests=0,
        old_driver_sha256=bind['old_driver']['sha256'],new_driver_sha256=bind['new_driver']['sha256'])
    with (work/'result.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':main()
