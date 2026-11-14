"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One granted genuine-header GCC9 ABI-caller compile; no link or runtime driver.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
P = D.parent.parent

def ref(p):
    p = Path(p)
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def write(name, data):
    (D / name).write_text(json.dumps(data, indent=2) + '\n')

def verify_header(observed, record):
    # Generated headers have no source counterpart; actual is their pinned identity.
    expected = (record['actual']['sha256']
                if record['compiler_path'].startswith('/work/output/build/')
                else record['expected_source_sha256'])
    assert observed['sha256'] == expected, observed['path']

row = {'scope': __doc__, 'compiler_started': False}
try:
    assert os.getuid() == os.geteuid() == 1000
    plan_path = D.parent / 'NEXT-ABI-FACTS-COMMAND.json'
    assert ref(plan_path)['sha256'] == '0bdc60c15087fa18a14272e942bc9c19d39fb87832e38f86071149b38da6ac39'
    plan = json.loads(plan_path.read_text())
    assert plan['fresh_output_directory'] == str(D.parent / 'future-abi-facts-output-1')
    original_argv = list(plan['argv'])
    plan['argv'] = list(plan['argv'])
    plan['argv'][plan['argv'].index('-o') + 1] = str(D / 'real-ABI-and-validation-caller.o')
    row['original_argv'] = original_argv
    row['authorized_output_path_change_only'] = True
    for r in plan['inputs'] + [plan['tool']]:
        assert ref(r['path']) == r, r['path']
    config = json.loads(Path(plan['inputs'][1]['path']).read_text())
    headers = []
    for r in config['dependency_inputs']:
        q = r['compiler_path']
        if q.endswith('/syscall.c'):
            continue
        if q.startswith('/src/'):
            path = ROOT / q.removeprefix('/src/')
        elif q.startswith('/work/output/build/'):
            path = Path(plan['generated_build_root']) / q.removeprefix('/work/output/build/')
        else:
            path = Path(q)
        observed = ref(path)
        verify_header(observed, r)
        headers.append(observed)
    assert ref(config['generated_config']['path']) == config['generated_config']
    generated = next(r for r in config['dependency_inputs']
                     if r['compiler_path'] == '/work/output/build/config.h')
    ordinary = next(r for r in config['dependency_inputs']
                    if r['compiler_path'].startswith('/src/')
                    and not r['compiler_path'].endswith('/syscall.c'))
    verify_header(ref(config['generated_config']['path']), generated)
    verify_header(ref(ROOT / ordinary['compiler_path'].removeprefix('/src/')), ordinary)
    mutated = dict(generated, actual=dict(generated['actual'], sha256='0' * 64))
    try:
        verify_header(ref(config['generated_config']['path']), mutated)
    except AssertionError:
        pass
    else:
        raise AssertionError('mutated generated identity accepted')
    row['literal_header_tests'] = {'generated_actual': 'PASS', 'source_expected': 'PASS',
                                   'mutated_generated_actual_rejected': 'PASS'}
    supervisor = P / 'next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1/run_sealed.py'
    assert ref(supervisor)['sha256'] == 'e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
    sys.path.insert(0, str(supervisor.parent))
    spec = importlib.util.spec_from_file_location('reviewed_supervisor', supervisor)
    accepted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(accepted)
    admission = accepted.admission()
    capacity = {str(p): os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in
                [ROOT, Path('/home/holden/mckernel-work/scratch')]}
    assert capacity[str(ROOT)] >= 8 * 2**30
    assert capacity['/home/holden/mckernel-work/scratch'] >= 12 * 2**30
    wrapper = ['/usr/bin/taskset', '-c', '6', '/usr/bin/prlimit', '--as=2147483648',
               '--cpu=60', '--fsize=67108864', '--core=0', '--'] + plan['argv']
    row.update(plan=ref(plan_path), authenticated_headers=headers, supervisor=ref(supervisor),
               admission=admission, capacity=capacity, argv=plan['argv'], actual_argv=wrapper,
               environment={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'}, uid=os.getuid(),
               started_wall=time.time(), started_monotonic=time.monotonic())
    write('PRE-COMPILER.json', row)
    with (D / 'compiler.stdout').open('xb') as out, (D / 'compiler.stderr').open('xb') as err:
        child = subprocess.Popen(wrapper, cwd=plan['cwd'], stdin=subprocess.DEVNULL,
                                 stdout=out, stderr=err, env=row['environment'],
                                 start_new_session=True, close_fds=True)
        row.update(compiler_started=True, pid=child.pid)
        raw = Path('/proc') / str(child.pid) / 'stat'
        try:
            row['birth_raw_stat'] = raw.read_text()
            row['birth_starttime'] = row['birth_raw_stat'].rsplit(')', 1)[1].split()[19]
        except FileNotFoundError:
            row['birth_raw_stat'] = None
            row['birth_capture'] = 'process already exited; direct wait still required'
        write('CHILD-STARTED.json', row)
        term_at = None
        while True:
            pid, status, usage = os.wait4(child.pid, os.WNOHANG)
            if pid:
                break
            elapsed = time.monotonic() - row['started_monotonic']
            if elapsed >= 90 and term_at is None:
                os.killpg(child.pid, signal.SIGTERM)
                term_at = time.monotonic()
                row['timed_out'] = True
            elif term_at is not None and time.monotonic() - term_at > 5:
                os.killpg(child.pid, signal.SIGKILL)
            time.sleep(0.01)
        child.returncode = os.waitstatus_to_exitcode(status)
    try:
        os.killpg(child.pid, 0)
        absent = False
    except ProcessLookupError:
        absent = True
    row.update(returncode=child.returncode, ended_wall=time.time(),
               elapsed=time.monotonic()-row['started_monotonic'], direct_wait=True,
               group_absent=absent, closed_streams=True, CPU_user=usage.ru_utime,
               CPU_system=usage.ru_stime, max_RSS_KiB=usage.ru_maxrss,
               stdout=ref(D/'compiler.stdout'), stderr=ref(D/'compiler.stderr'))
    assert child.returncode == 0 and absent and not row.get('timed_out'), 'first compiler failure'
    row.update(status='PASS_GENUINE_HEADER_PROCESS_VM_ABI_CALLER_COMPILE_ONLY',
               object=ref(Path(plan['argv'][plan['argv'].index('-o')+1])),
               limitations='C public function-pointer type and both node size/alignment static assertions compiled; 22-fact C/Rust comparison and validation functions NOT executed; no VMlock192/runtime/native claim.')
    write('ACTUAL-RECEIPT.json', row)
    print(json.dumps({k: row[k] for k in ['status','pid','returncode','direct_wait','group_absent','elapsed','CPU_user','CPU_system','max_RSS_KiB']}))
except BaseException as error:
    row.update(status='FAIL_STOPPED_NO_RETRY', error=repr(error), failed_wall=time.time())
    write('FIRST-FAILURE.json', row)
    raise
