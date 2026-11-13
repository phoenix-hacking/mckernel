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
