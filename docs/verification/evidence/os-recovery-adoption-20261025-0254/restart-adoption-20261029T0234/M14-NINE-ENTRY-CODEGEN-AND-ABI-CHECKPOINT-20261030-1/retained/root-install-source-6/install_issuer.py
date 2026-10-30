"""Functional McKernel one-shot READY/GO source issuer; no security testing.
No execution at import. Actual immutable intent and distinct admission required.
"""
import hashlib
import json
import os
import resource
from pathlib import Path
import select
import signal
import stat
import struct
import time
from decimal import Decimal
import deferred_fork
import graph_observations as obs
from ownership_latch import CustodyLatch


class IssuerUnknown(RuntimeError):
    def __init__(self,latch):super().__init__('install READY/GO custody unknown');self.latch=latch


def read_exact(fd,count,deadline_boot_ns):
    out=b'';poll=select.poll();poll.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while len(out)<count:
        now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        if now>=deadline_boot_ns:raise TimeoutError('READY/GO deadline')
        if not poll.poll(min(100,max(1,(deadline_boot_ns-now)//1000000))):continue
        chunk=os.read(fd,count-len(out))
        if not chunk:raise EOFError('READY/GO channel closed')
        out+=chunk
    return out


def bounds(install,template,deadline):
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not (type(deadline) is int and type(template['issued_boot_ns']) is int and
            template['issued_boot_ns']<=now<deadline<=template['deadline_boot_ns'] and
            time.monotonic_ns()<template['deadline_mono_ns'] and
            time.time_ns()<template['utc_cap_ns']<=install.WEEKLY_UTC_CAP_NS):
        raise ValueError('start/operation cap')


def verify_timeout_group(prelim,install,template,intent,controls,capacity):
    for parent in ('/','/usr','/usr/bin'):
        st=os.stat(parent)
        if st.st_uid!=0 or not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)&0o022:
            raise ValueError('tool path ancestry')
    for path,key in (('/usr/bin/sudo','sudo_sha256'),('/usr/bin/taskset','taskset_sha256'),('/usr/bin/prlimit','prlimit_sha256')):
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            st=os.fstat(fd)
            if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or
                not install.hex64(intent[key]) or hashlib.sha256(install.read_stable(fd,128*1024*1024)).hexdigest()!=intent[key]):
                raise ValueError('root-owned launch tool differs')
        finally:os.close(fd)
    if os.sched_getaffinity(0)!={6}:raise ValueError('operation CPU6 binding')
    limits={resource.RLIMIT_AS:(1073741824,1073741824),resource.RLIMIT_CPU:(60,60),
            resource.RLIMIT_FSIZE:(33554432,33554432),resource.RLIMIT_NOFILE:(256,256),resource.RLIMIT_CORE:(0,0)}
    if any(resource.getrlimit(key)!=value for key,value in limits.items()):raise ValueError('operation resource profile')
    pgid=os.getpgrp()
    if pgid<=1 or os.getppid()!=pgid:raise ValueError('timeout direct-parent group')
    identity=prelim.identity(pgid)
    if identity['pgrp']!=pgid:raise ValueError('timeout not group leader')
    if (type(intent['timeout_seconds']) is not int or intent['timeout_seconds']!=60 or
        type(intent['timeout_kill_grace_seconds']) is not int or intent['timeout_kill_grace_seconds']!=5):raise ValueError('timeout bounds')
    if min(template['deadline_boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME),
           template['deadline_mono_ns']-time.monotonic_ns(),template['utc_cap_ns']-time.time_ns())<=65000000000:
        raise ValueError('external timeout extends beyond original caps')
    before=prelim.identity(pgid)
    with open('/proc/%d/cmdline'%pgid,'rb') as stream:cmd=stream.read(131073)
    if len(cmd)>131072 or not cmd.endswith(b'\0'):raise ValueError('timeout argv bounded')
    args=cmd[:-1].split(b'\0')
    if args[:5]!=[b'/usr/bin/timeout',b'--signal=TERM',b'--kill-after=5s',b'60s',b'/usr/bin/python3']:
        raise ValueError('timeout executable argv')
    if not install.hex64(intent['timeout_argv_sha256']) or hashlib.sha256(cmd).hexdigest()!=intent['timeout_argv_sha256']:
        raise ValueError('timeout argv digest')
    exe=os.open('/proc/%d/exe'%pgid,os.O_RDONLY|os.O_CLOEXEC)
    try:
        st=os.fstat(exe);named=os.stat('/usr/bin/timeout')
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or
            (st.st_dev,st.st_ino)!=(named.st_dev,named.st_ino) or
            not install.hex64(intent['timeout_exe_sha256']) or
            hashlib.sha256(install.read_stable(exe,128*1024*1024)).hexdigest()!=intent['timeout_exe_sha256']):
            raise ValueError('root-owned timeout binary binding')
    finally:os.close(exe)
    actor_rows=list(controls['binding'].values())+[capacity['supervisor']]
    if (len(actor_rows)!=6 or any(os.getpgid(row['pid'])==pgid for row in actor_rows) or
        os.getpgid(intent['outer_pid'])==pgid):
        raise ValueError('campaign actor or outer owner inside timeout group')
    if prelim.identity(pgid)!=before or before!=identity:raise ValueError('timeout identity drift')
    return identity


def fresh_controls(prelim,template,install,deadline,intent):
    bounds(install,template,deadline)
    c,cref=prelim.read_bound(prelim.CONTROLS,1<<20)
    p,pref=prelim.read_bound(prelim.CAPACITY,1<<20)
    if (hashlib.sha256(c).hexdigest()!=template['controls_sha256'] or
        hashlib.sha256(p).hexdigest()!=template['capacity_sha256']):raise ValueError('current control bytes changed')
    controls=prelim.strict_json(c);capacity=prelim.strict_json(p)
    caps=prelim.controller_checks(controls,capacity,time.time())
    group=verify_timeout_group(prelim,install,template,intent,controls,capacity)
    ns=lambda value:int(Decimal(str(value))*Decimal(1000000000))
    if (caps['boot_id']!=template['boot_id'] or template['deadline_boot_ns']>ns(caps['boot_deadline']) or
        template['deadline_mono_ns']>ns(caps['monotonic_deadline']) or template['utc_cap_ns']>ns(caps['deadline'])):
        raise ValueError('operation cap looser than current control')
    bounds(install,template,deadline)
    return cref,pref,group


def require_outer_ancestor(prelim,expected_pid,expected_birth):
    if type(expected_pid) is not int or expected_pid<=1 or type(expected_birth) is not str or not expected_birth.isdigit():
        raise ValueError('known outer caller identity required')
    cursor=os.getppid();seen=set()
    for _ in range(32):
        if cursor<=1 or cursor in seen:break
        seen.add(cursor);first=prelim.identity(cursor)
        if cursor==expected_pid:
            if str(first['birth'])!=expected_birth or prelim.identity(cursor)!=first:
                raise ValueError('outer caller identity changed')
            return
        if prelim.identity(cursor)!=first:raise ValueError('caller ancestry changed')
        cursor=first['ppid']
    raise ValueError('admitted outer caller not in actual ancestry')


def run(install,watchdog,prelim,intent_fd,intent_sha,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd):
    if os.getuid()!=0 or os.geteuid()!=0:raise ValueError('root issuer required')
    install.root_file(intent_fd);raw=install.read_stable(intent_fd,install.MAX_SOURCE)
    if not install.hex64(intent_sha) or hashlib.sha256(raw).hexdigest()!=intent_sha:raise ValueError('start intent digest')
    intent=json.loads(raw,object_pairs_hook=install.unique)
    keys={'version','purpose','nonce','outer_pid','outer_birth','boot_id','phase1_deadline_boot_ns',
          'receipt_expires_boot_ns','weekly_used_percent','weekly_observed_utc_ns','service_status',
          'timeout_exe_sha256','timeout_argv_sha256','timeout_seconds','timeout_kill_grace_seconds',
          'sudo_sha256','taskset_sha256','prlimit_sha256','release_template'}
    if (type(intent) is not dict or set(intent)!=keys or type(intent['version']) is not int or intent['version']!=1 or
        intent['purpose']!='source-install-start-intent-v1' or not install.hex64(intent['nonce'])):
        raise ValueError('start intent/outer owner')
    require_outer_ancestor(prelim,intent['outer_pid'],intent['outer_birth'])
    if (type(intent['weekly_used_percent']) not in (int,float) or not 0<=intent['weekly_used_percent']<100 or
        type(intent['weekly_observed_utc_ns']) is not int or not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000 or
        intent['service_status']!='NO_NEW_REJECTION'):raise ValueError('fresh included-only status required')
    template=intent['release_template'];deadline=intent['phase1_deadline_boot_ns']
    if (type(template) is not dict or template.get('nonce')!=intent['nonce'] or
        template.get('controller_pid') is not None or template.get('controller_birth') is not None or
        template.get('boot_id')!=intent['boot_id'] or template.get('closure_sha256')!=install.CLOSURE_SHA256 or
        type(intent['receipt_expires_boot_ns']) is not int or deadline>intent['receipt_expires_boot_ns']):
        raise ValueError('start intent template')
    with open('/proc/sys/kernel/random/boot_id') as stream:boot_id=stream.read(128).strip()
    if boot_id!=intent['boot_id']:raise ValueError('boot changed')
    bounds(install,template,deadline)
    install.verify_base_runtime(template['interpreter'])
    install.verify_host_receipt(host_custody_fd,template)
    install.dir_identity(root_fd,template['operation_root'],True)
    for fd,key in ((controls_fd,'controls_sha256'),(capacity_fd,'capacity_sha256'),
                   (host_custody_fd,'host_install_custody_sha256'),(owner_release_fd,'owner_release_sha256')):
        install.root_file(fd)
        if hashlib.sha256(install.read_stable(fd,install.MAX_SOURCE)).hexdigest()!=template[key]:raise ValueError('receipt hash')
    _,_,initial_group=fresh_controls(prelim,template,install,deadline,intent)
    latch=CustodyLatch('ISSUER_HELD');latch.retain(intent_fd,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd)
    journal_fd=None;record=None
    try:
        with deferred_fork.DeferredFork() as guard:
            journal_fd=os.open('INSTALL-START-'+intent['nonce']+'.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
            latch.retain(journal_fd);os.fsync(root_fd)
            install.journal(journal_fd,{'state':'START_CONSUMED','nonce':intent['nonce'],'intent_sha256':intent_sha,'issuer_pid':os.getpid(),'issuer_birth':obs.process(os.getpid())[0]})
            ready_r,ready_w=os.pipe2(os.O_CLOEXEC);go_r,go_w=os.pipe2(os.O_CLOEXEC)
            latch.retain(ready_r,ready_w,go_r,go_w)
            def waiting_child():
                try:
                    me=os.getpid();birth=obs.process(me)[0]
                    ready=json.dumps({'pid':me,'birth':birth,'parent_pid':os.getppid(),'boot_id':boot_id,'nonce':intent['nonce']},sort_keys=True,separators=(',',':')).encode()
                    frame=struct.pack('!I',len(ready))+ready
                    if len(frame)>4096 or os.write(ready_w,frame)!=len(frame):raise OSError('short READY')
                    go=read_exact(go_r,65,deadline)
                    if go[:1]!=b'G':raise ValueError('GO absent')
                    release_sha=go[1:].decode('ascii')
                    if not install.hex64(release_sha):raise ValueError('GO release digest')
                    name='INSTALL-RELEASE-'+intent['nonce']+'.json'
                    rfd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
                    watchdog.run(install,rfd,release_sha,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd)
                except BaseException:
                    while True:signal.pause()
            record=latch.reserve_child('waiting-watchdog',root_fd,ready_r,ready_w,go_r,go_w)
            install.journal(journal_fd,{'state':'BEFORE_WAITING_FORK','nonce':intent['nonce']})
            pid,pidfd,birth=guard.fork_and_pin(record,waiting_child)
        size=struct.unpack('!I',read_exact(ready_r,4,deadline))[0]
        if not 0<size<=4092:raise ValueError('READY size')
        ready=json.loads(read_exact(ready_r,size,deadline),object_pairs_hook=install.unique)
        if ready!={'pid':pid,'birth':birth,'parent_pid':os.getpid(),'boot_id':boot_id,'nonce':intent['nonce']}:
            raise ValueError('READY identity')
        identity=prelim.identity(pid)
        if identity['ppid']!=os.getpid() or str(identity['birth'])!=birth or identity['pgrp']!=initial_group['pgrp']:
            raise ValueError('READY process or timeout group changed')
        install.journal(journal_fd,{'state':'READY_CAPTURED','ready':ready,'pidfd':pidfd})
        if fresh_controls(prelim,template,install,deadline,intent)[2]!=initial_group:raise ValueError('timeout group changed')
        install.verify_base_runtime(template['interpreter'])
        install.verify_host_receipt(host_custody_fd,template)
        watchdog.require_launch_grace(template)
        if prelim.identity(pid)!=identity:raise ValueError('waiting process changed')
        release=dict(template);release['controller_pid']=pid;release['controller_birth']=birth
        release_raw=(json.dumps(release,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
        release_sha=hashlib.sha256(release_raw).hexdigest();name='INSTALL-RELEASE-'+intent['nonce']+'.json'
        install.journal(journal_fd,{'state':'BEFORE_RELEASE_CREATE','name':name,'sha256':release_sha})
        writer=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=root_fd);latch.retain(writer)
        os.fchmod(writer,0o400);install.write_all(writer,release_raw);os.fsync(writer);os.fsync(root_fd)
        written=install.ident(os.fstat(writer))
        install.journal(journal_fd,{'state':'BEFORE_RELEASE_WRITER_CLOSE','historical_fd':writer,'identity':written})
        oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
        try:
            with latch.lock:latch.retained.remove(writer)
            try:os.close(writer)
            except BaseException:
                try:install.journal(journal_fd,{'state':'RELEASE_WRITER_CLOSURE_UNKNOWN','historical_fd':writer,'do_not_use_or_retry':True})
                except BaseException:pass
                raise
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
        install.journal(journal_fd,{'state':'RELEASE_WRITER_CLOSED','identity':written})
        rfd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);latch.retain(rfd)
        if install.ident(os.fstat(rfd))!=written:raise ValueError('release inode changed')
        before=install.flags(rfd);install.journal(journal_fd,{'state':'BEFORE_RELEASE_IMMUTABLE','name':name,'prior_flags':before})
        import fcntl
        fcntl.ioctl(rfd,install.SETFLAGS,struct.pack('I',before|install.IMMUTABLE))
        if not install.flags(rfd)&install.IMMUTABLE:raise ValueError('release immutable absent')
        os.fsync(rfd);os.fsync(root_fd)
        if hashlib.sha256(install.read_stable(rfd,install.MAX_SOURCE)).hexdigest()!=release_sha:raise ValueError('sealed release changed')
        install.journal(journal_fd,{'state':'RELEASE_SEALED','name':name,'sha256':release_sha,'pid':pid,'birth':birth})
        install.journal(journal_fd,{'state':'BEFORE_GO','pid':pid,'birth':birth,'release_sha256':release_sha})
        if fresh_controls(prelim,template,install,deadline,intent)[2]!=initial_group:raise ValueError('timeout group changed')
        install.verify_base_runtime(template['interpreter'])
        install.verify_host_receipt(host_custody_fd,template)
        watchdog.require_launch_grace(template)
        if not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000:raise ValueError('included-only observation stale before GO')
        if prelim.identity(pid)!=identity:raise ValueError('waiting process changed before GO')
        if os.write(go_w,b'G'+release_sha.encode('ascii'))!=65:raise OSError('short GO')
        install.journal(journal_fd,{'state':'GO_SENT','pid':pid,'birth':birth,'release_sha256':release_sha})
        # Issuer retains actual child record, pidfd and all handles until Root retirement.
        while True:signal.pause()
    except BaseException as error:
        if record is not None:record.unknown(error)
        else:latch.fail(error)
        if journal_fd is not None:
            try:install.journal(journal_fd,{'state':'UNKNOWN_RETAINED','error_type':type(error).__name__,'nonce_consumed':True})
            except BaseException:pass
        raise IssuerUnknown(latch) from error
