#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One frozen290 image operation: ordinary observations, actual flock, external
closed census + independent review, then the unchanged image owner. No retries,
compiler implementation, launcher or root-query engine is introduced here.
"""
import ast
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import time

D = Path(__file__).resolve().parent
CONFIG = D / 'FROZEN-CURRENT290-IMAGE-ENTRY-INPUTS.FINAL-ACTUAL69-9793-84DA-22_0485.json'
CONFIG_SHA = 'c262cec7a1c8a51a86effb8f600c27f499e3ea871b0fe3554e8cda7db3d4e626'
LOCK = Path('/run/lock/mckernel-development.lock')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def need(value, message):
    if not value:
        raise RuntimeError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def reference(path):
    path = Path(path)
    return dict(path=str(path), sha256=digest(path), bytes=path.stat().st_size)


def authenticate(row):
    path = Path(row['path'])
    need(reference(path) == row, 'exact source/metadata reference: ' + str(path))
    return path


def actual_config(path, checksum):
    """Late-bind only genuine fetched-publication metadata, never image inputs."""
    need(digest(CONFIG) == CONFIG_SHA, 'immutable base input configuration')
    need(digest(path) == checksum, 'exact root actual configuration SHA')
    base = strict(CONFIG)
    current = strict(path)
    need({k: v for k, v in current.items() if k != 'publication'} ==
         {k: v for k, v in base.items() if k != 'publication'},
         'only publication reference may differ from immutable image configuration')
    need(set(current['publication']) == {'path', 'sha256', 'bytes'}, 'exact publication reference fields')
    authenticate(current['publication'])
    return current


def strict(path, maximum=1 << 20):
    path = Path(path)
    def pairs(items):
        result = {}
        for key, value in items:
            need(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= maximum,
             'bounded unique regular metadata')
        raw = bytearray()
        while len(raw) <= maximum:
            block = os.read(fd, min(65536, maximum + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        identity = lambda m: (m.st_dev, m.st_ino, m.st_mode, m.st_nlink, m.st_uid, m.st_gid,
                              m.st_size, m.st_mtime_ns, m.st_ctime_ns)
        need(len(raw) == before.st_size and identity(os.fstat(fd)) == identity(before) and
             identity(os.stat(path, follow_symlinks=False)) == identity(before), 'stable metadata identity')
    finally:
        os.close(fd)
    return json.loads(raw, object_pairs_hook=pairs,
                      parse_constant=lambda _: (_ for _ in ()).throw(RuntimeError('nonfinite JSON')))


def publish(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    need(len(raw) < 1 << 20, 'compact caller receipt')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, 'wb', closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(fd)
    finally:
        os.close(fd)
    return reference(path)


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True, allow_nan=False) + '\n').encode()


def birth(pid):
    return Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]


def lock_functions(source):
    """Reuse these two existing functions without importing the old build owner."""
    raw = authenticate(source).read_bytes()
    body = [n for n in ast.parse(raw).body if isinstance(n, ast.FunctionDef) and
            n.name in {'identity', 'acquire_development_lock'}]
    need(len(body) == 2, 'exact existing lock primitives')
    ns = dict(os=os, stat=stat, fcntl=fcntl, LOCK=LOCK, Refusal=RuntimeError)
    exec(compile(ast.Module(body=body, type_ignores=[]), source['path'], 'exec'), ns)
    return ns


def check_held(fd, expected, identity):
    meta = os.fstat(fd)
    need(stat.S_ISREG(meta.st_mode) and meta.st_size == 0 and
         identity(meta) == expected == identity(os.stat(LOCK, follow_symlinks=False)),
         'same actual held FD and named permanent mutex identity')


def fresh(five_end, census_end, now=None):
    now = time.time() if now is None else now
    need(all(type(x) in (int, float) and 0 <= now - x <= 120
             for x in (five_end, census_end)), 'actual five and census <=120-second freshness')


def execution_grant(grant, review, payload_reference, payload, holder, argv, caller_sha, cfg, config_sha=CONFIG_SHA):
    need(grant['author'] == '/root' and grant['decision'] == 'GRANT_ONE_CURRENT290_IMAGE_OWNER' and
         grant['caller_sha256'] == caller_sha and grant['payload'] == payload_reference and
         grant['owner_argv'] == argv and grant['holder'] == holder and
         grant['actual_no_other_heavy'] is True and grant['no_heavy_since_latest_physical'] is True and
         grant['operation_scope'] == cfg['operation_scope'], 'genuine exact root execution grant')
    need(review['decision'] == 'PASS_EXECUTION' and review['implementation_ownership'] is False and
         review['reviewer'] not in ('/root', '', None) and review['caller_sha256'] == caller_sha and
         review['config_sha256'] == config_sha and review['metadata_fill_sha256'] == cfg['fill']['sha256'] and
         review['operation_scope'] == cfg['operation_scope'] and
         review['reviewed_release_payload_sha256'] == hashlib.sha256(canonical(payload)).hexdigest(),
         'independent exact final image-only execution review')


def cleanup_command_grant(command, review, owner_reference, owner_receipt, holder, admitted_source):
    target = {key: owner_receipt[key] for key in ('container_id', 'container_name', 'owner_nonce')}
    need(command['author'] == '/root' and command['decision'] == 'GRANT_EXISTING_NORMAL_CLEANUP' and
         command['holder'] == holder and command['owner_receipt'] == owner_reference and
         command['target'] == target and command['source'] == admitted_source and
         command['stdin_from_holder_fd'] == holder['fd'] and command['cleanup_held_fd'] == 0 and
         command['same_OFD_transport'] == 'STDIN_FD0_SUDO_A', 'exact root cleanup command/target/same-OFD transport')
    authenticate(command['source']); authenticate(command['request'])
    need(command['source']['path'] in command['argv'] and '/usr/bin/sudo' in command['argv'] and
         '-A' in command['argv'] and '-C' not in command['argv'], 'exact reviewed existing sudo-A cleanup entry')
    need(review['decision'] == 'PASS_EXISTING_SAME_OFD_NORMAL_CLEANUP_EXECUTION' and
         review['implementation_ownership'] is False and review['reviewer'] not in ('/root', '', None) and
         review['same_OFD_cleanup_compatibility_reviewed'] is True and
         review['reviewed_cleanup_command_payload_sha256'] == hashlib.sha256(canonical(
             {k: v for k, v in command.items() if k != 'independent_review'})).hexdigest(),
         'independent exact existing cleanup source/request/argv/held-stdin review')
    return command['argv']


def cleanup_completion(completion, review, owner_reference, owner_receipt, holder,
                       admitted_source, actual_command_reference, actual_join_reference):
    """Authenticate CONTROL metadata; actual protocol semantics need review.

    This is not a generic cleanup-result schema/parser. The selected EXISTING
    cleanup source must be independently reviewed for same-OFD compatibility;
    its genuine result and protocol-specific postflight bytes stay untouched.
    Mere root intent or an owner-only retired receipt cannot satisfy this gate.
    """
    target = {key: owner_receipt[key] for key in ('container_id', 'container_name', 'owner_nonce')}
    need(completion['author'] == '/root' and
         completion['decision'] == 'ACCEPT_EXISTING_NORMAL_CLEANUP_COMPLETED' and
         completion['holder'] == holder and completion['owner_receipt'] == owner_reference and
         completion['target'] == target, 'actual cleanup completion bound to same holder/owner')
    cleanup = completion['existing_cleanup']
    need(set(cleanup) == {'source', 'request', 'command', 'receipt', 'result', 'stdout', 'stderr', 'postflight'},
         'exact existing cleanup references; no intent-only handoff')
    need(cleanup['source'] == admitted_source and cleanup['command'] == actual_command_reference and
         cleanup['receipt'] == actual_join_reference, 'THIS actual selected cleanup command and join')
    for key in ('source', 'request', 'command', 'receipt', 'result', 'stdout', 'stderr'):
        authenticate(cleanup[key])
    need(isinstance(cleanup['postflight'], list) and cleanup['postflight'],
         'actual protocol-specific postflight references required')
    for row in cleanup['postflight']:
        authenticate(row)
    command = strict(cleanup['command']['path'])
    joined = strict(cleanup['receipt']['path'])
    need(command['argv'] == completion['cleanup_argv'] and
         cleanup['source']['path'] in command['argv'] and cleanup['request'] == command['request'],
         'exact selected existing cleanup source/request/argv')
    need(joined['returncode'] == 0 and joined['direct_child_joined'] is True and
         joined['group_absent'] is True and joined['closed_streams'] is True and
         joined['error'] is None and joined['retirement_error'] is None,
         'existing cleanup actually successful and fully joined')
    need(joined['captures']['stdout']['sha256'] == cleanup['stdout']['sha256'] and
         joined['captures']['stderr']['sha256'] == cleanup['stderr']['sha256'] and
         cleanup['stderr']['bytes'] == 0, 'existing cleanup exact closed streams')
    need(review['decision'] == 'PASS_EXISTING_NORMAL_CLEANUP_COMPLETE' and
         review['implementation_ownership'] is False and review['reviewer'] not in ('/root', '', None) and
         review['same_OFD_cleanup_compatibility_reviewed'] is True and
         review['reviewed_cleanup_completion_payload_sha256'] == hashlib.sha256(canonical(
             {k: v for k, v in completion.items() if k != 'independent_review'})).hexdigest(),
         'independent exact existing protocol/result/postflight/same-OFD completion review')
    need(owner_receipt.get('retired') is True and
         owner_receipt.get('client_retirement_unproven') is not True,
         'uncertain owner cannot release held mutex')
    return cleanup


def wait_record(path, five_end, deadline):
    while not os.path.lexists(path):
        need(time.time() < deadline and 0 <= time.time() - five_end <= 120,
             'stop stale preparation without query replay')
        time.sleep(0.2)
    return strict(path)


def wait_cleanup_record(path, fd, expected, identity):
    # Ownership has already been acquired: elapsed time never unlocks it.
    while not os.path.lexists(path):
        check_held(fd, expected, identity)
        time.sleep(0.1)
    check_held(fd, expected, identity)
    return strict(path)


def captured(command, root, name, pass_fds=(), stdin_fd=None):
    """No outer timeout/CPU kill, as in existing run_checked primitive."""
    out = root / (name + '.stdout')
    err = root / (name + '.stderr')
    started = time.time()
    with out.open('xb') as stdout, err.open('xb') as stderr:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL if stdin_fd is None else stdin_fd, stdout=stdout,
                                   stderr=stderr, close_fds=True, pass_fds=pass_fds,
                                   start_new_session=True)
        start = birth(process.pid)
        publish(root / (name + '.PROCESS.json'), dict(argv=command, pid=process.pid,
                starttime=start, pgid=process.pid, parent_pid=os.getpid(),
                started_at_epoch=started, inherited_fds=list(pass_fds), stdin_from_parent_fd=stdin_fd))
        while True:
            try:
                rc = process.wait()
                break
            except InterruptedError:
                continue
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        absent = True
    else:
        absent = False
    receipt = dict(argv=command, pid=process.pid, starttime=start,
                   returncode=rc, direct_child_joined=True, group_absent=absent,
                   closed_streams=True, started_at_epoch=started,
                   finished_at_epoch=time.time(), stdout=reference(out), stderr=reference(err),
                   error=None, retirement_error=None,
                   captures={'stdout': reference(out), 'stderr': reference(err)})
    publish(root / (name + '.JOIN.json'), receipt)
    need(absent, 'child process group must be absent')
    return receipt


def immediate(cfg, payload, fill, fd, identity):
    check_held(fd, cfg['permanent_mutex'], identity)
    for row in cfg['pins'].values():
        authenticate(row)
    fill.fetched(Path(cfg['publication']['path']), cfg['publication']['sha256'])
    mem = int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines()
                   if x.startswith('MemAvailable:'))) * 1024
    hostv = os.statvfs('/home/holden')
    scratchv = os.statvfs('/home/holden/mckernel-work/scratch')
    backing = Path('/home/holden/mckernel-work/scratch.ext4').stat()
    need(backing.st_size == 118111600640, 'unchanged backing size')
    gap = max(0, backing.st_size - 512 * backing.st_blocks)
    required = max(50248630272, (16 << 30) + gap + (4 << 30) + (640 << 20))
    values = dict(MemAvailable=mem, HOST_available=hostv.f_bavail * hostv.f_frsize,
                  HOST_required=required, scratch_available=scratchv.f_bavail * scratchv.f_frsize,
                  scratch_required=14091616256, full_sparse_gap=gap)
    need(mem >= 25501368320 and values['HOST_available'] >= required and
         values['scratch_available'] >= 14091616256, 'fresh complete entry floors')
    paths = fill.EXPECTED_NAMESPACE
    root = Path(paths[0])
    need(sorted(os.listdir(root)) == ['owner-evidence', 'owner-work'], 'same fresh attempt root')
    for path in paths[1:3]:
        meta = os.lstat(path)
        need(stat.S_ISDIR(meta.st_mode) and stat.S_IMODE(meta.st_mode) == 0o700 and
             meta.st_uid == meta.st_gid == 1000 and os.listdir(path) == [], 'empty private namespaces')
    need(all(not os.path.lexists(path) for path in paths[3:]), 'no shared/common/lease/owner namespaces')
    request = strict(cfg['pins']['request']['path'], 32 << 20)
    source = Path(request['source_root']); meta = os.lstat(source)
    expected = request['source_identity']
    need(meta.st_dev == expected['dev'] and meta.st_ino == expected['inode'] and
         stat.S_IMODE(meta.st_mode) == expected['mode'] and meta.st_uid == meta.st_gid == 1000,
         'exact frozen290 materialized source identity')
    need(payload['current_physical'] == cfg['physical'] and
         payload['current_live_postjoin'] == cfg['postjoin'], 'latest admitted typed physical references')
    return values


def execute(preparation_grant_path, actual_config_path, actual_config_sha):
    cfg = actual_config(actual_config_path, actual_config_sha)
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {7}, 'ordinary CPU7 caller')
    need(resource.getrlimit(resource.RLIMIT_CPU) == (resource.RLIM_INFINITY, resource.RLIM_INFINITY),
         'no inherited outer CPU kill')
    need(time.time() < cfg['deadline_epoch'] - 30, 'before fixed admission deadline')
    prep = strict(preparation_grant_path)
    need(prep['author'] == '/root' and prep['decision'] == 'GRANT_CURRENT290_READONLY_PREPARATION' and
         prep['caller_sha256'] == digest(__file__) and prep['config_sha256'] == actual_config_sha,
         'genuine root exact preparation grant required')
    authenticate(prep['census_observer'])
    authenticate(prep['existing_cleanup_source'])
    cleanup_source_review = strict(authenticate(prep['existing_cleanup_source_review']))
    need(cleanup_source_review['decision'] == 'PASS_SOURCE_EXISTING_SAME_OFD_IMAGE_CLEANUP' and
         cleanup_source_review['implementation_ownership'] is False and
         cleanup_source_review['reviewer'] not in ('/root', '', None) and
         cleanup_source_review['source'] == prep['existing_cleanup_source'] and
         cleanup_source_review['same_OFD_transport'] == 'STDIN_FD0_SUDO_A',
         'existing compatible cleanup entry independently source-reviewed BEFORE observations')
    for row in list(cfg['pins'].values()) + [cfg['interpreter'], cfg['taskset'], cfg['fill'],
                                             cfg['physical'], cfg['postjoin'], cfg['publication']]:
        authenticate(row)
    context = strict(authenticate(prep['context']))
    need(context['author'] == '/root' and context['aggregate']['actual_no_other_heavy'] is True and
         context['continuity']['no_heavy_since_latest_physical'] is True and
         context['actual_current_physical'] == cfg['physical'] and
         context['actual_current_live_postjoin'] == cfg['postjoin'], 'actual root continuity before observations')
    spec = importlib.util.spec_from_file_location('exact_current290_metadata_only', cfg['fill']['path'])
    fill = importlib.util.module_from_spec(spec); spec.loader.exec_module(fill)
    fill.fetched(Path(cfg['publication']['path']), cfg['publication']['sha256'])
    root = Path(cfg['capture_root']); root.mkdir(mode=0o700)
    publish(root / 'PREPARATION-GRANT-REFERENCE.json', reference(preparation_grant_path))
    initialized = strict(authenticate(prep['namespace_initialization']))
    need(initialized['status'] == 'PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY' and
         initialized['request'] == cfg['pins']['request'] and initialized['owner'] == cfg['pins']['owner'] and
         [row['path'] for row in initialized['identities']] == fill.EXPECTED_NAMESPACE[:3],
         'actual reviewed harmless namespace preparation bound to frozen952/f368')
    for row in initialized['identities']:
        meta = os.lstat(row['path'])
        need(stat.S_ISDIR(meta.st_mode) and
             (meta.st_dev, meta.st_ino, stat.S_IMODE(meta.st_mode), meta.st_uid, meta.st_gid) ==
             (row['device'], row['inode'], row['mode'], row['uid'], row['gid']) and
             sorted(os.listdir(row['path'])) == row['entries'], 'same initialized empty namespace identities')
    need(initialized['identities'][0]['entries'] == ['owner-evidence', 'owner-work'] and
         initialized['identities'][1]['entries'] == initialized['identities'][2]['entries'] == [] and
         all(not os.path.lexists(path) for path in fill.EXPECTED_NAMESPACE[3:]),
         'driver-owned paths still absent; no namespace mutation at live clock')
    five = captured(cfg['commands']['five_observations']['argv'], root, 'five')
    need(five['returncode'] == 0, 'stop failed five-query capture')
    P = Path(cfg['P'])
    actual = strict(P / 'actual-readonly-admission-capture-1/ACTUAL-READONLY-RESULT.json')
    five_end = actual['finished_at_epoch']
    ns = lock_functions(cfg['lock_primitive'])
    fd = ns['acquire_development_lock']({'live_binding': {'root_lock': cfg['permanent_mutex']}})
    owner_started = False
    owner_joined = False
    deferred = []
    def defer(signum, frame):
        deferred.append(signum)
    for signum in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM, signal.SIGQUIT):
        signal.signal(signum, defer)
    try:
        check_held(fd, cfg['permanent_mutex'], ns['identity'])
        holder = dict(path=str(LOCK), identity=cfg['permanent_mutex'], fd=fd, pid=os.getpid(),
                      starttime=birth(os.getpid()), boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
                      acquired_at_epoch=time.time(), owner_relationship='actual still-live parent; same open file description passed to owner')
        holder.update(original_holder_fd=fd, transported_fd=0, transport='STDIN_FD0_SUDO_A')
        context['continuity']['permanent_mutex'] = dict(device=27, inode=4, campaign_holds_dev_flock=True)
        context['actual_devflock_holder'] = holder
        context_path = P / 'ROOT-CURRENT290-ACTUAL-FETCH-AND-DEVFLOCK-CONTEXT.ACTUAL.json'
        publish(context_path, context)
        prepare_argv = list(cfg['commands']['prepare_metadata']['argv'])
        prepare_argv[8:10] = [cfg['publication']['path'], cfg['publication']['sha256']]
        prepared = captured(prepare_argv, root, 'prepare')
        need(prepared['returncode'] == 0, 'stop metadata prepare failure')
        compact = P / 'COMPACT-C252-CENSUS-REQUEST.ACTUAL-FIVE-BOUND.NOT-GRANTED.json'
        census_argv = list(cfg['commands']['compact_census']['argv']); census_argv[-1] = digest(compact)
        publish(root / 'CENSUS-READY.json', dict(scope=SCOPE, argv=census_argv,
                compact_request=reference(compact), holder=holder,
                inherited_observer_affinity_must_include=[2, 3, 4, 5], caller_affinity_unchanged=[7],
                five_end_epoch=five_end, deadline_epoch=min(five_end + 120, cfg['deadline_epoch'] - 30)))
        closed = wait_record(root / 'ROOT-CENSUS-CLOSED.json', five_end, cfg['deadline_epoch'] - 30)
        need(closed['author'] == '/root' and closed['argv'] == census_argv and
             closed['source'] == cfg['commands']['compact_census']['source'] and
             closed['observer_source'] == prep['census_observer'], 'exact root observer census binding')
        receipt = strict(authenticate(closed['receipt']))
        need(receipt['returncode'] == 0 and receipt['direct_child_joined'] and receipt['group_absent'] and
             receipt['closed_streams'] and receipt.get('error') is None and receipt.get('retirement_error') is None,
             'genuine census closed capture')
        stdout = authenticate(closed['stdout']); stderr = authenticate(closed['stderr'])
        need(stderr.stat().st_size == 0 and receipt['captures']['stdout']['sha256'] == digest(stdout) and
             receipt['captures']['stderr']['sha256'] == digest(stderr), 'census authentic streams')
        census_end = closed['finished_at_epoch']; fresh(five_end, census_end)
        need(closed['started_at_epoch'] <= census_end <= time.time(), 'actual census clock range')
        finished_argv = list(cfg['commands']['finish_metadata']['argv']); finished_argv[-2:] = [str(stdout), digest(stdout)]
        finished = captured(finished_argv, root, 'finish')
        need(finished['returncode'] == 0, 'stop metadata finish failure')
        payload_path = P / 'ROOT-CURRENT290-IMAGE-ONLY-PAYLOAD.FINAL.NOT-RELEASED.json'
        payload = strict(payload_path)
        publish(root / 'INDEPENDENT-EXECUTION-REVIEW-READY.json', dict(scope=SCOPE,
                caller=reference(__file__), config=reference(actual_config_path), payload=reference(payload_path),
                canonical_payload_sha256=hashlib.sha256(canonical(payload)).hexdigest(),
                closed_census=reference(root / 'ROOT-CENSUS-CLOSED.json'), holder=holder,
                five_end_epoch=five_end, census_end_epoch=census_end,
                operation_scope=cfg['operation_scope']))
        grant = wait_record(root / 'ROOT-EXECUTION-GRANT.json', five_end, cfg['deadline_epoch'] - 30)
        review = strict(authenticate(grant['independent_review']))
        execution_grant(grant, review, reference(payload_path), payload, holder,
                        cfg['commands']['owner_entry_unchanged']['argv'], digest(__file__), cfg, actual_config_sha)
        need(review['existing_cleanup_source'] == prep['existing_cleanup_source'],
             'live execution review binds actual compatible cleanup source')
        need(not deferred, 'stop deferred signal before owner admission')
        resources = immediate(cfg, payload, fill, fd, ns['identity'])
        fresh(five_end, census_end)
        publish(root / 'ACTUAL-OWNER-ENTRY.json', dict(scope=SCOPE, entry_epoch=time.time(),
                caller_pid=os.getpid(), caller_starttime=birth(os.getpid()), holder=holder,
                actual_five_end_epoch=five_end, actual_census_end_epoch=census_end,
                root_execution_grant=reference(root / 'ROOT-EXECUTION-GRANT.json'),
                resources=resources, owner_argv=grant['owner_argv'], operation_scope=cfg['operation_scope']))
        owner_started = True
        result = captured(grant['owner_argv'], root, 'owner', pass_fds=(fd,))
        owner_joined = True
        owner_receipt_path = Path(fill.EXPECTED_NAMESPACE[2]) / 'owner-receipt.json'
        owner_receipt = strict(owner_receipt_path)
        publish(root / 'ROOT-NORMAL-CLEANUP-COMPLETION-READY.json', dict(scope=SCOPE,
                caller_pid=os.getpid(), holder=holder, owner_join=result,
                owner_receipt=reference(owner_receipt_path), deferred_signals=deferred,
                instruction='SAME actual flock remains held through separately-required cleanup. Root must select/review an existing cleanup entry compatible with this SAME OFD, then supply joined cleanup and protocol-specific postflight completion. Intent to take cleanup cannot release this FD.'))
        cleanup_command_path = root / 'ROOT-EXISTING-NORMAL-CLEANUP-COMMAND.json'
        command = wait_cleanup_record(cleanup_command_path, fd, cfg['permanent_mutex'], ns['identity'])
        command_review = strict(authenticate(command['independent_review']))
        cleanup_argv = cleanup_command_grant(command, command_review, reference(owner_receipt_path),
                                             owner_receipt, holder, prep['existing_cleanup_source'])
        check_held(fd, cfg['permanent_mutex'], ns['identity'])
        # Popen duplicates the already-held SAME OFD onto standard FD0. sudo-A
        # preserves FD0 and gets authentication separately through askpass.
        # No sudo-C, new lock open, LOCK_UN, permission change or temporary gap.
        cleanup_join = captured(cleanup_argv, root, 'cleanup', stdin_fd=fd)
        need(cleanup_join['returncode'] == 0, 'failed cleanup preserves held mutex')
        publish(root / 'ROOT-CLEANUP-JOINED-AWAITING-INDEPENDENT-COMPLETION.json', dict(scope=SCOPE,
                holder=holder, cleanup_command=reference(cleanup_command_path),
                cleanup_join=reference(root / 'cleanup.JOIN.json'),
                instruction='Still holding SAME OFD. Actual existing protocol result and postflight need independent completion acceptance.'))
        # Existing f368 reports terminal_container_info_current=False even after
        # retire(); keep that fact. Root must genuinely verify normal retirement
        # and completed separately-required cleanup, never infer it here.
        # No timeout unlock: pending, malformed or uncertain completion keeps
        # SAME OFD held. Deadline does not authorize releasing live ownership.
        completion = wait_cleanup_record(root / 'ROOT-EXISTING-NORMAL-CLEANUP-COMPLETE.json',
                                         fd, cfg['permanent_mutex'], ns['identity'])
        accepted = strict(authenticate(completion['independent_review']))
        cleanup_completion(completion, accepted, reference(owner_receipt_path), owner_receipt, holder,
                           prep['existing_cleanup_source'], reference(cleanup_command_path),
                           reference(root / 'cleanup.JOIN.json'))
        check_held(fd, cfg['permanent_mutex'], ns['identity'])
        publish(root / 'TERMINAL-CLEANUP-COMPLETE-FLOCK-RELEASE.json', dict(scope=SCOPE,
                status='EXISTING_NORMAL_CLEANUP_COMPLETE_EXACT_FLOCK_RELEASE',
                owner_join=result, cleanup_completion=reference(root / 'ROOT-EXISTING-NORMAL-CLEANUP-COMPLETE.json')))
        return result['returncode']
    except BaseException as exc:
        if owner_started:
            try:
                publish(root / 'OWNERSHIP-QUARANTINE.json', dict(scope=SCOPE,
                        reason=repr(exc), owner_started=True, owner_joined=owner_joined,
                        holder_pid=os.getpid(), holder_fd=fd,
                        instruction='Preserve actual flock and all exclusions; root-owned reconciliation required.'))
            finally:
                while True:
                    try:
                        time.sleep(0.5)
                    except BaseException:
                        pass
        raise
    finally:
        # Reached only before owner admission, or after actual normal cleanup.
        os.close(fd)


if __name__ == '__main__':
    need(len(sys.argv) == 4, 'exact root preparation grant path, actual config path and SHA arguments')
    raise SystemExit(execute(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]))
