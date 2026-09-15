from pathlib import Path
from datetime import datetime, timezone
import hashlib, importlib.util, json, os, shlex, shutil

assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
repo, work = Path('/workspace'), Path('/work')
out = work / 'stability-linux-collector-build-20260915-2'
out.mkdir(); (out / 'tmp').mkdir(); (out / 'source/linux-sealed-v1').mkdir(parents=True)
record = dict(schema_version=1, status='RUNNING', started_utc=datetime.now(timezone.utc).isoformat(),
              commands=[], inputs=[], compiler_dependencies=[], compiled_outputs=[], loader_dependencies=[],
              application_acceptance=False, backend_enabled=False, guest_execution=False,
              root_positive_execution=False,
              scope='Pinned Linux collector rebuild after retained close_range/EPERM root failure; SHA9 and builder rejection only')

def identity(path):
    data = path.read_bytes()
    return dict(path=str(path), size=len(data), sha256=hashlib.sha256(data).hexdigest())

def save():
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')

try:
    assert shutil.disk_usage(work).free > 3 * 1024**3
    helper = Path(__file__)
    shutil.copyfile(helper, out / 'helper.py')
    record['helper'] = identity(helper)
    source = repo / 'scripts/tests/fixtures/application-collector-v1'
    names = ['collector.c', 'contract.md', 'fixture.c', 'root-profile.md', 'root_inside.py',
             'root_profile.py', 'run_collector_tests.py', 'sha256.c', 'sha256.h',
             'sha256_harness.c', 'tests.md']
    for name in names:
        src = source / 'linux-sealed-v1' / name
        dst = out / 'source/linux-sealed-v1' / name
        shutil.copyfile(src, dst)
        record['inputs'].append(dict(original=identity(src), retained=identity(dst)))
    for name in ('request.c', 'request.h'):
        src = source / name; dst = out / 'source' / name
        shutil.copyfile(src, dst)
        record['inputs'].append(dict(original=identity(src), retained=identity(dst)))
    src = repo / 'scripts/application-tests/supervisor.py'
    shutil.copyfile(src, out / 'supervisor.py')
    record['inputs'].append(dict(original=identity(src), retained=identity(out / 'supervisor.py')))
    expected = {
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/collector.c': '09a63a343fa8cc9f511a26693371f5ba4f55ac5ca56fcb47abdc44759830cf1f',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/contract.md': '194813f9cd1e49de63afb611c989c8574f3ecdd87c18ea5f634a7d205a88d7f3',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/fixture.c': 'd2c33206cb1dc938b31ef83c5827f3aae2ca4e78740178d0df2f221015bdfc6d',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root-profile.md': '68350568cca75248a85a3e43cdcf1ca85e1197dff24713aa4fc01128c47ddb52',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root_inside.py': '1eab68ce627271bb97febfd51c3455e5267280009ad0f1b6249ae92f5d568e19',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/root_profile.py': 'a65d104d76ec7ce3918d667ac02b1cea92c1a80cae321360b01c12190f2f6dd6',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/run_collector_tests.py': '691aee973f9ea5e79cdf7766b87c69e0d5d5a01ff334b8674cd099c776125bb5',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256.c': '8a8a93d4e7f7d1562f044671a673b48e96dc152ad65bd294f082b7b20b4a39e1',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256.h': '52cfafeecb6c411f7df956e6d444068185e17177bd8f21ed1270a2d06ce50e97',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/sha256_harness.c': 'cb5b4634f38be0121254f0ac7080ed134e134d7ada7cbddd4b45315362bd4ce9',
        'scripts/tests/fixtures/application-collector-v1/linux-sealed-v1/tests.md': '8d5249cef4565120ffeaad2949a011f32ac2a405b3b95d61a02e7e528236dacc',
        'scripts/tests/fixtures/application-collector-v1/request.c': 'c072005948e479e6f50d3f647bf649301741365d7c034c72d3047df3f85cc3ab',
        'scripts/tests/fixtures/application-collector-v1/request.h': 'e767e217104d3b89b0b6d0f74e37f8150600c0b078d40799e75d14f3ede8d00e',
        'scripts/application-tests/supervisor.py': '8b8700175e6673c3a6b652d4a93bd18b56def83dfa3ac4ec821d4ae6c554e873'}
    for row in record['inputs']:
        relative = str(Path(row['original']['path']).relative_to(repo))
        assert row['original']['sha256'] == expected.pop(relative)
        assert row['retained']['size'] == row['original']['size']
        assert row['retained']['sha256'] == row['original']['sha256']
    assert not expected
    spec = importlib.util.spec_from_file_location('collector_rebuild_supervisor', out / 'supervisor.py')
    supervisor = importlib.util.module_from_spec(spec); spec.loader.exec_module(supervisor)
    env = dict(PATH='/usr/local/bin:/usr/bin:/bin', LANG='C', LC_ALL='C', TZ='UTC', TMPDIR=str(out / 'tmp'))
    def run(label, argv, timeout=120, cap=8*1024**2):
        if not Path(argv[0]).is_absolute(): argv[0] = shutil.which(argv[0], path=env['PATH'])
        record['phase'] = label; save(); print('RUN', label, flush=True)
        result = supervisor.run_supervised(argv, cwd=str(out), env=env,
            attempt_dir=str(out / (label + '-collection')), timeout_seconds=timeout,
            cleanup_timeout_seconds=15, stdout_limit_bytes=cap, stderr_limit_bytes=cap)
        record['commands'].append(dict(label=label, argv=argv, environment=env, collection=result)); save()
        assert result['status'] == 'COMPLETED' and result['raw_wait_status'] == 0 and result['cleanup_complete'], (label, result)
        return (out / (label + '-collection') / 'stdout.bin').read_text()
    run('compiler-version', ['gcc', '--version'])
    units = {'request': out / 'source/request.c'}
    for name in ('sha256', 'collector', 'fixture', 'sha256_harness'):
        units[name] = out / 'source/linux-sealed-v1' / (name + '.c')
    for name, src in units.items():
        run('compile-' + name, ['gcc', '-std=c11', '-D_GNU_SOURCE', '-O2', '-g', '-Wall', '-Wextra', '-Werror',
            '-fno-pie', '-MD', '-MF', str(out / (name + '.d')), '-c', str(src), '-o', str(out / (name + '.o'))])
    executables = {'linux-collector':['request','sha256','collector'], 'fixture':['fixture'], 'sha256-harness':['sha256','sha256_harness']}
    for name, objects in executables.items():
        run('link-' + name, ['gcc', '-no-pie'] + [str(out / (obj + '.o')) for obj in objects] +
            ['-Wl,-Map=' + str(out / (name + '.map')), '-o', str(out / name)])
        run('elf-' + name, ['readelf', '-h', '-l', '-d', str(out / name)])
        run('disassembly-' + name, ['objdump', '-d', str(out / name)])
        for line in run('loader-' + name, ['ldd', str(out / name)]).splitlines():
            for part in line.split():
                if part.startswith('/') and Path(part).is_file():
                    observed = identity(Path(part))
                    if observed not in record['loader_dependencies']: record['loader_dependencies'].append(observed)
    for name in units:
        text = (out / (name + '.d')).read_text().split(':', 1)[1].replace('\\\n', ' ')
        for item in shlex.split(text):
            dep = Path(item)
            if not dep.is_absolute(): dep = out / dep
            dep = dep.resolve(); row = identity(dep)
            if any(old['original'] == row for old in record['compiler_dependencies']): continue
            dst = out / 'compiler-inputs' / str(dep).lstrip('/')
            dst.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(dep, dst)
            record['compiler_dependencies'].append(dict(original=row, retained=identity(dst)))
    record['compiled_outputs'] = [identity(out / (name + suffix)) for name in units for suffix in ('.o', '.d')]
    record['compiled_outputs'] += [identity(out / (name + suffix)) for name in executables for suffix in ('', '.map')]
    run('sha9', [str(out / 'sha256-harness')], timeout=10, cap=65536)
    expected_sha = b'PASS empty\nPASS abc\nPASS multi-56\nPASS boundary-55\nPASS boundary-56\nPASS boundary-63\nPASS boundary-64\nPASS boundary-65\nPASS rejected-update-preserves-state\n'
    assert (out / 'sha9-collection/stdout.bin').read_bytes() == expected_sha
    assert (out / 'sha9-collection/stderr.bin').read_bytes() == b''
    run('builder-negative', ['/usr/bin/python3', '-B', str(out / 'source/linux-sealed-v1/run_collector_tests.py'),
        '--collector', str(out / 'linux-collector'), '--fixture', str(out / 'fixture'),
        '--supervisor', str(out / 'supervisor.py'), '--attempt-root', str(out / 'builder-negative'), '--builder-only'], timeout=60)
    assert (out / 'builder-negative-collection/stdout.bin').read_bytes() == ('PASS builder-identity\nRETAINED ' + str(out / 'builder-negative') + '\n').encode()
    assert (out / 'builder-negative-collection/stderr.bin').read_bytes() == b''
    driver = json.loads((out / 'builder-negative/result.json').read_text())
    assert driver['status'] == 'PASS_INFRASTRUCTURE_ONLY' and len(driver['cases']) == 1 and driver['uid'] == driver['euid'] == 1000
    for row in record['inputs'] + record['compiler_dependencies']:
        assert identity(Path(row['original']['path'])) == row['original']
        assert identity(Path(row['retained']['path'])) == row['retained']
    for row in record['compiled_outputs'] + record['loader_dependencies']:
        assert identity(Path(row['path'])) == row
    record.update(status='PASS_LINUX_COLLECTOR_REBUILD_SHA9_BUILDER_NEGATIVE_ONLY', sha_cases=9, builder_cases=1,
                  clean_launch_requirement='root execution must bind close_fds, empty pass_fds and nofile=4096:4096')
except BaseException as error:
    record.update(status='FAIL', error_type=type(error).__name__, error=str(error)); raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat(); save(); print(record['status'], out, flush=True)
