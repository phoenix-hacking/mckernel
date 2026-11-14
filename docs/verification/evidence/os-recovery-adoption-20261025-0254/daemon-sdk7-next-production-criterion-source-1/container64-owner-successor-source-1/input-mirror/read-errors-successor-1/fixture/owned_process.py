"""Existing h990 capture adapter for this daemon fixture; never a production module.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No child or daemon runs on import. The caller must hold a current ordinary grant.
"""
import ast
import hashlib
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

HELPER = Path('/home/holden/mckernel/docs/verification/evidence/'
              'phase5-m03-handshake-runtime-checkpoint-20261020-1/'
              'sdk-physical-source/run_two_commands_source_bound_corrected.py')
HELPER_SHA = '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'


class Owner:
    def __init__(self, output):
        self.output = Path(output)
        self.started = time.monotonic()
        raw = HELPER.read_bytes()
        if hashlib.sha256(raw).hexdigest() != HELPER_SHA:
            raise ValueError('accepted h990 capture source changed')
        functions = {'need', 'write', 'hashed', 'stop', 'members', 'cpu_used',
                     'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
        constants = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA',
                     '_CENSUS', 'STOP_SIGNALS'}
        nodes = []
        for node in ast.parse(raw, str(HELPER)).body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                nodes.append(node)
            elif isinstance(node, ast.FunctionDef) and node.name in functions:
                nodes.append(node)
            elif isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id in constants
                    for target in node.targets):
                nodes.append(node)
        if {node.name for node in nodes if isinstance(node, ast.FunctionDef)} != functions:
            raise ValueError('complete unchanged h990 dependencies required')
        self.helper = {'__file__': str(HELPER), '__name__': 'daemon_fixture_h990_functions'}
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(HELPER), 'exec'), self.helper)
        for number in self.helper['STOP_SIGNALS']:
            signal.signal(number, self.helper['stop'])
        original_wait = self.helper['wait_terminal']

        def monitored_wait(process, seconds):
            # Keep unchanged h990 retirement after work monitoring reports failure.
            if self.helper['stopping']:
                return original_wait(process, seconds)
            deadline = time.monotonic() + seconds
            while not self.helper['terminal_unreaped'](process):
                self.accounting()
                if time.monotonic() >= deadline:
                    return False
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
            self.accounting()
            return True

        self.helper['wait_terminal'] = monitored_wait
        if len(os.sched_getaffinity(0)) != 1:
            raise ValueError('fresh dispatcher grant must bind one ordinary CPU')
        for kind, bound in ((resource.RLIMIT_AS, 2 << 30),
                            (resource.RLIMIT_CPU, 60),
                            (resource.RLIMIT_FSIZE, 32 << 20),
                            (resource.RLIMIT_NOFILE, 256),
                            (resource.RLIMIT_CORE, 0),
                            (resource.RLIMIT_STACK, 2 << 20)):
            if resource.getrlimit(kind) != (bound, bound):
                raise ValueError('exact inherited daemon fixture resource profile required')
        if os.environ.get('RUST_MIN_STACK') != '2097152':
            raise ValueError('explicit Rust worker stack binding required')
        signal.setitimer(signal.ITIMER_REAL, 90)

    def accounting(self):
        paths = list(self.output.rglob('*'))
        if len(paths) > 4096:
            raise ValueError('private fixture output inventory exceeded')
        total = sum(path.lstat().st_size for path in paths if path.is_file())
        if total > 64 << 20:
            raise ValueError('64MiB aggregate private fixture output exceeded')
        return total

    def run(self, argv, env, cwd, timeout, label):
        if self.helper['stopping']:
            raise InterruptedError('h990 owner stopped; preserve captures, no retry')
        target = self.output / label
        target.mkdir(mode=0o700)
        command = {'argv': argv, 'cwd': str(cwd), 'label': label}
        self.helper['write'](target / 'command.json', command)
        previous_env = dict(os.environ)
        previous_cwd = Path.cwd()
        try:
            # One controller thread; Rust workers exist only in captured children.
            os.environ.clear()
            os.environ.update(env)
            os.chdir(cwd)
            record = self.helper['owned_capture'](command, target, timeout, lambda: None)
            self.helper['write'](target / 'whole-join.json', record)
        finally:
            os.chdir(previous_cwd)
            os.environ.clear()
            os.environ.update(previous_env)
        if (not record['direct_child_joined'] or not record['group_absent']
                or not record['closed_streams'] or record['unexpected_group_members']
                or record['timed_out'] or record['error'] or record['retirement_error']):
            raise RuntimeError(label + ' h990 capture failed; stop and retain all evidence')
        self.accounting()
        if self.helper['cpu_used']() > 60:
            raise RuntimeError('whole fixture 60CPU acceptance budget exceeded')
        return subprocess.CompletedProcess(argv, record['returncode'],
                                           (target / 'stdout').read_bytes(),
                                           (target / 'stderr').read_bytes())
