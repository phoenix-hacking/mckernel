"""Functional McKernel source installation only; no security testing.

One-shot future entry. The independently admitted root watchdog must start the exact
immutable installer and retain parent/lease ownership. No work occurs on import.
"""
import argparse
import calendar
import fcntl
import hashlib
import json
import os
import signal
import stat
import struct
import sys
import time

CLOSURE_SHA256='81be55d5bf48ff462d291683ef1a26238b27581026bc5ffacc488125b6667ba6'
SOURCE_DIR='/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-MAX-PREFERRED-20261030-1/root-install-source-10/package'
WEEKLY_UTC_CAP_NS=calendar.timegm((2026,11,4,6,35,33))*1000000000
GETFLAGS=0x80086601
SETFLAGS=0x40086602
IMMUTABLE=0x10
MAX_SOURCE=2*1024*1024
_HELD=[]


def fail(message):raise ValueError(message)


def unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:fail('duplicate key')
        value[key]=item
    return value


def read_stable(fd,limit):
    before=os.fstat(fd)
    if not stat.S_ISREG(before.st_mode) or before.st_size>limit:fail('source type/size')
    os.lseek(fd,0,os.SEEK_SET);out=bytearray()
    while len(out)<=limit:
        part=os.read(fd,min(65536,limit+1-len(out)))
        if not part:break
        out.extend(part)
    after=os.fstat(fd)
    identity=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if len(out)>limit or identity(before)!=identity(after) or len(out)!=before.st_size:fail('unstable source')
    return bytes(out)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def flags(fd):
    raw=bytearray(4);fcntl.ioctl(fd,GETFLAGS,raw,True);return struct.unpack('I',raw)[0]


def ident(st):return {'device':st.st_dev,'inode':st.st_ino}


def hex64(value):
    return type(value) is str and len(value)==64 and all(ch in '0123456789abcdef' for ch in value)


def proc_birth(pid):
    with open('/proc/%d/stat'%pid,'r') as stream:text=stream.read(65536)
    fields=text.rsplit(')',1)[1].split()
    if len(fields)<20 or fields[0] in ('Z','X','x'):fail('parent birth unavailable')
    return fields[19]


def clock_check(release,controller_is_self=False):
    boot=time.clock_gettime_ns(time.CLOCK_BOOTTIME);mono=time.monotonic_ns();utc=time.time_ns()
    actual_controller=os.getpid() if controller_is_self else os.getppid()
    if actual_controller!=release['controller_pid'] or proc_birth(release['controller_pid'])!=release['controller_birth']:
        fail('controller no longer owns operation')
    if not (release['issued_boot_ns']<=boot<release['deadline_boot_ns'] and
            mono<release['deadline_mono_ns'] and utc<release['utc_cap_ns']<=WEEKLY_UTC_CAP_NS):
        fail('actual time bound exceeded')


def root_file(fd):
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)&0o022 or not flags(fd)&IMMUTABLE:
        fail('root-owned immutable file required')


def dir_identity(fd,expected,private=False):
    st=os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode) or ident(st)!=expected:fail('directory identity mismatch')
    if private and (st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700):fail('root-private directory required')


def open_exact(path,expected_ancestors,root_controlled=False,other_traverse=False):
    if type(path) is not str or not path.startswith('/') or '//' in path:fail('absolute canonical path required')
    parts=path.split('/')[1:]
    if not parts or any(x in ('','.','..') for x in parts) or type(expected_ancestors) is not list or len(expected_ancestors)!=len(parts)+1:
        fail('ancestor shape')
    current=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC);_HELD.append(current)
    dir_identity(current,expected_ancestors[0])
    if root_controlled and (os.fstat(current).st_uid!=0 or stat.S_IMODE(os.fstat(current).st_mode)&0o022):fail('untrusted root ancestry')
    if other_traverse and not stat.S_IMODE(os.fstat(current).st_mode)&0o001:fail('code ancestry not traversable')
    for index,part in enumerate(parts):
        current=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current)
        _HELD.append(current);dir_identity(current,expected_ancestors[index+1])
        if root_controlled and (os.fstat(current).st_uid!=0 or stat.S_IMODE(os.fstat(current).st_mode)&0o022):fail('untrusted root ancestry')
        if other_traverse and not stat.S_IMODE(os.fstat(current).st_mode)&0o001:fail('code ancestry not traversable')
    return current


def write_all(fd,raw):
    offset=0
    while offset<len(raw):
        count=os.write(fd,raw[offset:])
        if count<=0:raise OSError('short write')
        offset+=count


def journal(fd,event):
    write_all(fd,(json.dumps(event,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())
    os.fsync(fd)


def finish_writer(wfd,journal_fd,name,written):
    """Record ownership transfer before close; an uncertain fd is never retried."""
    journal(journal_fd,{'state':'BEFORE_WRITER_CLOSE','name':name,'identity':written,'historical_fd':wfd})
    oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT))
    try:
        _HELD.remove(wfd)
        try:os.close(wfd)
        except BaseException:
            try:journal(journal_fd,{'state':'WRITER_CLOSURE_UNKNOWN','name':name,'historical_fd':wfd,'do_not_use_or_retry':True})
            except BaseException:pass
            raise
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,oldmask)
    journal(journal_fd,{'state':'WRITER_CLOSED','name':name,'identity':written})


def verify_release(fd,expected,controller_is_self=False):
    if not hex64(expected):fail('admitted release digest required')
    root_file(fd);raw=read_stable(fd,MAX_SOURCE)
    if sha(raw)!=expected:fail('admission digest mismatch')
    release=json.loads(raw,object_pairs_hook=unique)
    keys={'version','purpose','nonce','boot_id','controller_pid','controller_birth','operation_root',
          'operation_path','operation_ancestors','code_path','code_ancestors','code_parent','source_dir','source_ancestors','lease','installer_sha256',
          'interpreter','closure_sha256','issued_boot_ns','deadline_boot_ns','deadline_mono_ns','utc_cap_ns',
          'one_shot_admission_id','controls_sha256','capacity_sha256','host_install_custody_sha256','owner_release_sha256',
          'term_grace_ns','kill_grace_ns','join_grace_ns','retire_operation_only','installer_pid','installer_birth','keeper_pid','keeper_birth'}
    if type(release) is not dict or set(release)!=keys or type(release['version']) is not int or release['version']!=1 or release['purpose']!='root-install-source-closure-v1':fail('admission schema')
    for key in ('nonce','installer_sha256','closure_sha256','one_shot_admission_id','controls_sha256','capacity_sha256','host_install_custody_sha256','owner_release_sha256'):
        if not hex64(release[key]):fail('missing actual admission binding '+key)
    if release['closure_sha256']!=CLOSURE_SHA256:fail('closure binding')
    for key in ('issued_boot_ns','deadline_boot_ns','deadline_mono_ns','utc_cap_ns','controller_pid','installer_pid','keeper_pid','term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(release[key]) is not int or release[key]<=0:fail('admission integer '+key)
    if type(release['retire_operation_only']) is not bool:fail('retirement intent')
    if type(release['controller_birth']) is not str or not release['controller_birth'].isdigit():fail('controller birth')
    actual_controller=os.getpid() if controller_is_self else os.getppid()
    if release['controller_pid']!=actual_controller or proc_birth(actual_controller)!=release['controller_birth']:fail('direct parent identity')
    if (os.getpid()!=release['installer_pid'] or proc_birth(os.getpid())!=release['installer_birth'] or
        proc_birth(release['keeper_pid'])!=release['keeper_birth']):fail('installer/keeper identity')
    with open('/proc/%d/stat'%actual_controller) as stream:parent_fields=stream.read(65536).rsplit(')',1)[1].split()
    if int(parent_fields[1])!=release['keeper_pid']:fail('timeout keeper parent')
    with open('/proc/sys/kernel/random/boot_id') as stream:boot=stream.read(128).strip()
    if release['boot_id']!=boot:fail('boot identity')
    clock_check(release,controller_is_self)
    return release


def verify_base_runtime(interp):
    """Installer-only trusted root-controlled base runtime; never alter it."""
    if (type(interp) is not dict or set(interp)!={'path','ancestors','device','inode','sha256'} or
        type(interp['path']) is not str or not hex64(interp['sha256'])):fail('interpreter binding')
    if os.readlink('/proc/self/exe')!=interp['path']:fail('running interpreter path differs')
    parent=open_exact(os.path.dirname(interp['path']),interp['ancestors'],True)
    fd=os.open(os.path.basename(interp['path']),os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent);_HELD.append(fd)
    st=os.fstat(fd)
    if (not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)&0o022 or
        ident(st)!={'device':interp['device'],'inode':interp['inode']}):fail('runtime owner or identity')
    if sha(read_stable(fd,128*1024*1024))!=interp['sha256']:fail('runtime bytes differ')
    running=os.stat('/proc/self/exe')
    if ident(running)!=ident(st):fail('running executable inode differs')


def verify_host_receipt(fd,release):
    root_file(fd);raw=read_stable(fd,MAX_SOURCE)
    if sha(raw)!=release['host_install_custody_sha256']:fail('host install custody digest')
    value=json.loads(raw,object_pairs_hook=unique)
    keys={'version','record_type','scope','native_release','native_currentfree','no_unlisted_later_operation',
          'v2_birth','retained_2gib_bytes','native12','scratch21','mutex27_4','boot_id','nonce',
          'issued_boot_ns','expires_boot_ns','host_available_bytes','host_floor_bytes','owner_release_sha256'}
    if (type(value) is not dict or set(value)!=keys or type(value['version']) is not int or value['version']!=1 or
        value['record_type']!='HOST_INSTALL_RESOURCE_CUSTODY_V1' or value['scope']!='ROOT_CODE_INSTALL_ONLY' or
        value['native_release'] is not False or value['native_currentfree'] is not None or
        value['no_unlisted_later_operation']!='UNKNOWN' or value['v2_birth'] is not None or
        type(value['retained_2gib_bytes']) is not int or value['retained_2gib_bytes']!=2147483648 or
        value['native12']!='HELD' or value['scratch21']!='HELD' or value['mutex27_4']!='HELD' or
        value['boot_id']!=release['boot_id'] or value['nonce']!=release['nonce'] or
        value['owner_release_sha256']!=release['owner_release_sha256']):fail('host-only custody record')
    for key in ('issued_boot_ns','expires_boot_ns','host_available_bytes','host_floor_bytes'):
        if type(value[key]) is not int or value[key]<0:fail('host custody integer')
    now=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    if not (value['issued_boot_ns']<=now<value['expires_boot_ns']<=release['deadline_boot_ns'] and
            value['host_available_bytes']>=value['host_floor_bytes']>=16*1024*1024*1024):
        fail('host custody freshness/capacity')
    return value


def install(release_fd,release_sha,source_fd,root_fd,code_fd,lease_fd,closure_fd,controls_fd,capacity_fd,host_custody_fd,owner_release_fd):
    if os.getuid()!=0 or os.geteuid()!=0:fail('admitted root operation required')
    release=verify_release(release_fd,release_sha)
    verify_base_runtime(release['interpreter'])
    verify_host_receipt(host_custody_fd,release)
    for fd,key in ((controls_fd,'controls_sha256'),(capacity_fd,'capacity_sha256'),
                   (host_custody_fd,'host_install_custody_sha256'),(owner_release_fd,'owner_release_sha256')):
        root_file(fd)
        if sha(read_stable(fd,MAX_SOURCE))!=release[key]:fail('actual receipt bytes differ: '+key)
    root_dir=open_exact(release['operation_path'],release['operation_ancestors'],True)
    code_dir=open_exact(release['code_path'],release['code_ancestors'],True,True)
    dir_identity(code_fd,release['code_parent']);dir_identity(code_dir,release['code_parent'])
    cs=os.fstat(code_fd)
    if cs.st_uid!=0 or stat.S_IMODE(cs.st_mode)!=0o755:fail('root-owned traversable code parent required')
    source_dir=open_exact(SOURCE_DIR,release['source_ancestors'])
    dir_identity(root_fd,release['operation_root'],True);dir_identity(root_dir,release['operation_root'],True)
    dir_identity(source_fd,release['source_dir']);dir_identity(source_dir,release['source_dir'])
    lease=os.fstat(lease_fd)
    if not stat.S_ISREG(lease.st_mode) or lease.st_uid!=0 or ident(lease)!=release['lease']:fail('lease identity')
    # The reviewed direct parent locks this exact open-file description before
    # fork and retains its copy; the child must never reopen or reflock it.
    if globals().get('_BOOTSTRAP_INSTALLER_HASH')!=release['installer_sha256']:
        fail('trusted verified-byte bootstrap required')
    closure_raw=read_stable(closure_fd,MAX_SOURCE)
    if sha(closure_raw)!=CLOSURE_SHA256:fail('source closure differs')
    closure=json.loads(closure_raw,object_pairs_hook=unique)
    if set(closure)!={'version','source_directory','python_files','contract_files','files'} or type(closure['version']) is not int or closure['version']!=1 or closure['source_directory']!=SOURCE_DIR or closure['python_files']!=20 or closure['contract_files']!=3 or len(closure['files'])!=23:
        fail('source closure shape')
    parser_source=os.open('parser',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=source_fd);_HELD.append(parser_source)
    blobs=[];names=set()
    for item in closure['files']:
        if type(item) is not dict or set(item)!={'name','size','sha256'}:fail('source row')
        name=item['name']
        if type(name) is not str or not name or name in names or not hex64(item['sha256']) or type(item['size']) is not int or not 0<=item['size']<=MAX_SOURCE:fail('source row values')
        parts=name.split('/')
        if len(parts) not in (1,2) or any(x in ('','.','..') for x in parts) or (len(parts)==2 and parts[0]!='parser'):fail('source relative path')
        names.add(name);clock_check(release)
        fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parser_source if len(parts)==2 else source_fd);_HELD.append(fd)
        raw=read_stable(fd,MAX_SOURCE)
        if len(raw)!=item['size'] or sha(raw)!=item['sha256']:fail('source bytes differ')
        blobs.append((item,raw))
    if sum(name.endswith('.py') for name in names)!=20 or not {'GRAPH-CONTRACT.json','parser/contract.json','parser/repaircontract.json','parser/candidate_data.py'}.issubset(names):fail('closure membership')
    claim='INSTALL-'+release['nonce']+'.jsonl'
    journal_fd=os.open(claim,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd);_HELD.append(journal_fd)
    os.fsync(root_fd)
    try:
        journal(journal_fd,{'state':'CLAIMED','nonce':release['nonce'],'release_sha256':release_sha,'closure_sha256':CLOSURE_SHA256})
        clock_check(release)
        output='installed-source-'+release['nonce']
        journal(journal_fd,{'state':'BEFORE_MKDIR','name':output,'parent':ident(os.fstat(code_fd))})
        os.mkdir(output,0o755,dir_fd=code_fd);os.fsync(code_fd)
        out=os.open(output,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=code_fd);_HELD.append(out)
        os.fchmod(out,0o755);ost=os.fstat(out)
        if ost.st_uid!=0 or stat.S_IMODE(ost.st_mode)!=0o755:fail('code directory mode')
        journal(journal_fd,{'state':'DIRECTORY_CREATED','identity':ident(ost)})
        journal(journal_fd,{'state':'BEFORE_MKDIR','name':'parser'})
        os.mkdir('parser',0o755,dir_fd=out);os.fsync(out)
        parser_out=os.open('parser',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=out);_HELD.append(parser_out)
        os.fchmod(parser_out,0o755);pst=os.fstat(parser_out)
        if pst.st_uid!=0 or stat.S_IMODE(pst.st_mode)!=0o755:fail('parser directory mode')
        journal(journal_fd,{'state':'DIRECTORY_CREATED','name':'parser','identity':ident(pst)})
        for item,raw in blobs:
            clock_check(release);name=item['name'];parts=name.split('/');parent=parser_out if len(parts)==2 else out
            journal(journal_fd,{'state':'BEFORE_CREATE','name':name,'sha256':item['sha256']})
            wfd=os.open(parts[-1],os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o444,dir_fd=parent);_HELD.append(wfd)
            os.fchmod(wfd,0o444);write_all(wfd,raw);os.fsync(wfd);os.fsync(parent);written=ident(os.fstat(wfd))
            finish_writer(wfd,journal_fd,name,written)
            check=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent);_HELD.append(check)
            st=os.fstat(check)
            if st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o444 or ident(st)!=written or sha(read_stable(check,MAX_SOURCE))!=item['sha256']:fail('installed file verification')
            prior=flags(check);journal(journal_fd,{'state':'BEFORE_IMMUTABLE','name':name,'identity':ident(st),'prior_flags':prior})
            fcntl.ioctl(check,SETFLAGS,struct.pack('I',prior|IMMUTABLE))
            if not flags(check)&IMMUTABLE:fail('immutable flag absent')
            if sha(read_stable(check,MAX_SOURCE))!=item['sha256'] or ident(os.fstat(check))!=written:fail('immutable reread differs')
            os.fsync(check);os.fsync(parent)
            journal(journal_fd,{'state':'FILE_HELD','name':name,'identity':ident(st),'sha256':item['sha256']})
        top={x for x in names if '/' not in x}|{'parser'};nested={x.split('/')[1] for x in names if x.startswith('parser/')}
        if set(os.listdir(out))!=top or set(os.listdir(parser_out))!=nested:fail('installed membership changed')
        for label,fd in (('parser',parser_out),('root',out)):
            before=flags(fd);journal(journal_fd,{'state':'BEFORE_DIRECTORY_IMMUTABLE','name':label,'identity':ident(os.fstat(fd)),'prior_flags':before})
            fcntl.ioctl(fd,SETFLAGS,struct.pack('I',before|IMMUTABLE))
            if not flags(fd)&IMMUTABLE:fail('directory immutable absent')
            os.fsync(fd)
        os.fsync(code_fd);clock_check(release)
        journal(journal_fd,{'state':'SOURCE_INSTALLED','identity':ident(os.fstat(out)),'closure_sha256':CLOSURE_SHA256,'nonce':release['nonce']})
        return output
    except BaseException as error:
        try:journal(journal_fd,{'state':'UNKNOWN_RETAINED','error_type':type(error).__name__})
        except BaseException:pass
        raise


def main():
    parser=argparse.ArgumentParser()
    for name in ('release-fd','source-fd','root-fd','code-fd','lease-fd','closure-fd','controls-fd','capacity-fd','host-custody-fd','owner-release-fd'):parser.add_argument('--'+name,type=int,required=True)
    parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args()
    try:install(args.release_fd,args.release_sha256,args.source_fd,args.root_fd,args.code_fd,args.lease_fd,args.closure_fd,args.controls_fd,args.capacity_fd,args.host_custody_fd,args.owner_release_fd)
    except BaseException:
        # External root watchdog owns this process and retained descriptors.
        # Unknown outcomes are never retired or retried here.
        while True:signal.pause()


if __name__=='__main__':main()
