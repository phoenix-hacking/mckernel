"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source delta only; actual e49 root operation is untouched.
"""
class DeadCallerIncompleteSnapshot(Exception):
    pass


def dead_caller_publisher(executable, argv):
    # Same executable/argv publisher predicate as frozen e49 PROC_CODE.
    heavy = {'qemu-system-x86_64', 'qemu-system-aarch64', 'qemu-kvm', 'mcexec', 'firecracker',
             'rustc', 'cargo', 'make', 'ninja', 'buildah', 'gcc', 'g++', 'cc', 'clang', 'clang++'}
    name = os.path.basename(executable[:-10] if executable.endswith(' (deleted)') else executable)
    if name in heavy or name.startswith('qemu-system-'):
        return True
    if name in ('docker', 'podman') and any(arg in ('build', 'run', 'start') for arg in argv[1:]):
        return True
    for arg in argv:
        base = os.path.basename(arg)
        if (base.startswith(('native_rust_exact_', 'native-exact-', 'native_exact_')) and
                base.endswith(('.py', '.sh')) and any(term in base for term in ('build', 'cleanup', 'recovery', 'prepare'))):
            return True
    return False


def dead_caller_forbidden_rows(rows, binding):
    groups = set(binding['group_ids'])
    roots = {binding['caller_pid'], binding['owner_pid'], *WAITER_PIDS,
             *(row['pid'] for row in binding['recorded_children'])}
    related = set(roots)
    while True:
        expanded = related | {row[0] for row in rows if row[1] in related}
        if expanded == related:
            break
        related = expanded
    if any(row[0] in related for row in rows):
        raise Refusal('dead-caller-owner-waiter-or-descendant-present')
    if any(row[3] in groups for row in rows):
        raise Refusal('dead-caller-or-owner-group-present')


def dead_caller_retained_births(raw_snapshots=()):
    """Carry positive retained facts and explicit pre-inventory history gaps."""
    births, seen_pids, exited_pids, compact_sequences = {}, set(), set(), set()
    def include(pid, birth):
        if type(pid) is not int or pid <= 0 or not isinstance(birth, str) or not birth.isdigit():
            raise Refusal('dead-caller-retained-birth-inventory')
        if pid in births and births[pid] != birth:
            raise Refusal('dead-caller-process-pid-reused')
        births[pid] = birth
    def seen(pid):
        if type(pid) is not int or pid <= 0:
            raise Refusal('dead-caller-retained-pid-inventory')
        seen_pids.add(pid)
    def raw_rows(snapshots, legacy):
        for rows in snapshots:
            for row in rows:
                seen(row['pid'])
                if row.get('validated_birth') is not None:
                    include(row['pid'], row['validated_birth'])
                elif legacy and row.get('stat_hex'):
                    fields = dead_caller_stat_fields(bytes.fromhex(row['stat_hex']), row['pid'])
                    include(row['pid'], fields[19].decode('ascii'))
                if row.get('current_absence', {}).get('confirmed_at_least_once') is True:
                    exited_pids.add(row['pid'])
    seed = _DEAD_CALLER_RETAINED_HISTORY_SEED
    for observation in [seed] + DEAD_CALLER_OBSERVATIONS:
        inventory = observation.get('observed_births')
        if inventory is not None:
            for pid, birth in inventory.items():
                if not isinstance(pid, str) or not pid.isdigit():
                    raise Refusal('dead-caller-retained-birth-inventory')
                include(int(pid), birth)
        elif 'raw_full_eof_snapshots' not in observation:
            compact_sequences.add(observation['sequence'])
        for pid in observation.get('observed_pids', []):
            seen(pid)
        for pid in observation.get('confirmed_exited_pids', []):
            seen(pid); exited_pids.add(pid)
        compact_sequences.update(observation.get('prior_compact_sequences', []))
        raw_rows(observation.get('raw_full_eof_snapshots', []), True)
    raw_rows(raw_snapshots, False)
    return births, sorted(compact_sequences), seen_pids, exited_pids


def record_dead_caller_observation(raw_snapshots, boot_id, error=None):
    """Retain each failed partial and the first COMPLETE successful pair.

    Every retry starts both snapshots afresh; all evidence keeps the original
    bounded canonical/full-EOF capture and aggregate byte accounting.
    """
    # Detach evidence before later confirmations mutate carried local records.
    raw_snapshots = json.loads(canonical(raw_snapshots))
    inventory, compact_sequences, seen_pids, exited_pids = dead_caller_retained_births(raw_snapshots)
    exited = [dict(pid=row['pid'], **row['current_absence']) for rows in raw_snapshots
              for row in rows if 'current_absence' in row]
    observation = dict(boot_id=boot_id, observed_epoch=time.time(), observer_pid=os.getpid(),
                       sequence=len(DEAD_CALLER_OBSERVATIONS), status=('REFUSED' if error else 'PASS_CURRENT_PAIR_WITH_CONFIRMED_EXITED_ROWS'
                               if exited else 'PASS_FULL_EOF_RECHECK'),
                       current_absence_rows=exited,
                       observed_births={str(pid): birth for pid, birth in sorted(inventory.items())},
                       observed_pids=sorted(seen_pids), confirmed_exited_pids=sorted(exited_pids),
                       prior_compact_sequences=compact_sequences,
                       prior_compact_pid_history='UNKNOWN' if compact_sequences else 'NO_RETAINED_COMPACT_GAP',
                       snapshots=[dict(process_count=len(rows), sha256=digest(canonical(rows)), bytes=len(canonical(rows)))
                                  for rows in raw_snapshots])
    if not any(row['status'] in ('PASS_FULL_EOF_RECHECK', 'PASS_CURRENT_PAIR_WITH_CONFIRMED_EXITED_ROWS')
               for row in DEAD_CALLER_OBSERVATIONS) or error:
        observation['raw_full_eof_snapshots'] = raw_snapshots
    if error:
        observation['error'] = error
    global DEAD_CALLER_CAPTURE_BYTES
    encoded = canonical(observation)
    if DEAD_CALLER_CAPTURE_BYTES + len(encoded) > 16 << 20:
        raise Refusal('dead-caller-capture-total-bound')
    DEAD_CALLER_CAPTURE_BYTES += len(encoded)
    DEAD_CALLER_OBSERVATIONS.append(observation)


def dead_caller_stat_fields(raw, pid):
    left, separator, right = raw.rpartition(b') ')
    fields = right.split()
    if (not separator or not left.startswith(str(pid).encode() + b' (') or len(fields) < 50 or
            fields[0] not in (b'R', b'S', b'D', b'Z', b'T', b't', b'X', b'x', b'K', b'W', b'P', b'I')):
        raise Refusal('dead-caller-process-stat')
    for field in fields[1:]:
        digits = field[1:] if field.startswith(b'-') else field
        if not digits or any(value < 48 or value > 57 for value in digits):
            raise Refusal('dead-caller-process-stat-number')
    if (pid <= 0 or int(fields[1]) < 0 or int(fields[2]) < 0 or int(fields[6]) < 0 or
            not fields[19].isdigit()):
        raise Refusal('dead-caller-process-stat-number')
    return fields


def dead_caller_confirm_exited(path, pid, protected, stage, observation):
    """Retain every confirmation fact, including bytes causing a refusal."""
    if pid in protected or pid <= 0:
        raise Refusal('dead-caller-protected-exit-cannot-be-inferred')
    for kind, read in (('stat', lambda: same_ofd_read(str(path / 'stat'), 65536)),
                       ('directory', lambda: os.stat(str(path), follow_symlinks=False))):
        expected = str(path / 'stat') if kind == 'stat' else str(path)
        try:
            value = read()
        except OSError as error:
            observation['confirmations'].append(dict(stage=stage, operation=kind,
                type=type(error).__name__, errno=error.errno, filename=error.filename))
            if type(error) is not FileNotFoundError or error.errno != 2 or error.filename != expected:
                observation['state'] = 'REFUSED_CONFIRMATION_UNOBSERVED_HISTORY'
                raise
        else:
            fact = dict(stage=stage, operation=kind, outcome='PRESENT')
            if kind == 'stat' and isinstance(value, bytes):
                fact['stat_hex'] = value.hex()
            observation['confirmations'].append(fact)
            observation['state'] = 'REFUSED_CONFIRMATION_UNOBSERVED_HISTORY'
            raise Refusal('dead-caller-exited-pid-reappeared')
    observation['state'] = 'CURRENT_ABSENT_UNOBSERVED_HISTORY'
    observation['confirmed_at_least_once'] = True



def dead_caller_absent():
    if DEAD_CALLER_BINDING is None:
        return
    if os.getuid() != 0 or os.geteuid() != 0:
        raise Refusal('dead-caller-root-observation-required')
    observer_pid = os.getpid()
    observer = same_ofd_process(observer_pid)
    if observer['uids'] != [0] * 4 or observer['gids'] != [0] * 4:
        raise Refusal('dead-caller-root-observer-credentials')
    boot_path = Path('/proc/sys/kernel/random/boot_id')
    before = boot_path.read_text().strip()
    forbidden = {DEAD_CALLER_BINDING['caller_pid'], DEAD_CALLER_BINDING['owner_pid'], *WAITER_PIDS,
                 *(row['pid'] for row in DEAD_CALLER_BINDING['recorded_children'])}
    protected = forbidden | {1, observer_pid}
    discovered = []
    births, compact_sequences, seen_pids, exited_pids = dead_caller_retained_births()
    exited_unobserved = {pid: (Path('/proc/' + str(pid)), dict(pid=pid, stat_hex=None,
        stat_after_hex=None, cmdline_hex=None, executable=None, current_absence=dict(
            state='RETAINED_EXIT_REQUIRES_CURRENT_RECONFIRMATION', confirmed_at_least_once=True,
            historical_birth='UNKNOWN', historical_argv='UNKNOWN', historical_executable='UNKNOWN',
            carried_from_pinned_history=True, confirmations=[]))) for pid in exited_pids}

    def observer_current():
        if (os.getuid() != 0 or os.geteuid() != 0 or os.getpid() != observer_pid or
                same_ofd_process(observer_pid) != observer):
            raise Refusal('dead-caller-root-observer-raced')
        if boot_path.read_text().strip() != before:
            raise Refusal('dead-caller-boot-raced')

    for attempt in range(1, 4):
        snapshots = []
        raw_snapshots = []
        try:
            observer_current()
            for snapshot_index in range(2):
                rows = []
                raw_rows = []
                if snapshot_index == 0:
                    raw_rows.extend(entry for path, entry in exited_unobserved.values())
                raw_snapshots.append(raw_rows)
                enumerated = set()
                entries = list(Path('/proc').iterdir())
                if len(entries) > 4096:
                    raise Refusal('dead-caller-process-count')
                for path in entries:
                    if not path.name.isdigit():
                        continue
                    pid = int(path.name)
                    if pid <= 0 or pid in enumerated:
                        raise Refusal('dead-caller-enumerated-pid-invalid-or-duplicate')
                    enumerated.add(pid)
                    if pid in exited_unobserved:
                        raise Refusal('dead-caller-exited-pid-reenumerated')
                    if pid in forbidden:
                        raise Refusal('dead-caller-owner-waiter-or-descendant-present')
                    previously_seen = pid in seen_pids
                    seen_pids.add(pid)
                    raw_entry = dict(pid=pid, stat_hex=None, stat_after_hex=None,
                                     cmdline_hex=None, executable=None)
                    raw_rows.append(raw_entry)

                    def process_read(kind, read, stage):
                        try:
                            return read()
                        except FileNotFoundError as error:
                            if (type(error) is not FileNotFoundError or error.errno != 2 or
                                    error.filename != str(path / kind) or pid in protected):
                                raise
                            raw_entry['incomplete_read'] = dict(type=type(error).__name__, errno=error.errno,
                                    filename=error.filename, attempt=attempt, stage=stage)
                            raise DeadCallerIncompleteSnapshot('attempt=' + str(attempt) + ':pid=' + str(pid) +
                                    ':stage=' + stage + ':' + str(error)) from error

                    try:
                        raw = process_read('stat', lambda: same_ofd_read(str(path / 'stat'), 65536), 'first-stat')
                    except DeadCallerIncompleteSnapshot:
                        # Only a never-observed numeric PID may use this path.
                        # Later-stage losses and previously read births retain
                        # the unchanged complete-pair restart/refusal behavior.
                        if pid in births or previously_seen:
                            raise
                        raw_entry['current_absence'] = dict(
                            state='UNCONFIRMED_FIRST_STAT_LOSS_UNOBSERVED_HISTORY',
                            historical_birth='UNKNOWN', historical_argv='UNKNOWN',
                            historical_executable='UNKNOWN',
                            eligibility='NO_PRIOR_RETAINED_OBSERVED_PID_OR_BIRTH',
                            prior_compact_pid_history='UNKNOWN' if compact_sequences else 'NO_RETAINED_COMPACT_GAP',
                            initial_failure=dict(raw_entry['incomplete_read']), confirmations=[])
                        dead_caller_confirm_exited(path, pid, protected, 'immediate-confirmation',
                                                   raw_entry['current_absence'])
                        exited_unobserved[pid] = (path, raw_entry)
                        continue
                    raw_entry['stat_hex'] = raw.hex()
                    fields = dead_caller_stat_fields(raw, pid)
                    row = [pid, int(fields[1]), fields[19].decode('ascii'), int(fields[2])]
                    if pid in births and births[pid] != row[2]:
                        raise Refusal('dead-caller-process-pid-reused')
                    births[pid] = row[2]
                    raw_entry['validated_birth'] = row[2]
                    discovered.append(row)
                    dead_caller_forbidden_rows(discovered, DEAD_CALLER_BINDING)
                    command = process_read('cmdline', lambda: same_ofd_read(str(path / 'cmdline'), 65536), 'cmdline')
                    raw_entry['cmdline_hex'] = command.hex()
                    if command and not command.endswith(b'\0'):
                        raise Refusal('dead-caller-cmdline-not-full-eof')
                    argv = [word.decode('utf-8', 'strict') for word in command[:-1].split(b'\0')] if command else []
                    if not argv and fields[0] not in (b'Z', b'X', b'x') and not (int(fields[6]) & 0x200000):
                        raise Refusal('dead-caller-live-command-unknown')
                    validate_dead_operation_argv(pid, argv, DEAD_CALLER_BINDING, observer_pid)
                    # Known command-name/script publishers are hard before exe read.
                    if pid != observer_pid and argv and dead_caller_publisher(argv[0], argv):
                        raise Refusal('dead-caller-known-publisher-present')
                    executable = process_read('exe', lambda: os.readlink(path / 'exe'), 'executable') if argv else ''
                    raw_entry['executable'] = executable
                    if pid != observer_pid and dead_caller_publisher(executable, argv):
                        raise Refusal('dead-caller-known-publisher-present')
                    check_raw = process_read('stat', lambda: same_ofd_read(str(path / 'stat'), 65536), 'second-stat')
                    raw_entry['stat_after_hex'] = check_raw.hex()
                    check = dead_caller_stat_fields(check_raw, pid)
                    if (check[1], check[2], check[19]) != (fields[1], fields[2], fields[19]):
                        raise Refusal('dead-caller-process-raced')
                    if pid == observer_pid and row[2] != observer['starttime']:
                        raise Refusal('dead-caller-root-observer-birth-raced')
                    rows.append(row)
                for exited_pid, (exited_path, entry) in exited_unobserved.items():
                    dead_caller_confirm_exited(exited_path, exited_pid, protected,
                        'snapshot-%d-complete' % snapshot_index, entry['current_absence'])
                snapshots.append(rows)
            for exited_pid, (exited_path, entry) in exited_unobserved.items():
                dead_caller_confirm_exited(exited_path, exited_pid, protected,
                    'pair-complete', entry['current_absence'])
            observer_current()
            validate_dead_caller_snapshots(snapshots, DEAD_CALLER_BINDING, before)
        except DeadCallerIncompleteSnapshot as error:
            try:
                observer_current()
            except Exception as observer_error:
                record_dead_caller_observation(raw_snapshots, before,
                        type(error).__name__ + ':' + str(error) + ':observer:' +
                        type(observer_error).__name__ + ':' + str(observer_error))
                raise
            record_dead_caller_observation(raw_snapshots, before, type(error).__name__ + ':' + str(error))
            if attempt == 3:
                raise Refusal('dead-caller-incomplete-pair-retry-exhausted') from error
            continue
        except Exception as error:
            record_dead_caller_observation(raw_snapshots, before, type(error).__name__ + ':' + str(error))
            raise
        record_dead_caller_observation(raw_snapshots, before)
        return
