"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Different-expert HOST adapter suffix02-19; reuse actual00/01, execute only on root's fresh grant.
"""
from pathlib import Path
import ast, builtins, dis, hashlib, importlib.util, json, os, resource, signal
import stat, subprocess, sys, time, types

P = Path(__file__).resolve().parent
A = P / 'actual-suffix-1'
H = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
READY_SHA = '00616cf05492639779ca69f5920f520f73abe125cd4d902088cdb621b63dfd7f'
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


need(sha(H) == HELPER_SHA, 'accepted h990 source')
functions = {'need', 'write', 'hashed', 'stop', 'cpu_used', 'members', 'process_start',
             'terminal_unreaped', 'wait_terminal', 'owned_capture'}
assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
nodes = []
for node in ast.parse(H.read_bytes()).body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        nodes.append(node)
    elif isinstance(node, ast.FunctionDef) and node.name in functions:
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in node.targets):
        nodes.append(node)
ns = {'__file__': str(H), 'subprocess': subprocess, 'stat': stat}
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(H), 'exec'), ns)


def required(code):
    names = {i.argval for i in dis.get_instructions(code) if i.opname == 'LOAD_GLOBAL'}
    for value in code.co_consts:
        if isinstance(value, types.CodeType):
            names.update(required(value))
    return names


for name in functions:
    need(not (required(ns[name].__code__) - set(ns) - set(vars(builtins))), 'helper globals: ' + name)
for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
    signal.signal(signum, ns['stop'])
write = ns['write']
os.umask(0o077)
A.mkdir(mode=0o700)  # One fresh namespace; never reuse old failed source/output.
records, objects, guards = [], {}, []
reused_count = 0
reused_artifacts = {}
failure, observation, stage = None, None, 'preflight'
begin = time.monotonic()
bound = {}


def bind(row):
    path = row['path']
    if path in bound:
        need(bound[path] == row['sha256'], 'consistent authority ' + path)
        return
    need(sha(path) == row['sha256'], 'exact held source/tool ' + path)
    bound[path] = row['sha256']


def headroom():
    used = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())['last_rate_limits']['primary']['usedPercent']
    need(used < 100, 'included-plan usage guard')
    mem = int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:'))) * 1024
    host = os.statvfs('/home/holden')
    scratch = os.statvfs('/home/holden/mckernel-work/scratch')
    backing = Path('/home/holden/mckernel-work/scratch.ext4').stat()
    gap = max(0, backing.st_size - backing.st_blocks * 512)
    facts = {'MemAvailable': mem, 'memory_required': 19 << 30,
             'HOST_available': host.f_bavail * host.f_frsize,
             'HOST_required': (16 << 30) + gap + (128 << 20) + 679477248,
             'scratch_available': scratch.f_bavail * scratch.f_frsize,
             'scratch_required': (12 << 30) + 679477248,
             'full_sparse_gap': gap, 'backing_size': backing.st_size,
             'backing_device': backing.st_dev, 'backing_inode': backing.st_ino,
             'included_used_percent': used, 'aggregate_jobs': 7}
    need(mem >= facts['memory_required'] and facts['HOST_available'] >= facts['HOST_required']
         and facts['scratch_available'] >= facts['scratch_required'], 'fresh aggregate/floors/fullgap')
    return facts


def competitors():
    allowed = {os.getpid()}
    pid = os.getppid()
    while pid > 1:
        allowed.add(pid)
        try:
            pid = int(Path('/proc/' + str(pid) + '/stat').read_text().rsplit(')', 1)[1].split()[1])
        except FileNotFoundError:
            break
    users, kernels = [], []
    for directory in Path('/proc').iterdir():
        if not directory.name.isdigit() or int(directory.name) in allowed:
            continue
        try:
            status = (directory / 'status').read_text()
            affinity = next(l.split(':', 1)[1].strip() for l in status.splitlines() if l.startswith('Cpus_allowed_list:'))
            state = next(l for l in status.splitlines() if l.startswith('State:'))
            if affinity != '6' or 'Z' in state:
                continue
            tail = (directory / 'stat').read_text().rsplit(')', 1)[1].split()
            ppid, flags = int(tail[1]), int(tail[6])
            status_ppid = int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')))
            row = {'pid': int(directory.name), 'start': int(tail[19]), 'PPid': ppid,
                   'flags': flags, 'comm': (directory / 'comm').read_text().strip()}
            if flags & 0x00200000 and ppid == status_ppid == 2:
                kernels.append(row)
            else:
                users.append(row)
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    need(not users, ('competing ordinary CPU6 userspace', users))
    return {'competing_userspace_CPU6': users, 'positive_PF_KTHREAD_PPid2_exemptions': kernels}


def stable(row):
    path = Path(row['path'])
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        need(stat.S_ISREG(st.st_mode), 'retained regular artifact')
        for key, attr in [('device','st_dev'),('inode','st_ino'),('uid','st_uid'),
                          ('gid','st_gid'),('nlink','st_nlink'),('size','st_size'),
                          ('mtime_ns','st_mtime_ns'),('ctime_ns','st_ctime_ns')]:
            need(row[key] == getattr(st, attr), ('retained FD/stat', key, str(path)))
        need(row['mode'] == oct(stat.S_IMODE(st.st_mode)), 'retained mode')
        after = path.lstat()
        need(all(getattr(st, key) == getattr(after, key) for key in ns['FIELDS']), 'retained stable FD/path')
    finally:
        os.close(fd)


def early_symbols(plan, label, text):
    # Same frozen observer predicates, checked at their earliest actual output.
    table = [line.split() for line in text.splitlines() if line.split()]

    def unique(name, kinds):
        rows = [row for row in table if row[-1] == name]
        need(len(rows) == 1 and rows[0][-2] in kinds, ('one expected symbol', name, rows))
        return rows[0]

    if label == '05-actual-Rust-symbols':
        for name in plan['oracles']['leaf_T']:
            unique(name, {'T'})
    elif label == '09-selected-cpu-ownership':
        for name in plan['oracles']['selected_C_T_absent']:
            need(not any(r[-1] == name and r[-2] in {'T', 't'} for r in table), 'selected C duplicate ' + name)
        for name in ['x86_int3_debug_print_enabled', 'x86_debug_handler_debug_print_enabled']:
            row = unique(name, {'R'})
            need(int(row[-3], 16) == 4, 'selected readonly datum R4')
    elif label == '09-fallback-cpu-ownership':
        for name in plan['oracles']['fallback_C_T_present']:
            unique(name, {'T'})
        for name in ['x86_int3_debug_print_enabled', 'x86_debug_handler_debug_print_enabled']:
            need(not any(r[-1] == name for r in table), 'fallback omits Rust config datum')


try:
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}, 'uid1000 exact CPU6')
    limits = [(resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60),
              (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
              (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)]
    for kind, value in limits:
        need(resource.getrlimit(kind) == (value, value), 'exact inherited limit ' + str(kind))
    need(os.environ.get('RUST_MIN_STACK') == '2097152', 'explicit Rust 2MiB stack')
    ready = P / 'EXACT-REMAINING18.NOT-GRANTED.CANONICAL-BOUND.json'
    need(sha(ready) == READY_SHA, 'frozen corrected twenty recipe')
    plan = json.loads(ready.read_bytes())
    need(plan['command_count'] == len(plan['commands']) == 20, 'exact twenty commands')
    gate = plan['operative_precondition']
    need(gate['canonical_equal_private_required'] is False, 'independent canonical/private gate')
    bind(gate['canonical_integration_root_receipt'])
    need(gate['root_confirmation_required_before_execution'] is False, 'genuine root canonical integration confirmed')
    for group in ['canonical_base_required', 'private_parent_required', 'candidate_required']:
        for row in gate[group].values():
            bind(row)
    for group in ['source_inputs', 'header_closure', 'tools']:
        for row in plan[group].values():
            bind(row)
    bind(plan['retained_observer'])
    spec = importlib.util.spec_from_file_location('f04_retained_observer', plan['retained_observer']['path'])
    observer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(observer)
    need(callable(observer.observe), 'actual pure observer entry')
    need(plan['remaining_command_count'] == len(plan['remaining_commands']) == 18, 'exact remaining eighteen')
    need([row['original_index'] for row in plan['remaining_commands']] == list(range(2,20)), 'unchanged original suffix indices')
    need(all(row['command']['cwd'] == str(P) for row in plan['remaining_commands']), 'explicit real parent CWD for suffix')
    need(not any(arg.startswith('--emit=obj=') for row in plan['remaining_commands'] for arg in row['command']['argv']), 'no Rust replay')
    for name, artifact in plan['retained_unchanged_artifacts'].items():
        bind(artifact['durable_authority'])
        authority = json.loads(Path(artifact['durable_authority']['path']).read_bytes())
        need(authority['object'] == artifact['object_NOT_REHASHED'], 'actual durable object authority')
        stable(artifact['object_NOT_REHASHED'])
        reused_artifacts[name] = artifact
    need(len(plan['actual_reused_commands']) == 2, 'exact successful original00/01')
    for index, record in enumerate(plan['actual_reused_commands']):
        need(record['index'] == index and record['command']['argv'] == plan['commands'][index]['argv']
             and record['command']['cwd'] == plan['commands'][index]['cwd'], 'exact retained00/01 producer')
        result = record['result']
        need(result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent']
             and result['closed_streams'] and result['error'] is None and result['retirement_error'] is None,
             'positive retained00/01 whole joins')
        records.append(record)
    reused_count = 2
    O = Path(plan['fresh_output_directory'])
    need(O == P / 'output-1' and not os.path.lexists(O), 'fresh exact corrected output namespace')
    admission = headroom()
    census = competitors()
    O.mkdir(mode=0o700)
    os.chdir(P)  # h990's dict API does not chdir for its caller.
    profile = {'scope': __doc__.splitlines()[0], 'recipe_sha256': READY_SHA,
               'driver_sha256': sha(Path(__file__)), 'helper_sha256': HELPER_SHA,
               'profile': plan['profile'], 'actual_affinity': sorted(os.sched_getaffinity(0)),
               'actual_limits': {str(k): resource.getrlimit(k) for k, _ in limits},
               'RUST_MIN_STACK': os.environ['RUST_MIN_STACK'], 'parent_CWD': str(Path.cwd()),
               'helper_globals_verified': True, 'TERM_INT_ALRM_registered': True,
               'independent_canonical_private_precondition': gate,
               'reused00_01_artifact_authorities': reused_artifacts,
               'reused00_01_no_recompile_or_object_rehash': True,
               'admission': admission, 'census': census, 'root_grant_required_externally': True}
    write(A / 'ACTUAL-PROFILE.json', profile)
    signal.setitimer(signal.ITIMER_REAL, max(.1, 96 - (time.monotonic() - begin)))
    for entry in plan['remaining_commands']:
        index, item = entry['original_index'], entry['command']
        stage = item['label']
        left = 90 - (time.monotonic() - begin)
        need(left > 0 and ns['cpu_used']() < 60, 'whole 90wall/60CPU budget')
        guards.append(headroom())
        produced = []
        prefix = '--emit=obj='
        emitted = [arg[len(prefix):] for arg in item['argv'] if arg.startswith(prefix)]
        need(len(emitted) <= 1, 'single declared object emission')
        produced.extend(emitted)
        if '-o' in item['argv']:
            need(item['argv'].count('-o') == 1, 'single declared compiler/link output')
            produced.append(item['argv'][item['argv'].index('-o') + 1])
        for output in produced:
            path = Path(output)
            need(path.is_absolute() and path.parent == O and not os.path.lexists(path), 'fresh declared producer output')
        capture = A / ('%02d' % index)
        capture.mkdir(mode=0o700)
        command = dict(item)
        command['profile_ref'] = str(A / 'ACTUAL-PROFILE.json')
        command['source_recipe_sha256'] = READY_SHA
        write(capture / 'command.json', command)
        os.chdir(item['cwd'])
        result = ns['owned_capture'](command, capture, left, lambda: None)
        write(capture / 'RESULT.json', result)
        records.append({'index': index, 'command': command, 'result': result})
        need(result['returncode'] == 0 and result['direct_child_joined'] and result['group_absent']
             and result['closed_streams'] and not result['timed_out']
             and result['error'] is None and result['retirement_error'] is None,
             ('first actual command failure; stop, no retry', index, result))
        for output in produced:
            row = ns['hashed'](Path(output), 32 << 20)
            objects[Path(output).name] = row
            write(A / ('DURABLE-' + Path(output).name + '.json'),
                  {'object': row, 'producer_index': index, 'producer_result': result,
                   'hashed_once_before_observers': True})
        if item['label'].startswith('04-'):
            variant = item['label'][3:-len('-controlled-run')]
            need((capture / 'stdout').read_text().splitlines() == plan['expected_stdout'][variant],
                 'strict current controlled state/count/NOTEXECUTED oracle')
            need((capture / 'stderr').stat().st_size == 0, 'controlled fixture empty stderr')
        if item['label'] in ['05-actual-Rust-symbols', '09-selected-cpu-ownership', '09-fallback-cpu-ownership']:
            early_symbols(plan, item['label'], (capture / 'stdout').read_text())
    observation = observer.observe(plan, records)
    for artifact in reused_artifacts.values():
        stable(artifact['object_NOT_REHASHED'])
    for path, expected in bound.items():
        need(sha(path) == expected, 'held source/tool postflight drift ' + path)
except BaseException as error:
    failure = type(error).__name__ + ': ' + str(error)
finally:
    signal.setitimer(signal.ITIMER_REAL, 0)
    joined = all(r['result']['direct_child_joined'] and r['result']['group_absent']
                 and r['result']['closed_streams'] and r['result']['retirement_error'] is None for r in records)
    report = {'scope': __doc__.splitlines()[0],
              'status': observation['status'] if failure is None and observation else 'STOP_FIRST_UNEXPECTED_NO_RETRY_EXPERT',
              'error': failure, 'last_stage': stage, 'new_commands': len(records)-reused_count,
              'reused_commands': reused_count, 'logical_commands': len(records), 'records': records,
              'retained_artifacts_not_rehashed': reused_artifacts,
              'objects_hashed_once_before_observers': objects, 'observation': observation,
              'seconds': time.monotonic() - begin, 'CPU_seconds': ns['cpu_used'](),
              'headroom_checks': guards, 'all_children_joined_groups_absent_streams_closed': joined,
              'CPU6_released': joined, 'inherited_NULL_freeze_HOLD': True,
              'native_or_privileged_instruction_execution': False, 'canonical_Git_P12_writes': 0,
              'engineering_percentage': None}
    write(A / 'ACTUAL-WHOLE-JOIN.json', report)
    print(json.dumps({k: report[k] for k in ['status', 'error', 'last_stage', 'new_commands', 'seconds', 'CPU_seconds', 'CPU6_released']}))
if failure is not None:
    raise SystemExit(1)
