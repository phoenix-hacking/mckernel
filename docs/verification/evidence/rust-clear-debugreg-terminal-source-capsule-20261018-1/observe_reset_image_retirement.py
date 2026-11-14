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

REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PREP = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-terminal-preparation-20261018-1')
CASE = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1')
CAPTURE = Path('/home/holden/mckernel-work/scratch/native-rust-clear-debugreg-image-guard-20261018-e4becbcd4971479f81426b3872cbe27c')
SOURCE = Path('/home/holden/mckernel/scripts/native_rust_cutover_image_terminal_cleanup.py')
TEST = Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')
SOURCE_SHA = '6851d37b2aaa59d47de9ef13aa15c7e95dda6c6c072d288c8090ae35db467b1a'
TEST_SHA = 'ac68e077d07e3c7ea8e822f53fd8e04e75066206679589191d44891a567242a3'
RETIREMENT = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-terminal-preparation-20261018-1/actual-physical-bindings.json')
RETIREMENT_SHA = '2950d0bb5bef75735f83d56d96fc97a650dba935649328e723ecfa3af64efd99'
OBJECT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-terminal-preparation-20261018-1/actual-process-object-authority.json')
OBJECT_AUTHORITY_SHA = '39b7cdbb520ea45eebe011f25a3f7323cf34d3f8f3daac27ad35adbd23c959eb'
NONCE = '4ea001c3547b44a8a1d9f302ba0bbdd9'
OUTPUT = PREP / ('root-observation-' + NONCE)
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PIDS = (1127075, 1127067, 1129794, 1127149, 1127091, 1127083, 1130264, 1129802)


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


METADATA_AS = 268435456
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


NEW_OBJECT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-terminal-preparation-20261018-1/retained-production-objects/retained-objects.json')
NEW_OBJECT_AUTHORITY_SHA = '46e32e867084afab307cd071880770e49b7a13f6013aa88383fef6ded9c7ee70'
ARTIFACT_AUTHORITY = Path('/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-actual-review-20261018-1/actual-review.json')
ARTIFACT_AUTHORITY_SHA = 'dacf4e3f08ecc119356471ff7c8c2a7112e3f1f2f96f61086268631f92c4a30f'
TERMINAL_INSPECTION_SHA = None

OBSERVATION_COMMAND = ['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve())]
OBSERVATION_PROFILE = dict(metadata_soft_as=268435456,metadata_hard_as=2147483648,only_exact_docker_child_soft_as=2147483648,command_timeout_seconds=30,output_limit_bytes=1048576,selected_hash_cap_bytes=134217728,inventory_cap=400000)

def canonical_payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()

def new_object_binding(m,bound):
    """Bind real selected identity/hash plus independently fd-stable timestamps."""
    path=Path(bound['path'])
    parent,_=m.directory(path.parent)
    fd=None
    try:
        fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode),'new object must be regular')
        fresh=m.observe_identity(path)
        after=os.fstat(fd)
        named=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
        keys=('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
        need(all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in keys),'new object metadata raced')
        metadata=dict(fresh,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns)
        need(all(metadata[k]==bound[k] for k in ('path','sha256','size','device','inode','mode','mtime_ns')),'new object authority binding differs')
        need((fresh['device'],fresh['inode'],fresh['size'],fresh['mode'])==(after.st_dev,after.st_ino,after.st_size,oct(stat.S_IMODE(after.st_mode))),'new object descriptor identity differs')
        return metadata
    finally:
        if fd is not None:os.close(fd)
        os.close(parent)

def validate_observation_release(path, expected, commit, tree):
    release=json.loads(stable_bytes(path,expected))
    need(release.get('schema')=='mckernel.fpu-copy-image.readonly-observation-release.v1' and
         release.get('status')=='PASS_EXECUTION_RELEASE' and release.get('cleanup_authorized') is False and
         release.get('fetched_source_verified') is True and release.get('git_commit')==commit and
         release.get('git_tree')==tree and release.get('nonce')==NONCE and
         release.get('output')==str(OUTPUT) and release.get('observer_sha256')==sha(Path(__file__).read_bytes()) and
         release.get('cleanup_source_sha256')==SOURCE_SHA and release.get('cleanup_tests_sha256')==TEST_SHA and
         release.get('retirement_sha256')==RETIREMENT_SHA and release.get('new_objects_sha256')==NEW_OBJECT_AUTHORITY_SHA and
         release.get('artifact_sha256')==ARTIFACT_AUTHORITY_SHA and
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


ARTIFACT_EXPECTED_GUARD = {'owner_receipt_sha256': '1c93b0dd2d4e3bd8cfc30700a8ef9911b77bd3a56b8092a97783988ca7e1a953', 'guard_result_sha256': '3c87616ee633388dca45a78f32b55b2f6abe9b93f6e8a79a303ef171698528cc', 'container_id': '10c33a4066452a753193bffe1bf8e744a6eb6580ca305c3218147194e05353a7', 'retired': True, 'physical_client_terminal_count': 8, 'common_shared_cleanup': False}
ARTIFACT_EXPECTED_PINS = {'image': {'bytes': 7928528, 'ctime_ns': 1792347186182070158, 'dev': 66306, 'gid': 1000, 'inode': 47872037, 'mode': 493, 'mtime_ns': 1792347186182070158, 'path': '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/owner-work/output/build/kernel/mckernel.img', 'sha256': 'e85a1e356e6d09a119d01bbfa2a5175b084dfda1158e9caff508c6434c9a216e', 'uid': 1000}, 'process': {'bytes': 318520, 'ctime_ns': 1792347185054145389, 'dev': 66306, 'gid': 1000, 'inode': 47872027, 'mode': 420, 'mtime_ns': 1792347185054145389, 'path': '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o', 'sha256': '250a61c8a68cb041f7ceb01ab789c59cba5b0d2a63fdbc096f44288bdda858a7', 'uid': 1000}, 'rust': {'bytes': 12641648, 'ctime_ns': 1792347184338193388, 'dev': 66306, 'gid': 1000, 'inode': 47872010, 'mode': 420, 'mtime_ns': 1792347184338193388, 'path': '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/owner-work/output/build/kernel/rust/mckernel_rust.o', 'sha256': '37dc0abbf68908161a9d8a28d4338bf6fe775e59d6b2269c1f8a7b54bb9ca63e', 'uid': 1000}, 'syscall': {'bytes': 211200, 'ctime_ns': 1792347185510114954, 'dev': 66306, 'gid': 1000, 'inode': 47872033, 'mode': 420, 'mtime_ns': 1792347185510114954, 'path': '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/owner-work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o', 'sha256': '586531535da38b7a45f825b20f5f57985df0c9dd0ec6f26c15ad8a38cec67ec5', 'uid': 1000}}

def validate_artifact_authority(review):
    need(isinstance(ARTIFACT_EXPECTED_GUARD,dict) and isinstance(ARTIFACT_EXPECTED_PINS,dict) and set(ARTIFACT_EXPECTED_PINS)=={'syscall','process','rust','image'},'PENDING_EXACT_CLEAR_DEBUGREG_ARTIFACT_IDENTITIES')
    need(review.get('schema')=='mckernel.independent-rust-clear-debugreg-image-actual-review.v1' and review.get('decision')=='PASS_ACTUAL_PRODUCTION_IMAGE_ARTIFACT_AND_GUARD_RETIREMENT' and review.get('implementation_ownership') is False,'actual independent scheduler image artifact authority required')
    guard=review.get('guard_retirement') or {}
    expected_guard=ARTIFACT_EXPECTED_GUARD
    need(all(guard.get(key)==value for key,value in expected_guard.items()),'exact scheduler artifact guard retirement required')
    actual=review.get('actual_artifacts') or {}
    need(set(actual)==set(ARTIFACT_EXPECTED_PINS),'exact scheduler artifact set required')
    for name,expected in ARTIFACT_EXPECTED_PINS.items():
        need(all(actual[name].get(key)==expected[key] for key in ('path','sha256','bytes','dev','inode','uid','mode')),'exact scheduler actual artifact binding required')
    return review


PENDING_BINDINGS = ()

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
    validate_observation_release(Path(opts.observation_release),opts.observation_release_sha256,opts.git_commit,opts.git_tree)
    for token in (opts.git_commit,opts.git_tree):
        need(len(token)==40 and all(c in '0123456789abcdef' for c in token),'published CODE Git identity required')
    module=types.ModuleType('_frozen_fp_cleanup_observation')
    module.__file__=str(SOURCE)
    exec(compile(stable_bytes(SOURCE,SOURCE_SHA),str(SOURCE),'exec'),module.__dict__)
    m=module
    stable_bytes(TEST,TEST_SHA)
    retirement=m.parse(stable_bytes(RETIREMENT,RETIREMENT_SHA))
    new_objects=m.parse(stable_bytes(NEW_OBJECT_AUTHORITY,NEW_OBJECT_AUTHORITY_SHA))
    validate_artifact_authority(m.parse(stable_bytes(ARTIFACT_AUTHORITY,ARTIFACT_AUTHORITY_SHA)))
    retirement=dict(retirement,outer_join=retirement['postjoin'],common_record_sha256=retirement['common']['sha256'],shared_record_sha256=retirement['shared']['sha256'])
    objects=m.parse(stable_bytes(OBJECT_AUTHORITY,OBJECT_AUTHORITY_SHA))
    need(retirement['cleanup_authorized'] is False and retirement['status']=='PASS_ORDINARY_PHYSICAL_RECORD_JOIN_ONLY' and retirement['lease_absent'] is True and retirement['client_count']==len(PIDS),'exact new physical retirement record join required')
    need(not OUTPUT.exists(),'fresh observation nonce required')
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
        m.BOOT_ID=BOOT;m.OWNER_PID=retirement['target']['owner_pid'];m.OWNER_START=retirement['target']['owner_starttime'];m.WAITER_PIDS=PIDS
        def process_snapshot():
            caller=[os.getpid(),Path('/proc/self/stat').read_bytes().rpartition(b') ')[2].split()[19].decode('ascii')]
            old=sys.argv;out=io.StringIO()
            try:
                sys.argv=['readonly-process',NONCE,str(caller[0]),caller[1]]
                with contextlib.redirect_stdout(out):
                    exec(compile(m.PROC_CODE,'<accepted cleanup read-only PROC_CODE>','exec'),{'__name__':'_readonly_process'})
            finally:
                sys.argv=old
            raw=out.getvalue().encode();need(len(raw)<=m.LIMIT,'process observation bound')
            m.validate_process_report(m.parse(raw),NONCE,caller)
            store('process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')]),raw)
        m.process_absent=process_snapshot
        mount_raw=capture_command(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],m.LIMIT)
        mounts=m.parse(mount_raw)['filesystems'];need(len(mounts)==1,'one scratch mount required')
        mount=mounts[0]
        need(mount['uuid']==m.UUID and mount['target']==str(ROOT) and mount['source']=='/dev/loop36' and mount['maj:min']=='7:36','scratch mount differs')
        owner=m.parse(stable_bytes(Path(retirement['owner']['path']),retirement['owner']['sha256']))
        guard=m.parse(stable_bytes(Path(retirement['guard']['path']),retirement['guard']['sha256']))
        old_inspect=m.parse(stable_bytes(Path(retirement['terminal_inspection']['path']),retirement['terminal_inspection']['sha256']))
        target=dict(m.KNOWN_TARGET,image_id=old_inspect['Image'],exit_code=0)
        m.validate_attempt_binding(target,dict(path=str(m.REQUEST),sha256=m.REQUEST_SHA))
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=0;m.EXPECTED_CONTAINER=old_inspect
        need(m.census(),'retained exact terminal container required')
        inspection=m.parse(m.docker(['inspect','--type','container',target['container_id']]))[0]
        m.validate_container_profile(inspection)
        m.image_receipt_binding(owner,guard,target,inspection,retirement['owner']['sha256'])
        statuses=sorted(CAPTURE.glob('command-*/status.json'));ledger=[]
        selected_paths={m.REQUEST,m.TERMINAL,Path(retirement['guard']['path']),Path(retirement['terminal_inspection']['path']),Path(retirement['outer_join']['path']),m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json',m.OUTPUT/'output/build/kernel/mckernel.img',m.OUTPUT/'evidence/artifacts/mckernel.img',Path(objects['source']['path']),Path(objects['retained_destination']['path']),RETIREMENT,OBJECT_AUTHORITY}
        selected_paths.update(Path(p) for p in ['/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_build_container_owner.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_build_image_prepare.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_build_image_rebind.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_build_image_rebind_probe.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_build_offline.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_disk_build_wrapper.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_mckernel_image_container_owner.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_mckernel_image_offline.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/adapters/native_rust_exact_mckernel_image_request_prepare.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/gitlink-inputs.json', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/heavy-proposal-1/native_exact_scratch22_authority3_image_guard.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/heavy-proposal-1/test_packet_joins.py', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/image-request.json', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/image-toolchain.json', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/materialization-receipt.json', '/home/holden/mckernel-work/host-preparation/rust-clear-debugreg-image-preparation-20261018-1/thin-inputs.json'])
        for object_pair in new_objects:
            need(isinstance(object_pair,dict) and object_pair['outside_generic_receipt_inventory'] is True,'explicit new object pair required')
            selected_paths.update(Path(object_pair[k]['path']) for k in ('original','retained'))
        for path in statuses:
            row=m.observe_identity(path);status=m.parse(m.read_bounded(path))
            need(status.get('state')=='exited' and status.get('exit_code')==0 and status.get('pid') in PIDS and not status.get('client_retirement_unproven'),'positive original client ledger required')
            ledger.append(dict(pid=status['pid'],status_path=str(path),status_sha256=row['sha256']))
            selected_paths.update((path,path.parent/'stdout',path.parent/'stderr'))
        need({r['pid'] for r in ledger}==set(PIDS) and len(ledger)==8,'all exact eight original clients required')
        for pair in new_objects:
            need((pair['original']['device'],pair['original']['inode'])!=(pair['retained']['device'],pair['retained']['inode']) and pair['original']['nlink']==pair['retained']['nlink']==1,'independent single-link retained production artifact required')
        new_object_metadata=[new_object_binding(m,pair[key]) for pair in new_objects for key in ('original','retained')]
        store('new-object-metadata.json',m.canonical(dict(authority_path=str(NEW_OBJECT_AUTHORITY),authority_sha256=NEW_OBJECT_AUTHORITY_SHA,objects=new_object_metadata)))
        selected_paths.add(OUTPUT/'new-object-metadata.json')
        selected=[m.observe_identity(path) for path in sorted(selected_paths)]
        selected_map={row['path']:row for row in selected}
        for key in ('source','retained_destination'):
            row=objects[key];fresh=selected_map[row['path']]
            need(fresh['sha256']==row['sha256'] and fresh['size']==row['size'] and fresh['device']==row['device'] and fresh['inode']==row['inode'],'both exact process objects must remain retained')
        for object_pair in new_objects:
            for key in ('original','retained'):
                row=object_pair[key];fresh=selected_map[row['path']]
                need(all(fresh[k]==row[k] for k in ('sha256','size','device','inode','mode')),'new CPU/process original or retained object differs')
        images=[selected_map[str(m.OUTPUT/relative)] for relative in ('output/build/kernel/mckernel.img','evidence/artifacts/mckernel.img')]
        need(images[0]['sha256']==images[1]['sha256']==retirement['image_sha256'],'both published images differ')
        need(selected_map[str(m.REQUEST)]['sha256']==m.REQUEST_SHA,'request bytes differ')
        records=[m.observe_identity(path) for path in (m.ATTEMPT,m.SHARED)]
        need([row['sha256'] for row in records]==[retirement['common_record_sha256'],retirement['shared_record_sha256']],'retained exclusion bytes differ')
        need(not os.path.lexists(m.LEASE),'request lease reappeared')
        request=m.parse(m.read_bounded(m.REQUEST))
        m.image_request_binding(request)
        observation=dict(mount=mount,root=m.observe_identity(ROOT),boot_id=BOOT,root_lock=lock,request=selected_map[str(m.REQUEST)],target=target,container_inspect=inspection,retained_exclusions=records,request_lease_absent=True,inventories={str(p):m.metadata_inventory(p) for p in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(Path(request['source_root'])),candidate_commit=m.IMAGE_CANDIDATE,candidate_tree=None,selected_files=selected,backup_root=m.observe_identity(ROOT/'mckernel-exact-candidate-scratch-22-authority3-metadata-backup'),namespace_binding=m.NAMESPACE_BINDING,namespace_ancestry=m.NAMESPACE_ANCESTRY,client_ledger=ledger,guard_proof=selected_map[str(CAPTURE/'guard-result.json')])
        # No configure/cleanup call: prepare_release only binds these bytes.
        need(m.census(),'terminal container changed during read-only observation')
        need(m.namespace_ancestry()==m.NAMESPACE_ANCESTRY and Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT,'post-observation ancestry/boot changed')
        for path in (m.OUTPUT,m.EVIDENCE):
            need(m.metadata_inventory(path)==observation['inventories'][str(path)],'preserved output metadata changed')
        for row in selected:
            need(m.observe_identity(Path(row['path']))==row,'selected input/artifact changed')
        repeated_object_metadata=[new_object_binding(m,pair[key]) for pair in new_objects for key in ('original','retained')]
        need(repeated_object_metadata==new_object_metadata,'new object metadata changed during observation')
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
