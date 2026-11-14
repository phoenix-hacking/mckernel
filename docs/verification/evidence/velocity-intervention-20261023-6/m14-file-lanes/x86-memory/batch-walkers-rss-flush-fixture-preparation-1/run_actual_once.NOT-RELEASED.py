"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded six-provider original-C/Rust reference cohort, never native acceptance.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, sys, time

P = Path(__file__).resolve().parent
RECIPE = P / 'BATCH-FIXTURE-FINAL-RECIPE.NOT-EXECUTED.json'
RECIPE_SHA = '50eb9bf22f54bc3ecc08f4278befaef363285eb508df88b17a2309fba1e37805'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(RECIPE) == RECIPE_SHA
r = json.loads(RECIPE.read_bytes())
assert os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}
assert Path(sys.executable).resolve() == Path('/home/holden/anaconda3/bin/python3').resolve() and sys.version_info[:2] == (3,9)
H = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert sha(H) == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
spec = importlib.util.spec_from_file_location('capture', H)
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)
for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(sig, cap.stop)
os.umask(0o077)
os.environ['RUST_MIN_STACK'] = '2097152'
for key, value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:
    resource.setrlimit(key,(value,value))
def sources():
    for row in r['sources'] + r['product_sources'] + r['actual_module_inputs'] + r['actual_header_inputs'] + list(r['reused67_header_pins'].values()) + [r['actual_debug_type_input']]:
        assert sha(Path(row['path'])) == row['sha256'], row
sources()
A = P / 'actual-batch-attempt-1'
A.mkdir(mode=0o700)
host = os.statvfs(P)
scratch = os.statvfs('/home/holden/mckernel-work/scratch')
back = Path('/home/holden/mckernel-work/scratch.ext4').stat()
gap = max(0,back.st_size-back.st_blocks*512)
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
facts = dict(MemAvailable=mem,memory_required=19<<30,HOST_available=host.f_bavail*host.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=(12<<30)+679477248,full_sparse_gap=gap,backing_size=back.st_size,reserves=679477248)
cap.write(A/'HEADROOM.json', facts)
assert mem >= facts['memory_required'] and facts['HOST_available'] >= facts['HOST_required'] and facts['scratch_available'] >= facts['scratch_required'], facts
cap.write(A/'PRELAUNCH-SOURCE-ARGV-PROFILE.json',dict(scope=__doc__,recipe_sha256=RECIPE_SHA,driver_sha256=sha(Path(__file__)),sources=r['sources'],profile=r['profile'],commands=r['commands'],capture_helper_sha256=sha(H),compiler_execution_grant='Root must separately grant this exact frozen cohort; this file is not a release.'))
results, artifacts = [], {}
begin, initial = time.monotonic(), cap.cpu_used()
signal.setitimer(signal.ITIMER_REAL,96)
try:
    for i, item in enumerate(r['commands'],1):
        d = A / ('%02d-' % i + item['label'])
        d.mkdir(mode=0o700)
        command = dict(argv=item['argv'],cwd=item['cwd'],purpose=item['purpose'])
        cap.write(d/'command.json', command)
        remaining = 90-(time.monotonic()-begin)
        remaining_cpu = 60-(cap.cpu_used()-initial)
        assert remaining > 0 and remaining_cpu > 0
        child_cpu = max(1,int(remaining_cpu))
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(child_cpu,child_cpu))
        row = cap.owned_capture(command,d,remaining,limits)
        cap.write(d/'whole-join.json',row)
        results.append(dict(label=item['label'],join=row))
        assert row['returncode'] == 0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None and not row['timed_out'], row
        label = item['label']
        if label.startswith('Rust-'):
            tag = label[5:]
            artifacts['Rust-'+tag] = cap.hashed(P/('fixture-'+tag+'.o'),32<<20)
            cap.write(d/'DURABLE-OBJECT.json',artifacts['Rust-'+tag])
        if label.startswith('GCC-link-'):
            tag = label[9:]
            artifacts['ELF-'+tag] = cap.hashed(P/('fixture-'+tag),32<<20)
            cap.write(d/'DURABLE-ELF.json',artifacts['ELF-'+tag])
        if label in r['expected_stdout']:
            text = (d/'stdout').read_text()
            assert text == r['expected_stdout'][label], repr(text)
        if label.startswith('symbols-'):
            text = (d/'stdout').read_text()
            for name in r['expected_unique_ELF_Rust_T']:
                found = [line.split() for line in text.splitlines() if line.split()[-1:] == [name]]
                assert len(found) == 1 and found[0][-2] == 'T', (name,found)
    sources()
    receipt = dict(scope=__doc__,status='PASS_ACTUAL_SIX_PROVIDER_C_RUST_BATCH_AND_REAL_ABI',recipe_sha256=RECIPE_SHA,driver_sha256=sha(Path(__file__)),results=results,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,artifacts=artifacts,actual_provider_pairs=r['expected_actual_pairs'],on_off_total_pairs=937,actual_tested_ports=['walkL1','walkL2','walkL3','RSS','memobjRSS','memobjFlush'],accounting_and_memobj_dispatch_bodies='Actual existing Rust modules; only two unrelated export names are fixture-namespaced, with original bodies preserved.',lower_C_provider_qualification=r['remaining_C_providers'],prior_L1_L2_suites_repeated=False,canonical_currentimage_changes=0,full78_GCC14_default_partial_native=None,CPU6_released=True)
    cap.write(P/'ACTUAL-SIX-PROVIDER-BATCH-RECEIPT.json',receipt)
    print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],CPU_seconds=receipt['CPU_seconds'],actual_pairs=937,CPU6_released=True)))
except BaseException as error:
    cap.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(error),completed_commands=len(results),results=results,artifacts_durable_before_failure=artifacts,CPU6_released=True,no_retry=True))
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
