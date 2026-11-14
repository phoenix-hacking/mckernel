"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-granted timer-table HOST cohort, CPU6/job1. First failure preserves prefix.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time

P = Path(__file__).resolve().parent


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def main():
    assert os.getuid() == os.geteuid() == os.getgid() == os.getegid() == 1000
    os.sched_setaffinity(0, {6})
    for kind, limit in [(resource.RLIMIT_AS, 2 * 2**30), (resource.RLIMIT_CPU, 60),
                        (resource.RLIMIT_FSIZE, 64 * 2**20), (resource.RLIMIT_CORE, 0)]:
        resource.setrlimit(kind, (limit, limit))
    grant_path = P / 'ROOT-ORDINARY-CPU6-GRANT.json'
    assert ref(grant_path)['sha256'] == '3fdf1be9efc7245742070108bda69a802733a5331c88acb60fec0aa78e5ffdb2'
    grant = json.loads(grant_path.read_text())
    assert grant['decision'] == 'GRANT_ONE_ORDINARY_CPU6_F02_TIMER_TABLE_HOST_COHORT'
    plan_path = Path(grant['plan']['path'])
    assert ref(plan_path) == grant['plan']
    plan = json.loads(plan_path.read_text())
    assert len(plan['commands']) == grant['maximum_compiler_test_commands'] == 7
    for row in plan['inputs'] + plan['tools']:
        assert ref(row['path']) == row, row['path']
    guard_dir = P.parent / ('m14-f06-selected-residual-implementation-20261026-1/'
        'next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/'
        'reviewed-account-supervisor-correction-1')
    assert ref(guard_dir / 'run_sealed.py')['sha256'] == 'e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
    sys.path.insert(0, str(guard_dir))
    spec = importlib.util.spec_from_file_location('accepted_timer_HOST_admission', guard_dir / 'run_sealed.py')
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    initial = guard.admission()
    output = Path(plan['output_namespace'])
    output.mkdir(mode=0o700)
    records, failure = [], None
    start_wall = time.time()
    try:
        for index, command in enumerate(plan['commands']):
            for row in plan['inputs'] + plan['tools']:
                assert ref(row['path']) == row, row['path']
            admission = guard.admission()
            wall, mono = time.time(), time.monotonic()
            stdout_path = output / (str(index) + '.stdout')
            stderr_path = output / (str(index) + '.stderr')
            timed_out = False
            with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
                child = subprocess.Popen(command['argv'], cwd=P, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, close_fds=True, start_new_session=True,
                    env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'RUST_BACKTRACE': '0',
                         'PYTHONDONTWRITEBYTECODE': '1'})
                while True:
                    pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                    if pid:
                        break
                    if time.monotonic() - mono >= 90:
                        timed_out = True
                        os.killpg(child.pid, signal.SIGKILL)
                        pid, status, usage = os.wait4(child.pid, 0)
                        break
                    time.sleep(.01)
                child.returncode = os.waitstatus_to_exitcode(status)
            try:
                os.killpg(child.pid, 0)
                absent = False
            except ProcessLookupError:
                absent = True
            record = dict(index=index, name=command['name'], argv=command['argv'],
                purpose=command['purpose'], pid=child.pid, started_wall=wall,
                ended_wall=time.time(), elapsed=time.monotonic()-mono,
                returncode=child.returncode, CPU_user=usage.ru_utime, CPU_system=usage.ru_stime,
                max_RSS_KiB=usage.ru_maxrss, direct_wait=True, group_absent=absent,
                streams_closed=True, timed_out=timed_out, admission=admission,
                stdout=ref(stdout_path), stderr=ref(stderr_path))
            records.append(record)
            (output / 'RESULTS.json').write_text(json.dumps(dict(status='RUNNING', results=records), indent=2) + '\n')
            if child.returncode or timed_out or not absent:
                raise RuntimeError('FIRST_FAILURE_STOP command ' + str(index))
        expected = ('PASS original-C/actual-Rust wrapper pairs=25750; real existing Rust timer semantics '
                    'plus callback/descriptor/ordering and ignored-return checks\n')
        assert (output / '6.stdout').read_text() == expected
    except BaseException as error:
        failure = repr(error)
    result = dict(scope=__doc__.splitlines()[0],
        status='FAIL_FIRST_STOP_RETAIN_SUCCESSFUL_PREFIX' if failure else 'PASS_TIMER120_HOST_15_ABI_WORDS_AND_GENUINE_TYPE_25750_COMPARISONS',
        grant=ref(grant_path), plan=ref(plan_path), initial_admission=initial,
        started_wall=start_wall, ended_wall=time.time(), results=records, failure=failure,
        first_compiler_timestamp=records[0]['started_wall'] if records else None,
        all_children_directly_joined=all(r['direct_wait'] for r in records),
        all_groups_absent=all(r['group_absent'] for r in records),
        all_streams_closed=all(r['streams_closed'] for r in records),
        CPU_seconds=sum(r['CPU_user']+r['CPU_system'] for r in records),
        command_wall_seconds=sum(r['elapsed'] for r in records),
        maximum_RSS_KiB=max((r['max_RSS_KiB'] for r in records), default=0),
        production_or_native_credit=False, current_C_records_counted=71,
        C_data_retirement_credit=0, whole_file_acceptance=False)
    (output / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], commands=len(records), failure=failure,
        all_joined=result['all_children_directly_joined'], groups_absent=result['all_groups_absent'],
        CPU_seconds=result['CPU_seconds'], wall_seconds=result['command_wall_seconds'],
        maximum_RSS_KiB=result['maximum_RSS_KiB'])))
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
