"""Host-fixture owned-child retirement only; imported after explicit execution grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import ctypes,json,os,signal,subprocess,time
from pathlib import Path
class Owner:
    def __init__(self, output):
        self.output=Path(output);self.records=[]
        libc=ctypes.CDLL(None,use_errno=True)
        libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
        if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'fixture subreaper admission')
    def run(self,argv,env,cwd,timeout,label):
        p=subprocess.Popen(argv,env=env,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout=b'';stderr=b'';timed_out=False;leader_joined=False;birth=None
        reaped=[];killed=[];error=None;group_signalled=False
        try:
            try:
                birth=Path('/proc/'+str(p.pid)+'/stat').read_text().rsplit(') ',1)[1].split()[19]
                stdout,stderr=p.communicate(timeout=timeout)
                leader_joined=p.returncode is not None
            except BaseException as exc:
                error=exc;timed_out=isinstance(exc,subprocess.TimeoutExpired)
                if timed_out:stdout=exc.output or b'';stderr=exc.stderr or b''
            # After communicate fails, the leader is still our unreaped child.
            # Never poll/reap it before this exact original session signal.
            deadline=time.monotonic()+6
            def left():
                value=deadline-time.monotonic()
                if value<=0:raise TimeoutError('six-second retirement envelope exhausted')
                return value
            if error is not None and p.returncode is None:
                try:os.killpg(p.pid,signal.SIGKILL);group_signalled=True
                except ProcessLookupError:pass
            if not leader_joined:
                # Join before pipe drainage: adopted setsid peers can retain pipes.
                p.wait(timeout=left());leader_joined=True
            children_file=Path('/proc/self/task')/str(os.getpid())/'children'
            while True:
                children=[int(x) for x in children_file.read_text().split()]
                if not children:break
                left()
                for child in children:
                    # This sole-threaded owner has not reaped this direct child.
                    # A successful WNOHANG=0 protects its PID until our next reap.
                    got,status=os.waitpid(child,os.WNOHANG)
                    if got:reaped.append({'pid':got,'status':status});continue
                    try:os.kill(child,signal.SIGKILL);killed.append(child)
                    except ProcessLookupError:pass
                time.sleep(min(0.01,left()))
            if error is not None:
                # Python3.8 communicate retries retain accumulated output bytes.
                stdout,stderr=p.communicate(timeout=left())
        except BaseException as exc:
            # No false join/current-free claim if any child retirement is uncertain.
            error=exc
        finally:
            for stream in (p.stdin,p.stdout,p.stderr):
                if stream is not None and not stream.closed:stream.close()
            children_file=Path('/proc/self/task')/str(os.getpid())/'children'
            remaining=[int(x) for x in children_file.read_text().split()]
            (self.output/(label+'.stdout')).write_bytes(stdout)
            (self.output/(label+'.stderr')).write_bytes(stderr)
            record={'label':label,'leader':p.pid,'leader_birth':birth,'status':p.returncode if leader_joined else 'UNKNOWN','leader_parent_joined':leader_joined,'timed_out':timed_out,'leader_group_signalled':group_signalled,'adopted_reaps':reaped,'adopted_kills':killed,'whole_descendants_joined':leader_joined and not remaining,'remaining_direct_children':remaining,'streams_closed':all(s is None or s.closed for s in (p.stdin,p.stdout,p.stderr)),'error':None if error is None else type(error).__name__+': '+str(error)}
            self.records.append(record)
            (self.output/'ownership.json').write_text(json.dumps(self.records,indent=2)+'\n')
        if error is not None:raise RuntimeError(label+' failed; captures retained, no retry: '+str(error)) from error
        if killed:raise RuntimeError(label+' left a live adopted descendant; retired and failed, no retry')
        if not record['whole_descendants_joined']:raise RuntimeError(label+' retirement UNKNOWN; stop, no retry')
        return subprocess.CompletedProcess(argv,p.returncode,stdout,stderr)

    def run_ihkmond_main(self, argv, env, cwd, ready_timeout, stop_timeout, label, *, pidfd_api):
        """One real, disabled-IHK-worker daemon case, inside its own namespace.

        A failure never escapes this dedicated owner. Original handles, raw
        exceptions and tracebacks remain reachable until a reviewed disposition.
        The existing fixture run() above is deliberately not used or changed.
        """
        import errno
        import fcntl
        import hashlib
        import math
        import re
        import select
        import stat
        import traceback

        if hasattr(self, '_f08_custody'):
            # A second call must not replace the first invocation's handles.
            self._f08_reentry_error = RuntimeError('F08 Owner invocation already exists; no replay')
            while True:
                try:
                    time.sleep(60)
                except BaseException:
                    pass

        expected_argv = ['/usr/local/sbin/ihkmond', '-k', '0', '-i', '-1']
        expected_env = {'LANG': 'C', 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin',
                        'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': '/tmp'}
        expected_exe = 'b9cf237dbd3d6156f050418945d6fd60fd9738d6604f399013761865f6830447'
        state = {'schema': 'mckernel.m15.f08.inside-custody.v1', 'status': 'UNKNOWN',
                 'launcher': None, 'pidfd': None, 'daemon_pid': None,
                 'raw_primary': None, 'raw_secondaries': [], 'stdout': b'', 'stderr': b'',
                 'record': {'label': label, 'argv': argv, 'env': env, 'cwd': cwd,
                            'launcher_parent_joined': False, 'daemon_parent_joined': False,
                            'pidfd_closed': False, 'stop_attempted': False,
                            'stop_successful': False, 'readiness_observed': False}}
        self._f08_custody = state
        record = state['record']

        def require(ok, message):
            if not ok:
                raise RuntimeError(message)

        def keep_error(exc, primary=False):
            raw = (exc, BaseException.__dict__['__traceback__'].__get__(exc, type(exc)))
            if primary and state['raw_primary'] is None:
                state['raw_primary'] = raw
            else:
                state['raw_secondaries'].append(raw)

        def error_projection(raw):
            if raw is None:
                return None
            exc, tb = raw
            try:
                return {'type': type(exc).__name__, 'message': str(exc),
                        'traceback': ''.join(traceback.format_exception(type(exc), exc, tb))}
            except BaseException as diagnostic_error:
                keep_error(diagnostic_error)
                return {'type': type(exc).__name__, 'formatting': 'FAILED_RAW_RETAINED'}

        def write_json(name, value):
            data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
            with (self.output / name).open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(str(self.output), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

        def preserve_original_waits():
            # A late wait of the SAME direct handle is custody, not a new run.
            # A failed wait channel is retained for disposition, never replaced.
            p = state['launcher']
            if p is None or not getattr(p, '_child_created', False):
                return
            changed = False
            if not record['launcher_parent_joined'] and not state.get('launcher_wait_channel_failed'):
                try:
                    status = p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    return
                except BaseException as wait_error:
                    keep_error(wait_error)
                    state['launcher_wait_channel_failed'] = True
                    return
                else:
                    record['late_launcher_wait'] = {'pid': p.pid, 'exit': status,
                                                    'same_original_Popen': True}
                    record['launcher_parent_joined'] = True
                    changed = True
            if record['launcher_parent_joined'] and not record['daemon_parent_joined'] and not state.get('daemon_wait_channel_failed'):
                try:
                    if state['daemon_pid'] is None:
                        adopted = children()
                        record['late_original_adopted_candidates'] = adopted
                        if len(adopted) == 1:
                            state['daemon_pid'] = adopted[0]
                            record['late_discovered_adopted_raw_stat'] = (Path('/proc') / str(adopted[0]) / 'stat').read_text()
                            # This later ownership observation earns no identity,
                            # readiness or functional success credit.
                    if state['daemon_pid'] is not None:
                        pid = state['daemon_pid']
                        got, status = os.waitpid(pid, os.WNOHANG)
                        if got:
                            record['late_daemon_wait'] = {'pid': got, 'raw_status': status,
                                                         'same_inside_owner': True}
                            record['daemon_parent_joined'] = True
                            changed = True
                except BaseException as wait_error:
                    keep_error(wait_error)
                    state['daemon_wait_channel_failed'] = True
            if changed:
                try:
                    write_json(label + '.LATE-WAITS-' + str(int(record['launcher_parent_joined'])) +
                               '-' + str(int(record['daemon_parent_joined'])) + '.json',
                               {'status': 'UNKNOWN_ORIGINAL_FAILURE_PRESERVED', 'facts': record,
                                'no_resource_or_functional_release': True})
                except BaseException as capture_error:
                    keep_error(capture_error)

        def retain_unknown(exc):
            try:
                keep_error(exc, primary=True)
                state['status'] = 'UNKNOWN'
                record['status'] = 'UNKNOWN'
                # These are historical facts only, never an implicit wait/poll.
                record['original_pidfd_retained'] = state['pidfd']
                record['daemon_pid'] = state['daemon_pid']
                p = state['launcher']
                record['launcher_handle_retained'] = p is not None
                record['launcher_recorded_returncode'] = getattr(p, 'returncode', None)
                record['primary_error'] = error_projection(state['raw_primary'])
                record['secondary_errors'] = [error_projection(x) for x in tuple(state['raw_secondaries'])]
                write_json(label + '.UNKNOWN.json', record)
            except BaseException as diagnostic_error:
                try:
                    keep_error(diagnostic_error)
                except BaseException:
                    pass
            # No wait replacement, signal, container action, return or re-raise.
            # Keep the same state/self/Popen/pidfd and raw tracebacks in scope.
            while True:
                try:
                    preserve_original_waits()
                except BaseException as keeper_error:
                    try:
                        keep_error(keeper_error)
                    except BaseException:
                        pass
                try:
                    time.sleep(1)
                except BaseException as keeper_error:
                    try:
                        keep_error(keeper_error)
                    except BaseException:
                        pass

        def snapshot_owner():
            pid = os.getpid()
            proc = Path('/proc/self')
            raw_status = (proc / 'status').read_text()
            fields = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
            raw_stat = (proc / 'stat').read_text()
            fds = {}
            for name in sorted(os.listdir(str(proc / 'fd')), key=int):
                fd = int(name)
                try:
                    value = os.fstat(fd)
                    target = os.readlink(str(proc / 'fd' / name))
                    fds[name] = {'target': target, 'device': value.st_dev, 'inode': value.st_ino,
                                 'mode': value.st_mode, 'descriptor_flags': fcntl.fcntl(fd, fcntl.F_GETFD),
                                 'status_flags': fcntl.fcntl(fd, fcntl.F_GETFL)}
                except OSError as exc:
                    if exc.errno not in (errno.ENOENT, errno.EBADF):
                        raise
                    # listdir's own descriptor can already have been closed.
            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            child_subreaper = ctypes.c_int(-1)
            if libc.prctl(37, ctypes.addressof(child_subreaper), 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), 'GET_CHILD_SUBREAPER')
            root = os.stat('/')
            return {'pid': pid, 'birth': raw_stat.rsplit(') ', 1)[1].split()[19],
                    'namespace': {n: os.stat(str(proc / 'ns' / n)).st_ino for n in ('pid', 'mnt')},
                    'root': [root.st_dev, root.st_ino],
                    'uid': [int(x) for x in fields['Uid'].split()],
                    'gid': [int(x) for x in fields['Gid'].split()],
                    'tasks': sorted(os.listdir(str(proc / 'task')), key=int),
                    'fds': fds, 'signals': {n: fields[n].strip() for n in ('SigBlk', 'SigIgn', 'SigCgt')},
                    'subreaper': child_subreaper.value, 'raw_stat': raw_stat, 'raw_status': raw_status}

        def stable_owner(a, b):
            return all(a[k] == b[k] for k in ('pid', 'birth', 'namespace', 'root', 'uid', 'gid', 'tasks', 'fds', 'signals'))

        def children():
            return [int(x) for x in (Path('/proc/self/task') / str(os.getpid()) / 'children').read_text().split()]

        def remaining(deadline):
            left = deadline - time.monotonic()
            if not left > 0:
                raise TimeoutError('issued F08 deadline expired; custody retained')
            return left

        def live_daemon():
            pid = state['daemon_pid']
            require(children() == [pid], 'expected only the original adopted daemon')
            got, status = os.waitpid(pid, os.WNOHANG)
            if got:
                record['daemon_wait'] = {'pid': got, 'raw_status': status}
                record['daemon_parent_joined'] = True
                raise RuntimeError('original daemon terminated before the owned stop')
            require(got == 0, 'unexpected nonblocking daemon wait result')

        def identity(pid, with_hash=False):
            proc = Path('/proc') / str(pid)
            raw_stat = (proc / 'stat').read_text()
            parts = raw_stat.rsplit(') ', 1)[1].split()
            raw_status = (proc / 'status').read_text()
            fields = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
            raw_cmdline = (proc / 'cmdline').read_bytes()
            root = os.stat(str(proc / 'root'))
            with (proc / 'exe').open('rb') as executable:
                before = os.fstat(executable.fileno())
                digest = None
                if with_hash:
                    digest = hashlib.sha256()
                    for chunk in iter(lambda: executable.read(1024 * 1024), b''):
                        digest.update(chunk)
                    digest = digest.hexdigest()
                after = os.fstat(executable.fileno())
            shape = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
            require(shape(before) == shape(after) and stat.S_ISREG(before.st_mode), 'daemon executable changed during identity read')
            value = {'pid': pid, 'ppid': int(parts[1]), 'birth': parts[19], 'state': parts[0],
                     'uid': [int(x) for x in fields['Uid'].split()],
                     'gid': [int(x) for x in fields['Gid'].split()],
                     'namespace': {n: os.stat(str(proc / 'ns' / n)).st_ino for n in ('pid', 'mnt')},
                     'root': [root.st_dev, root.st_ino], 'executable': shape(before),
                     'exe_link': os.readlink(str(proc / 'exe')),
                     'cmdline_hex': raw_cmdline.hex(), 'sha256': digest,
                     'raw_stat': raw_stat, 'raw_status': raw_status}
            require(value['ppid'] == os.getpid(), 'daemon is not this inside Owner direct child')
            require(value['uid'] == [1000] * 4 and value['gid'] == [1000] * 4, 'daemon credentials differ')
            require(value['namespace'] == record['owner_after_constructor']['namespace'], 'daemon PID/mount namespace differs')
            require(value['root'] == record['owner_after_constructor']['root'], 'daemon root differs')
            require(value['exe_link'] == expected_argv[0], 'daemon executable path differs')
            require(raw_cmdline == b'\0'.join(x.encode() for x in expected_argv) + b'\0', 'daemon cmdline differs')
            if with_hash:
                require(digest == expected_exe, 'daemon ELF bytes differ from selected b9cf')
            raw_after = (proc / 'stat').read_text()
            after_parts = raw_after.rsplit(') ', 1)[1].split()
            require(after_parts[19] == value['birth'] and int(after_parts[1]) == os.getpid(), 'daemon birth/PPID bookend differs')
            value['raw_stat_after'] = raw_after
            return value

        def same_daemon(value):
            first = record['daemon_identity']
            require(all(value[k] == first[k] for k in ('pid', 'ppid', 'birth', 'uid', 'gid', 'namespace', 'root', 'executable', 'exe_link', 'cmdline_hex')), 'original daemon identity changed')

        def pidfd_live():
            fd = state['pidfd']
            raw = (Path('/proc/self/fdinfo') / str(fd)).read_text()
            match = re.search(r'^Pid:\s+(\d+)\s*$', raw, re.M)
            require(match is not None and int(match.group(1)) == state['daemon_pid'], 'pidfd does not bind the original daemon')
            require(os.readlink('/proc/self/fd/' + str(fd)) == 'anon_inode:[pidfd]', 'unexpected pidfd descriptor type')
            poller = select.poll()
            poller.register(fd, select.POLLIN)
            events = poller.poll(0)
            require(not events, 'original pidfd is terminal or invalid')
            return {'fd': fd, 'raw_fdinfo': raw, 'poll': events}

        def provider_mappings():
            pid = state['daemon_pid']
            proc = Path('/proc') / str(pid)
            raw_maps = (proc / 'maps').read_text()
            parsed = []
            for line in raw_maps.splitlines():
                parts = line.split(None, 5)
                require(len(parts) >= 5, 'unrecognized actual daemon mapping row')
                major, minor = (int(x, 16) for x in parts[3].split(':'))
                parsed.append({'range': parts[0], 'permissions': parts[1], 'offset': parts[2],
                               'major': major, 'minor': minor, 'inode': int(parts[4]),
                               'path': parts[5] if len(parts) == 6 else None, 'raw': line})
            expected = {
                expected_argv[0]: expected_exe,
                '/usr/local/lib64/libihk.so': 'b7bcafd0923de851cd04b3934207e7217065e28434e95e505d4ed5fd4bfc96c2',
                '/usr/lib64/libudev.so.1.7.10': '034fd62bb884d5ee2244966e96db2a40970de1a423f75057380fae67ea9d0cce',
                '/usr/lib64/libcap.so.2.69': '70e8dbe271e2ea63127fbc20270ce60541d1244f0b170888d258b86b2573bcbf'}
            inputs = self._f08_artifacts
            require(len(inputs) == len(expected) and {row['path'] for row in inputs} == set(expected),
                    'exact selected provider file inputs required')
            bound = []
            for source in inputs:
                path = source['path']
                require(source['sha256'] == expected[path], 'selected provider source digest differs')
                actual = os.stat(str(proc / 'root' / path.lstrip('/')))
                shape = [actual.st_dev, actual.st_ino, actual.st_mode, actual.st_size,
                         actual.st_mtime_ns, actual.st_ctime_ns]
                require(shape == source['identity'], 'daemon namespace provider identity differs')
                matches = [row for row in parsed if row['major'] == os.major(actual.st_dev) and
                           row['minor'] == os.minor(actual.st_dev) and row['inode'] == actual.st_ino]
                require(matches and any('x' in row['permissions'] for row in matches),
                        'selected provider has no actual executable daemon mapping')
                bound.append({'input': source, 'actual_child_file_identity': shape, 'mappings': matches})
            return {'raw_maps': raw_maps, 'selected_files': bound,
                    'complete_remaining_provider_graph': 'Reuse selected46d graph; raw maps retained, no new graph acceptance.'}

        def readiness():
            pid = state['daemon_pid']
            proc = Path('/proc') / str(pid)
            sample = {'at_monotonic': time.monotonic(), 'fds': {}, 'tasks': sorted(os.listdir(str(proc / 'task')), key=int)}
            names = sorted(os.listdir(str(proc / 'fd')), key=int)
            try:
                for name in names:
                    sample['fds'][name] = {'target': os.readlink(str(proc / 'fd' / name)),
                                           'fdinfo': (proc / 'fdinfo' / name).read_text()}
            except FileNotFoundError:
                sample['incomplete'] = 'FD table changed during startup observation'
                return sample, False
            sample['raw_syscall'] = (proc / 'syscall').read_text()
            sample['raw_netlink'] = (proc / 'net/netlink').read_text()
            sample['raw_status'] = (proc / 'status').read_text()
            sample['fd_names_after'] = sorted(os.listdir(str(proc / 'fd')), key=int)
            if names != sample['fd_names_after'] or sample['tasks'] != [str(pid)]:
                return sample, False
            by_target = lambda target: [int(n) for n, row in sample['fds'].items() if row['target'] == target]
            epolls = by_target('anon_inode:[eventpoll]')
            signals = by_target('anon_inode:[signalfd]')
            done = by_target('anon_inode:[eventfd]')
            if not (len(epolls) == len(signals) == len(done) == 1):
                return sample, False
            ep, sig, event = epolls[0], signals[0], done[0]
            mask = re.search(r'^sigmask:\s*([0-9a-fA-F]+)\s*$', sample['fds'][str(sig)]['fdinfo'], re.M)
            count = re.search(r'^eventfd-count:\s*([0-9a-fA-F]+)\s*$', sample['fds'][str(event)]['fdinfo'], re.M)
            if mask is None or int(mask.group(1), 16) != 0x4002 or count is None or int(count.group(1), 16) != 0:
                return sample, False
            watches = []
            for line in sample['fds'][str(ep)]['fdinfo'].splitlines():
                if line.startswith('tfd:'):
                    match = re.match(r'^tfd:\s*(\d+)\s+events:\s*([0-9a-fA-F]+)\s+data:\s*([0-9a-fA-F]+)\b', line)
                    require(match is not None, 'unrecognized actual epoll watch record')
                    fd, events, data = int(match.group(1)), int(match.group(2), 16), int(match.group(3), 16)
                    watches.append({'fd': fd, 'events': events, 'data': data, 'raw': line})
            sample['epoll_watches'] = watches
            if len(watches) != 3 or len({row['fd'] for row in watches}) != 3:
                return sample, False
            watched = {row['fd'] for row in watches}
            if not ({sig, event} < watched) or any(not row['events'] & 1 or row['data'] != row['fd'] for row in watches):
                return sample, False
            monfd = next(iter(watched - {sig, event}))
            socket = re.fullmatch(r'socket:\[(\d+)\]', sample['fds'].get(str(monfd), {}).get('target', ''))
            if socket is None:
                return sample, False
            inode = int(socket.group(1))
            matching = []
            for line in sample['raw_netlink'].splitlines()[1:]:
                fields = line.split()
                if len(fields) == 10 and int(fields[-1]) == inode:
                    matching.append({'protocol': int(fields[1]), 'port_id': int(fields[2]),
                                     'groups': int(fields[3], 16), 'inode': inode, 'raw': line})
            sample['monitor_netlink'] = matching
            if len(matching) != 1 or matching[0]['protocol'] != 15 or matching[0]['groups'] == 0:
                return sample, False
            fields = dict(line.split(':', 1) for line in sample['raw_status'].splitlines() if ':' in line)
            expected_mask = int(record['owner_after_constructor']['signals']['SigBlk'], 16) | 0x4002
            if int(fields['SigBlk'].strip(), 16) != expected_mask:
                return sample, False
            call = sample['raw_syscall'].split()
            # Selected Linux x86_64 epoll_wait UAPI: epfd, events, maxevents, ms.
            if len(call) < 5 or call[0] != '232':
                return sample, False
            if int(call[1], 0) != ep or int(call[3], 0) != 3 or int(call[4], 0) != 250:
                return sample, False
            sample['bound_fds'] = {'epoll': ep, 'signalfd': sig, 'doneeventfd': event, 'monitor': monfd}
            return sample, True

        try:
            require(argv == expected_argv and env == expected_env and cwd == '/output', 'F08 exact payload binding differs')
            require(label == 'ihkmond-main-k0-i-1' and self.output == Path('/output'), 'F08 output/label binding differs')
            for value in (ready_timeout, stop_timeout):
                require(type(value) in (int, float) and math.isfinite(value) and value > 0, 'issued positive finite F08 deadlines required')
            record['owner_before_constructor'] = self._f08_preconstructor_baseline
            record['owner_after_constructor'] = snapshot_owner()
            require(stable_owner(record['owner_before_constructor'], record['owner_after_constructor']), 'constructor changed dedicated-owner fd/task/signal/identity baseline')
            require(record['owner_after_constructor']['subreaper'] == 1, 'inside Owner is not a subreaper')
            require(record['owner_after_constructor']['tasks'] == [str(os.getpid())] and not children(), 'dedicated sole-threaded child-free Owner required')
            record['operation'] = self._f08_operation
            record['provider_namespace_inputs'] = self._f08_artifacts
            record['readiness_timeout_seconds'] = ready_timeout
            record['stop_timeout_seconds'] = stop_timeout
            pidfd_api.require_implementation()
            ready_deadline = time.monotonic() + ready_timeout
            # Register the actual Popen object before its constructor can launch.
            p = subprocess.Popen.__new__(subprocess.Popen)
            state['launcher'] = p
            subprocess.Popen.__init__(p, argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            record['launcher_pid'] = p.pid
            raw = (Path('/proc') / str(p.pid) / 'stat').read_text()
            parts = raw.rsplit(') ', 1)[1].split()
            require(int(parts[1]) == os.getpid() and int(parts[19]) > 0, 'launcher birth/PPID binding failed')
            record['launcher_birth'] = parts[19]
            record['launcher_raw_stat'] = raw
            state['stdout'], state['stderr'] = p.communicate(timeout=remaining(ready_deadline))
            record['launcher_parent_joined'] = p.returncode is not None
            record['launcher_exit'] = p.returncode
            for suffix, data in (('stdout', state['stdout']), ('stderr', state['stderr'])):
                with (self.output / (label + '.' + suffix)).open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            require(record['launcher_parent_joined'] and p.returncode == 0, 'real launcher did not positively join0')
            require(state['stdout'] == b'' and state['stderr'] == b'', 'unexpected real launcher output')
            actual_children = children()
            record['children_after_launcher'] = actual_children
            require(len(actual_children) == 1, 'expected one actually adopted daemon after launcher join')
            state['daemon_pid'] = actual_children[0]
            live_daemon()
            record['daemon_identity'] = identity(state['daemon_pid'], with_hash=True)
            try:
                state['pidfd'] = pidfd_api.open_pidfd(state['daemon_pid'], flags=0)
            except BaseException as exc:
                if isinstance(exc, pidfd_api.PidfdVerificationError):
                    state['pidfd'] = exc.fd
                raise
            record['pidfd_binding'] = pidfd_live()
            same_daemon(identity(state['daemon_pid']))
            require(not record['stop_attempted'], 'stop was already attempted')
            observations = 0
            while True:
                remaining(ready_deadline)
                live_daemon()
                same_daemon(identity(state['daemon_pid']))
                sample, ready = readiness()
                state['last_readiness_raw'] = sample
                observations += 1
                row = {'sequence': observations, 'ready': ready, 'raw': sample}
                data = (json.dumps(row, sort_keys=True) + '\n').encode()
                with (self.output / (label + '.readiness.jsonl')).open('ab') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                live_daemon()
                same_daemon(identity(state['daemon_pid']))
                pidfd_live()
                if ready:
                    record['readiness_observed'] = True
                    record['readiness_sequence'] = observations
                    record['readiness_raw'] = sample
                    record['daemon_provider_mappings'] = provider_mappings()
                    break
                time.sleep(min(0.02, remaining(ready_deadline)))
            remaining(ready_deadline)
            live_daemon()
            record['daemon_before_stop'] = identity(state['daemon_pid'], with_hash=True)
            same_daemon(record['daemon_before_stop'])
            record['pidfd_before_stop'] = pidfd_live()
            record['stop_intent'] = {'pidfd': state['pidfd'], 'pid': state['daemon_pid'],
                                     'birth': record['daemon_identity']['birth'], 'signal': 15,
                                     'at_monotonic': time.monotonic()}
            write_json(label + '.STOP-INTENT.json', record['stop_intent'])
            remaining(ready_deadline)
            stop_deadline = time.monotonic() + stop_timeout
            record['stop_attempted'] = True
            pidfd_api.send_signal(state['pidfd'], signal.SIGTERM, flags=0)
            record['stop_successful'] = True
            write_json(label + '.STOP-RESULT.json', {'successful': True, 'signal': 15, 'at_monotonic': time.monotonic()})
            while True:
                remaining(stop_deadline)
                got, status = os.waitpid(state['daemon_pid'], os.WNOHANG)
                if got:
                    record['daemon_parent_joined'] = True
                    record['daemon_wait'] = {'pid': got, 'raw_status': status,
                                             'WIFEXITED': os.WIFEXITED(status),
                                             'exit': os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
                                             'WIFSIGNALED': os.WIFSIGNALED(status)}
                    require(got == state['daemon_pid'] and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0,
                            'original daemon did not positively exit0')
                    break
                time.sleep(min(0.01, remaining(stop_deadline)))
            for stream in (p.stdin, p.stdout, p.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            record['launcher_streams_closed'] = all(s is None or s.closed for s in (p.stdin, p.stdout, p.stderr))
            fd = state['pidfd']
            os.close(fd)
            state['pidfd'] = None
            record['pidfd_closed'] = True
            record['children_after_waits'] = children()
            require(not record['children_after_waits'] and record['launcher_streams_closed'], 'child/stream retirement incomplete')
            record['owner_after_waits'] = snapshot_owner()
            require(stable_owner(record['owner_before_constructor'], record['owner_after_waits']), 'dedicated-owner fd/task/signal/identity baseline differs')
            require(record['owner_after_waits']['subreaper'] == 1, 'subreaper unexpectedly changed')
            record['subreaper_scope'] = 'Remains1 for this dedicated Owner; no prctl restoration is claimed.'
            record['daemon_kernel_fd_table_retired'] = True
            record['source_inferences_only'] = ['prior checked real udev calls succeeded to reach the observed state',
                                               'normal Rust RAII branch and saved child signal-mask restoration']
            record['status'] = 'PASS'
            write_json(label + '.RESULT.json', record)
            self.records.append(record)
            state['status'] = 'PASS'
            return record
        except BaseException as exc:
            retain_unknown(exc)


# Private additive case; the complete qualified base above is unchanged.
class ActiveKmsgOwner(Owner):
    def run_ihkmond_active_kmsg(self, argv, env, cwd, ready_timeout, stop_timeout, label, *, pidfd_api):
        """One real, separately admitted active-kmsg-worker case in its owned namespace.

        A failure never escapes this dedicated owner. Original handles, raw
        exceptions and tracebacks remain reachable until a reviewed disposition.
        The existing fixture run() above is deliberately not used or changed.
        """
        import errno
        import fcntl
        import hashlib
        import math
        import re
        import select
        import stat
        import traceback

        if hasattr(self, '_f08_custody'):
            # A second call must not replace the first invocation's handles.
            self._f08_reentry_error = RuntimeError('F08 Owner invocation already exists; no replay')
            while True:
                try:
                    time.sleep(60)
                except BaseException:
                    pass

        expected_argv = ['/usr/local/sbin/ihkmond', '-k', '1', '-i', '-1']
        expected_env = {'LANG': 'C', 'LC_ALL': 'C', 'PATH': '/usr/bin:/bin',
                        'TZ': 'UTC', 'PYTHONDONTWRITEBYTECODE': '1', 'TMPDIR': '/tmp'}
        expected_exe = 'b9cf237dbd3d6156f050418945d6fd60fd9738d6604f399013761865f6830447'
        state = {'schema': 'mckernel.m15.f08.inside-active-kmsg-custody.v1', 'status': 'UNKNOWN',
                 'launcher': None, 'pidfd': None, 'daemon_pid': None,
                 'raw_primary': None, 'raw_secondaries': [], 'stdout': b'', 'stderr': b'',
                 'record': {'label': label, 'argv': argv, 'env': env, 'cwd': cwd,
                            'launcher_parent_joined': False, 'daemon_parent_joined': False,
                            'pidfd_closed': False, 'stop_attempted': False,
                            'stop_successful': False, 'readiness_observed': False}}
        self._f08_custody = state
        record = state['record']

        def require(ok, message):
            if not ok:
                raise RuntimeError(message)

        def keep_error(exc, primary=False):
            raw = (exc, BaseException.__dict__['__traceback__'].__get__(exc, type(exc)))
            if primary and state['raw_primary'] is None:
                state['raw_primary'] = raw
            else:
                state['raw_secondaries'].append(raw)

        def error_projection(raw):
            if raw is None:
                return None
            exc, tb = raw
            try:
                return {'type': type(exc).__name__, 'message': str(exc),
                        'traceback': ''.join(traceback.format_exception(type(exc), exc, tb))}
            except BaseException as diagnostic_error:
                keep_error(diagnostic_error)
                return {'type': type(exc).__name__, 'formatting': 'FAILED_RAW_RETAINED'}

        def write_json(name, value):
            data = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
            with (self.output / name).open('xb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            directory = os.open(str(self.output), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

        def preserve_original_waits():
            # A late wait of the SAME direct handle is custody, not a new run.
            # A failed wait channel is retained for disposition, never replaced.
            p = state['launcher']
            if p is None or not getattr(p, '_child_created', False):
                return
            changed = False
            if not record['launcher_parent_joined'] and not state.get('launcher_wait_channel_failed'):
                try:
                    status = p.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    return
                except BaseException as wait_error:
                    keep_error(wait_error)
                    state['launcher_wait_channel_failed'] = True
                    return
                else:
                    record['late_launcher_wait'] = {'pid': p.pid, 'exit': status,
                                                    'same_original_Popen': True}
                    record['launcher_parent_joined'] = True
                    changed = True
            if record['launcher_parent_joined'] and not record['daemon_parent_joined'] and not state.get('daemon_wait_channel_failed'):
                try:
                    if state['daemon_pid'] is None:
                        adopted = children()
                        record['late_original_adopted_candidates'] = adopted
                        if len(adopted) == 1:
                            state['daemon_pid'] = adopted[0]
                            record['late_discovered_adopted_raw_stat'] = (Path('/proc') / str(adopted[0]) / 'stat').read_text()
                            # This later ownership observation earns no identity,
                            # readiness or functional success credit.
                    if state['daemon_pid'] is not None:
                        pid = state['daemon_pid']
                        got, status = os.waitpid(pid, os.WNOHANG)
                        if got:
                            record['late_daemon_wait'] = {'pid': got, 'raw_status': status,
                                                         'same_inside_owner': True}
                            record['daemon_parent_joined'] = True
                            changed = True
                except BaseException as wait_error:
                    keep_error(wait_error)
                    state['daemon_wait_channel_failed'] = True
            if changed:
                try:
                    write_json(label + '.LATE-WAITS-' + str(int(record['launcher_parent_joined'])) +
                               '-' + str(int(record['daemon_parent_joined'])) + '.json',
                               {'status': 'UNKNOWN_ORIGINAL_FAILURE_PRESERVED', 'facts': record,
                                'no_resource_or_functional_release': True})
                except BaseException as capture_error:
                    keep_error(capture_error)

        def retain_unknown(exc):
            try:
                keep_error(exc, primary=True)
                state['status'] = 'UNKNOWN'
                record['status'] = 'UNKNOWN'
                # These are historical facts only, never an implicit wait/poll.
                record['original_pidfd_retained'] = state['pidfd']
                record['daemon_pid'] = state['daemon_pid']
                p = state['launcher']
                record['launcher_handle_retained'] = p is not None
                record['launcher_recorded_returncode'] = getattr(p, 'returncode', None)
                record['primary_error'] = error_projection(state['raw_primary'])
                record['secondary_errors'] = [error_projection(x) for x in tuple(state['raw_secondaries'])]
                write_json(label + '.UNKNOWN.json', record)
            except BaseException as diagnostic_error:
                try:
                    keep_error(diagnostic_error)
                except BaseException:
                    pass
            # No wait replacement, signal, container action, return or re-raise.
            # Keep the same state/self/Popen/pidfd and raw tracebacks in scope.
            while True:
                try:
                    preserve_original_waits()
                except BaseException as keeper_error:
                    try:
                        keep_error(keeper_error)
                    except BaseException:
                        pass
                try:
                    time.sleep(1)
                except BaseException as keeper_error:
                    try:
                        keep_error(keeper_error)
                    except BaseException:
                        pass

        def snapshot_owner():
            pid = os.getpid()
            proc = Path('/proc/self')
            raw_status = (proc / 'status').read_text()
            fields = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
            raw_stat = (proc / 'stat').read_text()
            fds = {}
            for name in sorted(os.listdir(str(proc / 'fd')), key=int):
                fd = int(name)
                try:
                    value = os.fstat(fd)
                    target = os.readlink(str(proc / 'fd' / name))
                    fds[name] = {'target': target, 'device': value.st_dev, 'inode': value.st_ino,
                                 'mode': value.st_mode, 'descriptor_flags': fcntl.fcntl(fd, fcntl.F_GETFD),
                                 'status_flags': fcntl.fcntl(fd, fcntl.F_GETFL)}
                except OSError as exc:
                    if exc.errno not in (errno.ENOENT, errno.EBADF):
                        raise
                    # listdir's own descriptor can already have been closed.
            libc = ctypes.CDLL(None, use_errno=True)
            libc.prctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong]
            child_subreaper = ctypes.c_int(-1)
            if libc.prctl(37, ctypes.addressof(child_subreaper), 0, 0, 0) != 0:
                raise OSError(ctypes.get_errno(), 'GET_CHILD_SUBREAPER')
            root = os.stat('/')
            return {'pid': pid, 'birth': raw_stat.rsplit(') ', 1)[1].split()[19],
                    'namespace': {n: os.stat(str(proc / 'ns' / n)).st_ino for n in ('pid', 'mnt')},
                    'root': [root.st_dev, root.st_ino],
                    'uid': [int(x) for x in fields['Uid'].split()],
                    'gid': [int(x) for x in fields['Gid'].split()],
                    'tasks': sorted(os.listdir(str(proc / 'task')), key=int),
                    'fds': fds, 'signals': {n: fields[n].strip() for n in ('SigBlk', 'SigIgn', 'SigCgt')},
                    'subreaper': child_subreaper.value, 'raw_stat': raw_stat, 'raw_status': raw_status}

        def stable_owner(a, b):
            return all(a[k] == b[k] for k in ('pid', 'birth', 'namespace', 'root', 'uid', 'gid', 'tasks', 'fds', 'signals'))

        def children():
            return [int(x) for x in (Path('/proc/self/task') / str(os.getpid()) / 'children').read_text().split()]

        def remaining(deadline):
            left = deadline - time.monotonic()
            if not left > 0:
                raise TimeoutError('issued F08 deadline expired; custody retained')
            return left

        def live_daemon():
            pid = state['daemon_pid']
            require(children() == [pid], 'expected only the original adopted daemon')
            got, status = os.waitpid(pid, os.WNOHANG)
            if got:
                record['daemon_wait'] = {'pid': got, 'raw_status': status}
                record['daemon_parent_joined'] = True
                raise RuntimeError('original daemon terminated before the owned stop')
            require(got == 0, 'unexpected nonblocking daemon wait result')

        def identity(pid, with_hash=False):
            proc = Path('/proc') / str(pid)
            raw_stat = (proc / 'stat').read_text()
            parts = raw_stat.rsplit(') ', 1)[1].split()
            raw_status = (proc / 'status').read_text()
            fields = dict(line.split(':', 1) for line in raw_status.splitlines() if ':' in line)
            raw_cmdline = (proc / 'cmdline').read_bytes()
            root = os.stat(str(proc / 'root'))
            with (proc / 'exe').open('rb') as executable:
                before = os.fstat(executable.fileno())
                digest = None
                if with_hash:
                    digest = hashlib.sha256()
                    for chunk in iter(lambda: executable.read(1024 * 1024), b''):
                        digest.update(chunk)
                    digest = digest.hexdigest()
                after = os.fstat(executable.fileno())
            shape = lambda s: [s.st_dev, s.st_ino, s.st_mode, s.st_size, s.st_mtime_ns, s.st_ctime_ns]
            require(shape(before) == shape(after) and stat.S_ISREG(before.st_mode), 'daemon executable changed during identity read')
            value = {'pid': pid, 'ppid': int(parts[1]), 'birth': parts[19], 'state': parts[0],
                     'uid': [int(x) for x in fields['Uid'].split()],
                     'gid': [int(x) for x in fields['Gid'].split()],
                     'namespace': {n: os.stat(str(proc / 'ns' / n)).st_ino for n in ('pid', 'mnt')},
                     'root': [root.st_dev, root.st_ino], 'executable': shape(before),
                     'exe_link': os.readlink(str(proc / 'exe')),
                     'cmdline_hex': raw_cmdline.hex(), 'sha256': digest,
                     'raw_stat': raw_stat, 'raw_status': raw_status}
            require(value['ppid'] == os.getpid(), 'daemon is not this inside Owner direct child')
            require(value['uid'] == [1000] * 4 and value['gid'] == [1000] * 4, 'daemon credentials differ')
            require(value['namespace'] == record['owner_after_constructor']['namespace'], 'daemon PID/mount namespace differs')
            require(value['root'] == record['owner_after_constructor']['root'], 'daemon root differs')
            require(value['exe_link'] == expected_argv[0], 'daemon executable path differs')
            require(raw_cmdline == b'\0'.join(x.encode() for x in expected_argv) + b'\0', 'daemon cmdline differs')
            if with_hash:
                require(digest == expected_exe, 'daemon ELF bytes differ from selected b9cf')
            raw_after = (proc / 'stat').read_text()
            after_parts = raw_after.rsplit(') ', 1)[1].split()
            require(after_parts[19] == value['birth'] and int(after_parts[1]) == os.getpid(), 'daemon birth/PPID bookend differs')
            value['raw_stat_after'] = raw_after
            return value

        def same_daemon(value):
            first = record['daemon_identity']
            require(all(value[k] == first[k] for k in ('pid', 'ppid', 'birth', 'uid', 'gid', 'namespace', 'root', 'executable', 'exe_link', 'cmdline_hex')), 'original daemon identity changed')

        def pidfd_live():
            fd = state['pidfd']
            raw = (Path('/proc/self/fdinfo') / str(fd)).read_text()
            match = re.search(r'^Pid:\s+(\d+)\s*$', raw, re.M)
            require(match is not None and int(match.group(1)) == state['daemon_pid'], 'pidfd does not bind the original daemon')
            require(os.readlink('/proc/self/fd/' + str(fd)) == 'anon_inode:[pidfd]', 'unexpected pidfd descriptor type')
            poller = select.poll()
            poller.register(fd, select.POLLIN)
            events = poller.poll(0)
            require(not events, 'original pidfd is terminal or invalid')
            return {'fd': fd, 'raw_fdinfo': raw, 'poll': events}

        def provider_mappings():
            pid = state['daemon_pid']
            proc = Path('/proc') / str(pid)
            raw_maps = (proc / 'maps').read_text()
            parsed = []
            for line in raw_maps.splitlines():
                parts = line.split(None, 5)
                require(len(parts) >= 5, 'unrecognized actual daemon mapping row')
                major, minor = (int(x, 16) for x in parts[3].split(':'))
                parsed.append({'range': parts[0], 'permissions': parts[1], 'offset': parts[2],
                               'major': major, 'minor': minor, 'inode': int(parts[4]),
                               'path': parts[5] if len(parts) == 6 else None, 'raw': line})
            expected = {
                expected_argv[0]: expected_exe,
                '/usr/local/lib64/libihk.so': 'b7bcafd0923de851cd04b3934207e7217065e28434e95e505d4ed5fd4bfc96c2',
                '/usr/lib64/libudev.so.1.7.10': '034fd62bb884d5ee2244966e96db2a40970de1a423f75057380fae67ea9d0cce',
                '/usr/lib64/libcap.so.2.69': '70e8dbe271e2ea63127fbc20270ce60541d1244f0b170888d258b86b2573bcbf'}
            inputs = self._f08_artifacts
            require(len(inputs) == len(expected) and {row['path'] for row in inputs} == set(expected),
                    'exact selected provider file inputs required')
            bound = []
            for source in inputs:
                path = source['path']
                require(source['sha256'] == expected[path], 'selected provider source digest differs')
                actual = os.stat(str(proc / 'root' / path.lstrip('/')))
                shape = [actual.st_dev, actual.st_ino, actual.st_mode, actual.st_size,
                         actual.st_mtime_ns, actual.st_ctime_ns]
                require(shape == source['identity'], 'daemon namespace provider identity differs')
                matches = [row for row in parsed if row['major'] == os.major(actual.st_dev) and
                           row['minor'] == os.minor(actual.st_dev) and row['inode'] == actual.st_ino]
                require(matches and any('x' in row['permissions'] for row in matches),
                        'selected provider has no actual executable daemon mapping')
                bound.append({'input': source, 'actual_child_file_identity': shape, 'mappings': matches})
            return {'raw_maps': raw_maps, 'selected_files': bound,
                    'complete_remaining_provider_graph': 'Reuse selected46d graph; raw maps retained, no new graph acceptance.'}

        def readiness():
            return self._f08_active_observer.initial_readiness(state['daemon_pid'], record)

        def active_live_guard():
            live_daemon()
            same_daemon(identity(state['daemon_pid']))
            pidfd_live()

        try:
            require(argv == expected_argv and env == expected_env and cwd == '/output', 'F08 exact payload binding differs')
            require(label == 'ihkmond-main-k1-i-1-real-add-remove' and self.output == Path('/output'), 'F08 output/label binding differs')
            for value in (ready_timeout, stop_timeout):
                require(type(value) in (int, float) and math.isfinite(value) and value > 0, 'issued positive finite F08 deadlines required')
            record['owner_before_constructor'] = self._f08_preconstructor_baseline
            record['owner_after_constructor'] = snapshot_owner()
            require(stable_owner(record['owner_before_constructor'], record['owner_after_constructor']), 'constructor changed dedicated-owner fd/task/signal/identity baseline')
            require(record['owner_after_constructor']['subreaper'] == 1, 'inside Owner is not a subreaper')
            require(record['owner_after_constructor']['tasks'] == [str(os.getpid())] and not children(), 'dedicated sole-threaded child-free Owner required')
            record['operation'] = self._f08_operation
            record['provider_namespace_inputs'] = self._f08_artifacts
            record['readiness_timeout_seconds'] = ready_timeout
            record['stop_timeout_seconds'] = stop_timeout
            require(isinstance(self._f08_active_observer, ActiveKmsgObserver),
                    'actual Root backend/input observer binding required')
            self._f08_active_observer.preflight()
            pidfd_api.require_implementation()
            ready_deadline = time.monotonic() + ready_timeout
            # Register the actual Popen object before its constructor can launch.
            p = subprocess.Popen.__new__(subprocess.Popen)
            state['launcher'] = p
            subprocess.Popen.__init__(p, argv, env=env, cwd=cwd, stdin=subprocess.DEVNULL,
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
            record['launcher_pid'] = p.pid
            raw = (Path('/proc') / str(p.pid) / 'stat').read_text()
            parts = raw.rsplit(') ', 1)[1].split()
            require(int(parts[1]) == os.getpid() and int(parts[19]) > 0, 'launcher birth/PPID binding failed')
            record['launcher_birth'] = parts[19]
            record['launcher_raw_stat'] = raw
            state['stdout'], state['stderr'] = p.communicate(timeout=remaining(ready_deadline))
            record['launcher_parent_joined'] = p.returncode is not None
            record['launcher_exit'] = p.returncode
            for suffix, data in (('stdout', state['stdout']), ('stderr', state['stderr'])):
                with (self.output / (label + '.' + suffix)).open('xb') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
            require(record['launcher_parent_joined'] and p.returncode == 0, 'real launcher did not positively join0')
            require(state['stdout'] == b'' and state['stderr'] == b'', 'unexpected real launcher output')
            actual_children = children()
            record['children_after_launcher'] = actual_children
            require(len(actual_children) == 1, 'expected one actually adopted daemon after launcher join')
            state['daemon_pid'] = actual_children[0]
            live_daemon()
            record['daemon_identity'] = identity(state['daemon_pid'], with_hash=True)
            try:
                state['pidfd'] = pidfd_api.open_pidfd(state['daemon_pid'], flags=0)
            except BaseException as exc:
                if isinstance(exc, pidfd_api.PidfdVerificationError):
                    state['pidfd'] = exc.fd
                raise
            record['pidfd_binding'] = pidfd_live()
            same_daemon(identity(state['daemon_pid']))
            require(not record['stop_attempted'], 'stop was already attempted')
            observations = 0
            while True:
                remaining(ready_deadline)
                live_daemon()
                same_daemon(identity(state['daemon_pid']))
                sample, ready = readiness()
                state['last_readiness_raw'] = sample
                observations += 1
                row = {'sequence': observations, 'ready': ready, 'raw': sample}
                data = (json.dumps(row, sort_keys=True) + '\n').encode()
                with (self.output / (label + '.readiness.jsonl')).open('ab') as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                live_daemon()
                same_daemon(identity(state['daemon_pid']))
                pidfd_live()
                if ready:
                    record['readiness_observed'] = True
                    record['readiness_sequence'] = observations
                    record['readiness_raw'] = sample
                    record['daemon_provider_mappings'] = provider_mappings()
                    break
                time.sleep(min(0.02, remaining(ready_deadline)))
            ready_deadline = self._f08_active_observer.observe(
                state['daemon_pid'], record, active_live_guard, remaining)
            remaining(ready_deadline)
            live_daemon()
            record['daemon_before_stop'] = identity(state['daemon_pid'], with_hash=True)
            same_daemon(record['daemon_before_stop'])
            record['pidfd_before_stop'] = pidfd_live()
            record['stop_intent'] = {'pidfd': state['pidfd'], 'pid': state['daemon_pid'],
                                     'birth': record['daemon_identity']['birth'], 'signal': 15,
                                     'at_monotonic': time.monotonic()}
            write_json(label + '.STOP-INTENT.json', record['stop_intent'])
            remaining(ready_deadline)
            stop_deadline = time.monotonic() + stop_timeout
            record['stop_attempted'] = True
            pidfd_api.send_signal(state['pidfd'], signal.SIGTERM, flags=0)
            record['stop_successful'] = True
            write_json(label + '.STOP-RESULT.json', {'successful': True, 'signal': 15, 'at_monotonic': time.monotonic()})
            while True:
                remaining(stop_deadline)
                got, status = os.waitpid(state['daemon_pid'], os.WNOHANG)
                if got:
                    record['daemon_parent_joined'] = True
                    record['daemon_wait'] = {'pid': got, 'raw_status': status,
                                             'WIFEXITED': os.WIFEXITED(status),
                                             'exit': os.WEXITSTATUS(status) if os.WIFEXITED(status) else None,
                                             'WIFSIGNALED': os.WIFSIGNALED(status)}
                    require(got == state['daemon_pid'] and os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0,
                            'original daemon did not positively exit0')
                    break
                time.sleep(min(0.01, remaining(stop_deadline)))
            for stream in (p.stdin, p.stdout, p.stderr):
                if stream is not None and not stream.closed:
                    stream.close()
            record['launcher_streams_closed'] = all(s is None or s.closed for s in (p.stdin, p.stdout, p.stderr))
            fd = state['pidfd']
            os.close(fd)
            state['pidfd'] = None
            record['pidfd_closed'] = True
            record['children_after_waits'] = children()
            require(not record['children_after_waits'] and record['launcher_streams_closed'], 'child/stream retirement incomplete')
            record['owner_after_waits'] = snapshot_owner()
            require(stable_owner(record['owner_before_constructor'], record['owner_after_waits']), 'dedicated-owner fd/task/signal/identity baseline differs')
            require(record['owner_after_waits']['subreaper'] == 1, 'subreaper unexpectedly changed')
            record['subreaper_scope'] = 'Remains1 for this dedicated Owner; no prctl restoration is claimed.'
            record['daemon_kernel_fd_table_retired'] = True
            record['source_inferences_only'] = ['prior checked real udev calls succeeded to reach the observed state',
                                               'normal Rust RAII branch and saved child signal-mask restoration']
            record['status'] = 'PASS'
            write_json(label + '.RESULT.json', record)
            self.records.append(record)
            state['status'] = 'PASS'
            return record
        except BaseException as exc:
            retain_unknown(exc)


"""Finite F08 observation component, appended to a private qualified Owner copy.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No native/device/event command is implemented here. Root inputs remain unissued.
"""
import errno as _ak_errno
import hashlib as _ak_hashlib
import re as _ak_re
import stat as _ak_stat


class ActiveKmsgObserver:
    ROOT = '01a18bc3-e072-7810-9426-75101b0856c0'
    INVOCATION = '20261112T094452Z-12a4bea0'
    SOURCE = '519defcd6719e1e55e44fb0de4f607061c59dd2cdf6d45024e3ad470c414a4ea'
    KMSG_SIZE = (4 << 20) - 4096
    SLOT = 1 << 20

    @staticmethod
    def need(ok, message):
        if not ok:
            raise RuntimeError('F08 active-worker refusal: ' + message)

    @classmethod
    def closed(cls, value, keys, label):
        cls.need(type(value) is dict and set(value) == set(keys.split()), 'closed ' + label)
        return value

    @classmethod
    def reference(cls, value):
        cls.closed(value, 'path bytes sha256', 'Root reference')
        cls.need(type(value['path']) is str and value['path'].startswith('/') and
                 type(value['bytes']) is int and value['bytes'] > 0 and
                 type(value['sha256']) is str and _ak_re.fullmatch('[0-9a-f]{64}', value['sha256']),
                 'non-null actual Root reference')

    @staticmethod
    def canonical(value):
        return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()

    @staticmethod
    def physical(st):
        return {'device': st.st_dev, 'inode': st.st_ino, 'mode': st.st_mode,
                'uid': st.st_uid, 'gid': st.st_gid, 'nlink': st.st_nlink,
                'rdev': st.st_rdev, 'mtime_ns': str(st.st_mtime_ns), 'ctime_ns': str(st.st_ctime_ns)}

    def __init__(self, operation, source_pins):
        self.operation = operation
        self.nonce = operation['nonce']
        self.out = Path('/output')
        self.baseline = None
        self.previous_idle = None
        self.seen_receipts = {}
        self.native_owner_identity = None
        self.backend = self.closed(operation['backend_binding'],
            'schema Root_thread_id invocation operation_nonce issued_utc_ns issued_mono_ns expires_after_seconds '
            'profile_ref expected_context_ref source_contract_sha256 root_validation kernel controller '
            'os_index generation dynamic_device_visibility_ref native_phase_timeout_seconds '
            'expected_ordinary_kmsg_record native_receipt_paths', 'backend binding')
        b = self.backend
        self.need(b['schema'] == 'mckernel.m15.f08.Root-active-kmsg-backend-binding.v1' and
                  b['Root_thread_id'] == self.ROOT and b['invocation'] == self.INVOCATION and
                  b['operation_nonce'] == self.nonce and b['source_contract_sha256'] == self.SOURCE,
                  'same Root/invocation/nonce/source backend binding')
        self.need(b['expires_after_seconds'] == 300 and type(b['expires_after_seconds']) is int,
                  'fixed300s Root input lifetime')
        for clock, actual in (('utc', time.time_ns()), ('mono', time.monotonic_ns())):
            issued = b['issued_' + clock + '_ns']
            self.need(type(issued) is int and 0 <= actual - issued <= 300 * 10**9,
                      'fresh actual backend issuance clocks')
        for key in ('profile_ref', 'expected_context_ref', 'dynamic_device_visibility_ref'):
            self.reference(b[key])
        v = self.closed(b['root_validation'],
            'schema issuer_uid parent_source_ref operation_review_ref inside_source_review_ref '
            'host_admission_ref native_admission_ref source_permission_ref native_owner_lifetime_ref '
            'implementation_sha256 all_actual_files_pinned_by_normal_Root_parent '
            'current_HOST_and_native_admissions_verified native_source_exec_ACK_and_ownership_eligible '
            'same_running_kernel_and_processed_udev_route_verified sole_OS0_kmsg_reader_lifetime_owned',
            'actual normal Root parent validation')
        self.need(v['schema'] == 'mckernel.m15.f08.normal-Root-active-backend-validation.v1' and
                  type(v['issuer_uid']) is int and v['issuer_uid'] == 0,
                  'actual Root issuer')
        for key in ('parent_source_ref', 'operation_review_ref', 'inside_source_review_ref',
                    'host_admission_ref', 'native_admission_ref', 'source_permission_ref',
                    'native_owner_lifetime_ref'):
            self.reference(v[key])
        for key in ('all_actual_files_pinned_by_normal_Root_parent',
                    'current_HOST_and_native_admissions_verified',
                    'native_source_exec_ACK_and_ownership_eligible',
                    'same_running_kernel_and_processed_udev_route_verified',
                    'sole_OS0_kmsg_reader_lifetime_owned'):
            self.need(v[key] is True, 'genuine external Root validation missing: ' + key)
        self.need(v['implementation_sha256'] == source_pins, 'exact reviewed inside source/provider pins')
        self.closed(b['kernel'], 'boot_id release machine loaded_module_cohort_ref', 'actual running kernel')
        self.reference(b['kernel']['loaded_module_cohort_ref'])
        self.closed(b['controller'], 'index path physical', 'controller0 identity')
        self.need(type(b['controller']['index']) is int and b['controller']['index'] == 0 and
                  b['controller']['path'] == '/dev/mcd0' and type(b['os_index']) is int and b['os_index'] == 0,
                  'literal controller0/OS0 supported case')
        self.closed(b['controller']['physical'],
                    'device inode mode uid gid nlink rdev mtime_ns ctime_ns', 'actual controller physical identity')
        self.need(type(b['generation']) is str and _ak_re.fullmatch('[0-9a-f]{64}', b['generation']),
                  'fresh Root-owned OS0 generation')
        self.need(type(b['native_phase_timeout_seconds']) is int and
                  0 < b['native_phase_timeout_seconds'] <= 180, 'bounded actual native phase deadline')
        k = self.closed(b['expected_ordinary_kmsg_record'], 'source_ref literal_hex', 'genuine normal boot record')
        self.reference(k['source_ref'])
        self.need(type(k['literal_hex']) is str and len(k['literal_hex']) % 2 == 0 and
                  2 <= len(k['literal_hex']) <= 8192 and _ak_re.fullmatch('[0-9a-f]+', k['literal_hex']),
                  'nonempty source-derived ordinary boot literal; no invented message')
        paths = {'create': '/output/native-create.Root.json', 'boot': '/output/native-boot.Root.json',
                 'remove': '/output/native-remove.Root.json'}
        self.need(b['native_receipt_paths'] == paths, 'only three finite native receipt paths')
        for path in paths.values():
            self.need(not os.path.lexists(path), 'no prior native receipt/nonce reuse')
        self.need(not os.path.lexists('/tmp/ihkmond'), 'fresh daemon-owned ring path required')
        self.binding_sha256 = _ak_hashlib.sha256(self.canonical(b)).hexdigest()
        self.preflight()

    def fresh(self):
        for clock, actual in (('utc', time.time_ns()), ('mono', time.monotonic_ns())):
            self.need(0 <= actual - self.backend['issued_' + clock + '_ns'] <= 300 * 10**9,
                      'backend input expired; original custody retained')

    def controller(self):
        value = os.lstat('/dev/mcd0')
        self.need(_ak_stat.S_ISCHR(value.st_mode) and
                  self.physical(value) == self.backend['controller']['physical'] and
                  os.access('/dev/mcd0', os.R_OK), 'same genuine readable controller0 required')
        return self.physical(value)

    def preflight(self):
        self.fresh()
        k = self.backend['kernel']
        self.need(Path('/proc/sys/kernel/random/boot_id').read_text().strip() == k['boot_id'] and
                  os.uname().release == k['release'] and os.uname().machine == k['machine'] == 'x86_64',
                  'same running kernel as the actual admitted native backend')
        static = self.operation['provider_context']['static']
        self.need(static['source_contract_sha256'] == self.SOURCE and
                  static['observed_tuple']['boot_id'] == k['boot_id'] and
                  static['monitor'] == {'channel': 'udev', 'group_mask': 2, 'protocol': 15},
                  'same genuine processed publisher context')
        raw = self.canonical(static)
        self.need(len(raw) == self.backend['expected_context_ref']['bytes'] and
                  _ak_hashlib.sha256(raw).hexdigest() == self.backend['expected_context_ref']['sha256'],
                  'exact canonical reviewed context DATA')
        self.controller()
        self.need(not os.path.lexists('/dev/mcos0'),
                  'OS0 must be genuinely created only after observer readiness; no preexisting-node fixture')

    def write(self, name, value):
        data = self.canonical(value)
        with (self.out / name).open('xb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        directory = os.open(str(self.out), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)

    def marker(self, phase, sample):
        value = {'schema': 'mckernel.m15.f08.active-worker-observed-barrier.v1',
                 'phase': phase, 'Root_thread_id': self.ROOT, 'invocation': self.INVOCATION,
                 'operation_nonce': self.nonce, 'generation': self.backend['generation'],
                 'backend_binding_sha256': self.binding_sha256,
                 'observed_mono_ns': time.monotonic_ns(), 'observed_utc_ns': time.time_ns(),
                 'daemon_pid': sample['pid'], 'tasks': sample['tasks'], 'roles': sample['roles'],
                 'native_action_or_event_injected': False}
        self.write('ACTIVE-' + phase.upper() + '.json', value)
        return value

    @staticmethod
    def watches(raw):
        rows = []
        for line in raw.splitlines():
            if line.startswith('tfd:'):
                m = _ak_re.match(r'^tfd:\s*(\d+)\s+events:\s*([0-9a-fA-F]+)\s+data:\s*([0-9a-fA-F]+)\b', line)
                ActiveKmsgObserver.need(m is not None, 'recognized actual epoll watch record')
                fd, events, data = int(m[1]), int(m[2], 16), int(m[3], 16)
                ActiveKmsgObserver.need(events & 1 and data == fd, 'EPOLLIN interest and actual fd userdata')
                rows.append({'fd': fd, 'events': events, 'data': data, 'raw': line})
        ActiveKmsgObserver.need(len({r['fd'] for r in rows}) == len(rows), 'unique actual epoll watches')
        return rows

    def sample(self, pid, record, phase):
        proc = Path('/proc') / str(pid)
        raw = {'pid': pid, 'observed_mono_ns': time.monotonic_ns(), 'phase': phase,
               'tasks': {}, 'fds': {}, 'roles': {}}
        try:
            tasks = sorted(os.listdir(str(proc / 'task')), key=int)
            names = sorted(os.listdir(str(proc / 'fd')), key=int)
            for tid in tasks:
                p = proc / 'task' / tid
                st = (p / 'stat').read_text()
                raw['tasks'][tid] = {'birth': st.rsplit(') ', 1)[1].split()[19],
                                     'comm': (p / 'comm').read_text().strip(),
                                     'syscall': (p / 'syscall').read_text(),
                                     'status': (p / 'status').read_text(), 'raw_stat': st}
            for fd in names:
                raw['fds'][fd] = {'target': os.readlink(str(proc / 'fd' / fd)),
                                  'fdinfo': (proc / 'fdinfo' / fd).read_text()}
            raw['raw_netlink'] = (proc / 'net/netlink').read_text()
            if names != sorted(os.listdir(str(proc / 'fd')), key=int) or tasks != sorted(os.listdir(str(proc / 'task')), key=int):
                return raw, False
        except FileNotFoundError:
            raw['incomplete'] = 'owned task/FD table changed while sampling'
            return raw, False
        workers = [t for t in tasks if t != str(pid)]
        if len(tasks) != 2 or len(workers) != 1 or raw['tasks'][workers[0]]['comm'] != 'ihkmond-kmsg':
            return raw, False
        expected_mask = int(record['owner_after_constructor']['signals']['SigBlk'], 16) | 0x4002
        for task in raw['tasks'].values():
            fields = dict(line.split(':', 1) for line in task['status'].splitlines() if ':' in line)
            if int(fields['SigBlk'].strip(), 16) != expected_mask:
                return raw, False
        target = lambda name: [int(n) for n, row in raw['fds'].items() if row['target'] == name]
        eps, sigs, events = target('anon_inode:[eventpoll]'), target('anon_inode:[signalfd]'), target('anon_inode:[eventfd]')
        if len(eps) != 2 or len(sigs) != 1 or len(events) != (4 if phase == 'active' else 2):
            return raw, False
        sig = sigs[0]
        mask = _ak_re.search(r'^sigmask:\s*([0-9a-fA-F]+)\s*$', raw['fds'][str(sig)]['fdinfo'], _ak_re.M)
        if mask is None or int(mask[1], 16) != 0x4002:
            return raw, False
        ids = {}
        for fd in events:
            text = raw['fds'][str(fd)]['fdinfo']
            event_id = _ak_re.search(r'^eventfd-id:\s*(\d+)\s*$', text, _ak_re.M)
            count = _ak_re.search(r'^eventfd-count:\s*([0-9a-fA-F]+)\s*$', text, _ak_re.M)
            if event_id is None or count is None or int(count[1], 16) != 0:
                return raw, False
            ids[fd] = int(event_id[1])
        if len(set(ids.values())) != len(ids):
            return raw, False
        watch = {ep: self.watches(raw['fds'][str(ep)]['fdinfo']) for ep in eps}
        main = [ep for ep in eps if sig in {r['fd'] for r in watch[ep]}]
        if len(main) != 1 or len(watch[main[0]]) != 3:
            return raw, False
        ep = main[0]; wep = next(e for e in eps if e != ep)
        main_events = {r['fd'] for r in watch[ep]} & set(events)
        if len(main_events) != 1:
            return raw, False
        done = next(iter(main_events))
        mon = {r['fd'] for r in watch[ep]} - {sig, done}
        if len(mon) != 1:
            return raw, False
        mon = next(iter(mon))
        sock = _ak_re.fullmatch(r'socket:\[(\d+)\]', raw['fds'].get(str(mon), {}).get('target', ''))
        if sock is None:
            return raw, False
        netlink = []
        for line in raw['raw_netlink'].splitlines()[1:]:
            fields = line.split()
            if len(fields) == 10 and int(fields[-1]) == int(sock[1]):
                netlink.append({'protocol': int(fields[1]), 'port_id': int(fields[2]),
                                'groups': int(fields[3], 16), 'inode': int(sock[1]), 'raw': line})
        if len(netlink) != 1 or netlink[0]['protocol'] != 15 or netlink[0]['groups'] != 2:
            return raw, False
        worker_fds = {r['fd'] for r in watch[wep]}
        if len(worker_fds) != (3 if phase == 'active' else 1) or not worker_fds <= set(events) - {done}:
            return raw, False
        call = raw['tasks'][str(pid)]['syscall'].split()
        if len(call) < 5 or call[0] != '232' or int(call[1], 0) != ep or int(call[3], 0) != 3 or int(call[4], 0) != 250:
            return raw, False
        call = raw['tasks'][workers[0]]['syscall'].split()
        if phase == 'active':
            if len(call) < 5 or call[0] != '232' or int(call[1], 0) != wep or int(call[3], 0) != 2 or int(call[4], 0) != 250:
                return raw, False
        elif not call or call[0] != '202':
            return raw, False
        raw['monitor_netlink'] = netlink
        raw['bound_fds'] = {'epoll': ep, 'signalfd': sig, 'doneeventfd': done, 'monitor': mon}
        raw['epoll_watches'] = watch[ep]
        raw['roles'] = {'main_epoll': ep, 'worker_epoll': wep, 'signal': sig, 'done': done,
                        'monitor': mon, 'eventfd_ids': {str(k): v for k, v in ids.items()},
                        'worker_watches': sorted(worker_fds), 'worker_tid': workers[0]}
        if self.baseline is not None:
            for tid in self.baseline['tasks']:
                if tid not in raw['tasks'] or raw['tasks'][tid]['birth'] != self.baseline['tasks'][tid]['birth']:
                    return raw, False
            base = self.baseline['roles']
            for key in ('main_epoll', 'worker_epoll', 'signal', 'done', 'monitor', 'worker_tid'):
                if raw['roles'][key] != base[key]:
                    return raw, False
            original = base['eventfd_ids']
            if any(raw['roles']['eventfd_ids'].get(k) != v for k, v in original.items()):
                return raw, False
            if not set(base['worker_watches']) <= worker_fds:
                return raw, False
        return raw, True

    def initial_readiness(self, pid, record):
        self.fresh()
        sample, ready = self.sample(pid, record, 'idle')
        if not ready:
            self.previous_idle = None
            return sample, False
        key = (sample['roles'], {k: v['birth'] for k, v in sample['tasks'].items()})
        if self.previous_idle != key:
            self.previous_idle = key
            return sample, False
        self.baseline = sample
        return sample, True

    def receipt(self, phase, after_mono_ns):
        path = Path(self.backend['native_receipt_paths'][phase])
        try:
            fd = os.open(str(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        except FileNotFoundError:
            return None
        try:
            before = os.fstat(fd)
            self.need(_ak_stat.S_ISREG(before.st_mode) and before.st_uid == 0 and before.st_gid == 0 and
                      _ak_stat.S_IMODE(before.st_mode) == 0o444 and before.st_nlink == 1 and
                      0 < before.st_size <= 65536, 'immutable Root-owned bounded phase receipt')
            with os.fdopen(fd, 'rb', closefd=False) as stream:
                data = stream.read(65537)
            self.need(self.physical(before) == self.physical(os.fstat(fd)) == self.physical(os.lstat(str(path))) and
                      len(data) == before.st_size, 'same original Root receipt file')
        finally:
            os.close(fd)
        value = self.closed(json.loads(data),
            'schema Root_thread_id invocation operation_nonce phase generation backend_binding_sha256 '
            'native_admission_sha256 native_owner_lifetime_sha256 kernel_boot_id '
            'action_started_mono_ns action_finished_mono_ns published_mono_ns '
            'actual_command_result_ref original_native_owner phase_command device_result status consumer_event_claim',
            'Root native phase receipt')
        self.need(value['schema'] == 'mckernel.m15.f08.Root-native-phase-projection.v1' and
                  value['Root_thread_id'] == self.ROOT and value['invocation'] == self.INVOCATION and
                  value['operation_nonce'] == self.nonce and value['phase'] == phase and
                  value['generation'] == self.backend['generation'] and
                  value['backend_binding_sha256'] == self.binding_sha256 and
                  value['kernel_boot_id'] == self.backend['kernel']['boot_id'] and
                  value['status'] == 'PASS' and value['consumer_event_claim'] is False,
                  'same actual native phase; no producer receipt relabeled consumer event')
        validation = self.backend['root_validation']
        self.need(value['native_admission_sha256'] == validation['native_admission_ref']['sha256'] and
                  value['native_owner_lifetime_sha256'] == validation['native_owner_lifetime_ref']['sha256'],
                  'same actual native admission/lifetime')
        self.reference(value['actual_command_result_ref'])
        owner = self.closed(value['original_native_owner'],
            'pid birth lifetime_ref custody_retained whole_operation_wait', 'original native owner')
        self.reference(owner['lifetime_ref'])
        self.need(type(owner['pid']) is int and owner['pid'] > 0 and type(owner['birth']) is str and
                  owner['birth'].isdigit() and int(owner['birth']) > 0 and
                  owner['lifetime_ref'] == validation['native_owner_lifetime_ref'] and
                  owner['custody_retained'] is True and owner['whole_operation_wait'] == 'EXTERNAL_PENDING',
                  'same retained native owner; no fabricated early whole-owner wait')
        command = self.closed(value['phase_command'],
            'approved_normal_command_ref actual_result_ref exit phase_completion_observed', 'actual normal native step')
        self.reference(command['approved_normal_command_ref'])
        self.reference(command['actual_result_ref'])
        self.need(command['actual_result_ref'] == value['actual_command_result_ref'] and
                  type(command['exit']) is int and command['exit'] == 0 and
                  command['phase_completion_observed'] is True,
                  'Root projection of actual source-approved native step; full owner closure stays external')
        times = [value[k] for k in ('action_started_mono_ns', 'action_finished_mono_ns', 'published_mono_ns')]
        self.need(all(type(t) is int for t in times) and
                  after_mono_ns <= times[0] <= times[1] <= times[2] <= time.monotonic_ns(),
                  'actual native phase follows the observed barrier')
        self.closed(value['device_result'], 'controller os_path os_physical os_absent', 'phase device result')
        self.need(value['device_result']['controller'] == self.controller() and
                  value['device_result']['os_path'] == '/dev/mcos0', 'same controller and literal OS0')
        if phase == 'remove':
            self.need(value['device_result']['os_absent'] is True and
                      value['device_result']['os_physical'] is None and not os.path.lexists('/dev/mcos0'),
                      'genuine remove and current exact OS0 absence')
        else:
            st = os.lstat('/dev/mcos0')
            self.need(value['device_result']['os_absent'] is False and _ak_stat.S_ISCHR(st.st_mode) and
                      value['device_result']['os_physical'] == self.physical(st) and
                      os.access('/dev/mcos0', os.R_OK), 'actual dynamically visible readable OS0 character device')
        native_owner_identity = (owner['pid'], owner['birth'],
                                 tuple(owner['lifetime_ref'][key] for key in ('path', 'bytes', 'sha256')))
        if phase == 'create':
            if self.native_owner_identity is None:
                self.native_owner_identity = native_owner_identity
        else:
            self.need(self.native_owner_identity is not None,
                      'CREATE must bind the original native owner before BOOT or REMOVE')
        self.need(native_owner_identity == self.native_owner_identity,
                  'same original CREATE native owner pid/birth/lifetime across all phases')
        result = {'path': str(path), 'bytes': len(data), 'sha256': _ak_hashlib.sha256(data).hexdigest(),
                  'physical': self.physical(before), 'value': value}
        if phase in self.seen_receipts:
            self.need(result == self.seen_receipts[phase], 'one immutable actual publication per native phase')
        else:
            self.seen_receipts[phase] = result
        return result

    def ring(self, pid, record):
        sample, idle = self.sample(pid, record, 'idle')
        self.need(idle and all('/tmp/ihkmond/' not in f['target'] for f in sample['fds'].values()),
                  'rearmed worker and no open ring writer before capture')
        directory = Path('/tmp/ihkmond/mcos0')
        for p in (directory.parent, directory):
            st = os.lstat(str(p))
            self.need(_ak_stat.S_ISDIR(st.st_mode) and st.st_uid == st.st_gid == 1000 and
                      _ak_stat.S_IMODE(st.st_mode) == 0o700, 'fresh private daemon ring directory')
        names = sorted(p.name for p in directory.iterdir())
        self.need(0 < len(names) <= 64 and all(_ak_re.fullmatch(r'kmsg(?:0|[1-9][0-9]?)', n) for n in names),
                  'only bounded selected daemon slot names')
        names.sort(key=lambda n: int(n[4:]))
        self.need(names == ['kmsg' + str(n) for n in range(len(names))],
                  'first bounded ordinary-boot generation; no rotation coverage inferred')
        dest = self.out / 'retained-ring'
        dest.mkdir(mode=0o700)
        rows = []; contents = []
        for name in names:
            path = directory / name
            fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                before = os.fstat(fd)
                self.need(_ak_stat.S_ISREG(before.st_mode) and before.st_uid == before.st_gid == 1000 and
                          before.st_nlink == 1 and _ak_stat.S_IMODE(before.st_mode) == 0o600 and
                          0 < before.st_size <= self.SLOT, 'selected private bounded ring regular file')
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    data = stream.read(self.SLOT + 1)
                self.need(len(data) == before.st_size and self.physical(before) == self.physical(os.fstat(fd)) ==
                          self.physical(os.lstat(str(path))), 'same closed-writer ring file')
            finally:
                os.close(fd)
            self.need(sum(len(x) for x in contents) + len(data) <= self.KMSG_SIZE,
                      'first benign observation bounded to one selected buffer; no log flood')
            with (dest / name).open('xb') as stream:
                stream.write(data); stream.flush(); os.fsync(stream.fileno())
            contents.append(data)
            rows.append({'name': name, 'source': str(path), 'physical': self.physical(before),
                         'bytes': len(data), 'sha256': _ak_hashlib.sha256(data).hexdigest()})
        required = bytes.fromhex(self.backend['expected_ordinary_kmsg_record']['literal_hex'])
        self.need(required in b''.join(contents), 'actual source-derived ordinary native boot record missing')
        dfd = os.open(str(dest), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
        final, idle = self.sample(pid, record, 'idle')
        self.need(idle and final['roles'] == sample['roles'], 'same rearmed worker after own ring capture')
        result = {'schema': 'mckernel.m15.f08.retained-real-kmsg-ring-observation.v1',
                  'slots': rows, 'total_bytes': sum(len(x) for x in contents),
                  'ordinary_boot_source_ref': self.backend['expected_ordinary_kmsg_record']['source_ref'],
                  'source_literal_present': True, 'before_TERM': True,
                  'raw_kmsg_privacy': 'PRIVATE; publish only safe sizes/digests and outcome',
                  'notification101_delivery': 'UNPROVED', 'syslog_receiver_delivery': 'UNPROVED',
                  'hungup_or_status2_delivery': 'UNPROVED', 'full_F08_acceptance': False}
        self.write('RETAINED-RING.json', result)
        return result

    def observe(self, pid, record, live_guard, remaining):
        self.need(self.baseline is not None, 'actual enabled two-task initial readiness required')
        self.preflight()
        ready = self.marker('ready', self.baseline)
        deadline = time.monotonic() + self.backend['native_phase_timeout_seconds']
        active = None; created = None; booted = None; boot_barrier = None; removed = None; rearmed = None
        sequence = 0; captured_bytes = 0
        while True:
            remaining(deadline); self.fresh(); live_guard()
            phase = 'active' if active is None or booted is None else 'idle'
            sample, valid = self.sample(pid, record, phase)
            sequence += 1
            row = json.dumps({'sequence': sequence, 'valid': valid, 'raw': sample}, sort_keys=True).encode() + b'\n'
            captured_bytes += len(row)
            self.need(len(row) <= 65536 and captured_bytes <= 24 * 2**20,
                      'bounded private observation capture; no fsize/profile expansion')
            with (self.out / 'ACTIVE-OBSERVATIONS.jsonl').open('ab') as stream:
                stream.write(row)
                stream.flush(); os.fsync(stream.fileno())
            if active is None:
                created = self.receipt('create', ready['observed_mono_ns'])
                if created is not None and valid:
                    active = self.marker('registered', sample)
                    record['active_registered_raw'] = sample
            elif booted is None:
                candidate = self.receipt('boot', active['observed_mono_ns'])
                if candidate is not None and valid:
                    self.need(candidate['value']['device_result']['os_physical'] ==
                              created['value']['device_result']['os_physical'],
                              'same original dynamically created OS0 node across ordinary boot')
                    booted = candidate
                    boot_barrier = self.marker('boot-receipt', sample)
            else:
                removed = self.receipt('remove', boot_barrier['observed_mono_ns'])
                if removed is not None and valid:
                    self.need(set(sample['roles']['eventfd_ids'].values()) ==
                              set(self.baseline['roles']['eventfd_ids'].values()),
                              'original notification endpoint identities retired before TERM')
                    rearmed = sample
                    ring = self.ring(pid, record)
                    done = self.marker('removed-rearmed', sample)
                    break
            live_guard()
            time.sleep(min(0.2, remaining(deadline)))
        result = {'schema': 'mckernel.m15.f08.real-add-remove-kmsg-observation.v1',
                  'backend_binding_sha256': self.binding_sha256, 'ready': ready,
                  'active_registration': active, 'Root_create': created, 'Root_boot': booted,
                  'Root_remove': removed, 'rearmed_before_TERM': done, 'rearmed_raw': rearmed,
                  'ring': ring, 'observed_evidence': 'actual two-task/fd transitions and fresh retained ring bytes',
                  'source_inference': 'matching mcos0 ADD/REMOVE consumed by unchanged selected worker path; endpoint kinds101/2 derive from that source, not from fdinfo type labels',
                  'notification101_delivery': 'UNPROVED', 'syslog_receiver_delivery': 'UNPROVED',
                  'hungup_or_status2_delivery': 'UNPROVED', 'full_F08_acceptance': False}
        self.write('ACTIVE-OBSERVATION.json', result)
        record['active_kmsg_observation'] = result
        return deadline
