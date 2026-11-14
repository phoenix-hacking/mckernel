"""Host-fixture owned-child retirement only; imported after explicit execution grant.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import ctypes,json,os,signal,subprocess,time
from pathlib import Path
class Owner:
    def __init__(self, output):
        self.output=Path(output);self.records=[]
        libc=ctypes.CDLL(None,use_errno=True)
        libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
        if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'fixture subreaper admission')
    def run(self,argv,env,cwd,timeout,label):
        p=subprocess.Popen(argv,env=env,cwd=cwd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
        stdout=b'';stderr=b'';timed_out=False;leader_joined=False;birth=None
        reaped=[];killed=[];error=None;group_signalled=False
        try:
            try:
                birth=Path('/proc/'+str(p.pid)+'/stat').read_text().rsplit(') ',1)[1].split()[19]
                stdout,stderr=p.communicate(timeout=timeout)
                leader_joined=p.returncode is not None
            except BaseException as exc:
                error=exc;timed_out=isinstance(exc,subprocess.TimeoutExpired)
                if timed_out:stdout=exc.output or b'';stderr=exc.stderr or b''
            # After communicate fails, the leader is still our unreaped child.
            # Never poll/reap it before this exact original session signal.
            deadline=time.monotonic()+6
            def left():
                value=deadline-time.monotonic()
                if value<=0:raise TimeoutError('six-second retirement envelope exhausted')
                return value
            if error is not None and p.returncode is None:
                try:os.killpg(p.pid,signal.SIGKILL);group_signalled=True
                except ProcessLookupError:pass
            if not leader_joined:
                # Join before pipe drainage: adopted setsid peers can retain pipes.
                p.wait(timeout=left());leader_joined=True
            children_file=Path('/proc/self/task')/str(os.getpid())/'children'
            while True:
                children=[int(x) for x in children_file.read_text().split()]
                if not children:break
                left()
                for child in children:
                    # This sole-threaded owner has not reaped this direct child.
                    # A successful WNOHANG=0 protects its PID until our next reap.
                    got,status=os.waitpid(child,os.WNOHANG)
                    if got:reaped.append({'pid':got,'status':status});continue
                    try:os.kill(child,signal.SIGKILL);killed.append(child)
                    except ProcessLookupError:pass
                time.sleep(min(0.01,left()))
            if error is not None:
                # Python3.8 communicate retries retain accumulated output bytes.
                stdout,stderr=p.communicate(timeout=left())
        except BaseException as exc:
            # No false join/current-free claim if any child retirement is uncertain.
            error=exc
        finally:
            for stream in (p.stdin,p.stdout,p.stderr):
                if stream is not None and not stream.closed:stream.close()
            children_file=Path('/proc/self/task')/str(os.getpid())/'children'
            remaining=[int(x) for x in children_file.read_text().split()]
            (self.output/(label+'.stdout')).write_bytes(stdout)
            (self.output/(label+'.stderr')).write_bytes(stderr)
            record={'label':label,'leader':p.pid,'leader_birth':birth,'status':p.returncode if leader_joined else 'UNKNOWN','leader_parent_joined':leader_joined,'timed_out':timed_out,'leader_group_signalled':group_signalled,'adopted_reaps':reaped,'adopted_kills':killed,'whole_descendants_joined':leader_joined and not remaining,'remaining_direct_children':remaining,'streams_closed':all(s is None or s.closed for s in (p.stdin,p.stdout,p.stderr)),'error':None if error is None else type(error).__name__+': '+str(error)}
            self.records.append(record)
            (self.output/'ownership.json').write_text(json.dumps(self.records,indent=2)+'\n')
        if error is not None:raise RuntimeError(label+' failed; captures retained, no retry: '+str(error)) from error
        if killed:raise RuntimeError(label+' left a live adopted descendant; retired and failed, no retry')
        if not record['whole_descendants_joined']:raise RuntimeError(label+' retirement UNKNOWN; stop, no retry')
        return subprocess.CompletedProcess(argv,p.returncode,stdout,stderr)
