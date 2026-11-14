# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Exact finite F05 cleanup via E088 and qualified same-Popen keeper only.
# Excluded worker01a1c48d/turn01a1ce01 signal/frame/xstate task remains excluded.
import ast,datetime,hashlib,json,os,pathlib,signal,subprocess,sys,time,traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE/'root-capture-1'
REQUEST_SHA256='2e3aa9fa771fac90156fb19fa45700740050b8eaca55cac008460da04fa7ef5e'
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]


def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def sha(path):return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def save(name,value):
    temporary=OUT/(name+'.pending')
    with temporary.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(str(temporary),str(OUT/name))
    for path in OUT.iterdir():
        if path.is_file():
            fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
            try:os.fsync(fd)
            finally:os.close(fd)
    fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)

def selected(item,names):
    raw=pathlib.Path(item['path']).read_bytes()
    assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),item['path'],'exec'),globals())

def main():
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    rp=pathlib.Path(sys.argv[1]);assert sha(rp)==sys.argv[2];review=json.loads(rp.read_bytes())
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']=='GO_EXACT_TLS_5645_TERMINAL_CONTAINER_CLEANUP_ONLY'
    for key,value in {'request_sha256':REQUEST_SHA256,'run_root_once_sha256':sha(HERE/'run_root_once.py'),'capture_root_once_sha256':sha(__file__),'capture_request_sha256':sha(HERE/'CAPTURE-REQUEST.json'),'profile_sha256':q['profile']['sha256'],'saved_artifact_manifest_sha256':q['saved_artifact_manifest']['sha256']}.items():assert review[key]==value,key
    assert sha(sys.argv[3])==sys.argv[4] and os.sched_getaffinity(0)=={0}
    grant=json.loads(pathlib.Path(sys.argv[3]).read_bytes())
    assert set(grant)==set(q['admission_fields']) and grant['request_sha256']==REQUEST_SHA256 and grant['charge']==q['charge']
    assert grant['runtime_operation_review']==dict(path=str(rp.resolve()),bytes=rp.stat().st_size,sha256=sys.argv[2])
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert not OUT.exists();os.umask(0o077);OUT.mkdir(mode=0o700)
    global ENV
    ENV=os.environ.copy();ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    selected(q['qualified_outer_capture'],['call'])
    argv=['/usr/bin/taskset','-c','0','/usr/bin/python3','-B',str(HERE/'run_root_once.py'),str(rp),sys.argv[2],sys.argv[3],sys.argv[4]]
    try:
        save('ROOT-ARGV.json',dict(argv=argv,request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4]))
        output=call('Root-parent',argv,timeout=180)
        assert len(clients)==1 and not pending_calls
        row=clients[0];assert row['exit']==0 and row['direct_wait_joined'] and row['streams_closed'] and row['receipt_persisted'] and not row['lifecycle_UNKNOWN'] and not row['resource_charge_retained']
        parent=json.loads((HERE/'execution-1/RESULT.json').read_bytes())
        assert parent['status']=='PASS_EXACT_TLS_5645_TERMINAL_CONTAINER_CLEANUP_ONLY' and len(parent['client_ownership'])==3 and len(parent['containers'])==1
        assert parent['containers'][0]['CID']==q['CID'] and parent['containers'][0]['removed'] and parent['containers'][0]['terminal_exit']==1 and not parent['containers'][0]['lifecycle_UNKNOWN']
        remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
        save('RESULT.json',dict(status='PASS_EXACT_TLS_5645_TERMINAL_CLEANUP_ROOT_PARENT_CAPTURE_ONLY',clients=clients,root_parent_argv=argv,remaining_direct_children=remaining,full_initial_terminal_Root_tool_and_independent_actual_Q_required=True,automatic_resource_retirement=False,native12_source_other_UNKNOWN_scopes_unchanged=True,compiler_observer_device_native_executed=False,original_acceptance=False))
        print(output.decode(),end='');return 0
    except BaseException as error:
        try:save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',clients=clients,root_parent_argv=argv,error=type(error).__name__+': '+str(error),traceback=traceback.format_exc(),automatic_container_kill_remove_or_resource_release=False,original_acceptance=False))
        except BaseException:pass
        raise

if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_bytes())
    selected(q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
