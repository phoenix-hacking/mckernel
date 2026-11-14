"""Functional M14 root leasekeeper and private timeout issuer. Source only."""
import ctypes
import fcntl
import hashlib
import json
import os
import resource
import select
import signal
import stat
import struct
import threading
import time
from decimal import Decimal
import deferred_fork
import graph_observations as obs
import install_completion as completion
from ownership_latch import CustodyLatch
from pidfd_custody import PidfdCustodyRecord

class IssuerUnknown(RuntimeError):
    def __init__(self,latch):super().__init__('keeper custody unknown');self.latch=latch


def set_subreaper():
    libc=ctypes.CDLL(None,use_errno=True);prctl=libc.prctl
    prctl.argtypes=(ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong);prctl.restype=ctypes.c_int
    if prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    actual=ctypes.c_int(-1)
    if prctl(37,ctypes.addressof(actual),0,0,0)!=0 or actual.value!=1:raise OSError(ctypes.get_errno(),'PR_GET_CHILD_SUBREAPER')


def read_exact(fd,count,deadline,template=None):
    out=b'';poll=select.poll();poll.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while len(out)<count:
        left=deadline-time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        if template is not None:left=min(left,template['deadline_mono_ns']-time.monotonic_ns(),template['utc_cap_ns']-time.time_ns())
        if left<=0:raise TimeoutError('READY/GO deadline')
        if not poll.poll(min(100,max(1,left//1000000))):continue
        part=os.read(fd,count-len(out))
        if not part:raise EOFError('READY/GO closed')
        out+=part
    return out


def bounds(install,template,deadline):
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not (type(deadline) is int and template['issued_boot_ns']<=now<deadline<=template['deadline_boot_ns'] and
            time.monotonic_ns()<template['deadline_mono_ns'] and time.time_ns()<template['utc_cap_ns']<=install.WEEKLY_UTC_CAP_NS):raise ValueError('operation caps')


def require_outer_ancestor(prelim,pid,birth):
    if type(pid) is not int or pid<=1 or type(birth) is not str or not birth.isdigit():raise ValueError('outer identity')
    cursor=os.getppid();seen=set()
    for _ in range(32):
        if cursor<=1 or cursor in seen:break
        seen.add(cursor);row=prelim.identity(cursor)
        if prelim.identity(cursor)!=row:raise ValueError('outer ancestry changed')
        if cursor==pid:
            if str(row['birth'])!=birth:raise ValueError('outer birth')
            return
        cursor=row['ppid']
    raise ValueError('outer owner absent')


def remaining_timeout_budget(timer_started_boot,now_boot):
    if type(timer_started_boot) is not int or type(now_boot) is not int or now_boot<timer_started_boot:
        raise ValueError('timer clock sequence')
    elapsed=now_boot-timer_started_boot
    if elapsed>=60000000000:raise TimeoutError('private timeout already expired before GO')
    return 65000000000-elapsed


def require_full_go_reserve(template,reserve):
    if type(reserve) is not int or not 1000000000<=reserve<=30000000000:raise ValueError('positive join/capture reserve')
    if completion.remaining(template)<=65000000000+reserve:
        raise ValueError('full timeout plus join/capture reserve exceeds caps')


def verify_tools(install,intent,template,timer_started_boot=None):
    for parent in ('/','/usr','/usr/bin'):
        st=os.stat(parent)
        if st.st_uid!=0 or not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)&0o022:raise ValueError('tool ancestry')
    for path,key in (('/usr/bin/sudo','sudo_sha256'),('/usr/bin/taskset','taskset_sha256'),('/usr/bin/prlimit','prlimit_sha256'),('/usr/bin/timeout','timeout_exe_sha256')):
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or not install.hex64(intent[key]) or hashlib.sha256(install.read_stable(fd,128*1024*1024)).hexdigest()!=intent[key]:raise ValueError('root tool binding')
        finally:os.close(fd)
    if os.sched_getaffinity(0)!={6}:raise ValueError('CPU6 affinity')
    limits={resource.RLIMIT_AS:(1073741824,1073741824),resource.RLIMIT_CPU:(60,60),resource.RLIMIT_FSIZE:(33554432,33554432),resource.RLIMIT_NOFILE:(256,256),resource.RLIMIT_CORE:(0,0)}
    if any(resource.getrlimit(key)!=value for key,value in limits.items()):raise ValueError('resource profile')
    if intent['timeout_seconds']!=60 or intent['timeout_kill_grace_seconds']!=5:raise ValueError('timeout profile')
    reserve=intent['join_capture_reserve_ns']
    if type(reserve) is not int or not 1000000000<=reserve<=30000000000:raise ValueError('positive join/capture reserve')
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if timer_started_boot is not None:remaining_timeout_budget(timer_started_boot,now)
    require_full_go_reserve(template,reserve)


def fresh_controls(prelim,install,template,deadline):
    bounds(install,template,deadline)
    c,_=prelim.read_bound(prelim.CONTROLS,1<<20);p,_=prelim.read_bound(prelim.CAPACITY,1<<20)
    if hashlib.sha256(c).hexdigest()!=template['controls_sha256'] or hashlib.sha256(p).hexdigest()!=template['capacity_sha256']:raise ValueError('controls changed')
    controls=prelim.strict_json(c);capacity=prelim.strict_json(p);caps=prelim.controller_checks(controls,capacity,time.time())
    ns=lambda v:int(Decimal(str(v))*Decimal(1000000000))
    if caps['boot_id']!=template['boot_id'] or template['deadline_boot_ns']>ns(caps['boot_deadline']) or template['deadline_mono_ns']>ns(caps['monotonic_deadline']) or template['utc_cap_ns']>ns(caps['deadline']):raise ValueError('control caps')
    bounds(install,template,deadline)
    return list(controls['binding'].values())+[capacity['supervisor']]


def verify_private_group(prelim,install,intent,timer_pid,timer_birth,ready,timer_argv,actors):
    timer=prelim.identity(timer_pid);child=prelim.identity(ready['pid'])
    if (str(timer['birth'])!=timer_birth or timer['ppid']!=os.getpid() or timer['pgrp']!=timer_pid or
        child['ppid']!=timer_pid or child['pgrp']!=timer_pid or str(child['birth'])!=ready['birth'] or ready['pgrp']!=timer_pid or
        ready['parent_pid']!=timer_pid or os.getpgrp()==timer_pid):raise ValueError('private timer/installer identity')
    if len(actors)!=6 or any(os.getpgid(row['pid'])==timer_pid for row in actors) or os.getpgid(intent['outer_pid'])==timer_pid:raise ValueError('owner inside private group')
    with open('/proc/%d/cmdline'%timer_pid,'rb') as stream:actual=stream.read(131073)
    expected=b'\0'.join(os.fsencode(x) for x in timer_argv)+b'\0'
    if len(actual)>131072 or actual!=expected:raise ValueError('timeout argv drift')
    fd=os.open('/proc/%d/exe'%timer_pid,os.O_RDONLY|os.O_CLOEXEC)
    try:
        st=os.fstat(fd);target=os.stat('/usr/bin/timeout')
        if (st.st_dev,st.st_ino)!=(target.st_dev,target.st_ino) or hashlib.sha256(install.read_stable(fd,128*1024*1024)).hexdigest()!=intent['timeout_exe_sha256']:raise ValueError('timeout executable drift')
    finally:os.close(fd)
    if prelim.identity(timer_pid)!=timer or prelim.identity(ready['pid'])!=child:raise ValueError('timer/installer identity drift')
    return timer,child,hashlib.sha256(actual).hexdigest()


def monitor_owned(latch,install,journal_fd,timer_pid,timer_fd,child_pid,child_fd,template,reserve):
    poll=select.poll();poll.register(timer_fd,select.POLLIN);poll.register(child_fd,select.POLLIN)
    timer_status=None;child_status=None;child_terminal=False
    while completion.remaining(template)>reserve:
        events=dict(poll.poll(100))
        if any(mask&(select.POLLERR|select.POLLNVAL) for mask in events.values()):raise IssuerUnknown(latch)
        if events.get(child_fd,0)&(select.POLLIN|select.POLLHUP):child_terminal=True
        if events.get(timer_fd,0)&select.POLLHUP and timer_status is None:raise IssuerUnknown(latch)
        if events.get(timer_fd,0)&select.POLLIN and timer_status is None:
            pid,status=os.waitpid(timer_pid,os.WNOHANG)
            if pid==timer_pid:
                timer_status=status;poll.unregister(timer_fd)
        if child_terminal:
            try:
                pid,status=os.waitpid(child_pid,os.WNOHANG)
                if pid==child_pid:child_status=status
            except ChildProcessError:pass
        if timer_status is not None and child_terminal:break
    if (timer_status is None or not os.WIFEXITED(timer_status) or os.WEXITSTATUS(timer_status)!=0 or not child_terminal or
        (child_status is not None and (not os.WIFEXITED(child_status) or os.WEXITSTATUS(child_status)!=0))):
        raise IssuerUnknown(latch)
    return {'timer_direct_wait_status':timer_status,'installer_pidfd_terminal':True,
            'installer_direct_wait_status':child_status}


def run(install,prelim,intent_fd,intent_sha,source_fd,root_fd,code_fd,lease_path,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd,wait_literal):
    if os.getuid()!=0 or os.geteuid()!=0 or threading.active_count()!=1:raise ValueError('single-thread root keeper required')
    install.root_file(intent_fd);raw=install.read_stable(intent_fd,install.MAX_SOURCE)
    if not install.hex64(intent_sha) or hashlib.sha256(raw).hexdigest()!=intent_sha:raise ValueError('start intent digest')
    intent=json.loads(raw,object_pairs_hook=install.unique)
    keys={'version','purpose','nonce','outer_pid','outer_birth','boot_id','phase1_deadline_boot_ns','receipt_expires_boot_ns','weekly_used_percent','weekly_observed_utc_ns','service_status','timeout_exe_sha256','timeout_seconds','timeout_kill_grace_seconds','sudo_sha256','taskset_sha256','prlimit_sha256','wait_literal_sha256','join_capture_reserve_ns','proc_scope','release_template'}
    if type(intent) is not dict or set(intent)!=keys or type(intent['version']) is not int or intent['version']!=1 or intent['purpose']!='source-install-start-intent-v1' or not install.hex64(intent['nonce']):raise ValueError('start intent')
    require_outer_ancestor(prelim,intent['outer_pid'],intent['outer_birth'])
    if hashlib.sha256(wait_literal.encode()).hexdigest()!=intent['wait_literal_sha256']:raise ValueError('waiting code binding')
    if type(intent['weekly_used_percent']) not in (int,float) or not 0<=intent['weekly_used_percent']<100 or type(intent['weekly_observed_utc_ns']) is not int or not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000 or intent['service_status']!='NO_NEW_REJECTION':raise ValueError('included status')
    template=intent['release_template'];deadline=intent['phase1_deadline_boot_ns']
    for key in ('controller_pid','controller_birth','installer_pid','installer_birth','keeper_pid','keeper_birth'):
        if template.get(key) is not None:raise ValueError('actual identity not yet known')
    if template.get('nonce')!=intent['nonce'] or template.get('boot_id')!=intent['boot_id'] or template.get('closure_sha256')!=install.CLOSURE_SHA256 or type(intent['receipt_expires_boot_ns']) is not int or deadline>intent['receipt_expires_boot_ns']:raise ValueError('template binding')
    with open('/proc/sys/kernel/random/boot_id') as stream:boot=stream.read(128).strip()
    if boot!=intent['boot_id']:raise ValueError('boot changed')
    bounds(install,template,deadline);install.verify_base_runtime(template['interpreter']);install.verify_host_receipt(host_fd,template);verify_tools(install,intent,template)
    root_check=install.open_exact(template['operation_path'],template['operation_ancestors'],True)
    source_check=install.open_exact(install.SOURCE_DIR,template['source_ancestors'])
    code_check=install.open_exact(template['code_path'],template['code_ancestors'],True,True)
    install.dir_identity(root_fd,template['operation_root'],True);install.dir_identity(root_check,template['operation_root'],True)
    install.dir_identity(source_fd,template['source_dir']);install.dir_identity(source_check,template['source_dir'])
    install.dir_identity(code_fd,template['code_parent']);install.dir_identity(code_check,template['code_parent'])
    code_stat=os.fstat(code_fd)
    if code_stat.st_uid!=0 or stat.S_IMODE(code_stat.st_mode)!=0o755:raise ValueError('code parent mode')
    for fd,key in ((controls_fd,'controls_sha256'),(capacity_fd,'capacity_sha256'),(host_fd,'host_install_custody_sha256'),(owner_fd,'owner_release_sha256')):
        install.root_file(fd)
        if hashlib.sha256(install.read_stable(fd,install.MAX_SOURCE)).hexdigest()!=template[key]:raise ValueError('receipt hash')
    fresh_controls(prelim,install,template,deadline)
    completion.verify_creation_custody(install,owner_fd,template,intent)
    proc_fd=os.open('/proc',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    completion.verify_proc_scope(proc_fd,intent['proc_scope'])
    if type(lease_path) is not str or os.path.dirname(lease_path)!=template['operation_path'] or os.path.basename(lease_path) in ('','.','..'):
        raise ValueError('lease must be under admitted private root')
    latch=CustodyLatch('KEEPER_HELD');latch.lease_disposition='UNLOCKED';latch.retain(intent_fd,source_fd,root_fd,code_fd,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd,proc_fd)
    journal_fd=None;timer_record=None;child_record=None;lease_fd=None
    try:
        with deferred_fork.DeferredFork() as guard:
            lease_fd=os.open(os.path.basename(lease_path),os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);latch.retain(lease_fd)
            lease_stat=os.fstat(lease_fd)
            if not stat.S_ISREG(lease_stat.st_mode) or lease_stat.st_uid!=0 or install.ident(lease_stat)!=template['lease']:
                raise ValueError('lease identity')
            journal_fd=os.open('INSTALL-START-'+intent['nonce']+'.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd);latch.retain(journal_fd);os.fsync(root_fd)
            install.journal(journal_fd,{'state':'START_CONSUMED','nonce':intent['nonce'],'intent_sha256':intent_sha,'keeper_pid':os.getpid(),'keeper_birth':obs.process(os.getpid())[0]})
            install.journal(journal_fd,{'state':'BEFORE_SUBREAPER'});set_subreaper();install.journal(journal_fd,{'state':'SUBREAPER_HELD'})
            captures=[]
            for stream in ('stdout','stderr'):
                name='INSTALL-CAPTURE-'+intent['nonce']+'-'+stream
                install.journal(journal_fd,{'state':'BEFORE_CAPTURE_CREATE','name':name})
                fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
                latch.retain(fd);os.fchmod(fd,0o600);os.fsync(fd);os.fsync(root_fd)
                captures.append((name,fd));install.journal(journal_fd,{'state':'CAPTURE_CREATED','name':name,'identity':install.ident(os.fstat(fd))})
            rr,rw=os.pipe2(os.O_CLOEXEC);gr,gw=os.pipe2(os.O_CLOEXEC);latch.retain(rr,rw,gr,gw)
            inherited=[install._BOOTSTRAP_SOURCE_FD,rw,gr,root_fd,source_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd]
            for fd in inherited:os.set_inheritable(fd,True)
            timer_argv=['/usr/bin/timeout','--signal=TERM','--kill-after=5s','60s','/usr/bin/python3','-I','-B','-c',wait_literal]+[str(fd) for fd in inherited]+[intent['nonce'],str(deadline),install.__file__,boot]
            def timeout_exec():
                os.dup2(captures[0][1],1);os.dup2(captures[1][1],2)
                os.execve('/usr/bin/timeout',timer_argv,{})
            timer_record=latch.reserve_child('timeout',root_fd,lease_fd,rr,rw,gr,gw,captures[0][1],captures[1][1])
            install.journal(journal_fd,{'state':'BEFORE_TIMER_FORK'})
            timer_started_boot=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
            timer_pid,timer_fd,timer_birth=guard.fork_and_pin(timer_record,timeout_exec)
        size=struct.unpack('!I',read_exact(rr,4,deadline,template))[0]
        if not 0<size<=4092:raise ValueError('READY size')
        ready=json.loads(read_exact(rr,size,deadline,template),object_pairs_hook=install.unique)
        if type(ready) is not dict or set(ready)!={'pid','birth','parent_pid','pgrp','boot_id','nonce'} or ready['boot_id']!=boot or ready['nonce']!=intent['nonce']:raise ValueError('READY record')
        actors=fresh_controls(prelim,install,template,deadline)
        timer,child,argv_sha=verify_private_group(prelim,install,intent,timer_pid,timer_birth,ready,timer_argv,actors)
        child_record=PidfdCustodyRecord(journal_fd,intent['nonce']);latch.retain(child_record)
        with deferred_fork.DeferredFork() as guard:
            child_fd=guard.acquire_and_pin(child_record,ready['pid'],ready['birth'])
        install.journal(journal_fd,{'state':'READY_CAPTURED','timer':timer,'installer':child,'timer_argv_sha256':argv_sha})
        install.verify_base_runtime(template['interpreter']);install.verify_host_receipt(host_fd,template)
        actors=fresh_controls(prelim,install,template,deadline)
        verify_private_group(prelim,install,intent,timer_pid,timer_birth,ready,timer_argv,actors)
        release=dict(template);release.update(controller_pid=timer_pid,controller_birth=timer_birth,installer_pid=ready['pid'],installer_birth=ready['birth'],keeper_pid=os.getpid(),keeper_birth=obs.process(os.getpid())[0])
        data=(json.dumps(release,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();digest=hashlib.sha256(data).hexdigest();name='INSTALL-RELEASE-'+intent['nonce']+'.json'
        install.journal(journal_fd,{'state':'BEFORE_RELEASE_CREATE','sha256':digest})
        writer=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=root_fd);latch.retain(writer)
        os.fchmod(writer,0o400);install.write_all(writer,data);os.fsync(writer);os.fsync(root_fd);identity=install.ident(os.fstat(writer))
        install.journal(journal_fd,{'state':'BEFORE_RELEASE_WRITER_CLOSE','historical_fd':writer,'identity':identity})
        old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
        try:
            with latch.lock:latch.retained.remove(writer)
            try:os.close(writer)
            except BaseException:
                try:install.journal(journal_fd,{'state':'RELEASE_WRITER_CLOSURE_UNKNOWN','historical_fd':writer,'do_not_use_or_retry':True})
                except BaseException:pass
                raise
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
        rfd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);latch.retain(rfd)
        if install.ident(os.fstat(rfd))!=identity:raise ValueError('release inode drift')
        before=install.flags(rfd);install.journal(journal_fd,{'state':'BEFORE_RELEASE_IMMUTABLE','prior_flags':before})
        fcntl.ioctl(rfd,install.SETFLAGS,struct.pack('I',before|install.IMMUTABLE))
        if not install.flags(rfd)&install.IMMUTABLE:raise ValueError('release not sealed')
        os.fsync(rfd);os.fsync(root_fd)
        if hashlib.sha256(install.read_stable(rfd,install.MAX_SOURCE)).hexdigest()!=digest:raise ValueError('release changed')
        install.journal(journal_fd,{'state':'RELEASE_SEALED','sha256':digest});install.journal(journal_fd,{'state':'BEFORE_GO'})
        actors=fresh_controls(prelim,install,template,deadline);verify_tools(install,intent,template,timer_started_boot)
        completion.verify_creation_custody(install,owner_fd,template,intent)
        install.verify_base_runtime(template['interpreter']);install.verify_host_receipt(host_fd,template)
        if not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000:raise ValueError('usage observation stale')
        verify_private_group(prelim,install,intent,timer_pid,timer_birth,ready,timer_argv,actors)
        if os.write(gw,b'G'+digest.encode())!=65:raise OSError('GO short')
        if read_exact(rr,1,deadline,template)!=b'L':raise ValueError('lease acknowledgement')
        latch.lease_disposition='HELD'
        install.journal(journal_fd,{'state':'GO_AND_LEASE_HELD','installer_pid':ready['pid'],'timer_pid':timer_pid})
        terminals=monitor_owned(latch,install,journal_fd,timer_pid,timer_fd,ready['pid'],child_fd,template,intent['join_capture_reserve_ns'])
        census=completion.census_empty(proc_fd,intent['proc_scope'],os.getpid(),timer_pid,template)
        proof=completion.install_proof(install,root_fd,code_fd,closure_fd,intent['nonce'],digest,template,latch.retained)
        capture_results=[completion.close_capture(install,latch,timer_record,journal_fd,root_fd,fd,name,template) for name,fd in captures]
        census=completion.census_empty(proc_fd,intent['proc_scope'],os.getpid(),timer_pid,template)
        custody=completion.verify_creation_custody(install,owner_fd,template,intent)
        completion.need_time(template)
        result={'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':intent['nonce'],'authority':None,
                'native_release':False,'native_currentfree':None,'terminals':terminals,'census':census,
                'creation_custody_verified':True,'creation_custody':custody,'source_closure_sha256':install.CLOSURE_SHA256,
                'keeper':{'pid':os.getpid(),'birth':obs.process(os.getpid())[0]},'timer':timer,'installer':child,
                'release_sha256':digest,'install_proof':proof,'captures':capture_results,
                'lease_disposition_at_handoff':'HELD','operation_lease_fd_closed':False}
        # Full nonce/identity/source-bound proof is durable and handed to the Root
        # capture before any authorized operation-only lease close.
        completion.publish_full_result(install,latch,journal_fd,root_fd,intent['nonce'],result,template)
        completion.verify_creation_custody(install,owner_fd,template,intent)
        result['operation_lease_fd_closed']=completion.retire_lease_if_authorized(install,latch,timer_record,journal_fd,lease_fd,owner_fd,release,result)
        return result,latch
    except BaseException as error:
        if timer_record is not None:timer_record.unknown(error)
        else:latch.fail(error)
        if journal_fd is not None:
            try:install.journal(journal_fd,{'state':'UNKNOWN_RETAINED','error_type':type(error).__name__,'nonce_consumed':True,'lease_disposition':getattr(latch,'lease_disposition','UNKNOWN')})
            except BaseException:pass
        raise IssuerUnknown(latch) from error
