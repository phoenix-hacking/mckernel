# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# One qualified e088 parent capture plus existing same-Popen uncertainty retention.
import ast,datetime,hashlib,json,os,pathlib,signal,subprocess,sys,traceback
ROOT=pathlib.Path('/home/holden/mckernel');HERE=pathlib.Path(__file__).resolve().parent;OUT=HERE/'root-capture-1'
REQUEST_SHA256='53942068f24fc8879f8208d4772f1fbb4d7d3c30d9a2b373c1daa4f680054b04'
clients=[];pending_calls={};keeper_capture_errors=[];OUTER_RETENTION_ERRORS=[];OUTER_ORIGINAL_WAITS=[]
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def save(name,value):
    temporary=OUT/(name+'.pending')
    with temporary.open('x') as stream:
        json.dump(value,stream,indent=2,sort_keys=True);stream.write('\n');stream.flush();os.fsync(stream.fileno())
    os.replace(str(temporary),str(OUT/name));fd=os.open(str(OUT),os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:os.fsync(fd)
    finally:os.close(fd)
def selected(item,names):
    raw=pathlib.Path(item['path']).read_bytes();assert len(raw)==item['bytes'] and hashlib.sha256(raw).hexdigest()==item['sha256']
    nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in names];assert {n.name for n in nodes}==set(names)
    exec(compile(ast.Module(body=nodes,type_ignores=[]),item['path'],'exec'),globals())
def main():
    assert len(sys.argv)==5 and sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256
    q=json.loads((HERE/'REQUEST.FROZEN.json').read_text());review_path=pathlib.Path(sys.argv[1]);assert sha(review_path)==sys.argv[2]
    review=json.loads(review_path.read_text());assert review['schema']=='m15-f05-create-independent-operation-review.v1' and review['reviewer'].startswith(q['independent_reviewer_prefix']) and review['decision'].startswith('GO')
    assert review['request_sha256']==REQUEST_SHA256 and review['run_root_once_sha256']==sha(HERE/'run_root_once.py') and review['capture_root_once_sha256']==sha(__file__)
    assert sha(sys.argv[3])==sys.argv[4] and os.sched_getaffinity(0)<={0,6,7}
    assert not OUT.exists();os.umask(0o077);OUT.mkdir(mode=0o700)
    global ENV
    ENV=os.environ.copy();ENV.update(q['host_environment']);ENV['SUDO_ASKPASS']=str(ROOT/'scripts/os_goal_sudo_askpass.py')
    selected(q['qualified_outer_capture'],['call'])
    argv=['/usr/bin/taskset','-c','7','/usr/bin/python3','-B',str(HERE/'run_root_once.py'),str(review_path),sys.argv[2],sys.argv[3],sys.argv[4]]
    try:
        save('ROOT-ARGV.json',dict(argv=argv,request_sha256=REQUEST_SHA256,review_sha256=sys.argv[2],admission_sha256=sys.argv[4]))
        output=call('Root-parent',argv,timeout=600)
        assert len(clients)==1 and not pending_calls
        rec=clients[0];assert rec['exit']==0 and rec['direct_wait_joined'] and rec['streams_closed'] and rec['receipt_persisted'] and not rec['lifecycle_UNKNOWN'] and not rec['resource_charge_retained']
        parent=json.loads((HERE/'execution-1/RESULT.json').read_text());assert parent['status']=='PASS_F05_NEW_CREATE_OBSERVER_LOCAL_LIBC_SEAMS_ONLY' and len(parent['containers'])==2 and all(c['removed'] and not c['lifecycle_UNKNOWN'] for c in parent['containers'])
        remaining=pathlib.Path('/proc/self/task/%d/children'%os.getpid()).read_text().split();assert not remaining
        save('RESULT.json',dict(status='PASS_FINITE_F05_CREATE_ROOT_PARENT_CAPTURE',clients=clients,root_parent_argv=argv,remaining_direct_children=remaining,original_acceptance=False,first_repeat_cohort_changed=False,full_outer_tool_completion_still_required_before_current_only_release=True));print(output.decode(),end='')
    except BaseException as e:
        try:save('RESULT.json',dict(status='FAILED_PRESERVED_NO_UNCHANGED_RETRY',clients=clients,root_parent_argv=argv,error=type(e).__name__+': '+str(e),traceback=traceback.format_exc(),automatic_resource_release=False,automatic_remove_or_container_kill=False,original_acceptance=False))
        except BaseException:pass
        raise
if __name__=='__main__':
    assert sha(HERE/'REQUEST.FROZEN.json')==REQUEST_SHA256;q=json.loads((HERE/'REQUEST.FROZEN.json').read_text())
    selected(q['qualified_same_handle_keeper'],['keeper_record','preserve_original_pending_waits','retain_outer_error','retain_original_pending_nonescaping','entry_once_with_original_custody'])
    sys.exit(entry_once_with_original_custody())
