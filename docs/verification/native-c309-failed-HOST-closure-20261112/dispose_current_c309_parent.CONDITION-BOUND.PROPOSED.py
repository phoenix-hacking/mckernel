"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exactly one source-bound failed-parent pidfd SIGKILL; no original wait or release.
"""
import base64,datetime,errno,fcntl,hashlib,json,os,pathlib,resource,select,signal,stat,sys,time,traceback,types
BASE=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-diagnostic-successor-1/normal-fixed30-reporting-proposal-1/current-c309-failed-recovery-1')
NONCE='c309bcddf9ddc0e4187a29d494c90a7be08a2882fe82614a380ccd3a5a951758'
TARGET_PID=1995217
TARGET_BIRTH='59502337'
SUDO_PID=1995214
SUDO_BIRTH='59502329'
SUDO_CALLER_PID=1995202
KEEPER_PID=1995219
KEEPER_BIRTH='59502349'
INSTALLER_PID=1995220
INSTALLER_BIRTH='59502365'
RAW_OUTPUT=None
OWNED=[]
RAW_CLOSE_ERRORS=[]
RAW_ERRORS=[]
ACTION_STATE={'signal_attempted':False,'signal_returned':False,'pidfd_terminal_observed':False}
def stable(st): return st.st_dev, st.st_ino, st.st_mode, st.st_nlink, st.st_size, st.st_mtime_ns, st.st_ctime_ns

def check(ok,message):
    if not ok:raise ValueError(message)

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

def open_exact(path):
    """Pin the same host path; consume each temporary handle before one close."""
    check(type(path) is str and path.startswith('/') and '//' not in path,'absolute host path')
    parts=path.split('/')[1:]
    check(parts and all(x not in ('','.','..') for x in parts),'host path')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);child=None
    try:
        for i,part in enumerate(parts):
            st=os.stat(part,dir_fd=fd,follow_symlinks=False)
            check(stat.S_ISDIR(st.st_mode) or stat.S_ISREG(st.st_mode),'symlink or special source path')
            opts=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if i<len(parts)-1:opts|=os.O_DIRECTORY
            child=os.open(part,opts,dir_fd=fd)
            check(stable(os.fstat(child))==stable(st),'host identity changed while opening')
            closing=fd;fd=None
            try:os.close(closing)
            except BaseException as error:
                RAW_CLOSE_ERRORS.append(('open_exact:temporary-parent',error,error.__traceback__));raise
            fd=child;child=None
        returned=fd;fd=None;return returned
    finally:
        remaining=(('open_exact:temporary-child',child),('open_exact:temporary-parent',fd));child=None;fd=None
        for label,closing in remaining:
            if closing is None:continue
            try:os.close(closing)
            except BaseException as error:RAW_CLOSE_ERRORS.append((label,error,error.__traceback__))

def own(fd,label):
    row={'fd':fd,'historical_fd':fd,'label':label,'state':'HELD'};OWNED.append(row);return row

def drain(rows):
    for row in reversed(rows):
        if row['state']!='HELD':continue
        fd=row['fd'];row['fd']=None;row['state']='CLOSE_ATTEMPTED_UNKNOWN'
        try:os.close(fd)
        except BaseException as error:RAW_CLOSE_ERRORS.append((row['label'],error,error.__traceback__))
        else:row['state']='CLOSED'

def identity(st):
    return {'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'nlink':st.st_nlink,'bytes':st.st_size,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}

def read_owned(row,limit):
    before=os.fstat(row['fd']);check(stat.S_ISREG(before.st_mode) and 0<before.st_size<=limit,'exact bounded regular input')
    raw=os.pread(row['fd'],before.st_size+1,0);after=os.fstat(row['fd'])
    check(len(raw)==before.st_size and stable(before)==stable(after),'stable complete input read')
    return before,raw

def raw_error(label,error,tb):
    return {'label':label,'type':type(error).__name__,'message':str(error)[:1024],'traceback':''.join(traceback.format_exception(type(error),error,tb))[-16384:]}

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def persist_raw(value):
    start=len(OWNED);primary=None;result=None
    try:
        parent=own(open_exact(str(pathlib.Path(RAW_OUTPUT).parent)),'evidence:parent-directory');name=pathlib.Path(RAW_OUTPUT).name
        os.mkdir(name,0o700,dir_fd=parent['fd']);directory=own(os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent['fd']),'evidence:Root-private-directory');root_private(directory['fd'])
        record=own(os.open('OWNER-RECORD.PRIVATE.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=directory['fd']),'evidence:private-writer');data=json.dumps(value,sort_keys=True,separators=(',',':')).encode()+b'\n';check(len(data)<=32*1024*1024,'bounded private output');write_all(record['fd'],data);os.fsync(record['fd']);os.fsync(directory['fd']);os.fsync(parent['fd']);st=os.fstat(record['fd']);check(st.st_uid==st.st_gid==0 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'Root-private output identity')
        result={'path':RAW_OUTPUT+'/OWNER-RECORD.PRIVATE.json','bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'identity':identity(st),'Root_uid0_mode0600_and_directory0700':True}
    except BaseException as error:primary=(error,error.__traceback__)
    finally:drain(OWNED[start:])
    if primary is not None:raise BaseException.with_traceback(primary[0],primary[1])
    check(not RAW_CLOSE_ERRORS,'own evidence close uncertain');return result

def digest_value(value):
    check(type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value),'saved digest type')
    return value

def reference_shape(row):
    check(type(row) is dict and set(row)=={'path','bytes','sha256'},'actual receipt reference')
    check(type(row['path']) is str and row['path'].startswith('/') and type(row['bytes']) is int and 0<row['bytes']<=4*1024*1024,'actual receipt ref bounds')
    digest_value(row['sha256'])

def fresh_admission(a,q,request_sha,review_sha):
    check(type(a) is dict and set(a)==set(q['required_parent_actor_admission_keys']),'complete admission field union')
    for key,value in q['admission_exact_values'].items():check(a[key]==value,'actual admission scope binding')
    check(a['request_sha256']==request_sha and a['review_sha256']==review_sha and a['complete_parent_actor_profile']==q['profile'],'exact request/review/profile')
    check(a['actual_current_account_result']=='ACCEPTED','actual accepted current account')
    for key in ('actual_current_account_ref','actual_source_permission_resource_ref'):reference_shape(a[key])
    check(type(a['at']) is str and 0<=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()<=25,'fresh actual UTC admission')
    check(type(a['issued_monotonic_ns']) is int and 0<=time.monotonic_ns()-a['issued_monotonic_ns']<=25*10**9,'fresh actual monotonic admission')
    for key in ('current_HOST_jobs_before','current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):check(type(a[key]) is int,'exact resource integer')
    check(1<=a['current_HOST_jobs_before']<3 and a['current_HOST_payload_reserved_bytes_before']>=2147483648 and a['controller_worker_overhead_bytes']>=0,'retain current original 2GiB job')
    check(a['controller_worker_overhead_bytes']+a['current_HOST_payload_reserved_bytes_before']+268435456<=4*2**30,'shared allowner HOST budget')
    check(a['MemAvailable_bytes']>=26*2**30 and a['host_free_bytes']>=16*2**30+67108864 and a['scratch_free_bytes']>=12*2**30+67108864,'current capacity and floors')

def sealed_json(path,digest,label):
    row=own(open_exact(path),label);st,raw=read_owned(row,4*1024*1024)
    check(st.st_uid in (0,1000) and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1,'sealed control input identity')
    check(hashlib.sha256(raw).hexdigest()==digest,'sealed control input hash')
    return strict_json(raw)

def read_path(path,limit):
    with open(path,'rb') as stream:raw=stream.read(limit+1)
    check(len(raw)<=limit,'read bound');return raw

def proc(pid,birth):
    raw=read_path('/proc/%d/stat'%pid,8192);tail=raw.rsplit(b')',1)[1].split()
    check(len(tail)>=20 and tail[0] not in (b'Z',b'X',b'x') and tail[19].decode()==birth,'exact live PID/birth required')
    status=read_path('/proc/%d/status'%pid,32768).decode('ascii')
    uid=next(x for x in status.splitlines() if x.startswith('Uid:')).split()[1:]
    check(uid==['0','0','0','0'],'actual original Root identity required')
    return {'pid':pid,'birth':birth,'state':tail[0].decode(),'ppid':int(tail[1]),'pgrp':int(tail[2]),'session':int(tail[3]),'uid':[int(x) for x in uid]}

def strict_json(raw):
    def nonfinite(value):raise ValueError('nonfinite JSON number')
    return json.loads(raw,object_pairs_hook=unique,parse_constant=nonfinite)

def bound_reference(row):
    reference_shape(row);data=pathlib.Path(row['path']).read_bytes()
    check(len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256'],'actual frozen source and saved fact binding')
    return data

def persist_at(label,value):
    global RAW_OUTPUT
    RAW_OUTPUT=str(BASE/('Root-A-'+str(os.getpid())+'-'+label))
    return persist_raw(value)

def retain_unknown(error,tb):
    RAW_ERRORS.append(('phaseA',error,tb))
    try:persist_at('UNKNOWN',{'status':'CURRENT_C309_PARENT_DISPOSITION_UNKNOWN_RETAINED','phase':'A','error':raw_error('phaseA',error,tb),'action_state':dict(ACTION_STATE),'original81691_and2GiB_lease_all_native_source_UNKNOWNs_retained':True,'no_other_signal_wait_flags_or_release':True})
    except BaseException as secondary:RAW_ERRORS.append(('report',secondary,secondary.__traceback__))
    # The same foreground actor retains its handles; no replacement or retry.
    while True:
        try:signal.pause()
        except BaseException as secondary:RAW_ERRORS.append(('hold-interruption',secondary,secondary.__traceback__))

def old_role_observation(pid,birth):
    try:raw=read_path('/proc/%d/stat'%pid,8192)
    except FileNotFoundError:return {'pid':pid,'expected_birth':birth,'observation':'ABSENT_CURRENT_DATA_NOT_ORIGINAL_WAIT'}
    tail=raw.rsplit(b')',1)[1].split();check(len(tail)>=20,'bounded original role stat')
    actual=tail[19].decode('ascii')
    if actual!=birth:return {'pid':pid,'expected_birth':birth,'observed_other_birth':actual,'observation':'REUSED_ORIGINAL_ABSENT_DATA_NOT_WAIT'}
    return {'pid':pid,'expected_birth':birth,'observed_birth':actual,'state':tail[0].decode('ascii'),'observation':'SAME_BIRTH_PRESENT_REQUIRES_OWN_DISPOSITION'}

def capture_channel_metadata():
    rows=[]
    for number,inode in ((1,2254658),(2,2254659)):
        st=os.stat('/proc/%d/fd/%d'%(TARGET_PID,number))
        check(stat.S_ISREG(st.st_mode) and st.st_uid==1000 and stat.S_IMODE(st.st_mode)==0o600 and st.st_nlink==1 and (st.st_dev,st.st_ino)==(66306,inode),'current failed parent original capture channel identity')
        text=read_path('/proc/%d/fdinfo/%d'%(TARGET_PID,number),32768).decode('ascii')
        values=[line.split()[1] for line in text.splitlines() if line.startswith('flags:')]
        check(len(values)==1,'actual parent capture FD access flags')
        flags=int(values[0],8);check(flags&os.O_ACCMODE in (os.O_WRONLY,os.O_RDWR),'original parent capture channel remains writable')
        check(stable(os.stat('/proc/%d/fd/%d'%(TARGET_PID,number)))==stable(st),'same capture channel through access metadata read')
        rows.append({'fd':number,'identity':identity(st),'flags':flags,'observation':'CURRENT_PARENT_WRITABLE_CAPTURE_FD_METADATA_ONLY_NO_CONTENT_READ'})
    return rows

def exact_target():
    first=proc(TARGET_PID,TARGET_BIRTH);sudo=proc(SUDO_PID,SUDO_BIRTH)
    check(first['ppid']==SUDO_PID and sudo['ppid']==SUDO_CALLER_PID,'original direct Root parent/SUDO/owning caller relation')
    children=read_path('/proc/%d/task/%d/children'%(TARGET_PID,TARGET_PID),32768).decode('ascii').split()
    check(not children,'no current running or unjoined owned child before exact parent disposition')
    keeper=old_role_observation(KEEPER_PID,KEEPER_BIRTH);installer=old_role_observation(INSTALLER_PID,INSTALLER_BIRTH)
    check(keeper['observation']!='SAME_BIRTH_PRESENT_REQUIRES_OWN_DISPOSITION' and installer['observation']!='SAME_BIRTH_PRESENT_REQUIRES_OWN_DISPOSITION','same-birth keeper or installer requires separate owning custody')
    status=read_path('/proc/%d/status'%TARGET_PID,32768).decode('ascii');masks={}
    threads=[line.split()[1] for line in status.splitlines() if line.startswith('Threads:')]
    check(threads==['1'],'current source-supported single-thread Root parent')
    for name in ('SigBlk','SigIgn','SigCgt'):
        values=[line.split()[1] for line in status.splitlines() if line.startswith(name+':')]
        check(len(values)==1,'current exact signal mask field');masks[name]=int(values[0],16)
    bit=1<<(int(signal.SIGKILL)-1)
    check(not (masks['SigBlk']|masks['SigIgn']|masks['SigCgt'])&bit,'exact SIGKILL mask consistency')
    channels=capture_channel_metadata();last=proc(TARGET_PID,TARGET_BIRTH);last_sudo=proc(SUDO_PID,SUDO_BIRTH)
    check(first==last and sudo==last_sudo,'same exact birth and original SUDO relation through current metadata checks')
    check(pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='3ba4f2ca-4323-433d-bfb8-7859268121b6','same actual boot')
    return {'parent':last,'sudo':last_sudo,'parent_direct_children':children,'parent_threads':1,'keeper':keeper,'installer':installer,'signal_masks':masks,'capture_channels':channels,'one_selected_signal':int(signal.SIGKILL),'original_heldRootFD_lease_inode_original_keeper_directwait':'UNPROVED_NOT_ADOPTED_OR_DISPOSED','peer_socket_semantic_state':'UNPROVED_NO_REMOTE_FD_OR_RPC_ACTION'}

def target_identity(value):
    return {key:value[key] for key in ('parent','sudo','parent_direct_children','parent_threads','keeper','installer','signal_masks','capture_channels')}

def actual_saved_facts(q):
    for key in ('actual_reader_qualification','actual_failed_family_conditions','original_sudo_birth_receipt','reader_only_retirement'):
        bound_reference(q[key])
    point=q['original_SUDO_CHILD_record'];point_row=own(open_exact(point['path']),'original-SUDO-CHILD-point-readonly')
    point_st,point_raw=read_owned(point_row,4096)
    check(len(point_raw)==point['bytes'] and hashlib.sha256(point_raw).hexdigest()==point['sha256'] and (point_st.st_dev,point_st.st_ino)==(66306,2254664) and point_st.st_uid==1000 and stat.S_IMODE(point_st.st_mode)==0o600 and point_st.st_nlink==1,'stable original owned SUDO saved point identity')
    sudo=strict_json(point_raw)
    check(sudo=={'birth':SUDO_BIRTH,'pid':SUDO_PID,'parent_pid':SUDO_CALLER_PID,'status':'DIRECT_CHILD_HELD','nonce':NONCE},'actual original owned SUDO point record not terminal proof')
    value=strict_json(bound_reference(q['actual_safe_saved_projection']));saved=value['safe_projection'];result=saved['result'];journal=saved['keeper_journal']
    check(value['status']=='SAVED_C309_TWO_FILE_PROJECTION_CAPTURED_NO_DISPOSITION' and value['nonce']==NONCE and value['all_two_saved_reads_enclosed_by_same_directory_and_file_bookends'] and value['all_new_own_FDs_closed'],'actual qualified saved two-file capture')
    check(result['nonce']==NONCE and result['installer']=={'pid':INSTALLER_PID,'birth':INSTALLER_BIRTH,'pgid':INSTALLER_PID} and result['keeper']=={'pid':KEEPER_PID,'birth':KEEPER_BIRTH} and result['installer_wait_status']==0,'already-recorded installer/keeper role and directwait DATA')
    check(result['captures']['count']==2 and all(row['writer_closed'] is True for row in result['captures']['rows']),'already-recorded two capture writers closed')
    check(journal['record_count']==16 and len(journal['RESULT_DURABLE_records'])==1 and not journal['RESULT_PARENT_ACK_records'] and saved['RESULT_DURABLE_matches_saved_result_hash']==[True],'actual saved durable result and no saved ACK DATA')
    return {'reader_qualification_sha256':q['actual_reader_qualification']['sha256'],'safe_projection_sha256':q['actual_safe_saved_projection']['sha256'],'recorded_installer_wait_status':0,'recorded_capture_writers_closed':True,'recorded_RESULT_DURABLE':True,'saved_RESULT_PARENT_ACK_present':False,'original_direct_waits_lease_rootFD_and_normal_completion_not_reconstructed':True},(point_row,point_st)

def load_pidfd(q):
    raw=bound_reference(q['pidfd_helper']);module=types.ModuleType('qualified_current_c309_pidfd');module.__file__=q['pidfd_helper']['path']
    exec(compile(raw,module.__file__,'exec'),module.__dict__);return module

def exact_own_pidfd(fd):
    text=read_path('/proc/self/fdinfo/%d'%fd,32768).decode('ascii')
    check([int(line.split()[1]) for line in text.splitlines() if line.startswith('Pid:')]==[TARGET_PID],'actual own pidfd current target')

def phase_A(q,a,request_sha,review_sha):
    try:
        saved,sudo_point=actual_saved_facts(q);P=load_pidfd(q);initial=exact_target()
        try:fd=P.open_pidfd(TARGET_PID,0)
        except P.PidfdVerificationError as error:
            own(error.fd,'actor:unverified-new-pidfd-unknown');raise
        row=own(fd,'actor:exact-c309-failed-parent-pidfd');pinned=exact_target()
        check(target_identity(initial)==target_identity(pinned),'same current parent custody after own pidfd pin')
        exact_own_pidfd(fd)
        poll=select.poll();poll.register(fd,select.POLLIN);check(not poll.poll(0),'original parent already terminal; no signal or invented old wait')
        before=persist_at('BEFORE',{'status':'CURRENT_C309_ONE_PARENT_SIGKILL9_PREPARED','target':pinned,'saved_source_facts':saved,'action_state':dict(ACTION_STATE),'original81691_and2GiB_lease_native12_source_globalUNKNOWNs_retained':True})
        # All source reads and private BEFORE fsync completed. The same target,
        # channels, absent old children, pidfd and fresh both clocks gate send.
        fresh_admission(a,q,request_sha,review_sha);last=exact_target()
        point_row,point_st=sudo_point
        check(stable(os.fstat(point_row['fd']))==stable(point_st) and stable(os.stat(q['original_SUDO_CHILD_record']['path'],follow_symlinks=False))==stable(point_st),'same original SUDO point held and named final bookends')
        exact_own_pidfd(fd)
        check(target_identity(last)==target_identity(pinned) and not poll.poll(0),'same current exact parent immediately before sole signal')
        fresh_admission(a,q,request_sha,review_sha)
        ACTION_STATE['signal_attempted']=True
        P.send_signal(fd,signal.SIGKILL,0)  # Exactly one signal to this pidfd only.
        ACTION_STATE['signal_returned']=True
        events=poll.poll(30000)
        check(any(pfd==fd and event&select.POLLIN for pfd,event in events),'exact parent pidfd terminal observation unavailable; retain UNKNOWN')
        ACTION_STATE['pidfd_terminal_observed']=True
        result={'status':'CURRENT_C309_FAILED_PARENT_PIDFD_TERMINAL_ORIGINAL81691_B_AND_LEASE_PROOF_PENDING','parent_pid':TARGET_PID,'parent_birth':TARGET_BIRTH,'signal':int(signal.SIGKILL),'pidfd_terminal_observed':True,'action_state':dict(ACTION_STATE),'before_private_ref':before,'saved_source_facts':saved,'original_Root_session':81691,'original_SUDO_or_keeper_direct_wait_proven':False,'original_heldRootFD_and_normal_lease_disposition':'UNPROVED_NOT_ADOPTED_OR_RESTORED','peer_socket_semantic_state':'UNPROVED_NO_REMOTE_FD_OR_RPC_ACTION','original_2GiB_lease_native12_source_globalUNKNOWN_retained':True,'any_resource_or_native_release_or_install_adoption':False,'TERM_or_other_role_or_group_signal':False,'second_supervisor_or_original_role_waitpid':False,'flags_FLOCK_namespace_account_verifier_issuer_native_operation':False}
        after=persist_at('AFTER',result);drain(OWNED)
        check(not RAW_CLOSE_ERRORS and all(r['state']=='CLOSED' and r['fd'] is None for r in OWNED),'all new actor own handles positively closed')
        children=read_path('/proc/self/task/%d/children'%os.getpid(),32768).decode('ascii').split();check(not children,'new actor direct children unknown')
        result.update(after_private_ref=after,all_new_actor_own_FDs_closed=True,new_actor_close_errors=0,remaining_new_actor_direct_children=children)
        return result
    except BaseException as error:retain_unknown(error,error.__traceback__)

def main():
    check(len(sys.argv)==7,'exact phaseA request/review/fresh admission arguments')
    request,request_sha,review,review_sha,admission,admission_sha=sys.argv[1:]
    q=sealed_json(request,request_sha,'request');go=sealed_json(review,review_sha,'review');a=sealed_json(admission,admission_sha,'Root actual admission')
    check(os.getuid()==os.geteuid()==0 and q['nonce']==NONCE and q['phase']=='A' and go['decision'].startswith('GO') and go['request']['sha256']==request_sha,'actualRoot exact source and operation GO')
    check(resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_CPU)==(40,40) and resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864) and resource.getrlimit(resource.RLIMIT_NOFILE)==(128,128) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0) and os.sched_getaffinity(0)=={0},'exact parent-disposition Root actor profile')
    fresh_admission(a,q,request_sha,review_sha)
    print(json.dumps(phase_A(q,a,request_sha,review_sha),sort_keys=True,allow_nan=False),flush=True);return 0

if __name__=='__main__':
    try:code=main()
    except BaseException as error:
        if ACTION_STATE['signal_attempted']:retain_unknown(error,error.__traceback__)
        drain(OWNED);print(json.dumps({'status':'C309_PHASE_A_PRECONDITION_FAILED_NO_SIGNAL_OR_DISPOSITION','error_type':type(error).__name__,'all_new_own_FDs_closed':all(r['state']=='CLOSED' for r in OWNED) and not RAW_CLOSE_ERRORS,'original81691_and2GiB_retained':True}));code=1
    sys.exit(code)
