"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Own exactly one newly authorized A3 finite verifier; retain original wait4 and streams.
No capture, holder, Docker, compiler, native, signal, retry or custom timeout operation.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess

H=Path(__file__).resolve().parent
A=H.parent
ROOT=Path('/home/holden/mckernel')

def ref(path):
    p=Path(path);assert p.is_absolute() and p.is_file() and not p.is_symlink()
    first=p.stat();raw=p.read_bytes();last=p.stat()
    assert (first.st_dev,first.st_ino,first.st_size,first.st_mtime_ns,first.st_ctime_ns)==(last.st_dev,last.st_ino,last.st_size,last.st_mtime_ns,last.st_ctime_ns)
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def auth(row):
    assert set(row)=={'path','bytes','sha256'} and ref(row['path'])==row
    return Path(row['path'])

def read(path):return json.loads(Path(path).read_bytes())
def checked(row):return read(auth(row))
def birth(pid):return int(Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19])

def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def main():
    assert os.getuid()==os.geteuid()==1000
    authority=H/'ROOT-REVIEWER-EXECUTION-AUTHORITY.json'
    assert ref(authority)==dict(path=str(authority),bytes=5156,sha256='94f851d818eedde7c84b323c844ec09061f9838293afe84ec44cd716bed9cd7b')
    g=read(authority)
    assert g['author']=='/root' and g['decision']=='AUTHORIZE_ONE_ACTUAL_A3_INDEPENDENT_FINITE_COLD_AND_HOT_REVIEW_ONLY'
    assert g['designated_reviewer']=='/root/observerreview' and g['maximum_invocations']==1
    assert g['nonce']=='e984210ca59641b299cf42d392eb953b' and g['admission']==str(A) and g['handoff']==str(H)
    for key in ['verifier_source','actual_bindings','actual_source_publication','actual_operation','actual_operation_review','actual_current_descriptor','closed_unlaunched_frontier']:auth(g[key])
    b=checked(g['actual_bindings']);refs=b['static_refs'];assert len(refs)==26
    assert b['nonce']==g['nonce'] and b['admission']==str(A) and b['actual_execution_authority'] is None
    for row in refs.values():auth(row)
    assert refs['finite_verifier']==g['verifier_source'] and refs['source_publication']==g['actual_source_publication']
    pub=checked(g['actual_source_publication']);assert len(pub['rows'])==761 and pub['runtime_authority'] is None
    published={}
    for row in pub['rows']:
        actual=row['actual'];auth(actual)
        blob=subprocess.run(['git','cat-file','blob',pub['commit']+':'+row['fetched_equivalent_path']],cwd=ROOT,capture_output=True,check=True).stdout
        assert len(blob)==actual['bytes'] and hashlib.sha256(blob).hexdigest()==actual['sha256']
        assert actual['path'] not in published;published[actual['path']]=actual
    for key,row in refs.items():
        if key!='source_publication':assert published[row['path']]==row
    policy=checked(refs['aggregate_job_policy']);assert published[policy['original_authorization']['path']]==policy['original_authorization']
    for name in ['OUTPUT','HOLDER','ROOT-PREHOLDER-PHYSICAL-1.json','ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.json','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json']:
        assert not os.path.lexists(A/name)
    for name in ['PREWARM_READY.json','FINITE-STARTED.json','INDEPENDENT-FINITE-REVIEW.PASS.json']:
        assert not os.path.lexists(H/name)
    C=Path(g['verifier_source']['path']).parent
    argv=g['argv'];assert argv[:10]==['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=2147483648:2147483648','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B']
    assert argv[10]==str(C/'finite_review.py') and argv[-1]==str(H)
    operation=checked(g['actual_operation']);review=checked(g['actual_operation_review'])
    assert review['independent'] is True
    runtime=C/'runtime_guard.py';runtime_ref=ref(runtime)
    assert runtime_ref in operation['subjects'].values(), 'actual operation authenticates A3 runtime consumer'
    spec=importlib.util.spec_from_file_location('independent_A3_exact_prestart_guard',runtime)
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    write(H/'INDEPENDENT-A3-PREFLIGHT.json',dict(scope=__doc__.splitlines()[0],reviewer='/root/observerreview',root_authority=ref(authority),bindings=g['actual_bindings'],source_publication=g['actual_source_publication'],independently_verified_fetched_rows=761,nonself_static_refs=25,original_job_authorization_covered=True,nonce=g['nonce'],guard_calls=0,observer_queries=0,finite_runs=0,root_capture_or_native_authority=False))
    write(H/'FINITE-ONCE-CLAIM.json',dict(scope=__doc__.splitlines()[0],reviewer='/root/observerreview',nonce=g['nonce'],argv=argv,root_authority=ref(authority),wrapper=ref(__file__),runtime_guard=runtime_ref))
    with (H/'finite.stdout').open('xb') as out,(H/'finite.stderr').open('xb') as err:
        # Actual current account/control/window gate immediately before Popen.
        clocks=guard.guard()
        child=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
        start=birth(child.pid)
        write(H/'FINITE-STARTED.json',dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=start,argv=argv,fresh_guard_immediately_before_Popen=clocks,root_authority=ref(authority),no_custom_timeout=True,no_automatic_signals=True))
        print(json.dumps(dict(status='ORIGINAL_A3_FINITE_STARTED',pid=child.pid,starttime=start,clocks=clocks)),flush=True)
        # Popen retains the original child identity; explicit wait4 supplies the
        # genuine positive wait4 fact without introducing a timeout or a signal.
        waited,status,usage=os.wait4(child.pid,0)
        assert waited==child.pid
        code=os.waitstatus_to_exitcode(status);child.returncode=code
    members=[];errors=[]
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:
            fields=(path/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==child.pid:members.append(dict(pid=int(path.name),state=fields[0],group=int(fields[2])))
        except (FileNotFoundError,ProcessLookupError):pass
        except BaseException as error:errors.append(dict(pid=path.name,error=repr(error)))
    result=dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=start,returncode=code,positive_direct_wait4_join=True,wait4_returned_pid=waited,wait4_raw_status=status,CPU_seconds=usage.ru_utime+usage.ru_stime,maximum_RSS_KiB=usage.ru_maxrss,streams_closed=True,remaining_group_members=members,group_observation_errors=errors,process_group_absent=not members and not errors,stdout=ref(H/'finite.stdout'),stderr=ref(H/'finite.stderr'),automatic_retry=False)
    write(H/'FINITE-JOINED.json',result);print(json.dumps(result),flush=True)
    return code

if __name__=='__main__':
    try:code=main()
    except BaseException as error:
        write(H/'FINITE-OWNER-FAILURE.json',dict(scope=__doc__.splitlines()[0],error=repr(error),automatic_retry=False,instruction='Preserve exact original process handle/identity and evidence; no implicit retirement/retry.'))
        raise
    raise SystemExit(code)
