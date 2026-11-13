# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# CURRENT64017 metadata only. Failure-instant mount row remains UNAVAILABLE.
# Excluded worker01a1c48d/turn01a1ce01 signal/frame/xstate task is never replayed.
import base64,datetime,errno,fcntl,hashlib,json,os,pathlib,signal,stat,struct,sys,time,traceback
ROOT_ID='01a18bc3-e072-7810-9426-75101b0856c0'
INVOCATION='20261112T094452Z-12a4bea0'
CREDIT_RUN='7c6ef3604bfb4008a917bba8cfb6cfaa'
HERE=pathlib.Path(__file__).resolve().parent
GIB=1024**3
GETFLAGS=0x80086601
q=None;reader=None;REQUEST_SHA256=None
ROLE_HANDLES={};ROLE_SKIPS={};OBSERVATION_ERRORS=[];RETAINED_ERRORS=[]
ACTOR_PRIMARY_RAW=None;ACTOR_PRIMARY_TB=None

def sha(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def read_ref(ref):
    path=pathlib.Path(ref['path']);st=path.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size<=2**20
    with path.open('rb') as stream:raw=stream.read(2**20+1)
    assert len(raw)<=2**20 and len(raw)==ref['bytes'] and hashlib.sha256(raw).hexdigest()==ref['sha256']
    assert identity(st)==identity(path.lstat()),'reference changed during read'
    return json.loads(raw)

def stable(st): return st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns

def check(ok,message):
    if not ok:raise ValueError(message)

def flags(fd):
    value=bytearray(4);fcntl.ioctl(fd,GETFLAGS,value,True)
    return struct.unpack('I',value)[0]

def unique(pairs):
    result={}
    for key,value in pairs:
        check(key not in result,'duplicate manifest key');result[key]=value
    return result

def write_all(fd,raw):
    position=0
    while position<len(raw):
        n=os.write(fd,raw[position:]);check(n>0,'short durable write');position+=n

def root_private(fd):
    st=os.fstat(fd)
    check(stat.S_ISDIR(st.st_mode) and st.st_uid==0 and stat.S_IMODE(st.st_mode)==0o700,'root-private operation directory')
    try:os.getxattr(fd,'system.posix_acl_access')
    except OSError as e:
        if e.errno==errno.ENODATA:return
        raise
    raise ValueError('extended ACL on private operation root')

def identity(st):
    return {'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'nlink':st.st_nlink,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}

class Bound(Exception): pass

class Reader:
    def __init__(self, bounds):
        self.bounds = bounds; self.total = 0; self.opened = {}; self.events = []
        self.close_uncertainties = []; self.next_generation = 0
        self.errors = []; self.max_total = bounds['aggregate_raw_metadata_bytes_max']

    def note_error(self, label, error):
        row = dict(label=label, error_type=type(error).__name__, errno=getattr(error, 'errno', None))
        self.errors.append(row); return row

    def open(self, path, directory=False, dir_fd=None):
        flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
        if directory: flags |= os.O_DIRECTORY
        if dir_fd is not None: dir_fd = dir_fd['fd']
        fd = os.open(str(path), flags, dir_fd=dir_fd)
        return self.adopt(fd, str(path))

    def adopt(self, fd, label):
        handle = dict(fd=fd,label=label,generation=self.next_generation,
            consumed=False,status='OPEN_OWNED')
        self.next_generation += 1
        self.opened[handle['generation']] = handle
        return handle

    def close(self, handle):
        generation = handle['generation']; fd = handle['fd']; label = handle['label']
        assert self.opened.get(generation) is handle
        if handle['consumed']:
            raise RuntimeError('same owned handle close already attempted; no retry')
        # Consume this unique open generation BEFORE the one actual close.
        # Any later numeric-FD reuse is a different handle and cannot erase it.
        handle['consumed'] = True; handle['status'] = 'CLOSE_ATTEMPTED_UNKNOWN'
        try:
            os.close(fd)
            try: os.fstat(fd)
            except OSError as error:
                if error.errno != errno.EBADF: raise
            else: raise RuntimeError('own reader FD close not proven')
        except BaseException as error:
            # Never erase an uncertain close or retry that descriptor. Even
            # later FD-number reuse cannot remove this permanent failure.
            self.close_uncertainties.append(dict(label=label, own_fd=fd, generation=generation, consumed=True,
                error_type=type(error).__name__, errno=getattr(error,'errno',None)))
            raise
        handle['status'] = 'CLOSED_CONFIRMED'
        self.opened.pop(generation)
        self.events.append(dict(label=label, own_fd=fd, generation=generation, consumed=True, close_returned=True, EBADF_after_close=True))

    def read(self, path, limit, dir_fd=None, regular=False):
        handle = self.open(path, dir_fd=dir_fd); fd = handle['fd']
        try:
            before = os.fstat(fd)
            if regular and not stat.S_ISREG(before.st_mode): raise Bound('nonregular public record')
            remaining = min(limit, self.max_total - self.total)
            if remaining < 0: raise Bound('aggregate metadata limit')
            pieces, count = [], 0
            while True:
                ask = min(65536, remaining + 1 - count, self.max_total - self.total)
                if ask <= 0: raise Bound('aggregate metadata limit')
                block = os.read(fd, ask)
                if not block: break
                pieces.append(block); count += len(block); self.total += len(block)
                if count > remaining: raise Bound('bounded read limit')
            raw = b''.join(pieces)
            after = os.fstat(fd)
            return raw, meta(before), meta(after)
        finally: self.close(handle)

def meta(s):
    return dict(dev=s.st_dev, ino=s.st_ino, uid=s.st_uid, gid=s.st_gid,
        mode=oct(stat.S_IMODE(s.st_mode)), nlink=s.st_nlink, bytes=s.st_size,
        mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns)

def verify_grant(grant,review_ref,cap_ref):
    assert set(grant)==set(q['admission_fields'])
    assert grant['schema']=='mckernel.Root-current-HOST-admission.current64017-readonly.v1'
    assert grant['Root_thread_id']==ROOT_ID and grant['invocation']==INVOCATION and grant['same_Root_finite_credit_run_id']==CREDIT_RUN
    assert grant['request_sha256']==REQUEST_SHA256 and grant['capture_request_sha256']==cap_ref['sha256']
    assert grant['protected_parent_sha256']==sha(HERE/'run_root_once.py') and grant['protected_outer_capture_sha256']==sha(HERE/'capture_root_once.py')
    assert grant['normal_profile_sha256']==q['profile']['sha256'] and grant['runtime_operation_review']==review_ref
    assert grant['source_manifest_sha256']==q['input_manifest']['sha256']
    assert grant['account_consumer_ref']==q['account_consumer_ref'] and grant['current_owner_private_ref']==q['current_owner_private_ref']
    assert grant['source_view_verified'] is True and grant['complete_owner_accounting'] is True and grant['native_and_historical_unknowns_preserved'] is True
    # This means no OTHER exclusive owner forbids this exact read-only reader;
    # the explicitly accounted original64017 target remains held and untouched.
    assert grant['no_exclusive_other_owner_scope'] is True
    assert grant['charge']==q['charge'] and grant['new_parent_capture_overhead_reserved_bytes']==0
    assert type(grant['current_HOST_jobs_before']) is int and 1<=grant['current_HOST_jobs_before']<3
    for key in ('other_current_HOST_payload_reserved_bytes','current_owned_controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        assert type(grant[key]) is int and grant[key]>=0,key
    assert grant['other_current_HOST_payload_reserved_bytes']>=1610612736
    assert grant['current_HOST_jobs_before']+1<=3
    assert grant['other_current_HOST_payload_reserved_bytes']+grant['current_owned_controller_worker_overhead_bytes']+q['charge']['planning_bytes']<=4*GIB
    assert grant['MemAvailable_bytes']>=26*GIB and grant['host_free_bytes']>=16*GIB+q['capture_headroom_bytes'] and grant['scratch_free_bytes']>=12*GIB+q['capture_headroom_bytes']
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert grant['host_boot_id']==pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    for key in ('current_owner_validation_ref','scoped_resource_evidence'):read_ref(grant[key])
    refs=grant['actual_source_service_permission_evidence_refs'];assert isinstance(refs,list) and refs
    for item in refs:read_ref(item)
    assert grant['original64017_scope_preserved']==q['original64017_scope_preserved']

def review_binding(review,cap_ref):
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']==q['operation_review_decision']
    wanted=dict(request_sha256=REQUEST_SHA256,run_root_once_sha256=sha(HERE/'run_root_once.py'),capture_root_once_sha256=sha(HERE/'capture_root_once.py'),capture_request_sha256=cap_ref['sha256'],collector_sha256=q['collector']['sha256'],profile_sha256=q['profile']['sha256'],input_manifest_sha256=q['input_manifest']['sha256'],source_path_bindings_sha256=q['source_path_bindings']['sha256'])
    for key,value in wanted.items():assert review[key]==value,key

def verify_reader_grant(grant,review):
    global REQUEST_SHA256
    REQUEST_SHA256=sys.argv[2]
    assert q['saved_Root']==ROOT_ID and q['invocation']==INVOCATION and q['finite_credit_run_id']==CREDIT_RUN
    cap_path=HERE/'CAPTURE-REQUEST.json';cap_ref=dict(path=str(cap_path),bytes=cap_path.stat().st_size,sha256=sha(cap_path));cap=read_ref(cap_ref)
    assert cap['request']['sha256']==REQUEST_SHA256 and cap['parent']['sha256']==sha(HERE/'run_root_once.py') and cap['outer_capture']['sha256']==sha(HERE/'capture_root_once.py')
    assert cap['collector']['sha256']==sha(__file__)==q['collector']['sha256']
    rp=pathlib.Path(sys.argv[3]);review_ref=dict(path=str(rp.resolve()),bytes=rp.stat().st_size,sha256=sys.argv[4])
    review_binding(review,cap_ref);verify_grant(grant,review_ref,cap_ref)
    binding=read_ref(q['source_path_bindings'])
    assert binding['exact_source_derived_UID0_paths']['initial_DATA_root']==q['initial_DATA_root']
    assert binding['qualified_same_runtime_literal']==q['runtime']
    assert binding['actual_role_identity_supplied_by_Root_not_live_read_by_author']==q['target']

def error_row(label,error):
    row=dict(label=label,type=type(error).__name__,errno=getattr(error,'errno',None))
    OBSERVATION_ERRORS.append(row)
    return row

def blob(raw,complete=True):
    return dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
                raw_base64=base64.b64encode(raw).decode('ascii'),complete=complete)

def metadata_pread(fd,limit,offset=0):
    remaining=reader.max_total-reader.total
    if remaining<=0:raise Bound('aggregate metadata budget exhausted before pread')
    ask=min(limit+1,remaining)
    raw=os.pread(fd,ask,offset)
    reader.total+=len(raw)
    return raw

def read_current(path,limit,dir_fd=None):
    if reader.max_total-reader.total<=0:raise Bound('aggregate metadata budget exhausted before read')
    handle=reader.open(path,dir_fd=dir_fd)
    try:
        raw=bytearray();eof=False
        while len(raw)<=limit:
            remaining=reader.max_total-reader.total
            if remaining<=0:break
            ask=min(65536,limit+1-len(raw),remaining)
            block=os.read(handle['fd'],ask)
            reader.total+=len(block)
            if not block:eof=True;break
            raw.extend(block)
        return bytes(raw),eof and len(raw)<=limit
    finally:reader.close(handle)

def exact_handle(path):
    # Qualified81012 open_exact component walk, using qualified consume-once
    # Reader generations for ALL newly owned intermediate descriptors.
    check(type(path) is str and path.startswith('/') and '//' not in path,'absolute exact input')
    parts=path.split('/')[1:]
    check(parts and all(p not in ('','.','..') for p in parts),'exact input components')
    parent=reader.open('/',directory=True)
    for index,part in enumerate(parts):
        before=os.stat(part,dir_fd=parent['fd'],follow_symlinks=False)
        check(stat.S_ISDIR(before.st_mode) or stat.S_ISREG(before.st_mode),'no input symlink/special target')
        child=reader.open(part,directory=index<len(parts)-1,dir_fd=parent)
        check(stable(before)==stable(os.fstat(child['fd'])),'exact input component changed')
        reader.close(parent);parent=child
    return parent

def proc_current(role):
    pid=role['pid'];prefix='/proc/%d'%pid
    result=dict(expected=role,classification='UNAVAILABLE_NO_AUTHORITY')
    if role['role'] in ROLE_SKIPS:
        result['classification']=ROLE_SKIPS[role['role']]
        result['numeric_PID_path_not_reopened']=True
        return result
    try:
        # A held proc-directory reference anchors subsequent metadata reads to
        # this task. Never follow the numeric PID path after a reuse observation.
        handle=ROLE_HANDLES.get(role['role'])
        if handle is None:
            handle=reader.open(prefix,directory=True)
            ROLE_HANDLES[role['role']]=handle
        raw,complete=read_current('stat',8192,dir_fd=handle)
        result['raw_stat']=blob(raw,complete)
        check(complete,'proc stat bound')
        right=raw.rfind(b')');tail=raw[right+1:].split()
        check(right>0 and len(tail)>=20,'proc stat fields')
        observed=dict(pid=int(raw[:raw.find(b'(')].strip()),birth=tail[19].decode('ascii'),
                      state=tail[0].decode('ascii'),ppid=int(tail[1]),pgrp=int(tail[2]),session=int(tail[3]))
        directory=os.fstat(handle['fd'])
        observed['proc_directory_owner_uid']=directory.st_uid
        observed['proc_directory_owner_gid']=directory.st_gid
        result['observed']=observed
        if observed['pid']!=pid or observed['birth']!=role['birth']:
            result['classification']='PID_REUSED_NO_TARGET_AUTHORITY'
            ROLE_SKIPS[role['role']]=result['classification']
            reader.close(handle);ROLE_HANDLES.pop(role['role'],None)
            return result
        result['classification']='BIRTH_MATCHED_CURRENT_DATA'
        if observed['state'] in ('Z','X','x'):
            result['classification']='TERMINAL_CURRENT_NO_ORIGINAL_WAIT_PROOF'
        try:
            ns=os.stat('ns/mnt',dir_fd=handle['fd'])
            result['mount_namespace']=dict(identity=identity(ns),link=os.readlink('ns/mnt',dir_fd=handle['fd']))
        except BaseException as error:result['namespace_error']=error_row('current-mntns-'+role['role'],error)
        # Directory owner metadata is not a credential/status/environ read.
        result['credentials_or_status_contents_read']=False
    except FileNotFoundError as error:
        result['error']=error_row('current-process-'+role['role'],error)
        result['classification']='ABSENT_UNPROVEN_RETIREMENT'
        ROLE_SKIPS[role['role']]=result['classification']
    except BaseException as error:result['error']=error_row('current-process-'+role['role'],error)
    return result

def process_set():
    return {role['role']:proc_current(role) for role in q['roles']}

def read_mountinfo_current(before):
    if before['provider']['classification']!='BIRTH_MATCHED_CURRENT_DATA':
        return dict(status='NOT_READ_BIRTH_OR_LIVE_SCOPE_UNPROVED',failure_instant_bytes='UNAVAILABLE')
    try:
        raw,complete=read_current('mountinfo',q['bounds']['mountinfo_bytes_max'],dir_fd=ROLE_HANDLES['provider'])
        return dict(status='FULL_CURRENT_RAW' if complete else 'CURRENT_PREFIX_ONLY_BOUND_EXCEEDED',
                    observed_at_utc_ns=time.time_ns(),observed_at_mono_ns=time.monotonic_ns(),
                    bytes_record=blob(raw,complete),raw_newline_count=raw.count(b'\n'),
                    no_mount_parser_invoked=True,failure_instant_bytes='UNAVAILABLE')
    except BaseException as error:return dict(status='UNAVAILABLE_CURRENT',error=error_row('current-mountinfo',error))

def runtime_record():
    wanted=q['runtime'];result=dict(expected=wanted)
    try:
        handle=exact_handle(wanted['path']);st=os.fstat(handle['fd'])
        result['identity_before']=identity(st);result['flags_before']=flags(handle['fd'])
        result['identity_matches_expected']=(st.st_dev,st.st_ino,st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),st.st_nlink,st.st_size)==(wanted['device'],wanted['inode'],wanted['uid'],wanted['gid'],wanted['mode'],wanted['nlink'],wanted['bytes'])
        if result['identity_matches_expected']:
            digest=hashlib.sha256();position=0
            while position<st.st_size:
                piece=os.pread(handle['fd'],min(1024*1024,st.st_size-position),position)
                check(bool(piece),'complete bound runtime digest');digest.update(piece);position+=len(piece)
            result['sha256']=digest.hexdigest();result['hash_matches_expected']=digest.hexdigest()==wanted['sha256']
        return result,handle
    except BaseException as error:
        result['error']=error_row('bound-runtime',error);return result,None

def journal_record(root,name,label):
    value=dict(path=q['initial_DATA_root']+'/'+name,first_rows_are_current_not_failureinstant=True)
    handle=None
    try:
        handle=reader.open(name,dir_fd=root);st=os.fstat(handle['fd'])
        value['identity_before']=identity(st)
        check(stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1,'bound Root journal regular identity')
        limit=q['bounds']['journal_bytes_max'];raw=metadata_pread(handle['fd'],limit)
        complete=len(raw)<=limit and len(raw)==st.st_size
        value['bytes_record']=blob(raw,complete)
        lines=raw.splitlines(keepends=True)
        value['raw_line_count']=len(lines)
        value['first_rows']=[blob(line) for line in lines[:q['bounds']['journal_first_rows_max']]]
        value['first_rows_truncated']=len(lines)>q['bounds']['journal_first_rows_max']
        value['safe_priorflags_observations']=[]
        for line in lines[:q['bounds']['journal_first_rows_max']]:
            try:item=json.loads(line,object_pairs_hook=unique)
            except (ValueError,UnicodeDecodeError):continue
            if type(item) is dict and set(item)=={'path','device','inode','old_flags'} and item['path']==q['runtime']['path'] and type(item['old_flags']) is int:
                value['safe_priorflags_observations'].append(item)
        value['priorflags_observation_count']=len(value['safe_priorflags_observations'])
        value['no_uniqueness_or_restoration_authority_inferred']=True
    except BaseException as error:value['error']=error_row(label,error)
    return value,handle

def private_reference_metadata(root,name,label):
    result=dict(path=q['initial_DATA_root']+'/'+name,contents_read=False,rollback_target=False)
    handle=None
    try:
        handle=reader.open(name,dir_fd=root);st=os.fstat(handle['fd'])
        result.update(identity_before=identity(st),flags_before=flags(handle['fd']))
        check(stat.S_ISREG(st.st_mode),'bound Root reference regular file')
    except BaseException as error:result['error']=error_row(label,error)
    return result,handle

def runtime_lock_rows():
    result=dict(matching_rows=[],observed_at_utc_ns=time.time_ns(),no_uniqueness_assertion=True)
    try:
        raw,complete=read_current('/proc/locks',q['bounds']['locks_bytes_max'])
        result['whole_locks_read_complete']=complete
        for line in raw.splitlines(keepends=True):
            fields=line.split()
            if len(fields)<8 or fields[1:4]!=[b'FLOCK',b'ADVISORY',b'WRITE']:continue
            try:
                major,minor,inode=fields[5].split(b':')
                match=(int(major,16),int(minor,16),int(inode))==(os.major(q['runtime']['device']),os.minor(q['runtime']['device']),q['runtime']['inode'])
                if match:result['matching_rows'].append(dict(owner_pid=int(fields[4]),raw=blob(line),range=[x.decode('ascii') for x in fields[6:8]]))
            except (ValueError,UnicodeDecodeError):continue
        result['observation_count']=len(result['matching_rows'])
    except BaseException as error:result['error']=error_row('runtime-FLOCK-metadata',error)
    return result

def descriptor_bindings(wanted,before):
    result=dict(selected=[],descriptor_numbers=[],no_peerFD_open_dup_close=True,no_uniqueness_assertion=True)
    if before['provider']['classification']!='BIRTH_MATCHED_CURRENT_DATA':
        result['status']='NOT_READ_BIRTH_OR_LIVE_SCOPE_UNPROVED';return result
    prefix='/proc/%d'%q['target']['provider_pid']
    try:
        proc_handle=ROLE_HANDLES['provider']
        fd_directory=reader.open('fd',directory=True,dir_fd=proc_handle)
        names=os.listdir(fd_directory['fd']);check(len(names)<=q['bounds']['provider_FD_count_max'] and all(x.isdecimal() for x in names),'bounded one-provider FD names')
        result['descriptor_numbers']=sorted(int(x) for x in names)
        for number in result['descriptor_numbers']:
            try:
                target=os.stat(str(number),dir_fd=fd_directory['fd'])
                labels=[label for label,key in wanted.items() if key==(target.st_dev,target.st_ino)]
                if not labels:continue
                raw,complete=read_current('fdinfo/'+str(number),q['bounds']['FDinfo_bytes_max'],dir_fd=proc_handle)
                result['selected'].append(dict(fd=number,labels=labels,target_metadata=identity(target),
                    target_link=os.readlink(str(number),dir_fd=fd_directory['fd']),raw_FDinfo=blob(raw,complete)))
            except BaseException as error:result.setdefault('errors',[]).append(error_row('bound-provider-FD-'+str(number),error))
        result['observations_by_label']={label:sum(label in row['labels'] for row in result['selected']) for label in wanted}
        reader.close(fd_directory)
    except BaseException as error:result['error']=error_row('provider-FD-metadata',error)
    return result

def current_snapshot():
    raw=dict(scope='CURRENT_64017_PROVIDER_METADATA_NOT_FAILURE_INSTANT',
             failed_mountinfo_row='UNAVAILABLE_NO_RECONSTRUCTION',at_utc_ns=time.time_ns(),at_mono_ns=time.monotonic_ns(),
             process_before=process_set(),source_path_bindings=q['source_path_bindings'],
             no_source_parser_or_failure_replay=True,no_original_scope_disposition=True)
    raw['mountinfo_current']=read_mountinfo_current(raw['process_before'])
    runtime,runtime_handle=runtime_record();raw['runtime']=runtime
    root=None;held=[];wanted={'runtime':(q['runtime']['device'],q['runtime']['inode'])}
    try:
        root=exact_handle(q['initial_DATA_root']);root_private(root['fd']);rst=os.fstat(root['fd'])
        raw['initial_DATA_root_identity']=identity(rst);wanted['initial_DATA_root']=(rst.st_dev,rst.st_ino)
        raw['journals']={}
        for label,name in q['journal_names'].items():
            value,handle=journal_record(root,name,label);raw['journals'][label]=value
            if handle is not None:held.append((label,value,handle));st=os.fstat(handle['fd']);wanted[label]=(st.st_dev,st.st_ino)
        raw['bound_private_references']={}
        for label,name in q['private_reference_names'].items():
            value,handle=private_reference_metadata(root,name,label);raw['bound_private_references'][label]=value
            if handle is not None:held.append((label,value,handle));st=os.fstat(handle['fd']);wanted[label]=(st.st_dev,st.st_ino)
    except BaseException as error:raw['initial_DATA_error']=error_row('exact-initial-DATA-root',error)
    raw['FLOCK_before']=runtime_lock_rows();raw['held_FD_bindings_before']=descriptor_bindings(wanted,raw['process_before'])
    raw['held_FD_bindings_after']=descriptor_bindings(wanted,raw['process_before']);raw['FLOCK_after']=runtime_lock_rows()
    for label,value,handle in held:
        try:
            value['identity_after']=identity(os.fstat(handle['fd']))
            value['held_identity_bookend_equal']=value.get('identity_before')==value['identity_after']
            if label in q['journal_names']:
                limit=q['bounds']['journal_bytes_max'];again=metadata_pread(handle['fd'],limit)
                value['current_bytes_after']=blob(again,len(again)<=limit and len(again)==os.fstat(handle['fd']).st_size)
                value['journal_raw_bookend_equal']=value.get('bytes_record',{}).get('sha256')==hashlib.sha256(again).hexdigest()
            else:value['flags_after']=flags(handle['fd'])
        except BaseException as error:value['bookend_error']=error_row(label+'-bookend',error)
    if runtime_handle is not None:
        try:runtime.update(identity_after=identity(os.fstat(runtime_handle['fd'])),path_identity_after=identity(os.stat(q['runtime']['path'],follow_symlinks=False)),flags_after=flags(runtime_handle['fd']))
        except BaseException as error:runtime['bookend_error']=error_row('runtime-bookend',error)
    raw['process_after']=process_set()
    raw['bookends_are_observations_not_original_wait_or_release']=True
    raw['observation_errors']=OBSERVATION_ERRORS
    return raw

def finish_known_own_handles_once():
    for handle in tuple(reader.opened.values()):
        if not handle['consumed']:
            try:reader.close(handle)
            except BaseException as error:RETAINED_ERRORS.append((error,error.__traceback__))

def hold_own_uncertainty_nonescaping():
    while True:
        try:
            if not reader.opened and not reader.close_uncertainties:return
            try:signal.pause()
            except BaseException as error:RETAINED_ERRORS.append((error,error.__traceback__))
        except BaseException as error:
            try:RETAINED_ERRORS.append((error,error.__traceback__))
            except BaseException:pass

def persist_private(raw):
    parent=exact_handle(str(HERE));name=q['private_output_directory_name']
    os.mkdir(name,0o700,dir_fd=parent['fd'])
    directory=reader.open(name,directory=True,dir_fd=parent);root_private(directory['fd'])
    fd=os.open(q['private_output_file_name'],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory['fd'])
    handle=reader.adopt(fd,'new-reader-private-DATA-writer')
    data=(json.dumps(raw,sort_keys=True,separators=(',',':'))+'\n').encode()
    check(len(data)<=q['bounds']['private_DATA_bytes_max'],'bounded complete private DATA')
    write_all(fd,data);os.fsync(fd);os.fsync(directory['fd']);os.fsync(parent['fd'])
    st=os.fstat(fd);check(st.st_uid==st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'new Root-private DATA identity')
    value=dict(path=str(HERE/name/q['private_output_file_name']),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),identity=identity(st),Root_uid0_mode0600_directory0700=True)
    reader.close(handle);reader.close(directory);reader.close(parent)
    return value

def main():
    global q,reader
    check(len(sys.argv)==7 and os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={0},'one admitted UID0 CPU0 metadata reader only')
    qpath=pathlib.Path(sys.argv[1]);check(sha(qpath)==sys.argv[2],'request hash')
    q=json.loads(qpath.read_bytes());review=read_ref(dict(path=sys.argv[3],bytes=pathlib.Path(sys.argv[3]).stat().st_size,sha256=sys.argv[4]))
    grant_ref=dict(path=sys.argv[5],bytes=pathlib.Path(sys.argv[5]).stat().st_size,sha256=sys.argv[6]);grant=read_ref(grant_ref)
    verify_reader_grant(grant,review)
    reader=Reader({'aggregate_raw_metadata_bytes_max':q['bounds']['aggregate_metadata_bytes_max']})
    raw=None;primary=None;primary_tb=None;output=None
    try:
        raw=current_snapshot()
    except BaseException as error:
        primary=error;primary_tb=error.__traceback__
        raw=dict(scope='CURRENT_METADATA_COLLECTION_PARTIAL_NO_ORIGINAL_AUTHORITY',error=error_row('outer-collection',error),failed_mountinfo_row='UNAVAILABLE')
    finally:
        # Preserve already collected raw evidence before the permanent OWN-FD
        # uncertainty hold. No uncertain close is retried or declared closed.
        finish_known_own_handles_once()
    raw.update(collector_pid=os.getpid(),collector_birth=pathlib.Path('/proc/self/stat').read_bytes().rsplit(b')',1)[1].split()[19].decode(),
               request_sha256=sys.argv[2],operation_review_sha256=sys.argv[4],admission_sha256=sys.argv[6],
               aggregate_current_raw_metadata_bytes=reader.total,own_input_FD_events=list(reader.events),own_input_FDs_closed=not reader.opened and not reader.close_uncertainties,
               original64017_session_HOST_1610612736B_job1_runtime_native12_source_globalUNKNOWNs_retained=True,
               sourceplans_code_config_rootI_files_are_evidence_not_rollback_targets=True)
    try:output=persist_private(raw)
    finally:
        try:finish_known_own_handles_once()
        finally:hold_own_uncertainty_nonescaping()
    children=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split()
    check(not children and not reader.opened and not reader.close_uncertainties,'new reader own closure')
    print(json.dumps(dict(status='CURRENT64017_METADATA_RECORDED_NO_DISPOSITION',collector_pid=raw['collector_pid'],collector_birth=raw['collector_birth'],
        raw_private_record=output,own_input_and_output_FDs_all_closed=True,own_close_errors=0,own_FD_close_events=reader.events,
        remaining_collector_direct_children=children,observation_error_count=len(OBSERVATION_ERRORS),
        primary_collection_error_type=type(primary).__name__ if primary else None,
        process_classifications_before={k:v['classification'] for k,v in raw.get('process_before',{}).items()},
        process_classifications_after={k:v['classification'] for k,v in raw.get('process_after',{}).items()},
        mountinfo_current_status=raw.get('mountinfo_current',{}).get('status'),
        no_parser_replay_no_failedinstant_reconstruction_no_original_release=True,
        original64017_1_5GiB_native12_runtime_source_allUNKNOWNs_retained=True),sort_keys=True),flush=True)
    return 0

if __name__=='__main__':
    try:
        result=main()
    except BaseException as original_error:
        ACTOR_PRIMARY_RAW=original_error;ACTOR_PRIMARY_TB=original_error.__traceback__
        raise
    finally:
        # Outermost same actor context cannot escape an uncertain OWN handle.
        # Neither bookkeeping failures nor a missing partial record allow exit.
        if reader is not None:
            while True:
                try:
                    finish_known_own_handles_once()
                    hold_own_uncertainty_nonescaping()
                    break
                except BaseException as retention_error:
                    try:RETAINED_ERRORS.append((retention_error,retention_error.__traceback__))
                    except BaseException:pass
    sys.exit(result)
