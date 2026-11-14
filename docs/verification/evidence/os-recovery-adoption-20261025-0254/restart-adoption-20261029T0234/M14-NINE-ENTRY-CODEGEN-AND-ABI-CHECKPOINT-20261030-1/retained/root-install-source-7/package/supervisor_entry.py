"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Verified-load entry for one root operation; no activation at import.
"""
import fcntl
import hashlib
import json
import os
import signal
import stat
import struct
import time
import graph_observations as obs
import operation_supervisor
import root_bootstrap
import inplace_custody as source
import deferred_fork
import runtime_binding


def fail(msg):raise ValueError(msg)


def unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:fail('duplicate config key')
        result[key]=value
    return result


def bootstrap_file(value):
    """One-shot root-only bootstrap; never overwrite or remove a predecessor."""
    parent=source.open_exact('/etc/mckernel/m14-graph-owner')
    try:
        source.root_private(parent)
        name='bootstrap.json'
        fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
        try:
            raw=obs.canonical(value)+b'\n';source.write_all(fd,raw)
            os.fsync(fd);os.fsync(parent)
            flags=source.flags(fd)
            fcntl.ioctl(fd,source.SETFLAGS,struct.pack('I',flags|source.IMMUTABLE))
            if not source.flags(fd)&source.IMMUTABLE:fail('bootstrap freeze failed')
            os.fsync(fd);os.fsync(parent)
            return hashlib.sha256(raw).hexdigest()
        finally:os.close(fd)
    finally:os.close(parent)


def verify_actual_operation_gates():
    # A frozen config and process liveness do not prove current controls,
    # stop/hold, weekly account, native ownership or resource admission.
    # Keep activation disabled until a separately reviewed live-gate adapter
    # binds those actual facts and the exact one-shot operation.
    raise RuntimeError('actual fresh operation gates are not implemented')


def run(config_path,config_sha,root_fd,lease_fd):
    """Operation entry called only from reviewed immutable-source loader.

    The watchdog parent retains both descriptors and supervises this exact PID.
    Mount activity belongs to a separately admitted owner; this function only
    observes its target namespace. Any failure preserves UNKNOWN and never cleans.
    """
    if os.geteuid()!=0:fail('root supervisor required')
    config_fd,raw=root_bootstrap.pinned_root_file(config_path,config_sha)
    held=[config_fd]
    cfg=json.loads(raw,object_pairs_hook=unique)
    keys={'nonce','boot_id','caps','watchdog_pid','watchdog_birth','owner','source_manifest',
          'target','validator','supervisor_entry_path','supervisor_entry_sha','interpreter_sha',
          'deadline_boot','mount_poll_seconds','runtime'}
    if type(cfg) is not dict or set(cfg)!=keys:fail('supervisor config shape')
    if type(cfg['runtime']) is not dict or set(cfg['runtime'])!={'path','sha256'}:fail('runtime config')
    runtime_binding.verify_current(cfg['runtime']['path'],cfg['runtime']['sha256'])
    if cfg['watchdog_pid']!=os.getppid() or obs.process(os.getppid())[0]!=cfg['watchdog_birth']:
        fail('watchdog parent identity changed')
    if type(cfg['deadline_boot']) not in (int,float) or not time.clock_gettime(time.CLOCK_BOOTTIME)<cfg['deadline_boot']<=cfg['caps']['boot']:
        fail('operation deadline')
    interval=cfg['mount_poll_seconds']
    if type(interval) not in (int,float) or not 1<=interval<=30:fail('mount polling bound')
    owner=cfg['owner'];validator=cfg['validator'];target=cfg['target'];manifest=cfg['source_manifest']
    if type(owner) is not dict or set(owner)!={'executable','executable_sha','entry','entry_sha','argv','environment','targets','max_step','bootstrap_source','bootstrap_sha','owner_config_path','owner_config_sha'}:
        fail('owner config')
    if type(validator) is not dict or set(validator)!={'executable','executable_sha','entry','entry_sha','argv','environment','uid','gid','max_age','max_step','bootstrap_source','bootstrap_sha','loader_manifest','loader_sha'}:
        fail('validator config')
    if (owner['executable']!=cfg['runtime']['path'] or owner['executable_sha']!=cfg['runtime']['sha256'] or
        validator['executable']!=cfg['runtime']['path'] or validator['executable_sha']!=cfg['runtime']['sha256']):
        fail('owner or validator runtime differs from verified supervisor')
    if type(target) is not dict or set(target)!={'pid','birth','mount_dev','mount_inode','hosts'}:fail('target config')
    if type(manifest) is not dict or set(manifest)!={'path','sha256'}:fail('source manifest config')
    verify_actual_operation_gates()
    operation=None
    try:
        operation=operation_supervisor.OperationSupervisor.__new__(operation_supervisor.OperationSupervisor)
        operation.__init__(root_fd,lease_fd,cfg['nonce'],cfg['boot_id'],cfg['caps'],cfg['watchdog_pid'],cfg['watchdog_birth'])
        bootstrap_fd,bootstrap_bytes=root_bootstrap.pinned_root_file(owner['bootstrap_source'],owner['bootstrap_sha']);held.append(bootstrap_fd)
        generated=root_bootstrap.owner_argv(owner['executable'],bootstrap_bytes,owner['entry'],owner['entry_sha'],
                                            owner['owner_config_path'],owner['owner_config_sha'])
        if generated!=owner['argv']:fail('owner verified-loader argv differs')
        operation.launch_owner(owner['executable'],owner['executable_sha'],owner['entry'],owner['entry_sha'],
            generated,owner['environment'],owner['targets'],cfg['deadline_boot'],owner['max_step'])
        operation.start_owner_service()
        while not operation.owner.ready_snapshot():
            if operation.state=='UNKNOWN_RETAINED' or time.clock_gettime(time.CLOCK_BOOTTIME)>=cfg['deadline_boot']:
                fail('owner READY unavailable')
            operation.lease.verify();time.sleep(0.1)
        mf,manifest_bytes=root_bootstrap.pinned_root_file(manifest['path'],manifest['sha256']);held.append(mf)
        operation.acquire_sources(manifest_bytes,manifest['sha256'])
        expected=(target['birth'],target['mount_dev'],target['mount_inode'])
        if obs.process(target['pid'])!=expected:fail('target mount namespace changed')
        operation.observe_before_children(target['pid'],target['hosts'])
        while True:
            operation.lease.verify();operation.owner.verify_owner()
            if operation.state=='UNKNOWN_RETAINED' or time.clock_gettime(time.CLOCK_BOOTTIME)>=cfg['deadline_boot']:
                fail('effective mount wait failed')
            mounts=obs.read_mountinfo(target['pid'],expected)
            if all(child in mounts for child in obs.CHILDREN):break
            time.sleep(interval)
        operation.observe_effective_graph()
        # This exact in-process argv identifies the reviewed immutable loader.
        argv=open('/proc/self/cmdline','rb').read().split(b'\0')
        if argv[-1:]!=[b'']:fail('supervisor argv')
        argv=[x.decode('utf-8') for x in argv[:-1]]
        if cfg['supervisor_entry_path'] not in argv:fail('supervisor entry argv missing')
        record={'version':1,'supervisor_source':cfg['supervisor_entry_path'],'supervisor_sha256':cfg['supervisor_entry_sha'],
          'interpreter_sha256':cfg['interpreter_sha'],'argv':argv,'contract_sha256':obs.CONTRACT_SHA,
          'lease_sha256':operation.lease.lease_sha256,'custody_sha256':operation.custody_sha256,
          'nonce':cfg['nonce'],'caps':cfg['caps'],'boot_id':cfg['boot_id'],'max_age_seconds':validator['max_age'],
          'max_step_seconds':validator['max_step']}
        bootstrap_file(record)
        exefd,_=root_bootstrap.pinned_root_file(validator['executable'],validator['executable_sha'],128*1024*1024);held.append(exefd)
        entryfd,_=root_bootstrap.pinned_root_file(validator['entry'],validator['entry_sha']);held.append(entryfd)
        bsfd,bsbytes=root_bootstrap.pinned_root_file(validator['bootstrap_source'],validator['bootstrap_sha']);held.append(bsfd)
        loaderfd,_=root_bootstrap.pinned_root_file(validator['loader_manifest'],validator['loader_sha']);held.append(loaderfd)
        expected_argv=root_bootstrap.validator_argv(validator['executable'],bsbytes,validator['loader_manifest'],validator['loader_sha'],validator['entry'])
        if validator['argv']!=expected_argv:fail('validator exact loader argv differs')
        with deferred_fork.DeferredFork() as guard:
            record=operation.reserve_validator(exefd,entryfd,bsfd,loaderfd,root_fd,lease_fd)
            journal_name='PIDFD-CUSTODY-'+cfg['nonce']+'.jsonl'
            journal_fd=os.open(journal_name,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=root_fd)
            record.add(journal_fd)
            source.write_all(journal_fd,obs.canonical({'status':'REGISTERED','nonce':cfg['nonce'],
                'supervisor_pid':os.getpid(),'supervisor_birth':obs.process(os.getpid())[0],
                'journal_device':os.fstat(journal_fd).st_dev,'journal_inode':os.fstat(journal_fd).st_ino,
                'role':'validator-supervisor-pidfd'})+b'\n')
            os.fsync(journal_fd);os.fsync(root_fd)
            sock,pid,pidfd,result=root_bootstrap.fork_validator(validator['executable'],validator['argv'],
                                          validator['uid'],validator['gid'],validator['environment'],record,guard,journal_fd,cfg['nonce'])
        if result[0]!='BOUND':
            operation.abort('validator pidfd unknown',record,sock);fail('validator pidfd unknown')
        held.append(pidfd);birth=record.birth
        operation.bind_validator(sock,pid,birth,pidfd,cfg['deadline_boot'],validator['max_age'],validator['max_step'],record)
        operation.start_graph_service()
        while operation.state!='UNKNOWN_RETAINED' and time.clock_gettime(time.CLOCK_BOOTTIME)<cfg['deadline_boot']:
            operation.lease.verify();time.sleep(1)
        fail('operation finished or ownership uncertain; watchdog retains custody')
    except BaseException:
        if operation is not None:
            operation.abort('entry failure')
            try:operation.collect_direct_joins()
            except BaseException:pass  # Direct-join publication failure remains UNKNOWN.
        # Keep child processes, flags, descriptors and lease until watchdog acts;
        # it alone may bound the direct child and still reports UNKNOWN.
        while True:signal.pause()


if __name__=='__main__':raise RuntimeError('SOURCE ONLY: verified loader and separately reviewed admission required')
