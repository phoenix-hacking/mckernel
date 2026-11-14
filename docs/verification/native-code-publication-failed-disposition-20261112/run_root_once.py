# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One failed-family actor. Root alone later joins ORIGINAL session36902.
import ast,datetime,hashlib,json,os,pathlib,resource,shutil,signal,stat,subprocess,sys,time,traceback,types
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'execution-1'
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]

def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(name,value):
    assert pathlib.Path(name).name==name
    raw=(json.dumps(value,indent=2,sort_keys=True)+'\n').encode()
    fd=os.open(str(OUT/name),os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    try:
        st=os.fstat(fd);assert stat.S_ISREG(st.st_mode) and st.st_uid==1000 and st.st_nlink==1
        offset=0
        while offset<len(raw):offset+=os.write(fd,raw[offset:])
        os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)

def selected(item,names):
    raw=pathlib.Path(item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),item['path'],'exec'),globals())

def support_from(q):
    item=q['source_inputs']['packet_support.py'];raw=pathlib.Path(item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    module=types.ModuleType('failed_scope_support');module.__file__=item['path'];exec(compile(raw,item['path'],'exec'),module.__dict__);return module

def main():
    assert len(sys.argv)==9
    qpath,qsha,review_path,review_sha,admission_path,admission_sha,argv_path,argv_sha=sys.argv[1:]
    assert pathlib.Path(qpath)==HERE/'REQUEST.json'
    raw=pathlib.Path(qpath).read_bytes();assert hashlib.sha256(raw).hexdigest()==qsha;q=json.loads(raw);support=support_from(q)
    for item in list(q['source_inputs'].values())+list(q['proof_inputs'].values())+list(q['tool_inputs'].values()):support.check_pin(item)
    review,_=support.read_fixed(review_path,review_sha)
    assert pathlib.Path(review_path)==pathlib.Path(q['review_path']) and review['schema']==q['review_schema']
    assert review['reviewer'].startswith('/root/m15_installed_leaf_review;') and review['decision'].startswith('GO')
    assert review['request_sha256']==qsha and review['source_binding_sha256']==q['source_binding_sha256']
    for name in ('run_root_once.py','dispose_failed_publication.py','packet_support.py'):
        assert review[name.replace('.py','')+'_sha256']==q['source_inputs'][name]['sha256']
    assert pathlib.Path(admission_path)==HERE/'ROOT-ADMISSION.json' and pathlib.Path(argv_path)==HERE/'ACTUAL-ACTOR-ARGV.json'
    admission,admission_identity=support.read_fixed(admission_path,admission_sha)
    actual,argv_identity=support.read_fixed(argv_path,argv_sha)
    argv=support.actor_argv(q,qsha,review_path,review_sha,admission_path,admission_sha)
    assert set(actual)=={'argv'} and actual['argv']==argv
    assert all(type(v) is str and '\x00' not in v and len(v.encode())<131072 for v in argv)
    assert sum(len(v.encode())+1 for v in argv)+65536<os.sysconf('SC_ARG_MAX')
    age=support.validate_admission(q,qsha,review_sha,admission,argv)
    assert os.getuid()==os.geteuid()==1000
    available=int(next(x.split()[1] for x in pathlib.Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
    host=shutil.disk_usage(ROOT).free;scratch=shutil.disk_usage(q['scratch_path']).free
    assert available>=26*2**30 and host>=16*2**30+32*2**20 and scratch>=12*2**30+32*2**20
    assert not os.path.lexists(OUT) and not os.path.lexists(q['evidence_directory'])
    os.umask(0o077);OUT.mkdir(mode=0o700)
    global ENV
    ENV=os.environ.copy();ENV['PATH']='/usr/sbin:/usr/bin:/sbin:/bin';ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    try:
        save('ADMISSION.json',dict(at=now(),request_sha256=qsha,review_sha256=review_sha,admission_sha256=admission_sha,
            admission_identity=admission_identity,actual_complete_Root_admission=admission,actor_argv_sha256=argv_sha,actor_argv_identity=argv_identity,
            age_seconds=age,actor_argv_normalized_sha256=support.normalized_argv_sha(argv),source_binding_sha256=q['source_binding_sha256'],
            capture_layout_sha256=q['capture_layout_sha256'],MemAvailable_bytes=available,host_free_bytes=host,scratch_free_bytes=scratch,
            original2GiB_session36902_and_all_holds_retained=True))
        selected(q['source_inputs']['qualified_e088_capture'],['call'])
        raw=call(q['command_id'],argv,timeout=q['initial_wait_seconds'])
        assert len(raw)<=65536;value=json.loads(raw)
        assert value['status'] in ('FAILED_SCOPE_TARGET_TERMINAL_PENDING_ORIGINAL_JOIN','NO_SIGNAL_HOLD','SIGNAL_ATTEMPT_TERMINAL_OUTCOME_UNKNOWN_RETAINED')
        for key,expected in [('request_sha256',qsha),('review_sha256',review_sha),('admission_sha256',admission_sha),('source_binding_sha256',q['source_binding_sha256'])]:assert value[key]==expected
        assert value['actor_own_FDs_closed'] and value['remaining_actor_children']==[]
        assert value['original_session']==36902 and value['original2GiB_and_all_other_holds_retained'] and value['original_resource_retirement'] is False
        assert value['original_keeper_direct_wait']=='UNPROVEN'
        if value['status']=='FAILED_SCOPE_TARGET_TERMINAL_PENDING_ORIGINAL_JOIN':
            assert value['signal_call_consumed'] and value['signal_attempted'] and value['signal_call_returned'] and value['target_pidfd_terminal'] and value['missing_predicate'] is None
        elif value['status']=='NO_SIGNAL_HOLD':
            assert not value['signal_attempted'] and not value['signal_call_returned'] and value['missing_predicate']
        else:
            assert value['signal_attempted'] and not value['signal_call_returned'] and value['target_pidfd_terminal'] and value['missing_predicate']
        assert len(clients)==1 and not pending_calls
        c=clients[0];assert c['exit']==0 and c['direct_wait_joined'] and c['streams_closed'] and c['receipt_persisted'] and c['primary_error'] is None and not c['secondary_errors'] and not c['lifecycle_UNKNOWN'] and not c['resource_charge_retained']
        assert (OUT/(q['command_id']+'.stderr')).read_bytes()==b''
        children=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not children
        save('RESULT.json',dict(status='CAPTURED_FAILED_SCOPE_DISPOSITION_DATA_PENDING_ORIGINAL_JOIN_AND_INDEPENDENT_QUALIFICATION',at=now(),
            request_sha256=qsha,review_sha256=review_sha,admission_sha256=admission_sha,actor_argv_sha256=argv_sha,source_binding_sha256=q['source_binding_sha256'],
            capture_layout_sha256=q['capture_layout_sha256'],clients=clients,redacted_actor_record=value,remaining_new_parent_children=children,
            raw_protected_DATA_not_opened_by_parent=True,original_session36902_not_joined_by_new_parent=True,
            original2GiB_and_all_other_holds_retained=True,original_resource_retirement=False,
            new256MiB_retained_until_full_Root_and_independent_actual_Q=True))
        print(json.dumps(dict(status='CAPTURED_FAILED_SCOPE_DATA',request_sha256=qsha,actor_status=value['status'],original2GiB_session36902_retained=True,original_resource_retirement=False),sort_keys=True))
    except BaseException as error:
        try:save('RESULT.json',dict(status='FAILED_SCOPE_ACTOR_OR_CAPTURE_ERROR_RETAINED',at=now(),request_sha256=qsha,error_type=type(error).__name__,error=str(error),traceback=traceback.format_exc(),clients=clients,pending_same_direct_handles=list(pending_calls),original2GiB_session36902_and_all_holds_retained=True,original_resource_retirement=False))
        except BaseException:pass
        raise

if __name__=='__main__':
    raw=(HERE/'REQUEST.json').read_bytes();assert len(sys.argv)==9 and hashlib.sha256(raw).hexdigest()==sys.argv[2];q=json.loads(raw)
    selected(q['source_inputs']['qualified_1f66_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
