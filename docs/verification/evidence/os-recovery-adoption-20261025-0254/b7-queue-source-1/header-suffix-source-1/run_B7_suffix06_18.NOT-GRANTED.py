"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One fixed h990 CPU6 suffix: original06..18 only; prefix00..05 retained.
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
B = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-process/b7-current81-six-C-layout-coherence-preparation-1/bounded-default-resource-set-assertion-correction-1')
WORK_CWD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-process/b7-current81-six-C-layout-coherence-preparation-1')
F = D / 'FIXED-SUFFIX-INPUTS.json'
F_SHA = 'f434a036720494567cb9e0b1d6e32e25116c3bbf8bf46309d547755b9b1616e6'
R = D / 'EXACT13-SUFFIX06-18.NOT-GRANTED.json'
R_SHA = 'f705f386d2bc45506c7cce7418945c68a4d3f1544802b6ed69047aa3a7f1b6e3'
M = B / 'EXACT-CURRENT81-B7-PRIVATE-SOURCE-COHORT.json'
M_SHA = '178b5a051b05436e35a9092b5529fa4e29787ce963dd71960118462b87ed341b'
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
assert len(recipe['commands']) == 13 and [c['original_index'] for c in recipe['commands']] == list(range(6, 19)) and manifest['source_count'] == 81
assert len(manifest['staged']) == 180 and len(manifest['consumed_inputs']) == 187
assert WORK_CWD.exists() and WORK_CWD.is_dir()
assert all(command['cwd'] == str(WORK_CWD) for command in recipe['commands'])
spec = importlib.util.spec_from_file_location('accepted_capture', H)
h = importlib.util.module_from_spec(spec)
spec.loader.exec_module(h)
inputs = {row['path']: row for row in authority['rows']}
assert len(inputs) == len(authority['rows']) == authority['count'] == 412
reader = Path(authority['fixed_FD_reader']['path'])
assert pin(reader) == authority['fixed_FD_reader']
namespace = dict(vars(h), FIXED_INPUTS=inputs)
exec(compile(reader.read_bytes(), str(reader), 'exec'), namespace)
read_input = namespace['fixed_input_hashed']
bindings = [read_input(Path(row['path']), row['maximum']) for row in authority['rows']]
for alias in authority['tool_aliases']:
    assert str(Path(alias['invocation_path']).resolve(strict=True)) == alias['resolved']
config_binding = json.loads(Path(authority['generated_include_binding']['path']).read_bytes())
directories = config_binding['finite_generated_include_directories']
selected = {arg[2:] for command in recipe['commands'] for arg in command['argv']
            if arg.startswith('-I' + str(B / 'generated-includes') + '/')}
assert len(directories) == 9
assert selected == {str(B / 'generated-includes' / str(i)) for i in (0, 1, 2, 6, 7, 8)}
assert selected <= {row['staged_include_directory'] for row in directories}
for row in directories:
    directory = Path(row['staged_include_directory'])
    assert sorted(str(path) for path in directory.iterdir()) == sorted(
        item['path'] for item in row['staged_files'])
O = Path(recipe['output_root'])
A = D / 'actual-suffix06-18-capture-1'
assert O == D / 'output-suffix-1'
assert sorted(p.name for p in (D / 'headers').iterdir()) == ['elf.h', 'elfcore.h', 'elfcoregpl.h']
assert recipe['commands'][0]['argv'].count('-I' + str(D / 'headers')) == 1
assert all('-I' + str(D / 'headers') not in c['argv'] for c in recipe['commands'][1:])
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
    for command in recipe['commands']:
        index = command['original_index']
        remaining = 90 - (time.monotonic() - begin)
        remaining_cpu = 60 - h.cpu_used()
        assert remaining > 0 and remaining_cpu > 0, 'shared nineteen-command CPU/wall budget'
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
        if index in {6, 14, 16, 17, 18}:
            if index == 0:
                tokens = [arg for arg in command['argv'] if arg.startswith('--emit=obj=')]
                assert len(tokens) == 1
                target = Path(tokens[0][len('--emit=obj='):])
            else:
                target = Path(command['argv'][command['argv'].index('-o') + 1])
            assert target.parent == O
            durable[str(target)] = h.hashed(target, 32 << 20)
            h.write(step / 'DURABLE-OBJECT-BEFORE-OBSERVERS.json', dict(
                artifact=durable[str(target)], producer_index=index,
                producer_command=command, producer_join=result, source_bindings=bindings))
    assert sorted(p.name for p in (D / 'headers').iterdir()) == ['elf.h', 'elfcore.h', 'elfcoregpl.h']
    for row in bindings + list(durable.values()):
        stable(row)
    for alias in authority['tool_aliases']:
        assert str(Path(alias['invocation_path']).resolve(strict=True)) == alias['resolved']
    for row in directories:
        assert sorted(str(path) for path in Path(row['staged_include_directory']).iterdir()) == sorted(
            item['path'] for item in row['staged_files'])
    assert h.cpu_used() <= 60 and time.monotonic() - begin <= 90
    h.write(A / 'WHOLE-JOIN.json', dict(scope=SCOPE,
        status='PASS_THIRTEEN_SUFFIX_COMPILER_NM_PARTIAL_ASM_COMMANDS_DIAGNOSTIC_ONLY',
        captures=results, original_indices=list(range(6, 19)),
        preserved_prefix=pin(D / 'PREFIX00-05.PRESERVED.json'),
        durable_objects=durable, CPU_seconds=h.cpu_used(),
        wall_seconds=time.monotonic() - begin, CPU6_released=True,
        raw_NM_is_artifact_review_input=True, old18_observer_run=False,
        symbol_or_layout_semantic_acceptance=None, default_image=None, native=None,
        actual_body_or_hardware_execution=False))
    print(json.dumps(dict(status='PASS_THIRTEEN_SUFFIX_DIAGNOSTIC_COMMANDS', commands=13,
                          CPU_seconds=h.cpu_used(), wall_seconds=time.monotonic() - begin,
                          CPU6_released=True)))
except BaseException as error:
    joined = active_capture is None and all(row['direct_child_joined'] and row['group_absent']
        and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None
        for row in results)
    h.write(A / 'FAILURE.STOP.json', dict(scope=__doc__, error=repr(error), captures=results,
        durable_objects=durable, active_capture=active_capture, CPU6_released=joined, STOP_no_retry=True))
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    os.fchdir(previous)
    os.close(previous)
