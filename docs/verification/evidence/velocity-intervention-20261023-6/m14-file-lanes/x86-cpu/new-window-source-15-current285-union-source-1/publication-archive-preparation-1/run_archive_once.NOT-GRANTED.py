"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed h990 CPU6 finite archive/readback command; no compiler/link/deletion.
Diagnostic output only; no old18 observer or layout/native acceptance is inferred.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import math
import os
import resource
import signal
import sys
import time

D = Path(__file__).resolve().parent
B = D
WORK_CWD = D
F = D / 'EXACT-FIXED-INPUT-FD-AUTHORITY.json'
F_SHA = 'f367c96cd08265541859c3fb4d07af75484bfe5319aac3761c7343dd47519fb8'
R = D / 'EXACT-ARCHIVE-COMMAND.NOT-GRANTED.json'
R_SHA = '14b29fd73f9bb48882185b5a506fa338e4cbda64c06c9749f529d8fb477560e7'
M = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-15-current285-union-source-1/FROZEN-CURRENT285-SOURCE-AND-HEADER-BINDINGS.json')
M_SHA = '4344a6ac73850b3faabc8fef908358f52bbf55591ad5991ad217a8fe4632af73'
H = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
H_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
SCOPE = __doc__.splitlines()[0]


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def stable(row):
    current = Path(row['path']).stat()
    names = dict(device='st_dev', inode='st_ino', size='st_size', uid='st_uid',
                 gid='st_gid', nlink='st_nlink', mtime_ns='st_mtime_ns', ctime_ns='st_ctime_ns')
    assert all(row[key] == getattr(current, field) for key, field in names.items()), row['path']


begin = time.monotonic()
assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
assert Path(sys.executable).resolve() == Path('/home/holden/anaconda3/bin/python3').resolve()
assert sys.version_info[:2] == (3, 9)
assert pin(H)['sha256'] == H_SHA and pin(F)['sha256'] == F_SHA
assert pin(R)['sha256'] == R_SHA and pin(M)['sha256'] == M_SHA
ready_path = D / 'EXECUTABLE-READY.NOT-GRANTED.json'
ready = json.loads(ready_path.read_bytes())
grant = json.loads((D / 'ROOT-GRANT.json').read_bytes())
assert grant['scope'] == SCOPE and grant['CPU'] == 6 and grant['ordinary_jobs'] == 1
assert grant['ready_sha256'] == pin(ready_path)['sha256']
assert ready['driver'] == pin(Path(__file__))
recipe = json.loads(R.read_bytes())
manifest = json.loads(M.read_bytes())
authority = json.loads(F.read_bytes())
assert len(recipe['commands']) == 1 and manifest['selected_Rust_source_count'] == 81
assert len(manifest['source_rows']) == 85
assert WORK_CWD.exists() and WORK_CWD.is_dir()
assert all(command['cwd'] == str(WORK_CWD) for command in recipe['commands'])
spec = importlib.util.spec_from_file_location('accepted_capture', H)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
inputs = {row['path']: row for row in authority['rows']}
assert len(inputs) == len(authority['rows']) == authority['count']
reader = Path(authority['fixed_FD_reader']['path'])
assert pin(reader) == authority['fixed_FD_reader']
namespace = dict(vars(h), FIXED_INPUTS=inputs)
exec(compile(reader.read_bytes(), str(reader), 'exec'), namespace)
read_input = namespace['fixed_input_hashed']
bindings = [read_input(Path(row['path']), row['maximum']) for row in authority['rows']]
for alias in authority['tool_aliases']:
    assert str(Path(alias['invocation_path']).resolve(strict=True)) == alias['resolved']
def check_header_namespaces():
    def raising(error):
        raise error
    for row in manifest['header_namespaces']:
        root = Path(row['path'])
        if row['state'] == 'ABSENT_EXACT_ACCEPTED_ARGV':
            assert not os.path.lexists(root), row['path']
            continue
        directories, files, links = [], [], []
        for current, children, names in os.walk(root, followlinks=False, onerror=raising):
            directories.extend(str((Path(current) / n).relative_to(root)) for n in children)
            for name in children + names:
                path = Path(current) / name
                if path.is_symlink():
                    links.append(dict(relative=str(path.relative_to(root)), target=os.readlink(path)))
            files.extend(str((Path(current) / n).relative_to(root)) for n in names)
        assert sorted(directories) == row['directories'], row['path']
        assert sorted(files) == sorted(r['relative'] for r in row['files']), row['path']
        assert sorted(links, key=lambda r: r['relative']) == sorted(row['symlinks'], key=lambda r: r['relative']), row['path']

check_header_namespaces()
O = D / 'output-1'
A = D / 'actual-archive-attempt-1'
assert not os.path.lexists(O) and not os.path.lexists(A)
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines()
               if line.startswith('MemAvailable:'))) * 1024
host = os.statvfs(D)
scratch = os.statvfs('/home/holden/mckernel-work/scratch')
back = Path('/home/holden/mckernel-work/scratch.ext4').stat()
gap = max(0, back.st_size - back.st_blocks * 512)
facts = dict(MemAvailable=mem, MemAvailable_required=25501368320,
             HOST_available=host.f_bavail * host.f_frsize,
             HOST_required=(16 << 30) + gap + (128 << 20) + 679477248,
             scratch_available=scratch.f_bavail * scratch.f_frsize,
             scratch_required=(12 << 30) + 679477248,
             full_sparse_gap=gap, backing_size=back.st_size, reserves=679477248)
assert mem >= facts['MemAvailable_required'] and back.st_size == 110 << 30, facts
assert facts['HOST_available'] >= facts['HOST_required'], facts
assert facts['scratch_available'] >= facts['scratch_required'], facts
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(sig, h.stop)
for key, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60),
                   (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                   (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)):
    resource.setrlimit(key, (value, value))
os.environ['RUST_MIN_STACK'] = '2097152'
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
os.umask(0o077)
O.mkdir(mode=0o700)
A.mkdir(mode=0o700)
h.write(A / 'FRESH-ADMISSION-AND-SOURCE-BINDING.json', dict(scope=__doc__, facts=facts,
        recipe=pin(R), manifest=pin(M), authority=pin(F), bindings=bindings,
        profile=recipe['profile'], grant=pin(D / 'ROOT-GRANT.json'), old18_observer_run=False))
results, durable = [], {}
active_capture = None
previous = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
signal.setitimer(signal.ITIMER_REAL, 96)
try:
    os.chdir(WORK_CWD)
    for index, command in enumerate(recipe['commands']):
        remaining = 90 - (time.monotonic() - begin)
        remaining_cpu = 60 - h.cpu_used()
        assert remaining > 0 and remaining_cpu > 0, 'shared thirteen-command CPU/wall budget'
        step = A / ('%02d' % index)
        step.mkdir(mode=0o700)
        h.write(step / 'command.json', command)

        def limits():
            limit = max(1, int(math.ceil(remaining_cpu)))
            resource.setrlimit(resource.RLIMIT_CPU, (limit, limit))

        active_capture = str(step)
        assert Path.cwd() == WORK_CWD
        result = h.owned_capture(command, step, remaining, limits)
        h.write(step / 'WHOLE-JOIN.json', result)
        results.append(result)
        active_capture = None
        assert result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent']
        assert result['closed_streams'] and not result['timed_out']
        assert result['error'] is None and result['retirement_error'] is None
        assert h.cpu_used() <= 60 and time.monotonic() - begin <= 90
        if index in set():
            if any(arg.startswith('--emit=') for arg in command['argv']):
                tokens = [arg for arg in command['argv'] if arg.startswith('--emit=')]
                assert len(tokens) == 1
                mode, separator, filename = tokens[0][len('--emit='):].partition('=')
                assert separator and mode in {'obj', 'metadata'}
                target = Path(filename)
            else:
                target = Path(command['argv'][command['argv'].index('-o') + 1])
            assert target.parent == O
            durable[str(target)] = h.hashed(target, 32 << 20)
            h.write(step / 'DURABLE-OBJECT-BEFORE-OBSERVERS.json', dict(
                artifact=durable[str(target)], producer_index=index,
                producer_command=command, producer_join=result, source_bindings=bindings))
    check_header_namespaces()
    for row in bindings + list(durable.values()):
        stable(row)
    for alias in authority['tool_aliases']:
        assert str(Path(alias['invocation_path']).resolve(strict=True)) == alias['resolved']
    assert h.cpu_used() <= 60 and time.monotonic() - begin <= 90
    h.write(A / 'WHOLE-JOIN.json', dict(scope=SCOPE,
        status='PASS_ONE_FINITE_CURRENT285_ARCHIVE_READBACK_COMMAND',
        captures=results, current_source_cohort=pin(M),
        durable_objects=durable, CPU_seconds=h.cpu_used(),
        wall_seconds=time.monotonic() - begin, CPU6_released=True,
        raw_NM_is_artifact_review_input=True, old18_observer_run=False,
        symbol_or_layout_semantic_acceptance=None, default_image=None, native=None,
        actual_body_or_hardware_execution=False))
    print(json.dumps(dict(status='PASS_ONE_FINITE_CURRENT285_ARCHIVE_READBACK_COMMAND', commands=1,
                          CPU_seconds=h.cpu_used(), wall_seconds=time.monotonic() - begin,
                          CPU6_released=True)))
except BaseException as error:
    joined = active_capture is None and all(row['direct_child_joined'] and row['group_absent']
        and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None
        for row in results)
    h.write(A / 'FAILURE.STOP.json', dict(scope=__doc__, error=repr(error), captures=results,
        durable_objects=durable, active_capture=active_capture, CPU6_released=joined, CPU_seconds=h.cpu_used(), wall_seconds=time.monotonic()-begin, peak_RSS_measured=False, STOP_no_retry=True))
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    os.fchdir(previous)
    os.close(previous)
