"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite nine-command Root-granted HOST adapter batch; reuse reviewed admission/profile.
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
BASE = D.parent
ROOT = Path('/home/holden/mckernel')
results = []
current = None

def ref(p):
    p = Path(p)
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def write(name, data):
    (D / name).write_text(json.dumps(data, indent=2) + '\n')

def verify(rows):
    for row in rows:
        assert ref(row['path']) == row, row['path']

try:
    assert os.getuid() == os.geteuid() == 1000
    grant_path = BASE / 'ROOT-ORDINARY-CPU6-GRANT.json'
    assert ref(grant_path)['sha256'] == '1539a95418f1c4d4bcb3dda95c23521f13392f6ec45fdc07e81fb547922a53bf'
    grant = json.loads(grant_path.read_text())
    verify(grant['plans'])
    assert ref(BASE/'READY.json')['sha256'] == grant['source_ready_RECEIPT']
    plans = [json.loads(Path(r['path']).read_text()) for r in grant['plans']]
    assert len(plans) == 3 and sum(len(p['commands']) for p in plans) == 9
    for plan in plans:
        verify(plan['inputs'] + plan['tools'] + [plan['genuine_configuration']])
        binding = json.loads((Path(plan['cwd'])/'SOURCE-BINDINGS.json').read_text())
        verify(binding['canonical_before'] + [binding['provider_source'], binding['selected_cursor'], binding['selected_object']])
        assert not Path(plan['fresh_output']).exists()
    config = json.loads(Path(plans[0]['genuine_configuration']['path']).read_text())
    generated_root = Path(config['generated_config']['path']).parent
    for parent in Path(config['generated_flags']['path']).parents:
        if parent.name == 'build':
            generated_root = parent
            break
    supervisor = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-selected-residual-implementation-20261026-1/next-process-vm-selected-1/next-prctl-getter-selected-1/actual-host-getter-1/reviewed-account-supervisor-correction-1/run_sealed.py')
    assert supervisor.is_file()
    assert ref(supervisor)['sha256'] == 'e8b84de39128433542b213fc3a374dd50d3e12f232bd397dddaa24859349a805'
    sys.path.insert(0, str(supervisor.parent))
    spec = importlib.util.spec_from_file_location('reviewed_supervisor', supervisor)
    accepted = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(accepted)
    index = 0
    for plan in plans:
        # Fresh output only; never remove or reuse an earlier attempt.
        Path(plan['fresh_output']).mkdir(mode=0o700)
        for local_index, argv in enumerate(plan['commands']):
            verify(plan['inputs'] + plan['tools'] + [plan['genuine_configuration']])
            headers = []
            for r in config['dependency_inputs']:
                q = r['compiler_path']
                if q.endswith('/syscall.c'):
                    continue
                if q.startswith('/src/'):
                    path = ROOT / q.removeprefix('/src/')
                    expected = r['expected_source_sha256']
                elif q.startswith('/work/output/build/'):
                    path = generated_root / q.removeprefix('/work/output/build/')
                    expected = r['actual']['sha256']
                else:
                    path = Path(q)
                    expected = r['expected_source_sha256']
                observed = ref(path)
                assert observed['sha256'] == expected, str(path)
                headers.append(observed)
            verify([config['generated_config']])
            admission = accepted.admission()
            capacity = {str(p): os.statvfs(p).f_bavail * os.statvfs(p).f_frsize for p in
                        [ROOT, Path('/home/holden/mckernel-work/scratch')]}
            assert capacity[str(ROOT)] >= 8 * 2**30
            assert capacity['/home/holden/mckernel-work/scratch'] >= 12 * 2**30
            wrapper = ['/usr/bin/taskset', '-c', '6', '/usr/bin/prlimit', '--as=2147483648',
                       '--cpu=60', '--fsize=67108864', '--core=0', '--'] + argv
            current = dict(index=index, local_index=local_index, symbol=plan['symbol'],
                argv=argv, actual_argv=wrapper, admission=admission, purpose=plan['purpose'],
                authenticated_headers=headers, capacity=capacity, uid=os.getuid(), child_started=False,
                environment={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'},
                started_wall=time.time(), started_monotonic=time.monotonic())
            write(str(index)+'.PRE-COMMAND.json', current)
            with (D/(str(index)+'.stdout')).open('xb') as out, (D/(str(index)+'.stderr')).open('xb') as err:
                child = subprocess.Popen(wrapper, cwd=plan['cwd'], stdin=subprocess.DEVNULL,
                    stdout=out, stderr=err, env=current['environment'], start_new_session=True, close_fds=True)
                current.update(child_started=True, pid=child.pid)
                try:
                    current['birth_raw_stat'] = (Path('/proc')/str(child.pid)/'stat').read_text()
                    current['birth_starttime'] = current['birth_raw_stat'].rsplit(')', 1)[1].split()[19]
                except FileNotFoundError:
                    current['birth_raw_stat'] = None
                    current['birth_capture'] = 'already exited; direct wait still required'
                write(str(index)+'.CHILD-STARTED.json', current)
                term_at = None
                while True:
                    pid, status, usage = os.wait4(child.pid, os.WNOHANG)
                    if pid:
                        break
                    elapsed = time.monotonic() - current['started_monotonic']
                    if elapsed >= 90 and term_at is None:
                        os.killpg(child.pid, signal.SIGTERM)
                        term_at = time.monotonic()
                        current['timed_out'] = True
                    elif term_at is not None and time.monotonic() - term_at > 5:
                        os.killpg(child.pid, signal.SIGKILL)
                    time.sleep(0.01)
                child.returncode = os.waitstatus_to_exitcode(status)
            try:
                os.killpg(child.pid, 0)
                absent = False
            except ProcessLookupError:
                absent = True
            current.update(returncode=child.returncode, ended_wall=time.time(),
                elapsed=time.monotonic()-current['started_monotonic'], direct_wait=True,
                group_absent=absent, closed_streams=True, CPU_user=usage.ru_utime,
                CPU_system=usage.ru_stime, max_RSS_KiB=usage.ru_maxrss,
                stdout=ref(D/(str(index)+'.stdout')), stderr=ref(D/(str(index)+'.stderr')))
            results.append(current)
            write('RESULTS.json', dict(status='RUNNING', grant=ref(grant_path), results=results))
            assert child.returncode == 0 and absent and not current.get('timed_out'), 'first command failure'
            if local_index == 2:
                assert (D/(str(index)+'.stdout')).read_text() == plan['expected_stdout']
            index += 1
    result = dict(status='PASS_F06_SELECTED26EB_THREE_ADAPTERS_HOST490', scope=__doc__,
                  grant=ref(grant_path), plans=grant['plans'], results=results,
                  source_composition='PASS before output creation', CPU6_free=True,
                  limitations=['real usercopy/fault fixups', 'actual forwarding/context lifetime',
                               'canonical/default/native selection'],
                  actual_scope='175 copy-to +175 copy-from +140 forward C/Rust parity pairs at inert provider boundaries only.')
    write('RESULTS.json', result)
    print(json.dumps(dict(status=result['status'], commands=len(results), CPU6_free=True,
        CPU_seconds=sum(r['CPU_user']+r['CPU_system'] for r in results),
        wall_seconds=sum(r['elapsed'] for r in results), max_RSS_KiB=max(r['max_RSS_KiB'] for r in results))))
except BaseException as error:
    write('FIRST-FAILURE.json', dict(status='FAIL_STOPPED_NO_RETRY', scope=__doc__,
        error=repr(error), failed_wall=time.time(), current=current, results=results))
    raise
