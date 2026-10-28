"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Own exactly one authorized original CURRENT118 finite verifier; no timeout or signals.
"""
from pathlib import Path
import importlib.util
import json
import os
import resource
import subprocess
import sys

H=Path(__file__).resolve().parent
sys.path.insert(0,str(H))
from review_static_correction1 import ref,auth,checked,read

def write(path,value):
    with path.open('x') as stream:
        json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())

def birth(pid):return int(Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()[19])

def main():
    assert os.getuid()==os.geteuid()==1000
    authority=H/'ROOT-REVIEWER-EXECUTION-AUTHORITY.json'
    assert ref(authority)==dict(path=str(authority),bytes=7960,sha256='78296ed3e7fe39b6c3071010c50a13fd8177103ab1ace000f771449b69d18f3c')
    grant=read(authority);release=checked(grant['prepared_release'])
    assert grant['author']=='/root' and grant['decision']=='AUTHORIZE_ONE_ORIGINAL_INDEPENDENT_CURRENT118_FINITE_REVIEW_PROCESS'
    assert grant['maximum_invocations']==1 and grant['reviewer']=='/root/observerreview'
    assert grant['nonce']==release['nonce']=='1d3f2239b2884cedbd9e7dbe248ae1aa'
    b=checked(release['bindings']);refs=b['static_refs']
    for row in refs.values():auth(row)
    command=grant['commands'][0];assert command==release['commands'][0] and command['owner']=='/root/observerreview'
    argv=command['argv'];assert argv[3]==refs['finite_verifier']['path']
    assert b['actual_execution_authority'] is None and refs['finite_verifier']['sha256']=='eacd859b938a70e6a07ed562ff07cd6377fc8314b3b14683ee441322d4de443e'
    for name in ['PREWARM_READY.json','FINITE-STARTED.json','INDEPENDENT-FINITE-REVIEW.PASS.json']:
        assert not os.path.lexists(H/name)
    spec=importlib.util.spec_from_file_location('independent118_exact_runner_prestart',auth(refs['runner']))
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    os.sched_setaffinity(0,{0});resource.setrlimit(resource.RLIMIT_AS,(2<<30,2<<30))
    assert os.sched_getaffinity(0)=={0}
    write(H/'FINITE-ONCE-CLAIM.json',dict(scope=__doc__.splitlines()[0],reviewer='/root/observerreview',nonce=b['nonce'],argv=argv,root_authority=ref(authority),release=grant['prepared_release'],wrapper=ref(__file__),profile=command['enforced_profile']))
    with (H/'finite.stdout').open('xb') as out,(H/'finite.stderr').open('xb') as err:
        # No report/file operation between the actual fresh guard and Popen.
        clocks=runner.current_operation_guard()
        child=subprocess.Popen(argv,stdout=out,stderr=err,start_new_session=True)
        start=birth(child.pid)
        actual_limit=next(line for line in Path('/proc',str(child.pid),'limits').read_text().splitlines() if line.startswith('Max address space'))
        write(H/'FINITE-STARTED.json',dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=start,argv=argv,affinity=sorted(os.sched_getaffinity(child.pid)),AS_bytes=2<<30,actual_AS_limit=actual_limit,fresh_guard_immediately_before_Popen=clocks,root_authority=ref(authority),automatic_timeout=False,automatic_kill=False))
        print(json.dumps(dict(status='ORIGINAL_CURRENT118_FINITE_STARTED',pid=child.pid,starttime=start,clocks=clocks)),flush=True)
        code=child.wait()
    members=[];errors=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():continue
        try:
            fields=(p/'stat').read_text().rsplit(')',1)[1].split()
            if int(fields[2])==child.pid:members.append(dict(pid=int(p.name),state=fields[0],group=int(fields[2])))
        except (FileNotFoundError,ProcessLookupError):pass
        except BaseException as error:errors.append(dict(pid=p.name,error=repr(error)))
    result=dict(scope=__doc__.splitlines()[0],pid=child.pid,starttime=start,returncode=code,positive_direct_wait_join=True,streams_closed=True,remaining_group_members=members,group_observation_errors=errors,process_group_absent=not members and not errors,stdout=ref(H/'finite.stdout'),stderr=ref(H/'finite.stderr'),automatic_retry=False)
    write(H/'FINITE-JOINED.json',result);print(json.dumps(result),flush=True)
    return code

if __name__=='__main__':
    try:code=main()
    except BaseException as error:
        write(H/'FINITE-OWNER-FAILURE.json',dict(scope=__doc__.splitlines()[0],error=repr(error),automatic_retry=False,instruction='Preserve actual process identity, original handles and all evidence; no implicit retirement or retry.'))
        raise
    raise SystemExit(code)
