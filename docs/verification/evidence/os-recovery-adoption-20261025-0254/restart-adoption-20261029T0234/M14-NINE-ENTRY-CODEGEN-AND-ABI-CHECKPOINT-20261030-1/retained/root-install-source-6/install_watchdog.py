"""Functional McKernel source install only; no security testing.
Post-sudo direct parent: one lease description, pre-owned child, no cleanup.
"""
import fcntl
import hashlib
import json
import os
import select
import signal
import stat
import time
import deferred_fork
import pidfd_compat
import graph_observations as obs
from ownership_latch import CustodyLatch


class WatchdogUnknown(RuntimeError):
    def __init__(self,latch):super().__init__('installer/watchdog outcome unknown');self.latch=latch


def check_time(install,release):
    boot=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not (release['issued_boot_ns']<=boot<release['deadline_boot_ns'] and
            time.monotonic_ns()<release['deadline_mono_ns'] and
            time.time_ns()<release['utc_cap_ns']<=install.WEEKLY_UTC_CAP_NS):
        raise ValueError('watchdog time bound')


def remaining_ns(release):
    return min(release['deadline_boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME),
               release['deadline_mono_ns']-time.monotonic_ns(),release['utc_cap_ns']-time.time_ns())


def reserved_grace(release):
    for key in ('term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(release[key]) is not int or release[key]<=0:raise ValueError('invalid reserved grace')
    total=release['term_grace_ns']+release['kill_grace_ns']+release['join_grace_ns']
    if total>30000000000:raise ValueError('grace reservation exceeds 30 seconds')
    return total


def require_launch_grace(release):
    if remaining_ns(release)<=reserved_grace(release)+500000000:
        raise TimeoutError('insufficient reserved stop and join grace before launch')


def watch_owned_child(install,release,pid,pidfd,journal_fd,events):
    """Stop by pidfd and join before any potentially blocking journal write."""
    total=reserved_grace(release);threshold=total+250000000
    poll=select.poll();poll.register(pidfd,select.POLLIN)
    def sent(sig,label):
        # In-memory latch precedes syscall. A journal/fsync cannot delay stop.
        item={'state':label+'_ATTEMPT','pid':pid};events.append(item)
        try:pidfd_compat.send_signal(pidfd,sig)
        except ProcessLookupError:
            item['result']='ESRCH'
            if poll.poll(0):return False
            raise
        except BaseException:
            item['result']='ERROR';raise
        item['result']='SENT';return True
    def ready_until(stage_boot_ns):
        while True:
            left=remaining_ns(release)
            if poll.poll(0):return True
            if left<=0:return False
            stage_left=stage_boot_ns-time.clock_gettime_ns(time.CLOCK_BOOTTIME)
            if stage_left<=0:return False
            poll.poll(max(1,min(100,stage_left//1000000,left//1000000)))
    while True:
        left=remaining_ns(release)
        if poll.poll(0):break
        if left<=threshold:
            # If there is no full TERM+KILL+join reservation, prefer KILL now.
            if left<total:
                sent(signal.SIGKILL,'CHILD_KILL_PIDFD')
                if left<=0:raise TimeoutError('deadline passed; pidfd kill attempted')
                end=time.clock_gettime_ns(time.CLOCK_BOOTTIME)+max(0,left-release['join_grace_ns'])
                if not ready_until(end):raise TimeoutError('child not terminal after immediate pidfd kill')
            else:
                term_failed=False
                try:sent(signal.SIGTERM,'CHILD_TERM_PIDFD')
                except BaseException:term_failed=True
                end=time.clock_gettime_ns(time.CLOCK_BOOTTIME)+release['term_grace_ns']
                if term_failed or not ready_until(end):
                    sent(signal.SIGKILL,'CHILD_KILL_PIDFD')
                    end=time.clock_gettime_ns(time.CLOCK_BOOTTIME)+release['kill_grace_ns']
                    if not ready_until(end):raise TimeoutError('child not terminal after pidfd kill')
            break
        poll.poll(max(1,min(100,(left-threshold)//1000000)))
    while remaining_ns(release)>0:
        reaped,status=os.waitpid(pid,os.WNOHANG)
        if reaped==pid:return status
        if reaped!=0:raise RuntimeError('unexpected wait identity')
        poll.poll(1)
    raise TimeoutError('direct child join not observed')


def run(install,release_fd,release_sha,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd):
    if os.getuid()!=0 or os.geteuid()!=0:raise ValueError('root watchdog required')
    # Validate the complete admission and all receipt bytes before lease/journal
    # mutation; controller is this process, and child later checks its parent.
    release=install.verify_release(release_fd,release_sha,True)
    install.verify_base_runtime(release['interpreter'])
    install.verify_host_receipt(host_custody_fd,release)
    for fd,key in ((controls_fd,'controls_sha256'),(capacity_fd,'capacity_sha256'),
                   (host_custody_fd,'host_install_custody_sha256'),(owner_release_fd,'owner_release_sha256')):
        install.root_file(fd)
        if hashlib.sha256(install.read_stable(fd,install.MAX_SOURCE)).hexdigest()!=release[key]:
            raise ValueError('receipt bytes differ')
    check_time(install,release)
    if os.getpgid(os.getppid())!=os.getpgrp():raise ValueError('issuer/watchdog process group differs')
    require_launch_grace(release)
    install.dir_identity(root_fd,release['operation_root'],True)
    lease=os.fstat(lease_fd)
    if not stat.S_ISREG(lease.st_mode) or lease.st_uid!=0 or install.ident(lease)!=release['lease']:
        raise ValueError('lease identity')
    latch=CustodyLatch('WATCHDOG_HELD');latch.retain(root_fd,lease_fd,release_fd,source_fd,code_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd)
    journal_fd=None;record=None;stop_events=[]
    try:
        def child_exec():
            try:
                # No exec/reopen: lease_fd is exactly the fork-inherited OFD.
                install.install(release_fd,release_sha,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd)
            except BaseException:
                while True:signal.pause()
            os._exit(0)
        with deferred_fork.DeferredFork() as guard:
            # This is the sole flock acquisition. Child inherits this description.
            fcntl.flock(lease_fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            journal_fd=os.open('INSTALL-WATCHDOG-'+release['nonce']+'.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
            latch.retain(journal_fd);os.fsync(root_fd)
            install.journal(journal_fd,{'state':'WATCHDOG_HELD','pid':os.getpid(),'birth':release['controller_birth'],
              'lease':install.ident(lease),'release_sha256':release_sha,'nonce':release['nonce']})
            record=latch.reserve_child('source-installer',lease_fd,root_fd,journal_fd)
            install.journal(journal_fd,{'state':'BEFORE_FORK','nonce':release['nonce']})
            require_launch_grace(release)
            pid,pidfd,birth=guard.fork_and_pin(record,child_exec)
        if os.getpgid(pid)!=os.getpgrp():raise ValueError('installer escaped timeout process group')
        install.journal(journal_fd,{'state':'CHILD_BOUND','pid':pid,'birth':birth,'pidfd':pidfd,'lease':install.ident(lease)})
        status=watch_owned_child(install,release,pid,pidfd,journal_fd,stop_events)
        for event in stop_events:install.journal(journal_fd,event)
        install.journal(journal_fd,{'state':'CHILD_TERMINAL','pid':pid,'birth':birth,'wait_status':status})
        if not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0:raise RuntimeError('installer non-success terminal')
        # SOURCE_INSTALLED is data in the child journal, never admission/acceptance.
        # Continue holding the same lease until the actual Root owner retires us.
        while True:signal.pause()
    except BaseException as error:
        if record is not None:record.unknown(error)
        else:latch.fail(error)
        if journal_fd is not None:
            try:
                for event in stop_events:install.journal(journal_fd,event)
                install.journal(journal_fd,{'state':'UNKNOWN_RETAINED','error_type':type(error).__name__})
            except BaseException:pass
        raise WatchdogUnknown(latch) from error
