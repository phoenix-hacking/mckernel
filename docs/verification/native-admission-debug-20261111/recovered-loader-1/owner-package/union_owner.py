"""Functional McKernel source-only union owner; no security testing.

No CLI operation or release. Requires a reviewed root supervisor, actual
independently admitted complete split manifests, exclusive privileged-writer
control, live custody, and an independently running bounded watchdog.
"""
import errno
import hashlib
import json
import math
import os
import select
import socket
import stat
import struct
import threading
import time
from pathlib import Path
import materializer as m
from source_freeze import FrozenInputs, freeze_union, mount_id, require_immutable
import split_inventory

MANIFEST_SHA='48b2c25266784641b28100c08c7c7baa4559d0aaffe670223ee71936f3deaffa'
PROTOCOL=Path(__file__).resolve().parent.parent/'authenticated-adapter-successor-1'/'custody_protocol_v2.py'
PROTOCOL_SHA='587cebf7b8359a1711f078882a012a701e290902dc4376d1bc6e4c03f7ce8cbb'
SPLITS=('/out/build','/out/source/linux-6.12.0-211.44.1.el10_2')
BOOT_CAP=1571568.6959155537
MONO_CAP=1556230.5688700147
UTC_CAP=1793774133
BOOT_ID='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'


def need(ok,message):
    if not ok:raise ValueError(message)


def canonical(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()


def operation_commitment(lease_sha,nonce,operation_root):
    return digest({'lease_sha256':lease_sha,'nonce':nonce,'operation_root':operation_root})


def read_protocol():
    parent=m._absolute_dir(str(PROTOCOL.parent));fd=None
    try:
        fd=os.open(PROTOCOL.name,m._READ,dir_fd=parent);before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=1<<20,'protocol source identity')
        raw=bytearray()
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            raw.extend(chunk);need(len(raw)<=1<<20,'protocol size')
        named=os.stat(PROTOCOL.name,dir_fd=parent,follow_symlinks=False)
        need(m._same(before,os.fstat(fd)) and m._same(before,named) and hashlib.sha256(raw).hexdigest()==PROTOCOL_SHA,'protocol bytes changed')
    finally:
        if fd is not None:os.close(fd)
        os.close(parent)
    env={'__name__':'shared_custody_protocol','__file__':str(PROTOCOL)}
    exec(compile(bytes(raw),str(PROTOCOL),'exec'),env)
    return env


def ident(fd):
    s=os.fstat(fd);need(stat.S_ISDIR(s.st_mode),'directory required')
    return {'device':s.st_dev,'inode':s.st_ino,'kind':'directory'}


def proc_birth(pid):
    fields=Path('/proc/%d/stat'%pid).read_text().rsplit(')',1)[1].split()
    need(fields[0] not in ('Z','X'),'supervisor not live')
    return fields[19]


def no_access_acl(fd):
    for key in ('system.posix_acl_access','system.posix_acl_default'):
        try:os.getxattr(fd,key)
        except OSError as exc:
            if exc.errno in (errno.ENODATA,errno.ENOTSUP):continue
            raise
        raise ValueError('private output directory has extended/default ACL')


def durable(parent_fd,name,obj):
    raw=canonical(obj)+b'\n'
    fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent_fd)
    try:
        offset=0
        while offset<len(raw):
            count=os.write(fd,raw[offset:]);need(count>0,'short evidence write');offset+=count
        os.fsync(fd)
    finally:os.close(fd)
    os.fsync(parent_fd)
    return hashlib.sha256(raw).hexdigest()


def receipt_identity(parent_fd,name,expected_sha,expected_bytes):
    fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=parent_fd)
    try:
        before=os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_uid==0 and stat.S_IMODE(before.st_mode)==0o600 and before.st_nlink==1 and before.st_size<=1<<20,'receipt identity')
        raw=bytearray()
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            raw.extend(chunk);need(len(raw)<=1<<20,'receipt oversized')
        named=os.stat(name,dir_fd=parent_fd,follow_symlinks=False)
        need(m._same(before,os.fstat(fd)) and m._same(before,named) and len(raw)==before.st_size,'receipt changed')
        value=hashlib.sha256(raw).hexdigest();need(value==expected_sha and bytes(raw)==expected_bytes,'receipt digest or content differs')
        return {'device':before.st_dev,'inode':before.st_ino,'mode':stat.S_IMODE(before.st_mode),
                'uid':before.st_uid,'gid':before.st_gid,'nlink':before.st_nlink,
                'size':before.st_size,'mtime_ns':before.st_mtime_ns,'ctime_ns':before.st_ctime_ns,'sha256':value}
    finally:os.close(fd)


class LeaseChannel:
    """One root supervisor union endpoint; channel alive is not mount proof."""
    def __init__(self,sock,pid,birth,nonce,lease_sha,custody_sha,deadline_boot,admitted_caps):
        self.protocol=read_protocol()
        for value in (nonce,lease_sha,custody_sha):self.protocol['sha256_hex'](value)
        need(type(pid) is int and pid>0 and type(birth) is str and birth.isdigit(),'supervisor identity')
        need(sock.family==socket.AF_UNIX and (sock.type & socket.SOCK_STREAM),'Unix stream required')
        need(type(admitted_caps) is dict and set(admitted_caps)=={'boot_id','boot_deadline','monotonic_deadline','deadline'},'admitted caps required')
        need(admitted_caps['boot_id']==BOOT_ID,'boot id differs')
        for key,ceiling in (('boot_deadline',BOOT_CAP),('monotonic_deadline',MONO_CAP),('deadline',UTC_CAP)):
            value=admitted_caps[key]
            need(type(value) in (int,float) and math.isfinite(value) and 0<value<=ceiling,'inherited clock ceiling')
        need(type(deadline_boot) in (int,float) and math.isfinite(deadline_boot) and 0<deadline_boot<=admitted_caps['boot_deadline'],'operation boot ceiling')
        self.sock=sock;self.pid=pid;self.birth=birth;self.nonce=nonce;self.lease_sha=lease_sha;self.custody_sha=custody_sha
        self.deadline_boot=deadline_boot;self.caps=dict(admitted_caps);self.seq=0;self._peer();self._clocks()
    def _peer(self):
        pid,uid,gid=struct.unpack('3i',self.sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        need(uid==0 and pid==self.pid and os.getppid()==pid and proc_birth(pid)==self.birth,'root direct-parent peer changed')
    def _clocks(self):
        boot=time.clock_gettime(time.CLOCK_BOOTTIME);mono=time.monotonic();utc=time.time()
        need(Path('/proc/sys/kernel/random/boot_id').read_text().strip()==self.caps['boot_id'],'boot changed')
        need(0<boot<self.deadline_boot and boot<self.caps['boot_deadline'] and
             0<mono<self.caps['monotonic_deadline'] and 0<utc<self.caps['deadline'],'clock ceiling expired')
    def assert_live(self):
        self._peer();self._clocks()
        p=select.poll();p.register(self.sock.fileno(),select.POLLIN|select.POLLHUP|select.POLLERR|select.POLLNVAL)
        need(not p.poll(0),'supervisor channel closed or has unsolicited data')
        return True
    def revoke(self):
        try:self.sock.shutdown(socket.SHUT_RDWR)
        except OSError:pass
        finally:self.sock.close()
    def observation(self,operation,targets):
        return {'operation':operation,'lease_sha256':self.lease_sha,'custody_sha256':self.custody_sha,
                'nonce':self.nonce,'targets':targets}
    def request(self,operation,targets,ready=None,transcript=None,expected_status='HELD',return_reply=False):
        self._peer();self._clocks();start=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
        need(start<int(self.deadline_boot*1e9),'supervisor deadline')
        self.seq+=1
        observed=self.observation(operation,targets)
        payload={'observation':observed}
        if ready is not None:payload['ready']=ready
        if transcript is not None:
            need(type(transcript) is dict and set(transcript)=={'prepare_request_sha256','prepare_accept_sha256'},'transcript shape')
            for value in transcript.values():self.protocol['sha256_hex'](value)
            payload.update(transcript)
        env=self.protocol['envelope']('union',operation,self.nonce,self.seq,self.lease_sha,self.custody_sha,payload)
        self.protocol['send'](self.sock,env,self.deadline_boot)
        reply=self.protocol['receive'](self.sock,self.deadline_boot)
        result=self.protocol['validate'](reply,'union',operation,self.nonce,self.seq,self.lease_sha,self.custody_sha)
        end=time.clock_gettime_ns(time.CLOCK_BOOTTIME);self._peer();self._clocks()
        need(type(result) is dict and set(result)=={'status','observed_boot_ns','request_sha256','observation_sha256'},'supervisor reply shape')
        stamp=result['observed_boot_ns']
        need(result['status']==expected_status and type(stamp) is int and start<=stamp<=end and end<int(self.deadline_boot*1e9),'supervisor observation stale')
        need(result['request_sha256']==digest(payload) and result['observation_sha256']==digest(observed),'supervisor observation binding')
        return result if return_reply else True


class UnknownPublicationError(RuntimeError):pass


class UnionOwner:
    """One owner with held source, split and output FDs; never retires itself."""
    def __init__(self,lease,output_parent,split_paths,split_specs,manifest_bytes):
        need(type(lease) is LeaseChannel,'authenticated channel required')
        need(hashlib.sha256(manifest_bytes).hexdigest()==MANIFEST_SHA,'exact scripts manifest')
        self.document=json.loads(manifest_bytes,object_pairs_hook=lease.protocol['unique'])
        need(set(split_paths)==set(SPLITS) and set(split_specs)==set(SPLITS),'exact split inputs required')
        for target in SPLITS:
            row=split_specs[target]
            need(type(row) is dict and set(row)=={'members','manifest_sha256'},'split spec shape')
            lease.protocol['sha256_hex'](row['manifest_sha256'])
            need(digest(row['members'])==row['manifest_sha256'],'split manifest digest differs')
        self.lease=lease;self.parent_path=str(output_parent);self.split_paths=split_paths;self.split_specs=split_specs
        self.fds=[];self.freeze=None;self.held_paths={};self.targets={};self.state='NEW';self.created=False;self.intent=False
        self.claim=threading.Lock();self.io_lock=threading.Lock();self.state_lock=threading.RLock()
        self.started=False;self.ready=False;self.unknown_latched=False
    def _pin(self,path):
        fd,pins=m._absolute_dir_pins(path);self.fds.append(fd);self.held_paths[path]=(fd,pins)
        return fd
    def _local_targets(self):
        need(not self.unknown_latched,'unknown ownership is sticky')
        if self.freeze is not None:self.freeze.verify()
        for path,(fd,pins) in self.held_paths.items():m._revalidate_destination_parent(path,pins,fd)
        rows={}
        for target,(path,fd,members,frozen) in self.targets.items():
            observed,inv=split_inventory.snapshot(fd,members,require_frozen=frozen)
            rows[target]={'path':path,'identity':observed['root'],'inventory_sha256':inv}
        return rows
    def _revalidate(self,operation='union-lease-check',select_targets=None):
        rows=self._local_targets()
        selected=rows if select_targets is None else {t:rows[t] for t in select_targets}
        self.lease.request(operation,selected)
        after=self._local_targets()
        need(after==rows,'actual held observation changed across supervisor check')
        return True
    def _epoch_start(self):
        self.freeze.epoch_start()
        self.epoch_paths={path:(ident(fd),mount_id(fd)) for path,(fd,_) in self.held_paths.items()}
        self._epoch_guard()
    def _epoch_guard(self):
        need(not self.unknown_latched,'unknown ownership is sticky')
        self.lease.assert_live();self.freeze.epoch_check()
        for path,(fd,pins) in self.held_paths.items():
            expected=self.epoch_paths[path]
            need((ident(fd),mount_id(fd))==expected,'held path identity/mount changed')
            m._revalidate_destination_parent(path,pins,fd)
            current=m._absolute_dir(path)
            try:need((ident(current),mount_id(current))==expected,'named path identity/mount changed')
            finally:os.close(current)
        for target in SPLITS:require_immutable(self.targets[target][1])
        self.lease.assert_live();return True
    def _journal(self,record):
        self.journal_seq+=1;row={'seq':self.journal_seq,'nonce':self.lease.nonce,**record}
        raw=canonical(row)+b'\n';offset=0
        while offset<len(raw):
            count=os.write(self.journal_fd,raw[offset:]);need(count>0,'short freeze journal write');offset+=count
        os.fsync(self.journal_fd)
    def _unknown(self,exc):
        with self.state_lock:
            self.unknown_latched=True
            self.state='UNKNOWN_RETAINED' if self.intent or self.created else 'DENIED_BEFORE_OUTPUT'
            self.ready=False
        try:self.lease.revoke()
        except BaseException:pass
        if self.intent or self.created:
            try:
                durable(self.parentfd,'SOURCE-UNKNOWN-'+self.lease.nonce+'.json',
                        {'status':self.state,'nonce':self.lease.nonce,'error':type(exc).__name__})
            except BaseException as publication:
                raise UnknownPublicationError('UNKNOWN ownership retained; publication failed') from publication
    def _announce_ready(self,parent,result,receipt_name,receipt):
        # No other union request can interleave between prepare and commit.
        with self.io_lock:
            need(self.state=='PREPARING' and not self.ready,'ready transition unavailable')
            need(receipt_name=='SOURCE-SUCCESS-'+self.lease.nonce+'.json','ready receipt name differs')
            need(result.get('status')=='PROVISIONAL_HELD_SOURCE_ONLY' and result.get('nonce')==self.lease.nonce and
                 result.get('lease_sha256')==self.lease.lease_sha and result.get('custody_sha256')==self.lease.custody_sha,'ready receipt fields differ')
            self._revalidate();final_rows=self._local_targets()
            need(final_rows==result['targets'],'targets changed before prepare')
            expected_bytes=canonical(result)+b'\n'
            ref=receipt_identity(parent,receipt_name,receipt,expected_bytes)
            ready={'owner_pid':os.getpid(),'owner_birth':proc_birth(os.getpid()),
                   'operation_root':ident(parent),'receipt_name':receipt_name,'receipt':ref}
            prepare_payload={'observation':self.lease.observation('union-owner-prepare',final_rows),'ready':ready}
            before_seq=self.lease.seq
            accepted=self.lease.request('union-owner-prepare',final_rows,ready=ready,
                                        expected_status='ACCEPTED',return_reply=True)
            need(self.lease.seq==before_seq+1,'prepare sequence changed')
            # This is a local re-observation: an intervening wire request would
            # consume the next sequence and invalidate the two-sided handshake.
            self.lease.assert_live()
            need(self._local_targets()==final_rows,'targets changed after acceptance')
            need(receipt_identity(parent,receipt_name,receipt,expected_bytes)==ref,'receipt changed after acceptance')
            self.lease.assert_live()
            need(self.lease.seq==before_seq+1,'unexpected interleaved request')
            transcript={'prepare_request_sha256':digest(prepare_payload),'prepare_accept_sha256':digest(accepted)}
            with self.state_lock:
                need(not self.unknown_latched and self.state=='PREPARING','unknown ownership prevents commit')
                self.ready_receipt=(receipt_name,receipt,ref,expected_bytes)
                self.state='HELD';self.ready=True
                # Once COMMIT is sent, only transport and continuing lease health
                # may fail; no later source check can authorize this commit.
                self.lease.request('union-owner-commit',final_rows,ready=ready,transcript=transcript)
    def prepare(self):
        with self.claim:
            need(not self.started,'owner already used');self.started=True;self.state='PREPARING'
        try:
            need(os.geteuid()==0,'root-owned materialization required')
            self.lease.request('union-lease-check',{})
            source=self.document['base_scripts_candidate'];self.freeze=FrozenInputs(source,self.document)
            parent=self._pin(self.parent_path);self.parentfd=parent
            parentstat=os.fstat(parent)
            need(parentstat.st_uid==0 and stat.S_IMODE(parentstat.st_mode)&0o077==0,'private output parent required')
            no_access_acl(parent)
            expected_commitment=operation_commitment(self.lease.lease_sha,self.lease.nonce,ident(parent))
            need(expected_commitment==self.lease.custody_sha,'operation-root custody commitment differs')
            for target,path in self.split_paths.items():
                fd=self._pin(path)
                self.targets[target]=(path,fd,self.split_specs[target]['members'],True)
            rows=self._local_targets();need(len({(v['identity']['device'],v['identity']['inode']) for v in rows.values()})==2,'split inputs alias')
            self._revalidate('union-bind-split-inputs',SPLITS)
            self._revalidate();name='scripts-union-'+self.lease.nonce
            self.intent=True
            durable(parent,'SOURCE-INTENT-'+self.lease.nonce+'.json',{'status':'INTENT','nonce':self.lease.nonce,'lease_sha256':self.lease.lease_sha,'custody_sha256':self.lease.custody_sha})
            os.mkdir(name,0o700,dir_fd=parent);self.created=True;os.fsync(parent)
            self.root_path=os.path.join(self.parent_path,name);root=self._pin(self.root_path);no_access_acl(root)
            os.mkdir('work',0o700,dir_fd=root);work_path=os.path.join(self.root_path,'work');work=self._pin(work_path)
            no_access_acl(work)
            self.targets['/work']=(work_path,work,{},False)
            self._revalidate()
            scripts_path=os.path.join(self.root_path,'scripts')
            m.copy_scripts_body(source,scripts_path,self.document);scripts=self._pin(scripts_path);os.fsync(root)
            durable(parent,'FREEZE-INTENT-'+self.lease.nonce+'.json',{'status':'INTENT','nonce':self.lease.nonce,'scripts':ident(scripts)})
            self.journal_fd=os.open('FREEZE-JOURNAL-'+self.lease.nonce+'.jsonl',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=parent)
            self.fds.append(self.journal_fd);os.fsync(parent);self.journal_seq=0
            self._revalidate();self._epoch_start()
            freeze_union(scripts,self.document,self._epoch_guard,self._journal)
            _,union=m._load_checker()['index_manifest'](self.document)
            members={path:({'type':row['type'],'mode':int(row['mode'],8),**({'bytes':row['bytes'],'sha256':row['sha256']} if row['type']=='file' else {})}) for path,row in union.items()}
            self.targets['/src/scripts']=(scripts_path,scripts,members,True)
            self._revalidate('union-freeze-output',('/src/scripts',))
            rows=self._local_targets();need(len({(v['identity']['device'],v['identity']['inode']) for v in rows.values()})==4,'target root alias')
            self._revalidate()
            result={'status':'PROVISIONAL_HELD_SOURCE_ONLY','nonce':self.lease.nonce,'lease_sha256':self.lease.lease_sha,
                    'custody_sha256':self.lease.custody_sha,'targets':rows,'source_manifest_sha256':MANIFEST_SHA,
                    'current_free':False,'mount_evidence':False,'owner_lifetime':'HELD'}
            receipt_name='SOURCE-SUCCESS-'+self.lease.nonce+'.json'
            receipt=durable(parent,receipt_name,result)
            self._announce_ready(parent,result,receipt_name,receipt)
            return result,receipt
        except BaseException as exc:
            self._unknown(exc);raise
    def custody(self):
        with self.io_lock:
            need(self.state=='HELD' and self.ready,'owner has no acknowledged held result')
            try:
                self._revalidate()
                name,digest_value,ref,expected_bytes=self.ready_receipt
                need(receipt_identity(self.parentfd,name,digest_value,expected_bytes)==ref,'ready receipt changed')
                rows=self._local_targets()
                need(rows==json.loads(expected_bytes)['targets'],'ready targets changed')
                return rows
            except BaseException as exc:
                self._unknown(exc);raise
    def close_after_independent_retirement(self):
        raise RuntimeError('No source-only authority to retire or release held custody')

if __name__=='__main__':raise RuntimeError('SOURCE ONLY: no actual operation release or physical owner binding')
