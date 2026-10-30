"""Functional M14 install-only phase zero. Source for review; not a release.

The caller must load this exact source through a hash-pinned root bootstrap and
supply reviewed modules and a reviewed admission object; see CONTRACT.md.
"""
import fcntl
import hashlib
import json
import os
import signal
import stat
import struct
import sys
import time

MAX = 2 * 1024 * 1024
GETFLAGS = 0x80086601
SETFLAGS = 0x40086602
IMMUTABLE = 0x10
HELD = []
WRITERS = []
WRITER_JOURNAL = None
STOP_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP, signal.SIGQUIT, signal.SIGALRM)


def fail(message):
    raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')


def exact_keys(value, keys):
    if type(value) is not dict or set(value) != set(keys):
        fail('admission schema')


def ident(st):
    return {'device': st.st_dev, 'inode': st.st_ino}


def held_open(path, flags, mode=0o777, dir_fd=None):
    """Retain actual acquired FD before configured stops may be delivered."""
    old = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        HELD.append(None)
        slot = len(HELD) - 1
        try:
            fd = os.open(path, flags, mode, dir_fd=dir_fd)
        except BaseException:
            HELD.pop()
            raise
        HELD[slot] = fd
        return fd
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


def open_dir(path, root_controlled=False, traverse=False):
    if type(path) is not str or not path.startswith('/') or '//' in path:
        fail('directory path')
    parts = path.split('/')[1:]
    if not parts or any(x in ('', '.', '..') for x in parts):
        fail('directory components')
    fd = held_open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    identities = []
    for part in [''] + parts:
        if part:
            fd = held_open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=fd)
        st = os.fstat(fd)
        if root_controlled and (st.st_uid != 0 or stat.S_IMODE(st.st_mode) & 0o022):
            fail('directory ancestry is not root controlled')
        if traverse and not stat.S_IMODE(st.st_mode) & 0o001:
            fail('directory ancestry is not traversable')
        identities.append(ident(st))
    return fd, identities


def create_dir(parent_fd, name, mode):
    if type(name) is not str or not name or name in ('.', '..') or '/' in name:
        fail('directory name')
    os.mkdir(name, mode, dir_fd=parent_fd)  # exclusive; never reuse
    os.fsync(parent_fd)
    fd = held_open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
    st = os.fstat(fd)
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != mode:
        fail('new directory owner/mode')
    return fd


def file_flags(fd):
    data = bytearray(4)
    fcntl.ioctl(fd, GETFLAGS, data, True)
    return struct.unpack('I', data)[0]


def _tracked_open(root_fd, name, flags, mode):
    """Defer configured stops across open and registration of the actual FD."""
    record = {'name':name, 'fd':None, 'state':'ACQUIRING'}
    old = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
    try:
        WRITERS.append(record)
        HELD.append(None)
        slot = len(HELD) - 1
        try:
            fd = os.open(name, flags, mode, dir_fd=root_fd)
        except BaseException:
            record['state'] = 'OPEN_FAILED'
            HELD.pop()
            raise
        HELD[slot] = fd
        record['fd'] = fd
        record['state'] = 'OPEN'
        return record
    finally:
        signal.pthread_sigmask(signal.SIG_SETMASK, old)


def open_writer_journal(root_fd):
    """Hold one append-only journal writer for the life of the owner."""
    global WRITER_JOURNAL
    if WRITER_JOURNAL is not None:
        fail('writer journal already initialized')
    record = _tracked_open(root_fd, 'phase0-writers.jsonl',
                           os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    WRITER_JOURNAL = record
    os.fchmod(record['fd'], 0o600)
    os.fsync(record['fd'])
    os.fsync(root_fd)
    writer_event({'state':'JOURNAL_HELD', 'identity':ident(os.fstat(record['fd']))})


def writer_event(value):
    if WRITER_JOURNAL is None or WRITER_JOURNAL['state'] != 'OPEN':
        fail('writer journal unavailable')
    raw = canonical(value)
    offset = 0
    while offset < len(raw):
        n = os.write(WRITER_JOURNAL['fd'], raw[offset:])
        if n <= 0:
            raise OSError('writer journal short write')
        offset += n
    os.fsync(WRITER_JOURNAL['fd'])


def immutable_file(root_fd, name, raw, install):
    if type(raw) is not bytes or len(raw) > MAX:
        fail('receipt size')
    writer_event({'state':'BEFORE_RECEIPT_CREATE','name':name})
    record = _tracked_open(root_fd, name,
                           os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    writer = record['fd']
    writer_event({'state':'RECEIPT_WRITER_OPEN','name':name,'fd':writer,'identity':ident(os.fstat(writer))})
    os.fchmod(writer, 0o600)
    start = os.fstat(writer)
    offset = 0
    while offset < len(raw):
        n = os.write(writer, raw[offset:])
        if n <= 0:
            raise OSError('short receipt write')
        offset += n
    os.fsync(writer)
    writer_event({'state':'BEFORE_RECEIPT_WRITER_CLOSE','name':name,'fd':writer,'identity':ident(start)})
    try:
        old = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
        try:
            record['state'] = 'CLOSING'
            HELD.remove(writer)
            try:
                os.close(writer)  # exactly one attempt; never retry an uncertain FD
            except BaseException:
                record['state'] = 'CLOSE_UNKNOWN'
                raise
            record['state'] = 'CLOSED'
        finally:
            signal.pthread_sigmask(signal.SIG_SETMASK, old)
    except BaseException:
        try:
            writer_event({'state':'RECEIPT_WRITER_DISPOSITION_UNKNOWN','name':name,
                          'fd':writer,'identity':ident(start),'last_state':record['state']})
        except BaseException:
            pass
        raise
    writer_event({'state':'RECEIPT_WRITER_CLOSE_RETURNED','name':name,'identity':ident(start)})
    fd = held_open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=root_fd)
    st = os.fstat(fd)
    if ident(st) != ident(start) or st.st_uid != 0 or st.st_nlink != 1 or stat.S_IMODE(st.st_mode) != 0o600:
        fail('receipt identity after writer close')
    if install.read_stable(fd, MAX) != raw:
        fail('receipt readback')
    fcntl.ioctl(fd, SETFLAGS, struct.pack('I', file_flags(fd) | IMMUTABLE))
    os.fsync(fd)
    os.fsync(root_fd)
    named = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
    install.root_file(fd)
    if ident(named) != ident(os.fstat(fd)) or install.read_stable(fd, MAX) != raw:
        fail('immutable receipt final readback')
    writer_event({'state':'RECEIPT_IMMUTABLE_READBACK','name':name,'identity':ident(st),'sha256':digest(raw)})
    return fd, digest(raw)


def verify_source(install, source_fd, closure_raw):
    if digest(closure_raw) != install.CLOSURE_SHA256:
        fail('source closure digest')
    closure = json.loads(closure_raw, object_pairs_hook=install.unique)
    if set(closure) != {'version', 'source_directory', 'python_files', 'contract_files', 'files'} or closure['source_directory'] != install.SOURCE_DIR or closure['python_files'] != 20 or closure['contract_files'] != 3 or len(closure['files']) != 23:
        fail('source closure shape')
    parser = held_open('parser', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=source_fd)
    names = set()
    for row in closure['files']:
        exact_keys(row, ('name', 'size', 'sha256'))
        name = row['name']
        if type(name) is not str or name in names:
            fail('source name')
        parts = name.split('/')
        if len(parts) not in (1, 2) or any(p in ('', '.', '..') for p in parts) or (len(parts) == 2 and parts[0] != 'parser'):
            fail('source relative name')
        names.add(name)
        fd = held_open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parser if len(parts) == 2 else source_fd)
        raw = install.read_stable(fd, MAX)
        if type(row['size']) is not int or len(raw) != row['size'] or digest(raw) != row['sha256']:
            fail('source bytes differ')
    if sum(name.endswith('.py') for name in names) != 20 or not {'GRAPH-CONTRACT.json', 'parser/contract.json', 'parser/repaircontract.json', 'parser/candidate_data.py'} <= names:
        fail('source closure membership')


def run(request, install, issuer, prelim, completion, closure_raw, wait_raw, review_raw, verified_source_pins, channel, root_parent_pid, root_parent_birth):
    """Enter from reviewed, hash-pinned bootstrap in the admitted root owner.

    On successful construction, enter the selected keeper in the same process.
    Once mutation starts every failure retains known open FDs and stops in UNKNOWN;
    a failed close has unknown disposition and is never retried by number.
    """
    keys = ('nonce','outer_pid','outer_birth','one_shot_admission_id','operation_parent','code_parent_parent',
            'deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns',
            'weekly_used_percent','weekly_observed_utc_ns','service_status','host_floor_bytes','scratch_path',
            'scratch_floor_bytes','min_mem_available_bytes','join_capture_reserve_ns','term_grace_ns','kill_grace_ns',
            'join_grace_ns','retire_operation_only','owner_release','owner_release_sha256','profile_sha256',
            'native12','scratch21','mutex27_4','v2_birth','retained_2gib_bytes',
            'native_currentfree','no_unlisted_later_operation')
    exact_keys(request, keys)
    if os.getuid() != 0 or os.geteuid() != 0 or not install.hex64(request['nonce']) or not install.hex64(request['one_shot_admission_id']):
        fail('actual admitted root owner and nonce required')
    for key in ('native12', 'scratch21', 'mutex27_4'):
        if request[key] != 'HELD':
            fail('actual retained resource record required')
    if request['v2_birth'] is not None or request['native_currentfree'] is not None or request['no_unlisted_later_operation'] != 'UNKNOWN' or type(request['retained_2gib_bytes']) is not int or request['retained_2gib_bytes'] != 2147483648:
        fail('unknown historical ownership must remain unknown')
    if type(request['retire_operation_only']) is not bool:
        fail('retirement authority type')
    issuer._parent_alive(prelim,root_parent_pid,root_parent_birth,channel)
    issuer.require_outer_ancestor(prelim, request['outer_pid'], request['outer_birth'])
    if type(request['weekly_used_percent']) not in (int, float) or not 0 <= request['weekly_used_percent'] < 100 or type(request['weekly_observed_utc_ns']) is not int or not 0 <= time.time_ns() - request['weekly_observed_utc_ns'] <= 30000000000 or request['service_status'] != 'NO_NEW_REJECTION':
        fail('fresh actual included status required')
    for key in ('deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns','host_floor_bytes','scratch_floor_bytes','min_mem_available_bytes','join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(request[key]) is not int or request[key] <= 0:
            fail('positive admitted bound required: ' + key)
    if request['host_floor_bytes'] < 16 * 1024**3 or request['scratch_floor_bytes'] < 12 * 1024**3 or request['min_mem_available_bytes'] < 24 * 1024**3:
        fail('capacity floor')
    if not 1000000000 <= request['join_capture_reserve_ns'] <= 30000000000:
        fail('join reserve')
    operation_parent, operation_ancestors = open_dir(request['operation_parent'], True)
    code_parent_parent, code_parent_ancestors = open_dir(request['code_parent_parent'], True, True)
    source_fd, source_ancestors = open_dir(install.SOURCE_DIR)
    verify_source(install, source_fd, closure_raw)
    owner = request['owner_release']
    exact_keys(owner, ('version','record_type','scope','nonce','native_release','status','review_sha256',
                       'creation_model_approval','manual_invocation','one_shot_admission_id','profile_sha256',
                       'controls_sha256','capacity_sha256','outer_pid','outer_birth','retire_operation_only'))
    owner_raw = canonical(owner)
    if (type(owner['version']) is not int or owner['version'] != 1 or
        owner['record_type'] != 'ROOT_INSTALL_OPERATION_RETIREMENT_V1' or owner['scope'] != 'ROOT_CODE_INSTALL_ONLY' or
        owner['nonce'] != request['nonce'] or owner['native_release'] is not False or
        owner['status'] != 'APPROVED_IF_VERIFIED' or not install.hex64(owner['review_sha256']) or
        type(review_raw) is not bytes or len(review_raw) > MAX or digest(review_raw) != owner['review_sha256'] or
        owner['manual_invocation'] != '20261030T175456Z-0e492844' or
        owner['one_shot_admission_id'] != request['one_shot_admission_id'] or
        not install.hex64(request['profile_sha256']) or owner['profile_sha256'] != request['profile_sha256'] or
        owner['outer_pid'] != request['outer_pid'] or owner['outer_birth'] != request['outer_birth'] or
        owner['retire_operation_only'] is not request['retire_operation_only'] or
        not install.hex64(request['owner_release_sha256']) or digest(owner_raw) != request['owner_release_sha256']):
        fail('actual Root-reviewed owner intent binding required')
    controls_raw, _ = prelim.read_bound(prelim.CONTROLS, 1 << 20)
    capacity_raw, _ = prelim.read_bound(prelim.CAPACITY, 1 << 20)
    caps = prelim.controller_checks(prelim.strict_json(controls_raw), prelim.strict_json(capacity_raw), time.time())
    if owner['controls_sha256'] != digest(controls_raw) or owner['capacity_sha256'] != digest(capacity_raw):
        fail('owner intent current controls differ')
    from decimal import Decimal
    ns = lambda value: int(Decimal(str(value)) * Decimal(1000000000))
    if request['deadline_boot_ns'] > ns(caps['boot_deadline']) or request['deadline_mono_ns'] > ns(caps['monotonic_deadline']) or request['utc_cap_ns'] > ns(caps['deadline']):
        fail('inherited tighter caps')
    boot_id = open('/proc/sys/kernel/random/boot_id', 'r').read(128).strip()
    if caps['boot_id'] != boot_id:
        fail('boot identity')
    host = os.statvfs(request['operation_parent'])
    host_available = host.f_bavail * host.f_frsize
    scratch = os.statvfs(request['scratch_path'])
    if host_available < request['host_floor_bytes'] or scratch.f_bavail * scratch.f_frsize < request['scratch_floor_bytes']:
        fail('actual storage floor')
    with open('/proc/meminfo', 'r') as stream:
        mem_rows = [line for line in stream if line.startswith('MemAvailable:')]
    if len(mem_rows) != 1 or int(mem_rows[0].split()[1]) * 1024 < request['min_mem_available_bytes']:
        fail('actual memory floor')
    proc_fd = held_open('/proc', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    proc = os.fstat(proc_fd)
    pidns = os.stat('/proc/self/ns/pid')
    proc_scope = {'proc_device': proc.st_dev, 'proc_inode': proc.st_ino, 'pidns_device': pidns.st_dev, 'pidns_inode': pidns.st_ino}
    completion.verify_proc_scope(proc_fd, proc_scope)
    executable = os.readlink('/proc/self/exe')
    interpreter_parent, interpreter_ancestors = open_dir(os.path.dirname(executable), True)
    interpreter_fd = held_open(os.path.basename(executable), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=interpreter_parent)
    executable_stat = os.fstat(interpreter_fd)
    interp = {'path': executable, 'ancestors': interpreter_ancestors, 'device': executable_stat.st_dev, 'inode': executable_stat.st_ino, 'sha256': digest(install.read_stable(interpreter_fd, 128 * 1024 * 1024))}
    install.verify_base_runtime(interp)
    tools = {}
    for name in ('sudo', 'taskset', 'prlimit'):
        fd = held_open('/usr/bin/' + name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
        tools[name] = digest(install.read_stable(fd, 128 * 1024 * 1024))
    # Check the independently reviewed Root intent and exact known-role
    # model before creating paths; this validates data and does not grant authority.
    # The selected verified-byte loader supplies actual source/toolproof pins.
    owner_template = {'nonce':request['nonce'], 'owner_release_sha256':request['owner_release_sha256'],
                      'installer_sha256':install._BOOTSTRAP_INSTALLER_HASH,
                      'interpreter':interp, 'deadline_boot_ns':request['deadline_boot_ns']}
    owner_intent = {'wait_literal_sha256':digest(wait_raw)}
    # Exact independent review bytes have been selected by Root and hashed.
    # They gain root-owned immutable custody only after the exclusive root exists.
    # All effects below are exclusive and never rolled back. Catch every
    # post-mutation error in the retained owner; the supervisor sees UNKNOWN.
    operation_name = 'mckernel-install-' + request['nonce']
    code_name = 'mckernel-code-' + request['nonce']
    mutated = False
    root_fd = None
    try:
        mutated = True
        root_fd = create_dir(operation_parent, operation_name, 0o700)
        open_writer_journal(root_fd)
        review_fd, review_sha = immutable_file(root_fd, 'expert-review', review_raw, install)
        install.root_file(review_fd)
        if digest(install.read_stable(review_fd, MAX)) != owner['review_sha256'] or review_sha != owner['review_sha256']:
            fail('sealed expert review differs from Root-selected bytes')
        exact_keys(verified_source_pins, ('issuer_sha256','completion_sha256','ipc_sha256'))
        if any(not install.hex64(value) for value in verified_source_pins.values()):
            fail('actual held-verified source pins required')
        completion.SOURCE_PINS = dict(verified_source_pins, review_sha256=review_sha)
        completion.verify_creation_model_value(install, owner, owner_template, owner_intent)
        copied_owner_fd, owner_sha = immutable_file(root_fd, 'owner-release.json', owner_raw, install)
        completion.verify_creation_model(install, copied_owner_fd, owner_template, owner_intent)
        code_fd = create_dir(code_parent_parent, code_name, 0o755)
        root_path = request['operation_parent'] + '/' + operation_name
        code_path = request['code_parent_parent'] + '/' + code_name
        writer_event({'state':'BEFORE_LEASE_CREATE','name':'lease'})
        lease_record = _tracked_open(root_fd, 'lease', os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
        lease_fd = lease_record['fd']
        writer_event({'state':'LEASE_OPEN','identity':ident(os.fstat(lease_fd)),'fd':lease_fd})
        os.fchmod(lease_fd, 0o600)
        os.fsync(lease_fd)
        os.fsync(root_fd)
        controls_fd, controls_sha = immutable_file(root_fd, 'controls.json', controls_raw, install)
        capacity_fd, capacity_sha = immutable_file(root_fd, 'capacity.json', capacity_raw, install)
        closure_fd, closure_sha = immutable_file(root_fd, 'source-closure.json', closure_raw, install)
        issued = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        host_record = {'version':1,'record_type':'HOST_INSTALL_RESOURCE_CUSTODY_V1','scope':'ROOT_CODE_INSTALL_ONLY','native_release':False,'native_currentfree':None,'no_unlisted_later_operation':'UNKNOWN','v2_birth':None,'retained_2gib_bytes':2147483648,'native12':request['native12'],'scratch21':request['scratch21'],'mutex27_4':request['mutex27_4'],'boot_id':boot_id,'nonce':request['nonce'],'issued_boot_ns':issued,'expires_boot_ns':request['receipt_expires_boot_ns'],'host_available_bytes':host_available,'host_floor_bytes':request['host_floor_bytes'],'owner_release_sha256':owner_sha}
        host_fd, host_sha = immutable_file(root_fd, 'host-custody.json', canonical(host_record), install)
        template = {'version':1,'purpose':'root-install-source-closure-v1','nonce':request['nonce'],'boot_id':boot_id,'controller_pid':None,'controller_birth':None,'operation_root':ident(os.fstat(root_fd)),'operation_path':root_path,'operation_ancestors':operation_ancestors+[ident(os.fstat(root_fd))],'code_path':code_path,'code_ancestors':code_parent_ancestors+[ident(os.fstat(code_fd))],'code_parent':ident(os.fstat(code_fd)),'source_dir':ident(os.fstat(source_fd)),'source_ancestors':source_ancestors,'lease':ident(os.fstat(lease_fd)),'installer_sha256':install._BOOTSTRAP_INSTALLER_HASH,'interpreter':interp,'closure_sha256':closure_sha,'issued_boot_ns':issued,'deadline_boot_ns':request['deadline_boot_ns'],'deadline_mono_ns':request['deadline_mono_ns'],'utc_cap_ns':request['utc_cap_ns'],'one_shot_admission_id':request['one_shot_admission_id'],'controls_sha256':controls_sha,'capacity_sha256':capacity_sha,'host_install_custody_sha256':host_sha,'owner_release_sha256':owner_sha,'term_grace_ns':request['term_grace_ns'],'kill_grace_ns':request['kill_grace_ns'],'join_grace_ns':request['join_grace_ns'],'retire_operation_only':request['retire_operation_only'],'root_parent_pid':root_parent_pid,'root_parent_birth':root_parent_birth,'installer_pid':None,'installer_birth':None,'keeper_pid':None,'keeper_birth':None}
        intent = {'version':1,'purpose':'source-install-start-intent-v1','nonce':request['nonce'],'outer_pid':request['outer_pid'],'outer_birth':request['outer_birth'],'boot_id':boot_id,'phase1_deadline_boot_ns':request['phase1_deadline_boot_ns'],'receipt_expires_boot_ns':request['receipt_expires_boot_ns'],'weekly_used_percent':request['weekly_used_percent'],'weekly_observed_utc_ns':request['weekly_observed_utc_ns'],'service_status':request['service_status'],'sudo_sha256':tools['sudo'],'taskset_sha256':tools['taskset'],'prlimit_sha256':tools['prlimit'],'wait_literal_sha256':digest(wait_raw),'join_capture_reserve_ns':request['join_capture_reserve_ns'],'proc_scope':proc_scope,'release_template':template}
        intent_fd, intent_sha = immutable_file(root_fd, 'start-intent.json', canonical(intent), install)
        issuer.bounds(install, template, request['phase1_deadline_boot_ns'])
        issuer.verify_direct_tools(install, intent, template)
        issuer.fresh_controls(prelim, install, template, request['phase1_deadline_boot_ns'])
        install.verify_host_receipt(host_fd, template)
        if digest(wait_raw) != intent['wait_literal_sha256']:
            fail('waiting literal binding')
        # Phase zero created but never locked this original open-file
        # description. Retire that descriptor exactly once before the keeper
        # opens the same identity-bound name and establishes its own
        # reviewed OFD custody. An uncertain close is never retried by number.
        lease_identity = ident(os.fstat(lease_fd))
        if lease_identity != template['lease']:
            fail('phase-zero lease identity changed')
        immutable_file(root_fd, 'phase0-before-lease-close.json', canonical({
            'state':'BEFORE_UNOWNED_LEASE_FD_CLOSE', 'nonce':request['nonce'],
            'lease':lease_identity}), install)
        try:
            old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, STOP_SIGNALS)
            try:
                lease_record['state'] = 'CLOSING'
                HELD.remove(lease_fd)
                try:
                    os.close(lease_fd)  # exactly one attempt; never retry uncertain FD
                except BaseException:
                    lease_record['state'] = 'CLOSE_UNKNOWN'
                    raise
                lease_record['state'] = 'CLOSED'
                lease_fd = None
            finally:
                signal.pthread_sigmask(signal.SIG_SETMASK,old_mask)
        except BaseException:
            try:
                writer_event({'state':'LEASE_DISPOSITION_UNKNOWN','identity':lease_identity,
                              'fd':lease_record['fd'],'last_state':lease_record['state']})
            except BaseException:
                pass
            raise
        immutable_file(root_fd, 'phase0-lease-close.json', canonical({
            'state':'UNOWNED_LEASE_FD_CLOSE_RETURNED', 'nonce':request['nonce'],
            'lease':lease_identity}), install)
        result, latch = issuer.run(install, prelim, intent_fd, intent_sha, source_fd, root_fd,
                                   code_fd, root_path+'/lease', closure_fd, controls_fd,
                                   capacity_fd, host_fd, copied_owner_fd, wait_raw.decode('utf-8'),
                                   channel, root_parent_pid, root_parent_birth)
        # Parent has acknowledged verified proof and holds the actual lease OFD.
        # Parent alone owns conditional disposition after positive keeper wait.
        return result
    except BaseException as error:
        if not mutated:
            raise
        try:
            if root_fd is not None:
                try:
                    immutable_file(root_fd, 'phase0-unknown.json', canonical({'state':'UNKNOWN_RETAINED','nonce':request['nonce'],'error_type':type(error).__name__}), install)
                except BaseException:
                    os.write(2, b'PHASE0_UNKNOWN_PUBLICATION_FAILED\n')
            os.write(2, ('PHASE0_UNKNOWN_RETAINED: ' + type(error).__name__ + ': ' + str(error) + '\n').encode())
        finally:
            while True:
                signal.pause()
