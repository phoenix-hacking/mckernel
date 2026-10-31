"""Functional M14 interpreter-ancestry repair; source only, no security testing."""
import errno
import fcntl
import hashlib
import json
import os
import signal
import stat
import time
from decimal import Decimal
from pathlib import Path

DEV=66306
EXPECTED=[('/',2,0o755,1792292390631682834,1792292390631682834),
          ('/usr',1048577,0o755,1612896530000000000,1626423154427998977),
          ('/usr/bin',1048578,0o777,1793383731386311743,1793383731386311743)]
MOUNT='29 1 259:2 / / rw,relatime shared:1 - ext4 /dev/nvme0n1p2 rw,errors=remount-ro'
NONCE='8c12bd228ca26f54732752129977b7310a74234a5d8812faaaa8658be5925bec'
OUTER=2996005;OUTER_BIRTH='118034116';OWNER=3121867;OWNER_BIRTH='120224742';CALLER=3121863;CALLER_BIRTH='120224717';SUDO=3121864;SUDO_BIRTH='120224735'
OBSERVATION='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-actual-caller-3/USR-BIN-MODE-OBSERVATION.json'
OBSERVATION_SHA='7bbafed0badf8f7c745782abaf583a0d76b59d9ff15a0afa8369dff94d3995f8'
UTC_CAP=1793774133*10**9
STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)
HELD=[]


def canon(v):return (json.dumps(v,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(raw):return hashlib.sha256(raw).hexdigest()
def hex64(s):return type(s) is str and len(s)==64 and all(c in '0123456789abcdef' for c in s)


def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:raise ValueError('duplicate JSON key')
        out[k]=v
    return out


def read_small(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        out=b''
        while len(out)<=limit:
            part=os.read(fd,min(65536,limit+1-len(out)))
            if not part:break
            out+=part
        if len(out)>limit:raise ValueError('bounded read exceeded')
        return out
    finally:os.close(fd)


def proc(pid):
    data=read_small('/proc/%d/stat'%pid,8192).decode().rsplit(')',1)[1].split()
    if len(data)<20 or data[0] in ('Z','X','x'):raise ValueError('process not live')
    return {'pid':pid,'ppid':int(data[1]),'birth':data[19],'uid':os.stat('/proc/%d'%pid).st_uid}


def root_session():
    cursor=os.getppid();seen=set()
    for _ in range(32):
        if cursor<=1 or cursor in seen:break
        seen.add(cursor);row=proc(cursor)
        if cursor==OUTER:
            if row['birth']!=OUTER_BIRTH or row['uid']!=1000:raise ValueError('Root session changed')
            return
        cursor=row['ppid']
    raise ValueError('actual Root session ancestor absent')


def mount_table():
    raw=read_small('/proc/self/mountinfo',1024*1024)
    lines=raw.decode().splitlines()
    if MOUNT not in lines:raise ValueError('expected host root mount differs')
    for line in lines:
        fields=line.split(' ')
        if len(fields)<7 or '-' not in fields:raise ValueError('mountinfo malformed')
        if fields[4] in ('/usr','/usr/bin'):raise ValueError('unexpected nested mount')
    return raw


def no_acl(fd):
    for name in ('system.posix_acl_access','system.posix_acl_default'):
        try:os.getxattr(fd,name)
        except OSError as error:
            if error.errno==errno.ENODATA:continue
            raise
        raise ValueError('directory ACL present')


def open_owned(path,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        rec={'state':'PENDING_OPEN','fd':None,'historical_fd':None};HELD.append(rec)
        try:fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dir_fd)
        except BaseException:
            rec['state']='OPEN_UNKNOWN';raise
        rec['fd']=fd;rec['state']='OWNED';return rec
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def close_owned(rec):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        if rec['state']!='OWNED' or type(rec['fd']) is not int:raise ValueError('descriptor not owned')
        fd=rec['fd'];rec['fd']=None;rec['historical_fd']=fd;rec['state']='CLOSING'
        try:os.close(fd)
        except BaseException:
            rec['state']='CLOSURE_UNKNOWN';raise
        rec['state']='VERIFIED_CLOSED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def row(fd,path):
    st=os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode):raise ValueError('directory type changed')
    no_acl(fd)
    return {'path':path,'device':st.st_dev,'inode':st.st_ino,'uid':st.st_uid,'gid':st.st_gid,
            'mode':stat.S_IMODE(st.st_mode),'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}


def expected_row(index,value):
    path,ino,mode,mtime,ctime=EXPECTED[index]
    if value!={'path':path,'device':DEV,'inode':ino,'uid':0,'gid':0,'mode':mode,'mtime_ns':mtime,'ctime_ns':ctime}:
        raise ValueError('observed ancestry metadata changed')


def controls(prelim,release):
    control,_=prelim.read_bound(prelim.CONTROLS,1<<20);capacity,_=prelim.read_bound(prelim.CAPACITY,1<<20)
    if sha(control)!=release['controls_sha256'] or sha(capacity)!=release['capacity_sha256']:raise ValueError('actual controls changed')
    caps=prelim.controller_checks(prelim.strict_json(control),prelim.strict_json(capacity),time.time())
    now_boot=time.clock_gettime_ns(time.CLOCK_BOOTTIME);now_mono=time.monotonic_ns();now_utc=time.time_ns()
    ns=lambda x:int(Decimal(str(x))*10**9)
    if not (release['issued_boot_ns']<=now_boot<release['expires_boot_ns']<=min(release['issued_boot_ns']+30000000000,ns(caps['boot_deadline'])) and
       now_mono<release['expires_mono_ns']<=ns(caps['monotonic_deadline']) and now_utc<release['utc_cap_ns']<=min(ns(caps['deadline']),UTC_CAP) and
       type(release['weekly_observed_utc_ns']) is int and 0<=now_utc-release['weekly_observed_utc_ns']<=30000000000 and
       type(release['weekly_used_percent']) in (int,float) and 0<=release['weekly_used_percent']<100 and release['service_status']=='NO_NEW_REJECTION'):
        raise ValueError('actual time/usage/control bounds')
    caller=proc(CALLER);sudo=proc(SUDO);owner=proc(OWNER)
    if (caller['birth']!=CALLER_BIRTH or caller['uid']!=1000 or caller['ppid']!=OUTER or
        sudo['birth']!=SUDO_BIRTH or sudo['uid']!=0 or sudo['ppid']!=CALLER or
        owner['birth']!=OWNER_BIRTH or owner['uid']!=0 or owner['ppid']!=SUDO):raise ValueError('current R3 owner chain changed')
    for key in ('mountns_device','mountns_inode'):
        if type(release[key]) is not int or release[key]<0:raise ValueError('mount namespace binding')
    a=os.stat('/proc/self/ns/mnt');b=os.stat('/proc/%d/ns/mnt'%OWNER)
    if (a.st_dev,a.st_ino)!=(release['mountns_device'],release['mountns_inode']) or (b.st_dev,b.st_ino)!=(a.st_dev,a.st_ino):raise ValueError('mount namespace changed')


def emit(v):
    raw=canon(v)
    if len(raw)>65536 or os.write(1,raw)!=len(raw):raise OSError('short DATA write')
    os.fsync(1)


def repair(prelim,release,release_sha,capture_device,capture_inode,review_path):
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={6}:raise ValueError('root/CPU6 required')
    st=os.fstat(1);flags=fcntl.fcntl(1,fcntl.F_GETFL)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=1000 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or
        (flags&os.O_ACCMODE)==os.O_RDONLY or (st.st_dev,st.st_ino)!=(capture_device,capture_inode)):raise ValueError('actual Root capture differs')
    root_session()
    keys={'status','scope','nonce','observation_sha256','review_sha256','controls_sha256','capacity_sha256','issued_boot_ns','expires_boot_ns',
          'expires_mono_ns','utc_cap_ns','weekly_observed_utc_ns','weekly_used_percent','service_status','mountns_device','mountns_inode','native_release','native_currentfree','reservation_release'}
    if (type(release) is not dict or set(release)!=keys or sha(canon(release))!=release_sha or release['status']!='REVIEWED_ONE_SHOT_FUNCTIONAL_MODE_REPAIR' or
        release['scope']!='USR_BIN_0777_TO_0755' or release['nonce']!=NONCE or release['native_release'] is not False or
        release['native_currentfree'] is not None or release['reservation_release'] is not False or
        any(not hex64(release[k]) for k in ('observation_sha256','review_sha256','controls_sha256','capacity_sha256'))):raise ValueError('reviewed exact release required')
    if release['observation_sha256']!=OBSERVATION_SHA or sha(read_small(OBSERVATION,65536))!=OBSERVATION_SHA or sha(read_small(review_path,1024*1024))!=release['review_sha256']:raise ValueError('actual observation/review binding')
    controls(prelim,release);before_mount=mount_table()
    root=open_owned('/');usr=open_owned('usr',root['fd']);target=open_owned('bin',usr['fd'])
    before=[row(root['fd'],'/'),row(usr['fd'],'/usr'),row(target['fd'],'/usr/bin')]
    for i,value in enumerate(before):expected_row(i,value)
    linked=os.stat('bin',dir_fd=usr['fd'],follow_symlinks=False)
    if (linked.st_dev,linked.st_ino)!=(DEV,1048578) or os.statvfs(target['fd']).f_flag&os.ST_RDONLY:raise ValueError('directory name/mount changed')
    if mount_table()!=before_mount:raise ValueError('mount table changed before repair')
    controls(prelim,release)
    emit({'status':'BEFORE_FCHMOD','nonce':NONCE,'before':before,'mount_sha256':sha(before_mount),
          'native_release':False,'native_currentfree':None,'reservation_release':False})
    if [row(root['fd'],'/'),row(usr['fd'],'/usr'),row(target['fd'],'/usr/bin')]!=before or mount_table()!=before_mount:
        raise ValueError('pre-repair metadata changed after publication')
    controls(prelim,release)
    operation={'state':'NOT_ATTEMPTED'};HELD.append(operation)
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        operation['state']='FCHMOD_IN_PROGRESS'
        try:os.fchmod(target['fd'],0o755)
        except BaseException:
            operation['state']='FCHMOD_UNKNOWN';raise
        operation['state']='FCHMOD_RETURNED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    os.fsync(target['fd']);after=[row(root['fd'],'/'),row(usr['fd'],'/usr'),row(target['fd'],'/usr/bin')]
    if after[:2]!=before[:2] or any(after[2][k]!=before[2][k] for k in ('path','device','inode','uid','gid','mtime_ns')) or after[2]['mode']!=0o755 or after[2]['ctime_ns']<before[2]['ctime_ns']:
        raise ValueError('post-repair metadata differs')
    linked=os.stat('bin',dir_fd=usr['fd'],follow_symlinks=False)
    if (linked.st_dev,linked.st_ino)!=(DEV,1048578) or mount_table()!=before_mount:raise ValueError('post-repair path or mount changed')
    readback=open_owned('bin',usr['fd'])
    if row(readback['fd'],'/usr/bin')!=after[2]:raise ValueError('separate readback differs')
    operation['state']='VERIFIED_0755'
    emit({'status':'FCHMOD_VERIFIED','nonce':NONCE,'after':after,'native_release':False,'native_currentfree':None,'reservation_release':False})
    for rec in (readback,target,usr,root):close_owned(rec)
    emit({'status':'MODE_REPAIR_COMPLETE_DESCRIPTORS_CLOSED','nonce':NONCE,'fd_dispositions':[readback['state'],target['state'],usr['state'],root['state']],
          'native_release':False,'native_currentfree':None,'reservation_release':False})


def guarded_repair(prelim,release,release_sha,capture_device,capture_inode,review_path):
    try:repair(prelim,release,release_sha,capture_device,capture_inode,review_path)
    except BaseException as error:
        try:emit({'status':'REPAIR_UNKNOWN','nonce':NONCE,'error_type':type(error).__name__,'states':[r['state'] for r in HELD],
                  'native_release':False,'native_currentfree':None,'reservation_release':False})
        except BaseException:pass
        # No retry, rollback, recursive operation, or resource release.
        raise
