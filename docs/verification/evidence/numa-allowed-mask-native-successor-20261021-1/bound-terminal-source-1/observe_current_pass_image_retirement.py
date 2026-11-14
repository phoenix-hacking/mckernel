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



FAILURE_CASE = Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/PASS-CASE-STATIC.json')
FAILURE_CASE_SHA = '6422685923bf3c6bac434c47a5771ecdaec491656d0c2e402866170da6e906ca'
REPO = Path('/home/holden/mckernel')
ROOT = Path('/home/holden/mckernel-work/scratch')
PREP = Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1')
CASE = Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/full-image-attempt-1')
CAPTURE = Path('/home/holden/mckernel-work/scratch/native-rust-phase5-current-optin-image-guard-d37f2175c1c049869e4a5872de864858')
SOURCE = Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-native-successor-preparation-20261021-1/bound-terminal-source-1/cleanup_pass_image.py')
TEST = Path('/home/holden/mckernel/scripts/tests/test_native_rust_cutover_image_terminal_cleanup.py')
SOURCE_SHA = '25e8657a301c6d486833de7bf8f6cdd7ebc360d9930a997809b3089b16551633'
TEST_SHA = '2fba315ad96f271124cf78f7441faa306f58ea03ae35cdbe78bba5be6488d630'
RETIREMENT = Path('/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/independent-runtime-binding-review-1/ROOT-RECORDED-INDEPENDENT-CURRENT-IMAGE-RETAINED-PHYSICAL-ACCEPTANCE.json')
RETIREMENT_SHA = '3351eefc3df372220d7a32c20932fa20f8143d466786f0d21bcb1d6e400e1b3f'
NONCE = 'numa-allowed-mask-pass-image-observation-1'
OUTPUT = PREP / ('root-observation-' + NONCE)
BOOT = '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'
PIDS = (2553251, 2556251, 2553176, 2556259, 2557124, 2553184, 2553192, 2553168)


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


TERMINAL_INSPECTION_SHA = 'd22352505a84fe5a8191bdc62f61f26e1764013cde84351e05dab0631af922c4'

OBSERVATION_COMMAND = ['/usr/bin/sudo','-A','/home/holden/anaconda3/bin/python3','-I','-B',str(Path(__file__).resolve())]
OBSERVATION_PROFILE = dict(metadata_soft_as=268435456,metadata_hard_as=2147483648,only_exact_docker_child_soft_as=2147483648,command_timeout_seconds=30,output_limit_bytes=1048576,selected_hash_cap_bytes=134217728,inventory_cap=400000)

def canonical_payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def validate_observation_release(path, expected, commit, tree):
    release=json.loads(stable_bytes(path,expected))
    need(release.get('schema')=='mckernel.phase5.current-pass-image.readonly-observation-release.v1' and
         release.get('status')=='PASS_EXECUTION_RELEASE' and release.get('cleanup_authorized') is False and
         release.get('fetched_source_verified') is True and release.get('git_commit')==commit and
         release.get('git_tree')==tree and release.get('nonce')==NONCE and
         release.get('output')==str(OUTPUT) and release.get('observer_sha256')==sha(Path(__file__).read_bytes()) and
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





PENDING_BINDINGS = ()

def current_pass_prerequisites(retirement,case,root_join,artifact):
    """Decode genuine retained physical and separate producer-artifact authority."""
    need(retirement['schema']=='mckernel.numa-current-image.retained-terminal-postjoin-review.v1' and
         retirement['status']=='PASS_ACTUAL_IMAGE_TERMINAL_RETAINED_POSTJOIN_SCOPE_ONLY' and
         retirement['build_status']=='PASS' and retirement['retired'] is True and
         retirement['terminal_container_retained'] is True and retirement['cleanup_separately_required'] is True and
         retirement['physical_release'] is False and retirement['record_release_complete'] is False and
         retirement['request_lease_absent'] is True and retirement['outer_direct_joined'] is True and
         retirement['outer_group_absent'] is True and retirement['root_mutex_reacquired_after_guard_join'] is True and
         retirement['exact_terminal_exit0_nonOOM_PID0'] is True and retirement['closed_saved_host_client_count']==8,
         'exact current retained PASS physical authority required')
    need(case['execution_authorized'] is False and case['successful_artifacts_required'] is True and
         case['target']['exit_code']==0,'current PASS case only')
    for key in ('container_id','container_name','owner_nonce','owner_pid','owner_starttime'):
        need(retirement[key]==case['target'][key],'retained target mismatch:'+key)
    for key,role in (('owner_receipt','owner_receipt'),('guard_result','guard_result'),
                     ('outer_status','outer_status'),('inner_status','inner_status'),
                     ('terminal_fresh_inspect','terminal_inspection')):
        need(retirement[key]==case['finite_roles'][role],'retained receipt/source mismatch:'+key)
    need(case['artifact_acceptance']==case['finite_roles']['artifact_acceptance'],
         'exact bound artifact reference differs')
    need(artifact['schema']=='mckernel.current-numa-scheduler.production-image-artifact-review.v1' and
         artifact['status']=='PASS_CURRENT_IMAGE_BUILD_LINK_AND_NAMED_BOUNDARIES_NO_NATIVE_ACCEPTANCE' and
         artifact['decision']=='PASS_ACTUAL_CURRENT_NUMA_SCHEDULER_IMAGE_AND_REAL_MCEEXEC_LINK_ARTIFACTS_ONLY' and
         artifact['implementation_ownership'] is False and isinstance(artifact['reviewer'],str) and
         bool(artifact['reviewer']) and artifact['physical_clearance'] is False,
         'separate genuine current NUMA/scheduler artifact authority required')
    need(artifact['producer_receipt']==case['finite_roles']['driver_receipt'],
         'genuine artifact producer receipt differs')
    for key in ('source_derivative_sha256','materialization_sha256'):
        need(artifact[key]==retirement[key]==case['source_identity'][key],
             'physical/artifact source fingerprint differs:'+key)
    need(root_join['status']=='PASS_ORDINARY_GUARD_POSTJOIN_READBACK_ONLY' and
         root_join['root27_4_reacquired_after_join'] is True and root_join['guard_direct_joined'] is True and
         root_join['common_shared_and_container_retained_for_separate_cleanup'] is True and
         root_join['cleanup_authorized'] is False and root_join['container_id']==case['target']['container_id'] and
         root_join['owner_receipt_sha256']==retirement['owner_receipt']['sha256'] and
         root_join['guard_result_sha256']==retirement['guard_result']['sha256'],'current guard postjoin mismatch')
    byrole={row['role']:row for row in case['full_original_record_authority']}
    need(set(byrole)==set(retirement['retained_ownership'])=={'common','shared'},
         'both original record authorities required')
    for role,expected in retirement['retained_ownership'].items():
        full=byrole[role]['full_descriptor']
        need(all(full[k]==v for k,v in expected.items()) and byrole[role]['sha256']==expected['sha256'],
             'complete retained record descriptor differs:'+role)
        record=byrole[role]['record']
        need(record['pid']==case['target']['owner_pid'] and record['starttime']==case['target']['owner_starttime'] and
             record['boot_id']==BOOT and record['inode']==expected['inode'] and
             record.get('dev',record.get('device'))==expected['device'],'retained record producer mismatch:'+role)
    need(case['source_identity']==CURRENT_EXPECTED_SOURCE,'exact frozen current source required')


CURRENT_EXPECTED_SOURCE = {'candidate_identity_scope': 'base_git_commit_only', 'candidate_sha': '942c927b1ec93cc31284ff498455909d9bb2d0fc', 'materialization_sha256': '317752dc9138cde2aac932da3b9e1b3e7f3434379361778a6aff035b2d46c44c', 'source_derivative_sha256': '050b953f46ff55f5ec819923819096fde8688400d860f7e666db9bbddb5b3f44', 'source_identity': {'dev': 66306, 'file_type': 16384, 'gid': 1000, 'inode': 48501031, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/source-materialization-1/materialized-source', 'uid': 1000}, 'source_root': '/home/holden/mckernel-work/host-preparation/numa-allowed-mask-image-successor-preparation-20261021-1/source-materialization-1/materialized-source'}

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
    case=m.parse(stable_bytes(FAILURE_CASE,FAILURE_CASE_SHA,4<<20))
    root_join=json.loads(stable_bytes(Path(case['current_live_postjoin']['path']),case['current_live_postjoin']['sha256']))
    artifact_ref=case['artifact_acceptance']
    artifact=json.loads(stable_bytes(Path(artifact_ref['path']),artifact_ref['sha256']))
    current_pass_prerequisites(retirement,case,root_join,artifact)
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
            raw=out.getvalue().encode();need(len(raw)<=m.LIMIT,'process observation bound')
            m.validate_process_report(m.parse(raw),NONCE,caller)
            store('process-%02d.json'%len([p for p in OUTPUT.iterdir() if p.name.startswith('process-')]),raw)
        m.process_absent=process_snapshot
        mount_raw=capture_command(['/usr/bin/findmnt','-J','-T',str(ROOT),'-o','TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],m.LIMIT)
        mounts=m.parse(mount_raw)['filesystems'];need(len(mounts)==1,'one scratch mount required')
        mount=mounts[0]
        need(mount['uuid']==m.UUID and mount['target']==str(ROOT) and mount['fstype']=='ext4' and {'rw','nodev','nosuid'}<=set(mount['options'].split(',')),'scratch mount differs')
        owner=m.parse(stable_bytes(Path(retirement['owner_receipt']['path']),retirement['owner_receipt']['sha256']))
        guard=m.parse(stable_bytes(Path(retirement['guard_result']['path']),retirement['guard_result']['sha256']))
        old_inspect=m.parse(stable_bytes(Path(retirement['terminal_fresh_inspect']['path']),retirement['terminal_fresh_inspect']['sha256']))
        target=dict(case['target']);need(target['image_id']==old_inspect['Image'],'actual current PASS image identity')
        m.validate_attempt_binding(target,dict(path=str(m.REQUEST),sha256=m.REQUEST_SHA))
        m.CONTAINER=target['container_id'];m.CONTAINER_NAME=target['container_name'];m.OWNER_NONCE=target['owner_nonce'];m.EXPECTED_EXIT=target['exit_code'];m.EXPECTED_CONTAINER=old_inspect
        need(m.census(),'retained exact terminal container required')
        inspection=m.parse(m.docker(['inspect','--type','container',target['container_id']]))[0]
        m.validate_container_profile(inspection)
        m.image_receipt_binding(owner,guard,target,inspection,retirement['owner_receipt']['sha256'])
        statuses=sorted(CAPTURE.glob('command-*/status.json'));ledger=[]
        selected_paths={Path(p) for p in case['finite_unique_paths']}
        selected_paths.update((SOURCE,TEST,FAILURE_CASE))
        need(set(selected_paths)>={m.REQUEST,m.TERMINAL,m.EVIDENCE/'attempt/container.log',m.OUTPUT/'evidence/receipt.json'},'PASS image minimum receipt roles')
        for path in statuses:
            row=m.observe_identity(path);status=m.parse(m.read_bounded(path))
            need(status.get('state')=='exited' and status.get('exit_code')==0 and status.get('pid') in PIDS and not status.get('client_retirement_unproven'),'positive original client ledger required')
            ledger.append(dict(pid=status['pid'],status_path=str(path),status_sha256=row['sha256']))
            selected_paths.update((path,path.parent/'stdout',path.parent/'stderr'))
        need({r['pid'] for r in ledger}==set(PIDS) and len(ledger)==len(PIDS),'all exact current original clients required')
        # Current successful primary/evidence artifacts are exact finite roles bound by the actual producer.
        # Store the finite selected role descriptors, preserving the original five-file export shape.
        finite_metadata=[m.observe_identity(Path(p)) for p in case['finite_unique_paths']]
        for row in finite_metadata:
            refs=[v for v in case['finite_roles'].values() if v['path']==row['path']]
            need(refs and all(row['sha256']==v['sha256'] and row['size']==v['bytes'] for v in refs),'closed PASS role bytes differ')
        store('new-object-metadata.json',m.canonical(dict(authority_path=str(FAILURE_CASE),authority_sha256=FAILURE_CASE_SHA,objects=finite_metadata,successful_artifacts_required=True)))
        selected_paths.add(OUTPUT/'new-object-metadata.json')
        selected=[m.observe_identity(path) for path in sorted(selected_paths)]
        selected_map={row['path']:row for row in selected}
        need(selected_map[str(m.REQUEST)]['sha256']==m.REQUEST_SHA,'request bytes differ')
        records=[m.observe_identity(path) for path in (m.ATTEMPT,m.SHARED)]
        need([row['sha256'] for row in records]==[retirement['retained_ownership']['common']['sha256'],retirement['retained_ownership']['shared']['sha256']],'retained exclusion bytes differ')
        for row,role in zip(records,('common','shared')):
            need(row==retirement['retained_ownership'][role],'retained full record identity differs:'+role)
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
        need([m.observe_identity(Path(p)) for p in case['finite_unique_paths']]==finite_metadata,'finite PASS role metadata changed during observation')
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
