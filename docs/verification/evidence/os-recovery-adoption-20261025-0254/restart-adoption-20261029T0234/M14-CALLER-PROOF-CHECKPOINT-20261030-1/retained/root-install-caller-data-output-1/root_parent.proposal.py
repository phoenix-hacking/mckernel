"""Functional M14 install-only direct root parent; no security testing.

Loaded only by a separately reviewed fixed-source bootstrap. No work on import.
The loaded direct_entry and direct_completion must be the exact verified modules
in the admitted source closure; a hash supplied as data is not admission.
"""
import hashlib
import json
import data_output
import fcntl
import contextlib
import os
import select
import signal
import socket
import stat
import threading
import time

import deferred_fork
import direct_entry
import direct_completion
import ownership_latch
import parent_control as ipc
import pidfd_compat


class Unknown(RuntimeError):pass


@contextlib.contextmanager
def alarm_deferred():
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGALRM,))
    try:yield
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def receive_owned(sock,caps,held,keeper_pid):
    with alarm_deferred():
        return ipc.receive(sock,caps,held,keeper_pid)


def process(pid):
    text=open('/proc/%d/stat'%pid,'r').read(8192)
    fields=text.rsplit(')',1)[1].split()
    if len(fields)<20 or fields[0] in ('Z','X','x'):raise ValueError('process not live')
    return {'pid':pid,'parent':int(fields[1]),'pgrp':int(fields[2]),'birth':fields[19]}


def pidfd_pid(fd):
    with open('/proc/self/fdinfo/%d'%fd,'r') as stream:
        data=stream.read(8193)
    if len(data)>8192:raise ValueError('pidfd info bound')
    rows=[line.split(':',1)[1].strip() for line in data.splitlines() if line.startswith('Pid:')]
    if len(rows)!=1 or not rows[0].isdigit():raise ValueError('pidfd identity')
    return int(rows[0])


def exact(frame,expected):
    if ipc.canonical(frame)!=ipc.canonical(expected):raise ValueError('unexpected exact frame')


def lease_identity(fd):
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600:
        raise ValueError('lease identity/mode')
    return {'device':st.st_dev,'inode':st.st_ino}


def ready_parent_socket(sock,keeper_fd,caps):
    poll=select.poll();poll.register(sock.fileno(),select.POLLIN|select.POLLHUP|select.POLLERR)
    poll.register(keeper_fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while True:
        left=ipc.remaining(caps)
        if left<=0:raise TimeoutError('custody handoff cap')
        for fd,events in poll.poll(min(100,max(1,left//1000000))):
            if fd==keeper_fd:raise Unknown('keeper terminal before custody handoff')
            if events&(select.POLLERR|select.POLLHUP|select.POLLNVAL):raise Unknown('custody channel lost')
            if events&select.POLLIN:return


def terminal(pidfd):
    poll=select.poll();poll.register(pidfd,select.POLLIN|select.POLLHUP|select.POLLERR)
    events=poll.poll(0)
    if not events:return False
    mask=events[0][1]
    if mask&(select.POLLERR|select.POLLNVAL):raise Unknown('pidfd poll error')
    return bool(mask&(select.POLLIN|select.POLLHUP))


def stop_owned(fds,sig):
    failures=[]
    for fd in fds:
        if fd is None:continue
        try:pidfd_compat.send_signal(fd,sig)
        except ProcessLookupError:pass
        except BaseException as error:failures.append(type(error).__name__)
    return failures


def wait_known(pid,pidfd):
    if not terminal(pidfd):return None
    try:child,status=os.waitpid(pid,os.WNOHANG)
    except ChildProcessError:return 'NOT_OUR_CHILD'
    if child==0:return None
    if child!=pid:raise Unknown('unexpected wait identity')
    return status


def retained_keeper_target(latch,record,error,known_pid,known_fd):
    """Recover only an owned, independently reverified direct-child pidfd.

    The original record stays UNKNOWN. A failed pidfd verification, missing
    process birth, process drift or incomplete ownership never authorizes use.
    """
    if known_pid is not None and known_fd is not None:return known_pid,known_fd
    try:
        cause=error;seen=set()
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            if isinstance(cause,pidfd_compat.PidfdVerificationError):return None,None
            cause=cause.__cause__ or cause.__context__
        with latch.lock:
            if (type(record) is not ownership_latch.ChildRecord or record.latch is not latch or
                latch.children.get('keeper') is not record or record.status!='UNKNOWN_RETAINED'):
                return None,None
            pid,fd,birth=record.pid,record.pidfd,record.birth
            if type(pid) is not int or pid<=1 or type(fd) is not int or fd<0:return None,None
            if known_pid is not None and known_pid!=pid:return None,None
            if known_fd is not None and known_fd!=fd:return None,None
            first=process(pid)
            if first['parent']!=os.getpid() or (birth is not None and first['birth']!=birth):return None,None
            if os.readlink('/proc/self/fd/%d'%fd)!='anon_inode:[pidfd]':return None,None
            if not fcntl.fcntl(fd,fcntl.F_GETFD)&fcntl.FD_CLOEXEC:return None,None
            if fcntl.fcntl(fd,fcntl.F_GETFL)&getattr(os,'O_NONBLOCK',0):return None,None
            if pidfd_pid(fd)!=pid or process(pid)!=first:return None,None
            # The record remains UNKNOWN; observation permits only this
            # pidfd-directed stop and direct-child wait, never retirement.
            record.failure_observation=first
            return pid,fd
    except BaseException:
        return None,None


def run(admission_raw,admission_sha,review_raw,review_sha,nonce,caps,actor_pids):
    """Execute the fixed reviewed entry. Not an admission or generic controller.

    Bootstrap must authenticate all input and source closure before calling.
    On any uncertainty this function retains the local owned record and does not
    return. No caller-provided executable or callable crosses this boundary.
    """
    if os.getuid()!=0 or os.geteuid()!=0 or threading.active_count()!=1:raise ValueError('single-thread root parent')
    if hashlib.sha256(admission_raw).hexdigest()!=admission_sha or hashlib.sha256(review_raw).hexdigest()!=review_sha:raise ValueError('input bytes drift')
    if type(nonce) is not str or len(nonce)!=64 or any(c not in '0123456789abcdef' for c in nonce):raise ValueError('nonce')
    if type(caps) is not dict or set(caps)!={'boot_ns','mono_ns','utc_ns'} or any(type(x) is not int for x in caps.values()):raise ValueError('clock caps')
    if type(actor_pids) is not list or len(actor_pids)!=6 or len(set(actor_pids))!=6 or any(type(x) is not int or x<=1 for x in actor_pids):raise ValueError('six actors')
    if ipc.remaining(caps)<=75000000000:raise ValueError('60s + 5s stop + 10s join reserve required')
    if signal.getitimer(signal.ITIMER_REAL)!=(0.0,0.0) or signal.SIGALRM in signal.pthread_sigmask(signal.SIG_BLOCK,()):raise ValueError('preexisting alarm or blocked SIGALRM')
    parent=process(os.getpid());now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    # Actual parent owns the adoption and wait path; no presumed process group.
    direct_completion.set_subreaper()
    parent_sock,child_sock=socket.socketpair(socket.AF_UNIX,socket.SOCK_SEQPACKET|socket.SOCK_CLOEXEC)
    parent_sock.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
    child_sock.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
    latch=ownership_latch.CustodyLatch('PARENT_OWNED');latch.retain(parent_sock,child_sock)
    record=latch.reserve_child('keeper',parent_sock,child_sock)
    installer_fd=None;installer_pid=None;lease_fd=None;keeper_fd=None;keeper_pid=None;result=None
    stop_at=min(now+60000000000,caps['boot_ns']-15000000000)
    stop_mono=time.monotonic_ns()+max(0,stop_at-now)
    stop_utc=time.time_ns()+max(0,stop_at-now)
    handoff_caps={'boot_ns':stop_at,'mono_ns':min(caps['mono_ns']-15000000000,stop_mono),'utc_ns':min(caps['utc_ns']-15000000000,stop_utc)}
    stop={'raised':False}
    def on_stop(signum,frame):
        if not stop['raised']:
            stop['raised']=True
            raise InterruptedError('configured stop received')
    try:
        for signum in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM):signal.signal(signum,on_stop)
        left=ipc.remaining(handoff_caps)
        if left<=0:raise Unknown('no deadline remaining')
        signal.setitimer(signal.ITIMER_REAL,left/1000000000)
        def child():
            parent_sock.close()
            signal.setitimer(signal.ITIMER_REAL,0)
            for signum in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM):signal.signal(signum,signal.SIG_DFL)
            signal.pthread_sigmask(signal.SIG_UNBLOCK,(signal.SIGALRM,))
            direct_entry.run(child_sock.fileno(),parent['pid'],parent['birth'],admission_raw,admission_sha,review_raw,review_sha)
            os._exit(0)
        with alarm_deferred():
            with deferred_fork.DeferredFork() as guard:
                keeper_pid,keeper_fd,keeper_birth=guard.fork_and_pin(record,child)
        child_sock.close()
        if process(keeper_pid)!={'pid':keeper_pid,'parent':parent['pid'],'pgrp':os.getpgrp(),'birth':keeper_birth}:raise Unknown('keeper identity')
        ready_parent_socket(parent_sock,keeper_fd,handoff_caps)
        frame,fds=receive_owned(parent_sock,handoff_caps,latch.retained,keeper_pid)
        if len(fds)!=1:raise Unknown('lease fd count')
        lease_fd=fds[0];lease=lease_identity(lease_fd)
        exact(frame,{'type':'LEASE','nonce':nonce,'seq':1,'keeper_pid':keeper_pid,'keeper_birth':keeper_birth,'lease':lease})
        ipc.send(parent_sock,{'type':'LEASE_ACK','nonce':nonce,'seq':1,'lease':lease},[],handoff_caps)
        ready_parent_socket(parent_sock,keeper_fd,handoff_caps)
        frame,fds=receive_owned(parent_sock,handoff_caps,latch.retained,keeper_pid)
        if len(fds)!=1:raise Unknown('installer pidfd count')
        installer_fd=fds[0];installer_pid=frame.get('installer_pid');installer_birth=frame.get('installer_birth')
        if type(installer_pid) is not int or type(installer_birth) is not str or pidfd_pid(installer_fd)!=installer_pid:raise Unknown('installer pidfd binding')
        expected={'type':'INSTALLER','nonce':nonce,'seq':2,'keeper_pid':keeper_pid,'keeper_birth':keeper_birth,
                  'installer_pid':installer_pid,'installer_birth':installer_birth,'installer_pgid':installer_pid}
        exact(frame,expected)
        if process(installer_pid)!={'pid':installer_pid,'parent':keeper_pid,'pgrp':installer_pid,'birth':installer_birth}:raise Unknown('installer process identity')
        if os.getpgrp()==installer_pid or any(os.getpgid(pid)==installer_pid for pid in actor_pids):raise Unknown('campaign actor in installer group')
        if process(keeper_pid)['birth']!=keeper_birth:raise Unknown('keeper birth changed')
        ipc.send(parent_sock,dict(expected,type='INSTALLER_ACK'),[],handoff_caps)
        ready_parent_socket(parent_sock,keeper_fd,handoff_caps)
        frame,fds=receive_owned(parent_sock,handoff_caps,latch.retained,keeper_pid)
        if len(fds)!=3 or set(frame)!={'type','nonce','seq','keeper_pid','keeper_birth','installer_pid','installer_birth','release_sha256'}:raise Unknown('GO shape')
        go_fds=fds
        release_sha=frame['release_sha256']
        if type(release_sha) is not str or len(release_sha)!=64 or any(c not in '0123456789abcdef' for c in release_sha):raise Unknown('release sha')
        expected_go={'type':'GO_READY','nonce':nonce,'seq':3,'keeper_pid':keeper_pid,'keeper_birth':keeper_birth,'installer_pid':installer_pid,'installer_birth':installer_birth}
        if ipc.canonical({k:frame[k] for k in expected_go})!=ipc.canonical(expected_go):raise Unknown('GO identity')
        if ipc.remaining(handoff_caps)<=0:raise Unknown('GO cap')
        go_verified=direct_completion.verify_parent_go(frame,go_fds,admission_raw,review_raw,latch.retained)
        if type(go_verified) is not dict or ipc.canonical(go_verified.get('lease'))!=ipc.canonical(lease):raise Unknown('lease differs from sealed release')
        if ipc.remaining(handoff_caps)<=0:raise Unknown('GO verification cap')
        if process(keeper_pid)['birth']!=keeper_birth or process(installer_pid)!={'pid':installer_pid,'parent':keeper_pid,'pgrp':installer_pid,'birth':installer_birth}:raise Unknown('process changed before GO')
        if os.getpgrp()==installer_pid or any(os.getpgid(pid)==installer_pid for pid in actor_pids):raise Unknown('actor group changed before GO')
        ipc.send(parent_sock,dict(frame,type='GO_AUTH'),[],handoff_caps)
        ready_parent_socket(parent_sock,keeper_fd,handoff_caps)
        frame,fds=receive_owned(parent_sock,handoff_caps,latch.retained,keeper_pid)
        if len(fds)!=3 or set(frame)!={'type','nonce','seq','keeper_pid','keeper_birth','installer_pid','installer_birth','release_sha256','result'}:raise Unknown('result shape')
        expected_result={'type':'RESULT','nonce':nonce,'seq':4,'keeper_pid':keeper_pid,'keeper_birth':keeper_birth,'installer_pid':installer_pid,'installer_birth':installer_birth,'release_sha256':release_sha}
        if ipc.canonical({k:frame[k] for k in expected_result})!=ipc.canonical(expected_result):raise Unknown('result identity')
        for earlier,current in zip(go_fds,fds):
            a=os.fstat(earlier);b=os.fstat(current)
            if (a.st_dev,a.st_ino,a.st_mode)!=(b.st_dev,b.st_ino,b.st_mode):raise Unknown('result descriptors changed')
        result_hash=hashlib.sha256(ipc.canonical(frame)).hexdigest()
        if ipc.remaining(handoff_caps)<=0:raise Unknown('proof cap')
        independent=direct_completion.verify_parent_result(frame,fds,admission_raw,review_raw,latch.retained)
        result=frame['result']
        if ipc.remaining(handoff_caps)<=0:raise Unknown('proof verification cap')
        ipc.send(parent_sock,{'type':'RESULT_ACK','nonce':nonce,'seq':4,'result_sha256':result_hash},[],handoff_caps)
        status=None
        while ipc.remaining(handoff_caps)>0:
            status=wait_known(keeper_pid,keeper_fd)
            if status is not None:break
            time.sleep(.05)
        if status is None or status=='NOT_OUR_CHILD' or not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0 or not terminal(installer_fd):raise Unknown('known roles not positively terminal')
        # The fixed verifier proves the keeper's direct successful installer wait
        # and durable result/captures; pidfd terminal is independently checked.
        if not direct_completion.verify_terminal_result(result,installer_pid,installer_birth,status):raise Unknown('terminal proof')
        terminal_evidence={'keeper':{'pid':keeper_pid,'birth':keeper_birth,'direct_wait_status':status},
                           'installer':{'pid':installer_pid,'birth':installer_birth,'pidfd_terminal':True,
                                        'keeper_direct_wait_status':result['installer_wait_status']}}
        return {'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':nonce,'authority':None,'native_release':False,'native_currentfree':None,'proof':result,'independent_verification':independent,'lease_disposition':'HELD','terminal_evidence':terminal_evidence},latch,lease_fd,go_fds[0]
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        latch.fail(error)
        # If fork_and_pin raised after recording the handle but before assigning
        # locals, recover only the still-owned, independently verified target.
        keeper_pid,keeper_fd=retained_keeper_target(latch,record,error,keeper_pid,keeper_fd)
        # Do not wait for filesystem journal I/O before stopping known children.
        stop_owned([installer_fd,keeper_fd],signal.SIGTERM)
        until=min(time.clock_gettime_ns(time.CLOCK_BOOTTIME)+5000000000,caps['boot_ns'])
        while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<until and ipc.remaining(caps)>0:
            try:
                if (installer_fd is None or terminal(installer_fd)) and (keeper_fd is None or terminal(keeper_fd)):break
            except BaseException:break
            time.sleep(.05)
        stop_owned([installer_fd,keeper_fd],signal.SIGKILL)
        # Keep original lease and pidfds indefinitely on uncertainty. Root must
        # provide independently reviewed operation custody before termination.
        while True:
            try:
                if keeper_pid is not None and keeper_fd is not None:wait_known(keeper_pid,keeper_fd)
                if installer_fd is not None and terminal(installer_fd):
                    try:os.waitpid(installer_pid,os.WNOHANG)
                    except (ChildProcessError,ValueError):pass
            except BaseException:pass
            time.sleep(1)


def serve(admission_raw,admission_sha,review_raw,review_sha,nonce,caps,actor_pids):
    """Fixed bootstrap must call this, never discard the returned live latch.

    Retirement is possible only after the fixed verifier confirms the original
    Root-approved operation-only authority, all proof and both positive waits.
    All exceptions retain ownership; no close is retried after ambiguity.
    """
    result,latch,lease_fd,root_fd=run(admission_raw,admission_sha,review_raw,review_sha,nonce,caps,actor_pids)
    journal_fd=None;close_state='HELD';full_sha=None;disposition_attempted=False
    try:
        request=json.loads(admission_raw,object_pairs_hook=ipc.unique)
        profile_sha=request['profile_sha256']
        if type(request['retire_operation_only']) is not bool:raise ValueError('retirement intent')
        if ipc.remaining(caps)<=0:raise Unknown('no handoff time remains')
        name='PARENT-RETIRE-'+nonce+'.jsonl'
        journal_record={'state':'PENDING_OPEN','fd':None};latch.retain(journal_record)
        with alarm_deferred():
            with deferred_fork.DeferredFork():
                journal_fd=os.open(name,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
                journal_record['fd']=journal_fd;journal_record['state']='OWNED'
        os.fsync(root_fd)
        def publish(event):
            raw=ipc.canonical(event);offset=0
            while offset<len(raw):
                count=os.write(journal_fd,raw[offset:])
                if count<=0:raise OSError('short retirement journal')
                offset+=count
            os.fsync(journal_fd)
        publish({'state':'COMPLETE_PROOF_BEFORE_LEASE_CLOSE','nonce':nonce,'result':result,'lease':lease_identity(lease_fd)})
        full_sha=data_output.publish_full(nonce,profile_sha,result,caps)
        if request['retire_operation_only'] is False:
            disposition_attempted=True
            data_output.publish_disposition(nonce,profile_sha,full_sha,'HELD','UNKNOWN',caps)
            while True:time.sleep(1)
        if not direct_completion.verify_parent_retirement_authority(result['proof'],admission_raw,review_raw):
            raise Unknown('retirement authority absent')
        if ipc.remaining(caps)<=0:raise Unknown('retirement cap expired')
        # Record disposition before the single close. An interrupted close is
        # possibly closed and may never be reused or retried.
        records=[r for r in latch.retained if isinstance(r,ipc.ReceivedCustody) and lease_fd in r.fds]
        if len(records)!=1:raise Unknown('lease record not uniquely owned')
        owner=records[0];slot=owner.fds.index(lease_fd)
        with alarm_deferred():
            with deferred_fork.DeferredFork():
                close_state='CLOSING';owner.state='CLOSING';owner.historical_fd=lease_fd;owner.fds[slot]=None
                try:os.close(lease_fd)
                except BaseException:
                    close_state='CLOSURE_UNKNOWN';owner.state='CLOSURE_UNKNOWN'
                    raise
                close_state='VERIFIED_CLOSED';owner.state='VERIFIED_CLOSED';lease_fd=None
        publish({'state':'LEASE_FD_CLOSED','nonce':nonce,'lease_disposition':close_state})
        os.fsync(root_fd)
        disposition_attempted=True
        data_output.publish_disposition(nonce,profile_sha,full_sha,'VERIFIED_CLOSED','COMPLETE',caps)
        signal.setitimer(signal.ITIMER_REAL,0)
        return {'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':nonce,'authority':None,'native_release':False,'native_currentfree':None,'lease_disposition':close_state}
    except BaseException as error:
        latch.fail(error)
        if full_sha is not None and not disposition_attempted:
            disposition_attempted=True
            report_state=close_state if close_state in ('HELD','CLOSURE_UNKNOWN','VERIFIED_CLOSED') else 'CLOSURE_UNKNOWN'
            try:data_output.publish_disposition(nonce,profile_sha,full_sha,report_state,'UNKNOWN',caps)
            except BaseException:pass
        signal.setitimer(signal.ITIMER_REAL,0)
        # If the close may have happened the historical number is never reused.
        # External Root retains the operation resource/uncertainty reservation.
        while True:time.sleep(1)
