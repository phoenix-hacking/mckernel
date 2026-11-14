"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Ordinary direct-parent capture for one independently released postjoin observer.
"""
import argparse,hashlib,json,os,pathlib,resource,subprocess,time

def reference(path):
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def identity(pid):
    fields=pathlib.Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
    return dict(pid=pid,birth=int(fields[19]),ppid=int(fields[1]),pgrp=int(fields[2]),sid=int(fields[3]))

def child_limits():
    os.sched_setaffinity(0,{0})
    for kind,value in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,60),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:
        resource.setrlimit(kind,(value,value))

def group_members(group):
    # Preserve the existing backend's missing-stat semantics; all other errors
    # remain explicit and prevent a positive group-retirement assertion.
    members=[];errors=[]
    try:
        for path in pathlib.Path('/proc').glob('[0-9]*/stat'):
            try:
                fields=path.read_text().rsplit(')',1)[1].split()
                if len(fields)<=2:raise ValueError('short process stat')
                if int(fields[2])==group:members.append(int(path.parent.name))
            except FileNotFoundError:continue
            except (PermissionError,ValueError,IndexError) as error:errors.append(dict(path=str(path),error=repr(error)))
    except (FileNotFoundError,PermissionError) as error:errors.append(dict(path='/proc',error=repr(error)))
    return sorted(members),errors

parser=argparse.ArgumentParser();parser.add_argument('--release',type=pathlib.Path,required=True);parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
rr=reference(args.release.resolve());assert rr['sha256']==args.release_sha256
release=json.loads(args.release.read_text());assert release['author']=='/root' and release['decision']=='AUTHORIZE_ONE_ROOT64_CURRENT118_POSTJOIN_READONLY_CAPTURE' and release['maximum_invocations']==1 and release['independent_execution_review']
source=pathlib.Path(release['source']['path']);assert reference(source)==release['source']
output=pathlib.Path(release['output']);assert not output.parent.exists()
capture=output.parent.parent/'actual-postjoin-parent-root1';capture.mkdir(mode=0o700)
argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(source),'--bindings',release['bindings']['path'],'--release',str(args.release.resolve()),'--release-sha256',rr['sha256'],'--output',str(output)]
parent=identity(os.getpid());started=time.monotonic()
with (capture/'stdout').open('xb') as stdout,(capture/'stderr').open('xb') as stderr:
    child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,preexec_fn=child_limits,start_new_session=True)
    actor=identity(child.pid)
    (capture/'STARTED.json').write_text(json.dumps(dict(parent=parent,child=actor,argv=argv,release=rr,epoch=time.time()),indent=2)+'\n')
    pid,status,usage=os.wait4(child.pid,0);assert pid==child.pid
    code=os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
    child.returncode=code
members,errors=group_members(child.pid)
value=dict(scope=__doc__.splitlines()[0],author='/root',pid=actor['pid'],birth=actor['birth'],starttime=actor['birth'],parent_pid=parent['pid'],parent_birth=parent['birth'],parent=parent,child=actor,argv=argv,release=rr,returncode=code,wait4_pid=pid,wait4_status=status,positive_wait4_join=True,positive_direct_parent_wait=True,positive_direct_wait_join=True,parent_streams_closed=stdout.closed and stderr.closed,streams_closed=stdout.closed and stderr.closed,process_group_absent=not members and not errors,remaining_group_members=members,group_observation_errors=errors,signals_sent=0,wall_seconds=time.monotonic()-started,user_cpu_seconds=usage.ru_utime,system_cpu_seconds=usage.ru_stime,peak_rss_kib=usage.ru_maxrss,finished_epoch=time.time(),stdout=reference(capture/'stdout'),stderr=reference(capture/'stderr'),current_free=False)
(capture/'DIRECT-PARENT-JOIN.ACTUAL.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
print(json.dumps(value,indent=2));raise SystemExit(code)
