"""Functional McKernel root-code-install preparation only; no security testing.
Root-approved material and a live authenticated owner are required. No action on import.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
import socket
import stat
import struct
import sys
import time
import types
from decimal import Decimal
from pathlib import Path

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
PHASE=BASE/'root-install-phase0-v10-source-2'
PROFILE_SHA='ed1d1dcb250522bb80c416babfd2c536556aeec8ef8702140a046d4931e776f2'
ENTRY_SHA='c1dc6fb445475fbba81e3600d32f11e8568ff7b74897b549a08c6fa20b3a81a4'
PHASE_SHA='d1e70e5bad642974c84a9eb926861385420ef1f713d1743d2029a79cdf46c119'
V10_PROFILE_SHA='fcf1713be0f08e4f51425e4989a0fe5b75879ae0d07a48e6fbaaab9b9c542687'
SOURCE_REVIEW_SHA='dca2da4105b084e8c7b403db08e4744bfab0b7fc1a92ddd96f19c0eec4de19a3'
PRELIM_SHA='de6de10ff79d07281e95216a5ecf751d03bade1d75445c87abd8a2e0405e124d'
OUTER_PID=2996005
OUTER_BIRTH='118034116'
INVOCATION='20261030T175456Z-0e492844'
PROPOSAL_PATH=BASE/'root-install-resource-admission-1'/'RESOURCE-ADMISSION.PROPOSED.json'
PROPOSAL_SHA='967e90918dae189ecc92fcec4da6d16bf1894235ce4d8a85858c3c3ced04089b'
MAX=2*1024*1024
IOC_GETFLAGS=0x80086601
IMMUTABLE=0x10
UTC_CAP_NS=1793774133*1000000000
TOTAL_BUDGET=int(Decimal('22.5447')*Decimal(1024**3))


def fail(message):raise ValueError(message)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def hex64(value):return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)
def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def unique(pairs):
    out={}
    for k,v in pairs:
        if k in out:fail('duplicate JSON key')
        out[k]=v
    return out


def read_stable(fd,limit=MAX):
    before=os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size>limit:fail('bounded regular file required')
    os.lseek(fd,0,os.SEEK_SET);data=bytearray()
    while len(data)<=limit:
        part=os.read(fd,min(65536,limit+1-len(data)))
        if not part:break
        data.extend(part)
    after=os.fstat(fd)
    identity=lambda x:(x.st_dev,x.st_ino,x.st_mode,x.st_uid,x.st_gid,x.st_nlink,x.st_size,x.st_mtime_ns,x.st_ctime_ns)
    if len(data)>limit or len(data)!=before.st_size or identity(before)!=identity(after):fail('file changed')
    return bytes(data)


def root_immutable(path,expected):
    if not hex64(expected) or type(path) is not str or not path.startswith('/') or '//' in path:fail('external immutable binding required')
    parts=path.split('/')[1:]
    if not parts or any(x in ('','.','..') for x in parts):fail('path components')
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    try:
        for index,part in enumerate(parts):
            parent=os.fstat(fd)
            if parent.st_uid!=0 or not stat.S_ISDIR(parent.st_mode) or stat.S_IMODE(parent.st_mode)&0o022:fail('root-controlled ancestry')
            flags=os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC
            if index<len(parts)-1:flags|=os.O_DIRECTORY
            nextfd=os.open(part,flags,dir_fd=fd);os.close(fd);fd=nextfd
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)&0o022:fail('external Root file ownership')
        b=bytearray(4);fcntl.ioctl(fd,IOC_GETFLAGS,b,True)
        if not struct.unpack('I',b)[0]&IMMUTABLE:fail('external Root file must be immutable')
        data=read_stable(fd)
        if sha(data)!=expected:fail('external Root file digest')
        return data
    finally:os.close(fd)


def source(path,expected):
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:raw=read_stable(fd)
    finally:os.close(fd)
    if sha(raw)!=expected:fail('source binding')
    return raw


def proc(pid):
    if type(pid) is not int or pid<=1:fail('process id')
    data=Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
    if len(data)<20 or data[0] in ('Z','X','x'):fail('process unavailable')
    return {'pid':pid,'ppid':int(data[1]),'birth':data[19]}


def load_prelim():
    path=BASE/'postjoin-daemon-metadata-observer-source-1'/'root_parent_preliminary.py'
    raw=source(path,PRELIM_SHA);module=types.ModuleType('_install_prelim');module.__file__=str(path)
    exec(compile(raw,str(path),'exec'),module.__dict__)
    return module


def live_controls():
    reader=load_prelim();c,cr=reader.read_bound(reader.CONTROLS,1<<20);p,pr=reader.read_bound(reader.CAPACITY,1<<20)
    control=reader.strict_json(c);capacity=reader.strict_json(p)
    caps=reader.controller_checks(control,capacity,time.time())
    outer=proc(OUTER_PID)
    if outer['birth']!=OUTER_BIRTH or os.stat('/proc/%d'%OUTER_PID).st_uid!=1000:fail('actual Root server identity changed')
    return {'controls_sha256':sha(c),'capacity_sha256':sha(p),'caps':caps,'outer':outer,
            'control_identity':cr,'capacity_identity':pr}


def exact_request(req):
    keys={'nonce','outer_pid','outer_birth','one_shot_admission_id','operation_parent','code_parent_parent',
      'deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns',
      'weekly_used_percent','weekly_observed_utc_ns','service_status','host_floor_bytes','scratch_path',
      'scratch_floor_bytes','min_mem_available_bytes','join_capture_reserve_ns','term_grace_ns','kill_grace_ns',
      'join_grace_ns','retire_operation_only','owner_release','owner_release_sha256','profile_sha256',
      'native12','scratch21','mutex27_4','v2_birth','retained_2gib_bytes','native_currentfree','no_unlisted_later_operation'}
    if type(req) is not dict or set(req)!=keys:fail('strict phase-zero request shape')
    if not hex64(req['nonce']) or not hex64(req['one_shot_admission_id']) or req['outer_pid']!=OUTER_PID or req['outer_birth']!=OUTER_BIRTH:fail('actual nonce or outer binding')
    if req['operation_parent']!='/var/lib' or req['code_parent_parent']!='/var/lib':fail('reviewed private/public parent choice')
    if req['scratch_path']!='/home/holden/mckernel-work/scratch':fail('scratch identity path')
    if req['native12']!='HELD' or req['scratch21']!='HELD' or req['mutex27_4']!='HELD' or req['v2_birth'] is not None or req['native_currentfree'] is not None or req['no_unlisted_later_operation']!='UNKNOWN' or req['retained_2gib_bytes']!=2147483648:fail('native and unknown holds')
    if type(req['retire_operation_only']) is not bool or req['profile_sha256']!=PROFILE_SHA:fail('profile/retirement binding')
    for key in ('deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns','host_floor_bytes','scratch_floor_bytes','min_mem_available_bytes','join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(req[key]) is not int or req[key]<=0:fail('positive actual bound '+key)
    if req['host_floor_bytes']<16*1024**3 or req['scratch_floor_bytes']<12*1024**3 or req['min_mem_available_bytes']<24*1024**3:fail('resource floor')
    if not 1000000000<=req['join_capture_reserve_ns']<=30000000000:fail('capture reserve')
    if (type(req['weekly_used_percent']) not in (int,float) or not math.isfinite(req['weekly_used_percent']) or not 0<=req['weekly_used_percent']<100 or
        type(req['weekly_observed_utc_ns']) is not int or not 0<=time.time_ns()-req['weekly_observed_utc_ns']<=30000000000 or req['service_status']!='NO_NEW_REJECTION'):
        fail('fresh included-only actual usage required')
    if not time.clock_gettime_ns(time.CLOCK_BOOTTIME)<req['phase1_deadline_boot_ns']<=req['receipt_expires_boot_ns']<=req['deadline_boot_ns'] or time.monotonic_ns()>=req['deadline_mono_ns'] or not time.time_ns()<req['utc_cap_ns']<=UTC_CAP_NS:fail('time caps')
    owner=req['owner_release']
    if type(owner) is not dict or sha(canonical(owner))!=req['owner_release_sha256']:fail('Root owner bytes binding')
    return req


def bind_actual(proposal,actual,review_raw,live):
    """Derive the phase-zero DATA request from Root proposal and fresh values.

    The actual record and review file remain DATA here. Execution authority is
    separately bound to the actual root-watchdog channel in exec_prepared.
    """
    if (type(proposal) is not dict or proposal.get('status')!='ROOT_PROPOSED_ONE_INSTALL_ONLY_PENDING_INDEPENDENT_OPERATION_REVIEW' or
        proposal.get('thread_id')!='01a18bc3-e072-7810-9426-75101b0856c0' or proposal.get('manual_invocation')!=INVOCATION or
        proposal.get('actual_operation_started') is not False or proposal.get('execution_release') is not None):fail('Root proposal identity')
    keys={'version','status','proposal_sha256','operation_review_sha256','operation_review_status','observed_boot_ns','expires_boot_ns',
      'weekly_used_percent','weekly_observed_utc_ns','service_status','deadline_boot_ns','deadline_mono_ns','utc_cap_ns',
      'phase1_deadline_boot_ns','receipt_expires_boot_ns','join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns',
      'retire_operation_only','owner_release','owner_release_sha256','other_committed_bytes','external_watchdog'}
    if type(actual) is not dict or set(actual)!=keys or type(actual['version']) is not int or actual['version']!=1 or actual['status']!='ROOT_ONE_SHOT_ACTUAL_VALUES':fail('fresh Root actual record shape')
    if actual['proposal_sha256']!=PROPOSAL_SHA or not hex64(actual['operation_review_sha256']) or sha(review_raw)!=actual['operation_review_sha256'] or actual['operation_review_status']!='PASS_ACTUAL_ONE_SHOT':fail('actual independent operation review binding')
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if type(actual['observed_boot_ns']) is not int or type(actual['expires_boot_ns']) is not int or not actual['observed_boot_ns']<=now<actual['expires_boot_ns']<=actual['phase1_deadline_boot_ns']:fail('actual record freshness')
    r=proposal['resources'];other=actual['other_committed_bytes']
    if (r['CPU']!=[6] or r['native_jobs_reserved']!=4 or r['operation_roles']!=3 or r['joint_operation_jobs']!=7 or
        r['operation_planning_bytes']!=4*1024**3 or r['retained_native_GiB']!=12 or r['retained_unknown_V2_GiB']!=2 or
        type(other) is not int or other<0 or 18*1024**3+other>TOTAL_BUDGET):fail('aggregate resource plan')
    if live['controls_sha256']!=proposal['actual_controls_sha256'] or live['capacity_sha256']!=proposal['actual_capacity_sha256']:fail('actual controls changed from reviewed proposal')
    for role,expected in proposal['actual_actor_bindings'].items():
        observed=proc(expected['pid'])
        if observed['ppid']!=expected['ppid'] or observed['birth']!=expected['start']:fail('reviewed actor changed '+role)
    if set(proposal['actual_actor_bindings'])!={'watcher','worker','server','guardian','monitor','capacity_supervisor'}:fail('six actor bindings')
    req={'nonce':proposal['nonce'],'outer_pid':OUTER_PID,'outer_birth':OUTER_BIRTH,
      'one_shot_admission_id':proposal['one_shot_admission_id'],'operation_parent':'/var/lib','code_parent_parent':'/var/lib',
      'scratch_path':'/home/holden/mckernel-work/scratch','host_floor_bytes':16*1024**3,'scratch_floor_bytes':12*1024**3,
      'min_mem_available_bytes':24*1024**3,'profile_sha256':PROFILE_SHA,'native12':'HELD','scratch21':'HELD',
      'mutex27_4':'HELD','v2_birth':None,'retained_2gib_bytes':2147483648,'native_currentfree':None,
      'no_unlisted_later_operation':'UNKNOWN'}
    for key in ('weekly_used_percent','weekly_observed_utc_ns','service_status','deadline_boot_ns','deadline_mono_ns','utc_cap_ns',
                'phase1_deadline_boot_ns','receipt_expires_boot_ns','join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns',
                'retire_operation_only','owner_release','owner_release_sha256'):req[key]=actual[key]
    req=exact_request(req);raw=canonical(req);request_sha=sha(raw)
    owner=req['owner_release']
    if (type(owner) is not dict or owner.get('controls_sha256')!=live['controls_sha256'] or owner.get('capacity_sha256')!=live['capacity_sha256'] or
        owner.get('nonce')!=req['nonce'] or owner.get('review_sha256')!=SOURCE_REVIEW_SHA or
        owner.get('one_shot_admission_id')!=req['one_shot_admission_id'] or owner.get('manual_invocation')!=INVOCATION):fail('actual Root owner/control binding')
    ns=lambda x:int(Decimal(str(x))*Decimal(1000000000));caps=live['caps']
    if (req['deadline_boot_ns']>ns(caps['boot_deadline']) or req['deadline_mono_ns']>ns(caps['monotonic_deadline']) or req['utc_cap_ns']>ns(caps['deadline']) or
        req['deadline_boot_ns']>now+180000000000):fail('inherited operation caps')
    return req,raw,request_sha


def profile_argv(request_sha):
    profile_raw=source(PHASE/'PROFILE.SOURCE-ONLY.json',PROFILE_SHA);profile=json.loads(profile_raw,object_pairs_hook=unique)
    entry=source(PHASE/'ENTRY-CODE.py',ENTRY_SHA);source(PHASE/'phase0.py',PHASE_SHA)
    source(BASE/'root-install-source-10'/'profile-argv-correction-2'/'INSTALL-PROFILE.SOURCE-ONLY.json',V10_PROFILE_SHA)
    source(BASE/'root-install-v10-focused-review-1'/'RESULT.md',SOURCE_REVIEW_SHA)
    argv=profile['argv']
    prefix=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/usr/bin/python3','-I','-B','-c']
    suffix=['<ROOT_REVIEWED_ADMISSION_SHA256>','<ROOT_SELECTED_REVIEW_PATH>','<ROOT_SELECTED_REVIEW_SHA256>']
    if type(argv) is not list or argv[:16]!=prefix or len(argv)!=20 or argv[16]!=entry.decode() or argv[17:]!=suffix:fail('exact phase-zero argv differs')
    return prefix+[entry.decode(),request_sha,str(BASE/'root-install-v10-focused-review-1'/'RESULT.md'),SOURCE_REVIEW_SHA]


def local_capacity(req,plan):
    host=os.statvfs(req['operation_parent']);scratch=os.statvfs(req['scratch_path'])
    if host.f_bavail*host.f_frsize<req['host_floor_bytes'] or scratch.f_bavail*scratch.f_frsize<req['scratch_floor_bytes']:fail('actual storage floor')
    lines=[x for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')]
    if len(lines)!=1 or int(lines[0].split()[1])*1024<req['min_mem_available_bytes']:fail('actual memory floor')
    parent=os.open('/var/lib',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st=os.fstat(parent)
        if st.st_uid!=0 or stat.S_IMODE(st.st_mode)&0o022 or not stat.S_IMODE(st.st_mode)&0o001:fail('Root operation/code parent')
        for name in ('mckernel-install-'+req['nonce'],'mckernel-code-'+req['nonce']):
            try:os.stat(name,dir_fd=parent,follow_symlinks=False)
            except FileNotFoundError:pass
            else:fail('fresh Root output already exists')
    finally:os.close(parent)


def write_exclusive(dir_fd,name,data):
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=dir_fd)
    try:
        offset=0
        while offset<len(data):
            count=os.write(fd,data[offset:])
            if count<=0:raise OSError('short artifact write')
            offset+=count
        os.fsync(fd)
    finally:os.close(fd)


def prepare(actual_path,actual_sha,review_path,review_sha,output_parent):
    # Root-selected actual bytes and external review are data, not standalone authority.
    actual_raw=source(Path(actual_path),actual_sha);review_raw=source(Path(review_path),review_sha)
    proposal_raw=source(PROPOSAL_PATH,PROPOSAL_SHA)
    proposal=json.loads(proposal_raw,object_pairs_hook=unique);actual=json.loads(actual_raw,object_pairs_hook=unique)
    if actual.get('operation_review_sha256')!=review_sha:fail('separate operation review hash')
    live=live_controls();req,raw,request_sha=bind_actual(proposal,actual,review_raw,live)
    local_capacity(req,proposal['resources']);argv=profile_argv(request_sha)
    parent=os.open(output_parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        st=os.fstat(parent)
        if st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:fail('private actual preparation parent')
        name='attempt-'+req['nonce'];os.mkdir(name,0o700,dir_fd=parent);os.fsync(parent)
        out=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent)
        try:
            bindings={'status':'PREPARED_ONLY_NO_EXECUTION','request_sha256':request_sha,'root_proposal_sha256':PROPOSAL_SHA,'actual_values_sha256':actual_sha,'operation_review_sha256':review_sha,
                'phase0_profile_sha256':PROFILE_SHA,'v10_corrected_profile_sha256':V10_PROFILE_SHA,'entry_sha256':ENTRY_SHA,'phase0_sha256':PHASE_SHA,
                'source_review_sha256':SOURCE_REVIEW_SHA,'controls_sha256':live['controls_sha256'],'capacity_sha256':live['capacity_sha256'],
                'outer':live['outer'],'nonce':req['nonce'],'external_watchdog':actual['external_watchdog']}
            write_exclusive(out,'request.json',raw);write_exclusive(out,'argv.json',canonical(argv));write_exclusive(out,'source-bindings.json',canonical(bindings))
            write_exclusive(out,'caller.json',canonical({'outer':live['outer'],'manual_invocation':INVOCATION,'nonce':req['nonce']}));os.fsync(out)
        finally:os.close(out)
        return os.path.join(output_parent,name),request_sha,argv,actual
    finally:os.close(parent)


def arm_with_existing_root_watchdog(sock,expected,request_sha,nonce,deadline_boot_ns):
    """Authenticate the independently admitted, already-existing root watchdog.

    The peer implements external_watchdog_adapter's operation-specific protocol;
    possession of a JSON file or callback is not an acknowledgement of custody.
    """
    keys={'pid','birth','exe_sha256'}
    if type(expected) is not dict or set(expected)!=keys or not hex64(expected['exe_sha256']):fail('actual external watchdog binding')
    if sock.family!=socket.AF_UNIX or sock.getsockopt(socket.SOL_SOCKET,socket.SO_TYPE)!=socket.SOCK_SEQPACKET:fail('watchdog channel type')
    pid,uid,gid=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
    if uid!=0 or pid!=expected['pid'] or proc(pid)['birth']!=expected['birth']:fail('watchdog peer identity')
    exe=os.open('/proc/%d/exe'%pid,os.O_RDONLY|os.O_CLOEXEC)
    try:
        if sha(read_stable(exe,128*1024*1024))!=expected['exe_sha256']:fail('watchdog executable')
    finally:os.close(exe)
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if now>=deadline_boot_ns:fail('watchdog deadline')
    sock.settimeout(min(5.0,(deadline_boot_ns-now)/1e9))
    request={'type':'ARM_INSTALL_OWNER_V1','nonce':nonce,'request_sha256':request_sha,'caller_pid':os.getpid(),'deadline_boot_ns':deadline_boot_ns}
    if sock.send(canonical(request))!=len(canonical(request)):fail('watchdog request short')
    response=json.loads(sock.recv(65536),object_pairs_hook=unique)
    if response!={'type':'INSTALL_OWNER_ARMED_V1','nonce':nonce,'request_sha256':request_sha,'caller_pid':os.getpid(),'watchdog_pid':pid,'watchdog_birth':expected['birth'],'deadline_boot_ns':deadline_boot_ns}:
        fail('watchdog did not affirm exact live custody')
    if proc(pid)['birth']!=expected['birth']:fail('watchdog identity changed')
    handoff={'type':'EXEC_HANDOFF_V1','nonce':nonce,'request_sha256':request_sha,'caller_pid':os.getpid()}
    data=canonical(handoff)
    if sock.send(data)!=len(data):fail('exec handoff short')
    acknowledgement=json.loads(sock.recv(65536),object_pairs_hook=unique)
    if acknowledgement!={'type':'EXEC_HANDOFF_ACK_V1','nonce':nonce,'request_sha256':request_sha,'caller_pid':os.getpid()}:
        fail('watchdog did not durably own handoff')


def exec_prepared(directory,request_sha,argv,approval,sock,actual_path,actual_sha,review_path,review_sha):
    # The authenticated root watchdog must already own/pin this process and
    # preserve its evidence/UNKNOWN on an exec failure or uncertain terminal.
    reqfd=os.open(os.path.join(directory,'request.json'),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        if sha(read_stable(reqfd))!=request_sha:fail('stdin bytes changed')
        req=exact_request(json.loads(read_stable(reqfd),object_pairs_hook=unique));live=live_controls()
        actual=json.loads(source(Path(actual_path),actual_sha),object_pairs_hook=unique)
        proposal=json.loads(source(PROPOSAL_PATH,PROPOSAL_SHA),object_pairs_hook=unique)
        refreshed,raw,refreshed_sha=bind_actual(proposal,actual,source(Path(review_path),review_sha),live)
        if refreshed_sha!=request_sha or refreshed!=req or actual!=approval:fail('fresh actual binding changed before exec')
        local_capacity(req,proposal['resources'])
        if req['owner_release']['controls_sha256']!=live['controls_sha256'] or req['owner_release']['capacity_sha256']!=live['capacity_sha256']:fail('controls changed before exec')
        if profile_argv(request_sha)!=argv:fail('argv changed before exec')
        arm_with_existing_root_watchdog(sock,approval['external_watchdog'],request_sha,req['nonce'],req['deadline_boot_ns'])
        os.lseek(reqfd,0,os.SEEK_SET);os.dup2(reqfd,0)
        os.execve(argv[0],argv,os.environ.copy())  # inherited SUDO_ASKPASS; never read or log it
    finally:os.close(reqfd)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--actual',required=True);parser.add_argument('--actual-sha256',required=True)
    parser.add_argument('--operation-review',required=True);parser.add_argument('--operation-review-sha256',required=True);parser.add_argument('--output-parent',required=True)
    parser.add_argument('--execute',action='store_true');parser.add_argument('--watchdog-fd',type=int)
    args=parser.parse_args()
    path,request_sha,argv,approval=prepare(args.actual,args.actual_sha256,args.operation_review,args.operation_review_sha256,args.output_parent)
    if args.execute:
        # The supplied source adapter has no independently established root
        # owner or reviewed keeper stop capability. Leave its launch path closed.
        fail('external root owner and keeper stop capability not established')
        if args.watchdog_fd is None:fail('authenticated existing root watchdog channel required')
        sock=socket.socket(fileno=os.dup(args.watchdog_fd))
        exec_prepared(path,request_sha,argv,approval,sock,args.actual,args.actual_sha256,args.operation_review,args.operation_review_sha256)
    print(path)


if __name__=='__main__':main()
