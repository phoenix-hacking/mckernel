# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Existing E088 direct-child capture and original same-Popen keeper methods only.
# Rejected worker01a1c48d / turn01a1ce01 signal/frame/xstate request is excluded.
import ast, datetime, hashlib, json, os, pathlib, signal, subprocess, sys, time, traceback
ROOT=pathlib.Path('/home/holden/mckernel')
HERE=pathlib.Path(__file__).resolve().parent
OUT=HERE/'root-capture-1'
REQUEST_SHA256='c787078e177dc6363edd02a3915d250b04f1b30f206e2ebbe2bb96521e381b86'
clients=[];pending_calls={};keeper_capture_errors=[]
OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]

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
    review_path=pathlib.Path(sys.argv[1]);assert sha(review_path)==sys.argv[2]
    review=json.loads(review_path.read_bytes())
    assert review['schema']==q['operation_review_schema'] and review['reviewer'].startswith(q['independent_reviewer_prefix'])
    assert review['decision']=='GO_F06_WRAPPER_SEVEN_ARTIFACT_COMPILER_PASSIVE_OPERATION'
    assert review['request_sha256']==REQUEST_SHA256 and review['run_root_once_sha256']==sha(HERE/'run_root_once.py') and review['capture_root_once_sha256']==sha(__file__)
    assert review['capture_request_sha256']==sha(HERE/'CAPTURE-REQUEST.json')
    for key,ref in [('compile_batch_sha256',q['compile_batch']),('command_plan_sha256',q['command_plan']),('profile_sha256',q['profile']),('source_review_sha256',q['source_review'])]:assert review[key]==ref['sha256']
    assert sha(sys.argv[3])==sys.argv[4] and os.sched_getaffinity(0)=={7}
    grant=json.loads(pathlib.Path(sys.argv[3]).read_bytes())
    assert set(grant)==set(q['admission_fields']) and grant['request_sha256']==REQUEST_SHA256
    assert grant['runtime_operation_review']==dict(path=str(review_path.resolve()),bytes=review_path.stat().st_size,sha256=sys.argv[2])
    assert grant['charge']==q['charge'] and grant['no_exclusive_other_owner_scope'] is True
    assert 0<=(time.time_ns()-grant['issued_utc_ns'])/1e9<=60 and 0<=(time.monotonic_ns()-grant['issued_mono_ns'])/1e9<=60
    assert not OUT.exists();os.umask(0o077);OUT.mkdir(mode=0o700)
    global ENV
    ENV=os.environ.copy();ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    selected(q['qualified_outer_capture'],['call'])
    argv=['/usr/bin/taskset','-c','7','/usr/bin/python3','-B',str(HERE/'run_root_once.py'),str(review_path),sys.argv[2],sys.argv[3],sys.argv[4]]
    try:
        save('ROOT-ARGV.json',dict(argv=argv,request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4]))
        output=call('Root-parent',argv,timeout=1200)
        assert len(clients)==1 and not pending_calls
        rec=clients[0]
        assert rec['exit']==0 and rec['direct_wait_joined'] and rec['streams_closed'] and rec['receipt_persisted'] and not rec['lifecycle_UNKNOWN'] and not rec['resource_charge_retained']
        parent=json.loads((HERE/'execution-1/RESULT.json').read_bytes())
        assert parent['status']=='PASS_F06_WRAPPERS_PROTECTED_COMPILER_PASSIVE_ONLY' and len(parent['containers'])==1
        assert all(c['removed'] and not c['lifecycle_UNKNOWN'] for c in parent['containers'])
        assert len(parent['client_ownership'])==10 and parent['payload_or_collector_executed'] is False and parent['staging_or_native_executed'] is False
        remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
        save('RESULT.json',dict(status='PASS_F06_WRAPPERS_ROOT_PARENT_PROTECTED_CAPTURE_ONLY',clients=clients,root_parent_argv=argv,remaining_direct_children=remaining,original_acceptance=False,payload_or_collector_executed=False,full_initial_and_terminal_Root_tool_replies_required=True,independent_actual_qualification_and_scoped_Root_retirement_required=True))
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
