"""One accepted-profile compiler/Linux reference; no McKernel/provider execution."""
from pathlib import Path
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time

Q = Path(__file__).resolve().parent
OLD = Path('/home/holden/mckernel-work/host-preparation/practical-rust-functional-batch-20261018-1')

def need(value, why):
    if not value:
        raise RuntimeError(why)

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def verify(row, path=None):
    path = Path(row.get('path', path))
    before = path.stat()
    need(stat.S_ISREG(before.st_mode) and before.st_size == row.get('size', row.get('bytes')), 'pinned file size')
    need(digest(path) == row['sha256'], 'pinned file hash: ' + str(path))
    after = path.stat()
    need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) == (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns), 'pin changed')
    if 'mode' in row:
        need(before.st_mode == row['mode'], 'pinned mode')
    return path

def metadata(path):
    s = path.stat()
    return dict(path=str(path), sha256=digest(path), device=s.st_dev, inode=s.st_ino, uid=s.st_uid, gid=s.st_gid, mode=s.st_mode, nlink=s.st_nlink, size=s.st_size, mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)

def put(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write('\n')

def main():
    start = time.monotonic()
    deadline = start + 160
    proposal = json.loads((Q / 'ordinary-compiler-linux-proposal.json').read_bytes())
    need(os.sched_getaffinity(0) == {6}, 'CPU6 allocation')
    state = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes())
    usage = state['last_rate_limits']['primary']['usedPercent']
    need(state.get('stop_reason') is None and type(usage) in (int, float) and usage < 97, 'usage/service stop')
    free = lambda path: os.statvfs(path).f_bavail * os.statvfs(path).f_frsize
    host, scratch = free('/home/holden'), free('/home/holden/mckernel-work/scratch')
    available = next(int(row.split()[1]) * 1024 for row in Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:'))
    reserve = (640 + 64) << 20
    need(min(host, available) >= (16 << 30) + reserve and scratch >= (12 << 30) + reserve, 'capacity floors/reserve')
    original = json.loads((OLD / 'ordinary-compiler-linux-proposal.json').read_bytes())
    binding_path = verify(original['bindings'])
    bindings = json.loads(binding_path.read_bytes())
    for row in bindings['tools'].values():
        verify(row)
    for row in bindings['installed_static_link_inputs'].values():
        verify(row)
    carrier_path = verify(bindings['target_rlib_binding_record'])
    carrier = json.loads(carrier_path.read_bytes())
    libraries = carrier['installed_target_rlib_bindings']
    need(len(libraries) == bindings['target_rlib_count'] == 27, 'exact 27 target libraries')
    root = Path(bindings['tools']['rustc']['path']).parent.parent / 'lib/rustlib/x86_64-unknown-linux-gnu/lib'
    for name, row in libraries.items():
        verify(row, Path(name) if Path(name).is_absolute() else root / name)
    for row in json.loads((Q / 'source-pins.json').read_bytes()).values():
        verify(row)
    for row in json.loads((Q / 'reference-tool-pins.json').read_bytes()).values():
        verify(row)
    run = Q / 'compiler-linux-reference-1'
    run.mkdir(mode=0o700)
    for name in ('home', 'tmp'):
        (Q / name).mkdir(mode=0o700)
    put(run / 'admission.json', dict(host_free=host, scratch_free=scratch, memory_available=available, reserve=reserve, usage_percent=usage, cpu=[6], profile=proposal['resources'], target_rlibs=27, inherited_static_inputs=len(bindings['installed_static_link_inputs']), root=False))
    captures = []
    for entry in proposal['commands']:
        directory = run / entry['label']
        directory.mkdir()
        argv = entry['argv']
        stage_start = time.monotonic()
        with (directory / 'stdout').open('xb') as stdout, (directory / 'stderr').open('xb') as stderr:
            child = subprocess.Popen(argv, cwd=entry['cwd'], env=proposal['environment'], stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
            child_start = Path('/proc/' + str(child.pid) + '/stat').read_text().rsplit(')', 1)[1].split()[19]
            put(directory / 'child.json', dict(pid=child.pid, start=child_start, argv=argv, cwd=entry['cwd'], env=proposal['environment'], process_group=child.pid))
            timed_out = False
            try:
                rc = child.wait(timeout=min(entry['timeout_seconds'], max(0.1, deadline - time.monotonic())))
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGTERM)
                try:
                    rc = child.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    rc = child.wait(timeout=1)
            stdout.flush(); stderr.flush()
        try:
            os.killpg(child.pid, 0)
            absent = False
        except ProcessLookupError:
            absent = True
        status = dict(pid=child.pid, start=child_start, returncode=rc, direct_child_joined=True, process_group_absent=absent, timed_out=timed_out, elapsed_seconds=time.monotonic() - stage_start, argv=argv, cwd=entry['cwd'], env=proposal['environment'], stdout=metadata(directory / 'stdout'), stderr=metadata(directory / 'stderr'))
        put(directory / 'status.json', status)
        captures.append(status)
        need(rc == 0 and absent and not timed_out, 'stage failed: ' + entry['label'])
    need((run / 'compile/stderr').stat().st_size == 0, 'compiler stderr')
    elf = (run / 'readelf/stdout').read_text()
    need(re.search(r'Type:\s+EXEC\b', elf) and 'INTERP' not in elf and '(NEEDED)' not in elf, 'static GNU ELF EXEC')
    oracle = json.loads((Q / 'frozen-oracle.json').read_bytes())
    actual = (run / 'linux-reference/stdout').read_bytes()
    need(actual == (Q / 'expected.stdout').read_bytes() and not (run / 'linux-reference/stderr').read_bytes(), 'frozen stdout/stderr oracle')
    observations = json.loads((Q / 'observations.json').read_bytes())
    children = observations['children']
    need(len(children) == 2 and len({row['pid'] for row in children}) == 2 and observations['owned_children'] == 0, 'two distinct children, zero owned')
    need([row['exit_code'] for row in children] == oracle['child_exit_codes'] and [row['wait_status'] for row in children] == oracle['raw_wait_statuses'], 'actual child exit statuses')
    need(all(row['eof'] and row['reaped'] and row['second_wait_errno'] == 10 and row['owned_after'] is False for row in children), 'reaping observations')
    trace = (Q / 'linux-process.trace').read_text()
    # Join strace's per-PID unfinished/resumed records before checking waits.
    # No timing or interleaving is part of the process oracle.
    pending, joined = {}, []
    for line in trace.splitlines():
        prefix = re.match(r'^(\d+)\s+(.*)$', line)
        if not prefix:
            joined.append(line)
            continue
        pid, body = prefix.groups()
        if body.endswith('<unfinished ...>'):
            pending[pid] = body.removesuffix('<unfinished ...>')
        elif re.match(r'^<\.\.\. \w+ resumed>', body) and pid in pending:
            joined.append(pid + ' ' + pending.pop(pid) + re.sub(r'^<\.\.\. \w+ resumed>', '', body))
        else:
            joined.append(line)
    trace = '\n'.join(joined)
    need('ENOENT' in trace and 'ECHILD' in trace and trace.count('execve(') >= 3, 'actual exec/error/wait trace')
    for row in children:
        pid = str(row['pid'])
        need(re.search(r'wait4\(' + pid + r',.*= ' + pid + r'\b', trace), 'actual owned child wait trace')
        need(re.search(r'wait4\(' + pid + r',.*= -1 ECHILD', trace), 'actual second wait trace')
    need(sum(path.stat().st_size for path in Q.rglob('*') if path.is_file()) <= 67108864, '64MiB aggregate output acceptance')
    result = dict(status='PASS_STATIC_RUST_LINUX_PROCESS_EXEC_WAIT_REFERENCE_ONLY', source=metadata(Q / 'process_exec_wait.rs'), binary=metadata(Q / 'process_exec_wait'), stdout_bytes=len(actual), stdout_sha256=hashlib.sha256(actual).hexdigest(), exit_code=0, child_observations=observations, trace=metadata(Q / 'linux-process.trace'), static_EXEC=True, target_libraries_verified=27, command_count=3, all_direct_joined=True, all_process_groups_absent=True, captures=captures, elapsed_seconds=time.monotonic() - start, new_guest_runs=0, native_acceptance=False, held_provider_changed=False, current_McKernel_CREATE_PPD_prerequisite=oracle['native_prerequisite'])
    put(Q / 'linux-reference-result.json', result)
    print(json.dumps(dict(status=result['status'], commands=3, stdout_bytes=len(actual), children=2, elapsed_seconds=result['elapsed_seconds'], root=False)))

if __name__ == '__main__':
    main()
