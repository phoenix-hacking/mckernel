"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One Root-granted four-command nominal-ABI correction suffix. First failure stops the suffix.
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

H = Path(__file__).resolve().parent


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
    manifest_path = H / 'SEALED-SUFFIX.json'
    assert ref(manifest_path)['sha256'] == '4a16ac9932731fbcef24cc2842ef27cad2b7efb5011b80f2ffb2af401f2a91f8'
    manifest = json.loads(manifest_path.read_text())
    assert len(manifest['commands']) == 4
    for row in manifest['inputs'] + manifest['tools']:
        assert ref(row['path']) == row, row['path']
    guard_path = Path(manifest['guard']['path'])
    sys.path.insert(0, str(guard_path.parent))
    spec = importlib.util.spec_from_file_location('accepted_e8b_line13_admission', guard_path)
    guard = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(guard)
    # The unchanged d300 loader pins and AST-loads canonical04b5/adf pure checks.
    # No rebinding, policy correction, main function or privileged action is used.
    initial = guard.admission()
    output = Path(manifest['output'])
    output.mkdir(mode=0o700)
    records, failure = [], None
    started = time.time()
    try:
        for index, command in enumerate(manifest['commands']):
            for row in manifest['inputs'] + manifest['tools']:
                assert ref(row['path']) == row, row['path']
            admitted = guard.admission()
            wall, mono = time.time(), time.monotonic()
            stdout_path, stderr_path = output / (str(index) + '.stdout'), output / (str(index) + '.stderr')
            timed_out = False
            with stdout_path.open('xb') as stdout, stderr_path.open('xb') as stderr:
                child = subprocess.Popen(command['argv'], cwd=H, stdin=subprocess.DEVNULL,
                    stdout=stdout, stderr=stderr, start_new_session=True, close_fds=True,
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
                streams_closed=True, timed_out=timed_out, admission=admitted,
                stdout=ref(stdout_path), stderr=ref(stderr_path))
            records.append(record)
            (output / 'RESULTS.json').write_text(json.dumps(dict(status='RUNNING', results=records), indent=2) + '\n')
            if child.returncode or timed_out or not absent:
                raise RuntimeError('FIRST_FAILURE_STOP command ' + str(index))
        assert (output / '2.stdout').read_text() == 'PASS actual-original-C/Rust tracked forwarding: 82 comparisons, eight providers, narrowing/flags/null/free/file/line\n'
        assert (output / '3.stdout').read_text() == 'PASS five current Rust consumers: 210 original-C argument comparisons, 13 genuine ABI rows; line/file/narrowing/null/flags exact\n'
    except BaseException as error:
        failure = repr(error)
    result = dict(scope=__doc__.splitlines()[0], status='FAIL_FIRST_STOP_RETAIN_PREFIX' if failure else 'PASS_HOST13_STORAGE_ABI_AND_292_ACTUAL_CONSUMER_COMPARISONS',
        grant=manifest['grant'], sealed_manifest=ref(manifest_path), initial_admission=initial,
        original_failed_result=manifest['original_failed_result'], original_failure=manifest['original_failure'],
        successful_prefixes_reused=manifest['successful_prefixes_reused'], total_root_attempted_commands=8,
        started_wall=started, ended_wall=time.time(), results=records, failure=failure,
        first_compiler_timestamp=records[0]['started_wall'] if records else None,
        all_children_directly_joined=all(r['direct_wait'] for r in records),
        all_groups_absent=all(r['group_absent'] for r in records),
        all_streams_closed=all(r['streams_closed'] for r in records),
        CPU_seconds=sum(r['CPU_user']+r['CPU_system'] for r in records),
        command_wall_seconds=sum(r['elapsed'] for r in records),
        maximum_RSS_KiB=max((r['max_RSS_KiB'] for r in records), default=0),
        original82_assertions_unchanged=True, additional_five_comparisons=210,
        account_loader='Unchanged accepted d300 loader uses pinned canonical04b5/adf pure functions; initial hash-label misunderstanding caused no workload failure or policy change.',
        production_or_native_credit=False, C_record_retirement_credit=0, whole_file_acceptance=False)
    (output / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], commands=len(records), failure=failure,
        all_joined=result['all_children_directly_joined'], groups_absent=result['all_groups_absent'],
        CPU_seconds=result['CPU_seconds'], wall_seconds=result['command_wall_seconds'],
        maximum_RSS_KiB=result['maximum_RSS_KiB'])))
    if failure:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
