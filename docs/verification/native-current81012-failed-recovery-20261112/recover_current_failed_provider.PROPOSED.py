import base64,datetime,fcntl,hashlib,json,os,pathlib,resource,select,signal,stat,struct,sys,time,traceback,types
from pathlib import Path
BASE=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-failed-recovery-1/configured-lock-absence-correction-1')
CONDITIONS=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current81012-failure-and-custody-review-1/saved-result-projection-operation-review-1/local-stable-binding-delta-review-1/actual-result-qualification-1/FAILED-ATTEMPT-RECOVERY.CONDITIONS.json')
CONDITIONS_SHA='7bef8c975eb42a07fe7637a008786047ea2e930fc788057c6faaf1eee2b7c1b0'
Q=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current81012-failure-and-custody-review-1/saved-result-projection-operation-review-1/local-stable-binding-delta-review-1/actual-result-qualification-1/QUALIFICATION.json')
Q_SHA='1e3215dc6def5dba7bff2e1bc820a3b40f3b1e4219b6f7c950442e14e0d0f4e6'
SAFE=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current81012-failure-and-custody-review-1/saved-result-projection-operation-review-1/local-stable-binding-delta-review-1/actual-result-qualification-1/ACTUAL-SAFE-RECOVERY-INPUT.DATA.json')
SAFE_SHA='406bcd5ffd9cf6d002f5fbaf800dc9910311604ffcc88dc0def017e4fd6b4758'
COLLECTOR=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-custody-read-1/saved-native-result-projection-1/local-stable-binding-correction-1/project_saved_native.READONLY.PROPOSED.py')
COLLECTOR_SHA='4c738a52c33afda062865dd5da897de34d5a51bcf52752ae24c81acddc0f0520'
PIDFD=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/candidate/package/pidfd_compat.py')
PIDFD_SHA='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
NATIVE_SOURCE=Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/candidate/package/native_resource_admission.py')
NATIVE_SOURCE_SHA='1e7ced654a476c1e978c65e6f91b57088a8803917f9dc68ab69481dade8c1462'
TARGET={'boot_id': '3ba4f2ca-4323-433d-bfb8-7859268121b6', 'finite_credit_run': '7c6ef3604bfb4008a917bba8cfb6cfaa', 'held_expected_flags': 524304, 'invocation': '20261112T094452Z-12a4bea0', 'nonce_context_only_not_reissue': '8d1833a8a7552f40403c045abe0107e6e8118c49bc39c79bc4830f3a4bb3031f', 'operation_root': '/var/lib/mckernel-native-signal-8d1833a8a7552f40403c045abe0107e6e8118c49bc39c79bc4830f3a4bb3031f', 'original_HOST_bytes_retained': 1610612736, 'original_HOST_jobs_retained': 1, 'original_Root_tool_session': 81012, 'prior_flags': 524288, 'provider_birth': '58283682', 'provider_pid': 1930708, 'runtime_bytes': 5490456, 'runtime_device': 66306, 'runtime_inode': 1048651, 'runtime_path': '/usr/bin/python3.8', 'runtime_sha256': '298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06', 'saved_Root': '01a18bc3-e072-7810-9426-75101b0856c0', 'sudo_birth': '58283676', 'sudo_pid': 1930695, 'supervisor_birth': '58283729', 'supervisor_pid': 1930710}
RAW_ERRORS=[]
OWN_PIDFDS=[]
ACTION_STATE={"signal_attempted":False,"signal_returned":False,"pidfd_terminal_observed":False}
def require(ok,message):
    if not ok:raise ValueError(message)

def sha(raw):return hashlib.sha256(raw).hexdigest()

def unique(pairs):
    value={}
    for key,item in pairs:require(key not in value,'duplicate key');value[key]=item
    return value

def bound(path,expected):
    raw=pathlib.Path(path).read_bytes();require(sha(raw)==expected,'exact reviewed bytes required');return raw

def load_module(path,expected,name):
    raw=bound(path,expected);module=types.ModuleType(name);module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__);return module

def refs_json(value):
    raw=bound(value['path'],value['sha256']);require(len(raw)==value['bytes'],'exact record size');return json.loads(raw,object_pairs_hook=unique)

def same_boot(value):return pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==value

def persist(C,phase,label,value):
    birth=pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
    C.RAW_OUTPUT=str(BASE/('Root-'+phase+'-'+str(os.getpid())+'-'+birth+'-'+label))
    return C.persist_raw(value)

def unknown(C,phase,error,tb):
    RAW_ERRORS.append((phase,error,tb))
    try:persist(C,phase,'UNKNOWN',{'status':'CURRENT_RECOVERY_UNKNOWN_RETAINED','phase':phase,'error_type':type(error).__name__,'traceback':''.join(traceback.format_exception(type(error),error,tb)),'native_and_historical_release':False,'action_state':dict(ACTION_STATE)})
    except BaseException as secondary:RAW_ERRORS.append(('report',secondary,secondary.__traceback__))
    # Existing foreground-retained-custody pattern, never a daemon/replacement.
    # Preserve actual owned pidfds/runtime FLOCK and raw errors for Root review.
    while True:
        try:signal.pause()
        except BaseException as secondary:RAW_ERRORS.append(('hold-interruption',secondary,secondary.__traceback__))

ADMISSION_KEYS={'schema','at','issued_monotonic_ns','saved_Root','invocation','same_Root_finite_credit_run_id','request_sha256','review_sha256','phase','action_scope','target_pid','target_birth','sudo_pid','sudo_birth','original_tool_session','signal_number','actual_current_account_result','actual_current_account_ref','actual_source_permission_resource_ref','complete_parent_actor_profile','new_current_family_bytes','new_current_jobs','current_HOST_jobs_before','current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes','host_boot_id','development_lock_identity','original_runtime_source_native1_5GiB_native12_and_all_UNKNOWNs_retained','no_C_runtime_restoration_native_reissue_or_resource_release_grant'}

def fresh_admission(a):
    age=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()
    require(0<=age<=25,'fresh current phaseA UTC admission')
    require(type(a['issued_monotonic_ns']) is int and 0<=time.monotonic_ns()-a['issued_monotonic_ns']<=25*10**9,'fresh current phaseA monotonic admission')

def authorize(request,request_sha,review,review_sha,admission,admission_sha):
    require(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={0},'admitted Root CPU0 only')
    q=json.loads(bound(request,request_sha),object_pairs_hook=unique)
    go=json.loads(bound(review,review_sha),object_pairs_hook=unique)
    a=json.loads(bound(admission,admission_sha),object_pairs_hook=unique)
    require(set(a)==ADMISSION_KEYS,'complete exact parent and actor admission field union')
    require(q['phase']=='A' and go['decision'].startswith('GO') and go['request']['sha256']==request_sha,'exact current phaseA operation review')
    require(a['schema']=='mckernel.Root-current81012-failed-provider-phaseA-admission.v1' and a['phase']=='A' and a['request_sha256']==request_sha and a['review_sha256']==review_sha,'actual exact phaseA admission')
    require(a['saved_Root']==TARGET['saved_Root'] and a['invocation']==TARGET['invocation'] and a['same_Root_finite_credit_run_id']==TARGET['finite_credit_run'],'same Root invocation and finite creditrun')
    require(a['host_boot_id']==TARGET['boot_id'] and same_boot(TARGET['boot_id']),'same actual boot')
    require(a['action_scope']=='EXACT_PROVIDER1930708_B58283682_PIDFD_SIGTERM_ONCE_ONLY' and a['signal_number']==int(signal.SIGTERM),'single exact provider signal scope')
    require(a['target_pid']==TARGET['provider_pid'] and a['target_birth']==TARGET['provider_birth'] and a['sudo_pid']==TARGET['sudo_pid'] and a['sudo_birth']==TARGET['sudo_birth'] and a['original_tool_session']==81012,'exact original provider sudo and owning tool')
    require(a['actual_current_account_result']=='ACCEPTED','actual fresh fe2/current7f8 owner/account/service result')
    for key in ('actual_current_account_ref','actual_source_permission_resource_ref'):
        ref=a[key];raw=bound(ref['path'],ref['sha256']);require(len(raw)==ref['bytes'],'actual fresh Root receipt bytes')
    require(a['complete_parent_actor_profile']==q['profile'] and a['new_current_family_bytes']==268435456 and a['new_current_jobs']==1,'complete exact current actor parent profile')
    require(type(a['current_HOST_jobs_before']) is int and 0<=a['current_HOST_jobs_before']<3,'complete current job count')
    for key in ('current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):
        require(type(a[key]) is int and a[key]>=0,'actual nonnegative resource integer')
    require(a['current_HOST_payload_reserved_bytes_before']>=1610612736 and a['current_HOST_payload_reserved_bytes_before']+a['controller_worker_overhead_bytes']+268435456<=4*2**30,'all original held/current/overhead/new actor fit shared4GiB')
    require(a['MemAvailable_bytes']>=26*2**30 and a['host_free_bytes']>=16*2**30+67108864 and a['scratch_free_bytes']>=12*2**30+67108864,'fresh resource and capture floors')
    require(a['original_runtime_source_native1_5GiB_native12_and_all_UNKNOWNs_retained'] is True and a['no_C_runtime_restoration_native_reissue_or_resource_release_grant'] is True,'all original holds and separate C')
    require(resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608),'exact actor profile')
    require(len(bound(Q,Q_SHA))>0 and len(bound(SAFE,SAFE_SHA))>0,'actual new qualification and safe data')
    conditions=json.loads(bound(CONDITIONS,CONDITIONS_SHA),object_pairs_hook=unique)
    require(conditions['current_exact_scope']==TARGET,'exact failed-attempt condition scope')
    fresh_admission(a);return q,a

def native_physical_reader():
    raw=bound(NATIVE_SOURCE,NATIVE_SOURCE_SHA).decode();tree=__import__('ast').parse(raw)
    names={'need','read_kernel','physical_snapshot'}
    selected=[node for node in tree.body if isinstance(node,__import__('ast').FunctionDef) and node.name in names]
    require({node.name for node in selected}==names,'exact existing native physical reader functions')
    namespace={'os':os}
    for node in tree.body:
        if isinstance(node,__import__('ast').Assign) and any(isinstance(x,__import__('ast').Name) and x.id in ('CGROUP','MEMBERS') for x in node.targets):
            namespace[node.targets[0].id]=__import__('ast').literal_eval(node.value)
    exec(compile(__import__('ast').Module(body=selected,type_ignores=[]),str(NATIVE_SOURCE),'exec'),namespace)
    return namespace['physical_snapshot']

def matching_locks(raw,wanted):
    rows=[]
    for line in raw.decode('ascii').splitlines():
        fields=line.split()
        if len(fields)>1 and fields[1]=='->':fields=fields[:1]+fields[2:]
        require(len(fields)>=8 and len(fields[5].split(':'))==3,'bounded kernel lock record grammar')
        a,b,c=fields[5].split(':');pair=(os.makedev(int(a,16),int(b,16)),int(c))
        if pair in wanted:rows.append({'device':pair[0],'inode':pair[1],'raw':line})
    return rows

def configured_lock_observation(admission):
    value=admission['development_lock_identity']
    require(type(value) is dict and set(value)=={'path','observation','identity'} and value['path']=='/run/lock/mckernel-development.lock','exact configured development-lock observation field')
    require(value['observation'] in ('PRESENT_ROOT_REGULAR_NLINK1','ABSENT_UNPROVEN'),'explicit configured-lock observation state')
    if value['observation']=='ABSENT_UNPROVEN':require(value['identity'] is None,'absent lock has no invented inode or lock proof')
    else:require(type(value['identity']) is dict and set(value['identity'])=={'device','inode','uid','gid','mode','nlink'},'exact observed development-lock inode fields')
    return value

def scoped_snapshot(C,physical,development,admission):
    native=physical(False)  # DATA only. It is not the later restoration gate.
    expected=configured_lock_observation(admission)
    wanted={(TARGET['runtime_device'],TARGET['runtime_inode'])}
    if expected['observation']=='ABSENT_UNPROVEN':
        require(development is None,'no invented development-lock descriptor')
        try:os.lstat('/run/lock/mckernel-development.lock')
        except FileNotFoundError:pass
        else:raise ValueError('configured development-lock observation changed; no substitute or fallback')
        lock_observation={'path':expected['path'],'observation':'ABSENT_UNPROVEN','identity':None,'matching_kernel_lock_rows':None,'absence_is_not_free_native_source_or_restoration_evidence':True}
    else:
        require(development is not None,'present configured development lock requires own read-only FD')
        st=os.fstat(development['fd']);identity={'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'nlink':st.st_nlink}
        require(stat.S_ISREG(st.st_mode) and st.st_uid==0 and st.st_nlink==1 and identity==expected['identity'],'actual exact development lock inode bound by fresh Root census')
        named=os.stat('/run/lock/mckernel-development.lock',follow_symlinks=False)
        require((named.st_dev,named.st_ino)==(st.st_dev,st.st_ino),'development lock named path changed')
        wanted.add((st.st_dev,st.st_ino))
        lock_observation={'path':expected['path'],'observation':expected['observation'],'identity':identity}
    lock_raw=C.read_path('/proc/locks',1024*1024);rows=matching_locks(lock_raw,wanted)
    if lock_observation['identity'] is not None:
        pair=(lock_observation['identity']['device'],lock_observation['identity']['inode'])
        lock_observation['matching_kernel_lock_rows']=[x for x in rows if (x['device'],x['inode'])==pair]
    return {'actual_native_profile_members_counters':native,'development_lock_observation':lock_observation,'matching_development_and_runtime_kernel_lock_rows':rows,'native_positive_idle_DATA_ONLY':all(not x for x in native['members'].values()) and native['memory_usage_bytes']==0 and native['pids']==0,'no_native_source_or_runtime_release_or_C_gate_from_this_snapshot':True}

def exact_target(C):
    provider=C.proc(TARGET['provider_pid'],TARGET['provider_birth']);sudo=C.proc(TARGET['sudo_pid'],TARGET['sudo_birth'])
    require(provider['ppid']==TARGET['sudo_pid'] and provider['pgrp']==provider['session']==1930695 and sudo['pgrp']==sudo['session']==1930695 and sudo['ppid']==1930694,'exact original provider/sudo/outer-parent relation')
    children=C.read_path('/proc/1930708/task/1930708/children',32768).decode('ascii').split()
    require(not children,'current provider direct children require separate custody')
    status=C.read_path('/proc/1930708/status',32768).decode('ascii');masks={}
    for name in ('SigBlk','SigIgn','SigCgt'):
        matches=[line.split()[1] for line in status.splitlines() if line.startswith(name+':')]
        require(len(matches)==1,'exact current signal mask field');masks[name]=int(matches[0],16)
    mask=1<<(int(signal.SIGTERM)-1)
    require(not (masks['SigBlk']|masks['SigIgn']|masks['SigCgt'])&mask,'exact provider SIGTERM must be unblocked unignored uncaught; no fallback')
    return {'provider':provider,'sudo':sudo,'provider_direct_children':children,'provider_signal_masks':masks,'appropriate_single_signal':int(signal.SIGTERM)}

def target_identity(value):
    keys=('pid','birth','ppid','pgrp','session','uid')
    return {'provider':{k:value['provider'][k] for k in keys},'sudo':{k:value['sudo'][k] for k in keys},'children':value['provider_direct_children'],'signal_masks':value['provider_signal_masks']}

def phase_A(q,a):
    C=load_module(COLLECTOR,COLLECTOR_SHA,'reviewed_current81012_metadata_methods')
    P=load_module(PIDFD,PIDFD_SHA,'reviewed_current81012_pidfd_compat')
    try:
        initial=exact_target(C);physical=native_physical_reader()
        observed=configured_lock_observation(a);development=None
        if observed['observation']=='PRESENT_ROOT_REGULAR_NLINK1':
            development=C.own(C.open_exact('/run/lock/mckernel-development.lock'),'actor:development-lock-readonly-no-FLOCK')
        scope_before=scoped_snapshot(C,physical,development,a)
        try:pidfd=P.open_pidfd(TARGET['provider_pid'],0)
        except P.PidfdVerificationError as error:
            C.own(error.fd,'actor:pidfd-verification-unknown');raise
        own=C.own(pidfd,'actor:exact-provider-pidfd');OWN_PIDFDS.append(own)
        pinned=exact_target(C)
        require(target_identity(initial)==target_identity(pinned) and same_boot(TARGET['boot_id']),'same original target bookends after own pidfd pin')
        info=C.read_path('/proc/self/fdinfo/'+str(pidfd),32768).decode('ascii')
        pids=[int(line.split()[1]) for line in info.splitlines() if line.startswith('Pid:')]
        require(pids==[1930708],'exact own pidfd current target')
        poll=select.poll();poll.register(pidfd,select.POLLIN);require(not poll.poll(0),'provider already terminal; no signal and no inferred old wait')
        evidence={'status':'EXACT_CURRENT_FAILED_PROVIDER_PHASE_A_PREPARED','target':pinned,'scope_snapshot':scope_before,'action_state':dict(ACTION_STATE),'original81012_and_all_runtime_source_native1_5GiB_native12_UNKNOWNs_retained':True,'no_C_or_original_wait_or_native_action':True}
        before_ref=persist(C,'A','BEFORE',evidence)
        # Private fsync and all potentially blocking source/metadata work have
        # finished. Recheck genuine grant freshness and exact target now.
        fresh_admission(a);last=exact_target(C)
        require(target_identity(last)==target_identity(pinned) and same_boot(TARGET['boot_id']) and not poll.poll(0),'same current exact provider immediately before one signal')
        fresh_admission(a)
        ACTION_STATE['signal_attempted']=True
        P.send_signal(pidfd,signal.SIGTERM,0)  # One pidfd signal, no escalation/retry.
        ACTION_STATE['signal_returned']=True
        events=poll.poll(30000)
        require(any(fd==pidfd and event&select.POLLIN for fd,event in events),'bounded exact pidfd terminal observation UNKNOWN')
        ACTION_STATE['pidfd_terminal_observed']=True
        after_scope=scoped_snapshot(C,physical,development,a)
        result={'status':'CURRENT_FAILED_PROVIDER_PIDFD_TERMINAL_ORIGINAL81012_B_AND_SEPARATE_C_PENDING','provider_pid':1930708,'birth':'58283682','signal':int(signal.SIGTERM),'pidfd_terminal_observed':True,'original_tool_session':81012,'original_sudo_direct_wait_or_streams_proven':False,'scope_before':scope_before,'scope_after':after_scope,'before_private_ref':before_ref,'action_state':dict(ACTION_STATE),'runtime_flags_changed':False,'FLOCK_acquired':False,'original_supervisor_waitpid_called':False,'native_or_runtime_or_resource_release':False}
        after_ref=persist(C,'A','AFTER',result)
        C.drain(C.OWNED);require(not C.RAW_CLOSE_ERRORS and all(row['state']=='CLOSED' for row in C.OWNED),'new actor own handle closure unknown')
        result.update(after_private_ref=after_ref,all_new_actor_own_FDs_closed=True,new_actor_close_errors=0,remaining_new_actor_direct_children=Path('/proc/self/task/%d/children'%os.getpid()).read_text().split())
        require(not result['remaining_new_actor_direct_children'],'new actor direct child custody unknown')
        return result
    except BaseException as error:
        RAW_ERRORS.append(('action-state',dict(ACTION_STATE)))
        unknown(C,'A',error,error.__traceback__)

def main():
    if len(sys.argv)!=8:raise PermissionError('EXECUTION_DISABLED: exact current phaseA request/review/fresh Root admission UNISSUED')
    phase,request,request_sha,review,review_sha,admission,admission_sha=sys.argv[1:]
    require(phase=='A','only current failed-provider A; B original Root wait; C separately unissued')
    q,a=authorize(request,request_sha,review,review_sha,admission,admission_sha)
    result=phase_A(q,a);print(json.dumps(result,sort_keys=True),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
