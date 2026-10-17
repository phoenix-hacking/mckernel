#!/usr/bin/env python3
"""Preview a dedicated-machine OS campaign; --run explicitly resumes it.

Reuse run_os_goal.py and its saved thread, watcher, leases and usage guards.
Default/--check never starts inference. This script never edits launcher state.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shlex
import stat
import subprocess
import sys
import tempfile

from os_goal_resources import check_resources, resolve_resources
from run_os_goal import DEFAULT_DISPATCHER_MODEL, INCLUDED_USAGE_STOP_PERCENT, model_routing
from os_goal_instructions import reconcile_instructions

REPO = Path(__file__).resolve().parents[1]
SCRATCH = Path('/home/holden/mckernel-work/scratch')
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
NOTE = REPO / 'docs/verification/os-milestones-20260914/PARALLEL-RESUME.md'
HOLD_ID = '20261017T021032370649Z-e1d9b3466e7c4dcfb8838159453e3bf2'
HOLD_SHA = 'a05027f2144889dfa93755e2680f27614352b588972becb178697f524ff831b9'


def read_json(path):
    return json.loads(path.read_text())


def state_directory(repo):
    value = subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', '--git-common-dir'], text=True).strip()
    return (repo / value).resolve() / 'os-autopilot'


def queue_blockers(directory):
    try:
        reconcile_instructions(directory, [{'id': HOLD_ID, 'sha256': HOLD_SHA}],
                               hashlib.sha256(NOTE.read_bytes()).hexdigest(), execute=False)
    except (OSError, ValueError) as error:
        return [str(error)]
    return []


def stopped_blockers(directory, state):
    failures = []
    if not state.get('thread_id') or not state.get('goal'):
        failures.append('A saved campaign and goal are required; this entry point never creates one.')
    if state.get('phase') != 'stopped' or state.get('active_turns'):
        failures.append('Saved dispatcher must be stopped with no active turns.')
    if (state.get('goal') or {}).get('status') != 'paused':
        failures.append('Saved goal must be paused; inspect its actual status before resuming.')
    if (state.get('resume_instruction') or {}).get('status') in ('sending', 'delivery_uncertain'):
        failures.append('Resume instruction delivery is uncertain; reconcile its saved turn before resuming.')
    for name in ('run.lock', 'watch.lock'):
        path = directory / name
        if path.exists():
            with path.open('rb') as stream:
                try:
                    fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    failures.append('Another launcher holds ' + name)
    for key in ('worker_pid', 'server_pid'):
        pid = state.get(key)
        if isinstance(pid, int) and Path('/proc', str(pid)).exists():
            failures.append('Saved ' + key + ' is present; reconcile PID/starttime before launch: ' + str(pid))
    watch = directory / 'watcher.json'
    if watch.is_file():
        pid = read_json(watch).get('watcher_pid')
        if isinstance(pid, int) and Path('/proc', str(pid)).exists():
            failures.append('Saved watcher PID is present; reconcile its birth identity: ' + str(pid))
    return failures


def host_blockers():
    failures = []
    mount = read_mount()
    if (mount.get('target') != str(SCRATCH) or mount.get('uuid') != UUID or
            mount.get('fstype') != 'ext4' or
            not {'rw', 'nodev', 'nosuid'} <= set(mount.get('options', '').split(','))):
        failures.append('Scratch mount/UUID/options differ from the retained filesystem.')
    controls = {
        '/sys/fs/cgroup/cpu,cpuacct/mckernel-dev/cpu.cfs_quota_us': '400000',
        '/sys/fs/cgroup/cpu,cpuacct/mckernel-dev/cpu.cfs_period_us': '100000',
        '/sys/fs/cgroup/memory/mckernel-dev/memory.limit_in_bytes': '12884901888',
        '/sys/fs/cgroup/pids/mckernel-dev/pids.max': '512',
    }
    for path, expected in controls.items():
        if Path(path).read_text().strip() != expected:
            failures.append('Validation control differs: ' + path)
    path = Path('/run/lock/mckernel-development.lock')
    before = path.lstat()
    if (before.st_uid != 0 or before.st_gid != 0 or
            not stat.S_ISREG(before.st_mode) or before.st_nlink != 1):
        failures.append('Root development lock identity/ownership requires reconciliation.')
    else:
        # Probe the existing inode without creating, replacing or unlinking it.
        with path.open('rb') as stream:
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                after = path.lstat()
                if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                    failures.append('Root development lock changed during observation.')
            except BlockingIOError:
                failures.append('Root development lock is held; reconcile the live owner first.')
    return mount, failures


def read_mount():
    raw = subprocess.check_output(
        ['findmnt', '-J', '-T', str(SCRATCH), '-o', 'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,MAJ:MIN'],
        text=True, timeout=10)
    rows = json.loads(raw)['filesystems']
    if len(rows) != 1:
        raise ValueError('Ambiguous scratch mount')
    return rows[0]


def launch_command(args, resources):
    return [sys.executable, '-B', str(REPO / 'scripts/run_os_goal.py'),
            '--model', args.model, '--effort', args.effort,
            '--profile', 'aggressive', '--max-agents', str(resources['max_agents']),
            '--build-jobs', str(resources['build_jobs']), '--memory-gib', str(resources['memory_gib']),
            '--hours', str(args.hours), '--agent-windows', args.windows,
            '--stall-seconds', '0', '--startup-instruction-file', str(NOTE),
            '--startup-instruction-sha256', hashlib.sha256(NOTE.read_bytes()).hexdigest(),
            '--supersede-instruction', HOLD_ID + ':' + HOLD_SHA]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--run', action='store_true', help='Authorize autonomous execution in the saved campaign')
    mode.add_argument('--check', action='store_true', help='Also check local CLI settings/models, without inference')
    parser.add_argument('--background', action='store_true',
                        help='With --run, detach the existing watcher and retain its console in a private log')
    parser.add_argument('--agents', type=int, help='Optional smaller ceiling; default is the measured maximum')
    parser.add_argument('--hours', type=float, default=0, help='0: no wall-clock cutoff; optional finite window')
    parser.add_argument('--windows', choices=('auto', 'on', 'off'), default='auto')
    parser.add_argument('--model', default=DEFAULT_DISPATCHER_MODEL, choices=[DEFAULT_DISPATCHER_MODEL],
                        help='Coordinator model; default: ' + DEFAULT_DISPATCHER_MODEL)
    parser.add_argument('--effort', choices=('low', 'medium', 'high'),
                        default='medium', help='Coordinator reasoning; default: medium')
    args = parser.parse_args(argv)
    if args.background and not args.run:
        parser.error('--background requires --run')
    if not math.isfinite(args.hours) or args.hours < 0:
        parser.error('hours must be finite and non-negative')
    resources = resolve_resources(repo=REPO)
    capacity = max(1, min(resources['cpu_count'] * 2, int(resources['memory_gib'] // resources['agent_memory_gib'])))
    resources = resolve_resources(max_agents=capacity if args.agents is None else args.agents, repo=REPO)
    check_resources(resources)
    directory = state_directory(REPO)
    state = read_json(directory / 'state.json')
    failures = stopped_blockers(directory, state) + queue_blockers(directory)
    mount, host_failures = host_blockers()
    failures += host_failures
    note = NOTE.read_text()
    if not note.strip() or len(note.encode()) > 8192 or HOLD_ID not in note:
        raise ValueError('Missing/invalid preparation-hold reconciliation in startup instructions')
    command = launch_command(args, resources)
    print(json.dumps({
        'mode': 'run' if args.run else 'check' if args.check else 'preview',
        'background': args.background,
        'thread_id': state['thread_id'], 'resources': resources,
        'model_routing': model_routing(args),
        'included_usage_stop_percent': INCLUDED_USAGE_STOP_PERCENT,
        'scratch': mount, 'startup_instruction_sha256': hashlib.sha256(note.encode()).hexdigest(),
        'pending_hold': 'Before activation the launcher archives only exact superseded bytes and an audit receipt.',
        'launch_blockers': failures,
        'engineering_prerequisites': [
            'Scratch21-specific cleanup implementation, independent review and fresh live identity release.',
            'Finish/review RS-011 source authority; retain failing discovery and run complete cheap checks.',
            'Commit/push/fetch the reviewed sources, prepare fresh scratch22; obtain a new one-shot build release.',
            'Real acceptance still requires original contracts, soaks, hardware and external qualification.'
        ],
        'command': shlex.join(command),
        'inference_started': False,
    }, indent=2), flush=True)
    if failures:
        return 1
    if args.check or args.run:
        # Existing preflight verifies advertised models, effective concurrency and
        # build environment. It starts only a local app server, never inference.
        subprocess.run(command + ['--check'], cwd=REPO, check=True)
    if args.run:
        if args.background:
            logs = directory / 'launch-logs'
            logs.mkdir(mode=0o700, parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='ab', dir=logs, prefix='parallel-', suffix='.log',
                                             delete=False) as stream:
                process = subprocess.Popen(command, cwd=REPO, stdin=subprocess.DEVNULL,
                                           stdout=stream, stderr=subprocess.STDOUT,
                                           start_new_session=True, close_fds=True)
            print(json.dumps({'launcher_pid': process.pid, 'console_log': stream.name,
                              'monitor': 'python3 -B ' + str(REPO / 'scripts/run_os_goal.py') + ' --progress'}),
                  flush=True)
            return 0
        # Same process/terminal, existing watcher/signal handling, no second
        # dispatcher, no custom restart loop and no launcher-state edits.
        os.execv(sys.executable, command)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print('os-parallel: ' + str(error), file=sys.stderr)
        sys.exit(1)
