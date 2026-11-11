# Exact SourcePR6805178926 scoped filesystem provisioning; no subprocess or imports from the project.
import datetime,json,os,resource,stat,sys
ANCESTOR='/home/holden/mckernel-work/scratch'
BASENAME='m14-native-c964-a2f00a61-staging-parent'
TARGET=ANCESTOR+'/'+BASENAME
FINAL='native-signal-c964-a2f00a61-stage-20261111-1'
RO='/home/holden/mckernel-work/scratch-readonly-20261105'
NAMESPACE='mnt:[4026531841]'
ANCESTOR_ID={'device':66306,'inode':49551073,'uid':0,'gid':0,'mode':0o755}
RO_ID={'device':1836,'inode':2,'uid':1000,'gid':1000,'mode':0o700}
ANCESTOR_MOUNT='29 1 259:2 / / rw,relatime shared:1 - ext4 /dev/nvme0n1p2 rw,errors=remount-ro'
RO_MOUNT='974 29 7:44 / /home/holden/mckernel-work/scratch-readonly-20261105 ro,nosuid,nodev,relatime shared:623 - ext4 /dev/loop44 ro,norecovery'
GIB=1024**3
FLAGS=os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC

def need(ok,message):
    if not ok:raise RuntimeError(message)

def identity(fd):
    value=os.fstat(fd);need(stat.S_ISDIR(value.st_mode),'held object is not a directory')
    return dict(device=value.st_dev,inode=value.st_ino,uid=value.st_uid,gid=value.st_gid,mode=stat.S_IMODE(value.st_mode))

def mount_rows():
    with open('/proc/self/mountinfo','rb') as stream:raw=stream.read(131073)
    need(len(raw)<=131072,'mountinfo bound exceeded')
    return raw.decode('utf-8','strict').splitlines()

def covering(rows,path):
    candidates=[line for line in rows if path==line.split()[4] or path.startswith(line.split()[4].rstrip('/')+'/')]
    need(bool(candidates),'no containing mount')
    return max(candidates,key=lambda line:len(line.split()[4]))

def verify_mounts():
    need(os.readlink('/proc/self/ns/mnt')==NAMESPACE,'executor mount namespace changed')
    rows=mount_rows();need(covering(rows,ANCESTOR)==ANCESTOR_MOUNT,'canonical ancestor containing mount changed')
    need(covering(rows,RO)==RO_MOUNT,'protected RO loop44 mapping changed')
    need(covering(rows,TARGET)==ANCESTOR_MOUNT,'target crosses an unapproved mount')
    return dict(namespace=NAMESPACE,ancestor_mount=ANCESTOR_MOUNT,protected_RO_mount=RO_MOUNT)

def exact_missing(fd,name):
    try:os.stat(name,dir_fd=fd,follow_symlinks=False)
    except FileNotFoundError:return True
    return False

def capacity(host_fd,scratch_fd):
    host=os.fstatvfs(host_fd);scratch=os.fstatvfs(scratch_fd)
    h=host.f_bavail*host.f_frsize;v=scratch.f_bavail*scratch.f_frsize
    need(h>=17*GIB and v>=13*GIB,'fresh1GiB output reserve above host16/scratch12GiB floors unavailable')
    return dict(host_available_bytes=h,scratch_available_bytes=v,reserved_output_bytes=GIB,host_floor_bytes=16*GIB,scratch_floor_bytes=12*GIB)

def proc_birth():
    with open('/proc/self/stat','rb') as stream:raw=stream.read(16385)
    need(len(raw)<=16384,'self stat bound');value=raw.rsplit(b') ',1)[1].split()[19].decode('ascii')
    need(value.isdigit() and int(value)>0,'self birth missing');return value

def directory_empty(fd):
    with os.scandir(fd) as entries:return next(entries,None) is None

def main():
    record=dict(schema='mckernel.exact-one-scoped-parent-provision.v1',authorization='SourcePR6805178926',target=TARGET,final_output=TARGET+'/'+FINAL,started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=os.getpid(),ppid=os.getppid(),birth=proc_birth(),source_sha256=globals().get('__source_sha256__'),writes_attempted=[],created=False,preexisting=False,secondary_close_errors=[])
    held=[];chain=[];primary=None
    def hold(fd):held.append(fd);return fd
    def verify_chain():
        for index,(name,fd,wanted) in enumerate(chain):
            need(identity(fd)==wanted,'held ancestor identity changed: '+name)
            if index:
                st=os.stat(name,dir_fd=chain[index-1][1],follow_symlinks=False)
                need(stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==(wanted['device'],wanted['inode']),'visible ancestor replaced: '+name)
        need(identity(chain[-1][1])==ANCESTOR_ID,'exact scratch ancestor changed')
        need(identity(ro_fd)==RO_ID,'protected RO directory identity changed')
        st=os.stat('scratch-readonly-20261105',dir_fd=chain[-2][1],follow_symlinks=False)
        need(stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==(RO_ID['device'],RO_ID['inode']),'visible protected RO mapping replaced')
        return verify_mounts()
    def verify_target(fd):
        value=identity(fd);st=os.stat(BASENAME,dir_fd=chain[-1][1],follow_symlinks=False)
        need(stat.S_ISDIR(st.st_mode) and (st.st_dev,st.st_ino)==(value['device'],value['inode']),'visible target identity changed')
        need(value['device']==ANCESTOR_ID['device'],'target filesystem differs from exact ancestor')
        need(value['uid']==value['gid']==1000 and value['mode']==0o700,'target is not exact UID1000:GID1000/0700')
        need(directory_empty(fd),'scoped parent is not empty; no mutation or cleanup permitted')
        need(exact_missing(fd,FINAL),'final stage output must remain absent')
        return value
    try:
        need(type(record['source_sha256']) is str and len(record['source_sha256'])==64,'verified sourceFD bootstrap required')
        need(os.getuid()==os.geteuid()==0,'exact privileged provisioning actor required')
        need(os.sched_getaffinity(0)=={7},'CPU7 affinity required')
        need(resource.getrlimit(resource.RLIMIT_AS)==(268435456,268435456),'actual AS256MiB cap differs')
        need(resource.getrlimit(resource.RLIMIT_CPU)==(30,30),'actual CPU30s cap differs')
        need(resource.getrlimit(resource.RLIMIT_FSIZE)==(8388608,8388608),'actual FSIZE8MiB cap differs')
        need(resource.getrlimit(resource.RLIMIT_CORE)==(0,0),'core files prohibited')
        record['initial_actor']=dict(uid=os.getuid(),euid=os.geteuid(),gid=os.getgid(),affinity=sorted(os.sched_getaffinity(0)))
        fd=hold(os.open('/',FLAGS));chain.append(('/',fd,identity(fd)))
        for name in ('home','holden','mckernel-work','scratch'):
            fd=hold(os.open(name,FLAGS,dir_fd=fd));chain.append((name,fd,identity(fd)))
        ancestor_fd=chain[-1][1];need(identity(ancestor_fd)==ANCESTOR_ID,'initial scratch ancestor identity mismatch')
        ro_fd=hold(os.open('scratch-readonly-20261105',FLAGS,dir_fd=chain[-2][1]));need(identity(ro_fd)==RO_ID,'initial RO view identity mismatch')
        host_fd=hold(os.open('mckernel',FLAGS,dir_fd=chain[2][1]))
        record['before_mounts']=verify_chain();record['before_capacity']=capacity(host_fd,ancestor_fd);record['ancestor_before']=identity(ancestor_fd);record['RO_before']=identity(ro_fd)
        os.umask(0o077)
        if exact_missing(ancestor_fd,BASENAME):
            verify_chain();record['writes_attempted'].append({'action':'mkdirat','basename':BASENAME,'mode':0o700,'beneath_exact_ancestor':ANCESTOR_ID})
            os.mkdir(BASENAME,0o700,dir_fd=ancestor_fd);record['created']=True
            target_fd=hold(os.open(BASENAME,FLAGS,dir_fd=ancestor_fd));initial=identity(target_fd);record['new_inode_before']=initial
            need(initial['device']==ANCESTOR_ID['device'] and initial['uid']==0 and initial['mode']==0o700,'new inode identity differs before any chown')
            st=os.stat(BASENAME,dir_fd=ancestor_fd,follow_symlinks=False);need((st.st_dev,st.st_ino)==(initial['device'],initial['inode']),'new visible inode changed')
            need(directory_empty(target_fd),'new directory unexpectedly contains entries')
            verify_chain();record['writes_attempted'].append({'action':'fchown','device':initial['device'],'inode':initial['inode'],'uid':1000,'gid':1000});os.fchown(target_fd,1000,1000)
            need(identity(target_fd)['inode']==initial['inode'],'held new inode changed after chown')
            verify_chain();record['writes_attempted'].append({'action':'fchmod','device':initial['device'],'inode':initial['inode'],'mode':0o700});os.fchmod(target_fd,0o700)
        else:
            record['preexisting']=True;target_fd=hold(os.open(BASENAME,FLAGS,dir_fd=ancestor_fd));record['existing_identity_readonly']=identity(target_fd)
            # No matching metadata is synthesized, and no chown/chmod occurs here.
            verify_target(target_fd)
        verify_chain();record['target_before_fsync']=verify_target(target_fd)
        # Only the authorized new/exact target and its already verified parent.
        os.fsync(target_fd);os.fsync(ancestor_fd)
        record['durable_target_root_readback']=verify_target(target_fd);record['durable_ancestor_root_readback']=identity(ancestor_fd);record['durable_parent_entry_matches_held_target']=True
        verify_chain()
        # All allowed filesystem mutations are complete before this irreversible drop.
        os.setgroups([1000]);os.setresgid(1000,1000,1000);os.setresuid(1000,1000,1000)
        need(os.getresuid()==(1000,1000,1000) and os.getresgid()==(1000,1000,1000) and os.getgroups()==[1000],'permanent1000 identity drop failed')
        with open('/proc/self/status','r') as stream:status=stream.read(65537)
        need(len(status)<=65536,'self status bound');fields={line.split(':',1)[0]:line.split(':',1)[1].strip() for line in status.splitlines() if ':' in line}
        need(int(fields['CapEff'],16)==int(fields['CapPrm'],16)==0,'capabilities remain after permanent drop')
        need(os.access('.',os.R_OK|os.W_OK|os.X_OK,dir_fd=target_fd,effective_ids=True,follow_symlinks=False),'realUID1000 targetRWX proof failed')
        need(os.access(TARGET,os.R_OK|os.W_OK|os.X_OK,effective_ids=True,follow_symlinks=False),'realUID1000 visible targetRWX proof failed')
        paths=['/','/home','/home/holden','/home/holden/mckernel-work',ANCESTOR]
        for path in paths:need(os.access(path,os.X_OK,effective_ids=True,follow_symlinks=False),'realUID1000 ancestor search failed: '+path)
        record['after_mounts']=verify_chain();record['target_UID1000_readback']=verify_target(target_fd);record['ancestor_after']=identity(ancestor_fd);record['RO_after']=identity(ro_fd);record['after_capacity']=capacity(host_fd,target_fd)
        record['postcheck_actor']=dict(real_effective_saved_UID=list(os.getresuid()),real_effective_saved_GID=list(os.getresgid()),supplementary_groups=os.getgroups(),CapEff=fields['CapEff'],CapPrm=fields['CapPrm'])
        record['actual_UID1000_ancestor_search_and_parent_RWX']=True;record['final_output_absent']=True;record['no_target_files_allocated']=True
        with open('/proc/self/task/%d/children'%os.getpid(),'r') as stream:children=stream.read(4097).split()
        need(not children,'unexpected provisioner child');record['remaining_direct_children']=children
    except BaseException as error:
        primary=error;record['error']={'type':type(error).__name__,'message':str(error)[:2048]};record['partial_target_retained_without_cleanup']=bool(record['created'])
    finally:
        for fd in reversed(held):
            try:os.close(fd)
            except BaseException as error:record['secondary_close_errors'].append({'fd':fd,'type':type(error).__name__})
    record['all_opened_directory_FDs_closed']=not record['secondary_close_errors'];record['finished_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    ok=primary is None and not record['secondary_close_errors']
    record['status']=('PASS_FRESH_SCOPED_PARENT_PROVISIONED_AND_REAL_UID1000_VERIFIED' if record['created'] else 'PASS_EXISTING_MATCHING_SCOPED_PARENT_READONLY_RECONCILED') if ok else 'FAILED_CLOSED_SCOPED_PARENT_ATTEMPT_RETAINED_NO_OTHER_ROUTE'
    record['other_parent_old_objects_mounts_native_or_hold_mutations']=False
    sys.stdout.write(json.dumps(record,sort_keys=True)+'\n');sys.stdout.flush()
    return 0 if ok else 1

if __name__=='__main__':sys.exit(main())
