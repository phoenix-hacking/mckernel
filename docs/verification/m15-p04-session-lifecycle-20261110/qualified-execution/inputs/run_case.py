#!/usr/bin/python3
"""One controlled same-session lifecycle case; invoked only after Root admission."""
import ctypes
import errno
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import sys
import time

BASE = Path(__file__).resolve().parent
PAYLOAD = b"controlled lifecycle payload; not a real dump\n"


def proc(pid):
    raw = Path('/proc/' + str(pid) + '/stat').read_text()
    fields = raw.rsplit(') ', 1)[1].split()
    return {'pid': pid, 'state': fields[0], 'ppid': int(fields[1]),
            'pgid': int(fields[2]), 'sid': int(fields[3]), 'birth': int(fields[19])}


def children():
    return [int(x) for x in (Path('/proc/self/task') / str(os.getpid()) / 'children').read_text().split()]


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('baseline', 'candidate'):
        raise ValueError('exact baseline or candidate required')
    variant = sys.argv[1]
    out = BASE / 'output'
    d = out / variant
    control = d / 'control'
    abi = json.loads((out / 'abi-values.json').read_text())
    for key, value in {'siginfo_bytes': 128, 'siginfo_alignment': 8,
                       'idtype_unsigned32': True, 'pidfd_open': 434,
                       'pidfd_send_signal': 424, 'P_PIDFD': 3,
                       'process_control_calls': 0}.items():
        if abi.get(key) != value:
            raise RuntimeError('actual typed C ABI receipt missing: ' + key)
    if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL or children():
        raise RuntimeError('controller must own an empty default-SIGCHLD child scope')
    libc = ctypes.CDLL(None, use_errno=True)
    libc.syscall.restype = ctypes.c_long
    libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                          ctypes.c_ulong, ctypes.c_ulong]
    libc.prctl.restype = ctypes.c_int
    previous = ctypes.c_int()
    if libc.prctl(37, ctypes.addressof(previous), 0, 0, 0) != 0 or previous.value not in (0, 1):
        raise OSError(ctypes.get_errno(), 'controller subreaper query')
    if libc.prctl(36, 1, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'controller subreaper acquisition')

    p = None
    fds = {}
    identities = {}
    signals = []
    waits = []
    stdout = b''
    stderr = b''
    joined = False
    restored = False
    primary = None
    cleanup_errors = []
    state = {'phase': 'launch', 'variant': variant}
    observed_publication = None
    result = None
    started = time.monotonic()
    deadline = started + 8

    def left(end=deadline):
        value = end - time.monotonic()
        if value <= 0:
            raise TimeoutError('controlled lifecycle deadline')
        return value

    def ready(fd):
        poller = select.poll()
        poller.register(fd, select.POLLIN)
        events = poller.poll(0)
        if any(flags & (select.POLLERR | select.POLLNVAL) for _, flags in events):
            raise RuntimeError('owned pidfd poll error')
        return any(flags & select.POLLIN for _, flags in events)

    def bind_fd(role, identity):
        fd = libc.syscall(ctypes.c_long(434), ctypes.c_int(identity['pid']), ctypes.c_uint(0))
        if fd < 0:
            raise OSError(ctypes.get_errno(), 'pidfd_open ' + role)
        try:
            after = proc(identity['pid'])
            if any(after[key] != identity[key] for key in ('pid', 'birth', 'ppid', 'pgid', 'sid')):
                raise RuntimeError('controlled identity changed across pidfd_open: ' + role)
        except BaseException:
            # A failed proof never publishes a descriptor for cleanup to signal.
            # Preserve that original proof error even if closing also fails.
            try:
                os.close(int(fd))
            except BaseException as close_error:
                try:
                    cleanup_errors.append('unverified local pidfd close: ' + type(close_error).__name__ + ': ' + str(close_error))
                except BaseException:
                    pass
            raise
        identities[role] = after
        fds[role] = int(fd)
        return int(fd)

    def send_exact(role, reason):
        if role not in identities or role not in fds:
            raise RuntimeError('no authenticated identity/descriptor for signal: ' + role)
        identity = identities[role]
        fd = fds[role]
        if (type(fd) is not int or fd < 0 or type(identity.get('pid')) is not int
                or identity['pid'] <= 0 or type(identity.get('birth')) is not int
                or identity['birth'] <= 0):
            raise RuntimeError('invalid authenticated signal binding: ' + role)
        if ready(fd):
            return False
        if libc.syscall(ctypes.c_long(424), ctypes.c_int(fd), ctypes.c_int(signal.SIGKILL),
                        ctypes.c_void_p(), ctypes.c_uint(0)) < 0:
            raise OSError(ctypes.get_errno(), 'pidfd_send_signal ' + role)
        signals.append({'role': role, 'pid': identity['pid'],
                        'birth': identity['birth'], 'pidfd': fd,
                        'signal': signal.SIGKILL, 'reason': reason})
        return True

    def adopted_wait(role, end):
        pid = identities[role]['pid']
        while True:
            got, status = os.waitpid(pid, os.WNOHANG)
            if got == pid:
                waits.append({'role': role, 'pid': got, 'status': status,
                              'positive_adopted_wait': True})
                return status
            if got != 0:
                raise RuntimeError('unexpected exact adopted wait identity')
            time.sleep(min(0.005, left(end)))

    try:
        binary = out / ('vmcore-' + variant)
        argv = [str(binary), str(d / 'input'), str(d / 'mckdump')]
        state['argv'] = argv
        env = {'PATH': str(d / 'tools') + ':/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
               'VMCORE_LIFECYCLE_CONTROL': str(control),
               'VM_FIXTURE_UNAME_TRACE': str(control / 'uname.json')}
        p = subprocess.Popen(argv, env=env, cwd=BASE, stdin=subprocess.DEVNULL,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             start_new_session=True)
        bind_fd('wrapper', proc(p.pid))
        state['phase'] = 'controlled-family-binding'
        while not ((control / 'peer.json').is_file() and (control / 'descendant.json').is_file()):
            if ready(fds['wrapper']):
                raise RuntimeError('wrapper exited before controlled ownership handshake')
            time.sleep(min(0.005, left()))
        peer_trace = json.loads((control / 'peer.json').read_text())
        receipt = json.loads((control / 'descendant.json').read_text())
        peer = proc(peer_trace['pid'])
        child = proc(receipt['pid'])
        if peer['ppid'] != p.pid or peer['pgid'] != peer['pid'] or peer['sid'] != peer['pid']:
            raise RuntimeError('controlled peer is not the wrapper-owned private session leader')
        if (peer_trace.get('descendant') != child['pid'] or child['ppid'] != peer['pid']
                or child['birth'] != receipt.get('birth')
                or child['pgid'] != peer['pid'] or child['sid'] != peer['pid']
                or receipt.get('pgid') != peer['pid'] or receipt.get('sid') != peer['pid']
                or receipt.get('hup_ignored') is not True or receipt.get('pty_fds_closed') is not True):
            raise RuntimeError('controlled descendant identity/session/receipt mismatch')
        status_fields = dict(line.split(':', 1) for line in Path('/proc/' + str(child['pid']) + '/status').read_text().splitlines() if ':' in line)
        if not int(status_fields['SigIgn'].strip(), 16) & (1 << (signal.SIGHUP - 1)):
            raise RuntimeError('controlled descendant does not actually ignore SIGHUP')
        fdroot = Path('/proc/' + str(child['pid']) + '/fd')
        pipe_facts = []
        for entry in fdroot.iterdir():
            target = os.readlink(str(entry))
            if entry.name in ('0', '1', '2'):
                raise RuntimeError('controlled descendant retained a PTY standard descriptor')
            if target.startswith('pipe:['):
                info = (Path('/proc/' + str(child['pid']) + '/fdinfo') / entry.name).read_text()
                flags = int(next(line.split()[1] for line in info.splitlines() if line.startswith('flags:')), 8)
                pipe_facts.append({'fd': int(entry.name), 'target': target, 'access_mode': flags & os.O_ACCMODE})
        pairs = [target for target in {row['target'] for row in pipe_facts}
                 if {row['access_mode'] for row in pipe_facts if row['target'] == target} >= {os.O_RDONLY, os.O_WRONLY}]
        if len(pairs) != 1:
            raise RuntimeError('controlled descendant lacks its single self-held read/write pipe')
        bind_fd('peer', peer)
        bind_fd('descendant', child)
        if ready(fds['peer']) or ready(fds['descendant']):
            raise RuntimeError('controlled family exited before first prompt permission')
        binding = {'wrapper': identities['wrapper'], 'peer': identities['peer'],
                   'descendant': identities['descendant'], 'receipt': receipt,
                   'actual_SIGHUP_ignored': True, 'standard_PTY_fds_closed': True,
                   'self_held_pipe': [row for row in pipe_facts if row['target'] == pairs[0]],
                   'all_pidfds_live_before_first_prompt': True}
        (control / 'binding.json').write_text(json.dumps(binding, indent=2) + '\n')
        with (control / 'root-pidfd-owned').open('x') as trigger:
            trigger.write('exact controlled family pidfds and birth/session/pipe facts bound\n')
        state['phase'] = 'dialogue-and-publication'
        while True:
            if (d / 'mckdump').exists() and observed_publication is None:
                observed_publication = {'first_observer_visibility_seconds': time.monotonic() - started,
                                        'descendant_pidfd_readable': ready(fds['descendant']),
                                        'scope': 'first observer visibility, not a syscall-order trace'}
            if ready(fds['wrapper']):
                break
            time.sleep(min(0.005, left()))
        stdout, stderr = p.communicate(timeout=left())
        joined = p.returncode is not None
        if observed_publication is None and (d / 'mckdump').exists():
            observed_publication = {'first_observer_visibility_seconds': time.monotonic() - started,
                                    'descendant_pidfd_readable': ready(fds['descendant']),
                                    'scope': 'after positive wrapper wait; not a syscall-order trace'}
        state['phase'] = 'returned-wrapper-contract'
        trace = json.loads((control / 'peer.json').read_text())
        staging = Path(trace['staging_output'])
        expected_commands = ['mod -s ihk_smp_x86 ' + str(d / 'prefix/kmod/ihk-smp-x86.ko'),
                             'extend ' + str(d / 'prefix/lib/ldump2mcdump.so'),
                             'ldump2mcdump 0 -o ' + str(staging),
                             'extend -u ' + str(d / 'prefix/lib/ldump2mcdump.so'), 'quit']
        ack = b'MCKERNEL_LDUMP2MCDUMP_SUCCESS ' + os.fsencode(staging)
        if (p.returncode != 0 or not joined or trace.get('leader_exit') != 0
                or trace['argv'][1:] != ['/usr/lib/debug/lib/modules/fixture-linux/vmlinux', str(d / 'input')]
                or trace['commands'] != expected_commands
                or staging.parent != d or not staging.name.startswith('.vmcore2mckdump-' + str(p.pid) + '-')
                or staging.exists() or (d / 'mckdump').read_bytes() != PAYLOAD
                or ack not in stdout.replace(b'\r\n', b'\n').splitlines()
                or not stdout.endswith(('mcdump: ' + str(d / 'mckdump') + ' is extracted.\n').encode())):
            raise RuntimeError('controlled argv/status/dialogue/ACK/staging/output contract failed')
        uname = json.loads((control / 'uname.json').read_text())
        if uname['argv'][1:] != ['-r']:
            raise RuntimeError('controlled uname contract failed')
        state['phase'] = 'descendant-at-positive-wrapper-return'
        if variant == 'baseline':
            if ready(fds['descendant']):
                raise RuntimeError('baseline child died automatically; lifecycle defect was not reproduced')
            current = proc(child['pid'])
            if current['birth'] != child['birth'] or current['ppid'] != os.getpid():
                raise RuntimeError('baseline live leak was not adopted by this exact controller')
            got, status = os.waitpid(child['pid'], os.WNOHANG)
            if got != 0:
                raise RuntimeError('baseline leak is not positively owned and still alive')
            state['phase'] = 'expected-baseline-pidfd-rescue'
            if not send_exact('descendant', 'expected baseline live-child defect after successful publication'):
                raise RuntimeError('baseline leak disappeared before exact pidfd rescue')
            status = adopted_wait('descendant', time.monotonic() + 6)
            if not os.WIFSIGNALED(status) or os.WTERMSIG(status) != signal.SIGKILL:
                raise RuntimeError('baseline rescue did not positively join expected SIGKILL child')
            classification = 'FAIL_EXPECTED_BASELINE_PUBLISHED_WITH_LIVE_DESCENDANT'
            ownership = 'live birth-bound leak observed; one exact pidfd SIGKILL and positive adopted wait'
        else:
            if not ready(fds['descendant']):
                raise RuntimeError('candidate returned/published with live descendant')
            try:
                got, status = os.waitpid(child['pid'], os.WNOHANG)
            except ChildProcessError as error:
                if error.errno != errno.ECHILD:
                    raise
            else:
                if got:
                    waits.append({'role': 'descendant', 'pid': got, 'status': status,
                                  'unexpected_controller_adopted_reap': True})
                raise RuntimeError('candidate left an adopted child for the outer controller')
            if signals or waits:
                raise RuntimeError('candidate needed outer rescue/reap')
            if observed_publication is not None and not observed_publication['descendant_pidfd_readable']:
                raise RuntimeError('candidate publication observed before descendant death')
            classification = 'PASS_CANDIDATE_NO_OUTER_RESCUE_OR_ADOPTED_CHILD'
            ownership = 'child pidfd dead at positive wrapper return; exact wait gives ECHILD; no outer signal/reap'
        if children():
            raise RuntimeError('controller has unexplained residual direct children')
        result = {'status': classification, 'variant': variant, 'wrapper_exit': p.returncode,
                  'wrapper_parent_joined': joined, 'binding': binding, 'peer_trace': trace,
                  'matched_exact_ACK': ack.decode(), 'staging_after_publication_absent': True,
                  'output_bytes_hex': PAYLOAD.hex(), 'publication_observation': observed_publication,
                  'ownership_evidence': ownership,
                  'candidate_wait_before_publication_scope': 'Actual no-outer-adoption/pidfd observation plus independently reviewed candidate source: retire waits leader and adopted children to ECHILD, restores scope, returns from finish, then staging.publish. No syscall wait trace is claimed.'}
    except BaseException as error:
        primary = error
    finally:
        retirement_end = time.monotonic() + 6
        if primary is not None:
            try:
                if p is not None and not joined:
                    if 'wrapper' in fds:
                        send_exact('wrapper', 'unexpected case failure; descriptor-bound direct child')
                    p.wait(timeout=left(retirement_end))
                    joined = p.returncode is not None
                for role in ('peer', 'descendant'):
                    if role in fds:
                        send_exact(role, 'unexpected case failure; bound controlled family only')
                        try:
                            adopted_wait(role, retirement_end)
                        except ChildProcessError:
                            pass
            except BaseException as error:
                cleanup_errors.append(type(error).__name__ + ': ' + str(error))
        if p is not None:
            try:
                # Join/retire before draining pipes, preserving the qualified ordering.
                if joined:
                    stdout, stderr = p.communicate(timeout=left(retirement_end))
            except BaseException as error:
                cleanup_errors.append(type(error).__name__ + ': ' + str(error))
            for stream in (p.stdin, p.stdout, p.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
        remaining = children()
        if not remaining:
            if libc.prctl(36, previous.value, 0, 0, 0) == 0:
                actual_previous = ctypes.c_int()
                restored = libc.prctl(37, ctypes.addressof(actual_previous), 0, 0, 0) == 0 and actual_previous.value == previous.value
        for fd in fds.values():
            os.close(fd)
        final = dict(result or {'status': 'FAIL_UNEXPECTED', 'variant': variant})
        final.update(active=state, identities=identities, signals=signals, adopted_waits=waits,
                     wrapper_parent_joined=joined, remaining_direct_children=remaining,
                     subreaper_previous=previous.value, subreaper_restored=restored,
                     streams_closed=p is None or all(s is None or s.closed for s in (p.stdin, p.stdout, p.stderr)),
                     error=None if primary is None else type(primary).__name__ + ': ' + str(primary),
                     cleanup_errors=cleanup_errors, elapsed_seconds=time.monotonic() - started,
                     production_acceptance=False, real_dump=False)
        if cleanup_errors or remaining or not joined or not restored:
            final['status'] = 'FAIL_UNEXPECTED_OR_UNKNOWN_CUSTODY'
        (d / 'wrapper.stdout').write_bytes(stdout)
        (d / 'wrapper.stderr').write_bytes(stderr)
        (d / 'RESULT.json').write_text(json.dumps(final, indent=2) + '\n')
        print(json.dumps({k: v for k, v in final.items() if k not in ('binding', 'peer_trace')}))
    return 0 if final['status'].startswith(('PASS_CANDIDATE_', 'FAIL_EXPECTED_BASELINE_')) else 1


if __name__ == '__main__':
    sys.exit(main())
