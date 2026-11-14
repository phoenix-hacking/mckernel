"""Functional M14 source-install terminal verification; no security testing."""
import hashlib
import json
import os
import stat
import time

MAX_JOURNAL=4*1024*1024
MAX_PROC=131072
CREATION_MODEL_SHA256='6d72c6db01f60c8d66fb55bd0d3e179cbc5666f86164e1a9a7fd2342d09612bd'
# The verified bootstrap or same-process phase-zero loader must set these pins.
SOURCE_PINS=None


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
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);held.append(fd)
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
    out=os.open('installed-source-'+nonce,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=code_fd);held.append(out)
    sub=os.open('parser',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=out);held.append(sub)
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
        f=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=directory);held.append(f);st=os.fstat(f)
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o444 or
            install.ident(st)!=finished['identity'] or st.st_size!=row['size'] or not install.flags(f)&install.IMMUTABLE):raise ValueError('installed file identity')
        if install.sha(install.read_stable(f,install.MAX_SOURCE))!=row['sha256']:raise ValueError('installed file bytes')
        result.append({'name':name,'identity':install.ident(st),'sha256':row['sha256']})
    return {'journal_identity':install.ident(os.fstat(fd)),'journal_sha256':install.sha(journal_raw),
            'directory_identity':install.ident(os.fstat(out)),'files':result}


def close_capture(install,latch,timer_record,journal_fd,root_fd,fd,name,template):
    need_time(template);before=os.fstat(fd);identity=install.ident(before)
    os.fsync(fd);install.journal(journal_fd,{'state':'BEFORE_CAPTURE_CLOSE','name':name,'identity':identity,'historical_fd':fd})
    import signal
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
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
    readfd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);latch.retain(readfd)
    st=os.fstat(readfd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or
        install.ident(st)!=identity):raise ValueError('capture identity')
    raw=install.read_stable(readfd,32*1024*1024)
    return {'name':name,'identity':identity,'length':len(raw),'sha256':hashlib.sha256(raw).hexdigest(),'writer_closed':True}


def retire_lease_if_authorized(install,latch,timer_record,journal_fd,lease_fd,owner_fd,release,complete):
    if not release['retire_operation_only']:return False
    install.root_file(owner_fd);raw=install.read_stable(owner_fd,install.MAX_SOURCE)
    if install.sha(raw)!=release['owner_release_sha256']:raise ValueError('retirement authority bytes')
    authority=json.loads(raw,object_pairs_hook=install.unique)
    terminals=complete.get('terminals',{});census=complete.get('census',{});proof=complete.get('install_proof',{});captures=complete.get('captures',[])
    if (type(authority) is not dict or authority.get('record_type')!='ROOT_INSTALL_OPERATION_RETIREMENT_V1' or
        authority.get('scope')!='ROOT_CODE_INSTALL_ONLY' or authority.get('nonce')!=release['nonce'] or
        authority.get('native_release') is not False or authority.get('status')!='APPROVED_IF_VERIFIED' or
        not install.hex64(authority.get('review_sha256')) or complete.get('status')!='INSTALL_ONLY_COMPLETE_PENDING_UID1000_READ' or
        complete.get('nonce')!=release['nonce'] or complete.get('native_release') is not False or
        complete.get('native_currentfree') is not None or terminals.get('timer_direct_wait_status')!=0 or
        terminals.get('installer_pidfd_terminal') is not True or terminals.get('installer_direct_wait_status') not in (None,0) or
        census.get('private_group_empty_observed') is not True or census.get('unexpected_direct_keeper_child_observed') is not False or census.get('global_descendants')!='UNKNOWN' or
        census.get('evidence_class')!='NONATOMIC_POINT_OBSERVATION' or complete.get('creation_model_bound') is not True or
        type(proof.get('files')) is not list or len(proof['files'])!=23 or type(captures) is not list or
        len(captures)!=2 or any(row.get('writer_closed') is not True for row in captures)):
        raise ValueError('operation-only retirement authority or positive proof absent')
    need_time(release);install.journal(journal_fd,{'state':'BEFORE_OWNED_LEASE_CLOSE','historical_fd':lease_fd})
    latch.lease_disposition='CLOSING'
    import signal
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
    try:
        with latch.lock:
            latch.retained.remove(lease_fd)
            if lease_fd in timer_record.handles:timer_record.handles.remove(lease_fd)
        try:os.close(lease_fd)
        except BaseException:
            latch.lease_disposition='CLOSURE_UNKNOWN'
            try:install.journal(journal_fd,{'state':'LEASE_CLOSURE_UNKNOWN','historical_fd':lease_fd,'do_not_use_or_retry':True})
            except BaseException:pass
            raise
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    latch.lease_disposition='CLOSED_CONFIRMED'
    install.journal(journal_fd,{'state':'OWNED_LEASE_FD_CLOSED','operation_only':True,'native_release':False})
    return True


TIMEOUT_PROOF_SHA256='2e7b538161bed50275f36befa2011344ccebc0370a4b2a6bcb4fed76235066f2'
TIMEOUT_BINARY_SHA256='91db1e64064f0bf5ee99abda3a054cc6f05748dad2af5a145f890c9172d28d73'


def verify_creation_model_value(install,owner,template,intent):
    """Check approved finite creation model; this is not live custody proof."""
    if type(SOURCE_PINS) is not dict or set(SOURCE_PINS)!={'issuer_sha256','completion_sha256','timeout_proof_sha256','review_sha256'}:
        raise ValueError('verified source/toolproof pins absent')
    if SOURCE_PINS['timeout_proof_sha256']!=TIMEOUT_PROOF_SHA256:raise ValueError('timeout toolproof pin differs')
    row=owner.get('creation_model_approval') if type(owner) is dict else None
    keys={'version','record_type','scope','nonce','native_release','native_currentfree','global_descendants',
          'status','model_sha256','toolproof_sha256','issuer_sha256','completion_sha256','installer_sha256',
          'wait_sha256','timeout_sha256','runtime_sha256','source_closure_sha256','review_sha256','trusted_platform'}
    if (type(row) is not dict or set(row)!=keys or type(row['version']) is not int or row['version']!=1 or
        row['record_type']!='ROOT_INSTALL_CREATION_MODEL_APPROVAL_V1' or row['scope']!='ROOT_CODE_INSTALL_ONLY' or
        row['nonce']!=template['nonce'] or row['native_release'] is not False or row['native_currentfree'] is not None or
        row['global_descendants']!='UNKNOWN' or row['status']!='APPROVED_KNOWN_ROLE_MODEL' or
        row['trusted_platform']!='PINNED_TIMEOUT_CPYTHON_LIBC_KERNEL' or row['model_sha256']!=CREATION_MODEL_SHA256 or
        row['toolproof_sha256']!=TIMEOUT_PROOF_SHA256 or row['issuer_sha256']!=SOURCE_PINS['issuer_sha256'] or
        row['completion_sha256']!=SOURCE_PINS['completion_sha256'] or row['installer_sha256']!=template['installer_sha256'] or
        row['wait_sha256']!=intent['wait_literal_sha256'] or row['timeout_sha256']!=TIMEOUT_BINARY_SHA256 or
        row['timeout_sha256']!=intent['timeout_exe_sha256'] or row['runtime_sha256']!=template['interpreter']['sha256'] or
        row['source_closure_sha256']!=install.CLOSURE_SHA256 or not install.hex64(row['review_sha256']) or
        row['review_sha256']!=SOURCE_PINS['review_sha256']):
        raise ValueError('Root-approved reviewed known-role creation model absent or differs')
    return {'record_type':row['record_type'],'model_sha256':row['model_sha256'],'toolproof_sha256':row['toolproof_sha256'],
            'review_sha256':row['review_sha256'],'trusted_platform':row['trusted_platform'],
            'scope':'ROOT_CODE_INSTALL_ONLY','global_descendants':'UNKNOWN'}


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
    writer=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd);latch.retain(writer)
    os.fchmod(writer,0o600);install.write_all(writer,raw);os.fsync(writer);os.fsync(root_fd);identity=install.ident(os.fstat(writer))
    install.journal(journal_fd,{'state':'BEFORE_RESULT_WRITER_CLOSE','identity':identity,'historical_fd':writer})
    import signal
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
    try:
        with latch.lock:latch.retained.remove(writer)
        try:os.close(writer)
        except BaseException:
            try:install.journal(journal_fd,{'state':'RESULT_WRITER_CLOSURE_UNKNOWN','historical_fd':writer,'do_not_use_or_retry':True})
            except BaseException:pass
            raise
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=root_fd);latch.retain(fd)
    st=os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o600 or
        install.ident(st)!=identity or install.read_stable(fd,MAX_JOURNAL)!=raw):raise ValueError('durable result identity')
    digest=install.sha(raw)
    install.journal(journal_fd,{'state':'RESULT_DURABLE','name':name,'identity':identity,'sha256':digest,'nonce':nonce})
    # The actual Root capture receives the entire proof before any lease close.
    if os.write(1,raw)!=len(raw):raise OSError('short result handoff')
    install.journal(journal_fd,{'state':'RESULT_HANDED_OFF','sha256':digest,'nonce':nonce})
    return {'name':name,'identity':identity,'sha256':digest}
