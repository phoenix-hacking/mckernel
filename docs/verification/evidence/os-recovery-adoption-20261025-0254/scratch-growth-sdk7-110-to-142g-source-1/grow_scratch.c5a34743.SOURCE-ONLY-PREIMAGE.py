#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite root-only scratch growth candidate. Import/tests never perform live operations.
"""
import argparse
import datetime
from decimal import Decimal
import fcntl
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import time

BACKING = '/home/holden/mckernel-work/scratch.ext4'
MOUNT = '/home/holden/mckernel-work/scratch'
LOOP = '/dev/loop36'
UUID = '2a5768c8-718d-4914-bdc0-6b32c5a92a52'
OLD, NEW = 118111600640, 152471339008
END = datetime.datetime(2026, 10, 27, 11, 24, 50, tzinfo=datetime.timezone.utc).timestamp()
COMMANDS = [['/usr/bin/truncate', '--no-create', '--size=152471339008', BACKING],
            ['/usr/sbin/losetup', '--set-capacity', LOOP],
            ['/usr/sbin/resize2fs', LOOP]]
TOOLS = {'/usr/bin/truncate': '72577f960652d3abb3f3a61b807b061fe433f0deaa8edec1f9230087806e299c',
         '/usr/sbin/losetup': '609b9febb788b95eae105d5a84ec625a6232384825c6c8d7451b7dd729893521',
         '/usr/sbin/resize2fs': '510f0bb49cef2a310269de44a897e4a20e96cd13135a099b08ff81cb5111cc34',
         '/usr/sbin/dumpe2fs': 'e6a51a180b4d0a85aa9247ada69c4af285a2155def0606e59d5490415a6c38d5'}
NATIVE2_SHA = 'f18a78021d4f801d54c556a60d8ae751c31c3681c4dafceb00e813efdebeb268'


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def ref(path):
    p = Path(path).resolve()
    return {'path': str(p), 'bytes': p.stat().st_size, 'sha256': digest(p)}


def load_ref(r):
    need(ref(r['path']) == r, 'reference differs: ' + r['path'])
    return json.loads(Path(r['path']).read_text())


def ident(st):
    return dict(device=st.st_dev, inode=st.st_ino, uid=st.st_uid, gid=st.st_gid,
                mode=stat.S_IMODE(st.st_mode), nlink=st.st_nlink, size=st.st_size)


def expected(size):
    return dict(path=BACKING, device=66306, inode=47468427, uid=0, gid=0,
                mode=0o600, nlink=1, size=size, uuid=UUID)


def full_capacity(available, allocated, capture, emergency):
    # Reserve all new sparse exposure, plus explicit full growth, floors and headroom.
    need(0 <= allocated <= OLD and capture > 0 and emergency > 0, 'capacity inputs')
    required = (NEW - OLD) + (NEW - allocated) + 16 * 2**30 + 8 * 2**30 + capture + emergency
    need(available >= required, 'full-growth HOST capacity insufficient')
    return required


def authority(source, grant_ref, review_ref, contract_ref, now):
    c, g, r = [load_ref(x) for x in (contract_ref, grant_ref, review_ref)]
    binding = dict(source=source, previous_serial_operation=c['previous_serial_operation'],
                   nonce=c['nonce'], before=expected(OLD), after=expected(NEW))
    need(c['previous_serial_operation']['sha256'] == NATIVE2_SHA, 'previous serial must be native2')
    load_ref(c['previous_serial_operation'])
    need(g['status'] == 'GRANTED_SCRATCH_GROWTH_110_TO_142G' and g['bindings'] == binding
         and g['contract'] == contract_ref and g['commands'] == COMMANDS
         and g['lower_reserves'] is False, 'grant mismatch')
    need(r['decision'] == 'PASS_SCRATCH_GROWTH_EXECUTION' and r['grant'] == grant_ref
         and r['bindings'] == binding and r['implementation_ownership'] is False
         and bool(r['reviewer']), 'independent execution review mismatch')
    acceptance = load_ref(c['native2_current_acceptance'])
    need(acceptance['decision'] == 'PASS_ACTUAL_NATIVE2_POSTJOIN_CURRENT_PHYSICAL'
         and acceptance['independent'] is True, 'native2 current acceptance required')
    account_guard(now)
    need(c['boot_id'] == Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'boot changed')
    need(c['issued_wall'] <= now <= c['expires_wall'] <= END and now + 600 < c['expires_wall'], 'window expired')
    need(c['account_guard']['status'] == 'PASS_CURRENT_ACCOUNT_GUARD'
         and c['account_guard']['observed_wall'] <= now
         and now - c['account_guard']['observed_wall'] <= 15
         and c['account_guard']['allowed_until_wall'] >= c['expires_wall'], 'current account guard required')
    need(c['source_only'] is False and c['execution_authority'] is True, 'source-only contract cannot execute')
    need(c['quiescence']['status'] == 'PASS_EXCLUSIVE_SCRATCH_GROWTH'
         and c['quiescence']['observed_wall'] <= now
         and now - c['quiescence']['observed_wall'] <= 15
         and all(c['quiescence'][k] is True for k in
                 ('no_native_owner', 'no_Docker_owner', 'no_other_heavy_owner',
                  'no_SDK_lease', 'paused_consumers_reconciled', 'scratch_exclusive')), 'fresh quiescence required')
    need(c['cpu_affinity'] == [2, 3, 4, 5] and c['jobs'] == 1
         and c['address_space_limit'] == 2 * 2**30 and c['aggregate_limit'] <= 12 * 2**30,
         'resource grant differs')
    return c, binding


def account_guard(now):
    s = json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text())
    heartbeat = datetime.datetime.fromisoformat(s['heartbeat_at']).timestamp()
    need(s['phase'] == 'running' and s['thread_id'] == '01a170fb-57c3-7ab3-862d-8005bef92a63'
         and s['credit_budget']['id'] == '7f4af94a83b14cc08f97401f5891d965'
         and Decimal(s['credit_budget']['budget']) == Decimal('57774.852125')
         and Decimal(s['credit_budget']['remaining']) > 0
         and s['credit_budget_error'] is None and 0 <= now - heartbeat < 180
         and s['last_rate_limits']['spendControlReached'] is False, 'live account guard')


def fs_fields(text):
    values = {}
    for line in text.splitlines():
        if ':' in line:
            k, v = line.split(':', 1)
            values[k.strip()] = v.strip()
    return dict(uuid=values['Filesystem UUID'], blocksize=int(values['Block size']),
                blocks=int(values['Block count']), reserved=int(values['Reserved block count']))


def fs_check(fields, after):
    blocks = 37224448 if after else 28835840
    need(fields['uuid'] == UUID and fields['blocksize'] == 4096 and fields['blocks'] == blocks,
         'ext4 geometry differs')
    if after:
        # Original ext4 integer reservation ratio, rounded within one block.
        need(abs(fields['reserved'] * 28835840 - 288358 * blocks) <= 28835840,
             'automatic ext4 reserve ratio differs')
    else:
        need(fields['reserved'] == 288358, 'original ext4 reservation differs')


def file_manifest(c):
    records = []
    manifest = load_ref(c['critical_files_manifest'])
    need(len(manifest) == 5, 'five critical files required')
    for r in manifest:
        p = Path(r['path'])
        need(str(p).startswith('/home/holden/mckernel-work/') and not p.is_symlink(), 'preserved file path')
        st = os.lstat(p)
        need(stat.S_ISREG(st.st_mode), 'preserved file type')
        actual = dict(path=str(p), device=st.st_dev, inode=st.st_ino, mode=st.st_mode,
                      uid=st.st_uid, gid=st.st_gid, bytes=st.st_size, nlink=st.st_nlink,
                      sha256=digest(p))
        need(actual == r, 'critical file differs: ' + str(p))
        records.append(actual)
    nodes = load_ref(c['scratch21_manifest'])
    need(len(nodes) == 24, '24 scratch21 nodes required')
    dirs = set()
    for r in nodes:
        st = os.lstat(r['path'])
        actual = dict(path=r['path'], device=st.st_dev, inode=st.st_ino, mode=st.st_mode,
                      uid=st.st_uid, gid=st.st_gid, size=st.st_size, nlink=st.st_nlink)
        if 'sha256' in r:
            need(stat.S_ISREG(st.st_mode), 'scratch21 file type')
            actual['sha256'] = digest(r['path'])
        else:
            need(stat.S_ISDIR(st.st_mode), 'scratch21 directory type')
            dirs.add(st.st_ino)
        need(actual == r, 'scratch21 node differs')
    need(dirs == {3933582, 4458708, 4458709, 6946858}, 'scratch21 directory identities')
    root_node = c['root_directory']
    need(root_node['path'] == MOUNT and ident(os.lstat(MOUNT)) == root_node['identity'],
         'root directory identity differs')
    return dict(critical_files=records, scratch21=nodes, root_directory=root_node)


def live(c, after, command):
    st = os.lstat(BACKING)
    need(stat.S_ISREG(st.st_mode) and dict(path=BACKING, **ident(st), uuid=UUID) == expected(NEW if after else OLD),
         'backing identity differs')
    need(os.stat(MOUNT).st_dev == 1828 and os.path.ismount(MOUNT), 'scratch mount differs')
    mounts = [x.split() for x in Path('/proc/self/mountinfo').read_text().splitlines()]
    rows = [x for x in mounts if x[4] == MOUNT]
    need(len(rows) == 1, 'mountinfo count')
    row = rows[0]; sep = row.index('-')
    need(row[sep + 1] == 'ext4' and row[sep + 2] == LOOP
         and {'rw', 'nosuid', 'nodev', 'relatime'} <= set(row[5].split(',')), 'mountinfo differs')
    loop_st = os.stat(LOOP)
    need(stat.S_ISBLK(loop_st.st_mode) and loop_st.st_rdev == os.makedev(7, 36), 'loop node differs')
    lp = Path('/sys/block/loop36')
    need(int((lp / 'size').read_text()) * 512 == (NEW if after else OLD), 'loop capacity differs')
    need((lp / 'loop/backing_file').read_text().strip() == BACKING
         and (lp / 'loop/offset').read_text().strip() == '0'
         and (lp / 'loop/sizelimit').read_text().strip() == '0'
         and (lp / 'loop/autoclear').read_text().strip() == '1'
         and (lp / 'ro').read_text().strip() == '0', 'loop binding differs')
    for p, sha in TOOLS.items():
        need(digest(p) == sha, 'tool changed: ' + p)
    result = command(['/usr/sbin/dumpe2fs', '-h', LOOP], 'geometry-after' if after else 'geometry-before', False)
    fs = fs_fields(result['stdout']); fs_check(fs, after)
    preserved = file_manifest(c)
    scratch_v = os.statvfs(MOUNT)
    need(scratch_v.f_bavail * scratch_v.f_frsize >= 12 * 2**30, 'scratch floor below 12GiB')
    if not after:
        v = os.statvfs(str(Path(BACKING).parent))
        full_capacity(v.f_bavail * v.f_frsize, st.st_blocks * 512,
                      c['capture_bytes'], c['emergency_bytes'])
    return dict(backing=expected(NEW if after else OLD), geometry=fs,
                preservation=preserved)


def sequence(run, before, after, journal):
    """Exactly three commands; every effect may be uncertain until its child returns."""
    before()
    results = []
    for n, argv in enumerate(COMMANDS):
        journal('mutation_intent', dict(index=n, argv=argv))
        result = run(argv, str(n), True)
        need(result['returncode'] == 0, 'growth command failed')
        results.append(result)
    after()
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('source-sha256', 'contract', 'grant', 'grant-sha256', 'review', 'review-sha256', 'output'):
        p.add_argument('--' + key, required=True)
    p.add_argument('--execute-exact-growth', action='store_true', required=True)
    a = p.parse_args()
    need(os.geteuid() == 0, 'root execution only')
    need(all(os.path.isabs(x) for x in (a.contract, a.grant, a.review, a.output)), 'absolute execution paths required')
    source = ref(__file__); need(source['sha256'] == a.source_sha256, 'source SHA mismatch')
    grant_ref, review_ref, contract_ref = map(ref, (a.grant, a.review, a.contract))
    need(grant_ref['sha256'] == a.grant_sha256 and review_ref['sha256'] == a.review_sha256, 'grant/review SHA mismatch')
    c, binding = authority(source, grant_ref, review_ref, contract_ref, time.time())
    out = Path(a.output)
    need(os.stat(out.parent).st_dev == os.stat(Path(BACKING).parent).st_dev
         and not str(out.resolve()).startswith(MOUNT + '/'), 'output must reside on HOST filesystem')
    need(str(out.resolve()) == c['output_path'] and not out.exists(), 'fresh exact output required')
    out.mkdir(mode=0o700)
    journal_fd = os.open(out / 'journal.jsonl', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC, 0o600)
    mutex_fd = None
    mutation = False
    child = None
    def journal(event, data):
        raw = json.dumps(dict(event=event, wall=time.time(), pid=os.getpid(), data=data), sort_keys=True) + '\n'
        data = memoryview(raw.encode())
        while data:
            written = os.write(journal_fd, data)
            need(written > 0, 'journal short write')
            data = data[written:]
        os.fsync(journal_fd)
    def command(argv, label, mutating):
        nonlocal mutation, child
        need(time.time() + 300 < min(c['expires_wall'], END), 'insufficient deadline reserve')
        if mutating:
            account_guard(time.time())
            for tool, sha in TOOLS.items():
                need(digest(tool) == sha, 'tool changed before mutation')
            mutation = True
        # Separate new regular streams, direct child and direct wait. No shell/process-group kill.
        start = time.monotonic(); usage = resource.getrusage(resource.RUSAGE_CHILDREN)
        with open(out / (label + '.stdout'), 'xb') as stdout, open(out / (label + '.stderr'), 'xb') as stderr:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                                     close_fds=True, env={'PATH': '/usr/sbin:/usr/bin', 'LC_ALL': 'C'})
            journal('child_started', dict(pid=child.pid, argv=argv))
            rc = child.wait(timeout=300)
        u = resource.getrusage(resource.RUSAGE_CHILDREN)
        result = dict(argv=argv, pid=child.pid, returncode=rc, elapsed=time.monotonic()-start,
                      user_seconds=u.ru_utime-usage.ru_utime, system_seconds=u.ru_stime-usage.ru_stime,
                      stdout_path=str(out / (label + '.stdout')), stderr_path=str(out / (label + '.stderr')),
                      stdout=(out / (label + '.stdout')).read_text(errors='replace'),
                      stderr=(out / (label + '.stderr')).read_text(errors='replace'))
        child = None
        journal('child_waited', result)
        need(rc == 0, 'child returned nonzero')
        return result
    def interrupted(signum, frame):
        raise InterruptedError('signal ' + str(signum))
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
        signal.signal(sig, interrupted)
    try:
        need(c['mutex']['path'] == '/run/lock/mckernel-development.lock', 'exact permanent mutex required')
        mutex_fd = os.open(c['mutex']['path'], os.O_RDWR | os.O_NOFOLLOW | os.O_CLOEXEC)
        st = os.fstat(mutex_fd)
        need(stat.S_ISREG(st.st_mode) and ident(st) == c['mutex']['identity']
             and st.st_uid == 0 and st.st_gid == 0 and st.st_nlink == 1
             and st.st_size == 0 and stat.S_IMODE(st.st_mode) == 0o644, 'mutex node differs')
        fcntl.flock(mutex_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal('own_fd_acquired', dict(fd=mutex_fd, identity=ident(st)))
        os.sched_setaffinity(0, c['cpu_affinity'])
        resource.setrlimit(resource.RLIMIT_AS, (2 * 2**30, 2 * 2**30))
        before_data = None; after_data = None
        def before():
            nonlocal before_data
            authority(source, grant_ref, review_ref, contract_ref, time.time())
            before_data = live(c, False, command)
            need(ident(os.lstat(c['mutex']['path'])) == ident(os.fstat(mutex_fd)), 'mutex path replaced')
            journal('all_guards_passed', before_data)
        def after():
            nonlocal after_data
            after_data = live(c, True, command)
            need(ident(os.lstat(c['mutex']['path'])) == ident(os.fstat(mutex_fd)), 'mutex path replaced')
            journal('postconditions_passed', after_data)
        results = sequence(command, before, after, journal)
        record = dict(status='PASS_ACTUAL_SCRATCH_GROWTH_COMMANDS', grant=grant_ref,
                      execution_review=review_ref, bindings=binding, argv=COMMANDS,
                      returncodes=[x['returncode'] for x in results], results=results,
                      before=before_data, after=after_data)
        with open(out / 'actual-commands.json', 'x') as actual:
            actual.write(json.dumps(record, indent=2) + '\n')
            actual.flush(); os.fsync(actual.fileno())
        os.close(mutex_fd); mutex_fd = None
        journal('FD-CLOSED', dict(fd_closed=True, holder_pid=os.getpid(),
                                 parent_must_prove_retirement=True))
        # Deliberately no normal_fd_release or closed growth closure: parent proves join.
    except BaseException as e:
        try:
            journal('QUARANTINE' if mutation else 'PREFLIGHT_STOP',
                    dict(error=repr(e), mutation_may_have_effect=mutation, fd=mutex_fd,
                         child_pid=child.pid if child else None, holder_pid=os.getpid()))
        except BaseException:
            # Evidence-storage failure must never release an uncertain actual owner.
            pass
        if mutation:
            # Preserve actual owner FD and any child. Never kill an uncertain resize child.
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT):
                signal.signal(sig, signal.SIG_IGN)
            while True:
                signal.pause()
        if mutex_fd is not None:
            os.close(mutex_fd)
        raise
    finally:
        os.close(journal_fd)


if __name__ == '__main__':
    main()
