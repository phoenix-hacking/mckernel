#!/home/holden/anaconda3/bin/python3
"""Future read-only root observation. No cleanup, deletion or source writes."""
import argparse
import contextlib
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import stat
import subprocess
import sys
import types



FAILURE_CASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/CURRENT-RETAINED-VALIDATOR-FAILURE.CASE.json')
FAILURE_CASE_SHA = '54883f8449dff36370eed07d7868c4b8aac9dd8e85765e27a841e3b173320c0d'
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PREP = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1')
CASE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-6')
CAPTURE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/retained-validation-attempt-6/owner-evidence/attempt')
SOURCE = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/cleanup_failed_retained_validator.py')
TEST = Path('/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/test_retained_validator_receipt.py')
SOURCE_SHA = 'fb3411e90b4e0e80e5cc57778464d4dc73cf73a65d7dd944eb8e7cd60f457862'
TEST_SHA = '058f2be584f9fa6b04a97d4e2a87ab6497c16296e0d642133387581485e084fa'
RETIREMENT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/ROOT-PROVIDED-TOOL81525-TERMINAL.RECORD.json')
RETIREMENT_SHA = 'd5bb689ba9fadadfd2521164768736b12b66bda58b4860b6fdbedb2d664cc6e0'
NONCE = 'm14-retained-validator-copy6-failed-observation-20261024-1'
OUTPUT = PREP / ('root-observation-' + NONCE)
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PIDS = (218109, 218117, 218133, 218125, 218217, 218190, 218226)


def need(ok, reason):
    if not ok:
        raise RuntimeError(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def stable_bytes(path, expected, maximum=1 << 20):
    need(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink source refused')
    fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_size <= maximum, 'bounded regular source required')
        data = bytearray()
        while len(data) <= maximum:
            part = os.read(fd, min(65536, maximum + 1 - len(data)))
            if not part:
                break
            data.extend(part)
        after = os.fstat(fd)
        keys = ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k) for k in keys) and
             all(getattr(path.lstat(),k)==getattr(after,k) for k in keys), 'source read raced')
    finally:
        os.close(fd)
    need(len(data) <= maximum and sha(data) == expected, 'source digest differs')
    return bytes(data)


def store(name, raw):
    need(len(raw) <= 128 * 1024 * 1024, 'finite observation output bound')
    fd = os.open(OUTPUT/name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


METADATA_AS = 536870912
DOCKER_AS = 2147483648
DIAGNOSTIC_CAP = 1048576
CLEAN_ENV = {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'}


def docker_child_profile(soft_as):
    # Single-threaded observer only; no global environment or container change.
    need(soft_as in (METADATA_AS, DOCKER_AS), 'fixed Docker child profile required')
    need(resource.getrlimit(resource.RLIMIT_AS) == (METADATA_AS, DOCKER_AS),
         'metadata parent resource profile differs')
    resource.setrlimit(resource.RLIMIT_AS, (soft_as, DOCKER_AS))


def observed_command(argv, limit, retain, timeout_seconds=30, docker_soft_as=DOCKER_AS):
    """Capture completed/timeout bytes before applying the unchanged strict oracle.

    Production caller supplies only its exact fixed read-only commands. The
    unprivileged tests use docker --version through this same launch path.
    subprocess.run kills and waits for the child on TimeoutExpired.
    """
    need(0 < limit <= DIAGNOSTIC_CAP, 'small observer command bound required')
    is_docker = argv[:1] == ['/usr/bin/docker']
    preexec = (lambda: docker_child_profile(docker_soft_as)) if is_docker else None
    timed_out = False
    launch_error = None
    try:
        result = subprocess.run(argv, env=CLEAN_ENV, stdin=subprocess.DEVNULL,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                timeout=timeout_seconds, check=False, preexec_fn=preexec)
        stdout, stderr, returncode = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, returncode = exc.stdout or b'', exc.stderr or b'', None
        timed_out = True
    except (OSError, subprocess.SubprocessError) as exc:
        stdout, stderr, returncode = b'', b'', None
        launch_error = type(exc).__name__ + ': ' + str(exc)
    row = dict(argv=argv,returncode=returncode,timed_out=timed_out,launch_error=launch_error,
               timeout_seconds=timeout_seconds,output_limit=limit,
               effective_address_space_soft_bytes=docker_soft_as if is_docker else METADATA_AS,
               effective_address_space_hard_bytes=DOCKER_AS,
               clean_environment=CLEAN_ENV)
    for label, raw, cap in (('stdout',stdout,limit),('stderr',stderr,DIAGNOSTIC_CAP)):
        row[label+'_sha256'] = sha(raw)
        row[label+'_observed_bytes'] = len(raw)
        row[label+'_retained_bytes'] = min(len(raw),cap)
        row[label+'_truncated'] = len(raw) > cap
        row[label+'_retained_sha256'] = sha(raw[:cap])
    retain(row,stdout[:limit],stderr[:DIAGNOSTIC_CAP])
    need(launch_error is None, 'root-command-launch-failed:' + argv[0])
    need(not timed_out, 'root-command-timeout:' + argv[0])
    need(not returncode and not stderr and len(stdout) <= limit,
         'root-command-failed:' + argv[0])
    return stdout


TERMINAL_INSPECTION_SHA = '62a2ea9f75badc0167478573642d1d43c0276a2da420ab75a0fde215e56c29da'

OBSERVATION_COMMAND = ['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve())]
OBSERVATION_PROFILE = {'metadata_soft_as': 536870912, 'metadata_hard_as': 2147483648, 'only_exact_docker_child_soft_as': 2147483648, 'command_timeout_seconds': 30, 'output_limit_bytes': 1048576, 'selected_hash_cap_bytes': 134217728, 'inventory_cap': 400000}

def canonical_payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def validate_observation_release(path, expected, commit, tree):
    release=json.loads(stable_bytes(path,expected))
    need(release.get('schema')=='mckernel.m14.current-failed-image.readonly-observation-release.v1' and
         release.get('status')=='PASS_EXECUTION_RELEASE' and release.get('cleanup_authorized') is False and
         release.get('fetched_source_verified') is True and release.get('git_commit')==commit and
         release.get('git_tree')==tree and release.get('nonce')==NONCE and
         release.get('output')==str(OUTPUT) and release.get('observer_sha256')==sha(Path(__file__).read_bytes()) and
         release.get('owned_logs_lifecycle_test_sha256')=='9474efff1ee2ed77ee8340c3a37cc6bf57cf83b68c3e0fdef0e823d7b0560b60' and
         release.get('cleanup_source_sha256')==SOURCE_SHA and release.get('cleanup_tests_sha256')==TEST_SHA and
         release.get('retirement_sha256')==RETIREMENT_SHA and release.get('failure_case_sha256')==FAILURE_CASE_SHA and
         release.get('observer_command')==OBSERVATION_COMMAND and
         release.get('resource_profile')==OBSERVATION_PROFILE,'exact independently released observation required')
    need(isinstance(release.get('author'),str) and release['author'] and release.get('source_review') and release.get('execution_review'),'independent observation reviews required')
    payload={key:value for key,value in release.items() if key!='execution_review'}
    for key in ('source_review','execution_review'):
        ref=release[key];review=json.loads(stable_bytes(Path(ref['path']),ref['sha256']))
        need(review.get('status')=='PASS' and isinstance(review.get('reviewer'),str) and review['reviewer'] and
             review['reviewer']!=release['author'] and review.get('implementation_ownership') is False and
             review.get('observer_sha256')==release['observer_sha256'] and
             review.get('cleanup_source_sha256')==SOURCE_SHA and review.get('cleanup_tests_sha256')==TEST_SHA,'independent exact observation review required')
        if key=='execution_review':
            need(review.get('reviewed_observation_payload_sha256')==sha(canonical_payload(payload)),'exact observation execution payload differs')
    return release





KNOWN_TOOL_TERMINAL = {'artifact_acceptance': False, 'authority': 'Root task report of closed tool81525 plus exact retained owner stdout; root fresh process/physical observation remains required.', 'capture_method': 'unified_exec', 'cleanup_separately_required': True, 'closed_streams': None, 'container_id': 'e3668ee5539ee1d4c6901881080662e906f50a28eb2d4c40f50c4d8b4da4ed0a', 'direct_child_joined': None, 'driver_error': None, 'driver_phase': None, 'driver_status': None, 'early_entry_failure': 'corrected driver identity before evidence root/driverreceipt/observer', 'exit_code': 1, 'group_absent': None, 'h990_outer_capture_present': False, 'outer_identity': None, 'owner_pid': 216990, 'owner_starttime': '65817737', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status': 'CLI_RETURNED', 'tool_session': 81525}
KNOWN_TARGET = {'container_id': 'e3668ee5539ee1d4c6901881080662e906f50a28eb2d4c40f50c4d8b4da4ed0a', 'container_name': 'mckernel-image-e96e3a8770554ab88c15df53dedd9635', 'exit_code': 1, 'image_id': 'sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5', 'owner_nonce': '9c2f4a360dda479987a3db77822e51ca', 'owner_pid': 216990, 'owner_starttime': '65817737'}
CLI_PROOF = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/CLOSED-IMAGE-OWNER-CLI-PROOF.json')

EXPECTED_CURRENT_FIXTURE = {'fixture_sha256': '058f2be584f9fa6b04a97d4e2a87ab6497c16296e0d642133387581485e084fa', 'schema': 'mckernel.m14.current-retained-receipt-pure-fixture.v1', 'source_sha256': 'e64f1bc5114c9648f4e2fdbd8d87ab5f48ebee7527a89f3de811f566eb07d505', 'status': 'PASS', 'tests_run': 12}
PENDING_BINDINGS = ()

def current_pass_prerequisites(retirement, case, root_join, artifact):
    """Exact failed-build authority; no invented historical outer join or artifact PASS."""
    need(retirement == KNOWN_TOOL_TERMINAL, 'truthful current unified-exec terminal record required')
    need(case['schema']=='mckernel.m14.failed-image-retained-case.v1' and
         case['execution_authorized'] is False and case['successful_artifacts_required'] is False and
         case['target']==KNOWN_TARGET and case['source_identity']==CURRENT_EXPECTED_SOURCE,
         'exact current failed case/source required')
    need(root_join['returncode']==0 and root_join['direct_child_joined'] is True and
         root_join['group_absent'] is True and root_join['closed_streams'] is True and
         root_join['error'] is None and root_join['retirement_error'] is None and
         root_join['timed_out'] is False and root_join['remaining_group_members']==[] and
         root_join['unexpected_group_members']==[], 'actual30 receipt fixture whole join required')
    for channel in ('stdout','stderr'):
        row=root_join['captures'][channel]
        need(row['path']==str(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-early-retirement-predicate-tests-1')/channel), 'current pure fixture stream path differs')
        raw=stable_bytes(Path(row['path']),row['sha256'])
        need(len(raw)==row['size'], 'current pure fixture stream size differs')
    result_ref=case['finite_roles']['fixture_result']
    actual_fixture=json.loads(stable_bytes(Path(result_ref['path']),result_ref['sha256']))
    need(actual_fixture==EXPECTED_CURRENT_FIXTURE, 'current retained receipt gate actual fixture required')
    need(artifact.get('status')=='FAIL' and artifact.get('retired') is True and
         artifact.get('cleanup_separately_required') is True and artifact.get('exit_code')==1 and
         artifact.get('container_id')==KNOWN_TARGET['container_id'] and
         case.get('driver_receipt_absent') is True and case.get('driver_evidence_root_absent') is True,
         'exact early COPY6 owner failure required; no artifact acceptance')


CURRENT_EXPECTED_SOURCE = {'candidate_identity_scope': 'base_git_commit_only', 'candidate_sha': '942c927b1ec93cc31284ff498455909d9bb2d0fc', 'materialization_sha256': 'a57d2d9f8f71fc026aceae8a64f3c34f5314e8d04031e63c262f0fdc036cbef8', 'source_derivative_sha256': '2b12d740e25b0dd3c2dbb17031d59d2f47fd4c9569a8820be869411da4aa97c1', 'source_identity': {'dev': 66306, 'file_type': 16384, 'gid': 1000, 'inode': 56250160, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source', 'uid': 1000}, 'source_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-10/m14-union2-default-image-preparation-1/source-materialization-CPU0-1/materialized-source'}

def decode_finite_case(case):
    """Reject scalar inventory schema; bind exact sorted role path union pre-mutation."""
    need(type(case) is dict, 'finite-case: dictionary required')
    roles=case.get('finite_roles'); paths=case.get('finite_unique_paths')
    need(type(roles) is dict and roles and all(type(k) is str and k for k in roles),
         'finite-case: named role dictionary required')
    need(type(paths) is list, 'finite-case: path list required; scalar schema refused')
    need(type(case.get('finite_role_count')) is int and case['finite_role_count']==len(roles),
         'finite-case: role count differs')
    need(type(case.get('finite_unique_path_count')) is int and case['finite_unique_path_count']==len(paths),
         'finite-case: path count differs')
    def path_name(value):
        need(type(value) is str and value.startswith('/') and not value.startswith('//') and
             '\x00' not in value and all(part not in ('','.','..') for part in value.split('/')[1:]),
             'finite-case: canonical absolute path required')
        p=Path(value)
        need(str(p)==value and not any(q.is_symlink() for q in (p,*p.parents)),
             'finite-case: nonsymlink canonical path required')
        return value
    bypath={}
    for role,row in roles.items():
        need(type(row) is dict and set(row)=={'path','sha256','bytes'},
             'finite-case: exact descriptor shape required:'+role)
        path=path_name(row['path']); digest=row['sha256']; size=row['bytes']
        need(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest) and
             type(size) is int and size>=0, 'finite-case: descriptor hash/byte shape differs:'+role)
        need(path not in bypath or bypath[path]==row, 'finite-case: conflicting aliases:'+role)
        bypath[path]=row
    need(all(type(p) is str for p in paths), 'finite-case: string paths required')
    for p in paths:path_name(p)
    need(paths==sorted(bypath), 'finite-case: exact sorted distinct role path union required')
    return tuple(paths)


FUTURE_LIFECYCLE_JOIN = '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-owned-logs-lifecycle-tests-1/WHOLE-JOIN.json'
EXPECTED_LIFECYCLE = {'schema': 'mckernel.copy6.exact-owned-log-lifecycle.v1', 'status': 'PASS', 'tests_run': 7, 'source_sha256': 'fb3411e90b4e0e80e5cc57778464d4dc73cf73a65d7dd944eb8e7cd60f457862', 'fixture_sha256': '9474efff1ee2ed77ee8340c3a37cc6bf57cf83b68c3e0fdef0e823d7b0560b60'}
EXPECTED_LIFECYCLE_RESULT = {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy6-normal-retirement-preparation-1/bounded-owned-logs-capture-correction-1/ACTUAL-OWNED-LOGS-LIFECYCLE-RESULT.json', 'bytes': 263, 'sha256': 'e3b9a6cac574acea5ecf1751ddac9383414f85326a08879038c7d2d823ecda93'}

def owned_lifecycle_prerequisites(reference):
    need(reference.get('path') == FUTURE_LIFECYCLE_JOIN, 'exact actual owned lifecycle wholejoin required')
    joined=json.loads(stable_bytes(Path(reference['path']),reference['sha256']))
    need(joined.get('returncode')==0 and joined.get('direct_child_joined') is True and
         joined.get('group_absent') is True and joined.get('closed_streams') is True and
         joined.get('error') is None and joined.get('retirement_error') is None and
         joined.get('timed_out') is False and joined.get('remaining_group_members')==[] and
         joined.get('unexpected_group_members')==[], 'actual owned lifecycle fixture must close cleanly')
    for channel in ('stdout','stderr'):
        stream=joined['captures'][channel]
        need(stream['path']==str(Path(FUTURE_LIFECYCLE_JOIN).parent/channel), 'exact lifecycle stream path')
        raw=stable_bytes(Path(stream['path']),stream['sha256'])
        need(len(raw)==stream['size'],'actual lifecycle stream size')
    actual=json.loads(stable_bytes(Path(EXPECTED_LIFECYCLE_RESULT['path']),EXPECTED_LIFECYCLE_RESULT['sha256']))
    need(actual==EXPECTED_LIFECYCLE,'actual seven owned-child controls required')
    return joined


def main(argv=None):
    need(not PENDING_BINDINGS, 'pending actual source bindings: ' + repr(PENDING_BINDINGS))
    args=argparse.ArgumentParser(description=__doc__)
    args.add_argument('--git-commit',required=True)
    args.add_argument('--git-tree',required=True)
    args.add_argument('--observation-release',required=True)
    args.add_argument('--observation-release-sha256',required=True)
    opts=args.parse_args(argv)
    need(os.getuid()==os.geteuid()==0, 'root read-only observation required')
    resource.setrlimit(resource.RLIMIT_AS,(METADATA_AS,DOCKER_AS))
    resource.setrlimit(resource.RLIMIT_CORE,(0,0))
    observation_release=validate_observation_release(Path(opts.observation_release),opts.observation_release_sha256,opts.git_commit,opts.git_tree)
    for token in (opts.git_commit,opts.git_tree):
        need(len(token)==40 and all(c in '0123456789abcdef' for c in token),'published CODE Git identity required')
    module=types.ModuleType('_frozen_fp_cleanup_observation')
    module.__file__=str(SOURCE)
    exec(compile(stable_bytes(SOURCE,SOURCE_SHA),str(SOURCE),'exec'),module.__dict__)
    m=module
    stable_bytes(TEST,TEST_SHA)
    retirement=m.parse(stable_bytes(RETIREMENT,RETIREMENT_SHA))
    case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))
    finite_paths=decode_finite_case(case)
    root_join_ref=observation_release['current_fixture_whole_join']
    need(root_join_ref['path']==str(Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-early-retirement-predicate-tests-1/WHOLE-JOIN.json')), 'exact current receipt fixture wholejoin path required')
    root_join=json.loads(stable_bytes(Path(root_join_ref['path']),root_join_ref['sha256']))
    artifact_ref=case['finite_roles']['owner_receipt']
    artifact=json.loads(stable_bytes(Path(artifact_ref['path']),artifact_ref['sha256']))
    current_pass_prerequisites(retirement,case,root_join,artifact)
    lifecycle_ref=observation_release['owned_logs_lifecycle_whole_join']
    lifecycle_join=owned_lifecycle_prerequisites(lifecycle_ref)
    need(not OUTPUT.exists() and not os.path.lexists(CLI_PROOF),'fresh observation and CLI-proof paths required')
    parent_fd,parent_chain=m.directory(PREP)
    lock_parent,_=m.directory(m.ROOT_LOCK.parent)
    lock_fd=None
    try:
        lock_fd=os.open(m.ROOT_LOCK.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=lock_parent)
        lock=m.observe_identity(m.ROOT_LOCK)
        need((lock['device'],lock['inode'],lock['uid'],lock['gid'],lock['mode'],lock['nlink'],lock['size'])==(27,4,0,0,'0o644',1,0),'persistent exact root mutex required')
        need(m.identity(os.fstat(lock_fd))==(27,4),'held root mutex differs')
        fcntl.flock(lock_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'boot differs')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY,'fixed namespace ancestry differs')
        OUTPUT.mkdir(mode=0o700)
        store('ownership.json',m.canonical(dict(nonce=NONCE,pid=os.getpid(),root_lock=lock,output=m.observe_identity(OUTPUT),role='READ_ONLY_OBSERVER_NO_CLEANUP')))
        command_rows=[]
        def capture_command(argv,limit):
            allowed = (argv == ['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','ps','-a','--no-trunc','--format','{{json .}}'] or
                       argv == ['/usr/bin/docker','--host=unix:///var/run/docker.sock','inspect','--type','container',m.KNOWN_TARGET['container_id']])
            need(allowed,'only exact fixed read-only observer commands permitted')
            name='readonly-command-%02d'%len(command_rows)
            def retain(row,stdout,stderr):
                store(name+'.stdout',stdout)
                store(name+'.stderr',stderr)
                command_rows.append(row)
                store(name+'.json',m.canonical(row))
            return observed_command(argv,limit,retain)
        m.root_command=capture_command
        process_paths=[]
        m.BOOT_ID=BOOT;m.OWNER_PID=case['target']['owner_pid'];m.OWNER_START=case['target']['owner_starttime'];m.WAITER_PIDS=PIDS
        def process_snapshot():
            caller=[os.getpid(),Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode('ascii')]
            old=sys.argv;out=io.StringIO()
            try:
                sys.argv=['readonly-process',NONCE,str(caller[0]),caller[1]]
                with contextlib.redirect_stdout(out):
                    exec(compile(m.PROC_CODE,'<accepted cleanup read-only PROC_CODE>','exec'),{'__name__':'_readonly_process'})
            finally:
                sys.argv=old
            raw=out.getvalue().encode();need(len(raw)<=m.PROC_LIMIT,'process observation bound')
            name='process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')])
            store(name,raw)
            m.validate_process_report(m.parse(raw),NONCE,caller)
            process_paths.append(OUTPUT/name)
        m.process_absent=process_snapshot
        mount_raw=capture_command(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],m.LIMIT)
        mounts=m.parse(mount_raw)['filesystems'];need(len(mounts)==1,'one scratch mount required')
        mount=mounts[0]
        need(mount['uuid']==m.UUID and mount['target']==str(ROOT) and mount['fstype']=='ext4' and {'rw','nodev','nosuid'}<=set(mount['options'].split(',')),'scratch mount differs')
        owner_ref=case['finite_roles']['owner_receipt']
        owner=m.parse(stable_bytes(Path(owner_ref['path']),owner_ref['sha256']))
        m.early_entry_failure_binding(stable_bytes(Path(case['finite_roles']['container_log']['path']),case['finite_roles']['container_log']['sha256']),os.path.lexists(m.OUTPUT/'evidence'))
        old_inspect=owner['terminal_container_info']
        target=dict(case['target']);need(target['image_id']==old_inspect['Image'],'actual current failed image identity')
        m.validate_attempt_binding(target,dict(path=str(m.REQUEST),sha256=m.REQUEST_SHA))
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=target['exit_code'];m.EXPECTED_CONTAINER=old_inspect
        need(m.census(),'retained exact terminal container required')
        inspection=m.parse(m.docker(['inspect','--type','container',target['container_id']]))[0]
        m.validate_container_profile(inspection)
        guard=dict(schema='mckernel.m14.failed-image-owner-cli-proof.v1',
                   status='CLOSED_CLI_AND_CURRENT_OWNER_ABSENCE_CONTAINER_RETAINED',
                   owner_status='FAIL',owner_receipt_sha256=owner_ref['sha256'],
                   container_id=target['container_id'],retired=True,retained_for_separate_cleanup=True,
                   interrupted_signal=None,known_owner=dict(pid=216990,starttime='65817737'),
                   unrecorded_outer_identity=None,tool_terminal=m.observe_identity(RETIREMENT),
                   fresh_process_observation=m.observe_identity(process_paths[-1]))
        m.image_receipt_binding(owner,guard,target,inspection,owner_ref['sha256'])
        proof_parent,_=m.directory(CLI_PROOF.parent)
        try:m.create_at(proof_parent,CLI_PROOF.name,m.canonical(guard)+b'\n')
        finally:os.close(proof_parent)
        statuses=sorted(CAPTURE.glob('command-*/status.json'));ledger=[]
        selected_paths={Path(p) for p in finite_paths}
        selected_paths.update((SOURCE,TEST,FAILURE_CASE,CLI_PROOF,RETIREMENT,process_paths[-1]))
        selected_paths.add(Path(root_join_ref['path']))
        selected_paths.add(Path(lifecycle_ref['path']))
        selected_paths.update(Path(lifecycle_join['captures'][label]['path']) for label in ('stdout','stderr'))
        selected_paths.update(Path(root_join['captures'][label]['path']) for label in ('stdout','stderr'))
        need(set(selected_paths)>={m.REQUEST,m.TERMINAL,m.EVIDENCE/'attempt/container.log',Path(case['finite_roles']['container_log']['path'])},'failed image minimum receipt roles')
        for path in statuses:
            row=m.observe_identity(path);status=m.parse(m.read_bounded(path))
            need(status.get('state')=='exited' and status.get('exit_code')==0 and status.get('pid') in PIDS and not status.get('client_retirement_unproven'),'positive original client ledger required')
            ledger.append(dict(pid=status['pid'],status_path=str(path),status_sha256=row['sha256']))
            selected_paths.update((path,path.parent/'stdout',path.parent/'stderr'))
        need({r['pid'] for r in ledger}==set(PIDS) and len(ledger)==len(PIDS),'all exact current original clients required')
        # Current successful primary/evidence artifacts are exact finite roles bound by the actual producer.
        # Store the finite selected role descriptors, preserving the original five-file export shape.
        finite_metadata=[m.observe_identity(Path(p)) for p in finite_paths]
        for row in finite_metadata:
            refs=[v for v in case['finite_roles'].values() if v['path']==row['path']]
            need(refs and all(row['sha256']==v['sha256'] and row['size']==v['bytes'] for v in refs),'closed current role bytes differ')
        store('new-object-metadata.json',m.canonical(dict(authority_path=str(FAILURE_CASE),authority_sha256=FAILURE_CASE_SHA,objects=finite_metadata,successful_artifacts_required=False)))
        selected_paths.add(OUTPUT/'new-object-metadata.json')
        selected=[m.observe_identity(path) for path in sorted(selected_paths)]
        selected_map={row['path']:row for row in selected}
        need(selected_map[str(m.REQUEST)]['sha256']==m.REQUEST_SHA,'request bytes differ')
        records=[m.observe_identity(path) for path in (m.ATTEMPT,m.SHARED)]
        for row,role in zip(records,('common','shared')):
            need(row==case['retained_ownership'][role],'retained full record identity differs:'+role)
            record=m.parse(m.read_bounded(Path(row['path'])))
            m.image_record_binding(Path(row['path']),row,record,m.parse(m.read_bounded(m.REQUEST)),target,BOOT)
        need(not os.path.lexists(m.LEASE),'request lease reappeared')
        request=m.parse(m.read_bounded(m.REQUEST))
        m.image_request_binding(request)
        observation=dict(mount=mount,root=m.observe_identity(ROOT),boot_id=BOOT,root_lock=lock,request=selected_map[str(m.REQUEST)],target=target,container_inspect=inspection,retained_exclusions=records,request_lease_absent=True,inventories={str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(Path(request['source_root'])),candidate_commit=m.IMAGE_CANDIDATE,candidate_tree=None,selected_files=selected,backup_root=m.observe_identity(ROOT/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'),namespace_binding=m.NAMESPACE_BINDING,namespace_ancestry=m.NAMESPACE_ANCESTRY,client_ledger=ledger,guard_proof=selected_map[str(CLI_PROOF)])
        # No configure/cleanup call: prepare_release only binds these bytes.
        need(m.census(),'terminal container changed during read-only observation')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'post-observation ancestry/boot changed')
        for path in (m.OUTPUT,m.EVIDENCE):
            need(m.metadata_inventory(path)==observation['inventories'][str(path)],'preserved output metadata changed')
        for row in selected:
            need(m.observe_identity(Path(row['path']))==row,'selected input/artifact changed')
        need([m.observe_identity(Path(p)) for p in finite_paths]==finite_metadata,'finite current role metadata changed during observation')
        need([m.observe_identity(p) for p in (m.ATTEMPT,m.SHARED)]==records and not os.path.lexists(m.LEASE),'ownership changed')
        fd,chain=m.directory(PREP);os.close(fd);need(chain==parent_chain,'output parent replaced')
        store('observation.json',m.canonical(observation)+b'\n')
        draft=m.prepare_release(observation,opts.git_commit,opts.git_tree)
        store('cleanup-release-draft.json',m.canonical(draft)+b'\n')
        store('observer-result.json',m.canonical(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',nonce=NONCE,observation_sha256=sha((OUTPUT/'observation.json').read_bytes()),cleanup_release_draft_sha256=sha((OUTPUT/'cleanup-release-draft.json').read_bytes()),commands=command_rows,cleanup_executed=False,application_acceptance=False)))
        os.fsync(parent_fd)
        print(json.dumps(dict(status='PASS_READ_ONLY_OBSERVATION_ONLY',output=str(OUTPUT),cleanup_executed=False)))
    finally:
        if lock_fd is not None:
            fcntl.flock(lock_fd,fcntl.LOCK_UN);os.close(lock_fd)
        os.close(lock_parent);os.close(parent_fd)


if __name__=='__main__':
    main()
