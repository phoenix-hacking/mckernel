import ast,base64,datetime,fcntl,hashlib,json,os,pathlib,resource,signal,stat,struct,sys,time,traceback,types
BASE=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-failed-recovery-1/phase-C-current-1')
TARGET={'boot_id': '3ba4f2ca-4323-433d-bfb8-7859268121b6', 'finite_credit_run': '7c6ef3604bfb4008a917bba8cfb6cfaa', 'held_expected_flags': 524304, 'invocation': '20261112T094452Z-12a4bea0', 'nonce_context_only_not_reissue': '8d1833a8a7552f40403c045abe0107e6e8118c49bc39c79bc4830f3a4bb3031f', 'operation_root': '/var/lib/mckernel-native-signal-8d1833a8a7552f40403c045abe0107e6e8118c49bc39c79bc4830f3a4bb3031f', 'original_HOST_bytes_retained': 1610612736, 'original_HOST_jobs_retained': 1, 'original_Root_tool_session': 81012, 'prior_flags': 524288, 'provider_birth': '58283682', 'provider_pid': 1930708, 'runtime_bytes': 5490456, 'runtime_device': 66306, 'runtime_inode': 1048651, 'runtime_path': '/usr/bin/python3.8', 'runtime_sha256': '298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06', 'saved_Root': '01a18bc3-e072-7810-9426-75101b0856c0', 'sudo_birth': '58283676', 'sudo_pid': 1930695, 'supervisor_birth': '58283729', 'supervisor_pid': 1930710}
COLLECTOR=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-custody-read-1/saved-native-result-projection-1/local-stable-binding-correction-1/project_saved_native.READONLY.PROPOSED.py')
COLLECTOR_SHA='4c738a52c33afda062865dd5da897de34d5a51bcf52752ae24c81acddc0f0520'
A_SOURCE=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/current81012-failed-recovery-1/configured-lock-absence-correction-1/recover_current_failed_provider.PROPOSED.py')
A_SOURCE_SHA='611b7b03b85304bf4738f5675b92e629ef7a24a9c00bae6c5401776763e4f1ea'
INPLACE=pathlib.Path('/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/nsfs-normal-fixed30-1/candidate/package/inplace_custody.py')
INPLACE_SHA='70307b730512cb56c3f63738fe9fc8c14a1603bb6ec4227e05db3ab36115890e'
PERSISTENT=[{'actual_wait_or_release_authority': False, 'contents': 'PRIVATE_NOT_PROJECTED', 'identity': {'bytes': 22917, 'ctime_ns': 1794496571075529231, 'device': 66306, 'gid': 0, 'inode': 53525073, 'mode': 384, 'mtime_ns': 1794496571071529107, 'nlink': 1, 'uid': 0}, 'name': 'source-manifest.json', 'observation': 'COMPLETE_READONLY_SNAPSHOT', 'sha256': 'd20e93337b6b14ab68345fc38e5eee09e3b81db399884772a6bffeb9abb1e5c7'}, {'actual_wait_or_release_authority': False, 'contents': 'PRIVATE_NOT_PROJECTED', 'identity': {'bytes': 2424, 'ctime_ns': 1794496571079529355, 'device': 66306, 'gid': 0, 'inode': 53525074, 'mode': 384, 'mtime_ns': 1794496571075529231, 'nlink': 1, 'uid': 0}, 'name': 'native-operation.json', 'observation': 'COMPLETE_READONLY_SNAPSHOT', 'sha256': 'cf10e68970ff286c7a14f59d968b944eeb5e71db0eef9a28d9f86e018aaaea2a'}, {'actual_wait_or_release_authority': False, 'contents': 'PRIVATE_NOT_PROJECTED', 'identity': {'bytes': 8578, 'ctime_ns': 1794496571079529355, 'device': 66306, 'gid': 0, 'inode': 53525075, 'mode': 384, 'mtime_ns': 1794496571079529355, 'nlink': 1, 'uid': 0}, 'name': 'registered-loader.json', 'observation': 'COMPLETE_READONLY_SNAPSHOT', 'sha256': 'ed2c91636cb8557fcab87add1993570116fa9dfa5e4a81cd9a528413b72fa1ad'}]
PACKAGE={'device': 66306, 'inode': 53525031, 'mode': 493, 'path': '/var/lib/mckernel-code-1f5f59d76bfeb43ce0f738ee07d7148fc5f7a69498273f0be498efcb4ea30cfd/installed-source-1f5f59d76bfeb43ce0f738ee07d7148fc5f7a69498273f0be498efcb4ea30cfd', 'uid': 0}
RAW_ERRORS=[]
ACTION_STATE={"new_exclusive_runtime_FLOCK":False,"CAS_attempted":False,"CAS_returned":False,"restored_flags_observed":False}
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
    require(len(matches)==1 and matches[0][-2:]==['0','EOF'] and os.getpid()!=1930708,'real NEW cleanup actor exclusive whole runtime FLOCK')
    return matches[0]

ADMISSION_KEYS={'schema','at','issued_monotonic_ns','saved_Root','invocation','same_Root_finite_credit_run_id','request_sha256','review_sha256','phase','action_scope','actual_current_account_result','actual_current_account_ref','actual_source_permission_resource_ref','complete_parent_actor_profile','new_current_family_bytes','new_current_jobs','current_HOST_jobs_before','current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes','host_boot_id','development_lock_identity','actual_AB_qualification_sha256','runtime_C_refinement_sha256','runtime_path','runtime_device','runtime_inode','expected_current_flags','restore_prior_flags','native12_source_global_partialUNKNOWNs_retained','persistent_control_package_I_unchanged','original_1_5GiB_held_until_actual_C_fullfamily_Q_Root_retirement'}

def fresh_admission(a):
    age=time.time()-datetime.datetime.fromisoformat(a['at']).timestamp()
    require(0<=age<=25,'fresh actual runtimeC UTC admission')
    require(type(a['issued_monotonic_ns']) is int and 0<=time.monotonic_ns()-a['issued_monotonic_ns']<=25*10**9,'fresh actual runtimeC monotonic admission')

def authorize(request,request_sha,review,review_sha,admission,admission_sha):
    require(os.getuid()==os.geteuid()==0 and os.sched_getaffinity(0)=={0},'admitted runtimeC Root CPU0 only')
    q=json.loads(bound(request,request_sha),object_pairs_hook=unique);go=json.loads(bound(review,review_sha),object_pairs_hook=unique);a=json.loads(bound(admission,admission_sha),object_pairs_hook=unique)
    require(set(a)==ADMISSION_KEYS,'complete exact parent and runtimeC actor admission union')
    require(q['phase']=='C' and go['decision'].startswith('GO') and go['request']['sha256']==request_sha,'exact separately reviewed runtimeC request')
    require(a['schema']=='mckernel.Root-current81012-temporary-runtime-only-phaseC-admission.v1' and a['phase']=='C' and a['request_sha256']==request_sha and a['review_sha256']==review_sha,'exact new runtimeC admission')
    require(a['saved_Root']==TARGET['saved_Root'] and a['invocation']==TARGET['invocation'] and a['same_Root_finite_credit_run_id']==TARGET['finite_credit_run'] and a['host_boot_id']==TARGET['boot_id'] and same_boot(TARGET['boot_id']),'same Root invocation finite run and boot')
    require(a['action_scope']=='EXACT_TEMP_RUNTIME1048651_FLAGS524304_TO524288_ONCE_ONLY' and (a['runtime_path'],a['runtime_device'],a['runtime_inode'],a['expected_current_flags'],a['restore_prior_flags'])==('/usr/bin/python3.8',66306,1048651,524304,524288),'only exact original temporary-runtime CAS scope')
    require(a['actual_current_account_result']=='ACCEPTED','fresh actual fe2/current7f8 currentowner/account/service result')
    for key in ('actual_current_account_ref','actual_source_permission_resource_ref'):
        ref=a[key];raw=bound(ref['path'],ref['sha256']);require(len(raw)==ref['bytes'],'actual new receipt bytes')
    require(a['actual_AB_qualification_sha256']==q['actual_AB_qualification']['sha256'] and a['runtime_C_refinement_sha256']==q['runtime_only_C_refinement']['sha256'],'actual new A+B and scoped runtimeC refinement')
    refs_json(q['actual_AB_qualification']);refs_json(q['runtime_only_C_refinement']);refs_json(q['actual_A_only_Root_retirement'])
    require(a['complete_parent_actor_profile']==q['profile'] and a['new_current_family_bytes']==268435456 and a['new_current_jobs']==1,'complete actual runtimeC family profile')
    require(type(a['current_HOST_jobs_before']) is int and 0<=a['current_HOST_jobs_before']<3,'all-current jobs count')
    for key in ('current_HOST_payload_reserved_bytes_before','controller_worker_overhead_bytes','MemAvailable_bytes','host_free_bytes','scratch_free_bytes'):require(type(a[key]) is int and a[key]>=0,'actual nonnegative resources')
    require(a['current_HOST_payload_reserved_bytes_before']>=1610612736 and a['current_HOST_payload_reserved_bytes_before']+a['controller_worker_overhead_bytes']+268435456<=4*2**30,'all original and current payload/overhead plus newC fit4GiB')
    require(a['MemAvailable_bytes']>=26*2**30 and a['host_free_bytes']>=16*2**30+67108864 and a['scratch_free_bytes']>=12*2**30+67108864,'fresh available/capture floors')
    require(a['native12_source_global_partialUNKNOWNs_retained'] is True and a['persistent_control_package_I_unchanged'] is True and a['original_1_5GiB_held_until_actual_C_fullfamily_Q_Root_retirement'] is True,'original and unrelated holds remain')
    require(resource.getrlimit(resource.RLIMIT_AS)==(134217728,134217728) and resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608),'exact Root runtimeC actor limits')
    fresh_admission(a);return q,a

def verify_actual_AB(q,C):
    qualified=refs_json(q['actual_AB_qualification'])
    require(qualified['decision']=='QUALIFIED_CURRENT81012_A_NEW_ACTOR_AND_FAILED_ORIGINAL_B_JOINS_SEPARATE_SCOPES','actual current81012 A+B qualification')
    data=refs_json(q['actual_A_B_handoff']);A=refs_json(data['actual_phase_A']);B=refs_json(data['actual_original_B'])
    require(A['status']=='CURRENT_FAILED_PROVIDER_PIDFD_TERMINAL_ORIGINAL81012_B_AND_SEPARATE_C_PENDING' and A['provider_pid']==1930708 and A['birth']=='58283682' and A['pidfd_terminal_observed'] is True and A['signal']==15 and A['original_tool_session']==81012 and A['all_new_actor_own_FDs_closed'] is True,'actual exact separately qualified A')
    require(B['schema']=='mckernel.Root-current81012-original-PhaseB-owning-route-failed-joins.v1' and B['original_tool_session']==81012 and B['original_Root_exit_code']==1 and B['native_application_success'] is False and B['no_original_supervisor_second_wait_or_raw_status_inference'] is True,'genuine original failed owning route')
    row=B['original_client_metadata'];require(row['pid']==1930695 and row['birth']=='58283676' and row['late_original_direct_wait_joined'] is True and row['late_original_exit']==-15 and row['streams_closed'] is True and B['secondary_error_count']==1,'actual original sudo late wait and streams with original failure preserved')
    for key in ('actual_original_tool_terminal','original_clients','original_late_wait'):refs_json(data[key])
    for capture in B['captures']:
        st=os.stat(capture['path'],follow_symlinks=False);require((st.st_dev,st.st_ino,st.st_uid,st.st_gid,stat.S_IMODE(st.st_mode),st.st_nlink,st.st_size)==tuple(capture[k] for k in ('device','inode','uid','gid','mode','nlink','bytes')),'actual original closed capture identity')
        require(sha(C.read_path(capture['path'],4096))==capture['sha256'],'actual original complete closed capture bytes')
    return {'A_ref':data['actual_phase_A'],'B_ref':data['actual_original_B'],'actual_AB_qualification':q['actual_AB_qualification'],'original_failed_UNKNOWN_and_timeout_preserved':True}

def ended_roles(C):
    result=[]
    for pid,birth in ((1930708,'58283682'),(1930695,'58283676'),(1930710,'58283729')):
        try:raw=C.read_path('/proc/%d/stat'%pid,8192)
        except FileNotFoundError:result.append({'pid':pid,'expected_birth':birth,'observation':'ABSENT_CORROBORATES_ACTUAL_ORIGINAL_JOINS_ONLY'});continue
        fields=raw.rsplit(b')',1)[1].split();require(len(fields)>=20,'bounded exact role stat')
        actual=fields[19].decode();require(actual!=birth,'exact original role still present; no runtime restoration')
        result.append({'pid':pid,'expected_birth':birth,'observed_birth':actual,'observation':'REUSED_OUT_OF_SCOPE_NO_ACTION'})
    return result

def read_claim(C,claim):
    private=claim['Root_private_record_reference'];parent=C.own(C.open_exact(str(pathlib.Path(private['path']).parent)),'runtimeC:saved-private-parent');C.root_private(parent['fd'])
    original=C.own(C.open_exact(private['path']),'runtimeC:exact-saved-private-record');st,raw=C.read_owned(original,1024*1024)
    require(C.identity(st)==private['identity'] and len(raw)==private['bytes'] and sha(raw)==private['sha256'],'exact original protected source identity/hash')
    data=json.loads(raw,object_pairs_hook=unique);j=claim['journal'];journal=C.own(C.open_exact(j['path']),'runtimeC:original-prior-journal');js,jraw=C.read_owned(journal,4096)
    require(C.identity(js)==j['identity'] and sha(jraw)==j['sha256'] and len(jraw)==586,'exact current journal586 inode53525069/hash4910')
    require(jraw==base64.b64decode(data['journal']['raw_base64'],validate=True) and data['journal']['sha256']==j['sha256'],'exact private saved journal bytes')
    rows=[json.loads(line,object_pairs_hook=unique) for line in jraw.splitlines()]
    require(len(rows)==2 and rows==data['journal']['rows'] and rows[0]==j['first_prior_row'],'actual exact first prior row and sole held row')
    held=rows[1];require(held['status']=='RUNTIME_HELD' and held['pid']==1930708 and held['birth']=='58283682' and held['native_driver_sha256']=='26f3c97014bdf8dc5a3337746c919b291f79be41d212e94771f9395cecff773e' and held['native_permission_from_provider'] is False,'actual original runtime holder/source binding')
    saved_input=base64.b64decode(data['Root_input']['raw_base64'],validate=True);input_sha=data['Root_input']['sha256']
    require(held['actualRoot_input_sha256']==input_sha and sha(saved_input)==input_sha,'actual original private four-key input bound by journal')
    live=C.own(C.open_exact(claim['actual_original_input_path']),'runtimeC:original-immutable-Root-input');ist,body=C.read_owned(live,65536)
    require(C.identity(ist)==data['Root_input']['identity'] and body==saved_input and sha(body)==input_sha and ist.st_uid==0 and ist.st_nlink==1 and C.flags(live['fd'])&0x10,'exact live immutable original Root input, never a new permission')
    actual=json.loads(body,object_pairs_hook=unique)
    require(set(actual)=={'kind','source_contract_sha256','caps','host_admission_ref'} and actual['kind']=='mckernel-native-signal-root-input-v1' and actual['source_contract_sha256']==claim['source_contract_sha256'],'genuine historical ownership/source input only')
    require(rows[0]=={'path':'/usr/bin/python3.8','device':66306,'inode':1048651,'old_flags':524288},'only exact originally journaled temporary I flag')
    return rows[0],journal,jraw,{'saved_private':private,'live_original_input_sha256':input_sha,'caps_historical_not_executed_or_grant':True}

def preserve_persistent(C):
    snapshots=[]
    for spec in PERSISTENT:
        path=TARGET['operation_root']+'/'+spec['name'];row=C.own(C.open_exact(path),'runtimeC:persistent-evidence:'+spec['name']);st,body=C.read_owned(row,65536)
        require(C.identity(st)==spec['identity'] and sha(body)==spec['sha256'] and st.st_uid==0 and st.st_nlink==1 and C.flags(row['fd'])&0x10,'persistent native evidence identity/hash/I must stay unchanged')
        snapshots.append((row,C.stable(st),C.flags(row['fd']),spec['sha256']))
    package=C.own(C.open_exact(PACKAGE['path']),'runtimeC:immutable-installed-package-directory-only');st=os.fstat(package['fd'])
    require(stat.S_ISDIR(st.st_mode) and {k:C.identity(st)[k] for k in ('device','inode','uid','mode')}=={k:PACKAGE[k] for k in ('device','inode','uid','mode')} and C.flags(package['fd'])&0x10,'exact immutable1f5 package directory, no inventory or mutation')
    return snapshots,(package,C.stable(st),C.flags(package['fd']))

def recheck_persistent(C,snapshots,package):
    for row,before,flags,digest in snapshots:
        st=os.fstat(row['fd']);require(C.stable(st)==before and C.flags(row['fd'])==flags and sha(os.pread(row['fd'],st.st_size+1,0))==digest,'persistent control evidence changed')
    row,before,flags=package;require(C.stable(os.fstat(row['fd']))==before and C.flags(row['fd'])==flags,'immutable package directory changed')

def physical_scope(A,C,physical,development,a):
    # A's exact scoped reader is reused, but C always invokes real positive
    # idle validation. It never promotes a missing development lock to proof.
    value=A.scoped_snapshot(C,lambda ignored:physical(True),development,a)
    lock=value['development_lock_observation']
    if lock['observation']=='PRESENT_ROOT_REGULAR_NLINK1':require(lock['matching_kernel_lock_rows']==[],'active configured development lock blocks runtimeC')
    else:require(lock['observation']=='ABSENT_UNPROVEN' and lock['identity'] is None and lock['matching_kernel_lock_rows'] is None,'absent configured development lock remains unresolved DATA')
    return value

def phase_C(q,a):
    C=load_module(COLLECTOR,COLLECTOR_SHA,'reviewed_current81012_metadata_methods');A=load_module(A_SOURCE,A_SOURCE_SHA,'reviewed_current81012_configured_scope_methods')
    try:
        joins=verify_actual_AB(q,C);roles=ended_roles(C);claim=refs_json(q['original_runtime_claim'])
        prior,journal,original_journal,input_proof=read_claim(C,claim)
        observed=A.configured_lock_observation(a);development=None
        if observed['observation']=='PRESENT_ROOT_REGULAR_NLINK1':development=C.own(C.open_exact('/run/lock/mckernel-development.lock'),'runtimeC:development-lock-readonly-no-FLOCK')
        physical=A.native_physical_reader();scope_before=physical_scope(A,C,physical,development,a)
        snapshots,package=preserve_persistent(C)
        runtime=C.own(C.open_exact('/usr/bin/python3.8'),'runtimeC:NEW-exclusive-runtime-FLOCK');runtime_check(C,runtime,524304)
        fcntl.flock(runtime['fd'],fcntl.LOCK_EX|fcntl.LOCK_NB);ACTION_STATE['new_exclusive_runtime_FLOCK']=True;lock=own_lock_key(runtime['fd']);runtime_check(C,runtime,524304)
        js,locked_journal=C.read_owned(journal,4096);require(C.identity(js)==claim['journal']['identity'] and locked_journal==original_journal and sha(locked_journal)==claim['journal']['sha256'],'actual original journal unchanged under own exclusive runtime FLOCK')
        cap=int(next(line.split()[1] for line in pathlib.Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:')),16);require(cap&(1<<9),'actual current CAP_LINUX_IMMUTABLE required')
        require(prior['old_flags']==524288 and C.flags(runtime['fd'])==(prior['old_flags']|0x10),'only exact old|I current temporary flags')
        before={'status':'CURRENT81012_TEMPORARY_RUNTIME_ONLY_CAS_PREPARED','actual_joins':joins,'roles_after_actual_joins':roles,'original_prior_row':prior,'own_runtime_FLOCK':lock,'current_flags':524304,'restore_flags':524288,'scope_before':scope_before,'private_input_proof':input_proof,'all_native12_source_global_partialUNKNOWNs_retained':True,'persistent_control_package_I_untouched':True,'action_state':dict(ACTION_STATE)}
        before_ref=persist(C,'C','BEFORE',before)
        # All source reads/private writes/fsync may block. Revalidate every
        # current prerequisite plus both clocks before the ONE exact ioctl.
        fresh_admission(a);ended_roles(C);scope_preCAS=physical_scope(A,C,physical,development,a)
        recheck_persistent(C,snapshots,package);runtime_check(C,runtime,524304);own_lock_key(runtime['fd'])
        js,now_journal=C.read_owned(journal,4096);require(C.identity(js)==claim['journal']['identity'] and now_journal==original_journal,'exact journal identity/bytes at CAS boundary')
        cap=int(next(line.split()[1] for line in pathlib.Path('/proc/self/status').read_text().splitlines() if line.startswith('CapEff:')),16);require(cap&(1<<9),'actual immutable capability at CAS boundary')
        constants={}
        for node in ast.parse(bound(INPLACE,INPLACE_SHA)).body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id=='SETFLAGS':constants['SETFLAGS']=ast.literal_eval(node.value)
        require(set(constants)=={'SETFLAGS'},'genuine existing SETFLAGS source constant')
        require(C.flags(runtime['fd'])==524304 and prior['old_flags']==524288,'exact fresh runtime-only compare-and-set')
        fresh_admission(a);ACTION_STATE['CAS_attempted']=True
        fcntl.ioctl(runtime['fd'],constants['SETFLAGS'],struct.pack('I',prior['old_flags']))
        ACTION_STATE['CAS_returned']=True
        runtime_check(C,runtime,524288);own_lock_key(runtime['fd']);ACTION_STATE['restored_flags_observed']=True
        scope_after=physical_scope(A,C,physical,development,a);recheck_persistent(C,snapshots,package)
        require(os.pread(journal['fd'],587,0)==original_journal and C.identity(os.fstat(journal['fd']))==claim['journal']['identity'],'original prior journal unchanged after exact restoration')
        result={'status':'CURRENT81012_TEMPORARY_RUNTIME_PRIOR_FLAGS_RESTORED_ONLY','runtime':'/usr/bin/python3.8','device':66306,'inode':1048651,'runtime_sha256':TARGET['runtime_sha256'],'restored_flags':524288,'actual_cleanup_pid':os.getpid(),'own_runtime_FLOCK':lock,'scope_preCAS':scope_preCAS,'scope_after':scope_after,'before_private_ref':before_ref,'action_state':dict(ACTION_STATE),'original_failure_and_UNKNOWNs_preserved':True,'NativeParentRetirement_created':False,'supervisor_waitpid_or_signal_issued':False,'persistent_control_package_I_unchanged':True,'native12_source_global_partialUNKNOWN_release':False,'original1_5GiB_resource_retirement_from_actor':False}
        restored_ref=persist(C,'C','RESTORED',result)
        C.drain([row for row in C.OWNED if row is not runtime]);require(not C.RAW_CLOSE_ERRORS,'all own ancillary closes positive before runtime last')
        C.drain([runtime]);require(not C.RAW_CLOSE_ERRORS and all(row['state']=='CLOSED' for row in C.OWNED),'own runtime/FLOCK closes last once')
        remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();require(not remaining,'own new actor direct children remain')
        result.update(restored_private_ref=restored_ref,all_new_own_FDs_closed_runtime_last=True,new_actor_close_errors=0,remaining_new_actor_direct_children=remaining)
        return result
    except BaseException as error:unknown(C,'C',error,error.__traceback__)

def main():
    if len(sys.argv)!=8:raise PermissionError('EXECUTION_DISABLED: exact separate runtime-only C review and fresh actual Root admission UNISSUED')
    phase,request,request_sha,review,review_sha,admission,admission_sha=sys.argv[1:];require(phase=='C','runtime-only C, no A reissue or original wait')
    q,a=authorize(request,request_sha,review,review_sha,admission,admission_sha);value=phase_C(q,a);print(json.dumps(value,sort_keys=True),flush=True);return 0
if __name__=='__main__':raise SystemExit(main())
