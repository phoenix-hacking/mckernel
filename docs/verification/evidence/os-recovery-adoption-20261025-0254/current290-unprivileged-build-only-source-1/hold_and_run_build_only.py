"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One root-granted ordinary postcleanup27:4 holder; capture birth/FD before execution review.
Never native cleanup, replay, broad Docker queries, signals or arbitrary command execution.
"""
import argparse,fcntl,importlib.util,json,os,stat,subprocess,time
from pathlib import Path
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('exact_build_only_runner',D/'run_build_only.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def write(path,value):
    with Path(path).open('x') as stream:
        stream.write(json.dumps(value,indent=2)+'\n');stream.flush();os.fsync(stream.fileno())
def birth(pid):return int((Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()[19])
def lock_is_held(raw,holder):
    token='%02x:%02x:%d'%(os.major(holder['device']),os.minor(holder['device']),holder['inode'])
    return any(len(v)>=8 and v[1:4]==['FLOCK','ADVISORY','WRITE'] and v[4]==str(holder['pid']) and v[5]==token and v[6:8]==['0','EOF'] for v in (line.split() for line in raw.splitlines()))
def releasable(output,runner_joined):
    # A joined exact runner without a launch claim never called Docker.
    if not runner_joined:return False
    if not (output/'claim.json').exists():return True
    if not (output/'terminal.json').exists():return False
    t=r.read(output/'terminal.json');cid=(output/'container.cid').read_text().strip()
    return t['container']==cid and len(cid)==64 and t['state']['Running'] is False and t['state']['Pid']==0

def run(bootstrap_path):
    r.require(os.getuid()==os.geteuid()==1000,'ordinary UID1000 holder/runner required')
    b=r.read(bootstrap_path);p=r.read(D/'PROFILE.SOURCE-ONLY.json')
    r.require(b['author']=='/root' and b['decision']=='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER' and b['maximum_invocations']==1,'new exact holder-only root grant')
    r.require(b['source']==r.reference(__file__) and b['runner']==r.reference(D/'run_build_only.py') and b['worker']==r.reference(D/'build_only_worker.py') and b['profile']==r.reference(D/'PROFILE.SOURCE-ONLY.json'),'exact published source closure')
    # Ordinary read-only FD/flock preparation only. One independent actual build
    # review follows HOLDER.READY and remains mandatory before any Docker call.
    r.require(b['native_custody_clearance']==p['native_custody_clearance'],'accepted current postcleanup proof only');r.auth(b['native_custody_clearance'])
    r.require(time.time()<r.DEADLINE,'fixed campaign deadline')
    handshake=r.strict_parent(b['fresh_handshake_root']);r.require(not os.path.lexists(handshake),'fresh exclusive handshake namespace')
    mutex=r.strict_parent(b['permanent_mutex_path']);st=mutex.lstat()
    r.require(stat.S_ISREG(st.st_mode) and (st.st_dev,st.st_ino)==(27,4),'same permanent27:4; no replacement')
    fd=os.open(mutex,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    acquired=False;joined=False;child_started=False;output=None;can_release=True
    try:
        r.require((os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(27,4),'opened same permanent27:4')
        # Never block, retire a holder or interpret a busy mutex as admission.
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB);acquired=True
        r.require((mutex.lstat().st_dev,mutex.lstat().st_ino)==(27,4),'unchanged path after sole acquisition')
        holder=dict(path=str(mutex),pid=os.getpid(),starttime=birth(os.getpid()),device=27,inode=4,fd=fd)
        r.require(lock_is_held(Path('/proc/locks').read_text(),holder),'actual holder full-EOF kernel row')
        handshake.mkdir(mode=0o700)
        ready=dict(status='ACTUAL_ONE_HEAVY_27_4_HELD_NOT_BUILD_ADMISSION',scope=p['scope'],nonce=b['nonce'],holder=holder,source=r.reference(__file__),bootstrap=r.reference(bootstrap_path),native_custody_clearance=b['native_custody_clearance'],deadline_epoch=r.DEADLINE)
        write(handshake/'HOLDER.READY.json',ready)
        # Root now binds actual holder/resource facts and independent exact build review.
        # No inference, Docker action, query or build occurs while waiting.
        until=min(r.DEADLINE,time.time()+1200);go=handshake/'ROOT-BUILD-GRANT.READY.json'
        while not go.exists():
            r.require(time.time()<until,'unlaunched holder wait expired before new actual build grant')
            time.sleep(0.25)
        g=r.read(go);r.require(g['author']=='/root' and g['nonce']==b['nonce'],'same root grant-ready identity')
        gp=r.auth(g['grant']);grant=r.read(gp);r.require(grant['nonce']==b['nonce'],'same actual one-heavy build nonce')
        resources=r.read(r.auth(grant['resource_authority']))
        r.require(resources['reservation_ready_record']==r.reference(handshake/'HOLDER.READY.json') and resources['reservation_holder']==holder,'actual same wrapper reservation proof')
        output=r.strict_parent(grant['fresh_output_root']);r.require(not os.path.lexists(output),'fresh exact build output')
        argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(D/'run_build_only.py'),'--execute',str(gp)]
        # The held FD is CLOEXEC; only this parent owns custody through the full join.
        with (handshake/'runner.stdout').open('xb') as stdout,(handshake/'runner.stderr').open('xb') as stderr:
            child=subprocess.Popen(argv,stdout=stdout,stderr=stderr,close_fds=True);child_started=True;can_release=False
            try:child_birth=birth(child.pid)
            except FileNotFoundError:child_birth=None
            write(handshake/'RUNNER.STARTED.json',dict(pid=child.pid,starttime=child_birth,argv=argv))
            code=child.wait();joined=True
        write(handshake/'RUNNER.JOINED.json',dict(pid=child.pid,starttime=child_birth,returncode=code,joined=True))
        can_release=releasable(output,joined)
        r.require(can_release,'container custody uncertain; holder remains quarantined for root reconciliation')
        write(handshake/'BUILD-LOCAL-TERMINAL.json',dict(returncode=code,joined=True,container_terminal_or_no_launch=True,holder=holder))
        return code
    except BaseException as error:
        if child_started and not can_release:
            if handshake.exists() and not (handshake/'QUARANTINE.json').exists():
                write(handshake/'QUARANTINE.json',dict(error=repr(error),holder_pid=os.getpid(),holder_starttime=birth(os.getpid()),holder_fd=fd,runner_joined=joined,instruction='Preserve exact27:4 custody; root reconciles actual build-only child/container without replay.'))
            while True:
                try:time.sleep(0.5)
                except BaseException:pass
        raise
    finally:
        if can_release:os.close(fd)
        # No explicit unlock of any inherited/native holder and no cleanup/replacement.

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--bootstrap-grant',required=True);args=parser.parse_args();raise SystemExit(run(Path(args.bootstrap_grant)))
