"""Functional M14 source-install terminal verification; no security testing."""
import hashlib
import json
import os
import signal
import stat
import time

MAX_JOURNAL=4*1024*1024
MAX_PROC=131072
CREATION_MODEL_SHA256='6d72c6db01f60c8d66fb55bd0d3e179cbc5666f86164e1a9a7fd2342d09612bd'
# The verified bootstrap or same-process phase-zero loader must set these pins.
SOURCE_PINS=None


def held_open(held,path,flags,mode=0o777,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        held.append(None);slot=len(held)-1
        try:fd=os.open(path,flags,mode,dir_fd=dir_fd)
        except BaseException:held.pop();raise
        held[slot]=fd;return fd
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def same_json(left,right):
    return json.dumps(left,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(right,sort_keys=True,separators=(',',':'),allow_nan=False)


def remaining(template):
    return min(template['deadline_boot_ns']-time.clock_gettime_ns(time.CLOCK_BOOTTIME),
               template['deadline_mono_ns']-time.monotonic_ns(),template['utc_cap_ns']-time.time_ns())


def need_time(template):
    if remaining(template)<=0:raise TimeoutError('completion exceeded original caps')


def verify_proc_scope(proc_fd,scope):
    if type(scope) is not dict or set(scope)!={'proc_device','proc_inode','pidns_device','pidns_inode'}:raise ValueError('actual proc scope required')
    st=os.fstat(proc_fd)
    if (st.st_dev,st.st_ino)!=(scope['proc_device'],scope['proc_inode']):raise ValueError('proc identity changed')
    me=os.stat('/proc/self/ns/pid');one=os.stat('/proc/1/ns/pid')
    if (me.st_dev,me.st_ino)!=(scope['pidns_device'],scope['pidns_inode']) or (one.st_dev,one.st_ino)!=(me.st_dev,me.st_ino):raise ValueError('pid namespace scope differs')


def proc_identity_at(proc_fd,name):
    d=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=proc_fd)
    try:
        f=os.open('stat',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=d)
        try:
            data=os.read(f,65537)
            if len(data)>65536:raise ValueError('oversized proc stat')
        finally:os.close(f)
    finally:os.close(d)
    suffix=data.rsplit(b')',1)
    if len(suffix)!=2:raise ValueError('malformed process stat')
    fields=suffix[1].split()
    if len(fields)<20:raise ValueError('short process stat')
    return (int(fields[1]),int(fields[2]),fields[19])


def census_empty(proc_fd,scope,keeper_pid,timer_pgid,template):
    """Reject every scan/read/identity error and every group member/descendant."""
    verify_proc_scope(proc_fd,scope);rows={};count=0
    with os.scandir(proc_fd) as scan:
        for entry in scan:
            if not entry.name.isdigit():continue
            count+=1
            if count>MAX_PROC:raise ValueError('process census bound')
            need_time(template)
            rows[int(entry.name)]=proc_identity_at(proc_fd,entry.name)
    for pid,identity in rows.items():
        need_time(template)
        if proc_identity_at(proc_fd,str(pid))!=identity:raise ValueError('process identity changed during census')
    verify_proc_scope(proc_fd,scope)
    if keeper_pid not in rows:raise ValueError('keeper missing from census')
    if any(group==timer_pgid for _,group,_ in rows.values()):raise ValueError('private group not empty')
    if any(parent==keeper_pid for pid,(parent,_,_) in rows.items() if pid!=keeper_pid):
        raise ValueError('unexpected direct keeper child observed')
    return {'processes_checked':count,'private_group_empty_observed':True,
            'unexpected_direct_keeper_child_observed':False,
            'global_descendants':'UNKNOWN','evidence_class':'NONATOMIC_POINT_OBSERVATION'}



def verify_writer_sequence(records,row):
    name=row['name']
    relevant=[r for r in records if r.get('name')==name and r.get('state') in ('BEFORE_CREATE','BEFORE_WRITER_CLOSE','WRITER_CLOSED','BEFORE_IMMUTABLE','FILE_HELD')]
    if [r['state'] for r in relevant]!=['BEFORE_CREATE','BEFORE_WRITER_CLOSE','WRITER_CLOSED','BEFORE_IMMUTABLE','FILE_HELD']:
        raise ValueError('writer disposition sequence')
    before,closing,closed,freeze,finished=relevant
    if before.get('sha256')!=row['sha256'] or finished.get('sha256')!=row['sha256'] or not (closing.get('identity')==closed.get('identity')==freeze.get('identity')==finished.get('identity')):
        raise ValueError('writer identity sequence')
    return finished


def install_proof(install,root_fd,code_fd,closure_fd,nonce,release_sha,template,held):
    need_time(template)
    raw=install.read_stable(closure_fd,install.MAX_SOURCE)
    if install.sha(raw)!=install.CLOSURE_SHA256:raise ValueError('closure digest')
    closure=json.loads(raw,object_pairs_hook=install.unique)
    files=closure['files'];names={row['name'] for row in files}
    if len(files)!=23 or len(names)!=23:raise ValueError('closure membership')
    name='INSTALL-'+nonce+'.jsonl'
    fd=held_open(held,name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('install journal identity')
    journal_raw=install.read_stable(fd,MAX_JOURNAL)
    if not journal_raw.endswith(b'\n'):raise ValueError('incomplete install journal')
    lines=journal_raw.splitlines()
    records=[json.loads(line,object_pairs_hook=install.unique) for line in lines]
    if not records or records[0]!={'state':'CLAIMED','nonce':nonce,'release_sha256':release_sha,'closure_sha256':install.CLOSURE_SHA256}:raise ValueError('install claim')
    last=records[-1]
    if (last.get('state')!='SOURCE_INSTALLED' or last.get('nonce')!=nonce or
        last.get('closure_sha256')!=install.CLOSURE_SHA256 or any(r.get('state') in ('UNKNOWN_RETAINED','WRITER_CLOSURE_UNKNOWN') for r in records)):
        raise ValueError('install terminal journal')
    out=held_open(held,'installed-source-'+nonce,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=code_fd)
    sub=held_open(held,'parser',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=out)
    for fd_dir in (out,sub):
        st=os.fstat(fd_dir)
        if st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o755 or not install.flags(fd_dir)&install.IMMUTABLE:raise ValueError('directory not immutable')
    if install.ident(os.fstat(out))!=last.get('identity'):raise ValueError('output inode differs')
    parser_created=[r for r in records if r.get('state')=='DIRECTORY_CREATED' and r.get('name')=='parser']
    root_freeze=[r for r in records if r.get('state')=='BEFORE_DIRECTORY_IMMUTABLE' and r.get('name')=='root']
    parser_freeze=[r for r in records if r.get('state')=='BEFORE_DIRECTORY_IMMUTABLE' and r.get('name')=='parser']
    if (len(parser_created)!=1 or len(root_freeze)!=1 or len(parser_freeze)!=1 or
        parser_created[0].get('identity')!=install.ident(os.fstat(sub)) or
        parser_freeze[0].get('identity')!=install.ident(os.fstat(sub)) or
        root_freeze[0].get('identity')!=install.ident(os.fstat(out))):raise ValueError('directory journal identity')
    top={n for n in names if '/' not in n}|{'parser'};nested={n.split('/')[1] for n in names if n.startswith('parser/')}
    if set(os.listdir(out))!=top or set(os.listdir(sub))!=nested:raise ValueError('installed membership')
    result=[]
    for row in files:
        need_time(template);name=row['name'];parts=name.split('/');directory=sub if len(parts)==2 else out
        finished=verify_writer_sequence(records,row)
        f=held_open(held,parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory);st=os.fstat(f)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o444 or
            not same_json(install.ident(st),finished['identity']) or st.st_size!=row['size'] or not install.flags(f)&install.IMMUTABLE):raise ValueError('installed file identity')
        if install.sha(install.read_stable(f,install.MAX_SOURCE))!=row['sha256']:raise ValueError('installed file bytes')
        result.append({'name':name,'identity':install.ident(st),'sha256':row['sha256']})
    return {'journal_identity':install.ident(os.fstat(fd)),'journal_sha256':install.sha(journal_raw),
            'directory_identity':install.ident(os.fstat(out)),'files':result}


def close_capture(install,latch,timer_record,journal_fd,root_fd,fd,name,template):
    need_time(template);before=os.fstat(fd);identity=install.ident(before)
    os.fsync(fd);install.journal(journal_fd,{'state':'BEFORE_CAPTURE_CLOSE','name':name,'identity':identity,'historical_fd':fd})
    import signal
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        with latch.lock:
            latch.retained.remove(fd)
            if fd in timer_record.handles:timer_record.handles.remove(fd)
        try:os.close(fd)
        except BaseException:
            try:install.journal(journal_fd,{'state':'CAPTURE_CLOSURE_UNKNOWN','name':name,'historical_fd':fd,'do_not_use_or_retry':True})
            except BaseException:pass
            raise
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    install.journal(journal_fd,{'state':'CAPTURE_WRITER_CLOSED','name':name,'identity':identity})
    readfd=held_open(latch.retained,name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
    st=os.fstat(readfd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or
        install.ident(st)!=identity):raise ValueError('capture identity')
    raw=install.read_stable(readfd,32*1024*1024)
    return {'name':name,'identity':identity,'length':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'writer_closed':True}


def retire_lease_if_authorized(*unused):
    raise ValueError('parent owns the shared lease disposition')


def verify_creation_model_value(install,owner,template,intent):
    """Validate Root-reviewed direct-role model; never infer global state."""
    keys={'issuer_sha256','completion_sha256','ipc_sha256','review_sha256'}
    if type(SOURCE_PINS) is not dict or set(SOURCE_PINS)!=keys:
        raise ValueError('verified direct source pins absent')
    row=owner.get('creation_model_approval') if type(owner) is dict else None
    expected={'version','record_type','scope','nonce','native_release','native_currentfree',
              'global_descendants','status','model_sha256','issuer_sha256','completion_sha256',
              'installer_sha256','wait_sha256','ipc_sha256','runtime_sha256','source_closure_sha256',
              'review_sha256','trusted_platform'}
    if (type(row) is not dict or set(row)!=expected or type(row['version']) is not int or row['version']!=1 or
        row['record_type']!='ROOT_INSTALL_DIRECT_MODEL_APPROVAL_V1' or row['scope']!='ROOT_CODE_INSTALL_ONLY' or
        row['nonce']!=template['nonce'] or row['native_release'] is not False or row['native_currentfree'] is not None or
        row['global_descendants']!='UNKNOWN' or row['status']!='APPROVED_KNOWN_ROLE_MODEL' or
        row['model_sha256']!='98ea72583a41f747f01c5bdb04b545319fc08cedf443366a6c2637a35562ed04' or
        row['issuer_sha256']!=SOURCE_PINS['issuer_sha256'] or row['completion_sha256']!=SOURCE_PINS['completion_sha256'] or
        row['ipc_sha256']!=SOURCE_PINS['ipc_sha256'] or row['review_sha256']!=SOURCE_PINS['review_sha256'] or
        row['installer_sha256']!=template['installer_sha256'] or row['wait_sha256']!=intent['wait_literal_sha256'] or
        row['runtime_sha256']!=template['interpreter']['sha256'] or row['source_closure_sha256']!=install.CLOSURE_SHA256 or
        row['trusted_platform']!='DIRECT_CPYTHON_LIBC_KERNEL' or not install.hex64(row['review_sha256'])):
        raise ValueError('reviewed direct creation model differs')
    return {'record_type':row['record_type'],'model_sha256':row['model_sha256'],
            'review_sha256':row['review_sha256'],'scope':'ROOT_CODE_INSTALL_ONLY','global_descendants':'UNKNOWN'}


def verify_creation_model(install,owner_fd,template,intent):
    install.root_file(owner_fd);raw=install.read_stable(owner_fd,install.MAX_SOURCE)
    if install.sha(raw)!=template['owner_release_sha256']:raise ValueError('owner release hash')
    return verify_creation_model_value(install,json.loads(raw,object_pairs_hook=install.unique),template,intent)


def publish_full_result(install,latch,journal_fd,root_fd,nonce,result,template):
    """Durably hand complete proof to Root before any operation lease close."""
    need_time(template)
    raw=(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if len(raw)>MAX_JOURNAL:raise ValueError('result too large')
    name='INSTALL-RESULT-'+nonce+'.json'
    install.journal(journal_fd,{'state':'BEFORE_RESULT_CREATE','name':name,'nonce':nonce})
    writer=held_open(latch.retained,name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
    os.fchmod(writer,0o600);install.write_all(writer,raw);os.fsync(writer);os.fsync(root_fd);identity=install.ident(os.fstat(writer))
    install.journal(journal_fd,{'state':'BEFORE_RESULT_WRITER_CLOSE','identity':identity,'historical_fd':writer})
    import signal
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        with latch.lock:latch.retained.remove(writer)
        try:os.close(writer)
        except BaseException:
            try:install.journal(journal_fd,{'state':'RESULT_WRITER_CLOSURE_UNKNOWN','historical_fd':writer,'do_not_use_or_retry':True})
            except BaseException:pass
            raise
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    fd=held_open(latch.retained,name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd)
    st=os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or
        install.ident(st)!=identity or install.read_stable(fd,MAX_JOURNAL)!=raw):raise ValueError('durable result identity')
    digest=install.sha(raw)
    install.journal(journal_fd,{'state':'RESULT_DURABLE','name':name,'identity':identity,'sha256':digest,'nonce':nonce})
    # Parent receives this exact complete object through the authenticated
    # retained-descriptor handoff; no lease disposition is performed here.
    return {'name':name,'identity':identity,'sha256':digest}


def set_subreaper():
    import ctypes
    libc=ctypes.CDLL(None,use_errno=True);prctl=libc.prctl
    prctl.argtypes=(ctypes.c_int,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong,ctypes.c_ulong);prctl.restype=ctypes.c_int
    if prctl(36,1,0,0,0)!=0:raise OSError(ctypes.get_errno(),'PR_SET_CHILD_SUBREAPER')
    actual=ctypes.c_int(-1)
    if prctl(37,ctypes.addressof(actual),0,0,0)!=0 or actual.value!=1:raise OSError(ctypes.get_errno(),'PR_GET_CHILD_SUBREAPER')


def _parent_context(frame,fds,admission_raw,review_raw,retained,phase1):
    import install_source_closure as install
    import install_issuer as issuer
    import reviewed_controller_reader as prelim
    if type(fds) is not list or len(fds)!=3:raise ValueError('actual root/code/closure FDs required')
    root,code,closure=fds
    request=json.loads(admission_raw,object_pairs_hook=install.unique)
    if type(request) is not dict or request.get('nonce')!=frame.get('nonce') or not install.hex64(frame.get('nonce')):
        raise ValueError('reviewed admission nonce')
    if type(review_raw) is not bytes or type(SOURCE_PINS) is not dict or set(SOURCE_PINS) not in ({'issuer_sha256','completion_sha256','ipc_sha256'},{'issuer_sha256','completion_sha256','ipc_sha256','review_sha256'}):
        raise ValueError('actual review or held-verified module pins')
    def opened(name):return held_open(retained,name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
    review_fd=opened('expert-review');install.root_file(review_fd)
    if install.read_stable(review_fd,install.MAX_SOURCE)!=review_raw:raise ValueError('sealed review differs')
    review_digest=install.sha(review_raw)
    if 'review_sha256' in SOURCE_PINS and SOURCE_PINS['review_sha256']!=review_digest:raise ValueError('review pin changed')
    SOURCE_PINS['review_sha256']=review_digest
    owner_fd=opened('owner-release.json');install.root_file(owner_fd)
    owner_raw=install.read_stable(owner_fd,install.MAX_SOURCE)
    expected=(json.dumps(request['owner_release'],sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if owner_raw!=expected or install.sha(owner_raw)!=request['owner_release_sha256'] or request['owner_release'].get('review_sha256')!=review_digest:raise ValueError('owner intent differs')
    intent_fd=opened('start-intent.json');install.root_file(intent_fd)
    intent=json.loads(install.read_stable(intent_fd,install.MAX_SOURCE),object_pairs_hook=install.unique)
    template=intent['release_template'];nonce=frame['nonce']
    if (intent['nonce']!=nonce or template['nonce']!=nonce or template['root_parent_pid']!=os.getpid() or
        template['root_parent_birth']!=install.proc_birth(os.getpid()) or template['owner_release_sha256']!=request['owner_release_sha256'] or
        template['one_shot_admission_id']!=request['one_shot_admission_id'] or
        template['deadline_boot_ns']!=request['deadline_boot_ns'] or template['deadline_mono_ns']!=request['deadline_mono_ns'] or
        template['utc_cap_ns']!=request['utc_cap_ns'] or template['retire_operation_only'] is not request['retire_operation_only']):
        raise ValueError('actual start intent differs')
    if not same_json(install.ident(os.fstat(root)),template['operation_root']) or not same_json(install.ident(os.fstat(code)),template['code_parent']):raise ValueError('strict root/code identities')
    install.dir_identity(root,template['operation_root'],True);install.dir_identity(code,template['code_parent'])
    if install.sha(install.read_stable(closure,install.MAX_SOURCE))!=install.CLOSURE_SHA256:raise ValueError('closure differs')
    root_named=install.open_exact(template['operation_path'],template['operation_ancestors'],True)
    code_named=install.open_exact(template['code_path'],template['code_ancestors'],True,True)
    install.dir_identity(root_named,template['operation_root'],True);install.dir_identity(code_named,template['code_parent'])
    code_stat=os.fstat(code)
    if code_stat.st_uid!=0 or stat.S_IMODE(code_stat.st_mode)!=0o755:raise ValueError('code parent mode')
    source_named=install.open_exact(install.SOURCE_DIR,template['source_ancestors'])
    install.dir_identity(source_named,template['source_dir'])
    for name,key in (('controls.json','controls_sha256'),('capacity.json','capacity_sha256')):
        fd=opened(name);install.root_file(fd)
        if install.sha(install.read_stable(fd,install.MAX_SOURCE))!=template[key]:raise ValueError('sealed control copy differs')
    host_fd=opened('host-custody.json');install.verify_host_receipt(host_fd,template)
    model=verify_creation_model(install,owner_fd,template,intent)
    if not phase1 and frame.get('result',{}).get('creation_model')!=model:raise ValueError('result model differs')
    issuer.fresh_controls(prelim,install,template,intent['phase1_deadline_boot_ns'] if phase1 else template['deadline_boot_ns'])
    if (intent['service_status']!='NO_NEW_REJECTION' or type(intent['weekly_used_percent']) not in (int,float) or not 0<=intent['weekly_used_percent']<100 or
        type(intent['weekly_observed_utc_ns']) is not int or (phase1 and not 0<=time.time_ns()-intent['weekly_observed_utc_ns']<=30000000000)):
        raise ValueError('included usage/service')
    release_fd=opened('INSTALL-RELEASE-'+nonce+'.json');install.root_file(release_fd)
    release_raw=install.read_stable(release_fd,install.MAX_SOURCE)
    if install.sha(release_raw)!=frame['release_sha256']:raise ValueError('actual release digest')
    release=json.loads(release_raw,object_pairs_hook=install.unique)
    expected_release=dict(template)
    expected_release.update(controller_pid=frame['keeper_pid'],controller_birth=frame['keeper_birth'],
                            keeper_pid=frame['keeper_pid'],keeper_birth=frame['keeper_birth'],
                            installer_pid=frame['installer_pid'],installer_birth=frame['installer_birth'])
    canonical=lambda value:(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if canonical(release)!=canonical(expected_release):raise ValueError('actual release actor binding')
    return install,request,intent,template,root,code,closure,release


def verify_parent_go(frame,fds,admission_raw,review_raw,retained):
    install,request,intent,template,root,code,closure,release=_parent_context(frame,fds,admission_raw,review_raw,retained,True)
    lease=template['lease']
    if type(lease) is not dict or set(lease)!={'device','inode'} or type(lease['device']) is not int or lease['device']<0 or type(lease['inode']) is not int or lease['inode']<=0:raise ValueError('strict lease identity')
    return {'nonce':intent['nonce'],'release_sha256':frame['release_sha256'],'scope':'ROOT_CODE_INSTALL_ONLY','native_currentfree':None,'lease':lease}


def verify_parent_result(frame,fds,admission_raw,review_raw,retained):
    install,request,intent,template,root,code,closure,release=_parent_context(frame,fds,admission_raw,review_raw,retained,False)
    result=frame.get('result');nonce=intent['nonce']
    if (type(result) is not dict or result.get('status')!='INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ' or
        result.get('nonce')!=nonce or result.get('native_release') is not False or result.get('native_currentfree') is not None or
        result.get('global_descendants')!='UNKNOWN' or result.get('release_sha256')!=frame['release_sha256'] or
        result.get('source_closure_sha256')!=install.CLOSURE_SHA256 or result.get('lease_disposition_at_handoff')!='HELD' or
        type(result.get('installer_wait_status')) is not int or result.get('installer_wait_status')!=0 or not same_json(result.get('installer'),{'pid':frame['installer_pid'],'birth':frame['installer_birth'],'pgid':frame['installer_pid']}) or
        not same_json(result.get('keeper'),{'pid':frame['keeper_pid'],'birth':frame['keeper_birth']})):raise ValueError('result scope/roles differ')
    proof=install_proof(install,root,code,closure,nonce,frame['release_sha256'],template,retained)
    if not same_json(proof,result.get('install_proof')):raise ValueError('independent installed proof differs')
    journal=held_open(retained,'INSTALL-START-'+nonce+'.jsonl',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
    raw=install.read_stable(journal,MAX_JOURNAL)
    if not raw.endswith(b'\n'):raise ValueError('incomplete keeper journal')
    records=[json.loads(line,object_pairs_hook=install.unique) for line in raw.splitlines()]
    if any(row.get('state') in ('UNKNOWN_RETAINED','CAPTURE_CLOSURE_UNKNOWN','RELEASE_WRITER_CLOSURE_UNKNOWN') for row in records):raise ValueError('unknown retained journal')
    waits=[row for row in records if row.get('state')=='INSTALLER_DIRECT_WAIT']
    if not same_json(waits,[{'state':'INSTALLER_DIRECT_WAIT','installer_pid':frame['installer_pid'],'birth':frame['installer_birth'],'status':0}]):raise ValueError('direct wait journal')
    captures=result.get('captures')
    if type(captures) is not list or len(captures)!=2:raise ValueError('capture cardinality')
    names={'INSTALL-CAPTURE-'+nonce+'-stdout','INSTALL-CAPTURE-'+nonce+'-stderr'}
    if {row.get('name') for row in captures}!=names:raise ValueError('capture names')
    for row in captures:
        if type(row) is not dict or set(row)!={'name','identity','length','sha256','writer_closed'} or row['writer_closed'] is not True:raise ValueError('capture schema')
        closed=[r for r in records if r.get('state')=='CAPTURE_WRITER_CLOSED' and r.get('name')==row['name']]
        if len(closed)!=1 or not same_json(closed[0].get('identity'),row['identity']):raise ValueError('capture writer closure')
        fd=held_open(retained,row['name'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root);st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or install.ident(st)!=row['identity']:raise ValueError('capture inode')
        content=install.read_stable(fd,32*1024*1024)
        if len(content)!=row['length'] or install.sha(content)!=row['sha256']:raise ValueError('capture bytes')
    result_fd=held_open(retained,'INSTALL-RESULT-'+nonce+'.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root)
    st=os.fstat(result_fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600:raise ValueError('result identity')
    expected=(json.dumps(result,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    if install.read_stable(result_fd,MAX_JOURNAL)!=expected:raise ValueError('durable result bytes')
    return {'scope':'ROOT_CODE_INSTALL_ONLY','nonce':nonce,'proof':proof,'captures':captures,'native_currentfree':None}


def verify_terminal_result(result,installer_pid,installer_birth,keeper_wait_status):
    if (type(result) is not dict or type(installer_pid) is not int or type(installer_birth) is not str or
        type(keeper_wait_status) is not int or not os.WIFEXITED(keeper_wait_status) or os.WEXITSTATUS(keeper_wait_status)!=0 or
        type(result.get('installer_wait_status')) is not int or result.get('installer_wait_status')!=0 or not same_json(result.get('installer'),{'pid':installer_pid,'birth':installer_birth,'pgid':installer_pid}) or
        result.get('native_release') is not False or result.get('native_currentfree') is not None or result.get('global_descendants')!='UNKNOWN'):
        raise ValueError('terminal evidence differs')
    return {'keeper_direct_wait_status':keeper_wait_status,'installer_direct_wait_status':0,'native_currentfree':None}


def verify_parent_retirement_authority(result,admission_raw,review_raw):
    import install_source_closure as install
    request=json.loads(admission_raw,object_pairs_hook=install.unique);owner=request['owner_release']
    if (request.get('retire_operation_only') is not True or type(owner) is not dict or
        owner.get('retire_operation_only') is not True or owner.get('record_type')!='ROOT_INSTALL_OPERATION_RETIREMENT_V1' or
        owner.get('scope')!='ROOT_CODE_INSTALL_ONLY' or owner.get('native_release') is not False or
        owner.get('status')!='APPROVED_IF_VERIFIED' or owner.get('nonce')!=result.get('nonce') or
        not install.hex64(owner.get('review_sha256')) or install.sha(review_raw)!=owner['review_sha256'] or
        result.get('native_release') is not False or result.get('native_currentfree') is not None or
        result.get('global_descendants')!='UNKNOWN' or type(result.get('installer_wait_status')) is not int or result.get('installer_wait_status')!=0 or
        type(result.get('install_proof')) is not dict or len(result['install_proof'].get('files',[]))!=23 or
        type(result.get('captures')) is not list or len(result['captures'])!=2 or any(row.get('writer_closed') is not True for row in result['captures'])):
        raise ValueError('conditional operation-only retirement authority absent')
    return {'scope':'ROOT_CODE_INSTALL_ONLY','nonce':result['nonce'],'native_release':False}
