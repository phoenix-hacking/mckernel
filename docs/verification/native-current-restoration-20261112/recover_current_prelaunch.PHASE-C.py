import base64,datetime,fcntl,hashlib,json,os,pathlib,resource,select,signal,stat,struct,sys,time,traceback,types
M=pathlib.Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
BASE=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current-prelaunch-recovery-1/phase-C-current-1')
CONDITIONS=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current-prelaunch-recovery-1/phase-A-current-1/CURRENT-CUSTODY-BINDING.DATA.json')
CONDITIONS_SHA='4c90feab9524ea3ae0b12659ecf12f58ea4026be8ba690d216398d75088df9e7'
Q=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-custody-independent-review-1/actual-qualification-1/QUALIFICATION.json')
Q_SHA='32194c2208251272714f920fa28e18497d248d22c612e1f71a29b4c5847b5912'
AUTH=M/'native-graph-fixed30-adoption-review-sourceacq-max-1/AUTHORITY-SCOPE-ADDENDUM.json'
AUTH_SHA='c319433c4d2c7081fb95b8fa325c83d7837fcd88189920e92a8f7b0f6f8d2c5e'
AUTH_ID='source-c05f2a92e95fa56ced99c2be6f74a9920a0cf9a07ac6cf9c03dffeb37c4d0be5'
COLLECTOR=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-review-1/current-provider-custody-read-1/collect_current_owner.READONLY.py')
COLLECTOR_SHA='116fa8a55c20c6078919f9623ea7d9b819dc30af86041ef8a799d414710eae7e'
PIDFD=pathlib.Path('/var/lib/mckernel-code-342d20ce74ad38c41aaaef6aa1fc31d8c49638d02bfbca1e841ac267b510c5ba/installed-source-342d20ce74ad38c41aaaef6aa1fc31d8c49638d02bfbca1e841ac267b510c5ba/pidfd_compat.py')
PIDFD_SHA='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
INPLACE=PIDFD.parent/'inplace_custody.py'
INPLACE_SHA='70307b730512cb56c3f63738fe9fc8c14a1603bb6ec4227e05db3ab36115890e'
RAW_ERRORS=[]
OWN_PIDFDS=[]

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

def authorize(phase,request,request_sha,review,review_sha,admission,admission_sha):
    # Default invocation has no action. Only the owning Root's exact reviewed
    # normal operation path supplies these real source/review/fresh-admission refs.
    require(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={0},'admitted Root/CPU0 only')
    q=json.loads(bound(request,request_sha),object_pairs_hook=unique)
    go=json.loads(bound(review,review_sha),object_pairs_hook=unique)
    a=json.loads(bound(admission,admission_sha),object_pairs_hook=unique)
    require(q['phase']==phase and go['decision'].startswith('GO'),'exact phase operation GO required')
    require(a['request_sha256']==request_sha and a['review_sha256']==review_sha and a['phase']==phase,'exact new phase admission')
    require(a['invocation']=='20261112T094452Z-12a4bea0' and a['same_Root_finite_credit_run_id']=='7c6ef3604bfb4008a917bba8cfb6cfaa','same Root/invocation/finite run')
    require(a['existing_9032_current_owner_account_result']=='ACCEPTED','actual current account/service owner accepted')
    require(a['standing_authority_instruction_source']==AUTH_ID and q['standing_authority_instruction_source']==AUTH_ID,'exact authenticated standing authority scope')
    require(a['authority_scope_receipt_sha256']==AUTH_SHA,'actual authority interpretation receipt')
    bound(AUTH,AUTH_SHA);bound(Q,Q_SHA);conditions=json.loads(bound(CONDITIONS,CONDITIONS_SHA),object_pairs_hook=unique)
    require(same_boot(conditions['actual_binding']['boot_id']),'same actual boot')
    age=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp();require(0<=age<=25,'fresh phase admission')
    require(type(a['current_HOST_jobs_before']) is int and 0<=a['current_HOST_jobs_before']<3,'shared job limit')
    require(a['current_owned_controller_worker_overhead_bytes']+a['other_current_HOST_payload_reserved_bytes']+q['family_planning_bytes']<=4*2**30,'shared total includes all held work')
    require(a['MemAvailable_bytes']>=26*2**30,'fresh available floor')
    require(resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608),'exact new Root helper profile')
    return q,conditions['actual_binding']

def read_claim(C,claim):
    # Root-private raw data is read only inside this later admitted Root actor;
    # no private input digest is invented or emitted to ordinary stdout.
    private=claim['Root_private_record_reference'];directory=C.own(C.open_exact(str(pathlib.Path(private['path']).parent)),'recovery:private-record-parent');C.root_private(directory['fd'])
    row=C.own(C.open_exact(private['path']),'recovery:private-owner-record');st,raw=C.read_owned(row,1024*1024)
    require(C.identity(st)==private['identity'] and sha(raw)==private['sha256'] and len(raw)==private['bytes'],'exact actual private record identity/bytes')
    data=json.loads(raw,object_pairs_hook=unique);j=claim['journal'];journal=C.own(C.open_exact(j['path']),'recovery:original-prior-journal');js,jraw=C.read_owned(journal,4096)
    require(C.identity(js)==j['identity'] and sha(jraw)==j['sha256'],'exact actual original journal inode/hash')
    original=base64.b64decode(data['journal']['raw_base64'],validate=True)
    require(jraw==original and data['journal']['sha256']==j['sha256'],'saved actual journal bytes')
    rows=[json.loads(x,object_pairs_hook=unique) for x in jraw.splitlines()]
    require(len(rows)==2 and rows[0]==j['first_prior_row'] and rows==data['journal']['rows'],'actual first row plus HELD record')
    held=rows[1];require(held['status']=='RUNTIME_HELD' and held['pid']==1837769 and held['birth']=='56509608' and held['native_permission_from_provider'] is False,'exact original HELD owner')
    require(held['actualRoot_input_sha256']==data['Root_input']['sha256'],'real private input digest bound, no caller digest')
    require(sha(base64.b64decode(data['Root_input']['raw_base64'],validate=True))==data['Root_input']['sha256'],'private Root input bytes')
    require(rows[0]=={'path':'/usr/bin/python3.8','device':66306,'inode':1048651,'old_flags':524288},'only exact operation-owned old I claim')
    return rows[0],held,journal

def runtime_check(C,row,expected_flags):
    st=os.fstat(row['fd']);require((st.st_dev,st.st_ino,st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),st.st_nlink,st.st_size)==(66306,1048651,0,0,0o755,1,5490456),'same canonical runtime inode')
    h=hashlib.sha256();pos=0
    while pos<st.st_size:
        chunk=os.pread(row['fd'],min(1024*1024,st.st_size-pos),pos);require(bool(chunk),'complete runtime read');h.update(chunk);pos+=len(chunk)
    require(h.hexdigest()=='298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06' and C.flags(row['fd'])==expected_flags,'exact runtime bytes and flag CAS')
    named=os.stat('/usr/bin/python3.8',follow_symlinks=False);require(C.stable(st)==C.stable(named),'runtime pathname same inode')
    return st

def own_lock_key(fd):
    st=os.fstat(fd);matches=[]
    for line in pathlib.Path('/proc/locks').read_text().splitlines():
        f=line.split()
        if len(f)<8 or f[1:4]!=['FLOCK','ADVISORY','WRITE']:continue
        major,minor,inode=f[5].split(':')
        if (int(f[4]),int(major,16),int(minor,16),int(inode))==(os.getpid(),os.major(st.st_dev),os.minor(st.st_dev),st.st_ino):matches.append([os.getpid(),int(major,16),int(minor,16),int(inode),f[6],f[7]])
    require(len(matches)==1 and matches[0][-2:]==['0','EOF'] and os.getpid()!=1837769,'real NEW cleanup actor exclusive whole runtime FLOCK')
    return matches[0]

def persist(C,phase,label,value):
    birth=pathlib.Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()[19]
    C.RAW_OUTPUT=str(BASE/('Root-'+phase+'-'+str(os.getpid())+'-'+birth+'-'+label))
    return C.persist_raw(value)
def unknown(C,phase,error,tb):
    RAW_ERRORS.append((phase,error,tb))
    try:persist(C,phase,'UNKNOWN',{'status':'CURRENT_RECOVERY_UNKNOWN_RETAINED','phase':phase,'error_type':type(error).__name__,'traceback':''.join(traceback.format_exception(type(error),error,tb)),'native_and_historical_release':False})
    except BaseException as secondary:RAW_ERRORS.append(('report',secondary,secondary.__traceback__))
    # Existing foreground-retained-custody pattern, never a daemon/replacement.
    # Preserve actual owned pidfds/runtime FLOCK and raw errors for Root review.
    while True:
        try:signal.pause()
        except BaseException as secondary:RAW_ERRORS.append(('hold-interruption',secondary,secondary.__traceback__))

def phase_A(q,claim):
    C=load_module(COLLECTOR,COLLECTOR_SHA,'reviewed_read_collection');P=load_module(PIDFD,PIDFD_SHA,'registered_pidfd_compat');pidfd=None
    try:
        prior,held,journal=read_claim(C,claim);raw={};fresh=C.collect(raw)
        require(fresh['journal']['sha256']==claim['journal']['sha256'] and fresh['original_FD_bindings']==claim['held_FDs'],'fresh exact current journal/FD/FLOCK scope')
        C.drain(C.OWNED);require(not C.RAW_CLOSE_ERRORS,'own read closes before disposition')
        try:pidfd=P.open_pidfd(1837769,0)
        except P.PidfdVerificationError as error:
            OWN_PIDFDS.append({'fd':error.fd,'state':'VERIFICATION_UNKNOWN'});raise
        own={'fd':pidfd,'state':'HELD'};OWN_PIDFDS.append(own)
        require(C.proc(1837769,'56509608')['ppid']==1837766 and C.proc(1837766,'56509602')['uid']==[0,0,0,0],'same target after pidfd pin')
        require(not pathlib.Path('/proc/1837769/task/1837769/children').read_text().split(),'exact original target has no native children')
        status=pathlib.Path('/proc/1837769/status').read_text();mask=1<<(int(signal.SIGTERM)-1)
        caught=int(next(x.split()[1] for x in status.splitlines() if x.startswith('SigCgt:')),16);ignored=int(next(x.split()[1] for x in status.splitlines() if x.startswith('SigIgn:')),16)
        require(not (caught|ignored)&mask,'normal SIGTERM disposition not inferred from process S')
        poll=select.poll();poll.register(pidfd,select.POLLIN);require(not poll.poll(0),'original target already terminal, no signal sent')
        persist(C,'A','BEFORE',{'status':'EXACT_PROVIDER_DISPOSITION_PREPARED','provider_pid':1837769,'birth':'56509608','signal':int(signal.SIGTERM),'original_tool':73649,'prior_row':prior,'fresh_record':fresh,'native_launch':False,'authority_instruction':AUTH_ID})
        P.send_signal(pidfd,signal.SIGTERM,0)  # Sole normal signal, no escalation.
        events=poll.poll(30000);require(any(fd==pidfd and event&select.POLLIN for fd,event in events),'bounded pidfd terminal observation unknown')
        result={'status':'PRELAUNCH_PROVIDER_PIDFD_TERMINAL_ORIGINAL_JOINS_PENDING','provider_pid':1837769,'birth':'56509608','signal':int(signal.SIGTERM),'pidfd_terminal_observed':True,'original_tool_session':73649,'original_sudo_direct_wait_or_streams_proven':False,'runtime_flags_changed':False,'FLOCK_acquired':False,'native_or_runtime_or_resource_release':False}
        persist(C,'A','AFTER',result);fd=own.pop('fd');own['state']='CLOSE_ATTEMPTED_UNKNOWN';os.close(fd);own['state']='CLOSED';return result
    except BaseException as error:unknown(C,'A',error,error.__traceback__)

# Pure DATA validation of genuine future raw captures. It returns no token,
# NativeParentRetirement, RootLease, caller grant or executable permission.
def validate_original_join_data(initial,final,clients,outcome):
    require(initial.get('session_id')==73649,'actual ORIGINAL tool session')
    require('session_id' not in final and type(final.get('exit_code')) is int and final['exit_code']!=0,'actual original terminal preserves failure')
    require(len(clients)==1,'one original direct Popen');row=clients[0]
    require(row['pid']==1837766 and row['birth']=='56509602' and row['label']=='native-runtime-provider','actual original sudo Popen')
    require(row.get('late_original_direct_wait_joined') is True and type(row.get('late_original_exit')) is int and row['late_original_exit']!=0 and row['streams_closed'] is True,'original owning keeper late wait/streams')
    require(outcome['status']=='FAILED_OR_UNKNOWN_PROVIDER_PRESERVED_PENDING_OWNING_ROOT_DISPOSITION' and outcome['remaining_original_direct_children']==[] and outcome['provider_report_matches_exit'] is False and outcome['native_or_runtime_or_source_or_historical_release_from_outer'] is False and outcome['application_acceptance'] is False,'genuine original prelaunch failed outcome, no restoration report')
    require(outcome['clients']==clients,'original result/capture join')

def phase_C(q,claim):
    C=load_module(COLLECTOR,COLLECTOR_SHA,'reviewed_read_collection')
    try:
        actual_A=refs_json(q['actual_phaseA_result_ref'])
        require(actual_A['status']=='PRELAUNCH_PROVIDER_PIDFD_TERMINAL_ORIGINAL_JOINS_PENDING' and actual_A['provider_pid']==1837769 and actual_A['birth']=='56509608' and actual_A['signal']==int(signal.SIGTERM) and actual_A['pidfd_terminal_observed'] is True and actual_A['original_tool_session']==73649,'genuine separately qualified phase-A pidfd result')
        # These SHA/size references MUST be the real future phase-B outputs;
        # phase-A request has none and cannot select or authorize phase C.
        joins=q['actual_original_join_refs'];data={name:refs_json(value) for name,value in joins.items()}
        require(set(data)=={'initial_tool','final_tool','original_clients','original_result'},'exact real original join captures')
        validate_original_join_data(data['initial_tool'],data['final_tool'],data['original_clients'],data['original_result'])
        prior,held,journal=read_claim(C,claim)
        runtime=C.own(C.open_exact('/usr/bin/python3.8'),'recovery:NEW-runtime-FLOCK');runtime_check(C,runtime,524304)
        require(os.getpid()!=1837769,'new real cleanup actor, no old PID impersonation')
        fcntl.flock(runtime['fd'],fcntl.LOCK_EX|fcntl.LOCK_NB);lock=own_lock_key(runtime['fd']);runtime_check(C,runtime,524304)
        _js,locked_journal=C.read_owned(journal,4096)
        require(sha(locked_journal)==claim['journal']['sha256'] and C.identity(_js)==claim['journal']['identity'],'same exact journal while NEW runtime lock held')
        cap=int(next(x.split()[1] for x in pathlib.Path('/proc/self/status').read_text().splitlines() if x.startswith('CapEff:')),16);require(cap&(1<<9),'actual Linux immutable capability')
        # Exact same-inode/current-flags CAS, never generic/historical flag clear.
        require(prior['old_flags']==524288 and C.flags(runtime['fd'])==prior['old_flags']|0x10,'only old|I operation-owned bit')
        persist(C,'C','BEFORE',{'status':'PRELAUNCH_FAILED_EXACT_RUNTIME_RESTORE_PREPARED','actual_original_joins':joins,'old_prior_row':prior,'actual_new_FLOCK':lock,'current_flags':524304,'restore_flags':524288,'authority_instruction':AUTH_ID,'native_retirement_object':None})
        constants={}
        import ast
        for node in ast.parse(bound(INPLACE,INPLACE_SHA)).body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='SETFLAGS':constants['SETFLAGS']=ast.literal_eval(node.value)
        require(set(constants)=={'SETFLAGS'},'genuine inplace SETFLAGS constant')
        fcntl.ioctl(runtime['fd'],constants['SETFLAGS'],struct.pack('I',prior['old_flags']))
        runtime_check(C,runtime,524288);own_lock_key(runtime['fd'])
        require(os.pread(journal['fd'],587,0)==locked_journal,'original prior journal unchanged after restoration')
        result={'status':'PRELAUNCH_FAILED_RUNTIME_PRIOR_FLAGS_RESTORED_CURRENT_ONLY','runtime':'/usr/bin/python3.8','device':66306,'inode':1048651,'restored_flags':524288,'actual_cleanup_pid':os.getpid(),'actual_new_FLOCK':lock,'original_failure_preserved':True,'NativeParentRetirement_created':False,'native12_historical_source_or_global_release':False}
        persist(C,'C','RESTORED',result)
        C.drain([row for row in C.OWNED if row is not runtime]);require(not C.RAW_CLOSE_ERRORS,'all new non-runtime closes positive before last runtime close')
        C.drain([runtime]);require(not C.RAW_CLOSE_ERRORS and all(row['state']=='CLOSED' for row in C.OWNED),'runtime/FLOCK own close last, once')
        result['all_new_own_FDs_closed_runtime_last']=True;return result
    except BaseException as error:unknown(C,'C',error,error.__traceback__)

def main():
    # Source is inert without this exact reviewed/just-admitted operation chain.
    # No --force/authority-true/retry/replacement/native admission switch exists.
    if len(sys.argv)!=8:raise PermissionError('EXECUTION_DISABLED: exact phase/request/review/fresh Root admission are unissued')
    phase,request,request_sha,review,review_sha,admission,admission_sha=sys.argv[1:]
    require(phase in ('A','C'),'only separately admitted A or C; B is original owning tool join')
    q,claim=authorize(phase,request,request_sha,review,review_sha,admission,admission_sha)
    result=phase_A(q,claim) if phase=='A' else phase_C(q,claim)
    print(json.dumps(result,sort_keys=True),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
