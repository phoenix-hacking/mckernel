"""Functional M14 owned control-process retirement; source only, no native cleanup."""
import fcntl
import math
from decimal import Decimal
import hashlib
import json
import os
import select
import signal
import stat
import sys
import time
from pathlib import Path

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
NONCE='8c12bd228ca26f54732752129977b7310a74234a5d8812faaaa8658be5925bec'
RES=BASE/'root-install-actual-caller-3'/'reservations'/('install-'+NONCE)
CAPTURE_SHA='bc1acc4935f8688a4a38e8920607f995c4fe40029e8a7ee536dbd411db2107e7'
STDERR_SHA='5ea1849eb55709f2eab2a3c199648596b2f6e482185b4e63ca4589a186354599'
PARENT_BODY_SHA='4acd57e90c1c38fc505960fcef34942e06ca5d7d62b7c8b2942f1aa16497d548'
REQUEST_SHA='176074ffe7f98766e4b8b14c572082bf2e4af4256fd970c55fd9042d97ae0b2b'
ARGV_SHA='7355025b0b6a1b717cb052849f71cf0ff4004ee179f1e6561d3a41c4d635f09f'
RES_SHA='97f8b093402985b5d937629afee2587053bfae42181e226c640d2ac985c73b92'
PROFILE_SHA='a57549a183a6447c3e42f03e4bf4d2b4c241b4d608fb501a7c2c9a8c975823bf'
BOOT_SHA='96f4c1496230b4de86a2edf2bfcd6318c9df0c2ddf9d57b5ee8ca04a31c61cda'
COMPAT_SHA='068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'
ROOT=3121867;ROOT_BIRTH='120224742';SUDO=3121864;SUDO_BIRTH='120224735';CALLER=3121863;CALLER_BIRTH='120224717'
KEEPER=3121868;KEEPER_BIRTH='120224750'
OUTER=2996005;OUTER_BIRTH='118034116';UTC_CAP=1793774133*10**9
MAX=2*1024*1024
STOPS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)
HELD=[]


def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:raise ValueError('duplicate JSON key')
        result[k]=v
    return result


def bounded(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size>limit:raise ValueError('bounded file')
        raw=b''
        while len(raw)<=limit:
            part=os.read(fd,min(65536,limit+1-len(raw)))
            if not part:break
            raw+=part
        after=os.fstat(fd)
        if len(raw)!=st.st_size or len(raw)>limit or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('file changed')
        return raw
    finally:os.close(fd)


def proc_read(path,limit):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        chunks=[];total=0
        while total<=limit:
            part=os.read(fd,min(65536,limit+1-total))
            if not part:break
            chunks.append(part);total+=len(part)
        if total>limit:raise ValueError('proc read bound')
        return b''.join(chunks)
    finally:os.close(fd)


def checked(path,expected):
    raw=bounded(path,MAX)
    if sha(raw)!=expected:raise ValueError('bound evidence differs')
    return raw


def proc(pid):
    path=Path('/proc/%d'%pid)
    with (path/'stat').open('r') as stream:raw=stream.read(8193)
    if len(raw)>8192 or ')' not in raw:raise ValueError('proc stat bound')
    f=raw.rsplit(')',1)[1].split()
    if len(f)<20 or f[0] in ('Z','X','x'):raise ValueError('process not live')
    with (path/'comm').open('r') as stream:comm=stream.read(128).strip()
    return {'pid':pid,'birth':f[19],'ppid':int(f[1]),'pgrp':int(f[2]),'uid':os.stat(str(path)).st_uid,'comm':comm}


def require_root_session_ancestor():
    cursor=os.getppid();seen=set()
    for _ in range(32):
        if cursor<=1 or cursor in seen:break
        seen.add(cursor);row=proc(cursor)
        if cursor==OUTER:
            if row['birth']!=OUTER_BIRTH or row['uid']!=1000:raise ValueError('Root session identity changed')
            return
        cursor=row['ppid']
    raise ValueError('actual Root session ancestor absent')


def live_chain():
    a=proc(OUTER);b=proc(CALLER);c=proc(SUDO);d=proc(ROOT)
    if (a['birth']!=OUTER_BIRTH or a['uid']!=1000 or b['birth']!=CALLER_BIRTH or b['uid']!=1000 or b['ppid']!=OUTER or
        c['birth']!=SUDO_BIRTH or c['uid']!=0 or c['ppid']!=CALLER or c['comm']!='sudo' or
        d['birth']!=ROOT_BIRTH or d['uid']!=0 or d['ppid']!=SUDO or d['comm']!='python3'):
        raise ValueError('owned exact process chain changed')
    return {'outer':a,'caller':b,'sudo':c,'root':d}


def failure_notes(capture):
    raw=checked(RES/'stderr.capture',STDERR_SHA)
    path_stat=os.stat(str(RES/'stderr.capture'))
    if (path_stat.st_dev,path_stat.st_ino)!=(capture['stderr']['device'],capture['stderr']['inode']):raise ValueError('stderr capture identity')
    lines=raw.splitlines(keepends=True)
    if len(lines)!=2:raise ValueError('exact failure note count')
    notes=[json.loads(line,object_pairs_hook=unique) for line in lines]
    if any(canonical(note)!=line for note,line in zip(notes,lines)):raise ValueError('noncanonical failure note')
    common={'record_type':'ROOT_INSTALL_FAILURE_DATA_V1','scope':'ROOT_CODE_INSTALL_ONLY','authority':None,
      'native_release':False,'native_currentfree':None,'outcome':'UNKNOWN','errno':None,'message_policy':'exact_fixed',
      'root_parent':{'pid':ROOT,'birth':ROOT_BIRTH},'keeper':{'pid':KEEPER,'birth':KEEPER_BIRTH}}
    expected=[dict(common,role='keeper',stage='child_entry',error_class='ValueError',error_message='directory ancestry is not root controlled'),
              dict(common,role='root_parent',stage='lease_handoff',error_class='Unknown',error_message='custody channel lost')]
    if canonical(notes)!=canonical(expected):raise ValueError('actual failure note differs')
    return notes


def allowed_source_files(argv):
    child_dir=BASE/'root-install-direct-child-successor-4'
    manifest=json.loads(checked(child_dir/'SOURCE-BOUND.json','5cc545b852a95ff9504baac5a97a6936c0647127691908fd88ac52934ea256b8'),object_pairs_hook=unique)
    closure=json.loads(checked(BASE/'root-install-source-10'/'SOURCE-CLOSURE.json','81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'),object_pairs_hook=unique)
    package={row['name']:row['sha256'] for row in closure['files']}
    result={str(BASE/'root-install-source-10'/'package'/name):package[name] for name in ('ownership_latch.py','graph_observations.py','pidfd_compat.py','pidfd_custody.py','deferred_fork.py')}
    for name in ('direct_entry.py','install_source_closure.py','install_completion.py','install_issuer.py','phase0.py','WAIT-INSTALL-CODE.py','DIRECT-MODEL.json'):
        result[str(child_dir/name)]=manifest['source_sha256'][name]
    result.update({str(BASE/'root-install-parent-successor-1'/'parent_control.py'):'eda1ff0139c3bbf0c713009fc7728eccf3418cc7ce5d028731bc443837d49bbe',
      str(BASE/'postjoin-daemon-metadata-observer-source-1'/'root_parent_preliminary.py'):'de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d',
      str(BASE/'root-install-parent-successor-5'/'root_parent.py'):PARENT_BODY_SHA,
      str(BASE/'root-install-source-10'/'SOURCE-CLOSURE.json'):'81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6',
      str(BASE/'root-install-caller-data-output-1'/'data_output.py'):'6e1197061e4c7f99abcea965c6b1fd6beb18556497174ed38e725dbbeeef3b22',
      argv[18]:argv[19]})
    return result


def target_metadata(capture,argv):
    self_ns=os.stat('/proc/self/ns/pid');target_ns=os.stat('/proc/%d/ns/pid'%ROOT)
    if (self_ns.st_dev,self_ns.st_ino)!=(target_ns.st_dev,target_ns.st_ino):raise ValueError('target PID namespace differs')
    root=Path('/proc/%d'%ROOT);tasks=list((root/'task').iterdir())
    if len(tasks)!=1 or tasks[0].name!=str(ROOT):raise ValueError('target thread set changed')
    with (root/'task'/str(ROOT)/'children').open('r') as stream:children=stream.read(4097)
    if len(children)>4096 or children.strip():raise ValueError('target children present')
    entries=list((root/'fd').iterdir())
    if len(entries)>128 or not {0,1,2}<={int(item.name) for item in entries}:raise ValueError('target FD count or capture bound')
    rows=[];pidfds=[];allowed=allowed_source_files(argv);expected_parent=BASE/'root-install-parent-successor-5'/'root_parent.py'
    checked(expected_parent,PARENT_BODY_SHA);parent_stat=os.stat(str(expected_parent));parent_seen=False
    for item in entries:
        n=int(item.name);target=os.readlink(str(item));st=os.stat(str(item))
        if target.startswith('/var/lib/mckernel-install-'+NONCE) or target.startswith('/var/lib/mckernel-code-'+NONCE):raise ValueError('R3 output custody present')
        if n==0:
            expected_st=os.stat(str(RES/'request.json'))
            if (st.st_dev,st.st_ino)!=(expected_st.st_dev,expected_st.st_ino):raise ValueError('live request FD differs')
        if n in (1,2):
            expected=capture['stdout' if n==1 else 'stderr']
            if (st.st_dev,st.st_ino)!=(expected['device'],expected['inode']):raise ValueError('live capture FD differs')
        if target==str(expected_parent):
            if (st.st_dev,st.st_ino)!=(parent_stat.st_dev,parent_stat.st_ino):raise ValueError('parent source inode drift')
            parent_seen=True
        if target=='anon_inode:[pidfd]':
            info=proc_read(root/'fdinfo'/str(n),65536).decode()
            fields=dict(line.split(':',1) for line in info.splitlines() if ':' in line)
            if fields.get('Pid','').strip()!='-1' or fields.get('NSpid','').strip()!='-1':raise ValueError('retained keeper pidfd not reaped')
            pidfds.append(n)
        elif n not in (0,1,2) and target in allowed:
            expected=allowed[target];named=os.stat(target)
            if (st.st_dev,st.st_ino)!=(named.st_dev,named.st_ino) or sha(bounded(target,MAX))!=expected:raise ValueError('held source inode or bytes changed')
        elif n not in (0,1,2) and not target.startswith('socket:'):
            raise ValueError('unlisted target FD custody')
        rows.append({'fd':n,'target':target,'device':st.st_dev,'inode':st.st_ino,'mode_type':stat.S_IFMT(st.st_mode)})
    if not parent_seen or len(pidfds)!=1:raise ValueError('single source-bound keeper ChildRecord pidfd absent')
    for prefix in ('mckernel-install-','mckernel-code-'):
        if os.path.lexists('/var/lib/'+prefix+NONCE):raise ValueError('R3 operation output exists')
    return {'root':proc(ROOT),'pid_namespace':{'device':self_ns.st_dev,'inode':self_ns.st_ino},'thread_count':1,'children':[], 'fd_metadata':sorted(rows,key=lambda x:x['fd']),
      'keeper_binding':{'pid':KEEPER,'birth':KEEPER_BIRTH,'pidfd':pidfds[0],
         'basis':'PARENT5_SINGLE_KEEPER_CHILDRECORD_BEFORE_LEASE','pidfd_Pid':'-1','pidfd_NSpid':'-1','direct_wait_status':'UNKNOWN'},
      'installer':'NOT_OBSERVED_BEFORE_CREATE_DIR','reservation_release':False,'native_release':False,'native_currentfree':None}


def own_pidfd_identity(fd):
    raw=proc_read('/proc/self/fdinfo/%d'%fd,65536).decode()
    fields=dict(line.split(':',1) for line in raw.splitlines() if ':' in line)
    if fields.get('Pid','').strip()!=str(ROOT) or os.readlink('/proc/self/fd/%d'%fd)!='anon_inode:[pidfd]':raise ValueError('owned pidfd target differs')
    if not fcntl.fcntl(fd,fcntl.F_GETFD)&fcntl.FD_CLOEXEC:raise ValueError('pidfd CLOEXEC')


def output(value):
    raw=canonical(value)
    if len(raw)>65536 or os.write(1,raw)!=len(raw):raise OSError('short outcome DATA')
    os.fsync(1)


def wait_terminal(fd,until,release):
    poll=select.poll();poll.register(fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while time.clock_gettime_ns(time.CLOCK_BOOTTIME)<until and time.monotonic_ns()<release['expires_mono_ns'] and time.time_ns()<release['utc_cap_ns']:
        events=poll.poll(100)
        if not events:continue
        mask=events[0][1]
        if mask&(select.POLLERR|select.POLLNVAL):raise ValueError('pidfd poll unknown')
        if mask&(select.POLLIN|select.POLLHUP):return True
    return False


def close_owned(record):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        if record['state']!='VERIFIED_HELD' or type(record['fd']) is not int:raise ValueError('pidfd not verified')
        fd=record['fd'];record['fd']=None;record['historical_fd']=fd;record['state']='CLOSING'
        try:os.close(fd)
        except BaseException:
            record['state']='CLOSURE_UNKNOWN';raise
        record['state']='VERIFIED_CLOSED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def run(compat,prelim,release,release_sha):
    if os.getuid()!=0 or os.geteuid()!=0 or os.sched_getaffinity(0)!={6}:raise ValueError('root/CPU6 stop owner required')
    capture=os.fstat(1);flags=fcntl.fcntl(1,fcntl.F_GETFL)
    if not stat.S_ISREG(capture.st_mode) or capture.st_nlink!=1 or (flags&os.O_ACCMODE)==os.O_RDONLY:raise ValueError('actual stdout capture required')
    require_root_session_ancestor()
    expected={'status':'REVIEWED_ONE_SHOT_OWNED_CONTROL_STOP','scope':'ROOT_INSTALL_CONTROL_ONLY','nonce':NONCE,
      'root_pid':ROOT,'root_birth':ROOT_BIRTH,'sudo_pid':SUDO,'sudo_birth':SUDO_BIRTH,'caller_pid':CALLER,'caller_birth':CALLER_BIRTH,
      'keeper_pid':KEEPER,'keeper_birth':KEEPER_BIRTH,
      'request_sha256':REQUEST_SHA,'argv_sha256':ARGV_SHA,'stderr_sha256':STDERR_SHA,'capture_sha256':CAPTURE_SHA,'parent_body_sha256':PARENT_BODY_SHA,'profile_sha256':PROFILE_SHA,
      'native_release':False,'native_currentfree':None,'reservation_release':False}
    extra={'issued_boot_ns','expires_boot_ns','expires_mono_ns','utc_cap_ns','weekly_observed_utc_ns','weekly_used_percent','service_status','controls_sha256','capacity_sha256'}
    if type(release) is not dict or set(release)!=set(expected)|extra or sha(canonical(release))!=release_sha:raise ValueError('exact separately reviewed stop release required')
    issued=release['issued_boot_ns'];expires=release['expires_boot_ns'];now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if type(issued) is not int or type(expires) is not int or not issued<=now<expires<=issued+30000000000:raise ValueError('fresh reviewed stop release required')
    percent=release['weekly_used_percent'];wall=time.time_ns()
    if type(percent) not in (int,float) or not math.isfinite(percent) or not 0<=percent<100 or type(release['weekly_observed_utc_ns']) is not int or not 0<=wall-release['weekly_observed_utc_ns']<=30000000000 or release['service_status']!='NO_NEW_REJECTION':raise ValueError('fresh included-only status required')
    controls,_=prelim.read_bound(prelim.CONTROLS,1<<20);capacity,_=prelim.read_bound(prelim.CAPACITY,1<<20)
    if sha(controls)!=release['controls_sha256'] or sha(capacity)!=release['capacity_sha256']:raise ValueError('actual controls changed')
    caps=prelim.controller_checks(prelim.strict_json(controls),prelim.strict_json(capacity),time.time())
    ns=lambda x:int(Decimal(str(x))*1000000000)
    if type(release['expires_mono_ns']) is not int or type(release['utc_cap_ns']) is not int or not (expires<=ns(caps['boot_deadline']) and time.monotonic_ns()<release['expires_mono_ns']<=ns(caps['monotonic_deadline']) and wall<release['utc_cap_ns']<=min(ns(caps['deadline']),UTC_CAP)):raise ValueError('inherited tighter stop caps')
    if canonical({k:release[k] for k in expected})!=canonical(expected):raise ValueError('stop release scope differs')
    request=json.loads(checked(RES/'request.json',REQUEST_SHA),object_pairs_hook=unique)
    reservation=json.loads(checked(RES/'RESERVATION.json',RES_SHA),object_pairs_hook=unique)
    argv=json.loads(checked(RES/'argv.json',ARGV_SHA),object_pairs_hook=unique)
    capture=json.loads(checked(RES/'CAPTURE.json',CAPTURE_SHA),object_pairs_hook=unique)
    failure_notes(capture)
    if (request.get('nonce')!=NONCE or request.get('profile_sha256')!=PROFILE_SHA or reservation.get('nonce')!=NONCE or
        reservation.get('status')!='RESERVED_UNKNOWN_UNTIL_ROOT_JOIN' or reservation.get('reservation_release',False) is not False):raise ValueError('retained reservation differs')
    if type(argv) is not list or len(argv)!=22 or sha(argv[16].encode())!=BOOT_SHA or argv[12:16]!=['/usr/bin/python3','-I','-B','-c']:raise ValueError('reviewed operation argv')
    if time.time_ns()>=UTC_CAP:raise ValueError('weekly cap ended')
    # Verify source/argv and exact retained custody before opening a pidfd.
    live_chain();target_metadata(capture,argv)
    cmd=proc_read('/proc/%d/cmdline'%ROOT,262144)
    if cmd!=b'\0'.join(os.fsencode(x) for x in argv[12:])+b'\0':raise ValueError('actual root bootstrap argv differs')
    exe=os.open('/proc/%d/exe'%ROOT,os.O_RDONLY|os.O_CLOEXEC)
    try:
        st=os.fstat(exe);system=os.stat('/usr/bin/python3')
        if (st.st_dev,st.st_ino)!=(system.st_dev,system.st_ino) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022:raise ValueError('root interpreter identity')
        h=hashlib.sha256();total=0
        while True:
            part=os.read(exe,65536)
            if not part:break
            total+=len(part)
            if total>128*1024*1024:raise ValueError('interpreter byte bound')
            h.update(part)
        expected_runtime=request['owner_release']['creation_model_approval']['runtime_sha256']
        if h.hexdigest()!=expected_runtime:raise ValueError('root interpreter bytes differ')
    finally:os.close(exe)
    live_chain();target_metadata(capture,argv)
    record={'state':'REGISTERED','fd':None,'historical_fd':None};HELD.append(record)
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOPS)
    try:
        try:fd=compat.open_pidfd(ROOT,0)
        except compat.PidfdVerificationError as error:
            record['fd']=error.fd;record['state']='UNKNOWN_RETAINED';raise
        record['fd']=fd;record['state']='PIDFD_OPENED'
        own_pidfd_identity(fd);record['state']='VERIFIED_HELD'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    # Kernel pins exact process; recheck chain and actual custody immediately.
    live_chain();metadata=target_metadata(capture,argv);own_pidfd_identity(fd)
    if time.time_ns()>=release['utc_cap_ns'] or time.monotonic_ns()>=release['expires_mono_ns'] or time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=expires:raise ValueError('stop release or weekly clock changed')
    output({'status':'PRESTOP_METADATA','nonce':NONCE,'metadata':metadata,'failure_notes_sha256':STDERR_SHA,
            'native_release':False,'native_currentfree':None,'reservation_release':False})
    live_chain();failure_notes(capture);metadata_after=target_metadata(capture,argv);own_pidfd_identity(fd)
    if canonical(metadata_after)!=canonical(metadata):raise ValueError('target metadata drift before signal')
    if time.time_ns()>=release['utc_cap_ns'] or time.monotonic_ns()>=release['expires_mono_ns'] or time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=expires:raise TimeoutError('stop release expired after metadata')
    start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);term_until=min(start+3000000000,expires);end=min(start+8000000000,expires)
    record['signal_phase']='TERM_IN_PROGRESS'
    compat.send_signal(fd,signal.SIGTERM);record['signal_phase']='TERM_SENT'
    terminated=wait_terminal(fd,term_until,release);used_kill=False
    if not terminated:
        terminated=wait_terminal(fd,min(end,time.clock_gettime_ns(time.CLOCK_BOOTTIME)+100000000),release)
    if not terminated:
        own_pidfd_identity(fd)
        if time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=end or time.monotonic_ns()>=release['expires_mono_ns'] or time.time_ns()>=release['utc_cap_ns']:raise TimeoutError('no escalation time')
        record['signal_phase']='KILL_IN_PROGRESS'
        compat.send_signal(fd,signal.SIGKILL);record['signal_phase']='KILL_SENT';used_kill=True;terminated=wait_terminal(fd,end,release)
    if not terminated:raise TimeoutError('target terminal unproved')
    record['signal_phase']='TARGET_TERMINAL'
    output({'status':'TARGET_PIDFD_TERMINAL','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,'kill_used':used_kill,
            'direct_wait':'NOT_OWNER','native_release':False,'native_currentfree':None,'reservation_release':False})
    close_owned(record)
    output({'status':'CONTROL_STOP_COMPLETE_PIDFD_CLOSED','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,
            'pidfd_disposition':record['state'],'caller_sudo_join':'NOT_OBSERVED','native_release':False,'native_currentfree':None,'reservation_release':False})
    return record


def guarded_run(compat,prelim,release,release_sha):
    try:return run(compat,prelim,release,release_sha)
    except BaseException as error:
        record=HELD[-1] if HELD else None
        state=None if record is None else record.get('state')
        phase='BEFORE_PIDFD' if record is None else record.get('signal_phase','BEFORE_SIGNAL')
        try:output({'status':'CONTROL_STOP_UNKNOWN','nonce':NONCE,'target_pid':ROOT,'target_birth':ROOT_BIRTH,
             'signal_phase':phase,'pidfd_disposition':state,'error_type':type(error).__name__,
             'native_release':False,'native_currentfree':None,'reservation_release':False})
        except BaseException:pass
        if record is not None and record.get('fd') is not None:
            # Never discard or reclose an uncertain owned target handle.
            while True:time.sleep(1)
        raise
