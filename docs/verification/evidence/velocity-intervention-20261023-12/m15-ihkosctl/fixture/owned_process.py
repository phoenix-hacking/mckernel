"""Host-fixture process ownership only; loaded after explicit execution grant.
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
        timed_out=False
        try:stdout,stderr=p.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out=True
            try:os.killpg(p.pid,signal.SIGKILL)
            except ProcessLookupError:pass
            stdout,stderr=p.communicate(timeout=3)
        # PTY peers create their own sessions. Once their wrapper exits, any
        # surviving descendant is adopted by this helper. Signal only unreaped
        # direct children, whose numeric PIDs cannot have been reused.
        deadline=time.monotonic()+3;reaped=[];killed=[]
        children_file=Path('/proc/self/task')/str(os.getpid())/'children'
        while True:
            children=[int(x) for x in children_file.read_text().split()]
            if not children:break
            for child in children:
                got,status=os.waitpid(child,os.WNOHANG)
                if got:reaped.append({'pid':got,'status':status});continue
                os.kill(child,signal.SIGKILL);killed.append(child)
            if time.monotonic()>deadline:raise RuntimeError('whole-descendant retirement UNKNOWN; retain owner and stop')
            time.sleep(0.01)
        (self.output/(label+'.stdout')).write_bytes(stdout)
        (self.output/(label+'.stderr')).write_bytes(stderr)
        self.records.append({'label':label,'leader':p.pid,'status':p.returncode,'timed_out':timed_out,'adopted_reaps':reaped,'adopted_kills':killed,'whole_descendants_joined':True})
        (self.output/'ownership.json').write_text(json.dumps(self.records,indent=2)+'\n')
        if timed_out:raise RuntimeError(label+' timed out; original captures retained, no retry')
        if killed:raise RuntimeError(label+' left a live adopted descendant; retired and failed, no retry')
        return subprocess.CompletedProcess(argv,p.returncode,stdout,stderr)
