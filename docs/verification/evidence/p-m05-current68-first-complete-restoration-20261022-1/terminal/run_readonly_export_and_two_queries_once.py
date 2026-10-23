"""Fixed M05 read-only export and two queries; accepted capture implementation unchanged."""
from pathlib import Path
import fcntl, hashlib, importlib.util, json, os, resource, signal, stat, sys, time
T = Path(__file__).resolve().parent
PINS = [{'path': '/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py', 'sha256': '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8', 'bytes': 14753}, {'path': '/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py', 'sha256': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'bytes': 51420}, {'path': '/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/abi2-boothelper-substitution-1/actual-successful-selfexec-retirement-1/EXACT-CURRENT-SDK-IMAGE-RECORD-PATHS.json', 'sha256': '71f1b057454131abf59fd82b7e58342ea3966f36326e7d430e2a3c7f0194c81b', 'bytes': 2415}, {'path': '/home/holden/mckernel-work/host-preparation/p-m05-current68-second-stop-binding-20261022-1/consumer-successor-1/runtime-current68-filebound-successor-1/logging-revision-1/terminal-preparation-1/ROOT-READONLY-OWNER-EXPORT-PROPOSAL.json', 'sha256': '16ecc5560355aec09db2ddc78687966e8b3318c3946593808d553f9f8b537da7', 'bytes': 2852}, {'path': '/home/holden/mckernel-work/host-preparation/p-m05-current68-second-stop-binding-20261022-1/consumer-successor-1/runtime-current68-filebound-successor-1/logging-revision-1/terminal-preparation-1/EXACT-CURRENT-NAME-LABEL-READONLY-QUERIES.json', 'sha256': 'dffef1b88d36bccce83c489ccf39751985c365e7474d3a90755f9fb1f9d82416', 'bytes': 2951}, {'path': '/home/holden/mckernel-work/host-preparation/p-m05-current68-second-stop-binding-20261022-1/consumer-successor-1/runtime-current68-filebound-successor-1/logging-revision-1/terminal-preparation-1/readonly_export_exact_owner.py', 'sha256': '42eb1663f75705401f1c6062a94bd3f477dd1f4121944d689b472dc5da0670b7', 'bytes': 1638}]
for row in PINS:
    assert hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256'], 'source/data pin'
module_path = Path(PINS[0]['path'])
spec = importlib.util.spec_from_file_location('accepted_m05_readonly_capture', module_path)
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
assert str(capture.CENSUS_SOURCE) == PINS[1]['path'] and capture.CENSUS_SHA == PINS[1]['sha256'], 'actual census binding'
assert os.sched_getaffinity(0) == {7}, 'CPU7 only'
assert resource.getrlimit(resource.RLIMIT_AS) == (2147483648, 2147483648), '2GiBAS'
assert resource.getrlimit(resource.RLIMIT_CPU) == (60,60), 'parentCPU60'
for sig in capture.STOP_SIGNALS:
    signal.signal(sig, capture.stop)
export = json.loads((T/'ROOT-READONLY-OWNER-EXPORT-PROPOSAL.json').read_text())
queries = json.loads((T/'EXACT-CURRENT-NAME-LABEL-READONLY-QUERIES.json').read_text())
O = T/'actual-readonly-serial-1'
O.mkdir(mode=0o700)
started = time.monotonic()
records = []
lock = None
error = None
try:
    lock = os.open('/run/lock/mckernel-development.lock',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
    info = os.fstat(lock)
    assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1 and (info.st_dev,info.st_ino)==(27,4), 'permanentmutex27:4'
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    absent=[]
    for row in json.loads(Path(PINS[2]['path']).read_text())['paths']:
        try:
            Path(row['path']).lstat()
        except FileNotFoundError:
            absent.append({'path':row['path'],'observation':'ENOENT'})
        else:
            raise ValueError('canonicalrecord present '+row['path'])
    capture.write(O/'admission-snapshot.json',{'mutex':{'device':info.st_dev,'inode':info.st_ino,'uid':info.st_uid,'mode':stat.S_IMODE(info.st_mode)},'canonical_absent':absent,'NPROC_inherited':list(resource.getrlimit(resource.RLIMIT_NPROC))})
    commands = [{'role':'exact-owner-export','argv':export['argv'],'cpu':30,'wall':35,'cap':33554432}] + [{'role':'exact-name-query' if i==0 else 'exact-label-query','argv':row['argv'],'cpu':10,'wall':15,'cap':1048576} for i,row in enumerate(queries['queries'])]
    for i,command in enumerate(commands):
        dest=O/('%02d-%s'%(i,command['role']));dest.mkdir(mode=0o700)
        capture.write(dest/'command.json',command)
        def limits():
            os.sched_setaffinity(0,{7})
            resource.setrlimit(resource.RLIMIT_CPU,(command['cpu'],command['cpu']))
            resource.setrlimit(resource.RLIMIT_FSIZE,(command['cap'],command['cap']))
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        row=capture.owned_capture(command,dest,command['wall'],limits)
        row.update(role=command['role'],argv=command['argv'])
        capture.write(dest/'status.json',row);records.append(row)
        assert row['returncode']==0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and not row['timed_out'] and not row['error'] and not row['retirement_error'], 'capture/join failure'
        assert row['captures']['stderr']['size']==0, 'nonempty stderr'
        if i==0:
            assert row['captures']['stdout']['size']<=16777216, 'encoded export cap'
        else:
            assert row['captures']['stdout']['size']==0, 'container present'
finally:
    if lock is not None:
        os.close(lock)
    # The accepted capture routine joins each direct child and closes streams before returning.
    capture.write(O/'serial-result.json',{'status':'PASS_READONLY_EXPORT_AND_TWO_QUERIES' if len(records)==3 and all(v['returncode']==0 and v['direct_child_joined'] and v['group_absent'] and v['closed_streams'] and not v['error'] and not v['retirement_error'] and v['captures']['stderr']['size']==0 for v in records) and records[1]['captures']['stdout']['size']==records[2]['captures']['stdout']['size']==0 else 'INCOMPLETE_OR_FAILED_PRESERVE_ALL','records':records,'elapsed_seconds':time.monotonic()-started,'physical_acceptance':False,'native_or_restoration_credit':False,'NPROC':'inherited','source_pins':PINS})
