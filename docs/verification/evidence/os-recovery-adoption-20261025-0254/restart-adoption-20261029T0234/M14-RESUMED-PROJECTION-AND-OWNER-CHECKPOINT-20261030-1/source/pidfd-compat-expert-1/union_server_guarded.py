"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-side union custody handler; no process creation or release at import.
"""
import hashlib
import pidfd_compat
import os
import select
import socket
import struct
import json
import stat
import threading
import custody_protocol_v2 as wire
import graph_observations as obs
import inplace_custody as source
import source_freeze
import split_inventory
import immutable_epoch
from ownership_latch import CustodyLatch


def fail(msg):raise ValueError(msg)


def birth(pid):
    fields=open('/proc/%d/stat'%pid).read().rsplit(')',1)[1].split()
    if len(fields)<20 or fields[0] in ('Z','X','x'):fail('union owner unavailable')
    return int(fields[1]),fields[19]


class UnionChannel:
    def __init__(self,sock,owner_pid,owner_birth,lease,custody_sha,expected_targets,deadline,max_step,latch):
        if os.geteuid()!=0 or birth(owner_pid)!=(os.getpid(),owner_birth):fail('owner is not direct child')
        creds=struct.unpack('3i',sock.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
        if sock.family!=socket.AF_UNIX or creds[0]!=os.getpid() or creds[1]!=0:fail('root-created socketpair required')
        if type(expected_targets) is not dict or set(expected_targets)!={'/src/scripts','/out/build','/out/source/linux-6.12.0-211.44.1.el10_2','/work'}:
            fail('exact owner target bindings required')
        wire.sha256_hex(custody_sha)
        if type(latch) is not CustodyLatch:fail('operation failure latch required')
        self.op_latch=latch
        self.sock,self.pid,self.birth,self.lease,self.custody_sha=sock,owner_pid,owner_birth,lease,custody_sha
        if type(max_step) not in (int,float) or not 0 < max_step <= 600:fail('reviewed finite operation limit required')
        self.expected=expected_targets;self.deadline=deadline;self.max_step=max_step;self.seq=0
        try:self.pidfd=pidfd_compat.open_pidfd(owner_pid,0)
        except pidfd_compat.PidfdVerificationError as error:
            self.pidfd=error.fd
            raise
        self.state='HELD';self.observed_targets={};self.ready=None;self.ready_fd=None;self.prepared=None;self.pending_fd=None;self.epochs={};self.guard=threading.RLock()

    def verify_owner(self):
        with self.guard:return self._verify_owner()

    def _verify_owner(self):
        poll=select.poll();poll.register(self.pidfd,select.POLLIN)
        link=select.poll();link.register(self.sock.fileno(),select.POLLHUP|select.POLLERR|select.POLLNVAL)
        if (self.state!='HELD' or poll.poll(0) or link.poll(0) or birth(self.pid)!=(os.getpid(),self.birth) or wire.boot_now()>=self.deadline):
            self.state='UNKNOWN_RETAINED';fail('union owner lost')
        self.lease.verify()
        if self.ready is not None:
            fd=self.ready_fd; current=os.fstat(fd)
            named=os.stat(self.ready['receipt_name'],dir_fd=self.lease.root_fd,follow_symlinks=False)
            if obs.canonical(_receipt_meta(current))!=obs.canonical({k:v for k,v in self.ready['receipt'].items() if k!='sha256'}) or (current.st_dev,current.st_ino)!=(named.st_dev,named.st_ino):
                self.state='UNKNOWN_RETAINED';self.ready=None;fail('ready receipt changed')
            if _fd_hash(fd)!=self.ready['receipt']['sha256']:
                self.state='UNKNOWN_RETAINED';self.ready=None;fail('ready receipt bytes changed')

    def ready_snapshot(self):
        with self.guard:
            self._verify_owner()
            return self.ready is not None

    def require_ready(self):
        with self.guard:
            self._verify_owner()
            if self.ready is None:fail('committed owner readiness missing')
            return self.ready_seq

    def handle_one(self):
        with self.guard:return self._handle_one()

    def _handle_one(self):
        self.verify_owner()
        token=self.op_latch.snapshot()
        if token[0]=='UNKNOWN_RETAINED':fail('operation already failed')
        deadline=min(self.deadline,wire.boot_now()+self.max_step)
        try:
            msg=wire.receive(self.sock,deadline)
            if type(msg) is not dict:fail('union envelope missing')
            op=msg.get('operation');allowed={'union-lease-check','union-freeze-output','union-bind-split-inputs','union-owner-prepare','union-owner-commit'}
            if op not in allowed:fail('union operation')
            if self.prepared is not None and op!='union-owner-commit':fail('prepared commit must be next')
            if self.prepared is None and op=='union-owner-commit':fail('commit without prepare')
            self.seq+=1
            payload=wire.validate(msg,'union',op,self.lease.nonce,self.seq,self.lease.lease_sha256,self.custody_sha)
            expected_keys=({'observation','ready'} if op=='union-owner-prepare' else
                           {'observation','ready','prepare_request_sha256','prepare_accept_sha256'} if op=='union-owner-commit' else {'observation'})
            if type(payload) is not dict or set(payload)!=expected_keys:fail('union payload shape')
            observation=payload['observation']
            if type(observation) is not dict or set(observation)!={'operation','lease_sha256','custody_sha256','nonce','targets'}:
                fail('union observation shape')
            if (observation['operation']!=op or observation['lease_sha256']!=self.lease.lease_sha256 or
                observation['custody_sha256']!=self.custody_sha or observation['nonce']!=self.lease.nonce):fail('union binding')
            targets=observation['targets']
            if type(targets) is not dict or not set(targets)<=set(self.expected):fail('union target set')
            if op in ('union-owner-prepare','union-owner-commit') and set(targets)!=set(self.expected):fail('ready requires four targets')
            if op=='union-freeze-output' and set(targets)!={'/src/scripts'}:fail('freeze target')
            if op=='union-bind-split-inputs' and set(targets)!={'/out/build','/out/source/linux-6.12.0-211.44.1.el10_2'}:fail('split targets')
            actual={}
            for target,row in targets.items():
                expected=self.expected[target]
                if type(row) is not dict or set(row)!={'path','identity','inventory_sha256'} or row['path']!=expected['path']:
                    fail('target path differs')
                fd=source.open_exact(row['path'])
                try:
                    st=os.fstat(fd)
                    if not stat_is_dir(st):fail('owner target not directory')
                    if target=='/work':
                        source.root_private(fd)
                        inventory=obs.inventory(row['path'])
                    elif target in self.epochs:
                        inventory=self.epochs[target].verify()[target]
                    else:
                        source.walk(fd,row['path'],'verify')
                        inventory=obs.inventory(row['path'])
                        if target=='/src/scripts':
                            source_freeze.verify_immutable_union(fd, expected['manifest'])
                        elif target in ('/out/build','/out/source/linux-6.12.0-211.44.1.el10_2'):
                            _, independent=split_inventory.snapshot(fd,expected['manifest'])
                            if independent!=inventory:fail('target independent inventory differs')
                        self.epochs[target]=immutable_epoch.ImmutableEpoch.__new__(immutable_epoch.ImmutableEpoch)
                        self.epochs[target].__init__({target:row['path']},{target:inventory},self.deadline)
                    actual[target]={'path':row['path'],'identity':obs.ident(st),'inventory_sha256':inventory}
                finally:os.close(fd)
            computed=dict(operation=op,lease_sha256=self.lease.lease_sha256,custody_sha256=self.custody_sha,
                          nonce=self.lease.nonce,targets=actual)
            if obs.canonical(computed)!=obs.canonical(observation):fail('target actual observation differs')
            self.observed_targets.update(actual)
            if op=='union-owner-prepare':
                if self.prepared is not None:fail('duplicate readiness prepare')
                ready=self._bind_ready(payload['ready'],computed)
            elif op=='union-owner-commit':
                old=self.prepared
                if (self.seq!=old['seq']+1 or obs.canonical(payload['ready'])!=obs.canonical(old['ready']) or
                    obs.canonical(actual)!=obs.canonical(old['targets']) or
                    payload['prepare_request_sha256']!=old['request_sha256'] or
                    payload['prepare_accept_sha256']!=old['accept_sha256']):
                    fail('readiness commit binding')
                self._verify_receipt(old['ready'],self.pending_fd)
            self.verify_owner()
            result={'status':'ACCEPTED' if op=='union-owner-prepare' else 'HELD',
                    'observed_boot_ns':__import__('time').clock_gettime_ns(__import__('time').CLOCK_BOOTTIME),
                    'request_sha256':hashlib.sha256(obs.canonical(payload)).hexdigest(),
                    'observation_sha256':hashlib.sha256(obs.canonical(computed)).hexdigest()}
            if op=='union-owner-prepare':
                self.prepared={'ready':ready,'targets':actual,'seq':self.seq,
                    'request_sha256':result['request_sha256'],
                    'accept_sha256':hashlib.sha256(obs.canonical(result)).hexdigest()}
            def publish():
                wire.send(self.sock,wire.envelope('union',op,self.lease.nonce,self.seq,self.lease.lease_sha256,
                          self.custody_sha,result),deadline)
                if op=='union-owner-commit':
                    self.ready,self.ready_fd,self.ready_seq=self.prepared['ready'],self.pending_fd,self.seq
                    self.pending_fd=None;self.prepared=None
            self.op_latch.publish(token,publish)
        except BaseException:
            # Keep pending receipt FD and evidence reachable on uncertain commit.
            self.state='UNKNOWN_RETAINED';self.ready=None;raise

    def _verify_receipt(self,ready,fd):
        current=os.fstat(fd)
        named=os.stat(ready['receipt_name'],dir_fd=self.lease.root_fd,follow_symlinks=False)
        if (obs.canonical(_receipt_meta(current))!=obs.canonical({k:v for k,v in ready['receipt'].items() if k!='sha256'}) or
            (current.st_dev,current.st_ino)!=(named.st_dev,named.st_ino) or _fd_hash(fd)!=ready['receipt']['sha256']):
            fail('prepared receipt changed')

    def _bind_ready(self, ready, observation):
        if self.ready is not None or type(ready) is not dict or set(ready)!={'owner_pid','owner_birth','operation_root','receipt_name','receipt'}:
            fail('ready shape or duplicate')
        if (type(ready['owner_pid']) is not int or ready['owner_pid']!=self.pid or ready['owner_birth']!=self.birth or
            obs.canonical(ready['operation_root'])!=obs.canonical(obs.ident(os.fstat(self.lease.root_fd))) or
            ready['receipt_name']!='SOURCE-SUCCESS-'+self.lease.nonce+'.json'):
            fail('ready identity binding')
        record=ready['receipt']
        if type(record) is not dict or set(record)!={'device','inode','mode','uid','gid','nlink','size','mtime_ns','ctime_ns','sha256'}:
            fail('ready receipt shape')
        fd=os.open(ready['receipt_name'],os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=self.lease.root_fd)
        try:
            st=os.fstat(fd)
            if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600 or st.st_nlink!=1 or st.st_size>1048576:
                fail('ready receipt ownership')
            if obs.canonical(_receipt_meta(st))!=obs.canonical({k:v for k,v in record.items() if k!='sha256'}) or _fd_hash(fd)!=record['sha256']:
                fail('ready receipt identity or bytes')
            raw=os.pread(fd,1048577,0)
            doc=json.loads(raw,object_pairs_hook=wire.unique)
            if (type(doc) is not dict or doc.get('status')!='PROVISIONAL_HELD_SOURCE_ONLY' or
                doc.get('owner_lifetime')!='HELD' or doc.get('nonce')!=self.lease.nonce or
                doc.get('lease_sha256')!=self.lease.lease_sha256 or doc.get('custody_sha256')!=self.custody_sha or
                obs.canonical(doc.get('targets'))!=obs.canonical(observation['targets']) or doc.get('current_free') is not False or
                doc.get('mount_evidence') is not False):
                fail('ready receipt content')
            if birth(self.pid)!=(os.getpid(),self.birth):fail('ready owner identity changed')
            self.pending_fd=fd;fd=None
            return ready
        finally:
            if fd is not None:os.close(fd)


def _fd_hash(fd):
    return hashlib.sha256(os.pread(fd,1048577,0)).hexdigest()


def _receipt_meta(st):
    return dict(device=st.st_dev,inode=st.st_ino,mode=stat.S_IMODE(st.st_mode),uid=st.st_uid,gid=st.st_gid,
                nlink=st.st_nlink,size=st.st_size,mtime_ns=st.st_mtime_ns,ctime_ns=st.st_ctime_ns)


def stat_is_dir(st):
    return stat.S_ISDIR(st.st_mode)
