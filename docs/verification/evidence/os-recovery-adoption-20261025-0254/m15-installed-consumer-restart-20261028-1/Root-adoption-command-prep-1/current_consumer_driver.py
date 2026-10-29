"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private serial leaf for the reviewed current-consumer phase data, not a controller.
Execution requires the parent's separately reviewed existing container/owner release.
Uses exact h990 child ownership with only optional Popen cwd support added.
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import time


def need(value, message):
    if not value:
        raise RuntimeError(message)


def checked(ref):
    raw = Path(ref['path']).read_bytes()
    need(len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256'], 'exact input ' + ref['path'])
    return raw


def capture_namespace(plan):
    raw = checked(plan['capture_helper'])
    need(plan['capture_helper']['sha256'] == '990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8', 'original h990')
    names = {'need', 'write', 'hashed', 'stop', 'members', 'process_start', 'terminal_unreaped', 'wait_terminal', 'owned_capture'}
    assignments = {'FIELDS', 'stopping', 'CENSUS_SOURCE', 'CENSUS_SHA', '_CENSUS', 'STOP_SIGNALS'}
    nodes = [n for n in ast.parse(raw).body if isinstance(n, (ast.Import, ast.ImportFrom)) or
             isinstance(n, ast.FunctionDef) and n.name in names or
             isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assignments for t in n.targets)]
    namespace = {'__file__': plan['capture_helper']['path']}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), plan['capture_helper']['path'], 'exec'), namespace)
    adapted = ast.parse(checked(plan['cwd_adapter']))
    function = [n for n in adapted.body if isinstance(n, ast.FunctionDef)]
    need(len(function) == 1 and function[0].name == 'owned_capture', 'single capture override')
    exec(compile(ast.Module(body=function, type_ignores=[]), plan['cwd_adapter']['path'], 'exec'), namespace)
    return namespace


def positive(record):
    return (record['returncode'] == 0 and record['direct_child_joined'] and record['group_absent'] and
            record['closed_streams'] and record['error'] is None and record['retirement_error'] is None and
            not record['timed_out'] and not record['unexpected_group_members'])


def execute(plan_path, plan_sha):
    raw = Path(plan_path).read_bytes()
    need(hashlib.sha256(raw).hexdigest() == plan_sha, 'Root-bound exact phase contract')
    plan = json.loads(raw)
    need(plan['runtime_authority'] is None and len(plan['phases']) == 15, 'exact reviewed phase data; no grant in plan')
    need(os.getuid() == os.geteuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}, 'existing SDK UID/CPU profile')
    need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == plan['boot_id'], 'same immutable boot')
    capture = capture_namespace(plan)
    root = Path('/work/evidence/current-consumer-phases')
    root.mkdir(mode=0o700)
    started = time.monotonic()
    records, git_records, artifacts = [], [], {}

    def remaining():
        clocks = [time.time(), time.monotonic(), time.clock_gettime(time.CLOCK_BOOTTIME)]
        value = min(plan['maximum_wall_seconds'] - (time.monotonic() - started),
                    *(end - now for end, now in zip(plan['fixed_three_clock_cutoffs'], clocks)))
        need(value > 0, 'same finite wall/window before next phase')
        usage = resource.getrusage(resource.RUSAGE_SELF), resource.getrusage(resource.RUSAGE_CHILDREN)
        need(sum(x.ru_utime + x.ru_stime for x in usage) <= 60, 'existing whole CPU60 envelope')
        need(sum(p.stat().st_size for p in Path('/work').rglob('*') if p.is_file()) <= 512 << 20,
             'existing aggregate512MiB owned output envelope')
        return value

    def limits():
        for key, value in ((resource.RLIMIT_AS, 2 << 30), (resource.RLIMIT_CPU, 60),
                           (resource.RLIMIT_FSIZE, 32 << 20), (resource.RLIMIT_NOFILE, 256),
                           (resource.RLIMIT_CORE, 0), (resource.RLIMIT_STACK, 2 << 20)):
            resource.setrlimit(key, (value, value))
        os.sched_setaffinity(0, {2, 3, 4, 5})

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGALRM):
        signal.signal(sig, capture['stop'])
    signal.setitimer(signal.ITIMER_REAL, remaining())
    receipt = dict(status='FAIL_PRESERVE_CURRENT_CONSUMER_PREFIX', commands=records,
                   artifacts=artifacts, source_adoption=plan['actual_source_adoption'],
                   default_compiler_credit=False, CLI_executed=False, native=False, file_closure=False)
    try:
        for index, phase in enumerate(plan['phases']):
            remaining()
            step = root / ('%02d' % index)
            step.mkdir(mode=0o700)
            expected = phase.get('output')
            if expected and expected.get('fresh'):
                need(not os.path.lexists(expected['path']), 'fresh phase output')
            if phase['kind'] == 'git_binding':
                need(len(git_records) == 6, 'six genuine Git captures before binding')
                capture['write'](Path('/work/output/current-source-git-captures.json'), git_records)
            command = dict(argv=phase['argv'], cwd=phase['cwd'], purpose=phase['purpose'])
            capture['write'](step / 'command.json', command)
            result = capture['owned_capture'](command, step, remaining(), limits)
            record = dict(phase=phase, result=result)
            records.append(record)
            capture['write'](step / 'RESULT.json', record)
            need(positive(result), 'first actual phase failure stops suffix')
            if phase['kind'] == 'git_identity':
                stdout, stderr = (step / 'stdout').read_text(), (step / 'stderr').read_text()
                need(stdout == phase['expected_stdout'] and stderr == '', 'exact default Git output')
                git_records.append(dict(phase=phase['git_phase'], argv=phase['argv'], cwd=phase['cwd'],
                                        stdout=stdout, stderr=stderr, returncode=result['returncode'],
                                        direct_child_joined=result['direct_child_joined'], group_absent=result['group_absent'],
                                        closed_streams=result['closed_streams'], truncated=False))
            if phase.get('expected_JSON_status'):
                need((step / 'stderr').stat().st_size == 0 and
                     json.loads((step / 'stdout').read_bytes())['status'] == phase['expected_JSON_status'], 'existing guard/binding result')
            if expected:
                path = Path(expected['path'])
                need(not path.is_symlink(), 'owned output path')
                if expected['type'] == 'directory':
                    need(path.is_dir(), 'explicit mkdir phase')
                else:
                    need(path.is_file() and path.stat().st_size > 0, 'actual phase file')
                    row = capture['hashed'](path, 32 << 20)
                    if expected.get('sha256'):
                        need(row['sha256'] == expected['sha256'], 'accepted Rust object reused exactly')
                    artifacts[str(path)] = row
            remaining()
        receipt['status'] = 'PASS_ACTUAL_CONFIGURE_LINK_COMPONENT_INSTALL_REUSED_SDK11_INPUTS_ONLY'
    except BaseException as error:
        receipt['error'] = repr(error)
        raise
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        capture['write'](Path('/work/evidence/current-consumer-producer.json'), receipt)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    execute(args.plan, args.sha256)
