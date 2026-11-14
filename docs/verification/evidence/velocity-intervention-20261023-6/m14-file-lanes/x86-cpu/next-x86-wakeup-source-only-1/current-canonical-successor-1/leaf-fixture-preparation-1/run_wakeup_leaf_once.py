"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
First twelve-command controlled wakeup leaf; execute only on root's fresh grant.
"""
from pathlib import Path
import ast, builtins, dis, hashlib, importlib.util, json, os, resource, signal
import stat, subprocess, sys, time, types

P = Path(__file__).resolve().parent
A = P / 'actual-wakeup-first-1'
H = Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
READY_SHA = 'f242646fb885e60ff09bcdb6baa6fb5bc4e453fad9e7ee52741228d044e9844a'
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


def early_symbols(plan, label, text):
    rows = [line.split() for line in text.splitlines() if line.split()]
    entry = [r for r in rows if r[-1] == '__x86_wakeup']
    if label == '07-Rust-NM' or label == '11-partial-NM':
        need(len(entry) == 1 and entry[0][-2] == 'T', 'actual Rust wakeup entry T once/no U')
    elif label == '08-selected-CPU-NM':
        need(len(entry) == 1 and entry[0][-2] == 'U', 'actual selected C Rust-entry import')
        for name in plan['declarative_data_symbols']:
            data = [r for r in rows if r[-1] == name]
            size = 20 if name == 'x86_wakeup_constants' else 8
            need(len(data) == 1 and data[0][-2] in {'R','D'} and int(data[0][-3],16) == size,
                 'actual initialized typed descriptor data '+name)


try:
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {6}, 'uid1000 exact CPU6')
    limits = [(resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60),
              (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
              (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)]
    for kind, value in limits:
        need(resource.getrlimit(kind) == (value, value), 'exact inherited limit ' + str(kind))
    need(os.environ.get('RUST_MIN_STACK') == '2097152', 'explicit Rust 2MiB stack')
    ready = P / 'EXECUTABLE-READY.NOT-GRANTED.json'
    need(sha(ready) == READY_SHA, 'frozen corrected twenty recipe')
    plan = json.loads(ready.read_bytes())
    need(plan['command_count'] == len(plan['commands']) == 12, 'exact twelve wakeup commands')
    gate = plan['operative_precondition']
    need(gate['canonical_equal_private_required'] is False, 'independent canonical/private gate')
    bind(gate['original_successor'])
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
    need(all(c['cwd'] == str(P) for c in plan['commands']), 'explicit real parent CWD in every command')
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
               'admission': admission, 'census': census, 'root_grant_required_externally': True}
    write(A / 'ACTUAL-PROFILE.json', profile)
    signal.setitimer(signal.ITIMER_REAL, max(.1, 96 - (time.monotonic() - begin)))
    for index, item in enumerate(plan['commands']):
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
        if item['label'] == '03-controlled-wakeup-run':
            need((capture / 'stdout').read_text().splitlines() == plan['expected_stdout'],
                 'strict actual18000/22ABI/NOTEXECUTED oracle')
            need((capture / 'stderr').stat().st_size == 0, 'controlled fixture empty stderr')
        if item['label'] == '04-real-selected-complete-CPU-and-ABI':
            actual_objects = observer.observe_objects(plan)
            write(A / 'ACTUAL-COMPLETE-TU-TYPE-ABI-ALLOCATED-BRIDGE.json',
                  {'observation': actual_objects, 'objects_durable_before_observer': objects})
        if item['label'] == '06-fallback-preprocess':
            fallback = (capture / 'stdout').read_text()
            need('static void __x86_wakeup(' in fallback and 'static void set_warm_reset_vector(' in fallback,
                 'literal fallback bodies before compiler inlining')
        if item['label'] in ['07-Rust-NM', '08-selected-CPU-NM', '11-partial-NM']:
            early_symbols(plan, item['label'], (capture / 'stdout').read_text())
    observation = observer.observe(plan, records)
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
              'error': failure, 'last_stage': stage, 'new_commands': len(records), 'records': records,
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
