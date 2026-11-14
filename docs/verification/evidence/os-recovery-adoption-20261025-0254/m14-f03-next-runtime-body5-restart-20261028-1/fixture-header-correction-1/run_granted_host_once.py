#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Execute only the exact new Root grant, stopping on first failure without retries.
"""
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
GRANT = HERE/'WORKER-RECORDED-STANDING-HOST-AUTHORIZATION.json'
GRANT_SHA = 'b67145d3ae0e65e50575314e541e4870737d8ef872d76e0483644d7be6aa5556'
GUARDIAN = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-operation-guard-source-20261028-1/guardian_guard.py')
GUARDIAN_SHA = '48893862bb3262a2c81d282215e4b9771b8f659e635a21856096c41233774f18'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def need(ok, why):
    if not ok:
        raise ValueError(why)

def ref(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def verify(row):
    need(ref(row['path']) == row, 'byte binding changed: '+row['path'])

def durable(path, value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())

def birth(pid):
    fields = (Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,start=fields[19],ppid=int(fields[1]),pgrp=int(fields[2]),
                session=int(fields[3]),state=fields[0])

def group_members(group):
    found = []
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():
            continue
        try:
            actor = birth(int(path.name))
            if actor['pgrp'] == group:
                found.append(actor)
        except (FileNotFoundError,ProcessLookupError,PermissionError):
            pass
    return found

def main():
    need(ref(GRANT)['sha256'] == GRANT_SHA, 'exact new Root grant')
    grant = json.loads(GRANT.read_text())
    need(grant['decision'] == 'WORKER_RECORDED_ACTUAL_PARENT_STANDING_HOST_AUTHORIZATION', 'ordinary grant')
    verify(grant['source_ready'])
    verify(grant['command_plan'])
    plan = json.loads(Path(grant['command_plan']['path']).read_text())
    need(not plan['executed'] and len(plan['commands']) == grant['maximum_commands'] == 2, 'exact three new commands')
    output = Path(grant['output'])
    need(not output.exists(), 'fresh output root required; never replay a started namespace')
    need(ref(GUARDIAN)['sha256'] == GUARDIAN_SHA, 'reviewed guardian source')
    spec = importlib.util.spec_from_file_location('body5_reviewed_readonly_guardian',GUARDIAN)
    guardian = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guardian)
    # One actual reviewed guard call authenticates its immutable source/arm closure.
    initial_clocks = guardian.guard()
    output.mkdir()
    capture = output/'actual-three-command-capture-1'
    capture.mkdir()
    durable(capture/'GUARDIAN-PREENTRY.json',dict(scope=SCOPE,status='PASS',source=ref(GUARDIAN),clocks_epoch_MONO_BOOT=initial_clocks))
    results = []
    total_start = time.monotonic()

    def before_command(index):
        need(ref(GRANT)['sha256'] == GRANT_SHA, 'grant unchanged')
        verify(grant['source_ready'])
        verify(grant['command_plan'])
        for row in grant['actual_source_preimage_bindings']+grant['actual_tools']:
            verify(row)
        need(ref(GUARDIAN)['sha256'] == GUARDIAN_SHA, 'guardian source unchanged')
        control = guardian.CONTROL
        clocks = [time.time(),time.monotonic(),time.clock_gettime(time.CLOCK_BOOTTIME)]
        # Fresh pure read-only validation of actual controls/time/account before
        # each command; no controller/module starts, locks, signals or writes.
        armed = json.loads(Path(guardian.ARM_RECEIPT_REF['path']).read_text())
        verify(guardian.ARM_RECEIPT_REF)
        guardian.validate_control_config(guardian.read(control/'armed-controller/CONFIG.json'))
        guardian.validate(guardian.read(guardian.BASE/'ACTUAL-WINDOW.json'),
            guardian.read(control/'armed-controller/journal.json'),
            guardian.read(control/'armed-controller/bridge-start.json'),
            guardian.read(guardian.CAMPAIGN/'state.json'),guardian.read(guardian.CAMPAIGN/'watcher.json'),
            guardian.birth,clocks,Path('/proc/sys/kernel/random/boot_id').read_text().strip(),armed)
        need(all(now < cap for now,cap in zip(clocks,grant['actual_cutoffs'])), 'strict grant caps')
        need(grant['cpu'] == 6 and grant['jobs'] == 1 and os.sched_getaffinity(0) == {6}, 'one CPU6 runner')
        if index == len(plan['commands'])-1:
            need(Path(plan['commands'][-1]['argv'][0]).is_file(), 'newly produced parity executable')
        return clocks

    for index, command in enumerate(plan['commands']):
        record_dir = capture/command['label']
        record_dir.mkdir()
        try:
            clocks = before_command(index)
        except Exception as error:
            durable(record_dir/'PREENTRY-REFUSAL.json',dict(scope=SCOPE,status='REFUSED_BEFORE_CHILD',error=repr(error)))
            results.append(dict(index=index,label=command['label'],status='PREENTRY_REFUSED',error=repr(error)))
            break
        stdout_path,stderr_path = record_dir/'stdout',record_dir/'stderr'
        stdout = stdout_path.open('xb')
        stderr = stderr_path.open('xb')
        read_gate,write_gate = os.pipe()
        started_epoch,started = time.time(),time.monotonic()
        pid = os.fork()
        if pid == 0:
            try:
                os.close(write_gate)
                os.setsid()
                os.sched_setaffinity(0,{6})
                resource.setrlimit(resource.RLIMIT_AS,(grant['AS_bytes'],grant['AS_bytes']))
                resource.setrlimit(resource.RLIMIT_CPU,(grant['CPU_seconds'],grant['CPU_seconds']))
                os.dup2(stdout.fileno(),1)
                os.dup2(stderr.fileno(),2)
                stdout.close()
                stderr.close()
                token = os.read(read_gate,1)
                os.close(read_gate)
                if token != b'1':
                    os._exit(125)
                os.chdir(command['cwd'])
                os.execv(command['argv'][0],command['argv'])
            except BaseException as error:
                os.write(2,repr(error).encode()+b'\n')
                os._exit(126)
        os.close(read_gate)
        actor = birth(pid)
        # The child may not yet have reached setsid; preserve the same PID birth
        # and observe its final gated profile before allowing the exact argv.
        gate_until = time.monotonic()+5
        while actor['pgrp'] != pid and time.monotonic() < gate_until:
            time.sleep(.001)
            actor = birth(pid)
        need(actor['pgrp'] == actor['session'] == pid and os.sched_getaffinity(pid) == {6}, 'gated child profile')
        record = dict(scope=SCOPE,index=index,label=command['label'],argv=command['argv'],cwd=command['cwd'],
            purpose=command['purpose'],actor=actor,affinity=sorted(os.sched_getaffinity(pid)),
            preentry_clocks_epoch_MONO_BOOT=clocks,started_epoch=started_epoch,
            limits=dict(AS_bytes=grant['AS_bytes'],CPU_seconds=grant['CPU_seconds'],wall_seconds=grant['wall_seconds'],jobs=1),
            stdout=str(stdout_path),stderr=str(stderr_path))
        if index == len(plan['commands'])-1:
            record['new_executable'] = ref(command['argv'][0])
        durable(record_dir/'command.json',record)
        os.write(write_gate,b'1')
        os.close(write_gate)
        joined = None
        while time.monotonic()-started < grant['wall_seconds']:
            observed,status,usage = os.wait4(pid,os.WNOHANG)
            if observed == pid:
                joined = (status,usage)
                break
            time.sleep(.01)
        elapsed = time.monotonic()-started
        stdout.close()
        stderr.close()
        result = dict(record,wall_seconds=elapsed,finished_epoch=time.time(),
                      stdout_record=ref(stdout_path),stderr_record=ref(stderr_path),
                      parent_streams_closed=stdout.closed and stderr.closed)
        if joined is None:
            result.update(status='WALL_LIMIT_OWNERSHIP_UNCERTAIN_NO_AUTOKILL_NO_RETRY',positive_wait4_join=False,
                          live_group_members=group_members(pid),child_proc_exists=(Path('/proc')/str(pid)).exists())
        else:
            status,usage = joined
            members = group_members(pid)
            returncode = os.waitstatus_to_exitcode(status)
            result.update(status='JOINED',returncode=returncode,wait_status=status,positive_wait4_join=True,
                          wait4_pid=pid,CPU_seconds=usage.ru_utime+usage.ru_stime,user_seconds=usage.ru_utime,
                          system_seconds=usage.ru_stime,peak_RSS_KiB=usage.ru_maxrss,
                          process_group_members=members,process_group_absent=not members,
                          child_proc_absent=not (Path('/proc')/str(pid)).exists())
        durable(record_dir/'result.json',result)
        results.append(result)
        if joined is None or result['returncode'] != 0 or not result['process_group_absent'] or not result['child_proc_absent']:
            break
    passed = (len(results) == 2 and all(row.get('returncode') == 0 and row.get('positive_wait4_join')
              and row.get('process_group_absent') and row.get('parent_streams_closed') for row in results))
    if passed:
        observed = Path(results[-1]['stdout']).read_text().strip()
        passed = observed == plan['expected_stdout'] and all(not Path(row['stderr']).read_bytes() for row in results[1:])
    final = dict(scope=SCOPE,status='PASS_TWO_COMMAND_CORRECTION_ABI52_AND_1152_PAIRS' if passed else 'FIRST_FAILURE_STOPPED_NO_RETRY',
                 grant=ref(GRANT),plan=grant['command_plan'],commands=results,actual_commands_started=sum('actor' in row for row in results),
                 whole_wall_seconds=time.monotonic()-total_start,canonical_writes=0,default_artifacts=0,native=0,file_closures=0,
                 limitations='HOST genuine-header ABI and mocked functional callbacks only; no default/native/file credit.')
    durable(output/'ACTUAL-HOST-RESULT.json',final)
    print(json.dumps(dict(status=final['status'],actual_commands_started=final['actual_commands_started'],receipt=ref(output/'ACTUAL-HOST-RESULT.json'))))

if __name__ == '__main__':
    main()
