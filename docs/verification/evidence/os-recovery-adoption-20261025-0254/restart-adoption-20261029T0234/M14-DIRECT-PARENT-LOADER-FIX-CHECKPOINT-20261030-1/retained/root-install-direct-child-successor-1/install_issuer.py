"""Functional M14 direct-child root leasekeeper. Source only."""
import ctypes
import fcntl
import hashlib
import json
import os
import resource
import select
import socket
import parent_control
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


def verify_direct_tools(install,intent,template):
    for parent in ('/','/usr','/usr/bin'):
        st=os.stat(parent)
        if st.st_uid!=0 or not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)&0o022:raise ValueError('tool ancestry')
    for path,key in (('/usr/bin/sudo','sudo_sha256'),('/usr/bin/taskset','taskset_sha256'),('/usr/bin/prlimit','prlimit_sha256')):
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or not install.hex64(intent[key]) or hashlib.sha256(install.read_stable(fd,128*1024*1024)).hexdigest()!=intent[key]:raise ValueError('tool binding')
        finally:os.close(fd)
    if os.sched_getaffinity(0)!={6}:raise ValueError('CPU6 affinity')
    limits={resource.RLIMIT_AS:(1073741824,1073741824),resource.RLIMIT_CPU:(60,60),resource.RLIMIT_FSIZE:(33554432,33554432),resource.RLIMIT_NOFILE:(256,256),resource.RLIMIT_CORE:(0,0)}
    if any(resource.getrlimit(key)!=value for key,value in limits.items()):raise ValueError('resource profile')
    reserve=intent['join_capture_reserve_ns']
    if type(reserve) is not int or not 1000000000<=reserve<=30000000000 or completion.remaining(template)<=65000000000+reserve:
        raise ValueError('parent deadline and completion reserve')


def fresh_controls(prelim,install,template,deadline):
    bounds(install,template,deadline)
    c,_=prelim.read_bound(prelim.CONTROLS,1<<20);p,_=prelim.read_bound(prelim.CAPACITY,1<<20)
    if hashlib.sha256(c).hexdigest()!=template['controls_sha256'] or hashlib.sha256(p).hexdigest()!=template['capacity_sha256']:raise ValueError('controls changed')
    controls=prelim.strict_json(c);capacity=prelim.strict_json(p);caps=prelim.controller_checks(controls,capacity,time.time())
    ns=lambda v:int(Decimal(str(v))*Decimal(1000000000))
    if caps['boot_id']!=template['boot_id'] or template['deadline_boot_ns']>ns(caps['boot_deadline']) or template['deadline_mono_ns']>ns(caps['monotonic_deadline']) or template['utc_cap_ns']>ns(caps['deadline']):raise ValueError('control caps')
    bounds(install,template,deadline)
    return list(controls['binding'].values())+[capacity['supervisor']]


def _held_open(latch,path,flags,mode=0o777,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        with latch.lock:
            latch.retained.append(None);slot=len(latch.retained)-1
            try:fd=os.open(path,flags,mode,dir_fd=dir_fd)
            except BaseException:
                latch.retained.pop();raise
            latch.retained[slot]=fd
            return fd
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def _held_pipe(latch):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        with latch.lock:
            latch.retained.extend((None,None));slot=len(latch.retained)-2
            try:readfd,writefd=os.pipe2(os.O_CLOEXEC)
            except BaseException:
                del latch.retained[slot:slot+2];raise
            latch.retained[slot:slot+2]=(readfd,writefd)
            return readfd,writefd
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def _expect_ack(channel,caps,latch,prelim,parent_pid,parent_birth,expected):
    value,fds=parent_control.receive(channel,caps,latch.retained,parent_pid)
    if fds or value!=expected:raise ValueError('parent acknowledgement differs')
    _parent_alive(prelim,parent_pid,parent_birth,channel)


def _parent_alive(prelim,pid,birth,channel):
    if os.getppid()!=pid or os.stat('/proc/%d'%pid).st_uid!=0 or str(prelim.identity(pid)['birth'])!=birth:
        raise ValueError('direct Root parent changed')
    poll=select.poll();poll.register(channel.fileno(),select.POLLHUP|select.POLLERR)
    if poll.poll(0):raise EOFError('parent channel lost')


def _wait_child(pid,pidfd,channel,caps):
    poll=select.poll();poll.register(pidfd,select.POLLIN|select.POLLHUP|select.POLLERR)
    poll.register(channel.fileno(),select.POLLHUP|select.POLLERR)
    while parent_control.remaining(caps)>0:
        waited,status=os.waitpid(pid,os.WNOHANG)
        if waited==pid:
            if not os.WIFEXITED(status) or os.WEXITSTATUS(status)!=0:raise ValueError('installer did not exit zero')
            return status
        events=dict(poll.poll(100))
        if events.get(channel.fileno(),0)&(select.POLLHUP|select.POLLERR):raise EOFError('parent lost during install')
        if events.get(pidfd,0)&select.POLLERR:raise OSError('installer pidfd error')
    raise TimeoutError('installer exceeded absolute caps')


def run(install,prelim,intent_fd,intent_sha,source_fd,root_fd,code_fd,lease_path,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd,wait_literal,channel,root_parent_pid,root_parent_birth):
    """Direct child keeper. Any failure retains known FDs and is UNKNOWN."""
    if os.getuid()!=0 or os.geteuid()!=0 or threading.active_count()!=1:raise ValueError('single-thread root keeper required')
    _parent_alive(prelim,root_parent_pid,root_parent_birth,channel)
    if channel.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_SEQPACKET:raise ValueError('seqpacket required')
    channel.setsockopt(socket.SOL_SOCKET,socket.SO_PASSCRED,1)
    install.root_file(intent_fd);raw=install.read_stable(intent_fd,install.MAX_SOURCE)
    if hashlib.sha256(raw).hexdigest()!=intent_sha:raise ValueError('intent bytes')
    intent=json.loads(raw,object_pairs_hook=install.unique)
    template=intent['release_template'];nonce=intent['nonce'];deadline=intent['phase1_deadline_boot_ns']
    if not install.hex64(nonce) or template['nonce']!=nonce or template['root_parent_pid']!=root_parent_pid or template['root_parent_birth']!=root_parent_birth:
        raise ValueError('actual Root parent/nonce binding')
    if any(template[k] is not None for k in ('controller_pid','controller_birth','installer_pid','installer_birth','keeper_pid','keeper_birth')):
        raise ValueError('future process identity already set')
    if hashlib.sha256(wait_literal.encode()).hexdigest()!=intent['wait_literal_sha256']:raise ValueError('waiting source')
    require_outer_ancestor(prelim,intent['outer_pid'],intent['outer_birth'])
    bounds(install,template,deadline);verify_direct_tools(install,intent,template);install.verify_base_runtime(template['interpreter']);install.verify_host_receipt(host_fd,template)
    completion.verify_creation_model(install,owner_fd,template,intent);fresh_controls(prelim,install,template,deadline)
    if type(intent['weekly_used_percent']) not in (int,float) or not 0<=intent['weekly_used_percent']<100 or intent['service_status']!='NO_NEW_REJECTION' or type(intent['weekly_observed_utc_ns']) is not int or not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000:
        raise ValueError('fresh included usage/service required')
    root_check=install.open_exact(template['operation_path'],template['operation_ancestors'],True)
    code_check=install.open_exact(template['code_path'],template['code_ancestors'],True,True)
    source_check=install.open_exact(install.SOURCE_DIR,template['source_ancestors'])
    install.dir_identity(root_fd,template['operation_root'],True);install.dir_identity(root_check,template['operation_root'],True)
    install.dir_identity(code_fd,template['code_parent']);install.dir_identity(code_check,template['code_parent'])
    install.dir_identity(source_fd,template['source_dir']);install.dir_identity(source_check,template['source_dir'])
    for fd,key in ((controls_fd,'controls_sha256'),(capacity_fd,'capacity_sha256'),(host_fd,'host_install_custody_sha256'),(owner_fd,'owner_release_sha256')):
        install.root_file(fd)
        if install.sha(install.read_stable(fd,install.MAX_SOURCE))!=template[key]:raise ValueError('receipt binding')
    if os.path.dirname(lease_path)!=template['operation_path'] or os.path.basename(lease_path) in ('','.','..'):raise ValueError('lease location')
    caps={'boot_ns':min(deadline,template['deadline_boot_ns']),'mono_ns':template['deadline_mono_ns'],'utc_ns':template['utc_cap_ns']}
    latch=CustodyLatch('KEEPER_HELD');latch.lease_disposition='UNLOCKED'
    latch.retain(intent_fd,source_fd,root_fd,code_fd,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd,channel)
    record=None;journal_fd=None
    try:
        lease=_held_open(latch,os.path.basename(lease_path),os.O_RDWR|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
        st=os.fstat(lease)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or install.ident(st)!=template['lease']:raise ValueError('actual lease inode')
        journal_fd=_held_open(latch,'INSTALL-START-'+nonce+'.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
        os.fsync(root_fd)
        keeper_birth=obs.process(os.getpid())[0]
        install.journal(journal_fd,{'state':'START_CONSUMED','nonce':nonce,'intent_sha256':intent_sha,'keeper_pid':os.getpid(),'keeper_birth':keeper_birth})
        lease_event={'type':'LEASE','nonce':nonce,'seq':1,'keeper_pid':os.getpid(),'keeper_birth':keeper_birth,'lease':template['lease']}
        parent_control.send(channel,lease_event,[lease],caps)
        _expect_ack(channel,caps,latch,prelim,root_parent_pid,root_parent_birth,{'type':'LEASE_ACK','nonce':nonce,'seq':1,'lease':template['lease']})
        captures=[]
        for stream in ('stdout','stderr'):
            name='INSTALL-CAPTURE-'+nonce+'-'+stream
            fd=_held_open(latch,name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
            os.fchmod(fd,0o600);os.fsync(fd);os.fsync(root_fd);captures.append((name,fd))
            install.journal(journal_fd,{'state':'CAPTURE_CREATED','name':name,'identity':install.ident(os.fstat(fd))})
        rr,rw=_held_pipe(latch);gr,gw=_held_pipe(latch)
        inherited=[install._BOOTSTRAP_SOURCE_FD,rw,gr,root_fd,source_fd,code_fd,lease,closure_fd,controls_fd,capacity_fd,host_fd,owner_fd]
        for fd in inherited:os.set_inheritable(fd,True)
        argv=['/usr/bin/python3','-I','-B','-c',wait_literal]+[str(fd) for fd in inherited]+[nonce,str(deadline),install.__file__,template['boot_id']]
        def child_exec():
            os.setpgid(0,0)
            os.dup2(captures[0][1],1);os.dup2(captures[1][1],2)
            os.execve('/usr/bin/python3',argv,{})
        record=latch.reserve_child('installer',root_fd,lease,rr,rw,gr,gw,captures[0][1],captures[1][1])
        install.journal(journal_fd,{'state':'BEFORE_INSTALLER_FORK'})
        with deferred_fork.DeferredFork() as guard:
            child_pid,child_fd,child_birth=guard.fork_and_pin(record,child_exec)
        size=struct.unpack('!I',read_exact(rr,4,deadline,template))[0]
        if not 0<size<=4092:raise ValueError('READY size')
        ready=json.loads(read_exact(rr,size,deadline,template),object_pairs_hook=install.unique)
        actual=prelim.identity(child_pid)
        if (ready!={'pid':child_pid,'birth':child_birth,'parent_pid':os.getpid(),'pgrp':child_pid,'boot_id':template['boot_id'],'nonce':nonce} or
            actual['ppid']!=os.getpid() or actual['pgrp']!=child_pid or str(actual['birth'])!=child_birth):raise ValueError('direct installer identity')
        event={'type':'INSTALLER','nonce':nonce,'seq':2,'keeper_pid':os.getpid(),'keeper_birth':keeper_birth,'installer_pid':child_pid,'installer_birth':child_birth,'installer_pgid':child_pid}
        parent_control.send(channel,event,[child_fd],caps)
        ack=dict(event);ack['type']='INSTALLER_ACK';_expect_ack(channel,caps,latch,prelim,root_parent_pid,root_parent_birth,ack)
        release=dict(template);release.update(controller_pid=os.getpid(),controller_birth=keeper_birth,installer_pid=child_pid,installer_birth=child_birth,keeper_pid=os.getpid(),keeper_birth=keeper_birth)
        data=(json.dumps(release,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();release_sha=hashlib.sha256(data).hexdigest()
        name='INSTALL-RELEASE-'+nonce+'.json';install.journal(journal_fd,{'state':'BEFORE_RELEASE_CREATE','sha256':release_sha})
        writer=_held_open(latch,name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o400,dir_fd=root_fd)
        os.fchmod(writer,0o400);install.write_all(writer,data);os.fsync(writer);os.fsync(root_fd);identity=install.ident(os.fstat(writer))
        install.journal(journal_fd,{'state':'BEFORE_RELEASE_WRITER_CLOSE','identity':identity,'historical_fd':writer})
        old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
        try:
            with latch.lock:latch.retained.remove(writer)
            try:os.close(writer)
            except BaseException:
                try:install.journal(journal_fd,{'state':'RELEASE_WRITER_CLOSURE_UNKNOWN','historical_fd':writer,'do_not_use_or_retry':True})
                except BaseException:pass
                raise
        finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
        rfd=_held_open(latch,name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
        if install.ident(os.fstat(rfd))!=identity:raise ValueError('release identity')
        fcntl.ioctl(rfd,install.SETFLAGS,struct.pack('I',install.flags(rfd)|install.IMMUTABLE));os.fsync(rfd);os.fsync(root_fd)
        install.root_file(rfd)
        if install.sha(install.read_stable(rfd,install.MAX_SOURCE))!=release_sha:raise ValueError('release readback')
        install.journal(journal_fd,{'state':'RELEASE_SEALED','sha256':release_sha})
        go={'type':'GO_READY','nonce':nonce,'seq':3,'keeper_pid':os.getpid(),'keeper_birth':keeper_birth,'installer_pid':child_pid,'installer_birth':child_birth,'release_sha256':release_sha}
        parent_control.send(channel,go,[root_fd,code_fd,closure_fd],caps)
        ack=dict(go);ack['type']='GO_AUTH';_expect_ack(channel,caps,latch,prelim,root_parent_pid,root_parent_birth,ack)
        _parent_alive(prelim,root_parent_pid,root_parent_birth,channel);verify_direct_tools(install,intent,template);fresh_controls(prelim,install,template,deadline)
        completion.verify_creation_model(install,owner_fd,template,intent);install.verify_host_receipt(host_fd,template)
        if not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000:raise ValueError('included usage expired')
        actual=prelim.identity(child_pid)
        if actual['ppid']!=os.getpid() or actual['pgrp']!=child_pid or str(actual['birth'])!=child_birth:raise ValueError('installer changed')
        fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB);latch.lease_disposition='HELD'
        if os.write(gw,b'G'+release_sha.encode())!=65:raise OSError('GO short')
        if read_exact(rr,1,deadline,template)!=b'L':raise ValueError('lease acknowledgement')
        install.journal(journal_fd,{'state':'GO_AND_LEASE_HELD','installer_pid':child_pid})
        caps={'boot_ns':template['deadline_boot_ns'],'mono_ns':template['deadline_mono_ns'],'utc_ns':template['utc_cap_ns']}
        status=_wait_child(child_pid,child_fd,channel,caps)
        install.journal(journal_fd,{'state':'INSTALLER_DIRECT_WAIT','installer_pid':child_pid,'birth':child_birth,'status':status})
        proof=completion.install_proof(install,root_fd,code_fd,closure_fd,nonce,release_sha,template,latch.retained)
        results=[completion.close_capture(install,latch,record,journal_fd,root_fd,fd,name,template) for name,fd in captures]
        model=completion.verify_creation_model(install,owner_fd,template,intent)
        result={'status':'INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ','nonce':nonce,'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN','installer_wait_status':status,'installer':{'pid':child_pid,'birth':child_birth,'pgid':child_pid},'keeper':{'pid':os.getpid(),'birth':keeper_birth},'release_sha256':release_sha,'install_proof':proof,'captures':results,'creation_model':model,'source_closure_sha256':install.CLOSURE_SHA256,'lease_disposition_at_handoff':'HELD'}
        completion.publish_full_result(install,latch,journal_fd,root_fd,nonce,result,template)
        message={'type':'RESULT','nonce':nonce,'seq':4,'keeper_pid':os.getpid(),'keeper_birth':keeper_birth,'installer_pid':child_pid,'installer_birth':child_birth,'release_sha256':release_sha,'result':result}
        parent_control.send(channel,message,[root_fd,code_fd,closure_fd],caps)
        result_sha=hashlib.sha256(parent_control.canonical(message)).hexdigest()
        _expect_ack(channel,caps,latch,prelim,root_parent_pid,root_parent_birth,{'type':'RESULT_ACK','nonce':nonce,'seq':4,'result_sha256':result_sha})
        install.journal(journal_fd,{'state':'RESULT_PARENT_ACK','nonce':nonce,'result_sha256':result_sha})
        return result,latch
    except BaseException as error:
        if record is not None:record.unknown(error)
        else:latch.fail(error)
        if journal_fd is not None:
            try:install.journal(journal_fd,{'state':'UNKNOWN_RETAINED','error_type':type(error).__name__,'nonce_consumed':True,'lease_disposition':getattr(latch,'lease_disposition','UNKNOWN')})
            except BaseException:pass
        raise IssuerUnknown(latch) from error
