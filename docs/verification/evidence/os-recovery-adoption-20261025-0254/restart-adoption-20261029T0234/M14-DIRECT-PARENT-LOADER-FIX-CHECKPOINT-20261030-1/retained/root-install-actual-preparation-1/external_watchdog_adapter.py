"""Functional McKernel install-only external owner adapter; source only.

Run only inside an already admitted root owner's existing event loop. No process,
thread, controller or privileged action is started by importing this module.
"""
import fcntl
import hashlib
import json
import os
import select
import socket
import stat
import struct
import sys
import time

HELD=[]


def fail(message):raise ValueError(message)


def arm(sock,driver,actual_path,actual_sha,review_path,review_sha,journal_fd,custody_module,guard_module):
    """Pin a caller process and durable UNKNOWN custody before acknowledging it.

    Caller must be the actual independently admitted root watchdog process,
    with an existing event loop and root-owned per-operation journal. The
    selected driver and pidfd module must have been loaded from reviewed bytes.
    """
    if os.getuid()!=0 or os.geteuid()!=0:fail('existing root owner required')
    if sock.family!=socket.AF_UNIX or sock.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_SEQPACKET:fail('channel type')
    caller,uid,_=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    if uid!=1000 or caller<=1:fail('actual calling process credentials')
    before=driver.proc(caller)
    st=os.fstat(journal_fd);mode=fcntl.fcntl(journal_fd,fcntl.F_GETFL)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600 or
        st.st_nlink!=1 or not mode&os.O_APPEND or mode&os.O_ACCMODE==os.O_RDONLY):fail('root custody journal')
    # Bytes and hashes alone do not authorize this operation. The caller must
    # obtain independent one-shot admission through its real root-owned control.
    actual_raw=driver.source(actual_path,actual_sha);review_raw=driver.source(review_path,review_sha)
    actual=json.loads(actual_raw,object_pairs_hook=driver.unique)
    proposal=json.loads(driver.source(driver.PROPOSAL_PATH,driver.PROPOSAL_SHA),object_pairs_hook=driver.unique)
    if actual.get('operation_review_sha256')!=review_sha:fail('external review binding')
    live=driver.live_controls();request,raw,request_sha=driver.bind_actual(proposal,actual,review_raw,live)
    expected=actual['external_watchdog']
    if type(expected) is not dict or set(expected)!={'pid','birth','exe_sha256'} or expected['pid']!=os.getpid() or driver.proc(os.getpid())['birth']!=expected['birth']:
        fail('actual watchdog process binding')
    exe=os.open('/proc/self/exe',os.O_RDONLY|os.O_CLOEXEC)
    try:
        if driver.sha(driver.read_stable(exe,128*1024*1024))!=expected['exe_sha256']:fail('watchdog executable binding')
    finally:os.close(exe)
    # Allocate the ownership record before opening the pidfd. In an uncertain
    # post-open verification error retain its exact FD, never numeric-signal it.
    # Both exact modules must be loaded from v10's pinned source by the root
    # owner's trusted entry, and share one PidfdCustodyRecord class identity.
    closure=json.loads(driver.source(driver.BASE/'root-install-source-10'/'SOURCE-CLOSURE.json','81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'))
    hashes={row['name']:row['sha256'] for row in closure['files']}
    for module,name in ((custody_module,'pidfd_custody.py'),(guard_module,'deferred_fork.py')):
        if os.path.abspath(module.__file__)!=str(driver.BASE/'root-install-source-10'/'package'/name):fail('custody module path')
        driver.source(driver.BASE/'root-install-source-10'/'package'/name,hashes[name])
    if guard_module.PidfdCustodyRecord is not custody_module.PidfdCustodyRecord:fail('custody class binding')
    pid_record=custody_module.PidfdCustodyRecord(journal_fd,request['nonce'])
    record={'state':'REGISTERED','caller':before,'nonce':request['nonce'],'request_sha256':request_sha,
            'deadline_boot_ns':request['deadline_boot_ns'],'pidfd':None,'pidfd_record':pid_record,'journal_fd':journal_fd}
    HELD.append(record)
    try:
        with guard_module.DeferredFork() as guard:
            record['pidfd']=guard.acquire_and_pin(pid_record,caller,before['birth'])
        if driver.proc(caller)!=before:fail('caller identity changed')
        remaining=(request['deadline_boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME))/1e9
        if remaining<=0:fail('deadline elapsed before arm')
        sock.settimeout(min(5.0,remaining))
        raw_packet=sock.recv(65536)
        packet=json.loads(raw_packet,object_pairs_hook=driver.unique)
        expected_packet={'type':'ARM_INSTALL_OWNER_V1','nonce':request['nonce'],'request_sha256':request_sha,
                         'caller_pid':caller,'deadline_boot_ns':request['deadline_boot_ns']}
        if packet!=expected_packet:fail('exact arm binding')
        if time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=request['deadline_boot_ns']:fail('deadline elapsed')
        event=driver.canonical({'state':'EXTERNAL_OWNER_ARMED','caller':before,'nonce':request['nonce'],
              'request_sha256':request_sha,'deadline_boot_ns':request['deadline_boot_ns'],'watchdog_pid':os.getpid(),
              'watchdog_birth':expected['birth'],'native_release':False})
        offset=0
        while offset<len(event):
            count=os.write(journal_fd,event[offset:])
            if count<=0:raise OSError('short owner journal')
            offset+=count
        os.fsync(journal_fd);record['state']='ARMED';record['socket']=sock
        reply={'type':'INSTALL_OWNER_ARMED_V1','nonce':request['nonce'],'request_sha256':request_sha,
               'caller_pid':caller,'watchdog_pid':os.getpid(),'watchdog_birth':expected['birth'],
               'deadline_boot_ns':request['deadline_boot_ns']}
        data=driver.canonical(reply)
        if sock.send(data)!=len(data):fail('owner acknowledgement short')
        return record
    except BaseException:
        record['state']='UNKNOWN_RETAINED'
        raise


def service_once(record,driver):
    """Existing event loop observes custody without adding a worker process.

    The initial socket closure after authenticated exec handoff is expected;
    it does not prove exec or descendant retirement. Every deadline/observation
    failure retains UNKNOWN; no numeric-PID signal or native release is used.
    """
    if record not in HELD or record.get('state') not in ('ARMED','HANDOFF_PENDING','UNKNOWN_RETAINED'):fail('unknown owner record')
    if record['state']=='UNKNOWN_RETAINED':return record['state']
    try:
        if time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=record['deadline_boot_ns']:
            record['state']='UNKNOWN_RETAINED';record['reason']='DEADLINE';return record['state']
        driver.live_controls()
        poll=select.poll();poll.register(record['pidfd'],select.POLLIN|select.POLLERR|select.POLLHUP)
        if record['state']=='ARMED':poll.register(record['socket'].fileno(),select.POLLIN|select.POLLHUP|select.POLLERR)
        for fd,events in poll.poll(0):
            if fd==record['pidfd']:
                record['state']='UNKNOWN_RETAINED';record['reason']='CALLER_TERMINAL';return record['state']
            if events&select.POLLIN:
                packet=json.loads(record['socket'].recv(65536),object_pairs_hook=driver.unique)
                expected={'type':'EXEC_HANDOFF_V1','nonce':record['nonce'],'request_sha256':record['request_sha256'],'caller_pid':record['caller']['pid']}
                if packet!=expected:fail('handoff binding')
                event=driver.canonical({'state':'EXEC_HANDOFF_PENDING','nonce':record['nonce'],'request_sha256':record['request_sha256'],'caller':record['caller']})
                offset=0
                while offset<len(event):
                    count=os.write(record['journal_fd'],event[offset:])
                    if count<=0:raise OSError('short handoff journal')
                    offset+=count
                os.fsync(record['journal_fd']);record['state']='HANDOFF_PENDING'
                reply=driver.canonical({'type':'EXEC_HANDOFF_ACK_V1','nonce':record['nonce'],'request_sha256':record['request_sha256'],'caller_pid':record['caller']['pid']})
                if record['socket'].send(reply)!=len(reply):fail('handoff acknowledgement')
            elif events&(select.POLLHUP|select.POLLERR):
                record['state']='UNKNOWN_RETAINED';record['reason']='CHANNEL_LOST';return record['state']
        return record['state']
    except BaseException:
        record['state']='UNKNOWN_RETAINED';record['reason']='OBSERVATION_UNKNOWN';return record['state']


def retire(*_args,**_kwargs):
    raise RuntimeError('no authority to retire operation or native ownership')
