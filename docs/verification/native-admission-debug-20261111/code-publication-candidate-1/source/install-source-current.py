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

CLOSURE_SHA256='56df8d9ba9ee78c8955b80861bb1fcbc39305f64439129b1174e457d91c85ce5'
# This fixed catalogue is the reviewed native code package only. No arbitrary closure CLI.
SOURCE_DIR='/home/holden/mckernel-work/m14-blocker-resolution-20261110/native-signal-real-binding-source-1/complete-interface-1/complete-candidate-2/correction-1/package'
FIXED_FILES=(('adapter.py', 18271, '6a2bc93c6e49cf69cdd14b86168476f3c5609a70f4873348bf1002cceb5fc8e3'), ('compositor.py', 15056, '987a00408b578c63f28ef1634d7fb4207ec5218258c9546da3864a0f28f1b63b'), ('custody_protocol_v2.py', 4452, '587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb'), ('deferred_fork.py', 12001, 'b28d2f3483fb90c858479b65c9cebe6bd1b586c01902f004ec44964da6b4625f'), ('graph_observations.py', 9505, 'df7bb673c206585318a4e41a58486c05548d9981b81074baeb29437f458114ed'), ('graph_producer.py', 10033, '58a46e9a51fe721fdd21a12958db9bc658aa591558c5b6a4ff3f640d02e053f5'), ('graph_server.py', 5764, '1ddf26217ce626882baa3b6a8ffe06af0bb16329e281ed78ac1c36dff4592074'), ('immutable_epoch.py', 4429, '018c15192472a3d8c5d598561969f78bc24e93a88e7c4bbecd9b79515c42dc20'), ('inplace_custody.py', 13865, '70307b730512cb56c3f63738fe9fc8c14a1603bb6ec4227e05db3ab36115890e'), ('materializer.py', 18424, 'c3115c13a29dde74f6d316b64d26a6266c5a5cfeed877ef19de088844e09ba37'), ('native_current_owner.py', 16267, '7207a8b68feaf4dc00bcb10cf25f32ef13073e1eeae060e86038c6f855080622'), ('native_diagnostic_container_owner.py', 60024, '3ecb921f3169f0116829d835cd4f1268bfe3f04ad9059f6494831fdb731fddd6'), ('native_resource_admission.py', 43352, 'afe83dc21462e92aee5642d425e65031c4f0d6eaa8d6bc73ee4c60f55775948b'), ('native_source_binding.py', 15188, '3fec8b716a8ad991eaf12949a7c42688733465b9931d13d1942b060d8cc282ca'), ('operation_supervisor.py', 9775, '1a1e1ed738a5fa8a62f010bacbb2a06b529f577fe93d37539e19f6c839b2be90'), ('operation_watchdog.py', 12077, 'debaf3c6ba43e09f632cf33505c7aabf72ba4dd18cf25b6a934b26ced3c5bb77'), ('ownership_latch.py', 4183, 'fb264b1e6f12852e6a11c44239089a015a02e25019f9094af586422398bfa390'), ('pidfd_compat.py', 3875, '068e8316ef03a03d1977d05ce755dfa8133c13bd4dfa56254c27b0066be2575c'), ('pidfd_custody.py', 10423, '3b22cac50183723456e6701031f00bdc446c04641c08c5864f1a379b5407686e'), ('retained-scope-facts.json', 12746, '7f7f4f58c733d6f42d631a1821241e3a632b823e981236038b03e675bdd4e362'), ('root_bootstrap.py', 18995, '7753d3ee7b05419fa3211afc910e65aec9c0086ae9dc1f2d5ff82ac1fb977328'), ('root_owner_entry.py', 4074, 'dc29c94ec726cac5840863f7cf1beb57bb950b2dc13ae8d68657a1f86792c472'), ('runtime_binding.py', 3350, '629b7b65d8d28169dffa71d86fbddeda8e1e0ef87f0dc4e91b264f8175717414'), ('source_freeze.py', 10475, '2a3cea45022e2104b6faa1ed8561ef9db1000a8a3734d94a1f17efab50ec8228'), ('split_inventory.py', 4799, '9bc54a33407c8abaed384a5d998fa3cea34d7f15179349e27e6122c09849de04'), ('supervisor_entry.py', 14804, 'a47aba63261aa94492b95614b0a53b899ee20bc359c8de321bd2f07ec34eb2cd'), ('union_owner.py', 20741, '955d879ff8fc0da6b81457bcea53415254a96367b9e23825bf07e8efb89ae2bb'), ('union_server_guarded.py', 12973, '3f96123f1a62ed427235c59f802452811522f62d5c5b4e5d84385c392a54a229'), ('verified_owner_loader.py', 6058, 'cec6e9506f29f07584ec5304c8deeb532a9d255be842b2faa55957c97a1f5c29'), ('verify_scripts_fd.py', 5695, '34bd9802c507b3408b685c6233f0a2f711edbdf7a6f31c5dcd3eaba70128ba8f'))

def fixed_catalog(closure):
    """Pure strict validation of this one fixed 29-code/one-static-data catalogue."""
    if (type(closure) is not dict or set(closure)!={'version','source_directory','python_files','contract_files','files'} or
        type(closure['version']) is not int or closure['version']!=1 or
        closure['source_directory']!=SOURCE_DIR or type(closure['python_files']) is not int or closure['python_files']!=29 or
        type(closure['contract_files']) is not int or closure['contract_files']!=1 or
        type(closure['files']) is not list or len(closure['files'])!=30):
        raise ValueError('source closure shape')
    actual=[];names=set()
    for row in closure['files']:
        if type(row) is not dict or set(row)!={'name','size','sha256'}:
            raise ValueError('source row')
        name=row['name']
        if (type(name) is not str or not name or name in ('.','..') or '/' in name or name in names or
            type(row['size']) is not int or not 0<=row['size']<=2097152 or
            type(row['sha256']) is not str or len(row['sha256'])!=64 or
            any(c not in '0123456789abcdef' for c in row['sha256'])):
            raise ValueError('source row values')
        names.add(name);actual.append((name,row['size'],row['sha256']))
    if tuple(actual)!=FIXED_FILES:
        raise ValueError('source closure membership')
    return closure['files']


# New-run bound from the actual 2026-11-05 included-only event; it is an outer
# ceiling, not a grant, a reset allowance, or a revival of the previous packet.
MAX_OPERATION_NS=180*1000000000
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
            mono<release['deadline_mono_ns'] and utc<release['utc_cap_ns']<=utc+MAX_OPERATION_NS):
        fail('actual time bound exceeded')


def root_file(fd):
    st=os.fstat(fd)
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)&0o022 or not flags(fd)&IMMUTABLE:
        fail('root-owned immutable file required')


def dir_identity(fd,expected,private=False):
    st=os.fstat(fd)
    if not stat.S_ISDIR(st.st_mode) or ident(st)!=expected:fail('directory identity mismatch')
    if private and (st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700):fail('root-private directory required')


def held_open(path,flags,mode=0o777,dir_fd=None):
    old=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
    try:
        _HELD.append(None);slot=len(_HELD)-1
        try:fd=os.open(path,flags,mode,dir_fd=dir_fd)
        except BaseException:_HELD.pop();raise
        _HELD[slot]=fd;return fd
    finally:signal.pthread_sigmask(signal.SIG_SETMASK,old)


def open_exact(path,expected_ancestors,root_controlled=False,other_traverse=False):
    if type(path) is not str or not path.startswith('/') or '//' in path:fail('absolute canonical path required')
    parts=path.split('/')[1:]
    if not parts or any(x in ('','.','..') for x in parts) or type(expected_ancestors) is not list or len(expected_ancestors)!=len(parts)+1:
        fail('ancestor shape')
    current=held_open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_CLOEXEC)
    dir_identity(current,expected_ancestors[0])
    if root_controlled and (os.fstat(current).st_uid!=0 or stat.S_IMODE(os.fstat(current).st_mode)&0o022):fail('untrusted root ancestry')
    if other_traverse and not stat.S_IMODE(os.fstat(current).st_mode)&0o001:fail('code ancestry not traversable')
    for index,part in enumerate(parts):
        current=held_open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=current)
        dir_identity(current,expected_ancestors[index+1])
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
    oldmask=signal.pthread_sigmask(signal.SIG_BLOCK,(signal.SIGINT,signal.SIGTERM,signal.SIGHUP,signal.SIGQUIT,signal.SIGALRM))
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
          'term_grace_ns','kill_grace_ns','join_grace_ns','retire_operation_only','installer_pid','installer_birth','keeper_pid','keeper_birth','root_parent_pid','root_parent_birth'}
    if type(release) is not dict or set(release)!=keys or type(release['version']) is not int or release['version']!=1 or release['purpose']!='root-install-source-closure-v1':fail('admission schema')
    for key in ('nonce','installer_sha256','closure_sha256','one_shot_admission_id','controls_sha256','capacity_sha256','host_install_custody_sha256','owner_release_sha256'):
        if not hex64(release[key]):fail('missing actual admission binding '+key)
    if release['closure_sha256']!=CLOSURE_SHA256:fail('closure binding')
    for key in ('issued_boot_ns','deadline_boot_ns','deadline_mono_ns','utc_cap_ns','controller_pid','installer_pid','keeper_pid','root_parent_pid','term_grace_ns','kill_grace_ns','join_grace_ns'):
        if type(release[key]) is not int or release[key]<=0:fail('admission integer '+key)
    if type(release['retire_operation_only']) is not bool:fail('retirement intent')
    if type(release['controller_birth']) is not str or not release['controller_birth'].isdigit():fail('controller birth')
    actual_controller=os.getpid() if controller_is_self else os.getppid()
    if release['controller_pid']!=actual_controller or proc_birth(actual_controller)!=release['controller_birth']:fail('direct parent identity')
    if (os.getpid()!=release['installer_pid'] or proc_birth(os.getpid())!=release['installer_birth'] or
        proc_birth(release['keeper_pid'])!=release['keeper_birth']):fail('installer/keeper identity')
    if release['controller_pid']!=release['keeper_pid'] or release['controller_birth']!=release['keeper_birth']:
        fail('direct controller and keeper identity differ')
    if type(release['root_parent_birth']) is not str or not release['root_parent_birth'].isdigit():
        fail('Root parent birth')
    with open('/proc/%d/stat'%actual_controller) as stream:parent_fields=stream.read(65536).rsplit(')',1)[1].split()
    if (int(parent_fields[1])!=release['root_parent_pid'] or release['root_parent_pid'] in (release['keeper_pid'],release['installer_pid']) or
        os.stat('/proc/%d'%release['root_parent_pid']).st_uid!=0 or proc_birth(release['root_parent_pid'])!=release['root_parent_birth']):
        fail('actual direct Root parent differs')
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
    rows=fixed_catalog(closure)
    blobs=[]
    for item in rows:
        name=item['name'];clock_check(release)
        fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=source_fd);_HELD.append(fd)
        raw=read_stable(fd,MAX_SOURCE)
        if len(raw)!=item['size'] or sha(raw)!=item['sha256']:fail('source bytes differ')
        blobs.append((item,raw))
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
        for item,raw in blobs:
            clock_check(release);name=item['name'];parent=out
            journal(journal_fd,{'state':'BEFORE_CREATE','name':name,'sha256':item['sha256']})
            wfd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o444,dir_fd=parent);_HELD.append(wfd)
            os.fchmod(wfd,0o444);write_all(wfd,raw);os.fsync(wfd);os.fsync(parent);written=ident(os.fstat(wfd))
            finish_writer(wfd,journal_fd,name,written)
            check=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent);_HELD.append(check)
            st=os.fstat(check)
            if st.st_uid!=0 or st.st_nlink!=1 or stat.S_IMODE(st.st_mode)!=0o444 or ident(st)!=written or sha(read_stable(check,MAX_SOURCE))!=item['sha256']:fail('installed file verification')
            prior=flags(check);journal(journal_fd,{'state':'BEFORE_IMMUTABLE','name':name,'identity':ident(st),'prior_flags':prior})
            fcntl.ioctl(check,SETFLAGS,struct.pack('I',prior|IMMUTABLE))
            if not flags(check)&IMMUTABLE:fail('immutable flag absent')
            if sha(read_stable(check,MAX_SOURCE))!=item['sha256'] or ident(os.fstat(check))!=written:fail('immutable reread differs')
            os.fsync(check);os.fsync(parent)
            journal(journal_fd,{'state':'FILE_HELD','name':name,'identity':ident(st),'sha256':item['sha256']})
        if set(os.listdir(out))!={item['name'] for item,_ in blobs}:fail('installed membership changed')
        for label,fd in (('root',out),):
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
