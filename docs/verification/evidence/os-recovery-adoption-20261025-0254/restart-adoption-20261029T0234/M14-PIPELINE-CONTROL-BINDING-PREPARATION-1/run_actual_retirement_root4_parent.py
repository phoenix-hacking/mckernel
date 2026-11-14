"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Direct parent capture for the independently released single stopped-container retirement.
"""
import hashlib,json,os,pathlib,resource,subprocess,time
D=pathlib.Path(__file__).resolve().parent

def birth(pid):
    f=pathlib.Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'birth':int(f[19]),'ppid':int(f[1]),'pgrp':int(f[2]),'sid':int(f[3])}

def limits():
    os.sched_setaffinity(0,{0})
    for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:
        resource.setrlimit(k,(v,v))

def ref(p):
    b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())

release=D/'ROOT-CURRENT118-NORMAL-RETIREMENT.ROOT4.ACTUAL.json'
rr=ref(release)
r=json.loads(release.read_text())
assert r['execution_review'] and r['decision']=='GRANT_ONE_EXACT_STOPPED_CURRENT118_CONTAINER_RETIREMENT'
capture=D/'ACTUAL-RETIREMENT-ROOT4-PARENT'
capture.mkdir(mode=0o700)
argv=['/usr/bin/python3','-I','-B',r['files']['executor']['path'],'--release',str(release),'--release-sha256',rr['sha256'],'--execute']
started=time.monotonic();parent=birth(os.getpid())
with (capture/'stdout').open('xb') as stdout,(capture/'stderr').open('xb') as stderr:
    child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,preexec_fn=limits,start_new_session=True)
    identity=birth(child.pid)
    (capture/'STARTED.json').write_text(json.dumps(dict(parent=parent,child=identity,argv=argv,epoch=time.time(),release=rr),indent=2)+'\n')
    pid,status,usage=os.wait4(child.pid,0)
    assert pid==child.pid
    rc=os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
    child.returncode=rc
result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',parent=parent,child=identity,argv=argv,positive_direct_parent_wait=True,positive_wait4_join=True,wait4_pid=pid,wait4_status=status,returncode=rc,streams_closed=stdout.closed and stderr.closed,signals_sent=0,wall_seconds=time.monotonic()-started,user_cpu_seconds=usage.ru_utime,system_cpu_seconds=usage.ru_stime,peak_rss_kib=usage.ru_maxrss,finished_epoch=time.time(),stdout=ref(capture/'stdout'),stderr=ref(capture/'stderr'),release=rr,native_clearance=False)
(capture/'DIRECT-PARENT-JOIN.ACTUAL.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(rc)
