"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Fixture-only successor: accepted h990 cancellation ownership plus existing subreaper.
"""
import ctypes,json,os,signal,subprocess,time
from pathlib import Path
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}
class Owner:
    def __init__(self,output):
        self.output=Path(output);self.records=[];self.stopping=False;self.capture_total=0;self.retirement_started=None
        libc=ctypes.CDLL(None,use_errno=True)
        libc.prctl.argtypes=[ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong]
        if libc.prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'fixture subreaper admission')
        for sig in STOP_SIGNALS:signal.signal(sig,self.stop)
    def stop(self,signum,frame):
        if self.stopping:return
        self.retirement_started=time.monotonic()
        self.stopping=True;signal.setitimer(signal.ITIMER_REAL,0)
        raise InterruptedError('fixture owner signal '+str(signum))
    @staticmethod
    def terminal(process):
        # h990: WNOWAIT reserves creator PID/PGID until all group signals end.
        return os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None
    def wait_terminal(self,process,seconds,out,err,enforce_budget=True):
        end=time.monotonic()+seconds
        while not self.terminal(process):
            sizes=[os.fstat(f.fileno()).st_size for f in (out,err)]
            if enforce_budget and (max(sizes)>32<<20 or self.capture_total+sum(sizes)>64<<20):raise RuntimeError('fixture capture budget exceeded')
            if time.monotonic()>=end:return False
            time.sleep(0.01)
        return True
    def children(self):
        return [int(x) for x in (Path('/proc/self/task')/str(os.getpid())/'children').read_text().split()]
    def run(self,argv,env,cwd,timeout,label):
        if self.stopping:raise InterruptedError('fixture owner already stopped')
        process=None;error=None;retirement_error=None;reaped=[];killed=[];joined=False;rc=None;birth=None
        stdout=stderr=b'';started=time.monotonic()
        # Exclusive disk streams replace unbounded PIPE buffers. Enclosing reviewed
        # RLIMIT_FSIZE32MiB plus live32MiB-per-stream/64MiB-total checks apply.
        with (self.output/(label+'.stdout')).open('xb') as out,(self.output/(label+'.stderr')).open('xb') as err:
            try:
                previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
                try:
                    def restore_mask():signal.pthread_sigmask(signal.SIG_SETMASK,previous)
                    process=subprocess.Popen(argv,env=env,cwd=cwd,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=restore_mask)
                finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
                birth=int(Path('/proc/'+str(process.pid)+'/stat').read_text().rsplit(')',1)[1].split()[19])
                if not self.wait_terminal(process,timeout,out,err):raise subprocess.TimeoutExpired(argv,timeout)
            except BaseException as exc:error=type(exc).__name__+': '+str(exc)
            finally:
                previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
                retirement_started=self.retirement_started if self.retirement_started is not None else time.monotonic()
                retirement_deadline=retirement_started+6
                action_deadline=retirement_deadline-1 # reserve one second for FD close/fsync/receipts
                def remaining(cap):return max(0,min(cap,action_deadline-time.monotonic()))
                if error:self.stopping=True;signal.setitimer(signal.ITIMER_REAL,0)
                try:
                    if process is not None:
                        # h990: no group action is allowed after direct wait.
                        if error:
                            self.terminal(process)
                            try:os.killpg(process.pid,signal.SIGTERM)
                            except ProcessLookupError:pass
                            if not self.wait_terminal(process,remaining(1.5),out,err,False):
                                try:os.killpg(process.pid,signal.SIGKILL)
                                except ProcessLookupError:pass
                                if not self.wait_terminal(process,remaining(1.5),out,err,False):raise RuntimeError('owned creator termination UNKNOWN')
                        if not self.terminal(process):raise RuntimeError('direct creator not terminal; retirement UNKNOWN')
                        rc=process.wait(timeout=remaining(0.25));joined=True
                    # Existing subreaper behavior retained for PTY peers which
                    # escaped creator session. Only unreaped direct children may
                    # be signalled; each is rechecked immediately before signal.
                    while True:
                        children=self.children()
                        if not children:break
                        if time.monotonic()>=action_deadline:raise RuntimeError('shared retirement action deadline exhausted; descendant join UNKNOWN')
                        for child in children:
                            got,status=os.waitpid(child,os.WNOHANG)
                            if got:reaped.append({'pid':got,'status':status});continue
                            os.kill(child,signal.SIGKILL);killed.append(child)
                        if time.monotonic()>=action_deadline:raise RuntimeError('whole-descendant retirement UNKNOWN; shared deadline exhausted')
                        time.sleep(min(0.01,max(0,action_deadline-time.monotonic())))
                except BaseException as exc:retirement_error=type(exc).__name__+': '+str(exc)
                finally:
                    out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno())
                    self.capture_total+=os.fstat(out.fileno()).st_size+os.fstat(err.fileno()).st_size
                    row={'label':label,'leader':process.pid if process else None,'birth':birth,'status':rc,'timed_out':isinstance(error,str) and error.startswith('TimeoutExpired:'),'error':error,'retirement_error':retirement_error,'direct_child_joined':joined,'adopted_reaps':reaped,'adopted_kills':killed,'whole_descendants_joined':retirement_error is None and not self.children(),'capture_total':self.capture_total,'seconds':time.monotonic()-started,'retirement_started':retirement_started,'retirement_deadline':retirement_deadline,'retirement_action_deadline':action_deadline,'status_kind':'FAIL' if error or retirement_error or killed else 'COMPLETE'}
                    self.records.append(row)
                    # Additive durable receipt per child survives cancellation.
                    with (self.output/(label+'.ownership.json')).open('x') as f:json.dump(row,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
                    try:
                        out.close();err.close()
                        if time.monotonic()>=retirement_deadline:
                            retirement_error=(retirement_error or '')+'; shared six-second retirement/receipt deadline exceeded'
                        closed=dict(row,closed_streams=True,retirement_error=retirement_error,retirement_seconds=time.monotonic()-retirement_started,status_kind='FAIL' if error or retirement_error or killed else 'COMPLETE')
                        with (self.output/(label+'.closed.json')).open('x') as f:json.dump(closed,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
                        if time.monotonic()>=retirement_deadline:raise RuntimeError('shared six-second durable receipt deadline exceeded; no success claim')
                    finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
        if error or retirement_error or killed:raise RuntimeError(label+' failed; ownership/captures retained; no retry: '+str((error,retirement_error,killed)))
        if self.capture_total>64<<20:raise RuntimeError('fixture aggregate capture bound exceeded')
        stdout=(self.output/(label+'.stdout')).read_bytes();stderr=(self.output/(label+'.stderr')).read_bytes()
        return subprocess.CompletedProcess(argv,rc,stdout,stderr)
