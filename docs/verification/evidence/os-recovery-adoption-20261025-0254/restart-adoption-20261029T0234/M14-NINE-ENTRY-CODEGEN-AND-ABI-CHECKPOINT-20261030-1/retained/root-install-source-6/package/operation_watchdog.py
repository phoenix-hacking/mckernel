"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Future one-shot parent watchdog. No process or root operation starts at import.
"""
import fcntl
import os
import select
import resource
import signal
import time
import graph_observations as obs
import inplace_custody as source
import custody_protocol_v2 as wire
import root_bootstrap
from ownership_latch import CustodyLatch,ChildRecord
import deferred_fork
import pidfd_compat
import runtime_binding


def fail(message):raise ValueError(message)


class LeaseStartUnknown(RuntimeError):
    def __init__(self,fd):
        super().__init__('operation lease acquisition uncertain; retain descriptor')
        self.fd=fd


def create_lease(root_fd,nonce):
    """Exclusive operation lease; caller retains this FD across child failure."""
    source.root_private(root_fd);wire.sha256_hex(nonce)
    name='GRAPH-LEASE-'+nonce
    fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        source.write_all(fd,obs.canonical({'nonce':nonce,'status':'OWNED_LEASE'})+b'\n')
        os.fsync(fd);os.fsync(root_fd)
        return fd
    except BaseException as error:
        # Caller receives and retains the uncertain descriptor and never unlinks it.
        raise LeaseStartUnknown(fd) from error


def fork_supervisor(executable,argv,environment,root_fd,lease_fd,record,guard):
    """Start a root child inheriting exactly the watchdog-owned operation FDs.

    The parent retains both descriptions. Caller first verifies immutable entry,
    interpreter and exact source bytes and separately obtains operation release.
    """
    if os.geteuid()!=0 or type(argv) is not list or not argv or argv[0]!=executable:
        fail('root and exact supervisor argv required')
    if type(environment) is not dict or any(type(k) is not str or type(v) is not str for k,v in environment.items()):
        fail('exact supervisor environment')
    if root_fd==lease_fd or min(root_fd,lease_fd)<3:fail('custody descriptors')
    source.root_private(root_fd)
    if type(record) is not ChildRecord or type(guard) is not deferred_fork.DeferredFork or not guard.entered:
        fail('guarded pre-registered supervisor custody required')
    record.add(root_fd,lease_fd)
    def child_exec():
        for fd in (root_fd,lease_fd):os.set_inheritable(fd,True)
        keep=sorted((root_fd,lease_fd))
        upper=resource.getrlimit(resource.RLIMIT_NOFILE)[0]
        if upper==resource.RLIM_INFINITY or upper>1048576:upper=1048576
        os.closerange(3,keep[0]);os.closerange(keep[0]+1,keep[1]);os.closerange(keep[1]+1,int(upper))
        env=dict(environment);env['MCKERNEL_OPERATION_ROOT_FD']=str(root_fd);env['MCKERNEL_OPERATION_LEASE_FD']=str(lease_fd)
        os.execve(executable,argv,env)
    pid,pidfd,birth=guard.fork_and_pin(record,child_exec)
    return pid,pidfd,('BOUND',None)


class LaunchUnknown(RuntimeError):
    def __init__(self,latch):
        super().__init__('supervisor launch outcome uncertain; retain registered custody')
        self.latch=latch


def launch_reviewed(root_fd,nonce,executable,executable_sha,bootstrap_path,bootstrap_sha,
                    loader_manifest,loader_sha,entry_path,environment,deadline_boot,grace_seconds,runtime_path,runtime_sha):
    """Future root-owner entry; reserve custody before a possible fork."""
    runtime_binding.verify_current(runtime_path,runtime_sha)
    if executable!=runtime_path or executable_sha!=runtime_sha:fail('watchdog/supervisor runtime differs')
    latch=CustodyLatch('WATCHDOG_HELD');latch.retain(root_fd)
    record=None
    try:
        with deferred_fork.DeferredFork() as guard:
            record=latch.reserve_child('supervisor',root_fd)
            token=latch.begin('WATCHDOG_HELD')
            source.root_private(root_fd)
            exe_fd,_=root_bootstrap.pinned_root_file(executable,executable_sha,128*1024*1024);record.add(exe_fd)
            bs_fd,bs_bytes=root_bootstrap.pinned_root_file(bootstrap_path,bootstrap_sha);record.add(bs_fd)
            manifest_fd,_=root_bootstrap.pinned_root_file(loader_manifest,loader_sha);record.add(manifest_fd)
            lease_fd=create_lease(root_fd,nonce);record.add(lease_fd)
            argv=root_bootstrap.supervisor_argv(executable,bs_bytes,loader_manifest,loader_sha,entry_path)
            pid,pidfd,result=fork_supervisor(executable,argv,environment,root_fd,lease_fd,record,guard)
        if result[0]!='BOUND':raise RuntimeError('supervisor pidfd unavailable')
        birth=record.birth
        watchdog=Watchdog.__new__(Watchdog);record.add(watchdog)
        watchdog.__init__(root_fd,lease_fd,nonce,pid,pidfd,birth,deadline_boot,grace_seconds)
        watchdog.latch=latch;watchdog.child_record=record
        latch.commit(token,'SUPERVISOR_BOUND',watchdog)
        return watchdog
    except BaseException as error:
        if record is not None:
            if isinstance(error,LeaseStartUnknown):record.add(error.fd)
            record.unknown(error)
        else:latch.fail(error)
        raise LaunchUnknown(latch) from error


def publish_unknown(root_fd,nonce,reason):
    name='GRAPH-WATCHDOG-UNKNOWN-'+nonce+'.json'
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
    try:
        source.write_all(fd,obs.canonical({'status':'UNKNOWN_RETAINED','nonce':nonce,'reason':reason})+b'\n')
        os.fsync(fd);os.fsync(root_fd)
    finally:os.close(fd)


class Watchdog:
    """Retain the same open lease description while supervising exact child PID.

    Caller must hold approved root operation/admission and independently assess
    all descendants and native state. A signal or direct wait never proves cleanup.
    """
    def __init__(self,root_fd,lease_fd,nonce,pid,pidfd,birth,deadline_boot,grace_seconds):
        source.root_private(root_fd);wire.sha256_hex(nonce)
        if type(pid) is not int or pid<=0 or type(birth) is not str or not birth.isdigit():fail('child identity')
        if obs.process(pid)[0]!=birth:fail('child birth changed')
        if type(deadline_boot) not in (int,float) or not wire.boot_now()<deadline_boot<=1571567.6959065471:fail('deadline')
        if type(grace_seconds) not in (int,float) or not 0<grace_seconds<=30:fail('grace')
        self.root_fd,self.lease_fd,self.nonce=root_fd,lease_fd,nonce
        self.pid,self.pidfd,self.birth,self.deadline,self.grace=pid,pidfd,birth,deadline_boot,grace_seconds
        self.state='HELD';self.wait_status=None

    def _poll(self,until):
        poll=select.poll();poll.register(self.pidfd,select.POLLIN)
        while wire.boot_now()<until:
            if poll.poll(max(1,min(1000,int((until-wire.boot_now())*1000)))):return True
        return False

    def _signal(self,sig):
        if obs.process(self.pid)[0]!=self.birth:fail('signal identity ambiguous')
        pidfd_compat.send_signal(self.pidfd,sig)

    def supervise(self):
        if self.state!='HELD':fail('watchdog already used')
        try:
            if not self._poll(self.deadline):
                self.state='UNKNOWN_RETAINED';self.latch.fail('supervisor deadline');publish_unknown(self.root_fd,self.nonce,'supervisor deadline')
                self._signal(signal.SIGTERM)
                if not self._poll(wire.boot_now()+self.grace):
                    self._signal(signal.SIGKILL)
                    if not self._poll(wire.boot_now()+self.grace):fail('supervisor direct join unknown')
            # waitpid only for this own child; other process/cgroup custody is unknown.
            got,status=os.waitpid(self.pid,0)
            if got!=self.pid:fail('direct wait identity')
            self.wait_status=status;self.state='UNKNOWN_RETAINED';self.latch.fail('direct wait only')
            return {'status':'DIRECT_WAIT_ONLY_UNKNOWN_RETAINED','wait_status':status,'nonce':self.nonce}
        except BaseException as error:
            self.state='UNKNOWN_RETAINED';self.latch.fail(error);raise

    def retire(self):
        raise RuntimeError('lease and flags remain held pending independent physical retirement')


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: no root operation admission')
