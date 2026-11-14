"""One real UID1000 fork for the pinned DeferredFork child restore path.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
No signals are sent to any PID or process group by this program.
"""
import hashlib
import json
import os
import resource
import select
import signal
import stat
import sys
import time
import types

BASE='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1'
PACKAGE=BASE+'/root-install-source-10/package'
PINS=(('ownership_latch','fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390'),
      ('graph_observations','df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed'),
      ('pidfd_compat','068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'),
      ('pidfd_custody','3b22cac50183723456e6701031f00bdc446c04641c08c5864f1a379b5407686e'),
      ('deferred_fork','b28d2f3483fb90c858479b65c9cebe6bd1b586c01902f004ec44964da6b4625f'))
STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT)


def source(name,expected):
    path=PACKAGE+'/'+name+'.py'
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>2097152:raise ValueError('source type/size')
        raw=b''
        while len(raw)<=2097152:
            part=os.read(fd,min(65536,2097153-len(raw)))
            if not part:break
            raw+=part
        after=os.fstat(fd)
        if ((before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=
            (after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns) or
            len(raw)!=before.st_size or hashlib.sha256(raw).hexdigest()!=expected):raise ValueError('source binding')
    finally:
        os.close(fd)  # single attempt; never retry an ambiguous descriptor
    module=types.ModuleType(name);module.__file__=path;sys.modules[name]=module
    exec(compile(raw,path,'exec'),module.__dict__)
    return module


def line(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def close_once(fd,outcomes,label):
    row={'label':label,'historical_fd':fd,'state':'CLOSING'};outcomes.append(row)
    try:os.close(fd)
    except BaseException:
        row['state']='CLOSE_UNKNOWN'
        raise
    row['state']='CLOSED'


def main():
    if os.getuid()!=1000 or os.geteuid()!=1000:raise ValueError('UID1000 required')
    if os.sched_getaffinity(0)!={6}:raise ValueError('CPU6 profile required')
    if (resource.getrlimit(resource.RLIMIT_AS)[0]!=536870912 or resource.getrlimit(resource.RLIMIT_CPU)[0]!=30 or
        resource.getrlimit(resource.RLIMIT_NOFILE)[0]!=128 or resource.getrlimit(resource.RLIMIT_CORE)[0]!=0):
        raise ValueError('exact ordinary light limits required')
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0) or signal.SIGALRM in signal.pthread_sigmask(signal.SIG_BLOCK,()):
        raise ValueError('unexpected inherited alarm or mask')
    modules={name:source(name,digest) for name,digest in PINS}
    deferred=modules['deferred_fork'];ownership=modules['ownership_latch']
    result_r,result_w=os.pipe2(os.O_CLOEXEC)
    gate_r,gate_w=os.pipe2(os.O_CLOEXEC)
    outcomes=[];latch=ownership.CustodyLatch('PROBE_OWNED');record=latch.reserve_child('probe',result_r,result_w,gate_r,gate_w)
    parent_pid=os.getpid();saved={};stop={'raised':False};expected_mask=None
    start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);deadline=start+20000000000
    def on_stop(signum,frame):
        if not stop['raised']:
            stop['raised']=True
            raise InterruptedError('configured stop received')
    def child_report(value):
        raw=line(value)
        if len(raw)>4096 or os.write(result_w,raw)!=len(raw):raise OSError('probe report short')
    class ReportingGuard(deferred.DeferredFork):
        # Test-only reporting around the unchanged production implementation.
        def _restore(self,child):
            try:return super()._restore(child)
            except BaseException as error:
                if child:
                    try:child_report({'stage':'RESTORE_ERROR','error_class':type(error).__name__,
                                      'errno':error.errno if isinstance(error,OSError) and type(error.errno) is int else None,
                                      'pid':os.getpid(),'ppid':os.getppid()})
                    except BaseException:pass
                raise
    def callback():
        try:
            mask=signal.pthread_sigmask(signal.SIG_BLOCK,())
            handlers=all(signal.getsignal(sig) is on_stop for sig in STOPS)
            child_report({'stage':'CALLBACK_AFTER_RESTORE','pid':os.getpid(),'ppid':os.getppid(),
                          'mask':sorted(int(sig) for sig in mask),'handlers_restored':handlers})
            poll=select.poll();poll.register(gate_r,select.POLLIN|select.POLLHUP|select.POLLERR)
            if not poll.poll(10000) or os.read(gate_r,1)!=b'G':os._exit(2)
            os._exit(0)
        except BaseException as error:
            try:child_report({'stage':'CALLBACK_ERROR','error_class':type(error).__name__,
                              'errno':error.errno if isinstance(error,OSError) and type(error.errno) is int else None,
                              'pid':os.getpid(),'ppid':os.getppid()})
            except BaseException:pass
            os._exit(2)
    guard_error=None;child_pid=None;child_fd=None;child_birth=None
    original_mask=signal.pthread_sigmask(signal.SIG_BLOCK,())
    try:
        for sig in STOPS+(signal.SIGALRM,):
            saved[sig]=signal.getsignal(sig);signal.signal(sig,on_stop)
        signal.setitimer(signal.ITIMER_REAL,20)
        alarm_old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGALRM,))
        try:
            expected_mask=signal.pthread_sigmask(signal.SIG_BLOCK,())
            try:
                with ReportingGuard() as guard:
                    child_pid,child_fd,child_birth=guard.fork_and_pin(record,callback)
            except BaseException as error:
                guard_error={'class':type(error).__name__,'errno':error.errno if isinstance(error,OSError) and type(error.errno) is int else None}
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,alarm_old)
        close_once(result_w,outcomes,'parent-result-writer')
        close_once(gate_r,outcomes,'parent-gate-reader')
        poll=select.poll();poll.register(result_r,select.POLLIN|select.POLLHUP|select.POLLERR)
        content=b''
        while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<deadline and b'\n' not in content:
            events=poll.poll(100)
            if not events:continue
            chunk=os.read(result_r,4097-len(content))
            if not chunk:break
            content+=chunk
            if len(content)>4096:raise ValueError('probe record too long')
        event=json.loads(content) if content.endswith(b'\n') and content.count(b'\n')==1 else None
        if event is not None and event.get('stage')=='CALLBACK_AFTER_RESTORE':
            if os.write(gate_w,b'G')!=1:raise OSError('gate write short')
        close_once(gate_w,outcomes,'parent-gate-writer')
        close_once(result_r,outcomes,'parent-result-reader')
        if child_pid is None:child_pid=record.pid
        if child_fd is None and type(record.birth) is str and record.birth.isdigit():child_fd=record.pidfd;child_birth=record.birth
        terminal=False;status=None
        if type(child_pid) is int and child_pid>0:
            if type(child_fd) is int and child_fd>=0:
                with open('/proc/self/fdinfo/%d'%child_fd) as stream:info=stream.read(8193)
                rows=[x.split(':',1)[1].strip() for x in info.splitlines() if x.startswith('Pid:')]
                if len(info)>8192 or rows!=[str(child_pid)]:raise ValueError('verified pidfd identity differs')
                p=select.poll();p.register(child_fd,select.POLLIN|select.POLLHUP|select.POLLERR)
                while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<deadline:
                    events=p.poll(100)
                    if events:
                        mask=events[0][1]
                        if mask&(select.POLLERR|select.POLLNVAL):raise OSError('pidfd poll failure')
                        if mask&(select.POLLIN|select.POLLHUP):terminal=True;break
            while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<deadline:
                waited,value=os.waitpid(child_pid,os.WNOHANG)
                if waited==child_pid:status=value;break
                time.sleep(.05)
        if child_fd is not None:close_once(child_fd,outcomes,'verified-child-pidfd')
        restored=(event is not None and event.get('stage')=='CALLBACK_AFTER_RESTORE' and
                  event.get('pid')==child_pid and event.get('ppid')==parent_pid and
                  event.get('mask')==sorted(int(sig) for sig in expected_mask) and event.get('handlers_restored') is True)
        complete=guard_error is None and terminal and type(status) is int and os.WIFEXITED(status) and os.WEXITSTATUS(status)==0 and restored
        report={'status':'PASS_RESTORE_OBSERVED' if complete else 'UNKNOWN_OR_RESTORE_FAILURE',
                'guard_error':guard_error,'child_event':event,'child_pid':child_pid,'child_birth':child_birth,
                'pidfd_terminal':terminal,'direct_wait_status':status,'parent_mask_before_guard':sorted(int(sig) for sig in expected_mask),
                'close_outcomes':outcomes,'native_release':False,'native_currentfree':None}
        raw=line(report)
        if os.write(1,raw)!=len(raw):raise OSError('probe output short')
        if not complete:raise RuntimeError('probe did not prove restore and terminal')
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.pthread_sigmask(signal.SIG_SETMASK,original_mask)
        for sig,handler in saved.items():signal.signal(sig,handler)


if __name__=='__main__':main()
