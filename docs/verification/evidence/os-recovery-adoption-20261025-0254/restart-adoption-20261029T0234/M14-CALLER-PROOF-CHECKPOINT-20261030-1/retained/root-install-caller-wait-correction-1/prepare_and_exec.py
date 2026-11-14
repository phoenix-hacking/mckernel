"""M14 install-only Root caller preparation. No effects on import.

Invoke only from the actual Root session after independent operation review.
A local JSON file by itself is not authority: Root's direct parent process and
its reservation/join/capture obligations are part of the trust bootstrap.
"""
import argparse,hashlib,json,math,os,resource,secrets,select,signal,stat,sys,time,types
from decimal import Decimal
from pathlib import Path

BASE=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1')
HERE=BASE/'root-install-parent3-admission-preparation-1'
PARENT=BASE/'root-install-parent-successor-4'
CHILD=BASE/'root-install-direct-child-successor-4'
PREP=BASE/'root-install-actual-preparation-1'/'prepare_install.py'
PREP_SHA='19268f85a02d929b479ddd08207a25a7676f89ef0d5fb6701eb9ae577bf7f194'
PARENT_SHA='d02ec0a8e0a6550afdb31d655068a07f213f387f42ad97d2a920ccfc39edcfdf'
PROFILE_SHA='af535cf3031e0aa7f955f72c0ffde7813eccd44b042bee1346f1b97970405eb9'
BOOT_SHA='7e2e05b2c19881ae4348b273e5eae7d734f199c93263219a2d0b49e2c763180c'
CHILD_SHA='7ac4718a01be185cc1d816bf5c91e84960b73ca51209d7c3b909cda354ccfcea'
CHILD_MANIFEST_SHA='5cc545b852a95ff9504baac5a97a6936c0647127691908fd88ac52934ea256b8'
CLOSURE_SHA='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'
IPC_SHA='eda1ff0139c3bbf0c713009fc7728eccf3418cc7ce5d028731bc443837d49bbe'
MODEL_SHA='98ea72583a41f747f01c5bdb04b545319fc08cedf443366a6c2637a35562ed04'
OLD_NONCE='b692f980fa10bda5271b39112fd8d454f33b622106e79eb9a4791c0c50abfde1'
OUTER=2996005;OUTER_BIRTH='118034116';INVOCATION='20261030T175456Z-0e492844'
OWNED=[]
STOP_SIGNALS=(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM)
MAX=2*1024*1024;BUDGET=int(Decimal('22.5447')*Decimal(1024**3));UTC_CAP=1793774133*10**9


def fail(message):raise ValueError(message)
def digest(raw):return hashlib.sha256(raw).hexdigest()
def canon(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def h64(x):return type(x) is str and len(x)==64 and all(c in '0123456789abcdef' for c in x)

def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result:fail('duplicate key')
        result[k]=v
    return result


def read(path,expected=None,limit=MAX):
    record=owned_open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);fd=record['fd']
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:fail('bounded file')
        parts=[];count=0
        while count<=limit:
            part=os.read(fd,min(65536,limit+1-count))
            if not part:break
            parts.append(part);count+=len(part)
        after=os.fstat(fd);raw=b''.join(parts)
        if count!=before.st_size or count>limit or (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):fail('file changed')
        if expected is not None and digest(raw)!=expected:fail('hash mismatch '+str(path))
        return raw
    finally:owned_close(record)


def base_check():
    # Actual direct Root session is the caller; the review JSON alone grants no authority.
    if os.getuid()!=1000 or os.geteuid()!=1000 or os.getppid()!=OUTER:fail('direct Root session caller required')
    raw=read(PREP,PREP_SHA);module=types.ModuleType('_existing_actual_controls');module.__file__=str(PREP)
    exec(compile(raw,str(PREP),'exec'),module.__dict__)
    if module.proc(OUTER)['birth']!=OUTER_BIRTH:fail('Root session birth changed')
    live=module.live_controls()
    proposal_raw=read(HERE/'RESOURCE-PROPOSAL-R2.json');proposal=json.loads(proposal_raw,object_pairs_hook=unique)
    if proposal.get('status')!='ROOT_RESOURCE_PROPOSAL_R2_NOT_ADMITTED':fail('proposal shape')
    for row in proposal['source_bindings'].values():read(row['path'],row['sha256'])
    read(proposal['fd_plan']['path'],proposal['fd_plan']['sha256'])
    read(PARENT/'FROZEN-SOURCE.json',PARENT_SHA);profile=json.loads(read(PARENT/'PROFILE.SOURCE-ONLY.json',PROFILE_SHA),object_pairs_hook=unique)
    boot=read(PARENT/'BOOTSTRAP.py',BOOT_SHA).decode();read(CHILD/'direct_entry.py',CHILD_SHA)
    child=json.loads(read(CHILD/'SOURCE-BOUND.json',CHILD_MANIFEST_SHA),object_pairs_hook=unique)
    prefix=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=60:60','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/usr/bin/python3','-I','-B','-c']
    argv=profile['argv'];suffix=['<FRESH_ADMISSION_SHA256>','<REVIEWED_SOURCE_REVIEW_PATH>','<REVIEWED_SOURCE_REVIEW_SHA256>','<STDOUT_CAPTURE_DEVICE>','<STDOUT_CAPTURE_INODE>']
    if len(argv)!=22 or argv[:16]!=prefix or argv[16]!=boot or argv[17:]!=suffix:fail('exact argv binding')
    return module,live,proposal,proposal_raw,child,prefix,boot


def fresh_values(actual,live):
    keys={'version','weekly_used_percent','weekly_observed_utc_ns','usage_evidence_sha256','service_status','sampled_boot_ns',
          'additional_reserved_bytes','sudo_overhead_reserved_bytes','sudo_overhead_observed_bytes',
          'deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns',
          'join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns','retire_operation_only',
          'controls_sha256','capacity_sha256','interpreter_sha256'}
    if type(actual) is not dict or set(actual)!=keys or type(actual['version']) is not int or actual['version']!=1:fail('actual values shape')
    now_boot=time.clock_gettime_ns(time.CLOCK_BOOTTIME);now_utc=time.time_ns();now_mono=time.monotonic_ns()
    percent=actual['weekly_used_percent']
    if (type(percent) not in (int,float) or not math.isfinite(percent) or not 0<=percent<100 or
        type(actual['weekly_observed_utc_ns']) is not int or not 0<=now_utc-actual['weekly_observed_utc_ns']<=30000000000 or
        not h64(actual['usage_evidence_sha256']) or actual['service_status']!='NO_NEW_REJECTION' or
        type(actual['sampled_boot_ns']) is not int or not 0<=now_boot-actual['sampled_boot_ns']<=30000000000):fail('fresh included usage and control status')
    extra=actual['additional_reserved_bytes'];reserve=actual['sudo_overhead_reserved_bytes'];observed=actual['sudo_overhead_observed_bytes']
    if any(type(x) is not int or x<0 for x in (extra,reserve,observed)) or not 512*1024**2<=reserve<=1024**3 or observed>reserve-512*1024**2 or 18*1024**3+extra>BUDGET:fail('aggregate or host-control reservation')
    if actual['controls_sha256']!=live['controls_sha256'] or actual['capacity_sha256']!=live['capacity_sha256']:fail('actual controls changed')
    if not h64(actual['interpreter_sha256']) or type(actual['retire_operation_only']) is not bool:fail('runtime or retirement')
    for k in ('deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns','join_capture_reserve_ns','term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(actual[k]) is not int or actual[k]<=0:fail('actual cap '+k)
    ns=lambda x:int(Decimal(str(x))*10**9);caps=live['caps']
    if not (now_boot+75000000000<actual['deadline_boot_ns']<=min(ns(caps['boot_deadline']),now_boot+180000000000) and
        now_mono+75000000000<actual['deadline_mono_ns']<=min(ns(caps['monotonic_deadline']),now_mono+180000000000) and
        now_utc+75000000000<actual['utc_cap_ns']<=min(ns(caps['deadline']),UTC_CAP,now_utc+180000000000) and
        now_boot<actual['phase1_deadline_boot_ns']<=actual['receipt_expires_boot_ns']<=actual['deadline_boot_ns'] and
        1000000000<=actual['join_capture_reserve_ns']<=30000000000):fail('tighter actual clock caps')
    return now_boot


def check_capacity():
    for path,floor in (('/var/lib',16*1024**3),('/home/holden/mckernel-work/scratch',12*1024**3)):
        fs=os.statvfs(path)
        if fs.f_bavail*fs.f_frsize<floor:fail('actual storage floor')
    rows=[line for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')]
    if len(rows)!=1 or int(rows[0].split()[1])*1024<24*1024**3:fail('actual memory floor')
    st=os.stat('/var/lib')
    if st.st_uid!=0 or not stat.S_ISDIR(st.st_mode) or stat.S_IMODE(st.st_mode)&0o022:fail('Root-controlled parent')


def build_request(actual,live,child,review_sha,nonce,admission_id):
    pins=child['source_sha256'];model={'version':1,'record_type':'ROOT_INSTALL_DIRECT_MODEL_APPROVAL_V1','scope':'ROOT_CODE_INSTALL_ONLY',
      'nonce':nonce,'native_release':False,'native_currentfree':None,'global_descendants':'UNKNOWN','status':'APPROVED_KNOWN_ROLE_MODEL',
      'model_sha256':MODEL_SHA,'issuer_sha256':pins['install_issuer.py'],'completion_sha256':pins['install_completion.py'],
      'installer_sha256':pins['install_source_closure.py'],'wait_sha256':pins['WAIT-INSTALL-CODE.py'],'ipc_sha256':IPC_SHA,
      'runtime_sha256':actual['interpreter_sha256'],'source_closure_sha256':CLOSURE_SHA,'review_sha256':review_sha,'trusted_platform':'DIRECT_CPYTHON_LIBC_KERNEL'}
    owner={'version':1,'record_type':'ROOT_INSTALL_OPERATION_RETIREMENT_V1','scope':'ROOT_CODE_INSTALL_ONLY','nonce':nonce,
      'native_release':False,'status':'APPROVED_IF_VERIFIED','review_sha256':review_sha,'creation_model_approval':model,
      'manual_invocation':INVOCATION,'one_shot_admission_id':admission_id,'profile_sha256':PROFILE_SHA,
      'controls_sha256':live['controls_sha256'],'capacity_sha256':live['capacity_sha256'],'outer_pid':OUTER,'outer_birth':OUTER_BIRTH,
      'retire_operation_only':actual['retire_operation_only']}
    request={'nonce':nonce,'outer_pid':OUTER,'outer_birth':OUTER_BIRTH,'one_shot_admission_id':admission_id,
      'operation_parent':'/var/lib','code_parent_parent':'/var/lib','scratch_path':'/home/holden/mckernel-work/scratch',
      'host_floor_bytes':16*1024**3,'scratch_floor_bytes':12*1024**3,'min_mem_available_bytes':24*1024**3,
      'owner_release':owner,'owner_release_sha256':digest(canon(owner)),'profile_sha256':PROFILE_SHA,
      'native12':'HELD','scratch21':'HELD','mutex27_4':'HELD','v2_birth':None,'retained_2gib_bytes':2*1024**3,
      'native_currentfree':None,'no_unlisted_later_operation':'UNKNOWN'}
    for k in ('deadline_boot_ns','deadline_mono_ns','utc_cap_ns','phase1_deadline_boot_ns','receipt_expires_boot_ns',
              'weekly_used_percent','weekly_observed_utc_ns','service_status','join_capture_reserve_ns','term_grace_ns',
              'kill_grace_ns','join_grace_ns','retire_operation_only'):request[k]=actual[k]
    return request


def owned_open(path,flags,mode=0o777,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
    try:
        record={'state':'PENDING_OPEN','fd':None,'historical_fd':None};OWNED.append(record)
        try:fd=os.open(path,flags,mode,dir_fd=dir_fd)
        except BaseException:
            record['state']='OPEN_UNKNOWN';raise
        record['fd']=fd;record['state']='OWNED';return record
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def owned_close(record):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
    try:
        if not any(item is record for item in OWNED) or record.get('state')!='OWNED' or type(record.get('fd')) is not int:fail('FD not owned')
        fd=record['fd'];record['fd']=None;record['historical_fd']=fd;record['state']='CLOSING'
        try:os.close(fd)
        except BaseException:
            record['state']='CLOSURE_UNKNOWN';raise
        record['state']='VERIFIED_CLOSED'
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def write_new(d,name,raw):
    record=owned_open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=d);fd=record['fd']
    try:
        off=0
        while off<len(raw):
            n=os.write(fd,raw[off:])
            if n<=0:raise OSError('short durable write')
            off+=n
        os.fsync(fd)
    finally:owned_close(record)


def load_fork_owners():
    raw=read(CHILD/'direct_entry.py',CHILD_SHA)
    if 'direct_entry' in sys.modules:fail('unexpected loaded direct entry')
    entry=types.ModuleType('direct_entry');entry.__file__=str(CHILD/'direct_entry.py');sys.modules['direct_entry']=entry
    exec(compile(raw,entry.__file__,'exec'),entry.__dict__);entry.load_for_parent()
    path=BASE/'root-install-parent-successor-2'/'root_parent.py'
    raw=read(path,'7d97d9f905f50e0cb4308411a1786d37361356afd2e104b2b1fc063cd854f74d')
    parent=types.ModuleType('_bound_parent_recovery');parent.__file__=str(path)
    exec(compile(raw,str(path),'exec'),parent.__dict__)
    return entry,parent,sys.modules['deferred_fork'],sys.modules['ownership_latch']


def proc_snapshot(pid):
    path=Path('/proc/%d'%pid)
    def statrow():
        with (path/'stat').open('r') as stream:text=stream.read(8193)
        if len(text)>8192:raise ValueError('process stat bound')
        f=text.rsplit(')',1)[1].split()
        if len(f)<20 or f[0] in ('Z','X','x'):raise ValueError('process terminal or stat short')
        return {'pid':pid,'ppid':int(f[1]),'pgrp':int(f[2]),'birth':f[19]}
    before=statrow();uid=os.stat(str(path)).st_uid
    with (path/'status').open('r') as stream:status_text=stream.read(65537)
    if len(status_text)>65536:raise ValueError('process status bound')
    rss=[line for line in status_text.splitlines() if line.startswith('VmRSS:')]
    if len(rss)!=1:raise ValueError('process RSS unavailable')
    rss_bytes=int(rss[0].split()[1])*1024
    with (path/'cmdline').open('rb') as stream:raw=stream.read(262145)
    if len(raw)>262144:raise ValueError('process argv bound')
    after=statrow()
    if before!=after:raise ValueError('process identity changed')
    before.update(uid=uid,rss_bytes=rss_bytes,cmdline_sha256=digest(raw));return before,raw


def owned_tree(root_pid,expected_birth):
    # /proc task children walk begins only at the exact owned sudo child.
    result={};todo=[root_pid]
    while todo:
        if len(result)>=16:raise ValueError('owned subtree process bound')
        pid=todo.pop(0)
        if pid in result:raise ValueError('duplicate subtree process')
        row,raw=proc_snapshot(pid);result[pid]=(row,raw)
        if pid==root_pid and row['birth']!=expected_birth:raise ValueError('owned sudo birth drift')
        with Path('/proc/%d/task/%d/children'%(pid,pid)).open('r') as stream:text=stream.read(4097)
        if len(text)>4096:raise ValueError('subtree children bound')
        children=[int(x) for x in text.split()]
        for child in children:
            if child<=1:raise ValueError('invalid subtree child')
            todo.append(child)
    for pid,(row,_) in result.items():
        if pid!=root_pid and row['ppid'] not in result:raise ValueError('subtree ancestry changed')
    return result


def identify_roles(tree,sudo_pid,bootstrap,wait_literal):
    # Exact pinned argv bytes distinguish the root Python bootstrap from sudo.
    needle=b'\0-c\0'+bootstrap.encode()+b'\0';wait=b'\0-c\0'+wait_literal.encode()+b'\0'
    python={pid:row for pid,(row,raw) in tree.items() if row['uid']==0 and needle in raw}
    roots=[row for pid,row in python.items() if row['ppid'] not in python]
    if len(roots)>1:raise ValueError('ambiguous root parent')
    result={}
    if not roots:return result
    root=roots[0];result['root_parent']=root
    keepers=[row for row in python.values() if row['ppid']==root['pid']]
    if len(keepers)>1:raise ValueError('ambiguous keeper')
    if not keepers:return result
    keeper=keepers[0];result['keeper']=keeper
    installers=[row for pid,(row,raw) in tree.items() if row['uid']==0 and row['ppid']==keeper['pid'] and wait in raw]
    if len(installers)>1:raise ValueError('ambiguous installer')
    if installers:
        if installers[0]['pgrp']!=installers[0]['pid']:raise ValueError('installer process group')
        result['installer']=installers[0]
    return result


def capture_close_and_hash(record,run,name):
    # Global owned record is consumed before its single close.
    if record.get('state')!='OWNED' or type(record.get('fd')) is not int:fail('capture not owned')
    fd=record['fd'];os.fsync(fd);identity=os.fstat(fd)
    if not stat.S_ISREG(identity.st_mode) or identity.st_uid!=1000 or identity.st_nlink!=1 or stat.S_IMODE(identity.st_mode)!=0o600:fail('capture ownership or type')
    state={'name':name,'state':'CLOSING','historical_fd':fd,'device':identity.st_dev,'inode':identity.st_ino}
    try:owned_close(record)
    except BaseException:
        state['state']=record['state'];raise
    state['state']='VERIFIED_CLOSED'
    reader=owned_open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=run);readfd=reader['fd']
    try:
        st=os.fstat(readfd)
        if (st.st_dev,st.st_ino)!=(identity.st_dev,identity.st_ino):raise ValueError('capture inode changed')
        chunks=[];total=0
        while total<=32*1024*1024:
            data=os.read(readfd,min(65536,32*1024*1024+1-total))
            if not data:break
            chunks.append(data);total+=len(data)
        after=os.fstat(readfd)
        if total>32*1024*1024 or total!=st.st_size or (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns):raise ValueError('capture bound or stability')
        raw=b''.join(chunks);state.update(length=total,sha256=digest(raw))
        return state,raw
    finally:owned_close(reader)


def parse_captured_data(raw,request,observed,wait_status,capture):
    lines=raw.splitlines(keepends=True)
    if len(lines)!=2 or any(not line.endswith(b'\n') for line in lines):fail('full and disposition JSONL required')
    full=json.loads(lines[0],object_pairs_hook=unique);final=json.loads(lines[1],object_pairs_hook=unique)
    if canon(full)!=lines[0] or canon(final)!=lines[1]:fail('noncanonical captured DATA')
    nonce=request['nonce'];profile=request['profile_sha256']
    common={'scope':'ROOT_CODE_INSTALL_ONLY','nonce':nonce,'profile_sha256':profile,'native_release':False,'native_currentfree':None}
    for obj in (full,final):
        if type(obj) is not dict or any(canon(obj.get(k))!=canon(v) for k,v in common.items()):fail('captured scope binding')
    if set(full)!={'record_type','scope','nonce','profile_sha256','root_parent','native_release','native_currentfree','result'} or full['record_type']!='ROOT_INSTALL_FULL_DATA_V1':fail('FULL schema')
    if set(final)!={'record_type','scope','nonce','profile_sha256','root_parent','full_sha256','lease_disposition','outcome','native_release','native_currentfree'} or final['record_type']!='ROOT_INSTALL_DISPOSITION_DATA_V1':fail('disposition schema')
    if final['full_sha256']!=digest(lines[0]) or canon(final['root_parent'])!=canon(full['root_parent']):fail('FULL digest/producer binding')
    if final['lease_disposition']!='VERIFIED_CLOSED' or final['outcome']!='COMPLETE':fail('operation closure not positively complete')
    if type(wait_status) is not int or not os.WIFEXITED(wait_status) or os.WEXITSTATUS(wait_status)!=0:fail('sudo direct wait not zero')
    data=full['result'];root=full['root_parent']
    if (type(data) is not dict or data.get('status')!='INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ' or data.get('authority') is not None or data.get('lease_disposition')!='HELD' or data.get('root_parent')!=root or data.get('nonce')!=nonce or data.get('native_release') is not False or data.get('native_currentfree') is not None or
        canon(data.get('stdout_capture'))!=canon({'device':capture['device'],'inode':capture['inode']})):fail('full result/caller capture binding')
    terminals=data.get('terminal_evidence');proof=data.get('proof')
    if type(terminals) is not dict or set(terminals)!={'keeper','installer'} or type(proof) is not dict:fail('terminal/proof shape')
    keeper=terminals['keeper'];installer=terminals['installer']
    if (type(keeper) is not dict or set(keeper)!={'pid','birth','direct_wait_status'} or type(keeper['direct_wait_status']) is not int or keeper['direct_wait_status']!=0 or
        type(installer) is not dict or set(installer)!={'pid','birth','pidfd_terminal','keeper_direct_wait_status'} or installer['pidfd_terminal'] is not True or type(installer['keeper_direct_wait_status']) is not int or installer['keeper_direct_wait_status']!=0):fail('terminal wait evidence')
    if proof.get('source_closure_sha256')!=CLOSURE_SHA or proof.get('native_release') is not False or proof.get('native_currentfree') is not None or proof.get('global_descendants')!='UNKNOWN':fail('proof scope')
    files=proof.get('install_proof',{}).get('files')
    closure=json.loads(read(BASE/'root-install-source-10'/'SOURCE-CLOSURE.json',CLOSURE_SHA),object_pairs_hook=unique)
    if type(files) is not list or len(files)!=23:fail('full 23-file proof absent')
    expected={(r['name'],r['sha256']) for r in closure['files']}
    if {(r.get('name'),r.get('sha256')) for r in files if type(r) is dict}!=expected:fail('proof membership/hashes')
    for role,producer in (('root_parent',root),('keeper',keeper),('installer',installer)):
        seen=observed.get(role)
        if type(producer) is not dict or type(seen) is not dict or type(producer.get('pid')) is not int or type(producer.get('birth')) is not str or seen.get('pid')!=producer['pid'] or seen.get('birth')!=producer['birth']:
            fail('missing or mismatched independent role observation: '+role)
    return {'full_sha256':digest(lines[0]),'producer_root_parent':root,'producer_terminals':terminals,'lease_disposition':'VERIFIED_CLOSED','outcome':'COMPLETE'}


def caller_rss():
    with Path('/proc/self/status').open('r') as stream:text=stream.read(65537)
    if len(text)>65536:raise ValueError('caller status bound')
    rows=[line for line in text.splitlines() if line.startswith('VmRSS:')]
    if len(rows)!=1:raise ValueError('caller RSS unknown')
    return int(rows[0].split()[1])*1024


def supervise(run,latch,child,child_pid,child_fd,child_birth,out,err,bootstrap,wait_literal,request,actual):
    observed={};attempted=set();errors=[];status=None;timed_out=False;resource_unknown=False;rss_peak=caller_rss();host_peak=0
    poll=select.poll();poll.register(child_fd,select.POLLIN|select.POLLHUP|select.POLLERR)
    while True:
        if (time.clock_gettime_ns(time.CLOCK_BOOTTIME)>=request['deadline_boot_ns'] or
            time.monotonic_ns()>=request['deadline_mono_ns'] or time.time_ns()>=request['utc_cap_ns']):timed_out=True
        try:
            rss_peak=max(rss_peak,caller_rss())
            if rss_peak>512*1024**2:errors.append('CALLER_RSS_RESERVE_EXCEEDED');resource_unknown=True
        except (OSError,ValueError):errors.append('CALLER_RSS_UNKNOWN');resource_unknown=True
        if len(errors)>64:errors=errors[-64:]
        if len(observed)<3 and not timed_out:
            try:
                tree=owned_tree(child_pid,child_birth);roles=identify_roles(tree,child_pid,bootstrap,wait_literal)
                root_roles={row['pid'] for row in roles.values()}
                host_bytes=caller_rss()+actual['sudo_overhead_observed_bytes']+sum(row['rss_bytes'] for pid,(row,_) in tree.items() if pid not in root_roles)
                host_peak=max(host_peak,host_bytes)
                if host_bytes>actual['sudo_overhead_reserved_bytes']:
                    errors.append('HOST_CONTROL_RESERVE_EXCEEDED');resource_unknown=True
                for role,row in roles.items():
                    if role in observed:
                        prior=observed[role]
                        if any(prior[k]!=row[k] for k in ('pid','birth','ppid','pgrp')):raise ValueError('role identity changed')
                        continue
                    if role in attempted:continue
                    attempted.add(role)
                    try:
                        write_new(run,'OBSERVED-'+role+'.json',canon({'status':'POINT_OBSERVATION_ONLY','role':role,'identity':row,'nonce_authority':None}))
                        os.fsync(run)
                    except BaseException as error:
                        errors.append('OBSERVATION_PUBLICATION_'+type(error).__name__)
                        continue
                    observed[role]=row
            except (FileNotFoundError,ProcessLookupError) as error:
                errors.append('TRANSIENT_SUBTREE_'+type(error).__name__)
                if len(errors)>64:errors=errors[-64:]
            except (OSError,ValueError) as error:
                errors.append(type(error).__name__);resource_unknown=True
                if len(errors)>64:errors=errors[-64:]
        events=poll.poll(1000 if timed_out else 100)
        if events:
            mask=events[0][1]
            if mask&(select.POLLERR|select.POLLNVAL):
                latch.fail('sudo pidfd polling unknown')
                try:write_new(run,'CALLER-WAIT-UNKNOWN.json',canon({'status':'PIDFD_POLL_UNKNOWN','native_release':False}));os.fsync(run)
                except BaseException:pass
                while True:time.sleep(1)
            if mask&(select.POLLIN|select.POLLHUP):
                try:waited_pid,status=os.waitpid(child_pid,os.WNOHANG)
                except BaseException as error:
                    latch.fail(error)
                    try:write_new(run,'CALLER-WAIT-UNKNOWN.json',canon({'status':'DIRECT_WAIT_UNKNOWN','native_release':False}));os.fsync(run)
                    except BaseException:pass
                    while True:time.sleep(1)
                if waited_pid==child_pid:break
                if waited_pid!=0:
                    latch.fail('unexpected direct wait target')
                    while True:time.sleep(1)
        # The caller lacks root signaling authority. Parent3 owns root stops.
        # Beyond the cap this process only retains custody and waits for a join.
    try:
        stdout,stdout_raw=capture_close_and_hash(out,run,'stdout.capture')
        stderr,_stderr_raw=capture_close_and_hash(err,run,'stderr.capture')
    except BaseException as error:
        latch.fail(error)
        try:write_new(run,'CAPTURE-UNKNOWN.json',canon({'status':'CAPTURE_CLOSURE_OR_READ_UNKNOWN','error_type':type(error).__name__,'native_release':False}));os.fsync(run)
        except BaseException:pass
        raise
    try:
        data=parse_captured_data(stdout_raw,request,observed,status,stdout);data_error=None
    except BaseException as error:
        data=None;data_error=type(error).__name__+': '+str(error)
    result={'status':'UNKNOWN_REQUIRES_ROOT_RECONCILIATION' if data is None or timed_out or resource_unknown or latch.failure is not None else 'FULL_DATA_CAPTURED_AWAIT_ROOT_SESSION_JOIN','sudo_pid':child_pid,'sudo_birth':child_birth,
      'sudo_direct_wait_status':status,'timed_out':timed_out,'resource_unknown':resource_unknown,'observed_roles':observed,'observation_errors':errors,
      'captures':[stdout,stderr],'caller_peak_rss_bytes':rss_peak,'host_control_observed_peak_bytes':host_peak,
      'host_control_observation_scope':'POINT_SAMPLES_UNTIL_ROLE_IDENTITIES_OBSERVED','verified_data':data,'data_error':data_error,
      'full_proof_source':'ROOT_PRODUCER_DATA_ONLY' if data is not None else 'UNKNOWN',
      'native_release':False,'native_currentfree':None,'reservation_release':False}
    write_new(run,'CALLER-TERMINAL.json',canon(result));os.fsync(run)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--actual-values',required=True);p.add_argument('--actual-values-sha256',required=True)
    p.add_argument('--operation-review',required=True);p.add_argument('--operation-review-sha256',required=True)
    p.add_argument('--reservation-parent',required=True);p.add_argument('--execute',action='store_true');args=p.parse_args()
    if not args.execute:fail('actual reviewed one-shot invocation requires --execute')
    if not h64(args.actual_values_sha256) or not h64(args.operation_review_sha256):fail('selected input hashes')
    module,live,proposal,proposal_raw,child,prefix,boot=base_check()
    actual=json.loads(read(args.actual_values,args.actual_values_sha256),object_pairs_hook=unique)
    review_raw=read(args.operation_review,args.operation_review_sha256);review=json.loads(review_raw,object_pairs_hook=unique)
    # This exact record must be separately issued by the independent reviewer;
    # direct caller is the existing Root process, not an arbitrary JSON reader.
    expected={'status':'PASS_ACTUAL_INSTALL_ONLY','scope':'ROOT_CODE_INSTALL_ONLY','proposal_sha256':digest(proposal_raw),
              'driver_sha256':digest(read(__file__)),'parent_manifest_sha256':PARENT_SHA,'child_manifest_sha256':CHILD_MANIFEST_SHA,
              'native_release':False,'native_currentfree':None,'retire_operation_only':actual['retire_operation_only']}
    if type(review) is not dict or canon(review)!=canon(expected):fail('exact independent operation review')
    fresh_values(actual,live);check_capacity()
    interpreter=Path('/usr/bin/python3').resolve(strict=True)
    if digest(read(interpreter,limit=128*1024*1024))!=actual['interpreter_sha256']:fail('actual system interpreter')
    if len(os.listdir('/proc/self/fd'))-1>16:fail('preoccupied FD limit exceeds modeled baseline')
    inherited=os.sched_getaffinity(0)
    if 6 not in inherited:fail('CPU6 not in existing affinity')
    os.sched_setaffinity(0,{6})
    if os.sched_getaffinity(0)!={6}:fail('CPU6 narrowing failed')
    nonce=secrets.token_hex(32);admission_id=secrets.token_hex(32)
    if nonce==OLD_NONCE or not h64(nonce) or not h64(admission_id):fail('fresh nonce')
    for name in ('mckernel-install-'+nonce,'mckernel-code-'+nonce):
        if os.path.lexists('/var/lib/'+name):fail('nonce output already exists')
    request=build_request(actual,live,child,args.operation_review_sha256,nonce,admission_id);raw=canon(request);request_sha=digest(raw)
    parent_record=owned_open(args.reservation_parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);parent=parent_record['fd']
    st=os.fstat(parent)
    if st.st_uid!=1000 or stat.S_IMODE(st.st_mode)!=0o700:fail('private Root-session reservation parent required')
    name='install-'+nonce;os.mkdir(name,0o700,dir_fd=parent);os.fsync(parent)
    run_record=owned_open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent);run=run_record['fd']
    # No cleanup: after this exclusive marker, any uncertain outcome is charged
    # and this nonce must never be replayed.
    self_row=module.proc(os.getpid())
    reservation={'status':'RESERVED_UNKNOWN_UNTIL_ROOT_JOIN','scope':'ROOT_CODE_INSTALL_ONLY','nonce':nonce,'admission_id':admission_id,
       'root_server':live['outer'],'driver':self_row,'request_sha256':request_sha,'operation_review_sha256':args.operation_review_sha256,
       'proposal_sha256':digest(proposal_raw),'actual_values_sha256':args.actual_values_sha256,'operation_reserved_bytes':4*1024**3,
       'additional_reserved_bytes':actual['additional_reserved_bytes'],'sudo_overhead_reserved_bytes':actual['sudo_overhead_reserved_bytes'],
       'future_sudo_and_root_pid_birth':'ROOT_SESSION_MUST_OBSERVE_AND_REGISTER','native_currentfree':None,'native_release':False,
       'no_unlisted_later_operation':'UNKNOWN','nonce_replay_forbidden':True}
    write_new(run,'RESERVATION.json',canon(reservation));write_new(run,'request.json',raw)
    out=owned_open('stdout.capture',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=run)
    err=owned_open('stderr.capture',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=run)
    os.fsync(out['fd']);os.fsync(err['fd'])
    capture_st=os.fstat(out['fd'])
    argv=prefix+[boot,request_sha,args.operation_review,args.operation_review_sha256,str(capture_st.st_dev),str(capture_st.st_ino)]
    write_new(run,'argv.json',canon(argv))
    write_new(run,'CAPTURE.json',canon({'stdout':{'device':os.fstat(out['fd']).st_dev,'inode':os.fstat(out['fd']).st_ino},
                                        'stderr':{'device':os.fstat(err['fd']).st_dev,'inode':os.fstat(err['fd']).st_ino},'nonce':nonce}))
    os.fsync(run);os.fsync(parent)
    # Exact fresh check after durable reservation, immediately before exec.
    fresh_values(actual,module.live_controls());check_capacity()
    if module.proc(OUTER)['birth']!=OUTER_BIRTH:fail('Root caller lost')
    write_new(run,'PREEXEC.json',canon({'nonce':nonce,'driver':self_row,'status':'EXEC_OUTCOME_UNKNOWN_UNTIL_JOIN'}));os.fsync(run)
    print(canon({'status':'PREEXEC_RESERVED','nonce':nonce,'reservation_dir':os.path.join(args.reservation_parent,name),'driver':self_row}).decode(),end='',flush=True)
    stdin=owned_open('request.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=run)
    if digest(os.read(stdin['fd'],len(raw)+1))!=request_sha:fail('stdin readback')
    os.lseek(stdin['fd'],0,os.SEEK_SET)
    # The unprivileged caller remains resident and owns exactly one sudo child.
    # All its CPU/RSS and sudo/frontend overhead are charged to Root's existing
    # host-control reserve. No extra privileged owner is introduced.
    entry,parent_recovery,deferred,latches=load_fork_owners()
    latch=latches.CustodyLatch('CALLER_OWNED');latch.retain(run,parent,stdin,out,err,entry)
    record=latch.reserve_child('keeper',run,stdin,out,err)
    self_row['pgrp']=os.getpgrp()
    if caller_rss()>512*1024**2:fail('caller RSS exceeds host-control share')
    fresh_values(actual,module.live_controls());check_capacity()
    write_new(run,'BEFORE-SUDO-FORK.json',canon({'nonce':nonce,'caller':self_row,'status':'OWNED_CHILD_PENDING'}));os.fsync(run)
    def child_exec():
        os.dup2(stdin['fd'],0);os.dup2(out['fd'],1);os.dup2(err['fd'],2)
        # sudo closes fd >=3 normally; the root process creates its own channel.
        os.execve(argv[0],argv,os.environ.copy())
    fresh_values(actual,module.live_controls())
    try:
        with deferred.DeferredFork() as guard:
            child_pid,child_fd,child_birth=guard.fork_and_pin(record,child_exec)
    except BaseException as error:
        latch.fail(error)
        child_pid,child_fd=parent_recovery.retained_keeper_target(latch,record,error,None,None)
        if child_pid is None or child_fd is None:
            # No verified direct child identity means no numeric wait or signal.
            # Retain UNKNOWN ownership until an external Root reconciliation.
            try:write_new(run,'CALLER-UNKNOWN.json',canon({'nonce':nonce,'status':'CHILD_IDENTITY_UNKNOWN','native_release':False}));os.fsync(run)
            except BaseException:pass
            while True:time.sleep(1)
        child_birth=record.failure_observation['birth']
    try:
        write_new(run,'SUDO-CHILD.json',canon({'nonce':nonce,'pid':child_pid,'birth':child_birth,'parent_pid':self_row['pid'],'status':'DIRECT_CHILD_HELD'}));os.fsync(run)
    except BaseException as error:
        # Do not abandon a verified child when publication fails.
        latch.fail(error)
    result=supervise(run,latch,record,child_pid,child_fd,child_birth,out,err,boot,entry.LOADED['wait_raw'].decode(),request,actual)
    print(canon(result).decode(),end='',flush=True)


if __name__=='__main__':main()
