"""Initial Root-owned immutable DATA publisher before the existing provider.
Source-only proposal; no account producer, daemon, controller or native grant.
"""
import datetime,hashlib,json,math,os,pathlib,resource,shutil,stat,sys,time,types
PROVIDER_SHA = '857d50e73baa704c990fcd2f6ea8814e7461ef337b39e5d28ff51742e6e4b049'
DRIVER_SHA = '26f3c97014bdf8dc5a3337746c919b291f79be41d212e94771f9395cecff773e'
PROVIDER_PATH = '/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/same_runtime_provider.PROPOSED.py'
DRIVER_PATH = '/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/normal_native_once.PROPOSED.py'
ACCOUNT_BYTES = b'"""Private source successor of the qualified account snapshot helper; no issuer entrypoint."""\nimport datetime\nimport hashlib\nimport importlib\nimport json\nimport math\nimport pathlib\nimport sys\nimport time\nfrom decimal import Decimal, InvalidOperation\nREPO = pathlib.Path(\'/home/holden/mckernel\')\nVALIDATOR_SHA256 = \'7f8b14f23c0d87ed2614d90a7cf4dcd5edf106419f7e0e48715aebd418da191d\'\n\ndef amount(value, *, positive=False):\n    if isinstance(value, bool) or not isinstance(value, (str, int, float)):\n        raise ValueError("Credit amount must be a finite number")\n    text = str(value)\n    if len(text) > 64:\n        raise ValueError("Credit amount is too long")\n    try:\n        number = Decimal(text)\n    except InvalidOperation as error:\n        raise ValueError("Invalid credit amount") from error\n    if not number.is_finite() or number < 0 or number > Decimal("1e12"):\n        raise ValueError("Credit amount is outside the supported range")\n    if positive and number == 0:\n        raise ValueError("Credit budget must be positive")\n    return number\n\ndef available_balance(limits):\n    if not isinstance(limits, dict) or not isinstance(limits.get("credits"), dict):\n        raise ValueError("Prepaid-credit balance is unknown")\n    credits = (limits or {}).get("credits") or {}\n    if credits.get("hasCredits") is not True or credits.get("unlimited") is not False:\n        raise ValueError("A finite available prepaid-credit balance is required")\n    balance = amount(credits.get("balance"))\n    if balance <= 0:\n        raise ValueError("Prepaid credits are exhausted")\n    if (limits or {}).get("spendControlReached"):\n        raise ValueError("Account spending control has been reached")\n    return balance\n\n\ndef _load_current_validator():\n    path = REPO / \'scripts/run_os_goal.py\'\n    assert hashlib.sha256(path.read_bytes()).hexdigest() == VALIDATOR_SHA256\n    scripts = str(REPO / \'scripts\')\n    # This is the normal canonical script namespace, never a private package.\n    if scripts not in sys.path:\n        sys.path.insert(0, scripts)\n    module = importlib.import_module(\'run_os_goal\')\n    assert pathlib.Path(module.__file__).resolve() == path.resolve()\n    return module.accepted_account_observation\n\n\ndef current_account_snapshot(expected_owner):\n    """Read a fresh durable poll/notification snapshot under independent owner pins.\n\n    expected_owner comes from the separately reviewed actual current Root admission;\n    it cannot be fabricated from a receipt or copied from an earlier invocation.\n    This helper performs no account request, controller write, nonce or issue.\n    """\n    assert type(expected_owner) is dict\n    credit_path = REPO / \'.git/os-autopilot/credit-runs/7c6ef3604bfb4008a917bba8cfb6cfaa.json\'\n    assert expected_owner[\'credit_run_id\'] == \'7c6ef3604bfb4008a917bba8cfb6cfaa\'\n    assert expected_owner[\'credit_ledger_path\'] == str(credit_path)\n    assert expected_owner[\'thread_id\'] == \'01a18bc3-e072-7810-9426-75101b0856c0\'\n    assert expected_owner[\'repo\'] == str(REPO)\n    assert expected_owner[\'boot_id\'] == pathlib.Path(\'/proc/sys/kernel/random/boot_id\').read_text().strip()\n    state_path = REPO / \'.git/os-autopilot/state.json\'\n    accept = _load_current_validator()\n    account_keys = (\'phase\', \'stop_reason\', \'weekly_usage_error\', \'weekly_confirmation_pending\',\n                    \'auth_mode\', \'credit_budget_error\', \'last_rate_limits\', \'credit_budget\',\n                    \'log_dir\', \'resume_instruction\', \'thread_id\', \'worker_pid\', \'worker_start\',\n                    \'server_pid\', \'server_start\', \'service_hold\', \'auth_hold\', \'billing_hold\',\n                    \'policy_hold\', \'goal\', \'repo\', \'guardian_run_id\', \'transport_failure\',\n                    \'last_account_observation\', \'last_account_notification\', \'successful_account_read\')\n\n    def checked_state():\n        value = json.loads(state_path.read_bytes())\n        assert value[\'phase\'] == \'running\' and value[\'stop_reason\'] is None\n        assert value[\'weekly_usage_error\'] is None and value[\'weekly_confirmation_pending\'] is False\n        assert value.get(\'auth_mode\') == \'chatgpt\' and value.get(\'credit_budget_error\') is None\n        assert not any(value.get(key) for key in (\'service_hold\', \'auth_hold\', \'billing_hold\', \'policy_hold\'))\n        for key in (\'log_dir\', \'thread_id\', \'worker_pid\', \'worker_start\', \'server_pid\',\n                    \'server_start\', \'repo\', \'guardian_run_id\'):\n            assert value.get(key) == expected_owner[key]\n        for kind in (\'worker\', \'server\'):\n            pid = expected_owner[kind + \'_pid\']\n            assert type(pid) is int and pid > 0\n            raw = pathlib.Path(\'/proc/%d/stat\' % pid).read_text()\n            fields = raw.rsplit(\')\', 1)[1].split()\n            assert fields[0] in (\'R\', \'S\', \'D\', \'T\', \'t\', \'W\', \'K\', \'P\', \'I\')\n            assert fields[19] == expected_owner[kind + \'_start\']\n        rate = value.get(\'last_rate_limits\')\n        assert type(rate) is dict and type(rate.get(\'primary\')) is dict\n        used = rate[\'primary\'].get(\'usedPercent\')\n        assert isinstance(used, (int, float)) and not isinstance(used, bool) and math.isfinite(used) and 0 <= used <= 100\n        assert rate[\'primary\'].get(\'windowDurationMins\') == 10080\n        assert rate.get(\'rateLimitReachedType\') is None\n        assert rate.get(\'spendControlReached\') is None or rate.get(\'spendControlReached\') is False\n        available_balance(rate)\n        saved = value[\'credit_budget\']\n        assert saved[\'id\'] == expected_owner[\'credit_run_id\']\n        assert amount(saved[\'budget\'], positive=True) == amount(expected_owner[\'credit_budget\'], positive=True)\n        assert amount(saved[\'remaining\'], positive=True) > 0\n        assert amount(saved[\'spent\']) < amount(saved[\'budget\'], positive=True)\n        amount(saved[\'last_balance\'], positive=True)\n        return value\n\n    last_mismatch = None\n    for attempt in range(3):\n        before = checked_state()\n        credit = json.loads(credit_path.read_bytes())\n        assert credit[\'id\'] == expected_owner[\'credit_run_id\']\n        assert amount(credit[\'budget\'], positive=True) == amount(expected_owner[\'credit_budget\'], positive=True)\n        assert amount(credit[\'remaining\'], positive=True) > 0\n        assert amount(credit[\'spent\']) < amount(credit[\'budget\'], positive=True)\n        # The original controller is the observation producer; no event is synthesized.\n        after = checked_state()\n        same_snapshot = all(before.get(key) == after.get(key) for key in account_keys)\n        if same_snapshot and credit == after[\'credit_budget\']:\n            accepted = accept(after, credit, expected_owner, time.time_ns(), time.monotonic_ns(), 25)\n            # Both controller bookends and the real ledger are coherent before\n            # validating freshness; transient mismatches consume bounded attempts.\n            rate = after[\'last_rate_limits\']\n            assert available_balance(rate) == amount(credit[\'last_balance\'], positive=True)\n            observed = accepted[\'received_utc_ns\'] / 1000000000\n            usage = {\'at\': datetime.datetime.fromtimestamp(observed, datetime.timezone.utc).isoformat(),\n                     \'source_event\': accepted[\'method\'], \'source_kind\': accepted[\'source\'],\n                     \'primary\': rate[\'primary\'], \'rateLimitReachedType\': rate.get(\'rateLimitReachedType\'),\n                     \'spendControlReached\': rate.get(\'spendControlReached\'),\n                     \'receipt_received_utc_ns\': accepted[\'received_utc_ns\'],\n                     \'receipt_received_mono_ns\': accepted[\'received_mono_ns\']}\n            return after, usage, credit, observed\n        last_mismatch = {\'attempt\': attempt + 1, \'state_changed_fields\':\n                         [key for key in account_keys if before.get(key) != after.get(key)],\n                         \'same_credit_record\': credit == after[\'credit_budget\']}\n    raise AssertionError(\'fresh current-owner account snapshot did not stabilize: \' + json.dumps(last_mismatch, sort_keys=True))\n'
ACCOUNT_SHA = 'fe2c38a7d559e0066c45da9de0fd65b5597b61cebbd5249663c645cfe08c7fe6'
ACCOUNT_PATH = '/home/holden/mckernel-work/resume-20261112T094452Z-native-binding-1/current-root-owner-1/current_account_snapshot.PROPOSED.py'
EXPECTED_OWNER = {'path': '/home/holden/mckernel-work/resume-reconciliation-20261112T094452Z-12a4bea0/CURRENT-OWNER.PRIVATE.json', 'bytes': 706, 'sha256': 'a51ed92a2b11f7cb65d83189ee0eee80c13537d0c76f2b1b0351dc38293e09a1'}
INVOCATION = '20261112T094452Z-12a4bea0'
PUB=None; PUBLISHED=[]; PROVIDER_STARTED=False; PROVIDER_NAMESPACE=None

def need(ok,message):
    if not ok:raise ValueError(message)

TRANSPORT_DATA = {'path': '/home/holden/mckernel-work/resume-20261112T094452Z-native-first-repeat-1f5f-binding-1/REVIEWED-SOURCE-LITERALS.DATA.json', 'bytes': 149591, 'sha256': '1c732c2f19700217aed7c51077fb1a9896d9473498729434e6716c9cef5d28c9'}
TRANSPORT_RECORDS=[]
TRANSPORT_FAILURES=[]

def transport_pairs(pairs):
    result={}
    for key,value in pairs:
        need(key not in result,'duplicate source transport JSON key')
        result[key]=value
    return result


def transport_identity(st):
    return (st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid,st.st_nlink,
            st.st_size,st.st_mtime_ns,st.st_ctime_ns)


def read_transport_sources(path,expected):
    # This is DATA transport of fixed reviewed code, never execution of a path.
    # One returned readonly FD is recorded before any stat/read and consumed
    # before its sole close. No retry can use an ambiguous numeric descriptor.
    need(path==TRANSPORT_DATA['path'] and expected==TRANSPORT_DATA['sha256'],
         'exact reviewed source DATA path and SHA required')
    record={'path':path,'fd':None,'historical_fd':None,'state':'OPENING'}
    TRANSPORT_RECORDS.append(record);primary=None;secondary=[];selected=None
    try:
        record['fd']=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        record['state']='OWNED';fd=record['fd'];before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid==1000 and
             before.st_gid==1000 and before.st_nlink==1 and
             stat.S_IMODE(before.st_mode)==0o600 and
             before.st_size==TRANSPORT_DATA['bytes'] and
             0<before.st_size<=256*1024,'exact UID1000 source DATA metadata')
        need(transport_identity(os.stat(path,follow_symlinks=False))==
             transport_identity(before),'source DATA path/FD identity mismatch')
        raw=b''
        while len(raw)<before.st_size:
            chunk=os.read(fd,min(65536,before.st_size-len(raw)))
            need(bool(chunk),'truncated source DATA');raw+=chunk
        need(os.read(fd,1)==b'','unexpected source DATA trailing bytes')
        need(transport_identity(os.fstat(fd))==transport_identity(before) and
             transport_identity(os.stat(path,follow_symlinks=False))==
             transport_identity(before),'source DATA changed during snapshot')
        need(len(raw)==TRANSPORT_DATA['bytes'] and
             hashlib.sha256(raw).hexdigest()==expected,'source DATA full SHA mismatch')
        value=json.loads(raw.decode('utf-8'),object_pairs_hook=transport_pairs,
                         parse_constant=lambda _:need(False,'nonfinite source DATA'))
        need(type(value) is dict and set(value)=={'kind','provider','driver'} and
             value['kind']=='mckernel-reviewed-provider-native-source-transport-v1',
             'source DATA exact schema')
        literals=[]
        for name,size,digest in (('provider',42709,PROVIDER_SHA),('driver',104614,DRIVER_SHA)):
            row=value[name]
            need(type(row) is dict and set(row)=={'source','bytes','sha256'} and
                 type(row['source']) is str and type(row['bytes']) is int and
                 row['bytes']==size and row['sha256']==digest,'source DATA exact member')
            body=row['source'].encode('utf-8')
            need(len(body)==size and hashlib.sha256(body).hexdigest()==digest,
                 'source DATA actual reviewed source bytes mismatch')
            literals.append(row['source'])
        selected=tuple(literals)
    except BaseException:
        primary=sys.exc_info();TRANSPORT_FAILURES.append(primary)
        if record['fd'] is None:record['state']='NO_HANDLE'
    # Raw ownership cleanup precedes formatting/reporting or any compile/exec.
    closing=record['fd'];record['fd']=None
    if closing is not None:
        record['historical_fd']=closing;record['state']='CLOSE_CONSUMED'
        try:
            os.close(closing);record['state']='CLOSED'
        except BaseException:
            failure=sys.exc_info();record['state']='UNKNOWN_NO_NUMERIC_RETRY'
            record['error']=failure[1];record['traceback']=failure[2]
            TRANSPORT_FAILURES.append(failure);secondary.append(failure)
    if primary is not None:
        if secondary:
            try:primary[1].publisher_transport_secondary_exceptions=list(secondary)
            except BaseException:TRANSPORT_FAILURES.append(sys.exc_info())
        raise BaseException.with_traceback(primary[1],primary[2])
    if secondary:
        failure=secondary[0];raise BaseException.with_traceback(failure[1],failure[2])
    need(record['state']=='CLOSED' and selected is not None,
         'source DATA own closure required before code compilation')
    return selected


def read_bound_raw(source,path,expected,limit=2*1024*1024):
    record=PUB.own(source.open_exact(path),'rawData:'+path)
    before=os.fstat(record['fd'])
    need(stat.S_ISREG(before.st_mode) and before.st_uid==1000 and before.st_nlink==1 and
         stat.S_IMODE(before.st_mode)==0o600 and 0<before.st_size<=limit,'actual UID1000 raw DATA file required')
    raw=b''
    while len(raw)<before.st_size:
        chunk=os.read(record['fd'],min(65536,before.st_size-len(raw)));need(bool(chunk),'short raw DATA read');raw+=chunk
    after=os.fstat(record['fd'])
    need((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==
         (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) and
         hashlib.sha256(raw).hexdigest()==expected,'raw DATA identity/hash changed')
    PUB.close_once(record)
    return raw

def pin_published(bootstrap,name,digest):
    path=PUB.ROOT_PATH+'/'+name;fd,raw=bootstrap.pinned_root_file(path,digest);row=PUB.own(fd,'publishedData:'+name);st=os.fstat(fd)
    result={'path':path,'sha256':digest,'bytes':len(raw),'device':st.st_dev,'inode':st.st_ino,
            'uid':st.st_uid,'gid':st.st_gid,'mode':stat.S_IMODE(st.st_mode),'nlink':st.st_nlink}
    PUBLISHED.append(result);return result

def account_projection(account,expected):
    state,usage,credit,observed=account.current_account_snapshot(expected)
    # The qualified9032 consumer reads actual39a state/ledger/receipt and live
    # owner bookends. No account/RPC call, allowance or acceptance is synthesized.
    return {'validator_sha256':ACCOUNT_SHA,'expected_owner_ref':EXPECTED_OWNER,
            'invocation':INVOCATION,'thread_id':state['thread_id'],
            'worker_pid':state['worker_pid'],'worker_start':state['worker_start'],
            'server_pid':state['server_pid'],'server_start':state['server_start'],
            'guardian_run_id':state['guardian_run_id'],'credit_run_id':credit['id'],
            'source_event':usage['source_event'],'source_kind':usage['source_kind'],
            'received_utc_ns':usage['receipt_received_utc_ns'],
            'received_mono_ns':usage['receipt_received_mono_ns'],
            'observed_utc':observed,'authority':None,'native_grant':False}

def check_measured(project):
    required={'kind','invocation','at','caps','current_HOST_jobs_before',
              'current_owned_controller_worker_overhead_bytes','other_current_HOST_payload_reserved_bytes',
              'MemAvailable_bytes','host_free_bytes','scratch_free_bytes','native_and_historical_unknowns_preserved'}
    need(type(project) is dict and set(project)==required and
         project['kind']=='mckernel-native-Root-measured-projection-v1' and project['invocation']==INVOCATION,
         'exact current Root measured projection DATA')
    age=time.time()-datetime.datetime.fromisoformat(project['at']).timestamp();need(0<=age<=30,'actual measured projection stale')
    jobs=project['current_HOST_jobs_before'];overhead=project['current_owned_controller_worker_overhead_bytes'];other=project['other_current_HOST_payload_reserved_bytes']
    need(type(jobs) is int and 0<=jobs<3 and type(overhead) is int and overhead>=0 and
         type(other) is int and other>=0 and overhead+other+1342177280<=4*2**30,'actual shared HOST capacity')
    for key,floor in (('MemAvailable_bytes',26*2**30),('host_free_bytes',16*2**30+32*2**20),('scratch_free_bytes',12*2**30+32*2**20)):
        need(type(project[key]) is int and project[key]>=floor,'measured capacity/floor')
    need(project['native_and_historical_unknowns_preserved'] is True,'current-only scope required')
    available=int(next(row.split()[1] for row in pathlib.Path('/proc/meminfo').read_text().splitlines() if row.startswith('MemAvailable:')))*1024
    host=shutil.disk_usage('/home/holden/mckernel').free;scratch=shutil.disk_usage('/home/holden/mckernel-work/m14-blocker-resolution-20261110/compute-image-source-1/output').free
    need(available>=26*2**30 and host>=16*2**30+32*2**20 and scratch>=12*2**30+32*2**20,'fresh actual memory/disk floor')
    return {'MemAvailable_bytes':available,'host_free_bytes':host,'scratch_free_bytes':scratch}

def main():
    global PUB,PROVIDER_STARTED,PROVIDER_NAMESPACE
    need(os.getuid()==os.geteuid()==os.getgid()==os.getegid()==0 and os.sched_getaffinity(0)=={6},'actual admitted Root/CPU6 required')
    need(len(sys.argv)==7 and sys.argv[0]=='-c','source DATA refs/rawProjection+SHA required')
    provider_data,provider_data_sha,driver_data,driver_data_sha,raw_path,raw_sha=sys.argv[1:]
    need(provider_data==driver_data and provider_data_sha==driver_data_sha,
         'one exact reviewed source DATA object required')
    provider_literal,driver_literal=read_transport_sources(provider_data,provider_data_sha)
    provider_sha=PROVIDER_SHA;driver_sha=DRIVER_SHA
    need(hashlib.sha256(provider_literal.encode()).hexdigest()==provider_sha==PROVIDER_SHA and
         hashlib.sha256(driver_literal.encode()).hexdigest()==driver_sha==DRIVER_SHA,'exact reviewed byte literals')
    definitions=types.ModuleType('provider_definitions');definitions.__file__=PROVIDER_PATH
    exec(compile(provider_literal,PROVIDER_PATH,'exec'),definitions.__dict__)
    need(sys.executable==definitions.RUNTIME['path'],'same canonical interpreter required')
    PUB=types.ModuleType('initial_data_writer');PUB.__file__=DRIVER_PATH
    exec(compile(driver_literal,DRIVER_PATH,'exec'),PUB.__dict__)
    need(resource.getrlimit(resource.RLIMIT_AS)==(536870912,536870912) and
         resource.getrlimit(resource.RLIMIT_FSIZE)==(67108864,67108864) and
         resource.getrlimit(resource.RLIMIT_NOFILE)==(512,512) and resource.getrlimit(resource.RLIMIT_CORE)==(0,0),'same normal Root profile')
    bootstrap=types.ModuleType('root_bootstrap');bootstrap.__file__=definitions.BOOTSTRAP_PATH;sys.modules['root_bootstrap']=bootstrap
    exec(compile(definitions.BOOTSTRAP_BYTES,bootstrap.__file__,'exec'),bootstrap.__dict__)
    fd,body=bootstrap.pinned_root_file(bootstrap.__file__,definitions.BOOTSTRAP_SHA);PUB.own(fd,'registered-bootstrap');need(body==definitions.BOOTSTRAP_BYTES,'physical bootstrap differs')
    modules={}
    for name in ('ownership_latch','graph_observations','inplace_custody'):
        spec=definitions.MODULES[name];fd,module=bootstrap.load_verified_module(name,spec['path'],spec['sha256']);PUB.own(fd,'installed-provider:'+name);modules[name]=module
    source=modules['inplace_custody'];obs=modules['graph_observations']
    need(hashlib.sha256(ACCOUNT_BYTES).hexdigest()==ACCOUNT_SHA,'exact qualified account consumer')
    account=types.ModuleType('current_actual_account_consumer');account.__file__=ACCOUNT_PATH
    exec(compile(ACCOUNT_BYTES,ACCOUNT_PATH,'exec'),account.__dict__)
    need(hashlib.sha256(pathlib.Path(ACCOUNT_PATH).read_bytes()).hexdigest()==ACCOUNT_SHA,'actual qualified9032 source changed')
    expected=json.loads(read_bound_raw(source,EXPECTED_OWNER['path'],EXPECTED_OWNER['sha256']),object_pairs_hook=source.unique)
    project=json.loads(read_bound_raw(source,raw_path,raw_sha),object_pairs_hook=source.unique,
                       parse_constant=lambda _: need(False,'nonfinite measured projection'))
    first=account_projection(account,expected);fresh=check_measured(project);PUB.check_caps(project['caps'],PUB.CORE['minimum_start_allowance_seconds'])
    status=pathlib.Path('/proc/self/status').read_text();cap=int(next(row.split()[1] for row in status.splitlines() if row.startswith('CapEff:')),16);need(cap&(1<<9),'actual immutable capability required')
    os.umask(0o077);varlib=PUB.own(source.open_exact('/var/lib'),'trusted-var-lib-parent');parent=os.fstat(varlib['fd'])
    need(stat.S_ISDIR(parent.st_mode) and parent.st_uid==0 and not stat.S_IMODE(parent.st_mode)&0o022,'trusted actual varlib parent')
    birth=obs.process(os.getpid())[0];basename='mckernel-native-initial-data-'+str(os.getpid())+'-'+birth
    os.mkdir(basename,0o700,dir_fd=varlib['fd']);os.fsync(varlib['fd'])
    root=PUB.own(os.open(basename,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=varlib['fd']),'new-current-operation-root')
    PUB.ROOT_FD=root['fd'];PUB.ROOT_PATH='/var/lib/'+basename;source.root_private(PUB.ROOT_FD)
    journal=PUB.own(os.open('INITIAL-CONTROL-FLAGS.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=PUB.ROOT_FD),'initial-data-prior-flags');PUB.CONTROL_JOURNAL_FD=journal['fd'];os.fsync(PUB.ROOT_FD)
    measured={'kind':'mckernel-native-host-measured-data-v1','authority':None,'native_grant':False,
              'raw_projection_ref':{'path':raw_path,'sha256':raw_sha},'current_actual_account':first,
              'measured':project,'fresh_memory_and_disk':fresh,'same_Root':PUB.CORE['same_Root'],
              'new_allowance_or_controller_or_resource_release':False}
    host_sha=PUB.save_control('HOST-ADMISSION.DATA.json',measured,bootstrap,source,True);host_ref=pin_published(bootstrap,'HOST-ADMISSION.DATA.json',host_sha)
    root_input={'kind':'mckernel-native-signal-root-input-v1','source_contract_sha256':PUB.CORE_SHA,
                'caps':project['caps'],'host_admission_ref':{'path':host_ref['path'],'sha256':host_ref['sha256']}}
    input_sha=PUB.save_control('ROOT-ADMISSION-INPUT.json',root_input,bootstrap,source,True);input_ref=pin_published(bootstrap,'ROOT-ADMISSION-INPUT.json',input_sha)
    catalogue={'kind':'initial-native-Root-DATA-catalog-v1','files':list(PUBLISHED),'raw_projection_ref':{'path':raw_path,'sha256':raw_sha},
               'qualified_account_source_sha256':ACCOUNT_SHA,'expected_owner_ref':EXPECTED_OWNER,
               'native_nonce_or_watchdog_identity_issued':False,'native_grant':False,'persistent_new_control_files_only':True}
    catalogue_sha=PUB.save_control('INITIAL-DATA-CATALOG.json',catalogue,bootstrap,source,True);catalogue_ref=pin_published(bootstrap,'INITIAL-DATA-CATALOG.json',catalogue_sha)
    # Revalidate the actual owner/credit/read observation and current caps after
    # publication. Nothing here constructs a native nonce, request, claim orPID.
    account_projection(account,expected);check_measured(project);PUB.check_caps(project['caps'],PUB.CORE['minimum_start_allowance_seconds'])
    need(not PUB.SECONDARY,'initial DATA own-close uncertain')
    saved=sys.argv;sys.argv=['-c',driver_literal,driver_sha,input_ref['path'],input_ref['sha256']]
    PROVIDER_NAMESPACE={'__name__':'__main__','__file__':PROVIDER_PATH}
    PROVIDER_STARTED=True
    try:
        # Execute FULL unchanged provider, including its qualified protected
        # entry boundary. Calling main directly would bypass that boundary.
        exec(compile(provider_literal,PROVIDER_PATH,'exec'),PROVIDER_NAMESPACE)
    except SystemExit as final:
        need(type(final.code) is int and final.code in (0,2) and
             PROVIDER_NAMESPACE.get('STATE')=='CLOSED_RESTORED' and
             all(row['state']=='CLOSED' for row in PROVIDER_NAMESPACE['OWNED']),
             'only genuine provider final return after restored/closed may exit')
        code=final.code
    else:raise RuntimeError('provider entry returned without its actual final disposition')
    finally:sys.argv=saved
    PUB.close_all();need(not PUB.SECONDARY and all(row['state']=='CLOSED' for row in PUB.OWNED),'initial DATA own closure unknown')
    print(json.dumps({'status':'INITIAL_DATA_PUBLISHED_PROVIDER_CLOSED_RESTORED','provider_exit':code,
          'root_input':input_ref,'host_admission':host_ref,'catalogue':catalogue_ref,
          'native_grant_from_DATA':False,'native_nonce_or_watchdog_generated_by_publisher':False},sort_keys=True),flush=True)
    return code

if __name__=='__main__':
    try:
        exit_code=main()
    except BaseException:
        primary=sys.exc_info()
        if PUB is not None:
            PUB.capture_raw_exception('initial-data-publisher-primary',primary[1],primary[2])
            if PROVIDER_STARTED and (PROVIDER_NAMESPACE is None or PROVIDER_NAMESPACE.get('STATE')!='CLOSED_RESTORED'):
                PUB.emit_failure_diagnostics('INITIAL_DATA_PROVIDER_CUSTODY_UNKNOWN',primary[1]);PUB.retain_diagnostic_custody()
            PUB.close_all()
            reported=PUB.emit_failure_diagnostics('INITIAL_DATA_AFTER_OWN_CLOSE_ATTEMPTS',primary[1])
            if PUB.SECONDARY or not reported:PUB.retain_diagnostic_custody()
        raise BaseException.with_traceback(primary[1],primary[2])
    raise SystemExit(exit_code)
