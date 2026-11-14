"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Sole bounded fixture-header correction, retained Rust object, failed02 plus pending four commands, never native acceptance.
"""
from pathlib import Path
import hashlib, importlib.util, json, os, resource, signal, sys, time

P = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/set-page-split-provider-fixture-preparation-1')
RECIPE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/set-page-split-provider-fixture-preparation-1/observer-header-inclusion-correction-1/EXACT-FAILED02-PLUS-PENDING4.NOT-RELEASED.json')
RECIPE_SHA = 'fa7c48d74379fcced2f5513ba4307613285487ac27a7ff638213d6816647e49e'
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
for key, value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0),(resource.RLIMIT_STACK,2<<20)]:
    resource.setrlimit(key,(value,value))
def sources():
    for row in r['sources'] + list(r['reused67_header_pins'].values()):
        assert sha(Path(row['path'])) == row['sha256'], row
sources()
# Reuse the original durable producer authority and stat identity, no object read.
retained = r['retained_Rust_object']['object']
retained_stat = Path(retained['path']).lstat()
for key, value in [('device',retained_stat.st_dev),('inode',retained_stat.st_ino),('size',retained_stat.st_size),('mtime_ns',retained_stat.st_mtime_ns),('ctime_ns',retained_stat.st_ctime_ns),('uid',retained_stat.st_uid),('gid',retained_stat.st_gid),('nlink',retained_stat.st_nlink)]:
    assert retained[key] == value, (key, retained['path'])
assert not Path(retained['path']).is_symlink()
prior_join = json.loads(Path(r['retained_Rust_object']['producer_join']['path']).read_bytes())
assert prior_join['returncode'] == 0 and prior_join['direct_child_joined'] and prior_join['group_absent'] and prior_join['closed_streams']
# h990 does not consume command['cwd']; bind the actual parent directory.
assert P == Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/set-page-split-provider-fixture-preparation-1')
assert P.resolve() == P and all(Path(item['cwd']) == P for item in r['commands'])
output_absence = {}
for name in ('fixture-set-split',):
    assert not os.path.lexists(P / name), name
    output_absence[name] = 'ABSENT'
A = P / 'actual-set-split-attempt-2-header-inclusion-correction-1'
A.mkdir(mode=0o700)
host = os.statvfs(P)
scratch = os.statvfs('/home/holden/mckernel-work/scratch')
back = Path('/home/holden/mckernel-work/scratch.ext4').stat()
gap = max(0,back.st_size-back.st_blocks*512)
mem = int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))) * 1024
facts = dict(MemAvailable=mem,memory_required=19<<30,HOST_available=host.f_bavail*host.f_frsize,HOST_required=(16<<30)+gap+(128<<20)+679477248,scratch_available=scratch.f_bavail*scratch.f_frsize,scratch_required=(12<<30)+679477248,full_sparse_gap=gap,backing_size=back.st_size,reserves=679477248)
cap.write(A/'HEADROOM.json', facts)
cap.write(A/'REUSED-RUST-STAT-AND-PRODUCER.json',dict(retained=retained,producer=r['retained_Rust_object'],original_digest_authority_only=True,object_rehashed=False,Rust_recompiled=False))
assert mem >= facts['memory_required'] and facts['HOST_available'] >= facts['HOST_required'] and facts['scratch_available'] >= facts['scratch_required'], facts
cap.write(A/'PRELAUNCH-SOURCE-ARGV-PROFILE.json',dict(scope=__doc__,recipe_sha256=RECIPE_SHA,driver_sha256=sha(Path(__file__)),sources=r['sources'],profile=r['profile'],commands=r['commands'],capture_helper_sha256=sha(H),compiler_execution_grant='Root must separately grant this exact frozen cohort; this file is not a release.'))
results, artifacts = [], {'Rust-set-split': retained}
previous_cwd_fd = os.open('.', os.O_RDONLY | os.O_DIRECTORY)
all_children_joined = True
os.chdir(P)
assert Path.cwd() == P
cap.write(A/'ACTUAL-CWD-AND-OUTPUT-ABSENCE.json', dict(cwd=str(Path.cwd()),device=P.stat().st_dev,inode=P.stat().st_ino,outputs=output_absence,OS_stack=resource.getrlimit(resource.RLIMIT_STACK),RUST_MIN_STACK=os.environ['RUST_MIN_STACK']))
begin, initial = time.monotonic(), cap.cpu_used()
signal.setitimer(signal.ITIMER_REAL,96)
try:
    for i, item in enumerate(r['commands'],2):
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
        all_children_joined = False
        row = cap.owned_capture(command,d,remaining,limits)
        all_children_joined = row['direct_child_joined'] and row['group_absent'] and row['closed_streams']
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
    receipt = dict(scope=__doc__,status='PASS_ACTUAL_SET_SPLIT_498_PAIRS_AND_REAL_ABI',recipe_sha256=RECIPE_SHA,driver_sha256=sha(Path(__file__)),results=results,seconds=time.monotonic()-begin,CPU_seconds=cap.cpu_used()-initial,artifacts=artifacts,actual_provider_pairs=r['expected_actual_pairs'],set_split_pairs=498,actual_tested_ports=['x86_pt_set_page_bridge', 'x86_split_alloc_new_pt_bridge', 'x86_split_page_map_bridge', 'x86_split_page_unmap_bridge'],controlled_external_endpoints=True,qualification=r['qualification'],prior_L1_L2_suites_repeated=False,canonical_currentimage_changes=0,full78_GCC14_default_partial_native=None,CPU6_released=True,reused_Rust_stat_and_producer=r['retained_Rust_object'],Rust_recompile=False,Rust_object_rehash=False,sole_bounded_header_correction=True)
    cap.write(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-memory/set-page-split-provider-fixture-preparation-1/observer-header-inclusion-correction-1/ACTUAL-SET-SPLIT-BOUNDED-HEADER-CORRECTION-RECEIPT.json'),receipt)
    print(json.dumps(dict(status=receipt['status'],seconds=receipt['seconds'],CPU_seconds=receipt['CPU_seconds'],actual_pairs=498,CPU6_released=True)))
except BaseException as error:
    cap.write(A/'FAILURE.STOP.json',dict(scope=__doc__,error=repr(error),completed_commands=len(results),results=results,artifacts_durable_before_failure=artifacts,CPU6_released=True,no_retry=True))
    raise
finally:
    signal.setitimer(signal.ITIMER_REAL,0)
    # Never restore a directory while a child ownership interval is unclosed.
    if all_children_joined:
        os.fchdir(previous_cwd_fd)
        os.close(previous_cwd_fd)
